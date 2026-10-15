# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Document<->fact adapter.

Maps the neutral extracted-document IR onto **FG writable facts only** and provides a
path for interview-entered writable facts. This package is the enforced collector boundary:
``OpenTax stays out`` — its sole output is Fact Graph writable facts in the engine's own
persister format, every path validated against ``dictionary/ty2025/``.

Public surface:
  * :func:`collector.adapter.forward.adapt` — documents + interview -> :class:`FactSet`.
  * :class:`collector.adapter.forward.DocumentInput`, :class:`collector.adapter.interview.Interview`.
  * :class:`collector.adapter.facts.FactSet` — validate + serialize to persister JSON.
"""
from __future__ import annotations

from .facts import Fact, FactSet
from .forward import DocumentInput, adapt
from .interview import Dependent, Interview

__all__ = ["Fact", "FactSet", "DocumentInput", "adapt", "Dependent", "Interview"]
