# Plan 05: APK static analysis with jadx

Status: not started. Risk: none for the camera. Needs installs: yes, see GATE.

## Question

What does the official Camera Remote app do for the X-A5 specifically, and does it implement the protocol
in Java/Kotlin or in native code?

## Why

Traffic captures (plan 04) show the bytes. The app code explains the intent: names for opcodes, the
property list the app uses, which camera models take which code path, and the connect sequence. It is
also the cheapest way to learn whether a native decompiler (plan 06) is needed at all.

## GATE: approvals

- Install `jadx` (about 75 MiB installed, 68 MiB download). It should run on the existing Java 27. If it
  does not, a JRE 21 is about 147 MiB installed. Verify by running it, do not assume.
- Obtain the APK from the owner's own phone, not from third-party APK mirror sites (supply-chain risk).

## Prerequisites

- The app package name from the store listing is `com.fujifilm_dsc.app.remoteshooter`. Confirm on the
  phone before relying on it.
- USB debugging enabled on the phone. `adb` is already installed on this machine
  (`/usr/bin/adb`), so no extra package is needed. Alternatively the owner supplies the file another
  way.
- `artifacts/camera-remote-apk/` and `artifacts/camera-remote-jadx/` (git-ignored).

## Steps

1. Get the APK from the phone:
   ```
   adb shell pm path com.fujifilm_dsc.app.remoteshooter
   adb pull <path from previous command> artifacts/camera-remote-apk/base.apk
   ```
   If the app is a split APK, pull every split listed. Record the app version and the SHA-256 of the
   files in the findings file.
2. Inspect the package without decompiling: `unzip -l base.apk`. Note `lib/*/*.so` native libraries and
   their sizes. If the Fuji protocol code is in a native library, plan 06 becomes relevant.
3. Decompile:
   ```
   jadx -d artifacts/camera-remote-jadx artifacts/camera-remote-apk/base.apk
   ```
   Check the output size. Move `artifacts/` to `/media/d` if it passes about 300 MB.
4. Search the output (use `rtk grep` or `grep -rn`) for:

   | Target | Why |
   |--------|-----|
   | `55740`, `55741`, `55742` | ports and where connections are opened |
   | `X-A5`, `XA5`, `X_A5` and model name lists | per-model behavior |
   | opcode constants, both hex and decimal (for example `0x101c` = 4124, `0x9022` = 36898) | opcode names and use |
   | property codes in the `0xd001` to `0xd4xx` range (libgphoto2 names `0xd001` FilmSimulation, `0xd017` ColorTemperature, `0xd018` Quality for newer bodies) | settings the app changes. The X-A5 may use different numbers, so compare, do not assume. |
   | `PTPIP`, `InitCommand`, init request builders, host name fields | handshake |
   | `LiveView`, `Preview`, JPEG framing | live view |
   | `Bluetooth`, `Remote Release` | separate from the Wi-Fi path |

5. For the X-A5 specifically, trace from the model check to the code it selects. List any property or
   opcode that applies only to older X-A bodies.
6. Write what you learn in `docs/protocol/wifi.md` in our own words (see plan 04 for the format). Cite
   the class and method name as evidence in the notes, but do not paste decompiled code.

## Clean-room reminder

The decompiled output stays in `artifacts/`. It is for understanding, not for copying. Notes in
`docs/protocol/` state behavior (message layout, opcode meaning, sequence), not source text.

## Exit criteria

- `docs/findings/<date>-apk-analysis.md`: app version, file hashes, whether native libraries carry
  protocol code, the model-specific paths for the X-A5, and open questions.
- Updated `docs/protocol/wifi.md`.

## Next step

- Protocol is in Java/Kotlin: plan 07, no native analysis needed.
- Protocol or crypto is in a native library: plan 06, aimed at that library only.
