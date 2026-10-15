# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Identity projection and cloud-payload lint — the client's own refusal.

The design's rule is that the cloud knows WHERE the name goes but not what it is, and the client
knows the name but not where. That holds only if something on the CLIENT refuses to send an
identifier. The service refuses identifiers it receives; this refuses them before they leave.
Two independent controls on either side of the wire, deliberately: a client that relies on the
server to reject its mistakes has no boundary of its own, and the cloud is the party
whose exposure we are trying to bound.

FAIL-CLOSED. A field nobody classified is REFUSED, never dropped. That is the single lesson shared
by #55 (elections/carryovers silently dropped), #69 (identifier keys silently dropped) and #73
(a defaulted birth month): a value that vanishes quietly produces a number computed as if it had
never been sent, and nobody finds out.

No tax knowledge lives here. The projection decides what may CROSS, never what anything means.
"""
from __future__ import annotations

import re

# Fields that stay on the client, by name: names, TINs, full dates of birth,
# addresses, phone/email, bank and account details, signatures, and source-document identity.
LOCAL_ONLY = frozenset({
    "taxpayer_name", "spouse_name", "dependent_name", "preparer_name", "employer_name",
    "ssn", "itin", "ein", "tin", "atin", "ip_pin",
    "address", "mailing_address", "phone", "email",
    "date_of_birth", "spouse_date_of_birth",
    "bank_account", "routing_number", "signature",
    "source_filename", "document_hash", "notes",
})

# Fields that may cross: computational derivatives only. Adding one here is the deliberate act that
# widens the boundary — which is why the default for an unlisted field is refusal, not passage.
# Every field of the service's fact schema is here, not merely the covered slice: whether a stream
# is COVERED is a different question from whether it is SAFE TO SEND, and conflating them would make
# widening coverage look like widening the privacy boundary. `test_client_payload.py` locks this set
# against the schema in both directions.
MAY_CROSS = frozenset({
    # envelope
    "tax_year", "case_id",
    # collections (structural containers, recursed into)
    "persons", "w2s", "int1099s", "oid1099s", "b1099s", "div1099s", "r1099s", "w2gs", "ssa1099s", "g1099s", "misc1099s", "hsa_distributions", "ssa_lump_sum_years", "care_providers", "f1095as", "schedule_c", "rentals", "k1s",
    "elections", "carryovers",
    # filer derivatives
    "filing_status", "spouse_itemizes", "community_property_domicile",
    "couple_required_to_file", "couple_files_only_for_refund",
    "filed_jointly_2023", "filed_jointly_2024",
    "hsa_excess_in_w2_wages",
    "combat_pay_election", "cdcc_combat_pay_election",
    "dependent_care_benefits_combat_pay_election",
    "received_digital_assets", "disposed_digital_assets",
    "foreign_financial_account", "foreign_trust_grantor",
    "foreign_trust_transactions",
    "eitc_reduced_or_disallowed", "ctc_odc_reduced_or_disallowed",
    "qualifying_child_of_another",
    "paid_estimated_taxes", "estimated_tax_payments_cents",
    "section_1341_credit_cents",
    "royalty_expenses_cents", "royalty_is_oil_gas_geothermal",
    "alimony_received_cents", "alimony_received_pre2019_agreement",
    "alimony_paid_cents", "alimony_paid_pre2019_agreement",
    "alimony_paid_section_682_trust",
    "main_home_in_us_over_half_year",
    "estimated_payments_under_different_name", "estimated_payments_with_former_spouse",
    "paid_student_loan_interest", "student_loans_qualify",
    "elects_lump_sum_benefits",
    "only_business_is_trading_securities",
    "student_loan_interest_cents",
    "student_loan_interest_employer_paid_cents", "student_loan_interest_from_qtp_cents",
    "residence_state", "received_alaska_pfd", "spouse_received_alaska_pfd",
    "lived_with_spouse_all_year", "months_lived_with_spouse",
    "separation_agreement_on_last_day", "lived_apart_last_six_months",
    "spouse_files_return", "spouse_had_gross_income", "spouse_can_be_claimed",
    "spouse_65_or_older", "spouse_is_blind",
    "role", "birth_year", "birth_month", "tin_type", "relationship", "is_blind",
    "k12_educator", "educator_expenses_cents",
    "made_ira_contributions", "traditional_ira_contributions_cents",
    "made_hsa_contributions", "hsa_own_contributions_cents",
    "hsa_own_contributions_after_year_end_cents",
    "hsa_december_31_value_cents",
    "hsa_prior_year_excess_cents",
    "roth_ira_and_able_contributions_cents",
    "roth_ira_contributions_cents",
    "received_retirement_distributions_2023_2024", "retirement_distributions_2023_cents",
    "retirement_distributions_2024_cents", "received_retirement_distributions_after_year_end",
    "retirement_distributions_after_year_end_cents", "box12_g_governmental_plan",
    "contributed_to_inherited_ira", "inherited_ira_contribution_cents",
    "spouse_covered_by_employer_plan",
    *[f"spouse_hsa_coverage_{m}" for m in ("jan", "feb", "mar", "apr", "may", "jun",
                                           "jul", "aug", "sep", "oct", "nov", "dec")],
    "someone_can_claim_you", "expect_to_be_claimed", "potential_claimer_must_file",
    "potential_claimer_filed", "potential_claimer_filed_only_for_refund",
    "months_in_home", "is_student", "is_permanently_disabled",
    "unable_to_care_for_self",
    "is_married", "provided_own_support", "gross_income_under_limit",
    "filer_provided_over_half_support", "could_be_qualifying_child_of_another",
    "has_other_biological_or_adoptive_parent", "filer_paid_most_of_home_upkeep",
    "child_residence_state", "child_emancipated", "child_emancipated_after_july_2",
    "was_spouse_during_year", "relationship_violates_local_law",
    "files_joint_return_with_spouse", "required_to_file_with_spouse",
    "joint_return_only_for_refund",
    "parents_situation", "child_in_parents_custody",
    "child_lived_with_parents_over_half_year", "parents_provided_over_half_support",
    "written_declaration",
    "child_parents_living",
    "nights_with_filer_vs_other_parent", "filer_agi_higher_than_other_parent",
    "parents_meet_divorced_or_separated_rule", "a_parent_signed_declaration_not_to_claim",
    "custodial_parent_claims_child_as_qualifying_person", "filer_agi_higher_than_custodial_parent",
    "spouse_death_year", "could_have_filed_jointly_year_of_death",
    # W-2
    "person", "employer_ref", "wages_cents", "withholding_cents", "social_security_wages_cents",
    "medicare_wages_cents", "social_security_withheld_cents", "medicare_withheld_cents",
    "statutory_employee", "retirement_plan", "third_party_sick_pay",             # box 13
    "has_rrta_codes",                                                            # box 14
    "dependent_care_benefits_cents",                                             # box 10
    "box12_a_cents", "box12_b_cents", "box12_c_cents", "box12_d_cents", "box12_e_cents", "box12_f_cents", "box12_g_cents", "box12_h_cents", "box12_j_cents", "box12_k_cents", "box12_l_cents", "box12_m_cents", "box12_n_cents", "box12_p_cents", "box12_q_cents", "box12_r_cents", "box12_s_cents", "box12_t_cents", "box12_v_cents", "box12_w_cents", "box12_y_cents", "box12_z_cents", "box12_aa_cents", "box12_bb_cents", "box12_dd_cents", "box12_ee_cents", "box12_ff_cents", "box12_gg_cents", "box12_hh_cents", "box12_ii_cents",                                                                  # box 12
    # other income streams (schema-accepted; the service refuses several for coverage reasons, which
    # is a coverage boundary, not a privacy one)
    "interest_cents", "government_interest_cents", "tax_exempt_interest_cents",
    "federal_withholding_cents",
    # Form 1099-B (`federal_withholding_cents` above is its box 4 too). Box 1a, the free-text
    # description, is not a field; the two dates are the sale's, not the person's.
    "date_acquired", "date_sold", "proceeds_cents", "cost_basis_cents",
    "accrued_market_discount_cents", "wash_sale_loss_disallowed_cents", "term", "collectibles",
    "qualified_opportunity_fund", "loss_not_allowed", "basis_reported_to_irs",
    # Form 1099-INT boxes 9, 12, 13 (boxes 2, 10 and 11 share the OID's names below)
    "private_activity_bond_interest_cents", "treasury_bond_premium_cents",
    "tax_exempt_bond_premium_cents",
    # Form 1099-OID (`federal_withholding_cents` above is its box 4 too)
    "original_issue_discount_cents", "other_periodic_interest_cents",
    "early_withdrawal_penalty_cents", "market_discount_cents", "acquisition_premium_cents",
    "treasury_oid_cents", "bond_premium_cents", "tax_exempt_oid_cents", "box2_is_tax_exempt",
    "fatca_filing_requirement",
    "ordinary_dividends_cents", "qualified_dividends_cents", "capital_gain_distributions_cents",
    "unrecaptured_1250_gain_cents", "section_199a_dividends_cents",
    "exempt_interest_dividends_cents",
    "gross_distribution_cents", "taxable_amount_cents", "taxable_amount_not_determined",
    "distribution_code", "ira_sep_simple", "winnings_cents",
    "other_cents", "other_percentage", "percentage_of_total_distribution",
    "qualified_hsa_funding_distribution_cents",
    "qualified_charitable_distribution_cents", "qcd_to_split_interest_entity",
    "qcd_prior_deducted_ira_contributions_cents",
    "rolled_over_cents", "ira_one_rollover_per_year",
    "reached_minimum_retirement_age", "public_safety_officer", "pso_premiums_paid_by_plan", "pso_premiums_cents",
    "date_of_payment", "box1_is_death_benefit_under_contract",
    "acquired_in_reportable_policy_sale", "acquired_for_valuable_consideration",
    "transfer_has_carryover_basis", "transfer_to_insured_or_related_party",
    "death_benefit_basis_cents",
    "hsa_funding_distribution_transfer_month",
    *[f"hsa_coverage_{m}" for m in ("jan", "feb", "mar", "apr", "may", "jun",
                                    "jul", "aug", "sep", "oct", "nov", "dec")],
    "hsa_testing_period_first_ineligible_month",
    "hsa_medicare_first_month",
    "form_type", "net_benefits_cents",
    "unemployment_compensation_cents", "repaid_cents",
    "other_income_cents", "is_alaska_pfd",
    "gross_distribution_cents", "hsa_distribution_code",
    # the earlier-year rows behind the Form 1040 line 6c election
    "earlier_year", "lump_sum_portion_cents", "benefits_received_cents",
    "adjusted_gross_income_cents", "exclusions_cents", "tax_exempt_interest_cents",
    "taxable_benefits_reported_cents", "filed_jointly", "mfs_lived_with_spouse", "qualified_medical_expenses_cents",
    "hsa_exception_amount_cents", "hsa_exception_reason",
    "hsa_medicare", "hsa_hdhp_coverage", "hsa_hdhp_type", "hsa_other_coverage",
    "hsa_funding_distribution", "hsa_prior_funding_distribution_election",
    "hsa_spouse_contributed", "hsa_marital_status_changed",
    "hsa_marital_change_affects_limit",
    "provider_type", "is_household_employee", "amount_paid_cents", "care_expenses_cents",
    # Form 1095-A's grid and Form 8962's questions.
    "jan_premium_cents", "jan_slcsp_cents", "jan_aptc_cents", "feb_premium_cents", "feb_slcsp_cents", "feb_aptc_cents", "mar_premium_cents", "mar_slcsp_cents", "mar_aptc_cents", "apr_premium_cents", "apr_slcsp_cents", "apr_aptc_cents", "may_premium_cents", "may_slcsp_cents", "may_aptc_cents", "jun_premium_cents", "jun_slcsp_cents", "jun_aptc_cents", "jul_premium_cents", "jul_slcsp_cents", "jul_aptc_cents", "aug_premium_cents", "aug_slcsp_cents", "aug_aptc_cents", "sep_premium_cents", "sep_slcsp_cents", "sep_aptc_cents", "oct_premium_cents", "oct_slcsp_cents", "oct_aptc_cents", "nov_premium_cents", "nov_slcsp_cents", "nov_aptc_cents", "dec_premium_cents", "dec_slcsp_cents", "dec_aptc_cents",
    "allocating_policy_or_alternative_calculation", "marketplace_estimated_income_at_least_100_fpl",
    "below_poverty_line_not_eligible_for_medicaid_due_to_immigration",
    "enrollee_not_eligible_for_marketplace_due_to_immigration", "dependents_modified_agi_cents",
    "mfs_ptc_exception", "mfs_ptc_exception_fourth_year",
    # Form 2441 Part III's questions.
    "self_employed_dependent_care_benefits_cents", "dependent_care_plan_maximum_cents",
    "dependent_care_carryover_cents", "dependent_care_forfeited_cents",
    "paid_prior_year_care_expenses_this_year",
    "prior_year_credit_claimed",
    "prior_year_credit_claimed_maximum",
    "prior_year_form_2441_line_3_cents",
    "prior_year_expenses_paid_this_year_cents",
    "prior_year_had_two_or_more_qualifying_persons",
    "prior_year_excluded_or_deducted_benefits_cents",
    "prior_year_lower_earned_income_cents",
    "prior_year_form_2441_line_6_cents",
    "prior_year_agi_cents",
    "gross_receipts_cents", "returns_and_allowances_cents", "cost_of_goods_sold_cents",
    "other_business_income_cents", "total_expenses_cents", "principal_business_code",
    "materially_participated", "all_investment_at_risk",
    "rents_received_cents", "property_type", "materially_participates_in_lessee",
    "active_participation", "fully_at_risk",
    "amount_at_risk_cents",
    "prior_year_unallowed_loss_cents", "active_participation_when_loss_arose",
    # itemized rental expenses and depreciation inputs.
    "insurance_cents", "management_fees_cents", "repairs_cents", "taxes_cents",
    "building_basis_cents", "is_nonresidential_real_property", "building_uses_standard_gds",
    "placed_in_service_in_current_year", "placed_in_service_month",
    "has_five_year_property", "five_year_property_basis_cents",
    "source", "ordinary_business_income_cents", "interest_income_cents", "dividend_income_cents",
    "royalties_cents", "se_earnings_cents", "basis_cents", "publicly_traded_partnership",
    "guaranteed_payments_services_cents", "guaranteed_payments_capital_cents", "general_partner",
    "qualified_ptp_income_cents", "qualified_ptp_is_sstb",
    "ptp_prior_year_unallowed_loss_cents", "deductible_se_loss_cents", "section_199a_qbi_cents",
    # elections / carryovers
    "itemize_when_lower", "capital_loss_cents", "ira_basis_cents",
})

# Identifier-SHAPED content, caught on the projected payload regardless of what the field is called.
# Belt and braces: classification is by name, and a name can be wrong.
_SHAPES = (
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "a TIN-shaped value"),
    (re.compile(r"\b\d{2}-\d{7}\b"), "an EIN-shaped value"),
    (re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+"), "an email address"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "a full date"),
    (re.compile(r"\b\d{3}-\d{4}\b"), "a phone-shaped value"),
)


# Fields that must be integers. This is the honest control for "a name ended up in a tax field":
# you cannot regex your way to "is this a person's name", but you CAN insist that money is integer
# cents and a year is a number. A string where an integer belongs is wrong whatever it contains.
INTEGER_FIELDS = frozenset({
    "estimated_tax_payments_cents",
    "section_1341_credit_cents",
    "student_loan_interest_cents",
    "student_loan_interest_employer_paid_cents", "student_loan_interest_from_qtp_cents",
    "birth_year", "birth_month", "person", "employer_ref", "tax_year",
    "placed_in_service_month",
}) | {f for f in MAY_CROSS if f.endswith("_cents")}


class PayloadRefused(ValueError):
    """The payload was not sent. Raised instead of quietly removing anything."""


def _walk_values(obj, path=""):
    """Every leaf value with a path whose LEAF NAME IS RECOVERABLE.

    The separator is the whole point. Joining segments with nothing produced `persons[0]birth_year`,
    from which `lint_payload` recovered the CONTAINER name — so the integer check below never fired
    on any nested field, and that check is this module's stated control for "a name ended up in a
    tax field". Found by an adversarial review, 2026-08-12; the live route was an interview answer
    like `birth_year: "May 1980"`, since the document route already requires integer cents.
    """
    if isinstance(obj, dict):
        for k, v in sorted(obj.items()):
            yield from _walk_values(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_values(v, f"{path}[{i}]")
    else:
        yield path, obj


def lint_payload(payload: dict) -> None:
    """Scan a payload that is about to leave the machine. Raises rather than sanitising.

    Sanitising would be the wrong shape: it would let a mistake through in altered form and leave
    the caller believing they sent what they meant to."""
    for path, value in _walk_values(payload):
        # The LEAF name: `w2s[0].wages_cents` -> `wages_cents`. Taking the container instead is how
        # this check silently stopped applying to everything nested.
        key = path.rsplit(".", 1)[-1].split("[")[0]
        # `isinstance(True, int)` is True in Python, so bools must be excluded explicitly — the
        # same trap `operations._tax_year` documents, where `True` would have computed as year 1.
        if key in INTEGER_FIELDS and (isinstance(value, bool) or not isinstance(value, int)):
            raise PayloadRefused(
                f"refusing to send: field {path!r} must be an integer, got "
                f"{type(value).__name__}. "
                f"A non-numeric value in a numeric field is how identity reaches the wire through "
                f"a field nobody thought to classify.")
        if not isinstance(value, str):
            continue
        for pattern, what in _SHAPES:
            if pattern.search(value):
                raise PayloadRefused(
                    f"refusing to send: field {path!r} contains {what}. The cloud never receives "
                    f"identifiers — correct the case rather than stripping the value, so the "
                    f"record and the payload keep saying the same thing.")


def _split(case: dict, payload: dict, overlay: dict, unknown: list, path: str = "") -> None:
    """Walk the real shape, not a flattened one. A fact set is nested — `persons: [...]`,
    `w2s: [...]`, `elections: {...}` — and an identifier hides just as easily inside a list item as
    at the top level. #69 was exactly that: the top level was checked and collection items were not."""
    for key, value in case.items():
        where = f"{path}{key}"
        if key in LOCAL_ONLY:
            overlay[where] = value
        elif key not in MAY_CROSS:
            unknown.append(where)
        elif isinstance(value, list):
            items = []
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    sub_payload, sub_overlay = {}, {}
                    _split(item, sub_payload, sub_overlay, unknown, f"{where}[{i}].")
                    overlay.update(sub_overlay)
                    items.append(sub_payload)
                else:
                    items.append(item)
            payload[key] = items
        elif isinstance(value, dict):
            sub_payload = {}
            _split(value, sub_payload, overlay, unknown, f"{where}.")
            payload[key] = sub_payload
        else:
            payload[key] = value


def project_case(case: dict) -> tuple:
    """Split a local case into (cloud payload, local identity overlay).

    The overlay is returned, never transmitted: it is what the client later stamps into the
    identity fields of the returned forms."""
    payload, overlay, unknown = {}, {}, []
    _split(case, payload, overlay, unknown)

    if unknown:
        raise PayloadRefused(
            f"refusing to send: {', '.join(sorted(unknown))} is not classified as either "
            f"local-only or safe-to-send. An unclassified field is refused rather than dropped — "
            f"a dropped field produces a return computed as if it had never been supplied.")

    lint_payload(payload)
    return payload, overlay
