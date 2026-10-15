# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""What a tab looks like — the single source both the writer and the reader read.

ONE FORM, ONE TAB, ONE COLUMN SPEC. Adding a form is adding a `TABS` entry and its
schema file; it is never editing a shared function.

DECLARED HERE, LOCKED TO THE SCHEMA BY TEST, IN BOTH DIRECTIONS — and never read from the schema
directory at runtime. That is this repo's standing pattern (`interview.CHOICES`,
`mapper.REQUIRED_ITEM_FIELDS`), and it exists because the deployed container ships `src/` +
`generated/` and no schema directory at all: a module that read the schema would work on a
developer's machine and fail in the container. (Said in words rather than as a path, because
`tests/test_workbook_layout.py` scans every module here for exactly such a literal.)

**The money discriminator is the `_cents` suffix, and it is the only rule.** A `_cents` field is
shown as dollars in an ORIGINAL / CURRENT pair. Everything else — `person`, `employer_ref`,
`birth_year`, `birth_month`, `months_in_home`, `distribution_code`, `principal_business_code`, the
booleans, the enums — is written as itself, one column, no conversion.

**Geometry, not flags.** Two header rows (the form's own box caption from `LABELS`, then
`From the form` / `Amount to use` under a money pair), data from row 3, column 1 the item
index, the last column the notes. The reader finds
ORIGINAL by its POSITION, because guard (c) is exactly that a saved workbook comes back with its
column runs compacted and its `hidden` attributes gone. Hiding is cosmetic; position is the
contract.
"""
from __future__ import annotations

import re
from collections import namedtuple

from ..interview import CHOICES, choices_for

Tab = namedtuple("Tab", "name group defname fields")
# kind: "index" | "original" | "current" | "value" | "note"
Column = namedtuple("Column", "field kind index")

HOUSEHOLD = "Household"
RESULT = "Computed return"

HEADER_ROW = 1
SUBHEADER_ROW = 2
FIRST_DATA_ROW = 3
# Rows past the last written one that still carry the dropdowns, so a person adding a second W-2 or
# a spouse gets the same offered codes the writer's own rows got.
SPARE_ROWS = 20

# The persons block floats: the assumptions above it grow and shrink between runs. So it is found by
# its LABEL in column A, and these are the offsets from that marker row.
PERSONS_HEADER_OFFSET = 1
PERSONS_SUBHEADER_OFFSET = 2
PERSONS_DATA_OFFSET = 3

# THE COLUMN'S OWN WORDS. Each one says what the column IS, in the words a
# person reads: where the figure came from, what the service will compute on, which item the
# row is, where the sentence about it lives. `Computed return` names what the tab HOLDS — the
# lines computed, with their citations, the refusals and the assumptions — and claims nothing
# beyond it: not `Review` (running the compute IS the review), and not `Your
# return` (nothing here is filed). Pinned as literals by test in both files.
INDEX_HEADER = "Item"
NOTE_HEADER = "Notes"
ORIGINAL_SUBHEADER = "From the form"
CURRENT_SUBHEADER = "Amount to use"
FIXED_HEADERS = frozenset({INDEX_HEADER, NOTE_HEADER, ORIGINAL_SUBHEADER, CURRENT_SUBHEADER})

# Household's block markers, written in column A and scanned for by the reader.
TAX_YEAR_ROW = "tax_year"
FILING_STATUS_ROW = "filing_status"
ASSUMPTIONS_BLOCK = "assumptions"
PERSONS_BLOCK = "persons"
# root yes/no questions asked on EVERY return, each its own Household row under Filing
# status — found by its label like the two rows above it. The page-1 digital-assets question,
# both parts, in the form's order. A root question asked on some statuses only (the mfs pair, the
# lived-together chain) is not here: it stays a gap said on Computed return, because an unasked
# row a person could fill is a refusal waiting to happen. Locked to `mapper.DIGITAL_ASSET_FIELDS`.
# the residence state joins first — the first ENUM root row (its dropdown is the schema's
# list, through `choices_for_field` like any other choice field). Locked to
# `mapper.EVERY_RETURN_ROOT_FIELDS`.
# Schedule B Part III's three questions join, in the form's order (lines 7a, 8, 8). Locked
# to `mapper.FOREIGN_ACCOUNT_FIELDS` by the layout test, not imported (the client never imports
# the mapper).
# Form 8862's three credit-history questions join, after Schedule B's; locked to
# `mapper.CREDIT_HISTORY_FIELDS` the same way.
ROOT_BOOLEAN_ROWS = ("received_alaska_pfd", "received_digital_assets", "disposed_digital_assets",
                     "foreign_financial_account", "foreign_trust_grantor",
                     "foreign_trust_transactions",
                     "eitc_reduced_or_disallowed", "ctc_odc_reduced_or_disallowed",
                     "qualifying_child_of_another",
                     "paid_estimated_taxes",                                # line 26
                     "estimated_payments_under_different_name",            # reached on a yes
                     "estimated_payments_with_former_spouse",
                     "paid_student_loan_interest", "student_loans_qualify",    # line 21
                     # alimony's two gates — each reached once its own amount is answered
                     # (the money rows below), never on a preceding yes/no of their own.
                     "alimony_received_pre2019_agreement", "alimony_paid_pre2019_agreement",
                     "alimony_paid_section_682_trust",   # reached on a pre-2019 yes
                     "main_home_in_us_over_half_year",   # line 27's childless-EIC main-home test
                     "elects_lump_sum_benefits",               # line 6c, reached on a statement
                     "only_business_is_trading_securities",   # reached on a Schedule C
                     # Form 8962's questions, reached by a Form 1095-A.
                     "allocating_policy_or_alternative_calculation",
                     "marketplace_estimated_income_at_least_100_fpl",
                     "below_poverty_line_not_eligible_for_medicaid_due_to_immigration",
                     "enrollee_not_eligible_for_marketplace_due_to_immigration",
                     "mfs_ptc_exception", "mfs_ptc_exception_fourth_year",
                     "filed_jointly_2023", "filed_jointly_2024",
                     "hsa_excess_in_w2_wages",
                     # Form 2441 Worksheet A's four yes-or-no answers.
                     "paid_prior_year_care_expenses_this_year",
                     "prior_year_credit_claimed",
                     "prior_year_credit_claimed_maximum",
                     "prior_year_had_two_or_more_qualifying_persons",
                     "royalty_is_oil_gas_geothermal")
# the PER-STATUS rows — asked only under the filing status that reaches them (the
# mapper's joint, married, separate and surviving-spouse sets), each a Household row like the
# every-return questions above and the reached rows below. These were once kept OFF the
# sheet ("asked as a gap and said on Computed return when unplaced"), so a joint return typed
# round after round ended NOT COMPLETE with zero located questions, and a workbook seeded from a
# complete fact set LOST these answers on the way through — no married return could reach the
# IRS forms through the shipped client. Joint first (the demo's shape), then the married chain in
# the dictionary's ask order, then the separate-return set, then the surviving-spouse pair. The
# twelve spouse HSA coverage months stay excluded (a month grid, not a question row).
STATUS_ROOT_ROWS = ("spouse_received_alaska_pfd",
                    "lived_with_spouse_all_year", "months_lived_with_spouse",
                    "separation_agreement_on_last_day", "lived_apart_last_six_months",
                    "couple_required_to_file", "couple_files_only_for_refund",
                    "spouse_itemizes", "community_property_domicile",                 # mfs
                    "spouse_files_return", "spouse_had_gross_income",
                    "spouse_can_be_claimed", "spouse_65_or_older", "spouse_is_blind",
                    "spouse_covered_by_employer_plan",
                    "spouse_death_year", "could_have_filed_jointly_year_of_death")    # qss
# root CHOICE rows (a dropdown over the schema's own enum), reached by a W-2's code Q.
ROOT_CHOICE_ROWS = ("combat_pay_election", "cdcc_combat_pay_election",
                    "dependent_care_benefits_combat_pay_election")
# root AMOUNT rows, reached on a yes to the question above each — dollars typed the way a
# form tab's money column is (the reader converts; a cents figure is never typed). Once an
# amount a root yes reached had no Household cell, so a workbook person who paid estimates could
# not finish the flow while the API and the CLI interview could.
ROOT_MONEY_ROWS = ("estimated_tax_payments_cents", "student_loan_interest_cents",
                   "student_loan_interest_employer_paid_cents", "student_loan_interest_from_qtp_cents",
                   "dependents_modified_agi_cents",
                   "dependent_care_carryover_cents", "dependent_care_forfeited_cents",
                   *("prior_year_form_2441_line_3_cents", "prior_year_expenses_paid_this_year_cents", "prior_year_excluded_or_deducted_benefits_cents", "prior_year_lower_earned_income_cents", "prior_year_form_2441_line_6_cents", "prior_year_agi_cents",),
                   "section_1341_credit_cents",
                   "royalty_expenses_cents",
                   "alimony_received_cents", "alimony_paid_cents")
# The rows a yes REACHES (asked on some returns only, under the question that reaches them) —
# every other root row is asked on every return. Locked to the mapper's reach predicates.
REACHED_ROOT_ROWS = ("filed_jointly_2023", "filed_jointly_2024",
                     "hsa_excess_in_w2_wages",
                     *ROOT_CHOICE_ROWS,
                     "estimated_tax_payments_cents", "estimated_payments_under_different_name",
                     "estimated_payments_with_former_spouse",
                     "student_loans_qualify", "student_loan_interest_cents",
                     "student_loan_interest_employer_paid_cents", "student_loan_interest_from_qtp_cents",
                     "alimony_received_pre2019_agreement", "alimony_paid_pre2019_agreement",
                     "alimony_paid_section_682_trust",
                     "elects_lump_sum_benefits",
                     "only_business_is_trading_securities",   # reached on a Schedule C
                     # every Form 8962 row is reached by a Form 1095-A.
                     "allocating_policy_or_alternative_calculation",
                     "marketplace_estimated_income_at_least_100_fpl",
                     "below_poverty_line_not_eligible_for_medicaid_due_to_immigration",
                     "enrollee_not_eligible_for_marketplace_due_to_immigration",
                     "dependents_modified_agi_cents",
                     "mfs_ptc_exception", "mfs_ptc_exception_fourth_year",
                     # Form 2441 lines 13 and 14, reached by a W-2's box 10.
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
                     "royalty_expenses_cents", "royalty_is_oil_gas_geothermal")
# Display order: each reached row sits under its own question.
ROOT_QUESTION_ROWS = ("residence_state", "received_alaska_pfd", "received_digital_assets",
                      "disposed_digital_assets", "foreign_financial_account",
                      "foreign_trust_grantor", "foreign_trust_transactions",
                      "eitc_reduced_or_disallowed", "ctc_odc_reduced_or_disallowed",
                      "qualifying_child_of_another",
                      "paid_estimated_taxes", "estimated_tax_payments_cents",
                      "estimated_payments_under_different_name",
                      "estimated_payments_with_former_spouse",
                      "section_1341_credit_cents",
                      # Schedule 1 lines 2a/19a — each amount, then its own gate.
                      "alimony_received_cents", "alimony_received_pre2019_agreement",
                      "alimony_paid_cents", "alimony_paid_pre2019_agreement",
                      "alimony_paid_section_682_trust",
                      "main_home_in_us_over_half_year",
                      "paid_student_loan_interest", "student_loans_qualify",
                      "student_loan_interest_cents",
                      "student_loan_interest_employer_paid_cents", "student_loan_interest_from_qtp_cents",
                      "elects_lump_sum_benefits",
                      "only_business_is_trading_securities",   # reached on a Schedule C
                      # Form 8962's questions in the ask order — line 9's gate, the
                      # below-poverty pair, the enrollment-family question, line 2b, and the
                      # separate-return exception last (sensitive, single-purpose).
                      "allocating_policy_or_alternative_calculation",
                      "marketplace_estimated_income_at_least_100_fpl",
                      "below_poverty_line_not_eligible_for_medicaid_due_to_immigration",
                      "enrollee_not_eligible_for_marketplace_due_to_immigration",
                      "dependents_modified_agi_cents",
                      "mfs_ptc_exception", "mfs_ptc_exception_fourth_year",
                      # Form 2441 lines 13 and 14, in the form's order.
                      "dependent_care_carryover_cents", "dependent_care_forfeited_cents",
                      # Form 2441 Worksheet A, in the worksheet's order.
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
                      # the royalty activity's expenses, then the oil/gas classification.
                      "royalty_expenses_cents", "royalty_is_oil_gas_geothermal",
                      # Form 8880's filed-jointly pair, reached by a prior-year distribution.
                      "filed_jointly_2023", "filed_jointly_2024",
                      "hsa_excess_in_w2_wages",
                      # the combat pay elections, in the dictionary's ask order, last.
                      *ROOT_CHOICE_ROWS,
                      # the per-status questions, after everything asked of every return.
                      *STATUS_ROOT_ROWS)

# Rows on Household that are NOT fact-schema fields. `tax_year` is the request envelope's year, not
# a fact — the root fact schema has no such property, and the lock excludes it by name here rather
# than by a special case buried in the test.
STATED_ROWS = (TAX_YEAR_ROW,)

PERSONS = Tab(name=HOUSEHOLD, group="persons", defname="person",
              fields=("role", "birth_year", "birth_month", "tin_type", "relationship",
                      "months_in_home", "is_student", "is_permanently_disabled",
                      "unable_to_care_for_self",
                      "is_married",
                      # the joint-return test, beside the married question it hangs off.
                      "files_joint_return_with_spouse", "required_to_file_with_spouse",
                      "joint_return_only_for_refund",
                      "provided_own_support", "gross_income_under_limit",
                      "filer_provided_over_half_support",
                      "could_be_qualifying_child_of_another",
                      # the split gate's custody questions, before the other-parent
                      # question they open.
                      "child_residence_state", "child_emancipated",
                      "child_emancipated_after_july_2",
                      # the member-of-household questions.
                      "was_spouse_during_year", "relationship_violates_local_law",
                      "has_other_biological_or_adoptive_parent",
                      # the benefit-split gate, beside the other-parent question it
                      # hangs off.
                      "parents_situation", "child_in_parents_custody",
                      "child_lived_with_parents_over_half_year",
                      "parents_provided_over_half_support", "written_declaration",
                      # the custodial-parent questions, after the declaration they hang off.
                      "nights_with_filer_vs_other_parent", "filer_agi_higher_than_other_parent",
                      # the non-parental arm's first question, after the split gate.
                      "child_parents_living",
                      # the non-parental split's links (custody is the column above).
                      "parents_meet_divorced_or_separated_rule", "a_parent_signed_declaration_not_to_claim",
                      "custodial_parent_claims_child_as_qualifying_person",
                      "filer_agi_higher_than_custodial_parent",
                      # Form 1040 line 12's blindness checkbox, per filer row.
                      "is_blind",
                      # the educator question on every filer row and the amount a yes
                      # reaches — the persons block's one money column.
                      "k12_educator", "educator_expenses_cents",
                      # the IRA question and the two answers a yes reaches.
                      "made_ira_contributions", "traditional_ira_contributions_cents",
                      "contributed_to_inherited_ira", "inherited_ira_contribution_cents",
                      # the own-HSA-contribution question and the two amounts a yes reaches.
                      "made_hsa_contributions", "hsa_own_contributions_cents",
                      "hsa_own_contributions_after_year_end_cents",
                      "hsa_prior_year_excess_cents",
                      "hsa_december_31_value_cents",
                      # the Roth-and-ABLE follow-up and Form 8880's questions.
                      "roth_ira_and_able_contributions_cents",
                      "roth_ira_contributions_cents",
                      "received_retirement_distributions_2023_2024",
                      "retirement_distributions_2023_cents", "retirement_distributions_2024_cents",
                      "received_retirement_distributions_after_year_end",
                      "retirement_distributions_after_year_end_cents",
                      # the HSA 20%-tax exception pair, reached by the 1099-SA tab.
                      "hsa_exception_amount_cents", "hsa_exception_reason",
                      # Form 8889 Part I's questions, in the ask order.
                      "hsa_medicare", "hsa_medicare_first_month", "hsa_hdhp_coverage", "hsa_hdhp_type",
                      # the twelve coverage months, in the schema's order.
                      "hsa_coverage_jan",
                      "hsa_coverage_feb",
                      "hsa_coverage_mar",
                      "hsa_coverage_apr",
                      "hsa_coverage_may",
                      "hsa_coverage_jun",
                      "hsa_coverage_jul",
                      "hsa_coverage_aug",
                      "hsa_coverage_sep",
                      "hsa_coverage_oct",
                      "hsa_coverage_nov",
                      "hsa_coverage_dec",
                      "hsa_other_coverage",
                      "hsa_funding_distribution", "hsa_prior_funding_distribution_election",
                      "qcd_prior_deducted_ira_contributions_cents",
                      "hsa_funding_distribution_transfer_month",
                      "hsa_testing_period_first_ineligible_month",
                      "hsa_spouse_contributed",
                      "hsa_marital_status_changed", "hsa_marital_change_affects_limit",
                      # Form 2441 line 2 column (d), on a qualifying person's row.
                      "care_expenses_cents",
                      # Form 2441 Part III on a filer row, reached by the W-2 tab's box 10.
                      "self_employed_dependent_care_benefits_cents",
                      "dependent_care_plan_maximum_cents",
                      # the page-1 "someone can claim you" chain, beside the other checkbox.
                      "someone_can_claim_you", "expect_to_be_claimed",
                      "potential_claimer_must_file", "potential_claimer_filed",
                      "potential_claimer_filed_only_for_refund",
                      "filer_paid_most_of_home_upkeep"))

TABS = (
    Tab("W-2", "w2s", "w2",
        ("person", "wages_cents", "withholding_cents", "social_security_wages_cents",
         "medicare_wages_cents", "social_security_withheld_cents",
         "medicare_withheld_cents",                                      # box 6
         "dependent_care_benefits_cents",                                # box 10
         # box 12, one column per code the form lists (A first, II last).
         "box12_a_cents", "box12_b_cents", "box12_c_cents", "box12_d_cents", "box12_e_cents", "box12_f_cents", "box12_g_cents", "box12_g_governmental_plan", "box12_h_cents", "box12_j_cents", "box12_k_cents", "box12_l_cents", "box12_m_cents", "box12_n_cents", "box12_p_cents", "box12_q_cents", "box12_r_cents", "box12_s_cents", "box12_t_cents", "box12_v_cents", "box12_w_cents", "box12_y_cents", "box12_z_cents", "box12_aa_cents", "box12_bb_cents", "box12_dd_cents", "box12_ee_cents", "box12_ff_cents", "box12_gg_cents", "box12_hh_cents", "box12_ii_cents",
         # box 13's three checkboxes, asked on every W-2.
         "statutory_employee", "retirement_plan", "third_party_sick_pay",
         "has_rrta_codes",                                              # box 14 RRTA
         "employer_ref")),
    Tab("1099-INT", "int1099s", "int1099",
        ("person", "interest_cents", "government_interest_cents", "tax_exempt_interest_cents",
         "federal_withholding_cents", "early_withdrawal_penalty_cents",
         "private_activity_bond_interest_cents", "market_discount_cents", "bond_premium_cents",
         "treasury_bond_premium_cents", "tax_exempt_bond_premium_cents")),
    Tab("1099-OID", "oid1099s", "oid1099",
        ("person", "original_issue_discount_cents", "other_periodic_interest_cents",
         "early_withdrawal_penalty_cents", "federal_withholding_cents", "market_discount_cents",
         "acquisition_premium_cents", "treasury_oid_cents", "bond_premium_cents",
         "tax_exempt_oid_cents", "box2_is_tax_exempt", "fatca_filing_requirement")),
    Tab("1099-B", "b1099s", "b1099",
        ("person", "date_acquired", "date_sold", "proceeds_cents", "cost_basis_cents",
         "accrued_market_discount_cents", "wash_sale_loss_disallowed_cents", "term",
         "federal_withholding_cents", "collectibles", "qualified_opportunity_fund",
         "loss_not_allowed", "basis_reported_to_irs")),
    Tab("1099-DIV", "div1099s", "div1099",
        ("person", "ordinary_dividends_cents", "qualified_dividends_cents",
         "capital_gain_distributions_cents", "unrecaptured_1250_gain_cents",
         "federal_withholding_cents", "section_199a_dividends_cents",
         "exempt_interest_dividends_cents")),
    Tab("1099-R", "r1099s", "r1099",
        ("person", "gross_distribution_cents", "taxable_amount_cents",
         "taxable_amount_not_determined", "distribution_code", "ira_sep_simple",
         "federal_withholding_cents",
         "other_cents", "other_percentage", "percentage_of_total_distribution",
         "qualified_hsa_funding_distribution_cents",
         "qualified_charitable_distribution_cents", "qcd_to_split_interest_entity",
         "rolled_over_cents", "ira_one_rollover_per_year",
         "reached_minimum_retirement_age", "public_safety_officer", "pso_premiums_paid_by_plan", "pso_premiums_cents",
         "date_of_payment", "box1_is_death_benefit_under_contract",
         "acquired_in_reportable_policy_sale", "acquired_for_valuable_consideration",
         "transfer_has_carryover_basis", "transfer_to_insured_or_related_party",
         "death_benefit_basis_cents")),
    Tab("W-2G", "w2gs", "w2g",
        ("person", "winnings_cents", "federal_withholding_cents")),
    # the benefit statement. The form-type column comes FIRST (the cheap gate before
    # the amounts), because SSA-1099 and RRB-1099 number these boxes differently, so the shared
    # columns carry the caption without its number.
    Tab("SSA-1099", "ssa1099s", "ssa1099",
        ("person", "form_type", "net_benefits_cents", "federal_withholding_cents")),
    # Form 1099-G, unemployment compensation. The same-year repayment is the Schedule 1
    # line 7 entry space, not a box, so it sits last, after the form's own boxes.
    Tab("1099-G", "g1099s", "g1099",
        ("person", "unemployment_compensation_cents", "federal_withholding_cents",
         "repaid_cents")),
    # Form 1099-MISC, box 3 (other income); box 2 (royalties) joined in The Alaska
    # PFD question is the engine's own per-form question, asked beside the box it is about; box 2
    # first (the form's own printed order), the royalty activity's other two answers at the root.
    Tab("1099-MISC", "misc1099s", "misc1099",
        ("person", "royalties_cents", "other_income_cents", "is_alaska_pfd",
         "federal_withholding_cents")),
    # Form 1099-SA. The code before the expenses (the cheap gate before the entry): a
    # code other than 1 is the engine's own knockout, and the expenses are Form 8889 line 15,
    # the filer's own figure.
    Tab("1099-SA", "hsa_distributions", "hsa_distribution",
        ("person", "gross_distribution_cents", "hsa_distribution_code",
         "qualified_medical_expenses_cents")),
    # Publication 915 Worksheet 2 and 3 — one row per earlier year a lump-sum payment is
    # for, no person column (the election is the return's, Form 1040 line 6c). The year first: it
    # picks the worksheet the engine refigures with, and it bounds what the other columns mean.
    Tab("Lump-sum years", "ssa_lump_sum_years", "ssa_lump_sum_year",
        ("earlier_year", "lump_sum_portion_cents", "benefits_received_cents",
         "adjusted_gross_income_cents", "exclusions_cents", "tax_exempt_interest_cents",
         "taxable_benefits_reported_cents", "filed_jointly", "mfs_lived_with_spouse")),
    # Form 2441 line 1 — one row per care provider, no person column (a provider is the
    # return's). The household-employee column before the amount: a yes is the engine's own
    # knockout (the cheap gate before the entry).
    Tab("Form 2441", "care_providers", "care_provider",
        ("provider_type", "is_household_employee", "amount_paid_cents")),
    # Form 1095-A Part III — the form's own grid, one column per cell (lines 21-32 by
    # month, columns A, B, C), no person column (a policy is the return's).
    Tab("1095-A", "f1095as", "f1095a",
        ("jan_premium_cents", "jan_slcsp_cents", "jan_aptc_cents",
         "feb_premium_cents", "feb_slcsp_cents", "feb_aptc_cents",
         "mar_premium_cents", "mar_slcsp_cents", "mar_aptc_cents",
         "apr_premium_cents", "apr_slcsp_cents", "apr_aptc_cents",
         "may_premium_cents", "may_slcsp_cents", "may_aptc_cents",
         "jun_premium_cents", "jun_slcsp_cents", "jun_aptc_cents",
         "jul_premium_cents", "jul_slcsp_cents", "jul_aptc_cents",
         "aug_premium_cents", "aug_slcsp_cents", "aug_aptc_cents",
         "sep_premium_cents", "sep_slcsp_cents", "sep_aptc_cents",
         "oct_premium_cents", "oct_slcsp_cents", "oct_aptc_cents",
         "nov_premium_cents", "nov_slcsp_cents", "nov_aptc_cents",
         "dec_premium_cents", "dec_slcsp_cents", "dec_aptc_cents")),
    Tab("Schedule C", "schedule_c", "schedule_c_activity",
        ("person", "gross_receipts_cents", "returns_and_allowances_cents",
         "cost_of_goods_sold_cents", "other_business_income_cents", "total_expenses_cents",
         "principal_business_code", "materially_participated", "all_investment_at_risk",
         "amount_at_risk_cents")),
    Tab("Rental", "rentals", "rental",
        ("person", "rents_received_cents", "total_expenses_cents",
         # the itemized expense lines and depreciation inputs, in the schema's own order.
         "insurance_cents", "management_fees_cents", "repairs_cents", "taxes_cents",
         "building_basis_cents", "is_nonresidential_real_property", "building_uses_standard_gds",
         "placed_in_service_in_current_year", "placed_in_service_month",
         "has_five_year_property", "five_year_property_basis_cents",
         "property_type",
         "materially_participates_in_lessee",
         "active_participation", "fully_at_risk", "amount_at_risk_cents",
         "prior_year_unallowed_loss_cents", "active_participation_when_loss_arose")),
    Tab("K-1", "k1s", "k1",
        ("person", "source", "ordinary_business_income_cents", "interest_income_cents",
         "dividend_income_cents", "qualified_dividends_cents", "royalties_cents",
         "se_earnings_cents", "deductible_se_loss_cents",
         "publicly_traded_partnership", "materially_participated",
         "basis_cents", "fully_at_risk", "amount_at_risk_cents",
         "guaranteed_payments_services_cents",
         "guaranteed_payments_capital_cents", "general_partner",
         "qualified_ptp_income_cents", "qualified_ptp_is_sstb",
         "ptp_prior_year_unallowed_loss_cents", "section_199a_qbi_cents")),
)

# Root groups with NO tab, each with the reason written down. They are OBJECTS, not arrays — one
# set of switches, not a list of documents — so there is no row to put them on, and the mapper
# refuses both outright (`UNSUPPORTED_FACT_GROUPS`), so a column offering them would collect a value
# whose only possible destination is a named refusal. Declared rather than omitted, because a group
# that is simply missing from a list is indistinguishable from one somebody forgot.
EXCLUDED_GROUPS = {
    # The per-status root questions (joint, married, separate, surviving spouse) were once listed
    # here; they are Household rows now — `STATUS_ROOT_ROWS`.
    **{f"spouse_hsa_coverage_{m}": ("a separate-return question, not a document; asked as a gap "
                                    "and said on Computed return when unplaced")
       for m in ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")},
    "elections": ("an object of switches rather than a collection of documents, and the mapper "
                  "refuses it outright (UNSUPPORTED_FACT_GROUPS) — a column for it would collect a "
                  "value whose only destination is a refusal"),
    "carryovers": ("carried-in amounts are an object rather than a collection of documents, and "
                   "the mapper refuses the group outright (UNSUPPORTED_FACT_GROUPS) — the same "
                   "reason as elections, written out rather than shared"),
}

# The two enums the interview does not carry, declared here and locked by test to the person and
# rental form schemas, exactly as CHOICES is.
BIRTH_MONTH_CHOICES = tuple(str(month) for month in range(1, 13))
PROPERTY_TYPES = ("residential", "commercial", "land", "self_rental", "other")

# the date-shaped fields — Form 1099-B boxes 1b and 1c, YYYY-MM-DD strings on the wire. A
# person who types a date into the cell gets a spreadsheet date (a day serial), which the reader
# turns back into that string.
DATE_FIELDS = frozenset({"date_acquired", "date_sold"})
BOOLEAN_FIELDS = frozenset({"is_student", "is_permanently_disabled", "is_blind", "k12_educator",
                            # the per-status yes/no rows (the two enums are dropdowns).
                            "spouse_received_alaska_pfd", "lived_with_spouse_all_year",
                            "separation_agreement_on_last_day", "lived_apart_last_six_months",
                            "couple_required_to_file", "couple_files_only_for_refund",
                            "spouse_itemizes", "community_property_domicile",
                            "spouse_files_return", "spouse_had_gross_income",
                            "spouse_can_be_claimed", "spouse_65_or_older", "spouse_is_blind",
                            "spouse_covered_by_employer_plan", "could_have_filed_jointly_year_of_death",
                            "filed_jointly", "mfs_lived_with_spouse",
                            "paid_prior_year_care_expenses_this_year",
                            "prior_year_credit_claimed",
                            "prior_year_credit_claimed_maximum",
                            "prior_year_had_two_or_more_qualifying_persons",
                            "unable_to_care_for_self",
                            "made_ira_contributions", "contributed_to_inherited_ira",
                            "made_hsa_contributions",
                            "received_retirement_distributions_2023_2024",
                            "received_retirement_distributions_after_year_end",
                            "filed_jointly_2023", "filed_jointly_2024", "box12_g_governmental_plan",
                            "hsa_funding_distribution", "hsa_prior_funding_distribution_election", "hsa_spouse_contributed",
                            "hsa_marital_status_changed", "hsa_marital_change_affects_limit",
                            "hsa_excess_in_w2_wages",
                            "taxable_amount_not_determined", "ira_sep_simple", "qcd_to_split_interest_entity",
                            "ira_one_rollover_per_year",
                            "reached_minimum_retirement_age", "public_safety_officer", "pso_premiums_paid_by_plan",
                            "box1_is_death_benefit_under_contract", "acquired_in_reportable_policy_sale",
                            "acquired_for_valuable_consideration", "transfer_has_carryover_basis",
                            "transfer_to_insured_or_related_party",
                            "is_alaska_pfd",
                            "royalty_is_oil_gas_geothermal",
                            "is_household_employee",
                            "materially_participated", "all_investment_at_risk",
                            "active_participation", "fully_at_risk",
                            "active_participation_when_loss_arose",
                            "materially_participates_in_lessee",
                            # the rental depreciation-input booleans.
                            "is_nonresidential_real_property", "building_uses_standard_gds",
                            "placed_in_service_in_current_year", "has_five_year_property",
                            "publicly_traded_partnership", "general_partner",
                            "qualified_ptp_is_sstb",
                            "is_married", "provided_own_support", "gross_income_under_limit",
                            "filer_provided_over_half_support",
                            "could_be_qualifying_child_of_another",
                            "has_other_biological_or_adoptive_parent",
                            "child_emancipated", "child_emancipated_after_july_2",
                            "was_spouse_during_year", "relationship_violates_local_law",
                            # the benefit-split gate's three Booleans (its two enums
                            # come from `interview.CHOICES` like every other dropdown).
                            "child_in_parents_custody",
                            "child_lived_with_parents_over_half_year",
                            "parents_provided_over_half_support",
                            "child_parents_living",
                            "filer_agi_higher_than_other_parent",
                            "parents_meet_divorced_or_separated_rule",
                            "a_parent_signed_declaration_not_to_claim",
                            "custodial_parent_claims_child_as_qualifying_person",
                            "filer_agi_higher_than_custodial_parent",
                            "someone_can_claim_you", "expect_to_be_claimed",
                            "potential_claimer_must_file", "potential_claimer_filed",
                            "potential_claimer_filed_only_for_refund",
                            "files_joint_return_with_spouse",
                            "required_to_file_with_spouse", "joint_return_only_for_refund",
                            "filer_paid_most_of_home_upkeep",
                            "statutory_employee", "retirement_plan",   # W-2 box 13
                            "third_party_sick_pay",
                            "has_rrta_codes",                          # W-2 box 14
                            "box2_is_tax_exempt", "fatca_filing_requirement",   # Form 1099-OID
                            "collectibles", "qualified_opportunity_fund",       # Form 1099-B
                            "loss_not_allowed", "basis_reported_to_irs",
                            *ROOT_BOOLEAN_ROWS})
BOOLEAN_CHOICES = ("true", "false")

_ITEM_PATH = re.compile(r"^([a-z][a-z0-9_]*)\[(\d+)\]\.([a-z][a-z0-9_]*)$")


def is_money(field: str) -> bool:
    """The whole rule. One suffix, no table, nothing to keep in step with anything."""
    return field.endswith("_cents")


def choices_for_field(field: str):
    """The codes a dropdown offers, in the schema's order, or None for a free field.

    `filing_status`, `role`, `tin_type` and `source` come straight from `interview.CHOICES`, which
    `tests/test_interview.py` already locks to the schema in both directions — so this is the
    schema's vocabulary and not a second copy of it."""
    if field in CHOICES:
        return tuple(choices_for(field))
    if field == "birth_month":
        return BIRTH_MONTH_CHOICES
    if field == "property_type":
        return PROPERTY_TYPES
    if field in BOOLEAN_FIELDS:
        return BOOLEAN_CHOICES
    return None


def columns_for(tab: Tab) -> tuple:
    """The tab's columns, left to right. A money field takes TWO — ORIGINAL then CURRENT."""
    columns = [Column(None, "index", 1)]
    index = 2
    for field in tab.fields:
        if is_money(field):
            columns.append(Column(field, "original", index))
            columns.append(Column(field, "current", index + 1))
            index += 2
        else:
            columns.append(Column(field, "value", index))
            index += 1
    columns.append(Column(None, "note", index))
    return tuple(columns)


def column_index(tab: Tab, field: str, kind: str) -> int:
    """The 1-based column for one field in one role. Raises KeyError rather than returning a
    plausible neighbour — a fact written one column left is a wrong return that looks finished."""
    for column in columns_for(tab):
        if column.field == field and column.kind == kind:
            return column.index
    raise KeyError(f"{tab.name} has no {kind!r} column for {field!r}")


def note_index(tab: Tab) -> int:
    return columns_for(tab)[-1].index


def tab_for_group(group: str):
    for tab in TABS:
        if tab.group == group:
            return tab
    return PERSONS if group == PERSONS.group else None


def split_path(path: str):
    """`w2s[0].wages_cents` -> `("w2s", 0, "wages_cents")`, or None if it is not an item path.

    The one spelling, matching `documents._path`, so a gap, a refusal and a cell all mean the same
    thing by the same string."""
    match = _ITEM_PATH.match(path)
    return None if match is None else (match.group(1), int(match.group(2)), match.group(3))


def holds(path: str) -> bool:
    """Does this workbook have a cell for that fact path? A refusal naming a path it does NOT hold
    goes to the Computed return tab unattributed, rather than being pinned to the wrong cell."""
    if path == FILING_STATUS_ROW or path in ROOT_QUESTION_ROWS:
        return True
    parts = split_path(path)
    if parts is None:
        return False
    group, _index, field = parts
    tab = tab_for_group(group)
    return tab is not None and field in tab.fields


# ---------------------------------------------------------------------------
# THE FORM'S OWN WORDS. The header a person reads is the box caption printed on the
# IRS form — `1 Wages, tips, other compensation` — and never the schema's field name. The table
# lives one level up, in `client/form_labels.py`, because `documents.py` asks about an unread box
# in the same words; it is imported here, not copied, so the two surfaces cannot drift. Every label
# is authored text (it reaches a sheet) and is scanned by the advice and identifier locks.

# PEOPLE COUNT FROM 1. Everything a person READS or TYPES is 1-based — the `Item` column, the
# person column, a row named in a message — and the fact path's index on the wire stays 0-based.
# `row_number` is the one place the two meet; the reader undoes it on the way in.
from ..form_labels import HOUSEHOLD_GROUP, LABELS, PERSON_LABEL  # noqa: F401  (re-exported)
from ..form_labels import label_for as _caption


def row_number(index: int) -> int:
    """The number a person sees for the item at this 0-based index: `w2s[0]` is `W-2 #1`."""
    return index + 1


def _group_of(group_or_tab) -> str:
    """A `Tab`, a fact group (`w2s`), a tab name (`W-2`), or Household, to the LABELS group key."""
    if isinstance(group_or_tab, Tab):
        return group_or_tab.group
    if group_or_tab in (HOUSEHOLD, HOUSEHOLD_GROUP):
        return HOUSEHOLD_GROUP
    for tab in TABS + (PERSONS,):
        if group_or_tab in (tab.group, tab.name):
            return tab.group
    raise KeyError(f"no tab, group or Household row set named {group_or_tab!r}")


def label_for(group_or_tab, field: str) -> str:
    """The caption a person reads over this field — a `Tab`, a group, a tab name or Household
    resolved to the table's group key. Raises KeyError rather than falling back to the field name:
    a header that quietly said `wages_cents` is the defect this table exists to end."""
    group = _group_of(group_or_tab)
    if group == HOUSEHOLD_GROUP and (group, field) not in LABELS:
        group = PERSONS.group                  # the persons block lives on the Household tab
    return _caption(group, field)


def describe(path: str) -> str:
    """A fact path in the form's words — `w2s[0].wages_cents` as
    `W-2 #1 · 1 Wages, tips, other compensation` — for a refusal and for the terminal. The number is
    the sheet's own `Item` column (people count from 1), so the message and the column agree. A path
    this workbook holds no cell for comes back AS ITSELF: nothing is invented for it."""
    if path in (TAX_YEAR_ROW, FILING_STATUS_ROW) or path in ROOT_QUESTION_ROWS:
        return ROOT_TEMPLATE.format(tab=HOUSEHOLD, label=label_for(HOUSEHOLD_GROUP, path))
    parts = split_path(path)
    if parts is None:
        return path
    group, index, field = parts
    tab = tab_for_group(group)
    if tab is None or field not in tab.fields:
        return path
    return ROW_FIELD_TEMPLATE.format(row=describe_row(group, index), label=label_for(tab, field))


def describe_row(group: str, index: int) -> str:
    """One item as a person counts it — `W-2 #1` for `w2s[0]`, `Household · person #2` for
    `persons[1]` — for a refusal about a row rather than a cell."""
    tab = tab_for_group(group)
    if tab is PERSONS:
        return PERSON_ITEM_TEMPLATE.format(tab=HOUSEHOLD, number=row_number(index))
    return ITEM_TEMPLATE.format(tab=tab.name, number=row_number(index))


# ---------------------------------------------------------------------------
# Every string this workbook AUTHORS. Text quoted from the library (a question, an assumption, a
# refusal) is provenance and is not listed here; this is the vocabulary the workbook invents, and it
# is scanned for advice by test. Provenance language only — no advice, no recommendation, and
# nothing that names a product.
BLOCK_ASSUMPTIONS = "assumptions stated by the service on the last run"
BLOCK_PERSONS = "persons on this return"
BLOCK_HOUSEHOLD = "household"
NO_RUN_YET = "no run yet — this tab is written by `run`"
NO_ASSUMPTIONS = "none stated"
RESULT_OUTCOME = "outcome"
RESULT_STOPPED = "stopped because"
RESULT_PROVENANCE = "provenance"
RESULT_LINES = "form lines"
RESULT_REFUSALS = "refusals and knockouts"
RESULT_BOUNDARY = "what this service cannot ask for"
RESULT_ASSUMPTIONS = "assumptions"
# Gaps the service named that pin no cell in this workbook — a root path, a field no tab holds. They
# are written here so a gap never vanishes between the response and the sheet.
RESULT_GAPS = "gaps named by the service with no cell to hold them"
# WHERE each open question is — the block a person reads first after a round that did not
# complete. A cell is named the way Excel's own Name Box reads it (`Household!B54`, `'W-2'!D3`),
# so the text typed there lands on the cell; a grid cell adds the row as the `Item` column counts
# it and the column's caption, so the far-right cell on a wide block is found by its heading.
RESULT_OPEN = "open questions — where each one is on this workbook"
GRID_LOCATION = "{at} — {row} row, column “{caption}”"
ROW_LOCATION = "{first}:{last} — {row} row"
STATED_TEMPLATE = "stated as {value} on {when}"
# How the note column is assembled. Format rather than prose — what they JOIN is the library's own
# question, quoted verbatim — but they are strings this file authors and they reach a sheet, so they
# are scanned with the rest of the authored text rather than exempted for carrying no words. An
# exemption is a judgement somebody has to re-make every time a constant is added; membership is
# not. Declared here because both directions need the one spelling: the writer joins with them and
# `run` re-writes the same column against them.
NOTE_TEMPLATE = "{label}: {note}"
NOTE_SEPARATOR = " | "
# How a row and a cell are NAMED to a person — in a refusal, and on the terminal. `W-2 #1`;
# `Household · person #2`; then `W-2 #1 · 1 Wages, tips, other compensation`; `Household · Tax
# year`. The number is the sheet's `Item` column (people count from 1). `REFUSAL_TEMPLATE` wraps one
# of them with the cell and the reason: `W-2 #1 · 1 Wages, tips, other compensation (cell D3):
# "abc" is not an amount`.
ITEM_TEMPLATE = "{tab} #{number}"
PERSON_ITEM_TEMPLATE = "{tab} · person #{number}"
ROW_FIELD_TEMPLATE = "{row} · {label}"
ROOT_TEMPLATE = "{tab} · {label}"
REFUSAL_TEMPLATE = "{where} (cell {ref}): {why}"
GAP_ROW_CREATED = "this row was named by the service and had no row in the sheet; it was added here"
# The forms a person RECEIVES on paper, each by its own name, in the tabs' order: the list the page
# asks "how many more?" about once the documents are read (decided 2026-09-28). A tab for a
# figure the person works out themselves (Schedule C, Rental, Form 2441, Lump-sum years) is not a
# form anyone hands them, so it is not on the list; those stay asked on the page.
RECEIVED_FORMS = (
    ("w2s", "Form W-2"), ("int1099s", "Form 1099-INT"), ("oid1099s", "Form 1099-OID"),
    ("b1099s", "Form 1099-B"), ("div1099s", "Form 1099-DIV"), ("r1099s", "Form 1099-R"),
    ("w2gs", "Form W-2G"), ("ssa1099s", "Form SSA-1099 or RRB-1099"), ("g1099s", "Form 1099-G"),
    ("misc1099s", "Form 1099-MISC"), ("hsa_distributions", "Form 1099-SA"),
    ("f1095as", "Form 1095-A"), ("k1s", "Schedule K-1"),
)
# The note on each row the page added for a form the person said they have (a count above 0).
ADDED_ROW_NOTE = ("A row for a {form} you said you have: type its boxes here. A yellow box is one "
                  "the return needs. Fill rows from the top; a row left empty is not used.")
# `run`'s own reasons for a round that produced no response. The loop's reasons (`pass_limit`,
# `terminal_outcome`) are its vocabulary and are quoted; these three are this surface's, so they are
# authored, listed, and scanned like every other word it invents.
STOPPED_READER_REFUSED = "reader_refused"
STOPPED_TRANSPORT_REFUSED = "transport_refused"
STOPPED_UNREACHABLE = "service_unreachable"
STOPPED_LOOP_REFUSED = "loop_refused"
STOPPED_PAYLOAD_REFUSED = "payload_refused"
# The write-back's refusal of a gap past the next free row — `loop._set_fact`'s rule, said on this
# side in the same words, because filling the row would leave the entries between empty.
# Said in the person's numbers (`W-2 #5`, the tab's name), never as the wire's `w2s[4]`.
BEYOND_NEXT_SLOT = ("the service named {where}, which is beyond the next free slot ({tab} holds "
                    "{count}). Filling it would leave the entries between them empty, and an empty "
                    "entry is an entity the return computes as absent.")

# The Computed return tab's block titles — the reader stops a block at the next one of these.
RESULT_TITLES = (RESULT_OUTCOME, RESULT_STOPPED, RESULT_PROVENANCE, RESULT_LINES, RESULT_REFUSALS,
                 RESULT_BOUNDARY, RESULT_ASSUMPTIONS, RESULT_GAPS, RESULT_OPEN)

_PLAIN_SHEET_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")


def sheet_ref(sheet: str, ref: str) -> str:
    """`Household!B54`, `'W-2'!D3` — a sheet-qualified reference in the form Excel's Name Box and
    formulas read: a name that is not a plain word is quoted, a quote inside it doubled."""
    name = sheet if _PLAIN_SHEET_NAME.fullmatch(sheet) else "'" + sheet.replace("'", "''") + "'"
    return f"{name}!{ref}"


AUTHORED_TEXT = (
    INDEX_HEADER, NOTE_HEADER, ORIGINAL_SUBHEADER, CURRENT_SUBHEADER,
    TAX_YEAR_ROW, FILING_STATUS_ROW, ASSUMPTIONS_BLOCK, PERSONS_BLOCK, *ROOT_QUESTION_ROWS,
    HOUSEHOLD, RESULT,
    BLOCK_ASSUMPTIONS, BLOCK_PERSONS, BLOCK_HOUSEHOLD, NO_RUN_YET, NO_ASSUMPTIONS,
    RESULT_OUTCOME, RESULT_STOPPED, RESULT_PROVENANCE, RESULT_LINES, RESULT_REFUSALS,
    RESULT_BOUNDARY, RESULT_ASSUMPTIONS, RESULT_GAPS, RESULT_OPEN, GRID_LOCATION, ROW_LOCATION,
    STATED_TEMPLATE, GAP_ROW_CREATED, ADDED_ROW_NOTE,
    *(words for _group, words in RECEIVED_FORMS),
    NOTE_TEMPLATE, NOTE_SEPARATOR,
    ITEM_TEMPLATE, PERSON_ITEM_TEMPLATE, ROW_FIELD_TEMPLATE, ROOT_TEMPLATE, REFUSAL_TEMPLATE,
    STOPPED_READER_REFUSED, STOPPED_TRANSPORT_REFUSED, STOPPED_LOOP_REFUSED,
    STOPPED_PAYLOAD_REFUSED, STOPPED_UNREACHABLE, BEYOND_NEXT_SLOT,
    # Every caption, once each (the shared withholding caption and the person label repeat across
    # tabs), so each is scanned for advice and for identifier shape with the rest.
    *dict.fromkeys(LABELS.values()),
)
