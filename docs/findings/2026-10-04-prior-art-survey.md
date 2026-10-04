# Prior art survey: projects with the same or a similar goal (2026-10-04)

Method: web searches, then reading the README, docs and source of the most relevant projects. Source files
were read in a scratch directory, not copied into this repo. "Seen" means seen in public material, not
tested on the X-A5. Star counts and push dates come from the GitHub API on 2026-10-04.

## Summary

The goal is **not new**. One active project already implements the Fuji Wi-Fi protocol including a
"remote mode" and documents it, and its author tested older cameras (X-A2). Nobody found mentions the
**X-A5** by name. The most valuable work for this repo is therefore to verify and fix the X-A5 on top of
existing code, and to document what is X-A5 specific, instead of building a protocol stack from zero.

## Projects

| Project | What it is | License | Language | Activity | Relevance |
|---------|------------|---------|----------|----------|-----------|
| [petabyt/libfuji](https://github.com/petabyt/libfuji) | Library for Fujifilm cameras over Wi-Fi, USB and Bluetooth: wireless communication mode, PC AutoSave, tether shooting, raw conversion. Documents the protocols in `docs/dev.md`. Used by Fudge. | MIT | C | pushed 2026-10-02 | **Highest.** Closest to the goal. Contains the handshake, the remote-mode setup and the live-view socket. |
| [petabyt/fudge](https://github.com/petabyt/fudge) | Android app, an alternative to Fujifilm's Camera Remote app. | none declared in the GitHub API | Kotlin and C | pushed 2026-10-03 | **High.** Same author as libfuji. A third-party page (DPReview thread) said live view and remote shutter were still on the roadmap. Not re-checked. |
| [Fudge writeup](https://danielc.dev/blog/fudge1/) | The author's explanation of Fuji's Wi-Fi protocol. States the author tested two cameras, **X-A2** and X-H1. | n/a | n/a | n/a | **High.** Describes separate setup sequences for older and newer bodies. |
| [Th0rgal/fuji-bridge](https://github.com/Th0rgal/fuji-bridge) | Photo import for Fujifilm cameras on iPhone, iPad and Mac over USB, Wi-Fi and Bluetooth wake. Has `docs/DEVELOPMENT.md` with protocol notes and camera quirks. | MIT | Swift | active (39 commits) | Medium. Import only, but its notes cover handshake retries and timing. Main camera is the X100VI. |
| [hkr/fuji-cam-wifi-tool](https://github.com/hkr/fuji-cam-wifi-tool) | Interactive tool: shutter, live view (v4l2loopback webcam), ISO, aperture, white balance, shutter speed. Forks exist ([edmc2](https://github.com/edmc2/fuji-cam-wifi-tool), [grw1983](https://github.com/grw1983/fuji-cam-wifi-tool)). | Unlicense | C++ | older, experimental | Medium. First public reverse engineering, on the X-T10. |
| [gphoto/libgphoto2](https://github.com/gphoto/libgphoto2) | `Fuji X (WLAN)` driver, marked EXPERIMENTAL, flagged for capture and preview. Issue [517](https://github.com/gphoto/libgphoto2/issues/517) tracks X-T series Wi-Fi. | LGPL-2.1-or-later | C | active | **High as a target.** The place where a fix reaches the most users. |
| [malc0mn/ptp-ip](https://github.com/malc0mn/ptp-ip) | Go PTP and PTP/IP implementation with a working PTP/IP path for the Fuji X-T1. | not checked | Go | not checked | Low to medium. Another independent reference. |
| [fujihack/fujihack](https://github.com/fujihack/fujihack) | Reverse engineering of Fujifilm camera firmware. | not checked | various | active | Low for this goal, and risky. Not needed for remote shooting. |
| Closed commercial apps: CamRanger 2, Cascable, Shutter+ | Remote control apps for Fujifilm cameras | proprietary | n/a | n/a | Show demand. X-A5 support in them was not checked. |
| [gkoh/furble](https://github.com/gkoh/furble) | Bluetooth camera remote (credited by libfuji) | MIT | C++ | not checked | Not usable here: Fuji says the X-A5 does not support the Bluetooth Remote Release feature. This is an inference from that statement, not a test. |

## Protocol facts from public sources

Mark: **source** means read in public code or docs. None of these is tested on the X-A5 yet, except where
the repo's own logs say so.

1. **Init packet.** 82 bytes: length, type 1, version `0x8f53e4f2`, a 16-byte GUID, the client name in
   UTF-16. libfuji, the hkr tool and fuji-bridge use the **same fixed GUID prefix** (first 12 bytes
   `ada5485d87b27f0bd3d5ded0`). The fuji-bridge notes say the official XApp sends the same version and
   GUID. **Source.** This is consistent with what the X-A5 accepted in the repo's probe (variant B).
2. **After the ack**, Fuji uses USB-style PTP containers over TCP, then `OpenSession`. libfuji waits at
   least 50 ms before `OpenSession` and starts the transaction id at 1, not 0, on every new socket.
   **Source** (libfuji source comments, fuji-bridge notes).
3. **Init Fail is expected and retried.** fuji-bridge notes: resend the init after Init Fail, including on a
   reconnect, up to four times at 0, 1, 2 and 4 seconds. libfuji retries its handshake. **Source.**
   libgphoto2 instead resends on the same socket, and the X-A5 closed it (see the repo's handshake
   finding).
4. **Older cameras need a button press on the camera.** After the ack the camera shows the client name and
   waits for the user to press OK. libfuji prints "Make sure you pressed OK". fuji-bridge polls property
   `0xD212` until `0xDF00` leaves "press OK". The libfuji user docs add that on older cameras the first
   connection needs **(OK) CHANGE** pressed, otherwise the camera rejects new clients. **Source.**
5. **Remote mode.** libfuji sets property `0xDF01` ("ClientState") to 5 (remote mode), then connects the
   event socket (55741) and the video socket (55742). **Source.** Older cameras differ from newer ones in
   this sequence per the Fudge writeup.
6. **USB opcodes `0x900c`, `0x900d`, `0x901d`.** libfuji's docs say these are custom Fuji opcodes found in
   Fuji's firmware update utility: create a file and write to a file, able to upload `AUTO_ACT.SCR` and
   `FPUPDATE.DAT` to the SD card, which normal PTP cannot do. The same docs say every Fujifilm camera since
   2011 implements `0x1001`-`0x100B`, `0x100F`, `0x1014`-`0x1016`, `0x101B`. **Source.** Matches the X-A5
   baseline exactly.
7. **USB tether needs a camera mode the X-A5 manual does not list.** libfuji describes USB tether shooting
   and a USB transport mode menu on cameras that have them. The X-A5 manual lists no USB mode setting.
   **Source plus the repo's manual extraction.**
8. **A freeze risk on old bodies.** libfuji marks X-A2, X-A1, X-T1, X-T10, X-E2, X-E2S, X-M1, X100T, X70,
   X30, XQ1 and XQ2 as bodies that can shut down or freeze when connecting to some modern phones, citing a
   Fujifilm notice. The X-A5 is not on that list. **Source.** If the camera freezes during tests, remove
   and reinsert the battery.

## What changes for this project

- **Plan 02 is closed.** The three unknown USB opcodes write files to the SD card for firmware updates.
  Probing them has no benefit for remote shooting and real risk to the camera. See the note in plan 02.
- **Plans 04 and 05 are less urgent.** The protocol is already documented in permissively licensed source.
  Capturing the official app stays useful to confirm X-A5 specific behavior.
- **New first-line hypotheses for the X-A5 handshake failure**: (H5) the first init after joining the Wi-Fi
  is expected to fail and a retry on a **new connection** succeeds, and (H6) the camera is waiting for the
  user to press OK. Both are tested by `scripts/fuji_hello_probe.py --seq`. See the handshake finding.
- **Likely best deliverables**, in order: (1) test the X-A5 against libfuji and report results upstream;
  (2) fix libgphoto2's Fuji Wi-Fi handshake (reconnect and retry, fixed GUID) so every gphoto2 front end
  works; (3) document X-A5 specifics in `docs/protocol/`. See plan 07.

## Gaps

- No source found that names the X-A5 for Wi-Fi remote control.
- libfuji's live-view and remote-shutter completeness was not tested or read beyond the connect flow.
- Fudge's license is undeclared in the GitHub API. Check before reusing any Fudge code. libfuji (MIT) is
  clear.
- `docs/DEVELOPMENT.md` of fuji-bridge was summarized by a web tool, not read in full.
