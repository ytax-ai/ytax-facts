# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Typed answers, parsed by rule — never by a model.

What a person types into the conversation becomes a fact value through the schema's own types:
money in dollars becomes integer cents, a yes/no becomes a boolean, a choice takes one of its
codes, a whole number respects its bounds, a person is counted from 1, a code matches its pattern.
Every refusal is one of the copy rules' fixed formulas ("This is required", "Must be between 1 and
12", "is not an amount") and never carries a field name.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..client.interview import choice_words, choices_for
from .._paths import data_root

_SCHEMA = data_root() / "schema" / "common"
_TRUE, _FALSE = {"true", "yes", "y"}, {"false", "no", "n"}
_MONEY = re.compile(r"^-?\d+(?:\.\d{1,2})?$")


class AnswerError(ValueError):
    """The typed answer does not fit the question; the message is the sentence the person reads."""


def _field_specs() -> dict:
    """Every declared property name → its schema node (first declaration wins)."""
    specs: dict = {}

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.get("properties", {}).items():
                specs.setdefault(key, value)
                walk(value)
            if "items" in node:
                walk(node["items"])

    for path in sorted(_SCHEMA.rglob("*.json")):
        walk(json.loads(path.read_text(encoding="utf-8")))
    return specs


_SPECS = _field_specs()


def _field_of(path: str) -> str:
    return path.rsplit(".", 1)[-1]


def parse_answer(path: str, text: str):
    field = _field_of(path)
    typed = (text or "").strip()
    if not typed:
        raise AnswerError("This is required")
    if field == "person":
        if not typed.isdigit() or int(typed) < 1:
            raise AnswerError("Must be a person's number, from 1")
        return int(typed) - 1
    spec = _SPECS.get(field)
    if spec is None:
        raise AnswerError("This is not a question this return asks")
    if field.endswith("_cents") or str(spec.get("$ref", "")).endswith("cents.schema.json"):
        amount = typed.replace("$", "").replace(",", "").strip()
        if not _MONEY.match(amount):
            raise AnswerError(f'"{typed}" is not an amount')
        if amount.startswith("-"):
            raise AnswerError("Must be 0 or more")
        try:
            return int(Decimal(amount) * 100)
        except InvalidOperation:
            raise AnswerError(f'"{typed}" is not an amount')
    if spec.get("type") == "boolean":
        low = typed.lower()
        if low in _TRUE:
            return True
        if low in _FALSE:
            return False
        raise AnswerError("Must be true or false")
    codes = spec.get("enum") or choices_for(field)
    if codes:
        match = next((c for c in codes if str(c).lower() == typed.lower()), None)
        words = choice_words(field) or {}
        if match is None:                  # the words the question offers are an answer too
            match = next((c for c, w in words.items() if w.lower() == typed.lower()), None)
        if match is None:
            raise AnswerError("Must be one of: " + ", ".join(words.get(c, str(c)) for c in codes))
        return match
    if spec.get("type") == "integer":
        if not re.fullmatch(r"-?\d+", typed):
            raise AnswerError(f'"{typed}" is not a whole number')
        value = int(typed)
        low, high = spec.get("minimum"), spec.get("maximum")
        if (low is not None and value < low) or (high is not None and value > high):
            if low is not None and high is not None:
                raise AnswerError(f"Must be between {low} and {high}")
            raise AnswerError(f"Must be {low} or more" if low is not None else f"Must be {high} or less")
        return value
    pattern = spec.get("pattern")
    if pattern:
        candidate = typed.upper() if re.search(r"\[0-9A-Z\]", pattern) else typed
        if not re.fullmatch(pattern.strip("^$"), candidate):
            raise AnswerError(f'"{typed}" is not a code')
        return candidate
    return typed
