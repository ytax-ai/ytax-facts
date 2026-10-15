# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""What the `coverage` operation answers — DERIVED, never hand-typed.

The published boundary has exactly two machine sources:

  * ``service/lines.py::LINE_MAP`` — the Form 1040 lines this service reports and can explain;
  * ``facts/mapper.py`` — the enforced refusal boundary (covered filing statuses, covered fact
    groups, refused income streams, one label per group, and the dependents and age-65 refusals
    verbatim).

So a change to what the service DOES changes what it SAYS, in the same commit. The one exception is
``DECLARED_EXCLUSIONS``: scope statements no code in this repo can measure, because nothing here
computes them at all. Those are marked as declared, and ``tests/test_coverage_derivation.py`` locks
each one two ways — the thing it says is out is ATTEMPTED (and refused), and the entry may not
vanish from the published answer.

World #1: this reports what the service computes and what it refuses. It makes no accuracy claim.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..facts import mapper
from . import lines as _lines
from .._paths import data_root


def _form_label() -> str:
    """"Form 1040 (2025)" — read off the line map's own citations, not restated here."""
    locator = _lines.LINE_MAP[0]["citation"]["locator"]
    return locator.split(", line")[0]


def supported_forms() -> list:
    """The covered inputs, then one entry per line the service actually serves."""
    statuses = ", ".join(sorted(mapper.COVERED_FILING_STATUSES))
    # Every covered fact group except the two structural ones (a filing status and filers are what
    # "filing status single" already says) — so promoting an income group to covered publishes it.
    inputs = [mapper.FACT_GROUP_LABELS[g]
              for g in sorted(mapper.COVERED_FACT_GROUPS - {"filing_status", "persons"})]
    form = _form_label()
    entries = [f"Filing status {statuses}, with {'; '.join(inputs)} — computed cent-exact, "
               f"with a citation on every line"]
    entries += [f"{form} line {spec['line_id']} — {spec['label']}" for spec in _lines.LINE_MAP]
    return entries


# Scope statements, NOT derived: nothing in this repo computes these, so nothing here can measure
# them. Each is attempted-and-refused in tests, and each is locked into the published answer.
DECLARED_EXCLUSIONS = (
    "itemized deductions — the standard deduction is the only deduction path this service computes",
    # Retired: "the additional standard deduction for blindness — there is no field for
    # it": there is one now (`persons[].is_blind`, Form 1040 line 12's own checkbox, asked on
    # every filer row), so publishing the old sentence would understate what is computed —
    # a served claim the code contradicts.
    "state returns — this service computes a federal return only",
    "Form 2210, the estimated-tax penalty",
    "e-filing — this service computes and cites; it never files",
)


def exclusions(tax_year: int) -> list:
    """Everything the service refuses, in the words of the refusal itself where there are any."""
    out = []
    pending = sorted(mapper.FILING_STATUSES - mapper.COVERED_FILING_STATUSES)
    if pending:
        covered = ", ".join(sorted(mapper.COVERED_FILING_STATUSES))
        # The reason clause holds for exactly the statuses that can still be pending: hoh and
        # qss both turn on a QUALIFYING PERSON, so the dependent scaffolding is the one thing
        # their coverage waits on (the separate-return scaffolding shipped with mfs).
        out.append(f"filing statuses other than {covered} ({'/'.join(pending)}) — each needs a "
                   f"qualifying person, and the dependent scaffolding is not finished")
    out += [f"{mapper.FACT_GROUP_LABELS[g]} — {_stream_reason(g)}"
            for g in mapper.UNSUPPORTED_STREAMS]
    out += [f"{mapper.FACT_GROUP_LABELS[g]} — not computed yet; refused rather than ignored"
            for g in mapper.UNSUPPORTED_FACT_GROUPS]
    # no dependents clause — nothing on that surface is refused any more (the constant
    # that stood here was retired with its last tier).
    out.append(mapper.MULTIPLE_EMPLOYERS_REFUSAL)
    out.append(mapper.age65_ambiguity_refusal(tax_year))
    out.append(mapper.dependent_day_ambiguity_refusal(tax_year))
    out += list(DECLARED_EXCLUSIONS)
    return out


def _stream_reason(group: str) -> str:
    """The per-stream sentence, split three ways on the DAG rather than asserted flat.

    The old single sentence — "not carried into the return yet" — was MEASURED FALSE at the pin
    for every refused stream: their writables reach the served lines; what is missing is this
    service's mapping. A refusal that misstates its own cause is worse than a bare one, so the
    artifact decides which of two true sentences each stream gets. The covered set does not move
    here: reachable is not mapped (`COVERED_FACT_GROUPS` is a mapper that exists, nothing else).
    """
    from . import reachability
    try:
        reachable = reachability.group_reaches(group)
    except reachability.ReachabilityUnknown:
        # A stream refused before the artifact learned its group (mid-development, or a fact
        # group with no engine collection behind it). Saying nothing about reachability is
        # honest; guessing either sentence is not.
        return "refused; the pinned dictionary carries no derived reachability for it yet"
    if reachable:
        return ("reachable at the pin; the service's mapping is not built. Refused rather than "
                "counted short")
    return "not carried into the return at the pin"


_KNOCKOUTS_ARTIFACT: dict | None = None


def _knockouts_artifact() -> dict:
    """`generated/knockouts.json`: every knockout fact in the pinned dictionary with the
    words a person reads for it, derived from the XML with NO engine and byte-checked at the pin
    (gate step 4). Cached; an absent artifact is an empty map, and the drift gate — not this
    loader — is what makes that loud."""
    global _KNOCKOUTS_ARTIFACT
    if _KNOCKOUTS_ARTIFACT is None:
        path = data_root() / "generated" / "knockouts.json"
        _KNOCKOUTS_ARTIFACT = (json.loads(path.read_text(encoding="utf-8")) if path.exists()
                               else {"pin": {}, "knockouts": {}})
    return _KNOCKOUTS_ARTIFACT


def knockout_words(path: str) -> str:
    """the words a person reads for a knockout. Collection items are looked up by shape
    (`/familyAndHousehold/#<id>/…` -> `/familyAndHousehold/*/…`); a path the artifact does not
    know — a pin bump that landed without regenerating — falls back to the path itself. ONE
    loader: `operations.knockouts_from` reads a refusal's words here, and `knockouts()` below
    serves the same table, so the two cannot disagree."""
    table = _knockouts_artifact()["knockouts"]
    shape = re.sub(r"/#[0-9a-f-]+/", "/*/", path)
    entry = table.get(shape) or table.get(path)
    return (entry or {}).get("words") or path


def knockout_aggregate() -> dict:
    """`/flowIsKnockedOut`'s members with the value that fires each and the words a person
    reads — the dictionary's own submission flag, read by `knockouts_from` beside its word-keyed
    scan so a knockout named without the word is never served as complete."""
    return _knockouts_artifact().get("aggregate") or {"path": "/flowIsKnockedOut", "members": []}


def knockouts_pin() -> str:
    """The dictionary hash the knockouts artifact was derived from — served so a caller
    can see it agrees with the envelope's `dictionary_hash`."""
    return _knockouts_artifact()["pin"].get("dictionary_sha256", "")


def knockouts() -> list:
    """Every knockout fact in the pinned dictionary, with its module and the words a person
    reads for it — from the pin-checked artifact, ordered by path, no engine forked. This once
    returned `[]` with the reason that reading the dictionary would mean forking the JVM; the
    artifact retired that reason (the sentence is gone, not softened)."""
    return [{"path": path, "module": entry["module"], "words": entry["words"]}
            for path, entry in sorted(_knockouts_artifact()["knockouts"].items())]


def assumptions() -> list:
    """What the mapper decides about a taxpayer without asking — derived from the mapper itself.

    A different thing from `exclusions()`, and the difference matters to whoever reads the answer.
    An exclusion is something this service REFUSES to compute, so the caller knows to go elsewhere.
    An assumption is something it computed anyway, resting on a claim about the taxpayer that nobody
    supplied and that no field in the fact schema lets them contradict — no estimated payments made,
    no Marketplace health plan, no digital assets received. Being silent about those is what turns a
    confident, cited, complete answer into a wrong one.

    Derived, never hand-kept: adding an assumption to the mapper publishes it here in
    the same commit.
    """
    return mapper.assumptions()


def unasked_boundary() -> list:
    """What this service CANNOT ask for and cannot compute — derived from the refusal boundary.

    The design's sharpest hazard: the cloud only asks for what it supports, so a taxpayer with
    interest income yields a wages-only fact set, nothing refuses, and `complete` is a wrong number.
    A complete return silent about this is worse than a refusal.

    It is the same set as the published exclusions, said in the shape a RESPONSE needs — one entry
    per fact class, machine-readable — rather than as prose for a coverage page. Derived from
    `mapper` so it cannot drift from what the service actually refuses: a stream promoted to covered
    disappears from here in the same commit that promotes it.
    """
    out = [{"fact_class": mapper.FACT_GROUP_LABELS[group],
            "why_not_supported": f"{_stream_reason(group)}; a request containing it is refused "
                                 f"rather than ignored"}
           for group in mapper.UNSUPPORTED_STREAMS]
    out += [{"fact_class": mapper.FACT_GROUP_LABELS[group],
             "why_not_supported": "accepted by the fact schema but mapped nowhere; refused rather "
                                  "than dropped silently"}
            for group in mapper.UNSUPPORTED_FACT_GROUPS]
    return out
