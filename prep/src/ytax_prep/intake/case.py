# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The intake case: service facts with per-fact provenance.

A `Case` never states a value the person or a document did not actually give it. Readers
`propose()` candidates — a value plus `Evidence` naming exactly where it came from (document,
page, box caption, source rectangle, raw text, reading tier). Only a `confirm()`ed, `answer()`ed
or `derive()`d value is a fact; `facts()` builds the nested service fact set from confirmed values
only. Two candidates that disagree on value are a `conflict` — `confirm()` refuses to pick one
blind; the caller must name the value to keep. An identifier field (name, ssn, address, ...) is
refused at `propose()` time: the case makes it unrepresentable, never merely unread.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from .._paths import data_root

NOT_GIVEN = object()

# More exact first: an "answer" (a person said so) or a "derived" fact beats anything read off a
# document; among document tiers, an exact field beats geometry, geometry beats OCR, OCR beats a
# model's guess.
TIER_ORDER = ("answer", "derived", "field", "geometry", "ocr", "model")

_PATH_RE = re.compile(r"^([a-z_0-9]+)(?:\[(\d+)\]\.([a-z_0-9]+))?$")
_IDENTITY_RE = re.compile(r"name|ssn|tin$|address|street|city|zip|phone|email|ein")


def _schema_field_names() -> frozenset:
    """Every property name the fact schema declares. The schema carries no identifier by design,
    so a declared name is never one — `estimated_payments_under_different_name` is a yes/no about
    estimated payments, and the identity pattern alone refused it (found in review)."""
    from pathlib import Path
    root = data_root() / "schema" / "common"
    names = set()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.get("properties", {}).items():
                names.add(key)
                walk(value)
            if "items" in node:
                walk(node["items"])

    for path in root.rglob("*.json"):
        walk(json.loads(path.read_text(encoding="utf-8")))
    return frozenset(names)


_SCHEMA_FIELDS = _schema_field_names()


class CaseError(ValueError):
    """A fact path is malformed, an identifier, or a confirm was asked to guess a value."""


@dataclass(frozen=True)
class Evidence:
    document: str
    page: int
    caption: str
    rect: tuple | None
    raw: str
    tier: str


@dataclass(frozen=True)
class Candidate:
    path: str
    value: object
    evidence: Evidence


def _parse_path(path):
    m = _PATH_RE.match(path)
    if not m:
        raise CaseError(f"not a fact path: {path!r}")
    return m.groups()  # (root, index-or-None, field-or-None)


def _check_path(path):
    root, index, field = _parse_path(path)
    last = field if field is not None else root
    if last not in _SCHEMA_FIELDS and _IDENTITY_RE.search(last):
        raise CaseError(f"identifier field refused: {path!r}")
    return root, index, field


def _evidence_dict(evidence):
    return {
        "document": evidence.document,
        "page": evidence.page,
        "caption": evidence.caption,
        "rect": list(evidence.rect) if evidence.rect is not None else None,
        "raw": evidence.raw,
        "tier": evidence.tier,
    }


def _evidence_from_dict(d):
    rect = d["rect"]
    return Evidence(d["document"], d["page"], d["caption"], tuple(rect) if rect is not None else None,
                     d["raw"], d["tier"])


class Case:
    def __init__(self, tax_year: int = 2025):
        self.tax_year = tax_year
        self._pending: dict[str, list[Candidate]] = {}
        self._confirmed: dict[str, tuple[object, Evidence]] = {}
        # answers a person TYPED for a form this version does not read — engine
        # inputs, keyed by engine path, held BESIDE the fact set and never inside it
        # (`facts.extras`). Each keeps the words it was asked in: that is its provenance.
        self._typed: dict[str, tuple[object, Evidence]] = {}
        # the DAY of each person's date of birth, by their number in `persons`.
        # Beside the fact set for the reason `_typed` is beside it — the fact schema holds no birth
        # day and no request can carry one; this reaches the engine through the in-process seam.
        self._birth_days: dict[int, int] = {}

    def keep_birth_day(self, person_index: int, day: int) -> None:
        self._birth_days[int(person_index)] = int(day)

    def birth_days(self) -> dict:
        """`{person index: day}` — what `map_to_engine(..., birth_days=...)` takes."""
        return dict(self._birth_days)

    def type_in(self, path: str, value, question: str) -> None:
        self._typed[path] = (value, Evidence("", 0, question, None, str(value), "typed"))

    def untype(self, paths) -> None:
        for path in list(paths):
            self._typed.pop(path, None)

    def typed(self) -> dict:
        """engine path -> value, exactly what `facts.extras` validates and merges."""
        return {path: value for path, (value, _evidence) in self._typed.items()}

    def typed_with_words(self) -> dict:
        return {path: (value, evidence.caption) for path, (value, evidence) in self._typed.items()}

    def propose(self, cand: Candidate) -> None:
        _check_path(cand.path)
        self._pending.setdefault(cand.path, []).append(cand)

    def pending(self) -> dict:
        return {path: list(cands) for path, cands in self._pending.items()}

    def conflicts(self) -> list:
        out = []
        for path, cands in self._pending.items():
            values = [c.value for c in cands]
            if any(v != values[0] for v in values[1:]):
                out.append(path)
        return out

    def confirm(self, path: str, value=NOT_GIVEN) -> None:
        _check_path(path)
        cands = self._pending.get(path)
        if not cands:
            raise CaseError(f"no pending candidate for {path!r}")
        if value is NOT_GIVEN:
            values = [c.value for c in cands]
            if any(v != values[0] for v in values[1:]):
                raise CaseError(f"{path} candidates disagree: {values} — pass the value to keep")
            chosen = values[0]
        else:
            chosen = value
        matching = [c for c in cands if c.value == chosen]
        if matching:
            best = min(matching, key=lambda c: TIER_ORDER.index(c.evidence.tier))
            evidence = best.evidence
        else:
            # `value` names something no candidate proposed — a person's own correction, not
            # what any reader read. Keep the box location for reference but tell the truth about
            # who said it: tier "answer", not the reader's tier or its raw text.
            best = min(cands, key=lambda c: TIER_ORDER.index(c.evidence.tier))
            e = best.evidence
            evidence = Evidence(e.document, e.page, e.caption, e.rect, str(chosen), "answer")
        self._confirmed[path] = (chosen, evidence)
        del self._pending[path]

    def answer(self, path: str, value, question: str) -> None:
        _check_path(path)
        evidence = Evidence("", 0, question, None, str(value), "answer")
        self._confirmed[path] = (value, evidence)
        self._pending.pop(path, None)

    def derive(self, path: str, value, reason: str) -> None:
        _check_path(path)
        evidence = Evidence("", 0, reason, None, str(value), "derived")
        self._confirmed[path] = (value, evidence)
        self._pending.pop(path, None)

    def forget(self, path: str) -> None:
        """Drop one answer so it can be asked again (a refusal is not a dead end — the person
        changes the answer that caused it). Only what a PERSON said is forgettable; a value read
        from a document is re-confirmed through its own turn, and a derived value follows whatever
        it was derived from."""
        _check_path(path)
        if path not in self._confirmed:
            raise CaseError(f"nothing answered at {path!r}")
        _value, evidence = self._confirmed[path]
        if evidence.tier != "answer":
            raise CaseError(f"{path} was not answered by a person ({evidence.tier})")
        del self._confirmed[path]

    def confirmed(self) -> dict:
        return dict(self._confirmed)

    def facts(self) -> dict:
        result = {"tax_year": self.tax_year}
        groups: dict[str, dict[int, dict]] = {}
        for path, (value, _evidence) in self._confirmed.items():
            root, index, field = _parse_path(path)
            if index is None:
                result[root] = value
            else:
                item = groups.setdefault(root, {}).setdefault(int(index), {})
                item[field] = value
        for group, items_by_index in groups.items():
            lst = [items_by_index.get(i, {}) for i in range(max(items_by_index) + 1)]
            while lst and lst[-1] == {}:
                lst.pop()
            if lst:
                result[group] = lst
        return result

    def to_json(self) -> str:
        pending = [
            {"path": cand.path, "value": cand.value, "evidence": _evidence_dict(cand.evidence)}
            for cands in self._pending.values()
            for cand in cands
        ]
        confirmed = {
            path: {"value": value, "evidence": _evidence_dict(evidence)}
            for path, (value, evidence) in self._confirmed.items()
        }
        typed = {path: {"value": value, "evidence": _evidence_dict(evidence)}
                 for path, (value, evidence) in self._typed.items()}
        return json.dumps({"tax_year": self.tax_year, "pending": pending, "confirmed": confirmed,
                           "typed": typed,
                           "birth_days": {str(i): d for i, d in self._birth_days.items()}})

    @classmethod
    def from_json(cls, text: str) -> "Case":
        data = json.loads(text)
        case = cls(tax_year=data["tax_year"])
        for item in data["pending"]:
            evidence = _evidence_from_dict(item["evidence"])
            case._pending.setdefault(item["path"], []).append(Candidate(item["path"], item["value"], evidence))
        for path, item in data["confirmed"].items():
            case._confirmed[path] = (item["value"], _evidence_from_dict(item["evidence"]))
        for path, item in (data.get("typed") or {}).items():     # absent in a case kept before typed lines
            case._typed[path] = (item["value"], _evidence_from_dict(item["evidence"]))
        for index, day in (data.get("birth_days") or {}).items():   # absent in a case kept before birth days
            case._birth_days[int(index)] = int(day)
        return case
