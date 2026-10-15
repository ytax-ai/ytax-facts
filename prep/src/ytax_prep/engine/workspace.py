# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""One known place for working files, and a bound on how long a crash's residue can live.

Every calculation writes a scenario file and reads back a resolved TSV, so fact data lands on disk
on the way to the engine. `TemporaryDirectory` removes it on return and on exception, which covers
almost everything — but not the case that matters: **SIGKILL, an OOM kill, or a container stop
mid-request leaves the directory behind**, and nothing ever comes back for it. That residue must
be bounded.

The fix cannot be "clean up harder on the way out": by construction the process is already gone. So
it is a **sweep on the way IN**. Every start clears what the last crash left, which makes the
lifetime of any residue bounded by the restart interval rather than unbounded.

TWO THINGS THIS DEPENDS ON, both deliberate:

* **One root.** Scattered temp directories cannot be swept, because nothing knows where to look.
  Everything lands under `work_root()`, which is what makes the crash path recoverable at all.
* **An age threshold, and a principled one.** The deployed shape runs `--concurrency=2`, and the
  warm host scales by MORE PROCESSES — so a starting process shares this directory with siblings
  that are mid-request. A sweep that deleted everything would pull a scenario file out from under a
  live calculation, turning cleanup into an outage. Anything still running has by definition not
  exceeded the per-request engine timeout, so that timeout is what separates residue from live work.

Best-effort by design: one undeletable entry must not stop the others, and must never take the
service down at startup. Failing to clean up is bad; failing to *start* because cleanup failed is
worse.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import tempfile
import time
from pathlib import Path

from .adapter import SUBPROCESS_TIMEOUT_SECONDS

# Overridable so tests never sweep a real root, and so a deployment can point working files at a
# writable volume without code changes.
WORK_ROOT_ENV = "YTAX_WORK_ROOT"

# Older than a full engine request => nobody is still working on it. Derived from the timeout rather
# than picked, so the two cannot drift into a window where the sweep eats live work.
MAX_WORK_AGE_SECONDS = SUBPROCESS_TIMEOUT_SECONDS + 60


def work_root() -> Path:
    """The single directory every working file lives under."""
    configured = os.environ.get(WORK_ROOT_ENV)
    root = Path(configured) if configured else Path(tempfile.gettempdir()) / "ytax-work"
    root.mkdir(parents=True, exist_ok=True)
    return root


@contextlib.contextmanager
def workspace(prefix: str = "req-"):
    """A directory for one request's working files, removed when the request ends.

    Yields a `str` so it drops into the existing `tempfile.TemporaryDirectory` call sites unchanged.
    """
    path = tempfile.mkdtemp(prefix=prefix, dir=str(work_root()))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def sweep(max_age_seconds: float = MAX_WORK_AGE_SECONDS) -> int:
    """Remove working directories older than `max_age_seconds`. Returns how many were removed.

    Called at startup: the process that crashed cannot clean up after itself, so the next one does.
    """
    root = Path(os.environ.get(WORK_ROOT_ENV) or (Path(tempfile.gettempdir()) / "ytax-work"))
    if not root.is_dir():
        return 0                       # first start on a fresh container — nothing to sweep
    cutoff = time.time() - max_age_seconds
    removed = 0
    for entry in root.iterdir():
        try:
            if entry.stat().st_mtime >= cutoff:
                continue               # young enough that a sibling process may still be using it
            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink()
            removed += 1
        except OSError:
            # Best effort. One entry we cannot remove must not stop the rest, and must never
            # prevent the service starting.
            continue
    return removed
