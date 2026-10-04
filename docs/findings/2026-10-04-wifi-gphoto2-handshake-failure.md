# Plan 03 result: libgphoto2 handshake rejected by the X-A5 (2026-10-04)

Part of [plan 03](../plans/03-wifi-gphoto2-test.md). Raw log:
`captures/wifi-gphoto2/2026-10-04-summary.log` (git-ignored, contains the PC host name).

## Setup

- Camera on its wireless screen, PC joined to the camera's open access point (see
  [AP observation](2026-10-04-wifi-ap-observation.md)). Camera address `192.168.0.1`.
- gphoto2 2.5.32 with libgphoto2 2.5.34, `--camera "Fuji X (WLAN)" --port ptpip:192.168.0.1 --summary`.

## Observed

| Step | Result |
|------|--------|
| TCP 55740 | **open** |
| TCP 55741, 55742 | refused (expected before a capture session) |
| libgphoto2 sends its 82-byte init request on 55740 | camera replies after about 1.2 ms with a 12-byte packet: `0c000000 05000000 1d200000` |
| Meaning of the reply | length 12, packet type 5 (**Init Fail**), reason `0x0000201d` = PTP response code **Invalid Parameter** |
| libgphoto2 error | `ptp_fujiptpip_init_command_ack: bad type returned 5`, then a retry 0.5 s later gets end of stream (camera closed the socket), then `Failed to connect.` |

The first packet libgphoto2 sent, in our own words: length 82, type 1, a 4-byte magic `0x8f53e4f2`, a
16-byte GUID that libgphoto2 generates once and stores in `~/.gphoto/settings`, then the PC host name
as UTF-16 padded with zeros. This matches the layout in libgphoto2 `fujiptpip.c` (`master`).

## Comparison with the other open-source tool

`hkr/fuji-cam-wifi-tool` (Unlicense) sends a packet with the **same layout and the same magic**. Its
differences are the GUID (a fixed constant instead of a random one) and the name (`CameraClient`).
That tool treats an Init Fail with reason `0x2019` (Device Busy) as "camera not ready". The X-A5
returned a different reason, `0x201d`.

## What this means

- The X-A5 is listening and speaks the Fuji variant of PTP/IP on 55740. That is better than a refused
  port: the protocol family is plausible for this body.
- The camera rejects something in the init packet. The packet layout and magic already match the other
  tool, so the likely culprits are the GUID, the name, or the camera state.
- This is the "TCP connects, init is rejected" row of the plan 03 outcome table. It does not yet
  require plans 04 and 05 to be run. A cheaper experiment comes first.

## Hypotheses (open)

| # | Hypothesis | Test |
|---|------------|------|
| H1 | The camera rejects a random GUID and accepts the fixed one the other tool uses | variants A vs B, D vs C |
| H2 | The camera rejects the host name used by libgphoto2 | variants B vs C |
| H3 | The camera state matters (screen, a prior failed attempt, or a lockout after the first rejection) | power-cycle the camera Wi-Fi between runs and note the screen shown |
| H4 | The X-A5 expects different field values than the X-T10 (for example another magic or a longer packet) | only if all variants fail; then plan 04 |

## Next experiment

`scripts/fuji_hello_probe.py` sends only the init packet in five variants (one per hypothesis) and
stops at the first one the camera accepts. It sends no commands and opens no session. Its packet for
variant A was checked byte for byte against the packet libgphoto2 sent.

Run it while joined to the camera network with the camera on its wireless screen:

```
python3 scripts/fuji_hello_probe.py
```

If the camera answers Init Fail to every variant even after a Wi-Fi power cycle, go to plan 04 and
capture what the official app sends.

## Probe result (18:49 to 18:50, same day)

Source: output of `scripts/fuji_hello_probe.py` pasted by the owner. Local log:
`captures/wifi-gphoto2/2026-10-04-hello-probe.txt` (git-ignored).

- First run: every variant failed with a connect timeout because the PC was not yet joined to the camera
  network. Not a result.
- Second run, joined:
  - **A** (random GUID, name `xa5-probe`): Init Fail, reason `0x201d`. This reproduces libgphoto2's failure.
  - **B** (the other tool's fixed GUID, name `CameraClient`): **Init Command Ack** (type 2, length 68).
    The script stopped there, so C, D and E were not tried.
- Third run: A timed out connecting (the camera was probably still busy with the previous connection),
  then B was accepted again. B is repeatable.

Decoded ack, in our own words: 4-byte connection number `0`, the camera's own 16-byte GUID (identifier,
not recorded here), then the camera name as UTF-16: `X-A5`. This matches the layout libgphoto2 expects.

### Conclusions

- **Confirmed:** the X-A5 accepts the Fuji init handshake when it receives the fixed GUID and name that
  the other tool uses, and rejects libgphoto2's random GUID plus the host name. The Wi-Fi protocol family
  matches the X-T10-era tool. This is the strongest evidence so far that open-source remote shooting on
  the X-A5 is feasible.
- **Not yet known:** whether the GUID, the name, or both caused the rejection. C, D and E isolate this.
- H3 (camera state) is weakened: the same camera state rejected A and accepted B within one run.
- Connections need a pause. A new connection right after a previous one can time out.

### Isolation result (19:08 to 19:12, same day)

Source: probe output pasted by the owner, log `captures/wifi-gphoto2/2026-10-04-hello-probe.txt`
(git-ignored). Every variant used a **new TCP connection** and the camera was on its wireless screen.

| Variant | GUID | Name | Result (times seen) |
|---------|------|------|---------------------|
| A | random, fresh each time | `xa5-probe` | Init Fail `0x201d` (many runs, including two in a row) |
| D | random, fresh each time | `CameraClient` | Init Fail `0x201d` (4 times) |
| E | our own fixed GUID `10 11 ... 1f` | `xa5-probe` | Init Fail `0x201d` |
| C | the other tool's fixed GUID | `xa5-probe` | **Init Command Ack** (2 times) |
| B | the other tool's fixed GUID | `CameraClient` | **Init Command Ack** (4 times, all runs) |

Conclusions:

- **The GUID decides.** The camera accepts the other tool's GUID with any name tried (C and B) and rejects
  random GUIDs and our own fixed GUID with any name tried (A, D, E).
- **The name does not matter** (C accepted with `xa5-probe`, D rejected with `CameraClient`).
- **A fixed GUID is not enough.** Variant E is fixed and was rejected. So the camera checks for a particular
  GUID value, or for a value the official apps and the open-source tools share.
- **H5 (retry on a new connection) is refuted for random GUIDs:** A was retried on fresh connections many
  times and never succeeded.
- **H6 (user must press OK) is not shown.** Acceptance happened with no reported prompt, but the owner was
  not asked to watch the camera screen. Still open.
- libgphoto2 generates a random GUID once and keeps it in `~/.gphoto/settings`. For the X-A5 that is
  enough to explain the failure seen in the original `gphoto2 --summary` run.
- The probe's accepted ack decodes as before: connection number 0, the camera's GUID (not recorded here),
  name `X-A5`.

Practical notes from the same session:

- The camera's access point appeared and disappeared. `nmcli device wifi connect` said "No network with
  SSID ... found" many times until `nmcli device wifi rescan` and a few retries. The camera's Wi-Fi may sleep
  or its beacon may be missed. Retry the scan before assuming a fault.
- `[Errno 101] Network is unreachable` means the PC had already dropped off the camera network.

### Prefix test (19:15, after the owner moved internet to USB tethering)

The PC joined the camera network over `wlp1s0` with internet kept on a USB tether, so the session stayed online.

| Variant | GUID | Result |
|---------|------|--------|
| F | the other tool's GUID with the last 4 bytes zeroed (what libfuji sends) | **Ack** |
| G | the same first 12 bytes, last 4 bytes random | **Ack** (the first try timed out connecting, see below) |

So the camera does **not** compare all 16 bytes. The first 12 bytes `ada5485d87b27f0bd3d5ded0` are enough, and
the last 4 bytes can be anything tried (`02 78 a8 c0`, zeros, random). Whether even fewer bytes are checked
is untested. For a fix, any GUID that starts with those 12 bytes works.

Timing and stability observed:

- Right after joining, the control port refused for a few seconds, then opened. Wait about 5 seconds.
- After the camera accepted a connection, a new connection within roughly 10 s timed out. Another try later
  succeeded. Space attempts out.
- Pings to the camera took about 180 ms.
- After several rapid attempts (probes, then three libgphoto2 tries that all got `connect cmd: Connection
  timed out`), the PC found itself off the camera network, with no ping reply. The camera's Wi-Fi had
  stopped or timed out. It has to be re-entered from the camera's wireless menu.

### Still open

- Whether fewer than 12 bytes of the GUID are checked.
- What comes after the ack on the X-A5: the event channel on 55741, `OpenSession`, device info, remote mode.
  The libgphoto2 run with the fixed GUID could not be completed because the camera's Wi-Fi dropped.

### Update after the prior art survey (same day)

Public projects ([survey](2026-10-04-prior-art-survey.md)) add two explanations that fit the data better
than "the camera whitelists a GUID":

- **H5, first init fails, retry on a new connection succeeds.** fuji-bridge resends the init after an Init
  Fail, on a reconnect, up to four times (0, 1, 2, 4 s). libfuji retries its handshake. libgphoto2 resends on
  the **same** socket, and the X-A5 closed it. The probe fits this: variant A failed first, variant B came
  second and was accepted. It also fits run 3, where the first connection timed out and the second worked.
- **H6, the camera waits for the user.** On older bodies the camera shows the client name after the ack and
  waits for OK, and a first connection may need (OK) CHANGE. Watch the camera screen during the probe.

The fixed GUID is shared by libfuji, the hkr tool and, per fuji-bridge's notes, the official XApp, so it is
not an identity that only one tool knows. That makes H1 (GUID check) less likely but not excluded.

### Next steps

1. Separate H5 from H1 and H2. Each command is one run, about 10 s apart. Watch the camera screen and
   write down anything it shows:
   ```
   python scripts/fuji_hello_probe.py --seq A,A        # same random-GUID variant twice, new connection each time
   python scripts/fuji_hello_probe.py --seq D          # random GUID + name CameraClient
   python scripts/fuji_hello_probe.py --seq C          # fixed GUID + our name
   python scripts/fuji_hello_probe.py --seq E          # own fixed GUID + our name
   ```
   If the second `A` is accepted, H5 explains everything: the fix is a reconnect-and-retry, with any GUID.
2. Try libgphoto2 itself once the cause is known. It reads its GUID from `~/.gphoto/settings` (section
   `ptp2_ip`, key `guid`) and uses the host name as the client name. This changes a file outside the repo, so
   back it up first and get the owner's go-ahead.
3. If libgphoto2 gets past the handshake, the next failure shows what else differs for the X-A5 (event
   channel on 55741, open session, device info). Capture it with `--debug` and add a finding.
4. In parallel, build libfuji and try it against the X-A5 (needs the owner's go-ahead for the clone and
   build, a few MB). It is the fastest way to learn how far an existing implementation gets.
5. Plan 04 stays in reserve for anything the public source cannot explain.
