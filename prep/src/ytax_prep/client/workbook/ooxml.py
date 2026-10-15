# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""OOXML primitives — XML strings, and one deterministic package. No tax knowledge, no layout.

Written with the stdlib and nothing else. The deployed container ships `src/` with no spreadsheet
library, and this workbook is produced AND read back by this package alone.

TWO GUARDS LIVE HERE AS ASSERTIONS, because both failures are invisible to every test that asserts
about facts and visible only to the person who opens the file:

  (a) **Overlapping `<col>` ranges are REPAIRED SILENTLY** and the column widths vanish. Silent, so
      only a byte-level check finds it.
  (b) **Overlapping merge ranges make the file refuse to open outright.**

The third guard (c) is the READER's — a saved workbook comes back with its column runs compacted
and its `hidden` flags gone — so nothing written here may be load-bearing for reading it back.

Determinism is a guard too: fixed zip entry timestamps and fixed document properties, so rebuilding
an unchanged case reproduces the bytes and a churned artifact in a diff means real content moved.

And one rule for every piece of text: **refuse rather than guess.** A character XML cannot carry, a
reference off the grid, a number that is not a number, a sheet name the file cannot hold — each
raises `WorkbookXMLError` naming what and where. Nothing is stripped, clamped or coerced, because a
stray control character in extracted text is data the person should see refused, not lose.
"""
from __future__ import annotations

import io
import math
import re
import zipfile
from collections import namedtuple
from xml.etree import ElementTree
from xml.sax.saxutils import escape

# Fixed, so two builds of the same case are byte-identical. The value is the zip epoch itself.
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FIXED_CREATED = "1980-01-01T00:00:00Z"

# The grid's edges. A reference past either is one Excel repairs away, silently.
MAX_ROW = 1_048_576
MAX_COL = 16_384

# `kind` is "s" (value is an int index into the shared strings) or "n" (value is the number's
# STORED STRING — never a float, because a float is what the money rules exist to keep out).
# `value=None` writes an empty but STYLED cell, which is what a GAP is.
# `kind` is also "b" (value is "0" or "1") or "f" (value is the cached result's stored string, or
# None; `formula` is the formula text). Both exist for ONE reason: a cell the reader refused is
# carried back as exactly what it was — so the next read refuses it again by the same name, rather
# than a refused boolean coming back as the string "1" and being read as a dollar.
Cell = namedtuple("Cell", "row col kind value style formula", defaults=(None,))

# A `<f>` element as it was found: its text and its attributes, in document order. Excel writes a
# filled-down formula as a MASTER `<f t="shared" ref="D3:D4" si="0">1+1</f>` and CHILDREN
# `<f t="shared" si="0"/>` with no text at all — so a formula carried back by its text alone had
# nothing to put back for a child. `Cell.formula` takes one of these, or a bare string for a formula
# with no attributes.
Formula = namedtuple("Formula", "text attributes")

# A cell as the reader found it, kept so the writer can put it back unchanged. `kind` is "s"
# (text, however it was stored), "b" (boolean; `text` is "0"/"1"), "f" (formula; `formula` is the
# formula text and `text` the cached result) or "n" (a number-typed cell whose text the parser
# refused — `12.345`, `inf`; it is carried back as TEXT, so no numeric `<v>` can be accepted on the
# way round). Declared here, beside the cell vocabulary, because the reader records it and the
# writer re-emits it and neither imports the other.
RefusedCell = namedtuple("RefusedCell", "kind text formula")
Col = namedtuple("Col", "first last width hidden")


class WorkbookXMLError(ValueError):
    """The XML was not produced. Raised instead of writing a file that gets silently repaired."""


# Characters XML 1.0 cannot carry in ANY form — not as text, not in an attribute, not escaped.
# `escape()` rewrites `& < >` only, so one of these would ship as a malformed part and the file would
# refuse to open. Lone surrogates are here too: they cannot be encoded as UTF-8 at all.
_XML_ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿\ud800-\udfff]")

# Exactly what a cell reference is: one to three capital letters, then a row with no leading zero.
_REF = re.compile(r"([A-Z]{1,3})([1-9][0-9]{0,6})")

# Exactly what a numeric cell stores: `dollars()` or `str(int)` — a decimal number, nothing else.
_NUMBER = re.compile(r"-?[0-9]+(\.[0-9]+)?")

# An attribute name, as XML spells one.
_XML_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]*")

_SHEET_NAME_FORBIDDEN = frozenset("[]:*?/\\")
_SHEET_NAME_MAX = 31


def _checked(text, where: str) -> str:
    """The ONE check every text path goes through. Returns the text unchanged, or raises naming the
    code point and where it was headed — a refusal, never a strip."""
    if not isinstance(text, str):
        raise WorkbookXMLError(f"{where}: {text!r} is not a string")
    hit = _XML_ILLEGAL.search(text)
    if hit is not None:
        raise WorkbookXMLError(
            f"{where}: U+{ord(hit.group()):04X} at offset {hit.start()} is not a character XML "
            f"can carry. Refused rather than stripped — a control character in extracted text is "
            f"data to see refused, not to lose.")
    return text


def _int(value, what: str) -> int:
    """An int and not a bool — `isinstance(True, int)` is True in Python, which is why the boolean
    is named here rather than left to the int check."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkbookXMLError(f"{what} {value!r} is not an integer")
    return value


def col_letter(index: int) -> str:
    _int(index, "column index")
    if index < 1:
        raise WorkbookXMLError(f"column index {index} is not 1-based")
    if index > MAX_COL:
        raise WorkbookXMLError(f"column index {index} is past the grid's last column, {MAX_COL}")
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def ref(row: int, col: int) -> str:
    _int(row, "row index")
    if row < 1:
        raise WorkbookXMLError(f"row index {row} is not 1-based")
    if row > MAX_ROW:
        raise WorkbookXMLError(f"row index {row} is past the grid's last row, {MAX_ROW}")
    return f"{col_letter(col)}{row}"


def parse_ref(text: str):
    """"C4" -> (4, 3). The reader's geometry and the tests both spell it here, once.

    ASCII capitals and ASCII digits only: `str.isalpha()` would take `Ä`, `str.isdigit()` would
    take `١`, and `int()` would turn the latter into a row number without a word."""
    match = _REF.fullmatch(text) if isinstance(text, str) else None
    if match is None:
        raise WorkbookXMLError(
            f"{text!r} is not a cell reference — one to three capital letters, then a row number "
            f"with no leading zero")
    letters, digits = match.groups()
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch) - ord("A") + 1)
    row = int(digits)
    if col > MAX_COL or row > MAX_ROW:
        raise WorkbookXMLError(
            f"{text!r} is past the grid's edge (column {col} of {MAX_COL}, row {row} of {MAX_ROW})")
    return row, col


def _box(a1: str, where: str):
    """`"A1:B3"` -> `(top, left, bottom, right)`, forward on BOTH axes.

    One cell written as a range (`B3:B3`) is a box here: it is legal OOXML in a dropdown's `sqref`.
    That a MERGE needs two cells or more is the merge's rule, and `merges_xml` says it."""
    start, _sep, end = a1.partition(":")
    if not end:
        raise WorkbookXMLError(
            f"{a1!r} is not a {where} — a range is two references joined by a colon")
    top, left = parse_ref(start)
    bottom, right = parse_ref(end)
    # Per axis, not as a tuple: `C1:A3` runs forward by row and backward by column, and a tuple
    # comparison let it through as a degenerate box that overlapped nothing.
    if bottom < top or right < left:
        raise WorkbookXMLError(f"{where} {a1!r} runs backwards")
    return top, left, bottom, right


def _sqref(sqref) -> str:
    """A space-separated list of references and ranges, each one on the grid."""
    if not isinstance(sqref, str) or not sqref:
        raise WorkbookXMLError(f"{sqref!r} is not a cell range list")
    for token in sqref.split(" "):
        if ":" in token:
            _box(token, "range")
        else:
            parse_ref(token)
    return sqref


def _attr(text, where: str = "an attribute") -> str:
    text = _checked("" if text is None else str(text), where)
    # An attribute's tab, LF and CR are normalised to spaces by every parser; the character
    # references are not.
    return (escape(text, {'"': "&quot;"})
            .replace("\t", "&#9;").replace("\n", "&#10;").replace("\r", "&#13;"))


def _text(text: str, where: str) -> str:
    # Element text keeps its tab and LF; only a literal CR is normalised away, so it alone is
    # written as a character reference.
    return escape(_checked(text, where)).replace("\r", "&#13;")


class StringTable:
    """First-seen order, deduplicated — deterministic without sorting, which would scramble the
    reading order a person sees in the file."""

    def __init__(self):
        self.strings = []
        self._index = {}

    def add(self, text) -> int:
        text = _checked("" if text is None else str(text), "a shared string")
        if text not in self._index:
            self._index[text] = len(self.strings)
            self.strings.append(text)
        return self._index[text]


def cols_xml(cols) -> str:
    """GUARD (a). Ranges must be forward, 1-based, on the grid, sorted and DISJOINT."""
    ordered = list(cols)
    previous = 0
    for c in ordered:
        _int(c.first, "<col> min")
        _int(c.last, "<col> max")
        if c.first < 1 or c.last < c.first:
            raise WorkbookXMLError(f"<col> range {c.first}-{c.last} is not a forward 1-based range")
        if c.last > MAX_COL:
            raise WorkbookXMLError(
                f"<col> range {c.first}-{c.last} runs past the grid's last column, {MAX_COL}")
        if c.first <= previous:
            raise WorkbookXMLError(
                f"<col> range {c.first}-{c.last} overlaps the range ending at column {previous}. "
                f"Overlapping ranges are repaired silently and the widths are lost, which is why "
                f"this is an assertion and not a comment.")
        # A number, never a string: the width is written into an attribute, and a string would be
        # written verbatim. 255 is the widest column a sheet holds.
        if (isinstance(c.width, bool) or not isinstance(c.width, (int, float))
                or not 0 < c.width <= 255):
            raise WorkbookXMLError(f"<col> width {c.width!r} is not a number between 0 and 255")
        previous = c.last
    if not ordered:
        return ""
    body = "".join(
        f'<col min="{c.first}" max="{c.last}" width="{c.width}" customWidth="1"'
        + (' hidden="1"' if c.hidden else "") + "/>"
        for c in ordered)
    return f"<cols>{body}</cols>"


def merges_xml(ranges) -> str:
    """GUARD (b). Overlapping merges make the file refuse to open, so this stops here instead."""
    boxes = []
    for a1 in ranges:
        top, left, bottom, right = _box(a1, "merge")
        if (top, left) == (bottom, right):
            raise WorkbookXMLError(f"{a1!r} is not a merge — a merge spans two cells or more")
        for other, (o_top, o_left, o_bottom, o_right) in boxes:
            if top <= o_bottom and o_top <= bottom and left <= o_right and o_left <= right:
                raise WorkbookXMLError(
                    f"merge {a1!r} overlaps {other!r}. A workbook whose merges overlap refuses to "
                    f"open, so this stops at the writer rather than at a person's screen.")
        boxes.append((a1, (top, left, bottom, right)))
    if not boxes:
        return ""
    body = "".join(f'<mergeCell ref="{_attr(a1, "a merge ref")}"/>' for a1, _box_ in boxes)
    return f'<mergeCells count="{len(boxes)}">{body}</mergeCells>'


def data_validation_xml(validations) -> str:
    """`[(sqref, [code, ...])]` -> `<dataValidations>`, an INLINE list per range.

    `showErrorMessage="0"` deliberately: the dropdown OFFERS the schema's codes, it does not police
    them. A value typed past it is refused BY NAME at `run` and painted red, which says what is
    wrong; a modal that says "invalid" says nothing.

    An inline list caps at 255 characters of formula. Every list this workbook offers is far
    shorter, and a longer one RAISES rather than being truncated into a dropdown quietly missing
    its last codes. A code carrying a comma would arrive as two codes and one carrying a double
    quote would end the list early, so both are refused here as well as at the layout."""
    if not validations:
        return ""
    parts = []
    for sqref, codes in validations:
        _sqref(sqref)
        where = f"the dropdown list for {sqref}"
        if not isinstance(codes, (list, tuple)) or not codes:
            raise WorkbookXMLError(f"{where} offers no codes — a dropdown of nothing is a dropdown "
                                   f"offering the empty string")
        for code in codes:
            _checked(code, where)
            if not code or '"' in code or "," in code:
                raise WorkbookXMLError(
                    f"{where}: code {code!r} cannot sit in an inline list — a comma splits it, a "
                    f"double quote ends it, and an empty code offers nothing")
        formula = ",".join(codes)
        if len(formula) + 2 > 255:
            raise WorkbookXMLError(
                f"{where} is {len(formula) + 2} characters, past the 255 an inline list holds — "
                f"it would be truncated and offer fewer codes than the schema accepts")
        parts.append(
            f'<dataValidation type="list" allowBlank="1" showInputMessage="1" '
            f'showErrorMessage="0" sqref="{_attr(sqref, "a dropdown sqref")}">'
            f'<formula1>"{_text(formula, where)}"</formula1></dataValidation>')
    return f'<dataValidations count="{len(parts)}">{"".join(parts)}</dataValidations>'


def _cell_xml(cell: Cell) -> str:
    at = ref(cell.row, cell.col)
    if _int(cell.style, f"style id of cell {at}") < 0:
        raise WorkbookXMLError(f"style id of cell {at} is {cell.style}, below 0")
    head = f'<c r="{at}" s="{cell.style}"'
    if cell.kind == "f":
        formula = Formula(cell.formula, ()) if isinstance(cell.formula, str) else cell.formula
        if not isinstance(formula, Formula):
            raise WorkbookXMLError(f"the formula cell {at} carries no formula")
        attributes = []
        for name, value in tuple(formula.attributes or ()):
            if not isinstance(name, str) or _XML_NAME.fullmatch(name) is None:
                raise WorkbookXMLError(f"the formula of cell {at} carries an attribute named "
                                       f"{name!r}, which is not an XML name")
            attributes.append(
                f' {name}="{_attr(value, f"the {name} attribute of the formula of cell {at}")}"')
        text = formula.text or ""
        named = dict(formula.attributes or ())
        # An attribute-only formula is valid OOXML for exactly one shape: a shared formula's child,
        # which names its master by `si`. A bare empty `<f/>` is still refused.
        if not text and not (named.get("t") == "shared" and "si" in named):
            raise WorkbookXMLError(f"the formula cell {at} carries no formula text")
        element = (f"<f{''.join(attributes)}>{_text(text, f'the formula of cell {at}')}</f>"
                   if text else f"<f{''.join(attributes)}/>")
        cached = cell.value
        if cached in (None, ""):
            return head + f">{element}</c>"
        cached = _checked(cached, f"the cached value of cell {at}")
        if _NUMBER.fullmatch(cached) is not None:
            return head + f">{element}<v>{cached}</v></c>"
        return head + f' t="str">{element}<v>{_text(cached, f"the cached value of cell {at}")}</v></c>'
    if cell.formula is not None:
        raise WorkbookXMLError(f"cell {at} carries a formula but is of kind {cell.kind!r}, not 'f'")
    if cell.value is None:
        return head + "/>"
    if cell.kind == "b":
        value = _checked(cell.value, f"the boolean cell {at}")
        if value not in ("0", "1"):
            raise WorkbookXMLError(f"the boolean cell {at} holds {value!r}; a boolean stores 0 or 1")
        return head + f' t="b"><v>{value}</v></c>'
    if cell.kind == "s":
        if _int(cell.value, f"shared string index of cell {at}") < 0:
            raise WorkbookXMLError(f"shared string index of cell {at} is {cell.value}, below 0")
        return head + f' t="s"><v>{cell.value}</v></c>'
    if cell.kind == "n":
        value = _checked(cell.value, f"the numeric cell {at}")
        if _NUMBER.fullmatch(value) is None:
            raise WorkbookXMLError(
                f"the numeric cell {at} holds {value!r}, which is not a decimal number string. "
                f"A numeric cell stores `dollars()` or `str(int)` and nothing else — anything "
                f"else is a cell Excel repairs.")
        return head + f"><v>{value}</v></c>"
    raise WorkbookXMLError(f"unknown cell kind {cell.kind!r} — this writer emits 's', 'n', 'b' "
                           f"and 'f' only")


# every style wraps, but a wrapped cell SHOWS one line unless its `<row>` says a height —
# so a label longer than its column was truncated on every sheet. The height is estimated from
# the text and the widths this writer wrote: one line per `width` characters (a column's width is
# in characters of the default font's digits, which text of ordinary words fits within), fifteen
# points a line, capped at the tallest row a sheet holds. A column with no `<col>` written is the
# default width. Text only: a number never wraps.
DEFAULT_COL_WIDTH = 8.43
DEFAULT_ROW_HEIGHT = 15
MAX_ROW_HEIGHT = 409.5


def _row_heights(cells, cols, merges, strings) -> dict:
    """`{row: height}` for every row whose text needs more than one line; nothing for the rest,
    so a row of short cells is written exactly as before."""
    width_of = {}
    for c in cols:
        for col in range(c.first, c.last + 1):
            width_of[col] = c.width
    spans = {}
    for rng in merges:
        start, _colon, end = rng.partition(":")
        (r1, c1), (r2, c2) = parse_ref(start), parse_ref(end)
        if r1 == r2:                   # a title across one row: the merged cell has the summed width
            spans[(r1, c1)] = sum(width_of.get(col, DEFAULT_COL_WIDTH) for col in range(c1, c2 + 1))
    lines_of = {}
    for cell in cells:
        if cell.kind != "s":
            continue
        text = strings[int(cell.value)]
        width = spans.get((cell.row, cell.col)) or width_of.get(cell.col, DEFAULT_COL_WIDTH)
        lines = sum(max(1, math.ceil(len(part) / width)) for part in text.split("\n"))
        if lines > 1:
            lines_of[cell.row] = max(lines_of.get(cell.row, 0), lines)
    return {row: min(lines * DEFAULT_ROW_HEIGHT, MAX_ROW_HEIGHT) for row, lines in lines_of.items()}


def sheet_xml(cells, cols=(), merges=(), validations=(), strings=None) -> str:
    """One worksheet part. Element order is the schema's: cols, sheetData, sheetProtection,
    mergeCells, dataValidations.

    `strings` is the shared-string table the cells index into; given, every row whose text runs
    past its column gets the height its lines need. Without it no height is estimated.

    `<sheetProtection>` is a GUIDE RAIL, not security (33a's caveat): locked cells steer an honest
    editor, they do not encrypt anything. This workbook carries no identity, so nothing in it needs
    protecting — the sentence stands anyway so nobody mistakes the one for the other."""
    rows = {}
    for cell in cells:
        rows.setdefault(cell.row, []).append(cell)
    heights = _row_heights(cells, cols, merges, strings) if strings is not None else {}
    body = []
    for row in sorted(rows):
        ordered = sorted(rows[row], key=lambda c: c.col)
        seen = set()
        for c in ordered:
            if c.col in seen:
                raise WorkbookXMLError(f"two cells written at {ref(c.row, c.col)}")
            seen.add(c.col)
        tall = f' ht="{heights[row]:g}" customHeight="1"' if row in heights else ""
        body.append(f'<row r="{row}"{tall}>' + "".join(_cell_xml(c) for c in ordered) + "</row>")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            + cols_xml(cols)
            + "<sheetData>" + "".join(body) + "</sheetData>"
            + '<sheetProtection sheet="1" objects="1" scenarios="1" selectLockedCells="0" '
              'selectUnlockedCells="0"/>'
            + merges_xml(merges) + data_validation_xml(validations)
            + "</worksheet>")


def sst_xml(strings) -> str:
    items = "".join(f'<si><t xml:space="preserve">{_text(s, f"shared string {i}")}</t></si>'
                    for i, s in enumerate(strings))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            f'count="{len(strings)}" uniqueCount="{len(strings)}">{items}</sst>')


def styles_xml(entries) -> str:
    """`[(fill_argb_or_None, money, bold, locked)]` -> the styles part, one `cellXfs` per entry IN
    ORDER, so an entry's position IS its style id.

    This file names no states. `styles.py` owns the vocabulary and hands the sequence down, which is
    what keeps the two acyclic. `numFmtId="2"` is the built-in `0.00`: money is displayed in dollars
    to two places, always."""
    fills = ['<fill><patternFill patternType="none"/></fill>',
             '<fill><patternFill patternType="gray125"/></fill>']
    fill_id = {}
    for fill, _money, _bold, _locked in entries:
        if fill and fill not in fill_id:
            fill_id[fill] = len(fills)
            fills.append('<fill><patternFill patternType="solid">'
                         f'<fgColor rgb="{_attr(fill, "a fill colour")}"/><bgColor indexed="64"/>'
                         "</patternFill></fill>")
    xfs = []
    for fill, money, bold, locked in entries:
        xfs.append(
            f'<xf numFmtId="{2 if money else 0}" fontId="{1 if bold else 0}" '
            f'fillId="{fill_id.get(fill, 0)}" borderId="0" xfId="0" applyNumberFormat="1" '
            f'applyFont="1" applyFill="1" applyAlignment="1" applyProtection="1">'
            f'<alignment vertical="top" wrapText="1"/>'
            f'<protection locked="{1 if locked else 0}"/></xf>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="2"><font><sz val="11"/></font><font><b/><sz val="11"/></font></fonts>'
            f'<fills count="{len(fills)}">' + "".join(fills) + "</fills>"
            '<borders count="1"><border/></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
            "</cellStyleXfs>"
            f'<cellXfs count="{len(xfs)}">' + "".join(xfs) + "</cellXfs>"
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            "</styleSheet>")


def workbook_xml(sheet_names) -> str:
    """Sheets in the order given; `rId(n)` matches `xl/worksheets/sheet(n).xml`, which is the one
    convention `package` below relies on.

    A sheet name the workbook cannot hold — empty, past 31 characters, carrying one of `[]:*?/\\`,
    starting or ending with an apostrophe, or repeating another name in any case — is refused."""
    seen = set()
    sheets = []
    for i, name in enumerate(sheet_names, start=1):
        where = f"sheet name {i}"
        _checked(name, where)
        if not name or len(name) > _SHEET_NAME_MAX:
            raise WorkbookXMLError(f"{where} {name!r} is empty or past {_SHEET_NAME_MAX} characters")
        if _SHEET_NAME_FORBIDDEN & set(name):
            raise WorkbookXMLError(f"{where} {name!r} carries one of the characters a sheet name "
                                   f"cannot: [ ] : * ? / \\")
        if name[0] == "'" or name[-1] == "'":
            raise WorkbookXMLError(f"{where} {name!r} starts or ends with an apostrophe")
        if name.casefold() in seen:
            raise WorkbookXMLError(f"{where} {name!r} repeats another sheet's name (names are "
                                   f"compared without case)")
        seen.add(name.casefold())
        sheets.append(f'<sheet name="{_attr(name, where)}" sheetId="{i}" r:id="rId{i}"/>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets>{"".join(sheets)}</sheets></workbook>')


_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_SML = "application/vnd.openxmlformats-officedocument.spreadsheetml"

WORKSHEET_TYPE = f"{_SML}.worksheet+xml"
PART_TYPES = {
    "xl/workbook.xml": f"{_SML}.sheet.main+xml",
    "xl/styles.xml": f"{_SML}.styles+xml",
    "xl/sharedStrings.xml": f"{_SML}.sharedStrings+xml",
    "docProps/core.xml": "application/vnd.openxmlformats-package.core-properties+xml",
    "docProps/app.xml":
        "application/vnd.openxmlformats-officedocument.extended-properties+xml",
}
REQUIRED_PARTS = ("xl/workbook.xml", "xl/styles.xml")

_SHEET_PART = re.compile(r"xl/worksheets/sheet([1-9][0-9]*)\.xml")

CORE_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<cp:coreProperties '
    'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:dcterms="http://purl.org/dc/terms/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    "<dc:title>yTax collection and review workbook</dc:title>"
    "<dc:creator>ytax-prep</dc:creator>"
    "<cp:lastModifiedBy>ytax-prep</cp:lastModifiedBy>"
    f'<dcterms:created xsi:type="dcterms:W3CDTF">{FIXED_CREATED}</dcterms:created>'
    f'<dcterms:modified xsi:type="dcterms:W3CDTF">{FIXED_CREATED}</dcterms:modified>'
    "</cp:coreProperties>")

APP_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
    'extended-properties">'
    "<Application>ytax-prep</Application></Properties>")


def _part_bytes(name: str, text) -> bytes:
    """UTF-8, and WELL-FORMED — the package's own backstop behind every text path's check. A lone
    surrogate would otherwise die inside `zipfile` as an untyped `UnicodeEncodeError`."""
    if not isinstance(text, str):
        raise WorkbookXMLError(f"part {name} is {type(text).__name__}, not a string")
    try:
        data = text.encode("utf-8")
    except UnicodeEncodeError as err:
        raise WorkbookXMLError(f"part {name} cannot be encoded: {err.reason} at offset "
                               f"{err.start}") from None
    try:
        ElementTree.fromstring(data)
    except ElementTree.ParseError as err:
        raise WorkbookXMLError(f"part {name} is not well-formed XML: {err}") from None
    return data


def package(parts: dict) -> bytes:
    """Assemble the `.xlsx`. `parts` carries `xl/workbook.xml`, `xl/styles.xml`,
    `xl/sharedStrings.xml` and `xl/worksheets/sheetN.xml`; the doc properties, the two rels parts
    and `[Content_Types].xml` are generated here so they cannot disagree with what is inside.

    A part with no declared content type RAISES: a part the content types do not name is a part
    nothing will read, and a silently unread part is the whole failure class this repo refuses. So
    does a missing workbook or styles part, a sheet part not numbered `1..n`, and a part that is
    not well-formed XML."""
    entries = dict(parts)
    entries["docProps/core.xml"] = CORE_XML
    entries["docProps/app.xml"] = APP_XML

    for name in REQUIRED_PARTS:
        if name not in entries:
            raise WorkbookXMLError(f"no {name} part — the relationships would point at nothing")

    prefix = "xl/worksheets/sheet"
    numbered = {}
    for name in entries:
        if name.startswith(prefix):
            match = _SHEET_PART.fullmatch(name)
            if match is None:
                raise WorkbookXMLError(f"worksheet part {name!r} is not named sheetN.xml")
            numbered[int(match.group(1))] = name
    if sorted(numbered) != list(range(1, len(numbered) + 1)):
        raise WorkbookXMLError(
            f"worksheet parts are numbered {sorted(numbered)}, not 1..{len(numbered)} — "
            f"`rId(n)` is `sheet(n).xml` and a gap would point a sheet at the wrong part")
    sheets = [numbered[n] for n in sorted(numbered)]

    overrides = []
    for name in entries:
        if name.startswith(prefix):
            content_type = WORKSHEET_TYPE
        else:
            content_type = PART_TYPES.get(name)
            if content_type is None:
                raise WorkbookXMLError(
                    f"no declared content type for part {name!r}; declare it in PART_TYPES rather "
                    f"than shipping a part nothing will read")
        overrides.append(f'<Override PartName="/{name}" ContentType="{content_type}"/>')

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
        'relationships+xml"/>' + "".join(sorted(overrides)) + "</Types>")

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{_PKG_REL}">'
        f'<Relationship Id="rId1" Type="{_REL}/officeDocument" Target="xl/workbook.xml"/>'
        f'<Relationship Id="rId2" Type="{_PKG_REL}/metadata/core-properties" '
        'Target="docProps/core.xml"/>'
        f'<Relationship Id="rId3" Type="{_REL}/extended-properties" Target="docProps/app.xml"/>'
        "</Relationships>")

    rels = [f'<Relationship Id="rId{i}" Type="{_REL}/worksheet" Target="{name[len("xl/"):]}"/>'
            for i, name in enumerate(sheets, start=1)]
    count = len(sheets)
    rels.append(f'<Relationship Id="rId{count + 1}" Type="{_REL}/styles" Target="styles.xml"/>')
    if "xl/sharedStrings.xml" in entries:
        rels.append(f'<Relationship Id="rId{count + 2}" Type="{_REL}/sharedStrings" '
                    'Target="sharedStrings.xml"/>')
    workbook_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     f'<Relationships xmlns="{_PKG_REL}">' + "".join(rels) + "</Relationships>")

    ordered = [("[Content_Types].xml", content_types),
               ("_rels/.rels", root_rels),
               ("xl/_rels/workbook.xml.rels", workbook_rels)]
    ordered += [(name, entries[name]) for name in sorted(entries)]

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, text in ordered:
            data = _part_bytes(name, text)
            info = zipfile.ZipInfo(name, date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 0            # fixed across platforms, or the bytes are not
            info.external_attr = 0o600 << 16
            zf.writestr(info, data)
    return buffer.getvalue()
