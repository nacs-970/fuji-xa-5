# Feasibility assessment: remote shooting on the X-A5 (2026-10-04)

Facts behind this assessment are in [the baseline probe](2026-10-04-baseline-probe.md).
Status of each claim is marked **verified** (observed on this camera), **source** (read in code or
documentation) or **open** (not tested).

## Question

Can an open-source tool give the X-A5 remote shooting, given that the official Camera Remote app does it
but is no longer updated?

## USB

- **Verified:** in the mode the camera was in, it advertises no capture operation (`0x100e`, `0x101c`)
  and no Fuji tether operation (`0x902b` and the `0x902x` family). Storage is read-only except delete.
- **Consequence:** adding `PTP_CAP` to the X-A5 entry in libgphoto2 would not give capture in this mode.
  The camera would reject the request.
- **Open:** Fuji cameras can expose different operation sets depending on the USB or connection mode in
  the camera menu. Only one mode was probed, and its label was not recorded. USB cannot be called a dead
  end until every mode has been surveyed (plan 01).
- **Open:** `0x900c`, `0x900d`, `0x901d` are vendor operations that libgphoto2 does not name for Fuji.
  The X-A5 manual describes USB only as a way to download pictures (MyFinePix Studio on Windows, Image
  Capture on macOS), and PC AutoSave as a wireless-LAN feature. So these operations may belong to the
  picture-download software, or to nothing the manual documents. Identifying them means sending vendor
  commands (plan 02, needs approval).
- **Source (full manual text, `docs/artifacts/x-a5-manual/`):** the manual's USB chapter lists no USB-mode
  menu item and no tether or live-view use. That makes extra USB modes less likely than assumed when
  plan 01 was written.

## Wi-Fi

- **Source:** the X-A5 manual says the Camera Remote app can control the camera over Bluetooth or Wi-Fi
  (see `references.md`). So the camera implements a remote-control protocol over Wi-Fi.
- **Source:** the installed libgphoto2 2.5.34 contains an experimental `Fuji X (WLAN)` driver with
  capture and live-preview flags. It speaks a Fuji-specific fork of PTP/IP on ports 55740, 55741, 55742.
- **Source:** an independent project, `hkr/fuji-cam-wifi-tool`, controls the X-T10 over Wi-Fi with the
  same three ports (shutter, live view, settings).
- **Open:** whether the X-A5 uses the same protocol variant as the X-T10 or X-T series. Nobody in the
  sources found so far mentions the X-A5 on Wi-Fi. This is the first thing to test (plan 03).
- **Source:** Fuji's page for the app's "Remote Release" feature says it needs a Bluetooth connection, is
  listed separately from Live View Shooting, and is not supported on the X-A5. So that exclusion is about
  the Bluetooth shutter release, not about Wi-Fi remote shooting with live view (see `references.md`).
  Whether the X-A5 supports Live View Shooting in the app is not stated on that page. The X-A5 manual's
  wireless page says the app can control the camera remotely.

## Official app status

Fuji says the Camera Remote app no longer gets updates and recommends XApp. Whether XApp supports the
X-A5 was not confirmed. This matters only as a source of captures (plan 04): the older app is the one
known to work with the X-A5.

## REA analysis status: not done

The request was to analyze with the REA MCP. It could not run. REA's deep providers (Ghidra 12.1.4 or
Hopper) are not installed or configured, and the default Java 27 is rejected by Ghidra.

`ptp2.so` was also the wrong first target, because its source is open and was read directly. Better REA
targets, in order of value:

1. The Camera Remote APK, only if the protocol code is native (`.so`) rather than Java or Kotlin.
2. The X-A5 firmware, only if the USB question stays open after plans 01 and 02.

See plan 06 for setup cost and approval gates.

## Verdict

- Likelihood that open-source remote shooting is achievable: **plausible, not established.** The Wi-Fi
  path has a working official implementation, existing partial open-source code and a known set of
  ports. The USB path looks closed in the one mode probed.
- Cheapest decisive experiment: plan 03 (about 15 minutes, no installs).
- If plan 03 fails: plans 04 and 05 give a protocol description from the official app's own traffic and
  code, within about 250 MB of disk.

## Disk and effort envelope

| Route | Extra disk (installed) | Source of the number |
|-------|------------------------|----------------------|
| Plans 01 to 03 | none | no installs |
| Plan 04 (`tcpdump` + `wireshark-cli`) | about 101 MiB | pacman database |
| Plan 05 (`jadx`) | about 75 MiB, plus APK and output | pacman database, APK size is an estimate |
| Plan 06 (Ghidra + JDK 21) | about 1.25 GiB, peak about 2 GiB while downloading | pacman database |

`/` has 2.9 GB free. Plans 01 to 05 fit in hundreds of MB. Plan 06 does not fit comfortably on `/`.
