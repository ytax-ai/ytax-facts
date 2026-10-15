# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Engine artifact interface — the single subprocess adapter over the PINNED engine.

The engine is consumed as a pinned, versioned artifact: the engine compiled to JavaScript (run on
Node.js) + dictionary + RUNNER_TODAY determinism pin. No engine source, dictionary, or scenario data lives in this repo.
"""
from .adapter import EngineAdapter, EngineNotAvailable, EnginePin, PINNED

__all__ = ["EngineAdapter", "EngineNotAvailable", "EnginePin", "PINNED"]
