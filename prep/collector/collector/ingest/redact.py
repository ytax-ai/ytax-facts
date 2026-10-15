# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Redaction: burn personal identifiers out of the PDF (true content removal).

Design choices (deliberate, to avoid destroying data needed downstream):
  * SSN and EIN are matched ONLY in their dashed formats, so bare digit runs
    (CUSIPs, lot numbers, account fragments) survive.
  * Account/routing numbers are redacted only when a context label is present.
  * Name/address redaction is label-anchored: text following a known label on
    the same line/region is burned.
  * A per-form *policy* controls what gets redacted, enabling the K-1 two-pass
    case (pass 1 keeps the partnership EIN, which extraction needs; pass 2 burns
    it after extraction). All other forms complete in a single pass.

Mechanism (permissive stack — replaces PyMuPDF redaction annotations):
**extract-filter-rebuild**. The redacted output is a NEW PDF built only from the
surviving content: every word box is read (pdfplumber), words intersecting a
redaction region are dropped, and the remaining words are re-drawn at their
original positions (reportlab), with black boxes over the redacted regions.
Redacted text is never written into the output file, so nothing is recoverable —
strictly true content removal.

Tradeoff (stated honestly; accepted by design): non-text page content (vector graphics, images,
form rules) is NOT carried into the redacted output — the rebuilt page holds
only the surviving text layer plus the black redaction boxes. That is
privacy-conservative (an embedded image the text scan cannot see is dropped,
not passed through unredacted, which the old annotation-based path would have
done), at the cost of visual fidelity on graphical documents. A word whose
token embeds a matched identifier is dropped whole (superset redaction).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from reportlab.pdfgen import canvas as _rl_canvas

from . import pdftext
from .models import FormType

SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
EIN_RE = re.compile(r"\b\d{2}-\d{7}\b")
# An UNDASHED TIN — how payroll actually prints W-2 box a — is caught with no pattern at all: it
# sits in a region already anchored to an identity label, and the whole region burns. That is what
# keeps the module's deliberate choice intact, structurally rather than by a rule that could be
# relaxed: a bare 9-digit run with no identity label near it is a CUSIP or a lot number, and it
# survives. There is deliberately no bare-digit regex here to be reached for later.
# Account/routing only with a nearby label keyword (handled positionally below).
_ACCOUNT_LABELS = ("account no", "account number", "acct", "routing")

# Real IRS forms use U+2019, not ASCII "'". Measured across the real source PDFs: the FORMS
# carry U+2019 exclusively, and only the prose instructions mix. Every possessive label below would
# otherwise be dead on contact with a real form — `"partner’s name".find("partner's name")` is -1.
# Normalisation happens in ONE place, applied to the page and to the table alike.
_CURLY = "’"


def _norm(s: str) -> str:
    return s.replace(_CURLY, "'").lower()


# (label, term). The TERM is the point. A flat `list[Rect]` is geometry with no provenance, so
# nothing downstream can tell an employee's SSN from an employer's EIN — which is what a per-term
# policy (K-1 pass 1 keeps the partnership EIN) and identity prefill both need.

# These are the labels REAL forms carry, read off the IRS PDFs rather than guessed: box e is
# "Employee's first name and initial", and the K-1 has no "Partner's name" at all — it reads
# "F Name, address, city, state, and ZIP code for partner entered in E." The previous table looked
# for "employee's name" and "partner's name", neither of which occurs on the forms they name.
_IDENTITY_LABELS: tuple[tuple[str, str], ...] = (
    # W-2
    ("employee's social security number", "employee.ssn"),
    ("employee's first name and initial", "employee.name"),
    ("employee's name", "employee.name"),
    ("employee name", "employee.name"),
    ("employee's address", "employee.address"),
    # 1099 family
    ("recipient's name", "recipient.name"),
    ("recipient name", "recipient.name"),
    ("recipient's tin", "recipient.tin"),
    ("recipient's address", "recipient.address"),
    # Schedule K-1 (1065)
    ("partner's ssn or tin", "partner.tin"),
    ("partner's ssn", "partner.tin"),
    ("name, address, city, state, and zip code for partner", "partner.address"),
    ("partner's name", "partner.name"),
    ("partnership's employer identification number", "partnership.ein"),
    ("partnership's ein", "partnership.ein"),
    ("partnership's name, address, city, state, and zip code", "partnership.address"),
    # W-2G
    ("winner's name", "winner.name"),
    # Box 9 on the current form (Rev. 1-2026) reads `WINNER’S TIN`, and nothing here matched that
    # wording — measured on `sources/fw2g--ty2025--2026-01.pdf`, where the corpus's only TIN plant
    # sat under box 11 (a driver's-license number) and the form's actual TIN box was never tested.
    # An undashed TIN escapes SSN_RE by design, so the winner's SSN was the one identifier on this
    # form that nothing would burn. It cost nothing while a W-2G classified UNKNOWN and the
    # pipeline emitted no artifact for it; reading the form is what turned it into an exposure.
    ("winner's tin", "winner.tin"),
    ("winner's taxpayer identification no.", "winner.tin"),   # older revisions' wording
    # Boxes 11 and 12 are NOT the TIN. `iw2g` requires two forms of identification, one with a
    # photo, so these hold a driver's-licence or passport number. Calling them `winner.tin` made
    # the page carry two different values for one term, which `prefill` correctly refuses as a
    # CONFLICT — so on a filled W-2G the winner's real TIN could never be proposed. They are
    # identity and still burn: `_wanted` sends anything that is not `.ssn`/`.tin`/`.ein` to
    # `redact_pii_labels`, which every policy in this module sets.
    ("first identification no.", "winner.identification_no"),
    ("second identification no.", "winner.identification_no"),
    # Form 1040
    ("your first name and middle initial", "primary.name"),
    ("your social security number", "primary.ssn"),
    ("spouse's first name and middle initial", "spouse.name"),
    ("spouse's social security number", "spouse.ssn"),
    ("home address (number and street)", "address.street"),
    # Generic box labels, last so a more specific one above claims the column first.
    ("last name", "person.last_name"),
    ("street address", "address.street"),
    ("city or town", "address.city"),
    ("name and address", "person.address"),
)

# How far the search for a value reaches below its label. Shared with `extract.py` through
# `pdftext`: keeping a burn inside the label's own COLUMN is the same geometry the extractor
# needs to read the right box, and the two carried their own numbers, tuned independently against
# the same forms.
_VALUE_ROWS = pdftext.VALUE_ROWS
_VALUE_BAND = pdftext.VALUE_BAND

# Helvetica descent (207/1000 em): converts a pdfminer glyph-box bottom back to
# the text baseline when re-drawing surviving words at their original spots.
_DESCENT_FRAC = 0.207
_DEFAULT_SIZE = 10.0

# (x0, top, x1, bottom) in top-down page coordinates.
Rect = tuple[float, float, float, float]


@dataclass(frozen=True)
class Hit:
    """One located identifier: what it is, what it says, and where it sits.

    The type plan step 1b needs and a flat rect could never be: a caller handed rects cannot tell an
    employee's SSN from an employer's EIN, so "return what you located" would be unusable for
    prefilling an identity file. Burn rects are DERIVED from hits, which keeps locating and policy
    one decision apart.

    Deliberately carries NO confidence. It did, as a constant 0.9 that nothing ever read — a number
    which is always the same reads as evidence while being decoration, and `prefill.py` decides
    what it can vouch for by SHAPE, which is a claim that can be checked."""

    term: str
    text: str
    rect: Rect


@dataclass
class RedactionPolicy:
    redact_ssn: bool = True
    redact_ein: bool = True
    redact_pii_labels: bool = True
    redact_account_numbers: bool = True
    # Terms this pass must NOT burn, whatever else it does. The K-1 two-pass case is exactly this:
    # pass 1 keeps the partnership EIN because extraction needs it, pass 2 removes it.
    keep_terms: frozenset[str] = frozenset()


# Per-form, per-pass policies. Pass 1 runs locally before extraction; pass 2
# runs after extraction (only K-1 needs it, to burn the partnership EIN that
# pass 1 intentionally preserved).
def policy_for(form_type: FormType, pass_no: int) -> RedactionPolicy:
    if form_type is FormType.K1_1065:
        if pass_no == 1:
            # Keep the partnership EIN (Box A) for extraction; burn the rest. Now expressed as the
            # TERM rather than as "no EIN pattern", so an undashed one is kept deliberately instead
            # of by accident, and pass 2 can still remove it.
            return RedactionPolicy(redact_ein=False,
                                   keep_terms=frozenset({"partnership.ein"}))
        return RedactionPolicy(  # pass 2: only the EIN remains to remove
            redact_ssn=False, redact_pii_labels=False,
            redact_account_numbers=False, redact_ein=True,
        )
    # All other forms: single full pass.
    return RedactionPolicy()


def _match_rects(page: pdftext.PageWords, pattern: re.Pattern[str]) -> list[Rect]:
    """Word boxes whose token contains a pattern match (dashed SSN/EIN)."""
    return [(w.x0, w.top, w.x1, w.bottom) for w in page.words if pattern.search(w.text)]


def _label_value_rects(page: pdftext.PageWords, labels: tuple[str, ...]) -> list[Rect]:
    """Rects covering text to the right of any matched label on the same line."""
    rects: list[Rect] = []
    for _key, ws in page.lines().items():
        line_text = " ".join(t.text for t in ws).lower()
        for lab in labels:
            idx = line_text.find(lab)
            if idx == -1:
                continue
            # Burn everything after the label text on this line.
            consumed = 0
            cut_x = None
            for t in ws:
                consumed += len(t.text) + 1
                if consumed > idx + len(lab):
                    cut_x = t.x0
                    break
            if cut_x is not None:
                x1 = max(t.x1 for t in ws)
                y0 = min(t.top for t in ws)
                y1 = max(t.bottom for t in ws)
                rects.append((cut_x - 1, y0 - 1, x1 + 1, y1 + 1))
    return rects


def _account_rects(page: pdftext.PageWords) -> list[Rect]:
    return _label_value_rects(page, _ACCOUNT_LABELS)


def _money_labels() -> tuple[str, ...]:
    """Every declared money-box label. A row that is one is a BOX, not somebody's identity.

    Without this, the row below an identity label was burned whatever it held — and on a 1099-INT
    the row below `Recipient's TIN` is `1 Interest income 1,234.00`, so redaction destroyed the only
    figure the form carries. Trying the row below first is right; taking it unconditionally
    is not.
    """
    from .extract import FORM_FIELDS      # imported here: `extract` must not depend on `redact`
    # Each declared SPELLING is a label of its own: the abbreviated `wages, tips, other comp`
    # must be refused as identity exactly as the IRS wording is.
    return tuple(spelling for table in FORM_FIELDS.values()
                 for spellings in table.values() for spelling in spellings)


def _is_label_row(text: str) -> bool:
    """Is this row a LABEL rather than a value?

    Substring-either-way, because a real form's label wraps: the K-1's box B label breaks across
    rows, so the row holds `Partnership's name, address,` while the table holds the whole thing.
    A one-way check missed it and burned the next box's label as if it were this box's value."""
    t = _norm(text).strip(" .:")
    if not t:
        return False
    if any(lab in t for lab in _money_labels()):
        return True          # a declared money box: never a person's name or TIN
    return any(lab in t or (len(t) > 8 and t in lab) for lab, _term in _IDENTITY_LABELS)


def _whole_value(lines: dict[int, list[pdftext.Word]],
                 row: list[pdftext.Word]) -> list[pdftext.Word]:
    """Grow a column-clipped value back out to its OWN contiguous run of words.

    `rows_below` admits a word by where it STARTS, which is what lets a value be wider than the
    short label above it. It is not enough: the words a long value is made OF also start further
    right, and the ones past the label's gutter were dropped from the burn. Measured on the real
    W-2G (adversarial review, 2026-08-14): `City or town` is a 3-word label, `Faketown ZZ 00000`
    is its value, and `00000` starts past the gutter — **the ZIP stayed on the redacted page**, and
    the corpus scored the page 100% because it only asked whether the WHOLE string survived.

    The run is bounded by the same gutters everything else here is: `segments` splits a line where
    the printed form rules one box from the next, so growing to the end of the value's own segment
    cannot reach into the neighbouring box.

    STRICTLY ADDITIVE, and that is not a detail. A first version returned the segment itself, which
    on a WIDE column — one whose clipped row already spans several segments — returned LESS than it
    was given: swept across the corpus it shrank the K-1's `partner.address` burn from a full label
    row to its first four words. Narrowing a burn is the one direction this function must never
    move, so it only ever appends what continues past the clipped row's right edge.
    """
    full = lines.get(row[0].line_no)
    if not full:
        return row
    seg = next((s for s in pdftext.segments(full) if row[0] in s), None)
    if seg is None:
        return row
    right = max(w.x1 for w in row)
    return row + [w for w in seg if w.x0 > right]


def _is_box_marker(words: list[pdftext.Word]) -> bool:
    """A row that is just the form's own box lettering — `E`, `A`, `13` — is not a value.

    Real forms letter their boxes on their own line, and treating that as the value both burns the
    wrong thing and stops the search before it reaches the row that holds the real one."""
    return len(words) == 1 and len(words[0].text.strip(" .")) <= 2


def locate_identity(page: pdftext.PageWords) -> list[Hit]:
    """Find identity on a page and say WHAT each hit is.

    Two things the old label matcher could not do, and a measurement put the cost at **7% recall** —
    on the real Schedule K-1 and the real Form 1040 it burned ZERO rects, locating nothing at all:

    * **The value is not on the label's line.** Printed forms put it in the box BELOW. The old
      matcher burned "everything after the label on this line", which on a real form is nothing.
    * **The label is not what the table said.** Box e reads "Employee's first name and initial",
      which does not contain "employee's name"; and every possessive entry was ASCII where the form
      uses U+2019, so five of eight were unmatchable on any real IRS form regardless of layout.

    The burn stays inside the label's own COLUMN, bounded by the gutters either side of it. That is
    not tidiness: on a W-2 the identity band and the box 1-6 money column are the same horizontal
    band, so burning the band to catch a name destroys the wages extraction needs.
    """
    hits: list[Hit] = []
    lines = page.lines()
    for key in sorted(lines):
        line = lines[key]
        joined = _norm(" ".join(w.text for w in line))
        for label, term in _IDENTITY_LABELS:
            idx = joined.find(label)
            if idx == -1:
                continue

            column = pdftext.column_for_label(line, idx, len(label))
            if column is None:
                continue

            # 1) The rows BELOW, within the same column — tried FIRST, because that is where
            #    printed forms put the value. Membership is by where a word STARTS: a value is
            #    routinely wider than the label above it, and bounding by its right edge would
            #    silently drop exactly those.
            # Only an ADDRESS may run past one row. A name, a TIN or an EIN occupies exactly one,
            # and letting them run was a real over-burn: on the K-1 fixture `partner.name` swallowed
            # the two rows beneath it — including the partnership EIN that pass 1 must KEEP for
            # extraction. Burning more than asked is not the safe direction here; it destroys the
            # data the next pass needs.
            # Bound what is BURNED, not what is examined. Real forms interleave fragments from
            # other columns between a label and its value — on the K-1 a bare box letter "E" and a
            # neighbouring caption sit between them — so capping the rows LOOKED at stops before
            # reaching the value. Only an address may span more than one burned row; a name, a TIN
            # or an EIN occupies exactly one, which is what stopped `partner.name` from swallowing
            # the partnership EIN that pass 1 must KEEP.
            burnable = _VALUE_ROWS if "address" in term else 1
            found, taken = False, 0
            for row in pdftext.rows_below(lines, key, column, _VALUE_ROWS, _VALUE_BAND):
                if _is_box_marker(row):
                    continue
                if _is_label_row(" ".join(w.text for w in row)):
                    break               # the next box's label, not this box's value
                hits.append(_hit(term, _whole_value(lines, row)))
                found, taken = True, taken + 1
                if taken >= burnable:
                    break

            # 2) Only if the box below held nothing: the value beside the label on its own line,
            #    which is the layout `fixtures/synthetic.py` writes. This is the FALLBACK, not the
            #    first try — on a real form the text after a label is usually the label's own
            #    parenthetical ("(Do not use TIN of a disregarded entity. See instructions.)"), and
            #    taking it first burned that instead of the taxpayer's TIN one row down.
            if found:
                continue
            if column.tail and not _is_label_row(" ".join(w.text for w in column.tail)):
                hits.append(_hit(term, column.tail))
    return hits


def _hit(term: str, words: list[pdftext.Word]) -> Hit:
    return Hit(
        term=term,
        text=" ".join(w.text for w in words),
        rect=(min(w.x0 for w in words) - 1, min(w.top for w in words) - 1,
              max(w.x1 for w in words) + 1, max(w.bottom for w in words) + 1),
    )


def _wanted(term: str, policy: RedactionPolicy) -> bool:
    """Whether this policy burns this term. Per-TERM, which a regex class could never express."""
    if term in policy.keep_terms:
        return False
    if term.endswith(".ein"):
        return policy.redact_ein
    if term.endswith((".ssn", ".tin")):
        return policy.redact_ssn
    return policy.redact_pii_labels


def _intersects(w: pdftext.Word, r: Rect) -> bool:
    return not (w.x1 <= r[0] or w.x0 >= r[2] or w.bottom <= r[1] or w.top >= r[3])


def _font_for(fontname: str) -> str:
    low = fontname.lower()
    bold = "bold" in low
    italic = "italic" in low or "oblique" in low
    if bold and italic:
        return "Helvetica-BoldOblique"
    if bold:
        return "Helvetica-Bold"
    if italic:
        return "Helvetica-Oblique"
    return "Helvetica"


def redact_file(in_path: Path, out_path: Path, policy: RedactionPolicy) -> int:
    """Apply `policy` to every page; write to out_path. Returns rects burned.

    The output is rebuilt from the surviving words only (see module docstring):
    redacted content is absent from the file, not covered over.
    """
    pages = pdftext.load_pages(in_path)
    c = _rl_canvas.Canvas(str(out_path), invariant=1)
    total = 0
    for page in pages:
        rects: list[Rect] = []
        if policy.redact_ssn:
            rects.extend(_match_rects(page, SSN_RE))
        if policy.redact_ein:
            rects.extend(_match_rects(page, EIN_RE))
        # Labelled identity: located as terms, then filtered by what this pass may burn.
        rects.extend(h.rect for h in locate_identity(page) if _wanted(h.term, policy))
        if policy.redact_account_numbers:
            rects.extend(_account_rects(page))
        total += len(rects)

        c.setPageSize((page.width, page.height))
        # 1) Surviving words, re-drawn at their original positions.
        for w in page.words:
            if any(_intersects(w, r) for r in rects):
                continue  # redacted: never written to the output
            size = w.size or _DEFAULT_SIZE
            baseline = (page.height - w.bottom) + _DESCENT_FRAC * size
            c.setFont(_font_for(w.fontname), size)
            c.setFillColorRGB(0, 0, 0)
            # Trailing space: an explicit word separator in the text run, so a
            # re-parse segments the rebuilt words exactly like the original's
            # space characters did (positions are absolute; the space itself
            # advances nothing).
            c.drawString(w.x0, baseline, w.text + " ")
        # 2) Black boxes marking the redacted regions (visual indication only —
        #    the underlying content was dropped above, not merely covered).
        c.setFillColorRGB(0, 0, 0)
        for r in rects:
            c.rect(r[0], page.height - r[3], r[2] - r[0], r[3] - r[1],
                   fill=1, stroke=0)
        c.showPage()
    c.save()
    return total
