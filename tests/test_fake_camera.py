"""Run the library against the fake camera. No hardware needed.

    python3 tests/test_fake_camera.py        (or: pytest tests)

The fake camera is built from public notes and our logs, so passing proves our sequencing and parsing, not
that the real camera agrees. One test, one fake process.
"""
import contextlib
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, "fake_camera"))
from fake_fuji_camera import FAKE_JPEG  # noqa: E402
from fuji_xa import Camera, FujiError  # noqa: E402
from fuji_xa.__main__ import PAGE, main, serve  # noqa: E402


def test_live_shoot_download():
    fake = subprocess.Popen([sys.executable, os.path.join(HERE, "fake_camera", "fake_fuji_camera.py")],
                            stdout=subprocess.PIPE, text=True)
    try:
        assert "listening" in fake.stdout.readline()
        with Camera("127.0.0.1") as cam:
            cam.start_live()
            jpeg = cam.frame()
            assert jpeg[:2] == b"\xff\xd8" and jpeg[-2:] == b"\xff\xd9"
            assert cam.postview() == b""         # no shot yet: the camera answers with no data (run 50)
            assert cam.shoot() is True
            assert cam.postview()[:2] == b"\xff\xd8" and cam.postview() == b""   # the shot as a small JPEG, once
            assert cam.shoot() is True           # right after the first: the fake answers Device Busy once
            name, data = cam.download()          # ends live view first
            assert name == "DSCF0001.JPG" and data == FAKE_JPEG
            assert cam.download(2)[1] == FAKE_JPEG   # a second download in the same session
            try:
                cam.start_live()                 # the real camera drops the session if we try this
                raise AssertionError("live view after a download must be refused")
            except FujiError:
                pass
        with Camera("127.0.0.1") as cam:         # a second session that only downloads
            assert cam.download(2)[1] == FAKE_JPEG
        assert main(["--ip", "127.0.0.1", "set", "0x5007", "0x118"]) == 0   # the `set` command, F-number to 2.8
        assert main(["--ip", "127.0.0.1", "set", "0xdf01", "5"]) == 1      # protocol state is refused
        with Camera("127.0.0.1") as cam:
            cam.start_live()
            cam.events()
            assert cam.props[0x5007] == 0x118
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            assert main(["--ip", "127.0.0.1", "props"]) == 0
        assert "focus point: column 7 of 13, row 4 of 7" in out.getvalue()   # 0xD17C = 0x03020704
        with tempfile.TemporaryDirectory() as tmp:   # one shot with its postview, then the download
            assert main(["--ip", "127.0.0.1", "shoot", "--postview", "-d", tmp]) == 0
            assert open(os.path.join(tmp, "postview_1.jpg"), "rb").read()[:2] == b"\xff\xd8"
            assert open(os.path.join(tmp, "DSCF0001.JPG"), "rb").read() == FAKE_JPEG
    finally:
        fake.kill()
        fake.wait()


def fetch(port, path, frames=0):
    """GET a path from the local server (retrying while it starts). With frames, stop after that many stream parts."""
    for _ in range(100):
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=5)
            break
        except OSError:
            time.sleep(0.1)
    s.sendall(f"GET {path} HTTP/1.0\r\n\r\n".encode())
    data = b""
    while not frames or data.count(b"--frame") < frames:
        chunk = s.recv(65536)
        if not chunk:
            break
        data += chunk
    s.close()
    return data


def test_page_script():
    """The focus square on the preview page: jumps at once on a click, white until focused, green, red (needs node)."""
    node = shutil.which("node")
    if not node:
        print("node not installed, page script test skipped")
        return
    page = re.search(rb"<script>(.*)</script>", PAGE, re.S).group(1)
    with tempfile.NamedTemporaryFile(suffix=".js") as script:
        script.write(page)
        script.flush()
        run = subprocess.run([node, os.path.join(HERE, "page_test.js"), script.name], capture_output=True, text=True)
    assert run.returncode == 0 and "FAIL" not in run.stdout, run.stdout + run.stderr


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def post(port, path, headers="", body=False):
    """POST with no body. Returns the status line (and the reply body with body=True)."""
    with socket.create_connection(("127.0.0.1", port), timeout=15) as s:
        s.sendall(f"POST {path} HTTP/1.0\r\nContent-Length: 0\r\n{headers}\r\n".encode())
        data = b""
        while chunk := s.recv(65536):
            data += chunk
        return data.split(b"\r\n\r\n", 1) if body else data.split(b"\r\n")[0]


def test_serve():
    fake = subprocess.Popen([sys.executable, os.path.join(HERE, "fake_camera", "fake_fuji_camera.py")],
                            stdout=subprocess.PIPE, text=True)
    try:
        assert "listening" in fake.stdout.readline()
        port = free_port()
        server = threading.Thread(target=main, args=(["--ip", "127.0.0.1", "serve", "--port", str(port), "--seconds", "4"],))
        server.start()
        stream = fetch(port, "/stream", frames=3)
        assert b"multipart/x-mixed-replace" in stream and stream.count(b"image/jpeg") >= 3 and b"\xff\xd8" in stream
        assert b'src="/stream"' in fetch(port, "/")
        server.join(15)
        assert not server.is_alive()   # --seconds ended the server and the camera session
    finally:
        fake.kill()
        fake.wait()


def test_focus():
    fake = subprocess.Popen([sys.executable, os.path.join(HERE, "fake_camera", "fake_fuji_camera.py")],
                            stdout=subprocess.PIPE, text=True)
    try:
        assert "listening" in fake.stdout.readline()
        with Camera("127.0.0.1") as cam:
            cam.start_live()
            assert cam.events()[0xD209] == 0
            cam.focus()
            assert cam.events()[0xD209] == 1     # the camera shows the lock in its change list (run 38)
            cam.release_focus()
            assert cam.events()[0xD209] == 0
            cam.focus()                          # left held on purpose: close() must let go
        with Camera("127.0.0.1") as cam:
            cam.start_live()
            assert cam.events()[0xD209] == 0
            port = free_port()                   # the preview page's Focus button, as the browser sends it
            server = threading.Thread(target=serve, args=(cam, "127.0.0.1", port, 9))
            server.start()
            fetch(port, "/")
            assert b" 204 " in post(port, "/focus/down")
            assert cam.events()[0xD209] == 1
            assert b" 204 " in post(port, "/focus/up")
            assert cam.events()[0xD209] == 0
            assert b" 404 " in post(port, "/nothing")
            started = threading.Event()          # a release that arrives while the lock is still being sent (run 42)
            real_op = cam.op

            locks = []

            def op(code, *args, **kwargs):
                if code == 0x9026:
                    locks.append(args)
                    started.set()
                return real_op(code, *args, **kwargs)

            cam.op = op
            lock = threading.Thread(target=cam.focus)
            lock.start()
            assert started.wait(5)
            cam.release_focus()                  # must wait for the lock to finish, then release it
            lock.join(5)
            assert cam.events()[0xD209] == 0
            cam.release_focus()
            cam.focus((5, 2))                    # a chosen cell: operation 0x9026 with one number, aspect 3:2, column, row
            assert cam.events()[0xD17C] == 0x03020502
            cam.focus((5, 2))                    # held: the page sends the lock again every second, the camera gets it again
            assert len(locks) == 3, locks        # the race lock, then these two
            cam.release_focus()
            assert b" 204 " in post(port, "/focus/down?cell=3,3")   # a click on the picture
            assert cam.events()[0xD17C] == 0x03020303
            state = json.loads(fetch(port, "/state").split(b"\r\n\r\n", 1)[1])
            assert state == {"aw": 3, "ah": 2, "col": 3, "row": 3, "cols": 13, "rows": 7, "af": 1}, state   # 1 = locked, shown green
            assert b" 204 " in post(port, "/focus/up")
            assert cam.events()[0xD17C] == 0x03020303      # the point stays after the release
            assert b" 204 " in post(port, "/focus/down")   # the Focus button: at the square, not at the centre
            assert cam.events()[0xD17C] == 0x03020303
            assert b" 204 " in post(port, "/focus/up")
            cam.focus()                                    # no cell: the camera goes to the centre
            assert cam.events()[0xD17C] == 0x03020704
            cam.release_focus()
            assert b" 204 " in post(port, "/focus/down?cell=3,3")
            assert cam.events()[0xD17C] == 0x03020303
            assert b" 204 " in post(port, "/focus/up")
            assert b" 500 " in post(port, "/focus/down?cell=14,1")  # outside the 13 x 7 grid: refused, nothing sent
            assert b" 500 " in post(port, "/focus/down?cell=x")
            assert cam.events()[0xD17C] == 0x03020303
            assert b'id=pt' in fetch(port, "/")
            server.join(15)
            assert not server.is_alive()
    finally:
        fake.kill()
        fake.wait()


def test_shoot_button():
    """The Shoot button's server side: focus at the square, shoot, return the postview. Needs --shoot and the X-Fuji header."""
    fake = subprocess.Popen([sys.executable, os.path.join(HERE, "fake_camera", "fake_fuji_camera.py")],
                            stdout=subprocess.PIPE, text=True)
    try:
        assert "listening" in fake.stdout.readline()
        with Camera("127.0.0.1") as cam:
            cam.start_live()
            cam.events()
            port = free_port()
            server = threading.Thread(target=serve, args=(cam, "127.0.0.1", port, 12, True))
            server.start()
            fetch(port, "/")
            assert json.loads(fetch(port, "/state").split(b"\r\n\r\n", 1)[1])["shoot"] is True
            assert b" 403 " in post(port, "/shoot")                       # another web page cannot send the header
            head, view = post(port, "/shoot", "X-Fuji: 1\r\n", body=True)
            assert b" 200 " in head.split(b"\r\n")[0] and view[:2] == b"\xff\xd8", head   # the postview of the shot
            assert cam.events()[0xD209] == 0                              # focus was let go after the shot
            assert b" 200 " in post(port, "/shoot", "X-Fuji: 1\r\n")   # a second shot gives a postview too
            server.join(20)
            assert not server.is_alive()
        with Camera("127.0.0.1") as cam:                                  # without --shoot there is no such page
            cam.start_live()
            port = free_port()
            server = threading.Thread(target=serve, args=(cam, "127.0.0.1", port, 3))
            server.start()
            fetch(port, "/")
            assert b" 404 " in post(port, "/shoot", "X-Fuji: 1\r\n")
            assert "shoot" not in json.loads(fetch(port, "/state").split(b"\r\n\r\n", 1)[1])
            server.join(10)
    finally:
        fake.kill()
        fake.wait()


if __name__ == "__main__":
    test_live_shoot_download()
    test_serve()
    test_focus()
    test_shoot_button()
    test_page_script()
    print("ok")
