#!/usr/bin/env python3
"""A fake Fuji Wi-Fi camera for testing our probe scripts without hardware.

It is built from public protocol notes (libfuji, hkr tool) and from what the X-A5 was seen to do in this
repo's logs. It is NOT a recording of the X-A5. Treat it as a test double: passing against it proves the
script's parsing and sequencing, not that the real camera agrees.

Listens on 127.0.0.1: 55740 (control), and after InitiateOpenCapture 55741 (events) and 55742 (live view).
Run it, then point a script at it:
    python3 tests/fake_camera/fake_fuji_camera.py &
    python3 scripts/fuji_remote_probe.py --ip 127.0.0.1 --stage live
"""
import socket
import struct
import threading
import time

GUID_PREFIX = bytes.fromhex("ada5485d87b27f0bd3d5ded0")  # the camera checks the first 12 bytes
HOST = "127.0.0.1"
FAKE_JPEG = b"\xff\xd8\xff\xe0" + bytes(range(256)) * 4500 + b"\xff\xd9"   # about 1.1 MB, two chunks
state = {"client_state": 2, "remote_ver": 0x20006, "capture_open": False, "objects": 3, "view": False,
         "events": None}


def listen(port):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, port))
    s.listen(1)
    return s


def recv_exact(c, n):
    buf = b""
    while len(buf) < n:
        chunk = c.recv(n - len(buf))
        if not chunk:
            raise ConnectionError
        buf += chunk
    return buf


def container(ctype, code, tid, payload=b""):
    return struct.pack("<IHHI", 12 + len(payload), ctype, code, tid) + payload


def video_server():
    srv = listen(55742)
    c, _ = srv.accept()
    jpeg = b"\xff\xd8\xff\xe0" + bytes(200) + b"\xff\xd9"
    for _ in range(100):
        total = 18 + len(jpeg)
        try:
            c.sendall(struct.pack("<I", total) + bytes(12) + b"\xfe\x7f" + jpeg)
        except OSError:
            break
        time.sleep(0.05)
    c.close()
    srv.close()


def event_server():
    srv = listen(55741)
    c, _ = srv.accept()
    state["events"] = c
    time.sleep(10)
    c.close()
    srv.close()


def announce_shot(c):
    """The three 28-byte events the X-A5 sent after a shot: ObjectAdded, 0xC001, CaptureComplete."""
    for code in (0xC004, 0xC001, 0x400D):
        time.sleep(0.1)
        try:
            c.sendall(struct.pack("<IHHI", 28, 4, code, 1) + struct.pack("<IIII", 0x0E, 0x0E, 0, 0))
        except OSError:
            return


def handle(c):
    init = recv_exact(c, 82)
    if init[12:24] != GUID_PREFIX:
        c.sendall(struct.pack("<III", 12, 5, 0x201D))
        return
    c.sendall(struct.pack("<II", 68, 2) + bytes(4) + bytes(range(16)) + "X-A5".encode("utf-16-le").ljust(40, b"\0"))
    while True:
        length = struct.unpack("<I", recv_exact(c, 4))[0]
        body = recv_exact(c, length - 4)
        ctype, code, tid = struct.unpack_from("<HHI", body, 0)
        params = [struct.unpack_from("<I", body, 8 + 4 * i)[0] for i in range((len(body) - 8) // 4)]
        if code == 0x1002 or code == 0x1003 or code == 0x101C or code == 0x1018:
            if code == 0x101C:
                state["capture_open"] = True
                threading.Thread(target=event_server, daemon=True).start()
                threading.Thread(target=video_server, daemon=True).start()
            c.sendall(container(3, 0x2001, tid))
            if code == 0x1003:
                return
        elif code == 0x1008:
            name = "DSCF0001.JPG\0".encode("utf-16-le")
            info = struct.pack("<IHHI", 0x10001, 0x3801, 0, len(FAKE_JPEG)) + bytes(40) + bytes([13]) + name
            c.sendall(container(2, code, tid, info) + container(3, 0x2001, tid))
        elif code == 0x101B:
            chunk = FAKE_JPEG[params[1]:params[1] + params[2]]
            c.sendall(container(2, code, tid, chunk) + container(3, 0x2001, tid))
        elif code == 0x1006:
            c.sendall(container(3, 0x2001, tid, struct.pack("<I", state["objects"])))
        elif code == 0x100E:
            if state["capture_open"]:
                state["objects"] += 1
                if state["events"]:
                    threading.Thread(target=announce_shot, args=(state["events"],), daemon=True).start()
            c.sendall(container(3, 0x2001, tid))
        elif code == 0x1015:
            prop = params[0]
            if prop == 0xD212:
                evs = [(0xDF00, 6 if state["client_state"] in (5, 11) else 2)]
                if state["view"]:
                    evs.append((0xD222, state["objects"]))
                payload = struct.pack("<H", len(evs)) + b"".join(struct.pack("<HI", a, b) for a, b in evs)
                c.sendall(container(2, code, tid, payload) + container(3, 0x2001, tid))
            elif prop == 0xDF24:
                c.sendall(container(2, code, tid, struct.pack("<I", state["remote_ver"])) + container(3, 0x2001, tid))
            elif prop in (0xDF21, 0xDF22, 0xDF25):
                c.sendall(container(2, code, tid, struct.pack("<I", 4)) + container(3, 0x2001, tid))
            else:
                c.sendall(container(3, 0x200A, tid))
        elif code == 0x1016:
            dlen = struct.unpack("<I", recv_exact(c, 4))[0]
            dbody = recv_exact(c, dlen - 4)
            if params[0] == 0xDF01:
                state["client_state"] = struct.unpack_from("<H", dbody, 8)[0]
                state["view"] = state["client_state"] == 11
            c.sendall(container(3, 0x2001, tid))
        else:
            c.sendall(container(3, 0x2005, tid))


def main():
    srv = listen(55740)
    print("fake camera listening on 55740", flush=True)
    while True:
        c, _ = srv.accept()
        try:
            handle(c)
        except (ConnectionError, OSError):
            pass
        finally:
            c.close()


if __name__ == "__main__":
    main()
