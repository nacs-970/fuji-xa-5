# 2026-10-05: USB mode survey (plan 01)

Camera: Fujifilm X-A5, firmware 1.21, on a charged battery with an SD card, USB cable to the Linux PC, camera
turned on. gphoto2 2.5.32 and libgphoto2 2.5.34 (installed binaries). Read-only: only `lsusb`, `gphoto2
--auto-detect`, `--summary` and `--list-config` were run. Raw output is in
`captures/usb-survey/2026-10-05-gphoto2-usb.txt` (git-ignored, the serial number is inside).

## What the owner saw

When the cable is plugged in, the camera goes straight into one USB mode that gives read/write access to the
SD card. There was no choice to make on the camera. The owner did not write down CONNECTION SETTING menu
labels this time, so "no USB item in that menu" rests on the owner's statement and on the manual
(printed pages 175 to 177 and the setup menu pages list Bluetooth, PC AUTO SAVE, instax and general wireless
settings only, nothing for USB).

## USB descriptor (`lsusb -v`)

- `04cb:02d5`, "USB PTP Camera", USB 2.0 High Speed, bus powered, 500 mA.
- One configuration, one interface: class 6 Imaging, subclass 1 Still Image Capture, protocol 1 PTP.
- Three endpoints: bulk OUT 0x01, bulk IN 0x82, interrupt IN 0x83.
- No mass-storage interface and no vendor-specific interface. So the "read/write to the SD card" mode is PTP
  object access, not a USB drive.

## gphoto2

- `--auto-detect`: `Fuji Fujifilm X-A5` on `usb:001,005`.
- `--summary`: "File Download, File Deletion, File Upload. No Image Capture, No Open Capture, No vendor specific
  capture". Storage access capability is "Read Only with Object deletion". The `File Upload` line is
  libgphoto2's reading of the operation list; not tested.
- Properties: only 3 answer (`0xD407` read-only u32 = 1, `0xD406` read/write string, empty, `0xD303`
  read-only u8 = 1) plus the battery level `0x5001` (value 3 of range 0 to 3). `0x5005`, `0x5007`, `0x500A`
  and `0x5010` answer `0x2007`. About 70 Fuji properties that the DeviceInfo lists answer `0x200A`.
  This is the same pattern as over Wi-Fi (`GetDevicePropDesc` refused with `0x2007` and `0x200A`), so the
  refusal is camera behavior, not a transport problem.
- `--list-config`: actions `autofocusdrive`, `autofocusdrivemanual`, `opcode`, status entries, and `other/5001`,
  `d407`, `d406`, `d303`. No capture or viewfinder entry.

## Trouble met

The first `gphoto2 --summary` (run by the owner) failed with "Could not claim the USB device". `fuser` showed
`gvfsd-gphoto2` holding `/dev/bus/usb/001/005`, because the desktop had auto-mounted the camera as
`gphoto2://...`. When we re-ran, the mount was gone and gphoto2 worked. How the mount went away was not checked.
To survey again, unmount first (`gio mount -u <the gphoto2:// URI from gio mount -l>`).

## Result

- The X-A5 has one USB mode: PTP over USB, download only. Nothing in the descriptor or the operation list
  offers capture, open capture or tether, which matches the 2026-10-04 baseline probe.
- Wi-Fi stays the only remote shooting route for this body.
- Not tested: whether `0xD406` (read/write string) does anything (not written, no write tests by owner
  decision); the camera in a different state (playback mode, Wi-Fi on) while plugged in; `lsusb -v` as root.
