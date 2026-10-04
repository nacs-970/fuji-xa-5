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
| 12 | `shoot -d /tmp/xa5-focus` (the owner said "ready" to the proposed one-photo test, subject at normal distance) | `fuji-xa` | **Worked.** One shutter release, handle 1 downloaded: `DSCF8713.JPG`, 6000x4000 JPEG, 5.2 MB, every operation `0x2001`. The picture is sharp where the focus fell (see "Focus") |
| 13 | `shoot -d /tmp/xa5-focus2` (the owner said yes to one photo), focus point on the centre, wall 60 cm away, toy 15 cm away | `fuji-xa` | **Worked.** One shutter release, handle 1 downloaded: `DSCF8714.JPG`, 6000x4000 JPEG, 7.3 MB, every operation `0x2001`. The wall in the centre is sharp, the toy is soft (see "Focus") |
| 14 | `preview --seconds 5 -o /tmp/xa5-preview.jpg`, live view only, no photo, to test whether the black screen after a session comes from image view | `fuji-xa` | **Worked.** Clean end (`0x1018`, CloseSession, both `0x2001`), one 640x480 JPEG of 11.0 KB. The owner saw the screen stay black after the LED went off, with no button pressed |
| 15 | `preview --seconds 5`, live view only, then a wait of 30 s and a light button press (Q) | `fuji-xa` | **Worked**, clean end, 11.7 KB frame. Afterwards the Q button and every other button except the shutter did nothing. The shutter button brought the live view back |
| 16 | `preview --seconds 5` with a new read-only `GetDevicePropValue` of `0xDF01` right after OpenSession and the version reads | `fuji-xa` | **Worked**, clean end, 11.7 KB frame. The read answered `0x2001`, 2 bytes: `0xDF01` = **16** (`0x10`) before we set it. Nothing was written back yet |
| 17 | `preview --seconds 5` with a write of `0xDF01` = 16 (the value read in run 16) just before CloseSession, the owner agreed | `fuji-xa` | The camera accepted the write (`0x2001`) and CloseSession (`0x2001`), the frame was 11.7 KB. **Afterwards the screen stayed black and the shutter button did not bring it back: the owner had to switch the camera off and on.** The owner heard no "ready" sound but was not sure |
| 18 | `props`, read-only: live view starts, then `GetDevicePropDesc` for each property in the change list. No photo | `fuji-xa` | **Worked**, clean end. Every `0x1014` failed (`0x2007` for the 8 standard properties, `0x200A` for the 20 Fuji ones), so no allowed values. The current values from the change list matched the owner's camera settings (see "Camera settings") |
| 19 | `props` again after the owner changed settings on the camera: ISO Auto3, f/3.6, 1/100, AF-C, Standard/Provia. No photo | `fuji-xa` | **Worked**, clean end. `0x5007` = `0x168`, `0xD001` = 1, `0xD02A` = `0x80000C80`, `0xD240` = `0x8000EA60`. See "Settings run 19" |
| 20 | `props` after the owner set 1/500 (dial on M). No photo | `fuji-xa` | **Worked**, clean end. `0xD240` = `0x8007A120` (low part 500000). The other settings were unchanged from run 19 |
| 21 | `set 0x5007 0x118` (F-number f/2.8, 2 bytes), the first write of a setting. The owner had set f/1.7 and said "yes write". No photo | `fuji-xa` | The camera answered **`0x200F`** (Access Denied) and nothing changed: the list still read `0xAA`. The direct read `GetDevicePropValue` of `0x5007` answered `0x2001` with 2 bytes `18 f0` (`0xF018`) before and after, which does not match the list value `0xAA`. Clean end, exit status 1 (the library reports a refused write) |
| 22 | `set 0xd240 0x8007a120 --size 4` (shutter speed 1/500, set over 1/100, dial on M). The owner said "ready, yes write". No photo | `fuji-xa` | The camera answered **`0x2007`** and nothing changed (the list still read `0x800186A0`). The direct read answered `0x2001` with 4 bytes `ff 18 f0 9f` before and after. Clean end, exit status 1 |
| 23 | Test A, one session: `shoot`, `download`, `shoot`, `download`, `shoot` (scratch script with our guard switched off after the first download). The owner asked for the test with up to 3 photos and said "ready" | `xa5-probe` | Shot 1 (complete event at 5.4 s) and download 1 worked (`DSCF8715.JPG`, 6 360 441 bytes). Shot 2: `0xDF01` = 5 answered `0x2001`, then the camera closed the connection about 3 s later. One photo taken, cleanup could not run. Two earlier attempts the same day were rejected, see "Client name". The owner saw the screen back to live view by itself (buttons not checked) |
| 24 | Test B: `shoot -n 3`, then the downloads (the owner said "b ready, ok") | `xa5-probe` | **Worked.** Three shots, handles 1 to 3 downloaded newest first: `DSCF8718` (7 473 797 bytes), `DSCF8717` (6 733 262), `DSCF8716` (6 680 414). All have JPEG start and end markers. Clean end. The owner saw the screen black until the shutter button was pressed |
| 25 | Ending experiment `sockets`: live view 3 s, then close the three sockets with no `0x1018` and no CloseSession. No photo, no download | `xa5-probe` | Frame 11.5 KB. **The screen stayed black until the shutter button was pressed**, as after a clean end. So not sending CloseSession is not what brought the screen back in run 7 and run 23 |
| 26 | Ending experiment 2: live view 2 s, image view (picture count 15, no download), then `0xDF01` = 5 again. No photo | `xa5-probe` | The camera answered `0x2001`, then closed the connection 3.1 s later (as in run 23). **The screen came back to live view by itself, but the shutter button and all other buttons did nothing except Q, the movie button and Fn. Switching the camera off and on fixed it** (owner report) |
| 27 | `serve` (new, MJPEG on `127.0.0.1:8080`) through a scratch script: its own client read the stream for 5 s while the server ran 45 s. Live view only, no photo | `xa5-probe` | **Worked.** 83 frames in 5.0 s (16.6 fps), all valid JPEG, 10 580 to 13 061 bytes. The saved frame is a real 640x480 picture. The owner watched it in a browser: "very smooth". The low rate was not explained, because this run did not count frames at the camera (see run 28) |
| 28 | `serve` for 60 s with a sample every 2 s: frames read from the camera, frames handed to viewers, CPU and RAM of our process. Browser connected. No photo | `xa5-probe` | **Worked.** The camera sent 59 to 60 fps and viewers got the same, except from about 14 s to 20 s: 24 to 27 fps, and 36 fps in one sample (camera and viewers equal, so the camera sent fewer; the owner did nothing at that time, cause not known). Our process used 1.7 to 2.1 % of one core at 60 fps and 0.7 % at 25 fps, and 28 to 29 MB of RAM (peak 29 MB, flat). Owner: "cpu + ram usage is normal". The owner also pressed the shutter button for autofocus and it did not work (when in the run is not recorded) |
| 29 | Scratch script: `GetDeviceInfo` before and after remote mode starts. Read-only, no photo | `xa5-probe` | **Worked.** The lists are identical in both: 25 operations, 7 events, 8 properties, nothing new, nothing gone. Neither lists `0x9026`, `0x9027`, `0x100E`, `0x101C` or `0x1018`. The working `0x100E`, `0x101C` and `0x1018` are not listed either, so the list does not tell what the camera accepts |
| 30 | `props` with the AF mode on ZONE (owner: "ready, zone"). No photo | `xa5-probe` | **Worked.** `0xD17C` = `0x03020804`, the same as before. No setting changed. The picture count read 16 (15 at run 26, the owner was asked about a photo and did not say) |
| 31 | `props`, single point at top-left (owner: "ready, single top-left") | `xa5-probe` | **Worked.** `0xD17C` = `0x03020101`. Nothing else changed |
| 32 | `props`, single point at top-right | `xa5-probe` | **Worked.** `0xD17C` = `0x03020D01`. Nothing else changed |
| 33 | `props`, single point at bottom-right | `xa5-probe` | **Worked.** `0xD17C` = `0x03020D07`. Nothing else changed |
| 34 | `props`, single point at the centre, chosen with DISP/BACK (owner: "ready, single center") | `xa5-probe` | **Worked.** `0xD17C` = `0x03020704`. Nothing else changed |
| 35 | `set 0xd17c 0x03020101 --size 4`: write the focus point to top-left, from the centre (`0x03020704`). The owner said "ready, yes write". No photo | `xa5-probe` | **The camera answered `0x2001`** and its change list then read `0x03020101`. The direct `GetDevicePropValue` returned `ff 18 f0 9f` before and after, the same bytes as for `0xD240` in run 22, so it does not show the value. After the session the owner pressed the shutter and the focus frame was **at the centre**, not top-left (the owner had not reset it by hand): no visible effect |
| 36 | `focus 1 1 --shoot` (new command: write the point, shoot, download). The owner said "ready, yes shoot" with the point at the centre | `xa5-probe` | The write was accepted again (`0x2001`, the list read `0x03020101`). One photo, `DSCF8720.JPG`, 6000x4000. Its metadata says autofocus ran at pixel (3000, 2000), the centre, not at top-left: see "Writing the focus point" |
| 37 | `focus 1 1 --shoot` again, after the owner set up a scene with detail near the top-left. The owner said "retry 1 1 single shot, ready" | `xa5-probe` | The write was accepted again (`0x2001`, the list read `0x03020101`). One photo, `DSCF8721.JPG`. **Its metadata says autofocus ran at pixel (2983, 1983)**, the centre of the 6000x4000 frame, not near (231, 286), where column 1, row 1 would be. So the written point was not used |

Runs 1 and 2 changed nothing on the camera or the SD card. Run 9 left one picture on the card without a copy. Run 12 was taken with a plain "ready" after the offer of a one-photo test. Run 23 took one picture and run 24 three. Runs 25 and 26 took none, and so did 27 to 35. Runs 36 and 37 took one each.

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
- Handle 1 was the new picture, as before. The picture is a blurred close-up. See "Focus" below: the blur is
  probably the subject being closer than the lens can focus.
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
- The pictures are blurred close-ups of the same scene, as before. See "Focus" below.
- Runs 10 and 11 reused the name `fuji-xa` without pressing "change" and were accepted at once. That fits the
  one-registered-name theory: the same name reconnects.

## Focus

Owner's report after run 11: autofocus is set in the camera settings, the lens is a 56 mm f/1.7, the subject was
closer than the lens can focus, and the owner hears the lens adjusting. So the blur comes from the minimum focus
distance, not from a missing focus step. This is the owner's observation, not a measurement.

Run 12 confirmed it: with the subject at a normal distance, one `0x100E` gave a sharp picture. In
`DSCF8713.JPG` the wall plates are sharp at full size (the "CLIPSAL" print and the wall texture are crisp), and the
paper in the foreground is soft, which is depth of field at f/1.7. So the camera runs its own autofocus on the
remote shutter command and no focus step is needed from the PC. Not tested: whether the lens already moves in live
view, and focus control from the PC (a chosen focus point, manual focus).

## Focus, run 13

The owner set the focus point to the centre on the camera. The wall behind was about 60 cm away, a toy about 15 cm
from the lens. `DSCF8714.JPG` shows the wall sharp at full size (plaster texture) and the toy soft. So the camera
focused on the set point, and the toy is below the lens's minimum focus distance, so it could not be sharp anyway.
The owner heard the lens move before the shutter sound. Run 12 and run 13 together: the shutter command makes the
camera run its own autofocus with the settings made on the camera. Not tested: what happens at two different
distances with the same point (the run 12 distance was not recorded), and any focus control from the PC.

## The camera after the session (runs 12 to 14)

Owner's reports. Run 12: a few seconds after the shot and the download, the camera played its "ready" sound again
but the screen stayed black. Run 13: the "ready" sound came after the LED went off, and the screen stayed black
after the PC was back on its own network. A firm press of the shutter button brought the live view back. The
library ended both sessions cleanly (`0x1016`, then CloseSession `0x1003`, both `0x2001`).

Run 14 was a live-view-only session of 5 s: no photo, no image view. The owner saw the same thing: the screen
stayed black after the LED went off, with no button pressed. So the link to image view was wrong. The black screen
after the session does not depend on what the session did. Earlier notes that the camera "returns to its shooting
screen" after a session were not checked against this (the owner may have pressed a button).

The owner's Auto Power Off setting is none, so the camera does not switch itself off. A different screen-saving
setting could still blank the screen.

Run 15 (the same live-view-only session of 5 s, no photo) tested this. The owner waited about 30 s without
touching the camera, then pressed a light button (Q): nothing happened. Every button except the shutter button did
nothing. The shutter button brought the live view back. So the screen is not simply asleep: the camera stays in a
locked state after the session ends, and only the shutter button leaves it. The library ended the session cleanly
in every run (`0x1018`, CloseSession, both `0x2001`).

Guess, tested in run 17 and **wrong**: the camera keeps some Wi-Fi remote state after CloseSession because the
client never sets its client state (`0xDF01`) back. The value
`0xDF01` has before our session is not recorded (the first `0xD212` list does not hold it). Run 16 read it: `0xDF01` is 16
(`0x10`) at the start of a session, before we set 5 (remote mode) or 11 (image view). 16 is a value we had not seen.
What 16 means is not known. How Fuji's own app ends a session is not known.

Run 17 wrote `0xDF01` = 16 just before CloseSession, with the owner's agreement. The camera answered `0x2001` to
the write and to CloseSession. Afterwards the screen stayed black and the shutter button no longer brought it back:
the owner had to switch the camera off and on. So writing the start value back did not restore the camera, and it
seems to have made the state worse than without it. One run only. The write-back was removed from the library
again and is not to be repeated. The camera was usable after the power cycle (to be confirmed by the owner).

So far the only known way back to the live view is the shutter button (runs 12 to 15). The cause of the locked
screen is still not known.

The owner's view: this is camera behaviour. Over USB the camera also shows no mode to switch to. It only opens the
memory for access and does not go back to the shooting mode by itself. So a remote session of any kind leaves the
camera in a state that the user ends on the camera. This fits runs 12 to 17 and is not proven. Decision: do not try
to work around it. Document it, press the shutter button once after a session.

## Download order and other endings (runs 23 to 26)

**Order.** Test A (run 23) repeated run 7 with a full trace in the scratch log: after the download, `0xDF01` = 5 was
answered `0x2001`, and the camera closed the connection before it answered the next read, about 3 s later. So image
view is one way in a session, now seen twice (runs 7 and 23). Test B (run 24) worked as in runs 10 and 11. Take all
the shots first, then download.

**Ending.** Idea: the black screen after a session might come from our clean ending, because in runs 7 and 23 the camera
dropped the connection itself (no `0x1018`, no CloseSession from us) and the screen came back to live view. Run 25 closed
all sockets without `0x1018` and CloseSession: the screen still stayed black until the shutter button. So that idea is
wrong. Run 26 repeated the camera's own drop without a shot or a download (image view, then `0xDF01` = 5). The screen
came back by itself, but the camera was locked: shutter button and all other buttons dead except Q, the movie button and
Fn, until the owner switched it off and on. In runs 7 and 23 the owner did not say whether the buttons worked.

So the way out of a session stays the one from runs 12 to 15: press the shutter button once. The mode `terminate`
(`0x1018` without CloseSession) in `end_test.py` was not run, because `sockets` already left the screen black. Not
tested: any other ending. Do not use the `0xDF01` = 5 from image view as an ending: it needs a power cycle.

## Local live-view stream (runs 27 and 28)

`fuji-xa serve` starts live view and serves it as an MJPEG stream (`multipart/x-mixed-replace`) from the standard
library's HTTP server: `/` is a page with the picture, `/stream` is the stream. Default `127.0.0.1:8080`, no login, so
keep it local. Several viewers share the frames, each sees a part. If the camera stops sending, the server ends and
the session closes. Fake-camera tested (`test_serve`).

Run 28 on the real X-A5: the camera sends about 60 fps and the server passes them all on, with 1.7 to 2.1 % of one
core and 28 to 29 MB of RAM. The browser does the decoding. For the browser the rest of the run only gave a snapshot of
`ps`, whose CPU column is the average since each process started, so it cannot tell what the stream cost. A fair
browser measurement would need two samples of the same processes a few seconds apart. Not done.

Frame rate: from about 14 s to 20 s the camera itself sent only 24 to 27 fps. Run 27's 16.6 fps may be the same effect
(the camera sending fewer frames), but run 27 did not count frames at the camera, so that is not shown. The owner did not cover the lens or
change anything then. What makes the camera slow down (scene, exposure, Wi-Fi) is not known.

Autofocus: the owner pressed the shutter button on the camera for autofocus during run 28 and it did not work.
The only autofocus seen so far runs on the shutter command from the PC (run 13). `docs/protocol/wifi.md` section 6
says a half-press wakes the black screen, so what the camera buttons do during a session is not settled: this run
shows only that a press did not start autofocus. Whether the PC can start autofocus without taking a picture is not
known.

## Focus point (runs 29 to 34)

DeviceInfo (run 29) is the same before and after remote mode starts and does not list `0x100E`, `0x101C` or `0x1018`,
which work. So its operation list cannot tell whether `0x9026` or `0x9027` (named LockS1Lock and UnlockS1Lock in
`libfuji`, SetFocusPoint and ResetFocusPoint in libgphoto2, both read 2026-10-05) would be accepted. They were not sent.

Runs 30 to 34 moved the focus point on the camera before each `props`. Only `0xD17C` changed:

| Setting on the camera | `0xD17C` | Second-lowest byte | Lowest byte |
|-----------------------|----------|--------------------|-------------|
| single point, top-left | `0x03020101` | 1 | 1 |
| single point, top-right | `0x03020D01` | 13 | 1 |
| single point, bottom-right | `0x03020D07` | 13 | 7 |
| single point, centre with DISP/BACK | `0x03020704` | 7 | 4 |
| single point set by hand to "centre" (before run 23), and ZONE in run 30 | `0x03020804` | 8 | 4 |

So the second-lowest byte is the column (1 to 13, left to right) and the lowest byte is the row (1 to 7, top to
bottom). 13 x 7 is 91 points. The exact centre is column 7, row 4. The point the owner set by hand earlier was one column
right of it. In zone mode the value was the zone's position, as far as one reading shows. The two high bytes `03 02` did
not change in any run, including zone mode. What they are is not known (the focus frame size is a guess, the manual says
single point has 5 sizes, not tested).

`0xD209` (AF status in libgphoto2) read 0 in all runs. The focus point can be read. Setting it, or starting autofocus
from the PC, is not tested: writes to `0x5007` and `0xD240` were refused (runs 21 and 22), the libgphoto2 USB focus
route (`0xD208`) was not supported over Wi-Fi (2026-10-04), and the vendor operations are gated.

## Writing the focus point (runs 35 to 37)

The camera accepted a 4-byte write of `0xD17C` (`0x03020101`) with `0x2001` and then reported the new value in its
change list, in runs 35, 36 and 37. That differs from `0x5007` and `0xD240`, which were refused (runs 21 and 22). But the
write has no effect on autofocus:
- After run 35 the owner found the focus frame at the centre.
- Run 36 wrote the point and shot in the same session. Its photo showed no sign of autofocus at top-left (a plain wall
  there, so weak evidence by eye).
- Run 37 did the same with a textured scene. Eyeballing and a sharpness map were again not decisive, because the wall and
  the objects near it sit in one plane. **The photo's own metadata is decisive.** The Fuji MakerNote tag `0x1023`
  (`FocusPixel`, read with Pillow and with `exiftool`) is (2983, 1983) in run 37: the centre of the 6000x4000 picture.
  Column 1, row 1 would be near (231, 286). So the point was not used.

`FocusPixel` is a way to check where autofocus ran for any photo, with no special scene. Earlier remote shots read
(3000, 2000) exactly (runs 23 and 24 and run 36), although the camera's own point was column 8 at that time (which would
be near x = 3462). So a shot released from the PC seems to focus at the exact centre whatever point the camera shows.
That is one tag read from a few photos, not a proof. Not checked: the same tag on a photo taken with the camera's own
shutter button at another point.

Conclusion so far: settings cannot be changed from the PC on the X-A5 over Wi-Fi in the ways we tried. `0x5007` and
`0xD240` were refused, and `0xD17C` was accepted and ignored. The protocol-state writes (`0xDF01`, `0xDF24`, `0xD227`)
work, because remote mode and image view depend on them. The `focus` command written for run 36 was removed again,
because `set` already writes a property and `shoot` already shoots.

## Camera settings (run 18)

The raw output is in `captures/wifi-gphoto2/2026-10-05-props.txt` (git-ignored). Before the run the owner read these
settings on the camera: ISO 1600, 1/200 s, f/1.7, white balance auto, film simulation Classic Chrome. The change
list held `0xD02A` = `0x640` (1600), `0x5007` = `0xAA` (170, f/1.70), `0xD240` = `0x80030D40` (200000 in the low
part, 1/200), `0x5005` = 2 and `0xD001` = `0xB`. So all five fit, with one data point each. The owner then added:
focus mode AF-S (`0x500A` = `0x8001`), the built-in flash closed (`0x500C` = 2, flash off in standard PTP; this
camera needs the flash popped up by hand), and exposure mode "auto" (`0x500E` = 1). The owner later corrected this: the dial was on M in runs 18 and 19. The
value 1 is manual in standard PTP, so it fits. The exposure compensation was not
given, so `0x5010` (= 0) is not matched. Nothing was written to the camera.

Not tested: `GetDevicePropValue` on these properties, the allowed values (another source is needed, since
`GetDevicePropDesc` is not served), and setting a value.

## Settings run 19

The raw output is in `captures/wifi-gphoto2/2026-10-05-props-2.txt` (git-ignored). Compared with run 18:

| Property | Run 18 (owner's setting) | Run 19 (owner's setting) |
|----------|--------------------------|--------------------------|
| `0x5007` F-number | `0xAA` (f/1.7) | `0x168` = 360 (f/3.6). Fits f-number x 100 |
| `0xD001` film simulation | `0xB` (Classic Chrome) | 1 (Standard/Provia) |
| `0xD02A` ISO | `0x640` = 1600 (ISO 1600) | `0x80000C80` (ISO Auto3). Top bit set, low part 3200 |
| `0xD240` shutter speed | `0x80030D40` (1/200) | `0x8000EA60` (1/100 set, 1/60 shown after the session). Low part 60000 |
| `0x500A` focus mode | `0x8001` (AF-S) | `0x8001` (AF-C set). **Did not change** |
| `0x5005`, `0x500C`, `0x500E`, `0x5010` | 2, 2, 1, 0 | 2, 2, 1, 0 (same) |

- The f-number and film simulation values are clear.
- ISO Auto3 sets the top bit. The low part 3200 may be the Auto3 limit or the ISO the camera chose. Not known.
- The shutter speed: the owner had set 1/100 with the dial on M (not auto, the owner corrected an earlier statement).
  After the run the owner pressed the shutter button to wake the camera and the screen showed 1/60. So 60000 is 1/60,
  and run 18's 200000 was 1/200. Both fit: low part = denominator x 1000. Two data points, fractions of a second only.
  The top bit is not understood, and slow speeds (above 1 s) are not tested. Why the speed was 1/60 and not the 1/100
  the owner set, in M mode, is not known.
- The focus mode value stayed `0x8001` although the owner set AF-C (confirmed by the owner). So `0x500A` does not tell
  AF-S and AF-C apart: it is not the AF mode, or the camera reports one value for both in remote mode, or it changes
  only in another state. Not known.

## Settings run 20

The raw output is in `captures/wifi-gphoto2/2026-10-05-props-3.txt` (git-ignored). The owner set 1/500 with the dial on M.
`0xD240` read `0x8007A120`: the low part is 500000, so 1/500 fits the pattern "denominator x 1000". With 1/200 (200000)
and 1/60 (60000) that makes three points, all with the top bit set. Aperture (`0x168`), film simulation (1), ISO
(`0x80000C80`) and focus mode (`0x8001`) did not change from run 19.

The owner saw 1/500 on the screen before the run and after it. So the session does not change the shutter speed. Run 19's
change from 1/100 to 1/60 is still unexplained (the speed may not have been 1/100 when the run started, or a wheel moved).

## First write of a setting (run 21)

The raw output is in `captures/wifi-gphoto2/2026-10-05-set-fnumber.txt` (git-ignored). `fuji-xa set 0x5007 0x118` wrote
2 bytes to `SetDevicePropValue`. The camera answered `0x200F` (Access Denied in standard PTP). The value did not change.
It was sent in remote mode with live view running, the dial on M, the aperture at f/1.7.

- `GetDevicePropValue` on `0x5007` works (`0x2001`), unlike `GetDevicePropDesc`. It returned `0xF018` while the change
  list said `0xAA`. The two are not the same number and the reason is not known.
- The owner says the lens has no aperture ring, and the screen still showed f/1.7 after the run. So a ring does not
  explain the refusal. Possible reasons, none tested: the aperture is set through another property, or the write
  needs another state or size, or `0x5007` cannot be written at all.
- The change list in this run read `0xD240` = `0x800186A0`. The owner confirms 1/100 was set, so 1/100 gives 100000: a
  fourth point for "denominator x 1000".
- Not tested: a write of any other setting (shutter speed `0xD240`, ISO `0xD02A`, film simulation `0xD001`).

## Second write of a setting (run 22)

The raw output is in `captures/wifi-gphoto2/2026-10-05-set-shutter.txt` (git-ignored). `fuji-xa set 0xd240 0x8007a120 --size 4`
wrote 4 bytes. The camera answered `0x2007` and did not change the value. Two settings writes are now refused with
different codes: `0x5007` with `0x200F` (run 21), `0xD240` with `0x2007` (run 22). In both runs live view was running and the dial was on M.

- The direct reads of these properties give numbers that do not match the change list: `0x5007` read `18 f0`, `0xD240` read
  `ff 18 f0 9f`. Both hold the bytes `18 f0`. This may be data that is not the setting's value. Not understood.
- Not tested: writing before live view starts (right after remote mode), writing `0xD001` or `0xD02A`, a write in another
  dial mode, a write of the value the camera already holds, and an 8-byte or other-size write.
- Public notes (libfuji, `lib/fuji.c`, read through a summarising tool) did not show how it sets these settings, so there is
  no reference to copy from yet.

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

Runs 23 to 26 (later the same day): the first two attempts used the library default `xa5-probe`, but the camera's
last registered name was `fuji-xa` (the name of runs 4 to 22, which were run with `--name fuji-xa`). They were rejected
with `0x201D` three times, then `Connection refused` on the control port. The mistake was ours: we forgot `--name`,
and first took it for another client that had registered a name. The next attempt with `xa5-probe` worked. What the
owner pressed on the camera in between is not recorded (probably "change"). From then on the registered name should be
`xa5-probe`, the library default. This fits the one-registered-name theory.

## Changes made because of this run

- The CLI got `--name`.
- A 60 s retry after a refusal was tried in runs 2 and 5 and removed again: run 5 connected on the first init,
  so no wait was needed, and a wrong name would otherwise hang for 60 s.
- `docs/protocol/wifi.md`, `README.md` and `docs/project-overview.md` no longer say the name is ignored.
