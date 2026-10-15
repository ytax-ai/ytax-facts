# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Classify a PDF into an IRS form type from its page-1 text.

Classification runs on intact text (before redaction can remove the form title)
and matches characteristic identifier strings. Unknown documents are reported as
UNKNOWN for manual review rather than guessed at. OCR is only needed when the
page has no text layer; an injectable OCR backend handles that case.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional

from . import pdftext
from .models import FormType

# WHERE a form says what it is. Identity lives in the title block; a form NUMBER appearing
# further down is a cross-reference to a different form, not a claim about this one. Measured on the
# real IRS PDFs: the K-1 says "Schedule K-1" on line 2 and "Interest income" — its own box 5 label —
# on line 17; Form 1040 mentions "1099-R" on line 53 of 80. Restricting identification to the title
# block is what separates the two, and it is the fix for two of the three failures below.
_TOP_FRACTION = 0.2      # of the page's lines, taken from EACH end
_TOP_MIN_LINES = 6

# Each entry: (FormType, [identifiers]). Matched with WORD BOUNDARIES against the title block only.

# Three things this table used to get wrong, all measured on real IRS forms rather than on the
# synthetic fixtures it was written against:

#   * "interest income" is Schedule K-1's own BOX 5 LABEL, not a 1099-INT identifier. Because
#     1099-INT sat earlier in an ordered first-match list, every real K-1 classified as a 1099-INT —
#     and the correct K-1 match, which the same page also produced, was discarded by ordering.
#   * "form w-2" is a PREFIX of "Form W-2G", so a gambling form classified as a W-2 and had W-2 box
#     extraction applied to boxes that are not W-2 boxes.
#   * Nothing distinguished a form's own number from a mention of another form's.

# Identifiers are now the form's TITLE or its own number, never a box label — a box label is shared
# vocabulary between forms and can never identify one.
_SIGNATURES: list[tuple[FormType, list[str]]] = [
    (FormType.W2, ["wage and tax statement", "form w-2"]),
    # Sits next to the W-2 on purpose: these two are the pair the word boundary in `_mentions`
    # exists for, and a reader who changes one should see the other. `w-2g` is the form's own
    # number and carries the whole match on a real Copy A, where the title *Certain Gambling
    # Winnings* is printed VERTICALLY down the right margin — one word per line, so the phrase
    # never occurs. The title is listed for the substitute statements that print it as an ordinary
    # heading; it identifies nothing on the IRS page itself.

    # A title needle also matches PROSE about the form — chrome reading "Report certain gambling
    # winnings on Schedule 1" classifies as a W-2G. That is this table's standing behaviour rather
    # than something this entry introduced (`i1099int` already reads as a 1099-INT and `i8959` as a
    # W-2), and it costs nothing today: an instructions page carries no boxes, so the result is an
    # empty extraction and not a wrong number. Noted so the next reader knows it is seen, not
    # missed.
    (FormType.W2G, ["w-2g", "certain gambling winnings"]),
    (FormType.F1099_INT, ["1099-int"]),
    (FormType.F1099_DIV, ["1099-div", "dividends and distributions"]),
    (FormType.F1099_B, ["1099-b", "proceeds from broker"]),
    (FormType.F1099_R, ["1099-r", "distributions from pensions"]),
    # the form's own number, plus its title where a substitute statement prints one instead
    # (the real IRS Copy B pages measured for this unit all print BOTH — "Form 1099-MISC
    # Miscellaneous Information", "Form 1099-G Certain Government Payments", "Form 1099-SA
    # Distributions From an HSA, Archer MSA, or Medicare Advantage MSA" — but the title alone is
    # kept as a fallback the way the W-2G entry above keeps "certain gambling winnings").
    (FormType.F1099_MISC, ["1099-misc", "miscellaneous information"]),
    (FormType.F1099_G, ["1099-g", "certain government payments"]),
    (FormType.F1099_SA, ["1099-sa", "distributions from an hsa"]),
    # Form 1099-OID: its own number only. The title, "Original Issue Discount", is NOT a needle —
    # a 1099-INT's instructions and a brokerage statement both print those words.
    (FormType.F1099_OID, ["1099-oid"]),
    (FormType.F1098, ["form 1098", "mortgage interest statement"]),
    # ⚠ `schedule k-1` ALONE CANNOT IDENTIFY THIS FORM — it is the shared title prefix of the
    # 1065, the 1041 and the 1120-S — so it is deliberately NOT a needle here. `form 1065` is each
    # form's OWN number, verified (docstring, `test_the_PARTNERSHIPS_k1_still_classifies...`) to
    # appear on a real 1065 page's chrome and on NEITHER of the other two K-1s'.
    (FormType.K1_1065, ["form 1065"]),
    # The S corporation's Schedule K-1, split out of `_UNSUPPORTED` now
    # that the collector reads its boxes (`extract.FORM_FIELDS[K1_1120S]`). `form 1120-s` is this
    # form's own number, printed directly under the shared "Schedule K-1" title and on no other K-1
    # — the same disambiguation `_UNSUPPORTED` already relied on to keep this form OUT of
    # `K1_1065`, now used to route it to its own type instead of refusing it. The 1041 used to
    # stay in `_UNSUPPORTED` here (its box numbering is not a shift of the same boxes) — it
    # later got the same treatment, once the box remapping was measured and
    # built out (`extract.FORM_FIELDS[K1_1041]`).
    (FormType.K1_1120S, ["form 1120-s"]),
    # The estate/trust Schedule K-1, split out of `_UNSUPPORTED` the same
    # way the 1120-S was. `form 1041` is this form's own number, printed directly under the shared
    # "Schedule K-1" title (`(Form 1041) 2025`) and on neither of the other two K-1s' chrome — see
    # `test_the_PARTNERSHIPS_k1_still_classifies_after_the_other_two_are_split_off`, which now
    # checks this needle too.
    (FormType.K1_1041, ["form 1041"]),
]

# Forms we can RECOGNISE but do not support. Naming them is the point: an unsupported form must
# classify UNKNOWN, never as the nearest supported one. A W-2C reading as a W-2 is worse than a
# W-2C reading as unknown — the first computes a return from the wrong boxes, the second refuses.

# W-2G USED TO BE THE WORKED EXAMPLE HERE and has moved to `_SIGNATURES`: the collector now reads
# its boxes 1 and 4. Note that this list is checked FIRST, so leaving an entry here would have
# short-circuited the new signature entirely — recognising a form and supporting it are the same
# switch, and it has exactly one position.

# ⚠ THE OTHER TWO SCHEDULES K-1 WERE THE HEADER RULE'S OWN COUNTEREXAMPLE, found by review of the
# client-side K-1 bridge and MEASURED ON REAL PAPER. `schedule k-1` is the title prefix of three
# different forms, and with `any()` semantics a broad `K1_1065` signature that included it matched
# all three:

#     f1041sk1--ty2025--2025-12.pdf   ->  K-1 (1065)      (a TRUST's Schedule K-1)
#     f1120ssk--ty2025--2026-01.pdf   ->  K-1 (1065)      (an S CORPORATION's Schedule K-1)

# That was survivable while nothing could consume a K-1 — the client refused the batch. It stopped
# being survivable the moment the client learned to read one, because the 1120-S prints its box 1
# header VERBATIM as `1 Ordinary business income (loss)`, the exact string the 1065 label map
# declares. Measured on an overlay of the real 1120-S page: an $88,500 shareholder figure extracted,
# crossed the client bridge, was stamped `source: "partnership"` and PASSED the outbound lint. A
# wrong fact, silently, on a return that looks finished — precisely what this list (and, later, the
# 1120-S's own `_SIGNATURES` row above) exists to stop.

# The 1120-S moved OUT of this list and into `_SIGNATURES` once the
# collector learned its own box numbering (box 4/5a/6, not 5/6a/7, and no guaranteed-payments box
# at all). The estate/trust K-1 later did the same, once its own genuine
# remapping (box 1 is *interest* income, not ordinary business income; box 6 is ordinary business
# income; no royalties box at all) was measured off the real page and built out.
_UNSUPPORTED: list[tuple[str, list[str]]] = [
    ("W-2C (corrected wage and tax statement)", ["w-2c"]),
    ("1099-NEC (nonemployee compensation)", ["1099-nec"]),
    # 1099-MISC MOVED TO `_SIGNATURES`: the collector now reads its box 3 and box 4.
    # Forms the pinned dictionary MODELS but that must not be read (measured on the pinned engine):
    # a Form 1099-PATR's boxes land on Schedule F line 3a, behind a farm this service never
    # declares — read, its box 4 withholding was credited on line 25d while its income reached no
    # line at all (52,000.00 of income with or without 1,000.00 in box 1). The other five bind
    # facts no computation reads. Each is refused BY NAME so the person is told
    # which paper was not used, rather than "no known form identifier".
    ("1099-PATR (taxable distributions received from cooperatives)", ["1099-patr"]),
    ("W-2AS (American Samoa wage and tax statement)", ["w-2as"]),
    ("W-2GU (Guam wage and tax statement)", ["w-2gu"]),
    ("W-2VI (U.S. Virgin Islands wage and tax statement)", ["w-2vi"]),
    ("Form 2439 (undistributed long-term capital gains)", ["form 2439"]),
    ("5498-SA (HSA, Archer MSA, or Medicare Advantage MSA information)", ["5498-sa"]),
    # Schedule K-1 (Form 8865), a foreign partnership's K-1 — measured on the pinned engine: build's
    # printed-box list for it carries build notes where the captions go and no spelling on the
    # boxes this service reads, so no box can be found on the page; and the form
    # prints neither item D nor item G, which the engine asks of every partnership K-1. Refused BY
    # NAME, not left as "no known form identifier". Only its own page says "form 8865" in the title
    # block — every other K-1, real and synthetic, was checked.
    ("Schedule K-1 (Form 8865) (a foreign partnership's K-1)", ["form 8865"]),
]


def _title_block(text: str) -> str:
    """The chrome of page 1 — its header AND its footer — where a form states what it is.

    Not the top alone. A W-2 puts `Form W-2  Wage and Tax Statement` along the BOTTOM, beneath the
    boxes, while a Schedule K-1 puts its title at the very top; the one thing they share is that
    neither states its identity in the MIDDLE. A cross-reference to another form does live there —
    Form 1040 mentions 1099-R on line 53 of 80 — so the body is exactly what has to be excluded.

    A short page is treated as all chrome, which is right: there is no body to confuse it with.
    """
    lines = text.splitlines()
    keep = max(_TOP_MIN_LINES, int(len(lines) * _TOP_FRACTION))
    if len(lines) <= keep * 2:
        return "\n".join(lines).lower()
    return "\n".join(lines[:keep] + lines[-keep:]).lower()


def _mentions(haystack: str, needle: str) -> bool:
    """Substring match with word boundaries, so `form w-2` does not match `Form W-2G`."""
    return re.search(rf"(?<![0-9a-z]){re.escape(needle)}(?![0-9a-z])", haystack) is not None

# An OCR backend takes a path and returns extracted page-1 text (or "").
OCRBackend = Callable[[Path], str]


def _noop_ocr(_path: Path) -> str:
    return ""


def page1_text(path: Path, ocr: OCRBackend = _noop_ocr) -> str:
    """Return page-1 text; fall back to OCR if there is no text layer."""
    if pdftext.page_count(path) == 0:
        return ""
    text = pdftext.page_text(path, 0)
    if text.strip():
        return text
    return ocr(path)  # scanned page: defer to OCR backend


def classify(path: Path, ocr: OCRBackend = _noop_ocr) -> tuple[FormType, Optional[str]]:
    """Return (FormType, warning). warning is set when the page had no text."""
    text = page1_text(path, ocr=ocr)
    warning = None
    if not text.strip():
        warning = "no text layer and OCR returned nothing"
        return FormType.UNKNOWN, warning
    title = _title_block(text)

    # Recognised-but-unsupported first, so it cannot fall through to a form it merely resembles.
    for name, needles in _UNSUPPORTED:
        if any(_mentions(title, n) for n in needles):
            return FormType.UNKNOWN, (
                f"recognised as {name}, which this collector does not support — refusing rather "
                f"than treating it as the nearest form it resembles")

    matched = [ft for ft, needles in _SIGNATURES
               if any(_mentions(title, n) for n in needles)]
    if len(matched) > 1:
        # Ambiguity is not resolved by list order. Ordering is what made every real Schedule K-1
        # classify as a 1099-INT: the page produced both, and the earlier entry silently won.
        names = ", ".join(sorted(ft.value for ft in matched))
        return FormType.UNKNOWN, (
            f"page 1 identifies as more than one form ({names}) — refusing rather than taking "
            f"whichever is listed first")
    if matched:
        return matched[0], None
    return FormType.UNKNOWN, "no known form identifier found on page 1"
