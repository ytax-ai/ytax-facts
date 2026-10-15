# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Permissive-licensed PDF text access shared by the ingest modules.

Replaces the PyMuPDF (`fitz`, copyleft-licensed) text APIs with `pdfplumber` (MIT, over
pdfminer.six MIT). The rest of the pipeline consumes only this module's
:class:`Word` / :class:`PageWords` shapes, so the extraction backend is a single
swap point.

Geometry convention: TOP-DOWN page coordinates (x0, top, x1, bottom), the same
convention the old fitz word tuples used, so the label/value walking logic in
``extract.py`` / ``redact.py`` carries over unchanged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

# Words whose vertical centers are within this many points are the same line.
_LINE_TOLERANCE = 2.0


@dataclass(frozen=True)
class Word:
    """One extracted word with its bounding box (top-down coords)."""

    x0: float
    top: float
    x1: float
    bottom: float
    text: str
    size: float          # font size in points (0.0 if unknown)
    fontname: str        # producer font name ("" if unknown)
    line_no: int         # index of the visual line this word belongs to


@dataclass
class PageWords:
    """A page's words (line-grouped) + its plain text and dimensions."""

    index: int           # 0-based page index
    width: float
    height: float
    text: str
    words: list[Word] = field(default_factory=list)

    @property
    def number(self) -> int:
        """0-based page index (mirrors the old fitz ``page.number``)."""
        return self.index

    def lines(self) -> dict[int, list[Word]]:
        """line_no -> words on that line, sorted left-to-right."""
        out: dict[int, list[Word]] = {}
        for w in self.words:
            out.setdefault(w.line_no, []).append(w)
        for ws in out.values():
            ws.sort(key=lambda t: t.x0)
        return out


def _group_lines(raw: list[dict]) -> list[Word]:
    """Assign a line number to each raw pdfplumber word by vertical clustering.

    Compared to the PREVIOUS word's midpoint, not to a fixed anchor set once per line.
    Anchoring on the first word never moved it, so a caption sharing its printed row with an
    unrelated column could drift past the tolerance from that first word even though every
    ADJACENT pair of words was well within it — measured on the real synthetic 1099-SA, where
    `RECIPIENT'S TIN` (mid 203.05) anchored the row, `3` (mid 205.05) joined at exactly the 2.0pt
    edge, and `Distribution`/`code` (mid 205.2) split onto a phantom second line at 2.15pt from
    the ANCHOR though only 0.15pt from `3` itself — one printed caption read as two, on a form
    that never wrapped it. The sort below is by midpoint, so this walk is monotone: merging two
    genuinely distinct ruled rows would need a run of intermediate baselines each within
    `_LINE_TOLERANCE` of the next, spanning a whole row's height, which a ruled form does not
    print (see `test_pdftext_line_grouping.py`).
    """
    ordered = sorted(raw, key=lambda w: ((w["top"] + w["bottom"]) / 2, w["x0"]))
    words: list[Word] = []
    line_no = -1
    current_mid: float | None = None
    for w in ordered:
        mid = (w["top"] + w["bottom"]) / 2
        if current_mid is None or abs(mid - current_mid) > _LINE_TOLERANCE:
            line_no += 1
        current_mid = mid           # move the anchor every word, not once per line
        words.append(Word(
            x0=float(w["x0"]), top=float(w["top"]),
            x1=float(w["x1"]), bottom=float(w["bottom"]),
            text=str(w["text"]),
            size=float(w.get("size") or 0.0),
            fontname=str(w.get("fontname") or ""),
            line_no=line_no,
        ))
    return words


# --- box geometry ------------------------------------------------------------
# Shared by `extract.py` and `redact.py`. Both learned the same lesson from opposite ends:
# the extractor read the NEXT BOX'S NUMBER as a value, and the redactor located nothing at
# all on a real form. The cause was one assumption in two places — *the value follows its
# label on the same line* — so the correction belongs in one place too, and this module already
# declares itself the owner of the geometry convention.

# What lives here is GEOMETRY. What counts as a label, and what to do with the words found, stays
# with each caller: the extractor wants one value, the redactor wants a region to burn and may take
# several rows for an address. Sharing the policy would have merged two things that only look alike.

# A gap wider than this separates one box from the next. Printed forms rule their boxes apart, and
# the gutter is what the eye reads as the boundary.
GUTTER = 12.0
# How far a value may sit below its label: rows, and points. ONE pair, used by both callers.
# They previously carried their own (2 rows / 30pt in the extractor, 3 / 34 in the redactor), tuned
# independently against the same forms — a disagreement nobody had argued for. Three rows because a
# real form interleaves fragments from other columns between a label and its value (a bare box
# letter on its own row), and 34 points because that is the largest label-to-value gap measured on
# the real IRS pages in the corpus. A caller that wants only the first row simply stops after it.
VALUE_ROWS = 3
VALUE_BAND = 34.0


# A STAMP is not a box. syndoc's synthetic pages carry a diagonal `SYNTHETIC — DEV/DEMO ONLY`
# watermark whose glyphs land as single-letter words at 42.7pt beside 6pt labels; a payer's `COPY B`
# stamp is the same shape. Measured on the profile-C 1099-R: the `O` at x=490 on box 7's own line
# would otherwise be the next segment — bounding the box short of its value — or the value itself.
# A word this many times larger than the label it stands beside is decoration: it bounds nothing
# and is never read. Labels and values on every real page in the corpus sit within 2× of each other.
DECORATION_RATIO = 4.0


def is_decoration(word: "Word", label_size: float) -> bool:
    return label_size > 0 and word.size >= DECORATION_RATIO * label_size


@dataclass(frozen=True)
class Column:
    """The box a label owns: how far its value may sit to either side, and how far down.

    `tail` is what follows the label on its OWN line, inside the column — the layout the synthetic
    fixtures write. On a real form it is usually the label's own parenthetical instead, which is why
    callers try the rows below first and treat this as the fallback.

    `right` is how far a caller may look; `narrow_right` is the label's OWN gutter (or the next
    box's header), which is where `right` stood before The two differ only for a caller that
    asked to widen (`page_width`), and what lies between them is read under stricter rules — see
    `extract._value_after_label`. `size` is the label's font size, for `is_decoration`.
    """

    left: float
    right: float
    floor: float            # bottom of the label's line: where "below" starts
    tail: list["Word"]
    narrow_right: float = -1.0
    size: float = 0.0

    def own_bound(self) -> float:
        return self.right if self.narrow_right < 0 else self.narrow_right


def segments(line: list["Word"], gutter: float = GUTTER) -> list[list["Word"]]:
    """Split a line into boxes at its gutters, left to right."""
    out: list[list[Word]] = []
    for w in line:
        if out and w.x0 - out[-1][-1].x1 <= gutter:
            out[-1].append(w)
        else:
            out.append([w])
    return out


# A bare box NUMBER as a printed form sets it: `1`, `6a`, `12b`. One pattern, shared with the
# extractor's clipped-header guard, so "what a box number looks like" has one answer.
BOX_NUMBER_RE = re.compile(r"^\d{1,2}[a-f]?$")


def _next_box_header(column: list["Word"], first_after: int) -> "Word | None":
    """The word where a NEIGHBOURING box's header begins inside this segment, if one does.

    `segments` splits a line where the printed gutter is wider than `GUTTER`. The real Schedule K-1
    rules Part II from Part III with less than that: `Partner's SSN or TIN (... See instructions.)`
    ends 11.99pt before `6b Qualified dividends` begins, and the address caption 10.4pt before `6c
    Dividend equivalents`. So the gutter rule alone called each pair ONE box, the TIN label owned a
    column to x=406, and the row beneath it -- the TIN and box 6b's figure -- burned whole.

    The form says where the next box starts in its own words: a bare box number followed by a
    CAPTION -- a capitalised word, as every printed header sets one. Only that shape counts. A box
    LETTER (`entered in E.` is the K-1's own caption, and `E` its last word), a parenthesised number
    (`(2) Last name` on the 1040's dependents table), a trailing number with nothing after it, and
    a cross-reference in running text (`total of boxes 3 and 7`, `from box 5 of your`, both found
    by the corpus sweep on instruction pages) are all things a caption legitimately contains, and
    trimming at any of them would NARROW a burn -- the direction `redact._whole_value` exists to
    forbid. Words inside the matched label itself are never candidates: `1 Wages` begins with one.
    """
    for i in range(first_after, len(column) - 1):
        if BOX_NUMBER_RE.match(column[i].text.strip()) and column[i + 1].text[:1].isupper():
            return column[i]
    return None


def column_for_label(line: list["Word"], char_index: int, label_len: int,
                     gutter: float = GUTTER, *, page_width: float | None = None) -> Column | None:
    """The column owned by the label found at `char_index` in this line's joined text.

    Bounding by the gutters is what keeps a caller inside its own box. On a W-2 the identity band
    and the box 1-6 money column are the SAME horizontal band, so a redactor that burns the band to
    catch a name destroys the wages, and an extractor that reads along the line picks up the
    neighbouring box's number.

    The gutter is not the only boundary the form prints. Where a neighbouring box's HEADER sits
    inside the label's segment -- closer than the gutter, as the K-1 sets Part III against Part II
    -- the column ends there instead (`_next_box_header`).

    `page_width` asks for the WIDER bound a payer-printed statement needs: the profile-C
    1099-R prints `1 Gross distribution` at x=319-379 and its amount right-aligned at x=492 on the
    row below, 113pt past the label's gutter, and every box read EMPTY. With it, `right` runs to
    the segment that follows the label on its own line (the next box's header, on the real
    1099-R `OMB No.`; on the real K-1 `14 Self-employment earnings`), else to the page's edge; the
    label's own gutter is kept as `narrow_right`, because what lies past it is read under stricter
    rules by the caller. Without it -- the redactor -- nothing changes: a burn must never widen on
    a rule written for reading.

    Decoration (`is_decoration`) neither bounds the column nor joins its tail.
    """
    consumed, anchor = 0, None
    for w in line:
        if consumed + len(w.text) > char_index:
            anchor = w
            break
        consumed += len(w.text) + 1
    if anchor is None:
        return None
    words = [w for w in line if not is_decoration(w, anchor.size)]
    segs = segments(words, gutter)
    seg_idx = next((i for i, s in enumerate(segs) if anchor in s), None)
    if seg_idx is None:
        return None
    column = segs[seg_idx]

    # The label's OWN printed text can straddle a segment gutter. On the real Schedule K-1
    # (Form 1041), box 1 and box 6 print their bare number 12.85pt from their caption — a hair
    # past `gutter` — so `segments` splits the number from words that are still part of the
    # SAME declared label (found reading the real pinned form: box 6
    # matched only its own "6", and the value search then walked into "7 Net rental real estate
    # income" one row down as though "7" were box 6's own figure). Grow the column through every
    # FOLLOWING segment that still holds a word inside the label's own matched span — never
    # further, so a genuinely different neighbour label sharing the line is untouched.
    label_end = char_index + label_len
    during, walked = set(), 0
    for w in line:
        start = walked
        walked += len(w.text) + 1
        if start < label_end and not is_decoration(w, anchor.size):
            during.add(id(w))
    while seg_idx + 1 < len(segs) and any(id(w) in during for w in segs[seg_idx + 1]):
        seg_idx += 1
        column = column + segs[seg_idx]

    end, consumed, after = label_end, 0, []
    for w in line:                      # the words that follow the matched label's text
        start = consumed
        consumed += len(w.text) + 1
        if start >= end and not is_decoration(w, anchor.size):
            after.append(w)
    narrow = column[-1].x1 + gutter
    first_after = next((i for i, w in enumerate(column) if w in after), len(column))
    header = _next_box_header(column, first_after)
    if header is not None:
        narrow = header.x0 - 1.0
    right = narrow
    if page_width is not None and header is None:
        following = [s for s in segs if s[0].x0 > column[-1].x1]
        right = max(narrow, following[0][0].x0 - gutter / 2 if following else page_width)
    tail = [w for w in after if w.text.strip() and w.x0 < right]
    return Column(left=column[0].x0 - 1.0, right=right,
                  floor=max(w.bottom for w in line), tail=tail,
                  narrow_right=narrow, size=anchor.size)


def rows_below(lines: dict[int, list["Word"]], line_no: int, column: Column,
               max_rows: int, band: float):
    """Yield candidate value rows beneath a label, nearest first, inside its column.

    Membership is by where a word STARTS, never by where it ends. A value is routinely WIDER than
    the label above it — a short label in 6pt over a figure in 10pt — and bounding by its right edge
    silently drops exactly those, which is the silent-zero failure both callers exist to prevent.
    Starting inside the column is enough to exclude the neighbour, whose words begin past the gutter
    by construction.

    `band` bounds the search vertically. A row cap alone is not a bound: on a sparse page the "next
    rows" can be most of a page away, and one caller returned the word "Form" — off the page title,
    200pt down — as a wages value before this existed.

    The band is measured from the last row YIELDED, not from the label, so a value that legitimately
    runs on — a street line then a city/state/ZIP line — is not cut off by its own length. A caller
    that stops after the first row is unaffected.

    The caller decides everything else: rows are yielded, not consumed.
    """
    floor = column.floor
    for key in [k for k in sorted(lines) if k > line_no][:max_rows]:
        row = [w for w in lines[key]
               if column.left <= w.x0 <= column.right and w.text.strip()
               and w.top - floor <= band and not is_decoration(w, column.size)]
        if row:
            yield row
            floor = max(w.bottom for w in row)


def page_count(path: Path) -> int:
    with pdfplumber.open(path) as pdf:
        return len(pdf.pages)


def page_text(path: Path, index: int) -> str:
    """Plain text of one page ("" when the page has no text layer)."""
    with pdfplumber.open(path) as pdf:
        if index >= len(pdf.pages):
            return ""
        return pdf.pages[index].extract_text() or ""


def all_text(path: Path) -> str:
    """Newline-joined plain text of every page."""
    with pdfplumber.open(path) as pdf:
        return "\n".join(pg.extract_text() or "" for pg in pdf.pages)


def load_page(path: Path, index: int) -> PageWords:
    """One page's line-grouped words + text."""
    with pdfplumber.open(path) as pdf:
        pg = pdf.pages[index]
        raw = pg.extract_words(extra_attrs=["size", "fontname"])
        return PageWords(
            index=index, width=float(pg.width), height=float(pg.height),
            text=pg.extract_text() or "", words=_group_lines(raw),
        )


def load_pages(path: Path) -> list[PageWords]:
    """Every page's line-grouped words + text (single file open)."""
    pages: list[PageWords] = []
    with pdfplumber.open(path) as pdf:
        for i, pg in enumerate(pdf.pages):
            raw = pg.extract_words(extra_attrs=["size", "fontname"])
            pages.append(PageWords(
                index=i, width=float(pg.width), height=float(pg.height),
                text=pg.extract_text() or "", words=_group_lines(raw),
            ))
    return pages
