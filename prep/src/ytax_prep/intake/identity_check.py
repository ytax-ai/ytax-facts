# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Does this document look like it belongs to the person filing this return?

A second copy of one Form W-2 was dropped on the page and the wages doubled, silently; and
nothing ever checked that the name and address on a document match the identity the filled forms will
carry. Both are answered here, and both by comparing what is ALREADY on this computer — never by
learning anything new about anybody.

THE DIRECTION MATTERS. This does not read the recipient's name off the paper: that would be an
identifier this service refuses to hold, and a name read badly is worse than none. It
takes the identity the person typed into `case.identity.ini` — which is theirs, already on this
machine, and never sent anywhere — and looks for it in the document's own text. What comes back is a
sentence for the person to act on, held in memory for as long as the page is open and written into
no file: not the case, not the session, not a fact.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

# What is worth checking, and the words for it. Only the parts a form prints for the recipient.
CHECKED = (("primary.first_name", "primary.last_name", "your name"),
           ("spouse.first_name", "spouse.last_name", "your spouse's name"),
           ("address.street", None, "your street address"),
           ("address.city", None, "your town or city"),
           ("address.zip", None, "your ZIP code"))
_WORD = re.compile(r"[a-z0-9]+")


def _normalise(text: str) -> str:
    return " ".join(_WORD.findall((text or "").lower()))


def content_key(result) -> str:
    """What this document says, as one value: its form and every figure read from it. Two documents
    with the same key are the same form read twice — the same W-2 scanned as well as saved, say —
    which the name-and-bytes check cannot see, and which doubles a wage if it goes in twice."""
    boxes = sorted((c.path.rsplit(".", 1)[-1], repr(c.value)) for c in (getattr(result, "candidates", None) or []))
    if not boxes:
        return ""                       # nothing was read: there is nothing to call the same
    h = hashlib.sha256(getattr(result, "form_type", "").encode())
    for field, value in boxes:
        h.update(f"\n{field}={value}".encode())
    return h.hexdigest()


def page_text(pdf: Path, pdf_root=None) -> str:
    """The document's own words, from its text layer, or from OCR when it has none. `""` when
    neither is available here — the check then says nothing rather than guessing."""
    try:
        from collector.ingest import pdftext
    except ImportError:
        return ""
    try:
        page = pdftext.load_page(Path(pdf), 0)
    except Exception:
        return ""
    if page.text and page.text.strip():
        return page.text
    try:
        from .readers.ocr import OcrUnavailable, page_words
    except ImportError:
        return ""
    try:
        read = page_words(Path(pdf))
    except (OcrUnavailable, Exception):
        return ""
    lines = read.lines()
    return "\n".join(" ".join(w.text for w in lines[key]) for key in sorted(lines))


def notes(document: str, text: str, identity: dict) -> list[str]:
    """What this document does not carry that the identity file says. One sentence per thing, in
    the person's own words, naming what to do: nothing is stored, and nothing is refused."""
    if not identity or not (text or "").strip():
        return []
    haystack = _normalise(text)
    out = []
    for first, second, words in CHECKED:
        parts = [identity.get(first, ""), identity.get(second, "") if second else ""]
        wanted = _normalise(" ".join(p for p in parts if p))
        if not wanted:
            continue
        if wanted not in haystack:
            out.append(f"{words.capitalize()} as your identity file has it does not appear on "
                       f"{document}. Check the form is yours, or correct the identity file — the "
                       f"figures were read either way, and nothing about this was kept.")
    return out


def check(pdf: Path, identity: dict, pdf_root=None) -> list[str]:
    return notes(Path(pdf).name, page_text(pdf, pdf_root), identity)
