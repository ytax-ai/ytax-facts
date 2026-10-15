# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Declarative document->fact mapping tables and the forward transform.

Each supported form has a :class:`FormMapping`: the dictionary collection it populates and a
table of :class:`BoxMapping` rows (canonical neutral-IR label -> writable fact suffix). The
forward transform :func:`map_document` turns one neutral :class:`ExtractedDocument` into a
list of FG writable :class:`~collector.adapter.facts.Fact`, honouring **integer cents** and
**unknown-not-zero** (an absent or unparseable field emits nothing).

The canonical IR labels here are the adapter's *vocabulary*: the W-2 extractor already emits
them (``box1_wages`` ...); the other forms' extractors are extension points, so
their labels are defined here and the adapter tests drive synthetic IR using them.

Every ``suffix`` below resolves to a writable fact-path checked against the live dictionary by
``test_adapter_targets_are_all_writable`` and gate 3 — the mechanism that keeps these tables
bound to the real dictionary instead of drifting strings.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..ingest.models import ExtractedDocument, FormType, parse_money_cents
from . import facts
from .facts import Fact


class UnsupportedForm(ValueError):
    """The form type has no forward mapping (see :data:`UNSUPPORTED` for why)."""


@dataclass(frozen=True)
class BoxMapping:
    """One box/label -> writable suffix row.

    ``kind`` selects serialization: ``"dollar"`` (integer-cents Dollar) or ``"string"`` (a
    coded sub-box such as the 1099-R distribution code, kept verbatim — not interpreted).
    """

    label: str
    suffix: str
    kind: str = "dollar"
    note: str = ""


@dataclass(frozen=True)
class FormMapping:
    """One form's forward table.

    ``has_filer`` says whether the collection has a per-item ``filer`` fact to link. It is True for
    every form but the W-2G, whose collection in dictionary/ty2025 defines the collection and two
    Dollar writables and NOTHING else — the 1040 consumes only the two aggregate totals, each a
    ``CollectionSum`` over every item, so nothing on the federal return turns on whose W-2G it is.
    Emitting the linkage anyway would put a non-existent path into the FactSet, which is exactly
    what `test_every_mapping_suffix_is_writable` exists to stop.
    """

    form_type: FormType
    collection: str
    boxes: tuple[BoxMapping, ...]
    has_filer: bool = True


# --- W-2  (/formW2s) ----------------------------------------------------------
# Labels match the live extractor (collector/ingest/extract.py::_W2_BOXES).
W2 = FormMapping(
    FormType.W2,
    "/formW2s",
    (
        BoxMapping("box1_wages", "writableWages"),
        BoxMapping("box2_fed_withholding", "writableFederalWithholding"),
        BoxMapping("box3_ss_wages", "writableOasdiWages", note="Box 3 = Social Security wages"),
        BoxMapping("box4_ss_withholding", "writableOasdiWithholding"),
        BoxMapping("box5_medicare_wages", "writableMedicareWages"),
        BoxMapping("box6_medicare_withholding", "writableMedicareWithholding"),
    ),
)

# --- 1099-INT  (/interestReports) ---------------------------------------------
INT_1099 = FormMapping(
    FormType.F1099_INT,
    "/interestReports",
    (
        BoxMapping("box1_interest_income", "writable1099Amount"),
        BoxMapping("box2_early_withdrawal_penalty", "writableEarlyWithdrawlPenaltyAmount"),
        BoxMapping("box3_interest_us_savings_treasury", "writableInterestOnGovernmentBonds"),
        BoxMapping("box4_fed_withholding", "writableTaxWithheld"),
        BoxMapping("box6_foreign_tax_paid", "writableForeignTaxPaid"),
        BoxMapping("box8_tax_exempt_interest", "writableTaxExemptInterest"),
    ),
)

# --- 1099-DIV  (/dividendReports) ---------------------------------------------
# The dictionary declares the box 2a (total capital gain distributions) and box 4 (federal income tax
# withheld) writables in dictionary/ty2025/. Absent IR fields map to nothing (unknown-not-zero),
# so a 1099-DIV that carries neither box still emits only the box 1a/1b writables.
DIV_1099 = FormMapping(
    FormType.F1099_DIV,
    "/dividendReports",
    (
        BoxMapping("box1a_ordinary_dividends", "writableOrdinaryDividends"),
        BoxMapping("box1b_qualified_dividends", "writableQualifiedDividends"),
        BoxMapping("box2a_capital_gain_distributions", "writableCapitalGainDistributions"),
        BoxMapping("box4_fed_withholding", "writableFederalWithholding"),
    ),
)

# --- 1099-R  (/form1099Rs) ----------------------------------------------------
R_1099 = FormMapping(
    FormType.F1099_R,
    "/form1099Rs",
    (
        BoxMapping("box1_gross_distribution", "writableGrossDistribution"),
        BoxMapping("box2a_taxable_amount", "writableTaxableAmount"),
        BoxMapping("box4_fed_withholding", "writableFederalWithholding"),
        BoxMapping(
            "box7_distribution_code", "writableDistributionCode", kind="string",
            note="Coded sub-box: kept verbatim (e.g. '7', 'B'); not interpreted here.",
        ),
    ),
)

# --- W-2G  (/formW2Gs) --------------------------------------------------------
# Labels match the live extractor (collector/ingest/extract.py::FORM_FIELDS[FormType.W2G]).
# this table used to be an `UNSUPPORTED` entry reading "the service mapper still lists
# `w2gs` in UNSUPPORTED_STREAMS" — true when it was written, and false since the stream was covered
# on 2026-08-20. The two Dollar boxes are the whole of what the ty2025 dictionary models
# for this form: box 1 -> /w2gWinnings -> Schedule 1 line 8b, box 4 -> /w2gWithholding -> Form 1040
# line 25c. `has_filer=False` because `/formW2Gs/*` has no filer fact — see FormMapping.
W2G = FormMapping(
    FormType.W2G,
    "/formW2Gs",
    (
        BoxMapping("box1_reportable_winnings", "writableReportableWinnings"),
        BoxMapping("box4_fed_withholding", "writableFederalWithholding"),
    ),
    has_filer=False,
)

FORM_MAPPINGS: dict[FormType, FormMapping] = {
    m.form_type: m for m in (W2, INT_1099, DIV_1099, R_1099, W2G)
}

# Forms intentionally NOT mapped, with the dictionary reason. The adapter never emits a
# non-writable path to force coverage; each reason below says what is missing.
UNSUPPORTED: dict[FormType, str] = {
    FormType.F1099_B: (
        "No per-transaction or per-form 1099-B writable exists in dictionary/ty2025/. "
        "Schedule D exposes only aggregate /writableNetShortTermGainOrLoss and "
        "/writableNetLongTermGainOrLoss — not a box-level 1099-B mapping, and deriving them "
        "from proceeds/basis would be tax computation, which the adapter must not do."
    ),
    FormType.F1098: "Mortgage-interest intake is not in the adapter's scope.",
    FormType.K1_1065: (
        "The collector READS this form (Part III boxes 1, 4a, 4b, 5, 6a and 7), and there is deliberately "
        "no forward mapping: the service mapper still lists `k1s` in UNSUPPORTED_STREAMS because "
        "pass-through income is not in the adapter's scope, and an incomplete mapping under-reports. "
        "Reading a form is not covering it."
    ),
}


def map_document(ir: ExtractedDocument, instance_id: str, filer_id: str) -> list[Fact]:
    """Forward transform: one neutral document -> writable facts for one collection instance.

    Emits the ``filer`` linkage plus a Dollar/String fact per *present, parseable* box.
    Absent fields and unparseable money strings are skipped (unknown-not-zero). The caller
    owns the collection membership (see :func:`collector.adapter.forward.adapt`).
    """
    mapping = FORM_MAPPINGS.get(ir.form_type)
    if mapping is None:
        reason = UNSUPPORTED.get(ir.form_type, "no mapping defined")
        raise UnsupportedForm(f"{ir.form_type.value}: {reason}")

    base = f"{mapping.collection}/#{instance_id}"
    # The filer linkage is conditional: a collection with no per-item `filer` fact — the
    # W-2G's — must not be handed one, or the adapter emits a path the dictionary does not define.
    out: list[Fact] = ([facts.collection_item(f"{base}/filer", filer_id)]
                       if mapping.has_filer else [])

    for box in mapping.boxes:
        fld = ir.field_by_label(box.label)
        if fld is None:
            continue  # unknown-not-zero: field absent from this document
        path = f"{base}/{box.suffix}"
        if box.kind == "dollar":
            cents = fld.value_cents if fld.value_cents is not None else parse_money_cents(fld.value)
            if cents is None:
                continue  # unparseable money -> unknown, never a guessed zero
            out.append(facts.dollar(path, cents))
        elif box.kind == "string":
            value = fld.value.strip()
            if not value:
                continue
            out.append(facts.string(path, value))
        else:  # pragma: no cover - guards against a typo'd mapping table
            raise ValueError(f"unknown box kind {box.kind!r} for {box.label}")

    return out
