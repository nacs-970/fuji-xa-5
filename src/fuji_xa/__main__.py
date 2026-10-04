"""fuji-xa: live view, shutter and download for a Fujifilm X-A camera over Wi-Fi.

Open WIRELESS COMMUNICATION on the camera and join its Wi-Fi first. One command is one session.
"""
import argparse
import logging
import os
import sys
import time

from . import Camera, FujiError


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
    sub.add_parser("props", help="print the properties the camera reports, with current values (read-only, no photo)")
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
            if a.cmd == "props":
                cam.start_live()   # the settings appear in the change list only after remote mode starts
                cam.events()
                for prop in sorted(cam.props):   # GetDevicePropDesc is not served over Wi-Fi (2026-10-05), so values only
                    print(f"{prop:#06x} {cam.props[prop]:#x}")
                return 0
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
