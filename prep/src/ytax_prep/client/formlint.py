# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The filled-forms lint: every filled form, box by box, against what the return says.

`fill_return` decides each mapped field's value in ONE place (`formfill.expected_values`). This
module reads a written file back and holds it to that answer: a box whose fact resolved Complete
and non-empty must carry that value; an identity box is filled exactly when the identity file
supplies it; a box that is rightly blank carries the fill's own stated reason. The lint runs in
the tests, in the corpus's fill stage, after every fill on a person's machine (the page reports
its count), and as `scripts/lint_filled_forms.py` on any output folder.

Verdict per box: `ok` (filled as expected), `defect` (expected a value; blank or different),
`extra` (filled where nothing was expected), `blank` (rightly blank, with the reason). A form
present in the output that the return should not have (a received form, a form not part of this
return) is a defect too.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..engine.adapter import EngineAdapter, discover_pin
from ..facts.extras import map_with_extras
from .formfill import _collection_members, _identity_plane, _resolved, expected_values, form_kinds
from .pdfform.reader import PdfTemplate, field_value
from .pdfform.registers import read_all


@dataclass
class FormLint:
    form_key: str
    file: str
    ok: int = 0
    defects: list = field(default_factory=list)     # "field <- fact: expected X, found Y"
    extra: list = field(default_factory=list)
    blank: dict = field(default_factory=dict)       # reason -> count


@dataclass
class LintReport:
    forms: list = field(default_factory=list)
    unexpected_files: list = field(default_factory=list)   # a received form, or one not this return's

    @property
    def defects(self) -> int:
        return sum(len(f.defects) for f in self.forms) + len(self.unexpected_files)

    @property
    def checked(self) -> int:
        return sum(f.ok + len(f.defects) + len(f.extra) + sum(f.blank.values()) for f in self.forms)

    def summary(self) -> dict:
        return {"checked": self.checked, "defects": self.defects,
                "forms": {f.form_key: {"file": f.file, "ok": f.ok, "defects": f.defects[:20],
                                       "extra": f.extra[:20], "blank": f.blank} for f in self.forms},
                "unexpected_files": self.unexpected_files}

    def words(self) -> str:
        """One line a person reads after a fill."""
        if self.checked == 0:
            return "No filled form was checked."
        if self.defects == 0:
            return f"Every box that should be filled is filled ({self.checked} boxes checked)."
        return (f"{self.defects} box(es) that should be filled are blank or wrong, of {self.checked} "
                f"checked; the report names them.")


def _same(expected, found) -> bool:
    if expected is True:
        return found == "X"
    return str(expected).strip() == str(found or "").strip()


def lint_filled(out_dir, facts: dict, *, tax_year: int = 2025, identity_path=None,
                engine_home=None, resolved: dict | None = None, notations_path=None,
                engine_extras: dict | None = None, birth_days: dict | None = None) -> LintReport:
    """Hold every filled file under `out_dir` to what the return says. `resolved` may be passed by
    a caller that just resolved (the fill), else the pinned engine resolves `facts` here."""
    pin = discover_pin(engine_home)
    pdf_root = Path(pin.dict_dir).parent.parent / "dictionary" / "pdf" / "2025"
    registers = read_all(pdf_root)
    kinds = form_kinds(pdf_root)
    id_fields, id_values = _identity_plane(identity_path)
    from . import notations
    notes = notations.read(notations_path) if notations_path else {}
    if resolved is None:
        resolved = _resolved(EngineAdapter(pin).resolve_facts(
            map_with_extras(facts, tax_year, engine_extras, birth_days)))
    by_stem = {reg.template.stem: reg for reg in registers.values() if reg.template is not None}
    report = LintReport()
    for pdf in sorted(Path(out_dir).glob("*.pdf")):
        stem, _, ordinal = pdf.stem.partition("-")
        reg = by_stem.get(stem)
        if reg is None:
            report.unexpected_files.append(f"{pdf.name}: no register at the pin has this template")
            continue
        if kinds.get(reg.form_key) == "input-document":
            report.unexpected_files.append(f"{pdf.name}: {reg.form_key} is a form the person received; never printed")
            continue
        member = None
        if reg.gate_kind == "includeForEach" and ordinal.isdigit():
            members = _collection_members(resolved, reg.gate_path)
            member = members[int(ordinal) - 1] if 0 < int(ordinal) <= len(members) else None
        tpl = PdfTemplate(pdf.read_bytes())
        expected, blanks = expected_values(reg, tpl, resolved, id_fields, id_values, member=member,
                                           notes=notes)
        lint = FormLint(reg.form_key, pdf.name)
        for dotted in sorted(reg.mappings):
            fld = tpl.fields.get(dotted)
            found = field_value(tpl, fld) if fld is not None else None
            if dotted in expected:
                if _same(expected[dotted], found):
                    lint.ok += 1
                else:
                    lint.defects.append(f"{dotted} <- {reg.mappings[dotted]}: expected "
                                        f"{expected[dotted]!r}, found {found!r}")
            elif found not in (None, ""):
                lint.extra.append(f"{dotted}: found {found!r}, nothing expected")
        for reason, what in blanks.items():
            lint.blank[reason] = len(what)
        report.forms.append(lint)
    return report
