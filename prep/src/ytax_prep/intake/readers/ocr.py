# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""OCR reader tier: a page with no text layer, rendered and read by RapidOCR (PP-OCR
models on ONNX Runtime), fed into the same word geometry `collector.ingest.extract` already reads
an exact text layer through.

Ported from the 2026-09-10 spike (`spike-docling/scanrun.py`, mode `rapid-geom`): render at 200 dpi
with `pypdfium2`, run RapidOCR, split each recognised line into words proportionally across its
box, scale pixels to PDF points, and hand the result to `pdftext._group_lines` — the same shape
`pdftext.load_page` returns for a digital page, so every downstream reader (`extract_declared`,
the register-driven field reader) is unchanged.

Nothing here imports `pdfplumber`/`pypdfium2`/`rapidocr` at module scope: `normalise_line` is pure
text and must import cleanly under plain `python3` with none of those installed (only the
collector venv carries them). The heavy imports happen inside `page_words`, which is also the
only place `OcrUnavailable` can be raised from.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # never imported at runtime — see the module docstring
    from collector.ingest import pdftext

# The three regexes are the spike's own fixes for what RapidOCR does to a box caption, unchanged:
#   - `2 a Taxable amount` -> `2a Taxable amount`     (OCR splits a box LETTER off its number)
#   - `3Social security wages` -> `3 Social security wages`   (OCR drops the space after a NUMBER)
#   - `code(s)· IRA` -> `code(s) · IRA`               (a separator glued onto the word before it)
# Order matters: the join must run before the split, or "2 a" would first be split into "2" + " a"
# and then joined right back — same-looking, but for the wrong reason, and fragile to reorder.

# The optional box-letter in the split pattern is POSSESSIVE (`[a-f]?+`, not `[a-f]?`): a plain
# `?` lets the engine backtrack off the letter it just joined on when the lookahead fails against
# the space that correctly follows it ("2a Taxable"), and then re-match with the digit ALONE —
# finding the box letter itself as the "next letter" needing a space inserted before it, undoing
# the join the first pattern just made. Possessive forbids that backtrack.
_JOIN_SPLIT_LETTER_RE = re.compile(r"^(\d{1,2}) ([a-f])(?=\s|[A-Z])")
_SPLIT_GLUED_NUMBER_RE = re.compile(r"^(\d{1,2}[a-f]?+)(?=[A-Za-z])")
_SPLIT_GLUED_SEPARATOR_RE = re.compile(r"(?<=[A-Za-z)])([·•])")


def normalise_line(text: str) -> str:
    """One OCR'd line of text -> the text the box geometry expects (see the module docstring)."""
    text = _JOIN_SPLIT_LETTER_RE.sub(r"\1\2", text)
    text = _SPLIT_GLUED_NUMBER_RE.sub(r"\1 ", text)
    text = _SPLIT_GLUED_SEPARATOR_RE.sub(r" \1", text)
    return text


class OcrUnavailable(RuntimeError):
    """`rapidocr` (or the page renderer, `pypdfium2`) is not importable in this interpreter."""


def _words_from_ocr(boxes: Any, texts: Any, img_w: int, img_h: int,
                    w_pt: float, h_pt: float) -> list[dict]:
    """OCR boxes (pixel corners) -> raw `pdftext._group_lines` word dicts, in PDF points.

    RapidOCR returns one box per recognised LINE, not per word; the geometry wants words, so each
    line is split on whitespace and its width divided across the parts proportionally to their
    character count (the spike's own approximation — good enough for the gutter/column logic,
    which only needs left edges to separate boxes, not per-glyph precision).
    """
    sx, sy = w_pt / img_w, h_pt / img_h
    raw: list[dict] = []
    for box, text in zip(boxes, texts):
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        x0, x1 = min(xs) * sx, max(xs) * sx
        top, bottom = min(ys) * sy, max(ys) * sy
        parts = normalise_line(str(text).strip()).split()
        if not parts:
            continue
        total = sum(len(p) for p in parts) + (len(parts) - 1)
        cur = x0
        for part in parts:
            width = (x1 - x0) * (len(part) + 0.5) / max(total, 1)
            raw.append(dict(x0=cur, x1=min(cur + width, x1), top=top, bottom=bottom,
                            text=part, size=(bottom - top) * 0.8, fontname="ocr"))
            cur += width + (x1 - x0) / max(total, 1) * 0.5
    return raw


def page_words(pdf: Path, dpi: int = 200, engine: Any = None) -> "pdftext.PageWords":
    """Page 1 of `pdf`, rendered at `dpi` and read by OCR, as a `pdftext.PageWords` — the same
    shape a digital page's text layer produces, so every existing reader works unchanged.

    `engine` is an object callable as `engine(image) -> result`, with `.boxes` and `.txts`
    attributes on the result (RapidOCR's own call shape) — a test's fake engine takes this seat, so
    tests do not have to run the real OCR models to exercise the geometry plumbing. `None` builds a
    real `rapidocr.RapidOCR()`.
    """
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise OcrUnavailable(f"page render unavailable: {exc}") from exc

    if engine is None:
        try:
            from rapidocr import RapidOCR
        except ImportError as exc:
            raise OcrUnavailable(f"rapidocr not importable: {exc}") from exc
        engine = RapidOCR()

    from collector.ingest import pdftext

    with pdfium.PdfDocument(str(pdf)) as doc:
        page = doc[0]
        w_pt, h_pt = page.get_size()
        image = page.render(scale=dpi / 72).to_pil().convert("RGB")
        page.close()

    result = engine(image)
    boxes = result.boxes if result.boxes is not None else []
    texts = result.txts if result.boxes is not None else []

    raw = _words_from_ocr(boxes, texts, image.width, image.height, w_pt, h_pt)
    words = pdftext._group_lines(raw)
    return pdftext.PageWords(index=0, width=w_pt, height=h_pt,
                             text=" ".join(w.text for w in words), words=words)
