# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The return kept in the working folder, so a person can stop and come back.

Until now a return lived only in the page's memory: closing the window, or restarting the app, lost
every answer and every document read, and the folder's PDFs had to be dropped again. This module
writes what the page holds — the case (its confirmed answers and their provenance) and the little
the loop keeps beside it (which documents were read, which questions were answered on a checklist,
which streams were closed, whether the figures were computed) — into the working folder's
`input/case.session.json`, and reads it back when that folder is opened again.

It stays on this computer, beside the identity file and the notations: it is the return, so it is
never sent anywhere. It holds no identity — names and taxpayer IDs live in `case.identity.ini`,
which this never touches — and the documents themselves stay where they are in `input\\`.

A document is stored as the RECORD of the read, not the read again: the figures it proposed are
already in the case, confirmed or waiting, so nothing is re-extracted when a folder is reopened,
and dropping the same file again is still refused by name (the digest travels with the record).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path

FILENAME = "case.session.json"
VERSION = 1


class SessionError(ValueError):
    """A saved return this page cannot read, said in words a person can act on."""


@dataclass
class DocumentRecord:
    """What the page remembers about a document it read: enough for the documents list, the
    duplicate check and the state proposal, never the extraction again."""
    document: str
    form_type: str
    read: int = 0
    group: str | None = None
    unconsumed: str | None = None
    not_carried: list = field(default_factory=list)
    # decision (a): None for a record saved before the split existed — the page then keeps the
    # single not-read line rather than calling every box "stored only".
    not_carried_lines: dict | None = None
    vocabulary: str = "tables"
    index: int | None = None
    digest: str | None = None
    content: str | None = None
    work_state: str | None = None
    work_state_evidence: object = None
    read: int = 0
    candidates: list = field(default_factory=list)
    unread: list = field(default_factory=list)


def _document_dict(doc) -> dict:
    return {"document": Path(getattr(doc, "document", "") or "").name,
            "form_type": getattr(doc, "form_type", "UNKNOWN"),
            "group": getattr(doc, "group", None),
            "unconsumed": getattr(doc, "unconsumed", None),
            "not_carried": list(getattr(doc, "not_carried", []) or []),
            "not_carried_lines": (None if getattr(doc, "not_carried_lines", None) is None
                                  else dict(doc.not_carried_lines)),
            "vocabulary": getattr(doc, "vocabulary", "tables"),
            "index": getattr(doc, "index", None),
            "digest": getattr(doc, "digest", None),
            # a workbook row carries the number of ANSWERS it gave, where a document row carries
            # the number of boxes read: `read` is the one name the page's list asks for
            "read": getattr(doc, "answered", None) or len(getattr(doc, "candidates", []) or []),
            # what the document SAYS, as one value: the same form read twice is
            # recognised across sittings too. It is a hash of figures, never a figure.
            "content": getattr(doc, "content", None),
            "work_state": getattr(doc, "work_state", None),
            "read": len(getattr(doc, "candidates", []) or [])}


def to_dict(loop, computed_at: str | None = None) -> dict:
    """Everything the page must hold to carry on where it stopped."""
    return {
        "version": VERSION,
        "saved_at": _now(),
        "tax_year": loop.case.tax_year,
        "case": json.loads(loop.case.to_json()),
        "documents": [_document_dict(d) for d in loop.documents],
        "counts": dict(loop._counts),
        "dependents_asked": bool(loop._dependents_asked),
        "declined": sorted(loop._declined),
        "checked": sorted(loop._checked),
        "closed": sorted(loop._closed),
        "topics_asked": bool(loop._topics_asked),          # the forms-not-read checklist
        "topics_ticked": list(loop._topics_ticked),
        "stubs": dict(loop._stubs),
        # the "how many more of these forms?" page: asked once, and the workbook its rows went to
        "more_forms_asked": bool(getattr(loop, "_more_forms_asked", False)),
        "more_forms": dict(getattr(loop, "_more_forms", {}) or {}),
        "more_taken": bool(getattr(loop, "_more_taken", False)),
        "more_workbook": getattr(loop, "more_workbook", None),
        "reviewed": bool(loop._reviewed),
        "computed_at": computed_at if computed_at is not None else getattr(loop, "computed_at", None),
        # which return the forms in the output folder were filled for: forms from before the
        # return last changed are never offered as this return's
        "filled_for": getattr(loop, "filled_for", None),
        # the answers return-workbook.xlsx was written from, and an edit of it the person turned
        # down: an edited workbook is asked about once, and again only if it changes again
        "workbook_for": getattr(loop, "workbook_for", None),
        "workbook_declined": getattr(loop, "workbook_declined", None),
    }


def _now() -> str:
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def save(loop, folder) -> Path:
    """Write the return into the working folder. The file is replaced whole, through a temporary
    file, so a stop in the middle never leaves half a return behind."""
    path = Path(folder) / "input" / FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(to_dict(loop), indent=1), encoding="utf-8")
    tmp.replace(path)
    return path


def read(folder) -> dict | None:
    """The saved return in this folder, or None when there is none. A file that cannot be read is
    REFUSED by name rather than ignored: silently starting an empty return would throw away
    everything the person had answered."""
    path = Path(folder) / "input" / FILENAME
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as why:
        raise SessionError(f"{path} holds a return this page cannot read ({why}). Move it aside to "
                           f"start again; the documents in this folder are untouched.")
    if not isinstance(doc, dict) or doc.get("version") != VERSION:
        raise SessionError(f"{path} was written by another version of this page. Move it aside to "
                           f"start again; the documents in this folder are untouched.")
    return doc


def set_aside(folder) -> Path | None:
    """Start this folder again: the saved return is RENAMED, never deleted — a person who meant to
    keep it can put the file back, and the documents in the folder are untouched."""
    import datetime
    path = Path(folder) / "input" / FILENAME
    if not path.is_file():
        return None
    kept = path.with_name(f"case.session.{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    path.replace(kept)
    return kept


def carries_a_return(doc: dict) -> bool:
    """Whether a saved file holds anything a person would recognise as their return. The page keeps
    a file the moment a folder is confirmed, so an empty one must not announce itself as work
    someone left behind."""
    return bool(doc.get("documents") or (doc.get("case") or {}).get("confirmed"))


def restore(doc: dict, ops=None, pdf_root=None, model=None, reader=None):
    """The loop the saved return describes, ready to carry on at the turn it stopped at."""
    from .case import Case
    from .loop import IntakeLoop
    try:
        case = Case.from_json(json.dumps(doc["case"]))
    except Exception as why:                      # a fact path this version no longer knows
        raise SessionError(f"the return saved in this folder cannot be opened by this version of "
                           f"the page ({why}). It is left as it is; 'Start this folder again' sets "
                           f"it aside.")
    loop = IntakeLoop(case, ops=ops, pdf_root=pdf_root, model=model, reader=reader)
    known = {f.name for f in fields(DocumentRecord)}
    loop.documents = [DocumentRecord(**{k: v for k, v in d.items() if k in known})
                      for d in doc.get("documents", [])]
    loop._counts = dict(doc.get("counts") or {})
    loop._dependents_asked = bool(doc.get("dependents_asked"))
    loop._declined = set(doc.get("declined") or [])
    loop._checked = set(doc.get("checked") or [])
    loop._closed = set(doc.get("closed") or [])
    loop._topics_asked = bool(doc.get("topics_asked"))     # absent in a return kept before the fallback:
    loop._topics_ticked = list(doc.get("topics_ticked") or [])   # the checklist is then asked once
    loop._stubs = dict(doc.get("stubs") or {})
    # absent in a return kept before the page asked it: asked once, when the folder is reopened
    loop._more_forms_asked = bool(doc.get("more_forms_asked"))
    loop._more_forms = {g: int(n) for g, n in (doc.get("more_forms") or {}).items()}
    loop._more_taken = bool(doc.get("more_taken"))
    loop.more_workbook = doc.get("more_workbook")
    loop._reviewed = bool(doc.get("reviewed"))
    # Figures carry when they were computed. A reopened return shows the answers it
    # holds, never figures from another sitting — so the compute is done again before anything is
    # shown, and `computed_at` is what the SAVED return said, for the sentence that names it.
    loop.computed_at = None
    loop.filled_for = doc.get("filled_for")      # absent in a return kept before: forms not vouched for
    loop.workbook_for = doc.get("workbook_for")
    loop.workbook_declined = doc.get("workbook_declined")
    return loop
