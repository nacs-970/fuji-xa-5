# Plan 03 result: a PTP session over Wi-Fi works on the X-A5 (2026-10-04)

Part of [plan 03](../plans/03-wifi-gphoto2-test.md). Raw logs in `captures/wifi-gphoto2/` (git-ignored):
`2026-10-04-summary-fixedguid-5.log` (libgphoto2) and `2026-10-04-session-probe.txt` (our script).
Each run started with a fresh Wi-Fi join through `scripts/with_camera_wifi.sh` (connect, run once,
reconnect to the previous network). The owner's internet ran over a USB tether during these runs.

## Result 1: libgphoto2 with the fixed GUID gets the ack, then breaks itself

Run: gphoto2 2.5.32, libgphoto2 2.5.34, `--camera "Fuji X (WLAN)" --port ptpip:192.168.0.1 --summary`, with
a temporary HOME whose `~/.gphoto/settings` holds the accepted GUID (the real settings file was not touched).

| Step in the log | What happened |
|-----------------|---------------|
| init request with the accepted GUID | camera replied with an **Init Command Ack** (length 68, type 2, name `X-A5`) |
| immediately after, libgphoto2 sent the **same 82-byte init request again** on the same socket | camera answered with a 12-byte packet: length 12, type 3, code `0x2003`, transaction id `0x8f53e4f2` |
| libgphoto2 | `bad type returned 537067523`, `Failed to connect.` |

Reading the second packet: after the ack the camera speaks USB-style PTP containers. It parsed the second init
packet as a command container with code 0 and the magic number as its transaction id. `0x2003` is PTP
"Session Not Open". The camera is not rejecting the client. libgphoto2 is sending the wrong packet.

Cause in `fujiptpip.c` (`master`, function `ptp_fujiptpip_connect`): the loop is
`do { send init; connect_tries++; read ack; ... } while (connect_tries < 2);`. A successful ack leaves
`connect_tries` at 1, so the loop runs a second time and sends the init again. There is no `break` on
success. The loop was written for the retry-on-Init-Fail case. Cameras that tolerate a second init (the
newer ones libgphoto2 was tested on) would not notice. **Hypothesis for the fix, not yet tested:** leave the
loop as soon as the ack is `PTP_RC_OK`.

So libgphoto2 needs two changes for the X-A5: a GUID that starts with the accepted 12 bytes, and no second
init after a successful ack.

## Result 2: our own script completes a session

`scripts/fuji_session_probe.py` (init with the accepted GUID, wait 50 ms, OpenSession, GetDeviceInfo,
CloseSession):

- Init Command Ack.
- `OpenSession`: response `0x2001` OK. The script allows 45 s in case the camera asks the user to press OK. No
  prompt was reported by the owner, and the script did not time the step, so whether a prompt appeared is
  unknown.
- `GetDeviceInfo`: response OK, 269 bytes. **Identical to the USB result:** same 25 operations, 7 events and
  8 properties. In particular, over Wi-Fi in this default state the camera does **not** advertise
  `0x100e`, `0x101c`, `0x902b` or `0x9022`.
- `CloseSession`: OK.

The DeviceInfo parser of the script was first checked against the 281-byte USB dump from the baseline probe
(25 operations, 7 events, 8 properties, model `X-A5`, version `1.21`) before it was used on the camera.

## What this means

- The X-A5's Wi-Fi protocol is the Fuji variant of PTP/IP that the other projects document, and a plain
  script can open a session on it. The feasibility of remote shooting over Wi-Fi is now supported by an
  observation on this body, not just by other people's code.
- **Advertised operations do not show what remote mode can do.** libfuji uses `InitiateOpenCapture`
  (`0x101c`) to make the camera open the event (55741) and live-view (55742) sockets, even though the
  camera does not list it. The same goes for the earlier USB conclusion: "no capture operation advertised"
  was never proof that capture is impossible there. The Wi-Fi remote-mode sequence is the thing to test next.
- Remaining steps in libfuji's flow, from its source (public, MIT): read the camera's event list until the
  camera is not in "wait for access" state, read some version properties, set the camera-state property
  `0xdf00` and the client-state property `0xdf01` (remote mode), set a remote-version property, call
  `InitiateOpenCapture`, then connect to ports 55741 and 55742.

## Next experiment (needs the owner's go-ahead)

A `scripts/fuji_remote_probe.py` that follows the libfuji sequence up to the live-view socket:

- Read-only first: event list, version properties.
- **Changes camera state:** `SetDevicePropValue` on `0xdf00`/`0xdf01` and `InitiateOpenCapture`. This is what
  the official app does on connect. It is a mode switch, not a write to the card. It does not take a photo.
- Read a few live-view JPEG frames from 55742, save one to `/tmp`, stop with `TerminateOpenCapture`.
- Taking a photo is a separate step, asked for on its own.

If the camera locks up, power-cycle it (remove and reinsert the battery if needed).
