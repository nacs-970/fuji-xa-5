# Plan 06: Ghidra / REA native analysis

Status: blocked, waiting for the owner's approval. Risk: none for the camera. Cost: about 1.25 GiB of
disk. Needs installs: yes (Ghidra and a JDK 21).

## Question

What does native code in the official app (or, if USB stays open, in the camera firmware) do that the
Java layer, traffic captures and libgphoto2 source cannot explain?

## When to run this

Only when one of these is true after the earlier plans:

1. Plan 05 shows the Fuji protocol, a handshake secret or a custom framing lives in a native `.so` of the
   APK.
2. Plan 01 and 02 leave USB tether open and the firmware is the only way to learn which operations the
   camera implements.

Do not run it just to say the REA analysis was done. `ptp2.so` (libgphoto2) is not a useful target
because its source is open and was read directly.

## Why it is blocked today

Observed on 2026-10-04, from REA's own diagnostics:

- Ghidra provider: `GHIDRA_INSTALL_DIR` is not set, no Ghidra is installed, and the default Java 27 is
  rejected (`unsupported_version`). REA asks for Ghidra **12.1.4**.
- Hopper provider: `/opt/hopper/bin/Hopper` is missing.

## GATE: approvals

- Install Ghidra and JDK 21. Cost, from the pacman database: `ghidra` 742 MiB installed (355 MiB
  download), `jdk21-openjdk` 504 MiB installed (335 MiB download). That is about 1.25 GiB installed and a
  peak near 2 GiB during download, on a `/` that has 2.9 GB free.
- Choice of install location (see options).
- Whether to change the system default Java. Prefer **not** to. Point REA at JDK 21 with `JAVA_HOME` in the
  MCP server's environment instead.

## Install options

| Option | Disk on `/` | Notes |
|--------|-------------|-------|
| A. pacman packages | about 1.25 GiB installed, peak about 2 GiB | Simplest. Leaves about 0.9 GB free on `/` if the downloaded packages stay in the pacman cache, about 1.6 GB if the cache is cleaned afterwards (arithmetic from the sizes above, not measured). |
| B. Ghidra release archive and a JDK 21 archive unpacked under `/media/d` | near zero | `/media/d` is NTFS (`fuseblk`). Executable bits and speed need a test run before relying on it. |

Before either: run `pacman -Si ghidra` and compare its version with the 12.1.4 that REA asks for. If they
differ, either install the matching release (option B) or check what REA accepts.

## Steps

1. Install per the chosen option. Record versions.
2. Set `GHIDRA_INSTALL_DIR` and `JAVA_HOME` in the REA MCP server environment. Run `rea doctor` (named
   in REA's own error message) and confirm the Ghidra provider reports ready. Restart the MCP server if it
   requires it.
3. Extract the target.
   - Native library from the APK: `unzip` the `.so` for the right ABI from the APK into
     `artifacts/ghidra/input/`.
   - Firmware: download from Fuji's official site into `artifacts/firmware/`. Identify the container
     format first (file magic, entropy). If it is encrypted or compressed with an unknown scheme, stop and
     record that. Do not spend days on it without a decision.
4. Analyze with the REA tools: `open_binary`, `binary_overview`, `search_strings`
   (ports `55740`, `55741`, `55742`, model names, `X-A5`), `find_code_for_string`, `procedure_callers`,
   `procedure_pseudo_code`, `analyze_function`. Name and comment functions as you go
   (`set_address_name`, `set_comment`) so the work survives a restart.
5. Tie each finding to evidence from plans 03 to 05 (the same opcode or field seen in a pcap or in the
   Java code). A native finding with no cross-check stays marked **guessed**.
6. Write results into `docs/protocol/` in our own words.

## Clean-room reminder

Decompiled output and Ghidra projects stay in `artifacts/ghidra/`. Never paste pseudocode into the repo.
Notes describe behavior: message layout, state machine, field meaning.

## Exit criteria

- `docs/findings/<date>-native-analysis.md`: what was analyzed (file, version, SHA-256), what was learned,
  what remains unknown, and how long it took.
- Updated `docs/protocol/`.

## Next step

Plan 07.
