# artifacts/

Local-only working material that is not ours to redistribute and is too big or too sensitive to commit.
Everything here except this file is git-ignored.

Expected contents, created by the plans:

```
artifacts/
  camera-remote-apk/     the official Camera Remote APK, copied from the owner's own phone (plan 05)
  camera-remote-jadx/    jadx decompiler output for that APK                              (plan 05)
  ghidra/                Ghidra projects, only if plan 06 is approved                      (plan 06)
  firmware/              X-A5 firmware download, only if plan 06 needs it                  (plan 06)
```

Rules:
- Do not copy anything from here into `docs/` or `src/` verbatim. Write findings in your own words.
- Disk is tight on `/` (94 % used). If a directory here grows past about 300 MB, move it to `/media/d`
  and leave a symlink. `/tmp` is a RAM-backed tmpfs and is lost on reboot.
