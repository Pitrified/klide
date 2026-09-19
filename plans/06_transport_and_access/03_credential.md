---
status: draft
---

# Phase 3 - A credential on the wire

## Overview

Give the host a way to refuse a connection it does not recognise, using the key written onto the
device at provisioning time. Blocked on phase 1, per TD6: the shape has to be one the Lua client can
implement, and that is a fact about the device rather than a preference.

If phase 1 answers T1 with a yes, this phase may be unnecessary, because the tailnet already
answers who is connecting. Whether it is worth having anyway, as defence that does not depend on one
vendor, is a decision for when that answer exists.

Context: [`00_start.md`](00_start.md), TD4 and TD5.

## Goals

1. An unrecognised connection gets nothing, and says so in the log.
2. The key is written at provisioning time over USB and revoked by changing one value on the host.
3. Both implementations of the protocol agree, klide's and the viewer's.

## Plan

- Settle T3: the message shape, fixed length, readable with `string.byte` arithmetic, compared in
  constant time. Decide between a new message type and a version bump, and write the answer into
  [`../../docs/protocol.md`](../../docs/protocol.md), which is the file a second implementation reads.
- Settle T5: where the host keeps the key, and what a connection presenting an old one sees.
- Settle T6: whether the viewer presents a credential or is exempted as local.
- Implement it on the host, in the viewer and on the device, in that order, with a test that a
  connection presenting nothing is refused.
- Make the refusal visible in the log. The diary review named diagnosis without instrumentation as a
  recurring cost, and a silently dropped connection is exactly that shape.

## Out of scope

- Encryption. A credential authenticates and does not encrypt, per TD5. Anything that needs
  confidentiality is phase 4.
- Any pairing flow. Provisioning is physical, per TD4.

## Done when

- A client without the key is refused by the host and by the viewer's decoder alike.
- Rotating the key is plugging in the cable, demonstrated once end to end.
- [`../../docs/protocol.md`](../../docs/protocol.md) describes the handshake well enough to implement
  from without reading klide's code.

## What the implementation found
