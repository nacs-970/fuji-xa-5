"""fuji-xa: live view, shutter and download for a Fujifilm X-A camera over Wi-Fi.

Open WIRELESS COMMUNICATION on the camera and join its Wi-Fi first. One command is one session.
"""
import argparse
import logging
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import Camera, FujiError

PAGE = b"""<!doctype html><meta charset="utf-8"><title>fuji-xa</title>
<body style="margin:0;background:#000;color:#fff;font:16px sans-serif">
<img src="/stream" style="width:100%">
<p style="margin:8px">Hold <b>Space</b> or the button to focus. The lens focuses while you hold, and keeps it when you let go.
<button id=f style="font-size:20px;padding:8px 24px">Focus</button></p>
<script>
const f = document.getElementById("f");
let down = false, chain = Promise.resolve();   // "up" is sent only after "down" was answered
const press = d => { if (d !== down) { down = d; chain = chain.then(() => fetch("/focus/" + (d ? "down" : "up"), {method: "POST"})).catch(() => {}); } };
f.onpointerdown = () => press(true);
for (const e of ["pointerup", "pointerleave", "pointercancel"]) f.addEventListener(e, () => press(false));
addEventListener("keydown", e => { if (e.code === "Space") { e.preventDefault(); press(true); } });
addEventListener("keyup", e => { if (e.code === "Space") press(false); });
addEventListener("blur", () => press(false));
</script>"""


def serve(cam, host, port, seconds=None):
    """Live view as an MJPEG stream: open http://HOST:PORT/ in a browser. Runs until Ctrl-C or `seconds`.

    The page has a Focus button (and the Space key): hold = half press, the camera focuses at its own point (Camera.focus).

    ponytail: no login, and several viewers share the frames (each sees a part). Any local web page can press Focus. Keep
    HOST on 127.0.0.1.
    """
    stop, failed, hold = threading.Event(), [], []

    def let_go():
        for timer in hold:
            timer.cancel()
        hold.clear()
        cam.release_focus()

    def finish():
        stop.set()
        srv.shutdown()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            if self.path != "/stream":
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(PAGE)))
                self.end_headers()
                self.wfile.write(PAGE)
                return
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while not stop.is_set():
                    jpeg = cam.frame()
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n%s\r\n"
                                     % (len(jpeg), jpeg))
            except OSError:
                pass   # the viewer left
            except FujiError as exc:   # the camera stopped sending, or the session is ending
                if not stop.is_set():
                    failed.append(exc)
                    threading.Thread(target=finish).start()

        def do_POST(self):
            try:
                if self.path == "/focus/down":
                    cam.focus()
                    timer = threading.Timer(10, let_go)   # the browser never said "up" (tab closed, key held)
                    timer.daemon = True
                    timer.start()
                    hold.append(timer)
                elif self.path == "/focus/up":
                    let_go()
                else:
                    return self.send_error(404)
            except (FujiError, OSError) as exc:
                return self.send_error(500, str(exc).splitlines()[0])
            self.send_response(204)
            self.end_headers()

        def log_message(self, *args):
            pass

    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"live view: http://{host}:{srv.server_address[1]}/  (Ctrl-C to stop)", flush=True)
    if seconds:
        timer = threading.Timer(seconds, finish)
        timer.daemon = True
        timer.start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        srv.server_close()
    if failed:
        raise failed[0]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fuji-xa", description=__doc__)
    ap.add_argument("--ip", default="192.168.0.1", help="camera address")
    ap.add_argument("--name", default="xa5-probe",
                    help="client name. The camera seems to accept only the name it registered last, "
                         "until you press 'change' on it")
    ap.add_argument("-v", "--verbose", action="store_true", help="log every camera operation")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preview", help="save one live-view frame (640x480 JPEG)")
    p.add_argument("-o", "--out", default="preview.jpg", help="file to write")
    p.add_argument("--seconds", type=float, default=1.0, help="read frames this long, keep the largest")
    p = sub.add_parser("serve", help="live view as an MJPEG stream on a local port, open the address in a browser")
    p.add_argument("--host", default="127.0.0.1", help="address to listen on (no login, keep it local)")
    p.add_argument("--port", type=int, default=8080, help="port to listen on")
    p.add_argument("--seconds", type=float, help="stop after this long (default: until Ctrl-C)")
    sub.add_parser("props", help="print the properties the camera reports, with current values (read-only, no photo)")
    p = sub.add_parser("set", help="write one camera setting and read it back (CHANGES CAMERA STATE). The X-A5 refused the F-number and shutter speed, and accepted the focus point (0xD17C) without using it")
    p.add_argument("prop", type=lambda x: int(x, 0), help="property code from `props`, for example 0x5007")
    p.add_argument("value", type=lambda x: int(x, 0), help="new value, for example 0x118 for f/2.8")
    p.add_argument("--size", type=int, default=2, choices=(2, 4), help="bytes of the value")
    p = sub.add_parser("shoot", help="take photos (WRITES TO THE SD CARD), then download them")
    p.add_argument("-n", "--count", type=int, default=1, help="how many shots; all are taken before any download")
    p.add_argument("-d", "--dir", default=".", help="folder for the pictures")
    p.add_argument("--no-download", action="store_true", help="only release the shutter")
    p = sub.add_parser("download", help="download a picture from the card")
    p.add_argument("-d", "--dir", default=".", help="folder for the pictures")
    p.add_argument("--handle", type=int, default=1, help="1 is the newest picture, 2 the next older")
    p.add_argument("-n", "--count", type=int, default=1, help="download this many, starting at --handle")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.WARNING, format="%(message)s")

    try:
        with Camera(a.ip, a.name) as cam:
            if a.cmd == "preview":
                cam.start_live()
                best, end = b"", time.time() + a.seconds
                while time.time() < end or not best:
                    best = max(best, cam.frame(), key=len)   # the first frame can be small while exposure settles
                with open(a.out, "wb") as fh:
                    fh.write(best)
                print(a.out)
                return 0
            if a.cmd == "serve":
                cam.start_live()
                serve(cam, a.host, a.port, a.seconds)
                return 0
            if a.cmd == "props":
                cam.start_live()   # the settings appear in the change list only after remote mode starts
                cam.events()
                for prop in sorted(cam.props):   # GetDevicePropDesc is not served over Wi-Fi (2026-10-05), so values only
                    print(f"{prop:#06x} {cam.props[prop]:#x}")
                if 0xD17C in cam.props:   # focus point, decoded from four points on the camera (finding, runs 31 to 34)
                    print(f"focus point: column {cam.props[0xD17C] >> 8 & 0xFF} of 13, row {cam.props[0xD17C] & 0xFF} of 7")
                return 0
            if a.cmd == "set":
                cam.start_live()
                cam.events()
                if a.prop not in cam.props or a.prop >> 8 == 0xDF:   # 0xDFxx is protocol state, not a setting
                    raise FujiError(f"{a.prop:#06x} is not a setting the camera reported")
                read = lambda: cam.op(0x1015, (a.prop,), ok=None)   # noqa: E731  GetDevicePropValue, may not be served
                listed, direct = cam.props[a.prop], read()
                rcode = cam.set_prop(a.prop, a.value, a.size, ok=None)
                time.sleep(0.5)
                cam.events()
                print(f"{a.prop:#06x} before: list {listed:#x}, read {direct[0]:#06x} {direct[1].hex()}")
                print(f"wrote {a.value:#x}, camera answered {rcode:#06x}")
                print(f"after: list {cam.props[a.prop]:#x}, read {(r := read())[0]:#06x} {r[1].hex()}")
                return 0 if rcode == 0x2001 else 1
            if a.cmd == "shoot":
                for _ in range(a.count):
                    cam.shoot()
                if a.no_download:
                    print(f"shutter released {a.count} time(s)")
                    return 0
                handles = range(1, a.count + 1)   # handle 1 is the newest picture
            else:
                handles = range(a.handle, a.handle + a.count)
            os.makedirs(a.dir, exist_ok=True)
            for handle in handles:
                name, data = cam.download(handle)
                path = os.path.join(a.dir, name)
                with open(path, "wb") as fh:
                    fh.write(data)
                print(path)
            return 0
    except (FujiError, OSError) as exc:
        print(f"fuji-xa: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
