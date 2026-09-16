"""The simulated device: the panel, and the client logic that sits on it.

AD4 puts the client's own behaviour here rather than on the Kobo, so the device client is later a
port of something already working instead of a first attempt. What lives here is therefore
everything a KOReader plugin would have to do: hold a framebuffer, draw a received rectangle into
it with a refresh mode, keep a bounded cache of pages, pan inside a page that is taller than the
screen without asking the host, and draw its own overlay when the host goes away.

Time is claimed, not spent. `elapsed_ms` accumulates what the refresh modes in `waveform` say they
cost, so a design that redraws too often shows up as a large number rather than as a slow test.
Nothing here sleeps for real. The claims and their provenance are in `waveform`.

Ghosting accumulation is not modelled (A2). The device counts partial refreshes since the last
flash, which is what a client needs in order to decide when to flash, but it does not degrade the
image, because there is nothing to calibrate that degradation against yet.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

from klide.frame import Frame
from klide.panel import Panel
from klide.waveform import Mode, Waveform, get_mode

WHITE = 15
BLACK = 0


class PageNotCachedError(KeyError):
    """The page is not in the device's cache, so the host has to send it again."""


class DeviceAsleepError(RuntimeError):
    """The panel cannot be drawn to while the device is suspended."""


@dataclass(frozen=True)
class Refresh:
    """One update of the panel, as the device would account for it."""

    mode: Mode
    x: int
    y: int
    width: int
    height: int
    local: bool


@dataclass
class Device:
    """A Libra 2, as far as the host can tell.

    `cache_pages` bounds the cache. The UI notes settle the size as a handful of pages, thrown away
    on exit, on the grounds that 512 MB of RAM against a frame of about a megabyte makes the limit
    a design choice rather than a hardware one.
    """

    panel: Panel
    cache_pages: int = 4
    flash_every: int = 8

    framebuffer: bytearray = field(init=False)
    pages: OrderedDict[int, Frame] = field(init=False, default_factory=OrderedDict)
    current_page: int = field(init=False, default=0)
    scroll: int = field(init=False, default=0)
    elapsed_ms: int = field(init=False, default=0)
    since_flash: int = field(init=False, default=0)
    history: list[Refresh] = field(init=False, default_factory=list)
    asleep: bool = field(init=False, default=False)
    connected: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        self.framebuffer = bytearray([WHITE] * (self.panel.width * self.panel.height))

    # The panel

    def snapshot(self) -> Frame:
        """What the screen shows right now, as a frame."""
        return Frame(
            panel=self.panel,
            x=0,
            y=0,
            width=self.panel.width,
            height=self.panel.height,
            levels=bytes(self.framebuffer),
        )

    def _blit(self, frame: Frame, at_x: int, at_y: int) -> None:
        """Copy a rectangle into the framebuffer, clipped to the panel."""
        for row in range(frame.height):
            dst_y = at_y + row
            if not 0 <= dst_y < self.panel.height:
                continue
            start = max(0, -at_x)
            end = min(frame.width, self.panel.width - at_x)
            if end <= start:
                continue
            src = row * frame.width
            dst = dst_y * self.panel.width + at_x
            self.framebuffer[dst + start : dst + end] = frame.levels[src + start : src + end]

    def _refresh(self, mode: Mode, x: int, y: int, width: int, height: int, local: bool) -> None:
        self.elapsed_ms += mode.milliseconds
        if mode.flashes:
            self.since_flash = 0
        else:
            self.since_flash += 1
        self.history.append(Refresh(mode, x, y, width, height, local))

    # Messages from the host

    def receive(self, frame: Frame, waveform: Waveform, page_id: int = 0) -> None:
        """Draw a received rectangle, caching it as a page if it is one.

        A page may be taller than the panel; only the visible window is drawn. That is the taller
        page buffer from the UI notes, and it is what makes panning a local answer.
        """
        if self.asleep:
            raise DeviceAsleepError("the panel is suspended; resume before drawing")
        self.connected = True
        if page_id:
            self._cache(page_id, frame)
            self.current_page = page_id
            self.scroll = 0
            self._draw_page()
        else:
            self._blit(frame, frame.x, frame.y)
        self._refresh(get_mode(waveform), frame.x, frame.y, frame.width, frame.height, local=False)

    def _cache(self, page_id: int, frame: Frame) -> None:
        self.pages[page_id] = frame
        self.pages.move_to_end(page_id)
        while len(self.pages) > self.cache_pages:
            self.pages.popitem(last=False)

    # Answered on the device, with no round trip

    def show_cached(self, page_id: int) -> None:
        """Redisplay a page the device already holds.

        This is the reason the cache exists: revisiting a view costs a refresh rather than a
        refresh plus a round trip. Raises if the page has been evicted, which is the host's cue to
        send it again.
        """
        if page_id not in self.pages:
            raise PageNotCachedError(f"page {page_id} is not cached; held: {sorted(self.pages)}")
        self.pages.move_to_end(page_id)
        self.current_page = page_id
        self.scroll = 0
        self._draw_page()
        self._refresh(self._local_mode(), 0, 0, self.panel.width, self.panel.height, local=True)

    def pan(self, delta: int) -> int:
        """Scroll inside the current page without asking the host. Returns the new offset.

        Panning is clamped at both ends rather than wrapping or paging, because running off the
        end of a page is a view change and the host owns those.
        """
        page = self.pages.get(self.current_page)
        if page is None:
            raise PageNotCachedError("no page is displayed, so there is nothing to pan")
        limit = max(0, page.height - self.panel.height)
        self.scroll = max(0, min(limit, self.scroll + delta))
        self._draw_page()
        self._refresh(self._local_mode(), 0, 0, self.panel.width, self.panel.height, local=True)
        return self.scroll

    def _local_mode(self) -> Mode:
        """A full refresh when one is due, otherwise the text mode.

        Panning redraws the whole screen, so it cannot use A2: that mode goes from black and white
        to black and white only, and the page is greyscale text.
        """
        if self.since_flash >= self.flash_every:
            return get_mode(Waveform.GC16)
        return get_mode(Waveform.GL16)

    def _draw_page(self) -> None:
        page = self.pages[self.current_page]
        window = Frame(
            panel=self.panel,
            x=0,
            y=0,
            width=page.width,
            height=min(self.panel.height, page.height - self.scroll),
            levels=page.levels[
                self.scroll * page.width : (self.scroll + self.panel.height) * page.width
            ],
        )
        self.framebuffer[:] = bytearray([WHITE] * (self.panel.width * self.panel.height))
        self._blit(window, 0, 0)

    # Power

    def sleep(self) -> None:
        """Suspend. The framebuffer survives, which is why a resume can repaint from the cache."""
        self.asleep = True

    def resume(self) -> None:
        """Wake and repaint from what the device already holds.

        The design does not need the socket to survive a suspend, it needs coming back to be quick.
        A resume flashes, because the panel has been off and the first draw after that is the one
        place a full refresh is clearly worth its cost.
        """
        self.asleep = False
        if self.current_page in self.pages:
            self._draw_page()
        self._refresh(
            get_mode(Waveform.GC16), 0, 0, self.panel.width, self.panel.height, local=True
        )

    # The host going away

    def disconnect(self) -> None:
        """Lose the host, and say so on the screen.

        K6's answer: keep showing the cache and overlay a marker, because a stale frame with a
        visible warning beats a blank screen. The client has to draw this itself, since the host is
        by definition gone, which is the case that proves the device is not only a frame sink.
        """
        self.connected = False
        self._draw_overlay("host disconnected")
        self._refresh(get_mode(Waveform.DU), 0, 0, self.panel.width, 64, local=True)

    def _draw_overlay(self, text: str) -> None:
        """Paint a banner across the top of whatever is already on screen."""
        height = 56
        strip = Image.new("L", (self.panel.width, height), color=0)
        draw = ImageDraw.Draw(strip)
        font = ImageFont.load_default(size=26)
        draw.text((24, 14), text, font=font, fill=255)
        banner = Frame.from_image(strip, self.panel)
        self._blit(banner, 0, 0)
