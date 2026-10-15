# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Reading the workbook back — refusing rather than guessing.

THE ONE RULE: a value this reader cannot be sure of is refused **BY NAME**, and never rounded,
defaulted, or dropped. A dropped field is a return computed as if it had not been supplied, which is
a wrong number rather than a smaller one.

TWO KINDS OF REFUSAL, deliberately separated. A **structural** fault — a missing or renamed tab, a
header that is not the column spec, an extra column, a hole in the rows — RAISES: nothing in the
file is readable under a shape that is not the shape. A **value** fault is COLLECTED, all of them,
because `run` paints every named cell in one pass and a person fixing one figure per round trip
pays a full cycle for each.

GEOMETRY, NEVER FLAGS. ORIGINAL is the left column of a money pair, at a fixed index under the fixed
header rows. Guard (c) is exactly why: a saved workbook comes back with its column runs compacted
and its `hidden` attributes gone, so anything hidden-dependent would work here and fail after the
first save. **No fill is ever read either** — a colour is a thing a person can paint over, and
CHANGED is computed by comparing the two columns.

Nothing here imports `writer`.
"""
from __future__ import annotations

import io
import re
import zipfile
from collections import namedtuple
from dataclasses import dataclass
from decimal import Decimal, DecimalException, InvalidOperation
from xml.etree import ElementTree

from . import layout, ooxml
from .ooxml import Formula, RefusedCell

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
DOC_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# Non-money fields the schema types as integers. A string where an integer belongs is wrong whatever
# it contains. This is the cell-level set: it overlaps `payload.INTEGER_FIELDS` but is not it —
# `tax_year` is read by its own Household row below rather than as a field, and `months_in_home`
# is an integer on the sheet that the payload check does not name.
INTEGER_FIELDS = frozenset({"person", "birth_year", "birth_month", "months_in_home",
                            "employer_ref"})

# A row index, a year, a month: a plain run of digits and nothing else. `0.0` and `1e1` both
# CONVERT to an integer, and neither is how anyone writes one.
_PLAIN_INTEGER = re.compile(r"^-?\d+$")
# A shared-string index: ASCII digits, nothing else. `\d` would take `١`, and `int()` would read it.
_SHARED_INDEX = re.compile(r"[0-9]+")

Refusal = namedtuple("Refusal", "cell fact message")
_Cell = namedtuple("_Cell", "kind text formula")

# A cell that was READ AND REFUSED, distinct from a cell that is BLANK. Both used to come back as
# None, which made one bad figure produce two refusals: the parse refusal, and then the "something
# was deleted" refusal for the empty CURRENT beside a filled ORIGINAL. One wrong cell is one
# refusal, or a person fixing the first is told about a second that was never true.
REFUSED = object()


class WorkbookRefused(ValueError):
    """The workbook's SHAPE is not the shape. Raised, because nothing under it can be trusted."""


@dataclass(frozen=True)
class WorkbookRead:
    """Everything one read produces. `facts` is what crosses; the rest is what the rewrite needs.

    A refusal names a VALUE; it does not forget the CELL — nor what KIND of cell it was. `refused`
    is `{path: RefusedCell}` for every CURRENT or value cell a value refusal names: its kind, its
    stored text, its formula. The rewrite puts that back exactly, so the next read refuses the same
    cell by the same name until a figure is typed. A carry-back that kept the text and dropped the
    kind turned a refused boolean into an accepted $1.00 on the next run, and a refused formula into
    its cached value; a refused cell that came back blank would read as ABSENT and the form would
    cross without the figure.

    `originals` is recorded for a money pair whether or not its CURRENT was refused: integer cents,
    or a `RefusedCell` for an ORIGINAL the reader itself refused — a foreign edit to a locked
    column, carried back as what it was rather than laundered into a number. A CURRENT that parsed
    beside a refused ORIGINAL is not the cell refused, and stays in `facts` as the figure it is."""
    tax_year: int | None
    facts: dict
    originals: dict
    stated: tuple
    edits: tuple
    refusals: tuple
    assumptions: tuple
    refused: dict
    # {(group, index): text} — the note COLUMN's stored text per row, plus ("filing_status", 0).
    # Carried so an UNCROSSED round can re-emit what an earlier crossing round said; text
    # only, never styles — a foreign save's fills are not trusted, and state stays derived.
    notes: dict


def _refuse(sheet: str, row: int, col: int, path: str, why: str) -> Refusal:
    """One spelling of a named refusal, in the form's own words:
    `W-2 #1 · 1 Wages, tips, other compensation (cell D3): "abc" is not an amount`. The number is
    the sheet's `Item` column — people count from 1; the path in `fact` stays 0-based.

    `fact` KEEPS the fact path — the wire contract, by which a gap, a service refusal and a cell all
    mean the same thing — and `cell` is the sheet-qualified reference; only the MESSAGE is for a
    person, and it never spells a field name."""
    reference = ooxml.ref(row, col)
    return Refusal(cell=f"{sheet}!{reference}", fact=path,
                   message=layout.REFUSAL_TEMPLATE.format(where=layout.describe(path),
                                                          ref=reference, why=why))


def _part_name(target: str) -> str:
    """A relationship target to a zip entry name. This writer emits `worksheets/sheet1.xml`,
    relative to `xl/`; a foreign save (Excel's, or an independent library's) emits the
    package-absolute `/xl/worksheets/sheet1.xml`. Guard (c) covers both, so neither form is a
    structural fault."""
    return target[1:] if target.startswith("/") else "xl/" + target


def _runs_text(element) -> str:
    """The text of a `<si>` or `<is>`: its `<t>` and the `<t>` of each `<r>` run, concatenated —
    and NOT the `<t>` under `<rPh>`. A phonetic run is the reading guide (furigana) a
    Japanese-locale save attaches beside the value; it says how the text is pronounced, not what
    it is. Read as value text it turned `480` with the guide `25` into `48025`, a wrong number that
    crossed with zero refusals."""
    if element.tag == f"{MAIN}rPh":
        return ""
    if element.tag == f"{MAIN}t":
        return element.text or ""
    return "".join(_runs_text(child) for child in element)


class _Package:
    """The zip, its shared strings, and one cell map per sheet. Sheet names are resolved through the
    workbook's OWN relationships, because a saved file does not promise `sheet1.xml` means the first
    tab. A missing `xl/sharedStrings.xml` is an empty table, not a fault: a foreign save that wrote
    every string inline has none."""

    def __init__(self, data: bytes):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            self._strings = []
            if "xl/sharedStrings.xml" in names:
                root = ElementTree.fromstring(zf.read("xl/sharedStrings.xml"))
                self._strings = [_runs_text(si) for si in root.iter(f"{MAIN}si")]
            rels = ElementTree.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
            target = {r.get("Id"): _part_name(r.get("Target")) for r in rels}
            book = ElementTree.fromstring(zf.read("xl/workbook.xml"))
            self._sheets = {}
            for sheet in book.iter(f"{MAIN}sheet"):
                part = target[sheet.get(f"{DOC_REL}id")]
                self._sheets[sheet.get("name")] = ElementTree.fromstring(zf.read(part))
        self._cells = {}

    def sheet_names(self) -> list:
        return list(self._sheets)

    def _shared_string(self, sheet: str, at: str, index: str) -> str:
        """The string a `t="s"` cell points at — or a refusal naming the cell. `int()` would take
        `-1` and read the LAST string, `١` and read the second, `""` nothing at all; an index past
        the table is an `IndexError` no sentence explains. No spreadsheet writes any of them, so
        nothing in the file is trusted past one."""
        if _SHARED_INDEX.fullmatch(index) is None or int(index) >= len(self._strings):
            raise WorkbookRefused(
                f"{sheet}!{at} points at shared string {index!r}, and the workbook's table holds "
                f"{len(self._strings)} — that is not a cell any spreadsheet writes, so nothing in "
                f"the file is trusted past it.")
        return self._strings[int(index)]

    def cells(self, sheet: str) -> dict:
        """`{(row, col): _Cell}`. `text` is the cell's STORED STRING — never a float."""
        if sheet in self._cells:
            return self._cells[sheet]
        out = {}
        for c in self._sheets[sheet].iter(f"{MAIN}c"):
            row, col = ooxml.parse_ref(c.get("r"))
            kind = c.get("t") or "n"
            f = c.find(f"{MAIN}f")
            # The whole element, attributes in document order: a shared formula's child has no
            # text at all, and goes back as exactly `<f t="shared" si="0"/>`.
            formula = None if f is None else Formula(f.text or "", tuple(f.attrib.items()))
            v = c.find(f"{MAIN}v")
            if kind == "s":
                text = "" if v is None else self._shared_string(sheet, c.get("r"), v.text or "")
            elif kind == "inlineStr":
                inline = c.find(f"{MAIN}is")
                text = "" if inline is None else _runs_text(inline)
            else:
                text = "" if v is None or v.text is None else v.text
            if kind == "b" and text.strip() and text.strip() not in ("0", "1"):
                # No spreadsheet writes this cell. Collected as a value refusal it would have to
                # be carried back, and as text "2" re-reads as $2.00; as a boolean it is not one.
                raise WorkbookRefused(
                    f"{sheet}!{c.get('r')} is typed as a boolean and holds {text.strip()!r}; a "
                    f"boolean stores 0 or 1. That is not a cell any spreadsheet writes, so nothing "
                    f"in the file is trusted past it.")
            out[(row, col)] = _Cell(kind=kind, text=text.strip(), formula=formula)
        self._cells[sheet] = out
        return out


def _finite_decimal(text: str):
    """`Decimal(text)` when it is a FINITE number, else None — the one place the sheet's text becomes
    a number.

    `Decimal` happily constructs `inf`, `Infinity`, `nan` and `sNaN`. None of them is a figure on a
    form, and each fails later in its own way: an infinity passes every whole-number comparison and
    then overflows `int()`; a signalling NaN raises on the first multiplication rather than at
    construction. So finiteness is checked HERE, and the callers never see one."""
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    return value if value.is_finite() else None


def _plain_integer(text: str):
    """`int(text)` when the text is a plain run of digits, else None. No `Decimal` at all: an index
    or a year that needs converting is not one a person wrote."""
    return int(text) if _PLAIN_INTEGER.match(text) else None


def _to_cents(cell: _Cell, sheet: str, row: int, col: int, path: str, refusals: list):
    """Dollars in the sheet to integer cents, EXACTLY — and refusing by name where it cannot.

    Reads the stored STRING, never a float. Strips the chrome a person's own editing leaves ($, a
    thousands separator, a space); accounting parentheses are a negative. Parses with `Decimal`, and
    **refuses anything that is not a whole number of cents** rather than rounding it: `12.345` is a
    figure somebody meant something by, and picking one of the two nearest is a guess about
    somebody's return."""
    if cell is None or (not cell.text and cell.formula is None):
        return None
    if cell.formula is not None:
        refusals.append(_refuse(sheet, row, col, path,
                                "this is a formula cell, and a formula is not a value a person "
                                "stated — replace it with the figure you mean"))
        return REFUSED
    if cell.kind == "b":
        refusals.append(_refuse(sheet, row, col, path,
                                f'"{cell.text}" is a boolean, and this cell holds an amount in '
                                f'dollars'))
        return REFUSED
    text = cell.text
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    for chrome in ("$", ",", " ", " "):
        text = text.replace(chrome, "")
    if negative and text.startswith("-"):
        # `(5.00)` is a negative; `(-5.00)` says the sign twice. Stripping the parentheses and
        # then negating the negative turned it into +500 — a sign flip, not a refusal.
        refusals.append(_refuse(sheet, row, col, path,
                                f'"{cell.text}" is not an amount — a minus sign inside accounting '
                                f'parentheses says the sign twice'))
        return REFUSED
    if text in ("", "-"):
        return None
    amount = _finite_decimal(text)
    if amount is None:
        refusals.append(_refuse(sheet, row, col, path, f'"{cell.text}" is not an amount'))
        return REFUSED
    try:
        cents = amount * 100
        whole = cents == cents.to_integral_value()
        value = int(-cents) if negative else int(cents)
    except (DecimalException, ValueError, OverflowError):
        # A finite Decimal can still signal on arithmetic (an exponent past the context's ceiling).
        refusals.append(_refuse(sheet, row, col, path, f'"{cell.text}" is not an amount'))
        return REFUSED
    if not whole and cell.kind == "n":
        # A NUMBER cell is a binary double, and Excel (or any library that saves the file) may
        # spell one with every digit it carries: 634.81 is saved as `634.8099999999999` or
        # `634.80999999999995`. That spelling IS 634.81 — the same stored number — so it is read as
        # 634.81. Only where the nearest whole cent is the identical double: `12.345` is not
        # 12.34 or 12.35 as a double either, and is still refused. A figure typed as TEXT is
        # never adjusted (a demo, 2026-09-22: a workbook saved once was refused).
        nearest = cents.to_integral_value()
        try:
            if float(text) == float(nearest / 100):
                whole = True
                value = int(-nearest) if negative else int(nearest)
        except (ValueError, OverflowError):
            pass
    if not whole:
        refusals.append(_refuse(sheet, row, col, path,
                                f'"{cell.text}" is not a whole number of cents. It is not rounded '
                                f'here — say what you mean to the cent.'))
        return REFUSED
    return value


def _to_value(cell: _Cell, name: str, sheet: str, row: int, col: int, path: str, refusals: list):
    """A non-money field, read as itself. Enums are checked against the schema's own list."""
    if cell is None or (not cell.text and cell.formula is None):
        return None
    if cell.formula is not None:
        refusals.append(_refuse(sheet, row, col, path,
                                "this is a formula cell, and a formula is not a value a person "
                                "stated"))
        return REFUSED
    text = cell.text
    codes = layout.choices_for_field(name)

    if name in layout.DATE_FIELDS and cell.kind in ("n", "b"):
        # a typed date is stored as a day serial counted from 1899-12-30 (the 1900 date
        # system the writer's workbooks use). A whole serial is that date; anything else is
        # refused by name rather than guessed.
        import datetime
        serial = None if cell.kind == "b" else _plain_integer(text)
        if serial is None or not 1 <= serial <= 2958465:
            refusals.append(_refuse(sheet, row, col, path, f'"{text}" is not a date'))
            return REFUSED
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=serial)).isoformat()

    if name in layout.BOOLEAN_FIELDS:
        if cell.kind == "b":
            return text == "1"
        if text.lower() in layout.BOOLEAN_CHOICES:
            return text.lower() == "true"
        refusals.append(_refuse(sheet, row, col, path,
                                f'"{text}" is not one of the accepted values: '
                                f'{", ".join(layout.BOOLEAN_CHOICES)}'))
        return REFUSED

    if name in INTEGER_FIELDS:
        if cell.kind == "b":
            refusals.append(_refuse(sheet, row, col, path,
                                    f'"{text}" is a boolean, and this cell holds a whole number'))
            return REFUSED
        value = _plain_integer(text)
        if value is None:
            refusals.append(_refuse(sheet, row, col, path, f'"{text}" is not a whole number'))
            return REFUSED
        if codes and str(value) not in codes:
            refusals.append(_refuse(sheet, row, col, path,
                                    f'"{text}" is not one of the accepted values: '
                                    f'{", ".join(codes)}'))
            return REFUSED
        if name == "person":
            # PEOPLE COUNT FROM 1. The person typed the Household tab's number (its `Item`
            # column reads 1, 2, …); the wire
            # carries `person` 0-based. A `0` is a number no person on the sheet has — refused by
            # name rather than read as the first person.
            if value < 1:
                refusals.append(_refuse(sheet, row, col, path,
                                        f'"{text}" — there is no person {value}; persons are '
                                        f'numbered from 1'))
                return REFUSED
            return value - 1
        return value

    if codes and text not in codes:
        refusals.append(_refuse(sheet, row, col, path,
                                f'"{text}" is not one of the accepted codes: {", ".join(codes)}'))
        return REFUSED
    return text


def _refused_cell(cell: _Cell) -> RefusedCell:
    """The cell as it was, for the writer to put back. A formula first, whatever its result type;
    then a boolean; then anything stored as text; and a number-typed cell last, as `"n"`."""
    if cell.formula is not None:
        return RefusedCell("f", cell.text, cell.formula)
    if cell.kind == "b":
        return RefusedCell("b", cell.text, None)
    if cell.kind in ("s", "inlineStr", "str", "e"):
        return RefusedCell("s", cell.text, None)
    return RefusedCell("n", cell.text, None)


def _check_headers(cells: dict, sheet: str, tab, header_row: int, subheader_row: int) -> None:
    """The header row must equal `layout`'s column spec EXACTLY, and nothing may sit beyond it.

    `additionalProperties:false` all the way down means a column the schema does not define could
    only ever be dropped, and a dropped field is a return computed as if it had not been supplied.

    Both header rows are PASSED IN from `layout`'s own constants, as the writer's `_grid` takes
    them, rather than derived here as `+ 1`: the geometry belongs to the layout, not to this check.
    """
    width = layout.note_index(tab)
    for (row, col), cell in cells.items():
        if row in (header_row, subheader_row) and col > width and cell.text:
            raise WorkbookRefused(
                f"{sheet} carries a column at {ooxml.col_letter(col)} "
                f"({cell.text!r}) that this workbook's spec does not define. A column the fact "
                f"schema has no field for could only ever be dropped, and a dropped field is a "
                f"return computed as if it had not been supplied.")
    for column in layout.columns_for(tab):
        if column.kind == "current":
            continue                       # the caption is merged across the pair
        # The caption the writer wrote, from the one table — never the field name.
        expected = (layout.INDEX_HEADER if column.kind == "index" else
                    layout.NOTE_HEADER if column.kind == "note" else
                    layout.label_for(tab, column.field))
        found = cells.get((header_row, column.index))
        actual = "" if found is None else found.text
        if actual != expected:
            raise WorkbookRefused(
                f"{sheet}!{ooxml.ref(header_row, column.index)} says {actual!r}; the column spec "
                f"says {expected!r}. Reading a renamed column would put one field's figure on "
                f"another field's line.")


def _row_is_blank(cells: dict, line: int, width: int) -> bool:
    """Neither the index column nor the note column counts. `run` creates a row the service named —
    index cell and all — for the person to fill; left empty, the index is all that is there, and an
    index is not a person. A note with no values beside it is not a row either."""
    return not any(cells.get((line, col)) and cells[(line, col)].text
                   for col in range(2, width))


def _data_lines(cells: dict, sheet: str, tab, first: int) -> list:
    width = layout.note_index(tab)
    lines = []
    line = first
    while not _row_is_blank(cells, line, width):
        lines.append(line)
        line += 1
    for (row, col), cell in cells.items():
        if row > line and 1 < col < width and cell.text:
            raise WorkbookRefused(
                f"{sheet} has a row at {row} below a blank row at {line}. Refusing rather than "
                f"dropping a row you typed — rows are read as one run, and a hole in them is a "
                f"line the return would compute as absent.")
    return lines


def _read_grid(cells: dict, sheet: str, tab, header_row: int, subheader_row: int, first_row: int,
               refusals: list, originals: dict, stated: list, edits: list, refused: dict,
               notes: dict) -> list:
    _check_headers(cells, sheet, tab, header_row, subheader_row)
    items = []
    for index, line in enumerate(_data_lines(cells, sheet, tab, first_row)):
        item = {}
        for name in tab.fields:
            path = f"{tab.group}[{index}].{name}"
            if layout.is_money(name):
                left = layout.column_index(tab, name, "original")
                right = layout.column_index(tab, name, "current")
                was = _to_cents(cells.get((line, left)), sheet, line, left, path, refusals)
                now = _to_cents(cells.get((line, right)), sheet, line, right, path, refusals)
                if was is REFUSED or now is REFUSED:
                    # Already refused BY NAME, once. Reporting the same cell twice — as unreadable
                    # and then as deleted — sends a person hunting for a second fault that is not
                    # there. But the CELLS are kept, each as the KIND it was: the ORIGINAL as
                    # read, or as the refused cell itself; the CURRENT as the refused cell itself,
                    # or — when it parsed and only the ORIGINAL was refused — as the figure it is,
                    # untouched. A rewrite that blanked either would leave blank beside blank,
                    # which the next read takes as absent, and the form would cross without it.
                    if was is REFUSED:
                        originals[path] = _refused_cell(cells[(line, left)])
                    elif was is not None:
                        originals[path] = was
                    if now is REFUSED:
                        refused[path] = _refused_cell(cells[(line, right)])
                    elif now is not None:
                        item[name] = now
                    continue
                if was is not None:
                    originals[path] = was
                if was is not None and now is None:
                    refusals.append(_refuse(
                        sheet, line, right, path,
                        "the column holding what was read carries a figure and this cell is "
                        "empty — something was deleted, and guessing which of the two you meant "
                        "is not this reader's job"))
                    continue
                if now is None:
                    continue
                if was is None:
                    stated.append(path)
                elif now != was:
                    edits.append(path)
                item[name] = now
            else:
                col = layout.column_index(tab, name, "value")
                value = _to_value(cells.get((line, col)), name, sheet, line, col, path, refusals)
                if value is REFUSED:
                    refused[path] = _refused_cell(cells[(line, col)])
                elif value is not None:
                    item[name] = value
        note_cell = cells.get((line, layout.note_index(tab)))
        if note_cell is not None and note_cell.text:
            notes[(tab.group, index)] = note_cell.text
        items.append(item)
    return items


def _household(package: _Package, refusals: list, originals: dict, stated: list, edits: list,
               refused: dict, notes: dict):
    """Household's blocks are found by their LABEL in column A, not by a fixed row: the assumptions
    block above the persons grid grows and shrinks between runs. Nothing here is money, so no
    ORIGINAL geometry is needed on this tab and the floating block costs nothing."""
    cells = package.cells(layout.HOUSEHOLD)
    marker = {}
    for (row, col), cell in sorted(cells.items()):
        if col == 1 and cell.text and cell.text not in marker:
            marker[cell.text] = row
    # The two rows are found by the plain LABEL the writer put in column A (`Tax year`, `Filing
    # status`), from the one table; the path constants are the wire's names and are on no sheet.
    year_label = layout.label_for(layout.HOUSEHOLD_GROUP, layout.TAX_YEAR_ROW)
    status_label = layout.label_for(layout.HOUSEHOLD_GROUP, layout.FILING_STATUS_ROW)
    # the root yes/no rows, found by their labels the same way.
    root_labels = {path: layout.label_for(layout.HOUSEHOLD_GROUP, path)
                   for path in layout.ROOT_QUESTION_ROWS}
    for label in (year_label, status_label, *root_labels.values(), layout.PERSONS_BLOCK):
        if label not in marker:
            raise WorkbookRefused(
                f"the {layout.HOUSEHOLD} tab has no {label!r} row. Its blocks are found by their "
                f"own label in the first column, so a renamed or deleted one cannot be read past.")

    # THE YEAR IS A CELL LIKE EVERY OTHER: a formula and a boolean are refused by name and carried
    # back as what they were. `=2025` used to be read as 2025 and rewritten as a plain number;
    # `t="b"` `<v>1</v>` used to be sent as tax year 1.
    year_row = marker[year_label]
    year_cell = cells.get((year_row, 2))
    tax_year = None
    if year_cell is not None and (year_cell.text or year_cell.formula is not None):
        if year_cell.formula is not None:
            why = ("this is a formula cell, and a formula is not a value a person stated — "
                   "replace it with the year you mean")
        elif year_cell.kind == "b":
            why = f'"{year_cell.text}" is a boolean, and this cell holds a year'
        else:
            tax_year = _plain_integer(year_cell.text)
            why = None if tax_year is not None else (
                f'"{year_cell.text}" is not a year — a year is a whole number')
        if why is not None:
            refusals.append(_refuse(layout.HOUSEHOLD, year_row, 2, layout.TAX_YEAR_ROW, why))
            refused[layout.TAX_YEAR_ROW] = _refused_cell(year_cell)

    status_row = marker[status_label]
    filing = _to_value(cells.get((status_row, 2)), layout.FILING_STATUS_ROW, layout.HOUSEHOLD,
                       status_row, 2, layout.FILING_STATUS_ROW, refusals)
    if filing is REFUSED:
        refused[layout.FILING_STATUS_ROW] = _refused_cell(cells[(status_row, 2)])
        filing = None

    # each root yes/no row is read as the boolean field it is (`_to_value` reads the
    # dropdown's own words); a refused cell is carried back by its path like the status cell.
    root = {}
    for path, label in root_labels.items():
        row = marker[label]
        if path in layout.ROOT_MONEY_ROWS:
            # a root amount row reads as dollars, the way a form tab's money column does.
            value = _to_cents(cells.get((row, 2)), layout.HOUSEHOLD, row, 2, path, refusals)
        else:
            value = _to_value(cells.get((row, 2)), path, layout.HOUSEHOLD, row, 2, path, refusals)
        if value is REFUSED:
            refused[path] = _refused_cell(cells[(row, 2)])
            value = None
        if value is not None:
            root[path] = value
        root_note = cells.get((row, 3))
        if root_note is not None and root_note.text:
            notes[(path, 0)] = root_note.text

    assumptions = []
    if layout.ASSUMPTIONS_BLOCK in marker:
        line = marker[layout.ASSUMPTIONS_BLOCK] + 1
        while cells.get((line, 1)) and cells[(line, 1)].text:
            text = cells[(line, 1)].text
            if text != layout.NO_ASSUMPTIONS:
                assumptions.append(text)
            line += 1

    status_note = cells.get((status_row, 3))
    if status_note is not None and status_note.text:
        notes[(layout.FILING_STATUS_ROW, 0)] = status_note.text

    persons = _read_grid(cells, layout.HOUSEHOLD, layout.PERSONS,
                         marker[layout.PERSONS_BLOCK] + layout.PERSONS_HEADER_OFFSET,
                         marker[layout.PERSONS_BLOCK] + layout.PERSONS_SUBHEADER_OFFSET,
                         marker[layout.PERSONS_BLOCK] + layout.PERSONS_DATA_OFFSET,
                         refusals, originals, stated, edits, refused, notes)
    return tax_year, filing, persons, tuple(assumptions), root


def read_reviewed_lines(data: bytes):
    """The review gate, seen from `fill`: the `form lines` block of the Computed return tab, read
    back as ``{"<form> <line>": amount_string}`` — or None when the tab is absent or holds no
    lines (a `run` never wrote it, or the round computed nothing). `fill` refuses on None and on
    any mismatch with its own resolve: running the compute IS the review, and a rendering may
    only follow one."""
    cells = _result_cells(data)
    if cells is None:
        return None
    lines = {}
    for r in _block_rows(cells, layout.RESULT_LINES):
        amount = cells.get((r, 3))
        lines[cells[(r, 1)].text] = amount.text if amount is not None else ""
    return lines or None


def _result_cells(data: bytes):
    """The Computed return tab's cells, or None when the workbook has no such tab."""
    try:
        package = _Package(data)
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as fault:
        raise WorkbookRefused(
            f"not a workbook: {fault.__class__.__name__}: {fault}. Nothing was read from it.") from fault
    if layout.RESULT not in package.sheet_names():
        return None
    return package.cells(layout.RESULT)


def _block_rows(cells: dict, title: str) -> list:
    """The rows under one block title of the Computed return tab, up to the next title — each
    with text in column A. Empty when the title is absent."""
    rows = sorted({r for (r, _c) in cells})
    start = next((r for r in rows
                  if cells.get((r, 1)) is not None and cells[(r, 1)].text == title), None)
    if start is None:
        return []
    found = []
    for r in rows:
        if r <= start:
            continue
        head = cells.get((r, 1))
        if head is None or not head.text:
            continue
        if head.text in layout.RESULT_TITLES:
            break
        found.append(r)
    return found


def read_open_questions(data: bytes) -> tuple:
    """what the last round left open, as `((what is asked, where it is), ...)` in the order
    the Computed return tab lists them — Household first, then the tabs. Empty when the round
    completed, when nothing was run, or when the round stopped before it could say."""
    cells = _result_cells(data)
    if cells is None:
        return ()
    found = []
    for r in _block_rows(cells, layout.RESULT_OPEN):
        where = cells.get((r, 2))
        if where is not None and where.text:
            found.append((cells[(r, 1)].text, where.text))
    return tuple(found)


def read_outcome(data: bytes):
    """The outcome the last round wrote — `complete`, `incomplete`, ... — or None when no round
    answered (never run, or the round stopped before a response)."""
    cells = _result_cells(data)
    if cells is None:
        return None
    # The line is labelled with the same word as its block title, so it is found by the pair —
    # the label in column A beside a value in column B — not by walking the block.
    for r in sorted({r for (r, _c) in cells}):
        head, value = cells.get((r, 1)), cells.get((r, 2))
        if (head is not None and head.text == layout.RESULT_OUTCOME
                and value is not None and value.text):
            return value.text
    return None


def read_workbook(data: bytes) -> WorkbookRead:
    """Bytes in, facts out — or a named refusal for every cell that could not be read."""
    try:
        package = _Package(data)
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as fault:
        raise WorkbookRefused(
            f"not a workbook: {fault.__class__.__name__}: {fault}. Nothing was read from it.") from fault
    names = package.sheet_names()
    known = {layout.HOUSEHOLD, layout.RESULT} | {tab.name for tab in layout.TABS}
    unknown = [name for name in names if name not in known]
    if unknown:
        raise WorkbookRefused(
            f"this workbook has tab(s) {', '.join(repr(n) for n in unknown)}, which the column spec "
            f"does not define. A renamed tab is refused rather than guessed at: the tab says which "
            f"form its rows are, and a wrong guess files one form's figures on another's lines.")
    if layout.HOUSEHOLD not in names:
        raise WorkbookRefused(
            f"this workbook has no {layout.HOUSEHOLD} tab. Filing status and the persons on the "
            f"return live there, and no return can be computed without them.")

    refusals, originals, stated, edits, refused, notes = [], {}, [], [], {}, {}
    tax_year, filing, persons, assumptions, root = _household(package, refusals, originals, stated,
                                                              edits, refused, notes)

    facts = {}
    if filing is not None:
        facts[layout.FILING_STATUS_ROW] = filing
    facts.update(root)                                    # the root yes/no rows, when answered
    # `[{}]` is KEPT, exactly as a form tab keeps it. A counted row has a text cell, and text
    # either parses into the item or is refused — so a row that reads as `{}` had every cell it
    # held refused, a refusal exists, and nothing is sent. Filtering it out as "no persons" let
    # the rewrite synthesise a blank row in its place and the refused text vanished.
    if persons:
        facts["persons"] = persons

    for tab in layout.TABS:
        if tab.name not in names:
            continue
        items = _read_grid(package.cells(tab.name), tab.name, tab, layout.HEADER_ROW,
                           layout.SUBHEADER_ROW, layout.FIRST_DATA_ROW, refusals, originals,
                           stated, edits, refused, notes)
        if items:
            facts[tab.group] = items

    return WorkbookRead(tax_year=tax_year, facts=facts, originals=originals,
                        stated=tuple(stated), edits=tuple(edits),
                        refusals=tuple(refusals), assumptions=assumptions,
                        refused=refused, notes=notes)
