# Plan 04: Wi-Fi traffic capture of the official app

Status: not started. Risk: low for the camera, medium for privacy (captures hold identifiers).
Needs installs: yes, see GATE. Run only if plan 03 fails or works partially.

## Question

What exactly does the official Camera Remote app send to the X-A5 and receive from it, for connect,
settings, shutter and live view?

## Why

Plan 03 shows whether libgphoto2's driver matches the X-A5. If it does not, the official app is the
reference implementation. Its traffic is the most direct description of the protocol the camera expects,
and it can be observed without touching the app's code.

## GATE: approvals

- Install `wireshark-cli` (about 100 MiB installed) to read pcap files. Install `tcpdump` (about 1 MiB)
  only if capturing on the PC.
- Install a capture app on the owner's phone, if using method A.
- The official app is used with the owner's own camera and phone only.

## Prerequisites

- Plan 03 result recorded, so we know what to compare against.
- An Android phone with the Camera Remote app that already pairs with the X-A5. Android is assumed.
  An iPhone needs a Mac to capture and is out of scope until the owner says otherwise.
- `captures/wifi-pcap/` exists (`mkdir -p captures/wifi-pcap`).

## Capture methods

Use the first one that works.

| Method | How | Extra disk | Notes |
|--------|-----|------------|-------|
| A. On-phone capture | A non-root capture app that records the app's traffic through Android's VPN service (PCAPdroid is one such app) | none on the PC | Expected to see traffic to the camera's local address. **Not yet verified** with this camera. Android may route differently on a Wi-Fi network without internet, so check the pcap actually contains port 55740 traffic. |
| B. PC joins the camera network, official app runs on the PC | Android emulator on the PC, `tcpdump` on the PC's Wi-Fi interface | large (emulator images are in the GB range) | Does not fit the disk budget on `/`. Use only if A fails and the owner approves a location on `/media/d`. |
| C. PC in monitor mode, phone joins the camera | PC Wi-Fi adapter in monitor mode on the camera's channel (channel 6 on 2026-10-04) | none beyond tools | The camera's network is **open** (observed 2026-10-04), so no key is needed to read the frames. Needs an adapter that supports monitor mode (not checked on `wlp1s0`). Putting the adapter in monitor mode drops the PC's normal Wi-Fi. |

## Steps (method A)

1. Install the capture app on the phone. Record its version in the findings file.
2. Join the camera's Wi-Fi from the phone. Start the capture, scoped to the Camera Remote app only.
3. Perform **one scenario per capture** and stop the capture after each. Keep each under about 30 seconds,
   because live view streams JPEG frames continuously.

   | File name suffix | Scenario |
   |------------------|----------|
   | `01-connect` | open the app, connect, reach the main screen |
   | `02-idle-10s` | stay connected, do nothing for 10 s (keep-alive traffic) |
   | `03-live-view` | start live view for 10 s, stop it |
   | `04-set-iso` | change ISO once |
   | `05-set-aperture-or-shutter` | change one exposure setting once |
   | `06-shutter` | take one photo from the app |
   | `07-transfer` | open the image list, download one image |
   | `08-disconnect` | leave the remote screen, disconnect |

4. Export each capture as pcap and copy it to `captures/wifi-pcap/<date>-<suffix>.pcap` on the PC.
5. Write a sidecar `<date>-<suffix>.md` with: app version, phone model, camera firmware, exact UI action,
   and the time of each action.

## Analysis

With `tshark`:

```
tshark -r <file>.pcap -q -z conv,tcp                          # which connections, how much data
tshark -r <file>.pcap -Y "tcp.port==55740 && tcp.len>0" \
  -T fields -e frame.time_relative -e ip.src -e tcp.srcport -e tcp.len -e tcp.payload
```

Work in this order:

1. Which ports and in which order does the app open them (`conv,tcp`)?
2. Dump the first exchange on 55740 as hex. Compare field by field with libgphoto2's `fujiptpip.c`
   init request (packet type, fixed length 82 for the init, host name, version fields) and with the
   camera's reply. Note differences.
3. For each scenario, list request opcodes, parameters and response codes. Mark what changes between
   captures (for example the ISO value).
4. For live view, find the stream framing on 55742 and how a JPEG frame is delimited.
5. For events, find the framing on 55741.

Write results as protocol notes in `docs/protocol/wifi.md` in our own words. Use a table per message
(direction, opcode or type, fields, meaning, evidence file). Mark every row **observed** or **guessed**.

## Privacy and clean-room

- Raw pcaps hold the camera serial, MAC, SSID and phone or PC host name. They stay in `captures/`
  (git-ignored). Sanitize before using any as a test fixture (see plan 07).
- Describe message layouts, opcodes and sequences in your own words. Do not copy app code, app text
  or app assets into the repo. Short hex examples of protocol messages are fine in `docs/protocol/`
  once identifiers (serial, MAC, host name) are removed.

## Exit criteria

- One pcap per scenario, with sidecar notes.
- `docs/protocol/wifi.md` covers connect, keep-alive, one setting change, shutter and live view, with a
  list of what is still unknown.
- `docs/findings/<date>-wifi-capture.md` records method, tool versions, and which scenarios worked.

## Next step

Plan 05 in parallel (the APK tells why the bytes look as they do). Then plan 07.
