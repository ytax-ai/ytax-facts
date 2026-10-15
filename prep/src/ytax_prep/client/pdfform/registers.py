# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Read build's per-form field register (`configuration.yml`) — a restricted YAML subset.

The registers are hand-and-sweep-authored mappings, one per template: nested mappings only, one
entry per line, `#` comments, no lists, no quoting, no multi-line scalars. That subset is parsed
here with the stdlib and anything outside it is REFUSED BY NAME (`RegisterSurprise`): the register
bytes are pinned (`REGISTERS_SHA256` in tests/test_register_locks.py), so a surprise is a
pin-bump event to look at, not input to guess through.

A mapping's VALUE is kept raw. Most are a single fact path; some are upstream's filler constructs
(`~` pseudo-path accessors, two paths joined by the word `space`) — classifying those is the
filler's job, and an unimplemented construct becomes a stated blank, never a guess.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class RegisterSurprise(ValueError):
    """The register used a construct outside the restricted subset — named, never guessed."""


_LINE = re.compile(r"^(?P<indent> *)(?P<key>[^:#\s][^:#]*):(?: (?P<value>[^#].*?))?\s*(?:#.*)?$")


@dataclass
class FormRegister:
    form_key: str                    # "IRS1040"
    template: Path | None            # the sibling f*.pdf; None until the blank form is fetched
    gate_kind: str | None            # "includeWhen" | "includeForEach" | None (ungated: never renders)
    gate_path: str | None            # the gate fact path
    mappings: dict                   # dotted AcroForm field name -> raw register value


def read_register(config_path: Path) -> FormRegister:
    form_key = config_path.parent.parent.name
    pdfs = sorted(config_path.parent.glob("*.pdf"))
    if len(pdfs) > 1:
        raise RegisterSurprise(f"{form_key}: expected exactly one template pdf, found {len(pdfs)}")
    # A released copy fetches the blank IRS forms separately (scripts/fetch_irs_forms.py); a form
    # whose blank is not there yet still reads (its field map serves the document reader) and is
    # refused by name only if a return needs it printed.

    gate_kind = gate_path = None
    mappings: dict = {}
    stack: list[tuple[int, str]] = []  # (indent, key) path under `form:`
    in_form = False

    for lineno, line in enumerate(config_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line:
            raise RegisterSurprise(f"{form_key}:{lineno}: tab indentation is outside the subset")
        m = _LINE.match(line)
        if not m:
            raise RegisterSurprise(f"{form_key}:{lineno}: unparseable line {line!r}")
        indent, key, value = len(m.group("indent")), m.group("key").strip(), m.group("value")

        if indent == 0:
            in_form = key == "form"
            stack = []
            if key in ("includeWhen", "includeForEach"):
                if gate_kind is not None:
                    raise RegisterSurprise(f"{form_key}:{lineno}: two render gates")
                if not value or not value.startswith("/"):
                    raise RegisterSurprise(f"{form_key}:{lineno}: gate has no fact path")
                gate_kind, gate_path = key, value.strip()
            elif key != "form":
                raise RegisterSurprise(f"{form_key}:{lineno}: unknown top-level key {key!r}")
            continue

        if not in_form:
            raise RegisterSurprise(f"{form_key}:{lineno}: indented content outside `form:`")
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if value is None or value == "":
            stack.append((indent, key))
        else:
            dotted = ".".join([k for _, k in stack] + [key])
            if dotted in mappings:
                raise RegisterSurprise(f"{form_key}:{lineno}: duplicate mapping for {dotted}")
            mappings[dotted] = value.strip()

    # A register with NO gate is a real pinned state (UNMAPPED.md marks several `NO`): upstream's
    # rule is that a gateless form can never render, so the filler reports it as ungated rather
    # than crashing here or silently dropping it.
    return FormRegister(form_key=form_key, template=pdfs[0] if pdfs else None,
                        gate_kind=gate_kind, gate_path=gate_path, mappings=mappings)


def read_all(pdf_root: Path) -> dict:
    """Every form register under `<pdf_root>/<FORM>/en/configuration.yml`, keyed by form."""
    out = {}
    for cfg in sorted(pdf_root.glob("*/en/configuration.yml")):
        reg = read_register(cfg)
        out[reg.form_key] = reg
    return out


def form_kinds(pdf_root: Path) -> dict:
    """`{form_key: kind}` from the dictionary's own `form-modules.tsv`: `render` for a
    form this repo prints, `input-document` for one the person received (INPUT-FORMS.md §a, never
    printed). {} when the pin carries no table, so nothing changes at a pin before it."""
    path = Path(pdf_root) / "form-modules.tsv"
    if not path.is_file():
        return {}
    kinds = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cells = line.split("\t")
        if len(cells) >= 2 and cells[0] and cells[0] != "form":
            kinds[cells[0].strip()] = cells[1].strip()
    return kinds
