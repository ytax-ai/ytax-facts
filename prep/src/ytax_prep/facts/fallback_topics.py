# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The fallback's ALLOW-LIST: the engine inputs a person may type that no service
field reaches, topic by topic. Data, reviewed by a person — never derived at run time.

WHY A LIST AND NOT A RULE. The design offered "every writable in an uncovered module, minus
identifiers". Measured through the whole service (`tmp/logs/fallback-through-service.md`,
2026-09-17) that rule served a wrong return as `complete` three times in thirteen, and its
identifier pattern passed a street address (`/casualtyEvents/*/description`). And the dictionary
states limits in PROSE that no rule can read: `/writableMortgageInterest` says "the $750,000
acquisition-debt limit is attested by the filer, not modeled" — typed blindly, a return outside
that limit is served complete and wrong. So a writable is offered only when a person has read its
dictionary entry and written, here, the words it is asked in and what typing it asserts.

SHAPE. One entry per topic:
  label     what a person recognises, in the checklist ("Did any of these apply to you in 2025?")
  form      the form the answers land on
  status    "offered" — asked on the page; "held" — known, measured, NOT asked, with the reason
  gate      the ONE fact the service would otherwise own that ticking the topic may set, and only
            to true (the measurement's finding 4: without `/hasItemizedDeductions` the typed
            amounts sit in the graph and move nothing); None when the module needs none
  writables path -> {kind, ask, line[, min, max]}; `kind` and the bounds must equal the pinned
            dictionary's `<Writable>` kind and `<Limit>`s (a Dollar or Int is at least 0 unless said)

Every path is a ROOT writable: no collection member, nothing the mapper emits or classifies. The
lock is `tests/test_fallback_extras.py`, which reads the pinned dictionary.

Copy: the form's printed caption and its line, one ask, no advice (the writing-taxpayer-facing-copy
skill). The dictionary's `<Name>` is developer text and is never shown.
"""
from __future__ import annotations

DOLLAR, BOOLEAN, INT = "Dollar", "Boolean", "Int"
OFFERED, HELD = "offered", "held"

# Form 5695's business-use question, one answer for the return, asked by both parts of the form —
# so it is an ATTESTATION of each topic (a writable may sit in one topic only), and the one
# attestation whose answer the engine itself reads: `sends` names the dictionary writable the
# attested answer is sent on. The pinned dictionary holds every Form 5695 cost until it is
# answered (section 25D(e)(7) and section 25C(f)(1) count only the nonbusiness part of an item used
# less than 80% for nonbusiness purposes; measured at the alpha-1 pin: 14,820.00 of solar costs
# alone left line 24 unresolved, and with No, 4,115.00 -> 0.00). A yes asks each item's
# nonbusiness-use percentage, which this list does not offer, so a yes is refused in its own words.
FORM_5695_BUSINESS_USE = {
    "ask": "Is any of this property used partly for business, such as a home office or a rented "
           "part of the home, so that less than 80% of its use is for nonbusiness purposes?",
    "rule": "Form 5695 counts only the nonbusiness share of an item used less than 80% for "
            "nonbusiness purposes (Form 5695 instructions); the share is figured item by item.",
    "must_be": False,
    "refusal": "Property used less than 80% for nonbusiness purposes counts only its nonbusiness "
               "share on Form 5695, and that share is not asked in this version. Refused rather "
               "than computed on the whole cost. The figures here are not your return.",
    "sends": "/writableForm5695AnyItemUnder80PercentNonbusinessUse",
}

TOPICS: dict = {
    "lifetime_learning_credit": {
        "label": "Tuition or other education expenses for the lifetime learning credit",
        "form": "Form 8863",
        "status": OFFERED,
        "gate": None,
        "writables": {
            "/writableLlcQualifiedExpenses": {
                "kind": DOLLAR, "line": "Form 8863, line 10",
                "ask": "Adjusted qualified education expenses for the lifetime learning credit, "
                       "all students together — Form 8863, line 10."},
            # the alpha-1 pin: section 25A(g)(8) allows the credit only when the student received
            # Form 1098-T, or one of the Secretary's exceptions applies, and the pinned dictionary
            # holds line 24 until line 22a(2) is answered (measured: unanswered, line 24 resolves
            # only as a stand-in; yes, 4,115.00 -> 2,431.00 on 8,420.00). The exceptions are not
            # asked here, so a no is refused in its own words.
            "/writableForm8863FirstInstitutionCurrentYear1098T": {
                "kind": BOOLEAN, "line": "Form 8863, line 22a(2)",
                "ask": "Did the student receive Form 1098-T from the school for 2025? — Form "
                       "8863, line 22a(2).",
                "must_be": True,
                "refusal": "Without a 2025 Form 1098-T from the school, the lifetime learning "
                           "credit is allowed only under an exception this version does not ask. "
                           "Refused rather than computed without it. The figures here are not "
                           "your return."},
        },
        # Form 8863 Part III's student name and TIN must be PRESENT before the engine
        # grants the credit (measured: without them line 24 stays uncredited and resolves only as a
        # Placeholder; with them 4,115.00 -> 2,431.00 on 8,420.00 of expenses). They are identity —
        # this service never holds a name or a TIN — so they are synthesized, the mapper's own
        # posture for a payer's name, and move no figure.
        "companions": {
            "/writableAotcStudentName": ("string", "Synthetic Student"),
            "/writableAotcStudentTin": ("tin", ("899", "00", "0099")),
        },
    },
    "residential_clean_energy": {
        "label": "Solar electric property installed at a home",
        "form": "Form 5695",
        "status": OFFERED,
        "gate": None,
        "attestations": {"business_use": FORM_5695_BUSINESS_USE},
        "writables": {
            "/writableSolarElectricCosts": {
                "kind": DOLLAR, "line": "Form 5695, line 1",
                "ask": "Qualified solar electric property costs — Form 5695, line 1."},
        },
    },
    "energy_efficient_home_improvement": {
        "label": "Insulation or air sealing added to your main home",
        "form": "Form 5695",
        "status": OFFERED,
        "gate": None,
        "attestations": {"business_use": FORM_5695_BUSINESS_USE},
        "writables": {
            "/writableEeImprovementsInMainHome": {
                "kind": BOOLEAN, "line": "Form 5695, line 17a",
                "ask": "Were the qualified energy efficiency improvements installed in or on your "
                       "main home located in the United States? — Form 5695, line 17a."},
            "/writableEeImprovementsOriginalUser": {
                "kind": BOOLEAN, "line": "Form 5695, line 17b",
                "ask": "Are you the original user of the qualified energy efficiency "
                       "improvements? — Form 5695, line 17b."},
            "/writableEeImprovementsExpected5Years": {
                "kind": BOOLEAN, "line": "Form 5695, line 17c",
                "ask": "Are the components reasonably expected to remain in use for at least 5 "
                       "years? — Form 5695, line 17c."},
            "/writableEeImprovementsConstructionRelated": {
                "kind": BOOLEAN, "line": "Form 5695, line 17e",
                "ask": "Are any of the improvements related to the construction of this main "
                       "home? — Form 5695, line 17e."},
            "/writableInsulationCosts": {
                "kind": DOLLAR, "line": "Form 5695, line 18a",
                "ask": "Insulation material or system, or air sealing material or system, "
                       "costs — Form 5695, line 18a."},
        },
    },
    "mortgage_interest_credit": {
        "label": "A Mortgage Credit Certificate from a state or local government",
        "form": "Form 8396",
        "status": OFFERED,
        "gate": None,
        "writables": {
            "/writableMortgageInterestOnCertifiedIndebtedness": {
                "kind": DOLLAR, "line": "Form 8396, line 1",
                "ask": "Interest paid on the certified indebtedness amount shown on the "
                       "certificate — Form 8396, line 1."},
            "/writableMccCreditRatePercent": {
                "kind": INT, "line": "Form 8396, line 2", "min": 10, "max": 50,
                "ask": "The certificate credit rate shown on the certificate, as a whole "
                       "percent — Form 8396, line 2."},
        },
    },
    # Board decision 8's group B: the two Schedule C methods whose inputs sit on the BUSINESS, not
    # the return (rule 6 — `/scheduleCs/[0]/…`). MEASURED on the pinned engine on the showcase profiles
    # that carry them: with these lines typed, `profile-home-office-regular` and
    # `profile-schedule-c-vehicle` land on EVERY served line of their own oracle.
    "home_office_regular": {
        "label": "A home office, by the regular method",
        "form": "Form 8829",
        "status": OFFERED,
        "gate": None,
        "member_group": "/scheduleCs",     # the engine collection a line is typed against
        "member_rows": "schedule_c",       # …and the fact-set group whose rows it attaches to
        "attestations": {
            "not_already_in_total_expenses": {
                "ask": "Are these home costs left OUT of the total expenses you gave for this "
                       "business?",
                "rule": "Form 8829 works out the business part of your home costs and it lands on "
                        "Schedule C, line 30 — a separate line from the total expenses on line 28. "
                        "A cost entered in both places is deducted twice.",
                "must_be": True,
                "refusal": "Home costs already inside the total expenses for this business would "
                           "be deducted twice — once on Schedule C, line 28 and again on line 30. "
                           "Refused rather than counted twice. Take them out of the total, or "
                           "leave this form off.",
            },
        },
        "writables": {
            "/scheduleCs/*/electsRegularHomeOfficeMethod": {
                "kind": BOOLEAN, "line": "Form 8829, the regular method",
                "ask": "Are you working out this home office by the regular method — your actual "
                       "home costs — rather than the simplified square-foot rate? Form 8829, the "
                       "regular method.",
                "must_be": True,
                "refusal": "The simplified square-foot rate is not the method this version "
                           "computes from typed lines. Refused rather than computed by a method "
                           "these figures are not for.",
            },
            "/scheduleCs/*/writableForm8829DirectExpenses": {
                "kind": DOLLAR, "line": "Form 8829, Part II, column (a)",
                "ask": "Costs for the business part of your home only — Form 8829, Part II, column "
                       "(a). Enter 0 if none."},
            "/scheduleCs/*/writableForm8829IndirectExpenses": {
                "kind": DOLLAR, "line": "Form 8829, Part II, column (b)",
                "ask": "Costs for your whole home — insurance, rent, repairs and maintenance, "
                       "utilities — Form 8829, Part II, column (b). Enter the whole amount, not "
                       "the business share; enter 0 if none."},
            "/scheduleCs/*/writableForm8829HomeDepreciation": {
                "kind": DOLLAR, "line": "Form 8829, Part III, line 42",
                "ask": "Depreciation for the business part of your home — Form 8829, Part III, "
                       "line 42. Enter 0 if none."},
            "/scheduleCs/*/writableHomeOfficeBusinessArea": {
                "kind": INT, "line": "Form 8829, line 1",
                "ask": "Area used regularly and only for this business, in square feet — Form "
                       "8829, line 1."},
            "/scheduleCs/*/writableHomeOfficeTotalArea": {
                "kind": INT, "line": "Form 8829, line 2",
                "ask": "Total area of your home, in square feet — Form 8829, line 2."},
        },
    },
    "actual_vehicle_expenses": {
        "label": "A vehicle used for a business, by its actual costs",
        "form": "Schedule C, line 9",
        "status": OFFERED,
        "gate": None,
        "member_group": "/scheduleCs",     # the engine collection a line is typed against
        "member_rows": "schedule_c",       # …and the fact-set group whose rows it attaches to
        "attestations": {
            "not_already_in_total_expenses": {
                "ask": "Are these vehicle costs left OUT of the total expenses you gave for this "
                       "business?",
                "rule": "Car and truck expenses land on Schedule C, line 9. The instructions say "
                        "the other way to claim a vehicle is to include its actual expenses in the "
                        "total expenses instead, so a cost entered in both places is deducted "
                        "twice.",
                "must_be": True,
                "refusal": "Vehicle costs already inside the total expenses for this business "
                           "would be deducted twice — once there and again on Schedule C, line 9. "
                           "Refused rather than counted twice. Take them out of the total, or "
                           "leave this form off.",
            },
        },
        "writables": {
            "/scheduleCs/*/electsActualVehicleExpense": {
                "kind": BOOLEAN, "line": "Schedule C, line 9, the actual-expense method",
                "ask": "Are you deducting what this vehicle actually cost to run, rather than the "
                       "standard mileage rate? Schedule C, line 9, the actual-expense method.",
                "must_be": True,
                "refusal": "The standard mileage rate can be taken only by someone who owned the "
                           "vehicle and used that rate from its first business year, or leases it "
                           "and uses that rate for the whole lease — a test this version does not "
                           "carry. Refused rather than computed without it.",
            },
            "/scheduleCs/*/writableActualVehicleOperatingCosts": {
                "kind": DOLLAR, "line": "Schedule C, line 9, actual operating costs",
                "ask": "What this vehicle cost to run for the whole year — Schedule C, line 9, "
                       "actual operating costs. Enter the whole amount, not the business share."},
            "/scheduleCs/*/writableBusinessMilesDriven": {
                "kind": INT, "line": "Schedule C, Part IV, line 44a",
                "ask": "Miles driven for this business — Schedule C, Part IV, line 44a."},
            "/scheduleCs/*/writableVehicleTotalMiles": {
                "kind": INT, "line": "Schedule C, Part IV, lines 44a to 44c",
                "ask": "Miles this vehicle was driven altogether — Schedule C, Part IV, lines 44a "
                       "to 44c."},
        },
    },
    # By design, the guideline is to keep the calculation correct for this. Publication 525 says
    # it itself, and the dictionary quotes it: "Figure your tax under both methods and compare the
    # results. Use the method (deduction or credit) that results in less tax." So the ELECTION is
    # not a question here — the pinned dictionary computes the lesser of the two methods itself,
    # and the service names both figures (`operations._claim_of_right_statement`). What is
    # asked is only what nobody but the person knows: what they repaid, and the earlier year's tax
    # both ways.
    "claim_of_right_repayment": {
        "label": "Money repaid this year that was taxed in an earlier year",
        "form": "Publication 525, Repayments",
        "status": OFFERED,
        "gate": None,
        "writables": {
            "/writableOtherClaimOfRightRepaymentIncludedInEarlierYearIncome": {
                "kind": DOLLAR, "line": "Publication 525, Repayments",
                "ask": "How much did you repay in 2025 that you had included in your income in an "
                       "earlier year — repaid wages, for instance, but not unemployment "
                       "compensation or social security benefits? Publication 525, Repayments."},
            "/writablePriorYearTaxAsFiled": {
                "kind": DOLLAR, "line": "Publication 525, Repayments, Method 2, step 2",
                "ask": "What was the total tax on your return for the earlier year the repaid "
                       "amount was included in? Publication 525, Repayments, Method 2, step 2."},
            "/writablePriorYearTaxRefiguredWithoutRepaidIncome": {
                "kind": DOLLAR, "line": "Publication 525, Repayments, Method 2, step 3",
                "ask": "What would that earlier year's total tax have been without the repaid "
                       "amount in income? Publication 525, Repayments, Method 2, step 3."},
        },
    },
    "itemized_deductions": {
        "label": "Itemized deductions (Schedule A)",
        "form": "Schedule A (Form 1040)",
        "status": OFFERED,
        # HELD until 2026-09-22 (board decision 8). Three of the four reasons were STALE at
        # Read from the dictionary's own prose: the $750,000 acquisition-debt limit
        # is MODELED now, through the Pub 936 Table 1 balances below (measured: a 418,000 average
        # balance deducts the whole 18,000 of interest, a 900,000 one does not); the 60%-of-AGI
        # limit on cash gifts and the 30%-of-AGI limit on non-cash gifts are MODELED ("was
        # attested", both). What is left is SCOPE, which is what the attestations below ask, and
        # the section 63(e) election, which is the person's own choice and says what it does.
        "gate": "/hasItemizedDeductions",
        # Each a yes-or-no the person answers before the figures, with the rule beside it in the
        # dictionary's own terms. The answer that breaks it refuses — this service does not take a
        # Schedule A whose amounts it would have to compute at a limit it does not carry.
        "attestations": {
            "cash_gifts_in_scope": {
                "ask": "Were your cash and check gifts all to public charities, and all made by "
                       "you — not a share passed through to you by a partnership or S corporation?",
                "rule": "Schedule A, line 11 is cash and check gifts to public charities. A gift to "
                        "a private nonoperating foundation is held to a different limit, which this "
                        "version does not compute. A partnership's or S corporation's share, from "
                        "Schedule K-1 (Form 1065) box 13 code A or Schedule K-1 (Form 1120-S) box "
                        "12 code A, is already counted from that document.",
                "must_be": True,
                "refusal": "Cash gifts to a private nonoperating foundation, or a share passed "
                           "through from a partnership or S corporation, are not amounts this "
                           "version computes on Schedule A, line 11. Refused rather than counted at "
                           "a limit this version does not carry.",
            },
            "non_cash_gifts_in_scope": {
                "ask": "Were your gifts other than cash all property you had held more than a year, "
                       "given at its fair market value to public charities?",
                "rule": "Schedule A, line 12 as this version computes it is capital-gain property "
                        "held more than one year, given at fair market value to public charities. "
                        "Property held a year or less, the election to reduce a gift to its basis, "
                        "gifts to 30%-limit organizations and qualified conservation contributions "
                        "are each computed differently, and this version does not carry them.",
                "must_be": True,
                "refusal": "Gifts other than cash that are not capital-gain property held more than "
                           "a year, given at fair market value to a public charity, are not amounts "
                           "this version computes on Schedule A, line 12. Refused rather than "
                           "counted at a limit this version does not carry.",
            },
        },
        "writables": {
            "/writableMedicalExpenses": {"kind": DOLLAR, "line": "Schedule A, line 1",
                                         "ask": "Medical and dental expenses — Schedule A, line 1. "
                                                "Enter 0 if none."},
            "/writableStateLocalTaxes": {"kind": DOLLAR, "line": "Schedule A, line 5d",
                                         "ask": "State and local taxes — Schedule A, line 5d. "
                                                "Enter 0 if none."},
            "/writableMortgageInterest": {"kind": DOLLAR, "line": "Schedule A, line 8e",
                                          "ask": "Home mortgage interest and points — Schedule A, "
                                                 "line 8e. Enter 0 if none."},
            # Pub 936 Table 1's own three balances. MEASURED on the pinned engine: with any mortgage
            # interest the return does not resolve until the post-2017 balance is answered, and
            # the dictionary's own rule is that the two older balances are answered TOGETHER or
            # not at all ("partial older-debt answers do not fall back to the simplified
            # calculation" — and two of three stalls the return). Asked as three, each with the
            # dictionary's own "enter zero when none", so nobody can land in the partial state;
            # measured, all three at zero gives the figure the simplified path gives.
            "/writableScheduleALine8AverageAcquisitionDebtBalance": {
                "kind": DOLLAR, "line": "Publication 936, Table 1, line 7",
                "ask": "Average balance for the year of home debt taken out after December 15, "
                       "2017 to buy, build or substantially improve your home — Publication 936, "
                       "Table 1, line 7. Enter 0 if none."},
            "/writableScheduleALine8AverageGrandfatheredDebtBalance": {
                "kind": DOLLAR, "line": "Publication 936, Table 1, line 1",
                "ask": "Average balance for the year of home debt taken out on or before October "
                       "13, 1987, which Publication 936 calls grandfathered debt — Publication 936, "
                       "Table 1, line 1. Enter 0 if none."},
            "/writableScheduleALine8AveragePre2018AcquisitionDebtBalance": {
                "kind": DOLLAR, "line": "Publication 936, Table 1, line 2",
                "ask": "Average balance for the year of home debt taken out after October 13, 1987 "
                       "and before December 16, 2017 to buy, build or substantially improve your "
                       "home — Publication 936, Table 1, line 2. Enter 0 if none."},
            "/writableCharitableCash": {"kind": DOLLAR, "line": "Schedule A, line 11",
                                        "ask": "Gifts by cash or check — Schedule A, line 11. "
                                               "Enter 0 if none."},
            "/writableCharitableNonCash": {"kind": DOLLAR, "line": "Schedule A, line 12",
                                           "ask": "Gifts other than by cash or check — Schedule A, "
                                                  "line 12. Enter 0 if none."},
            "/writableOtherItemizedDeductions": {"kind": DOLLAR, "line": "Schedule A, line 16",
                                                 "ask": "Other itemized deductions — Schedule A, "
                                                        "line 16. Enter 0 if none."},
            "/writableElectToItemize": {
                "kind": BOOLEAN, "line": "Schedule A, line 18",
                "ask": "Do you elect to itemize deductions even though they are less than your "
                       "standard deduction? — Schedule A, line 18. Answering yes uses the itemized "
                       "total on Form 1040, line 12 even when it is the smaller figure."},
        },
    },
}


def offered_topics() -> dict:
    return {key: topic for key, topic in TOPICS.items() if topic["status"] == OFFERED}


def offered_writables() -> dict:
    """path -> (topic key, entry), over the topics the page asks."""
    return {path: (key, entry) for key, topic in offered_topics().items()
            for path, entry in topic["writables"].items()}


def topics_for(facts: dict) -> dict:
    """The topics this RETURN can be asked — every offered one, less any form that is about one of
    something the return does not have. A Form 8829 is about a business: with no Schedule C on the
    return there is nothing to attach it to, and offering it would ask for figures that could not
    be typed against anything."""
    rows = facts or {}
    return {key: topic for key, topic in offered_topics().items()
            if not topic.get("member_rows") or (rows.get(topic["member_rows"]) or [])}


def rows_for(topic: dict, facts: dict) -> list:
    """The row numbers of `facts` this topic is asked against — `[0]` for a return with one
    business, `[0, 1]` for two, and `[None]` for a form that is about the return itself."""
    if not topic.get("member_rows"):
        return [None]
    return list(range(len((facts or {}).get(topic["member_rows"]) or [])))


def path_for(path: str, row) -> str:
    """The offered path as it is typed for one row: `/scheduleCs/*/x` -> `/scheduleCs/[0]/x`."""
    return path if row is None else path.replace("/*/", f"/[{row}]/", 1)


def offered_gates() -> dict:
    """gate path -> topic key, over the topics the page asks."""
    return {topic["gate"]: key for key, topic in offered_topics().items() if topic["gate"]}
