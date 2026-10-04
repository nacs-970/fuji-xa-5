# Plan 07: Implementation

Status: Branch 3 started on 2026-10-04 with the Python library in `src/fuji_xa/` (`Camera` class and the
`fuji-xa` command: preview, shoot, download). It follows the probe sequence that ran on the real X-A5 and is
tested against the fake camera. `preview` ran on the real camera on 2026-10-05 ([finding](../findings/2026-10-05-library-first-real-run.md)); `shoot` and `download` have not. The libgphoto2 patch (Branch 2) is
the second step and is not started.

## Question

Given what plans 01 to 06 found, what is the smallest open-source deliverable that gives the X-A5 remote
shooting, and where should it live?

## Prior art changes the starting point (2026-10-04)

[libfuji](https://github.com/petabyt/libfuji) (MIT, C, active) already implements Fuji's Wi-Fi protocol with
a remote mode and was tested on the X-A2. See [the survey](../findings/2026-10-04-prior-art-survey.md). So
this plan should not start by writing a new protocol stack. Order of work:

1. Test the X-A5 with libfuji and with a patched libgphoto2.
2. Contribute the fixes upstream: libgphoto2 (reconnect and retry on Init Fail, and whatever else the X-A5
   needs) and, if useful, libfuji (an X-A5 report and quirks).
3. Write down X-A5 specifics in `docs/protocol/`.
4. Start a standalone code base (Branch 3) only if upstream cannot take the change or the goal needs
   something they will not host.

libfuji is MIT, so its code can be reused with attribution, including inside LGPL libgphoto2. Fudge declares
no license in the GitHub API, so do not copy from it until that is clarified.

## Branches

Pick the branch from the decision tree in [00-overview.md](00-overview.md).

### Branch 1: works already (plan 03 passes)

libgphoto2's `Fuji X (WLAN)` driver already controls the X-A5.

Deliverables:
- `docs/` guide: how to put the camera in Wi-Fi remote mode, join its network, and run `gphoto2` for
  summary, preview and capture. Tested firmware version, libgphoto2 version, host OS.
- Report the result upstream to libgphoto2 (an issue that says the X-A5 works over Wi-Fi, with the log),
  so the camera list can say so.
- Optional small helper: a script that shows live preview or feeds it to a virtual webcam
  (`v4l2loopback`), only if there is demand. Do not build it speculatively.

### Branch 2: patch (plan 03 partly works, or the handshake differs slightly)

Change libgphoto2's Fuji Wi-Fi code so the X-A5 works.

Deliverables:
- A patch against libgphoto2 `master` for the files that matter (`fujiptpip.c`, `library.c`), with the
  logic for the difference found in plans 04 to 06.
- A regression test based on a sanitized pcap replay (see Testing).
- A pull request upstream. Upstream-first is the recommendation, because it gives the `gphoto2` CLI and
  every libgphoto2 front end (for example darktable and entangle) support for free, and it keeps one
  protocol implementation instead of two.

### Branch 3: standalone (the protocol differs too much, or upstream does not accept the patch)

A small library plus a CLI, written from our own protocol notes.

Deliverables:
- Library: connect, keep-alive, get and set a few properties (ISO, aperture or shutter, white balance),
  shutter, live view frames, file transfer.
- CLI over the library.
- `docs/protocol/` as the specification the code follows.

Proposed layout, created only when this branch starts:

```
src/
  <lib>/            protocol implementation (language to be decided)
  cli/              command-line tool
tests/
  fake_camera/      replay server that plays recorded exchanges
  fixtures/         sanitized message sequences derived from captures
docs/protocol/      wifi.md and any usb notes, the source of truth for the code
```

## Decisions for the owner (open)

| Decision | Options | Recommendation |
|----------|---------|----------------|
| License | LGPL-2.1-or-later (upstreamable into libgphoto2) vs MIT or Apache-2.0 (standalone) | LGPL-2.1-or-later if Branch 1 or 2. A permissive license only if Branch 3 and the owner wants it. |
| Language for Branch 3 | C (matches libgphoto2), Python (fast to prototype), Rust (safe, single binary) | decide when Branch 3 starts |
| Scope | X-A5 only vs a family of older X-A bodies | X-A5 first. Add other bodies only with a captured session from each. |

Do not add a `LICENSE` file until this is decided.

## Testing

- **Fake camera:** a small server that replays recorded request and response sequences on the same
  ports (55740 command, 55741 event, 55742 JPEG). It lets tests run in CI with no camera.
- **Sanitizing fixtures:** before any capture-derived data is committed, replace the serial number, MAC
  address, SSID, host name and any image content. Keep protocol bytes. Keep a note of what was changed.
- **Real-camera test:** a manual checklist (connect, read settings, preview, capture, disconnect) run
  before each release, with firmware version and result recorded in `docs/findings/`.

## Clean-room rules

- Code is written from `docs/protocol/`, not from decompiled output. If one person reads decompiled code
  and another writes the implementation, record that in the findings.
- No Fuji binaries, firmware, APKs, assets or text in the repo.
- If code is taken from libgphoto2 (LGPL) or `fuji-cam-wifi-tool` (Unlicense), keep each file's license
  header and note the origin in `docs/references.md`.

See [docs/legal-and-clean-room.md](../legal-and-clean-room.md).

## Exit criteria

- The chosen branch's deliverables exist and the real-camera checklist passes on the X-A5.
- The README states what works, what does not, and the tested firmware version.
