#!/usr/bin/env python3
"""Put the X-A5 into Fuji's Wi-Fi remote mode, read live-view frames, optionally take one photo.

Plan 03 follow-up. The sequence follows what public projects document (libfuji, MIT); nothing here is
confirmed for the X-A5 until it runs. Stages, each includes the ones before it:

  read   open a session, read the camera's event list and version properties, say which client mode the
         public notes would pick. Read-only.
  mode   additionally set the client-state property 0xdf01 to that mode and the remote-version property
         0xdf24. CHANGES CAMERA STATE (the official app does this on connect). Only if the mode is
         remote mode (5), unless --force-mode is given.
  live   additionally InitiateOpenCapture (0x101c), connect the event (55741) and live-view (55742)
         sockets, read frames for a few seconds, save one JPEG, then TerminateOpenCapture.
         CHANGES CAMERA STATE. Does not take a photo.
  download  separate path (no remote mode): switch to the image-view client mode, read the object count,
         download the newest picture to --photo-out. Reads pictures only, deletes and writes nothing on the
         card. CHANGES CAMERA STATE (client mode and transfer properties).
  shoot  (with --download-after: then end live view, switch to image view, download the newest picture)
         like live, then take ONE photo with InitiateCapture (0x100e, 0, 0) while live view is open, and
         log what the camera reports. WRITES TO THE SD CARD. Refuses to run without --yes-take-photo.
         The older Fuji remote flow in public notes (fuji-cam-wifi-tool) releases the shutter this way.
         libgphoto2's focus properties (0xd207, 0xd208) answer "not supported" on the X-A5, see
         docs/findings/2026-10-04-wifi-remote-mode-probe.md.

The camera may show a client name or a yes/no dialog and wait for the user. Watch the camera screen and
accept it. The camera goes back to shooting mode when the connection ends, so open WIRELESS COMMUNICATION
again before each run.

Run one per Wi-Fi join:
    scripts/with_camera_wifi.sh -- python3 scripts/fuji_remote_probe.py --stage live

Output also goes to captures/wifi-gphoto2/<date>-remote-probe.txt (git-ignored). The serial number is
never printed.
"""
import argparse
import datetime
import os
import socket
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fuji_hello_probe import GUID_HKR, PORT, TYPES, build_init  # noqa: E402
from fuji_session_probe import RC, parse_container, read_container  # noqa: E402

EVENT_PORT = 55741
VIDEO_PORT = 55742

P_EVENTS = 0xD212       # list of changed properties (u16 count, then u16 code + u32 value each)
P_CAMERA_STATE = 0xDF00
P_CLIENT_STATE = 0xDF01
P_IMAGE_GET_VER = 0xDF21
P_GET_OBJ_VER = 0xDF22
P_REMOTE_VER = 0xDF24
P_REMOTE_GET_OBJ_VER = 0xDF25
REMOTE_VERSION_TO_SET = 0x2000C   # the "highest" value the public notes say Fuji's app sets

CAMERA_STATES = {0: "wait for access", 1: "multiple transfer", 2: "full access", 3: "PC autosave", 6: "remote access"}
CLIENT_MODES = {1: "view multiple", 2: "view all images", 3: "old remote", 5: "remote mode"}

OC_OPEN, OC_CLOSE = 0x1002, 0x1003
OC_GET_NUM_OBJECTS, OC_GET_OBJECT_INFO, OC_INIT_CAPTURE = 0x1006, 0x1008, 0x100E
OC_GET_PARTIAL_OBJECT = 0x101B
P_OBJECT_COUNT = 0xD222
P_ENABLE_CORRECT_FILE_SIZE = 0xD227
MODE_REMOTE_IMG_VIEW = 11   # "image gallery in remote mode" (libfuji notes)
CHUNK = 0x100000
OC_GET_PROP, OC_SET_PROP = 0x1015, 0x1016
OC_INIT_OPEN_CAPTURE, OC_TERMINATE_OPEN_CAPTURE = 0x101C, 0x1018


class Ptp:
    """USB-style PTP containers over the control socket."""

    def __init__(self, sock):
        self.s = sock
        self.tid = 0
        self.last_resp = b""   # response parameters of the last operation

    def op(self, code, params=(), data=None, timeout=10.0):
        self.tid += 1
        tid = self.tid
        self.s.sendall(struct.pack("<IHHI", 12 + 4 * len(params), 1, code, tid)
                       + b"".join(struct.pack("<I", p) for p in params))
        if data is not None:
            self.s.sendall(struct.pack("<IHHI", 12 + len(data), 2, code, tid) + data)
        payload = b""
        while True:
            _, ctype, rcode, _, body = parse_container(read_container(self.s, timeout))
            if ctype == 2:
                payload += body
            elif ctype == 3:
                self.last_resp = body
                return rcode, payload, tid
            else:
                raise RuntimeError(f"unexpected container type {ctype}")

    def get_prop(self, prop, timeout=10.0):
        rcode, data, _ = self.op(OC_GET_PROP, (prop,), timeout=timeout)
        return rcode, data

    def set_prop(self, prop, value: int, size: int, timeout=10.0):
        fmt = {2: "<H", 4: "<I"}[size]
        rcode, _, _ = self.op(OC_SET_PROP, (prop,), data=struct.pack(fmt, value), timeout=timeout)
        return rcode


def as_int(data: bytes):
    if len(data) == 2:
        return struct.unpack("<H", data)[0]
    if len(data) == 4:
        return struct.unpack("<I", data)[0]
    return None


def parse_events(data: bytes):
    if len(data) < 2:
        return []
    n = struct.unpack_from("<H", data, 0)[0]
    out = []
    for i in range(n):
        off = 2 + 6 * i
        if off + 6 > len(data):
            break
        out.append(struct.unpack_from("<HI", data, off))
    return out


def download_latest(ptp, say, rcname, events, out, handle=None) -> int:
    """Switch to the image-view client mode, read the object count, download one picture."""

    def ev_value(evs, code):
        for c, v in evs or []:
            if c == code:
                return v
        return None

    say("Image-view setup (as in libfuji's remote gallery flow)")
    events()
    say(f"  camera state 0xdf00 = 6: {rcname(ptp.set_prop(P_CAMERA_STATE, 6, 2))}")
    events()
    evs = events()
    say(f"  client state 0xdf01 = {MODE_REMOTE_IMG_VIEW}: {rcname(ptp.set_prop(P_CLIENT_STATE, MODE_REMOTE_IMG_VIEW, 2))}")
    rcode, data = ptp.get_prop(P_REMOTE_GET_OBJ_VER)
    say(f"  get 0xdf25: {rcname(rcode)} value={as_int(data)}")
    say(f"  set 0xdf25 = 5: {rcname(ptp.set_prop(P_REMOTE_GET_OBJ_VER, 5, 4))} (not fatal)")
    evs = events()

    count = ev_value(evs, P_OBJECT_COUNT)
    for _ in range(6):
        if count:
            break
        time.sleep(0.5)
        count = ev_value(events(), P_OBJECT_COUNT)
    rcode, _, _ = ptp.op(OC_GET_NUM_OBJECTS, (0xFFFFFFFF, 0, 0))
    num = struct.unpack_from("<I", ptp.last_resp, 0)[0] if rcode == 0x2001 and len(ptp.last_resp) >= 4 else None
    say(f"Object count: event 0xd222 = {count}, GetNumObjects = {num}")
    if not (count or num):
        say("  no objects reported, stopping")
        return 5
    if handle is None:
        handle = 1   # handle 1 is the newest picture on the X-A5 (confirmed 2026-10-04 with two pictures)
        say("  no --handle given: using handle 1 (the newest)")

    rcode, data, _ = ptp.op(OC_GET_OBJECT_INFO, (handle,))
    say(f"GetObjectInfo handle {handle}: {rcname(rcode)}")
    if rcode != 0x2001 or len(data) < 54:
        return 6
    fmt, _, size = struct.unpack_from("<HHI", data, 4)
    name_len = data[52]
    name = data[53:53 + 2 * name_len].decode("utf-16-le", errors="replace").rstrip("\x00")
    say(f"  file name {name!r}, format 0x{fmt:04x}, size {size} bytes")
    if size == 0 or size > 64 * 1024 * 1024:
        say("  size not plausible, stopping")
        return 6

    say(f"Download property 0xd227 = 1: {rcname(ptp.set_prop(P_ENABLE_CORRECT_FILE_SIZE, 1, 2))} (not fatal)")
    got, t0 = bytearray(), time.time()
    try:
        while len(got) < size:
            want = min(CHUNK, size - len(got))
            rcode, chunk, _ = ptp.op(OC_GET_PARTIAL_OBJECT, (handle, len(got), want), timeout=60)
            if rcode != 0x2001 or not chunk:
                say(f"  GetPartialObject at {len(got)}: {rcname(rcode)}, {len(chunk)} bytes")
                break
            got += chunk
    finally:
        say(f"Download property 0xd227 = 0: {rcname(ptp.set_prop(P_ENABLE_CORRECT_FILE_SIZE, 0, 2))} (not fatal)")
    if not got:
        return 7
    with open(out, "wb") as fh:
        fh.write(got)
    start = "JPEG marker" if got[:2] == b"\xff\xd8" else got[:4].hex()
    say(f"  saved {len(got)} of {size} bytes to {out} in {time.time() - t0:.1f} s; starts with {start}")
    return 0 if len(got) == size else 8


def shoot_with_liveview(ptp, say, rcname, events, vid_sock, ev_sock, wait: float) -> int:
    """With open capture running, send one InitiateCapture (0x100e, 0, 0) and watch what the camera does.

    The older Fuji remote flow (fuji-cam-wifi-tool notes) releases the shutter with this one command while
    live view is open. The live-view socket is drained in a thread so the camera is not blocked on it.
    """
    stop = threading.Event()
    frames = [0]

    def drain():
        vid_sock.settimeout(1)
        while not stop.is_set():
            try:
                chunk = vid_sock.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                return
            if not chunk:
                return
            frames[0] += len(chunk)

    t = threading.Thread(target=drain, daemon=True)
    t.start()
    try:
        rcode, _, _ = ptp.op(OC_GET_NUM_OBJECTS, (0xFFFFFFFF, 0, 0))
        before = struct.unpack_from("<I", ptp.last_resp, 0)[0] if rcode == 0x2001 and len(ptp.last_resp) >= 4 else None
        say(f"GetNumObjects before: {rcname(rcode)}, count {before}")

        say("InitiateCapture (0x100e, 0, 0): releases the shutter once")
        t0 = time.time()
        rcode, _, _ = ptp.op(OC_INIT_CAPTURE, (0, 0), timeout=wait)
        say(f"  {rcname(rcode)} after {time.time() - t0:.1f} s")
        if rcode != 0x2001:
            return 7

        say(f"Watching the event socket and properties for {wait:.0f} s")
        t_end = time.time() + wait
        ev_sock.settimeout(0.5)
        seen = ""
        while time.time() < t_end:
            try:
                data = ev_sock.recv(4096)
                if data:
                    say(f"  event socket: {len(data)} bytes {data.hex()}")
                    t_end = min(t_end, time.time() + 3)
            except socket.timeout:
                pass
            except OSError as exc:
                say(f"  event socket: {exc}")
                break
            rcode, d = ptp.get_prop(P_EVENTS)
            cur = ", ".join(f"0x{c:04x}={v:#x}" for c, v in parse_events(d)) if rcode == 0x2001 else rcname(rcode)
            if cur != seen:
                say(f"  properties: {cur}")
                seen = cur
            time.sleep(0.3)
        rcode, _, _ = ptp.op(OC_GET_NUM_OBJECTS, (0xFFFFFFFF, 0, 0))
        after = struct.unpack_from("<I", ptp.last_resp, 0)[0] if rcode == 0x2001 and len(ptp.last_resp) >= 4 else None
        say(f"GetNumObjects after: {rcname(rcode)}, count {after}")
        say(f"Live view delivered {frames[0]} bytes during the shot. Check the camera screen and the SD card.")
        return 0
    finally:
        stop.set()
        t.join(2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ip", default="192.168.0.1")
    ap.add_argument("--stage", choices=("read", "mode", "live", "shoot", "download"), default="read")
    ap.add_argument("--name", default="xa5-probe", help="client name shown on the camera")
    ap.add_argument("--force-mode", type=int, help="set this client mode instead of the one the notes pick")
    ap.add_argument("--seconds", type=float, default=3.0, help="live-view read time")
    ap.add_argument("--out", default="/tmp/xa5-liveview.jpg", help="where to save one live-view JPEG")
    ap.add_argument("--wait", type=float, default=60.0, help="seconds to wait for the user on the camera")
    ap.add_argument("--photo-out", default="/tmp/xa5-photo.jpg", help="stage download: where to save the picture")
    ap.add_argument("--handle", type=int, help="stage download: object handle (default: 1, the newest)")
    ap.add_argument("--download-after", action="store_true",
                    help="stage shoot: after the shot, end live view, switch to image view and download the newest picture")
    ap.add_argument("--yes-take-photo", action="store_true", help="required for stage shoot: takes one photo")
    ap.add_argument("--shoot-wait", type=float, default=30.0, help="seconds to wait for the new picture")
    args = ap.parse_args()
    if args.stage == "shoot" and not args.yes_take_photo:
        print("stage shoot takes a photo and writes to the SD card. Add --yes-take-photo to confirm.")
        return 2

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outdir = os.path.join(repo, "captures", "wifi-gphoto2")
    os.makedirs(outdir, exist_ok=True)
    logpath = os.path.join(outdir, f"{datetime.date.today()}-remote-probe.txt")
    log = open(logpath, "a", encoding="utf-8")

    t_start = time.time()

    def say(msg=""):
        line = f"[+{time.time() - t_start:5.1f}s] {msg}" if msg else ""
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    def rcname(rc):
        return f"0x{rc:04x} ({RC.get(rc, '?')})"

    say(f"# remote probe {datetime.datetime.now().isoformat(timespec='seconds')} stage={args.stage} "
        f"camera={args.ip}:{PORT}")
    sock = None
    for attempt, delay in enumerate((0, 1, 2, 4), 1):
        time.sleep(delay)
        try:
            sock = socket.create_connection((args.ip, PORT), timeout=5)
            sock.settimeout(5)
            sock.sendall(build_init(GUID_HKR, args.name))
            raw = read_container(sock, 5)
        except (OSError, ConnectionError) as exc:
            say(f"init attempt {attempt}: {exc}")
            if sock:
                sock.close()
            sock = None
            continue
        ptype = struct.unpack_from("<II", raw, 0)[1]
        if ptype == 2:
            say(f"init attempt {attempt}: accepted (InitCommandAck)")
            break
        reason = struct.unpack_from("<I", raw, 8)[0] if len(raw) >= 12 else 0
        say(f"init attempt {attempt}: type={ptype} ({TYPES.get(ptype, '?')}) reason=0x{reason:04x}. "
            "If the camera shows a client name or an OK prompt, accept it on the camera now.")
        sock.close()
        sock = None
    if sock is None:
        say("init never accepted, stopping")
        return 2

    ptp = Ptp(sock)
    state = {"capture_tid": None, "terminated": False, "session": False}
    ev_sock = vid_sock = None
    rc_exit = 0
    try:
        time.sleep(0.05)

        say("OpenSession")
        rcode, _, _ = ptp.op(OC_OPEN, (1,), timeout=args.wait)
        say(f"  {rcname(rcode)}")
        if rcode not in (0x2001, 0x201E):
            return 3
        state["session"] = True

        def events():
            rcode, data = ptp.get_prop(P_EVENTS)
            if rcode != 0x2001:
                say(f"  events: {rcname(rcode)}")
                return None
            evs = parse_events(data)
            say("  events: " + (", ".join(f"0x{c:04x}={v:#x}" for c, v in evs) if evs else "none")
                + (f"   [raw {data.hex()}]" if not evs and data else ""))
            return evs

        say("Events (0xd212)")
        camera_state = None
        deadline = time.time() + args.wait
        while True:
            evs = events()
            for code, value in evs or []:
                if code == P_CAMERA_STATE:
                    camera_state = value
            if camera_state not in (None, 0) or time.time() > deadline:
                break
            say("  camera state unknown or 'wait for access', polling (accept on the camera if it asks)")
            time.sleep(0.5)
        say(f"  camera state 0xdf00: {camera_state} ({CAMERA_STATES.get(camera_state, '?')})")

        say("Version properties")
        values = {}
        for prop, label in ((P_GET_OBJ_VER, "get-object version 0xdf22"),
                            (P_REMOTE_GET_OBJ_VER, "remote get-object version 0xdf25"),
                            (P_IMAGE_GET_VER, "image-get version 0xdf21"),
                            (P_REMOTE_VER, "remote version 0xdf24")):
            rcode, data = ptp.get_prop(prop)
            val = as_int(data) if rcode == 0x2001 else None
            values[prop] = val
            say(f"  {label}: {rcname(rcode)}" + (f" value={val:#x}" if val is not None else
                                                    (f" raw={data.hex()}" if data else "")))
        remote_version = values.get(P_REMOTE_VER)

        # Mode choice as described in public notes (libfuji): remote mode if the camera reports a remote
        # version or is in remote-access state, otherwise a view/old-remote mode.
        if remote_version is not None or camera_state == 6:
            mode = 5
        elif camera_state == 1:
            mode = 1
        elif camera_state == 2:
            mode = 2
        elif camera_state == 3:
            mode = 3
        else:
            mode = 2
        say(f"Mode the public notes would pick: {mode} ({CLIENT_MODES.get(mode, '?')})")
        if args.stage == "read":
            say("stage read: stopping before any state change")
            return 0
        if args.stage == "download":
            return download_latest(ptp, say, rcname, events, args.photo_out, args.handle)
        if args.force_mode is not None:
            mode = args.force_mode
            say(f"  --force-mode: using {mode}")
        elif mode != 5:
            say("  not remote mode, so not setting it. Use --force-mode 5 to override.")
            return 0

        say(f"SetDevicePropValue 0xdf01 = {mode} (the camera may ask on its screen, waiting up to {args.wait:.0f} s)")
        rcode = ptp.set_prop(P_CLIENT_STATE, mode, 2, timeout=args.wait)
        say(f"  {rcname(rcode)}")
        if rcode != 0x2001:
            return 4
        events()

        if remote_version is not None:
            say(f"SetDevicePropValue 0xdf24 = {REMOTE_VERSION_TO_SET:#x}")
            rcode = ptp.set_prop(P_REMOTE_VER, REMOTE_VERSION_TO_SET, 4)
            say(f"  {rcname(rcode)}")
            events()
        if args.stage == "mode":
            say("stage mode: stopping before InitiateOpenCapture")
            return 0

        say("InitiateOpenCapture (0x101c, 0, 0)")
        state["capture_tid"] = ptp.tid + 1
        rcode, _, _ = ptp.op(OC_INIT_OPEN_CAPTURE, (0, 0), timeout=args.wait)
        say(f"  {rcname(rcode)}")
        if rcode != 0x2001:
            return 5
        events()
        time.sleep(0.05)

        say(f"Connecting event socket {EVENT_PORT} and live-view socket {VIDEO_PORT}")
        for port, label in ((EVENT_PORT, "event"), (VIDEO_PORT, "video")):
            s = None
            for attempt in range(1, 6):
                try:
                    s = socket.create_connection((args.ip, port), timeout=3)
                    break
                except OSError as exc:
                    say(f"  {label} connect attempt {attempt} failed: {exc}")
                    time.sleep(0.2)
            if s is None:
                return 6
            say(f"  {label} socket connected")
            if label == "event":
                ev_sock = s
            else:
                vid_sock = s

        if args.stage == "shoot":
            rc = shoot_with_liveview(ptp, say, rcname, events, vid_sock, ev_sock, args.shoot_wait)
            if rc != 0 or not args.download_after:
                return rc
            say("TerminateOpenCapture before switching to image view")
            rcode, _, _ = ptp.op(OC_TERMINATE_OPEN_CAPTURE, (state["capture_tid"],), timeout=10)
            say(f"  {rcname(rcode)}")
            state["terminated"] = True
            for sk in (ev_sock, vid_sock):
                sk.close()
            ev_sock = vid_sock = None
            time.sleep(0.5)
            return download_latest(ptp, say, rcname, events, args.photo_out, args.handle)

        say(f"Reading live-view frames for {args.seconds:.0f} s")
        vid_sock.settimeout(5)
        frames, best, sizes, t0 = 0, b"", [], time.time()
        while time.time() - t0 < args.seconds:
            try:
                head = b""
                while len(head) < 18:
                    chunk = vid_sock.recv(18 - len(head))
                    if not chunk:
                        raise ConnectionError("live-view socket closed")
                    head += chunk
                total = struct.unpack("<I", head[:4])[0]
                body = b""
                while len(body) < total - 18:
                    chunk = vid_sock.recv(total - 18 - len(body))
                    if not chunk:
                        raise ConnectionError("live-view socket closed")
                    body += chunk
            except (OSError, ConnectionError) as exc:
                say(f"  live-view read stopped: {exc}")
                break
            frames += 1
            frame = head + body
            soi = frame.find(b"\xff\xd8")
            if frames <= 3:
                say(f"  frame {frames}: total length {total}, header {head.hex()}, "
                    f"JPEG start at byte {soi if soi >= 0 else 'not found'}")
            if soi >= 0:
                sizes.append(len(frame) - soi)
                if len(frame) - soi >= len(best):
                    best = frame[soi:]
        elapsed = max(time.time() - t0, 0.001)
        if best:
            with open(args.out, "wb") as fh:
                fh.write(best)
            say(f"  saved the largest frame to {args.out} ({len(best)} bytes; frame sizes "
                f"{min(sizes)} to {max(sizes)} bytes)")
        say(f"  {frames} frames in {elapsed:.1f} s ({frames / elapsed:.1f} fps)")
        return 0 if frames else 7
    except (OSError, ConnectionError, RuntimeError, struct.error) as exc:
        say(f"ERROR: {exc}")
        rc_exit = 9
        return rc_exit
    finally:
        # Leave the camera tidy whatever happened.
        try:
            if state["capture_tid"] is not None and not state["terminated"]:
                say("TerminateOpenCapture")
                rcode, _, _ = ptp.op(OC_TERMINATE_OPEN_CAPTURE, (state["capture_tid"],), timeout=10)
                say(f"  {rcname(rcode)}")
                state["terminated"] = True
            if state["session"]:
                say("CloseSession")
                rcode, _, _ = ptp.op(OC_CLOSE, (), timeout=10)
                say(f"  {rcname(rcode)}")
        except (OSError, ConnectionError, RuntimeError, struct.error) as exc:
            say(f"  cleanup failed: {exc}")
        for s in (ev_sock, vid_sock, sock):
            try:
                if s:
                    s.close()
            except OSError:
                pass
        say(f"# log: {logpath}")


if __name__ == "__main__":
    sys.exit(main())
