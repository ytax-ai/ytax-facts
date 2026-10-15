# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Which engine the service uses — warm by default, cold by explicit choice.

Adopted (2026-08-12) after the case was measured at the pin.
The engine is kept warm across requests instead of forking a JVM per calculation: **2.13 s → 0.47 s**
per call, with the resolved TSV byte-identical either way.

WHAT THIS DOES AND DOES NOT COST, corrected after measuring both ends. A cold fork already peaks at
**442 MiB**; the resident process holds **496 MiB**. So warmth barely moves PEAK memory — what it
changes is that the memory is *sustained* rather than transient. At `--concurrency=2` the deployed
`--memory=1Gi` instance was already marginal today (two concurrent cold forks ≈ 880 MiB peak); warm
makes it permanently marginal instead of intermittently. **That sizing question is real and it is
older than this change**, and it belongs to whoever signs for spend.

ONE PROCESS-WIDE INSTANCE, deliberately: the runner's `dictCache` is unsynchronised, so calculations
are serialised per process and concurrency is served by more processes. A second warm engine inside
one process would buy nothing and double the footprint.

`YTAX_ENGINE_MODE=cold` reverts to a fork per calculation without a code change. That is an
explicit switch, not a fallback: nothing silently downgrades, because a service that quietly changes
how it computes is a service whose numbers you cannot reason about.
"""
from __future__ import annotations

import atexit
import os
import threading

from .adapter import EngineAdapter
from .warm import WarmEngine

ENGINE_MODE_ENV = "YTAX_ENGINE_MODE"

_warm: WarmEngine | None = None
_lock = threading.Lock()


def default_engine():
    """The engine this process should use. Warm unless explicitly told otherwise."""
    if os.environ.get(ENGINE_MODE_ENV, "warm").strip().lower() == "cold":
        return EngineAdapter()
    global _warm
    with _lock:
        if _warm is None:
            _warm = WarmEngine()
            atexit.register(_shutdown)
        return _warm


def _shutdown() -> None:
    global _warm
    engine, _warm = _warm, None
    if engine is not None:
        engine.close()


def reset_for_test() -> None:
    """Drop the process-wide engine. Tests that switch modes must not inherit the other one."""
    _shutdown()
