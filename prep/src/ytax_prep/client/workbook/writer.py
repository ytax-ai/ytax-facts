# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Facts to bytes — the workbook a person opens, corrects, and runs again.

FOUR CONVENTIONS, each one a thing the prototype rounds taught:

  * **Dollars, never cents.** `123.45` in the sheet; `Decimal(cents) / 100` to two places, always.
    A person reading `4825000` where wages belong will either correct a figure that was right or
    accept one that was not.
  * **ORIGINAL beside CURRENT.** What the Collector read sits, locked and grey, next to what will
    actually be computed on. `run` never mutates ORIGINAL — it is the record a correction is
    measured against, and a record that moves is not one.
  * **A not-read box is a visible, editable `0.00`**, with the library's own question in the note
    column. Not an omission, not a silent zero: a default somebody can see and change.
  * **A gap is EMPTY and yellow.** Absence is not zero. Writing `0.00` there would answer a question
    nobody asked.

This module NEVER imports `reader`. `layout` is the single source of what a tab looks like, so the
two directions cannot drift.

NO ADVICE ANYWHERE. Every string this file authors is in `layout.AUTHORED_TEXT` and is scanned by
test; every other string on a sheet is quoted verbatim from the library or from the service's own
response — provenance, not opinion.
"""
from __future__ import annotations

import re
from collections import namedtuple
from dataclasses import dataclass, field, replace
from decimal import Decimal

from ..documents import unread_box_questions
from ..interview import completeness_prompt
from . import layout, ooxml, styles

# Fragments that could only ever be an identifier. The fact schema makes these impossible
# (`additionalProperties:false` at every level) — this is the second control, on this side, so a
# `layout.TABS` entry that named one would stop here rather than produce a column for it.
# `tin_type` is deliberately NOT caught: the TIN's computational TYPE is a sanctioned derivative;
# its digits are what is forbidden, and no field spells them.
FORBIDDEN_HEADER_FRAGMENTS = (
    "name", "address", "ssn", "itin", "atin", "_ein", "birth_day", "date_of_birth",
    "phone", "email", "bank", "routing", "signature",
)
# The same screen on the CAPTION a column is headed with: phrases that only ever
# name an identifier. Not a bare "number" — the honest `Type of taxpayer ID (never the number)`
# would trip it — and not "social security", which `3 Social security wages` carries honestly.
FORBIDDEN_LABEL_PHRASES = ("security number", "identification number", "date of birth")


class WriterRefused(ValueError):
    """Nothing was written. Raised instead of producing a sheet with a wrong or unsayable cell."""


@dataclass
class CellState:
    """One field of one item, as the sheet will show it."""
    original: object = None      # what the Collector read; None means it read nothing
    current: object = None       # what will be computed on
    state: str = "CURRENT"       # a `styles.STATES` name
    note: str = ""               # the question, or the refusal, in the library's own words
    # A cell the reader refused, carried back as the kind it was (`ooxml.RefusedCell`). A dedicated
    # slot, deliberately: gating the carry-back on the TYPE of `current` let a cents literal typed
    # as a string reach a sheet as text, which is the cents sweep's exact category.
    refused: object = None       # the CURRENT / value cell, when it was the one refused
    original_refused: object = None   # the ORIGINAL cell, when it was the one refused


@dataclass
class Row:
    index: int                   # the fact path's index — `w2s[2]` is index 2
    cells: dict = field(default_factory=dict)
    note: str = ""               # said once for the whole row, ahead of the per-cell notes


@dataclass
class Model:
    """Everything the render needs, and nothing about how it is drawn.

    Both entry points build one of these — `build_workbook` at collect, `rewrite_workbook` at
    run — so the two produce the same file for the same content."""
    tax_year: object = None          # an int, or the `ooxml.RefusedCell` the reader refused
    filing_status: CellState = field(default_factory=CellState)
    # Household's root yes/no rows, `{path: CellState}` in `layout.ROOT_QUESTION_ROWS` order.
    root_answers: dict = field(default_factory=dict)
    persons: list = field(default_factory=list)
    groups: dict = field(default_factory=dict)
    assumptions: tuple = ()
    result: object = None            # the loop's response dict, or None before the first run
    stopped_because: str = ""
    extra_refusals: tuple = ()       # refusals naming no cell this workbook holds
    unplaced_gaps: tuple = ()        # gaps naming no cell this workbook holds; on Computed return
    open_gaps: tuple = ()            # every gap this round left open, located on Computed return


def dollars(cents) -> str:
    """Cents to a two-place dollar string. Exact — `Decimal`, never a float."""
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise WriterRefused(
            f"{cents!r} is not integer cents. Money is integer cents and never a float, a string, "
            f"or a boolean — `isinstance(True, int)` is True in Python, which is why the boolean is "
            f"named here rather than left to the int check.")
    return str((Decimal(cents) / 100).quantize(Decimal("0.01")))


def check_headers(tab) -> None:
    """Refuse a tab whose columns could carry an identifier.

    The SCHEMA lock lives in `tests/test_workbook_layout.py` (both directions; the container ships
    no schema directory). This is the runtime half: a fragment that could only be an identifier
    stops the write, so a `layout.TABS` entry naming one never produces a column at all."""
    for name in tab.fields:
        for fragment in FORBIDDEN_HEADER_FRAGMENTS:
            if fragment in name:
                raise WriterRefused(
                    f"{tab.name} declares a column {name!r}, which carries the identifier fragment "
                    f"{fragment!r}. This workbook holds no identity of any kind — the only person "
                    f"handle in the file is the index plus the role.")
    # The caption is what the person READS, so it is screened as the field name is — after the
    # field screen, so a forged field name is refused by its own name before any caption lookup.
    for name in tab.fields:
        label = layout.label_for(tab, name)
        lowered = label.lower()
        for phrase in FORBIDDEN_HEADER_FRAGMENTS + FORBIDDEN_LABEL_PHRASES:
            if phrase in lowered:
                raise WriterRefused(
                    f"{tab.name} would head the column {name!r} with {label!r}, which carries the "
                    f"identifier phrase {phrase!r}. This workbook holds no identity of any kind — "
                    f"the only person handle in the file is the index plus the role.")


def _cell_at_collect(path: str, value, unread: dict, asked: dict, money: bool,
                     original=None) -> CellState:
    """What ONE cell looks like the first time the workbook is written.

    Four states, and the split that matters is between the two that carry a figure and the two that
    do not: a not-read box carries a visible `0.00` a person can correct, and a gap carries nothing
    at all, because absence is not zero."""
    if path in unread:
        # An unread box the service also asks as a REQUIRED question is a gap, not a
        # default: its `0.00` would read back as an answer and compute a $0 return nobody checked.
        # It becomes the SAME cell as every other required gap — empty, yellow, worded with the
        # question's own ask and provenance — because leaving it empty makes the return REFUSE
        # ("required and was not supplied"), the opposite of the not-read note's "computed as
        # though the box were empty". Its NOTREAD twin — an unread box that is NOT required
        # (box 2, say) — keeps the correctable `0.00` and the not-read words, which are true there.
        question = asked.get(path)
        if question is not None and not getattr(question, "optional", False):
            return CellState(state="GAP", note=f"{question.ask} {question.why}")
        return CellState(original=None, current=0 if money else None,
                         state="NOTREAD", note=unread[path])
    if value is not None:
        # `From the form` is what the PAPER says, when the caller knows it: an amount the person
        # changed (in this workbook, taken back as their answer) keeps the form's figure beside it
        # and is marked CHANGED, as a computed-again workbook already marks it. Without one, the
        # value is both — the first write, where nothing has been changed yet.
        if money and original is not None and original != value:
            return CellState(original=original, current=value, state="CHANGED")
        return CellState(original=value, current=value, state="CURRENT")
    question = asked.get(path)
    if question is not None:
        # An OPTIONAL question is an invitation with a stated default — its wording
        # reaches the note, but the cell must not wear the GAP paint: yellow says "the return
        # needs this", and an optional field does not. It stays the typable cell it was.
        state = "CURRENT" if getattr(question, "optional", False) else "GAP"
        return CellState(state=state, note=f"{question.ask} {question.why}")
    return CellState()


def _rows_at_collect(tab, items, unread: dict, asked: dict, originals: dict | None = None) -> list:
    rows = []
    for index, item in enumerate(items or []):
        cells = {}
        for name in tab.fields:
            path = f"{tab.group}[{index}].{name}"
            cells[name] = _cell_at_collect(path, item.get(name), unread, asked,
                                           layout.is_money(name), (originals or {}).get(path))
        rows.append(Row(index=index, cells=cells))
    return rows


def added_rows(tab, start: int, count: int, gap_fields) -> list:
    """`count` rows after the `start` rows a group already holds, for forms the person said they
    have and will type in (decided 2026-09-28). Each carries its `Item` index, the fields
    the return needs painted GAP yellow, and one note naming the form; nothing else. Left empty, a
    row is only its index and note, which the reader takes as no row at all."""
    words = dict(layout.RECEIVED_FORMS).get(tab.group, tab.name)
    rows = []
    for index in range(start, start + count):
        cells = {name: CellState(state="GAP") if name in gap_fields else CellState()
                 for name in tab.fields}
        rows.append(Row(index=index, cells=cells,
                        note=layout.ADDED_ROW_NOTE.format(form=words)))
    return rows


def _gap_fields(group: str, case: dict) -> frozenset:
    """The fields a row of `group` must carry for the return to take it. `person` only on a joint
    return: with one filer the page derives it, so a yellow box there would ask for nothing."""
    from ...facts import mapper
    needed = set(mapper.REQUIRED_ITEM_FIELDS.get(group, ()))
    if case.get("filing_status") != "mfj":
        needed.discard("person")
    return frozenset(needed)


def model_from_case(case: dict, unread: dict, asked: dict, result=None,
                    originals: dict | None = None, added: dict | None = None) -> Model:
    """The collect-side model: the facts the documents produced, plus every open question."""
    status = case.get("filing_status")
    if status is not None:
        filing = CellState(current=status, state="CURRENT")
    else:
        question = asked.get(layout.FILING_STATUS_ROW)
        filing = CellState(state="GAP", note=("" if question is None
                                              else f"{question.ask} {question.why}"))
    # the root yes/no rows — the same two states the filing-status row has.
    root = {}
    for path in layout.ROOT_QUESTION_ROWS:
        value = case.get(path)
        if value is not None:
            root[path] = CellState(current=value, state="CURRENT")
        else:
            question = asked.get(path)
            # a row a root yes has not reached is a plain blank, not a gap.
            root[path] = CellState(state="GAP" if question is not None else "CURRENT",
                                   note=("" if question is None
                                         else f"{question.ask} {question.why}"))

    persons = _rows_at_collect(layout.PERSONS, case.get("persons"), unread, asked)
    if not persons:
        # No person at all. The service reports ONE gap (`persons`), not one per field, so the
        # workbook offers one empty row rather than leaving a person nowhere to be entered.
        question = asked.get("persons")
        note = "" if question is None else f"{question.ask} {question.why}"
        persons = [Row(index=0, cells={name: CellState(state="GAP", note=note)
                                       for name in layout.PERSONS.fields})]

    groups = {}
    for tab in layout.TABS:
        items = case.get(tab.group) or []
        rows = _rows_at_collect(tab, items, unread, asked, originals) if items else []
        more = int((added or {}).get(tab.group) or 0)
        if more > 0:
            # a form with no document read still gets its tab when the person counted one
            rows += added_rows(tab, len(items), more, _gap_fields(tab.group, case))
        if rows:
            groups[tab.group] = rows

    return Model(tax_year=case.get("tax_year"), filing_status=filing, root_answers=root,
                 persons=persons,
                 groups=groups,
                 assumptions=tuple((result or {}).get("assumptions") or ()),
                 result=result)


def build_workbook(case: dict, documents: list, questions, result=None,
                   originals: dict | None = None, added: dict | None = None) -> bytes:
    """`collect`: documents in, workbook out. The one public entry point for a first write.
    `originals` is `{path: cents}` of what the paper says, where an answer may differ from it.
    `added` is `{group: count}`: rows to type in, after the group's own, for forms the person said
    they have (`added_rows`)."""
    unread = unread_box_questions(list(documents))
    asked = {question.fact: question for question in questions}
    return render(model_from_case(case, unread, asked, result, originals, added))


def _text(row: int, col: int, value, state: str, table) -> ooxml.Cell:
    if value in (None, ""):
        return ooxml.Cell(row, col, None, None, styles.style_id(state))
    return ooxml.Cell(row, col, "s", table.add(str(value)), styles.style_id(state))


def _carried(row: int, col: int, refused, style: int, table) -> ooxml.Cell:
    """A cell the reader refused, put back as EXACTLY the kind it was, so the next read refuses it
    again by the same name. A boolean stays `t="b"`; a formula keeps its text and its cached value;
    text stays text — and so does a number-typed cell the parser refused (`12.345`, `inf`), because
    a numeric `<v>` would be accepted on the way round and a refusal would become a figure."""
    if refused.kind == "f":
        # The whole `<f>` element — text AND attributes — so a shared formula's child, which has
        # no text, goes back as `<f t="shared" si="0"/>` rather than crashing the rewrite or being
        # laundered into its cached value as text.
        return ooxml.Cell(row, col, "f", refused.text or None, style, formula=refused.formula)
    if refused.kind == "b":
        # The reader refuses the FILE for a boolean that is not 0 or 1, so none reaches here.
        return ooxml.Cell(row, col, "b", refused.text, style)
    return ooxml.Cell(row, col, "s", table.add(refused.text), style)


def _money_cell(row: int, col: int, cents, state: str, table, refused=None) -> ooxml.Cell:
    style = styles.style_id(state, True)
    if refused is not None:
        return _carried(row, col, refused, style, table)
    if cents is None:
        return ooxml.Cell(row, col, None, None, style)
    return ooxml.Cell(row, col, "n", dollars(cents), style)


def _plain_cell(row: int, col: int, name: str, cell: CellState, table) -> ooxml.Cell:
    style = styles.style_id(cell.state, False)
    if cell.refused is not None:
        return _carried(row, col, cell.refused, style, table)
    value = cell.current
    if value is None:
        return ooxml.Cell(row, col, None, None, style)
    if name in layout.BOOLEAN_FIELDS:
        # Written as the same word the dropdown offers, so a person's edit and the writer's own
        # output are the one vocabulary — which is why the two words are read out of that
        # vocabulary rather than spelled again here.
        true, false = layout.BOOLEAN_CHOICES[0], layout.BOOLEAN_CHOICES[1]
        return ooxml.Cell(row, col, "s", table.add(true if value else false), style)
    if isinstance(value, bool):
        raise WriterRefused(f"{name} is not a boolean field, and {value!r} is a boolean")
    if isinstance(value, int):
        # The person column shows the Household tab's `#` (people count from 1); the wire's
        # `person` is 0-based, and the reader undoes this on the way in. Every other integer is
        # written as itself.
        shown = layout.row_number(value) if name == "person" else value
        return ooxml.Cell(row, col, "n", str(shown), style)
    return ooxml.Cell(row, col, "s", table.add(str(value)), style)


def _grid(tab, rows, table, header_row: int, subheader_row: int, first_data_row: int):
    """The two header rows, the data rows and the spare rows for one item grid — the shape every
    form tab and the Household persons block share, so they cannot drift apart.

    The three rows are PASSED IN from `layout`'s own constants rather than derived here as `+1` and
    `+2`: a form tab's grid sits at the top of its sheet, and the persons block floats below an
    assumptions block that grows and shrinks, so the offsets belong to the geometry and not to this
    function."""
    check_headers(tab)
    cells, merges, validations = [], [], []
    sub = subheader_row
    first = first_data_row
    columns = layout.columns_for(tab)

    for column in columns:
        here = ooxml.ref(header_row, column.index)
        below = ooxml.ref(sub, column.index)
        if column.kind == "index":
            cells.append(_text(header_row, column.index, layout.INDEX_HEADER, "LABEL", table))
            merges.append(f"{here}:{below}")
        elif column.kind == "note":
            cells.append(_text(header_row, column.index, layout.NOTE_HEADER, "LABEL", table))
            merges.append(f"{here}:{below}")
        elif column.kind == "original":
            # THE FORM'S OWN CAPTION, never the field name.
            cells.append(_text(header_row, column.index, layout.label_for(tab, column.field),
                               "LABEL", table))
            # The pair's right edge is the CURRENT column as `layout` places it, not `+ 1`.
            right = layout.column_index(tab, column.field, "current")
            merges.append(f"{here}:{ooxml.ref(header_row, right)}")
            cells.append(_text(sub, column.index, layout.ORIGINAL_SUBHEADER, "LABEL", table))
        elif column.kind == "current":
            cells.append(_text(sub, column.index, layout.CURRENT_SUBHEADER, "LABEL", table))
        else:
            cells.append(_text(header_row, column.index, layout.label_for(tab, column.field),
                               "LABEL", table))
            merges.append(f"{here}:{below}")

    for offset, row in enumerate(rows):
        line = first + offset
        # PEOPLE COUNT FROM 1: the `#` a person reads is `row_number(index)`; the path stays 0-based.
        cells.append(ooxml.Cell(line, 1, "n", str(layout.row_number(row.index)),
                                styles.style_id("LABEL")))
        notes = [row.note] if row.note else []
        for column in columns:
            if column.kind in ("index", "note"):
                continue
            cell = row.cells.get(column.field) or CellState()
            if column.kind == "original":
                cells.append(_money_cell(line, column.index, cell.original, "ORIGINAL", table,
                                         cell.original_refused))
            elif column.kind == "current":
                cells.append(_money_cell(line, column.index, cell.current, cell.state, table,
                                         cell.refused))
            else:
                cells.append(_plain_cell(line, column.index, column.field, cell, table))
            if cell.note and column.kind != "original":
                notes.append(layout.NOTE_TEMPLATE.format(label=layout.label_for(tab, column.field),
                                                         note=cell.note))
        cells.append(_text(line, layout.note_index(tab),
                           layout.NOTE_SEPARATOR.join(notes), "DEFAULT", table))

    # THE SPARE ROWS ARE WRITTEN, NOT LEFT ABSENT. Every sheet carries `<sheetProtection>` and
    # `styles.LOCKED` includes DEFAULT, so `cellXfs[0]` — which is what an ABSENT cell resolves to —
    # is LOCKED. A spare row with no cells in it is a row nobody can type in, and the dropdown
    # spanning it would offer the schema's codes into cells that refuse the keystroke. So every
    # column a person may fill gets a blank CURRENT-styled cell, which is unlocked.

    # The index, ORIGINAL and note columns stay ABSENT on purpose: locked by absence, which is what
    # keeps the record of what the Collector read out of reach for free, and the note column is
    # written by this file rather than typed into.
    spare_from = first + len(rows)
    for line in range(spare_from, spare_from + layout.SPARE_ROWS):
        for column in columns:
            if column.kind in ("current", "value"):
                cells.append(ooxml.Cell(line, column.index, None, None,
                                        styles.style_id("CURRENT", column.kind == "current")))

    last = spare_from + layout.SPARE_ROWS - 1
    for column in columns:
        if column.kind != "value":
            continue
        codes = layout.choices_for_field(column.field)
        if codes and len(",".join(codes)) + 2 <= 255:
            letter = ooxml.col_letter(column.index)
            validations.append((f"{letter}{first}:{letter}{last}", codes))
        # A list past 255 characters cannot ride an INLINE validation (the format truncates it,
        # and ooxml refuses to write a dropdown that offers fewer codes than the schema accepts).
        # `relationship`'s 25 dictionary codes are that case: the cell goes out WITHOUT a
        # dropdown, the prompt in the note carries every code, and the reader still refuses a
        # wrong word by name — the vocabulary is enforced either way; only the offer's mechanism
        # differs. A range-referenced list (a codes sheet) is the recorded follow-up if the typing
        # burden matters in practice.
    return cells, merges, validations, first + len(rows)


def _cols_for(tab):
    """Column widths — one `<col>` per column, strictly increasing, so guard (a) cannot trip."""
    widths = []
    for column in layout.columns_for(tab):
        if column.kind == "index":
            widths.append(ooxml.Col(column.index, column.index, 5, False))
        elif column.kind == "note":
            widths.append(ooxml.Col(column.index, column.index, 60, False))
        elif column.kind == "original":
            widths.append(ooxml.Col(column.index, column.index, 16, False))
        else:
            widths.append(ooxml.Col(column.index, column.index, 18, False))
    return widths


# the Household tab's column A carries two things — the root rows' plain labels (46 of them,
# the longest 107 characters) and the persons block's `#` index — and `_cols_for(layout.PERSONS)`
# sized it as the index column, width 5, so every root row a unit added overflowed further. Sized
# from the labels it holds and capped so the tab still fits a screen; every style wraps, so a label
# past the cap folds rather than spills. Locked by `HouseholdColumnAFitsItsLabelsTest`.
HOUSEHOLD_LABEL_WIDTH_CAP = 70


def _household_widths() -> list:
    rows = (layout.TAX_YEAR_ROW, layout.FILING_STATUS_ROW, *layout.ROOT_QUESTION_ROWS)
    longest = max(len(layout.label_for(layout.HOUSEHOLD_GROUP, row)) for row in rows)
    width = min(HOUSEHOLD_LABEL_WIDTH_CAP, longest + 2)
    return [col._replace(width=width) if col.first == 1 else col
            for col in _cols_for(layout.PERSONS)]


# The Household tab's rows, computed once per model: the root question rows by path, the row the
# assumptions block starts on, and the row the persons block's label sits on. `_household_sheet`
# draws from it and `_locate` names cells from it, so the two cannot disagree about where the
# floating persons block landed this round.
_HouseholdRows = namedtuple("_HouseholdRows", "root assumptions persons")


def _household_rows(model: Model) -> _HouseholdRows:
    root = {}
    row = 4                                        # rows 1-3: title, tax year, filing status
    for path in layout.ROOT_QUESTION_ROWS:
        root[path] = row
        row += 1
    row += 1                                       # one blank row ends the block
    assumptions = row
    row += 1 + len(model.assumptions or (layout.NO_ASSUMPTIONS,))
    row += 1                                       # one blank row ends the block
    return _HouseholdRows(root=root, assumptions=assumptions, persons=row)


def _placeable(path: str) -> bool:
    """Does `_locate` name a cell for this path? The whole-row `persons` gap counts: its row is
    on the sheet even though no single cell is."""
    return path == layout.PERSONS_BLOCK or layout.holds(path)


def _locate(model: Model, path: str):
    """WHERE a gap's cell is, as `(sort key, text)` — or None for a path no cell holds.

    The text leads with the sheet-qualified reference (`Household!B54`), which is what Excel's
    Name Box takes; a grid cell adds the row as the `Item` column counts it and the column's
    caption; the whole-row `persons` gap of the first round names the row's cells. The key orders
    the list the way the workbook is read: Household, then the tabs in their order, top down."""
    rows = _household_rows(model)
    if path == layout.FILING_STATUS_ROW:
        return (0, 3, 2), layout.sheet_ref(layout.HOUSEHOLD, ooxml.ref(3, 2))
    if path in rows.root:
        return (0, rows.root[path], 2), layout.sheet_ref(layout.HOUSEHOLD,
                                                         ooxml.ref(rows.root[path], 2))
    persons_first = rows.persons + layout.PERSONS_DATA_OFFSET
    if path == layout.PERSONS_BLOCK:
        fields = layout.PERSONS.fields
        first = ooxml.ref(persons_first, layout.column_index(layout.PERSONS, fields[0], "value"))
        last_kind = "current" if layout.is_money(fields[-1]) else "value"
        last = ooxml.ref(persons_first, layout.column_index(layout.PERSONS, fields[-1], last_kind))
        return (0, persons_first, 0), layout.ROW_LOCATION.format(
            first=layout.sheet_ref(layout.HOUSEHOLD, first), last=last,
            row=layout.describe_row(layout.PERSONS.group, 0))
    parts = layout.split_path(path)
    if parts is None:
        return None
    group, index, field = parts
    tab = layout.tab_for_group(group)
    if tab is None or field not in tab.fields:
        return None
    kind = "current" if layout.is_money(field) else "value"
    col = layout.column_index(tab, field, kind)
    if tab is layout.PERSONS:
        order, line = 0, persons_first + index
    else:
        order, line = 1 + layout.TABS.index(tab), layout.FIRST_DATA_ROW + index
    return (order, line, col), layout.GRID_LOCATION.format(
        at=layout.sheet_ref(tab.name, ooxml.ref(line, col)),
        row=layout.describe_row(group, index), caption=layout.label_for(tab, field))


# a Household root row's note is written in column C, which the persons block below sizes
# as an ordinary 18-wide value column — so once rows took the height their text needs, a note
# became a tall strip eighteen characters wide. The note spans this many columns instead (C:F,
# 72 characters — the width the other tabs' Notes column has), read from its top-left cell as
# before. The tab's `<cols>` stay the persons block's own.
HOUSEHOLD_NOTE_SPAN = 4


def _household_note_merge(row: int) -> str:
    return f"{ooxml.col_letter(3)}{row}:{ooxml.col_letter(2 + HOUSEHOLD_NOTE_SPAN)}{row}"


def _household_sheet(model: Model, table):
    """Three blocks, in order: filing status; assumptions; persons.

    The assumptions block GROWS AND SHRINKS between runs, so the persons block below it does not sit
    at a fixed row — it is found by its own label in column A, and `_household_rows` says where it
    is this round. Nothing on this tab is money, so no ORIGINAL geometry is needed here, which is
    why the floating block costs nothing."""
    width = layout.note_index(layout.PERSONS)
    edge = ooxml.col_letter(width)
    cells, merges, validations = [], [], []

    cells.append(_text(1, 1, layout.BLOCK_HOUSEHOLD, "LABEL", table))
    merges.append(f"A1:{edge}1")

    # Column A carries the row's plain LABEL — `Tax year`, `Filing status` — and the reader finds
    # each row by that label; the path constants stay the wire's names and never reach the sheet.
    cells.append(_text(2, 1, layout.label_for(layout.HOUSEHOLD_GROUP, layout.TAX_YEAR_ROW),
                       "LABEL", table))
    if isinstance(model.tax_year, ooxml.RefusedCell):
        # The year the reader refused, carried back as the cell it was, red, for the person to
        # see and correct.
        cells.append(_carried(2, 2, model.tax_year, styles.style_id("INVALID"), table))
    elif model.tax_year is not None:
        if isinstance(model.tax_year, bool) or not isinstance(model.tax_year, int):
            raise WriterRefused(f"tax_year {model.tax_year!r} is not an integer year. It is written "
                                f"as a number, and a string that happens to spell one is not one.")
        cells.append(ooxml.Cell(2, 2, "n", str(model.tax_year), styles.style_id("ORIGINAL")))

    cells.append(_text(3, 1, layout.label_for(layout.HOUSEHOLD_GROUP, layout.FILING_STATUS_ROW),
                       "LABEL", table))
    cells.append(_plain_cell(3, 2, layout.FILING_STATUS_ROW, model.filing_status, table))
    cells.append(_text(3, 3, model.filing_status.note, "DEFAULT", table))
    merges.append(_household_note_merge(3))
    validations.append(("B3", layout.choices_for_field(layout.FILING_STATUS_ROW)))

    # the root yes/no rows, one under the other, each found by its label like the two above.
    rows = _household_rows(model)
    for path in layout.ROOT_QUESTION_ROWS:
        row = rows.root[path]
        cell = model.root_answers.get(path) or CellState()
        cells.append(_text(row, 1, layout.label_for(layout.HOUSEHOLD_GROUP, path), "LABEL", table))
        if path in layout.ROOT_MONEY_ROWS:
            # a root amount row is a money cell — dollars shown, dollars typed, no dropdown.
            cells.append(_money_cell(row, 2, cell.current, cell.state, table, cell.refused))
        else:
            cells.append(_plain_cell(row, 2, path, cell, table))
            validations.append((f"B{row}", layout.choices_for_field(path)))
        cells.append(_text(row, 3, cell.note, "DEFAULT", table))
        merges.append(_household_note_merge(row))

    row = rows.assumptions
    cells.append(_text(row, 1, layout.ASSUMPTIONS_BLOCK, "LABEL", table))
    cells.append(_text(row, 2, layout.BLOCK_ASSUMPTIONS, "LABEL", table))
    merges.append(f"B{row}:{edge}{row}")
    row += 1
    for text in (model.assumptions or (layout.NO_ASSUMPTIONS,)):
        cells.append(_text(row, 1, text, "DEFAULT", table))
        merges.append(f"A{row}:{edge}{row}")
        row += 1
    row = rows.persons

    cells.append(_text(row, 1, layout.PERSONS_BLOCK, "LABEL", table))
    cells.append(_text(row, 2, layout.BLOCK_PERSONS, "LABEL", table))
    merges.append(f"B{row}:{edge}{row}")

    grid_cells, grid_merges, grid_validations, _end = _grid(
        layout.PERSONS, model.persons, table,
        row + layout.PERSONS_HEADER_OFFSET,
        row + layout.PERSONS_SUBHEADER_OFFSET,
        row + layout.PERSONS_DATA_OFFSET)
    cells += grid_cells
    merges += grid_merges
    validations += grid_validations
    return ooxml.sheet_xml(cells, _household_widths(), merges, validations, strings=table.strings)


def _return_values(model: Model) -> dict:
    """`{path: value}` of every answer this workbook carries — the Household rows, each person and
    each document row — as the fact paths `derived_from` names them (`group[].field`, a row's
    index kept apart). Only what is present: a blank is not an input to anything."""
    values = {}
    for path, cell in (model.root_answers or {}).items():
        values[path] = [(None, cell.current)]
    if model.filing_status is not None and model.filing_status.current is not None:
        values["filing_status"] = [(None, model.filing_status.current)]
    for group, rows in (("persons", model.persons), *((g, r) for g, r in (model.groups or {}).items())):
        for r in rows or []:
            for name, cell in (r.cells or {}).items():
                values.setdefault(f"{group}[].{name}", []).append((r.index, cell.current))
    return values


def _shown(name: str, value) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if name.endswith("_cents") and isinstance(value, int):
        return dollars(value)
    return str(value)


def _based_on(entry: dict, values: dict, lines: dict) -> str:
    """What THIS line was computed from on THIS return, so the workbook explains each
    calculation: the other Form 1040
    lines it is built on, by number, name and figure; then the answers and document boxes this
    return actually carries, in the form's own words, with their figures. `derived_from` is the
    engine's own dependency list — static, everything the line COULD depend on — so an input the
    return does not carry, a blank, a zero or a no is left out. Nothing here is computed."""
    said = []
    for path in entry.get("derived_from") or []:
        if path.startswith("/"):
            other = lines.get(path)
            amount = (other or {}).get("value_cents")
            if (other is not None and other.get("line_id") != entry.get("line_id")
                    and amount not in (0, None)):          # a line at 0.00 adds nothing to say
                said.append(f"line {other['line_id']} {other.get('label', '')}"
                            + (f" {dollars(amount)}" if isinstance(amount, int) else ""))
            continue
        for index, value in values.get(path, []):
            if value in (None, "", 0, False):
                continue
            name = path.rsplit(".", 1)[-1]
            where = layout.describe(path.replace("[]", f"[{index}]") if index is not None else path)
            said.append(f"{where}: {_shown(name, value)}")
    if said:     # the copy standard's own form for a computed figure
        return "This amount is based on: " + "; ".join(dict.fromkeys(said)) + "."
    return "Nothing on this return reports an amount for this line."


def _result_sheet(model: Model, table):
    """Written fresh each run. PROVENANCE LANGUAGE ONLY: every string here is either the service's
    own words or a citation. No advice, no recommendation, no accuracy claim."""
    cells, merges = [], []
    row = 1

    def block(title):
        nonlocal row
        cells.append(_text(row, 1, title, "RESULT", table))
        merges.append(f"A{row}:D{row}")
        row += 1

    def line(label, value="", extra=""):
        nonlocal row
        cells.append(_text(row, 1, label, "LABEL", table))
        cells.append(_text(row, 2, value, "DEFAULT", table))
        cells.append(_text(row, 3, extra, "DEFAULT", table))
        row += 1

    widths = [ooxml.Col(1, 1, 26, False), ooxml.Col(2, 2, 40, False), ooxml.Col(3, 4, 60, False),
              ooxml.Col(5, 5, 90, False)]
    response = model.result

    if response is None:
        # A ROUND CAN END WITH NO RESPONSE AT ALL — the reader refused and nothing was sent, or the
        # service raised instead of answering. Those rounds still have to SAY so here: a Computed
        # return tab reading "no run yet" after a refused run is the silent failure this whole
        # surface exists to close.
        if not (model.stopped_because or model.extra_refusals):
            block(layout.RESULT)
            line(layout.NO_RUN_YET)
            return ooxml.sheet_xml(cells, widths, merges, strings=table.strings)
        block(layout.RESULT_OUTCOME)
        line(layout.RESULT_STOPPED, model.stopped_because)
        block(layout.RESULT_REFUSALS)
        for text in model.extra_refusals:
            cells.append(_text(row, 1, text, "DEFAULT", table))
            merges.append(f"A{row}:D{row}")
            row += 1
        return ooxml.sheet_xml(cells, widths, merges, strings=table.strings)

    block(layout.RESULT_OUTCOME)
    line(layout.RESULT_OUTCOME, response.get("outcome") or "")
    line(layout.RESULT_STOPPED, model.stopped_because)

    # WHERE EACH OPEN QUESTION IS, first — before the lines, because a person who has to go
    # somewhere else reads this block and not the rest. Column A is the cell in the form's words
    # (the same words the sheet's `Item` column and headers use), column B the sheet-qualified
    # cell with its row and caption, column C the service's own why, unchanged. Ordered as the
    # workbook is read: Household top down, then each tab. A gap no cell holds is in its own
    # block below and is not repeated here.
    block(layout.RESULT_OPEN)
    located = []
    for gap in model.open_gaps:
        path = gap.get("fact") or ""
        where = _locate(model, path)
        if where is not None:
            located.append((where[0], where[1], path, gap.get("why") or ""))
    for _key, where, path, why in sorted(located, key=lambda entry: entry[0]):
        said = (layout.describe_row(layout.PERSONS.group, 0) if path == layout.PERSONS_BLOCK
                else layout.describe(path))
        line(said, where, why)

    block(layout.RESULT_PROVENANCE)
    for key in ("engine_version", "dictionary_hash", "input_hash", "computed_at"):
        line(key, (response.get("provenance") or {}).get(key) or "")

    block(layout.RESULT_LINES)
    values = _return_values(model)
    from ...service.lines import LINE_MAP
    by_path = {spec["fact_path"]: spec["line_id"] for spec in LINE_MAP}
    served = {entry.get("line_id"): entry for form in response.get("forms") or []
              for entry in form.get("lines") or []}
    lines_by_path = {path: served[line_id] for path, line_id in by_path.items() if line_id in served}
    for form in response.get("forms") or []:
        for entry in form.get("lines") or []:
            amount = entry.get("value_cents")
            citation = entry.get("citation") or {}
            line(f"{form.get('form_id', '')} {entry.get('line_id', '')}".strip(),
                 entry.get("label") or "",
                 (dollars(amount) if isinstance(amount, int) and not isinstance(amount, bool)
                  else entry.get("enum_value") or ""))
            cells.append(_text(row - 1, 4,
                               f"{citation.get('source_doc', '')} {citation.get('locator', '')}"
                               .strip(), "DEFAULT", table))
            cells.append(_text(row - 1, 5, _based_on(entry, values, lines_by_path), "DEFAULT", table))

    block(layout.RESULT_REFUSALS)
    for refusal in response.get("refusals") or []:
        citation = refusal.get("citation") or {}
        # a knockout's words (the dictionary's own sentence) first, its path second;
        # a refusal with no words keeps its boundary where it was.
        words = refusal.get("words")
        line(refusal.get("code") or "", words or refusal.get("boundary") or "",
             (refusal.get("boundary") or "") if words
             else f"{citation.get('source_doc', '')} {citation.get('locator', '')}".strip())
    for text in model.extra_refusals:
        cells.append(_text(row, 1, text, "DEFAULT", table))
        merges.append(f"A{row}:D{row}")
        row += 1

    # A GAP THAT PINS NO CELL IS STILL SAID. A root path (`persons`, `filing_status` when its cell
    # already holds a value) or a field no tab carries has no cell to be yellow in; written here,
    # in the service's own words, so that a gap never vanishes between the response and the sheet.
    block(layout.RESULT_GAPS)
    for gap in model.unplaced_gaps:
        # A PERSON READS THIS TAB, so column A is the form's own words. The raw path follows in
        # the next column — machine provenance, the way a refusal carries its `fact` — and the
        # service's own `why` sits beside it, unchanged.
        line(layout.describe(gap.get("fact") or ""), gap.get("fact") or "",
             gap.get("why") or "")

    block(layout.RESULT_BOUNDARY)
    boundary = response.get("unasked_boundary") or []
    prompt = completeness_prompt(boundary)
    if prompt:
        cells.append(_text(row, 1, prompt, "DEFAULT", table))
        merges.append(f"A{row}:D{row}")
        row += 1
    for entry in boundary:
        line(entry.get("fact_class") or "", entry.get("why_not_supported") or "")

    block(layout.RESULT_ASSUMPTIONS)
    for text in model.assumptions or ():
        cells.append(_text(row, 1, text, "DEFAULT", table))
        merges.append(f"A{row}:D{row}")
        row += 1

    return ooxml.sheet_xml(cells, widths, merges, strings=table.strings)


def render(model: Model) -> bytes:
    """One model, one deterministic package. Household, each non-empty form, Computed return."""
    table = ooxml.StringTable()
    sheets = [(layout.HOUSEHOLD, _household_sheet(model, table))]
    for tab in layout.TABS:
        rows = model.groups.get(tab.group)
        if not rows:
            continue                      # a group with nothing in it produces no tab
        cells, merges, validations, _end = _grid(
            tab, rows, table, layout.HEADER_ROW, layout.SUBHEADER_ROW, layout.FIRST_DATA_ROW)
        sheets.append((tab.name, ooxml.sheet_xml(cells, _cols_for(tab), merges, validations,
                                                 strings=table.strings)))
    sheets.append((layout.RESULT, _result_sheet(model, table)))

    parts = {"xl/workbook.xml": ooxml.workbook_xml([name for name, _xml in sheets]),
             "xl/styles.xml": styles.styles_xml(),
             "xl/sharedStrings.xml": ooxml.sst_xml(table.strings)}
    for position, (_name, sheet_xml) in enumerate(sheets, start=1):
        parts[f"xl/worksheets/sheet{position}.xml"] = sheet_xml
    return ooxml.package(parts)



@dataclass
class _Round:
    """What one round brought back, threaded through every cell decision.

    `used` collects the gap paths some cell answered for — a repainted cell, a created row, the
    synthesised persons row, a refused beyond-the-slot index. Every gap NOT in it is written on
    the Computed return tab
    under its own heading, so a gap the service named can never vanish between the response and
    the sheet. `assumed` marks the entries `model_from_read` added FROM an assumption, which are
    not the service's gaps and are not reported as such when the cell already holds an answer."""
    invalid: dict
    gaps: dict
    refused: dict                  # `read.refused`: each refused cell, as the kind it was
    stated_at: str
    # Whether the payload REACHED the service this round. A response is proof that it did; a
    # refusal the service raised (a `TransportRefused`) is proof too, and the caller says so. A
    # round the reader or the projector refused sent nothing, and a cell that did not cross was
    # not stated — writing "stated as 0.00 on <when>" for it would be a claim about a round that
    # never happened.
    crossed: bool = False
    used: set = field(default_factory=set)
    assumed: set = field(default_factory=set)
    beyond: set = field(default_factory=set)   # gaps refused as beyond the next free slot
    extra: list = field(default_factory=list)


def _cell_at_run(path: str, value, original, money: bool, round: _Round) -> CellState:
    """What ONE cell looks like after a round. Every state comes from the two VALUES.

    **NOT-READ becomes STATED.** A blank ORIGINAL beside a filled CURRENT is a figure nobody
    extracted and somebody sent — a `0.00` default that crossed, or a row a person typed. Both are
    now a statement, and the note says so with the run's own timestamp.

    **CHANGED is a comparison**, never a stored flag: a flag is a claim about the past that nothing
    checks. Only a money field can be CHANGED, because only a money field has an ORIGINAL beside it.
    """
    original_refused = original if isinstance(original, ooxml.RefusedCell) else None
    if original_refused is not None:
        original = None
    refused = round.refused.get(path)
    note = round.invalid.get(path, "")
    if refused is not None:
        # THE READER REFUSED THIS CELL. It goes back as exactly the kind it was — boolean, formula,
        # text — in INVALID red, beside the ORIGINAL as it was read, so the next run refuses the
        # same cell by the same name until a figure is typed. Blanking it would leave blank beside
        # blank on the next read, which is ABSENT: the form would cross without the figure.
        return CellState(original=original, original_refused=original_refused, refused=refused,
                         state="INVALID", note=note)
    if original_refused is not None:
        # THE READER REFUSED THE ORIGINAL — a foreign edit to a locked column. It goes back as it
        # was, under its own style, and keeps refusing. The CURRENT beside it parsed and is not the
        # cell refused: its number, its type and its style are left alone; only the note says.
        return CellState(original_refused=original_refused, current=value, state="CURRENT",
                         note=note)
    if path in round.invalid:
        # A refusal the service raised names a value the reader parsed, and `value` is it: kept,
        # painted, never blanked.
        return CellState(original=original, current=value, state="INVALID", note=note)
    if value is None:
        gap = round.gaps.get(path)
        if gap is not None:
            round.used.add(path)
            return CellState(original=original, current=None, state="GAP",
                             note=gap.get("why") or "")
        return CellState(original=original)
    if money and original is None:
        if not round.crossed:
            # Nothing was sent, so nothing was stated. The figure nobody extracted keeps the
            # pale-blue NOT-READ mark it carries until a round crosses. The cell itself derives
            # no note; whatever the note column already said survives through the row-level
            # carry in `model_from_read` — text only, this round adds nothing to it.
            return CellState(original=None, current=value, state="NOTREAD")
        shown = dollars(value)
        return CellState(original=None, current=value, state="CURRENT",
                         note=layout.STATED_TEMPLATE.format(value=shown, when=round.stated_at))
    if money and original is not None and value != original:
        return CellState(original=original, current=value, state="CHANGED")
    return CellState(original=original, current=value, state="CURRENT")


def _gap_row(tab, index: int, round: _Round, note: str) -> Row:
    """An empty GAP-styled row the service asked for: each cell carries its own gap's words if the
    service named that field, and the row says ONCE why it is there."""
    cells = {}
    for name in tab.fields:
        path = f"{tab.group}[{index}].{name}"
        gap = round.gaps.get(path)
        if gap is not None:
            round.used.add(path)
        cells[name] = CellState(state="GAP", note=(gap.get("why") or "") if gap else "")
    return Row(index=index, cells=cells, note=note)


def _rows_at_run(tab, items, originals: dict, round: _Round) -> list:
    rows = []
    for index, item in enumerate(items or []):
        cells = {}
        for name in tab.fields:
            path = f"{tab.group}[{index}].{name}"
            # the persons block's money column takes the plain-cell STATE logic — an
            # amount a person typed there is CURRENT, never the grid's pale-blue NOT-READ (a
            # figure a document failed to yield; nothing on Household comes from a document).
            # The WRITE is still a money cell, by the `_cents` rule.
            cells[name] = _cell_at_run(path, item.get(name), originals.get(path),
                                       layout.is_money(name) and tab is not layout.PERSONS,
                                       round)
        rows.append(Row(index=index, cells=cells))

    # A GAP MAY NAME A ROW THAT DOES NOT EXIST YET. `persons[1].role` is a legitimate gap for an
    # `mfj` return with one person written, so the write-back CREATES the row — at the next free
    # index, and only there. An index beyond it is refused by name rather than filled: filling it
    # would leave the entries between them empty, and an empty entry is an entity the return
    # computes as absent. Same rule `loop._set_fact` already enforces, said on this side too.
    named = {}
    for path in round.gaps:
        parts = layout.split_path(path)
        if parts and parts[0] == tab.group:
            named.setdefault(parts[1], []).append(path)
    for index in sorted(named):
        if index < len(rows):
            continue
        if index > len(rows):
            round.extra.append(layout.BEYOND_NEXT_SLOT.format(
                where=layout.describe_row(tab.group, index), tab=tab.name, count=len(rows)))
            round.used.update(named[index])     # said in the refusal; not said again as a gap
            round.beyond.update(named[index])
            continue
        rows.append(_gap_row(tab, index, round, layout.GAP_ROW_CREATED))
    return rows


# An assumption naming this path is ANSWERABLE: `persons[i].birth_month` is a real question, and
# answering it replaces the assumption — the next run's `assumptions[]` no longer carries it and the
# row stops being highlighted. Everything else in `assumptions[]` is STATED ONLY: written as text on
# Household so the person reads it, with no cell to answer it in (spec section 6).
_ASSUMED_ANSWERABLE = re.compile(r"\bpersons\[(\d+)\]\.birth_month\b")


def model_from_read(read, *, response=None, invalid=None, stopped_because="", stated_at="",
                    extra_refusals=(), crossed=None) -> Model:
    """The run-side model: what the sheet said, plus what this round did to it.

    `crossed` says whether the payload reached the service. A response is proof that it did, so
    the default is `response is not None`; a round that ended in a refusal the service raised has
    no response and did cross, and that caller says `crossed=True`. A round with no response
    writes nothing as stated, and carries the assumptions the sheet already held: the last thing
    the service said still stands until the service says something else."""
    if crossed is None:
        crossed = response is not None
    round = _Round(invalid=dict(invalid or {}),
                   gaps={gap["fact"]: gap for gap in ((response or {}).get("gaps") or [])},
                   refused=dict(read.refused), stated_at=stated_at,
                   crossed=crossed, extra=list(extra_refusals))
    assumptions = (tuple(read.assumptions) if response is None
                   else tuple(response.get("assumptions") or ()))

    # The answerable assumption becomes a real question in the cell it is about: empty, GAP-yellow,
    # carrying the dropdown that column always carries, with the assumption's OWN words in the note.
    # STRUCTURED when a response is in hand: the service serves `assumption_details` with
    # the fact beside the statement, so the cell is keyed on the field, never parsed out of prose.
    # The regex remains ONLY for the carried-sheet path — a round with no response re-derives from
    # the assumptions block the reader carried, and a sheet stores sentences, not structure.
    details = (response or {}).get("assumption_details")
    if details is not None:
        for entry in details:
            fact = entry.get("fact")
            if fact and _ASSUMED_ANSWERABLE.fullmatch(fact) and fact not in round.gaps:
                round.gaps[fact] = {"fact": fact, "why": entry.get("statement") or ""}
                round.assumed.add(fact)
    else:
        for text in assumptions:
            found = _ASSUMED_ANSWERABLE.search(text)
            if found and found.group(0) not in round.gaps:
                round.gaps[found.group(0)] = {"fact": found.group(0), "why": text}
                round.assumed.add(found.group(0))

    status_path = layout.FILING_STATUS_ROW
    filing = _cell_at_run(status_path, read.facts.get(status_path), None, False, round)
    # a root money row takes the plain-cell STATE logic (a typed amount is CURRENT, never
    # the grid's pale-blue NOT-READ, which marks a figure a document failed to yield); only the
    # WRITE is a money cell, so dollars are shown and typed.
    root = {path: _cell_at_run(path, read.facts.get(path), None, False, round)
            for path in layout.ROOT_QUESTION_ROWS}

    persons = _rows_at_run(layout.PERSONS, read.facts.get("persons"), read.originals, round)
    if not persons:
        # No person at all — the ordinary first run after a collect from a W-2 alone. The service
        # reports ONE gap (`persons`), not one per field, so the workbook offers one empty row
        # rather than leaving a person nowhere to be entered: the same row `model_from_case`
        # writes, with the service's words said once for the row.
        gap = round.gaps.get("persons")
        if gap is not None:
            round.used.add("persons")
        persons = [_gap_row(layout.PERSONS, 0, round, (gap or {}).get("why") or "")]

    groups = {}
    for tab in layout.TABS:
        rows = _rows_at_run(tab, read.facts.get(tab.group), read.originals, round)
        if rows:
            groups[tab.group] = rows

    if not crossed:
        # a round that said NOTHING must not erase what the last crossing round said. The
        # reader carried each row's note-column TEXT; a row this round has no note for gets its
        # previous text back verbatim (it is already label-prefixed and joined). A row this round
        # DID note — a refusal, a repainted gap — speaks this round's words alone, and a crossing
        # round never enters this block: the carry is for silence, not a cache.
        carried = getattr(read, "notes", {}) or {}

        def _carry(row, key):
            if not row.note and not any(cell.note for cell in row.cells.values()):
                row.note = carried.get(key, "")

        for person_row in persons:
            _carry(person_row, ("persons", person_row.index))
        for group, rows in groups.items():
            for row in rows:
                _carry(row, (group, row.index))
        if not filing.note and (layout.FILING_STATUS_ROW, 0) in carried:
            filing = replace(filing, note=carried[(layout.FILING_STATUS_ROW, 0)])
        for path, cell in root.items():
            if not cell.note and (path, 0) in carried:
                root[path] = replace(cell, note=carried[(path, 0)])

    # the no-cell block holds only what NO cell can hold. A held path the round did not
    # paint — its cell already carries a value the service still calls missing — is located in
    # the open block instead, pointing at that cell, rather than said here as if it had nowhere
    # to go.
    unplaced = tuple(gap for path, gap in round.gaps.items()
                     if path not in round.used and path not in round.assumed
                     and not _placeable(path))
    # everything this round left open — placed or not — minus what is an assumption and
    # what was refused by name. `_result_sheet` says where each one is; one it cannot place is
    # in the no-cell block already.
    open_gaps = tuple(gap for path, gap in round.gaps.items()
                      if path not in round.assumed and path not in round.beyond)
    tax_year = read.tax_year
    if tax_year is None:
        tax_year = read.refused.get(layout.TAX_YEAR_ROW)
    return Model(tax_year=tax_year, filing_status=filing, root_answers=root, persons=persons,
                 groups=groups,
                 assumptions=assumptions, result=response, stopped_because=stopped_because,
                 extra_refusals=tuple(round.extra), unplaced_gaps=unplaced,
                 open_gaps=open_gaps)


def rewrite_workbook(read, *, response=None, invalid=None, stopped_because="", stated_at="",
                     extra_refusals=(), crossed=None) -> bytes:
    """`run`'s write-back. The ORIGINAL columns come straight off `read.originals`, unchanged."""
    return render(model_from_read(read, response=response, invalid=invalid,
                                  stopped_because=stopped_because, stated_at=stated_at,
                                  extra_refusals=extra_refusals, crossed=crossed))
