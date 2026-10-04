#!/usr/bin/env python3
"""Open a PTP session on the X-A5 over Wi-Fi and read its DeviceInfo. Read-only.

Plan 03 follow-up. Steps, one connection, nothing is changed on the camera:
  1. init handshake on TCP 55740 with the GUID the camera accepts (see fuji_hello_probe.py)
  2. wait 50 ms, then OpenSession (transaction id 1, session id 1)
  3. GetDeviceInfo, print the operations, events and properties the camera advertises over Wi-Fi
  4. CloseSession

After the init ack the camera uses USB-style PTP containers on the same socket:
    u32 length, u16 type (1 command, 2 data, 3 response), u16 code, u32 transaction id, u32 params...
Older Fuji bodies may show the client name on their screen and wait for OK before answering OpenSession.
This script waits up to 45 s for that. Watch the camera screen and press OK if it asks.

Run through the Wi-Fi wrapper, one run per join:
    scripts/with_camera_wifi.sh -- python3 scripts/fuji_session_probe.py

Output also goes to captures/wifi-gphoto2/<date>-session-probe.txt (git-ignored). The serial number from
DeviceInfo is not printed.
"""
import argparse
import datetime
import os
import socket
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fuji_hello_probe import GUID_HKR, PORT, TYPES, build_init  # noqa: E402

RC = {0x2001: "OK", 0x2002: "General Error", 0x2003: "Session Not Open", 0x2004: "Invalid TransactionID",
      0x2005: "Operation Not Supported", 0x2007: "Incomplete Transfer", 0x2009: "Invalid Object Handle",
      0x200A: "Device Prop Not Supported", 0x2019: "Device Busy", 0x201D: "Invalid Parameter",
      0x201E: "Session Already Open", 0x200F: "Access Denied"}
OPS = {0x1001: "GetDeviceInfo", 0x1002: "OpenSession", 0x1003: "CloseSession", 0x1004: "GetStorageIDs",
       0x1005: "GetStorageInfo", 0x1006: "GetNumObjects", 0x1007: "GetObjectHandles", 0x1008: "GetObjectInfo",
       0x1009: "GetObject", 0x100A: "GetThumb", 0x100B: "DeleteObject", 0x100C: "SendObjectInfo",
       0x100D: "SendObject", 0x100E: "InitiateCapture", 0x100F: "FormatStore", 0x1014: "GetDevicePropDesc",
       0x1015: "GetDevicePropValue", 0x1016: "SetDevicePropValue", 0x101B: "GetPartialObject",
       0x101C: "InitiateOpenCapture", 0x902B: "FujiGetDeviceInfo", 0x9022: "FujiGetCapturePreview",
       0x9020: "FujiInitiateMovieCapture", 0x9021: "FujiTerminateMovieCapture"}


def recv_exact(s: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("camera closed the connection")
        buf += chunk
    return buf


def read_container(s: socket.socket, timeout: float):
    s.settimeout(timeout)
    head = recv_exact(s, 4)
    length = struct.unpack("<I", head)[0]
    body = recv_exact(s, length - 4) if length > 4 else b""
    return head + body


def parse_container(raw: bytes):
    length, ctype, code, tid = struct.unpack_from("<IHHI", raw, 0)
    return length, ctype, code, tid, raw[12:]


def command(s, code: int, tid: int, params=(), timeout: float = 10.0):
    pkt = struct.pack("<IHHI", 12 + 4 * len(params), 1, code, tid) + b"".join(struct.pack("<I", p) for p in params)
    s.sendall(pkt)
    data = b""
    while True:
        raw = read_container(s, timeout)
        length, ctype, rcode, rtid, payload = parse_container(raw)
        if ctype == 2:
            data += payload
        elif ctype == 3:
            return rcode, data
        else:
            raise RuntimeError(f"unexpected container type {ctype} code 0x{rcode:04x}")


def ptp_string(buf: bytes, off: int):
    n = buf[off]
    off += 1
    text = buf[off:off + 2 * n].decode("utf-16-le", errors="replace").rstrip("\x00")
    return text, off + 2 * n


def u16_array(buf: bytes, off: int):
    n = struct.unpack_from("<I", buf, off)[0]
    off += 4
    vals = list(struct.unpack_from(f"<{n}H", buf, off)) if n else []
    return vals, off + 2 * n


def parse_device_info(buf: bytes):
    off = 0
    std, ext_id, ext_ver = struct.unpack_from("<HIH", buf, off)
    off += 8
    ext_desc, off = ptp_string(buf, off)
    func_mode = struct.unpack_from("<H", buf, off)[0]
    off += 2
    ops, off = u16_array(buf, off)
    events, off = u16_array(buf, off)
    props, off = u16_array(buf, off)
    capture_fmts, off = u16_array(buf, off)
    image_fmts, off = u16_array(buf, off)
    maker, off = ptp_string(buf, off)
    model, off = ptp_string(buf, off)
    version, off = ptp_string(buf, off)
    return dict(std=std, ext_id=ext_id, ext_ver=ext_ver, ext_desc=ext_desc, func_mode=func_mode, ops=ops,
                events=events, props=props, capture_fmts=capture_fmts, image_fmts=image_fmts, maker=maker,
                model=model, version=version)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ip", default="192.168.0.1")
    ap.add_argument("--name", default="xa5-probe", help="client name shown on the camera")
    ap.add_argument("--open-timeout", type=float, default=45.0, help="seconds to wait for OpenSession (OK prompt)")
    args = ap.parse_args()

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outdir = os.path.join(repo, "captures", "wifi-gphoto2")
    os.makedirs(outdir, exist_ok=True)
    logpath = os.path.join(outdir, f"{datetime.date.today()}-session-probe.txt")
    log = open(logpath, "a", encoding="utf-8")

    def say(msg: str = "") -> None:
        print(msg, flush=True)
        log.write(msg + "\n")
        log.flush()

    say(f"# session probe {datetime.datetime.now().isoformat(timespec='seconds')} camera={args.ip}:{PORT}")
    try:
        s = socket.create_connection((args.ip, PORT), timeout=5)
    except OSError as exc:
        say(f"connect failed: {exc}")
        return 1
    with s:
        s.settimeout(5)
        s.sendall(build_init(GUID_HKR, args.name))
        raw = read_container(s, 5)
        length, ptype = struct.unpack_from("<II", raw, 0)
        say(f"init reply: len={length} type={ptype} ({TYPES.get(ptype, '?')})")
        if ptype != 2:
            say(f"  raw={raw.hex()}")
            say("init not accepted, stopping")
            return 2
        time.sleep(0.05)  # the camera needs at least 50 ms before OpenSession (public notes)

        say(f"OpenSession (waiting up to {args.open_timeout:.0f} s; if the camera shows the client name, press OK)")
        try:
            rcode, _ = command(s, 0x1002, 1, (1,), timeout=args.open_timeout)
        except (OSError, ConnectionError, RuntimeError) as exc:
            say(f"  OpenSession failed: {exc}")
            return 3
        say(f"  response 0x{rcode:04x} ({RC.get(rcode, '?')})")
        if rcode not in (0x2001, 0x201E):
            return 4

        say("GetDeviceInfo")
        try:
            rcode, data = command(s, 0x1001, 2, timeout=15)
        except (OSError, ConnectionError, RuntimeError) as exc:
            say(f"  GetDeviceInfo failed: {exc}")
            return 5
        say(f"  response 0x{rcode:04x} ({RC.get(rcode, '?')}), {len(data)} bytes of data")
        if data:
            try:
                di = parse_device_info(data)
            except (struct.error, IndexError) as exc:
                say(f"  could not parse DeviceInfo: {exc}. raw head: {data[:64].hex()}")
            else:
                say(f"  manufacturer={di['maker']!r} model={di['model']!r} version={di['version']!r} (serial not printed)")
                say(f"  vendor extension id=0x{di['ext_id']:08x} version={di['ext_ver']} desc={di['ext_desc']!r} "
                    f"functional mode=0x{di['func_mode']:04x}")
                say(f"  operations ({len(di['ops'])}):")
                for op in di["ops"]:
                    say(f"    0x{op:04x} {OPS.get(op, '')}")
                say(f"  events ({len(di['events'])}): " + " ".join(f"0x{e:04x}" for e in di["events"]))
                say(f"  properties ({len(di['props'])}): " + " ".join(f"0x{p:04x}" for p in di["props"]))
                for want in (0x100E, 0x101C, 0x902B, 0x9022):
                    say(f"  advertises 0x{want:04x} {OPS.get(want, '')}: {'yes' if want in di['ops'] else 'no'}")

        say("CloseSession")
        try:
            rcode, _ = command(s, 0x1003, 3, timeout=10)
            say(f"  response 0x{rcode:04x} ({RC.get(rcode, '?')})")
        except (OSError, ConnectionError, RuntimeError) as exc:
            say(f"  CloseSession failed: {exc}")
    say(f"# log: {logpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
