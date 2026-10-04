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
| 38 | Scratch script `focus_s1.py`: live view, then vendor op `0x9026` (no parameters), 3 s, `0x9027` if accepted. No photo. The owner said "ready, yes vendor" and listened | `xa5-probe` | **`0x9026` answered `0x2001`**, `0x9027` answered `0x2001`. `0xD209` read 0 before, **1 after `0x9026`** (still 1 about 3 s later) and 0 after `0x9027`. Nothing else in the change list changed. **The owner heard the lens move.** The session ended normally. See "Locking autofocus from the PC" |
| 39 | Scratch script `focus_af.py`: live view with a sharpness reading every 0.25 s, write `0xD17C` = `0x03020101`, `0x9026` (no parameters), 4 s, one shot while locked, `0x9027`, download. The owner said "ready, yes vendor, yes shoot"; the subject was a screen with text | `xa5-probe` | `0x9026`, the shutter command and `0x9027` all answered `0x2001`, CaptureComplete arrived, exit status 0. `0xD209` went 0 to 1 within about 0.5 s of `0x9026` and stayed 1 until `0x9027` (about 5 s), never 2 or 3. One photo, `DSCF8722.JPG`: `FocusPixel` (2983, 1983), `AFMode` Single Point, `FocusWarning` Good. See "Locking autofocus from the PC" |
| 40 | Scratch script `focus_pt.py`: live view with a PC preview (`serve` in a thread, browser on port 8080), 10 s, write `0xD17C` = `0x03020101`, `0x9026`, 4 s, `0x9027`, 8 s more; an 8 x 6 edge-strength grid of the live-view frames. No photo. The owner said "ready, yes vendor, with pc preview". The subject was a plush toy left of the centre, and the top-left corner of the frame was plain wall | `xa5-probe` | `0x9026` and `0x9027` answered `0x2001`. `0xD209` read 0, then 1 about 0.3 s after the lock, then 0 after the unlock. The frame was blurred before the lock, the toy's face was sharp at the end of the lock and still sharp 8 s after the unlock. The cells that got sharper are columns 3 and 4, rows 2 and 3 (x 160 to 320, y 80 to 240 of the 640x480 frame), next to the centre. The top-left cell did not change. So the lens focused on the object near the centre, not at the written top-left point. See "Locking autofocus from the PC" |
| 41 | `fuji-xa -v serve --seconds 90` with the new Focus button and Space key on the page (`Camera.focus()`), a browser on port 8080. The owner said "ready, y vendor" | `xa5-probe` | Every `0x9026` and `0x9027` answered `0x2001` (at least 28 pairs in the log tail), the session ended normally. The log had no timestamps. The owner: "shutter button didn't work at all, i have to use spacebar" (the owner later said this meant the camera's own shutter button: it did not focus during the session, as in run 28). See "Focus from the preview page" |
| 42 | The same with `--seconds 30` and timestamps on the log lines. The owner said "retry again 30s this time" and "ready" | `xa5-probe` | All operations answered `0x2001`. The pairs were not balanced: four `0x9026` with only two `0x9027` between 25.96 s and 32.40 s of the log, while the owner clicked the page button. Later presses came as clean pairs. The session ended normally. See "Focus from the preview page" |
| 43 | `fuji-xa -v serve --seconds 30` again, after the race fix, with the duration of each operation in the log. The owner said "ready" | `xa5-probe` | 13 locks and 13 releases, strictly alternating, all `0x2001`. The session ended normally. `0x9026` took 0.00 to 0.04 s (0.41 s once), `0x9027` 0.00 to 2.51 s. The owner: clicks on the page button focused the lens, Space holds of about 2 s focused it, and the focus showed in the preview within 1 to 2 s. See "Focus from the preview page" |
| 44 | Scratch script `button_watch.py`, read-only: live view with the PC preview (its Focus button switched off), the property list read about 10 times a second and the event port listened to for 75 s, printing only changes. The owner pressed the shutter (half-press), Q, DISP/BACK and Menu. The owner said "ready for button" | `xa5-probe` | **No property changed and no event arrived** in 75 s (22 properties in the list). None of the camera's buttons did anything for the session, as the owner saw it; a half-press of the shutter woke the black screen. The owner also tried Space and the page's Focus button: they were refused (HTTP 500) as designed. The session ended normally. See "Camera buttons" |
| 45 | Scratch script `focus_cell.py`: live view with the PC preview, vendor operation `0x9026` with the parameter `0x03020303` (column 3, row 3) held 4 s, `0x9027`, the live-view frame headers recorded, then the read-only vendor operation `0x902B` with no parameters. No photo. The owner said "ready, yes vendor" | `xa5-probe` | `0x9026` with the parameter answered `0x2001`, `0xD209` went 0 to 1 within 0.3 s and back to 0 after `0x9027`, as with no parameter. **The frames did not sharpen**: the edge strength of every 80 px cell changed by 1 or less between the frame before the lock and the one at its end. The owner answered "yes, yes" to my questions whether the lens moved and whether the preview sharpened (I read it that way; the question about an object in the cell was not answered separately), so the two frames I sampled may have missed it. The frame header: bytes 4 and 5 after the length are a 16-bit frame counter, the other 12 bytes were 0 in all 1151 frames, so the header carries no autofocus information. **`0x902B` answered `0x2001` with 360 bytes: 10 property descriptions**, with ranges and allowed values (see "Property descriptions"). The session ended normally |
| 46 | `fuji-xa -v serve --seconds 90` with the new page: a green square for the camera's focus point, click on the picture to focus there, Space and a Focus button. About 50 clicks and a few presses of Space. The owner said "ready, yes vendor" | `xa5-probe` | Every `0x9026` (with a cell, or none for Space) and `0x9027` answered `0x2001`; the lock answered in 0.00 to 0.43 s, the release in up to 1.09 s. The session ended normally. The owner: the square appeared and jumped to the clicked cell; **the lens focused at the clicked point**; the square stayed on the cell after the release; Space and the Focus button, which sent no cell, **moved the point to the centre** and focused there; the preview stuttered for the first few seconds. **Choosing the focus point from the PC works.** See "Choosing the focus point" |
| 47 | `fuji-xa -v serve --seconds 90` with the coloured square (white until focused, green, red; the square jumps at once on a click), property list read every 0.25 s. The owner said "ready, yes vendor" | `xa5-probe` | About 60 locks and releases, all answered `0x2001`, session ended normally. `0xD209` went 0 to 1 between 0.7 and 1.7 s after the lock was sent and back to 0 about 0.2 to 0.5 s after the release; a click let go within about 0.7 s never reached 1; **it was never 2**. The owner: **the square needed 1 to 2 s to turn green while the camera beeped after about 0.5 s**, and **in AF-C the lens did not keep refocusing while Space, the Focus button or the mouse was held and the camera was moved**. Not reported: red, a plain wall, the stutter. See "Green delay and AF-C" |
| 48 | `fuji-xa -v serve --seconds 100` with the property list read every 0.1 s and the page sending `0x9026` again every second while Space, the Focus button or the mouse was held; raw log saved. The owner said "ready, yes vendor" | `xa5-probe` | 17 locks and 4 releases, **every `0x9026` and `0x9027` answered `0x2001`**; repeats took 0.00 s, or 1.2 to 2.1 s when the camera was already locked. **`0x1015` took 0.6 to 2.5 s to answer while the camera was focusing, and `0xD209` turned 1 in the same moment the slow read returned.** The owner: **the lens refocused when the camera moved**, green came sooner, but the preview stutters until the focus completes; no red. **The session ended by itself** about 5 s after the last release: no live-view frame for 5 s, the close timed out (`cleanup failed: timed out`), `fuji-xa: no live-view frame arrived`. The owner saw the **camera return to its normal live preview after it disconnected**. See "Green delay and AF-C" |
| 49 | `fuji-xa -v serve --seconds 120` with the repeat every 2 s by default and `?every=1` and `?every=3` in the page address; raw log saved. The owner said "ready, yes vendor" | `xa5-probe` | 23 holds, every `0x9026` and `0x9027` answered `0x2001`, **the session ended normally** (`0x1018`, `0x1003`), and the run-48 drop did not come back. `0xD209` turned 1 within 0.48 to 0.67 s of the lock in 4 holds, after 0.9 to 5.4 s in 11, and 8 holds were let go before it turned green; 54 of 461 property reads took over 0.3 s (up to 2.5 s). The owner: **`?every=1` updates the focus fastest and `?every=3` slowest; green is closer to the camera's beep than before; the camera screen is black after the session, as after every normal one**; no red. See "Green delay and AF-C" |
| 50 | Scratch script `postview_try.py`: live view, vendor operation `0x9022` (the app's GetPostview, no parameters) once before any shot, one shot, then `0x9022` twice. The owner said "ready, yes vendor, yes shoot" | `xa5-probe` | Before the shot `0x9022` answered `0x2001` with **0 bytes**. The shot took 2.9 s to `CaptureComplete`. The first `0x9022` after it answered `0x2001` with **42 751 bytes, a 640 x 480 JPEG, in 0.04 s**: the picture just taken, with black bars top and bottom like the live view (3:2 in 4:3). The second one answered `0x2001` with 0 bytes. **One photo on the SD card, not downloaded.** See "Postview" |
| 51 | `fuji-xa -v shoot --postview -n 1 -d <folder>`: one shot, `Camera.postview()` right after it, then the usual download. The owner said "ready, yes vendor, yes shoot" | `xa5-probe` | `0x9022` answered `0x2001` with **42 331 bytes in 0.03 s**, saved as `postview_1.jpg` (640 x 480 JPEG). Then live view ended and **the download worked as before**: `DSCF8724.JPG`, 7.2 MB, 6000 x 4000, 8 reads of 0.06 to 0.34 s (about 1.8 s), `FocusWarning` Good, `FocusPixel` 2983 1983. **The postview is the same picture as the download**, seen side by side. The session ended normally. One photo on the card, with a copy. See "Postview" |
| 52 | `fuji-xa -v shoot --postview -n 3 -d <folder>`: three shots with a postview read after each, then the download of all three. The owner said "ready, yes vendor, yes shoot" and moved the camera a little between shots | `xa5-probe` | Every `0x9022` answered `0x2001` with a JPEG: 40 269, 40 032 and 48 223 bytes, in 0.01 to 0.03 s. Shots 2 and 3 each answered `0x2019` (busy) once and then `0x2001` after the 0.5 s retry, as in earlier runs. The download then fetched all three (handles 1 to 3, newest first: `DSCF8727`, `DSCF8726`, `DSCF8725`, 7.3 to 7.8 MB, 6000 x 4000). **Each postview is the picture of its own shot**, compared side by side in order. `FocusWarning`: Good, Out of focus, Good (no focus lock sent). The session ended normally. Three photos on the card, with copies. See "Postview" |
| 53 | Scratch script `lvsize_try.py`: live view, then `GetDevicePropValue` (`0x1015`) of `0xD174` (live view size in libgphoto2) and `0xD173` (live view quality), with a write of `0xD174` planned only if the read worked. No photo. The owner said "ready, yes vendor" | `xa5-probe` | **Both reads answered `0x200A`, property not supported**, so nothing was written. Live frames: 640 x 480, 91 in 1.5 s. The session ended normally. See "Postview" |
| 54 | `fuji-xa -v shoot --postview -n 2 --no-download -d <folder>`: shot, postview, shot, postview, end, no download. The owner said "ready, yes vendor, yes shoot" | `xa5-probe` | Both `0x9022` answered `0x2001` with a 640 x 480 JPEG (18 496 and 18 498 bytes, 0.02 and 0.01 s; small because the scene was a plain wall and a corner). **The second shot answered `0x2001` at once, no `0x2019` busy answer**, because the postview read had run in between. The session ended normally (`0x1018`, `0x1003`), live view only, no image view. Two photos on the card, **not downloaded** (the owner can fetch them with `fuji-xa download`). See "Postview" |

Runs 1 and 2 changed nothing on the camera or the SD card. Run 9 left one picture on the card without a copy. Run 12 was taken with a plain "ready" after the offer of a one-photo test. Run 23 took one picture and run 24 three. Runs 25 and 26 took none, and so did 27 to 35. Runs 36 and 37 took one each. Run 38 took none, run 39 one and runs 40 to 46 none.

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

## Locking autofocus from the PC (runs 38 to 40)

Before this run the docs said focus control from the PC was "not known", and the vendor operations `0x9026` and
`0x9027` (SetFocusPoint and ResetFocusPoint in libgphoto2, LockS1Lock and UnlockS1Lock in `libfuji`, names only, no
parameters in either) had never been sent. The owner agreed to a vendor command ("ready, yes vendor"). The scratch
script started live view, sent `0x9026` with no parameters, waited 3 s, and sent `0x9027`.
- Both answered `0x2001`.
- `0xD209` (AFStatus in libgphoto2) went 0, 1, 0. In libgphoto2's USB notes 1 means busy, 2 ok and 3 failed. That is not
  checked on this camera, and the script read the value once after the 3 s wait, so it is not known whether 1 would have
  turned into 2 or 3 given more time.
- The owner heard the lens move. So the PC can start the camera's autofocus without a photo, which the docs had as open.
- Not known: which focus point the lock uses (a write of `0xD17C` is ignored by the shutter command, run 37, and not yet
  tried before `0x9026`), whether parameters change anything, what a photo taken while locked shows, and whether the
  lock is the same as a half press.
- The change list was the same in the three reads except `0xD209`. The session ended normally (exit status 0).

Run 39 repeated the lock with a written focus point, one shot while locked, and a live-view record:
- The sequence worked as in run 38. `0xD209` was 1 from the first read after `0x9026` until `0x9027`, about 5 s, and
  never became 2 or 3. On this camera it looks like "locked", not libgphoto2's busy, ok and failed (from one run, not
  confirmed). The shutter command was accepted while locked (`0x2001`, CaptureComplete).
- The written point was not used. `FocusPixel` of `DSCF8722.JPG` is (2983, 1983), the centre of the 6000x4000 frame and
  the same two numbers as run 37, not near (231, 286). Either the lock ignores `0xD17C` like the shutter command does, or
  the shutter command re-ran autofocus at the centre. These two cannot be told apart from this run.
- The live-view frames saved before, during and after the lock show a screen with text: soft before, crisp text during
  and after. The camera was moved by hand between frames, so that is a hint that the lens focused, not a measurement.
  The edge-strength numbers for the centre and top-left boxes (1.5 to 11) mean nothing here, because both boxes hold
  mostly plain wall. A later test needs a box on the subject.
- The two photos that read `FocusWarning` Good (runs 37 and 39) both have `FocusPixel` (2983, 1983). The five that read
  `Out of focus` (a plain wall) have (3000, 2000). That fits "an exact (3000, 2000) means autofocus found nothing to lock
  on", from two against five photos, not tested.
- The owner heard the lens move in run 39, and the camera was set to AF-C (continuous). In AF-C the camera may keep
  refocusing, which could be why `0xD209` stayed at 1. Not tested: run the lock in AF-S.

Run 40 asked the same question with no shutter command: write `0xD17C` to top-left, lock, unlock, and watch the live view
(the owner also watched it in a browser through `serve`).
- The lens moved to the object near the centre and stayed there after `0x9027`. The top-left corner was plain wall in
  that frame, so a lock at the written point had nothing to focus on, and the frame did not look like that.
- So the written point is not used by `0x9026` without parameters, and not by the shutter command either (run 39).
- `0xD209` again read 1 during the lock and never 2. The owner's AF mode in run 40 (AF-S or AF-C) was not recorded, so
  the AF-C idea from run 39 is still open.
- After the run the scratch script's preview thread raised `FujiError: live view is not running` once the session had
  ended. That is because `serve` was started in a thread and the session closed under it, not a camera problem.

## Focus from the preview page (runs 41 to 43)

`fuji-xa serve` got a Focus button and a Space key: hold = `0x9026`, let go = `0x9027` (through `Camera.focus()` and
`release_focus()`). Runs 41 and 42 were its first real runs.
- The camera accepted every operation. The page works with the camera.
- **A bug of ours showed in run 42.** `Camera` set its "locked" flag after the lock operation had finished, and the
  page sends "down" and "up" from two threads. A quick click sent "up" while the lock was still in flight, so the release
  was skipped and the camera stayed locked (four locks, two releases). The lock now covers the check, the operation and
  the flag. A test on the fake camera reproduces the race without the lock and passes with it. The owner later said run 41's
  "shutter button didn't work" meant the camera's own shutter button, so this bug is not what they saw in run 41.
- **Timing (run 43, measured with the new duration log).** `0x9026` answers at once, 0.00 to 0.04 s (0.41 s the first time).
  `0x9027` took 0.00 to 2.51 s, with no clear link to how long the owner held. My guess in the first version of this
  text, that `0x9026` takes about 0.9 s, was wrong: it came from log spacing when presses queued behind a slow
  `0x9027`. Possible, not tested: the release waits until the camera's autofocus has finished.
- After run 43 the page was changed to send "up" only after "down" was answered, so the two requests cannot swap order
  (two separate requests on two connections could, in principle). That page version has not run in a real browser yet.
  The fake-camera test for the race now starts the release exactly while the lock is in flight, instead of two threads
  started together, which failed about one run in six.
- **Owner's report on run 43:** a mouse click on the page button focused the lens, a Space hold focused it, and the preview
  showed the focus within 1 to 2 s. So a click of about 0.15 s is enough and the page needs no minimum hold.
- The camera's own shutter button did not focus during the session in runs 28 and 41 (owner). Why is not known.
- Not known: whether a held lock stops further focusing (an X-T3 over USB does, public notes), what the camera does
  with a lock while the lens is already focused, and whether the camera's own shutter button reports anything to the PC.

## Camera buttons (run 44)

Run 44 asked whether the camera tells the PC when its own buttons are pressed during a session. It does not. While the
owner pressed the shutter (half-press), Q, DISP/BACK and Menu, the property list and the event port showed no change at
all for 75 s. The same method did show our own lock (`0xD209` changed in runs 38 to 43), so it can see changes. The
owner saw no button do anything except the half-press waking the black screen, and the Focus button and Space on the
preview page were refused on purpose in this run.
- So the camera's own shutter button cannot focus and cannot be mapped to the PC's lock. The PC is the only way to focus.
- The owner added afterwards that the dials and a full press of the shutter did nothing either during a session (no photo
  was taken). Those two were not part of the script's 75 s record, so only the camera's own behaviour is known there,
  not whether it reported them to the PC.
- Not tested: the touch screen, and pressing for longer.

## Property descriptions (run 45)

Vendor operation `0x902B`, which the official app uses (APK finding), answered `0x2001` with no parameters and no
trouble. The reply is a 32-bit count (10), then per property a 32-bit size that includes its own four bytes and a standard
PTP property description: code, data type, read-only or get/set flag, default, current value, form flag, and a range or a
list of allowed values. The layout matched what public libgphoto2 code reads, except for the size rule. The properties:

| Property | Flag | Current | Allowed |
|----------|------|---------|---------|
| `0xD019` | read-only | 1 | 0, 1 |
| `0x500C` (flash mode) | get/set | 2 | 2 only |
| `0x5012` | get/set | 0 | 0, 2, 4 |
| `0xD17C` (the app's S1 lock) | get/set | `0x03020303` (the cell we sent, see below) | range 0 to `0x10090D07`, step 1 |
| `0xD245` (AF select mode) | get/set | 2 | 0, 1, 2, 3 |
| `0xD240` (shutter speed) | get/set | `0x800186A0` (1/100) | one value, `0x7530` |
| `0x5005` (white balance) | get/set | 2 | 2, 4, 6, `0x8001`, `0x8002`, `0x8003`, `0x8006`, `0x800A`, `0x800B`, `0x800C` |
| `0x5007` (F-number) | get/set | `0xAA` (f/1.7) | `0xFFFF`, `0xDC`, `0x118` |
| `0xD001` (film simulation) | get/set | 1 | 1 to 5, `0xB`, 6 to `0xA` |
| `0xD02A` (ISO) | get/set | `0x80000C80` | 27 values, see below |

- `0xD17C`: the maximum `0x10090D07` is the same layout as the value. Low two bytes `0x0D07` are the grid, **13 columns by
  7 rows**, as the app reads it. High two bytes `0x1009` are 16 and 9, so the maximum aspect is 16:9 and the current one
  (`03 02`) is 3:2. The grid is read from the camera, so it is not hard-coded in the app.
- **ISO values** (`0xD02A`): a plain number is the ISO itself (`0xC8` = 200 up to `0x3200` = 12800, in the usual
  thirds: 200, 250, 320, 400, 500, 640, 800, 1000, 1250, 1600, 2000, 2500, 3200, 4000, 5000, 6400, 8000, 10000, 12800),
  `0x40000064`, `0x40006400` and `0x4000C800` are the extended values (100, 25600, 51200), and `0x80000000` plus a number is
  Auto up to that ISO (`0x80000190`, `320`, `640`, `C80`, `1900` are Auto up to 400, 800, 1600, 3200, 6400). So the
  `0x80000C80` we read in run 19 is Auto up to 3200, which is what the camera was set to ("Auto3").
- The get/set flag is not a promise. `0x5007` and `0xD240` are marked get/set and our writes were refused (runs 21 and
  22). The list for `0x5007` (three values) and `0xD240` (one) is also shorter than what the camera can do, and the current
  F-number (`0xAA`) is not in it, so these two lists describe something other than the lens' real range. Not understood.
- `0xD17C` read `0x03020303` after the lock, the cell we sent. That is not proof that autofocus used it: in runs 35 to 37
  the camera also read back what we wrote and ignored it.

## Choosing the focus point (runs 45 and 46)

**It works.** Vendor operation `0x9026` with one 32-bit parameter focuses the X-A5 at the chosen cell. The parameter is
the picture aspect (two bytes, `03 02` for 3:2), then the column (1 to 13) and the row (1 to 7), the same layout as `0xD17C`,
as the official app does for a tap (APK finding). `0x9027` with no parameter releases it.
- The owner saw the lens focus at the clicked point, and the camera's `0xD17C` followed the cell (`0x902B` read it back in
  run 45, the page showed it as a square in run 46).
- **The point stays after the release.** The release does not reset it.
- **A lock without a cell moves the point to the centre** and focuses there (runs 38 to 43 did exactly that, which is why
  they always focused at the centre). A write of `0xD17C` still does nothing (runs 35 to 37).
- Run 45's script frames did not show a clear sharpening: two frames per phase, the camera was moved by hand, and the cell
  lay on a blurred dark edge. The owner reported the lens moving and the preview sharpening. Run 46, where the owner clicked
  on objects and watched, is the clear result.
- After run 46 the page's Focus button and Space were changed to lock at the square's cell, because a lock without a cell
  sends the point back to the centre. That change was tested on the fake camera only.
- `Camera.focus((column, row))` and the page's click-to-focus are the library side of this. The grid, 13 by 7, is a constant
  taken from the camera's `0xD17C` range maximum (run 45); another body may differ.
- **`0xD209` is the colour of the camera's focus frame.** The app's code (APK finding) draws its focus frame white for 0,
  green for 1 (focused, locked) and red for 2 (focus failed), and it also tells the camera's S1 lock state from it. That
  fits what we saw (0 at rest, 1 for the whole lock, never 2 or 3) and replaces my guess in run 38 that 1 meant busy. A
  value of 2 has not been seen yet: a click on a plain wall would be the way to try it.
- After run 46 the page's square was changed: it jumps to the clicked cell at once, stays white while the camera has not
  focused, turns green on `0xD209` = 1 and red on 2, and the page reads the camera four times a second now. Run 47 tried
  it on the camera: white and green work, green comes late, red was not seen (see "Green delay and AF-C").
- The preview stuttered for the first few seconds of run 46. Earlier runs also showed dips (24 to 27 fps, and 16.6 fps on
  the first client). The page now also reads the camera's property list twice a second, which might add to it. Not measured.

Public sources read after run 39 (2026-10-05, listed in `docs/references.md`, nothing copied): none says what `0x9026` takes.
The Go package `mikefsq/ptp/fuji` only names it. On USB (X-T3, X-T5) autofocus is a half press: `0xD208` = `0x9300` then
`InitiateCapture`, poll `0xD209` (1 busy, 2 ok, 3 failed), then release. Our `0xD209` stayed at 1 for the whole lock. The
X-A5 answered `0x200A` for `0xD208` over Wi-Fi (2026-10-04), so `0x9026` may be its Wi-Fi form of the half press. A
libgphoto2 issue in a fork says Fuji sets the point by a grid index (`0xD347`, grid `0xD025`), which is not confirmed on
this camera. The Go package lists focus mode `0x0001` as manual focus, which would stop the camera hunting. Writing
`0x500A` on the X-A5 is not tried.

## Green delay and AF-C (run 47)

The owner's account of the coloured square:
- **Green came 1 to 2 s after the click, the camera's beep about 0.5 s after it** (the owner's estimate). The log fits the late
  green: `0xD209` turned 1 between 0.7 and 1.7 s after the lock was sent, and a click let go within about 0.7 s never
  reached 1 (the release cancelled the focus first). Our own reading added up to 0.25 s (property list) plus up to 0.25 s
  (page), so the property seems to lag the beep, but how much of the delay is our reading rate is not known. Not known
  either whether the beep is the camera's "focus found" signal.
- **One lock does not follow a moving subject in AF-C.** The owner held Space, the Focus button and the mouse while moving
  the camera, and the lens stayed where the first lock put it. One `0x9026` looks like one focus action whatever the AF mode
  (`0x500A` reads the same in AF-S and AF-C, runs 18 and 19). The S1 code of the official app (APK finding) has no AF-C case
  that I found.
- Not reported: red, a click on a plain wall, the stutter. Red (`0xD209` = 2) has still never been seen.
- The camera started the session with its focus point at column 4, row 5, not the centre: it remembers the last point.

Changes after run 47 (the library and the page read the camera ten times a second, was four; the page sends "down" again
every second while a key or the mouse is held and the library sends `0x9026` again each time; the 10 s watchdog counts from
the last "down") were tried in run 48:
- **A repeated lock makes the lens follow.** The owner moved the camera and the lens refocused. The camera answered every
  repeat `0x2001`. The price: the preview stutters while the camera focuses, and with a repeat every second it focuses nearly
  all the time. The page now repeats every 2 s and takes `?every=1` or `?every=3` in its address (seconds), one repeat at a
  time. Fake camera and page script only. Not tried on the camera.
- **Why green comes late, from the log.** While the camera focuses it answers the property-list read (`0x1015`) only after
  0.6 to 2.5 s, and `0xD209` showed 1 in the same read. The lock itself is answered at once. So the delay is the camera's
  answer time, and reading faster does not help. Not tried: reading `0xD209` alone (`0x1015` with that property) during the
  focus, which might be answered sooner.
- **`0xD209` did not go back to 0 on a repeat.** It stayed 1 from the first green until the release, even when the repeat
  refocused. So it is "locked", not "focused right now".
- **The session ended by itself.** After the last release (a lock at the centre cell that never turned green, let go after
  0.9 s) the camera sent no live-view frame for 5 s, then did not answer the close. The owner saw the camera show its normal
  live preview afterwards, not the black screen of every earlier session. The owner pressed nothing on the camera. It may be
  the repeated locks (17 locks for 4 releases, never seen before), or something else: one run only. If it comes back
  with the 2 s repeat, the repeats are suspect. **Idea, not tried:** the black screen after a session may come from how we
  close (`0x1018`, `0x1003`), since a session the camera ended itself left no black screen. Closing the sockets without them,
  on purpose, would show it.
- `serve` does not say when its reading thread stops: it ends silently on the first error. Not changed.

Run 49 (the page repeats every 2 s, `?every=1` and `?every=3` tried in one session):
- **The interval sets how fast the lens follows:** 1 s fastest, 3 s slowest (owner). Which one stutters least was not reported.
  The default stays 2 s.
- **Green is closer to the beep.** The log agrees only in part: 4 of 15 holds turned green within 0.7 s, the others took 0.9
  to 5.4 s, and 54 of 461 property reads still took over 0.3 s. Whether the rest is a camera that is slow to focus or slow to
  report is not known.
- **The drop of run 48 did not come back** (one 120 s session, 23 holds, the same repeated locks), so it is not shown to
  come from them.
- **The black screen came back after this normal close**, and run 48's session, which the camera ended itself, left the
  live preview. That fits the idea that our close (`0x1018`, `0x1003`) leaves the black screen, but it is two sessions.
  Still not tried on purpose.
- Red was not seen again.

## Postview (run 50)

**`0x9022` returns the picture just taken, small and at once.** Sent with no parameters after a shot, it answered `0x2001` with
a JPEG of 640 x 480 (42 751 bytes) in 0.04 s, against 1.2 s for the 6 MB file through the download path. I looked at it: it is
the scene the shot was aimed at, with black bars at the top and bottom (the 3:2 picture inside a 4:3 frame, like the live
view). The picture was out of focus because no focus lock was sent before the shot.
- **It can be read once.** The second call, a moment later, answered `0x2001` with no data. Before any shot the answer was
  also `0x2001` with no data. So a client has to call it right after each shot and keep the bytes.
- Only tried right after `CaptureComplete`. Not known: whether it works earlier (right after `InitiateCapture`), and how long
  after the shot the picture stays available.
- It uses no download, so it does not switch the camera to image view (the step that cannot be undone in a session).
  Downloading afterwards was not tried in this run.
- The shot left one picture on the SD card.
- **Run 51 put it in the library and the command line** (`Camera.postview()`, `fuji-xa shoot --postview`). One shot, the
  postview (42 331 bytes, 0.03 s), then the download in the same session: the download still worked and the postview was
  the same picture, checked side by side with the 6000 x 4000 file shrunk to the same size. So a client can show the shot
  within a fraction of a second and fetch the full file later. This run did not put the postview on the `serve` page.
- **Run 52: three shots in a row.** A postview after each of three shots, all answered, each matching its own shot. A
  quick second or third shot still answers busy first (`0x2019`), and the postview was read only after the shot's
  `CaptureComplete`, so the busy answer did not touch it. Then all three downloaded (handle 1 is the newest, so the file
  names come in reverse shot order). Not tried: the postview of a shot taken while the previous one is still being written.
- **Run 54: shot, postview, shot, postview, end.** Both postviews came back, the second shot was not answered busy this time
  (in runs 50 to 52 shots 2 and 3 were), and the session ended without a download. Whether the postview read in between
  is what avoids the busy answer, or the pause it adds, was not isolated: one run.
- **Can the postview size be changed? Not known.** `0x9022` takes no parameter, and the official app has no setting for it
  (its receive buffer is a fixed 12 MB). The postview has the live view's size, 640 x 480 with bars. libgphoto2 lists a
  16-bit property `0xD174`, "live view size", with 1 = XGA, 2 = VGA and 3 = QVGA, for USB cameras (X-T3). It is not in the
  X-A5's change list. **Run 53 read `0xD174` and `0xD173` on the X-A5: both answered `0x200A` (not supported).** So there
  is no known way to change the postview size. It stays 640 x 480. A larger picture quickly would mean the download (6 to
  8 MB in about 2 s). The thumbnail operation `0x100A` was not tried.

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
