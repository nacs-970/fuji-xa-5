# Fuji Wi-Fi remote protocol as the X-A5 uses it

Clean-room notes in our own words. Camera: Fujifilm X-A5, firmware 1.21. Everything marked **observed** was
seen on this camera on 2026-10-04 with our scripts (`scripts/`), and the evidence is in
[the remote-mode finding](../findings/2026-10-04-wifi-remote-mode-probe.md) and the
[handshake](../findings/2026-10-04-wifi-gphoto2-handshake-failure.md) and
[session](../findings/2026-10-04-wifi-session-probe.md) findings. **Inferred** means taken from public notes
about other bodies and not checked here. **Not known** means we have no answer.

All integers are little-endian. "Container" means a USB-style PTP container.

## 1. Network

| Item | Value | Status |
|------|-------|--------|
| Access point | Open (no password). Name starts with `FUJIFILM-`, then the model, then four digits | observed |
| When it exists | Only while the camera shows its WIRELESS COMMUNICATION screen. It disappears when the camera sleeps or the session ends | observed |
| Camera address | `192.168.0.1`. The camera is the DHCP server and gives the client an address in a /16 network | observed |
| Control port | TCP 55740, open as soon as the access point is up | observed |
| Event port | TCP 55741, refuses connections until InitiateOpenCapture succeeds | observed |
| Live-view port | TCP 55742, same rule | observed |

Practical notes (observed): the access point can take several scans to appear, and the control port opens a few
seconds after the camera answers ping. Connections within about 10 s of an accepted one often time out. Open the
wireless screen on the camera, join, run one session, leave.

## 2. Control connection handshake (TCP 55740)

The client sends one 82-byte Init Request. The camera answers with an Ack (accepted) or Fail.

Init Request (82 bytes):

| Offset | Size | Field | Status |
|--------|------|-------|--------|
| 0 | 4 | length = 82 | observed |
| 4 | 4 | packet type = 1 | observed |
| 8 | 4 | magic `0x8F53E4F2` | observed |
| 12 | 16 | client GUID, see the rule below | observed |
| 28 | 54 | client name, UTF-16, zero padded | observed |

Init Ack (68 bytes): length 68, type 2, a 4-byte index, the camera's 16-byte GUID, then the camera name as
UTF-16 padded to 40 bytes (the name was `X-A5`). Observed.

Init Fail (12 bytes): length 12, type 5, a 4-byte reason. Reasons seen: `0x201D` (invalid parameter). The
public notes also name `0x2019` (device busy). Observed for `0x201D`.

**GUID rule (observed).** The camera accepts a GUID only if its first 12 bytes match the prefix
`ada5485d87b27f0bd3d5ded0`, which is the value used by the public tool `fuji-cam-wifi-tool`. The last four bytes
may be zero or random. A random GUID and a different fixed GUID were both rejected with `0x201D`.

**Client name (observed; the explanation is the owner's theory and fits every run).** The camera seems to
accept only the client name it registered last. On 2026-10-05 the owner reopened the wireless screen without
pressing "change" on the camera. The name `fuji-xa` was then refused with `0x201D` on 10 tries in two runs,
while `xa5-probe`, the name used before, was accepted at once. In a later run the owner pressed "change" on the camera first (in the owner's words, to let any device
connect) and then OK to confirm the transfer. `fuji-xa` was accepted on the first try with no refusal. The packets differ only in the name.
Not tested: whether `xa5-probe` is now refused without "change" (the theory says yes). Not tested: whether OK alone, without "change", would also work. The earlier handshake tests (2026-10-04) accepted both `xa5-probe` and `CameraClient`
within an hour. Whether the owner pressed "change" between them was not recorded, so that does not contradict
the theory. A client should say, when refused, that the camera may expect its last name or a "change" on the
camera.

**Open point.** One run with the accepted prefix was rejected (`0x201D`), and runs a minute later were
accepted. The cause is not known. The camera also showed a name and a "transmit OK?" style prompt on its screen
at times, and the owner pressed OK. Retrying the init up to four times (waiting 0, 1, 2, 4 s) costs nothing.

**Do not send the init packet twice on one connection.** After the Ack, a second init on the same socket makes
the camera answer with Session Not Open. This is why libgphoto2's Fuji driver fails (observed).

After the Ack, wait about 50 ms before the first command (inferred, harmless).

## 3. PTP over the control connection

After the Ack the socket carries ordinary PTP containers, as on USB:

`u32 length (all bytes), u16 type (1 command, 2 data, 3 response, 4 event), u16 code, u32 transaction id, then
parameters (u32 each)`.

Transaction ids start at 1 and count up. `OpenSession` (`0x1002`, parameter 1) works at once and returns
`0x2001`. `GetDeviceInfo` over Wi-Fi returns the same list as over USB: 25 operations, 7 events and 8
properties, with no capture operation listed (observed). The camera still accepts `0x101C` and `0x100E`.
Do not rely on DeviceInfo to find what the camera can do.

Never send the Fuji operations `0x900C`, `0x900D` or `0x901D`. They write firmware files.

## 4. Fuji state properties and the event list

Properties are read with `GetDevicePropValue` (`0x1015`) and written with `SetDevicePropValue` (`0x1016`, data
phase of 2 or 4 bytes).

**Event list, property `0xD212` (observed).** A read returns a list of properties that changed:
`u16 count`, then `count` entries of `u16 property code, u32 value`. An empty list is the two bytes `00 00`.
Poll it as a substitute for events on the control connection.

| Property | Meaning | Values seen on the X-A5 |
|----------|---------|-------------------------|
| `0xDF00` | camera state | 6 at the start of every session (remote access). After setting client state 11 it reads `0x0B`, meaning not known |
| `0xDF01` | client state, set by the client | read 16 (`0x10`) right after OpenSession, before we set it (run 16). We set 5 (remote mode) and 11 (image view). Both accepted |
| `0xDF21` | image-get version | 3 |
| `0xDF22` | get-object version | 3 |
| `0xDF24` | remote version | read `0x20003`. We set `0x2000C` (the value from public notes). Accepted |
| `0xDF25` | remote get-object version | read 1. We set 5 before image view. Accepted |
| `0xD222`, `0xD220`, `0xD401` | picture count (see section 8) | 0, 1, 2, 3 across our shots |
| `0xD229` | picture counter, name from public notes ("capture remaining") | falls by one a few seconds after a shot. Starting values near `0xB81`. After InitiateOpenCapture it reads `0x281` lower |
| `0x5007` | F-number | `0xAA` at f/1.7 and `0x168` (360) at f/3.6 (run 19): the value is the f-number times 100. A write of `0x118` (f/2.8, 2 bytes) answered `0x200F` and changed nothing (run 21). `GetDevicePropValue` returns `0xF018` for it, not `0xAA`: not understood |
| `0x5005` | white balance | 2 while the owner's setting was auto |
| `0xD001` | film simulation | `0xB` for Classic Chrome (run 18), 1 for Standard/Provia (run 19) |
| `0xD02A` | ISO | `0x640` (1600) for ISO 1600 (run 18). `0x80000C80` for ISO Auto3 (run 19): the top bit may mean auto and the low part 3200 (`0xC80`) may be the auto limit or the chosen ISO. Not known which |
| `0xD240` | shutter speed | `0x80030D40` for 1/200 (run 18), `0x8000EA60` for 1/60 (run 19) and `0x8007A120` for 1/500 (run 20, set by the owner). and `0x800186A0` for 1/100 (run 21, set by the owner). All fit: low part = denominator x 1000 (200000, 60000, 500000, 100000). In run 19 the owner had set 1/100 on the camera (dial on M) and the screen showed 1/60 after the session. Who changed it is not known. Four data points, fractions of a second only. The top bit was set in all three and is not understood. In run 20 the screen showed 1/500 before and after the session, so the session does not change the speed |
| `0x500A` | focus mode (name from standard PTP) | `0x8001` with the owner's camera set to AF-S (run 18) and to AF-C (run 19). It does not tell them apart |
| `0x500C` | flash mode | 2 while the built-in flash was closed (it must be popped up by hand on this camera). In standard PTP 2 is flash off |
| `0x500E` | exposure mode | 1 with the mode dial on M in runs 18 and 19 (the owner first said auto, then corrected it). In standard PTP 1 is manual, which fits. One value only |
| `0x5010` | exposure bias (name from standard PTP) | 0. The owner did not give the camera's setting |

Setting `0xDF01` = 5 took between 0.3 s and 5.4 s. The camera may wait on its own screen for the user to confirm.
Set timeouts of 60 s.

The settings rows above (`0x5007`, `0x5005`, `0xD001`, `0xD02A`, `0xD240`) come from the change list that
`0xD212` returns after remote mode starts (run 18). Each was matched to one value the owner read on the camera
screen (all but `0x5010`), so one data point each. `GetDevicePropDesc` (`0x1014`) does not give the allowed values over Wi-Fi: the
standard properties answer `0x2007` and the Fuji ones `0x200A`. `GetDevicePropValue` (`0x1015`) answers `0x2001`
for `0x5007` (run 21), but with a different number than the change list. Writing `0x5007` was refused with `0x200F` and writing `0xD240` (4 bytes) with `0x2007`, both with live view running
and the dial on M (runs 21 and 22). Both left the value unchanged. Writing the other settings is not tested.

Properties from the libgphoto2 capture sequence (`0xD207`, `0xD208`, `0x500D`) answer `0x200A` (not supported)
on the X-A5. Do not use them.

## 5. Remote mode and live view

Sequence (observed, 1 to 2 s in total):

1. Init, `OpenSession`.
2. Read `0xD212` until `0xDF00` is not 0 (it was 6 at once).
3. Set `0xDF01` = 5. Read the events again.
4. Set `0xDF24` = `0x2000C`.
5. `InitiateOpenCapture` (`0x101C`, parameters 0, 0). Returns `0x2001` in about 0.6 s. Remember this
   operation's transaction id.
6. Connect TCP 55741 and 55742. No handshake is needed on either. The camera sends data right away.
7. Read live-view frames and drain them continuously. If the client stops reading, the camera is blocked.
8. Finish with `TerminateOpenCapture` (`0x1018`, parameter = the transaction id from step 5), then
   `CloseSession` (`0x1003`).

**Live-view frame, TCP 55742 (observed).** An 18-byte header, then a JPEG:

| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | total frame length, header included |
| 4 | 4 | zero |
| 8 | 4 | frame counter (the first frame we read had 5) |
| 12 | 6 | zero |
| 18 | n | JPEG data, 640x480 baseline, picture has black bars (3:2 picture in a 4:3 frame) |

About 60 frames per second. A frame with the lens cap on is about 6.6 KB, a normal scene about 11.4 KB. The
`fe 7f` marker named in public notes was not present.

## 6. Shutter

With open capture running, send **one** `InitiateCapture` (`0x100E`, parameters 0, 0). It returns `0x2001`
at once (observed, three runs). No focus step is needed. The camera runs its own autofocus on this command, with
the focus mode and focus point set on the camera. With the point on the centre and the wall 60 cm away, the wall was
sharp and a toy 15 cm from the lens was soft (too close to focus). The owner heard the lens move before the shutter
sound (run 13). Focus control from the PC is not known.

After the command the camera sends events on TCP 55741. Each event is a 28-byte container: length 28,
type 4, code, transaction id (1), four u32 parameters, the fourth always 0 (observed). Read the container by
its length field. The first three parameters:

| Delay after the command | Event code | Parameters |
|-------------------------|-----------|------------|
| 1.5 to 2 s | `0xC004` (Fuji ObjectAdded) | `0x0E`, `0x0E`, 0 |
| about 2.5 s | `0xC001` | `0x0E`, `0x0E`, a changing value. Meaning not known |
| about 3.5 s | `0x400D` (PTP CaptureComplete) | `0x0E`, `0x0E`, 0 |

The first parameter is not the handle to download (see section 8). The picture is written to the SD card, and
the camera makes its shutter sound.

**Device Busy (observed 2026-10-05).** A second `InitiateCapture` right after a completed shot (after the
`0x400D` event) answers `0x2019`. Retry every 0.5 s: one retry was enough in four cases. HIGH PERFORMANCE on
or off made no difference. Take several shots in a row in live view, then download.

The camera screen is black while the session is open, with the LED blinking. The owner saw this after shots
with and without a download, and also when the connection started, before any shot (owner reports
2026-10-04 and 2026-10-05). A half-press wakes it. HIGH PERFORMANCE off does not change this. A 30 s run with
live view only (no shot, no download) showed the same: black with the LED blinking from the start of the
connection to its end. So it is the camera's state during a Wi-Fi remote session, not an effect of the
shutter or of a download (observed 2026-10-05).

## 7. Ending a session

`TerminateOpenCapture`, then `CloseSession`, then close the sockets. After the client leaves the Wi-Fi, the
camera shows "connection lost" and returns to its shooting screen. The owner must open the wireless screen
again before the next session (observed, normal).

After a session the screen stays black once the PC is back on its own network, and a firm press of the shutter
button brings the live view back. The camera plays its "ready" sound after the LED goes off. The owner saw this
after a shot with a download (runs 12 and 13) and also after a live-view-only session of 5 s with no photo and no
image view (run 14). So image view is not the cause. After a live-view-only session (run 15) the owner waited about
30 s: a light button (Q) and every other button did nothing, and only the shutter button brought the live view back.
So it is not a sleeping screen. Writing `0xDF01` back to its start value (16) before CloseSession did not help: the
shutter button then did not work either, and the camera had to be switched off and on (run 17). Do not do that.
The cause is not known. The owner's view is that it is camera behaviour: over USB the camera also only opens its
memory and does not return to the shooting mode itself. Press the shutter button once after a session.

## 8. Reading pictures

Remote mode does not expose the picture list. Switch the same session to image view:

1. `TerminateOpenCapture` if live view is open, then close the 55741 and 55742 sockets and wait 0.5 s.
2. Read the events. Set `0xDF00` = 6. Read the events twice.
3. Set `0xDF01` = 11. Read `0xDF25`, set it to 5. Read the events.
4. The event list now holds `0xDF00` = `0x0B` and `0xD222` = the picture count.
5. `GetObjectInfo` (`0x1008`, parameter = handle).
6. Set `0xD227` = 1 (from public notes, effect not tested here).
7. `GetPartialObject` (`0x101B`, handle, offset, size) in chunks of up to 1 MiB, until the size from step 5.
8. Set `0xD227` = 0.

All observed to work, including the switch from remote mode to image view in one session.

**Image view is one way (observed 2026-10-05).** Going back from image view to remote mode in the same session
failed: setting `0xDF01` = 5 was accepted after about 3 s, and then the camera closed the control connection.
Take all shots first, then download.

**Handles (observed).** Handles start at 1 and **handle 1 is the newest picture**, handle 2 the next older, and
so on up to the count. Handle 3 answered `0x2007` when the count was 2. After three new shots, handles 1, 2 and 3 were those three
pictures, newest first, and three downloads in one session worked (observed 2026-10-05).
`GetNumObjects` (`0x1006`) returned 0 every time and is not usable.

**Count.** `0xD222` read 0, 1, 2, 3 across our shots, so it grows by one per picture. It did not include a
picture the owner took earlier with the lens cap on, so it is not the total on the card. What it counts is not
known.

**ObjectInfo layout (observed).** The camera returns the standard PTP dataset: storage id (u32 at 0), format
(u16 at 4, `0x3801` for JPEG), protection (u16 at 6), compressed size (u32 at 8). The file name is a PTP string
at offset 52: one byte with the character count, then UTF-16.

Speed: about 5 MB/s. A 6 to 7 MB full-size JPEG took 1.2 to 1.4 s.

## 9. What is not known or not done

- How to control focus from the PC (a focus point, manual focus), and whether the lens already moves in live view.
- What the `0xC001` event parameter is, and what `0xD222` counts.
- Why one init with the accepted prefix was rejected once.
- The allowed values of the camera settings, and how to set them (ISO, aperture, shutter speed, white balance, film simulation, exposure compensation). Movies, thumbnails.
- Whether other X-A bodies behave the same.
- Whether `0xDF24` = `0x2000C` and `0xD227` are needed on the X-A5 (we always sent them).
