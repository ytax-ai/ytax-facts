# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Map derivative-only service facts -> engine persister-format facts (Phase 0, ty2025).

Deterministic and identifier-free on the way in: the caller passes only computational derivatives
(tin_type, birth_year/month, integer cents). The mapper synthesizes the placeholder identifiers the
engine requires (a structurally-valid synthetic TIN of the requested type; a dateOfBirth with a
fixed placeholder day) purely inside the returned fact set, which is fed straight to the engine and
never stored. UUIDs are assigned deterministically from item order so the same input yields the same
fact set (idempotent — supports the same-input_hash => byte-identical contract).

Resolved coverage (connectable slice): SINGLE-filer W-2 wages and, since Form W-2G gambling
winnings and withholding, cent-exact. Everything else — other filing statuses, dependents, and the
remaining income streams — raises ServiceFactsError (honest refusal,
not a silent wrong number) until the scaffolding that makes each amount FLOW into the return is
completed. (The rename table in schema/rename-table.json maps more fields than are resolved here;
mapping a field is necessary but not sufficient — the engine flow must be proven cent-exact first.)
"""
from __future__ import annotations

import re as _re                                       # the percentage shape
import datetime as _dt                                 # box 13's date

CENTS = 100


class ServiceFactsError(ValueError):
    """A fact set the Phase-0 mapper cannot faithfully express (out of the covered set)."""


class FactsSchemaError(ServiceFactsError):
    """The request does not conform to the fact schema — a required field missing, or a field of the
    wrong type. A CALLER fault, not a boundary.

    Separate from its parent because the two mean opposite things to whoever reads the error.
    `OUT_OF_COVERAGE` says *this service can never do this*; a forgotten field says *send it again
    with the field*. Reporting the second as the first is the misreport once fixed for engine
    timeouts, where a JVM crash told a preparer their return was permanently unsupported.

    It SUBCLASSES `ServiceFactsError` so every existing `except` clause keeps working; only the
    callers that care about the distinction have to name it."""


# ---- persister wrappers ---------------------------------------------------------------------

def _bool(v):    return {"$type": "gov.irs.factgraph.persisters.BooleanWrapper", "item": bool(v)}
def _str(v):     return {"$type": "gov.irs.factgraph.persisters.StringWrapper", "item": v}
def _dollar(c):  return {"$type": "gov.irs.factgraph.persisters.DollarWrapper", "item": _money(c)}
def _day(d):     return {"$type": "gov.irs.factgraph.persisters.DayWrapper", "item": {"date": d}}
def _int_wrap(v): return {"$type": "gov.irs.factgraph.persisters.IntWrapper", "item": int(v)}
def _enum(path, val):
    return {"$type": "gov.irs.factgraph.persisters.EnumWrapper",
            "item": {"enumOptionsPath": path, "value": [val]}}
def _collection(ids):
    return {"$type": "gov.irs.factgraph.persisters.CollectionWrapper", "item": {"items": ids}}
def _collection_item(cid):
    return {"$type": "gov.irs.factgraph.persisters.CollectionItemWrapper", "item": {"id": cid}}
def _tin(area, group, serial):
    return {"$type": "gov.irs.factgraph.persisters.TinWrapper",
            "item": {"area": area, "group": group, "serial": serial}}
def _ein(prefix, serial):
    return {"$type": "gov.irs.factgraph.persisters.EinWrapper",
            "item": {"prefix": prefix, "serial": serial}}


def _money(cents: int) -> str:
    if not isinstance(cents, int):
        # state the rule, never echo the submitted value — served messages can reach logs,
        # and a fact value in a log line is exactly what the privacy contract forbids.
        raise ServiceFactsError("money must be integer cents")
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // CENTS}.{cents % CENTS:02d}"


# Deterministic UUIDs from a prefix + index (no randomness — idempotent fact sets).
def _uuid(prefix_hex: str, i: int) -> str:
    p = prefix_hex[0]
    return f"{p}{i:07x}-0000-4000-8000-{i:012x}"


# Synthetic placeholder TINs by type — PLACEHOLDERS carrying the TYPE the engine needs, never a
# real identifier. REVISED with dependents coverage, measured at the pin: the child
# tax credit reads the SSN SHAPE (`tin/isSSN`), and a 900-area TIN reads as an ITIN — so the
# SSN types now use area 899 GROUP 00, which the SSA has never issued (still an impossible real
# SSN) yet reads as an SSN engine-side. ITIN/ATIN deliberately KEEP the 900 range: they must go
# on reading as what they are. The serial is PER PERSON (the index), because dependent
# eligibility requires TIN uniqueness (`isTinUnique`) — a fixed per-type serial made an mfj
# couple share a TIN, survivable only while nothing compared them.
_SYNTH_TIN = {
    "ssn_valid_for_employment": ("899", "00"),
    "ssn_other":                ("899", "00"),
    "ssn_dhs_authorization":    ("899", "00"),
    "ssn_dhs_authorization_expired": ("899", "00"),
    "itin":                     ("900", "70"),
    "atin":                     ("900", "93"),
    "none":                     ("899", "00"),
}


def _synth_tin(tin_type: str, person_index: int):
    area, group = _SYNTH_TIN[tin_type]
    return _tin(area, group, f"{person_index + 1:04d}")

# ---- the covered set, declared once ------------------------------------------------------------
# These constants ARE the boundary: `map_to_engine` enforces them and the `coverage` operation
# derives its answer from them (src/ytax_prep/service/coverage.py), so the published
# boundary cannot drift from the enforced one. `tests/test_coverage_derivation.py` locks it in
# every direction: the three sets must PARTITION the fact schema's groups (union equal, pairwise
# disjoint), so a schema addition nothing here handles fails the gate instead of being silently
# ignored; and COVERED_FACT_GROUPS is not a hand-kept list — an income group counts as covered only
# when a real mapper function exists for it (`_INCOME_MAPPERS` below), so a group cannot be
# promoted to "covered" without the code that actually maps it.

FILING_STATUSES = frozenset({"single", "mfj", "mfs", "hoh", "qss"})
# Connectable slice: `single` and, since its coverage, `mfj` (two filers, married) are proven
# cent-exact against the pinned engine. mfs/hoh/qss still need spouse-variant / dependent /
# dependent scaffolding not yet complete — refuse rather than under-resolve (World #1).
# ALL FIVE since hoh/qss coverage — FILING_STATUSES == COVERED_FILING_STATUSES, every
# status covered. The refusal branch stays (demote-and-simulate tests
# keep it measured) for any future uncovered status.
COVERED_FILING_STATUSES = frozenset({"single", "mfj", "mfs", "hoh", "qss"})

# Every fact group the schema defines -> the label the boundary is published under. One label per
# group, whichever side of the boundary it is on, so the covered and refused lists cannot describe
# the same group two different ways.
# Form W-2 box 10 and Form 2441 Part III — the field names (the measurements and the
# predicates sit with `dcb_person_questions_reached`).
W2_BOX10_FIELD = "dependent_care_benefits_cents"
DCB_PLAN_MAX_FIELD = "dependent_care_plan_maximum_cents"
DCB_SELF_EMPLOYED_FIELD = "self_employed_dependent_care_benefits_cents"
DCB_PERSON_FIELDS = (DCB_SELF_EMPLOYED_FIELD, DCB_PLAN_MAX_FIELD)
DCB_CARRYOVER_FIELD = "dependent_care_carryover_cents"
DCB_FORFEITED_FIELD = "dependent_care_forfeited_cents"
DCB_ROOT_FIELDS = frozenset({DCB_CARRYOVER_FIELD, DCB_FORFEITED_FIELD})

# Form W-2 box 12. One cents field per code the 2025 form lists, each 1:1 with the
# dictionary's writable for that code. Measured at the pin (wages-single-mid, each code at 100):
# A, B, M and N are Schedule 2 line 13 — line 24 up by their sum, 34 down by it, 33 and 25d
# unchanged, no knockout (box 14's RRTA regime split is handled apart); J, K, L, P, R, T, Z, F and II
# fire the dictionary's own /knockoutForBox12Value (K computes the excise tax AND knocks out);
# C, V, Y, DD, FF, GG and HH move nothing and reach nothing (the DAG agrees); D, E, G, H, S, AA,
# BB and EE reach the retirement savings contributions credit (Form 8880 — 20% of 2,000 at
# 25,000 of wages, measured; G needs the governmental-plan answer too) — CARRIED since the
# route's own questions asked; W the Form 8889 contribution chain, Q the earned income election
# — routes this service has not built, so each is refused by name rather than computed as if
# the box were blank.
# /formW2s/*/writableHasBox12Codes is a flow variable: code A moves line 24 without it
# (measured), so it is never sent.
# Form 8880, the retirement savings contributions credit (Schedule 3 line 4). Measured at the
# pin (wages-single-low, wages 25,000, line 24 = 928.00): a box 12 deferral of 2,000 (D, E, G with
# a governmental plan, H, S, AA, BB, EE) or 2,000 of IRA and ABLE contributions through the
# self-reported pair gives the 20% credit, 400 (528.00); the covered traditional IRA writable
# feeds the deduction and NOT the credit (AGI 23,000, credit 0 — a 1,000 credit missed in
# silence until now); a 2023 distribution of 1,000 halves the base (728.00), a post-year-end one
# of 500 takes 100 off (628.00); the section serves the credit with the distribution questions
# UNANSWERED (the favourable silence), so they are asked as required gaps; on a joint return a
# 2023 distribution with the filed-jointly answer absent zeroes the credit (measured), so that
# pair is asked; a spouse's distribution counts against the primary only if they filed jointly
# that year (200 / 400). Eligibility is the dictionary's: not a student, 18 or older on
# December 31, not claimed as a dependent, AGI under the limit (single 39,500; 50% / 20% / 10%
# at 23,750 / 25,500). The student answer is the first question the route reaches — unasked, a
# student filer's default of "not a student" hands them the credit. The January-of-boundary
# cohort (born January of tax_year − 17: by the dictionary's day-before-birthday rule, born
# January 1 they are 18 on December 31, born January 2-31 they are 17) is refused with
# contributions: the synthesized day 01 makes the whole cohort 18 when 30/31 of it is 17
# (measured: 2008-01 → 400, 2008-02 → 0, 2007-12 → 400).
SAVERS_AGE = 18
SAVERS_STUDENT_FIELD = "is_student"
SAVERS_DIST_PRIOR_FIELD = "received_retirement_distributions_2023_2024"
SAVERS_DIST_2023_FIELD = "retirement_distributions_2023_cents"
SAVERS_DIST_2024_FIELD = "retirement_distributions_2024_cents"
SAVERS_DIST_AFTER_FIELD = "received_retirement_distributions_after_year_end"
SAVERS_DIST_AFTER_AMOUNT_FIELD = "retirement_distributions_after_year_end_cents"
SAVERS_PERSON_FIELDS = (SAVERS_DIST_PRIOR_FIELD, SAVERS_DIST_2023_FIELD, SAVERS_DIST_2024_FIELD,
                        SAVERS_DIST_AFTER_FIELD, SAVERS_DIST_AFTER_AMOUNT_FIELD)
SAVERS_ROOT_EMISSION = {"filed_jointly_2023": "/writableFiledJointReturnFor2023",
                        "filed_jointly_2024": "/writableFiledJointReturnFor2024"}
SAVERS_ROOT_FIELDS = frozenset(SAVERS_ROOT_EMISSION)
W2_BOX12_G_PLAN_FIELD = "box12_g_governmental_plan"
# W-2 box 12 code W — employer HSA contributions, Form 8889 Part I. Measured at the pin:
# sent with the coverage questions unanswered the section is a Placeholder and the return
# completes as if within the limit whatever the amount (9,000 against a 4,300 limit moved
# nothing); answered, the excess over the line 8 limit is Schedule 1 line 8z other income and a
# 6% Form 5329 excise (5,000 self-only: 700 + 42, line 24 928.00 → 1,040.00). The questions,
# in the dictionary's own gate order (each later one is reached only on the path the earlier
# answers leave open; every other answer is the dictionary's own knockout, served with words).
W2_BOX12_W_FIELD = "box12_w_cents"
HSA_MEDICARE_FIELD = "hsa_medicare"                       # enrolledInMedicare
HSA_COVERAGE_FIELD = "hsa_hdhp_coverage"                  # hsaHdhpCoverageStatus
HSA_TYPE_FIELD = "hsa_hdhp_type"                          # typeOfHdhp
HSA_OTHER_COVERAGE_FIELD = "hsa_other_coverage"           # hadOtherCoverageIneligibleForHSA
HSA_FUNDING_FIELD = "hsa_funding_distribution"            # hasMadeQualifiedHsaFundingDistribution
HSA_SPOUSE_CONTRIBUTED_FIELD = "hsa_spouse_contributed"   # writableMfsLine6Check (mfs, family)
HSA_MARITAL_CHANGED_FIELD = "hsa_marital_status_changed"  # writableChangeInMaritalStatusDuringTaxYear
HSA_MARITAL_AFFECTS_FIELD = "hsa_marital_change_affects_limit"   # writableMaritalChangeAffectContributionLimitBool
# the qualified HSA funding distribution (an IRA-to-HSA trustee transfer) is carried: its
# amount on the IRA Form 1099-R that reports it (the dictionary's line 4c election `hfd` with
# `writableHfdAmount`), and the once-per-lifetime election asked of the filer.
R1099_HFD_FIELD = "qualified_hsa_funding_distribution_cents"      # /form1099Rs/*/writableHfdAmount
HSA_PRIOR_HFD_FIELD = "hsa_prior_funding_distribution_election"   # /{primary,secondary}FilerHasPriorLifetimeHfdElection
# the qualified charitable distribution on an IRA Form 1099-R — the trustee paid the
# distribution directly to a charity (Form 1040 instructions, lines 4a and 4b, Exception 3). The
# dictionary computes it from the line 4c election `qcd`, the amount, the split-interest answer
# (false computes; a yes is its own knockout) and the filer's post-70½ deducted-contribution
# history (Pub 590-B Appendix D line 1; answered, never defaulted). Measured through the mapper
# (wages-single-low, filer born 1950, an IRA 1099-R of 10,000 with code 7 and box 2a 10,000):
# 10,000 to a charity 1,128.00 → 126.00 (line 4b 0); 4,000 of it → 728.00; a history of 1,000
# → 226.00; two forms with a QCD each and a history of 0 compute, with a positive history the
# dictionary refuses both (the offset lands on one form only).
R1099_BOX8_AMOUNT_FIELD = "other_cents"                         # /form1099Rs/*/writableOtherDollar
R1099_BOX8_PERCENT_FIELD = "other_percentage"                   # /form1099Rs/*/writableOtherPercentage
R1099_BOX9A_FIELD = "percentage_of_total_distribution"          # /form1099Rs/*/writablePercentageTotalDistribution
R1099_BOX_FIELDS = (R1099_BOX8_AMOUNT_FIELD, R1099_BOX8_PERCENT_FIELD, R1099_BOX9A_FIELD)
_R1099_PERCENT_SHAPE = _re.compile(r"^(100(\.0{1,3})?|[0-9]{1,2}(\.[0-9]{1,3})?)$")   # the dictionary's Match limit
# IRC 402(l) — an eligible retired public safety officer excludes up to 3,000 of the premiums
# their government plan paid directly for accident, health or long-term care insurance out of the
# distribution. Three answers per Form 1099-R the dictionary asks about (`flowAskAboutPublicSafetyOfficer`:
# a box 7 code with a 2 or a 7 and no B) on a non-IRA form (the exclusion is refused on an IRA —
# measured, yes/yes/2,500 on an IRA code 7: `/flowKnockoutRetirementPublicSafetyOfficer`). Measured on
# wages-and-r1099-single (a code-7 pension of 10,000): 2,500 → 4,565.00, 4,000 → 4,505.00 (the cap),
# 0 → 4,865.00, the officer's no → 4,865.00; yes/yes with no amount is the dictionary's own knockout,
# so the amount is required behind the second yes.
R1099_PSO_FIELD = "public_safety_officer"                        # /form1099Rs/*/writeablePublicSafetyOfficer
R1099_PSO_PREMIUMS_FIELD = "pso_premiums_paid_by_plan"           # /form1099Rs/*/writeablePublicSafetyOfficerPremiums
R1099_PSO_AMOUNT_FIELD = "pso_premiums_cents"                    # /form1099Rs/*/writablePsoPremiumsPaid
R1099_PSO_FIELDS = (R1099_PSO_FIELD, R1099_PSO_PREMIUMS_FIELD, R1099_PSO_AMOUNT_FIELD)
# a Form 1099-R whose box 7 carries only the disability code (3, 3D or D3) on a non-IRA form
# computes only on the dictionary's disability-wages path, which reads whether the recipient had
# reached the plan's minimum retirement age: no puts the taxable amount on Form 1040 line 1h as
# wages; yes puts it on lines 5a/5b as a pension (measured; the dictionary's description still says
# a yes knocks out); no answer is `/knockoutForForm1099RDistributionCode`. The
# service never sent it, so every code-3 form knocked out (profile-disability).
R1099_MRA_FIELD = "reached_minimum_retirement_age"            # /form1099Rs/*/writableReachedMinimumRetirementAge
R1099_DISABILITY_CODES = frozenset({"3", "3D", "D3"})
# the death-benefit chain (IRC 101; register rows 56/15/43/44/45/16). A Form 1099-R with a box 7
# code of C (a reportable death benefit under IRC 6050Y — Table 1 states the code as an identity) or 4
# and a date in box 13 is priced by the dictionary from the filer's answers — a reportable policy sale
# and what was paid for the policy, or the IRC 101(a)(2) carve-outs; the service sent no box 13, so
# the dictionary's own guard never fired and the form fell through to box 2a. Measured on
# wages-and-r1099-single (box 1 = box 2a = 10,000): a sale with a 6,000 basis 4,865.00 → 4,145.00;
# fully excluded 3,665.00; a code 4 form whose box 1 is not that contract's death benefit, or with a
# companion code other than D, is the dictionary's own knockout.
R1099_DATE_FIELD = "date_of_payment"                                    # /form1099Rs/*/writableDateOfPayment
R1099_DB_BOX1_FIELD = "box1_is_death_benefit_under_contract"           # …/writableBox1IsTheDeathBenefitUnderThatContract
R1099_DB_SALE_FIELD = "acquired_in_reportable_policy_sale"              # …/writableAcquiredInReportablePolicySale
R1099_DB_CONSIDERATION_FIELD = "acquired_for_valuable_consideration"    # …/writableDeathBenefitAcquiredForValuableConsideration
R1099_DB_CARRYOVER_FIELD = "transfer_has_carryover_basis"               # …/writableDeathBenefitTransferHasCarryoverBasis
R1099_DB_RELATED_FIELD = "transfer_to_insured_or_related_party"         # …/writableDeathBenefitTransferToInsuredOrRelatedParty
R1099_DB_BASIS_FIELD = "death_benefit_basis_cents"                      # …/writableReportableDeathBenefitBasis
R1099_DB_FIELDS = (R1099_DATE_FIELD, R1099_DB_BOX1_FIELD, R1099_DB_SALE_FIELD, R1099_DB_CONSIDERATION_FIELD,
                   R1099_DB_CARRYOVER_FIELD, R1099_DB_RELATED_FIELD, R1099_DB_BASIS_FIELD)
R1099_CODE_C_FAMILY = frozenset({"C", "CD", "DC"})                      # box1IsIdentifiedAsTheReportableDeathBenefit
R1099_CODE_4_FAMILY = frozenset({"4", "4D", "D4"})                      # the same fact's second leg, behind the attestation
R1099_QCD_FIELD = "qualified_charitable_distribution_cents"        # /form1099Rs/*/writableQcdAmount
R1099_QCD_SPLIT_FIELD = "qcd_to_split_interest_entity"             # /form1099Rs/*/writableIsQcdToSplitInterestEntity
QCD_HISTORY_FIELD = "qcd_prior_deducted_ira_contributions_cents"   # /{primary,secondary}FilerQcdOffsetCarryover
# The dictionary's sufficient age bound (`/form1099Rs/*/isQcdEligibleByAge`): born on or before
# 1954-01-01, at least 71 on 2025-01-01. By year alone this service admits births through 1953;
# a 1954 birth is day-ambiguous (the synthesized day 01 would admit a month the bound admits one
# day of — the synthesized-day posture) and is refused with a positive amount; later births are
# refused by name.
QCD_AGE_BOUND_YEAR = 1954
# the indirect rollover — the recipient rolled the distribution over themselves within 60
# days (Form 1040 instructions, lines 4a/4b and 5a/5b, "Rollovers"; IRC 402(c)(3)(A), 408(d)(3)).
# No box shows it; the frontier module computes it from `writableIsIndirectRollover`, the amount,
# the 60-day answer (true computes) and, on an IRA form, the one-rollover-per-year answer (true
# computes, false is the dictionary's knockout). Measured through the mapper (wages-single-low, a
# Form 1099-R of 10,000, code 7, box 2a 10,000 — 2,075.00): a pension form with 10,000 rolled
# over → 928.00 (line 5b 0), 4,000 → 1,595.00 (line 5b 6,000); an IRA form with 10,000 rolled
# over → 928.00 (line 4a 10,000, 4b 0). A PARTIAL rollover on an IRA form is an engine defect
# at this pin (counted on lines 4b and 5b both: 12,000 taxed of 10,000) and is
# refused by name until the pin moves.
R1099_ROLLOVER_FIELD = "rolled_over_cents"                          # /form1099Rs/*/writableIndirectRolloverAmount
R1099_IRA_ONE_PER_YEAR_FIELD = "ira_one_rollover_per_year"          # /form1099Rs/*/writableIraOneRolloverPerYearSatisfied
# the qualified HSA funding distribution above the Form 8889 line 8 limitation. The
# dictionary clamps the exclusion to the IRC 408(d)(9)(C)(i) cap and puts the overflow on Form
# 1040 line 4b only when (a) the twelve-month coverage vector governs line 3 — the
# vector may be PREFILLED from the all-year answers, which this does (twelve months of
# the carried type, twelve Medicare months of no) — and (b) the month of the transfer is answered
# (row 70). Measured through the mapper (wages-single-low-hsa-funding, self-only all year, 928.00
# with 3,000 transferred): 5,000 transferred with the month → cap 4,300, 700 on line 4b,
# 1,040.00 (the knockout before); family 9,000 → cap 8,550, 450 on 4b, 1,000.00; a filer born
# 1965 with 5,000 → cap 5,300 (the catch-up), 928.00. The vector alone moves no committed value.
HSA_TRANSFER_MONTH_FIELD = "hsa_funding_distribution_transfer_month"   # /filers/*/writableHsaFundingDistributionTransferMonth
HSA_TRANSFER_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
# The line 8 base limitation by coverage type (2025: 4,300 self-only, 8,550 family) — the month is
# asked where it DECIDES, a transfer above the base; the 55-or-older catch-up is the dictionary's.
HSA_BASE_LIMIT_CENTS = {"self_only": 430000, "family": 855000}
HSA_VECTOR_LITERALS = {"self_only": "selfOnly", "family": "family"}
# the twelve coverage months — the vector's editable rows — asked where the
# all-year prefill cannot say (coverage for part of the year; the `both` type) and sent as the
# vector the dictionary's Line 3 Limitation Chart reads. Measured at the pin: 3,000 code W with
# self-only coverage January through June → line 3 2,150, 1,064.00 (the knockout before); July
# through December → 4,300 by the last-month rule, 928.00; `both` with family in December →
# 8,550. The type stays asked beside the months: the dictionary's excess computation reads it
# (measured: without it the six-month filer's 850 excess goes uncharged, 928.00).
HSA_MONTH_FIELDS = tuple(f"hsa_coverage_{m}" for m in HSA_TRANSFER_MONTHS)   # /filers/*/writableHsaCoverageTypeMonth01..12
HSA_MONTH_LITERALS = {"none": "none", "self_only": "selfOnly", "family": "family"}
# on a separate return, the spouse's twelve coverage months —
# return-level rows the dictionary reads for IRC 223(b)(5)(A)'s collapse and the line 6 division,
# asked once the filer with family coverage answers that the spouse also had HSA contributions
# (`/hsaMfsSpouseVectorAnswered` is what narrows `/flowKnockoutMFSLine6Check`; the rows cannot
# default — unanswered they read none, which cannot fire the collapse). Measured at the pin on
# wages-mfs-hsa-family with the rows answered and the marital question reached behind them:
# 3,000 code W computes at 3,665.00 with the cap halved to 4,275 (the knockout before); 5,000
# code W puts 725 on Schedule 1 line 8z and 44 on Form 5329, 3,793.00.
HSA_MFS_SPOUSE_MONTH_FIELDS = tuple(f"spouse_hsa_coverage_{m}" for m in HSA_TRANSFER_MONTHS)   # /writableHsaMfsSpouseCoverageTypeMonth01..12
_HSA_MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August",
                "September", "October", "November", "December")
# the first month of the transfer's testing period in which the filer was not an eligible
# individual — asked of a part-year filer with a funding distribution,
# where the dictionary reads it (`/filers/*/hasUnmodeledHsaFundingDistribution`'s second arm
# refuses the return without it). Twenty-five answers: none, then every month of 2025 and 2026 —
# a December-2025 transfer's window ends in December 2026. Measured on 5,000 transferred in June
# with self-only coverage January through June: none → 1,388.00, jul2025 → Form 8889 Part III
# line 19 5,000 and its 10%, 2,488.00; mar2026 → 1,388.00 (a 2026 breach is that year's return).
# Medicare for part of the year — the month enrollment began, asked once; the twelve-month
# Medicare vector (row 9) is sent from it, no before and yes from that month on, because IRC
# 223(b)(7) zeroes the limitation for the first month of entitlement and every month after (the
# dictionary's `hsaMedicareLimitationZeroMonthNN` latches, but its answered gate wants all twelve).
# Measured at the pin: 3,000 code W, self-only all year, Medicare from July → line 3 2,150,
# 1,064.00 (the knockout before); with a 5,000 June transfer and the testing period kept → 1,388.00.
HSA_MEDICARE_ONSET_FIELD = "hsa_medicare_first_month"   # /filers/*/writableHsaEnrolledInMedicareMonth01..12 (from it on)
HSA_TESTING_FIELD = "hsa_testing_period_first_ineligible_month"   # /filers/*/writableHsaTestingPeriodFirstIneligibleMonth
HSA_TESTING_MONTHS = ("none", *[f"{m}2025" for m in HSA_TRANSFER_MONTHS], *[f"{m}2026" for m in HSA_TRANSFER_MONTHS])
HSA_CONTRIBUTION_FIELDS = (HSA_MEDICARE_FIELD, HSA_MEDICARE_ONSET_FIELD, HSA_COVERAGE_FIELD, HSA_TYPE_FIELD,
                           *HSA_MONTH_FIELDS,
                           HSA_OTHER_COVERAGE_FIELD, HSA_FUNDING_FIELD, HSA_PRIOR_HFD_FIELD,
                           HSA_TESTING_FIELD,
                           HSA_SPOUSE_CONTRIBUTED_FIELD,
                           HSA_MARITAL_CHANGED_FIELD, HSA_MARITAL_AFFECTS_FIELD)
HSA_ENUM_FIELDS = (HSA_MEDICARE_FIELD, HSA_COVERAGE_FIELD, HSA_TYPE_FIELD, HSA_OTHER_COVERAGE_FIELD)
HSA_YEAR_SPANS = {"all_year": "allYear", "part_of_year": "partOfYear", "none": "noneOfYear"}
HSA_OTHER_COVERAGE_SPANS = {"whole_year": "wholeYear", "part_of_year": "partOfYear", "none": "noneOfYear"}
HSA_HDHP_TYPES = {"self_only": "selfOnly", "family": "family", "both": "both"}
HSA_ENUM_OPTIONS = {   # service code → (dictionary options path, its literals)
    HSA_MEDICARE_FIELD: ("/enrolledInMedicareOptions", HSA_YEAR_SPANS),
    HSA_COVERAGE_FIELD: ("/hsaHdhpCoverageStatusOptions", HSA_YEAR_SPANS),
    HSA_TYPE_FIELD: ("/typeOfHdhpOptions", HSA_HDHP_TYPES),
    HSA_OTHER_COVERAGE_FIELD: ("/hadOtherCoverageIneligibleForHSAOptions", HSA_OTHER_COVERAGE_SPANS),
}
HSA_EXCESS_IN_WAGES_FIELD = "hsa_excess_in_w2_wages"      # /writableHsaEmployerExcessAlreadyInW2Income
# the filer's OWN HSA contributions, Form 8889 line 2 — asked on every filer row (the IRA
# shape: the dictionary asks the activity question on every return). Measured at the pin: 2,000
# of own contributions is the line 13 deduction (line 24 928.00 → 728.00); an amount made after
# year end for the year adds (500 → 678.00); a yes with the amount unanswered computed zero in
# silence, so the amount is required; the after-year-end amount is optional, sent as 0 and
# stated (an unsent one fires the dictionary's dependent knockout, measured).
HSA_MADE_FIELD = "made_hsa_contributions"                          # writable{Role}FilerHasMadeContributionsToHsa
HSA_OWN_AMOUNT_FIELD = "hsa_own_contributions_cents"               # writableHsaNonemployerContributionsTaxYear
HSA_OWN_AFTER_FIELD = "hsa_own_contributions_after_year_end_cents" # writableHsaNonemployerContributionsTaxYearPlusOne
HSA_OWN_FIELDS = (HSA_MADE_FIELD, HSA_OWN_AMOUNT_FIELD, HSA_OWN_AFTER_FIELD)
# Form 5329 line 49's cap — the HSAs' value on December 31 (including the year's contributions
# made by the due date). Optional on a filer row with HSA activity; sent verbatim (a 0 is the filer's
# own statement that the account was emptied); absent sends nothing and is STATED. The dictionary
# reads it only behind a positive Form 5329 line 48, and there it is mandatory: unsent with an
# excess, the return is its standalone knockout /flowKnockoutHsaForm5329Line49AccountValueUnsupplied
# (IRC 4973(a)'s "shall not exceed" is not an election declined by silence), where it once taxed
# the whole excess (measured: 700 of excess, 200 in the account → 12, 1,010.00; 5,000 → 42,
# 1,040.00). Never pre-filled: a 0 would zero every filer's excise (register row 18).
HSA_DEC31_FIELD = "hsa_december_31_value_cents"                    # /filers/*/writableHsaDecember31AccountValue
# Form 5329 line 42 — the excess still in the account at the end of 2024 (the 2024 Form 5329
# line 48, where its line 49 was above zero). Line 43 absorbs it against the room under Form 8889
# line 12; what remains joins line 48 for the 6%. Optional on a filer row with HSA activity, the
# root yes derived from a positive amount; absent sends the no and is STATED (it was the mapper's
# own assumption once). Measured: 2,000 on a 3,000 code W self-only filer → 700 past the
# 1,300 of room, 42 (928.00 → 970.00); 500 beside a 700 current excess → 1,200, 72 (1,040.00 →
# 1,070.00). On a filer without contributions line 12 is undefined and the dictionary refuses the
# carry-in (`/flowKnockoutHsaExcessContributions`, register row 15's second slice) — sent, served.
HSA_PRIOR_EXCESS_FIELD = "hsa_prior_year_excess_cents"             # /filers/*/writableHsaPriorYearExcessContributionsForm5329Line48
HSA_ROOT_FIELDS = frozenset({HSA_EXCESS_IN_WAGES_FIELD})
# Form W-2 box 12 code Q (nontaxable combat pay) and the three combat pay elections — one
# per line the dictionary asks separately: Form 1040 line 1i (the earned income credit), Form 2441
# Part II (the credit) and Form 2441 Part III (the exclusion). Each is a choice over the service's
# own four values, mapped to the dictionary's `/combatPayOptions` literal by which filers carry
# code Q; an option naming a filer with no code Q is refused by name (the dictionary's
# `/claimedSpouseCombatPayWithoutMFJ` is a submission block, never a knockout with words).
W2_BOX12_Q_FIELD = "box12_q_cents"
COMBAT_ELECTION_FIELD = "combat_pay_election"                           # /combatPayElection
CDCC_COMBAT_ELECTION_FIELD = "cdcc_combat_pay_election"                 # /cdccCombatPayElection
DCB_COMBAT_ELECTION_FIELD = "dependent_care_benefits_combat_pay_election"   # /cdccCombatPayElectionForBenefits
COMBAT_ELECTION_EMISSION = {COMBAT_ELECTION_FIELD: "/combatPayElection",
                            CDCC_COMBAT_ELECTION_FIELD: "/cdccCombatPayElection",
                            DCB_COMBAT_ELECTION_FIELD: "/cdccCombatPayElectionForBenefits"}
COMBAT_ROOT_FIELDS = frozenset(COMBAT_ELECTION_EMISSION)
COMBAT_ELECTION_CHOICES = ("own", "spouse", "both", "none")
COMBAT_ELECTION_LINE = {COMBAT_ELECTION_FIELD: "Form 1040 line 1i (the earned income credit)",
                        CDCC_COMBAT_ELECTION_FIELD: "Form 2441 Part II (the child and dependent care credit)",
                        DCB_COMBAT_ELECTION_FIELD: "Form 2441 Part III (the dependent care benefits exclusion)"}
W2_BOX12_DEFERRAL_FIELDS = ("box12_d_cents", "box12_e_cents", "box12_g_cents", "box12_h_cents",
                            "box12_s_cents", "box12_aa_cents", "box12_bb_cents", "box12_ee_cents")
W2_BOX12_CODES = (  # (code, dictionary writable, the form's caption, disposition, route)
    ("a", "uncollectedOasdiTaxOnTips", "Uncollected social security or RRTA tax on tips", "carried", ""),
    ("b", "uncollectedMedicareTaxOnTips", "Uncollected Medicare tax on tips", "carried", ""),
    ("c", "taxableLifeInsuranceOver50k", "Taxable cost of group-term life insurance over $50,000", "inert", ""),
    ("d", "401kDeferrals", "Elective deferrals under a section 401(k) cash or deferred arrangement plan", "carried", "Form 8880 (Schedule 3 line 4)"),
    ("e", "403bDeferrals", "Elective deferrals under a section 403(b) salary reduction agreement", "carried", "Form 8880 (Schedule 3 line 4)"),
    ("f", "sarsepDeferrals", "Elective deferrals under a section 408(k)(6) salary reduction SEP", "knockout", ""),
    ("g", "457bDeferrals", "Elective deferrals and employer contributions to a section 457(b) deferred compensation plan", "carried", "Form 8880 (Schedule 3 line 4)"),
    ("h", "501c18Deferrals", "Elective deferrals to a section 501(c)(18)(D) tax-exempt organization plan", "carried", "Form 8880 (Schedule 3 line 4)"),
    ("j", "nontaxableSickPay", "Nontaxable sick pay", "knockout", ""),
    ("k", "goldenParachuteExciseTax", "20% excise tax on excess golden parachute payments", "knockout", ""),
    ("l", "expenseReimbursements", "Substantiated employee business expense reimbursements", "knockout", ""),
    ("m", "uncollectedOasdiTaxOnLifeInsuranceOver50k", "Uncollected social security or RRTA tax on taxable cost of group-term life insurance over $50,000", "carried", ""),
    ("n", "uncollectedMedicareTaxOnLifeInsuranceOver50k", "Uncollected Medicare tax on taxable cost of group-term life insurance over $50,000", "carried", ""),
    ("p", "armedForcesMovingExpenses", "Excludable moving expense reimbursements paid directly to a member of the U.S. Armed Forces", "knockout", ""),
    ("q", "writableCombatPay", "Nontaxable combat pay", "carried", "Schedule 8812 line 18b; Form 1040 line 1i and Form 2441 through the combat pay elections"),
    ("r", "archerMsaContributions", "Employer contributions to an Archer MSA", "knockout", ""),
    ("s", "simpleContributions", "Employee salary reduction contributions under a section 408(p) SIMPLE plan", "carried", "Form 8880 (Schedule 3 line 4)"),
    ("t", "adoptionBenefits", "Adoption benefits", "knockout", ""),
    ("v", "nsoIncome", "Income from exercise of nonstatutory stock option(s)", "inert", ""),
    ("w", "employerHsaContributions", "Employer contributions (including employee contributions through a cafeteria plan) to an employee's health savings account (HSA)", "carried", "Form 8889 (Schedule 1 line 8z, Form 5329 Part VII)"),
    ("y", "409aDeferrals", "Deferrals under a section 409A nonqualified deferred compensation plan", "inert", ""),
    ("z", "nqdcDeferrals", "Income under a nonqualified deferred compensation plan that fails to satisfy section 409A", "knockout", ""),
    ("aa", "roth401kContributions", "Designated Roth contributions under a section 401(k) plan", "carried", "Form 8880 (Schedule 3 line 4)"),
    ("bb", "roth403bContributions", "Designated Roth contributions under a section 403(b) plan", "carried", "Form 8880 (Schedule 3 line 4)"),
    ("dd", "healthCoverageCost", "Cost of employer-sponsored health coverage", "inert", ""),
    ("ee", "roth457bContributions", "Designated Roth contributions under a governmental section 457(b) plan", "carried", "Form 8880 (Schedule 3 line 4)"),
    ("ff", "qsehraBenefits", "Permitted benefits under a qualified small employer health reimbursement arrangement", "inert", ""),
    ("gg", "83iIncome", "Income from qualified equity grants under section 83(i)", "inert", ""),
    ("hh", "83iDeferrals", "Aggregate deferrals under section 83(i) elections as of the close of the calendar year", "inert", ""),
    ("ii", "nonTaxableMedicaidWaiverPayments", "Medicaid waiver payments excluded from gross income under Notice 2014-7", "knockout", ""),
)
W2_BOX12_BY_FIELD = {f"box12_{code}_cents": (code, leaf, caption, disposition, route)
                     for code, leaf, caption, disposition, route in W2_BOX12_CODES}
W2_BOX12_FIELDS = tuple(W2_BOX12_BY_FIELD)
W2_BOX12_CARRIED = tuple(f for f, (_c, _l, _cap, d, _r) in W2_BOX12_BY_FIELD.items() if d == "carried")
W2_BOX12_EMITTED = tuple(f for f, (_c, _l, _cap, d, _r) in W2_BOX12_BY_FIELD.items()
                         if d in ("carried", "inert"))


FACT_GROUP_LABELS = {
    "spouse_itemizes": "the separate-return checkbox (spouse itemizes)",
    # the lived-together chain, root questions on every married return.
    "lived_with_spouse_all_year": "the married-return question (lived with your spouse all year)",
    "months_lived_with_spouse": "the married-return question (how long you lived together)",
    "separation_agreement_on_last_day": "the married-return question (a separation agreement on the last day)",
    "lived_apart_last_six_months": "the married-return question (lived apart the last six months)",
    "community_property_domicile": "the community-property domicile question (Form 8958)",
    # the separate-return spouse chain (five root answers).
    "spouse_files_return": "the separate-return question (spouse files a return)",
    "spouse_had_gross_income": "the separate-return question (spouse had gross income)",
    "spouse_can_be_claimed": "the separate-return question (spouse can be claimed by another)",
    "spouse_65_or_older": "the separate-return spouse checkbox (65 or older)",
    "spouse_is_blind": "the separate-return spouse checkbox (blind)",
    "spouse_covered_by_employer_plan": "the separate-return spouse's retirement plan coverage "
                                       "(the IRA deduction's phase-out)",
    **{f: f"the separate-return spouse's HSA coverage month ({n}; Form 8889 line 6)"
       for f, n in zip(HSA_MFS_SPOUSE_MONTH_FIELDS, ("January", "February", "March", "April", "May", "June",
                                                    "July", "August", "September", "October", "November",
                                                    "December"))},
    "spouse_death_year": "the qualifying-surviving-spouse death-year question",
    # the joint return's filing-requirement pair, root questions behind a claimable spouse.
    "couple_required_to_file": "the joint-return question (the couple is required to file)",
    # the Form 8880 filed-jointly pair, root questions on a joint return.
    "filed_jointly_2023": "the joint-return question (filed jointly for 2023, Form 8880 line 4)",
    "filed_jointly_2024": "the joint-return question (filed jointly for 2024, Form 8880 line 4)",
    "hsa_excess_in_w2_wages": "the question whether an excess employer HSA contribution is already in W-2 wages (Form 8889)",
    # the three combat pay elections, on a return with a W-2 box 12 code Q amount.
    "combat_pay_election": "the combat pay election (Form 1040 line 1i, the earned income credit)",
    "cdcc_combat_pay_election": "the combat pay election for the child and dependent care credit (Form 2441 Part II)",
    "dependent_care_benefits_combat_pay_election": "the combat pay election for the dependent care benefits exclusion (Form 2441 Part III)",
    "couple_files_only_for_refund": "the joint-return question (the couple files only for a refund)",
    "could_have_filed_jointly_year_of_death":
        "the could-have-filed-jointly question (year of the spouse's death)",
    # the residence state on every return; the Alaska dividend pair behind an Alaska answer.
    "residence_state": "the residence-state question (the state you lived in and earned income in)",
    "received_alaska_pfd": "the Alaska Permanent Fund dividend question",
    "spouse_received_alaska_pfd": "the Alaska Permanent Fund dividend question (spouse)",
    # the page-1 digital-assets question, its two parts, on every return.
    "received_digital_assets": "the Form 1040 page-1 digital-assets question (received)",
    "disposed_digital_assets": "the Form 1040 page-1 digital-assets question (disposed of)",
    # Schedule B Part III, the three questions, on every return.
    "foreign_financial_account": "the Schedule B line 7a question (a foreign financial account)",
    "foreign_trust_grantor": "the Schedule B line 8 question (owner or grantor of a foreign trust)",
    "foreign_trust_transactions": "the Schedule B line 8 question (a distribution from or transfer "
                                  "to a foreign trust)",
    # Form 8862's credit-history questions, on every return.
    "eitc_reduced_or_disallowed": "the Form 8862 question (an earned income credit reduced or "
                                  "disallowed in a prior year)",
    "ctc_odc_reduced_or_disallowed": "the Form 8862 question (a child tax credit, additional child "
                                     "tax credit or credit for other dependents reduced or "
                                     "disallowed in a prior year)",
    "qualifying_child_of_another": "the Form 8862 line 4 question (could be another taxpayer's "
                                   "qualifying child)",
    # Form 1040 line 26, the root question and what a yes reaches.
    "paid_estimated_taxes": "the estimated tax payments question",
    "section_1341_credit_cents": "the Schedule 3 line 13b credit for repaid income (IRC 1341)",
    "estimated_tax_payments_cents": "the estimated tax payments amount (and the amount applied "
                                    "from last year's return)",
    # Schedule 1 lines 2a/19a, alimony received and paid, and each side's gate.
    "alimony_received_cents": "the Schedule 1 line 2a alimony received amount",
    "alimony_received_pre2019_agreement": "the alimony-received pre-2019-agreement gate",
    "alimony_paid_cents": "the Schedule 1 line 19a alimony paid amount",
    "alimony_paid_pre2019_agreement": "the alimony-paid pre-2019-agreement gate",
    "alimony_paid_section_682_trust": "the alimony-paid section 682 trust question",
    # the Form 1040 page-1 main-home checkbox, on every return.
    "main_home_in_us_over_half_year": "the Form 1040 page-1 main-home-in-the-U.S. checkbox",
    "estimated_payments_under_different_name": "the estimated payments follow-up (payments made "
                                               "under a different name)",
    "estimated_payments_with_former_spouse": "the estimated payments follow-up (payments made "
                                             "jointly with a former spouse)",
    # Schedule 1 line 21, the root question and what a yes reaches.
    "paid_student_loan_interest": "the student loan interest question",
    "elects_lump_sum_benefits": "the Social Security lump-sum election (Form 1040 line 6c)",
    "only_business_is_trading_securities": "the Form 8960 sole-trader question",
    # the questions a Form 1095-A reaches.
    "allocating_policy_or_alternative_calculation": "the Form 8962 line 9 question (allocating "
                                                    "policy amounts, or the year-of-marriage "
                                                    "alternative calculation)",
    "marketplace_estimated_income_at_least_100_fpl": "the Form 8962 question (the Marketplace "
                                                     "estimated household income at or above "
                                                     "100% of the federal poverty line)",
    "below_poverty_line_not_eligible_for_medicaid_due_to_immigration":
        "the Form 8962 question (household income below the federal poverty line and not "
        "eligible for Medicaid because of immigration status)",
    "enrollee_not_eligible_for_marketplace_due_to_immigration":
        "the Form 8962 question (someone in the tax family not lawfully present)",
    "dependents_modified_agi_cents": "the Form 8962 line 2b amount (the dependents' modified AGI)",
    "paid_prior_year_care_expenses_this_year": "the Form 2441 Worksheet A root (2024 care expenses paid in 2025)",
    "prior_year_credit_claimed": "the Form 2441 Worksheet A question (the 2024 credit was claimed)",
    "prior_year_credit_claimed_maximum": "the Form 2441 Worksheet A question (the 2024 credit was claimed on the maximum expenses)",
    "prior_year_form_2441_line_3_cents": "the Form 2441 Worksheet A line 1 amount (2024 Form 2441 line 3)",
    "prior_year_expenses_paid_this_year_cents": "the Form 2441 Worksheet A line 2 amount (2024 expenses paid in 2025)",
    "prior_year_had_two_or_more_qualifying_persons": "the Form 2441 Worksheet A line 4 question (two or more qualifying persons in 2024)",
    "prior_year_excluded_or_deducted_benefits_cents": "the Form 2441 Worksheet A line 5 amount (2024 benefits excluded or deducted)",
    "prior_year_lower_earned_income_cents": "the Form 2441 Worksheet A line 7 amount (the smaller 2024 earned income)",
    "prior_year_form_2441_line_6_cents": "the Form 2441 Worksheet A line 9 amount (2024 Form 2441 line 6)",
    "prior_year_agi_cents": "the Form 2441 Worksheet A line 11 amount (2024 adjusted gross income)",
    "mfs_ptc_exception": "the Form 8962 separate-return exception",
    "mfs_ptc_exception_fourth_year": "the Form 8962 separate-return exception's fourth-year "
                                     "question",
    "student_loans_qualify": "the student loan interest follow-up (the loans qualify)",
    "student_loan_interest_cents": "the student loan interest amount (Form 1098-E box 1)",
    "student_loan_interest_employer_paid_cents":
        "the student loan interest an employer paid under a section 127 program",
    "student_loan_interest_from_qtp_cents":
        "the student loan interest paid from tax-free qualified tuition program earnings",
    "filing_status": "filing status",
    "persons": "filers",
    "w2s": "Form W-2 wages, federal withholding, the Social-Security / Medicare wage and "
           "withholding boxes, and box 10 dependent care benefits",
    # Form 2441 Part III's root lines, reached once a filer reports a benefit.
    DCB_CARRYOVER_FIELD: "the Form 2441 line 13 question (prior-year benefits used in the grace "
                         "period)",
    DCB_FORFEITED_FIELD: "the Form 2441 line 14 question (benefits forfeited or carried forward)",
    "int1099s": "1099-INT interest",
    "oid1099s": "1099-OID original issue discount",
    "b1099s": "1099-B proceeds from sales of stocks, bonds and other property",
    "div1099s": "1099-DIV dividends",
    "r1099s": "1099-R distributions",
    "w2gs": "W-2G gambling winnings",
    "ssa1099s": "SSA-1099 / RRB-1099 Social Security benefits",
    "g1099s": "Form 1099-G unemployment compensation",
    "misc1099s": "Form 1099-MISC royalties (box 2) and other income (box 3)",
    # the royalty activity's two root answers no 1099-MISC box carries.
    "royalty_expenses_cents": "the royalty activity's ordinary expenses (Schedule E line 20)",
    "royalty_is_oil_gas_geothermal": "whether the royalty activity is oil, gas, or geothermal "
                                     "(Schedule E line 18 depletion)",
    "hsa_distributions": "Form 1099-SA HSA distributions (Form 8889 Part II)",
    "ssa_lump_sum_years": "the earlier years a Social Security lump-sum payment is for "
                          "(Publication 915, Worksheet 2 and 3)",
    "care_providers": "Form 2441 care providers (child and dependent care credit)",
    "f1095as": "Form 1095-A Marketplace coverage (Form 8962, the premium tax credit)",
    "schedule_c": "Schedule C self-employment income",
    "rentals": "rental income (Schedule E)",
    "k1s": "K-1 income (partnership, S-corp, estate or trust)",
    "elections": "the itemize-when-lower election",
    "carryovers": "carried-in amounts (capital loss, IRA basis)",
}

# Income groups with a real mapper function. Populated at the bottom of this module, once those
# functions exist — covering a new stream means writing one, not editing a list.
_INCOME_MAPPERS = {}

# Income streams whose engine flow (the flags that make the amount reach total income and tax) is
# not complete. An incomplete mapping under-reports, which World #1 forbids, so they are an honest
# refusal. Order is display order.
# `w2gs` was removed: it was decided (2026-08-20) that W-2G is covered, and the flow this
# tuple exists to guard is complete AT OUR PIN — formW2Gs.xml carries box 1 to Schedule 1 line 8b
# (income.xml) and box 4 into /totalWithholding (taxCalculations.xml), both measured here, not
# assumed. Nothing else moved.
# `int1099s`, `div1099s`, then `r1099s` were removed: each flow was proven complete at
# the pin by the reachability artifact, and their mappers below carry the boxes the schema
# models.
# EMPTY since the last stream (k1s) was covered: every income group the fact schema
# names now has a mapper. The tuple stays — the refusal machinery, `coverage`'s exclusions and
# the `unasked_boundary` derivation all read it, and the next uncovered stream re-enters here.
UNSUPPORTED_STREAMS = ()

# Fact groups the schema accepts that this mapper maps NOWHERE. Sending one used to be a SILENT
# drop — the caller got a number computed as if they had not sent it. They are refused instead.
UNSUPPORTED_FACT_GROUPS = ("elections", "carryovers")

# Every person field the fact schema defines. Anything else in a person object is refused, not
# dropped: that is what makes the schema's shape true at RUNTIME and not merely on paper — the
# rule that once read "the service accepts no blindness input" and, since reads "the
# blindness checkbox is a filer-row field and nothing else on a person is accepted".
# (`relationship` and `months_in_home` are dependent-only qualifiers and are read by nothing while
# dependents are refused — the one accepted-and-unread pair, called out here because the rest of
# this module refuses rather than ignores.)
# `birth_month` is optional (a birth DAY is a forbidden identifier; the month is a sanctioned
# derivative). When it is absent the mapper must still synthesize a whole date for the engine, and
# THIS is the month it uses. the age-65 day-ambiguity guard reads the same constant, because a
# guard that tests the supplied value while the mapper uses a defaulted one is not a guard.
DEFAULT_BIRTH_MONTH = 1

# The three answers to "Who this person is to the return" — the person schema's own `role`
# enum. Declared here rather than read from schema/ for the same reason PERSON_FIELDS is:
# the deployed container ships src/ + generated/ without schema/.
ROLES = ("primary", "spouse", "dependent")

PERSON_FIELDS = frozenset({"role", "birth_year", "birth_month", "tin_type", "relationship",
                           "months_in_home", "is_student", "is_permanently_disabled",
                           # The dependent qualifiers: asked on every claimed
                           # dependent; on a filer row refused by name by
                           # `refuse_dependent_answers_on_a_filer_row` (until then this
                           # comment claimed a guard that did not run, and the nine were
                           # accepted and silently dropped there).
                           "is_married", "provided_own_support", "gross_income_under_limit",
                           "filer_provided_over_half_support",
                           "could_be_qualifying_child_of_another",
                           "has_other_biological_or_adoptive_parent",
                           # the benefit-split gate, asked on the filer's own
                           # biological or adopted child once that child is answered as
                           # having another legal parent, and one link at a time —
                           # `dependent_benefit_split_questions_reached` is the population,
                           # and an answer off it is refused by name.
                           "parents_situation", "child_in_parents_custody",
                           "child_lived_with_parents_over_half_year",
                           "parents_provided_over_half_support", "written_declaration",
                           # the joint-return test, asked on a MARRIED dependent row only
                           # and one link at a time — `dependent_joint_return_questions_reached`
                           # is the population, and an answer off it is refused by name.
                           "files_joint_return_with_spouse", "required_to_file_with_spouse",
                           "joint_return_only_for_refund",
                           # The keeping-up-home answer (hoh/qss;
                           # a single return's qualifying rows too).
                           "filer_paid_most_of_home_upkeep",
                           # the custodial-parent questions, the split chain's last links.
                           "nights_with_filer_vs_other_parent", "filer_agi_higher_than_other_parent",
                           # the non-parental split's links (its third, `child_in_parents_custody`,
                           # is the split gate's field on a non-parent row).
                           "parents_meet_divorced_or_separated_rule",
                           "a_parent_signed_declaration_not_to_claim",
                           "custodial_parent_claims_child_as_qualifying_person",
                           "filer_agi_higher_than_custodial_parent",
                           # the non-parental arm's first question, asked on a claimed
                           # dependent the filer is not the parent of (`parents_living_question_armed`).
                           "child_parents_living",
                           # the split gate's custody questions on a claimed dependent 18 or
                           # older (`child_custody_questions_reached`); refused by name off it.
                           "child_residence_state", "child_emancipated",
                           "child_emancipated_after_july_2",
                           # the member-of-household questions
                           # (`household_member_questions_reached`); refused by name off it.
                           "was_spouse_during_year", "relationship_violates_local_law",
                           # Form 1040 line 12's own checkbox, per filer row. Refused on
                           # a dependent row by the guard below — the engine's dependent item
                           # has no blindness fact, so an answer there would move nothing.
                           "is_blind",
                           # the educator question on every filer row and the amount its
                           # yes reaches (`educator_questions_reached`); refused on a dependent
                           # row and where unreached by `refuse_misplaced_educator_answers`.
                           "k12_educator", "educator_expenses_cents",
                           # the IRA question on every filer row and the two answers its
                           # yes reaches (`ira_questions_reached`).
                           "made_ira_contributions", "traditional_ira_contributions_cents",
                           "contributed_to_inherited_ira",
                           # the amount behind an inherited-IRA yes (`ira_questions_reached`).
                           "inherited_ira_contribution_cents",
                           # the Roth-and-ABLE follow-up, and Form 8880's questions on a
                           # filer row with contributions (`savers_questions_reached`).
                           "roth_ira_and_able_contributions_cents",
                           "roth_ira_contributions_cents",
                           "received_retirement_distributions_2023_2024",
                           "retirement_distributions_2023_cents", "retirement_distributions_2024_cents",
                           "received_retirement_distributions_after_year_end",
                           "retirement_distributions_after_year_end_cents",
                           # the page-1 "someone can claim you" chain, per filer row.
                           "someone_can_claim_you", "expect_to_be_claimed",
                           "potential_claimer_must_file", "potential_claimer_filed",
                           "potential_claimer_filed_only_for_refund",
                           # the HSA 20%-tax exception pair, reached by a filer's taxable
                           # distributions (`hsa_exception_questions_reached`).
                           "hsa_exception_amount_cents", "hsa_exception_reason",
                           # Form 8889 Part I's questions on a filer row with a code W
                           # amount (`hsa_questions_reached`).
                           "hsa_medicare", "hsa_hdhp_coverage", "hsa_hdhp_type", "hsa_other_coverage",
                           *HSA_MONTH_FIELDS,
                           "hsa_testing_period_first_ineligible_month",
                           "hsa_medicare_first_month",
                           "hsa_funding_distribution", "hsa_prior_funding_distribution_election",
                           "qcd_prior_deducted_ira_contributions_cents",
                           "hsa_funding_distribution_transfer_month",
                           "hsa_spouse_contributed",
                           "hsa_marital_status_changed", "hsa_marital_change_affects_limit",
                           # the own-contributions question on every filer row, the two
                           # amounts behind a yes (`hsa_own_questions_reached`).
                           "made_hsa_contributions", "hsa_own_contributions_cents",
                           "hsa_own_contributions_after_year_end_cents",
                           HSA_DEC31_FIELD,
                           HSA_PRIOR_EXCESS_FIELD,
                           # Form 2441 line 2 column (d), on a qualifying person's row
                           # (`care_expense_question_reached`).
                           "care_expenses_cents",
                           # Form 2441 Part III on a filer row — the sole-proprietorship
                           # benefit and the plan maximum (`dcb_person_questions_reached`).
                           "self_employed_dependent_care_benefits_cents",
                           "dependent_care_plan_maximum_cents",
                           # Form 2441's other qualifying-person arm, on a claimed
                           # dependent's row (`unable_to_care_question_reached`).
                           "unable_to_care_for_self"})

# the same rule for every OTHER collection. The schema declares `additionalProperties: false`
# on each of these objects, but NEITHER TRANSPORT VALIDATES REQUESTS (REST does none; MCP validates
# responses only) — so the schema is documentation and this is the only enforcement that runs. Until
# this existed, a W-2 carrying `employee_name`/`employee_ssn` was accepted and the keys silently
# dropped by `_w2`'s `.get()` reads, while the identical trick on a person was refused.
# Declared here rather than read from schema/ because the deployed container ships src/ + generated/
# only; `test_schema.py` asserts these sets equal the schema's, so the two cannot drift.
# Work item 0b — what the schema REQUIRES, enforced. The schema has always declared these; nothing
# checked them, because REST validates no request and MCP validates responses only. So `_w2` read
# `w2.get("wages_cents", 0)` and a caller who omitted the one figure a return is built on received a
# confident, cited, COMPLETE answer of $0.00.

# ABSENCE IS NOT ZERO. A caller who means zero sends zero; a caller who says nothing has told us
# nothing. That distinction is what the gap loop reports on, and it cannot exist while every missing
# value has a stand-in.

# Declared here rather than read from schema/ for the same reason as COLLECTION_ITEM_FIELDS above:
# the deployed container ships src/ + generated/ without schema/. `test_schema.py` asserts these
# equal the schema's own `required` lists, so the two cannot drift.
REQUIRED_ROOT_FIELDS = frozenset({"filing_status", "persons"})

# The separate-return pair (mfs coverage): root booleans asked on every mfs
# return, refused on any other status — the printed checkbox and the Form 8958 domicile test
# belong to a separate return only.
MFS_ROOT_FIELDS = frozenset({"spouse_itemizes", "community_property_domicile",
                             # the spouse chain, asked in this order, each only when the
                             # one before unlocks it.
                             "spouse_files_return", "spouse_had_gross_income",
                             "spouse_can_be_claimed", "spouse_65_or_older", "spouse_is_blind",
                             # the other spouse's employer-plan coverage, reached once the
                             # filer contributed to an IRA and the couple did not live apart all
                             # year (`ira_coverage_question_reached`).
                             "spouse_covered_by_employer_plan",
                             # the spouse's twelve HSA coverage months, reached once the
                             # filer with family coverage answers that the spouse also had HSA
                             # contributions (`hsa_mfs_spouse_months_asked`).
                             *HSA_MFS_SPOUSE_MONTH_FIELDS})
# The chain's links: (field, the answer to the previous field that reaches it). The root's
# own link is the printed checkbox: `spouse_itemizes` False reaches it — an itemizing spouse
# necessarily FILES (an implication of the printed form), so behind an itemizing answer the
# chain is unreached and the filing fact is emitted as that implication. Review-found before
# the spouse chain shipped: with the root reached on every mfs return, itemizes=true +
# files=false was accepted and the engine's two-fact zeroing chain (/spouseItemizes AND
# /MFSLivingSpouseFilingReturn) read the contradiction as "not zeroed" — measured, 18,950
# served where the rule says 0.
MFS_SPOUSE_CHAIN = (("spouse_files_return", False), ("spouse_had_gross_income", False),
                    ("spouse_can_be_claimed", False), ("spouse_65_or_older", False),
                    ("spouse_is_blind", False))


def mfs_spouse_questions_reached(facts: dict) -> list:
    """The spouse-chain fields the answers so far REACH, in order — the first once the spouse
    is answered as not itemizing; each later one only when the previous answer is the
    unlocking one (the two checkbox answers share a link, so both are reached together).
    Read by the gaps, the mapper's backstop and the unreached-answer refusal, so the three
    cannot disagree."""
    if facts.get("spouse_itemizes") is not False:
        return []
    reached = ["spouse_files_return"]
    prev = "spouse_files_return"
    for field, unlock in MFS_SPOUSE_CHAIN[1:]:
        if field == "spouse_is_blind":
            if "spouse_65_or_older" in reached:
                reached.append(field)
            continue
        if facts.get(prev) is unlock:
            reached.append(field)
            prev = field
        else:
            break
    return reached
# The qss pair (qss coverage): asked on every
# qualifying-surviving-spouse return, refused elsewhere — the same per-status rule.
QSS_ROOT_FIELDS = frozenset({"spouse_death_year", "could_have_filed_jointly_year_of_death"})
# the joint return's filing-requirement pair — asked once either spouse can be claimed as
# someone's dependent, refused elsewhere (the same per-status rule).
MFJ_ROOT_FIELDS = frozenset({"couple_required_to_file", "couple_files_only_for_refund"})
STATUS_ROOT_FIELDS = {"mfs": MFS_ROOT_FIELDS, "qss": QSS_ROOT_FIELDS, "mfj": MFJ_ROOT_FIELDS}
# the Form 1040 page-1 digital-assets question, asked on EVERY return the way the
# dictionary's two writables ask it — part (a) received, part (b) disposed (income.xml). Neither
# moves a served line: their one reader is `/notDigitalAssets` (NOT Any), which completes the
# income-sources section and is a <Not>-wrapped member of `/flowIsKnockedOut`, so a yes on either
# is a knockout — served honestly; both were once attested false and published.
DIGITAL_ASSET_FIELDS = frozenset({"received_digital_assets", "disposed_digital_assets"})
DIGITAL_ASSET_EMISSION = {"received_digital_assets": "/receivedDigitalAssets",
                          "disposed_digital_assets": "/disposedDigitalAssets"}
# Schedule B Part III — lines 7a and 8 — asked on EVERY return the way the dictionary's three
# writables ask it (income.xml): a financial interest in or signature authority over a foreign
# financial account; owner or grantor of a foreign trust; a distribution from or transfer to one.
# Measured at the pin (wages-single-mid, each true alone): any yes makes `/hasForeignAccountsOrTrusts`
# true, an unconditional member of `/flowIsKnockedOut` (and `/requiresScheduleB` with it, which is
# how the static DAG reaches the interest lines); no served figure moves on any fixture. All three
# were once attested false and published as assumptions. In the form's order; a tuple because
# the asks are in that order.
FOREIGN_ACCOUNT_FIELDS = ("foreign_financial_account", "foreign_trust_grantor",
                          "foreign_trust_transactions")
FOREIGN_ACCOUNT_EMISSION = {"foreign_financial_account": "/hasForeignAccounts",
                            "foreign_trust_grantor": "/isForeignTrustsGrantor",
                            "foreign_trust_transactions": "/hasForeignTrustsTransactions"}
# the credit-history answers — Form 8862's questions — asked on EVERY return the way the
# dictionary's three writables ask them: an earned income credit reduced or disallowed in a prior
# year (eitc.xml), a child tax credit / ODC / ACTC reduced or disallowed (ctcOdc.xml), and whether
# the filer could be another taxpayer's EITC qualifying child (Form 8862 line 4). Measured at the
# pin, each true alone: on a return with a credit in play the engine leaves the credit UNRESOLVED
# (`/eitcQualified`, `/ctcQualified` or `/eitcQcTest` absent, `/creditsSectionComplete` false —
# the Form 8862 chain wants answers this service does not carry) and the credit line resolves as a
# Placeholder 0; on a return with no credit in play nothing moves and the section stays complete.
# `operations._require_credit_history_resolved` reads the engine's own eligibility answers
# (`/eitcQualified`, `/ctcQualified`) after resolve — absent exactly then, measured; the section
# flag itself is unresolved at baseline on a claimed-dependent filer, so it is not the rule. All
# three were once attested false and published as assumptions.
CREDIT_HISTORY_FIELDS = ("eitc_reduced_or_disallowed", "ctc_odc_reduced_or_disallowed",
                         "qualifying_child_of_another")
CREDIT_HISTORY_EMISSION = {"eitc_reduced_or_disallowed": "/eitcHadImproperClaims",
                           "ctc_odc_reduced_or_disallowed": "/receivedImproperClaims",
                           "qualifying_child_of_another": "/eitcQcOfAnother"}
# Form 1040 line 26 — estimated tax payments and the amount applied from last year's return.
# The root question (`/paidEstimatedTaxesOrFromLastYear`) is asked on every return; a yes REACHES
# the amount (`/estimatedTaxPaymentWritable`, line 26 → line 33) and the two follow-ups the
# dictionary's section completeness wants (`/estimatedTaxesIsComplete`): paid under a different
# name (a yes then wants the former NAME) and paid jointly with a former spouse (a yes then wants
# the former spouse's TIN) — both identifiers this boundary forbids, so a yes on either is refused
# by name and a no completes the section. Measured at the pin on wages-single-mid: yes + $1,000
# moves line 33 5,400 → 6,400 and line 34 1,285 → 2,285; `/totalTax` unchanged; no knockout. The
# root answer was once attested false and published as an assumption.
# Schedule 3 line 13b — the IRC 1341(a)(5) credit for repayment of amounts included in
# income in an earlier year. The dictionary carries it as a SELF-REPORTED intake
# (`/writableClaimOfRightRepaymentCreditSection1341`), read complete-safe into `/sched3Line13b` and
# added into line 14: "the intake only serves a filer who already figured the credit and is not
# refused". (a)(5) is a prior-year tax recomputed, which this service does not hold — so the figure
# is the filer's, never computed here, and the ask carries provenance rather than instruction.
# Measured at the pin on wages-single-mid: a 500.00 entry moves line 13b and line 14 to 500.00 and
# total payments 5,400.00 -> 5,900.00, with no knockout; unsent, the credit was silently 0.
# OPTIONAL, the root posture: absent is no credit and `gaps._ABSENT_MEANS` says so.

# THE INTAKE ABOVE IS RETIRED BY THE DICTIONARY. The dictionary keeps
# `/writableClaimOfRightRepaymentCreditSection1341` only "so saved returns load: never asked, read
# by nothing"; the credit is now DERIVED from two earlier-year tax figures and reaches Schedule 3
# line 13b only above a $3,000 repayment with the credit method elected. A figure sent here would
# be dropped and the return served complete without it, so until that intake is built the
# field is no longer invited, an amount above 0 is REFUSED by name, and nothing is emitted. The
# schema keeps the field so the refusal can name it; an absent or 0 answer is what it always was.
SECTION_1341_FIELD = "section_1341_credit_cents"
SECTION_1341_FIELDS = frozenset({SECTION_1341_FIELD})


def refuse_section_1341_credit(facts: dict) -> None:
    """a section 1341 credit above 0 is out of coverage at this pin — refused by name rather
    than dropped. Shape errors are `_cents_or_zero`'s, exactly as before."""
    if SECTION_1341_FIELD in facts and _cents_or_zero(facts[SECTION_1341_FIELD]) > 0:
        raise ServiceFactsError(
            f"{SECTION_1341_FIELD} is above 0, and a credit typed as one figure is not how this "
            f"is computed: the credit is the fall in the EARLIER year's tax, so the earlier "
            f"year's tax as filed and as refigured are what decide it. Refused rather than "
            f"computed from a figure nobody can check. On the local page this is asked as its own "
            f"form — what you repaid, and that earlier year's tax both ways — and the return is "
            f"then figured both ways, Publication 525's own rule, and the lower one is used.")
ESTIMATED_PAYMENTS_FIELD = "paid_estimated_taxes"
ESTIMATED_PAYMENTS_AMOUNT_FIELD = "estimated_tax_payments_cents"
ESTIMATED_PAYMENTS_FOLLOWUP_FIELDS = ("estimated_payments_under_different_name",
                                      "estimated_payments_with_former_spouse")
ESTIMATED_PAYMENTS_FIELDS = frozenset({ESTIMATED_PAYMENTS_FIELD, ESTIMATED_PAYMENTS_AMOUNT_FIELD,
                                       *ESTIMATED_PAYMENTS_FOLLOWUP_FIELDS})
# Schedule 1 line 21 — student loan interest. The root question
# (`/hadStudentLoanInterestPayments`) is asked on every return; a yes REACHES whether the loans
# qualify (`/studentLoansQualify`) and the interest paid (`/studentLoanInterestAmount`, Form 1098-E
# box 1) — the two writables the chain wants (studentLoanAdjustment.xml); the engine applies the
# $2,500 cap, the income phase-out and the claimed-dependent rule itself. Measured at the pin on
# wages-single-mid: yes + qualify + $1,500 moves line 11 52,000 → 50,500 and line 24
# 4,115 → 3,935; not-qualify → 0; on wages-single-high (120,000) the phase-out zeroes it; the two
# follow-ups unanswered leave `/agi` and `/totalTax` unresolved. The root answer was once
# attested false and published as an assumption.
# Form 1099-OID — `interest.xml`'s `/originalIssueDiscountReports`, at the pin.
# The nine money boxes that reach a Form 1040 line, by the box each is printed in. NOT carried: box 7
# (a description, free text), box 9 (investment expenses — reaches no line at the pin), boxes 12-14
# (state), and everything that identifies the payer or the recipient.
OID_EMISSION = {
    "original_issue_discount_cents": "writableOriginalIssueDiscount",                  # box 1
    "other_periodic_interest_cents": "writableBox2StatedInterest",                     # box 2
    "early_withdrawal_penalty_cents": "writableEarlyWithdrawalPenalty",                # box 3
    "federal_withholding_cents": "writableTaxWithheld",                                # box 4
    "market_discount_cents": "writableMarketDiscount",                                 # box 5
    "acquisition_premium_cents": "writableAcquisitionPremium",                         # box 6
    "treasury_oid_cents": "writableOriginalIssueDiscountOnTreasuryObligations",        # box 8
    "bond_premium_cents": "writableBondPremium",                                       # box 10
    "tax_exempt_oid_cents": "writableBox11TaxExemptOid",                               # box 11
}
OID_MONEY_FIELDS = tuple(OID_EMISSION)

# Form 1099-INT boxes 2 and 9-13 — the census's unsent line-changing boxes. Sent only when
# supplied: measured on the pinned engine, an unsent one resolves as zero, so a return without them is
# byte-identical to the one before. Box 6 (foreign tax paid) is NOT here: sending it trips the
# engine's own `/knockoutInterestIncome` foreign-tax knockout.
INT_EXTRA_EMISSION = {
    "early_withdrawal_penalty_cents": "writableEarlyWithdrawlPenaltyAmount",           # box 2
    "private_activity_bond_interest_cents": "writableSpecifiedPrivateActivityBondInterest",  # 9
    "market_discount_cents": "writableMarketDiscount",                                 # box 10
    "bond_premium_cents": "writableBondPremium",                                       # box 11
    "treasury_bond_premium_cents": "writableBondPremiumOnTreasuryObligations",         # box 12
    "tax_exempt_bond_premium_cents": "writableBondPremiumOnTaxExemptBond",             # box 13
}

# Form 1099-B — `scheduleD.xml`'s `/form8949Transactions`, one item per transaction (the IRS
# template's one row). Sent: boxes 1b, 1c, 1d, 1e, 1g, 2 and 12. Read so they can be REFUSED by
# name: 1f, 3 (both marks), 4 and 7. Not carried: 1a (free text; the dictionary prints it only),
# boxes 5 and 6 (they change no amount), 8-11 and 13 (the unread-box notice names them), 14-16
# (state), and everything that identifies the payer or the recipient.
B1099_EMISSION = {
    "date_acquired": "writableDateAcquired",                                            # 1b
    "date_sold": "writableDateSold",                                                    # 1c
    "proceeds_cents": "writableProceeds",                                               # 1d
    "cost_basis_cents": "writableCostBasis",                                            # 1e
    "wash_sale_loss_disallowed_cents": "writableAdjustmentAmount",                      # 1g
    "term": "writableIsLongTerm",                                                       # 2
    "basis_reported_to_irs": "writableBasisReportedToIrs",                              # 12
}
B1099_TERM_FIELD = "term"
B1099_REFUSED = {
    "accrued_market_discount_cents": (
        "box 1f (accrued market discount) has an amount — it is ordinary interest income as "
        "well as a Form 8949 column (g) adjustment (code D), and that pair is not in the "
        "covered set"),
    "federal_withholding_cents": (
        "box 4 (federal income tax withheld) has an amount — at this version the engine does "
        "not carry the Form 1099-B box into Form 1040 line 25b, so the tax already paid would "
        "be left out of the return"),
    "collectibles": (
        "box 3 (Collectibles) is checked — a collectibles gain is taxed at up to 28% through "
        "the Schedule D worksheet, and that split is not in the covered set"),
    "qualified_opportunity_fund": (
        "box 3 (QOF) is checked — a qualified opportunity fund disposition is reported with "
        "Form 8997, which is not in the covered set"),
    "loss_not_allowed": (
        "box 7 (loss not allowed based on the amount in 1d) is checked — the part of the loss "
        "that is not allowed is not in the covered set"),
}
B1099_FIELDS = (*B1099_EMISSION, *B1099_REFUSED)
# Box 3's two marks are ASKED, never presumed unchecked: build's list gives them one shared
# spelling and so none, so a page cannot answer them, and an unread Collectibles
# mark would tax a 28% gain at the lower rates as complete. The questions retire when the list
# spells them.
B1099_ASKED_MARKS = ("collectibles", "qualified_opportunity_fund")
OID_TAX_EXEMPT_FIELD = "box2_is_tax_exempt"
OID_FATCA_FIELD = "fatca_filing_requirement"
STUDENT_LOAN_FIELD = "paid_student_loan_interest"
STUDENT_LOAN_REACHED_FIELDS = ("student_loans_qualify", "student_loan_interest_cents")
# IRC 221(e)(1)'s two reductions — the interest an employer paid tax-free under a
# section 127 program (`/writableStudentLoanInterestEmployerPaidSection127`) and the interest paid
# from tax-free qualified tuition program earnings
# (`/writableStudentLoanInterestFromTaxFreeQtpEarnings`). The engine subtracts both BEFORE the
# $2,500 cap, and on a return that claims the deduction (`/flowShowStudentLoansAmount`: paid yes
# AND the loans qualify) leaves line 21 Incomplete until both are answered — a condition of
# allowance, never a silent $0. So both are asked once `student_loans_qualify` is yes; a no
# claims nothing and reaches neither.
STUDENT_LOAN_NETTING_FIELDS = ("student_loan_interest_employer_paid_cents",
                               "student_loan_interest_from_qtp_cents")
STUDENT_LOAN_FIELDS = frozenset({STUDENT_LOAN_FIELD, *STUDENT_LOAN_REACHED_FIELDS,
                                 *STUDENT_LOAN_NETTING_FIELDS})
# Form 1040 line 6c — the lump-sum election for Social Security benefits received for an
# earlier year (`/writableSocialSecurityLumpSumElection`), asked once the return carries a
# benefit statement (`ssa1099s`). A no is the regular method; a yes is the dictionary's own
# `/socialSecurityLumpSumIntakeIncomplete` knockout (measured: the earlier-year figures the
# election needs are not carried here), served with words. With no statement the writable is
# false as a derivation of the input — no benefits, no election — never an assumption. It was
# once answered no on every return and published.
LUMP_SUM_FIELD = "elects_lump_sum_benefits"
# Schedule 1 line 2a (alimony received) and line 19a (alimony paid). Each amount is the
# dictionary's own OPTIONAL raw interview answer (`/writableAlimonyReceivedAmount`,
# `/writableAlimonyPaidAmount`) — invited on every return like `section_1341_credit_cents`, never a
# required gap; absent, `gaps._ABSENT_MEANS` states no alimony was received/paid. Answering an
# amount REACHES its own pre-2019-agreement gate (`/alimonyReceivedPre2019Agreement`,
# `/alimonyPaidPre2019Agreement`), which decides includibility/deductibility under TCJA sec. 11051:
# an amount entered with the gate unanswered resolves the return Incomplete rather than a silent $0
# (the dictionary's own rule) — so the gate, once reached, IS a required gap, the
# `STUDENT_LOAN_REACHED_FIELDS` shape. The recipient's SSN (Schedule 1 line 19b) is documentary and
# does not gate the paid side; it is not carried here. Neither side's printed agreement-date
# line (2b/19c) is carried either — both are print-only companions the dictionary reads back only
# to REFUTE a pre-2019 claim, and this service never emits them, so the paid side's actual gate
# (`/alimonyPaidPre2019AgreementApplies`) falls through to the attestation term for term. Measured
# against profile-alimony (the corpus profile that surfaced the gap): wages $63,480 +
# alimony received $13,200 (gate true) moves Form 1040 line 8 to 13,200.00 and line 9 to 76,680.00;
# alimony paid $5,400 (gate true) then moves line 11 (AGI) to 71,280.00.
ALIMONY_RECEIVED_AMOUNT_FIELD = "alimony_received_cents"
ALIMONY_RECEIVED_GATE_FIELD = "alimony_received_pre2019_agreement"
ALIMONY_PAID_AMOUNT_FIELD = "alimony_paid_cents"
ALIMONY_PAID_GATE_FIELD = "alimony_paid_pre2019_agreement"
ALIMONY_AMOUNT_FIELDS = (ALIMONY_RECEIVED_AMOUNT_FIELD, ALIMONY_PAID_AMOUNT_FIELD)
# IRC 215(d) — alimony the former spouse received as the income of a section 682
# trust is not deductible by the payer (`/writableAlimonyPaidIsSection682TrustIncome`). The engine
# holds `/deductibleAlimonyPaid` Incomplete on a return that CLAIMS the deduction (an amount, and
# the pre-2019 gate not resolved false) until it is answered, and treats it as moot otherwise — so
# it is asked once the paid amount is given AND its pre-2019 gate is yes.
ALIMONY_PAID_TRUST_FIELD = "alimony_paid_section_682_trust"
ALIMONY_GATE_FIELDS = (ALIMONY_RECEIVED_GATE_FIELD, ALIMONY_PAID_GATE_FIELD,
                       ALIMONY_PAID_TRUST_FIELD)
ALIMONY_GATE_TO_AMOUNT = {ALIMONY_RECEIVED_GATE_FIELD: ALIMONY_RECEIVED_AMOUNT_FIELD,
                          ALIMONY_PAID_GATE_FIELD: ALIMONY_PAID_AMOUNT_FIELD,
                          ALIMONY_PAID_TRUST_FIELD: ALIMONY_PAID_AMOUNT_FIELD}
# What each gate is asked after, in the words the two refusals below say it with.
ALIMONY_GATE_ASKED_ONCE = {
    ALIMONY_RECEIVED_GATE_FIELD: f"{ALIMONY_RECEIVED_AMOUNT_FIELD} is answered",
    ALIMONY_PAID_GATE_FIELD: f"{ALIMONY_PAID_AMOUNT_FIELD} is answered",
    ALIMONY_PAID_TRUST_FIELD: f"{ALIMONY_PAID_AMOUNT_FIELD} is answered and "
                              f"{ALIMONY_PAID_GATE_FIELD} is yes"}
ALIMONY_FIELDS = frozenset({*ALIMONY_AMOUNT_FIELDS, *ALIMONY_GATE_FIELDS})
# the Form 1040 page-1 checkbox, printed on EVERY return next to the address block —
# "Check here if your main home, and your spouse's if filing a joint return, was in the U.S. for
# more than half of 2025" — one Boolean for the whole return (`/writableMainHomeInUsOverHalfYear`,
# eitc.xml). It is Publication 596 Rule 14, an eligibility condition for the EIC without a
# qualifying child, and nothing else: no other served line reads it. UNANSWERED READS TRUE — the
# dictionary's own complete-safe alias (`/mainHomeInUsOverHalfYear`, the IsComplete/Switch idiom)
# — so this field is OPTIONAL and invited on every return like `section_1341_credit_cents`/the
# alimony amounts above, never a required gap; absent, `gaps._ABSENT_MEANS` states the favorable
# default the engine already applies. The checkbox is printed unconditionally (every return sees
# it), unlike the eligibility test it feeds, so asking behind a service-side re-derivation of the
# other childless-EIC tests (no qualifying child, the age band, not a dependent) would duplicate
# engine logic this service does not own. Measured against a synthetic single filer, age 30, SSN
# valid for employment, wages $14,000, no dependents: an explicit false zeroes total payments
# (line 33/34, 389.00 -> 0.00) where an absent answer or an explicit true leaves them at 389.00.
# The corpus profile `profile-eitc-main-home` (an explicit false, different wages) showed the
# same shape as a $327.00 gap against the oracle before this field existed to carry it.
MAIN_HOME_FIELD = "main_home_in_us_over_half_year"
MAIN_HOME_FIELDS = frozenset({MAIN_HOME_FIELD})
# Form 8960's sole-trader attestation
# (`/writableSection475eTraderInFinancialInstrumentsOrCommoditiesElection`) — "Is trading in financial instruments or commodities your ONLY trade or business?" One
# answer for the return, no default: with a Schedule C profit or loss and the answer BLANK the
# engine discloses the net investment income line Incomplete, and total tax with it (measured on
# the pinned engine: profile-schedule-c-vehicle, lines 24 and 34 unresolved). Asked once the return carries a
# Schedule C — the engine's own reach is a nonzero net, and an answer on a return whose net is
# exactly 0 is moot and complete-safe. A NO is the ordinary business and computes as before. A
# YES moves the business off Schedule SE and its profit into net investment income, and reaches
# the section 475(a) dealer question per business (row 245) — a route this service does not
# carry, so a yes is refused by name rather than computed.
SOLE_TRADER_FIELD = "only_business_is_trading_securities"
SOLE_TRADER_FIELDS = frozenset({SOLE_TRADER_FIELD})


def sole_trader_question_reached(facts: dict) -> bool:
    """Whether the Form 8960 sole-trader question is reached — a Schedule C."""
    return isinstance(facts, dict) and bool(facts.get("schedule_c"))


def refuse_misplaced_sole_trader_answers(facts: dict) -> None:
    """An answer past the reach is refused by name; a reached one left unanswered is backstopped
    as a question, never defaulted (`gaps.gaps_for` asks first); a yes is out of coverage."""
    reached = sole_trader_question_reached(facts)
    if SOLE_TRADER_FIELD in facts and not reached:
        raise ServiceFactsError(
            f"{SOLE_TRADER_FIELD} is answered but the return carries no Schedule C — the Form "
            f"8960 sole-trader question is asked once a business is present; refused rather "
            f"than dropped")
    if reached and SOLE_TRADER_FIELD not in facts:
        raise FactsSchemaError(
            f"{SOLE_TRADER_FIELD} is a Form 8960 question, asked on every return that carries a "
            f"Schedule C, not a default — answer it (prepare_return asks it as a gap)")
    if reached and facts.get(SOLE_TRADER_FIELD) is True:
        raise ServiceFactsError(
            f"{SOLE_TRADER_FIELD} is yes — a business whose only activity is trading in "
            f"financial instruments or commodities is figured off Schedule SE and through Form "
            f"8960, with a section 475(a) dealer question per business, and that route is not in "
            f"the covered set; refused rather than computed")


def lump_sum_question_reached(facts: dict) -> bool:
    """whether the line 6c question is reached — the return carries a benefit statement."""
    return isinstance(facts, dict) and bool(facts.get("ssa1099s"))


def refuse_misplaced_lump_sum_answers(facts: dict) -> None:
    """an answer past the reach is refused by name; a reached one left unanswered is
    backstopped as a question, never defaulted (`gaps.gaps_for` asks first)."""
    reached = lump_sum_question_reached(facts)
    if LUMP_SUM_FIELD in facts and not reached:
        raise ServiceFactsError(
            f"{LUMP_SUM_FIELD} is answered but the return carries no benefit statement — the "
            f"Form 1040 line 6c election is asked once an SSA-1099 or RRB-1099 is present; "
            f"refused rather than dropped")
    if reached and LUMP_SUM_FIELD not in facts:
        raise FactsSchemaError(
            f"{LUMP_SUM_FIELD} is a Form 1040 line 6c question, asked on every return that "
            f"carries a benefit statement, not a default — answer it (prepare_return asks it "
            f"as a gap)")
    # the earlier-year rows belong to a return that elects. Off that reach they are refused
    # by name rather than dropped; on it, at least one row is required — the election cannot be
    # made without naming a year, which is what the dictionary's own intake guard says.
    rows = facts.get(LUMP_SUM_GROUP) if isinstance(facts, dict) else None
    if rows and not lump_sum_years_reached(facts):
        raise ServiceFactsError(
            f"{LUMP_SUM_GROUP} is answered where the answers so far do not reach it — the "
            f"earlier years a lump-sum payment is for are asked once a return with a benefit "
            f"statement elects the lump-sum method (Form 1040, line 6c); refused rather than "
            f"dropped")
    if lump_sum_years_reached(facts) and not rows:
        raise FactsSchemaError(
            f"{LUMP_SUM_GROUP} is asked once the Form 1040 line 6c election is made — the "
            f"election names the earlier years the payment is for, and without them it cannot "
            f"be figured (prepare_return asks it as a gap)")
    for i, row in enumerate(rows or []):
        if not isinstance(row, dict) or LUMP_SUM_YEAR_FIELD not in row:
            continue                          # the required-field check names it first
        year = row[LUMP_SUM_YEAR_FIELD]
        if not isinstance(year, int) or isinstance(year, bool) or not (
                LUMP_SUM_YEAR_MIN <= year <= LUMP_SUM_YEAR_MAX):
            raise FactsSchemaError(
                f"{LUMP_SUM_GROUP}[{i}].{LUMP_SUM_YEAR_FIELD} is outside the years a lump-sum "
                f"payment can be for. Must be between {LUMP_SUM_YEAR_MIN} and "
                f"{LUMP_SUM_YEAR_MAX}")
    years = [row.get(LUMP_SUM_YEAR_FIELD) for row in rows or [] if isinstance(row, dict)]
    if len(years) != len(set(years)):
        raise ServiceFactsError(
            f"{LUMP_SUM_GROUP} names the same earlier year twice — Publication 915 refigures "
            f"one worksheet per earlier year, so two rows for one year would refigure it "
            f"twice; refused rather than merged")
# Schedule 1 line 11 — educator expenses. The dictionary's `/wasK12Educators` is an enum
# over `/k12EducatorOptions` (neither / tpDid / spouseDid / bothDid — the spouse arms conditioned
# on a joint return) and the amounts are two root writables, `/primaryEducatorExpensesWritable`
# and `/secondaryEducatorExpensesWritable`. Asked in the per-filer-row shape: `k12_educator`
# on every filer row (the primary; the spouse on a joint return, the only status with a spouse
# row), `educator_expenses_cents` reached on that row's yes. The enum is derived from the rows'
# answers after the filers block; each amount lands on its filer's writable. Measured at the pin:
# $250 on wages-single-mid moves line 11 52,000 -> 51,750; $400 serves as 300 (the engine's own
# per-educator cap, applied by the dictionary, never here); a claimed joint return
# (`/isMFJDependent`) takes its answered amount like any other — the dictionary zeroes only an
# UNASKED question there, and this service always sends the enum — so $250 moves its line 11
# 16,000 -> 15,750; a yes without its amount leaves line 11 unresolved. The enum was once
# attested `neither` and published as an assumption.
EDUCATOR_FIELD = "k12_educator"
EDUCATOR_AMOUNT_FIELD = "educator_expenses_cents"
EDUCATOR_FIELDS = frozenset({EDUCATOR_FIELD, EDUCATOR_AMOUNT_FIELD})
EDUCATOR_OPTIONS = {(False, False): "neither", (True, False): "tpDid",
                    (False, True): "spouseDid", (True, True): "bothDid"}


def educator_questions_reached(person) -> list:
    """The educator fields one FILER row's answers reach, in order: the yes/no on every filer
    row, the amount once that row answers yes. A dependent row reaches neither. Read by the
    gaps, the mapper's backstop and the misplaced-answer refusal, so the three cannot disagree."""
    if not isinstance(person, dict) or person.get("role") == "dependent":
        return []
    reached = [EDUCATOR_FIELD]
    if person.get(EDUCATOR_FIELD) is True:
        reached.append(EDUCATOR_AMOUNT_FIELD)
    return reached


def refuse_misplaced_educator_answers(persons: list) -> None:
    """The educator adjustment is the filer's and, on a joint return, the spouse's — a
    dependent's answer moves nothing on this return, and an amount typed on a row that has not
    answered yes is a figure the engine would never read. Both are refused by name rather than
    accepted and dropped."""
    for i, person in enumerate(persons):
        if not isinstance(person, dict):
            continue
        reached = educator_questions_reached(person)
        for field in (EDUCATOR_FIELD, EDUCATOR_AMOUNT_FIELD):
            if field not in person or field in reached:
                continue
            if person.get("role") == "dependent":
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered on a dependent row — the educator "
                    f"expenses adjustment (Schedule 1, line 11) is the filer's and, on a joint "
                    f"return, the spouse's; a dependent's answer moves nothing on this return; "
                    f"refused rather than dropped")
            raise ServiceFactsError(
                f"persons[{i}].{field} is answered where the answers so far do not reach it — "
                f"the amount is asked once that person answers yes to having been a K-12 "
                f"educator; refused rather than dropped")
# Schedule 1 line 20 — the IRA deduction. The dictionary's `/madeIraContributions` is one
# boolean for the return; the amounts are per-filer writables (`/primaryFilerTraditionalIra-
# Contributions`, `/secondaryFilerTraditionalIraContributions`), as are the inherited-IRA answers
# (`/writable{Primary,Secondary}FilerContributedToInheritedIra`). Asked in the per-filer-row
# shape: `made_ira_contributions` on every filer row, the amount and the inherited answer reached
# on that row's yes; the return's boolean is true when any row says yes. Measured at the pin:
# $3,000 on wages-single-mid moves line 11 52,000 -> 49,000; a yes with no amount served a
# deduction of 0 SILENTLY (hence the backstop); $8,000, or any amount paid in to an inherited
# IRA (asked behind the inherited yes, below), fires the dictionary's own
# `/flowKnockoutIraExcessContribution` (served); the annual
# limit, the employer-plan phase-out (the filers' own coverage from W-2 box 13) and the
# spousal-IRA compensation rule are the dictionary's. On a SEPARATE return of a couple who did not
# live apart all year the OTHER spouse's coverage decides the phase-out and resolves false when
# unanswered (measured: covered -> 0, unanswered -> the full deduction), so it is asked there
# (`spouse_covered_by_employer_plan`, `/writableMfsSpouseCoveredByEmployerPlan`). Not asked: the
# Roth amounts and the section 408(o) elections — measured moving nothing at the pin (a Roth
# amount changes no served line and does not enter the excess guard) — REVISED since: the Roth
# amount reaches line 24 through Form 8880 line 1, so it is the third follow-up on a yes.
# REVISED AGAIN, and the "does not enter the excess guard" half was simply false: the
# dictionary's `/writable{Primary,Secondary}FilerRothIraContributions` is IRC 219(c)(1)(B)(ii)(III)'s
# reduction term in the spousal (Kay Bailey Hutchison) limit, so on a JOINT return one spouse's Roth
# contributions cut the compensation left for the other's deduction — and past that cut the excess
# guard's third leg (`/secondaryFilerHasIraExcessContribution`) fires. Measured at the pin
# (12,000 of compensation, the primary 7,000 to a Roth, the spouse 7,000 traditional): served
# complete at 3,146.00 with a 7,000 deduction, where the dictionary allows 5,000 and refuses. The
# boolean was once attested false and published as an assumption.
IRA_FIELD = "made_ira_contributions"
IRA_AMOUNT_FIELD = "traditional_ira_contributions_cents"
IRA_INHERITED_FIELD = "contributed_to_inherited_ira"
# the third follow-up on a yes — the Roth IRA and ABLE contributions. The Roth amount was once
# recorded as moving nothing; it moves line 24 through Form 8880 line 1 (measured: the self-reported
# pair alone gives the credit, and the covered traditional writable does not), so it is asked.
IRA_ROTH_ABLE_FIELD = "roth_ira_and_able_contributions_cents"
IRA_REACHED_FIELDS = (IRA_AMOUNT_FIELD, IRA_INHERITED_FIELD, IRA_ROTH_ABLE_FIELD)
# the amount behind an inherited-IRA yes. A yes was once the dictionary's whole-contribution
# denial and its excess knockout outright; the pinned dictionary denies only the AMOUNT paid in to
# the inherited account (IRC 219(d)(4) — "any amount paid to an inherited individual retirement
# account"), treats that amount as a section 4973(b)(1) excess with nothing allowable, and holds
# the deduction and Form 5329 lines 15-17 Incomplete until it is answered. Measured at the pin on
# wages-single-mid with 3,000 contributed: a yes with nothing more leaves AGI unresolved; 0 serves
# the full 3,000 deduction; 1,000 fires `/flowKnockoutIraExcessContribution`. Asked once the
# inherited answer is yes, never defaulted; no more than the traditional amount on the same row.
IRA_INHERITED_AMOUNT_FIELD = "inherited_ira_contribution_cents"
# how much of that combined amount was the Roth IRA half. Form 8880 line 1 adds Roth and
# ABLE together, which is why the combined figure is asked; IRC 219(c)(1)(B)(ii)(III) counts the
# Roth half ALONE, so the combined figure cannot be routed to the dictionary's reduction term —
# doing so would cut an ABLE contributor's spousal limit by money the statute does not count and
# refuse a return it allows. Asked where it can change a figure and nowhere else (see
# `ira_roth_split_reached`): the dictionary reads that term only in the spousal computation.
IRA_ROTH_SPLIT_FIELD = "roth_ira_contributions_cents"
IRA_ROTH_EMISSION = {True: "/writablePrimaryFilerRothIraContributions",
                     False: "/writableSecondaryFilerRothIraContributions"}
IRA_FIELDS = frozenset({IRA_FIELD, *IRA_REACHED_FIELDS, IRA_INHERITED_AMOUNT_FIELD,
                        IRA_ROTH_SPLIT_FIELD})
IRA_COVERAGE_FIELD = "spouse_covered_by_employer_plan"
IRA_EMISSION = {
    True: {IRA_AMOUNT_FIELD: "/primaryFilerTraditionalIraContributions",
           IRA_INHERITED_FIELD: "/writablePrimaryFilerContributedToInheritedIra",
           IRA_INHERITED_AMOUNT_FIELD: "/writablePrimaryFilerAmountPaidToInheritedIra"},
    False: {IRA_AMOUNT_FIELD: "/secondaryFilerTraditionalIraContributions",
            IRA_INHERITED_FIELD: "/writableSecondaryFilerContributedToInheritedIra",
            IRA_INHERITED_AMOUNT_FIELD: "/writableSecondaryFilerAmountPaidToInheritedIra"},
}


def ira_questions_reached(person) -> list:
    """The IRA fields one FILER row's answers reach, in order: the yes/no on every filer row,
    the amount and the inherited-IRA answer once that row answers yes, and the amount paid in to
    the inherited account once that answer is yes. A dependent row reaches none. Read by the gaps,
    the mapper's backstop and the misplaced-answer refusal."""
    if not isinstance(person, dict) or person.get("role") == "dependent":
        return []
    reached = [IRA_FIELD]
    if person.get(IRA_FIELD) is True:
        reached.extend(IRA_REACHED_FIELDS)
        if person.get(IRA_INHERITED_FIELD) is True:
            reached.insert(reached.index(IRA_INHERITED_FIELD) + 1, IRA_INHERITED_AMOUNT_FIELD)
    return reached


def ira_roth_split_reached(facts: dict, person_index: int) -> bool:
    """whether this filer row is asked how much of its combined Roth-and-ABLE amount went to
    a Roth IRA. Three gates, each measured: a JOINT return (the dictionary reads the Roth term only
    in `/ssbw{Primary,Secondary}FilerSpousalCombinedCompensation`, so no other status can move);
    a filer row that answered yes to contributing; and a POSITIVE combined amount (a 0 splits into
    two zeroes, and asking would be a screen that changes nothing)."""
    if not isinstance(facts, dict) or facts.get("filing_status") != "mfj":
        return False
    persons = facts.get("persons") or []
    person = persons[person_index] if person_index < len(persons) else None
    if not isinstance(person, dict) or person.get("role") not in ("primary", "spouse"):
        return False
    if person.get(IRA_FIELD) is not True:
        return False
    return _cents_or_zero(person.get(IRA_ROTH_ABLE_FIELD)) > 0


def ira_coverage_question_reached(facts: dict) -> bool:
    """whether the separate-return coverage question is reached — a separate return, the
    primary answered yes to contributing, and the lived-together chain has settled the
    couple as NOT apart all year. Unsettled (the chain's own gaps come first) is not reached."""
    if not isinstance(facts, dict) or facts.get("filing_status") != "mfs":
        return False
    primary = next((p for p in facts.get("persons") or []
                    if isinstance(p, dict) and p.get("role") == "primary"), None)
    if primary is None or primary.get(IRA_FIELD) is not True:
        return False
    together = facts.get("lived_with_spouse_all_year")
    if together is True:
        return True
    if together is False:
        return facts.get("months_lived_with_spouse") in ("more_than_six_months",
                                                          "six_months_or_less")
    return False


def refuse_misplaced_ira_answers(facts: dict) -> None:
    """The IRA questions belong to filer rows, the amount and the inherited answer to a row
    that said yes, and the coverage question to a separate return that reaches it. Each
    misplaced answer is refused by name rather than accepted and dropped (a non-separate return
    carrying the coverage answer is refused by the status-root rule)."""
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict):
            continue
        reached = ira_questions_reached(person)
        if ira_roth_split_reached(facts, i):
            reached = [*reached, IRA_ROTH_SPLIT_FIELD]
        for field in (IRA_FIELD, *IRA_REACHED_FIELDS, IRA_INHERITED_AMOUNT_FIELD,
                      IRA_ROTH_SPLIT_FIELD):
            if field not in person or field in reached:
                continue
            if field == IRA_INHERITED_AMOUNT_FIELD and person.get("role") != "dependent":
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered where the answers so far do not reach it "
                    f"— the amount paid in to an inherited IRA is asked once that person answers "
                    f"yes to contributing to an IRA and yes to contributing to an inherited one; "
                    f"refused rather than dropped")
            if field == IRA_ROTH_SPLIT_FIELD and person.get("role") != "dependent":
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered where the answers so far do not reach it "
                    f"— the Roth half of the combined amount is asked on a JOINT return, on a "
                    f"filer row that contributed, once that row reports a combined Roth and ABLE "
                    f"amount above 0; refused rather than dropped")
            if person.get("role") == "dependent":
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered on a dependent row — the IRA deduction "
                    f"(Schedule 1, line 20) is the filer's and, on a joint return, the "
                    f"spouse's; a dependent's answer moves nothing on this return; refused "
                    f"rather than dropped")
            raise ServiceFactsError(
                f"persons[{i}].{field} is answered where the answers so far do not reach it — "
                f"it is asked once that person answers yes to contributing to an IRA; refused "
                f"rather than dropped")
    if (facts.get("filing_status") == "mfs" and IRA_COVERAGE_FIELD in facts
            and not ira_coverage_question_reached(facts)):
        raise ServiceFactsError(
            f"{IRA_COVERAGE_FIELD} is answered where the answers so far do not reach it — it "
            f"is asked on a separate return once the filer answers yes to contributing to an "
            f"IRA and the couple did not live apart all year; refused rather than dropped")


# the residence state — `/filerResidenceAndIncomeState`, the dictionary's enum over
# `/scopedStateOptions` (the 50 states, DC, moreThanOne, noneOfThese; its order) — asked on
# every return. Measured at the pin: no answer moves a served figure; `noneOfThese` fires
# `/flowKnockoutUnsupportedState`, a community-property state on a separate return fires
# `/knockoutSubjectToCommunityPropertyLaws` (both the dictionary's own, served), and
# `ak` once made `/eligibleForApf` true (no longer: the dictionary does not infer
# the dividend from residence) — the Alaska Permanent Fund dividend questions below.
RESIDENCE_STATE_FIELD = "residence_state"
RESIDENCE_STATES = ("moreThanOne", "al", "ak", "az", "ar", "ca", "co", "ct", "de", "dc", "fl", "ga",
                    "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn",
                    "ms", "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok",
                    "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi",
                    "wy", "noneOfThese")
# The Alaska Permanent Fund dividend pair. The dictionary wants the filer's answer on EVERY
# return (`/aboutYouIsComplete` wraps it in IsComplete) and the spouse's on every JOINT return
# (spouseSection.xml, unconditionally inside the mfj branch) — not only behind an `ak`
# residence, which is where the dividend is possible. So the filer's is asked on every return
# and the spouse's on every joint one. A yes is refused by name — Form 1099-MISC Alaska PFD
# income is not a covered stream, and the dictionary computes a yes with no 1099-MISC entries
# SILENTLY (measured: no knockout, no figure) — so it never crosses. With both answered no the
# two writables and `/hasCompletedApfSection` (the section's Done marker) go through.
ALASKA_PFD_FIELDS = frozenset({"received_alaska_pfd", "spouse_received_alaska_pfd"})

# Form 1099-SA HSA distributions (Form 8889 Part II). The box 3 code as printed, mapped to
# the dictionary's own option names; the per-filer 20%-tax exception PAIR (amount AND reason,
# both required together) on the persons row.
HSA_GROUP = "hsa_distributions"
# Form 1040 line 6c's lump-sum election (IRC 86(e)) computes. The election was asked and a
# yes was the dictionary's own `/socialSecurityLumpSumIntakeIncomplete` refusal, because the
# earlier-year figures were not carried. They are a collection in the dictionary, one row per
# earlier year, and all nine of a row's writables are required — `earlierYearIntakeAnswered` is an
# All over the nine, with no gate order between them (read at the pin). The year picks the
# worksheet the engine refigures with (2 for 1994 and later, 3 for 1993 and earlier) and both arms
# read the same nine. Measured on wages-single-ssa: taxable benefits 10,200.00 -> 5,100.00 and
# total tax 5,339.00 -> 4,727.00 with a 2023 row; an earlier year whose income was HIGHER moves
# nothing, so answering can never make a return worse.
LUMP_SUM_GROUP = "ssa_lump_sum_years"
LUMP_SUM_YEAR_FIELD = "earlier_year"
LUMP_SUM_YEAR_MIN, LUMP_SUM_YEAR_MAX = 1984, 2024
LUMP_SUM_ITEM_FIELDS = ("earlier_year", "lump_sum_portion_cents", "benefits_received_cents",
                        "adjusted_gross_income_cents", "exclusions_cents",
                        "tax_exempt_interest_cents", "taxable_benefits_reported_cents",
                        "filed_jointly", "mfs_lived_with_spouse")
LUMP_SUM_EMISSION = {
    "earlier_year": "writableEarlierYear",
    "lump_sum_portion_cents": "writableEarlierYearLumpSumPortion",
    "benefits_received_cents": "writableEarlierYearBenefitsReceived",
    "adjusted_gross_income_cents": "writableEarlierYearAdjustedGrossIncome",
    "exclusions_cents": "writableEarlierYearExclusions",
    "tax_exempt_interest_cents": "writableEarlierYearTaxExemptInterest",
    "taxable_benefits_reported_cents": "writableEarlierYearTaxableBenefitsReported",
    "filed_jointly": "writableEarlierYearFiledJointly",
    "mfs_lived_with_spouse": "writableEarlierYearMfsLivedWithSpouse",
}
LUMP_SUM_BOOLEAN_FIELDS = frozenset({"filed_jointly", "mfs_lived_with_spouse"})


def lump_sum_years_reached(facts: dict) -> bool:
    """whether the earlier-year rows are asked — the return carries a benefit statement and
    the filer elected the lump-sum method. The dictionary reads them nowhere else."""
    return (lump_sum_question_reached(facts)
            and isinstance(facts, dict) and facts.get(LUMP_SUM_FIELD) is True)
HSA_CODE_FIELD = "hsa_distribution_code"
HSA_CODES = {"1": "normalDistribution", "2": "excessContributions", "3": "disability",
             "4": "deathOtherThanCode6", "5": "prohibitedTransaction",
             "6": "deathDistributionAfterYear"}
HSA_EXCEPTION_AMOUNT_FIELD = "hsa_exception_amount_cents"
HSA_EXCEPTION_REASON_FIELD = "hsa_exception_reason"
HSA_EXCEPTION_FIELDS = (HSA_EXCEPTION_AMOUNT_FIELD, HSA_EXCEPTION_REASON_FIELD)
HSA_EXCEPTION_REASONS = {"age65": "age65", "disability": "disability",
                         "death_of_beneficiary": "deathOfBeneficiary", "none": "none"}
# The dictionary admits box 3 code 3 (disability) beside code 1 — its knockout now
# reads "a distribution code other than 1, 2 or 3" — and moved that code's refusal to the
# attestation residue: a filer with a taxable distribution who has not answered the pair is
# refused. So the pair is reached under code 3 too (measured: 400.00 taxable, 4,243.00 with no
# exception and 4,163.00 with the disability exception — code 1's own figures). Code 2 is
# admitted by the dictionary as well and stays THIS service's refusal by name (the
# withdrawn-excess-contribution route is not carried), so it never reaches here.
HSA_CODES_ADMITTED = ("1", "3")
HSA_EXCEPTION_AGE = 66   # the dictionary derives the exception for a filer 66+ at the close

# Form 2441 child and dependent care expenses. A fact group `care_providers` (line 1: who was
# paid, the household-employee column, the amount) and a per-person `care_expenses_cents` (line 2
# column (d)) on a qualifying person's row. Measured at the pin: the credit reads the per-person
# amounts, one organization provider (synthetic identity) closes the section, and every qualifying
# row without an answer must be told "no expenses" or the section stalls.
CDCC_GROUP = "care_providers"
CARE_EXPENSES_FIELD = "care_expenses_cents"
CDCC_PROVIDER_TYPE_FIELD = "provider_type"
CDCC_HOUSEHOLD_EMPLOYEE_FIELD = "is_household_employee"
CDCC_AMOUNT_FIELD = "amount_paid_cents"
CDCC_PROVIDER_TYPES = ("organization", "tax_exempt_organization", "individual")
CDCC_QUALIFYING_AGE = 13   # a dependent under 13 at the close, or who turned 13 after January 1


def _birth_year_month(person: dict):
    year = person.get("birth_year")
    if not isinstance(year, int) or isinstance(year, bool):
        return None, None
    month = person.get("birth_month", DEFAULT_BIRTH_MONTH)
    if not isinstance(month, int) or isinstance(month, bool):
        month = DEFAULT_BIRTH_MONTH
    return year, month


# Form 2441's other qualifying-person arm. Measured at the pin (wages-and-child-single-cdcc,
# expenses 3,000): a claimed dependent who is unable to care for themselves is a qualifying
# person at 15, 20 and the January-of-boundary 13-year-old (a qualifying relative too) — credit 600
# where the age arm alone gives 0. Asked at 13 or older by birth year; inert under 13 and in
# February–December of the boundary year, where the age arm already qualifies the row (measured:
# the same total tax with a yes or a no); the January-of-boundary cohort with a yes is
# day-invariant (the arm reads no birthday). Nothing outside the CDCC section reads it.
UNABLE_TO_CARE_FIELD = "unable_to_care_for_self"


def unable_to_care_question_reached(person: dict, tax_year: int = 2025) -> bool:
    """Where the answer DECIDES: a claimed dependent's row 13 or older at the close of the year
    — asked there as a required gap (the return stops with the question); a younger row
    qualifies on age alone (inert, measured) and an answer on it is accepted unasked."""
    if not isinstance(person, dict) or person.get("role") != "dependent":
        return False
    year, _month = _birth_year_month(person)
    return year is not None and tax_year - year >= CDCC_QUALIFYING_AGE


def refuse_misplaced_unable_to_care(persons: list) -> None:
    """The answer belongs on a dependent's row; a filer's own incapacity is
    `is_permanently_disabled` (the Form 2441 filer arm). Refused by name rather than dropped."""
    for i, person in enumerate(persons):
        if (isinstance(person, dict) and UNABLE_TO_CARE_FIELD in person
                and person.get("role") != "dependent"):
            raise ServiceFactsError(
                f"persons[{i}].{UNABLE_TO_CARE_FIELD} is answered on a filer row — Form 2441 "
                f"reads it of a claimed dependent; a filer who is unable to care for themselves "
                f"is entered with is_permanently_disabled; refused rather than dropped")


def care_expense_day_ambiguous(person: dict, tax_year: int = 2025) -> bool:
    """the synthesized-day posture. A dependent born in January of `tax_year - 13` turned 13 on a day
    this service does not carry: born January 1 they are not a qualifying person (they did not
    turn 13 AFTER January 1), born January 2-31 they are. The mapper synthesizes day 01, which
    would silently drop the credit for the ~30/31 — so that one cohort's answer is refused.
    a yes to `unable_to_care_for_self` qualifies them on the other arm, which reads no
    birthday (measured: the January cohort with a yes computes the full credit) — not
    ambiguous then."""
    if not isinstance(person, dict) or person.get("role") != "dependent":
        return False
    if person.get(UNABLE_TO_CARE_FIELD) is True:
        return False
    year, month = _birth_year_month(person)
    return year == tax_year - CDCC_QUALIFYING_AGE and month == 1


def care_expense_question_reached(facts: dict, person_index: int, tax_year: int = 2025) -> bool:
    """Whether one persons row is a Form 2441 qualifying person on what the service sends,
    mirroring the dictionary (measured at the pin):

      * a claimed dependent under 13 at the close of the year, or who turned 13 after January 1
        (born in `tax_year - 13`: month 1 with the synthesized day 01 is NOT — the day-ambiguous
        cohort `care_expense_day_ambiguous` refuses — months 2-12 are), or, at any age, who
        is unable to care for themselves (`unable_to_care_for_self` yes, a required gap on a
        row 13 or older, never defaulted; measured at 15, 20 and the January-of-boundary 13-year-old);
      * a filer, primary or spouse, on a joint return, permanently and totally disabled
        (`is_permanently_disabled`), who lived with their spouse all year or more than six months
        (the lived-together chain's own answers; unanswered, that cheaper gap is asked first).

    `tax_year` defaults to the pinned year for the same reason `hsa_exception_questions_reached`
    does: the mapper passes the request's, the gaps loop the default, and ty2025 is the only
    year mapped."""
    if not isinstance(facts, dict):
        return False
    persons = facts.get("persons") or []
    if not 0 <= person_index < len(persons) or not isinstance(persons[person_index], dict):
        return False
    person = persons[person_index]
    role = person.get("role")
    if role == "dependent":
        year, month = _birth_year_month(person)
        if year is None:
            return False
        age = tax_year - year
        return (age < CDCC_QUALIFYING_AGE or (age == CDCC_QUALIFYING_AGE and month > 1)
                or person.get(UNABLE_TO_CARE_FIELD) is True)
    if role not in ("primary", "spouse") or facts.get("filing_status") != "mfj":
        return False
    if person.get("is_permanently_disabled") is not True:
        return False
    return (facts.get("lived_with_spouse_all_year") is True
            or facts.get("months_lived_with_spouse") == "more_than_six_months")


def care_expenses_entered(facts: dict) -> int:
    """The sum of every persons row's `care_expenses_cents` (ints above zero)."""
    total = 0
    for person in (facts.get("persons") or []) if isinstance(facts, dict) else []:
        if not isinstance(person, dict):
            continue
        v = person.get(CARE_EXPENSES_FIELD)
        if isinstance(v, int) and not isinstance(v, bool) and v > 0:
            total += v
    return total


# Form W-2 box 10 and Form 2441 Part III. Measured at the pin (wages-and-child-single-cdcc:
# AGI 48,250, expenses 3,000, credit 600): box 10 of 3,000 excludes the whole 3,000 and the credit
# falls to 0 (line 24 865 → 1,465); 6,000 excludes 3,000 and taxes 3,000 on line 1e (1,825);
# without expenses, or with no qualifying person, every dollar is taxable; the plan maximum caps
# the exclusion (2,000 → 1,000 taxable); line 14 forfeited reduces the benefit (500 → excluded
# 2,500, credit 100); line 13 carryover adds to it (1,000 → 1,000 taxable); a separate return's
# limit is 2,500. Unanswered, the plan maximum and the line 14 yes/no STALL Part III; the
# sole-proprietorship benefit and the line 13 pair complete with the dictionary's own meaning
# (0 and no). Spouse-only box 10 wants the spouse's plan maximum alone. A joint return where
# both spouses report a benefit and either earned less than the expenses is the dictionary's
# own /flowKnockoutBenefitsDistribution (measured: wages 2,000 / 1,000, two qualifying persons,
# 6,000 of expenses, box 10 on both), served with words; the split it wants is not entered.
def _cents_or_zero(v) -> int:
    """A reach predicate reads a non-integer as absent; the mapper's own type refusal names it."""
    return v if isinstance(v, int) and not isinstance(v, bool) else 0


def w2_box10_total(facts: dict, person_index: int) -> int:
    """This filer's Form W-2 box 10 across their W-2s."""
    return sum(_cents_or_zero(w2.get(W2_BOX10_FIELD)) for w2 in (facts.get("w2s") or [])
               if isinstance(w2, dict) and w2.get("person") == person_index)


def _has_own_business(facts: dict, person_index: int) -> bool:
    """A Schedule C or a partnership K-1 on this filer's row — the only sources of a dependent
    care benefit that is not on a Form W-2 (Form 2441 line 12's own instruction)."""
    return (any(isinstance(it, dict) and it.get("person") == person_index
                for it in (facts.get("schedule_c") or []))
            or any(isinstance(it, dict) and it.get("person") == person_index
                   and it.get("source") == "partnership" for it in (facts.get("k1s") or [])))


def dcb_reported_by(facts: dict, person_index: int) -> bool:
    """The dictionary's /hasReported{Primary,Secondary}FilerDependentCareBenefits: box 10 on any
    of the filer's W-2s, or their own sole-proprietorship benefit, above 0."""
    persons = facts.get("persons") or []
    if not 0 <= person_index < len(persons) or not isinstance(persons[person_index], dict):
        return False
    person = persons[person_index]
    if person.get("role") not in ("primary", "spouse"):
        return False
    # the sole-proprietorship benefit counts only where its own question is reached (a
    # business on the return) — anywhere else it is a misplaced answer, refused by name
    return (w2_box10_total(facts, person_index) > 0
            or (_has_own_business(facts, person_index)
                and _cents_or_zero(person.get(DCB_SELF_EMPLOYED_FIELD)) > 0))


def dcb_reported(facts: dict) -> bool:
    return any(dcb_reported_by(facts, i) for i in range(len(facts.get("persons") or [])))


def dcb_person_questions_reached(facts: dict, person_index: int) -> list:
    """The Part III questions one FILER row reaches, in the ask order: the sole-proprietorship
    benefit (optional, 0 when absent) once the filer's W-2s carry box 10 or the return carries
    their Schedule C or partnership K-1; the plan maximum (required — Part III stalls without
    it) once the filer reports a benefit either way. A dependent row reaches nothing."""
    persons = facts.get("persons") or []
    if not 0 <= person_index < len(persons) or not isinstance(persons[person_index], dict):
        return []
    if persons[person_index].get("role") not in ("primary", "spouse"):
        return []
    reached = []
    if w2_box10_total(facts, person_index) > 0 or _has_own_business(facts, person_index):
        reached.append(DCB_SELF_EMPLOYED_FIELD)
    if dcb_reported_by(facts, person_index):
        reached.append(DCB_PLAN_MAX_FIELD)
    return reached


def dcb_root_questions_reached(facts: dict) -> list:
    """Form 2441 lines 13 and 14, reached once any filer reports a benefit: the carryover
    (optional, none when absent) then the forfeited amount (required — the dictionary stalls
    without its yes/no)."""
    return [DCB_CARRYOVER_FIELD, DCB_FORFEITED_FIELD] if dcb_reported(facts) else []


def refuse_misplaced_dependent_care_benefits(facts: dict) -> None:
    """A Part III answer past its reach is refused by name rather than dropped (a
    dependent's row reaches nothing; the plan maximum is a reporting filer's; a
    sole-proprietorship benefit wants that business on the return; lines 13 and 14 want a
    reported benefit — a prior-year carryover with no benefit this year is not carried). A plan
    maximum of 0 beside a reported benefit is refused: a section 129 plan states its limit, and
    a 0 makes every dollar of the benefit taxable in silence (measured)."""
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict):
            continue
        reached = dcb_person_questions_reached(facts, i)
        for field in DCB_PERSON_FIELDS:
            if field in person and field not in reached:
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered but the Form 2441 Part III questions do "
                    f"not reach it with the facts given (the plan maximum is asked of a filer "
                    f"whose Form W-2 box 10 or own sole-proprietorship benefit is above 0; the "
                    f"sole-proprietorship benefit of a filer with box 10, a Schedule C, or a "
                    f"partnership K-1 on the return; a dependent's row reaches neither); "
                    f"refused rather than dropped")
        v = person.get(DCB_PLAN_MAX_FIELD)
        if (DCB_PLAN_MAX_FIELD in reached and isinstance(v, int) and not isinstance(v, bool)
                and v <= 0):
            raise ServiceFactsError(
                f"persons[{i}].{DCB_PLAN_MAX_FIELD} is 0 beside dependent care benefits above "
                f"0 — a dependent care assistance plan states the most it allows for the year, "
                f"and a 0 here makes every dollar of the benefit taxable in silence (measured); "
                f"refused rather than computed on 0")
    reached = dcb_root_questions_reached(facts)
    for field in sorted(DCB_ROOT_FIELDS):
        if field in facts and field not in reached:
            raise ServiceFactsError(
                f"{field} is answered but no filer reports dependent care benefits (Form W-2 "
                f"box 10, or a benefit from their own sole proprietorship or partnership) — "
                f"Form 2441 Part III's lines 13 and 14 are read only then, and a prior-year "
                f"carryover with no benefit this year is not carried here; refused rather "
                f"than dropped")


# Form 2441 Worksheet A — the second credit for 2024 care expenses paid in 2025 (i2441's
# Worksheet A, thirteen lines and ten inputs, all shipping in the dictionary). The service carried
# none, so `/cdccHasCreditForPriorYearExpenses` was never answered and Worksheet A's line 13 fell
# back to a hardcoded $0: the credit was silently understated, taxpayer-adverse. Measured on
# wages-and-child-single-cdcc (2024 line 3 = 3,000; 1,000 paid in 2025; one qualifying person in
# 2024; no 2024 benefits; the smaller 2024 earned income 30,000; 2024 line 6 = 2,000; 2024 AGI =
# 40,000): the prior-year credit is 220.00 and line 24 falls 865.00 → 645.00; on
# mfj-disabled-spouse-cdcc-combat-pay 636.00 → 416.00; claimed the maximum in 2024 computes 0.
# The amount reaches Form 1040 only through Form 2441 line 9b, so it moves money only on a return
# with 2025 care expenses — which is exactly where the root is invited.
WORKSHEET_A_ROOT_FIELD = "paid_prior_year_care_expenses_this_year"
WORKSHEET_A_CLAIMED_FIELD = "prior_year_credit_claimed"
WORKSHEET_A_CLAIMED_MAX_FIELD = "prior_year_credit_claimed_maximum"
WORKSHEET_A_CARRY_FIELDS = (
                             "prior_year_form_2441_line_3_cents",
                             "prior_year_expenses_paid_this_year_cents",
                             "prior_year_had_two_or_more_qualifying_persons",
                             "prior_year_excluded_or_deducted_benefits_cents",
                             "prior_year_lower_earned_income_cents",
                             "prior_year_form_2441_line_6_cents",
                             "prior_year_agi_cents",)
WORKSHEET_A_FIELDS = (WORKSHEET_A_ROOT_FIELD, WORKSHEET_A_CLAIMED_FIELD,
                      WORKSHEET_A_CLAIMED_MAX_FIELD, *WORKSHEET_A_CARRY_FIELDS)
WORKSHEET_A_ROOT_FIELDS = frozenset(WORKSHEET_A_FIELDS)
WORKSHEET_A_PATHS = {
    "prior_year_form_2441_line_3_cents": "/writableCdccPriorYearForm2441Line3",
    "prior_year_expenses_paid_this_year_cents": "/writableCdccPriorYearExpensesPaidInCurrentYear",
    "prior_year_had_two_or_more_qualifying_persons": "/writableCdccPriorYearHadTwoOrMoreQualifyingPersons",
    "prior_year_excluded_or_deducted_benefits_cents": "/writableCdccPriorYearExcludedOrDeductedBenefits",
    "prior_year_lower_earned_income_cents": "/writableCdccPriorYearLowerEarnedIncome",
    "prior_year_form_2441_line_6_cents": "/writableCdccPriorYearAmountCreditWasFiguredOn",
    "prior_year_agi_cents": "/writableCdccPriorYearAgi",
}


def worksheet_a_root_reached(facts: dict) -> bool:
    """the root is invited on a return that files Form 2441 — a qualifying person with 2025
    care expenses. Absent it is sent as no and stated (the dictionary's own $0 fallback, said out
    loud), which also resolves `/knockoutCdccWorksheetA` false instead of leaving it Incomplete."""
    return care_providers_question_reached(facts)


def worksheet_a_questions_reached(facts: dict) -> list:
    """the chain behind a yes, in the dictionary's own order — did you claim the credit for
    2024; behind that yes only, did you claim it on the maximum expenses (i2441's test is one
    conjunction, and claimed-max behind a no is never read — measured); then the seven carry-ins
    from the 2024 return. Claiming the maximum ends the chain: Worksheet A computes 0 (measured)."""
    if not isinstance(facts, dict) or not worksheet_a_root_reached(facts):
        return []
    if facts.get(WORKSHEET_A_ROOT_FIELD) is not True:
        return [WORKSHEET_A_ROOT_FIELD]
    reached = [WORKSHEET_A_ROOT_FIELD, WORKSHEET_A_CLAIMED_FIELD]
    if facts.get(WORKSHEET_A_CLAIMED_FIELD) is True:
        reached.append(WORKSHEET_A_CLAIMED_MAX_FIELD)
        if facts.get(WORKSHEET_A_CLAIMED_MAX_FIELD) is not False:
            return reached
    elif facts.get(WORKSHEET_A_CLAIMED_FIELD) is not False:
        return reached
    return reached + list(WORKSHEET_A_CARRY_FIELDS)


def refuse_misplaced_worksheet_a_answers(facts: dict) -> None:
    """an answer the chain does not reach is refused by name rather than dropped or sent."""
    if not isinstance(facts, dict):
        return
    reached = worksheet_a_questions_reached(facts)
    for field in WORKSHEET_A_FIELDS:
        if field in facts and field not in reached:
            raise ServiceFactsError(
                f"{field} is answered where the answers so far do not reach it — Form 2441's "
                f"Worksheet A is asked on a return with 2025 care expenses, behind a yes to "
                f"{WORKSHEET_A_ROOT_FIELD}, and the 2024 figures behind a claim that was not for "
                f"the maximum expenses allowed; refused rather than dropped")


def care_providers_question_reached(facts: dict) -> bool:
    """The providers group is asked once any person carries care expenses above zero (Form 2441
    line 1 must name who was paid before line 2's amounts count)."""
    return care_expenses_entered(facts) > 0


def refuse_misplaced_care_expenses(facts: dict, tax_year: int = 2025) -> None:
    """`care_expenses_cents` belongs on a qualifying person's row; anywhere else it is
    refused by name rather than dropped (measured: the dictionary computes a silent zero for a
    non-qualifying person). The January cohort of the boundary year is refused as day-ambiguous.
    A providers group beside no expenses at all is refused too — line 1 names who was paid for
    the care on line 2, and without line 2 the credit is a silent zero."""
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict) or CARE_EXPENSES_FIELD not in person:
            continue
        if care_expense_question_reached(facts, i, tax_year):
            continue
        if care_expense_day_ambiguous(person, tax_year):
            raise ServiceFactsError(
                f"persons[{i}].{CARE_EXPENSES_FIELD} is answered on a dependent born in January "
                f"{tax_year - CDCC_QUALIFYING_AGE} — whether they turned 13 after January 1 "
                f"{tax_year} (Form 2441's qualifying-person test) turns on the birth day, and "
                f"this service has no birth day; refused rather than guessed (a yes to "
                f"persons[{i}].{UNABLE_TO_CARE_FIELD} qualifies them on the other arm, which "
                f"reads no birthday)")
        if person.get("role") == "dependent":
            raise ServiceFactsError(
                f"persons[{i}].{CARE_EXPENSES_FIELD} is answered on a dependent who is not a "
                f"qualifying person for Form 2441 — a claimed dependent under 13 at the close of "
                f"{tax_year}, or who turned 13 after January 1; a dependent 13 or older qualifies "
                f"only if unable to care for themselves — answer persons[{i}]."
                f"{UNABLE_TO_CARE_FIELD} yes if so; refused rather than dropped (the engine "
                f"would compute a silent zero)")
        raise ServiceFactsError(
            f"persons[{i}].{CARE_EXPENSES_FIELD} is answered on a filer row the engine does not "
            f"treat as a qualifying person — a filer qualifies only on a joint return, permanently "
            f"and totally disabled, having lived with their spouse more than half the year; "
            f"refused rather than dropped (the engine would compute a silent zero)")
    if (facts.get(CDCC_GROUP) or []) and not care_providers_question_reached(facts):
        raise ServiceFactsError(
            f"{CDCC_GROUP} is filled while no person carries care expenses above 0 — Form 2441 "
            f"line 1 names who was paid for the care on line 2; enter each qualifying person's "
            f"expenses (persons[].{CARE_EXPENSES_FIELD}) or remove the providers; refused rather "
            f"than served with the credit at zero")


def refuse_malformed_care_providers(items: list) -> None:
    """The provider type is the schema's own enum, refused by name outside it."""
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        kind = item.get(CDCC_PROVIDER_TYPE_FIELD)
        if kind is not None and kind not in CDCC_PROVIDER_TYPES:
            raise FactsSchemaError(
                f"{CDCC_GROUP}[{i}].{CDCC_PROVIDER_TYPE_FIELD} must be one of "
                f"{', '.join(CDCC_PROVIDER_TYPES)}, got {kind!r}")


# Form 1095-A (Form 8962, the premium tax credit). A fact group `f1095as` carrying the
# form's own Part III grid — lines 21-32, columns A (enrollment premiums), B (the applicable
# SLCSP premium), C (advance payment of the credit) — as 36 optional cents fields; and the
# root questions a form reaches (Form 8962 line 9's gate, the two below-poverty questions, the
# enrollment-family immigration question, line 2b, the separate-return exception pair).
# Measured at the pin: a month is a coverage month when column A is above zero; a 12-month
# level policy closes on the annual route (line 33 totals), anything else on the monthly route;
# annual totals on a partial-year policy compute a silent zero; one form per return.
PTC_GROUP = "f1095as"
PTC_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
PTC_MONTH_TITLES = {"jan": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr", "may": "May", "jun": "Jun",
                    "jul": "Jul", "aug": "Aug", "sep": "Sep", "oct": "Oct", "nov": "Nov", "dec": "Dec"}
PTC_MONTH_NAMES = {"jan": "January", "feb": "February", "mar": "March", "apr": "April", "may": "May",
                   "jun": "June", "jul": "July", "aug": "August", "sep": "September",
                   "oct": "October", "nov": "November", "dec": "December"}
# (service column, the dictionary's monthly writable stem, the printed column letter)
PTC_COLUMNS = (("premium", "Premium", "A"), ("slcsp", "SlcspPremium", "B"), ("aptc", "AptcPremium", "C"))


def ptc_field(month: str, column: str) -> str:
    return f"{month}_{column}_cents"


PTC_ITEM_FIELDS = tuple(ptc_field(m, c) for m in PTC_MONTHS for c, _stem, _letter in PTC_COLUMNS)
PTC_ALLOCATION_FIELD = "allocating_policy_or_alternative_calculation"        # Form 8962 line 9
PTC_ESTIMATE_FIELD = "marketplace_estimated_income_at_least_100_fpl"
PTC_MEDICAID_FIELD = "below_poverty_line_not_eligible_for_medicaid_due_to_immigration"
PTC_IMMIGRATION_FIELD = "enrollee_not_eligible_for_marketplace_due_to_immigration"
PTC_DEPENDENTS_MAGI_FIELD = "dependents_modified_agi_cents"                   # Form 8962 line 2b
PTC_MFS_EXCEPTION_FIELD = "mfs_ptc_exception"
PTC_MFS_FOURTH_YEAR_FIELD = "mfs_ptc_exception_fourth_year"
PTC_ROOT_FIELDS = frozenset({PTC_ALLOCATION_FIELD, PTC_ESTIMATE_FIELD, PTC_MEDICAID_FIELD,
                             PTC_IMMIGRATION_FIELD, PTC_DEPENDENTS_MAGI_FIELD,
                             PTC_MFS_EXCEPTION_FIELD, PTC_MFS_FOURTH_YEAR_FIELD})
PTC_ROOT_REQUIRED_FIELDS = PTC_ROOT_FIELDS - {PTC_DEPENDENTS_MAGI_FIELD}


def _ptc_cents(item: dict, month: str, column: str, strict: bool = True) -> int:
    """One cell as cents. `strict` (the mapper's emission and refusals) raises on a value that
    is not an integer; the reach predicate reads with `strict=False` and treats it as absent,
    because `gaps_for` is engine-free and runs before the mapper's own type refusal — a
    predicate that raised there would escape the envelope as a 500 instead of a refusal."""
    v = item.get(ptc_field(month, column), 0)
    if isinstance(v, bool) or not isinstance(v, int):
        if strict:
            raise FactsSchemaError(
                f"{PTC_GROUP}[].{ptc_field(month, column)} must be an integer number of cents")
        return 0
    return v


def ptc_covered_months(item: dict, strict: bool = True) -> list:
    """The coverage months on one form: every month whose column A is above zero."""
    return [m for m in PTC_MONTHS if _ptc_cents(item, m, "premium", strict) > 0]


def ptc_has_aptc(facts: dict, strict: bool = True) -> bool:
    return any(isinstance(it, dict) and any(_ptc_cents(it, m, "aptc", strict) > 0 for m in PTC_MONTHS)
               for it in (facts.get(PTC_GROUP) or []))


def ptc_questions_reached(facts: dict) -> list:
    """The root questions one Form 1095-A reaches, in the ask order: Form 8962 line 9's gate
    first (a yes is refused by name — Parts IV and V are not carried); then the below-poverty
    question the form's column C decides (advance payments made: the Marketplace-estimate
    question; none: the Medicaid-immigration question — both inert above the poverty line,
    measured, so one of them is asked on every return with a form); with claimed dependents the
    enrollment-family immigration question (a yes is the dictionary's own knockout) and line 2b
    (optional: absent is 0); on a separate return the exception, and on a yes its fourth-year
    follow-up — sensitive and single-purpose, last."""
    if not isinstance(facts, dict) or not (facts.get(PTC_GROUP) or []):
        return []
    reached = [PTC_ALLOCATION_FIELD]
    reached.append(PTC_ESTIMATE_FIELD if ptc_has_aptc(facts, strict=False) else PTC_MEDICAID_FIELD)
    if any(isinstance(p, dict) and p.get("role") == "dependent" for p in facts.get("persons") or []):
        reached += [PTC_IMMIGRATION_FIELD, PTC_DEPENDENTS_MAGI_FIELD]
    if facts.get("filing_status") == "mfs":
        reached.append(PTC_MFS_EXCEPTION_FIELD)
        if facts.get(PTC_MFS_EXCEPTION_FIELD) is True:
            reached.append(PTC_MFS_FOURTH_YEAR_FIELD)
    return reached


def refuse_malformed_f1095as(items: list) -> None:
    """Shapes the dictionary computes in silence or blocks without words, refused by name:
    two or more forms (the dictionary's own BlockSubmission and a knockout the emission never
    reaches — one form per return at the pin); a form with no coverage month; advance payments
    (column C) in a month with no enrollment premium; and a zero or blank column B on a coverage
    month — the instructions send the filer to the Marketplace's SLCSP tool when column B is
    blank, and a zero computes a credit of zero in silence."""
    if len(items) > 1:
        raise ServiceFactsError(
            f"{PTC_GROUP} carries {len(items)} forms — the engine accepts one Form 1095-A per "
            f"return at this pin (a second is its own block on submission); refused rather than "
            f"computed on the first alone")
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        covered = ptc_covered_months(item)
        if not covered:
            raise ServiceFactsError(
                f"{PTC_GROUP}[{i}] has no month with an enrollment premium (column A) above 0 — "
                f"a Form 1095-A with no coverage month reaches nothing; refused rather than "
                f"computed as no coverage")
        for m in PTC_MONTHS:
            if _ptc_cents(item, m, "aptc") > 0 and m not in covered:
                raise ServiceFactsError(
                    f"{PTC_GROUP}[{i}].{ptc_field(m, 'aptc')} is above 0 while "
                    f"{ptc_field(m, 'premium')} is 0 — column C without column A is not a "
                    f"month the form reports; refused rather than repaid in silence")
            if m in covered and _ptc_cents(item, m, "slcsp") <= 0:
                raise ServiceFactsError(
                    f"{PTC_GROUP}[{i}].{ptc_field(m, 'slcsp')} is 0 on a coverage month — when "
                    f"Form 1095-A column B is blank the instructions have the premium for the "
                    f"applicable second lowest cost silver plan looked up for that month; a "
                    f"zero computes a credit of 0 in silence, so it is refused rather than served")


def dependent_filer_ptc_route(facts: dict) -> bool:
    """Mirrors the dictionary's /notMfjAndPrimaryFilerCouldBeDependentAndClaimerIsRequired
    ToFileOrFilingForCredits from the page-1 answers: not a joint return, the primary can
    be claimed, and the claimer must file or filed for more than a refund. On that route the
    dictionary reads a Form 8962 dependent-filer chain this seat never sends (/dependentTp
    SelfEnrolled, /dependentTpEnrolledSomeoneElse, the other-tax-family question) instead of
    the has-plan writable — measured: the form is dropped and the return served complete with
    the advance payments neither repaid nor reconciled."""
    if facts.get("filing_status") == "mfj":
        return False
    primary = next((p for p in (facts.get("persons") or [])
                    if isinstance(p, dict) and p.get("role") == "primary"), None)
    if primary is None or primary.get("someone_can_claim_you") is not True:
        return False
    if primary.get("potential_claimer_must_file") is True:
        return True
    return (primary.get("potential_claimer_must_file") is False
            and primary.get("potential_claimer_filed") is True
            and primary.get("potential_claimer_filed_only_for_refund") is not True)


def refuse_misplaced_ptc_answers(facts: dict) -> None:
    """A root answer past the reach is refused by name; Form 8962 line 9 answered yes is
    refused by name (Part IV allocations and the Part V alternative calculation are not carried,
    and the dictionary computes the full credit with no allocation and no words, measured); a
    Form 1095-A on a claimable primary filer's return is refused by name (the dependent-filer
    chain of Form 8962 is not carried, and the dictionary drops the form in silence, measured)."""
    if (facts.get(PTC_GROUP) or []) and dependent_filer_ptc_route(facts):
        raise ServiceFactsError(
            f"{PTC_GROUP} is entered on a return whose primary filer can be claimed as a "
            f"dependent by someone who must file (or filed for more than a refund) — Form 8962 "
            f"for a dependent filer asks whether the filer enrolled themself or was enrolled by "
            f"the claimer, questions not carried here, and the engine would serve the return "
            f"with the form dropped and the advance payments neither repaid nor reconciled; "
            f"refused rather than computed without it")
    reached = ptc_questions_reached(facts)
    for field in sorted(PTC_ROOT_FIELDS):
        if field in facts and field not in reached:
            raise ServiceFactsError(
                f"{field} is answered but the Form 1095-A questions do not reach it with the "
                f"facts given (they are asked once a Form 1095-A is entered: line 9's gate, then "
                f"the below-poverty question column C decides, the enrollment-family question "
                f"with claimed dependents, the separate-return exception on a separate return); "
                f"refused rather than dropped")
    if facts.get(PTC_ALLOCATION_FIELD) is True:
        raise ServiceFactsError(
            f"{PTC_ALLOCATION_FIELD} is yes — Form 8962 Part IV (allocating policy amounts with "
            f"another taxpayer) and Part V (the alternative calculation for the year of marriage) "
            f"are not carried here, and the engine would compute the full credit with no "
            f"allocation in silence; refused rather than computed")


def hsa_taxable_distributions(facts: dict, person_index: int) -> int:
    """This filer's Form 8889 line 16 on the collection route: gross less qualified medical
    expenses over their items (a repayment above gross is refused before this reads)."""
    total = 0
    for item in facts.get(HSA_GROUP) or []:
        if isinstance(item, dict) and item.get("person") == person_index:
            g, e = item.get("gross_distribution_cents"), item.get("qualified_medical_expenses_cents")
            if isinstance(g, int) and isinstance(e, int) and not isinstance(g, bool) and not isinstance(e, bool):
                total += max(g - e, 0)
    return total


def hsa_exception_questions_reached(facts: dict, person_index: int, tax_year: int = 2025) -> list:
    """The exception pair one FILER row reaches: both halves, once that filer's taxable
    distributions are above zero, every one of their forms carries code 1 (any other code is the
    dictionary's own knockout, which comes first), and the filer is under 66 at the close of the
    year — a filer 66 or older has the whole of line 16 excepted by the dictionary's own
    derivation and is never asked (measured: born 1959 derived, born 1960 asked; the year-end
    age, not a day). A dependent row reaches nothing.

    `tax_year` defaults to the pinned year: the mapper passes the request's, the gaps loop the
    default. They agree because ty2025 is the only year the service maps — `estimate_2026` is
    refusal-only and never asks a persons-row gap. When a second year lands, thread it through
    `gaps_for` so the age-66 boundary reads one year on both sides."""
    if not isinstance(facts, dict):
        return []
    persons = facts.get("persons") or []
    if not 0 <= person_index < len(persons) or not isinstance(persons[person_index], dict):
        return []
    person = persons[person_index]
    if person.get("role") not in ("primary", "spouse"):
        return []
    if hsa_taxable_distributions(facts, person_index) <= 0:
        return []
    if any(isinstance(it, dict) and it.get("person") == person_index
           and it.get(HSA_CODE_FIELD) not in HSA_CODES_ADMITTED
           for it in facts.get(HSA_GROUP) or []):
        return []
    birth_year = person.get("birth_year")
    if isinstance(birth_year, int) and not isinstance(birth_year, bool) and tax_year - birth_year >= HSA_EXCEPTION_AGE:
        return []
    return list(HSA_EXCEPTION_FIELDS)


def refuse_misplaced_hsa_answers(facts: dict, tax_year: int = 2025) -> None:
    """The exception pair belongs to a filer row whose taxable distributions reach it;
    anywhere else it is refused by name rather than dropped (a filer 66 or older answering it
    would be silently ignored by the dictionary — measured)."""
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict):
            continue
        reached = hsa_exception_questions_reached(facts, i, tax_year)
        for field in HSA_EXCEPTION_FIELDS:
            if field not in person or field in reached:
                continue
            if person.get("role") == "dependent":
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered on a dependent row — Form 8889 is the "
                    f"filer's and, on a joint return, the spouse's; refused rather than dropped")
            raise ServiceFactsError(
                f"persons[{i}].{field} is answered where the answers so far do not reach it — "
                f"the 20%-tax exception is asked once that person's HSA distributions exceed "
                f"their qualified medical expenses, every one of their Forms 1099-SA carries "
                f"distribution code 1, and they are under 66 at the close of the year (older, "
                f"the exception is the engine's own derivation); refused rather than dropped")


def refuse_malformed_hsa_distributions(items: list) -> None:
    """Two shapes the dictionary computes in silence, refused by name: qualified medical
    expenses above the gross distribution (measured: line 16 floors at zero, no knockout — the
    excess is not a figure the form carries), and distribution code 2 (excess contributions),
    which computes as a normal distribution with no knockout while the withdrawn-excess route it
    belongs to is not carried here. Codes 3-6 go through: each is the dictionary's own knockout,
    served with words."""
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        g, e = item.get("gross_distribution_cents"), item.get("qualified_medical_expenses_cents")
        if (isinstance(g, int) and isinstance(e, int) and not isinstance(g, bool)
                and not isinstance(e, bool) and e > g):
            raise ServiceFactsError(
                f"hsa_distributions[{i}].qualified_medical_expenses_cents ({e}) exceeds the gross "
                f"distribution ({g}) — Form 8889 line 15 cannot exceed line 14c; refused rather "
                f"than served as a zero taxable amount")
        if item.get(HSA_CODE_FIELD) == "2":
            raise ServiceFactsError(
                f"hsa_distributions[{i}].{HSA_CODE_FIELD} is 2 (excess contributions) — the "
                f"withdrawn-excess-contribution route that code belongs to is not carried here, "
                f"and the engine would compute it as a normal distribution in silence; refused "
                f"rather than computed")
MISC_PFD_FIELD = "is_alaska_pfd"
ALASKA_PFD_EMISSION = {"received_alaska_pfd": "/receivedAlaskaPfd",
                       "spouse_received_alaska_pfd": "/spouseReceivedAlaskaPfd"}


def misc_pfd_question_reached(item) -> bool:
    """the per-item Alaska PFD classification is a real question only once box 3
    (`other_income_cents`) is above 0 — a $0 box (the ordinary state of a royalty-only 1099-MISC,
    box 2) has no "other income" to classify, so it is answered automatically rather than asked."""
    if not isinstance(item, dict):
        return False
    v = item.get("other_income_cents")
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


# royalty income received outside a Schedule K-1 (the dictionary's scheduleE.xml: ONE
# return-level royalty activity — not a collection, unlike rentals or K-1s). Box 2 of every Form
# 1099-MISC (`misc1099s[].royalties_cents`) is summed by this service into the single root
# `/writableRoyaltyIncome`; the ordinary expenses and the oil/gas/geothermal classification are
# root answers no 1099-MISC box carries (the payer does not know the recipient's own expenses).
MISC_ROYALTIES_FIELD = "royalties_cents"                        # box 2 (misc1099s[] item)
ROYALTY_EXPENSES_FIELD = "royalty_expenses_cents"               # root
ROYALTY_OIL_GAS_FIELD = "royalty_is_oil_gas_geothermal"         # root
ROYALTY_ROOT_FIELDS = frozenset({ROYALTY_EXPENSES_FIELD, ROYALTY_OIL_GAS_FIELD})


def royalty_income_total(facts: dict) -> int:
    """the one royalty activity's gross income — every misc1099s[].royalties_cents (box 2),
    summed. The dictionary carries no per-item royalty collection, so the service does the
    summation the engine does not."""
    if not isinstance(facts, dict):
        return 0
    return sum(_cents_or_zero(item.get(MISC_ROYALTIES_FIELD))
               for item in (facts.get("misc1099s") or []) if isinstance(item, dict))


def royalty_expenses_reached(facts: dict) -> bool:
    """the root royalty-expenses answer and the oil/gas/geothermal classification are
    reached only once the return claims royalty income."""
    return royalty_income_total(facts) > 0


def refuse_misplaced_royalty_answers(facts: dict) -> None:
    """a royalty answer past its reach is refused by name rather than dropped or silently
    computed against an activity the return does not claim; a misplaced Alaska PFD classification
    (box 3 at 0 or absent) is refused the same way."""
    if not isinstance(facts, dict):
        return
    reached = royalty_expenses_reached(facts)
    for field in sorted(ROYALTY_ROOT_FIELDS):
        if field in facts and not reached:
            raise ServiceFactsError(
                f"{field} is answered but no misc1099s[].{MISC_ROYALTIES_FIELD} on this return "
                f"is above 0 — the royalty activity's expenses and oil/gas classification are "
                f"asked only once the return claims royalty income; refused rather than dropped")
    for i, item in enumerate(facts.get("misc1099s") or []):
        if (isinstance(item, dict) and MISC_PFD_FIELD in item
                and not misc_pfd_question_reached(item)):
            raise ServiceFactsError(
                f"misc1099s[{i}].{MISC_PFD_FIELD} is answered but this form's "
                f"other_income_cents is not above 0 — the Alaska Permanent Fund dividend "
                f"classification is asked only once box 3 carries an amount; refused rather "
                f"than dropped")
# Every root question asked on EVERY return, in the interview's order — the workbook's Household
# rows read this set (`layout.ROOT_QUESTION_ROWS`).
EVERY_RETURN_ROOT_FIELDS = (frozenset({RESIDENCE_STATE_FIELD, "received_alaska_pfd"})
                            | DIGITAL_ASSET_FIELDS | frozenset(FOREIGN_ACCOUNT_FIELDS)
                            | frozenset(CREDIT_HISTORY_FIELDS)
                            | frozenset({ESTIMATED_PAYMENTS_FIELD})
                            | frozenset({STUDENT_LOAN_FIELD})
                            | SECTION_1341_FIELDS
                            | frozenset(ALIMONY_AMOUNT_FIELDS)
                            | MAIN_HOME_FIELDS)
REQUIRED_PERSON_FIELDS = frozenset({"role", "birth_year", "tin_type"})
REQUIRED_ITEM_FIELDS = {
    "w2s": frozenset({"person", "wages_cents"}),
    "int1099s": frozenset({"person"}),
    "oid1099s": frozenset({"person"}),
    # the engine leaves a Form 8949 row with either amount blank INCOMPLETE (register row
    # 419), so a blank box 1e is a question, not a zero.
    "b1099s": frozenset({"person", "proceeds_cents", "cost_basis_cents"}),
    "div1099s": frozenset({"person"}),
    # `gross_distribution_cents` joined the required pair — the W-2G posture: the
    # form is issued because a distribution happened, so a blank box 1 is an unread box.
    "r1099s": frozenset({"person", "distribution_code", "gross_distribution_cents"}),
    # `winnings_cents` joins `person`, the W-2 posture rather than the information returns'.
    # A W-2G is ISSUED because a reportable win crossed a threshold, so a blank box 1 is an unread
    # box, not a win of nothing — absence is not zero. (The client already said so:
    # `client/documents.py::REQUIRED_LABELS["W-2G"]` has required box 1 since decided off the
    # paper. This is the service-side half of the same reading.)
    "w2gs": frozenset({"person", "winnings_cents"}),
    # the W-2G posture — a benefit statement is issued because benefits were paid, so a
    # blank box 5 is an unread box; the form type keys the amount to its writable.
    "ssa1099s": frozenset({"person", "form_type", "net_benefits_cents"}),
    "g1099s": frozenset({"person", "unemployment_compensation_cents"}),
    # box 3 is required — the form is issued because an amount was paid. The Alaska PFD
    # flag moved OUT of this unconditional set in it is required only once box 3 is above 0
    # (`misc_pfd_question_reached`), asked as a conditional gap rather than blanket-required —
    # a $0 box (a royalty-only 1099-MISC, box 2) auto-answers false and is never asked.
    "misc1099s": frozenset({"person", "other_income_cents"}),
    # all four required — unanswered expenses tax the whole distribution (measured), and
    # the box 3 code decides whether the dictionary's own knockout fires.
    "hsa_distributions": frozenset({"person", "gross_distribution_cents", "hsa_distribution_code",
                                    "qualified_medical_expenses_cents"}),
    # all nine required — the dictionary's `earlierYearIntakeAnswered` is an All over the
    # nine, and a half-answered row leaves the election unmade (measured, the refusal fires).
    "ssa_lump_sum_years": frozenset(LUMP_SUM_ITEM_FIELDS),
    # all three required — the type decides the synthetic identity the engine is given, the
    # household-employee column is the dictionary's own knockout, the amount is line 1 column (e).
    "care_providers": frozenset({"provider_type", "is_household_employee", "amount_paid_cents"}),
    # nothing required — a blank cell is a month without coverage; a form with no coverage
    # month at all is refused by name.
    "f1095as": frozenset(),
    # Line 28 joins lines 1 and person because the engine's net-profit chain NEVER
    # resolves without it (measured at the pin: gross alone leaves /totalIncome unresolved) — a
    # blank line 28 is an unread answer, not zero expenses.
    "schedule_c": frozenset({"person", "gross_receipts_cents", "total_expenses_cents"}),
    # Rents joins person — the stream is the property's income, and a vacancy
    # year is a stated 0, not an absence.
    "rentals": frozenset({"person", "rents_received_cents"}),
    # Which form comes first (the cheap gate); the rest of a K-1's
    # required answers are CONDITIONAL (item D on partnerships, the loss trio on a loss) and
    # are asked as gaps, not required fields.
    "k1s": frozenset({"person", "source"}),
}

# Every field the schema types as an integer (directly or through $defs/cents). Checked because
# `isinstance(True, int)` is True in Python — the THIRD place in this repo where that trap would
# have produced a wrong number instead of an error: `client/payload.py` documents it for the
# outbound payload, and `operations._tax_year` for the year, where `True` computed as tax year 1.
# Here `wages_cents: True` reaches `_money()` and renders as one cent.
INTEGER_FACT_FIELDS = frozenset({
    "birth_month", "birth_year", "months_in_home", "person", "employer_ref",
    "estimated_tax_payments_cents",
    "section_1341_credit_cents",
    "alimony_received_cents", "alimony_paid_cents",
    "student_loan_interest_cents",
    "student_loan_interest_employer_paid_cents",
    "student_loan_interest_from_qtp_cents",
    "educator_expenses_cents",
    "traditional_ira_contributions_cents",
    # the earlier-year row's figures, and the year itself (an Int, not a Dollar)
    "earlier_year", "lump_sum_portion_cents", "benefits_received_cents",
    "adjusted_gross_income_cents", "exclusions_cents", "taxable_benefits_reported_cents",
    "roth_ira_contributions_cents",
    "net_benefits_cents",
    *(f for f in OID_MONEY_FIELDS if f != "federal_withholding_cents"),      # Form 1099-OID
    *INT_EXTRA_EMISSION,                                                     # Form 1099-INT
    "proceeds_cents", "cost_basis_cents", "accrued_market_discount_cents",   # Form 1099-B
    "wash_sale_loss_disallowed_cents",
    "unemployment_compensation_cents", "repaid_cents",
    "other_income_cents",
    "gross_distribution_cents", "qualified_medical_expenses_cents",
    "hsa_exception_amount_cents",
    "amount_paid_cents", "care_expenses_cents",
    *PTC_ITEM_FIELDS, PTC_DEPENDENTS_MAGI_FIELD,
    W2_BOX10_FIELD, *DCB_PERSON_FIELDS, *DCB_ROOT_FIELDS,
    *W2_BOX12_FIELDS,
    IRA_ROTH_ABLE_FIELD, IRA_INHERITED_AMOUNT_FIELD,
    SAVERS_DIST_2023_FIELD, SAVERS_DIST_2024_FIELD,
    HSA_OWN_AMOUNT_FIELD, HSA_OWN_AFTER_FIELD,
    SAVERS_DIST_AFTER_AMOUNT_FIELD,
    "basis_cents", "se_earnings_cents", "deductible_se_loss_cents", "amount_at_risk_cents",
    "guaranteed_payments_services_cents", "guaranteed_payments_capital_cents",
    "qualified_ptp_income_cents", "ptp_prior_year_unallowed_loss_cents",
    "section_199a_qbi_cents",
    "capital_gain_distributions_cents", "capital_loss_cents", "cost_of_goods_sold_cents",
    "dividend_income_cents", "other_business_income_cents", "returns_and_allowances_cents",
    "federal_withholding_cents", "gross_distribution_cents", "gross_receipts_cents",
    "qualified_hsa_funding_distribution_cents",
    "qualified_charitable_distribution_cents",
    "qcd_prior_deducted_ira_contributions_cents",
    "rolled_over_cents",
    "other_cents",
    "pso_premiums_cents",
    "death_benefit_basis_cents",
    "hsa_december_31_value_cents",
    "hsa_prior_year_excess_cents",
    "prior_year_form_2441_line_3_cents",
    "prior_year_expenses_paid_this_year_cents",
    "prior_year_excluded_or_deducted_benefits_cents",
    "prior_year_lower_earned_income_cents",
    "prior_year_form_2441_line_6_cents",
    "prior_year_agi_cents",
    "exempt_interest_dividends_cents", "government_interest_cents", "interest_cents",
    "interest_income_cents", "ira_basis_cents", "medicare_wages_cents",
    "medicare_withheld_cents", "royalty_expenses_cents",
    "prior_year_unallowed_loss_cents", "section_199a_dividends_cents",
    "unrecaptured_1250_gain_cents",
    "ordinary_business_income_cents", "ordinary_dividends_cents", "qualified_dividends_cents",
    "rents_received_cents", "royalties_cents", "social_security_wages_cents",
    "social_security_withheld_cents", "tax_exempt_interest_cents", "taxable_amount_cents",
    "total_expenses_cents", "wages_cents", "winnings_cents", "withholding_cents",
    # rental expenses and depreciation inputs.
    "insurance_cents", "management_fees_cents", "repairs_cents", "taxes_cents",
    "building_basis_cents", "five_year_property_basis_cents", "placed_in_service_month",
})

COLLECTION_ITEM_FIELDS = {
    "w2s": frozenset({"person", "wages_cents", "withholding_cents",
                      "social_security_wages_cents", "medicare_wages_cents",
                      "social_security_withheld_cents", "medicare_withheld_cents",
                      "employer_ref",
                      "statutory_employee", "retirement_plan", "third_party_sick_pay",
                      "has_rrta_codes",
                      W2_BOX10_FIELD,
                      *W2_BOX12_FIELDS,
                      W2_BOX12_G_PLAN_FIELD}),
    "int1099s": frozenset({"person", *INT_EXTRA_EMISSION, "interest_cents", "government_interest_cents",
                           "tax_exempt_interest_cents", "federal_withholding_cents"}),
    "oid1099s": frozenset({"person", *OID_MONEY_FIELDS, OID_TAX_EXEMPT_FIELD, OID_FATCA_FIELD}),
    "b1099s": frozenset({"person", *B1099_FIELDS}),
    "div1099s": frozenset({"person", "ordinary_dividends_cents", "qualified_dividends_cents",
                           "capital_gain_distributions_cents", "unrecaptured_1250_gain_cents",
                           "federal_withholding_cents", "section_199a_dividends_cents",
                           "exempt_interest_dividends_cents"}),
    "r1099s": frozenset({"person", "gross_distribution_cents", "taxable_amount_cents",
                         "taxable_amount_not_determined", "distribution_code", "ira_sep_simple",
                         "federal_withholding_cents",
                         "qualified_hsa_funding_distribution_cents",
                         "qualified_charitable_distribution_cents",
                         "qcd_to_split_interest_entity",
                         "rolled_over_cents", "ira_one_rollover_per_year",
                         *R1099_BOX_FIELDS,
                         *R1099_PSO_FIELDS,
                         R1099_MRA_FIELD,
                         *R1099_DB_FIELDS}),
    "w2gs": frozenset({"person", "winnings_cents", "federal_withholding_cents"}),
    "ssa1099s": frozenset({"person", "form_type", "net_benefits_cents",
                           "federal_withholding_cents"}),
    "g1099s": frozenset({"person", "unemployment_compensation_cents",
                         "federal_withholding_cents", "repaid_cents"}),
    "misc1099s": frozenset({"person", "other_income_cents", "federal_withholding_cents",
                            "is_alaska_pfd",
                            MISC_ROYALTIES_FIELD}),
    "hsa_distributions": frozenset({"person", "gross_distribution_cents", "hsa_distribution_code",
                                    "qualified_medical_expenses_cents"}),
    "ssa_lump_sum_years": frozenset(LUMP_SUM_ITEM_FIELDS),
    "care_providers": frozenset({"provider_type", "is_household_employee",
                                 "amount_paid_cents"}),
    "f1095as": frozenset(PTC_ITEM_FIELDS),
    "schedule_c": frozenset({"person", "gross_receipts_cents", "returns_and_allowances_cents",
                             "cost_of_goods_sold_cents", "other_business_income_cents",
                             "total_expenses_cents", "principal_business_code",
                             "materially_participated", "all_investment_at_risk",
                             "amount_at_risk_cents"}),
    "rentals": frozenset({"person", "rents_received_cents", "total_expenses_cents",
                          "property_type", "materially_participates_in_lessee",
                          "active_participation", "fully_at_risk",
                          "amount_at_risk_cents", "prior_year_unallowed_loss_cents",
                          "active_participation_when_loss_arose",
                          # itemized expenses and depreciation inputs.
                          "insurance_cents", "management_fees_cents", "repairs_cents",
                          "taxes_cents", "building_basis_cents",
                          "is_nonresidential_real_property", "building_uses_standard_gds",
                          "placed_in_service_in_current_year", "placed_in_service_month",
                          "has_five_year_property", "five_year_property_basis_cents"}),
    "k1s": frozenset({"person", "source", "ordinary_business_income_cents",
                      "interest_income_cents", "dividend_income_cents",
                      "qualified_dividends_cents", "royalties_cents", "se_earnings_cents",
                      "publicly_traded_partnership", "materially_participated", "basis_cents",
                      "fully_at_risk", "guaranteed_payments_services_cents",
                      "guaranteed_payments_capital_cents", "general_partner",
                      "qualified_ptp_income_cents", "qualified_ptp_is_sstb",
                      "ptp_prior_year_unallowed_loss_cents", "deductible_se_loss_cents",
                      "amount_at_risk_cents", "section_199a_qbi_cents"}),
}

# DEPENDENTS_REFUSAL retired with dependents coverage — the rows map now. Later work
# retired the SECOND clause of what stood here ("married dependents, and children with another
# biological or adoptive parent"): the joint-return test is three questions the dictionary asks,
# so a married dependent computes. What was left of that second clause was retired — "children
# with another biological or adoptive parent (the divorced-and-separated-parents rule set)" —
# because the benefit-split GATE is five questions the dictionary asks, and every answer that
# closes it leaves the child claimed under the ordinary rules. What survives is the two tiers
# BEHIND that gate, each named by its own cause and raised in
# refuse_unsupported_dependent_answers.
# The non-parental population, for every string a person reads (the refusal, the interview
# prompt, the absent-statement, the served exclusion below): the dictionary's set in words, not a
# paraphrase that also fits a parent. Defined here because the exclusion reads it.
NON_PARENT_QC_IN_WORDS = ("a sibling, half- or step-sibling, stepchild, foster child, grandchild, "
                          "or a sibling's child or other descendant")

# DEPENDENTS_STILL_REFUSED is GONE. It stood here from dependents coverage as the served
# dependents exclusion and was narrowed by the married dependent, the split gate, the custodial
# tier and finally the non-parental split as each refusal became
# questions the dictionary asks. Nothing on the dependents surface is refused now; `coverage`
# serves no dependents clause.

# The excess Social Security withholding credit (Schedule 3 line 11) turns on having had MORE
# THAN ONE EMPLOYER, and the dictionary decides that by grouping W-2s on EIN + employer name — two
# facts this service cannot express. `_w2` gives every W-2 the same constant employer name and sets
# no EIN, so two employers collapse into one and the credit is silently DENIED. Making the
# placeholder distinct per W-2 would be wrong in the other direction: it would ALLOW the credit when
# one employer issued two W-2s (the dictionary has a node test for exactly that case). The service
# cannot distinguish those two situations from what it accepts, so it refuses the multi-W-2 case
# rather than guess — the same rule as the age-65 day ambiguity. Restoring coverage needs an opaque,
# non-identifying employer discriminator in the fact schema, verified against a live engine.
# The statutory OASDI rate. Used ONLY to refuse an impossible box 4 — not to compute anything; the
# tax stays in the engine. A box 4 above the rate on box 3 is a caller-input fault, and left
# unrefused the engine turns it into /knockoutFormW2s PLUS a large refundable credit, served as a
# normal 200 (measured: ~$10,918 conjured from two impossible W-2s).
OASDI_RATE_NUM, OASDI_RATE_DEN = 62, 1000

# A filer holding several W-2s IS supported — but only with the three facts the excess Social
# Security credit actually needs, each measured against the pinned engine rather than assumed:
#   * employer_ref — distinct employer identity moves /primaryFilerExcessOasdiWithheld from 0.00 to
#     3961.80 on two $120k W-2s; identical identity correctly denies it.
#   * box 4 — WITHOUT it the credit is 0.00 however many employers there were.
#   * box 3 — the eligibility gate sums capped BOX 3, not box 1, and box 3 defaults from box 1 here.
#     Elective deferrals split them, exactly for the near-wage-base earners this credit serves.
# Accepting the return without them would serve a zero credit that looks successful.
MULTIPLE_EMPLOYERS_REFUSAL = (
    "a filer with more than one Form W-2 must supply `employer_ref`, "
    "`social_security_wages_cents` (box 3) and `social_security_withheld_cents` (box 4) on each of "
    "them — the excess Social Security withholding credit turns on whether those W-2s came from "
    "different employers, on box 3 (which is what the eligibility test sums; box 1 is not it, and "
    "the two differ whenever there are elective deferrals), and on box 4. Without all three the "
    "credit computes as zero, which would be a silently wrong number. `employer_ref` is an opaque "
    "per-request grouping label (same value = same employer), never an employer identifier. Two "
    "filers with one W-2 each (both spouses working) need none of them: the credit is per person")

_MARITAL = {"single": "single", "mfj": "married", "mfs": "married", "hoh": "single", "qss": "widowed"}
# The dictionary's own filing-status literals (/filingStatusOptions). `single` coincides with the
# service code, which is why the translation was invisible until mfj: passing the service's `mfj`
# through would hand the persister an enum value the dictionary never declared.
_DICT_FILING = {"single": "single", "mfj": "marriedFilingJointly",
                "mfs": "marriedFilingSeparately", "hoh": "headOfHousehold",
                "qss": "qualifiedSurvivingSpouse"}


# ---- what the service DECIDES without asking ---------------------------------------------------
# The mapper does not only map. To hand the engine a resolvable fact set it asserts ~40 writables
# nobody supplied. Every one is a statement that changes the return if it is wrong, and the caller
# was never given a field in which to contradict it — so unlike a dropped election or a defaulted
# `wages_cents`, no amount of care on their side surfaces it. That is the design's
# `unasked_boundary`, and why a `complete` silent about it is worse than a refusal.

# Three categories, and the split is the point. `tests/test_assumptions.py` asserts they PARTITION
# what a real `map_to_engine` call emits, so a new writable nobody classified fails the gate instead
# of becoming assumption forty-one that nobody noticed. Collection ids are normalised to `*`.

# Claims about the PERSON. Published by `coverage`, because a taxpayer is entitled to know what was
# assumed on their behalf. Each value is a clause that reads after "we assumed ".
ASSUMED_ABOUT_TAXPAYER = {
    # Page-1 questions answered on the taxpayer's behalf. (`/receivedDigitalAssets` and
    # `/disposedDigitalAssets` were here until the service asked them — DERIVED_FROM_INPUT.)
    "/presidentalCampaignDesignation": "you designate nothing to the Presidential Election "
                                       "Campaign Fund",
    # Payments and credits already made or claimable — these move the refund
    # (`/paidEstimatedTaxesOrFromLastYear` sat here as "you made no estimated tax payments and
    # carried nothing from last year's refund" until the service asked the line 26 question on every
    # return — DERIVED_FROM_INPUT.)
    # (`/1095As` sat here as "you had no Marketplace health plan, so no premium tax credit is
    # computed" and `/writableHasPtcQualifyingPlan` as "you had no plan qualifying for the
    # premium tax credit" until the service covered Form 1095-A — both DERIVED_FROM_INPUT now.)
    # the one answer the section still assumes, per form.
    "/1095As/*/hasChangeInCircumstance":
        "no change in circumstances (income, household, or coverage) went unreported to the "
        "Marketplace during the year — Form 8962 is computed on the Form 1095-A as issued",
    # (`/cdccCareProviders` sat here as "you paid no child or dependent care expenses" and
    # `/writableCdccHasQualifyingExpenses` as "you had no qualifying child or dependent care
    # expenses" until the service covered Form 2441 — both DERIVED_FROM_INPUT now. What the section
    # still assumes is named below, per provider and per qualifying person.)
    "/cdccCareProviders/*/isEmployerFurnished":
        "no care provider is entered as furnished by your employer — an employer who furnished "
        "the care is entered as a provider on Form 2441 line 1 like any other, and the benefit "
        "itself is read from Form W-2 box 10",
    "/cdccCareProviders/*/hasTinOrEin":
        "each care provider's name, address, and taxpayer identification number are on hand for "
        "Form 2441 line 1 (columns (a) to (c) are not carried here)",
    "/familyAndHousehold/*/cdccHadExpensesPaidToQualifyingProvider":
        "the care expenses entered for each qualifying person were paid to a provider who was "
        "not your spouse, the child's parent, your dependent, or your child under 19 (Form "
        "2441 line 1 instructions)",
    "/filers/*/cdccHadExpensesPaidToQualifyingProvider":
        "the care expenses entered for a disabled filer were paid to a provider who was not "
        "your spouse, your dependent, or your child under 19 (Form 2441 line 1 instructions)",
    # (`/hasCdccCarryoverAmountFromPriorTaxYear` sat here as "you carried no dependent-care
    # amount from last year" until the service derived it from the Form 2441 line 13 answer.)
    # (`/wasK12Educators` sat here as "neither you nor a spouse was a K-12 educator" until the
    # service asked it on every filer row — DERIVED_FROM_INPUT.)
    # (`/hadStudentLoanInterestPayments` sat here as "you paid no student loan interest" until
    # the service asked the Schedule 1 line 21 question on every return — DERIVED_FROM_INPUT.)
    # (`/madeIraContributions` sat here as "you made no IRA contributions" until the service asked it
    # on every filer row — DERIVED_FROM_INPUT.)
    "/interestReports/*/factaFilingRequired": "no 1099-INT you received has its FATCA filing "
                                              "requirement box checked",
    "/form1099Rs/*/factaFilingRequirement": "no 1099-R you received has its FATCA filing "
                                            "requirement box checked",
    # Rentals: the four itemized expense lines (insurance, management fees,
    # repairs, taxes) MOVED to `gaps._ABSENT_MEANS` — each is now sometimes a real
    # taxpayer-supplied figure and sometimes an unasked zero on the SAME emitted path, so the
    # request-conditional mechanism replaces this universal one (see `_map_rentals`'s docstring).
    # the one inference this service draws from a line 1b code. Published on every return
    # that carries a type 7 and nowhere else, because that is the only return it is about.
    "/rentalProperties/*/selfRental":
        "no separate self-rental answer was asked — Schedule E line 1b's own type 7, "
        "Self-Rental, was used to treat the property as rented to a trade or business you own "
        "an interest in, which is what lets its profit be treated as non-passive (Form 1040, "
        "line 9)",
    # only ever EMITTED on the no-depreciation-input path (no building basis, no 5-year
    # property claimed on this property) — see `_map_rentals`. Unlike the four lines above, the
    # universal presence-check this dict relies on stays correct here because the path is only
    # ever sent when the assumption is true.
    "/rentalProperties/*/depreciationOverride":
        "no building depreciation basis or 5-year MACRS personal property was supplied for "
        "this property, so line 18 depreciation prints zero",
    # Income the service never asks about
    # (`/form1099Gs` sat here as "you received no Form 1099-G (unemployment or state tax
    # refunds)" until the service covered the collection — which, measured at the pin, holds
    # UNEMPLOYMENT COMPENSATION ONLY. The sentence's second half survives on its own below: box 2,
    # the state or local income tax refund, is a ROOT intake whose prior-year worksheet is not
    # carried, so the refund is emitted zero and published.)
    "/writableStateAndLocalIncomeTaxRefundReceived":
        "you received no state or local income tax refund, credit, or offset (Form 1099-G, "
        "box 2)",
    # per 1099-G item. The state box is the W-2 posture (a different state is the
    # dictionary's own knockout, never reached from here); the earlier-year repayment is the
    # Schedule 1 line 7 leg this service does not carry (a Schedule A claim-of-right deduction
    # below $3,000, the dictionary's own knockout above it), so it is answered none and published.
    "/form1099Gs/*/writableState": "the state on your Form 1099-G is the state you live in",
    "/form1099Gs/*/writableAmountPaidBackForBenefitsBeforeTaxYear":
        "you repaid no unemployment compensation that you received in an earlier year (the "
        "Schedule 1, line 7 repayment covers only benefits received and repaid in the same year)",
    # (`/form1099Miscs` sat here as "you received no Form 1099-MISC" until the service covered the
    # collection — box 3 other income, the only box the pinned dictionary holds.)
    # per 1099-MISC item, the W-2 posture; measured at the pin, no state knockout exists
    # in the module, so nothing fires either way.
    "/form1099Miscs/*/writableState": "the state on your Form 1099-MISC is the state you live in",
    # (`/socialSecurityReports` sat here as "you received no Social Security benefits" until
    # the service covered the stream — DERIVED_FROM_INPUT, the interest collection's precedent.)
    # (`/writableSocialSecurityLumpSumElection` sat here for a time as "you make no
    # lump-sum election …" — asked once a benefit statement exists now; DERIVED_FROM_INPUT.)
    # (`/hsaDistributions` sat here as "you took no HSA distributions" until the service covered the
    # collection — DERIVED_FROM_INPUT. `/someFilerHadNonW2HsaActivity` stays: true from the
    # input when a distribution exists, false otherwise, and either way the CONTRIBUTION half
    # of what it says is assumed — Form 8889 Part I is not carried.)
    # (`/someFilerHadNonW2HsaActivity` sat here as "no HSA contributions were made outside a
    # W-2" until the service asked every filer row — DERIVED_FROM_INPUT, with the two HasMade twins.)
    # the HSA section's own questions, answered once a distribution opens it. Each is a
    # claim about the person; each names the leg not carried.
    "/hasHsaMedicalSavingsAccountType": "you have no Archer MSA or Medicare Advantage MSA",
    "/writableHasHsaWithdrawnExcessContributionsYesNo":
        "you withdrew no excess HSA contributions",
    "/someFilersMadeTestingPeriodContribution":
        "no HSA contribution was made under the last-month rule (no testing period)",
    "/someFilersHaveTestingPeriodAdditionalIncome":
        "there is no testing-period failure income (Form 8889 line 18)",
    # (`/filers/*/hasMadeQualifiedHsaFundingDistribution` sat here as "no qualified HSA funding
    # distribution was made" until the service asked it of a code W filer — DERIVED_FROM_INPUT; the
    # 1099-SA-only filer's no is STATED through `gaps._ABSENT_MEANS` instead.)
    "/hsaDistributions/*/writableDistributionsRolloverBool":
        "no part of the HSA distribution was rolled over (Form 8889 line 14b)",
    "/hsaDistributions/*/hasWithdrawnExcessContributions":
        "the HSA distribution included no withdrawn excess contributions (Form 8889 line 14b)",
    # (`/receivedAlaskaPfd` was here until the service asked the residence state and, behind an
    # Alaska answer, the dividend question itself — DERIVED_FROM_INPUT.)
    # the two halves of the Form 8995-A scaffold. The claim is what routes an
    # above-threshold return to Form 8995-A at all; the empty collection is what says no
    # per-business detail was carried, and it is the one that decides a number.
    "/writableClaims8995A": "any qualified business income deduction above the section 199A "
                            "threshold is figured on Form 8995-A rather than left at zero — "
                            "that route is answered yes on every return, whether or not this "
                            "one has such a deduction",
    "/qualifiedBusinesses": "each business's qualified business income is the Schedule C "
                            "figure or the amount a Schedule K-1's section 199A statement "
                            "reports, and nothing else — no W-2 wages, property basis or "
                            "specified-service answer was carried. Below the section 199A "
                            "threshold those change no figure. Above it a business's own W-2 "
                            "wage and property limitation (Form 8995-A, Part II) is not in the "
                            "covered set: only the qualified REIT dividend and publicly traded "
                            "partnership half is figured (Form 8995-A, lines 28-32), and a "
                            "return with business income from a Schedule C or a Schedule K-1 "
                            "is refused rather than figured",
    # `/livedTogetherAllYearWithSpouse` stood here as "on a separate return, you and your spouse
    # lived together all year" until the service made it the caller's answer (the lived-together
    # chain, asked on every married return) — an assumption inverted into a question.
    # (The credit-history answers — `/eitcHadImproperClaims`, `/eitcQcOfAnother`,
    # `/receivedImproperClaims` — were attested false and published here until the service asked
    # Form 8862's questions on every return — DERIVED_FROM_INPUT.)
    # (Foreign accounts and trusts — `/hasForeignAccounts`, `/hasForeignTrustsTransactions`,
    # `/isForeignTrustsGrantor` — were attested false and published here until the service asked
    # Schedule B Part III on every return — DERIVED_FROM_INPUT.)
    # Household employment
    "/flowKnockoutHouseholdEmployee": "you had no household employee",
    # Per dependent: the same stated assumptions the filers get. Each is a
    # statement that changes eligibility if wrong, and no field exists to contradict it.
    # (`/familyAndHousehold/*/writableRequiredToFile` and
    # `/familyAndHousehold/*/writableFilingOnlyForRefund` sat here as "no claimed dependent is
    # required to file their own return" and "no claimed dependent files a return of their own,
    # for a refund or otherwise" until the same inversion, repeated: they are two links
    # of the joint-return chain the caller answers now, DERIVED_FROM_INPUT, published nowhere,
    # and sent only on the married rows the chain reaches.)
    "/familyAndHousehold/*/isUsCitizenFullYear":
        "each claimed dependent was a US citizen or resident all year",
    "/familyAndHousehold/*/deceased": "each claimed dependent was alive all year",
    # (`/familyAndHousehold/*/unableToCareForSelf` sat here as "no claimed dependent is unable
    # to care for themselves" until the service asked it on the row — DERIVED_FROM_INPUT.)
    "/familyAndHousehold/*/hasIpPin": "no claimed dependent has an IRS Identity Protection "
                                      "PIN (which would be needed at filing)",
    # Per filer. (`/filers/*/isBlind` sat here as "you are not blind" until Form 1040
    # line 12 prints the checkbox on every status, and it is the filer's own answer now —
    # DERIVED_FROM_INPUT, published nowhere.)
    # `/filers/*/canBeClaimed` stood here as "nobody else can claim you as a dependent" until
    # the service made it the caller's answer — the Form 1040 page-1 checkbox, asked on every
    # filer row.
    "/filers/*/isUsCitizenFullYear": "you were a US citizen or resident all year",
    # Per W-2
    # (`/formW2s/*/hasRRTACodes` sat here as "your W-2 carries no Railroad Retirement (RRTA)
    # codes" until the service asked box 14 on every W-2 — DERIVED_FROM_INPUT.)
    # (Box 13's three checkboxes — retirementPlan, statutoryEmployee, thirdPartySickPay — were
    # attested false and published here until the service asked them on every W-2 —
    # DERIVED_FROM_INPUT.)
    "/formW2s/*/nonstandardOrCorrectedChoice": "your W-2 is neither nonstandard nor corrected",
    "/formW2s/*/writableState": "your W-2 state is the state you live in",
}

# Says nothing about a taxpayer. NOT published: Direct File screen markers, section-complete flags,
# feature flags, and the synthetic placeholder identity — which exists precisely BECAUSE the boundary
# forbids receiving the real thing, so calling it an assumption about the person inverts what it is.
# Publishing these would bury the real assumptions in noise.
ENGINE_PLUMBING = {
    "/hasSeenReviewScreen": "Direct File screen marker",
    # the Alaska Permanent Fund section's Done marker — sent once its questions are
    # answered (the dividend pair, both no; a yes is refused), never ahead of them.
    "/hasCompletedApfSection": "Direct File screen marker (the Alaska Permanent Fund section's "
                               "Done, sent once its questions are answered)",
    "/flowHasSeenAmount": "Direct File screen marker",
    "/flowHasSeenCreditsIntroNoCredits": "Direct File screen marker",
    "/flowHasSeenDeductions": "Direct File screen marker",
    "/flowHasSeenTotalIncomeSummary": "Direct File screen marker",
    "/1095AsIsDone": "section-complete marker",
    "/cdccCareProvidersIsDone": "section-complete marker",
    "/form1099GsIsDone": "section-complete marker",
    "/form1099MiscsIsDone": "section-complete marker",
    "/hsaDistributionsIsDone": "section-complete marker",
    "/socialSecurityReportsIsDone": "section-complete marker",
    "/socialSecurityReports/*/hasSeenLastAvailableScreen": "Direct File screen marker",
    "/familyAndHouseholdIsDone": "section-complete marker",
    "/formW2sIsDone": "section-complete marker",
    "/incomeSourcesSupported": "feature flag",
    "/is1099RFeatureFlagEnabled": "feature flag",
    "/hasCompleted1099RSection": "feature flag",
    "/hasSome1099rFormsBeforeSectionEnabled": "feature flag",
    "/interestReportsIsDone": "section-complete marker",
    "/interestReports/*/payer": "synthetic placeholder — payer identity may not cross",
    "/originalIssueDiscountReports/*/payer": "synthetic placeholder — payer identity may not cross",
    "/dividendReports/*/payer": "synthetic placeholder — payer identity may not cross",
    "/form1099Rs/*/payer": "synthetic placeholder — payer identity may not cross",
    "/form1099Gs/*/payer": "synthetic placeholder — payer identity may not cross",
    "/form1099Gs/*/payer/tin": "synthetic placeholder EIN — the payer's identity may not cross; "
                               "the item's own completeness reads it beside withholding",
    "/form1099Gs/*/hasSeenLastAvailableScreen": "Direct File screen marker",
    "/form1099Miscs/*/payer": "synthetic placeholder — payer identity may not cross",
    "/form1099Miscs/*/hasSeenLastAvailableScreen": "Direct File screen marker",
    "/hsaDistributions/*/writableTrusteeName": "synthetic placeholder — the trustee's identity "
                                                "may not cross",
    "/hsaDistributions/*/hasSeenLastAvailableScreen": "Direct File screen marker",
    # a care provider's identity may not cross — name, number and address are synthetic
    # placeholders (the address is the first one this mapper synthesizes).
    "/cdccCareProviders/*/writableOrganizationName": "synthetic placeholder — the provider's "
                                                     "identity may not cross",
    "/cdccCareProviders/*/writableFirstName": "synthetic placeholder — the provider's identity "
                                              "may not cross",
    "/cdccCareProviders/*/writableLastName": "synthetic placeholder — the provider's identity "
                                             "may not cross",
    "/cdccCareProviders/*/writableEin": "synthetic placeholder EIN — the real one may not cross",
    "/cdccCareProviders/*/writableTin": "synthetic placeholder TIN — the real one may not cross",
    "/cdccCareProviders/*/writableAddress": "synthetic placeholder address — the real one may "
                                            "not cross",
    "/filers/*/tin": "synthetic placeholder TIN — the real one may not cross the boundary",
    "/familyAndHousehold/*/tin": "synthetic placeholder TIN — the real one may not cross "
                                 "the boundary",
    "/formW2s/*/employerName": "synthetic placeholder — employer identity may not cross",
    "/formW2s/*/ein": "synthetic placeholder EIN derived from the per-request employer ordinal",
}

# Computed from what the caller DID supply. Not assumptions; listed so the partition is total.
DERIVED_FROM_INPUT = frozenset({
    "/filingStatus", "/maritalStatus", "/filers",
    "/filers/*/isPrimaryFiler",      # from `role`
    "/filers/*/dateOfBirth",         # from birth_year + birth_month (day is synthesized)
    "/filers/*/isDisabled",          # from `is_permanently_disabled`
    "/filers/*/isStudent",           # from `is_student` — asked on a filer row with
                                     # retirement contributions (Form 8880's student test)
    "/formW2s", "/formW2s/*/filer",
    "/formW2s/*/writableWages", "/formW2s/*/writableFederalWithholding",
    "/formW2s/*/writableOasdiWages", "/formW2s/*/writableMedicareWages",
    "/formW2s/*/writableOasdiWithholding",
    "/formW2s/*/writableMedicareWithholding",                            # box 6
    # box 13's three checkboxes, the caller's answers on every W-2. A checked "Statutory
    # employee" box is the dictionary's own knockout; the other two move no served line at the pin.
    "/formW2s/*/statutoryEmployee", "/formW2s/*/retirementPlan", "/formW2s/*/thirdPartySickPay",
    # box 14's RRTA question, the caller's answer on every W-2. A yes is the dictionary's own
    # knockout (/flowKnockoutHasRRTACodesInBox14NotInNY — it fires in every state at the pin).
    "/formW2s/*/hasRRTACodes",
    # Schedule B Part III (lines 7a and 8), the caller's answers on every return. Any yes is
    # the dictionary's own knockout (`/hasForeignAccountsOrTrusts`); the artifact's reach runs
    # through `/requiresScheduleB` to the interest lines, and no fixture moves.
    "/hasForeignAccounts", "/isForeignTrustsGrantor", "/hasForeignTrustsTransactions",
    # the credit-history answers (Form 8862's questions), the caller's on every return; a yes
    # with a credit in play is refused by name after resolve, where the engine leaves it unresolved.
    "/eitcHadImproperClaims", "/receivedImproperClaims", "/eitcQcOfAnother",
    # Form 1040 line 26 — the root answer on every return; on a yes the amount and the two
    # follow-ups (each a no, a yes being refused by name) from the caller's answers.
    "/paidEstimatedTaxesOrFromLastYear", "/estimatedTaxPaymentWritable",
    "/paidEstimatedTaxesOrFromLastYearUnderDifferentName", "/paidEstimatedTaxesWithFormerSpouse",
    # Schedule 1 line 21 — the root answer on every return; on a yes whether the loans
    # qualify and the interest paid, from the caller's answers.
    "/hadStudentLoanInterestPayments", "/studentLoansQualify", "/studentLoanInterestAmount",
    # The rollover question answered NO — the caller's own `rolled_over_cents` of 0.
    "/form1099Rs/*/writableIsIndirectRollover",
    # IRC 221(e)(1)'s two reductions, once the loans qualify.
    "/writableStudentLoanInterestEmployerPaidSection127",
    "/writableStudentLoanInterestFromTaxFreeQtpEarnings",
    # the educator question per filer row and each filer's amount — the caller's answers.
    "/wasK12Educators", "/primaryEducatorExpensesWritable", "/secondaryEducatorExpensesWritable",
    # the IRA question per filer row, each filer's amount and inherited-IRA answer, and
    # the separate return's coverage answer — the caller's answers.
    "/madeIraContributions", "/primaryFilerTraditionalIraContributions",
    "/secondaryFilerTraditionalIraContributions", "/writablePrimaryFilerContributedToInheritedIra",
    "/writableSecondaryFilerContributedToInheritedIra", "/writableMfsSpouseCoveredByEmployerPlan",
    "/writablePrimaryFilerAmountPaidToInheritedIra", "/writableSecondaryFilerAmountPaidToInheritedIra",
    # Three paths, no fourth: `/formW2Gs` has no `IsDone` marker and no per-item `filer`, so
    # unlike the W-2 block above there is nothing here that is plumbing or an assumption. Both
    # leaves are figures the caller supplied.
    "/formW2Gs",
    "/formW2Gs/*/writableReportableWinnings", "/formW2Gs/*/writableFederalWithholding",
    # SSA-1099 / RRB-1099. The collection (empty on a return without one, the interest
    # precedent), each item's filer and form type, and the amount and withholding on the
    # writable the form type keys — the SSA pair or the RRB pair.
    # the line 6c election — the caller's answer once a statement exists, and a
    # derivation of "no statement" otherwise.
    "/writableSocialSecurityLumpSumElection",
    # Form 8960's sole-trader attestation, once the return carries a Schedule C.
    "/writableSection475eTraderInFinancialInstrumentsOrCommoditiesElection",
    "/socialSecurityReports", "/socialSecurityReports/*/filer",
    "/socialSecurityReports/*/writableFormType",
    "/socialSecurityReports/*/ssaNetBenefits", "/socialSecurityReports/*/rrbNetBenefits",
    "/socialSecurityReports/*/writableSsaFederalTaxWithheld",
    "/socialSecurityReports/*/writableRrbFederalTaxWithheld",
    # 1099-INT. `has1099` is derived from the GROUP'S OWN NAME: an `int1099s` item
    # is by definition the Form 1099-INT a payer issued, so the dictionary's no-1099 interest
    # branch is never this group's. `filer` exists here (unlike the W-2G) and is sent.
    "/interestReports", "/interestReports/*/filer", "/interestReports/*/has1099",
    "/interestReports/*/writable1099Amount",
    "/interestReports/*/writableInterestOnGovernmentBonds",
    "/interestReports/*/writableTaxExemptInterest", "/interestReports/*/writableTaxWithheld",
    *(f"/interestReports/*/{leaf}" for leaf in INT_EXTRA_EMISSION.values()),
    # Form 1099-OID. `filer` is sent; the nine money
    # boxes always (a blank is a stated 0); the box 2 tax-exempt answer on the one case the form
    # does not settle, the person's or — with no box 2 amount to classify — a stated no.
    "/originalIssueDiscountReports", "/originalIssueDiscountReports/*/filer",
    # Form 1099-B: the collection itself, and column (f)'s code W beside a box 1g amount
    # (print-only in the dictionary — "NOTHING IN THIS DICTIONARY READS THIS FACT").
    "/form8949Transactions", "/form8949Transactions/*/writableAdjustmentCodes",
    *(f"/form8949Transactions/*/{leaf}" for leaf in B1099_EMISSION.values()),
    *(f"/originalIssueDiscountReports/*/{leaf}" for leaf in OID_EMISSION.values()),
    "/originalIssueDiscountReports/*/writableBox2IsTaxExempt",
    # Form 1099-G. `has1099` is the group's own name, the interest precedent. `repaid` and
    # the same-year writable are one field (`repaid_cents`): the checkbox is the amount being
    # non-zero, as the printed line 7 instruction has it.
    "/form1099Gs", "/form1099Gs/*/filer", "/form1099Gs/*/has1099", "/form1099Gs/*/amount",
    "/form1099Gs/*/writableFederalTaxWithheld", "/form1099Gs/*/repaid",
    "/form1099Gs/*/writableAmountPaidBackForBenefitsInTaxYear",
    # Form 1099-MISC box 3. The Alaska PFD flag is the caller's own answer to the
    # dictionary's per-form question, reconciled with the root pair.
    "/form1099Miscs", "/form1099Miscs/*/filer", "/form1099Miscs/*/writableOtherIncome",
    "/form1099Miscs/*/writableFederalWithholding", "/form1099Miscs/*/writableIsAlaskaPfd",
    # Form 1099-SA. The activity twins are true for a filer with a distribution; the
    # exception pair is the filer row's own answer where reached.
    "/hsaDistributions", "/hsaDistributions/*/filer", "/hsaDistributions/*/writableGrossDistribution",
    "/hsaDistributions/*/writableQualifiedMedExpenses", "/hsaDistributions/*/hsaDistributionCode",
    "/writablePrimaryFilerHadNonW2HsaActivity", "/writableSecondaryFilerHadNonW2HsaActivity",
    # Form 2441. The providers group and the per-person amounts; the two root answers are
    # derived from whether any expense was entered; the "no expenses" answer on a qualifying row
    # without an amount is the input's own absence, sent so the section closes (measured).
    "/cdccCareProviders", "/cdccCareProviders/*/writableIsOrganization",
    "/cdccCareProviders/*/writableIsTaxExempt", "/cdccCareProviders/*/writableAmountPaidForCare",
    "/cdccCareProviders/*/writableIsHouseholdEmployee",
    "/writableCdccHasQualifyingExpenses", "/writableCdccTotalQualifiedDependentCareExpenses",
    "/familyAndHousehold/*/cdccHasDependentCareExpenses",
    "/familyAndHousehold/*/unableToCareForSelf",
    "/familyAndHousehold/*/writableCdccQualifyingExpenseAmount",
    "/filers/*/cdccHasDependentCareExpenses", "/filers/*/writableCdccQualifyingExpenseAmount",
    # Form W-2 box 10 and Form 2441 Part III — each yes/no derived from a money answer.
    "/formW2s/*/writableDependentCareBenefits",
    # Form W-2 box 12 — the four Schedule 2 line 13 codes and the seven that move nothing
    # at the pin, each a money answer (the flow variable writableHasBox12Codes is never sent).
    "/formW2s/*/uncollectedOasdiTaxOnTips",
    "/formW2s/*/uncollectedMedicareTaxOnTips",
    "/formW2s/*/taxableLifeInsuranceOver50k",
    "/formW2s/*/uncollectedOasdiTaxOnLifeInsuranceOver50k",
    "/formW2s/*/uncollectedMedicareTaxOnLifeInsuranceOver50k",
    "/formW2s/*/nsoIncome",
    "/formW2s/*/409aDeferrals",
    "/formW2s/*/healthCoverageCost",
    "/formW2s/*/qsehraBenefits",
    "/formW2s/*/83iIncome",
    "/formW2s/*/83iDeferrals",
    # Form 8880 — the eight box 12 deferral codes (line 2), code G's plan answer, the
    # self-reported line-1 pair, the line-4 distribution answers and the filed-jointly pair.
    "/formW2s/*/401kDeferrals",
    "/formW2s/*/403bDeferrals",
    "/formW2s/*/457bDeferrals",
    "/formW2s/*/501c18Deferrals",
    "/formW2s/*/simpleContributions",
    "/formW2s/*/roth401kContributions",
    "/formW2s/*/roth403bContributions",
    "/formW2s/*/roth457bContributions",
    "/formW2s/*/457bIsGovernmentalPlan",
    "/hasSelfReportedContributions",
    "/writableHasHsaExcessContributionsPreviousYear",   # from the filer rows' carry-in amounts
    "/writablePrimaryFilerIraAndAbleContributions", "/writableSecondaryFilerIraAndAbleContributions",
    "/hasDistributionsInLastThreeYears",
    "/writablePrimaryFiler2023Distributions", "/writablePrimaryFiler2024Distributions",
    "/writableSecondaryFiler2023Distributions", "/writableSecondaryFiler2024Distributions",
    "/hasCurrentYearDistributions",
    "/writablePrimaryFilerPostYearEndDistributions", "/writableSecondaryFilerPostYearEndDistributions",
    "/writableFiledJointReturnFor2023", "/writableFiledJointReturnFor2024",
    "/socialSecurityLumpSumEarlierYears",
    "/socialSecurityLumpSumEarlierYears/*/writableEarlierYear",
    "/socialSecurityLumpSumEarlierYears/*/writableEarlierYearLumpSumPortion",
    "/socialSecurityLumpSumEarlierYears/*/writableEarlierYearBenefitsReceived",
    "/socialSecurityLumpSumEarlierYears/*/writableEarlierYearAdjustedGrossIncome",
    "/socialSecurityLumpSumEarlierYears/*/writableEarlierYearExclusions",
    "/socialSecurityLumpSumEarlierYears/*/writableEarlierYearTaxExemptInterest",
    "/socialSecurityLumpSumEarlierYears/*/writableEarlierYearTaxableBenefitsReported",
    "/socialSecurityLumpSumEarlierYears/*/writableEarlierYearFiledJointly",
    "/socialSecurityLumpSumEarlierYears/*/writableEarlierYearMfsLivedWithSpouse",
    "/writablePrimaryFilerRothIraContributions",
    "/writableSecondaryFilerRothIraContributions",
    # W-2 box 12 code W and Form 8889 Part I's questions, the married filer's pair, the
    # separate return's line 6 check and the excess-in-wages answer.
    "/formW2s/*/employerHsaContributions",
    "/filers/*/enrolledInMedicare", "/filers/*/hsaHdhpCoverageStatus", "/filers/*/typeOfHdhp",
    "/filers/*/hadOtherCoverageIneligibleForHSA", "/filers/*/writableMfsLine6Check",
    "/filers/*/hasMadeQualifiedHsaFundingDistribution",   # the code W filer's own answer; the
                                                          # 1099-SA-only filer's no is stated
    # the own-contributions answer on every filer row and its two amounts.
    "/someFilerHadNonW2HsaActivity",
    "/filers/*/writablePrimaryFilerHasMadeContributionsToHsa",
    "/filers/*/writableSecondaryFilerHasMadeContributionsToHsa",
    "/filers/*/writableHsaNonemployerContributionsTaxYear",
    "/filers/*/writableHsaNonemployerContributionsTaxYearPlusOne",
    # the twelve-month coverage and Medicare vectors, prefilled from the all-year answers.
    *[f"/filers/*/writableHsaCoverageTypeMonth{m:02d}" for m in range(1, 13)],
    *[f"/filers/*/writableHsaEnrolledInMedicareMonth{m:02d}" for m in range(1, 13)],
    "/filers/*/writableChangeInMaritalStatusDuringTaxYear",
    "/filers/*/writableMaritalChangeAffectContributionLimitBool",
    "/writableHsaEmployerExcessAlreadyInW2Income",
    "/writablePrimaryFilerDependentCarePlanMaximum", "/writableSecondaryFilerDependentCarePlanMaximum",
    "/writablePrimaryFilerSelfEmployedDependentCareBenefits",
    "/writableSecondaryFilerSelfEmployedDependentCareBenefits",
    "/hasCdccCarryoverAmountFromPriorTaxYear", "/writableCdccCarryoverAmountFromPriorTaxYear",
    "/writableHasCdccForfeitedCredits", "/writableCdccForfeitedCredits",
    # Form 1095-A. The form's grid and what the mapper derives from it (the policy dates
    # from the first and last coverage months, the months themselves, the route's answers and
    # the annual totals), the root has-plan / has-advance answers, and the root questions.
    "/1095As", "/1095As/*/writablePolicyStartDate", "/1095As/*/writablePolicyEndDate",
    "/1095As/*/hasCoverageMonths", "/1095As/*/coverageMonths",
    "/1095As/*/writablePremiumsOrSlcspChange",
    "/1095As/*/writablePtcAnnualPremium", "/1095As/*/writableSlcspAnnualPremium",
    "/1095As/*/writableAptcAnnualAmount",
    *(f"/1095As/*/writablePtcMonthly{stem}{PTC_MONTH_TITLES[m]}"
      for m in PTC_MONTHS for _c, stem, _l in PTC_COLUMNS),
    "/writableHasPtcQualifyingPlan", "/writableHasAdvancedPtc",
    "/writableIsAdditionalPersonInEnrollmentFamily", "/writableWantsToUseAltCalculations",
    "/writableMarketplaceEstimatedIncomeAtLeast100Fpl",
    "/writableBelow100ThresholdAndNotEligibleForMedicaidBecauseOfImmigrationStatus",
    "/writableHasImmigrationStatusNotEligibleForMarketplace", "/writablePtcDependentsModifiedAgi",
    "/writableDependentsRequiredToFile",                                     # from the line 2b amount
    "/cdccHasCreditForPriorYearExpenses",
    "/cdccClaimedCreditForPriorYearExpenses",
    "/cdccClaimedMaxCreditForPriorTaxYear",
    "/writableCdccPriorYearForm2441Line3",
    "/writableCdccPriorYearExpensesPaidInCurrentYear",
    "/writableCdccPriorYearHadTwoOrMoreQualifyingPersons",
    "/writableCdccPriorYearExcludedOrDeductedBenefits",
    "/writableCdccPriorYearLowerEarnedIncome",
    "/writableCdccPriorYearAmountCreditWasFiguredOn",
    "/writableCdccPriorYearAgi",
    "/writableHasMfsException", "/writableClaimingMfsExceptionForFourthStraightYear",
    "/filers/*/writableHsaCollectionExceptionAmount",
    "/filers/*/writableHsaCollectionExceptionReason",
    # 1099-DIV. Seven amounts, because three boxes the old schema lacked each
    # mis-state a return that carries them: box 5 is the QBI deduction's input, box 12 moves the
    # senior deduction's MAGI, box 2b re-rates a slice of box 2a.
    # 1099-R. `taxable_amount` is deliberately NOT always here: absence sends
    # NOTHING, and the pinned dictionary's own knockouts stop the return rather than letting
    # this service determine a taxable amount the payer did not state.
    "/form1099Rs", "/form1099Rs/*/filer", "/form1099Rs/*/writableGrossDistribution",
    "/form1099Rs/*/writeablePublicSafetyOfficer", "/form1099Rs/*/writeablePublicSafetyOfficerPremiums",
    "/form1099Rs/*/writablePsoPremiumsPaid",
    "/form1099Rs/*/writableReachedMinimumRetirementAge",
    "/form1099Rs/*/writableDateOfPayment", "/form1099Rs/*/writableBox1IsTheDeathBenefitUnderThatContract",
    "/form1099Rs/*/writableAcquiredInReportablePolicySale", "/form1099Rs/*/writableReportableDeathBenefitBasis",
    "/form1099Rs/*/writableDeathBenefitAcquiredForValuableConsideration",
    "/form1099Rs/*/writableDeathBenefitTransferHasCarryoverBasis",
    "/form1099Rs/*/writableDeathBenefitTransferToInsuredOrRelatedParty",
    "/form1099Rs/*/writableTaxableAmount", "/form1099Rs/*/writableTaxableAmountNotDetermined",
    "/form1099Rs/*/writableDistributionCode", "/form1099Rs/*/iraSepSimple",
    "/form1099Rs/*/writableFederalWithholding",
    "/dividendReports", "/dividendReports/*/filer",
    "/dividendReports/*/writableOrdinaryDividends",
    "/dividendReports/*/writableQualifiedDividends",
    "/dividendReports/*/writableCapitalGainDistributions",
    "/dividendReports/*/writableUnrecapturedSection1250Gain",
    "/dividendReports/*/writableFederalWithholding",
    "/dividendReports/*/writableSection199ADividends",
    "/dividendReports/*/writableExemptInterestDividends",
    # Schedule C. `hasScheduleCIncome` is derived from the group's own presence
    # (the `has1099` reading). The two loss-gate booleans are the FILER'S OWN answers to line G
    # and box 32a — asked when line 31 is a loss, never defaulted. RETIRED: the sentence
    # that stood here ("`writableAllInvestmentAtRisk` is emitted only as TRUE: a false is
    # refused before mapping (the Form 6198 branch), which keeps `writableAmountAtRisk`
    # provably outside this emission surface"): box 32b is answered now, so the boolean is
    # emitted both ways and the simplified Form 6198 amount rides beside a false.
    "/hasScheduleCIncome",
    "/scheduleCs", "/scheduleCs/*/filer",
    "/scheduleCs/*/writableGrossReceipts", "/scheduleCs/*/writableReturnsAndAllowances",
    "/scheduleCs/*/writableCostOfGoodsSold", "/scheduleCs/*/writableOtherBusinessIncome",
    "/scheduleCs/*/writableTotalExpenses", "/scheduleCs/*/writableLineBPrincipalBusinessCode",
    "/scheduleCs/*/writableMateriallyParticipated", "/scheduleCs/*/writableAllInvestmentAtRisk",
    "/scheduleCs/*/writableAmountAtRisk",
    # Rentals. Same shape as Schedule C where it is the same rule (retired:
    # the clause that stood here — "`fullyAtRisk` emitted only as TRUE, keeping `amountAtRisk`
    # — the Form 6198 branch — provably outside the emission surface" — on all three streams at
    # once), and deliberately DIFFERENT where the engine is: `activeParticipation` is
    # the filer's own §469(i) answer and BOTH its values are computed (a No suspends the loss on
    # the modeled Form 8582 path — never a refusal). `priorYearUnallowedLoss` is last year's
    # Form 8582 figure, sent only when stated.
    "/hasScheduleERentalIncome",
    "/rentalProperties",
    "/rentalProperties/*/grossIncome", "/rentalProperties/*/writableLine19OtherExpense",
    "/rentalProperties/*/writableLine1bPropertyTypeCode",
    # the filer's own §469(c)(1)/(h) answer about the LESSEE business. (Its partner,
    # `/rentalProperties/*/selfRental`, is NOT here — it is derived from the line 1b code rather
    # than answered, so it is published as an assumption instead.)
    "/rentalProperties/*/materiallyParticipatesInLessee",
    "/rentalProperties/*/activeParticipation", "/rentalProperties/*/fullyAtRisk",
    "/rentalProperties/*/amountAtRisk", "/rentalProperties/*/priorYearUnallowedLoss",
    "/rentalProperties/*/writableActivelyParticipatedWhenPriorYearLossArose",
    # the itemized expense lines and the depreciation inputs — `insurance`,
    # `managementFees`, `repairs` and `taxes` MOVED here from `ASSUMED_ABOUT_TAXPAYER` (each is
    # now sometimes a real supplied figure, sometimes an unasked zero on the same emitted path;
    # the per-request zero is stated instead through `gaps._ABSENT_MEANS`). The basis and
    # placed-in-service facts are the taxpayer's own depreciation inputs; the engine computes
    # the deduction, never this service.
    "/rentalProperties/*/insurance", "/rentalProperties/*/managementFees",
    "/rentalProperties/*/repairs", "/rentalProperties/*/taxes",
    "/rentalProperties/*/buildingBasis", "/rentalProperties/*/writableIsNonresidentialRealProperty",
    "/rentalProperties/*/writableBuildingBasisUsesStandardGDS",
    "/rentalProperties/*/placedInServiceInCurrentYear", "/rentalProperties/*/placedInServiceMonth",
    "/rentalProperties/*/hasFiveYearProperty", "/rentalProperties/*/fiveYearPropertyBasis",
    # K-1s — TWO collections behind one service group, split on `source`:
    # partnership/s_corp ride /formK1s, estate_trust rides /form1041K1s (which has no per-item
    # filer — the W-2G posture). `fullyAtRisk` is emitted BOTH ways since with the
    # simplified Form 6198 amount beside a false; a negative box 14A goes through VERBATIM
    # beside the deductible part the service asks.
    "/writableHasK1Income", "/writableHasEstateTrustK1",
    "/writableHasRoyaltyIncome",
    "/formK1s", "/formK1s/*/filer", "/formK1s/*/entityType", "/formK1s/*/ordinaryIncome",
    "/formK1s/*/writableIsPubliclyTradedPartnership", "/formK1s/*/materiallyParticipated",
    "/formK1s/*/basis", "/formK1s/*/fullyAtRisk", "/formK1s/*/amountAtRisk",
    "/formK1s/*/writableSeEarnings",
    # the partner's own already-limited deductible part of a box 14A loss — an INPUT,
    # transcribed off the printed partner instruction, never derived here.
    "/formK1s/*/writableDeductibleSeEarningsLoss",
    # the guaranteed-payments pair and item G.
    "/formK1s/*/writableGuaranteedPaymentsServices",
    "/formK1s/*/writableGuaranteedPaymentsCapital", "/formK1s/*/writablePartnerIsGeneralPartner",
    # box 20 code Z — the qualified PTP amount, its SSTB flag and the §469(k) carry-in.
    "/formK1s/*/writableQualifiedPtpIncomeOrLoss", "/formK1s/*/writableQualifiedPtpIsSstb",
    "/formK1s/*/writablePtpPriorYearUnallowedLoss",
    "/formK1s/*/writablePortfolioInterestIncome", "/formK1s/*/writablePortfolioOrdinaryDividends",
    "/formK1s/*/writablePortfolioQualifiedDividends", "/formK1s/*/writableK1065Box7Royalties",
    "/form1041K1s",
    "/form1041K1s/*/writableBox1InterestIncome", "/form1041K1s/*/writableBox2aOrdinaryDividends",
    "/form1041K1s/*/writableBox2bQualifiedDividends",
    "/form1041K1s/*/writableBox6OrdinaryBusinessIncome",
    # mfs and the spouse chain — every one of these is the filer's own answer
    # (`/MFSLivingSpouseFilingReturn` was once assumed; asked now).
    "/spouseItemizes", "/MFSLivingSpouseFilingReturn", "/MFSSpouseHasGrossIncome",
    "/MFSSpouse65OrOlder",
    # Dependents. Every asked qualifier plus the derivations that carry it:
    # the (category, specific) relationship pair from the one `relationship` code, the
    # residency buckets from `months_in_home`, `tpClaims` from the row's own meaning (a
    # dependent row IS the claim), the tinType/validity pair from `tin_type`, and the
    # filer-side validity enums the CTC gate reads.
    "/familyAndHousehold",
    "/familyAndHousehold/*/dateOfBirth", "/familyAndHousehold/*/tinType",
    "/familyAndHousehold/*/ssnEmploymentValidity",
    "/familyAndHousehold/*/relationshipCategory", "/familyAndHousehold/*/childRelationship",
    "/familyAndHousehold/*/siblingRelationship",
    "/familyAndHousehold/*/parentalRelationship", "/familyAndHousehold/*/inlawRelationship",
    "/familyAndHousehold/*/residencyDuration", "/familyAndHousehold/*/monthsLivedWithTPInUS",
    "/familyAndHousehold/*/married", "/familyAndHousehold/*/ownSupport",
    # the joint-return test. Two of these three were published attestations until this
    # unit; all three are the filer's own answers now, sent only as far as the chain reaches.
    "/familyAndHousehold/*/writableJointReturn",
    "/familyAndHousehold/*/writableRequiredToFile",
    "/familyAndHousehold/*/writableFilingOnlyForRefund",
    "/familyAndHousehold/*/grossIncomeTest", "/familyAndHousehold/*/writableQrSupportTest",
    "/familyAndHousehold/*/writableCouldBeQualifyingChildOfAnother",
    # the split gate's custody questions — the caller's answers, as far as reached (the
    # emancipation date a synthesized day on the answered side of July 2).
    "/familyAndHousehold/*/writableChildResidenceJurisdiction",
    "/familyAndHousehold/*/writableChildEmancipatedUnderStateLaw",
    "/familyAndHousehold/*/writableChildEmancipationDate",
    # the member-of-household questions — the caller's answers, as far as reached.
    "/familyAndHousehold/*/writableWasSpouseAtAnyTimeInTaxYear",
    "/familyAndHousehold/*/writableCdccRelationshipViolatesLocalLaw",
    "/familyAndHousehold/*/hasOtherBiologicalOrAdoptiveParent",
    # the non-parental arm's first question — the caller's answer, sent only as a NO.
    "/familyAndHousehold/*/biologicalOrAdoptiveParentsLiving",
    # the custodial-parent questions — the caller's answers, sent as far as reached.
    "/familyAndHousehold/*/nightsWithTpVsOtherParent",
    "/familyAndHousehold/*/tpAgiHigherThanOtherParent",
    # the non-parental split's own writables — the caller's answers, as far as reached.
    # the lived-together chain — the caller's answers on a married return, as far as reached.
    "/livedTogetherAllYearWithSpouse", "/spouseLivedTogetherMonths",
    "/writableSeparationAgreement", "/writableLivedApartLastSixMonths",
    "/familyAndHousehold/*/parentsMeetReqsRuleForChildrenOfDivorcedParents",
    "/familyAndHousehold/*/nonParentalSomeParentNotClaiming",
    "/familyAndHousehold/*/specialRuleChildUsedByCustodialParentAsQP",
    "/familyAndHousehold/*/specialRuleAgiTest",
    # the benefit-split gate. All five are the filer's own answers, sent only as far as
    # the chain reaches — nothing here was ever an attestation, because the whole population
    # was refused outright until this unit.
    "/familyAndHousehold/*/parentalSituation",
    "/familyAndHousehold/*/inParentsCustody",
    "/familyAndHousehold/*/livedWithTpOrOtherBiologicalOrAdoptiveParentMoreThanSixMonths",
    "/familyAndHousehold/*/parentalSupport",
    "/familyAndHousehold/*/whichParentNotClaiming",
    "/familyAndHousehold/*/fullTimeStudent",
    "/familyAndHousehold/*/permanentTotalDisability",
    "/familyAndHousehold/*/tpClaims",
    "/primaryFilerSsnEmploymentValidity", "/secondaryFilerSsnEmploymentValidity",
    # Form 1040 line 12's blindness checkbox — “You: Are blind” on every status,
    # “Spouse: Is blind” on a joint return — asked per filer row. The SAME normalised path
    # already carried the separate-return spouse answer, so nothing new is emitted here:
    # the attestation became an answer.
    "/filers/*/isBlind",
    # the "someone can claim you" chain — the caller's answers, as far as reached.
    "/filers/*/canBeClaimed", "/filers/*/willBeClaimed", "/filers/*/potentialClaimerMustFile",
    "/filers/*/potentialClaimerDidFile", "/primaryFilerPotentialClaimerFiledOnlyForRefund",
    # the joint return's filing-requirement pair behind a claimable spouse.
    "/MFJRequiredToFile", "/MFJDependentsFilingForCredits",
    # the page-1 digital-assets question, both parts — the caller's answers on every
    # return. No served line reads them; a yes is the dictionary's own knockout.
    "/receivedDigitalAssets", "/disposedDigitalAssets",
    # the residence state on every return; the Alaska dividend answers behind `ak`.
    "/filerResidenceAndIncomeState", "/receivedAlaskaPfd", "/spouseReceivedAlaskaPfd",
    # hoh/qss — the campaign's last unit: the keeping-up-home answer and the
    # qss pair. Eligibility-side only (no served line moves on them; the post-resolve gate
    # reads the engine's own eligibility answer). the upkeep answer also emits on a
    # single return's qualifying rows, where it completes the household section and moves
    # nothing.
    "/familyAndHousehold/*/tpPaidMostOfHomeUpkeep",
    "/yearOfSpouseDeath", "/canFileJointlyYearOfSpouseDeath",
})


def assumptions() -> list:
    """The published statements, sorted for a byte-stable answer (provenance rule 4)."""
    return sorted(ASSUMED_ABOUT_TAXPAYER.values())


def _normalise_path(path: str) -> str:
    """`/filers/#a0000000-.../isBlind` -> `/filers/*/isBlind`. Collection ids are per-request."""
    import re
    return re.sub(r"#[0-9a-f-]+", "*", path)


def assumptions_for(facts: dict, tax_year: int = 2025, birth_days: dict | None = None) -> list:
    """What was assumed about THIS return — not the general list.

    `coverage` answers "what does this service assume?"; a response has to answer "what did it assume
    about me?", or the preparer acknowledging it at submit is acknowledging boilerplate. A fact set
    with no W-2 must not claim anything about W-2 box 13.

    DERIVED, by intersecting the published set with the writables `map_to_engine` actually emitted
    for this request — the same method the partition test uses. That makes the per-response subset a
    property of the request rather than a second table to keep in step with the first.

    Raises whatever `map_to_engine` raises: assumptions describe a computation that HAPPENED, and
    there is none behind a refusal.
    """
    emitted = {_normalise_path(p) for p in map_to_engine(facts, tax_year, birth_days=birth_days)["facts"]}
    return sorted(statement for path, statement in ASSUMED_ABOUT_TAXPAYER.items()
                  if path in emitted)


def _scaffold(filing_status: str) -> dict:
    """The structural (non-income, non-person) writables a simple ty2025 return needs, with safe
    defaults. Derived from the demo profiles' structural fact set; parameterized by filing status."""
    f = {}
    for empty in ("/1095As", "/cdccCareProviders", "/form1099Gs", "/form1099Miscs",
                  "/hsaDistributions", "/socialSecurityReports",
                  # build's own single-filer scenarios send the interest collection
                  # EMPTY rather than omitting it. Omitted, every per-item /interestReports/*
                  # derivation resolves ABSENT, /totalIncome inherits Placeholder through the
                  # interest aggregate, and so does /agi. The income mappers overwrite these
                  # when the stream is present.
                  "/interestReports"):
        f[empty] = _collection([])
        f[empty + "IsDone"] = _bool(True)
    # Same convention, no IsDone marker in build's scenario for these two.
    f["/form1099Rs"] = _collection([])
    # Form 1099-G box 2 is a ROOT intake at the pin (not a leaf of `/form1099Gs`, which
    # holds unemployment compensation only). Measured: absent and zero resolve the same return;
    # a figure leaves total income unresolved until the prior-year worksheet is answered, which
    # this service does not carry. Emitted zero so the assumption is a real emission, published.
    f["/writableStateAndLocalIncomeTaxRefundReceived"] = _dollar(0)
    f["/familyAndHousehold"] = _collection([])
    # `/familyAndHouseholdIsDone` is a plain writable Boolean — the dictionary's own words
    # are "The user has clicked Done for the family and HH section" — with a Placeholder of False,
    # so every served return read it Placeholder false and it was one of the members holding
    # `/flowIncomplete` true. Sending it is safe and says nothing about the taxpayer: the REAL
    # incompleteness signal is a DIFFERENT fact, `/hasIncompleteDependents` (its own
    # `BlockSubmissionOnTrue`, a count of `/familyAndHousehold/*/isIncomplete`), whose derivation
    # never reads this marker — so the marker cannot mask it. That signal read TRUE wherever a
    # claimed person's keeping-up-home question was unanswered off an hoh/qss return; the
    # question is now asked on every row the engine's own screen gate asks it of
    # (`upkeep_question_armed`), so the single fixtures resolve it false — and, since the
    # lived-together chain is asked on a married return, on the joint fixture too;
    # `FlowIncompleteIsHonestlyTrueTest` locks the per-fixture table. The marker is sent unconditionally, with or without
    # dependents, because the section is equally finished either way — a return with no
    # dependents has answered the dependents section by having none. `/flowIncomplete` itself
    # stays TRUE after this, and honestly so: its `/aboutYouIsComplete` member wants the filer's
    # name, address and phone, which no schema here can carry.
    f["/familyAndHouseholdIsDone"] = _bool(True)
    # the Form 8995-A arm. ABOVE the section 199A threshold (2025: 197,300 single /
    # 394,600 mfj, 50,000 phase-in) `taxCalculations:/qualifiedBusinessIncomeDeduction` took
    # its $0 catch-all on EVERY served return: Form 8995's arm wants taxable income at or
    # below the threshold, and Form 8995-A's wants `qbi:/claims8995A`, whose writable this
    # service emitted for nobody. Measured at the pin, all three regimes:
    #   * the claim ALONE breaks the return — `/qbi8995aDpadPassThrough` (Form 8995-A line 38)
    #     has NO fall-through without an ANSWERED `/qualifiedBusinesses`, so `/taxableIncome`
    #     and `/totalTax` resolve Incomplete and the runner discards them. The two facts are
    #     one change, never one without the other;
    #   * the claim over an EMPTY collection computes the qualified REIT dividend / publicly
    #     traded partnership half (Form 8995-A lines 28-32), which needs no per-business
    #     detail: 1,190 on the SSTB PTP fixture, 200 on 1,000 of section 199A dividends;
    #   * BELOW the threshold and on a return with no QBI input at all it moves NOTHING
    #     (`/qbiUsesForm8995A` stays false there) — measured across the whole committed
    #     corpus, of which exactly ONE fixture moved (the SSTB PTP one, re-blessed).
    # The EMPTY collection is not a claim that the filer has no business: it is the absence of
    # the Part II per-business detail (W-2 wages, unadjusted basis of property) this schema
    # carries no intake for, published as an assumption and REFUSED post-resolve on the one
    # population where it drops a component — an above-threshold return whose Schedule C
    # profit is auto-derived qualified business income (measured: Form 8995-A line 27 = 0
    # against 39,464 of `/qbiAutoDerivedAmount`, in the phase-in range and above the upper
    # threshold alike). There is no `/qualifiedBusinessesIsDone` twin in the pinned
    # dictionary; the collection's own answeredness is what the gate reads.
    f["/qualifiedBusinesses"] = _collection([])
    f["/writableClaims8995A"] = _bool(True)
    for flag, val in {
        # (`/disposedDigitalAssets` and `/receivedDigitalAssets` were attested false here
        # until the service asked them — `DIGITAL_ASSET_EMISSION`.)
        # (`/hasForeignAccounts`, `/hasForeignTrustsTransactions` and `/isForeignTrustsGrantor`
        # were attested false here until the service asked them — `FOREIGN_ACCOUNT_EMISSION`.)
        # (`/hadStudentLoanInterestPayments` was attested false here until the service asked it —
        # `student_loan_questions_reached` and the emission in `map_to_engine`.)
        # (`/madeIraContributions` was attested false here until the service asked it on every filer
        # row — `ira_questions_reached` and the emission after the filers block.)
        # (`/paidEstimatedTaxesOrFromLastYear` was attested false here until the service asked it —
        # `estimated_payments_questions_reached` and the emission in `map_to_engine`.)
        # (`/hasCdccCarryoverAmountFromPriorTaxYear` was attested false here once —
        # `_cdcc_section` derives it from the line 13 carryover.)
        # (`/writableSocialSecurityLumpSumElection` was once answered no here and published;
        # it is asked once a benefit statement exists — the emission in `map_to_engine`.)
        # (`/receivedAlaskaPfd` was attested false here until `ALASKA_PFD_EMISSION`.)
        # (The Form 8862 gate on the child credits, `/receivedImproperClaims`,
        # and the EITC pair, `/eitcHadImproperClaims` / `/eitcQcOfAnother`, were attested false
        # here —
        # unanswered, every return with a qualifying child resolves its payments Placeholder
        # and the credit a placeholder 0. All three are asked now — `CREDIT_HISTORY_EMISSION` —
        # and a yes with a credit in play is refused after resolve rather than served with
        # that placeholder 0 as a figure.)
        # `/livedTogetherAllYearWithSpouse` was once attested TRUE here on a separate return; it is
        # asked now (with the rest of the lived-together chain) on every married return — see
        # `lived_together_questions_reached` and the emission in `map_to_engine`.
        # (`/writableCdccHasQualifyingExpenses` was attested false here until derived
        # from the persons rows' care expenses in `_cdcc_section` now.)
        "/someFilerHadNonW2HsaActivity": False,
        # (`/writableHasPtcQualifyingPlan` was attested false here until derived from
        # the Form 1095-A group in `_ptc_section` now.)
        "/flowKnockoutHouseholdEmployee": False,
        "/incomeSourcesSupported": True, "/is1099RFeatureFlagEnabled": True,
        "/hasCompleted1099RSection": True, "/hasSome1099rFormsBeforeSectionEnabled": False,
        "/hasSeenReviewScreen": True, "/flowHasSeenAmount": True,
        "/flowHasSeenCreditsIntroNoCredits": True, "/flowHasSeenDeductions": True,
        "/flowHasSeenTotalIncomeSummary": True,
    }.items():
        f[flag] = _bool(val)
    f["/filingStatus"] = _enum("/filingStatusOptions", _DICT_FILING[filing_status])
    f["/maritalStatus"] = _enum("/maritalStatusOptions", _MARITAL[filing_status])
    f["/presidentalCampaignDesignation"] = _enum("/presidentalCampaignOptions", "neither")
    # (`/wasK12Educators` was attested `neither` here until the service asked it on every filer row —
    # derived from the rows' answers after the filers block in `map_to_engine`.)
    return f


# The dictionary's relationship model is a CATEGORY enum plus a per-category specific enum
# (dependentsRelationship.xml); the service's flat 27-code vocabulary (spelled from the
# pinned /relationshipOptions) maps one-to-one onto (category, specific-fact, literal) triples.
# `none_of_the_above` is the category `notRelated` with no specific fact.
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

# The child-category codes — the population the benefit-split question (another biological or
# adoptive parent) belongs to; measured: a non-child dependent completes without it.
_CHILD_CATEGORY = frozenset(code for code, (cat, _f, _l) in _RELATIONSHIP.items()
                            if cat == "childOrDescendants")

# The dictionary's two relationship tests — `/familyAndHousehold/*/qcRelationshipTest` and
# `/familyAndHousehold/*/qrRelationshipTest` (dependentsRelationship.xml) — spelled in this
# service's own 27-code vocabulary. They are written out rather than derived from
# `_RELATIONSHIP`'s categories because the categories do NOT decide them: `foster_parent`,
# `step_grand_parent` and `step_sibling_of_parent` are `parentOrAncestors` codes the
# qualifying-RELATIVE test omits (no limb of IRC 152(d)(2) reaches them; they qualify only by the
# whole-year member-of-household route), and the three
# `child_of_*_sibling` / `other_descendant_of_*_sibling` codes split across the two tests. Every
# cell is measured against the engine by `UpkeepOnASingleReturnTest`'s mirror test, so a pin that
# moves either list fails by name instead of drifting.
_QC_RELATIONSHIP_TEST = frozenset({
    "biological_child", "adopted_child", "step_child", "foster_child",
    "grand_child_or_other_descendant_of_child",
    "sibling", "half_sibling", "step_sibling",
    "child_of_sibling", "child_of_half_sibling", "child_of_step_sibling",
    "other_descendant_of_sibling", "other_descendant_of_half_sibling",
    "other_descendant_of_step_sibling",
})
_QR_RELATIONSHIP_TEST = frozenset({
    "biological_child", "adopted_child", "step_child", "foster_child",
    "grand_child_or_other_descendant_of_child",
    "sibling", "half_sibling", "step_sibling",
    "child_of_sibling", "child_of_half_sibling",
    "parent", "step_parent", "grand_parent", "other_ancestor_of_parent", "sibling_of_parent",
    "child_in_law", "parent_in_law", "sibling_in_law", "siblings_spouse",
})

# months_in_home -> the dictionary's residency buckets. 6 months exactly maps to the
# not-more-than-half branch DELIBERATELY: the statute says MORE than one-half, and this service
# will not round a tie in the credit's favour (the schema description says so to the caller).
_MONTH_WORDS = {7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def dependent_residency_duration(person: dict):
    """The `/residencyDuration` literal this row will be MAPPED to, or None when the row has not
    answered `months_in_home` yet.

    One function so the bucket the engine receives and the bucket `upkeep_question_armed`
    reasons about cannot drift apart — one discipline: the ask, the backstop and the
    refusal read the same arithmetic the mapper writes.
    """
    months = person.get("months_in_home")
    if not isinstance(months, int) or isinstance(months, bool):
        return None
    if months == 12:
        return "allYear"
    if months >= 7:
        return "sevenToElevenMonths"           # more than half of the year, not all of it
    if months == 6:
        return "sixMonths"                     # six months, but not more than half of the year
    return "lessThanSixMonths"


# The lived-together chain, asked on every MARRIED return (mfj, mfs) in the dictionary's
# order (filers.xml): `livedTogetherAllYearWithSpouse` → if no, `spouseLivedTogetherMonths`
# (`/spouseLivedTogetherMonthsOptions`: livedApartAllYear / livedTogetherMoreThanSixMonths /
# livedTogetherSixMonthsOrLess) → more than six asks `writableSeparationAgreement` (for the
# spouse flow to complete), six or less asks `writableLivedApartLastSixMonths`. The derived
# `/livedApartLastSixMonths` — false when together all year or more than six months, true when
# apart all year, the leaf's answer when six months or less — is what `/filerCouldQualifyForHoh`
# reads on a married return, and through it the child's keeping-up-home gate. Measured on the
# joint fixture: every cell resolves, `/hasIncompleteDependents` false, no served figure moves.
MARRIED_ROOT_FIELDS = frozenset({"lived_with_spouse_all_year", "months_lived_with_spouse",
                                 "separation_agreement_on_last_day", "lived_apart_last_six_months"})
_MONTHS_WITH_SPOUSE = {"apart_all_year": "livedApartAllYear",
                       "more_than_six_months": "livedTogetherMoreThanSixMonths",
                       "six_months_or_less": "livedTogetherSixMonthsOrLess"}
LIVED_TOGETHER_EMISSION = {
    "lived_with_spouse_all_year": "/livedTogetherAllYearWithSpouse",
    "months_lived_with_spouse": "/spouseLivedTogetherMonths",
    "separation_agreement_on_last_day": "/writableSeparationAgreement",
    "lived_apart_last_six_months": "/writableLivedApartLastSixMonths",
}


def lived_together_questions_reached(facts: dict) -> list:
    """the lived-together questions this return's answers so far REACH, in order — the
    root on every married return, each later one only when the previous answer opens it. One
    predicate, four uses (the gap, the statement surface, the backstop + unreached refusal,
    the emission)."""
    if not isinstance(facts, dict) or facts.get("filing_status") not in ("mfj", "mfs"):
        return []
    reached = ["lived_with_spouse_all_year"]
    if facts.get("lived_with_spouse_all_year") is not False:
        return reached
    reached.append("months_lived_with_spouse")
    months = facts.get("months_lived_with_spouse")
    if months == "more_than_six_months":
        reached.append("separation_agreement_on_last_day")
    elif months == "six_months_or_less":
        reached.append("lived_apart_last_six_months")
    return reached


def lived_apart_last_six_months_resolved(facts: dict):
    """the dictionary's derived `/livedApartLastSixMonths` on the answers so far — True,
    False, or None while the chain has not reached an answer that settles it."""
    if not isinstance(facts, dict) or facts.get("filing_status") not in ("mfj", "mfs"):
        return None
    together = facts.get("lived_with_spouse_all_year")
    if together is True:
        return False
    if together is not False:
        return None
    months = facts.get("months_lived_with_spouse")
    if months == "apart_all_year":
        return True
    if months == "more_than_six_months":
        return False
    if months == "six_months_or_less":
        leaf = facts.get("lived_apart_last_six_months")
        return leaf if isinstance(leaf, bool) else None
    return None


def refuse_misplaced_lived_together_answers(facts: dict) -> None:
    """a lived-together answer on an unmarried return, or past where the chain reaches, is
    refused BY NAME, never dropped; a reached link left unanswered is backstopped by name."""
    reached = lived_together_questions_reached(facts)
    for field in sorted(MARRIED_ROOT_FIELDS):
        if field not in facts or field in reached:
            continue
        if facts.get("filing_status") not in ("mfj", "mfs"):
            raise ServiceFactsError(
                f"{field} is answered on a {facts.get('filing_status')!r} return — the "
                f"lived-together questions are asked on a married return only; refused rather "
                f"than dropped")
        raise ServiceFactsError(
            f"{field} is answered but the lived-together questions do not reach it with the "
            f"answers given (living together all year, or the months answered, has already "
            f"settled it); refused rather than dropped")
    if facts.get("months_lived_with_spouse") not in (None, *_MONTHS_WITH_SPOUSE):
        raise ServiceFactsError(
            f"months_lived_with_spouse is {facts.get('months_lived_with_spouse')!r}, which is not "
            f"one of the dictionary's three answers (apart_all_year, more_than_six_months, "
            f"six_months_or_less); refused rather than dropped")
    for field in reached:
        if field not in facts:
            raise FactsSchemaError(
                f"{field} is a question on every married return, not a default — answer it "
                f"(prepare_return asks it as a gap)")


# The Form 1040 page-1 checkbox "Someone can claim: You as a dependent", asked as the
# dictionary asks it (filers.xml): `canBeClaimed` → if yes, `willBeClaimed` and
# `potentialClaimerMustFile` → if the claimer need not file, `potentialClaimerDidFile` → if they
# filed, `/primaryFilerPotentialClaimerFiledOnlyForRefund`. `primaryFilerIsClaimedAsDependent` =
# (canBeClaimed AND (mustFile OR (didFile AND NOT filedOnlyForRefund))) AND willBeClaimed AND NOT
# taxpayerCannotBeClaimed; a claimed dependent filer's standard deduction is the greater of
# $1,350 or earned income + $450, capped at the regular amount, and the EITC is not allowed —
# measured: wages 10,000 → line 12 10,450, EITC 649 → 0. The ROOT is asked on every filer row
# (a spouse's checkbox is printed too); the chain past it runs on the PRIMARY row — the spouse's
# own chain (`secondaryFilerIsClaimedAsDependent`) waits on the joint filing-requirement flow
# (`/MFJRequiredToFile`, `/MFJClaimingRefundOnly`), not asked, so a spouse's YES is refused by
# name rather than computed on a hole.
CLAIM_ME_FIELDS = frozenset({"someone_can_claim_you", "expect_to_be_claimed",
                             "potential_claimer_must_file", "potential_claimer_filed",
                             "potential_claimer_filed_only_for_refund"})
CLAIM_ME_EMISSION = {"someone_can_claim_you": "canBeClaimed", "expect_to_be_claimed": "willBeClaimed",
                     "potential_claimer_must_file": "potentialClaimerMustFile",
                     "potential_claimer_filed": "potentialClaimerDidFile"}


def claim_me_questions_reached(person) -> list:
    """the "someone can claim you" questions this ROW's answers so far REACH, in order —
    the root on every filer row, the links on the primary row once the root is yes. One
    predicate, four uses (the gap, the statement surface, the backstop + refusals, the emission)."""
    if not isinstance(person, dict) or person.get("role") not in ("primary", "spouse"):
        return []
    reached = ["someone_can_claim_you"]
    if person.get("someone_can_claim_you") is not True:
        return reached
    if person.get("role") == "spouse":
        # the dictionary's spouse chain reads canBeClaimed and willBeClaimed; the rest of
        # the decision is the COUPLE's (`mfj_claim_questions_reached`), asked at the root.
        return reached + ["expect_to_be_claimed"]
    reached += ["expect_to_be_claimed", "potential_claimer_must_file"]
    if person.get("potential_claimer_must_file") is not False:
        return reached
    reached.append("potential_claimer_filed")
    if person.get("potential_claimer_filed") is True:
        reached.append("potential_claimer_filed_only_for_refund")
    return reached


def refuse_misplaced_claim_me_answers(persons: list) -> None:
    """an answer off the chain's reach — on a dependent row, past the reach on a filer
    row, or a spouse's YES (the joint filing-requirement flow behind it is not asked) — is
    refused BY NAME, never dropped; a reached link left unanswered is backstopped by name."""
    for i, person in enumerate(persons):
        if not isinstance(person, dict):
            continue
        reached = claim_me_questions_reached(person)
        for field in sorted(CLAIM_ME_FIELDS):
            if field not in person or field in reached:
                continue
            if person.get("role") == "dependent":
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered on a dependent row — the \"someone can "
                    f"claim you\" questions are the filer's own, printed on Form 1040 page 1; "
                    f"refused rather than dropped")
            raise ServiceFactsError(
                f"persons[{i}].{field} is answered but the \"someone can claim you\" questions "
                f"do not reach it with the answers given (a no has settled it, or the claimer "
                f"must file); refused rather than dropped")
        # (A spouse's yes was refused here until the service asked the couple's filing-requirement
        # questions that decide it — `mfj_claim_questions_reached`.)
        for field in reached:
            if field not in person:
                raise FactsSchemaError(
                    f"persons[{i}].{field} is a question on this filer row — Form 1040 page 1, "
                    f"\"Someone can claim: You as a dependent\" — not a default; answer it "
                    f"(prepare_return asks it as a gap)")


# On a JOINT return whether either spouse is claimed as someone's dependent turns on the
# couple (filers.xml): `secondaryFilerIsClaimedAsDependent` needs NOT `/MFJRequiredToFile`, and
# `/taxpayerCannotBeClaimed` (the couple files for tax benefits, so nobody can claim them) =
# treatAsMFJ AND the flow subsection AND NOT required AND NOT `/MFJClaimingRefundOnly` (= NOT the
# writable `/MFJDependentsFilingForCredits`). The dictionary shows the subsection once a spouse
# can be claimed or the primary could be a dependent. Measured (both W-2s 8,000): required →
# nobody claimed (31,500 / EITC 649); not required and filing for credits → nobody CAN be
# claimed (the same); not required and refund-only → claimed (16,450 / 0). The primary's claim
# on a joint return was once served with the requirement unanswered — a Placeholder
# false let 16,450 through — and a spouse's yes was refused.


def mfj_claim_questions_reached(facts: dict) -> list:
    """the couple's filing-requirement questions this joint return's answers REACH —
    the first once any filer row is answered claimable, the refund-only one once the couple is
    answered not required to file. One predicate, four uses."""
    if not isinstance(facts, dict) or facts.get("filing_status") != "mfj":
        return []
    rows = [p for p in (facts.get("persons") or []) if isinstance(p, dict)
            and p.get("role") in ("primary", "spouse")]
    if not any(p.get("someone_can_claim_you") is True for p in rows):
        return []
    reached = ["couple_required_to_file"]
    if facts.get("couple_required_to_file") is False:
        reached.append("couple_files_only_for_refund")
    return reached


def refuse_misplaced_mfj_claim_answers(facts: dict) -> None:
    """a couple's answer past the reach (nobody claimable; or required, so the refund-only
    question is not reached) is refused by name; a reached one left unanswered is backstopped.
    Off a joint return the STATUS_ROOT_FIELDS owner rule refuses it first."""
    if facts.get("filing_status") != "mfj":
        return
    reached = mfj_claim_questions_reached(facts)
    for field in sorted(MFJ_ROOT_FIELDS):
        if field in facts and field not in reached:
            raise ServiceFactsError(
                f"{field} is answered but the joint return's filing-requirement questions do "
                f"not reach it with the answers given (they are asked once a spouse can be "
                f"claimed as someone's dependent, and the refund-only one only when the couple "
                f"is not required to file); refused rather than dropped")
    for field in reached:
        if field not in facts:
            raise FactsSchemaError(
                f"{field} is a question on a joint return where a spouse can be claimed as "
                f"someone's dependent, not a default — answer it (prepare_return asks it as a gap)")


def refuse_missing_residence_state(facts: dict) -> None:
    """the residence state is asked on every return — absent, a question (backstopped);
    a code outside the dictionary's list is refused by name (the schema refuses it first)."""
    if RESIDENCE_STATE_FIELD not in facts:
        raise FactsSchemaError(
            f"{RESIDENCE_STATE_FIELD} is the residence-state question, asked on every return, "
            f"not a default — answer it (prepare_return asks it as a gap)")
    if facts[RESIDENCE_STATE_FIELD] not in RESIDENCE_STATES:
        raise ServiceFactsError(
            f"{RESIDENCE_STATE_FIELD} {facts[RESIDENCE_STATE_FIELD]!r} is not one of the "
            f"dictionary's jurisdictions (a two-letter postal code, dc, moreThanOne or "
            f"noneOfThese); refused rather than guessed")


def alaska_pfd_questions_reached(facts: dict) -> list:
    """the Alaska Permanent Fund dividend questions this return REACHES — the filer's on
    every return, the spouse's too on a joint return (the dictionary's own completeness wants
    exactly those). One predicate, four uses (the gap, the statement, the backstop + refusals,
    the emission)."""
    if not isinstance(facts, dict):
        return []
    reached = ["received_alaska_pfd"]
    if facts.get("filing_status") == "mfj":
        reached.append("spouse_received_alaska_pfd")
    return reached


def refuse_misplaced_alaska_pfd_answers(facts: dict) -> None:
    """an answer past the reach is refused by name; a reached one left unanswered is
    backstopped; a YES is refused by name — the income it announces (Form 1099-MISC, Alaska
    Permanent Fund dividend) is not a covered stream, and the dictionary would compute the
    return without it in silence."""
    reached = alaska_pfd_questions_reached(facts)
    for field in sorted(ALASKA_PFD_FIELDS):
        if field in facts and field not in reached:
            raise ServiceFactsError(
                f"{field} is answered but the Alaska Permanent Fund dividend questions do not "
                f"reach it (the spouse's is asked on a joint return only); refused rather than "
                f"dropped")
    for field in reached:
        if field not in facts:
            raise FactsSchemaError(
                f"{field} is the Alaska Permanent Fund dividend question, asked on every return "
                f"(the spouse's on every joint return), not a default — answer it "
                f"(prepare_return asks it as a gap)")
    # a yes is RECONCILED with the 1099-MISC stream rather than refused outright (the
    # blanket refusal stood until the stream was covered). Measured at the pin, a yes
    # with no item flagged computes the return in silence without the dividend, and a flagged
    # item beside a no routes the amount to the Alaska total in silence — so each contradiction
    # is refused by name, and a yes with a flagged item for that person goes through.
    items = facts.get("misc1099s") or []
    persons = facts.get("persons") or []
    for field, role in (("received_alaska_pfd", "primary"),
                        ("spouse_received_alaska_pfd", "spouse")):
        if field not in reached:
            continue
        index = next((i for i, p in enumerate(persons)
                      if isinstance(p, dict) and p.get("role") == role), None)
        flagged = [i for i, item in enumerate(items)
                   if isinstance(item, dict) and item.get(MISC_PFD_FIELD) is True
                   and item.get("person") == index]
        if facts[field] is True and not flagged:
            raise ServiceFactsError(
                f"{field} is yes, but no Form 1099-MISC on this return is marked as an Alaska "
                f"Permanent Fund dividend for that person (misc1099s[].{MISC_PFD_FIELD}) — the "
                f"dictionary would compute this return without the dividend; refused rather "
                f"than computed")
        if facts[field] is False and flagged:
            raise ServiceFactsError(
                f"misc1099s[{flagged[0]}].{MISC_PFD_FIELD} is yes but {field} is no — the two "
                f"answers contradict; refused rather than guessed")


def refuse_missing_digital_asset_answers(facts: dict) -> None:
    """the page-1 digital-assets question is asked on every return, both parts — an absent
    answer is backstopped as a question, never defaulted (`gaps.gaps_for` asks first). There is
    no off-reach refusal: every status asks it, so no answer is ever misplaced."""
    for field in sorted(DIGITAL_ASSET_FIELDS):
        if field not in facts:
            raise FactsSchemaError(
                f"{field} is the Form 1040 page-1 digital-assets question, asked on every "
                f"return, not a default — answer it (prepare_return asks it as a gap)")


def estimated_payments_questions_reached(facts: dict) -> list:
    """the line 26 questions this return REACHES — the root question on every return; on a
    yes, the amount and the two follow-ups. One predicate, four uses (the gap, the statement, the
    backstop + refusals, the emission)."""
    if not isinstance(facts, dict):
        return []
    reached = [ESTIMATED_PAYMENTS_FIELD]
    if facts.get(ESTIMATED_PAYMENTS_FIELD) is True:
        reached.append(ESTIMATED_PAYMENTS_AMOUNT_FIELD)
        reached.extend(ESTIMATED_PAYMENTS_FOLLOWUP_FIELDS)
    return reached


def refuse_misplaced_estimated_payments_answers(facts: dict) -> None:
    """an answer past the reach is refused by name; a reached one left unanswered is
    backstopped; a YES on either follow-up is refused by name — the former name and the former
    spouse's TIN it would then need are identifiers this schema cannot carry."""
    reached = estimated_payments_questions_reached(facts)
    for field in sorted(ESTIMATED_PAYMENTS_FIELDS):
        if field in facts and field not in reached:
            raise ServiceFactsError(
                f"{field} is answered but the estimated tax payments questions do not reach it "
                f"(the amount and the follow-ups are asked once {ESTIMATED_PAYMENTS_FIELD} is "
                f"yes); refused rather than dropped")
    for field in reached:
        if field not in facts:
            raise FactsSchemaError(
                f"{field} is a Form 1040 line 26 question (estimated tax payments), asked on "
                f"every return that reaches it, not a default — answer it (prepare_return asks "
                f"it as a gap)")
    if facts.get("estimated_payments_under_different_name") is True:
        raise ServiceFactsError(
            "estimated_payments_under_different_name is yes — the former name the payments were "
            "made under is an identifier this schema cannot carry, and the return cannot be "
            "completed without it; refused rather than computed")
    if facts.get("estimated_payments_with_former_spouse") is True:
        raise ServiceFactsError(
            "estimated_payments_with_former_spouse is yes — the former spouse's taxpayer "
            "identification number is an identifier this schema cannot carry, and the return "
            "cannot be completed without it; refused rather than computed")


def student_loan_questions_reached(facts: dict) -> list:
    """the line 21 questions this return REACHES — the root question on every return; on a
    yes, whether the loans qualify and the interest paid. One predicate, four uses."""
    if not isinstance(facts, dict):
        return []
    reached = [STUDENT_LOAN_FIELD]
    if facts.get(STUDENT_LOAN_FIELD) is True:
        reached.extend(STUDENT_LOAN_REACHED_FIELDS)
        if facts.get("student_loans_qualify") is True:
            reached.extend(STUDENT_LOAN_NETTING_FIELDS)
    return reached


def refuse_misplaced_student_loan_answers(facts: dict) -> None:
    """an answer past the reach is refused by name; a reached one left unanswered is
    backstopped as a question, never defaulted (`gaps.gaps_for` asks first)."""
    reached = student_loan_questions_reached(facts)
    for field in sorted(STUDENT_LOAN_FIELDS):
        if field in facts and field not in reached:
            raise ServiceFactsError(
                f"{field} is answered but the student loan interest questions do not reach it "
                f"(whether the loans qualify and the interest paid are asked once "
                f"{STUDENT_LOAN_FIELD} is yes, and the employer-paid and qualified tuition "
                f"program amounts once student_loans_qualify is yes); refused rather than "
                f"dropped")
    for field in reached:
        if field not in facts:
            raise FactsSchemaError(
                f"{field} is a Schedule 1 line 21 question (student loan interest), asked on "
                f"every return that reaches it, not a default — answer it (prepare_return asks "
                f"it as a gap)")


def alimony_questions_reached(facts: dict) -> list:
    """the pre-2019-agreement gate each alimony amount reaches, once entered. Unlike student
    loan's single yes gating both follow-ups, each amount is its own independent, always-invited
    optional question (`ALIMONY_AMOUNT_FIELDS`, never a gap) — this reports only the two GATE
    fields the answered amounts reach, one per side."""
    if not isinstance(facts, dict):
        return []
    reached = []
    if ALIMONY_RECEIVED_AMOUNT_FIELD in facts:
        reached.append(ALIMONY_RECEIVED_GATE_FIELD)
    if ALIMONY_PAID_AMOUNT_FIELD in facts:
        reached.append(ALIMONY_PAID_GATE_FIELD)
        if facts.get(ALIMONY_PAID_GATE_FIELD) is True:
            reached.append(ALIMONY_PAID_TRUST_FIELD)
    return reached


def refuse_misplaced_alimony_answers(facts: dict) -> None:
    """a gate answered without its amount is refused by name (there is nothing for it to
    gate); a reached gate left unanswered is backstopped as a question, never defaulted as a $0
    the dictionary itself refuses to assert — `gaps.gaps_for` asks first."""
    reached = alimony_questions_reached(facts)
    for field in ALIMONY_GATE_FIELDS:
        if field in facts and field not in reached:
            raise ServiceFactsError(
                f"{field} is answered but it is asked only once "
                f"{ALIMONY_GATE_ASKED_ONCE[field]} — the gate has nothing to gate; refused "
                f"rather than dropped")
    for field in reached:
        if field not in facts:
            raise FactsSchemaError(
                f"{field} is asked once {ALIMONY_GATE_ASKED_ONCE[field]}, not a "
                f"default — answer it (prepare_return asks it as a gap)")


def refuse_missing_credit_history_answers(facts: dict) -> None:
    """Form 8862's three questions are asked on every return — an absent answer is
    backstopped as a question, never defaulted (`gaps.gaps_for` asks first)."""
    for field in CREDIT_HISTORY_FIELDS:
        if field not in facts:
            raise FactsSchemaError(
                f"{field} is a Form 8862 credit-history question, asked on every return, not a "
                f"default — answer it (prepare_return asks it as a gap)")


def refuse_missing_foreign_account_answers(facts: dict) -> None:
    """Schedule B Part III (lines 7a and 8) is asked on every return, three answers — an
    absent one is backstopped as a question, never defaulted (`gaps.gaps_for` asks first). Every
    status asks it, so no answer is ever misplaced."""
    for field in FOREIGN_ACCOUNT_FIELDS:
        if field not in facts:
            raise FactsSchemaError(
                f"{field} is a Schedule B Part III question (foreign accounts and trusts), asked "
                f"on every return, not a default — answer it (prepare_return asks it as a gap)")


def upkeep_question_armed(filing_status, person, facts=None) -> bool:
    """the rows the keeping-up-home answer belongs to. One predicate, three uses — the gap
    (`gaps.gaps_for`), the mapper backstop, and the refusal — so they cannot disagree about
    which row they are about.

    Two arms, both measured against the pinned dictionary:
      * hoh / qss — every claimed dependent row.
      * single — the rows the engine's own screen gate asks it of. That gate,
        `/familyAndHousehold/*/flowAddPersonKeepingUpHome`, is `/filerCouldQualifyForHoh` (or
        `/filerCouldQualifyForQss`) AND either the qualifying-CHILD relationship test, or the
        qualifying-RELATIVE one with the person in the home more than half the year. On an
        unmarried return `/filerCouldQualifyForHoh` is unconditionally true, so the gate reduces
        to its relationship arm, which is what this reads.

    Every other status is false. On a MARRIED return the gate's filer arm reaches
    `/eligibleForMFJ` / `/livedApartLastSixMonths` — the lived-together chain, which is asked,
    so the question is armed there exactly when that chain says the spouses lived apart the last
    six months (`facts` carries the chain's answers).

    TOTAL over a PARTIAL row: `gaps_for` runs before `relationship` and `months_in_home` are
    answered, and an unanswered qualifier leaves this question not-yet-armed — which asks those
    cheaper gaps first instead of inventing this one from a hole.
    """
    if not isinstance(person, dict) or person.get("role") != "dependent":
        return False
    if filing_status in ("hoh", "qss"):
        return True
    if filing_status in ("mfj", "mfs"):
        # on a married return the gate's filer arm is `/filerCouldQualifyForHoh` =
        # eligibleForMFJ AND livedApartLastSixMonths — true exactly when the lived-together
        # chain resolves "apart the last six months" (apart all year, or six months or less
        # together and apart the last six). Measured on the joint fixture, cell by cell.
        if lived_apart_last_six_months_resolved(facts) is not True:
            return False
    elif filing_status != "single":
        return False
    relationship = person.get("relationship")
    if relationship in _QC_RELATIONSHIP_TEST:
        return True
    return (relationship in _QR_RELATIONSHIP_TEST
            and dependent_residency_duration(person) in ("allYear", "sevenToElevenMonths"))

# the joint-return test, in the dictionary's own order. The links are
# (field, the answer to the PREVIOUS field that reaches it) — the root's own link is
# `is_married` true, which is the gate `dependent_joint_return_questions_reached` opens on.
# `/familyAndHousehold/*/jointReturnTest` is NOT married OR NOT jointReturn OR
# (filingOnlyForRefund AND NOT requiredToFile), so each answer that settles the test ends the
# chain: no joint return settles it PASSED, required-to-file settles it FAILED, and only a
# joint return the couple is not required to file still needs the refund-only answer. The
# dictionary agrees on the last one in its own words — `filingOnlyForRefund` reads
# `requiredToFile` and resolves false without its writable once that is complete and true
# ("We only ask either requiredToFile or filingOnlyForRefund").
DEPENDENT_JOINT_RETURN_CHAIN = (("files_joint_return_with_spouse", True),
                                ("required_to_file_with_spouse", True),
                                ("joint_return_only_for_refund", False))

# The engine path each link is sent as — the same three writables the register names.
DEPENDENT_JOINT_RETURN_EMISSION = {
    "files_joint_return_with_spouse": "writableJointReturn",
    "required_to_file_with_spouse": "writableRequiredToFile",
    "joint_return_only_for_refund": "writableFilingOnlyForRefund",
}


def dependent_joint_return_questions_reached(person) -> list:
    """the joint-return questions this ROW's answers so far REACH, in order — the first
    once the row is a dependent answered MARRIED, each later one only when the previous answer
    is the unlocking one.

    One predicate, four uses — the gap (`gaps.gaps_for`), the mapper backstop, the
    unreached-answer refusal and the emission — so they cannot disagree about which questions
    this row is being asked.

    TOTAL over a PARTIAL row: a row that has not answered `is_married` yet reaches nothing, so
    that cheaper gap is asked first instead of a chain being invented out of a hole. A filer
    row reaches nothing either — the joint-return test is a DEPENDENT's test, and the filer's
    own marital status is `filing_status`.
    """
    if not isinstance(person, dict) or person.get("role") != "dependent":
        return []
    if person.get("is_married") is not True:
        return []
    reached = [DEPENDENT_JOINT_RETURN_CHAIN[0][0]]
    prev = reached[0]
    for field, unlock in DEPENDENT_JOINT_RETURN_CHAIN[1:]:
        if person.get(prev) is unlock:
            reached.append(field)
            prev = field
        else:
            break
    return reached

# the benefit-split gate, in the dictionary's own order. The dictionary's
# `/familyAndHousehold/*/eligibleForBenefitSplit` is an All over five writable answers plus two
# derived ones (`childMayQualifyForBenefitSplit`, `tpIsParent`), so any single answer that fails
# closes the gate and the child is claimed under the ordinary rules — measured at the pin on
# every closing answer: every served line identical to the baseline to the cent.

# The links are (field, the answers to THAT field that keep the split ALIVE). Cheap gate first:
# `parents_situation` settles most rows with one answer, because the dictionary's
# `parentsAreDivorcedSeparatedOrLivingApart` is simply "not other".

# The population the parental arm can open on is the filer's own biological or adopted child and
# nothing else — MEASURED at the pin, not read off the field's name: `tpIsParent` is
# `biologicalChild` OR `adoptedChild`, so a stepchild, foster child or grandchild answered as
# having another legal parent resolves `tpIsNotParent` and belongs to the non-parental rule,
# which is refused by name.
_BENEFIT_SPLIT_PARENTAL_RELATIONSHIPS = frozenset({"biological_child", "adopted_child"})

DEPENDENT_BENEFIT_SPLIT_CHAIN = (
    ("parents_situation", ("divorced_or_separated", "lived_apart_last_six_months")),
    ("child_in_parents_custody", (True,)),
    ("child_lived_with_parents_over_half_year", (True,)),
    ("parents_provided_over_half_support", (True,)),
    # `i_did` and `they_did` open the custodial-parent questions — nights with the
    # filer vs the other parent, and only when nights are equal, whose AGI is higher
    # (`tpIsCustodialParent` = nights more, OR nights equal AND the filer's AGI higher).
    # `nobody_did` closes the gate. Every cell past here resolves at the pin: two compute (the
    # custodial parent who signed the declaration away keeps the EITC and loses the CTC), ten
    # knock out — the engine's own outcomes, served as such, never a refusal.
    ("written_declaration", ("i_did", "they_did")),
    ("nights_with_filer_vs_other_parent", ("equal",)),
    ("filer_agi_higher_than_other_parent", ()),
)

# The engine path each link is sent as — the writables the dictionary's gate reads.
DEPENDENT_BENEFIT_SPLIT_EMISSION = {
    "parents_situation": "parentalSituation",
    "child_in_parents_custody": "inParentsCustody",
    "child_lived_with_parents_over_half_year":
        "livedWithTpOrOtherBiologicalOrAdoptiveParentMoreThanSixMonths",
    "parents_provided_over_half_support": "parentalSupport",
    "written_declaration": "whichParentNotClaiming",
    "nights_with_filer_vs_other_parent": "nightsWithTpVsOtherParent",
    "filer_agi_higher_than_other_parent": "tpAgiHigherThanOtherParent",
}

# The two enums, in the pinned dictionary's own literals.
_PARENTS_SITUATION = {"divorced_or_separated": "divorcedOrSeparated",
                      "lived_apart_last_six_months": "livedApartLastSixMonths",
                      "other": "other"}
_WRITTEN_DECLARATION = {"i_did": "iDid", "they_did": "theyDid", "nobody_did": "nobodyDid"}
# the nights enum, `/moreLessEqualOptions` in the pinned constants.xml — the same words.
_NIGHTS = {"more": "more", "less": "less", "equal": "equal"}

# The qualifying-child relationships where the filer is NOT the child's parent — the
# dictionary's `tpIsNotParent` (= qcRelationshipTest AND NOT tpIsParent), DERIVED from the two
# sets above so it cannot drift from them, and mirrored cell by cell against the resolved graph
# by `NonParentDependentParentsLivingTest`. Twelve codes at the pin. On every one the claim
# chain waits on `biologicalOrAdoptiveParentsLiving` ("Are the dependent's biological or
# adoptive parents living?"): a NO claims the child under the ordinary rules (measured on all
# twelve: the baseline to the cent), a YES opens the non-parental split — its own questions,
# not asked — which is refused by name as the non-parental tier.
_NON_PARENT_QC_RELATIONSHIPS = _QC_RELATIONSHIP_TEST - _BENEFIT_SPLIT_PARENTAL_RELATIONSHIPS



# The pinned dictionary's `/taxYear` constant — the year the ENGINE ages a dependent against
# (`age` = /taxYear − birth year), whatever `tax_year` a request carries. The age-at-July-2 leg
# below mirrors the engine, so it reads this and not the request.
_PINNED_TAX_YEAR = 2025


def child_may_qualify_for_split(person) -> bool:
    """the dictionary's `childMayQualifyForBenefitSplit` on what the service SENDS — whether the
    child can still be in a parent's custody for the rule for children of divorced or separated
    parents. Three arms, any one opens it:
      * disabled: `disabilityStatusMayAffectBenefits` (age on July 2 of 18 or more, here) and
        permanently and totally disabled;
      * young: `age` (the tax year less the birth year — no month) under 18, or under the age of
        majority of the state the child lived in (`ageOfMajorityForCustodyTest`);
      * of age but not emancipated: at or over that age of majority and answered not emancipated,
        or emancipated after July 2.
    An emancipation answered yes with a date on or before July 2 closes every arm. The state and
    emancipation answers are `child_custody_questions_reached`'s — the same answers the mapper
    emits — so an answer off that chain (refused by name) is never read here. Mirrored cell by
    cell by `SplitAgeLegTest`. TOTAL over a PARTIAL row: an unanswered birth year, state or
    emancipation answer the engine needs is not armed (the engine leaves the fact Incomplete) —
    those cheaper gaps are asked first.

    One leg is read wider than the engine: the disabled arm's "born before the oldest filer"
    branch of `disabilityStatusMayAffectBenefits` is not read (it needs the filer rows), so such a
    dependent — 17 on July 2 and older than every filer — is asked the state question the engine
    could do without; once it is answered both agree."""
    if not isinstance(person, dict) or person.get("role") != "dependent":
        return False
    age = _age_at_year_end(person)
    if age is None:
        return False
    reached = child_custody_questions_reached(person)
    emancipated = person.get(EMANCIPATED_FIELD) if EMANCIPATED_FIELD in reached else None
    if emancipated is True and person.get(EMANCIPATED_AFTER_MIDYEAR_FIELD) is not True:
        return False                  # on or before July 2 closes every arm; unanswered: Incomplete
    if _disabled_arm_holds(person):
        return True
    if age < CUSTODY_AGE_OF_MAJORITY_FLOOR:
        return True
    majority = _age_of_majority(person) if CHILD_STATE_FIELD in reached else None
    if majority is None:
        return False                  # the state is unanswered: Incomplete
    if age < majority:
        return True
    return emancipated is not None    # not emancipated, or emancipated after July 2


def _age_at_year_end(person) -> int | None:
    """the dictionary's `/familyAndHousehold/*/age` — the pinned tax year less the birth year (the
    month does not enter). None without a `birth_year`."""
    year = person.get("birth_year")
    if not isinstance(year, int) or isinstance(year, bool):
        return None
    return _PINNED_TAX_YEAR - year


def _disabled_arm_holds(person) -> bool:
    """the split gate's disabled arm on what the service sends: 18 or more on July 2 (the
    age leg of `disabilityStatusMayAffectBenefits`) and answered permanently and totally
    disabled."""
    age = _age_at_july_2(person)
    return age is not None and age >= 18 and person.get(DISABILITY_FIELD) is True


# The custody questions the split gate asks at this pin (`dependentsBenefitSplit.xml`): the state
# or territory the child lived in (`writableChildResidenceJurisdiction`), whether the child was
# emancipated under that state's law (`writableChildEmancipatedUnderStateLaw`), and on a yes
# whether that was after July 2 (the one thing the engine reads from
# `writableChildEmancipationDate`, through `childEmancipationDateAfterCustodyMidyear`).
CHILD_STATE_FIELD = "child_residence_state"
EMANCIPATED_FIELD = "child_emancipated"
EMANCIPATED_AFTER_MIDYEAR_FIELD = "child_emancipated_after_july_2"
CHILD_CUSTODY_FIELDS = (CHILD_STATE_FIELD, EMANCIPATED_FIELD, EMANCIPATED_AFTER_MIDYEAR_FIELD)
# the dictionary's `/childResidenceJurisdictionOptions`, in its order: the 50 states and DC (the
# `/scopedStateOptions` codes), five territories, and outside the United States.
CHILD_RESIDENCE_STATES = (
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "dc", "fl", "ga", "hi", "id", "il", "in",
    "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh",
    "nj", "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut",
    "vt", "va", "wa", "wv", "wi", "wy", "pr", "gu", "vi", "as", "mp", "outsideUnitedStates")
# `ageOfMajorityForCustodyTest`: 19 in Alabama and Nebraska, 21 in Mississippi and Puerto Rico,
# 18 for every other answer — and 18 is the floor below which no state is asked.
CUSTODY_AGE_OF_MAJORITY_FLOOR = 18
_CUSTODY_AGE_OF_MAJORITY = {"al": 19, "ne": 19, "ms": 21, "pr": 21}
# `writableChildEmancipationDate` is a Day; the engine reads only which side of July 2 it falls
# on, so the answer is sent as a synthesized day on that side (the synthesized-day convention).
_EMANCIPATION_DAY = {True: f"{_PINNED_TAX_YEAR}-12-31", False: f"{_PINNED_TAX_YEAR}-07-02"}


def _age_of_majority(person) -> int | None:
    state = person.get(CHILD_STATE_FIELD)
    if state not in CHILD_RESIDENCE_STATES:
        return None
    return _CUSTODY_AGE_OF_MAJORITY.get(state, CUSTODY_AGE_OF_MAJORITY_FLOOR)


def child_custody_questions_reached(person) -> list:
    """the custody questions this ROW's answers so far REACH, in order. One predicate, four uses
    — the gap (`gaps.gaps_for`), the mapper backstop, the unreached-answer refusal and the
    emission — the `disability_question_armed` shape.

    Asked on a claimed dependent with a qualifying-child relationship (the only rows where a
    reader of `childMayQualifyForBenefitSplit` can turn on it) who is 18 or older at the end of
    the year, unless the disabled arm already opens the split: first the state; then, once the
    child is at or over that state's age of majority, whether the child was emancipated; on a
    yes, whether that was after July 2. TOTAL over a PARTIAL row: no `relationship` or
    `birth_year` yet, or a disability question asked and unanswered, reaches nothing, so those
    cheaper gaps are asked first."""
    if not isinstance(person, dict) or person.get("role") != "dependent":
        return []
    if person.get("relationship") not in _QC_RELATIONSHIP_TEST:
        return []
    age = _age_at_year_end(person)
    if age is None or age < CUSTODY_AGE_OF_MAJORITY_FLOOR:
        return []
    july_2 = _age_at_july_2(person)
    if july_2 is not None and july_2 >= 18 and DISABILITY_FIELD not in person:
        return []                     # the disability question first
    if _disabled_arm_holds(person):
        return []
    reached = [CHILD_STATE_FIELD]
    majority = _age_of_majority(person)
    if majority is None or age < majority:
        return reached
    reached.append(EMANCIPATED_FIELD)
    if person.get(EMANCIPATED_FIELD) is True:
        reached.append(EMANCIPATED_AFTER_MIDYEAR_FIELD)
    return reached


# The member-of-household route of the qualifying-relative relationship test
# (`/familyAndHousehold/*/memberOfHouseholdTest`, IRC 152(d)(2)(H) and 152(f)(3)): a person not
# related to the filer in a listed way qualifies by living with the filer all year, if they were
# not the filer's spouse at any time in the year (`writableWasSpouseAtAnyTimeInTaxYear`) and the
# relationship did not violate local law (`writableCdccRelationshipViolatesLocalLaw`). The test
# reads both answers bare, so unanswered they leave the dependent's eligibility Incomplete. The
# local-law answer has a second reader: `cdccQualifyingPerson` (IRC 21(e)(1)), which reads it
# IsComplete-first on a person who could qualify the filer for the credit when the return claims
# care expenses. One question per person, whichever reader reaches it.
WAS_SPOUSE_FIELD = "was_spouse_during_year"
LOCAL_LAW_FIELD = "relationship_violates_local_law"
HOUSEHOLD_MEMBER_FIELDS = (WAS_SPOUSE_FIELD, LOCAL_LAW_FIELD)
HOUSEHOLD_MEMBER_EMISSION = {
    WAS_SPOUSE_FIELD: "writableWasSpouseAtAnyTimeInTaxYear",
    LOCAL_LAW_FIELD: "writableCdccRelationshipViolatesLocalLaw",
}


def household_member_route_reached(person) -> bool:
    """the dictionary's ASKED WHEN for the member-of-household route, on what the service sends:
    a claimed dependent whose relationship fails the qualifying-relative relationship list
    (`_QR_RELATIONSHIP_TEST`, the dictionary's `qrRelationshipTest`) and who lived with the
    filer all year (`months_in_home` 12, sent as `residencyDuration` allYear — the encoding the
    schema gives a child born or a person who died during the year too). The route's born-or-died
    arm (`qssBornOrDiedResidencyException`) is complete-safe false here: the service never sends
    its entire-time answer. TOTAL over a PARTIAL row: no `relationship` or `months_in_home` yet
    reaches nothing, so those cheaper gaps are asked first."""
    if not isinstance(person, dict) or person.get("role") != "dependent":
        return False
    relationship = person.get("relationship")
    if relationship not in _RELATIONSHIP or relationship in _QR_RELATIONSHIP_TEST:
        return False
    return dependent_residency_duration(person) == "allYear"


def household_member_questions_reached(facts, person_index: int, tax_year: int = 2025) -> list:
    """the member-of-household questions this ROW reaches, in order. One predicate, four uses —
    the gap (`gaps.gaps_for`), the mapper backstop, the unreached-answer refusal and the emission
    — the `child_custody_questions_reached` shape.

      * the member-of-household route (`household_member_route_reached`): both questions;
      * otherwise a claimed dependent who is a Form 2441 qualifying person on what the service
        sends (`care_expense_question_reached`) on a return that claims care expenses (some row's
        `care_expenses_cents` above 0): the local-law question alone, the credit's own reader.
    """
    if not isinstance(facts, dict):
        return []
    persons = facts.get("persons") or []
    if not 0 <= person_index < len(persons):
        return []
    person = persons[person_index]
    if household_member_route_reached(person):
        return list(HOUSEHOLD_MEMBER_FIELDS)
    if (isinstance(person, dict) and person.get("role") == "dependent"
            and care_expense_question_reached(facts, person_index, tax_year)
            and care_expenses_entered(facts) > 0):
        return [LOCAL_LAW_FIELD]
    return []


def refuse_misplaced_household_member_answers(facts: dict, tax_year: int = 2025) -> None:
    """the member-of-household questions: an answer the row does not reach is refused by name
    (on any row), and a reached question left unanswered is backstopped by name."""
    persons = facts.get("persons") or []
    for i, person in enumerate(persons):
        if not isinstance(person, dict):
            continue
        reached = household_member_questions_reached(facts, i, tax_year)
        for field in HOUSEHOLD_MEMBER_FIELDS:
            if field not in person or field in reached:
                continue
            if person.get("role") != "dependent":
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered on a filer row — it is asked about a "
                    f"claimed dependent only; refused rather than dropped")
            raise ServiceFactsError(
                f"persons[{i}].{field} is answered, and the engine does not ask it for this "
                f"person with the answers given: whether the person was the filer's spouse at "
                f"any time in the year, and whether the relationship violated local law, are "
                f"asked of a claimed dependent not related to the filer in one of the listed "
                f"ways who lived with the filer all year; the local-law question also of a "
                f"Form 2441 qualifying person on a return that claims care expenses; refused "
                f"rather than dropped")
    for i, person in enumerate(persons):
        for field in household_member_questions_reached(facts, i, tax_year):
            if field not in person:
                raise FactsSchemaError(
                    f"persons[{i}].{field} is a question on this dependent row — the "
                    f"qualifying-relative household test or Form 2441's qualifying-person test "
                    f"reads it — not a default; answer it (prepare_return asks it as a gap)")


def _household_member_section(f: dict, facts: dict, tax_year: int) -> None:
    """the member-of-household answers, exactly as far as each row reaches."""
    for i, person in enumerate(facts.get("persons") or []):
        for field in household_member_questions_reached(facts, i, tax_year):
            if field in person:
                f[f"/familyAndHousehold/#{_uuid('2', i + 1)}/"
                  f"{HOUSEHOLD_MEMBER_EMISSION[field]}"] = _bool(person[field])


def _age_at_july_2(person) -> int | None:
    """the dictionary's `ageAtFirstHalfOfYear` on what the service SENDS — age at year end,
    less one when born after July (the day synthesized as the 1st, so a July birth reads as on
    or before July 2), against the pinned tax year. None without a `birth_year`. One function,
    so the split's age leg and the disability question's arming cannot drift apart."""
    year = person.get("birth_year")
    if not isinstance(year, int) or isinstance(year, bool):
        return None
    month = person.get("birth_month", DEFAULT_BIRTH_MONTH)
    if not isinstance(month, int) or isinstance(month, bool):
        month = DEFAULT_BIRTH_MONTH
    age_at_year_end = _PINNED_TAX_YEAR - year
    return age_at_year_end - 1 if month > 7 else age_at_year_end


# "Is the dependent permanently and totally disabled?" — the dictionary's
# `/familyAndHousehold/*/permanentTotalDisability`. The engine reads it only together with
# `disabilityStatusMayAffectBenefits` (its own ask gate): in the qualifying-child `ageTest` and the
# EIC's `eicAgeTest` (IRC 152(c)(3)(B): disabled, any age), and in
# `childMayQualifyForBenefitSplit`. All three sit behind the qualifying-child relationship test.
DISABILITY_FIELD = "is_permanently_disabled"


def _oldest_filer_birth(facts) -> tuple | None:
    """the dictionary's `/minimumFilerDateOfBirth` as (year, month): the older filer's on a
    joint return, the primary filer's otherwise. None while the primary's `birth_year` is
    unanswered (that cheaper gap is asked first)."""
    if not isinstance(facts, dict):
        return None
    persons = [p for p in facts.get("persons") or [] if isinstance(p, dict)]
    roles = ("primary", "spouse") if facts.get("filing_status") == "mfj" else ("primary",)
    births = {p.get("role"): _birth_year_month(p) for p in persons if p.get("role") in roles}
    if births.get("primary", (None, None))[0] is None:
        return None
    return min(b for b in births.values() if b[0] is not None)


def disability_question_armed(person, facts=None) -> bool:
    """whether this row is asked whether the dependent is permanently and totally disabled.
    One predicate, two uses — the gap (`gaps.gaps_for`) and the mapper backstop; an answer on a
    row it does not arm is accepted unasked and emitted as before.

    Mirrors the dictionary's `disabilityStatusMayAffectBenefits` — `ageAtFirstHalfOfYear` 18 or
    more, OR under 18 and born before `/minimumFilerDateOfBirth` (older than the filer, so the
    age arm's "younger than the filer" leg fails) — on a qualifying-child relationship
    (`_QC_RELATIONSHIP_TEST`), the only rows where any reader of the answer can turn on it. The
    service carries no birth day: a dependent born in the same month as the oldest filer is
    asked (the day would decide). TOTAL over a PARTIAL row: no `relationship` or `birth_year`
    yet means not armed, so those cheaper gaps are asked first."""
    if not isinstance(person, dict) or person.get("role") != "dependent":
        return False
    if person.get("relationship") not in _QC_RELATIONSHIP_TEST:
        return False
    age = _age_at_july_2(person)
    if age is None:
        return False
    if age >= 18:
        return True
    oldest = _oldest_filer_birth(facts)
    return oldest is not None and _birth_year_month(person) <= oldest


def other_parent_question_armed(person) -> bool:
    """whether this row is asked whether the child has another living biological or
    adoptive parent. The pinned dictionary reads that answer in exactly one place —
    `eligibleForBenefitSplit`'s parental arm, which also requires `tpIsParent` — so it is asked
    on the split population only (`_BENEFIT_SPLIT_PARENTAL_RELATIONSHIPS`, one source) and is an
    unasked answer everywhere else. It was once asked on every child-category row and a
    stepchild's answer, which the engine never read, was what a refusal turned on."""
    return (isinstance(person, dict) and person.get("role") == "dependent"
            and person.get("relationship") in _BENEFIT_SPLIT_PARENTAL_RELATIONSHIPS
            and child_may_qualify_for_split(person))


def parents_living_question_armed(person) -> bool:
    """whether this row is asked whether the child's own parents are living. One
    predicate, three uses — the gap (`gaps.gaps_for`), the mapper backstop and the refusals —
    the same shape. TOTAL over a PARTIAL row: no `relationship` yet means not armed, so that
    cheaper gap is asked first."""
    # the same age/disability leg the other-parent question has — measured: an
    # 18-year-old stepchild's claim resolves WITHOUT this answer (`reachedNonParentalBenefitSplit`
    # is false once `childMayQualifyForBenefitSplit` is), so asking it there is asking a question
    # the engine ignores.
    return (isinstance(person, dict) and person.get("role") == "dependent"
            and person.get("relationship") in _NON_PARENT_QC_RELATIONSHIPS
            and child_may_qualify_for_split(person))


# The non-parental split — the tier behind a YES to "are the child's own parents living?" on
# a row where the filer is not the parent — in the dictionary's order: `reachedNonParentalBenefitSplit`
# = childMayQualifyForBenefitSplit AND tpIsNotParent AND parentsLiving AND inParentsCustody AND
# nonParentalSomeParentNotClaiming AND parentsMeetReqsRuleForChildrenOfDivorcedParents; then
# `disqualifiedDueToParentalCustody` = reached AND (NOT specialRuleAgiTest OR
# specialRuleChildUsedByCustodialParentAsQP). Any "no" on the first three claims the child under
# the ordinary rules; the deep cells either disqualify the child or give the filer the split's
# benefits without the dependency claim — every cell computed, none refused, none knocked out.
DEPENDENT_NONPARENTAL_SPLIT_CHAIN = (
    ("parents_meet_divorced_or_separated_rule", (True,)),
    ("a_parent_signed_declaration_not_to_claim", (True,)),
    ("child_in_parents_custody", (True,)),                       # the split gate's field, this row
    ("custodial_parent_claims_child_as_qualifying_person", (False,)),
    ("filer_agi_higher_than_custodial_parent", ()),
)
DEPENDENT_NONPARENTAL_SPLIT_EMISSION = {
    "parents_meet_divorced_or_separated_rule": "parentsMeetReqsRuleForChildrenOfDivorcedParents",
    "a_parent_signed_declaration_not_to_claim": "nonParentalSomeParentNotClaiming",
    "child_in_parents_custody": "inParentsCustody",
    "custodial_parent_claims_child_as_qualifying_person": "specialRuleChildUsedByCustodialParentAsQP",
    "filer_agi_higher_than_custodial_parent": "specialRuleAgiTest",
}


def dependent_nonparental_split_questions_reached(person) -> list:
    """the non-parental split questions this ROW's answers so far REACH, in order — the
    first once a non-parent child the engine can split is answered as having living parents,
    each later one only while the answers keep the split alive. One predicate, four uses (the
    gap, the statement surface, the backstop + unreached refusal, the emission)."""
    if not parents_living_question_armed(person):            # carries the age leg
        return []
    if person.get("child_parents_living") is not True:
        return []
    reached = [DEPENDENT_NONPARENTAL_SPLIT_CHAIN[0][0]]
    prev, prev_alive = DEPENDENT_NONPARENTAL_SPLIT_CHAIN[0]
    for field, alive in DEPENDENT_NONPARENTAL_SPLIT_CHAIN[1:]:
        if not _split_link_alive(person.get(prev), prev_alive):
            break
        reached.append(field)
        prev, prev_alive = field, alive
    return reached


def _split_link_alive(answer, alive) -> bool:
    """True when THIS link's answer keeps the split alive, so the next link is reached.

    Identity for the Booleans (`1 is not True`, and a mistyped answer must not unlock a
    question), equality for the situation enum's strings."""
    return any(answer is a or (isinstance(a, str) and answer == a) for a in alive)


def dependent_benefit_split_questions_reached(person) -> list:
    """the benefit-split questions this ROW's answers so far REACH, in order — the first
    once the row is the filer's own biological or adopted child answered as having ANOTHER
    legal parent, each later one only while the answers so far keep the split alive.

    One predicate, four uses — the gap (`gaps.gaps_for`), the mapper backstop, the
    unreached-answer refusal and the emission — so they cannot disagree about which questions
    this row is being asked.

    TOTAL over a PARTIAL row: a row that has not answered the other-parent question yet
    reaches nothing, so that cheaper gap is asked first instead of a chain being invented out
    of a hole. A filer row reaches nothing either — the split is a question about a CLAIMED
    child, and a stepchild, foster child or grandchild row reaches nothing because the filer
    is not that child's parent (such a row is asked the non-parental arm's own first question
    instead; with another legal parent answered it is the non-parental tier, refused by name).
    """
    if not isinstance(person, dict) or person.get("role") != "dependent":
        return []
    if not other_parent_question_armed(person):                          # one gate
        return []
    if person.get("has_other_biological_or_adoptive_parent") is not True:
        return []
    reached = [DEPENDENT_BENEFIT_SPLIT_CHAIN[0][0]]
    prev, prev_alive = DEPENDENT_BENEFIT_SPLIT_CHAIN[0]
    for field, alive in DEPENDENT_BENEFIT_SPLIT_CHAIN[1:]:
        if not _split_link_alive(person.get(prev), prev_alive):
            break
        reached.append(field)
        prev, prev_alive = field, alive
    return reached


# The dependent tinType literals, from the pinned /tinTypeOptions.
_DEP_TIN_TYPE = {"ssn_valid_for_employment": "ssn", "ssn_other": "ssn",
                 "ssn_dhs_authorization": "ssn", "ssn_dhs_authorization_expired": "ssn",
                 "itin": "itin", "atin": "atin", "none": "none"}
# A card that reads "Valid for work only with DHS authorization": the dependent list spells the
# in-effect arm `...InEffect`, the filer list (`_VALIDITY` below) does not.
_DEP_SSN_VALIDITY = {"ssn_valid_for_employment": "neither", "ssn_other": "notValid",
                     "ssn_dhs_authorization": "validOnlyWithDhsAuthorizationInEffect",
                     "ssn_dhs_authorization_expired": "validOnlyWithDhsAuthorizationExpired"}


def _dependent(f: dict, cid: str, person: dict, person_index: int, tax_year: int,
               birth_days: dict | None = None) -> None:
    """One claimed dependent -> a `/familyAndHousehold` item.

    The engine models the WHOLE §152 test battery; this mapper supplies the filer's own answers
    (the seven asked qualifiers — `gaps.gaps_for` asks them, the guard refuses a hole) and the
    same stated assumptions the filers get. Measured at the pin, end to end: a qualifying child
    computes the 2,200 CTC, a qualifying relative the 500 ODC, the refundable ACTC reaches
    line 33, and a battery the answers do not satisfy computes NO credit — the engine's own
    tests decide, never this mapper.
      * `tpClaims` is TRUE by the row's meaning: a `dependent` row on this return IS the claim
        (hoh/qss may later need non-claimed household members; that semantic is noted in the
        register disposition, not smuggled in here).
      * The synthetic TIN is SSN-SHAPED but impossible (area 899 group 00 — never issued), and
        per-person, because eligibility requires TIN uniqueness. See _SYNTH_TIN.
      * The day of birth is synthesized (day 01) exactly as for filers — measured across twelve
        January birth years: no served line moves between day 01 and day 15 at this pin (the
        born-on-Jan-1 chain feeds EITC/CDCC, both uncovered); DayInvarianceTest carries the
        cohort.
    """
    b = f"/familyAndHousehold/#{cid}"
    f[f"{b}/dateOfBirth"] = _day(_date_of_birth(person, person_index, birth_days))
    f[f"{b}/tin"] = _synth_tin(person["tin_type"], person_index)
    f[f"{b}/tinType"] = _enum("/tinTypeOptions", _DEP_TIN_TYPE[person["tin_type"]])
    if person["tin_type"] in _DEP_SSN_VALIDITY:
        f[f"{b}/ssnEmploymentValidity"] = _enum(
            "/familyAndHouseholdSsnEmploymentValidityOptions",
            _DEP_SSN_VALIDITY[person["tin_type"]])
    category, specific_fact, literal = _RELATIONSHIP[person["relationship"]]
    f[f"{b}/relationshipCategory"] = _enum("/relationshipCategoryOptions", category)
    if specific_fact:
        f[f"{b}/{specific_fact}"] = _enum(f"/{specific_fact}Options", literal)
    duration = dependent_residency_duration(person)
    f[f"{b}/residencyDuration"] = _enum("/residencyDurationOptions", duration)
    if duration in ("allYear", "sevenToElevenMonths"):    # the residency test passed
        f[f"{b}/monthsLivedWithTPInUS"] = _enum("/monthsLivedWithTPInUSOptions",
                                                _MONTH_WORDS[person["months_in_home"]])
    f[f"{b}/married"] = _bool(person["is_married"])
    # the non-parental arm's first question, on the rows the dictionary asks it of. Only a
    # NO ever reaches here — a YES is refused by name before emission (the non-parental tier).
    if parents_living_question_armed(person) and "child_parents_living" in person:
        f[f"{b}/biologicalOrAdoptiveParentsLiving"] = _bool(person["child_parents_living"])
    # the non-parental split's writables, exactly as far as the chain reaches.
    for field in dependent_nonparental_split_questions_reached(person):
        if field in person:
            f[f"{b}/{DEPENDENT_NONPARENTAL_SPLIT_EMISSION[field]}"] = _bool(person[field])
    # the joint-return test's three writables, sent exactly as far as the chain reaches
    # and no further. Same function as the ask, the backstop and the refusal read, so an
    # answer that was refused as unreached can never arrive here anyway. On an UNMARRIED row
    # none of the three is sent: `married` false short-circuits every one of the derived
    # facts, and measured at the pin the served lines are identical to the cent whether the
    # two old attestations ride along or not.
    for field in dependent_joint_return_questions_reached(person):
        f[f"{b}/{DEPENDENT_JOINT_RETURN_EMISSION[field]}"] = _bool(person[field])
    f[f"{b}/ownSupport"] = _bool(person["provided_own_support"])
    f[f"{b}/grossIncomeTest"] = _bool(person["gross_income_under_limit"])
    f[f"{b}/writableQrSupportTest"] = _bool(person["filer_provided_over_half_support"])
    f[f"{b}/writableCouldBeQualifyingChildOfAnother"] = _bool(
        person["could_be_qualifying_child_of_another"])
    # the split gate's custody questions, exactly as far as the chain reaches.
    for field in child_custody_questions_reached(person):
        if field not in person:
            continue
        if field == CHILD_STATE_FIELD:
            f[f"{b}/writableChildResidenceJurisdiction"] = _enum(
                "/childResidenceJurisdictionOptions", person[field])
        elif field == EMANCIPATED_FIELD:
            f[f"{b}/writableChildEmancipatedUnderStateLaw"] = _bool(person[field])
        else:
            f[f"{b}/writableChildEmancipationDate"] = _day(_EMANCIPATION_DAY[person[field]])
    if other_parent_question_armed(person):
        f[f"{b}/hasOtherBiologicalOrAdoptiveParent"] = _bool(
            person["has_other_biological_or_adoptive_parent"])
    # the benefit-split gate's five writables, sent exactly as far as the chain reaches
    # and no further. Same function as the ask, the backstop and the refusal read, so an answer
    # that was refused as unreached can never arrive here anyway. On a row that answered NO to
    # the other-parent question none of the five is sent — the gate's own
    # `hasOtherBiologicalOrAdoptiveParent` leg is already false.
    for field in dependent_benefit_split_questions_reached(person):
        path = f"{b}/{DEPENDENT_BENEFIT_SPLIT_EMISSION[field]}"
        if field == "parents_situation":
            f[path] = _enum("/parentalSituationOptions", _PARENTS_SITUATION[person[field]])
        elif field == "written_declaration":
            f[path] = _enum("/writtenDeclarationOptions", _WRITTEN_DECLARATION[person[field]])
        elif field == "nights_with_filer_vs_other_parent":
            f[path] = _enum("/moreLessEqualOptions", _NIGHTS[person[field]])
        else:
            f[path] = _bool(person[field])
    f[f"{b}/fullTimeStudent"] = _bool(bool(person.get("is_student", False)))
    f[f"{b}/permanentTotalDisability"] = _bool(
        bool(person.get("is_permanently_disabled", False)))
    if "filer_paid_most_of_home_upkeep" in person:
        f[f"{b}/tpPaidMostOfHomeUpkeep"] = _bool(person["filer_paid_most_of_home_upkeep"])
    f[f"{b}/tpClaims"] = _bool(True)
    # The same stated assumptions the filers get, per dependent:
    f[f"{b}/isUsCitizenFullYear"] = _bool(True)
    f[f"{b}/deceased"] = _bool(False)
    # asked on the row (Form 2441's other qualifying-person arm); absent is no.
    f[f"{b}/unableToCareForSelf"] = _bool(person.get(UNABLE_TO_CARE_FIELD) is True)
    f[f"{b}/hasIpPin"] = _bool(False)


def _filer(f: dict, cid: str, person: dict, primary: bool, person_index: int = 0,
           birth_days: dict | None = None) -> None:
    # Every filer (primary AND spouse) needs full identity + status writables — the standard
    # deduction depends on both spouses' age/blindness, so a bare spouse leaves the return unresolved.
    base = f"/filers/#{cid}"
    f[f"{base}/isPrimaryFiler"] = _bool(primary)
    f[f"{base}/dateOfBirth"] = _day(_date_of_birth(person, person_index, birth_days))
    f[f"{base}/tin"] = _synth_tin(person["tin_type"], person_index)
    # the page-1 "someone can claim you" answer, never an attestation (it was `False` here
    # once); the chain's links follow it on the primary row, as far as reached.
    f[f"{base}/canBeClaimed"] = _bool(person["someone_can_claim_you"])
    for field in claim_me_questions_reached(person)[1:]:
        if field in person and field in CLAIM_ME_EMISSION:
            f[f"{base}/{CLAIM_ME_EMISSION[field]}"] = _bool(person[field])
    if primary and "potential_claimer_filed_only_for_refund" in claim_me_questions_reached(person) \
            and "potential_claimer_filed_only_for_refund" in person:
        f["/primaryFilerPotentialClaimerFiledOnlyForRefund"] = _bool(
            person["potential_claimer_filed_only_for_refund"])
    # the filer's own answer to line 12's checkbox, never an attestation. The caller is
    # backstopped for it above, so reading the key directly is what keeps the two in step.
    f[f"{base}/isBlind"] = _bool(person["is_blind"])
    # this filer's educator expenses, on the dictionary's writable for this filer, once
    # the row answers yes (the backstop guarantees the amount is there behind a yes).
    if person.get(EDUCATOR_FIELD) is True:
        f["/primaryEducatorExpensesWritable" if primary else
          "/secondaryEducatorExpensesWritable"] = _dollar(person[EDUCATOR_AMOUNT_FIELD])
    # this filer's traditional IRA contributions and inherited-IRA answer, on the
    # dictionary's writables for this filer, once the row answers yes (the backstop guarantees
    # both are there behind a yes).
    if person.get(IRA_FIELD) is True:
        f[IRA_EMISSION[primary][IRA_AMOUNT_FIELD]] = _dollar(person[IRA_AMOUNT_FIELD])
        f[IRA_EMISSION[primary][IRA_INHERITED_FIELD]] = _bool(person[IRA_INHERITED_FIELD])
        if person[IRA_INHERITED_FIELD] is True:
            f[IRA_EMISSION[primary][IRA_INHERITED_AMOUNT_FIELD]] = _dollar(
                person[IRA_INHERITED_AMOUNT_FIELD])
    f[f"{base}/isDisabled"] = _bool(bool(person.get("is_permanently_disabled", False)))
    f[f"{base}/isStudent"] = _bool(bool(person.get("is_student", False)))
    f[f"{base}/isUsCitizenFullYear"] = _bool(True)


def _w2(f: dict, cid: str, filer_cid: str, w2: dict, employer_ordinal: int = 0) -> None:
    b = f"/formW2s/#{cid}"
    # NOT `.get(..., 0)`. `wages_cents` is schema-required and `_refuse_missing_or_mistyped` has
    # already enforced it, so reading it directly is what keeps the two in step: if the requirement
    # is ever relaxed, this raises loudly instead of quietly resuming the $0.00 default (work item
    # 0b, the design's worked example of a silently wrong `complete`).
    wages = w2["wages_cents"]
    f[f"{b}/filer"] = _collection_item(filer_cid)
    f[f"{b}/writableWages"] = _dollar(wages)
    f[f"{b}/writableFederalWithholding"] = _dollar(w2.get("withholding_cents", 0))
    f[f"{b}/writableOasdiWages"] = _dollar(w2.get("social_security_wages_cents", wages))
    f[f"{b}/writableMedicareWages"] = _dollar(w2.get("medicare_wages_cents", wages))
    if W2_BOX10_FIELD in w2:                                              # box 10
        f[f"{b}/writableDependentCareBenefits"] = _dollar(w2[W2_BOX10_FIELD])
    for field in W2_BOX12_EMITTED:                                        # box 12
        if field in w2:
            f[f"{b}/{W2_BOX12_BY_FIELD[field][1]}"] = _dollar(w2[field])
    if W2_BOX12_G_PLAN_FIELD in w2:                                       # code G's plan
        f[f"{b}/457bIsGovernmentalPlan"] = _bool(w2[W2_BOX12_G_PLAN_FIELD])
    # Employer identity is SYNTHESIZED from the dense ordinal, never received. The dictionary's
    # multi-employer test groups on the EIN, so THAT is what must vary; the name stays constant so no
    # caller-supplied number ends up inside a string that is exported (`/formW2s/*/ein` carries
    # mef="true"). Prefix 00 is unassigned — it cannot collide with a real EIN, the same convention
    # as the 900-range synthetic TINs.
    f[f"{b}/employerName"] = _str("Synthetic Employer")
    f[f"{b}/ein"] = _ein("00", f"{employer_ordinal:07d}")
    if "social_security_withheld_cents" in w2:
        f[f"{b}/writableOasdiWithholding"] = _dollar(w2["social_security_withheld_cents"])
    if "medicare_withheld_cents" in w2:                                    # box 6
        f[f"{b}/writableMedicareWithholding"] = _dollar(w2["medicare_withheld_cents"])
    # box 13's three checkboxes and box 14's RRTA question are the caller's answers
    # (backstopped by `refuse_missing_w2_asked_answers`, so reading the keys directly keeps the
    # two in step).
    for field, leaf in W2_ASKED_EMISSION.items():
        f[f"{b}/{leaf}"] = _bool(w2[field])
    f[f"{b}/nonstandardOrCorrectedChoice"] = _enum("/w2NonstandardCorrectedOptions", "neither")
    f[f"{b}/writableState"] = _enum("/incomeFormStateOptions", "sameState")


# Used where a served line turns on it (2026-09-22): the person's exact BIRTH DAY, from
# the page's own store on their own computer, keyed by the person's index in `persons`. It is NOT a
# fact field and no published contract knows it (`test_schema.FORBIDDEN_FACT_PROPERTIES` still
# forbids the property name outright, so no birth day can be sent to this service over the wire);
# it reaches here only through the in-process seam the typed lines use. Absent — every
# caller but the local page — the day is synthesized 01 exactly as before, and the two day-ambiguous
# cohorts below are refused exactly as before.
def validate_birth_days(persons: list, birth_days) -> dict:
    """`{person index: day}`, refused BY NAME as a whole when any entry is not a real day of that
    person's own birth month. Returns {} for None, which is every caller that does not hold days."""
    import datetime
    if not birth_days:
        return {}
    if not isinstance(birth_days, dict):
        raise ServiceFactsError("the birth days must be given as a person's number and their day")
    out = {}
    for key, day in birth_days.items():
        try:
            index = int(key)
        except (TypeError, ValueError):
            raise ServiceFactsError(f"{key!r} is not a person's number on this return")
        if not 0 <= index < len(persons):
            raise ServiceFactsError(
                f"a birth day was given for person {index + 1}, who is not on this return")
        if isinstance(day, bool) or not isinstance(day, int):
            raise ServiceFactsError(f"persons[{index}]'s birth day must be a whole number, got {day!r}")
        person = persons[index]
        month = person.get("birth_month", DEFAULT_BIRTH_MONTH)
        try:
            datetime.date(int(person["birth_year"]), int(month), day)
        except (ValueError, KeyError, TypeError):
            raise ServiceFactsError(
                f"persons[{index}]'s birth day {day} is not a day of the month and year already "
                f"answered for them")
        out[index] = day
    return out


def _date_of_birth(person: dict, person_index: int, birth_days: dict | None) -> str:
    """The date this service sends for one person. ONE place, for the reason DEFAULT_BIRTH_MONTH is
    one place: a guard and the value it guards cannot drift apart if there is only one."""
    month = person.get("birth_month", DEFAULT_BIRTH_MONTH)
    day = (birth_days or {}).get(person_index, 1)
    return f"{person['birth_year']}-{month:02d}-{day:02d}"


def age65_ambiguity_refusal(tax_year: int) -> str:
    """The words a day-ambiguous caller is told — and, verbatim, the published exclusion. One
    source of words, so the boundary a caller reads is the boundary they hit."""
    ambiguous_year = tax_year - 64
    return (f"filers born in January {ambiguous_year} — for tax year {tax_year} the additional "
            f"standard deduction for age 65 turns on being born before Jan 2 {ambiguous_year}, "
            f"so it turns on the day of that date of birth. The day was not given; refused rather "
            f"than guessed. On the local page the date of birth is answered whole and the day stays "
            f"on that computer, and this return is computed.")


def _refuse_age65_day_ambiguous(persons: list, tax_year: int, birth_days: dict | None = None) -> None:
    """The age-65 additional standard deduction turns on 'born before January 2, <tax_year-64>'.
    The service knows only birth_year + month (a day is a forbidden identifier), and the mapper
    synthesizes day 01 — which would silently GRANT the bump to everyone born in January of that
    year, wrong for the ~30/31 born Jan 2-31. So that one cohort is day-ambiguous: REFUSE it rather
    than emit a silently-wrong number (World #1). Every other year/month is unambiguous from
    year+month alone (day 01 lands on the correct side of Jan 2).

    this tests the month the MAPPER WILL USE, not the month the caller SUPPLIED. They differ —
    `birth_month` is optional in the person schema — so testing the supplied value let an omitted
    month slip past this guard and synthesize January 1, granting the age-65 bump to (say) a
    July-born filer: a silently wrong Form 1040 line 12. Both sites now read DEFAULT_BIRTH_MONTH,
    so a guard and the value it guards cannot drift apart again."""
    ambiguous_year = tax_year - 64
    for i, p in enumerate(persons):
        if i in (birth_days or {}):
            continue                  # their day is known, so nothing is guessed
        if p.get("birth_year") == ambiguous_year and p.get("birth_month", DEFAULT_BIRTH_MONTH) == 1:
            raise ServiceFactsError(age65_ambiguity_refusal(tax_year))


# The DEPENDENT January cohorts. At an earlier pin no served line moved between a dependent's
# synthesized day 01 and any other day (measured across twelve January birth years;
# `test_contract.DependentDayInvarianceTest` pinned it). At the pin three do, because the dictionary
# applies the day-before-birthday rule to the child's age tests and the earned income credit is
# figured — measured by sweeping January of every birth year 2000-2025, day 01 against day 15:
#   * January of tax_year - 16, any child (2009 for 2025): the child tax credit's under-17 test. Born January 1
#     the child is 17 on December 31 (500.00, the credit for other dependents); born January 2-31
#     they are 16 (2,200.00). Line 24 3,165.00 against 1,465.00.
#   * January of tax_year - 18, NOT a student (2007): the qualifying child's under-19 test.
#   * January of tax_year - 23, a student (2002): the under-24 test.
# The earned income credit has since been given its own calendar-year age test (Schedule EIC's
# "If born after 2006"), so it no longer moves with the day; the dependency age test still does —
# born January 1 the child is not a qualifying child, and once their gross income fails the
# qualifying-relative limit the 500.00 credit for other dependents goes (line 24 3,665.00
# against 3,165.00).
# The day is a forbidden identifier, so each cohort is refused rather than guessed — the age-65
# posture, and the same words published as an exclusion.
DEPENDENT_DAY_AMBIGUOUS_AGES = ((17, None, "the child tax credit's under-17 test"),
                                (19, False, "the qualifying child's under-19 test"),
                                (24, True, "the qualifying child's under-24 student test"))


def dependent_day_ambiguity(person: dict, tax_year: int) -> str | None:
    """What a dependent's unknown birth day would decide, or None when year and month settle it.
    A person born January 1 attains an age on December 31, so the boundary year for an under-N
    test is `tax_year + 1 - N`."""
    if not isinstance(person, dict) or person.get("role") != "dependent":
        return None
    if person.get("birth_month", DEFAULT_BIRTH_MONTH) != 1:
        return None
    for age, student, test in DEPENDENT_DAY_AMBIGUOUS_AGES:
        if person.get("birth_year") == tax_year + 1 - age and student in (None, bool(person.get("is_student"))):
            return test
    return None


def dependent_day_ambiguity_refusal(tax_year: int) -> str:
    """The words a caller is told — and, verbatim, the published exclusion."""
    return (f"dependents born in January {tax_year - 16}, in January {tax_year - 18} and not a "
            f"student, or in January {tax_year - 23} and a student — for tax year {tax_year} an "
            f"age test for the child tax credit or for a qualifying child turns on whether they "
            f"were born on January 1. That day was not given; refused rather than guessed. On the "
            f"local page the date of birth is answered whole and the day stays on that computer, "
            f"and this return is computed.")


def _refuse_dependent_day_ambiguous(persons: list, tax_year: int, birth_days: dict | None = None) -> None:
    for i, p in enumerate(persons):
        if i in (birth_days or {}):
            continue                  # their day is known, so nothing is guessed
        if dependent_day_ambiguity(p, tax_year) is not None:
            raise ServiceFactsError(dependent_day_ambiguity_refusal(tax_year))


BOX4_TOO_HIGH_REFUSAL = (
    "social_security_withheld_cents exceeds the statutory rate on social_security_wages_cents — "
    "one employer cannot withhold more than the rate, and the engine treats that as a knockout "
    "while still computing a refundable credit from it; refused as the caller-input fault it is")


# the W-2 half of a review finding. Every W-2 money box now carries `minimum: 0` in
# `w2.schema.json`, so a negative is a malformed request, and neither transport validates a
# request. Measured in review at an earlier pin: wages of -52,000.00 computed line 9 = -5,200,000
# and refunded the whole withholding on line 34, a cited 200, because the dictionary's
# `<Limit type="Min">` does not run on the persister path. Build's formW2s now floors box 1 and box
# 2 at $0 where they are read (b161c1939b); re-measured at the alpha-1 pin, the same request
# serves line 1a and line 9 as 0. So this refusal is belt-and-braces against a sign error, not the
# only thing between the person and a subtracted wage — but a box read as $0 is still not the
# figure on the form, so the request is still refused rather than served.
NEGATIVE_W2_REFUSAL = (
    "a Form W-2 money box is negative — no W-2 box can report one, and the engine would read it as "
    "0, which is not the figure on the form. Refused as the malformed request it is "
    "(`w2.schema.json` says `minimum: 0` on every money box): send it again with the figure the "
    "form shows")

_W2_MONEY_BOXES = ("wages_cents", "withholding_cents", "social_security_wages_cents",
                   "medicare_wages_cents", "social_security_withheld_cents")


def refuse_negative_w2_amounts(w2s: list) -> None:
    """`FactsSchemaError` (SCHEMA_INVALID), the same call as `refuse_negative_w2g_amounts`
    and for the same reason: a schema-invalid request is "send it again", never a boundary. Runs
    BEFORE `refuse_impossible_box4`, so a negative box 3 is reported as the sign fault the caller
    can act on rather than as an impossible rate. Type is checked before either runs."""
    for w2 in w2s:
        for field in _W2_MONEY_BOXES:
            value = w2.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value < 0:
                raise FactsSchemaError(NEGATIVE_W2_REFUSAL)


def refuse_impossible_box4(w2s: list) -> None:
    """From review. Box 4 above the statutory rate on box 3 is arithmetically impossible for a single
    employer. Left unrefused it is worse than wrong: the engine resolves /knockoutFormW2s (the return
    must not be filed) AND a large refundable credit, and the service served that as a normal 200."""
    for w2 in w2s:
        box4 = w2.get("social_security_withheld_cents")
        box3 = w2.get("social_security_wages_cents", w2.get("wages_cents"))
        if box4 is None or box3 is None:
            continue
        if not isinstance(box4, int) or not isinstance(box3, int):
            continue
        # The rate applied to box 3, rounded half-up to the cent (a corpus finding): an
        # employer withholds whole cents, so 6.2% of 41,368.00 = 2,564.816 is correctly withheld as
        # 2,564.82. Compared unrounded, every W-2 whose withholding rounds up was refused — seven
        # synthetic showcase profiles the pinned engine computes. One rounding is allowed, nothing
        # beyond it. A form printed in whole dollars rounds the same way to the dollar (measured: an
        # IRS test scenario's box 4 of 943.00 on box 3 of 15,205.00, where 6.2% is 942.71), so a
        # whole-dollar box 4 may be the rate rounded half-up to the dollar. A box 4 with cents
        # keeps the one-cent rule.
        allowed = (box3 * OASDI_RATE_NUM * 2 + OASDI_RATE_DEN) // (OASDI_RATE_DEN * 2)
        allowed_dollars = (box3 * OASDI_RATE_NUM * 2 + OASDI_RATE_DEN * 100) // (OASDI_RATE_DEN * 200) * 100
        if box4 > (max(allowed, allowed_dollars) if box4 % 100 == 0 else allowed):
            raise ServiceFactsError(BOX4_TOO_HIGH_REFUSAL)


def employer_ordinals(w2s: list) -> dict:
    """Caller `employer_ref` -> a DENSE per-request ordinal, in first-appearance order.

    Any injective map preserves the grouping semantics exactly (same ref = same employer), and this
    one bounds the value by the W-2 count. That matters: the ordinal becomes an EIN serial via
    `f"{n:07d}"`, which pads but never truncates — so an unbounded caller value produced an 8+ char
    serial, tripped `Ein.scala`'s length precondition, and surfaced as ENGINE_UNAVAILABLE → HTTP 503
    'retry': an unbounded JVM-forking loop driven by a caller-controlled field. Normalising also
    keeps the caller's number out of the fact graph entirely."""
    out, n = {}, 0
    for w2 in w2s:
        ref = w2.get("employer_ref", 0)
        if ref not in out:
            out[ref] = n
            n += 1
    return out


def refuse_multiple_employers(w2s: list) -> None:
    """The excess Social Security withholding credit is tested PER PERSON — the IRS wording is
    "if you, or your spouse if filing a joint return, had more than one employer". So the ambiguity
    this service cannot resolve is one filer holding several W-2s, not a household holding several:
    two spouses with one W-2 each is the most ordinary joint return there is and must keep working.

    `person` is an index into persons[] and defaults to 0 (as `_map_w2s` reads it), so W-2s with no
    person field all belong to the SAME filer — the ambiguous case, not the safe one.

    The refusal is now an ASK, not a rejection: supply the three facts the credit needs and the
    return computes. Refusing outright was the earlier, over-broad answer."""
    counts = {}
    for w2 in w2s:
        counts[w2.get("person", 0)] = counts.get(w2.get("person", 0), 0) + 1
    for w2 in w2s:
        if counts[w2.get("person", 0)] > 1 and not (
                "employer_ref" in w2
                and "social_security_wages_cents" in w2
                and "social_security_withheld_cents" in w2):
            raise ServiceFactsError(MULTIPLE_EMPLOYERS_REFUSAL)


NEGATIVE_W2G_REFUSAL = (
    "a Form W-2G box 1 or box 4 amount is negative — neither box can report one, and the engine "
    "would read a negative box 1 as 0 on Schedule 1 line 8b, which is not the figure on the form. "
    "Refused as the malformed request it is (`w2g.schema.json` says `minimum: 0` on both boxes): "
    "send it again with the figure the form shows")


def refuse_negative_ssa1099_amounts(items: list) -> None:
    """Box 5 net benefits may be negative on a real statement (repayments over benefits);
    at the pin the engine serves the negative on line 6a, taxes nothing and, above $3,000, fires
    its own knockout. Below that the excess is a Schedule A route this service does not serve, and
    a negative figure on a served line 6a is not what the printed form carries — so a negative is
    refused by name, `FactsSchemaError` like the W-2G boxes (the schema says `minimum: 0`)."""
    for i, item in enumerate(items):
        for field in ("net_benefits_cents", "federal_withholding_cents"):
            value = item.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value < 0:
                raise FactsSchemaError(
                    f"ssa1099s[{i}].{field} is negative ({value}) — "
                    + ("repayments exceeding the year's benefits open an itemized deduction "
                       "this service does not carry, so the figure is refused rather than "
                       "served as a negative line 6a"
                       if field == "net_benefits_cents" else
                       "withholding is never negative"))


def refuse_misplaced_g1099_repayments(items: list) -> None:
    """`repaid_cents` is the Schedule 1 line 7 entry space: unemployment compensation
    received in the year and repaid in the same year, netted against box 1. Measured at the pin,
    a repayment above the year's benefits floors line 7 at zero with no knockout — the excess is
    the earlier-year (claim-of-right) leg, a Schedule A route this service does not carry — so
    the contradiction between the two fields is refused by name rather than served as a silent
    zero. A cross-field rule the schema cannot express: `ServiceFactsError`, the misplaced-answer
    class."""
    for i, item in enumerate(items):
        repaid = item.get("repaid_cents")
        amount = item.get("unemployment_compensation_cents")
        if (isinstance(repaid, int) and not isinstance(repaid, bool)
                and isinstance(amount, int) and not isinstance(amount, bool)
                and repaid > amount):
            raise ServiceFactsError(
                f"g1099s[{i}].repaid_cents ({repaid}) exceeds the year's unemployment "
                f"compensation ({amount}) — a repayment above the benefits received in the "
                "year is a repayment of an earlier year's benefits, which opens an itemized "
                "deduction (or the engine's own knockout above $3,000) this service does not "
                "carry; refused rather than served as a zero line 7")


def refuse_negative_w2g_amounts(w2gs: list) -> None:
    """The two W-2G writables carry `<Limit type="Min"><Dollar>0</Dollar></Limit>` in
    formW2Gs.xml, and it would be easy to read that as the engine refusing a negative for us. IT
    DOES NOT — measured, not assumed: both amounts pass straight through the persister and
    resolve. At an earlier pin -3,400.00 of winnings was SUBTRACTED from total income in a normal,
    cited 200. Build's "unfloored Min readers" sweep (40ded01860) now floors box 1 at $0 where
    /w2gWinnings sums it; re-measured at the alpha-1 pin, the same request serves line 9 unchanged
    and refunds the withholding. So this refusal is belt-and-braces now — but a box read as $0 is
    still not the figure on the form, so it stays a refusal rather than a silent zero.

    Type is checked before this runs (`_refuse_missing_or_mistyped`), so a comparison here cannot
    raise a TypeError on a string — the ordering `refuse_impossible_box4` already relies on.

    `FactsSchemaError`, not its parent (review): the schema says `minimum: 0`, so a negative
    is a malformed request — `SCHEMA_INVALID`, "send it again" — and reporting it as
    `OUT_OF_COVERAGE` ("this service can never do this") would be a misreport. It is also
    what keeps it OUT of `coverage.exclusions()`, which lists boundaries, not caller faults."""
    for g in w2gs:
        for field in ("winnings_cents", "federal_withholding_cents"):
            value = g.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value < 0:
                raise FactsSchemaError(NEGATIVE_W2G_REFUSAL)


NEGATIVE_OID1099_REFUSAL = (
    "a Form 1099-OID box amount is negative — no box of the form can report one, and the engine "
    "does not stop it: a negative would be SUBTRACTED from interest income or from the "
    "withholding on line 25d. The schema says minimum 0; send the figure the form shows.")


def oid_tax_exempt_question_reached(item: dict) -> bool:
    """Whether the box 2 tax-exempt question is reached on this form: box 2 has an amount and box
    11 has none — the one case the form does not settle (with box 11 above 0 its instructions
    classify box 2 as tax-exempt). A REQUIRED answer and never a default: at an earlier pin an
    item missing it was DROPPED FROM THE RETURN WHOLE, in silence (1,000.00 of box 1 served as
    0.00, `complete`); re-measured at the alpha-1 pin, a blank box 2 or box 11 now reads $0 and
    this answer, unanswered where it is reached, holds the return Incomplete — so it is still
    asked, and the zeros the mapper sends for blank boxes are now belt-and-braces."""
    return (isinstance(item, dict) and _cents_or_zero(item.get("other_periodic_interest_cents")) > 0
            and _cents_or_zero(item.get("tax_exempt_oid_cents")) == 0)


def b1099_term_question_reached(item: dict) -> bool:
    """box 2 is ASKED when box 1b or 1c has no date. MEASURED on the pinned engine: with both
    dates the engine works out the holding period itself (a contradicting box 2 is overridden);
    with a date missing and box 2 unanswered, every served line resolves incomplete."""
    return isinstance(item, dict) and not ("date_acquired" in item and "date_sold" in item)


def refuse_malformed_b1099s(items: list, tax_year: int) -> None:
    import datetime
    for i, item in enumerate(items):
        for field, why in B1099_REFUSED.items():
            value = item.get(field)
            if value is True or (isinstance(value, int) and not isinstance(value, bool)
                                 and value > 0):
                raise ServiceFactsError(
                    f"b1099s[{i}].{field}: on this Form 1099-B {why}; refused rather than "
                    f"computed without it")
        dates = {}
        for field in ("date_acquired", "date_sold"):
            if field in item:
                try:
                    dates[field] = datetime.date.fromisoformat(item[field])
                except (TypeError, ValueError):
                    raise FactsSchemaError(f"b1099s[{i}].{field} is not a date")
        if "date_sold" in dates and dates["date_sold"].year != tax_year:
            raise FactsSchemaError(
                f"b1099s[{i}].date_sold is outside the tax year — a Form 1099-B for {tax_year} "
                f"reports sales made in {tax_year}")
        if len(dates) == 2 and dates["date_acquired"] > dates["date_sold"]:
            raise FactsSchemaError(f"b1099s[{i}].date_acquired is after date_sold")
        if item.get(B1099_TERM_FIELD) == "ordinary":
            raise ServiceFactsError(
                f"b1099s[{i}].term: box 2 of this Form 1099-B is marked Ordinary — that gain or "
                f"loss is not reported on Form 8949 and is not in the covered set; refused "
                f"rather than computed as a capital gain")
        for field in B1099_ASKED_MARKS:
            if field not in item:
                raise FactsSchemaError(
                    f"b1099s[{i}].{field} (box 3) is a question on every Form 1099-B, not a "
                    f"default — answer it true or false (prepare_return asks it as a gap)")
        if b1099_term_question_reached(item) and B1099_TERM_FIELD not in item:
            raise FactsSchemaError(
                f"b1099s[{i}].term (box 2, short-term or long-term) is a question when box 1b "
                f"or 1c has no date, not a default — answer it (prepare_return asks it as a gap)")


def refuse_malformed_oid1099s(items: list) -> None:
    for i, item in enumerate(items):
        for field in OID_MONEY_FIELDS:
            value = item.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value < 0:
                raise FactsSchemaError(NEGATIVE_OID1099_REFUSAL)
        reached = oid_tax_exempt_question_reached(item)
        if OID_TAX_EXEMPT_FIELD in item and not reached:
            raise ServiceFactsError(
                f"oid1099s[{i}].{OID_TAX_EXEMPT_FIELD} is answered but the form settles it: it is "
                f"asked only when box 2 has an amount and box 11 has none (with an amount in box "
                f"11 the form's instructions make box 2 tax-exempt); refused rather than dropped")
        if reached and OID_TAX_EXEMPT_FIELD not in item:
            raise FactsSchemaError(
                f"oid1099s[{i}].{OID_TAX_EXEMPT_FIELD} is a question on a Form 1099-OID with an "
                f"amount in box 2 and none in box 11, not a default — answer it (prepare_return "
                f"asks it as a gap)")
        if item.get(OID_FATCA_FIELD) is True:
            raise ServiceFactsError(
                f"oid1099s[{i}].{OID_FATCA_FIELD} is checked — the Form 8938 reporting that box "
                f"points to is not in the covered set; refused rather than computed without it")


NEGATIVE_INT1099_REFUSAL = (
    "a Form 1099-INT box amount is negative — none of its amount boxes can report one, and the "
    "engine does not stop it (the same measured hole as the W-2G's Min-0 limit): a negative "
    "would be SUBTRACTED from interest income or from the withholding on line 25d. The schema "
    "says minimum 0; send the figure the form shows.")


def refuse_negative_int1099_amounts(items: list) -> None:
    """The negative-amount posture applied to the third covered stream: the dictionary's
    Min-0 limits are UI constraints, not persister checks, so the service refuses negatives
    itself — `FactsSchemaError` (SCHEMA_INVALID, a caller fault to correct and resend), never
    OUT_OF_COVERAGE."""
    for item in items:
        for field in ("interest_cents", "government_interest_cents",
                      "tax_exempt_interest_cents", "federal_withholding_cents",
                      *INT_EXTRA_EMISSION):
            value = item.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value < 0:
                raise FactsSchemaError(NEGATIVE_INT1099_REFUSAL)


IMPOSSIBLE_DIV_SLICE_REFUSAL = (
    "a Form 1099-DIV slice is larger than the box it sits inside — box 1b and box 5 are each "
    "part of box 1a, and box 2b is part of box 2a, by the form's own instructions. The engine "
    "does not stop an impossible slice; it would compute a wrong preferential-rate split. Check "
    "the form and send the amounts as printed.")


def refuse_impossible_div_slices(items: list) -> None:
    """The box-4-over-6.2% posture applied to the dividend slices: a containment the printed form
    guarantees is checked here because nothing downstream will."""
    for item in items:
        ordinary = item.get("ordinary_dividends_cents")
        capgain = item.get("capital_gain_distributions_cents")
        for outer, inner in ((ordinary, item.get("qualified_dividends_cents")),
                             (ordinary, item.get("section_199a_dividends_cents")),
                             (capgain, item.get("unrecaptured_1250_gain_cents"))):
            if (isinstance(inner, int) and not isinstance(inner, bool) and inner > 0
                    and isinstance(outer, int) and not isinstance(outer, bool)
                    and inner > outer):
                raise FactsSchemaError(IMPOSSIBLE_DIV_SLICE_REFUSAL)


def refuse_negative_div1099_amounts(items: list) -> None:
    """The negative-amount posture, fourth stream: the dictionary's Min-0 limits are UI
    constraints, not persister checks."""
    for item in items:
        for field in ("ordinary_dividends_cents", "qualified_dividends_cents",
                      "capital_gain_distributions_cents", "unrecaptured_1250_gain_cents",
                      "federal_withholding_cents", "section_199a_dividends_cents",
                      "exempt_interest_dividends_cents"):
            value = item.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value < 0:
                raise FactsSchemaError(
                    "a Form 1099-DIV box amount is negative — no box on the form can report "
                    "one, and the engine does not stop it. The schema says minimum 0; send the "
                    "figure the form shows.")


def refuse_negative_r1099_amounts(items: list) -> None:
    """The negative-amount posture, fifth stream."""
    for item in items:
        for field in ("gross_distribution_cents", "taxable_amount_cents",
                      "federal_withholding_cents", R1099_HFD_FIELD, R1099_QCD_FIELD, R1099_ROLLOVER_FIELD):
            value = item.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value < 0:
                raise FactsSchemaError(
                    "a Form 1099-R box amount is negative — no box on the form can report one, "
                    "and the engine does not stop it. The schema says minimum 0; send the "
                    "figure the form shows.")


def schedule_c_net_cents(item: dict) -> int:
    """Schedule C line 31 as the pinned engine will compute it: line 1 − line 2 − line 4 + line 6
    − line 28. ONE definition, read by both the loss-gate ask (`gaps.gaps_for`) and the loss-gate
    refusals below — computed twice, the ask threshold and the engine's netProfit sign could
    drift apart. Returns > receipts is deliberately NOT refused: refunds of a prior year's sales
    can exceed this year's receipts, and the form itself allows a negative line 3 — measured at
    the pin, the engine computes it as an ordinary loss."""
    def amt(field):
        v = item.get(field)
        return v if isinstance(v, int) and not isinstance(v, bool) else 0
    return (amt("gross_receipts_cents") - amt("returns_and_allowances_cents")
            - amt("cost_of_goods_sold_cents") + amt("other_business_income_cents")
            - amt("total_expenses_cents"))


# the section 465 amount at risk, one field on three loss streams and ONE population
# sentence, spelled per stream: the at-risk answer is ANSWERED and FALSE, and the stream's
# current year is a LOSS. `_AT_RISK` names the boolean each stream spells it with; the loss test
# is the stream's own, never a second copy — `schedule_c_net_cents`, `rental_current_net_cents`
# and `k1_has_box1_loss` already decide it for the ask and the other refusals.
_AT_RISK = {"schedule_c": "all_investment_at_risk", "rentals": "fully_at_risk",
            "k1s": "fully_at_risk"}


def at_risk_amount_armed(group: str, item: dict, has_loss: bool) -> bool:
    """True where `amount_at_risk_cents` is a QUESTION — the one place it may be answered at all.

    The dictionary reads its own amount only when the boolean is answered and false
    (`atRiskLimitationApplies` on every stream), and only a current-year loss reaches the cap:
    measured at the pin, a rental profit with the boolean false and no amount resolves every
    served line, while a LOSS with the boolean false and no amount resolves none of them. So the
    same condition arms the ask, the absence statement and the refusal."""
    return has_loss and item.get(_AT_RISK[group]) is False


def refuse_off_population_at_risk_amount(group: str, i: int, item: dict, has_loss: bool,
                                         boxes: str) -> None:
    """The off-population refusal, by name. `boxes` is how this stream's form asks the question,
    so the sentence names what the filer answered rather than a field."""
    if "amount_at_risk_cents" not in item or at_risk_amount_armed(group, item, has_loss):
        return
    where = f"{group}[{i}].amount_at_risk_cents"
    answer = item.get(_AT_RISK[group])
    if answer is True:
        raise ServiceFactsError(
            f"{where} is answered where {boxes} says all the investment is at risk — the "
            f"Form 6198 cap applies only when it is not, and a loss that is fully at risk is "
            f"taken in full; refused rather than dropped")
    if answer is None:
        raise ServiceFactsError(
            f"{where} is answered before {boxes} is — whether the Form 6198 cap applies at all "
            f"is that answer's to give; refused rather than routed on a guess")
    raise ServiceFactsError(
        f"{where} is answered where there is no loss for the year, so the Form 6198 cap has "
        f"nothing to bind on — the amount at risk limits a loss and this year shows none; "
        f"refused rather than dropped")


def require_at_risk_amount(group: str, i: int, item: dict, has_loss: bool, boxes: str) -> None:
    """The ask's backstop. Unanswered on the armed population the dictionary's own deductible
    loss is Incomplete and NO served line resolves (measured at the pin, all three streams), so
    the service asks the question instead of serving a return that cannot be built."""
    if at_risk_amount_armed(group, item, has_loss) and "amount_at_risk_cents" not in item:
        raise FactsSchemaError(
            f"{group}[{i}].amount_at_risk_cents (the simplified Form 6198 amount at risk) is a "
            f"question once {boxes} says some investment is not at risk and the year is a loss, "
            f"not a default — answer it, 0 if nothing is at risk (prepare_return asks it as a "
            f"gap)")


def refuse_negative_schedule_c_amounts(items: list) -> None:
    """The negative-amount posture, sixth stream."""
    for item in items:
        for field in ("gross_receipts_cents", "returns_and_allowances_cents",
                      "cost_of_goods_sold_cents", "other_business_income_cents",
                      "total_expenses_cents", "amount_at_risk_cents"):
            value = item.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value < 0:
                raise FactsSchemaError(
                    "a Schedule C amount is negative — no line 1 through 28 entry can be one "
                    "(a loss appears on line 31, computed, never typed), and the Form 6198 "
                    "amount at risk is entered as not less than zero. The schema says "
                    "minimum 0; send the figures the form shows.")


def refuse_unsupported_schedule_c_loss_answers(items: list) -> None:
    """The loss gate. The pinned engine treats line G as record-only (nothing
    computed reads it) and an unanswered box 32 as fully at risk — build's own descriptions say
    so — which means it would take EVERY loss in full. This service will not state either answer
    for the filer: on a loss, both are questions (`gaps.gaps_for` asks them first) and a line G
    "No" is refused. RETIRED: the third clause that stood here — "box 32b is refused whatever
    the sign, so the only 32a value ever emitted is a true": box 32b now asks the simplified
    Form 6198 amount at risk beside it and the loss is capped at that amount."""
    for i, item in enumerate(items):
        loss = schedule_c_net_cents(item) < 0
        refuse_off_population_at_risk_amount("schedule_c", i, item, loss, "box 32")
        if loss:
            if item.get("materially_participated") is False:
                raise ServiceFactsError(
                    "line G (“Did you ‘materially participate’ in the operation "
                    "of this business during 2025?”) is answered No and this business has "
                    "a loss — Form 8582 is not in the covered set, and that loss cannot be "
                    "computed without it")
            for field in ("materially_participated", "all_investment_at_risk"):
                if field not in item:
                    raise FactsSchemaError(
                        f"schedule_c[{i}].{field} is a question when the business has a loss, "
                        f"not a default — answer it (prepare_return asks it as a gap)")
        # Last, because it sits BEHIND box 32: the amount is a question only once that box is
        # answered 32b, so the filer meets line G and box 32 first.
        require_at_risk_amount("schedule_c", i, item, loss, "box 32")


def rental_expenses_pre_depreciation_cents(item: dict) -> int:
    """line 20 as far as this service can measure it BEFORE the engine runs — the lump
    `total_expenses_cents` when that is how the property answered, else the sum of the four
    itemized lines this schema carries (insurance, management fees, repairs, taxes). Depreciation
    (line 18) is EXCLUDED either way when itemized: the engine computes it from
    `building_basis_cents` / `five_year_property_basis_cents`, never this service, so a property
    itemizing its expenses without a lump total is measured here as more profitable than the
    engine's own line 21 by whatever it later depreciates. That is a stated approximation of the
    loss-gate ASK threshold (`rental_current_net_cents` below), not of the served figure: on the
    four rental-depreciation profiles it decides nothing (each nets positive, or already carries
    the loss-gate answers, before AND after depreciation) — a hypothetical property profitable before
    depreciation but a loss after it would need those answers asked one round later than an
    engine resolve could confirm them."""
    def amt(field):
        v = item.get(field)
        return v if isinstance(v, int) and not isinstance(v, bool) else 0
    if "total_expenses_cents" in item:
        return amt("total_expenses_cents")
    return amt("insurance_cents") + amt("management_fees_cents") + amt("repairs_cents") \
        + amt("taxes_cents")


def rental_current_net_cents(item: dict) -> int:
    """Schedule E line 21 for this property, as the engine will compute it: line 3 rents minus
    the line 20 total. The §465 at-risk question turns on THIS sign — the current year's loss is
    what at-risk limits; a prior-year carry-in already passed at-risk in its own year.

    the line 20 half now reads `rental_expenses_pre_depreciation_cents`, which EXCLUDES
    depreciation on the itemized path — see that function's docstring for the stated limit."""
    def amt(field):
        v = item.get(field)
        return v if isinstance(v, int) and not isinstance(v, bool) else 0
    return amt("rents_received_cents") - rental_expenses_pre_depreciation_cents(item)


def rental_combined_net_cents(item: dict) -> int:
    """Form 8582 line 1d for this property: the current year net COMBINED with the prior years'
    unallowed loss (Part IV column (c)). The §469(i) active-participation question turns on THIS
    sign — measured at the pin, a 5,000 profit against an 8,000 carry-in nets to −3,000 and is
    suspended in full when active participation is unanswered."""
    def amt(field):
        v = item.get(field)
        return v if isinstance(v, int) and not isinstance(v, bool) else 0
    return rental_current_net_cents(item) - amt("prior_year_unallowed_loss_cents")


# Reg. 1.469-2(f)(6). ONE predicate spelled two ways, and the second reads the first, so
# the ask, the absence statement and the refusal can never disagree about which property they are
# about. The line 1b type code DERIVES the self-rental flag rather than a second boolean asking
# the same thing twice: the form's own list labels type 7 "Self-Rental", and the pinned dictionary
# warns in as many words that a code disagreeing with the flag "changes no computed line" — one
# answer is the only shape in which they cannot disagree.


def rental_is_self_rental(item: dict) -> bool:
    """Schedule E line 1b type 7. The whole self-rental population, and the only place the lessee
    answer may be given at all."""
    return item.get("property_type") == "self_rental"


def self_rental_recharacterization_armed(item: dict) -> bool:
    """True where the lessee answer DECIDES a number — a self-rental whose net for the year,
    after any prior years' unallowed loss, is a PROFIT.

    Both halves measured at the pin, not inferred. The gate (`recharacterizesSelfRental`) reads
    `netAfterPriorLoss`, so a 12,000 self-rental profit against a 20,000 carry-in recharacterizes
    NOTHING and every served line is identical either way; the rule is asymmetric, so a
    self-rental LOSS is not recharacterized either. `rental_combined_net_cents` is that same
    Form 8582 line 1d combine the active-participation question already turns on — never a
    second copy. (On a profit the section 465 cap cannot bind, so the combine and the
    dictionary's at-risk-allowed net are the same number.)"""
    return rental_is_self_rental(item) and rental_combined_net_cents(item) > 0


def refuse_off_population_lessee_participation(i: int, item: dict) -> None:
    """Refused by name off the self-rental population. The sentence names the answer the filer
    gave on the form, never the field: material participation in a LESSEE business is a question
    only about a property rented to one."""
    if "materially_participates_in_lessee" not in item or rental_is_self_rental(item):
        return
    given = item.get("property_type")
    raise ServiceFactsError(
        f"rentals[{i}].materially_participates_in_lessee is answered on a property whose "
        f"Schedule E line 1b type of property is "
        + (f"{given}" if given else "not given")
        + ", so there is no lessee business for it to be about — the question belongs to a "
          "property rented to a trade or business the filer owns an interest in (line 1b type "
          "7, Self-Rental); refused rather than dropped")


def require_lessee_participation(i: int, item: dict) -> None:
    """The ask's backstop. Unanswered, the dictionary's gate resolves false and the profit stays
    passive — a computed return, and on one carrying another property's passive loss the WRONG
    number in the taxpayer's favour (measured: 12,000 of self-rental profit absorbs 6,000 of
    another property's loss, 720 of tax). The SSTB flag's lesson exactly: a
    taxpayer-favourable silent default is the one an ask has to replace."""
    if (self_rental_recharacterization_armed(item)
            and "materially_participates_in_lessee" not in item):
        raise FactsSchemaError(
            f"rentals[{i}].materially_participates_in_lessee is a question on a self-rental "
            f"(Schedule E line 1b type 7) whose year is a profit, not a default — answer it "
            f"(prepare_return asks it as a gap)")


def refuse_lessee_answer_contradicting_type_7(i: int, item: dict) -> None:
    """Schedule E's instructions DEFINE line 1b type 7: "Enter code '7' for
    self-rental if you rent property to a trade or business in which you materially participated."
    The dictionary follows them: under code 7 the code is the whole attestation and
    the lessee answer is NOT READ. So a no beside type 7 would be computed as a yes (measured:
    `/rentalNonpassiveNet` 12,000.00 either way). An answer this service asked for and the engine ignores is refused by name —
    the two statements contradict, and which of them is wrong is the filer's to say."""
    if rental_is_self_rental(item) and item.get("materially_participates_in_lessee") is False:
        raise ServiceFactsError(
            f"rentals[{i}] gives Schedule E line 1b type 7 (Self-Rental) and answers that the "
            f"filer did not materially participate in the business renting it — the form's "
            f"instructions define type 7 as a property rented to a business the filer materially "
            f"participated in, so the two contradict; refused rather than computed on either one. "
            f"A property rented to a business the filer did not materially participate in takes "
            f"the type that describes the property itself")


# the expense intake's two shapes are mutually exclusive on ONE property — a lump
# `total_expenses_cents` (line 20 as a whole) or the four itemized lines this schema carries
# (insurance, management fees, repairs, taxes) plus the depreciation inputs (building basis,
# 5-year property). Refused rather than summed or overridden, because either combination would
# silently change which figure line 20 actually carries.
_RENTAL_ITEMIZED_FIELDS = ("insurance_cents", "management_fees_cents", "repairs_cents",
                           "taxes_cents", "building_basis_cents", "has_five_year_property")


def refuse_mixed_rental_expense_shapes(i: int, item: dict) -> None:
    if "total_expenses_cents" not in item:
        return
    given = sorted(f for f in _RENTAL_ITEMIZED_FIELDS if f in item)
    if given:
        raise ServiceFactsError(
            f"rentals[{i}].total_expenses_cents is answered beside "
            f"{', '.join(f'rentals[{i}].{f}' for f in given)} — the line 20 total and the "
            f"itemized lines it would otherwise add up from are not combined; refused rather "
            f"than silently choosing one")


def rental_building_class_armed(item: dict) -> bool:
    """True when the building's MACRS recovery-period CLASS is a question —
    `building_basis_cents` answered and positive. The pinned dictionary's own refusal
    (`buildingRecoveryPeriodUnknown` / `/knockoutRentalBuildingRecoveryPeriodUnknown`) blocks
    FILING a return in exactly this state, unanswered — measured against the pin on all four
    rental-depreciation profiles' own oracle facts, which carry a building basis and never answer
    this class (a corpus gap that predates this unit, not a service defect). Asked here, as a gap,
    before that knockout is ever reached."""
    basis = item.get("building_basis_cents")
    return isinstance(basis, int) and not isinstance(basis, bool) and basis > 0


def refuse_off_population_building_class(i: int, item: dict) -> None:
    if "is_nonresidential_real_property" in item and not rental_building_class_armed(item):
        raise ServiceFactsError(
            f"rentals[{i}].is_nonresidential_real_property is answered where no positive "
            f"building_basis_cents was given — the recovery-period class decides nothing "
            f"without a depreciable building basis to apply it to; refused rather than dropped")


def require_building_class(i: int, item: dict) -> None:
    if rental_building_class_armed(item) and "is_nonresidential_real_property" not in item:
        raise FactsSchemaError(
            f"rentals[{i}].is_nonresidential_real_property (the building's MACRS recovery-"
            f"period class — Form 4562 Part III line 19i, 27.5-year residential, or line 19j, "
            f"39-year nonresidential) is a question once building_basis_cents is answered and "
            f"positive, not a default — answer it (prepare_return asks it as a gap); the "
            f"pinned dictionary refuses to FILE a rental whose building basis is answered but "
            f"whose class is not")


def refuse_off_population_standard_gds(i: int, item: dict) -> None:
    if "building_uses_standard_gds" in item and not rental_building_class_armed(item):
        raise ServiceFactsError(
            f"rentals[{i}].building_uses_standard_gds is answered where no positive "
            f"building_basis_cents was given — the recovery-period method decides nothing "
            f"without a depreciable building basis to apply it to; refused rather than dropped")


def require_standard_gds(i: int, item: dict) -> None:
    """The method attestation beside the class: on a positive building basis the pinned
    dictionary leaves the building's depreciation, Schedule E line 18 and AGI Incomplete until
    it is answered, and an answered false is its own knockout
    (`/knockoutRentalBuildingRecoveryPeriodUnknown`) — asked as a gap, never defaulted."""
    if rental_building_class_armed(item) and "building_uses_standard_gds" not in item:
        raise FactsSchemaError(
            f"rentals[{i}].building_uses_standard_gds (whether the building is depreciated "
            f"under regular MACRS GDS over 27.5 or 39 years — Form 4562 Part III line 19i or "
            f"19j) is a question once building_basis_cents is answered and positive, not a "
            f"default — answer it (prepare_return asks it as a gap); unanswered, the pinned "
            f"dictionary leaves Schedule E line 18 incomplete")


def rental_loss_arose_participation_armed(item: dict) -> bool:
    """True when the active participation in the year a carried-in loss AROSE is a question: a
    prior years' unallowed loss above zero and active participation answered yes. The pinned
    dictionary reads it (`priorYearLossQualifiesForActiveParticipation`) only on the active
    participation arms of the rental's Form 8582 Part IV and Part V figures, so a No to active
    participation, or no carried-in loss, resolves without it — measured at the pin. Unanswered
    on this population those figures, the passive-loss totals, Schedule E and AGI are all
    Incomplete: the instructions keep a prior-year loss in Part IV only when the filer actively
    participated both in the year it arose and this year (2025 Instructions for Form 8582,
    Part IV column (c); IRC 469(i)(1)), and either default would misstate the loss allowed."""
    loss = item.get("prior_year_unallowed_loss_cents")
    return (isinstance(loss, int) and not isinstance(loss, bool) and loss > 0
            and item.get("active_participation") is True)


def refuse_off_population_loss_arose_participation(i: int, item: dict) -> None:
    if ("active_participation_when_loss_arose" in item
            and not rental_loss_arose_participation_armed(item)):
        raise ServiceFactsError(
            f"rentals[{i}].active_participation_when_loss_arose is answered where there is no "
            f"prior_year_unallowed_loss_cents above zero with active_participation true — it "
            f"decides where a carried-in loss goes on Form 8582 only then; refused rather than "
            f"dropped")


def require_loss_arose_participation(i: int, item: dict) -> None:
    if (rental_loss_arose_participation_armed(item)
            and "active_participation_when_loss_arose" not in item):
        raise FactsSchemaError(
            f"rentals[{i}].active_participation_when_loss_arose (whether you actively "
            f"participated in this rental in the year the prior years' unallowed loss arose — "
            f"Form 8582 Part IV or Part V column (c)) is a question once "
            f"prior_year_unallowed_loss_cents is above zero and active_participation is true, "
            f"not a default — answer it (prepare_return asks it as a gap); unanswered, the "
            f"pinned dictionary leaves this rental's Form 8582 figures incomplete")


def refuse_off_population_placed_in_service_flag(i: int, item: dict) -> None:
    """`placed_in_service_in_current_year` is a question about a BUILDING; a property
    with no `building_basis_cents` at all has none to place in service."""
    if "placed_in_service_in_current_year" in item and "building_basis_cents" not in item:
        raise ServiceFactsError(
            f"rentals[{i}].placed_in_service_in_current_year is answered where no "
            f"building_basis_cents was given — there is no building for the question to be "
            f"about; refused rather than dropped")


def rental_placed_in_service_month_armed(item: dict) -> bool:
    """True when the month is a question — `placed_in_service_in_current_year` answered
    true."""
    return item.get("placed_in_service_in_current_year") is True


def refuse_off_population_placed_in_service_month(i: int, item: dict) -> None:
    if "placed_in_service_month" in item and not rental_placed_in_service_month_armed(item):
        raise ServiceFactsError(
            f"rentals[{i}].placed_in_service_month is answered where "
            f"placed_in_service_in_current_year is not true — the month selects the first-"
            f"year mid-month fraction only for a building placed in service THIS year; "
            f"refused rather than dropped")


def require_placed_in_service_month(i: int, item: dict) -> None:
    if rental_placed_in_service_month_armed(item) and "placed_in_service_month" not in item:
        raise FactsSchemaError(
            f"rentals[{i}].placed_in_service_month is a question once "
            f"placed_in_service_in_current_year is true, not a default — answer it "
            f"(prepare_return asks it as a gap)")


def rental_five_year_basis_armed(item: dict) -> bool:
    """True when the 5-year property's cost basis is a question — `has_five_year_property`
    answered true."""
    return item.get("has_five_year_property") is True


def refuse_off_population_five_year_basis(i: int, item: dict) -> None:
    if "five_year_property_basis_cents" in item and not rental_five_year_basis_armed(item):
        raise ServiceFactsError(
            f"rentals[{i}].five_year_property_basis_cents is answered where "
            f"has_five_year_property is not true — the cost basis is a question only once a "
            f"5-year property item is claimed; refused rather than dropped")


def require_five_year_basis(i: int, item: dict) -> None:
    if rental_five_year_basis_armed(item) and "five_year_property_basis_cents" not in item:
        raise FactsSchemaError(
            f"rentals[{i}].five_year_property_basis_cents is a question once "
            f"has_five_year_property is true, not a default — answer it (prepare_return asks "
            f"it as a gap)")


def refuse_negative_rental_amounts(items: list) -> None:
    """The negative-amount posture, seventh stream. The itemized expense lines and the
    depreciation-input amounts joined the swept fields — same rule, no line 3/20/9/11/14/16/18
    entry can be negative."""
    for item in items:
        for field in ("rents_received_cents", "total_expenses_cents",
                      "prior_year_unallowed_loss_cents", "amount_at_risk_cents",
                      "insurance_cents", "management_fees_cents", "repairs_cents",
                      "taxes_cents", "building_basis_cents", "five_year_property_basis_cents"):
            value = item.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value < 0:
                raise FactsSchemaError(
                    "a Schedule E amount is negative — no line 3, 9, 11, 14, 16 or 20 entry "
                    "can be one (a loss appears on line 21, computed, never typed), no "
                    "depreciable basis can be one, the Form 8582 prior years' unallowed loss "
                    "is entered as a positive amount, and the Form 6198 amount at risk is "
                    "entered as not less than zero. The schema says minimum 0; send the "
                    "figures the form shows.")


def refuse_unsupported_rental_answers(items: list) -> None:
    """The rentals loss gate — the same shape as Schedule C's where the rule is
    the same, and deliberately NOT where the engine differs. RETIRED: the sentence that
    stood here ("`fully_at_risk` false is refused — the simplified Form 6198 amount-at-risk
    intake is not asked — coverable with one field, the STREAM-COVERAGE-COST follow-up"): that
    one field is asked now, and a false computes the loss capped at it.
    `active_participation` false is NEVER refused: the pinned
    engine models the Form 8582 suspension, so a No computes an honest return with the loss
    suspended. RETIRED: the sentence that stood here ("`self_rental` is refused: a
    self-rental profit is recharacterized non-passive only together with the lessee-participation
    answer, and multiple properties are representable, so carrying the type code while ignoring
    the rule could let that profit absorb another property's passive loss in the §8582 netting")
    and the refusal under it ("a self-rental … is not in the covered set: its profit is treated
    as non-passive only together with the material-participation answer for the lessee business,
    which is not asked"): that answer IS asked now, so the type code maps, the flag is derived
    from it, and the §8582 netting the sentence feared is exactly what the ask prevents."""
    for i, item in enumerate(items):
        refuse_off_population_lessee_participation(i, item)
        require_lessee_participation(i, item)
        refuse_lessee_answer_contradicting_type_7(i, item)
        # the expense-shape mutual exclusivity, then the depreciation-input pairs — each
        # a question only once its own arming answer is given, off-population otherwise.
        refuse_mixed_rental_expense_shapes(i, item)
        refuse_off_population_building_class(i, item)
        require_building_class(i, item)
        refuse_off_population_standard_gds(i, item)
        require_standard_gds(i, item)
        refuse_off_population_placed_in_service_flag(i, item)
        refuse_off_population_placed_in_service_month(i, item)
        require_placed_in_service_month(i, item)
        refuse_off_population_five_year_basis(i, item)
        require_five_year_basis(i, item)
        loss = rental_current_net_cents(item) < 0
        refuse_off_population_at_risk_amount("rentals", i, item, loss,
                                             "the at-risk answer for this rental")
        if loss and "fully_at_risk" not in item:
            raise FactsSchemaError(
                f"rentals[{i}].fully_at_risk is a question when the property's year is a loss, "
                f"not a default — answer it (prepare_return asks it as a gap)")
        require_at_risk_amount("rentals", i, item, loss,
                               "the at-risk answer for this rental")
        if rental_combined_net_cents(item) < 0 and "active_participation" not in item:
            raise FactsSchemaError(
                f"rentals[{i}].active_participation is a question when the property's net "
                f"(after any prior unallowed loss) is a loss, not a default — answer it "
                f"(prepare_return asks it as a gap)")
        refuse_off_population_loss_arose_participation(i, item)
        require_loss_arose_participation(i, item)


ESTATE_TRUST_PARTICIPATION = "/writableEstateTrustK1MateriallyParticipated"
ESTATE_TRUST_AT_RISK = "/writableEstateTrustFullyAtRisk"
ESTATE_TRUST_AT_RISK_AMOUNT = "/writableEstateTrustAmountAtRisk"


def refuse_conflicting_estate_trust_participation(items: list) -> None:
    """The dictionary asks this ONCE for the return, not once per form, so two Schedule K-1s
    (Form 1041) that answer it differently cannot both be sent — refused by name rather than one
    of them silently winning."""
    for field, said in (("materially_participated", "material participation"),
                        ("fully_at_risk", "whether the investment is at risk"),
                        ("amount_at_risk_cents", "how much is at risk")):
        answers = {item.get(field) for item in items
                   if item.get("source") == "estate_trust" and field in item}
        if len(answers) > 1:
            raise ServiceFactsError(
                f"two Schedule K-1s (Form 1041) answer {said} differently, and this return "
                f"carries one answer for all of them; refused rather than taking one and "
                f"dropping the other")


def k1_has_box1_loss(item: dict) -> bool:
    """The K-1 loss-gate condition, shared by the asks (`gaps.gaps_for`) and the refusal
    backstop below: box 1 as printed is negative. SIGNED input — the one stream where the
    figure itself carries the sign, so there is no arithmetic to share, only the comparison."""
    v = item.get("ordinary_business_income_cents")
    return isinstance(v, int) and not isinstance(v, bool) and v < 0


# The three K-1 forms, and which service fields each can carry — the fields outside a form's set
# are REFUSED on that form by name (never dropped), because the printed schedule has no box for
# them: item D and box 14 are Form 1065 items; royalties is carried for the 1065's box 7 only;
# the 1041 K-1 has no loss-limit intake at the pin (its box 6 loss is refused outright below).
_K1_FORM_LABELS = {"partnership": "Schedule K-1 (Form 1065)",
                   "s_corp": "Schedule K-1 (Form 1120-S)",
                   "estate_trust": "Schedule K-1 (Form 1041)"}
_K1_FIELDS_NOT_ON = {
    "partnership": frozenset(),
    "s_corp": frozenset({"publicly_traded_partnership", "se_earnings_cents",
                         "royalties_cents", "guaranteed_payments_services_cents",
                         "guaranteed_payments_capital_cents", "general_partner",
                         "qualified_ptp_income_cents", "qualified_ptp_is_sstb",
                         "ptp_prior_year_unallowed_loss_cents",
                         "deductible_se_loss_cents"}),
    # `materially_participated`, `fully_at_risk` and `amount_at_risk_cents` LEFT this set
    # (2026-09-22). The dictionary DOES carry both limits for this form — the sentence that stood
    # here said otherwise and was stale. MEASURED on the pinned engine: a box 6 loss of 5,000.00 is
    # deducted whole on a yes and SUSPENDED on a no, and with the answer absent it deducts as
    # entered; and `profile-estate-atrisk` reaches its oracle on EVERY served line once the
    # at-risk pair is sent (it was a named profile gap until then). BASIS stays here: the 1041
    # K-1 has no basis-limit intake at the pin.
    "estate_trust": frozenset({"publicly_traded_partnership", "se_earnings_cents",
                               "royalties_cents", "basis_cents",
                               "guaranteed_payments_services_cents",
                               "guaranteed_payments_capital_cents", "general_partner",
                               "qualified_ptp_income_cents", "qualified_ptp_is_sstb",
                               "ptp_prior_year_unallowed_loss_cents",
                               "deductible_se_loss_cents", "section_199a_qbi_cents"}),
}
# box 20 code Z's three answers. They belong to ONE population — a Schedule K-1 (Form
# 1065) whose item D is checked — and are refused everywhere else by name, because a code Z
# amount from a partnership that is not publicly traded is per-business qualified business
# income (`qbi:/qualifiedBusinesses`), which the service carries as `section_199a_qbi_cents`.
_K1_PTP_CODE_Z_FIELDS = ("qualified_ptp_income_cents", "qualified_ptp_is_sstb",
                         "ptp_prior_year_unallowed_loss_cents")
# the two guaranteed-payment boxes; printed on the Form 1065 K-1 only.
_K1_GUARANTEED_FIELDS = ("guaranteed_payments_services_cents",
                         "guaranteed_payments_capital_cents")


def k1_has_guaranteed_payment(item: dict) -> bool:
    """A box 4a or 4b amount above zero — the dictionary's own SE-assessment gate keys on
    exactly this (boxes 4a+4b > 0), so a reported 0 asks nothing."""
    return any(isinstance(item.get(f), int) and not isinstance(item.get(f), bool)
               and item.get(f) > 0 for f in _K1_GUARANTEED_FIELDS)


def k1_has_se_loss(item: dict) -> bool:
    """a Form 1065 K-1 whose box 14 code A is ANSWERED and NEGATIVE — the one population
    the deductible part of the loss belongs to. The source test is part of it: the other two
    forms print no box 14, and answering box 14A there is already refused by name."""
    value = item.get("se_earnings_cents")
    return (item.get("source") == "partnership" and isinstance(value, int)
            and not isinstance(value, bool) and value < 0)


# the qualified business members, prefix c5 (the synthetic workbook's own, and clear of
# the Schedule C ids `_uuid("c", i)` make).
def _qbi_member_id(i: int) -> str:
    return f"c5{i:06x}-0000-4000-8000-{i:012x}"


def _qualified_business_members(f: dict, facts: dict) -> list:
    """one `/qualifiedBusinesses` member per K-1 whose section 199A statement reports
    qualified business income, carrying the statement's amount; and, once there is one, one
    member per Schedule C LINKED to it (`linkedScheduleC`, amount unsent so the dictionary's own
    derivation figures it) — because a non-empty list switches `/qbiSimplifiedAmount` from the
    return-level Schedule C derivation to the members' sum, and a Schedule C with no member
    would drop out of the deduction. No K-1 amount above 0: the list stays EMPTY and the return
    is byte-identical to the one before this statement was carried (a statement answered 0
    changes nothing).

    A statement LOSS where it is the only qualified business on the return moves no served line
    (the deduction floors at 0 on Form 8995 line 4), so the list stays empty. Beside another
    business it would be netted against that one's income, and it counts only to the extent
    the K-1 loss is allowed this year (basis, at-risk, passive limits) — a tie the dictionary
    does not carry — so that return is refused by name."""
    k1s = facts.get("k1s") or []
    asked = section_199a_asked(facts)
    for i, item in enumerate(k1s):
        if "section_199a_qbi_cents" in item and i not in asked:
            raise ServiceFactsError(
                f"k1s[{i}].section_199a_qbi_cents is answered on a Schedule K-1 that is not "
                f"asked it — it belongs to a partnership that is not publicly traded, or an S "
                f"corporation, whose box 1 reports business income (a loss only beside other "
                f"business income; a publicly traded partnership's statement amount is "
                f"qualified_ptp_income_cents); refused rather than routed on a guess")
    for i in asked:
        qbi = k1s[i].get("section_199a_qbi_cents")
        if qbi is None:
            # Nothing in the dictionary refuses silence: an empty /qualifiedBusinesses takes
            # no K-1 income at all, so an unanswered statement is the deduction quietly
            # forgone (measured: 1,760.00 of tax on 40,000.00 of box 1).
            raise FactsSchemaError(
                f"k1s[{i}].section_199a_qbi_cents (the qualified business income on this "
                f"K-1's section 199A statement) is a question on every partnership or S "
                f"corporation K-1 whose box 1 reports business income, not a default — answer "
                f"it, 0 if the statement reports none (prepare_return asks it as a gap)")
        se = k1s[i].get("se_earnings_cents")
        if qbi > 0 and isinstance(se, int) and not isinstance(se, bool) and se > 0:
            # The statement's figure is not this return's QBI here, and the dictionary has
            # nothing that turns it into that — acknowledged, never figured.
            raise ServiceFactsError(
                f"k1s[{i}].section_199a_qbi_cents is reported beside self-employment earnings "
                f"in box 14 code A — the statement's amount is reduced by the deductible part "
                f"of self-employment tax attributable to the business before it is qualified "
                f"business income, and that reduction is not in the covered set; refused "
                f"rather than figured on the larger amount")
    amounts = [(i, k1s[i]["section_199a_qbi_cents"]) for i in asked
               if k1s[i]["section_199a_qbi_cents"]]
    schedule_cs = facts.get("schedule_c") or []
    if any(amount < 0 for _, amount in amounts) and (
            schedule_cs or any(amount > 0 for _, amount in amounts)):
        raise ServiceFactsError(
            "a Schedule K-1's section 199A statement reports a qualified business loss beside "
            "another business's qualified business income — the loss is netted against that "
            "income only to the extent the K-1 loss itself is allowed this year (basis, "
            "at-risk and passive limits), and that tie is not in the covered set; refused "
            "rather than netted as entered")
    if not any(amount > 0 for _, amount in amounts):
        return []
    ids = []
    for n, (i, amount) in enumerate(amounts):
        cid = _qbi_member_id(n)
        ids.append(cid)
        f[f"/qualifiedBusinesses/#{cid}/writableQualifiedBusinessIncome"] = _dollar(amount)
    for j in range(len(schedule_cs)):
        cid = _qbi_member_id(len(amounts) + j)
        ids.append(cid)
        f[f"/qualifiedBusinesses/#{cid}/linkedScheduleC"] = _collection_item(_uuid("c", j))
    return ids


def _k1_box1(item: dict) -> int:
    box1 = item.get("ordinary_business_income_cents")
    return box1 if isinstance(box1, int) and not isinstance(box1, bool) else 0


def _k1_section_199a_population(item: dict) -> bool:
    """A partnership K-1 whose item D says it is NOT publicly traded, or an S corporation K-1,
    with a box 1 figure other than 0 — the K-1s whose section 199A statement can report
    per-business qualified business income. A PTP's statement amount is box 20 code Z (`qualified_ptp_income_cents`); an estate or trust K-1 is outside it."""
    source = item.get("source")
    if source == "partnership" and item.get("publicly_traded_partnership") is not False:
        return False
    return source in ("partnership", "s_corp") and _k1_box1(item) != 0


def section_199a_asked(facts: dict) -> list:
    """the K-1 indices whose section 199A statement is ASKED. Every K-1 in the population
    with box 1 INCOME; one with a box 1 LOSS only where the return has other business income the
    statement's loss would be netted against (a Schedule C, or an income K-1 in the population)
    — alone, a qualified business loss moves no served line (Form 8995 line 4 floors at 0)."""
    k1s = (facts.get("k1s") or []) if isinstance(facts, dict) else []
    population = [i for i, item in enumerate(k1s)
                  if isinstance(item, dict) and _k1_section_199a_population(item)]
    other_income = bool(facts.get("schedule_c")) or any(_k1_box1(k1s[i]) > 0 for i in population)
    return [i for i in population if _k1_box1(k1s[i]) > 0 or other_income]


def refuse_negative_k1_amounts(items: list) -> None:
    """The negative-amount posture, eighth stream — for the UNSIGNED boxes only. Box 1/box 6 and
    box 14A are SIGNED as printed (a loss is the box's own statement, not an impossible number), so
    they pass. So is `deductible_se_loss_cents`, which is a NEGATIVE amount on nearly every
    return that answers it: box 14A's negative used to be stopped by the engine's own knockout
    (/knockoutK1NegativeSeEarnings), and now the deductible part of the loss is ASKED
    instead — the partner's own already-limited figure, which the return then computes with."""
    for item in items:
        for field in ("interest_income_cents", "dividend_income_cents",
                      "qualified_dividends_cents", "royalties_cents", "basis_cents",
                      "amount_at_risk_cents",
                      *_K1_GUARANTEED_FIELDS):
            value = item.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value < 0:
                raise FactsSchemaError(
                    "a Schedule K-1 amount is negative in a box that cannot print one — only "
                    "the ordinary business income and self-employment earnings boxes print a "
                    "(loss). The schema says minimum 0; send the figures the form shows.")
        # the §469(k) carry-in is not a box — it is last year's suspended loss, stored as
        # a positive magnitude and SUBTRACTED (the dictionary's own Min $0). A negative would be
        # added back as a gain, so it gets its own words rather than the box sentence above.
        carry_in = item.get("ptp_prior_year_unallowed_loss_cents")
        if (isinstance(carry_in, int) and not isinstance(carry_in, bool) and carry_in < 0):
            raise FactsSchemaError(
                "the prior-year unallowed loss from a publicly traded partnership is negative "
                "— it is entered as a positive amount, the size of the loss being carried "
                "forward. The schema says minimum 0; send the amount the prior year suspended.")


def refuse_unsupported_k1_answers(items: list) -> None:
    """The K-1 gate. Per-form vocabulary first: a field
    the printed form has no box for is refused by name. Then the loss rules, measured at the
    pin: the partnership/s_corp loss trio is asked (a No on material participation is COMPUTED
    — the engine models the Form 8582 suspension); RETIRED: the clause that stood here
    ("`fully_at_risk` false is refused — the simplified Form 6198 amount-at-risk intake is not
    asked") — that intake is asked now, and a false computes the basis-allowed loss capped at
    it; an estate_trust box 6 loss is
    refused — measured, it would deduct as entered, and the passive-activity classification
    that would limit it is not asked."""
    for i, item in enumerate(items):
        source = item.get("source")
        for field in sorted(_K1_FIELDS_NOT_ON.get(source, frozenset())):
            if field in item:
                label = _K1_FORM_LABELS[source]
                if field == "royalties_cents":
                    why = ("royalties are carried at the pin for the Form 1065 K-1's box 7 "
                           "only")
                elif field in ("materially_participated", "basis_cents", "fully_at_risk",
                               "amount_at_risk_cents"):
                    why = f"the {label} loss limits are not carried at the pin"
                else:
                    why = f"the {label} prints no such item"
                raise ServiceFactsError(
                    f"k1s[{i}].{field} is answered on a {label} — {why}; refused rather than "
                    f"dropped")
        box1_loss = k1_has_box1_loss(item)
        refuse_off_population_at_risk_amount("k1s", i, item, box1_loss,
                                             "the at-risk answer for this activity")
        qualified = item.get("qualified_dividends_cents")
        ordinary = item.get("dividend_income_cents")
        if (isinstance(qualified, int) and not isinstance(qualified, bool) and
                qualified > (ordinary if isinstance(ordinary, int)
                             and not isinstance(ordinary, bool) else 0)):
            raise FactsSchemaError(
                "qualified dividends exceed ordinary dividends on this K-1 — the qualified "
                "box is a slice of the ordinary one on all three forms; send the figures the "
                "form shows.")
        others = [other for j, other in enumerate(items) if j != i]
        unclassified = [j for j, other in enumerate(items) if j != i
                        and other.get("source") in ("partnership", "s_corp")
                        and not k1_has_box1_loss(other) and "materially_participated" not in other]
        if source == "estate_trust" and k1_has_box1_loss(item) and unclassified:
            # MEASURED on profile-passive-netting: a suspended passive loss is NETTED against
            # passive income from another activity, and whether that activity's income IS passive
            # turns on ITS material participation. That is asked now of a partnership or S
            # corporation K-1 with a profit beside a loss — so a missing answer is a
            # question, not a default.
            raise FactsSchemaError(
                f"k1s[{unclassified[0]}].materially_participated is a question when another K-1 "
                f"on the return reports a loss — whether its income is passive decides how much "
                f"of that loss is allowed; answer it (prepare_return asks it as a gap)")
        if source == "estate_trust" and k1_has_box1_loss(item) and any(
                other.get("source") not in ("partnership", "s_corp") for other in others):
            # Another estate or trust K-1 beside this loss: its participation is ONE return-level
            # answer at the pin, shared by every Form 1041 K-1, so two cannot be classified apart.
            raise ServiceFactsError(
                "a Schedule K-1 (Form 1041) box 6 loss beside another Schedule K-1 (Form 1041) "
                "is not in the covered set: material participation is one answer for every estate "
                "or trust K-1 on the return at this version, so the two activities cannot be told "
                "apart, and that decides how much of this loss is allowed this year; refused "
                "rather than suspending the whole loss")
        if source == "estate_trust" and k1_has_box1_loss(item) and "materially_participated" not in item:
            # …and the answer is what makes the loss computable: without it the engine deducts it
            # as entered (measured), so this stays a refusal for an UNANSWERED loss only.
            raise FactsSchemaError(
                f"k1s[{i}].materially_participated is a question when box 6 of a Schedule K-1 "
                f"(Form 1041) is a loss, not a default — it decides whether the loss is allowed "
                f"or suspended; answer it (prepare_return asks it as a gap)")
        if source in ("partnership", "s_corp") and box1_loss:
            for field in ("materially_participated", "basis_cents", "fully_at_risk"):
                if field not in item:
                    raise FactsSchemaError(
                        f"k1s[{i}].{field} is a question when box 1 is a loss, not a "
                        f"default — answer it (prepare_return asks it as a gap)")
            # last of the loss trio's questions because it sits BEHIND the at-risk
            # answer: the amount is asked only once that answer is a No.
            require_at_risk_amount("k1s", i, item, box1_loss,
                                   "the at-risk answer for this activity")
        # and it comes BEFORE the item D backstop below on purpose: when a code Z
        # answer is present, the field that has to move is the code Z one or item D, and the
        # refusal has to name both rather than only the one that happens to be missing.
        answered_code_z = [f for f in _K1_PTP_CODE_Z_FIELDS if f in item]
        if (source == "partnership" and answered_code_z
                and item.get("publicly_traded_partnership") is not True):
            named = ", ".join(f"k1s[{i}].{f}" for f in answered_code_z)
            if item.get("publicly_traded_partnership") is False:
                raise ServiceFactsError(
                    f"{named} is answered on a Schedule K-1 (Form 1065) whose item D says the "
                    f"partnership is not publicly traded — a box 20 code Z amount from a "
                    f"partnership that is not a PTP is per-business qualified business income, "
                    f"answered as k1s[{i}].section_199a_qbi_cents; refused rather than "
                    f"routed to the publicly traded partnership half of Form 8995 line 6")
            raise ServiceFactsError(
                f"{named} is answered on a Schedule K-1 (Form 1065) whose item D is "
                f"unanswered — k1s[{i}].publicly_traded_partnership decides whether this is "
                f"qualified PTP income or per-business qualified business income (an intake "
                f"not in the covered set), so it is answered first; refused rather than "
                f"routed on a guess")
        if (source == "partnership" and item.get("publicly_traded_partnership") is True
                and "qualified_ptp_income_cents" not in item):
            # the ask on every PTP K-1. Nothing in the dictionary refuses silence here —
            # the complete-safe alias resolves $0 — so an unanswered box 20 code Z is a
            # qualified business income deduction quietly forgone with nothing on the return to
            # show it. The gap asks; this is its backstop. 0 is an answer.
            raise FactsSchemaError(
                f"k1s[{i}].qualified_ptp_income_cents (box 20 code Z, the section 199A "
                f"statement) is a question on every K-1 whose item D is checked, not a default "
                f"— answer it, 0 if the statement reports no qualified PTP amount "
                f"(prepare_return asks it as a gap)")
        if (source == "partnership" and item.get("publicly_traded_partnership") is True
                and "qualified_ptp_is_sstb" not in item):
            # the ask beside the amount, and it is ASKED for the reason the amount is.
            # Nothing in the dictionary refuses silence — `/writableQualifiedPtpIsSstb` is
            # optional and an unanswered flag leaves the qualified amount whole. That was
            # inert while the deduction routed $0 above the section 199A threshold; with Form
            # 8995-A computing it became the taxpayer-FAVOURABLE guess (the full 20% where
            # the law may allow the applicable percentage or nothing), reaching Form 1040
            # line 15. The gap asks; this is its backstop.
            raise FactsSchemaError(
                f"k1s[{i}].qualified_ptp_is_sstb (whether the partnership is a specified "
                f"service trade or business) is a question on every K-1 whose item D is "
                f"checked, not a default — answer it true or false (prepare_return asks it "
                f"as a gap)")
        if source == "partnership" and "publicly_traded_partnership" not in item:
            raise FactsSchemaError(
                f"k1s[{i}].publicly_traded_partnership (item D) is a question on every "
                f"partnership K-1, not a default — answer it (prepare_return asks it as a "
                f"gap)")
        if source == "partnership" and "general_partner" not in item:
            # item G, the same shape as item D. The engine's own default (limited
            # partner) is the taxpayer-adverse one on purpose; silence must not reach it.
            raise FactsSchemaError(
                f"k1s[{i}].general_partner (item G) is a question on every partnership K-1, "
                f"not a default — answer it (prepare_return asks it as a gap)")
        if (source == "partnership" and k1_has_guaranteed_payment(item)
                and "se_earnings_cents" not in item):
            # the dictionary's SE-assessment gate — a guaranteed payment with box 14
            # unanswered resolves Result.Incomplete, which the pinned runner discards; the
            # service asks the question and refuses to compute without the answer (0 counts).
            raise FactsSchemaError(
                f"k1s[{i}].se_earnings_cents (box 14 code A) is a question once a guaranteed "
                f"payment is reported, not a default — answer it, 0 for a blank box "
                f"(prepare_return asks it as a gap)")
        # the deductible part of a box 14 code A LOSS. Off-population refusals first
        # (the wrong form is already refused above by the per-form vocabulary loop), then the
        # range, then the backstop — the order the filer meets them in.
        if "deductible_se_loss_cents" in item and not k1_has_se_loss(item):
            if "se_earnings_cents" not in item:
                raise ServiceFactsError(
                    f"k1s[{i}].deductible_se_loss_cents is answered on a Schedule K-1 (Form "
                    f"1065) whose box 14 code A is unanswered — box 14A is answered first: "
                    f"whether there is a deductible part at all, and the range it may lie "
                    f"in, are the printed figure's own; refused rather than routed on a guess")
            raise ServiceFactsError(
                f"k1s[{i}].deductible_se_loss_cents is answered on a Schedule K-1 (Form 1065) "
                f"whose box 14A is not a loss, so its deductible part is not a question — the "
                f"printed instruction asks for a deductible amount only where the box is a "
                f"loss, and a box that is not one is taken as entered; refused rather than "
                f"dropped")
        if k1_has_se_loss(item):
            answer = item.get("deductible_se_loss_cents")
            if answer is None:
                # The gap asks; this is its backstop. Unanswered, the dictionary's own
                # /formK1s/*/seEarningsAllowed is Result.Incomplete and the return refuses —
                # so the service asks the question instead of serving a refusal.
                raise FactsSchemaError(
                    f"k1s[{i}].deductible_se_loss_cents (the deductible part of the box 14 "
                    f"code A loss) is a question on every Schedule K-1 (Form 1065) whose box "
                    f"14 code A is a loss, not a default — answer it, 0 if none of the loss "
                    f"is deductible this year (prepare_return asks it as a gap)")
            if not (item["se_earnings_cents"] <= answer <= 0):
                # A FIELD ERROR, not a refusal of the return: the entry contradicts the box it
                # comes from. The dictionary fences both ends and deliberately carries NO Limit
                # element — a clamp would rewrite a contradictory entry into a plausible one —
                # so an out-of-range answer costs a blocked return, and catching it here is
                # kinder. the rule, never the submitted figure.
                raise FactsSchemaError(
                    f"k1s[{i}].deductible_se_loss_cents is outside the range box 14 code A "
                    f"allows. Must be between the box 14 code A loss and 0")


# The seven dependent qualifiers this service ASKS (gaps first, this backstop second). The
# benefit-split question is asked for child-category relationships only — measured: a
# non-child dependent completes without it.
DEPENDENT_ASKED_FIELDS = ("relationship", "months_in_home", "is_married",
                          "provided_own_support", "gross_income_under_limit",
                          "filer_provided_over_half_support",
                          "could_be_qualifying_child_of_another")

# every field that is a question about a CLAIMED DEPENDENT and nobody else — the asked
# seven above, the child-only tie-breaker (`is_blind`'s mirror: asked on a child row, a gap there),
# and the keeping-up-home answer. Derived, not retyped, so the set the guard refuses on
# a filer row cannot drift from the set the gap surface asks on a dependent row. Two dependent-
# only sets live OUTSIDE it by design, each refused on a filer row by its own chain guard
# (measured): the joint-return trio and the benefit-split five.
DEPENDENT_ONLY_FIELDS = frozenset(DEPENDENT_ASKED_FIELDS) | {
    "has_other_biological_or_adoptive_parent", "filer_paid_most_of_home_upkeep",
    "child_parents_living"}


def refuse_unsupported_dependent_answers(persons: list) -> None:
    """The dependents gate. Two chains, two named refusals
    and a backstop; everything else asked is a gap first.

    RETIRED: the refusal that stood first here — "a married dependent is not in the
    covered set: the joint-return test needs the dependent's own filing answers, which are
    not asked — refused rather than assumed unmarried". The dictionary asks those answers;
    they are `DEPENDENT_JOINT_RETURN_CHAIN` now, and a failed joint-return test is a COMPUTED
    outcome — the person is simply not claimed — never a refusal.

    RETIRED: the one that stood second — "this child has another biological or adoptive
    parent — the rule for children of divorced or separated parents (custody nights, the
    higher-AGI comparison, Form 8332's written declaration) is not asked, and a claim cannot
    be computed without it". The dictionary asks that rule's GATE too: it is
    `DEPENDENT_BENEFIT_SPLIT_CHAIN` now, five answers on the filer's own biological or adopted
    child, and any one of them that closes the gate is a COMPUTED outcome — measured at the
    pin, every served line identical to the ordinary-rules baseline to the cent. What is left
    refused now is ONE tier, named by its cause: the non-parental rule for a claimed
    dependent the filer is not the parent of whose own parents are living (a yes to that
    question). The
    custodial-parent questions a written declaration opens were the other tier until the service made
    them the chain's last two links — every outcome there is the engine's own, computed or
    knocked out.
    """
    # the spouse-chain shape: an answer the chain does not reach is refused BY NAME, never
    # dropped. Every row, not the dependent rows only — the joint-return test is a
    # dependent's test, so one of these three on a FILER row is an answer about somebody who
    # is not being claimed, and accepting it would let a caller believe it counted.
    for i, person in enumerate(persons):
        if not isinstance(person, dict):
            continue
        reached = dependent_joint_return_questions_reached(person)
        for field, _unlock in DEPENDENT_JOINT_RETURN_CHAIN:
            if field not in person or field in reached:
                continue
            if person.get("role") != "dependent":
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered on a filer row — the joint-return "
                    f"test is asked of a married dependent only, and this return's own "
                    f"marital status is `filing_status`; refused rather than dropped")
            if person.get("is_married") is not True:
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered for a dependent who is not answered "
                    f"married — the joint-return test is asked only once `is_married` is "
                    f"true; refused rather than dropped")
            raise ServiceFactsError(
                f"persons[{i}].{field} is answered but the joint-return chain does not reach "
                f"it with the answers given (a dependent who files no joint return, or who "
                f"is required to file one, has already settled the test); refused rather "
                f"than dropped")
    # the two tiers the benefit-split gate leaves refused, and the gate's own
    # unreached-answer refusal. Ordered before the backstops below for the same reason the
    # joint-return one is: a coverage boundary is a different answer from a missing field, and
    # the caller who meets it cannot fix it by sending the row again.
    # RETIRED: the sentence that stood here for a stepchild, foster child or grandchild with
    # another legal parent — "… on a row where the filer is not this child's parent — the rule
    # for a child whose own parents are living but who is claimed by someone else is not asked,
    # and a claim cannot be computed without it". The engine never read that answer on such a
    # row (its one reader requires `tpIsParent`), so it is an UNASKED answer there, refused as
    # such; the non-parental tier's one sentence is the parents-living yes.
    # the split gate's custody questions: an answer the chain does not reach is refused by
    # name, on any row.
    for i, person in enumerate(persons):
        if not isinstance(person, dict):
            continue
        reached = child_custody_questions_reached(person)
        for field in CHILD_CUSTODY_FIELDS:
            if field not in person or field in reached:
                continue
            if person.get("role") != "dependent":
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered on a filer row — the custody questions "
                    f"are asked about a claimed dependent only; refused rather than dropped")
            raise ServiceFactsError(
                f"persons[{i}].{field} is answered, and the engine does not ask it for this "
                f"person with the answers given: the state the child lived in is asked of "
                f"a claimed dependent with a qualifying-child relationship who is 18 or older "
                f"at the end of the year and is not answered permanently and totally disabled; "
                f"whether the child was emancipated, once the child is at or over that state's "
                f"age of majority; and whether that was after July 2, on a yes; refused rather "
                f"than dropped")
    for i, person in enumerate(persons):
        if not isinstance(person, dict) or person.get("role") != "dependent":
            continue
        if ("has_other_biological_or_adoptive_parent" in person
                and not other_parent_question_armed(person)):
            raise ServiceFactsError(
                f"persons[{i}].has_other_biological_or_adoptive_parent is answered, and the "
                f"engine does not ask it for this person: whether a child has another living "
                f"biological or adoptive parent is read only where the filer is that child's "
                f"biological or adoptive parent and the child can still be in a parent's "
                f"custody — under 18 at the end of the year, under the age of majority of the "
                f"state the child lived in, not emancipated, or permanently and totally "
                f"disabled; refused rather than dropped")
    for i, person in enumerate(persons):
        if not isinstance(person, dict):
            continue
        reached = dependent_benefit_split_questions_reached(person)
        reached_nonparental = dependent_nonparental_split_questions_reached(person)
        for field, _alive in DEPENDENT_BENEFIT_SPLIT_CHAIN:
            if field not in person or field in reached or field in reached_nonparental:
                continue
            if person.get("role") != "dependent":
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered on a filer row — the benefit-split "
                    f"questions are asked about a claimed child only; refused rather than "
                    f"dropped")
            if person.get("has_other_biological_or_adoptive_parent") is not True:
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered for a child who is not answered as "
                    f"having another living biological or adoptive parent — the benefit-split "
                    f"questions are asked only once that answer is yes; refused rather than "
                    f"dropped")
            raise ServiceFactsError(
                f"persons[{i}].{field} is answered but the benefit-split questions do not "
                f"reach it with the answers given (an answer that leaves the child claimed "
                f"under the ordinary rules has already settled the gate); refused rather than "
                f"dropped")
        # RETIRED: the refusal that stood here for `i_did` / `they_did` ("… the split's
        # custodial-parent questions, nights with each parent and the higher adjusted gross
        # income, are not asked here, and the engine withdraws the figure one answer later;
        # refused rather than served"): they are the chain's last two links now.
    for i, person in enumerate(persons):
        if not isinstance(person, dict) or person.get("role") != "dependent":
            continue
        for field in DEPENDENT_ASKED_FIELDS:
            if field == "has_other_biological_or_adoptive_parent":
                continue
            if field not in person:
                raise FactsSchemaError(
                    f"persons[{i}].{field} is a question on every claimed dependent, not a "
                    f"default — answer it (prepare_return asks it as a gap)")
        if (other_parent_question_armed(person)
                and "has_other_biological_or_adoptive_parent" not in person):
            raise FactsSchemaError(
                f"persons[{i}].has_other_biological_or_adoptive_parent is a question on "
                f"every claimed child of the filer's own, not a default — answer it "
                f"(prepare_return asks it as a gap)")
        # the non-parental arm's first question — refused by name off the rows the engine
        # asks it of; a YES refused by name as the non-parental tier (the split's own questions
        # for a child whose parents are living are not asked, and the claim never resolves
        # without them); backstopped by name when the row is asked and has not answered.
        if "child_parents_living" in person and not parents_living_question_armed(person):
            raise ServiceFactsError(
                f"persons[{i}].child_parents_living is answered, and the engine does not ask it "
                f"for this person: whether the child's own parents are living is asked of "
                f"{NON_PARENT_QC_IN_WORDS} who can still be in a parent's custody — under 18 "
                f"at the end of the year, under the age of majority of the state the child "
                f"lived in, not emancipated, or permanently and totally disabled; refused "
                f"rather than dropped")
        # RETIRED: the refusal that stood here for a YES ("… the non-parental rule for such a
        # child (whether a parent is claiming them, whose adjusted gross income is higher) is
        # not asked, and the claim cannot be computed without it; refused rather than assumed"):
        # the rule is `DEPENDENT_NONPARENTAL_SPLIT_CHAIN` now. An answer the chain does not
        # reach is refused by name; a reached link left unanswered is backstopped by name.
        reached_np = dependent_nonparental_split_questions_reached(person)
        for field, _alive in DEPENDENT_NONPARENTAL_SPLIT_CHAIN:
            if field == "child_in_parents_custody":
                continue                      # the split gate's field; its own guard above covers it
            if field in person and field not in reached_np:
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered but the non-parental split's questions "
                    f"do not reach it with the answers given (they are asked of a child the "
                    f"filer is not the parent of whose own parents are living, one at a time, "
                    f"and an answer that leaves the child claimed under the ordinary rules has "
                    f"already settled it); refused rather than dropped")
        for field in reached_np:
            if field not in person:
                raise FactsSchemaError(
                    f"persons[{i}].{field} is a question on this dependent row — the filer is "
                    f"not this child's parent and the child's own parents are living — not a "
                    f"default; answer it (prepare_return asks it as a gap)")
        for field in child_custody_questions_reached(person):
            if field not in person:
                raise FactsSchemaError(
                    f"persons[{i}].{field} is a question on this dependent row — the child is "
                    f"18 or older and may still be in a parent's custody — not a default; answer "
                    f"it (prepare_return asks it as a gap)")
        if parents_living_question_armed(person) and "child_parents_living" not in person:
            raise FactsSchemaError(
                f"persons[{i}].child_parents_living is a question on this dependent row — the "
                f"filer is not this child's parent — not a default; answer it (prepare_return "
                f"asks it as a gap)")
        # the joint-return chain's backstop — the same reach function the gap surface
        # asks from, so a link the caller was asked and skipped is refused rather than
        # defaulted. The chain is walked in order, so the FIRST unanswered link is the one
        # named: the questions after it are not reached until this one has an answer.
        for field in dependent_joint_return_questions_reached(person):
            if field not in person:
                raise FactsSchemaError(
                    f"persons[{i}].{field} is a question on this married dependent's row, "
                    f"not a default — answer it (prepare_return asks it as a gap)")
        # the benefit-split gate's backstop, the same shape and the same reason — the
        # reach function the gap surface asks from, walked in order, so the FIRST unanswered
        # link is the one named.
        for field in dependent_benefit_split_questions_reached(person):
            if field not in person:
                raise FactsSchemaError(
                    f"persons[{i}].{field} is a question on this child's row, not a default "
                    f"— answer it (prepare_return asks it as a gap)")


def refuse_dependent_answers_on_a_filer_row(persons: list) -> None:
    """Every field in `DEPENDENT_ONLY_FIELDS` is a question about a CLAIMED DEPENDENT —
    the relationship, residency, support and income tests, the tie-breakers, the keeping-up-home
    answer — and means nothing on the filer's or the spouse's own row: the mapper never emitted
    one from there, so the answer was accepted and silently dropped. That is the class refused
    everywhere else (an answer accepted and dropped lets a caller believe it counted),
    so each is refused BY NAME on a non-dependent row, the mirror of `is_blind` on a
    dependent row."""
    for i, person in enumerate(persons):
        # the filer roles: `primary` / `spouse` and nothing else. The
        # sentence below says "this row is the filer's or the spouse's own", so a row whose
        # role is neither of those (nor `dependent`) must fall through to the role check and
        # be told what is actually wrong with it — its role.
        if not isinstance(person, dict) or person.get("role") not in ("primary", "spouse"):
            continue
        for field in sorted(DEPENDENT_ONLY_FIELDS):
            if field in person:
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered on a filer row — it is a question about "
                    f"a claimed dependent, and this row is the filer's or the spouse's own; "
                    f"refused rather than dropped")


def refuse_misplaced_blindness_answers(persons: list) -> None:
    """Form 1040 line 12 prints a blindness checkbox for the filer and, on a joint
    return, for the spouse — and for nobody else. A DEPENDENT's blindness moves nothing on
    this return (the engine's `/familyAndHousehold` item has no blindness fact at all), so an
    answer on a dependent row is refused by name rather than accepted and dropped: accepting
    it would let a caller believe a checkbox was ticked somewhere."""
    for i, person in enumerate(persons):
        if not isinstance(person, dict):
            continue
        if person.get("role") == "dependent" and "is_blind" in person:
            raise ServiceFactsError(
                f"persons[{i}].is_blind is answered on a dependent row — Form 1040 line 12's "
                f"blindness checkbox is printed for the filer (and, on a joint return, the "
                f"spouse) only, and a dependent's blindness moves nothing on this return; "
                f"refused rather than dropped")


def refuse_misplaced_separate_return_answers(facts: dict) -> None:
    """The separate-return gate (mfs coverage). Both root booleans belong to a
    married-filing-separately return only; on any other status they are refused, never dropped.
    On mfs, `community_property_domicile` true is refused — the Form 8958 community-income
    allocation is not in the covered set, and computing a separate return without it would
    mis-state BOTH spouses' returns (the engine's own three-arm guard for this population
    hangs on a state answer this service never has, so the deciding question is asked HERE);
    both absent on mfs is the backstop below — `gaps.gaps_for` asks first."""
    status = facts.get("filing_status")
    _STATUS_NAMES = {"mfs": "separate (married-filing-separately)",
                     "qss": "qualifying-surviving-spouse",
                     "mfj": "joint (married-filing-jointly)"}
    for owner, fields in STATUS_ROOT_FIELDS.items():
        for field in sorted(fields):
            if field in facts and status != owner:
                raise ServiceFactsError(
                    f"{field} is answered on a {status!r} return — the question belongs to "
                    f"a {_STATUS_NAMES[owner]} return only; refused rather than dropped")
    if status == "mfs":
        # an answer the chain does not reach is refused by name, never dropped — an
        # itemizing spouse files a return (so a files-no answer beside it contradicts, and the
        # engine would read the pair as "not zeroed"), and a spouse who files makes the
        # income/claimable/age/blindness answers moot; silently accepting either would let a
        # caller believe it counted.
        reached = set(mfs_spouse_questions_reached(facts))
        for field, _unlock in MFS_SPOUSE_CHAIN:
            if field in facts and field not in reached:
                if facts.get("spouse_itemizes") is True:
                    raise ServiceFactsError(
                        f"{field} is answered on a return whose spouse itemizes — a spouse who "
                        f"itemizes files a return, so the separate-return spouse questions "
                        f"(spouse_files_return onward) are not reached; refused rather than "
                        f"dropped")
                raise ServiceFactsError(
                    f"{field} is answered but the separate-return spouse chain does not reach "
                    f"it with the answers given (it is asked only once the spouse does not "
                    f"itemize, files no return, had no gross income and cannot be claimed by "
                    f"another, in that order); refused rather than dropped")
        if facts.get("community_property_domicile") is True:
            raise ServiceFactsError(
                "the filer's or their spouse's domicile is in a community property state — "
                "the Form 8958 community-income allocation is not in the covered set, and a "
                "separate return computed without it would mis-state both spouses' returns")
        # The pair, on every separate return; the chain's links only as far as the answers
        # reach — the emission block backstops those with the same function.
        for field in ("community_property_domicile", "spouse_itemizes"):
            if field not in facts:
                raise FactsSchemaError(
                    f"{field} is a question on every married-filing-separately return, not "
                    f"a default — answer it (prepare_return asks it as a gap)")
    if status == "qss":
        for field in sorted(QSS_ROOT_FIELDS):
            if field not in facts:
                raise FactsSchemaError(
                    f"{field} is a question on every qualifying-surviving-spouse return, "
                    f"not a default — answer it (prepare_return asks it as a gap)")
    # the keeping-up-home answer, on the rows the ENGINE asks it of — every dependent row
    # of an hoh/qss return, and on a single return the rows its own screen gate
    # `/familyAndHousehold/*/flowAddPersonKeepingUpHome` asks. `upkeep_question_armed` is that
    # population, and the gap surface imports the same function, so the ask and this backstop
    # can never disagree. Two refusals, because the two ways to be off the population are
    # different facts about the return and the reader deserves the true one.
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict) or person.get("role") != "dependent":
            continue
        armed = upkeep_question_armed(status, person, facts)
        if "filer_paid_most_of_home_upkeep" in person and not armed:
            if status == "single":
                raise ServiceFactsError(
                    f"persons[{i}].filer_paid_most_of_home_upkeep is answered, and the engine "
                    f"does not ask it for this person: the keeping-up-home question reaches a "
                    f"qualifying-child relationship, or a qualifying-relative one with the "
                    f"person in the home more than half the year, and this row is neither; "
                    f"refused rather than dropped")
            raise ServiceFactsError(
                f"persons[{i}].filer_paid_most_of_home_upkeep is answered on a {status!r} "
                f"return — on a married return the keeping-up-home question is asked only once "
                f"the lived-together answers say you lived apart from your spouse for the last "
                f"six months of the year (apart all year, or together six months or less and "
                f"apart the last six), and this return's answers do not; refused rather than "
                f"dropped")
        if "filer_paid_most_of_home_upkeep" not in person and armed:
            raise FactsSchemaError(
                f"persons[{i}].filer_paid_most_of_home_upkeep is a question on this dependent "
                f"row of a {status} return, not a default — answer it (prepare_return asks it "
                f"as a gap)")
    if status in ("hoh", "qss") and not any(
            isinstance(person, dict) and person.get("role") == "dependent"
            for person in facts.get("persons") or []):
        raise ServiceFactsError(
            "a head-of-household or qualifying-surviving-spouse return names a qualifying "
            "person, and none is here — add the person's row (prepare_return asks for it as "
            "a gap)")


def _refuse_unmapped_input(facts: dict) -> None:
    """No fact GROUP the caller sends may be silently dropped. A group this mapper does not map is
    either a known-but-unsupported one (refused by name) or unknown to the schema entirely (refused
    as unknown); a person field outside the schema's set is refused the same way. Ignoring any of
    them would return a number computed as if the caller had not sent it — a silently wrong answer.
    A group is refused whenever it is PRESENT and non-empty, whatever it carries: `{"itemize_when_
    lower": false}` asks for the behaviour we happen to have, but answering it would be a promise
    this service cannot keep for the `true` case, so it is refused too."""
    known = (COVERED_FACT_GROUPS | set(UNSUPPORTED_STREAMS) | set(UNSUPPORTED_FACT_GROUPS)
             | MFS_ROOT_FIELDS | QSS_ROOT_FIELDS | MARRIED_ROOT_FIELDS | MFJ_ROOT_FIELDS
             | EVERY_RETURN_ROOT_FIELDS | ALASKA_PFD_FIELDS)
    unknown = sorted(set(facts) - known)
    if unknown:
        raise ServiceFactsError(
            f"unknown fact group(s) {', '.join(unknown)}: not in the fact schema, and refusing is "
            f"the only honest answer — an ignored input silently changes the return")
    for group in UNSUPPORTED_FACT_GROUPS:
        if facts.get(group):
            raise ServiceFactsError(
                f"{FACT_GROUP_LABELS[group]} ({group}) is accepted by the fact schema but maps "
                f"nowhere in the covered set; refusing rather than dropping it silently")
    for i, p in enumerate(facts.get("persons") or []):
        extra = sorted(set(p) - PERSON_FIELDS)
        if extra:
            raise ServiceFactsError(
                f"persons[{i}] carries field(s) {', '.join(extra)} that are not in the fact "
                f"schema; refusing rather than ignoring them")
    # every other collection, same rule. This runs BEFORE the unsupported-stream refusals so an
    # identifier smuggled into an unsupported stream is reported as what it is, and it covers the one
    # collection that IS mapped (w2s) — which is where the hole actually was.
    for group, allowed in COLLECTION_ITEM_FIELDS.items():
        for i, item in enumerate(facts.get(group) or []):
            if not isinstance(item, dict):
                raise ServiceFactsError(f"{group}[{i}] must be an object")
            extra = sorted(set(item) - allowed)
            if extra:
                raise ServiceFactsError(
                    f"{group}[{i}] carries field(s) {', '.join(extra)} that are not in the fact "
                    f"schema; refusing rather than ignoring them")


def _require_present_and_typed(obj: dict, required: frozenset, where: str) -> None:
    """One object: everything the schema requires is there, and everything present is the right type.

    The two checks live together because they are one question — *did the caller actually tell us
    this?* A field that is absent and a field that is `true` where cents belong are the same defect
    wearing different clothes: both produce a number the caller never supplied."""
    for field_name in sorted(required - set(obj)):
        raise FactsSchemaError(
            f"{where}{field_name} is required and was not supplied. Absence is not zero — if that "
            f"is what you mean, send 0 explicitly. Defaulting it would return a number computed as "
            f"if you had answered when you had not.")
    for field_name in sorted(set(obj) & INTEGER_FACT_FIELDS):
        value = obj[field_name]
        # `isinstance(True, int)` is True in Python; see INTEGER_FACT_FIELDS for the two other
        # places in this service where that would have produced a wrong number.
        if isinstance(value, bool) or not isinstance(value, int):
            raise FactsSchemaError(
                f"{where}{field_name} must be an integer, got {type(value).__name__}. Money is "
                f"integer cents and never a float, a string, or a boolean.")


def _refuse_missing_or_mistyped(facts: dict) -> None:
    """Work item 0b, at the one place every request funnels through.

    Runs AFTER the unknown-key refusals (an identifier smuggled into a W-2 is the more urgent thing
    to report) and BEFORE the numeric refusals, which compare box 3 against box 4 and would raise a
    TypeError — a 500 on a caller fault — if a string reached them."""
    for field_name in sorted(REQUIRED_ROOT_FIELDS - set(facts)):
        raise FactsSchemaError(f"{field_name} is required and was not supplied")
    # the ROOT money answers are typed here too (line 13's carryover and line 14's
    # forfeiture join the estimated payments, the student loan interest and Form 8962 line 2b).
    # Once a string at the root reached the section emitters untyped — a "0" on line 14
    # would have derived the no in silence.
    _require_present_and_typed(facts, frozenset(), "")
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict):
            raise FactsSchemaError(f"persons[{i}] must be an object")
        _require_present_and_typed(person, REQUIRED_PERSON_FIELDS, f"persons[{i}].")
    for group in sorted(REQUIRED_ITEM_FIELDS):
        for i, item in enumerate(facts.get(group) or []):
            _require_present_and_typed(item, REQUIRED_ITEM_FIELDS[group], f"{group}[{i}].")


def map_to_engine(facts: dict, tax_year: int = 2025, *, birth_days: dict | None = None) -> dict:
    """Return the {"facts": {...}} persister object for the engine runner. Raises ServiceFactsError
    for anything outside the Phase-0 covered set (including the age-65 day-ambiguous cohort, unless
    `birth_days` settles it — the local page's own store, never a request field)."""
    filing = facts.get("filing_status")
    if filing not in FILING_STATUSES:
        # sorted(): the served message must be byte-identical run to run (provenance rule 4) —
        # a bare set() renders in PYTHONHASHSEED order.
        raise ServiceFactsError(
            f"filing_status must be one of {', '.join(sorted(FILING_STATUSES))}, got {filing!r}")
    if filing not in COVERED_FILING_STATUSES:
        covered = ", ".join(sorted(COVERED_FILING_STATUSES))
        pending = "/".join(sorted(FILING_STATUSES - COVERED_FILING_STATUSES))
        raise ServiceFactsError(
            f"filing_status {filing!r} is not in the covered set yet (only {covered}); "
            f"{pending} scaffolding is pending")
    _refuse_unmapped_input(facts)
    _refuse_missing_or_mistyped(facts)
    refuse_multiple_employers(facts.get("w2s") or [])
    refuse_negative_w2_amounts(facts.get("w2s") or [])
    refuse_impossible_box4(facts.get("w2s") or [])
    refuse_negative_w2g_amounts(facts.get("w2gs") or [])
    refuse_negative_ssa1099_amounts(facts.get("ssa1099s") or [])
    refuse_misplaced_g1099_repayments(facts.get("g1099s") or [])
    refuse_malformed_hsa_distributions(facts.get(HSA_GROUP) or [])
    refuse_malformed_care_providers(facts.get(CDCC_GROUP) or [])
    refuse_malformed_f1095as(facts.get(PTC_GROUP) or [])
    refuse_negative_int1099_amounts(facts.get("int1099s") or [])
    refuse_malformed_oid1099s(facts.get("oid1099s") or [])                # Form 1099-OID
    refuse_malformed_b1099s(facts.get("b1099s") or [], tax_year)          # Form 1099-B
    refuse_negative_div1099_amounts(facts.get("div1099s") or [])
    refuse_impossible_div_slices(facts.get("div1099s") or [])
    refuse_negative_r1099_amounts(facts.get("r1099s") or [])
    refuse_negative_schedule_c_amounts(facts.get("schedule_c") or [])
    refuse_unsupported_schedule_c_loss_answers(facts.get("schedule_c") or [])
    refuse_negative_rental_amounts(facts.get("rentals") or [])
    refuse_unsupported_rental_answers(facts.get("rentals") or [])
    refuse_negative_k1_amounts(facts.get("k1s") or [])
    refuse_unsupported_k1_answers(facts.get("k1s") or [])
    refuse_conflicting_estate_trust_participation(facts.get("k1s") or [])
    refuse_misplaced_separate_return_answers(facts)
    refuse_dependent_answers_on_a_filer_row(facts.get("persons") or [])
    refuse_unsupported_dependent_answers(facts.get("persons") or [])
    refuse_misplaced_blindness_answers(facts.get("persons") or [])
    refuse_misplaced_educator_answers(facts.get("persons") or [])
    refuse_misplaced_ira_answers(facts)
    persons = facts.get("persons") or []
    if not persons:
        raise ServiceFactsError("at least one person is required")
    # Role arithmetic. A joint return names exactly two filers — one primary, one
    # spouse — and any other status names one. Refused BEFORE the engine call, in the sentence a
    # person can act on; `prepare_return`'s gap for the missing spouse fires earlier still, so a
    # loop-driven caller meets a question, not this refusal.
    # The role words themselves. The schema enumerates three and NEITHER TRANSPORT VALIDATES A
    # REQUEST, so a row answered anything else was once treated as a filer, mapped with
    # `isPrimaryFiler` false, and the return computed — the silent-drop class refused
    # everywhere else. It is named here rather than in the dependent guards so that the row
    # freed from "answered on a filer row" meets a sentence about its role.
    for i, person in enumerate(persons):
        if isinstance(person, dict) and person.get("role") not in ROLES:
            raise ServiceFactsError(
                f"persons[{i}].role is {person.get('role')!r}, which is not one of the three "
                f"answers to \"Who this person is to the return\" — answer `primary`, "
                f"`spouse` or `dependent`")
    filer_roles = [p.get("role") for p in persons
                   if isinstance(p, dict) and p.get("role") != "dependent"]
    if filer_roles.count("primary") > 1:
        raise ServiceFactsError(
            "a return names one primary filer, and this one names more — answer `spouse` under "
            "\"Who this person is to the return\" for the second person of a joint return")
    spouse_rows = filer_roles.count("spouse")
    if filing == "mfj":
        if spouse_rows == 0:
            raise ServiceFactsError(
                "a joint return names two people, and only one is here — add the spouse's row "
                "and answer `spouse` under \"Who this person is to the return\"")
        if spouse_rows > 1:
            raise ServiceFactsError("a joint return names one spouse, and this one names more")
    elif spouse_rows:
        raise ServiceFactsError(
            f"filing status {filing!r} names one filer; a `spouse` row belongs on a joint return")
    birth_days = validate_birth_days(persons, birth_days)                 # the local page's store
    _refuse_age65_day_ambiguous(persons, tax_year, birth_days)
    _refuse_dependent_day_ambiguous(persons, tax_year, birth_days)
    # after the structural checks (a joint return names two people, roles, TINs), so a
    # malformed household meets its own sentence and not this chain's backstop.
    refuse_misplaced_lived_together_answers(facts)
    refuse_misplaced_claim_me_answers(persons)
    refuse_misplaced_mfj_claim_answers(facts)
    refuse_missing_digital_asset_answers(facts)
    refuse_missing_residence_state(facts)
    refuse_misplaced_alaska_pfd_answers(facts)
    refuse_misplaced_hsa_answers(facts, tax_year)
    refuse_misplaced_care_expenses(facts, tax_year)
    refuse_misplaced_dependent_care_benefits(facts)
    refuse_unsupported_box12_codes(facts.get("w2s") or [])
    refuse_misplaced_savers_answers(facts, tax_year)
    _require_savers_answers(facts, tax_year)
    refuse_misplaced_hsa_own_answers(facts)
    _require_hsa_own_answers(facts)
    refuse_misplaced_hsa_transfer_month(facts)
    refuse_misplaced_rollover_answers(facts)
    refuse_misplaced_qcd_answers(facts)
    refuse_misplaced_pso_answers(facts)
    refuse_misplaced_mra_answer(facts)
    refuse_misplaced_death_benefit_answers(facts, tax_year)
    refuse_misplaced_worksheet_a_answers(facts)
    refuse_rollover_beside_funding_distribution(facts)
    refuse_misplaced_hsa_funding_amounts(facts)
    _require_hsa_funding_amounts(facts)
    _require_qcd_answers(facts)
    _require_rollover_answers(facts)
    _require_hsa_transfer_month(facts)
    refuse_hsa_medicare_onset_contradictions(facts)                       # before the funding check — a bad month stops the chain
    refuse_misplaced_hsa_mfs_spouse_months(facts)
    refuse_misplaced_hsa_december_value(facts)
    refuse_misplaced_hsa_prior_excess(facts)
    refuse_hsa_carry_in_without_activity(facts)                          # after the dependent-row refusal
    refuse_hsa_mfs_spouse_family_without_the_check(facts)
    refuse_misplaced_hsa_contribution_answers(facts)
    refuse_hsa_month_contradictions(facts)
    refuse_hsa_testing_period_contradictions(facts)
    _require_hsa_contribution_answers(facts)
    refuse_misplaced_combat_pay_answers(facts)
    _require_combat_pay_answers(facts)
    refuse_misplaced_unable_to_care(facts.get("persons") or [])
    refuse_misplaced_ptc_answers(facts)
    refuse_missing_w2_asked_answers(facts.get("w2s"))
    refuse_missing_foreign_account_answers(facts)
    refuse_missing_credit_history_answers(facts)
    refuse_misplaced_estimated_payments_answers(facts)
    refuse_misplaced_student_loan_answers(facts)
    refuse_misplaced_lump_sum_answers(facts)
    refuse_misplaced_sole_trader_answers(facts)
    refuse_section_1341_credit(facts)
    refuse_misplaced_royalty_answers(facts)
    if royalty_expenses_reached(facts) and ROYALTY_EXPENSES_FIELD not in facts:
        raise FactsSchemaError(
            f"{ROYALTY_EXPENSES_FIELD} is asked once the return claims royalty income (any "
            f"misc1099s[].royalties_cents above 0) — answer it (prepare_return asks it as a gap)")
    for i, item in enumerate(facts.get("misc1099s") or []):
        if (isinstance(item, dict) and misc_pfd_question_reached(item)
                and MISC_PFD_FIELD not in item):
            raise FactsSchemaError(
                f"misc1099s[{i}].{MISC_PFD_FIELD} is asked once this form's other_income_cents "
                f"is above 0 — answer it (prepare_return asks it as a gap)")
    refuse_misplaced_alimony_answers(facts)

    f = _scaffold(filing)
    # the residence state from the caller's answer; the dividend answers as reached (both
    # no — a yes was refused above), and the section's Done marker once they are answered.
    f["/filerResidenceAndIncomeState"] = _enum("/scopedStateOptions", facts[RESIDENCE_STATE_FIELD])
    for field in alaska_pfd_questions_reached(facts):
        f[ALASKA_PFD_EMISSION[field]] = _bool(facts[field])
    f["/hasCompletedApfSection"] = _bool(True)
    # the page-1 digital-assets question, both parts, from the caller's answers.
    for field, path in DIGITAL_ASSET_EMISSION.items():
        f[path] = _bool(facts[field])
    # Schedule B Part III, lines 7a and 8, from the caller's answers.
    for field, path in FOREIGN_ACCOUNT_EMISSION.items():
        f[path] = _bool(facts[field])
    # Form 8862's credit-history questions, from the caller's answers.
    for field, path in CREDIT_HISTORY_EMISSION.items():
        f[path] = _bool(facts[field])
    # Form 1040 line 26 from the caller's answers — the root answer always; on a yes the
    # amount and the two follow-ups (both no: a yes was refused above).
    f["/paidEstimatedTaxesOrFromLastYear"] = _bool(facts[ESTIMATED_PAYMENTS_FIELD])
    if facts[ESTIMATED_PAYMENTS_FIELD] is True:
        f["/estimatedTaxPaymentWritable"] = _dollar(facts[ESTIMATED_PAYMENTS_AMOUNT_FIELD])
        f["/paidEstimatedTaxesOrFromLastYearUnderDifferentName"] = _bool(False)
        f["/paidEstimatedTaxesWithFormerSpouse"] = _enum(
            "/paidEstimatedTaxesWithFormerSpouseOptions", "neither")
    # retired: nothing is emitted — the dictionary reads the old
    # writable nowhere — and an amount above 0 was refused by name before this point.
    # Schedule 1 line 21 from the caller's answers — the root answer always; on a yes
    # whether the loans qualify and the interest paid.
    f["/hadStudentLoanInterestPayments"] = _bool(facts[STUDENT_LOAN_FIELD])
    if facts[STUDENT_LOAN_FIELD] is True:
        f["/studentLoansQualify"] = _bool(facts["student_loans_qualify"])
        f["/studentLoanInterestAmount"] = _dollar(facts["student_loan_interest_cents"])
        if facts["student_loans_qualify"] is True:
            f["/writableStudentLoanInterestEmployerPaidSection127"] = _dollar(
                facts["student_loan_interest_employer_paid_cents"])
            f["/writableStudentLoanInterestFromTaxFreeQtpEarnings"] = _dollar(
                facts["student_loan_interest_from_qtp_cents"])
    # Form 1040 line 6c — the caller's answer once a benefit statement exists (the
    # backstop above guarantees it), false as a derivation of "no statement" otherwise. A yes
    # is the dictionary's own knockout, served with words.
    f["/writableSocialSecurityLumpSumElection"] = _bool(
        facts[LUMP_SUM_FIELD] if lump_sum_question_reached(facts) else False)
    # Form 8960's sole-trader attestation — only a no reaches here (a yes and a
    # reached blank are refused above); off the reach nothing is sent and the question is moot.
    if sole_trader_question_reached(facts):
        f["/writableSection475eTraderInFinancialInstrumentsOrCommoditiesElection"] = _bool(
            facts[SOLE_TRADER_FIELD])
    # Schedule 1 line 2a/19a from the caller's answers — each amount only when the caller
    # sent it (absent means no alimony, never a stated 0); the gate alongside it, backstopped by
    # `refuse_misplaced_alimony_answers` (a reached-but-absent gate never reaches map_to_engine).
    if ALIMONY_RECEIVED_AMOUNT_FIELD in facts:
        f["/writableAlimonyReceivedAmount"] = _dollar(facts[ALIMONY_RECEIVED_AMOUNT_FIELD])
        f["/alimonyReceivedPre2019Agreement"] = _bool(facts[ALIMONY_RECEIVED_GATE_FIELD])
    if ALIMONY_PAID_AMOUNT_FIELD in facts:
        f["/writableAlimonyPaidAmount"] = _dollar(facts[ALIMONY_PAID_AMOUNT_FIELD])
        f["/alimonyPaidPre2019Agreement"] = _bool(facts[ALIMONY_PAID_GATE_FIELD])
        if facts[ALIMONY_PAID_GATE_FIELD] is True:
            f["/writableAlimonyPaidIsSection682TrustIncome"] = _bool(
                facts[ALIMONY_PAID_TRUST_FIELD])
    # the Form 1040 page-1 main-home checkbox — only when the caller sent it (absent means
    # the engine's own complete-safe true, never a stated answer). An explicit false is emitted
    # exactly as sent: this is the one direction that denies the childless EIC.
    if MAIN_HOME_FIELD in facts:
        f["/writableMainHomeInUsOverHalfYear"] = _bool(facts[MAIN_HOME_FIELD])

    if filing == "qss":
        _DEATH_YEAR = {"last_year": "taxYearMinusOne", "two_years_ago": "taxYearMinusTwo"}
        f["/yearOfSpouseDeath"] = _enum("/yearOfSpouseDeathOptions",
                                        _DEATH_YEAR[facts["spouse_death_year"]])
        f["/canFileJointlyYearOfSpouseDeath"] = _bool(
            facts["could_have_filed_jointly_year_of_death"])

    if filing == "mfs":
        # The separate-return pair (the guard above has already run): the answer to the
        # printed checkbox goes through, and a true carries its implication — an itemizing
        # spouse is necessarily a FILING spouse, so one ask completes the engine's two-fact
        # zeroing chain (/standardDeductionZeroedByMfsSpouseItemizing reads both).
        f["/spouseItemizes"] = _bool(facts["spouse_itemizes"])
    # the couple's filing-requirement pair, as far as reached; the refund-only answer is
    # emitted INVERTED — the dictionary's writable is "filing for credits".
    for field in mfj_claim_questions_reached(facts):
        if field not in facts:
            continue
        if field == "couple_required_to_file":
            f["/MFJRequiredToFile"] = _bool(facts[field])
        else:
            f["/MFJDependentsFilingForCredits"] = _bool(not facts[field])
    # the lived-together chain, exactly as far as reached.
    for field in lived_together_questions_reached(facts):
        if field not in facts:
            continue
        if field == "months_lived_with_spouse":
            f[LIVED_TOGETHER_EMISSION[field]] = _enum("/spouseLivedTogetherMonthsOptions",
                                                      _MONTHS_WITH_SPOUSE[facts[field]])
        else:
            f[LIVED_TOGETHER_EMISSION[field]] = _bool(facts[field])
        # The spouse chain is emitted after the filers block below: two of its answers
        # land on the secondary filer item, which that block creates.

    filer_ids = []
    filer_by_index = {}                       # persons index -> filer cid, any row order
    dependent_ids = []
    for i, p in enumerate(persons):
        if p.get("role") == "dependent":
            cid = _uuid("2", i + 1)
            dependent_ids.append(cid)
            _dependent(f, cid, p, i, tax_year, birth_days)
            continue
        # Form 1040 line 12's checkbox is a question on every filer row — “You: Are
        # blind”, and “Spouse: Is blind” on a joint return. A row without it stops the return
        # with the question; `gaps.gaps_for` asks it first, so a loop-driven caller meets the
        # ask and never this backstop. Placed AFTER the role arithmetic so a mis-roled row is
        # still refused by the sentence about roles.
        if "is_blind" not in p:
            raise FactsSchemaError(
                f"persons[{i}].is_blind is a question on every filer row, not a default — "
                f"answer it (prepare_return asks it as a gap)")
        # the educator question on every filer row, and its amount once that row says
        # yes — the same stop-with-the-question backstop, one sentence per field.
        for field in educator_questions_reached(p):
            if field not in p:
                raise FactsSchemaError(
                    f"persons[{i}].{field} is "
                    + ("a question on every filer row, not a default"
                       if field == EDUCATOR_FIELD else
                       "asked once that person answers yes to having been a K-12 educator")
                    + " — answer it (prepare_return asks it as a gap)")
        # the IRA question on every filer row, its amount and inherited answer once that
        # row says yes — a yes without the amount served a deduction of 0 silently (measured).
        for field in ira_questions_reached(p):
            if field not in p:
                raise FactsSchemaError(
                    f"persons[{i}].{field} is "
                    + ("a question on every filer row, not a default"
                       if field == IRA_FIELD else
                       "asked once that person answers yes to contributing to an inherited IRA"
                       if field == IRA_INHERITED_AMOUNT_FIELD else
                       "asked once that person answers yes to contributing to an IRA")
                    + " — answer it (prepare_return asks it as a gap)")
        if IRA_INHERITED_AMOUNT_FIELD in p:
            if not (0 <= _cents_or_zero(p.get(IRA_INHERITED_AMOUNT_FIELD))
                    <= _cents_or_zero(p.get(IRA_AMOUNT_FIELD))):
                raise FactsSchemaError(
                    f"persons[{i}].{IRA_INHERITED_AMOUNT_FIELD} is outside the range the "
                    f"traditional amount allows. Must be between 0 and the traditional IRA "
                    f"contributions reported on this row")
        # the Roth half, once the row reaches it. Unanswered there is no complete-safe
        # default — 0 would hand the spouse a limit the statute does not allow and the combined
        # amount would over-cut it — so the question is required and the backstop stops with it.
        if ira_roth_split_reached(facts, i) and IRA_ROTH_SPLIT_FIELD not in p:
            raise FactsSchemaError(
                f"persons[{i}].{IRA_ROTH_SPLIT_FIELD} is asked on a joint return once this "
                f"filer reports a combined Roth and ABLE amount above 0 — answer it "
                f"(prepare_return asks it as a gap)")
        if IRA_ROTH_SPLIT_FIELD in p:
            _roth = _cents_or_zero(p.get(IRA_ROTH_SPLIT_FIELD))
            if not 0 <= _roth <= _cents_or_zero(p.get(IRA_ROTH_ABLE_FIELD)):
                raise FactsSchemaError(
                    f"persons[{i}].{IRA_ROTH_SPLIT_FIELD} is outside the range the combined "
                    f"amount allows. Must be between 0 and the Roth IRA and ABLE account "
                    f"contributions reported on this row")
        # the HSA exception pair once this filer's taxable distributions reach it —
        # unanswered, the dictionary refuses the return (measured), never a silent 20% tax.
        for field in hsa_exception_questions_reached(facts, i, tax_year):
            if field not in p:
                raise FactsSchemaError(
                    f"persons[{i}].{field} is asked once that person's HSA distributions exceed "
                    f"their qualified medical expenses (the 20%-tax exception, both halves) — "
                    f"answer it (prepare_return asks it as a gap)")
        cid = _uuid("1", i + 1)
        filer_ids.append(cid)
        filer_by_index[i] = cid
        _filer(f, cid, p, primary=(p.get("role") == "primary"), person_index=i,
               birth_days=birth_days)
    if not filer_ids:
        raise ServiceFactsError("a primary filer is required")
    # the dictionary's one enum for both filers, derived from the rows' answers (every
    # filer row carries one — the backstop above). A spouse row exists on a joint return only,
    # which is what keeps the enum's spouse arms off every other status.
    f["/wasK12Educators"] = _enum("/k12EducatorOptions", EDUCATOR_OPTIONS[(
        any(p.get("role") == "primary" and p.get(EDUCATOR_FIELD) is True for p in persons),
        any(p.get("role") == "spouse" and p.get(EDUCATOR_FIELD) is True for p in persons))])
    # the dictionary's one IRA boolean for the return — true when any filer row says yes;
    # each row's amount and inherited answer land on that filer's writables in `_filer`.
    f["/madeIraContributions"] = _bool(any(
        p.get("role") != "dependent" and p.get(IRA_FIELD) is True for p in persons))
    # each filer's Roth IRA contributions on the dictionary's own writable for that filer —
    # IRC 219(c)(1)(B)(ii)(III)'s reduction term in the OTHER spouse's limit, so both rows send it.
    # Only the Roth half: the ABLE remainder belongs to Form 8880 line 1 and to nothing here.
    for i, p in enumerate(persons):
        if ira_roth_split_reached(facts, i):
            f[IRA_ROTH_EMISSION[p.get("role") == "primary"]] = _dollar(
                _cents_or_zero(p.get(IRA_ROTH_SPLIT_FIELD)))
    if len(filer_ids) == 1:
        # the Direct File convention the dictionary is written against — /filers ALWAYS
        # carries two items, the unused second one holding nothing but isPrimaryFiler false
        # (build's own single-filer scenarios, e.g. 1040-withholdings-without-attachments.json).
        # Without it /secondaryFiler (a Find over /filers) never resolves, every secondary-filer
        # aggregate under /totalIncome resolves Placeholder, /agi inherits it, and every
        # IsComplete(/agi) guard in the dictionary — Form 8960 line 17, the K-1 capital-GP
        # knockout — substitutes 0. Measured: with this item /agi resolves Complete. Engine
        # plumbing, not an assumption about a person: no identity, no dates. On a SEPARATE
        # return it also carries the two spouse answers the chain below reaches (
        # canBeClaimed, isBlind) — the filer's own answers about the spouse, on the item the
        # dictionary reads them from.
        # Kept OUT of filer_ids: it is nobody, so no person index may resolve to it.
        cid = _uuid("1", len(persons) + 1)
        f[f"/filers/#{cid}/isPrimaryFiler"] = _bool(False)
        f["/filers"] = _collection(filer_ids + [cid])
        secondary_cid = cid
    else:
        f["/filers"] = _collection(filer_ids)
        secondary_cid = None
    if filing == "mfs":
        # the separate-return spouse chain, the filer's own answers (the guard above has
        # refused off-status and unreached answers; the backstop here refuses a reached answer
        # that is absent — gaps_for asks first). IRC 151(b)/63(f): the spouse's age and
        # blindness amounts join this return's line 12 only when the spouse files no return,
        # had no gross income and is nobody's dependent — the dictionary's own
        # /MFSSpouseProvidesNoBenefits chain, fed link by link. A spouse who files ends it
        # (once an assumption, now an answer); unreached links are left unsent, the engine's
        # own Any/All short-circuits keep the return Complete (measured, every ending). An
        # ITEMIZING spouse reaches none of it: the filing fact rides as the stated implication
        # and the zeroing chain reads both facts true.
        reached = mfs_spouse_questions_reached(facts)
        for field in reached:
            if field not in facts:
                raise FactsSchemaError(
                    f"{field} is a question on this separate return, not a default — answer "
                    f"it (prepare_return asks it as a gap)")
        if facts["spouse_itemizes"] is True:
            f["/MFSLivingSpouseFilingReturn"] = _bool(True)
        else:
            f["/MFSLivingSpouseFilingReturn"] = _bool(facts["spouse_files_return"])
        if "spouse_had_gross_income" in reached:
            f["/MFSSpouseHasGrossIncome"] = _bool(facts["spouse_had_gross_income"])
        if "spouse_can_be_claimed" in reached:
            f[f"/filers/#{secondary_cid}/canBeClaimed"] = _bool(facts["spouse_can_be_claimed"])
        if "spouse_65_or_older" in reached:
            f["/MFSSpouse65OrOlder"] = _bool(facts["spouse_65_or_older"])
            f[f"/filers/#{secondary_cid}/isBlind"] = _bool(facts["spouse_is_blind"])
        # the other spouse's employer-plan coverage, once the filer contributed to an IRA
        # and the couple did not live apart all year — unanswered, the dictionary resolves it
        # false and serves the full deduction (measured), so the backstop stops the return.
        if ira_coverage_question_reached(facts):
            if IRA_COVERAGE_FIELD not in facts:
                raise FactsSchemaError(
                    f"{IRA_COVERAGE_FIELD} is a question on this separate return, not a "
                    f"default — answer it (prepare_return asks it as a gap)")
            f["/writableMfsSpouseCoveredByEmployerPlan"] = _bool(facts[IRA_COVERAGE_FIELD])
        # the spouse's twelve HSA coverage months behind the line 6 check — the rows the
        # dictionary's /hsaMfsSpouseVectorAnswered gate wants (register row 52); unanswered it
        # refuses the return itself, so the backstop stops it here first.
        if hsa_mfs_spouse_months_asked(facts):
            for m, field in enumerate(HSA_MFS_SPOUSE_MONTH_FIELDS, 1):
                if field not in facts:
                    raise FactsSchemaError(
                        f"{field} is a question on this separate return, not a default — answer "
                        f"it (prepare_return asks it as a gap)")
                f[f"/writableHsaMfsSpouseCoverageTypeMonth{m:02d}"] = _enum(
                    "/hsaMonthlyCoverageTypeOptions", HSA_MONTH_LITERALS[facts[field]])
    if dependent_ids:
        f["/familyAndHousehold"] = _collection(dependent_ids)
    # The filer-side CTC gate reads each filer's SSN work-validity as a TOP-LEVEL enum
    # (`/someFilerHasSsnValidForCtc` — measured: the credit computes only when it resolves).
    # Derived from the filer's own tin_type, spouse included on a joint return.
    _VALIDITY = {"ssn_valid_for_employment": "neither", "ssn_other": "notValid",
                 "ssn_dhs_authorization": "validOnlyWithDhsAuthorization",
                 "ssn_dhs_authorization_expired": "validOnlyWithDhsAuthorizationExpired"}
    filer_rows = [p for p in persons if p.get("role") != "dependent"]
    for row in filer_rows:
        which = ("/primaryFilerSsnEmploymentValidity" if row.get("role") == "primary"
                 else "/secondaryFilerSsnEmploymentValidity")
        if row.get("tin_type") in _VALIDITY:
            f[which] = _enum("/ssnEmploymentValidityOptions", _VALIDITY[row["tin_type"]])

    def filer_ref(idx):
        # W-2s etc. reference a filer by index into persons[]; map to that filer's cid.
        # This USED to coerce anything out of range to `filer_ids[0]`, which silently attributed a
        # spouse's W-2 to the primary — on exactly the field the per-person Social Security logic
        # reasons about, and invisibly, since the return still computed. A negative index was worse:
        # Python would have indexed from the END. Refusing is the only honest answer; the caller
        # pointed at somebody who is not there.
        if not 0 <= idx < len(filer_ids):
            raise FactsSchemaError(
                f"person index {idx} does not name a filer in this return (there "
                f"{'is 1 filer' if len(filer_ids) == 1 else f'are {len(filer_ids)} filers'}). "
                f"Attributing the form to somebody else would change the return without saying so.")
        return filer_ids[idx]

    # Non-wage income streams: an incomplete mapping under-reports, which World #1 forbids
    # ("never a silently wrong number"), so each is an honest OUT_OF_COVERAGE refusal until its
    # mapper exists. The refusal's stated CAUSE comes from the reachability artifact: the
    # old sentence blamed the engine ("the flow … is not complete") and was measured false at the
    # pin for every one of these streams — the engine carries them; the missing piece is OURS.
    for stream in UNSUPPORTED_STREAMS:
        if facts.get(stream):
            from ..service import reachability
            if reachability.group_reaches(stream):
                why = ("the engine at the pin can carry it into the return, but this service's "
                       "mapping for it is not built — refusing rather than counting the return "
                       "short")
            else:
                why = "it is not carried into the return at the pin — refused rather than ignored"
            raise ServiceFactsError(
                f"{FACT_GROUP_LABELS[stream]} is not in the covered set yet "
                f"({covered_income()}); {why}")

    for group in sorted(_INCOME_MAPPERS):
        _INCOME_MAPPERS[group](f, facts.get(group) or [], filer_ref)
    _map_royalties(f, facts)
    f["/qualifiedBusinesses"] = _collection(_qualified_business_members(f, facts))
    _hsa_section(f, facts, filer_by_index, tax_year)
    _combat_section(f, facts)
    _qcd_history_section(f, facts)
    # the providers group once any person carries care expenses — unanswered, the section
    # never closes (measured); the gap is asked, the backstop stops with the question.
    if care_providers_question_reached(facts) and not (facts.get(CDCC_GROUP) or []):
        raise FactsSchemaError(
            f"{CDCC_GROUP} is asked once a person carries care expenses above 0 — Form 2441 "
            f"line 1: who provided the care (an organization, a tax-exempt organization, or an "
            f"individual), whether they were your household employee, and the amount paid — "
            f"answer it (prepare_return asks it as a gap)")
    _cdcc_section(f, facts, filer_by_index, tax_year)
    _savers_section(f, facts, tax_year)
    # Form 2441's other qualifying-person arm on a claimed dependent's row 13 or older —
    # unanswered, the row's status is nobody's answer; the gap asks, the backstop stops.
    for i, person in enumerate(facts.get("persons") or []):
        if (unable_to_care_question_reached(person, tax_year)
                and UNABLE_TO_CARE_FIELD not in person):
            raise FactsSchemaError(
                f"persons[{i}].{UNABLE_TO_CARE_FIELD} is asked of a claimed dependent 13 or "
                f"older (Form 2441's qualifying-person test) — answer it (prepare_return asks "
                f"it as a gap)")
    # the qualifying-child age test's disability arm — unanswered, a dependent past the age
    # arm is silently not disabled; the gap asks, the backstop stops.
    for i, person in enumerate(facts.get("persons") or []):
        if disability_question_armed(person, facts) and DISABILITY_FIELD not in person:
            raise FactsSchemaError(
                f"persons[{i}].{DISABILITY_FIELD} is asked of a claimed dependent who is 18 or "
                f"older at mid-year, or not younger than the filer (the qualifying-child age "
                f"test) — answer it (prepare_return asks it as a gap)")
    # the member-of-household questions (the qualifying-relative household test, and the
    # local-law question Form 2441 also reads) — refused off their rows, backstopped on them,
    # after the unable-to-care backstop so a row's Form 2441 reach is settled first.
    refuse_misplaced_household_member_answers(facts, tax_year)
    _household_member_section(f, facts, tax_year)
    # Form 2441 Part III — unanswered, the plan maximum and line 14 stall the section
    # (measured); the gaps ask them, the backstop stops with the question.
    for i, person in enumerate(facts.get("persons") or []):
        if (isinstance(person, dict) and DCB_PLAN_MAX_FIELD not in person
                and DCB_PLAN_MAX_FIELD in dcb_person_questions_reached(facts, i)):
            raise FactsSchemaError(
                f"persons[{i}].{DCB_PLAN_MAX_FIELD} is asked once that filer's Form W-2 box 10 "
                f"or own sole-proprietorship benefit is above 0 — answer it (prepare_return "
                f"asks it as a gap)")
    if DCB_FORFEITED_FIELD in dcb_root_questions_reached(facts) and DCB_FORFEITED_FIELD not in facts:
        raise FactsSchemaError(
            f"{DCB_FORFEITED_FIELD} is asked once a filer reports dependent care benefits "
            f"({FACT_GROUP_LABELS[DCB_FORFEITED_FIELD]}) — answer it (prepare_return asks it "
            f"as a gap)")
    # the root questions a Form 1095-A reaches — unanswered, the section never closes
    # (measured); the gaps are asked, the backstop stops with the question.
    for field in ptc_questions_reached(facts):
        if field in PTC_ROOT_REQUIRED_FIELDS and field not in facts:
            raise FactsSchemaError(
                f"{field} is asked once a Form 1095-A is entered ({FACT_GROUP_LABELS[field]}) — "
                f"answer it (prepare_return asks it as a gap)")
    _ptc_section(f, facts)

    return {"facts": f}


def covered_income() -> str:
    """The covered income groups, in the words `coverage` publishes them under. Served inside every
    stream refusal, DERIVED rather than typed: a review found the refusal still saying "the
    wages-only slice" after W-2G was covered — a served boundary statement that had quietly become
    false ("a refusal that misstates its own cause is worse than a bare one")."""
    return "; ".join(FACT_GROUP_LABELS[g]
                     for g in sorted(COVERED_FACT_GROUPS - {"filing_status", "persons"}))


# Form W-2 box 13, the three printed checkboxes, asked on every W-2 (an assumption inverted into
# a question, per item), never a default. Measured at the pin, each checked alone on
# wages-single-mid:
# "Statutory employee" fires /flowKnockoutStatutoryEmployee and /knockoutFormW2s (a statutory
# employee's wages belong on Schedule C — once that W-2 was computed as ordinary wages and
# served complete); "Retirement plan" reaches the covered-by-employer-plan facts, the IRA-deduction
# limit chain, which moves nothing while IRA contributions are not asked; "Third-party sick pay" has
# no reader at all.
W2_BOX13_FIELDS = ("statutory_employee", "retirement_plan", "third_party_sick_pay")
W2_BOX13_EMISSION = {"statutory_employee": "statutoryEmployee", "retirement_plan": "retirementPlan",
                     "third_party_sick_pay": "thirdPartySickPay"}
# Form W-2 box 14 — does it list Railroad Retirement Tax Act (RRTA) codes? Asked on every
# W-2, the same shape. Measured at the pin (wages-single-mid, residence IL and NY alike): a yes
# makes /formW2s/*/hasRRTACodesReported true, the first disjunct of ../reportsRRTAWithoutCompensation
# — the whole body of /flowKnockoutHasRRTACodesInBox14NotInNY, a /flowIsKnockedOut member whose
# "NotInNY" is history — because this service never sends the box-14 RRTA compensation that sizes
# Form 8959 Part III. The answer was once attested false and published as an assumption, so
# a railroad employee's W-2 was computed as ordinary wages and served complete.
W2_BOX14_RRTA_FIELD = "has_rrta_codes"
W2_ASKED_FIELDS = (*W2_BOX13_FIELDS, W2_BOX14_RRTA_FIELD)
W2_ASKED_EMISSION = {**W2_BOX13_EMISSION, W2_BOX14_RRTA_FIELD: "hasRRTACodes"}
_W2_ASKED_BOX = {**{f: "a box 13 checkbox" for f in W2_BOX13_FIELDS},
                 W2_BOX14_RRTA_FIELD: "the box 14 Railroad Retirement (RRTA) question"}


def savers_contributions(facts: dict, person_index: int) -> int:
    """the cents Form 8880 counts for one filer — the box 12 deferral codes on that filer's
    W-2s (line 2) and the IRA and ABLE contributions on their row (line 1)."""
    total = 0
    for w2 in facts.get("w2s") or []:
        if isinstance(w2, dict) and w2.get("person") == person_index:
            total += sum(_cents_or_zero(w2.get(field)) for field in W2_BOX12_DEFERRAL_FIELDS)
    person = (facts.get("persons") or [None] * (person_index + 1))[person_index]
    if isinstance(person, dict) and person.get(IRA_FIELD) is True:
        total += _cents_or_zero(person.get(IRA_AMOUNT_FIELD)) + _cents_or_zero(person.get(IRA_ROTH_ABLE_FIELD))
    return total


def savers_return_contributions(facts: dict, person_index: int) -> int:
    """the contributions that reach Form 8880 for one filer row — on a JOINT return the
    route is the return's, not the row's: Form 8880 line 4 puts both spouses' distributions in
    both columns (measured: a spouse's 2023 distribution of 1,000 takes the primary's credit from
    400 to 200 when they filed jointly that year), so every filer row is asked once either filer
    contributes. On every other status the row's own contributions decide; a dependent row is
    never reached (0)."""
    persons = facts.get("persons") or []
    def _filer(i):
        p = persons[i] if i < len(persons) else None
        return isinstance(p, dict) and p.get("role") in ("primary", "spouse")
    if not _filer(person_index):
        return 0
    if facts.get("filing_status") == "mfj":
        return sum(savers_contributions(facts, i) for i in range(len(persons)) if _filer(i))
    return savers_contributions(facts, person_index)


def savers_day_ambiguous(person: dict, tax_year: int = 2025) -> bool:
    """the synthesized-day posture: a filer born in January of `tax_year - 17` turns 18 on a day this
    service does not carry — by the dictionary's day-before-birthday rule, born January 1 they
    are 18 on December 31 (eligible), born January 2-31 they are 17 (not). The synthesized day
    01 would serve the credit to the ~30/31 (measured: 2008-01 → 400, 2008-02 → 0)."""
    if not isinstance(person, dict) or person.get("role") not in ("primary", "spouse"):
        return False
    year, month = _birth_year_month(person)
    return year == tax_year - SAVERS_AGE + 1 and month == 1


def savers_questions_reached(facts: dict, person_index: int, tax_year: int = 2025) -> list:
    """the Form 8880 fields one FILER row's answers reach, in order — the student test
    first (cheap gate; a yes ends the route), then the prior-two-years distributions question
    and its two amounts on a yes, then the post-year-end question and its amount on a yes.
    Reached only by a filer 18 or older by birth year (the January-of-boundary cohort is refused,
    never asked) with contributions above 0 on their W-2s or their IRA row — on a joint return,
    on either filer's (`savers_return_contributions`). AGI is the dictionary's to decide: above
    its limit the answers are inert, so they are still asked."""
    persons = facts.get("persons") or []
    person = persons[person_index] if person_index < len(persons) else None
    if not isinstance(person, dict) or person.get("role") not in ("primary", "spouse"):
        return []
    year, _month = _birth_year_month(person)
    if year is None or savers_day_ambiguous(person, tax_year) or tax_year - year < SAVERS_AGE:
        return []                            # 17 by birth year; the January cohort is refused
    if savers_return_contributions(facts, person_index) <= 0:
        return []
    reached = [SAVERS_STUDENT_FIELD]
    if person.get(SAVERS_STUDENT_FIELD) is not False:
        return reached                       # absent: asked; true: the dictionary's own no
    reached.append(SAVERS_DIST_PRIOR_FIELD)
    if person.get(SAVERS_DIST_PRIOR_FIELD) is True:
        reached.extend((SAVERS_DIST_2023_FIELD, SAVERS_DIST_2024_FIELD))
    reached.append(SAVERS_DIST_AFTER_FIELD)
    if person.get(SAVERS_DIST_AFTER_FIELD) is True:
        reached.append(SAVERS_DIST_AFTER_AMOUNT_FIELD)
    return reached


def savers_root_questions_reached(facts: dict, tax_year: int = 2025) -> list:
    """the filed-jointly questions a joint return reaches — one per prior year in which
    either filer reports a distribution above 0 (measured: unanswered, the credit is zeroed)."""
    if not isinstance(facts, dict) or facts.get("filing_status") != "mfj":
        return []
    reached = []
    for year_field, root in ((SAVERS_DIST_2023_FIELD, "filed_jointly_2023"),
                             (SAVERS_DIST_2024_FIELD, "filed_jointly_2024")):
        for i, person in enumerate(facts.get("persons") or []):
            if (year_field in savers_questions_reached(facts, i, tax_year)
                    and _cents_or_zero(person.get(year_field)) > 0):
                reached.append(root)
                break
    return reached


def box12_g_plan_question_reached(w2) -> bool:
    """box 12 code G counts toward Form 8880 line 2 only from a governmental section 457(b)
    plan (measured: 2,000 of G with the answer false gives 0), so the answer is asked on every
    W-2 whose code G amount is above 0."""
    return isinstance(w2, dict) and _cents_or_zero(w2.get("box12_g_cents")) > 0


def refuse_misplaced_savers_answers(facts: dict, tax_year: int = 2025) -> None:
    """A Form 8880 answer past its reach is refused by name rather than dropped; a filer
    in the January-of-boundary cohort with contributions is refused rather than aged by a
    synthesized day; a filed-jointly answer outside its reach, and a governmental-plan answer
    on a W-2 without code G, likewise."""
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict):
            continue
        if savers_day_ambiguous(person, tax_year) and savers_return_contributions(facts, i) > 0:
            raise ServiceFactsError(
                f"persons[{i}] is a filer on a return with retirement contributions and was born "
                f"in January {tax_year - SAVERS_AGE + 1} — whether they were 18 on December 31 {tax_year} "
                f"(Form 8880's age test) turns on the birth day, and this service has no birth "
                f"day; refused rather than guessed")
        reached = savers_questions_reached(facts, i, tax_year)
        for field in SAVERS_PERSON_FIELDS:
            if field in person and field not in reached:
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered where the answers so far do not reach it — "
                    f"Form 8880's questions are asked of a filer 18 or older, not a student, with "
                    f"retirement contributions on the return, the amounts behind a yes; refused "
                    f"rather than dropped")
    reached_root = savers_root_questions_reached(facts, tax_year)
    for field in sorted(SAVERS_ROOT_FIELDS):
        if field in facts and field not in reached_root:
            raise ServiceFactsError(
                f"{field} is answered where the answers so far do not reach it — it is asked on "
                f"a joint return once a filer reports a distribution for that year (Form 8880, "
                f"line 4); refused rather than dropped")
    for i, w2 in enumerate(facts.get("w2s") or []):
        if isinstance(w2, dict) and W2_BOX12_G_PLAN_FIELD in w2 and not box12_g_plan_question_reached(w2):
            raise ServiceFactsError(
                f"w2s[{i}].{W2_BOX12_G_PLAN_FIELD} is answered on a W-2 with no code G amount in "
                f"box 12; refused rather than dropped")


def _require_savers_answers(facts: dict, tax_year: int = 2025) -> None:
    """every Form 8880 question the route reaches is answered — unanswered, the dictionary
    serves the credit on the favourable silence (measured), never here."""
    for i, person in enumerate(facts.get("persons") or []):
        for field in savers_questions_reached(facts, i, tax_year):
            if field not in person:
                raise FactsSchemaError(
                    f"persons[{i}].{field} is asked of a filer with retirement contributions "
                    f"(Form 8880; on a joint return, of both filers once either has them) — "
                    f"answer it (prepare_return asks it as a gap)")
    for field in savers_root_questions_reached(facts, tax_year):
        if field not in facts:
            raise FactsSchemaError(
                f"{field} is asked on a joint return once a filer reports a distribution for that "
                f"year (Form 8880, line 4) — answer it (prepare_return asks it as a gap)")
    for i, w2 in enumerate(facts.get("w2s") or []):
        if box12_g_plan_question_reached(w2) and W2_BOX12_G_PLAN_FIELD not in w2:
            raise FactsSchemaError(
                f"w2s[{i}].{W2_BOX12_G_PLAN_FIELD} is asked on every W-2 with a code G amount in "
                f"box 12 — answer it true or false (prepare_return asks it as a gap)")


def _savers_section(f: dict, facts: dict, tax_year: int) -> None:
    """Form 8880's writables, exactly as far as reached. The root yes/no facts are derived
    from the filer rows (the dictionary asks them once per return; the amounts are per filer) and
    sent only when some filer reaches the route; a filer who answered no sends no amount, which
    the dictionary reads as 0 (measured: one filer's amounts alone do not stall the section).
    The line-1 amount is the covered traditional IRA plus the Roth-and-ABLE answer: the deduction
    writable feeds the deduction only (measured, no double count)."""
    any_reached = self_total = 0
    prior_any = after_any = False
    for i, person in enumerate(facts.get("persons") or []):
        reached = savers_questions_reached(facts, i, tax_year)
        if not reached:
            continue
        any_reached += 1
        who = "Primary" if person.get("role") == "primary" else "Secondary"
        line1 = 0
        if person.get(IRA_FIELD) is True:
            line1 = _cents_or_zero(person.get(IRA_AMOUNT_FIELD)) + _cents_or_zero(person.get(IRA_ROTH_ABLE_FIELD))
        if line1 > 0:
            f[f"/writable{who}FilerIraAndAbleContributions"] = _dollar(line1)
            self_total += line1
        if person.get(SAVERS_DIST_PRIOR_FIELD) is True:
            prior_any = True
            f[f"/writable{who}Filer2023Distributions"] = _dollar(_cents_or_zero(person.get(SAVERS_DIST_2023_FIELD)))
            f[f"/writable{who}Filer2024Distributions"] = _dollar(_cents_or_zero(person.get(SAVERS_DIST_2024_FIELD)))
        if person.get(SAVERS_DIST_AFTER_FIELD) is True:
            after_any = True
            f[f"/writable{who}FilerPostYearEndDistributions"] = _dollar(
                _cents_or_zero(person.get(SAVERS_DIST_AFTER_AMOUNT_FIELD)))
    if not any_reached:
        return
    f["/hasSelfReportedContributions"] = _bool(self_total > 0)
    f["/hasDistributionsInLastThreeYears"] = _bool(prior_any)
    f["/hasCurrentYearDistributions"] = _bool(after_any)
    for field in savers_root_questions_reached(facts, tax_year):
        if field in facts:
            f[SAVERS_ROOT_EMISSION[field]] = _bool(facts[field])


def hsa_w2_contributions(facts: dict, person_index: int) -> int:
    """the cents of W-2 box 12 code W on one filer row's W-2s (Form 8889 line 9)."""
    return sum(_cents_or_zero(w2.get(W2_BOX12_W_FIELD)) for w2 in facts.get("w2s") or []
               if isinstance(w2, dict) and w2.get("person") == person_index)


def hsa_own_questions_reached(person) -> list:
    """the own-contribution fields one FILER row's answers reach, in order — the yes/no
    on every filer row (the dictionary asks the activity question on every return), then on a
    yes the amount (required: unanswered, the dictionary computed zero in silence) and the
    amount made after year end for the year (optional, stated as 0). A dependent row reaches
    none."""
    if not isinstance(person, dict) or person.get("role") not in ("primary", "spouse"):
        return []
    reached = [HSA_MADE_FIELD]
    if person.get(HSA_MADE_FIELD) is True:
        reached.extend((HSA_OWN_AMOUNT_FIELD, HSA_OWN_AFTER_FIELD))
    return reached


def hsa_own_contributions(person) -> bool:
    """whether this filer row answered yes to contributing to their HSA themselves."""
    return isinstance(person, dict) and person.get(HSA_MADE_FIELD) is True


def hsa_transfer_above_base(facts: dict, person_index: int) -> bool:
    """this filer's funding-distribution total is above the base limitation for their
    carried coverage — the cell whose cap the other spouse's coverage decides."""
    persons = facts.get("persons") or [] if isinstance(facts, dict) else []
    person = persons[person_index] if person_index < len(persons) else None
    if not isinstance(person, dict):
        return False
    if hsa_w2_contributions(facts, person_index) <= 0 and not hsa_own_contributions(person):
        return False                         # a filer with no HSA activity opens nothing (and the
                                             # two spouses' openers would otherwise read each other)
    return hsa_transfer_decides(facts, person_index)


def hsa_spouse_coverage_opener(facts: dict, person_index: int) -> bool:
    """on a joint return, a filer row with no HSA activity of its own whose spouse's
    funding distribution is above the base limitation — or, since whose spouse's coverage
    months were asked (a part-year primary's line 3 needs the spouse's vector to govern) — IRC 223(b)(5)(A) reads this filer's
    coverage for the couple's shared limitation (measured: the spouse on family coverage moves
    the primary's cap from 4,300 to 4,275), so their coverage is asked, not prefilled."""
    if not isinstance(facts, dict) or facts.get("filing_status") != "mfj":
        return False
    persons = facts.get("persons") or []
    person = persons[person_index] if person_index < len(persons) else None
    if not isinstance(person, dict) or person.get("role") not in ("primary", "spouse"):
        return False
    if hsa_w2_contributions(facts, person_index) > 0 or hsa_own_contributions(person):
        return False
    return any(isinstance(p, dict) and j != person_index and p.get("role") in ("primary", "spouse")
               and (hsa_transfer_above_base(facts, j) or hsa_vector_shaped(facts, j))
               for j, p in enumerate(persons))                                # a shaped vector too


def hsa_december_value_asked(facts: dict, person_index: int) -> bool:
    """the December 31 value is invited on every filer row with 2025 HSA activity
    (`hsa_row_has_2025_activity`) — the population on which Form 5329 line 49 can read it, and
    the same population the carry-in refusal spares, so the dictionary's line 49 knockout never
    asks for a value the page refuses. The engine decides whether an excess exists at all, so the
    value is never a gap."""
    return hsa_row_has_2025_activity(facts, person_index)


def hsa_prior_excess_asked(facts: dict, person_index: int) -> bool:
    """the carry-in is invited where the December 31 value is — a filer row with 2025 HSA
    activity. A positive carry-in on a filer row with none is the service's own refusal
    (`refuse_hsa_carry_in_without_activity`)."""
    return hsa_december_value_asked(facts, person_index)


def hsa_row_has_2025_activity(facts: dict, person_index: int) -> bool:
    """any 2025 HSA activity on this FILER row: a code W amount, the person's own contributions,
    a qualified funding transfer on one of their Forms 1099-R, or the Form 8889 Part I coverage
    chain reached for them (a joint return's spouse opened by the other's transfer). The ONE
    definition behind the December 31 value's invitation, the carry-in's invitation and the
    carry-in refusal."""
    persons = facts.get("persons") or [] if isinstance(facts, dict) else []
    person = persons[person_index] if 0 <= person_index < len(persons) else None
    if not isinstance(person, dict) or person.get("role") not in ("primary", "spouse"):
        return False
    if hsa_w2_contributions(facts, person_index) > 0 or hsa_own_contributions(person):
        return True
    if any(isinstance(r, dict) and r.get("person", 0) == person_index
           and _cents_or_zero(r.get(R1099_HFD_FIELD)) > 0 for r in facts.get("r1099s") or []):
        return True
    return bool(hsa_questions_reached(facts, person_index))


def refuse_hsa_carry_in_without_activity(facts: dict) -> None:
    """a positive carry-in on a filer row with no 2025 HSA activity is refused before resolve.
    The dictionary would take the whole carry-in to Form 5329 line 48 (build's b28-prep landing
    narrowed /flowKnockoutHsaExcessContributions to an unanswered contributions question, which
    this service always answers), but line 43 absorbs the carry-in against the room under Form
    8889 line 12, and Part I — the coverage that sets that room — is not asked on such a row, so
    the room would read 0 unasked; and line 49's cap, the December 31 value, is not invited there
    either. Refused in the service's own words rather than served as a figure or a dead end."""
    for i, person in enumerate(facts.get("persons") or []):
        if (isinstance(person, dict) and person.get("role") in ("primary", "spouse")
                and _cents_or_zero(person.get(HSA_PRIOR_EXCESS_FIELD)) > 0
                and not hsa_row_has_2025_activity(facts, i)):
            raise ServiceFactsError(
                f"For person {i + 1}, an excess HSA contribution carried in from 2024 was entered "
                f"(Form 5329, line 42) with no 2025 HSA contributions or coverage answers. This "
                f"version does not figure Form 5329 Part VII for a prior-year excess carried into "
                f"such a year: Form 8889 Part I is not asked for that person, so the room on Form "
                f"5329 line 43 could not be established. The figures are withheld.")


def hsa_prior_excess_carried(facts: dict) -> bool:
    """the dictionary's yes/no, derived — a positive carry-in on any filer row."""
    return any(isinstance(p, dict) and p.get("role") in ("primary", "spouse")
               and _cents_or_zero(p.get(HSA_PRIOR_EXCESS_FIELD)) > 0
               for p in (facts.get("persons") or []))


def refuse_misplaced_hsa_prior_excess(facts: dict) -> None:
    """the carry-in belongs to a filer row; on a dependent row it is refused by name."""
    for i, person in enumerate(facts.get("persons") or []):
        if isinstance(person, dict) and HSA_PRIOR_EXCESS_FIELD in person and person.get("role") not in ("primary", "spouse"):
            raise ServiceFactsError(
                f"persons[{i}].{HSA_PRIOR_EXCESS_FIELD} is answered on a dependent row — Form 5329 is "
                f"the filer's, and on a joint return the spouse's; refused rather than dropped")


def refuse_misplaced_hsa_december_value(facts: dict) -> None:
    """an answer on a row the invitation does not reach is refused by name."""
    for i, person in enumerate(facts.get("persons") or []):
        if isinstance(person, dict) and HSA_DEC31_FIELD in person and not hsa_december_value_asked(facts, i):
            raise ServiceFactsError(
                f"persons[{i}].{HSA_DEC31_FIELD} is answered where the answers so far do not reach it — "
                f"the HSAs' December 31 value is invited on a filer row with 2025 HSA activity (a Form "
                f"W-2 box 12 code W amount, the person's own HSA contributions, a qualified HSA funding "
                f"distribution, or the coverage questions reached), where Form 5329 line 49 reads it; "
                f"refused rather than dropped")


def hsa_questions_reached(facts: dict, person_index: int) -> list:
    """the Form 8889 Part I fields one FILER row's answers reach, in the dictionary's gate
    order — Medicare enrollment first (the coverage status is not needed behind a Medicare
    knockout), then the HDHP coverage status (asked only with no Medicare), the coverage type
    (only with coverage all year), the other-coverage question (only self-only or family), the
    qualified funding distribution (only with no other coverage), then on a separate return with
    family coverage whether the spouse contributed (Form 8889 line 6), and on a married or
    widowed filer whose other-coverage answer is none whether their marital status changed,
    with the follow-up on a yes. Every answer off that path is the dictionary's own knockout
    (measured: each fires on its own, the later questions unanswered), so the chain stops there
    and the return is served knocked out. Reached only by a filer row with a code W amount
    above 0 on their W-2s."""
    persons = facts.get("persons") or []
    person = persons[person_index] if person_index < len(persons) else None
    if not isinstance(person, dict) or person.get("role") not in ("primary", "spouse"):
        return []
    if hsa_w2_contributions(facts, person_index) <= 0 and not hsa_own_contributions(person):
        if not hsa_spouse_coverage_opener(facts, person_index):
            return []                        # a yes to own contributions opens it too
        # the other spouse's transfer is above the base — this row's coverage decides
        # the couple's cap. Medicare first (an enrolled spouse leaves the legacy chain), then
        # the coverage span (none is twelve months of no coverage; part of the year is the
        # knockout), then the type behind all-year coverage; the chain stops there — the
        # other-coverage and funding questions belong to a filer with an HSA.
        reached = [HSA_MEDICARE_FIELD]
        if hsa_medicare_onset_asked(facts, person_index):
            reached.append(HSA_MEDICARE_ONSET_FIELD)        # the spouse's onset month
            if person.get(HSA_MEDICARE_ONSET_FIELD) not in HSA_TRANSFER_MONTHS:
                return reached
        elif person.get(HSA_MEDICARE_FIELD) not in ("none", "all_year"):
            return reached                       # all year is twelve months of yes on THIS chain —
                                                 # IRC 223(b)(5)(A) reads the spouse's coverage, not their
                                                 # Medicare, for the couple's cap (measured: 1,790.00 either way)
        reached.append(HSA_COVERAGE_FIELD)
        if person.get(HSA_COVERAGE_FIELD) in ("all_year", "part_of_year"):
            reached.append(HSA_TYPE_FIELD)
            if hsa_months_asked(facts, person_index):
                reached.extend(HSA_MONTH_FIELDS)            # the spouse's months too
        return reached
    reached = [HSA_MEDICARE_FIELD]
    if hsa_medicare_onset_asked(facts, person_index):
        # Medicare for part of the year — the month enrollment began, then the chain goes on
        # (the Medicare vector is sent from that month; the limitation is the months before it)
        reached.append(HSA_MEDICARE_ONSET_FIELD)
        if person.get(HSA_MEDICARE_ONSET_FIELD) not in HSA_TRANSFER_MONTHS:
            return reached
    elif person.get(HSA_MEDICARE_FIELD) != "none" and not (
            person.get(HSA_MEDICARE_FIELD) == "all_year" and hsa_medicare_answer_carried(facts, person_index)):
        return reached
    # Medicare all year goes on too (a filer who can be claimed as a dependent stays on the legacy chain: the stop) — carried as twelve months of yes on the Medicare vector
    # once the coverage chain is answered (line 3 is then 0 and the code W amount is the excess the
    # dictionary carries to Schedule 1 line 8z; measured: 3,000 code W → 1,415.00). Behind no
    # coverage the chain stops at the coverage answer, no vector goes out and the dictionary's
    # knockout stays (its completeness gate wants a type the flow never asks there).
    reached.append(HSA_COVERAGE_FIELD)
    if person.get(HSA_COVERAGE_FIELD) not in ("all_year", "part_of_year"):
        return reached
    reached.append(HSA_TYPE_FIELD)
    if person.get(HSA_TYPE_FIELD) not in ("self_only", "family", "both"):
        return reached
    if hsa_months_asked(facts, person_index):
        # coverage for part of the year, or the `both` type — the twelve months are asked
        # (row 9's editable rows; the type kept beside them, the dictionary's excess computation
        # reads it), and the chain goes on once every month is answered.
        reached.extend(HSA_MONTH_FIELDS)
        if not all(m in person for m in HSA_MONTH_FIELDS):
            return reached
    elif person.get(HSA_COVERAGE_FIELD) == "part_of_year" or person.get(HSA_TYPE_FIELD) == "both":
        return reached                       # the legacy chain: a claimed filer,
                                             # a separate return — the dictionary's knockout, named
    reached.append(HSA_OTHER_COVERAGE_FIELD)
    if person.get(HSA_OTHER_COVERAGE_FIELD) != "none":
        return reached
    reached.append(HSA_FUNDING_FIELD)
    if person.get(HSA_FUNDING_FIELD) is True:
        # a yes is asked for the amount on each of the filer's IRA Forms 1099-R first
        # (`hsa_funding_r1099_reached`); with an amount carried, the once-per-lifetime election
        # is asked, and the chain goes on (measured: on a joint return the section completes
        # only with the marital answer). No amount carried, the chain stops and the dictionary's
        # own knockout names it.
        if hsa_funding_distribution_total(facts, person_index) <= 0:
            return reached
        reached.append(HSA_PRIOR_HFD_FIELD)
        if person.get(HSA_PRIOR_HFD_FIELD) is not False:
            return reached
        if hsa_testing_period_asked(facts, person_index):
            # the transfer opened a testing period and the year was not one of full
            # eligibility — the dictionary refuses the return without the first ineligible month
            reached.append(HSA_TESTING_FIELD)
            if person.get(HSA_TESTING_FIELD) is None:
                return reached
    elif person.get(HSA_FUNDING_FIELD) is not False:
        return reached
    if facts.get("filing_status") == "mfs" and person.get(HSA_TYPE_FIELD) == "family":
        reached.append(HSA_SPOUSE_CONTRIBUTED_FIELD)
        if person.get(HSA_SPOUSE_CONTRIBUTED_FIELD) is True:
            # the spouse's twelve coverage months (return-level,
            # `HSA_MFS_SPOUSE_MONTH_FIELDS`) come next; the marital question waits behind them —
            # measured: without it the dictionary's section never completes and an excess is
            # neither refused nor added to income. A filer who can be claimed as a dependent
            # stays on the legacy chain (no vector): the yes is the knockout there,
            # and twelve questions before a certain refusal are not asked (the opener's condition,
            # mirrored — the site cannot call `hsa_mfs_spouse_months_asked`).
            if person.get("someone_can_claim_you") is True:
                return reached
            if not all(m in facts for m in HSA_MFS_SPOUSE_MONTH_FIELDS):
                return reached
        elif person.get(HSA_SPOUSE_CONTRIBUTED_FIELD) is not False:
            return reached
    if (hsa_mfs_vector_needs_rows(facts, person)
            and not all(m in facts for m in HSA_MFS_SPOUSE_MONTH_FIELDS)):
        # beside a Medicare-shaped vector the spouse's rows are needed whatever the check
        # said, or whether it was shown (a self-only filer): on a separate return the vector
        # governs line 3 only with them (measured: without them the Medicare knockouts fire).
        return reached
    if _MARITAL.get(facts.get("filing_status")) != "single":
        reached.append(HSA_MARITAL_CHANGED_FIELD)
        if person.get(HSA_MARITAL_CHANGED_FIELD) is True:
            reached.append(HSA_MARITAL_AFFECTS_FIELD)
    return reached


def hsa_mfs_vector_needs_rows(facts: dict, person) -> bool:
    """this separate-return filer's vector is Medicare-shaped (enrollment for part of the
    year, the month answered), so it must govern line 3 — and on a separate return it governs
    only with the spouse's twelve rows. Not a filer who can be claimed as a dependent (the legacy
    chain). Answer-only: reads one row, so the chain site can read it."""
    return (isinstance(facts, dict) and facts.get("filing_status") == "mfs"
            and isinstance(person, dict) and person.get("someone_can_claim_you") is not True
            and person.get("role") in ("primary", "spouse")
            and ((person.get(HSA_MEDICARE_FIELD) == "part_of_year"
                  and person.get(HSA_MEDICARE_ONSET_FIELD) in HSA_TRANSFER_MONTHS)
                 or person.get(HSA_MEDICARE_FIELD) == "all_year"))            # all year too


def hsa_mfs_spouse_months_asked(facts: dict) -> bool:
    """the separate-return spouse's twelve coverage months are asked — a separate return
    whose filer reached the line 6 check and answered that the spouse also had HSA contributions
    (register row 52; the dictionary refuses the return until all twelve are answered, and the
    rows cannot default) — not a filer who can be claimed as a dependent, whose legacy chain
    sends no vector: the yes is the knockout there. also beside a
    Medicare-shaped vector (`hsa_mfs_vector_needs_rows`), whatever the check says or whether it
    is shown, once the filer's chain has come to the rows. Reads the filer rows' reach with the
    rows taken as answered, so the chain can read it back."""
    if not isinstance(facts, dict) or facts.get("filing_status") != "mfs":
        return False
    filled = {**facts, **{m: "none" for m in HSA_MFS_SPOUSE_MONTH_FIELDS}}
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict) or person.get("someone_can_claim_you") is True:
            continue
        reached = hsa_questions_reached(filled, i)
        check = (person.get(HSA_SPOUSE_CONTRIBUTED_FIELD) is True
                 and HSA_SPOUSE_CONTRIBUTED_FIELD in reached)          # a stray yes on a row the check never reaches opens nothing
        if (check or hsa_mfs_vector_needs_rows(facts, person)) and HSA_MARITAL_CHANGED_FIELD in reached:
            return True
    return False


def refuse_hsa_mfs_spouse_family_without_the_check(facts: dict) -> None:
    """A separate-return filer without family coverage of their own whose spouse's rows
    carry a family month: IRC 223(b)(5)(A) puts the filer on the family limit for that month, and
    whether that limit is divided on Form 8889 line 6 turns on whether the spouse holds an HSA —
    a question the dictionary shows only behind the filer's own family coverage.
    Served undivided it would be the wrong figure; refused by name instead."""
    if not isinstance(facts, dict) or facts.get("filing_status") != "mfs":
        return
    if not all(m in facts for m in HSA_MFS_SPOUSE_MONTH_FIELDS) or not hsa_mfs_spouse_months_asked(facts):
        return
    family = [n for m, n in zip(HSA_MFS_SPOUSE_MONTH_FIELDS, _HSA_MONTH_NAMES) if facts.get(m) == "family"]
    if not family:
        return
    for person in facts.get("persons") or []:
        if (isinstance(person, dict) and hsa_mfs_vector_needs_rows(facts, person)
                and person.get(HSA_TYPE_FIELD) != "family"):
            raise ServiceFactsError(
                f"On this separate return you answered that your spouse had family coverage under "
                f"a high deductible health plan on the first day of {family[0]}; that puts you on "
                f"the family limit for Form 8889 line 3 for that month, and whether the limit is "
                f"divided between you on line 6 turns on whether your spouse holds a health "
                f"savings account, which is asked only of a filer with family coverage of their "
                f"own. The figures here are not your return.")


def refuse_misplaced_hsa_mfs_spouse_months(facts: dict) -> None:
    """A spouse month outside none / self_only / family is refused by name; so is a month
    answered on a separate return that does not reach it (the filer without family coverage, the
    line 6 check unanswered or answered no). On any other status the status-root rule refuses it
    first."""
    if not isinstance(facts, dict):
        return
    for field in HSA_MFS_SPOUSE_MONTH_FIELDS:
        if field in facts and facts[field] not in HSA_MONTH_LITERALS:
            raise FactsSchemaError(
                f"{field} must be one of {', '.join(HSA_MONTH_LITERALS)}, got {facts[field]!r}")
    if facts.get("filing_status") == "mfs" and not hsa_mfs_spouse_months_asked(facts):
        for field in HSA_MFS_SPOUSE_MONTH_FIELDS:
            if field in facts:
                raise ServiceFactsError(
                    f"{field} is answered where the answers so far do not reach it — the spouse's "
                    f"coverage months are asked on a separate return once the filer with family "
                    f"coverage answers that the spouse also had HSA contributions, or beside "
                    f"Medicare enrollment for part of the year (Form 8889 lines 3 and 6); refused "
                    f"rather than dropped")


def hsa_funding_answer_assumed(facts: dict, person_index: int) -> bool:
    """a filer with Form 1099-SA distributions and no code W amount is not asked the
    funding-distribution question; the no is sent for them and STATED (`gaps._ABSENT_MEANS`)."""
    persons = facts.get("persons") or []
    person = persons[person_index] if person_index < len(persons) else None
    return (hsa_w2_contributions(facts, person_index) <= 0
            and not hsa_own_contributions(person)
            and any(isinstance(it, dict) and it.get("person") == person_index
                    for it in facts.get(HSA_GROUP) or []))


def hsa_excess_question_reached(facts: dict) -> bool:
    """the excess-in-wages answer is accepted on any return with a code W amount above 0
    (the limit it is measured against — self-only, family, the joint split, the age-55
    addition — is the dictionary's to compute, so no service-side bound decides the reach);
    unanswered, the dictionary reports the excess as other income (its own adverse default)."""
    return any(hsa_w2_contributions(facts, i) > 0 for i, p in enumerate(facts.get("persons") or [])
               if isinstance(p, dict))


def combat_pay_by_filer(facts: dict) -> dict:
    """{persons index: cents} of W-2 box 12 code Q for each filer row (primary, spouse) —
    the sum over that filer's W-2s; a dependent's W-2 is not a filer's (the dictionary's
    `/primaryFilerHasCombatPay` and `/MFJSpouseHasCombatPay` read the filers' W-2s only)."""
    persons = facts.get("persons") or [] if isinstance(facts, dict) else []
    by = {i: 0 for i, p in enumerate(persons) if isinstance(p, dict) and p.get("role") in ("primary", "spouse")}
    for w2 in facts.get("w2s") or [] if isinstance(facts, dict) else []:
        if isinstance(w2, dict) and w2.get("person") in by:
            by[w2["person"]] += _cents_or_zero(w2.get(W2_BOX12_Q_FIELD))
    return by


def combat_pay_roles(facts: dict) -> tuple:
    """(primary has code Q, spouse has code Q) — on a non-joint return the spouse row is not a
    filer of this return, so its W-2s are not read here."""
    persons = facts.get("persons") or []
    by = combat_pay_by_filer(facts)
    joint = facts.get("filing_status") == "mfj"
    primary = any(by.get(i, 0) > 0 for i, p in enumerate(persons) if isinstance(p, dict) and p.get("role") == "primary")
    spouse = joint and any(by.get(i, 0) > 0 for i, p in enumerate(persons) if isinstance(p, dict) and p.get("role") == "spouse")
    return primary, spouse


def combat_pay_elections_reached(facts: dict) -> list:
    """the elections a return reaches, in the ask order. The Form 1040 line 1i election
    once any filer's W-2 carries code Q above 0 (measured: unanswered, line 1i is a Placeholder —
    the credit alone falls back to the dictionary's own comparison fact, the printed line does
    not); the Form 2441 Part II election when care expenses are on the return too (measured:
    unanswered, the credit is a Placeholder 0 and line 24 is served 1,100 higher); the Part III
    election when dependent care benefits are reported too (measured: unanswered, every served
    line is a Placeholder). The dictionary's Part III gate also asks that a filer's base wages
    be under the exclusion maximum; asking past that gate is inert (measured: an election sent
    on a return that does not read it changes nothing), so the wider reach is the one taken. A
    carryover with no box 10 is refused before this, so `dcb_reported` is the whole of
    the dictionary's `/hasReportedDependentCareBenefits` here."""
    if not isinstance(facts, dict):
        return []
    primary, spouse = combat_pay_roles(facts)
    if not (primary or spouse):
        return []
    reached = [COMBAT_ELECTION_FIELD]
    if care_expenses_entered(facts) > 0:
        reached.append(CDCC_COMBAT_ELECTION_FIELD)
    if dcb_reported(facts):
        reached.append(DCB_COMBAT_ELECTION_FIELD)
    return reached


def combat_pay_option(facts: dict, field: str, choice) -> str:
    """The dictionary's `/combatPayOptions` literal for the service's choice, by which filers
    carry code Q. `own` → usePrimaryCombatPay when only the primary has it, else
    usePrimaryNotSpouseCombatPay; `spouse` likewise; `both` only when both do; `none` →
    noCombatPay. A choice naming a filer with no code Q is refused by name — the dictionary
    would accept it and block submission (`/claimedSpouseCombatPayWithoutMFJ`) or read it as
    none, both in silence."""
    if choice not in COMBAT_ELECTION_CHOICES:
        raise ServiceFactsError(
            f"{field} {choice!r} is not one of the combat pay election's choices "
            f"({', '.join(COMBAT_ELECTION_CHOICES)}); refused rather than guessed")
    primary, spouse = combat_pay_roles(facts)
    if choice == "none":
        return "noCombatPay"
    if choice == "own":
        if not primary:
            raise ServiceFactsError(
                f"{field} is 'own' but no W-2 of the primary filer carries box 12 code Q — "
                f"the election can only name a filer whose W-2 reports nontaxable combat pay; "
                f"refused rather than sent")
        return "usePrimaryNotSpouseCombatPay" if spouse else "usePrimaryCombatPay"
    if choice == "spouse":
        if not spouse:
            raise ServiceFactsError(
                f"{field} is 'spouse' but no W-2 of a spouse on this return carries box 12 "
                f"code Q (on a separate return a spouse's W-2 is not this return's) — the "
                f"election can only name a filer whose W-2 reports nontaxable combat pay; "
                f"refused rather than sent")
        return "useSpouseNotPrimaryCombatPay" if primary else "useSpouseCombatPay"
    if not (primary and spouse):
        raise ServiceFactsError(
            f"{field} is 'both' but only one filer's W-2 carries box 12 code Q; answer 'own' "
            f"or 'spouse' for that filer, or 'none'; refused rather than sent")
    return "useBothCombatPay"


def refuse_misplaced_combat_pay_answers(facts: dict) -> None:
    """An election answered where the answers so far do not reach it, a choice outside
    the four, or a choice naming a filer with no code Q, is refused by name rather than dropped
    or sent."""
    if not isinstance(facts, dict):
        return
    reached = combat_pay_elections_reached(facts)
    for field in (COMBAT_ELECTION_FIELD, CDCC_COMBAT_ELECTION_FIELD, DCB_COMBAT_ELECTION_FIELD):
        if field not in facts:
            continue
        if field not in reached:
            raise ServiceFactsError(
                f"{field} is answered where the answers so far do not reach it — it is asked on "
                f"a return whose W-2 box 12 carries code Q (nontaxable combat pay)"
                + (", with care expenses on the return" if field == CDCC_COMBAT_ELECTION_FIELD else "")
                + (", with dependent care benefits reported" if field == DCB_COMBAT_ELECTION_FIELD else "")
                + "; refused rather than dropped")
        combat_pay_option(facts, field, facts[field])


def _require_combat_pay_answers(facts: dict) -> None:
    """every reached election is answered — the backstop behind `gaps.gaps_for`, which
    asks first. Unanswered, the dictionary leaves the line, the credit or the whole return a
    Placeholder (measured), never a figure."""
    if not isinstance(facts, dict):
        return
    for field in combat_pay_elections_reached(facts):
        if field not in facts:
            raise FactsSchemaError(
                f"{field} is asked on this return — {COMBAT_ELECTION_LINE[field]} — once a "
                f"filer's W-2 box 12 carries code Q; answer own, spouse, both or none "
                f"(prepare_return asks it as a gap), not a default")


def _combat_section(f: dict, facts: dict) -> None:
    """the three elections as the dictionary's own option literals. Code Q itself is
    emitted with the other carried box 12 amounts (`/formW2s/*/writableCombatPay`, Schedule 8812
    line 18b unconditionally)."""
    for field in combat_pay_elections_reached(facts):
        if field in facts:
            f[COMBAT_ELECTION_EMISSION[field]] = _enum("/combatPayOptions",
                                                       combat_pay_option(facts, field, facts[field]))


def hsa_funding_distribution_total(facts: dict, person_index: int) -> int:
    """the cents of qualified HSA funding distribution on this filer's IRA Forms 1099-R."""
    if not isinstance(facts, dict):
        return 0
    return sum(_cents_or_zero(it.get(R1099_HFD_FIELD)) for it in facts.get("r1099s") or []
               if isinstance(it, dict) and it.get("person") == person_index and it.get("ira_sep_simple"))


def hsa_funding_r1099_reached(facts: dict, r1099_index: int) -> bool:
    """the funding-distribution amount is asked on an IRA Form 1099-R (the IRA/SEP/SIMPLE
    box checked) of a filer who answered yes to `hsa_funding_distribution` where that question
    is reached. Measured: the transfer leaves Form 1040 line 4b and lands on Form 8889 line 10
    (3,000 excluded: 1,235.00 → 928.00)."""
    items = facts.get("r1099s") or [] if isinstance(facts, dict) else []
    if r1099_index >= len(items) or not isinstance(items[r1099_index], dict):
        return False
    item = items[r1099_index]
    if not item.get("ira_sep_simple"):
        return False
    i = item.get("person")
    persons = facts.get("persons") or []
    if not isinstance(i, int) or i >= len(persons) or not isinstance(persons[i], dict):
        return False
    return (persons[i].get(HSA_FUNDING_FIELD) is True
            and HSA_FUNDING_FIELD in hsa_questions_reached(facts, i))


def r1099_direct_rollover(item: dict) -> bool:
    """an IRA/SEP/SIMPLE Form 1099-R whose box 7 code contains G or H — a direct rollover
    (the dictionary's `isDirectRollover` reads the same two letters)."""
    return (isinstance(item, dict) and bool(item.get("ira_sep_simple"))
            and any(c in str(item.get("distribution_code", "")).upper() for c in "GH"))


def refuse_rollover_beside_funding_distribution(facts: dict) -> None:
    """a direct-rollover code beside a qualified HSA funding distribution on the same
    Form 1099-R is refused by name — a direct rollover is not a transfer into an HSA, and the
    dictionary's line 4c election is one choice."""
    for j, item in enumerate(facts.get("r1099s") or [] if isinstance(facts, dict) else []):
        if r1099_direct_rollover(item) and _cents_or_zero(item.get(R1099_HFD_FIELD)) > 0:
            raise ServiceFactsError(
                f"r1099s[{j}] carries a direct-rollover code ({item.get('distribution_code')}) "
                f"and a qualified HSA funding distribution — a distribution rolled over directly "
                f"into another retirement account was not transferred into an HSA; refused "
                f"rather than sent as either")


def _r1099_recipient(facts: dict, item: dict):
    """The filer row a Form 1099-R belongs to, or None."""
    i = item.get("person") if isinstance(item, dict) else None
    persons = facts.get("persons") or [] if isinstance(facts, dict) else []
    if not isinstance(i, int) or isinstance(i, bool) or i >= len(persons) or not isinstance(persons[i], dict):
        return None
    return persons[i]


def _r1099_fully_taxable_ira(item: dict) -> bool:
    """An IRA/SEP/SIMPLE Form 1099-R whose box 2a equals box 1 above 0 and is not marked
    undetermined — the QCD's signature on the form (the custodian does not know where the money
    went), and the only shape the dictionary's `isSupportedQcdElection` admits."""
    if not isinstance(item, dict) or not item.get("ira_sep_simple"):
        return False
    if item.get("taxable_amount_not_determined"):
        return False
    gross = _cents_or_zero(item.get("gross_distribution_cents"))
    return gross > 0 and "taxable_amount_cents" in item and _cents_or_zero(item.get("taxable_amount_cents")) == gross


def qcd_recipient_age_status(person: dict) -> str:
    """`eligible` (born through 1953 — the dictionary's bound by year alone), `ambiguous` (born
    January 1954, or 1954 with no month: the bound admits January 1 only, and this service
    carries no day), or `refused` (February 1954 onward — the bound decides them by month)."""
    year, month = _birth_year_month(person)
    if year is None:
        return "refused"
    if year < QCD_AGE_BOUND_YEAR:
        return "eligible"
    if year == QCD_AGE_BOUND_YEAR and ("birth_month" not in person or month == 1):
        return "ambiguous"
    return "refused"


def qcd_r1099_reached(facts: dict, r1099_index: int) -> bool:
    """the qualified-charitable-distribution amount is asked on an IRA Form 1099-R with box
    2a equal to box 1 (above 0), no direct-rollover code, no HSA funding distribution, whose
    recipient was born through 1953. Elsewhere the dictionary's arm cannot admit it, and a
    positive answer is refused by name."""
    items = facts.get("r1099s") or [] if isinstance(facts, dict) else []
    if r1099_index >= len(items) or not isinstance(items[r1099_index], dict):
        return False
    item = items[r1099_index]
    if not _r1099_fully_taxable_ira(item) or r1099_direct_rollover(item):
        return False
    if _cents_or_zero(item.get(R1099_HFD_FIELD)) > 0:
        return False
    person = _r1099_recipient(facts, item)
    return person is not None and qcd_recipient_age_status(person) == "eligible"


def _pso_item_asked(item) -> bool:
    """the officer question on a Form 1099-R whose box 7 the dictionary asks about — a code
    with a 2 or a 7 and no B (`flowAskAboutPublicSafetyOfficer`) — on a form without the
    IRA/SEP/SIMPLE box (the exclusion does not reach an IRA, and the dictionary refuses a yes there)."""
    if not isinstance(item, dict) or item.get("ira_sep_simple"):
        return False
    code = str(item.get("distribution_code", "")).upper()
    return any(c in code for c in "27") and "B" not in code


def _pso_item_premiums_asked(item) -> bool:
    return _pso_item_asked(item) and item.get(R1099_PSO_FIELD) is True


def _pso_item_amount_asked(item) -> bool:
    return _pso_item_premiums_asked(item) and item.get(R1099_PSO_PREMIUMS_FIELD) is True


def _r1099_item(facts, r1099_index):
    items = facts.get("r1099s") or [] if isinstance(facts, dict) else []
    return items[r1099_index] if r1099_index < len(items) else None


def pso_question_reached(facts: dict, r1099_index: int) -> bool:
    """see `_pso_item_asked` — the officer question on this form."""
    return _pso_item_asked(_r1099_item(facts, r1099_index))


def pso_premiums_question_reached(facts: dict, r1099_index: int) -> bool:
    """the plan-paid-premiums question behind the officer's yes."""
    return _pso_item_premiums_asked(_r1099_item(facts, r1099_index))


def pso_amount_reached(facts: dict, r1099_index: int) -> bool:
    """the amount behind the second yes — required there: a yes with no amount is the
    dictionary's own knockout rather than an exclusion of 0."""
    return _pso_item_amount_asked(_r1099_item(facts, r1099_index))


def mra_question_reached(facts: dict, r1099_index: int) -> bool:
    """the minimum-retirement-age question, on a non-IRA Form 1099-R whose box 7 carries only
    the disability code (the dictionary's `hasDisabilityCodeOnly`: 3, 3D or D3)."""
    item = _r1099_item(facts, r1099_index)
    return (isinstance(item, dict) and not item.get("ira_sep_simple")
            and _r1099_code(item) in R1099_DISABILITY_CODES)


def refuse_misplaced_mra_answer(facts: dict) -> None:
    """an answer on a form the question does not reach is refused by name, not dropped."""
    if not isinstance(facts, dict):
        return
    for j, item in enumerate(facts.get("r1099s") or []):
        if isinstance(item, dict) and R1099_MRA_FIELD in item and not mra_question_reached(facts, j):
            raise ServiceFactsError(
                f"r1099s[{j}].{R1099_MRA_FIELD} is answered where the answers so far do not reach it — "
                "it is asked on a Form 1099-R whose box 7 code is 3 (disability) without the "
                "IRA/SEP/SIMPLE box; refused rather than dropped")


def refuse_misplaced_pso_answers(facts: dict) -> None:
    """an answer on a form the chain does not reach, or a link answered past an earlier no,
    is refused by name rather than dropped or sent."""
    if not isinstance(facts, dict):
        return
    for j, item in enumerate(facts.get("r1099s") or []):
        if not isinstance(item, dict):
            continue
        if R1099_PSO_AMOUNT_FIELD in item:
            v = item[R1099_PSO_AMOUNT_FIELD]
            if isinstance(v, bool) or not isinstance(v, int):
                raise FactsSchemaError(f"r1099s[{j}].{R1099_PSO_AMOUNT_FIELD} is not an amount")
            if v < 0:
                raise FactsSchemaError(f"r1099s[{j}].{R1099_PSO_AMOUNT_FIELD} is not an amount (negative); "
                                       f"Must be 0 or more")
        for field, reached, where_asked in (
                (R1099_PSO_FIELD, pso_question_reached, "on a Form 1099-R with a box 7 code of 2 or 7 (no B) without the IRA/SEP/SIMPLE box — the exclusion (IRC 402(l)) reaches a government plan's distribution, not an IRA's"),
                (R1099_PSO_PREMIUMS_FIELD, pso_premiums_question_reached, "once the person answers yes to being an eligible retired public safety officer"),
                (R1099_PSO_AMOUNT_FIELD, pso_amount_reached, "once the plan is answered to have paid the premiums")):
            if field in item and not reached(facts, j):
                raise ServiceFactsError(
                    f"r1099s[{j}].{field} is answered where the answers so far do not reach it — "
                    f"it is asked {where_asked}; refused rather than dropped")


def _r1099_code(item) -> str:
    return str(item.get("distribution_code", "")).upper() if isinstance(item, dict) else ""


def _db_code_c(item) -> bool:
    """a Form 1099-R the dictionary reads as a reportable death benefit by its code alone — C, CD
    or DC (`box1IsIdentifiedAsTheReportableDeathBenefit`, exact codes) — on a non-IRA form."""
    return isinstance(item, dict) and not item.get("ira_sep_simple") and _r1099_code(item) in R1099_CODE_C_FAMILY


def _db_code_4(item) -> bool:
    """a code 4, 4D or D4 form — the death benefit only where the filer says box 1 is it."""
    return isinstance(item, dict) and not item.get("ira_sep_simple") and _r1099_code(item) in R1099_CODE_4_FAMILY


def _db_dated(item) -> bool:
    return (_db_code_c(item) or _db_code_4(item)) and isinstance(item.get(R1099_DATE_FIELD), str) and item[R1099_DATE_FIELD] != ""


def _db_box1_asked(item) -> bool:
    return _db_code_4(item) and _db_dated(item)


def _db_sale_asked(item) -> bool:
    return _db_dated(item) and (_db_code_c(item) or item.get(R1099_DB_BOX1_FIELD) is True)


def _db_consideration_asked(item) -> bool:
    return _db_sale_asked(item) and item.get(R1099_DB_SALE_FIELD) is False


def _db_carryover_asked(item) -> bool:
    return _db_consideration_asked(item) and item.get(R1099_DB_CONSIDERATION_FIELD) is True


def _db_basis_asked(item) -> bool:
    if not _db_sale_asked(item):
        return False
    if item.get(R1099_DB_SALE_FIELD) is True:
        return True
    return (_db_carryover_asked(item) and item.get(R1099_DB_CARRYOVER_FIELD) is False
            and item.get(R1099_DB_RELATED_FIELD) is False)


def death_benefit_date_required(facts: dict, r1099_index: int) -> bool:
    """box 13 is a required gap on a code C family form — the payer completes it for every
    reportable death benefit, and the dictionary prices nothing without it."""
    return _db_code_c(_r1099_item(facts, r1099_index))


def death_benefit_date_invited(facts: dict, r1099_index: int) -> bool:
    """on a code 4 family form box 13 is invited — blank is an ordinary distribution to a
    beneficiary, taxed as box 2a reports, and stated."""
    return _db_code_4(_r1099_item(facts, r1099_index))


def death_benefit_date_asked(facts: dict, r1099_index: int) -> bool:
    item = _r1099_item(facts, r1099_index)
    return _db_code_c(item) or _db_code_4(item)


def death_benefit_box1_reached(facts: dict, r1099_index: int) -> bool:
    return _db_box1_asked(_r1099_item(facts, r1099_index))


def death_benefit_sale_reached(facts: dict, r1099_index: int) -> bool:
    return _db_sale_asked(_r1099_item(facts, r1099_index))


def death_benefit_consideration_reached(facts: dict, r1099_index: int) -> bool:
    return _db_consideration_asked(_r1099_item(facts, r1099_index))


def death_benefit_carryover_reached(facts: dict, r1099_index: int) -> bool:
    """Rows 44 and 45 together, behind a consideration yes — either alone frees the benefit."""
    return _db_carryover_asked(_r1099_item(facts, r1099_index))


def death_benefit_basis_reached(facts: dict, r1099_index: int) -> bool:
    return _db_basis_asked(_r1099_item(facts, r1099_index))


DEATH_BENEFIT_REACHED = {
    R1099_DATE_FIELD: death_benefit_date_asked,
    R1099_DB_BOX1_FIELD: death_benefit_box1_reached,
    R1099_DB_SALE_FIELD: death_benefit_sale_reached,
    R1099_DB_CONSIDERATION_FIELD: death_benefit_consideration_reached,
    R1099_DB_CARRYOVER_FIELD: death_benefit_carryover_reached,
    R1099_DB_RELATED_FIELD: death_benefit_carryover_reached,
    R1099_DB_BASIS_FIELD: death_benefit_basis_reached,
}


def refuse_misplaced_death_benefit_answers(facts: dict, tax_year: int = 2025) -> None:
    """box 13's shape (the form's date as YYYY-MM-DD, no later than the dictionary's own limit —
    the first day of the following year), and an answer where the chain does not reach it, refused
    by name rather than dropped or sent."""
    if not isinstance(facts, dict):
        return
    for j, item in enumerate(facts.get("r1099s") or []):
        if not isinstance(item, dict):
            continue
        if R1099_DATE_FIELD in item:
            v = item[R1099_DATE_FIELD]
            if not isinstance(v, str) or not _re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", v):
                raise FactsSchemaError(f"r1099s[{j}].{R1099_DATE_FIELD} is not a date; Must be the box 13 date as YYYY-MM-DD")
            try:
                d = _dt.date.fromisoformat(v)
            except ValueError:
                raise FactsSchemaError(f"r1099s[{j}].{R1099_DATE_FIELD} is not a date; Must be the box 13 date as YYYY-MM-DD")
            if d > _dt.date(int(tax_year) + 1, 1, 1):
                raise FactsSchemaError(f"r1099s[{j}].{R1099_DATE_FIELD} is not a date of payment for this return; "
                                       f"Must be no later than {int(tax_year) + 1}-01-01")
        if R1099_DB_BASIS_FIELD in item:
            v = item[R1099_DB_BASIS_FIELD]
            if isinstance(v, bool) or not isinstance(v, int):
                raise FactsSchemaError(f"r1099s[{j}].{R1099_DB_BASIS_FIELD} is not an amount")
            if v < 0:
                raise FactsSchemaError(f"r1099s[{j}].{R1099_DB_BASIS_FIELD} is not an amount (negative); Must be 0 or more")
        for field, reached, where_asked in (
                (R1099_DATE_FIELD, death_benefit_date_asked, "on a Form 1099-R with a box 7 code of C, CD, DC, 4, 4D or D4 without the IRA/SEP/SIMPLE box — the payer's date of payment for a reportable death benefit (IRC 6050Y)"),
                (R1099_DB_BOX1_FIELD, death_benefit_box1_reached, "on a code 4, 4D or D4 form with a date in box 13 (a code C form states it by its code)"),
                (R1099_DB_SALE_FIELD, death_benefit_sale_reached, "on a code C form with a date in box 13, or a code 4 form whose box 1 is answered to be the death benefit under that contract"),
                (R1099_DB_CONSIDERATION_FIELD, death_benefit_consideration_reached, "once the policy is answered not to have been acquired in a reportable policy sale"),
                (R1099_DB_CARRYOVER_FIELD, death_benefit_carryover_reached, "once the policy is answered to have been transferred for valuable consideration"),
                (R1099_DB_RELATED_FIELD, death_benefit_carryover_reached, "once the policy is answered to have been transferred for valuable consideration"),
                (R1099_DB_BASIS_FIELD, death_benefit_basis_reached, "behind a reportable policy sale, or behind a transfer for valuable consideration with neither a carryover basis nor a transfer to the insured or a related party")):
            if field in item and not reached(facts, j):
                raise ServiceFactsError(
                    f"r1099s[{j}].{field} is answered where the answers so far do not reach it — "
                    f"it is asked {where_asked}; refused rather than dropped")


def qcd_split_question_reached(facts: dict, r1099_index: int) -> bool:
    """The one-time split-interest-entity answer is asked once the amount is positive."""
    if not qcd_r1099_reached(facts, r1099_index):
        return False
    return _cents_or_zero(facts["r1099s"][r1099_index].get(R1099_QCD_FIELD)) > 0


def qcd_history_reached(facts: dict, person_index: int) -> bool:
    """The filer's post-70½ deducted-contribution history is asked once any of their Forms
    1099-R carries a positive qualified charitable distribution."""
    items = facts.get("r1099s") or [] if isinstance(facts, dict) else []
    return any(isinstance(it, dict) and it.get("person") == person_index and qcd_split_question_reached(facts, j)
               for j, it in enumerate(items))


def _r1099_has_direct_rollover_code(item: dict) -> bool:
    """Box 7 carries G or H on any form — the pension form's code too (`r1099_direct_rollover`
    is the IRA-only election derivation)."""
    return isinstance(item, dict) and any(c in str(item.get("distribution_code", "")).upper() for c in "GH")


def rollover_r1099_reached(facts: dict, r1099_index: int) -> bool:
    """the rolled-over amount is asked on a Form 1099-R with box 2a equal to box 1 (above 0,
    not marked undetermined), no direct-rollover code, no HSA funding distribution and no
    qualified charitable distribution on the form — one exclusion per form, and the shape every
    cell was measured on."""
    items = facts.get("r1099s") or [] if isinstance(facts, dict) else []
    if r1099_index >= len(items) or not isinstance(items[r1099_index], dict):
        return False
    item = items[r1099_index]
    if not _r1099_fully_taxable_ira(dict(item, ira_sep_simple=True)) or _r1099_has_direct_rollover_code(item):
        return False
    if _cents_or_zero(item.get(R1099_HFD_FIELD)) > 0 or _cents_or_zero(item.get(R1099_QCD_FIELD)) > 0:
        return False
    return _r1099_recipient(facts, item) is not None


def rollover_one_per_year_reached(facts: dict, r1099_index: int) -> bool:
    """On an IRA form the one-rollover-per-year answer is asked behind the whole distribution
    rolled over — the only IRA shape this unit figures (a partial one is refused by name for
    the engine defect, so its answer would never be read)."""
    if not rollover_r1099_reached(facts, r1099_index):
        return False
    item = facts["r1099s"][r1099_index]
    amount = _cents_or_zero(item.get(R1099_ROLLOVER_FIELD))
    return bool(item.get("ira_sep_simple")) and amount > 0 and amount == _cents_or_zero(item.get("gross_distribution_cents"))


def refuse_misplaced_rollover_answers(facts: dict) -> None:
    """A positive rolled-over amount where the frontier's arm was not measured, a partial one
    on an IRA form, one above box 2a, or a one-per-year answer with no amount, is
    refused by name rather than dropped or sent."""
    if not isinstance(facts, dict):
        return
    for j, item in enumerate(facts.get("r1099s") or []):
        if not isinstance(item, dict):
            continue
        if R1099_ROLLOVER_FIELD in item:
            v = item[R1099_ROLLOVER_FIELD]
            if isinstance(v, bool) or not isinstance(v, int):
                raise FactsSchemaError(f"r1099s[{j}].{R1099_ROLLOVER_FIELD} is not an amount")
            if v < 0:
                raise FactsSchemaError(f"r1099s[{j}].{R1099_ROLLOVER_FIELD} is not an amount (negative); "
                                       f"Must be 0 or more")
            where = f"r1099s[{j}].{R1099_ROLLOVER_FIELD}"
            if v > 0 and not rollover_r1099_reached(facts, j):
                if _r1099_has_direct_rollover_code(item):
                    raise ServiceFactsError(
                        f"{where} is answered beside a direct-rollover code ({item.get('distribution_code')}) — "
                        f"the payer rolled that distribution over directly, and the code carries it; refused "
                        f"rather than sent as both")
                if _cents_or_zero(item.get(R1099_HFD_FIELD)) > 0 or _cents_or_zero(item.get(R1099_QCD_FIELD)) > 0:
                    raise ServiceFactsError(
                        f"{where} is answered beside a qualified HSA funding distribution or a qualified "
                        f"charitable distribution on the same Form 1099-R — one distribution carries one "
                        f"exclusion here; refused rather than sent as either")
                raise ServiceFactsError(
                    f"{where} is answered on a Form 1099-R whose box 2a is not the whole of box 1 (or is "
                    f"marked not determined) — a rollover is figured here only where the custodian reported "
                    f"the distribution as fully taxable; refused rather than sent")
            gross = _cents_or_zero(item.get("gross_distribution_cents"))
            if v > gross:
                raise ServiceFactsError(
                    f"{where} is above this Form 1099-R's box 1 gross distribution — the part rolled over is "
                    f"part of the distribution, never more; refused rather than sent")
            if 0 < v < gross and item.get("ira_sep_simple"):
                raise ServiceFactsError(
                    f"{where} is a part of the distribution on a Form 1099-R with the IRA/SEP/SIMPLE box "
                    f"checked — at this engine pin a partial rollover on an IRA form is counted on Form 1040 "
                    f"lines 4b and 5b both; refused rather than sent until the pin moves. The "
                    f"whole distribution rolled over is figured.")
        if R1099_IRA_ONE_PER_YEAR_FIELD in item:
            if not isinstance(item[R1099_IRA_ONE_PER_YEAR_FIELD], bool):
                raise FactsSchemaError(f"r1099s[{j}].{R1099_IRA_ONE_PER_YEAR_FIELD} is not true or false")
            if not rollover_one_per_year_reached(facts, j):
                raise ServiceFactsError(
                    f"r1099s[{j}].{R1099_IRA_ONE_PER_YEAR_FIELD} is answered on a Form 1099-R that is not an "
                    f"IRA form with a rolled-over amount — the one-rollover-per-year question is asked behind "
                    f"that amount on an IRA form; refused rather than dropped")


def _require_rollover_answers(facts: dict) -> None:
    """every reached rollover question is answered — the backstop behind `gaps.gaps_for`."""
    if not isinstance(facts, dict):
        return
    for j, item in enumerate(facts.get("r1099s") or []):
        if rollover_r1099_reached(facts, j) and R1099_ROLLOVER_FIELD not in item:
            raise FactsSchemaError(
                f"r1099s[{j}].{R1099_ROLLOVER_FIELD} is asked on this Form 1099-R (box 2a the whole of box 1) "
                f"— the part rolled over into another retirement account within 60 days, 0 if none "
                f"(prepare_return asks it as a gap)")
        if rollover_one_per_year_reached(facts, j) and R1099_IRA_ONE_PER_YEAR_FIELD not in item:
            raise FactsSchemaError(
                f"r1099s[{j}].{R1099_IRA_ONE_PER_YEAR_FIELD} is asked behind a rolled-over amount on an IRA "
                f"Form 1099-R — whether it was the only IRA-to-IRA rollover in the 12 months before it "
                f"(prepare_return asks it as a gap)")


def refuse_misplaced_qcd_answers(facts: dict) -> None:
    """A positive qualified-charitable-distribution amount where the dictionary's arm
    cannot admit it, a split-interest answer with no amount, or a history on a filer no form
    of theirs reaches, is refused by name rather than dropped or sent (sent, the dictionary
    knocks the return out with words that cannot name the box)."""
    if not isinstance(facts, dict):
        return
    for j, item in enumerate(facts.get("r1099s") or []):
        if not isinstance(item, dict):
            continue
        if R1099_QCD_FIELD in item:
            v = item[R1099_QCD_FIELD]
            if isinstance(v, bool) or not isinstance(v, int):
                raise FactsSchemaError(f"r1099s[{j}].{R1099_QCD_FIELD} is not an amount")
            if v < 0:
                raise FactsSchemaError(f"r1099s[{j}].{R1099_QCD_FIELD} is not an amount (negative); "
                                       f"Must be 0 or more")
            if v > 0 and not qcd_r1099_reached(facts, j):
                where = f"r1099s[{j}].{R1099_QCD_FIELD}"
                if not item.get("ira_sep_simple"):
                    raise ServiceFactsError(
                        f"{where} is answered on a Form 1099-R without the IRA/SEP/SIMPLE box checked "
                        f"— a qualified charitable distribution comes out of an IRA; refused rather than sent")
                if r1099_direct_rollover(item):
                    raise ServiceFactsError(
                        f"{where} is answered beside a direct-rollover code ({item.get('distribution_code')}) — "
                        f"a distribution rolled over directly into another retirement account was not paid "
                        f"to a charity; refused rather than sent as either")
                if _cents_or_zero(item.get(R1099_HFD_FIELD)) > 0:
                    raise ServiceFactsError(
                        f"{where} is answered beside a qualified HSA funding distribution on the same Form "
                        f"1099-R — one distribution carries one line 4c election; refused rather than sent as either")
                if not _r1099_fully_taxable_ira(item):
                    raise ServiceFactsError(
                        f"{where} is answered on a Form 1099-R whose box 2a is not the whole of box 1 (or is "
                        f"marked not determined) — a qualified charitable distribution is figured here only "
                        f"where the custodian reported the distribution as fully taxable; refused rather than sent")
                person = _r1099_recipient(facts, item)
                status = qcd_recipient_age_status(person) if person is not None else "refused"
                if status == "ambiguous":
                    raise ServiceFactsError(
                        f"{where} is answered for a recipient born in January {QCD_AGE_BOUND_YEAR} — whether "
                        f"they were born on January 1 decides it, and this service carries no birth day; refused "
                        f"rather than sent as either")
                raise ServiceFactsError(
                    f"{where} is answered for a recipient born after January 1, {QCD_AGE_BOUND_YEAR} — a "
                    f"qualified charitable distribution is figured here for a recipient at least 71 on "
                    f"January 1, 2025 (born on or before January 1, {QCD_AGE_BOUND_YEAR}); refused rather than sent")
            if v > _cents_or_zero(item.get("taxable_amount_cents")):
                raise ServiceFactsError(
                    f"r1099s[{j}].{R1099_QCD_FIELD} is above this Form 1099-R's box 2a taxable amount — a "
                    f"qualified charitable distribution is part of the distribution it came out of, never "
                    f"more; refused rather than sent")
        if R1099_QCD_SPLIT_FIELD in item:
            if not isinstance(item[R1099_QCD_SPLIT_FIELD], bool):
                raise FactsSchemaError(f"r1099s[{j}].{R1099_QCD_SPLIT_FIELD} is not true or false")
            if not qcd_split_question_reached(facts, j):
                raise ServiceFactsError(
                    f"r1099s[{j}].{R1099_QCD_SPLIT_FIELD} is answered on a Form 1099-R that carries no "
                    f"qualified charitable distribution — the split-interest question is asked behind a "
                    f"positive amount; refused rather than dropped")
    for i, person in enumerate(facts.get("persons") or []):
        if isinstance(person, dict) and QCD_HISTORY_FIELD in person:
            v = person[QCD_HISTORY_FIELD]
            if isinstance(v, bool) or not isinstance(v, int):
                raise FactsSchemaError(f"persons[{i}].{QCD_HISTORY_FIELD} is not an amount")
            if v < 0:
                raise FactsSchemaError(f"persons[{i}].{QCD_HISTORY_FIELD} is not an amount (negative); "
                                       f"Must be 0 or more")
            if not qcd_history_reached(facts, i):
                raise ServiceFactsError(
                    f"persons[{i}].{QCD_HISTORY_FIELD} is answered on a filer none of whose Forms 1099-R "
                    f"carries a qualified charitable distribution — the history is asked behind that "
                    f"amount; refused rather than dropped")


def _require_qcd_answers(facts: dict) -> None:
    """every reached qualified-charitable-distribution question is answered — the backstop
    behind `gaps.gaps_for`, which asks first."""
    if not isinstance(facts, dict):
        return
    for j, item in enumerate(facts.get("r1099s") or []):
        if qcd_r1099_reached(facts, j) and R1099_QCD_FIELD not in item:
            raise FactsSchemaError(
                f"r1099s[{j}].{R1099_QCD_FIELD} is asked on this IRA Form 1099-R (box 2a the whole of "
                f"box 1, a recipient born through {QCD_AGE_BOUND_YEAR - 1}) — the part the trustee paid "
                f"directly to a charity, 0 if none (prepare_return asks it as a gap)")
        if qcd_split_question_reached(facts, j) and R1099_QCD_SPLIT_FIELD not in item:
            raise FactsSchemaError(
                f"r1099s[{j}].{R1099_QCD_SPLIT_FIELD} is asked behind a qualified charitable distribution — "
                f"whether it was the one-time election to a split-interest entity (prepare_return asks it as a gap)")
    for i, person in enumerate(facts.get("persons") or []):
        if qcd_history_reached(facts, i) and QCD_HISTORY_FIELD not in person:
            raise FactsSchemaError(
                f"persons[{i}].{QCD_HISTORY_FIELD} is asked once a Form 1099-R of this filer carries a "
                f"qualified charitable distribution — the traditional IRA contributions deducted in earlier "
                f"years at 70½ or older not already offset, 0 if none (prepare_return asks it as a gap)")


def _qcd_history_section(f: dict, facts: dict) -> None:
    """the filer's post-70½ deducted-contribution history, on the dictionary's per-filer
    root writable — sent only where reached (the dictionary reads it only behind a `qcd` election)."""
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict) or not qcd_history_reached(facts, i):
            continue
        role = {"primary": "primary", "spouse": "secondary"}.get(person.get("role"))
        if role is None:
            continue
        f[f"/{role}FilerQcdOffsetCarryover"] = _dollar(person[QCD_HISTORY_FIELD])


def hsa_medicare_onset_asked(facts: dict, person_index: int) -> bool:
    """the month Medicare enrollment began is asked of a filer row that answered Medicare
    for part of the year, where the vector can govern (not claimable; the opened spouse without an
    HSA stays on their own chain). on a separate return too — the vector governs there
    only with the spouse's twelve rows beside it (`hsa_mfs_spouse_months_asked`), which the
    chain then asks whatever the line 6 check says. Reads this row's answers only."""
    if not isinstance(facts, dict):
        return False
    persons = facts.get("persons") or []
    person = persons[person_index] if person_index < len(persons) else None
    if not isinstance(person, dict) or person.get("someone_can_claim_you") is True:
        return False
    if person.get("role") not in ("primary", "spouse"):
        return False
    if (hsa_w2_contributions(facts, person_index) <= 0 and not hsa_own_contributions(person)
            and not hsa_spouse_coverage_opener(facts, person_index)):   # the opened spouse too
        return False
    return person.get(HSA_MEDICARE_FIELD) == "part_of_year"


def hsa_spouse_chain(facts: dict, person_index: int) -> bool:
    """this row is on the spouse-coverage chain — no HSA activity of its own, opened by the other
    spouse's transfer or shaped vector."""
    persons = facts.get("persons") or [] if isinstance(facts, dict) else []
    person = persons[person_index] if person_index < len(persons) else None
    return (isinstance(person, dict) and hsa_w2_contributions(facts, person_index) <= 0
            and not hsa_own_contributions(person) and hsa_spouse_coverage_opener(facts, person_index))


def hsa_medicare_answer_carried(facts: dict, person_index: int) -> bool:
    """the Medicare answer the vector can carry — none; part of the year with the onset month
    answered; all year on the spouse chain, and on a filer row with HSA activity who
    cannot be claimed as a dependent — twelve months of yes, line 3 of zero, the code W amount the
    year's excess (measured: 1,415.00); a claimed filer stays on the legacy chain."""
    persons = facts.get("persons") or [] if isinstance(facts, dict) else []
    person = persons[person_index] if person_index < len(persons) else None
    if not isinstance(person, dict):
        return False
    answer = person.get(HSA_MEDICARE_FIELD)
    if answer == "none":
        return True
    if answer == "part_of_year":
        return hsa_medicare_onset_asked(facts, person_index) and person.get(HSA_MEDICARE_ONSET_FIELD) in HSA_TRANSFER_MONTHS
    if answer != "all_year":
        return False
    if hsa_spouse_chain(facts, person_index):
        return True
    # a filer with HSA activity on Medicare all year — carried (twelve months of yes) unless
    # they can be claimed as a dependent (the legacy chain)
    return (person.get("role") in ("primary", "spouse") and person.get("someone_can_claim_you") is not True
            and (hsa_w2_contributions(facts, person_index) > 0 or hsa_own_contributions(person)))


def hsa_medicare_months(facts: dict, person_index: int) -> list:
    """The twelve Medicare answers sent with the vector: no throughout; — no before the
    enrollment month and yes from it through December; or — yes throughout for all year."""
    persons = facts.get("persons") or [] if isinstance(facts, dict) else []
    person = persons[person_index] if person_index < len(persons) else None
    onset = person.get(HSA_MEDICARE_ONSET_FIELD) if isinstance(person, dict) else None
    if hsa_medicare_onset_asked(facts, person_index) and onset in HSA_TRANSFER_MONTHS:
        first = HSA_TRANSFER_MONTHS.index(onset)
        return [m >= first for m in range(12)]
    if isinstance(person, dict) and person.get(HSA_MEDICARE_FIELD) == "all_year" and hsa_medicare_answer_carried(facts, person_index):
        return [True] * 12                       # the spouse on Medicare all year; a filer too
    return [False] * 12


def hsa_vector_shaped(facts: dict, person_index: int) -> bool:
    """this filer's vector is not the plain all-year prefill — the months were asked
   , or the Medicare onset month was asked and answered — so the limitation is the
    chart's, not the type's base, and any transfer decides (the cap is not computable without
    the month); on a joint return the other spouse's coverage is then asked (the opener).
    Answer-only: reads one row."""
    persons = facts.get("persons") or [] if isinstance(facts, dict) else []
    person = persons[person_index] if person_index < len(persons) else None
    if not isinstance(person, dict):
        return False
    if hsa_w2_contributions(facts, person_index) <= 0 and not hsa_own_contributions(person):
        return False                         # a row without HSA activity has no transfer to decide,
                                             # and the two spouses' openers would otherwise read each other
    if hsa_explicit_vector(facts, person_index) is not None:
        return True
    if person.get(HSA_MEDICARE_FIELD) == "all_year" and hsa_medicare_answer_carried(facts, person_index):
        return True                              # twelve months of yes — line 3 is 0
    return (hsa_medicare_onset_asked(facts, person_index)
            and person.get(HSA_MEDICARE_ONSET_FIELD) in HSA_TRANSFER_MONTHS)


def hsa_months_asked(facts: dict, person_index: int) -> bool:
    """the twelve coverage months are asked — HDHP coverage for part of the year, or the
    `both` type, with the type answered — of a filer the vector can govern for: not one who can
    be claimed as a dependent (the legacy chain) and not on a separate return
    (the spouse's rows are asked there; the filer's own months on a separate return are not yet
    governed — the line 6 check is shown only behind all-year coverage, so a part-year filer
    collapsed onto family could never say whether the spouse holds an HSA). Reads this row's
    answers only, so the two spouses' openers can each ask it."""
    if not isinstance(facts, dict) or facts.get("filing_status") == "mfs":
        return False
    persons = facts.get("persons") or []
    person = persons[person_index] if person_index < len(persons) else None
    if not isinstance(person, dict) or person.get("someone_can_claim_you") is True:
        return False
    if not hsa_medicare_answer_carried(facts, person_index):
        return False
    if person.get(HSA_COVERAGE_FIELD) == "part_of_year":
        return person.get(HSA_TYPE_FIELD) in ("self_only", "family", "both")
    return person.get(HSA_COVERAGE_FIELD) == "all_year" and person.get(HSA_TYPE_FIELD) == "both"


def hsa_testing_period_asked(facts: dict, person_index: int) -> bool:
    """the testing-period month is asked where the dictionary reads it — a filer whose
    HDHP coverage ran for part of the year, with the twelve months answered and a funding
    distribution above 0. The `both` type keeps the all-year status and is eligible all year; an
    all-year filer is never offered the question (register row 4: the writable wins on a
    contradiction). Reads this row's answers and the filer's forms only."""
    persons = facts.get("persons") or [] if isinstance(facts, dict) else []
    person = persons[person_index] if person_index < len(persons) else None
    if not isinstance(person, dict) or hsa_funding_distribution_total(facts, person_index) <= 0:
        return False
    if facts.get("filing_status") == "mfs":
        # on a separate return a transfer beside a governing vector is the dictionary's own
        # knockout whatever the testing answer (measured: the exclusion cap does not compute there,
        # with or without the month), so the question would be a dead one; an answer is refused
        # by name as unreached.
        return False
    if person.get(HSA_MEDICARE_FIELD) == "all_year" and hsa_medicare_answer_carried(facts, person_index):
        # Medicare all year is no eligible month at all — a transfer beside it is the
        # dictionary's own knockout whatever the testing answer, so the question would be a dead
        # one; an answer is refused by name as unreached.
        return False
    if person.get(HSA_COVERAGE_FIELD) == "part_of_year":
        return hsa_explicit_vector(facts, person_index) is not None
    # Medicare for part of the year is not eligibility all year either — with the vector
    # the chain carries (the asked months, or the all-year one-type prefill), answer-only here
    if not hsa_medicare_onset_asked(facts, person_index) or person.get(HSA_MEDICARE_ONSET_FIELD) not in HSA_TRANSFER_MONTHS:
        return False
    if hsa_explicit_vector(facts, person_index) is not None:
        return True
    return (person.get(HSA_COVERAGE_FIELD) == "all_year" and person.get(HSA_TYPE_FIELD) in ("self_only", "family")
            and person.get("someone_can_claim_you") is not True)


def hsa_explicit_vector(facts: dict, person_index: int):
    """the twelve literals of an asked vector, every month answered; None elsewhere."""
    if not hsa_months_asked(facts, person_index):
        return None
    person = facts["persons"][person_index]
    if not all(m in person for m in HSA_MONTH_FIELDS):
        return None
    literals = [HSA_MONTH_LITERALS.get(person[m]) for m in HSA_MONTH_FIELDS]
    return None if None in literals else literals


def hsa_vector_months(facts: dict, person_index: int):
    """The twelve literals this filer's vector is sent with: the asked months, else
    twelve of the prefilled all-year literal (the opened spouse); None where no vector is sent."""
    explicit = hsa_explicit_vector(facts, person_index)
    if explicit:
        return explicit
    literal = hsa_vector_prefill(facts, person_index)
    return [literal] * 12 if literal else None


def hsa_transfer_decides(facts: dict, person_index: int) -> bool:
    """this filer's transfer month decides the cap — an asked vector with any funding
    distribution (the service does not re-derive the limitation chart), or the excess test on the
    prefilled one: the total above the base limitation for the carried type."""
    persons = facts.get("persons") or [] if isinstance(facts, dict) else []
    person = persons[person_index] if person_index < len(persons) else None
    if not isinstance(person, dict):
        return False
    total = hsa_funding_distribution_total(facts, person_index)
    if person.get(HSA_MEDICARE_FIELD) == "all_year" and hsa_medicare_answer_carried(facts, person_index):
        # the exclusion cap is 0 on Medicare all year — a transfer is the dictionary's own
        # knockout with or without the month (measured), so the month would be a dead question
        return False
    if hsa_vector_shaped(facts, person_index):
        return total > 0
    if hsa_vector_prefill(facts, person_index) is None:
        return False
    limit = HSA_BASE_LIMIT_CENTS.get(person.get(HSA_TYPE_FIELD))
    return limit is not None and total > limit


def hsa_vector_prefill(facts: dict, person_index: int):
    """the coverage literal (`selfOnly` / `family`) the filer's twelve-month vector is
    prefilled with — a filer whose Form 8889 Part I chain is carried through the other-coverage
    answer (no Medicare, HDHP coverage all year, one type, no other coverage); None elsewhere
    (part-year coverage, the `both` type: the legacy chain, byte for byte)."""
    persons = facts.get("persons") or [] if isinstance(facts, dict) else []
    person = persons[person_index] if person_index < len(persons) else None
    if not isinstance(person, dict):
        return None
    if hsa_months_asked(facts, person_index):
        return None                          # the asked months are the vector, not a prefill
    reached = hsa_questions_reached(facts, person_index)
    if HSA_FUNDING_FIELD not in reached:
        # the spouse without an HSA, asked their coverage on a joint return — no coverage
        # is twelve months of none; all-year coverage of one type is twelve months of it.
        if not hsa_spouse_coverage_opener(facts, person_index):
            return None
        if person.get(HSA_COVERAGE_FIELD) == "none":
            return "none"
        if HSA_TYPE_FIELD in reached:
            return HSA_VECTOR_LITERALS.get(person.get(HSA_TYPE_FIELD))
        return None
    if person.get("someone_can_claim_you") is True:
        # A filer who can be claimed as a dependent stays on the legacy chain: the dictionary's
        # vector route reads no dependent rule for line 3 (measured: the claimed code W
        # cell files at 928.00 with the vector where the legacy chain charges the employer leg
        # as excess, 1,415.00), and a route
        # that quietly drops an excise the other route charges is not this service's to pick.
        return None
    return HSA_VECTOR_LITERALS.get(person.get(HSA_TYPE_FIELD))


def hsa_vector_governs(facts: dict) -> bool:
    """The dictionary's `/hsaLine3VectorGoverns` as the service can make it true: on a joint
    return both filers' vectors prefilled (the spouse's coverage is what IRC 223(b)(5)(A) reads);
    on a separate return the dictionary wants the spouse's vector too, which no answer here
    carries; otherwise the primary's."""
    if not isinstance(facts, dict):
        return False
    persons = facts.get("persons") or []
    filers = [i for i, p in enumerate(persons) if isinstance(p, dict) and p.get("role") in ("primary", "spouse")]
    if not filers:
        return False
    if facts.get("filing_status") == "mfs":
        # The spouse's twelve rows are sent, and the dictionary's gate then holds on a separate
        # return — but this test decides whether a TRANSFER month is asked, and a separate return's
        # funding distribution above the halved limitation is still the dictionary's own knockout
        # (measured: 5,000 transferred beside 3,000 code W → /flowHsaContributionsOverLimitKnockout,
        # the exclusion cap not computable); asking the month there would be a dead question.
        return False
    if facts.get("filing_status") == "mfj":
        return len(filers) == 2 and all(hsa_vector_months(facts, i) for i in filers)
    return all(hsa_vector_months(facts, i) for i in filers)


def hsa_transfer_month_reached(facts: dict, person_index: int) -> bool:
    """The transfer month is asked where it decides: the vector governs and this filer's
    funding-distribution total is above the base limitation for their coverage type."""
    persons = facts.get("persons") or [] if isinstance(facts, dict) else []
    person = persons[person_index] if person_index < len(persons) else None
    if not isinstance(person, dict) or not hsa_vector_governs(facts):
        return False
    return hsa_transfer_decides(facts, person_index)


def refuse_misplaced_hsa_transfer_month(facts: dict) -> None:
    """A transfer month outside the twelve, or one answered where the answers so far do
    not reach it, is refused by name rather than dropped."""
    if not isinstance(facts, dict):
        return
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict) or HSA_TRANSFER_MONTH_FIELD not in person:
            continue
        v = person[HSA_TRANSFER_MONTH_FIELD]
        if v not in HSA_TRANSFER_MONTHS:
            raise FactsSchemaError(
                f"persons[{i}].{HSA_TRANSFER_MONTH_FIELD} must be one of {', '.join(HSA_TRANSFER_MONTHS)}, got {v!r}")
        if not hsa_transfer_month_reached(facts, i):
            raise ServiceFactsError(
                f"persons[{i}].{HSA_TRANSFER_MONTH_FIELD} is answered where the answers so far do not reach "
                f"it — the month of the transfer is asked of a filer whose qualified HSA funding distribution "
                f"is above the Form 8889 line 8 base limitation for their coverage — or beside an asked coverage "
                f"vector with any transfer — with the coverage answers "
                f"carried for every filer on the return; refused rather than dropped")


def _require_hsa_transfer_month(facts: dict) -> None:
    """the reached month is answered — the backstop behind `gaps.gaps_for`."""
    if not isinstance(facts, dict):
        return
    for i, person in enumerate(facts.get("persons") or []):
        if hsa_transfer_month_reached(facts, i) and HSA_TRANSFER_MONTH_FIELD not in person:
            raise FactsSchemaError(
                f"persons[{i}].{HSA_TRANSFER_MONTH_FIELD} is asked once this filer's qualified HSA funding "
                f"distribution is above the Form 8889 line 8 base limitation, or beside an asked coverage vector "
                f"with any transfer — the month of 2025 the IRA "
                f"trustee made the transfer (prepare_return asks it as a gap)")


def refuse_misplaced_hsa_funding_amounts(facts: dict) -> None:
    """A funding-distribution amount on a Form 1099-R that does not reach it, a negative
    one, or one above the distribution it came out of, is refused by name rather than dropped
    or sent (the dictionary would knock the return out with words that cannot name the box)."""
    if not isinstance(facts, dict):
        return
    for j, item in enumerate(facts.get("r1099s") or []):
        if not isinstance(item, dict) or R1099_HFD_FIELD not in item:
            continue
        v = item[R1099_HFD_FIELD]
        if isinstance(v, bool) or not isinstance(v, int):
            raise FactsSchemaError(f"r1099s[{j}].{R1099_HFD_FIELD} is not an amount")
        if v < 0:
            raise FactsSchemaError(f"r1099s[{j}].{R1099_HFD_FIELD} is not an amount (negative); "
                                   f"Must be 0 or more")
        if not hsa_funding_r1099_reached(facts, j):
            raise ServiceFactsError(
                f"r1099s[{j}].{R1099_HFD_FIELD} is answered where the answers so far do not reach "
                f"it — a qualified HSA funding distribution is asked on an IRA Form 1099-R (the "
                f"IRA/SEP/SIMPLE box checked) of a filer who answered yes to the funding "
                f"distribution question (Form 8889 line 10); refused rather than dropped")
        gross = _cents_or_zero(item.get("gross_distribution_cents"))
        if v > gross:
            raise ServiceFactsError(
                f"r1099s[{j}].{R1099_HFD_FIELD} is above this Form 1099-R's box 1 gross "
                f"distribution — a qualified HSA funding distribution is part of the "
                f"distribution it came out of, never more; refused rather than sent")


def _require_hsa_funding_amounts(facts: dict) -> None:
    """every IRA Form 1099-R the funding yes reaches carries an amount (0 allowed) — the
    backstop behind `gaps.gaps_for`, which asks first."""
    if not isinstance(facts, dict):
        return
    for j, item in enumerate(facts.get("r1099s") or []):
        if hsa_funding_r1099_reached(facts, j) and R1099_HFD_FIELD not in item:
            raise FactsSchemaError(
                f"r1099s[{j}].{R1099_HFD_FIELD} is asked on this IRA Form 1099-R once its filer "
                f"answers yes to the qualified HSA funding distribution question — the amount "
                f"transferred into the HSA, 0 if none of this distribution (prepare_return asks "
                f"it as a gap)")


def refuse_misplaced_hsa_contribution_answers(facts: dict) -> None:
    """A Form 8889 Part I answer past its reach, a choice outside the schema's own, or an
    excess-in-wages answer on a return with no code W amount, is refused by name rather than
    dropped."""
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict):
            continue
        reached = hsa_questions_reached(facts, i)
        for field in HSA_CONTRIBUTION_FIELDS:
            if field in person and field not in reached:
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered where the answers so far do not reach it — "
                    f"Form 8889 Part I's questions are asked of a filer with a W-2 box 12 code W "
                    f"amount, each behind the one before; refused rather than dropped")
        for field in HSA_ENUM_FIELDS:
            if field in person and person[field] not in HSA_ENUM_OPTIONS[field][1]:
                raise FactsSchemaError(
                    f"persons[{i}].{field} must be one of "
                    f"{', '.join(HSA_ENUM_OPTIONS[field][1])}, got {person[field]!r}")
    if HSA_EXCESS_IN_WAGES_FIELD in facts and not hsa_excess_question_reached(facts):
        raise ServiceFactsError(
            f"{HSA_EXCESS_IN_WAGES_FIELD} is answered on a return with no W-2 box 12 code W "
            f"amount — it is the question whether an excess employer HSA contribution is already "
            f"in W-2 wages (Form 8889); refused rather than dropped")


def refuse_hsa_month_contradictions(facts: dict) -> None:
    """A month outside none / self_only / family is refused by name; so is a vector that
    contradicts the answers it was asked behind — coverage for part of the year with every month
    covered or no month covered (all_year and none are those answers), the `both` type without
    both types among the months, one type with a month of the other. Months answered where they
    are not reached are `refuse_misplaced_hsa_contribution_answers`'s."""
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict):
            continue
        for field in HSA_MONTH_FIELDS:
            if field in person and person[field] not in HSA_MONTH_LITERALS:
                raise FactsSchemaError(
                    f"persons[{i}].{field} must be one of {', '.join(HSA_MONTH_LITERALS)}, got {person[field]!r}")
        if not hsa_months_asked(facts, i) or not all(m in person for m in HSA_MONTH_FIELDS):
            continue
        values = [person[m] for m in HSA_MONTH_FIELDS]
        covered = {v for v in values if v != "none"}
        if person.get(HSA_COVERAGE_FIELD) == "all_year" and "none" in values:
            raise ServiceFactsError(
                f"persons[{i}].{HSA_COVERAGE_FIELD} is all_year while a month carries no high deductible "
                f"health plan coverage — part_of_year is that answer; refused rather than sent")
        if person.get(HSA_COVERAGE_FIELD) == "part_of_year" and "none" not in values:
            raise ServiceFactsError(
                f"persons[{i}].{HSA_COVERAGE_FIELD} is part_of_year while every month carries high "
                f"deductible health plan coverage — all_year is that answer; refused rather than sent")
        if person.get(HSA_COVERAGE_FIELD) == "part_of_year" and not covered:
            raise ServiceFactsError(
                f"persons[{i}].{HSA_COVERAGE_FIELD} is part_of_year while no month carries high "
                f"deductible health plan coverage — none is that answer; refused rather than sent")
        if person.get(HSA_TYPE_FIELD) == "both" and covered != {"self_only", "family"}:
            raise ServiceFactsError(
                f"persons[{i}].{HSA_TYPE_FIELD} is both while the months carry "
                f"{' and '.join(sorted(covered)) or 'no'} coverage — the one type is that answer; "
                f"refused rather than sent")
        if person.get(HSA_TYPE_FIELD) in ("self_only", "family") and covered - {person[HSA_TYPE_FIELD]}:
            raise ServiceFactsError(
                f"persons[{i}].{HSA_TYPE_FIELD} is {person[HSA_TYPE_FIELD]} while a month carries the "
                f"other coverage type — both is that answer; refused rather than sent")


def refuse_hsa_medicare_onset_contradictions(facts: dict) -> None:
    """An enrollment month outside the twelve is refused by name; January is Medicare all
    year (that answer, the dictionary's knockout) and is refused as the contradiction it is. An
    answer where the chain does not reach it is `refuse_misplaced_hsa_contribution_answers`'s."""
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict) or HSA_MEDICARE_ONSET_FIELD not in person:
            continue
        v = person[HSA_MEDICARE_ONSET_FIELD]
        if v not in HSA_TRANSFER_MONTHS:
            raise FactsSchemaError(
                f"persons[{i}].{HSA_MEDICARE_ONSET_FIELD} must be one of {', '.join(HSA_TRANSFER_MONTHS)}, got {v!r}")
        if v == "jan":
            raise ServiceFactsError(
                f"persons[{i}].{HSA_MEDICARE_ONSET_FIELD} is January while {HSA_MEDICARE_FIELD} is "
                f"part_of_year — enrolled from January is all_year, and that is the answer; refused "
                f"rather than sent")


def refuse_hsa_testing_period_contradictions(facts: dict) -> None:
    """A testing-period answer outside the twenty-five is refused by name; so is a month
    outside the window the transfer opened — a 2025 month before the transfer month (the period
    starts at the transfer, IRC 408(d)(9)(D)(iii)), or a month after the 12th month after it.
    An answer where the chain does not reach it is `refuse_misplaced_hsa_contribution_answers`'s."""
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict) or HSA_TESTING_FIELD not in person:
            continue
        v = person[HSA_TESTING_FIELD]
        if v not in HSA_TESTING_MONTHS:
            raise FactsSchemaError(
                f"persons[{i}].{HSA_TESTING_FIELD} must be one of {', '.join(HSA_TESTING_MONTHS)}, got {v!r}")
        transfer = person.get(HSA_TRANSFER_MONTH_FIELD)
        if v == "none" or transfer not in HSA_TRANSFER_MONTHS:
            continue
        start = HSA_TRANSFER_MONTHS.index(transfer)
        answered = HSA_TESTING_MONTHS.index(v) - 1            # 0 = January 2025 … 23 = December 2026
        if answered < start:
            raise ServiceFactsError(
                f"persons[{i}].{HSA_TESTING_FIELD} names a month before the transfer month "
                f"({transfer} 2025) — the testing period runs from the month of the transfer through "
                f"the last day of the 12th month after it, so an earlier month is outside it; answer "
                f"none, or a month in that window; refused rather than sent")
        if answered > start + 12:
            raise ServiceFactsError(
                f"persons[{i}].{HSA_TESTING_FIELD} names a month after the testing period ended — the "
                f"period runs from the transfer month ({transfer} 2025) through the last day of the 12th "
                f"month after it; answer none, or a month in that window; refused rather than sent")


def refuse_misplaced_hsa_own_answers(facts: dict) -> None:
    """The own-contribution question belongs to filer rows, the amounts to a row that said
    yes; each misplaced answer is refused by name rather than dropped."""
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict):
            continue
        reached = hsa_own_questions_reached(person)
        for field in HSA_OWN_FIELDS:
            if field not in person or field in reached:
                continue
            if person.get("role") == "dependent":
                raise ServiceFactsError(
                    f"persons[{i}].{field} is answered on a dependent row — the HSA deduction "
                    f"(Form 8889 line 13) is the filer's and, on a joint return, the spouse's; "
                    f"a dependent's answer moves nothing on this return; refused rather than "
                    f"dropped")
            raise ServiceFactsError(
                f"persons[{i}].{field} is answered where the answers so far do not reach it — "
                f"it is asked once that person answers yes to contributing to their HSA "
                f"themselves (Form 8889 line 2); refused rather than dropped")


def _require_hsa_own_answers(facts: dict) -> None:
    """the own-contribution question is answered on every filer row and the amount behind
    a yes — unanswered, the dictionary computed the deduction as zero in silence (measured)."""
    for i, person in enumerate(facts.get("persons") or []):
        for field in hsa_own_questions_reached(person):
            if field == HSA_OWN_AFTER_FIELD or field in person:
                continue                                  # the after-year-end amount is optional
            raise FactsSchemaError(
                f"persons[{i}].{field} is a question on every filer row — Form 8889 line 2, "
                f"the filer's own HSA contributions — not a default; answer it (prepare_return "
                f"asks it as a gap)")


def _require_hsa_contribution_answers(facts: dict) -> None:
    """every Form 8889 Part I question the route reaches is answered — unanswered, the
    dictionary computes the code W amount as within the limit whatever it is (measured), never
    here."""
    for i, person in enumerate(facts.get("persons") or []):
        for field in hsa_questions_reached(facts, i):
            if field not in person:
                raise FactsSchemaError(
                    f"persons[{i}].{field} is asked of a filer with HSA contributions on the "
                    f"return (Form 8889 Part I) — answer it (prepare_return asks it as a gap)")


def refuse_unsupported_box12_codes(w2s: list) -> None:
    """A box 12 amount the dictionary knocks out, or one that reaches a route this service
    has not built, is refused by name before the engine — never dropped (the return would compute
    as if the box were blank, in silence) and never computed (a knocked-out return renders
    nothing, and the dictionary's knockout words cannot name the code). An amount of 0 is the
    dictionary's own no-op (its knockout tests for a positive value) and is neither sent nor
    refused. A negative amount is not an amount."""
    for i, w2 in enumerate(w2s or []):
        if not isinstance(w2, dict):
            continue
        for field, (code, _leaf, caption, disposition, route) in W2_BOX12_BY_FIELD.items():
            v = w2.get(field)
            if v is None or isinstance(v, bool) or not isinstance(v, int):
                continue                           # absent, or the type check has already refused
            if v < 0:
                raise FactsSchemaError(f"w2s[{i}].{field} is not an amount (a negative box 12 "
                                       f"entry); Must be 0 or more")
            if v == 0:
                continue
            if disposition == "knockout":
                raise ServiceFactsError(
                    f"w2s[{i}].{field} (Form W-2 box 12, code {code.upper()} — {caption}) is a "
                    f"code the dictionary knocks a return out for; a return carrying it is not "
                    f"one this service computes — refused rather than computed without it")
            if disposition == "unbuilt":
                raise ServiceFactsError(
                    f"w2s[{i}].{field} (Form W-2 box 12, code {code.upper()} — {caption}) "
                    f"reaches {route}, a route this service has not built; refused rather than "
                    f"computed as if the box were blank")


def refuse_missing_w2_asked_answers(w2s: list) -> None:
    """every W-2 answers box 13's three checkboxes and box 14's RRTA question — an
    absent one is a question (`gaps.gaps_for` asks first), never an unchecked default."""
    for i, w2 in enumerate(w2s or []):
        if not isinstance(w2, dict):
            continue
        for field in W2_ASKED_FIELDS:
            if field not in w2:
                raise FactsSchemaError(
                    f"w2s[{i}].{field} is {_W2_ASKED_BOX[field]} on every Form W-2, not a default — "
                    f"answer it true or false (prepare_return asks it as a gap)")


refuse_missing_w2_box13_answers = refuse_missing_w2_asked_answers   # the old name, kept for callers


def _map_w2s(f: dict, w2s: list, filer_ref) -> None:
    """The one income group with a real mapper. Its presence in `_INCOME_MAPPERS` — not a list
    somewhere — is what makes `w2s` a COVERED fact group, so nothing can be published as covered
    without the code that actually maps it."""
    ids = []
    ordinals = employer_ordinals(w2s)
    for i, w2 in enumerate(w2s):
        cid = _uuid("a", i)
        ids.append(cid)
        _w2(f, cid, filer_ref(w2["person"]), w2, ordinals[w2.get("employer_ref", 0)])
    f["/formW2s"] = _collection(ids)
    f["/formW2sIsDone"] = _bool(True)


_INCOME_MAPPERS["w2s"] = _map_w2s


def _map_w2gs(f: dict, w2gs: list, filer_ref) -> None:
    """Form W-2G — box 1 reportable winnings and box 4 federal withholding.

    NOT SHAPED LIKE `_map_w2s`, and every difference is the DICTIONARY's rather than a style
    choice. The six facts this mapper relies on: the collection, two per-item Dollar writables,
    and three derived totals (`/w2gWinnings` -> Schedule 1 line 8b -> total income;
    `/w2gWithholding` -> Form 1040 line 25c, inside `/totalWithholding` on line 25d; `/hasW2Gs`).
    At an earlier pin (f8c954649) those six were the WHOLE module; a later pin grew it to
    44 (the printed form's optional field set — payer/winner detail the service's schema cannot
    carry, plus state boxes), with the six unchanged and the two structural absences below still
    absent. Mirroring `_map_w2s` by reflex would send facts that do not exist:

      * THERE IS NO `/formW2GsIsDone`. `_map_w2s` writes `/formW2sIsDone` because formW2s.xml has
        one; this collection has no section-complete marker at all.

      * THERE IS NO `/formW2Gs/*/filer`. The 1040 consumes only the two aggregate totals, and both
        are `CollectionSum`s over every item regardless of whose form it is — so which filer holds
        a W-2G changes nothing on the federal return. `person` is still VALIDATED, through
        `filer_ref` below, and an index naming nobody is refused exactly as it is on a W-2: a
        caller pointing at a filer who is not there has made a mistake whether or not we would have
        used the answer. IT THEN MAPS NOWHERE. That is deliberate, and it is the whole reason this
        line looks like a no-op. (Coverage is `single`-only today, so there is one filer to name;
        the validation is what keeps the refusal honest when that changes.)

      * THE COLLECTION IS WRITTEN ONLY WHEN THERE ARE ITEMS, where `_map_w2s` writes `/formW2s`
        unconditionally. Both totals are complete-safe — `Switch` on `IsComplete(/formW2Gs)`, the
        `/alaskaPfdIncome` shape — so an EMPTY collection resolves to the same zeros an absent one
        does. MEASURED, not assumed: resolving `wages-single-mid` with and without an empty
        `/formW2Gs` differs in exactly one resolved fact, `/formW2Gs` itself, and no served number
        moves. Writing it anyway would therefore change the engine fact set of every W-2G-less
        return to buy nothing, and the syndoc profile builder already made this call for the same
        reason ("emitted only when the profile carries W-2Gs, so prior profiles stay
        byte-identical"). The three committed contract goldens stay byte-identical because of this.

      * BOX 4 ABSENT IS SENT AS 0, the W-2 `withholding_cents` precedent (decided
        2026-08-11: withholding stays schema-optional, and the component that has the document is
        the one that asks). Blank box 4 is an ordinary state of a real W-2G — withholding applies
        to some wager types and amounts and not others. The absence is not silent: `gaps.py`
        STATES it in the response, the same way it states an absent W-2 box 2.

    `winnings_cents` is read directly rather than with `.get(..., 0)` — it is schema-required and
    `_refuse_missing_or_mistyped` has already enforced it, so if that requirement is ever relaxed
    this raises loudly instead of quietly resuming a $0.00 default (the work-item-0b lesson).
    """
    if not w2gs:
        return
    ids = []
    for i, g in enumerate(w2gs):
        cid = _uuid("b", i)
        ids.append(cid)
        filer_ref(g["person"])          # validated; see the docstring — it maps nowhere
        b = f"/formW2Gs/#{cid}"
        f[f"{b}/writableReportableWinnings"] = _dollar(g["winnings_cents"])
        f[f"{b}/writableFederalWithholding"] = _dollar(g.get("federal_withholding_cents", 0))
    f["/formW2Gs"] = _collection(ids)


_INCOME_MAPPERS["w2gs"] = _map_w2gs


# the dictionary's own option set for `/socialSecurityReports/*/writableFormType`.
SSA_FORM_TYPES = {"ssa_1099": "SSA-1099", "rrb_1099": "RRB-1099"}
SSA_EMISSION = {
    "ssa_1099": ("ssaNetBenefits", "writableSsaFederalTaxWithheld"),
    "rrb_1099": ("rrbNetBenefits", "writableRrbFederalTaxWithheld"),
}


def _map_ssa1099s(f: dict, items: list, filer_ref) -> None:
    """Form SSA-1099 / RRB-1099 — box 5 net benefits and the withholding box.

    Shaped by the dictionary's socialSecurity.xml, measured at the pin: each item carries its
    filer, the form type (`/socialSecurityIncomeFormTypeOptions`: SSA-1099 / RRB-1099) and the
    amount on the writable that type keys — `ssaNetBenefits` or `rrbNetBenefits`, read by the
    item's `netBenefits` Switch — with withholding on the matching pair. `/socialSecurityBenefits`
    (line 6a) is the CollectionSum of `netBenefits`; the taxable amount (line 6b) is the
    dictionary's worksheet; `/form1099Withholding` carries the withholding into line 25d.

      * THE SCAFFOLD ALREADY WRITES `/socialSecurityReports` EMPTY on every return (the interest
        precedent) and `/socialSecurityReportsIsDone` true; this mapper overwrites the collection
        when there are items. An absent collection would leave the aggregate unresolved.

      * `hasSeenLastAvailableScreen` is the item's screen marker — plumbing (ENGINE_PLUMBING),
        emitted because the item's own `isComplete` reads it.

      * THE WITHHOLDING BOX ABSENT IS SENT AS 0, the W-2 and W-2G posture: blank is an ordinary
        state of the box, and `gaps.py` STATES the absence in the response.

      * The line 6c lump-sum election is answered no in the scaffold and published as an
        assumption; a yes is the dictionary's own `/socialSecurityLumpSumIntakeIncomplete`
        knockout (the earlier-years intake is not carried).

    `net_benefits_cents` and `form_type` are read directly — both schema-required and enforced by
    `_refuse_missing_or_mistyped`, so a relaxed requirement raises here rather than resuming a
    default."""
    if not items:
        return
    ids = []
    for i, item in enumerate(items):
        cid = _uuid("c", i)
        ids.append(cid)
        b = f"/socialSecurityReports/#{cid}"
        form = item["form_type"]
        if form not in SSA_EMISSION:
            raise FactsSchemaError(
                f"ssa1099s[{i}].form_type must be one of {', '.join(sorted(SSA_EMISSION))}, "
                f"got {form!r}")
        amount, withheld = SSA_EMISSION[form]
        f[f"{b}/filer"] = _collection_item(filer_ref(item["person"]))
        f[f"{b}/writableFormType"] = _enum("/socialSecurityIncomeFormTypeOptions",
                                           SSA_FORM_TYPES[form])
        f[f"{b}/hasSeenLastAvailableScreen"] = _bool(True)
        f[f"{b}/{amount}"] = _dollar(item["net_benefits_cents"])
        f[f"{b}/{withheld}"] = _dollar(item.get("federal_withholding_cents", 0))
    f["/socialSecurityReports"] = _collection(ids)


_INCOME_MAPPERS["ssa1099s"] = _map_ssa1099s


def _map_ssa_lump_sum_years(f: dict, items: list, filer_ref) -> None:
    """the earlier years a 2025 lump-sum payment is attributable to — the collection Pub. 915
    Worksheet 2 (1994 and later) or Worksheet 3 (1993 and earlier) refigures one row at a time.

      * RETURN-LEVEL, no `filer`: the dictionary's items carry none. A lump sum belongs to the
        benefit statement, and the election is the return's (Form 1040 line 6c).
      * ALL NINE ARE REQUIRED (`REQUIRED_ITEM_FIELDS`): the dictionary's
        `earlierYearIntakeAnswered` is an All over the nine with no gate order, and a row missing
        one leaves `/socialSecurityLumpSumEarlierYearsAnswered` false — the election is simply not
        made and the return stays on the regular method, which is why it must never be defaulted.
      * The year is an Int, not a Dollar, and the dictionary bounds it 1984..2024; the range is
        refused by name in `refuse_misplaced_lump_sum_answers` before this runs.
      * The rows are sent only where they are reached; an empty collection is never written, so a
        return that does not elect is untouched.
    """
    if not items:
        return
    ids = []
    for i, item in enumerate(items):
        cid = _uuid("e", i)
        ids.append(cid)
        b = f"/socialSecurityLumpSumEarlierYears/#{cid}"
        for field, leaf in LUMP_SUM_EMISSION.items():
            value = item[field]
            if field == LUMP_SUM_YEAR_FIELD:
                f[f"{b}/{leaf}"] = _int_wrap(value)
            elif field in LUMP_SUM_BOOLEAN_FIELDS:
                f[f"{b}/{leaf}"] = _bool(bool(value))
            else:
                f[f"{b}/{leaf}"] = _dollar(value)
    f["/socialSecurityLumpSumEarlierYears"] = _collection(ids)


_INCOME_MAPPERS[LUMP_SUM_GROUP] = _map_ssa_lump_sum_years


def _map_g1099s(f: dict, items: list, filer_ref) -> None:
    """Form 1099-G unemployment compensation — box 1, box 4 and the same-year repayment.

    Shaped by the dictionary's unemployment.xml, measured at the pin: the collection holds
    UNEMPLOYMENT COMPENSATION ONLY (box 2, the state refund, is a root intake — see `_scaffold`).
    `amount` (box 1) less the same-year repayment is `netUnemploymentComp`, summed into
    `/unemploymentCompensation` (Schedule 1 line 7), then `/schedule1Line10AdditionalIncome`
    (Form 1040 line 8) and `/totalIncome`; `writableFederalTaxWithheld` (box 4) reaches line 25d.

      * THE SCAFFOLD ALREADY WRITES `/form1099Gs` EMPTY on every return; this mapper overwrites
        the collection when there are items.

      * THE PAYER TIN IS SYNTHESIZED ON EVERY ITEM. The item's own `isComplete` wants a payer
        TIN whenever withholding is non-zero, and an item left incomplete still moves line 25d
        with no knockout — a return would be served complete over an incomplete item. Always
        sent, no branch. Prefix 00 is unassigned (the W-2 employer convention); the serial space
        starts at 9,000,000 so it cannot collide with a W-2 employer ordinal.

      * `repaid` is the printed line 7 checkbox: checked exactly when the same-year repayment is
        non-zero. The earlier-year writable is answered zero and PUBLISHED (ASSUMED_ABOUT_TAXPAYER).

      * `writableState` is attested `sameState`, the W-2 posture, and published; the different-
        state knockout can never fire from this emission.

      * `writableIsCommunityIncome` is not sent: unanswered reads false (the dictionary is
        IsComplete-first), and the Form 8958 return it would matter on is refused upstream.

      * THE WITHHOLDING AND REPAYMENT BOXES ABSENT ARE SENT AS 0, the W-2G posture: blank is an
        ordinary state of the box, and `gaps.py` STATES each absence in the response.
    """
    if not items:
        return
    ids = []
    for i, item in enumerate(items):
        cid = _uuid("3", i)
        ids.append(cid)
        b = f"/form1099Gs/#{cid}"
        repaid = item.get("repaid_cents", 0)
        f[f"{b}/filer"] = _collection_item(filer_ref(item["person"]))
        f[f"{b}/has1099"] = _bool(True)
        f[f"{b}/hasSeenLastAvailableScreen"] = _bool(True)
        f[f"{b}/payer"] = _str("Synthetic Payer")
        f[f"{b}/payer/tin"] = _ein("00", f"{9000000 + i:07d}")
        f[f"{b}/amount"] = _dollar(item["unemployment_compensation_cents"])
        f[f"{b}/writableFederalTaxWithheld"] = _dollar(item.get("federal_withholding_cents", 0))
        f[f"{b}/repaid"] = _bool(repaid > 0)
        f[f"{b}/writableAmountPaidBackForBenefitsInTaxYear"] = _dollar(repaid)
        f[f"{b}/writableAmountPaidBackForBenefitsBeforeTaxYear"] = _dollar(0)
        f[f"{b}/writableState"] = _enum("/incomeFormStateOptions", "sameState")
    f["/form1099Gs"] = _collection(ids)


_INCOME_MAPPERS["g1099s"] = _map_g1099s


def _map_misc1099s(f: dict, items: list, filer_ref) -> None:
    """Form 1099-MISC box 2 royalties, box 3 other income, box 4 and the Alaska PFD flag
   .

    Shaped by the dictionary's form1099Misc.xml, measured at the pin: the ITEM's own completeness
    reads box 3, the screen marker and the Alaska classification only — box 2 has no
    per-item engine writable at all (the dictionary models royalties as ONE return-level activity,
    `/writableRoyaltyIncome`, never a per-form collection); `royalty_income_total` sums it and
    `_map_royalties` emits the root fact separately. `writableOtherIncome` routes by the flag —
    `/form1099MiscOtherIncome` or `/alaskaPfdIncome` — both into `/otherIncome` (Schedule 1
    line 8z), then `/schedule1Line10AdditionalIncome` (Form 1040 line 8) and `/totalIncome`;
    `writableFederalWithholding` reaches line 25d.

      * THE SCAFFOLD ALREADY WRITES `/form1099Miscs` EMPTY on every return; this mapper overwrites
        the collection when there are items.

      * `writableIsAlaskaPfd` IS SENT ON EVERY ITEM, satisfying the register's own "answered for
        item completeness" reading (row 191) without asking a question nobody can answer: the
        caller's answer when box 3 is above 0 (`misc_pfd_question_reached`); AUTO false otherwise
        — a $0 box (the ordinary state of a royalty-only 1099-MISC) has nothing to
        classify, and unanswered reads TRUE at the pin only when box 3 truly carries an amount.
        The answer is reconciled with the root pair in `refuse_misplaced_alaska_pfd_answers`.

      * No payer TIN is wanted (the item's completeness reads box 3 and the screen marker only,
        withholding or not — unlike the 1099-G); the payer name is a synthetic placeholder.

      * `writableState` sameState is attested and published, the W-2 posture; no state knockout
        exists in the module at the pin. `writableIsCommunityIncome` is not sent (Form 8958
        returns are refused upstream).

      * THE WITHHOLDING BOX ABSENT IS SENT AS 0, the W-2G posture, stated by `gaps.py`.
    """
    if not items:
        return
    ids = []
    for i, item in enumerate(items):
        cid = _uuid("5", i)
        ids.append(cid)
        b = f"/form1099Miscs/#{cid}"
        f[f"{b}/filer"] = _collection_item(filer_ref(item["person"]))
        f[f"{b}/hasSeenLastAvailableScreen"] = _bool(True)
        f[f"{b}/payer"] = _str("Synthetic Payer")
        f[f"{b}/writableOtherIncome"] = _dollar(item["other_income_cents"])
        f[f"{b}/writableFederalWithholding"] = _dollar(item.get("federal_withholding_cents", 0))
        is_pfd = item.get(MISC_PFD_FIELD)
        if is_pfd is None:
            is_pfd = False                                    # box 3 is 0 — nothing to classify
        f[f"{b}/writableIsAlaskaPfd"] = _bool(bool(is_pfd))
        f[f"{b}/writableState"] = _enum("/incomeFormStateOptions", "sameState")
    f["/form1099Miscs"] = _collection(ids)


_INCOME_MAPPERS["misc1099s"] = _map_misc1099s


def _map_royalties(f: dict, facts: dict) -> None:
    """the return's one royalty activity (scheduleE.xml — a root fact, not a collection).

    Every misc1099s[].royalties_cents (box 2) is summed into `/writableRoyaltyIncome`; nothing is
    emitted when the sum is 0 (`/writableHasRoyaltyIncome` unanswered is complete-safe false at
    the pin, exactly the K-1-income-flag posture). The ordinary expenses and the oil/gas
    classification are root answers no 1099-MISC box carries — `refuse_misplaced_royalty_answers`
    and the map_to_engine backstop guarantee `ROYALTY_EXPENSES_FIELD` is present whenever this
    runs above 0."""
    total = royalty_income_total(facts)
    if total <= 0:
        return
    f["/writableHasRoyaltyIncome"] = _bool(True)
    f["/writableRoyaltyIncome"] = _dollar(total)
    if ROYALTY_EXPENSES_FIELD in facts:
        f["/writableRoyaltyExpenses"] = _dollar(_cents_or_zero(facts[ROYALTY_EXPENSES_FIELD]))
    if ROYALTY_OIL_GAS_FIELD in facts:
        f["/writableRoyaltyIsOilGasGeothermal"] = _bool(bool(facts[ROYALTY_OIL_GAS_FIELD]))


def _map_hsa_distributions(f: dict, items: list, filer_ref) -> None:
    """The Form 1099-SA items — the collection half of `_hsa_section`, registered like
    every other stream so the fact group is known, refused when malformed, and priced."""
    if not items:
        return
    ids = []
    for i, item in enumerate(items):
        cid = _uuid("6", i)
        ids.append(cid)
        b = f"/hsaDistributions/#{cid}"
        f[f"{b}/filer"] = _collection_item(filer_ref(item["person"]))
        f[f"{b}/writableGrossDistribution"] = _dollar(item["gross_distribution_cents"])
        f[f"{b}/writableQualifiedMedExpenses"] = _dollar(item["qualified_medical_expenses_cents"])
        code = item[HSA_CODE_FIELD]
        if code not in HSA_CODES:
            raise FactsSchemaError(
                f"{HSA_GROUP}[{i}].{HSA_CODE_FIELD} must be one of {', '.join(HSA_CODES)}, got {code!r}")
        f[f"{b}/hsaDistributionCode"] = _enum("/hsaDistributionCodeOptions", HSA_CODES[code])
        f[f"{b}/writableDistributionsRolloverBool"] = _bool(False)
        f[f"{b}/hasWithdrawnExcessContributions"] = _bool(False)
        f[f"{b}/writableTrusteeName"] = _str("Synthetic Trustee")
        f[f"{b}/hasSeenLastAvailableScreen"] = _bool(True)
    f["/hsaDistributions"] = _collection(ids)


_INCOME_MAPPERS[HSA_GROUP] = _map_hsa_distributions


def _hsa_section(f: dict, facts: dict, filer_by_index: dict, tax_year: int) -> None:
    """Form 1099-SA HSA distributions, Form 8889 Part II — measured to closure at the pin.

    A distribution alone moves no line: the dictionary's HSA intro section wants its own
    questions answered before the collection route reads. The MINIMAL closing set for a filer
    with distributions and no contributions (measured, no Form 8889 Part I coverage grid):

      * root: `/someFilerHadNonW2HsaActivity` (true with any item, else false — published
        either way, the contribution half being assumed), the MSA-type question, the
        excess-contribution pair and the testing-period pair, all answered no and PUBLISHED;
      * per filer, BOTH filers on a joint return (measured: the intro section's second Any
        wants the spouse's twin even when only the primary has a form): the activity twin
        (`/writable{Primary,Secondary}FilerHadNonW2HsaActivity`, true for a filer with a form)
        and the contributions answer (no, published); for a filer with a form the
        funding-distribution answer (no, published) and, where reached, the 20%-tax exception
        PAIR (`hsa_exception_questions_reached`: taxable above zero, code 1 throughout, under
        66 at the close — a filer 66 or older has the exception derived by the dictionary);
      * per item: filer, box 1, the line 15 expenses, the box 3 code as the dictionary's own
        option (codes 3-6 are its own knockouts, served with words; code 2 is refused
        upstream), the rollover and withdrawn-excess answers (no, published), a synthetic
        trustee name and the screen marker (plumbing).

    Without items nothing but the root activity answer is sent — the scaffold's empty
    collection and Done marker stand, and the wages-only goldens do not move.

    the CONTRIBUTION half: a filer row with W-2 box 12 code W above 0 opens the same
    section (the root set above is sent for it too — the Placeholder section otherwise completes
    the return as if within the limit, measured), and its Form 8889 Part I answers are sent
    exactly as far as `hsa_questions_reached` reaches them: the four choices as the
    dictionary's own options, the funding-distribution answer from the row (a 1099-SA-only
    filer keeps the published no), the separate return's line 6 check, the married filer's
    change-of-status answer as the dictionary's two-way option and its follow-up; the return's
    excess-in-wages answer when given.

    LINE 2: every filer row answers whether they contributed themselves; a yes opens the
    section the same way (measured: 2,000 is the line 13 deduction, 928.00 → 728.00) and sends
    the amount and the after-year-end amount (0 when absent — an unsent one fires the
    dictionary's dependent knockout, measured); a no sends both as 0, so a claimed code W
    filer who answers files with the dictionary's excise instead of that knockout (measured:
    1,415.00); the activity twins are the rows' answers."""
    items = facts.get(HSA_GROUP) or []
    persons = facts.get("persons") or []
    w_filers = {i for i, p in enumerate(persons)
                if isinstance(p, dict) and hsa_w2_contributions(facts, i) > 0}
    own_filers = {i for i, p in enumerate(persons) if hsa_own_contributions(p)}
    f["/someFilerHadNonW2HsaActivity"] = _bool(bool(items) or bool(own_filers))
    if not items and not w_filers and not own_filers and not hsa_prior_excess_carried(facts):
        return                                   # a carry-in alone opens the section too
    f["/hasHsaMedicalSavingsAccountType"] = _bool(False)
    # the yes/no is the caller's now — a positive carry-in on any filer row; a 0 or an absent
    # amount is the no (the dictionary refuses a yes with no positive amount), stated when absent.
    f["/writableHasHsaExcessContributionsPreviousYear"] = _bool(hsa_prior_excess_carried(facts))
    f["/writableHasHsaWithdrawnExcessContributionsYesNo"] = _bool(False)
    f["/someFilersMadeTestingPeriodContribution"] = _bool(False)
    f["/someFilersHaveTestingPeriodAdditionalIncome"] = _bool(False)
    if HSA_EXCESS_IN_WAGES_FIELD in facts:
        f["/writableHsaEmployerExcessAlreadyInW2Income"] = _bool(facts[HSA_EXCESS_IN_WAGES_FIELD])
    for i, person in enumerate(persons):
        if not isinstance(person, dict) or person.get("role") not in ("primary", "spouse"):
            continue
        role = "Primary" if person.get("role") == "primary" else "Secondary"
        fid = filer_by_index[i]
        has = any(isinstance(it, dict) and it.get("person") == i for it in items)
        f[f"/writable{role}FilerHadNonW2HsaActivity"] = _bool(has or i in own_filers)
        f[f"/filers/#{fid}/writable{role}FilerHasMadeContributionsToHsa"] = _bool(i in own_filers)
        # line 2 on EVERY filer row of the active section — the row's amounts on a yes,
        # 0.00 and 0.00 on a no. A no with the writables unsent leaves both members of the
        # dictionary's dependent knockout firing on a claimed code W filer (measured, W 3,000:
        # unsent → knocked out; sent as 0 → 1,415.00, the excise the dictionary computes).
        own = i in own_filers
        f[f"/filers/#{fid}/writableHsaNonemployerContributionsTaxYear"] = _dollar(
            person[HSA_OWN_AMOUNT_FIELD] if own else 0)
        f[f"/filers/#{fid}/writableHsaNonemployerContributionsTaxYearPlusOne"] = _dollar(
            _cents_or_zero(person.get(HSA_OWN_AFTER_FIELD)) if own else 0)
        if _cents_or_zero(person.get(HSA_PRIOR_EXCESS_FIELD)) > 0:
            f[f"/filers/#{fid}/writableHsaPriorYearExcessContributionsForm5329Line48"] = _dollar(person[HSA_PRIOR_EXCESS_FIELD])
        if HSA_DEC31_FIELD in person:
            # Form 5329 line 49's cap, the smaller of the excess and this value: sent verbatim (a 0
            # is the filer's own statement); absent sends nothing and is stated (`gaps._ABSENT_MEANS`).
            f[f"/filers/#{fid}/writableHsaDecember31AccountValue"] = _dollar(person[HSA_DEC31_FIELD])
        if i in w_filers or i in own_filers or hsa_spouse_coverage_opener(facts, i):
            for field in hsa_questions_reached(facts, i):
                if field not in person:
                    continue
                if field in HSA_ENUM_OPTIONS:
                    options, literals = HSA_ENUM_OPTIONS[field]
                    leaf = {HSA_MEDICARE_FIELD: "enrolledInMedicare", HSA_COVERAGE_FIELD: "hsaHdhpCoverageStatus",
                            HSA_TYPE_FIELD: "typeOfHdhp", HSA_OTHER_COVERAGE_FIELD: "hadOtherCoverageIneligibleForHSA"}[field]
                    f[f"/filers/#{fid}/{leaf}"] = _enum(options, literals[person[field]])
                elif field == HSA_FUNDING_FIELD:
                    f[f"/filers/#{fid}/hasMadeQualifiedHsaFundingDistribution"] = _bool(person[field])
                elif field == HSA_PRIOR_HFD_FIELD:
                    f[f"/{role.lower()}FilerHasPriorLifetimeHfdElection"] = _bool(person[field])
                elif field == HSA_TESTING_FIELD:
                    f[f"/filers/#{fid}/writableHsaTestingPeriodFirstIneligibleMonth"] = _enum(
                        "/hsaTestingPeriodFirstIneligibleMonthOptions", person[field])
                elif field == HSA_SPOUSE_CONTRIBUTED_FIELD:
                    f[f"/filers/#{fid}/writableMfsLine6Check"] = _bool(person[field])
                elif field == HSA_MARITAL_CHANGED_FIELD:
                    f[f"/filers/#{fid}/writableChangeInMaritalStatusDuringTaxYear"] = _enum(
                        "/changeInMaritalStatusDuringTaxYearOptions",
                        "wasMarriedOrDivorcedThisYear" if person[field] else "wasNotMarriedNorDivorcedThisYear")
                elif field == HSA_MARITAL_AFFECTS_FIELD:
                    f[f"/filers/#{fid}/writableMaritalChangeAffectContributionLimitBool"] = _bool(person[field])
            # the twelve-month coverage vector, PREFILLED from the all-year answers (the
            # register's own prefill, row 9): twelve months of the carried type and twelve
            # Medicare months of no, or from the onset month on — DERIVED_FROM_INPUT. It governs line
            # 3 only when every filer the married rule reads has it (`hsa_vector_governs`), and
            # then the transfer month, asked where the transfer is above the base limitation,
            # lets the dictionary clamp the exclusion (measured: 5,000 self-only → 700 on 4b).
            cov = hsa_vector_months(facts, i)                                 # asked, or prefilled
            if cov:
                for (m, literal), enrolled in zip(enumerate(cov, 1), hsa_medicare_months(facts, i)):
                    f[f"/filers/#{fid}/writableHsaCoverageTypeMonth{m:02d}"] = _enum("/hsaMonthlyCoverageTypeOptions", literal)
                    f[f"/filers/#{fid}/writableHsaEnrolledInMedicareMonth{m:02d}"] = _bool(enrolled)
                if hsa_transfer_month_reached(facts, i):
                    f[f"/filers/#{fid}/writableHsaFundingDistributionTransferMonth"] = _enum(
                        "/hsaFundingDistributionTransferMonthOptions", person[HSA_TRANSFER_MONTH_FIELD])
        if hsa_funding_answer_assumed(facts, i):
            # the stated no (`gaps._ABSENT_MEANS`) — sent whichever branch the row took (
            # the spouse opener puts a row with a form in the branch above too)
            f[f"/filers/#{fid}/hasMadeQualifiedHsaFundingDistribution"] = _bool(False)
        if hsa_exception_questions_reached(facts, i, tax_year):
            f[f"/filers/#{fid}/writableHsaCollectionExceptionAmount"] = _dollar(person[HSA_EXCEPTION_AMOUNT_FIELD])
            reason = person[HSA_EXCEPTION_REASON_FIELD]
            if reason not in HSA_EXCEPTION_REASONS:
                raise FactsSchemaError(
                    f"persons[{i}].{HSA_EXCEPTION_REASON_FIELD} must be one of "
                    f"{', '.join(HSA_EXCEPTION_REASONS)}, got {reason!r}")
            f[f"/filers/#{fid}/writableHsaCollectionExceptionReason"] = _enum(
                "/hsaCollectionExceptionReasonOptions", HSA_EXCEPTION_REASONS[reason])


def _map_int1099s(f: dict, items: list, filer_ref) -> None:
    """Form 1099-INT — boxes 1, 3, 8 and 4.

    Shaped by `interest.xml` at the pin, not by reflex from the other mappers:

      * `has1099` is TRUE BY CONSTRUCTION: this fact group is, by its own name, the Form
        1099-INT a payer issued. The dictionary's other branch (`no1099Amount`, interest nobody
        reported on a form) is not this group's to claim.
      * ALL FOUR AMOUNTS ARE OPTIONAL, because a real 1099-INT can carry any subset — a
        savings-bond-only form has box 3 and an empty box 1 (the form's own instruction: box 1
        is "taxable interest not included in box 3"). An absent amount is sent as zero and
        STATED (`gaps._ABSENT_MEANS`), the directive-28 posture.
      * `filer` EXISTS here (unlike the W-2G) and is sent: the federal totals sum every item
        regardless, but the fact is declared and whose form it is stays true on the wire.
      * `payer` is SYNTHESIZED — payer identity may not cross the boundary — and
        `factaFilingRequired` is asserted false and PUBLISHED as an assumption: the schema has
        no field for that checkbox, and silence about an asserted answer is what the
        assumptions discipline exists to prevent.
      * Box 3 is sent to `writableInterestOnGovernmentBonds`, which the derived side treats as
        zero when absent — measured at the pin — so absence stays absence for the ENGINE while
        the STATEMENT above covers the caller.
    """
    if not items:
        return
    ids = []
    for i, item in enumerate(items):
        cid = _uuid("7", i)
        ids.append(cid)
        b = f"/interestReports/#{cid}"
        f[f"{b}/filer"] = _collection_item(filer_ref(item["person"]))
        f[f"{b}/has1099"] = _bool(True)
        f[f"{b}/factaFilingRequired"] = _bool(False)
        f[f"{b}/payer"] = _str("Synthetic Payer")
        f[f"{b}/writable1099Amount"] = _dollar(item.get("interest_cents", 0))
        f[f"{b}/writableInterestOnGovernmentBonds"] = _dollar(
            item.get("government_interest_cents", 0))
        f[f"{b}/writableTaxExemptInterest"] = _dollar(item.get("tax_exempt_interest_cents", 0))
        f[f"{b}/writableTaxWithheld"] = _dollar(item.get("federal_withholding_cents", 0))
        for field, leaf in INT_EXTRA_EMISSION.items():                  # boxes 2, 9-13
            if field in item:
                f[f"{b}/{leaf}"] = _dollar(item[field])
    f["/interestReports"] = _collection(ids)
    f["/interestReportsIsDone"] = _bool(True)


_INCOME_MAPPERS["int1099s"] = _map_int1099s


def _map_oid1099s(f: dict, items: list, filer_ref) -> None:
    """Form 1099-OID — boxes 1, 2, 3, 4, 5, 6, 8, 10 and 11 (`interest.xml`).

    Shaped by the module and by measurement (`tmp/probe_oid.py`, wages-single-mid at the pin):

      * EVERY MONEY BOX IS SENT, a blank one as 0 and STATED (`gaps._ABSENT_MEANS`). For boxes 2
        and 11 that is not a nicety: the engine's item is complete only when both are answered,
        and an incomplete item is left out of the return WHOLE and in silence.
      * THE TAX-EXEMPT ANSWER is the person's where the form does not settle it
        (`oid_tax_exempt_question_reached`). With no amount in box 2 and none in box 11 there is
        nothing to classify, and a no is stated so the item completes; with an amount in box 11
        the form's instructions settle it and nothing is sent.
      * `filer` is sent; `payer` is SYNTHESIZED (payer identity may not cross the boundary).
        There is no `has1099` and no section marker on this collection — every difference from
        `_map_int1099s` is the dictionary's.
      * A checked FATCA box never reaches here (`refuse_malformed_oid1099s`); unchecked, nothing
        is sent — the dictionary reads it nowhere at the pin.
    """
    if not items:
        return
    ids = []
    for i, item in enumerate(items):
        cid = _uuid("d", i)
        ids.append(cid)
        b = f"/originalIssueDiscountReports/#{cid}"
        f[f"{b}/filer"] = _collection_item(filer_ref(item["person"]))
        f[f"{b}/payer"] = _str("Synthetic Payer")
        for field, leaf in OID_EMISSION.items():
            f[f"{b}/{leaf}"] = _dollar(item.get(field, 0))
        if _cents_or_zero(item.get("tax_exempt_oid_cents")) == 0:
            f[f"{b}/writableBox2IsTaxExempt"] = _bool(bool(item.get(OID_TAX_EXEMPT_FIELD, False)))
    f["/originalIssueDiscountReports"] = _collection(ids)


_INCOME_MAPPERS["oid1099s"] = _map_oid1099s


def _map_b1099s(f: dict, items: list, filer_ref) -> None:
    """Form 1099-B — one `/form8949Transactions` item per form (`scheduleD.xml`).

    Shaped by measurement (`tmp/probe-1099b`, wages-single-mid on the pinned engine):
      * Boxes 1d and 1e always (both are required: the engine leaves a row with either blank
        incomplete). A short-term gain of 4,000.00 moves line 9 and is taxed at the ordinary
        rate; long-term, at the capital gain rate (600.00 against 960.00 at 24%); a 9,000.00
        loss is limited to 3,000.00.
      * Box 1g is column (g), POSITIVE, with code W in column (f): 10,000.00 - 12,000.00 +
        1,500.00 nets -500.00.
      * Box 2 is sent as read; with both dates the engine's own holding period decides. It is
        asked when a date is missing (`b1099_term_question_reached`).
      * `person` is validated and then maps nowhere: the collection has no filer (the rental
        precedent). Nothing identifying crosses, and box 1a (free text) is not sent.
    """
    if not items:
        return
    ids = []
    for i, item in enumerate(items):
        filer_ref(item["person"])
        cid = f"b8{i:06x}-0000-4000-8000-{i:012x}"
        ids.append(cid)
        b = f"/form8949Transactions/#{cid}"
        f[f"{b}/writableProceeds"] = _dollar(item["proceeds_cents"])
        f[f"{b}/writableCostBasis"] = _dollar(item["cost_basis_cents"])
        for field in ("date_acquired", "date_sold"):
            if field in item:
                f[f"{b}/{B1099_EMISSION[field]}"] = _day(item[field])
        if B1099_TERM_FIELD in item:
            f[f"{b}/writableIsLongTerm"] = _bool(item[B1099_TERM_FIELD] == "long")
        if _cents_or_zero(item.get("wash_sale_loss_disallowed_cents")) > 0:
            f[f"{b}/writableAdjustmentAmount"] = _dollar(item["wash_sale_loss_disallowed_cents"])
            f[f"{b}/writableAdjustmentCodes"] = _str("W")
        if "basis_reported_to_irs" in item:
            f[f"{b}/writableBasisReportedToIrs"] = _bool(item["basis_reported_to_irs"])
    f["/form8949Transactions"] = _collection(ids)


_INCOME_MAPPERS["b1099s"] = _map_b1099s


def _map_div1099s(f: dict, items: list, filer_ref) -> None:
    """Form 1099-DIV — boxes 1a, 1b, 2a, 2b, 4, 5 and 12.

    Shaped by the dividends module at the pin:

      * ALL SEVEN AMOUNTS ARE OPTIONAL — a real 1099-DIV carries any subset — and every absence
        is sent as zero and STATED (`gaps._ABSENT_MEANS`).
      * THREE BOXES ARE SLICES OF OTHERS, by the form's own instructions, and an impossible
        slice is refused before the engine sees it: box 1b and box 5 are each inside box 1a,
        box 2b inside box 2a. The engine does not stop an impossible slice any more than it
        stops a negative (the W-2G lesson); it would compute a wrong preferential-rate split.
      * NO SECTION MARKER and NO `has1099` here: the dividends module declares neither — the
        `_map_w2gs` rule again, every difference is the dictionary's.
      * `payer` is synthesized; there is no FATCA writable on this module.
    """
    if not items:
        return
    ids = []
    for i, item in enumerate(items):
        cid = _uuid("8", i)
        ids.append(cid)
        b = f"/dividendReports/#{cid}"
        f[f"{b}/filer"] = _collection_item(filer_ref(item["person"]))
        f[f"{b}/payer"] = _str("Synthetic Payer")
        f[f"{b}/writableOrdinaryDividends"] = _dollar(item.get("ordinary_dividends_cents", 0))
        f[f"{b}/writableQualifiedDividends"] = _dollar(item.get("qualified_dividends_cents", 0))
        f[f"{b}/writableCapitalGainDistributions"] = _dollar(
            item.get("capital_gain_distributions_cents", 0))
        f[f"{b}/writableUnrecapturedSection1250Gain"] = _dollar(
            item.get("unrecaptured_1250_gain_cents", 0))
        f[f"{b}/writableFederalWithholding"] = _dollar(item.get("federal_withholding_cents", 0))
        f[f"{b}/writableSection199ADividends"] = _dollar(
            item.get("section_199a_dividends_cents", 0))
        f[f"{b}/writableExemptInterestDividends"] = _dollar(
            item.get("exempt_interest_dividends_cents", 0))
    f["/dividendReports"] = _collection(ids)


_INCOME_MAPPERS["div1099s"] = _map_div1099s


def _map_r1099s(f: dict, items: list, filer_ref) -> None:
    """Form 1099-R — boxes 1, 2a, 2b, 4, 7 and the IRA/SEP/SIMPLE checkbox.

    Shaped by the 1099-R modules at the pin, and the sharpest edges are what is NOT sent:

      * AN ABSENT BOX 2a SENDS NOTHING — measured: the dictionary KNOCKS the return OUT either
        way (2b checked: `knockoutTaxableAmountNotDetermined`; 2b unchecked and 2a blank: the
        blank-2a knockout) — because determining a taxable amount the payer did not state is
        advice, and the service computes and cites, never advises. The knockout is the engine's
        own answer, served as `knocked_out`.
      * THE DAY-ARMED CHAINS STAY UNARMED. The Form 4972 lump-sum election and the
        community-property allocation are what make lines 9/11/25d day-sensitive through this
        collection (`test_day_sensitivity.py`), and every writable that arms them is OUTSIDE
        this mapper's emission — proven by the resolve-time day-invariance test, which is the
        covering rule that lock demanded before coverage could land.
      * Box 7's code goes through VERBATIM; a code the dictionary does not recognise, or one
        gating an unsupported path (early distributions among them), stops as the engine's own
        knockout rather than being second-guessed here. on an IRA/SEP/SIMPLE form a code
        containing G or H ALSO derives the line 4c election `rollover` — the payer's statement,
        not a person's choice — so the full and the partial direct rollover compute; one
        reported as fully taxable (box 2a equal to box 1) stays the engine's own knockout.
      * a positive qualified charitable distribution derives the election `qcd` with its
        amount and the split-interest answer; the filer's history goes on the root writable.
      * a positive rolled-over amount sends the frontier's indirect-rollover inputs (the
        60-day answer true by the question's words; the IRA one-per-year answer as given).
      * The checkboxes read as the form does: absent means unchecked.
    """
    if not items:
        return
    ids = []
    for i, item in enumerate(items):
        cid = _uuid("9", i)
        ids.append(cid)
        b = f"/form1099Rs/#{cid}"
        f[f"{b}/filer"] = _collection_item(filer_ref(item["person"]))
        f[f"{b}/payer"] = _str("Synthetic Payer")
        f[f"{b}/factaFilingRequirement"] = _bool(False)
        f[f"{b}/writableGrossDistribution"] = _dollar(item["gross_distribution_cents"])
        if "taxable_amount_cents" in item:
            f[f"{b}/writableTaxableAmount"] = _dollar(item["taxable_amount_cents"])
        f[f"{b}/writableTaxableAmountNotDetermined"] = _bool(
            bool(item.get("taxable_amount_not_determined", False)))
        f[f"{b}/writableDistributionCode"] = _str(item["distribution_code"])
        f[f"{b}/iraSepSimple"] = _bool(bool(item.get("ira_sep_simple", False)))
        f[f"{b}/writableFederalWithholding"] = _dollar(
            item.get("federal_withholding_cents", 0))
        # boxes 8 and 9a, sent verbatim when present — blank sends nothing (the form's own
        # default). At the pin any nonblank entry is the dictionary's own knockout (measured on a
        # code-7 pension and on an IRA form: `/knockoutForForm1099RBox8Value`, `…Box8Percentage`,
        # `…Box9aPercentage`; a zero computes unchanged; box 8 beside code W stays the knockout —
        # no Simplified Method runs here). Form 4972, which would consume them, is the day-armed
        # chain that stays unarmed. The box 9a root resolves a Placeholder on a non-IRA form
        #; `operations._PLACEHOLDER_ROOT_NAMED_BY_CAUSE` serves it from the cause.
        for field in (R1099_BOX8_PERCENT_FIELD, R1099_BOX9A_FIELD):
            if field in item and not (isinstance(item[field], str) and _R1099_PERCENT_SHAPE.fullmatch(item[field])):
                # the dictionary's Match limit, refused here: an engine limit violation is an
                # error, not a knockout (measured: "150" leaves the flag true with no member named)
                raise FactsSchemaError(f"r1099s[{i}].{field} is not a percentage in the form's own "
                                       "shape (0 to 100, up to three decimals)")
        if R1099_BOX8_AMOUNT_FIELD in item:
            f[f"{b}/writableOtherDollar"] = _dollar(item[R1099_BOX8_AMOUNT_FIELD])
        if R1099_BOX8_PERCENT_FIELD in item:
            f[f"{b}/writableOtherPercentage"] = _str(item[R1099_BOX8_PERCENT_FIELD])
        if R1099_BOX9A_FIELD in item:
            f[f"{b}/writablePercentageTotalDistribution"] = _str(item[R1099_BOX9A_FIELD])
            # The dictionary's box 9a knockout now refuses only on an AFFIRMATIVE
            # contradiction, and one of the boxes it reads is box 2b's "Total distribution" mark,
            # which this schema does not carry — so on a pension form a box 9a share stopped
            # refusing and the return computed with no word about Form 4972 (measured: 50.00 and
            # 100 both `complete`). A pin bump does not widen coverage by accident: the earlier
            # posture is kept here by name until box 2b's mark is read. An IRA form and a
            # direct-rollover code are still the dictionary's own knockout, served with words.
            # (The shape check above leaves only 0-100 with up to three decimals, so float is exact
            # enough to tell 0 from not 0.)
            if float(item[R1099_BOX9A_FIELD]) != 0 and not item.get("ira_sep_simple") \
                    and str(item.get("distribution_code", "")).upper() not in ("G", "H"):
                raise ServiceFactsError(
                    f"r1099s[{i}].{R1099_BOX9A_FIELD} is other than 0 — box 9a reports this "
                    f"person's share of a total distribution, which may be figured on Form 4972, "
                    f"and that form is not in the covered set; refused rather than computed "
                    f"without it")
        if R1099_MRA_FIELD in item:                                           # code 3, line 1h
            f[f"{b}/writableReachedMinimumRetirementAge"] = _bool(bool(item[R1099_MRA_FIELD]))
        if _pso_item_asked(item):                                             # IRC 402(l)
            # The chain as far as answered: a no anywhere ends it (sent, so the dictionary's flow
            # sees an answer); the amount behind the second yes is required by the gaps, so a
            # yes/yes with no amount never reaches the engine's own knockout from here.
            if R1099_PSO_FIELD in item:
                f[f"{b}/writeablePublicSafetyOfficer"] = _bool(bool(item[R1099_PSO_FIELD]))
            if _pso_item_premiums_asked(item) and R1099_PSO_PREMIUMS_FIELD in item:
                f[f"{b}/writeablePublicSafetyOfficerPremiums"] = _bool(bool(item[R1099_PSO_PREMIUMS_FIELD]))
            if _pso_item_amount_asked(item) and R1099_PSO_AMOUNT_FIELD in item:
                f[f"{b}/writablePsoPremiumsPaid"] = _dollar(item[R1099_PSO_AMOUNT_FIELD])
        if _db_dated(item):                                                   # IRC 101, box 13
            # Box 13 opens the dictionary's guard; every answer below is IsComplete-guarded there,
            # so the chain is sent as far as answered and an unanswered link is the gaps' to ask —
            # never the engine's knockout from here, except the code 4 form whose box 1 the filer
            # says is not that contract's death benefit (the dictionary's own refusal, with words).
            f[f"{b}/writableDateOfPayment"] = _day(item[R1099_DATE_FIELD])
            if _db_box1_asked(item) and R1099_DB_BOX1_FIELD in item:
                f[f"{b}/writableBox1IsTheDeathBenefitUnderThatContract"] = _bool(bool(item[R1099_DB_BOX1_FIELD]))
            if _db_sale_asked(item) and R1099_DB_SALE_FIELD in item:
                f[f"{b}/writableAcquiredInReportablePolicySale"] = _bool(bool(item[R1099_DB_SALE_FIELD]))
            if _db_consideration_asked(item) and R1099_DB_CONSIDERATION_FIELD in item:
                f[f"{b}/writableDeathBenefitAcquiredForValuableConsideration"] = _bool(bool(item[R1099_DB_CONSIDERATION_FIELD]))
            if _db_carryover_asked(item):
                if R1099_DB_CARRYOVER_FIELD in item:
                    f[f"{b}/writableDeathBenefitTransferHasCarryoverBasis"] = _bool(bool(item[R1099_DB_CARRYOVER_FIELD]))
                if R1099_DB_RELATED_FIELD in item:
                    f[f"{b}/writableDeathBenefitTransferToInsuredOrRelatedParty"] = _bool(bool(item[R1099_DB_RELATED_FIELD]))
            if _db_basis_asked(item) and R1099_DB_BASIS_FIELD in item:
                f[f"{b}/writableReportableDeathBenefitBasis"] = _dollar(item[R1099_DB_BASIS_FIELD])
        if _cents_or_zero(item.get(R1099_HFD_FIELD)) > 0:                   # line 4c, hfd
            f[f"{b}/writableLine4cElection"] = _enum("/line4cElectionOptions", "hfd")
            f[f"{b}/writableHfdAmount"] = _dollar(item[R1099_HFD_FIELD])
            # an HSA funding distribution is not a qualified charitable distribution: the
            # dictionary's QCD-only box 3 question, derived, never asked (DERIVED_FROM_INPUT)
            f[f"{b}/writableIsBox3SplitInterestEntityQcd"] = _bool(False)
        elif r1099_direct_rollover(item):                                     # line 4c, rollover
            # The payer's code G/H says the distribution was rolled over directly: the
            # dictionary's line 4c election is the code's own, derived, never asked. Measured:
            # an IRA 1099-R of 10,000 with code G and box 2a 0 was /knockoutIraSepSimple and
            # now files at the parent's figure; a partial one (box 2a 4,000) taxes the 4,000.
            f[f"{b}/writableLine4cElection"] = _enum("/line4cElectionOptions", "rollover")
        elif _cents_or_zero(item.get(R1099_QCD_FIELD)) > 0:                   # line 4c, qcd
            # The trustee paid this part directly to a charity: the dictionary's election, its
            # amount, and the split-interest answer the arm needs answered (false computes; a
            # yes is the dictionary's own knockout). The filer's history rides on the root
            # writable (`_qcd_history_section`). Measured: 10,000 of 10,000, 1,128.00 → 126.00.
            f[f"{b}/writableLine4cElection"] = _enum("/line4cElectionOptions", "qcd")
            f[f"{b}/writableQcdAmount"] = _dollar(item[R1099_QCD_FIELD])
            f[f"{b}/writableIsQcdToSplitInterestEntity"] = _bool(bool(item.get(R1099_QCD_SPLIT_FIELD, False)))
        elif _cents_or_zero(item.get(R1099_ROLLOVER_FIELD)) > 0:              # the indirect rollover
            # The recipient rolled this part over themselves within 60 days — the question's
            # own words carry the 60 days, so the frontier's 60-day answer is true by the
            # answer; a rollover outside them is a 0 here. On an IRA form the one-per-year
            # answer rides with it (false is the dictionary's knockout). Measured: a pension
            # form's 10,000 rolled over, 2,075.00 → 928.00; 4,000 of it → 1,595.00.
            f[f"{b}/writableIsIndirectRollover"] = _bool(True)
            f[f"{b}/writableIndirectRolloverAmount"] = _dollar(item[R1099_ROLLOVER_FIELD])
            f[f"{b}/writableIndirectRolloverWithin60Days"] = _bool(True)
            if item.get("ira_sep_simple"):
                f[f"{b}/writableIraOneRolloverPerYearSatisfied"] = _bool(bool(item.get(R1099_IRA_ONE_PER_YEAR_FIELD, False)))
        if R1099_ROLLOVER_FIELD in item and _cents_or_zero(item[R1099_ROLLOVER_FIELD]) == 0:
            # The person's "0 rolled over" IS the answer to the rollover question,
            # and the dictionary now wants it said. Unsent, a form whose box 2a is 0 leaves the
            # partly-taxable-pension chain — and taxable income with it — unresolved (measured on
            # wages-and-r1099-single with box 2a 0: nothing served; sent as no, 3,665.00, the
            # earlier pin's figure). On every other form it moves nothing (measured: 4,865.00 either way).
            f[f"{b}/writableIsIndirectRollover"] = _bool(False)
    f["/form1099Rs"] = _collection(ids)


_INCOME_MAPPERS["r1099s"] = _map_r1099s


def _address():
    """A synthetic placeholder address — the first this mapper synthesizes. An address is an
    identifier and never crosses; the engine wants one where a form prints one."""
    return {"$type": "gov.irs.factgraph.persisters.AddressWrapper",
            "item": {"streetAddress": "1 Synthetic St", "city": "Springfield",
                     "postalCode": "00000", "stateOrProvence": "TN", "country": "USA"}}


def _map_care_providers(f: dict, items: list, filer_ref) -> None:
    """Form 2441 line 1, one item per provider. Measured to closure at the pin: a provider
    is complete with a name, an address (or an employer's W-2, not carried), an identification
    (an EIN, a TIN, or the tax-exempt answer), the tax-exempt answer for an organization, and
    the amount. The person's own answers are the type (the column (c) vocabulary: EIN,
    "Tax-Exempt", or SSN), the household-employee column and the amount; the identity is
    synthetic (PLUMBING) and the employer-furnished answer is no (published). The household-
    employee yes is the dictionary's own knockout, served with words. Without items the
    scaffold's empty collection and Done marker stand."""
    if not items:
        return
    ids = []
    for i, item in enumerate(items):
        cid = _uuid("4", i)
        ids.append(cid)
        b = f"/cdccCareProviders/#{cid}"
        kind = item[CDCC_PROVIDER_TYPE_FIELD]
        if kind not in CDCC_PROVIDER_TYPES:
            raise FactsSchemaError(
                f"{CDCC_GROUP}[{i}].{CDCC_PROVIDER_TYPE_FIELD} must be one of "
                f"{', '.join(CDCC_PROVIDER_TYPES)}, got {kind!r}")
        f[f"{b}/isEmployerFurnished"] = _bool(False)
        organization = kind != "individual"
        f[f"{b}/writableIsOrganization"] = _bool(organization)
        if organization:
            f[f"{b}/writableOrganizationName"] = _str("Synthetic Care Provider")
            f[f"{b}/writableIsTaxExempt"] = _bool(kind == "tax_exempt_organization")
            if kind == "organization":
                f[f"{b}/hasTinOrEin"] = _bool(True)
                f[f"{b}/writableEin"] = _ein("00", f"{9100000 + i:07d}")
        else:
            f[f"{b}/writableFirstName"] = _str("Synthetic")
            f[f"{b}/writableLastName"] = _str("Provider")
            f[f"{b}/hasTinOrEin"] = _bool(True)
            f[f"{b}/writableTin"] = _tin("900", "00", f"{i + 1:04d}")
        f[f"{b}/writableAddress"] = _address()
        f[f"{b}/writableAmountPaidForCare"] = _dollar(item[CDCC_AMOUNT_FIELD])
        f[f"{b}/writableIsHouseholdEmployee"] = _bool(item[CDCC_HOUSEHOLD_EMPLOYEE_FIELD])
    f["/cdccCareProviders"] = _collection(ids)


_INCOME_MAPPERS[CDCC_GROUP] = _map_care_providers


def _cdcc_section(f: dict, facts: dict, filer_by_index: dict, tax_year: int) -> None:
    """Form 2441 line 2: each qualifying person's expenses, and the two root answers the
    section derives from them. Measured at the pin: the credit is the sum of the per-person
    amounts, each gated by the row's has-expenses answer and the paid-to-a-qualifying-provider
    answer (assumed, published — the ask carries the rule); a qualifying row WITHOUT an answer
    must say no or the section stalls; the root has-expenses answer opens the section and the
    total is wanted only by the benefits side (sent when above zero)."""
    total = 0
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict) or not care_expense_question_reached(facts, i, tax_year):
            continue
        base = (f"/familyAndHousehold/#{_uuid('2', i + 1)}" if person.get("role") == "dependent"
                else f"/filers/#{filer_by_index[i]}")
        amount = person.get(CARE_EXPENSES_FIELD)
        has = isinstance(amount, int) and not isinstance(amount, bool) and amount > 0
        f[f"{base}/cdccHasDependentCareExpenses"] = _bool(has)
        if has:
            f[f"{base}/cdccHadExpensesPaidToQualifyingProvider"] = _bool(True)
            f[f"{base}/writableCdccQualifyingExpenseAmount"] = _dollar(amount)
            total += amount
    f["/writableCdccHasQualifyingExpenses"] = _bool(total > 0)
    # Part III wants the total even at 0 once a benefit is reported (measured: without it
    # the section stalls; with it every dollar of the benefit is taxable on line 1e).
    reported = dcb_reported(facts)
    if total > 0 or reported:
        f["/writableCdccTotalQualifiedDependentCareExpenses"] = _dollar(total)
    # each filer's plan maximum and sole-proprietorship benefit (box 10 rides on the W-2
    # in `_w2`), then the root line 13 carryover and line 14 forfeiture — each a money answer
    # the dictionary's yes/no pair is derived from; the carryover writable carries a one-cent
    # floor, so the amount is sent only above 0.
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict) or person.get("role") not in ("primary", "spouse"):
            continue
        who = "Primary" if person.get("role") == "primary" else "Secondary"
        reached = dcb_person_questions_reached(facts, i)
        if DCB_PLAN_MAX_FIELD in reached and DCB_PLAN_MAX_FIELD in person:
            f[f"/writable{who}FilerDependentCarePlanMaximum"] = _dollar(person[DCB_PLAN_MAX_FIELD])
        if DCB_SELF_EMPLOYED_FIELD in reached and DCB_SELF_EMPLOYED_FIELD in person:
            f[f"/writable{who}FilerSelfEmployedDependentCareBenefits"] = _dollar(
                person[DCB_SELF_EMPLOYED_FIELD])
    carry = _cents_or_zero(facts.get(DCB_CARRYOVER_FIELD)) if reported else 0
    f["/hasCdccCarryoverAmountFromPriorTaxYear"] = _bool(carry > 0)
    if carry > 0:
        f["/writableCdccCarryoverAmountFromPriorTaxYear"] = _dollar(carry)
    # Form 2441 Worksheet A — the root sent on every Form 2441 return (absent is the no the
    # statement says), the rest as far as the chain reaches.
    reached_wa = worksheet_a_questions_reached(facts)
    if WORKSHEET_A_ROOT_FIELD in reached_wa:
        f["/cdccHasCreditForPriorYearExpenses"] = _bool(facts.get(WORKSHEET_A_ROOT_FIELD) is True)
        for field, path in ((WORKSHEET_A_CLAIMED_FIELD, "/cdccClaimedCreditForPriorYearExpenses"),
                            (WORKSHEET_A_CLAIMED_MAX_FIELD, "/cdccClaimedMaxCreditForPriorTaxYear")):
            if field in reached_wa and field in facts:
                f[path] = _bool(bool(facts[field]))
        for field in WORKSHEET_A_CARRY_FIELDS:
            if field in reached_wa and field in facts:
                value = facts[field]
                f[WORKSHEET_A_PATHS[field]] = (_bool(bool(value)) if isinstance(value, bool)
                                               else _dollar(value))
    if reported:
        forfeited = _cents_or_zero(facts.get(DCB_FORFEITED_FIELD))
        f["/writableHasCdccForfeitedCredits"] = _bool(forfeited > 0)
        if forfeited > 0:
            f["/writableCdccForfeitedCredits"] = _dollar(forfeited)


def _month_enum(months) -> dict:
    """The dictionary's multi-enum of coverage months, lowercase three-letter values."""
    return {"$type": "gov.irs.factgraph.persisters.MultEnumWrapper",
            "item": {"enumOptionsPath": "/1095As/*/monthOptions", "values": list(months)}}


def _map_f1095as(f: dict, items: list, filer_ref) -> None:
    """Form 1095-A Part III, the one form the pin accepts. Measured to closure:

      * the coverage months are the months whose column A is above zero; the policy dates are
        the first and last of them — day 01 and the month's last day, synthesized by
        construction (the form's Part III months ARE the coverage months: a policy that began
        mid-month reaches Part III only through the birth/adoption exception, and either way
        that month is one the form reports, so day 01 is the right posture and the served
        lines are day-invariant);
      * a 12-month LEVEL policy (every column A equal, every column B equal) takes the annual
        route: line 33's totals, `writablePremiumsOrSlcspChange` no, the annual advance payment
        when any was made — Form 8962 line 10 yes, line 11;
      * anything else takes the monthly route (lines 12-23): every month inside the policy's
        dates carries its three monthly writables (0 for a month without coverage — a gap
        closes, measured), and a 12-month policy says `writablePremiumsOrSlcspChange` yes.
        Annual totals on a partial-year policy compute a SILENT ZERO (measured), which is why
        the grid, not the totals, is the input;
      * `hasChangeInCircumstance` no is the section's one assumption, published."""
    if not items:
        return
    item = items[0]
    cid = _uuid("0", 1)          # the one prefix no other collection uses
    b = f"/1095As/#{cid}"
    covered = ptc_covered_months(item)
    first, last = PTC_MONTHS.index(covered[0]), PTC_MONTHS.index(covered[-1])
    in_range = PTC_MONTHS[first:last + 1]
    year = _PINNED_TAX_YEAR
    import calendar
    f[f"{b}/writablePolicyStartDate"] = _day(f"{year}-{first + 1:02d}-01")
    f[f"{b}/writablePolicyEndDate"] = _day(f"{year}-{last + 1:02d}-{calendar.monthrange(year, last + 1)[1]:02d}")
    f[f"{b}/hasCoverageMonths"] = _bool(True)
    f[f"{b}/coverageMonths"] = _month_enum(covered)
    f[f"{b}/hasChangeInCircumstance"] = _bool(False)
    premiums = [_ptc_cents(item, m, "premium") for m in PTC_MONTHS]
    slcsps = [_ptc_cents(item, m, "slcsp") for m in PTC_MONTHS]
    aptcs = [_ptc_cents(item, m, "aptc") for m in PTC_MONTHS]
    level_full_year = (len(covered) == 12 and len(set(premiums)) == 1 and len(set(slcsps)) == 1)
    if level_full_year:
        f[f"{b}/writablePremiumsOrSlcspChange"] = _bool(False)
        f[f"{b}/writablePtcAnnualPremium"] = _dollar(sum(premiums))
        f[f"{b}/writableSlcspAnnualPremium"] = _dollar(sum(slcsps))
        if any(aptcs):
            f[f"{b}/writableAptcAnnualAmount"] = _dollar(sum(aptcs))
    else:
        if len(in_range) == 12:
            f[f"{b}/writablePremiumsOrSlcspChange"] = _bool(True)
        for m in in_range:
            for column, stem, _letter in PTC_COLUMNS:
                f[f"{b}/writablePtcMonthly{stem}{PTC_MONTH_TITLES[m]}"] = _dollar(_ptc_cents(item, m, column))
    f["/1095As"] = _collection([cid])


_INCOME_MAPPERS[PTC_GROUP] = _map_f1095as


def _ptc_section(f: dict, facts: dict) -> None:
    """The premium tax credit's root answers: the has-plan answer is the group's own
    presence (false on every return without a form — the wages-only goldens do not move); with a
    form, the has-advance answer from column C, Form 8962 line 9's gate as its two writables
    (no, the yes being refused upstream), and the reached root questions as answered."""
    items = facts.get(PTC_GROUP) or []
    f["/writableHasPtcQualifyingPlan"] = _bool(bool(items))
    if not items:
        return
    f["/writableHasAdvancedPtc"] = _bool(ptc_has_aptc(facts))
    f["/writableIsAdditionalPersonInEnrollmentFamily"] = _bool(False)
    f["/writableWantsToUseAltCalculations"] = _bool(False)
    reached = ptc_questions_reached(facts)
    for field, path in ((PTC_ESTIMATE_FIELD, "/writableMarketplaceEstimatedIncomeAtLeast100Fpl"),
                        (PTC_MEDICAID_FIELD, "/writableBelow100ThresholdAndNotEligibleForMedicaidBecauseOfImmigrationStatus"),
                        (PTC_IMMIGRATION_FIELD, "/writableHasImmigrationStatusNotEligibleForMarketplace"),
                        (PTC_MFS_EXCEPTION_FIELD, "/writableHasMfsException"),
                        (PTC_MFS_FOURTH_YEAR_FIELD, "/writableClaimingMfsExceptionForFourthStraightYear")):
        if field in reached:
            f[path] = _bool(bool(facts[field]))
    if PTC_DEPENDENTS_MAGI_FIELD in reached and PTC_DEPENDENTS_MAGI_FIELD in facts:
        f["/writablePtcDependentsModifiedAgi"] = _dollar(facts[PTC_DEPENDENTS_MAGI_FIELD])
    if PTC_DEPENDENTS_MAGI_FIELD in reached:
        # The yes/no the dictionary's own member reads (`/dependentsRequiredToFile`: a qualifying
        # plan, a claimed dependent, this answer — IRC 36B(d)(2)(A)), derived from the line 2b
        # amount as the HSA carry-in's root is derived: a positive amount is a dependent required
        # to file (line 2b is entered only for one), and that is the dictionary's own refusal,
        # served with words; 0 or absent is the no the absence statement already says. Unsent, the
        # member never resolved and a positive line 2b filed complete (measured at the pin).
        f["/writableDependentsRequiredToFile"] = _bool(_cents_or_zero(facts.get(PTC_DEPENDENTS_MAGI_FIELD)) > 0)


def _map_schedule_c(f: dict, items: list, filer_ref) -> None:
    """Schedule C activities -> `/scheduleCs` (the sixth stream).

    The pinned dictionary's OWN intake is the collapsed one — lines 8-27a, home-office and
    vehicle detail are one line 28 total — so the mapping is the form's summary lines, verbatim:
      * Lines 1, 2, 4, 6, 28 map straight through; the three optional amounts are sent as zero
        when absent, and SAID (`gaps._ABSENT_MEANS`). COGS is its own line — folding it into
        line 28 double-subtracts it, on the dictionary's own warning.
      * Line B goes through when supplied; a blank line B stays a blank box.
      * THE LOSS GATE: line G and box 32a are the filer's answers, never this service's. A loss
        item reaches here only with both answered (the guard refuses/asks otherwise), and a
        line G No is refused before this runs. RETIRED: the sentence that stood here ("box
        32b is refused too, so `writableAllInvestmentAtRisk` is only ever emitted true and
        `writableAmountAtRisk` — the Form 6198 branch — stays provably outside the emission
        surface"): box 32b is emitted now, with `writableAmountAtRisk` beside it. On a profit,
        an unanswered box 32 is unsent — the form does not ask it there either.
      * No business name, address or EIN crosses — identity may not cross; unlike the
        1099 payers the engine needs no placeholder here (measured: the flow completes without
        one), so nothing synthetic is emitted at all.
    """
    if not items:
        return
    ids = []
    for i, item in enumerate(items):
        cid = _uuid("c", i)
        ids.append(cid)
        b = f"/scheduleCs/#{cid}"
        f[f"{b}/filer"] = _collection_item(filer_ref(item["person"]))
        f[f"{b}/writableGrossReceipts"] = _dollar(item["gross_receipts_cents"])
        f[f"{b}/writableReturnsAndAllowances"] = _dollar(
            item.get("returns_and_allowances_cents", 0))
        f[f"{b}/writableCostOfGoodsSold"] = _dollar(item.get("cost_of_goods_sold_cents", 0))
        f[f"{b}/writableOtherBusinessIncome"] = _dollar(
            item.get("other_business_income_cents", 0))
        f[f"{b}/writableTotalExpenses"] = _dollar(item["total_expenses_cents"])
        if "principal_business_code" in item:
            f[f"{b}/writableLineBPrincipalBusinessCode"] = _str(item["principal_business_code"])
        if "materially_participated" in item:
            f[f"{b}/writableMateriallyParticipated"] = _bool(item["materially_participated"])
        if "all_investment_at_risk" in item:
            f[f"{b}/writableAllInvestmentAtRisk"] = _bool(item["all_investment_at_risk"])
        # the simplified Form 6198 Part II line 10b figure. Sent only where the guard
        # above lets it be answered — box 32b on a line 31 loss — so the dictionary's own
        # "consulted only when box 32 is answered and false" is never contradicted.
        if "amount_at_risk_cents" in item:
            f[f"{b}/writableAmountAtRisk"] = _dollar(item["amount_at_risk_cents"])
    f["/scheduleCs"] = _collection(ids)
    f["/hasScheduleCIncome"] = _bool(True)


_INCOME_MAPPERS["schedule_c"] = _map_schedule_c

# Schedule E line 1b's printed type-of-property codes, from the list the form prints below the
# table. RETIRED: the clause that stood here ("`self_rental` (code 7) is refused before
# mapping"): code 7 maps, and it is the one code that is not record-only in this service, because
# the flag the recharacterization rule turns on is DERIVED from it. Codes 3 (vacation/short-term)
# and 6 (royalties) have no service vocabulary — the schema's enum is the covered set.
_RENTAL_TYPE_CODES = {"residential": 1, "commercial": 4, "land": 5, "self_rental": 7, "other": 8}


def _map_rentals(f: dict, items: list, filer_ref) -> None:
    """Rental properties -> `/rentalProperties` (the seventh stream; itemized
    expenses and depreciation inputs added later).

    The dictionary ITEMIZES Schedule E's expense lines (unlike Schedule C, where it collapses
    them). This service now offers BOTH of the dictionary's own shapes, refused if a property
    answers both (`refuse_mixed_rental_expense_shapes`):
      * the LUMP shape — `total_expenses_cents`, one question, riding line 19 (other) — is the
        original design and stays exactly as it computed: insurance, management fees,
        repairs, taxes and the depreciation override are asserted zero on this path (the
        engine's non-complete-safe intakes; measured at the pin, the flow never resolves while
        any of them is unanswered).
      * the ITEMIZED shape — `insurance_cents`, `management_fees_cents`,
        `repairs_cents`, `taxes_cents` ride their own printed lines (9, 11, 14, 16) directly,
        zero when absent and SAID (`gaps._ABSENT_MEANS`, since each is now sometimes a real
        figure and sometimes an unasked zero on the SAME emitted path — the four moved OUT of
        `ASSUMED_ABOUT_TAXPAYER`, which cannot say "sometimes"). Depreciation (line 18) is
        NEVER this service's to state: `building_basis_cents` and, once positive,
        `is_nonresidential_real_property` (Form 4562 Part III's recovery-period class — a
        question there, and a dictionary knockout otherwise:
        `rental_building_class_armed`/`require_building_class`) drive the engine's own
        straight-line building depreciation; `placed_in_service_in_current_year` (and, once
        true, `placed_in_service_month`) selects the mid-month first-year fraction;
        `has_five_year_property` and, once true, `five_year_property_basis_cents` drive the
        engine's own 5-year MACRS personal-property depreciation. `depreciationOverride` is
        sent (zero) ONLY when NEITHER a building basis NOR a 5-year property is given — the
        no-depreciation-input path, byte-identical to every earlier lump-shape return — and
        omitted entirely otherwise, so the engine's own MACRS computation runs unreplaced.
      * THE LOSS GATE, measured rather than imported from Schedule C. RETIRED: the clause
        that stood here ("`fullyAtRisk` is only ever emitted TRUE — a false is refused before
        this runs, keeping `amountAtRisk`, the Form 6198 branch, outside the emission
        surface"): the boolean is emitted both ways now, with `amountAtRisk` beside a false.
        `activeParticipation` goes through
        as the filer's own §469(i) answer and BOTH values compute (a No suspends the loss on
        the engine's modeled Form 8582 path — the opposite of Schedule C's record-only line G).
      * `priorYearUnallowedLoss` (last year's Form 8582 figure) is sent only when stated —
        absence means no carry-in, and the assumptions say so.
      * Line 1b's type code is RECORD ONLY in the dictionary and goes through for the printed
        box — with ONE exception this service makes deliberately. Retired: the clause that
        stood here ("`self_rental` is refused (the recharacterization it triggers needs an
        unasked answer)"): type 7 is answered now, and because the form's own list labels it
        "Self-Rental" the code DERIVES `selfRental` rather than a second boolean being asked
        beside it. The dictionary's own warning is why — a separately answered flag could
        disagree with the code, and the code would lose silently. The derivation is published as
        an assumption on every return that carries it. `materiallyParticipatesInLessee` is the
        filer's own §469(c)(1)/(h) answer about the LESSEE business, asked on a self-rental
        profit and refused off that population; together the two move the profit out of the
        §8582 pool (Reg. §1.469-2(f)(6)).
      * No identity crosses: the property's address (line 1a) is never sent, and the flow
        completes without it — nothing synthetic is emitted.
    """
    if not items:
        return
    ids = []
    for i, item in enumerate(items):
        cid = _uuid("d", i)
        ids.append(cid)
        b = f"/rentalProperties/#{cid}"
        # THERE IS NO `/rentalProperties/*/filer` — the W-2G shape: the 1040 consumes aggregate
        # rental totals summed over every property regardless of whose it is. `person` is still
        # VALIDATED (an index naming nobody is refused), then maps nowhere.
        filer_ref(item["person"])
        f[f"{b}/grossIncome"] = _dollar(item["rents_received_cents"])
        f[f"{b}/writableLine19OtherExpense"] = _dollar(item.get("total_expenses_cents", 0))
        # each printed line is its own answer, zero when absent (`gaps._ABSENT_MEANS`
        # states it — these are no longer a universal assumption, since they are sometimes a
        # real figure).
        f[f"{b}/insurance"] = _dollar(item.get("insurance_cents", 0))
        f[f"{b}/managementFees"] = _dollar(item.get("management_fees_cents", 0))
        f[f"{b}/repairs"] = _dollar(item.get("repairs_cents", 0))
        f[f"{b}/taxes"] = _dollar(item.get("taxes_cents", 0))
        claims_building = "building_basis_cents" in item
        claims_five_year = item.get("has_five_year_property") is True
        if claims_building:
            f[f"{b}/buildingBasis"] = _dollar(item["building_basis_cents"])
            if "is_nonresidential_real_property" in item:
                f[f"{b}/writableIsNonresidentialRealProperty"] = _bool(
                    item["is_nonresidential_real_property"])
            if "building_uses_standard_gds" in item:
                f[f"{b}/writableBuildingBasisUsesStandardGDS"] = _bool(
                    item["building_uses_standard_gds"])
            if "placed_in_service_in_current_year" in item:
                f[f"{b}/placedInServiceInCurrentYear"] = _bool(
                    item["placed_in_service_in_current_year"])
                if "placed_in_service_month" in item:
                    f[f"{b}/placedInServiceMonth"] = _int_wrap(item["placed_in_service_month"])
        if "has_five_year_property" in item:
            f[f"{b}/hasFiveYearProperty"] = _bool(item["has_five_year_property"])
        if claims_five_year:
            f[f"{b}/fiveYearPropertyBasis"] = _dollar(item.get("five_year_property_basis_cents", 0))
        # The no-depreciation-input path: nothing to depreciate was given at all, so line 18
        # prints zero exactly as every earlier return did — `ASSUMED_ABOUT_TAXPAYER` states it.
        # Omitted (never sent) once either depreciation input is given, so the engine's own
        # MACRS computation runs unreplaced.
        if not claims_building and not claims_five_year:
            f[f"{b}/depreciationOverride"] = _dollar(0)
        if "property_type" in item:
            f[f"{b}/writableLine1bPropertyTypeCode"] = _int_wrap(
                _RENTAL_TYPE_CODES[item["property_type"]])
            # emitted only where the code says type 7. The dictionary's flag is
            # three-state and false-or-unanswered means the same thing (the ordinary passive
            # path), so sending a false on every other code would add an emitted fact that
            # changes nothing — and the ONE state that matters is the one the code states.
            if rental_is_self_rental(item):
                f[f"{b}/selfRental"] = _bool(True)
        if "materially_participates_in_lessee" in item:
            f[f"{b}/materiallyParticipatesInLessee"] = _bool(
                item["materially_participates_in_lessee"])
        if "active_participation" in item:
            f[f"{b}/activeParticipation"] = _bool(item["active_participation"])
        if "fully_at_risk" in item:
            f[f"{b}/fullyAtRisk"] = _bool(item["fully_at_risk"])
        # the simplified Form 6198 Part II line 10b figure, sent only on the population
        # the guard above allows to answer it (the at-risk answer No, on a current-year loss).
        if "amount_at_risk_cents" in item:
            f[f"{b}/amountAtRisk"] = _dollar(item["amount_at_risk_cents"])
        if "prior_year_unallowed_loss_cents" in item:
            f[f"{b}/priorYearUnallowedLoss"] = _dollar(item["prior_year_unallowed_loss_cents"])
        # sent only on the population the guard allows to answer it (a carried-in loss above
        # zero, active participation yes).
        if "active_participation_when_loss_arose" in item:
            f[f"{b}/writableActivelyParticipatedWhenPriorYearLossArose"] = _bool(
                item["active_participation_when_loss_arose"])
    f["/rentalProperties"] = _collection(ids)
    f["/hasScheduleERentalIncome"] = _bool(True)


_INCOME_MAPPERS["rentals"] = _map_rentals

# The dictionary's own K-1 entity-type literals (/k1EntityTypeOptions) — the _DICT_FILING lesson
# again: the service's `s_corp` is the dictionary's `sCorp`.
_K1_ENTITY = {"partnership": "partnership", "s_corp": "sCorp"}


def _map_k1s(f: dict, items: list, filer_ref) -> None:
    """Schedule K-1s -> TWO collections, split on `source` (the LAST stream).

    Which form comes first (cheap gate before expensive entry), because the three forms
    number their boxes differently and the pinned dictionary routes them differently:
    partnership and s_corp K-1s are `/formK1s` items (Schedule E Part II), the estate_trust
    K-1 is a `/form1041K1s` item (Part III) with its OWN leaf names and NO per-item filer
    (the W-2G posture: `person` is validated, then maps nowhere — Part III sums over every
    item regardless of whose it is).

      * Box 1 / box 6 goes through SIGNED, as the box prints it. A partnership/s_corp loss
        reaches here only with the loss trio answered (material participation, basis,
        at-risk — the guard asks otherwise); the engine then computes EVERY combination,
        including the Form 8582 suspension on a No and the basis-capped deduction. An
        estate_trust loss never reaches here (refused: it would deduct as entered).
      * Item D is asked on every partnership K-1 — measured: the pinned flow-completeness
        guard (`/formK1sItemDIsComplete`) stays false without it. Both answers compute; on a
        PTP the engine's own §469(k)/limited-partner presumption takes over UNLESS item G
        says general partner (the presumption reads item G).
      * Item G is asked on every partnership K-1 too: it decides whether a box 4b
        payment is excluded from net investment income (a limited partner above the Form
        8960 threshold is the engine's own knockout, served as a refusal) and whether the
        PTP presumption above applies.
      * Boxes 4a/4b (guaranteed payments) go through as printed, nonpassive to Schedule E
        line 28 column (k). Reporting one makes box 14 code A a question (0 is an answer):
        the dictionary's SE-assessment gate would otherwise resolve the item Incomplete,
        which the pinned runner discards — so the ask and its backstop are the service's.
      * Box 20 code Z belongs to an item-D PTP and nowhere else. The amount is ASKED
        on every such K-1 because nothing refuses its absence — the complete-safe alias
        resolves $0 and the qualified business income deduction is quietly forgone — and it
        is REFUSED off that population, because a code Z amount from a partnership that is
        not a PTP is per-business QBI (`qbi:/qualifiedBusinesses`), an intake not carried
        here. That refusal is also what makes `/knockoutK1QualifiedPtpAmountWithoutItemD`
        unreachable through this mapper: no request shape emits the amount without item D.
      * Box 14A (SE earnings) goes through verbatim, negatives included. A blank box is no SE
        earnings: the partnership computes the figure. Retired: the sentence that stood
        here ("the engine's own knockout stops a negative, because the deductible part of an
        SE loss is the partner's limitation figure") — that figure is now ASKED
        (`deductible_se_loss_cents`, emitted as `writableDeductibleSeEarningsLoss`), so a
        negative 14A computes and `/knockoutK1NegativeSeEarnings` is unreachable through this
        mapper: an unanswered deductible part is refused by name before the engine is called.
      * `fullyAtRisk` is emitted BOTH ways since which retired the standing rule that
        stood here ("only ever emitted TRUE, the third stream running: `amountAtRisk` stays
        provably outside the emission surface") on all three streams at once. A false carries
        `amountAtRisk`, and the basis-allowed loss is capped at it — section 704(d) first,
        section 465 second, measured at the pin.
      * No identity crosses: entity names, addresses, EINs and TINs are never sent, and both
        flows complete without them — nothing synthetic is emitted.
    """
    if not items:
        return
    k1_ids, est_ids = [], []
    for i, item in enumerate(items):
        if item["source"] == "estate_trust":
            filer_ref(item["person"])       # validated, then maps nowhere (no per-item filer)
            cid = _uuid("f", i)
            est_ids.append(cid)
            b = f"/form1041K1s/#{cid}"
            if "ordinary_business_income_cents" in item:
                f[f"{b}/writableBox6OrdinaryBusinessIncome"] = _dollar(
                    item["ordinary_business_income_cents"])
            if "interest_income_cents" in item:
                f[f"{b}/writableBox1InterestIncome"] = _dollar(item["interest_income_cents"])
            if "dividend_income_cents" in item:
                f[f"{b}/writableBox2aOrdinaryDividends"] = _dollar(
                    item["dividend_income_cents"])
                f[f"{b}/writableBox2bQualifiedDividends"] = _dollar(
                    item.get("qualified_dividends_cents", 0))
            continue
        cid = _uuid("e", i)
        k1_ids.append(cid)
        b = f"/formK1s/#{cid}"
        f[f"{b}/filer"] = _collection_item(filer_ref(item["person"]))
        f[f"{b}/entityType"] = _enum("/k1EntityTypeOptions", _K1_ENTITY[item["source"]])
        # box 1 is sent as 0 when blank, and STATED (gaps._ABSENT_MEANS). Unlike the
        # portfolio boxes, `ordinaryIncome` has no 0-default alias in the dictionary: absent,
        # the item's Part II chain resolves Placeholder, /agi inherits it, and every
        # IsComplete(/agi) guard (Form 8960 line 17, the capital-GP knockout) substitutes 0.
        # Measured: sent as 0 the item resolves Complete and the value is unchanged.
        f[f"{b}/ordinaryIncome"] = _dollar(item.get("ordinary_business_income_cents", 0))
        if "publicly_traded_partnership" in item:
            f[f"{b}/writableIsPubliclyTradedPartnership"] = _bool(
                item["publicly_traded_partnership"])
        if "materially_participated" in item:
            f[f"{b}/materiallyParticipated"] = _bool(item["materially_participated"])
        if "basis_cents" in item:
            f[f"{b}/basis"] = _dollar(item["basis_cents"])
        if "fully_at_risk" in item:
            f[f"{b}/fullyAtRisk"] = _bool(item["fully_at_risk"])
        if "amount_at_risk_cents" in item:
            f[f"{b}/amountAtRisk"] = _dollar(item["amount_at_risk_cents"])
        if "se_earnings_cents" in item:
            f[f"{b}/writableSeEarnings"] = _dollar(item["se_earnings_cents"])
        # the deductible part of a box 14A LOSS, SIGNED. Two facts on purpose — the
        # printed box 14A keeps flowing to `seEarnings` for the rest of Schedule SE's
        # reconciliation, and this one is what `seEarningsAllowed` carries onto line 2.
        if "deductible_se_loss_cents" in item:
            f[f"{b}/writableDeductibleSeEarningsLoss"] = _dollar(
                item["deductible_se_loss_cents"])
        if "interest_income_cents" in item:
            f[f"{b}/writablePortfolioInterestIncome"] = _dollar(item["interest_income_cents"])
        if "dividend_income_cents" in item:
            f[f"{b}/writablePortfolioOrdinaryDividends"] = _dollar(
                item["dividend_income_cents"])
            f[f"{b}/writablePortfolioQualifiedDividends"] = _dollar(
                item.get("qualified_dividends_cents", 0))
        if "royalties_cents" in item:
            f[f"{b}/writableK1065Box7Royalties"] = _dollar(item["royalties_cents"])
        # boxes 4a/4b and item G, on the dictionary's own writables (the 0-default
        # aliases downstream keep an item without them byte-identical).
        if "guaranteed_payments_services_cents" in item:
            f[f"{b}/writableGuaranteedPaymentsServices"] = _dollar(
                item["guaranteed_payments_services_cents"])
        if "guaranteed_payments_capital_cents" in item:
            f[f"{b}/writableGuaranteedPaymentsCapital"] = _dollar(
                item["guaranteed_payments_capital_cents"])
        if "general_partner" in item:
            f[f"{b}/writablePartnerIsGeneralPartner"] = _bool(item["general_partner"])
        # box 20 code Z. The amount is SIGNED (a qualified PTP loss is a loss — the
        # floor is Form 8995 line 8 inside the consumer, never here); the SSTB flag and the
        # §469(k) carry-in are optional and send NOTHING when absent, so the dictionary's own
        # complete-safe aliases (false, $0) keep an item without them byte-identical.
        if "qualified_ptp_income_cents" in item:
            f[f"{b}/writableQualifiedPtpIncomeOrLoss"] = _dollar(
                item["qualified_ptp_income_cents"])
        if "qualified_ptp_is_sstb" in item:
            f[f"{b}/writableQualifiedPtpIsSstb"] = _bool(item["qualified_ptp_is_sstb"])
        if "ptp_prior_year_unallowed_loss_cents" in item:
            f[f"{b}/writablePtpPriorYearUnallowedLoss"] = _dollar(
                item["ptp_prior_year_unallowed_loss_cents"])
    if k1_ids:
        f["/formK1s"] = _collection(k1_ids)
        f["/writableHasK1Income"] = _bool(True)
    if est_ids:
        f["/form1041K1s"] = _collection(est_ids)
        f["/writableHasEstateTrustK1"] = _bool(True)
        # One answer for the return, which is how the dictionary asks it; the items are refused
        # above if they disagree. It governs the member route's box 6 too (measured on the pinned engine).
        est = [item for item in items if item.get("source") == "estate_trust"]
        for field, path in (("materially_participated", ESTATE_TRUST_PARTICIPATION),
                            ("fully_at_risk", ESTATE_TRUST_AT_RISK),
                            ("amount_at_risk_cents", ESTATE_TRUST_AT_RISK_AMOUNT)):
            answered = [item[field] for item in est if field in item]
            if answered:
                f[path] = (_dollar(answered[0]) if field.endswith("_cents")
                           else _bool(bool(answered[0])))


_INCOME_MAPPERS["k1s"] = _map_k1s

# Covered = the structural groups every return needs, plus exactly the income groups that have a
# mapper above. Derived, never hand-kept.
# The two mfs root booleans join the structural side: mapped (one to /spouseItemizes, one
# enforced service-side), never a stream.
# every root QUESTION the covered set carries — the per-status pairs and chains (mfs, qss)
# and the married chain owned by two statuses. Root questions, never streams: the tests that
# derive the covered INCOME set subtract this and nothing else.
ROOT_QUESTION_FIELDS = (MFS_ROOT_FIELDS | QSS_ROOT_FIELDS | MARRIED_ROOT_FIELDS | MFJ_ROOT_FIELDS
                        | EVERY_RETURN_ROOT_FIELDS | ALASKA_PFD_FIELDS
                        | ESTIMATED_PAYMENTS_FIELDS | STUDENT_LOAN_FIELDS
                        | frozenset({LUMP_SUM_FIELD})
                        | SOLE_TRADER_FIELDS
                        | PTC_ROOT_FIELDS | DCB_ROOT_FIELDS
                        | frozenset(WORKSHEET_A_FIELDS)
                        | SAVERS_ROOT_FIELDS | HSA_ROOT_FIELDS
                        | COMBAT_ROOT_FIELDS
                        | ALIMONY_FIELDS
                        | ROYALTY_ROOT_FIELDS
                        | MAIN_HOME_FIELDS)
COVERED_FACT_GROUPS = (frozenset({"filing_status", "persons"}) | ROOT_QUESTION_FIELDS
                       | frozenset(_INCOME_MAPPERS))
