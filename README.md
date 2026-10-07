# fuji-xa-5: open-source remote shooting for older Fujifilm X-A cameras

Goal: let a Linux PC (and later other platforms) take pictures and show live view on the Fujifilm X-A5
without the official smartphone app, which is no longer updated. The result must be open source and
reusable for other older X-A bodies.

> **Unofficial. Use at your own risk.**
>
> - This project is not made, endorsed or supported by FUJIFILM Corporation. Fujifilm, X-A5 and Camera Remote are
>   trademarks of their owners. The names only say which camera this works with. No Fuji code, firmware or app is in
>   this repo.
> - The protocol was found by watching the camera and reading the official app. Some of the commands we send are
>   not documented by Fuji. We tested one X-A5 and nothing else. The software comes with no warranty.
> - No lasting damage was seen, but a session can leave the camera odd: the screen stays black until you press the
>   shutter once, and twice (runs 17 and 26 in the [finding](docs/findings/2026-10-05-library-first-real-run.md)) the
>   camera needed a power cycle.
> - `fuji-xa shoot` and the Shoot button of `fuji-xa serve --shoot` write pictures to the SD card.
> - Never send the operations `0x9040`, `0x9041` and `0x9042`. They are the camera's firmware update. The library
>   does not send them.

Status: **experimental, works on one X-A5.** The `fuji-xa` library and command give live view, shutter, download,
focus at a chosen point and the postview picture over Wi-Fi. It needs no Fuji software. The findings, the protocol
notes and the plans are in `docs/`. The Shoot button of `serve --shoot` is tested on a fake camera only. Movies, zoom
and the shutter speed, F-number and exposure steps are not tried.

## Quick start

Needs Python 3.10 or newer and no other package. `pip install .` installs the `fuji-xa` command, or run
`PYTHONPATH=src python3 -m fuji_xa` from a clone.

1. On the camera, open the **WIRELESS COMMUNICATION** screen. The camera's Wi-Fi network (an open one, named
   `FUJIFILM-X-A5-` and four digits) only exists while that screen is shown.
2. Join that network and run one command. [`scripts/with_camera_wifi.sh`](scripts/with_camera_wifi.sh) does both with
   NetworkManager and goes back to your own network afterwards:
   ```
   scripts/with_camera_wifi.sh -- fuji-xa serve             # live view at http://127.0.0.1:8080/ (click the picture to focus)
   scripts/with_camera_wifi.sh -- fuji-xa shoot -d pics     # takes one photo, saves it from the card to pics/
   scripts/with_camera_wifi.sh -- fuji-xa props             # read-only: what the camera reports
   ```
3. Use one command per join: the camera tends to stop its Wi-Fi when a session ends. Keep your internet on another
   connection (for example a USB tether) while the Wi-Fi card is on the camera network.
4. The camera remembers one client name (`xa5-probe`, `--name` changes it). If a new name is refused, accept the change on
   the camera.

`fuji-xa --help` lists the commands. The commands that change the camera or the card say so in their help text.

## Where things stand (2026-10-08)

- Over USB, the X-A5 currently advertises **no capture operation**, and its manual lists no USB mode
  setting. See [baseline probe](docs/findings/2026-10-04-baseline-probe.md).
- The official app controls the camera over **Wi-Fi**. The camera's access point is open, and TCP port
  55740 accepts connections. libgphoto2's experimental `Fuji X (WLAN)` driver is **rejected at the
  handshake** (Init Fail, reason `0x201d`) because it sends a random GUID. The camera accepts the fixed GUID
  that open-source tools use, and a client name. The camera seems to accept only the name it registered last (a different name was refused until the owner pressed "change" on the camera; see the [library finding](docs/findings/2026-10-05-library-first-real-run.md)). With that GUID a **PTP session opens and DeviceInfo reads
  over Wi-Fi** (our script), while libgphoto2 still fails because it sends a second init packet after the ack.
  See [session finding](docs/findings/2026-10-04-wifi-session-probe.md). See [handshake finding](docs/findings/2026-10-04-wifi-gphoto2-handshake-failure.md).
- **Remote mode and live view work.** Our `scripts/fuji_remote_probe.py` set remote mode, started open
  capture and read live-view JPEG frames (640x480, about 60 fps) from the X-A5 over Wi-Fi. The live view shows a
  real image once the lens cap is off. One `InitiateCapture` releases the shutter and the picture is saved to
  the SD card (owner confirmed twice). The camera screen is black during the session and stays black afterwards until the shutter button is pressed once (camera behaviour, see the [library finding](docs/findings/2026-10-05-library-first-real-run.md)). Download works too, and shoot plus download runs in one session (`--stage shoot --download-after`): `--stage download` fetched the picture (6 MB) in 1.2 s. See
  [remote-mode finding](docs/findings/2026-10-04-wifi-remote-mode-probe.md).
- **Focus.** A shot released from the PC seems to focus at the centre of the frame. The camera's focus point can be
  read (`fuji-xa props`, property `0xD17C`), and a write of it is accepted and ignored. The vendor operation `0x9026` starts the camera's autofocus from the PC (the lens moves,
  `0xD209` goes to 1) and `0x9027` releases it, at the camera's own point, not one we write (runs 38 to 40). The official app's code (read from its APK, [finding](docs/findings/2026-10-05-apk-analysis.md)) showed that touch focus is `0x9026` with one number: picture aspect, column, row, the same layout as `0xD17C`. We tried it and the lens focuses at the chosen cell (runs 45 and 46). To see where autofocus ran,
  read the photo's metadata (see [Useful tools](#useful-tools)). See [protocol notes](docs/protocol/wifi.md) section 6.
- **The official app's code was read** (APK from the owner's phone, jadx and `llvm-objdump`, nothing sent to the camera,
  [finding](docs/findings/2026-10-05-apk-analysis.md)). It gave the focus-point parameter, the property descriptions
  (`0x902B`), and a table of the app's vendor operations in the [protocol notes](docs/protocol/wifi.md) section 6: postview
  (`0x9022`: it returns the shot as a 640 x 480 JPEG in 0.04 s, then the download still works, runs 50 and 51; `fuji-xa shoot --postview` saves it; `fuji-xa serve --shoot` adds a Shoot button to the page that focuses at the square, takes a photo and shows the postview: fake camera only so far), zoom, the step operations for shutter speed,
  F-number and exposure bias, and movies, which are not tried yet. It also showed that `0x9040`, `0x9041` and `0x9042` are the **firmware update**
  operations: never send them ([AGENTS.md](AGENTS.md)). Our start already matches the app's version handshake.
- The protocol is written down in [docs/protocol/wifi.md](docs/protocol/wifi.md) (clean-room, with a status on
  every fact).
- The goal is **not new**: [libfuji](https://github.com/petabyt/libfuji) (MIT, C, active) and its Android app
  Fudge already implement Fuji's Wi-Fi protocol including a remote mode, tested on the X-A2 and X-H1. Nobody
  found names the X-A5. See [prior art survey](docs/findings/2026-10-04-prior-art-survey.md).
- The Ghidra analysis (plan 06) has **not run**: Ghidra and a supported JDK are not installed. The app's native code was
  read with `llvm-objdump` instead (see above). See [feasibility assessment](docs/findings/2026-10-04-feasibility-assessment.md).

## Useful tools

Every photo the camera saves records what the camera did, and `exiftool` reads it (no special scene needed). It is a
separate install (Arch: `perl-image-exiftool`, Debian and Ubuntu: `libimage-exiftool-perl`), and the `fuji-xa` library
does not need it. Seen on our own photos, details in [protocol notes](docs/protocol/wifi.md) section 6:

- `exiftool -FocusPixel -AFMode photo.JPG`: where autofocus ran, as x and y in the 6000x4000 frame (centre `3000 2000`).
- `exiftool -FocusWarning -BlurWarning -ExposureWarning photo.JPG`: the camera's own verdicts. Of 6 photos shot from the
  PC, 5 read `Out of focus` (all at `3000 2000`): their centre is a plain wall, where autofocus cannot lock. The 6th, a
  textured subject, is sharp and reads `Good` (at `2983 1983`). Use a textured subject for any focus test.
- `exiftool -ISO -ExposureTime -FNumber -FilmMode -WhiteBalance photo.JPG`: what the camera used. Use it to check the
  settings we decode from the change list (ISO was 200 to 1250 on Auto at 1/100).
- Many photos at once: `exiftool -p '$FileName $FocusPixel $FocusWarning $ISO $ExposureTime' *.JPG`.
- A full dump prints serial number tags. Name the tags you want, and never commit or paste the serial.

## Plans

Agents and contributors: read [AGENTS.md](AGENTS.md) first (rules, camera safety, git workflow). The
whole picture is in [docs/project-overview.md](docs/project-overview.md).

Read [docs/plans/00-overview.md](docs/plans/00-overview.md) first. It has the order, the decision tree
and the disk budget.

| # | Plan | Needs install | Touches camera | Status |
|---|------|---------------|----------------|--------|
| 01 | [USB mode survey](docs/plans/01-usb-mode-survey.md) | no | read-only | not started |
| 02 | [USB unknown vendor ops](docs/plans/02-usb-unknown-vendor-ops.md) | no | **sends vendor commands** | **closed**: ops are firmware file-write ops, do not probe |
| 03 | [Wi-Fi test with libgphoto2](docs/plans/03-wifi-gphoto2-test.md) | no | takes a photo | **remote mode, live view, shutter and download work** with our script; libgphoto2 still fails on a bug ([finding](docs/findings/2026-10-04-wifi-session-probe.md)) |
| 04 | [Wi-Fi traffic capture](docs/plans/04-wifi-traffic-capture.md) | `tcpdump`, `wireshark-cli` | no (app drives it) | not started |
| 05 | [APK static analysis](docs/plans/05-apk-static-analysis.md) | `jadx` | no | **done 2026-10-05** ([finding](docs/findings/2026-10-05-apk-analysis.md)) |
| 06 | [Ghidra / REA native analysis](docs/plans/06-ghidra-rea-native-analysis.md) | Ghidra + JDK 21 | no | blocked: needs approval |
| 07 | [Implementation](docs/plans/07-implementation.md) | depends | depends | waits for 03 to 06 |
| 08 | [Next camera tests](docs/plans/08-next-camera-tests.md) | no | **vendor commands, a few photos** | not started: Shoot button, step operations, who ends the session |

## Repo layout

```
README.md                      this file
AGENTS.md                      rules for agents and contributors (git workflow, camera safety)
.gitignore                     keeps captures/ and artifacts/ out of git
docs/
  project-overview.md          goal, how the camera is controlled, state, road map
  plans/                       one file per plan, plus 00-overview.md
  findings/                    dated facts and assessments, written after work is done
  protocol/                    clean-room protocol notes in our own words (filled by plans 04 to 06)
  legal-and-clean-room.md      rules for what may be committed
  references.md                upstream projects and manuals, with what each is used for
scripts/                       probe tools written for the plans (own code); `with_camera_wifi.sh` runs one command per fresh Wi-Fi join
captures/                      raw logs and pcap files, git-ignored (see captures/README.md)
artifacts/                     APKs, firmware, decompiler output, git-ignored (see artifacts/README.md)
src/fuji_xa/                   Python library and `fuji-xa` command (preview, serve, shoot, download, props, set). Fake-camera tested. All of them ran on the real camera, except that `set` was refused by the camera. `Camera.focus()` and the Focus button on the `serve` page (click or hold Space = half press, autofocus at the camera's own point, focus shows in the preview in 1 to 2 s) ran on the real camera in runs 41 to 43. The page also draws the camera's focus point as a square and lets you click the picture to focus at that cell (`Camera.focus((column, row))`): this worked on the real camera (run 46). The square is white until the camera has focused, green when it has and red when focusing failed, as the official app shows it (`0xD209`): it ran on the real camera in run 47, but green comes 1 to 2 s after the camera's beep and red was never seen. In AF-C one lock does not follow a moving subject, so the page sends the lock again every 2 s while a key or button is held (`?every=` in the address changes it, in seconds): the lens follows (runs 48 and 49, 1 s fastest, 3 s slowest), and the preview stutters while the camera focuses ([finding](docs/findings/2026-10-05-library-first-real-run.md))
tests/                         fake camera test double (`tests/fake_camera/`) and `tests/test_fake_camera.py`; pcap replay comes with plan 07
```

## Working rules

1. Read-only first. Anything that sends vendor commands to the camera, writes to its card, installs
   software or downloads a binary needs the owner's approval first. Plans mark these steps with
   **GATE**.
2. Clean-room. Never commit Fuji binaries, firmware, APKs or decompiled code. Document protocol
   behavior in our own words. See [docs/legal-and-clean-room.md](docs/legal-and-clean-room.md).
3. Record every claim with its source and version. libgphoto2 claims state whether they come from the
   installed 2.5.34 binary or from `master`.
4. Findings go in `docs/findings/` with a date. Plans describe what to do, findings describe what
   happened. Do not mix them.

5. Version control is git. Commit small, only when the owner asks, never `captures/` or `artifacts/`, and
   never run destructive git commands without asking. Details in [AGENTS.md](AGENTS.md#version-control-use-git).

## License

[MIT](LICENSE), decided 2026-10-08. It covers our code and notes. It does not cover Fuji's app, firmware, manual
or trademarks, none of which are in this repo. A libgphoto2 patch, if we send one, goes under that project's licence.
