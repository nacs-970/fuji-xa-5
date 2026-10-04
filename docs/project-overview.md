# Project overview

## Goal

Control a Fujifilm X-A5 from a Linux PC: live view, shutter release and later camera settings, without the
official Camera Remote smartphone app, which Fuji no longer updates. The result must be open source and
usable on other older X-A bodies (X-A1, X-A2, X-A3, X-A10 and similar) that the app also supported.

## Why it is not a USB project

The X-A5 manual lists no USB mode setting. USB is for downloading pictures only, and over USB the camera
advertises no capture operation (see the [baseline probe](findings/2026-10-04-baseline-probe.md)). Remote
control runs over the camera's own Wi-Fi network.

## How the camera is controlled

Summary of what we verified on a real X-A5 (firmware 1.21). Details are in the findings.

1. The camera broadcasts an open Wi-Fi network (name starts with `FUJIFILM-`) when the user opens
   WIRELESS COMMUNICATION. It is the DHCP server at `192.168.0.1`.
2. Control uses TCP port 55740 with a Fuji variant of PTP/IP. The client sends an 82-byte init packet with a
   16-byte GUID and a client name. The camera accepts only GUIDs that start with the 12-byte prefix used by
   existing open-source tools. Random GUIDs get Init Fail `0x201d`. The camera seems to accept only the client name it registered last, until the user presses "change" on it.
3. After the ack the socket carries USB-style PTP containers. OpenSession works at once.
4. The client reads the Fuji event property `0xD212`, sets client state `0xDF01` to 5 (remote mode) and the
   remote version `0xDF24` to `0x2000C`, then calls InitiateOpenCapture `0x101C`.
5. The camera opens TCP 55741 (events) and 55742 (live view). Live view is a stream of 640x480 JPEG frames
   at about 60 fps, each with an 18-byte header.
6. The client ends with TerminateOpenCapture `0x1018` and CloseSession.

The camera may show the client name and ask the user to press OK on its screen. It leaves the wireless
screen after a client session, so each test needs a fresh join.

The protocol is documented in [protocol/wifi.md](protocol/wifi.md).

## Where things stand (2026-10-04)

| Area | State |
|------|-------|
| Handshake with a fixed GUID prefix | works ([finding](findings/2026-10-04-wifi-session-probe.md)) |
| Session, DeviceInfo over Wi-Fi | works |
| Remote mode, open capture, live view | works ([finding](findings/2026-10-04-wifi-remote-mode-probe.md)) |
| Shutter release | works: one `InitiateCapture` (`0x100E`, 0, 0) with live view open. The picture is saved to the SD card, confirmed by the owner ([finding](findings/2026-10-04-wifi-remote-mode-probe.md)) |
| Shoot and download in one session | works (`--stage shoot --download-after`, 9 s, newest picture is handle 1) |
| Image download | works: `--stage download` fetched a 6 MB JPEG in 1.2 s ([finding](findings/2026-10-04-wifi-remote-mode-probe.md)). Handle 1 is the newest picture |
| libgphoto2 `Fuji X (WLAN)` driver | fails: random GUID, and a second init after the ack |
| Settings (ISO, aperture, film simulation) | not started |
| Native analysis with Ghidra/REA | not run, tools not installed ([plan 06](plans/06-ghidra-rea-native-analysis.md)) |

The goal is not new. [libfuji](https://github.com/petabyt/libfuji) and its app Fudge already cover this
protocol on other bodies. Nobody found names the X-A5. Our contribution is X-A5 evidence, a small clean
client and a path into libgphoto2. See the [prior art survey](findings/2026-10-04-prior-art-survey.md).

## Repo map

| Path | Purpose |
|------|---------|
| `AGENTS.md` | rules for agents and contributors, including git workflow and camera safety |
| `docs/plans/` | numbered plans, `00-overview.md` has the order and the decision tree |
| `docs/findings/` | dated experiment reports |
| `scripts/` | probe tools and the Wi-Fi wrapper |
| `tests/fake_camera/` | fake camera used to test scripts without hardware |
| `captures/`, `artifacts/` | raw evidence and downloaded tools, git-ignored |
| `src/fuji_xa/` | Python library and `fuji-xa` command (plan 07). `preview`, `shoot` and `download` ran on the real camera |

## Version control

The repo uses git. Rules are in [AGENTS.md](../AGENTS.md#version-control-use-git):

- small commits, one subject each;
- commit only on the owner's request;
- never commit `captures/`, `artifacts/`, Fuji binaries, firmware or decompiled code;
- no destructive git commands without asking;
- the branch is `master`. It is pushed to the private GitHub repo `nacs-970/fuji-xa-5` (`origin`), and
  pushes happen only on the owner's request.

## Road map

1. **Shutter**: done (`shoot` stage of `fuji_remote_probe.py`). Still open: does the camera focus before the
   shot, and why does its screen go black afterwards?
2. **Image transfer**: done for one picture. Still open: why the camera hides the third (black) picture (handle 3 answers `0x2007`), thumbnail and list views.
3. **libgphoto2 patch**: fixed GUID prefix and no second init after the ack. Test with
   `gphoto2 --camera "Fuji X (WLAN)" --port ptpip:192.168.0.1 --capture-preview`. Offer it upstream
   (issue 517).
4. **Standalone client** in `src/` (language and license still to decide, see
   [plan 07](plans/07-implementation.md)) with a pcap-replay test suite.
5. **Other X-A bodies**: publish the test procedure so owners of X-A1, X-A2, X-A3 and X-A10 can report results.

## Open decisions

- License: depends on whether the code goes upstream into libgphoto2 (LGPL-2.1-or-later) or ships alone.
- Client language: Python for probes now, something packaged for `src/` later.
- Branch name (`master` or `main`) and when to make the GitHub repo public: not decided. The repo is private
  for now.
