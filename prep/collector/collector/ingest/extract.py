# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Conservative extraction of labeled values into the neutral IR.

Philosophy (matches the intake's conservatism): capture high-confidence labeled
values, keep the raw text in the IR so gaps can be filled later, and DO NOT guess
on layout-dependent tabular data (e.g. 1099-B lots) — flag it for assisted
extraction instead.

Coverage status:
  * W-2 — implemented as the worked example (a labeled-box extractor).
  * Other forms — classification + redaction policy exist, but their extraction
    tables are an explicit extension point. Each added form is a new entry in
    EXTRACTORS plus a label map; the IR shape and the pipeline do not change.

Each extractor returns a list[ExtractedField]. Extraction is positional/label
based using pdfplumber word boxes (via :mod:`.pdftext` — the permissive stack),
so every field carries a SourceRegion (used by a downstream
reconciliation view to crop the source).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from . import pdftext
from .models import (
    ExtractedDocument,
    ExtractedField,
    FieldOutcome,
    FieldReport,
    FormType,
    SourceRegion,
    parse_money_cents,
)

Extractor = Callable[[pdftext.PageWords], list[ExtractedField]]

# How far the search for a value reaches below its label. Shared with `redact.py` through
# `pdftext` — the two used to disagree (2 rows / 30pt here, 3 / 34 there) by accident rather
# than by argument, and the numbers were tuned independently against the same forms.
_VALUE_ROWS = pdftext.VALUE_ROWS
_VALUE_BAND = pdftext.VALUE_BAND


# Captions the extractor KNOWS as another box's and never reads: a value search must tell a
# value from them exactly as it does from a declared label, but they map to no fact. The 1099-R's
# `2b Taxable amount not determined / Total distribution` prints two checkboxes on one line, and
# without this the second caption was read as the first box's value, `Total`, on every layout.
NEIGHBOUR_LABELS = ("total distribution",)

# W-2 box 15's caption, `15 State  Employer's state ID number` (s-state-from-w2). Kept apart from
# `FORM_FIELDS[W2]` on purpose: box 15 fills no `w2s[]` field (that table is locked to
# `W2_LABEL_TO_FIELD`), it only lets the intake page PROPOSE the root residence-state answer. Each
# spelling starts at `State` so the box's column starts where the two-letter state prints; only a
# two-letter state is ever taken from the box, never the employer's state ID beside it. Goes to the
# dictionary's `boxes.tsv` with the rest of this module's spellings.
W2_BOX15_STATE_LABELS = ("state employer's state id number", "state employer's state id no")


def _all_labels() -> list[str]:
    """Every declared label — EACH SPELLING its own label — plus the neighbour captions, so
    a value search can tell a value from the NEXT box's label."""
    return [spelling.lower()
            for table in FORM_FIELDS.values() for spellings in table.values() for spelling in spellings
            ] + list(NEIGHBOUR_LABELS)


# A printed box carries its own CURRENCY MARK, and it is chrome, not a value. Measured on the real
# `fw2g` Copy A: the row under `1 Reportable winnings` is a lone `$` sitting in box 1's own column,
# and the row under `4 Federal income tax withheld` is another. Before this, both boxes came back
# `FOUND` with the value `"$"` — unparseable, confidence 0.7. That is wrong in BOTH directions at
# once: a blank box reported as read, and a filled box's real figure never looked for. Neither
# reconstructed 1099 page could produce it, because we drew those and did not draw a `$`.
_CURRENCY_CHROME = {"$"}

# The shape of a BOX HEADER on an information return: a box number, then words. `_all_labels` can
# only recognise the boxes we DECLARED, so on a real form every neighbouring box is invisible to it
# — and skipping past a chrome row without this walks straight into one. On the pristine W-2G the
# row under box 4's `$` is `6 Race`, and `parse_money_cents("6")` is 600: #113 arriving from a new
# direction, a wrong figure with nothing refusing.
_BOX_HEADER_RE = re.compile(r"^\d{1,2}[a-f]?\s+[a-z]")

# What the column clip is allowed to have removed for `_is_clipped_box_header` to speak: a box
# NUMBER, and nothing else. See that function.
_CLIPPED_NUMBER_RE = pdftext.BOX_NUMBER_RE      # one answer to "what is a box number"


def _is_chrome(token: pdftext.Word) -> bool:
    """Chrome is a printed mark that is not a value: a box's own `$`, and any
    token with no letter or digit in it -- the `·` syndoc prints between a distribution code and
    its IRA mark, the `—` a payer prints in a blank box, a bare `/`. None of these was ever a
    figure; each used to come back FOUND at confidence 0.7 and be refused downstream."""
    text = token.text.strip()
    return text in _CURRENCY_CHROME or not any(ch.isalnum() for ch in text)


# What a box HOLDS. Every box was money until the 1099-R: box 7 holds a one- or two-character
# code (`7`, `G`, `4G`) and the IRA/SEP/SIMPLE and 2b boxes hold a mark. The kind decides two things:
# what a token must look like to be read from BEYOND the label's own gutter, and downstream, what
# the client carries (a text code, a boolean) instead of integer cents.
MONEY, CODE, CHECK = "money", "code", "check"
FIELD_KINDS = {
    "box7_distribution_code": CODE,
    "box2b_taxable_amount_not_determined": CHECK,
    "box7b_ira_sep_simple": CHECK,
    # 1099-SA box 3 is a code too, the same treatment as the 1099-R's box 7 — `1`, never
    # 100 cents. This layer's own `value_shaped` check stays the loose one- or two-character shape
    # (it only gates the widened-zone search, which this box never needs); the client's tighter
    # check against `hsa_distribution.schema.json`'s enum (1-6, unlike the 1099-R's open pattern)
    # is in `ytax_prep.client.documents`.
    "box3_distribution_code": CODE,
    # Form 1099-OID: the one mark the form carries. A checked box is refused downstream by name
    # (Form 8938 is not covered), so it has to be READ, not presumed unchecked.
    "fatca_filing_requirement": CHECK,
    # Form 1099-B box 7: a mark, refused downstream by name when checked — so it is READ.
    "box7_loss_not_allowed": CHECK,
}
# `r1099.schema.json`'s own pattern for `distribution_code`; the service-side test locks the two.
CODE_RE = re.compile(r"^[0-9A-Z]{1,2}$")
# A checkbox mark, as pages print one: syndoc's `[X]`, a bare `X`, the ballot glyphs.
CHECK_MARKS = frozenset({"x", "[x]", "☒", "☑", "✓", "✔"})


def value_shaped(kind: str, text: str) -> bool:
    text = text.strip()
    if kind == CODE:
        return CODE_RE.match(text.upper()) is not None
    if kind == CHECK:
        return text.lower() in CHECK_MARKS
    return parse_money_cents(text) is not None


_BOX_NUMBER_PREFIX_RE = re.compile(r"^\d{1,2}[a-z]?\s*$")


def _inside_a_longer_label(joined: str, idx: int, target: str, known: list[str]) -> bool:
    """Is the match of `target` at `idx` part of a LONGER known label printed on this line — one
    that adds WORDS to it (`bond premium` inside `bond premium on treasury obligations`, `total
    distribution` inside `your percentage of total distribution`)? A label that adds only a box
    number (`4 federal income tax withheld`), finishes a word the match cut short (`comp` ->
    `compensation`) or adds only a parenthetical (`(loss)`) is the same caption, not another box's.

    The caller skips the WHOLE LINE on the first match that sits inside a longer label, so a bare
    caption printed AFTER a longer one on the same line would be skipped with it. The IRS layouts
    measured print the shorter caption first (1099-INT `11 Bond premium` beside `10 Market
    discount`, above boxes 12 and 13), which is what the layout test holds."""
    for label in known:
        at = label.find(target)
        if len(label) <= len(target) or at == -1:
            continue
        before, after = label[:at], label[at + len(target):]
        if not after.strip() and (not before.strip() or _BOX_NUMBER_PREFIX_RE.match(before)):
            continue                          # the same caption with its box number
        if after and (not after[0].isspace() or after.strip().startswith("(")):
            continue                          # the same word cut short (`comp`), or its `(loss)`
        start = joined.find(label)
        while start != -1:
            if start <= idx and idx + len(target) <= start + len(label):
                return True
            start = joined.find(label, start + 1)
    return False


def _leads_with_label(text: str, known: list[str]) -> bool:
    """Does this text BEGIN with another box's label or a box header? The same-line tail is
    vetoed on this (a value may be followed by a neighbour's label; it cannot be preceded by one)."""
    low = text.strip().lower()
    return any(low.startswith(lab) for lab in known) or _BOX_HEADER_RE.match(low) is not None


def _header_shaped(row: list[pdftext.Word]) -> bool:
    """Is this row a box HEADER -- `6 Race` -- once its LEADING chrome is off?

    Leading only, and that is the whole point. The case that settled it is `$ 6 Race`: the box's own
    `$` shares the row with the next header, so chrome had to come off before the pattern could
    see the number. But a distribution code row prints `1 · IRA [X]`: strip EVERY chrome token
    and it reads `1 ira [x]`, header-shaped, and box 7 of every IRA layout came back EMPTY. The
    `·` between the number and the word is what says the number is a VALUE with a separator after
    it, and a header never prints one there."""
    tokens = list(row)
    while tokens and _is_chrome(tokens[0]):
        tokens = tokens[1:]
    return _BOX_HEADER_RE.match(" ".join(t.text for t in tokens).lower()) is not None


def _under_foreign_header(lines: dict[int, list[pdftext.Word]], candidate: pdftext.Word,
                          column: pdftext.Column, known: list[str]) -> bool:
    """Does a box header stand ABOVE this candidate, in the widened zone, at or left of it?

    The widening past a label's own gutter reads into space the form did not rule as the
    label's box, and on the real Schedule K-1 that space is the right-hand column of Part III:
    `2 Net rental real estate income` is alone on its line, so its column would run to the page
    edge, and the row beneath it holds box 14's figure -- self-employment earnings, filled on most
    partners' K-1s while box 2 is blank on most. A figure is a figure; what says whose it is, is
    the header printed above it. A header-shaped segment (or a declared label) starting past the
    label's own gutter and no further right than the candidate claims the candidate.
    """
    zone_left = column.own_bound() - pdftext.GUTTER
    for key in sorted(lines):
        line = [w for w in lines[key] if not pdftext.is_decoration(w, column.size)]
        if not line or line[0].top >= candidate.top:
            continue
        for seg in pdftext.segments(line):
            if not (zone_left <= seg[0].x0 <= candidate.x0 + pdftext.GUTTER):
                continue
            text = " ".join(t.text for t in seg).lower()
            if _BOX_HEADER_RE.match(text) or any(text.startswith(lab) for lab in known):
                return True
    return False


def _is_next_boxs_label(text: str, known: list[str]) -> bool:
    low = text.strip().lower()
    return any(lab in low for lab in known) or _BOX_HEADER_RE.match(low) is not None


def _is_clipped_box_header(lines: dict[int, list[pdftext.Word]],
                           row: list[pdftext.Word]) -> bool:
    """Is this row a box header whose NUMBER the column clip removed?

    `rows_below` admits a word by where it starts, inside the label's own column — which is what
    keeps a value from being read out of the neighbouring box. On the real Schedule K-1 that clip
    hides the very thing `_BOX_HEADER_RE` looks for. Box 5's label owns `x∈[317.5, 394.6]`; the row
    beneath it is `6a Ordinary dividends`, whose `6a` starts at **x=316.4** — 1.1pt further left,
    because a two-character box number is set wider than a one-character one. So the row that
    reached the guard was `Ordinary dividends`, with no leading number to match, and the pristine
    form returned **box 5 = `"Ordinary"`, FOUND**: a blank box reported as read, the same failure
    the W-2G's `$` chrome produced reached by a different route.

    The fix widens what the guard SEES, never what the extractor READS. The row is grown back to the
    printed box it was sliced out of — `segments` splits a line at its gutters, which is where the
    form itself rules one box from the next, the same bound `redact._whole_value` uses — and only
    the box-header SHAPE is tested against it. The known-label test stays on the clipped row: it
    matches anywhere in a string, and a K-1 line can span half the page in one segment.

    ⚠ ONLY A BOX NUMBER MAY HAVE BEEN CLIPPED, and that bound is the whole difference between this
    guard and a guess. Asking merely whether the SEGMENT starts header-shaped vetoes a row whose
    clipped-off prefix is a WHOLE neighbouring box: put `6b Qualified` entirely left of the column
    and a real figure first inside it, and the segment reads `6b qualified 48,250.00` — header
    shaped, so the box's own value is thrown away and a filled box reports EMPTY. That is the
    mirror-image failure of the one this fixes, and it is reachable: constructed by adversarial
    review, 2026-08-14 (case J). So the prefix the clip removed must be a bare box number — the
    thing whose absence made the plain guard blind — and anything more means the row genuinely
    belongs to a neighbour we were never reading anyway.

    Chrome comes off first here for the same reason it does at the call site: a segment beginning
    with a `$` cannot match a pattern anchored on a box number.
    """
    full = lines.get(row[0].line_no)
    if not full:
        return False
    seg = next((s for s in pdftext.segments(full) if row[0] in s), None)
    if seg is None or seg == row:
        return False        # nothing was clipped: the plain guard already saw this row
    clipped = " ".join(t.text for t in seg if t.x0 < row[0].x0).strip().lower()
    if not _CLIPPED_NUMBER_RE.match(clipped):
        return False        # a whole neighbouring box, not a severed box number
    text = " ".join(t.text for t in seg if not _is_chrome(t)).strip().lower()
    return _BOX_HEADER_RE.match(text) is not None


def _value_after_label(page: pdftext.PageWords, label_words: list[str],
                       kind: str = MONEY,
                       known: list[str] | None = None) -> tuple[ExtractedField | None, FieldOutcome]:
    """Find a label and return its box's value — from the same line, or the row BELOW it.

    `label_words` is the field's declared SPELLINGS, each a whole label: the IRS form's
    wording first, then what payroll layouts print instead. A line is searched for each in turn,
    so the first spelling on the page wins and a form that abbreviates `1 Wages, tips, other
    compensation` to `1 Wages, tips, other comp.` (syndoc's profile-C; the ADP-style Copy B) reads
    its box 1 rather than reporting it NOT_LOCATED beside a box 3 it read fine. A spelling that is a
    PREFIX of the printed word is safe: `column_for_label` counts the word that carries the end of
    the match as the label's own, so `comp` against `compensation` never hands `compensation` back
    as the value.

    Returns `(field, outcome)`. The outcome distinguishes *the label is not on this page* from
    *the label is here and its box is blank*. A blank box and an unread box are opposite facts —
    one says the taxpayer had no federal withholding, the other says we could not read it — and only
    the second may not be treated as zero.

    THE VALUE BELONGS TO THE LABEL'S COLUMN, not merely to its line. Taking the next token on
    the line was wrong on any form that puts two boxes side by side, which the printed W-2 does:
    the label row reads `1 Wages, tips, other compensation   2 Federal income tax withheld`, so the
    token after box 1's label is `2` — **the next box's number**. It parses as money, so box 1 was
    returned as $2.00 at confidence 0.9, and boxes 2/4/6, being last on their line, reported EMPTY
    and crossed as an explicit 0. A real-layout W-2 produced $2.00 of wages and no withholding with
    nothing refusing.

    So the search is bounded by the gutters either side of the label, and a candidate that is itself
    a declared label is rejected rather than read as a value.

    BEYOND THE LABEL'S OWN GUTTER. A payer-printed statement right-aligns its amounts: on
    the profile-C 1099-R every value sits 113pt past its label's gutter, and every box read EMPTY.
    `column_for_label(page_width=...)` now widens the column to the next segment on the label's
    line, else to the page's edge -- and a token found only in that widened zone is read under two
    rules the label's own column never needed, both measured on real pages before this shipped:
    it must be `value_shaped` for the box's `kind` (the real 1099-R's title text `IRAs,` lies
    below-right of box 2a and is not money), and no box header may stand above it in that zone
    (`_under_foreign_header`: the real K-1's box 14 figure lies below-right of box 2).
    """
    # THE MOST SPECIFIC SPELLING FIRST, ACROSS THE WHOLE PAGE (found in a demo, 2026-09-22): a
    # 1099-INT's box 1 is spelled `Interest income` and `1 interest income`, and the page was read
    # line by line with any spelling allowed on each — so the form's TITLE, `Form 1099-INT Interest
    # Income`, matched first and the row under it, `Tax year 2025`, came back as $2,025.00 of
    # interest (the model read the box's 843.00). A longer spelling is the more specific one (it
    # carries the box number), so each is tried over every line before the next; and once any
    # spelling has found this box's line, a looser one is not let loose on the rest of the page.
    targets = sorted(dict.fromkeys(spelling.lower() for spelling in label_words), key=len, reverse=True)
    # `known` is every OTHER box's spelling on this form, the veto for a tail or a row that is a
    # neighbour's label rather than this box's value. The caller that reads from the dictionary's
    # printed-box sidecar (INPUT-FORMS.md §b) passes the sidecar's own spellings; without one the
    # declared tables below are the whole vocabulary.
    known = _all_labels() if known is None else known
    label_seen, seen_with = False, None

    lines = page.lines()
    for key, target in ((key, target) for target in targets for key in sorted(lines)):
        if label_seen and target != seen_with:
            break            # this box's line was found by a more specific spelling
        line = lines[key]
        joined = " ".join(t.text for t in line).lower()
        idx = joined.find(target)
        if idx == -1:
            continue
        if _inside_a_longer_label(joined, idx, target, known):
            # `bond premium` (1099-INT box 11) is also the start of `bond
            # premium on treasury obligations` (box 12). A match that sits inside a LONGER known
            # label on this line is that other box's caption, not this box's — the line is skipped.
            continue
        label_seen, seen_with = True, target

        # The box this label owns, and therefore how far its value may sit. Bounding by the
        # gutters is what stops the next box's number being read as this box's value.
        column = pdftext.column_for_label(line, idx, len(target), page_width=page.width)
        if column is None:
            continue

        # 1) Same line, inside this box only: the layout `fixtures/synthetic.py` writes. A tail
        # that BEGINS with a neighbour's label (`· IRA/SEP/SIMPLE` after `7 Distribution code(s)`)
        # is that neighbour's, not a value; the rows below are tried instead.
        tail = [t for t in column.tail if not _is_chrome(t)]
        if tail and not _leads_with_label(" ".join(t.text for t in tail), known):
            return _field(page, label_words, tail[0]), FieldOutcome.FOUND

        # 2) The row below, within the same column: the layout the printed form uses.
        for row in pdftext.rows_below(lines, key, column, _VALUE_ROWS, _VALUE_BAND):
            # ⚠ ORDER IS LOAD-BEARING. The guard must see the row the extractor will actually
            # READ, so chrome comes off FIRST. Testing the guard against the unfiltered text
            # re-opened where a box's `$` shares a visual line with the next box's header,
            # the joined row starts with `$`, `_BOX_HEADER_RE` cannot match, and the filter then
            # handed the box NUMBER back as the value — measured on a W-2 as $6.00 of federal
            # withholding at confidence 0.9, replacing an unparseable `'$'` that had refused.
            # Found by adversarial review, 2026-08-14; no page in the corpus could reach it,
            # because the real forms separate those two rows by 12pt.
            cells = [t for t in row if not _is_chrome(t)]
            text = " ".join(t.text for t in cells).lower()
            # `_is_clipped_box_header` is the same question asked of the row's whole printed BOX,
            # for the case where the column bound cut the box number off the header (the real K-1's
            # `6a Ordinary dividends` under box 5). It runs on the same chrome-filtered basis.
            # The header SHAPE is tested with only leading chrome removed (`_header_shaped`):
            # `$ 6 Race` is a header, `1 · IRA [X]` is a code with its mark.
            if (any(lab in text for lab in known) or _header_shaped(row)
                    or _is_clipped_box_header(lines, row)):
                break        # that is the next box's label, not this box's value
            if not cells:
                # The box's own `$` and nothing else. Keep looking rather than call it the value:
                # this corpus's overlay prints the amount on the row UNDER the mark, and a tight
                # payer layout puts it beside the mark inside the same column. (Beyond the column's
                # gutter it is a different box and this box reads EMPTY, which is correct.)
                continue
            inside = [t for t in cells if t.x0 <= column.own_bound()]
            # inside the label's own column, a value-shaped token wins; a token carrying a
            # digit is a figure even when garbled, and is returned so it refuses downstream rather
            # than becoming a 0; a row of WORDS with no digit — the end of an employer line that
            # runs under the box (profile-mortgage-credit's `(SYNTHETIC)`) — is someone else's
            # text, so the search goes on to the next row within the band.
            shaped = [t for t in inside if value_shaped(kind, t.text)]
            if shaped:
                return _field(page, label_words, shaped[0]), FieldOutcome.FOUND
            figures = [t for t in inside if any(ch.isdigit() for ch in t.text)]
            if figures:
                return _field(page, label_words, figures[0]), FieldOutcome.FOUND
            # Only the widened zone holds anything: read it under the two stricter rules.
            for t in cells:
                if t.x0 > column.own_bound() and value_shaped(kind, t.text) \
                        and not _under_foreign_header(lines, t, column, known):
                    return _field(page, label_words, t), FieldOutcome.FOUND
            if inside:
                continue        # words only in the box's own column: not this box's value

    # The label was on the page but its box held nothing: the box exists and is blank.
    return None, (FieldOutcome.EMPTY if label_seen else FieldOutcome.NOT_LOCATED)


def _field(page: pdftext.PageWords, label_words: list[str],
           token: pdftext.Word) -> ExtractedField:
    cents = parse_money_cents(token.text)
    return ExtractedField(
        label=label_words[0],
        value=token.text,
        confidence=0.9 if cents is not None else 0.7,
        source=SourceRegion(page.number + 1, token.x0, token.top, token.x1, token.bottom),
        value_cents=cents,
    )


# --- W-2 worked example -------------------------------------------------------
# A minimal but real set of W-2 boxes. Labels are matched loosely (substring on a
# line); values are the next token. Money tokens get higher confidence.

# EACH ENTRY IS A LIST OF SPELLINGS, every one a whole label, tried in order. Lists once
# held one each, and the IRS form's own wording is still first everywhere; a second is added
# only where a real layout prints something else for the same box — never a bare fragment that
# would match a heading or a neighbour (the title collisions above stand).
# WHAT EACH FORM HAS, declared once per form type. This registry is what makes the pipeline
# extensible to every form rather than to W-2 plus special cases: `extract_declared` walks whatever
# is declared here for the classified type and reports an outcome for EVERY declared field, so
# adding a form means adding its table, not a new code path.

# It also makes today's real state visible instead of silent: a form type declared with no fields
# reports "0 declared" rather than looking like a document nothing could be read from.
# FALLBACK, being retired (INPUT-FORMS.md §b, 2026-09-14): the dictionary's per-form printed-box
# sidecar `boxes.tsv` now owns each box's caption and accepted spellings, imported from this table.
# The intake reader takes its
# spellings from the sidecar wherever the pin carries one and comes here only where it does not.
# Nothing is added here for a form whose sidecar exists; the table goes when the pin bump that
# carries sidecars for every form in FACT_GROUPS lands.
FORM_FIELDS: dict[FormType, dict[str, list[str]]] = {
    FormType.W2: {
        # payroll layouts abbreviate box 1's caption — syndoc's profile-C prints `1 Wages,
        # tips, other comp.` and read 3 and 5 while box 1 came back NOT_LOCATED. `comp` (no period)
        # takes `comp.` and `compensation` both; the word rule in `column_for_label` keeps the long
        # word inside the label.
        "box1_wages": ["wages, tips, other compensation", "wages, tips, other comp"],
        "box2_fed_withholding": ["federal income tax withheld"],
        "box3_ss_wages": ["social security wages"],
        "box4_ss_withholding": ["social security tax withheld"],
        "box5_medicare_wages": ["medicare wages and tips"],
        "box6_medicare_withholding": ["medicare tax withheld"],
    },
    # Only the boxes a fact field can actually hold — `schema/common/facts/int1099.schema.json`
    # carries interest, tax-exempt interest and federal withholding, and nothing else. Extracting a
    # box with nowhere to go would be a figure the taxpayer supplied and the return silently
    # dropped, which is the failure `UNMAPPED_BUT_HARMLESS` exists to make impossible to do by
    # accident.

    # `interest income` is ALSO Schedule K-1's box 5 label — the collision that made every real K-1
    # classify as a 1099-INT. It is safe HERE and was not safe there because this table is
    # keyed on FormType: a label only has to identify a box within a form already identified.
    # ⚠ THE BOX NUMBER IS PART OF THE LABEL HERE, and it has to be. This form's TITLE is
    # "Interest Income" — the same words as its box 1 label — so a bare `interest income` matches
    # the title line first and takes the value after it, which is the YEAR. Measured on the fixture
    # before this was fixed: box 1 came back as $2,025.00, read off `Form 1099-INT Interest Income
    # 2025`. That is the same shape again, arriving from a different direction: a label that is
    # real, in a place that is not a box.

    # Classification solved its version of this positionally (a form names itself in its chrome),
    # and extraction cannot: a W-2's money boxes sit in the top fifth of the page while its
    # title is at the bottom, so there is no region to exclude. The box number is what distinguishes
    # a box from a heading, and information returns print it.
    FormType.F1099_INT: {
        "box1_interest": ["1 interest income"],
        "box4_fed_withholding": ["4 federal income tax withheld"],
        "box8_tax_exempt_interest": ["8 tax-exempt interest"],
        # boxes 2 and 9-13, spelled as build's IRS1099INT list spells them.
        "box2_early_withdrawal_penalty": ["early withdrawal penalty"],
        "box9_private_activity_bond_interest": ["specified private activity bond interest"],
        "box10_market_discount": ["market discount"],
        # Box 11's caption is the start of boxes 12's and 13's; `_inside_a_longer_label` keeps
        # the search off their lines.
        "box11_bond_premium": ["bond premium"],
        "box12_treasury_bond_premium": ["bond premium on treasury obligations"],
        "box13_tax_exempt_bond_premium": ["bond premium on tax-exempt bond"],
    },
    # Only the four boxes `schema/common/facts/div1099.schema.json` can hold. Boxes 2b-2f, 3 and
    # 5-12 have no fact field, so extracting them would be a figure the taxpayer supplied and the
    # return silently dropped.

    # ⚠ THE BOX NUMBER MATTERS MORE HERE THAN ON THE 1099-INT, and is not a nicety. A bare
    # `ordinary dividends` also matches **box 2e, Section 897 Ordinary Dividends**, and a bare
    # `capital gain` also matches **box 2f, Section 897 Capital Gain**. Those are section 897
    # amounts for foreign investors: reading 2e as box 1a would put the wrong figure on Schedule B
    # and refuse nothing. The form's title, *Dividends and Distributions*, is the same title collision again.
    FormType.F1099_DIV: {
        "box1a_ordinary_dividends": ["1a total ordinary dividends"],
        "box1b_qualified_dividends": ["1b qualified dividends"],
        "box2a_capital_gain_distributions": ["2a total capital gain distr"],
        "box4_fed_withholding": ["4 federal income tax withheld"],
    },
    # W-2G, *Certain Gambling Winnings*. The one form here whose labels are read off a REAL IRS
    # FORM pdf rather than off instructions — `sources/fw2g--ty2025--2026-01.pdf`, Copy A — so
    # neither the wording nor the geometry below is ours.

    # Only the two boxes `schema/common/facts/w2g.schema.json` can hold: `winnings_cents` and
    # `federal_withholding_cents`. The other sixteen (2 date won, 3 type of wager, 5-18) have no
    # fact field, and reading one would be a figure the taxpayer supplied and the return silently
    # dropped.

    # ⚠ THE BOX NUMBER IS PART OF THE LABEL. **Four** boxes on this form say *winnings* — 1
    # Reportable winnings, 7 Winnings from identical wagers, 14 State winnings, 16 Local winnings —
    # and so does the form's own title, *Certain Gambling Winnings*. A bare `winnings` is the title
    # collision with more collidees than the 1099-INT had, and on any layout that prints the title
    # above the boxes it matches the heading and takes the value after it.
    FormType.W2G: {
        "box1_reportable_winnings": ["1 reportable winnings"],
        "box4_fed_withholding": ["4 federal income tax withheld"],
    },
    # Schedule K-1 (Form 1065), *Partner's Share of Income, Deductions, Credits, etc.* The second
    # form here whose labels are read off a REAL IRS FORM pdf —
    # `sources/f1065sk1--ty2025--2026-01.pdf` — so neither the wording nor the geometry is ours.

    # Only the six boxes `schema/common/facts/k1.schema.json` can hold:
    # `ordinary_business_income_cents`, `interest_income_cents`, `dividend_income_cents`,
    # `royalties_cents`. Part III carries ~30 more (2, 3, 4c, 6b, 6c, 8, 9a-9c, 10-23) and
    # reading one would be a figure the taxpayer supplied and the return silently dropped
    #. Box 6a is *Ordinary dividends* and 6b is *Qualified dividends*: the schema has
    # ONE dividend field and 6a is the total, so 6b is a neighbour, not a second field.

    # ⚠ THE PARENTHETICAL IS PART OF THE LABEL, and on this form that is not cosmetic. Declared as
    # a bare `1 ordinary business income`, the printed label's own tail — `(loss)` — is the next
    # thing on that line, so the extractor returns it as the box's VALUE: FOUND, unparseable,
    # confidence 0.7. A blank box reported as read, from inside the label itself. Measured on the
    # pristine page; pinned by `tests/test_k1_extraction.TheParentheticalIsPartOfTheLabelTest`.

    # ⚠ THE BOX NUMBER IS PART OF THE LABEL, as everywhere else here. Part III stacks its boxes in
    # one narrow column, so `ordinary dividends` alone is 6a and 6b at once, and `interest income`
    # alone is also the 1099-INT's box 1 — the collision that made every real K-1 classify as a
    # 1099-INT.
    FormType.K1_1065: {
        "box1_ordinary_business_income": ["1 ordinary business income (loss)"],
        # boxes 4a/4b joined the schema, so they are read rather than asked.
        "box4a_guaranteed_payments_services": ["4a guaranteed payments for services"],
        "box4b_guaranteed_payments_capital": ["4b guaranteed payments for capital"],
        "box5_interest_income": ["5 interest income"],
        "box6a_ordinary_dividends": ["6a ordinary dividends"],
        "box7_royalties": ["7 royalties"],
    },
    # Schedule K-1 (Form 1120-S), *Shareholder's Share of Income, Deductions, Credits, etc.*
    # Labels read off the REAL IRS FORM pdf
    # (`dictionary/pdf/2025/IRS1120SSK/en/f1120ssk.pdf`, pypdf-dumped — see
    # `scripts/k1_captions_pypdf_check.py`, which already verified these same words against all
    # three K-1 templates for the shared `form_labels.py` captions).

    # THE SAME FOUR FACTS AS THE 1065, AT DIFFERENT BOX NUMBERS. This form's Part III shifts every
    # box after 1 by one relative to the 1065 (no guaranteed-payments boxes 4a-4c to make room
    # for): interest is box 4 (not 5), ordinary dividends box 5a (not 6a), royalties box 6 (not
    # 7). Box 1's own caption — "1 Ordinary business income (loss)" — is IDENTICAL to the 1065's,
    # which is exactly the collision `classify._UNSUPPORTED` used to refuse this whole form over
    # (a shareholder figure read as a partner's); it is safe here because `FORM_FIELDS` is keyed on
    # FormType and this page now classifies as its own `K1_1120S`, never `K1_1065`.

    # ⚠ NO GUARANTEED-PAYMENTS BOX EXISTS ON THIS FORM AT ALL (they are a partnership-only concept,
    # IRC section 707(c)) — so, unlike the 1065 above, this table declares no
    # `guaranteed_payments_*` label. `extract_declared` only ever reports an outcome for a label
    # DECLARED here, so this form proposes nothing for those fields rather than a stated 0 for a
    # box it never prints.

    # ⚠ BOX 6, ROYALTIES, DOES PRINT ON THIS FORM AND IS STILL NOT DECLARED — the one row here
    # where a real box is left unread for a reason that is not about the page. `k1.schema.json`'s
    # `royalties_cents` IS the fact this box would become, but `mapper.py`'s own
    # `_K1_FIELDS_NOT_ON["s_corp"]` refuses that field on every s_corp item by name: the pinned
    # engine's writable fact-graph carries a shareholder's royalties nowhere at all (a dictionary
    # gap, not this collector's to fix). Declaring the box here would extract a figure the client
    # bridge (`documents.py`'s `K1_1120S_LABEL_TO_FIELD`, which drift-locks against this table)
    # would then have nowhere honest to route.
    FormType.K1_1120S: {
        "box1_ordinary_business_income": ["1 ordinary business income (loss)"],
        "box4_interest_income": ["4 interest income"],
        "box5a_ordinary_dividends": ["5a ordinary dividends"],
    },
    # Schedule K-1 (Form 1041), *Beneficiary's Share of Income, Deductions, Credits, etc.*
    # Labels read off the real IRS form pdf (the pin's own
    # `dictionary/pdf/2025/IRS1041SK1/en/f1041sk1.pdf`, pypdf-dumped — see
    # `scripts/k1_captions_pypdf_check.py`, which independently checks these same captions
    # against all three K-1 templates).

    # A GENUINE REMAPPING, NOT A NUMBERING SHIFT, unlike the 1120-S above. Box 1 on THIS form is
    # *Interest income* (the 1065/1120-S read that box at 5/4); box 2a is *Ordinary dividends*
    # (2b, printed right after it, is *Qualified dividends* — a neighbour, not a second field,
    # the same box-6a/6b relationship the 1065 has); box 6 is *Ordinary business income*, with no
    # "(loss)" in its printed caption (the 1065/1120-S both print "(loss)" on their box 1).

    # ⚠ NO ROYALTIES BOX EXISTS ON THIS FORM AT ALL. An estate or trust's royalties are folded
    # into box 5, "Other portfolio and nonbusiness income" — a box this schema has no field for,
    # and one this map declares nothing for on purpose: reading "5 other portfolio and
    # nonbusiness income" as `royalties_cents` would report a figure that may not be royalties at
    # all (it is whatever else box 5 happens to carry), which is worse than not reading it.
    # `mapper.py`'s own `_K1_FIELDS_NOT_ON["estate_trust"]` refuses `royalties_cents` on every
    # estate_trust item for the same reason `K1_1120S_LABEL_TO_FIELD` gives for the s_corp case:
    # the pinned engine's writable fact-graph carries an estate/trust beneficiary's royalties
    # nowhere at all (a dictionary gap, not this collector's to fix).

    # ⚠ NO GUARANTEED-PAYMENTS BOX EITHER, the same reading as the 1120-S: guaranteed payments are
    # a partnership-only concept (IRC section 707(c)), and this form prints no such box.
    FormType.K1_1041: {
        "box1_interest_income": ["1 interest income"],
        "box2a_ordinary_dividends": ["2a ordinary dividends"],
        "box2b_qualified_dividends": ["2b qualified dividends"],
        "box6_ordinary_business_income": ["6 ordinary business income"],
    },
    # Form 1099-B: ONE transaction, the IRS template's one row. Only the
    # boxes build's printed-box list can find on a page are spelled — as the list spells them.
    # Boxes 1b-1e, 2 and 12 carry a Form 8949 note in their list spelling and box 3's two marks
    # share one, so none of those is looked for; the page asks them. A broker's
    # consolidated statement (many rows) is a reading problem this table does not attempt.
    FormType.F1099_B: {
        "box1f_accrued_market_discount": ["accrued market discount"],
        "box1g_wash_sale_loss_disallowed": ["wash sale loss disallowed"],
        "box4_fed_withholding": ["federal income tax withheld"],
        "box7_loss_not_allowed": ["check if loss is not allowed based on amount in 1d"],
    },
    # Form 1099-R, *Distributions From Pensions, Annuities, Retirement or Profit-Sharing Plans,
    # IRAs, Insurance Contracts, etc.*. The boxes `schema/common/facts/r1099.schema.json`
    # carries and a statement prints on its face: 1, 2a, 2b (a mark), 4, 7 (a code) and the
    # IRA/SEP/SIMPLE mark beside it. Labels are the IRS form's own words, box number included.

    # ⚠ THE 2026 IRS TEMPLATE WRAPS ITS LABELS -- `4 Federal income tax` / `withheld`, `7a Dist.` /
    # `code(s)`, `7b IRA/SEP/` / `SIMPLE` -- and splits box 7 into 7a-7d. A label is matched on
    # ONE printed line, so on that template boxes 4, 7 and the marks are NOT_LOCATED and asked;
    # boxes 1 and 2a locate and read EMPTY on the blank form (measured 2026-09-09 on irs.gov's
    # `f1099r.pdf`; the corpus holds the form's instructions but not the form). That is the safe
    # outcome. A second spelling for a wrapped label would be a fragment, which the rule above forbids.
    FormType.F1099_R: {
        "box1_gross_distribution": ["1 gross distribution"],
        "box2a_taxable_amount": ["2a taxable amount"],
        "box2b_taxable_amount_not_determined": ["2b taxable amount not determined"],
        "box4_fed_withholding": ["4 federal income tax withheld"],
        "box7_distribution_code": ["7 distribution code(s)"],
        "box7b_ira_sep_simple": ["ira/sep/simple"],
    },
    # Form 1099-MISC, *Miscellaneous Information*. The boxes
    # `schema/common/facts/misc1099.schema.json` holds: box 2 (royalties), box 3 (other income)
    # and box 4. Boxes 1 (rents) and 5-18 have no fact field and are never looked for — measured
    # on the synthetic corpus's three ROYALTY 1099-MISCs
    # (`collector/tests/layouts/profilemulti-stream_1099misc.pdf` among them), where the money
    # lives in box 2 and box 3 is printed but blank on every one; box 2 was given a fact field
    # (the one return-level royalty activity, `mapper._map_royalties`) rather than leaving the
    # money unread.
    # `is_alaska_pfd` is required by the schema but is not a box on any 1099-MISC — it is the
    # engine's own per-form question (`documents.py` asks it, never reads it from a page).
    FormType.F1099_MISC: {
        "box2_royalties": ["2 royalties"],
        "box3_other_income": ["3 other income"],
        "box4_fed_withholding": ["4 federal income tax withheld"],
    },
    # Form 1099-G, *Certain Government Payments*. Only the boxes
    # `schema/common/facts/g1099.schema.json` holds: box 1, unemployment compensation, and box 4.
    # Boxes 2 (state/local refunds — not covered), 3, 5-11 have no fact field. `repaid_cents` is
    # required-adjacent but is not a box either (the Schedule 1 line 7 repayment entry space, not
    # printed on the form) and so is never read here.
    FormType.F1099_G: {
        "box1_unemployment_compensation": ["1 unemployment compensation"],
        "box4_fed_withholding": ["4 federal income tax withheld"],
    },
    # Form 1099-OID, *Original Issue Discount*. Every box `schema/common/facts/oid1099.schema.json`
    # holds — the nine amounts and the FATCA mark (a CHECK, `FIELD_KINDS`). Captions as printed,
    # from build's boxes.tsv sidecar. Box 7 (description), box 9 (investment
    # expenses) and the state boxes 12-14 have no fact field and are never looked for.
    FormType.F1099_OID: {
        # Spelled WITHOUT the box number, as build's sidecar states them (its
        # aliases for this form are the captions alone; `test_the_collectors_spellings_are_all_in_
        # the_sidecar` holds the two together). Safe here because no caption is a prefix of another.
        # Boxes 1 and 8 and the FATCA mark WRAP on the real IRS page, where a whole caption
        # locates none of the three. The spellings are build's to state; until
        # they land those boxes are ASKED, not read — acknowledged, not worked around here.
        "box1_original_issue_discount": ["original issue discount for the year"],
        "box2_other_periodic_interest": ["other periodic interest"],
        "box3_early_withdrawal_penalty": ["early withdrawal penalty"],
        "box4_fed_withholding": ["federal income tax withheld"],
        "box5_market_discount": ["market discount"],
        "box6_acquisition_premium": ["acquisition premium"],
        "box8_oid_on_treasury_obligations": ["original issue discount on u.s. treasury obligations"],
        "box10_bond_premium": ["bond premium"],
        "box11_tax_exempt_oid": ["tax-exempt oid"],
        "fatca_filing_requirement": ["fatca filing requirement"],
    },
    # Form 1099-SA, *Distributions From an HSA, Archer MSA, or Medicare Advantage MSA*. Only
    # the boxes `schema/common/facts/hsa_distribution.schema.json` holds: box 1, gross
    # distribution, and box 3, distribution code (a CODE, not money — `FIELD_KINDS` says so, the
    # same treatment box 7 of the 1099-R gets). Boxes 2 (earnings on excess contributions), 4 (FMV
    # on date of death) and 5 (account type, a checkbox) have no fact field.
    # `qualified_medical_expenses_cents` is required by the schema but is on no box — "the
    # recipient's own records (Form 8889 line 15), never a 1099-SA box" per the synthetic page's
    # own payer statement, measured on `profilehsa-distribution_1099sa.pdf`.
    FormType.F1099_SA: {
        "box1_gross_distribution": ["1 gross distribution"],
        "box3_distribution_code": ["3 distribution code"],
    },
    FormType.F1098: {},
}

# Kept as the old name so nothing that referenced it breaks; the registry is the source.
_W2_BOXES = FORM_FIELDS[FormType.W2]


def extract_declared(page: pdftext.PageWords,
                     form_type: FormType,
                     fields: dict[str, list[str]] | None = None,
                     kinds: dict[str, str] | None = None,
                     known: list[str] | None = None) -> tuple[list[ExtractedField], list[FieldReport]]:
    """Walk every field declared for `form_type`, reporting what became of each.

    `fields` (label -> spellings) and `kinds` (label -> MONEY/CODE/CHECK) replace this module's
    own tables when the caller has a better source: the intake reader builds them from the
    dictionary's printed-box sidecar, `boxes.tsv` (INPUT-FORMS.md §b), the register that owns
    captions and accepted spellings. `known` travels with them (see `_value_after_label`).
    Without them the tables below apply — the fallback the standard retires once a pin carries
    sidecars."""
    found: list[ExtractedField] = []
    reports: list[FieldReport] = []
    table = FORM_FIELDS.get(form_type, {}) if fields is None else fields
    kind_of = FIELD_KINDS if kinds is None else kinds
    for canonical, label_words in table.items():
        kind = kind_of.get(canonical, MONEY)
        fld, outcome = _value_after_label(page, label_words, kind, known)
        reports.append(FieldReport(label=canonical, outcome=outcome))
        if fld is not None:
            fld.label = canonical  # normalize to a stable internal label
            if kind != MONEY:
                # A code or a mark is not money: `7` is a code, never 700 cents.
                fld.value_cents = None
                fld.confidence = 0.9 if value_shaped(kind, fld.value) else 0.7
            found.append(fld)
    return found, reports


def extract_w2(page: pdftext.PageWords) -> list[ExtractedField]:
    """Back-compatible shim: the found fields only."""
    return extract_declared(page, FormType.W2)[0]


def _needs_assisted(_page: pdftext.PageWords) -> list[ExtractedField]:
    return []


EXTRACTORS: dict[FormType, Extractor] = {
    FormType.W2: extract_w2,
    # Extension points — classification & redaction are wired; add extractors here.
    FormType.F1099_INT: lambda page: extract_declared(page, FormType.F1099_INT)[0],
    FormType.F1099_DIV: lambda page: extract_declared(page, FormType.F1099_DIV)[0],
    FormType.W2G: lambda page: extract_declared(page, FormType.W2G)[0],
    FormType.K1_1065: lambda page: extract_declared(page, FormType.K1_1065)[0],
    FormType.K1_1120S: lambda page: extract_declared(page, FormType.K1_1120S)[0],
    FormType.K1_1041: lambda page: extract_declared(page, FormType.K1_1041)[0],
    FormType.F1099_B: lambda page: extract_declared(page, FormType.F1099_B)[0],
    FormType.F1099_R: lambda page: extract_declared(page, FormType.F1099_R)[0],
    FormType.F1099_OID: lambda page: extract_declared(page, FormType.F1099_OID)[0],
    FormType.F1099_MISC: lambda page: extract_declared(page, FormType.F1099_MISC)[0],
    FormType.F1099_G: lambda page: extract_declared(page, FormType.F1099_G)[0],
    FormType.F1099_SA: lambda page: extract_declared(page, FormType.F1099_SA)[0],
    FormType.F1098: _needs_assisted,
}


def extract(path: Path, form_type: FormType) -> ExtractedDocument:
    doc_ir = ExtractedDocument(form_type=form_type, source_path=str(path))
    pages = pdftext.load_pages(path)
    doc_ir.raw_text = "\n".join(pg.text for pg in pages)
    if form_type not in FORM_FIELDS:
        doc_ir.warnings.append(f"no extractor for {form_type.value}")
        return doc_ir
    # Run on page 1 (these single-page forms carry their boxes there).
    fields, reports = extract_declared(pages[0], form_type) if pages else ([], [])
    doc_ir.fields = fields
    doc_ir.outcomes = reports
    if not fields:
        doc_ir.warnings.append(
            f"{form_type.value}: no high-confidence fields extracted "
            "(extension point or assisted extraction needed)"
        )
    return doc_ir
