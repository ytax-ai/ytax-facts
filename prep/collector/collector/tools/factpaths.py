#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Enumerate the *writable* fact-paths declared by the TY2025 Fact Graph dictionary.

This is the keystone of the collector: the
document->fact adapter may only emit writable fact-paths that actually
exist in `dictionary/ty2025/`. This module reads the dictionary XML directly and
exposes the authoritative set, plus a validator that gate 3 (`collector/gate.sh`)
runs in CI. It is the analog of the dictionary track's namespace lint: it keeps
the adapter bound to the real dictionary instead of drifting hard-coded strings.

A *writable* fact is a `<Fact path="...">` element whose direct child is a
`<Writable>` element (per `docs-upstream/writing-facts.md` and the
`FactDictionaryModule.rng` schema). Derived facts (`<Derived>`) are excluded:
the adapter writes inputs, it never writes computed values.

The dictionary XML uses no XML namespace, so tag names are matched bare.

Usage (run from anywhere; the dictionary is located relative to this file):

    python collector/collector/tools/factpaths.py list                 # one path per line
    python collector/collector/tools/factpaths.py validate /a/b /c     # exit 1 on any unknown
    python collector/collector/tools/factpaths.py selftest             # used by gate 3
    python collector/collector/tools/factpaths.py list --dict-dir DIR   # override location
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# collector/collector/tools/factpaths.py -> parents[3] is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _default_dict_dir() -> Path:
    """Where the TY2025 dictionary lives. **`YTAX_ENGINE_HOME` or nothing.**

    In the BUILD repo the dictionary sat at `<repo>/dictionary/ty2025`, beside this package. In this
    application the engine is a **pinned artifact**: there is no in-tree dictionary, and its
    location comes from `YTAX_ENGINE_HOME` (an engine home at the pin), as it does for every other
    consumer here.

    **There is deliberately NO fallback to the old sibling path** (decided 2026-08-11). A fallback
    would resolve to a directory that belongs to a different repo — either absent, or present and
    holding a DIFFERENT dictionary than the one this service is pinned to. Both outcomes are worse
    than stopping: the first fails somewhere confusing, and the second is the exact mistake that
    caused a fix to be verified against the wrong dictionary and reverted. Choosing a dictionary by
    accident is how a wrong number gets computed confidently.
    """
    import os
    home = os.environ.get("YTAX_ENGINE_HOME")
    if not home:
        raise RuntimeError(
            "YTAX_ENGINE_HOME is not set, so there is no dictionary to read. This repo "
            "consumes the engine as a PINNED ARTIFACT — it keeps no dictionary of its own, and "
            "there is no fallback path on purpose: guessing which dictionary to use is how a "
            "number gets computed against the wrong tax year's rules. Set it to an engine home at "
            "the pin (see BUILD.md, 'Run from the source files'), then confirm with "
            "`discover_pin().matches_pin`.")
    return Path(home) / "dictionary" / "ty2025"


DEFAULT_DICT_DIR = _default_dict_dir()

# A collection-instance segment in a concrete path: "#<uuid>" or a bare integer
# index. The dictionary authors collection members with a literal "*" wildcard
# (e.g. /dividendReports/*/amount); a runtime adapter produces concrete ids. We
# normalize the latter back to "*" before matching.
_INSTANCE_SEG = re.compile(r"^(#[0-9a-fA-F-]+|\d+)$")


def _local(tag: str) -> str:
    """Strip any XML namespace from a tag name (defensive; dictionary has none)."""
    return tag.rsplit("}", 1)[-1]


def writable_factpaths(dict_dir: Path = DEFAULT_DICT_DIR) -> set[str]:
    """Return the set of writable fact-paths declared across the dictionary.

    Raises FileNotFoundError if the directory is missing, ValueError if it is
    present but declares no writable facts (a sign the parser or the path is
    wrong — never silently return an empty set, which would make the validator
    reject everything).
    """
    if not dict_dir.is_dir():
        raise FileNotFoundError(f"dictionary directory not found: {dict_dir}")

    paths: set[str] = set()
    for xml_path in sorted(dict_dir.glob("*.xml")):
        root = ET.parse(xml_path).getroot()
        for fact in root.iter():
            if _local(fact.tag) != "Fact":
                continue
            path = fact.get("path")
            if not path:
                continue
            if any(_local(child.tag) == "Writable" for child in fact):
                paths.add(path)

    if not paths:
        raise ValueError(
            f"no writable fact-paths found under {dict_dir} — "
            "wrong directory, or the dictionary format changed"
        )
    return paths


def declared_factpaths(dict_dir: Path = DEFAULT_DICT_DIR) -> set[str]:
    """Return EVERY declared fact-path (writable *and* derived) across the dictionary dir.

    The writable-only :func:`writable_factpaths` is what the adapter is bound to; this wider set
    also validates *derived* fact-paths (never writable) against the dictionary. Unlike
    :func:`writable_factpaths` an empty result is allowed — a directory may legitimately be
    scanned before any module exists.
    """
    if not dict_dir.is_dir():
        raise FileNotFoundError(f"dictionary directory not found: {dict_dir}")
    paths: set[str] = set()
    for xml_path in sorted(dict_dir.glob("*.xml")):
        root = ET.parse(xml_path).getroot()
        for fact in root.iter():
            if _local(fact.tag) != "Fact":
                continue
            path = fact.get("path")
            if path:
                paths.add(path)
    return paths


def normalize(path: str) -> str:
    """Collapse concrete collection-instance segments (#guid / index) to '*'.

    Lets a runtime path like /dividendReports/#a1b2/amount match the authored
    wildcard /dividendReports/*/amount.
    """
    return "/".join(
        "*" if _INSTANCE_SEG.match(seg) else seg for seg in path.split("/")
    )


def unknown_paths(
    candidates: list[str], dict_dir: Path = DEFAULT_DICT_DIR
) -> list[str]:
    """Return the candidates that are NOT writable fact-paths, order preserved."""
    valid = writable_factpaths(dict_dir)
    return [p for p in candidates if normalize(p) not in valid]


def _cmd_list(args: argparse.Namespace) -> int:
    for p in sorted(writable_factpaths(args.dict_dir)):
        print(p)
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    missing = unknown_paths(args.paths, args.dict_dir)
    if missing:
        print("INVALID: the following are not writable fact-paths:", file=sys.stderr)
        for p in missing:
            print(f"  {p}", file=sys.stderr)
        return 1
    print(f"OK: all {len(args.paths)} path(s) are writable fact-paths")
    return 0


def _cmd_selftest(args: argparse.Namespace) -> int:
    """Gate 3: prove the enumerator works against the live dictionary."""
    paths = writable_factpaths(args.dict_dir)
    print(f"OK: enumerated {len(paths)} writable fact-paths from {args.dict_dir}")
    # Round-trip: every enumerated path must validate against itself, and a
    # deliberately bogus path must be rejected.
    sample = sorted(paths)[0]
    assert not unknown_paths([sample], args.dict_dir), "self-validation failed"
    bogus = "/__definitely_not_a_real_fact__"
    assert unknown_paths([bogus], args.dict_dir) == [bogus], "bogus path accepted"
    print("OK: self-validation round-trip passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dict-dir",
        type=Path,
        default=DEFAULT_DICT_DIR,
        help="dictionary directory to read (default: dictionary/ty2025)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="print every writable fact-path")
    p_val = sub.add_parser("validate", help="exit nonzero if any path is not writable")
    p_val.add_argument("paths", nargs="+")
    sub.add_parser("selftest", help="enumerate + round-trip validate (gate 3)")

    args = parser.parse_args(argv)
    dispatch = {"list": _cmd_list, "validate": _cmd_validate, "selftest": _cmd_selftest}
    try:
        return dispatch[args.cmd](args)
    except BrokenPipeError:
        # Downstream closed the pipe (e.g. `... | head`); not an error.
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
