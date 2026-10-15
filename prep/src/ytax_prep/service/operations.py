# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The five operations over the pinned engine (Phase 0, stateless).

Each compute op: derivative facts -> engine facts (mapper) -> adapter.resolve -> extract cited lines
-> response envelope. World #1: compute and cite; never advise. estimate_2026 is refusal-only
(YEAR_NOT_ANNOUNCED) until ty2026 lands. coverage needs no engine.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
from pathlib import Path
from decimal import Decimal, InvalidOperation

from ..engine import EngineAdapter, EngineNotAvailable
from ..engine.mode import default_engine
from ..engine.adapter import PINNED_DESCRIBE, dictionary_sha256, discover_pin
from ..facts import FactsSchemaError, ServiceFactsError, map_to_engine
from ..facts.extras import map_with_extras
from ..facts import mapper
from ..facts.mapper import assumptions_for as _assumptions_for
from .gaps import assumed_absent_details as _assumed_absent_details
from .gaps import gaps_for as _gaps_for
from . import coverage as _coverage
from .lines import F1040, LINE_MAP


# The tax years the request schema admits (schema/common/compute-request.schema.json `tax_year`
# enum). Kept here rather than read at runtime because the deployed container ships `src/` and
# `generated/` only, not `schema/`; `test_coverage_derivation.py` asserts this tuple equals the
# schema's enum, so the two cannot drift.
TAX_YEARS = (2024, 2025, 2026)

# what a caller is told when the engine cannot be reached or fails. STATIC — no path, no
# stderr, no exception text; the diagnostic goes in OperationError.detail, which is never served and
# never logged. Carried under ENGINE_UNAVAILABLE (HTTP 503), NOT OUT_OF_COVERAGE: EngineNotAvailable
# is raised for a non-zero JVM exit, a missing emitted TSV, and the 300s subprocess timeout — none of
# which say anything about whether the return is in scope. Telling a preparer their return is
# permanently unsupported because a JVM fell over is a wrong answer, not a conservative one.
ENGINE_UNAVAILABLE_MESSAGE = "the calculation engine is unavailable"


class OperationError(Exception):
    """A structured operation error: carries a code from the operations' error vocabulary."""

    # `message` is SERVED. `detail` is not — it holds internal diagnostics (engine stderr, paths,
    # exception text) that must never reach a caller or a log line. Keeping them in separate fields
    # makes the safe thing the default: `as_error()` cannot leak what it never reads.
    def __init__(self, code: str, message: str, field_path: str | None = None,
                 detail: str | None = None):
        super().__init__(message)
        self.code, self.message, self.field_path = code, message, field_path
        self.detail = detail

    def as_error(self) -> dict:
        e = {"code": self.code, "message": self.message}
        if self.field_path:
            e["field_path"] = self.field_path
        return e


def _cents_from_dollar(value: str) -> int:
    """'52000.00' / '-12.34' -> integer cents, exact (Decimal, no float). Rounds half-up if the
    engine ever emits more than 2 fractional digits (it emits 2 today), never silently truncating."""
    from decimal import ROUND_HALF_UP, Decimal
    return int((Decimal(value) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


# The dictionary marks returns that COMPUTE but MUST NOT BE FILED — /knockoutFormW2s
# and the /flowKnockout* family (56 of them). At the previous pin nothing derived the W-2 one, so
# this state was unreachable and `"KNOCKOUT": 200` sat in the REST status map with nothing anywhere
# emitting it. At the pin it is wired into the excess-OASDI chain, so a knocked-out return
# would otherwise be served as an ordinary 200 result with a clean number on it.

# Only Complete/true counts. A Placeholder is a stand-in that resolved, not a test the taxpayer
# tripped — emitting one would tell a preparer their return cannot be filed on the strength of a
# default value.
# The post-resolve eligibility gate (hoh/qss coverage).
# Scoped to the two statuses whose eligibility turns on ASKED answers the engine tests
# (qualifying person, home upkeep, the spouse-death pair); single/mfj/mfs eligibility is
# consistent by construction — the scaffold derives maritalStatus FROM the declared status.
# Measured at the pin: the engine computes the DECLARED status's numbers even when its own
# eligibility answer is false, so without this gate a non-qualifying filer would be served a
# head-of-household return that looks complete. Raised as OUT_OF_COVERAGE so both compute
# paths give the refusal treatment every other boundary gets; gaps stay [] deliberately — a
# refusal is not a request for more data, and the remedy is a different status.
_STATUS_ELIGIBILITY = {"hoh": ("/eligibleForHoh", "head of household"),
                       "qss": ("/eligibleForQss", "qualifying surviving spouse")}


# A post-resolve gate once stood here for the capital-guaranteed-payment NIIT knockout, which
# could not fire because /agi resolved Placeholder. The cause was found on OUR side — the
# scaffold omitted build's two-filer and empty-collection conventions — and with /agi Complete the
# dictionary's own /knockoutK1CapitalGuaranteedPaymentsNiit fires (measured; the K1 gate tests
# pin it). The gate retired the day it became redundant, as its comment promised.


def _require_declared_status_eligible(facts: dict, resolved: dict) -> None:
    gate = _STATUS_ELIGIBILITY.get(facts.get("filing_status"))
    if gate is None:
        return
    path, words = gate
    row = resolved.get(path)          # (status, type, value) tuples from _parse_resolved
    value = row[2] if row else None
    if value == "true":
        return
    if value == "false":
        raise OperationError(
            "OUT_OF_COVERAGE",
            f"the answers on this return do not establish {words} — the engine's own "
            f"eligibility answer ({path}) came back false. The figures a {words} return "
            f"would show are not this filer's; a different filing status is the remedy, "
            f"not more data.")
    # Unresolved: defensive — the gaps and the mapper backstop ask every input this gate
    # reads, so an unresolved answer here means a pin moved the eligibility chain. Stated
    # rather than crashed, and stated as OURS to fix.
    raise OperationError(
        "OUT_OF_COVERAGE",
        f"the {words} eligibility answer ({path}) did not resolve — every question this "
        f"service asks was answered, so the pinned eligibility chain has moved; this is a "
        f"service defect to report, not a data problem.")


# The credit-history answers (Form 8862's questions) are asked on every return. Measured at
# the pin, a yes on a return with a credit in play makes the engine leave that credit UNRESOLVED —
# the Form 8862 chain wants the notice year, whether the ban expired, whether the credit was
# claimed since — and the credit line resolves as a Placeholder 0 that `_cited_lines` keeps: an
# earned income credit silently gone from a return served `complete`. What is read is the
# engine's own eligibility answer for each credit — `/eitcQualified`, `/ctcQualified` —
# present (any value) on all 60 fixtures at baseline and on
# every return with no credit in play whatever the answer, ABSENT exactly when a yes opened a
# chain the engine could not finish (measured). Not `/creditsSectionComplete`: it is unresolved at
# baseline on a claimed-dependent filer and Placeholder on the claimed-spouse joint return, so a
# rule on it refused a yes for a reason the answer did not cause. Not `/eitcQcTest` either: a
# qualifying-child yes leaves it absent on a childless filer above the EITC limit while nothing
# served moves.
_CREDIT_ELIGIBILITY_FACTS = ("/eitcQualified", "/ctcQualified")
# Each yes names what it means and which follow-up questions the dictionary asks next — measured
# per field, because the three chains differ (a refusal that misstates its own cause is
# worse than a bare one). The two disallowance answers open Form 8862's notice questions; the
# qualifying-child answer opens the dictionary's questions about the OTHER taxpayer.
_CREDIT_HISTORY_WORDS = {
    "eitc_reduced_or_disallowed": (
        "an earned income credit reduced or disallowed in a prior year",
        "Form 8862's further questions — the notice year, whether the ban has expired, whether "
        "the credit was claimed since"),
    "ctc_odc_reduced_or_disallowed": (
        "a child tax credit, additional child tax credit or credit for other dependents reduced "
        "or disallowed in a prior year",
        "Form 8862's further questions — the notice year, whether the ban has expired, whether "
        "the credit was claimed since"),
    "qualifying_child_of_another": (
        "being claimable as another taxpayer's qualifying child",
        "Form 8862 line 4's follow-up questions — whether that other taxpayer is required to "
        "file, is filing, and files only for a refund"),
}


def _require_credit_history_resolved(facts: dict, resolved: dict) -> None:
    yeses = [f for f in mapper.CREDIT_HISTORY_FIELDS if facts.get(f) is True]
    if not yeses:
        return
    unresolved = [p for p in _CREDIT_ELIGIBILITY_FACTS if p not in resolved]
    if not unresolved:
        return
    named = "; ".join(f"{f} (yes: {_CREDIT_HISTORY_WORDS[f][0]})" for f in yeses)
    wants = "; ".join(sorted({_CREDIT_HISTORY_WORDS[f][1] for f in yeses}))
    raise OperationError(
        "OUT_OF_COVERAGE",
        f"{named} — with a credit in play, that answer opens {wants} — questions this service "
        f"does not carry, so the engine left the credit's eligibility ({', '.join(unresolved)}) "
        f"unresolved rather than computing it. Refused rather than served with the credit "
        f"dropped to a placeholder zero.")


# `care_expense_question_reached` mirrors the dictionary's AGE arm of the qualifying-person
# test on what the service sends; the CLAIM arm (`isClaimedIfClaimable`, `isClaimedDependent`)
# is the engine's own reading of the whole return — measured: a married child filing jointly
# (`wages-and-married-child-joint-single`) passes the age arm and is not claimed, and the
# dictionary computes the credit with that child's expenses silently dropped. So after resolve
# the row's own `cdccQualifyingPerson` is read back for every person with expenses, and a row
# the engine does not treat as a qualifying person is refused rather than served as a zero.
def _require_care_expenses_on_qualifying_persons(facts: dict, resolved: dict) -> None:
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict):
            continue
        amount = person.get(mapper.CARE_EXPENSES_FIELD)
        if not (isinstance(amount, int) and not isinstance(amount, bool) and amount > 0):
            continue
        if person.get("role") == "dependent":
            path = f"/familyAndHousehold/#{mapper._uuid('2', i + 1)}/cdccQualifyingPerson"
        else:
            path = f"/filers/#{mapper._uuid('1', i + 1)}/cdccQualifyingPerson"
        row = resolved.get(path)
        if row and row[0] == "Complete" and row[2] == "true":
            continue
        raise OperationError(
            "OUT_OF_COVERAGE",
            f"persons[{i}].{mapper.CARE_EXPENSES_FIELD} is answered on a person the engine does "
            f"not treat as a qualifying person for Form 2441 once the whole return is read — "
            f"the age test passes, but the return does not claim them (a married child filing "
            f"jointly, a child claimed by the other parent) — so the credit would be computed "
            f"with that amount silently dropped. Refused rather than served as a zero.")


# The mapper mirrors the dictionary's dependent-filer condition from the page-1 answers
# and refuses a Form 1095-A on that route before resolve; this reads the dictionary's OWN answer
# after resolve so a mirror that drifts from the pin cannot let the form be dropped in silence
# (measured: `hasPtcQualifyingPlan` switches to the never-sent dependent-filer chain, the
# return closes complete with the advance payments neither repaid nor reconciled).
def _require_ptc_not_on_dependent_filer_route(facts: dict, resolved: dict) -> None:
    if not (facts.get(mapper.PTC_GROUP) or []):
        return
    row = resolved.get("/notMfjAndPrimaryFilerCouldBeDependentAndClaimerIsRequiredToFileOrFilingForCredits")
    if row and row[0] == "Complete" and row[2] == "true":
        raise OperationError(
            "OUT_OF_COVERAGE",
            f"{mapper.PTC_GROUP} is entered on a return the engine reads as a claimable "
            f"dependent's (the claimer must file, or filed for more than a refund) — Form 8962 "
            f"for a dependent filer asks questions not carried here, and the return would be "
            f"served with the form dropped and the advance payments neither repaid nor "
            f"reconciled. Refused rather than served without it.")


# `_cited_lines` OMITS a served line whose fact the engine left unresolved — honest in
# itself (never a fabricated 0) — but until this gate the OUTCOME still said `complete`: a
# stepchild, foster child or grandchild dependent row was served as a finished return with lines
# 24, 33 and 34 simply missing (the non-parental arm's first question is never asked). A
# shorter form is not a return; an unresolved served line is this service's boundary, named.
def _require_every_served_line_resolved(resolved: dict) -> None:
    """Every `LINE_MAP` fact the renderer would keep must be present after resolve; the
    complement of `_cited_lines`' keep-set is refused BY NAME, so nothing can be omitted silently
    again. Placeholder rows are kept (the renderer keeps them — a separate question, measured
    on every fixture: none serves one today)."""
    missing = [(spec["line_id"], spec["fact_path"]) for spec in LINE_MAP
               if (resolved.get(spec["fact_path"]) or ("Absent",))[0]
               not in ("Complete", "Placeholder")]
    if not missing:
        return
    named = "; ".join(f"line {line} ({path})" for line, path in missing)
    raise OperationError(
        "OUT_OF_COVERAGE",
        f"the engine did not resolve {len(missing)} served line(s) on this return — {named} — "
        f"every question this service asks was answered, so the pinned chain waits on an "
        f"answer this service does not ask for this household. Refused rather than served with "
        f"the line(s) missing; this is a service boundary to report, not a data problem.")



def _require_typed_lines_took_effect(resolved: dict) -> None:
    """The typed lines, held to the fallback's own acceptance test — never complete
    but wrong. A served line that resolves only as a PLACEHOLDER beside typed lines means the
    engine is still waiting on something that form needs and computed the return WITHOUT it.
    Measured on the pinned engine: 8,420.00 typed on Form 8863 line 10 left line 24 at the uncredited
    4,115.00, a Placeholder, served `complete` — the form wanted its Part III student rows present
    (now sent, `fallback_topics` companions). With no typed lines a Placeholder is kept as before
    (measured on every fixture: none serves one)."""
    stand_ins = [spec["line_id"] for spec in LINE_MAP
                 if (resolved.get(spec["fact_path"]) or ("Absent",))[0] == "Placeholder"]
    if not stand_ins:
        return
    raise OperationError(
        "OUT_OF_COVERAGE",
        f"the lines typed in for a form this version does not read were not all used: Form 1040 "
        f"line(s) {', '.join(stand_ins)} resolved only as a stand-in, so the engine is still "
        f"waiting on something that form needs. Refused rather than served as if the typed lines "
        f"had counted. The figures here are not your return.")


# the Form 8995-A scaffold's own boundary. Above the section 199A threshold the deduction
# is figured on Form 8995-A, and this service sends `/qualifiedBusinesses` EMPTY — there is no
# per-business intake in the schema (W-2 wages paid by the business, unadjusted basis of its
# property, its SSTB status). Measured at the pin: with an empty collection Form 8995-A line 27
# (the qualified business income component) is 0, so a Schedule C profit's own share of the
# deduction is DROPPED — 39,464 of `/qbiAutoDerivedAmount` earned nothing, in the phase-in range
# and above the upper threshold alike. Serving that is a computed Form 1040 line 15 with a
# component the law allows silently missing, which is a wrong number, so the return is refused
# instead — the mfs Form 8958 precedent, and gaps stay [] because the remedy is an intake this
# service does not have rather than an answer the caller can supply.

# THE TRIGGER IS THE ENGINE'S OWN ANSWERS, never a recomputation here: `/isAboveQbiThreshold`
# already carries the per-status threshold (2025: 197,300 single / 394,600 mfj), and
# `/qbiAutoDerivedAmount` is the Schedule C amount Part II would have to limit. The third came
# later: once a K-1's section 199A statement puts members in `/qualifiedBusinesses`, the
# Schedule C amount moves INTO the members' sum and `/qbiAutoDerivedAmount` no longer reaches the
# deduction — so `/qbiSimplifiedAmount` (Form 8995 line 4 before its floor, the members' sum) is
# read beside it. Measured on the pinned engine: 400,000.00 of K-1 statement income above the
# threshold served line 13 = 0.00 with `/qbiAutoDerivedAmount` at 0.00 — this guard's blind spot
# before the third answer.

# WHAT IS DELIBERATELY NOT A TRIGGER, each measured rather than reasoned:
#   * a RENTAL — its net income never reaches `/qbiAutoDerivedAmount` (0.00 below the threshold,
#     in the phase-in range and above the upper one). In this dictionary a rental is a section
#     199A trade or business only through an ENTERED `/qualifiedBusinesses` item, so it earns no
#     deduction either side of the threshold and this scaffold drops nothing for it;
#   * a Schedule C LOSS — `/qbiAutoDerivedAmount` has a GreaterOf $0 floor, so there is no
#     positive component for Part II to limit and nothing is dropped;
#   * anything BELOW the threshold — Form 8995 (the simplified form) takes the auto-derived
#     amount in full there, measured unchanged by this scaffold;
#   * the qualified REIT dividend / publicly traded partnership half — Form 8995-A lines 28-32
#     take no per-business detail, which is the whole reason the scaffold computes at all.
_QBI_PART_II_REFUSAL = (
    "this return has qualified business income from a business on Schedule C or a Schedule "
    "K-1 and taxable income above the section 199A threshold. Above that threshold each business's deduction "
    "is figured on Form 8995-A, Part II, which limits it by the W-2 wages that business paid "
    "and the unadjusted basis of the property it holds — neither amount is in the covered set, "
    "so the business's part of the deduction cannot be figured. The figures here are not your "
    "return.")


_QBI_GATE_UNRESOLVED = (
    "whether this return needs Form 8995-A, Part II could not be established — the section "
    "199A threshold answer did not resolve. This is a service defect to report, not a data "
    "problem, and the figures are withheld rather than served unchecked.")


def _require_qbi_part_ii_not_needed(resolved: dict) -> None:
    above = resolved.get("/isAboveQbiThreshold")
    auto = resolved.get("/qbiAutoDerivedAmount")
    members = resolved.get("/qbiSimplifiedAmount")
    # Defensive, and stated as OURS: both facts are complete-safe in the pinned dictionary and
    # resolve Complete on every committed fixture, so a missing or non-Complete one means the
    # pin moved the section 199A chain under a scaffold that keeps claiming Form 8995-A.
    # UNRESOLVED REFUSES rather than passes — the same direction the gate itself takes, because
    # the thing that cannot be checked is whether a served line is missing a component.
    if any(v is None or v[0] != "Complete" for v in (above, auto, members)):
        raise OperationError("OUT_OF_COVERAGE", _QBI_GATE_UNRESOLVED)
    if above[2] != "true":
        return
    try:
        amounts = [Decimal(auto[2]), Decimal(members[2])]
    except (InvalidOperation, TypeError):
        raise OperationError("OUT_OF_COVERAGE", _QBI_GATE_UNRESOLVED)
    if max(amounts) > 0:
        raise OperationError("OUT_OF_COVERAGE", _QBI_PART_II_REFUSAL)


# the knockout words live in `coverage` now — one loader for the refusal's words and the
# served coverage list. Re-exported here so `knockouts_from` reads the same function.
from .coverage import knockout_words  # noqa: E402
import re as _re  # noqa: E402

# a "knockout"-named detail fact served only when the member it feeds fires.
_VISIBILITY_ONLY_UNLESS = {
    "/filers/*/causesHsaContributionsOverLimitKnockout": "/flowHsaContributionsOverLimitKnockout",
    # part-year coverage and the `both` type compute once the twelve-month vector governs
    # (`/flowKnockoutHdhpCoverageNotAllYear` and `/flowKnockoutHsaSelfAndFamilyCoverage` are gated
    # on Not(/hsaLine3VectorGoverns) at the pin); the per-filer detail stays true on the answer.
    "/filers/*/hsaHdhpCoverageStatusKnockout": "/flowKnockoutHdhpCoverageNotAllYear",
    "/filers/*/typeOfHdhpKnockout": "/flowKnockoutHsaSelfAndFamilyCoverage",
    # Medicare for part of the year computes once the Medicare vector governs
    "/filers/*/enrolledInMedicarePartOfYearKnockout": "/flowKnockoutHsaCoverageChanging",
    # the separate return's line 6 check computes once the spouse's vector is answered
    # (`/flowKnockoutMFSLine6Check` is gated on Not(/hsaLine3VectorGoverns) at the pin).
    "/filers/*/causesHsaMfsLine6Knockout": "/flowKnockoutMFSLine6Check",
    # Medicare all year computes once the Medicare vector governs (line 3 = 0, the excess charged)
    "/filers/*/enrolledInMedicareAllYearKnockout": "/flowKnockoutEnrolledInMedicareAllYear",
}

# a root knockout served from the item's own cause where the root resolves a Placeholder.
# `/knockoutForForm1099RBox9aPercentage` is Count(All(cause, Not(box9aEntryConsistent))) > 0, and
# the frontier's consistency fact is a Placeholder on a Form 1099-R whose Form 4972 Part III is not
# computed (measured at the pin on a code-7 pension with box 9a 50.00: the cause Complete true, the
# root and `/flowIsKnockedOut` Placeholder true; each Complete on an IRA form).
# The unanswered divisor is a correct refusal, so the cause names it.
_PLACEHOLDER_ROOT_NAMED_BY_CAUSE = {
    "/form1099Rs/*/causesRetirementBox9aPercentageKO": "/knockoutForForm1099RBox9aPercentage",
}


def knockouts_from(resolved: dict) -> list:
    """Resolved facts -> KNOCKOUT refusals, in path order (stable output for a stable input).
    each carries `words`, the dictionary's own sentence for it, beside the path.

    the word-keyed scan below is the per-fact DETAIL; the dictionary's own submission flag
    `/flowIsKnockedOut` is the AUTHORITY. It is an Any over 102 members, 18 named without the
    word (`/notDigitalAssets`, `/hasForeignAccountsOrTrusts`, …), so when the aggregate is true
    the members that fired are read off the graph through the pin-checked member table
    (polarity-aware — a <Not>-wrapped member fires when FALSE) and named too; and if none can be
    named, the aggregate's own boundary is served. A knocked-out return is never `complete`."""
    # one detail fact is EXCLUDED unless the member it feeds fires —
    # `/filers/*/causesHsaContributionsOverLimitKnockout` is true for every over-limit HSA filer
    # and feeds the interview's summary table, while the member it once fed
    # (`/flowHsaContributionsOverLimitKnockout`) is false since the excess-income add-back
    # shipped (the dictionary's own words: "this fact only narrows what BLOCKS"); the return
    # computes that income (measured: 5,000 self-only → 700 of Schedule 1 line 8z). Every other
    # detail fact keeps refusing on its own (the household-employee and deemed-income
    # knockouts fire with the flag a Placeholder, measured at the pin).
    out = []
    for path in sorted(resolved):
        status, _type, value = resolved[path]
        if "nockout" in path and status == "Complete" and value == "true":
            member = _VISIBILITY_ONLY_UNLESS.get(_re.sub(r"#[0-9a-f-]+", "*", path))
            if member is not None:
                row = resolved.get(member)
                if not (row and row[0] == "Complete" and row[2] == "true"):
                    continue
            out.append({"code": "KNOCKOUT", "boundary": path,
                        "manifest_ref": "coverage#knockouts", "words": knockout_words(path)})
    named = {r["boundary"] for r in out}
    for path in sorted(resolved):
        root = _PLACEHOLDER_ROOT_NAMED_BY_CAUSE.get(_re.sub(r"#[0-9a-f-]+", "*", path))
        if root is None or root in named:
            continue
        row = resolved.get(root)
        if row and row[0] == "Complete":
            continue                     # the dictionary answered the root itself, either way
        status, _type, value = resolved[path]
        if status == "Complete" and value == "true":
            out.append({"code": "KNOCKOUT", "boundary": root,
                        "manifest_ref": "coverage#knockouts", "words": knockout_words(root)})
            named.add(root)
    flag = resolved.get("/flowIsKnockedOut")
    if flag and flag[0] == "Complete" and flag[2] == "true":
        named = {r["boundary"] for r in out}
        for member in _coverage.knockout_aggregate()["members"]:
            row = resolved.get(member["path"])
            if (row and row[0] == "Complete" and row[2] == member["fires_when"]
                    and member["path"] not in named):
                out.append({"code": "KNOCKOUT", "boundary": member["path"],
                            "manifest_ref": "coverage#knockouts",
                            "words": member["words"] or knockout_words(member["path"])})
                named.add(member["path"])
        if not out:
            out.append({"code": "KNOCKOUT", "boundary": "/flowIsKnockedOut",
                        "manifest_ref": "coverage#knockouts",
                        "words": ("The dictionary knocked this return out — it cannot be filed as "
                                  "computed — through a member this service cannot name at this "
                                  "pin. The figures here are not your return.")})
    return out


def _parse_resolved(tsv: str) -> dict:
    """path -> (status, type, value) for every resolved fact line."""
    out = {}
    for ln in tsv.splitlines():
        parts = ln.split("\t", 3)
        if len(parts) == 4:
            out[parts[0]] = (parts[1], parts[2], parts[3])
    return out


_HOH_QP_PATH = "/hohQualifyingPerson"

# Board decision 3. Publication 525's own instruction for a claim-of-right repayment over $3,000:
# "Figure your tax under both methods and compare the results. Use the method (deduction or credit)
# that results in less tax." That is arithmetic the statute states, not a preference. The service
# once resolved the return twice, forcing each method through the dictionary's method answer, and
# served the lower. The pinned dictionary does the comparison itself (IRC 1341(a): the year's tax
# IS the lesser of the two, not a filer choice): /electsClaimOfRightRepaymentDeduction reads the
# computed /claimOfRightDeductionGivesLesserTax, and the old method answer is deprecated and read
# by nothing — so the two resolves came back identical and the note named a method the engine had
# not used. One resolve now; the note reads the engine's own two legs and its own choice. Neither
# figure is a recommendation: both are this return, computed.
_REPAYMENT = "/writableOtherClaimOfRightRepaymentIncludedInEarlierYearIncome"
_COR_LEGS = ("/claimOfRightRepaymentExceedsThreshold", "/electsClaimOfRightRepaymentDeduction",
             "/taxWithClaimOfRightDeduction", "/taxWithoutClaimOfRightDeduction",
             "/claimOfRightRepaymentCreditSection1341")


def _money(cents: int) -> str:
    return f"{'-' if cents < 0 else ''}${abs(cents) // 100:,}.{abs(cents) % 100:02d}"


def _claim_of_right_statement(resolved: dict) -> str | None:
    """What the person is told when a claim-of-right repayment over $3,000 decides the tax: the
    tax each way, as the engine figured it, and which this return uses. None when no repayment
    reaches the $3,000 test or any leg is unresolved (the return's own gates speak then)."""
    rows = [resolved.get(path) for path in _COR_LEGS]
    if any(not row or row[0] != "Complete" for row in rows):
        return None
    over, deduction, with_it, without_it, credit = (row[2] for row in rows)
    if over != "true":
        return None
    cents = lambda v: round(Decimal(v) * 100)
    with_it, without_it, credit = cents(with_it), cents(without_it), cents(credit)
    return ("you repaid more than $3,000 this year that was taxed in an earlier year, and "
            "Publication 525 figures the tax both ways: with the repayment deducted on Schedule "
            f"A, line 16, the tax is {_money(with_it)}; without it, the tax is "
            f"{_money(without_it)} less the {_money(credit)} the repayment added to the earlier "
            f"year's tax, taken as the credit on Schedule 3, line 13b, which comes to "
            f"{_money(without_it - credit)}. This return uses the "
            + ("deduction, as the two are equal (section 1341 takes the deduction on a tie)"
               if with_it == without_it - credit else
               f"{'deduction' if deduction == 'true' else 'credit'}, the lower of the two"))
_UUID_RE = _re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _hoh_qualifying_person_choice(engine_facts: dict, resolved: dict):
    """the dictionary's head-of-household qualifying person is a WRITABLE choice over the
    persons it derives as eligible (`/hohQualifyingPeople`), and the mapper cannot make it — the
    eligible set is the engine's. Unsent, `/hohQPHasTin` stays Incomplete and `/knockoutHohQpHasNoTin`
    never resolves, so a qualifying child with no TIN filed as head of household (measured at the
    pin: 2,615.00 served complete where the dictionary refuses). After the first resolve the first
    eligible person with a TIN is chosen, else the first eligible person, and the return is
    resolved again so the dictionary's own refusal fires. The choice moves no served line
    (measured: two eligible children, every line identical whichever is sent), so it is a
    selection the layer states, never a derivation the filer owns. Returns the persister wrapper,
    or None where there is nothing to choose."""
    facts = engine_facts.get("facts") or {}
    status = resolved.get("/filingStatus")
    if _HOH_QP_PATH in facts or not (status and status[0] == "Complete" and status[2] == "headOfHousehold"):
        return None
    row = resolved.get("/hohQualifyingPeople")
    if not (row and row[0] == "Complete"):
        return None
    ids = _UUID_RE.findall(row[2])
    if not ids:
        return None
    def has_tin(i):
        t = resolved.get(f"/familyAndHousehold/#{i}/tinType")
        return bool(t and t[0] == "Complete" and t[2] != "none")
    chosen = next((i for i in ids if has_tin(i)), ids[0])
    return {"$type": "gov.irs.factgraph.persisters.CollectionItemWrapper", "item": {"id": chosen}}


def _hoh_qualifying_person_detail(resolved: dict):
    """the choice, stated on the wire as an assumption detail keyed on that person's TIN
    type — the field the refusal reads. The persons index is the id's own (`_uuid('2', i + 1)`)."""
    row = resolved.get(_HOH_QP_PATH) if resolved else None
    if not (row and row[0] == "Complete"):
        return None
    m = _UUID_RE.search(row[2])
    if not m:
        return None
    i = int(m.group(0)[1:8], 16) - 1
    return {"fact": f"persons[{i}].tin_type",
            "statement": (f"person {i + 1} is used as the qualifying person for head of household filing "
                          f"status — the first eligible person with a TIN, else the first eligible person; "
                          f"the figures are the same for any eligible person, and a qualifying person with "
                          f"no TIN is refused")}


class Operations:
    def __init__(self, adapter: EngineAdapter | None = None):
        self._adapter = adapter
        self._dict_hash = None

    # ---- helpers ----------------------------------------------------------------------------

    def _require_adapter(self):
        if self._adapter is None:
            try:
                self._adapter = default_engine()
            except EngineNotAvailable as e:
                raise OperationError("ENGINE_UNAVAILABLE", ENGINE_UNAVAILABLE_MESSAGE, detail=str(e))
        return self._adapter

    def _dictionary_hash(self) -> str:
        if self._dict_hash is not None:
            return self._dict_hash
        # Resolve the pinned dictionary directory. Prefer an already-loaded adapter; otherwise
        # discover the pin directly — a FILESYSTEM-ONLY lookup (no JVM subprocess), so the
        # engine-free `coverage` path still carries the real active-year dictionary hash on a
        # deployed container (provenance is the payload) rather than
        # "sha256:unavailable". Falls back to "unavailable" only when no engine home is configured
        # (e.g. local dev without a pin) — honest, and NOT cached so a later-configured pin is seen.
        try:
            dict_dir = (self._adapter.pin.dict_dir if self._adapter is not None
                        else discover_pin().dict_dir)
        except EngineNotAvailable:
            return "sha256:unavailable"
        try:
            # ONE implementation, shared with the pin check in engine/adapter.py. The value served
            # here as provenance must be the value the pin ENFORCES — two implementations could
            # drift, and then the number a caller verifies against would not be the number the pin
            # protects. (os.walk, not listdir: nested dictionary content must be hashed too.)
            self._dict_hash = dictionary_sha256(dict_dir)
        except Exception:
            self._dict_hash = "sha256:unavailable"
        return self._dict_hash

    def _input_hash(self, facts: dict) -> str:
        canon = json.dumps(facts, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(canon).hexdigest()

    def _envelope(self, facts: dict, result: dict, refusals: list | None = None) -> dict:
        # Determinism guarantee is over engine_version + dictionary_hash +
        # input_hash + result: same input_hash => identical bytes for THOSE. `computed_at` is a
        # wall-clock stamp and is deliberately excluded from that byte-identical guarantee.
        return {
            "engine_version": PINNED_DESCRIBE,
            "dictionary_hash": self._dictionary_hash(),
            "input_hash": self._input_hash(facts),
            "computed_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "result": result,
            "refusals": refusals or [],
        }

    def _assumption_pack(self, facts: dict, year: int, resolved: dict | None = None,
                         birth_days: dict | None = None) -> list:
        """Every assumption as `{fact, statement}`: the mapper's scaffold statements carry
        `fact` None — they rest on no field a caller could set — and the assumed-absent ones
        carry the service field their statement is about. The strings view every response also
        serves is this list's statements, one derivation, two spellings."""
        chosen = _hoh_qualifying_person_detail(resolved)
        return ([{"fact": None, "statement": statement}
                 for statement in _assumptions_for(facts, year, birth_days)]
                + _assumed_absent_details(facts)
                + ([chosen] if chosen else []))

    def _cited_lines(self, resolved: dict) -> list:
        """Resolved facts -> the served lines, cited. Shared by calculate_return and prepare_return
        so the two cannot report the same return differently."""
        lines = []
        for spec in LINE_MAP:
            entry = resolved.get(spec["fact_path"])
            if entry is None or entry[0] not in ("Complete", "Placeholder"):
                continue  # unresolved on this return; omit (honest — never a fabricated 0).
                          # unreachable on a served return — `_resolve` refuses by name
                          # (`_require_every_served_line_resolved`) before a line can be omitted.
            lines.append({
                "line_id": spec["line_id"],
                "label": spec["label"],
                "value_cents": _cents_from_dollar(entry[2]),
                "citation": spec["citation"],
                "derived_from": spec["derived_from"],
            })
        return lines

    def _tax_year(self, request: dict) -> int:
        """The one place `tax_year` leaves the request. Neither transport validates a request
        against the schema (REST does none; MCP validates responses only), so an out-of-enum or
        wrong-typed value used to reach arithmetic — `tax_year - 64` in the mapper's age-65 check —
        and surface as a 500 on REST or an unhandled TypeError that killed the MCP serve loop. It
        is a caller-input fault: refuse it as one. Booleans are ints in Python and are rejected
        explicitly (`True` would compute as year 1)."""
        year = request.get("tax_year", 2025)
        if isinstance(year, bool) or not isinstance(year, int) or year not in TAX_YEARS:
            raise OperationError(
                "SCHEMA_INVALID",
                f"tax_year must be one of {', '.join(str(y) for y in TAX_YEARS)}, got {year!r}",
                field_path="tax_year")
        return year

    def _facts_of(self, request: dict) -> dict:
        facts = request.get("facts")
        if facts is None:
            raise OperationError("SCHEMA_INVALID",
                                 "Phase 0 accepts inline `facts` only (workspaces are a later phase)",
                                 field_path="facts")
        return facts

    def _resolve(self, facts: dict, tax_year: int, engine_extras: dict | None = None,
                 birth_days: dict | None = None, notes: list | None = None) -> dict:
        # `engine_extras`: answers a person typed for engine inputs no service
        # field reaches — IN-PROCESS ONLY, never part of a REST or MCP request (the transports call
        # these operations without it). Validated and merged after the mapper (`facts.extras`); with
        # none given the engine request is the mapper's own, byte for byte.
        # Map BEFORE requiring the engine. Coverage is a property of the request, not of whether a
        # JVM is reachable — with the order reversed, an out-of-coverage input got ENGINE_UNAVAILABLE
        # on an engine-less host, making a permanent boundary look like a transient outage (and, when
        # both codes were OUT_OF_COVERAGE, hiding that they are different answers at all).
        try:
            # With nothing typed this is the mapper itself, called by the name it always was —
            # literally the old path, and the one a test can stall (`map_to_engine` is patched in
            # EveryServedLineResolvesOrTheReturnIsRefusedTest; one change once routed past it and
            # those two engine-backed tests went red on main unseen by CI, which has no engine).
            engine_facts = (map_with_extras(facts, tax_year, engine_extras, birth_days)
                            if engine_extras
                            else map_to_engine(facts, tax_year, birth_days=birth_days))
        except FactsSchemaError as e:
            # A required field missing, or one of the wrong type: the caller can fix it by sending
            # it again. `OUT_OF_COVERAGE` would say the opposite — that no amount of data helps —
            # which is the misreport once fixed for engine timeouts. Ordered before the parent class
            # because FactsSchemaError IS a ServiceFactsError.
            raise OperationError("SCHEMA_INVALID", str(e))
        except ServiceFactsError as e:
            raise OperationError("OUT_OF_COVERAGE", str(e))
        adapter = self._require_adapter()
        try:
            tsv = adapter.resolve_facts(engine_facts)
        except EngineNotAvailable as e:
            raise OperationError("ENGINE_UNAVAILABLE", ENGINE_UNAVAILABLE_MESSAGE, detail=str(e))
        resolved = _parse_resolved(tsv)
        choice = _hoh_qualifying_person_choice(engine_facts, resolved)
        if choice is not None:
            # A second resolve on a head-of-household return only (a resolve costs seconds at the
            # pin; a single or joint return never pays it). The path is set here, not in the
            # mapper, because the eligible set is the engine's — so it is outside the mapper's
            # partition (`test_assumptions`) by construction and stated on the wire instead.
            engine_facts["facts"][_HOH_QP_PATH] = choice
            try:
                tsv = adapter.resolve_facts(engine_facts)
            except EngineNotAvailable as e:
                raise OperationError("ENGINE_UNAVAILABLE", ENGINE_UNAVAILABLE_MESSAGE, detail=str(e))
            resolved = _parse_resolved(tsv)
        if notes is not None:
            said = _claim_of_right_statement(resolved)
            if said is not None:
                notes.append({"fact": _REPAYMENT, "statement": said})
        _require_declared_status_eligible(facts, resolved)
        _require_credit_history_resolved(facts, resolved)
        _require_care_expenses_on_qualifying_persons(facts, resolved)
        _require_ptc_not_on_dependent_filer_route(facts, resolved)
        _require_qbi_part_ii_not_needed(resolved)
        _require_every_served_line_resolved(resolved)
        if engine_extras:
            _require_typed_lines_took_effect(resolved)
        return resolved

    # ---- the five operations ----------------------------------------------------------------

    def calculate_return(self, request: dict, *, engine_extras: dict | None = None,
                         birth_days: dict | None = None) -> dict:
        facts = self._facts_of(request)
        notes: list = []
        resolved = self._resolve(facts, self._tax_year(request), engine_extras, birth_days, notes)
        lines = self._cited_lines(resolved)
        # What was assumed about THIS taxpayer to produce these numbers. `coverage` answers the
        # general question; a response that serves a figure has to answer the specific one, or the
        # preparer acknowledging it at submit is acknowledging boilerplate. Derived from the same
        # request that produced `resolved`, so the two cannot describe different returns.
        # Two kinds, one list, because a caller does not care which mechanism produced them: what
        # the mapper decides on every return (`assumptions_for`), and what THIS request left out
        # that still moved a number (`assumed_absent`) — an optional figure cannot be refused, so
        # the only honest alternative is to say it was treated as zero.
        details = self._assumption_pack(facts, self._tax_year(request), resolved, birth_days) + notes
        result = {"forms": [{"form_id": "1040", "lines": lines}],
                  "assumptions": [d["statement"] for d in details],
                  "assumption_details": details}
        return self._envelope(facts, result, refusals=knockouts_from(resolved))

    def prepare_return(self, request: dict, *, engine_extras: dict | None = None,
                       birth_days: dict | None = None) -> dict:
        """One round of the loop: what is still missing, or the finished return.

        FROZEN CONTRACT (2026-08-11), after the spike exercised it. Three things it deliberately
        does NOT carry, each because a field nothing produces is a promise nothing keeps:

          * no `signature` — no response signing exists service-side;
          * no `error` outcome — a transient failure is an ENGINE_UNAVAILABLE envelope, not a
            result, and the client normalises it;
          * no `gaps_only` mode — an `incomplete` renders nothing, so outcome semantics already
            cover what the flag was for.

        The order matters. Gaps are computed BEFORE the engine is required, because a missing input
        is a property of the request: reversed, an incomplete fact set on an engine-less host would
        report ENGINE_UNAVAILABLE and make a fixable omission look like an outage — the ordering bug
        once fixed for `_resolve`.
        """
        facts = self._facts_of(request)
        year = self._tax_year(request)
        unasked = _coverage.unasked_boundary()

        def envelope(outcome, gaps=(), forms=(), refusals=None, assumptions=None):
            # `assumptions` is the details list; the strings view is derived here so the two
            # served views are one derivation.
            details = list(assumptions if assumptions is not None else [])
            return self._envelope(facts, {
                "outcome": outcome,
                "versions": {"tax_year": year},
                "gaps": list(gaps),
                "assumptions": [d["statement"] for d in details],
                "assumption_details": details,
                "unasked_boundary": unasked,
                "forms": list(forms),
            }, refusals=refusals)

        gaps = _gaps_for(facts)
        if gaps:
            # Nothing is computed and nothing is rendered. Assumptions are omitted deliberately:
            # they describe a calculation that has not happened yet, and showing them now would
            # train a preparer to dismiss the list that matters at submit time.
            return envelope("incomplete", gaps=gaps)

        try:
            notes: list = []
            resolved = self._resolve(facts, year, engine_extras, birth_days, notes)
        except OperationError as e:
            if e.code == "OUT_OF_COVERAGE":
                return envelope("refused", refusals=[{"code": e.code, "boundary": e.message,
                                                      "manifest_ref": "coverage#exclusions"}])
            raise                       # SCHEMA_INVALID and ENGINE_UNAVAILABLE stay error envelopes

        knockouts = knockouts_from(resolved)
        assumptions = self._assumption_pack(facts, year, resolved, birth_days) + notes
        if knockouts:
            # It COMPUTES but must not be FILED. Serving forms here would put a renderable return in
            # front of someone the dictionary says cannot file it.
            return envelope("knocked_out", refusals=knockouts, assumptions=assumptions)

        lines = self._cited_lines(resolved)
        return envelope("complete", forms=[{"form_id": "1040", "lines": lines}],
                        assumptions=assumptions)

    def coverage(self, request: dict) -> dict:
        year = self._tax_year(request)
        # DERIVED from the line map + the mapper's enforced boundary (service/coverage.py) — never
        # a hand-typed list, which goes stale the moment either one changes.
        result = {
            "supported_forms": _coverage.supported_forms(),
            "knockouts": _coverage.knockouts(),
            "exclusions": _coverage.exclusions(year),
            # What the mapper DECIDES without asking. Distinct from `exclusions`: an exclusion is
            # something the service refuses to compute, so the caller knows to go elsewhere; an
            # assumption is something it computed anyway, on a claim about the taxpayer that nobody
            # supplied and no field lets them contradict. Silence about those is what makes a
            # confident answer wrong.
            "assumptions": _coverage.assumptions(),
            # constant_provenance reports IRS-constant ANNOUNCEMENT status per year (announced vs
            # pending) — deliberately NOT per-year dictionary content hashes (D38 considered): this
            # service pins/bakes in only ty2025, so genuine 2024/2026 dictionary hashes aren't
            # available here to carry (those are later-phase artifacts), and content-hash ≠
            # announcement-status. The active pinned dictionary's real hash is carried at the
            # envelope level (`dictionary_hash` below), which now resolves it filesystem-only.
            "constant_provenance": {
                "2024": {"announced": 1, "pending": 0},
                "2025": {"announced": 1, "pending": 0},
                "2026": {"announced": 0, "pending": 1},
            },
        }
        # coverage needs no engine; stamp provenance without forking a JVM (the dictionary_hash
        # lookup below is filesystem-only — see _dictionary_hash).
        return {
            "engine_version": PINNED_DESCRIBE,
            "dictionary_hash": self._dictionary_hash(),
            "input_hash": self._input_hash({"tax_year": year}),
            "computed_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "result": result,
            "refusals": [],
        }
