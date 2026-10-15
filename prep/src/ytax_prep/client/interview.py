# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""What the documents could not answer — asked last, and only once.

The interview used to come FIRST: fill a template, then drop your files in. That order makes a
person type things the paperwork already states, and asks every question whether or not it matters
for their return.

This inverts it. Documents are read first; what remains is the **residue** — the short list of facts
no W-2 or 1099 states, each carrying the Form 1040 lines it would move. A question that cannot say
why it is being asked is a question a preparer learns to click through.

WHAT DOCUMENTS GENUINELY CANNOT SAY, and why each is unavoidable:

  * **filing status** — a choice about a household, not a fact printed on anything;
  * **dates of birth** — a W-2 states wages, not age, and age decides the additional standard
    deduction (the #73 chain);
  * **who each person is to the return** — primary, spouse, dependent;
  * **TIN type** — whether an SSN is valid for employment changes credit eligibility, and the
    number's digits (which we never take) would not tell you anyway.

Derived from `service/gaps.py`, deliberately: the questions asked here and the gaps the service
reports are the same list, so a preparer cannot answer everything the interview asks and still be
told something is missing. Adding a required field to the schema adds a question here for free.

NO TAX ADVICE. Every prompt states what a field IS and which line it reaches. None recommends a
value, and none infers one — World #1 applies to a question just as it applies to an answer.
"""
from __future__ import annotations

from ..service.gaps import consumed_by, gaps_for
from ..service.lines import F1040

# The exact values the fact schema accepts for each CHOICE field, in the schema's order, each with
# the plain words a person would use for it. The CODE is the answer; the words say what it means.

# the filing-status prompt used to offer "married filing jointly" — words the schema refuses
# (it accepts `mfj`), so a person who answered exactly as asked was refused SCHEMA_INVALID.
# `tin_type` and the K-1's `source` had the same drift. The prompt and the enum are one source now:
# declared here rather than read from schema/ (the container ships src/ only — the same reason
# `mapper` declares its sets), and LOCKED to the schema files by `tests/test_interview.py` in both
# directions, so a value the schema refuses cannot be offered and one it accepts cannot be left out.
# Since 2026-08-20 this is the standing rule rather than a fix: the schema/dictionary
# says what to ask; the interview does not carry its own vocabulary.
CHOICES = {
    # the dictionary's own jurisdiction list (/scopedStateOptions), in its order.
    "residence_state": (
        ('moreThanOne', 'more than one of these'),
        ('al', 'Alabama'),
        ('ak', 'Alaska'),
        ('az', 'Arizona'),
        ('ar', 'Arkansas'),
        ('ca', 'California'),
        ('co', 'Colorado'),
        ('ct', 'Connecticut'),
        ('de', 'Delaware'),
        ('dc', 'the District of Columbia'),
        ('fl', 'Florida'),
        ('ga', 'Georgia'),
        ('hi', 'Hawaii'),
        ('id', 'Idaho'),
        ('il', 'Illinois'),
        ('in', 'Indiana'),
        ('ia', 'Iowa'),
        ('ks', 'Kansas'),
        ('ky', 'Kentucky'),
        ('la', 'Louisiana'),
        ('me', 'Maine'),
        ('md', 'Maryland'),
        ('ma', 'Massachusetts'),
        ('mi', 'Michigan'),
        ('mn', 'Minnesota'),
        ('ms', 'Mississippi'),
        ('mo', 'Missouri'),
        ('mt', 'Montana'),
        ('ne', 'Nebraska'),
        ('nv', 'Nevada'),
        ('nh', 'New Hampshire'),
        ('nj', 'New Jersey'),
        ('nm', 'New Mexico'),
        ('ny', 'New York'),
        ('nc', 'North Carolina'),
        ('nd', 'North Dakota'),
        ('oh', 'Ohio'),
        ('ok', 'Oklahoma'),
        ('or', 'Oregon'),
        ('pa', 'Pennsylvania'),
        ('ri', 'Rhode Island'),
        ('sc', 'South Carolina'),
        ('sd', 'South Dakota'),
        ('tn', 'Tennessee'),
        ('tx', 'Texas'),
        ('ut', 'Utah'),
        ('vt', 'Vermont'),
        ('va', 'Virginia'),
        ('wa', 'Washington'),
        ('wv', 'West Virginia'),
        ('wi', 'Wisconsin'),
        ('wy', 'Wyoming'),
        ('noneOfThese', 'none of these'),
    ),
    "spouse_death_year": (
        ("last_year", "the year before the tax year"),
        ("two_years_ago", "two years before the tax year"),
    ),
    "filing_status": (
        ("single", "single"),
        ("mfj", "married filing jointly"),
        ("mfs", "married filing separately"),
        ("hoh", "head of household"),
        ("qss", "qualifying surviving spouse"),
    ),
    "role": (
        ("primary", "the primary filer"),
        ("spouse", "the spouse"),
        ("dependent", "a dependent"),
    ),
    "tin_type": (
        ("ssn_valid_for_employment", "an SSN valid for employment"),
        ("ssn_other", "an SSN not valid for employment"),
        ("ssn_dhs_authorization", "an SSN valid for work only with DHS authorization, still in effect"),
        ("ssn_dhs_authorization_expired", "an SSN valid for work only with DHS authorization, now expired"),
        ("itin", "an ITIN"),
        ("atin", "an ATIN"),
        ("none", "no taxpayer ID"),
    ),
    # which benefit statement — the dictionary's own option set, in its order.
    "form_type": (
        ("ssa_1099", "Form SSA-1099, Social Security Benefit Statement"),
        ("rrb_1099", "Form RRB-1099, Railroad Retirement tier 1 (Social Security equivalent)"),
    ),
    # the 1099-SA box 3 codes as printed, and the 20%-tax exception's grounds.
    "hsa_distribution_code": (
        ("1", "1 — Normal distribution"),
        ("2", "2 — Excess contributions"),
        ("3", "3 — Disability"),
        ("4", "4 — Death (other than code 6)"),
        ("5", "5 — Prohibited transaction"),
        ("6", "6 — Death distribution after the year of death"),
    ),
    "hsa_exception_reason": (
        ("age65", "distributed after turning 65"),
        ("disability", "distributed after becoming disabled"),
        ("death_of_beneficiary", "distributed after the account beneficiary died"),
        ("none", "no exception applies"),
    ),
    # Form 1099-B box 2, its three checkboxes in the form's words. Ordinary is offered
    # because the form prints it; the service refuses it by name.
    "term": (
        ("short", "Short-term gain or loss"),
        ("long", "Long-term gain or loss"),
        ("ordinary", "Ordinary"),
    ),
    # Form 8889 Part I's four choices, in the form's words.
    "hsa_medicare": (
        ("all_year", "enrolled in Medicare all year"),
        ("part_of_year", "enrolled for part of the year"),
        ("none", "not enrolled in Medicare"),
    ),
    # the month Medicare enrollment began.
    "hsa_medicare_first_month": (
        ("jan", "January"),
        ("feb", "February"),
        ("mar", "March"),
        ("apr", "April"),
        ("may", "May"),
        ("jun", "June"),
        ("jul", "July"),
        ("aug", "August"),
        ("sep", "September"),
        ("oct", "October"),
        ("nov", "November"),
        ("dec", "December"),
    ),
    "hsa_hdhp_coverage": (
        ("all_year", "covered by a high deductible health plan all year"),
        ("part_of_year", "covered for part of the year"),
        ("none", "not covered by a high deductible health plan"),
    ),
    "hsa_hdhp_type": (
        ("self_only", "self-only coverage"),
        ("family", "family coverage"),
        ("both", "both self-only and family coverage during the year"),
    ),
    # the month of the IRA-to-HSA transfer.
    "hsa_funding_distribution_transfer_month": (
        ("jan", "January"), ("feb", "February"), ("mar", "March"), ("apr", "April"),
        ("may", "May"), ("jun", "June"), ("jul", "July"), ("aug", "August"),
        ("sep", "September"), ("oct", "October"), ("nov", "November"), ("dec", "December"),
    ),
    # the separate-return spouse's twelve coverage months.
    "spouse_hsa_coverage_jan": (
        ("none", "no high deductible health plan coverage on the first day of January"),
        ("self_only", "self-only coverage on the first day of January"),
        ("family", "family coverage on the first day of January"),
    ),
    "spouse_hsa_coverage_feb": (
        ("none", "no high deductible health plan coverage on the first day of February"),
        ("self_only", "self-only coverage on the first day of February"),
        ("family", "family coverage on the first day of February"),
    ),
    "spouse_hsa_coverage_mar": (
        ("none", "no high deductible health plan coverage on the first day of March"),
        ("self_only", "self-only coverage on the first day of March"),
        ("family", "family coverage on the first day of March"),
    ),
    "spouse_hsa_coverage_apr": (
        ("none", "no high deductible health plan coverage on the first day of April"),
        ("self_only", "self-only coverage on the first day of April"),
        ("family", "family coverage on the first day of April"),
    ),
    "spouse_hsa_coverage_may": (
        ("none", "no high deductible health plan coverage on the first day of May"),
        ("self_only", "self-only coverage on the first day of May"),
        ("family", "family coverage on the first day of May"),
    ),
    "spouse_hsa_coverage_jun": (
        ("none", "no high deductible health plan coverage on the first day of June"),
        ("self_only", "self-only coverage on the first day of June"),
        ("family", "family coverage on the first day of June"),
    ),
    "spouse_hsa_coverage_jul": (
        ("none", "no high deductible health plan coverage on the first day of July"),
        ("self_only", "self-only coverage on the first day of July"),
        ("family", "family coverage on the first day of July"),
    ),
    "spouse_hsa_coverage_aug": (
        ("none", "no high deductible health plan coverage on the first day of August"),
        ("self_only", "self-only coverage on the first day of August"),
        ("family", "family coverage on the first day of August"),
    ),
    "spouse_hsa_coverage_sep": (
        ("none", "no high deductible health plan coverage on the first day of September"),
        ("self_only", "self-only coverage on the first day of September"),
        ("family", "family coverage on the first day of September"),
    ),
    "spouse_hsa_coverage_oct": (
        ("none", "no high deductible health plan coverage on the first day of October"),
        ("self_only", "self-only coverage on the first day of October"),
        ("family", "family coverage on the first day of October"),
    ),
    "spouse_hsa_coverage_nov": (
        ("none", "no high deductible health plan coverage on the first day of November"),
        ("self_only", "self-only coverage on the first day of November"),
        ("family", "family coverage on the first day of November"),
    ),
    "spouse_hsa_coverage_dec": (
        ("none", "no high deductible health plan coverage on the first day of December"),
        ("self_only", "self-only coverage on the first day of December"),
        ("family", "family coverage on the first day of December"),
    ),
    # the twelve coverage months.
    "hsa_coverage_jan": (
        ("none", "no high deductible health plan coverage on the first day of January"),
        ("self_only", "self-only coverage on the first day of January"),
        ("family", "family coverage on the first day of January"),
    ),
    "hsa_coverage_feb": (
        ("none", "no high deductible health plan coverage on the first day of February"),
        ("self_only", "self-only coverage on the first day of February"),
        ("family", "family coverage on the first day of February"),
    ),
    "hsa_coverage_mar": (
        ("none", "no high deductible health plan coverage on the first day of March"),
        ("self_only", "self-only coverage on the first day of March"),
        ("family", "family coverage on the first day of March"),
    ),
    "hsa_coverage_apr": (
        ("none", "no high deductible health plan coverage on the first day of April"),
        ("self_only", "self-only coverage on the first day of April"),
        ("family", "family coverage on the first day of April"),
    ),
    "hsa_coverage_may": (
        ("none", "no high deductible health plan coverage on the first day of May"),
        ("self_only", "self-only coverage on the first day of May"),
        ("family", "family coverage on the first day of May"),
    ),
    "hsa_coverage_jun": (
        ("none", "no high deductible health plan coverage on the first day of June"),
        ("self_only", "self-only coverage on the first day of June"),
        ("family", "family coverage on the first day of June"),
    ),
    "hsa_coverage_jul": (
        ("none", "no high deductible health plan coverage on the first day of July"),
        ("self_only", "self-only coverage on the first day of July"),
        ("family", "family coverage on the first day of July"),
    ),
    "hsa_coverage_aug": (
        ("none", "no high deductible health plan coverage on the first day of August"),
        ("self_only", "self-only coverage on the first day of August"),
        ("family", "family coverage on the first day of August"),
    ),
    "hsa_coverage_sep": (
        ("none", "no high deductible health plan coverage on the first day of September"),
        ("self_only", "self-only coverage on the first day of September"),
        ("family", "family coverage on the first day of September"),
    ),
    "hsa_coverage_oct": (
        ("none", "no high deductible health plan coverage on the first day of October"),
        ("self_only", "self-only coverage on the first day of October"),
        ("family", "family coverage on the first day of October"),
    ),
    "hsa_coverage_nov": (
        ("none", "no high deductible health plan coverage on the first day of November"),
        ("self_only", "self-only coverage on the first day of November"),
        ("family", "family coverage on the first day of November"),
    ),
    "hsa_coverage_dec": (
        ("none", "no high deductible health plan coverage on the first day of December"),
        ("self_only", "self-only coverage on the first day of December"),
        ("family", "family coverage on the first day of December"),
    ),
    # the testing-period month — none, then every month of 2025 and 2026.
    "hsa_testing_period_first_ineligible_month": (
        ("none", "eligible in every month of the testing period"),
        ("jan2025", "January 2025"),
        ("feb2025", "February 2025"),
        ("mar2025", "March 2025"),
        ("apr2025", "April 2025"),
        ("may2025", "May 2025"),
        ("jun2025", "June 2025"),
        ("jul2025", "July 2025"),
        ("aug2025", "August 2025"),
        ("sep2025", "September 2025"),
        ("oct2025", "October 2025"),
        ("nov2025", "November 2025"),
        ("dec2025", "December 2025"),
        ("jan2026", "January 2026"),
        ("feb2026", "February 2026"),
        ("mar2026", "March 2026"),
        ("apr2026", "April 2026"),
        ("may2026", "May 2026"),
        ("jun2026", "June 2026"),
        ("jul2026", "July 2026"),
        ("aug2026", "August 2026"),
        ("sep2026", "September 2026"),
        ("oct2026", "October 2026"),
        ("nov2026", "November 2026"),
        ("dec2026", "December 2026"),
    ),
    "hsa_other_coverage": (
        ("whole_year", "other health coverage the whole year"),
        ("part_of_year", "other health coverage part of the year"),
        ("none", "no other health coverage"),
    ),
    # the combat pay elections — the same four choices on each of the three lines.
    **{field: (
        ("own", "count the primary filer's combat pay"),
        ("spouse", "count the spouse's combat pay"),
        ("both", "count both filers' combat pay"),
        ("none", "count no combat pay"),
    ) for field in ("combat_pay_election", "cdcc_combat_pay_election",
                    "dependent_care_benefits_combat_pay_election")},
    # Form 2441 line 1 column (c)'s own vocabulary — an EIN, "Tax-Exempt", or an SSN.
    "provider_type": (
        ("organization", "an organization — column (c) carries its EIN"),
        ("tax_exempt_organization", "a tax-exempt organization — column (c) reads \"Tax-Exempt\""),
        ("individual", "an individual — column (c) carries their SSN"),
    ),
    "source": (
        ("partnership", "a partnership"),
        ("s_corp", "an S corporation"),
        ("estate_trust", "an estate or trust"),
    ),
    # The pinned dictionary's own relationship vocabulary (/relationshipOptions), in its order,
    # spelled in the schema's snake_case (the enum the free-text field waited on exists at
    # the pin, so the drift closes the standing way: the dictionary decides, the schema declares,
    # this table offers). Dependent rows are refused at compute today, and the dependent
    # qualifiers are not ASKED while that holds (the dependent gate) — this entry is the dropdown's and
    # the reader's vocabulary, so a typed word is accepted or refused by name, never passed on to
    # fail later.
    # the state or territory a dependent lived in, the dictionary's own list
    # (/childResidenceJurisdictionOptions) in its order: the residence_state codes without
    # moreThanOne or noneOfThese, then five territories and outside the United States.
    "child_residence_state": (
        ('al', 'Alabama'),
        ('ak', 'Alaska'),
        ('az', 'Arizona'),
        ('ar', 'Arkansas'),
        ('ca', 'California'),
        ('co', 'Colorado'),
        ('ct', 'Connecticut'),
        ('de', 'Delaware'),
        ('dc', 'the District of Columbia'),
        ('fl', 'Florida'),
        ('ga', 'Georgia'),
        ('hi', 'Hawaii'),
        ('id', 'Idaho'),
        ('il', 'Illinois'),
        ('in', 'Indiana'),
        ('ia', 'Iowa'),
        ('ks', 'Kansas'),
        ('ky', 'Kentucky'),
        ('la', 'Louisiana'),
        ('me', 'Maine'),
        ('md', 'Maryland'),
        ('ma', 'Massachusetts'),
        ('mi', 'Michigan'),
        ('mn', 'Minnesota'),
        ('ms', 'Mississippi'),
        ('mo', 'Missouri'),
        ('mt', 'Montana'),
        ('ne', 'Nebraska'),
        ('nv', 'Nevada'),
        ('nh', 'New Hampshire'),
        ('nj', 'New Jersey'),
        ('nm', 'New Mexico'),
        ('ny', 'New York'),
        ('nc', 'North Carolina'),
        ('nd', 'North Dakota'),
        ('oh', 'Ohio'),
        ('ok', 'Oklahoma'),
        ('or', 'Oregon'),
        ('pa', 'Pennsylvania'),
        ('ri', 'Rhode Island'),
        ('sc', 'South Carolina'),
        ('sd', 'South Dakota'),
        ('tn', 'Tennessee'),
        ('tx', 'Texas'),
        ('ut', 'Utah'),
        ('vt', 'Vermont'),
        ('va', 'Virginia'),
        ('wa', 'Washington'),
        ('wv', 'West Virginia'),
        ('wi', 'Wisconsin'),
        ('wy', 'Wyoming'),
        ('pr', 'Puerto Rico'),
        ('gu', 'Guam'),
        ('vi', 'the U.S. Virgin Islands'),
        ('as', 'American Samoa'),
        ('mp', 'the Northern Mariana Islands'),
        ('outsideUnitedStates', 'outside the United States'),
    ),
    # the benefit-split gate's two enums, from the pinned dictionary's own option lists
    # (/parentalSituationOptions, /writtenDeclarationOptions) in their order, spelled in the
    # schema's snake_case. The dropdown offers these codes and nothing else — the service
    # refuses any other word by name rather than passing it on to fail later.
    "parents_situation": (
        ("divorced_or_separated", "divorced or legally separated"),
        ("lived_apart_last_six_months", "living apart for the last six months of the year"),
        ("other", "none of these"),
    ),
    "written_declaration": (
        ("i_did", "I signed one"),
        ("they_did", "the other parent signed one"),
        ("nobody_did", "neither of us signed one"),
    ),
    # how long the spouses lived together, the dictionary's three literals
    # (/spouseLivedTogetherMonthsOptions) in the schema's snake_case.
    "months_lived_with_spouse": (
        ("apart_all_year", "apart all year"),
        ("more_than_six_months", "together more than six months"),
        ("six_months_or_less", "together six months or less"),
    ),
    # the nights answer, the dictionary's own three literals (/moreLessEqualOptions).
    "nights_with_filer_vs_other_parent": (
        ("more", "more nights with me"),
        ("less", "fewer nights with me"),
        ("equal", "the same number of nights with each parent"),
    ),
    "relationship": (
        ("biological_child", "their biological child"),
        ("adopted_child", "their adopted child"),
        ("step_child", "their stepchild"),
        ("foster_child", "their foster child"),
        ("grand_child_or_other_descendant_of_child", "a grandchild or other descendant of their child"),
        ("child_in_law", "their son- or daughter-in-law"),
        ("sibling", "their sibling"),
        ("child_of_sibling", "a child of their sibling"),
        ("half_sibling", "their half sibling"),
        ("child_of_half_sibling", "a child of their half sibling"),
        ("step_sibling", "their stepsibling"),
        ("child_of_step_sibling", "a child of their stepsibling"),
        ("other_descendant_of_sibling", "another descendant of their sibling"),
        ("other_descendant_of_half_sibling", "another descendant of their half sibling"),
        ("other_descendant_of_step_sibling", "another descendant of their stepsibling"),
        ("siblings_spouse", "their sibling's spouse"),
        ("sibling_in_law", "their spouse's sibling"),
        ("parent", "their parent"),
        ("foster_parent", "their foster parent"),
        ("sibling_of_parent", "a sibling of their parent"),
        ("grand_parent", "their grandparent"),
        ("other_ancestor_of_parent", "another ancestor of their parent"),
        ("step_parent", "their stepparent"),
        ("step_grand_parent", "a parent of their stepparent, or their grandparent's spouse"),
        ("step_sibling_of_parent", "a stepsibling of their parent"),
        ("parent_in_law", "their parent-in-law"),
        ("none_of_the_above", "none of the above"),
    ),
}


def _offer(field: str) -> str:
    """The choices in plain words, in order — rendered from CHOICES so the prompt cannot name a
    value on its own. The code is a dropdown's value and an accepted answer, never a word in the
    sentence (`intake.answers.parse_answer` accepts the words as well as the code, which is
    what the old words-only offer lacked)."""
    words = [w for _code, w in CHOICES[field]]
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + ", or " + words[-1]


def choice_words(field: str) -> dict | None:
    """{code: plain words} for a choice field, in order — what a dropdown shows beside each value —
    or None for a free field."""
    return {code: words for code, words in CHOICES[field]} if field in CHOICES else None


def choices_for(field: str) -> list | None:
    """The accepted codes for a choice field, in order — for a dropdown — or None for a free field."""
    return [code for code, _words in CHOICES[field]] if field in CHOICES else None


# Plain-language prompts, keyed by the field a gap names. A prompt is not a definition of the tax
# concept — it is the smallest true statement that lets someone answer, plus what it moves. A
# choice field's prompt is BUILT from CHOICES above, never typed.
PROMPTS = {
    "persons": "Who is on this return? Give the primary filer, a spouse if filing jointly, and "
               "any dependents.",
    "filing_status": f"How is this return filed? Answer with one of: {_offer('filing_status')}.",
    "role": f"Who is this person to the return? Answer with one of: {_offer('role')}.",
    "birth_year": "What year was this person born?",
    "birth_month": "Which month were they born in? (The day is never asked and never sent.)",
    "tin_type": f"What TYPE of taxpayer ID do they have — never the number itself? Answer with one "
                f"of: {_offer('tin_type')}.",
    "person": "Which person on this return does this document belong to?",
    "wages_cents": "Box 1 of this W-2 — wages, tips and other compensation.",
    "withholding_cents": "Box 2 — federal income tax withheld. Enter 0 if the box is empty.",
    # box 10, the one W-2 box Form 2441 Part III reads.
    "dependent_care_benefits_cents": ("Box 10 of this W-2 — dependent care benefits. Enter 0 if "
                                      "the box is empty; used for Form 2441 Part III."),
    # box 12, one ask per code in the form's own words.
    "box12_a_cents": ("Box 12 of this W-2 — the amount printed beside code A (uncollected social security or RRTA tax on tips). Leave it blank if no code A is printed"
                     "; used for Schedule 2 line 13."),
    "box12_b_cents": ("Box 12 of this W-2 — the amount printed beside code B (uncollected Medicare tax on tips). Leave it blank if no code B is printed"
                     "; used for Schedule 2 line 13."),
    "box12_c_cents": ("Box 12 of this W-2 — the amount printed beside code C (taxable cost of group-term life insurance over $50,000). Leave it blank if no code C is printed"
                     "; it moves no line this service serves."),
    "box12_d_cents": ("Box 12 of this W-2 — the amount printed beside code D (elective deferrals under a section 401(k) cash or deferred arrangement plan). Leave it blank if no code D is printed"
                     ". An amount here reaches Form 8880, which this service has not built; the return is refused rather than computed as if the box were blank."),
    "box12_e_cents": ("Box 12 of this W-2 — the amount printed beside code E (elective deferrals under a section 403(b) salary reduction agreement). Leave it blank if no code E is printed"
                     ". An amount here reaches Form 8880, which this service has not built; the return is refused rather than computed as if the box were blank."),
    "box12_f_cents": ("Box 12 of this W-2 — the amount printed beside code F (elective deferrals under a section 408(k)(6) salary reduction SEP). Leave it blank if no code F is printed"
                     ". An amount here is one the engine does not compute a return with; the return is refused, not computed without it."),
    "box12_g_cents": ("Box 12 of this W-2 — the amount printed beside code G (elective deferrals and employer contributions to a section 457(b) deferred compensation plan). Leave it blank if no code G is printed"
                     ". An amount here reaches Form 8880, which this service has not built; the return is refused rather than computed as if the box were blank."),
    "box12_g_governmental_plan": ("Box 12 code G of this W-2 — is the section 457(b) plan a "
                                  "governmental plan? Used for Form 8880, "
                                  "line 2 (only a governmental plan's deferrals count)."),
    "box12_h_cents": ("Box 12 of this W-2 — the amount printed beside code H (elective deferrals to a section 501(c)(18)(D) tax-exempt organization plan). Leave it blank if no code H is printed"
                     ". An amount here reaches Form 8880, which this service has not built; the return is refused rather than computed as if the box were blank."),
    "box12_j_cents": ("Box 12 of this W-2 — the amount printed beside code J (nontaxable sick pay). Leave it blank if no code J is printed"
                     ". An amount here is one the engine does not compute a return with; the return is refused, not computed without it."),
    "box12_k_cents": ("Box 12 of this W-2 — the amount printed beside code K (20% excise tax on excess golden parachute payments). Leave it blank if no code K is printed"
                     ". An amount here is one the engine does not compute a return with; the return is refused, not computed without it."),
    "box12_l_cents": ("Box 12 of this W-2 — the amount printed beside code L (substantiated employee business expense reimbursements). Leave it blank if no code L is printed"
                     ". An amount here is one the engine does not compute a return with; the return is refused, not computed without it."),
    "box12_m_cents": ("Box 12 of this W-2 — the amount printed beside code M (uncollected social security or RRTA tax on taxable cost of group-term life insurance over $50,000). Leave it blank if no code M is printed"
                     "; used for Schedule 2 line 13."),
    "box12_n_cents": ("Box 12 of this W-2 — the amount printed beside code N (uncollected Medicare tax on taxable cost of group-term life insurance over $50,000). Leave it blank if no code N is printed"
                     "; used for Schedule 2 line 13."),
    "box12_p_cents": ("Box 12 of this W-2 — the amount printed beside code P (excludable moving expense reimbursements paid directly to a member of the U.S. Armed Forces). Leave it blank if no code P is printed"
                     ". An amount here is one the engine does not compute a return with; the return is refused, not computed without it."),
    "box12_q_cents": ("Box 12 of this W-2 — the amount printed beside code Q (nontaxable combat pay). Leave it blank if no code Q is printed"
                     ". An amount here reaches the earned income election (Form 1040 line 1i), which this service has not built; the return is refused rather than computed as if the box were blank."),
    "box12_r_cents": ("Box 12 of this W-2 — the amount printed beside code R (employer contributions to an Archer MSA). Leave it blank if no code R is printed"
                     ". An amount here is one the engine does not compute a return with; the return is refused, not computed without it."),
    "box12_s_cents": ("Box 12 of this W-2 — the amount printed beside code S (employee salary reduction contributions under a section 408(p) SIMPLE plan). Leave it blank if no code S is printed"
                     ". An amount here reaches Form 8880, which this service has not built; the return is refused rather than computed as if the box were blank."),
    "box12_t_cents": ("Box 12 of this W-2 — the amount printed beside code T (adoption benefits). Leave it blank if no code T is printed"
                     ". An amount here is one the engine does not compute a return with; the return is refused, not computed without it."),
    "box12_v_cents": ("Box 12 of this W-2 — the amount printed beside code V (income from exercise of nonstatutory stock option(s)). Leave it blank if no code V is printed"
                     "; it moves no line this service serves."),
    "box12_w_cents": ("Box 12 of this W-2 — the amount printed beside code W (employer contributions (including employee contributions through a cafeteria plan) to an employee's health savings account (HSA)). Leave it blank if no code W is printed"
                     ". An amount here reaches Form 8889, which this service has not built; the return is refused rather than computed as if the box were blank."),
    "box12_y_cents": ("Box 12 of this W-2 — the amount printed beside code Y (deferrals under a section 409A nonqualified deferred compensation plan). Leave it blank if no code Y is printed"
                     "; it moves no line this service serves."),
    "box12_z_cents": ("Box 12 of this W-2 — the amount printed beside code Z (income under a nonqualified deferred compensation plan that fails to satisfy section 409A). Leave it blank if no code Z is printed"
                     ". An amount here is one the engine does not compute a return with; the return is refused, not computed without it."),
    "box12_aa_cents": ("Box 12 of this W-2 — the amount printed beside code AA (designated Roth contributions under a section 401(k) plan). Leave it blank if no code AA is printed"
                      ". An amount here reaches Form 8880, which this service has not built; the return is refused rather than computed as if the box were blank."),
    "box12_bb_cents": ("Box 12 of this W-2 — the amount printed beside code BB (designated Roth contributions under a section 403(b) plan). Leave it blank if no code BB is printed"
                      ". An amount here reaches Form 8880, which this service has not built; the return is refused rather than computed as if the box were blank."),
    "box12_dd_cents": ("Box 12 of this W-2 — the amount printed beside code DD (cost of employer-sponsored health coverage). Leave it blank if no code DD is printed"
                      "; it moves no line this service serves."),
    "box12_ee_cents": ("Box 12 of this W-2 — the amount printed beside code EE (designated Roth contributions under a governmental section 457(b) plan). Leave it blank if no code EE is printed"
                      ". An amount here reaches Form 8880, which this service has not built; the return is refused rather than computed as if the box were blank."),
    "box12_ff_cents": ("Box 12 of this W-2 — the amount printed beside code FF (permitted benefits under a qualified small employer health reimbursement arrangement). Leave it blank if no code FF is printed"
                      "; it moves no line this service serves."),
    "box12_gg_cents": ("Box 12 of this W-2 — the amount printed beside code GG (income from qualified equity grants under section 83(i)). Leave it blank if no code GG is printed"
                      "; it moves no line this service serves."),
    "box12_hh_cents": ("Box 12 of this W-2 — the amount printed beside code HH (aggregate deferrals under section 83(i) elections as of the close of the calendar year). Leave it blank if no code HH is printed"
                      "; it moves no line this service serves."),
    "box12_ii_cents": ("Box 12 of this W-2 — the amount printed beside code II (medicaid waiver payments excluded from gross income under Notice 2014-7). Leave it blank if no code II is printed"
                      ". An amount here is one the engine does not compute a return with; the return is refused, not computed without it."),
    # box 13's three checkboxes, one ask each, in the form's words.
    "statutory_employee": "Box 13 of this W-2 — is “Statutory employee” checked?",
    "retirement_plan": "Box 13 of this W-2 — is “Retirement plan” checked?",
    "third_party_sick_pay": "Box 13 of this W-2 — is “Third-party sick pay” checked?",
    # box 14's Railroad Retirement question, the dictionary's own reading of the box.
    "has_rrta_codes": ("Box 14 of this W-2 — does it list Railroad Retirement Tax Act (RRTA) "
                       "codes (RRTA compensation, Tier 1 or Tier 2 tax)?"),
    # Form 1099-B: box 2, asked where box 1b or 1c has no date.
    "term": (f"Which box 2 checkbox is marked on this Form 1099-B? Answer with one of: "
             f"{_offer('term')} — used for Form 1040, line 16."),
    # Form 1099-OID: the one thing the form does not print, and its one checkbox.
    "box2_is_tax_exempt": ("Box 2 of this Form 1099-OID — is that interest tax-exempt? "
                           "Used for Form 1040, lines 2a and 2b."),
    "fatca_filing_requirement": "Is “FATCA filing requirement” checked on this Form 1099-OID?",
    "distribution_code": "The distribution code printed in box 7 of this 1099-R.",
    # the benefit statement's boxes, named by form in GROUP_PROMPTS below.
    "net_benefits_cents": "Net benefits for the year — box 5 of the SSA-1099 or RRB-1099.",
    # Form 1099-G box 1, and the Schedule 1 line 7 repayment — the filer's own figure,
    # printed on no box.
    "unemployment_compensation_cents": "Unemployment compensation — box 1 of this 1099-G.",
    # Form 1099-MISC box 3, and the engine's own per-form Alaska question.
    "other_income_cents": "Other income — box 3 of this 1099-MISC.",
    # Form 1099-SA's boxes and the Form 8889 line 15 figure.
    "gross_distribution_cents": "Gross distribution — box 1 of this 1099-SA.",
    "hsa_distribution_code": f"The distribution code printed in box 3 of this 1099-SA. Answer "
                             f"with one of: {_offer('hsa_distribution_code')}.",
    "qualified_medical_expenses_cents":
        "Unreimbursed qualified medical expenses paid with this distribution (Form 8889, line "
        "15). Enter 0 if none.",
    "hsa_exception_amount_cents":
        "Of this person's taxable HSA distributions (Form 8889, line 16), how much was "
        "distributed after they became disabled, after the account beneficiary died, or after "
        "they turned 65? Enter 0 if none of it (Form 8889, line 17b).",
    "hsa_exception_reason": f"Which of those is the ground for that amount? Answer with one of: "
                            f"{_offer('hsa_exception_reason')}.",
    # Form 8889 Part I on a filer with a W-2 box 12 code W amount, in the ask order.
    "hsa_medicare": f"Was this person enrolled in Medicare during 2025? Answer with one of: "
                    f"{_offer('hsa_medicare')}; used for Form 8889 Part I.",
    # the month Medicare enrollment began.
    "hsa_medicare_first_month":
        f"In which month of 2025 did this person's Medicare enrollment begin? Answer with one of: "
        f"{_offer('hsa_medicare_first_month')}; used for Form 8889, line 3.",
    "hsa_hdhp_coverage": f"Was this person covered by a high deductible health plan during 2025? "
                         f"Answer with one of: {_offer('hsa_hdhp_coverage')}; used for Form 8889, "
                         f"line 1.",
    "hsa_hdhp_type": f"Which coverage did that plan provide? Answer with one of: "
                     f"{_offer('hsa_hdhp_type')}; used for Form 8889, line 1.",
    # the separate-return spouse's twelve coverage months.
    "spouse_hsa_coverage_jan":
        f"On the first day of January 2025, what coverage did your spouse's high deductible "
        f"health plan provide? Answer with one of: {_offer('spouse_hsa_coverage_jan')}; used for "
        f"Form 8889, lines 3 and 6.",
    "spouse_hsa_coverage_feb":
        f"On the first day of February 2025, what coverage did your spouse's high deductible "
        f"health plan provide? Answer with one of: {_offer('spouse_hsa_coverage_feb')}; used for "
        f"Form 8889, lines 3 and 6.",
    "spouse_hsa_coverage_mar":
        f"On the first day of March 2025, what coverage did your spouse's high deductible "
        f"health plan provide? Answer with one of: {_offer('spouse_hsa_coverage_mar')}; used for "
        f"Form 8889, lines 3 and 6.",
    "spouse_hsa_coverage_apr":
        f"On the first day of April 2025, what coverage did your spouse's high deductible "
        f"health plan provide? Answer with one of: {_offer('spouse_hsa_coverage_apr')}; used for "
        f"Form 8889, lines 3 and 6.",
    "spouse_hsa_coverage_may":
        f"On the first day of May 2025, what coverage did your spouse's high deductible "
        f"health plan provide? Answer with one of: {_offer('spouse_hsa_coverage_may')}; used for "
        f"Form 8889, lines 3 and 6.",
    "spouse_hsa_coverage_jun":
        f"On the first day of June 2025, what coverage did your spouse's high deductible "
        f"health plan provide? Answer with one of: {_offer('spouse_hsa_coverage_jun')}; used for "
        f"Form 8889, lines 3 and 6.",
    "spouse_hsa_coverage_jul":
        f"On the first day of July 2025, what coverage did your spouse's high deductible "
        f"health plan provide? Answer with one of: {_offer('spouse_hsa_coverage_jul')}; used for "
        f"Form 8889, lines 3 and 6.",
    "spouse_hsa_coverage_aug":
        f"On the first day of August 2025, what coverage did your spouse's high deductible "
        f"health plan provide? Answer with one of: {_offer('spouse_hsa_coverage_aug')}; used for "
        f"Form 8889, lines 3 and 6.",
    "spouse_hsa_coverage_sep":
        f"On the first day of September 2025, what coverage did your spouse's high deductible "
        f"health plan provide? Answer with one of: {_offer('spouse_hsa_coverage_sep')}; used for "
        f"Form 8889, lines 3 and 6.",
    "spouse_hsa_coverage_oct":
        f"On the first day of October 2025, what coverage did your spouse's high deductible "
        f"health plan provide? Answer with one of: {_offer('spouse_hsa_coverage_oct')}; used for "
        f"Form 8889, lines 3 and 6.",
    "spouse_hsa_coverage_nov":
        f"On the first day of November 2025, what coverage did your spouse's high deductible "
        f"health plan provide? Answer with one of: {_offer('spouse_hsa_coverage_nov')}; used for "
        f"Form 8889, lines 3 and 6.",
    "spouse_hsa_coverage_dec":
        f"On the first day of December 2025, what coverage did your spouse's high deductible "
        f"health plan provide? Answer with one of: {_offer('spouse_hsa_coverage_dec')}; used for "
        f"Form 8889, lines 3 and 6.",
    # the twelve coverage months.
    "hsa_coverage_jan":
        f"On the first day of January 2025, what coverage did this person's high deductible "
        f"health plan provide? Answer with one of: {_offer('hsa_coverage_jan')}; used for "
        f"Form 8889, line 3.",
    "hsa_coverage_feb":
        f"On the first day of February 2025, what coverage did this person's high deductible "
        f"health plan provide? Answer with one of: {_offer('hsa_coverage_feb')}; used for "
        f"Form 8889, line 3.",
    "hsa_coverage_mar":
        f"On the first day of March 2025, what coverage did this person's high deductible "
        f"health plan provide? Answer with one of: {_offer('hsa_coverage_mar')}; used for "
        f"Form 8889, line 3.",
    "hsa_coverage_apr":
        f"On the first day of April 2025, what coverage did this person's high deductible "
        f"health plan provide? Answer with one of: {_offer('hsa_coverage_apr')}; used for "
        f"Form 8889, line 3.",
    "hsa_coverage_may":
        f"On the first day of May 2025, what coverage did this person's high deductible "
        f"health plan provide? Answer with one of: {_offer('hsa_coverage_may')}; used for "
        f"Form 8889, line 3.",
    "hsa_coverage_jun":
        f"On the first day of June 2025, what coverage did this person's high deductible "
        f"health plan provide? Answer with one of: {_offer('hsa_coverage_jun')}; used for "
        f"Form 8889, line 3.",
    "hsa_coverage_jul":
        f"On the first day of July 2025, what coverage did this person's high deductible "
        f"health plan provide? Answer with one of: {_offer('hsa_coverage_jul')}; used for "
        f"Form 8889, line 3.",
    "hsa_coverage_aug":
        f"On the first day of August 2025, what coverage did this person's high deductible "
        f"health plan provide? Answer with one of: {_offer('hsa_coverage_aug')}; used for "
        f"Form 8889, line 3.",
    "hsa_coverage_sep":
        f"On the first day of September 2025, what coverage did this person's high deductible "
        f"health plan provide? Answer with one of: {_offer('hsa_coverage_sep')}; used for "
        f"Form 8889, line 3.",
    "hsa_coverage_oct":
        f"On the first day of October 2025, what coverage did this person's high deductible "
        f"health plan provide? Answer with one of: {_offer('hsa_coverage_oct')}; used for "
        f"Form 8889, line 3.",
    "hsa_coverage_nov":
        f"On the first day of November 2025, what coverage did this person's high deductible "
        f"health plan provide? Answer with one of: {_offer('hsa_coverage_nov')}; used for "
        f"Form 8889, line 3.",
    "hsa_coverage_dec":
        f"On the first day of December 2025, what coverage did this person's high deductible "
        f"health plan provide? Answer with one of: {_offer('hsa_coverage_dec')}; used for "
        f"Form 8889, line 3.",
    "hsa_other_coverage": f"Did this person have other health coverage that is not a high "
                          f"deductible health plan? Answer with one of: "
                          f"{_offer('hsa_other_coverage')}; used for Form 8889 Part I.",
    "hsa_funding_distribution":
        "Did this person make a qualified HSA funding distribution from an IRA in 2025 — a "
        "transfer the IRA trustee made directly into the health savings account? "
        "A yes is then asked for the amount on each IRA Form 1099-R; used for Form 8889, "
        "line 10 and Form 1040, line 4b.",
    "hsa_prior_funding_distribution_election":
        "Did this person make a qualified HSA funding distribution in any earlier year? The "
        "election can be made once in a lifetime. Used for Form 8889, "
        "line 10 and Form 1040, line 4b.",
    # the testing-period month.
    "hsa_testing_period_first_ineligible_month":
        f"This person's IRA-to-HSA transfer opened a testing period that runs from the month of "
        f"the transfer through the last day of the 12th month after it. What was the first month "
        f"in that window in which they were not an eligible individual? Answer with one of: "
        f"{_offer('hsa_testing_period_first_ineligible_month')}; used for Form 8889 Part III, "
        f"line 19 and Schedule 2, line 17d.",
    "qualified_hsa_funding_distribution_cents":
        "How much of this Form 1099-R's distribution did the IRA trustee transfer directly into "
        "the health savings account (a qualified HSA funding distribution)? Enter 0 if none of "
        "it; used for Form 8889, line 10 and Form 1040, line 4b.",
    # the qualified charitable distribution.
    "qualified_charitable_distribution_cents":
        "How much of this Form 1099-R's distribution did the IRA trustee pay directly to a "
        "charity (a qualified charitable distribution)? Enter 0 if none of it; used for Form "
        "1040, line 4b.",
    "qcd_to_split_interest_entity":
        "Was that payment the one-time election to a charitable remainder trust, charitable "
        "remainder annuity trust or charitable gift annuity (a split-interest entity)? "
        "Used for Form 1040, line 4b.",
    "qcd_prior_deducted_ira_contributions_cents":
        "The traditional IRA contributions this person deducted in earlier years in which they "
        "were 70½ or older that have not already reduced a qualified charitable distribution — "
        "0 if none; Pub 590-B Appendix D line 1; used for Form 1040, line 4b.",
    # the indirect rollover.
    "rolled_over_cents":
        "How much of this Form 1099-R's distribution did this person roll over themselves into "
        "another retirement account within 60 days? Enter 0 if none of it, or if it was later "
        "than 60 days; used for Form 1040, line 4b or 5b.",
    "ira_one_rollover_per_year":
        "Was this the only IRA-to-IRA rollover this person made in the 12 months before it (the "
        "one-rollover-per-year rule)? Used for Form 1040, line 4b.",
    # the code-3 disability form's question — the same words the gaps carry.
    "reached_minimum_retirement_age":
        "Had this person reached the minimum retirement age set by the employer's plan when this "
        "disability payment was made — generally the age at which the plan first pays a pension to "
        "someone who is not disabled? Used for Form 1040, line 1h.",
    # the public-safety-officer premium exclusion (IRC 402(l)) — the same words the gaps carry.
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
    # the death-benefit chain (IRC 101) — the same words the gaps carry.
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
    # the month of the IRA-to-HSA transfer.
    "hsa_funding_distribution_transfer_month":
        f"In which month of 2025 did the IRA trustee transfer the money into this person's "
        f"health savings account? Answer with one of: {_offer('hsa_funding_distribution_transfer_month')}; "
        f"used for Form 8889, line 10 and Form 1040, line 4b.",
    "hsa_spouse_contributed":
        "On this separate return: did this person's spouse have contributions to a health savings "
        "account for 2025? Used for Form 8889, line 6.",
    "hsa_marital_status_changed":
        "Did this person's marital status change during 2025 — a marriage, a divorce, or the loss "
        "of a spouse? Used for Form 8889, line 3.",
    "hsa_marital_change_affects_limit":
        "Does that change affect this person's HSA contribution limit — did the coverage type "
        "change with it? Used for Form 8889, line 3.",
    # Form 2441 line 1 (the providers) and line 2 (each qualifying person's expenses).
    "provider_type": f"Who provided this care? Answer with one of: {_offer('provider_type')} "
                     f"(Form 2441, line 1, column (c)).",
    "is_household_employee": ("Was this care provider your household employee in 2025? Answer "
                              "yes or no — for example, this generally includes nannies but not "
                              "daycare centers (Form 2441, line 1, column (d))."),
    "amount_paid_cents": "Amount paid to this care provider in 2025 (Form 2441, line 1, column (e)).",
    # Form 1095-A Part III's cells, each by its line and column, and Form 8962's questions.
    "jan_premium_cents": "Form 1095-A line 21 (January), column A \u2014 Monthly enrollment premiums. Enter 0 or leave blank for a month without coverage.",
    "jan_slcsp_cents": "Form 1095-A line 21 (January), column B \u2014 Monthly second lowest cost silver plan (SLCSP) premium. Enter 0 or leave blank for a month without coverage.",
    "jan_aptc_cents": "Form 1095-A line 21 (January), column C \u2014 Monthly advance payment of premium tax credit. Enter 0 or leave blank for a month without coverage.",
    "feb_premium_cents": "Form 1095-A line 22 (February), column A \u2014 Monthly enrollment premiums. Enter 0 or leave blank for a month without coverage.",
    "feb_slcsp_cents": "Form 1095-A line 22 (February), column B \u2014 Monthly second lowest cost silver plan (SLCSP) premium. Enter 0 or leave blank for a month without coverage.",
    "feb_aptc_cents": "Form 1095-A line 22 (February), column C \u2014 Monthly advance payment of premium tax credit. Enter 0 or leave blank for a month without coverage.",
    "mar_premium_cents": "Form 1095-A line 23 (March), column A \u2014 Monthly enrollment premiums. Enter 0 or leave blank for a month without coverage.",
    "mar_slcsp_cents": "Form 1095-A line 23 (March), column B \u2014 Monthly second lowest cost silver plan (SLCSP) premium. Enter 0 or leave blank for a month without coverage.",
    "mar_aptc_cents": "Form 1095-A line 23 (March), column C \u2014 Monthly advance payment of premium tax credit. Enter 0 or leave blank for a month without coverage.",
    "apr_premium_cents": "Form 1095-A line 24 (April), column A \u2014 Monthly enrollment premiums. Enter 0 or leave blank for a month without coverage.",
    "apr_slcsp_cents": "Form 1095-A line 24 (April), column B \u2014 Monthly second lowest cost silver plan (SLCSP) premium. Enter 0 or leave blank for a month without coverage.",
    "apr_aptc_cents": "Form 1095-A line 24 (April), column C \u2014 Monthly advance payment of premium tax credit. Enter 0 or leave blank for a month without coverage.",
    "may_premium_cents": "Form 1095-A line 25 (May), column A \u2014 Monthly enrollment premiums. Enter 0 or leave blank for a month without coverage.",
    "may_slcsp_cents": "Form 1095-A line 25 (May), column B \u2014 Monthly second lowest cost silver plan (SLCSP) premium. Enter 0 or leave blank for a month without coverage.",
    "may_aptc_cents": "Form 1095-A line 25 (May), column C \u2014 Monthly advance payment of premium tax credit. Enter 0 or leave blank for a month without coverage.",
    "jun_premium_cents": "Form 1095-A line 26 (June), column A \u2014 Monthly enrollment premiums. Enter 0 or leave blank for a month without coverage.",
    "jun_slcsp_cents": "Form 1095-A line 26 (June), column B \u2014 Monthly second lowest cost silver plan (SLCSP) premium. Enter 0 or leave blank for a month without coverage.",
    "jun_aptc_cents": "Form 1095-A line 26 (June), column C \u2014 Monthly advance payment of premium tax credit. Enter 0 or leave blank for a month without coverage.",
    "jul_premium_cents": "Form 1095-A line 27 (July), column A \u2014 Monthly enrollment premiums. Enter 0 or leave blank for a month without coverage.",
    "jul_slcsp_cents": "Form 1095-A line 27 (July), column B \u2014 Monthly second lowest cost silver plan (SLCSP) premium. Enter 0 or leave blank for a month without coverage.",
    "jul_aptc_cents": "Form 1095-A line 27 (July), column C \u2014 Monthly advance payment of premium tax credit. Enter 0 or leave blank for a month without coverage.",
    "aug_premium_cents": "Form 1095-A line 28 (August), column A \u2014 Monthly enrollment premiums. Enter 0 or leave blank for a month without coverage.",
    "aug_slcsp_cents": "Form 1095-A line 28 (August), column B \u2014 Monthly second lowest cost silver plan (SLCSP) premium. Enter 0 or leave blank for a month without coverage.",
    "aug_aptc_cents": "Form 1095-A line 28 (August), column C \u2014 Monthly advance payment of premium tax credit. Enter 0 or leave blank for a month without coverage.",
    "sep_premium_cents": "Form 1095-A line 29 (September), column A \u2014 Monthly enrollment premiums. Enter 0 or leave blank for a month without coverage.",
    "sep_slcsp_cents": "Form 1095-A line 29 (September), column B \u2014 Monthly second lowest cost silver plan (SLCSP) premium. Enter 0 or leave blank for a month without coverage.",
    "sep_aptc_cents": "Form 1095-A line 29 (September), column C \u2014 Monthly advance payment of premium tax credit. Enter 0 or leave blank for a month without coverage.",
    "oct_premium_cents": "Form 1095-A line 30 (October), column A \u2014 Monthly enrollment premiums. Enter 0 or leave blank for a month without coverage.",
    "oct_slcsp_cents": "Form 1095-A line 30 (October), column B \u2014 Monthly second lowest cost silver plan (SLCSP) premium. Enter 0 or leave blank for a month without coverage.",
    "oct_aptc_cents": "Form 1095-A line 30 (October), column C \u2014 Monthly advance payment of premium tax credit. Enter 0 or leave blank for a month without coverage.",
    "nov_premium_cents": "Form 1095-A line 31 (November), column A \u2014 Monthly enrollment premiums. Enter 0 or leave blank for a month without coverage.",
    "nov_slcsp_cents": "Form 1095-A line 31 (November), column B \u2014 Monthly second lowest cost silver plan (SLCSP) premium. Enter 0 or leave blank for a month without coverage.",
    "nov_aptc_cents": "Form 1095-A line 31 (November), column C \u2014 Monthly advance payment of premium tax credit. Enter 0 or leave blank for a month without coverage.",
    "dec_premium_cents": "Form 1095-A line 32 (December), column A \u2014 Monthly enrollment premiums. Enter 0 or leave blank for a month without coverage.",
    "dec_slcsp_cents": "Form 1095-A line 32 (December), column B \u2014 Monthly second lowest cost silver plan (SLCSP) premium. Enter 0 or leave blank for a month without coverage.",
    "dec_aptc_cents": "Form 1095-A line 32 (December), column C \u2014 Monthly advance payment of premium tax credit. Enter 0 or leave blank for a month without coverage.",
    "allocating_policy_or_alternative_calculation": "Are you allocating policy amounts with another taxpayer, or using the alternative calculation for year of marriage? Used for Form 8962, line 9.",
    "marketplace_estimated_income_at_least_100_fpl": "When you enrolled, did the Marketplace estimate your household income at or above 100% of the federal poverty line? Used for Form 8962 when household income is below the poverty line.",
    "below_poverty_line_not_eligible_for_medicaid_due_to_immigration": "Is your household income below the federal poverty line while you are not eligible for Medicaid because of your immigration status? Used for Form 8962 when household income is below the poverty line.",
    "enrollee_not_eligible_for_marketplace_due_to_immigration": "Is anyone in your tax family who was enrolled on the Marketplace policy not lawfully present in the United States? Used for Form 8962.",
    "mfs_ptc_exception": "On a separate return, do you qualify for the exception for a victim of domestic abuse or spousal abandonment? Used for Form 8962, line A.",
    "mfs_ptc_exception_fourth_year": "Are you claiming that exception for a fourth consecutive year? Used for Form 8962.",
    # Form 2441 lines 13 and 14, reached once a filer reports a benefit.
    "dependent_care_carryover_cents": ("Prior-year dependent care benefits you used during this "
                                       "year's grace period (Form 2441, line 13). Enter 0 if none."),
    # Form 2441 Worksheet A — the second credit for 2024 expenses paid in 2025.
    "paid_prior_year_care_expenses_this_year":
        "Did you pay in 2025 any qualified care expenses you had in 2024 but had not paid by the end of "
        "2024? Used for Form 2441, Worksheet A.",
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
        "11).",
    "dependent_care_forfeited_cents": ("Of the dependent care benefits reported, how much was "
                                       "forfeited or carried forward to 2026 (Form 2441, line 14)? "
                                       "Enter 0 if none."),
    "dependents_modified_agi_cents": "The total modified AGI of the dependents in your tax family who were required to file a return (Form 8962, line 2b). Enter 0 if none were.",
    "care_expenses_cents": ("Qualified care expenses paid in 2025 for this person's care, counting "
                            "only amounts paid to someone who was not your spouse, not the "
                            "child's parent, not your dependent, and not your child under 19 "
                            "(Form 2441, line 2, column (d)). Enter 0 if none."),
    # Form 2441 Part III on a filer row.
    "self_employed_dependent_care_benefits_cents": (
        "Amount this filer received in 2025 under a dependent care assistance program of their "
        "own sole proprietorship or partnership (Form 2441, line 12). Enter 0 if none."),
    "dependent_care_plan_maximum_cents": (
        "The most this filer's employer's dependent care assistance plan allows for 2025, from "
        "the plan's own documents; used for Form 2441 Part III."),
    "is_alaska_pfd": ("Is box 3 of this 1099-MISC an Alaska Permanent Fund dividend? Answer "
                      "yes or no — a dividend is Schedule 1, line 8g; any other payment is "
                      "line 8z."),
    "repaid_cents": ("Of the unemployment compensation on this 1099-G, how much did you repay "
                     "during 2025? Enter 0 if none — used for Schedule 1, line 7."),
    # The Schedule C loss gate: both are the filer's own answers to the printed
    # form, asked only when the business shows a loss — the form itself asks box 32 only there.
    "materially_participated":
        "Did you “materially participate” in the operation of this business during 2025? "
        "(Schedule C line G.)",
    "all_investment_at_risk":
        "Is all the investment in this business at risk? Yes checks box 32a (“All investment "
        "is at risk.”); no checks box 32b (“Some investment is not at risk.”) and asks how "
        "much is at risk.",
    # the itemized Schedule E expense lines — asked only once the property has already
    # named a printed line instead of a lump total (`total_expenses_cents` and these are
    # refused together). Each names its own box.
    "insurance_cents":
        "Insurance for this rental in 2025 (Schedule E, line 9). Enter 0 if none.",
    "management_fees_cents":
        "Management fees for this rental in 2025 (Schedule E, line 11). Enter 0 if none.",
    "repairs_cents":
        "Repairs for this rental in 2025 (Schedule E, line 14). Enter 0 if none.",
    "taxes_cents":
        "Real estate or property taxes for this rental in 2025 (Schedule E, line 16). Enter "
        "0 if none.",
    # the depreciation inputs — the engine computes the deduction from these, never this
    # service. `is_nonresidential_real_property` (and `building_uses_standard_gds`, the
    # recovery-period method beside it) is asked only once a building basis is
    # entered, because that is when the pinned dictionary needs the class to compute a
    # recovery period at all (and refuses to file the return without it).
    "building_basis_cents":
        "The building's depreciable basis — land already excluded (Form 4562, Part III). "
        "Leave blank if you are not claiming building depreciation for this property.",
    "is_nonresidential_real_property":
        "Is the building nonresidential real property — an office, store, or warehouse — "
        "rather than residential rental property? It decides the "
        "building's MACRS recovery period, 39 years or 27.5 (Form 4562, Part III).",
    "building_uses_standard_gds":
        "Is the building depreciated under regular MACRS over 27.5 years or 39 years, rather "
        "than ADS or another recovery period? Used for Schedule E, line 18.",
    "placed_in_service_in_current_year":
        "Was the building placed in service during 2025? A yes "
        "asks the month next.",
    "placed_in_service_month":
        "In what calendar month was the building placed in service? Answer 1 through 12 "
        "(Form 4562, Part III).",
    "has_five_year_property":
        "Does this rental have a 5-year MACRS personal-property item — an appliance, "
        "carpeting, or furniture — placed in service in 2025?",
    "five_year_property_basis_cents":
        "The depreciable cost of that 5-year property item (Form 4562, Part III, line 19b).",
    # The rentals loss gate — both the filer's own §469/§465 answers, asked only
    # when the property's year (or its Form 8582 combine) is a loss.
    "active_participation":
        "Did you actively participate in this rental — make management decisions in a "
        "significant and bona fide sense? (It decides whether Form 8582's special allowance "
        "applies or the loss carries forward.)",
    "fully_at_risk":
        "Is all the investment in this rental at risk? A no asks how much is at risk and the "
        "loss is capped at it (Form 6198).",
    # the amount behind a no. The field name is shared by all three loss streams, so
    # this entry is the RENTALS wording and the other two override it in GROUP_PROMPTS —
    # the `fully_at_risk` split exactly.
    "amount_at_risk_cents":
        "Some investment in this rental is not at risk, so the year's loss is capped: how "
        "much is at risk? Enter the simplified Form 6198 amount (Part II, line 10b), or 0 if "
        "nothing is at risk — used for Form 1040, line 9.",
    # asked on a self-rental (line 1b type 7) whose year is a profit. The field name is
    # this stream's alone, so there is no GROUP_PROMPTS override to write.
    "materially_participates_in_lessee":
        "This property made a profit and its Schedule E line 1b type is 7, Self-Rental. Did you "
        "materially participate in the business it is rented to — the tenant's business, not "
        "the rental itself? A yes treats the profit as non-passive, used for Form 1040, "
        "line 9.",
    "prior_year_unallowed_loss_cents":
        "Prior years' unallowed losses for this rental, from last year's Form 8582 — entered "
        "as a positive amount, or leave blank for none.",
    # asked once a carried-in loss is entered on a rental with active participation yes:
    # Form 8582 keeps that loss in Part IV only when the filer also participated the year it
    # arose.
    "active_participation_when_loss_arose":
        "Did you also actively participate in this rental in the year (or years) the prior "
        "years' unallowed loss arose? If the years differ, answer no. It decides whether the "
        "loss goes in Form 8582 Part IV, with the special allowance, or Part V.",
    # The K-1 gates.
    "publicly_traded_partnership":
        "Item D of this K-1: “Check if this is a publicly traded partnership (PTP)”. Answer "
        "yes if the box is checked, no if not.",
    "basis_cents":
        "The adjusted basis in this interest before the loss — the loss deducts only up to "
        "it; the rest carries forward.",
    # Form 1040 line 12's blindness checkbox, per filer row. Role-neutral here — one
    # column serves both rows of a joint return, and gaps_for carries the you/your-spouse
    # split where the ask is per row.
    "is_blind":
        "Is this person blind? (Form 1040, line 12 prints the checkbox “Are blind” for you "
        "and “Is blind” for a spouse.) True adds the additional standard deduction amount "
        "for blindness.",
    # the educator question per filer row and the amount a yes reaches. Role-neutral
    # here, as `is_blind` is; gaps_for carries the you/your-spouse split.
    "k12_educator":
        "Was this person a kindergarten through grade 12 teacher, instructor, counselor, "
        "principal, or aide in a school for at least 900 hours during a school year? "
        "(Schedule 1, line 11.)",
    "educator_expenses_cents":
        "The unreimbursed classroom expenses this person paid this year (Schedule 1, line 11).",
    # the IRA question per filer row and the two answers a yes reaches.
    "made_ira_contributions":
        "Did this person contribute to an IRA or an ABLE account for the year? (Schedule 1, "
        "line 20; Form 8880, line 1.)",
    "traditional_ira_contributions_cents":
        "The traditional IRA contributions this person made for the year, 0 if they were to a "
        "Roth IRA or an ABLE account only (Schedule 1, line 20).",
    "contributed_to_inherited_ira":
        "Were any of this person's contributions made to an inherited IRA?",
    "inherited_ira_contribution_cents":
        "How much of this person's traditional IRA contributions was new money paid in to an "
        "IRA inherited from someone other than a spouse? Do not count a transfer of the "
        "original owner's balance (Schedule 1, line 20).",
    # the own-HSA-contribution question on every filer row, the two amounts a yes reaches.
    "made_hsa_contributions":
        "Did this person contribute to a health savings account themselves in 2025 — outside "
        "the employer's payroll contributions on Form W-2 box 12 code W? A qualified HSA funding "
        "distribution transferred from an IRA counts as a yes. (Form 8889, line 2.)",
    "hsa_own_contributions_cents":
        "The HSA contributions this person made for 2025 themselves, not through the employer; "
        "0 if the only contribution was a transfer from an IRA (Form 8889, line 2).",
    "hsa_own_contributions_after_year_end_cents":
        "Of those, or in addition, the amount contributed after December 31, 2025 and before "
        "the due date, for 2025; 0 if none (Form 8889, line 2).",
    # Form 5329 line 42 — the printed condition is part of the question.
    "hsa_prior_year_excess_cents":
        "The excess HSA contribution still in this person's account at the end of 2024 — line 48 of "
        "their 2024 Form 5329, only if its line 49 was more than zero; 0 otherwise (Form 5329, "
        "line 42).",
    # Form 5329 line 49's cap — the printed parenthesis is part of the question.
    "hsa_december_31_value_cents":
        "The total value of this person's HSAs on December 31, 2025, including 2025 "
        "contributions made in 2026; 0 only if the accounts were empty (Form 5329, line 49).",
    # Form 8880 — the Roth-and-ABLE follow-up, the student test and the line-4 questions.
    "roth_ira_and_able_contributions_cents":
        "The Roth IRA and ABLE account contributions this person made for the year, 0 if none "
        "(Form 8880, line 1).",
    # the Roth half of that amount, on a joint return — the spousal-limit reduction term.
    "roth_ira_contributions_cents":
        "How much of those contributions went to the Roth IRA, 0 if none "
        "(Schedule 1, line 20).",
    "is_student":
        "Was this person enrolled as a full-time student during any part of five calendar months "
        "of 2025? Used for Form 8880 on a filer (a student's contributions "
        "and distributions are left out of the credit), and for the dependent tests on a "
        "dependent.",
    "received_retirement_distributions_2023_2024":
        "Did this person receive any distribution from a retirement plan, an IRA or an ABLE "
        "account in 2023 or 2024? Used for Form 8880, line 4.",
    "retirement_distributions_2023_cents":
        "The distributions this person received in 2023, 0 if none (Form 8880, line 4).",
    "retirement_distributions_2024_cents":
        "The distributions this person received in 2024, 0 if none (Form 8880, line 4).",
    "received_retirement_distributions_after_year_end":
        "Did, or will, this person receive a distribution from a retirement plan, an IRA or an "
        "ABLE account after December 31, 2025 and before the return's due date, including "
        "extensions? Used for Form 8880, line 4.",
    "retirement_distributions_after_year_end_cents":
        "That distribution amount (Form 8880, line 4).",
    # Dependents: the seven qualifiers, in the words gaps_for asks them.
    "relationship": f"How is this dependent related to the primary filer? Answer with one "
                    f"of: {_offer('relationship')}.",
    # the qualifying-child age test's disability arm, on a dependent's row.
    "is_permanently_disabled": ("Was this dependent permanently and totally disabled at any time "
                                "in 2025? Used for the qualifying-child age test (Form 1040, "
                                "Dependents)."),
    # Form 2441's other qualifying-person arm, on a dependent's row.
    "unable_to_care_for_self": ("Was this dependent physically or mentally unable to care for "
                                "themselves in 2025? Used for Form 2441 "
                                "(a dependent who turned 13 before the year, or on January 1, is "
                                "a qualifying person only if so)."),
    "months_in_home": "How many months did this dependent live with you during the year? "
                      "Six months exactly counts as not more than half. For a child born "
                      "(or who died) during the year, answer 12 if your home was theirs for "
                      "more than half the time they were alive.",
    "is_married": "Is this dependent married?",
    "provided_own_support": "Did this person provide more than half of their OWN support "
                            "for the year?",
    "gross_income_under_limit": "Is this person's own gross income for the year under the "
                                "dependent income limit? (See the Form 1040 instructions' "
                                "gross income test.)",
    "filer_provided_over_half_support": "Did you provide more than half of this person's "
                                        "support for the year?",
    "could_be_qualifying_child_of_another": "Could this person be the qualifying child of "
                                            "another taxpayer?",
    # the split gate's custody questions, on a dependent 18 or older at the end of the year.
    "child_residence_state":
        f"In which state or U.S. territory did this dependent live on July 2, 2025? Answer with "
        f"one of: {_offer('child_residence_state')}.",
    "child_emancipated": ("Was this dependent emancipated under the law of the state they lived "
                          "in, in 2025 or earlier? Used for the rule for children of divorced or "
                          "separated parents (Form 1040, Dependents)."),
    "child_emancipated_after_july_2": ("Was this dependent emancipated after July 2, 2025? Used "
                                       "for the rule for children of divorced or separated "
                                       "parents (Form 1040, Dependents)."),
    # the member-of-household questions, on a dependent not related in a listed way who lived
    # with the filer all year; the local-law one on a Form 2441 qualifying person's row too.
    "was_spouse_during_year": ("Was this person your spouse at any time in 2025? Used for the "
                               "qualifying-relative household test (Form 1040, Dependents)."),
    "relationship_violates_local_law": ("Did your relationship with this person violate local "
                                        "law at any time in 2025? Used for the dependent tests "
                                        "(Form 1040, Dependents) and Form 2441."),
    # asked about the filer's own biological or adopted child only — the one place the
    # engine reads the answer.
    "has_other_biological_or_adoptive_parent": "Does this child have another living "
                                               "biological or adoptive parent?",
    # the benefit-split gate, in the dictionary's own words. Asked about the filer's own
    # biological or adopted child once that child is answered as having another legal parent,
    # one link at a time — the workbook offers all five columns and the service refuses the
    # ones this row's answers do not reach.
    "parents_situation": f"What is your situation with this child's other legal parent? "
                         f"Answer with one of: {_offer('parents_situation')}.",
    "child_in_parents_custody": "As of July 2, was this child still in the legal custody of "
                                "their biological or adoptive parents?",
    "child_lived_with_parents_over_half_year":
        "Did this child live with you and/or their other legal parent for more than six "
        "months of the year?",
    "parents_provided_over_half_support":
        "Did you and/or this child's other legal parent pay more than half of this child's "
        "support for the year?",
    # the non-parental arm's first question, in the dictionary's words — asked on a
    # claimed dependent the filer is not the parent of.
    "child_parents_living": "Are this person's biological or adoptive parents living? Asked "
                            "about a sibling, half- or step-sibling, stepchild, foster child, "
                            "grandchild, or a sibling's child or other descendant; a no claims "
                            "them under the ordinary rules.",
    # the custodial-parent questions, asked once a parent signed the declaration.
    "nights_with_filer_vs_other_parent":
        f"Did this child spend more nights with you, fewer nights with you, or the same number "
        f"of nights with each parent? Answer with one of: {_offer('nights_with_filer_vs_other_parent')}.",
    "filer_agi_higher_than_other_parent":
        "Was your adjusted gross income higher than the other parent's? Asked only when the "
        "nights were equal.",
    # the non-parental split, behind "are this person's own parents living?" = yes.
    "parents_meet_divorced_or_separated_rule":
        "Do this person's parents meet the rule for children of divorced or separated parents, "
        "or parents who lived apart?",
    "a_parent_signed_declaration_not_to_claim":
        "Has either of this person's parents signed a written declaration not to claim them?",
    "custodial_parent_claims_child_as_qualifying_person":
        "Does the custodial parent claim this person as their qualifying person — for head of "
        "household, the earned income credit, or another credit?",
    "filer_agi_higher_than_custodial_parent":
        "Was your adjusted gross income higher than the custodial parent's?",
    "written_declaration": f"Has either parent signed a written declaration not to claim "
                           f"this child, sometimes on Form 8332? Answer with one of: "
                           f"{_offer('written_declaration')}.",
    # the joint-return test, in the dictionary's own words. Asked on a married
    # dependent row only, one link at a time — the workbook offers all three columns and the
    # service refuses the ones this row's answers do not reach.
    "files_joint_return_with_spouse": "Are this dependent and their spouse filing a joint "
                                      "return?",
    "required_to_file_with_spouse": "Are this dependent and their spouse required to file?",
    "joint_return_only_for_refund": "Are this dependent and their spouse filing a return "
                                    "only to claim a refund of income tax withheld or "
                                    "estimated tax paid?",
    # the page-1 "someone can claim you" chain, on every filer row.
    "someone_can_claim_you": "Can someone else claim this person as a dependent? (The form's "
                             "page-1 checkbox: “Someone can claim: You as a dependent”.)",
    "expect_to_be_claimed": "Do you expect that person to claim you this year?",
    "potential_claimer_must_file": "Is the person who could claim you required to file a tax "
                                   "return?",
    "potential_claimer_filed": "Did the person who could claim you file a tax return anyway?",
    "potential_claimer_filed_only_for_refund":
        "Did they file only to get a refund of tax withheld or estimated tax paid?",
    # hoh/qss: the last asks. the upkeep question is also asked on a single
    # return's qualifying rows, so the one static ask says what is true on each status rather
    # than claiming the status turns on it everywhere (the gap `why` already splits the two).
    "filer_paid_most_of_home_upkeep":
        "Did you pay more than half the cost of keeping up the home this person lived in? "
        "It settles a head-of-household or qualifying-surviving-spouse status, and on a "
        "single return it completes the household section.",
    "spouse_death_year": f"Which year did your spouse die? Answer with one of: "
                         f"{_offer('spouse_death_year')}. (A spouse who died during the tax "
                         f"year files jointly for that year.)",
    "could_have_filed_jointly_year_of_death":
        "Could you have filed jointly with your spouse for the year they died, whether or "
        "not you did?",
    # the residence state, on every return; the Alaska Permanent Fund dividend questions
    # behind an Alaska answer.
    "residence_state":
        f"Which U.S. state, or the District of Columbia, did you live in and earn income in "
        f"during the year? Answer with one of: {_offer('residence_state')}.",
    "received_alaska_pfd":
        "Did you receive an Alaska Permanent Fund dividend during the year? (It is reported on "
        "Form 1099-MISC.)",
    "spouse_received_alaska_pfd":
        "Did your spouse receive an Alaska Permanent Fund dividend during the year? (It is "
        "reported on Form 1099-MISC.)",
    # the page-1 digital-assets question, both parts, in the words gaps_for asks them.
    "received_digital_assets": 'At any time during the year, did you receive a digital asset (or a financial interest in one) as a reward, award, or payment for property or services? (Part (a) of the Form 1040 page-1 digital-assets question.)',
    "disposed_digital_assets": 'At any time during the year, did you sell, exchange, gift, or otherwise dispose of a digital asset (or a financial interest in one)? (Part (b) of the same question.)',
    # Schedule B Part III, lines 7a and 8, in the words gaps_for asks them.
    "foreign_financial_account": "At any time during the year, did you have a financial interest in or signature authority over a financial account (such as a bank account, securities account, or brokerage account) located in a foreign country? (Schedule B, line 7a.)",
    "foreign_trust_grantor": "During the year, were you the owner or grantor of a foreign trust? (Schedule B, line 8.)",
    "foreign_trust_transactions": "During the year, did you receive a distribution from, or were you a transferor to, a foreign trust? (Schedule B, line 8.)",
    # Form 8862's credit-history questions, in the words gaps_for asks them.
    "eitc_reduced_or_disallowed": "Has the IRS reduced or disallowed an earned income credit you claimed in a prior year, for any reason other than a math or clerical error? (Form 8862, Part II.)",
    "ctc_odc_reduced_or_disallowed": "Has the IRS reduced or disallowed a child tax credit, additional child tax credit or credit for other dependents you claimed in a prior year, for any reason other than a math or clerical error? (Form 8862, Part III.)",
    "qualifying_child_of_another": "Could you (or your spouse if filing jointly) be claimed as a qualifying child of another taxpayer for the year? (Form 8862, line 4.)",
    # Form 1040 line 26 and what a yes reaches, in the words gaps_for asks them.
    "paid_estimated_taxes": "Did you make estimated tax payments for the year, or apply an amount from last year's return to this year's tax? (Form 1040, line 26.)",
    "estimated_tax_payments_cents": "The total estimated tax payments made for the year, plus any amount applied from last year's return.",
    # the filer's own IRC 1341(a)(5) figure — provenance, never instruction. Leave it blank
    # if you did not repay income counted in an earlier year, or did not figure this credit.
    "section_1341_credit_cents":
        "If you repaid income that was counted in an earlier year and figured the credit for it "
        "(Publication 525), enter that credit — Schedule 3, line 13b. Leave blank if none.",
    # the royalty activity's root answers — the same words the gaps carry.
    "royalty_expenses_cents":
        "What were the total ordinary expenses for the royalty income above — agent or "
        "collection fees, legal fees, and similar costs, but not depletion? Enter the total, or "
        "0 if none; used for Schedule E.",
    "royalty_is_oil_gas_geothermal":
        "Is the royalty income above from an oil, gas, or geothermal property? "
        "Used for Schedule E's depletion deduction.",
    "estimated_payments_under_different_name": "Were any of those payments made under a name different from the one on this return?",
    "estimated_payments_with_former_spouse": "Were any of those payments made jointly with a former spouse?",
    # Schedule 1 lines 2a/19a — provenance, never instruction. Leave the amount blank if
    # none; each amount reaches its own gate.
    "alimony_received_cents":
        "Did you receive alimony or separate maintenance payments during the year? If so, enter "
        "the total — Schedule 1, line 2a. Leave blank if none.",
    "alimony_received_pre2019_agreement":
        "Was the divorce or separation agreement under which you received that alimony entered "
        "into on or before December 31, 2018, and not later modified to end its inclusion in "
        "income?",
    "alimony_paid_cents":
        "Did you pay alimony or separate maintenance payments during the year? If so, enter the "
        "total — Schedule 1, line 19a. Leave blank if none.",
    "alimony_paid_pre2019_agreement":
        "Was the divorce or separation agreement under which you paid that alimony entered into "
        "on or before December 31, 2018, and not later modified to end its deductibility?",
    # IRC 215(d) — reached once the amount is given and the agreement is pre-2019.
    "alimony_paid_section_682_trust":
        "Was that alimony paid to your former spouse as the income of a trust (an alimony trust "
        "under section 682), rather than by you directly under the divorce or separation "
        "agreement?",
    # the Form 1040 page-1 main-home checkbox, in the form's own words — provenance, never
    # instruction. Leave it blank if your main home was in the U.S. for more than half of 2025;
    # answer only if it was not.
    "main_home_in_us_over_half_year":
        "Check here if your main home, and your spouse's if filing a joint return, was in the "
        "U.S. for more than half of 2025 (Form 1040, page 1). Leave blank if yes; answer no "
        "only if it was not.",
    # Schedule 1 line 21 and what a yes reaches, in the words gaps_for asks them.
    # the line 6c election, asked once a benefit statement exists.
    "elects_lump_sum_benefits": "Did any of the benefits reported on your statements include a lump-sum payment for an earlier year that you elect to figure under the lump-sum method? (Form 1040, line 6c.)",
    # Form 8960's sole-trader question, asked once a Schedule C exists.
    "only_business_is_trading_securities": "Is trading in financial instruments or commodities your only trade or business? (Form 8960.)",
    "paid_student_loan_interest": "Did you pay interest on a student loan during the year? (Schedule 1, line 21.)",
    "student_loans_qualify": "Were the loans taken out solely to pay qualified education expenses for you, your spouse, or your dependent, and not from a related person or an employer plan?",
    "student_loan_interest_cents": "The student loan interest paid during the year (Form 1098-E, box 1).",
    # IRC 221(e)(1)'s two reductions — reached once the loans qualify.
    "student_loan_interest_employer_paid_cents":
        "How much of that student loan interest did your employer pay for you, tax-free, under "
        "an educational assistance program? Enter 0 if none.",
    "student_loan_interest_from_qtp_cents":
        "How much of that student loan interest was paid with tax-free earnings from a qualified "
        "tuition program (a 529 plan)? Enter 0 if none.",
    # the Form 8880 filed-jointly pair, behind a prior-year distribution on a joint return.
    "filed_jointly_2023": ("Did you and your spouse file a joint return for 2023? Used for Form "
                           "8880, line 4."),
    "filed_jointly_2024": ("Did you and your spouse file a joint return for 2024? Used for Form "
                           "8880, line 4."),
    # the combat pay elections, on a return with a W-2 box 12 code Q amount.
    "combat_pay_election": (f"Box 12 code Q of a W-2 reports nontaxable combat pay. Do you elect to "
                            f"count it as earned income for the earned income credit? Answer with "
                            f"one of: {_offer('combat_pay_election')}; used for Form 1040 line 1i "
                            f"(the credit is figured with the answer given)."),
    "cdcc_combat_pay_election": (f"The same combat pay, for the child and dependent care credit: do "
                                 f"you elect to count it as earned income there? Answer with one "
                                 f"of: {_offer('cdcc_combat_pay_election')}; used for Form 2441 "
                                 f"Part II."),
    "dependent_care_benefits_combat_pay_election": (
        f"The same combat pay, for the dependent care benefits on your W-2: do you elect to count "
        f"it as earned income for the exclusion? Answer with one of: "
        f"{_offer('dependent_care_benefits_combat_pay_election')}; used for Form 2441 Part III."),
    # the excess-in-wages question, on a return with a W-2 box 12 code W amount.
    "hsa_excess_in_w2_wages": ("Did the employer already include any excess HSA contribution in "
                               "W-2 box 1 wages? One answer for the whole return — on a joint "
                               "return a yes drops both filers' excess from income. "
                               "Used for Form 8889 (the excess is other income on "
                               "Schedule 1 line 8z unless it is)."),
    # the joint return's filing-requirement pair, behind a claimable spouse.
    "couple_required_to_file": "Are you and your spouse required to file a tax return?",
    "couple_files_only_for_refund":
        "Are you filing only to get a refund of tax withheld or estimated tax paid — not to "
        "claim dependents or credits?",
    # the lived-together chain, on every married return.
    "lived_with_spouse_all_year": "Did you live with your spouse for the whole year?",
    "months_lived_with_spouse":
        f"How long did you live with your spouse this year? Answer with one of: "
        f"{_offer('months_lived_with_spouse')}.",
    "separation_agreement_on_last_day":
        "On the last day of the year, were you living apart from your spouse under a "
        "separation agreement?",
    "lived_apart_last_six_months":
        "Did you live apart from your spouse for the last six months of the year?",
    # mfs: the separate-return pair.
    "spouse_itemizes":
        "Does your spouse itemize deductions on their separate return? (The form asks: "
        "“Your spouse itemizes on a separate return”.) If yes, this return's standard "
        "deduction is zero.",
    "community_property_domicile":
        "Is your domicile, or your spouse's, in a community property state? (Form 8958 keys "
        "on domicile.) A separate return in a community property state cannot be computed "
        "here.",
    # the separate-return spouse chain, in the words gaps_for asks them.
    "spouse_files_return":
        "Does your spouse file their own return for the year? If not, the next questions "
        "decide whether the spouse's age or blindness amount joins this return's standard "
        "deduction (Form 1040, line 12).",
    "spouse_had_gross_income":
        "Did your spouse have any gross income for the year? (Used for Form 1040, line 12.)",
    "spouse_can_be_claimed":
        "Can someone else claim your spouse as a dependent? (Used for Form 1040, line 12.)",
    "spouse_65_or_older":
        "Was your spouse born before January 2, 1961? (The form's spouse checkbox on line 12 "
        "— a yes adds the spouse's age amount to this return's standard deduction.)",
    "spouse_is_blind":
        "Is your spouse blind? (The form's spouse checkbox on line 12 — a yes adds the "
        "spouse's blindness amount to this return's standard deduction.)",
    # the separate return's coverage question.
    "spouse_covered_by_employer_plan":
        "Was your spouse covered by a retirement plan at work during the year? (Schedule 1, "
        "line 20.)",
    "source": f"What kind of entity issued this K-1? Answer with one of: {_offer('source')}.",
    # which benefit statement this is — the amounts are named without a box number
    # because the two forms number them differently.
    "form_type": f"Which statement reports these benefits? Answer with one of: {_offer('form_type')}.",
}

# A prompt keyed by (GROUP, field), for the case where the group changes what the question
# MEANS. `person` is that case: on a W-2 it asks whose wages these are, and on a Schedule C it asks
# who the proprietor is — a business belongs to ONE filer, and a joint return has to pick one. Told
# only "which person does this document belong to?", a joint filer with one business cannot see
# that their answer decides whose self-employment it is.

# Looked up FIRST, with `PROMPTS` as the fallback, so a group nobody has worded keeps the generic
# question rather than inheriting another form's: `rentals` and `k1s` also require only `person`
# and are deliberately left generic here — the same mechanism, unworded, until each is worded on
# the strength of its own form.
GROUP_PROMPTS = {
    # Publication 915 Worksheet 2 and 3 — one row per earlier year the lump-sum payment is
    # for. Each ask names the worksheet line it fills; the year picks which worksheet runs.
    ("ssa_lump_sum_years", "earlier_year"):
        "Which earlier year is this row for? The benefit statement shows the year or years the "
        "payment is for; enter a year from 1984 to 2024.",
    ("ssa_lump_sum_years", "lump_sum_portion_cents"):
        "How much of the lump-sum payment is for that year? (Publication 915, Worksheet 2 and 3, line "
        "1.)",
    ("ssa_lump_sum_years", "benefits_received_cents"):
        "What benefits did you receive in that year itself — box 5 of that year's statement? Enter 0 "
        "if none.",
    ("ssa_lump_sum_years", "adjusted_gross_income_cents"):
        "What was your adjusted gross income for that year? (Publication 915, Worksheet 2 and 3, line "
        "3.)",
    ("ssa_lump_sum_years", "exclusions_cents"):
        "What exclusions and adjustments did that year's return have? (Publication 915, Worksheet 2 "
        "and 3, line 4.) Enter 0 if none.",
    ("ssa_lump_sum_years", "tax_exempt_interest_cents"):
        "What tax-exempt interest did you have that year? (Publication 915, Worksheet 2 and 3, line "
        "5.) Enter 0 if none.",
    ("ssa_lump_sum_years", "taxable_benefits_reported_cents"):
        "How much of that year's benefits was already taxed — what that year's return reported? Enter "
        "0 if none.",
    ("ssa_lump_sum_years", "filed_jointly"):
        "Was that year's return a joint return? It decides the base amount the "
        "refigure uses.",
    ("ssa_lump_sum_years", "mfs_lived_with_spouse"):
        "Was that year's return married filing separately, with the two of you living together at "
        "some time that year?",

    # the benefit statement's withholding box — "federal_withholding_cents" is shared
    # with three other forms, and each numbers it differently.
    ("ssa1099s", "federal_withholding_cents"):
        "Federal income tax withheld — SSA-1099 box 6, or RRB-1099 box 10. Enter 0 if the box "
        "is blank.",
    # Form 1099-G's withholding box.
    ("g1099s", "federal_withholding_cents"):
        "Federal income tax withheld — box 4 of this 1099-G. Enter 0 if the box is blank.",
    # Form 1099-MISC's withholding box.
    ("misc1099s", "federal_withholding_cents"):
        "Federal income tax withheld — box 4 of this 1099-MISC. Enter 0 if the box is blank.",
    # royalties_cents is shared with k1s[] (box 7 there); this form's own box number.
    ("misc1099s", "royalties_cents"):
        "Royalties — box 2 of this 1099-MISC. Enter 0 if the box is blank.",
    # The K-1 loss gate: both field names are REUSED from other groups
    # (schedule_c's line G, the rentals at-risk pair), and the fallback would print the other
    # form's words — "Schedule C line G" on a K-1, "this rental" on a partnership. The group
    # changes what the question means, so the group speaks.
    ("k1s", "materially_participated"):
        "This K-1's box 1 is a loss. Did you materially participate in the partnership or "
        "S corporation's business? A no routes the loss through "
        "Form 8582 rather than deducting it now.",
    ("k1s", "fully_at_risk"):
        "Is all the investment in this K-1's activity at risk? A no asks how much is at risk "
        "and the loss is capped at it (Form 6198).",
    # the same question in each stream's own words — "this business", "this rental",
    # "this K-1's activity" — because the group is what changes what it is about.
    ("k1s", "amount_at_risk_cents"):
        "Some investment in this K-1's activity is not at risk, so the box 1 loss is capped: "
        "how much is at risk? Enter the simplified Form 6198 amount (Part II, line 10b), or 0 "
        "if nothing is at risk — used for Form 1040, line 9.",
    ("schedule_c", "amount_at_risk_cents"):
        "Box 32b is checked on this business, so the line 31 loss is capped: how much is at "
        "risk? Enter the simplified Form 6198 amount (Part II, line 10b), or 0 if nothing is "
        "at risk — used for Form 1040, lines 9, 11, 15 and 24.",
    # the guaranteed-payments asks. Item G is printed on every Schedule K-1 (Form 1065);
    # box 14 code A becomes a question once a guaranteed payment is reported, and a blank box
    # is answered as 0 — the words say so, and say nothing about what the box ought to hold.
    ("k1s", "general_partner"):
        "Item G of this Schedule K-1 (Form 1065): which box is checked — “General partner or "
        "LLC member-manager” (answer yes) or “Limited partner or other LLC member” (answer "
        "no)? It decides how a guaranteed payment for capital and a publicly traded "
        "partnership's loss are treated.",
    ("k1s", "se_earnings_cents"):
        "This K-1 reports a guaranteed payment, so box 14 code A (self-employment earnings) "
        "has to be answered: enter the amount printed beside code A, or 0 if box 14 is blank "
        "— used for Schedule SE, and for Form 1040, lines 11 and 24.",
    # box 20 code Z. The ask names the box and the code as the form's own list does,
    # and says what a statement reporting nothing is answered as. The sign rule is the
    # statement's own words, not an instruction of ours.
    ("k1s", "qualified_ptp_income_cents"):
        "Item D of this Schedule K-1 (Form 1065) is checked, so box 20 code Z (Section 199A "
        "information) has to be answered: enter the qualified publicly traded partnership "
        "income from the statement attached to this K-1 — a loss as a negative amount, or 0 "
        "if the statement reports no qualified amount.",
    # Form 1099-B: the boxes build's list cannot find on a page yet.
    ("b1099s", "proceeds_cents"):
        "Box 1d of this Form 1099-B — proceeds — used for Form 1040, line 9.",
    ("b1099s", "cost_basis_cents"):
        "Box 1e of this Form 1099-B — cost or other basis. If the box is blank, enter the basis "
        "from your own records, or 0 — used for Form 1040, line 9.",
    ("b1099s", "collectibles"):
        "Is the box 3 “Collectibles” checkbox marked on this Form 1099-B? Answer yes or no.",
    ("b1099s", "qualified_opportunity_fund"):
        "Is the box 3 “QOF” checkbox marked on this Form 1099-B? Answer yes or no.",
    # the same statement on the K-1s that are not a PTP's — per-business qualified
    # business income. The box differs by form, so the ask names both.
    ("k1s", "section_199a_qbi_cents"):
        "Enter the qualified business income from the section 199A statement attached to this "
        "Schedule K-1 (box 20 code Z on Form 1065, box 17 code V on Form 1120-S), or 0 if the "
        "statement reports none; a loss as a negative amount — used for Form 1040, lines 13 "
        "and 15.",
    # it stopped being optional the day Form 8995-A began computing — an unanswered
    # flag left the qualified amount whole, which is the favourable side above the section
    # 199A threshold, so it is asked like the amount beside it.
    ("k1s", "qualified_ptp_is_sstb"):
        "Is this publicly traded partnership a specified service trade or business? No box on "
        "the K-1 says so; it is used for Schedule A (Form 8995-A), "
        "Part II.",
    ("k1s", "ptp_prior_year_unallowed_loss_cents"):
        "How much loss from THIS publicly traded partnership did earlier years suspend and "
        "carry forward? Enter it as a positive amount. Leave it blank and nothing is sent — "
        "no prior-year unallowed loss from this PTP.",
    # the deductible part of a box 14 code A LOSS. The prompt table is static, so the
    # printed loss cannot be quoted back here the way the gap `why` quotes it; the ask names
    # the box and the sign instead, in the printed instruction's own terms.
    ("k1s", "deductible_se_loss_cents"):
        "This K-1's box 14 code A is a loss. Enter how much of that loss you are allowed to "
        "deduct this year after the basis, at-risk and passive-activity limits, as a negative "
        "amount or 0 if none — used for Schedule SE, and for Form 1040, lines 11, 15 and 24.",
    ("schedule_c", "person"):
        "Which person on this return is the proprietor of this business? A Schedule C belongs to "
        "ONE filer; on a joint return, say which filer — the primary or the spouse. (The name "
        "on the form is removed before it is read, so it has to be asked.)",
}

# Facts nothing in a folder of tax documents can state. Named so the interview can explain WHY it is
# asking rather than appearing to have failed to read something.
NOT_ON_ANY_DOCUMENT = frozenset({
    "filing_status", "persons", "role", "birth_year", "birth_month", "tin_type",
    # line 12's blindness checkbox — a fact about the person, printed on no document
    # this service reads.
    "is_blind",
    # the educator question and the amount — the person's own work and spending.
    "k12_educator", "educator_expenses_cents",
    # the IRA question and its answers — the person's own contributions.
    "made_ira_contributions", "traditional_ira_contributions_cents", "contributed_to_inherited_ira",
    "inherited_ira_contribution_cents",
    "made_hsa_contributions", "hsa_own_contributions_cents",
    "hsa_own_contributions_after_year_end_cents",
    "hsa_december_31_value_cents",
    "hsa_prior_year_excess_cents",
    # the Schedule 1 line 7 same-year repayment — the filer's own figure, on no 1099-G box.
    "repaid_cents",
    # whether a 1099-MISC's box 3 is an Alaska PFD — the filer's knowledge, on no box.
    "is_alaska_pfd",
    # the royalty activity's ordinary expenses (the taxpayer's own records, never a 1099
    # box) and the oil/gas/geothermal classification — the filer's own knowledge of the property.
    "royalty_expenses_cents", "royalty_is_oil_gas_geothermal",
    # Form 8889 lines 15 and 17a/17b — the filer's own figures, on no 1099-SA box.
    "qualified_medical_expenses_cents", "hsa_exception_amount_cents", "hsa_exception_reason",
    # Form 2441 is a form the filer prepares — its lines 1 and 2 are the filer's own
    # answers (a provider's Form W-10 gives identity, which is not entered).
    "provider_type", "is_household_employee", "amount_paid_cents", "care_expenses_cents",
    # Form 8962's questions are the filer's own answers, on no 1095-A box.
    "allocating_policy_or_alternative_calculation", "marketplace_estimated_income_at_least_100_fpl",
    "below_poverty_line_not_eligible_for_medicaid_due_to_immigration",
    "enrollee_not_eligible_for_marketplace_due_to_immigration", "dependents_modified_agi_cents",
    "mfs_ptc_exception", "mfs_ptc_exception_fourth_year",
    # Form 2441 Part III's own questions — box 10 is the one on a document.
    "self_employed_dependent_care_benefits_cents", "dependent_care_plan_maximum_cents",
    "dependent_care_carryover_cents", "dependent_care_forfeited_cents",
    "unable_to_care_for_self",
    # a dependent's disability — the filer's own knowledge, on no document.
    "is_permanently_disabled",
    # The Schedule C loss-gate pair: a Schedule C is a form the filer prepares, not one they
    # receive — line G and box 32 carry the filer's own answers, so no folder of documents can
    # state them.
    "materially_participated", "all_investment_at_risk",
    # The rentals pair: the filer's own §469(i)/§465 answers.
    "active_participation", "fully_at_risk", "active_participation_when_loss_arose",
    # no Schedule E box asks it — the §469(c)(1)/(h) determination about the LESSEE
    # business is the filer's own. Line 1b's type code, which derives the other half of the
    # rule, IS printed, which is why only this one is here.
    "materially_participates_in_lessee",
    # the amount at risk is not a box on any of the three forms either — Form 6198's
    # own Part II line 10b, worked out from the filer's basis in the activity. Box 32 IS
    # printed on a Schedule C, which is why the boolean above and this amount split.
    "amount_at_risk_cents",
    # The K-1 basis: a limitation figure the filer keeps, not a box on the K-1 itself. Item D
    # IS printed on the form, so it stays on-document.
    "basis_cents",
    # neither is a box. Whether a PTP is a specified service trade or business is a
    # question about the partnership, and the §469(k) carry-in is last year's suspended loss,
    # which this year's K-1 does not print. Box 20 code Z itself IS printed, so the amount
    # stays on-document — the figure lives on the statement attached to it.
    "qualified_ptp_is_sstb", "ptp_prior_year_unallowed_loss_cents",
    # box 14 code A IS printed, but its DEDUCTIBLE part is not — the printed instruction
    # tells the partner to work it out off the return, from basis, at-risk and passive limits
    # this year's K-1 does not state. The `basis_cents` precedent exactly.
    "deductible_se_loss_cents",
    # The separate-return pair: the filer's own knowledge of the spouse's return and domicile.
    "spouse_itemizes", "community_property_domicile",
    # the page-1 "someone can claim you" chain — the filer's own knowledge, on no document.
    "someone_can_claim_you", "expect_to_be_claimed", "potential_claimer_must_file",
    "potential_claimer_filed", "potential_claimer_filed_only_for_refund",
    # the residence state and the Alaska dividend questions — the filer's own knowledge.
    "residence_state", "received_alaska_pfd", "spouse_received_alaska_pfd",
    # the page-1 digital-assets question — the filer's own knowledge, on no document.
    "received_digital_assets", "disposed_digital_assets",
    # Schedule B Part III — the filer's own knowledge, on no document.
    "foreign_financial_account", "foreign_trust_grantor", "foreign_trust_transactions",
    # Form 8862's credit-history questions — the filer's own history, on no document.
    "eitc_reduced_or_disallowed", "ctc_odc_reduced_or_disallowed", "qualifying_child_of_another",
    # Form 1040 line 26 — the filer's own payments, on no document this service reads.
    "paid_estimated_taxes", "estimated_tax_payments_cents", "section_1341_credit_cents",
    "estimated_payments_under_different_name", "estimated_payments_with_former_spouse",
    # alimony has no information return — the amounts and the agreement dates come from the
    # taxpayer's own records / the divorce decree.
    "alimony_received_cents", "alimony_received_pre2019_agreement",
    "alimony_paid_cents", "alimony_paid_pre2019_agreement", "alimony_paid_section_682_trust",
    # Schedule 1 line 21 — the filer's own loans; Form 1098-E is not a collected document.
    "paid_student_loan_interest", "student_loans_qualify", "student_loan_interest_cents",
    "student_loan_interest_employer_paid_cents", "student_loan_interest_from_qtp_cents",
    "elects_lump_sum_benefits",
    "only_business_is_trading_securities",
    # the joint return's filing-requirement pair — the couple's own answers.
    "couple_required_to_file", "couple_files_only_for_refund",
    # Form 8880's questions — the filer's own answers, on no document.
    "roth_ira_and_able_contributions_cents", "roth_ira_contributions_cents", "is_student",
    "received_retirement_distributions_2023_2024", "retirement_distributions_2023_cents",
    "retirement_distributions_2024_cents", "received_retirement_distributions_after_year_end",
    "retirement_distributions_after_year_end_cents", "filed_jointly_2023", "filed_jointly_2024",
    "box12_g_governmental_plan",
    "box2_is_tax_exempt",                     # Form 1099-OID: the payer prints no such box
    # Form 8889 Part I's questions — the filer's own answers, on no document.
    "hsa_medicare", "hsa_hdhp_coverage", "hsa_hdhp_type", "hsa_other_coverage",
    "hsa_funding_distribution", "hsa_prior_funding_distribution_election",
    "qualified_hsa_funding_distribution_cents",
    "qualified_charitable_distribution_cents", "qcd_to_split_interest_entity",
    "qcd_prior_deducted_ira_contributions_cents",
    "rolled_over_cents", "ira_one_rollover_per_year",
    "reached_minimum_retirement_age", "public_safety_officer", "pso_premiums_paid_by_plan", "pso_premiums_cents",
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
    "box1_is_death_benefit_under_contract", "acquired_in_reportable_policy_sale",        # (box 13
    "acquired_for_valuable_consideration", "transfer_has_carryover_basis",               # is on the form)
    "transfer_to_insured_or_related_party", "death_benefit_basis_cents",
    "hsa_funding_distribution_transfer_month",
    *[f"hsa_coverage_{m}" for m in ("jan", "feb", "mar", "apr", "may", "jun",
                                    "jul", "aug", "sep", "oct", "nov", "dec")],
    "hsa_testing_period_first_ineligible_month",
    "hsa_medicare_first_month",
    "hsa_spouse_contributed", "hsa_marital_status_changed",
    "hsa_marital_change_affects_limit", "hsa_excess_in_w2_wages",
    # the combat pay elections — the filer's own choice, on no document.
    "combat_pay_election", "cdcc_combat_pay_election", "dependent_care_benefits_combat_pay_election",
    # the lived-together chain — the filer's own household, on no document.
    "lived_with_spouse_all_year", "months_lived_with_spouse",
    "separation_agreement_on_last_day", "lived_apart_last_six_months",
    # the separate-return spouse chain — the filer's own knowledge of the spouse.
    "spouse_files_return", "spouse_had_gross_income", "spouse_can_be_claimed",
    "spouse_65_or_older", "spouse_is_blind",
    "spouse_covered_by_employer_plan",
    *[f"spouse_hsa_coverage_{m}" for m in ("jan", "feb", "mar", "apr", "may", "jun",
                                           "jul", "aug", "sep", "oct", "nov", "dec")],
    # The dependent qualifiers: household facts no tax document states.
    "months_in_home", "is_married", "provided_own_support", "gross_income_under_limit",
    "filer_provided_over_half_support", "could_be_qualifying_child_of_another",
    "has_other_biological_or_adoptive_parent",
    # the split gate's custody questions — the filer's own knowledge of the household.
    "child_residence_state", "child_emancipated", "child_emancipated_after_july_2",
    # the member-of-household questions — the filer's own knowledge of the household.
    "was_spouse_during_year", "relationship_violates_local_law",
    # the joint-return test — the filer's own knowledge of a married dependent's return.
    "files_joint_return_with_spouse", "required_to_file_with_spouse",
    "joint_return_only_for_refund",
    # the benefit-split gate — the filer's own knowledge of the household, on no document.
    "parents_situation", "child_in_parents_custody",
    "child_lived_with_parents_over_half_year", "parents_provided_over_half_support",
    "written_declaration",
    # the non-parental arm's first question — the filer's own knowledge of the household.
    "child_parents_living",
    # the custodial-parent questions — the filer's own knowledge, on no document.
    "nights_with_filer_vs_other_parent", "filer_agi_higher_than_other_parent",
    # the non-parental split's links.
    "parents_meet_divorced_or_separated_rule", "a_parent_signed_declaration_not_to_claim",
    "custodial_parent_claims_child_as_qualifying_person", "filer_agi_higher_than_custodial_parent",
    # The hoh/qss asks (and, since the upkeep question on a single return's qualifying
    # rows): the filer's own household and history.
    "filer_paid_most_of_home_upkeep", "spouse_death_year",
    "could_have_filed_jointly_year_of_death",
})

# Fields a document DOES state, which we still have to ask for — because identity is removed from
# every document before it is read. Saying so matters: told only that it "was not read", a person
# goes looking for a W-2 that does, in fact, name them.
REMOVED_BEFORE_READING = frozenset({"person"})


class Question:
    """One thing to ask, with everything needed to ask it well."""

    __slots__ = ("fact", "field", "ask", "why", "consumed_by", "on_document", "choices",
                 "optional")

    def __init__(self, fact: str, field: str, ask: str, why: str,
                 consumed_by: list, on_document: bool, choices: list | None = None,
                 optional: bool = False):
        self.fact = fact                  # the path an answer is written back to
        self.field = field                # the bare field name
        self.ask = ask                    # what a person reads
        self.why = why                    # what it changes, in their terms
        self.consumed_by = consumed_by    # [form, line] pairs, for showing the effect
        self.on_document = on_document    # was this something a document should have said?
        self.choices = choices            # the accepted codes, in order, or None for a free field
        self.optional = optional          # an invitation, not a blocker: blank has a stated default

    def __repr__(self) -> str:            # pragma: no cover - debugging aid
        return f"Question({self.fact!r})"

    def as_dict(self) -> dict:
        return {"fact": self.fact, "ask": self.ask, "why": self.why,
                "consumed_by": self.consumed_by, "on_document": self.on_document,
                "choices": self.choices, "optional": self.optional}


def _why(field: str, lines: list) -> str:
    where = (f"It is used to compute Form 1040 line(s) {', '.join(lines)}."
             if lines else "It is needed to build the return.")
    if field in NOT_ON_ANY_DOCUMENT:
        return ("No tax document states this, so it has to be asked. " + where)
    if field in REMOVED_BEFORE_READING:
        return ("Your document does name this, but names and taxpayer IDs are removed from every "
                "document before it is read — so it has to be asked instead. " + where)
    return ("This should be on one of your documents; it was not read from any of them. " + where)


def open_questions(case: dict) -> list:
    """What still has to be asked, after the documents have been read.

    One question per missing required fact, in the order the service reports them, each naming the
    lines it moves. Returns an empty list when the documents answered everything.
    """
    facts = {k: v for k, v in case.items() if k != "tax_year"}
    questions = []
    for gap in gaps_for(facts):
        field = gap["fact"].rsplit(".", 1)[-1]
        group = gap["fact"].split("[", 1)[0]      # `schedule_c[0].person` -> `schedule_c`
        lines = [line for _form, line in gap["consumed_by"]]
        questions.append(Question(
            fact=gap["fact"],
            field=field,
            ask=GROUP_PROMPTS.get((group, field)) or PROMPTS.get(field, f"What is {field}?"),
            why=_why(field, lines),
            consumed_by=gap["consumed_by"],
            on_document=field not in NOT_ON_ANY_DOCUMENT and field not in REMOVED_BEFORE_READING,
            choices=choices_for(field),
        ))

    # the OPTIONAL asks, after everything blocking (cheap gate before expensive entry).
    # Role-conditioned, derived from the same absence rule: an optional input
    # that moves a served line and was not supplied is worth ASKING before the first run, not only
    # asserting about after one. Today that is `birth_month` on every person row. The dependent
    # qualifiers are deliberately NOT here while the mapper refuses dependents outright — an ask
    # whose every answer ends in a refusal is noise — and the lock in tests/test_interview.py
    # inverts the day that coverage lands.
    month_lines = consumed_by("persons[].birth_month")
    for i, person in enumerate(facts.get("persons") or []):
        if isinstance(person, dict) and person and "birth_month" not in person:
            questions.append(Question(
                fact=f"persons[{i}].birth_month",
                field="birth_month",
                ask=PROMPTS["birth_month"],
                why=("If you leave this blank, January is used — which decides whether the "
                     "age-65 additional standard deduction applies. "
                     + (f"It is used to compute Form 1040 line(s) {', '.join(month_lines)}."
                        if month_lines else "")).strip(),
                consumed_by=[[F1040, line_id] for line_id in month_lines],
                on_document=False,
                choices=choices_for("birth_month"),
                optional=True,
            ))
    # the HSAs' December 31 value — optional on a filer row with HSA activity. The engine
    # decides whether an excess exists, so it is never a gap and never pre-filled (a 0 would zero
    # every filer's excise — the register's own warning); left blank where line 48 has an excess,
    # the return is the dictionary's own knockout, and the invitation says so.
    from ..facts import mapper as _mapper
    value_lines = consumed_by("persons[].hsa_december_31_value_cents")
    for i, person in enumerate(facts.get("persons") or []):
        if (isinstance(person, dict) and person and "hsa_december_31_value_cents" not in person
                and _mapper.hsa_december_value_asked(facts, i)):
            questions.append(Question(
                fact=f"persons[{i}].hsa_december_31_value_cents",
                field="hsa_december_31_value_cents",
                ask=PROMPTS["hsa_december_31_value_cents"],
                why=("Needed where Form 5329 line 48 shows an excess HSA contribution: line 49 "
                     "is 6% of the smaller of the excess and this value, and a return with an "
                     "excess is not figured without it. "
                     + (f"It is used to compute Form 1040 line(s) {', '.join(value_lines)}."
                        if value_lines else "")).strip(),
                consumed_by=[[F1040, line_id] for line_id in value_lines],
                on_document=False,
                choices=choices_for("hsa_december_31_value_cents"),
                optional=True,
            ))
    # the carry-in from 2024 — the same population; left blank, no carry-in is stated for the row.
    carry_lines = consumed_by("persons[].hsa_prior_year_excess_cents")
    for i, person in enumerate(facts.get("persons") or []):
        if (isinstance(person, dict) and person and "hsa_prior_year_excess_cents" not in person
                and _mapper.hsa_prior_excess_asked(facts, i)):
            questions.append(Question(
                fact=f"persons[{i}].hsa_prior_year_excess_cents",
                field="hsa_prior_year_excess_cents",
                ask=PROMPTS["hsa_prior_year_excess_cents"],
                why=("If you leave this blank, no excess is carried in from 2024 — a carry-in joins "
                     "Form 5329 line 48 for the 6% after the room under Form 8889 line 12 absorbs "
                     "it. "
                     + (f"It is used to compute Form 1040 line(s) {', '.join(carry_lines)}."
                        if carry_lines else "")).strip(),
                consumed_by=[[F1040, line_id] for line_id in carry_lines],
                on_document=False,
                choices=choices_for("hsa_prior_year_excess_cents"),
                optional=True,
            ))
    # Form 2441 Worksheet A's root — invited on a return that files Form 2441; blank is the
    # no the statement says, and a yes opens the 2024 figures the worksheet reads.
    wa_lines = consumed_by("paid_prior_year_care_expenses_this_year")
    if "paid_prior_year_care_expenses_this_year" not in facts and _mapper.worksheet_a_root_reached(facts):
        questions.append(Question(
            fact="paid_prior_year_care_expenses_this_year",
            field="paid_prior_year_care_expenses_this_year",
            ask=PROMPTS["paid_prior_year_care_expenses_this_year"],
            why=("If you leave this blank, no 2024 care expenses are treated as paid in 2025 and "
                 "Form 2441's Worksheet A credit is 0. "
                 + (f"It is used to compute Form 1040 line(s) {', '.join(wa_lines)}."
                    if wa_lines else "")).strip(),
            consumed_by=[[F1040, line_id] for line_id in wa_lines],
            on_document=False,
            choices=choices_for("paid_prior_year_care_expenses_this_year"),
            optional=True,
        ))
    # retired: the section 1341 credit is no longer invited — the
    # dictionary reads the old figure nowhere, and an amount above 0 is refused by name in the mapper.
    # the royalty activity's oil/gas/geothermal classification — invited once the return
    # claims royalty income (any misc1099s[].royalties_cents above 0); blank claims no percentage
    # depletion, the dictionary's own conservative default.
    oilgas_lines = consumed_by(_mapper.ROYALTY_OIL_GAS_FIELD)
    if (_mapper.ROYALTY_OIL_GAS_FIELD not in facts
            and _mapper.royalty_expenses_reached(facts)):
        questions.append(Question(
            fact=_mapper.ROYALTY_OIL_GAS_FIELD,
            field=_mapper.ROYALTY_OIL_GAS_FIELD,
            ask=PROMPTS[_mapper.ROYALTY_OIL_GAS_FIELD],
            why=("If you leave this blank, no percentage depletion is taken against the royalty "
                 "income — the property is treated as not oil, gas, or geothermal. "
                 + (f"It is used to compute Form 1040 line(s) {', '.join(oilgas_lines)}."
                    if oilgas_lines else "")).strip(),
            consumed_by=[[F1040, line_id] for line_id in oilgas_lines],
            on_document=False,
            choices=choices_for(_mapper.ROYALTY_OIL_GAS_FIELD),
            optional=True,
        ))
    # alimony received/paid — invited on EVERY return, never a gap: most returns have
    # neither, and a blank is the "none" `gaps._ABSENT_MEANS` states. Answering an amount reaches
    # its own pre-2019-agreement gate, asked separately (the required-gap loop above) once it is
    # supplied.
    alimony_received_lines = consumed_by("alimony_received_cents")
    if "alimony_received_cents" not in facts:
        questions.append(Question(
            fact="alimony_received_cents",
            field="alimony_received_cents",
            ask=PROMPTS["alimony_received_cents"],
            why=("If you leave this blank, no alimony is treated as received and Schedule 1, "
                 "line 2a is 0. "
                 + (f"It is used to compute Form 1040 line(s) {', '.join(alimony_received_lines)}."
                    if alimony_received_lines else "")).strip(),
            consumed_by=[[F1040, line_id] for line_id in alimony_received_lines],
            on_document=False,
            choices=choices_for("alimony_received_cents"),
            optional=True,
        ))
    alimony_paid_lines = consumed_by("alimony_paid_cents")
    if "alimony_paid_cents" not in facts:
        questions.append(Question(
            fact="alimony_paid_cents",
            field="alimony_paid_cents",
            ask=PROMPTS["alimony_paid_cents"],
            why=("If you leave this blank, no alimony is treated as paid and Schedule 1, line "
                 "19a is 0. "
                 + (f"It is used to compute Form 1040 line(s) {', '.join(alimony_paid_lines)}."
                    if alimony_paid_lines else "")).strip(),
            consumed_by=[[F1040, line_id] for line_id in alimony_paid_lines],
            on_document=False,
            choices=choices_for("alimony_paid_cents"),
            optional=True,
        ))
    # the itemized Schedule E expense lines and the depreciation inputs, invited per
    # rental property — the same posture (an optional input that moves a served line is
    # worth asking, not only asserting about after the fact). MUTUALLY EXCLUSIVE with
    # `total_expenses_cents`: a property that already answered the lump shape does not open
    # these (the mapper backstop refuses the mix), and none of the four opens the OTHER shape
    # either — this unit adds no invitation for `total_expenses_cents` itself, which stays
    # exactly as un-invited as it was before (a caller may still supply it directly).
    _RENTAL_EXPENSE_INVITES = (
        ("insurance_cents", "line 9 insurance"),
        ("management_fees_cents", "line 11 management fees"),
        ("repairs_cents", "line 14 repairs"),
        ("taxes_cents", "line 16 taxes"),
    )
    for i, item in enumerate(facts.get("rentals") or []):
        if not isinstance(item, dict) or not item or "total_expenses_cents" in item:
            continue
        for field, printed in _RENTAL_EXPENSE_INVITES:
            if field in item:
                continue
            field_lines = consumed_by(f"rentals[].{field}")
            questions.append(Question(
                fact=f"rentals[{i}].{field}",
                field=field,
                ask=PROMPTS[field],
                why=(f"If you leave this blank, {printed} prints zero. "
                     + (f"It is used to compute Form 1040 line(s) {', '.join(field_lines)}."
                        if field_lines else "")).strip(),
                consumed_by=[[F1040, line_id] for line_id in field_lines],
                on_document=False,
                choices=choices_for(field),
                optional=True,
            ))
        # The depreciation inputs — the engine computes the deduction from these, never this
        # service. `placed_in_service_in_current_year` opens only once a building basis is
        # entered (the mapper refuses it otherwise): asking it before then would risk a
        # taxpayer answering a question about a building that was never claimed.
        if "building_basis_cents" not in item:
            basis_lines = consumed_by("rentals[].building_basis_cents")
            questions.append(Question(
                fact=f"rentals[{i}].building_basis_cents",
                field="building_basis_cents",
                ask=PROMPTS["building_basis_cents"],
                why=("If you leave this blank, no building depreciation is claimed for this "
                     "property (Schedule E line 18). "
                     + (f"It is used to compute Form 1040 line(s) {', '.join(basis_lines)}."
                        if basis_lines else "")).strip(),
                consumed_by=[[F1040, line_id] for line_id in basis_lines],
                on_document=False,
                choices=choices_for("building_basis_cents"),
                optional=True,
            ))
        elif "placed_in_service_in_current_year" not in item:
            pis_lines = consumed_by("rentals[].placed_in_service_in_current_year")
            questions.append(Question(
                fact=f"rentals[{i}].placed_in_service_in_current_year",
                field="placed_in_service_in_current_year",
                ask=PROMPTS["placed_in_service_in_current_year"],
                why=("If you leave this blank, the building is treated as placed in service "
                     "in a prior year (a full straight-line recovery year). "
                     + (f"It is used to compute Form 1040 line(s) {', '.join(pis_lines)}."
                        if pis_lines else "")).strip(),
                consumed_by=[[F1040, line_id] for line_id in pis_lines],
                on_document=False,
                choices=choices_for("placed_in_service_in_current_year"),
                optional=True,
            ))
        if "has_five_year_property" not in item:
            five_lines = consumed_by("rentals[].has_five_year_property")
            questions.append(Question(
                fact=f"rentals[{i}].has_five_year_property",
                field="has_five_year_property",
                ask=PROMPTS["has_five_year_property"],
                why=("If you leave this blank, no 5-year MACRS personal property is claimed "
                     "for this property. "
                     + (f"It is used to compute Form 1040 line(s) {', '.join(five_lines)}."
                        if five_lines else "")).strip(),
                consumed_by=[[F1040, line_id] for line_id in five_lines],
                on_document=False,
                choices=choices_for("has_five_year_property"),
                optional=True,
            ))
    # alimony received/paid — invited on EVERY return, never a gap: most returns have
    # neither, and a blank is the "none" `gaps._ABSENT_MEANS` states. Answering an amount reaches
    # its own pre-2019-agreement gate, asked separately (the required-gap loop above) once it is
    # supplied.
    alimony_received_lines = consumed_by("alimony_received_cents")
    if "alimony_received_cents" not in facts:
        questions.append(Question(
            fact="alimony_received_cents",
            field="alimony_received_cents",
            ask=PROMPTS["alimony_received_cents"],
            why=("If you leave this blank, no alimony is treated as received and Schedule 1, "
                 "line 2a is 0. "
                 + (f"It is used to compute Form 1040 line(s) {', '.join(alimony_received_lines)}."
                    if alimony_received_lines else "")).strip(),
            consumed_by=[[F1040, line_id] for line_id in alimony_received_lines],
            on_document=False,
            choices=choices_for("alimony_received_cents"),
            optional=True,
        ))
    alimony_paid_lines = consumed_by("alimony_paid_cents")
    if "alimony_paid_cents" not in facts:
        questions.append(Question(
            fact="alimony_paid_cents",
            field="alimony_paid_cents",
            ask=PROMPTS["alimony_paid_cents"],
            why=("If you leave this blank, no alimony is treated as paid and Schedule 1, line "
                 "19a is 0. "
                 + (f"It is used to compute Form 1040 line(s) {', '.join(alimony_paid_lines)}."
                    if alimony_paid_lines else "")).strip(),
            consumed_by=[[F1040, line_id] for line_id in alimony_paid_lines],
            on_document=False,
            choices=choices_for("alimony_paid_cents"),
            optional=True,
        ))
    # the Form 1040 page-1 main-home checkbox — invited on EVERY return, never a gap: the
    # checkbox is printed unconditionally, and a blank is the engine's own favorable "in the
    # U.S." default (Publication 596 Rule 14).
    main_home_lines = consumed_by("main_home_in_us_over_half_year")
    if "main_home_in_us_over_half_year" not in facts:
        questions.append(Question(
            fact="main_home_in_us_over_half_year",
            field="main_home_in_us_over_half_year",
            ask=PROMPTS["main_home_in_us_over_half_year"],
            why=("If you leave this blank, your main home is treated as in the U.S. for more "
                 "than half of 2025. "
                 + (f"It is used to compute Form 1040 line(s) {', '.join(main_home_lines)}."
                    if main_home_lines else "")).strip(),
            consumed_by=[[F1040, line_id] for line_id in main_home_lines],
            on_document=False,
            choices=choices_for("main_home_in_us_over_half_year"),
            optional=True,
        ))
    # box 13 on a code 4 family Form 1099-R — invited, not required: an ordinary distribution to
    # a beneficiary leaves it blank and is taxed as box 2a reports; a date opens the death-benefit
    # questions. (On a code C form it is a required gap, asked above.)
    date_lines = consumed_by("r1099s[].date_of_payment")
    for i, item in enumerate(facts.get("r1099s") or []):
        if (isinstance(item, dict) and item and "date_of_payment" not in item
                and _mapper.death_benefit_date_invited(facts, i)):
            questions.append(Question(
                fact=f"r1099s[{i}].date_of_payment",
                field="date_of_payment",
                ask=PROMPTS["date_of_payment"],
                why=("If you leave this blank, box 13 is taken as blank and this distribution is taxed "
                     "as box 2a reports; a date opens the questions that price a death benefit under a "
                     "life insurance contract (IRC 101). "
                     + (f"It is used to compute Form 1040 line(s) {', '.join(date_lines)}."
                        if date_lines else "")).strip(),
                consumed_by=[[F1040, line_id] for line_id in date_lines],
                on_document=True,
                choices=None,
                optional=True,
            ))
    # care expenses on a Form 2441 qualifying person's row — optional, stated as 0 when
    # left blank (`gaps.py::_ABSENT_MEANS`; the mapper never refuses an absent amount by itself).
    # Invited the same way the optional HSA figures are, on the same gate the
    # required `unable_to_care_for_self` gap uses (`mapper.care_expense_question_reached`), so the
    # conversation gets a chance to state the real figure instead of silently defaulting to it.
    care_lines = consumed_by("persons[].care_expenses_cents")
    for i, person in enumerate(facts.get("persons") or []):
        if (isinstance(person, dict) and person
                and _mapper.CARE_EXPENSES_FIELD not in person
                and _mapper.care_expense_question_reached(facts, i)):
            questions.append(Question(
                fact=f"persons[{i}].{_mapper.CARE_EXPENSES_FIELD}",
                field=_mapper.CARE_EXPENSES_FIELD,
                ask=PROMPTS[_mapper.CARE_EXPENSES_FIELD],
                why=("If you leave this blank, no child or dependent care expenses are counted "
                     "for this qualifying person. "
                     + (f"It is used to compute Form 1040 line(s) {', '.join(care_lines)}."
                        if care_lines else "")).strip(),
                consumed_by=[[F1040, line_id] for line_id in care_lines],
                on_document=False,
                choices=choices_for(_mapper.CARE_EXPENSES_FIELD),
                optional=True,
            ))
    # the after-year-end own-HSA-contribution amount — optional, stated as 0 when left
    # blank (`_require_hsa_own_answers` skips it by name). Invited once a filer row answered yes
    # to contributing themselves (`mapper.hsa_own_questions_reached`), the same population the
    # required amount (`hsa_own_contributions_cents`) is asked of.
    hsa_after_lines = consumed_by(f"persons[].{_mapper.HSA_OWN_AFTER_FIELD}")
    for i, person in enumerate(facts.get("persons") or []):
        if (isinstance(person, dict) and person
                and _mapper.HSA_OWN_AFTER_FIELD not in person
                and _mapper.HSA_OWN_AFTER_FIELD in _mapper.hsa_own_questions_reached(person)):
            questions.append(Question(
                fact=f"persons[{i}].{_mapper.HSA_OWN_AFTER_FIELD}",
                field=_mapper.HSA_OWN_AFTER_FIELD,
                ask=PROMPTS[_mapper.HSA_OWN_AFTER_FIELD],
                why=("If you leave this blank, none of this person's own HSA contributions are "
                     "treated as made after December 31, 2025 and before the filing deadline. "
                     + (f"It is used to compute Form 1040 line(s) {', '.join(hsa_after_lines)}."
                        if hsa_after_lines else "")).strip(),
                consumed_by=[[F1040, line_id] for line_id in hsa_after_lines],
                on_document=False,
                choices=choices_for(_mapper.HSA_OWN_AFTER_FIELD),
                optional=True,
            ))
    return questions


def completeness_prompt(unasked_boundary: list) -> str | None:
    """The question nobody asks, and the one most likely to make a return wrong.

    Everything above is about facts we know are missing. This is about income this service cannot
    ask for at all: it never requests interest, dividends or retirement distributions, so a folder
    containing them yields a wages-only return that no gap and no refusal will flag. A `complete`
    answer that is silent about that is worse than a refusal, so the person is told plainly and in
    their own terms.
    """
    if not unasked_boundary:
        return None
    classes = [entry["fact_class"] for entry in unasked_boundary]
    return ("Before this return is used: this service does not handle "
            + "; ".join(classes)
            + ". If you had any of these, the figures here are not your return.")
