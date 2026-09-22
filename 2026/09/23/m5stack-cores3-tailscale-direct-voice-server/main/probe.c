// CoreS3: Wi-Fi -> Tailscale -> one complete WAV, without VPS or audio playback.
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "esp_event.h"
#include "esp_heap_caps.h"
#include "esp_http_client.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_netif_sntp.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "tailscale_esp32.h"

#if __has_include("config.h")
#include "config.h"
#else
#include "config.example.h"
#endif

static const char *TAG = "probe";
static EventGroupHandle_t wifi_events;
#define WIFI_READY BIT0
#define MAX_WAV_BYTES (2U * 1024U * 1024U)

static void log_heap(const char *stage)
{
    ESP_LOGI(TAG, "heap %s: internal=%u largest=%u minimum=%u", stage,
             (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT),
             (unsigned)heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT),
             (unsigned)heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
    ESP_LOGI(TAG, "main stack minimum free: %u bytes",
             (unsigned)uxTaskGetStackHighWaterMark(NULL));
}

static void wifi_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        const wifi_event_sta_disconnected_t *event = data;
        xEventGroupClearBits(wifi_events, WIFI_READY);
        ESP_LOGW(TAG, "Wi-Fi disconnected (reason=%u); reconnecting", event->reason);
        esp_wifi_connect();
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        const ip_event_got_ip_t *event = data;
        ESP_LOGI(TAG, "Wi-Fi IP: " IPSTR, IP2STR(&event->ip_info.ip));
        xEventGroupSetBits(wifi_events, WIFI_READY);
    }
}

static esp_err_t start_wifi(void)
{
    const char *ssid = PROBE_WIFI_SSID;
    const char *password = PROBE_WIFI_PASSWORD;
    wifi_config_t config = {0};
    if (!ssid[0] || strlen(ssid) > sizeof(config.sta.ssid) ||
        strlen(password) > sizeof(config.sta.password)) {
        ESP_LOGE(TAG, "Set Wi-Fi credentials in the ignored config.h and rebuild");
        return ESP_ERR_INVALID_ARG;
    }
    memcpy(config.sta.ssid, ssid, strlen(ssid));
    memcpy(config.sta.password, password, strlen(password));
    config.sta.pmf_cfg.capable = true;
    wifi_events = xEventGroupCreate();
    if (!wifi_events) return ESP_ERR_NO_MEM;
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    if (!esp_netif_create_default_wifi_sta()) return ESP_ERR_NO_MEM;
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_event, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, wifi_event, NULL));
    // Keep the old Arduino Wi-Fi settings in NVS intact.
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &config));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));
    EventBits_t bits = xEventGroupWaitBits(wifi_events, WIFI_READY, pdFALSE, pdTRUE,
                                         pdMS_TO_TICKS(60000));
    return (bits & WIFI_READY) ? ESP_OK : ESP_ERR_TIMEOUT;
}

static bool wait_for_tailscale(void)
{
    char previous_url[512] = "";
    for (unsigned elapsed = 0; elapsed < 600; elapsed += 2) {
        char auth_url[512] = "";
        tailscale_esp32_get_auth_url(auth_url, sizeof(auth_url));
        if (auth_url[0] && strcmp(previous_url, auth_url) != 0) {
            ESP_LOGW(TAG, "Approve this device in your tailnet: %s", auth_url);
            strlcpy(previous_url, auth_url, sizeof(previous_url));
        }
        // Assigned IP alone does not prove the server is reachable; HTTP does.
        if (!auth_url[0] && tailscale_esp32_is_connected()) {
            char ip[16];
            if (tailscale_esp32_get_ip(ip, sizeof(ip)) == ESP_OK) {
                ESP_LOGI(TAG, "Tailscale IP assigned: %s", ip);
                return true;
            }
        }
        if (elapsed % 30 == 0) ESP_LOGI(TAG, "Waiting for Tailscale (%u s)", elapsed);
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
    return false;
}

static uint32_t read_le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static bool download_wav(void)
{
    char url[256];
    int url_len = snprintf(url, sizeof(url), "%s%s", PROBE_SERVER_BASE, PROBE_WAV_PATH);
    if (url_len < 0 || url_len >= sizeof(url)) return false;
    esp_http_client_config_t config = {
        .url = url,
        .timeout_ms = 15000,
        .buffer_size = 4096,
        .disable_auto_redirect = true,
    };
    esp_http_client_handle_t http = esp_http_client_init(&config);
    if (!http) return false;
    bool passed = false;
    int64_t start = esp_timer_get_time();
    ESP_LOGI(TAG, "GET %s", url);
    esp_err_t err = esp_http_client_open(http, 0);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "HTTP open failed: %s", esp_err_to_name(err));
        goto cleanup;
    }
    int64_t content_length = esp_http_client_fetch_headers(http);
    int status = esp_http_client_get_status_code(http);
    ESP_LOGI(TAG, "HTTP status=%d length=%" PRId64, status, content_length);
    if (status != 200 || content_length > MAX_WAV_BYTES) goto cleanup;

    // Stream and discard the body: no large WAV allocation or PSRAM required.
    uint8_t buffer[4096];
    uint8_t header[12];
    size_t header_size = 0;
    size_t total = 0;
    while (!esp_http_client_is_complete_data_received(http)) {
        if (esp_timer_get_time() - start > 90000000LL) {
            ESP_LOGW(TAG, "WAV transfer exceeded 90 seconds");
            goto cleanup;
        }
        int count = esp_http_client_read(http, (char *)buffer, sizeof(buffer));
        if (count < 0) goto cleanup;
        if (count == 0) {
            if (esp_http_client_is_complete_data_received(http)) break;
            ESP_LOGW(TAG, "WAV stream ended before HTTP body was complete");
            goto cleanup;
        }
        if (total + (size_t)count > MAX_WAV_BYTES) goto cleanup;
        size_t take = sizeof(header) - header_size;
        if (take > (size_t)count) take = count;
        memcpy(header + header_size, buffer, take);
        header_size += take;
        total += count;
    }
    if (header_size != sizeof(header) || memcmp(header, "RIFF", 4) != 0 ||
        memcmp(header + 8, "WAVE", 4) != 0 || (uint64_t)read_le32(header + 4) + 8 != total ||
        (content_length > 0 && (uint64_t)content_length != total)) {
        ESP_LOGW(TAG, "Not a complete RIFF/WAVE file (%u bytes)", (unsigned)total);
        goto cleanup;
    }
    int64_t elapsed = esp_timer_get_time() - start;
    ESP_LOGI(TAG, "PASS: WAV bytes=%u time_ms=%" PRId64 " rate_KiB_s=%.1f",
             (unsigned)total, elapsed / 1000,
             elapsed > 0 ? total * 1000000.0 / elapsed / 1024.0 : 0.0);
    passed = true;
cleanup:
    esp_http_client_close(http);
    esp_http_client_cleanup(http);
    return passed;
}

void app_main(void)
{
    // Give the USB console a moment to enumerate after reset.
    vTaskDelay(pdMS_TO_TICKS(2000));
    ESP_LOGI(TAG, "CoreS3 Tailscale probe / upstream c537f4b");
    log_heap("boot");
    esp_err_t err = nvs_flash_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "NVS init: %s; existing NVS was NOT erased", esp_err_to_name(err));
        return;
    }
    err = start_wifi();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Wi-Fi failed: %s", esp_err_to_name(err));
        return;
    }
    // TLS certificate validation and WireGuard timestamps need correct time.
    esp_sntp_config_t sntp = ESP_NETIF_SNTP_DEFAULT_CONFIG(PROBE_NTP_SERVER);
    ESP_ERROR_CHECK(esp_netif_sntp_init(&sntp));
    err = esp_netif_sntp_sync_wait(pdMS_TO_TICKS(30000));
    esp_netif_sntp_deinit();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "NTP failed: %s; check UDP/123 and retry after reset", esp_err_to_name(err));
        return;
    }
    tailscale_config_t ts = {
        .auth_key = PROBE_TAILSCALE_AUTH_KEY,
        .hostname = PROBE_TAILSCALE_HOSTNAME,
        .control_server = "login.tailscale.com",
    };
    err = tailscale_esp32_start(&ts);
    if (err != ESP_OK || !wait_for_tailscale()) {
        ESP_LOGE(TAG, "Tailscale start/registration failed or timed out");
        return;
    }
    log_heap("tailscale");
    // IP assignment can precede DERP / WireGuard handshake completion.
    for (unsigned attempt = 1; attempt <= 6; attempt++) {
        ESP_LOGI(TAG, "WAV attempt %u/6", attempt);
        if (download_wav()) {
            log_heap("wav-complete");
            ESP_LOGI(TAG, "Probe complete. Reset to repeat; audio playback is not enabled.");
            return;
        }
        vTaskDelay(pdMS_TO_TICKS(5000));
    }
    log_heap("wav-failed");
    ESP_LOGE(TAG, "FAIL: could not download a complete WAV through Tailscale");
}
