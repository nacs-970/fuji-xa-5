# Plan overview

How the seven plans fit together, in what order to run them, and what each result changes.

## Goal

An open-source tool that triggers the shutter, changes basic settings and shows live view on the
Fujifilm X-A5 from a PC, without the official smartphone app. Reusable for other older X-A bodies if
their protocol matches.

## Two candidate routes

| Route | Evidence so far | Decided by |
|-------|-----------------|------------|
| USB PTP | camera advertises no capture operation in the one mode probed | plans 01, 02 |
| Wi-Fi (Fuji fork of PTP/IP, ports 55740 to 55742) | official app does it, libgphoto2 has an experimental driver, X-A5 untested | plans 03 to 06 |

## Order and gates

```
Phase A  no installs, low risk
  01 USB mode survey ............ read-only
  03 Wi-Fi test with libgphoto2 .. takes one photo

Phase B  only if 03 fails or works partially
  04 Wi-Fi traffic capture ....... GATE: install tcpdump + wireshark-cli
  05 APK static analysis ......... GATE: install jadx, obtain APK from owner's own phone

Phase C  only if A and B leave a question open
  02 USB unknown vendor ops ...... GATE: owner approves sending vendor commands
  06 Ghidra / REA native ......... GATE: owner approves ~1.25 GiB install and a JDK 21

Phase D
  07 Implementation .............. starts as soon as one route is understood
```

Numbering is by topic, not by run order. Run Phase A first.

## Decision tree

```
03 Wi-Fi test with libgphoto2
 |-- connects, summary works, preview and capture work
 |     -> 07 branch "works already": document, add X-A5 notes, upstream, small helper tools
 |-- connects, but properties, preview or capture fail
 |     -> 04 capture the official app, compare with libgphoto2 behavior -> 07 branch "patch"
 |-- does not connect (TCP refused, handshake rejected)
 |     -> 04 + 05 to learn the real handshake -> 07 branch "patch" or "standalone"
 |-- cannot be run (no Wi-Fi mode, no way to join the camera network)
       -> fix the setup first; this is a blocker, not a result

01 USB mode survey
 |-- some mode advertises 0x100e, 0x101c or 0x902x
 |     -> new plan "USB tether for X-A5"; much cheaper than Wi-Fi if real
 |-- no mode does
       -> USB stays download-only; keep 02 only if the vendor ops look useful

04 + 05 leave an answer in native code
 -> 06
```

## Disk budget

Checked on 2026-10-04: `/` 2.9 GB free (94 % used), `/media/d` 25 GB free (NTFS), `/tmp` tmpfs 3.6 GB
(RAM, cleared on reboot).

| Plan | Added disk | Basis |
|------|------------|-------|
| 01, 02, 03 | under 5 MB of logs | estimate |
| 04 | about 101 MiB for packages, plus pcap files (keep captures to tens of seconds) | pacman database, estimate |
| 05 | about 75 MiB for `jadx`, plus APK (estimate 30 to 60 MB) and decompiler output (estimate up to a few hundred MB) | pacman database, estimates |
| 06 | about 1.25 GiB installed, peak about 2 GiB during download | pacman database |

Plans 01 to 05 together stay in the low hundreds of MB. Move `artifacts/` to `/media/d` if it passes about
300 MB.

## Definition of done for the research phase

1. We know which route (Wi-Fi, USB or both) the X-A5 supports, with logs to prove it.
2. The protocol parts needed for shutter, settings and live view are written down in `docs/protocol/` in
   our own words.
3. A short list of what is still unknown.

Then plan 07 decides what to build.

## Updating these docs

When a plan runs, write the outcome as a dated file in `docs/findings/`, update the status column in
the root `README.md`, and update the decision tree above if the result changes the order.
