"""Run the library against the fake camera. No hardware needed.

    python3 tests/test_fake_camera.py        (or: pytest tests)

The fake camera is built from public notes and our logs, so passing proves our sequencing and parsing, not
that the real camera agrees. One test, one fake process.
"""
import contextlib
import io
import os
import socket
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, "fake_camera"))
from fake_fuji_camera import FAKE_JPEG  # noqa: E402
from fuji_xa import Camera, FujiError  # noqa: E402
from fuji_xa.__main__ import main  # noqa: E402


def test_live_shoot_download():
    fake = subprocess.Popen([sys.executable, os.path.join(HERE, "fake_camera", "fake_fuji_camera.py")],
                            stdout=subprocess.PIPE, text=True)
    try:
        assert "listening" in fake.stdout.readline()
        with Camera("127.0.0.1") as cam:
            cam.start_live()
            jpeg = cam.frame()
            assert jpeg[:2] == b"\xff\xd8" and jpeg[-2:] == b"\xff\xd9"
            assert cam.shoot() is True
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


def test_serve():
    fake = subprocess.Popen([sys.executable, os.path.join(HERE, "fake_camera", "fake_fuji_camera.py")],
                            stdout=subprocess.PIPE, text=True)
    try:
        assert "listening" in fake.stdout.readline()
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
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


if __name__ == "__main__":
    test_live_shoot_download()
    test_serve()
    print("ok")
