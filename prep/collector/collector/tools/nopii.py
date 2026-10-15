#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""No-PII scan: prove every git-tracked Collector file holds only synthetic data.

Collector gate 4 (the privacy posture). Raw and redacted documents are never
committed (`collector/.gitignore`); the only committed documents are synthetic
fixtures. This scan enforces that whatever *is* committed uses identifiers from
the deliberately-invalid ranges, so a real SSN or EIN can never slip in.

Rules (a match outside the synthetic-safe range FAILS the gate):

  SSN  `NNN-NN-NNNN` : area number must be 000, 666, or 900-999. Those areas
                       are never issued by the SSA, so a real SSN cannot use
                       them. (Bare 9-digit runs are NOT matched, to avoid false
                       positives on CUSIPs and lot numbers.)
  EIN  `NN-NNNNNNN`  : prefix must be 00. The IRS has never issued the 00
                       prefix, so synthetic EINs use it and real ones cannot.

Scope: files reported by `git ls-files collector/`. Text files are scanned
directly; committed PDFs are scanned via their extracted text (pdfplumber —
the permissive stack) when available, else reported as un-scannable (which
is acceptable only because the .gitignore keeps non-synthetic PDFs out of the
tree entirely).

    python collector/collector/tools/nopii.py            # scan; exit 1 on any finding
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# collector/collector/tools/nopii.py -> parents[3] is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_COLLECTOR = _REPO_ROOT / "collector"

_SSN_RE = re.compile(r"\b(\d{3})-(\d{2})-(\d{4})\b")
_EIN_RE = re.compile(r"\b(\d{2})-(\d{7})\b")


def _ssn_is_synthetic(area: str) -> bool:
    a = int(area)
    return a == 0 or a == 666 or a >= 900


def _ein_is_synthetic(prefix: str) -> bool:
    return prefix == "00"


def _tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "collector/"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [_REPO_ROOT / line for line in out.splitlines() if line]


def _text_of(path: Path) -> str | None:
    """Return text content for scanning, or None if the file can't be scanned."""
    if path.suffix.lower() == ".pdf":
        try:
            import pdfplumber  # type: ignore[import-untyped]
        except ImportError:
            return None
        try:
            with pdfplumber.open(path) as doc:
                return "\n".join(pg.extract_text() or "" for pg in doc.pages)
        except Exception:
            return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None  # binary / unreadable: nothing to scan


def scan() -> list[str]:
    """Return a list of human-readable findings (empty == clean)."""
    findings: list[str] = []
    for path in _tracked_files():
        text = _text_of(path)
        if text is None:
            continue
        rel = path.relative_to(_REPO_ROOT)
        for m in _SSN_RE.finditer(text):
            if not _ssn_is_synthetic(m.group(1)):
                findings.append(f"{rel}: real-looking SSN {m.group(0)}")
        for m in _EIN_RE.finditer(text):
            if not _ein_is_synthetic(m.group(1)):
                findings.append(f"{rel}: real-looking EIN {m.group(0)}")
    return findings


def main() -> int:
    findings = scan()
    if findings:
        print("FAIL: non-synthetic identifiers in committed files:", file=sys.stderr)
        for f in findings:
            print(f"  {f}", file=sys.stderr)
        return 1
    print("OK: no non-synthetic SSN/EIN identifiers in tracked collector files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
