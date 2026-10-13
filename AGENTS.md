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
- The code is MIT (`LICENSE`, decided 2026-10-08). Do not copy code from a project whose licence does not allow it.
- Fuji's X-A5 manual is not committed (owner decision, 2026-10-08). A local copy lives in the git-ignored
  `artifacts/x-a5-manual/`. Cite the official PDF in `docs/references.md` instead. Put nothing else from Fuji in
  the tracked tree.
- The branch is `master`. The remote `origin` is the public GitHub repo `nacs-970/fuji-xa-5` (public since
  2026-10-14). Push only when the owner asks. Do not rename the branch, change the repo's visibility or add a tag
  unless asked. Everything pushed is public: check a change for serial numbers, MAC addresses and Fuji material first.

## Rules for touching the camera

The camera is real hardware owned by the user. A wrong write can freeze it or change its settings.

1. Read-only first. Ask the owner before any step that changes camera state, writes to the SD card, sends
   a vendor command, installs software or downloads a binary. The plans mark these steps **GATE**.
2. Never send Fuji operations `0x900c`, `0x900d` or `0x901d` (USB), or `0x9040`, `0x9041` or `0x9042` (Wi-Fi). They
   write firmware files ([USB finding](docs/plans/02-usb-unknown-vendor-ops.md), [Wi-Fi finding](docs/findings/2026-10-05-apk-analysis.md)).
   Never write `0xDF01` = 19 (firmware transfer mode) and never send `0x100B` (DeleteObject).
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
docs/legal-and-clean-room.md   what may be committed
docs/references.md             upstream projects and manuals
scripts/                       probe tools: fuji_hello_probe.py, fuji_session_probe.py,
                               fuji_remote_probe.py, with_camera_wifi.sh
tests/fake_camera/             test double that speaks the protocol on 127.0.0.1
captures/, artifacts/          raw logs, manual, tools (git-ignored)
src/fuji_xa/                   Python library and `fuji-xa` command (run with PYTHONPATH=src, no install)
tests/test_fake_camera.py      library test against the fake camera: python3 tests/test_fake_camera.py
pyproject.toml, LICENSE        package metadata, MIT licence
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

## Useful tools

A photo from the camera records what the camera did, so read it with `exiftool` after a shot instead of judging the
picture by eye. `exiftool` is not part of this repo and not every machine has it: run `command -v exiftool` first. If it
prints nothing, tell the user and ask them to install it (Arch: `perl-image-exiftool`, Debian and Ubuntu:
`libimage-exiftool-perl`). Do not install it yourself. On the owner's machine it is `/usr/bin/vendor_perl/exiftool`.
Details and caveats: [wifi.md](docs/protocol/wifi.md) section 6.

- Where autofocus ran: `exiftool -FocusPixel -AFMode photo.JPG`. x and y in the 6000x4000 frame, centre `3000 2000`.
- The camera's own verdicts: `exiftool -FocusWarning -BlurWarning -ExposureWarning photo.JPG`. Of 6 photos shot from the
  PC, 5 read `Out of focus` (all at `3000 2000`): their centre is a plain wall, where autofocus cannot lock. The 6th, a
  textured subject, is sharp and reads `Good` (at `2983 1983`). Use a textured subject at the centre for any focus test.
- What the camera used: `exiftool -ISO -ExposureTime -FNumber -FilmMode -WhiteBalance photo.JPG`. Compare it with the
  settings decoded from the change list (`0xD02A`, `0xD240`, `0x5007`, `0xD001`, `0x5005`). ISO was 200 to 1250 on Auto
  at 1/100, which may help decode the `0xD02A` top bit.
- Many photos at once: `exiftool -p '$FileName $FocusPixel $FocusWarning $ISO $ExposureTime' *.JPG`.
- Never print the serial number. A full dump (`-FujiFilm:all`, `-a -G1 -s`) includes serial tags: name the tags you want.
- Idea, not tested: `GetPartialObject` (`0x101B`) may fetch only the start of a picture, enough for these tags, instead
  of a 6 MB download.

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
