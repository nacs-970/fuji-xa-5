# Baseline probe of the X-A5 over USB (2026-10-04)

Facts only. Interpretation is in [the feasibility assessment](2026-10-04-feasibility-assessment.md).

## Setup

| Item | Value |
|------|-------|
| Host OS | Arch Linux, kernel 7.2.8-arch1-2 |
| gphoto2 | 2.5.32 |
| libgphoto2 | 2.5.34-1 (package), camlib `/usr/lib/libgphoto2/2.5.34/ptp2.so` |
| Camera | Fujifilm X-A5, firmware `1.21` (from DeviceInfo "device version") |
| USB ID | `04cb:02d5`, High Speed (480 Mbps) |
| Camera USB mode | **not recorded** (the camera menu label was not noted). Plan 01 fixes this. |
| Serial number | redacted. It is present in the local, git-ignored raw log. |

Raw evidence: `captures/baseline/2026-10-04-gphoto2-summary.debug.log` (git-ignored).
Produced by: `gphoto2 --debug --debug-logfile=<file> --summary`. All commands in this probe are read-only.

## USB descriptor

- One configuration, one interface: class 6 (Imaging), subclass 1, protocol 1 (PTP).
- Endpoints: bulk OUT `0x01`, bulk IN `0x82`, interrupt IN `0x83` (64 bytes, interval 11).
- No mass-storage interface is exposed in this mode.

## Session behavior

- `gphoto2 --auto-detect` finds `Fuji Fujifilm X-A5` at `usb:001,007`.
- The first `OpenSession` (`0x1002`) got no response within 8 s (`PTP I/O Error 0x02ff`). The retry
  succeeded immediately. Likely cause is unknown. Check whether it repeats in other modes (plan 01).

## What the camera itself reports (DeviceInfo, `0x1001`)

- Manufacturer `FUJIFILM`, model `X-A5`.
- Vendor extension ID `0x00000006` (Microsoft/MTP), version 100, description `fujifilm.co.jp: 1.0;`.
  libgphoto2 rewrites the ID to Fuji (`0x0e`) because of the description string (`library.c`).
- Functional mode `0x0000`.
- Operations (25):
  - Standard PTP: `0x1001` to `0x1009`, `0x100a`, `0x100b`, `0x100c`, `0x100d`, `0x100f`, `0x1014`,
    `0x1015`, `0x1016`, `0x101b`.
  - MTP object properties: `0x9801`, `0x9802`, `0x9803`, `0x9805`.
  - Vendor, **unidentified**: `0x900c`, `0x900d`, `0x901d`.
- **Not present:** `0x100e` InitiateCapture, `0x101c` InitiateOpenCapture, and every Fuji tether
  operation (`0x9020` to `0x9042`, including `0x902b` GetDeviceInfo).
- Events: `0x4002` ObjectAdded, `0x4003` ObjectRemoved, `0x4004` StoreAdded, `0x4005` StoreRemoved,
  `0x4006` DevicePropChanged, `0x4008` DeviceInfoChanged, `0x4009` RequestObjectTransfer.
- Device properties advertised (8): `0x5001` battery, `0x5005` white balance, `0x5007` F-number,
  `0x500a` focus mode, `0x5010` exposure bias, `0xd407` perceived device type, `0xd406` session
  initiator info, `0xd303`.

## What the camera actually serves

| Query | Result |
|-------|--------|
| `0x5001` battery level | works, range 0 to 3, value 3 |
| `0x5005`, `0x5007`, `0x500a`, `0x5010` describe | `0x2007` Incomplete Transfer (advertised but not served) |
| `0xd407`, `0xd406`, `0xd303` describe | works (`0xd407` = 1, `0xd406` = empty string, `0xd303` = 1) |
| `0x500d` and about 60 Fuji properties (`0xd38c`, `0xd171`, `0xd242`, ...) | `0x200a` Device Prop Not Supported |
| Storage `0x00010001` | SD card, about 121.9 GB, access "Read Only with Object deletion" |
| `/store_00010001/DCIM` | listed as empty. Not checked whether the card is empty or the mode hides files. |

Note: the roughly 60 Fuji properties are **not** reported by the camera. libgphoto2 injects a static list
for every Fuji vendor ID (`library.c`, around lines 380 to 460 in `master`). They are listed here only
because the camera rejected each one.

## What the current driver exposes for this camera

`gphoto2 --abilities`: no capture, no configuration support, delete selected files, no delete all,
thumbnails, file upload.

`gphoto2 --list-config` returns only:

```
/main/actions/autofocusdrive
/main/actions/autofocusdrivemanual
/main/actions/opcode
/main/status/{serialnumber,manufacturer,cameramodel,deviceversion,vendorextension,batterylevel}
/main/other/{5001,d407,d406,d303}
```

The `Fuji:Fujifilm X-A5` entry in `library.c` (`master`) is `{0x04cb, 0x02d5, 0}`. Flags `0` mean no
`PTP_CAP` and no `PTP_CAP_PREVIEW`. The same is true of X-A2, X-E2, X-T10 and X-T20. X-T1, X-T2,
X-Pro2, X-E3, X-H1 and X-T3 carry `PTP_CAP|PTP_CAP_PREVIEW`.

## Wi-Fi driver present in the same library

`gphoto2 --list-cameras` lists `"Fuji X (WLAN)" (EXPERIMENTAL)`. The installed `ptp2.so` contains
`ptp_fujiptpip_*` symbols. In `master`, `fujiptpip.c` documents three TCP pipes: command 55740, event
55741, JPEG 55742. The event and JPEG pipes open only after the capture session starts.

## Tooling status at the time of the probe

- REA MCP: `open_binary` accepted `ptp2.so`. Every analysis call then failed with
  `provider_unavailable`: Ghidra not configured (`GHIDRA_INSTALL_DIR` unset, no Ghidra installed,
  default Java 27 rejected), Hopper missing at `/opt/hopper/bin/Hopper`.
- Other tools present: `gphoto2`, `objdump`, `gdb`, `adb`, `ip`. Not present: `tshark`, `wireshark`,
  `ptpcam`, `jadx`, `tcpdump`, `nc` (checked with `which` later the same day).
- Disk: `/` 94 % used, 2.9 GB free. `/media/d` (NTFS, `fuseblk`) 25 GB free. `/tmp` is tmpfs (3.6 GB).

## Source versions

- Installed binary: libgphoto2 2.5.34-1.
- Source read: libgphoto2 `master`, downloaded 2026-10-04. `master` head was commit
  `e4108a531c868cb60c8ab2eaa2bef8d4b1b9a3ae` (committed 2026-10-03) when checked right afterwards.
  Line numbers in these docs refer to that source and may drift.
