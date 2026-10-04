"""Run the library against the fake camera. No hardware needed.

    python3 tests/test_fake_camera.py        (or: pytest tests)

The fake camera is built from public notes and our logs, so passing proves our sequencing and parsing, not
that the real camera agrees. One test, one fake process.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, "fake_camera"))
from fake_fuji_camera import FAKE_JPEG  # noqa: E402
from fuji_xa import Camera, FujiError  # noqa: E402


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
    finally:
        fake.kill()
        fake.wait()


if __name__ == "__main__":
    test_live_shoot_download()
    print("ok")
