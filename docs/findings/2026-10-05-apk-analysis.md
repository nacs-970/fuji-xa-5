# Camera Remote APK analysis (plan 05), 2026-10-05

Plan: [05](../plans/05-apk-static-analysis.md). Question asked: how does the official app choose a focus point, and what
does vendor operation `0x9026` take? Written in our own words from decompiled Java. The decompiled output stays in
`artifacts/` (git-ignored, on `/media/d`) and nothing from it is pasted here. The same person (the agent) read the code and
wrote this note, as `docs/legal-and-clean-room.md` asks us to say.

## What was analysed

| Item | Value |
|------|-------|
| Package | `com.fujifilm_dsc.app.remoteshooter`, taken with `adb pull` from the owner's own phone (USB debugging, one `base.apk`, no splits) |
| Version | 4.10.2 (build 4.10.2.0), versionCode 48, minSdk 21, targetSdk 35 |
| File | `base.apk`, 18 524 661 bytes, SHA-256 `6baf3448100331f9e2083b9b1a5ccd75db79635e076ac5ab9792ca5afee9944c` |
| Tools | `adb` 1.0.41, `jadx` 1.5.6 (Arch `extra`) on Java 27, `readelf` and `strings` on the native libraries |
| Output | 59 MB, 4 652 Java files, in `/media/d/fuji-xa-5-artifacts/camera-remote-jadx` (linked from `artifacts/`) |

## Where the protocol lives

The Wi-Fi protocol is in native code. The APK carries `libFTLPTPIP.so` (the PTP/IP part, 249 KB for arm64) and `libFFIR.so`
(448 KB). The Java class `photo_receiver/ControlFFIR` is a thin wrapper that calls about 55 native functions, among them
Init, Open, Close, GetDeviceInfo, GetDevicePropDescAll, GetDevicePropValue, SetDevicePropValue, InitiateOpenCapture (and a
two-phase form), TerminateOpenCapture, InitiateCapture, InitiateMovieCapture, LockS1Lock, UnlockS1Lock, StepFnumber,
StepShutterspeed, StepExposureBias, StartZoom, StepZoom, StopZoom, GetThroughPicture, GetPostview, ReadImage, ReadThumbnail
and SetGPSInfo. So the Java side shows the call surface and the order of calls, not the bytes on the wire. Only port 55740
appears as a constant in the Java (`ControlFFIR`, `MainActivity`, `BTManagerService`).

## Focus: what the app does (read from `FinderView`, `CameraControlActivity`, `RemoteAPICall`)

- The app calls property `0xD17C` (53628) **S1 lock**. Our name "focus point position" came from watching it change.
- Its four bytes are: picture aspect width, picture aspect height, column, row. For the X-A5 the first two bytes are `03 02`,
  which is **3:2**, the aspect of the 6000x4000 picture. That answers the open question about the high bytes in
  `docs/protocol/wifi.md`.
- The app reads the property's current value and its maximum. The maximum holds the grid size as columns and rows (we saw a
  13 x 7 grid), so the app does not hard-code the grid. We cannot read the maximum because `GetDevicePropDesc` is refused.
- A tap on the live view becomes a cell: column and row counted from 1, in the grid laid over the picture. The app only
  accepts taps in cells that are valid for the current AF area mode (property `0xD245`, the app calls it AF select mode;
  our list reads 2).
- **Touch focus is `LockS1Lock` with one integer made from those four bytes** (aspect width, aspect height, column, row, in
  that order, as one 32-bit number). The app builds it from hex strings and reads it back with radix 16, which gives the
  same layout as `0xD17C`. Letting go is `UnlockS1Lock` with no argument, which matches what we sent in runs 38 to 43.
- Property `0xD209` (53769) is the **S1 lock colour**: the app draws the focus frame white for 0, green for 1 (focused) and
  red for 2 (focus failed), and treats 1 as the camera having locked focus. libgphoto2's "AF status" name for it comes from USB.
- The native names are `FTL_PTP_LockS1Lock` and `FTL_PTP_UnlockS1Lock`. Which PTP operation they send, and whether the
  integer travels as a PTP parameter or in a data phase, is **not known**: that is native code, not read.

## Other findings

- **Model flags** (`assets/json/CAMERA_INFO.json`): the X-A5 is flagged for remote shooting, photo receiving, photo viewing,
  reserved photo receiving, GPS assist and date and location sync. Remote release (Bluetooth shutter) and remote firmware
  update are off for the X-A5. The X-A7 has remote release on.
- **Step functions.** The app changes F-number, shutter speed and exposure bias with `StepFnumber`, `StepShutterspeed` and
  `StepExposureBias`, not by writing an absolute value. That may be why our direct writes to `0x5007` and `0xD240` were
  refused (runs 21 and 22). Not tested. The same goes for the zoom functions.
- **`GetDevicePropDescAll`** is a separate native call. It may be how the app learns ranges, since the standard
  `GetDevicePropDesc` is refused. Not tested.
- The property numbers in the app's list match ours where we have both: ISO `0xD02A`, film simulation `0xD001`, focus mode
  `0x500A`, exposure `0x5007`.

## Function modes (read from `CameraConnectActivity` and `CameraControlActivity`)

The app's `SetFunctionMode(n)` is our client state `0xDF01`: 5 and 11, the two values we set, are among its arguments.
The app's own log texts (Japanese) say what each value is for:

| Value | Meaning in the app |
|-------|--------------------|
| 5 | remote mode (live view and shutter): what we call remote mode |
| 11 | set from the remote screen when it moves to viewing pictures: what we call image view |
| 1 and 8 | photo receiver: the camera sends one or several pictures to the phone (8 is the "version 1.2" form) |
| 2 and 9 | camera viewer: browse the camera's pictures from the phone (9 is the "version 1.2" form) |
| 7 | sent when the camera reports an unknown mode, right before the app closes the connection |

The native code confirms it: `SetFunctionMode` writes property `0xDF01` and `SetCameraFunctionMode` writes `0xDF00`.
`SetCameraFunctionMode(6)` is what the app sends on the way to the camera view, and our image view also sets `0xDF00` = 6.
We read 16 in `0xDF01` right after OpenSession (run 16); the app has no name for it in the code we read.
Value 7 is the only one that looks like an "abort and leave" notice. Whether it also avoids the black screen and the dead
buttons after a session is not known and not tried: the app uses it only on its error path, then closes.

## Native analysis: five functions disassembled (owner approved, 2026-10-05)

The owner approved reading five short functions of `libFTLPTPIP.so` (arm64) with `llvm-objdump`, which is already
installed. The listings stay in `/media/d/fuji-xa-5-artifacts/disasm/` (git-ignored, not copied here). Each function builds
one PTP operation through the same generic send routine. What they send, in our words:

| App function | Operation | Parameters | Data phase |
|--------------|-----------|------------|------------|
| `FTL_PTP_LockS1Lock` | `0x9026` | **one 32-bit parameter**: the integer from Java (aspect width, aspect height, column, row) | none |
| `FTL_PTP_UnlockS1Lock` | `0x9027` | none | none |
| `FTL_PTP_StepFnumber` | `0x902D` | one 32-bit parameter | none |
| `FTL_PTP_StepShutterspeed` | `0x902C` | one 32-bit parameter | none |
| `FTL_PTP_StepExposureBias` | `0x902E` | one 32-bit parameter | none |

- Each function also takes a last argument that goes to the send routine as its final argument. It is probably a timeout.
  That is a guess and it is not part of the message.
- The Java side passes **0 or 1** to the three Step functions (the on-screen minus and plus buttons). Which value steps up
  and which down is not known.
- So `0x9026` with no parameter, which we sent in runs 38 to 43, was a lock without a point (the camera moved the point to the
  centre). With the parameter it focuses at the chosen cell: tried, it works (runs 45 and 46).
- The Step operations may be the way to change F-number, shutter speed and exposure bias, because our direct writes
  were refused. Not tried.

## Native analysis: all other functions (owner: "Disassemble all finding", 2026-10-05)

The same method for the rest of the exported `FTL_PTP_*` functions of `libFTLPTPIP.so` (arm64): a small script read the
operation code that is loaded before the call to the generic send routine, the data direction and the parameter count.
"Not read" means the script could not find the parameter count, not that there is none. Listings: `/media/d/fuji-xa-5-artifacts/disasm/`.
Not disassembled at first: `FmSendObject`, `FmSendObjectInfo`, `FmSendPartialObject` (read later, see "The firmware functions"),
`GetDeviceInfo` (a large parser) and `VendorExtensionOperation` (a generic hook).

| App function | Operation | Parameters | Data |
|--------------|-----------|------------|------|
| `GetDevicePropDescAll` | **`0x902B`** | not read | reads data in (all property descriptions) |
| `GetDevicePropDesc` (and the `_Int`, `_Str` forms) | `0x1014` | not read | reads data in |
| `GetDevicePropValue` (property list form) | `0x1015` | not read | reads data in |
| `ResetDevicePropValue` | `0x1017` | 1 (the property) | none |
| `InitiateOpenCapture`, `InitiateOpenCapturePhase1` | `0x101C` | 2 | none |
| `TerminateOpenCapture` | `0x1018` | 1 | none |
| `InitiateCapture` | `0x100E` | 2 | none |
| `CancelInitiateCapture` | **`0x9030`** | not read | none |
| `InitiateMovieCapture` | **`0x9020`** | 2 | none |
| `TerminateMovieCapture` | **`0x9021`** | 1 | none |
| `OpenSession`, `CloseSession` | `0x1002` (1 parameter), `0x1003` | | none |
| `GetNumObjects`, `GetObjectHandles` | `0x1006`, `0x1007` | 2 each | |
| `GetObjectInfo`, `GetObject`, `GetThumb`, `GetPartialObject` | `0x1008`, `0x1009`, `0x100A`, `0x101B` (3 parameters: handle, offset, size) | | reads data in |
| `GetStorageIDs`, `GetStorageInfo` | `0x1004`, `0x1005` | | reads data in |
| `DeleteObject` | `0x100B` | 1 | none (it deletes a picture: we never send it) |

What follows from it:
- **`0x902B` is how the app gets every property description at once**, with ranges and allowed values, instead of the
  standard `0x1014` that our camera refuses. We never sent `0x902B`. It is a read, so it is the safest next probe, and it
  should show the grid size behind `0xD17C`, the allowed values and which settings can be written.
- **Movies:** start is `0x9020` (2 parameters) and stop is `0x9021` (1 parameter). Not tried. What the two parameters are
  is not known.
- **`CancelInitiateCapture`** is `0x9030`, probably what the app sends to abort a shot. Not tried.
- **The app ends a session the way we do.** Its close stops the property polling, sends `TerminateOpenCapture` if live view
  runs, then `CloseSession`. The native close writes no function mode. So a different closing operation does not explain
  the black screen after a session. (The Java side only sends mode 7 on its error path.)
- `GetThroughPicture` is not a PTP operation: it hands over live-view frames that a receiver thread has read from the
  video port. The format of the 18-byte frame header is not decoded here (that code is in the receiver thread, not read).
  The next camera run records the headers to see which bytes change.
- The `OpenSession` wrapper also calls `CloseSession`, perhaps to clear a session left open. Not confirmed.

## More native functions, and the firmware functions (owner: "disassemble the forbidden one too", 2026-10-05)

Reading only, nothing sent to the camera. The listings stay in `/media/d/fuji-xa-5-artifacts/disasm/` (git-ignored).
`libFFIR.so` builds some operations itself and not through the `FTL_PTP_*` functions, so a scan of both libraries for
operation codes in `0x9000` to `0x90ff` found these (the full table is in the [protocol notes](../protocol/wifi.md), section 6):
`0x9022` GetPostview (no parameters, data in), `0x9023` to `0x9025` zoom (step, start, stop), `0x9040` to `0x9042` firmware.

**The firmware functions.** `FmSendObjectInfo` is `0x9040`, `FmSendObject` is `0x9041` and `FmSendPartialObject` is `0x9042`.
"Fm" is firmware: the Java class that calls them is the app's firmware-update screen. Its order is: set the client state
`0xDF01` to 19, read and write the version property `0xDF27` (value 1), send the object info (the file name `FUP_FILE.DAT`
and its size), then the file in pieces. We never send these, and AGENTS.md now lists them. The app's model list marks the
X-A5 with "remote firmware update: no" and "remote release: no" (the second matches what we found: no shutter by Bluetooth).

**What we can change, from the code.**
- **Our start already matches the app.** After the client state it reads the remote version `0xDF24` and writes `0x2000C`
  (131084), the same value the app uses when its model list has no entry for the camera, which holds for the X-A5. So a
  missing version handshake is not what leaves the buttons dead or the screen black.
- **Postview (`0x9022`)** could show the shot at once without downloading the 6 MB file. A read, not tried.
- **The step operations** act on the shutter speed `0xD240`, the F-number `0x5007` and the exposure bias `0x5010`. The
  Java side sends 0 for the left button of the app's ring and 1 for the right one. Whether right raises the value is not
  known: a test reads the property before and after.
- **Zoom** (`0x9023` to `0x9025`) with two parameters for step and start. Only useful with a power-zoom lens. Not tried.
- **Movies** (`0x9020`, `0x9021`): the Java side passes nothing, the native code gets its two parameters from a stored
  setting. The "movie" and "still" modes appear as the values `0x6011` and `0x6001` inside the app. Not tried, writes to the card.
- Focus lock: no AF-C case in the app's S1 code. When the colour property turns 1 the app only records that the camera is
  locked, so our repeat-the-lock approach (runs 48 and 49) is our own, not the app's.

## Open questions

1. ~~Whether `0x9026` with the parameter really moves the focus to the cell~~: it does (runs 45 and 46). Still open: what the camera answers if the cell is outside the valid area for the AF mode (the page refuses cells outside the 13 x 7 grid before sending).
2. Which of 0 and 1 steps up for the three Step operations, and what each step changes (a stop, a third of a stop).
3. What `0x902B` returns on the X-A5 and what its parameters are (the app code that sets them is not read).
4. What the two parameters of `0x9020` and the parameter of `0x9021` are, and whether the X-A5 records movies this way.
5. What the live-view frame header carries (recorded in the next camera run).
