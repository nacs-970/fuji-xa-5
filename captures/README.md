# captures/

Raw evidence from the camera: `gphoto2` debug logs, USB logs, pcap files. Everything here except this
file is git-ignored.

Why ignored: captures contain the camera serial number, MAC address, SSID and the PC host name.
Sanitize before anything is shared or used as a test fixture (see `docs/plans/07-implementation.md`).

## Layout

```
captures/
  baseline/        first probe of the camera over USB (done)
  usb-survey/      one log per camera USB mode          (plan 01)
  usb-vendor-ops/  results of vendor opcode probes      (plan 02)
  wifi-gphoto2/    gphoto2 over Wi-Fi test logs         (plan 03)
  wifi-pcap/       official app <-> camera pcap files   (plan 04)
```

Naming: `YYYY-MM-DD-<what>.<ext>`, for example `2026-10-04-gphoto2-summary.debug.log`.
Put the camera menu mode or app action in the file name or in a sidecar `.md` note next to it.
