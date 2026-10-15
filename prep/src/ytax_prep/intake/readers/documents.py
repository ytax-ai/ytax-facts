# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Document reading — tiers into candidates.

A dropped PDF is classified (the Collector's own `classify`), then read tier by tier: an AcroForm
value the pin's own register maps to a service field (tier "field"), else the word geometry a
digital text layer gives `extract_declared` (tier "geometry"), else the same geometry read off an
OCR'd render (tier "ocr"), else — when a local model is given and a box is still unread — a vision
model prompted with the page image and the form's own captions (tier "model"). A box the exact
tier already read is never re-read by a lower tier.

Every value this module proposes is a `Candidate` needing confirmation; nothing here writes a
fact. What VALUE a candidate carries is exactly what `ytax_prep.client.documents._fields_of`
would carry for the same box (the two must never drift, because both feed the same fact schema):
money is `value_cents`, a code is upper-cased text matching `CODE_RE`, a check is `True`, and a box
the document reports BLANK is a stated `0` unless the box is a mark (absence is "unchecked", not a
candidate) or the box is in `BLANK_OMITS` (absence is not zero — see `documents.py`'s own note on
`box2a_taxable_amount`). A box the extractor never located, or a REQUIRED box the document reports
blank (`REQUIRED_LABELS`), proposes nothing at all: its caption is reported in `unread` instead, for
the loop to ask about later.

No redaction runs before reading on the client. Nothing here needs to exclude an
identity box by name — the label maps this module reads through (`FACT_GROUPS`) never include one
in the first place, and `Case.propose` refuses one by pattern if it ever somehow arrived.
"""
from __future__ import annotations

import functools
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from collector.ingest import pdftext as _pdftext
from collector.ingest.classify import classify
from collector.ingest.extract import (
    FORM_FIELDS,
    W2_BOX15_STATE_LABELS,
    _value_after_label,
    extract_declared,
    value_shaped,
)
from collector.ingest.models import FieldOutcome, FormType, parse_money_cents

from ..case import Candidate, Evidence
from ..registers import (BOX_FACT_OF, IDENTIFIER_TYPES, NEVER_DATA, BoxRegister, box_fact, boxes_for,
                         field_map)
from .ocr import OcrUnavailable, page_words
from ...client.documents import (
    BLANK_OMITS,
    CHECK,
    CODE,
    CODE_ENUMS,
    CODE_RE,
    FACT_GROUPS,
    FORM_CONSTANTS,
    LABEL_KINDS,
    MONEY,
    REQUIRED_LABELS,
)
from ...client.form_labels import label_for
from ...client.pdfform.reader import FormField, PdfSurprise, PdfTemplate
from ..._paths import data_root

_REPO_ROOT = data_root()


@functools.lru_cache(maxsize=1)
def _reachability() -> dict:
    return json.loads((_REPO_ROOT / "generated" / "reachability.json").read_text(encoding="utf-8"))


@dataclass
class ReadResult:
    document: str
    form_type: str
    group: str | None
    candidates: list[Candidate]
    unread: list[str]              # unread = service fields asked later, by caption
    unconsumed: str | None         # the reason, when the form has no fact group
    # Boxes the person can see a figure in that NO fact receives — the dictionary's own printed-box
    # register names them (INPUT-FORMS.md §k: a box the register does not carry is a declared gap,
    # kept out of the fact graph and TOLD to the person; never a guessed path, never a silent
    # drop). Named as `box 14, Other`; the value is not kept. Empty at a pin with no sidecar.
    not_carried: list[str] = field(default_factory=list)
    # Decided 2026-09-26: of `not_carried`, the boxes whose bound writable CAN reach
    # a served Form 1040 line (`reachability.box_reach`, the static reach), name -> those lines. A
    # declared gap with no fact is here with [] — whether it changes a line is not known, and it is
    # never presented as "stored only". A name not in this map is stored only at this pin.
    not_carried_lines: dict = field(default_factory=dict)
    # Where this read's box vocabulary came from: "sidecar" (the dictionary's `boxes.tsv`, the
    # reading contract) or "tables" (the collector's own declared spellings, the fallback).
    vocabulary: str = "tables"
    # W-2 box 15's two-letter state, lower case as the residence-state choices spell it (`ny`), and
    # where it was read. NOT a candidate: box 15 names the state the wages were reported to, not
    # where the person lived, so the loop only PROPOSES it as the residence-state answer, and only
    # when every document that names a state names this one. The employer's state ID beside it is
    # never kept: nothing but a two-letter postal code in the dictionary's list is ever accepted.
    work_state: str | None = None
    work_state_evidence: Evidence | None = None


@dataclass(frozen=True)
class BoxPlan:
    """One box the reader looks for on the page: which service field it fills, the spellings a
    payer may print for it, how its value is shaped, and (a code box) the values it accepts."""
    field: str                    # the bare service field, `wages_cents`
    spellings: tuple[str, ...]    # () = never searched on a page (unread, asked later)
    kind: str                     # MONEY / CODE / CHECK
    legend: frozenset             # a CODE box's accepted values; empty = the schema's own pattern


# The sidecar's fact type -> how this reader shapes the box's value. A type not named here is
# never read off a page: identifiers by rule, and the shapes this reader has no
# parser for yet (Int, Day) are left unread and asked in the interview, exactly as before.
_KIND_OF_TYPE = {"Dollar": MONEY, "Bool": CHECK, "Boolean": CHECK, "Enum": CODE, "String": CODE}


def _plans(form_type_value: str, group: str, mapping: dict, pdf_root: Path | None,
           ) -> tuple[list[BoxPlan], BoxRegister | None, list[str] | None]:
    """What to look for, and the vocabulary it came from.

    WITH a sidecar at the pin (`boxes.tsv`, INPUT-FORMS.md §b): each service field the collector
    reads for this group is joined to its printed box through the writable it becomes
    (`reachability.service_fields`) and the sidecar row bound to that writable; the row's spellings
    and its declared `type` drive the search; a service field the register binds no box to is a
    declared gap and is not read. The set of boxes read stays the collector's mapping — a box the
    sidecar carries for a service field the mapping does not name is NOT read yet, because what
    its blank means (a stated 0, or nothing) is a decision per box (`BLANK_OMITS`), not a rule.
    WITHOUT one: the collector's own tables, unchanged.

    Returns (plans, sidecar or None, the `known` spellings for the extractor's neighbour veto —
    None means "use the collector's tables' vocabulary")."""
    sidecar = boxes_for(form_type_value, pdf_root)
    form_type = FormType(form_type_value)
    table = FORM_FIELDS.get(form_type, {})
    if sidecar is None:
        return ([BoxPlan(fld, tuple(table.get(label, ())), LABEL_KINDS.get(label, MONEY),
                         frozenset(CODE_ENUMS.get(label, ())))
                 for label, fld in mapping.items()], None, None)
    writable_of = _reachability()["service_fields"]
    by_fact = sidecar.by_fact()
    plans = []
    for label, fld in mapping.items():
        row = by_fact.get(box_fact(form_type_value, group, fld, writable_of))
        if row is None:
            # The register binds NO box to this writable at this pin: the box is a declared gap
            # (§k), and the collector's own spelling for it is exactly the guessed path the
            # standard forbids. Unread here; the interview asks it in its own words.
            plans.append(BoxPlan(fld, (), LABEL_KINDS.get(label, MONEY), frozenset()))
            continue
        if row.type in IDENTIFIER_TYPES:
            plans.append(BoxPlan(fld, (), CODE, frozenset()))
            continue
        kind = _KIND_OF_TYPE.get(row.type or "")
        if kind is None:
            plans.append(BoxPlan(fld, (), LABEL_KINDS.get(label, MONEY), frozenset()))
            continue
        legend = frozenset(row.legend) if row.type == "Enum" else frozenset(CODE_ENUMS.get(label, ()))
        plans.append(BoxPlan(fld, row.match_spellings or row.spellings, kind, legend))
    return plans, sidecar, list(sidecar.labels)


def _not_carried(page, sidecar: BoxRegister, read_facts: set[str], known: list[str]) -> list[str]:
    return [row.named() for row in _not_carried_rows(page, sidecar, read_facts, known)]


def _lines_of(rows: list) -> dict:
    """#(a): the not-carried boxes that can change a served line, name -> lines (see ReadResult)."""
    reach = _reachability().get("box_reach", {})
    # A fact the mapper fills itself — an identity placeholder (`ENGINE_PLUMBING`: W-2 box c's
    # `employerName`, "employer identity may not cross") — is not a gap the person can close: the
    # figure on the paper is never used, so it is named with the stored-only boxes. Measured: without
    # this, box c was called line-changing on 19 of the 92 showcase W-2s.
    from ...facts.mapper import ENGINE_PLUMBING
    out = {}
    for row in rows:
        if row.fact in ENGINE_PLUMBING:
            continue
        lines = reach.get(row.fact) if row.fact else []
        if lines is None:
            lines = []                        # a fact the artifact does not know: not "stored only"
        if lines or not row.fact or row.fact not in reach:
            out[row.named()] = list(lines)
    return out


def _not_carried_rows(page, sidecar: BoxRegister, read_facts: set[str], known: list[str]) -> list:
    """The sidecar's boxes that NO fact receives — a declared gap (UNDECLARED, BLOCKED) or a writable
    no service field reaches (`read_facts`) — that the page shows a value in. Page furniture, identity cells and
    reserved boxes are skipped (never data, §k); identifier-typed boxes are never searched at all.
    Only the box's NAME is kept: the figure stays on the paper."""
    out = []
    for row in sidecar.rows:
        if not row.spellings or row.type in IDENTIFIER_TYPES or row.reason in NEVER_DATA:
            continue
        if row.fact and row.fact in read_facts:
            continue
        kind = _KIND_OF_TYPE.get(row.type or "", MONEY)
        _, outcome = _value_after_label(page, list(row.spellings), kind, known)
        if outcome == FieldOutcome.FOUND:
            out.append(row)
    return out


_TWO_LETTERS = __import__("re").compile(r"^[A-Za-z]{2}$")


def _work_state(page, document: str, known: list[str] | None) -> tuple[str | None, Evidence | None]:
    """W-2 box 15's state, or `(None, None)`. The box prints the state and the employer's state ID
    number side by side; the first token read is kept only when it is two letters naming one of the
    dictionary's jurisdictions (`mapper.RESIDENCE_STATES`). Anything else — an ID number read from
    a box whose state is blank, a stray word — is dropped whole, so no part of the ID reaches a
    value, an evidence field or anything served."""
    from ...facts.mapper import RESIDENCE_STATES
    found, outcome = _value_after_label(page, list(W2_BOX15_STATE_LABELS), CODE, known)
    if outcome != FieldOutcome.FOUND or found is None:
        return None, None
    text = found.value.strip()
    if not _TWO_LETTERS.match(text) or text.lower() not in RESIDENCE_STATES:
        return None, None
    rect = (found.source.x0, found.source.y0, found.source.x1, found.source.y1) if found.source else None
    page_no = found.source.page if found.source else 1
    return text.lower(), Evidence(document, page_no, "15 State", rect, text.upper(), "geometry")


def _typed_value(kind: str, raw: Any) -> Any:
    """One raw string, read as its box's KIND — the value a `Candidate` carries, never a display
    string. `None` means the text is not shaped like its kind and nothing should be proposed."""
    text = str(raw).strip()
    if kind == CODE:
        upper = text.upper()
        return upper if CODE_RE.match(upper) else None
    if kind == CHECK:
        # A mark box is read from a MARK (`X`, `[X]`, a ballot glyph — the collector's own set),
        # never from "some text sat there": measured on the 1099-R's box 2b, the word `Total` from
        # the neighbouring caption read as True. An AcroForm checkbox's on-state arrives as `X`.
        return True if value_shaped(CHECK, text) else None
    return parse_money_cents(raw)


def _acroform_value(template: PdfTemplate, ff: FormField) -> str | None:
    """The `/V` a filled AcroForm field carries, decoded the same way the template reader decodes
    any other PDF string (`PdfTemplate._t`'s own BOM rule) — `None` when the field was never
    filled in, or a button whose state is not its ON state."""
    d = template.resolve(ff.field_ref)
    if not isinstance(d, dict):
        return None
    v = d.get("/V")
    if v is None:
        return None
    if ff.field_type == "Btn":
        name = v.lstrip("/") if isinstance(v, str) else None
        return "X" if (ff.on_state and name == ff.on_state) else None
    if isinstance(v, bytes):
        if v[:2] == b"\xfe\xff":
            return v[2:].decode("utf-16-be")
        return v.decode("latin-1")
    return str(v)


def _read_field_tier(pdf: Path, form_type_value: str, group: str, kind_of: dict[str, str],
                      index: int, pdf_root: Path | None) -> tuple[list[Candidate], set[str]]:
    """AcroForm values -> candidates, tier "field". Empty whenever there is nothing to read this
    way: no pin to check a register against, no register for this form at the pin, no AcroForm on
    the page at all, or a register that maps nothing the pin's own PDF actually has filled in."""
    if pdf_root is None:
        return [], set()
    fm = field_map(form_type_value, Path(pdf_root), _reachability())
    if not fm:
        return [], set()
    try:
        template = PdfTemplate(pdf.read_bytes())
    except PdfSurprise:
        return [], set()

    prefix = f"{group}[]."
    candidates: list[Candidate] = []
    resolved: set[str] = set()
    for dotted, service_field in fm.items():
        if not service_field.startswith(prefix):
            continue
        bare = service_field[len(prefix):]
        if bare not in kind_of:
            continue
        formfield = template.fields.get(dotted)
        if formfield is None:
            continue
        raw = _acroform_value(template, formfield)
        if not raw:
            continue
        value = _typed_value(kind_of[bare], raw)
        if value is None:
            continue
        path = f"{group}[{index}].{bare}"
        evidence = Evidence(pdf.name, 1, label_for(group, bare), None, raw, "field")
        candidates.append(Candidate(path, value, evidence))
        resolved.add(bare)
    return candidates, resolved


def _cached_ocr(pdf: Path, cache: dict) -> Any:
    """`page_words(pdf)`, run at most once per document: `classify`'s OCR hook and the tier-2/3
    reader both want a scanned page's OCR, and running RapidOCR twice over the same page for one
    document would double the cost for nothing new."""
    if "page" not in cache:
        cache["page"] = page_words(pdf)
    return cache["page"]


def _classify_ocr_backend(pdf: Path, cache: dict) -> str:
    """`classify`'s OCR hook, for a scanned page 1: the same OCR tier this module reads boxes
    through, so a document with no text layer still identifies itself. `""` (never raised) when
    OCR is not available here — `classify` then reports UNKNOWN with its own "no text layer and
    OCR returned nothing" warning, exactly as it would with no backend at all.

    Rebuilt line by line, not `PageWords.text` (one space-joined string): `classify._title_block`
    keeps only the page's first and last few LINES as the title block, and a one-line page reads
    as "all chrome" — the multi-form-mention refusal `classify` exists to run never gets the
    chance to see a body it should have excluded."""
    try:
        page = _cached_ocr(pdf, cache)
    except OcrUnavailable as why:
        # measured 2026-09-17: in the FROZEN Windows bundle this fires and a scanned document was
        # named only "could not be classified" — the reason has to reach the person, and the page
        # says it, or nobody can tell a bad scan from a reader that is not there at all
        cache["ocr_unavailable"] = str(why)
        return ""
    lines = page.lines()
    return "\n".join(" ".join(w.text for w in lines[key]) for key in sorted(lines))


def _tier23_page(pdf: Path, cache: dict):
    """The page for tier "geometry" or tier "ocr", and which one it was — `(None, None)` when
    there is no text layer AND OCR is not available in this interpreter."""
    page = _pdftext.load_page(pdf, 0)
    if page.text.strip():
        return page, "geometry"
    try:
        return _cached_ocr(pdf, cache), "ocr"
    except OcrUnavailable as why:
        cache["ocr_unavailable"] = str(why)
        return None, None


def _render_png(pdf: Path, dpi: int = 200) -> bytes:
    """Page 1, rendered for the model tier. Only ever called when a model was actually given —
    `pypdfium2` (already a `pdfplumber` dependency) is imported here, not at module scope."""
    import io

    import pypdfium2 as pdfium

    with pdfium.PdfDocument(str(pdf)) as doc:
        page = doc[0]
        image = page.render(scale=dpi / 72).to_pil().convert("RGB")
        page.close()
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _unconsumed_reason(form_type: FormType, warning: str | None, ocr_unavailable: str | None = None) -> str:
    if form_type is FormType.UNKNOWN:
        reason = "the document could not be classified into a supported form"
        if warning:
            reason += f" ({warning})"
        if ocr_unavailable:
            # a page with no text layer, and no reader to read the picture: say which, so the
            # answer is "this copy needs a reader that works here", not "this form is unknown"
            reason += (f". This document has no text layer, and the reader that reads a scan "
                       f"cannot run here: {ocr_unavailable}")
        return reason + "."
    return (f"a {form_type.value} was recognised but this client has no fact group for it. "
            f"Its figures are never carried.")


def _constant_candidates(document: str, group: str, index: int, form_type_value: str) -> list[Candidate]:
    """`FORM_CONSTANTS` for this form type, as candidates — a fact the document declares by being
    the form it is (K-1 `source`: which entity's Schedule K-1 this is), not one it prints in a box.

    This used to be applied only on the OTHER document-reading path
    (`client.documents._new_item`), never on this tiered reader — so `source` fell through to an
    open interview question, asked per `k1s[]` INDEX with no way to tie it back to which physical
    document produced that index. Answering it from a profile's own array order (the only thing
    available to answer it FROM) is exactly how a reader item ended up carrying one K-1's money
    boxes and a different K-1's entity type: nothing but position linked the two, and nothing
    requires read order to match any array order a profile happens to use. Proposing it here, at
    the SAME index this document's own money-box candidates use, ties an item's identity to its
    own document instead of to whatever position it happened to arrive in.
    """
    return [
        Candidate(f"{group}[{index}].{field}", value,
                  Evidence(document, 1, label_for(group, field), None, str(value), "field"))
        for field, value in FORM_CONSTANTS.get(form_type_value, {}).items()
    ]


def read_document(pdf: Path, index: int, model=None, pdf_root: Path | None = None) -> ReadResult:
    """One document, read tier by tier into candidates. `index` is this document's position
    within its fact group — the second W-2 in a batch is `index=1`, and every candidate's path is
    built from it (`w2s[1].wages_cents`), matching exactly how `client.documents` numbers a batch.
    """
    pdf = Path(pdf)
    ocr_cache: dict = {}
    form_type, warning = classify(pdf, ocr=lambda p: _classify_ocr_backend(p, ocr_cache))
    form_type_value = form_type.value
    document = pdf.name

    if form_type_value not in FACT_GROUPS:
        return ReadResult(document=document, form_type=form_type_value, group=None,
                          candidates=[], unread=[],
                          unconsumed=_unconsumed_reason(form_type, warning,
                                                        ocr_cache.get("ocr_unavailable")))

    group, mapping = FACT_GROUPS[form_type_value]
    plans, sidecar, known = _plans(form_type_value, group, mapping, pdf_root)
    kind_of = {p.field: p.kind for p in plans}
    legend_of = {p.field: p.legend for p in plans}
    required = {mapping[label] for label in REQUIRED_LABELS.get(form_type_value, ()) if label in mapping}
    blank_omits = {mapping[label] for label in BLANK_OMITS if label in mapping}

    candidates, resolved = _read_field_tier(pdf, form_type_value, group, kind_of, index, pdf_root)
    candidates.extend(_constant_candidates(document, group, index, form_type_value))
    pending: set[str] = set()
    not_carried: list[str] = []
    not_carried_lines: dict = {}

    page, tier_name = (None, None)
    if len(resolved) < len(plans) or sidecar is not None or form_type_value == "W-2":
        page, tier_name = _tier23_page(pdf, ocr_cache)   # a W-2's box 15 is only read off the page
    work_state, work_state_evidence = (None, None)

    if page is not None:
        table = {p.field: list(p.spellings) for p in plans if p.spellings}
        fields, reports = extract_declared(page, form_type, table, kind_of, known)
        by_field = {f.label: f for f in fields}
        outcomes = {r.label: r.outcome for r in reports}
        for p in plans:
            fact = p.field
            if fact in resolved:
                continue
            outcome = outcomes.get(fact)
            if outcome == FieldOutcome.FOUND:
                f = by_field[fact]
                if p.kind == MONEY:
                    value = f.value_cents if (isinstance(f.value_cents, int)
                                              and not isinstance(f.value_cents, bool)) else None
                else:
                    value = _typed_value(p.kind, f.value)
                    if value is not None and p.kind == CODE and p.legend and value not in p.legend:
                        value = None      # a code the box's own legend does not list: ask, never send
                if value is None:
                    pending.add(fact)
                    continue
                rect = (f.source.x0, f.source.y0, f.source.x1, f.source.y1) if f.source else None
                page_no = f.source.page if f.source else 1
                evidence = Evidence(document, page_no, label_for(group, fact), rect, f.value, tier_name)
                candidates.append(Candidate(f"{group}[{index}].{fact}", value, evidence))
                resolved.add(fact)
            elif outcome == FieldOutcome.EMPTY:
                if fact in required:
                    pending.add(fact)
                else:
                    if p.kind == MONEY and fact not in blank_omits:
                        evidence = Evidence(document, 1, label_for(group, fact), None, "", tier_name)
                        candidates.append(Candidate(f"{group}[{index}].{fact}", 0, evidence))
                    resolved.add(fact)
            else:
                pending.add(fact)
        if form_type_value == "W-2":
            work_state, work_state_evidence = _work_state(page, document, known)
            if work_state_evidence is not None and tier_name != "geometry":
                e = work_state_evidence
                work_state_evidence = Evidence(e.document, e.page, e.caption, e.rect, e.raw, tier_name)
        if sidecar is not None:
            # "No fact receives it" means NO service field reaches the writable at all — not
            # merely none the collector reads off this form. A box whose writable the interview
            # asks for later (the 1099-R's box 8, `other_cents`) is read-later, not unused, and
            # naming it here would contradict the question that follows.
            # …and a box `BOX_FACT_OF` joins to its service field (the 1041 K-1's, a 1099-B's
            # box 1g) is read too, by that join, though its own writable is never sent.
            read_facts = (set(_reachability()["service_fields"].values())
                          | {fact for (ft, _f), fact in BOX_FACT_OF.items()
                             if ft == form_type_value})
            carried_rows = _not_carried_rows(page, sidecar, read_facts, known or [])
            not_carried = [row.named() for row in carried_rows]
            not_carried_lines = _lines_of(carried_rows)
    else:
        for p in plans:
            if p.field not in resolved:
                pending.add(p.field)

    if model is not None and pending:
        try:
            from .model import read_with_model
        except ImportError:
            read_with_model = None
        if read_with_model is not None:
            captions = {fact: label_for(group, fact) for fact in pending}
            png = _render_png(pdf)
            for fact, raw in read_with_model(png, form_type_value, captions, model):
                if fact not in pending:
                    continue
                value = _typed_value(kind_of[fact], raw)
                if value is not None and kind_of[fact] == CODE and legend_of[fact] and value not in legend_of[fact]:
                    value = None
                if value is None:
                    continue
                evidence = Evidence(document, 1, label_for(group, fact), None, str(raw), "model")
                candidates.append(Candidate(f"{group}[{index}].{fact}", value, evidence))
                resolved.add(fact)
                pending.discard(fact)

    unread = [label_for(group, fact) for fact in pending]
    return ReadResult(document=document, form_type=form_type_value, group=group,
                      candidates=candidates, unread=unread, unconsumed=None,
                      not_carried=not_carried,
                      not_carried_lines=not_carried_lines,
                      vocabulary="sidecar" if sidecar is not None else "tables",
                      work_state=work_state, work_state_evidence=work_state_evidence)
