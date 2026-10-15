# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The committed reachability artifact, loaded once and questioned by name.

`generated/reachability.json` is derived from the pinned dictionary's own DAG at development time
(`scripts/generate_reachability.py`) and byte-guarded in the gate; the container ships it inside
`generated/`, so every answer here is engine-free — `coverage` stays the one operation the
anonymous tier can call with no engine anywhere.

A name outside the artifact is REFUSED, never answered `[]`: an empty list is a real answer ("this
input moves no served line" — `/formW2s/*/filer` earns it honestly), so handing it to a typo would
manufacture a confident falsehood.

What these answers MEAN carries the artifact's own ceiling: static reachability says CAN, not
WILL — an edge exists in the pinned XML; whether it carries a value for a given return depends on
conditions and knockouts evaluated at resolve time.
"""
from __future__ import annotations

import json
from pathlib import Path
from .._paths import data_root

_ARTIFACT_PATH = data_root() / "generated" / "reachability.json"
_cache: dict | None = None


class ReachabilityUnknown(KeyError):
    """A name the artifact does not carry — refused by name rather than answered empty."""


def load() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(_ARTIFACT_PATH.read_text(encoding="utf-8"))
    return _cache


def reaches(dict_path: str) -> tuple:
    entry = load()["inputs"].get(dict_path)
    if entry is None:
        raise ReachabilityUnknown(
            f"{dict_path} is not an input the reachability artifact answers for — the artifact "
            f"covers the rename-table paths and mapper.DERIVED_FROM_INPUT; a name outside them "
            f"is refused rather than answered with an empty list.")
    return tuple(entry["reaches"])


def service_field_path(field: str):
    """The engine path behind a service field, or None for a field with no engine-side join
    (identity-plane and envelope fields) — None is an answer, an unknown path is not."""
    return load()["service_fields"].get(field)


def group_reaches(group: str) -> tuple:
    entry = load()["groups"].get(group)
    if entry is None:
        raise ReachabilityUnknown(
            f"{group} is not a fact group the reachability artifact prices — it covers "
            f"STREAM_COLLECTIONS; a group with no engine collection has no reachability to claim.")
    return tuple(entry["reaches"])


def line_feeds(line_id: str) -> tuple:
    feeds = load()["line_feeds"].get(line_id)
    if feeds is None:
        raise ReachabilityUnknown(f"{line_id} is not a served line the artifact knows")
    return tuple(feeds)
