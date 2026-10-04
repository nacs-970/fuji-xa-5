# docs/protocol/

Clean-room protocol notes, written in our own words from observation on the X-A5. No decompiled code and no
identifiers (serial, MAC, full SSID, host name). See [../legal-and-clean-room.md](../legal-and-clean-room.md).

| File | Content |
|------|---------|
| [wifi.md](wifi.md) | Fuji Wi-Fi remote protocol on the X-A5: network, handshake and GUID rule, state properties, remote mode and live view, shutter, ending a session, reading pictures, open questions |

Planned: `usb-vendor-ops.md` is closed, not planned. The operations `0x900C`, `0x900D` and `0x901D` write
firmware files and must not be probed (see [plan 02](../plans/02-usb-unknown-vendor-ops.md)).

Format rules:

- Tables for messages: field, offset, size, meaning.
- Every statement carries a status: **observed** (seen on the X-A5, with a finding that holds the evidence),
  **inferred** (from public notes about other bodies) or **not known**.
- Update the file when a new run changes a fact, and date the change in the matching finding.
