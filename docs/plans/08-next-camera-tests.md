# Plan 08: Next camera tests

Status: not started (written 2026-10-05, after run 54). Three tests, in the order of value. Every test is one fresh Wi-Fi join
through `scripts/with_camera_wifi.sh`; the owner reopens WIRELESS COMMUNICATION and says "ready" first. Approvals are named per test.
What is not known yet is listed in [protocol notes](../protocol/wifi.md) section 9.

## Test 1: the Shoot button on the camera

**Question.** Does `fuji-xa serve --shoot` focus at the clicked cell, take the photo and show its postview, and does the photo's
`FocusPixel` land on that cell? Built after run 54 and tested on the fake camera only.

**Needs.** "yes vendor" (focus lock and postview) and "yes shoot" for N photos (say N, 3 is enough).

**Steps.**
1. Aim at a scene with texture in at least three different places (left, middle, right, and one high or low).
2. `scripts/with_camera_wifi.sh -- env PYTHONPATH=src python3 -m fuji_xa -v serve --shoot --seconds 150`, open the page.
3. For each place: click the cell, wait for green, press Shoot. Note what the page shows and how long it took.
4. A second fresh join: `fuji-xa download -n N -d <folder>` (a session that downloads cannot be the live one).
5. `exiftool -p '$FileName $FocusPixel $FocusWarning' <folder>/*.JPG` (check that `exiftool` is installed first). The expected point for column
   c and row r is about x = (c - 0.5) / 13 x 6000 and y = (r - 0.5) / 7 x 4000.

**Reads.** FocusPixel within one cell (about 460 x 570 px) of the expected point and `Good`: the lock carries into the shot. FocusPixel at
the centre for every click: the shot ignores the cell. A failed or busy shot (HTTP 409 or 500 on the page) goes in the findings with the log.
The page also shows whether the postview matches the shot, and whether the lock was let go afterwards (`0xD209` back to 0).

## Test 2: the step operations

**Question.** Do `0x902D` (F-number), `0x902C` (shutter speed) and `0x902E` (exposure bias) change the settings that direct writes could
not change, and which of the parameters 0 and 1 raises the value?

**Needs.** "yes vendor". Changes camera exposure settings, no photo. A scratch script `step_try.py` is to be written first (not yet).

**Steps.** For one operation at a time: read the property (`0x5007`, `0xD240`, `0x5010`; read by `0x1015` if it is not in the change list), send
the operation with 1, read it back after 0.5 s, send 1 again, then 0 twice, then once more to land on the start value, and read at each step. Stop at
the first refusal. The mode dial decides what the camera lets us change, so the owner says the dial position before each run:
A for the F-number, S or M for the shutter speed, P, A or S for exposure bias. Runs 21 and 22 refused direct writes with the dial on M.

**Reads.** The value changes by one step per call and the direction matches the parameter: the step operations are the way to set exposure.
A refusal code (`0x2005`, `0x200F`, `0x2019`, other) or no change goes in the findings with the dial position. The value must be back at the start at the end of the run.

## Test 3: who ends the session, and the black screen

**What is known.** Runs 12 to 15: after a normal end the screen stays black and only the shutter button leaves it. Run 17: writing `0xDF01` = 16
before the close made it worse (power cycle needed): never again. Run 25: closing the sockets without `0x1018` and `0x1003` also leaves it black, so our
closing operations are not the cause. Runs 7, 23, 26 and 48: a session **the camera ends** brings the live view back (in run 26 the buttons stayed dead until a
power cycle; after run 48 they were not checked). Run 49: a normal end, black again.

**Question.** Is there an ending the client can choose that leaves the camera normal, screen and buttons?

**Variants, one per join, no photo.** Each needs "yes vendor", and the owner agrees to a power cycle if the buttons stay dead.
1. `0xDF01` = 7 (the official app's abort notice, which it sends before it closes after an error), then `0x1018` and `0x1003`. Not tried.
2. `0x1018` and then the sockets, without `0x1003` (`end_test.py terminate`, written but not run; low value after run 25).
3. A camera-ended session in live view on purpose. Known triggers: `0xDF01` = 5 again from image view (runs 7, 23, 26: leaves dead buttons), and whatever happened at the end of run 48 (unknown). Only try
   this last, and only if variants 1 and 2 leave the black screen.

**Owner reports after each.** The screen (black or live view), the LED, whether the shutter half-press, Q, Menu and the dials work, and whether the next join works without a power cycle.

**Reads.** A variant that leaves a working live view and working buttons is the ending to use. If none does, the answer stays: press the shutter button once after a session.
