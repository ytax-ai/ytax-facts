# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Which filer does this document belong to? (plan v2 step 2.)

A W-2 names its employee, and redaction removes that name before anything downstream reads the
document — deliberately, since the whole design keeps identity off the wire. So the question *whose
W-2 is this?* has to be answered on this machine, from what redaction LOCATED rather than from what
survived into the extraction.

WHY IT MATTERS MORE THAN IT LOOKS. `documents.py` attributed every W-2 to filer 0. Two spouses with
one W-2 each — the most ordinary joint return there is — then looked like ONE filer holding two
W-2s, which `refuse_multiple_employers` correctly refuses. The refusal was doing its job on
data that was wrong before it arrived. The mirror case is worse and does not refuse: with two of
three W-2s belonging to the primary, a spouse's wages land on the primary's line, where nothing on
a rendered return makes it visible.

THE BAR IS THE SAME AS EVERYWHERE ELSE HERE: propose only what is unambiguous, and say so plainly
when it is not. A wrong filer is a wrong return that looks finished. Names are COMPARED, never
split — by rule — so this asks only whether the parts a document offers agree with the parts a
person has.
"""
from __future__ import annotations

from dataclasses import dataclass

# What a document's located identity is called, in the DOCUMENT's terms (`prefill` keeps them that
# way on purpose), mapped to the part of a person's name it should be compared against.
_DOCUMENT_NAME_TERMS = {
    "employee.name": "first_name",        # W-2 box e is "first name and initial"
    "recipient.name": "first_name",
    "winner.name": "first_name",
    "partner.name": "first_name",
    "person.last_name": "last_name",
}

# Why no filer could be proposed. A closed set: these are the cases a person has to resolve, and
# free text would make them impossible to count or to handle differently.
NO_NAME = "no-name-located"        # redaction found no name on the document to match on
NO_MATCH = "matches-nobody"        # a name was found and it matches none of the filers
AMBIGUOUS = "matches-several"      # it matches more than one filer


@dataclass(frozen=True)
class FilerProposal:
    """The filer a document appears to belong to. A PROPOSAL, confirmable like any other."""

    person: int
    matched_on: tuple


@dataclass(frozen=True)
class NoFiler:
    """No filer could be proposed, and why. The reason is the question to put to a person."""

    reason: str
    candidates: tuple = ()


def _key(text: str) -> str:
    """Compare on case and spacing only.

    Deliberately not a fuzzy match. `Pat` and `Patricia` are different people until somebody says
    otherwise, and a similarity threshold is exactly the kind of guess that puts a spouse's wages on
    the primary's line without anything looking wrong.
    """
    return " ".join(text.split()).casefold()


def _first_token(text: str) -> str:
    """A W-2's box e holds `first name and initial`, so `Pat Q` should match the person `Pat`."""
    parts = _key(text).split()
    return parts[0] if parts else ""


def propose_filer(located: dict, persons: list) -> FilerProposal | NoFiler:
    """Match a document's located name against the filers already known.

    `located` is the document's identity in its own terms (`{"employee.name": "Pat Q"}`), as
    `prefill.propose` produces it. `persons` is the filers, each a mapping that may carry
    `first_name` and `last_name`.

    A single filer is unambiguous by construction: there is nobody else it could be.

    Otherwise every name part the document offers must agree with that person, and **exactly one**
    person may match. Zero or several is a question, not a default — because the default that was
    there before, filer 0, is precisely what made an ordinary joint return unfilable.
    """
    if len(persons) <= 1:
        return FilerProposal(person=0, matched_on=("only filer",))

    offered = {part: value for term, value in located.items()
               if (part := _DOCUMENT_NAME_TERMS.get(term)) and str(value).strip()}
    if not offered:
        return NoFiler(NO_NAME)

    matches, matched_on = [], ()
    for index, person in enumerate(persons):
        agreed = []
        for part, value in sorted(offered.items()):
            known = str(person.get(part) or "").strip()
            if not known:
                continue                      # this person has no such part: neither agree nor not
            if part == "first_name":
                ok = _first_token(value) == _first_token(known)
            else:
                ok = _key(value) == _key(known)
            if not ok:
                agreed = []
                break
            agreed.append(part)
        if agreed:
            matches.append(index)
            matched_on = tuple(agreed)

    if not matches:
        return NoFiler(NO_MATCH)
    if len(matches) > 1:
        # Two filers the document cannot distinguish — spouses sharing a surname, with no first name
        # located. Guessing here is the failure this module exists to prevent.
        return NoFiler(AMBIGUOUS, candidates=tuple(matches))
    return FilerProposal(person=matches[0], matched_on=matched_on)
