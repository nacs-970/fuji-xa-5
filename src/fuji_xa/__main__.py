"""fuji-xa: live view, shutter and download for a Fujifilm X-A camera over Wi-Fi.

Open WIRELESS COMMUNICATION on the camera and join its Wi-Fi first. One command is one session.
"""
import argparse
import json
import logging
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import GRID, P_FOCUS_COLOUR, P_FOCUS_POINT, Camera, FujiError

PAGE = b"""<!doctype html><meta charset="utf-8"><title>fuji-xa</title>
<body style="margin:0;background:#000;color:#fff;font:16px sans-serif">
<div id=wrap style="position:relative"><img id=img src="/stream" draggable=false style="width:100%;display:block">
<div id=pt style="position:absolute;border:3px solid #fff;box-shadow:0 0 0 1px #000,inset 0 0 0 1px #000;box-sizing:border-box;pointer-events:none;display:none"></div></div>
<p style="margin:8px">Click the picture to focus there, or hold <b>Space</b> or the button to focus at the square. White: not focused. Green: focused. Red: focus failed. The lens keeps its focus when you let go.
<button id=f style="font-size:20px;padding:8px 24px">Focus</button></p>
<script>
let down = false, query = "", chain = Promise.resolve(), area = null;   // "up" is sent only after "down" was answered
const post = path => { chain = chain.then(() => fetch(path, {method: "POST"})).catch(() => {}); };
const press = (d, q) => { if (d !== down) { down = d; query = q || ""; post(d ? "/focus/down" + query : "/focus/up"); } };
// held: lock again every 2 s (page address ?every=1 for 1 s), so the lens follows a moving subject. The camera stutters while it
// focuses, so a short time is quicker to follow and rougher to watch. This also keeps the server's 10 s watchdog away.
const every = 1000 * (new URLSearchParams(location.search).get("every") || 2);
let busy = false;   // one repeat at a time: the camera answers a lock late while it focuses
setInterval(() => {
  if (!down || busy) return;
  busy = true;
  chain = chain.then(() => down && fetch("/focus/down" + query, {method: "POST"})).catch(() => {}).then(() => { busy = false; });
}, every);
const f = document.getElementById("f"), img = document.getElementById("img"), pt = document.getElementById("pt");
f.onpointerdown = () => press(true);
for (const e of ["pointerup", "pointerleave", "pointercancel"]) f.addEventListener(e, () => press(false));
addEventListener("keydown", e => { if (e.code === "Space") { e.preventDefault(); press(true); } });
addEventListener("keyup", e => { if (e.code === "Space") press(false); });
addEventListener("blur", () => press(false));
// the autofocus grid lies over the picture (aspect aw:ah), which sits in the middle of the 4:3 live-view frame
let last = null, pending = null;   // pending: the cell just clicked, shown at once in white until the camera reports it
function layout(s) {
  const W = img.clientWidth, H = W * 3 / 4, wide = s.aw / s.ah >= 4 / 3;
  const w = wide ? W : H * s.aw / s.ah, h = wide ? W * s.ah / s.aw : H;
  return {x: (W - w) / 2, y: (H - h) / 2, w, h, cols: s.cols, rows: s.rows};
}
function draw(col, row, colour) {
  area = layout(last);
  pt.style.display = "block"; pt.style.borderColor = colour;
  pt.style.left = area.x + (col - 1) * area.w / area.cols + "px"; pt.style.top = area.y + (row - 1) * area.h / area.rows + "px";
  pt.style.width = area.w / area.cols + "px"; pt.style.height = area.h / area.rows + "px";
}
// the camera's 0xD209 is the colour of its focus frame: 0 white, 1 green (focused), 2 red (focus failed)
const COLOURS = ["#fff", "#0f0", "#f00"];
async function refresh() {
  try {
    const s = await (await fetch("/state")).json();
    if (!s.col) return;
    last = s;
    if (pending && ((s.col === pending.col && s.row === pending.row) || Date.now() - pending.t > 2000)) pending = null;
    if (pending) draw(pending.col, pending.row, "#fff");
    else draw(s.col, s.row, COLOURS[s.af] || "#fff");
  } catch (e) {}
}
setInterval(refresh, 100); refresh();
img.onpointerdown = e => {
  if (!area) return;
  const r = img.getBoundingClientRect(), x = e.clientX - r.left - area.x, y = e.clientY - r.top - area.y;
  if (x < 0 || y < 0 || x >= area.w || y >= area.h) return;
  const col = Math.floor(x / area.w * area.cols) + 1, row = Math.floor(y / area.h * area.rows) + 1;
  pending = {col, row, t: Date.now()};
  draw(col, row, "#fff");
  press(true, "?cell=" + col + "," + row);
};
img.onpointerup = img.onpointerleave = img.onpointercancel = () => press(false);
</script>"""


def serve(cam, host, port, seconds=None):
    """Live view as an MJPEG stream: open http://HOST:PORT/ in a browser. Runs until Ctrl-C or `seconds`.

    The page shows the camera's focus point as a square (property 0xD17C, read ten times a second): white until the
    camera has focused, green when it has, red when focusing failed (property 0xD209, the app's "S1 lock colour"). Click the picture
    to focus there (Camera.focus with a cell, worked on the X-A5, run 46), or hold the Focus button or Space to focus at the
    square again (a lock without a cell would move the point to the centre).

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

    def poll():   # keep the focus point fresh for the page
        while not stop.wait(0.1):
            try:
                cam.events()
            except (FujiError, OSError):
                return

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/state":
                point = cam.props.get(P_FOCUS_POINT)
                state = {} if point is None else {"aw": point >> 24, "ah": point >> 16 & 255, "col": point >> 8 & 255,
                                                   "row": point & 255, "cols": GRID[0], "rows": GRID[1], "af": cam.props.get(P_FOCUS_COLOUR, 0)}
                body = json.dumps(state).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
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
                url = urlparse(self.path)
                if url.path == "/focus/down":
                    cell = parse_qs(url.query).get("cell")
                    point = cam.props.get(P_FOCUS_POINT)
                    if cell:
                        cell = tuple(int(n) for n in cell[0].split(","))
                    elif point:   # no click: focus at the square, not at the centre
                        cell = (point >> 8 & 255, point & 255)
                    cam.focus(cell or None)
                    for old in hold:   # the page repeats "down" every second while held: 10 s after the last one, let go
                        old.cancel()
                    hold.clear()
                    timer = threading.Timer(10, let_go)   # the browser never said "up" (tab closed)
                    timer.daemon = True
                    timer.start()
                    hold.append(timer)
                elif url.path == "/focus/up":
                    let_go()
                else:
                    return self.send_error(404)
            except (FujiError, OSError, ValueError) as exc:
                return self.send_error(500, str(exc).splitlines()[0])
            self.send_response(204)
            self.end_headers()

        def log_message(self, *args):
            pass

    srv = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=poll, daemon=True).start()
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
