# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The 1040 line map — resolved engine fact path -> (form, line, label, IRS citation).

Phase 0 covers the core Form 1040 summary lines. Each carries a citation to the vendored 2025
Form 1040 (provenance language only — never an accuracy claim, World #1). value_cents is extracted
from the engine's resolved DollarWrapper value cent-exact.
"""

F1040 = "f1040--ty2025"


def _c(line):
    return {"source_doc": F1040, "locator": f"Form 1040 (2025), line {line}"}


# form_line_id -> {fact_path, label, citation, derived_from}. Order is display order.
LINE_MAP = [
    {"line_id": "1a", "fact_path": "/wages", "label": "Wages (W-2 box 1)", "citation": _c("1a"),
     "derived_from": ["w2s[].wages_cents"]},
    # Form W-2 box 10 through Form 2441 Part III — the taxable benefits (line 26) land
    # here; every baseline resolves it Complete at 0 (measured).
    {"line_id": "1e", "fact_path": "/taxableDependentCare",
     "label": "Taxable dependent care benefits from Form 2441, line 26", "citation": _c("1e"),
     "derived_from": ["w2s[].dependent_care_benefits_cents", "persons[].self_employed_dependent_care_benefits_cents", "persons[].dependent_care_plan_maximum_cents", "persons[].unable_to_care_for_self", "dependent_care_carryover_cents", "dependent_care_forfeited_cents",
                      "dependent_care_benefits_combat_pay_election"]},
    # Social Security benefits — the statements' box 5 total and the dictionary's
    # taxable amount (the worksheet: measured, $12,000 beside 52,000 of wages taxes 10,200;
    # beside 16,000, 3,000).
    {"line_id": "6a", "fact_path": "/socialSecurityBenefits", "label": "Social security benefits",
     "citation": _c("6a"), "derived_from": ["ssa1099s[].net_benefits_cents"]},
    {"line_id": "6b", "fact_path": "/taxableSocialSecurityBenefits",
     "label": "Taxable amount of social security benefits", "citation": _c("6b"),
     "derived_from": ["/socialSecurityBenefits", "ssa1099s[].net_benefits_cents",
                      # the line 6c election. and, behind a yes, the earlier-year
                      # rows Publication 915 Worksheet 2 or 3 refigures this line from.
                      "elects_lump_sum_benefits",
                      "ssa_lump_sum_years[].earlier_year",
                      "ssa_lump_sum_years[].lump_sum_portion_cents",
                      "ssa_lump_sum_years[].benefits_received_cents",
                      "ssa_lump_sum_years[].adjusted_gross_income_cents",
                      "ssa_lump_sum_years[].exclusions_cents",
                      "ssa_lump_sum_years[].tax_exempt_interest_cents",
                      "ssa_lump_sum_years[].taxable_benefits_reported_cents",
                      "ssa_lump_sum_years[].filed_jointly",
                      "ssa_lump_sum_years[].mfs_lived_with_spouse"]},
    # Form 1040 line 8, "Additional income from Schedule 1, line 10" — the dictionary's own
    # Schedule 1 line 10 ("Combine lines 1 through 7 and 9"), which every stream that lands on
    # Schedule 1 flows through: Schedule C (line 3), Schedule E rentals and K-1s (line 5),
    # unemployment compensation (line 7), W-2G winnings (line 8b) and 1099-MISC box 3 (line 8z,
    # 8g for an Alaska dividend). derived_from is the artifact's own answer: each entry is
    # DAG-true to /schedule1Line10AdditionalIncome (LineMapLockTest), pruned from line 9's list.
    {"line_id": "8", "fact_path": "/schedule1Line10AdditionalIncome",
     "label": "Additional income from Schedule 1, line 10", "citation": _c("8"),
     "derived_from": ["w2gs[].winnings_cents",
                      "g1099s[].unemployment_compensation_cents", "g1099s[].repaid_cents",
                      "misc1099s[].other_income_cents",
                      # the one return-level royalty activity — box 2 of every 1099-MISC,
                      # summed, plus the two root answers no box carries.
                      "misc1099s[].royalties_cents", "royalty_expenses_cents",
                      "royalty_is_oil_gas_geothermal",
                      # Schedule 1 line 8f, the taxable HSA distribution.
                      "hsa_distributions[].gross_distribution_cents",
                      "hsa_distributions[].qualified_medical_expenses_cents",
                      "schedule_c[].gross_receipts_cents", "schedule_c[].returns_and_allowances_cents",
                      "schedule_c[].cost_of_goods_sold_cents", "schedule_c[].other_business_income_cents",
                      "schedule_c[].total_expenses_cents", "schedule_c[].all_investment_at_risk",
                      "schedule_c[].amount_at_risk_cents",
                      "only_business_is_trading_securities",   # Form 8960's sole-trader answer
                      "rentals[].rents_received_cents", "rentals[].total_expenses_cents",
                      "rentals[].active_participation", "rentals[].fully_at_risk",
                      "rentals[].amount_at_risk_cents", "rentals[].prior_year_unallowed_loss_cents",
                      "rentals[].active_participation_when_loss_arose",
                      "rentals[].property_type", "rentals[].materially_participates_in_lessee",
                      # itemized expenses and depreciation inputs, joined at the same
                      # line 20/21 seam the lump total already reaches.
                      "rentals[].insurance_cents", "rentals[].management_fees_cents",
                      "rentals[].repairs_cents", "rentals[].taxes_cents",
                      "rentals[].building_basis_cents",
                      "rentals[].is_nonresidential_real_property",
                      "rentals[].building_uses_standard_gds",
                      "rentals[].placed_in_service_in_current_year",
                      "rentals[].placed_in_service_month",
                      "rentals[].has_five_year_property",
                      "rentals[].five_year_property_basis_cents",
                      "k1s[].ordinary_business_income_cents", "k1s[].interest_income_cents",
                      "k1s[].dividend_income_cents", "k1s[].royalties_cents",
                      "k1s[].publicly_traded_partnership", "k1s[].materially_participated",
                      "k1s[].basis_cents", "k1s[].fully_at_risk", "k1s[].amount_at_risk_cents",
                      "k1s[].guaranteed_payments_services_cents",
                      "k1s[].guaranteed_payments_capital_cents",
                      "k1s[].ptp_prior_year_unallowed_loss_cents",
                      # Schedule 1 line 2a (alimony received) is one of the five Part I legs
                      # this fact's own 2026-08-30 rebody names explicitly (income.xml).
                      "alimony_received_cents", "alimony_received_pre2019_agreement"]},
    {"line_id": "9", "fact_path": "/totalIncome", "label": "Total income", "citation": _c("9"),
     # Interest and dividends belong on Form 1040 line 9 in general, but this service REFUSES both
     # streams at the door (`mapper.UNSUPPORTED_STREAMS`) — so crediting them told a caller their
     # interest income had been considered when it could never have been supplied. `derived_from`
     # is SERVED provenance, and provenance must describe this service, not the form in the
     # abstract. They return here when the streams become covered; `test_gaps.py` fails if they
     # reappear before that.

     # W-2G box 1 IS here, because that is what "when the streams become covered" meant.
     # Gambling winnings reach line 9 through Schedule 1 line 8b (`/w2gWinnings` -> `/otherIncome`),
     # never through line 1a — wages and winnings are different lines on the printed form and the
     # provenance has to say which. Interest RETURNED here with 1099-INT coverage: boxes 1 and 3 both
     # feed `/interestIncome` -> line 2b -> line 9 (box 3 is taxable federally and excluded from
     # box 1 by the form's own instruction, so both are named).
     # Schedule C joined with its coverage: net profit reaches line 9 through Schedule 1 line 3,
     # and every summary-line input moves it — lines 1, 2, 4, 6 and 28 by name, because the net
     # is their arithmetic and no one of them is "the" income figure.
     "derived_from": ["w2s[].wages_cents", "w2gs[].winnings_cents", "int1099s[].interest_cents",
                      # line 6b joins the line 9 sum.
                      "/taxableSocialSecurityBenefits", "ssa1099s[].net_benefits_cents",
                      # Schedule 1 line 7 → line 10 → Form 1040 line 8, inside line 9.
                      "g1099s[].unemployment_compensation_cents", "g1099s[].repaid_cents",
                      "misc1099s[].other_income_cents",
                      # the one return-level royalty activity.
                      "misc1099s[].royalties_cents", "royalty_expenses_cents",
                      "royalty_is_oil_gas_geothermal",
                      "hsa_distributions[].gross_distribution_cents",
                      "hsa_distributions[].qualified_medical_expenses_cents",
                      "int1099s[].government_interest_cents",
                      # 1099-INT boxes 10, 11 and 12 adjust taxable interest (measured:
                      # +200.00, -100.00, -100.00 on line 9).
                      "int1099s[].market_discount_cents", "int1099s[].bond_premium_cents",
                      "int1099s[].treasury_bond_premium_cents",
                      # Form 1099-OID: boxes 1, 2, 5 and 8 add to taxable interest; boxes 6 and 10
                      # reduce it; box 11 (or the answer asked when it is blank) decides whether
                      # box 2 counts at all. Measured on the pinned engine.
                      "oid1099s[].original_issue_discount_cents",
                      "oid1099s[].other_periodic_interest_cents",
                      "oid1099s[].market_discount_cents",
                      "oid1099s[].acquisition_premium_cents",
                      "oid1099s[].treasury_oid_cents",
                      "oid1099s[].bond_premium_cents",
                      "oid1099s[].tax_exempt_oid_cents",
                      "oid1099s[].box2_is_tax_exempt",
                      "div1099s[].ordinary_dividends_cents",
                      "div1099s[].capital_gain_distributions_cents",
                      # Form 1099-B: boxes 1d, 1e and 1g net on Form 8949 and Schedule D
                      # into line 7. Measured on the pinned engine: a 4,000.00 gain adds 4,000.00; a
                      # 9,000.00 loss subtracts the 3,000.00 limit; box 1g nets a 2,000.00 loss
                      # to 500.00.
                      "b1099s[].proceeds_cents", "b1099s[].cost_basis_cents",
                      "b1099s[].wash_sale_loss_disallowed_cents",
                      "r1099s[].taxable_amount_cents",
                      "schedule_c[].gross_receipts_cents",
                      "schedule_c[].returns_and_allowances_cents",
                      "schedule_c[].cost_of_goods_sold_cents",
                      "schedule_c[].other_business_income_cents",
                      "schedule_c[].total_expenses_cents",
                      # box 32b's own follow-up. It moves the line 31 loss, so it moves
                      # every line the five summary inputs above do — measured beside a second
                      # business showing a 10,000 profit, a 3,000 loss capped at 0 against
                      # 3,000 gives line 9 58,250 -> 55,250.
                      # the lead's review: box 32a itself belongs here now. It was
                      # outside provenance because a false was REFUSED, so the box had one
                      # effective value and moved nothing; with 32b computing it moves this
                      # line exactly as its own follow-up does. Its two sibling streams
                      # (`rentals[].fully_at_risk`, `k1s[].fully_at_risk`) have been named
                      # here since their streams were covered — this closes the odd one out.
                      "schedule_c[].all_investment_at_risk",
                      "schedule_c[].amount_at_risk_cents",
                      "only_business_is_trading_securities",   # Form 8960's sole-trader answer
                      # Rentals joined with their coverage, through Schedule E line 21 ->
                      # Schedule 1 line 5. The two §469/§465 booleans and the Form 8582
                      # carry-in are here because they move the ALLOWED loss — measured: a No
                      # on active participation suspends it entirely. Unlike Schedule C, the
                      # stream stops at line 9: no SE tax (rental income is not
                      # self-employment) and no QBI at this pin, so lines 11/15/24 move only
                      # through their upstream served facts.
                      "rentals[].rents_received_cents", "rentals[].total_expenses_cents",
                      "rentals[].active_participation", "rentals[].fully_at_risk",
                      # the simplified Form 6198 amount at risk, and line 9 ONLY — the
                      # rentals rule above, re-measured for it. Beside a 10,000 Schedule C
                      # net, a 6,000 rental loss capped at 0 against 3,000 moves line 9
                      # 58,250 -> 55,250 and line 11 57,543 -> 54,543: the SAME 3,000, because
                      # rental income is not self-employment (the half-SE deduction stays 707)
                      # and carries no QBI at this pin (the deduction stays 1,859). Lines 11,
                      # 15, 16, 24 and 34 all move — every one of them THROUGH line 9.
                      "rentals[].amount_at_risk_cents",
                      "rentals[].prior_year_unallowed_loss_cents",
                      "rentals[].active_participation_when_loss_arose",
                      # the itemized expense lines and the depreciation inputs join line
                      # 9 through the same Schedule E line 20/21 seam the lump total already
                      # reaches — rental-5yr (25,440 gross rents) nets to 4,412 once insurance,
                      # management fees, repairs, taxes and the building/5-year depreciation
                      # inputs are all carried instead of a lump total.
                      "rentals[].insurance_cents", "rentals[].management_fees_cents",
                      "rentals[].repairs_cents", "rentals[].taxes_cents",
                      "rentals[].building_basis_cents",
                      "rentals[].is_nonresidential_real_property",
                      "rentals[].building_uses_standard_gds",
                      "rentals[].placed_in_service_in_current_year",
                      "rentals[].placed_in_service_month",
                      "rentals[].has_five_year_property",
                      "rentals[].five_year_property_basis_cents",
                      # Reg. §1.469-2(f)(6). WIRED ON A PROBE, not on the DAG's reach:
                      # the artifact says the self-rental flag can reach 9, 11, 12, 15, 16, 24,
                      # 33 and 34, and the probe says which of those it MOVES. Beside a second
                      # property at a 6,000 passive loss, answering the lessee question yes on
                      # a 12,000 self-rental profit gives line 9 54,250 -> 60,250 — the profit
                      # leaves the §8582 pool, so the other property's loss suspends instead of
                      # being absorbed. Re-measured beside a 10,000 Schedule C net (the loss-gate
                      # probe shape): lines 9, 11 and 15 each move by the SAME 6,000 and 16 and
                      # 24 follow from 15 — the half-SE deduction stays 707 and the qualified
                      # business income deduction stays 1,859, because recharacterized rental
                      # income is neither self-employment income nor §199A qualified business
                      # income at this pin. So: line 9 only, the rentals rule above.
                      # `property_type` is here because the type code DERIVES the self-rental
                      # flag; the rename table maps one dictionary path per service field and
                      # the code's own printed-box path is record-only, so the generator joins
                      # this field to `selfRental` — the writable that moves the line — and the
                      # table records both.
                      "rentals[].property_type",
                      "rentals[].materially_participates_in_lessee",
                      # K-1s joined with their coverage — the last stream. The loss trio and
                      # item D are here because they move the ALLOWED loss (suspension, basis
                      # cap, PTP netting); box 14A is NOT: SE earnings move lines 11 and 24
                      # only.
                      "k1s[].ordinary_business_income_cents", "k1s[].interest_income_cents",
                      "k1s[].dividend_income_cents", "k1s[].royalties_cents",
                      "k1s[].publicly_traded_partnership", "k1s[].materially_participated",
                      "k1s[].basis_cents", "k1s[].fully_at_risk",
                      # the at-risk answer's own follow-up, and line 9 ONLY, for the
                      # same measured reason as the rental one. Beside a 10,000 Schedule C
                      # net, a 6,000 box 1 loss capped at 0 against 3,000 moves lines 9 and 11
                      # by the same 3,000 (58,250 -> 55,250 and 57,543 -> 54,543) and leaves
                      # both the half-SE deduction and the QBI deduction where they were —
                      # a box 1 loss is not self-employment income and per-business QBI is
                      # not an intake this service carries.
                      "k1s[].amount_at_risk_cents",
                      # boxes 4a/4b flow nonpassive through Schedule E line 28
                      # column (k) into total income — never the Form 8582 pool, never
                      # QBI (IRC 199A(c)(4)(B)), so line 15 is untouched. Item G moves no
                      # served line: it decides a knockout (served as a refusal) and the
                      # PTP presumption, which only ever changes an ALLOWED loss already
                      # credited to the trio above.
                      "k1s[].guaranteed_payments_services_cents",
                      "k1s[].guaranteed_payments_capital_cents",
                      # the §469(k) carry-in, and ONLY it, of the box 20 code Z trio.
                      # MEASURED at the pin: it is a term of the PTP's step-1 combination, so
                      # a 3,000 carry-in against a 12,000 box 1 leaves an overall gain of
                      # 9,000 in Schedule E column (k) and total income falls by exactly the
                      # carry-in. The code Z amount itself moves nothing here — it is a
                      # section 199A quantity that never touches Schedule E — and the SSTB
                      # flag moves no served line at all (see line 15).
                      "k1s[].ptp_prior_year_unallowed_loss_cents",
                      # Form W-2 box 10 through Form 2441 Part III (the artifact: every
                      # one reaches 9, 11, 24, 33 and 34; measured moving 11 and 24).
                      "w2s[].dependent_care_benefits_cents",
                      # W-2 box 12 code W and Form 8889 Part I (Schedule 1 line 8z).
                      "w2s[].box12_w_cents",
                      "persons[].hsa_medicare",
                      "persons[].hsa_hdhp_coverage",
                      "persons[].hsa_hdhp_type",
                      "persons[].hsa_other_coverage",
                      "persons[].hsa_funding_distribution",
                      "persons[].hsa_spouse_contributed",
                      # the separate-return spouse's twelve coverage months (line 6's division).
                      "spouse_hsa_coverage_jan",
                      "spouse_hsa_coverage_feb",
                      "spouse_hsa_coverage_mar",
                      "spouse_hsa_coverage_apr",
                      "spouse_hsa_coverage_may",
                      "spouse_hsa_coverage_jun",
                      "spouse_hsa_coverage_jul",
                      "spouse_hsa_coverage_aug",
                      "spouse_hsa_coverage_sep",
                      "spouse_hsa_coverage_oct",
                      "spouse_hsa_coverage_nov",
                      "spouse_hsa_coverage_dec",
                      "persons[].hsa_marital_status_changed",
                      "persons[].hsa_marital_change_affects_limit",
                      "hsa_excess_in_w2_wages",
                      # the combat pay elections (the artifact: the Form 1040 and Form 2441
                      # Part II elections reach 24/33/34; the Part III election, through the taxable
                      # benefit on line 1e, reaches 9 and 11 too).
                      "dependent_care_benefits_combat_pay_election",
                      # the qualified HSA funding distribution (the artifact: both reach every
                      # served block through line 4b and Form 8889 line 10).
                      "r1099s[].qualified_hsa_funding_distribution_cents",
                      "persons[].hsa_prior_funding_distribution_election",
                      # the qualified charitable distribution (the artifact: line 4b reaches
                      # every served block).
                      "r1099s[].qualified_charitable_distribution_cents",
                      "r1099s[].qcd_to_split_interest_entity",
                      "persons[].qcd_prior_deducted_ira_contributions_cents",
                      # the indirect rollover (the artifact: lines 4b and 5b reach every block).
                      "r1099s[].rolled_over_cents",
                      "r1099s[].ira_one_rollover_per_year",
                      "r1099s[].reached_minimum_retirement_age", "r1099s[].public_safety_officer", "r1099s[].pso_premiums_paid_by_plan",
                      "r1099s[].pso_premiums_cents",
                      "r1099s[].date_of_payment", "r1099s[].box1_is_death_benefit_under_contract",
                      "r1099s[].acquired_in_reportable_policy_sale", "r1099s[].acquired_for_valuable_consideration",
                      "r1099s[].transfer_has_carryover_basis", "r1099s[].transfer_to_insured_or_related_party",
                      "r1099s[].death_benefit_basis_cents",
                      # the transfer month (the artifact: line 4b reaches every block).
                      "persons[].hsa_funding_distribution_transfer_month",
                      "persons[].hsa_testing_period_first_ineligible_month",
                      # the twelve coverage months (line 3's chart; the same reach).
                      "persons[].hsa_coverage_jan",
                      "persons[].hsa_coverage_feb",
                      "persons[].hsa_coverage_mar",
                      "persons[].hsa_coverage_apr",
                      "persons[].hsa_coverage_may",
                      "persons[].hsa_coverage_jun",
                      "persons[].hsa_coverage_jul",
                      "persons[].hsa_coverage_aug",
                      "persons[].hsa_coverage_sep",
                      "persons[].hsa_coverage_oct",
                      "persons[].hsa_coverage_nov",
                      "persons[].hsa_coverage_dec",
                      "persons[].hsa_medicare_first_month",
                      # the own-contribution question and its two amounts (Form 8889
                      # line 2; the artifact: the same reach as code W; measured moving 24 and 34).
                      "persons[].made_hsa_contributions",
                      "persons[].hsa_own_contributions_cents",
                      "persons[].hsa_own_contributions_after_year_end_cents",
                      "persons[].self_employed_dependent_care_benefits_cents",
                      "persons[].dependent_care_plan_maximum_cents", "persons[].unable_to_care_for_self",
                      "dependent_care_carryover_cents", "dependent_care_forfeited_cents",
                      # alimony:/taxableAlimonyReceived is a direct addend of
                      # /totalIncome (taxCalculations.xml's own addend list).
                      "alimony_received_cents", "alimony_received_pre2019_agreement"]},
    {"line_id": "11", "fact_path": "/agi", "label": "Adjusted gross income", "citation": _c("11"),
     # Schedule C is named here IN ADDITION to /totalIncome: the deductible half of
     # self-employment tax (Schedule 1 line 15) subtracts between lines 9 and 11 without
     # passing through any served fact, so line 11 moves on these inputs independently of
     # line 9.
     "derived_from": [
                      # the student loan interest deduction (Schedule 1 line 21 -> line
                      # 10 -> line 11; measured: $1,500 moves 52,000 -> 50,500).
                      "paid_student_loan_interest", "student_loans_qualify",
                      "student_loan_interest_cents",
                      # IRC 221(e)(1)'s two reductions, netted before the cap.
                      "student_loan_interest_employer_paid_cents",
                      # Form 1099-OID box 3: the early withdrawal penalty (Schedule 1 line 18).
                      "oid1099s[].early_withdrawal_penalty_cents",
                      # 1099-INT box 2, the same Schedule 1 line 18 penalty (measured: 300.00
                      # lowers line 11 by 300.00).
                      "int1099s[].early_withdrawal_penalty_cents",
                      "student_loan_interest_from_qtp_cents",
                      # the educator expenses adjustment (Schedule 1 line 11 -> line 10
                      # -> line 11; measured: $250 moves 52,000 -> 51,750, $400 serves as 300).
                      "persons[].k12_educator", "persons[].educator_expenses_cents",
                      # the IRA deduction (Schedule 1 line 20 -> line 10 -> line 11;
                      # measured: $3,000 moves 52,000 -> 49,000; on a separate return the
                      # other spouse's coverage phases it out).
                      # (`persons[].made_ira_contributions` is the gate, not an input the DAG
                      # reaches a line from — the dictionary's boolean only completes the
                      # section; the amount is what moves line 20.)
                      "persons[].traditional_ira_contributions_cents",
                      "persons[].roth_ira_contributions_cents",
                      "persons[].contributed_to_inherited_ira",
                      "persons[].inherited_ira_contribution_cents",
                      "spouse_covered_by_employer_plan",
                      "/totalIncome",
                      # K-1 box 14A joined with K-1 coverage: SE tax's deductible half
                      # subtracts here, the Schedule C shape.
                      "k1s[].se_earnings_cents",
                      # This WIRES what was once only STATED. The measurement was never in
                      # doubt: at the pin, beside a 10,000 Schedule C net, a -2,500 allowed
                      # loss gives self-employment tax 1,060 and AGI 57,720 against 1,413 and
                      # 57,543 at a deductible of 0 (`K1NegativeSeEarningsNowCOMPUTESTest`).
                      # What was missing was the DAG behind it — `derived_from` is locked
                      # against the committed artifact
                      # (`test_reachability_consumers.LineMapLockTest`) so that no entry is a
                      # hand-written shadow of the dictionary, and the generator was composing
                      # `/primaryFilerK1s/*/seEarningsAllowed` (a `<Filter path="/formK1s">`
                      # alias) into `/formK1s/*/*/seEarningsAllowed`, a doubled `/*` that is no
                      # declared Fact, so the leaf carried no downstream edge at all. The
                      # composition is fixed; all 83 residue nodes of that shape are gone and
                      # the lock now sees this route (`reaches` [] -> 9, 11, 12, 15, 16, 24,
                      # 33, 34).
                      "k1s[].deductible_se_loss_cents",
                      "schedule_c[].gross_receipts_cents",
                      "schedule_c[].returns_and_allowances_cents",
                      "schedule_c[].cost_of_goods_sold_cents",
                      "schedule_c[].other_business_income_cents",
                      "schedule_c[].total_expenses_cents",
                      # the Schedule C amount at risk is named here for the reason the
                      # five above are — it moves the Schedule SE base, so line 11 moves by
                      # MORE than line 9 does. Measured beside a second business showing a
                      # 10,000 profit: a 3,000 loss capped at 0 against 3,000 moves line 9 by
                      # 3,000 and line 11 by 2,788 (57,543 -> 54,755), the half-SE deduction
                      # falling 707 -> 495 on a self-employment base of 10,000 -> 7,000. The
                      # rentals and K-1 amounts are NOT here: measured the same way, both move
                      # lines 9 and 11 by the identical figure.
                      # the lead's review: box 32a moves this line for the same
                      # measured reason its follow-up does — see line 9.
                      "schedule_c[].all_investment_at_risk",
                      "schedule_c[].amount_at_risk_cents",
                      "only_business_is_trading_securities",   # Form 8960's sole-trader answer
                      # Form W-2 box 10 through Form 2441 Part III (the artifact: every
                      # one reaches 9, 11, 24, 33 and 34; measured moving 11 and 24).
                      "w2s[].dependent_care_benefits_cents",
                      # W-2 box 12 code W and Form 8889 Part I (Schedule 1 line 8z).
                      "w2s[].box12_w_cents",
                      "persons[].hsa_medicare",
                      "persons[].hsa_hdhp_coverage",
                      "persons[].hsa_hdhp_type",
                      "persons[].hsa_other_coverage",
                      "persons[].hsa_funding_distribution",
                      "persons[].hsa_spouse_contributed",
                      # the separate-return spouse's twelve coverage months (line 6's division).
                      "spouse_hsa_coverage_jan",
                      "spouse_hsa_coverage_feb",
                      "spouse_hsa_coverage_mar",
                      "spouse_hsa_coverage_apr",
                      "spouse_hsa_coverage_may",
                      "spouse_hsa_coverage_jun",
                      "spouse_hsa_coverage_jul",
                      "spouse_hsa_coverage_aug",
                      "spouse_hsa_coverage_sep",
                      "spouse_hsa_coverage_oct",
                      "spouse_hsa_coverage_nov",
                      "spouse_hsa_coverage_dec",
                      "persons[].hsa_marital_status_changed",
                      "persons[].hsa_marital_change_affects_limit",
                      "hsa_excess_in_w2_wages",
                      # the combat pay elections (the artifact: the Form 1040 and Form 2441
                      # Part II elections reach 24/33/34; the Part III election, through the taxable
                      # benefit on line 1e, reaches 9 and 11 too).
                      "dependent_care_benefits_combat_pay_election",
                      # the qualified HSA funding distribution (the artifact: both reach every
                      # served block through line 4b and Form 8889 line 10).
                      "r1099s[].qualified_hsa_funding_distribution_cents",
                      "persons[].hsa_prior_funding_distribution_election",
                      # the qualified charitable distribution (the artifact: line 4b reaches
                      # every served block).
                      "r1099s[].qualified_charitable_distribution_cents",
                      "r1099s[].qcd_to_split_interest_entity",
                      "persons[].qcd_prior_deducted_ira_contributions_cents",
                      # the indirect rollover (the artifact: lines 4b and 5b reach every block).
                      "r1099s[].rolled_over_cents",
                      "r1099s[].ira_one_rollover_per_year",
                      "r1099s[].reached_minimum_retirement_age", "r1099s[].public_safety_officer", "r1099s[].pso_premiums_paid_by_plan",
                      "r1099s[].pso_premiums_cents",
                      "r1099s[].date_of_payment", "r1099s[].box1_is_death_benefit_under_contract",
                      "r1099s[].acquired_in_reportable_policy_sale", "r1099s[].acquired_for_valuable_consideration",
                      "r1099s[].transfer_has_carryover_basis", "r1099s[].transfer_to_insured_or_related_party",
                      "r1099s[].death_benefit_basis_cents",
                      # the transfer month (the artifact: line 4b reaches every block).
                      "persons[].hsa_funding_distribution_transfer_month",
                      "persons[].hsa_testing_period_first_ineligible_month",
                      # the twelve coverage months (line 3's chart; the same reach).
                      "persons[].hsa_coverage_jan",
                      "persons[].hsa_coverage_feb",
                      "persons[].hsa_coverage_mar",
                      "persons[].hsa_coverage_apr",
                      "persons[].hsa_coverage_may",
                      "persons[].hsa_coverage_jun",
                      "persons[].hsa_coverage_jul",
                      "persons[].hsa_coverage_aug",
                      "persons[].hsa_coverage_sep",
                      "persons[].hsa_coverage_oct",
                      "persons[].hsa_coverage_nov",
                      "persons[].hsa_coverage_dec",
                      "persons[].hsa_medicare_first_month",
                      # the own-contribution question and its two amounts (Form 8889
                      # line 2; the artifact: the same reach as code W; measured moving 24 and 34).
                      "persons[].made_hsa_contributions",
                      "persons[].hsa_own_contributions_cents",
                      "persons[].hsa_own_contributions_after_year_end_cents",
                      "persons[].self_employed_dependent_care_benefits_cents",
                      "persons[].dependent_care_plan_maximum_cents", "persons[].unable_to_care_for_self",
                      "dependent_care_carryover_cents", "dependent_care_forfeited_cents",
                      # Schedule 1 line 19a (alimony paid) subtracts through
                      # /adjustmentsExcludingStudentLoanAndIra directly into AGI.
                      "alimony_paid_cents", "alimony_paid_pre2019_agreement",
                      "alimony_paid_section_682_trust"]},
    # 2026-09-22: the served fact was `/standardDeduction`, and Form 1040 line 12 is not that — the
    # printed line is "Standard deduction or itemized deductions", which the engine computes as
    # `/standardOrItemizedDeductions`. While nothing this service builds could itemize the two were
    # the same figure on every return (MEASURED: all 175 committed fixtures, no difference), so the
    # defect was latent. It stops being latent the moment Schedule A is offered: an itemizing return
    # would print the STANDARD deduction on the line it deducted the itemized total on (measured:
    # 15,750.00 printed where 33,000.00 was deducted) — a complete and wrong printed line.
    {"line_id": "12", "fact_path": "/standardOrItemizedDeductions",
     "label": "Standard deduction or itemized deductions",
     # birth_month belongs here: it is what the age-65 additional standard deduction turns on
     # (via the engine's dayBeforeDateOfBirth -> age65OrOlder chain), and omitting it from this
     # provenance list is what made it easy to miss.
     "citation": _c("12"),
     # Tax-exempt interest joined with 1099-INT coverage: line 12 has the senior deduction since
     # TY2025, and its MAGI phase-out adds tax-exempt interest back — so for a 65-or-older filer
     # the box 8 figure genuinely moves this line.
     # spouse_itemizes joined with mfs coverage: a yes zeroes this line outright
     # (IRC 63(c)(6)(A)), the engine's own first Switch arm.
     "derived_from": [
                      # a filer someone claims gets the dependent's standard deduction
                      # (earned income + $450, capped) — measured 15,750 -> 10,450 at wages 10,000.
                      # Only the root is wired here: the static DAG reaches line 12 from
                      # `canBeClaimed` but not from the chain's later links (the lock's rule is
                      # no DAG-false provenance), whose movement is visible on line 33.
                      "persons[].someone_can_claim_you",
                      # the couple's filing requirement decides whether a claimable
                      # spouse is claimed — 31,500 -> 16,450 at 8,000 each.
                      "couple_required_to_file", "couple_files_only_for_refund","filing_status", "persons[].birth_year", "persons[].birth_month",
                      "int1099s[].tax_exempt_interest_cents",
                      "div1099s[].exempt_interest_dividends_cents",
                      "spouse_itemizes",
                      # Form 1040 line 12's own blindness checkbox, per filer row
                      # (“You: Are blind”, and “Spouse: Is blind” on a joint return).
                      "persons[].is_blind",
                      # the separate-return spouse chain — the spouse's age and
                      # blindness amounts join this line when the chain reaches them.
                      "spouse_files_return", "spouse_had_gross_income",
                      "spouse_can_be_claimed", "spouse_65_or_older", "spouse_is_blind"]},
    {"line_id": "15", "fact_path": "/taxableIncome", "label": "Taxable income", "citation": _c("15"),
     # Box 5 joined with 1099-DIV coverage: section 199A dividends feed the 20% QBI deduction
     # (Form 1040 line 13), which subtracts here without passing through any served fact.
     # Schedule C joined with its coverage for the same reason box 5 did: net profit feeds the
     # QBI deduction, which subtracts here without passing through any served fact.
     # box 20 code Z joins for the reason box 5 did — the qualified PTP amount is the
     # other half of Form 8995 line 6, and the 20% it earns on line 9 subtracts here without
     # passing through any served fact (measured: a 12,000 code Z amount below the section
     # 199A threshold moves this line by 2,400).

     # ITS SSTB FLAG JOINED WITH and it was outside this list until then for a reason
     # that has stopped being true. A measurement found a true answer reducing the amount inside
     # Form 8995 (12,000 to 5,952 at the 49.6% applicable percentage) while
     # `/qualifiedBusinessIncomeDeduction` routed to its $0 catch-all on every
     # above-threshold return, because the Form 8995-A arm wants `qbi:/claims8995A` and no
     # intake emitted its writable — so the flag moved a FORM line and no served one, and was
     # STATED instead. The scaffold claims Form 8995-A on every return over an EMPTY
     # `qbi:/qualifiedBusinesses`, the qualified REIT dividend / publicly traded partnership
     # half (Form 8995-A lines 28-32) computes with no per-business detail, and the flag now
     # reaches THIS line: measured 1,190 against 2,400 in the phase-in range, and 0 against
     # 2,400 past the upper threshold. `K1QualifiedPtpCodeZGateTest.test_the_SSTB_flag_moves_
     # a_FORM_line_AND_a_SERVED_line_which_is_this_tests_INVERSION` holds that measurement.

     # the deductible part of a box 14A LOSS moves this line and box 14A ITSELF does
     # NOT, which is a measurement rather than a judgement. The deductible part could once not
     # be LISTED (line 11 carries that reason); box 14A itself was DAG-ALLOWED here throughout and
     # was kept out by the measurement alone. With the composition repaired, measurement is
     # now all that decides for either — and it splits the pair.
     # The half-SE deduction is APPORTIONED to the qualified business before it reduces the
     # QBI base, so a POSITIVE box 14A leaves the Schedule C business's share untouched
     # (measured: a +4,000 box 14A beside a 10,000 Schedule C net raises SE tax 1,413 -> 1,978
     # and leaves the deduction at 1,859) — box 14A reaches line 15 only through /agi, which
     # is already named. The DAG has always ALLOWED `k1s[].se_earnings_cents` here and it
     # stays out: a CAN the lock permits but no resolve turns into a WILL is a ceiling, not
     # provenance. A NEGATIVE allowed loss shrinks the whole half-SE deduction and the
     # Schedule C business absorbs all of it: 1,859 at a deductible of 0, 1,894 at -2,500,
     # 1,943 at -6,000 (`K1NegativeSeEarningsNowCOMPUTESTest.test_the_deductible_amount_
     # moves_taxable_income_beyond_AGI`). That is a move /agi and the line-12 amount cannot
     # account for, so it is named here.
     # …and the line-12 amount, which is the printed line's own fact since 2026-09-22 — the
     # standard deduction OR the itemized total, whichever this return spends.
     "derived_from": ["/agi", "/standardOrItemizedDeductions", "div1099s[].section_199a_dividends_cents",
                      "k1s[].deductible_se_loss_cents",
                      "k1s[].qualified_ptp_income_cents",
                      "k1s[].qualified_ptp_is_sstb",
                      "k1s[].section_199a_qbi_cents",
                      "schedule_c[].gross_receipts_cents",
                      "schedule_c[].returns_and_allowances_cents",
                      "schedule_c[].cost_of_goods_sold_cents",
                      "schedule_c[].other_business_income_cents",
                      "schedule_c[].total_expenses_cents",
                      # same measurement, the QBI half of it. Capping the 3,000 loss at
                      # 0 leaves the qualified business income deduction at 1,859 and capping
                      # it at 3,000 drops it to 1,301 (20% of the net less its share of the
                      # half-SE deduction, 10,000 - 707 against 7,000 - 495), so line 15 moves
                      # 39,934 -> 37,704 where /agi and /standardDeduction account for only
                      # 2,788 of it. The rentals and K-1 amounts leave the deduction alone.
                      # the lead's review: box 32a moves this line for the same
                      # measured reason its follow-up does — see line 9.
                      "schedule_c[].all_investment_at_risk",
                      "schedule_c[].amount_at_risk_cents"]},
    {"line_id": "16", "fact_path": "/tentativeTaxFromTaxableIncome", "label": "Tax",
     # Qualified dividends and the 2a/2b slices joined with 1099-DIV coverage: they re-rate the tax
     # through the QDCGT worksheet without changing line 15.
     "citation": _c("16"),
     "derived_from": ["/taxableIncome", "filing_status", "div1099s[].qualified_dividends_cents",
                      "div1099s[].capital_gain_distributions_cents",
                      "div1099s[].unrecaptured_1250_gain_cents",
                      # the holding period re-rates a Form 1099-B gain without changing
                      # line 15 (measured: 4,000.00 at 24% short-term, 15% long-term). The dates
                      # decide it where both are given; box 2 where one is not.
                      "b1099s[].term", "b1099s[].date_acquired", "b1099s[].date_sold",
                      # K-1 qualified dividends joined with K-1 coverage: all three forms'
                      # qualified box re-rates through the QDCGT worksheet, as box 1b does.
                      "k1s[].qualified_dividends_cents"]},
    {"line_id": "24", "fact_path": "/totalTax", "label": "Total tax", "citation": _c("24"),
     # Schedule C joined with its coverage: self-employment tax (Schedule SE -> Schedule 2
     # line 4) adds here without passing through line 16 or any served fact.
     # The dependent qualifiers joined with dependents coverage: the child tax credit and the
     # credit for other dependents subtract between lines 16 and 24 without passing through
     # a served fact, and every qualifier moves which credit (or none) applies.
     "derived_from": ["/tentativeTaxFromTaxableIncome",
                      "persons[].relationship", "persons[].months_in_home",
                      "persons[].is_married", "persons[].provided_own_support",
                      "persons[].gross_income_under_limit",
                      "persons[].filer_provided_over_half_support",
                      "persons[].could_be_qualifying_child_of_another",
                      # the joint-return test, wired on a PROBE and not on the DAG's
                      # reach. Resolving the same household claimed and not-claimed at the
                      # pin moved exactly three served lines — 24 (1,465 -> 3,665), 33
                      # (6,345 -> 6,000) and 34 (4,880 -> 2,335). Line 16 did NOT move: the
                      # tax before credits is the same return, and the whole 2,200 is the
                      # child tax credit falling away between lines 16 and 24. Line 34's
                      # provenance is the two served facts it subtracts, so it names no
                      # qualifier here — the convention every other dependent answer follows.
                      "persons[].files_joint_return_with_spouse",
                      "persons[].required_to_file_with_spouse",
                      "persons[].joint_return_only_for_refund",
                      # the custodial-parent tier, wired on a PROBE. On the split-parents
                      # household a parent who signed the declaration away and is the custodial
                      # parent keeps the EITC and loses the CTC: line 24 1,465 -> 3,665, line 33
                      # unchanged at 6,345 (the 345 EITC stays), line 34 follows. The four
                      # earlier gate links still move nothing and stay unwired.
                      "persons[].written_declaration",
                      "persons[].nights_with_filer_vs_other_parent",
                      "persons[].filer_agi_higher_than_other_parent",
                      # the non-parental split, wired on a PROBE. Its deep cells take the
                      # child out of the dependency claim (line 24 1,465 -> 3,665) — and the
                      # disqualified cells also take the EITC (line 33 6,345 -> 6,000).
                      "persons[].parents_meet_divorced_or_separated_rule",
                      "persons[].a_parent_signed_declaration_not_to_claim",
                      "persons[].custodial_parent_claims_child_as_qualifying_person",
                      "persons[].filer_agi_higher_than_custodial_parent",
                      "k1s[].se_earnings_cents",
                      # self-employment tax is computed off the ALLOWED box 14A figure,
                      # which for a loss is `k1s[].deductible_se_loss_cents` — measured, 1,060
                      # at -2,500 against 1,413 at 0 beside a 10,000 Schedule C net. LISTED
                      # since the alias composition the DAG lock reads was repaired.
                      "k1s[].deductible_se_loss_cents",
                      # W-2 box 5 is the Form 8959 base, and Additional Medicare Tax lands
                      # in total tax without passing through line 16 or any other served fact.
                      # MEASURED at the pin, not inferred: box 5 = 250,000 against box 1 = 230,000
                      # moved line 24 from 50,117.00 to 50,297.00 — 0.9% of the 20,000 above the
                      # 200,000 threshold. Box 3 and box 4 got rename-table rows in the same unit
                      # and NO row here: their reach is real but no fixture makes a resolve move.
                      "w2s[].medicare_wages_cents",
                      "schedule_c[].gross_receipts_cents",
                      "schedule_c[].returns_and_allowances_cents",
                      "schedule_c[].cost_of_goods_sold_cents",
                      "schedule_c[].other_business_income_cents",
                      "schedule_c[].total_expenses_cents",
                      # self-employment tax is computed off the CAPPED net, so the
                      # amount at risk lands in total tax without passing line 16 — measured,
                      # 1,413 at a cap of 0 against 989 at 3,000, line 24 5,966 -> 5,278 where
                      # line 16 moved only 264. The rentals and K-1 amounts move no
                      # self-employment tax at all, so neither is named here.
                      # the lead's review: box 32a moves this line for the same
                      # measured reason its follow-up does — see line 9.
                      "schedule_c[].all_investment_at_risk",
                      "schedule_c[].amount_at_risk_cents",
                      "only_business_is_trading_securities",   # Form 8960's sole-trader answer
                      # the additional 20% tax on HSA distributions (Form 8889 line 17b,
                      # Schedule 2), less the attested exception amount.
                      "hsa_distributions[].gross_distribution_cents",
                      "hsa_distributions[].qualified_medical_expenses_cents",
                      "persons[].hsa_exception_amount_cents",
                      # the child and dependent care credit (Form 2441 line 11, Schedule 3
                      # line 2) inside line 20 — the per-person amounts; the providers' own
                      # fields change no dollar (measured).
                      "persons[].care_expenses_cents",
                      # Form 1095-A's grid (Form 8962) and the root questions a form reaches.
                      "f1095as[].jan_premium_cents",
                      "f1095as[].jan_slcsp_cents",
                      "f1095as[].jan_aptc_cents",
                      "f1095as[].feb_premium_cents",
                      "f1095as[].feb_slcsp_cents",
                      "f1095as[].feb_aptc_cents",
                      "f1095as[].mar_premium_cents",
                      "f1095as[].mar_slcsp_cents",
                      "f1095as[].mar_aptc_cents",
                      "f1095as[].apr_premium_cents",
                      "f1095as[].apr_slcsp_cents",
                      "f1095as[].apr_aptc_cents",
                      "f1095as[].may_premium_cents",
                      "f1095as[].may_slcsp_cents",
                      "f1095as[].may_aptc_cents",
                      "f1095as[].jun_premium_cents",
                      "f1095as[].jun_slcsp_cents",
                      "f1095as[].jun_aptc_cents",
                      "f1095as[].jul_premium_cents",
                      "f1095as[].jul_slcsp_cents",
                      "f1095as[].jul_aptc_cents",
                      "f1095as[].aug_premium_cents",
                      "f1095as[].aug_slcsp_cents",
                      "f1095as[].aug_aptc_cents",
                      "f1095as[].sep_premium_cents",
                      "f1095as[].sep_slcsp_cents",
                      "f1095as[].sep_aptc_cents",
                      "f1095as[].oct_premium_cents",
                      "f1095as[].oct_slcsp_cents",
                      "f1095as[].oct_aptc_cents",
                      "f1095as[].nov_premium_cents",
                      "f1095as[].nov_slcsp_cents",
                      "f1095as[].nov_aptc_cents",
                      "f1095as[].dec_premium_cents",
                      "f1095as[].dec_slcsp_cents",
                      "f1095as[].dec_aptc_cents",
                      "marketplace_estimated_income_at_least_100_fpl",
                      "below_poverty_line_not_eligible_for_medicaid_due_to_immigration",
                      "dependents_modified_agi_cents",
                      "paid_prior_year_care_expenses_this_year",
                      "prior_year_form_2441_line_3_cents",
                      "prior_year_expenses_paid_this_year_cents",
                      "prior_year_had_two_or_more_qualifying_persons",
                      "prior_year_excluded_or_deducted_benefits_cents",
                      "prior_year_lower_earned_income_cents",
                      "prior_year_form_2441_line_6_cents",
                      "prior_year_agi_cents",
                      "mfs_ptc_exception",
                      "mfs_ptc_exception_fourth_year",
                      # Publication 596 Rule 14, the childless-EIC main-home-in-the-U.S.
                      # test — invited on every return, optional (absent reads the engine's own
                      # complete-safe true). The artifact: the earned income credit feeds the
                      # Form 5695/8812 credit-limit worksheets, so this reaches 24 too.
                      "main_home_in_us_over_half_year",
                      # Form W-2 box 10 through Form 2441 Part III (the artifact: every
                      # one reaches 9, 11, 24, 33 and 34; measured moving 11 and 24).
                      "w2s[].dependent_care_benefits_cents",
                      # W-2 box 12 code W and Form 8889 Part I's questions (the
                      # artifact: each reaches 6b, 8, 9, 11, 12, 15, 16, 24, 33, 34 through the
                      # Schedule 1 line 8z excess income; measured moving 9, 11, 15, 16, 24, 33, 34
                      # — 5,000 self-only: 700 of income and 42 of Form 5329 excise).
                      "w2s[].box12_w_cents",
                      "persons[].hsa_medicare",
                      "persons[].hsa_hdhp_coverage",
                      "persons[].hsa_hdhp_type",
                      "persons[].hsa_other_coverage",
                      "persons[].hsa_funding_distribution",
                      "persons[].hsa_spouse_contributed",
                      # the separate-return spouse's twelve coverage months (line 6's division).
                      "spouse_hsa_coverage_jan",
                      "spouse_hsa_coverage_feb",
                      "spouse_hsa_coverage_mar",
                      "spouse_hsa_coverage_apr",
                      "spouse_hsa_coverage_may",
                      "spouse_hsa_coverage_jun",
                      "spouse_hsa_coverage_jul",
                      "spouse_hsa_coverage_aug",
                      "spouse_hsa_coverage_sep",
                      "spouse_hsa_coverage_oct",
                      "spouse_hsa_coverage_nov",
                      "spouse_hsa_coverage_dec",
                      "persons[].hsa_marital_status_changed",
                      "persons[].hsa_marital_change_affects_limit",
                      "hsa_excess_in_w2_wages",
                      # the combat pay elections (the artifact: the Form 1040 and Form 2441
                      # Part II elections reach 24/33/34; the Part III election, through the taxable
                      # benefit on line 1e, reaches 9 and 11 too).
                      "combat_pay_election", "cdcc_combat_pay_election",
                      "dependent_care_benefits_combat_pay_election",
                      # the qualified HSA funding distribution (the artifact: both reach every
                      # served block through line 4b and Form 8889 line 10).
                      "r1099s[].qualified_hsa_funding_distribution_cents",
                      "persons[].hsa_prior_funding_distribution_election",
                      # the qualified charitable distribution (the artifact: line 4b reaches
                      # every served block).
                      "r1099s[].qualified_charitable_distribution_cents",
                      "r1099s[].qcd_to_split_interest_entity",
                      "persons[].qcd_prior_deducted_ira_contributions_cents",
                      # the indirect rollover (the artifact: lines 4b and 5b reach every block).
                      "r1099s[].rolled_over_cents",
                      "r1099s[].ira_one_rollover_per_year",
                      "r1099s[].reached_minimum_retirement_age", "r1099s[].public_safety_officer", "r1099s[].pso_premiums_paid_by_plan",
                      "r1099s[].pso_premiums_cents",
                      "r1099s[].date_of_payment", "r1099s[].box1_is_death_benefit_under_contract",
                      "r1099s[].acquired_in_reportable_policy_sale", "r1099s[].acquired_for_valuable_consideration",
                      "r1099s[].transfer_has_carryover_basis", "r1099s[].transfer_to_insured_or_related_party",
                      "r1099s[].death_benefit_basis_cents",
                      # the transfer month (the artifact: line 4b reaches every block).
                      "persons[].hsa_funding_distribution_transfer_month",
                      "persons[].hsa_testing_period_first_ineligible_month",
                      # the twelve coverage months (line 3's chart; the same reach).
                      "persons[].hsa_coverage_jan",
                      "persons[].hsa_coverage_feb",
                      "persons[].hsa_coverage_mar",
                      "persons[].hsa_coverage_apr",
                      "persons[].hsa_coverage_may",
                      "persons[].hsa_coverage_jun",
                      "persons[].hsa_coverage_jul",
                      "persons[].hsa_coverage_aug",
                      "persons[].hsa_coverage_sep",
                      "persons[].hsa_coverage_oct",
                      "persons[].hsa_coverage_nov",
                      "persons[].hsa_coverage_dec",
                      "persons[].hsa_medicare_first_month",
                      # the own-contribution question and its two amounts (Form 8889
                      # line 2; the artifact: the same reach as code W; measured moving 24 and 34).
                      "persons[].made_hsa_contributions",
                      "persons[].hsa_own_contributions_cents",
                      "persons[].hsa_own_contributions_after_year_end_cents",
                      "persons[].hsa_december_31_value_cents",
                      "persons[].hsa_prior_year_excess_cents",
                      # Form W-2 box 12's four uncollected-tax codes, Schedule 2
                      # line 13 (the artifact: 24, 33, 34; measured moving 24 and 34).
                      # Form 8880 — the eight box 12 deferral codes (line 2; H also
                      # reaches 9 and 11 per the DAG, measured moving neither), code G's plan
                      # answer, the student test, the Roth-and-ABLE follow-up (line 1), the
                      # line-4 distribution answers and the filed-jointly pair (measured on 24
                      # and 34; the artifact: each reaches 24, 33, 34).
                      "w2s[].box12_d_cents",
                      "w2s[].box12_e_cents",
                      "w2s[].box12_g_cents",
                      "w2s[].box12_h_cents",
                      "w2s[].box12_s_cents",
                      "w2s[].box12_aa_cents",
                      "w2s[].box12_bb_cents",
                      "w2s[].box12_ee_cents",
                      "w2s[].box12_g_governmental_plan",
                      "persons[].roth_ira_and_able_contributions_cents",
                      "persons[].received_retirement_distributions_2023_2024",
                      "persons[].retirement_distributions_2023_cents",
                      "persons[].retirement_distributions_2024_cents",
                      "persons[].received_retirement_distributions_after_year_end",
                      "persons[].retirement_distributions_after_year_end_cents",
                      "filed_jointly_2023",
                      "filed_jointly_2024",
                      "w2s[].box12_a_cents",
                      "w2s[].box12_b_cents",
                      "w2s[].box12_m_cents",
                      "w2s[].box12_n_cents",
                      "persons[].self_employed_dependent_care_benefits_cents",
                      "persons[].dependent_care_plan_maximum_cents", "persons[].unable_to_care_for_self",
                      "dependent_care_carryover_cents", "dependent_care_forfeited_cents"
                      ]},
    {"line_id": "25d", "fact_path": "/totalWithholding", "label": "Federal income tax withheld",
     # 25d is the TOTAL of 25a/25b/25c, and W-2G box 4 is named by 25c ("Include on line 25c any
     # Federal income tax withheld on your Form(s) W-2G"). Verified at the pin rather than inferred
     # from the instructions: taxCalculations.xml's `/totalWithholding` Add carries
     # `formW2Gs:/w2gWithholding` as a fourth addend alongside the W-2, 1099 and Form 8959 terms.
     "citation": _c("25d"),
     "derived_from": ["w2s[].withholding_cents", "w2gs[].federal_withholding_cents",
                      # box 6 above the regular 1.45% rate on box 5 is Form 8959 line 24
                      # (Additional Medicare Tax withholding), one of the Add's four terms —
                      # measured, profile-additional-medicare (moved to the oracle's figure).
                      "w2s[].medicare_withheld_cents",
                      # the benefit statement's withholding box, inside line 25b.
                      "ssa1099s[].federal_withholding_cents",
                      "g1099s[].federal_withholding_cents",
                      "misc1099s[].federal_withholding_cents",
                      "int1099s[].federal_withholding_cents",
                      "oid1099s[].federal_withholding_cents",             # Form 1099-OID box 4
                      "div1099s[].federal_withholding_cents",
                      "r1099s[].federal_withholding_cents"]},
    # line 26 — the caller's own figure once the line 26 question is answered yes; a no is
    # a 0 the dictionary's Switch produces. Measured: $1,000 here moves line 33 by $1,000.
    {"line_id": "26", "fact_path": "/estimatedAndFromLastYear",
     "label": "2025 estimated tax payments and amount applied from 2024 return",
     "citation": _c("26"),
     "derived_from": ["paid_estimated_taxes", "estimated_tax_payments_cents"]},
    {"line_id": "33", "fact_path": "/totalPayments", "label": "Total payments", "citation": _c("33"),
     # The refundable additional child tax credit (Form 8812) joined with dependents coverage: it
     # lands in total payments, so the qualifiers that decide it are provenance here too —
     # measured: an mfj child return pays 522 of ACTC past a zeroed tax.
     "derived_from": ["/totalWithholding",
                      # line 26 joins total payments (5,400 -> 6,400 on a $1,000 answer).
                      "/estimatedAndFromLastYear",
                      "persons[].relationship", "persons[].months_in_home",
                      "persons[].is_married", "persons[].provided_own_support",
                      "persons[].gross_income_under_limit",
                      "persons[].filer_provided_over_half_support",
                      "persons[].could_be_qualifying_child_of_another",
                      # measured with line 24 above — a dependent the joint-return test
                      # fails takes the 345 earned income credit out of total payments with
                      # them (6,345 -> 6,000).
                      "persons[].files_joint_return_with_spouse",
                      "persons[].required_to_file_with_spouse",
                      "persons[].joint_return_only_for_refund",
                      # a filer someone claims gets no earned income credit (649 -> 0 at
                      # wages 10,000). on a joint return the couple's answers decide it.
                      "couple_required_to_file", "couple_files_only_for_refund",
                      "persons[].someone_can_claim_you", "persons[].expect_to_be_claimed",
                      "persons[].potential_claimer_must_file", "persons[].potential_claimer_filed",
                      "persons[].potential_claimer_filed_only_for_refund",
                      # the disqualified cells of the non-parental split take the EITC
                      # (6,345 -> 6,000); the split-benefits cell keeps it.
                      "persons[].parents_meet_divorced_or_separated_rule",
                      "persons[].a_parent_signed_declaration_not_to_claim",
                      "persons[].custodial_parent_claims_child_as_qualifying_person",
                      "persons[].filer_agi_higher_than_custodial_parent",
                      # Form 1095-A's grid (Form 8962) and the root questions a form reaches.
                      "f1095as[].jan_premium_cents",
                      "f1095as[].jan_slcsp_cents",
                      "f1095as[].jan_aptc_cents",
                      "f1095as[].feb_premium_cents",
                      "f1095as[].feb_slcsp_cents",
                      "f1095as[].feb_aptc_cents",
                      "f1095as[].mar_premium_cents",
                      "f1095as[].mar_slcsp_cents",
                      "f1095as[].mar_aptc_cents",
                      "f1095as[].apr_premium_cents",
                      "f1095as[].apr_slcsp_cents",
                      "f1095as[].apr_aptc_cents",
                      "f1095as[].may_premium_cents",
                      "f1095as[].may_slcsp_cents",
                      "f1095as[].may_aptc_cents",
                      "f1095as[].jun_premium_cents",
                      "f1095as[].jun_slcsp_cents",
                      "f1095as[].jun_aptc_cents",
                      "f1095as[].jul_premium_cents",
                      "f1095as[].jul_slcsp_cents",
                      "f1095as[].jul_aptc_cents",
                      "f1095as[].aug_premium_cents",
                      "f1095as[].aug_slcsp_cents",
                      "f1095as[].aug_aptc_cents",
                      "f1095as[].sep_premium_cents",
                      "f1095as[].sep_slcsp_cents",
                      "f1095as[].sep_aptc_cents",
                      "f1095as[].oct_premium_cents",
                      "f1095as[].oct_slcsp_cents",
                      "f1095as[].oct_aptc_cents",
                      "f1095as[].nov_premium_cents",
                      "f1095as[].nov_slcsp_cents",
                      "f1095as[].nov_aptc_cents",
                      "f1095as[].dec_premium_cents",
                      "f1095as[].dec_slcsp_cents",
                      "f1095as[].dec_aptc_cents",
                      "marketplace_estimated_income_at_least_100_fpl",
                      "below_poverty_line_not_eligible_for_medicaid_due_to_immigration",
                      "dependents_modified_agi_cents",
                      "paid_prior_year_care_expenses_this_year",
                      "prior_year_form_2441_line_3_cents",
                      "prior_year_expenses_paid_this_year_cents",
                      "prior_year_had_two_or_more_qualifying_persons",
                      "prior_year_excluded_or_deducted_benefits_cents",
                      "prior_year_lower_earned_income_cents",
                      "prior_year_form_2441_line_6_cents",
                      "prior_year_agi_cents",
                      "mfs_ptc_exception",
                      "mfs_ptc_exception_fourth_year",
                      # Publication 596 Rule 14, the childless-EIC main-home-in-the-U.S.
                      # test — invited on every return, optional (absent reads the engine's own
                      # complete-safe true). Measured on a synthetic single filer, wages $14,000,
                      # no qualifying child: an explicit false zeroes total payments (389.00 -> 0.00).
                      "main_home_in_us_over_half_year",
                      # Form W-2 box 10 through Form 2441 Part III (the artifact: every
                      # one reaches 9, 11, 24, 33 and 34; measured moving 11 and 24).
                      "w2s[].dependent_care_benefits_cents",
                      # W-2 box 12 code W and Form 8889 Part I (Schedule 1 line 8z).
                      "w2s[].box12_w_cents",
                      "persons[].hsa_medicare",
                      "persons[].hsa_hdhp_coverage",
                      "persons[].hsa_hdhp_type",
                      "persons[].hsa_other_coverage",
                      "persons[].hsa_funding_distribution",
                      "persons[].hsa_spouse_contributed",
                      # the separate-return spouse's twelve coverage months (line 6's division).
                      "spouse_hsa_coverage_jan",
                      "spouse_hsa_coverage_feb",
                      "spouse_hsa_coverage_mar",
                      "spouse_hsa_coverage_apr",
                      "spouse_hsa_coverage_may",
                      "spouse_hsa_coverage_jun",
                      "spouse_hsa_coverage_jul",
                      "spouse_hsa_coverage_aug",
                      "spouse_hsa_coverage_sep",
                      "spouse_hsa_coverage_oct",
                      "spouse_hsa_coverage_nov",
                      "spouse_hsa_coverage_dec",
                      "persons[].hsa_marital_status_changed",
                      "persons[].hsa_marital_change_affects_limit",
                      "hsa_excess_in_w2_wages",
                      # the combat pay elections (the artifact: the Form 1040 and Form 2441
                      # Part II elections reach 24/33/34; the Part III election, through the taxable
                      # benefit on line 1e, reaches 9 and 11 too).
                      "combat_pay_election", "cdcc_combat_pay_election",
                      "dependent_care_benefits_combat_pay_election",
                      # the qualified HSA funding distribution (the artifact: both reach every
                      # served block through line 4b and Form 8889 line 10).
                      "r1099s[].qualified_hsa_funding_distribution_cents",
                      "persons[].hsa_prior_funding_distribution_election",
                      # the qualified charitable distribution (the artifact: line 4b reaches
                      # every served block).
                      "r1099s[].qualified_charitable_distribution_cents",
                      "r1099s[].qcd_to_split_interest_entity",
                      "persons[].qcd_prior_deducted_ira_contributions_cents",
                      # the indirect rollover (the artifact: lines 4b and 5b reach every block).
                      "r1099s[].rolled_over_cents",
                      "r1099s[].ira_one_rollover_per_year",
                      "r1099s[].reached_minimum_retirement_age", "r1099s[].public_safety_officer", "r1099s[].pso_premiums_paid_by_plan",
                      "r1099s[].pso_premiums_cents",
                      "r1099s[].date_of_payment", "r1099s[].box1_is_death_benefit_under_contract",
                      "r1099s[].acquired_in_reportable_policy_sale", "r1099s[].acquired_for_valuable_consideration",
                      "r1099s[].transfer_has_carryover_basis", "r1099s[].transfer_to_insured_or_related_party",
                      "r1099s[].death_benefit_basis_cents",
                      # the transfer month (the artifact: line 4b reaches every block).
                      "persons[].hsa_funding_distribution_transfer_month",
                      "persons[].hsa_testing_period_first_ineligible_month",
                      # the twelve coverage months (line 3's chart; the same reach).
                      "persons[].hsa_coverage_jan",
                      "persons[].hsa_coverage_feb",
                      "persons[].hsa_coverage_mar",
                      "persons[].hsa_coverage_apr",
                      "persons[].hsa_coverage_may",
                      "persons[].hsa_coverage_jun",
                      "persons[].hsa_coverage_jul",
                      "persons[].hsa_coverage_aug",
                      "persons[].hsa_coverage_sep",
                      "persons[].hsa_coverage_oct",
                      "persons[].hsa_coverage_nov",
                      "persons[].hsa_coverage_dec",
                      "persons[].hsa_medicare_first_month",
                      # the own-contribution question and its two amounts (Form 8889
                      # line 2; the artifact: the same reach as code W; measured moving 24 and 34).
                      "persons[].made_hsa_contributions",
                      "persons[].hsa_own_contributions_cents",
                      "persons[].hsa_own_contributions_after_year_end_cents",
                      # Form W-2 box 12's four uncollected-tax codes, Schedule 2
                      # line 13 (the artifact: 24, 33, 34; measured moving 24 and 34).
                      # Form 8880 — the eight box 12 deferral codes (line 2; H also
                      # reaches 9 and 11 per the DAG, measured moving neither), code G's plan
                      # answer, the student test, the Roth-and-ABLE follow-up (line 1), the
                      # line-4 distribution answers and the filed-jointly pair (measured on 24
                      # and 34; the artifact: each reaches 24, 33, 34).
                      "w2s[].box12_d_cents",
                      "w2s[].box12_e_cents",
                      "w2s[].box12_g_cents",
                      "w2s[].box12_h_cents",
                      "w2s[].box12_s_cents",
                      "w2s[].box12_aa_cents",
                      "w2s[].box12_bb_cents",
                      "w2s[].box12_ee_cents",
                      "w2s[].box12_g_governmental_plan",
                      "persons[].roth_ira_and_able_contributions_cents",
                      "persons[].received_retirement_distributions_2023_2024",
                      "persons[].retirement_distributions_2023_cents",
                      "persons[].retirement_distributions_2024_cents",
                      "persons[].received_retirement_distributions_after_year_end",
                      "persons[].retirement_distributions_after_year_end_cents",
                      "filed_jointly_2023",
                      "filed_jointly_2024",
                      "w2s[].box12_a_cents",
                      "w2s[].box12_b_cents",
                      "w2s[].box12_m_cents",
                      "w2s[].box12_n_cents",
                      "persons[].self_employed_dependent_care_benefits_cents",
                      "persons[].dependent_care_plan_maximum_cents", "persons[].unable_to_care_for_self",
                      "dependent_care_carryover_cents", "dependent_care_forfeited_cents"
                      ]},
    {"line_id": "34", "fact_path": "/overpayment", "label": "Overpayment", "citation": _c("34"),
     "derived_from": ["/totalPayments", "/totalTax",
                      # Form 1095-A's grid (Form 8962) and the root questions a form reaches.
                      "f1095as[].jan_premium_cents",
                      "f1095as[].jan_slcsp_cents",
                      "f1095as[].jan_aptc_cents",
                      "f1095as[].feb_premium_cents",
                      "f1095as[].feb_slcsp_cents",
                      "f1095as[].feb_aptc_cents",
                      "f1095as[].mar_premium_cents",
                      "f1095as[].mar_slcsp_cents",
                      "f1095as[].mar_aptc_cents",
                      "f1095as[].apr_premium_cents",
                      "f1095as[].apr_slcsp_cents",
                      "f1095as[].apr_aptc_cents",
                      "f1095as[].may_premium_cents",
                      "f1095as[].may_slcsp_cents",
                      "f1095as[].may_aptc_cents",
                      "f1095as[].jun_premium_cents",
                      "f1095as[].jun_slcsp_cents",
                      "f1095as[].jun_aptc_cents",
                      "f1095as[].jul_premium_cents",
                      "f1095as[].jul_slcsp_cents",
                      "f1095as[].jul_aptc_cents",
                      "f1095as[].aug_premium_cents",
                      "f1095as[].aug_slcsp_cents",
                      "f1095as[].aug_aptc_cents",
                      "f1095as[].sep_premium_cents",
                      "f1095as[].sep_slcsp_cents",
                      "f1095as[].sep_aptc_cents",
                      "f1095as[].oct_premium_cents",
                      "f1095as[].oct_slcsp_cents",
                      "f1095as[].oct_aptc_cents",
                      "f1095as[].nov_premium_cents",
                      "f1095as[].nov_slcsp_cents",
                      "f1095as[].nov_aptc_cents",
                      "f1095as[].dec_premium_cents",
                      "f1095as[].dec_slcsp_cents",
                      "f1095as[].dec_aptc_cents",
                      "marketplace_estimated_income_at_least_100_fpl",
                      "below_poverty_line_not_eligible_for_medicaid_due_to_immigration",
                      "dependents_modified_agi_cents",
                      "paid_prior_year_care_expenses_this_year",
                      "prior_year_form_2441_line_3_cents",
                      "prior_year_expenses_paid_this_year_cents",
                      "prior_year_had_two_or_more_qualifying_persons",
                      "prior_year_excluded_or_deducted_benefits_cents",
                      "prior_year_lower_earned_income_cents",
                      "prior_year_form_2441_line_6_cents",
                      "prior_year_agi_cents",
                      "mfs_ptc_exception",
                      "mfs_ptc_exception_fourth_year",
                      # Publication 596 Rule 14, the childless-EIC main-home-in-the-U.S.
                      # test — invited on every return, optional (absent reads the engine's own
                      # complete-safe true). Measured on a synthetic single filer, wages $14,000,
                      # no qualifying child: an explicit false zeroes total payments (389.00 -> 0.00).
                      "main_home_in_us_over_half_year",
                      # Form W-2 box 10 through Form 2441 Part III (the artifact: every
                      # one reaches 9, 11, 24, 33 and 34; measured moving 11 and 24).
                      "w2s[].dependent_care_benefits_cents",
                      # W-2 box 12 code W and Form 8889 Part I (Schedule 1 line 8z).
                      "w2s[].box12_w_cents",
                      "persons[].hsa_medicare",
                      "persons[].hsa_hdhp_coverage",
                      "persons[].hsa_hdhp_type",
                      "persons[].hsa_other_coverage",
                      "persons[].hsa_funding_distribution",
                      "persons[].hsa_spouse_contributed",
                      # the separate-return spouse's twelve coverage months (line 6's division).
                      "spouse_hsa_coverage_jan",
                      "spouse_hsa_coverage_feb",
                      "spouse_hsa_coverage_mar",
                      "spouse_hsa_coverage_apr",
                      "spouse_hsa_coverage_may",
                      "spouse_hsa_coverage_jun",
                      "spouse_hsa_coverage_jul",
                      "spouse_hsa_coverage_aug",
                      "spouse_hsa_coverage_sep",
                      "spouse_hsa_coverage_oct",
                      "spouse_hsa_coverage_nov",
                      "spouse_hsa_coverage_dec",
                      "persons[].hsa_marital_status_changed",
                      "persons[].hsa_marital_change_affects_limit",
                      "hsa_excess_in_w2_wages",
                      # the combat pay elections (the artifact: the Form 1040 and Form 2441
                      # Part II elections reach 24/33/34; the Part III election, through the taxable
                      # benefit on line 1e, reaches 9 and 11 too).
                      "combat_pay_election", "cdcc_combat_pay_election",
                      "dependent_care_benefits_combat_pay_election",
                      # the qualified HSA funding distribution (the artifact: both reach every
                      # served block through line 4b and Form 8889 line 10).
                      "r1099s[].qualified_hsa_funding_distribution_cents",
                      "persons[].hsa_prior_funding_distribution_election",
                      # the qualified charitable distribution (the artifact: line 4b reaches
                      # every served block).
                      "r1099s[].qualified_charitable_distribution_cents",
                      "r1099s[].qcd_to_split_interest_entity",
                      "persons[].qcd_prior_deducted_ira_contributions_cents",
                      # the indirect rollover (the artifact: lines 4b and 5b reach every block).
                      "r1099s[].rolled_over_cents",
                      "r1099s[].ira_one_rollover_per_year",
                      "r1099s[].reached_minimum_retirement_age", "r1099s[].public_safety_officer", "r1099s[].pso_premiums_paid_by_plan",
                      "r1099s[].pso_premiums_cents",
                      "r1099s[].date_of_payment", "r1099s[].box1_is_death_benefit_under_contract",
                      "r1099s[].acquired_in_reportable_policy_sale", "r1099s[].acquired_for_valuable_consideration",
                      "r1099s[].transfer_has_carryover_basis", "r1099s[].transfer_to_insured_or_related_party",
                      "r1099s[].death_benefit_basis_cents",
                      # the transfer month (the artifact: line 4b reaches every block).
                      "persons[].hsa_funding_distribution_transfer_month",
                      "persons[].hsa_testing_period_first_ineligible_month",
                      # the twelve coverage months (line 3's chart; the same reach).
                      "persons[].hsa_coverage_jan",
                      "persons[].hsa_coverage_feb",
                      "persons[].hsa_coverage_mar",
                      "persons[].hsa_coverage_apr",
                      "persons[].hsa_coverage_may",
                      "persons[].hsa_coverage_jun",
                      "persons[].hsa_coverage_jul",
                      "persons[].hsa_coverage_aug",
                      "persons[].hsa_coverage_sep",
                      "persons[].hsa_coverage_oct",
                      "persons[].hsa_coverage_nov",
                      "persons[].hsa_coverage_dec",
                      "persons[].hsa_medicare_first_month",
                      # the own-contribution question and its two amounts (Form 8889
                      # line 2; the artifact: the same reach as code W; measured moving 24 and 34).
                      "persons[].made_hsa_contributions",
                      "persons[].hsa_own_contributions_cents",
                      "persons[].hsa_own_contributions_after_year_end_cents",
                      "persons[].hsa_december_31_value_cents",
                      "persons[].hsa_prior_year_excess_cents",
                      # Form W-2 box 12's four uncollected-tax codes, Schedule 2
                      # line 13 (the artifact: 24, 33, 34; measured moving 24 and 34).
                      # Form 8880 — the eight box 12 deferral codes (line 2; H also
                      # reaches 9 and 11 per the DAG, measured moving neither), code G's plan
                      # answer, the student test, the Roth-and-ABLE follow-up (line 1), the
                      # line-4 distribution answers and the filed-jointly pair (measured on 24
                      # and 34; the artifact: each reaches 24, 33, 34).
                      "w2s[].box12_d_cents",
                      "w2s[].box12_e_cents",
                      "w2s[].box12_g_cents",
                      "w2s[].box12_h_cents",
                      "w2s[].box12_s_cents",
                      "w2s[].box12_aa_cents",
                      "w2s[].box12_bb_cents",
                      "w2s[].box12_ee_cents",
                      "w2s[].box12_g_governmental_plan",
                      "persons[].roth_ira_and_able_contributions_cents",
                      "persons[].received_retirement_distributions_2023_2024",
                      "persons[].retirement_distributions_2023_cents",
                      "persons[].retirement_distributions_2024_cents",
                      "persons[].received_retirement_distributions_after_year_end",
                      "persons[].retirement_distributions_after_year_end_cents",
                      "filed_jointly_2023",
                      "filed_jointly_2024",
                      "w2s[].box12_a_cents",
                      "w2s[].box12_b_cents",
                      "w2s[].box12_m_cents",
                      "w2s[].box12_n_cents",
                      "persons[].self_employed_dependent_care_benefits_cents",
                      "persons[].dependent_care_plan_maximum_cents", "persons[].unable_to_care_for_self",
                      "dependent_care_carryover_cents", "dependent_care_forfeited_cents"
                      ]},
]
