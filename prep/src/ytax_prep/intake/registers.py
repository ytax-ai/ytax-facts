# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Field names to service fields — build's per-form field register, inverted.

`ytax_prep.client.pdfform.registers.read_register` reads one register: dotted AcroForm
field name -> a raw register value, most often an engine writable path
(`/formW2Gs/*/writableFederalWithholding`). `generated/reachability.json`'s `service_fields` maps
the other direction, service field -> writable (`w2gs[].federal_withholding_cents ->
/formW2Gs/*/writableFederalWithholding`). Composing register-field -> writable -> service field
gives an intake reader the one thing it needs: which AcroForm box, if filled, tells us a service
fact — without ever routing through an identity-shaped writable (those never appear in
`service_fields` at all) or a writable two service fields could mean (excluded below).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ..client.pdfform.registers import read_register

# Collector form type (as the collector names it) -> build's register key
# (`dictionary/pdf/<year>/<key>/en/configuration.yml`). Some of these registers don't exist yet
# at any given pin — `field_map` reports that as None rather
# than guessing.
INTAKE_FORM_KEYS: dict[str, str] = {
    "W-2": "IRSW2",
    "W-2G": "IRSW2G",
    "1099-R": "IRS1099R",
    "1099-INT": "IRS1099INT",
    "1099-DIV": "IRS1099DIV",
    "1099-OID": "IRS1099OID",
    "1099-B": "IRS1099B",
    "K-1 (1065)": "IRS1065SK1",
    "K-1 (1120-S)": "IRS1120SSK",   # the pin's own register key
    "K-1 (1041)": "IRS1041SK1",     # the pin's own register key
    "1099-G": "IRS1099G",
    "1099-MISC": "IRS1099MISC",
    "1099-SA": "IRS1099SA",
    "SSA-1099": "IRSSSA1099",
    "1095-A": "IRS1095A",
}

# The printed box's OWN register fact, where that is not the writable the service field becomes.
# A box normally joins to its service field through one fact: the sidecar binds the box to a
# writable, and `reachability["service_fields"]` says which service field becomes that writable.
# That join breaks where build binds the box to a DOCUMENT collection and the service field becomes
# a computation-side fact instead — measured on the pinned engine:
# one service group read from three forms (`k1s`: the 1041 K-1's boxes are `/form1041K1s` leaves,
# the rename table's row is the 1065's `/formK1s`), Form 1099-SA (`/form1099Sas`, sent as
# `/hsaDistributions`), and Form 1099-MISC box 2 (`/form1099Miscs/*/writableRoyalties`, sent as the
# return-level `/writableRoyaltyIncome`). Unjoined, the reader took each for a declared gap and left
# the box unread: profile-estate-trust lost its box 6 and the return went Incomplete. Each entry
# says only "this printed box is this service field" — what the collector's label table said.
BOX_FACT_OF: dict[tuple[str, str], str] = {
    ("K-1 (1041)", "interest_income_cents"): "/form1041K1s/*/writableBox1InterestIncome",
    ("K-1 (1041)", "dividend_income_cents"): "/form1041K1s/*/writableBox2aOrdinaryDividends",
    ("K-1 (1041)", "qualified_dividends_cents"): "/form1041K1s/*/writableBox2bQualifiedDividends",
    ("K-1 (1041)", "ordinary_business_income_cents"):
        "/form1041K1s/*/writableBox6OrdinaryBusinessIncome",
    ("1099-MISC", "royalties_cents"): "/form1099Miscs/*/writableRoyalties",
    # Form 1099-OID's FATCA mark: the mapper never SENDS it (a checked box is refused by name), so
    # reachability has no row for it — but the box has to be read for that refusal to happen.
    ("1099-OID", "fatca_filing_requirement"):
        "/originalIssueDiscountReports/*/writableFatcaFilingRequirement",
    # Form 1099-B's refused boxes: never sent (a figure or a mark is refused by name), so
    # reachability has no row for them — but each has to be read for its refusal to happen.
    ("1099-B", "accrued_market_discount_cents"):
        "/form8949Transactions/*/writableForm1099BAccruedMarketDiscount",
    ("1099-B", "federal_withholding_cents"):
        "/form8949Transactions/*/writableForm1099BFederalWithholding",
    ("1099-B", "loss_not_allowed"): "/form8949Transactions/*/writableForm1099BLossNotAllowed",
    # Box 1g is sent as Form 8949 column (g) (`writableAdjustmentAmount`, code W); build binds the
    # printed box to its own per-form slot.
    ("1099-B", "wash_sale_loss_disallowed_cents"):
        "/form8949Transactions/*/writableForm1099BWashSaleLossDisallowed",
    ("1099-SA", "gross_distribution_cents"): "/form1099Sas/*/writableGrossDistribution",
    ("1099-SA", "hsa_distribution_code"): "/form1099Sas/*/writableDistributionCode",
}


def box_fact(form_type: str, group: str, field: str, service_fields: dict) -> str:
    """The register fact the printed box of `field` on `form_type` is bound to, "" when none."""
    return (BOX_FACT_OF.get((form_type, field))
            or service_fields.get(f"{group}[].{field}", ""))


def writable_to_service(reachability: dict) -> dict[str, str]:
    """Invert `reachability["service_fields"]` (service field -> writable) to writable -> service
    field.

    A `(role=primary|spouse)` (or `(role=dependent)`) annotated key is dropped outright — usually
    it names the same writable as a plain key elsewhere in the map, for a specific person role
    (`persons[].tin_type (role=dependent)` is the one exception with no plain twin, but it stays
    excluded on the same rule: the annotation says a reader still can't use it unconditionally). A
    writable left ambiguous even after that — e.g. `dateOfBirth` reached by both
    `persons[].birth_month` and `persons[].birth_year`, `isBlind` reached by both a person field
    and `spouse_is_blind` — is dropped too: a filled box alone can't say which fact it means.
    """
    plain = {service: writable for service, writable in reachability["service_fields"].items()
              if "(role=" not in service}
    counts: dict[str, int] = {}
    for writable in plain.values():
        counts[writable] = counts.get(writable, 0) + 1
    return {writable: service for service, writable in plain.items() if counts[writable] == 1}


def field_map(form_type: str, pdf_root: Path, reachability: dict) -> dict[str, str] | None:
    """Dotted AcroForm field name -> service field, for one collector form type at this pin.

    None when the form has no register yet at this pin, or its register maps no field to a
    service field (an all-gap register, e.g. IRS1065SK1's hand-review backlog)."""
    form_key = INTAKE_FORM_KEYS.get(form_type)
    if form_key is None:
        return None
    config_path = Path(pdf_root) / form_key / "en" / "configuration.yml"
    if not config_path.is_file():
        return None
    register = read_register(config_path)
    inverse = writable_to_service(reachability)
    mapped = {field: inverse[raw] for field, raw in register.mappings.items() if raw in inverse}
    return mapped or None


# ---------------------------------------------------------------------------------------------
# The printed-box sidecar — the reading contract (dictionary INPUT-FORMS.md §b, §k, 2026-09-14)

# `configuration.yml` is keyed by the IRS fillable PDF's AcroForm field id. A taxpayer's own
# document — a payroll substitute, a broker's consolidated 1099, a phone scan — has no such id; a
# reader has a box number and a printed caption. So build generates, beside every register,
# `boxes.tsv`: ONE ROW PER PRINTED BOX, copies collapsed, with the caption, the accepted spellings,
# the bound fact, its dictionary type, an enumerated box's legend, and for a gap its reason token.
# The reader takes captions, spellings, types and legends from HERE and owns nothing about the
# paper. At a pin that carries no sidecar for a form, `boxes_for` is None and the reader falls back
# to the collector's declared tables (`collector.ingest.extract.FORM_FIELDS`), which the standard
# retires.

# The standard has a `row` column: one printed box can hold
# several rows — a W-2's box 12a is Code and Amount — and `box + row` is what identifies a reading.
# It is exactly the fix for the aliases-keyed-on-box-number collisions found in
# development. A sidecar whose columns differ from the standard's is still refused rather than
# read by position.
SIDECAR_COLUMNS = ("box", "row", "caption", "aliases", "fields", "fact", "type", "legend", "reason")
# A printed box id as the standard defines it: a number with an optional letter (`1`, `12a`), or a
# letter (`e`). Anything else in the column is an emitter slug, shown to nobody as a box number.
_PRINTED_BOX = __import__("re").compile(r"^(?:\d{1,2}[a-zA-Z]?|[a-zA-Z])$")
# What the sidecar writes for an unnumbered box (the standard's §b table says `-`; the emitter
# writes an em dash); both read as "no number".
_NO_BOX = {"", "-", "—"}
# Gap reason tokens a reader treats as "never data" (§k): page furniture, an identity cell, a box
# the instructions reserve. Any other reason (UNDECLARED, BLOCKED) is a box the dictionary has not
# modelled yet — still a declared gap, but one a person may see a figure in.
NEVER_DATA = frozenset({"STRUCTURAL", "IDENTITY", "RESERVED"})
# Types a reader never reads off a page: identifiers (no identifier fields, ever).
IDENTIFIER_TYPES = frozenset({"EIN", "TIN"})


@dataclass(frozen=True)
class BoxRow:
    box: str                      # "" for an unnumbered box
    row: str                      # the row's position within its box, "" when the box has one row
    caption: str                  # the printed caption, for a person to read
    spellings: tuple[str, ...]    # what a reader may match this box by, lower case; () = never searched
    fields: tuple[str, ...]       # the AcroForm ids that are this box, as the sidecar spells them
    fact: str | None              # the bound writable, None for a declared gap
    type: str | None              # Dollar / Bool / Enum / String / Int / Day / EIN / TIN, as written
    legend: tuple[str, ...]       # an enumerated box's accepted values, empty when none stated
    reason: str | None            # a gap's reason token
    # the spellings the READING PLAN may search — pass 1's survivors, without pass 2. The
    # extractor skips a line where the match sits inside a longer known label, so a caption that is
    # the start of another box's (`bond premium`, 1099-INT box 11) is safe to search. `spellings`
    # keeps pass 2 for the not-read notice, which would otherwise name `box 15, State` on every W-2
    # (measured: 39 profiles). Empty = the same as `spellings`.
    match_spellings: tuple[str, ...] = ()

    def named(self) -> str:
        """How a report names this box to a person: `box 7, Distribution code(s)`. The standard
        keys `box` to the PRINTED number or letter; an emitter slug (`payer-name`, `account`) is not
        something a person can find on the paper, so such a row is named by its caption alone."""
        return f"box {self.box}, {self.caption}" if _PRINTED_BOX.match(self.box) else self.caption


@dataclass(frozen=True)
class BoxRegister:
    form_key: str
    rows: tuple[BoxRow, ...]
    # EVERY spelling the sidecar states for this form, usable or not: the extractor's veto that a
    # token beside a box is a neighbour's caption and not this box's value must know every caption
    # on the page, including one the collision rule made unusable for MATCHING. Measured: with
    # `total distribution` dropped from the veto, the 1099-R's box 2b mark read as True from the
    # word `Total` that begins the next caption.
    labels: tuple[str, ...] = ()

    def by_fact(self) -> dict[str, BoxRow]:
        return {r.fact: r for r in self.rows if r.fact}


def _spellings(rows: list[tuple[BoxRow, tuple[str, ...]]]) -> list[BoxRow]:
    """Settle each row's usable spellings under one rule: A SPELLING THAT COULD NAME TWO BOXES
    NAMES NEITHER. The candidates are the sidecar's aliases, then the caption itself.

    Pass 1 — a spelling two rows carry is dropped from both. The emitter keys its aliases on the
    box NUMBER, so the two checkboxes printed as box 2b on a 1099-R both carried `2b taxable
    amount not determined`; matching it would bind the wrong fact.
    Pass 2 — a spelling that sits inside another row's SURVIVING spelling is dropped: `total
    distribution` is inside `your percentage of total distribution`, and a line search finds
    whichever prints first. Only survivors count, so a shared alias dropped in pass 1 does not
    also take the caption beneath it (box 7's `distribution code(s)` stays readable).
    The row is kept either way — a box with no spelling left is reported, never searched."""
    owners: dict[str, set[int]] = {}
    for i, (_, cands) in enumerate(rows):
        for s in cands:
            owners.setdefault(s, set()).add(i)
    unique = {s: next(iter(o)) for s, o in owners.items() if len(o) == 1}
    out = []
    for i, (row, cands) in enumerate(rows):
        survivors = tuple(s for s in cands if unique.get(s) == i)
        keep = tuple(s for s in survivors
                     if not any(s != o and s in o and j != i for o, j in unique.items()))
        out.append(BoxRow(row.box, row.row, row.caption, keep, row.fields, row.fact, row.type,
                          row.legend, row.reason, match_spellings=survivors))
    return out


def read_boxes(path: Path) -> BoxRegister:
    """Parse one `boxes.tsv`. Comment lines (`#`) are the header prose; the first data line names
    the columns, in the standard's order, and a sidecar whose columns differ is refused rather
    than read by position."""
    path = Path(path)
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        raise ValueError(f"{path}: no rows")
    reader = csv.DictReader(lines, delimiter="\t", quoting=csv.QUOTE_NONE)
    if tuple(reader.fieldnames or ()) != SIDECAR_COLUMNS:
        raise ValueError(f"{path}: columns {reader.fieldnames} are not {list(SIDECAR_COLUMNS)}")
    rows: list[tuple[BoxRow, tuple[str, ...]]] = []
    for rec in reader:
        box = (rec["box"] or "").strip()
        within = (rec["row"] or "").strip()
        caption = (rec["caption"] or "").strip()
        aliases = [a.strip().lower() for a in (rec["aliases"] or "").split("|") if a.strip()]
        candidates: list[str] = []
        for s in (*aliases, caption.lower()):
            if s and s not in candidates:
                candidates.append(s)
        row = BoxRow(
            box="" if box in _NO_BOX else box,
            row=within,
            caption=caption,
            spellings=(),
            fields=tuple(f.strip() for f in (rec["fields"] or "").split("|") if f.strip()),
            fact=(rec["fact"] or "").strip() or None,
            type=(rec["type"] or "").strip() or None,
            legend=tuple(v.strip() for v in (rec["legend"] or "").split(";") if v.strip()),
            reason=(rec["reason"] or "").strip() or None,
        )
        rows.append((row, tuple(candidates)))
    labels = tuple(dict.fromkeys(s for _, cands in rows for s in cands))
    return BoxRegister(form_key=path.parent.parent.name, rows=tuple(_spellings(rows)), labels=labels)


def pin_pdf_root(engine_home=None) -> Path | None:
    """The pinned dictionary's `pdf/<year>` tree on THIS computer — where build's printed-box lists
    (`boxes.tsv`) sit beside the registers the fill already reads — or None when there is no
    engine home here or it carries no such tree. The ONE place the root is derived (the running
    page reads with build's lists), so the page, a restored session and the corpus
    read with the same vocabulary. None means the reader's own tables, as before.

    NOT checked here: that the engine home is the PINNED bytes (`EnginePin.matches_pin` hashes the
    whole dictionary and checks the engine it was built with, and a loop is built on every start, restore and start-again).
    The bound on a mismatch is small and already enforced elsewhere: another dictionary's
    spellings find fewer boxes, which are then ASKED, and compute and fill refuse a home that is
    not the pin."""
    from ..engine import EngineNotAvailable
    from ..engine.adapter import discover_pin
    try:
        dict_dir = Path(discover_pin(engine_home).dict_dir)
    except EngineNotAvailable:
        return None
    root = dict_dir.parent.parent / "dictionary" / "pdf" / "2025"
    return root if root.is_dir() else None


def boxes_for(form_type: str, pdf_root: Path | None) -> BoxRegister | None:
    """The sidecar for one collector form type at this pin, or None when the pin carries none —
    the reader then falls back to its declared tables and nothing served moves."""
    if pdf_root is None:
        return None
    form_key = INTAKE_FORM_KEYS.get(form_type)
    if form_key is None:
        return None
    path = Path(pdf_root) / form_key / "en" / "boxes.tsv"
    if not path.is_file():
        return None
    return read_boxes(path)
