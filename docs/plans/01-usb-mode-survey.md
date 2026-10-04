# Plan 01: USB mode survey

Status: not started. Risk: none, read-only. Needs installs: none.

## Question

Does any USB or connection mode in the X-A5 menu expose a capture or tether operation over PTP?

## Why

The baseline probe saw one mode only, and its menu label was not recorded. In that mode the camera
advertised no `0x100e`, no `0x101c` and no `0x902x` operations. Fuji bodies commonly change their
USB behavior with a menu setting (not yet confirmed for the X-A5), so one negative result does not
close USB.

Note (2026-10-04): the X-A5 manual page "Connecting to Computers via USB" lists no USB-mode setting and
says no special camera settings are needed. So there may be only one USB mode. If the menus really have
no USB or connection item that changes USB behavior, this plan reduces to confirming that and recording
the exact menu labels checked. Source: <https://fujifilm-dsc.com/en/manual/x-a5/connections/computer/index.html>
(the manual's CONNECTION SETTING menu has Bluetooth, PC AUTO SAVE, instax and general items, per
<https://app.fujifilm-dsc.com/en-int/manual/x-a5/menu_setup/setup_menu3/index.html>). PC AUTO SAVE is a
wireless-LAN setting there, so it does not by itself indicate a different USB mode.

## Prerequisites

- Camera on a charged battery, SD card inserted, USB cable to the PC.
- The camera menu path for USB or connection settings. The manual lists none for USB, so check the
  CONNECTION SETTING menu and write down the exact labels you see.
- `captures/usb-survey/` exists (create it with `mkdir -p captures/usb-survey`).

## Allowed commands

Only these. They do not change camera state:

```
lsusb -d 04cb:
lsusb -v -d 04cb:02d5            # product ID may differ per mode, adjust
gphoto2 --auto-detect
gphoto2 --summary
gphoto2 --list-config
gphoto2 --list-files
gphoto2 --abilities
```

Do **not** use `--capture-*`, `--delete-*`, `--upload-file`, `--set-config` or `--folder` write options in
this plan.

## Steps

For each mode offered by the camera (record the exact menu label as `<mode>`):

1. Set the mode on the camera. Reconnect the USB cable if the camera asks.
2. Record the USB identity:
   `lsusb -d 04cb:` and, if the product ID changed, `lsusb -v -d 04cb:<pid> | head -80`. A mass-storage
   mode shows interface class 8 instead of 6 and needs no PTP probing. Note it and move on.
3. Capture the PTP session:
   ```
   timeout 60 gphoto2 --debug \
     --debug-logfile=captures/usb-survey/$(date +%F)-<mode>.log --summary
   ```
4. Run `gphoto2 --list-config` and `gphoto2 --list-files`. Save the output next to the log as
   `<date>-<mode>.txt`.
5. From the log, take the **first** `Device info:` block. That is what the camera reports (operations,
   events and properties). The second block already contains properties that libgphoto2 injected for
   every Fuji vendor ID and must not be counted as camera features.
   ```
   awk '/Device info:/{n++} n==1' <log> | cut -c1-120
   ```
   Check the counts against the hexdump: the length fields in the raw `Get device info` reply give the
   true number of operations and properties.
6. Note whether the first `OpenSession` timed out (`PTP I/O Error (0x02ff)`) and whether storage is
   "Read Only".

## Results table (copy into a findings file)

| Mode label | USB ID / class | Ops count | Has `0x100e` / `0x101c` / `0x902x` | Props reported | Storage access | Files listed | First OpenSession OK |
|------------|----------------|-----------|-------------------------------------|----------------|----------------|--------------|----------------------|
| (baseline, label unknown) | `04cb:02d5` / 6 | 25 | no / no / no | 8 | read only + delete | 0 | no (retry worked) |

## Exit criteria

- Every selectable USB or connection mode has a row.
- Write `docs/findings/<date>-usb-mode-survey.md` with the table and the exact menu labels.

## Next step

- A mode advertises `0x100e`, `0x101c` or `0x902x`: stop and write a new plan "USB tether for X-A5".
  This would be much cheaper than the Wi-Fi route.
- No mode does: USB stays download and delete only. Decide on plan 02 only if the unidentified vendor
  operations look useful.
- Update the status in the root `README.md` and the decision tree in `00-overview.md`.
