# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Stamp local identity into the identity fields the cloud left empty.

`payload.project_case` keeps identity off the wire; this puts it back, locally. Between them they
are one boundary: the cloud says "this field holds `primary.ssn`" and the client knows what
`primary.ssn` is. Neither half can complete a return alone, which is the design working rather than
a limitation to route around.

WHY A SHARED VOCABULARY. The cloud cannot name a client's storage — it has never seen the case — and
the client cannot know a form's field geometry. A small agreed vocabulary (`primary.ssn`,
`spouse.name`, `address`) is the only thing that has to cross, and it carries no values.

FAIL-CLOSED, and for a sharper reason than in the projection. An identity field left unfilled on a
return that otherwise looks finished is worse than a refusal: a blank SSN is easy to miss on a
rendered 1040, a leftover `[SSN]` looks like a rendering bug rather than missing data, and a
silently wrong value is invisible. So an unresolvable field stops the merge and says which term
failed.

No tax knowledge, and no arithmetic: computed values pass through untouched. Doing anything else
here would put tax logic on the client, which the design forbids.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import identity_file
from .._paths import data_root

# The agreed terms. Extending this is a contract change on BOTH sides, which is why it is a closed
# set rather than a convention — an open one drifts silently and fails at render time.

# DERIVED FROM THE FORM, not declared beside it. The terms are the values of
# `generated/identity_fields_f1040_ty2025.json`, which `scripts/derive_identity_fields.py` read off
# the real IRS AcroForm. So this set cannot name a box the form does not have, cannot omit one it
# does, and cannot drift from it — `tests/test_identity_vocabulary.py` locks it both ways. The
# identity file the taxpayer edits is built from the same JSON, so the file, this vocabulary and the
# form's boxes are one thing described once.

# The previous set said `primary.name` and `address`. The form has SEPARATE first/last name boxes
# and splits the address five ways, so those terms could not fill those boxes: a full name went into
# `f1_14`, the FIRST-name box, and `f1_15`/`f1_22`/`f1_23`/`f1_24` were never filled at all.
_IDENTITY_MAP_PATH = ("generated", "identity_fields_f1040_ty2025.json")


def _derived_terms() -> frozenset[str]:
    root = data_root()
    data = json.loads((root.joinpath(*_IDENTITY_MAP_PATH)).read_text(encoding="utf-8"))
    return frozenset(data["fields"].values())


# Contact details are NOT on Form 1040's identity boxes — the form has nowhere to put them — but
# they are part of what a preparer holds locally, so they stay in the vocabulary as a named extra
# rather than vanishing from a closed contract set without anyone deciding to drop them.
NON_FORM_TERMS = frozenset({"phone", "email"})
VOCABULARY = _derived_terms() | NON_FORM_TERMS

# Local case field -> vocabulary suffix, per person role. These are STRUCTURED: the form has a box
# per part, so the case must carry a part per box.
_PERSON_TERMS = {"first_name": "first_name", "last_name": "last_name",
                 "ssn": "ssn", "itin": "ssn"}
_CASE_TERMS = {"phone": "phone", "email": "email"}

# Fields that hold several boxes' worth of identity in one string. They are REFUSED rather than
# split: "Avery Barnes" splits cleanly and "Maria de la Cruz" and "Park Ji-eun" do not, and a wrong
# split puts a surname in the wrong box where nothing on a rendered form makes it visible. The same
# goes for a one-line address against five boxes.
_UNSPLITTABLE = {
    "taxpayer_name": "first_name / last_name",
    "spouse_name": "first_name / last_name",
    "address": "street / apt / city / state / zip",
    "mailing_address": "street / apt / city / state / zip",
}


class IdentityMergeRefused(ValueError):
    """The merge stopped. Raised instead of rendering a form with a hole in it."""


def identity_index(case: dict) -> dict:
    """Build the vocabulary -> value index from structured person data.

    NOT used by the loop, and deliberately: identity cannot live in a case's facts half —
    `project_case` refuses it — so this can only be handed data that no saveable case carries. It
    remains as what it honestly is, a converter from structured person fields to vocabulary terms,
    for a caller that already holds them.

    Keyed off each person's ROLE, never their list position: `persons[0]` is not necessarily the
    primary filer, and keying off position would put the spouse's SSN on the primary's line — wrong,
    and invisible on a rendered form."""
    index = {}
    for person in case.get("persons") or []:
        role = person.get("role")
        if role not in ("primary", "spouse"):
            continue                      # dependents carry no identity fields on Form 1040 itself
        _refuse_unsplittable(person, role)
        for field, term in _PERSON_TERMS.items():
            if field in person:
                index[f"{role}.{term}"] = person[field]
    _refuse_unsplittable(case, None)
    for field, term in _CASE_TERMS.items():
        if field in case:
            index.setdefault(term, case[field])
    return index


def _refuse_unsplittable(holder: dict, role: str | None) -> None:
    """Stop on a field that packs several of the form's boxes into one string.

    Guessing is the failure this exists to prevent: splitting on whitespace is right for
    "Avery Barnes" and wrong for "Maria de la Cruz", and the wrong answer is a surname in a box
    nobody checks. So it refuses and names the file that holds the parts separately.
    """
    for field, parts in _UNSPLITTABLE.items():
        if field not in holder:
            continue
        where = f"persons[role={role!r}].{field}" if role else field
        raise IdentityMergeRefused(
            f"{where} holds one string where Form 1040 has separate boxes ({parts}). Splitting it "
            f"here would be a guess — correct for 'Avery Barnes', wrong for 'Maria de la Cruz' — "
            f"and a wrong split is invisible on a rendered return. Supply the parts separately in "
            f"{identity_file.FILENAME}, which is laid out in the form's own terms.")


def merge_identity(forms: list, index: dict, unconfirmed: dict | None = None) -> list:
    """Return a LOCAL copy of `forms` with identity values resolved.

    The response is not mutated: the filled artefact is a separate object, so nothing that could be
    sent anywhere ever carries identity."""
    filled = []
    for form in forms:
        values = {}
        for slot in form.get("identity_fields") or []:
            term, field = slot.get("identity"), slot.get("field_name")
            if term not in VOCABULARY:
                raise IdentityMergeRefused(
                    f"the response asks for identity term {term!r}, which is not in the agreed "
                    f"vocabulary. That is a contract mismatch between client and service — "
                    f"refusing rather than rendering {field!r} with a hole in it.")
            if term in (unconfirmed or {}):
                # The teeth on prefill. A value read off a document and not yet checked must not
                # reach a rendered return: a wrong prefill is worse than a blank, because a blank
                # gets attention and a wrong value does not. Refusing here, and saying WHERE it came
                # from, is what keeps a proposal a proposal.
                raise IdentityMergeRefused(
                    f"{term!r} was read from {unconfirmed[term]} and nobody has checked it "
                    f"(form {form.get('form_id')}, field {field!r}). A value nobody confirmed must "
                    f"not be printed on a return — confirm or correct it first.")
            if term not in index:
                raise IdentityMergeRefused(
                    f"no local value for {term!r} (form {form.get('form_id')}, field {field!r}). "
                    f"An identity field left blank on an otherwise finished return is easy to miss "
                    f"and impossible to distinguish from a rendering fault — refusing instead.")
            values[field] = index[term]
        filled.append({**form, "identity_values": values})
    return filled
