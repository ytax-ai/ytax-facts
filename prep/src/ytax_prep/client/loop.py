# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The bounded gap loop — the client-side controller that drives the conversation.

The cloud is stateless: it remembers nothing between requests, so the client resends the COMPLETE
fact set every round and the cloud replies with what is still missing. Statelessness is what lets the
service hold no case data at all, which is what the privacy claim rests on. The cost is
paid here, in the client: the loop owns the case, applies each answer, and decides when to stop.

WHY IT MUST BE BOUNDED, and why the bound is not "until the gaps run out". The fact set grows
monotonically but the GAP set need not — answering "yes, I have a 1095-A" instantiates roughly thirty
new writables, so a rule like "stop when the gaps stop shrinking" would abort a loop that is
progressing perfectly. The loop therefore terminates on things it can observe about ITSELF: a
terminal outcome, an answerer with nothing to add, or the pass limit.

Two budgets, not one. `error` means transient — a crash, a timeout, a full queue — and the spec's
outcome table says retry. Spending a gap pass on one would let a single flaky JVM exhaust the budget
of a return that had nothing wrong with it. An error response also carries no trustworthy content,
only a trustworthy shape, so the loop never reads `gaps[]` out of one: questions manufactured by a
crashed process are worse than no questions.

NOT VERIFIED HERE, because it does not exist yet: response signing. There is none service-side. When
it lands, it belongs in `_accept` — before the outcome is believed and before identity is merged onto
the result — because a tampered `complete` is precisely the response the local merge would paste a
real name and SSN onto.

No tax knowledge lives here. The loop decides WHEN to ask, never what an answer means.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

from .merge import merge_identity
from .payload import project_case

# The five outcomes of the design's response contract. A sixth one arriving means the contract moved,
# which is a thing to stop on, not to guess at.
OUTCOMES = frozenset({"complete", "incomplete", "knocked_out", "refused", "error"})
TERMINAL = frozenset({"complete", "knocked_out", "refused"})

_TOKEN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?$")


class LoopRefused(ValueError):
    """The loop stopped rather than guess. Raised, never returned as an outcome."""


@dataclass
class GapLoopResult:
    """What the loop produces. `outcome` is the service's; `stopped_because` is the loop's own —
    keeping them separate is what stops "ran out of budget" from ever reading as "finished"."""
    outcome: str
    stopped_because: str
    passes: int
    errors: int
    case: dict                                  # the grown case, for the caller to persist
    response: dict
    gaps: list = field(default_factory=list)
    unasked_boundary: list = field(default_factory=list)
    forms: list = field(default_factory=list)
    # The preparer's submit-time decision about the assumptions: whatever the acknowledger returned
    # ("reviewed", "declined", a timestamp, a user id). None means it was never asked, which only
    # happens when nothing rendered.
    acknowledgement: object = None
    assumptions: list = field(default_factory=list)


def _accept(response: dict, tax_year: int) -> str:
    """Check the envelope, return the outcome. The checks performable TODAY, no more.

    An `error` is checked for SHAPE only. The spec is explicit that its content cannot be trusted,
    and content-checking it would let a crashed process fail a run that a retry would have
    completed."""
    outcome = response.get("outcome")
    if outcome not in OUTCOMES:
        raise LoopRefused(
            f"the service returned outcome {outcome!r}, which is not one of {sorted(OUTCOMES)}. "
            f"An unrecognised outcome means the contract moved — refusing rather than defaulting, "
            f"because every default here is a guess about somebody's return.")
    if outcome == "error":
        return outcome
    echoed = (response.get("versions") or {}).get("tax_year")
    if echoed != tax_year:
        raise LoopRefused(
            f"the response was computed for tax year {echoed!r}, not the {tax_year!r} requested. A "
            f"return computed against the wrong year's law is wrong in a way no field-level check "
            f"catches.")
    return outcome


def _set_fact(case: dict, path: str, value, overwrite: bool = False) -> None:
    """Apply one answer at its dotted/indexed path — `w2s[0].withholding_cents`.

    `overwrite` is False for the loop, whose rounds must be monotonic, and True for a case REVISION,
    where correcting an answer is the whole point (`client/case.py`). One grammar, two policies,
    both stated rather than one of them implied.

    A fact set is NESTED, and a setter that only walks the top level is the exact bug the payload
    projector shipped with: the top level looked clean and the collection item was wrong. So this
    walks the real shape.

    Two refusals, both about keeping the request sequence monotonic. Writing past the next free slot
    would punch holes in a collection, and a hole is a person the return computes as if they were not
    there. Overwriting a value already sent makes the outcome depend on which pass you look at —
    correcting a wrong entry is a NEW case, not a loop round.

    ASSUMPTION, stated because it will be settled elsewhere: "already answered" is `is not None`, so
    a leaf explicitly stored as `None` reads as absent and would be overwritten silently. No fact
    schema property is null-typed today (checked), so a case cannot legitimately carry one. Work item
    0b — inverting the mapper's silent defaults into explicit absence — is where absence gets a real
    representation, and this check follows it rather than inventing one first."""
    tokens = []
    for part in path.split("."):
        m = _TOKEN.match(part)
        if not m:
            raise LoopRefused(f"the service named a gap at {path!r}, which is not a fact path this "
                              f"client can resolve — refusing rather than writing it somewhere.")
        tokens.append((m.group(1), None if m.group(2) is None else int(m.group(2))))

    node = case
    for i, (name, index) in enumerate(tokens):
        last = i == len(tokens) - 1
        if index is None:
            if last:
                if node.get(name) is not None and not overwrite:
                    raise LoopRefused(
                        f"refusing to overwrite {path!r}, which already carries a value. The loop "
                        f"fills gaps; it does not revise answers. A correction is a new case.")
                node[name] = value
                return
            node = node.setdefault(name, {})
            if not isinstance(node, dict):
                raise LoopRefused(f"{path!r} descends into {name!r}, which is not an object")
        else:
            container = node.setdefault(name, [])
            if not isinstance(container, list):
                raise LoopRefused(f"{path!r} indexes {name!r}, which is not a collection")
            if index > len(container):
                raise LoopRefused(
                    f"refusing {path!r}: {name}[{index}] is beyond the next free slot "
                    f"({name} holds {len(container)}). Filling it would leave the entries between "
                    f"them empty, and an empty entry is an entity the return computes as absent.")
            if last:
                raise LoopRefused(
                    f"refusing {path!r}: a gap names a FACT, not a whole collection item. Accepting "
                    f"an object here would import unclassified fields straight past the projection.")
            if index == len(container):
                container.append({})
            node = container[index]


def run_gap_loop(case: dict, send, answer, acknowledge, *, identity: dict | None = None,
                 unconfirmed: dict | None = None,
                 max_passes: int = 6, max_errors: int = 3):
    """Drive the case to a terminal state, or stop and say why.

    `send(payload) -> response` is the service call; `answer(gaps) -> {path: value}` is whoever can
    supply missing facts — a preparer at a screen, or a stub. Both are injected because this unit is
    buildable before `prepare_return` exists and must not wait for it.

    `acknowledge(assumptions) -> decision` is the SUBMIT-TIME gate (decided 2026-08-11):
    at the moment a complete calculation becomes a rendered return, the preparer is shown what the
    service assumed about this taxpayer and asked whether they want to review it. The gate is on the
    ASKING — "declined" is a valid decision and still renders; a decision of `None` refuses. It is a
    REQUIRED parameter, deliberately: an optional one with a permissive default is the silent render
    this exists to close. **Policy switch, if it is ever wanted:** to make declining BLOCK the
    return, reject any decision but "reviewed" in `_finish` — one condition, one place.

    `identity` is the `{term: value}` mapping the taxpayer's own identity file yields
    (`identity_file.read`, or `CaseFile.confirmed_identity`), in the form's terms —
    `primary.first_name`, `address.city`. `unconfirmed` names anything read off a document that
    nobody has checked yet; the merge refuses those rather than printing them.

    It is optional only because a run that renders no forms needs none. **There is no fallback to
    reading identity from the case**: identity cannot live in the facts half at all — `project_case`
    refuses it, which is the same control the wire uses — so that branch could only ever return
    nothing, and it failed with a message about a missing VALUE when the truth was a missing
    ARGUMENT. Identity reaches the render from the file the person manages, and from nowhere else.

    The caller's case is never mutated: the grown copy comes back on the result, so a caller who
    abandons a loop is left with exactly what they started with."""
    current = copy.deepcopy(case)
    tax_year = current.get("tax_year")
    passes = errors = 0
    response: dict = {}

    while True:
        # Re-projected EVERY round, deliberately. A newly answered fact has never been linted, and
        # the client's own refusal is the control that must see it before it can leave the machine.
        payload, _overlay = project_case(current)
        response = send(payload)
        outcome = _accept(response, tax_year)

        if outcome == "error":
            errors += 1
            if errors >= max_errors:
                return GapLoopResult(outcome="error", stopped_because="error_budget",
                                     passes=passes, errors=errors, case=current, response=response)
            continue

        passes += 1
        if outcome in TERMINAL:
            return _finish(outcome, "terminal_outcome", passes, errors, current, response,
                           acknowledge, identity=identity, unconfirmed=unconfirmed)

        if passes >= max_passes:
            # Terminal for the LOOP, not for the return: the outcome stays `incomplete`, because a
            # loop that ran out of budget has not produced anything.
            return _finish(outcome, "pass_limit", passes, errors, current, response)

        answers = answer(response.get("gaps") or []) or {}
        if not answers:
            # Asking the same question again cannot produce a different answer.
            return _finish(outcome, "no_progress", passes, errors, current, response)

        for path in sorted(answers):
            _set_fact(current, path, answers[path])


def _finish(outcome, stopped_because, passes, errors, case, response,
            acknowledge=None, identity=None, unconfirmed=None) -> GapLoopResult:
    """Assemble the result. Two things are lifted out of the response body deliberately.

    `unasked_boundary` becomes a first-class field because it is the design's sharpest hazard: the
    cloud only asks for what it supports, so a taxpayer with interest income yields a wages-only fact
    set, nothing refuses, and `complete` is a wrong number. The loop cannot know whether this
    taxpayer HAS un-askable income — so it surfaces the list rather than deciding for them.

    Forms are merged with local identity only on `complete`. An `incomplete` renders nothing, so a
    half-answered return cannot be mistaken for a draft."""
    forms, decision = [], None
    assumptions = response.get("assumptions") or []
    if outcome == "complete":
        # SUBMIT TIME, and only here. An `incomplete` renders nothing, and prompting on a pass that
        # produces no return teaches a preparer to dismiss the prompt — which destroys the gate on
        # the pass that matters. A refusal never reaches this branch either: nothing was computed,
        # so nothing was assumed.
        decision = acknowledge(assumptions)
        if decision is None:
            raise LoopRefused(
                "the return was not rendered: the submit-time acknowledgement returned no decision. "
                "A preparer may decline to review the assumptions, but the return may not render "
                "without them having been asked — that silence is the whole thing this gate closes.")
        wants_identity = any(f.get("identity_fields") for f in (response.get("forms") or []))
        if identity is None and wants_identity:
            # No fallback. It used to read identity out of the CASE, which no saveable case can
            # carry — `project_case` refuses identity in the facts half, so that branch yielded {}
            # and the merge then refused with "no local value for 'primary.ssn'", pointing a caller
            # at the identity file when the truth was that nothing had been passed at all.
            raise LoopRefused(
                "the response asks for identity fields, and no identity was supplied to the loop. "
                "It comes from the identity file the person manages, and from nowhere else — pass "
                "`identity=` (and `unconfirmed=` for anything not yet checked). Refusing rather "
                "than rendering a return with holes where a name and TIN belong.")
        forms = merge_identity(response.get("forms") or [], identity or {}, unconfirmed=unconfirmed)
    return GapLoopResult(
        outcome=outcome, stopped_because=stopped_because, passes=passes, errors=errors,
        case=case, response=response,
        gaps=response.get("gaps") or [],
        unasked_boundary=response.get("unasked_boundary") or [],
        forms=forms, acknowledgement=decision, assumptions=assumptions)
