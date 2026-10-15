# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The packaged application stops on its own once its page is gone, so closing the browser tab
does not leave it running in the background.

The page checks in while it is open, and says so when its tab closes. The application stops when
the page said it was closing and no page has checked in since, for GRACE seconds (a reload's new
page checks in well within that), or when no page has checked in at all for SILENCE seconds (a
browser that closed without a word; a hidden tab still checks in about once a minute, since
browsers slow a background tab's timers to that). It never stops while it is working: a return
being computed, or a model's check running. A computer that slept is not a page that left: the
time asleep is not counted.
"""
from __future__ import annotations

import threading
import time

GRACE = 90
SILENCE = 600
TICK = 5
ASLEEP = 30        # a gap this long between two ticks is the computer sleeping


class PageWatch:
    def __init__(self, stop, busy, clock=time.monotonic, grace: float | None = None,
                 silence: float | None = None, tick: float | None = None):
        self._stop, self._busy, self._clock = stop, busy, clock
        self.grace = GRACE if grace is None else grace
        self.silence = SILENCE if silence is None else silence
        self.tick_seconds = TICK if tick is None else tick
        self._lock = threading.Lock()
        self._seen = self._last_tick = clock()
        self._closing: float | None = None
        self._done = threading.Event()

    def seen(self) -> None:
        """A page asked for something: it is open."""
        with self._lock:
            self._seen = self._clock()
            self._closing = None

    def closing(self) -> None:
        """A page's tab is closing (or the page is being reloaded)."""
        with self._lock:
            self._closing = self._clock()

    def due(self) -> str | None:
        """Why the application should stop now, or None."""
        with self._lock:
            now, seen, closing = self._clock(), self._seen, self._closing
        if self._busy():
            return None
        if closing is not None and now - closing >= self.grace:
            return "the page was closed"
        if now - seen >= self.silence:
            return "no page was open"
        return None

    def tick(self) -> bool:
        """One look; True when it stopped the application."""
        now = self._clock()
        with self._lock:
            if now - self._last_tick > ASLEEP:
                # asleep in between: the page gets its full time again from the wake
                self._seen = now
                if self._closing is not None:
                    self._closing = now
            self._last_tick = now
        reason = self.due()
        if reason is None:
            return False
        self._done.set()
        self._stop(reason)
        return True

    def start(self) -> threading.Thread:
        def watch():
            while not self._done.wait(self.tick_seconds):
                if self.tick():
                    return
        thread = threading.Thread(target=watch, name="page-watch", daemon=True)
        thread.start()
        return thread

    def cancel(self) -> None:
        self._done.set()
