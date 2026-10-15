# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The form's own words — one caption per fact field, shared by every surface that speaks to a person.

THE RULE is the rule for cents applied to vocabulary: the internal format
never reaches the person. A header, a note, a refusal, a question about a box the Collector could
not read — each names the box by the caption printed on the IRS form, `1 Wages, tips, other
compensation`, and never by the schema's `wages_cents`.

This module sits at the client level, above `workbook/` and beside `documents.py`, because both
import it: the workbook heads its columns with these words and `documents._question` asks about an
unread box in them. It imports nothing of its own, so it can never be the far end of a cycle.

Keyed `(group, field)`; `("household", …)` for the workbook's two Household rows. Locked by
`tests/test_workbook_layout.py` to `layout.TABS` + `layout.PERSONS` in BOTH directions (every field
has a caption; no caption for a field that does not exist) and to `documents.FACT_GROUPS` (every box
the Collector maps can be asked about in the form's words). The FORM captions are pinned verbatim
by test — they were verified against the IRS forms for ty2025 (irs.gov PDFs, read page by page;
case and punctuation included), so a drift here is a failing line, not a header nobody re-checked.
The `person` column, `employer_ref`, the K-1 `source` and every Household / persons label are THIS
PRODUCT'S OWN plain words — the interview's vocabulary — and not a caption on any form; the table
marks them.

PEOPLE COUNT FROM 1. The person column's caption says where its number comes from — the Household
tab's own first column (headed `Item`), which a person reads as 1, 2, …; the
wire's `person` index is 0-based and `workbook.layout.row_number` is the one place the two meet.
The caption names no column header on purpose (it used to carry a stale `person #`):
a header can be renamed again, and "the person's number" stays true through it.
"""
from __future__ import annotations

PERSON_LABEL = "Whose form (the person's number on the Household tab)"

# The Household rows' group key — not a fact group; the two rows are the request envelope's year
# and the root `filing_status`.
HOUSEHOLD_GROUP = "household"

LABELS = {
    # Form W-2 (2025), boxes 1-6.
    ("w2s", "person"): PERSON_LABEL,
    ("w2s", "wages_cents"): "1 Wages, tips, other compensation",
    ("w2s", "withholding_cents"): "2 Federal income tax withheld",
    ("w2s", "social_security_wages_cents"): "3 Social security wages",
    ("w2s", "medicare_wages_cents"): "5 Medicare wages and tips",
    ("w2s", "social_security_withheld_cents"): "4 Social security tax withheld",
    ("w2s", "medicare_withheld_cents"): "6 Medicare tax withheld",
    ("w2s", "dependent_care_benefits_cents"): "10 Dependent care benefits",
    # box 12 prints four code/amount slots; one column per code the form lists, captioned
    # with the code and its meaning from the form's own list (the K-1 box 20 code Z precedent).
    ("w2s", "box12_a_cents"): "12 Code A — Uncollected social security or RRTA tax on tips",
    ("w2s", "box12_b_cents"): "12 Code B — Uncollected Medicare tax on tips",
    ("w2s", "box12_c_cents"): "12 Code C — Taxable cost of group-term life insurance over $50,000",
    ("w2s", "box12_d_cents"): "12 Code D — Elective deferrals under a section 401(k) cash or deferred arrangement plan",
    ("w2s", "box12_e_cents"): "12 Code E — Elective deferrals under a section 403(b) salary reduction agreement",
    ("w2s", "box12_f_cents"): "12 Code F — Elective deferrals under a section 408(k)(6) salary reduction SEP",
    ("w2s", "box12_g_cents"): "12 Code G — Elective deferrals and employer contributions to a section 457(b) deferred compensation plan",
    ("w2s", "box12_g_governmental_plan"): "12 Code G — Governmental section 457(b) plan",
    ("w2s", "box12_h_cents"): "12 Code H — Elective deferrals to a section 501(c)(18)(D) tax-exempt organization plan",
    ("w2s", "box12_j_cents"): "12 Code J — Nontaxable sick pay",
    ("w2s", "box12_k_cents"): "12 Code K — 20% excise tax on excess golden parachute payments",
    ("w2s", "box12_l_cents"): "12 Code L — Substantiated employee business expense reimbursements",
    ("w2s", "box12_m_cents"): "12 Code M — Uncollected social security or RRTA tax on taxable cost of group-term life insurance over $50,000",
    ("w2s", "box12_n_cents"): "12 Code N — Uncollected Medicare tax on taxable cost of group-term life insurance over $50,000",
    ("w2s", "box12_p_cents"): "12 Code P — Excludable moving expense reimbursements paid directly to a member of the U.S. Armed Forces",
    ("w2s", "box12_q_cents"): "12 Code Q — Nontaxable combat pay",
    ("w2s", "box12_r_cents"): "12 Code R — Employer contributions to an Archer MSA",
    ("w2s", "box12_s_cents"): "12 Code S — Employee salary reduction contributions under a section 408(p) SIMPLE plan",
    ("w2s", "box12_t_cents"): "12 Code T — Adoption benefits",
    ("w2s", "box12_v_cents"): "12 Code V — Income from exercise of nonstatutory stock option(s)",
    ("w2s", "box12_w_cents"): "12 Code W — Employer contributions (including employee contributions through a cafeteria plan) to an employee's health savings account (HSA)",
    ("w2s", "box12_y_cents"): "12 Code Y — Deferrals under a section 409A nonqualified deferred compensation plan",
    ("w2s", "box12_z_cents"): "12 Code Z — Income under a nonqualified deferred compensation plan that fails to satisfy section 409A",
    ("w2s", "box12_aa_cents"): "12 Code AA — Designated Roth contributions under a section 401(k) plan",
    ("w2s", "box12_bb_cents"): "12 Code BB — Designated Roth contributions under a section 403(b) plan",
    ("w2s", "box12_dd_cents"): "12 Code DD — Cost of employer-sponsored health coverage",
    ("w2s", "box12_ee_cents"): "12 Code EE — Designated Roth contributions under a governmental section 457(b) plan",
    ("w2s", "box12_ff_cents"): "12 Code FF — Permitted benefits under a qualified small employer health reimbursement arrangement",
    ("w2s", "box12_gg_cents"): "12 Code GG — Income from qualified equity grants under section 83(i)",
    ("w2s", "box12_hh_cents"): "12 Code HH — Aggregate deferrals under section 83(i) elections as of the close of the calendar year",
    ("w2s", "box12_ii_cents"): "12 Code II — Medicaid waiver payments excluded from gross income under Notice 2014-7",
    # box 13's three checkboxes, as the form prints them.
    ("w2s", "statutory_employee"): "13 Statutory employee",
    ("w2s", "retirement_plan"): "13 Retirement plan",
    ("w2s", "third_party_sick_pay"): "13 Third-party sick pay",
    # box 14 prints one caption ("14 Other") over free text; the column names the one
    # reading of it that is asked, the way the K-1's box 20 column names code Z.
    ("w2s", "has_rrta_codes"): "14 Other — Railroad Retirement Tax Act (RRTA) codes listed",
    ("w2s", "employer_ref"): "Employer (reference)",              # ours — not a box
    # Form 1099-INT (2025).
    ("int1099s", "person"): PERSON_LABEL,
    ("int1099s", "interest_cents"): "1 Interest income",
    # Box 3's caption is transcribed from the IRS Instructions for Forms 1099-INT and 1099-OID
    # (Rev. January 2024), heading "Box 3. Interest on U.S. Savings Bonds and Treasury
    # Obligations" — the 1099-INT form PDF is not in the pin's template set, so the
    # form-printed casing check rides the next human caption pass, like the originals did.
    ("int1099s", "government_interest_cents"): "3 Interest on U.S. Savings Bonds and Treasury Obligations",
    ("int1099s", "tax_exempt_interest_cents"): "8 Tax-exempt interest",
    ("int1099s", "federal_withholding_cents"): "4 Federal income tax withheld",
    # boxes 2 and 9-13, as printed on the 2025 form.
    ("int1099s", "early_withdrawal_penalty_cents"): "2 Early withdrawal penalty",
    ("int1099s", "private_activity_bond_interest_cents"): "9 Specified private activity bond interest",
    ("int1099s", "market_discount_cents"): "10 Market discount",
    ("int1099s", "bond_premium_cents"): "11 Bond premium",
    ("int1099s", "treasury_bond_premium_cents"): "12 Bond premium on Treasury obligations",
    ("int1099s", "tax_exempt_bond_premium_cents"): "13 Bond premium on tax-exempt bond",
    # Form 1099-DIV (2025).
    # Form 1099-B: captions as printed on the 2025 form (build's IRS1099B sidecar carries
    # the same words, some with the Form 8949 column they feed appended).
    ("b1099s", "person"): PERSON_LABEL,
    ("b1099s", "date_acquired"): "1b Date acquired",
    ("b1099s", "date_sold"): "1c Date sold or disposed",
    ("b1099s", "proceeds_cents"): "1d Proceeds",
    ("b1099s", "cost_basis_cents"): "1e Cost or other basis",
    ("b1099s", "accrued_market_discount_cents"): "1f Accrued market discount",
    ("b1099s", "wash_sale_loss_disallowed_cents"): "1g Wash sale loss disallowed",
    ("b1099s", "term"): "2 Short-term gain or loss / Long-term gain or loss / Ordinary",
    ("b1099s", "collectibles"): "3 Check if proceeds from: Collectibles",
    ("b1099s", "qualified_opportunity_fund"): "3 Check if proceeds from: QOF",
    ("b1099s", "federal_withholding_cents"): "4 Federal income tax withheld",
    ("b1099s", "loss_not_allowed"): "7 Check if loss is not allowed based on amount in 1d",
    ("b1099s", "basis_reported_to_irs"): "12 Check if basis reported to IRS",
    # Form 1099-OID: captions as printed, from build's boxes.tsv sidecar.
    ("oid1099s", "person"): PERSON_LABEL,
    ("oid1099s", "original_issue_discount_cents"): "1 Original issue discount for the year",
    ("oid1099s", "other_periodic_interest_cents"): "2 Other periodic interest",
    ("oid1099s", "early_withdrawal_penalty_cents"): "3 Early withdrawal penalty",
    ("oid1099s", "federal_withholding_cents"): "4 Federal income tax withheld",
    ("oid1099s", "market_discount_cents"): "5 Market discount",
    ("oid1099s", "acquisition_premium_cents"): "6 Acquisition premium",
    ("oid1099s", "treasury_oid_cents"): "8 Original issue discount on U.S. Treasury obligations",
    ("oid1099s", "bond_premium_cents"): "10 Bond premium",
    ("oid1099s", "tax_exempt_oid_cents"): "11 Tax-exempt OID",
    ("oid1099s", "box2_is_tax_exempt"): "2 Other periodic interest — tax-exempt",
    ("oid1099s", "fatca_filing_requirement"): "FATCA filing requirement",
    ("div1099s", "person"): PERSON_LABEL,
    ("div1099s", "ordinary_dividends_cents"): "1a Total ordinary dividends",
    ("div1099s", "qualified_dividends_cents"): "1b Qualified dividends",
    ("div1099s", "capital_gain_distributions_cents"): "2a Total capital gain distr.",
    # The three added later are transcribed from the vendored IRS instructions
    # headings (i1099div--ty2025--2024-01.txt: "Box 2b. Unrecap. Sec. 1250 Gain", "Box 5.
    # Section 199A Dividends", "Box 12. Exempt-Interest Dividends") — the 1099-DIV form PDF is
    # not in the pin's template set, so the form-printed casing check rides the next human
    # caption pass, like the 1099-INT's box 3.
    ("div1099s", "unrecaptured_1250_gain_cents"): "2b Unrecap. Sec. 1250 Gain",
    ("div1099s", "federal_withholding_cents"): "4 Federal income tax withheld",
    ("div1099s", "section_199a_dividends_cents"): "5 Section 199A Dividends",
    ("div1099s", "exempt_interest_dividends_cents"): "12 Exempt-Interest Dividends",
    # Form 1099-R (2025). Box 7 is one box on the 2025 form; the 2026 form splits it into 7a/7b.
    ("r1099s", "person"): PERSON_LABEL,
    ("r1099s", "gross_distribution_cents"): "1 Gross distribution",
    ("r1099s", "taxable_amount_cents"): "2a Taxable amount",
    ("r1099s", "taxable_amount_not_determined"): "2b Taxable amount not determined",
    ("r1099s", "distribution_code"): "7 Distribution code(s)",
    ("r1099s", "ira_sep_simple"): "IRA/SEP/SIMPLE",
    ("r1099s", "federal_withholding_cents"): "4 Federal income tax withheld",
    ("r1099s", "other_cents"): "8 Other",
    ("r1099s", "other_percentage"): "8 Other %",
    ("r1099s", "percentage_of_total_distribution"): "9a Your percentage of total distribution",
    ("r1099s", "qualified_hsa_funding_distribution_cents"): "Transferred to an HSA by the trustee (Form 8889 line 10)",
    ("r1099s", "qualified_charitable_distribution_cents"): "Paid directly to a charity by the trustee (a qualified charitable distribution)",
    ("r1099s", "qcd_to_split_interest_entity"): "The one-time election to a split-interest entity",
    ("r1099s", "rolled_over_cents"): "Rolled over into another retirement account within 60 days",
    ("r1099s", "ira_one_rollover_per_year"): "The only IRA-to-IRA rollover in the 12 months before it",
    ("r1099s", "reached_minimum_retirement_age"): "Had reached the plan's minimum retirement age (a disability payment, code 3)",
    ("r1099s", "public_safety_officer"): "An eligible retired public safety officer's government plan distribution",
    ("r1099s", "pso_premiums_paid_by_plan"): "The plan paid insurance premiums out of it",
    ("r1099s", "pso_premiums_cents"): "Premiums the plan paid out of it (excluded up to 3,000, Form 1040 line 5b)",
    ("r1099s", "date_of_payment"): "13 Date of payment",
    ("r1099s", "box1_is_death_benefit_under_contract"): "Box 1 is the death benefit under that life insurance contract",
    ("r1099s", "acquired_in_reportable_policy_sale"): "The policy was acquired in a reportable policy sale",
    ("r1099s", "acquired_for_valuable_consideration"): "The policy was transferred for valuable consideration",
    ("r1099s", "transfer_has_carryover_basis"): "The transfer kept the transferor's basis",
    ("r1099s", "transfer_to_insured_or_related_party"): "The transfer was to the insured or a party related to the insured",
    ("r1099s", "death_benefit_basis_cents"): "Paid for the policy in total (price, premiums and other amounts; box 5 is the payer's estimate)",
    # Form W-2G (2025).
    ("w2gs", "person"): PERSON_LABEL,
    ("w2gs", "winnings_cents"): "1 Reportable winnings",
    ("w2gs", "federal_withholding_cents"): "4 Federal income tax withheld",
    # Form SSA-1099 / RRB-1099. The two forms number these boxes differently (5 and 6
    # against 5 and 10), so the shared captions carry no number (the K-1 rule).
    ("ssa1099s", "person"): PERSON_LABEL,
    ("ssa1099s", "form_type"): "Which form (SSA-1099 or RRB-1099)",
    ("ssa1099s", "net_benefits_cents"): "Net benefits",
    ("ssa1099s", "federal_withholding_cents"): "Federal income tax withheld",
    # Form 1099-G. Boxes 1 and 4 as printed; the same-year repayment is the Schedule 1
    # line 7 entry space, printed on no box, so its caption names the line instead.
    ("g1099s", "person"): PERSON_LABEL,
    ("g1099s", "unemployment_compensation_cents"): "1 Unemployment compensation",
    ("g1099s", "federal_withholding_cents"): "4 Federal income tax withheld",
    ("g1099s", "repaid_cents"): "Repaid in the same year (Schedule 1 line 7)",
    # Form 1099-MISC. Box 3 and box 4 as printed; the Alaska PFD question is the engine's
    # own per-form question, on no box.
    ("misc1099s", "person"): PERSON_LABEL,
    ("misc1099s", "royalties_cents"): "2 Royalties",
    ("misc1099s", "other_income_cents"): "3 Other income",
    ("misc1099s", "is_alaska_pfd"): "Box 3 is an Alaska Permanent Fund dividend",
    ("misc1099s", "federal_withholding_cents"): "4 Federal income tax withheld",
    # Form 1099-SA. Boxes 1 and 3 as printed; the expenses are Form 8889 line 15.
    ("hsa_distributions", "person"): PERSON_LABEL,
    ("ssa_lump_sum_years", "earlier_year"): "Earlier year (Worksheet 2 and 3, \u201cEnter earlier year\u201d)",
    ("ssa_lump_sum_years", "lump_sum_portion_cents"): "Part of the lump sum for that year (Worksheet 2 and 3, line 1)",
    ("ssa_lump_sum_years", "benefits_received_cents"): "Benefits received in that year (that year's box 5)",
    ("ssa_lump_sum_years", "adjusted_gross_income_cents"): "That year's adjusted gross income (Worksheet 2 and 3, line 3)",
    ("ssa_lump_sum_years", "exclusions_cents"): "That year's exclusions and adjustments (Worksheet 2 and 3, line 4)",
    ("ssa_lump_sum_years", "tax_exempt_interest_cents"): "That year's tax-exempt interest (Worksheet 2 and 3, line 5)",
    ("ssa_lump_sum_years", "taxable_benefits_reported_cents"): "Benefits already taxed for that year (Worksheet 2 line 7)",
    ("ssa_lump_sum_years", "filed_jointly"): "That year's return was a joint return",
    ("ssa_lump_sum_years", "mfs_lived_with_spouse"): "That year was married filing separately and living together",
    ("hsa_distributions", "gross_distribution_cents"): "1 Gross distribution",
    ("hsa_distributions", "hsa_distribution_code"): "3 Distribution code",
    ("hsa_distributions", "qualified_medical_expenses_cents"): "Qualified medical expenses paid (Form 8889 line 15)",
    # Form 2441 line 1, columns (c) to (e) as printed; identity columns (a) and (b) are not
    # entered.
    ("care_providers", "provider_type"): "(c) Identifying number — organization, tax-exempt, or individual (the number is not entered)",
    ("care_providers", "is_household_employee"): "(d) Was the care provider your household employee in 2025?",
    ("care_providers", "amount_paid_cents"): "(e) Amount paid",
    # Form 1095-A Part III, lines 21-32 by month, columns A, B, C. The 1095-A itself is not
    # in the pin's vendored sources; the captions are the column heads as the Form 8962
    # instructions quote them ("lines 21 through 32, column A" — the monthly enrollment premiums,
    # the monthly premium for the applicable SLCSP, the monthly APTC).
    ("f1095as", "jan_premium_cents"): "21 January \u2014 A. Monthly enrollment premiums",
    ("f1095as", "jan_slcsp_cents"): "21 January \u2014 B. Monthly second lowest cost silver plan (SLCSP) premium",
    ("f1095as", "jan_aptc_cents"): "21 January \u2014 C. Monthly advance payment of premium tax credit",
    ("f1095as", "feb_premium_cents"): "22 February \u2014 A. Monthly enrollment premiums",
    ("f1095as", "feb_slcsp_cents"): "22 February \u2014 B. Monthly second lowest cost silver plan (SLCSP) premium",
    ("f1095as", "feb_aptc_cents"): "22 February \u2014 C. Monthly advance payment of premium tax credit",
    ("f1095as", "mar_premium_cents"): "23 March \u2014 A. Monthly enrollment premiums",
    ("f1095as", "mar_slcsp_cents"): "23 March \u2014 B. Monthly second lowest cost silver plan (SLCSP) premium",
    ("f1095as", "mar_aptc_cents"): "23 March \u2014 C. Monthly advance payment of premium tax credit",
    ("f1095as", "apr_premium_cents"): "24 April \u2014 A. Monthly enrollment premiums",
    ("f1095as", "apr_slcsp_cents"): "24 April \u2014 B. Monthly second lowest cost silver plan (SLCSP) premium",
    ("f1095as", "apr_aptc_cents"): "24 April \u2014 C. Monthly advance payment of premium tax credit",
    ("f1095as", "may_premium_cents"): "25 May \u2014 A. Monthly enrollment premiums",
    ("f1095as", "may_slcsp_cents"): "25 May \u2014 B. Monthly second lowest cost silver plan (SLCSP) premium",
    ("f1095as", "may_aptc_cents"): "25 May \u2014 C. Monthly advance payment of premium tax credit",
    ("f1095as", "jun_premium_cents"): "26 June \u2014 A. Monthly enrollment premiums",
    ("f1095as", "jun_slcsp_cents"): "26 June \u2014 B. Monthly second lowest cost silver plan (SLCSP) premium",
    ("f1095as", "jun_aptc_cents"): "26 June \u2014 C. Monthly advance payment of premium tax credit",
    ("f1095as", "jul_premium_cents"): "27 July \u2014 A. Monthly enrollment premiums",
    ("f1095as", "jul_slcsp_cents"): "27 July \u2014 B. Monthly second lowest cost silver plan (SLCSP) premium",
    ("f1095as", "jul_aptc_cents"): "27 July \u2014 C. Monthly advance payment of premium tax credit",
    ("f1095as", "aug_premium_cents"): "28 August \u2014 A. Monthly enrollment premiums",
    ("f1095as", "aug_slcsp_cents"): "28 August \u2014 B. Monthly second lowest cost silver plan (SLCSP) premium",
    ("f1095as", "aug_aptc_cents"): "28 August \u2014 C. Monthly advance payment of premium tax credit",
    ("f1095as", "sep_premium_cents"): "29 September \u2014 A. Monthly enrollment premiums",
    ("f1095as", "sep_slcsp_cents"): "29 September \u2014 B. Monthly second lowest cost silver plan (SLCSP) premium",
    ("f1095as", "sep_aptc_cents"): "29 September \u2014 C. Monthly advance payment of premium tax credit",
    ("f1095as", "oct_premium_cents"): "30 October \u2014 A. Monthly enrollment premiums",
    ("f1095as", "oct_slcsp_cents"): "30 October \u2014 B. Monthly second lowest cost silver plan (SLCSP) premium",
    ("f1095as", "oct_aptc_cents"): "30 October \u2014 C. Monthly advance payment of premium tax credit",
    ("f1095as", "nov_premium_cents"): "31 November \u2014 A. Monthly enrollment premiums",
    ("f1095as", "nov_slcsp_cents"): "31 November \u2014 B. Monthly second lowest cost silver plan (SLCSP) premium",
    ("f1095as", "nov_aptc_cents"): "31 November \u2014 C. Monthly advance payment of premium tax credit",
    ("f1095as", "dec_premium_cents"): "32 December \u2014 A. Monthly enrollment premiums",
    ("f1095as", "dec_slcsp_cents"): "32 December \u2014 B. Monthly second lowest cost silver plan (SLCSP) premium",
    ("f1095as", "dec_aptc_cents"): "32 December \u2014 C. Monthly advance payment of premium tax credit",
    # Schedule C (Form 1040), 2025: line 1, line 28, and line B (the principal business code).
    ("schedule_c", "person"): PERSON_LABEL,
    ("schedule_c", "gross_receipts_cents"): "1 Gross receipts or sales",
    ("schedule_c", "returns_and_allowances_cents"): "2 Returns and allowances",
    ("schedule_c", "cost_of_goods_sold_cents"): "4 Cost of goods sold (from line 42)",
    ("schedule_c", "other_business_income_cents"):
        "6 Other income, including federal and state gasoline or fuel tax credit or refund",
    ("schedule_c", "total_expenses_cents"): "28 Total expenses",
    ("schedule_c", "principal_business_code"): "B Enter code from instructions",
    ("schedule_c", "materially_participated"):
        "G Did you “materially participate” in the operation of this business "
        "during 2025?",
    ("schedule_c", "all_investment_at_risk"): "32a All investment is at risk.",
    # no Schedule C box prints the amount — box 32b routes the filer to Form 6198, and
    # this is that form's Part II line 10b figure, so the column takes the form it comes from
    # (the `basis_cents` precedent: this product's words where no box prints the caption).
    ("schedule_c", "amount_at_risk_cents"): "Amount at risk (Form 6198, line 10b)",
    # Schedule E (Form 1040), 2025, Part I. The dropdown keeps the schema's codes.
    ("rentals", "person"): PERSON_LABEL,
    ("rentals", "rents_received_cents"): "3 Rents received",
    ("rentals", "total_expenses_cents"): "20 Total expenses",
    # the itemized expense lines print their own Schedule E box numbers. The
    # depreciation-input pair carries no Schedule E box at all — Form 4562 Part III is where
    # they live, so the column takes that form's words (the `basis_cents` precedent above).
    ("rentals", "insurance_cents"): "9 Insurance",
    ("rentals", "management_fees_cents"): "11 Management fees",
    ("rentals", "repairs_cents"): "14 Repairs",
    ("rentals", "taxes_cents"): "16 Taxes",
    ("rentals", "building_basis_cents"): "Building depreciable basis (Form 4562, Part III)",
    ("rentals", "is_nonresidential_real_property"):
        "Nonresidential real property (Form 4562, Part III)",
    ("rentals", "building_uses_standard_gds"):
        "Regular MACRS, 27.5 or 39 years (Form 4562, Part III)",
    ("rentals", "placed_in_service_in_current_year"): "Building placed in service this year",
    ("rentals", "placed_in_service_month"): "Month placed in service",
    ("rentals", "has_five_year_property"):
        "Has 5-year property (Form 4562, Part III, line 19b)",
    ("rentals", "five_year_property_basis_cents"):
        "5-year property basis (Form 4562, Part III, line 19b)",
    ("rentals", "property_type"): "1b Type of Property",
    # The loss-gate pair and the carry-in: no Schedule E box prints the first two — the words
    # come from the statutes' own terms (§469(i) active participation; §465 at risk), plain and
    # short; the third is Form 8582 Part IV column (c), verbatim.
    ("rentals", "active_participation"): "Active participation",
    ("rentals", "fully_at_risk"): "All investment is at risk",
    ("rentals", "amount_at_risk_cents"): "Amount at risk (Form 6198, line 10b)",
    # line 1b type 7 is the only type code that decides a number here, and the answer it
    # opens is not a printed box on Schedule E at all — Form 8582's recharacterization rule is
    # where it lives, so the column takes that form's words (the `basis_cents` precedent).
    ("rentals", "materially_participates_in_lessee"):
        "Materially participates in the lessee business (Form 8582 recharacterization)",
    ("rentals", "prior_year_unallowed_loss_cents"): "Prior years' unallowed losses",
    ("rentals", "active_participation_when_loss_arose"):
        "Active participation in the year the loss arose",
    # Schedule K-1 (2025). `source` is ours — which K-1 — not a box. The amount captions carry
    # NO box number (the copy skill's own rule for a group whose documents number the same
    # amount differently): the numbers below were the 1065's — interest is its box 5 but the
    # 1120-S's box 4 and the 1041's line 1 — so a numbered caption was correct for one form in
    # three. Verified against all three pinned templates' printed text (pypdf over
    # dictionary/pdf/2025/IRS{1065SK1,1120SSK,1041SK1}, 2026-09-01; the reproducible check is
    # scripts/k1_captions_pypdf_check.py): "Interest income" and "Ordinary dividends" are printed
    # verbatim on all three; "Ordinary business income" is the 1041's exact words and the printed
    # prefix of the other two (they add "(loss)"); "Royalties" is printed on the 1065 and 1120-S —
    # the 1041 has NO royalties box at all (an estate or trust reports royalties inside its
    # line 5, "Other portfolio and nonbusiness income"), which is a fact for the source-specific
    # note when 1041 intake is worded, not a caption this shared column can carry a number for.
    ("k1s", "person"): PERSON_LABEL,
    ("k1s", "source"): ("Which Schedule K-1 (1065 partnership / 1120-S S corporation / 1041 "
                        "estate or trust)"),
    ("k1s", "ordinary_business_income_cents"): "Ordinary business income",
    ("k1s", "interest_income_cents"): "Interest income",
    ("k1s", "dividend_income_cents"): "Ordinary dividends",
    ("k1s", "royalties_cents"): "Royalties",
    # The rest of the K-1 columns follow the same rule (number-free shared words),
    # except item D — a Form 1065-only ask, so it may keep its printed letter.
    ("k1s", "qualified_dividends_cents"): "Qualified dividends",
    ("k1s", "se_earnings_cents"): "Self-employment earnings (loss)",
    ("k1s", "publicly_traded_partnership"):
        "D Check if this is a publicly traded partnership (PTP)",
    ("k1s", "materially_participated"): "Materially participated",
    ("k1s", "basis_cents"): "Adjusted basis before this loss",
    ("k1s", "fully_at_risk"): "All investment is at risk",
    ("k1s", "amount_at_risk_cents"): "Amount at risk (Form 6198, line 10b)",
    # the guaranteed-payments pair and item G print on the Form 1065 K-1 only, so like
    # item D they keep the printed number/letter (read off the pinned template; the caption
    # check in tests/test_workbook_layout.py holds them to the register).
    ("k1s", "guaranteed_payments_services_cents"): "4a Guaranteed payments for services",
    ("k1s", "guaranteed_payments_capital_cents"): "4b Guaranteed payments for capital",
    ("k1s", "general_partner"): "G General partner or LLC member-manager",
    # box 20 prints ONE caption over a list of code-and-amount pairs, so the column has
    # to name the code too — the face's "20 Other information" plus the code list's own words
    # for Z. The other two are not boxes at all: one is a question about the partnership, the
    # other a figure the filer carries forward, so both take this product's words (the
    # `basis_cents` precedent).
    ("k1s", "qualified_ptp_income_cents"):
        "20 Other information — code Z, Section 199A information",
    ("k1s", "qualified_ptp_is_sstb"): "This PTP is a specified service trade or business",
    # box 20 code Z on Form 1065, box 17 code V on Form 1120-S — two numbers for one
    # figure, so the caption carries no number (the one-group-several-forms rule).
    ("k1s", "section_199a_qbi_cents"): "Section 199A information — qualified business income",
    ("k1s", "ptp_prior_year_unallowed_loss_cents"): "Prior-year unallowed loss from this PTP",
    # not a box either. Box 14 code A is printed; the DEDUCTIBLE part of it is the
    # figure the printed instruction tells the partner to work out off the return, so the
    # column takes this product's words (the `basis_cents` precedent again).
    ("k1s", "deductible_se_loss_cents"): "Deductible part of the box 14 code A loss",
    # Household and the persons block: this product's own words (the interview's), not a form's.
    (HOUSEHOLD_GROUP, "tax_year"): "Tax year",
    (HOUSEHOLD_GROUP, "filing_status"): "Filing status",
    # the residence state — this product's own words (the interview's).
    (HOUSEHOLD_GROUP, "residence_state"): "State you lived in and earned income in",
    (HOUSEHOLD_GROUP, "received_alaska_pfd"): "Alaska Permanent Fund dividend received",
    (HOUSEHOLD_GROUP, "filed_jointly_2023"): "Filed jointly for 2023 (Form 8880 line 4)",
    (HOUSEHOLD_GROUP, "filed_jointly_2024"): "Filed jointly for 2024 (Form 8880 line 4)",
    (HOUSEHOLD_GROUP, "hsa_excess_in_w2_wages"): "Excess employer HSA contribution already in W-2 wages (Form 8889)",
    # the three combat pay elections, each the form's own line.
    (HOUSEHOLD_GROUP, "combat_pay_election"): "Nontaxable combat pay election (Form 1040 line 1i)",
    (HOUSEHOLD_GROUP, "cdcc_combat_pay_election"): "Combat pay election for the credit (Form 2441 Part II)",
    (HOUSEHOLD_GROUP, "dependent_care_benefits_combat_pay_election"): "Combat pay election for the benefits exclusion (Form 2441 Part III)",
    # the Form 1040 page-1 digital-assets question, its two parts as the form letters them.
    (HOUSEHOLD_GROUP, "received_digital_assets"): "Digital assets (a): received",
    (HOUSEHOLD_GROUP, "disposed_digital_assets"): "Digital assets (b): disposed of",
    # Schedule B Part III, the three questions the dictionary asks of lines 7a and 8.
    (HOUSEHOLD_GROUP, "foreign_financial_account"): "Schedule B 7a: foreign financial account",
    (HOUSEHOLD_GROUP, "foreign_trust_grantor"): "Schedule B 8: owner or grantor of a foreign trust",
    (HOUSEHOLD_GROUP, "foreign_trust_transactions"): "Schedule B 8: distribution from or transfer to a foreign trust",
    # Form 8862's credit-history questions, in the form's words.
    (HOUSEHOLD_GROUP, "eitc_reduced_or_disallowed"): "Form 8862: earned income credit reduced or disallowed in a prior year",
    (HOUSEHOLD_GROUP, "ctc_odc_reduced_or_disallowed"): "Form 8862: child tax credit, ACTC or ODC reduced or disallowed in a prior year",
    (HOUSEHOLD_GROUP, "qualifying_child_of_another"): "Form 8862 line 4: could be claimed as another taxpayer's qualifying child",
    # Form 1040 line 26's question, as the form prints the line.
    (HOUSEHOLD_GROUP, "paid_estimated_taxes"): "Estimated tax payments made (Form 1040 line 26)",
    # the rows a yes above reaches — the amount in dollars, the follow-ups as yes/no.
    (HOUSEHOLD_GROUP, "estimated_tax_payments_cents"): "Estimated tax payments, total (Form 1040 line 26)",
    (HOUSEHOLD_GROUP, "section_1341_credit_cents"): "Credit for repayment of amounts included in income from earlier years (Schedule 3 line 13b)",
    (HOUSEHOLD_GROUP, "royalty_expenses_cents"): "Royalty activity ordinary expenses (Schedule E line 20)",
    (HOUSEHOLD_GROUP, "royalty_is_oil_gas_geothermal"): "Royalty activity is oil, gas, or geothermal (Schedule E line 18 depletion)",
    # Schedule 1 lines 2a/19a, each amount invited on every return, each gate reached once
    # its amount is answered.
    (HOUSEHOLD_GROUP, "alimony_received_cents"): "Alimony received (Schedule 1 line 2a)",
    (HOUSEHOLD_GROUP, "alimony_received_pre2019_agreement"): "Alimony received under an agreement entered into on or before December 31, 2018",
    (HOUSEHOLD_GROUP, "alimony_paid_cents"): "Alimony paid (Schedule 1 line 19a)",
    (HOUSEHOLD_GROUP, "alimony_paid_pre2019_agreement"): "Alimony paid under an agreement entered into on or before December 31, 2018",
    (HOUSEHOLD_GROUP, "alimony_paid_section_682_trust"): "Alimony paid as the income of a section 682 trust",
    # the Form 1040 page-1 main-home checkbox, invited on every return.
    (HOUSEHOLD_GROUP, "main_home_in_us_over_half_year"): "Main home in the U.S. for more than half of 2025",
    (HOUSEHOLD_GROUP, "estimated_payments_under_different_name"): "Estimated payments made under different filer details",
    (HOUSEHOLD_GROUP, "estimated_payments_with_former_spouse"): "Estimated payments made jointly with a former spouse",
    (HOUSEHOLD_GROUP, "paid_student_loan_interest"): "Student loan interest paid (Schedule 1 line 21)",
    (HOUSEHOLD_GROUP, "student_loans_qualify"): "Student loans qualify (solely for qualified education expenses)",
    (HOUSEHOLD_GROUP, "student_loan_interest_cents"): "Student loan interest paid, total (Form 1098-E box 1)",
    (HOUSEHOLD_GROUP, "student_loan_interest_employer_paid_cents"): "Student loan interest paid by an employer, tax-free (section 127 program)",
    (HOUSEHOLD_GROUP, "student_loan_interest_from_qtp_cents"): "Student loan interest paid from tax-free qualified tuition program earnings",
    # the per-status rows — this product's own words (the interview's), the form's where
    # the form prints the question, one provenance clause at most.
    (HOUSEHOLD_GROUP, "spouse_received_alaska_pfd"): "Alaska Permanent Fund dividend received by your spouse (joint return)",
    (HOUSEHOLD_GROUP, "lived_with_spouse_all_year"): "Lived with your spouse for the whole year",
    (HOUSEHOLD_GROUP, "months_lived_with_spouse"): "How long you lived with your spouse this year",
    (HOUSEHOLD_GROUP, "separation_agreement_on_last_day"): "Living apart under a separation agreement on the last day of the year",
    (HOUSEHOLD_GROUP, "lived_apart_last_six_months"): "Lived apart from your spouse for the last six months of the year",
    (HOUSEHOLD_GROUP, "couple_required_to_file"): "You and your spouse are required to file a return",
    (HOUSEHOLD_GROUP, "couple_files_only_for_refund"): "Filing jointly only to claim a refund",
    (HOUSEHOLD_GROUP, "spouse_itemizes"): "Your spouse itemizes on a separate return (Form 1040 page 1)",
    (HOUSEHOLD_GROUP, "community_property_domicile"): "Domicile in a community property state (Form 8958)",
    (HOUSEHOLD_GROUP, "spouse_files_return"): "Your spouse files their own return",
    (HOUSEHOLD_GROUP, "spouse_had_gross_income"): "Your spouse had gross income this year",
    (HOUSEHOLD_GROUP, "spouse_can_be_claimed"): "Someone can claim your spouse as a dependent",
    (HOUSEHOLD_GROUP, "spouse_65_or_older"): "Spouse was 65 or older at the end of the year (Form 1040 line 12)",
    (HOUSEHOLD_GROUP, "spouse_is_blind"): "Spouse is blind (Form 1040 line 12)",
    (HOUSEHOLD_GROUP, "spouse_covered_by_employer_plan"): "Your spouse was covered by a retirement plan at work",
    (HOUSEHOLD_GROUP, "spouse_death_year"): "Year your spouse died",
    (HOUSEHOLD_GROUP, "could_have_filed_jointly_year_of_death"): "Could have filed jointly for the year your spouse died",
    (HOUSEHOLD_GROUP, "allocating_policy_or_alternative_calculation"): "Sharing policy amounts with another taxpayer, or the year-of-marriage alternative (Form 8962 line 9)",
    (HOUSEHOLD_GROUP, "marketplace_estimated_income_at_least_100_fpl"): "Marketplace estimated household income at or above 100% of the poverty line (Form 8962)",
    (HOUSEHOLD_GROUP, "below_poverty_line_not_eligible_for_medicaid_due_to_immigration"): "Household income below the poverty line and not eligible for Medicaid due to immigration status (Form 8962)",
    (HOUSEHOLD_GROUP, "enrollee_not_eligible_for_marketplace_due_to_immigration"): "Someone enrolled on the policy is not lawfully present (Form 8962)",
    (HOUSEHOLD_GROUP, "dependents_modified_agi_cents"): "Dependents' modified AGI (Form 8962 line 2b)",
    (HOUSEHOLD_GROUP, "mfs_ptc_exception"): "Separate-return exception for domestic abuse or spousal abandonment (Form 8962 line A)",
    (HOUSEHOLD_GROUP, "mfs_ptc_exception_fourth_year"): "Claiming that exception for a fourth consecutive year (Form 8962)",
    # Form 2441 lines 13 and 14.
    (HOUSEHOLD_GROUP, "dependent_care_carryover_cents"): "Prior-year dependent care benefits used in the grace period (Form 2441 line 13)",
    (HOUSEHOLD_GROUP, "dependent_care_forfeited_cents"): "Dependent care benefits forfeited or carried forward (Form 2441 line 14)",
    (HOUSEHOLD_GROUP, "paid_prior_year_care_expenses_this_year"): "Paid 2024 care expenses in 2025 (Form 2441, Worksheet A)",
    (HOUSEHOLD_GROUP, "prior_year_credit_claimed"): "Claimed the child and dependent care credit for 2024",
    (HOUSEHOLD_GROUP, "prior_year_credit_claimed_maximum"): "Claimed the 2024 credit on the maximum expenses allowed",
    (HOUSEHOLD_GROUP, "prior_year_form_2441_line_3_cents"): "2024 Form 2441 line 3 (Worksheet A, line 1)",
    (HOUSEHOLD_GROUP, "prior_year_expenses_paid_this_year_cents"): "2024 expenses paid in 2025 (Worksheet A, line 2)",
    (HOUSEHOLD_GROUP, "prior_year_had_two_or_more_qualifying_persons"): "Two or more qualifying persons in 2024 (Worksheet A, line 4)",
    (HOUSEHOLD_GROUP, "prior_year_excluded_or_deducted_benefits_cents"): "2024 benefits excluded or deducted (Worksheet A, line 5)",
    (HOUSEHOLD_GROUP, "prior_year_lower_earned_income_cents"): "Smaller 2024 earned income (Worksheet A, line 7)",
    (HOUSEHOLD_GROUP, "prior_year_form_2441_line_6_cents"): "2024 Form 2441 line 6 (Worksheet A, line 9)",
    (HOUSEHOLD_GROUP, "prior_year_agi_cents"): "2024 adjusted gross income (Worksheet A, line 11)",
    (HOUSEHOLD_GROUP, "elects_lump_sum_benefits"): "Lump-sum election for benefits received for an earlier year (Form 1040 line 6c)",
    (HOUSEHOLD_GROUP, "only_business_is_trading_securities"): "Trading in financial instruments or commodities is the only trade or business (Form 8960)",
    ("persons", "role"): "Who this person is to the return",
    ("persons", "birth_year"): "Year of birth",
    ("persons", "birth_month"): "Month of birth",
    ("persons", "tin_type"): "Type of taxpayer ID (never the number)",
    ("persons", "relationship"): "Relationship to you",
    ("persons", "months_in_home"): "Months lived in your home",
    ("persons", "is_student"): "Student",
    ("persons", "is_permanently_disabled"): "Permanently and totally disabled",
    ("persons", "unable_to_care_for_self"): "Unable to care for themselves (Form 2441 qualifying person)",
    ("persons", "is_married"): "Married",
    ("persons", "provided_own_support"): "Provided over half their own support",
    ("persons", "gross_income_under_limit"): "Gross income under the dependent limit",
    ("persons", "filer_provided_over_half_support"): "You provided over half their support",
    ("persons", "could_be_qualifying_child_of_another"):
        "Could be another taxpayer’s qualifying child",
    ("persons", "parents_situation"): "Your situation with their other legal parent",
    ("persons", "child_in_parents_custody"): "In their parents' legal custody on July 2",
    ("persons", "child_lived_with_parents_over_half_year"):
        "Lived with a legal parent more than six months",
    ("persons", "parents_provided_over_half_support"):
        "Their parents paid more than half their support",
    ("persons", "written_declaration"): "A parent signed a declaration not to claim them",
    # the custodial-parent questions.
    ("persons", "nights_with_filer_vs_other_parent"): "Nights with you vs the other parent",
    ("persons", "filer_agi_higher_than_other_parent"): "Your AGI was higher than the other parent's",
    # the non-parental arm's first question.
    ("persons", "child_parents_living"): "Their own parents are living",
    # the non-parental split.
    ("persons", "parents_meet_divorced_or_separated_rule"): "Their parents meet the divorced-or-separated rule",
    ("persons", "a_parent_signed_declaration_not_to_claim"): "A parent of theirs signed a declaration not to claim them",
    ("persons", "custodial_parent_claims_child_as_qualifying_person"): "Their custodial parent claims them as a qualifying person",
    ("persons", "filer_agi_higher_than_custodial_parent"): "Your AGI was higher than their custodial parent's",
    ("persons", "files_joint_return_with_spouse"): "Filing a joint return with their spouse",
    ("persons", "required_to_file_with_spouse"): "They and their spouse are required to file",
    ("persons", "joint_return_only_for_refund"):
        "Their joint return is only to claim a refund",
    # the split gate's custody questions.
    ("persons", "child_residence_state"): "State or territory they lived in on July 2",
    ("persons", "child_emancipated"): "Emancipated under that state's law",
    ("persons", "child_emancipated_after_july_2"): "Emancipated after July 2",
    # the member-of-household questions.
    ("persons", "was_spouse_during_year"): "Was your spouse at any time in the year",
    ("persons", "relationship_violates_local_law"): "Relationship violated local law",
    ("persons", "has_other_biological_or_adoptive_parent"):
        "Has another biological or adoptive parent",
    ("persons", "is_blind"): "Blind",
    # the educator question and the amount a yes reaches (Schedule 1 line 11).
    ("persons", "k12_educator"): "K-12 educator (900 or more hours in a school year)",
    ("persons", "educator_expenses_cents"): "Educator expenses paid (Schedule 1 line 11)",
    # the IRA question and the two answers a yes reaches (Schedule 1 line 20).
    ("persons", "made_ira_contributions"): "Contributed to an IRA or ABLE account (Schedule 1 line 20; Form 8880)",
    # the own-HSA-contribution question and the two amounts a yes reaches (Form 8889 line 2).
    ("persons", "made_hsa_contributions"): "Contributed to an HSA yourself, outside payroll (Form 8889 line 2)",
    ("persons", "hsa_own_contributions_cents"): "Own HSA contributions for the year (Form 8889 line 2)",
    ("persons", "hsa_own_contributions_after_year_end_cents"): "Own HSA contributions made after year end for 2025 (Form 8889 line 2)",
    ("persons", "hsa_prior_year_excess_cents"): "Excess HSA contribution still in the account at the end of 2024 (2024 Form 5329 line 48; Form 5329 line 42)",
    ("persons", "hsa_december_31_value_cents"): "Value of HSAs on December 31, 2025, including 2025 contributions made in 2026 (Form 5329 line 49)",
    ("persons", "roth_ira_and_able_contributions_cents"): "Roth IRA and ABLE contributions (Form 8880 line 1)",
    ("persons", "roth_ira_contributions_cents"): "Roth IRA contributions (part of the Form 8880 line 1 amount)",
    ("persons", "received_retirement_distributions_2023_2024"): "Retirement distributions received in 2023 or 2024 (Form 8880 line 4)",
    ("persons", "retirement_distributions_2023_cents"): "Distributions received in 2023 (Form 8880 line 4)",
    ("persons", "retirement_distributions_2024_cents"): "Distributions received in 2024 (Form 8880 line 4)",
    ("persons", "received_retirement_distributions_after_year_end"): "Retirement distributions after year end, before the due date (Form 8880 line 4)",
    ("persons", "retirement_distributions_after_year_end_cents"): "Distributions after year end, before the due date — amount (Form 8880 line 4)",
    ("persons", "traditional_ira_contributions_cents"): "Traditional IRA contributions (Schedule 1 line 20)",
    ("persons", "contributed_to_inherited_ira"): "Contributions made to an inherited IRA",
    ("persons", "inherited_ira_contribution_cents"): "Amount paid in to an inherited IRA (Schedule 1 line 20)",
    # the HSA 20%-tax exception pair (Form 8889 lines 17a/17b).
    ("persons", "hsa_exception_amount_cents"): "HSA distributions exempt from the additional 20% tax (Form 8889 line 17b)",
    ("persons", "hsa_exception_reason"): "Ground for that exemption (age 65, disability, death of the beneficiary)",
    ("persons", "hsa_medicare"): "Enrolled in Medicare — all year, part of the year, or none (Form 8889 Part I)",
    ("persons", "hsa_medicare_first_month"): "Month Medicare enrollment began (Form 8889 line 3)",
    ("persons", "hsa_hdhp_coverage"): "High deductible health plan coverage — all year, part of the year, or none (Form 8889 line 1)",
    ("persons", "hsa_hdhp_type"): "Coverage type — self-only, family, or both (Form 8889 line 1)",
    ("persons", "hsa_other_coverage"): "Other health coverage, not a high deductible plan — whole year, part of the year, or none (Form 8889 Part I)",
    ("persons", "hsa_funding_distribution"): "Qualified HSA funding distribution from an IRA (Form 8889 line 10)",
    ("persons", "hsa_prior_funding_distribution_election"): "Qualified HSA funding distribution in an earlier year (the once-per-lifetime election)",
    ("persons", "qcd_prior_deducted_ira_contributions_cents"): "IRA contributions deducted at 70½ or older not yet offset against a QCD (Pub 590-B Appendix D line 1)",
    ("persons", "hsa_funding_distribution_transfer_month"): "Month of the IRA-to-HSA transfer (Form 8889 line 10)",
    ("persons", "hsa_testing_period_first_ineligible_month"): "First month of the IRA-to-HSA transfer's testing period without HDHP eligibility (Form 8889 line 19)",
    ("persons", "hsa_coverage_jan"): "HDHP coverage on the first day of January (Form 8889 line 3)",
    ("persons", "hsa_coverage_feb"): "HDHP coverage on the first day of February (Form 8889 line 3)",
    ("persons", "hsa_coverage_mar"): "HDHP coverage on the first day of March (Form 8889 line 3)",
    ("persons", "hsa_coverage_apr"): "HDHP coverage on the first day of April (Form 8889 line 3)",
    ("persons", "hsa_coverage_may"): "HDHP coverage on the first day of May (Form 8889 line 3)",
    ("persons", "hsa_coverage_jun"): "HDHP coverage on the first day of June (Form 8889 line 3)",
    ("persons", "hsa_coverage_jul"): "HDHP coverage on the first day of July (Form 8889 line 3)",
    ("persons", "hsa_coverage_aug"): "HDHP coverage on the first day of August (Form 8889 line 3)",
    ("persons", "hsa_coverage_sep"): "HDHP coverage on the first day of September (Form 8889 line 3)",
    ("persons", "hsa_coverage_oct"): "HDHP coverage on the first day of October (Form 8889 line 3)",
    ("persons", "hsa_coverage_nov"): "HDHP coverage on the first day of November (Form 8889 line 3)",
    ("persons", "hsa_coverage_dec"): "HDHP coverage on the first day of December (Form 8889 line 3)",
    ("persons", "hsa_spouse_contributed"): "Spouse had HSA contributions this year, on a separate return (Form 8889 line 6)",
    ("persons", "hsa_marital_status_changed"): "Marital status changed during the year (Form 8889 line 3)",
    ("persons", "hsa_marital_change_affects_limit"): "That change affects the HSA contribution limit (Form 8889 line 3)",
    # Form 2441 line 2 column (d), on a qualifying person's row.
    ("persons", "care_expenses_cents"): "Qualified care expenses paid for this person (Form 2441 line 2)",
    # Form 2441 Part III on a filer row.
    ("persons", "self_employed_dependent_care_benefits_cents"): "Dependent care benefits from this filer's own sole proprietorship or partnership (Form 2441 line 12)",
    ("persons", "dependent_care_plan_maximum_cents"): "Most this filer's employer's dependent care plan allows for 2025 (Form 2441 Part III)",
    # the page-1 "someone can claim you" chain.
    ("persons", "someone_can_claim_you"): "Someone can claim them as a dependent",
    ("persons", "expect_to_be_claimed"): "They expect to be claimed",
    ("persons", "potential_claimer_must_file"): "The person who could claim them must file",
    ("persons", "potential_claimer_filed"): "That person filed anyway",
    ("persons", "potential_claimer_filed_only_for_refund"): "That person filed only for a refund",
    ("persons", "filer_paid_most_of_home_upkeep"):
        "You paid over half the cost of keeping up their home",
}


def label_for(group: str, field: str) -> str:
    """The caption a person reads for this field. Raises KeyError rather than falling back to the
    field name: a header or a question that quietly said `wages_cents` is the defect this table
    exists to end. (`workbook.layout.label_for` resolves a tab or a tab name to its group first.)"""
    return LABELS[(group, field)]
