# Wire protocol, version 2

What the host sends and the panel receives. Written after the code rather than before it, which is
what app phase 2 asks for: the shape is what the walking skeleton needed, not what a design
document predicted. Phase 3 revised it, again from need rather than foresight.

One protocol serves the simulator and the real device (AD5). The simulator is not a mock of the
device, it is the first client of the same contract, so the device client is later a second
implementation rather than a rewrite (AD4).

## What changed in version 2

Version 1 had one message type in one fixed header, which was enough to prove a frame crosses the
wire. Phase 3 needed a second type going the other way, a refresh mode on each frame, and a page
identity for the device's cache. A single fixed header cannot carry two message shapes, so it split
into a common part and a type-specific body.

The encoding rules did not change. They were already decided by the client that does not exist yet.

## Messages

    common header, 9 bytes
    offset  size  field
    0       4     magic, b"KLD2"
    4       1     message type, 1 = frame, 2 = input
    5       4     body length

    frame body, host to device, 12 bytes then pixels
    0       1     bits per pixel
    1       1     refresh mode
    2       2     page id, 0 for a rectangle belonging to no page
    4       2     x
    6       2     y
    8       2     width
    10      2     height
    12      ...   rows of packed pixels

    input body, device to host, 8 bytes
    0       1     event kind, 1 = tap, 2 = swipe, 3 = button
    1       1     direction
    2       1     button
    3       1     reserved, zero
    4       2     x
    6       2     y

All integers are big-endian and unsigned. A reader takes nine bytes, reads the length, then takes
that many more, and only then looks at the type.

The frame payload is rows of pixels, two per byte at four bits each, the leftmost pixel in the high
nibble. Each row is padded to a whole byte, so a row starts at `y * ceil(width / 2)` and no reader
has to carry a bit offset from one row into the next.

Refresh mode is an index into a fixed list, `a2, du, gl16, gc16`. Appending to that list is safe
and reordering it is not, because a reorder silently changes what every existing client draws.
There is a test asserting the order for that reason.

A page id names the page a frame belongs to, so the device can cache it and be asked for it again
without a round trip. Zero means the message is a rectangle that is drawn and forgotten. A page may
be taller than the panel, which is what the device pans inside; two bytes of height caps that at
65535, or about thirty-nine screens.

## Why it looks like this

**Every field is a whole number of bytes, and none is bit-packed.** The other end of this wire is
a KOReader Lua plugin (Q3, still open, but Lua is the leading candidate). KOReader's Lua has no
`string.unpack`, so the client reads the header with `string.byte` and arithmetic. A two-byte
field is `hi * 256 + lo`. There is a test that reads the header exactly that way, so the
constraint is checked rather than remembered.

Row padding comes from the same place. Without it, an odd-width rectangle leaves half a byte
carried into the next row, and every row after the first starts on a different nibble. That is
cheap in Python and unpleasant in Lua for no gain, since the waste is at most one byte per row.

**Coordinates are in the header from the start.** A full frame is the message whose rectangle
covers the panel, and a dirty rectangle is the same message with a smaller one. The skeleton put
the fields in before anything needed them, which turned out right: the device draws a partial
rectangle today, clipped to the panel, with no second message type and no revision to this part of
the format.

What does not exist yet is a host that chooses to send one. Everything the host currently sends is
a whole page, so dirty rectangles are a capability with no caller. Phase 4 has the case that forces
it, which is streaming text into a view a paragraph at a time.

**Bit depth travels with the message.** The Libra 2 is 4bpp and it is the only panel registered.
A 1bpp Kindle panel is the case that would exercise this field, and carrying it means such a
client fails loudly on a mismatch instead of misreading the payload. The packing code itself is
4bpp only and raises `UnsupportedDepthError` otherwise, which is a named ceiling rather than a
silent one.

**There is no compression.** A full 1264x1680 frame packs to just over a megabyte. Over a unix
socket that is free, and over Tailscale or USB networking it has not been measured. The phase 3
question is dirty rectangles, which cut the same cost by a larger factor and are wanted anyway, so
compression waits for a measurement that says it is still needed after that.

## What is not here yet

No handshake, no acknowledgement, no compression, and no way for the device to ask for a page by
id. The last one is the next likely addition: the device can already tell that a page has been
evicted from its cache, but it has no message for saying so, so the host would have to be told by a
gesture instead. Nothing has needed it yet.

Compression is no longer merely absent, it is a question with a number on it. The viewer sent
frames to its browser as raw pixels until someone reached it through an SSH tunnel and waited four
to five seconds a press; a panel of rendered text compresses about two orders of magnitude, and the
same screen went from 2765 KB to 24 KB. That was a viewer-internal transport and changed nothing
here, but a full frame on this wire is about a megabyte of packed 4bpp, over Wi-Fi, to a device
with 512 MB of RAM. Whether the frame body should be deflated is D1 in
[the device phase](../plans/04_klide_app/06_device_client.md), and it turns on what KOReader's Lua
can decompress, which is a fact about that firmware rather than something to reason out from here.
A protocol change the client cannot decode is worse than a slow protocol.

The magic carries a version, so a client that meets a protocol it does not know refuses it rather
than misreading it.

## Checking it against AD5

AD5 requires that whatever the simulator speaks, the Kobo can speak. The three things that would
have broken that, and what was done instead:

| would break a Lua client | chosen instead |
| --- | --- |
| bit-packed or little-endian header fields | byte-aligned big-endian, read with `string.byte` |
| a length prefix that needs 64-bit arithmetic | 4 bytes, and a frame is about a megabyte |
| rows packed continuously across boundaries | each row padded to a whole byte |

Checked by a second implementation since app phase 5. `viewer/klide_viewer.py` speaks this protocol
without importing klide: it was written from the table above rather than from the code, and it
decodes real frames from a real host over TCP. That is the difference between a format and a
specification, and it found nothing wrong, which is the useful result.

Still unverified: Lua. The viewer is Python, so it shares the language's habits even when it does
not share the code, and the constraint this format was shaped by is what KOReader's Lua can parse.
The test that reads the header with `string.byte` arithmetic stands in for that until Q3 is
answered and a real plugin exists.
