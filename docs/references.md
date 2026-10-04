# References

What each source is used for. Add a line when a new source influences a decision or a protocol note.
Retrieval dates are 2026-10-04 unless noted.

## Code

| Source | Used for | Notes |
|--------|----------|-------|
| [libgphoto2](https://github.com/gphoto/libgphoto2) `camlibs/ptp2/` | Existing Fuji USB and Wi-Fi support: `library.c` (camera table, Fuji init), `ptp.h` (opcodes, properties), `fujiptpip.c` (Wi-Fi) | LGPL-2.1-or-later. Source read: `master` (head `e4108a5` on 2026-10-03). Installed binary: 2.5.34. |
| [hkr/fuji-cam-wifi-tool](https://github.com/hkr/fuji-cam-wifi-tool) | Independent implementation of Fuji Wi-Fi remote control (ports 55740 to 55742: command, async events, JPEG stream) | Unlicense per its repository. Experimental, described as limited and mostly undocumented. X-T10 mentioned. Its init packet layout and one GUID constant were compared in the [handshake finding](findings/2026-10-04-wifi-gphoto2-handshake-failure.md); the GUID is used as a test value in `scripts/fuji_hello_probe.py`. |
| [grw1983/fuji-cam-wifi-tool](https://github.com/grw1983/fuji-cam-wifi-tool) | A repository titled "Trying to reverse-engineer the Fuji X-T10 wifi remote control protocol" | Relationship to the tool above not checked. Not read in detail. |
| [petabyt/libfuji](https://github.com/petabyt/libfuji) | Closest prior art: Fuji Wi-Fi, USB and Bluetooth library with a remote mode. Handshake, retries, `docs/dev.md` protocol notes, USB opcode notes. | MIT. Read 2026-10-04 (`lib/fuji.c`, `lib/fujiptp.h`, docs). |
| [petabyt/fudge](https://github.com/petabyt/fudge) and the [writeup](https://danielc.dev/blog/fudge1/) | Android app on libfuji. The writeup says the author tested the X-A2 and X-H1 and describes older versus newer setup. | License not declared in the GitHub API. |
| [Th0rgal/fuji-bridge](https://github.com/Th0rgal/fuji-bridge) | Handshake retry timing, 50 ms before `OpenSession`, OK-prompt polling (`docs/DEVELOPMENT.md`, summarized by a web tool). | MIT. |
| [mikefsq/ptp `fuji`](https://pkg.go.dev/github.com/mikefsq/ptp/fuji) | Go package for Fuji X-T5 over USB. Names `0x9026` "Set focus point" and `0x9027` "Reset focus point" (names only, no layouts found). Focus mode values `0x0001` manual, `0x8001` AF-S, `0x8002` AF-C. Its capture sequence half-presses (S1) first, polls `0xD209` (1 busy, 2 ok, 3 failed) and must release S1 on every failure path | Read 2026-10-05 through its docs and `capture.go`, nothing copied |
| [OpenXWebcam PR 2](https://github.com/antonyshyn/OpenXWebcam/pull/2) | X-T3 over USB: autofocus is `0xD208` = `0x9300`, then `InitiateCapture`, poll `0xD209` until it leaves "focusing", then release by writing `0x0005` to `0xD208`. Leaving S1 held stops the camera focusing again | Read 2026-10-05 (page text), nothing copied |
| [malc0mn/ptp-ip](https://github.com/malc0mn/ptp-ip) | Go PTP/IP implementation with a working Fuji X-T1 path. Not read. | not checked |
| [Fujihack](https://fujihack.org/) | Lead only: reverse-engineering of Fuji cameras, including work mentioned for the X-A2 | Not reviewed. Check its license before using anything from it. |

## Discussions

| Source | Used for |
|--------|----------|
| [libgphoto2 issue 517](https://github.com/gphoto/libgphoto2/issues/517) | Notes that the Fuji Wi-Fi protocol is a significant fork of PTP/IP and that init fails with `Unsure on type` and `got reply type` errors on X-T series. Does not mention X-A series. |

## Fujifilm documentation and apps

| Source | Used for |
|--------|----------|
| [X-A5 owner's manual, wireless connections](https://fujifilm-dsc.com/en/manual/x-a5/connections/wireless/index.html) | Camera Remote app controls the camera over Bluetooth or Wi-Fi. PC AutoSave is a wireless-LAN upload feature (the full manual confirms this). That wireless-connections page does not mention tethered shooting or live view over USB. |
| [X-A5 owner's manual (PDF)](https://fujifilm-dsc.com/en/manual/x-a5/x-a5_omw_en_s_f.pdf) | Menu names for the USB and Wi-Fi modes (to be read in plan 01 and plan 03) |
| [Fuji Rumors on the Camera Remote app and XApp](https://www.fujirumors.com/fujifilm-says-major-x-app-update-is-coming-includes-compatibility-for-older-fujifilm-cameras-camera-remote-app-is-dead/) | The Camera Remote app gets no more updates. Fuji recommends XApp. |
| [FUJIFILM Camera Remote on Google Play](https://play.google.com/store/apps/details?id=com.fujifilm_dsc.app.remoteshooter) | Package name `com.fujifilm_dsc.app.remoteshooter` |
| [Remote Release](https://app.fujifilm-dsc.com/en/manual/camera_remote/usage/remote_release/) | Remote Release releases the shutter from a phone and requires a Bluetooth connection. It is listed separately from Live View Shooting. The page says the X-A5, X-T100 and FinePix XP130 do not support Remote Release. |
| [Tethered Shooting](https://app.fujifilm-dsc.com/en/tether/) | Fuji's current tether app. The X-A5's inclusion was not confirmed. |
