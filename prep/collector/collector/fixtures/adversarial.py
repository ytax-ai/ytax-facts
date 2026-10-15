# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Adversarial redaction corpus: real IRS layouts, synthetic identity. SYNTHETIC DATA ONLY.

WHY THIS EXISTS. `synthetic.py` writes its W-2 as `Employee's name {FAKE_NAME}` -- the redactor's
own `_PII_LABELS` string, verbatim, on one line, value to the right. Every fixture in that module is
written to the redactor's own label list and single-line layout, so redaction passing on it proves
nothing about a real document. This module builds the corpus that CAN fail, so recall becomes a
number instead of an assumption (issue plan v2 step 0).

TWO KINDS OF PAGE, and the difference is stated rather than blurred:

  * **Real-layout** (`overlay_real_form`) -- a page of an actual IRS PDF from
    the directory YTAX_IRS_SOURCES names (READ-ONLY from this repo). Its word boxes are re-drawn at their
    own coordinates and synthetic identity is planted in the row BELOW its real label, which is
    where the real form puts it. Nothing about the label text or the geometry is ours, so the page
    cannot be accidentally written to suit the redactor. Schedule K-1 (1065) is the one form the
    collector handles that exists here as a real PDF.
  * **Reconstructed** (`make_w2_real_layout`) -- there is NO real W-2 form PDF in `sources/`, and
    the W-2 is the collector's primary form. So its box labels are taken verbatim from the IRS's
    own W-2/W-3 instructions (`iw2w3`, e.g. *"Box a--Employee's social security number"*,
    *"Box h--Employee's first name and initial, Last name,"*) and laid out label-above-value as the
    printed form does. IRS-authored wording, our geometry -- weaker evidence than a real page, and
    labelled as such wherever the number is reported.

Identity values are invalid by construction: the SSN 000 area is never issued, and the names and
addresses are nonsense. No real taxpayer data, here or anywhere.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from reportlab.pdfgen import canvas as _rl_canvas

from ..ingest import pdftext

# The real IRS PDFs this corpus overlays. Read-only, and absent on a machine that has no build-repo
# checkout -- callers self-skip rather than fabricate a page (see `sources_dir`).
SOURCES = Path(os.environ["YTAX_IRS_SOURCES"]) if os.environ.get("YTAX_IRS_SOURCES") else None

_PAGE_W, _PAGE_H = 612, 792  # US Letter

# Synthetic identity. The 000 SSN area is never issued; everything else is nonsense.
ID_NAME_FIRST = "Pat Q"
ID_NAME_LAST = "Testperson"
ID_SSN_DASHED = "000-12-3456"
ID_SSN_BARE = "000123456"        # how payroll systems actually print box a
ID_SSN_BARE_2 = "000998877"      # a SECOND undashed TIN, so two plants on one page stay attributable
ID_STREET = "123 Nowhere Lane"
ID_CITY_LINE = "Faketown ZZ 00000"
ID_EIN = "00-7654321"


IDENTITY = "identity"   # must be REMOVED by redaction
TAX = "tax"             # must SURVIVE redaction -- extraction needs it


@dataclass(frozen=True)
class Plant:
    """One synthetic value placed on a page, and what redaction owes it.

    `term` is the vocabulary term (what the value IS); `anchor` is the real label text it sits
    under, kept so a miss can be attributed to a cause instead of merely counted.

    `kind` is the two-sided bar. `IDENTITY` must be gone from the redacted artifact; `TAX` must
    still be there. One mechanism reports both, because the cheapest way to score 100% recall is to
    burn the page -- and on a real W-2 the identity band and the box 1-6 money column are the same
    band. A corpus that only counts removals calls that a total success.
    """

    term: str
    value: str
    anchor: str
    kind: str = IDENTITY
    # WHICH occurrence of `anchor` to plant under, when a form prints the same label twice. A W-2G
    # has `City or town` in the PAYER's block (line 7) and again in the WINNER's (line 23), and
    # first-match put a plant named `winner.city` in the payer's box -- so the winner's own address
    # box, the one that is the taxpayer's identity, was never on the page. Zero-based; every
    # existing plant keeps the first match it always had.
    occurrence: int = 0
    # How far below its label's line the value's baseline sits. 11pt is one line height -- the
    # default every plant has always used. A test that wants a figure LOW in its printed box (a
    # preparer's software does not all print at the same height) says so here, rather than
    # re-implementing the overlay to do it.
    drop: float = 11.0


def make_1099int_money_under_identity(path: Path) -> list[Plant]:
    """A 1099-INT with its money box directly BENEATH an identity label. RECONSTRUCTED.

    This geometry is what no other corpus page had, and it is why this fixture exists: on the W-2 page the
    money sits in a separate column from the identity band, so a redactor that swallowed the row
    below an identity label was never caught. Here the row under `Recipient's TIN` is box 1 — and
    burning it destroys the only figure the form carries.

    Box wording is the IRS's (`i1099int`); the geometry is ours, since `sources/` holds the
    instructions and no 1099-INT FORM pdf. Same standing caveat as the W-2 page.
    """
    c = _rl_canvas.Canvas(str(path), pagesize=(_PAGE_W, _PAGE_H), invariant=1)

    def label(x: float, y: float, text: str) -> None:
        c.setFont("Helvetica", 6.5)
        c.drawString(x, _PAGE_H - y, text)

    def value(x: float, y: float, text: str) -> None:
        c.setFont("Helvetica", 10)
        c.drawString(x, _PAGE_H - y, text + " ")

    label(72, 72, "Form 1099-INT   Interest Income   2025")
    label(72, 100, "RECIPIENT’S name")
    value(72, 114, f"{ID_NAME_FIRST} {ID_NAME_LAST}")
    label(72, 136, "RECIPIENT’S TIN")
    value(72, 150, ID_SSN_BARE)
    # The money box, one row under the identity band — the geometry that failed.
    label(72, 172, "1 Interest income")
    value(72, 186, "1,234.00")
    label(72, 208, "4 Federal income tax withheld")
    value(72, 222, "150.00")
    c.showPage()
    c.save()

    return [
        Plant("recipient.name", f"{ID_NAME_FIRST} {ID_NAME_LAST}", "RECIPIENT’S name"),
        Plant("recipient.tin", ID_SSN_BARE, "RECIPIENT’S TIN"),
        Plant("int.box1_interest", "1,234.00", "1 Interest income", TAX),
        Plant("int.box4_withholding", "150.00", "4 Federal income tax withheld", TAX),
    ]


def make_1099div_with_section897(path: Path) -> list[Plant]:
    """A 1099-DIV carrying the boxes that COLLIDE with the ones we want. RECONSTRUCTED.

    Box 2e is *Section 897 Ordinary Dividends* and box 2f *Section 897 Capital Gain* — so a bare
    `ordinary dividends` or `capital gain` label matches the wrong box. Those are section 897
    amounts for foreign investors, and reading 2e as box 1a would put the wrong figure on Schedule B
    while refusing nothing. This page exists so that stays measured rather than argued.

    Money sits under the identity band as on the 1099-INT page, which is the geometry that caught
    Box wording is the IRS's (`i1099div`); the geometry is ours, since `sources/` holds the
    instructions and no 1099-DIV FORM pdf.
    """
    c = _rl_canvas.Canvas(str(path), pagesize=(_PAGE_W, _PAGE_H), invariant=1)

    def label(x: float, y: float, text: str) -> None:
        c.setFont("Helvetica", 6.5)
        c.drawString(x, _PAGE_H - y, text)

    def value(x: float, y: float, text: str) -> None:
        c.setFont("Helvetica", 10)
        c.drawString(x, _PAGE_H - y, text + " ")

    label(72, 72, "Form 1099-DIV   Dividends and Distributions   2025")
    label(72, 100, "RECIPIENT’S name")
    value(72, 114, f"{ID_NAME_FIRST} {ID_NAME_LAST}")
    label(72, 136, "RECIPIENT’S TIN")
    value(72, 150, ID_SSN_BARE)
    label(72, 172, "1a Total ordinary dividends")
    value(72, 186, "2,400.00")
    label(72, 208, "1b Qualified dividends")
    value(72, 222, "1,900.00")
    label(72, 244, "2a Total capital gain distr.")
    value(72, 258, "310.00")
    # The decoys. Different figures on purpose: reading one as box 1a is then VISIBLE.
    label(72, 280, "2e Section 897 ordinary dividends")
    value(72, 294, "77.00")
    label(72, 316, "2f Section 897 capital gain")
    value(72, 330, "88.00")
    c.showPage()
    c.save()

    return [
        Plant("recipient.name", f"{ID_NAME_FIRST} {ID_NAME_LAST}", "RECIPIENT’S name"),
        Plant("recipient.tin", ID_SSN_BARE, "RECIPIENT’S TIN"),
        Plant("div.box1a", "2,400.00", "1a Total ordinary dividends", TAX),
        Plant("div.box1b", "1,900.00", "1b Qualified dividends", TAX),
        Plant("div.box2a", "310.00", "2a Total capital gain distr.", TAX),
        Plant("div.box2e_decoy", "77.00", "2e Section 897 ordinary dividends", TAX),
    ]


def sources_dir() -> Path | None:
    """The real-IRS-PDF directory (YTAX_IRS_SOURCES), or None when it is unset or absent."""
    return SOURCES if SOURCES is not None and SOURCES.is_dir() else None


def _draw_words(c: _rl_canvas.Canvas, page: pdftext.PageWords) -> None:
    """Re-draw a real page's words at their own coordinates (same mechanism redact.py rebuilds with)."""
    for w in page.words:
        size = w.size or 8.0
        c.setFont("Helvetica", size)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(w.x0, (page.height - w.bottom) + 0.207 * size, w.text + " ")


def _locate_anchor(page: pdftext.PageWords, anchor: str,
                   occurrence: int = 0) -> tuple[float, float] | None:
    """Where `anchor`'s own first word starts: (x0, line bottom), in the REAL text (U+2019 and all).

    The x is the ANCHOR's, not its line's, because a real form puts several labels on one line --
    Form 1040 line 8 is *"Your first name and middle initial | Last name | Your social security
    number"*. Left-aligning all three to the line would stack three values in one spot and measure
    a page nobody has.

    `occurrence` picks WHICH match, because a repeated label is not an ambiguity to resolve by
    order: a W-2G prints `City or town` for the payer and again for the winner, and taking the
    first put the winner's address in the payer's box.
    """
    needle = anchor.lower()
    seen = -1
    for _no, ws in sorted(page.lines().items()):
        text = " ".join(w.text for w in ws).lower()
        idx = text.find(needle)
        if idx == -1:
            continue
        seen += 1
        if seen < occurrence:
            continue
        consumed = 0
        for w in ws:                      # map the character offset back to the word that holds it
            nxt = consumed + len(w.text) + 1
            if nxt > idx:
                return w.x0, max(t.bottom for t in ws)
            consumed = nxt
        return ws[0].x0, max(t.bottom for t in ws)
    return None


def overlay_real_form(
    src: Path, out: Path, plants: list[Plant], *, page_index: int = 0,
) -> tuple[list[Plant], list[Plant]]:
    """Plant synthetic identity BELOW its real label on a real IRS page; write it to `out`.

    Returns `(placed, dropped)`. A plant whose anchor is not on the page is DROPPED and handed back
    so the caller can report it -- a corpus that quietly plants nothing measures nothing, and would
    report the resulting silence as a pass.
    """
    page = pdftext.load_page(src, page_index)
    c = _rl_canvas.Canvas(str(out), invariant=1)
    c.setPageSize((page.width, page.height))
    _draw_words(c, page)

    placed: list[Plant] = []
    dropped: list[Plant] = []
    for p in plants:
        spot = _locate_anchor(page, p.anchor, p.occurrence)
        if spot is None:
            dropped.append(p)
            continue
        # The real form's own geometry: the value goes in the box below its label, left-aligned to
        # it. One line height down clears the label without leaving the box.
        x, bottom = spot
        c.setFont("Helvetica", 9.0)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(x, page.height - bottom - p.drop, p.value + " ")
        placed.append(p)

    c.showPage()
    c.save()
    return placed, dropped


def k1_plants() -> list[Plant]:
    """Identity AND money on the real Schedule K-1 (1065), anchored to the form's own labels.

    Note what is NOT here: a "Partner's name" label. The real form has none -- it reads *"F Name,
    address, city, state, and ZIP code for partner entered in E."* The `synthetic.py` fixture's
    `Partner's name` line is an invention, and it is the only reason `partner's name` in
    `_PII_LABELS` ever matches anything.

    THE MONEY SIDE. The collector used to classify this form, run the two-pass redaction, and
    extract NOTHING -- so one box was planted here as the survival half of the bar. It now READS
    Part III boxes 1, 4a, 4b, 5, 6a and 7 (the six `k1.schema.json` can hold), and each has to hold up both
    halves: survive the redaction that removes the partner, and extract to its OWN figure.

    THE DECOYS. Part III stacks ~30 boxes in one narrow column, and three of them are planted with
    figures deliberately unlike ours: 6b *Qualified dividends* (one character from 6a, and the
    schema carries a single dividend field, so 6a's total is the one we read), 13 *Other deductions*
    and 14 *Self-employment earnings (loss)*. Reading one shows up as a WRONG value rather than as
    something indistinguishable. They are also money that redaction must not eat.

    **BOX 6b USED TO SCORE AS DESTROYED, and the corpus was right (closed).** Its label shares
    its line with *"E Partner's SSN or TIN (Do not use TIN of a disregarded entity. See
    instructions.)"*, 11.99pt apart against a 12pt `pdftext.GUTTER`, so the gutter rule called them
    ONE box, the partner-TIN burn's column ran to x=406, and the row beneath carried the TIN *and*
    box 6b's figure -- the burn took both, and `partner.tin` located as `000123456 8,222.00` was
    refused as `wrong-shape`. That hit was byte-identical with the extraction table declared and
    emptied, so declaring boxes did not cause it; it was the sub-gutter over-burn the W-2G unit
    recorded as unreachable, made reachable by planting money in Part III. Measuring the
    fix found the address label chained the same way into `6c Dividend equivalents`.
    `pdftext.column_for_label` now ends a column where the next box's HEADER begins; 6b survives,
    the TIN proposes, and `tests/test_k1_extraction.py::TheSubGutterOverBurnIsClosedTest` holds
    both chained labels on the real page. No box the collector READS (1/4a/4b/5/6a/7) ever shared a
    line with an identity label; that boundary is still pinned there.

    ⚠ **DECLARING THESE BOXES CHANGES THE REDACTOR**, which is not obvious and was nearly shipped
    undisclosed. `redact._money_labels()` reads `extract.FORM_FIELDS`, so every newly declared label
    is now a row `_is_label_row` refuses to burn. Swept with `locate_identity` over the same 922
    corpus pages: **4 pages changed, every one of them a Schedule K-1**, 6 rects lost and 2 gained,
    and each is a printed BOX LABEL that used to be burned as though it were the partner's address
    -- `partner.address` no longer takes `7 Royalties`, and on the pristine page it stops at the
    label row and lands on the next one instead. That is the same protection arriving for this form.
    Identity recall is unchanged at 20/20. `TheDeclarationChangesTheRedactorTooTest` pins it.
    """
    return [
        Plant("partner.ssn", ID_SSN_BARE, "Partner’s SSN or TIN"),
        Plant("partner.name", f"{ID_NAME_FIRST} {ID_NAME_LAST}",
              "Name, address, city, state, and ZIP code for partner"),
        Plant("partnership.ein", ID_EIN, "Partnership’s employer identification number"),
        # Box 1 sits in the same band as the Part II identity boxes: the survival side of the bar.
        Plant("k1.box1_ordinary_income", "12,000.00", "Ordinary business income (loss)", TAX),
        # boxes 4a/4b are declared now; planted in their own boxes like the others.
        Plant("k1.box4a_guaranteed_payments_services", "10,000.00",
              "Guaranteed payments for services", TAX),
        Plant("k1.box4b_guaranteed_payments_capital", "2,500.00",
              "Guaranteed payments for capital", TAX),
        Plant("k1.box5_interest_income", "1,500.00", "Interest income", TAX),
        Plant("k1.box6a_ordinary_dividends", "2,750.00", "Ordinary dividends", TAX),
        Plant("k1.box7_royalties", "640.00", "Royalties", TAX),
        Plant("k1.box6b_qualified_dividends_decoy", "8,222.00", "Qualified dividends", TAX),
        Plant("k1.box13_other_deductions_decoy", "7,333.00", "Other deductions", TAX),
        Plant("k1.box14_self_employment_decoy", "9,111.00",
              "Self-employment earnings (loss)", TAX),
    ]


def f1040_plants() -> list[Plant]:
    """Identity on the real Form 1040, whose label-above-value geometry is already documented by
    `scripts/derive_identity_fields.py` ("On Form 1040 the label sits ABOVE its box")."""
    return [
        Plant("primary.first_name", ID_NAME_FIRST, "Your first name and middle initial"),
        Plant("primary.last_name", ID_NAME_LAST, "Last name"),
        Plant("primary.ssn", ID_SSN_BARE, "Your social security number"),
        Plant("address.street", ID_STREET, "Home address (number and street)"),
    ]


def w2g_plants() -> list[Plant]:
    """Identity AND money on the real Form W-2G. The only SUPPORTED form with a real FORM pdf.

    It was carried as a generalisation probe while the collector refused this form -- identity only,
    one money plant, classified UNKNOWN. The collector now READS boxes 1 and 4, so the page has to
    hold up the other side of the bar too: the two declared boxes must survive redaction AND
    extract to their own figures, on geometry that is the IRS's rather than ours.

    THE DECOYS. Four boxes on this form say *winnings* -- 1, 7, 14, 16 -- and so does the title.
    Boxes 7 and 14 carry figures deliberately unlike boxes 1 and 4, so a label that matched the
    wrong box shows up as a WRONG VALUE rather than as something indistinguishable. They are also
    money that redaction must not eat, which is the same bar box 1 is held to.
    """
    return [
        Plant("winner.name", f"{ID_NAME_FIRST} {ID_NAME_LAST}", "WINNER’S name"),
        # Box 9 is the form's ACTUAL TIN box, and it was never on this page: the plant below it
        # anchors box 11, which holds a driver's-license number. Box 9 reads `WINNER’S TIN` -- no
        # `_IDENTITY_LABELS` entry matched that wording, and an undashed TIN escapes SSN_RE by
        # design, so the winner's SSN was the one identifier on a W-2G that nothing would burn.
        # Harmless while the form classified UNKNOWN and the pipeline emitted nothing; not harmless
        # now that it is read. The apostrophe is U+2019: `_locate_anchor` lowercases but does not
        # normalise, so an ASCII anchor silently plants nothing.
        Plant("winner.tin_box9", ID_SSN_BARE_2, "WINNER’S TIN"),
        # Box 11 is a driver's-licence number, not a TIN -- see `redact._IDENTITY_LABELS`. Still
        # identity, still must burn; it is only the TERM that was wrong.
        Plant("winner.identification_no", ID_SSN_BARE, "First identification no."),
        # `City or town` occurs twice -- the PAYER's block (line 7) and the WINNER's (line 23).
        # First-match put this plant in the payer's box, so the winner's own address box, which is
        # the taxpayer identity on this form, was never on the page. The second occurrence is the
        # winner's. (Its ZIP is also the value that showed the burn stopping at the label's gutter.)
        Plant("winner.city", ID_CITY_LINE, "City or town", occurrence=1),
        Plant("w2g.box1_reportable_winnings", "3,400.00", "Reportable winnings", TAX),
        Plant("w2g.box4_fed_withholding", "812.00", "Federal income tax withheld", TAX),
        Plant("w2g.box7_identical_wagers_decoy", "777.00", "Winnings from identical wagers", TAX),
        Plant("w2g.box14_state_winnings_decoy", "421.00", "State winnings", TAX),
    ]


def make_w2_real_layout(path: Path) -> list[Plant]:
    """A W-2 in the printed form's box layout, with the IRS's own box wording. RECONSTRUCTED.

    There is no real W-2 form PDF in `sources/` (only the W-2/W-3 *instructions*), so this is the
    one corpus member whose geometry is ours rather than the IRS's. What is not ours: the label
    strings, taken verbatim from those instructions. Three things the printed form does that
    `synthetic.py` does not -- each independently defeats a different part of the redactor:

      * box e reads "Employee's first name and initial", which does not contain "employee's name";
      * the value sits in the box BELOW its label, not after it on the same line;
      * box a prints the SSN without dashes, as payroll systems do.

    The apostrophes are U+2019, which is what every real IRS form uses.
    """
    c = _rl_canvas.Canvas(str(path), pagesize=(_PAGE_W, _PAGE_H), invariant=1)

    def label(x: float, y: float, text: str) -> None:
        c.setFont("Helvetica", 6.5)
        c.drawString(x, _PAGE_H - y, text)

    def value(x: float, y: float, text: str) -> None:
        c.setFont("Helvetica", 10)
        c.drawString(x, _PAGE_H - y, text + " ")

    label(72, 72, "a Employee’s social security number")
    value(72, 86, ID_SSN_BARE)
    label(72, 110, "b Employer identification number (EIN)")
    value(72, 124, ID_EIN)
    label(72, 148, "c Employer’s name, address, and ZIP code")
    value(72, 162, "Acme Widgets Inc")
    label(72, 200, "e Employee’s first name and initial          Last name          Suff.")
    value(72, 214, ID_NAME_FIRST)
    value(220, 214, ID_NAME_LAST)
    label(72, 238, "f Employee’s address and ZIP code")
    value(72, 252, ID_STREET)
    value(72, 266, ID_CITY_LINE)

    # Money boxes -- ALSO label-above-value, because that is where the printed form puts them, and
    # because it is the whole difficulty of this page: on a real W-2 the identity band and the box
    # 1-6 money column are the SAME horizontal band. A redactor that burns the band to catch the
    # name takes the wages with it, and the earlier corpus could not see that happen because it drew
    # these same-line.
    money = [
        ("1", "Wages, tips, other compensation", "48,250.00", "box1_wages"),
        ("2", "Federal income tax withheld", "5,310.00", "box2_fed_withholding"),
        ("3", "Social security wages", "48,250.00", "box3_ss_wages"),
        ("4", "Social security tax withheld", "2,991.50", "box4_ss_withholding"),
        ("5", "Medicare wages and tips", "48,250.00", "box5_medicare_wages"),
        ("6", "Medicare tax withheld", "699.63", "box6_medicare_withholding"),
    ]
    tax_plants: list[Plant] = []
    for i, (n, lab, amount, term) in enumerate(money):
        row = 72 + (i // 2) * 38
        col = 330 + (i % 2) * 130
        label(col, row, f"{n} {lab}")
        value(col, row + 14, amount)
        tax_plants.append(Plant(term, amount, lab, TAX))

    c.setFont("Helvetica", 9)
    c.drawString(72, _PAGE_H - 300, "Form W-2  Wage and Tax Statement  2025")
    # A bare digit run that must SURVIVE: the control for the module's deliberate choice not to
    # match bare digit runs (CUSIPs, lot numbers). Without it "burn everything" scores 100% recall.
    c.drawString(72, _PAGE_H - 320, "Reference 037833100 lot 000987654")
    c.showPage()
    c.save()

    return [
        Plant("employee.ssn", ID_SSN_BARE, "Employee’s social security number"),
        Plant("employee.first_name", ID_NAME_FIRST, "Employee’s first name and initial"),
        Plant("employee.last_name", ID_NAME_LAST, "Last name"),
        Plant("employee.street", ID_STREET, "Employee’s address and ZIP code"),
        Plant("employee.city_state_zip", ID_CITY_LINE, "Employee’s address and ZIP code"),
        Plant("control.bare_digits", "037833100", "Reference", TAX),
        *tax_plants,
    ]
