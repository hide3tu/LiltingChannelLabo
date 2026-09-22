# CoreS3 probe: 2026-09-23 JST

## Build and flash

- Board: CoreS3 / ESP32-S3 revision 0.2, 16 MiB flash, USB Serial/JTAG (COM3).
- Build: `espressif/idf:v6.0`, ESP-IDF 6.0, target `esp32s3`.
- Image digest: `sha256:59df146f64aa0b13886a13a74682ad157482b446f5cc16582500803c95c71401`.
- Initial app: 956,176 bytes. Enrollment-fix app: 956,256 bytes.
- Final app with Tokyo DERP and TLS fixes: 951,824 bytes.
- Final app SHA-256: `3974D0074E97B51B293B0A4748C8166D677F5DE49CCF814E5C0ED5424A329928`.
- Factory partition: 3 MiB. Flash writes verified by esptool 5.3.0.
- Wi-Fi association, DHCP, NTP, TLS validation and Tailscale control handshake succeeded.
- Browser enrollment completed. NVS keys survived reflashing and restarting.
- Final firmware downloaded the complete WAV on two separate boots.

## Existing firmware backup

Before the first write, saved all 16,777,216 bytes with per-block and whole-flash
MD5 verification. ROM backup took 478.6 seconds.

- File: `../../.tailscale-work/cores3-before-tailscale-20260923-verified.bin`
- SHA-256: `E730F729CA4582EE27468EC679FE78C1328DA14C5154AE51CD92FE89715C8DC8`
- Normal esptool stub reading stopped after 4 KiB in this environment; root cause
  is undetermined. `backup_rom.py` with esptool 5.3.0 and `--no-stub` succeeded.

The backup includes device settings and is deliberately excluded from Git.

## PC baseline (not CoreS3 throughput)

- Same voice server, TCP 8357, `/filler/filler_0.wav`.
- HTTP 200; 433,964 bytes; 0.153943 seconds (one download).
- WAV: 48 kHz, 16-bit mono; 216,960 frames / 4.52 seconds.

## Runtime changes

- The upstream empty-auth-key path repeated registration and received HTTP 404
  (`node not found`) while the browser approval was still pending.
- Added the Tailscale `Followup` field and deferred MapRequest until enrollment.
  The patched device keeps waiting on the same approval URL.
- Windows CP932 output could not print an upstream em dash. `monitor.py` now
  sets UTF-8 stdout; the saved log was already UTF-8.

Local logs: `serial-probe.log`, `serial-enrollment.log` (excluded from Git because
they contain enrollment URLs). Neither speaker playback nor STT/TTS inference
has been tested by this probe.

## Device WAV result (final firmware)

| Item | First boot | Reboot with stored keys |
|---|---:|---:|
| HTTP status | 200 | 200 |
| Bytes received and validated | 433,964 | 433,964 |
| Successful request duration | 9,025 ms | 8,816 ms |
| Transfer rate | 47.0 KiB/s | 48.1 KiB/s |
| Internal free heap after transfer | 89,780 B | 89,784 B |
| Internal minimum free heap | 70,108 B | 69,576 B |
| Main stack minimum free | 8,604 B | 8,604 B |

Both boots used attempt 2 of 6 after the first TCP connection timed out. The
durations above exclude boot, enrollment and that failed attempt. Both logs
finished with `Probe complete`; neither final-firmware run crashed.

Path: CoreS3 -> Tokyo DERP (`derp7h.tailscale.com`, region 7) -> voice server.
No VPS PHP relay; direct UDP is not validated. Logs: `serial-final.log` and
`serial-repeat.log`, both excluded from Git.

Earlier attempts exposed an 8 KiB main stack overflow and a NULL receive-counter
dereference in the TLS writer. The final configuration uses a 16 KiB main stack,
persistent TLS buffers, and serialized nonblocking DERP TLS reads/writes.
The intermediate relay-only firmware crashed twice before a successful download;
that run is not counted in the final-firmware results above.
