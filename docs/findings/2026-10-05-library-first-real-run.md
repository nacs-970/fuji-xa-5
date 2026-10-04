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

Runs 1 and 2 changed nothing on the camera or the SD card.

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
