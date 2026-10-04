# Plan 02: USB unknown vendor operations (`0x900c`, `0x900d`, `0x901d`)

Status: **closed, do not run (2026-10-04).** The operations are now identified from public sources: libfuji's
protocol notes say `0x900c`, `0x900d` and `0x901d` are Fuji file-write operations (create a file, write to a
file) that Fuji's firmware update utility uses to put `AUTO_ACT.SCR` and `FPUPDATE.DAT` on the SD card. They do
nothing for remote shooting, and sending them wrongly could modify the card or the camera. See
[the prior art survey](../findings/2026-10-04-prior-art-survey.md), item 6. The rest of this file is kept as the
record of the original plan.

Original status: blocked, waiting for the owner's approval. Risk: **medium**. This plan sends vendor commands
the project cannot yet describe. Needs installs: none.

## Question

What do the three vendor operations that the X-A5 advertises over USB do, and is any of them useful for
capture, live view or settings?

## Why

The camera lists `0x900c`, `0x900d` and `0x901d`. libgphoto2 does not define them for Fuji, so nothing
public in the code already read explains them. The X-A5 manual describes USB only as a way to download
pictures (MyFinePix Studio on Windows, Image Capture on macOS), so the operations may belong to that
software. PC AutoSave is a wireless-LAN feature in the manual, not a USB one. Do not assume they match
other vendors: the same numbers mean different things in
Canon and Leica code (`0x900c`, `0x900d`, `0x901d` are Canon and Leica operations in libgphoto2's `ptp.h`).

## GATE: approval

Do not run any step marked **SEND** until the owner approves. Reasons:

- An unknown operation could change camera state, write to the card, or change settings.
- A data-phase operation sent with the wrong payload could leave the session hung until a power cycle.

Approval should cover: which operation numbers, a spare or backed-up SD card, and a fully charged
battery.

## Phase 1: passive, no camera traffic

1. Search public material for these opcodes in the Fuji context: libgphoto2 issues and commits, the
   Fujihack project, community PTP notes. Record each hit and its source in the findings file.
2. Run plan 01 first. If a mode changes which operations are advertised, note when `0x900c`,
   `0x900d`, `0x901d` appear or disappear. That ties them to a mode.
3. If MyFinePix Studio (the manual's USB download software for Windows) can run on a Windows machine the
   owner controls, a USB capture of it talking to the camera is a better source than guessing. That needs
   a Windows host or VM and USB capture tooling, so it is optional and requires its own approval.

## Phase 2: active probing (**SEND**, after approval)

Rules:

1. Camera on a spare or backed-up card, full battery, no important photos on the card.
2. Start with zero parameters and no data phase. Read only the response code.
3. One operation at a time. After each, run `gphoto2 --summary` to check the session still works. Power
   cycle if it does not and note that in the log.
4. Never send a data phase (`SendObject`-style) until the matching `…Info` operation has been understood.
5. Stop at the first response that changes camera state or card contents, and write it down.

Tool: libgphoto2 exposes a raw opcode action. `gphoto2 --list-config` shows `/main/actions/opcode` on
this camera. Read its help text with `gphoto2 --get-config /main/actions/opcode` (read-only) to learn the
exact value format before using it. Do not guess the syntax.

Log every attempt to `captures/usb-vendor-ops/<date>-<opcode>.log` with `--debug` enabled, including
the exact command line.

## Exit criteria

- Each of the three operations has a finding: response code, response parameters, data phase direction
  and size if any, whether camera state changed, and what the owner saw on the camera screen.
- `docs/findings/<date>-usb-vendor-ops.md` records results. Anything reusable goes into
  `docs/protocol/usb-vendor-ops.md` in our own words.

## Next step

- An operation helps with capture or live view: write a new USB tether plan.
- None does: record that USB is download-only and stop. Do not continue probing other opcodes without a
  new reason.
