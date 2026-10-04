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

Runs 1 and 2 changed nothing on the camera or the SD card. Run 9 left one picture on the card without a copy. Run 12 was taken with a plain "ready" after the offer of a one-photo test.

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

## Changes made because of this run

- The CLI got `--name`.
- A 60 s retry after a refusal was tried in runs 2 and 5 and removed again: run 5 connected on the first init,
  so no wait was needed, and a wrong name would otherwise hang for 60 s.
- `docs/protocol/wifi.md`, `README.md` and `docs/project-overview.md` no longer say the name is ignored.
