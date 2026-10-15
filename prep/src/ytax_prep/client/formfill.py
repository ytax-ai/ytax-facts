# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The client workflow's LAST task: fill the pinned IRS forms with the computed
return.

`fill_return(facts, out_dir, ...)` resolves the case against the LOCAL pinned engine (the
engine runs on the client's machine), selects every form whose register gate resolves
Complete/true, and writes each template with the values the resolve produced — the SAME resolve
the served lines come from, so the number in a box is the number the person just reviewed on the
`Computed return` tab.

Two value planes, never mixed (spec §2):

* the ENGINE plane — amounts, checkboxes, enums, straight from the resolved facts. The engine
  call carries the SYNTHETIC placeholder identity, so an identity-shaped field is structurally
  barred from this plane, and a final sweep refuses any placeholder literal in the output.
* the IDENTITY plane — the eleven Form 1040 identity boxes named by
  `generated/identity_fields_f1040_ty2025.json`, filled ONLY from the person's local identity
  file (confirmed values). With no identity file they stay BLANK, and the report says so.

Everything not written is a STATED blank with its reason — never an omission.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree

from . import identity_file, notations
from .pdfform.reader import PdfSurprise, PdfTemplate
from .pdfform.registers import FormRegister, read_all, form_kinds
from .pdfform.writer import fill_fields
from ..engine.adapter import EngineAdapter, discover_pin
from ..facts import map_to_engine  # noqa: F401  (kept for importers)
from ..facts.extras import map_with_extras
from ..facts import mapper
from ..service.lines import LINE_MAP

# The service's own acceptance rule for a SERVED line (operations._cited_lines): Complete or
# Placeholder both carry the value it cites. The box on the printed form must show the same
# number the `Computed return` tab showed, so served facts use the served rule; every OTHER fact
# stays Complete-only — a placeholder on a box the service never serves is a stated blank.
_SERVED_PATHS = frozenset(spec["fact_path"] for spec in LINE_MAP)
_LINE_BY_PATH = {spec["fact_path"]: spec["line_id"] for spec in LINE_MAP}


class FillRefused(ValueError):
    """The fill may not proceed, and the sentence says why — a review that has not happened, a
    review that no longer matches, or an engine home that is not the pin."""

# Identity-SHAPED tokens: a mapped fact whose path carries one of these and is not on the
# identity plane is refused into a stated blank rather than engine-filled — fail closed, because
# the engine plane holds placeholders for exactly these shapes. (`otherFormName` — a form-number
# write-in — is swept up too; a stated blank for a box we never fill is the safe false positive.)
# `/payer$`: a payer's NAME on Schedule B's rows — identity the service synthesises,
# never a fill value; the row's amount beside it is filled.
_IDENTITY_TOKENS = re.compile(
    r"name|tin\b|address|email|phone|occupation|pin\b|signature|dateofdeath|identityprotection|/payer$",
    re.IGNORECASE)

# Placeholder literals that must never appear in a written value (mapper's synthetic
# identity). The serial is per-person since the TIN revision, so the sweep is on
# the area-group PREFIX. Two shapes, matched differently on purpose: the dashed prefix is a
# plain substring (a dash cannot appear in a dollar amount), but the undashed form is anchored
# to NINE CONSECUTIVE DIGITS — a bare five-digit prefix would refuse a legitimate amount that
# happens to carry it ("89900.00" contains "89900"; wages of $89,900 are not a leaked TIN).
_PLACEHOLDER_LITERALS = tuple(
    "-".join(t) + "-" for t in mapper._SYNTH_TIN.values()) + ("Synthetic",)
_PLACEHOLDER_TIN_RE = re.compile(
    "(?<![0-9])(" + "|".join(sorted({"".join(t) for t in mapper._SYNTH_TIN.values()}))
    + r")[0-9]{4}(?![0-9])")


@dataclass
class FormFill:
    form_key: str
    out_path: Path | None            # None when nothing was written for this form
    written: dict = field(default_factory=dict)     # dotted field -> value written
    blank: dict = field(default_factory=dict)       # reason -> [dotted field / path]


@dataclass
class FillReport:
    filled: list                      # [FormFill] — gate true; one entry PER COPY for per-item forms
    not_this_return: list             # includeWhen false, or a per-item collection with no items
    ungated: list                     # registers with no gate — can never render, upstream's rule
    gate_unresolved: list             # gate fact absent or Placeholder — stated, not guessed
    not_asked_here: list = field(default_factory=list)   # FORMS_NOT_ASKED_HERE
    stated: list = field(default_factory=list)   # choices this fill made, in sentences
    input_forms: list = field(default_factory=list)   # received forms, never printed
    lint: dict | None = None                        # formlint's summary of the written files


def _resolved(tsv: str) -> dict:
    rows = {}
    for line in tsv.splitlines():
        path, status, ftype, value = line.split("\t", 3)
        rows[path] = (status, ftype, value)
    return rows


def _require_reviewed(resolved: dict, reviewed_lines: dict) -> None:
    """This compute's served lines against the review surface's, exact — line ids AND values.

    The reviewed keys carry the tab's own spelling ("1040 9"); the LAST token is the line id.
    A line the tab shows that this compute does not, one this compute serves that the tab never
    showed, and a value that moved are all the same refusal: what would print is not what was
    reviewed."""
    computed = {}
    for path, (status, _ftype, value) in resolved.items():
        if path in _LINE_BY_PATH and status in ("Complete", "Placeholder"):
            computed[_LINE_BY_PATH[path]] = value
    reviewed = {key.rsplit(" ", 1)[-1]: val for key, val in reviewed_lines.items()}
    if reviewed != computed:
        moved = sorted(set(reviewed) ^ set(computed)
                       | {k for k in reviewed.keys() & computed.keys()
                          if reviewed[k] != computed[k]})
        raise FillRefused(
            f"the reviewed lines do not match this computation (line "
            f"{', '.join(moved)}) — a figure changed since the last run. Run again, look at "
            f"the Computed return tab, then fill: running the compute IS the review.")


def _identity_plane(identity_path) -> tuple[dict, dict]:
    """(short field name -> term, term -> confirmed value). Empty values with no identity file."""
    fields = identity_file.load_identity_map()["fields"]
    values = identity_file.read(identity_path) if identity_path else {}
    return fields, values


def fill_return(facts: dict, out_dir, *, reviewed_lines, tax_year: int = 2025,
                identity_path=None, engine_home=None, notations_path=None,
                engine_extras: dict | None = None, birth_days: dict | None = None) -> FillReport:
    """`reviewed_lines` is REQUIRED and is the review gate at this surface: the `form
    lines` the person's review surface showed (`{"1040 9": "55400.00", ...}` — what
    `read_reviewed_lines` reads off the Computed return tab). The fill resolves fresh and
    REFUSES unless its own served lines match, so a workbook that was never run — or was edited
    after its last run — cannot become a rendered form. Rendering without the review having
    happened is what is impossible."""
    if not reviewed_lines:
        raise FillRefused(
            "this workbook has no computed lines to review — run it first. Running the compute "
            "IS the review, and fill renders only a reviewed computation.")
    pin = discover_pin(engine_home)
    if not pin.matches_pin:
        raise FillRefused(
            "the engine home is not the pinned engine — fill will not render figures from a "
            "different dictionary. Use the engine home the build stages (BUILD.md, 'Run from the "
            "source files').")
    dict_dir = Path(pin.dict_dir)
    pdf_root = dict_dir.parent.parent / "dictionary" / "pdf" / "2025"
    if not pdf_root.is_dir():
        raise PdfSurprise("engine home has no dictionary/pdf — use the engine home the build "
                          "stages (BUILD.md, 'Run from the source files')")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # the identity file against the return BEFORE the engine round — a cheap gate first.
    id_fields, id_values = _identity_plane(identity_path)
    notes = notations.read(notations_path) if notations_path else {}
    misfit = identity_file.against_return(id_values, facts)
    if misfit:
        raise FillRefused(misfit)

    resolved = _resolved(EngineAdapter(pin).resolve_facts(
        map_with_extras(facts, tax_year, engine_extras, birth_days)))
    _require_reviewed(resolved, reviewed_lines)

    report = FillReport([], [], [], [])
    registers = read_all(pdf_root)
    kinds = form_kinds(pdf_root)
    for form_key, reg in sorted(registers.items()):
        if kinds.get(form_key) == "input-document":
            # INPUT-FORMS.md §a: a form the person RECEIVED — a W-2G, a W-2, a
            # 1099 — is read from, never printed by this repo. The copy this used to write carried
            # the figures and no payer, which is a form nobody can use; the return's own forms
            # carry those figures where they belong. Said only for a form this return HAS (its
            # collection holds a member); a K-1 nobody received is not worth a sentence.
            report.input_forms.append(form_key)
            if reg.gate_kind == "includeForEach" and _collection_members(resolved, reg.gate_path):
                report.stated.append(INPUT_FORM_NOT_PRINTED.format(form=FORM_NAMES.get(form_key, form_key)))
            continue
        if reg.gate_kind is None:
            report.ungated.append(form_key)
            continue
        if reg.gate_kind == "includeForEach":
            # One filled copy per collection member, in the collection's own order, ordinals
            # 1-based (people count from 1). An empty collection is a form this return simply
            # does not carry — the same bucket as a false includeWhen gate.
            members = _collection_members(resolved, reg.gate_path)
            if not members:
                report.not_this_return.append(form_key)
                continue
            for ordinal, member in enumerate(members, start=1):
                report.filled.append(_fill_one(reg, resolved, id_fields, id_values, out_dir,
                                               member=member, ordinal=ordinal, notes=notes))
            continue
        gate = resolved.get(reg.gate_path)
        if gate is None and switch_settled_false(reg.gate_path, resolved, dict_dir):
            # the gate is a default-less switch whose every condition resolved false — the
            # dictionary's own shape for "true, or undefined" — so the form is not this return's.
            report.not_this_return.append(form_key)
            report.stated.append(NOT_THIS_RETURN.format(form=FORM_NAMES.get(form_key, form_key)))
            continue
        if gate is None or gate[0] != "Complete":
            if form_key in FORMS_NOT_ASKED_HERE:
                report.not_asked_here.append(form_key)
            else:
                report.gate_unresolved.append(form_key)
            continue
        if gate[2] != "true":
            if _is_the_over_65_route(form_key, reg, registers):
                report.stated.append(FORM_1040_FOR_OVER_65)     # Form 1040 is everyone's
            else:
                report.not_this_return.append(form_key)
                if form_key in SAID_WHEN_NOT_THIS_RETURN:
                    # The pinned dictionary makes /requiresSchedule1 a complete-safe false on an ordinary
                    # return, so the not-this-return sentence is said here too, not only where this module
                    # settled a default-less switch itself.
                    report.stated.append(NOT_THIS_RETURN.format(form=FORM_NAMES.get(form_key, form_key)))
                continue
        report.filled.append(_fill_one(reg, resolved, id_fields, id_values, out_dir, notes=notes))
    _refuse_when_nothing_written(report, registers)
    return report


# the register gates `IRS1040` on the not-over-65 indicator — the dictionary
# routes a filer 65 or older to Form 1040-SR — and carries no `IRS1040SR`. Form 1040-SR is the
# same 2025 return in larger print (every line id, caption and box matches; measured against
# irs.gov's own files), and the IRS's instructions say "Everyone can file Form 1040", so on that
# route Form 1040 is written and the choice is stated. If an SR register ever appears, upstream's
# routing takes over untouched.
_MAIN_FORM = "IRS1040"
_MAIN_FORM_TWIN = "IRS1040SR"
_NOT_OVER_65_GATE = "/pdfNotOver65SRIndicator"
FORM_1040_FOR_OVER_65 = ("Form 1040 was written. This version writes Form 1040 for every filer; "
                         "Form 1040-SR, the same return in larger print, is an option a filer 65 or "
                         "older may use instead.")


def _is_the_over_65_route(form_key: str, reg, registers: dict) -> bool:
    return (form_key == _MAIN_FORM and reg.gate_path == _NOT_OVER_65_GATE
            and _MAIN_FORM_TWIN not in registers)


def _refuse_when_nothing_written(report: FillReport, registers: dict) -> None:
    """Silence with exit 0 is the wrong shape: a fill that wrote no form refuses, by the counts."""
    if report.filled:
        return
    raise FillRefused(
        f"nothing was written: {len(report.not_this_return)} forms are not part of this return, "
        f"{len(report.gate_unresolved)} are not settled by this return's answers, "
        f"{len(report.not_asked_here)} are forms this version does not ask about, and "
        f"{len(report.ungated)} form templates carry no render rule yet.")


# The forms a person hears named; anything else prints as its register key.
FORM_NAMES = {"IRS1040": "Form 1040", "IRS1040S1": "Schedule 1 (Form 1040)",
              "IRS1040S2": "Schedule 2 (Form 1040)", "IRS1040S3": "Schedule 3 (Form 1040)",
              "IRSW2G": "Form W-2G"}
NOT_THIS_RETURN = "{form} is not part of this return."
# the form a person looks for when Form 1040's lines 8 and 10 are blank — said when it is not
# this return's, whichever way the dictionary settles its gate. Only Schedule 1.
SAID_WHEN_NOT_THIS_RETURN = frozenset({"IRS1040S1"})
INPUT_FORM_NOT_PRINTED = ("{form} is a form you received, so it is not printed here; its figures are "
                          "carried on the return's own forms.")


def _fact_definition(path: str, dict_dir: Path):
    """The `<Fact>` element defining `path` in the pinned dictionary, or None."""
    needle = f'<Fact path="{path}">'
    for module in sorted(dict_dir.glob("*.xml")):
        text = module.read_text(encoding="utf-8")
        start = text.find(needle)
        if start < 0:
            continue
        end = text.find("</Fact>", start)
        try:
            return ElementTree.fromstring(text[start:end + len("</Fact>")])
        except ElementTree.ParseError:
            return None
    return None


def _condition_false(node, resolved: dict) -> bool:
    """Does this `<When>` condition resolve Complete false? Only the shapes the register's gates
    use are read — `<Dependency>` and `<Any>`/`<All>` of them; anything else is not settled."""
    tag = node.tag
    if tag == "Dependency":
        row = resolved.get(node.get("path", ""))
        return row is not None and row[0] == "Complete" and row[2] == "false"
    if tag in ("Any", "All"):
        kids = list(node)
        if not kids:
            return False
        if tag == "Any":
            return all(_condition_false(k, resolved) for k in kids)
        return any(_condition_false(k, resolved) and _all_complete(node, resolved) for k in kids)
    return False


def _all_complete(node, resolved: dict) -> bool:
    return all(resolved.get(d.get("path", ""), ("", "", ""))[0] == "Complete"
               for d in node.iter("Dependency"))


def switch_settled_false(path: str, resolved: dict, dict_dir: Path) -> bool:
    """a gate absent from the engine's dump because its definition is a `<Switch>` with no
    default — the dictionary's shape for "true, or undefined" (`/requiresSchedule1`: any of three
    booleans) — is FALSE when every case's condition resolved Complete false. Read at the pin,
    never guessed: a switch with a default, a case whose condition is not settled, or a shape
    this reader does not know leaves the gate unresolved, and the report says so."""
    fact = _fact_definition(path, dict_dir)
    if fact is None:
        return False
    derived = fact.find("Derived")
    if derived is None or len(derived) != 1 or derived[0].tag != "Switch":
        return False
    switch = derived[0]
    if switch.find("Default") is not None:
        return False
    cases = switch.findall("Case")
    if not cases:
        return False
    for case in cases:
        when = case.find("When")
        if when is None or len(when) != 1 or not _condition_false(when[0], resolved):
            return False
    return True


# Forms the pin carries a register for and this service asks NOTHING about: their
# whole intake is outside it, so the engine leaves their gate undetermined on EVERY return, and
# "this return's answers do not settle whether they belong to it" was printed at a person with one
# W-2. That sentence is for a gate the person's own answers could have settled; these get their
# own. A reviewed list, not a rule: two rules were tried and both misjudged (the gate's whole
# dependency closure — Form 8936's reads the tax its credit is limited by, which reaches
# everything; the gate's own dictionary module — which calls Schedule 2 and Schedule SE unasked).
# It applies ONLY while the gate is undetermined: a gate the engine resolves true fills the form
# whatever this says. `tests/test_fill_sentences.py` locks it to the pin — the forms left
# undetermined on a wages-only return must be exactly these, so a new one at the next pin is
# classified by a person. Form 2106 is not on the list: its gate resolves on every return, so
# where it is not filed it is simply not this return's.
FORMS_NOT_ASKED_HERE = frozenset({"IRS3903", "IRS4797", "IRS8828", "IRS8936", "IRS8978"})


_COLLECTION_RE = re.compile(r"Collection\(Vector\((.*)\)\)")


def _collection_members(resolved: dict, path: str) -> list:
    """The collection's member ids, in the collection's own order — or [] when it is absent or
    empty, which is not an error: a return with no W-2G carries no W-2G copies."""
    row = resolved.get(path)
    if row is None or row[0] != "Complete" or row[1] != "Collection":
        return []
    inner = _COLLECTION_RE.fullmatch(row[2])
    if inner is None:
        raise PdfSurprise(f"{path}: unrecognisable collection value {row[2]!r} — the runner's "
                          f"spelling changed; look before trusting any per-item fill")
    return [m for m in (part.strip() for part in inner.group(1).split(",")) if m]


_FILER_ALIASES = {"/primaryFiler/": "true", "/secondaryFiler/": "false"}


def _filer_alias(path: str, resolved: dict) -> str:
    """the register writes a filer's own facts as `/primaryFiler/<fact>` (the dictionary's
    derived reference), and the runner dumps them under `/filers/#<id>/<fact>` — so the age-65
    and blind boxes were stated blank as "not resolved at this pin" on every return. The id is
    the filer whose `isPrimaryFiler` is true (false for the secondary); with no such filer the
    path is left as written and stays a stated blank."""
    for prefix, flag in _FILER_ALIASES.items():
        if path.startswith(prefix):
            ids = [k.split("/")[2] for k, row in resolved.items()
                   if k.startswith("/filers/#") and k.endswith("/isPrimaryFiler")
                   and row[0] == "Complete" and row[2] == flag]
            if len(ids) == 1:
                return f"/filers/{ids[0]}/" + path[len(prefix):]
    return path


MAIN_HOME_WRITABLE = "/writableMainHomeInUsOverHalfYear"
MAIN_HOME_DERIVED = "/mainHomeInUsOverHalfYear"

_HEADER_NAMES = re.compile(r"^/primaryFiler/fullName(?: space space /pdfSecondaryFiler/fullName)?$")


def _header_identity(raw: str, id_values: dict, resolved: dict) -> str | None:
    """A schedule header's identity — `None` when `raw` is not one, `""` when it is one the identity
    file does not supply. The names line is the primary filer's name, joined by "&" to the spouse's
    only on a joint return (the register's own spouse term is `pdfSecondaryFiler`, which the return
    carries only then); the number is the primary filer's."""
    if raw == "/primaryFiler/tin":
        return id_values.get("primary.ssn", "")
    if not _HEADER_NAMES.match(raw):
        return None

    def full(who):
        return " ".join(p for p in (id_values.get(f"{who}.first_name", ""),
                                    id_values.get(f"{who}.last_name", "")) if p).strip()
    primary, spouse = full("primary"), full("spouse")
    if not primary:
        return ""
    row = resolved.get("/isFilingStatusMFJ")          # (status, type, value), as `_resolved` reads it
    joint = bool(row) and str(row[2]).strip().lower() == "true"
    return f"{primary} & {spouse}" if joint and spouse and "pdfSecondaryFiler" in raw else primary


_ROW_INDEX = re.compile(r"^(/[A-Za-z0-9]+)/\[(\d+)\](/.*)$")


def _row_path(raw: str, resolved: dict) -> tuple[str | None, str | None]:
    """Upstream's ordinal row notation, `/interestReports/[2]/roundedTaxableInterest`, as the
    runner spells the third member's fact — or (None, reason) when the collection has no such
    row, which is the right blank for a return with fewer payers than the schedule has lines.
    Schedule B lines 1 and 5 were once stated "not resolved at this pin" on every return
    because this notation was never translated."""
    m = _ROW_INDEX.match(raw)
    if m is None:
        return raw, None
    members = _collection_members(resolved, m.group(1))
    index = int(m.group(2))
    if index >= len(members):
        return None, "no such row on this return"
    return f"{m.group(1)}/#{members[index]}{m.group(3)}", None


def expected_values(reg: FormRegister, tpl: PdfTemplate, resolved: dict, id_fields: dict,
                    id_values: dict, *, member: str | None = None,
                    notes: dict | None = None) -> tuple[dict, dict]:
    """What every mapped field of `reg` should carry on this return: `(values, blanks)` — the
    field values to write, and for each field left blank the stated reason. THE ONE PLACE this is
    decided: the fill writes exactly `values`, and the lint (`formlint.py`) holds a filled file to
    the same answer, so a box the fill should have filled and did not cannot pass unnoticed."""
    values: dict = {}
    blanks: dict = {}

    def blank(reason: str, what: str):
        blanks.setdefault(reason, []).append(what)

    for dotted, raw in sorted(reg.mappings.items()):
        fld = tpl.fields.get(dotted)
        if fld is None:
            # The register and its own template disagree — pinned bytes, so this is a register
            # defect to route to build, not a condition to skip quietly.
            raise PdfSurprise(f"{reg.form_key}: register maps {dotted} but the template has no "
                              f"such field")
        short = dotted.rsplit(".", 1)[-1]
        if member is None and reg.form_key == "IRS1040" and short in id_fields:
            term = id_fields[short]
            if term in id_values:
                values[dotted] = id_values[term]
            else:
                blank("identity not supplied — fill from your identity file, or by hand", dotted)
            continue
        # Form 1040's notation strip — printed from the page's own answers, kept on
        # this computer; no fact in the dictionary depends on any of them (measured at the pin).
        notation = notations.value_for(raw, notes or {})
        if notation is not None:
            if notation is True or (isinstance(notation, str) and notation):
                values[dotted] = notation
            else:
                blank("not ticked on the page's notations", f"{dotted} <- {raw}")
            continue
        # The main-home checkbox prints what the return was COMPUTED with. Left
        # blank, the writable resolves nothing while the engine's own `/mainHomeInUsOverHalfYear`
        # takes it as true (Publication 596 Rule 14) — an unticked box beside a credit computed on
        # a yes is the form disagreeing with its own figures.
        if raw == MAIN_HOME_WRITABLE and resolved.get(raw) is None:
            row = resolved.get(MAIN_HOME_DERIVED)
            if row and row[0] == "Complete" and str(row[2]).strip().lower() == "true":
                values[dotted] = True
                continue
        header = _header_identity(raw, id_values, resolved)   # per-copy forms (4684, 4972) too
        if header is not None:
            # Every schedule's "Name(s) shown on return" and "Your social security
            # number" header prints the identity the person typed on the page — the same identity
            # file as Form 1040's own boxes, never the engine plane's placeholders.
            if header:
                values[dotted] = header
            else:
                blank("identity not supplied — fill from your identity file, or by hand", dotted)
            continue
        if "~" in raw or " " in raw:
            blank("filler transform not implemented", f"{dotted} <- {raw}")
            continue
        if _IDENTITY_TOKENS.search(raw):
            blank("identity-shaped fact — never filled from the engine plane", f"{dotted} <- {raw}")
            continue
        lookup, why = _row_path(raw, resolved)
        if lookup is None:
            blank(why, f"{dotted} <- {raw}")
            continue
        lookup = lookup if member is None else lookup.replace("/*/", f"/#{member}/")
        lookup = _filer_alias(lookup, resolved)
        row = resolved.get(lookup)
        if row is None:
            blank("fact not resolved at this pin", f"{dotted} <- {raw}")
            continue
        status, ftype, value = row
        if status != "Complete" and not (status == "Placeholder" and raw in _SERVED_PATHS):
            blank("engine result is a placeholder — not printable", f"{dotted} <- {raw}")
            continue
        if fld.field_type == "Btn":
            if ftype != "Boolean":
                blank("non-boolean fact mapped to a checkbox", f"{dotted} <- {raw}")
                continue
            if value == "true":
                values[dotted] = True
            # false: unchecked IS the template's state
            continue
        if ftype == "Boolean":
            blank("boolean fact mapped to a text box", f"{dotted} <- {raw}")
            continue
        values[dotted] = value
    return values, blanks


def _fill_one(reg: FormRegister, resolved: dict, id_fields: dict, id_values: dict,
              out_dir: Path, *, member: str | None = None, ordinal: int | None = None,
              notes: dict | None = None) -> FormFill:
    if reg.template is None:
        raise PdfSurprise(f"{reg.form_key}: this return needs that form printed, and its blank form "
                          f"is not in the engine home yet — fetch it with scripts/fetch_irs_forms.py")
    template = reg.template.read_bytes()
    tpl = PdfTemplate(template)
    result = FormFill(form_key=reg.form_key, out_path=None)
    values, result.blank = expected_values(reg, tpl, resolved, id_fields, id_values, member=member,
                                          notes=notes)
    result.written = dict(values)

    for v in values.values():
        if isinstance(v, str) and (any(lit in v for lit in _PLACEHOLDER_LITERALS)
                                   or _PLACEHOLDER_TIN_RE.search(v)):
            raise PdfSurprise(
                f"a synthetic placeholder literal reached a fill value ({v!r}) — the identity "
                f"planes have been mixed; refusing to write the file")

    name = reg.template.stem + (f"-{ordinal}" if ordinal is not None else "") + ".pdf"
    out_path = out_dir / name
    out_path.write_bytes(fill_fields(template, values))
    result.out_path = out_path
    return result
