# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The notations at the top of Form 1040, page 1, kept on this computer.

Form 1040 prints a strip of special notations above the name: "Filed pursuant to section
301.9100-2", "Combat zone", "Deceased" with the date of death, and "Other" with up to three written
entries. Measured at the pin, no fact in the dictionary depends on any of them: they print, and
nothing computed here moves. So they are not facts the engine resolves — the page asks them, this
module keeps them beside the identity file in the working folder's `input\\` (never sent anywhere),
and the fill writes them into the boxes the register names for them. The date of death is a full
date: it prints as month, day and year, and it stays on this computer like a name does.

The combat zone's effect on tax is not this box: combat pay reaches the return through Form W-2 box
12, code Q, and the combat pay questions.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

FILENAME = "case.notations.json"
FIELDS = ("section_9100_relief", "combat_zone", "deceased", "date_of_death", "other",
          "other_entries")
MAX_ENTRY = 40

# The register's own fact for each box (dictionary/pdf/2025/IRS1040/en/configuration.yml).
BOXES = {
    "/writableForm1040Section9100ReliefNotation": "section_9100_relief",
    "/writableForm1040CombatZoneNotation": "combat_zone",
    "/writableForm1040PrimaryFilerDeceased": "deceased",
    "/writableForm1040OtherFilingNotation": "other",
}
ENTRIES = ("/writableForm1040OtherFilingNotationFirstEntry",
           "/writableForm1040OtherFilingNotationSecondEntry",
           "/writableForm1040OtherFilingNotationThirdEntry")
DATE = "/writableForm1040PrimaryFilerDateOfDeath"
DATE_PARTS = {"~dateMonth": "%m", "~dateDay": "%d", "~dateYear": "%Y"}


class NotationError(ValueError):
    """A notation this page cannot keep, said in words a person can act on."""


def clean(given: dict, tax_year: int = 2025) -> dict:
    """What the page sent, checked: ticks are true or false, a date of death is a real date in or
    before the tax year's following year, and "Other" carries at most three short entries."""
    out = {key: bool(given.get(key)) for key in ("section_9100_relief", "combat_zone", "deceased", "other")}
    date = str(given.get("date_of_death") or "").strip()
    if out["deceased"]:
        if not date:
            raise NotationError("Deceased is ticked: enter the date of death.")
        try:
            day = datetime.date.fromisoformat(date)
        except ValueError:
            raise NotationError("The date of death must be a date, like 2025-06-15.")
        if not tax_year <= day.year <= tax_year + 1:
            raise NotationError(f"The date of death must be in {tax_year} or {tax_year + 1}.")
        out["date_of_death"] = day.isoformat()
    elif date:
        raise NotationError("A date of death is entered but Deceased is not ticked.")
    entries = [str(e).strip() for e in (given.get("other_entries") or []) if str(e or "").strip()]
    if len(entries) > 3:
        raise NotationError("Other takes at most three entries.")
    if any(len(e) > MAX_ENTRY for e in entries):
        raise NotationError(f"Each Other entry is at most {MAX_ENTRY} characters.")
    if entries and not out["other"]:
        raise NotationError("Other entries are written but Other is not ticked.")
    out["other_entries"] = entries
    return out


def read(path) -> dict:
    path = Path(path)
    if not path.is_file():
        return {}
    try:
        return clean(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, NotationError) as why:
        raise NotationError(f"{path} cannot be read: {why}")


def write(path, given: dict, tax_year: int = 2025) -> dict:
    kept = clean(given, tax_year)
    Path(path).write_text(json.dumps(kept, indent=1), encoding="utf-8")
    return kept


def value_for(raw: str, notes: dict):
    """The value a register fact prints from the notations, `None` when `raw` is not a notation
    box, and `""` when it is one the notations leave empty (unticked, or no such entry)."""
    if raw in BOXES:
        return True if notes.get(BOXES[raw]) else ""
    if raw in ENTRIES:
        entries = notes.get("other_entries") or []
        index = ENTRIES.index(raw)
        return entries[index] if index < len(entries) else ""
    if raw.startswith(DATE + "/"):
        part = DATE_PARTS.get(raw[len(DATE) + 1:])
        date = notes.get("date_of_death")
        if part is None:
            return None
        return datetime.date.fromisoformat(date).strftime(part) if date else ""
    return None
