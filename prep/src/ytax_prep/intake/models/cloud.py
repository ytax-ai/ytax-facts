# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The cloud tier's guard.

A cloud model may see what a blank form and the dictionary say — captions, writable names,
question wording — and never what a person's documents or answers say. The guard is by TYPE:
only a `ValueFreeQuestion` is accepted, never a case, a fact set or free text. And by CONTENT:
no field of it may carry a value shape — an amount, a dollar sign, a taxpayer-ID, EIN or date
shape, a year outside the tax years in scope, a long digit run, or a collection member id. Form
numbers (1040, 1099-R, 8889), box numbers and codes (2a, 12, code 7) and writable names with
digits in them (`roth401kContributions`) are not values and pass.

The provider, account and key are the person's own, entered on their machine;
this program holds none. Every call is logged without the key so the page can list it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# The tax years a value-free question may name (the forms' own years); any other year is treated
# as a person's date — a birth year, a year of death, a prior return's year.
TAX_YEARS = frozenset({"2024", "2025", "2026"})

_VALUE_SHAPES = (
    re.compile(r"\$"),                                         # a dollar sign
    re.compile(r"\d[\d,]*\.\d{2}(?!\d)"),                      # 43,780.00 · 634.81
    re.compile(r"(?<!\d)\d{1,3}(?:,\d{3})+(?!\d)"),            # 43,780
    re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),             # a taxpayer ID
    re.compile(r"(?<!\d)\d{2}-\d{7}(?!\d)"),                   # an EIN
    re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)"),             # an ISO date
    re.compile(r"(?<!\d)\d{1,2}/\d{1,2}/\d{2,4}(?!\d)"),       # a written date
    re.compile(r"(?<![A-Za-z\d])\d{5,}(?![A-Za-z\d])"),        # a ZIP, an account number
    re.compile(r"#"),                                          # a collection member id
)
_YEAR = re.compile(r"(?<![A-Za-z\d])((?:19|20)\d{2})(?![A-Za-z\d])")


class CloudRefused(ValueError):
    """The question may not leave the computer, or there is no provider to send it to."""


@dataclass(frozen=True)
class ValueFreeQuestion:
    form: str
    captions: tuple
    writables: tuple
    question: str

    def texts(self):
        return (self.form, *self.captions, *self.writables, self.question)


def value_shape_in(text: str) -> str | None:
    """The first value-shaped fragment in `text`, or None."""
    for shape in _VALUE_SHAPES:
        m = shape.search(text)
        if m:
            return m.group(0)
    for m in _YEAR.finditer(text):
        if m.group(1) not in TAX_YEARS:
            return m.group(1)
    return None


def _no_provider(provider, key, payload):
    raise CloudRefused("no provider configured — the cloud tier is off until you name a provider "
                       "and enter your own key")


class CloudClient:
    def __init__(self, provider: str, key: str, transport=None):
        self.provider = provider
        self._key = key
        self._transport = transport if (transport is not None and provider and key) else _no_provider
        self.log: list = []

    def ask(self, q) -> str:
        if type(q) is not ValueFreeQuestion:
            raise CloudRefused(f"only a value-free question may be sent, not {type(q).__name__}")
        for text in q.texts():
            if not isinstance(text, str):
                raise CloudRefused("every part of a value-free question is text")
            found = value_shape_in(text)
            if found is not None:
                raise CloudRefused(f"the question carries a value ({found!r}), so it stays on this computer")
        payload = {"form": q.form, "captions": list(q.captions), "writables": list(q.writables),
                   "question": q.question}
        reply = self._transport(self.provider, self._key, payload)
        self.log.append({"provider": self.provider, **payload})
        return reply
