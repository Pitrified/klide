# Wire protocol, version 1

What the host sends and the panel receives. Written after the walking skeleton rather than before
it, which is what app phase 2 asks for: the shape is what the skeleton needed, not what a design
document predicted.

One protocol serves the simulator and the real device (AD5). The simulator is not a mock of the
device, it is the first client of the same contract, so the device client is later a second
implementation rather than a rewrite (AD4).

## Message

    offset  size  field
    0       4     magic, b"KLD1"
    4       1     message type, 1 = frame
    5       1     bits per pixel
    6       2     x
    8       2     y
    10      2     width
    12      2     height
    14      4     payload length
    18      ...   payload

All integers are big-endian and unsigned. The header is 18 bytes and is followed immediately by
the payload, so a reader takes 18 bytes, reads the length, then takes that many more.

The payload is rows of pixels, two per byte at four bits each, the leftmost pixel in the high
nibble. Each row is padded to a whole byte, so a row starts at `y * ceil(width / 2)` and no
reader has to carry a bit offset from one row into the next.

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
covers the panel; the dirty rectangles of phase 3 are the same message with a smaller one. Adding
the fields now costs eight bytes per message and means the client does not need a second message
type later. This is the one place the skeleton looks ahead, and it does so because the UI notes
already put a hybrid of full frames and dirty rectangles as the likely landing point.

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

No handshake, no acknowledgement, no input. The skeleton's host sends one frame to one client and
closes, which is enough to prove a frame crosses the wire and no more. Phase 3 brings a connection
that stays open, and touch and the page-turn buttons travelling the other way; those need a second
message type and a direction field, and the magic carries a version so a client can refuse a
protocol it does not know.

## Checking it against AD5

AD5 requires that whatever the simulator speaks, the Kobo can speak. The three things that would
have broken that, and what was done instead:

| would break a Lua client | chosen instead |
| --- | --- |
| bit-packed or little-endian header fields | byte-aligned big-endian, read with `string.byte` |
| a length prefix that needs 64-bit arithmetic | 4 bytes, and a frame is about a megabyte |
| rows packed continuously across boundaries | each row padded to a whole byte |

Unverified: no Lua client exists yet. The test that reads the header with byte arithmetic shows
the header is readable that way, which is weaker than a working client and is the strongest check
available before Q3 is answered.
