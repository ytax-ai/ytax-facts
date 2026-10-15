# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""What the service still needs, and which line each missing figure would have built.

Spec item 4 — the gap-list spike. **Nothing here is published.** A `prepare_return` operation in
`schema/operations/` would land in the OpenAPI document, the MCP tool defs and the size budget, and
would freeze by accident the very contract the design says to freeze last and only after exercising.
This module exists to exercise it.

DERIVED, NOT DECLARED — and that is the whole design. v1 claimed gaps could be derived from the
engine's dependency graph; withdrawn, because the pinned runner discards `Result.Incomplete`. What
replaced it was a *declared* table, and a declared table is honest but drifts. So the two halves
come from what already exists:

  * WHICH inputs are required — `mapper.REQUIRED_*`, the same sets `map_to_engine` enforces, so a
    gap can never name a field the service does not actually require;
  * WHICH lines consume them — the transitive closure of `LINE_MAP`'s own `derived_from`, which is
    the provenance the service already serves.

So what the service says a line is built from, and what it asks for when that input is missing, are
one statement rather than two that can disagree.

ALL AT ONCE, not one at a time. `map_to_engine` refuses on the FIRST missing field — correct for a
refusal, wrong for a gap list, because a preparer told about one missing figure per round trip pays
a full resolve for each. `missing_required` gathers everything before returning.
"""
from __future__ import annotations

from ..facts import mapper
from .lines import F1040, LINE_MAP

# fact_path -> the line that produces it, so an input can be followed through the return.
_LINE_BY_FACT_PATH = {spec["fact_path"]: spec for spec in LINE_MAP}
_DISPLAY_ORDER = [spec["line_id"] for spec in LINE_MAP]


def consumed_by(field: str) -> list:
    """Every served line a caller-supplied field CAN reach — from the dictionary's own DAG.

    `field` is in `derived_from`'s vocabulary — `w2s[].wages_cents`, `persons[].birth_year`.

    Was a hand-written closure over `LINE_MAP`; now a lookup in the reachability artifact
   , so the answer is the pinned engine's own dependency truth rather than a
    declared list's transitive shadow. Two consequences, both deliberate: the answer carries the
    artifact's CAN-not-WILL ceiling (an edge exists; whether it moves a number on a given return
    is resolve-time), and a field with NO engine-side join — identity-plane fields, whose engine
    half is the synthesized placeholder — answers `[]` honestly rather than guessing. The
    transitive step is still the point: wages reach the overpayment through total income, AGI,
    taxable income, tax and total tax, and a direct-mentions answer would say two lines where the
    DAG says seven.
    """
    from . import reachability
    path = reachability.service_field_path(field)
    if path is None:
        return []
    reached = set(reachability.reaches(path))
    return [line_id for line_id in _DISPLAY_ORDER if line_id in reached]


def missing_required(facts: dict) -> list:
    """Every required input the caller has not supplied, as client-applicable paths.

    Reads `mapper`'s own declared sets — not a copy — so a gap can never name a field the service
    does not require, and a field made required in the schema shows up here without a second edit.
    """
    missing = []
    for field in sorted(mapper.REQUIRED_ROOT_FIELDS - set(facts)):
        missing.append(field)
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict):
            continue
        for field in sorted(mapper.REQUIRED_PERSON_FIELDS - set(person)):
            missing.append(f"persons[{i}].{field}")
    for group in sorted(mapper.REQUIRED_ITEM_FIELDS):
        for i, item in enumerate(facts.get(group) or []):
            if not isinstance(item, dict):
                continue
            for field in sorted(mapper.REQUIRED_ITEM_FIELDS[group] - set(item)):
                missing.append(f"{group}[{i}].{field}")
    return missing


def _provenance_name(path: str) -> str:
    """`w2s[0].wages_cents` -> `w2s[].wages_cents`, the vocabulary `derived_from` speaks.

    Collection indices are per-request; provenance is about the SHAPE of the return, so the index is
    dropped rather than matched."""
    import re
    return re.sub(r"\[\d+\]", "[]", path)


# Optional inputs that still MOVE A SERVED LINE, with what the service does when they are absent.
# Three exist today, and `consumed_by` identifies them rather than a hand-kept list: an optional
# field named in `LINE_MAP.derived_from` is by definition one whose absence changes a number.

# The rule this enforces is work item 0b's, on the side the schema cannot reach. `wages_cents` is
# required, so absence is refused. `withholding_cents` is optional (by design: keep it optional,
# and let the component that reads the W-2 reflect the paper) — so absence cannot be
# refused, and the only honest alternative is to SAY it. An explicit `0` is an answer and says
# nothing; absence is not an answer and says so.
_ABSENT_MEANS = {
    # Each names the FIELD a caller can set, not just the concept: an assumption you cannot act on
    # is only slightly better than one you were never told.
    "w2s[].withholding_cents":
        "{where}.withholding_cents (W-2 box 2, federal income tax withheld) was not supplied, so "
        "it was computed as zero",
    # Box 5 is optional and the mapper defaults it to box 1 — which is right for the
    # ordinary W-2 and WRONG the moment they differ, because box 5 is what Form 8959 taxes. An
    # explicit box 5 equal to box 1 says so; an absent one is not an answer, so it is stated.
    # Box 10 blank is the ordinary W-2 — no dependent care benefits from that employer.
    "w2s[].dependent_care_benefits_cents":
        "{where}.dependent_care_benefits_cents (W-2 box 10, dependent care benefits) was not "
        "supplied, so it was computed as zero — no benefits from this employer reach Form 2441 "
        "Part III",
    # Box 12 blank is the ordinary W-2 — the four Schedule 2 line 13 codes, one each; the
    # other twenty-six codes reach no served line, or are refused before the engine.
    "w2s[].box12_a_cents":
        "{where}.box12_a_cents (W-2 box 12, code A — uncollected social security or RRTA tax on tips) was not "
        "supplied, so it was computed as zero — nothing from it reaches Schedule 2 line 13",
    "w2s[].box12_b_cents":
        "{where}.box12_b_cents (W-2 box 12, code B — uncollected Medicare tax on tips) was not "
        "supplied, so it was computed as zero — nothing from it reaches Schedule 2 line 13",
    "w2s[].box12_m_cents":
        "{where}.box12_m_cents (W-2 box 12, code M — uncollected social security or RRTA tax on taxable cost of group-term life insurance over $50,000) was not "
        "supplied, so it was computed as zero — nothing from it reaches Schedule 2 line 13",
    "w2s[].box12_n_cents":
        "{where}.box12_n_cents (W-2 box 12, code N — uncollected Medicare tax on taxable cost of group-term life insurance over $50,000) was not "
        "supplied, so it was computed as zero — nothing from it reaches Schedule 2 line 13",
    # The eight retirement-deferral codes, Form 8880 line 2 — blank is the ordinary W-2.
    "w2s[].box12_d_cents":
        "{where}.box12_d_cents (W-2 box 12, code D — elective deferrals under a section 401(k) plan) was not "
        "supplied, so it was computed as zero — nothing from it reaches Form 8880 line 2",
    "w2s[].box12_e_cents":
        "{where}.box12_e_cents (W-2 box 12, code E — elective deferrals under a section 403(b) agreement) was not "
        "supplied, so it was computed as zero — nothing from it reaches Form 8880 line 2",
    "w2s[].box12_g_cents":
        "{where}.box12_g_cents (W-2 box 12, code G — deferrals and employer contributions to a section 457(b) plan) was not "
        "supplied, so it was computed as zero — nothing from it reaches Form 8880 line 2",
    "w2s[].box12_h_cents":
        "{where}.box12_h_cents (W-2 box 12, code H — elective deferrals to a section 501(c)(18)(D) plan) was not "
        "supplied, so it was computed as zero — nothing from it reaches Form 8880 line 2",
    "w2s[].box12_s_cents":
        "{where}.box12_s_cents (W-2 box 12, code S — salary reduction contributions under a section 408(p) SIMPLE plan) was not "
        "supplied, so it was computed as zero — nothing from it reaches Form 8880 line 2",
    "w2s[].box12_aa_cents":
        "{where}.box12_aa_cents (W-2 box 12, code AA — designated Roth contributions under a section 401(k) plan) was not "
        "supplied, so it was computed as zero — nothing from it reaches Form 8880 line 2",
    "w2s[].box12_bb_cents":
        "{where}.box12_bb_cents (W-2 box 12, code BB — designated Roth contributions under a section 403(b) plan) was not "
        "supplied, so it was computed as zero — nothing from it reaches Form 8880 line 2",
    "w2s[].box12_ee_cents":
        "{where}.box12_ee_cents (W-2 box 12, code EE — designated Roth contributions under a governmental section 457(b) plan) was not "
        "supplied, so it was computed as zero — nothing from it reaches Form 8880 line 2",
    "w2s[].medicare_wages_cents":
        "{where}.medicare_wages_cents (W-2 box 5, Medicare wages and tips) was not supplied, so "
        "box 1 wages were used in its place — which is the figure the Additional Medicare Tax on "
        "Form 8959 is computed from",
    # Box 6 blank is the ordinary W-2 for most filers — Additional Medicare Tax withholding
    # only exists once an employer withheld above the regular 1.45% rate. An explicit box 6 says
    # so; an absent one is not an answer, so it is stated (Form 8959 line 24, Form 1040 25d/33).
    "w2s[].medicare_withheld_cents":
        "{where}.medicare_withheld_cents (W-2 box 6, Medicare tax withheld) was not supplied, so "
        "it was computed as zero — nothing from it reaches Form 8959's Additional Medicare Tax "
        "withholding line",
    "persons[].birth_month":
        "{where}.birth_month was not supplied, so January was used — which decides whether the "
        "age-65 additional standard deduction applies, and for a dependent it sets the "
        "synthesized date of birth the age tests read",
    # The W-2G's box 4 is optional for the same reason the W-2's box 2 is — blank is an
    # ordinary state of that box — so it earns the same treatment: sent as zero, and SAID. The rule
    # this file states is not W-2-shaped, and a stream that met it and was left out would be the
    # silent half of the precedent rather than the whole of it.
    "w2gs[].federal_withholding_cents":
        "{where}.federal_withholding_cents (W-2G box 4, federal income tax withheld) was not "
        "supplied, so it was computed as zero",
    # the benefit statement's withholding box, the same posture.
    "ssa1099s[].federal_withholding_cents":
        "{where}.federal_withholding_cents (the benefit statement's federal income tax withheld "
        "box — SSA-1099 box 6, RRB-1099 box 10) was not supplied, so it was computed as zero",
    # Form 1099-G's withholding box and the Schedule 1 line 7 same-year repayment, the
    # same posture — a blank box 4 is ordinary, and most filers repaid nothing.
    "g1099s[].federal_withholding_cents":
        "{where}.federal_withholding_cents (Form 1099-G box 4, federal income tax withheld) was "
        "not supplied, so it was computed as zero",
    "g1099s[].repaid_cents":
        "{where}.repaid_cents (unemployment compensation received and repaid in the same year, "
        "the Schedule 1, line 7 repayment) was not supplied, so it was computed as zero",
    # Form 1099-MISC's withholding box, the same posture.
    "misc1099s[].federal_withholding_cents":
        "{where}.federal_withholding_cents (Form 1099-MISC box 4, federal income tax withheld) "
        "was not supplied, so it was computed as zero",
    # box 2 of every 1099-MISC is summed into the one return-level royalty activity;
    # absent on any one form, it contributes nothing to that sum.
    "misc1099s[].royalties_cents":
        "{where}.royalties_cents (Form 1099-MISC box 2, royalties) was not supplied, so it was "
        "computed as zero",
    "royalty_expenses_cents":
        "royalty_expenses_cents was not supplied — it is asked once the return claims royalty "
        "income (a Form 1099-MISC box 2 above zero), and the return stops with that question "
        "rather than crediting no expenses (Schedule E line 20)",
    "royalty_is_oil_gas_geothermal":
        "royalty_is_oil_gas_geothermal was not supplied, so no percentage depletion is taken "
        "against the royalty income — the property is treated as not oil, gas, or geothermal "
        "(Schedule E line 18)",
    # 1099-INT: all four boxes are optional because a real form can carry any
    # subset — box 1 excludes box 3 by the form's own instruction, so a savings-bond-only
    # 1099-INT has a legitimately blank box 1. Each absence is a statement, not a default.
    "int1099s[].interest_cents":
        "{where}.interest_cents (1099-INT box 1, interest income) was not supplied, so it was "
        "computed as zero",
    "int1099s[].government_interest_cents":
        "{where}.government_interest_cents (1099-INT box 3, interest on U.S. Savings Bonds and "
        "Treasury obligations) was not supplied, so it was computed as zero",
    "int1099s[].tax_exempt_interest_cents":
        "{where}.tax_exempt_interest_cents (1099-INT box 8, tax-exempt interest) was not "
        "supplied, so it was computed as zero",
    "int1099s[].federal_withholding_cents":
        "{where}.federal_withholding_cents (1099-INT box 4, federal income tax withheld) was "
        "not supplied, so it was computed as zero",
    # Form 1099-OID: nine optional amounts — a form carries any subset of its boxes, and each
    # absence is a statement, not a default. (The mapper SENDS every one as zero: the engine drops
    # an item whose box 2 or box 11 is unsent, measured on the pinned engine.)
    "oid1099s[].original_issue_discount_cents":
        "{where}.original_issue_discount_cents (1099-OID box 1, original issue discount) was not supplied, so it was "
        "computed as zero",
    "oid1099s[].other_periodic_interest_cents":
        "{where}.other_periodic_interest_cents (1099-OID box 2, other periodic interest) was not supplied, so it was "
        "computed as zero",
    "oid1099s[].early_withdrawal_penalty_cents":
        "{where}.early_withdrawal_penalty_cents (1099-OID box 3, early withdrawal penalty) was not supplied, so it was "
        "computed as zero",
    "oid1099s[].federal_withholding_cents":
        "{where}.federal_withholding_cents (1099-OID box 4, federal income tax withheld) was not supplied, so it was "
        "computed as zero",
    "oid1099s[].market_discount_cents":
        "{where}.market_discount_cents (1099-OID box 5, market discount) was not supplied, so it was "
        "computed as zero",
    "oid1099s[].acquisition_premium_cents":
        "{where}.acquisition_premium_cents (1099-OID box 6, acquisition premium) was not supplied, so it was "
        "computed as zero",
    "oid1099s[].treasury_oid_cents":
        "{where}.treasury_oid_cents (1099-OID box 8, original issue discount on U.S. Treasury "
        "obligations) was not supplied, so it was computed as zero",
    "oid1099s[].bond_premium_cents":
        "{where}.bond_premium_cents (1099-OID box 10, bond premium) was not supplied, so it was "
        "computed as zero",
    "oid1099s[].tax_exempt_oid_cents":
        "{where}.tax_exempt_oid_cents (1099-OID box 11, tax-exempt OID) was not supplied, so it "
        "was computed as zero",
    # The one thing Form 1099-OID does not print, asked, never assumed.
    "oid1099s[].box2_is_tax_exempt":
        "{where}.box2_is_tax_exempt was not supplied — it is asked on a Form 1099-OID with an "
        "amount in box 2 and none in box 11, and the return stops with that question rather than "
        "assuming the interest is taxable",
    # Form 1099-INT boxes 2 and 9-13: sent only when supplied; an unsent one is none.
    **{f"int1099s[].{field}":
       f"{{where}}.{field} (1099-INT box {box}, {caption}) was not supplied, so it was taken as none"
       for field, box, caption in (
           ("early_withdrawal_penalty_cents", 2, "early withdrawal penalty"),
           ("market_discount_cents", 10, "market discount"),
           ("bond_premium_cents", 11, "bond premium"),
           ("treasury_bond_premium_cents", 12, "bond premium on Treasury obligations"))},
    # (Boxes 9 and 13 carry no statement: measured, neither moves a served line on its own — box
    # 9 is an AMT preference, box 13 reduces the tax-exempt interest on line 2a.)
    # Form 1099-B: each absence a statement. Box 2 is the stops-with-the-question kind only
    # where a date is missing (`mapper.b1099_term_question_reached`); with both dates the
    # dictionary works the holding period out itself.
    "b1099s[].date_acquired":
        "{where}.date_acquired (1099-B box 1b) was not supplied, so the holding period is the "
        "box 2 answer",
    "b1099s[].date_sold":
        "{where}.date_sold (1099-B box 1c) was not supplied, so the holding period is the box 2 "
        "answer",
    "b1099s[].term":
        "{where}.term (1099-B box 2) was not supplied — the holding period was worked out from "
        "the dates in boxes 1b and 1c",
    "b1099s[].wash_sale_loss_disallowed_cents":
        "{where}.wash_sale_loss_disallowed_cents (1099-B box 1g) was not supplied, so no wash "
        "sale adjustment was made",
    # The refused boxes (1f, 3, 4, 7) carry no statement: they reach no served line, and an
    # absent one is simply a form without that mark or figure.
    # 1099-DIV: seven optional amounts, each absence a statement.
    "div1099s[].ordinary_dividends_cents":
        "{where}.ordinary_dividends_cents (1099-DIV box 1a, total ordinary dividends) was not "
        "supplied, so it was computed as zero",
    "div1099s[].qualified_dividends_cents":
        "{where}.qualified_dividends_cents (1099-DIV box 1b, qualified dividends) was not "
        "supplied, so it was computed as zero — ordinary rates were applied",
    "div1099s[].capital_gain_distributions_cents":
        "{where}.capital_gain_distributions_cents (1099-DIV box 2a, total capital gain "
        "distributions) was not supplied, so it was computed as zero",
    "div1099s[].unrecaptured_1250_gain_cents":
        "{where}.unrecaptured_1250_gain_cents (1099-DIV box 2b, unrecaptured section 1250 gain) "
        "was not supplied, so it was computed as zero",
    "div1099s[].federal_withholding_cents":
        "{where}.federal_withholding_cents (1099-DIV box 4, federal income tax withheld) was "
        "not supplied, so it was computed as zero",
    "div1099s[].section_199a_dividends_cents":
        "{where}.section_199a_dividends_cents (1099-DIV box 5, section 199A dividends) was not "
        "supplied, so it was computed as zero — no qualified business income deduction was "
        "claimed for it",
    "div1099s[].exempt_interest_dividends_cents":
        "{where}.exempt_interest_dividends_cents (1099-DIV box 12, exempt-interest dividends) "
        "was not supplied, so it was computed as zero",
    # 1099-R. Box 2a's absence is the one statement in this table that does NOT
    # mean zero: the return knocks out instead, and the sentence says so.
    "r1099s[].taxable_amount_cents":
        "{where}.taxable_amount_cents (1099-R box 2a, taxable amount) was not supplied — the "
        "return stops rather than guessing, because determining a taxable amount the payer did "
        "not state is not this service's to do",
    # the qualified HSA funding distribution on an IRA 1099-R, behind the filer's yes.
    "r1099s[].qualified_hsa_funding_distribution_cents":
        "{where}.qualified_hsa_funding_distribution_cents was not supplied — it is asked on each "
        "IRA Form 1099-R of a filer who answered yes to the qualified HSA funding distribution "
        "question (Form 8889 line 10), and the return stops with that question rather than "
        "assuming an amount",
    "persons[].hsa_prior_funding_distribution_election":
        "{where}.hsa_prior_funding_distribution_election was not supplied — it is asked once a "
        "Form 1099-R carries a qualified HSA funding distribution (the election can be made once "
        "in a lifetime), and the return stops with that question rather than assuming an answer",
    # the testing-period month, where a part-year filer's transfer opened one.
    "persons[].hsa_testing_period_first_ineligible_month":
        "{where}.hsa_testing_period_first_ineligible_month was not supplied — it is asked once a "
        "filer with an IRA-to-HSA transfer reports high deductible health plan coverage for part "
        "of the year (Form 8889 Part III, the testing period), and the return stops with that "
        "question rather than assuming the period was kept",
    # the qualified charitable distribution on an IRA 1099-R, its split-interest answer,
    # and the filer's post-70½ deduction history.
    "r1099s[].qualified_charitable_distribution_cents":
        "{where}.qualified_charitable_distribution_cents was not supplied — it is asked on each "
        "IRA Form 1099-R reported as fully taxable whose recipient was born through 1953 (Form "
        "1040 line 4b), and the return stops with that question rather than assuming an amount",
    "r1099s[].qcd_to_split_interest_entity":
        "{where}.qcd_to_split_interest_entity was not supplied — it is asked behind a qualified "
        "charitable distribution (the one-time split-interest election), and the return stops "
        "with that question rather than assuming an answer",
    "persons[].qcd_prior_deducted_ira_contributions_cents":
        "{where}.qcd_prior_deducted_ira_contributions_cents was not supplied — it is asked once a "
        "Form 1099-R of this filer carries a qualified charitable distribution (Pub 590-B Appendix "
        "D line 1), and the return stops with that question rather than assuming an amount",
    # the funding distribution's transfer month, above the line 8 base limitation.
    "persons[].hsa_funding_distribution_transfer_month":
        "{where}.hsa_funding_distribution_transfer_month was not supplied — it is asked once a "
        "filer's qualified HSA funding distribution is above the Form 8889 line 8 base limitation "
        "or beside an asked coverage vector with any transfer (the month decides the exclusion "
        "cap), and the return stops with that question rather "
        "than assuming a month",
    # the twelve coverage months, prefilled where the all-year answer says them all —
    # every month named in provenance is stated (the gaps lock); served once, on January.
    **{f"persons[].hsa_coverage_{m}":
        f"{{where}}.hsa_coverage_{m} was not supplied — the twelve coverage months of Form 8889 "
        f"line 3 (January through December) are asked once a filer's high deductible health plan "
        f"coverage ran for part of the year, or gave both self-only and family coverage, and the "
        f"return stops with that question; on a filer covered all year by one type or not at all, "
        f"the month is taken to carry that answer"
       for m in ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")},
    # the indirect rollover and, on an IRA form, the one-rollover-per-year answer.
    "r1099s[].rolled_over_cents":
        "{where}.rolled_over_cents was not supplied — it is asked on each Form 1099-R reported as "
        "fully taxable (Form 1040 line 4b or 5b), and the return stops with that question rather "
        "than assuming no rollover",
    "r1099s[].ira_one_rollover_per_year":
        "{where}.ira_one_rollover_per_year was not supplied — it is asked behind a rolled-over "
        "amount on an IRA Form 1099-R (the one-rollover-per-year rule), and the return stops with "
        "that question rather than assuming an answer",
    # the code-3 disability form's minimum-retirement-age answer, asked, never assumed.
    "r1099s[].reached_minimum_retirement_age":
        "{where}.reached_minimum_retirement_age was not supplied — it is asked on each Form 1099-R "
        "whose box 7 code is 3 (disability) without the IRA/SEP/SIMPLE box, and the return stops "
        "with that question rather than assuming an answer (Form 1040 line 1h)",
    # the public-safety-officer chain — each link asked, never assumed.
    "r1099s[].public_safety_officer":
        "{where}.public_safety_officer was not supplied — it is asked on each pension Form 1099-R "
        "with a box 7 code of 2 or 7 (not an IRA), and the return stops with that question rather "
        "than assuming the person is not a retired public safety officer (IRC 402(l), Form 1040 line 5b)",
    "r1099s[].pso_premiums_paid_by_plan":
        "{where}.pso_premiums_paid_by_plan was not supplied — it is asked once the person answers yes "
        "to being an eligible retired public safety officer, and the return stops with that question "
        "rather than assuming an answer",
    "r1099s[].pso_premiums_cents":
        "{where}.pso_premiums_cents was not supplied — it is asked once the plan is answered to have "
        "paid the premiums, and the return stops with that question rather than excluding nothing",
    # the death-benefit chain — box 13 stated where blank on a code 4 form; each link asked.
    "r1099s[].date_of_payment":
        "{where}.date_of_payment (Form 1099-R box 13, date of payment) was not supplied — on a box 7 "
        "code C form the return stops with that question; on a code 4 form box 13 is taken as blank, "
        "so the distribution is taxed as box 2a reports and no death-benefit question (IRC 101, Form "
        "1040 line 5b) is asked",
    "r1099s[].box1_is_death_benefit_under_contract":
        "{where}.box1_is_death_benefit_under_contract was not supplied — it is asked on a code 4 form "
        "with a date in box 13, and the return stops with that question rather than assuming whether "
        "box 1 is the death benefit under that contract",
    "r1099s[].acquired_in_reportable_policy_sale":
        "{where}.acquired_in_reportable_policy_sale was not supplied — it is asked on a form with a date "
        "in box 13, and the return stops with that question rather than assuming how the policy was acquired",
    "r1099s[].acquired_for_valuable_consideration":
        "{where}.acquired_for_valuable_consideration was not supplied — it is asked once the policy is "
        "answered not to have been acquired in a reportable policy sale, and the return stops with that question",
    "r1099s[].transfer_has_carryover_basis":
        "{where}.transfer_has_carryover_basis was not supplied — it is asked once the policy is answered "
        "to have been transferred for valuable consideration, and the return stops with that question",
    "r1099s[].transfer_to_insured_or_related_party":
        "{where}.transfer_to_insured_or_related_party was not supplied — it is asked once the policy is "
        "answered to have been transferred for valuable consideration, and the return stops with that question",
    "r1099s[].death_benefit_basis_cents":
        "{where}.death_benefit_basis_cents was not supplied — it is asked behind a reportable policy sale, "
        "or behind a transfer for valuable consideration with neither carve-out, and the return stops with "
        "that question rather than taxing the whole payment",
    "r1099s[].federal_withholding_cents":
        "{where}.federal_withholding_cents (1099-R box 4, federal income tax withheld) was not "
        "supplied, so it was computed as zero",
    # Schedule C: three optional amounts, each absence a statement. Line G and
    # box 32a are NOT here — on a loss they are questions (`gaps_for` below), never defaults.
    "schedule_c[].returns_and_allowances_cents":
        "{where}.returns_and_allowances_cents (Schedule C line 2, returns and allowances) was "
        "not supplied, so it was computed as zero",
    "schedule_c[].cost_of_goods_sold_cents":
        "{where}.cost_of_goods_sold_cents (Schedule C line 4, cost of goods sold) was not "
        "supplied, so it was computed as zero",
    "schedule_c[].other_business_income_cents":
        "{where}.other_business_income_cents (Schedule C line 6, other income) was not "
        "supplied, so it was computed as zero",
    # the same population sentence in this stream's words. Line G and box 32a stay out
    # of this table (on a loss they are questions, never defaults); the amount behind box 32b
    # is a question too, and says so.
    "schedule_c[].amount_at_risk_cents":
        "{where}.amount_at_risk_cents was not supplied — the simplified Form 6198 amount at "
        "risk is asked whenever a business with a line 31 loss checks box 32b, and the return "
        "stops with that question rather than capping the loss at a figure nobody gave",
    # Rentals.
    "rentals[].total_expenses_cents":
        "{where}.total_expenses_cents (Schedule E line 20, total expenses) was not supplied, "
        "so it was computed as zero",
    "rentals[].prior_year_unallowed_loss_cents":
        "{where}.prior_year_unallowed_loss_cents (Form 8582 Part IV column (c), prior years' "
        "unallowed losses) was not supplied, so no prior-year unallowed loss was carried in",
    # the four itemized expense lines — each now sometimes a real supplied figure and
    # sometimes an unasked zero on the SAME emitted engine path (`mapper.ASSUMED_ABOUT_TAXPAYER`
    # cannot say "sometimes", so these moved here instead of staying a universal assumption).
    "rentals[].insurance_cents":
        "{where}.insurance_cents (Schedule E line 9, insurance) was not supplied, so it was "
        "computed as zero",
    "rentals[].management_fees_cents":
        "{where}.management_fees_cents (Schedule E line 11, management fees) was not "
        "supplied, so it was computed as zero",
    "rentals[].repairs_cents":
        "{where}.repairs_cents (Schedule E line 14, repairs) was not supplied, so it was "
        "computed as zero",
    "rentals[].taxes_cents":
        "{where}.taxes_cents (Schedule E line 16, taxes) was not supplied, so it was computed "
        "as zero",
    # the depreciation inputs. Absence here is NOT zero in the usual sense — no basis
    # supplied means no building depreciation is claimed for the property at all (Schedule E
    # line 18, via Form 4562 Part III), not that a supplied basis was treated as 0.
    "rentals[].building_basis_cents":
        "{where}.building_basis_cents was not supplied, so no building depreciation is "
        "claimed for this property (Schedule E line 18, via Form 4562 Part III)",
    "rentals[].placed_in_service_in_current_year":
        "{where}.placed_in_service_in_current_year was not supplied, so this property's "
        "building, if any, was treated as placed in service in a prior year (a full "
        "straight-line recovery year, Form 4562 Part III)",
    "rentals[].has_five_year_property":
        "{where}.has_five_year_property was not supplied, so no 5-year MACRS personal "
        "property (an appliance, carpeting, or furniture) is claimed for this property "
        "(Form 4562 Part III line 19b)",
    # the depreciation-input pairs carry the loss-gate pair's shape — armed on ONE
    # population, the only place they may be answered at all, and the return stops with the
    # question there rather than assuming an answer.
    "rentals[].is_nonresidential_real_property":
        "{where}.is_nonresidential_real_property was not supplied — it is asked whenever a "
        "building's depreciable basis is entered and positive, and the return stops with "
        "that question rather than assuming a class; this rental has no such basis",
    "rentals[].building_uses_standard_gds":
        "{where}.building_uses_standard_gds was not supplied — it is asked whenever a "
        "building's depreciable basis is entered and positive, and the return stops with "
        "that question rather than assuming a recovery period; this rental has no such basis",
    "rentals[].placed_in_service_month":
        "{where}.placed_in_service_month was not supplied — it is asked whenever the "
        "property's building was placed in service this year, and the return stops with "
        "that question rather than assuming a month; this rental's building was not placed "
        "in service this year",
    "rentals[].five_year_property_basis_cents":
        "{where}.five_year_property_basis_cents was not supplied — it is asked whenever this "
        "property claims a 5-year MACRS personal-property item, and the return stops with "
        "that question rather than assuming a basis; this rental claims no such item",
    # line 1b's type of property stopped being record-only in this service the moment the
    # code derived the self-rental treatment, so its ABSENCE decides a number and has to say so.
    # ARMED on a profit (`_self_rental_code_could_decide` below): on a loss the code is record
    # only again, because a self-rental LOSS is never recharacterized (measured) — the sentence
    # would be true and idle, which is the must-not-become-noise case.
    "rentals[].property_type":
        "{where}.property_type (Schedule E line 1b, type of property) was not supplied, so the "
        "property was treated as an ordinary rental and not as a self-rental — a self-rental's "
        "profit can be moved out of the passive pool, and this one was not",
    # The rentals loss-gate pair: like 1099-R box 2a, absence here is NOT zero. On a loss the
    # return stops with the question (a gap) rather than assuming an answer; a computed return
    # carrying either statement therefore had no loss that needed it.
    "rentals[].active_participation":
        "{where}.active_participation was not supplied — it is asked whenever the rental's "
        "net, after any prior years' unallowed loss, is a loss, and the return stops with "
        "that question rather than assuming an answer; this return's rental had no such loss",
    "rentals[].active_participation_when_loss_arose":
        "{where}.active_participation_when_loss_arose was not supplied — it is asked whenever a "
        "prior years' unallowed loss above zero is entered on a rental with active "
        "participation, and the return stops with that question rather than assuming where "
        "the loss goes on Form 8582; this rental carried in no such loss",
    # the lead's review: box 32a earns the sentence its two sibling booleans already
    # have. Same shape and same reason they carry — the question is asked on a loss and the
    # return stops there, so an ABSENT answer can only be a business with no loss, which the
    # sentence says rather than leaving the reader to infer.
    "schedule_c[].all_investment_at_risk":
        "{where}.all_investment_at_risk (Schedule C box 32) was not supplied — it is asked "
        "whenever the business's line 31 is a loss, and the return stops with that question "
        "rather than assuming an answer; this business had no such loss",
    "rentals[].fully_at_risk":
        "{where}.fully_at_risk was not supplied — it is asked whenever the rental's year is a "
        "loss, and the return stops with that question rather than assuming an answer; this "
        "return's rental had no such loss",
    # armed on ONE population — a rental whose year is a loss and whose at-risk answer
    # is present and FALSE (`_at_risk_amount_armed` below) — the only place it may be answered
    # at all. Stops-with-the-question, like the loss-gate pair above it: unanswered, the
    # dictionary's own deductible loss is Incomplete and no served line resolves, so the
    # service asks first and the mapper backstop refuses the request by name.
    "rentals[].amount_at_risk_cents":
        "{where}.amount_at_risk_cents was not supplied — the simplified Form 6198 amount at "
        "risk is asked whenever a rental with a loss for the year is not fully at risk, and "
        "the return stops with that question rather than capping the loss at a figure nobody "
        "gave",
    # armed on ONE population — a property whose Schedule E line 1b type is 7
    # (`_self_rental_lessee_armed` below), the only place the answer may be given at all. On a
    # self-rental whose year is a PROFIT the return stops with the question, so a computed return
    # carrying this statement can only be a self-rental with no such profit, which the sentence
    # says rather than leaving the reader to infer.
    "rentals[].materially_participates_in_lessee":
        "{where}.materially_participates_in_lessee was not supplied — it is asked whenever a "
        "self-rental's net for the year, after any prior years' unallowed loss, is a profit, "
        "and the return stops with that question rather than assuming an answer; this "
        "self-rental had no such profit, and a self-rental loss is never recharacterized",
    # K-1s. The amount boxes: absence sends nothing — a blank box reports
    # nothing, and the engine computes no income from it. The conditional questions carry the
    # rentals-pair shape: on the arming condition the return stops with the question.
    "k1s[].ordinary_business_income_cents":
        "{where}.ordinary_business_income_cents (ordinary business income or loss) was not "
        "supplied, so it was sent as zero — a blank box 1 reports no ordinary business income "
        "(on a partnership or S corporation K-1 the engine needs the box answered to finish "
        "the return; an estate or trust K-1's blank box 6 sends nothing)",
    "k1s[].interest_income_cents":
        "{where}.interest_income_cents (interest income) was not supplied, so nothing was "
        "sent for it — a blank box reports nothing",
    "k1s[].dividend_income_cents":
        "{where}.dividend_income_cents (ordinary dividends) was not supplied, so nothing was "
        "sent for it — a blank box reports nothing",
    "k1s[].qualified_dividends_cents":
        "{where}.qualified_dividends_cents (qualified dividends) was not supplied, so it was "
        "computed as zero — ordinary rates were applied",
    "k1s[].royalties_cents":
        "{where}.royalties_cents (royalties) was not supplied, so nothing was sent for it — "
        "a blank box reports nothing",
    "k1s[].se_earnings_cents":
        "{where}.se_earnings_cents (self-employment earnings, box 14 code A) was not "
        "supplied, so nothing was sent for it — a blank box 14 on a K-1 reporting no "
        "guaranteed payment is the partnership reporting no self-employment earnings, and no "
        "self-employment tax was computed from this K-1 (with a guaranteed payment it is asked "
        "instead, and the return stops with that question)",
    "k1s[].publicly_traded_partnership":
        "{where}.publicly_traded_partnership was not supplied — item D is asked on every "
        "partnership K-1, and the return stops with that question rather than assuming an "
        "answer; this K-1 is not a partnership one",
    "k1s[].materially_participated":
        "{where}.materially_participated was not supplied — it is asked whenever box 1 is a "
        "loss, and the return stops with that question rather than assuming an answer; this "
        "K-1 had no such loss",
    "k1s[].basis_cents":
        "{where}.basis_cents was not supplied — it is asked whenever box 1 is a loss, and "
        "the return stops with that question rather than assuming an answer; this K-1 had no "
        "such loss",
    "k1s[].fully_at_risk":
        "{where}.fully_at_risk was not supplied — it is asked whenever box 1 is a loss, and "
        "the return stops with that question rather than assuming an answer; this K-1 had no "
        "such loss",
    # the same population sentence in this stream's words.
    "k1s[].amount_at_risk_cents":
        "{where}.amount_at_risk_cents was not supplied — the simplified Form 6198 amount at "
        "risk is asked whenever a K-1 with a box 1 loss is not fully at risk, and the return "
        "stops with that question rather than capping the loss at a figure nobody gave",
    # the guaranteed-payments pair (a blank box reports nothing) and item G (asked on
    # every partnership K-1, the stops-with-the-question pattern).
    "k1s[].guaranteed_payments_services_cents":
        "{where}.guaranteed_payments_services_cents (guaranteed payments for services, box 4a) "
        "was not supplied, so nothing was sent for it — a blank box reports nothing",
    "k1s[].guaranteed_payments_capital_cents":
        "{where}.guaranteed_payments_capital_cents (guaranteed payments for capital, box 4b) "
        "was not supplied, so nothing was sent for it — a blank box reports nothing",
    "k1s[].general_partner":
        "{where}.general_partner was not supplied — item G is asked on every partnership "
        "K-1, and the return stops with that question rather than assuming an answer; this "
        "K-1 is not a partnership one",
    # box 20 code Z. All three are armed on ONE population — a partnership K-1 whose
    # item D is checked — because that is the only place any of them may be answered at all
    # (`_PTP_CODE_Z_ARMED` below); a statement about a field the service would have refused
    # is noise. The amount is the stops-with-the-question kind; the other two are sent-as-
    # nothing kinds, and each says what the engine then does.
    "k1s[].qualified_ptp_income_cents":
        "{where}.qualified_ptp_income_cents (box 20 code Z, the section 199A statement) was "
        "not supplied — it is asked on every K-1 whose item D is checked, and the return "
        "stops with that question rather than treating the statement as reporting nothing",
    # The SSTB flag was turned from an OPTIONAL input (absence sent as nothing, stated) into
    # an ASKED one, so its sentence became the amount's kind: stops-with-the-question, never a
    # default. It stays in this table rather than leaving it because the lock that derives the
    # optional set reads `REQUIRED_ITEM_FIELDS`, which cannot express "required once item D is
    # checked" — exactly why `qualified_ptp_income_cents`, required on the same population
    # since sits here too. In a served response neither ever appears: the mapper
    # backstop refuses the request by name first.
    "k1s[].qualified_ptp_is_sstb":
        "{where}.qualified_ptp_is_sstb was not supplied — it is asked on every K-1 whose item "
        "D is checked, and the return stops with that question rather than treating the "
        "partnership as not a specified service trade or business",
    "k1s[].ptp_prior_year_unallowed_loss_cents":
        "{where}.ptp_prior_year_unallowed_loss_cents was not supplied, so nothing was sent "
        "for it — no prior-year unallowed loss from this publicly traded partnership",
    # the stops-with-the-question kind, armed on the K-1s whose box 1 business income a
    # section 199A statement is asked (`mapper.section_199a_asked`).
    "k1s[].section_199a_qbi_cents":
        "{where}.section_199a_qbi_cents (the section 199A statement's qualified business "
        "income) was not supplied — it is asked on every partnership or S corporation K-1 "
        "whose box 1 reports business income, and the return stops with that question rather "
        "than treating the statement as reporting none",
    # armed on ONE population — a Form 1065 K-1 whose box 14 code A is answered and
    # NEGATIVE (`_deductible_se_loss_armed` below), the only place it may be answered at all.
    # Stops-with-the-question, like the code Z amount: unanswered, the dictionary's own
    # per-item allowance is Incomplete and the return refuses, so the service asks first and
    # the mapper backstop refuses the request by name — in a served response this never appears.
    "k1s[].deductible_se_loss_cents":
        "{where}.deductible_se_loss_cents was not supplied — the deductible part of a box 14 "
        "code A loss is asked on every K-1 that reports one, and the return stops with that "
        "question rather than entering the whole printed loss on Schedule SE",
    # Dependents: the asked qualifiers carry the stops-with-the-question
    # pattern — on a dependent row each is a gap, never a default.
    "persons[].relationship":
        "{where}.relationship was not supplied — it is asked on every claimed dependent, "
        "and the return stops with that question rather than assuming an answer",
    "persons[].months_in_home":
        "{where}.months_in_home was not supplied — it is asked on every claimed dependent, "
        "and the return stops with that question rather than assuming an answer",
    "persons[].is_married":
        "{where}.is_married was not supplied — it is asked on every claimed dependent, and "
        "the return stops with that question rather than assuming an answer",
    "persons[].provided_own_support":
        "{where}.provided_own_support was not supplied — it is asked on every claimed "
        "dependent, and the return stops with that question rather than assuming an answer",
    "persons[].gross_income_under_limit":
        "{where}.gross_income_under_limit was not supplied — it is asked on every claimed "
        "dependent, and the return stops with that question rather than assuming an answer",
    "persons[].filer_provided_over_half_support":
        "{where}.filer_provided_over_half_support was not supplied — it is asked on every "
        "claimed dependent, and the return stops with that question rather than assuming an "
        "answer",
    "persons[].could_be_qualifying_child_of_another":
        "{where}.could_be_qualifying_child_of_another was not supplied — it is asked on "
        "every claimed dependent, and the return stops with that question rather than "
        "assuming an answer",
    # the joint-return test, on a MARRIED dependent row and one link at a time — the
    # same stops-with-the-question pattern (two of the three were published attestations
    # until this unit). `mapper.dependent_joint_return_questions_reached` arms them.
    "persons[].files_joint_return_with_spouse":
        "{where}.files_joint_return_with_spouse was not supplied — it is asked on every "
        "married dependent, and the return stops with that question rather than assuming "
        "an answer",
    "persons[].required_to_file_with_spouse":
        "{where}.required_to_file_with_spouse was not supplied — it is asked of a married "
        "dependent who files a joint return, and the return stops with that question rather "
        "than assuming an answer",
    "persons[].joint_return_only_for_refund":
        "{where}.joint_return_only_for_refund was not supplied — it is asked of a married "
        "dependent whose joint return they are not required to file, and the return stops "
        "with that question rather than assuming an answer",
    # the benefit-split gate, on the filer's own biological or adopted child answered as
    # having another legal parent, and one link at a time — the same stops-with-the-question
    # pattern (the whole population was refused outright until this unit).
    # `mapper.dependent_benefit_split_questions_reached` arms them.
    "persons[].parents_situation":
        "{where}.parents_situation was not supplied — it is asked about a child with another "
        "living biological or adoptive parent, and the return stops with that question rather "
        "than assuming an answer",
    "persons[].child_in_parents_custody":
        "{where}.child_in_parents_custody was not supplied — it is asked about a child whose "
        "parents are divorced, separated or living apart, and the return stops with that "
        "question rather than assuming an answer",
    "persons[].child_lived_with_parents_over_half_year":
        "{where}.child_lived_with_parents_over_half_year was not supplied — it is asked about a "
        "child in their parents' legal custody, and the return stops with that question rather "
        "than assuming an answer",
    "persons[].parents_provided_over_half_support":
        "{where}.parents_provided_over_half_support was not supplied — it is asked about a "
        "child who lived with a parent for more than six months, and the return stops with that "
        "question rather than assuming an answer",
    "persons[].written_declaration":
        "{where}.written_declaration was not supplied — it is asked about a child whose earlier "
        "answers leave the benefit split open, and the return stops with that question rather "
        "than assuming an answer",
    # the custodial-parent questions — the same stops-with-the-question pattern.
    "persons[].nights_with_filer_vs_other_parent":
        "{where}.nights_with_filer_vs_other_parent was not supplied — it is asked once a parent "
        "has signed a declaration not to claim this child, and the return stops with that "
        "question rather than assuming an answer",
    "persons[].filer_agi_higher_than_other_parent":
        "{where}.filer_agi_higher_than_other_parent was not supplied — it is asked once the "
        "child's nights with each parent are equal, and the return stops with that question "
        "rather than assuming an answer",
    # Form 1040 line 12's blindness checkbox, per filer row — the same
    # stops-with-the-question pattern (it was an attestation, published, until this unit).
    # the page-1 "someone can claim you" chain — the same stops-with-the-question pattern.
    "persons[].someone_can_claim_you":
        "{where}.someone_can_claim_you was not supplied — the page-1 checkbox is asked on every "
        "filer row, and the return stops with that question rather than assuming an answer",
    "persons[].expect_to_be_claimed":
        "{where}.expect_to_be_claimed was not supplied — it is asked once someone can claim you, "
        "and the return stops with that question rather than assuming an answer",
    "persons[].potential_claimer_must_file":
        "{where}.potential_claimer_must_file was not supplied — it is asked once someone can "
        "claim you, and the return stops with that question rather than assuming an answer",
    "persons[].potential_claimer_filed":
        "{where}.potential_claimer_filed was not supplied — it is asked once the person who could "
        "claim you need not file, and the return stops with that question rather than assuming "
        "an answer",
    "persons[].potential_claimer_filed_only_for_refund":
        "{where}.potential_claimer_filed_only_for_refund was not supplied — it is asked once that "
        "person filed anyway, and the return stops with that question rather than assuming an "
        "answer",
    "persons[].is_blind":
        "{where}.is_blind was not supplied — the blindness checkbox is asked on every filer "
        "row, and the return stops with that question rather than assuming an answer",
    # the educator question on every filer row; the amount once that row says yes.
    "persons[].k12_educator":
        "{where}.k12_educator was not supplied — whether this person was a K-12 educator is "
        "asked on every filer row, and the return stops with that question rather than "
        "assuming an answer",
    "persons[].educator_expenses_cents":
        "{where}.educator_expenses_cents was not supplied — it is asked once that person "
        "answers yes to having been a K-12 educator, and the return stops with that question "
        "rather than assuming an amount",
    # the IRA question on every filer row; the amount and the inherited answer on a yes.
    "persons[].made_ira_contributions":
        "{where}.made_ira_contributions was not supplied — whether this person contributed to "
        "an IRA or an ABLE account is asked on every filer row, and the return stops with that "
        "question rather than assuming an answer",
    "persons[].traditional_ira_contributions_cents":
        "{where}.traditional_ira_contributions_cents was not supplied — it is asked once that "
        "person answers yes to contributing to an IRA, and the return stops with that question "
        "rather than assuming an amount",
    # the own-HSA-contribution question on every filer row, the amount behind a yes (each
    # stops with the question); the after-year-end amount optional, sent as zero and stated.
    "persons[].made_hsa_contributions":
        "{where}.made_hsa_contributions was not supplied — whether this person contributed to "
        "their health savings account themselves (Form 8889 line 2) is asked on every filer "
        "row, and the return stops with that question rather than assuming an answer",
    "persons[].hsa_own_contributions_cents":
        "{where}.hsa_own_contributions_cents was not supplied — it is asked once that person "
        "answers yes to contributing to their HSA themselves (Form 8889 line 2), and the return "
        "stops with that question rather than assuming an amount",
    "persons[].hsa_own_contributions_after_year_end_cents":
        "{where}.hsa_own_contributions_after_year_end_cents was not supplied, so it was "
        "computed as zero — no contribution made after December 31, 2025 and before the due "
        "date counts for 2025 (Form 8889 line 2)",
    # Form 5329 line 42 — the carry-in from 2024. Absent is the no the mapper once assumed
    # for every return; said on every filer row with HSA activity now.
    "persons[].hsa_prior_year_excess_cents":
        "{where}.hsa_prior_year_excess_cents was not supplied, so no excess HSA contribution was "
        "carried in from 2024 for this person — a carry-in (the 2024 Form 5329 "
        "line 48, where its line 49 was above zero) would join Form 5329 line 48 for the 6% after "
        "the room under Form 8889 line 12 absorbed it",
    # Form 5329 line 49's cap. The dictionary reads it only behind an excess on line 48, and
    # there it is mandatory: absent, a return with an excess is the dictionary's own knockout
    # (it no longer taxes the whole excess), so a completed return without it had no excess.
    "persons[].hsa_december_31_value_cents":
        "{where}.hsa_december_31_value_cents was not supplied — Form 5329 line 49 reads the value "
        "of that person's HSAs on December 31, 2025 (including 2025 contributions made in 2026) "
        "only where line 48 shows an excess HSA contribution, and a return with an excess is not "
        "figured without it",
    # the HSA 20%-tax exception amount, reached by the filer's own Forms 1099-SA.
    "persons[].hsa_exception_amount_cents":
        "{where}.hsa_exception_amount_cents was not supplied — it is asked once that person's "
        "HSA distributions exceed their qualified medical expenses, and the return stops with "
        "that question rather than assuming no exception",
    # Form 2441 line 2 column (d), on a qualifying person's row — absent means none were
    # entered for that person, and the engine is told so.
    # Form 8962 line 2b, reached by a Form 1095-A on a return with dependents — absent
    # means no dependent was required to file, and the engine reads 0.
    # Form 2441 Worksheet A's root — absent is the no the dictionary's own $0 fallback takes.
    # the section 1341 credit is the filer's own figure; absent, none is claimed.
    "section_1341_credit_cents":
        "section_1341_credit_cents (Schedule 3 line 13b — the credit for repayment of amounts "
        "included in income in an earlier year) was not supplied, so no such credit is claimed",
    # each alimony amount is the filer's own figure, invited on every return; absent, none
    # was received/paid. Each gate is reached only once its amount is answered.
    "alimony_received_cents":
        "alimony_received_cents (Schedule 1 line 2a) was not supplied, so no alimony is treated "
        "as received",
    "alimony_received_pre2019_agreement":
        "alimony_received_pre2019_agreement was not supplied — it is asked once alimony_received_cents "
        "is answered, and the return stops with that question rather than assuming an answer",
    "alimony_paid_cents":
        "alimony_paid_cents (Schedule 1 line 19a) was not supplied, so no alimony is treated as paid",
    "alimony_paid_pre2019_agreement":
        "alimony_paid_pre2019_agreement was not supplied — it is asked once alimony_paid_cents is "
        "answered, and the return stops with that question rather than assuming an answer",
    "alimony_paid_section_682_trust":
        "alimony_paid_section_682_trust was not supplied — it is asked once alimony_paid_cents is "
        "answered and alimony_paid_pre2019_agreement is yes, and the return stops with that "
        "question rather than assuming an answer",
    # the Form 1040 page-1 main-home checkbox — absent reads as the engine's own
    # complete-safe TRUE, taxpayer-favorable and stated rather than assumed silently.
    "main_home_in_us_over_half_year":
        "main_home_in_us_over_half_year was not supplied, so the main home is treated as in the "
        "U.S. for more than half of 2025 — the earned income credit without a qualifying child is "
        "not denied on that account",
    "paid_prior_year_care_expenses_this_year":
        "paid_prior_year_care_expenses_this_year was not supplied, so no 2024 care expenses are treated as paid in 2025 and "
        "Form 2441's Worksheet A credit is 0",
    "prior_year_credit_claimed":
        "prior_year_credit_claimed was not supplied — it is asked once you answer that you paid 2024 care "
        "expenses in 2025, and the return stops with that question rather than assuming what was claimed "
        "for 2024",
    "prior_year_credit_claimed_maximum":
        "prior_year_credit_claimed_maximum was not supplied — it is asked once you answer that the 2024 "
        "credit was claimed, and the return stops with that question rather than assuming the 2024 claim "
        "was for the maximum expenses",
    "prior_year_form_2441_line_3_cents":
        "prior_year_form_2441_line_3_cents was not supplied — it is asked once the Worksheet A chain "
        "reaches the 2024 figures, and the return stops with that question rather than crediting nothing",
    "prior_year_expenses_paid_this_year_cents":
        "prior_year_expenses_paid_this_year_cents was not supplied — it is asked once the Worksheet A "
        "chain reaches the 2024 figures, and the return stops with that question rather than crediting "
        "nothing",
    "prior_year_had_two_or_more_qualifying_persons":
        "prior_year_had_two_or_more_qualifying_persons was not supplied — it is asked once the Worksheet "
        "A chain reaches the 2024 figures, and the return stops with that question rather than assuming "
        "one qualifying person in 2024",
    "prior_year_excluded_or_deducted_benefits_cents":
        "prior_year_excluded_or_deducted_benefits_cents was not supplied — it is asked once the Worksheet "
        "A chain reaches the 2024 figures, and the return stops with that question rather than assuming "
        "no 2024 benefits",
    "prior_year_lower_earned_income_cents":
        "prior_year_lower_earned_income_cents was not supplied — it is asked once the Worksheet A chain "
        "reaches the 2024 figures, and the return stops with that question rather than crediting nothing",
    "prior_year_form_2441_line_6_cents":
        "prior_year_form_2441_line_6_cents was not supplied — it is asked once the Worksheet A chain "
        "reaches the 2024 figures, and the return stops with that question rather than crediting nothing",
    "prior_year_agi_cents":
        "prior_year_agi_cents was not supplied — it is asked once the Worksheet A chain reaches the 2024 "
        "figures, and the return stops with that question rather than crediting nothing",
    "dependents_modified_agi_cents":
        "dependents_modified_agi_cents was not supplied — no dependent in your tax family was "
        "required to file a return, so Form 8962 line 2b is 0",
    # Form 2441 lines 13 and 14, reached once a filer reports a benefit — line 13 is none
    # when absent (the dictionary's own meaning); line 14 is asked, and the return stops with it.
    "dependent_care_carryover_cents":
        "dependent_care_carryover_cents was not supplied — no prior-year dependent care benefit "
        "used in this year's grace period was counted (Form 2441 line 13)",
    "dependent_care_forfeited_cents":
        "dependent_care_forfeited_cents was not supplied — it is asked once a filer reports "
        "dependent care benefits, and the return stops with that question rather than treating "
        "none of the benefit as forfeited or carried forward (Form 2441 line 14)",
    # the Form 8962 questions a form reaches — each is asked, and the return stops with
    # the question rather than assuming an answer.
    "marketplace_estimated_income_at_least_100_fpl":
        "marketplace_estimated_income_at_least_100_fpl was not supplied — it is asked once a "
        "Form 1095-A with advance payments is entered, and the return stops with that question "
        "rather than assuming an answer",
    "below_poverty_line_not_eligible_for_medicaid_due_to_immigration":
        "below_poverty_line_not_eligible_for_medicaid_due_to_immigration was not supplied — it "
        "is asked once a Form 1095-A without advance payments is entered, and the return stops "
        "with that question rather than assuming an answer",
    "mfs_ptc_exception":
        "mfs_ptc_exception was not supplied — it is asked once a Form 1095-A is entered on a "
        "separate return, and the return stops with that question rather than assuming an answer",
    "mfs_ptc_exception_fourth_year":
        "mfs_ptc_exception_fourth_year was not supplied — it is asked once the separate-return "
        "exception is answered yes, and the return stops with that question rather than assuming "
        "an answer",
    # Form 1095-A's grid — a blank column A is a month without coverage (stated once per
    # month: the loop below skips columns B and C of a month whose column A is blank); a blank
    # column C on a coverage month is a month without advance payments.
    "f1095as[].jan_premium_cents":
        "{where}.jan_premium_cents was not supplied \u2014 January is not a coverage month on this Form 1095-A (line 21, column A blank), so no premium, SLCSP premium, or advance payment is counted for it",
    "f1095as[].jan_slcsp_cents":
        "{where}.jan_slcsp_cents was not supplied \u2014 no applicable SLCSP premium for January (line 21, column B)",
    "f1095as[].jan_aptc_cents":
        "{where}.jan_aptc_cents was not supplied \u2014 no advance payment of the credit was made for January (line 21, column C blank), so none is reconciled for it",
    "f1095as[].feb_premium_cents":
        "{where}.feb_premium_cents was not supplied \u2014 February is not a coverage month on this Form 1095-A (line 22, column A blank), so no premium, SLCSP premium, or advance payment is counted for it",
    "f1095as[].feb_slcsp_cents":
        "{where}.feb_slcsp_cents was not supplied \u2014 no applicable SLCSP premium for February (line 22, column B)",
    "f1095as[].feb_aptc_cents":
        "{where}.feb_aptc_cents was not supplied \u2014 no advance payment of the credit was made for February (line 22, column C blank), so none is reconciled for it",
    "f1095as[].mar_premium_cents":
        "{where}.mar_premium_cents was not supplied \u2014 March is not a coverage month on this Form 1095-A (line 23, column A blank), so no premium, SLCSP premium, or advance payment is counted for it",
    "f1095as[].mar_slcsp_cents":
        "{where}.mar_slcsp_cents was not supplied \u2014 no applicable SLCSP premium for March (line 23, column B)",
    "f1095as[].mar_aptc_cents":
        "{where}.mar_aptc_cents was not supplied \u2014 no advance payment of the credit was made for March (line 23, column C blank), so none is reconciled for it",
    "f1095as[].apr_premium_cents":
        "{where}.apr_premium_cents was not supplied \u2014 April is not a coverage month on this Form 1095-A (line 24, column A blank), so no premium, SLCSP premium, or advance payment is counted for it",
    "f1095as[].apr_slcsp_cents":
        "{where}.apr_slcsp_cents was not supplied \u2014 no applicable SLCSP premium for April (line 24, column B)",
    "f1095as[].apr_aptc_cents":
        "{where}.apr_aptc_cents was not supplied \u2014 no advance payment of the credit was made for April (line 24, column C blank), so none is reconciled for it",
    "f1095as[].may_premium_cents":
        "{where}.may_premium_cents was not supplied \u2014 May is not a coverage month on this Form 1095-A (line 25, column A blank), so no premium, SLCSP premium, or advance payment is counted for it",
    "f1095as[].may_slcsp_cents":
        "{where}.may_slcsp_cents was not supplied \u2014 no applicable SLCSP premium for May (line 25, column B)",
    "f1095as[].may_aptc_cents":
        "{where}.may_aptc_cents was not supplied \u2014 no advance payment of the credit was made for May (line 25, column C blank), so none is reconciled for it",
    "f1095as[].jun_premium_cents":
        "{where}.jun_premium_cents was not supplied \u2014 June is not a coverage month on this Form 1095-A (line 26, column A blank), so no premium, SLCSP premium, or advance payment is counted for it",
    "f1095as[].jun_slcsp_cents":
        "{where}.jun_slcsp_cents was not supplied \u2014 no applicable SLCSP premium for June (line 26, column B)",
    "f1095as[].jun_aptc_cents":
        "{where}.jun_aptc_cents was not supplied \u2014 no advance payment of the credit was made for June (line 26, column C blank), so none is reconciled for it",
    "f1095as[].jul_premium_cents":
        "{where}.jul_premium_cents was not supplied \u2014 July is not a coverage month on this Form 1095-A (line 27, column A blank), so no premium, SLCSP premium, or advance payment is counted for it",
    "f1095as[].jul_slcsp_cents":
        "{where}.jul_slcsp_cents was not supplied \u2014 no applicable SLCSP premium for July (line 27, column B)",
    "f1095as[].jul_aptc_cents":
        "{where}.jul_aptc_cents was not supplied \u2014 no advance payment of the credit was made for July (line 27, column C blank), so none is reconciled for it",
    "f1095as[].aug_premium_cents":
        "{where}.aug_premium_cents was not supplied \u2014 August is not a coverage month on this Form 1095-A (line 28, column A blank), so no premium, SLCSP premium, or advance payment is counted for it",
    "f1095as[].aug_slcsp_cents":
        "{where}.aug_slcsp_cents was not supplied \u2014 no applicable SLCSP premium for August (line 28, column B)",
    "f1095as[].aug_aptc_cents":
        "{where}.aug_aptc_cents was not supplied \u2014 no advance payment of the credit was made for August (line 28, column C blank), so none is reconciled for it",
    "f1095as[].sep_premium_cents":
        "{where}.sep_premium_cents was not supplied \u2014 September is not a coverage month on this Form 1095-A (line 29, column A blank), so no premium, SLCSP premium, or advance payment is counted for it",
    "f1095as[].sep_slcsp_cents":
        "{where}.sep_slcsp_cents was not supplied \u2014 no applicable SLCSP premium for September (line 29, column B)",
    "f1095as[].sep_aptc_cents":
        "{where}.sep_aptc_cents was not supplied \u2014 no advance payment of the credit was made for September (line 29, column C blank), so none is reconciled for it",
    "f1095as[].oct_premium_cents":
        "{where}.oct_premium_cents was not supplied \u2014 October is not a coverage month on this Form 1095-A (line 30, column A blank), so no premium, SLCSP premium, or advance payment is counted for it",
    "f1095as[].oct_slcsp_cents":
        "{where}.oct_slcsp_cents was not supplied \u2014 no applicable SLCSP premium for October (line 30, column B)",
    "f1095as[].oct_aptc_cents":
        "{where}.oct_aptc_cents was not supplied \u2014 no advance payment of the credit was made for October (line 30, column C blank), so none is reconciled for it",
    "f1095as[].nov_premium_cents":
        "{where}.nov_premium_cents was not supplied \u2014 November is not a coverage month on this Form 1095-A (line 31, column A blank), so no premium, SLCSP premium, or advance payment is counted for it",
    "f1095as[].nov_slcsp_cents":
        "{where}.nov_slcsp_cents was not supplied \u2014 no applicable SLCSP premium for November (line 31, column B)",
    "f1095as[].nov_aptc_cents":
        "{where}.nov_aptc_cents was not supplied \u2014 no advance payment of the credit was made for November (line 31, column C blank), so none is reconciled for it",
    "f1095as[].dec_premium_cents":
        "{where}.dec_premium_cents was not supplied \u2014 December is not a coverage month on this Form 1095-A (line 32, column A blank), so no premium, SLCSP premium, or advance payment is counted for it",
    "f1095as[].dec_slcsp_cents":
        "{where}.dec_slcsp_cents was not supplied \u2014 no applicable SLCSP premium for December (line 32, column B)",
    "f1095as[].dec_aptc_cents":
        "{where}.dec_aptc_cents was not supplied \u2014 no advance payment of the credit was made for December (line 32, column C blank), so none is reconciled for it",
    "persons[].care_expenses_cents":
        "{where}.care_expenses_cents was not supplied — no child or dependent care expenses "
        "were entered for this qualifying person (Form 2441 line 2), so none are counted",
    # stated on a claimed dependent's row 13 or older, where the answer decides whether
    # the row is a Form 2441 qualifying person; a younger row qualifies on age alone.
    # Form 8880 — the Roth-and-ABLE follow-up on an IRA yes, the student test and the
    # distribution questions on a filer row with contributions; each stops with the question.
    "persons[].roth_ira_contributions_cents":
        "{where}.roth_ira_contributions_cents was not supplied — it is asked on a joint return "
        "once that person reports a combined Roth IRA and ABLE amount above 0, so no Roth "
        "contribution reduces the other spouse's IRA limit (IRC 219(c)) on this return",
    "persons[].roth_ira_and_able_contributions_cents":
        "{where}.roth_ira_and_able_contributions_cents was not supplied — it is asked once that "
        "person answers yes to contributing to an IRA (Form 8880 line 1), and the return stops "
        "with that question rather than assuming an amount",
    "persons[].received_retirement_distributions_2023_2024":
        "{where}.received_retirement_distributions_2023_2024 was not supplied — it is asked of a "
        "filer with retirement contributions, on a joint return of both filers once either has "
        "them (Form 8880 line 4), and the return stops with that question rather than assuming "
        "no distributions",
    "persons[].retirement_distributions_2023_cents":
        "{where}.retirement_distributions_2023_cents was not supplied — it is asked once that "
        "person answers yes to distributions in 2023 or 2024, and the return stops with that "
        "question rather than assuming an amount",
    "persons[].retirement_distributions_2024_cents":
        "{where}.retirement_distributions_2024_cents was not supplied — it is asked once that "
        "person answers yes to distributions in 2023 or 2024, and the return stops with that "
        "question rather than assuming an amount",
    "persons[].received_retirement_distributions_after_year_end":
        "{where}.received_retirement_distributions_after_year_end was not supplied — it is asked "
        "of a filer with retirement contributions, on a joint return of both filers once either "
        "has them (Form 8880 line 4), and the return stops with that question rather than "
        "assuming no distributions",
    "persons[].retirement_distributions_after_year_end_cents":
        "{where}.retirement_distributions_after_year_end_cents was not supplied — it is asked "
        "once that person answers yes to a distribution after year end, and the return stops "
        "with that question rather than assuming an amount",
    "w2s[].box12_g_governmental_plan":
        "{where}.box12_g_governmental_plan was not supplied — it is asked on every W-2 with a "
        "code G amount in box 12 (Form 8880 line 2), and the return stops with that question "
        "rather than assuming a governmental plan",
    # Form 8889 Part I on a filer row with a W-2 box 12 code W amount, each question behind
    # the one before; each stops with the question. Code W itself, computed as zero when absent.
    "w2s[].box12_w_cents":
        "{where}.box12_w_cents (W-2 box 12, code W — employer contributions to a health savings "
        "account) was not supplied, so it was computed as zero — nothing from it reaches Form "
        "8889 line 9",
    "persons[].hsa_medicare":
        "{where}.hsa_medicare was not supplied — it is asked of a filer with a W-2 box 12 code W "
        "amount (Form 8889 Part I), and the return stops with that question rather than assuming "
        "no Medicare enrollment",
    # the month Medicare enrollment began.
    "persons[].hsa_medicare_first_month":
        "{where}.hsa_medicare_first_month was not supplied — it is asked once a filer with HSA "
        "contributions, or a joint return's spouse whose coverage is asked, reports Medicare "
        "enrollment for part of the year (Form 8889 line 3: the "
        "limitation is zero from that month on), and the return stops with that question rather "
        "than assuming a month",
    "persons[].hsa_hdhp_coverage":
        "{where}.hsa_hdhp_coverage was not supplied — it is asked of a filer with a code W amount "
        "and no Medicare enrollment (Form 8889 line 1), and the return stops with that question "
        "rather than assuming coverage all year",
    "persons[].hsa_hdhp_type":
        "{where}.hsa_hdhp_type was not supplied — it is asked once that filer had high deductible "
        "health plan coverage all year (Form 8889 line 1), and the return stops with that "
        "question rather than assuming self-only coverage",
    "persons[].hsa_other_coverage":
        "{where}.hsa_other_coverage was not supplied — it is asked once that filer's coverage "
        "type is self-only or family (Form 8889 Part I), and the return stops with that question "
        "rather than assuming no other coverage",
    "persons[].hsa_funding_distribution":
        "{where}.hsa_funding_distribution was not supplied — on a filer with a W-2 box 12 code W "
        "amount it is asked once they report no other coverage, and the return stops with that "
        "question; on a filer with Form 1099-SA distributions and no code W amount it is not "
        "asked, and no qualified HSA funding distribution from an individual retirement "
        "arrangement is used (Form 8889 line 10)",
    "persons[].hsa_spouse_contributed":
        "{where}.hsa_spouse_contributed was not supplied — it is asked on a separate return once "
        "that filer reports family coverage (Form 8889 line 6), and the return stops with that "
        "question rather than assuming the spouse contributed nothing",
    "persons[].hsa_marital_status_changed":
        "{where}.hsa_marital_status_changed was not supplied — it is asked of a married or widowed "
        "filer with a code W amount and no other coverage (Form 8889 line 3), and the return "
        "stops with that question rather than assuming no change",
    "persons[].hsa_marital_change_affects_limit":
        "{where}.hsa_marital_change_affects_limit was not supplied — it is asked once that filer "
        "reports a change of marital status (Form 8889 line 3), and the return stops with that "
        "question rather than assuming the limit is unaffected",
    "persons[].unable_to_care_for_self":
        "{where}.unable_to_care_for_self was not supplied — it is asked of a claimed dependent "
        "13 or older (Form 2441's other qualifying-person arm), and the return stops with that "
        "question rather than treating the dependent as able to care for themselves",
    # Form 2441 Part III on a filer row — the sole-proprietorship benefit is 0 when absent
    # (the dictionary's own meaning); the plan maximum is asked, and the return stops with it.
    "persons[].self_employed_dependent_care_benefits_cents":
        "{where}.self_employed_dependent_care_benefits_cents was not supplied — no dependent "
        "care benefit from your own sole proprietorship or partnership was counted on Form 2441 "
        "line 12",
    "persons[].dependent_care_plan_maximum_cents":
        "{where}.dependent_care_plan_maximum_cents was not supplied — it is asked once that "
        "filer's Form W-2 box 10 or own sole-proprietorship benefit is above 0, and the return "
        "stops with that question rather than excluding benefits against a limit nobody gave",
    "persons[].contributed_to_inherited_ira":
        "{where}.contributed_to_inherited_ira was not supplied — it is asked once that person "
        "answers yes to contributing to an IRA, and the return stops with that question rather "
        "than assuming an answer",
    "persons[].inherited_ira_contribution_cents":
        "{where}.inherited_ira_contribution_cents was not supplied — it is asked once that "
        "person answers yes to contributing to an inherited IRA, and the return stops with that "
        "question rather than assuming an amount",
    # hoh/qss: the last asks, same stops-with-the-question pattern. The population was widened
    # to the rows the ENGINE asks it of — every dependent row of an hoh/qss
    # return, and on a single return the rows its own screen gate asks — so the sentence names
    # both instead of claiming the question belongs to two statuses.
    # the non-parental arm's first question, on a claimed dependent the filer is not the
    # parent of — the same stops-with-the-question pattern.
    "persons[].child_parents_living":
        "{where}.child_parents_living was not supplied — it is asked of a claimed dependent who "
        "is a sibling, half- or step-sibling, stepchild, foster child, grandchild, or a "
        "sibling's child or other descendant, and the return stops with that question rather "
        "than assuming an answer",
    # the non-parental split's links — the same stops-with-the-question pattern.
    "persons[].parents_meet_divorced_or_separated_rule":
        "{where}.parents_meet_divorced_or_separated_rule was not supplied — it is asked about a "
        "claimed dependent the filer is not the parent of whose own parents are living, and the "
        "return stops with that question rather than assuming an answer",
    "persons[].a_parent_signed_declaration_not_to_claim":
        "{where}.a_parent_signed_declaration_not_to_claim was not supplied — it is asked once the "
        "child's parents meet the divorced-or-separated rule, and the return stops with that "
        "question rather than assuming an answer",
    "persons[].custodial_parent_claims_child_as_qualifying_person":
        "{where}.custodial_parent_claims_child_as_qualifying_person was not supplied — it is asked "
        "once the child is in their parents' custody with a declaration signed, and the return "
        "stops with that question rather than assuming an answer",
    "persons[].filer_agi_higher_than_custodial_parent":
        "{where}.filer_agi_higher_than_custodial_parent was not supplied — it is asked once the "
        "custodial parent does not use the child as their qualifying person, and the return stops "
        "with that question rather than assuming an answer",
    "persons[].filer_paid_most_of_home_upkeep":
        "{where}.filer_paid_most_of_home_upkeep was not supplied — it is asked on every "
        "dependent row of a head-of-household or qualifying-surviving-spouse return, and on "
        "a single return of every dependent row the engine asks it of, and the return stops "
        "with that question rather than assuming an answer",
    "spouse_death_year":
        "spouse_death_year was not supplied — it is asked on every "
        "qualifying-surviving-spouse return, and the return stops with that question "
        "rather than assuming an answer",
    "could_have_filed_jointly_year_of_death":
        "could_have_filed_jointly_year_of_death was not supplied — it is asked on every "
        "qualifying-surviving-spouse return, and the return stops with that question "
        "rather than assuming an answer",
    # mfs: the separate-return pair. Root facts, asked on every mfs return —
    # the return stops with the question, never an assumed answer.
    # the lived-together chain, on every married return — root fields.
    "lived_with_spouse_all_year":
        "lived_with_spouse_all_year was not supplied — it is asked on every married return, and "
        "the return stops with that question rather than assuming an answer",
    "months_lived_with_spouse":
        "months_lived_with_spouse was not supplied — it is asked once you did not live with your "
        "spouse all year, and the return stops with that question rather than assuming an answer",
    "separation_agreement_on_last_day":
        "separation_agreement_on_last_day was not supplied — it is asked once you lived together "
        "more than six months but not all year, and the return stops with that question rather "
        "than assuming an answer",
    "lived_apart_last_six_months":
        "lived_apart_last_six_months was not supplied — it is asked once you lived together six "
        "months or less, and the return stops with that question rather than assuming an answer",
    # the joint return's filing-requirement pair — root questions behind a claimable spouse.
    "couple_required_to_file":
        "couple_required_to_file was not supplied — it is asked on a joint return once a spouse "
        "can be claimed as someone's dependent, and the return stops with that question rather "
        "than assuming an answer",
    "couple_files_only_for_refund":
        "couple_files_only_for_refund was not supplied — it is asked once the couple is not "
        "required to file, and the return stops with that question rather than assuming an answer",
    # the filed-jointly pair on a joint return, behind a prior-year distribution.
    "filed_jointly_2023":
        "filed_jointly_2023 was not supplied — it is asked on a joint return once a filer reports "
        "a 2023 distribution (Form 8880 line 4), and the return stops with that question rather "
        "than assuming an answer",
    "filed_jointly_2024":
        "filed_jointly_2024 was not supplied — it is asked on a joint return once a filer reports "
        "a 2024 distribution (Form 8880 line 4), and the return stops with that question rather "
        "than assuming an answer",
    # the excess-in-wages question on a return with a code W amount — optional, the
    # dictionary's own adverse default when absent.
    "hsa_excess_in_w2_wages":
        "hsa_excess_in_w2_wages was not supplied — any employer HSA contribution over the Form "
        "8889 line 8 limit is reported as other income on Schedule 1 line 8z, as if the employer "
        "had not already included it in W-2 box 1 wages; answer yes if the W-2 already carries "
        "it in wages — one answer for the whole return, and on a joint return a yes drops both "
        "filers' excess from income",
    # the three combat pay elections, each asked once a filer's W-2 carries code Q.
    "combat_pay_election":
        "combat_pay_election was not supplied — it is asked once a filer's W-2 box 12 carries "
        "code Q (nontaxable combat pay), and the return stops with that question rather than "
        "assuming an answer (Form 1040 line 1i is unresolved without it)",
    "cdcc_combat_pay_election":
        "cdcc_combat_pay_election was not supplied — it is asked once a filer's W-2 box 12 "
        "carries code Q and care expenses are on the return (Form 2441 Part II), and the return "
        "stops with that question rather than assuming an answer",
    "dependent_care_benefits_combat_pay_election":
        "dependent_care_benefits_combat_pay_election was not supplied — it is asked once a "
        "filer's W-2 box 12 carries code Q and dependent care benefits are reported (Form 2441 "
        "Part III), and the return stops with that question rather than assuming an answer",
    # the residence state on every return; the Alaska dividend pair behind an Alaska answer.
    "residence_state":
        "residence_state was not supplied — it is asked on every return (the state you lived in "
        "and earned income in), and the return stops with that question rather than assuming an "
        "answer",
    "received_alaska_pfd":
        "received_alaska_pfd was not supplied — it is asked on every return, and the return "
        "stops with that question rather than assuming an answer",
    "spouse_received_alaska_pfd":
        "spouse_received_alaska_pfd was not supplied — it is asked on every joint return, and "
        "the return stops with that question rather than assuming an answer",
    # the page-1 digital-assets question, both parts, on every return.
    "received_digital_assets":
        "received_digital_assets was not supplied — it is asked on every return (part (a) of "
        "the Form 1040 page-1 digital-assets question), and the return stops with that question "
        "rather than assuming an answer",
    # Schedule B Part III, three answers, on every return.
    "foreign_financial_account":
        "foreign_financial_account was not supplied — it is asked on every return (Schedule B "
        "line 7a, a foreign financial account), and the return stops with that question rather "
        "than assuming an answer",
    "foreign_trust_grantor":
        "foreign_trust_grantor was not supplied — it is asked on every return (Schedule B line 8, "
        "owner or grantor of a foreign trust), and the return stops with that question rather "
        "than assuming an answer",
    "foreign_trust_transactions":
        "foreign_trust_transactions was not supplied — it is asked on every return (Schedule B "
        "line 8, a distribution from or transfer to a foreign trust), and the return stops with "
        "that question rather than assuming an answer",
    # Form 8862's credit-history questions, three answers, on every return.
    "eitc_reduced_or_disallowed":
        "eitc_reduced_or_disallowed was not supplied — it is asked on every return (Form 8862: an "
        "earned income credit reduced or disallowed in a prior year), and the return stops with "
        "that question rather than assuming an answer",
    "ctc_odc_reduced_or_disallowed":
        "ctc_odc_reduced_or_disallowed was not supplied — it is asked on every return (Form 8862: "
        "a child tax credit, additional child tax credit or credit for other dependents reduced or "
        "disallowed in a prior year), and the return stops with that question rather than "
        "assuming an answer",
    "qualifying_child_of_another":
        "qualifying_child_of_another was not supplied — it is asked on every return (Form 8862 "
        "line 4: claimable as another taxpayer's qualifying child), and the return stops with "
        "that question rather than assuming an answer",
    # Form 1040 line 26 — the root question on every return; the amount and the two
    # follow-ups once it is yes.
    "paid_estimated_taxes":
        "paid_estimated_taxes was not supplied — it is asked on every return (Form 1040 line 26: "
        "estimated tax payments, or an amount applied from last year's return), and the return "
        "stops with that question rather than assuming an answer",
    "estimated_tax_payments_cents":
        "estimated_tax_payments_cents was not supplied — it is asked once estimated tax payments "
        "are answered yes (Form 1040 line 26), and the return stops with that question rather "
        "than assuming an amount",
    "estimated_payments_under_different_name":
        "estimated_payments_under_different_name was not supplied — it is asked once estimated "
        "tax payments are answered yes, and the return stops with that question rather than "
        "assuming an answer",
    "estimated_payments_with_former_spouse":
        "estimated_payments_with_former_spouse was not supplied — it is asked once estimated tax "
        "payments are answered yes, and the return stops with that question rather than "
        "assuming an answer",
    # Schedule 1 line 21 — the root question on every return; the two follow-ups once yes.
    "paid_student_loan_interest":
        "paid_student_loan_interest was not supplied — it is asked on every return (Schedule 1 "
        "line 21: student loan interest), and the return stops with that question rather than "
        "assuming an answer",
    "student_loans_qualify":
        "student_loans_qualify was not supplied — it is asked once student loan interest is "
        "answered yes, and the return stops with that question rather than assuming an answer",
    # the line 6c election, reached once a benefit statement exists.
    "elects_lump_sum_benefits":
        "elects_lump_sum_benefits was not supplied — it is asked once the return carries a "
        "benefit statement (Form 1040, line 6c), and the return stops with that question rather "
        "than assuming an answer",
    # Form 8960's sole-trader question, reached once a Schedule C exists.
    "only_business_is_trading_securities":
        "only_business_is_trading_securities was not supplied — it is asked once the return carries a "
        "Schedule C (Form 8960), and the return stops with that question rather than assuming "
        "the business is not a trading business",
    "student_loan_interest_cents":
        "student_loan_interest_cents was not supplied — it is asked once student loan interest is "
        "answered yes (Form 1098-E box 1), and the return stops with that question rather than "
        "assuming an amount",
    "student_loan_interest_employer_paid_cents":
        "student_loan_interest_employer_paid_cents was not supplied — it is asked once "
        "student_loans_qualify is answered yes, and the return stops with that question rather "
        "than assuming no employer paid any of the interest",
    "student_loan_interest_from_qtp_cents":
        "student_loan_interest_from_qtp_cents was not supplied — it is asked once "
        "student_loans_qualify is answered yes, and the return stops with that question rather "
        "than assuming none of the interest was paid from qualified tuition program earnings",
    "disposed_digital_assets":
        "disposed_digital_assets was not supplied — it is asked on every return (part (b) of "
        "the Form 1040 page-1 digital-assets question), and the return stops with that question "
        "rather than assuming an answer",
    "spouse_itemizes":
        "spouse_itemizes was not supplied — it is asked on every married-filing-separately "
        "return (the printed checkbox: “Your spouse itemizes on a separate return”), and the "
        "return stops with that question rather than assuming an answer",
    "community_property_domicile":
        "community_property_domicile was not supplied — it is asked on every "
        "married-filing-separately return, and the return stops with that question rather "
        "than assuming an answer",
    # the separate-return spouse chain — asked in order, each only when the previous
    # answer reaches it; a reached question stops the return, never an assumed answer.
    "spouse_files_return":
        "spouse_files_return was not supplied — it is asked on a married-filing-separately "
        "return whose spouse does not itemize, and the return stops with that question rather "
        "than assuming an answer",
    "spouse_had_gross_income":
        "spouse_had_gross_income was not supplied — it is asked only when the spouse files no "
        "return, and the return stops with that question when it is reached",
    "spouse_can_be_claimed":
        "spouse_can_be_claimed was not supplied — it is asked only when the spouse files no "
        "return and had no gross income, and the return stops with that question when it is "
        "reached",
    "spouse_65_or_older":
        "spouse_65_or_older was not supplied — it is asked only when the spouse files no "
        "return, had no gross income and cannot be claimed by another, and the return stops "
        "with that question when it is reached",
    "spouse_is_blind":
        "spouse_is_blind was not supplied — it is asked in the same case as the spouse's age "
        "question, and the return stops with that question when it is reached",
    # the separate return's coverage question.
    "spouse_covered_by_employer_plan":
        "spouse_covered_by_employer_plan was not supplied — it is asked on a separate return "
        "once the filer contributed to an IRA and the couple did not live apart all year, and "
        "the return stops with that question when it is reached",
    # the separate-return spouse's twelve coverage months (Form 8889 line 6).
    **{f"spouse_hsa_coverage_{m}":
        f"spouse_hsa_coverage_{m} was not supplied — the twelve coverage months of the filer's "
        f"spouse (Form 8889 lines 3 and 6, January through December) are asked on a separate return "
        f"once the filer with family coverage answers that the spouse also had HSA contributions, "
        f"or beside the filer's Medicare enrollment for part of the year, and the return stops with "
        f"that question when it is reached"
       for m in ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")},
}


# the three box 20 code Z answers and the one population they belong to. Everywhere
# else the mapper refuses them by name, so an absence statement there would describe a field
# the caller could not have supplied.
_PTP_CODE_Z_FIELDS = ("qualified_ptp_income_cents", "qualified_ptp_is_sstb",
                      "ptp_prior_year_unallowed_loss_cents")


def _ptp_code_z_armed(item: dict) -> bool:
    return (item.get("source") == "partnership"
            and item.get("publicly_traded_partnership") is True)


def _at_risk_amount_armed(group: str, item: dict) -> bool:
    """the section 465 amount at risk, on the one population that can answer it — the
    at-risk answer present and FALSE, on a current-year loss. Reads the mapper's own arming
    test, which in turn reads the stream's own loss arithmetic (`schedule_c_net_cents`,
    `rental_current_net_cents`, `k1_has_box1_loss`), so the ask, the statement and the refusal
    can never disagree about which item they are about."""
    return mapper.at_risk_amount_armed(group, item, _AT_RISK_LOSS[group](item))


def _self_rental_code_could_decide(item: dict) -> bool:
    """where Schedule E line 1b's type of property stops being record-only — a rental
    whose net for the year, after any prior years' unallowed loss, is a PROFIT, which is the
    only sign at which a type 7 would recharacterize anything. Off it the code decides nothing
    and its absence has nothing to say."""
    return mapper.rental_combined_net_cents(item) > 0


def _self_rental_lessee_armed(item: dict) -> bool:
    """the lessee material-participation answer's population — Schedule E line 1b type 7,
    and nothing else. Reads the mapper's own test rather than a copy.

    NOTE the split, which is deliberate: this is the population that may ANSWER (and the guard on
    the absence statement), while `mapper.self_rental_recharacterization_armed` is the narrower
    population that is ASKED — a self-rental whose net after any prior unallowed loss is a
    profit. The boolean siblings behave the same way (`fully_at_risk` is asked on a loss and
    accepted on a profit); only the amount-shaped fields are refused off their ask population."""
    return mapper.rental_is_self_rental(item)


_AT_RISK_LOSS = {
    "schedule_c": lambda item: mapper.schedule_c_net_cents(item) < 0,
    "rentals": lambda item: mapper.rental_current_net_cents(item) < 0,
    "k1s": lambda item: mapper.k1_has_box1_loss(item),
}

# The ask, one sentence per stream because each form asks the at-risk question in its own
# words. The figure is the same one on all three: Form 6198 Part II line 10b.
_AT_RISK_ASK = {
    "rentals": "Some investment in this rental is not at risk, so the year's loss is capped: "
               "how much is at risk?",
    "schedule_c": "Box 32b is checked on this business (“Some investment is not at risk.”), so "
                  "the line 31 loss is capped: how much is at risk?",
    "k1s": "Some investment in this K-1's activity is not at risk, so the box 1 loss is "
           "capped: how much is at risk?",
}
# The provenance clause is per stream because `lines.LINE_MAP` is: a capped rental or K-1 loss
# reaches lines 11, 15 and 24 only through line 9, while a capped Schedule C loss moves the
# Schedule SE base and reaches all four independently (the agreement rule — the prose a person
# reads and the declared provenance say the same thing).
_AT_RISK_WHY = {
    "rentals": " Enter the simplified Form 6198 amount (Part II, line 10b), or 0 if nothing is "
               "at risk — the loss deducts only up to it, used for Form 1040, line 9.",
    "k1s": " Enter the simplified Form 6198 amount (Part II, line 10b), or 0 if nothing is at "
           "risk — the loss deducts only up to it, used for Form 1040, line 9.",
    "schedule_c": " Enter the simplified Form 6198 amount (Part II, line 10b), or 0 if nothing "
                  "is at risk — the loss deducts only up to it, used for Form 1040, lines 9, "
                  "11, 15 and 24.",
}


def _deductible_se_loss_armed(item: dict) -> bool:
    """a Form 1065 K-1 whose box 14 code A is answered and NEGATIVE. Reads the mapper's
    own test rather than a copy, so the ask, the statement and the refusal can never drift
    apart on which K-1 they are about."""
    return mapper.k1_has_se_loss(item)


def assumed_absent_details(facts: dict) -> list:
    """Optional inputs that move a served line and were not supplied — `{fact, statement}` pairs.

    The FACT travels structured: a client that paints the statement onto the cell it is
    about keys on `fact`, never on parsing the sentence back out of prose. `assumed_absent` below
    is this list's statements, so the sentence a person reads and the field a client acts on are
    one derivation that cannot disagree.
    """
    stated = []
    # Derived from `_ABSENT_MEANS` itself (review): this walked a hand-kept tuple while the
    # comment above claimed otherwise, and a fourth optional input would have landed unstated.
    # `test_every_optional_input_named_in_provenance_is_stated` closes the other half — every
    # optional field `derived_from` names must have a statement here.
    for key in sorted(_ABSENT_MEANS):
        template = _ABSENT_MEANS[key]
        lines = consumed_by(key)
        if "[]." not in key:
            # A ROOT field: stated when its arming status is the return's and the answer is
            # absent. Extended for the qss pair exactly as the mfs comment predicted — the
            # arming condition is per field.
            _ROOT_ARMED_BY = {"spouse_itemizes": "mfs", "community_property_domicile": "mfs",
                              "spouse_death_year": "qss",
                              "could_have_filed_jointly_year_of_death": "qss",
                              **{field: "mfs" for field, _u in mapper.MFS_SPOUSE_CHAIN}}
            armed = facts.get("filing_status") == _ROOT_ARMED_BY.get(key)
            if key in mapper.MARRIED_ROOT_FIELDS:
                # a lived-together link is stated only when the answers so far REACH it.
                armed = key in mapper.lived_together_questions_reached(facts)
            if key in mapper.MFJ_ROOT_FIELDS:
                armed = key in mapper.mfj_claim_questions_reached(facts)
            if key == mapper.IRA_COVERAGE_FIELD:
                armed = mapper.ira_coverage_question_reached(facts)
            if key in mapper.EVERY_RETURN_ROOT_FIELDS:
                armed = True                          # asked on every return
            if key in mapper.ALASKA_PFD_FIELDS:
                armed = key in mapper.alaska_pfd_questions_reached(facts)
            if key in mapper.ESTIMATED_PAYMENTS_FIELDS:
                armed = key in mapper.estimated_payments_questions_reached(facts)
            if key in mapper.STUDENT_LOAN_FIELDS:
                armed = key in mapper.student_loan_questions_reached(facts)
            if key in mapper.ALIMONY_GATE_FIELDS:
                armed = key in mapper.alimony_questions_reached(facts)
            if key == mapper.LUMP_SUM_FIELD:
                armed = mapper.lump_sum_question_reached(facts)
            if key == mapper.SOLE_TRADER_FIELD:
                armed = mapper.sole_trader_question_reached(facts)
            if key in mapper.PTC_ROOT_FIELDS:
                armed = key in mapper.ptc_questions_reached(facts)
            if key in mapper.DCB_ROOT_FIELDS:
                armed = key in mapper.dcb_root_questions_reached(facts)
            if key in mapper.ROYALTY_ROOT_FIELDS:
                armed = mapper.royalty_expenses_reached(facts)
            if key in mapper.WORKSHEET_A_FIELDS:
                armed = key in mapper.worksheet_a_questions_reached(facts)
            if key in mapper.SAVERS_ROOT_FIELDS:
                armed = key in mapper.savers_root_questions_reached(facts)
            if key in mapper.HSA_ROOT_FIELDS:
                armed = mapper.hsa_excess_question_reached(facts)
            if key in mapper.COMBAT_ROOT_FIELDS:
                armed = key in mapper.combat_pay_elections_reached(facts)
            if key in mapper.HSA_MFS_SPOUSE_MONTH_FIELDS:
                armed = mapper.hsa_mfs_spouse_months_asked(facts)
            if armed and key in dict(mapper.MFS_SPOUSE_CHAIN):
                # a chain link is stated only when the answers so far REACH it.
                armed = key in mapper.mfs_spouse_questions_reached(facts)
            if armed and key not in facts:
                stated.append({"fact": key,
                               "statement": template
                               + (f" (Form 1040 line(s) {', '.join(lines)})" if lines else "")})
            continue
        group, field = key.split("[].")
        for i, item in enumerate(facts.get(group) or []):
            if not isinstance(item, dict) or field in item:
                continue                      # supplied — including an explicit 0, which is an answer
            if (group == "persons" and field in mapper.DEPENDENT_ASKED_FIELDS
                    and item.get("role") != "dependent"):
                continue                      # a dependent qualifier says nothing about a filer row
            if field == "is_blind" and item.get("role") == "dependent":
                continue                      # the checkbox is not printed for a dependent
            if (field in mapper.EDUCATOR_FIELDS
                    and field not in mapper.educator_questions_reached(item)):
                continue                      # a filer row's question; the amount on a yes
            if (field in mapper.IRA_FIELDS
                    and field not in mapper.ira_questions_reached(item)
                    and not (field == mapper.IRA_ROTH_SPLIT_FIELD
                             and mapper.ira_roth_split_reached(facts, i))):
                continue                      # the same shape (the Roth half too)
            if (field in mapper.HSA_OWN_FIELDS
                    and field not in mapper.hsa_own_questions_reached(item)):
                continue                      # the same shape
            if field == mapper.HSA_DEC31_FIELD and not mapper.hsa_december_value_asked(facts, i):
                continue                      # invited on a filer row with HSA activity
            if field == mapper.HSA_PRIOR_EXCESS_FIELD and not mapper.hsa_prior_excess_asked(facts, i):
                continue                      # the same population
            if (field in (mapper.SAVERS_STUDENT_FIELD, *mapper.SAVERS_PERSON_FIELDS)
                    and field not in mapper.savers_questions_reached(facts, i)):
                continue                      # Form 8880's questions, as far as reached
            if (group == "w2s" and field == mapper.W2_BOX12_G_PLAN_FIELD
                    and not mapper.box12_g_plan_question_reached(item)):
                continue                      # asked only beside a code G amount
            if (group == "r1099s" and field == mapper.R1099_HFD_FIELD
                    and not mapper.hsa_funding_r1099_reached(facts, i)):
                continue                      # asked only on an IRA 1099-R behind a funding yes
            if (group == "r1099s" and field == mapper.R1099_QCD_FIELD
                    and not mapper.qcd_r1099_reached(facts, i)):
                continue                      # asked on a fully taxable IRA 1099-R of a filer born through 1953
            if (group == "r1099s" and field == mapper.R1099_QCD_SPLIT_FIELD
                    and not mapper.qcd_split_question_reached(facts, i)):
                continue                      # asked behind a positive amount
            if (group == "persons" and field == mapper.QCD_HISTORY_FIELD
                    and not mapper.qcd_history_reached(facts, i)):
                continue                      # asked once a form of the filer carries one
            if (group == "persons" and field == mapper.HSA_TRANSFER_MONTH_FIELD
                    and not mapper.hsa_transfer_month_reached(facts, i)):
                continue                      # asked above the line 8 base limitation
            if (group == "r1099s" and field == mapper.R1099_ROLLOVER_FIELD
                    and not mapper.rollover_r1099_reached(facts, i)):
                continue                      # asked on a fully taxable 1099-R with no other exclusion
            if (group == "r1099s" and field == mapper.R1099_MRA_FIELD
                    and not mapper.mra_question_reached(facts, i)):
                continue                      # asked on a code-3 disability form
            if group == "r1099s" and field in mapper.R1099_PSO_FIELDS and not {
                    mapper.R1099_PSO_FIELD: mapper.pso_question_reached,
                    mapper.R1099_PSO_PREMIUMS_FIELD: mapper.pso_premiums_question_reached,
                    mapper.R1099_PSO_AMOUNT_FIELD: mapper.pso_amount_reached}[field](facts, i):
                continue                      # the officer chain, as far as reached
            if (group == "r1099s" and field in mapper.R1099_DB_FIELDS
                    and not mapper.DEATH_BENEFIT_REACHED[field](facts, i)):
                continue                      # the death-benefit chain, as far as reached
            if (group == "b1099s" and field == mapper.B1099_TERM_FIELD
                    and mapper.b1099_term_question_reached(item)):
                continue                      # asked (a gap) where a date is missing
            if (group == "oid1099s" and field == mapper.OID_TAX_EXEMPT_FIELD
                    and not mapper.oid_tax_exempt_question_reached(item)):
                continue                      # Form 1099-OID: asked beside box 2 with box 11 blank
            if (group == "r1099s" and field == mapper.R1099_IRA_ONE_PER_YEAR_FIELD
                    and not mapper.rollover_one_per_year_reached(facts, i)):
                continue                      # asked behind a positive amount on an IRA form
            if (field in mapper.HSA_CONTRIBUTION_FIELDS
                    and field not in mapper.hsa_questions_reached(facts, i)
                    and not (field == mapper.HSA_FUNDING_FIELD
                             and mapper.hsa_funding_answer_assumed(facts, i))
                    and not (field == mapper.HSA_MONTH_FIELDS[0]
                             and mapper.hsa_vector_prefill(facts, i))):   # the prefill is stated
                continue                      # Form 8889 Part I, as far as reached; the
                                              # 1099-SA-only filer's assumed no is stated
            if (field in mapper.HSA_EXCEPTION_FIELDS
                    and field not in mapper.hsa_exception_questions_reached(facts, i)):
                continue                      # reached by the filer's 1099-SA forms
            if (field in mapper.DCB_PERSON_FIELDS
                    and field not in mapper.dcb_person_questions_reached(facts, i)):
                continue                      # a filer row's Form 2441 Part III questions
            if (field == mapper.UNABLE_TO_CARE_FIELD
                    and not mapper.unable_to_care_question_reached(item)):
                continue                      # decides only on a dependent row 13 or older
            if (field == mapper.CARE_EXPENSES_FIELD
                    and not mapper.care_expense_question_reached(facts, i)):
                continue                      # stated only on a qualifying person's row
            if (field in mapper.CLAIM_ME_FIELDS
                    and field not in mapper.claim_me_questions_reached(item)):
                continue                      # a link is stated only when reached
            if (field == "filer_paid_most_of_home_upkeep"
                    and not mapper.upkeep_question_armed(
                        facts.get("filing_status"), item, facts)):
                continue                      # only the dependent rows the engine's own
                                              # screen gate asks it of may answer it at all
            if (field == "child_parents_living"
                    and not mapper.parents_living_question_armed(item)):
                continue                      # asked only where the filer is not the parent
            if (field in dict(mapper.DEPENDENT_JOINT_RETURN_CHAIN)
                    and field not in mapper.dependent_joint_return_questions_reached(item)):
                continue                      # a joint-return link is stated only when
                                              # this row's answers so far REACH it
            if (field in dict(mapper.DEPENDENT_BENEFIT_SPLIT_CHAIN)
                    and field not in mapper.dependent_benefit_split_questions_reached(item)
                    and field not in mapper.dependent_nonparental_split_questions_reached(item)):
                continue                      # a split link is stated only when
                                              # this row's answers so far REACH it
            if (field in dict(mapper.DEPENDENT_NONPARENTAL_SPLIT_CHAIN)
                    and field not in mapper.dependent_nonparental_split_questions_reached(item)):
                continue
            if field in _PTP_CODE_Z_FIELDS and not _ptp_code_z_armed(item):
                continue                      # only a partnership K-1 whose item D is
                                              # checked may answer these at all
            if (field == "section_199a_qbi_cents"
                    and not (group == "k1s" and i in mapper.section_199a_asked(facts))):
                continue
            if (field == "deductible_se_loss_cents"
                    and not _deductible_se_loss_armed(item)):
                continue                      # only a Form 1065 K-1 whose box 14 code A
                                              # is a LOSS may answer it at all
            if (field == "amount_at_risk_cents"
                    and not _at_risk_amount_armed(group, item)):
                continue                      # only a loss item whose at-risk answer is
                                              # present and FALSE may answer it at all
            if (field == "materially_participates_in_lessee"
                    and not _self_rental_lessee_armed(item)):
                continue                      # only a Schedule E line 1b type 7 property
                                              # may answer it at all
            if (field == "active_participation_when_loss_arose"
                    and not mapper.rental_loss_arose_participation_armed(item)):
                continue                      # only a carried-in loss with active
                                              # participation yes may answer it at all
            # the depreciation-input pairs, the same shape.
            if (field in ("is_nonresidential_real_property", "building_uses_standard_gds")
                    and not mapper.rental_building_class_armed(item)):
                continue                      # only a property with a positive building basis
                                              # may answer it at all
            if (field == "placed_in_service_month"
                    and not mapper.rental_placed_in_service_month_armed(item)):
                continue                      # only a property placed in service this year
                                              # may answer it at all
            if (field == "five_year_property_basis_cents"
                    and not mapper.rental_five_year_basis_armed(item)):
                continue                      # only a property claiming a 5-year item may
                                              # answer it at all
            if field == "property_type" and not _self_rental_code_could_decide(item):
                continue                      # on a loss the code is record only again
            if group == mapper.PTC_GROUP and not field.endswith("_premium_cents"):
                month = field.split("_", 1)[0]
                if not item.get(mapper.ptc_field(month, "premium")):
                    continue                  # column A blank says it once for the month
            stated.append({"fact": f"{group}[{i}].{field}",
                           "statement": template.format(where=f"{group}[{i}]")
                           # The root branch above has always guarded this; the item branch
                           # had no field with an empty answer until whose route to a
                           # served line the committed DAG cannot see (see lines.py, line 11).
                           # "(Form 1040 line(s) )" is not a sentence anyone should read.
                           + (f" (Form 1040 line(s) {', '.join(lines)})" if lines else "")})
    return stated


def assumed_absent(facts: dict) -> list:
    """The statements view of `assumed_absent_details` — a caller reaching the API directly
    cannot be refused for omitting an optional figure, and must not be left to discover from the
    arithmetic that it was treated as zero."""
    return [entry["statement"] for entry in assumed_absent_details(facts)]


_MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August",
                "September", "October", "November", "December")


# the death-benefit chain's asks, in the words the interview serves too.
DEATH_BENEFIT_WHY = {
    "date_of_payment":
        "Enter the date in box 13 (Date of payment) of this Form 1099-R as YYYY-MM-DD — a payer completes "
        "it for a reportable death benefit under section 6050Y; used for Form 1040, line 5b.",
    "box1_is_death_benefit_under_contract":
        "Is the amount in box 1 of this Form 1099-R the death benefit paid under the life insurance "
        "contract the other questions on this form describe? Used for Form 1040, "
        "line 5b.",
    "acquired_in_reportable_policy_sale":
        "Did this person acquire the life insurance policy this death benefit was paid under from someone "
        "else — by buying it or taking an interest in it — rather than being named as its beneficiary? "
        "Answer yes only if, at the time, they had no substantial family, business or financial "
        "relationship with the insured apart from that interest (a reportable policy sale); used for Form "
        "1040, line 5b.",
    "acquired_for_valuable_consideration":
        "Was that policy, or an interest in it, transferred to this person for valuable consideration — "
        "money or something else of value? Used for Form 1040, line 5b.",
    "transfer_has_carryover_basis":
        "Did the policy keep the transferor's basis in this person's hands — a transfer whose basis is "
        "figured from the transferor's, such as a gift or a tax-free exchange? Used "
        "for Form 1040, line 5b.",
    "transfer_to_insured_or_related_party":
        "Was the policy transferred to the insured, to a partner of the insured or a partnership the "
        "insured is a partner in, or to a corporation the insured is a shareholder or officer of? "
        "Used for Form 1040, line 5b.",
    "death_benefit_basis_cents":
        "What did this person pay for the policy in total — the price paid to acquire it plus every "
        "premium and other amount paid on it since? One amount; box 5 is the payer's estimate, not the "
        "answer; used for Form 1040, line 5b.",
}


# the code-3 disability form's question, in the words the interview serves too.
MRA_WHY = (
    "Had this person reached the minimum retirement age set by the employer's plan when this "
    "disability payment was made — generally the age at which the plan first pays a pension to "
    "someone who is not disabled? Used for Form 1040, line 1h.")


# the three asks of the public-safety-officer chain, in the words the interview serves too.
PSO_WHY = {
    "public_safety_officer":
        "Is this person an eligible retired public safety officer — a law enforcement officer, "
        "firefighter, chaplain, or member of a rescue squad or ambulance crew, retired for disability "
        "or after reaching normal retirement age — and is this Form 1099-R from their government "
        "retirement plan? Used for Form 1040, line 5b.",
    "pso_premiums_paid_by_plan":
        "Did that plan pay accident, health or long-term care insurance premiums directly to the "
        "insurer out of this distribution? Used for Form 1040, line 5b.",
    "pso_premiums_cents":
        "How much of this distribution did the plan pay for those premiums during 2025? Enter 0 if "
        "none of it; used for Form 1040, line 5b.",
}


# Form 2441 Worksheet A's asks — the words the interview serves too.
WORKSHEET_A_WHY = {
    "prior_year_credit_claimed":
        "Did you claim the child and dependent care credit on your 2024 return? "
        "Used for Form 2441, Worksheet A.",
    "prior_year_credit_claimed_maximum":
        "On your 2024 return, did you claim the credit on the maximum amount of qualified expenses "
        "allowed for 2024? Used for Form 2441, Worksheet A.",
    "prior_year_form_2441_line_3_cents":
        "Enter the amount from line 3 of your 2024 Form 2441 (Worksheet A, line 1).",
    "prior_year_expenses_paid_this_year_cents":
        "How much of your 2024 qualified care expenses did you pay in 2025 (Worksheet A, line 2)? Enter 0 "
        "if none.",
    "prior_year_had_two_or_more_qualifying_persons":
        "Did you have two or more qualifying persons in 2024 (Worksheet A, line 4)?",
    "prior_year_excluded_or_deducted_benefits_cents":
        "How much in dependent care benefits did you exclude or deduct on your 2024 return (Worksheet A, "
        "line 5)? Enter 0 if none.",
    "prior_year_lower_earned_income_cents":
        "Enter the smaller of your and your spouse's 2024 earned income, or your own 2024 earned income "
        "if you were not married in 2024 (Worksheet A, line 7).",
    "prior_year_form_2441_line_6_cents":
        "Enter the amount from line 6 of your 2024 Form 2441 — the amount your 2024 credit was figured on "
        "(Worksheet A, line 9).",
    "prior_year_agi_cents":
        "Enter your 2024 adjusted gross income, from line 11 of your 2024 Form 1040 (Worksheet A, line "
        "11).",}


def gaps_for(facts: dict) -> list:
    """The gap list: one entry per missing required input, with what it would have built.

    Shape matches the design's `gaps[]` — `{fact, consumed_by, required, why}` — and `fact` is a
    path the client's `_set_fact` can write back, because a gap the caller cannot answer is a
    question nobody can act on.
    """
    gaps = []
    for path in missing_required(facts):
        lines = consumed_by(_provenance_name(path))
        gaps.append({
            "fact": path,
            "consumed_by": [[F1040, line_id] for line_id in lines],
            "required": True,
            "why": (f"{path} is required and was not supplied. "
                    + (f"It is used to compute Form 1040 line(s) {', '.join(lines)}."
                       if lines else
                       "It is needed to build the return, though it does not appear on a line "
                       "this service serves.")),
        })
    # unlocked by mfj coverage: a joint return with one person gets the spouse's row as a
    # GAP — a question, asked where the interview asks everything else — so the missing half of
    # the household is met as an ask, never discovered as a refusal.
    if facts.get("filing_status") == "mfj":
        rows = [p for p in (facts.get("persons") or [])
                if isinstance(p, dict) and p.get("role") != "dependent"]
        if rows and not any(p.get("role") == "spouse" for p in rows):
            gaps.append({
                "fact": "persons",
                "consumed_by": [],
                "required": True,
                "why": ("A joint return names two people, and only one is here. Add the "
                        "spouse's row and answer `spouse` under \"Who this person is to the "
                        "return\"."),
            })
    # Form W-2 box 13's three checkboxes, on every W-2 — asked in the form's words, one
    # per box, backstopped by `mapper.refuse_missing_w2_box13_answers`. `consumed_by` is what the
    # artifact derives (none reaches a served line at the pin; a checked "Statutory employee" box
    # is the dictionary's own knockout). All three were once attested unchecked and published.
    # Box 14's RRTA question joins the same loop: a yes is the dictionary's own knockout
    # (Form 8959 Part III needs the box-14 RRTA compensation this service does not carry) — said
    # once, where it lands (the knockout's words), never inside the question.
    _W2_ASK = {
        "statutory_employee": ("Box 13 of this W-2 — is “Statutory employee” checked?",
                               " A yes checks the box; it moves no line by itself."),
        "retirement_plan": ("Box 13 of this W-2 — is “Retirement plan” checked?",
                            " A yes checks the box; it moves no line by itself."),
        "third_party_sick_pay": ("Box 13 of this W-2 — is “Third-party sick pay” checked?",
                                 " A yes checks the box; it moves no line by itself."),
        mapper.W2_BOX14_RRTA_FIELD: (
            "Box 14 of this W-2 — does it list Railroad Retirement Tax Act (RRTA) codes "
            "(RRTA compensation, Tier 1 or Tier 2 tax)?",
            " Used for Form 8959, Part III."),
    }
    for i, w2 in enumerate(facts.get("w2s") or []):
        if not isinstance(w2, dict):
            continue
        for field in mapper.W2_ASKED_FIELDS:
            if field in w2:
                continue
            ask, why = _W2_ASK[field]
            gaps.append({
                "fact": f"w2s[{i}].{field}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"w2s[].{field}")],
                "required": True,
                "why": ask + why,
            })
    # the residence state, first among the root asks — a gate the dictionary's own knockouts
    # read (noneOfThese; a community-property state on a separate return) and the one that decides
    # which state questions follow. `consumed_by` is what the artifact derives (the static DAG CAN
    # reach lines 24, 33 and 34 through the state-marketplace chain; no fixture at the pin moves).
    if mapper.RESIDENCE_STATE_FIELD not in facts:
        gaps.append({
            "fact": mapper.RESIDENCE_STATE_FIELD,
            "consumed_by": [[F1040, line] for line in consumed_by(mapper.RESIDENCE_STATE_FIELD)],
            "required": True,
            "why": ("Which U.S. state, or the District of Columbia, did you live in and earn "
                    "income in during the year? Used to decide which state questions this return "
                    "is asked; it moves no line by itself."),
        })
    # The Alaska Permanent Fund dividend pair — the filer's on every return, the spouse's on a
    # joint return — armed by `mapper.alaska_pfd_questions_reached`, the same predicate the
    # backstop and emission read. The dividend is possible in Alaska only, but the dictionary
    # wants both answers on every return of the shape, so they are asked, never attested.
    _ALASKA_WHY = {
        "received_alaska_pfd":
            "Did you receive an Alaska Permanent Fund dividend during the year? (It is reported "
            "on Form 1099-MISC.)",
        "spouse_received_alaska_pfd":
            "Did your spouse receive an Alaska Permanent Fund dividend during the year? (It is "
            "reported on Form 1099-MISC.)",
    }
    for field in mapper.alaska_pfd_questions_reached(facts):
        if field in facts:
            continue
        gaps.append({
            "fact": field,
            "consumed_by": [[F1040, line] for line in consumed_by(field)],
            "required": True,
            "why": (_ALASKA_WHY[field]
                    + " Used to complete the Alaska Permanent Fund section; it moves no line by "
                      "itself."),
        })
    # the Form 1040 page-1 digital-assets question, both parts, on every return — in
    # page-1 order (above the standard-deduction checkboxes), and first among the asks because
    # a yes decides a knockout before any figure is entered. `consumed_by` is what the
    # reachability artifact derives for the pair: no served line reads either writable (their
    # one reader completes the income-sources section and is a member of the dictionary's
    # knockout aggregate), so the answer is honestly empty — the qss pair's shape. Both were
    # once attested no on the taxpayer's behalf and published as assumptions.
    _DIGITAL_ASSET_WHY = {
        "received_digital_assets": 'At any time during the year, did you receive a digital asset (or a financial interest in one) as a reward, award, or payment for property or services? (Part (a) of the Form 1040 page-1 digital-assets question.)',
        "disposed_digital_assets": 'At any time during the year, did you sell, exchange, gift, or otherwise dispose of a digital asset (or a financial interest in one)? (Part (b) of the same question.)',
    }
    for field in sorted(mapper.DIGITAL_ASSET_FIELDS):
        if field in facts:
            continue
        gaps.append({
            "fact": field,
            "consumed_by": [[F1040, line] for line in consumed_by(field)],
            "required": True,
            "why": (_DIGITAL_ASSET_WHY[field]
                    + " Printed on page 1 of Form 1040; it moves no line by itself."),
        })
    # Schedule B Part III — lines 7a and 8 — on every return, in the form's order, right
    # after the page-1 pair because any yes decides a knockout before a figure is entered.
    # `consumed_by` is what the reachability artifact derives: the static DAG CAN reach lines 9,
    # 11, 12, 15, 16, 24, 33 and 34 — through `/hasForeignAccountsOrTrusts` → `/requiresScheduleB`
    # → `/interestIncome` (Schedule B's taxable-interest path) — while no fixture at the pin moves
    # on any answer (a yes is the knockout aggregate's member before any figure). All three were
    # once attested no on the taxpayer's behalf and published as assumptions.
    _FOREIGN_ACCOUNT_WHY = {
        "foreign_financial_account": "At any time during the year, did you have a financial interest in or signature authority over a financial account (such as a bank account, securities account, or brokerage account) located in a foreign country? (Schedule B, line 7a.)",
        "foreign_trust_grantor": "During the year, were you the owner or grantor of a foreign trust? (Schedule B, line 8.)",
        "foreign_trust_transactions": "During the year, did you receive a distribution from, or were you a transferor to, a foreign trust? (Schedule B, line 8.)",
    }
    for field in mapper.FOREIGN_ACCOUNT_FIELDS:
        if field in facts:
            continue
        gaps.append({
            "fact": field,
            "consumed_by": [[F1040, line] for line in consumed_by(field)],
            "required": True,
            "why": (_FOREIGN_ACCOUNT_WHY[field]
                    + " Printed on Schedule B, Part III; it moves no line by itself."),
        })
    # Form 8862's credit-history questions on every return, after Schedule B's. `consumed_by`
    # is what the reachability artifact derives (the static DAG reaches the credit lines through
    # the eligibility facts). A yes with a credit in play is refused by name after resolve, where
    # the engine leaves `/eitcQualified` or `/ctcQualified` unresolved
    # (`operations._require_credit_history_resolved`); a yes with none in play computes. All
    # three were once attested no on the taxpayer's behalf and published as assumptions.
    _CREDIT_HISTORY_WHY = {
        "eitc_reduced_or_disallowed": "Has the IRS reduced or disallowed an earned income credit you claimed in a prior year, for any reason other than a math or clerical error? (Form 8862, Part II.)",
        "ctc_odc_reduced_or_disallowed": "Has the IRS reduced or disallowed a child tax credit, additional child tax credit or credit for other dependents you claimed in a prior year, for any reason other than a math or clerical error? (Form 8862, Part III.)",
        "qualifying_child_of_another": "Could you (or your spouse if filing jointly) be claimed as a qualifying child of another taxpayer for the year? (Form 8862, line 4.)",
    }
    for field in mapper.CREDIT_HISTORY_FIELDS:
        if field in facts:
            continue
        gaps.append({
            "fact": field,
            "consumed_by": [[F1040, line] for line in consumed_by(field)],
            "required": True,
            "why": (_CREDIT_HISTORY_WHY[field]
                    + " Used for Form 8862."),
        })
    # Form 1040 line 26 — the root question on every return; a yes reaches the amount and
    # the two follow-ups, armed by `mapper.estimated_payments_questions_reached`, the predicate
    # the backstop and the emission read. `consumed_by` is the artifact's answer (line 33 and
    # what it feeds). The root answer was once attested no and published as an assumption.
    _ESTIMATED_WHY = {
        mapper.ESTIMATED_PAYMENTS_FIELD:
            ("Did you make estimated tax payments for the year, or apply an amount from last "
             "year's return to this year's tax? (Form 1040, line 26.)",
             " A yes asks the amount."),
        mapper.ESTIMATED_PAYMENTS_AMOUNT_FIELD:
            ("The total estimated tax payments made for the year, plus any amount applied from "
             "last year's return.", " Used for Form 1040, lines 26 and 33."),
        "estimated_payments_under_different_name":
            ("Were any of those payments made under a name different from the one on this "
             "return?", " Used to complete the estimated tax payments "
             "section."),
        "estimated_payments_with_former_spouse":
            ("Were any of those payments made jointly with a former spouse?",
             " Used to complete the estimated tax payments section."),
    }
    for field in mapper.estimated_payments_questions_reached(facts):
        if field in facts:
            continue
        ask, why = _ESTIMATED_WHY[field]
        gaps.append({
            "fact": field,
            "consumed_by": [[F1040, line] for line in consumed_by(field)],
            "required": True,
            "why": ask + why,
        })
    # Form 2441 line 14, required once any filer reports dependent care benefits
    # (`mapper.dcb_root_questions_reached`); line 13 is optional and stated when absent.
    if (mapper.DCB_FORFEITED_FIELD in mapper.dcb_root_questions_reached(facts)
            and mapper.DCB_FORFEITED_FIELD not in facts):
        gaps.append({
            "fact": mapper.DCB_FORFEITED_FIELD,
            "consumed_by": [[F1040, line] for line in consumed_by(mapper.DCB_FORFEITED_FIELD)],
            "required": True,
            "why": ("Of the dependent care benefits reported, how much was forfeited or carried "
                    "forward to 2026 (Form 2441, line 14)? Enter 0 if none."),
        })
    # the royalty activity's ordinary expenses, required once the return claims royalty
    # income (any misc1099s[].royalties_cents above 0) — Schedule E's own "both required" reading.
    if (mapper.royalty_expenses_reached(facts)
            and mapper.ROYALTY_EXPENSES_FIELD not in facts):
        _re_lines = consumed_by(mapper.ROYALTY_EXPENSES_FIELD)
        gaps.append({
            "fact": mapper.ROYALTY_EXPENSES_FIELD,
            "consumed_by": [[F1040, line] for line in _re_lines],
            "required": True,
            "why": ("What were the total ordinary expenses for the royalty income above — agent "
                    "or collection fees, legal fees, and similar costs, but not depletion? Enter "
                    "the total, or 0 if none; used for Schedule E."),
        })
    # box 3's Alaska PFD classification, asked only once box 3 carries an amount above 0 —
    # a $0 box (a royalty-only 1099-MISC) is answered automatically and never asked.
    for i, item in enumerate(facts.get("misc1099s") or []):
        if (isinstance(item, dict) and mapper.misc_pfd_question_reached(item)
                and mapper.MISC_PFD_FIELD not in item):
            gaps.append({
                "fact": f"misc1099s[{i}].{mapper.MISC_PFD_FIELD}",
                "consumed_by": [[F1040, line]
                                for line in consumed_by(f"misc1099s[].{mapper.MISC_PFD_FIELD}")],
                "required": True,
                "why": ("Is the \"other income\" reported on this Form 1099-MISC an Alaska "
                        "Permanent Fund dividend? Used for Schedule 1."),
            })
    # Form 2441 Worksheet A — the second credit for 2024 expenses paid in 2025. The root is
    # invited (absent is the no the statement says); behind a yes the 2024 answers are required,
    # in the dictionary's own order, and the return stops with each rather than crediting nothing.
    _wa_reached = mapper.worksheet_a_questions_reached(facts)
    for _field in _wa_reached:
        if _field != mapper.WORKSHEET_A_ROOT_FIELD and _field not in facts:
            gaps.append({
                "fact": _field,
                "consumed_by": [[F1040, line] for line in consumed_by(_field)],
                "required": True,
                "why": WORKSHEET_A_WHY[_field],
            })
            break
    # Form 8962's questions, reached by a Form 1095-A (`mapper.ptc_questions_reached`):
    # line 9's gate first, then the below-poverty question column C decides, the enrollment-
    # family question with claimed dependents, the separate-return exception last. Line 2b is
    # optional and stated when absent, never asked.
    _PTC_WHY = {
        mapper.PTC_ALLOCATION_FIELD:
            "Are you allocating policy amounts with another taxpayer, or using the alternative calculation for year of marriage? Used for Form 8962, line 9.",
        mapper.PTC_ESTIMATE_FIELD:
            "When you enrolled, did the Marketplace estimate your household income at or above 100% of the federal poverty line? Used for Form 8962 when household income is below the poverty line.",
        mapper.PTC_MEDICAID_FIELD:
            "Is your household income below the federal poverty line while you are not eligible for Medicaid because of your immigration status? Used for Form 8962 when household income is below the poverty line.",
        mapper.PTC_IMMIGRATION_FIELD:
            "Is anyone in your tax family who was enrolled on the Marketplace policy not lawfully present in the United States? Used for Form 8962.",
        mapper.PTC_MFS_EXCEPTION_FIELD:
            "On a separate return, do you qualify for the exception for a victim of domestic abuse or spousal abandonment? Used for Form 8962, line A.",
        mapper.PTC_MFS_FOURTH_YEAR_FIELD:
            "Are you claiming that exception for a fourth consecutive year? Used for Form 8962.",
    }
    for field in mapper.ptc_questions_reached(facts):
        if field in facts or field not in mapper.PTC_ROOT_REQUIRED_FIELDS:
            continue
        gaps.append({
            "fact": field,
            "consumed_by": [[F1040, line] for line in consumed_by(field)],
            "required": True,
            "why": _PTC_WHY[field],
        })
    # Schedule 1 line 21 — the root question on every return; a yes reaches whether the
    # loans qualify and the interest paid, armed by `mapper.student_loan_questions_reached`.
    # The engine applies the cap, the phase-out and the claimed-dependent rule itself. The root
    # answer was once attested no and published as an assumption.
    _STUDENT_LOAN_WHY = {
        mapper.STUDENT_LOAN_FIELD:
            ("Did you pay interest on a student loan during the year? (Schedule 1, "
             "line 21.)", " A yes asks the amount."),
        "student_loans_qualify":
            ("Were the loans taken out solely to pay qualified education expenses for you, your "
             "spouse, or your dependent, and not from a related person or an employer plan?",
             " Used for Schedule 1, line 21."),
        "student_loan_interest_cents":
            ("The student loan interest paid during the year (Form 1098-E, box 1).",
             " Used for Schedule 1, line 21, and Form 1040, line 11."),
        "student_loan_interest_employer_paid_cents":
            ("How much of that student loan interest did your employer pay for you, tax-free, "
             "under an educational assistance program?",
             " Enter 0 if none; used for Schedule 1, line 21."),
        "student_loan_interest_from_qtp_cents":
            ("How much of that student loan interest was paid with tax-free earnings from a "
             "qualified tuition program (a 529 plan)?",
             " Enter 0 if none; used for Schedule 1, line 21."),
    }
    for field in mapper.student_loan_questions_reached(facts):
        if field in facts:
            continue
        ask, why = _STUDENT_LOAN_WHY[field]
        gaps.append({
            "fact": field,
            "consumed_by": [[F1040, line] for line in consumed_by(field)],
            "required": True,
            "why": ask + why,
        })
    # Form 1040 line 6c — the lump-sum election, asked once the return carries a benefit
    # statement. A yes is the dictionary's own knockout (the earlier-year figures are not
    # carried here), served with words; a no is the regular method.
    if mapper.lump_sum_question_reached(facts) and mapper.LUMP_SUM_FIELD not in facts:
        gaps.append({
            "fact": mapper.LUMP_SUM_FIELD,
            "consumed_by": [[F1040, line] for line in consumed_by(mapper.LUMP_SUM_FIELD)],
            "required": True,
            "why": ("Did any of the benefits reported on your statements include a lump-sum "
                    "payment for an earlier year that you elect to figure under the lump-sum "
                    "method? (Form 1040, line 6c.) Used for Form 1040, "
                    "line 6b."),
        })
    # Form 8960's sole-trader question, asked once the return carries a Schedule C.
    # A no is the ordinary business; a yes is refused by name (`refuse_misplaced_sole_trader_answers`).
    if mapper.sole_trader_question_reached(facts) and mapper.SOLE_TRADER_FIELD not in facts:
        gaps.append({
            "fact": mapper.SOLE_TRADER_FIELD,
            "consumed_by": [[F1040, line] for line in consumed_by(mapper.SOLE_TRADER_FIELD)],
            "required": True,
            "why": ("Is trading in financial instruments or commodities your only trade or business? (Form 8960.) Used for Schedule SE and Form 8960."),
        })
    # Schedule 1 line 2a/19a's pre-2019-agreement gates — each reached only once its own
    # amount (alimony_received_cents / alimony_paid_cents, invited on every return, never a gap
    # in itself) is answered. Entering an amount with the gate unanswered is genuinely unknown
    # includibility/deductibility (the dictionary's own rule), not a $0 to assume.
    _ALIMONY_WHY = {
        mapper.ALIMONY_RECEIVED_GATE_FIELD:
            "Was the divorce or separation agreement under which you received that alimony "
            "entered into on or before December 31, 2018, and not later modified to end its "
            "inclusion in income? Used for Schedule 1, line 2a.",
        mapper.ALIMONY_PAID_GATE_FIELD:
            "Was the divorce or separation agreement under which you paid that alimony entered "
            "into on or before December 31, 2018, and not later modified to end its "
            "deductibility? Used for Schedule 1, line 19a.",
        mapper.ALIMONY_PAID_TRUST_FIELD:
            "Was that alimony paid to your former spouse as the income of a trust (an alimony "
            "trust under section 682), rather than by you directly under the divorce or "
            "separation agreement? Used for Schedule 1, line 19a.",
    }
    for field in mapper.alimony_questions_reached(facts):
        if field in facts:
            continue
        gaps.append({
            "fact": field,
            "consumed_by": [[F1040, line] for line in consumed_by(field)],
            "required": True,
            "why": _ALIMONY_WHY[field],
        })
    # Form 1040 line 12's blindness checkbox — printed for the filer on every status
    # and for the spouse on a joint return, so it is asked on every filer row. Until this
    # unit it was attested false and published as an assumption, which withheld the
    # additional standard deduction from every blind filer who could have answered.
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict) or person.get("role") == "dependent":
            continue
        if "is_blind" in person:
            continue
        spouse_row = person.get("role") == "spouse"
        gaps.append({
            "fact": f"persons[{i}].is_blind",
            "consumed_by": [[F1040, "12"]],
            "required": True,
            "why": (("Is your spouse blind? (The form's spouse checkbox on line 12: "
                     "“Is blind”.)" if spouse_row else
                     "Are you blind? (The form's checkbox on line 12: "
                     "“Are blind”.)")
                    + " A yes adds the additional standard deduction "
                      "amount for blindness, used for Form 1040, line 12."),
        })
    # Schedule 1 line 11 — whether each filer was a K-12 educator, asked on every filer
    # row (the primary; the spouse on a joint return), and that person's expenses once the row
    # says yes, armed by `mapper.educator_questions_reached`. The engine applies the $300
    # per-educator cap and the claimed-joint-return rule itself. The answer was once attested
    # "neither" and published as an assumption.
    for i, person in enumerate(facts.get("persons") or []):
        spouse_row = isinstance(person, dict) and person.get("role") == "spouse"
        for field in mapper.educator_questions_reached(person):
            if field in person:
                continue
            if field == mapper.EDUCATOR_FIELD:
                why = (("Was your spouse a" if spouse_row else "Were you a")
                       + " kindergarten through grade 12 teacher, instructor, counselor, "
                         "principal, or aide in a school for at least 900 hours during a "
                         "school year? Used for Schedule 1, line 11.")
            else:
                why = (("The unreimbursed classroom expenses your spouse paid this year."
                        if spouse_row else
                        "The unreimbursed classroom expenses you paid this year.")
                       + " Used for Schedule 1, line 11.")
            gaps.append({
                "fact": f"persons[{i}].{field}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"persons[].{field}")],
                "required": True,
                "why": why,
            })
    # Schedule 1 line 20 — whether each filer contributed to an IRA, asked on every filer
    # row, and that person's traditional amount and inherited-IRA answer once the row says yes,
    # armed by `mapper.ira_questions_reached`. The annual limit, the phase-out and the excess
    # knockout are the dictionary's. The answer was once attested no and published.
    for i, person in enumerate(facts.get("persons") or []):
        spouse_row = isinstance(person, dict) and person.get("role") == "spouse"
        you, your = ("your spouse", "your spouse's") if spouse_row else ("you", "your")
        _ira_fields = list(mapper.ira_questions_reached(person))
        if mapper.ira_roth_split_reached(facts, i):
            _ira_fields.append(mapper.IRA_ROTH_SPLIT_FIELD)
        for field in _ira_fields:
            if field in person:
                continue
            if field == mapper.IRA_FIELD:
                why = (f"Did {you} contribute to an IRA or an ABLE account for the year? "
                       f"Used for Schedule 1, line 20 and Form 8880, line 1.")
            elif field == mapper.IRA_AMOUNT_FIELD:
                why = (f"The traditional IRA contributions {you} made for the year, 0 if they "
                       f"were to a Roth IRA or an ABLE account only. Used for Schedule 1, line 20.")
            elif field == mapper.IRA_ROTH_SPLIT_FIELD:
                why = (f"Of {your} combined Roth IRA and ABLE account contributions, how much "
                       f"went to the Roth IRA? Used for Schedule 1, line 20.")
            elif field == mapper.IRA_INHERITED_AMOUNT_FIELD:
                why = (f"Of {your} traditional IRA contributions, how much was new money paid in "
                       f"to an IRA inherited from someone other than a spouse? A transfer of the "
                       f"original owner's balance is not counted. Used for Schedule 1, line 20.")
            elif field == mapper.IRA_ROTH_ABLE_FIELD:
                why = (f"The Roth IRA and ABLE account contributions {you} made for the year, 0 "
                       f"if none. Used for Form 8880, line 1 (the retirement savings "
                       f"contributions credit).")
            else:
                why = (f"Were any of {your} contributions made to an inherited IRA? "
                       f"Used for Schedule 1, line 20.")
            gaps.append({
                "fact": f"persons[{i}].{field}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"persons[].{field}")],
                "required": True,
                "why": why,
            })
    # Form 8880 on a filer row with retirement contributions (on a joint return, on both
    # filer rows once either has them — a spouse's distributions count against the primary's
    # contributions, and a student spouse's are left out, measured) — the student test first,
    # then the line-4 distribution questions and the amounts behind a yes, armed by
    # `mapper.savers_questions_reached` (the same predicate the backstop and emission read).
    for i, person in enumerate(facts.get("persons") or []):
        spouse_row = isinstance(person, dict) and person.get("role") == "spouse"
        you, your = ("your spouse", "your spouse's") if spouse_row else ("you", "your")
        was = "Was" if spouse_row else "Were"          # the verb agrees with the row
        _SAVERS_WHY = {
            mapper.SAVERS_STUDENT_FIELD:
                f"{was} {you} enrolled as a full-time student during any part of five calendar "
                f"months of 2025? Used for Form 8880 (a student's "
                f"contributions and distributions are left out of the retirement savings "
                f"contributions credit).",
            mapper.SAVERS_DIST_PRIOR_FIELD:
                f"Did {you} receive any distribution from a retirement plan, an IRA or an ABLE "
                f"account in 2023 or 2024? Used for Form 8880, line 4.",
            mapper.SAVERS_DIST_2023_FIELD:
                f"The distributions {you} received in 2023, 0 if none (Form 8880, line 4).",
            mapper.SAVERS_DIST_2024_FIELD:
                f"The distributions {you} received in 2024, 0 if none (Form 8880, line 4).",
            mapper.SAVERS_DIST_AFTER_FIELD:
                f"Did {you} receive, or will {you} receive, a distribution from a retirement "
                f"plan, an IRA or an ABLE account after December 31, 2025 and before the return's "
                f"due date, including extensions? Used for Form 8880, "
                f"line 4.",
            mapper.SAVERS_DIST_AFTER_AMOUNT_FIELD:
                f"That distribution amount, in {your} name (Form 8880, line 4).",
        }
        for field in mapper.savers_questions_reached(facts, i):
            if field in person:
                continue
            gaps.append({
                "fact": f"persons[{i}].{field}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"persons[].{field}")],
                "required": True,
                "why": _SAVERS_WHY[field],
            })
    _SAVERS_ROOT_WHY = {
        "filed_jointly_2023": "Did you and your spouse file a joint return for 2023?",
        "filed_jointly_2024": "Did you and your spouse file a joint return for 2024?",
    }
    for field in mapper.savers_root_questions_reached(facts):
        if field in facts:
            continue
        gaps.append({
            "fact": field,
            "consumed_by": [[F1040, line] for line in consumed_by(field)],
            "required": True,
            "why": (_SAVERS_ROOT_WHY[field]
                    + " Used for Form 8880, line 4 — a spouse's distribution that year counts "
                      "against your contributions only if you filed jointly then."),
        })
    # the combat pay elections, each once a filer's W-2 box 12 carries code Q. The choice
    # is the person's; the copy names the line the answer decides and nothing else (the
    # dictionary's own comparison fact is not read back into words).
    _primary_q, _spouse_q = mapper.combat_pay_roles(facts)
    _joint = facts.get("filing_status") == "mfj"
    _whose = ("both filers' W-2s report" if _primary_q and _spouse_q
              else "the spouse's W-2 reports" if _spouse_q
              else "the primary filer's W-2 reports" if _joint else "your W-2 reports")
    _choices = ("Answer own (count the primary filer's combat pay), spouse (count the spouse's), "
                "both, or none" if _primary_q and _spouse_q else
                "Answer spouse (count the spouse's combat pay) or none" if _spouse_q else
                "Answer own (count the primary filer's combat pay) or none" if _joint else
                "Answer own (count your combat pay) or none")
    _COMBAT_WHY = {
        mapper.COMBAT_ELECTION_FIELD:
            f"Box 12 code Q — {_whose} nontaxable combat pay. Do you elect to count it as "
            f"earned income for the earned income credit? {_choices}; used for Form 1040 "
            f"line 1i — the credit is figured with the answer given.",
        mapper.CDCC_COMBAT_ELECTION_FIELD:
            f"The same combat pay, for the child and dependent care credit: do you elect to "
            f"count it as earned income there? {_choices}; used for Form 2441 Part II — the "
            f"credit is figured with the answer given.",
        mapper.DCB_COMBAT_ELECTION_FIELD:
            f"The same combat pay, for the dependent care benefits on your W-2: do you elect "
            f"to count it as earned income for the exclusion? {_choices}; used for Form 2441 "
            f"Part III — the excluded and the taxable benefit are figured with the answer given.",
    }
    for field in mapper.combat_pay_elections_reached(facts):
        if field in facts:
            continue
        gaps.append({
            "fact": field,
            "consumed_by": [[F1040, line] for line in consumed_by(field)],
            "required": True,
            "why": _COMBAT_WHY[field],
        })
    # the transfer month, asked of a filer whose funding distribution is above the base
    # limitation for their coverage (the cap the dictionary computes from it).
    for i, person in enumerate(facts.get("persons") or []):
        if mapper.hsa_transfer_month_reached(facts, i) and mapper.HSA_TRANSFER_MONTH_FIELD not in person:
            spouse_row = person.get("role") == "spouse"
            your = "your spouse's" if spouse_row else "your"
            gaps.append({
                "fact": f"persons[{i}].{mapper.HSA_TRANSFER_MONTH_FIELD}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"persons[].{mapper.HSA_TRANSFER_MONTH_FIELD}")],
                "required": True,
                "why": (f"In which month of 2025 did the IRA trustee transfer the money into {your} health "
                        f"savings account? "
                        f"Used for Form 8889, line 10 and Form 1040, line 4b."),
            })
    # the qualified HSA funding distribution's amount, on each IRA Form 1099-R of a filer
    # who answered yes (0 if none of this distribution was transferred).
    for i, item in enumerate(facts.get("r1099s") or []):
        if mapper.hsa_funding_r1099_reached(facts, i) and mapper.R1099_HFD_FIELD not in item:
            gaps.append({
                "fact": f"r1099s[{i}].{mapper.R1099_HFD_FIELD}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"r1099s[].{mapper.R1099_HFD_FIELD}")],
                "required": True,
                "why": ("How much of this Form 1099-R's distribution did the IRA trustee transfer "
                        "directly into the health savings account (a qualified HSA funding "
                        "distribution)? Enter 0 if none of it; used for Form 8889, line 10 and "
                        "Form 1040, line 4b."),
            })
    # the qualified charitable distribution — the amount on each fully taxable IRA Form
    # 1099-R of a filer born through 1953, the split-interest answer behind a positive amount,
    # and the filer's post-70½ deduction history once a form of theirs carries one.
    for i, item in enumerate(facts.get("r1099s") or []):
        if mapper.qcd_r1099_reached(facts, i) and mapper.R1099_QCD_FIELD not in item:
            gaps.append({
                "fact": f"r1099s[{i}].{mapper.R1099_QCD_FIELD}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"r1099s[].{mapper.R1099_QCD_FIELD}")],
                "required": True,
                "why": ("How much of this Form 1099-R's distribution did the IRA trustee pay directly "
                        "to a charity (a qualified charitable distribution)? Enter 0 if none of it; "
                        "used for Form 1040, line 4b."),
            })
        elif mapper.qcd_split_question_reached(facts, i) and mapper.R1099_QCD_SPLIT_FIELD not in item:
            gaps.append({
                "fact": f"r1099s[{i}].{mapper.R1099_QCD_SPLIT_FIELD}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"r1099s[].{mapper.R1099_QCD_SPLIT_FIELD}")],
                "required": True,
                "why": ("Was that payment the one-time election to a charitable remainder trust, "
                        "charitable remainder annuity trust or charitable gift annuity (a split-interest "
                        "entity)? Used for Form 1040, line 4b."),
            })
    for i, person in enumerate(facts.get("persons") or []):
        if mapper.qcd_history_reached(facts, i) and mapper.QCD_HISTORY_FIELD not in person:
            spouse_row = person.get("role") == "spouse"
            you, were = ("your spouse", "your spouse was") if spouse_row else ("you", "you were")
            gaps.append({
                "fact": f"persons[{i}].{mapper.QCD_HISTORY_FIELD}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"persons[].{mapper.QCD_HISTORY_FIELD}")],
                "required": True,
                "why": (f"The traditional IRA contributions {you} deducted in earlier years in which "
                        f"{were} 70½ or older that have not already reduced a qualified charitable "
                        f"distribution, in cents — 0 if none; Pub 590-B Appendix D line 1; used for "
                        f"Form 1040, line 4b."),
            })
    # the death-benefit chain (IRC 101) on a Form 1099-R with a date in box 13 — the cheap gate
    # first (a code 4 form: is box 1 that contract's death benefit), the sale attestation, the
    # IRC 101(a)(2) questions behind a no, the basis last; box 13 itself is required on a code C
    # form and invited on a code 4 form (an ordinary distribution to a beneficiary leaves it blank).
    for i, item in enumerate(facts.get("r1099s") or []):
        if not isinstance(item, dict):
            continue
        def _db_gap(field):
            gaps.append({
                "fact": f"r1099s[{i}].{field}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"r1099s[].{field}")],
                "required": True,
                "why": DEATH_BENEFIT_WHY[field],
            })
        if mapper.death_benefit_date_required(facts, i) and mapper.R1099_DATE_FIELD not in item:
            _db_gap(mapper.R1099_DATE_FIELD); continue
        if mapper.death_benefit_box1_reached(facts, i) and mapper.R1099_DB_BOX1_FIELD not in item:
            _db_gap(mapper.R1099_DB_BOX1_FIELD); continue
        if mapper.death_benefit_sale_reached(facts, i) and mapper.R1099_DB_SALE_FIELD not in item:
            _db_gap(mapper.R1099_DB_SALE_FIELD); continue
        if mapper.death_benefit_consideration_reached(facts, i) and mapper.R1099_DB_CONSIDERATION_FIELD not in item:
            _db_gap(mapper.R1099_DB_CONSIDERATION_FIELD); continue
        if mapper.death_benefit_carryover_reached(facts, i):
            missing = [fld for fld in (mapper.R1099_DB_CARRYOVER_FIELD, mapper.R1099_DB_RELATED_FIELD) if fld not in item]
            for fld in missing:
                _db_gap(fld)
            if missing:
                continue
        if mapper.death_benefit_basis_reached(facts, i) and mapper.R1099_DB_BASIS_FIELD not in item:
            _db_gap(mapper.R1099_DB_BASIS_FIELD)
    # the minimum-retirement-age answer on each code-3 disability Form 1099-R.
    for i, item in enumerate(facts.get("r1099s") or []):
        if mapper.mra_question_reached(facts, i) and mapper.R1099_MRA_FIELD not in item:
            gaps.append({
                "fact": f"r1099s[{i}].{mapper.R1099_MRA_FIELD}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"r1099s[].{mapper.R1099_MRA_FIELD}")],
                "required": True,
                "why": MRA_WHY,
            })
    # the public-safety-officer premium exclusion (IRC 402(l)) — the officer's attestation on
    # each pension Form 1099-R the dictionary asks about, the plan-paid premiums behind a yes, the
    # amount behind the second yes (a yes with no amount is the dictionary's own knockout).
    for i, item in enumerate(facts.get("r1099s") or []):
        if mapper.pso_question_reached(facts, i) and mapper.R1099_PSO_FIELD not in item:
            gaps.append({
                "fact": f"r1099s[{i}].{mapper.R1099_PSO_FIELD}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"r1099s[].{mapper.R1099_PSO_FIELD}")],
                "required": True,
                "why": PSO_WHY[mapper.R1099_PSO_FIELD],
            })
        elif mapper.pso_premiums_question_reached(facts, i) and mapper.R1099_PSO_PREMIUMS_FIELD not in item:
            gaps.append({
                "fact": f"r1099s[{i}].{mapper.R1099_PSO_PREMIUMS_FIELD}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"r1099s[].{mapper.R1099_PSO_PREMIUMS_FIELD}")],
                "required": True,
                "why": PSO_WHY[mapper.R1099_PSO_PREMIUMS_FIELD],
            })
        elif mapper.pso_amount_reached(facts, i) and mapper.R1099_PSO_AMOUNT_FIELD not in item:
            gaps.append({
                "fact": f"r1099s[{i}].{mapper.R1099_PSO_AMOUNT_FIELD}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"r1099s[].{mapper.R1099_PSO_AMOUNT_FIELD}")],
                "required": True,
                "why": PSO_WHY[mapper.R1099_PSO_AMOUNT_FIELD],
            })
    # the indirect rollover — the amount on each fully taxable Form 1099-R with no other
    # exclusion, and on an IRA form the one-rollover-per-year answer behind a positive amount.
    for i, item in enumerate(facts.get("r1099s") or []):
        if mapper.rollover_r1099_reached(facts, i) and mapper.R1099_ROLLOVER_FIELD not in item:
            gaps.append({
                "fact": f"r1099s[{i}].{mapper.R1099_ROLLOVER_FIELD}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"r1099s[].{mapper.R1099_ROLLOVER_FIELD}")],
                "required": True,
                "why": ("How much of this Form 1099-R's distribution did the recipient roll over themselves "
                        "into another retirement account within 60 days? Enter 0 if none of it, or if it "
                        "was later than 60 days; used for Form 1040, line 4b or 5b."),
            })
        elif mapper.rollover_one_per_year_reached(facts, i) and mapper.R1099_IRA_ONE_PER_YEAR_FIELD not in item:
            gaps.append({
                "fact": f"r1099s[{i}].{mapper.R1099_IRA_ONE_PER_YEAR_FIELD}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"r1099s[].{mapper.R1099_IRA_ONE_PER_YEAR_FIELD}")],
                "required": True,
                "why": ("Was this the only IRA-to-IRA rollover the recipient made in the 12 months before "
                        "it (the one-rollover-per-year rule)? Used for Form 1040, "
                        "line 4b."),
            })
    # Form 1099-OID: whether the box 2 interest is tax-exempt — the one case the form does not
    # settle (box 2 above 0, box 11 blank). Never defaulted: the engine drops the whole item
    # without it (measured on the pinned engine).
    # Form 1099-B box 2: asked where box 1b or 1c has no date. Never defaulted — measured
    # on the pinned engine, every served line resolves incomplete without it.
    for i, item in enumerate(facts.get("b1099s") or []):
        for field, words in (("collectibles", "Collectibles"), ("qualified_opportunity_fund", "QOF")):
            if field not in item:
                gaps.append({
                    "fact": f"b1099s[{i}].{field}",
                    "consumed_by": [],
                    "required": True,
                    "why": (f"Is the box 3 “{words}” checkbox marked on this Form 1099-B? Answer "
                            f"yes or no."),
                })
        if mapper.b1099_term_question_reached(item) and mapper.B1099_TERM_FIELD not in item:
            gaps.append({
                "fact": f"b1099s[{i}].{mapper.B1099_TERM_FIELD}",
                "consumed_by": [[F1040, line]
                                for line in consumed_by(f"b1099s[].{mapper.B1099_TERM_FIELD}")],
                "required": True,
                "why": ("Which box 2 checkbox is marked on this Form 1099-B: short-term, "
                        "long-term, or ordinary? — used for Form 1040, line 16."),
            })
    for i, item in enumerate(facts.get("oid1099s") or []):
        if mapper.oid_tax_exempt_question_reached(item) and mapper.OID_TAX_EXEMPT_FIELD not in item:
            gaps.append({
                "fact": f"oid1099s[{i}].{mapper.OID_TAX_EXEMPT_FIELD}",
                "consumed_by": [[F1040, line]
                                for line in consumed_by(f"oid1099s[].{mapper.OID_TAX_EXEMPT_FIELD}")],
                "required": True,
                "why": ("Box 2 of this Form 1099-OID — is that interest tax-exempt? "
                        "Used for Form 1040, lines 2a and 2b."),
            })
    for i, w2 in enumerate(facts.get("w2s") or []):
        if mapper.box12_g_plan_question_reached(w2) and mapper.W2_BOX12_G_PLAN_FIELD not in w2:
            gaps.append({
                "fact": f"w2s[{i}].{mapper.W2_BOX12_G_PLAN_FIELD}",
                "consumed_by": [[F1040, line]
                                for line in consumed_by(f"w2s[].{mapper.W2_BOX12_G_PLAN_FIELD}")],
                "required": True,
                "why": ("Box 12 code G of this W-2 — is the section 457(b) plan a governmental "
                        "plan? Used for Form 8880, line 2 (only a "
                        "governmental plan's deferrals count)."),
            })
    # the own-HSA-contribution question on every filer row (the IRA question's shape), the amount
    # behind a yes — armed by `mapper.hsa_own_questions_reached`.
    for i, person in enumerate(facts.get("persons") or []):
        spouse_row = isinstance(person, dict) and person.get("role") == "spouse"
        you = "your spouse" if spouse_row else "you"
        for field in mapper.hsa_own_questions_reached(person):
            if field in person or field == mapper.HSA_OWN_AFTER_FIELD:
                continue
            if field == mapper.HSA_MADE_FIELD:
                why = (f"Did {you} contribute to a health savings account yourself in 2025 — "
                       f"outside your employer's payroll contributions on Form W-2 box 12 code "
                       f"W? A qualified HSA funding distribution transferred from an IRA counts as a "
                       f"yes. Used for Form 8889, line 2.")
            else:
                why = (f"The HSA contributions {you} made for 2025 yourself, not through the "
                       f"employer, in cents — 0 if the only contribution was a transfer from an "
                       f"IRA; used for Form 8889, line 2 (the deduction on Schedule 1, line 13).")
            gaps.append({
                "fact": f"persons[{i}].{field}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"persons[].{field}")],
                "required": True,
                "why": why,
            })
    # Form 8889 Part I on a filer row with a W-2 box 12 code W amount — the questions in
    # the dictionary's gate order, each behind the one before, armed by
    # `mapper.hsa_questions_reached` (the same predicate the backstop and emission read).
    for i, person in enumerate(facts.get("persons") or []):
        spouse_row = isinstance(person, dict) and person.get("role") == "spouse"
        you, your, they = (("your spouse", "your spouse's", "your spouse") if spouse_row
                           else ("you", "your", "you"))
        was = "Was" if spouse_row else "Were"          # the verb agrees with the row
        were, Your = ("was", "Your spouse's") if spouse_row else ("were", "Your")
        _HSA_WHY = {
            mapper.HSA_MEDICARE_FIELD:
                f"{was} {you} enrolled in Medicare for all of 2025, part of it, or none of it? "
                f"Used for Form 8889 Part I (Medicare "
                f"enrollment ends HSA eligibility; asked because of the HSA contributions on "
                f"this return).",
            mapper.HSA_MEDICARE_ONSET_FIELD:
                f"In which month of 2025 did {your} Medicare enrollment begin? "
                f"Used for Form 8889, line 3 (the "
                f"contribution limit is zero from that month on).",
            mapper.HSA_COVERAGE_FIELD:
                f"Was {you} covered by a high deductible health plan for all of 2025, part of it, "
                f"or none of it? Used for Form 8889, line 1.",
            mapper.HSA_TYPE_FIELD:
                f"Was {your} high deductible health plan self-only coverage, family coverage, or "
                f"both during the year? Used for Form 8889, "
                f"line 1.",
            # the twelve months (Form 8889 line 3's chart), one ask each.
            **{field: (f"On the first day of {name} 2025, what coverage did {your} high deductible "
                       f"health plan provide — none, self-only, or family? "
                       f"Used for Form 8889, line 3.")
               for field, name in zip(mapper.HSA_MONTH_FIELDS, _MONTH_NAMES)},
            mapper.HSA_OTHER_COVERAGE_FIELD:
                f"Did {you} have other health coverage that is not a high deductible health plan "
                f"for the whole year, part of it, or none of it? "
                f"Used for Form 8889 Part I.",
            mapper.HSA_FUNDING_FIELD:
                f"Did {you} make a qualified HSA funding distribution from an IRA in 2025 — a "
                f"transfer the IRA trustee made directly into the health savings account? "
                f"A yes is then asked for the amount on each IRA Form 1099-R; used "
                f"for Form 8889, line 10 and Form 1040, line 4b.",
            mapper.HSA_PRIOR_HFD_FIELD:
                f"Did {you} make a qualified HSA funding distribution in any earlier year? The "
                f"election can be made once in a lifetime. Used for Form "
                f"8889, line 10 and Form 1040, line 4b.",
            mapper.HSA_TESTING_FIELD:
                f"{Your} IRA-to-HSA transfer opened a testing period that runs from the month of the "
                f"transfer through the last day of the 12th month after it. What was the first month "
                f"in that window in which {you} {were} not an eligible individual — or {were} "
                f"{you} eligible in every month of it? Used for Form 8889 Part III, line 19 and "
                f"Schedule 2, line 17d.",
            mapper.HSA_SPOUSE_CONTRIBUTED_FIELD:
                f"Did {your} spouse have contributions to a health savings account for 2025? "
                f"Used for Form 8889, line 6.",
            mapper.HSA_MARITAL_CHANGED_FIELD:
                f"Did {your} marital status change during 2025 — did {they} marry, divorce, or "
                f"lose a spouse? Used for Form 8889, line 3.",
            mapper.HSA_MARITAL_AFFECTS_FIELD:
                f"Does that change in marital status affect {your} HSA contribution limit — "
                f"did {your} coverage type change with it? Used for Form "
                f"8889, line 3.",
        }
        for field in mapper.hsa_questions_reached(facts, i):
            if field in person:
                continue
            gaps.append({
                "fact": f"persons[{i}].{field}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"persons[].{field}")],
                "required": True,
                "why": _HSA_WHY[field],
            })
    # Form 8889 line 17a/17b — the 20%-tax exception pair on a filer row whose Forms 1099-SA
    # show taxable distributions (armed by `mapper.hsa_exception_questions_reached`: taxable above
    # zero, code 1 throughout, under 66 at the close). Both halves required together.
    for i, person in enumerate(facts.get("persons") or []):
        spouse_row = isinstance(person, dict) and person.get("role") == "spouse"
        you, your = ("your spouse", "your spouse's") if spouse_row else ("you", "your")
        they = "your spouse" if spouse_row else "you"
        for field in mapper.hsa_exception_questions_reached(facts, i):
            if field in person:
                continue
            if field == mapper.HSA_EXCEPTION_AMOUNT_FIELD:
                why = (f"Of {your} taxable HSA distributions (Form 8889, line 16), how much was "
                       f"distributed after {they} became disabled, after the account beneficiary "
                       f"died, or after {they} turned 65? Enter 0 if none of it; used for Form "
                       f"8889, line 17b.")
            else:
                why = ("Which of those is the ground for that amount? Answer with one of: "
                       "distributed after turning 65, distributed after becoming disabled, "
                       "distributed after the account beneficiary died, or no exception applies; "
                       "used for Form 8889, line 17a.")
            gaps.append({
                "fact": f"persons[{i}].{field}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"persons[].{field}")],
                "required": True,
                "why": why,
            })
    # Form 2441 Part III on a filer row — the plan maximum, required once that filer
    # reports a benefit (`mapper.dcb_person_questions_reached`); the sole-proprietorship benefit
    # is optional and stated when absent. Direct File's own question, not a printed line.
    for i, person in enumerate(facts.get("persons") or []):
        spouse_row = isinstance(person, dict) and person.get("role") == "spouse"
        your = "your spouse's" if spouse_row else "your"
        if (mapper.DCB_PLAN_MAX_FIELD in mapper.dcb_person_questions_reached(facts, i)
                and mapper.DCB_PLAN_MAX_FIELD not in person):
            gaps.append({
                "fact": f"persons[{i}].{mapper.DCB_PLAN_MAX_FIELD}",
                "consumed_by": [[F1040, line]
                                for line in consumed_by(f"persons[].{mapper.DCB_PLAN_MAX_FIELD}")],
                "required": True,
                "why": (f"The most {your} employer's dependent care assistance plan allows for "
                        f"2025, from the plan's own documents; used for Form 2441 Part III to "
                        f"figure the excluded and taxable benefits."),
            })
    # Form 2441's other qualifying-person arm, asked on a claimed dependent's row 13 or
    # older — where the answer decides whether the row may carry care expenses at all
    # (`mapper.unable_to_care_question_reached`); a younger row qualifies on age alone.
    for i, person in enumerate(facts.get("persons") or []):
        if (mapper.unable_to_care_question_reached(person)
                and mapper.UNABLE_TO_CARE_FIELD not in person):
            gaps.append({
                "fact": f"persons[{i}].{mapper.UNABLE_TO_CARE_FIELD}",
                "consumed_by": [[F1040, line]
                                for line in consumed_by(f"persons[].{mapper.UNABLE_TO_CARE_FIELD}")],
                "required": True,
                "why": ("Was this dependent physically or mentally unable to care for themselves "
                        "in 2025? Used for Form 2441 (a dependent who "
                        "turned 13 before the year, or on January 1, is a qualifying person "
                        "only if so)."),
            })
    # the qualifying-child age test's disability arm, asked on a claimed dependent the age arm
    # does not already settle (`mapper.disability_question_armed`, the same predicate the
    # backstop reads). Its lines are the dependent path's own reach: the filer row's path is a
    # different fact, so the service field carries no single row in the artifact.
    for i, person in enumerate(facts.get("persons") or []):
        if (mapper.disability_question_armed(person, facts)
                and mapper.DISABILITY_FIELD not in person):
            from . import reachability
            reached = set(reachability.reaches("/familyAndHousehold/*/permanentTotalDisability"))
            gaps.append({
                "fact": f"persons[{i}].{mapper.DISABILITY_FIELD}",
                "consumed_by": [[F1040, line] for line in _DISPLAY_ORDER if line in reached],
                "required": True,
                "why": ("Was this dependent permanently and totally disabled at any time in "
                        "2025? Used for the qualifying-child age test (Form 1040, Dependents)."),
            })
    # Form 1040 line 6c — the earlier years a lump-sum payment is for, asked once the return
    # elects (`mapper.lump_sum_years_reached`); the mapper backstop stops with the question. Each
    # row's nine figures are required item fields, so `REQUIRED_ITEM_FIELDS` asks them per row.
    if mapper.lump_sum_years_reached(facts) and not (facts.get(mapper.LUMP_SUM_GROUP) or []):
        gaps.append({
            "fact": mapper.LUMP_SUM_GROUP,
            "consumed_by": [[F1040, line] for line in consumed_by("ssa1099s[].net_benefits_cents")],
            "required": True,
            "why": ("Which earlier years is your lump-sum payment for? Add one row per year "
                    "(Publication 915, Worksheet 2 or 3) — the benefit statement shows the year "
                    "or years, and each row carries that year's figures."),
        })
    # Form 2441 line 1 — the care providers, asked once any person carries care expenses
    # above zero (`mapper.care_providers_question_reached`); the mapper backstop stops with the
    # question. `consumed_by` is what the amounts reach: the providers themselves change no dollar.
    if mapper.care_providers_question_reached(facts) and not (facts.get(mapper.CDCC_GROUP) or []):
        gaps.append({
            "fact": mapper.CDCC_GROUP,
            "consumed_by": [[F1040, line] for line in consumed_by("persons[].care_expenses_cents")],
            "required": True,
            "why": ("Who provided the care you entered expenses for? Add one row per provider "
                    "(Form 2441, line 1): whether column (c) carries an organization's EIN, "
                    "\"Tax-Exempt\", or an individual's SSN; whether the provider was your "
                    "household employee in 2025 (column (d)); and the amount paid (column (e)). "
                    "Names, addresses and numbers are not entered."),
        })
    # the page-1 "someone can claim you" chain — the root on every filer row, the links on
    # the primary row as the answers reach them (`mapper.claim_me_questions_reached`).
    _CLAIM_ME_WHY = {
        "someone_can_claim_you":
            "Can someone else claim you as a dependent? (The form's page-1 checkbox: “Someone "
            "can claim: You as a dependent”.)",
        "expect_to_be_claimed": "Do you expect that person to claim you this year?",
        "potential_claimer_must_file": "Is the person who could claim you required to file a tax "
                                       "return?",
        "potential_claimer_filed": "Did the person who could claim you file a tax return anyway?",
        "potential_claimer_filed_only_for_refund":
            "Did they file only to get a refund of tax withheld or estimated tax paid?",
    }
    for i, person in enumerate(facts.get("persons") or []):
        for field in mapper.claim_me_questions_reached(person):
            if field in person:
                continue
            why = _CLAIM_ME_WHY[field]
            if field == "someone_can_claim_you" and person.get("role") == "spouse":
                why = ("Can someone else claim your spouse as a dependent? (The form's page-1 "
                       "checkbox: “Someone can claim: Your spouse as a dependent”.)")
            gaps.append({
                "fact": f"persons[{i}].{field}",
                "consumed_by": [[F1040, line] for line in consumed_by(f"persons[].{field}")],
                "required": True,
                "why": why + " A filer someone claims gets a smaller standard deduction and no "
                             "earned income credit — Form 1040, lines 12 and 33.",
            })
    # The Schedule C loss gate: when a business's line 31 is a loss, line G and
    # box 32a become the form's own questions — the printed Schedule C asks box 32 ONLY on a
    # loss, and this service asks exactly where the form does. The engine would take the loss
    # either way (line G is record-only at the pin; unanswered box 32 is treated as fully at
    # risk), which is precisely why neither may be defaulted here. The threshold and the
    # engine's netProfit sign share one definition: `mapper.schedule_c_net_cents`.
    for i, item in enumerate(facts.get("schedule_c") or []):
        if not isinstance(item, dict) or mapper.schedule_c_net_cents(item) >= 0:
            continue
        if "materially_participated" not in item:
            gaps.append({
                "fact": f"schedule_c[{i}].materially_participated",
                "consumed_by": [],
                "required": True,
                "why": ("This business has a loss, and the form asks: “Did you "
                        "‘materially participate’ in the operation of this business during "
                        "2025?” (Schedule C line G). Answer Yes or No — used to decide "
                        "whether the loss can be computed here."),
            })
        if "all_investment_at_risk" not in item:
            gaps.append({
                "fact": f"schedule_c[{i}].all_investment_at_risk",
                "consumed_by": [],
                "required": True,
                "why": ("This business has a loss, and the form asks which box describes the "
                        "investment in it: “All investment is at risk.” (box 32a) or “Some "
                        "investment is not at risk.” (box 32b). Answer yes for box 32a or "
                        "no for box 32b — box 32b then asks how much is at risk, and the "
                        "loss is capped at it."),
            })
        if _at_risk_amount_armed("schedule_c", item) and "amount_at_risk_cents" not in item:
            # behind the at-risk answer, and only there. It is the answer's own
            # follow-up — the dictionary reads the amount only when the boolean is present
            # and false, and unanswered it leaves every served line Incomplete.
            gaps.append({
                "fact": f"schedule_c[{i}].amount_at_risk_cents",
                "consumed_by": [[F1040, l]
                                for l in consumed_by("schedule_c[].amount_at_risk_cents")],
                "required": True,
                "why": _AT_RISK_ASK["schedule_c"] + _AT_RISK_WHY["schedule_c"],
            })
    # The rentals loss gate — two DIFFERENT thresholds because two different rules:
    # the §465 at-risk question turns on the CURRENT year's loss (a carry-in already passed
    # at-risk in its own year); the §469(i) active-participation question turns on the Form 8582
    # line 1d COMBINE (current net with the prior unallowed loss — measured at the pin, a 5,000
    # profit against an 8,000 carry-in nets to −3,000 and turns on this answer). Both share the
    # mapper's own arithmetic, never a re-derivation.
    for i, item in enumerate(facts.get("rentals") or []):
        if not isinstance(item, dict):
            continue
        if mapper.rental_current_net_cents(item) < 0 and "fully_at_risk" not in item:
            gaps.append({
                "fact": f"rentals[{i}].fully_at_risk",
                "consumed_by": [],
                "required": True,
                "why": ("This rental has a loss for the year. Is all the investment in it at "
                        "risk? A no then asks how much is at risk, "
                        "and the loss is capped at it (Form 6198)."),
            })
        if _at_risk_amount_armed("rentals", item) and "amount_at_risk_cents" not in item:
            # behind the at-risk answer, and only there. It is the answer's own
            # follow-up — the dictionary reads the amount only when the boolean is present
            # and false, and unanswered it leaves every served line Incomplete.
            gaps.append({
                "fact": f"rentals[{i}].amount_at_risk_cents",
                "consumed_by": [[F1040, l]
                                for l in consumed_by("rentals[].amount_at_risk_cents")],
                "required": True,
                "why": _AT_RISK_ASK["rentals"] + _AT_RISK_WHY["rentals"],
            })
        if (mapper.self_rental_recharacterization_armed(item)
                and "materially_participates_in_lessee" not in item):
            # asked where it decides a number, and only there. Unanswered the dictionary's
            # gate resolves false and the profit stays passive — a computed return, and the
            # taxpayer-FAVOURABLE side, which is what makes silence unacceptable rather than
            # merely incomplete (the SSTB flag's lesson).
            gaps.append({
                "fact": f"rentals[{i}].materially_participates_in_lessee",
                "consumed_by": [[F1040, l] for l in
                                consumed_by("rentals[].materially_participates_in_lessee")],
                "required": True,
                "why": ("This property made a profit for the year and its Schedule E line 1b "
                        "type is 7, Self-Rental. Did you materially participate in the "
                        "business it is rented to — the tenant's business, not the rental "
                        "itself? A yes treats the profit as "
                        "non-passive, used for Form 1040, line 9."),
            })
        if mapper.rental_combined_net_cents(item) < 0 and "active_participation" not in item:
            gaps.append({
                "fact": f"rentals[{i}].active_participation",
                "consumed_by": [],
                "required": True,
                "why": ("This rental's net for the year, after any prior years' unallowed "
                        "loss, is a loss. Did you actively participate in the rental — make "
                        "management decisions in a significant and bona fide sense? "
                        "It decides whether Form 8582's special allowance "
                        "applies or the loss is carried forward."),
            })
        if (mapper.rental_loss_arose_participation_armed(item)
                and "active_participation_when_loss_arose" not in item):
            gaps.append({
                "fact": f"rentals[{i}].active_participation_when_loss_arose",
                "consumed_by": [[F1040, l] for l in
                                consumed_by("rentals[].active_participation_when_loss_arose")],
                "required": True,
                "why": ("This rental carries in a prior years' unallowed loss and you actively "
                        "participated in it in 2025. Did you also actively participate in it "
                        "in the year (or years) that loss arose? If the years differ, answer "
                        "no. It decides whether the loss is entered in Form 8582 Part IV, "
                        "with the special allowance, or Part V."),
            })
        # the depreciation-input pairs. Each is a question only once its own arming
        # answer is given — a building basis for the class, a claimed 5-year property for its
        # basis, a current-year building for its month — mirroring the loss-gate pair above.
        if (mapper.rental_building_class_armed(item)
                and "is_nonresidential_real_property" not in item):
            gaps.append({
                "fact": f"rentals[{i}].is_nonresidential_real_property",
                "consumed_by": [[F1040, l] for l in
                                consumed_by("rentals[].is_nonresidential_real_property")],
                "required": True,
                "why": ("This property's building depreciation basis is entered. Is the "
                        "building nonresidential real property (an office, store, or "
                        "warehouse) rather than residential rental property? "
                        "It decides the building's MACRS recovery period, 39 years "
                        "or 27.5, on Form 4562 Part III."),
            })
        if (mapper.rental_building_class_armed(item)
                and "building_uses_standard_gds" not in item):
            gaps.append({
                "fact": f"rentals[{i}].building_uses_standard_gds",
                "consumed_by": [[F1040, l] for l in
                                consumed_by("rentals[].building_uses_standard_gds")],
                "required": True,
                "why": ("This property's building depreciation basis is entered. Is the "
                        "building depreciated under regular MACRS over 27.5 years or 39 "
                        "years, rather than ADS or another recovery period? "
                        "Used for Schedule E, line 18."),
            })
        if (mapper.rental_placed_in_service_month_armed(item)
                and "placed_in_service_month" not in item):
            gaps.append({
                "fact": f"rentals[{i}].placed_in_service_month",
                "consumed_by": [[F1040, l] for l in
                                consumed_by("rentals[].placed_in_service_month")],
                "required": True,
                "why": ("This property's building was placed in service this year. In what "
                        "calendar month? Answer 1 through 12 — it selects the first-year "
                        "mid-month depreciation fraction on Form 4562 Part III."),
            })
        if (mapper.rental_five_year_basis_armed(item)
                and "five_year_property_basis_cents" not in item):
            gaps.append({
                "fact": f"rentals[{i}].five_year_property_basis_cents",
                "consumed_by": [[F1040, l] for l in
                                consumed_by("rentals[].five_year_property_basis_cents")],
                "required": True,
                "why": ("This property claims a 5-year MACRS personal-property item (an "
                        "appliance, carpeting, or furniture). What is its depreciable cost "
                        "basis? Used for Form 4562 Part III line 19b."),
            })
    # The dependents gates: every claimed dependent's qualifiers are QUESTIONS
    # — the engine models the whole §152 battery and these are the filer's own answers to it;
    # assuming any of them claims (or denies) a dependent on this service's say-so. The
    # benefit-split question is scoped to child relationships (measured: a non-child
    # dependent completes without it) and can only be asked once the relationship is known.
    _DEP_ASKS = {
        "relationship": "How is this dependent related to the primary filer?",
        "months_in_home": "How many months did this dependent live with you during the "
                          "year? Six months exactly counts as not more than half. For a "
                          "child born (or who died) during the year, answer 12 if your home "
                          "was theirs for more than half the time they were alive.",
        "is_married": "Is this dependent married?",
        "provided_own_support": "Did this person provide more than half of their OWN "
                                "support for the year?",
        "gross_income_under_limit": "Is this person's own gross income for the year under "
                                    "the dependent income limit? (See the Form 1040 "
                                    "instructions' gross income test.)",
        "filer_provided_over_half_support": "Did you provide more than half of this "
                                            "person's support for the year?",
        "could_be_qualifying_child_of_another": "Could this person be the qualifying child "
                                                "of another taxpayer?",
    }
    for i, person in enumerate(facts.get("persons") or []):
        if not isinstance(person, dict) or person.get("role") != "dependent":
            continue
        for field, ask in _DEP_ASKS.items():
            if field not in person:
                gaps.append({
                    "fact": f"persons[{i}].{field}",
                    "consumed_by": [],
                    "required": True,
                    "why": ask + " Used to decide whether this dependent can be claimed and "
                                 "which credit applies.",
                })
        if (mapper.other_parent_question_armed(person)
                and "has_other_biological_or_adoptive_parent" not in person):
            gaps.append({
                "fact": f"persons[{i}].has_other_biological_or_adoptive_parent",
                "consumed_by": [],
                "required": True,
                "why": ("Does this child have another living biological or adoptive "
                        "parent? Used to decide whether this child is claimed under the "
                        "ordinary rules or the rule for children of divorced or separated "
                        "parents."),
            })
    # the split gate's custody questions, on a claimed dependent 18 or older at the end of the
    # year, one link at a time — armed by `mapper.child_custody_questions_reached`, the same
    # predicate the mapper's backstop, its unreached-answer refusal and the emission read.
    _CUSTODY_WHY = {
        mapper.CHILD_STATE_FIELD:
            "In which state or U.S. territory did this dependent live on July 2, 2025, or "
            "outside the United States?",
        mapper.EMANCIPATED_FIELD:
            "Was this dependent emancipated under the law of the state they lived in, in 2025 "
            "or earlier?",
        mapper.EMANCIPATED_AFTER_MIDYEAR_FIELD:
            "Was this dependent emancipated after July 2, 2025?",
    }
    for i, person in enumerate(facts.get("persons") or []):
        for field in mapper.child_custody_questions_reached(person):
            if field in person:
                continue
            gaps.append({
                "fact": f"persons[{i}].{field}",
                "consumed_by": [[F1040, line]
                                for line in consumed_by(f"persons[].{field}")],
                "required": True,
                "why": (_CUSTODY_WHY[field]
                        + " Used to decide whether this dependent was still in a parent's "
                          "custody under the rule for children of divorced or separated "
                          "parents (Form 1040, Dependents)."),
            })
    # the member-of-household questions, on a claimed dependent not related to the filer in a
    # listed way who lived with the filer all year (both), or a Form 2441 qualifying person on a
    # return that claims care expenses (the local-law question alone) — armed by
    # `mapper.household_member_questions_reached`, the same predicate the backstop, the
    # unreached-answer refusal and the emission read.
    for i, person in enumerate(facts.get("persons") or []):
        reached = mapper.household_member_questions_reached(facts, i)
        on_route = mapper.household_member_route_reached(person)
        for field in reached:
            if field in person:
                continue
            if field == mapper.WAS_SPOUSE_FIELD:
                why = ("Was this person your spouse at any time in 2025? Used for the "
                       "qualifying-relative household test (Form 1040, Dependents).")
            elif on_route:
                why = ("Did your relationship with this person violate local law at any time in "
                       "2025? Used for the qualifying-relative household test (Form 1040, "
                       "Dependents) and Form 2441.")
            else:
                why = ("Did your relationship with this person violate local law at any time in "
                       "2025? Used for Form 2441's qualifying-person test.")
            gaps.append({
                "fact": f"persons[{i}].{field}",
                "consumed_by": [[F1040, line]
                                for line in consumed_by(f"persons[].{field}")],
                "required": True,
                "why": why,
            })
    # the non-parental arm's first question, on every claimed dependent the filer is not
    # the parent of (the dictionary's `tpIsNotParent`) — armed by
    # `mapper.parents_living_question_armed`, the same predicate the backstop and refusals read.
    for i, person in enumerate(facts.get("persons") or []):
        if not mapper.parents_living_question_armed(person) or "child_parents_living" in person:
            continue
        gaps.append({
            "fact": f"persons[{i}].child_parents_living",
            "consumed_by": [[F1040, line]
                            for line in consumed_by("persons[].child_parents_living")],
            "required": True,
            "why": ("Are this person's biological or adoptive parents living? Used to decide "
                    "whether this person is claimed under the ordinary rules — Form 1040, "
                    "lines 24, 33 and 34."),
        })
    # the joint-return test, on a married dependent row only and one link at a time —
    # the next question is asked once the previous answer reaches it, so a filer whose
    # dependent files no joint return sees ONE question. Armed by
    # `mapper.dependent_joint_return_questions_reached`, the same predicate the mapper's
    # backstop, its unreached-answer refusal and the emission read.
    _JOINT_RETURN_WHY = {
        "files_joint_return_with_spouse":
            "Are this person and their spouse filing a joint return?",
        "required_to_file_with_spouse":
            "Are this person and their spouse required to file?",
        "joint_return_only_for_refund":
            "Are this person and their spouse filing a return only to claim a refund of "
            "income tax withheld or estimated tax paid?",
    }
    for i, person in enumerate(facts.get("persons") or []):
        for field in mapper.dependent_joint_return_questions_reached(person):
            if field in person:
                continue
            gaps.append({
                "fact": f"persons[{i}].{field}",
                "consumed_by": [[F1040, line]
                                for line in consumed_by(f"persons[].{field}")],
                "required": True,
                "why": (_JOINT_RETURN_WHY[field]
                        + " Used to decide whether this dependent can be claimed — Form "
                          "1040, lines 24, 33 and 34."),
            })
    # the benefit-split gate, on the filer's own biological or adopted child answered as
    # having another legal parent, and one link at a time — the cheapest question settles most
    # rows, so a filer whose parents' situation is neither divorce nor separation nor living
    # apart sees ONE question. Armed by `mapper.dependent_benefit_split_questions_reached`, the
    # same predicate the mapper's backstop, its unreached-answer refusal and the emission read.
    _BENEFIT_SPLIT_WHY = {
        "parents_situation":
            "What is your situation with this child's other legal parent — divorced or "
            "separated, living apart for the last six months of the year, or something else?",
        "child_in_parents_custody":
            "As of July 2, was this child still in the legal custody of their biological or "
            "adoptive parents?",
        "child_lived_with_parents_over_half_year":
            "Did this child live with you and/or their other legal parent for more than six "
            "months of the year?",
        "parents_provided_over_half_support":
            "Did you and/or this child's other legal parent pay more than half of their "
            "support for the year?",
        "written_declaration":
            "Has either parent signed a written declaration not to claim this child, "
            "sometimes on Form 8332 — you, the other parent, or neither?",
        # the custodial-parent questions, in the dictionary's words.
        "nights_with_filer_vs_other_parent":
            "Did this child spend more nights with you, fewer nights with you, or the same "
            "number of nights with each parent?",
        "filer_agi_higher_than_other_parent":
            "Was your adjusted gross income higher than the other parent's?",
    }
    for i, person in enumerate(facts.get("persons") or []):
        for field in mapper.dependent_benefit_split_questions_reached(person):
            if field in person:
                continue
            gaps.append({
                "fact": f"persons[{i}].{field}",
                "consumed_by": [[F1040, line]
                                for line in consumed_by(f"persons[].{field}")],
                "required": True,
                "why": (_BENEFIT_SPLIT_WHY[field]
                        + (" Used to decide which parent claims this child and which credits "
                           "go with them — Form 1040, lines 24 and 34."
                           if field in ("nights_with_filer_vs_other_parent",
                                        "filer_agi_higher_than_other_parent")
                           else " Used to decide whether this child is claimed under the "
                                "ordinary rules or the rule for children of divorced or "
                                "separated parents.")),
            })
    # the non-parental split, behind a YES to "are the child's own parents living?", one
    # link at a time — armed by `mapper.dependent_nonparental_split_questions_reached`.
    _NONPARENTAL_WHY = {
        "parents_meet_divorced_or_separated_rule":
            "Do this child's parents meet the rule for children of divorced or separated parents, "
            "or parents who lived apart?",
        "a_parent_signed_declaration_not_to_claim":
            "Has either of this child's parents signed a written declaration not to claim them?",
        "child_in_parents_custody":
            "As of July 2, was this child still in the legal custody of their biological or "
            "adoptive parents?",
        "custodial_parent_claims_child_as_qualifying_person":
            "Does the custodial parent claim this child as their qualifying person — for head of "
            "household, the earned income credit, or another credit?",
        "filer_agi_higher_than_custodial_parent":
            "Was your adjusted gross income higher than the custodial parent's?",
    }
    for i, person in enumerate(facts.get("persons") or []):
        for field in mapper.dependent_nonparental_split_questions_reached(person):
            if field in person:
                continue
            gaps.append({
                "fact": f"persons[{i}].{field}",
                "consumed_by": [[F1040, line]
                                for line in consumed_by(f"persons[].{field}")],
                "required": True,
                "why": (_NONPARENTAL_WHY[field]
                        + " Used to decide whether this child is claimed on this return — Form "
                          "1040, lines 24, 33 and 34."),
            })
    # the joint return's filing-requirement pair, behind a claimable spouse — armed by
    # `mapper.mfj_claim_questions_reached`, the same predicate the backstop and emission read.
    _MFJ_CLAIM_WHY = {
        "couple_required_to_file": "Are you and your spouse required to file a tax return?",
        "couple_files_only_for_refund":
            "Are you filing only to get a refund of tax withheld or estimated tax paid — not to "
            "claim dependents or credits?",
    }
    for field in mapper.mfj_claim_questions_reached(facts):
        if field in facts:
            continue
        gaps.append({
            "fact": field,
            "consumed_by": [[F1040, line] for line in consumed_by(field)],
            "required": True,
            "why": (_MFJ_CLAIM_WHY[field]
                    + " Used to decide whether a spouse someone can claim is claimed on this "
                      "return — the standard deduction and the earned income credit, Form 1040 "
                      "lines 12 and 33."),
        })
    # the lived-together chain on every married return, one link at a time — armed by
    # `mapper.lived_together_questions_reached`, the same predicate the backstop, the refusal
    # and the emission read. It decides whether the child's keeping-up-home question is asked
    # on a married return, and completes the spouse and household sections.
    _LIVED_TOGETHER_WHY = {
        "lived_with_spouse_all_year": "Did you live with your spouse for the whole year?",
        "months_lived_with_spouse":
            "How long did you live with your spouse this year — apart all year, together more "
            "than six months, or together six months or less?",
        "separation_agreement_on_last_day":
            "On the last day of the year, were you living apart from your spouse under a "
            "separation agreement?",
        "lived_apart_last_six_months":
            "Did you live apart from your spouse for the last six months of the year?",
    }
    for field in mapper.lived_together_questions_reached(facts):
        if field in facts:
            continue
        gaps.append({
            "fact": field,
            "consumed_by": [[F1040, line] for line in consumed_by(field)],
            "required": True,
            "why": (_LIVED_TOGETHER_WHY[field]
                    + " Used to decide which household questions this return is asked; it "
                      "moves no line by itself."),
        })
    # hoh/qss — the last asks. The qss pair (root), the keeping-up-home answer (every row the
    # engine asks it of, past hoh/qss too), and the missing qualifying-person row.
    status = facts.get("filing_status")
    if status == "qss":
        if "spouse_death_year" not in facts:
            gaps.append({
                "fact": "spouse_death_year",
                "consumed_by": [],
                "required": True,
                "why": ("Which of the two preceding tax years did your spouse die in? The "
                        "qualifying-surviving-spouse status exists for exactly those two "
                        "years (a spouse who died during the tax year files jointly for "
                        "that year)."),
            })
        if "could_have_filed_jointly_year_of_death" not in facts:
            gaps.append({
                "fact": "could_have_filed_jointly_year_of_death",
                "consumed_by": [],
                "required": True,
                "why": ("Could you have filed jointly with your spouse for the year they "
                        "died, whether or not you did? Used to decide whether the "
                        "qualifying-surviving-spouse status can be computed."),
            })
    if status in ("hoh", "qss"):
        rows = [q for q in (facts.get("persons") or [])
                if isinstance(q, dict) and q.get("role") == "dependent"]
        if not rows:
            gaps.append({
                "fact": "persons",
                "consumed_by": [],
                "required": True,
                "why": ("This filing status names a qualifying person, and none is here. "
                        "Add the person's row and answer `dependent` under \"Who this "
                        "person is to the return\"."),
            })
    # the keeping-up-home question, on every row the ENGINE asks it of. Armed by
    # `mapper.upkeep_question_armed` — the same function the mapper's backstop and refusal read,
    # so the ask and the refusal cannot disagree about which row they are about. Two `why`
    # sentences, because the reason differs and only one of them is true on each return: on an
    # hoh/qss return the declared status turns on the answer; on a single return the status is
    # already settled and the answer is what finishes the household section.
    for i, person in enumerate(facts.get("persons") or []):
        if not mapper.upkeep_question_armed(status, person, facts):
            continue
        if "filer_paid_most_of_home_upkeep" in person:
            continue
        gaps.append({
            "fact": f"persons[{i}].filer_paid_most_of_home_upkeep",
            "consumed_by": [],
            "required": True,
            "why": ("Did you pay more than half the cost of keeping up the home this person "
                    "lived in? "
                    + ("The filing status turns on it."
                       if status in ("hoh", "qss")
                       else "The household section is not complete without it.")),
        })
    # The K-1 gates. Item D on every partnership K-1 (measured: the pinned
    # flow-completeness guard stays false without it); the loss trio on a partnership or
    # s_corp box 1 loss. The estate_trust loss never reaches a gap — it is refused outright
    # (`mapper.refuse_unsupported_k1_answers`).
    # The separate-return pair — domicile FIRST (its true dooms the return:
    # knockouts-first, the cheap gate before the next question), then the printed checkbox.
    if facts.get("filing_status") == "mfs":
        if "community_property_domicile" not in facts:
            gaps.append({
                "fact": "community_property_domicile",
                "consumed_by": [],
                "required": True,
                "why": ("Is your domicile, or your spouse's, in a community property state? "
                        "(Form 8958 keys on domicile.) A separate "
                        "return in a community property state cannot be computed here."),
            })
        if "spouse_itemizes" not in facts:
            gaps.append({
                "fact": "spouse_itemizes",
                "consumed_by": [[F1040, "12"]],
                "required": True,
                "why": ("Does your spouse itemize deductions on their separate return? (The "
                        "form asks: “Your spouse itemizes on a separate return”.) If yes, "
                        "this return's standard deduction is zero — used for Form 1040, "
                        "line 12."),
            })
        # the spouse chain, one link at a time — the next question is asked only once
        # the previous answer reaches it, so a filer whose spouse files sees one question.
        _SPOUSE_WHY = {
            "spouse_files_return":
                "Does your spouse file their own return for the year? "
                "If not, the next questions decide whether the spouse's age or blindness "
                "amount joins this return's standard deduction, Form 1040, line 12.",
            "spouse_had_gross_income":
                "Did your spouse have any gross income for the year? "
                "Used for Form 1040, line 12.",
            "spouse_can_be_claimed":
                "Can someone else claim your spouse as a dependent? "
                "Used for Form 1040, line 12.",
            "spouse_65_or_older":
                "Was your spouse born before January 2, 1961? (The form's spouse checkbox on "
                "line 12.) A yes adds the spouse's age amount to this "
                "return's standard deduction.",
            "spouse_is_blind":
                "Is your spouse blind? (The form's spouse checkbox on line 12.) A yes adds "
                "the spouse's blindness amount to this return's standard deduction.",
        }
        for field in mapper.mfs_spouse_questions_reached(facts):
            if field not in facts:
                gaps.append({"fact": field, "consumed_by": [[F1040, "12"]],
                             "required": True, "why": _SPOUSE_WHY[field]})
        # the other spouse's employer-plan coverage decides the IRA deduction's phase-out
        # on a separate return of a couple who did not live apart all year.
        if (mapper.ira_coverage_question_reached(facts)
                and mapper.IRA_COVERAGE_FIELD not in facts):
            gaps.append({
                "fact": mapper.IRA_COVERAGE_FIELD,
                "consumed_by": [[F1040, line]
                                for line in consumed_by(mapper.IRA_COVERAGE_FIELD)],
                "required": True,
                "why": ("Was your spouse covered by a retirement plan at work during the year? "
                        "Used for Schedule 1, line 20."),
            })
        # the spouse's twelve HSA coverage months, behind the filer's line 6 check — the
        # dictionary divides the shared family limitation once every month is answered.
        if mapper.hsa_mfs_spouse_months_asked(facts):
            for field, name in zip(mapper.HSA_MFS_SPOUSE_MONTH_FIELDS, _MONTH_NAMES):
                if field in facts:
                    continue
                gaps.append({
                    "fact": field,
                    "consumed_by": [[F1040, line] for line in consumed_by(field)],
                    "required": True,
                    "why": (f"On the first day of {name} 2025, what coverage did your spouse's high "
                            f"deductible health plan provide — none, self-only, or family? "
                            f"Used for Form 8889, lines 3 and 6."),
                })
    for i, item in enumerate(facts.get("k1s") or []):
        if not isinstance(item, dict):
            continue
        if (item.get("source") == "partnership"
                and "publicly_traded_partnership" not in item):
            gaps.append({
                "fact": f"k1s[{i}].publicly_traded_partnership",
                "consumed_by": [],
                "required": True,
                "why": ("Every Schedule K-1 (Form 1065) asks item D: “Check if this is a "
                        "publicly traded partnership (PTP)”. A yes checks the box — "
                        "it decides how a loss or the qualified business income deduction is "
                        "computed."),
            })
        if item.get("source") == "partnership" and "general_partner" not in item:
            # item G on every partnership K-1 — after item D (both printed, both
            # cheap; D first because it is the older gate and the PTP presumption item G
            # bears on only exists once D is true).
            gaps.append({
                "fact": f"k1s[{i}].general_partner",
                "consumed_by": [],
                "required": True,
                "why": ("Every Schedule K-1 (Form 1065) prints item G: “General partner or "
                        "LLC member-manager” or “Limited partner or other LLC member”. "
                        "Answer yes for the first box, no for the second — it decides "
                        "how a guaranteed payment for capital and a publicly traded "
                        "partnership's loss are treated."),
            })
        # SHAPE NOTE (repaired): the four K-1 item gaps below served `consumed_by` as a
        # bare list of line ids while every other gap in this module — and the published
        # response schema, which declares "[form, line] pairs" — serves PAIRS. Nothing caught
        # it: the client's `open_questions` unpacks each entry into `_form, line`, so a
        # two-character id silently yielded its SECOND CHARACTER and a person reading the code
        # Z ask was told "Form 1040 line(s) 5, 6, 4, 3, 4" (measured), while a one-character id
        # raised ValueError outright (the guaranteed-payment box 14A ask, and the
        # deductible-loss ask the moment its reach stopped being empty). A sweep now exists
        # that would have caught it — `EveryEmittedGapMatchesTheDeclaredSchemaTest` validates
        # every gap this function can emit against the declared `$defs/gap`, over the fixture
        # corpus with one field removed at a time plus the K-1 shapes no complete fixture
        # reaches, and its negative control is this exact defect.
        if (_ptp_code_z_armed(item) and "qualified_ptp_income_cents" not in item):
            # box 20 code Z, after item D (which arms it) and item G. Nothing in the
            # dictionary refuses its absence — the complete-safe alias resolves $0 — so an
            # unasked code Z is a qualified business income deduction quietly forgone.
            gaps.append({
                "fact": f"k1s[{i}].qualified_ptp_income_cents",
                "consumed_by": [[F1040, l] for l in consumed_by("k1s[].qualified_ptp_income_cents")],
                "required": True,
                "why": ("Item D of this Schedule K-1 (Form 1065) is checked, so box 20 code "
                        "Z (Section 199A information) has to be answered: enter the qualified "
                        "publicly traded partnership income from the statement attached to "
                        "this K-1 — a loss as a negative amount, or 0 if the statement "
                        "reports no qualified amount."),
            })
        if (_ptp_code_z_armed(item) and "qualified_ptp_is_sstb" not in item):
            # asked, not defaulted. It was optional while the deduction routed $0 above
            # the section 199A threshold — the answer moved a form line and no served one. Now
            # that Form 8995-A computes, silence is the taxpayer-FAVOURABLE side (the whole
            # qualified amount, where the law may allow the applicable percentage or nothing),
            # and a question the filer can answer that moves a served line is asked.
            gaps.append({
                "fact": f"k1s[{i}].qualified_ptp_is_sstb",
                "consumed_by": [[F1040, l] for l in consumed_by("k1s[].qualified_ptp_is_sstb")],
                "required": True,
                "why": ("Is this publicly traded partnership a specified service trade or "
                        "business? No box on the K-1 says so; it is "
                        "used for Schedule A (Form 8995-A), Part II."),
            })
        if (i in mapper.section_199a_asked(facts) and "section_199a_qbi_cents" not in item):
            # after item D (which decides a partnership's population). Nothing in the
            # dictionary refuses its absence — an empty `/qualifiedBusinesses` takes no K-1
            # income — so an unasked statement is the deduction quietly forgone.
            where = ("box 20 code Z" if item.get("source") == "partnership"
                     else "box 17 code V")
            gaps.append({
                "fact": f"k1s[{i}].section_199a_qbi_cents",
                "consumed_by": [[F1040, l] for l in consumed_by("k1s[].section_199a_qbi_cents")],
                "required": True,
                "why": (f"Enter the qualified business income from the section 199A statement "
                        f"attached to this Schedule K-1 ({where}), or 0 if the statement "
                        f"reports none; a loss as a negative amount — used for Form 1040, "
                        f"lines 13 and 15."),
            })
        if (item.get("source") == "partnership" and mapper.k1_has_guaranteed_payment(item)
                and "se_earnings_cents" not in item):
            # a guaranteed payment makes box 14 code A a question (0 is an answer) —
            # the dictionary's own SE-assessment gate refuses the item otherwise, and the
            # pinned runner discards that Incomplete, so the ask lives here.
            gaps.append({
                "fact": f"k1s[{i}].se_earnings_cents",
                "consumed_by": [[F1040, l] for l in consumed_by("k1s[].se_earnings_cents")],
                "required": True,
                "why": ("This K-1 reports a guaranteed payment, so box 14 code A "
                        "(self-employment earnings) has to be answered: enter the amount "
                        "printed beside code A, or 0 if box 14 is blank — used for Schedule "
                        "SE, and for Form 1040, lines 11 and 24."),
            })
        if (_deductible_se_loss_armed(item)
                and "deductible_se_loss_cents" not in item):
            # right after box 14A itself, and before the box 1 loss trio — the printed
            # instruction under box 14 code A ("enter only the deductible amount on Schedule
            # SE") asks the PARTNER for this figure, and the engine cannot re-derive it: the
            # 704(d) / 465 / 469 suspension it turns on is cross-year state the single-year
            # graph does not hold. Unanswered, the return refuses.
            loss = f"${abs(item['se_earnings_cents']) / 100:,.2f}"
            gaps.append({
                "fact": f"k1s[{i}].deductible_se_loss_cents",
                "consumed_by": [[F1040, l] for l in consumed_by("k1s[].deductible_se_loss_cents")],
                "required": True,
                "why": (f"This K-1's box 14 code A is a loss of {loss}. Enter how much of "
                        f"that loss you are allowed to deduct this year after the basis, "
                        f"at-risk and passive-activity limits, as a negative amount or 0 if "
                        f"none — used for Schedule SE, and for Form 1040, lines 11, 15 "
                        f"and 24."),
            })
        if (item.get("source") in ("partnership", "s_corp")
                and mapper.k1_has_box1_loss(item)):
            asks = {
                "materially_participated":
                    "This K-1's box 1 is a loss. Did you materially participate in the "
                    "activity? A no routes the loss through Form "
                    "8582 rather than deducting it now.",
                "basis_cents":
                    "This K-1's box 1 is a loss. What is the adjusted basis in the interest "
                    "before this loss? The loss deducts only up to it; the rest carries "
                    "forward.",
                "fully_at_risk":
                    "This K-1's box 1 is a loss. Is all the investment in the activity at "
                    "risk? A no then asks how much is at risk, and "
                    "the loss is capped at it (Form 6198).",
            }
            for field, why in asks.items():
                if field not in item:
                    gaps.append({
                        "fact": f"k1s[{i}].{field}",
                        "consumed_by": [],
                        "required": True,
                        "why": why,
                    })
        if (item.get("source") in ("partnership", "s_corp") and not mapper.k1_has_box1_loss(item)
                and "materially_participated" not in item
                and any(mapper.k1_has_box1_loss(other)
                        for j, other in enumerate(facts.get("k1s") or []) if j != i)):
            # A PROFIT beside another K-1's loss: whether this income is passive decides how much
            # of that loss is allowed this year — a passive loss is netted against passive income
            # (Form 8582). MEASURED on profile-passive-netting: unasked, the loss beside
            # it was suspended whole where the engine allows part of it.
            gaps.append({
                "fact": f"k1s[{i}].materially_participated",
                "consumed_by": [],
                "required": True,
                "why": ("Another Schedule K-1 on this return reports a loss. Did you materially "
                        "participate in the activity this K-1 reports? A no makes its income "
                        "passive, so a passive loss can be deducted against it (Form 8582)."),
            })
        if (item.get("source") == "estate_trust" and mapper.k1_has_box1_loss(item)
                and "materially_participated" not in item):
            # 2026-09-22: the one loss answer a Schedule K-1 (Form 1041) does carry. MEASURED at
            # A 5,000.00 box 6 loss deducts whole on a yes and is SUSPENDED on a no,
            # and with the answer absent it deducts as entered — which is why the loss was refused
            # outright until now. Basis and at-risk are not asked here: those limits are not
            # carried for this form, and answering them is refused.
            gaps.append({
                "fact": f"k1s[{i}].materially_participated",
                "consumed_by": [],
                "required": True,
                "why": ("This Schedule K-1 (Form 1041) reports a loss in box 6. Did you "
                        "materially participate in the activity? A no "
                        "suspends the loss as a passive one rather than deducting it now."),
            })
        if (item.get("source") == "estate_trust" and mapper.k1_has_box1_loss(item)
                and "fully_at_risk" not in item):
            # …and the other limit this form does carry. Without it the loss deducts past the
            # amount at risk: measured, `profile-estate-atrisk` reaches its oracle only once this
            # answer and the amount behind it are sent.
            gaps.append({
                "fact": f"k1s[{i}].fully_at_risk",
                "consumed_by": [],
                "required": True,
                "why": ("This Schedule K-1 (Form 1041) reports a loss in box 6. Is all the "
                        "investment in the activity at risk? A no then "
                        "asks how much is at risk, and the loss is capped at it (Form 6198)."),
            })
        if _at_risk_amount_armed("k1s", item) and "amount_at_risk_cents" not in item:
            # behind the at-risk answer, and only there. It is the answer's own
            # follow-up — the dictionary reads the amount only when the boolean is present
            # and false, and unanswered it leaves every served line Incomplete.
            gaps.append({
                "fact": f"k1s[{i}].amount_at_risk_cents",
                "consumed_by": [[F1040, l]
                                for l in consumed_by("k1s[].amount_at_risk_cents")],
                "required": True,
                "why": _AT_RISK_ASK["k1s"] + _AT_RISK_WHY["k1s"],
            })
    return gaps
