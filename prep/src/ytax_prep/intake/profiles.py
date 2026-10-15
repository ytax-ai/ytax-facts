# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Showcase profiles inverted into service shape, and the pinned engine's own lines as the
oracle.

`generated/reachability.json` `service_fields` names ONE engine path per service field, built
forward by `src/ytax_prep/facts/mapper.py`. This module walks a showcase profile's own
engine-shaped `facts.json` (already pinned-engine-native — no mapper involved in producing it) and
inverts that table: for every engine path the profile carries that `service_fields` also names, it
recovers the service field value that would have produced it. `map_to_engine` is never imported or
called here — the inverse stands on its own, the way the mapper's emission tables (`_SYNTH_TIN`,
`_DICT_FILING`, `EDUCATOR_OPTIONS`) are documented, not on a live dependency.

The identity plane (filer/dependent TINs, names, addresses) is never recovered as a value — only
`tin_type`, read off the TIN's SHAPE (does the area start with "9"?) and the mapper's own
employment-validity side channel, exactly the two facts `_SYNTH_TIN` and `_filer`/`_dependent`
derive it from. No name or address field is ever produced (the schema has none to produce into).

Anything this inverse cannot express — an engine value with no service-field translation at all
(`/casualtyEvents`, an explicit true `/hasQbiIncome`), a NEGATIVE `/writableEstateTrustK1Income`
(the schema's own `k1s[].source == "estate_trust"` route would deduct it as entered, which the
mapper refuses), or an aggregate fact (`/madeIraContributions`, `/hasDistributionsInLastThreeYears`)
whose true literal cannot be split back across the filers that produced it — raises `ProfileGap`
naming the engine path, never a guessed value. A claimed dependent's full §152 qualifying-person
battery IS now recovered (`_dependent_person`): the relationship,
residency, support and CDCC fields the showcase's own claimed-dependent profiles carry, with
`gross_income_under_limit` and `filer_provided_over_half_support` sent `True` only where that is
provably inert (a row this inverse's own answers already qualify as a qualifying CHILD — see
`_dependent_person`'s docstring). A NON-NEGATIVE `/writableEstateTrustK1Income` IS recovered
(`_legacy_estate_trust_k1`), as is Form 8889 Part I's per-filer contribution
chain (`_apply_hsa_fields`), `/writableAlimonyReceivedAmount`/`/writableAlimonyPaidAmount` and
`/writableMainHomeInUsOverHalfYear` (the generic root-scalar join, once `schema/rename-table.json`
carries them) — a handful of root/per-filer facts the mapper reads but never emits from a service
answer (`/hasQbiIncome`, the legacy scalar IRA-distribution intake) still have no service-shape
equivalent; those raise `ProfileGap` rather than being guessed at, and need a mapper/schema
addition this task does not make.
"""
from __future__ import annotations

import os
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from ..engine.adapter import EngineAdapter
from ..facts import mapper
from ..service import reachability as _reachability
from ..service.lines import LINE_MAP

# The synthetic showcase profiles live outside this repository; YTAX_SHOWCASE_PROFILES names them.
# Unset, SHOWCASE is a path under os.devnull, which is never a directory, so every caller's
# existence check reads it as absent and self-skips.
SHOWCASE = (Path(os.environ["YTAX_SHOWCASE_PROFILES"]) if os.environ.get("YTAX_SHOWCASE_PROFILES")
            else Path(os.devnull) / "showcase-profiles")

FILER_ROOT = "/filers"
DEPENDENT_ROOT = "/familyAndHousehold"

# ---- the mapper's own tables, mirrored for inversion (mapper.py: _DICT_FILING, _SYNTH_TIN,
# EDUCATOR_OPTIONS, _DEP_TIN_TYPE, _DEP_SSN_VALIDITY, the filer-side `_VALIDITY`) --------------

_DICT_FILING_INVERSE = {
    "single": "single", "marriedFilingJointly": "mfj", "marriedFilingSeparately": "mfs",
    "headOfHousehold": "hoh", "qualifiedSurvivingSpouse": "qss",
}

# mapper.EDUCATOR_OPTIONS: {(primary_did, spouse_did): literal} -> inverted here.
_EDUCATOR_OPTIONS_INVERSE = {
    "neither": (False, False), "tpDid": (True, False),
    "spouseDid": (False, True), "bothDid": (True, True),
}

# mapper._VALIDITY (filer side) and mapper._DEP_SSN_VALIDITY (dependent side) share these two
# literals for the same two service types; the "notValid"/"neither" enum never appears without one
# of these having produced it.
_SSN_VALIDITY_INVERSE = {"neither": "ssn_valid_for_employment", "notValid": "ssn_other",
                         "validOnlyWithDhsAuthorization": "ssn_dhs_authorization",
                         "validOnlyWithDhsAuthorizationInEffect": "ssn_dhs_authorization",
                         "validOnlyWithDhsAuthorizationExpired": "ssn_dhs_authorization_expired"}

# mapper.py always emits "neither" for a False estimated_payments_with_former_spouse and refuses
# a True by name (the former-spouse TIN is an identifier this schema cannot carry) — so a
# service value is always one of these two states, and every other
# /paidEstimatedTaxesWithFormerSpouseOptions literal ("tpDid", "spouseDid", "bothDid") is some
# filer's own YES to the question, which this schema also represents as True (the refusal then
# applies downstream, exactly as it would to a service-side True answer).
_ESTIMATED_PAYMENTS_FORMER_SPOUSE_INVERSE = {
    "neither": False, "tpDid": True, "spouseDid": True, "bothDid": True,
}

EDUCATOR_FIELD = "k12_educator"
# mapper.py's EDUCATOR_AMOUNT_FIELD, and the two root writables `/madeIraContributions`'s sibling
# educator aggregate reaches per filer (`/primaryEducatorExpensesWritable`,
# `/secondaryEducatorExpensesWritable`) — the same shape as the IRA per-filer facts above.
EDUCATOR_AMOUNT_FIELD = "educator_expenses_cents"
_EDUCATOR_AMOUNT_PER_FILER = {True: "/primaryEducatorExpensesWritable",
                              False: "/secondaryEducatorExpensesWritable"}
IRA_FIELD = "made_ira_contributions"
HSA_CONTRIBUTIONS_FIELD = "made_hsa_contributions"
# mapper.py's Form 8889 Part I fields — mirrored here (the module's no-live-dependency
# discipline). Four of these share ONE literal engine leaf across both filer rows
# (`hsaHdhpCoverageStatus`, `typeOfHdhp`, `hadOtherCoverageIneligibleForHSA`,
# `enrolledInMedicare` — mapper.py `_hsa_section`), so they are recovered by a direct per-filer
# walk (`_apply_hsa_fields` below) rather than through `_service_fields_inverse`, which cannot
# record a role-conditioned engine path (the same reason the IRA/educator per-filer tables above
# exist by hand). `made_hsa_contributions` IS role-conditioned in the engine
# (`writable{Primary,Secondary}FilerHasMadeContributionsToHsa`) for the same reason.
HSA_MEDICARE_FIELD = "hsa_medicare"
HSA_COVERAGE_FIELD = "hsa_hdhp_coverage"
HSA_TYPE_FIELD = "hsa_hdhp_type"
HSA_OTHER_COVERAGE_FIELD = "hsa_other_coverage"
HSA_FUNDING_FIELD = "hsa_funding_distribution"
HSA_OWN_AMOUNT_FIELD = "hsa_own_contributions_cents"
HSA_OWN_AFTER_FIELD = "hsa_own_contributions_after_year_end_cents"
_HSA_YEAR_SPANS_INVERSE = {"allYear": "all_year", "partOfYear": "part_of_year", "noneOfYear": "none"}
_HSA_OTHER_COVERAGE_SPANS_INVERSE = {"wholeYear": "whole_year", "partOfYear": "part_of_year",
                                     "noneOfYear": "none"}
_HSA_HDHP_TYPES_INVERSE = {"selfOnly": "self_only", "family": "family", "both": "both"}
_HSA_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
HSA_MONTH_FIELDS = tuple(f"hsa_coverage_{m}" for m in _HSA_MONTHS)
# mapper.py's HSA_EXCEPTION_REASONS (the 20%-tax exception), inverted.
HSA_EXCEPTION_AMOUNT_FIELD = "hsa_exception_amount_cents"
HSA_EXCEPTION_REASON_FIELD = "hsa_exception_reason"
_HSA_EXCEPTION_REASONS_INVERSE = {"age65": "age65", "disability": "disability",
                                  "deathOfBeneficiary": "death_of_beneficiary", "none": "none"}
# mapper.py: IRA_AMOUNT_FIELD, IRA_INHERITED_FIELD, IRA_ROTH_ABLE_FIELD — mirrored here (the
# module's no-live-dependency discipline) because `ira_questions_reached` makes all three
# unconditionally required the moment a filer row's `made_ira_contributions` is true.
IRA_AMOUNT_FIELD = "traditional_ira_contributions_cents"
IRA_INHERITED_FIELD = "contributed_to_inherited_ira"
IRA_INHERITED_AMOUNT_FIELD = "inherited_ira_contribution_cents"
IRA_ROTH_ABLE_FIELD = "roth_ira_and_able_contributions_cents"

# mapper.py's IRA_EMISSION table (`/primaryFilerTraditionalIraContributions` +
# `/writablePrimaryFilerContributedToInheritedIra`, and the secondary-filer twins) plus the
# combined Roth-and-ABLE writable — the PER-FILER facts `/madeIraContributions` aggregates over.
# A profile that answers one of a filer's three names it as the filer who contributed, which is
# exactly the attribution the bare aggregate boolean cannot carry alone.
_IRA_PER_FILER_TRAD = {True: "/primaryFilerTraditionalIraContributions",
                       False: "/secondaryFilerTraditionalIraContributions"}
_IRA_PER_FILER_ROTH_ABLE = {True: "/writablePrimaryFilerIraAndAbleContributions",
                            False: "/writableSecondaryFilerIraAndAbleContributions"}
_IRA_PER_FILER_INHERITED = {True: "/writablePrimaryFilerContributedToInheritedIra",
                            False: "/writableSecondaryFilerContributedToInheritedIra"}
_IRA_PER_FILER_INHERITED_AMOUNT = {True: "/writablePrimaryFilerAmountPaidToInheritedIra",
                                   False: "/writableSecondaryFilerAmountPaidToInheritedIra"}

# Promoted-default fields: this service asks more than the raw engine needs as
# INPUT — a root or per-person question every return answers, promoted from an attested default
# to an asked one, each of whose root answer was once attested
# false and published as an assumption. A showcase profile's own facts.json is built directly
# against the engine, never through this service's conversation, so it carries no engine fact for
# any of these at all — there is nothing here to INVERT, honestly or otherwise. The recovery is
# the same neutral default this service itself used before it started asking: false. Measured on
# profile-A/profile-C: no served line depends on any of the three credit-history answers (no
# credit is in play on either — neither has a dependent, and both filers' income is far above the
# childless-EIC ceiling), and the same holds for the HSA/rollover fields below (no HSA
# distribution, no employer HSA box on the W-2, and the 1099-R shows no rollover on the profile's
# own facts).
_CREDIT_HISTORY_DEFAULTS = {
    "eitc_reduced_or_disallowed": False,
    "ctc_odc_reduced_or_disallowed": False,
    "qualifying_child_of_another": False,
}

_DOB_RE = re.compile(r"^(\d{4})-(\d{2})-\d{2}$")


class ProfileGap(ValueError):
    """An engine fact this inverse cannot express in service shape. Message names the path."""


def profiles() -> list[Path]:
    """Sorted showcase profile directories that carry `input/facts.json`."""
    if not SHOWCASE.is_dir():
        return []
    return sorted(p for p in SHOWCASE.iterdir() if (p / "input" / "facts.json").is_file())


# ---- small persister-format helpers -----------------------------------------------------------

def _cents(dollar: str) -> int:
    """The mapper's `_money` in reverse: '52000.00' -> 5200000 cents, exact (Decimal, never
    float)."""
    return int((Decimal(dollar) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _type_of(fact: dict) -> str:
    return fact.get("$type", "").rsplit(".", 1)[-1]


def _value_of(fact: dict, path: str):
    """A BooleanWrapper/StringWrapper/DollarWrapper/IntWrapper's persister value in service
    shape. EnumWrapper is handled by the caller (translation is field-specific)."""
    t = _type_of(fact)
    item = fact.get("item")
    if t == "BooleanWrapper":
        return bool(item)
    if t == "StringWrapper":
        return item
    if t == "DollarWrapper":
        return _cents(item)
    if t == "IntWrapper":
        return int(item)
    raise ProfileGap(f"{path}: a {t} value has no generic service-shape translation")


def _parse_resolved(tsv: str) -> dict:
    """path -> (status, type, value) for every resolved fact line — the same shape
    `service.operations._parse_resolved` reads, kept local so this module never imports a
    leading-underscore name across a package boundary."""
    out = {}
    for ln in tsv.splitlines():
        parts = ln.split("\t", 3)
        if len(parts) == 4:
            out[parts[0]] = (parts[1], parts[2], parts[3])
    return out


# ---- generated/reachability.json service_fields, inverted --------------------------------------

_ROLE_RE = re.compile(r"^(.*?)(?: \(role=(.*)\))?$")


def _service_fields_inverse() -> dict:
    """engine path (with `*` for a collection item) -> [(service field, role-or-None), ...],
    the reverse of `generated/reachability.json`'s `service_fields` (357 entries; some carry a
    `(role=...)` annotation this splits off)."""
    sf = _reachability.load()["service_fields"]
    inv: dict = {}
    for key, engine_path in sf.items():
        m = _ROLE_RE.match(key)
        field, role = m.group(1), m.group(2)
        inv.setdefault(engine_path, []).append((field, role))
    return inv


# ---- filers / dependents -> persons -------------------------------------------------------

def _filer_tin_type(base: str, area: str, group: str, validity_literal) -> str:
    """`_SYNTH_TIN` and the filer-side `_VALIDITY` table, inverted. Only the TIN's SHAPE (area
    starting with "9" or not) and the employment-validity side channel are read — never the
    digits themselves, which carry no meaning here beyond that shape (no identifier
    ever enters the service fact set)."""
    if area.startswith("9"):
        # mapper._SYNTH_TIN: itin -> ("900","70"), atin -> ("900","93"); a showcase profile's own
        # synthetic generator does not share the mapper's exact group digits, so only the ATIN
        # marker (group "93") is matched literally — every other 9-area group reads as an ITIN,
        # the same "reads as what it is" shape the mapper's own comment states.
        return "atin" if group == "93" else "itin"
    if validity_literal is None:
        return "none"
    if validity_literal in _SSN_VALIDITY_INVERSE:
        return _SSN_VALIDITY_INVERSE[validity_literal]
    raise ProfileGap(f"{base}/tin: ssnEmploymentValidity {validity_literal!r} has no service "
                      f"tin_type")


def _filer_rows(facts: dict) -> list:
    """[(cid, is_primary, person_dict), ...] for every REAL filer row (a phantom single-filer
    slot -- isPrimaryFiler false and nothing else, mapper.py `map_to_engine` around
    `len(filer_ids) == 1` -- carries no dateOfBirth and is skipped, never counted as a person)."""
    root = facts.get(FILER_ROOT)
    if root is None:
        raise ProfileGap(f"{FILER_ROOT}: no filers collection")
    rows = []
    for cid in root["item"]["items"]:
        base = f"{FILER_ROOT}/#{cid}"
        dob = facts.get(f"{base}/dateOfBirth")
        if dob is None:
            continue                                       # the phantom second-filer slot
        m = _DOB_RE.match(dob["item"]["date"])
        if not m:
            raise ProfileGap(f"{base}/dateOfBirth: unparseable date {dob['item']['date']!r}")
        year, month = int(m.group(1)), int(m.group(2))
        primary_fact = facts.get(f"{base}/isPrimaryFiler")
        is_primary = bool(primary_fact["item"]) if primary_fact is not None else False
        tin_fact = facts.get(f"{base}/tin")
        if tin_fact is None:
            raise ProfileGap(f"{base}/tin: a real filer row with no TIN")
        area, group = tin_fact["item"]["area"], tin_fact["item"]["group"]
        validity_path = ("/primaryFilerSsnEmploymentValidity" if is_primary
                          else "/secondaryFilerSsnEmploymentValidity")
        validity_fact = facts.get(validity_path)
        validity_literal = (validity_fact["item"]["value"][0]
                             if validity_fact is not None else None)
        tin_type = _filer_tin_type(base, area, group, validity_literal)
        claim_fact = facts.get(f"{base}/canBeClaimed")
        if claim_fact is None:
            raise ProfileGap(f"{base}/canBeClaimed: required and absent")
        blind_fact = facts.get(f"{base}/isBlind")
        if blind_fact is None:
            raise ProfileGap(f"{base}/isBlind: required and absent")
        person = {
            "role": "primary" if is_primary else "spouse",
            "birth_year": year,
            "birth_month": month,
            "tin_type": tin_type,
            "someone_can_claim_you": bool(claim_fact["item"]),
            "is_blind": bool(blind_fact["item"]),
        }
        # mapper.py emits `/filers/*/isStudent` unconditionally with a Python-side False default
        # (`person.get("is_student", False)`), so the mapper itself never requires an answer —
        # but the service's own gaps.py makes it a REQUIRED gap once that filer's
        # made_ira_contributions is true (Form 8880's student test). Recovered whenever the raw
        # engine carries it, which costs nothing on a row where it is never asked for.
        student_fact = facts.get(f"{base}/isStudent")
        if student_fact is not None:
            person["is_student"] = bool(student_fact["item"])
        # the rest of the "someone can claim you" chain (mapper.CLAIM_ME_EMISSION), as the
        # profile answered it; the page asks each link only where the chain reaches it
        for field, leaf in (("expect_to_be_claimed", "willBeClaimed"),
                            ("potential_claimer_must_file", "potentialClaimerMustFile"),
                            ("potential_claimer_filed", "potentialClaimerDidFile")):
            link = facts.get(f"{base}/{leaf}")
            if link is not None:
                person[field] = bool(link["item"])
        refund_only = facts.get("/primaryFilerPotentialClaimerFiledOnlyForRefund")
        if is_primary and refund_only is not None:
            person["potential_claimer_filed_only_for_refund"] = bool(refund_only["item"])
        rows.append((cid, is_primary, person))
    if not rows:
        raise ProfileGap(f"{FILER_ROOT}: no real filer row (every slot was the phantom one)")
    rows.sort(key=lambda r: not r[1])                        # isPrimaryFiler true first
    return rows


# mapper.py's `_RELATIONSHIP` table (category, specific_fact, literal), mirrored here per the
# module's no-live-dependency discipline. `none_of_the_above` carries no specific fact (its
# category alone, "notRelated", settles it) and is handled separately below.
_RELATIONSHIP = {
    "biological_child": ("childOrDescendants", "childRelationship", "biologicalChild"),
    "adopted_child": ("childOrDescendants", "childRelationship", "adoptedChild"),
    "step_child": ("childOrDescendants", "childRelationship", "stepChild"),
    "foster_child": ("childOrDescendants", "childRelationship", "fosterChild"),
    "grand_child_or_other_descendant_of_child":
        ("childOrDescendants", "childRelationship", "grandChildOrOtherDescendantOfChild"),
    "sibling": ("siblingOrDescendants", "siblingRelationship", "sibling"),
    "child_of_sibling": ("siblingOrDescendants", "siblingRelationship", "childOfSibling"),
    "other_descendant_of_sibling":
        ("siblingOrDescendants", "siblingRelationship", "otherDescendantOfSibling"),
    "half_sibling": ("siblingOrDescendants", "siblingRelationship", "halfSibling"),
    "child_of_half_sibling":
        ("siblingOrDescendants", "siblingRelationship", "childOfHalfSibling"),
    "other_descendant_of_half_sibling":
        ("siblingOrDescendants", "siblingRelationship", "otherDescendantOfHalfSibling"),
    "step_sibling": ("siblingOrDescendants", "siblingRelationship", "stepSibling"),
    "child_of_step_sibling":
        ("siblingOrDescendants", "siblingRelationship", "childOfStepSibling"),
    "other_descendant_of_step_sibling":
        ("siblingOrDescendants", "siblingRelationship", "otherDescendantOfStepSibling"),
    "parent": ("parentOrAncestors", "parentalRelationship", "parent"),
    "step_parent": ("parentOrAncestors", "parentalRelationship", "stepParent"),
    "foster_parent": ("parentOrAncestors", "parentalRelationship", "fosterParent"),
    "grand_parent": ("parentOrAncestors", "parentalRelationship", "grandParent"),
    "other_ancestor_of_parent":
        ("parentOrAncestors", "parentalRelationship", "otherAncestorOfParent"),
    "sibling_of_parent": ("parentOrAncestors", "parentalRelationship", "siblingOfParent"),
    "step_grand_parent": ("parentOrAncestors", "parentalRelationship", "stepGrandParent"),
    "step_sibling_of_parent":
        ("parentOrAncestors", "parentalRelationship", "stepSiblingOfParent"),
    "child_in_law": ("inlaws", "inlawRelationship", "childInLaw"),
    "parent_in_law": ("inlaws", "inlawRelationship", "parentInLaw"),
    "sibling_in_law": ("inlaws", "inlawRelationship", "siblingInLaw"),
    "siblings_spouse": ("inlaws", "inlawRelationship", "siblingsSpouse"),
    "none_of_the_above": ("notRelated", None, None),
}
_CATEGORY_SPECIFIC_FACT = {}
_RELATIONSHIP_INVERSE = {}
for _code, (_cat, _field, _lit) in _RELATIONSHIP.items():
    if _field:
        _CATEGORY_SPECIFIC_FACT.setdefault(_cat, _field)
        _RELATIONSHIP_INVERSE[(_cat, _field, _lit)] = _code
del _code, _cat, _field, _lit

# mapper.py's `_MONTH_WORDS` ({7: "seven", ..., 12: "twelve"}), inverted.
_MONTH_WORDS_INVERSE = {"six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}


def _dependent_relationship(facts: dict, base: str) -> str:
    cat_fact = facts.get(f"{base}/relationshipCategory")
    if cat_fact is None:
        raise ProfileGap(f"{base}/relationshipCategory: required and absent")
    category = cat_fact["item"]["value"][0]
    if category == "notRelated":
        return "none_of_the_above"
    field = _CATEGORY_SPECIFIC_FACT.get(category)
    if field is None:
        raise ProfileGap(f"{base}/relationshipCategory: {category!r} has no service relationship")
    spec_fact = facts.get(f"{base}/{field}")
    if spec_fact is None:
        raise ProfileGap(f"{base}/{field}: required and absent")
    literal = spec_fact["item"]["value"][0]
    key = (category, field, literal)
    if key not in _RELATIONSHIP_INVERSE:
        raise ProfileGap(f"{base}/{field}: {literal!r} has no service relationship code")
    return _RELATIONSHIP_INVERSE[key]


def _dependent_tin_type(base: str, tin_type_literal: str, validity_literal) -> str:
    """mapper.py's `_DEP_TIN_TYPE` / `_DEP_SSN_VALIDITY`, inverted. Unlike a filer's TIN, a
    dependent's `tinType` states itin/atin/none directly — only "ssn" is split further by the
    validity side channel, the same two literals a filer's own TIN validity uses."""
    if tin_type_literal in ("itin", "atin", "none"):
        return tin_type_literal
    if tin_type_literal != "ssn":
        raise ProfileGap(f"{base}/tinType: {tin_type_literal!r} has no service tin_type")
    if validity_literal is None:
        # a Direct File profile asks a dependent's card legend only where a credit turns on it;
        # unasked is the ordinary card, valid for employment
        return "ssn_valid_for_employment"
    if validity_literal not in _SSN_VALIDITY_INVERSE:
        raise ProfileGap(f"{base}/ssnEmploymentValidity: {validity_literal!r} has no service "
                          f"tin_type")
    return _SSN_VALIDITY_INVERSE[validity_literal]


def _dependent_person(facts: dict, base: str) -> dict:
    """One `/familyAndHousehold` item -> a `role: "dependent"` persons[] entry. Recovers exactly
    the fields mapper.py's `_dependent` (facts/mapper.py) reads off a dependent row: the four it
    emits UNCONDITIONALLY (`is_married`, `provided_own_support`, `gross_income_under_limit`,
    `filer_provided_over_half_support`, `could_be_qualifying_child_of_another`) must all be
    present or `_dependent` raises a bare KeyError far from here.

    `gross_income_under_limit` and `filer_provided_over_half_support` (Form 1040 instructions'
    qualifying-RELATIVE gross-income and support tests) are read by the engine ONLY inside the
    qualifying-relative arm (familyAndHousehold.xml: `../grossIncomeTest` is a dependency of
    exactly one Switch case, the QR one) — unreachable on a row this inverse's OWN recovered
    answers already qualify as a qualifying CHILD (the population every showcase dependent
    profile carries: a claimed biological/adopted child, residency and support all answered).
    True is sent for both because on that population it is provably inert, not because it is
    guessed: measured across every showcase dependent profile, the served lines are identical
    whichever of True/False these two carry.
    """
    dob = facts.get(f"{base}/dateOfBirth")
    if dob is None:
        raise ProfileGap(f"{base}/dateOfBirth: required and absent")
    m = _DOB_RE.match(dob["item"]["date"])
    if not m:
        raise ProfileGap(f"{base}/dateOfBirth: unparseable date {dob['item']['date']!r}")
    year, month = int(m.group(1)), int(m.group(2))

    tin_type_fact = facts.get(f"{base}/tinType")
    if tin_type_fact is None:
        raise ProfileGap(f"{base}/tinType: required and absent")
    validity_fact = facts.get(f"{base}/ssnEmploymentValidity")
    validity_literal = validity_fact["item"]["value"][0] if validity_fact is not None else None
    tin_type = _dependent_tin_type(base, tin_type_fact["item"]["value"][0], validity_literal)

    relationship = _dependent_relationship(facts, base)

    residency_fact = facts.get(f"{base}/residencyDuration")
    if residency_fact is None:
        raise ProfileGap(f"{base}/residencyDuration: required and absent")
    residency_literal = residency_fact["item"]["value"][0]
    months_fact = facts.get(f"{base}/monthsLivedWithTPInUS")
    if residency_literal == "lessThanSixMonths":
        # below six months the mapper sends the bucket and no month count, so every count from 0
        # to 5 resolves alike: 0 stands for the bucket
        months_fact = None
        months_literal = None
    elif residency_literal == "sixMonths":
        # six months, not more than half the year: the residency test fails here and the
        # months-in-the-US question is never reached (the mapper sends none), so 6 is the answer
        months_fact = None
        months_literal = "six"
    elif months_fact is None:
        # a Direct File profile never asked the month count: all year is twelve months; more than
        # half the year but not all of it is the bucket's floor, seven
        months_literal = {"allYear": "twelve", "sevenToElevenMonths": "seven"}.get(residency_literal)
        if months_literal is None:
            raise ProfileGap(f"{base}/monthsLivedWithTPInUS: required and absent")
    else:
        months_literal = months_fact["item"]["value"][0]
    if residency_literal == "sevenToElevenMonths" and months_literal == "six":
        raise ProfileGap(f"{base}/monthsLivedWithTPInUS: six months in the United States on a "
                          f"more-than-half-the-year row — months_in_home carries one count, not two")
    if months_literal is not None and months_literal not in _MONTH_WORDS_INVERSE:
        raise ProfileGap(f"{base}/monthsLivedWithTPInUS: {months_literal!r} has no service "
                          f"months_in_home")
    months_in_home = 0 if months_literal is None else _MONTH_WORDS_INVERSE[months_literal]

    def _req_bool(leaf: str) -> bool:
        fact = facts.get(f"{base}{leaf}")
        if fact is None:
            raise ProfileGap(f"{base}{leaf}: required and absent")
        return bool(fact["item"])

    person = {
        "role": "dependent",
        "birth_year": year,
        "birth_month": month,
        "tin_type": tin_type,
        "relationship": relationship,
        "months_in_home": months_in_home,
        "is_married": _req_bool("/married"),
        # unasked on a Direct File row: the child did not provide over half their own support
        "provided_own_support": bool((facts.get(f"{base}/ownSupport") or {}).get("item", False)),
        # absent on a Direct File profile that was never asked it (no other person could claim
        # the child): no, the answer the page's own question defaults a person to
        "could_be_qualifying_child_of_another":
            bool((facts.get(f"{base}/writableCouldBeQualifyingChildOfAnother") or {}).get("item", False)),
        # read where the profile states them (an adult qualifying relative turns on both); the
        # docstring's True only where it does not
        "gross_income_under_limit": bool((facts.get(f"{base}/grossIncomeTest") or {}).get("item", True)),
        "filer_provided_over_half_support":
            bool((facts.get(f"{base}/writableQrSupportTest") or {}).get("item", True)),
    }
    other_parent_fact = facts.get(f"{base}/hasOtherBiologicalOrAdoptiveParent")
    if other_parent_fact is not None:
        person["has_other_biological_or_adoptive_parent"] = bool(other_parent_fact["item"])
    # the benefit-split chain behind it, as the profile answered it (mapper's own literals, read
    # back): each link the page asks only where the chain reaches it
    enum_inverse = {
        "parents_situation": {v: k for k, v in mapper._PARENTS_SITUATION.items()},
        "written_declaration": {v: k for k, v in mapper._WRITTEN_DECLARATION.items()},
        "nights_with_filer_vs_other_parent": {v: k for k, v in mapper._NIGHTS.items()},
    }
    for field, leaf in (mapper.DEPENDENT_BENEFIT_SPLIT_EMISSION.items()
                        if person.get("has_other_biological_or_adoptive_parent") else ()):
        link = facts.get(f"{base}/{leaf}")
        if link is None:
            continue
        if field in enum_inverse:
            literal = link["item"]["value"][0]
            if literal not in enum_inverse[field]:
                raise ProfileGap(f"{base}/{leaf}: {literal!r} has no service {field}")
            person[field] = enum_inverse[field][literal]
        else:
            person[field] = bool(link["item"])
    # mapper.py `upkeep_question_armed`: always armed on hoh/qss (every claimed dependent row);
    # on single, armed only for the rows the engine's own screen gate reaches; on mfj/mfs, armed
    # only when the lived-together chain says the spouses lived apart the last six months. This
    # inverse recovers the status-level enum but not that lived-apart chain, so only the
    # unconditional hoh/qss population is safe to forward — measured: an mfj row's own
    # `tpPaidMostOfHomeUpkeep` answer is refused by name (`refuse_root_scalars`) rather than
    # silently accepted when the row is not armed.
    filing_status_fact = facts.get("/filingStatus")
    filing_status_literal = (filing_status_fact["item"]["value"][0]
                              if filing_status_fact is not None else None)
    upkeep_fact = facts.get(f"{base}/tpPaidMostOfHomeUpkeep")
    if upkeep_fact is not None and filing_status_literal in ("headOfHousehold",
                                                              "qualifiedSurvivingSpouse"):
        person["filer_paid_most_of_home_upkeep"] = bool(upkeep_fact["item"])
    unable_fact = facts.get(f"{base}/unableToCareForSelf")
    if unable_fact is not None:
        person["unable_to_care_for_self"] = bool(unable_fact["item"])
    living_fact = facts.get(f"{base}/biologicalOrAdoptiveParentsLiving")
    if living_fact is not None:
        person["child_parents_living"] = bool(living_fact["item"])
    student_fact = facts.get(f"{base}/fullTimeStudent")
    if student_fact is not None and bool(student_fact["item"]):
        person["is_student"] = True
    disabled_fact = facts.get(f"{base}/permanentTotalDisability")
    if disabled_fact is not None:
        person["is_permanently_disabled"] = bool(disabled_fact["item"])
    # the benefit-split gate's custody chain (mapper.child_custody_questions_reached), read in
    # chain order and only as far as the chain reaches: the state, then whether the child was
    # emancipated, then whether that was after July 2 (a date after the tax year reads as no)
    custody = {
        "child_residence_state": lambda f: f["item"]["value"][0],
        "child_emancipated": lambda f: bool(f["item"]),
        "child_emancipated_after_july_2":
            lambda f: "2025-07-02" < f["item"]["date"] <= "2025-12-31",
    }
    leaves = {"child_residence_state": "writableChildResidenceJurisdiction",
              "child_emancipated": "writableChildEmancipatedUnderStateLaw",
              "child_emancipated_after_july_2": "writableChildEmancipationDate"}
    for _ in custody:
        pending = [f for f in mapper.child_custody_questions_reached(person) if f not in person]
        if not pending:
            break
        fact = facts.get(f"{base}/{leaves[pending[0]]}")
        if fact is None:
            break
        person[pending[0]] = custody[pending[0]](fact)
    # Form 2441 line 2, the qualifying person's own care-expense amount — mapper.py derives
    # BOTH `cdccHasDependentCareExpenses` and `cdccHadExpensesPaidToQualifyingProvider` from this
    # one amount (`_cdcc_section`), so recovering it here is enough; the two raw booleans need no
    # translation of their own.
    care_fact = facts.get(f"{base}/writableCdccQualifyingExpenseAmount")
    if care_fact is not None:
        person["care_expenses_cents"] = _value_of(care_fact, f"{base}/writableCdccQualifyingExpenseAmount")
    return person


def _dependents(facts: dict) -> list:
    """Every `/familyAndHousehold` item -> a `role: "dependent"` persons[] entry (see
    `_dependent_person`)."""
    root = facts.get(DEPENDENT_ROOT)
    if root is None or not root["item"]["items"]:
        return []
    return [_dependent_person(facts, f"{DEPENDENT_ROOT}/#{cid}") for cid in root["item"]["items"]]


def _apply_combined_person_fields(facts: dict, filer_persons: list) -> None:
    """`/wasK12Educators` and `/madeIraContributions` are aggregates over the filer rows
    (mapper.py: `EDUCATOR_OPTIONS`, and an `any(...)` for the IRA flag) -- the first is exactly
    invertible (one literal per (primary, spouse) pair), the second is lossy on a `true` (which
    filer said so cannot be recovered from one boolean) and is left unset then, an OPTIONAL field
    the mapper defaults false for anyway."""
    k12 = facts.get("/wasK12Educators")
    if k12 is not None:
        literal = k12["item"]["value"][0]
        if literal not in _EDUCATOR_OPTIONS_INVERSE:
            raise ProfileGap(f"/wasK12Educators: {literal!r} has no service k12_educator pair")
        primary_did, spouse_did = _EDUCATOR_OPTIONS_INVERSE[literal]
        for _, is_primary, person in filer_persons:
            person[EDUCATOR_FIELD] = primary_did if is_primary else spouse_did
            if person[EDUCATOR_FIELD]:
                # Required once k12_educator is true (mapper.py: "refused anywhere it is not").
                amount_fact = facts.get(_EDUCATOR_AMOUNT_PER_FILER[is_primary])
                if amount_fact is None:
                    raise ProfileGap(f"{_EDUCATOR_AMOUNT_PER_FILER[is_primary]}: required and "
                                      f"absent for an educator filer")
                person[EDUCATOR_AMOUNT_FIELD] = _value_of(
                    amount_fact, _EDUCATOR_AMOUNT_PER_FILER[is_primary])
    ira = facts.get("/madeIraContributions")
    if ira is not None and bool(ira["item"]) is False:
        for _, _, person in filer_persons:
            person[IRA_FIELD] = False
    elif ira is not None:
        attributed = False
        for _, is_primary, person in filer_persons:
            trad_fact = facts.get(_IRA_PER_FILER_TRAD[is_primary])
            roth_fact = facts.get(_IRA_PER_FILER_ROTH_ABLE[is_primary])
            if trad_fact is None and roth_fact is None:
                person[IRA_FIELD] = False
                continue
            attributed = True
            person[IRA_FIELD] = True
            # traditional_ira_contributions_cents, contributed_to_inherited_ira and
            # roth_ira_and_able_contributions_cents are ALL unconditionally required once this
            # row's made_ira_contributions is true (mapper.py `ira_questions_reached`). Recovered
            # from the matching per-filer engine fact when present; the engine's own $0/false
            # complete-safe reading otherwise (measured: profile-layoff-year's own filer answers
            # only the traditional amount, and no served line depends on the other two moving off
            # that default).
            person[IRA_AMOUNT_FIELD] = (_value_of(trad_fact, _IRA_PER_FILER_TRAD[is_primary])
                                         if trad_fact is not None else 0)
            person[IRA_ROTH_ABLE_FIELD] = (
                _value_of(roth_fact, _IRA_PER_FILER_ROTH_ABLE[is_primary])
                if roth_fact is not None else 0)
            inherited_fact = facts.get(_IRA_PER_FILER_INHERITED[is_primary])
            person[IRA_INHERITED_FIELD] = (bool(inherited_fact["item"])
                                            if inherited_fact is not None else False)
            # the amount behind an inherited yes, required there (`ira_questions_reached`);
            # recovered from the per-filer writable when the profile answers it.
            paid_fact = facts.get(_IRA_PER_FILER_INHERITED_AMOUNT[is_primary])
            if person[IRA_INHERITED_FIELD] and paid_fact is not None:
                person[IRA_INHERITED_AMOUNT_FIELD] = _value_of(
                    paid_fact, _IRA_PER_FILER_INHERITED_AMOUNT[is_primary])
        if not attributed:
            raise ProfileGap("/madeIraContributions: true, and which filer said so cannot be "
                              "recovered from this one aggregate boolean")
    # Form 8880 line 4 — two MORE root aggregates over the filer rows (mapper.py
    # `_savers_section`: `prior_any`/`after_any`, each an OR over every filer's own answer),
    # required once that filer's own IRA/HSA/W-2 contributions reach the savers-credit question
    # (`savers_questions_reached`). A FALSE aggregate is exactly invertible with no per-filer
    # amount needed — an OR of falses can only be every operand false — the same way the
    # combined K-12 pair is exact; only a TRUE aggregate is lossy the way `/madeIraContributions`
    # is, and is left to `ProfileGap` for the same reason.
    for engine_path, field in (("/hasDistributionsInLastThreeYears", "received_retirement_distributions_2023_2024"),
                                ("/hasCurrentYearDistributions", "received_retirement_distributions_after_year_end")):
        agg = facts.get(engine_path)
        if agg is None:
            continue
        if bool(agg["item"]) is False:
            for _, _, person in filer_persons:
                if person.get(IRA_FIELD) is True:
                    person[field] = False
        else:
            raise ProfileGap(f"{engine_path}: true, and which filer said so cannot be recovered "
                              f"from this one aggregate boolean")
    # Form 8889 Part I — a per-filer walk, not an aggregate (see `_apply_hsa_fields`),
    # recovered before the blanket default below so a filer who DOES carry HSA activity keeps it.
    _apply_hsa_fields(facts, filer_persons)
    # Every OTHER filer row answers no to this (measured: no showcase profile ever answers
    # `made_hsa_contributions` false explicitly either — it is the neutral default this service
    # asks on every return, per the K-12 pair's shape).
    for _, _, person in filer_persons:
        person.setdefault(HSA_CONTRIBUTIONS_FIELD, False)


def _hsa_amount(facts: dict, base: str, leaf: str) -> int:
    fact = facts.get(f"{base}/{leaf}")
    return _value_of(fact, f"{base}/{leaf}") if fact is not None else 0


def _apply_hsa_fields(facts: dict, filer_rows: list) -> None:
    """mapper.py's `_hsa_section` per-filer facts, inverted, one filer row at a
    time (never an aggregate — see the constants' own comment above).

    `made_hsa_contributions` is read off the ROLE-CONDITIONED leaf when the profile answers it
    directly; when it does not (measured: profile-hsa-partyear and profile-hsa-partyear-55plus
    carry the own-contribution DOLLAR amount but never answer this yes/no leaf at all — the
    pinned engine reads the amount alone), a positive own-contribution amount is what stands in
    for it, the same way an explicit 0 stands in for a no.

    The rest of Form 8889 Part I is REQUIRED the moment either this filer's own contribution or
    their W-2 box 12 code W is positive (mapper.py `hsa_questions_reached`) — so once contributions
    are recovered, `hsa_hdhp_coverage`, `hsa_hdhp_type` and `hsa_other_coverage` are recovered from
    the profile's own answers (one literal engine leaf shared by both filer rows), and
    `hsa_medicare` defaults to "none" when the chain reaches it but the profile never answers it at
    all (measured: no showcase profile ever carries `enrolledInMedicare`).

    The twelve-month coverage vector (`HSA_MONTH_FIELDS`) is required once coverage is
    "part_of_year": a genuine per-month answer is recovered verbatim (none exists in the showcase
    yet); a count-only legacy scalar (`writableHsaMonthsOfCoverage` — an engine fact
    `service_fields` names no field for at all) is reconstructed as that many months of the
    recovered type from January, the rest "none". Measured provably inert on both showcase
    profiles that carry it (profile-hsa-partyear, profile-hsa-partyear-55plus): the alternative
    placement (December-inclusive, which could invoke the last-month rule) computes the identical
    served lines, because the contribution is below the prorated base limitation either way — so
    which months are chosen never moves a served line."""
    for cid, is_primary, person in filer_rows:
        base = f"{FILER_ROOT}/#{cid}"
        made_leaf = ("writablePrimaryFilerHasMadeContributionsToHsa" if is_primary
                     else "writableSecondaryFilerHasMadeContributionsToHsa")
        made_fact = facts.get(f"{base}/{made_leaf}")
        own_cents = _hsa_amount(facts, base, "writableHsaNonemployerContributionsTaxYear")
        after_cents = _hsa_amount(facts, base, "writableHsaNonemployerContributionsTaxYearPlusOne")
        made = bool(made_fact["item"]) if made_fact is not None else (own_cents > 0 or after_cents > 0)

        # The 20%-tax exception pair — reached whenever THIS filer's own HSA
        # distributions are taxable above zero, independent of the contribution chain below (a
        # 1099-SA-only filer with no contribution activity still reaches it — measured:
        # profile-hsa-distribution). Both engine leaves are role-invariant.
        # `hsa_exception_reason` defaults to "none" when the profile answers the amount but not
        # the reason (measured: that profile's own amount is 0.00 — no part of the distribution
        # is exception-eligible, so which reason accompanies a zero amount is provably inert).
        exception_amount_fact = facts.get(f"{base}/writableHsaCollectionExceptionAmount")
        if exception_amount_fact is not None:
            person[HSA_EXCEPTION_AMOUNT_FIELD] = _value_of(
                exception_amount_fact, f"{base}/writableHsaCollectionExceptionAmount")
            reason_fact = facts.get(f"{base}/writableHsaCollectionExceptionReason")
            if reason_fact is not None:
                literal = reason_fact["item"]["value"][0]
                if literal not in _HSA_EXCEPTION_REASONS_INVERSE:
                    raise ProfileGap(f"{base}/writableHsaCollectionExceptionReason: {literal!r} "
                                      f"has no service {HSA_EXCEPTION_REASON_FIELD}")
                person[HSA_EXCEPTION_REASON_FIELD] = _HSA_EXCEPTION_REASONS_INVERSE[literal]
            else:
                person.setdefault(HSA_EXCEPTION_REASON_FIELD, "none")

        if not made:
            continue
        person[HSA_CONTRIBUTIONS_FIELD] = True
        person[HSA_OWN_AMOUNT_FIELD] = own_cents
        person[HSA_OWN_AFTER_FIELD] = after_cents

        for leaf, field, table in (
            ("hsaHdhpCoverageStatus", HSA_COVERAGE_FIELD, _HSA_YEAR_SPANS_INVERSE),
            ("typeOfHdhp", HSA_TYPE_FIELD, _HSA_HDHP_TYPES_INVERSE),
            ("hadOtherCoverageIneligibleForHSA", HSA_OTHER_COVERAGE_FIELD,
             _HSA_OTHER_COVERAGE_SPANS_INVERSE),
            ("enrolledInMedicare", HSA_MEDICARE_FIELD, _HSA_YEAR_SPANS_INVERSE),
        ):
            fact = facts.get(f"{base}/{leaf}")
            if fact is None:
                continue
            literal = fact["item"]["value"][0]
            if literal not in table:
                raise ProfileGap(f"{base}/{leaf}: {literal!r} has no service {field}")
            person[field] = table[literal]
        person.setdefault(HSA_MEDICARE_FIELD, "none")

        # Form 8889 line 3's marital-status question: an enum at this pin
        # (/changeInMaritalStatusDuringTaxYearOptions), a yes/no on the page
        marital_fact = facts.get(f"{base}/writableChangeInMaritalStatusDuringTaxYear")
        if marital_fact is not None:
            person["hsa_marital_status_changed"] = (
                marital_fact["item"]["value"][0] == "wasMarriedOrDivorcedThisYear")
        affects_fact = facts.get(f"{base}/writableMaritalChangeAffectContributionLimitBool")
        if affects_fact is not None:
            person["hsa_marital_change_affects_limit"] = bool(affects_fact["item"])

        funding_fact = facts.get(f"{base}/hasMadeQualifiedHsaFundingDistribution")
        if funding_fact is not None:
            person[HSA_FUNDING_FIELD] = bool(funding_fact["item"])

        if person.get(HSA_COVERAGE_FIELD) == "part_of_year":
            month_vector_present = any(f"{base}/writableHsaCoverageTypeMonth{m:02d}" in facts
                                       for m in range(1, 13))
            if not month_vector_present:
                count_fact = facts.get(f"{base}/writableHsaMonthsOfCoverage")
                if count_fact is None:
                    raise ProfileGap(f"{base}/writableHsaCoverageTypeMonth01..12: required and "
                                      f"absent (coverage is part_of_year) with no "
                                      f"writableHsaMonthsOfCoverage count to reconstruct it from")
                count = int(count_fact["item"])
                hdhp_type = person.get(HSA_TYPE_FIELD)
                if hdhp_type not in ("self_only", "family"):
                    raise ProfileGap(f"{base}/writableHsaMonthsOfCoverage: {count} months with no "
                                      f"single self_only/family type to fill them with")
                for i, mfield in enumerate(HSA_MONTH_FIELDS):
                    person[mfield] = hdhp_type if i < count else "none"


def _persons(facts: dict) -> tuple:
    """(persons list, filer cid -> index into that list) -- filers first (isPrimaryFiler true
    ahead of the spouse), any recovered dependents after."""
    filer_rows = _filer_rows(facts)
    _apply_combined_person_fields(facts, filer_rows)
    persons = [row[2] for row in filer_rows]
    cid_index = {row[0]: i for i, row in enumerate(filer_rows)}
    persons.extend(_dependents(facts))
    return persons, cid_index


# ---- item collections (w2s, r1099s, ...) --------------------------------------------------

def _group_roots(inv: dict) -> dict:
    """service group name -> its engine collection root path (e.g. "w2s" -> "/formW2s"), read
    off any `<group>[].field` entry's engine path rather than hand-listed, so a new mapped group
    is picked up the day `service_fields` names it."""
    # a group's fields may land in more than one engine collection —
    # `k1s[].section_199a_qbi_cents` is a `/qualifiedBusinesses` member, every other K-1 field a
    # `/formK1s` leaf — so the root is the collection MOST of the group's fields land in, never
    # whichever entry the mapping happened to list first.
    counts: dict = {}
    for engine_path, targets in inv.items():
        if "/*/" not in engine_path:
            continue
        prefix = engine_path.split("/*/", 1)[0]
        for field, _role in targets:
            if "[]." in field:
                group = field.split("[]", 1)[0]
                counts.setdefault(group, {}).setdefault(prefix, 0)
                counts[group][prefix] += 1
    return {group: max(by_prefix, key=by_prefix.get) for group, by_prefix in counts.items()}


# mapper.py's own K-1 entity-type literals (_K1_ENTITY = {"partnership": "partnership",
# "s_corp": "sCorp"}), inverted for k1s[].source. estate_trust never appears here: its K-1 goes
# through a wholly different collection (/form1041K1s, no `entityType` leaf at all — see
# mapper.py's `_map_k1s`), which this generic collection inverse never reaches.
_K1_SOURCE_INVERSE = {"partnership": "partnership", "sCorp": "s_corp"}

# mapper.py's HSA_CODES (Form 1099-SA box 3), inverted: the engine's own option literal ->
# the schema's printed-code string. Without this the generic passthrough forwarded the literal
# itself ("normalDistribution") straight into a field whose schema enum is "1".."6" (measured:
# profile-hsa-distribution's own OperationError).
_HSA_DISTRIBUTION_CODE_INVERSE = {
    "normalDistribution": "1", "excessContributions": "2", "disability": "3",
    "deathOtherThanCode6": "4", "prohibitedTransaction": "5", "deathDistributionAfterYear": "6",
}

# Which (group, field) pairs need a literal translation rather than the generic EnumWrapper
# passthrough — the `_DICT_FILING` lesson applied to a collection item's own field.
_COLLECTION_ENUM_TRANSLATORS = {
    ("k1s", "source"): _K1_SOURCE_INVERSE,
    ("hsa_distributions", "hsa_distribution_code"): _HSA_DISTRIBUTION_CODE_INVERSE,
}

# Every `<group>[]` schema in schema/common/facts/*.schema.json requires `person` EXCEPT
# care_providers (Form 2441 line 1 belongs to the return, not to either filer — no `person`
# property at all), `ssa_lump_sum_years` (an earlier-year worksheet row, not a document) and
# `f1095as` (out of this inverse's group machinery entirely — no `/*/` engine path is ever
# discovered for it). Checked directly against the schema files rather than derived from
# `service_fields`, which cannot see a `person` mapper.py validates but never emits anywhere
# (rentals — see `_collection_items` below).
_GROUPS_WITHOUT_PERSON = frozenset({"care_providers", "ssa_lump_sum_years", "f1095as"})

# One service field, two engine writables (schema/rename-table.json, `rentals[].property_type`):
# the printed Schedule E line 1b CODE, and the `selfRental` flag this service derives from the same
# answer so the code and the treatment cannot disagree. Read back the other way BOTH leaves land on
# the one field, and a profile carrying only the flag (measured: profile-self-rental has
# `/selfRental: true` and no code at all) turned `property_type` into the boolean `True`, which the
# mapper then refused by name — the profile could not be measured at all. Each leaf is translated to
# the field's own enum, and two leaves that disagree are a gap, not a last-one-wins.
_RENTAL_TYPE_FROM_CODE = {1: "residential", 4: "commercial", 5: "land", 7: "self_rental", 8: "other"}


def _rental_type_from_flag(value, path):
    if value is True:
        return "self_rental"
    return None                     # false or unanswered: the ordinary passive path, no answer


def _rental_type_from_code(value, path):
    try:
        return _RENTAL_TYPE_FROM_CODE[int(value)]
    except (KeyError, TypeError, ValueError):
        raise ProfileGap(f"{path}: {value!r} is not a Schedule E line 1b type this service carries")


_COLLECTION_LEAF_TRANSLATORS = {
    ("rentals", "/selfRental"): _rental_type_from_flag,
    ("rentals", "/writableLine1bPropertyTypeCode"): _rental_type_from_code,
}


def _collection_items(facts: dict, group: str, root_path: str, inv: dict,
                       filer_cid_index: dict) -> list:
    root = facts.get(root_path)
    if root is None:
        return []
    leaf_targets = {}                                         # "/leaf" -> [(field, role), ...]
    prefix = root_path + "/*"
    for engine_path, targets in inv.items():
        if not engine_path.startswith(prefix + "/"):
            continue
        leaf = engine_path[len(prefix):]                       # "/writableWages"
        leaf_targets[leaf] = [(f, r) for f, r in targets if f.startswith(group + "[].")]
    # Not every group's schema has a `person` field at all (care_providers does not — Form 2441
    # line 1 belongs to the RETURN, not to either filer) — `_GROUPS_WITHOUT_PERSON` names the
    # showcase exception. `service_fields` cannot answer this by itself: `rentals[].person` maps
    # nowhere in the mapper (mapper.py `_map_rentals`: "VALIDATED ... then maps nowhere"), so no
    # such key exists in `generated/reachability.json` even though rental.schema.json requires
    # `person` same as every other item group.
    group_has_person = group not in _GROUPS_WITHOUT_PERSON
    items = []
    for cid in root["item"]["items"]:
        base = f"{root_path}/#{cid}"
        item = {}
        for leaf, targets in leaf_targets.items():
            if not targets:
                continue
            path = base + leaf
            fact = facts.get(path)
            if fact is None:
                continue
            field = targets[0][0].split(".", 1)[1]
            if field == "person":
                if _type_of(fact) != "CollectionItemWrapper":
                    raise ProfileGap(f"{path}: expected a filer reference")
                filer_cid = fact["item"]["id"]
                if filer_cid not in filer_cid_index:
                    raise ProfileGap(f"{path}: references a filer this inverse did not recover")
                item["person"] = filer_cid_index[filer_cid]
                continue
            translator = _COLLECTION_LEAF_TRANSLATORS.get((group, leaf))
            if translator is not None:
                value = translator(_value_of(fact, path), path)
                if value is None:
                    continue
                if item.get(field, value) != value:
                    raise ProfileGap(f"{path}: says {value!r} where another box of this property "
                                      f"says {item[field]!r}")
                item[field] = value
                continue
            if _type_of(fact) == "EnumWrapper":
                literal = fact["item"]["value"][0]
                table = _COLLECTION_ENUM_TRANSLATORS.get((group, field))
                if table is None:
                    item[field] = literal                        # passthrough (no dedicated table)
                elif literal in table:
                    item[field] = table[literal]
                else:
                    raise ProfileGap(f"{path}: {literal!r} has no service {field}")
            else:
                item[field] = _value_of(fact, path)
        # A demo profile built directly against the engine routinely skips `/filer` on an item
        # collection the mapper always requires a `person` index for (measured: every K-1 profile
        # in the showcase). On a SINGLE real filer there is only one person this item could belong
        # to; on more than one, which filer is genuinely ambiguous without the reference.
        if group_has_person and "person" not in item:
            if len(filer_cid_index) == 1:
                item["person"] = 0
            else:
                raise ProfileGap(f"{base}/filer: absent, and which of {len(filer_cid_index)} "
                                  f"filers this {group} item belongs to cannot be recovered")
        items.append(item)
    return items


# ---- root scalars -------------------------------------------------------------------------

# /spouseLivedTogetherMonthsOptions -> the schema's months_lived_with_spouse
_SPOUSE_MONTHS_INVERSE = {"livedApartAllYear": "apart_all_year",
                          "livedTogetherMoreThanSixMonths": "more_than_six_months",
                          "livedTogetherSixMonthsOrLess": "six_months_or_less"}

_ROOT_ENUM_TRANSLATORS = {
    "filing_status": _DICT_FILING_INVERSE,
    "months_lived_with_spouse": _SPOUSE_MONTHS_INVERSE,
    "spouse_death_year": {"taxYearMinusOne": "last_year", "taxYearMinusTwo": "two_years_ago"},
    "estimated_payments_with_former_spouse": _ESTIMATED_PAYMENTS_FORMER_SPOUSE_INVERSE,
}

# mapper.py's own status gates (MARRIED_ROOT_FIELDS, MFS_ROOT_FIELDS, QSS_ROOT_FIELDS,
# MFJ_ROOT_FIELDS): each of these root fields is refused OUT_OF_COVERAGE when sent on a return
# whose filing_status does not reach it. A showcase profile's raw facts.json can carry one of
# these engine paths as boilerplate regardless of the actual status on that scenario (measured:
# profile-A, `single`, still carries `/livedTogetherAllYearWithSpouse`) — the generic root-scalar
# pass above has no filing_status context to gate on, so anything it recovers into one of these
# fields is dropped again here unless the status actually reaches it.
_MARRIED_ONLY_FIELDS = frozenset({"lived_with_spouse_all_year", "months_lived_with_spouse",
                                  "separation_agreement_on_last_day",
                                  "lived_apart_last_six_months"})
_MFS_ONLY_FIELDS = frozenset({"spouse_itemizes", "community_property_domicile",
                              "spouse_files_return", "spouse_had_gross_income",
                              "spouse_can_be_claimed", "spouse_65_or_older", "spouse_is_blind"})
_QSS_ONLY_FIELDS = frozenset({"spouse_death_year", "could_have_filed_jointly_year_of_death"})
_MFJ_ONLY_FIELDS = frozenset({"couple_required_to_file", "couple_files_only_for_refund",
                              "spouse_received_alaska_pfd"})


def _drop_status_mismatched_fields(out: dict) -> None:
    status = out.get("filing_status")
    if status not in ("mfj", "mfs"):
        for field in _MARRIED_ONLY_FIELDS:
            out.pop(field, None)
    if status != "mfs":
        for field in _MFS_ONLY_FIELDS:
            out.pop(field, None)
    if status != "qss":
        for field in _QSS_ONLY_FIELDS:
            out.pop(field, None)
    if status != "mfj":
        for field in _MFJ_ONLY_FIELDS:
            out.pop(field, None)


def _root_scalars(facts: dict, inv: dict) -> dict:
    out = {}
    for engine_path, targets in inv.items():
        if "/*/" in engine_path:
            continue
        fact = facts.get(engine_path)
        if fact is None:
            continue
        for field, _role in targets:
            if "[]" in field or field in out:
                continue
            if _type_of(fact) == "EnumWrapper":
                literal = fact["item"]["value"][0]
                table = _ROOT_ENUM_TRANSLATORS.get(field)
                if table is None:
                    out[field] = literal                        # passthrough
                elif literal in table:
                    out[field] = table[literal]
                else:
                    raise ProfileGap(f"{engine_path}: {literal!r} has no service {field}")
            else:
                out[field] = _value_of(fact, engine_path)
    return out


# ---- the public interface -----------------------------------------------------------------

# Engine paths this inverse has no service-field translation for AT ALL (no mapper emission
# reaches them; `generated/reachability.json` names no service field for them either) but which
# carry real income/adjustment dollars a silent skip would misrepresent as "the filer never had
# this" rather than "this service cannot yet ask about it". Checked before anything else so a
# profile carrying one of these fails LOUD (a ProfileGap naming the path) instead of quietly
# rendering a wrong COMPLETE return.

# `/writableAlimonyReceivedAmount` and `/writableAlimonyPaidAmount` LEFT THIS TUPLE:
# `alimony_received_cents`/`alimony_paid_cents` are now root service fields
# (`schema/rename-table.json`), so `_root_scalars`'s generic join recovers them like any other
# root scalar — no special-casing needed here. profile-alimony now round-trips
# (tests/test_intake_profiles.py's `must_pass`).

# `/writableMainHomeInUsOverHalfYear` LEFT THIS TUPLE TOO: `main_home_in_us_over_half_year`
# is now a root service field (`schema/rename-table.json`), recovered the same generic way.
# profile-eitc-main-home now round-trips (tests/test_intake_profiles.py's `must_pass`).
_UNMAPPED_INCOME_PATHS = (
    # Form 4684 casualty/theft losses (a federally declared disaster or otherwise): a whole
    # collection (`/casualtyEvents`) with no service group at all — mapper.py has no
    # `_map_casualty_events`, `generated/reachability.json` names no service field for any of its
    # leaves, and `schema/common/facts/*.schema.json` carries no matching group. Checked on the
    # collection itself rather than the root `/hasCasualtyLoss` marker (measured: both are present
    # together on profile-qualified-disaster-loss, but the collection is the one a mapper/schema
    # addition would actually need to carry).
    "/casualtyEvents",
    # Two CREDITS the fact schema has no field for at either pin (rows on 2026-09-19): the
    # American opportunity credit's expenses and Form 1116's foreign tax paid. They were skipped in
    # silence — and at an earlier pin that cost nothing visible, because the old snapshot's own
    # oracle lacked the rows the engine needs before it grants either credit, so both sides
    # agreed on the uncredited figure. Verify's re-snapshot answers those
    # rows; the oracle now credits, and a silent skip here is exactly the wrong COMPLETE return
    # this tuple exists to prevent. (The lifetime learning credit is NOT here: the
    # typed lines carry `/writableLlcQualifiedExpenses`.)
    "/writableAotcQualifiedExpenses",
    "/writableForeignTaxPaid",
)


def _check_unmapped_income(facts: dict) -> None:
    for path in _UNMAPPED_INCOME_PATHS:
        if path in facts:
            raise ProfileGap(f"{path}: no service field maps this engine path (needs a mapper "
                              f"and schema addition, not an inversion)")
    # qbi.xml `/hasQbiIncome`: "An explicit answer... wins (including an explicit FALSE, which
    # suppresses both auto-enable arms)". No service field names it and the mapper never emits
    # it. A K-1's section 199A statement amount IS asked (`section_199a_qbi_cents`)
    # and becomes a `/qualifiedBusinesses` member, so the auto-enable arm admits it; what a
    # profile answering this root still carries that no service field does is the Form 8995-A
    # Part II detail beside its members (W-2 wages, property basis, the specified-service flag)
    # — measured on profile-qbi-8995a, whose one member carries all three.
    qbi_fact = facts.get("/hasQbiIncome")
    if qbi_fact is not None and bool(qbi_fact["item"]) is True:
        raise ProfileGap("/hasQbiIncome: true, and this profile's qualified businesses carry "
                          "Form 8995-A Part II detail (W-2 wages, property basis) that no "
                          "service field carries — a K-1's section 199A statement amount is "
                          "asked since the per-business limitation is not (needs a "
                          "mapper and schema addition, not an inversion)")


# The legacy scalar IRA-distribution intake (mapper.py's own dictionary comment,
# form1099Rs.xml "/knockoutIraSepSimple": "the ordinary IRA distribution now computes ... from the
# collection ... so what survives is the residue"). `/writableIraDistributionAmount` and
# `/writableEarlyDistributionsIncludible` are a demo-era alternative to the `/formK1s`-style
# `/form1099Rs` collection this mapper actually emits through — no service field names either
# scalar, and none ever will (form1099Rs.xml calls the scalar route legacy beside the
# collection route it retired toward). The dollars they carry are real, though, and the SAME
# dollars a `/form1099Rs` item with a matching box 7 code produces (measured: profile-ira-
# distribution round-trips cent-exact this way). Recovered as one r1099s item, never silently
# dropped.
def _legacy_ira_scalar_r1099(facts: dict, filer_cid_index: dict) -> dict | None:
    scalar = facts.get("/writableIraDistributionAmount")
    if scalar is None:
        return None
    if facts.get("/form1099Rs", {}).get("item", {}).get("items"):
        raise ProfileGap("/writableIraDistributionAmount: present beside a populated /form1099Rs "
                          "collection — the engine's own double-intake knockout "
                          "(/knockoutIraDistributionDoubleIntake), not a single r1099s item this "
                          "inverse can build")
    cents = _value_of(scalar, "/writableIraDistributionAmount")
    code = "7"
    early = facts.get("/writableEarlyDistributionsIncludible")
    if early is not None:
        early_cents = _value_of(early, "/writableEarlyDistributionsIncludible")
        if early_cents != cents:
            raise ProfileGap("/writableEarlyDistributionsIncludible: partly early, partly not — "
                              "this inverse only recovers a distribution that is entirely one or "
                              "the other")
        code = "1"                                # Form 5329 Part I: fully early, no exception
    if len(filer_cid_index) != 1:
        raise ProfileGap("/writableIraDistributionAmount: not a per-filer fact, and which of "
                          f"{len(filer_cid_index)} filers it belongs to cannot be recovered")
    return {
        "person": 0,
        "gross_distribution_cents": cents,
        "taxable_amount_cents": cents,
        "distribution_code": code,
        "ira_sep_simple": True,
        "rolled_over_cents": 0,
    }


# mapper.py requires BOTH of these on every PARTNERSHIP k1s[] item (`_map_k1s`: "publicly_traded_
# partnership" via `/formK1sItemDIsComplete`'s guard; "general_partner", FactsSchemaError at
# `_map_k1s` line ~4388) — never on an s_corp item, which prints neither box. Every K-1 profile in
# the showcase omits both engine facts entirely (measured across all four showcase K-1 profiles).
# The pinned dictionary's own complete-safe reading of "unanswered" is what these two defaults
# reproduce, not a taxpayer answer this service invented:
#   * item G (writablePartnerIsGeneralPartner): "OPTIONAL writable; use the complete-safe
#     ../partnerIsGeneralPartner downstream" (scheduleE.xml) — false (limited partner).
#   * item D (writableIsPubliclyTradedPartnership): false is what a profile with no PTP box-20
#     code Z income and no item-D-gated line ever needed answered (measured: every showcase K-1
#     profile's own served lines are unchanged by this default — none carries a code Z amount).
def _apply_k1_defaults(items: list) -> None:
    for item in items:
        if item.get("source") != "partnership":
            continue
        item.setdefault("publicly_traded_partnership", False)
        item.setdefault("general_partner", False)


# The estate/trust K-1 SCALAR intake (`/writableEstateTrustK1Income`, beside
# `/writableHasEstateTrustK1` and `/writableEstateTrustK1MateriallyParticipated`) — a THIRD K-1
# shape beside `/formK1s` (partnership/s_corp) and the schema's own `k1s[].source == "estate_trust"`
# route (`/form1041K1s`, mapper.py's `_map_k1s`). Every showcase estate/trust profile uses this
# scalar route, never `/form1041K1s`.

# A NON-NEGATIVE box 6 amount round-trips cent-exact through the `k1s[].source == "estate_trust"`
# route (measured: profile-estate-trust — `ordinary_business_income_cents` set to this scalar's own
# figure reaches the identical served lines). `person` is validated by the mapper and then "maps
# nowhere" (`_map_k1s`'s own comment: Part III sums over every item regardless of whose it is), so
# any valid filer index does — there is always at least one (`_filer_rows` itself requires it).

# A NEGATIVE amount does not round-trip: mapper.py refuses a `k1_has_box1_loss` estate_trust item
# by name ("it would deduct as entered, and the passive-activity classification that would limit
# it is not asked" — k1.schema.json's own words), measured here on profile-estate-atrisk and
# profile-self-rental (both refused). A loss stays a `ProfileGap` naming the scalar path, never
# guessed into a route the mapper itself would refuse.
def _legacy_estate_trust_k1(facts: dict) -> dict | None:
    scalar = facts.get("/writableEstateTrustK1Income")
    if scalar is None:
        return None
    cents = _value_of(scalar, "/writableEstateTrustK1Income")
    item = {"source": "estate_trust", "person": 0, "ordinary_business_income_cents": cents}
    if cents < 0:
        # 2026-09-22: a LOSS round-trips now. The passive-activity answer the mapper asks for is
        # the SAME return-level fact this scalar route carries, so it is recovered rather than
        # guessed; absent, the mapper's own ask stands and the profile stops there by name.
        answer = facts.get("/writableEstateTrustK1MateriallyParticipated")
        if answer is None:
            raise ProfileGap(
                "/writableEstateTrustK1MateriallyParticipated: a box 6 LOSS is allowed or "
                "suspended by this answer, and this profile carries no answer to it; the mapper "
                "asks for it rather than deducting the loss as entered")
        item["materially_participated"] = bool(_value_of(answer, "/writableEstateTrustK1MateriallyParticipated"))
        at_risk = facts.get("/writableEstateTrustFullyAtRisk")
        # A profile that answers this carries the answer; one that does not is a household whose
        # whole investment IS at risk, which is what the engine computes from the absence — so the
        # inverse says so rather than leaving the service's own question unanswerable.
        item["fully_at_risk"] = (True if at_risk is None
                                 else bool(_value_of(at_risk, "/writableEstateTrustFullyAtRisk")))
        amount = facts.get("/writableEstateTrustAmountAtRisk")
        if not item["fully_at_risk"] and amount is not None:
            item["amount_at_risk_cents"] = _value_of(amount, "/writableEstateTrustAmountAtRisk")
    return item


# mapper.py's `_map_care_providers` derives BOTH the organization flag and the tax-exempt flag
# from ONE service field (`provider_type`); `generated/reachability.json` names only
# `/writableIsOrganization` for it, so the generic collection inverse above (`_collection_items`)
# would read that single BooleanWrapper and set the field to a raw True/False rather than the
# schema's three-way enum. Recomputed here from BOTH raw dictionary facts, mirroring
# `_map_care_providers`'s own `organization = kind != "individual"` /
# `writableIsTaxExempt = (kind == "tax_exempt_organization")` split in reverse.
def _w2_employer_refs(facts: dict, root_path: str, ids: list, items: list) -> None:
    """`w2s[].employer_ref` from each Form W-2's own EIN: the same EIN is the same employer.

    The page asks which employer each of a person's W-2s is from (the excess Social Security
    withholding credit turns on it), and the mapper turns `employer_ref` back into one synthetic
    EIN per employer — so a dense ordinal over the profile's EINs, in first-appearance order,
    reproduces exactly the grouping the profile's own facts make. A W-2 with no EIN keeps no ref."""
    ordinals: dict = {}
    for cid, item in zip(ids, items):
        fact = facts.get(f"{root_path}/#{cid}/ein")
        if fact is None:
            continue
        ein = fact["item"]
        key = (ein.get("prefix"), ein.get("serial")) if isinstance(ein, dict) else ein
        item["employer_ref"] = ordinals.setdefault(key, len(ordinals))


def _fix_care_provider_types(facts: dict, root_path: str, ids: list, items: list) -> None:
    for cid, item in zip(ids, items):
        base = f"{root_path}/#{cid}"
        # cdcc.xml's own writable description: "UNANSWERED IS THE NORMAL STATE, NOT AN ERROR ...
        # this writable is Incomplete on every existing return and ../isHouseholdEmployee falls
        # back to its shipping mirror" (false) — no showcase profile ever answers it (this
        # application owns this intake, the same comment notes). False is the engine's own complete-safe reading,
        # not a guess, and this service's stricter REQUIRED gate needs an explicit value to send.
        item.setdefault("is_household_employee", False)
        is_org = facts.get(f"{base}/writableIsOrganization")
        if is_org is None:
            raise ProfileGap(f"{base}/writableIsOrganization: required and absent")
        if not bool(is_org["item"]):
            item["provider_type"] = "individual"
            continue
        tax_exempt = facts.get(f"{base}/writableIsTaxExempt")
        item["provider_type"] = ("tax_exempt_organization"
                                  if tax_exempt is not None and bool(tax_exempt["item"])
                                  else "organization")


# mapper.py's SSA_FORM_TYPE_LEAVES: which sibling leaf a report's amount is filed under decides
# `form_type` — no engine fact states the enum directly (`/writableFormType` is itself OPTIONAL,
# read through the complete-safe `../formType` downstream, per socialSecurity.xml's own writable
# description), so a profile that never answers it (measured: every showcase SSA profile) is read
# off WHICH of the two leaf shapes it actually used instead of guessed.
_SSA_FORM_TYPE_LEAF = {"ssaNetBenefits": "ssa_1099", "rrbNetBenefits": "rrb_1099"}


def _fix_ssa_form_types(facts: dict, root_path: str, ids: list, items: list) -> None:
    for cid, item in zip(ids, items):
        base = f"{root_path}/#{cid}"
        for leaf, form_type in _SSA_FORM_TYPE_LEAF.items():
            if facts.get(f"{base}/{leaf}") is not None:
                item["form_type"] = form_type
                break
        else:
            raise ProfileGap(f"{base}: neither ssaNetBenefits nor rrbNetBenefits present — "
                              f"form_type cannot be recovered")


def service_facts(engine_doc: dict, tax_year: int = 2025) -> dict:
    """A showcase profile's own engine-shaped `facts.json` -> the service fact set a scripted
    person answering from it would have produced. Never guesses: an engine path this inverse
    cannot express raises `ProfileGap` naming it."""
    facts = engine_doc["facts"]
    _check_unmapped_income(facts)
    inv = _service_fields_inverse()
    out = _root_scalars(facts, inv)
    if "filing_status" not in out:
        raise ProfileGap("/filingStatus: required and absent")
    _drop_status_mismatched_fields(out)
    persons, cid_index = _persons(facts)
    out["persons"] = persons
    for group, root_path in _group_roots(inv).items():
        # "persons" is a false group: several `persons[].field` entries in `service_fields` share
        # the group-splitting `persons[].` prefix `_group_roots` keys on, but `persons` is not a
        # collection this generic machinery can build — it is `_persons()`'s own filers-then-
        # dependents list, already assigned above. Building it here too, from whichever ONE root
        # path `_group_roots` happens to land on, would silently replace that list (measured: with
        # `/familyAndHousehold` as the discovered root, a return with claimed dependents had its
        # real persons list — role, birth_year, tin_type, everything `_persons()` built — stomped
        # by a garbage two-field-per-item list built from unrelated `persons[]` leaf names).
        if group == "persons":
            continue
        items = _collection_items(facts, group, root_path, inv, cid_index)
        if group == "r1099s":
            for item in items:
                # the indirect-rollover amount, asked on every R1099 the rollover chain
                # reaches — absent from a profile built outside this service's conversation the
                # same way the credit-history/HSA fields are (module docstring); 0 is the neutral
                # "no rollover" answer, and every profile's own `writableIsIndirectRollover` is
                # false where this fires (measured).
                item.setdefault("rolled_over_cents", 0)
            legacy = _legacy_ira_scalar_r1099(facts, cid_index)
            if legacy is not None:
                items.append(legacy)
        elif group == "k1s":
            _apply_k1_defaults(items)
            legacy_k1 = _legacy_estate_trust_k1(facts)
            if legacy_k1 is not None:
                items.append(legacy_k1)
        elif group == "care_providers":
            root = facts.get(root_path)
            ids = root["item"]["items"] if root is not None else []
            _fix_care_provider_types(facts, root_path, ids, items)
        elif group == "ssa1099s":
            root = facts.get(root_path)
            ids = root["item"]["items"] if root is not None else []
            _fix_ssa_form_types(facts, root_path, ids, items)
        elif group == "w2s":
            root = facts.get(root_path)
            ids = root["item"]["items"] if root is not None else []
            _w2_employer_refs(facts, root_path, ids, items)
        if items:
            out[group] = items
    # no showcase profile's facts say whether a K-1's business income is section 199A
    # qualified business income. A profile with no `/qualifiedBusinesses`
    # computes no deduction on it, which is what 0 reproduces — read as that, until the profiles
    # say otherwise. After every group is built: a loss K-1 is asked only beside a Schedule C.
    for i in mapper.section_199a_asked(out):
        out["k1s"][i].setdefault("section_199a_qbi_cents", 0)
    if out.get("filing_status") == "mfj":
        out.setdefault("spouse_received_alaska_pfd", False)
    if out.get("filing_status") == "qss":
        # the qualifying-surviving-spouse questions, read off the profile (no rename-table row
        # names them, so the generic root pass does not)
        year = facts.get("/yearOfSpouseDeath")
        if year is not None:
            literal = year["item"]["value"][0]
            table = _ROOT_ENUM_TRANSLATORS["spouse_death_year"]
            if literal not in table:
                raise ProfileGap(f"/yearOfSpouseDeath: {literal!r} has no service spouse_death_year")
            out.setdefault("spouse_death_year", table[literal])
        jointly = facts.get("/canFileJointlyYearOfSpouseDeath")
        if jointly is not None:
            out.setdefault("could_have_filed_jointly_year_of_death", bool(jointly["item"]))

    if "ssa1099s" in out:
        # No `/socialSecurityLumpSumEarlierYears` item and no `/writableSocialSecurityLumpSumElection`
        # answer exists on any showcase SSA profile (measured): there is no earlier-year figure
        # anywhere in the engine facts a True election would need, so False (the regular method)
        # is the only value consistent with what the profile actually carries.
        out.setdefault("elects_lump_sum_benefits", False)
    for field, default in _CREDIT_HISTORY_DEFAULTS.items():
        out.setdefault(field, default)
    return out


def oracle_lines(engine_doc: dict, engine_home=None) -> dict:
    """The pinned engine, resolving the profile's OWN facts.json directly (no mapper, no
    service) -> {"11": "75240.00", ...} for every served line (`LINE_MAP`) that resolves
    Complete or Placeholder — the same keep-rule `service.operations._cited_lines` uses, so the
    two views of "the served lines" cannot silently disagree about which lines that is."""
    adapter = EngineAdapter(engine_home=engine_home)
    tsv = adapter.resolve_facts(engine_doc)
    resolved = _parse_resolved(tsv)
    lines = {}
    for spec in LINE_MAP:
        entry = resolved.get(spec["fact_path"])
        if entry is not None and entry[0] in ("Complete", "Placeholder"):
            lines[spec["line_id"]] = entry[2]
    return lines
