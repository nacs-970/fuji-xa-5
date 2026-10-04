# AGENTS.md

Instructions for AI agents and human contributors working in this repo. Read [README.md](README.md) for the
status and [docs/project-overview.md](docs/project-overview.md) for the full picture before you start.

## Project in one paragraph

Open-source remote shooting for the Fujifilm X-A5 (and later other older X-A bodies) from a Linux PC,
without Fuji's discontinued smartphone app. The camera is controlled over Wi-Fi with a Fuji-specific
variant of PTP/IP. Over USB the X-A5 only supports picture download. As of 2026-10-04 our own script
opens a session, enters remote mode, reads live view, releases the shutter and downloads the picture over
Wi-Fi. The next steps are a clean client in `src/` and a libgphoto2 patch.

## Version control: use git

- This repo is under git. Commit your work to git. Do not leave finished work uncommitted.
- Commit only when the owner asks, or when the owner has told you to commit as you go. State the plan first.
- Keep commits small and about one thing: one probe script, one finding, one plan update.
- Commit message: short imperative subject (`Add remote probe live stage`), then a body that says what was
  tested on the real camera and what was only tested against the fake camera.
- Never run `git reset --hard`, `git checkout .`, `git restore .` or `git clean -fd`. Ask before any
  destructive git operation. To compare an old version, use `git show <rev>:<path>` or clone to a temp dir.
- `captures/` and `artifacts/` are git-ignored on purpose. Never force-add them. They can hold the camera
  serial number and Fuji material. Do not commit a Fuji binary, APK, firmware or decompiled code.
- Do not add a `LICENSE` file until the owner decides the license (see
  [plan 07](docs/plans/07-implementation.md)).
- Exception: `docs/artifacts/x-a5-manual/` (Fuji's X-A5 manual) is meant to be committed. The owner decided
  this. Put nothing else from Fuji in `docs/artifacts/`.
- The branch is `master`. The remote `origin` is the private GitHub repo `nacs-970/fuji-xa-5`. Push only when
  the owner asks. Do not rename the branch, make the repo public or add a tag unless asked.

## Rules for touching the camera

The camera is real hardware owned by the user. A wrong write can freeze it or change its settings.

1. Read-only first. Ask the owner before any step that changes camera state, writes to the SD card, sends
   a vendor command, installs software or downloads a binary. The plans mark these steps **GATE**.
2. Never send Fuji operations `0x900c`, `0x900d` or `0x901d`. They write firmware files
   ([finding](docs/plans/02-usb-unknown-vendor-ops.md)).
3. Taking a photo needs a fresh yes from the owner for that run. Earlier approval for live view does not
   cover it.
4. One test = one fresh Wi-Fi join: connect, run once, reconnect. Use the wrapper, not a loop:
   `scripts/with_camera_wifi.sh -- python3 scripts/<script>.py`. The camera often drops Wi-Fi after a client
   session and goes back to shooting mode.
5. The owner must reopen **WIRELESS COMMUNICATION** on the camera before each run, and may have to press OK
   on the camera. Ask for that, say what you run, and wait for "ready". Do not retry in a tight loop.
6. If the camera freezes, the fix is to remove and reinsert the battery. Tell the owner.
7. Always end a session cleanly: TerminateOpenCapture, then CloseSession (the scripts do this in `finally`).

## Layout

```
README.md, AGENTS.md           status and rules
docs/project-overview.md       what the project is, how it works, where it stands
docs/plans/                    what to do (one file per plan, 00-overview.md first)
docs/findings/                 what happened (dated, one per experiment)
docs/protocol/                 clean-room protocol notes in our own words
docs/artifacts/x-a5-manual/    owner's manual (PDF and text), published on purpose, see legal doc
docs/legal-and-clean-room.md   what may be committed
docs/references.md             upstream projects and manuals
scripts/                       probe tools: fuji_hello_probe.py, fuji_session_probe.py,
                               fuji_remote_probe.py, with_camera_wifi.sh
tests/fake_camera/             test double that speaks the protocol on 127.0.0.1
captures/, artifacts/          raw logs, manual, tools (git-ignored)
src/                           created by plan 07
```

## How to work

- Plans say what to do. Findings say what happened. Do not mix them. Date every finding (`YYYY-MM-DD-name.md`).
- Record each claim with its source and version. Say whether a libgphoto2 claim comes from the installed
  2.5.34 binary or from `master`. Say "not tested" when it is not tested.
- Clean-room: write protocol behavior in your own words. Public notes (libfuji, fuji-cam-wifi-tool,
  libgphoto2) are references, not code to paste. See [docs/legal-and-clean-room.md](docs/legal-and-clean-room.md).
- Test new probe code against the fake camera first: run `tests/fake_camera/fake_fuji_camera.py` and pass
  `--ip 127.0.0.1`. The fake camera is built from public notes, not from a recording. Passing it does not prove
  the real camera works.
- Fake-camera runs append to the real logs in `captures/wifi-gphoto2/`. Remove those lines after a test, or
  the evidence is mixed. `--dry-run` on the hello probe never writes logs.
- Scripts log to `captures/wifi-gphoto2/<date>-<name>.txt`. Do not print the camera serial number.
- Disk is tight (`/` was about 94% full). Keep large files under `/media/d` and save images under `/tmp`.

## Environment notes

- Arch Linux, NetworkManager, one Wi-Fi interface `wlp1s0`. Internet comes from a USB tether, so the Wi-Fi
  interface can join the camera network without cutting the session.
- Camera access point is open (no password), camera address `192.168.0.1`, control port TCP 55740,
  events 55741, live view 55742 (the last two open only after InitiateOpenCapture).
- gphoto2 2.5.32 and libgphoto2 2.5.34 are installed. Not installed: Ghidra, jadx, tcpdump, tshark, nc.
- Shell quirks seen in this repo:
  - `pkill -f <name>` can match your own shell command and kill it. Use `timeout` for test servers.
  - A command-output filter in this setup can shorten output (`head`, `wc`, `grep` results). Never redirect
    filtered output into a file you care about. It once wrote a `[56 more lines]` marker into a log. Write
    files from Python, or bypass the filter with `command <tool>`.
  - `mv -i` prompts and hangs. Use `command mv -f ... </dev/null`.
  - `sleep` in the foreground can be blocked. Use retry loops or the wrapper script.
