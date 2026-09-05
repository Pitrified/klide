---
status: draft
---

# UI and UX brainstorm

Starting notes, not decisions. Sits under [`00_start.md`](00_start.md); D1 and D11 come from [`../00_initial/00_start.md`](../00_initial/00_start.md).
Nothing here is tested, and the KOReader API names below are from documentation rather than from running code.

## Is host-renders-and-streams right

That is D1, and it still looks right for the reasons it was taken: layout, markdown, diff colouring and syntax highlighting
are all easier in Python on a real machine than in Lua on the device, and a second device becomes mostly a screen size.

What it actually commits to is smaller than it sounds. D1 says pixels are computed on the host.
It does not say the device is forbidden to know anything: caching, panning within a received image, and gesture interpretation can all sit on the device
without moving layout off the host.

## The spectrum

From most host-side to most device-side.

1. **Full frames.** Host sends a whole screen image, device blits it. Simplest possible client. The Libra 2 panel is 1264x1680, so 8bpp is a little over 2 MB raw per frame, against 512 MB of RAM. Leans on compression and on not sending many.
2. **Dirty rectangles.** Host sends only the region that changed, with its coordinates, and the device blits and refreshes that region. Same model as 1, much less data, and it matches how e-ink wants to be driven. Probably where this lands.
3. **Draw list.** Host sends positioned text runs and rules, device renders them with fonts it already has. Smaller payloads than pixels, layout still host-side, but now the device needs the same fonts and metrics or the layout the host computed is wrong.
4. **Taller-than-screen pages.** Host renders a page several screens tall, device pans within it locally. Swipes get instant feedback without a round trip, at the cost of the device holding state.
5. **Semantic content.** Host sends structured content, device lays it out. Contradicts D1 and puts the interesting work in Lua.

There is also a non-option worth naming so it stops coming up: generating an epub or HTML per conversation and letting KOReader open it.
Cheap, and it fails the primary requirement, which is continuous update with no reload.

A hybrid of 2 and 4 is the obvious first guess: dirty rectangles for streaming text, a taller page buffer for scrolling.

## Touch and swipe

Touch is always handled on the device, whatever else is true, because that is where the touchscreen is.
The question is only whether a gesture is answered locally or forwarded.

- **Forwarded.** Device sends a gesture event to the host, host recomputes and pushes a frame. One network round trip on top of the refresh. Fine for anything that changes what is displayed: next conversation, open a diff, jump to a file.
- **Local.** Device answers from what it already holds: panning inside a taller page, or showing a "loading" marker. No round trip, so it feels immediate.

As a KOReader plugin the mechanism looks like `InputContainer:registerTouchZones` with entries carrying an `id`, a `ges` of `tap` or `swipe`,
a `screen_zone` in ratio coordinates, and a handler receiving the gesture, where a swipe carries a `direction`. Unverified.

The Libra 2 also has physical page-turn buttons, which the Kindle path did not.
Paging is the most frequent action and the one that most wants to feel instant,
so it is the best candidate for a local answer and for not spending a gesture on.

Provisional gesture map, given klide is read-only toward Claude (D11):

- page-turn buttons, and swipe left and right: page within the current view
- swipe up and down: switch view, conversation to diff to files
- tap left and right thirds: previous and next item in the current list
- tap centre: open or close the item under the cursor
- long hold: force a full refresh, which doubles as the ghosting escape hatch

## Streaming or polling

Push, from a connection the device opens outward to the host. That works the same over Tailscale, LAN or USB networking,
and it avoids the host needing to find the device.
Polling was rejected for the Kindle path already, and nothing about Kobo brings it back.

The catch is device-side concurrency, which differs by client shape:

- **KOReader plugin.** Lua with a single UI event loop, so a blocking read is not available. The pattern other plugins use is a non-blocking socket polled from `UIManager:scheduleIn` at a short interval. That is local polling, not network polling, and it costs a wakeup rather than a round trip. It also puts a floor on latency equal to the poll interval.
- **Native binary.** Two threads or two processes, one blocking on the socket and one on the input device. Simpler concurrency, more to build and install.

Either way the shape is a slideshow driven by the host: the host decides when a frame is worth sending.

## How fast

Three limits, in the order they bite.

1. **The reader.** Streaming every token to e-ink is pointless. The host should coalesce and send a frame when the content settled, or on a cadence, whichever comes first.
2. **The panel.** KOReader exposes refresh modes, `a2`, `fast`, `ui`, `partial`, `flashui`, `flashpartial`, `full`, and the fast ones trade quality for latency. Partial updates accumulate ghosting until a full refresh clears it. How many, and how slow each is, is a measurement the spike has to take.
3. **The link.** Only matters if we send full frames uncompressed. Dirty rectangles make it a non-issue.

Text appearing a line or a paragraph at a time, with a full refresh occasionally, is the target to aim at until something is measured.

## Fullscreen

Yes, and not by choice. KOReader takes over the framebuffer and Nickel is suspended while it runs, so there is no window, no chrome and no status bar
unless klide draws one. A native binary is the same picture, except it has to stop Nickel itself or Nickel will paint over it.

The real UX problem in this area is not framing but sleep. The device suspends on its own, and a display that goes blank mid-answer is useless.
KOReader has the machinery for this, and battery life is the counterweight.

## Rough view set

Conversation, conversation list, changed files, one diff, file tree, one file. Six views, one gesture map, one status line.
Everything on the list except the diff is a scrolling column of text, which is the case to make good first.

## To measure in the spike

- Latency of a small partial refresh, and how many before ghosting forces a full one.
- How long a reconnect and repaint takes after a wake. Holding the socket across a suspend is no longer needed, coming back fast is.
- Poll interval that keeps the UI responsive without draining the battery.
- Cost of a full frame against a dirty rectangle, once a real panel size is known.

## Preliminary feelings

Recorded 2026-09-05, from a first read of the above. Leanings, not settled.

* **Device-side cache and a taller page buffer, yes.** Enough to drag the page around and to reopen something without a round trip.
  Minimal to small: a handful of pages in memory, bounded, thrown away on exit. No database and nothing to maintain on the device.
  512 MB of RAM against a 2 MB frame means the ceiling is a design choice, not a hardware limit.
* **Fullscreen, gladly.**
* **Sleep is not a problem.** This is an interactive sink for checking on an assistant, not an unattended dashboard, so the device sleeps
  the way it normally does and no keep-alive machinery is needed. What that does require is a clean resume: reconnect and repaint quickly
  on wake. The socket does not have to survive a suspend, it has to come back without ceremony.
* **K5, yes.** The device holds a little state. See the cache note above for the size.
* **K6, keep showing the cache and overlay a marker.** A stale frame with a visible warning beats a blank screen.
  This is the one place the client has to draw something itself rather than blit what it was sent, since the host is by definition gone.
  As a KOReader plugin that is free.

## Pinch to zoom

The gesture is available, KOReader detects pinch and spread. What is not available is a smooth zoom.

Two reasons. The panel cannot track fingers continuously, so anything gradual will look like a slideshow of intermediate states.
And the frame is a bitmap the host rendered at one size, so scaling it on the device gives a blurry image rather than more detail.

The workable version is discrete: detect the gesture, treat it as one step of text size, ask the host to re-render, replace the frame.
A scaled version of the cached bitmap can fill the gap while the real frame arrives, if the wait is visible.
Same shape as dragging, where the honest approach is to move in steps or to settle on release rather than to promise
continuous feedback the panel cannot deliver.

## Open questions

- K4: Which of the spectrum options for the first working version. Leaning 2, with 4 added if scrolling feels bad.
- ~~K5: Does the device hold any state beyond the current frame.~~ Yes, a small bounded cache. See Preliminary feelings.
- ~~K6: What happens on disconnect.~~ Keep showing the cache, overlay a marker.
- K9: How the taller page buffer and the cache interact. One is for panning inside a view, the other for revisiting views, and they may or may not be the same thing.
