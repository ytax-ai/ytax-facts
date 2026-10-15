# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Parse a fillable IRS template: xref streams, object streams, the AcroForm field tree.

The pinned templates are modern PDFs — the cross-reference is a compressed STREAM (ISO 32000
§7.5.8), most objects live inside compressed OBJECT streams (§7.5.7), and every field name sits
inside one of those, so nothing useful is visible to a byte scan. This reader implements exactly
the subset those templates need and REFUSES BY NAME anything outside it (`PdfSurprise`): the
template bytes are pinned by `REGISTERS_SHA256`, so a parse surprise is a pin-bump event to look
at, never a runtime condition to guess through.

Naming: IRS templates carry their XFA-mirrored partial names literally (`/T (topmostSubform[0])`,
`/T (f1_14[0])`). A button field with several widget kids is addressed by build's register per
WIDGET — `c1_10[0]`, `c1_10[1]` — so a multi-widget terminal named `x[0]` fans out to `x[k]` per
kid, which is the convention the dictionary's field registers use and the enumeration test pins.

Stdlib only.
"""
from __future__ import annotations

import re
import zlib
from dataclasses import dataclass


class PdfSurprise(ValueError):
    """The template used a PDF feature outside the implemented subset — named, never guessed."""


class Ref:
    __slots__ = ("num", "gen")

    def __init__(self, num: int, gen: int):
        self.num, self.gen = num, gen

    def __repr__(self):
        return f"Ref({self.num},{self.gen})"

    def __eq__(self, other):
        return isinstance(other, Ref) and (self.num, self.gen) == (other.num, other.gen)

    def __hash__(self):
        return hash((self.num, self.gen))


_WS = b"\x00\t\n\x0c\r %"
_DELIM = b"()<>[]{}/%"


def _skip_ws(data: bytes, i: int) -> int:
    n = len(data)
    while i < n:
        c = data[i:i + 1]
        if c == b"%":
            j = data.find(b"\n", i)
            i = n if j < 0 else j + 1
        elif c in b"\x00\t\n\x0c\r ":
            i += 1
        else:
            break
    return i


def _parse_name(data: bytes, i: int):
    # after the '/'
    j = i
    n = len(data)
    while j < n and data[j:j + 1] not in _WS + _DELIM.replace(b"/", b"") and data[j:j + 1] != b"/":
        j += 1
    raw = data[i:j]
    # #xx escapes
    out = re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), raw)
    return "/" + out.decode("latin-1"), j


def _parse_literal_string(data: bytes, i: int):
    # after the '('
    out, depth, n = bytearray(), 1, len(data)
    while i < n:
        c = data[i]
        if c == 0x5C:  # backslash
            i += 1
            e = data[i:i + 1]
            mapped = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f",
                      b"(": b"(", b")": b")", b"\\": b"\\"}.get(e)
            if mapped is not None:
                out += mapped
                i += 1
            elif e.isdigit():
                k = 1
                while k < 3 and data[i + k:i + k + 1].isdigit():
                    k += 1
                out.append(int(data[i:i + k], 8) & 0xFF)
                i += k
            else:  # line continuation or unknown escape: keep literally
                i += 1
        elif c == 0x28:
            depth += 1
            out.append(c)
            i += 1
        elif c == 0x29:
            depth -= 1
            if depth == 0:
                return bytes(out), i + 1
            out.append(c)
            i += 1
        else:
            out.append(c)
            i += 1
    raise PdfSurprise("unterminated literal string")


_NUM_RE = re.compile(rb"[+-]?\d*\.?\d+")


def parse_object(data: bytes, i: int):
    """One PDF object at `i` -> (value, next index). Dicts are Python dicts keyed by /Name;
    strings are bytes; names are '/x' strings; refs are Ref."""
    i = _skip_ws(data, i)
    c = data[i:i + 1]
    if c == b"<":
        if data[i:i + 2] == b"<<":
            d = {}
            i += 2
            while True:
                i = _skip_ws(data, i)
                if data[i:i + 2] == b">>":
                    return d, i + 2
                if data[i:i + 1] != b"/":
                    raise PdfSurprise(f"dictionary key is not a name at byte {i}")
                key, i = _parse_name(data, i + 1)
                val, i = parse_object(data, i)
                d[key] = val
        # hex string
        j = data.index(b">", i)
        hx = re.sub(rb"[^0-9A-Fa-f]", b"", data[i + 1:j])
        if len(hx) % 2:
            hx += b"0"
        return bytes.fromhex(hx.decode()), j + 1
    if c == b"(":
        return _parse_literal_string(data, i + 1)
    if c == b"/":
        return _parse_name(data, i + 1)
    if c == b"[":
        arr = []
        i += 1
        while True:
            i = _skip_ws(data, i)
            if data[i:i + 1] == b"]":
                return arr, i + 1
            v, i = parse_object(data, i)
            arr.append(v)
    if data[i:i + 4] == b"true":
        return True, i + 4
    if data[i:i + 5] == b"false":
        return False, i + 5
    if data[i:i + 4] == b"null":
        return None, i + 4
    m = _NUM_RE.match(data, i)
    if m:
        # `N G R` indirect reference lookahead
        mref = re.match(rb"(\d+)[\x00\t\n\x0c\r ]+(\d+)[\x00\t\n\x0c\r ]+R(?![A-Za-z])", data[i:i + 32])
        if mref:
            return Ref(int(mref.group(1)), int(mref.group(2))), i + mref.end()
        tok = m.group()
        return (float(tok) if b"." in tok else int(tok)), m.end()
    raise PdfSurprise(f"unparseable object at byte {i}: {data[i:i+20]!r}")


def _png_unpredict(raw: bytes, columns: int) -> bytes:
    row_len = columns + 1
    if len(raw) % row_len:
        raise PdfSurprise("predictor data is not a whole number of rows")
    out = bytearray()
    prev = bytearray(columns)
    for r in range(0, len(raw), row_len):
        ft, row = raw[r], bytearray(raw[r + 1:r + row_len])
        for x in range(columns):
            a = row[x - 1] if x else 0
            b = prev[x]
            cc = prev[x - 1] if x else 0
            if ft == 0:
                pass
            elif ft == 1:
                row[x] = (row[x] + a) & 0xFF
            elif ft == 2:
                row[x] = (row[x] + b) & 0xFF
            elif ft == 3:
                row[x] = (row[x] + ((a + b) >> 1)) & 0xFF
            elif ft == 4:
                p = a + b - cc
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - cc)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else cc)
                row[x] = (row[x] + pred) & 0xFF
            else:
                raise PdfSurprise(f"PNG filter {ft} is not implemented")
        out += row
        prev = row
    return bytes(out)


@dataclass
class FormField:
    """One register-addressable field (a terminal field, or one widget of a multi-widget one)."""
    name: str
    field_type: str          # "Tx", "Btn", "Ch"
    field_ref: Ref           # the terminal field object (holds /V)
    widget_ref: Ref          # the widget to stamp /AS on (== field_ref when merged)
    on_state: str | None     # for Btn: the widget's non-Off appearance state name, no slash


class PdfTemplate:
    def __init__(self, data: bytes):
        self.data = data
        self.xref: dict[int, tuple] = {}   # num -> ("n", offset) | ("c", container, index)
        self.trailer: dict = {}
        self._cache: dict[int, object] = {}
        self._objstm_cache: dict[int, tuple] = {}
        self._load_xref_chain()
        self.fields: dict[str, FormField] = {}
        self._walk_acroform()

    # ---- xref / objects ----------------------------------------------------------------

    def _load_xref_chain(self):
        tail = self.data[-64:]
        m = re.search(rb"startxref[\x00\t\n\x0c\r ]+(\d+)", tail)
        if not m:
            raise PdfSurprise("no startxref")
        offset = int(m.group(1))
        seen = set()
        while offset and offset not in seen:
            seen.add(offset)
            offset = self._load_xref_stream(offset)

    def _load_xref_stream(self, offset: int) -> int:
        d, stream = self._parse_indirect_at(offset)
        if d.get("/Type") != "/XRef":
            raise PdfSurprise("classic xref tables are not in the pinned templates' subset")
        content = self._decode_stream(d, stream)
        w = d["/W"]
        if len(w) != 3:
            raise PdfSurprise("/W is not three columns")
        size = d["/Size"]
        index = d.get("/Index", [0, size])
        row = sum(w)
        pos = 0
        for k in range(0, len(index), 2):
            start, count = index[k], index[k + 1]
            for num in range(start, start + count):
                rec = content[pos:pos + row]
                pos += row
                f = []
                p = 0
                for width in w:
                    f.append(int.from_bytes(rec[p:p + width], "big") if width else 1)
                    p += width
                if num in self.xref:
                    continue  # first (newest) xref section wins
                if f[0] == 1:
                    self.xref[num] = ("n", f[1])
                elif f[0] == 2:
                    self.xref[num] = ("c", f[1], f[2])
                # type 0 (free): ignore
        for key in ("/Root", "/Size", "/Info", "/ID"):
            self.trailer.setdefault(key, d.get(key))
        return d.get("/Prev", 0)

    def _parse_indirect_at(self, offset: int):
        m = re.match(rb"(\d+)[\x00\t\n\x0c\r ]+(\d+)[\x00\t\n\x0c\r ]+obj", self.data[offset:offset + 32])
        if not m:
            raise PdfSurprise(f"no indirect object at byte {offset}")
        val, i = parse_object(self.data, offset + m.end())
        i = _skip_ws(self.data, i)
        stream = None
        if self.data[i:i + 6] == b"stream":
            i += 6
            if self.data[i:i + 2] == b"\r\n":
                i += 2
            elif self.data[i:i + 1] == b"\n":
                i += 1
            length = self.resolve(val.get("/Length"))
            if not isinstance(length, int):
                raise PdfSurprise("/Length did not resolve to an integer")
            stream = self.data[i:i + length]
        return val, stream

    def _decode_stream(self, d: dict, stream: bytes) -> bytes:
        filt = d.get("/Filter")
        if filt is None:
            content = stream
        elif filt == "/FlateDecode" or filt == ["/FlateDecode"]:
            content = zlib.decompress(stream)
        else:
            raise PdfSurprise(f"stream filter {filt} is not implemented")
        parms = d.get("/DecodeParms") or {}
        if isinstance(parms, list):
            parms = parms[0] or {}
        pred = parms.get("/Predictor", 1)
        if pred == 1:
            return content
        if pred >= 10:
            return _png_unpredict(content, parms["/Columns"])
        raise PdfSurprise(f"predictor {pred} is not implemented")

    def get_object(self, num: int):
        if num in self._cache:
            return self._cache[num]
        entry = self.xref.get(num)
        if entry is None:
            raise PdfSurprise(f"object {num} is not in the cross-reference")
        if entry[0] == "n":
            val, _stream = self._parse_indirect_at(entry[1])
        else:
            _kind, container, idx = entry
            val = self._objstm_object(container, idx)
        self._cache[num] = val
        return val

    def raw_stream(self, num: int) -> bytes | None:
        """The decoded stream of a type-1 object, for callers that need one (none today)."""
        entry = self.xref.get(num)
        if not entry or entry[0] != "n":
            return None
        d, stream = self._parse_indirect_at(entry[1])
        return self._decode_stream(d, stream) if stream is not None else None

    def _objstm_object(self, container: int, idx: int):
        if container not in self._objstm_cache:
            entry = self.xref.get(container)
            if not entry or entry[0] != "n":
                raise PdfSurprise(f"object stream {container} is not a direct object")
            d, stream = self._parse_indirect_at(entry[1])
            if d.get("/Type") != "/ObjStm":
                raise PdfSurprise(f"object {container} is not an object stream")
            content = self._decode_stream(d, stream)
            n, first = d["/N"], d["/First"]
            header = content[:first].split()
            pairs = [(int(header[2 * k]), int(header[2 * k + 1])) for k in range(n)]
            self._objstm_cache[container] = (content, first, pairs)
        content, first, pairs = self._objstm_cache[container]
        if idx >= len(pairs):
            raise PdfSurprise(f"object stream index {idx} out of range")
        _num, off = pairs[idx]
        val, _ = parse_object(content, first + off)
        return val

    def resolve(self, x):
        while isinstance(x, Ref):
            x = self.get_object(x.num)
        return x

    # ---- AcroForm ----------------------------------------------------------------------

    def _walk_acroform(self):
        root = self.resolve(self.trailer.get("/Root"))
        acro_ref = root.get("/AcroForm")
        self.acroform_ref = acro_ref if isinstance(acro_ref, Ref) else None
        acro = self.resolve(acro_ref)
        if not acro:
            raise PdfSurprise("template has no AcroForm")
        for ref in acro.get("/Fields", []):
            self._walk_field(ref, "", None)

    @staticmethod
    def _t(d) -> str | None:
        t = d.get("/T")
        if not isinstance(t, bytes):
            return None
        if t[:2] == b"\xfe\xff":  # ISO 32000 §7.9.2.2: UTF-16BE text string with BOM
            return t[2:].decode("utf-16-be")
        return t.decode("latin-1")  # PDFDocEncoding; ASCII-identical for these names

    def _walk_field(self, ref: Ref, prefix: str, inherited_ft):
        d = self.resolve(ref)
        t = self._t(d)
        name = f"{prefix}.{t}" if (prefix and t) else (t or prefix)
        ft = d.get("/FT", inherited_ft)
        kids = d.get("/Kids")
        if kids:
            kid_dicts = [self.resolve(k) for k in kids]
            if any(self._t(kd) is not None for kd in kid_dicts):
                for k in kids:
                    self._walk_field(k, name, ft)
                return
            self._terminal(name, ft, ref, list(zip(kids, kid_dicts)))
        else:
            self._terminal(name, ft, ref, [(ref, d)])

    def _terminal(self, name: str, ft, field_ref: Ref, widgets):
        if ft is None:
            raise PdfSurprise(f"terminal field {name!r} has no /FT")
        ftype = ft.lstrip("/")
        if len(widgets) == 1:
            names = [name]
        else:
            if not name.endswith("[0]"):
                raise PdfSurprise(f"multi-widget field {name!r} does not end in [0]")
            base = name[:-3]
            names = [f"{base}[{k}]" for k in range(len(widgets))]
        for widget_name, (wref, wd) in zip(names, widgets):
            on = self._on_state(wd) if ftype == "Btn" else None
            self.fields[widget_name] = FormField(
                name=widget_name, field_type=ftype, field_ref=field_ref,
                widget_ref=wref, on_state=on)

    def _on_state(self, widget: dict) -> str | None:
        ap = self.resolve(widget.get("/AP"))
        if not ap:
            return None
        n = self.resolve(ap.get("/N"))
        if not isinstance(n, dict):
            return None
        for key in n:
            if key != "/Off":
                return key.lstrip("/")
        return None


def field_value(template: "PdfTemplate", ff: "FormField"):
    """The `/V` a filled AcroForm field carries, decoded like every other PDF string here — `None`
    when the field was never filled, or a button whose state is not its ON state (then "X")."""
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
