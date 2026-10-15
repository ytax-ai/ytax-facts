# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The model reader tier: the last resort, and never trusted on its own say-so.

`read_with_model` sends one rendered page to a model client (`LocalModel` or, in tests,
`FakeModel`) with a prompt naming the form and every caption still unread, and a JSON schema that
can hold nothing but a string per caption field. Whatever comes back is filtered by the SAME code
path every other tier answers to: a field the caption map never named is not a service field at
all and is dropped; a value that does not `value_shaped()` for its field's kind — a code box
holding something money-shaped, a money box holding letters — is dropped too. The model's own
confidence, if it reports one, is never read: only this shape check decides whether a value
becomes a `Candidate` for a person to confirm.
"""
from __future__ import annotations

import re

from ytax_prep.client.documents import CODE_RE, FACT_GROUPS, LABEL_KINDS

MONEY, CODE, CHECK = "money", "code", "check"

try:  # pragma: no cover - exercised only inside the collector venv
    from collector.ingest.extract import value_shaped as _collector_value_shaped
except ImportError:  # pragma: no cover - the normal case outside the collector venv
    _collector_value_shaped = None

_CHECK_MARKS = frozenset({"x", "[x]", "☒", "☑", "✓", "✔"})
# A local stand-in for collector.ingest.extract's own money check (parse_money_cents), used only
# when the collector package is not importable (no venv on PYTHONPATH). Same shape it accepts:
# an optional sign or parens, an optional "$", grouped or ungrouped digits, an optional cents part.
_MONEY_RE = re.compile(r"^\(?-?\$?\s*\d{1,3}(,\d{3})*(\.\d{1,2})?\)?$")


def _local_value_shaped(kind: str, text: str) -> bool:
    text = text.strip()
    if kind == CODE:
        return CODE_RE.match(text.upper()) is not None
    if kind == CHECK:
        return text.lower() in _CHECK_MARKS
    return _MONEY_RE.match(text) is not None


def value_shaped(kind: str, text: str) -> bool:
    if _collector_value_shaped is not None:
        return _collector_value_shaped(kind, text)
    return _local_value_shaped(kind, text)


def _kind_for_field(form_type: str, field: str) -> str:
    """The value kind (`money`/`code`/`check`) a service field holds, keyed back through the
    per-form label maps in `client.documents` — the same maps and the same `LABEL_KINDS` the
    document-reading tiers use, so the model tier judges a value exactly as they do."""
    group = FACT_GROUPS.get(form_type)
    if group is None:
        return MONEY
    _, label_to_field = group
    for label, mapped_field in label_to_field.items():
        if mapped_field == field:
            return LABEL_KINDS.get(label, MONEY)
    return MONEY


def _schema_for(captions: dict[str, str]) -> dict:
    """One optional string property per service field the caller still wants read; nothing else
    is representable, so a model cannot invent a field this schema did not name."""
    return {
        "type": "object",
        "properties": {field: {"type": "string"} for field in captions},
        "additionalProperties": False,
    }


def _prompt_for(form_type: str, captions: dict[str, str]) -> str:
    lines = [
        f"This image is one page of a {form_type} tax form. Read each of the following boxes "
        "and report the value exactly as printed. Omit a field entirely if its box is blank or "
        "cannot be read.",
    ]
    for field, caption in captions.items():
        lines.append(f"- {field}: {caption}")
    return "\n".join(lines)


def read_with_model(page_png: bytes, form_type: str, captions: dict[str, str],
                     model) -> list[tuple[str, str]]:
    """Read every caption in `captions` off `page_png` through `model`. Returns
    `[(service_field, raw_text)]` for values the model returned that pass `value_shaped()` for
    that field's kind; a field the model invented (not in `captions`) or a malformed value is
    silently dropped, never asked about differently than an unread box. `ModelUnavailable` from
    `model.extract()` propagates — the caller decides what an unavailable model tier means."""
    schema = _schema_for(captions)
    prompt = _prompt_for(form_type, captions)
    reply = model.extract(page_png, prompt, schema)
    if not isinstance(reply, dict):
        return []
    out = []
    for field, caption in captions.items():
        if field not in reply:
            continue
        raw = reply[field]
        if not isinstance(raw, str):
            continue
        kind = _kind_for_field(form_type, field)
        if value_shaped(kind, raw):
            out.append((field, raw))
    return out
