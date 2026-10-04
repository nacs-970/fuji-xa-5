"""Remote shooting for Fujifilm X-A cameras over Wi-Fi: live view, shutter, download.

Protocol notes: docs/protocol/wifi.md. Tested on an X-A5 (firmware 1.21) only.
Join the camera's Wi-Fi first (camera screen: WIRELESS COMMUNICATION). One Camera is one session, and the
camera leaves wireless mode when the session ends.

    with Camera() as cam:
        cam.start_live()
        jpeg = cam.frame()           # 640x480 JPEG
        cam.shoot()                  # WRITES TO THE SD CARD
        name, data = cam.download()  # the newest picture, full size

The order of the camera operations follows scripts/fuji_remote_probe.py, which is what ran on the real
camera. Change the order only after a real run shows a step is not needed.
"""
import logging
import select
import socket
import struct
import threading
import time

__all__ = ["Camera", "FujiError"]

log = logging.getLogger("fuji_xa")

PORT, EVENT_PORT, VIDEO_PORT = 55740, 55741, 55742
# The camera checks only the first 12 bytes of the client GUID. This is the value every successful X-A5
# session used (the public fuji-cam-wifi-tool GUID).
GUID = bytes.fromhex("ada5485d87b27f0bd3d5ded00278a8c0")
OK = 0x2001

P_EVENTS, P_CAMERA_STATE, P_CLIENT_STATE = 0xD212, 0xDF00, 0xDF01
P_IMAGE_GET_VER, P_GET_OBJ_VER, P_REMOTE_VER, P_REMOTE_GET_OBJ_VER = 0xDF21, 0xDF22, 0xDF24, 0xDF25
P_OBJECT_COUNT, P_CORRECT_FILE_SIZE = 0xD222, 0xD227
REMOTE_MODE, IMAGE_VIEW_MODE, REMOTE_VERSION = 5, 11, 0x2000C
CHUNK = 0x100000


class FujiError(Exception):
    """The camera refused or did something unexpected. `rcode` is the PTP response code, if any."""

    def __init__(self, message, rcode=None):
        super().__init__(message)
        self.rcode = rcode


def _recv(s, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("the camera closed the connection")
        buf += chunk
    return bytes(buf)


def _close(s):
    try:
        s.shutdown(socket.SHUT_RDWR)   # wakes a thread that is blocked in recv
    except OSError:
        pass
    s.close()


def _init_packet(name):
    pkt = bytearray(82)
    struct.pack_into("<III", pkt, 0, 82, 1, 0x8F53E4F2)
    pkt[12:28] = GUID
    raw = name.encode("utf-16-le")[:52]
    pkt[28:28 + len(raw)] = raw
    return bytes(pkt)


class Camera:
    """One session with the camera. Connects in the constructor; use it as a context manager.

    `wait` is how long to wait when the camera may be asking the user to accept on its own screen.
    """

    remote_version = None   # P_REMOTE_VER as the camera reports it, None if it did not answer

    def __init__(self, ip="192.168.0.1", name="xa5-probe", wait=60.0):
        self.ip, self.wait = ip, wait
        self.tid = 0
        self.props = {}                    # last value of each property the camera reported as changed
        self._ctl = self._ev = self._vid = self._reader = None
        self._session = self._viewing = False
        self._capture_tid = None           # transaction id of InitiateOpenCapture, needed to end it
        self._cond = threading.Condition()
        self._frame, self._frame_n, self._seen, self._dead = None, 0, 0, False
        try:
            self._ctl = self._handshake(name)
            time.sleep(0.05)
            self.op(0x1002, (1,), ok=(OK, 0x201E), timeout=wait)   # OpenSession, or already open
            self._session = True
            deadline = time.time() + wait
            while True:
                self.events()
                if self.props.get(P_CAMERA_STATE):
                    break
                if time.time() > deadline:
                    raise FujiError("the camera stayed in 'wait for access'. Accept on the camera screen.")
                time.sleep(0.5)
            for prop in (P_GET_OBJ_VER, P_REMOTE_GET_OBJ_VER, P_IMAGE_GET_VER, P_REMOTE_VER):
                rcode, data = self.op(0x1015, (prop,), ok=None)
                if prop == P_REMOTE_VER and rcode == OK and len(data) in (2, 4):
                    self.remote_version = int.from_bytes(data, "little")
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # --- PTP over the control socket ---------------------------------------------------------------

    def _handshake(self, name):
        """Send the init packet, up to 4 tries. The camera seems to accept only the client name it registered
        last: a different name was refused (0x201D) until the user pressed "change" on the camera. The camera
        also once refused a good init and took a later one (cause unknown)."""
        msg = ""
        for delay in (0, 1, 2, 4):
            time.sleep(delay)
            s = None
            try:
                s = socket.create_connection((self.ip, PORT), timeout=5)
                s.sendall(_init_packet(name))
                length, ptype = struct.unpack("<II", _recv(s, 8))
                rest = _recv(s, length - 8)
                if ptype == 2:
                    return s
                reason = struct.unpack_from("<I", rest)[0] if len(rest) >= 4 else 0
                msg = f"init rejected, reason 0x{reason:04x}"
            except OSError as exc:
                msg = f"init failed: {exc}"
            log.warning(msg)
            if s:
                _close(s)
        raise FujiError(f"{msg}. Is WIRELESS COMMUNICATION open on the camera? If it is, the camera may expect "
                        f"the client name it registered last: use that name (--name), or press 'change' on "
                        f"the camera to register '{name}'.")

    def op(self, code, params=(), data=None, ok=(OK,), timeout=10.0):
        """Run one PTP operation. Returns (response code, data). Raises FujiError unless the code is in `ok`
        (`ok=None` accepts any code)."""
        self.tid += 1
        s = self._ctl
        s.settimeout(timeout)
        s.sendall(struct.pack("<IHHI", 12 + 4 * len(params), 1, code, self.tid)
                  + b"".join(struct.pack("<I", p) for p in params))
        if data is not None:
            s.sendall(struct.pack("<IHHI", 12 + len(data), 2, code, self.tid) + data)
        payload = b""
        while True:
            length, ctype, rcode, _ = struct.unpack("<IHHI", _recv(s, 12))
            body = _recv(s, length - 12)
            if ctype == 2:
                payload += body
            elif ctype == 3:
                break
            else:
                raise FujiError(f"unexpected container type {ctype} after operation 0x{code:04x}")
        log.debug("operation 0x%04x %s -> 0x%04x, %d bytes", code, params, rcode, len(payload))
        if ok is not None and rcode not in ok:
            raise FujiError(f"operation 0x{code:04x} answered 0x{rcode:04x}", rcode)
        return rcode, payload

    def set_prop(self, prop, value, size=2, ok=(OK,), timeout=10.0):
        return self.op(0x1016, (prop,), data=value.to_bytes(size, "little"), ok=ok, timeout=timeout)[0]

    def events(self):
        """Read the camera's list of changed properties. Returns {property: value}."""
        data = self.op(0x1015, (P_EVENTS,))[1]
        count = struct.unpack_from("<H", data)[0] if len(data) >= 2 else 0
        evs = dict(struct.unpack_from("<HI", data, 2 + 6 * i) for i in range(min(count, (len(data) - 2) // 6)))
        self.props.update(evs)
        log.debug("events %s", {f"0x{k:04x}": hex(v) for k, v in evs.items()})
        return evs

    # --- live view and shutter -----------------------------------------------------------------------

    def start_live(self):
        """Enter remote mode and start live view. CHANGES CAMERA STATE (the official app does the same)."""
        if self._capture_tid is not None:
            return
        if self._viewing:   # 2026-10-05: setting remote mode again made the X-A5 close the connection
            raise FujiError("live view after a download is not possible in the same session. Start a new one.")
        self.set_prop(P_CLIENT_STATE, REMOTE_MODE, timeout=self.wait)
        self.events()
        if self.remote_version is not None:
            self.set_prop(P_REMOTE_VER, REMOTE_VERSION, 4)
            self.events()
        self._capture_tid = self.tid + 1
        self.op(0x101C, (0, 0), timeout=self.wait)   # InitiateOpenCapture: opens the event and video ports
        self.events()
        time.sleep(0.05)
        self._ev = self._connect(EVENT_PORT)
        self._vid = self._connect(VIDEO_PORT)
        self._frame_n = self._seen = 0
        self._dead = False
        self._reader = threading.Thread(target=self._read_frames, args=(self._vid,), daemon=True)
        self._reader.start()

    def _connect(self, port):
        for attempt in range(5):
            try:
                return socket.create_connection((self.ip, port), timeout=3)
            except OSError as exc:
                log.debug("port %d, attempt %d: %s", port, attempt + 1, exc)
                time.sleep(0.2)
        raise FujiError(f"could not connect to camera port {port}")

    def _read_frames(self, s):
        """Read live-view frames for as long as the socket lives. The camera blocks if nobody reads them."""
        try:
            while True:
                total = struct.unpack_from("<I", _recv(s, 18))[0]   # 18-byte header, then the JPEG
                jpeg = _recv(s, total - 18)
                with self._cond:
                    self._frame, self._frame_n = jpeg, self._frame_n + 1
                    self._cond.notify_all()
        except (OSError, struct.error):
            pass
        finally:
            with self._cond:
                self._dead = True
                self._cond.notify_all()

    def frame(self, timeout=5.0):
        """The next live-view JPEG (640x480): a frame newer than the one the last call returned."""
        if self._capture_tid is None:
            raise FujiError("live view is not running, call start_live() first")
        with self._cond:
            self._cond.wait_for(lambda: self._frame_n > self._seen or self._dead, timeout)
            if self._frame_n <= self._seen:
                raise FujiError("no live-view frame arrived")
            self._seen = self._frame_n
            return self._frame

    def shoot(self, timeout=15.0):
        """Release the shutter once. WRITES TO THE SD CARD. Starts live view if it is not running.

        Returns True when the camera reported the picture complete, False if that did not arrive in
        `timeout` seconds. The picture exists in both cases once the camera accepted the shutter.
        """
        self.start_live()
        self.op(0x100E, (0, 0), timeout=self.wait)   # InitiateCapture, live view must be open
        end = time.time() + timeout
        while time.time() < end:
            try:
                if select.select([self._ev], [], [], 0.3)[0]:
                    self._ev.settimeout(5)
                    length, _, code = struct.unpack("<IHH", _recv(self._ev, 8))
                    _recv(self._ev, max(length - 8, 0))
                    if code == 0x400D:   # PTP CaptureComplete
                        return True
            except OSError as exc:
                log.warning("event socket: %s", exc)
                return False
            self.events()
        log.warning("shutter accepted, but no CaptureComplete event within %.0f s", timeout)
        return False

    # --- reading pictures ----------------------------------------------------------------------------

    def _stop_live(self):
        """End open capture while the reader still drains the video socket, then close the sockets."""
        if self._capture_tid is None:
            return
        tid, self._capture_tid = self._capture_tid, None
        try:
            self.op(0x1018, (tid,), ok=None)   # TerminateOpenCapture
        finally:
            for s in (self._ev, self._vid):
                if s:
                    _close(s)
            self._ev = self._vid = None
            if self._reader:
                self._reader.join(2)
        time.sleep(0.5)

    def _enter_image_view(self):
        self.events()
        self.set_prop(P_CAMERA_STATE, 6, ok=None)
        self.events()
        self.events()
        self.set_prop(P_CLIENT_STATE, IMAGE_VIEW_MODE, timeout=self.wait)
        self.op(0x1015, (P_REMOTE_GET_OBJ_VER,), ok=None)
        self.set_prop(P_REMOTE_GET_OBJ_VER, 5, 4, ok=None)
        for _ in range(7):   # the picture count shows up in the events a moment later
            self.events()
            if self.props.get(P_OBJECT_COUNT):
                break
            time.sleep(0.5)
        self._viewing = True

    def download(self, handle=1):
        """Return (file name, bytes) of a picture on the card. Handle 1 is the newest, 2 the next older.
        Ends live view first. GetNumObjects always answers 0 on the X-A5, so the count is not checked."""
        self._stop_live()
        if not self._viewing:
            self._enter_image_view()
        info = self.op(0x1008, (handle,))[1]   # GetObjectInfo
        if len(info) < 54:
            raise FujiError("object info too short")
        size = struct.unpack_from("<I", info, 8)[0]
        name = info[53:53 + 2 * info[52]].decode("utf-16-le", errors="replace").rstrip("\x00")
        if not 0 < size <= 64 * 1024 * 1024:
            raise FujiError(f"{name}: implausible size {size}")
        self.set_prop(P_CORRECT_FILE_SIZE, 1, ok=None)
        got = bytearray()
        try:
            while len(got) < size:
                chunk = self.op(0x101B, (handle, len(got), min(CHUNK, size - len(got))), timeout=60)[1]
                if not chunk:
                    raise FujiError(f"{name}: the camera sent nothing at byte {len(got)} of {size}")
                got += chunk
        finally:
            self.set_prop(P_CORRECT_FILE_SIZE, 0, ok=None)
        return name, bytes(got)

    def close(self):
        """End the session: TerminateOpenCapture if live view runs, then CloseSession."""
        if self._ctl is None:
            return
        try:
            self._stop_live()
            if self._session:
                self.op(0x1003, ok=None)
        except (OSError, FujiError) as exc:
            log.warning("cleanup failed: %s", exc)
        finally:
            _close(self._ctl)
            self._ctl = None
