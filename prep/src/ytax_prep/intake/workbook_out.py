# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The original workbook, written beside the filled forms.

The page no longer READS a workbook — the documents and the questions are the input — but a person
can still try a scenario in one: change an amount, compute again, see what moves. So every fill
writes `return-workbook.xlsx` into the output folder from the answers the page holds, computed once
against the same local engine, and the page can compute it again after it is edited. It is facts
only: `build_workbook` takes no identity, so no name, taxpayer ID or date the page keeps locally
ever enters it. Computing it changes nothing on the page; the return there stays the one asked.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

NAME = "return-workbook.xlsx"


def _stated_at() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write(facts: dict, tax_year: int, out_dir, ops=None, originals: dict | None = None) -> Path:
    """Build the workbook from the page's answers and compute it once; return where it went.
    `originals` — what the paper says, `{path: cents}` — fills `From the form` where an answer
    differs from it (seen 2026-09-23: changing `Amount to use` changed it too)."""
    from ..client.interview import open_questions
    from ..client.transport import local_sender
    from ..client.workbook.__main__ import run_workbook
    from ..client.workbook.writer import build_workbook
    case = {**facts, "tax_year": tax_year}
    data = build_workbook(case, [], open_questions(case), originals=originals)
    data = run_workbook(data, local_sender(ops), stated_at=_stated_at())
    path = Path(out_dir) / NAME
    path.write_bytes(data)
    return path


def write_added(facts: dict, tax_year: int, out_dir, added: dict) -> Path:
    """The workbook for forms the person said they have and will type in (decided
    2026-09-28): the return read so far, plus `added` — `{group: count}` — empty rows after each
    group's own, to be filled and saved. Written, NOT computed: a compute reads the file back and
    writes it again, and an empty row is not read, so the rows would be gone before anyone saw
    them. Same name and folder as the workbook a fill writes."""
    from ..client.interview import open_questions
    from ..client.workbook.writer import build_workbook
    case = {**facts, "tax_year": tax_year}
    data = build_workbook(case, [], open_questions(case), added=dict(added))
    path = Path(out_dir) / NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def compute_again(out_dir, ops=None) -> Path:
    """The person edited the workbook: compute it again in place, the workbook's own `run`."""
    from ..client.transport import local_sender
    from ..client.workbook.__main__ import run_workbook
    path = Path(out_dir) / NAME
    if not path.is_file():
        raise FileNotFoundError(f"There is no {NAME} in {Path(out_dir)} yet; fill the forms first.")
    path.write_bytes(run_workbook(path.read_bytes(), local_sender(ops), stated_at=_stated_at()))
    return path
