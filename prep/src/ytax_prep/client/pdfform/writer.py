# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Set AcroForm field values by APPENDING an incremental update (ISO 32000 §7.5.6).

The template bytes are never rewritten: the output is template + new versions of exactly the
objects being changed (each touched terminal field gets `/V`, its widget `/AS` for a button, the
AcroForm dictionary gets `/NeedAppearances true`) + one continuation cross-reference STREAM whose
`/Prev` points at the template's own xref. Stripping the appended tail therefore recovers the
pinned template byte-for-byte, and the same values produce the same bytes in any order — the
workbook's determinism discipline applied to a PDF.

Stdlib only.
"""
from __future__ import annotations

import re
import zlib

from .reader import FormField, PdfSurprise, PdfTemplate, Ref


def _serialize(value) -> bytes:
    if isinstance(value, dict):
        inner = b" ".join(_serialize_name(k) + b" " + _serialize(v) for k, v in value.items())
        return b"<< " + inner + b" >>"
    if isinstance(value, list):
        return b"[ " + b" ".join(_serialize(v) for v in value) + b" ]"
    if isinstance(value, Ref):
        return b"%d %d R" % (value.num, value.gen)
    if isinstance(value, str):  # a NAME ('/x')
        return _serialize_name(value)
    if isinstance(value, bytes):  # a string
        escaped = value.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
        escaped = escaped.replace(b"\r", b"\\r").replace(b"\n", b"\\n")
        return b"(" + escaped + b")"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if value is None:
        return b"null"
    if isinstance(value, int):
        return b"%d" % value
    if isinstance(value, float):
        return (b"%.6f" % value).rstrip(b"0").rstrip(b".")
    raise PdfSurprise(f"unserializable value of type {type(value).__name__}")


def _pdf_text(v: str) -> bytes:
    """A text string's bytes: PDFDocEncoding-compatible latin-1 when it fits, else the
    UTF-16BE-with-BOM form of ISO 32000 §7.9.2.2 — a name like "Nguyễn" is written, not crashed
    on. The reader's `_t` decodes both."""
    try:
        return v.encode("latin-1")
    except UnicodeEncodeError:
        return b"\xfe\xff" + v.encode("utf-16-be")


def _serialize_name(name: str) -> bytes:
    if not name.startswith("/"):
        raise PdfSurprise(f"a dictionary key must be a name, got {name!r}")
    out = bytearray(b"/")
    for b in name[1:].encode("latin-1"):
        if b in b"\x00\t\n\x0c\r ()<>[]{}/%#" or b < 0x21 or b > 0x7E:
            out += b"#%02X" % b
        else:
            out.append(b)
    return bytes(out)


def fill_fields(template: bytes, values: dict) -> bytes:
    """Return template + incremental update setting `values` (dotted field name -> str | bool).

    A string sets a text/choice field's `/V`; True checks a button (its widget's on-state);
    False is refused-as-noise-free: unchecked IS the template's state, nothing is written.
    Unknown names, type mismatches, and two checked widgets of one field refuse by name.
    """
    tpl = PdfTemplate(template)

    # name -> FormField, validated
    chosen: dict[str, tuple] = {}
    for name in sorted(values):
        field = tpl.fields.get(name)
        if field is None:
            raise PdfSurprise(f"no such field on this template: {name}")
        v = values[name]
        if field.field_type == "Btn":
            if not isinstance(v, bool):
                raise PdfSurprise(f"{name} is a button; its value must be True/False, got {v!r}")
            if v is False:
                continue
        elif field.field_type in ("Tx", "Ch"):
            if not isinstance(v, str):
                raise PdfSurprise(f"{name} takes a string, got {type(v).__name__}")
        else:
            raise PdfSurprise(f"{name}: field type {field.field_type} is not fillable here")
        chosen[name] = (field, v)

    # group by terminal field object; build the new object versions
    new_objects: dict[int, dict] = {}  # obj num -> new dict value

    def updated(ref: Ref) -> dict:
        if ref.gen != 0:
            raise PdfSurprise(f"object {ref.num} has generation {ref.gen}; only 0 is supported")
        if ref.num not in new_objects:
            original = tpl.resolve(ref)
            if not isinstance(original, dict):
                raise PdfSurprise(f"object {ref.num} is not a dictionary")
            new_objects[ref.num] = dict(original)  # copy — never mutate the reader's cache
        return new_objects[ref.num]

    by_field: dict[int, list] = {}
    for name in sorted(chosen):
        field, v = chosen[name]
        by_field.setdefault(field.field_ref.num, []).append((name, field, v))

    for _num, entries in sorted(by_field.items()):
        buttons = [(n, f) for (n, f, v) in entries if f.field_type == "Btn"]
        if len(buttons) > 1:
            raise PdfSurprise(
                "two widgets of the same button field cannot both be checked: "
                + ", ".join(n for n, _ in buttons))
        for name, field, v in entries:
            fd = updated(field.field_ref)
            if field.field_type == "Btn":
                if not field.on_state:
                    raise PdfSurprise(f"{name}: no on-state to check")
                fd["/V"] = "/" + field.on_state
                updated(field.widget_ref)["/AS"] = "/" + field.on_state
            else:
                fd["/V"] = _pdf_text(v)

    # NeedAppearances on the AcroForm dictionary
    if tpl.acroform_ref is None:
        raise PdfSurprise("inline AcroForm dictionaries are outside the implemented subset")
    updated(tpl.acroform_ref)["/NeedAppearances"] = True

    # append the update
    out = bytearray(template)
    if not out.endswith(b"\n"):
        out += b"\n"
    offsets: dict[int, int] = {}
    for num in sorted(new_objects):
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num + _serialize(new_objects[num]) + b"\nendobj\n"

    # continuation xref stream
    size = tpl.trailer["/Size"]
    xref_num = size
    offsets[xref_num] = len(out)
    entry_nums = sorted(offsets)
    rows = b""
    index: list[int] = []
    run_start = None
    prev_num = None
    for num in entry_nums:
        if run_start is None or num != prev_num + 1:
            if run_start is not None:
                index += [run_start, prev_num - run_start + 1]
            run_start = num
        rows += b"\x01" + offsets[num].to_bytes(4, "big") + b"\x00\x00"
        prev_num = num
    index += [run_start, prev_num - run_start + 1]

    m = re.search(rb"startxref[\x00\t\n\x0c\r ]+(\d+)", template[-64:])
    prev_xref = int(m.group(1))
    payload = zlib.compress(rows, 9)
    xref_dict = {
        "/Type": "/XRef", "/Size": size + 1, "/W": [1, 4, 2], "/Index": index,
        "/Prev": prev_xref, "/Filter": "/FlateDecode", "/Length": len(payload),
        "/Root": tpl.trailer["/Root"],
    }
    if tpl.trailer.get("/Info") is not None:
        xref_dict["/Info"] = tpl.trailer["/Info"]
    if tpl.trailer.get("/ID") is not None:
        xref_dict["/ID"] = tpl.trailer["/ID"]
    out += b"%d 0 obj\n" % xref_num + _serialize(xref_dict) + b"\nstream\n" + payload
    out += b"\nendstream\nendobj\n"
    out += b"startxref\n%d\n%%%%EOF\n" % offsets[xref_num]
    return bytes(out)
