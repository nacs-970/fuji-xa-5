# Finding: first real-camera runs of the `fuji_xa` library (2026-10-05)

Camera: Fujifilm X-A5, firmware 1.21. Host: Arch Linux, `wlp1s0` joined through
`scripts/with_camera_wifi.sh`. Code: `src/fuji_xa/` at the working-tree state before its first commit. Each run
was one fresh Wi-Fi join with WIRELESS COMMUNICATION reopened on the camera.

## Results

| Run | Command | Client name | Result |
|-----|---------|-------------|--------|
| 1 | `preview` | `fuji-xa` | Init Fail `0x201D` on all 4 tries. Session never opened |
| 2 | `preview`, retry window 60 s after a refusal | `fuji-xa` | Init Fail `0x201D` 6 times, then `Connection refused` on the control port. The owner reported that the camera showed a client name. Session never opened |
| 3 | `preview` | `xa5-probe` | **Worked.** Session, remote mode, live view, clean end. Saved a 640x480 JPEG of 11 032 bytes (a blurred close-up, as in the earlier probe runs) |
| 4 | `preview`; the owner had been asked to press "change" first | `fuji-xa` | Init Fail `0x201D` 4 times. The run was cut short by the owner, who then asked whether OK must be pressed first. What was pressed is not recorded |
| 5 | `preview`, 60 s retry after a refusal; the owner pressed "change" (to let any device connect), then OK to confirm the transfer | `fuji-xa` | **Worked on the first init, no refusal.** Live view and clean end as in run 3 |
| 6 | `shoot -d /tmp` (the owner said yes to one photo) | `fuji-xa` | **Worked.** One shutter release, then the newest picture downloaded: `DSCF8707.JPG`, 6000x4000 JPEG, 4 988 909 bytes, in 5 chunks. Exit status 0 |
| 7 | three shots in one session (shot 1 + download, shot 2 + download, shot 3 only), to test the black-screen theory | `fuji-xa` | Shot 1 and its download worked (`DSCF8708.JPG`, 6 852 340 bytes). Going back to live view for shot 2 failed: `0xDF01` = 5 was accepted after about 3 s, then the camera closed the control connection. Shots 2 and 3 were not taken |
| 8 | `preview --seconds 30`, live view only, no shutter, to test the black-screen theory | `fuji-xa` | **Worked.** 30 s of live view, clean end, no photo taken. The owner saw the screen black with the LED blinking from the moment the connection started until the end |
| 9 | `shoot -n 3`, no busy retry yet | `fuji-xa` | Shot 1 accepted. Shot 2's `0x100E` answered `0x2019` (Device Busy) right after the completion event, so the library raised and the session ended cleanly. One picture was taken and not downloaded |
| 10 | `shoot -n 3` with a busy retry, HIGH PERFORMANCE on, "change" not pressed | `fuji-xa` | All 3 shots accepted: shots 2 and 3 each answered `0x2019` once, then `0x2001` after 0.5 s. The switch to image view and the download of handle 1 worked (`DSCF8712.JPG`, 6 823 794 bytes), but the CLI could not save it because the folder did not exist (our bug, fixed). Handles 2 and 3 were not tried |
| 11 | `download -n 3` | `fuji-xa` | **Worked.** Handles 1, 2 and 3 were `DSCF8712`, `DSCF8711` and `DSCF8710`, the three pictures of run 10, newest first. All 6000x4000 JPEG, 6.5 to 7.0 MB, in one session, every operation `0x2001` |

Runs 1 and 2 changed nothing on the camera or the SD card. Run 9 left one picture on the card without a copy.

## What run 3 showed

- The library's operation order, taken from `scripts/fuji_remote_probe.py`, works on the real camera: OpenSession,
  event reads, the four version properties, `0xDF01` = 5, `0xDF24` = `0x2000C`, InitiateOpenCapture `0x101C`,
  both sockets, frames, TerminateOpenCapture `0x1018` with the transaction id of the `0x101C` call (11), CloseSession.
- All operations answered `0x2001`.
- The first `0xD212` read listed 6 properties (`0xDF00` = 6, `0xD222` = 3, `0xD220` = 3, `0xD401` = 3). After
  `0xDF01` = 5 it listed 22 properties. After InitiateOpenCapture `0xD229` read `0x8FE`, down from `0xB7E`
  (a difference of `0x280`, about the `0x281` seen before).
- The frame came from the background reader thread. Not tested yet: the shutter and download through the
  library on the real camera.

## What run 6 showed (shoot and download through the library)

- Sequence: the run 3 prelude, `0x100E` (0, 0) answered `0x2001`, six `0xD212` polls while waiting for the
  event, `0x1018` (11), image-view setup, `0x1008` for handle 1, `0x101B` in chunks, `0x1003`.
- `shoot()` printed no warning, so the `0x400D` CaptureComplete event arrived within 15 s. The log does not
  print the event itself, so this is inferred from the missing warning.
- `0xD229` (frames remaining) went from `0x8FE` to `0x8FD` during the wait. After the switch to image view
  `0xD222` read 4, one more than before the shot. The file name `DSCF8707` follows the earlier `DSCF8706`.
- Handle 1 was the new picture, as before. The picture is a blurred close-up, so the camera is probably not
  focusing before the shot. That is still not known.
- Not checked in this run: the shutter sound and the camera screen afterwards (asked of the owner).

## What run 7 showed (three-shot test, black screen)

- **Image view is one way in a session.** After a download, setting remote mode (`0xDF01` = 5) again was
  accepted, and then the camera closed the connection at the next read. The library now refuses
  `start_live()` after a download. A second shot after a download needs a new session. Not tested: whether
  the camera still accepts a new init right after that (it leaves wireless mode when a session ends).
- **Black screen.** The owner reported that the screen was black with the LED blinking during the 10 s after
  shot 1 and its download, with the session still open. After the failed run the camera showed its normal
  live view. Earlier (2026-10-04) the screen also went black when the connection started, before any shot,
  and after shots without a download. So the screen is probably black for the whole Wi-Fi session and the
  shutter and the download are not the cause.
- **Run 8 confirmed it.** With live view only, no shot and no download, the screen was black with the LED
  blinking from the start of the connection to its end. So the black screen is the camera's state during a Wi-Fi
  remote session. It is not a fault and not caused by our code. It needs no fix, and the library cannot change it.
  A user must know that the camera screen shows nothing while remote control runs.

## What runs 9 to 11 showed (several shots, several downloads)

- **Device Busy.** A second `InitiateCapture` straight after a completed shot answers `0x2019`. One retry after
  0.5 s was enough, four times. HIGH PERFORMANCE on (run 10) did not remove it. The library now retries every
  0.5 s for up to 15 s.
- **Several shots, then several downloads, in one session works.** Take all shots in live view, then switch to
  image view once and download handles 1, 2, 3.
- **Handle 3 works** when the camera holds at least three pictures from the recent shots (it answered `0x2007`
  on 2026-10-04 when the count was 2).
- The pictures are blurred close-ups of the same scene, as before. Focus before the shot is still not known.
- Runs 10 and 11 reused the name `fuji-xa` without pressing "change" and were accepted at once. That fits the
  one-registered-name theory: the same name reconnects.

## Client name

The packet for `fuji-xa` was compared byte for byte with the probe's packet and the library's for the same name,
and they are identical. The only difference between runs 1–2 and run 3 is the name. Earlier
[handshake tests](2026-10-04-wifi-gphoto2-handshake-failure.md) saw `xa5-probe` and `CameraClient` accepted and
concluded the name is not checked. That conclusion holds only for those two names.

The owner's theory: the camera accepts only the client name it registered last. If the wireless screen is
reopened without pressing "change", a different name is refused. Runs 1 to 3 fit this (the last name was
`xa5-probe`). Run 5 fits it: the owner pressed "change" first, which in their words lets any device connect, then OK.
Run 4 fits it if they had not pressed "change". The earlier
"client name error can't connect" (libgphoto2 sent the host name) fits too.

Not known:
- what the owner pressed before run 4 (not recorded);
- whether `xa5-probe` is now refused without "change". That run would show whether the camera really keeps
  one registered name. Not run;
- whether "change" alone, or OK alone, would be enough. The owner pressed both in run 5.

The library's default name is `xa5-probe`. When refused, it now says the camera may expect its last name,
or that the user should press "change".

## Changes made because of this run

- The CLI got `--name`.
- A 60 s retry after a refusal was tried in runs 2 and 5 and removed again: run 5 connected on the first init,
  so no wait was needed, and a wrong name would otherwise hang for 60 s.
- `docs/protocol/wifi.md`, `README.md` and `docs/project-overview.md` no longer say the name is ignored.
