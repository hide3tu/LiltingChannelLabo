idf_component_register(
    SRCS "probe.c"
    INCLUDE_DIRS ".."
    PRIV_REQUIRES esp_wifi esp_event esp_netif esp_http_client esp_timer
                  nvs_flash tailscale
)
