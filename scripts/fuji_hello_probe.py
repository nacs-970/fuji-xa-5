#!/usr/bin/env python3
"""Probe the Fuji Wi-Fi control port with variations of the first (init) packet.

Plan 03 follow-up. libgphoto2's `Fuji X (WLAN)` driver gets Init_Fail (reason 0x201d) from the X-A5.
This script finds out which field of the init packet the camera objects to. It sends ONLY the init
packet on TCP 55740, reads the reply, closes the socket and goes on to the next variant. It sends no
PTP commands and opens no session. It stops at the first variant the camera accepts, unless
--no-stop is given.

Packet layout (82 bytes, as observed in libgphoto2 and in the hkr tool's source, little endian):
    0   u32  length = 82
    4   u32  packet type = 1 (Init Command Request)
    8   u32  magic 0x8f53e4f2
    12  16B  GUID
    28  UTF-16LE host name, zero padded up to 82 bytes

Reply: u32 length, u32 type. Type 2 = Init Command Ack, type 5 = Init Fail followed by a u32 reason.

Run while the PC is joined to the camera's Wi-Fi and the camera shows its wireless screen:
    python3 scripts/fuji_hello_probe.py            # camera 192.168.0.1
    python3 scripts/fuji_hello_probe.py --dry-run  # print packets only, no network
    python3 scripts/fuji_hello_probe.py --seq A,A  # ordered list, letters may repeat (retry test)

Output also goes to captures/wifi-gphoto2/<date>-hello-probe.txt (git-ignored).
"""
import argparse
import datetime
import os
import socket
import struct
import sys
import time

PORT = 55740
PACKET_LEN = 82
MAGIC = 0x8F53E4F2
REASONS = {0x2019: "Device Busy", 0x201D: "Invalid Parameter", 0x200F: "Access Denied",
           0x201E: "Session Already Open", 0x2002: "General Error"}
TYPES = {1: "InitCommandRequest", 2: "InitCommandAck", 3: "InitEventRequest", 4: "InitEventAck",
         5: "InitFail"}

# GUID that the hkr/fuji-cam-wifi-tool project (Unlicense) sends. Used here only as a test value.
GUID_HKR = bytes.fromhex("ada5485d87b27f0bd3d5ded00278a8c0")
GUID_FIXED = bytes(range(0x10, 0x20))
GUID_RANDOM = os.urandom(16)

VARIANTS = [
    ("A", "random GUID + name xa5-probe (libgphoto2 style, expect Init_Fail 0x201d)", GUID_RANDOM, "xa5-probe"),
    ("B", "hkr GUID + name CameraClient (the other tool's exact values)", GUID_HKR, "CameraClient"),
    ("C", "hkr GUID + name xa5-probe (isolates the name)", GUID_HKR, "xa5-probe"),
    ("D", "random GUID + name CameraClient (isolates the GUID)", GUID_RANDOM, "CameraClient"),
    ("E", "own fixed GUID + name xa5-probe (any fixed GUID?)", GUID_FIXED, "xa5-probe"),
    ("F", "libfuji-style GUID (hkr GUID with last 4 bytes zero) + name xa5-probe", GUID_HKR[:12] + bytes(4), "xa5-probe"),
    ("G", "hkr GUID first 12 bytes + random last 4 bytes + name xa5-probe (prefix check?)", GUID_HKR[:12] + bytes(4), "xa5-probe"),
]


def build_init(guid: bytes, name: str) -> bytes:
    pkt = bytearray(PACKET_LEN)
    struct.pack_into("<II", pkt, 0, PACKET_LEN, 1)
    struct.pack_into("<I", pkt, 8, MAGIC)
    pkt[12:28] = guid
    raw = name.encode("utf-16-le")
    max_name = PACKET_LEN - 28 - 2  # keep a terminating zero
    pkt[28:28 + min(len(raw), max_name)] = raw[:max_name]
    return bytes(pkt)


def decode_reply(data: bytes) -> str:
    if not data:
        return "no data (camera closed the connection)"
    if len(data) < 8:
        return f"short reply {data.hex()}"
    length, ptype = struct.unpack_from("<II", data, 0)
    text = f"len={length} type={ptype} ({TYPES.get(ptype, 'unknown')}) raw={data.hex()}"
    if ptype == 5 and len(data) >= 12:
        reason = struct.unpack_from("<I", data, 8)[0]
        text += f" reason=0x{reason:04x} ({REASONS.get(reason, 'unknown')})"
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ip", default="192.168.0.1", help="camera address (default 192.168.0.1)")
    ap.add_argument("--seq", "--only", dest="seq",
                    help="ordered, comma separated variant letters, repeats allowed, for example A,A,B")
    ap.add_argument("--no-stop", action="store_true", help="keep going after the camera accepts")
    ap.add_argument("--pause", type=float, default=2.0, help="seconds between variants")
    ap.add_argument("--dry-run", action="store_true", help="print packets, do not connect")
    args = ap.parse_args()

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outdir = os.path.join(repo, "captures", "wifi-gphoto2")
    os.makedirs(outdir, exist_ok=True)
    logpath = os.path.join(outdir, f"{datetime.date.today()}-hello-probe.txt")
    log = open(os.devnull, "w") if args.dry_run else open(logpath, "a", encoding="utf-8")

    def say(msg: str) -> None:
        print(msg)
        if not args.dry_run:  # a dry run must not touch real logs
            log.write(msg + "\n")
            log.flush()

    by_letter = {v[0]: v for v in VARIANTS}
    order = [x.strip().upper() for x in args.seq.split(",")] if args.seq else [v[0] for v in VARIANTS]
    unknown = [x for x in order if x not in by_letter]
    if unknown:
        ap.error(f"unknown variant letter(s): {','.join(unknown)}")
    say(f"# hello probe {datetime.datetime.now().isoformat(timespec='seconds')} camera={args.ip}:{PORT}")
    for step, letter in enumerate(order, 1):
        _, desc, guid, name = by_letter[letter]
        if letter in ("A", "D"):
            guid = os.urandom(16)  # a fresh random GUID per attempt for the random-GUID variants
        elif letter == "G":
            guid = GUID_HKR[:12] + os.urandom(4)
        pkt = build_init(guid, name)
        say(f"\n[{step}:{letter}] {desc}")
        say(f"    sent {len(pkt)} bytes: {pkt.hex()}")
        if args.dry_run:
            continue
        try:
            with socket.create_connection((args.ip, PORT), timeout=3) as s:
                s.settimeout(3)
                s.sendall(pkt)
                try:
                    reply = s.recv(1024)
                except socket.timeout:
                    reply = None
            say("    reply: " + ("timeout, no reply in 3 s" if reply is None else decode_reply(reply)))
        except OSError as exc:
            say(f"    connect or send failed: {exc}")
            reply = None
        if reply and len(reply) >= 8 and struct.unpack_from("<I", reply, 4)[0] == 2:
            if args.no_stop:
                say("    ACCEPTED by the camera. Connection closed without sending anything else.")
            else:
                say("    ACCEPTED by the camera. Stopping here. Connection closed without sending anything else.")
                break
        time.sleep(args.pause)
    say(f"\n# log: {logpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
