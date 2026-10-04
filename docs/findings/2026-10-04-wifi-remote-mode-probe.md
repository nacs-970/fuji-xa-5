# Wi-Fi remote mode and live view on the X-A5 (2026-10-04)

Camera: Fujifilm X-A5, firmware 1.21. Client: `scripts/fuji_remote_probe.py --stage live`, run through
`scripts/with_camera_wifi.sh`. Raw log: `captures/wifi-gphoto2/2026-10-04-remote-probe.txt` (git-ignored).
The protocol steps follow the public notes listed in `docs/references.md`. Nothing was captured to the SD card.

## Result

The X-A5 enters remote mode and streams live view over Wi-Fi with an open-source client. One run succeeded
from join to clean shutdown in 9.3 s.

| Step | Result |
|------|--------|
| Init on TCP 55740, GUID with the accepted 12-byte prefix, name `xa5-probe` | accepted (attempt 1) |
| OpenSession | `0x2001` OK, immediately |
| Fuji event property `0xD212` | camera state `0xDF00` = 6 (remote access) at once |
| Version props | `0xDF22` = 3, `0xDF25` = 1, `0xDF21` = 3, `0xDF24` = `0x20003` |
| Set `0xDF01` = 5 (remote mode) | OK after 5.4 s (the camera took that long; it may wait on its screen) |
| Set `0xDF24` = `0x2000C` | OK |
| InitiateOpenCapture `0x101C` (0, 0) | OK, 0.6 s |
| Connect TCP 55741 and 55742 | both accepted at once |
| Live view | 179 frames in 3.0 s (59.6 fps), 640x480 baseline JPEG, 18-byte header per frame |
| TerminateOpenCapture, CloseSession | both OK |

The camera does not advertise capture operations in DeviceInfo, but accepts `0x101C` anyway.

## Live-view frame format

Each frame is an 18-byte header followed by a JPEG. The header holds the total length (u32, header
included), four zero bytes, a frame counter (u32 at offset 8: 5, 6, 7 for the first three frames) and six
zero bytes. The `fe 7f` marker named in the public notes was not present. Every frame was
6611 bytes, and the one frame viewed was fully black. That means one of: lens cap on or dark scene, the camera
sends a placeholder before its sensor starts, or the stream needs another step. It was the lens cap (see the
second run below). The script now saves the largest frame and logs the size range.

### Second run, lens cap removed (22:58)

Same steps, all OK. Live view now shows a real image: a close, out-of-focus wall, 640x480 with black bars
above and below (a 3:2 picture in a 4:3 frame). Frames were 11408 to 11486 bytes, 301 frames in 5.0 s
(60.0 fps). The black frames in the first run came from the lens cap, not from the protocol. Setting
`0xDF01` = 5 took 2.0 s this time, not 5.4 s. The owner reported that the camera screen showed a name and a
"transmit OK?" style question, and that they pressed OK. The exact text and which step triggered it are not
recorded.

### Third run, shutter stage, libgphoto2-style properties (23:04)

The first `shoot` stage followed libgphoto2's Fuji capture code (priority mode `0xD207`, shutter property
`0xD208`, exposure time `0x500D`). Remote mode was set as before. The camera answered `0x200A`
(DevicePropNotSupported) for all three: `0xD207` set, `0x500D` get and `0xD208` set. The script stopped before
any shutter command. No photo was taken, CloseSession returned OK. `GetNumObjects` (`0x1006`) returned 0 in
remote mode with a card inserted, so the object count cannot confirm a new photo by itself (to check).
Conclusion: the X-A5 does not use the libgphoto2 X-T focus-then-release property sequence in this mode.
The stage was rewritten to the older flow in public notes (fuji-cam-wifi-tool): open capture and live view
running, then one `InitiateCapture` (`0x100E`, params 0, 0). Result in the next section.

### Fourth run, shutter stage, one `InitiateCapture` (23:11)

Sequence: init, OpenSession, remote mode (`0xDF01` = 5 took 0.3 s this time), `0xDF24` = `0x2000C`,
InitiateOpenCapture, connect 55741 and 55742, then `InitiateCapture` (`0x100E`, 0, 0) with live view open
and its socket drained in a thread.

| Observation | Value |
|-------------|-------|
| `InitiateCapture` response | `0x2001` OK, immediate |
| Frames remaining (`0xD229` in the property list) | `0x900` (2304) before, `0x8FF` (2303) after the shot |
| Event socket (55741), 2.7 s after the command | event `0xC004` (Fuji ObjectAdded), parameters `0x0E`, `0x0E`, 0 |
| Event socket, 3.2 s | event `0xC001`, parameters `0x0E`, `0x0E`, `0x4926` (meaning not known) |
| Event socket, 4.5 s | event `0x400D` (PTP CaptureComplete), parameters `0x0E`, `0x0E`, 0 |
| `GetNumObjects` before and after | 0 and 0: useless in remote mode, do not use it to detect a photo |
| Live view during the shot | 2.68 MB read in about 5 s, no stall |
| TerminateOpenCapture, CloseSession | both OK |

Each event packet is 28 bytes: u32 length, u16 type (4 = event), u16 code, u32 transaction id (1), then
four u32 parameters (the first three are listed below, the fourth was always 0; corrected 2026-10-04
when the fake camera test showed that 12 + 3 x 4 is only 24 bytes).

The camera itself reported one picture taken (frames remaining dropped by one, ObjectAdded, CaptureComplete).
The owner has not yet confirmed the picture on the card, so treat "a photo was written" as reported by the
camera, not as verified. Nothing was downloaded.

A single `InitiateCapture` is enough: no focus step and no `0xD208` property. Whether the camera focused
before the shot is not known.

### Fifth run, same shutter stage, HIGH PERFORMANCE off (23:17)

Same sequence and the same results: `InitiateCapture` OK, events `0xC004`, `0xC001` (third parameter
`0x4FCD` this time, `0x4926` before), `0x400D` at 2.7, 3.2 and 4.5 s, `GetNumObjects` 0, clean shutdown.

Frames remaining (`0xD229`) across runs, from the log:

| Point | Value |
|-------|-------|
| Before any open capture, runs 1 to 4 | `0xB81` (2945) |
| After InitiateOpenCapture (a fixed offset of `0x281` lower) | `0x900` |
| After the shot in run 4 | `0x8FF` (one lower) |
| Before open capture in run 5 | `0xB80` (2944): one lower than runs 1 to 4, which fits the photo from run 4 |
| After InitiateOpenCapture in run 5 | `0x8FF` |
| After the shot in run 5, within the watch window | unchanged, still `0x8FF` |

So the counter drop after the shot was seen in run 4 but not in run 5. Whether run 5 wrote a picture is not
established. The starting `0xD229` of the next run answers it: `0xB7F` means two pictures exist, `0xB80`
means only run 4 wrote one. The owner heard the shutter in run 4 and reported the screen going black after the
photo.

Owner report for run 5: the shutter fired and the picture was saved to the SD card. The camera screen went
black afterwards, the same as with HIGH PERFORMANCE on, so that setting is not the cause. This settles the
shutter question: one `InitiateCapture` writes a picture to the card. It also means `0xD229` did not show the
second picture within the watch window, so do not use it as an immediate confirmation.

### Sixth run, download stage (23:26)

`--stage download` (no remote mode; image-view client mode as in libfuji's gallery flow). Everything returned OK.

| Step | Result |
|------|--------|
| Initial event list | `0xD222` = 2 and `0xD220` = 2, `0xD401` = 2 (two pictures on the card) |
| `0xDF00` = 6, then `0xDF01` = 11 | OK |
| `0xDF25` read 1, set 5 | OK |
| `GetNumObjects` | 0 (still useless on this camera) |
| `GetObjectInfo` handle 2 | OK: `DSCF8704.JPG`, format `0x3801` (JPEG), 5,978,877 bytes |
| `0xD227` = 1, then `GetPartialObject` (`0x101B`) in 1 MiB chunks, then `0xD227` = 0 | all OK |
| Transfer | all 5,978,877 bytes in 1.2 s, file starts with the JPEG marker |

The file is a 6000x4000 JPEG with EXIF: Fujifilm X-A5, software "Digital Camera X-A5 Ver1.21", camera clock
23:11:54. It is a blurry close-up of a wall, as expected from a test shot.

Findings from this run:

- **Object count.** The `0xD222` value in the initial event list is a reliable picture count here: 0 in runs 1
  to 4, 1 at the start of run 5, 2 at the start of this run. That matches one picture per shutter run, so run 5
  did write a picture even though `0xD229` did not change in its watch window. Use `0xD222`, not `0xD229`.
  Caveat: the owner says the card holds three pictures (an older black one, then 8704 and 8705), while
  `0xD222` read 2. So `0xD222` is not the total on the card. It may count pictures since some reset
  (power-on or the first wireless session). What it counts is not known.
- **Handle order.** The picture downloaded as handle 2 has the clock time of run 4's shot (23:11), not of run
  5's (23:17). The owner confirmed on the camera that the newest picture is 118-8705 and that the download
  was 118-8704. So the highest handle is not the newest. Handle 1 turned out to be the newest
  (see the seventh run). Test: run the download stage with `--handle 1` and compare the file name. Not tested yet.
- **Speed.** About 5 MB/s over the camera's access point. A full-size JPEG takes a little over a second.
- No file was deleted or written on the card. The camera state changed only in the client mode and the
  transfer properties, and both ended with CloseSession OK.

### Seventh run, download stage, default handle 1 (23:34)

Same setup steps and the same event list (`0xD222` = 2). `GetObjectInfo` handle 1 returned `DSCF8705.JPG`,
7,173,297 bytes. It downloaded completely in 1.4 s. EXIF camera clock 23:17:52, which is run 5's shot. So:

- **Handle 1 is the newest picture, handle 2 the next older (`DSCF8704.JPG`).** Confirmed with the owner's
  file numbers.
- The owner says the card holds a third, black picture (taken with the lens cap on, the camera showed nothing
  while the cap was on). The camera still counts 2 objects, so that picture is outside the range 1 to `0xD222`
  or the count excludes it. Handle 3 was not tried.

### Eighth run, download stage, handle 3 (23:41)

Same setup, `0xD222` = 2. `GetObjectInfo` handle 3 returned `0x2007` (Incomplete Transfer in the PTP
specification, an odd answer for a missing handle). The script stopped; session closed cleanly. So the third
picture on the card (the black one) is not reachable as handle 3. Only handles 1 and 2 answer. Why the camera
leaves the black picture out is not known.

### Ninth run, shoot and download in one session (23:35)

`--stage shoot --yes-take-photo --download-after`. One join, 9.0 s from init to CloseSession, all steps OK:

1. Remote mode, open capture, live view sockets, one `InitiateCapture` (same events `0xC004`, `0xC001`,
   `0x400D` as before, 3.0 to 4.7 s after the command).
2. This time `0xD229` dropped (`0x8FF` to `0x8FE`) 3.2 s after the shot, so that counter does move, but late.
   The starting value was `0xB7F`, one below the previous run.
3. `TerminateOpenCapture`, then the image-view setup (`0xDF01` = 11) in the same session. The camera accepted it.
4. The initial event list now showed `0xD222` = 3.
5. `GetObjectInfo` handle 1 returned `DSCF8706.JPG` (7,109,840 bytes), one number above the previous newest
   (8705). It downloaded completely in 1.4 s. EXIF camera clock 23:35:50, a 6000x4000 picture of a new scene
   (a blurry close-up, so focus was not tested).

So the whole remote-shooting loop works on the X-A5 from a Linux PC with our own script: join the camera
network, remote mode, live view, shutter release, download the new picture, close.

Notes: switching from remote mode to image view inside one session works. After a shot the newest picture is
handle 1. The black picture the owner took earlier is still not visible: `0xD222` rose from 2 to 3 with our
shot while the card should now hold four pictures (the owner's three plus this one), so `0xD222` probably
counts only the pictures reachable through this interface and the black one is not among them. Not verified.

## Handshake: what we learned

- The earlier Init Fail (`0x201d`) at 22:49:59 did not repeat. Later runs at 22:50 and 22:53 were accepted
  with the same GUID. Before the 22:53 run the owner reported a "client name error" on the camera and no
  connection; the exact screen text and its timing are not recorded. Hypothesis, not tested: the camera
  state at connect time decides, and the first connect after the wireless screen opens works best.
- Init is accepted on attempt 1 in the good run, so the retry loop was not needed here.
- The 5.4 s delay on setting `0xDF01` = 5 matches a camera that switches its own mode. No on-screen
  prompt was reported for this step.

## Still open

1. Why the 22:49:59 init failed. One failure and three accepted runs: not enough to say.
2. What the on-camera prompt says and when it appears (the owner pressed OK).
3. What does `0xD222` count, and why is the black picture missing from the handles? Handle 3 answers `0x2007`. Photo capture writes to the SD card and needs the owner's approval.
4. libgphoto2 still fails on its own (random GUID, second init after ack). Patch not tried.
