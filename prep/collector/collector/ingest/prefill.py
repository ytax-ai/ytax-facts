# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Propose identity values from what redaction located (plan v2 step 1b).

THE ASYMMETRY THIS MODULE EXISTS FOR. `redact.locate_identity` serves two consumers with **opposite
bars**. Redaction optimises RECALL: burning a form's title by accident harms nothing, so a generous
superset is exactly right. Prefill optimises PRECISION: a wrong value written into a taxpayer's
identity file is worse than a blank one, because — in the plan's own words — *a blank gets attention
and a wrong value does not*. Same hits, opposite filters.

MEASURED BEFORE THIS EXISTED: **68%** of located hits were the identity value. The rest included the
form's own title offered as an employee address, a page fragment (`'erei f yourm ainh ome,a ndy
our'`) offered as a spouse SSN, and a partial value (`'Faketown ZZ'` where the line reads `Faketown
ZZ 00000'`) — which is not a near miss but a wrong box.

SO THE BAR IS PRECISION, NOT COVERAGE. Proposing nothing is a safe outcome; proposing wrongly is
not. Everything located and not proposed is REPORTED, with the reason, never silently dropped:
"we could not vouch for this" is information, and it is the thing a person can act on.

VALIDATION IS BY SHAPE AND BY THE LABEL TABLES — NEVER BY A BLACKLIST. Rejecting the string
`'Form W-2 Wage and Tax Statement'` by listing it would repeat `fixtures/synthetic.py`'s mistake
exactly: a check written against the corpus's own junk, which passes for that corpus and nothing
else. A candidate is rejected because it *has the shape of a label* or *lacks the shape of its
term*, both of which generalise.

TERMS ARE DOCUMENT-RELATIVE, and that is the trust boundary, not an oversight. A W-2 says
`employee.name`; only the client knows WHICH PERSON that is. Mapping `employee.name ->
primary.first_name` here would silently decide whose W-2 this is, which for a joint return is a
decision nobody made — it is plan step 2 (filer matching), and it belongs on the other side.

PROPOSALS NEVER REACH `out/`. They stay on the in-memory object and are excluded from the
serialised IR, the same rule `raw_text` follows since it was found carrying a plaintext EIN into
`out/sources/`. This data is strictly worse than that was.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .extract import FORM_FIELDS
from .redact import Hit, _IDENTITY_LABELS, _norm

# Shapes strong enough to vouch for. A TIN is nine digits or the dashed form; an EIN is its own
# dashed form; a name is letters and the punctuation names really carry, with NO digits.
_TIN = re.compile(r"^(?:\d{9}|\d{3}-\d{2}-\d{4})$")
_EIN = re.compile(r"^(?:\d{9}|\d{2}-\d{7})$")
_NAME = re.compile(r"^[A-Za-z][A-Za-z.'\-]*(?: [A-Za-z][A-Za-z.'\-]*){0,4}$")

# Why a located value was not proposed. A closed set, because these counts are the honest report of
# how much prefill actually covers — free text would make that unmeasurable.
LOOKS_LIKE_A_LABEL = "looks-like-a-label"     # the text contains a form's own label
WRONG_SHAPE = "wrong-shape"                   # not the shape its term claims
NO_VALIDATOR = "no-validator"                 # this term has no shape we can vouch for yet
CONFLICT = "conflict"                         # the same term was located twice, differently


@dataclass(frozen=True)
class Proposal:
    """A value we are willing to put in front of a person, in the DOCUMENT's terms.

    Deliberately carries no confidence score. `Hit.confidence` was a constant nothing read, and a
    number that is always 0.9 reads as evidence while being decoration. A proposal is made or it is
    not; the reason it was not is on `Unproposed`.
    """

    term: str
    value: str


@dataclass(frozen=True)
class Unproposed:
    """Located, and not vouched for. Reported rather than dropped."""

    term: str
    text: str
    reason: str


def _labels() -> tuple[str, ...]:
    """Every label either module knows: a value that contains one is a label, not a value."""
    out = [lab for lab, _term in _IDENTITY_LABELS]
    # each declared SPELLING is a label of its own
    out += [spelling for table in FORM_FIELDS.values() for spellings in table.values() for spelling in spellings]
    return tuple(out)


def _validator(term: str):
    if term.endswith(".ein"):
        return _EIN
    if term.endswith((".ssn", ".tin")):
        return _TIN
    if term.endswith((".name", ".first_name", ".last_name")):
        return _NAME
    # Addresses are COMPOUND — `Faketown ZZ 00000` is three of the form's boxes in one string — and
    # It is settled that a value spanning several boxes is refused rather than split. That argument
    # was made for names, where "Maria de la Cruz" has no safe split; zip and state are more
    # shape-anchored, so this is defensible to revisit. It is a decision to make deliberately on the
    # client side, not one to inherit here by writing a parser.
    return None


def propose(hits: list[Hit]) -> tuple[list[Proposal], list[Unproposed]]:
    """Split located hits into what we will vouch for and what we will not.

    Returns `(proposals, unproposed)`. Both are reported: the second is not a failure list, it is
    the honest statement of what redaction found and prefill could not confirm.
    """
    labels = _labels()
    proposals: dict[str, Proposal] = {}
    unproposed: list[Unproposed] = []
    conflicted: set[str] = set()

    for hit in hits:
        text = hit.text.strip()
        norm = _norm(text)

        if any(lab in norm for lab in labels):
            unproposed.append(Unproposed(hit.term, text, LOOKS_LIKE_A_LABEL))
            continue

        shape = _validator(hit.term)
        if shape is None:
            unproposed.append(Unproposed(hit.term, text, NO_VALIDATOR))
            continue
        if not shape.match(text):
            unproposed.append(Unproposed(hit.term, text, WRONG_SHAPE))
            continue

        existing = proposals.get(hit.term)
        if existing is None:
            proposals[hit.term] = Proposal(hit.term, text)
        elif existing.value != text:
            # Two different answers for one term. Neither is proposed: choosing between them would
            # be a guess, and a guess here is the wrong-prefill case this module exists to avoid.
            conflicted.add(hit.term)
            unproposed.append(Unproposed(hit.term, text, CONFLICT))
        # An identical repeat is simply the same value found twice — deduped, not a conflict.

    for term in conflicted:
        dropped = proposals.pop(term, None)
        if dropped is not None:
            unproposed.append(Unproposed(term, dropped.value, CONFLICT))

    return sorted(proposals.values(), key=lambda p: p.term), unproposed
