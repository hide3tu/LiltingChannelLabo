# Vendored components

Source: https://github.com/ciniml/serial_wifi_logger

Commit: `c537f4b8b64306bc2510641045160ff19fcec5d2`

Copied only `components/tailscale` and `components/wireguard`. The USB serial
logger, web UI and OTA application are not included. Files retain the upstream
copyright/license notices; WireGuard also includes `components/wireguard/LICENSE`.

Local changes:

- `tailscale_control.c`: send the previous approval URL as `Followup` on
  registration retries, and keep `registered` false while `AuthURL` is pending.
- `tailscale_esp32.c`: skip MapRequest until browser enrollment completes.
- `tailscale_netmap.c` and `tailscale_esp32.c`: implement the existing
  `TAILSCALE_DERP_ONLY` option in endpoint selection and DISCO startup.
- `Kconfig` and `tailscale_netmap.c`: add preferred DERP region selection. This
  probe selects region 7 (Tokyo), the voice server's current relay region.
- `tailscale_derp.c`: serialize read/write access to the TLS context. After the
  DERP handshake, use nonblocking I/O and retry WANT_READ/WANT_WRITE without
  holding the mutex, so an idle reader does not block ACK transmissions.

On CoreS3, the original empty-auth-key path repeatedly created new approval
URLs and requested a map before the node existed (HTTP 404). The local patch
uses the continuation field documented in Tailscale's
[`RegisterRequest`](https://github.com/tailscale/tailscale/blob/main/tailcfg/tailcfg.go).

After enrollment, the original endpoint selection timed out on the voice
server's HTTP port. It used the first advertised direct endpoint and did not
apply `TAILSCALE_DERP_ONLY`. The upstream DERP client keeps one connection and
the default netmap selection chose the smallest region ID (New York). The
relay-only probe explicitly uses the destination's Tokyo region. This is a
targeted connectivity test, not an implementation of automatic DERP selection
for arbitrary peers in different regions.

The first relay-only transfer reached HTTP 200 but crashed in
`ssl_check_ctr_renegotiate` from `derp_tx_task` with a NULL receive counter.
The probe also disables `MBEDTLS_DYNAMIC_BUFFER` so receive-buffer lifetimes
do not invalidate that counter between TLS operations. The main-task stack was
increased from 8 to 16 KiB after a separate observed stack overflow.

Publication packaging: `build.ps1` mounts this directory directly instead of
assuming the original `steps/step04_tailscale_probe` layout. The example server
address is a placeholder. The credential-import helper, device credentials,
serial logs, firmware backup, and build outputs are not included. Application
and vendored component sources are unchanged from the tested final firmware.
