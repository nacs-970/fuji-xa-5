# Legal notes and clean-room rules

This is a working policy for the project, not legal advice. Laws about reverse engineering for
interoperability differ by country. The owner is responsible for checking the rules that apply to them
and to anyone who uses or contributes to the project.

## What this project does

It studies how the owner's own camera and the official app communicate, so that an independent program
can talk to the same camera. It does not break access controls, remove licensing, or copy the official
app.

## What may be committed

| Allowed | Not allowed |
|---------|-------------|
| Our own notes on message layouts, opcodes, property meanings and sequences | Fuji APKs, firmware images, native libraries, app assets |
| Short protocol hex examples with identifiers removed | Decompiled or disassembled code, even in part |
| Our own scripts and code | Raw captures with serial numbers, MAC addresses, SSIDs or host names |
| Links and citations to public sources | Text copied from the official app or manuals beyond a short quote |
| Sanitized test fixtures | Photos or image data from other people |

`.gitignore` already keeps `captures/` and `artifacts/` out of git. Do not work around it.

The X-A5 owner's manual is not kept in the repo, neither the PDF nor a text conversion (owner decision,
2026-10-08). Fuji owns that text, and a full extraction is not a short quote. Keep your own copy in the
git-ignored `artifacts/x-a5-manual/` and cite the official PDF in `docs/references.md`.

## Clean-room practice

1. Observation (traffic, device probing, decompiler output) lives in `captures/` and `artifacts/`.
2. Findings are written in `docs/findings/` and `docs/protocol/` as descriptions of behavior.
3. Code is written from those descriptions. Preferably the person who writes the code does not copy
   from decompiler output. If one person does both, say so in the findings.
4. When code or ideas come from other open-source projects, keep their license headers and credit them in
   `docs/references.md`.

## Third-party licenses to keep in mind

- libgphoto2 is LGPL-2.1-or-later. Code derived from it must stay compatible.
- `hkr/fuji-cam-wifi-tool` is under the Unlicense, per its repository.
- Check the license of any other project before reusing its code. The Fujihack project in particular has
  its own rules; read them before using anything from it.

## Device safety

Never flash firmware or send write-type vendor commands to the camera without the owner's approval. See
the **GATE** markers in the plans.
