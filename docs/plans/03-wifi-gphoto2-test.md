# Plan 03: Wi-Fi test with libgphoto2

Status: not started. Risk: low. The test takes one photo, so it writes to the SD card.
Needs installs: none.

## Question

Does libgphoto2's experimental `Fuji X (WLAN)` driver talk to the X-A5 over Wi-Fi? If it does, how far
does it get: connect, summary, live preview, capture?

## Why this goes first

It is the cheapest decisive experiment. The official app controls the X-A5 over Wi-Fi, the installed
libgphoto2 2.5.34 already contains a Fuji Wi-Fi driver with capture and preview flags, and nobody in the
sources reviewed has reported an X-A5 result. A pass saves most of the project. A failure tells us
exactly where the protocol differs.

## Prerequisites

- Camera on a charged battery, SD card inserted.
- Camera in the state it uses for the Camera Remote app. Per Fuji's manuals: press the button assigned to
  **WIRELESS COMMUNICATION**, or select **WIRELESS COMMUNICATION** in the shooting or playback menu
  (older bodies such as the X-A2 use the playback menu). The camera then broadcasts its own Wi-Fi network,
  which a phone selects from its Wi-Fi list. The camera name shown comes from
  CONNECTION SETTING > GENERAL SETTINGS > NAME. The manuals do not state the SSID format or whether a
  password is needed, so record what you see. Whether the camera listens on port 55740 in this state
  without the app is **unknown**: that is part of what the test shows.
- A PC network interface that can join the camera's access point. This PC has one Wi-Fi interface
  (`wlp1s0`) and no other network interface, so joining the camera network cuts the PC's internet,
  including a Claude Code session running on it. Either run the test in a separate terminal and
  reconnect afterwards, or add a second (USB) Wi-Fi adapter.
- `captures/wifi-gphoto2/` exists (`mkdir -p captures/wifi-gphoto2`).
- The model string. Confirm it with `gphoto2 --list-cameras | grep WLAN`. On 2026-10-04 it was
  `"Fuji X (WLAN)" (EXPERIMENTAL)`.

## Steps

Tip: run each test through `scripts/with_camera_wifi.sh -- <command>`. It joins the camera network, runs the
command once, and reconnects to your previous network. The camera often stops its Wi-Fi after a client
connection, so every test should start with a fresh join (as in manual testing).


1. Join the camera's Wi-Fi network from the PC (NetworkManager is installed here):
   ```
   nmcli dev wifi list
   nmcli dev wifi connect "<camera SSID>"            # add: password "<key>" if the camera shows one
   ```
   Record SSID and security type. Note the SSID of your normal network first so you can rejoin it.
2. Find the camera's address. The camera acts as the DHCP server, so its address is normally the gateway:
   ```
   ip -4 route show dev wlp1s0
   ```
   It is often `192.168.0.1`, but use what the route shows. Record the address.
3. Reachability check, no camera protocol yet:
   ```
   ping -c 3 <camera-ip>
   timeout 3 bash -c 'exec 3<>/dev/tcp/<camera-ip>/55740' && echo open || echo closed
   ```
   `nc` is not installed here, so the second command uses bash's `/dev/tcp`. Record whether port 55740
   accepts a connection. 55741 and 55742 normally refuse until a capture
   session starts. That is expected, not a failure.
4. Summary:
   ```
   gphoto2 --camera "Fuji X (WLAN)" --port ptpip:<camera-ip> \
     --debug --debug-logfile=captures/wifi-gphoto2/$(date +%F)-summary.log --summary
   ```
5. Live preview, if step 4 works:
   ```
   gphoto2 --camera "Fuji X (WLAN)" --port ptpip:<camera-ip> \
     --debug --debug-logfile=captures/wifi-gphoto2/$(date +%F)-preview.log \
     --capture-preview --filename=/tmp/xa5-preview.jpg
   ```
   Save the output under `/tmp` (RAM), not in the repo.
6. Capture, if step 5 works. **This takes a photo and writes it to the card.** Ask the owner before
   running it:
   ```
   gphoto2 --camera "Fuji X (WLAN)" --port ptpip:<camera-ip> \
     --debug --debug-logfile=captures/wifi-gphoto2/$(date +%F)-capture.log --capture-image
   ```
7. If a step fails, stop and keep the log. Do not retry in a loop. Power cycle the camera Wi-Fi before the
   next attempt.

## What to extract from each log

- Which TCP connections opened, in what order, and which one the camera closed or reset.
- The init request sent (hostname and version fields) and the camera's reply, or the absence of one.
- Errors such as `Unsure on type`, `got reply type` or `PTP I/O Error`. libgphoto2 issue 517 reports
  these on X-T series bodies when the protocol differs.
- Whether the camera showed a pairing or "connect" prompt on its screen.

## Outcome table

| Result | Meaning | Next |
|--------|---------|------|
| Summary, preview and capture all work | the existing driver already supports the X-A5 | plan 07, branch "works already" |
| Connects but a later step fails | partial protocol match | plan 04, focus on the failing step |
| TCP connects, init is rejected or closed | handshake differs for this body | plans 04 and 05 |
| TCP refused on 55740 | wrong mode, address or protocol | recheck setup, then plan 04 to see what the app connects to |
| Cannot reach the camera network | setup problem, not a result | fix setup |

## Exit criteria

`docs/findings/<date>-wifi-gphoto2-test.md` with: camera Wi-Fi mode label, address, each command run,
result per step, and the key lines from each log. Update the status in the root `README.md` and the
decision tree in `00-overview.md`.
