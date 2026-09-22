#pragma once

#define PROBE_WIFI_SSID ""
#define PROBE_WIFI_PASSWORD ""

// Empty = print the Tailscale device approval URL on the serial console.
#define PROBE_TAILSCALE_AUTH_KEY ""
#define PROBE_TAILSCALE_HOSTNAME "m5cores3-probe"

// Direct server address. No VPS / voice-relay.php in this test.
#define PROBE_SERVER_BASE "http://100.64.0.1:8357" // Replace with your server's Tailscale IPv4.
#define PROBE_WAV_PATH "/filler/filler_0.wav"
#define PROBE_NTP_SERVER "ntp.nict.jp"
