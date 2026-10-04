# Wi-Fi access point observation (2026-10-04, plan 03 in progress)

Partial result of [plan 03](../plans/03-wifi-gphoto2-test.md). The camera was put in its wireless mode
(menu path used: not recorded) and joined from the PC with NetworkManager. Source: terminal output pasted
by the owner.

## Observed

| Item | Value |
|------|-------|
| SSID | `FUJIFILM-X-A5-<4 digits>` (the digits match the end of the camera serial number, so treat the exact SSID as an identifier) |
| Security | **None** (open network) per `nmcli`, mode Infra, 2.4 GHz, channel 6 |
| Join | `nmcli device wifi connect <SSID>` succeeded with no password |
| PC address | `192.168.171.2` from DHCP, route `192.168.0.0/16`, so the netmask is /16 |
| Camera address | `192.168.0.1` (the DHCP default gateway) |

## Not a valid result

The owner's first port check used `192.168.171.2`, which is the **PC's own address**, so
"Connection refused" on 55740 says nothing about the camera. The check must target `192.168.0.1`.
Port status of the camera is therefore still **unknown**.

## Consequences

- No Bluetooth step was needed to make the access point appear (the owner did not report pairing, but
  that was not asked, so treat this as unconfirmed).
- The network is open, so a monitor-mode capture on channel 6 would see unencrypted frames. That makes
  plan 04 method C easier than assumed: no network key is needed, only a Wi-Fi adapter that supports
  monitor mode (not checked on `wlp1s0`).
- The camera is a /16 DHCP server at `192.168.0.1`. Use that address for `--port ptpip:`.
