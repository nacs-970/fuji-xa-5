# fuji-xa-5: open-source remote shooting for older Fujifilm X-A cameras

Goal: let a Linux PC (and later other platforms) take pictures and show live view on the Fujifilm X-A5
without the official smartphone app, which is no longer updated. The result must be open source and
reusable for other older X-A bodies.

Status: **research phase.** No implementation code exists yet. This repo holds the findings, the plans and
the evidence layout.

## Where things stand (2026-10-04)

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
- The protocol is written down in [docs/protocol/wifi.md](docs/protocol/wifi.md) (clean-room, with a status on
  every fact).
- The goal is **not new**: [libfuji](https://github.com/petabyt/libfuji) (MIT, C, active) and its Android app
  Fudge already implement Fuji's Wi-Fi protocol including a remote mode, tested on the X-A2 and X-H1. Nobody
  found names the X-A5. See [prior art survey](docs/findings/2026-10-04-prior-art-survey.md).
- The REA/Ghidra native analysis has **not run**: Ghidra and a supported JDK are not installed.
  See [feasibility assessment](docs/findings/2026-10-04-feasibility-assessment.md).

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
| 05 | [APK static analysis](docs/plans/05-apk-static-analysis.md) | `jadx` | no | not started |
| 06 | [Ghidra / REA native analysis](docs/plans/06-ghidra-rea-native-analysis.md) | Ghidra + JDK 21 | no | blocked: needs approval |
| 07 | [Implementation](docs/plans/07-implementation.md) | depends | depends | waits for 03 to 06 |

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
src/fuji_xa/                   Python library and `fuji-xa` command (preview, serve, shoot, download, props, set). Fake-camera tested. All of them ran on the real camera, except that `set` was refused by the camera ([finding](docs/findings/2026-10-05-library-first-real-run.md))
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

Not chosen yet. This is an open decision in [plan 07](docs/plans/07-implementation.md). Do not add a
`LICENSE` file until it is decided, because the choice depends on whether the code goes upstream into
libgphoto2 (LGPL-2.1-or-later) or ships as a standalone project.
