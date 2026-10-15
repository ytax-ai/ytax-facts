# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The named cell states, and the one formula that turns a state into a `cellXfs` id.

Eight states plus a default, each in a PLAIN and a MONEY variant — money carries the built-in
`0.00` format, because dollars in the sheet is the whole convention and a `person`
index rendered `0.00` would be a lie about what the column holds.

`style_id(state, money)` is `2 * position + money`, so `cell_xfs()` can hand `ooxml.styles_xml` a
flat sequence whose POSITION is the id. One formula, no lookup table to fall out of step.

**Nothing reads a style back.** Every state the reader and `run` care about is derived from VALUES
and GEOMETRY — CHANGED by comparing the two columns, NOT-READ by a blank ORIGINAL beside a filled
CURRENT. Excel's own save is not trusted to preserve a fill, and a colour is a thing a person can
paint over. Colours are for the person; the facts are for the geometry.
"""
from __future__ import annotations

from . import ooxml

# Order IS the id order. Appending a state is safe; reordering renumbers every cell in the file.
STATES = ("DEFAULT", "LABEL", "RESULT", "ORIGINAL", "CURRENT", "CHANGED", "NOTREAD", "GAP",
          "INVALID")

# ARGB. Grey for what was read, amber for a correction, pale blue for a box nobody read, yellow for
# a fact nobody has supplied, red for a value the service refused BY NAME.
FILLS = {
    "DEFAULT": None,
    "LABEL": None,
    "RESULT": None,
    "ORIGINAL": "FFEDEDED",
    "CURRENT": None,
    "CHANGED": "FFFFE0B2",
    "NOTREAD": "FFD6EAF8",
    "GAP": "FFFFF59D",
    "INVALID": "FFFFCDD2",
}

BOLD = frozenset({"LABEL", "RESULT"})

# Locked cells steer an honest editor; they are a GUIDE RAIL, not security (33a). ORIGINAL is
# locked because it is the record of what the Collector read — `run` never mutates it either.
LOCKED = frozenset({"DEFAULT", "LABEL", "RESULT", "ORIGINAL"})

_POSITION = {state: i for i, state in enumerate(STATES)}


def style_id(state: str, money: bool = False) -> int:
    """`2 * position + money`. An unknown state raises rather than falling back to plain: a cell
    silently styled DEFAULT is a correction nobody can see."""
    return _POSITION[state] * 2 + (1 if money else 0)


def cell_xfs() -> tuple:
    """`(fill, money, bold, locked)` per style id, in id order — `ooxml.styles_xml`'s input."""
    entries = []
    for state in STATES:
        for money in (False, True):
            entries.append((FILLS[state], money, state in BOLD, state in LOCKED))
    return tuple(entries)


def styles_xml() -> str:
    return ooxml.styles_xml(cell_xfs())
