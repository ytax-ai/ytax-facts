# Tax interpretations in this dictionary — a request for expert review

This dictionary computes a 2025 federal individual income tax return (Form 1040 and the schedules and forms
that feed it). Tax law does not always give one answer. Where a form, its instructions and the Internal
Revenue Code point different ways, or say nothing about a case the software must still handle, somebody has
to choose. The choices collected here were made by **the product owner, who is not a tax professional**. They
were made so the software behaves the same way every time, not because the owner is sure they are right.

**Nothing in this document is tax advice.** It describes what the software does and why.

**We ask enrolled agents, CPAs and tax attorneys to review these choices.** For each entry, tell us whether you
would confirm it, correct it, or need more facts. A short answer is useful: the entry ID, "confirm" or
"correct", and one sentence of reasons, with a citation if you have one.

> **How to respond:** open an issue at https://github.com/ytax-ai/ytax-facts/issues.

Each entry also carries **our best recommendation**. It is written by the team that maintains the dictionary,
working only from the sources listed. The owner asked for it to be stated plainly, even where it differs from
the owner's call. Where it differs, the software still follows the owner's call until a reviewer or a
published authority settles the question. The recommendation is a view, not a ruling.

## How to read this document

- **Our current call** is what the software does today. Some entries are marked **implementation in
  progress**: the call is made and the work to follow it is under way. For those, the facts named are the ones
  that exist today; their names may change when the work lands.
- **Refuse** means the software will not produce a return for that population. It stops and says why, rather
  than file a number it cannot stand behind. A refusal is never silent.
- **Confidence** is our confidence in our own recommendation, not in the owner's call.
- **Direction if wrong** says who is hurt if the current call turns out to be wrong: *over-tax* (the filer
  pays too much), *under-tax* (the return understates tax), or *refusal* (a filer who could have been served
  is turned away).
- **Where it lives** names the fact files in this directory and the fact paths inside them. A path is written
  `file:/path`, where `file` is `dictionary/ty2025/<file>.xml` and `/path` is the `<Fact path="...">` in that
  file. A `*` in a path stands for each item of a collection (each dependent, each rental property, and so on).
- **Authority** quotes are copied from the published documents themselves: the IRS forms, instructions and
  publications, the U.S. Code, and the Code of Federal Regulations. The maintainers keep a verified copy of each
  document the dictionary relies on and re-read every quote against it. We give the publisher, the page printed
  on the document, and the exact words, so a reader can check them against the official copy.
  Hyphens that only break a word at the end of a printed line are removed. `[...]` marks words left out.
  Where our copy has no printed page (a web edition), we name the section heading instead. Where the
  maintainers do not hold a copy of a source, we say so and cite nothing.
- The U.S. Code quotes are from the 2024 edition published by the Office of the Law Revision Counsel (laws in
  effect January 6, 2025), unless the entry says otherwise. The 26 CFR quotes are from the April 1, 2025
  annual edition.

This document covers only the choices the owner made. The dictionary also records many smaller readings made
while it was built, each tagged `interpretation:provisional` beside the fact it governs (about 2,500 of them).
They are not reviewed here. `INTERPRETATION-TAGS.md`, in this directory, explains the tags and how to find
them.

**One general tension runs through several entries.** The owner's general instruction is that tax law is the
authority: a form or a convenience never overrides the statute. In a few entries (AD-01, AD-02, IN-13) the owner
nonetheless chose the IRS form's or the industry's reading where the statute's text points elsewhere. Those
entries say so, and they are among the ones we most want checked.

## Summary

Groups are listed in return order. Within a group, entries where our recommendation differs from the current
call come first, then those where our confidence is low, then the rest.

"Agrees?" compares our recommendation with the owner's call: **Yes**, **No**, or **Partly**.

| ID | Form / line | Question | Our current call | Our best recommendation | Agrees? | Confidence | Population affected | Direction if wrong | Authority | Facts (file: key fact) |
|---|---|---|---|---|---|---|---|---|---|---|
| GEN-01 | All forms | Does an unanswered question block the return? | Only if the filer reached it (entered a document, opened a part) and it is required | Keep | Yes | High | Every filer | Refusal (friction) or under-tax | No IRS text; completeness convention | `flow: /flowIsKnockedOut` |
| GEN-02 | All forms | When a population is not built yet, compute an estimate or refuse? | Refuse, with a stated reason | Keep; publish the list of refusals | Yes | High | Filers in unbuilt areas | Refusal | No IRS text; product boundary | `flow: /flowIsKnockedOut` |
| GEN-03 | All forms | Refuse a return where every amount is $0? | File it (owner ruled to retire the refusal) | Retire the refusal | Yes | High | $0 returns, incl. a Form 8962 reconciliation netting $0 | Refusal of a required return | Form 1040 instructions (2025) p. 8 | `flow: /flowIsKnockedOut` (no longer carries the $0 test) |
| FS-04 | Custody test for divorced or separated parents | When is a child too old to be "in the custody" of a parent? | Asks whether the child was emancipated (and when); the age-of-majority table for the child's state (19 AL/NE, 21 MS/PR, else 18) only decides when the answer is required | Ask whether the child was emancipated; keep the table only as a prompt | Yes | Low | Parents of children aged 18-20 | Wrong parent claims the child | Pub. 504 (2025) p. 9; state statutes not stored | `dependentsBenefitSplit: /familyAndHousehold/*/writableChildEmancipatedUnderStateLaw` |
| FS-02 | Filing status | May a filer widowed during the year, who lived apart from the spouse, file head of household? | Yes, if the spouse was not in the home at death or at any time from July 1 to death | Keep | Yes | Medium-low | Widowed filers with a child who had separated | Under-tax (if HOH barred) | IRC 2(b)(2)(C), 2(c), 7703(b); 26 CFR 1.2-2(e) | `filers: /livedApartLastSixMonths` |
| FS-03 | Qualifying surviving spouse | When is a spouse missing in a combat zone treated as having died? | The earlier date IRC 2(a)(3) gives, both ways: it closes the status when the earlier date is before the two-year window, and opens it when a death determined in the tax year is deemed inside the window; year-level test | Keep | Yes | Medium | Very small | Under-tax (closing) or over-tax (opening) | IRC 2(a)(3), p. 56 | `filers: /spouseMissingStatusDeemedDeathBeforeQssWindow`, `filers: /spouseMissingStatusDeemedDeathInQssWindow` |
| FS-01 | Form 8332 / IRC 152(e) | If the filer's own answers show the release fails, refuse or compute? | Compute as if 152(e) does not apply | Keep | Yes | High | Divorced parents with contradictory release answers | Wrong parent claims the child | IRC 152(e)(1)-(2), p. 720 | `dependentsBenefitSplit: /knockedOutByContradictory8832` |
| FS-05 | EIC home-in-U.S. test | How is a service member stationed abroad on extended active duty handled? | One question: counting that time as U.S. time, was the main home in the U.S. over half the year? | Keep | Yes | High | Military EIC claimants | Over-claim or denial of EIC | IRC 32(c)(4), p. 137 | `eitc: /writableMainHomeInUsOverHalfYearCountingExtendedActiveDutyAbroad` |
| FS-07 | Qualifying child of more than one person, non-parent claimant | When a filer who is not the child's parent and another taxpayer can both claim the child, who may use the child? | The IRC 152(c)(4) tie-breaker from three answers: can a parent claim, does a parent claim, is the filer's AGI higher; a tie is not higher; unanswered, the return is refused | Keep | Yes | Medium | Grandparents, aunts, uncles and others sharing a home with a child | Over-claim (a lower-AGI non-parent claims) or loss of the child | IRC 152(c)(4)(A), (C), p. 719; Pub. 501 (2025) pp. 15-16 | `familyAndHousehold: /familyAndHousehold/*/nonParentLosesQualifyingChildTieBreak` |
| FS-06 | Divorced-parent rule, IRC 152(e) | Does a disabled child emancipated before midyear stay in the special rule? | No; emancipation takes the child out (owner ratified) | Keep | Yes | Medium | Parents of emancipated disabled adult children | Wrong parent claims the child | Pub. 504 (2025) p. 9 | `dependentsBenefitSplit: /familyAndHousehold/*/childMayQualifyForBenefitSplit` |
| IN-13 | Form 172 line 1 | Are the new Schedule 1-A deductions left out of the NOL computation? | Yes, with the QBI deduction (common practice). The owner kept this call after review. | Start from taxable income before the NOL, add back only what IRC 172(d) lists | No | Low | Filers with an NOL and a Schedule 1-A deduction | Over-tax (NOL too small) | IRC 172(d)(3), (4), (8), p. 878 | `form172: /form172Line1AgiLessDeductions` |
| IN-19 | Form 4797 | Holding period unanswered on a sale of business property | Derived from the line 19 dates; with no dates, a gain waits for the answer and a loss is refused | Treat an unanswered holding period on a gain as unanswered (hold the return), or derive it from the dates | Yes | Medium | Business-property sellers who skip the question | Over-tax | Form 4797 instructions (2025) p. 1 | `form4797: /section1245Dispositions/*/heldMoreThanOneYearComplete` |
| IN-18 | Form 8621 line 7c → Schedule D | Where do a QEF's 28% and unrecaptured 1250 portions go? | Separate intakes feeding the two Schedule D worksheets | Keep; confirm the worksheet lines | Yes | Low | PFIC shareholders with a QEF election | Under-tax | Form 8621 instructions (2025) p. 12 | `form8621: /form8621Funds/*/line7cCollectiblesGain` |
| IN-12 | Form 8829 line 37 vs line 42 | Improvement placed in service on the day business use began: basis or separate depreciation? | Owner ruling 2026-10-01: compare by day; only strictly after first business use is separate (line 42); same day is basis (lines 37-40) | Keep | Yes | Medium | Home-office filers with improvements | Small either way | Form 8829 instructions (2025) p. 5 | `scheduleC: /scheduleCs/*/homeAdditions/*/rowIsModeled` |
| IN-01 | Form 1040 line 3a | Is a nominee's share of qualified dividends removed from line 3a? | Yes, per payer | Keep | Yes | High | Nominee recipients | Under-tax | Pub. 550 (2025), "Qualified dividends" | `dividendReports: /dividendReports/*/writableNomineeQualifiedDividends` |
| IN-02 | Form 1099-MISC boxes 8 and 15 | Is a blank box zero or unknown? | Unknown: must be answered | Keep | Yes | Medium | Filers with Form 1099-MISC | Under-tax (if read as zero) | No IRS text; box captions only | `form1099Misc: /form1099Miscs/*/isComplete` |
| IN-03 | Schedule 3 line 13b / Schedule A line 16 | Claim of right over $3,000: how is the lower-tax method chosen? | Computed: the software figures the tax with the deduction and the tax without it less the earlier-year decrease, and takes the lesser (the deduction on a tie); with income averaging, both figures are the Schedule J tax (IN-160); returns where its two figures are not the whole tax are refused | Keep (owner decision supersedes the earlier filer-answer design) | Yes | High | Filers who repaid more than $3,000 | Over-tax, or refusal outside the computed population | IRC 1341(a), p. 2429; Pub. 525 (2025) pp. 36-37; Pub. 915 (2025) p. 15 | `taxCalculations: /claimOfRightDeductionGivesLesserTax` |
| IN-04 | Schedule E, vacation home | Are rental expenses entered whole and allocated by days, or entered already allocated? | Entered whole; allocated by fair-rental days over days used | Keep | Yes | High | Mixed-use rentals | Over- or under-deduction | IRC 280A(e)(1), p. 1048; Pub. 527 (2025) p. 25 | `scheduleE: /rentalProperties/*/dwellingUsedAsHome` |
| IN-05 | Schedule E, depreciation | Building class unanswered: assume 27.5 years? | No default; the return waits for the answer | Keep | Yes | High | Rental owners | Under-tax (if 27.5 assumed) | IRC 168(c), p. 784 | `scheduleE: /knockoutRentalBuildingRecoveryPeriodUnknown` |
| IN-06 | Schedule E, prior-year losses | Unanswered prior-year unallowed loss: zero or unknown? | Unknown (in progress) | Keep | Yes | High | Rental owners | Over- or under-tax | No IRS text | `scheduleE: /rentalProperties/*/priorYearUnallowedLoss` |
| IN-07 | Schedule E, PTP / Form 4797 | Is a PTP's section 1231 gain combined with the same PTP's loss? | Combine; a passive box 10 loss beside the same PTP's income is still refused | Keep | Yes | High | PTP investors | Over-tax | Partner's Instructions for Schedule K-1 (Form 1065) (2025) p. 10 | `scheduleE: /knockoutK1PtpSection1231NotCombined` |
| IN-08 | Schedule K-1, PTP | Item D (PTP) unanswered; limited partner's participation unanswered | Item D has no default; LP participation presumed not material | Keep | Yes | High | K-1 recipients | Under- or over-tax | IRC 469(h)(2), p. 1637 | `scheduleE: /formK1s/*/materiallyParticipatedAfterPresumption` |
| IN-09 | Form 8582 / K-1 box 12 | Is a passive K-1's section 179 share a passive deduction? | Yes, an ordinary passive-activity deduction | Keep | Yes | High | Passive K-1 investors | Under-tax | Form 8582 instructions (2025) p. 8 | `scheduleE: /formK1s/*/section179PassiveActivityDeduction` |
| IN-10 | Form 4835 line 34 | Does the at-risk box limit the Form 4835 loss? | Yes, as on Schedules C, E and F | Keep | Yes | High | Farm landlords with losses | Under-tax | Form 4835 (2025) line 34 | `form4835: /form4835AtRiskLimitationApplies` |
| IN-11 | Form 4684 | Property columns; casualty to a home used for a Schedule C business | Columns A-D; line 27 from that business's Form 8829 line 35 | Keep | Yes | High | Casualty filers | Under-tax | Form 4684 instructions (2025) p. 10 | `form4684: /casualtyEvents/*/properties/*/writableAdjustedBasis` |
| IN-14 | Form 8915-F, lines 4b/5b | Disaster distributions: per person? what stays on line 4b/5b? | Per person; only the excess stays on 4b/5b; both-spouses case refused | Keep | Yes | High | Disaster-distribution recipients | Over-tax | Form 8915-F (Rev. 12-2025) p. 2; instructions p. 9 | `form8915F: /form8915FCurrentQualifiedPensionTaxableRemoval` |
| IN-15 | Schedule F / Form 4835, section 175 | Order and base of the soil and water conservation limit | Section 175 first, per taxpayer, on its own base | Keep | Yes | High | Farmers | Over- or under-tax | 26 CFR 1.175-5(a)(2), p. 212 | `form4835: /form4835Section175GrossIncomeFromFarming` |
| IN-16 | Form 4797 line 29a | Filer's single percentage, or a receipt-age schedule? | Filer's single figure, as the line asks | Keep | Yes | High | Section 1255 dispositions | Either | Form 4797 instructions (2025) p. 12 | `form4797: /section1245Dispositions/*/writableSection1255ApplicablePercentageOfPayments` |
| IN-17 | Schedule D / Form 2439 | Section 1202 exclusion: computed per notice, or a filer figure? | Filer figure | Keep | Yes | High | QSB stock holders | Either | Schedule D instructions (2025) p. 8 | `scheduleD: /writableSection1202ExclusionFromForm8949` |
| IN-20 | Schedule 1 line 8z / Form 8960 line 6 | Section 1296 mark-to-market PFIC amounts: where is each entered? | Regular-tax amounts only from the Form 8621 entries; the NIIT position list feeds only Form 8960 line 6 | Keep | Yes | High | PFIC mark-to-market holders | Double count (under- or over-tax) | Form 8960 instructions (2025) p. 12 | `form8960: /niitLine6Section1296MarkToMarketAdjustment` |
| IN-21 | Form 1099-DA boxes 4 and 11c | Backup withholding and a creator's first-sale NFT proceeds | Box 4 goes to line 25b; box 11c is refused until built | Keep the box 11c refusal until its route is built | Yes | High | NFT creators with first-sale proceeds | Box 4 computed; box 11c refused | Form 1099-DA (2025) recipient instructions; Form 1040 instructions (2025) pp. 15-16, 39 | `scheduleD: /form1099DaFederalIncomeTaxWithheld`, `/knockoutForm1099DaCreatorFirstSaleProceedsNotRouted` |
| IN-22 | Form 4835 line 10 / Schedule F line 12 | Conservation expense entered on Form 4835 by a filer who claims no farm rental: deduction and carryforward | No deduction and no share of the 25% limit; the whole amount, carry-in included, is shown as carried forward | Keep the zero deduction; confirm the carryforward | Yes | Medium | Filers with a stray Form 4835 entry | Under-tax if carried forward wrongly | IRC 175(b), p. 17; Form 4835 (2025) p. 2 | `form4835: /form4835Line10` |
| IN-50 | Form 8621 line 8 | A QEF distribution above the year's inclusion, not shown previously taxed: how is it taxed? | As an ordinary (never qualified) dividend, wholly; line 8b is the intake for any QEF; unanswered is refused | Keep; model a distribution beyond the QEF's earnings and profits if one appears | Yes | Medium | QEF shareholders with large distributions | Under-tax (if left out) | Form 8621 instructions (2025) p. 13; IRC 1293(c), 301(c), 1(h)(11)(C)(iii) | `form8621: /form8621Funds/*/qefDistributionDividend` |
| IN-51 | Form 8621 lines 9a-9c / Form 1040 line 24 | Election B for two or more funds: how much tax is deferred? | The section 1294(b)(1) excess measured once: tax less the filer's figure without all electing funds' line 8e, never more than the line 9c sum; unanswered is refused | Keep; model the per-fund split if the regulation is obtained | Yes | Medium | Shareholders deferring tax on several QEFs | Under-tax (over-deferral) if the per-fund sum were used | IRC 1294(b)(1); Form 8621 instructions (2025) p. 13 | `form8621: /form8621CurrentTaxDeferral` |
| IN-52 | Form 8621 Part I | When is Part I not required? | Only the $25,000 ($50,000 joint) aggregate and $5,000 indirect exceptions, for a section 1291 fund with no excess distribution or gain; the fund list is taken as complete; an unanswered input keeps Part I | Keep; add the estate, trust and chain-of-ownership exceptions if needed | Yes | Medium | Small PFIC holders | Extra Part I printed (no tax effect) | Form 8621 instructions (2025) pp. 5-6 | `form8621: /form8621Funds/*/partIRequired` |
| IN-53 | Form 1040 line 1h / Form 1099-MISC box 3 | Compensation of an H-2A agricultural worker reported in box 3: other income or wages? | Wages on line 1h (earned income), not line 8z | Keep | Yes | Medium | H-2A workers who gave no TIN | Over-tax (EIC) if wrong the other way; under-tax if box 3 is not wages | IRC 32(c)(2)(A)(i); Pub. 225 (2025) p. 86 | `form1099Misc: /primaryFilerForm1099MiscH2aCompensation` |
| IN-54 | Form 8958 line 4 / Schedule 1 line 1 | On a community-property separate return, whose is a taxable state or local income tax refund? | Refuse until built; the build splits it by who paid the tax (community funds: half each) | Keep the refusal; build this reading | Yes | Medium | Community-property filers filing separately with a taxable refund | Refusal | Pub. 525 (2025) p. 23; Pub. 555 (12-2024) p. 7; Form 8958 p. 4 | `filers: /communityPropertyAllocationInputsComplete` |
| IN-55 | Form 8958 / IRC 66(b) | Must a filer who kept community income from the spouse report all of it? | No question is asked; the return follows state law until the IRS disallows | Keep | Partly | Medium | Community-property filers filing separately | Under-tax | IRC 66(b); Pub. 555 (12-2024) p. 8 | `filers: /isCommunityPropertyAllocationReturn` |
| IN-56 | Schedule 1 line 8z (Form 1099-PATR) | Where do cooperative distributions go without Schedule F? | Boxes 1, 2, 3 and 5 to Schedule 1 line 8z, less the Schedule C line 6 business part and nontaxable box 1 dividends; Schedule F on a farm return | Keep | Yes | Medium | Non-farm cooperative patrons | Income over-stated if box 1 was personal-use; SE tax missed if business | Form 1099-PATR (Rev. 4-2025) p. 4; Form 1040 instructions (2025) p. 92 | `income: /schedule1Line8zCooperativeDistributionsWithoutScheduleF` |
| IN-62 | Schedule E Part I and Part II / Form 8582 (entire disposition) | A passive activity sold in full: how is the release figured when the return has other passive activities? | Combine only that activity's income, losses and prior-year unallowed losses; an overall loss leaves Form 8582 and is deducted in full as nonpassive; an overall gain stays on Form 8582 | Keep | Yes | High | Filers who sell a rental or a partnership interest with suspended losses | Over-tax (losses left suspended) before this build | Form 8582 instructions (2025) p. 9; IRC 469(g)(1)(A), p. 1636 | `scheduleE: /formK1s/*/dispositionReleasedLoss` |
| IN-63 | Schedule E Part II (entire disposition) | Which disposed activities are still refused? | A K-1 with a box 22 or 23 activity statement, and a passive non-PTP K-1 with a box 12 section 179 deduction | Build the per-activity carry-in and a section 179 ordering | Yes | Low | Partners in multi-activity partnerships, and passive section 179 electors, who sell out | None (refused) | Form 8582 instructions (2025) p. 9; Partner's Instructions for Schedule K-1 (Form 1065) (2025) | `scheduleE: /knockoutPassiveEntireDispositionReleaseNotBuilt` |
| IN-23 | Form 172 lines 7 and 12 | A negative entry for nonbusiness income or business capital gains | Read as zero | Keep | Yes | High | NOL filers who mistype a sign | Under-stated NOL | Form 172 (Rev. December 2024) p. 1 | `form172: /form172Line8NonbusinessGainAndIncome` |
| IN-24 | Form 1040 line 1h / Form 1099-R code 3 | A partly taxable disability pension before minimum retirement age: line 1h or refuse? | Box 2a on line 1h as wages (owner ruling) | Keep | Yes | High | Disability pensioners below minimum retirement age with cost basis | Refusal (if wrong the other way, under-tax) | Pub. 575 (2025) p. 6; Form 1040 instructions (2025) p. 25 | `form1099Rs: /form1099Rs/*/isDisabilityWagesBeforeMinRetirementAge` |
| IN-25 | Form 1040 lines 4a-5b / Form 1099-R rollovers | A rollover after 60 days but within a longer period the IRS allows (waiver, self-certification, frozen deposit, code M due date) | Excluded like a timely rollover; code M forms asked (owner ruling) | Keep | Yes | High | Late rollovers | Refusal or under-tax | IRC 402(c)(3)(B)-(C); Pub. 590-A (2025) p. 24; Pub. 575 (2025) p. 23 | `form1099RFrontier: /form1099Rs/*/writableIndirectRolloverCompletedWithinExtendedPeriod` |
| IN-26 | Form 5329 lines 1-2 | In-plan Roth rollover recapture exception: netted before line 1 or on line 2? | Recapture in full on line 1, exception on line 2 with its number (owner ruling) | Keep | Yes | High | Designated Roth account early distributions within 5 years of an IRR | Print only (tax unchanged) | Form 5329 instructions (2025) pp. 3, 5 | `form1099RFrontier: /form1099Rs/*/inPlanRothRolloverRecaptureExceptedAmount` |
| IN-230 | Form 8606 lines 13-15a (Pub. 590-B Worksheet 1-1) | Worksheet 1-1 line 5 includes QCDs and an HSA funding distribution: do they enter the ratio or reach line 15a? | No: Form 8606 lines 7-9 feed the worksheet, so a QCD or HSA funding distribution takes no basis and no share reaches line 15a | Keep | Yes | High | Filers who contribute, may not deduct all of it, and make a QCD or HSA funding distribution in the same year | Under-tax (a few hundred dollars in the worked example) if the worksheet's literal ratio is right | IRC 408(d)(8)(D), 408(d)(9)(E); Pub. 590-B (2025) pp. 14, 17; Form 8606 (2025) p. 1 line 7 | `form8606: /form8606Ws11NontaxablePortion` |
| IN-231 | Form 5329 line 1 / Form 8606 line 15a | An early IRA Form 1099-R that Form 8606 figures: what goes on line 1? | Each form's pro rata share of the owner's line 15a (less the Line 15c Worksheet repayment reduction), not box 2a | Keep | Yes | High | Filers under 59 1/2 with basis in a traditional IRA who take an early distribution | Over-tax if box 2a were right; under-tax if a repaid distribution should stay on line 1 | Instructions for Form 5329 (2025) p. 3; Instructions for Form 8606 (2025) p. 11; IRC 72(t)(1), 408(d)(2) | `form1099RFrontier: /form1099Rs/*/form5329Line1ItemAmount` |
| IN-27 | Form 1040 line 5b / Form 1099-R box 6 | NUA election: how to know a lump-sum distribution? | Ask; the election has no effect on a non-lump-sum distribution (owner ruling) | Keep | Yes | Medium | Filers with employer securities who elect to include NUA | Over-tax (if box 6 wrongly added) | IRC 402(e)(4)(A), (B), (D)(i) | `form1099RFrontier: /form1099Rs/*/writableNuaDistributionIsLumpSum` |
| IN-28 | Schedule 1 line 8a | An NOL deduction entered as one figure, without the year each loss arose | Not deducted until the losses are listed; then computed with the 80% limit | Keep | Yes | High | NOL carryforward filers | Over-tax if a listed loss is mistyped; under-tax avoided | IRC 172(a)(2); Form 172 instructions (Rev. December 2024) p. 4 | `income: /schedule1Line8aNetOperatingLossDeduction` |
| IN-29 | Schedule SE line 2 / EIC Worksheet B line 1a | Fees of a fee-basis state or local official: which line, and is earned income adjusted? | Line 2 when the position is solely fee-paid and uncovered; $0 otherwise; unanswered waits; no earned-income subtraction for fees also on a W-2 | Keep the line; review the earned-income overlap | Yes | Medium | Fee-basis state and local officials (for example some county clerks and justices of the peace) | Over-credit of EIC if fees are also wages; under-tax if the placement were wrong | Schedule SE instructions (2025) p. 4; IRC 1402(c)(1), p. 2511; Form 1040 instructions (2025) p. 47 | `scheduleSE: /primaryFilerScheduleSeFeeBasisOfficialFeesIncluded` |
| IN-30 | Form 4797 lines 4, 5, 10, 16 / Schedule D lines 4, 11 | Where Form 6252 line 26 and Form 8824 lines 22 and 14 go; the installment answer when unanswered | The filer states the property's character and holding period; unanswered with an amount waits; an unanswered installment answer reads No unless a Form 6252 is filed | Keep | Yes | Medium | Installment sellers and like-kind exchangers | Over- or under-tax if routed wrong | Form 6252 instructions (2025) p. 4; Form 8824 instructions (2025) pp. 3, 5 | `form4797: /form6252Sales/*/form4797Line4Amount` |
| IN-41 | Form 8582 Part IV / Part V column (c) | Prior-year unallowed rental loss: when does it use the $25,000 active participation allowance? | Only when the filer says they actively participated in the year the loss arose too; one Yes/No per rental; unanswered is refused | Keep; split by year if a filer's history is mixed | Yes | High | Rental owners with a carried loss | Under-tax (if the loss wrongly used the allowance) | Form 8582 instructions (2025) p. 10; IRC 469(i)(1), p. 1637 | `scheduleE: /rentalProperties/*/priorYearLossQualifiesForActiveParticipation` |
| IN-57 | Schedule D line 13 / Form 1099-DIV boxes 2a, 2b, 2d | Capital gain distributions received as a nominee: which part of boxes 2b and 2d goes with the nominee share? | The filer states the nominee part of box 2a; boxes 2b and 2d leave in the same proportion | Keep | Yes | Medium | Nominees of fund distributions | Over-tax or under-tax at the 25%/28% rates if a fund splits its parts differently | Schedule D instructions (2025) p. 2; Pub. 550 (2025) Nominees | `dividendReports: /dividendReports/*/capitalGainDistributionsBelongingToFiler` |
| IN-58 | Schedule E Part II / Schedule K-1 (Form 8865) | A foreign partnership K-1 prints no item D (publicly traded) checkbox: ask it, or exempt it? And what marks an item as foreign? | Ask item D in the statute's words; the line 28 column (c) foreign-partnership answer marks the item | Keep | Yes | Medium | U.S. partners in foreign partnerships | Refusal (friction) if wrong | IRC 469(k)(2); Schedule K-1 (Form 8865) (2025) | `scheduleE: /formK1s/*/writableIsPubliclyTradedPartnership` |
| IN-59 | Schedule SE line 2 / Schedule K-1 (Form 1065) box 14 code A | A limited partner: subtract anything from box 14 code A? | No: box 14 code A as the partnership issued it | Keep | Yes | Medium | Limited partners and LLC members | Over-tax or under-tax of self-employment tax if a partnership misreports | Schedule SE instructions (2025) p. 3; Partner's Instructions for Schedule K-1 (Form 1065) (2025) p. 22 | `scheduleE: /primaryFilerK1SeEarnings` |
| IN-60 | Form 1040 line 6b / Pub. 915 Worksheet 4 | Lump-sum election for a filer who must use Pub. 590-A Appendix B: which IRA deduction does Worksheet 4 line 7 take? | The Appendix B Worksheet 2 deduction as claimed on Schedule 1 line 20 (Appendix B Worksheet 3 stands in for Worksheet 1); the IRA deduction is not refigured under the election | Keep | Yes | Medium | Social security recipients covered by a workplace plan who contribute to a traditional IRA and receive a lump-sum payment for earlier years | Over-tax if the deduction were left out (the election helps less); under-tax if the deduction should be refigured lower | Pub. 915 (2025) p. 5, p. 18 Worksheet 4 line 7; Pub. 590-A (2025) p. 54 Appendix B Worksheet 1 line 2, p. 56 Worksheet 3 line 2 | `socialSecurity: /lumpSumElectionWksht4Line8` |
| IN-64 | Schedule SE lines 1a and 2 / Schedule K-1 (Form 1065) box 20 code AN | Which partnership's box 14 code A goes on line 1a (farm partnerships) rather than line 2? | A partnership that reports box 20 code AN (farming and fishing business); its box 14 code A goes on line 1a and leaves line 2 | Keep | Yes | Medium | Partners in farm partnerships | None on the tax: line 3 combines lines 1a and 2; a fishing partnership's amount prints on line 1a | Schedule SE (2025) lines 1a and 2; Schedule SE instructions (2025) p. 3; Partner's Instructions for Schedule K-1 (Form 1065) (2025) p. 31 | `scheduleSE: /primaryFilerScheduleSeLine1a` |
| IN-65 | Schedule C line 1 / Schedule SE line 3 (IRC 7873) | A tribe member's income from a fishing rights-related activity of the tribe: how does the return keep it out of income and self-employment tax? | It is left off the return: not in Schedule C gross receipts, its allocable expenses not deducted, and a business that is wholly such an activity is not a Schedule C | Keep; add a K-1 intake for a qualified Indian entity's distributive share if needed | Yes | High | Members of tribes with treaty fishing rights | Over-tax if reported; under-tax if the allocable expenses were still deducted | IRC 7873(a)(1); Pub. 525 (2025) p. 34; IRC 265(a)(1) | `scheduleC: /scheduleCs`, `scheduleC: /scheduleCs/*/writableGrossReceipts` |
| IN-66 | Schedule 1 line 1 (Form 1099-G box 3) | Box 3 of a Form 1099-G is blank: which year is the box 2 refund for? | The filer says whether it is for 2024 tax; a 2024 refund goes through the 2024 worksheet, another year's through Publication 525 | Keep | Yes | Medium | Filers with a state or local income tax refund whose Form 1099-G leaves box 3 blank | Wrong worksheet if the filer answers wrongly; none if read from the form | Form 1099-G instructions (Rev. 3-2024) p. 2; Form 1040 instructions (2025) p. 88 | `unemployment: /form1099Gs/*/writableBox2RefundIsForTaxYear2024WhenBox3Blank`, `unemployment: /form1099Gs/*/box2RefundIsForTaxYear2024` |
| IN-67 | Schedule 1 line 8z (Form 1099-G box 6) | Where does a taxable government grant go? | The filer says whether the grant is trade or business income: no, Schedule 1 line 8z; yes, the business's other income on Schedule C or F (entered there) | Keep | Yes | Medium | Recipients of taxable federal, state or local grants | Income on the wrong line (self-employment tax missed or added) if the filer answers wrongly | Form 1099-G (Rev. 3-2024) recipient instructions p. 5; Form 1040 instructions (2025) p. 92; Schedule C instructions (2025) p. 5 | `unemployment: /form1099Gs/*/writableTaxableGrantIsTradeOrBusinessIncome`, `income: /schedule1Line8zForm1099GTaxableGrants` |
| IN-68 | Schedule F lines 4b and 6a (Form 1099-G boxes 7 and 9) | How do agriculture payments and CCC market gain reach Schedule F without counting twice? | The filer says whether box 7 is a crop disaster payment; program payments and box 9 fill a blank line 4b (box 9 left out under the CCC loan election), a typed line 4b wins; disaster payments set a floor for line 6a; with neither Schedule F nor Form 4835 the return is refused | Keep | Yes | Medium | Farmers and farm landlords with Forms 1099-G boxes 7 or 9 | Taxpayer-adverse on a blank line 4b whose taxable amount is less than the documents (cost-sharing exclusion) | Form 1099-G (Rev. 3-2024) recipient instructions p. 5; Schedule F instructions (2025) p. 4; Pub. 225 (2025) p. 11 | `scheduleF: /scheduleFLine4b`, `scheduleF: /scheduleFLine6aDocumentedProceeds`, `unemployment: /knockoutForm1099GAgriculturePaymentsWithoutAFarmSchedule` |
| IN-69 | Form 4952 line 4a / 4d (publicly traded partnership) | Does a PTP's box 10 section 1231 gain enter investment income through the PTP's line 4a amount? | No: the line 4a amount is the positive part of the smaller of the Schedule E result and the result with box 10; a box 10 gain goes to line 4d, which the filer enters | Keep | Yes | Medium | Partners in PTPs with a box 10 gain and investment interest expense | Under-deduction if the filer leaves the gain off line 4d | Partner's Instructions for Schedule K-1 (Form 1065) (2025) p. 10; Form 4952 instructions (2025) p. 3; IRC 163(d)(4)(B) | `scheduleE: /formK1s/*/ptpNonpassiveGainInInvestmentIncome` |
| IN-70 | Schedule E line 28 (h)/(k) and Form 4797 line 2 (publicly traded partnership) | A PTP's passive box 10 loss beside its own Schedule E income: how much is allowed and where? | Allowed on Form 4797 up to the Schedule E-side income, that income printed in column (h), the net gain portion in column (k); all of it on an entire disposition | Keep | Yes | High | Partners in PTPs with a passive box 10 loss and Schedule E income | Over-tax if too little allowed; under-tax if too much | Partner's Instructions for Schedule K-1 (Form 1065) (2025) p. 10; Form 8582 instructions (2025) p. 13 | `scheduleE: /formK1s/*/ptpSection1231PassiveLossAllowedOnForm4797` |
| IN-75 | Form 1040 line 1 / Form 8959 line 1 (Form 499R-2/W-2PR) | Puerto Rico wages of a filer who is not a bona fide resident, and box 22 Medicare wages | Refuse wages without a bona fide residence answer of yes; refuse box 22 that takes Form 8959 over the threshold or one statement over $200,000 | Keep until the wage measure, its line, the Form 1116 credit and Form 8959 lines 1 and 19 are built | Yes | High | Filers with Form 499R-2/W-2PR wages | Refusal | Publication 570 (2025) p. 20; Instructions for Form 8959 (2025) p. 1 | `formW2s: /knockoutForm499R2W2PrAmountsNotCarried` |
| IN-71 | Schedule E line 26 / Form 8582 (home also rented) | Is a home rented 15 days or more a passive activity? | No: its net goes to line 26 outside Form 8582; a carried passive loss is offset against its own income, a larger one is refused | Keep | Yes | High | Owners of vacation homes rented 15 days or more | Over-tax or under-tax where another passive loss or the special allowance was affected | IRC 469(j)(10); IRC 469(f)(1)(A); Form 8582 instructions (2025) p. 3 | `scheduleE: /rentalProperties/*/section469j10NonpassiveNet` |
| IN-72 | Schedule A lines 5b and 8a (rental also used personally) | Where does the personal part of a mixed-use rental's taxes and mortgage interest go? | Taxes' personal part to line 5b for every mixed-use rental; mortgage interest's personal part to line 8a only for a rental used as a home; two such homes refused | Keep | Yes | High | Itemizers with a vacation home or a rental also used personally | Over-tax if left off; under-tax if also typed by the filer | Pub. 527 (2025) pp. 25, 30; IRC 163(h)(4)(A)(i) | `scheduleE: /rentalPropertiesPersonalRealEstateTaxes`, `scheduleE: /rentalHomesPersonalMortgageInterest` |
| IN-87 | Form 1040 line 1a (Form 499R-2/W-2PR, U.S. Government employer) | Wages a bona fide resident of Puerto Rico receives from the U.S. Government on a Form 499R-2/W-2PR | Ask whether the employer is the U.S. Government; refuse when yes or unanswered | Keep until the U.S. wage figure (less excludable cost-of-living allowances), its line and the Form 1116 credit are built | Yes | High | Bona fide Puerto Rico residents employed by a federal agency | Refusal | IRC 933(1); Publication 570 (2025) p. 20 | `formW2s: /knockoutForm499R2W2PrAmountsNotCarried` |
| IN-88 | Schedule 3 line 11 (Form 499R-2/W-2PR box 21) | Does Puerto Rico social security tax withheld count toward the excess social security credit? | Yes: box 21 is social security tax withheld, each Form 499R-2/W-2PR is an employer, boxes 20 and 24 are its wages | Keep | No | High | Filers with Form 499R-2/W-2PR wages and more than one employer | Computation | Instructions for Form 1040 (2025) p. 117; Instructions for Schedule 8812 (2025) p. 9; IRC 3121(e)(2) | `schedule3: /excessSocialSecurityTaxWithheld` |
| IN-91 | Form 8949 code Y / Form 8997 Part III | Whether an attested QOF inclusion amount rounded to whole dollars agrees with the computed amount | Accept a difference under $1; refuse $1 or more | Keep | Yes | Low | QOF investors with a 5-year or 7-year basis increase | Refusal of a correctly rounded return if the tolerance were zero | IRC 1400Z-2(b)(2); 2025 Instructions for Form 1040 p. 23 | `form8997: /qofInclusionDispositions/*/qofInclusionAttestedGainDisagrees` |
| IN-92 | Form 8949 code Z / Form 8997 Part II | How the statutory limits on a QOF deferral are checked | One filer attestation of the four limits; refuse a deferral without it | Keep | Partly | Medium | Filers deferring gain in a qualified opportunity fund | Over-deferral (under-charge) if an attestation is false | IRC 1400Z-2(a)(1), (a)(2)(A); Form 8997 (Rev. December 2025) General Instructions | `form8997: /writableQofDeferralWithinStatutoryLimits`, `form8997: /knockoutQofDeferralLimitsNotAttested` |
| IN-97 | Schedule 3 line 11 (Forms W-2AS, W-2GU, W-2VI box 4) | Does territorial social security tax withheld count toward the excess social security credit, the same as Puerto Rico? | Yes: IRC 3121(e)(2)'s "United States" also includes the Virgin Islands, Guam and American Samoa; box 4 is social security tax withheld, each territorial statement is an employer, box 3 is its wages | Keep | No | High | Filers with a territorial Form W-2 and more than one employer | Computation | Instructions for Form 1040 (2025) p. 117; Instructions for Schedule 8812 (2025) p. 9; IRC 3121(e)(2) | `schedule3: /excessSocialSecurityTaxWithheld` |
| IN-160 | Schedule J line 23 / Schedule A line 16 / Schedule 3 line 13b | Claim of right over $3,000 on an income-averaging return: how are the two section 1341 taxes figured? | Each is the Schedule J tax: the Tax Table or rate-schedule tax on (taxable income with or without the deduction, less the elected farm income), plus the same base-year increase; an election of more farm income than the taxable income with the deduction is refused | Keep | Yes | Medium | Farmers and fishers who average income and repaid more than $3,000 | Over-tax, or refusal of the narrow over-election population | IRC 1341(a), U.S. Code p. 2429; IRC 1301(a), p. 2423; Schedule J (2025) p. 1 line 2a, p. 2 line 23 | `taxCalculations: /taxWithClaimOfRightDeduction` |
| AD-05 | Form 7206 / Form 8962 | Self-employed health insurance and PTC: which method? | Both methods; the more favorable result is used | Keep for now; offer the iterative method later or tell affected filers | Yes | High | Self-employed Marketplace enrollees | Over-tax (small) | Pub. 974 (2025) p. 47 | `form7206: /pub974SimplifiedMethodApplies` |
| AD-01 | Form 8889 line 6 | Last-month rule: does deemed coverage decide the spouse-allocation rules? | Yes, follow the form | Keep, but low confidence | Yes | Low | Married HSA owners | ~$50 per couple either way | IRC 223(b)(8)(A)(ii), p. 970; Form 8889 instructions (2025) p. 4 | `hsa: /filers/*/hsaLine6HadFamilyCoverageAnyMonth` |
| AD-02 | Form 8889 / Form 5329 | Employer HSA contribution for someone claimable as a dependent | An excess contribution (line 3 limit is $0) | Keep | Yes | Medium | Dependents with HSAs | Over-tax | Form 8889 instructions (2025) p. 2; IRC 223(b)(6), 106(d)(1) | `hsa: /filers/*/hasHsaContributionsAndCanBeClaimedAsDependent` |
| AD-04 | Form 5329 line 43 / Form 8889 | Prior-year HSA excess, no 2025 contributions: ask coverage? | Yes, ask the coverage questions (held for a later update) | Keep | Yes | High | HSA owners with an excess carry-in | Over-tax (refused today) | Form 5329 (2025) line 43 | `hsa: /filers/*/hsaHdhpCoverageStatusDerived` |
| AD-03 | Form 8889 line 17a | Exceptions to the 20% HSA tax | Filer states the reason; age 65 derived from birth date | Keep | Yes | High | HSA non-medical distributions | Under-tax | Form 8889 (2025) lines 17a-17b | `hsa: /filers/*/writableHsaCollectionExceptionReason` |
| AD-06 | Form 8283 | $500 filing test: each item or total? | Total for all noncash property | Keep | Yes | High | Noncash donors | None on tax (attachment only) | Form 8283 (Rev. 12-2025) p. 1; instructions p. 1 | `form8283: /form8283TotalDeductionForFilingTest` |
| AD-07 | Form 4562 Part V line 26/27 column (h) | Later-year car limit for a car placed in service before 2025 | Tax years in service = 2025 - year placed + 1; Tables 1-4 and Pub. 946 (2025, 2004, 1998) by year; electric and truck-or-van asked where the tables split; before 1987 refused | Keep; vendor a pre-1987 table if the population appears | Yes | Medium | Business filers depreciating a car placed in service before 2025 | Over- or under-deduction (column (h)) | Form 4562 instructions (2025) pp. 15-16; Pub. 946 (2025) ch. 5, (2004) ch. 5, (1998) ch. 4 | `form4562: /form4562ListedProperties/*/section280FLaterYearLimit` |
| AD-11 | Form 4562 Part I, multi-activity | Summary line 9/12: property totals or the allocation? | Property totals; the allocation must add up to line 12, else refused | Keep | Yes | High | Filers with several businesses electing section 179 | Refusal (friction) | Form 4562 instructions (2025) p. 5, Line 12 | `form4562: /knockoutSection179AllocationDoesNotDivideSummaryLine12` |
| AD-12 | Form 4562 Part III col. (g), Part VI col. (f) | Tables or the instructions steps; months counted | Steps (checked against the tables); beginning month counted in full | Keep | Yes | Medium | Business filers with 2025 property or amortization | Over- or under-deduction by rounding | Form 4562 instructions (2025) pp. 12, 19; Pub. 946 (2025) App. A | `form4562: /form4562Assets/*/depreciationDeductionAllowed` |
| AD-13 | Form 4562 per business; Sch. C l.13, Sch. F l.14, Form 4835 l.12 | Which line 22 goes where; each copy line 12 | Up to 5 numbered copies; schedules name their copy; allocations must add up to Summary line 12 | Keep; add rental copies later | Yes | Medium | Filers with more than one business or farm | Depreciation on the wrong schedule (SE tax, QBI) | Form 4562 instructions (2025) pp. 2, 5 | `form4562: /form4562Copy1Line22Total` |
| AD-08 | Form 2555 line 49 (Part IX) | Is the prior-year housing deduction carryover allowed when line 33 is not more than line 36? | Yes: allowed up to line 47 minus line 48, as the Code says (owner ruling) | Keep, as ruled | Yes | Medium | Form 2555 filers with a carryover and no current housing cost amount | Over-tax (carryover lost) or under-tax if the form's condition governs | IRC 911(c)(4)(C), p. 2153; Pub. 54 (2025) p. 19; Form 2555 (2025) p. 3 | `form2555Housing: /form2555Line49HousingDeductionCarryover` |
| AD-09 | Form 2555 line 29b worksheet | A location worksheet with 366 days: full-year limit or daily limit? | Daily limit times 366 | Keep | Yes | Medium | Fiscal-year filers whose year spans a leap day | Over-tax ($100-$300) if the full-year limit were used | Form 2555 instructions (2025) p. 5; Form 2555 (2025) p. 3 | `form2555Housing: /form2555HousingLocations/*/limit` |
| AD-10 | Form 7206 line 2 | Which age picks the long-term care premium limit: plain year-end age, or the day-before convention? | Year-end age (2025 minus birth year), as the line prints it | Keep | Yes | Medium | January 1 births just below a band boundary with long-term care premiums | Over-tax (lower band) | IRC 213(d)(10)(A), p. 938; Form 7206 (2025) line 2; Form 7206 instructions (2025) p. 2 | `form7206: /filers/*/form7206LongTermCarePremiumAgeBandLimit` |
| AD-21 | Form 8689 line 25 | Does "your IRA deduction" include a section 219(f)(6) deduction for a prior-year excess contribution? | Yes: line 25 uses each spouse's Schedule 1 line 20 IRA deduction, including it | Keep | Yes | High | USVI-income filers with an absorbed prior-year IRA excess | Over-tax (USVI share too small) if left out | Form 8689 (2025) p. 4; IRC 219(f)(6) | `form8689: /form8689Line25` |
| AD-22 | Form 1040 line 10 / Schedule 1 line 26 | A filer who excludes Puerto Rico or other territory income: full adjustments or the part allowed? | The part allowed, which is also what AGI subtracts | Keep; later apportion each Schedule 1 line so the schedule adds up | Yes | Medium | Bona fide territory residents excluding income under IRC 931 or 933 | Under-tax or a return whose lines 9, 10 and 11a do not add up | Pub. 1321 (Rev. 10-2025) p. 6; Pub. 570 (2025) p. 33 | `taxCalculations: /adjustmentsToIncome` |
| AD-23 | Form 8889 line 6; Form 8853 line 3 | Can spouses divide the family HSA (or Archer MSA) limit other than equally, including on separate returns? | Yes: a stated agreed share replaces the half, capped at line 5; joint shares over the limit are refused | Keep | Yes | High | Married HSA holders with family coverage who split the limit unequally | Under-deduction if the equal split is forced; over-deduction if unchecked | IRC 223(b)(5)(B)(ii); Form 8889 instructions (2025) p. 7 | `hsa: /filers/*/writableHsaAgreedFamilyLimitShare` |
| AD-24 | Form 8995 line 1 / Form 8995-A line 2 (QBI from Schedule C) | Several self-employment businesses and one Schedule 1 line 16 retirement plan deduction: how much reduces each business's QBI? | Line 16 times each business's net profit over the total net profit of all profitable self-employment businesses (Form 7206 line 5); the Schedule C businesses' shares reduce their QBI | Keep; add a per-plan business question if joint filers need it | Yes | Medium | Filers with two or more self-employment businesses and a SEP, SIMPLE or solo 401(k) deduction | Over-tax or under-tax by business when the plan covers one spouse's business only | Treas. Reg. 1.199A-3(b)(1)(vi); Form 8995 instructions (2025) p. 2 | `qbi: /qbiScheduleCSelfEmployedRetirementPlanDeduction` |
| AD-25 | Form 8995-A line 2 (QBI from Schedule C) | The section 224 business tips deduction is figured once for the return: how much leaves each business's QBI? | The return amount in proportion to each profitable Schedule C business's net profit, so it leaves QBI once in total | Keep; ask for tips by business if filers need it | Yes | Medium | Tipped sole proprietors with two or more Schedule C businesses above the threshold | Wrong business's wage limit applies (deduction by business, not total QBI) | Treas. Reg. 1.199A-3(b)(5); Form 8995-A instructions (2025) p. 1 | `qbi: /qualifiedBusinesses/*/scheduleCAttributableTipsExclusion` |
| AD-26 | Schedule 1 line 11 / Form 8815 line 9 | Educator expenses less the Form 8815 exclusion: the loop, and two educators on a joint return | Line 11 = entered expenses less the exclusion, then the $300 limits (exclusion taken from expenses above the limits first); Form 8815 line 9 and the other modified AGIs use the unreduced deduction | Keep | Yes | Medium | Educators who also exclude savings bond interest | Line 11 too high or a modified AGI too low (by at most $600) | IRC 62(d)(2); Form 1040 instructions (2025) p. 93; Form 8815 (2025) p. 4 | `educatorAdjustment: /educatorExpensesAdjustment` |
| AD-27 | Schedule 1-A lines 6 and 14c (tips and overtime) | On a joint return where only one spouse has a valid SSN and that spouse received part of the tips or overtime, is the whole deduction lost? | No: the part received by the spouse without a valid SSN is left out (the filer states it) and the rest is deducted | Keep | Yes | Medium | Mixed-status joint filers with tips or overtime | Under-tax if the whole deduction should be denied | IRC 224(e)(1), 225(d)(1); Form 1040 instructions (2025), Schedule 1-A | `schedule1A: /schedule1ATipsReceivedByIneligibleSsnSpouse` |
| AD-28 | Schedule A lines 2-4 and 11-14 | Adjusted gross income is negative: what are the medical floor and the charitable ceilings? | Figured on AGI floored at $0: the medical deduction is the medical expenses (never more), and gifts under a percentage ceiling are carried over, never a negative deduction | Keep | Yes | High | Itemizers with a business, farm or rental loss larger than their income | Over-tax if a negative base should allow more; under-tax is not possible | IRC 213(a), 170(b)(1)(H); Schedule A (2025) lines 3-4 | `scheduleA: /scheduleAAgiForPercentageLimits` |
| AD-29 | Form 8283 line 1 column (d) | Contribution date outside 2025 on a carryover-year return | Typed as a date; a bound constraint flags a non-2025 date only when the return is not a charitable carryover year | Keep | Yes | High | Charitable carryover-year filers | Wrongful refusal if a knockout were used instead | i8283 (2025), Noncash Contributions Carried Over to Later Year | `form8283: /form8283Items/*/writableContributionDate` |
| AD-30 | Schedule 1 line 20 / IRA Deduction Worksheet lines 8 and 9 | A minister's W-2 salary is also on Schedule SE line 2: is it IRA compensation twice? | No: it counts once, as wages on worksheet line 8; worksheet line 9 leaves it out | Keep | Yes | High | Ministers paid on Form W-2 who contribute to a traditional IRA | Under-tax before this build (compensation counted the salary twice) | IRC 219(b)(1)(B); Form 1040 instructions (2025) p. 98; Schedule SE instructions (2025) p. 1 | `scheduleSE: /primaryFilerSelfEmploymentEarnedIncomeForIraCompensation` |
| AD-31 | Schedule A line 12 / Pub. 526 Worksheet 2 lines 9 and 15-18 | Noncash gifts to 50% limit organizations other than capital gain property at FMV (ordinary income property; elected capital gain property; K-1 code C): what limit, and who figures the reduction? | 50% of AGI less the deductible cash gifts; the filer enters the reduced amount; K-1 code C joins | Keep | Yes | High | Itemizers giving used goods, inventory or short-term property, or electing to reduce capital gain property | Over-tax before this build (held to 30% of AGI) | IRC 170(b)(1)(A), 170(e)(1)(A); Pub. 526 (2025) pp. 26-27; Schedule K-1 (Form 1065) instructions (2025) p. 19 | `scheduleA: /writableCharitable50PctOrgNonCash` |
| AD-32 | Schedule 1 Part II / Form 7206 line 12 (IRC 933, 931) | With a territory exclusion, is the self-employed health insurance deduction disallowed, and is a penalty on excluded interest deducted? | The deduction stays apportioned, with the excluded Schedule C profit taken off its earned income limit on Form 7206 line 12; a penalty on a deposit whose interest is excluded is not deducted | Keep | Yes | Medium | Bona fide residents of Puerto Rico or another territory with self-employment income or time deposits | Under-tax before this build (the limit ignored the exclusion; the penalty was apportioned) | Pub. 1321 (2025) p. 6; IRC 933(1); 26 CFR 1.861-8(e)(9)(iii); IRC 162(l)(2)(A); IRC 401(c)(2)(A)(iv) | `form7206: /form7206Line12TerritoryExcludedEarnedIncome`, `interest: /earlyWithdrawalPenaltyOnExcludedTerritoryInterest` |
| AD-45 | Form 8829 line 9 / Form 4684 Section B (a Schedule C home) | Where does the federally declared disaster share of a home office casualty go? | Refuse a Schedule C home casualty not answered as outside a federally declared disaster, and a home casualty when two businesses file Form 8829 | Keep until line 9 and the split between businesses are built | Yes | High | Home-office filers with a disaster casualty | Refusal | Instructions for Form 8829 (2025) p. 3; Instructions for Form 4684 (2025) p. 10 | `form8829: /knockoutForm8829HomeCasualtyNotCarried` |
| AD-46 | Form 4684 lines 7 and 8 (property columns) | Safe harbor and corrosive drywall figures when properties are entered one by one | Refuse the event until the columns ask the figures; refuse more than four columns | Keep until per-column intakes and an additional-sheet print are built | Yes | High | Casualty filers using Rev. Proc. 2018-08 or 2010-36 | Refusal | Instructions for Form 4684 (2025) pp. 7-8; Publication 547 (2025) p. 6 | `form4684: /knockoutCasualtyPropertyColumnsNotCarried` |
| CR-01 | Form 2441 lines 29-31, line 3 | Line 29 zero or less | Stop: lines 30-31 blank, line 3 zero | Keep | Yes | High | Filers with large employer care benefits | Print error only | Form 2441 (2025) p. 2 | `cdcc: /cdccQualifyingExpenses` |
| CR-02 | Form 2441 lines 4-5 | Clergy / church employee earned income | As the instructions list (no change) | Keep | Yes | High | Clergy, church employees | Either | Form 2441 instructions (2025) p. 4 | `income: /cdccPrimaryActualEarnedIncomeForCreditsUnfloored` |
| CR-03 | Form 3800 | Business credits not yet computed | Refuse | Keep | Yes | High | Filers with general business credits | Refusal | No IRS text; product boundary | `form3800: /knockoutForm3800CreditComponentNotComputed` |
| CR-04 | Form 1116 / Schedule K-3 | Which Schedule K-3 recipients are refused? | Refuse only what the return cannot carry or does not carry: a reduction off line 12, a redetermination, a non-passive exception mismatch, taxes in a second category, and a partial carry of the direct foreign taxes | Keep | Yes | Medium | Partners and shareholders with foreign taxes | Refusal (partial-carry test too strict) or under-tax | Form 1116 instructions (2025) pp. 2, 8, 9; Schedule K-3 partner and shareholder instructions (2025); Form 1040 instructions (2025) p. 115 | `scheduleK3: /knockoutScheduleK3ForeignAmountsNotCarried` |
| CR-05 | Form 1116 / Schedule K-3 | Refuse a K-3 recipient who chose to deduct foreign taxes? | No; the deduction elector files (owner ruling) | Keep the release | Yes | Medium | K-3 recipients who deduct | Under-tax (taxes not on Schedule A) | IRC 901(a), p. 2109; Form 1116 instructions (2025) p. 2 | `foreignTaxCredit: /knockoutScheduleK3ForeignTaxesReachNoLine` |
| CR-06 | Schedule 3 line 1 | Credit without Form 1116 for a filer who chose the deduction? | No credit (owner ruling) | Keep | Yes | High | Small-FTC filers who deduct | Over-credit (credit and deduction both) | IRC 904(j)(1)(A), p. 2128; Form 1116 instructions (2025) pp. 1-2 | `foreignTaxCredit: /qualifiesForNoForm1116Exception` |
| CR-08 | Form 1116 Part II column (u) | Provisional credit for a contested tax elected without Form 7204 | Election not made; the contested tax is not credited (not refused) | Keep | Yes | High | Filers with a contested foreign tax | Over-credit if credited without the agreement | Treas. Reg. 1.905-1(c)(3), (d)(4), pp. 1025, 1027; Form 1116 instructions (2025) p. 5 | `form1116: /form1116ForeignCountries/*/writableFilesForm7204ProvisionalCreditAgreement` |
| CR-07 | Form 5695 lines 19-29 | A typed cost total with no QMID for each item it adds up | Earns $0 for that category (owner ruling); only items itemized with their own QMID count | Keep | Yes | High | Energy efficient home improvement credit filers who type a total | Over-credit if the typed dollars were allowed | IRC 25C(h)(1), p. 150; Form 5695 instructions (2025) p. 6 | `form5695: /form5695OtherDoorCredit` |
| IN-270 | Form 5695 line 10, line 11; fuel cell joint-occupancy ceiling | Does fuel cell capacity between half-kilowatt steps count in proportion? | Implementation in progress: whole half kilowatts only ($500 and $1,667 per whole half kW; 1,300 W gives $1,000) | Keep | Yes | High | Fuel cell filers whose nameplate capacity is not a half-kW multiple | Over-credit if proportional counting were kept | IRC 25D(b)(1), 25D(e)(4)(A); Instructions for Form 5695 (2025) p. 4, Line 10 | `form5695: /form5695Line10CapacityLimitForPrint` |
| IN-271 | Form 5695 lines 19-29 | An item whose QMID is not printed on its line (or a typed line b with no statement): does it count? | Ruled (lead 2026-09-30): no; its printed cost is $0, other items still count | Keep | Yes | High | Part II filers with incomplete QMIDs | Over-credit if unprinted QMIDs counted | IRC 25C(h)(1)(B); Instructions for Form 5695 (2025) pp. 1, 6 | `form5695: /form5695Line22aCentralAcCostTakenIntoAccount` |
| IN-272 | Form 5695 lines 25b, 25e | Must the enabled property earn a credit? | Ruled (lead 2026-09-30): code A no; codes B-G yes; no code gives $0 | Keep | Yes | High | Filers claiming enabling property | Over-credit if B-G needed no allowed credit | IRC 25C(d)(2)(D)(iii)(I)-(II); Instructions for Form 5695 (2025) p. 6, Line 25b | `form5695: /form5695EnablingPropertyCredit` |
| IN-273 | Form 5695 line 32a; lines 18b-29h, 28 | How does a joint occupant share the Part II limits? | Ruled (lead 2026-09-30): per line the smaller of the usual figure and limit x own/(own+others); line 28 $1,200 x own/(own+others) when own line 27 is over $1,200; line 29h follows the per-line rule; not refused | Keep | Yes | Medium | Joint occupants (not spouses filing jointly) | Over-credit if no proration; refusal if refused | Instructions for Form 5695 (2025) p. 3, Joint occupancy; IRC 25C(f)(1) | `form5695: /form5695InsulationCredit`, `form5695: /form5695CombinedCappedCredit` |
| IN-274 | Form 5695 lines 7c-8 | A joint occupant's fuel cell used under 80% for nonbusiness: which rule first? | Ruled (lead 2026-10-01): 25D(e)(7) first, then the (e)(4) allocation on that portion; not held | Keep | Yes | Medium | Joint occupants with business use of a fuel cell | Over- or under-credit when the ceiling binds | IRC 25D(e)(4)(B), 25D(e)(7) | `form5695: /form5695Line8FuelCellCostTakenIntoAccount` |
| IN-275 | Form 5695 line 30 (two main homes), line 10 | Typed figures from another form: the other home's line 30 above $3,200; a typed line 10 that is not a half-kW step | Ruled (lead 2026-10-01): line 30 held above $3,200; the kW capacity decides line 10 | Keep | Yes | High | Joint filers with two homes; fuel cell filers | Over-credit if passed through | Instructions for Form 5695 (2025) pp. 3-4; Form 5695 lines 28, 29h | `form5695: /form5695TotalHomeImprovementCredit` |
| IN-276 | Form 5695 lines 25c-25d | Three or more items of enabling property | Ruled (lead 2026-10-01): the return holds; the form carries two QMID boxes and every item needs its QMID reported | Keep | Yes | Medium | Filers with three or more enabling items | Credit for an item with no reported QMID | Form 5695 (2025) line 25d; Instructions for Form 5695 (2025), Part II caution | `form5695: /form5695EnablingPropertyQmidsReported` |
| IN-277 | Form 5695: every skip gate and every input a money line needs | A section question left unanswered with a cost behind it | Ruled (lead 2026-10-01): the return holds with a named reason; credits, printed cost lines and the line 28 numerator use one gate test | Keep | Yes | High | Part II filers who skip a section question | Under- or over-credit if the lines disagree | Form 5695 (2025) lines 17a-17c, 21a; Instructions for Form 5695 (2025) | `form5695: /form5695SectionAAnsweredNo` |
| IN-278 | Form 5695 line 17e | Improvements related to the construction of the main home: does a Yes close Section A? | Ruled (lead 2026-10-01): yes - follow the instructions (skip 18a-20d); a filer claiming improvements to an existing home answers No | Keep | Yes | Medium | Part II filers in a newly built home | Under-credit if a filer reading only the form answers Yes for non-construction improvements | Instructions for Form 5695 (2025), Line 17e; Form 5695 (2025) line 17e | `form5695: /form5695SectionAQuestionsAnswered` |
| IN-280 | Schedule C line 1 (statutory employee) | Statutory-employee wages and other receipts entered on one Schedule C | Ruled (lead 2026-10-01): the combination is held with a named reason directing a second Schedule C; two Schedules C compute (SE tax on the non-statutory one) | Keep | Yes | High | Statutory employees with other self-employment receipts | Under-charged SE tax if the combined schedule computed | Instructions for Schedule C (2025), Statutory employees | `scheduleC: /writableGrossReceipts` |
| IN-290 | Schedule C prior-year unallowed passive loss and prior-year at-risk loss | Unanswered: hold or $0? | Ruled (lead 2026-10-01): hold with a named reason when the business has a loss or is passive (IN-277, IN-289); a filer with none answers $0 | Keep | Yes | High | Schedule C filers | Money | Instructions for Form 8582 (2025); Instructions for Schedule C (2025) line 32; Form 6198 | `scheduleC` |
| IN-291 | Form 8960 and a passive Schedule C | Does a passive trade or business's net income enter Form 8960? | Ruled (lead 2026-10-01): yes - a passive activity's trade or business income is net investment income (IRC 1411(c)(2)(A)); it enters Form 8960 line 4a; built by pair PSC | Keep | Yes | High | Schedule C filers | Money | IRC 1411(c)(2)(A); Instructions for Form 8960 (2025) | `scheduleC` |
| IN-292 | Form 8995 and Form 461; prior-year passive loss in QBI | How does line 8p and an allowed prior-year passive loss reach QBI? | Ruled (lead 2026-10-01): QBI excludes the line 8p excess business loss, apportioned among the businesses; an allowed prior-year passive loss is a Form 8995 line 3 carryforward, pre-2018 losses excluded | Keep | Yes | High | Schedule C filers | Money | Instructions for Form 8995 (2025) | `scheduleC` |
| IN-293 | Form 8582 modified AGI and a passive Schedule C | How does a passive Schedule C enter Form 8582 MAGI? | Ruled (lead 2026-10-01): only through the pool's net passive income or loss as the instructions direct, never through Schedule C line 31; a cycle is broken by computing MAGI before passive amounts | Keep | Yes | High | Schedule C filers | Money | Instructions for Form 8582 (2025) | `scheduleC` |
| IN-294 | Form 461 and a statutory-employee Schedule C | Is a statutory employee's Schedule C on Form 461? | Ruled (lead 2026-10-01): no - excess business losses are determined without regard to any trade or business of performing services of an employee | Keep | Yes | High | Schedule C filers | Money | Instructions for Form 461 (2025), Definitions | `scheduleC` |
| IN-295 | Form 8829 home used in more than one business; more than one home for one business | Compute or hold? | Ruled (lead 2026-10-01): compute - line 36 is allocated among the businesses by the filer's reasonable method (an intake per business); several homes for one business use one Form 8829 per home; an unanswered allocation holds | Keep | Yes | High | Schedule C filers | Money | Instructions for Form 8829 (2025), line 36; Instructions for Schedule C (2025), line 30 | `scheduleC` |
| IN-296 | Blank optional amount lines on Schedule C and Form 8829 | Which blank lines read $0 and which hold? | Ruled (lead 2026-10-01): amount lines the filer enters only if any (returns and allowances, cost of goods sold detail, other income, the expense lines, Part III detail, Form 8829 column amounts) read $0 when blank; questions and inputs a computed line requires hold (IN-277) | Keep | Yes | High | Schedule C filers | Money | Schedule C (2025) and Form 8829 (2025) as printed | `scheduleC` |
| IN-297 | Schedule C line 9 standard mileage rate | Eligibility and double deduction | Ruled (lead 2026-10-01): an eligibility question per vehicle (i1040sc line 9 conditions); the standard mileage rate excludes depreciation and lease payments; the business share of car-loan interest goes on line 16b, never also on Schedule 1-A (amended 2026-10-05); unanswered with miles entered holds | Keep | Yes | High | Schedule C filers | Money | Instructions for Schedule C (2025), line 9 | `scheduleC` |
| IN-298 | Form 4562 rows for a home first used for business in 2025 | How is the home kept off Schedule C line 13? | Ruled (lead 2026-10-01): a home-row flag on the linked Form 4562 rows; flagged rows reach Form 8829 only, never Schedule C line 13 | Keep | Yes | High | Schedule C filers | Money | Instructions for Form 8829 (2025), line 41 | `scheduleC` |
| IN-299 | Rounding of Schedule C net profit | Does /scheduleCNetProfit round? | Ruled (lead 2026-10-01): no - under IN-285 Schedule C keeps cents through line 31 and net profit; rounding happens only where Form 1040 already rounds | Keep | Yes | High | Schedule C filers | Money | IN-285 | `scheduleC` |
| IN-281 | Form 461 line 5 (Schedule E rental) | Is a Schedule E rental a trade or business for the excess business loss limitation? | Ruled: ask per rental (`/rentalProperties/*/writableRentalIsTradeOrBusiness`); Yes keeps it on line 5, No adds its loss or income back on lines 10-11; unanswered on a return that reaches Form 461 holds | Keep | Yes | Medium | Filers with a rental beside a business loss near the threshold | Under-charged if a nonbusiness rental loss counts toward the excess business loss, over-charged the other way | Instructions for Form 461 (2025) Definitions, Trade or business; Line 5; Lines 10-11 | `scheduleE: /rentalProperties/*` (intake to build) |
| IN-282 | Form 461 line 3 (capital gains and losses) | Which capital gains count on Form 461, and how are capital losses treated? | Ruled: ask the capital gain net income attributable to the trade or business (`/writableForm461BusinessCapitalGainNetIncome`); line 3 takes Form 1040 line 7a, gains above the smaller of that amount and capital gain net income are added back on line 10, and capital losses are added back on line 11 | Keep | Yes | Medium | Business-loss filers with capital gains or losses | Under-charged if nonbusiness gains offset the business loss | Instructions for Form 461 (2025) Definitions, Treatment of capital gains and losses; Line 3 | `scheduleD: /capitalGainOrLossForForm1040` (intake to build) |
| IN-283 | Form 8582 Part VII (Schedule C loss activities) | The ratable split of the unallowed loss leaves an odd cent: which activity carries it? | Ruled: round each share half up to the cent and give the residual (plus or minus) to the last listed loss activity, so column (c) totals line C exactly | Keep | Yes | High | Filers with two or more passive loss activities | A cent of loss allowed or disallowed twice | Instructions for Form 8582 (2025) Part VII, columns (b) and (c) | `scheduleC: /scheduleCs/*/section469SuspendedPassiveLoss` |
| IN-284 | Schedule C line 31 / Form 8582 Part V column (c) | How does a prior-year unallowed passive loss of a Schedule C business enter the return? | Ruled: ask it per business (`/scheduleCs/*/writablePriorYearUnallowedPassiveLoss`, the 2024 Form 8582 Part VII column (c)); it enters Part V column (c); the allowed part reduces line 31 (PAL); the rest carries forward | Keep | Yes | High | Passive Schedule C businesses with suspended losses | Over-charged when a suspended loss is never released | Instructions for Schedule C (2025) Line 31; Instructions for Form 8582 (2025) Part V column (c) | `scheduleC: /scheduleCs/*/netProfit` |
| IN-285 | Schedule C lines 1-31 and Form 8829 | Lines 7, 29 and 31 now keep cents; line 30 is Form 8829 line 36 rounded to whole dollars. Which? | Ruled: one rule for the schedule: either every Schedule C and Form 8829 line keeps cents (rounding only at Form 1040), or every one rounds; today the existing constraint rounds line 30 while F kept cents on 7, 29 and 31 | Keep | Yes | Medium | Every Schedule C with cents | Under a dollar per line; a printed form that does not add up | Instructions for Form 1040 (2025), Rounding Off to Whole Dollars | `scheduleC: /scheduleCs/*/homeOfficeDeduction` |
| IN-286 | Form 461 / Form 172 (farming losses) | Does the farming-loss ordering change Schedule 1 line 8p? | Ruled: no; the ordering (threshold first to farming losses) only characterizes the resulting NOL for the 2-year farming carryback; line 8p is unchanged | Keep | Yes | High | Filers with both farming and nonfarming business losses | None on line 8p; a mischaracterized NOL otherwise | Instructions for Form 461 (2025) Farming and nonfarming losses | `income: /schedule1Line8pIncomeOrZero` |
| IN-287 | Schedule C checkboxes (line 1 statutory box, line H) | Is a checkbox left unchecked an unanswered question that holds? | Ruled: no; a "check if" box unanswered is unchecked (the statutory box is decided by a statutory Form W-2 link; line H by the business-began date when start-up costs are entered, which holds when unanswered) | Keep | Yes | Medium | Every Schedule C filer | A silent default if a checked box were needed | Schedule C (2025) lines 1 and H | `scheduleC: /scheduleCs/*/isStatutoryEmployeeIncome` |
| IN-288 | Form 461 lines 4, 5 (K-1 box 1) and 6 | Are Form 4797 Part I items, Schedule K-1 box 1 business income and Schedule F trade or business items without asking? | Ruled: yes; Form 4797 Part I property is property used in a trade or business, a K-1 business is decided at the entity level, and Schedule F is a farming business; no question is asked | Keep | Yes | High | Business-loss filers with these lines | None if the premise holds | Instructions for Form 461 (2025) Note; Instructions for Form 4797 (2025) | `income: /schedule1Line8pIncomeOrZero` |
| IN-289 | Schedule C / Form 8829 gate questions | Which Schedule C and Form 8829 questions hold when unanswered (IN-277 applied to this module)? | Ruled: hold: line G and line 32 with a loss; 32b amount at risk; vehicle method and business miles; home office method; Form 8829 total area, all-income-from-home, daycare non-exclusive, itemize, use stopped, additions, line 37 basis, operating expenses; simplified square feet and shared; gross receipts. Do not hold: checkboxes (IN-287), Form 8829 carryovers (an absent carryover is $0 by its text: "Enter any amount from your 2024 Form 8829") | Keep | Yes | Medium | Every Schedule C filer who leaves a question | A silent default on a money line | Form 8829 (2025) line 3 routing; Instructions for Form 8829 (2025) Lines 25 and 31; Instructions for Schedule C (2025) | `scheduleC: /scheduleCLossesHaveLineGAndLine32Answered` and the matrix holds |
| CR-09 | EIC earned income / Schedule SE line 2 | Wages from a foreign government or international organization with no Form W-2 are on Form 1040 line 1h and on Schedule SE line 2: counted once or twice? | Once: taken out of the wage figure and kept in self-employment earnings, as the printed Clergy treatment does | Keep | Yes | Medium | U.S. citizens employed by a foreign government or international organization in the U.S. | Over-credit (counted twice, below the phaseout) or under-credit (above it) | IRC 32(c)(2)(A), p. 137; Form 1040 instructions (2025) p. 43 | `eitc: /eitcForeignGovernmentWagesDualReportedSubtrahend` |
| CR-10 | EIC / child born and died with no SSN | A child born and died in 2025 with neither an SSN nor the birth or death document, beside a counted sibling: refuse the return? | No: the child is left out of the EIC count and listed on no row; the return files on the counted children | Keep | Yes | Medium | Parents of a child who died shortly after birth with no SSN and no document | Refusal of a filable return (if refused) | Schedule EIC (2025) line 2; IRC 32(c)(3)(D), p. 137 | `familyAndHousehold: /knockoutPersonBornAndDiedInTaxYearWithoutTin` |
| CR-11 | Form 8863 line 22(3) | A 2024 Form 1098-T with box 7 checked and no 2025 statement: is the Form 1098-T requirement met? | Yes: a Yes on line 22(3) meets it for that institution; the expenses must still be paid in 2025 | Keep | Yes | Medium | Students whose school sent only a 2024 statement with box 7 checked | Credit allowed without a qualifying statement (if the reading is wrong) | IRC 25A(g)(8), p. 97; Form 8863 (2025) p. 2 line 22; Form 8863 instructions (2025) p. 4 | `form8863: /aotcFirstInstitutionPayeeStatementMet` |
| CR-12 | Form 8839 carryforward worksheet (line 18) | A prior lot a separate return cannot use this year: carried or lost? | Carried to 2026 until the five-year limit | Keep | Yes | Medium | Married filers filing separately with an adoption credit carryforward | Carryforward overstated (if lost) | IRC 23(c) (web edition); Form 8839 instructions (2025) pp. 2, 8 | `form8839: /form8839CreditCarryforwardTo2026` |
| CR-13 | Form 8801 lines 11, 33, 54 | The 2024 filing status: which answer picks the $116,300 or $232,600 breakpoint when the Form 8801 question is blank or disagrees with the refund worksheet? | The Form 8801 answer; if blank, the 2024 status given for the refund worksheet | Keep | Yes | High | Filers claiming the prior-year minimum tax credit who were married filing separately for 2024 | Over-credit (MFS filer taxed at 26% in the band) | Form 8801 (2025) p. 1 | `form6251: /form8801PriorYearFilingStatusWasMarriedFilingSeparately` |
| CR-14 | Form 8396 line 3 | A reissued mortgage credit certificate at a rate above the original; a home that was the main home for only part of the year | No credit under the higher-rate certificate (the refinance year keeps the original leg); part year: line 1 is the interest for the main-home period | Keep | Yes | High | Mortgage credit certificate holders who refinanced or moved | Over-credit if wrong the other way | Form 8396 (2025) p. 2; IRC 25(e)(3)(A) | `form8396: /form8396ReissuedRateAboveOriginal` |
| CR-15 | Form 8941 lines 8 and 9 (Worksheets 5 and 6) | The two phaseout reductions: rounded fraction or exact, and may the credit go below zero when they add to more than line 7? | The exact fraction, one rounding to the cent; line 9 floored at $0 | Keep | Yes | High | Sole proprietors with more than 10 FTEs and average wages over $33,300 | Cents only (fraction); a negative credit reducing other credits (floor) | IRC 45R(c); Form 8941 instructions (2025) p. 8 | `form8941: /form8941Line9` |
| CR-16 | Form 8881 lines 5, 6a, 6g, 12-13 | Which employees line 6a counts; a plan with no eligible rank-and-file employee; the prior-plan test for the contributions credit | Line 6a counts employees paid at least $5,000 and also decides the Part III caution; no startup costs credit with no eligible non-highly compensated employee; a prior plan zeroes lines 5 and 6g in every year | Keep (1) and (2); (3) is the weaker reading | Partly | Medium | Small employers starting a retirement plan | Refusal of a credit (under-claim) if (3) is wrong; over-credit if (1) is | IRC 45E(c)(2), (d)(1)(B), (f)(4), pp. 273-275; Form 8881 (Rev. December 2025) p. 1 | `form8881: /writableForm8881Line6aEmployeesPrecedingTaxYear` |
| CR-17 | Form 8936 lines 6 and 9 (Schedule A copies) | Does the IRC 30D(f)(10) MAGI limitation deny the Schedule-A-copies business-use AND personal-use amounts? | Yes to both: each is $0 when the shared both-years MAGI test fails, matching the scalar arm's own gate | Keep; both halves fixed, nothing left open | Yes | High | Filers entering Schedule A (Form 8936) vehicle copies whose MAGI exceeds the threshold both years | Under-tax (an unenforced denial) if this call is wrong | IRC 30D(f)(10)(A), (c)(1), (c)(2); 2025 Instructions for Form 8936, "Part I-MAGI Amount" | `form8936: /form8936PartIIBusinessUseCreditFromScheduleA`, `/form8936PartIIIPersonalUseCreditFromScheduleA` |
| CR-37 | Form 8881 line 6c | The per-employee contribution cap in the third plan year | Cap at $1,333.33 (the statute's $1,000 credit at 75%), not the printed $1,334 | Follow the statute | Yes | Low | Small employers in the third year of a new plan with employees above $1,000 | Over-credit of $0.50 per employee if the printed figure were used | IRC 45E(f)(2)(A), (f)(3); Instructions for Form 8881 (Rev. December 2025) p. 4 | `form8881: /writableForm8881Line6cCappedEmployerContributions` |
| OT-03 | Form 8960 | Citizen married to a nonresident alien, joint return without the NIIT election | Separate figures for NIIT, $125,000 threshold (partly built) | Keep | Yes | High | Mixed-residency couples | Under-tax | 26 CFR 1.1411-2, p. 63; Form 8960 instructions (2025) p. 23 | `form8960: /niitThreshold` |
| OT-01 | Form 6251 | ISO basis and Part III refigure not built | Refuse when evidenced and AMT-exposed | Keep | Yes | High | ISO holders who sold, AMT capital gain differences | Refusal | Form 6251 instructions (2025) pp. 4, 13 | `form6251: /knockoutAmtPart3RefigureUnbuilt` |
| OT-02 | Form 6251 line 2l | Must straight-line rental property be refused for AMT? | No; only accelerated methods are refused | Keep | Yes | High | Rental owners in AMT range | Under-tax | Form 6251 instructions (2025) p. 5 | `form6251: /knockoutAmtUnmodeledPreference` |
| OT-04 | Form 8828 / Schedule 2 | Subsidy questions unanswered; month counts | Recapture incomplete until answered; months derived from dates | Keep | Yes | High | Federally subsidized mortgage sellers | Either | Form 8828 (Rev. 12-2024) | `form8828: /form8828SubjectToRecaptureTax` |
| OT-05 | Form 5329 lines 1-2 | Is the Form 8915-F line 32 amount entered before or after the Form 5329 exceptions? | Before (gross): it goes on line 1, exceptions on line 2; the age 59 1/2 exception is applied for an owner who was 59 1/2 all year | Keep | Yes | High | Filers who did not repay a disaster home-purchase distribution | Over-tax if read as net | Form 8915-F instructions (2025) p. 26; Form 5329 instructions (2025) p. 5 | `form5329: /form5329PrimaryFilerDerivedException12Amount` |
| OT-06 | Form 8828 / IRC 143(m)(8)(C) | A transfer to a current spouse (not incident to divorce) with no gain or loss under section 1041: recapture? | No recapture (the statute covers any section 1041 transfer) | Keep | Yes | High | Owners who transfer a subsidized home to a spouse | Recapture charged that the statute bars (if narrowed) | IRC 143(m)(8)(C); Form 8828 instructions (Rev. November 2024) p. 1 | `form8828: /form8828SubjectToRecaptureTax` |
| OT-07 | Form 8938 | Any-time reporting threshold for a part-year specified individual | Whole-year aggregate kept (conservative, over-refusal only); part-year window not built, no intake exists | Keep until the part-year intake is built | Yes | Medium | Part-year specified individuals near the threshold | Over-refusal only (asked to file when not required); no under-refusal | Treas. Reg. 1.6038D-2(a)(9) | `form8938: /form8938ComputedMaximumValue` |
| OT-09 | Form 965-A Part I and Part II | A 2025 increase to an installment net 965 tax liability: is it always prorated over the installments? | Not when the filer answers that it is a deficiency due to negligence, intentional disregard or fraud; then the whole increase is paid in 2025. Unanswered takes the general proration | Keep | Yes | High | Filers paying a net 965 tax liability in installments whose liability was increased by an examination | Under-payment in 2025 if a culpable deficiency were prorated | IRC 965(h)(4); Instructions for Form 965-A (Rev. January 2021) p. 3 | `form965A: /form965ALiabilities/*/catchUpDue` |
| OT-10 | Form 6251 Who Must File | Statement 4 needs line 7 figured without lines 2c through 3: how, on a Part III return? | Refigure lines 4 to 6 and take line 7 at the 26 and 28 percent rates, an upper bound; attach when it exceeds line 10 and lines 2c through 3 are negative | Keep | Yes | Medium | Filers with negative AMT adjustments (for example an ATNOLD or a negative line 3) | Over-attachment only on Part III returns; no amount moves | Instructions for Form 6251 (2025) p. 1 | `form6251: /amtWhoMustFileStatement4` |
| IN-150 | Schedule H lines 1, 3, 5 and 15 | Do qualified parking and commuter cash reimbursements leave a household employee's wages, for FUTA too, and before the $2,800 test? | Yes: up to $325 a month each (capped at twelve months for the year) leaves the wages for the $2,800 test and lines 1, 3, 5 and 15; more than the wages refuses | Keep | Yes | Medium | Household employers who reimburse parking or commuting in cash | Under-tax if the monthly limit was exceeded in some months | Instructions for Schedule H (2025) p. 5; IRC 3121(a)(20), 3306(b)(16) | `scheduleH: /householdEmployees/*/transportationReimbursementExclusion` |
| IN-151 | Schedule H lines 1, 3, 5 and 15 | Is an F, J, M or Q nonimmigrant household employee (an au pair), or one covered by a totalization agreement, on Schedule H? | Statute over the printed lists: F/J/M/Q visa-purpose service is off lines 1, 3, 5 and 15; totalization-covered wages are off lines 1, 3 and 5 only | Keep | Yes | High | Household employers of au pairs and of foreign-covered workers | Under-tax if the filer answers Yes wrongly | IRC 3121(b)(19), 3306(c)(19), 3101(c), 3111(c) | `scheduleH: /householdEmployees/*/isExcludedFromSocialSecurityAndMedicareWages` |
| IN-152 | Schedule H lines 1, 3, 5 and 15 | A household employee whose taxes go on the filer's business Form 941/943/944 or are paid by a section 3504 agent | Taken off Schedule H per employee, so the taxes are not assessed twice | Keep | Yes | High | Business owners who report household staff with their business payroll; home care recipients with an agent | Under-tax only if the taxes were in fact not reported elsewhere | Instructions for Schedule H (2025) pp. 2, 9-10 | `scheduleH: /householdEmployees/*/taxesReportedOnBusinessReturnOrByAgent` |
| IN-250 | Schedule H (the whole form), Schedule 2 line 9 | A joint return on which both spouses employ household workers: how many Schedules H, and what each prints | One Schedule H per employer spouse, each with that spouse's name, SSN, employees, line 7, lines 10-14 and line 17 rows; lines A and B read per schedule, lines C/9 and 27 print the return's one answer; Schedule 2 line 9 is the two line 26 amounts added | Keep | Yes | High (two schedules); Medium (line B per schedule) | Married couples filing jointly who both employ household workers | None: the combined tax is unchanged; the risk is a mismatched printed schedule | Instructions for Schedule H (2025) pp. 3-4; Schedule H (2025) lines A-C, 26-27 | `scheduleH: /filersFilingScheduleH`, `scheduleH: /filers/*/scheduleHLineB`, `scheduleH: /filers/*/scheduleHLine26` |
| IN-251 | Schedule H line 17 | More than two states on line 17 | The first two rows print on the form; the rest print on an attached statement in the line 17 column format, headed with the form, line, name and SSN; line 18 totals include every row | Keep | Yes | High | Household employers who paid unemployment contributions to three or more states | None: the totals already count every row | Instructions for Schedule H (2025) p. 6 | `scheduleH: /filers/*/scheduleHFutaStateContributions` |
| OT-08 | Form 8912 | Where a pre-2008 QZAB credit sits in the CREB/54A/54AA limitation order | Old-QZAB first (ignores all others), then CREB, then qualified tax credit bonds, then BAB; total credit unaffected, only the deduction/carryforward split could move | Built: line 12 is split between the bond kinds in this order; within one kind the filer splits it | Yes | Medium | Filers holding more than one bond-credit type | Deduction-vs-carryforward split only; no total moves | IRC 1397E(c)(2), (k); IRC 54(c)(2); IRC 54A(c)(1)(B); IRC 54AA(c)(1)(B) | `form8912: /form8912Bonds/*/allocatedAllowedCredit` |
| PP-01 | Form 2210 / Form 2210-F | Combat zone or contingency operation, underpayment penalty | Leave the penalty line blank and let the IRS figure it; refuse only a filer who must file Form 2210 with a penalty | Leave the penalty line blank for these filers and let the IRS figure it | Yes | Medium | Service members and spouses | Refusal | IRC 7508(a); Form 2210 instructions (2025) p. 1 | `form2210: /form2210CombatZoneIrsFiguresPenalty` |
| PP-02 | Form 1040 line 25c / Form 1042-S | Which box is the withholding credit? | Box 10 only; refuse boxes 7b, 7c and 11 | Box 11 is never the credit; keep the refusal until its income treatment is settled | Yes | Medium | Form 1040 filers with a Form 1042-S | Refusal (or over-credit if box 11 were counted) | IRC 1462; Form 1042-S instructions (2025) p. 29; Pub. 519 (2025) p. 43 | `form1042S: /form1042SWithholding` |
| IN-100 | Form 2210 Schedule AI lines 14 and 16 | Where do the Form 4972, Form 8814 and alternative minimum taxes go, and are they annualized? | Line 16, entered by period: AMT on annualized period income before the exemption, Form 4972 and Form 8814 by the period of the event; column (d) must equal the annual taxes; line 14 no longer refuses | Keep | Yes | Medium | Box C filers with a lump-sum distribution, a Form 8814 child or AMT | Under-penalty if an early period is understated | Form 2210 instructions (2025) p. 10; Form 2210 (2025) p. 3; Pub. 505 (2025) p. 26 | `form2210: /form2210ScheduleAiPart1AttestationsConsistent` |
| IN-180 | Schedule C line 30, simplified method (Pub. 587 part-year use) | Which date starts the month count when business use of the home begins during the year? | The home first-use date, which holds when unanswered (the business-start floor was removed, amended 2026-10-05); a month counts with at least 15 days of use | Keep | Yes | High (rule), Medium (floor) | Simplified-method filers who began or stopped home use during the year | Over- or under-deduction of a few months | Pub. 587 (2025) pp. 11-12, Example 1 | `scheduleC: /scheduleCs/*/simplifiedMethodPartYearMonthsQualifying` |
| IN-181 | Schedule C line 30, Simplified Method Worksheet line 3c | Is the $5 rate times the daycare decimal rounded before line 4? | Yes, to the cent (an exact half cent to the even cent); line 5 keeps cents (amended 2026-10-05) | Keep | Yes | High | Simplified-method daycare filers not using the space exclusively | Up to $1.50 of deduction | Instructions for Schedule C (2025) p. 11 | `scheduleC: /scheduleCs/*/simplifiedMethodLine3cRate` |
| IN-182 | Form 8829 lines 10-17 | Where does the business part of the home's mortgage interest and real estate taxes go? | Standard deduction: lines 16 and 17, under the income limit; itemizer: lines 10 and 11 with the personal part on Schedule A (IN-220) | Keep | Yes | High | Regular-method home-office filers with a mortgage or real estate taxes | Under-tax (double deduction, or an uncapped amount) | Instructions for Form 8829 (2025) pp. 3-4 | `scheduleC: /scheduleCs/*/form8829StandardDeductionMortgageInterestAndTaxes`, `form8829: /knockoutForm8829ItemizerMortgageInterestAndTaxesNotSplit` |
| IN-190 | Schedule C line 9, business parking fees and tolls | Under the actual-expense method, are business parking fees and tolls prorated with operating costs? | No: added in full under either method; only operating costs take the business-use share | Keep | Yes | High | Schedule C filers deducting actual car expenses with business parking or tolls | Under-deduction of the personal-use share of parking and tolls | Instructions for Schedule C (2025) p. 6; Pub. 463 (2025) ch. 4 | `scheduleC: /scheduleCs/*/carTruckExpenses` |
| IN-183 | Schedule C line 30 (Simplified Method Worksheet line 1; Form 8829 line 8) | How is the gross income limitation of the business use of the home figured? | Asks whether all income is from the home (required); line 29 + home-use gain - unrelated loss, or the home-use share of gross income - line 28 - unrelated loss; blank gain or loss is $0 | Keep | Yes | High (arithmetic), Medium (blank loss) | Home-office filers with income from another place, or with a Form 8949 / 4797 gain or loss | Under-tax if an unrelated loss is not reported | Instructions for Schedule C (2025) p. 11; Instructions for Form 8829 (2025) p. 2 | `scheduleC: /scheduleCs/*/homeOfficeGrossIncomeLimitation` |
| IN-184 | Form 8829 lines 41-42, home first used for business 1981-1986 | Can line 42 be computed from Pub. 534? | Yes for a home in business use all year: line 40 x 2.2% (45-year alternate elected) or $0; a cessation year keeps the filer's figure | Keep | Yes | Medium | Regular-method filers with a pre-1987 home | Over- or under-deduction if the election answer is wrong | Instructions for Form 8829 (2025) p. 5; Pub. 534 (Rev. 11-2016) p. 19 | `scheduleC: /scheduleCs/*/form8829Pub534IsModeled` |
| IN-210 | Form 2210 Part I line 2 and Schedule AI line 16, household employment taxes | When are Schedule H taxes left out of the estimated-tax penalty base? | When nothing is withheld (Form 1040 line 25d is zero) and, without them, line 4 less line 6 is under $1,000 or the no-liability exception holds; the section 6654(e)(3) waivers and the section 6654(d) safe harbors do not count | Keep | Yes | High | Household employers with no income tax withholding and a small income tax | Over-penalty only, if a waiver would have applied | IRC 3510(b)(2), 6654(e); Instructions for Form 2210 (2025) p. 2; Instructions for Schedule H (2025) p. 8 | `estimatedPayments: /form2210HouseholdEmploymentTaxesLeaveTheBase`, `estimatedPayments: /form2210HouseholdEmploymentTaxesOnLine2` |
| IN-220 | Form 8829 lines 10, 11, 16, 17; Schedule A lines 5b, 8a | How is an itemizer's home mortgage interest and real estate tax split between Form 8829 and Schedule A? | Enter once on Form 8829; business part (debt-limit fraction to line 10, rest line 16; Line 11 Worksheet to line 11, rest line 17) on Form 8829, personal part added to Schedule A 5b and 8a; the worksheet iteration refused | Keep | Yes | High (split); Medium (proportional debt limit with two homes) | Itemizers with a regular-method home office and a mortgage or real estate taxes | Over- or under-tax (double deduction; wrong tier) | Instructions for Form 8829 (2025) pp. 3-4; Pub. 587 (2025) pp. 18-19 | `scheduleC: /scheduleCs/*/form8829Line10DeductibleMortgageInterestBusinessPart`, `form8829: /scheduleCs/*/form8829Line11WorksheetRealEstateTaxesOnLine11`, `scheduleC: /form8829PersonalHomeRealEstateTaxesTotal` |
| PR-01 | Several lines (Forms 8814, 8839, 8863, 8815, 8615, 2555, Sch. A) | Amount times a ratio: round once or twice? | To the cent, then to the dollar | Keep; make Form 2555 line 36 match | Yes | Medium | Filers at a half-dollar boundary | $1 either way | Form 1040 instructions (2025) p. 23 | `form8814: /form8814Children/*/line9QualifiedDividendsIncluded` |
| PR-02 | Schedule 2, typed lines | Printed box vs amount added to the total | Print the amount actually added (floored at $0) | Keep | Yes | High | Filers with typed "other tax" entries | Print error only | No IRS text | `schedule2: /schedule2Line17zAnyOtherTaxesPrinted` |
| PR-03 | Form 2555 line 35 | "Rounded to at least three places": how many places, and which way? | Exactly three places, half up, rounded once from the exact quotient | Keep | Yes | High | Form 2555 filers with employer-provided housing amounts | $1 either way on line 36 | Form 2555 (2025) p. 3 | `form2555Housing: /form2555Line35EmployerProvidedRatioThousandths` |
| IN-300 | Form 5695 exterior doors, joint occupancy | Separate door shares and raw payment normalization | Apply each $250 door limit to that same door payment fraction; retain existing category policy pending review | Bounded candidate; category and subcent questions open | No family acceptance | High | Joint occupants with exterior doors | SC-06 category trigger and SC-07 subcent rounding remain unresolved | IRC 25C(b)(4); Instructions for Form 5695 (2025) p. 3; Form 1040 instructions (2025), Rounding Off to Whole Dollars | `form5695: /form5695DoorAllocatedCreditTotal` |
| IN-301 | Schedule 1 line 20 with a section 501(c)(18) deduction (line 24f) | Where does the 501(c)(18) deduction enter the IRA limit, and is it added back to modified AGI? | Statute order: phase out the full deductible amount ($10 rounding, $200 floor), take the lesser of that and compensation, then subtract the allowable 501(c)(18) deduction (never below $0); modified AGI adds the line 24f deduction back; a 501(c)(18) contributor is an active participant | Keep | Yes | High | Filers in a pre-June-25-1959 employee-funded 501(c)(18) plan (W-2 box 12 code H) | Over-tax if wrong; the IRS worksheets give a lower modified AGI and a larger deduction | IRC 219(b)(1), (b)(3), (e)(2), (g)(1), (g)(3)(A)(ii), (g)(5)(B), pp. 949-951; Pub. 590-A (2025) pp. 9-11, 16 | `iraDeduction: /iraProratedDeductionLimitNetOf501c18` |
| IN-302 | Schedule 1 line 20, married filing jointly | Does the IRA Deduction Worksheet's combined compensation (line 10) let the higher-paid spouse deduct above that spouse's own compensation? | No: each spouse is capped at that spouse's own compensation; only the spouse with less compensation adds the other spouse's compensation, reduced by that spouse's IRA deduction, designated nondeductible contribution and Roth contribution | Keep | Yes | High | Joint filers where the higher-paid spouse is 50 or older with compensation from $7,000 to below $8,000 | Over-tax if wrong; the pooled reading gives up to $1,000 more deduction | IRC 219(b)(1)(B), (c)(1)-(2), (f)(2), p. 949; Pub. 590-A (2025) pp. 9, 11 | `iraDeduction: /primaryFilerTraditionalIraDeductionAllowable` |
| IN-303 | Schedule 1 line 20: alimony as IRA compensation | Is all taxable pre-2019 alimony (Schedule 1 line 2a) compensation, or only alimony under a decree? | Only payments under a decree of divorce or separate maintenance, or a written instrument incident to one (former section 71(b)(2)(A)), executed before 2019 and not modified to adopt the 2017 repeal; a written separation agreement or a support decree is not compensation; computed per spouse | Keep | Yes | High | Recipients of pre-2019 alimony under a separation agreement or support decree | Under-tax if wrong (the instructions' reading counts more compensation) | Former IRC 219(f)(1) last sentence and its 2017 effective-date note; former IRC 71(b)(2) (2016 ed.); Pub. 590-A (2025) p. 7 | `iraDeduction: /primaryFilerIraCompensation` |
| IN-304 | Form 8606 line 1: the difficulty-of-care increase (IRC 408(o)(5)) | Is the increased nondeductible limit capped in total? | Yes: the increase (lesser of the excluded payments and the deductible amount less compensation) raises only the compensation side of Form 8606 line 1, which never exceeds the deductible amount; line 1 is that side or the contributions, whichever is smaller, minus the deduction taken (amended 2026-10-04) | Keep | Yes | High | Foster-care providers with excluded difficulty-of-care payments, married filing jointly | Over-contribution allowed without excise if wrong | IRC 408(a)(1), 408(o)(5); Pub. 590-A (2025) p. 15 | `form8606: /form8606DifficultyOfCareLimitIncrease` |
| IN-305 | Form 5329 lines 10 and 15, the spouse with less compensation | What is that spouse's section 4973 allowable amount? | The section 219(c) limit computed without section 219(g), reduced by the other spouse's allowed deduction, designated nondeductible contribution and Roth contribution, not by the other spouse's raw contribution | Keep | Yes | High | Joint filers where the higher-paid spouse has an undesignated excess | Excise wrong either way if wrong | IRC 4973(b)(1)(B) and flush sentence; IRC 219(c)(1)(B)(ii) | `form5329: /spouseForm5329Line10TraditionalIraUnusedLimit` |
| IN-306 | Form 5329 line 11: earnings on a contribution returned by the due date | Do the earnings returned with a section 408(d)(4) distribution reduce the excess on line 11? | No: section 408(d)(4) takes the distribution out of section 408(d)(1) and taxes the earnings under section 61 in the contribution year; line 11 counts only section 408(d)(1) inclusions; no intake for the earnings exists today | Keep | Yes | High | Filers who withdrew a contribution with earnings before the due date | Excess misstated if wrong | IRC 408(d)(4); IRC 4973(b)(2)(A) | `form5329: /form5329Line15ReturnedContributionOrZero` |
| IN-307 | Schedule SE and Schedule 1 line 15, and the IRA worksheet line 9 that reads them | Cents or whole dollars? | Whole dollars on every printed Schedule SE line (products figured to the cent first, then the line rounded half-up, away from zero); Schedule 1 line 15 adds each filer's rounded line 13; IRA worksheet line 9 subtracts the printed lines 15 and 16 and rounds only its own total | Keep | Yes | High | Every return with self-employment tax | About $1 on AGI or line 15 | Form 1040 instructions (2025) p. 23, Rounding Off to Whole Dollars; PR-01; IN-285 | `scheduleSE: /primaryFilerSelfEmploymentTaxDeduction` |
| IN-308 | Schedule 1 line 20 / IRA Deduction Worksheet lines 8 and 9: foreign-government wages with no Form W-2 | Counted once as wages, or once as self-employment earnings net of the half-SE-tax deduction? | Once, as wages on line 8; line 9 leaves them out. This is the IRA compensation placement under IRC 219; CR-09's EIC placement under IRC 32 is a different concept and stays | Keep | Yes | Medium | U.S. citizens paid by a foreign government or international organization without a W-2 who contribute to an IRA | Over-deduction of at most the half-SE-tax share if wrong | IRC 219(b)(1)(B), 219(f)(1); Pub. 590-A (2025) p. 6; AD-30 | `iraDeduction: /primaryFilerIraCompensation` |
| IN-309 | Schedule 1 line 20: a prior-year excess deducted this year (IRC 219(f)(6)) with Roth contributions under the phaseout | Does a Roth contribution use up the phased deduction room for the deemed contribution? | No. The deemed part is the least of the prior excess, the phased limit less traditional contributions, and the unphased limit less traditional and Roth contributions; any absorbed remainder becomes Form 8606 line 1 basis | Provisional | Yes | Medium | Covered filers in the phaseout band with a prior-year excess and Roth contributions | Over-deduction of up to the Roth amount if wrong | IRC 219(f)(6), 219(g)(1), 4973(b)(2)(C) and flush sentence, 408A(c)(2); Pub. 590-A (2025) Worksheet 1-5; Form 5329 and Form 8606 instructions (2025) | `iraDeduction: /primaryFilerSection219f6PriorYearExcessDeduction` |
| IN-310 | Form 8829 lines 6 and 7 | Exact ratio or the printed two-decimal percentage? | The exact ratio | Keep | Yes | High | Daycare filers using part of the home | Cents | IRC 280A(c)(4)(C); Pub. 587 (2025) | `scheduleC` |
| IN-311 | Form 8829 line 33 limited; line 31 carryover | Order of casualty and depreciation in a limited line 33, and the casualty share of a carryover | Casualty first, depreciation last; a blank casualty share of the carryover reads $0 (IN-296) | Keep | Yes | Medium | Home-office filers with a casualty and a limited deduction | Schedule C line 30 and SE tax | Pub. 587 (2025) | `scheduleC` |
| IN-312 | Form 4562 section 179 limit with a home office | Which limit is figured first when each depends on the other? | Pub. 946's eight-step procedure, with the home-office deduction as the other deduction | Keep | Yes | Medium | Section 179 electors whose business-income limit binds and who have a home office | Section 179 allowed and carried | IRC 179(b)(3)(C), 280A(c)(5); Instructions for Form 4562 (2025); Pub. 946 (2025) | `scheduleC` |
| IN-313 | Schedule SE, community income | Scope of the separate-return add-back | Built for a business one spouse carries on, on separate returns; no add-back for registered domestic partners or under IRC 66(a); IRC 66(b) per IN-55; a business both spouses operate splits SE income by distributive shares on any filing status (amended 2026-10-05) | Keep | Yes | High | Married filers in community-property states | SE tax | IRC 1402(a)(5), 66, 879(a)(2); Pub. 555 | `scheduleSE` |
| IN-314 | Schedule C line 30 simplified method, spouses in one home | One 300 square foot cap or one each? | One each, for different portions of the home | Keep | Yes | High | Spouses each with a home business | Up to $1,500 | Rev. Proc. 2013-13 section 4.08(5); Pub. 587 (2025) | `scheduleC` |
| IN-315 | Schedule C excluded under IRC 933 (Puerto Rico) | How the excluded profit appears on Form 1040 | Schedule C computed and attached for Schedule SE and Form 7206; line 31 left off Schedule 1 line 3 | Provisional | Yes | Medium | Bona fide Puerto Rico residents with a business | Presentation only | IRC 933; Pub. 570 (2025) | `scheduleC` |
| IN-316 | Schedule C, section 195 start-up costs | Election left unanswered | The deduction is taken (capitalizing is the affirmative election) | Keep | Yes | High | New businesses with start-up costs | Up to $5,000 plus amortization | IRC 195(b); Pub. 535; Instructions for Form 4562 (2025) | `scheduleC` |
| IN-317 | Form 8829, daycare room not used exclusively | Direct expenses at 100% or by the time ratio? | By the time ratio (confirms the build and IN-182) | Keep | Yes | High | Daycare providers | Direct expenses | IRC 280A(c)(4)(C); Pub. 587 (2025) | `scheduleC` |
| IN-318 | Form 4562 section 179, active conduct | Does line G No mean the business is not actively conducted? | No: ask about meaningful participation when line G is No and section 179 is elected; unanswered holds | Keep | Yes | High | Section 179 electors who did not materially participate | Section 179 allowed | Instructions for Form 4562 (2025); Pub. 946 (2025) | `scheduleC` |
| IN-319 | Form 1040 line 4b, QCD from a SEP or SIMPLE IRA | Is a plan with no employer contribution this year excluded? | Only an ongoing plan is excluded (IRC 408(k)(2) makes SEP status year by year) | Keep | Yes | Medium | QCD donors with a SEP or SIMPLE IRA | The QCD amount | IRC 408(d)(8)(B), 408(k)(2); Pub. 590-B (2025) | `form1099Rs` |
| IN-320 | Form 5329 line 2, code 1D form | Is terminal illness an exception for a nonqualified annuity? | No: IRC 72(q)(2) has no terminal-illness exception; the 10% applies | Keep | Yes | High | Terminally ill annuity owners under 59 1/2 | 10% of the taxable amount | IRC 72(q)(2), 72(t)(2)(L); Pub. 575 (2025) | `form1099Rs` |
| IN-321 | Simplified Method table | Age at the annuity starting date with a fraction | Completed years | Keep | Yes | Medium | Retirees starting an annuity at a fractional age near a band edge | Recovery per year | IRC 72(d)(1)(B)(iv); Pub. 575 (2025) | `form1099RFrontier` |
| IN-322 | Form 5329 line 2, IRC 72(q)(2)(G), (I) or (J) | Which exception number? | Exception 16 (the i5329 entry names Pub. 575's additional annuity exceptions) | Keep | Yes | Medium | Nonqualified annuity owners | Print only | Instructions for Form 5329 (2025); Pub. 575 (2025) | `form1099Rs` |
| IN-323 | Form 1040 line 4b, QCD above the annual ceiling with basis | Does the excess take a share of Form 8606 basis? | No: the excess is fully taxable and stays off Form 8606 line 7 (IN-230) | Keep | Yes | Medium | QCD donors above the ceiling with basis | Timing of basis recovery | IRC 408(d)(8)(D); Pub. 590-B (2025) | `form1099Rs` |
| IN-324 | Form 1040 line 5b, public safety officer premiums | What caps the exclusion in 2025? | The instructions' taxable-amount cap; the statute's later-year adjustment is not modelled | Keep | Yes | Medium | Retired public safety officers | No 2025 effect | IRC 402(l)(3)(B); Form 1040 instructions (2025) | `form1099Rs` |
| IN-325 | Form 1040 line 4c statement | Counted per distribution or per return? | Per return | Keep | Yes | High | Filers with several line 4c exceptions | Print only | Form 1040 instructions (2025) | `form1099Rs` |
| IN-326 | Form 1040 line 4a, a 2025 Form 1099-R coded JP | Report the returned Roth excess on 2025 line 4a? | No: leave it off the 2025 return | Keep | Yes | Medium | Filers who withdrew a 2025 Roth excess in 2026 | Print only | Instructions for Form 8606 (2025) | `form1099Rs` |
| IN-327 | Form 1040 line 4b, QCD age | When does an owner reach 70 1/2 for a QCD? | Six calendar months after the 70th birthday (the last day of that month when the day does not exist); computed, not refused | Provisional | Yes | Medium | QCD donors born July 1954 to June 1955 | The QCD exclusion | IRC 408(d)(8)(B)(ii); Treas. Reg. 1.401(a)(9)-6 (by analogy) | `form1099Rs` |
| IN-328 | Form 8880 line 4, IRA code 4 distributions | Does a beneficiary's distribution count? | A surviving spouse's counts; a non-spouse beneficiary's does not; the question is asked only when it matters, and unanswered holds; QCDs and section 408(d)(5) returns count; military retirement pay does not | Keep | Yes | High | Saver's credit claimants with an inherited IRA distribution | Saver's credit | IRC 25B(d)(2); Form 8880 (2025) | `form1099Rs` |
| IN-329 | Schedule C line 1, Form 1099-NEC box 1 above line 1 | What happens with no explanation? | Compute from line 1 as entered; the explanation statement is required, and an unanswered statement holds the return | Keep | Yes | High | Schedule C filers whose 1099-NEC totals exceed line 1 | None if explained | Instructions for Schedule C (2025), line 1 | `scheduleC` |
| IN-331 | Form 8606 line 1 and Schedule 1 line 20 | How is the election to treat a contribution as nondeductible expressed? | A Form 8606 line 1 designation is the election: the deduction taken is the lesser of the allowable deduction and (the smaller of the compensation side and the contributions) less the designation, never below zero; an elected-deduction amount is the complementary expression; both given must agree within $1, else a reasoned refusal; neither given means the full allowable deduction; a designation above the most that can be designated is refused | Keep | Yes | High | Traditional IRA contributors who designate nondeductible contributions | A mis-entered line 1 reduces the deduction instead of refusing | IRC 408(o)(2)(B)(ii), (C)(ii); Instructions for Form 8606 (2025), Line 1; Form 1040 instructions (2025); Pub. 590-A (2025) | `iraDeduction: /primaryFilerTraditionalIraDeduction` |
| IN-332 | Form 4562 section 179 with home offices in several businesses | How do Pub. 946's eight steps run, and how is section 179 allocated? | Steps 1, 5 and 7 on aggregate income including wages; steps 4 and 8 per business; the filer's allocation governs, else Pub. 946's equal-per-property default (computes) | Provisional | Yes | Medium | Section 179 electors with several businesses and a home office | The split between section 179 and home-office carryovers, and each business's line 31 | IRC 179(b)(3), 280A(c)(5)(B)(ii); Pub. 946 (2025); Instructions for Form 4562 (2025) | `scheduleC` |
| IN-333 | Schedule C, section 195 costs in the year of disposal | How is the remaining balance split? | The whole unamortized balance is deducted; amortization runs through the month of disposition and the rest is an ordinary deduction; a sale's effect is open | Keep | Yes | Medium | Owners who close a business with unamortized start-up costs | Line placement only (the total is fixed) | IRC 195(b)(2), 165(c)(1) | `scheduleC` |
| IN-334 | Schedule C, section 195 for a reopened business | Does reopening start a new first-year amount? | No: "began" is first operation; reopening costs are current expenses; the 180 months are not suspended (provisional) | Provisional | Yes | Medium | Owners who reopen a dormant business | Up to $5,000 of first-year deduction | IRC 195(b)(1), (c)(1)(A)(ii); Instructions for Schedule C (2025) | `scheduleC` |
| IN-335 | Form 4972 lines 24 and 27, the tax from the Tax Rate Schedule | Cents, or whole dollars before line 25 and line 28 multiply by 10? | Whole dollars: figure each line to the cent from the schedule, round the printed line half-up, and multiply the printed amount by 10 (the IN-307 pattern) | Keep | Yes | Medium | Form 4972 filers (participants born before January 2, 1936, and their beneficiaries) | Up to $5 on lines 25, 28, 29 and 30 | Form 4972 (2025) lines 24-28; Instructions for Form 1040 (2025), Rounding Off to Whole Dollars; IN-307 | `form1099RFrontier` |
| IN-336 | Form 5329 lines 15-17, a payment to an inherited IRA | Is a payment that IRC 219(d)(4) makes nondeductible an excess contribution? | Yes: it is an amount contributed under IRC 4973(b)(1)(A) with $0 allowable under (B), so the whole payment is excess; it also counts as contributed in IRC 4973(b)(2)(C) and IRC 219(f)(6)(A); a trustee-to-trustee transfer of the decedent's balance is not a contribution | Keep | Yes | High | Non-spouse beneficiaries who pay new money into an inherited IRA | 6% excise on the payment | IRC 219(d)(4), 4973(b), 219(f)(6); Instructions for Form 5329 (2025) lines 15-17 | `iraDeduction: /primaryFilerSection4973CurrentYearExcess` |
| IN-337 | Schedule 1 line 24f, the 25% limit of IRC 219(b)(3)(B) | Which compensation is the 25% base? | Section 415(c)(3) compensation from the employer maintaining the 501(c)(18) plan that is includible in gross income: W-2 box 1 of the W-2s that report code H; not the section 219(f)(1) IRA compensation (combat pay, alimony and stipends are out); provisional for several employers | Provisional in part | Yes | Medium | 501(c)(18) participants with combat pay, alimony, stipends or a second employer | The allowed line 24f amount and the line 24f refusal | IRC 219(b)(3)(B), 219(f)(1), 219(f)(7), 415(c)(3) | `iraDeduction: /primaryFiler501c18AllowedDeduction` |
| IN-338 | Schedule 1 line 20, the spousal limit of IRC 219(c) | Does term (I) take the spouse's whole section 219(a) deduction? | Yes: the spouse's IRA deduction including any section 219(f)(6) amount, plus the spouse's allowed 501(c)(18) deduction | Keep | Yes | High | Married couples filing jointly where the higher earner has a 501(c)(18) deduction or a section 219(f)(6) deemed contribution | The lower earner's deduction and Form 5329 excess | IRC 219(c)(1)(B)(ii)(I), 219(e)(2), 219(f)(6) | `iraDeduction: /primaryFilerSpousalCombinedCompensation` |
| IN-339 | Form 1040 lines 4a-4c, a QCD whose exclusion the post-70½ deduction offset reduces | Is the distribution still reported under Exception 3? | Yes: it is still a qualified charitable distribution under IRC 408(d)(8)(B); line 4a is the total, line 4b is the amount includible after the offset (not -0-), and box 2 on line 4c is checked | Keep | Yes | High | QCD donors who deducted IRA contributions after age 70½ | Line 4a reported, line 4b the includible amount | IRC 408(d)(8)(A)-(B); Instructions for Form 1040 (2025), lines 4a and 4b, Exception 3; Pub. 590-B (2025), Jim's example | `form1099Rs` |
| IN-340 | Schedule 1 line 20, spousal limit term (III), a Roth contribution returned by the due date | Does a Roth contribution returned in a section 408(d)(4) distribution still count as a contribution on behalf of the spouse? | No: it is treated as never contributed, per the Instructions for Form 8606 (2025); the statute is silent on term (III), so the instruction governs | Keep | Yes | Medium | Married couples where one spouse's Roth contribution was returned by the due date | The other spouse's spousal limit | IRC 219(c)(1)(B)(ii)(III), 408(d)(4), 4973(f); Instructions for Form 8606 (2025) | `iraDeduction: /primaryFilerRothIraContributionReturnedByDueDateOrZero` |
| IN-330 | Schedule C line 6, a positive section 481(a) adjustment | Computed spread or filer figure? | The filer enters this year's portion; no computed spread and no hold | Keep | Yes | Medium | Filers changing an accounting method with a positive adjustment | Line 6 income | Instructions for Schedule C (2025), line 6; Pub. 946 (2025) | `scheduleC` |

## General conventions

### GEN-01 — An unanswered question the filer never reached never blocks the return

**The question.** The software asks about hundreds of possible situations. Most filers never see most of the
questions. When a question is left unanswered, should the software assume the common answer (usually "no" or
$0), or wait for an answer?

**What the software does.** A question the filer never reached (because nothing they entered leads to it)
never stops the return. But once the filer has entered a document or opened a part of a form, a required box
left blank in it holds the return until it is answered. The software does not fill such a box with a guess.

**Why the owner chose it.** A guessed $0 in a box the filer skipped by mistake files a wrong number silently.
Holding the return is visible and the filer can fix it.

**Our best recommendation.** Keep it. It is the ordinary discipline of a careful preparer: do not sign a
return with a blank the client never explained. Several entries below apply this rule to specific boxes
(IN-02, IN-05, IN-06); a reviewer who disagrees with one of them is really disagreeing with where this line is
drawn.

**What we would like a reviewer to check.** Whether any of the boxes treated as "required once reached" are
ones practitioners routinely treat as zero when blank.

**Where it lives.** Applies across the dictionary. The return-level stop is `flow:/flowIsKnockedOut`; each
module's completeness facts decide what counts as "reached".

### GEN-02 — Refuse, with a reason, rather than estimate an unbuilt population

**The question.** Some situations the software does not yet compute (for example, most general business
credits, the AMT refiguring of capital gains after an incentive stock option exercise, the penalty
postponement for combat-zone service). Should it compute an approximation, or refuse?

**What the software does.** It refuses. A "knockout" fact detects the situation from the filer's own answers
and stops the return with a stated reason. Each knockout names the work that will replace it.

**Why the owner chose it.** The owner's goal for this release is a clear boundary: what the software does, it
does correctly, and the boundary is guarded by refusals.

**Our best recommendation.** Keep it, and publish the list of refusals beside this document so filers and
preparers know in advance what the software will not do. A refusal is costly to the filer turned away, so each
knockout should fire only on the population that is really affected; several entries below (CR-03, OT-01,
PP-01) turn on exactly that question.

**What we would like a reviewer to check.** Whether any refusal is wider than it needs to be, or whether a
simple, correct treatment exists that would serve the filer instead (PP-01 is our own example).

**Where it lives.** Every knockout is a member of `flow:/flowIsKnockedOut`. Besides those named in CR-03, OT-01
and PP-01, examples are `familyAndHousehold:/knockoutNonParentClaimsQualifyingChildOfAnother` (a non-parent
claiming a child who is also another taxpayer's qualifying child, until the tie-breaker questions are built) and
`form8960:/knockoutNiitCfcPficAdjustmentNotModeled` (foreign-corporation adjustments to net investment income).

### GEN-03 — A return where every amount is $0

**The question.** A return can have no income tax, no payments and no credits: every figure is $0. Should the
software refuse it as having nothing to compute, or let it file?

**The IRS text.** Instructions for Form 1040 (2025), page 8: "If you, your spouse with whom you are filing a joint
return, or a dependent was enrolled in coverage through the Marketplace for 2025 and advance payments of the
premium tax credit were made for this coverage, you must file a 2025 return and attach Form 8962."

**What the software does.** It lets the return file. It used to refuse it
(`taxCalculations:/knockoutHasNoPaymentsOrCredits`). That refusal also turned away filers the instructions
require to file, such as a Form 8962 reconciliation that nets to exactly $0. The owner ruled to retire the
refusal, and it is retired: the $0 test is no longer a reason `flow:/flowIsKnockedOut` stops a return. The
narrower HSA rule that also refused a $0 return with HSA distributions is retired too (the Form 8889
instructions say a filer with HSA distributions must file), and with no reader left the $0 test fact itself
is deleted.

**Why the owner chose it.** A $0 return is still a valid return, and some filers must send one.

**Our best recommendation.** Retire it, as ruled. Nothing is lost: a $0 return has no refund and no balance due,
and filing it serves a filer who must file.

**What we would like a reviewer to check.** Whether any other filer with an all-$0 return should be stopped for a
reason other than the amounts.

**Where it lives.** `flow:/flowIsKnockedOut` (the refusal list, which includes no $0 test);
`tests/nodes/ty2025/taxCalculations/all-zero-return-files` (an all-$0 return that files).

## Filing status and dependents

### FS-04 — Custody test: when a child is too old to be "in the custody" of a parent

**The question.** For divorced or separated parents, the special rule that lets the noncustodial parent claim
a child applies only while the child is in the custody of one or both parents. A child emancipated under
state law is treated as living with neither parent. The software needs to know when that happens.

**The IRS text.** Publication 504 (2025), *Divorced or Separated Individuals*, page 9: "Emancipated child. If
a child is emancipated under state law, the child is treated as not living with either parent." Example 5 on
the same page applies it to a child "emancipated under the law of the state where the child lives."

**What the software does.** It asks "Was the child emancipated under your state's law during 2025?" and, if
so, on what date. An emancipation on or before July 2, 2025 takes the child out of the custody test (the
publication's Example 5); a later date leaves the child in a parent's custody for more than half the year. The
question must be answered once the child reaches the age of majority for the child's state or territory of
residence (19 in Alabama and Nebraska, 21 in Mississippi and Puerto Rico, 18 everywhere else); unanswered at
that age, the return waits for the answer rather than assuming 18. An answer given for a younger child (for
example, emancipated by marriage at 17) is honored too. The age table only decides when the question must be
answered.

**Why the owner chose it.** The owner first approved an age-of-majority table decided from one answer, and
after review chose to ask about emancipation directly.

**Our best recommendation — partly differs.** Keep the child's-state rule; it follows Example 5 exactly. But
the publication's test is *emancipation under state law*, and age of majority is only a proxy for it. A child
can be emancipated earlier (by marriage or a court order), and some states extend support or custody past 18
while the child is still in high school. The ages 19 and 21 come from state statutes that are **not among the
documents the maintainers hold**, so this document cannot cite them. We would ask the filer directly ("Was the child
emancipated under your state's law during 2025? If so, on what date?") and use the table only to decide when
to ask.

**The owner's decision after review (2026-09-25).** The owner decided to follow our recommendation. It is
built: "What the software does" above describes the software as it is now.

**What we would like a reviewer to check.** (1) Whether the four exceptions (AL, NE, MS, PR) are complete and
correct for 2025. (2) Whether age of majority is an acceptable stand-in for emancipation for this rule, or
whether preparers ask about emancipation directly.

**Where it lives.** `dependentsBenefitSplit:/familyAndHousehold/*/writableChildEmancipatedUnderStateLaw`,
`dependentsBenefitSplit:/familyAndHousehold/*/writableChildEmancipationDate`,
`dependentsBenefitSplit:/familyAndHousehold/*/childEmancipationDateAfterCustodyMidyear`,
`dependentsBenefitSplit:/familyAndHousehold/*/writableChildResidenceJurisdiction`,
`dependentsBenefitSplit:/familyAndHousehold/*/ageOfMajorityForCustodyTest`,
`dependentsBenefitSplit:/familyAndHousehold/*/childMayQualifyForBenefitSplit`.

### FS-02 — Head of household for a filer widowed during the year who had separated from the spouse

**The question.** A filer's spouse died during 2025. Before the death the two had separated, and the filer
kept up a home for a child for more than half the year. May the filer file as head of household, or only
married filing jointly or separately?

**The competing texts.**
- IRC 2(b)(2)(C) (U.S. Code p. 56): "a taxpayer shall be considered as married at the close of his taxable
  year if his spouse (other than a spouse described in subparagraph (B)) died during the taxable year." Read
  alone, this bars head of household.
- IRC 2(c) (p. 57): "For purposes of this part, an individual shall be treated as not married at the close of
  the taxable year if such individual is so treated under the provisions of section 7703(b)."
- IRC 7703(b)(3) (p. 4038) requires that "during the last 6 months of the taxable year, such individual's
  spouse is not a member of such household".
- 26 CFR 1.2-2(e) (p. 25): "an individual who is considered as not married under section 143(b) shall be
  considered as not married for purposes of determining whether he or she qualifies as a single individual, a
  married individual, a head of household or a surviving spouse under sections 1 and 2 of the Code."
  The historical note to section 7703 (p. 4038) records that "Provisions relating to determination of marital
  status were formerly contained in section 143 of this title".

**What the software does.** Head of household stays available when the section 7703(b) tests are met. For a
filer widowed in the year, the living-apart test is met only if the spouse was not a member of the household
at the time of death **and** at no time from July 1 through the date of death. So a filer who separated in
January and whose spouse died in March qualifies; a filer who lived with the spouse until a March death does
not. The death itself never satisfies the test.

**Why the owner chose it.** An internal review found no way to defeat the statutory chain: section 2(b)(2) is
limited to "this subsection", while section 2(c) applies to "this part", and the regulation applies the
living-apart rule to head-of-household status by name. The owner ruled to build it.

**The strongest objection.** IRS training material and the publications speak of a widowed filer as
"considered married for the whole year" and list only joint or separate filing in the year of death. No IRS
text we found addresses a filer who had separated before the death. The July-1-to-death fence is a
construction, not statute text; it exists to stop the literal 7703(b)(3) reading from giving head of household
to every widow(er) whose spouse died before July 1.

**Our best recommendation.** Keep it. The statute and regulation support it, and the fence keeps it narrow.
Our confidence is medium-low only because the IRS's own teaching material points the other way.

**What we would like a reviewer to check.** Whether practitioners allow head of household in this situation,
and whether the July-1-to-death fence is the right construction.

**Where it lives.** `filers:/filerCouldQualifyForHoh`, `filers:/livedApartLastSixMonths`,
`filers:/spouseDiedInTaxYear`, `filers:/writableDeceasedSpouseInHouseholdJulyToDeath`.

### FS-03 — Qualifying surviving spouse when the spouse was missing in a combat zone

**The question.** A qualifying surviving spouse may use joint rates for the two years after the spouse's
death. When the spouse was in missing status from combat-zone service, which date counts as the death?

**The statute.** IRC 2(a)(3) (U.S. Code p. 56): "the date on which such individual died shall be treated as
the earlier of the date determined under subparagraph (A) or the date determined under subparagraph (B)" —
(A) being the date of the official determination of death, and (B) "the date which is 2 years after the date
designated under section 112 as the date of termination of combatant activities in that zone" (Vietnam
excepted).

**What the software does.** It asks whether the spouse's death was determined while in combat-zone missing
status, and the date combatant activities in that zone were designated as ended. It then refuses qualifying
surviving spouse status once the tax year is past the window that the two-years-after-termination date
allows. It also applies the rule the other way: when the death was determined during the tax year itself
and the two-years-after-termination date falls in either of the two preceding years, the death is treated
as falling inside the window, so the filer can be a qualifying surviving spouse for the tax year. It works
in whole years.

**Why the owner chose it.** A small population, but the statute is explicit, and the owner ruled to build the
closing rule rather than declare the population out of scope. The opening rule was added under the owner's
standing rule to follow the statute where it is clear: IRC 2(a)(3) takes "the earlier of" the two dates with
no exception for the order in which they fall, and the joint return the filer may also make for the year of
the determination is a different return (it carries the spouse's items and needs the representative's
authority), so it does not stand in for the status.

**Our best recommendation.** Keep it. Our confidence is medium because the test works in years, not dates.

**What we would like a reviewer to check.** The year arithmetic at the edge of the window.

**Where it lives.** `filers:/writableSpouseDeathDeterminedWhileInCombatZoneMissingStatus`,
`filers:/writableSpouseCombatZoneTerminationOfCombatantActivitiesDate`,
`filers:/spouseMissingStatusDeemedDeathBeforeQssWindow`, `filers:/widowedCouldQualifyForQSS`.

### FS-01 — Form 8332 release that fails on the filer's own answers

**The question.** Divorced parents can move the child-related tax benefits to the noncustodial parent if the
custodial parent signs a release (Form 8332 or similar) and the noncustodial parent attaches it. What should
the software do when the filer's own answers show the release fails? Three cases: (a1) the filer is the
custodial parent under the nights test but says the *other* parent signed; (a2) the filer is *not* the
custodial parent but says *they* signed; (b) the noncustodial parent says they do not have the signed release
to attach.

**The statute.** IRC 152(e)(1) (U.S. Code p. 720) treats the child as the noncustodial parent's "if the
requirements described in paragraph (2) or (3) are met." Paragraph (2): "(A) the custodial parent signs a
written declaration [...] that such custodial parent will not claim such child as a dependent [...] and (B) the
noncustodial parent attaches such written declaration to the noncustodial parent’s return".

**What the software does.** It computes the return as if section 152(e) does not apply: the custodial parent
keeps the child in case (a1); in cases (a2) and (b) the ordinary qualifying-child tests decide. A release
question left unanswered still holds the return.

**Why the owner chose it.** When the statute's conditions are not met, the statute simply does not apply;
refusing the whole return also took away benefits the custodial parent is entitled to (the child care credit,
the earned income credit, head of household).

**Our best recommendation.** Keep it. It is the plain reading of 152(e).

**What we would like a reviewer to check.** Whether preparers would instead treat these answers as a data
error to be resolved with the client before filing, rather than computing.

**Where it lives.** `dependentsBenefitSplit:/knockedOutByContradictory8832`,
`dependentsBenefitSplit:/knockedOutByNonCustodialParentBenefitSplit`,
`dependentsBenefitSplit:/familyAndHousehold/*/contradictory8832Knockout`,
`dependentsBenefitSplit:/familyAndHousehold/*/writableNoncustodialParentHasReleaseToAttach`,
`dependentsBenefitSplit:/familyAndHousehold/*/tpCanClaimSplitBenefitsDependencyCtcOdc`,
`dependentsBenefitSplit:/familyAndHousehold/*/noncustodialParentSection152eRouteOpen`.

### FS-05 — Earned income credit: service member stationed abroad on extended active duty

**The question.** The earned income credit requires a main home in the United States for more than half the
year. The Code treats a service member's home as in the United States while stationed abroad on extended
active duty. An earlier version of the software asked whether the filer was so stationed "at any time" in
2025, and a yes satisfied the whole test — so one month abroad passed a half-year test.

**The statute.** IRC 32(c)(4) (U.S. Code p. 137): "the principal place of abode of a member of the Armed
Forces of the United States shall be treated as in the United States during any period during which such
member is stationed outside the United States while serving on extended active duty with the Armed Forces of
the United States."

**What the software does.** One question, which replaced the "at any time" question, asks:
"Counting the time you were stationed outside the U.S. on extended active duty as time in the U.S., was your
main home in the U.S. for more than half of 2025?"

**Why the owner chose it.** It asks the statute's own question in one step. The alternative, a day count, also
feeds other forms and costs more.

**Our best recommendation.** Keep it. It matches "during any period" exactly.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `eitc:/writableMainHomeInUsOverHalfYearCountingExtendedActiveDutyAbroad`,
`eitc:/mainHomeInUsOverHalfYearCountingExtendedActiveDutyAbroad`, `eitc:/mainHomeInUsOverHalfYear`, `familyAndHousehold:/familyAndHousehold/*/livedWithTpInUsMostOfYear`.

### FS-07 — Qualifying child of more than one person: a claimant who is not the child's parent

**The question.** A child can be the qualifying child of two taxpayers, for example a grandparent and a
parent who live together, or a grandparent and an aunt. Only one may use the child for the dependency, the
child tax credit, head of household, the dependent care credit and the earned income credit. When the filer
is not the child's parent, which of them may?

**The statute.** IRC 152(c)(4) (U.S. Code p. 719): the child is treated as the qualifying child of the
taxpayer who is "(i) a parent of the individual, or (ii) if clause (i) does not apply, the taxpayer with the
highest adjusted gross income"; and "If the parents of an individual may claim such individual as a
qualifying child but no parent so claims the individual, such individual may be claimed as the qualifying
child of another taxpayer but only if the adjusted gross income of such taxpayer is higher than the highest
adjusted gross income of any parent of the individual." Publication 501 (2025), pages 15-16, restates the
rules and defines a parent as a biological or adoptive parent.

**What the software does.** For a child who is also another taxpayer's qualifying child, when the filer is
not the child's parent (and the section 152(e) path for divorced or separated parents does not apply), it
asks three questions: can one of the child's parents claim the child; if so, does a parent claim the child;
and is the filer's AGI higher than the highest AGI of any parent who can claim the child (or, when no parent
can, than every other person who can claim the child). A parent claiming, or an AGI that is not higher,
gives the child to the other taxpayer: the child is then not the filer's dependent, earned income credit
child or head of household qualifying person. Otherwise the filer may use the child. While the questions are
unanswered the return is refused.

**Why we chose it.** The statute is clear on the order: a parent first; with no parent claiming, a non-parent
only with an AGI higher than every parent's; with no parent able to claim, the highest AGI. The owner's
standing rule is to follow the statute where it is clear. Two readings were needed. An equal AGI is read as
not higher, because the statute speaks of "the highest" and "higher than". And where no parent can claim, the
rule is applied whether or not the other non-parent actually claims the child, because clause (ii) assigns the
child to the highest-AGI taxpayer without a claim condition; Publication 501 says the persons may choose only
"subject to these tiebreaker rules".

**Our best recommendation.** Keep it. Confidence is medium because the IRS enforces the rules mainly when two
returns actually claim the same child, and a filer who is not the highest-AGI claimant may in practice be
allowed the child when the other person does not claim it.

**What we would like a reviewer to check.** Whether the highest-AGI rule between two non-parents binds when
the higher-AGI person does not claim the child.

**Where it lives.** `familyAndHousehold:/familyAndHousehold/*/writableQcOfAnotherParentCanClaim`,
`familyAndHousehold:/familyAndHousehold/*/writableQcOfAnotherParentClaims`,
`familyAndHousehold:/familyAndHousehold/*/writableTpAgiHigherThanOtherQcClaimants`,
`familyAndHousehold:/familyAndHousehold/*/nonParentLosesQualifyingChildTieBreak`,
`familyAndHousehold:/knockoutNonParentClaimsQualifyingChildOfAnother`.

### FS-06 — A disabled child emancipated before midyear and the divorced-parent rule

**The question.** The special rule for children of divorced or separated parents (IRC 152(e)) applies to a child
in the custody of one or both parents. A child who is permanently and totally disabled has no upper age limit
for that rule. If such a child was emancipated under state law before the middle of the year, does the rule
still apply?

**The IRS text.** Publication 504 (2025), page 9: "Emancipated child. If a child is emancipated under state law,
the child is treated as not living with either parent."

**What the software does.** A child answered as emancipated before midyear leaves the special rule, whether or not
the child is disabled. The owner ratified this reading.

**Why the owner chose it.** Publication 504's emancipation rule has no exception for a disabled child.

**Our best recommendation.** Keep it. The disability rule removes the age ceiling; it does not change who the
child lives with, and an emancipated child lives with neither parent.

**What we would like a reviewer to check.** Whether an emancipated, disabled adult child can still be in a
parent's custody for IRC 152(e) under any state's law.

**Where it lives.** `dependentsBenefitSplit:/familyAndHousehold/*/childMayQualifyForBenefitSplit`,
`dependentsBenefitSplit:/familyAndHousehold/*/writableChildEmancipatedUnderStateLaw`.

## Income

### IN-13 — Form 172 line 1: the new Schedule 1-A deductions and the net operating loss

**The question.** Form 172 figures a net operating loss. Its line 1 starts from adjusted gross income less the
standard or itemized deduction. For 2025 there are four new below-the-line deductions on Schedule 1-A
(qualified tips, qualified overtime, qualified passenger-vehicle loan interest, and the enhanced deduction
for seniors), and the qualified business income deduction. Should the loss computation start before or after
them?

**The statute.** IRC 172(d) (U.S. Code p. 878) lists the modifications, and the list is closed. Among them:
"(3) [...] No deduction shall be allowed under section 151 (relating to personal exemptions)"; "(4)
Nonbusiness deductions of taxpayers other than corporations [...] the deductions allowable by this chapter
which are not attributable to a taxpayer's trade or business shall be allowed only to the extent of the
amount of the gross income not derived from such trade or business"; "(8) [...] Any deduction under section
199A shall not be allowed." The Law Revision Counsel's preliminary U.S. Code text with laws in effect on
September 22, 2026, shows the same list with no paragraph for the tips, overtime or car-loan
deductions.

**What the software does.** It follows common practice: line 1 is adjusted gross income less the standard or
itemized deduction, so all four Schedule 1-A deductions and the QBI deduction are left out of the loss
computation entirely. The IRS has not revised Form 172 or its instructions for 2025.

**Why the owner chose it.** The owner ruled to follow common practice. Our research of published software and
commentary found no one computing it any other way, and Form 172 itself was not updated.

**Our best recommendation — differs.** The senior deduction (a section 151 deduction) and the QBI deduction
are excluded by paragraphs (3) and (8); that part is solid. But nothing in 172(d) excludes the tips, overtime
and car-loan interest deductions outright. Read literally, they are ordinary deductions: they belong in the
starting figure, and paragraph (4) then limits them only if they are *nonbusiness* deductions exceeding
nonbusiness income. Leaving them out entirely makes the loss smaller than the statute allows (over-tax in the
year the loss is used). We would include them in line 1 and test them under paragraph (4). Our confidence is
low: whether these deductions are "attributable to a trade or business" (an employee's services are
generally a trade or business) is unsettled, and IRS guidance may yet say otherwise. A revised Form 172, IRS
guidance, or a reviewer's reading of paragraph (4) would settle it.

**The owner's decision after review (2026-09-25).** The owner kept the current call after review.

**What we would like a reviewer to check.** How you would treat the tips, overtime and car-loan deductions in
an NOL computation for 2025, and whether they are business or nonbusiness deductions under 172(d)(4).

**Where it lives.** `form172:/form172Line1AgiLessDeductions`, `form172:/writableForm172Line6NonbusinessDeductions`.

### IN-19 — Form 4797: holding period left unanswered on a sale of business property

**The question.** Business property sold at a gain goes to Form 4797 Part II if held one year or less (all
ordinary income) and to Part III and then Part I if held longer (depreciation recapture ordinary, the rest a
section 1231 gain that may be taxed at capital gain rates). What if the filer does not say how long they held
it?

**The IRS text.** Instructions for Form 4797 (2025), page 1, chart "Where To Make First Entry for Certain Items
Reported on This Form": depreciable tangible trade or business property "Sold or exchanged at a gain" goes to
"Part II" if "Held 1 year or less" and "Part III (1245)" if "Held more than 1 year".

**What the software does.** An unanswered holding period is derived from the acquisition and sale dates on
line 19 when both are entered: held more than one year sends the gain to Part III, one year or less to Part II
(a sale on the anniversary of the purchase is one year or less; the day after is more). With no answer and no
dates, a gain holds the return until the question is answered, and a loss is refused. The same rule applies
to the other holding tests on the form: the livestock holding periods (12 and 24 months), the full years a
section 1252 farm property was held, and whether the property is livestock, each derived from the dates where
they can be and otherwise waiting for the answer.

**Why the owner chose it.** The first reading (an unanswered holding period on a gain is one year or less,
ratified by the owner) never understated tax. After review the owner chose to derive the period from the
dates, or wait for the answer, instead.

**Our best recommendation — differs.** An unanswered question should not silently produce the less favorable
answer either. A long-held gain wrongly sent to Part II loses the capital-gain rate on the section 1231 part —
a silent over-tax the filer cannot see. We would hold the return until the question is answered (the same
rule GEN-01 applies elsewhere), or derive the holding period from the acquisition and sale dates where the
filer entered them. Our confidence is medium: the current call is safe for the government and simple, and the
disagreement is about which kind of error to prefer.

**The owner's decision after review (2026-09-25).** The owner decided to follow our recommendation. It is
built: "What the software does" above describes the software as it is now.

**What we would like a reviewer to check.** (1) Whether deriving the holding period from the dates, and
otherwise waiting for the answer, is how you handle an unanswered holding period. (2) Section 1252 farm land:
the software treats the 5th anniversary of acquisition as still "within 5 years" (100%) and the day after as
the next band (80%), reading IRC 1252(a)(3) with the Form 4797 instructions' day-after counting rule. Is that
right? A filer answering the full-year count directly on that day would likely say 5 and get 80%.

**Where it lives.** `form4797:/section1245Dispositions/*/heldMoreThanOneYear`,
`form4797:/section1245Dispositions/*/heldMoreThanOneYearComplete`,
`form4797:/section1245Dispositions/*/isSection1245PropertyComplete`,
`form4797:/section1245Dispositions/*/isLivestockComplete`,
`form4797:/form4797Section1231Sales/*/heldMoreThanOneYearByDates`,
`form4797:/section1245Dispositions/*/heldMoreThanOneYearByDates`,
`form4797:/section1245Dispositions/*/heldTwentyFourMonthsOrMoreByDates`,
`form4797:/section1245Dispositions/*/heldTwelveMonthsOrMoreByDates`,
`form4797:/section1245Dispositions/*/farmlandFullYearsByDates`.

### IN-18 — Qualified electing fund gain: the 28% and unrecaptured section 1250 portions

**The question.** A shareholder of a passive foreign investment company with a qualified electing fund
election reports the fund's net capital gain on Form 8621 line 7c. Part of it may be collectibles (28%) gain or
unrecaptured section 1250 gain, taxed at higher rates. Where do those portions go on the Schedule D
worksheets?

**The IRS text.** Instructions for Form 8621 (2025), page 12, Line 7c: "Portions of the net capital gain may
have to be reported on different lines of Schedule D, depending upon the information provided by the QEF
concerning the section 1(h) categories of net capital gains and amounts thereof, derived by the QEF." The 28%
Rate Gain Worksheet in the Schedule D instructions (2025), page 11, line 4, names only "Form 1099-DIV, box 2d",
"Form 2439, box 1d" and "Schedule K-1 from a partnership, S corporation, estate, or trust". Neither worksheet
names Form 8621. The regulation the Form 8621 instructions point to for the fund's reporting (Regulations
section 1.1293-1) is not quoted here.

**What the software does.** Separate amounts per fund for the 28% and unrecaptured section 1250 portions of
line 7c, each capped at that fund's line 7c amount, added to the 28% Rate Gain Worksheet line 4 and the
Unrecaptured Section 1250 Gain Worksheet line 13. The worksheet lines are marked as a provisional reading.

**Why the owner chose it.** The instructions say the portions go to different lines; not splitting them
undertaxes.

**Our best recommendation.** Keep the split. Our confidence in the exact worksheet lines is low, because the
IRS text does not name them.

**What we would like a reviewer to check.** Which worksheet lines you use for a QEF's collectibles and
unrecaptured section 1250 amounts.

**Where it lives.** `form8621:/form8621Funds/*/line7c`, `form8621:/form8621Funds/*/isQef`,
`form8621:/form8621Funds/*/writableLine7cCollectiblesGain`,
`form8621:/form8621Funds/*/writableLine7cUnrecapturedSection1250Gain`, `form8621:/form8621CollectiblesGain`,
`form8621:/form8621UnrecapturedSection1250Gain`,
`scheduleD:/twentyEightPercentRateGainLines1Through4`, `scheduleD:/unrecapturedSection1250GainLine13`.

### IN-12 — Home office: an improvement placed in service on the day business use began

**The question.** On Form 8829, improvements placed in service *after* the filer began using the home for
business are depreciated separately (line 42 statement); earlier ones are part of the home's basis (lines 37-40).
How is "after" compared, and what about the same day?

**The IRS text.** Instructions for Form 8829 (2025), page 5: "Attach your own statement showing the cost or
other basis of additions and improvements, used at least partially for business, that were placed in service
after you began to use your home for business. Do not include any amounts on lines 37 through 40 for these
expenditures."

**Owner ruling (2026-10-01, superseding the earlier "on or after" reading).** Follow the Form 8829
instructions literally. Only an improvement placed in service strictly *after* the first day of business use is
depreciated separately on the line 42 statement. One placed in service on that day or earlier is part of the home's
basis on lines 37-40, which the instructions define as the basis "on the date you first used the home for business"
(https://www.irs.gov/pub/irs-pdf/i8829.pdf, page 5). The dates are still compared by day, so an improvement
finished earlier in the same month stays in the basis (verify row FED-1040SC-F8829-LINE42-ADDITIONS-040).

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `scheduleC:/scheduleCs/*/homeAdditions/*/rowIsModeled`.

### IN-01 — Qualified dividends received as a nominee

**The question.** A filer who receives dividends as a nominee for someone else subtracts the nominee amount on
Schedule B. Must the nominee's share of *qualified* dividends also come off Form 1040 line 3a?

**The IRS text.** Publication 550 (2025), *Investment Income and Expenses*, chapter 1, section "Qualified
dividends" (our copy is the IRS web edition, which has no printed page numbers): "Do not include any of
the following on Form 1040 or 1040-SR, line 3a." The first item listed is "Qualified dividends you received
as a nominee."

**What the software does.** A per-payer question asks how much of the nominee amount was qualified dividends
(box 1b). That amount, capped at the payer's box 1b and nominee amount, is subtracted from line 3a. A return
that allocates community income on Form 8958 and has a nominee distribution on community dividends is refused,
because the nominee share cannot yet be split between the spouses.

**Why the owner chose it.** The publication is explicit; the owner chose to build it rather than refuse the
population.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `dividendReports:/dividendReports/*/writableNomineeDistribution`,
`dividendReports:/dividendNomineeDistributionTotal`,
`dividendReports:/dividendReports/*/writableNomineeQualifiedDividends`,
`dividendReports:/dividendNomineeQualifiedDividendsTotal`, `dividendReports:/knockoutCommunityPropertyNomineeDividends`,
`income:/qualifiedDividends`.

### IN-02 — A blank box 8 or 15 on a Form 1099-MISC

**The question.** When a filer transcribes a Form 1099-MISC and leaves box 8 ("Substitute payments in lieu of
dividends or interest") or box 15 ("Nonqualified deferred compensation") blank, is that $0 or unknown?

**The IRS text.** Only the box captions (Form 1099-MISC, Rev. April 2025, Copy B). No IRS text addresses a box
the filer left blank when entering the form into software.

**What the software does.** Unknown. The two boxes must be answered (with $0 if
empty on the paper form) before the Form 1099-MISC counts as complete, as box 4 already is.

**Why the owner chose it.** Consistency with GEN-01 and with box 4: a skipped box should not become a silent
$0 of income.

**Our best recommendation.** Keep it. The cost is one extra confirmation for filers whose boxes are empty.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `form1099Misc:/form1099Miscs/*/isComplete`,
`form1099Misc:/form1099Miscs/*/writableSubstitutePayments`,
`form1099Misc:/form1099Miscs/*/writableNonqualifiedDeferredCompensation`.

### IN-03 — Claim of right (IRC 1341): choosing the lower-tax method

**The question.** A filer who repays more than $3,000 that was taxed in an earlier year gets the lower of two
results: a deduction this year, or a credit equal to the decrease in the earlier year's tax. How is the choice
made?

**The statute.** IRC 1341(a) (U.S. Code p. 2429): where "the amount of such deduction exceeds $3,000", "the tax
imposed by this chapter for the taxable year shall be the lesser of the following": the tax computed with the
deduction, or the tax without it minus "the decrease in tax under this chapter [...] for the prior taxable year
(or years) which would result solely from the exclusion of such item". Publication 525 (2025), page 36:
"Figure your tax under both methods and compare the results. Use the method (deduction or credit) that results
in less tax." Publication 915 (2025), page 15: "If both methods produce the same tax, deduct the repayment on
Schedule A (Form 1040), line 16."

**What the software does.** The owner decided that the software computes the choice, as the statute states it,
superseding the earlier design in which the method was an answer the filer supplied. The earlier year's tax as
filed and as refigured remain answers the filer supplies (that return is not in this software), and both are
asked whenever the repayment exceeds $3,000. The software then figures, side by side and without running the
return twice, the taxable income and the Tax Table tax with the repayment deducted on Schedule A line 16 and
without it, and takes the deduction when that tax is no more than the tax without it less the decrease, and the
credit on Schedule 3 line 13b otherwise. When the deduction does not change line 12e (the filer does not itemize,
or the standard deduction is larger either way) the two taxes are equal and the credit is taken whenever the
decrease is above $0. On a return that elects Schedule J income averaging, each figure is the Schedule J tax with or without the
deduction (IN-160). Where the two figures are not the whole tax for the year (a qualified business income
deduction, qualified dividends or capital gains, income averaging of more farm income than the taxable income with
the deduction, the foreign earned income exclusion, a community-property allocation that itemizes, or the
alternative minimum tax or a nonrefundable credit on the return the comparison chose), the return is refused rather
than filed on an unverified method. Until the
earlier-year figures are answered, neither method is taken.

**Why the owner chose it.** The statute makes the lesser amount the tax; it is not an election. Computing it
removes the risk that a filer, or the interview, records the higher-tax method.

**Our best recommendation.** Keep it. The refused population is a build boundary, not a reading: widening it
means figuring the preferential-rate worksheets, the alternative minimum tax and the credit limits on both sides.

**What we would like a reviewer to check.** Whether the "decrease in the earlier year's tax" the filer is asked
for is a figure clients can realistically supply, and whether comparing the Form 1040 line 16 tax (with the
refusals above) is the right measure of "the tax imposed by this chapter" for the population computed.

**Where it lives.** `taxCalculations:/claimOfRightDeductionGivesLesserTax`,
`taxCalculations:/knockoutClaimOfRightComparisonUnbuilt`, `scheduleA:/electsClaimOfRightRepaymentDeduction`,
`scheduleA:/claimOfRightRepaymentTotal`, `scheduleA:/claimOfRightRepaymentExceedsThreshold`,
`scheduleA:/claimOfRightRepaymentDeduction`, `schedule3:/sched3Line13b`.

### IN-04 — Vacation home: whole-property expenses allocated by days

**The question.** For a dwelling used both personally and as a rental, the expenses must be divided between
rental and personal use. Does the filer enter the expenses already divided (the amounts that go on Schedule E),
or the whole-property totals for the software to divide?

**The IRS text.** IRC 280A(e)(1) (U.S. Code p. 1048) limits the rental expenses to "an amount which bears the
same relationship to such expenses as the number of days during each year that the unit (or portion thereof)
is rented at a fair rental bears to the total number of days during such year that the unit (or portion
thereof) is used." Instructions for Schedule E (2025), page 5: "You must allocate your expenses based on the
number of days of personal use to total use of the property." Publication 527 (2025), page 25: "divide your
expenses between the rental use and the personal use based on the number of days used for each purpose."

**What the software does.** The filer enters whole-property totals; the software divides them by fair-rental
days over total days used, and then applies the order of deductions of Publication 527's Worksheet 5-1. For the
worksheet's mortgage interest and taxes tier the filer confirms whether they itemize, and the return is refused
if that answer disagrees with the deduction the return takes. The unit's net, profit or loss, is kept out of
the passive activity rules (see IN-71). An itemizer whose rental part of mortgage interest and taxes pushes the
fully deductible expenses above the rents is refused, because the unit's net is figured without the itemize
choice. A home rented fewer than 15 days is not a rental property at all: the return asks the filer to remove it.

**Why the owner chose it.** Dividing is arithmetic the software can do reliably; asking filers to do it
invites errors.

**Our best recommendation.** Keep it. The divisor must be days *used* (rental plus personal), not days in the
year, as the statute says. Mortgage interest and taxes on such a home are the subject of a long-standing
difference between the IRS's allocation and a court-approved alternative; the maintainers hold
no copy of it, so we cite nothing for it and the software follows the IRS publication.

**What we would like a reviewer to check.** Whether you would allocate mortgage interest and property taxes by
the IRS publication's method.

**Where it lives.** `scheduleE:/rentalProperties/*/dwellingUsedAsHome`,
`scheduleE:/rentalProperties/*/section280ALimitedNet`, `scheduleE:/writableWorksheet51ElectsToItemize`,
`taxCalculations:/worksheet51ItemizeRecommended`, `scheduleE:/knockoutRentalWorksheet51ElectionDisagreesWithReturn`,
`scheduleE:/knockoutRentalDwellingRentedUnder15Days`, `scheduleE:/knockoutRentalDwellingUsedAsHomeLoss`,
`scheduleE:/rentalProperties/*/section469j10NonpassiveNet`.

### IN-05 — Rental building: class of property left unanswered

**The question.** A residential rental building is depreciated over 27.5 years, a nonresidential one over 39.
If the filer does not say which, may the software assume residential?

**The statute.** IRC 168(c) (U.S. Code p. 784): "Residential rental property 27.5 years"; "Nonresidential real
property 39 years."

**What the software does.** No assumption. On a positive building basis the filer confirms whether the
standard recovery period applies; an unanswered confirmation holds the return, and the interview asks the
question. The software never uses 27.5 years for silence.

**Why the owner chose it.** Assuming residential over-deducts on every nonresidential building whose owner
skipped the question.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `scheduleE:/rentalProperties/*/writableBuildingBasisUsesStandardGDS`,
`scheduleE:/rentalProperties/*/buildingRecoveryPeriodUnknown`,
`scheduleE:/knockoutRentalBuildingRecoveryPeriodUnknown`, `scheduleE:/rentalProperties/*/buildingDatedMethodSelected`.

### IN-06 — Rental: prior-year unallowed loss left unanswered

**The question.** For a real estate professional's rental that was passive in earlier years, the prior-year
unallowed loss offsets this year's income from that activity. If the filer does not answer the prior-year
loss, is it $0?

**The IRS text.** None addresses an unanswered carryover amount; this is a completeness convention (GEN-01).

**What the software does (implementation in progress).** The amount stays unknown and the result waits for an
answer. A neighbouring fact treats the same unanswered amount as $0; that inconsistency is recorded and is not
changed by this ruling.

**Why the owner chose it.** A carryover the filer has but did not enter would otherwise be lost silently.

**Our best recommendation.** Keep it, and make the neighbouring fact consistent.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `scheduleE:/rentalProperties/*/repFormerPassiveIncomeOffset`,
`scheduleE:/rentalProperties/*/priorYearUnallowedLoss`, `scheduleE:/rentalProperties/*/netAfterPriorLoss`.

### IN-07 — Publicly traded partnership: section 1231 gain and the same partnership's loss

**The question.** Losses from a publicly traded partnership can offset only that partnership's income. When
the same partnership reports a section 1231 gain (K-1 box 10) and an overall loss, are they combined?

**The IRS text.** Partner's Instructions for Schedule K-1 (Form 1065) (2025), page 10, example: "Report the
$7,200 gain on the appropriate line of Form 4797. On Schedule E (Form 1040), line 28, report $7,200 of the
losses as a passive loss in column (g). Carry forward the unallowed loss of $4,800 ($12,000 − $7,200)."

**What the software does.** A box 10 gain (and a box 10 loss reported as passive) is combined into the
per-partnership passive result, as in the example, which the software reproduces ($12,000 loss, $7,200 gain,
$4,800 carried forward). One case is still refused: a passive box 10 loss beside the same partnership's
income, where part of the loss belongs on Form 4797.

**Why the owner chose it.** The instructions' own worked example combines them.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `scheduleE:/formK1s/*/ptpSection469NetWithSection1231`,
`scheduleE:/formK1s/*/ptpSection1231AmountInCombination`, `scheduleE:/formK1s/*/ptpSection469Net`,
`scheduleE:/knockoutK1PtpSection1231NotCombined`.

### IN-08 — Schedule K-1: publicly traded partnership checkbox and a limited partner's participation

**The question.** (1) If the K-1's item D ("publicly traded partnership") is left unanswered, may the software
infer it? (2) If a limited partner of a publicly traded partnership does not say whether they materially
participated, what is assumed?

**The statute.** IRC 469(h)(2) (U.S. Code p. 1637): "Except as provided in regulations, no interest in a
limited partnership as a limited partner shall be treated as an interest with respect to which a taxpayer
materially participates."

**What the software does.** (1) Item D is the filer's answer only, with no default; unanswered, the
partnership-dependent results wait for it. A K-1 from an S corporation has no item D and is never a publicly
traded partnership. (2) For a limited partner (including one whose general-partner box is unanswered) of a
publicly traded partnership, unanswered participation is treated as not material; answering yes rebuts it.
A general partner with unanswered participation and a section 179 amount is refused.

**Why the owner chose it.** The first follows the printed form; the second follows the statutory presumption.

**Our best recommendation.** Keep both.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `scheduleE:/formK1s/*/isPubliclyTradedPartnership`,
`scheduleE:/formK1s/*/partnerIsGeneralPartner`, `scheduleE:/formK1s/*/materiallyParticipated`,
`scheduleE:/formK1s/*/materiallyParticipatedAfterPresumption`, `scheduleE:/knockoutK1Section179OnPtp`.

### IN-09 — A passive K-1's section 179 deduction

**The question.** Is a section 179 deduction passed through on a K-1 from a passive activity a passive-activity
deduction (limited by Form 8582), or something else?

**The IRS text.** Instructions for Form 8582 (2025), page 8: "Passive activity deductions include all
deductions from activities that are passive activities for the current tax year".

**What the software does.** After the Form 4562 limits, the share is one of that activity's passive-activity
deductions; for a publicly traded partnership it enters that partnership's own computation; nonpassive, it goes
to Schedule E column (j). The at-risk limit is applied first.

**Why the owner chose it.** It follows the passive-activity instructions; no separate class exists.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `scheduleE:/formK1s/*/section179PassiveActivityDeduction`,
`scheduleE:/formK1s/*/section179AllocatedShare`, `scheduleE:/formK1s/*/atRiskAllowedSection179`,
`scheduleE:/formK1s/*/ptpSection179Allowed`.

### IN-10 — Form 4835: the at-risk box limits the loss

**The question.** Form 4835 (farm rental income) asks, when there is a loss, whether all investment is at risk.
Does checking "some investment is not at risk" limit the loss, as the same question does on Schedules C, E and
F, or is it only printed?

**The IRS text.** Form 4835 (2025), line 34: "If line 32 is a loss, check the box that describes your
investment in this activity", and line 34c: "If you checked box 34b, you must complete Form 6198 before going
to Form 8582."

**What the software does.** The answer limits the deductible loss to the amount at risk and carries the excess
forward, as on the other forms.

**Why the owner chose it.** The owner ruled that the same question must behave the same way on every form it
appears on.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `form4835:/writableForm4835AllInvestmentAtRisk`, `form4835:/writableForm4835AmountAtRisk`,
`form4835:/form4835AtRiskLimitationApplies`, `form4835:/form4835Line34cDeductibleLossAfterAtRisk`.

### IN-11 — Form 4684: property columns, and a casualty to a home used for business

**The question.** (1) Form 4684 has four property columns (A-D) per casualty event. Does the per-property list
hold all four columns, or only B-D beside a separate column A? (2) For a casualty to a home used in a business
reported on Schedule C, how is the right business found?

**The IRS text.** Instructions for Form 4684 (2025), page 10: "If the loss involved a home used for a business
for which you are filing Schedule C (Form 1040) [...] figure your deductible casualty or theft loss on Form 8829
[...] Enter on Form 4684, line 27, the deductible loss from Form 8829, line 35".

**What the software does.** (1) The list holds columns A-D (its first item is column A), and line 10 is the sum
over all answered items. (2) Each casualty event says whether the home was used for a Schedule C business and
names that Schedule C; line 27 is that business's Form 8829 line 35. If the business is not named, the line
waits for the answer rather than computing an uncapped loss.

**Why the owner chose it.** It follows the form's own layout and the instruction above.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `form4684:/casualtyEvents/*/properties/*/writableAdjustedBasis` (and the sibling property
facts), `form4684:/casualtyEvents/*/propertyColumnsAnswered`, `form4684:/casualtyEvents/*/lineTenCasualtyLoss`,
`form4684:/casualtyEvents/*/writableHomeUsedForScheduleCBusiness`, `form4684:/casualtyEvents/*/writableHomeScheduleC`,
`form4684:/casualtyEvents/*/homeUsedForBusinessOrRentedOut`, `form4684:/knockoutCasualtyGain`,
`form8829:/scheduleCs/*/writableForm8829Line35CasualtyPortion`,
`form8829:/scheduleCs/*/form8829Line29ExcessCasualtyLosses`.

### IN-14 — Qualified disaster distributions (Form 8915-F)

**The question.** (1) On a joint return, whose Form 8915-F is it? (2) What part of a current-year qualified
disaster distribution stays on Form 1040 line 4b or 5b?

**The IRS text.** Form 8915-F (Rev. December 2025), page 2, line 7: "Taxable amount. Enter the excess of the sum
of lines 2 through 4 in column (a) over the amount on line 6. Report this excess as IRA and/or pension and
annuity distributions, as applicable, in accordance with the instructions for your tax return." Instructions
for Form 8915-F (Rev. December 2025), page 9: "If both you and your spouse are required to file Form 8915-F,
file a separate Form 8915-F for each of you."

**What the software does.** The form belongs to one spouse, and the Form 5329 early-distribution exception
follows that spouse. Only the excess stays on line 4b/5b; the qualified amount is taxed through the form
itself. A joint return where both spouses need their own Form 8915-F is refused for now.

**Why the owner chose it.** The owner ruled to build what the law requires even though it spans several
forms. It removed a measured double count of the qualified amount on line 4b/5b.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `form8915F:/writableForm8915FBelongsToSecondaryFiler`,
`form8915F:/form8915FCurrentQualifiedPensionTaxableRemoval`, `form8915F:/form8915FCurrentQualifiedIraTaxableRemoval`,
`form8915F:/knockoutForm8915FBothSpousesRequireTheForm`, `income:/ordinaryPensionDistributionsBeforeForm8915FRemoval`,
`income:/knockoutForm8915FQualifiedAmountExceedsOrdinaryRoute`.

### IN-15 — Farming: the soil and water conservation limit (section 175) and prepaid farm supplies (section 464)

**The question.** (1) The section 175 deduction is limited to 25% of gross income from farming. Is the limit per
activity or per taxpayer, and what is in the base? (2) Section 464 limits prepaid farm supplies by reference to
other deductible farm expenses, which include the section 175 deduction. Which is figured first?

**The regulation.** 26 CFR 1.175-5(a)(2) (p. 212): "the term gross income from farming means the gross income
of the taxpayer, derived in ‘‘the business of farming’’ as defined in § 1.175–3, from the production of crops,
fruits, or other agricultural products, including fish, or from livestock (including livestock held for draft,
breeding, or dairy purposes)."

**What the software does.** Section 175 is figured first, against gross income from farming not reduced by the
prepaid-supplies limit, and its allowed amount then enters the section 464 computation. The limit is one per
taxpayer across Schedule F and Form 4835. The base is the production income, plus gains on draft, breeding and
dairy livestock, less receipts not from production. Where prepaid poultry is placed on Schedule F is not yet
settled and that case is refused.

**Why the owner chose it.** The owner ruled "tax law is the authority" and allowed new questions where needed.

**Our best recommendation.** Keep it; the regulation is explicit.

**What we would like a reviewer to check.** Where you report prepaid poultry costs on Schedule F (Part I line 1b
or Part II), since the IRS farm publication is not consistent on it.

**Where it lives.** `form4835:/form4835Section175GrossIncomeFromFarming`, `form4835:/form4835Section175ConservationExpenseCap`,
`form4835:/section1245Dispositions/*/section175LivestockGain`, `scheduleF:/scheduleFPrepaidFarmSuppliesLimit`,
`scheduleF:/scheduleFPrepaidFarmSuppliesDisallowed`.

### IN-16 — Form 4797 line 29a: the section 1255 percentage

**The question.** Line 29a asks for the "applicable percentage" of excluded conservation cost-sharing payments.
Should the filer enter that one figure, or a schedule of payments by year of receipt for the software to
compute it?

**The IRS text.** Instructions for Form 4797 (2025), page 12, Line 29a: "Use 100% if the property is disposed
of less than 10 years after receipt of payments excluded from income. Use 100% minus 10% for each year, or part
of a year, that the property was held over 10 years after receipt of the excluded payments. Use zero if 20
years or more."

**What the software does.** It takes the one figure the line asks for. An unanswered line 29a with a section
1255 gain is refused.

**Why the owner chose it.** The form asks for one figure; a schedule of eleven age bands would move the same
judgement onto the filer eleven times.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `form4797:/section1245Dispositions/*/writableSection1255ApplicablePercentageOfPayments`,
`form4797:/section1245Dispositions/*/section1255ApplicablePercentageOfPayments`, `form4797:/section1255OrdinaryRecapture`.

### IN-17 — Section 1202 exclusion shown on Form 2439

**The question.** A regulated investment company may report section 1202 (small business stock) gain on Form
2439. Should the software compute the exclusion from the notice, or take the filer's figure?

**The IRS text.** Instructions for Schedule D (2025), page 8, on entering the exclusion: "enter as a positive
number the amount of your allowable exclusion on line 2 of the 28% Rate Gain Worksheet; if you excluded 60% of
the gain, enter 2/3 of the exclusion; if you excluded 75% of the gain, enter 1/3 of the exclusion".

**What the software does.** The exclusion is the filer's figure, entered once with the rest of the section 1202
exclusion; the notice-based computation is not built.

**Why the owner chose it.** The eligible fraction and tier depend on facts the notice does not carry, and a
computed third figure would double count against the filer's existing entry.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `scheduleD:/writableSection1202ExclusionFromForm8949`, `form2439:/form2439IncludedSection1202Gain`,
`dividendReports:/dividendReports/*/writableSection1202Exclusion`.

### IN-20 — Section 1296 mark-to-market amounts: one entry point each

**The question.** A shareholder who made the mark-to-market election for a passive foreign investment company
reports the yearly gain or loss as ordinary income, and the net investment income tax then counts the same
amounts. Where is each amount entered, so nothing is counted twice?

**The IRS text.** Instructions for Form 8960 (2025), page 12: "if you’re subject to the section 1296
mark-to-market rules for a PFIC, you’ll include in NII any amounts included in income for regular income tax
purposes under section 1296(a)(1) and deduct from NII any amounts deducted from income for regular income tax
purposes under section 1296(a)(2). Use line 6 to make increases or decreases to NII as a result of this rule
(for items that aren’t otherwise reflected on Form 8960)."

**What the software does.** The regular-tax ordinary income comes only from the filer's Form 8621 entries
(Schedule 1 line 8z). The separate list of mark-to-market positions used for the net investment income tax feeds
only Form 8960 line 6, never Schedule 1.

**Why the owner chose it.** One amount, one entry point: the same mark must not reach income twice.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `income:/schedule1Line8zSection1296MarkToMarketIncomeOrZero`, `form8960:/niitSection1296Positions`,
`form8960:/niitSection1296PositionsLine6Total`, `form8960:/niitLine6Section1296MarkToMarketAdjustment`.

### IN-21 — Form 1099-DA: backup withholding (box 4) and a creator's first-sale proceeds (box 11c)

**The question.** Form 1099-DA reports digital asset sales. Two of its boxes carry amounts that do not flow through
the Form 8949 sale rows: box 4, backup withholding, and box 11c, the proceeds from the first sale of an NFT the
filer created or minted. What should the software do with each?

**The IRS text.** Form 1099-DA (2025), Instructions for Recipient: "Box 4. Shows backup withholding. Generally, a
filer must backup withhold if you did not furnish your TIN to the filer. See Form W-9 for information on backup
withholding. Include this amount on your income tax return as tax withheld." and "Box 11c. Shows the gross
proceeds from the first sale of any specified NFTs you created or minted." Box 1f "does not include the gross
proceeds from the first sale of any specified NFTs you created or minted, which are reported in box 11c."
Instructions for Form 1040 (2025), page 39, Line 25b: "If you received a 2025 Form 1099 showing federal income
tax withheld on dividends, taxable or tax-exempt interest income, unemployment compensation, social security
benefits, railroad retirement benefits, or other income you received, include the amount withheld in the total
on line 25b."

**What the software does.** Box 4 of every received Form 1099-DA (not a VOID copy) is added, with its cents, to
the line 25b total, which is rounded once. A Form 8949 row marked as reported on a Form 1099-DA does not also count a
Form 1099-B box 4, so the broker's withholding is counted once. The software refuses a return with an amount in box
11c, because it does not yet decide where a creator's first-sale proceeds are reported (they are not a Form 8949
disposition).

**Why the owner chose it.** Box 4 needs no interpretation: the recipient instructions and the line 25b instructions
put it on line 25b, so it is computed (operator rule NE-8: follow the text when it is clear). For box 11c, a refusal
instead of unreported income (GEN-02).

**Our best recommendation.** Keep the box 11c refusal until its route is built. The Form 1040 instructions (pages
15-16, "How To Report Digital Asset Transactions") say a digital asset held for sale to customers in a trade or
business is reported as income of the same type (for example, inventory on Schedule C), and other ordinary income
from digital assets not reported elsewhere goes on Schedule 1, line 8v. A creator's own artistic composition is not a
capital asset (IRC 1221(a)(3)), so the first sale is not a Form 8949 disposition either way. Box 11c is gross
proceeds; the creator's basis is not on the statement. The route therefore needs the filer to say which case applies
and to give a basis, and it must not double count Schedule C gross receipts already entered.

**What we would like a reviewer to check.** Where you report a creator's first-sale NFT proceeds for a filer who
is not in the business of creating them.

**Where it lives.** `scheduleD:/form1099DaFederalIncomeTaxWithheld`, `scheduleD:/form1099Das/*/federalIncomeTaxWithheldOrZero`,
`taxCalculations:/form1099Withholding`, `scheduleD:/knockoutForm1099DaCreatorFirstSaleProceedsNotRouted`,
`scheduleD:/form1099Das/*/creatorFirstSaleProceedsEntered`.

### IN-22 — Form 4835 line 10: a conservation expense entered by a filer who claims no farm rental

**The question.** A filer answers the Form 4835 conservation expense question (line 10), or enters a prior-year
section 175 carryover for it, but says the return has no farm rental income. Should that amount use part of the
one 25% limit the return shares with Schedule F line 12, and what happens to it?

**The IRS text.** Form 4835 (2025), page 2, Purpose of Form: "use Form 4835 to report farm rental income based on
crops or livestock produced by the tenant." IRC 175(b): "The amount deductible under subsection (a) for any
taxable year shall not exceed 25 percent of the gross income derived from farming during the taxable year. If for
any taxable year the total of the expenditures treated as expenses which are not chargeable to capital account
exceeds 25 percent of the gross income derived from farming during the taxable year, such excess shall be
deductible for succeeding taxable years in order of time". Publication 225 (2025), chapter 5: a landowner who
receives farm rental payments based on farm production is in the business of farming.

**What the software does.** A return that claims no farm rental files no Form 4835, so line 10 is $0 and the
amount takes nothing from the 25% limit; Schedule F line 12 keeps the whole limit. The Form 4835 carryforward
figure then reports the whole amount, carry-in included, as carried to a later year.

**Why.** The zero deduction follows from the form: without the rental there is no Form 4835 to deduct it on.
The carryforward does not follow as clearly. A prior-year carryover that was not deducted remains an excess under
section 175(b), but a current-year expense of a landowner who reports no production-based rent may not be a
section 175 expense of a farming business at all, and then it should not carry forward.

**Our best recommendation.** Keep the zero deduction. For the carryforward, carry the prior-year carryover and
ask whether a current-year expense belongs to a farming business before carrying it.

**What we would like a reviewer to check.** Whether a current-year Form 4835 line 10 expense of a landowner who
reports no farm rental that year carries forward under section 175(b).

**Where it lives.** `form4835:/form4835Line10`, `form4835:/form4835Section175CarryForward`,
`form4835:/form4835Section175ConservationExpenseCapRemainingAfterForm4835Line10`.

### IN-23 — Form 172 lines 7 and 12: a negative entry for nonbusiness income or business capital gains

**The question.** Form 172 line 7 (nonbusiness income other than capital gains) and line 12 (business capital
gains) are filer entries. If a filer enters a negative figure there, should it lower line 8 or line 13, and so
shrink the net operating loss?

**The IRS text.** Form 172 (Rev. December 2024), page 1: line 7 "Nonbusiness income other than capital gains",
line 8 "Add lines 5 and 7", line 12 "Business capital gains (without regard to any section 1202 exclusion)",
line 13 "Add lines 10 and 12". The instructions list the items that make up line 7 (ordinary dividends,
annuities, interest, and similar income).

**What the software does.** A negative entry on line 7 or line 12 is read as zero, so line 8 is never less than
line 5 and line 13 is never less than line 10. This is not an owner ruling.

**Why.** Both lines name income or gains, and neither can be below zero. Losses have their own lines (2, 6 and 11)
and the form limits them there. A negative entry is a sign error, and letting it through would lower lines 8 and
13 and so shrink the loss.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** That no item the instructions send to line 7 or line 12 is a net
figure that can be below zero.

**Where it lives.** `form172:/form172Line8NonbusinessGainAndIncome`, `form172:/form172Line13BusinessCapitalLossAllowance`.
### IN-24 — Form 1099-R code 3: a partly taxable disability pension before minimum retirement age

**The question.** A Form 1099-R with box 7 code 3 (disability) is paid to a filer who has not reached the plan's
minimum retirement age, and box 2a (taxable amount) is less than box 1. Should box 2a go on Form 1040 line 1h as
wages, or should the return be refused because only a fully taxable form was supported?

**The IRS text.** Publication 575 (2025), page 6, Disability Pensions: "You must report your taxable disability
payments as wages on Form 1040, 1040-SR, or 1040-NR, line 1h, until you reach minimum retirement age."
Instructions for Form 1040 (2025), page 25, Line 1h: "Disability pensions shown on Form 1099-R if you haven't
reached the minimum retirement age set by your employer."

**What the software does.** Box 2a goes on line 1h as wages whether or not it equals box 1; the part of box 1 above
box 2a is not income and is reported nowhere. The owner ruled on 2026-09-27 ("if IRS allows those, do them"); this
replaces an earlier call that refused a partly taxable code 3 form on the ground that cost recovery begins only at
minimum retirement age.

**Why the owner chose it.** The instruction names the taxable payments and sets no full-taxability condition, and
the payer's box 2a is the taxable amount.

**Our best recommendation.** Keep. The earlier reading drew a condition the text does not print.

**What we would like a reviewer to check.** Whether a payer's box 2a below box 1 on a pre-retirement-age code 3
form is reliable, or whether the filer should be asked to confirm the taxable amount.

**Where it lives.** `form1099Rs: /form1099Rs/*/isDisabilityWagesBeforeMinRetirementAge`,
`form1099Rs: /primaryFilerDisabilityPensionsBeforeMinRetirementAge`,
`form1099Rs: /secondaryFilerDisabilityPensionsBeforeMinRetirementAge`.

### IN-25 — A late rollover completed within a longer rollover period the IRS allows

**The question.** A filer rolled over a distribution after the 60-day limit, but within a period the IRS allows: an
automatic waiver, a self-certification, an IRS waiver, a frozen deposit, or, for a qualified plan loan offset (box 7
code M), by the return due date. Is the rolled-over amount excluded, or is the return refused?

**The IRS text.** IRC 402(c)(3) (2024 edition of the United States Code, Title 26): "Except as provided in
subparagraphs (B) and (C), paragraph (1) shall not apply to any transfer of a distribution made after the 60th day
following the day on which the distributee received the property distributed." Subparagraph (B): "The Secretary
may waive the 60-day requirement under subparagraph (A) where the failure to waive such requirement would be
against equity or good conscience". Subparagraph (C): for a qualified plan loan offset amount, the limit is "the
due date (including extensions) for filing the return of tax for the taxable year". Publication 590-A (2025), page
24: "There are three ways to obtain a waiver of the 60-day rollover requirement." and that under Revenue Procedure 2020-46 "you may
make a written certification to a plan administrator or an IRA trustee that you missed the 60-day rollover
contribution deadline". Publication 575 (2025), page 23, Frozen deposits: "The 60-day
rollover period is extended by the period for which the amount is a frozen deposit".

**What the software does.** After a No to the 60-day question it asks whether the rollover was completed within the
rollover period that applies (the five cases above). A Yes excludes the rolled-over amount, up to box 2a, as for a
timely rollover; a No still refuses the return. The rollover question is now also asked on code M forms. The owner
ruled on 2026-09-27 ("if IRS allows those, do them").

**Why the owner chose it.** The statute and the publications make each of these a lawful rollover.

**Our best recommendation.** Keep. A late rollover the filer answers No to stays refused, because a late deposit into
an IRA may also be an excess contribution, which is not computed. A self-certification is not an IRS waiver and may
be reviewed on audit (Pub. 590-A); the question's help text says which cases count.

**What we would like a reviewer to check.** Whether disaster relief under a federally declared disaster should be
named separately; today it reaches the question only through the waiver and self-certification cases.

**Where it lives.** `form1099RFrontier: /form1099Rs/*/writableIndirectRolloverCompletedWithinExtendedPeriod`,
`form1099RFrontier: /form1099Rs/*/indirectRolloverInputsComplete`, `form1099Rs: /form1099Rs/*/flowAskAboutIndirectRollover`.

### IN-26 — In-plan Roth rollover recapture: line 1 in full, the exception on line 2

**The question.** A Form 1099-R box 10 reports an amount allocable to an in-plan Roth rollover made within the
5-year period, and the filer answers that part of it is excepted from the additional tax. Is the exception netted
before Form 5329 line 1, or is the whole recapture on line 1 and the exception on line 2?

**The IRS text.** Instructions for Form 5329 (2025), page 3: "You may also need to include a recapture amount on
line 1 if you have ever made an in-plan Roth rollover". Page 5, Line 2: "Enter on line 2 the amount that you can
exclude. In the space provided, enter the applicable exception number (01–23). If more than one exception applies,
enter 99."

**What the software does.** The whole box 10 recapture goes on line 1; the excepted part (never more than box 10)
goes on line 2, and the exception number comes from the line 2 exception-number question (99 when more than one
applies). The tax on line 4 is unchanged. The owner ruled on 2026-09-27 ("if IRS allows those, do them"); this
replaces netting the exception before line 1.

**Why the owner chose it.** The instructions place the recapture on line 1 and every exception on line 2.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Nothing further; the printed lines now follow the instructions.

**Where it lives.** `form1099RFrontier: /form1099Rs/*/inPlanRothRolloverRecaptureAmount`,
`form1099RFrontier: /form1099Rs/*/inPlanRothRolloverRecaptureExceptedAmount`,
`form1099RFrontier: /form1099REarlyDistributionExceptionTotal`, `form5329: /form5329PrimaryFilerDocumentExceptionTotal`.

### IN-27 — Net unrealized appreciation: the election only on a lump-sum distribution

**The question.** A filer with employer securities (box 6) answers Yes to including the net unrealized appreciation
(NUA) in income. The election exists only for a lump-sum distribution. How does the software tell a lump-sum
distribution: from box 2b (total distribution), or by asking?

**The IRS text.** IRC 402(e)(4)(B): "in the case of any lump sum distribution which includes securities of the
employer corporation, there shall be excluded from gross income the net unrealized appreciation" and "a taxpayer may
elect, on the return of tax on which a lump sum distribution is required to be included, not to have this
subparagraph apply to such distribution." IRC 402(e)(4)(A) excludes the NUA from any other distribution, with no
election. IRC 402(e)(4)(D)(i): a lump-sum distribution "means the distribution or payment within one taxable year of
the recipient of the balance to the credit of an employee which becomes payable to the recipient" on account of
death, after age 59 1/2, on separation from service, or after disability.

**What the software does.** It asks, after a Yes to the election, whether the distribution is a lump-sum
distribution. On a No, box 6 stays excluded and box 2a is the taxable amount; unanswered, the taxable amount is not
computed. The owner ruled on 2026-09-27 ("if IRS allows those, do them"; pick the treatment the sources support).

**Why the owner chose it.** Box 2b records that an account was paid out in full, not why; the definition also needs
one of four events and the aggregation of the employer's plans of one kind, so box 2b is not a sufficient test.

**Our best recommendation.** Keep the question.

**What we would like a reviewer to check.** Whether the help text's one-sentence definition is enough for filers.

**Where it lives.** `form1099RFrontier: /form1099Rs/*/writableNuaDistributionIsLumpSum`,
`form1099RFrontier: /form1099Rs/*/effectiveTaxableAmount`,
`form1099RFrontier: /form1099Rs/*/netUnrealizedAppreciationExcludedFromIncome`.

### IN-230 — Form 8606 on the Worksheet 1-1 route: qualified charitable and HSA funding distributions stay out of the ratio

**The question.** A filer who contributed to a traditional IRA for 2025, may not deduct all of it, and also
took a distribution figures the nontaxable part on Publication 590-B Worksheet 1-1 instead of Form 8606 lines
6-12. The worksheet's line 5 says to include qualified charitable distributions (QCDs) and a one-time HSA
funding distribution in the total distributions. Form 8606 line 7 says to leave them out. Does a QCD or HSA
funding distribution enter the worksheet's ratio, and does any share of it reach line 15a?

**The statute and instructions.** IRC 408(d)(8)(D) (current text, unchanged from the 2024 edition): "Notwithstanding
section 72, in determining the extent to which a distribution is a qualified charitable distribution, the entire
amount of the distribution shall be treated as includible in gross income without regard to subparagraph (A) to
the extent that such amount does not exceed the aggregate amount which would have been so includible if all
amounts in all individual retirement plans of the individual were distributed during such taxable year [...].
Proper adjustments shall be made in applying section 72 to other distributions in such taxable year and
subsequent taxable years." IRC 408(d)(9)(E) says the same for a qualified HSA funding distribution. Publication
590-B (2025), page 14: "If your IRA includes nondeductible contributions, the distribution is first considered
to be paid out of otherwise taxable income." The same page works an example (Amy): a $25,000 distribution from
an IRA worth $30,000 with $10,000 of basis is a $20,000 QCD; "Amy enters -0- on line 4b" and "After the
distribution, her basis in her IRA is $5,000." Form 8606 (2025), page 1, line 7: "Also, do not include qualified
charitable distributions; a one-time distribution to fund an HSA". Publication 590-B (2025), page 17, Worksheet
1-1 line 5: "Also, include repayments of qualified disaster distributions, qualified charitable distributions
(QCDs), and a one-time distribution to fund a health savings account (HSA)."

**What the software does.** On the worksheet route it uses Form 8606 lines 7 and 8 as the worksheet's line 5
and Form 8606 line 9 (year-end value plus lines 7 and 8) as its line 6. A QCD or HSA funding distribution is in
neither, so it takes no basis and no share of it reaches line 15a. It is excluded from income on its own Form
1040 line 4c election.

**Why we chose it.** The statute is clear: the QCD and the HSA funding distribution come first out of the amount
that would otherwise be taxable, and the other distributions are adjusted so the basis stays with them. Leaving
both out of the ratio is that adjustment; it is also exactly what Form 8606 line 7 does on the ordinary route, and
Amy's example shows the result (the basis stays with the non-QCD part). Read literally, worksheet line 5 would
move basis onto the QCD. Example: $6,000 of basis (with the 2025 contribution), $50,000 year-end value, a
$10,000 ordinary distribution and a $20,000 QCD. Our call: ratio 6,000 / 60,000 = 0.100, line 15a $9,000. The
worksheet read literally: ratio 6,000 / 80,000 = 0.075; if only the ordinary distribution's share reaches line
15a it is $9,250 ($250 more income); if the whole worksheet line 9 did, $27,750, which would tax the QCD the
statute excludes. The disaster-repayment words on worksheet lines 4 and 5 are the same adjustment Form 8606 lines
6 and 7 already ask for ("Subtract certain 2025 retirement plan distribution repayments treated as rollovers";
"but do include certain 2025 retirement plan distribution repayments treated as rollovers"), so the filer's line
6 and 7 answers carry them.

**Our best recommendation.** Keep. Confidence high.

**What we would like a reviewer to check.** Whether the worksheet's inclusion of QCDs and HSA funding
distributions in line 5 is meant to produce a different result from Form 8606 line 7 for a filer who contributes
and makes a QCD in the same year.

**Where it lives.** `form8606: /form8606Ws11NontaxablePortion`, `form8606: /spouseForm8606Ws11NontaxablePortion`,
`form8606: /form8606Line15a`.

### IN-231 — Form 5329 line 1 for an early traditional IRA distribution that Form 8606 figures: each form's pro rata share of line 15a

**The question.** A filer under 59 1/2 with basis in a traditional IRA takes an early distribution. The Form
1099-R shows the whole distribution in box 2a; Form 8606 figures the taxable part. Form 5329 line 1 takes "early
distributions includible in income". When the filer has several Form 1099-Rs, some early and some not (for
example one with an exception code), how much of line 15a belongs to each?

**The statute and instructions.** Instructions for Form 5329 (2025), page 3, Line 1: "Enter the amount of early
distributions includible in income (other than qualified disaster recovery distributions)". Instructions for
Form 8606 (2025), page 11, Line 15c: "If you were under age 59 1/2 at the time you received distributions from
your traditional IRA, there is generally an additional 10% tax on the portion of the distribution that is
included in income". IRC 72(t)(1): "10 percent of the portion of such amount which is includible in gross
income". IRC 408(d)(2): all of an individual's IRAs are "treated as 1 contract" and all distributions in a year
as one distribution.

**What the software does.** Each Form 1099-R that the owner's Form 8606 figures puts on line 1 its pro rata
share of that owner's line 15a less the Line 15c Worksheet repayment reduction: box 1 (less any QCD, HSA funding
distribution or rolled-over part) times that amount, divided by line 7, never more than box 2a. Its line 2
exception, exception 12 and the 25 percent SIMPLE IRA amount are measured against that share. The qualified
disaster part stays in the share, because Form 5329 takes the qualified disaster recovery distributions off line
1 on its own. A form that can only be a conversion (line 7 is $0) puts $0 on line 1.

**Why we chose it.** Because every IRA of the owner is one contract and the year's distributions one
distribution, each distribution has the same nontaxable fraction, so its includible part is its share of line
15a. Box 2a overstates it by the basis share (the 10 percent was charged on too much before this change).

**Our best recommendation.** Keep. Confidence high.

**What we would like a reviewer to check.** Whether the repaid part on the Line 15c Worksheet (a qualified
birth or adoption, emergency, domestic abuse or terminal illness distribution repaid within 3 years) should also
leave line 1 when it was an early distribution, as the software does.

**Where it lives.** `form1099RFrontier: /form1099Rs/*/form5329Line1ItemAmount`,
`form8606: /form8606Line15aLessRepaymentReduction`, `form8606: /spouseForm8606Line15aLessRepaymentReduction`.

### IN-28 — Schedule 1 line 8a: an NOL deduction entered as one figure, without the year each loss arose

**The question.** A filer enters a net operating loss deduction for Schedule 1 line 8a as a single amount and does
not list the losses it comes from. Can that figure be deducted as entered?

**The IRS text.** IRC 172(a)(2), for a tax year beginning after 2020, allows "(A) the aggregate amount of net
operating losses arising in taxable years beginning before January 1, 2018, carried to such taxable year, plus
(B) the lesser of" the later losses and "80 percent of the excess (if any) of" taxable income figured without the
NOL, section 199A and section 250 deductions over the amount in (A). Instructions for Form 172 (Rev. December
2024), page 4: "when carryforwards can be used, they can only offset 80% of taxable income in future years."

**What the software does.** A positive single figure with no list of losses is not deducted. Line 8a stays
unresolved until the filer lists each loss carried in (the year it began and the amount still available) and, for
losses from 2018 on, the taxable income the 80 percent limit is measured against. The software then computes the
deduction. An answer of $0 still means no deduction. This follows the owner's direction of 2026-09-27 to fix the
uncapped route.

**Why.** The limit depends on the year each loss arose, and a single figure does not carry it. Taking the figure as
entered let a 2018-or-later loss through with no 80 percent limit. Capping the whole figure at 80 percent would
over-tax a filer whose losses predate 2018. Asking for the list is the only way to apply the statute.

**Our best recommendation.** Keep. The screen should ask for the list of losses and never the single figure.

**What we would like a reviewer to check.** That no filer can apply the section 172(a)(2) limit to a single figure
without the year each loss arose.

**Where it lives.** `income:/schedule1Line8aNetOperatingLossDeduction`, `income:/writableNetOperatingLossDeduction`,
`form172:/form172NolCarryIns`, `form172:/form172AllowedNolDeduction`.

### IN-29 — Schedule SE: fees of a fee-basis state or local government official

**The question.** A state or local official paid only by fees, in a position no federal-state social security
agreement covers, owes self-employment tax on the fees. The instructions do not say on which Schedule SE line the
fees go, or what happens to earned income when the same fees are also reported as wages. Which line does the
software use, and does it adjust earned income?

**The IRS text.** Instructions for Schedule SE (2025), page 4, Other Income and Losses Included in Net Earnings
From Self-Employment, item 8: "Fees as a state or local government employee if you were paid only on a fee basis
and the job wasn’t covered under a federal-state social security coverage agreement." Same page, Income and
Losses Not Included, item 1: "This includes services performed as a public official (except as a fee-basis
government employee as explained in item 8". IRC 1402(c)(1) (2024 edition, page 2511) excludes "the performance
of the functions of a public office, other than the functions of a public office of a State or a political
subdivision thereof with respect to fees received in any period in which the functions are performed in a
position compensated solely on a fee basis and in which such functions are not covered under an agreement".

**What the software does.** Two questions per filer: the fees, and whether the position was paid only by fees and
not covered by a section 218 agreement. With Yes, the fees are added to that filer's Schedule SE line 2; with No,
nothing is added. With the fees entered and the second question unanswered, Schedule SE line 3 and the
self-employment tax stay unanswered (the return waits for the answer); neither answer is assumed. The fees are
not added to income by this question (they are reported wherever the filer's other income entries report them),
and earned income for the EIC and the additional child tax credit counts the fees once on the self-employment
side, with no subtraction for fees a Form W-2 also reports. This is the maintainers' reading, not an owner
ruling.

**Why it was chosen.** Line 2 is the nonfarm line and is where the instructions route the other employee-type
inclusions (U.S. citizens employed by foreign governments). EIC Worksheet B line 1a is "the amount from Schedule
SE, Part I, line 3", and no printed worksheet gives a subtraction for this population, unlike the clergy
subtraction the EIC instructions do print.

**Our best recommendation.** Keep the line 2 placement. Ask the reviewer about the earned-income overlap.

**What we would like a reviewer to check.** Whether fees that also appear in Form W-2 box 1 should be taken out
of wages in EIC Step 5 (as the instructions do for clergy), so that they are not counted twice as earned income.

**Where it lives.** `scheduleSE:/primaryFilerScheduleSeFeeBasisOfficialFeesIncluded`,
`scheduleSE:/secondaryFilerScheduleSeFeeBasisOfficialFeesIncluded`, `scheduleSE:/selfEmploymentEarnedIncome`.
### IN-41 — Form 8582: a prior-year rental loss from a year without active participation

**The question.** A rental owner who actively participates in 2025 carries a prior-year unallowed loss from the
activity. Does that loss use the special allowance for rental real estate with active participation (up to
$25,000), and what does the software ask to decide it?

**The IRS text.** Instructions for Form 8582 (2025), page 10, Part IV: "Don’t enter a prior-year unallowed loss in
column (c) of Part IV unless you actively participated in the activity in both the year the loss arose and the
current tax year. If you didn’t actively participate in both years, enter the prior-year unallowed loss in column
(c) of Part V." IRC 469(i)(1) allows the offset for losses from rental real estate activities in which the
individual "actively participated in such taxable year (and if any portion of such loss or credit arose in another
taxable year, in such other taxable year)."

**What the software does.** For each rental with a prior-year loss and active participation in 2025 it asks one
question: did you actively participate in the year the loss arose? Yes keeps the loss in Part IV; No moves it to
Part V, where it offsets only passive income. The question has no default: until it is answered the rental's
passive-loss figures do not resolve.

**Why the call was made.** Either default misstates tax: assuming Yes lets a loss use the allowance the statute
denies it (the defect this entry records), assuming No denies it to a filer who did participate. A loss that built up
over several years with different answers is answered No, the conservative choice, because one answer per rental
cannot split it.

**Our best recommendation.** Keep. If filers with mixed histories appear, ask for the part of the loss that arose in
years of active participation.

**What we would like a reviewer to check.** That answering No for a mixed history is acceptable, and that the Part V
treatment is the same for a carried loss of a rental actively participated in this year.

**Where it lives.** `scheduleE: /rentalProperties/*/writableActivelyParticipatedWhenPriorYearLossArose`,
`scheduleE: /rentalProperties/*/priorYearLossQualifiesForActiveParticipation`,
`scheduleE: /rentalProperties/*/activeEligibleNet`, `scheduleE: /rentalProperties/*/nonActiveNet`.

### IN-30 — Form 6252 and Form 8824 amounts: where they go, and the installment answer

**The question.** Form 6252 line 26 and Form 8824 lines 22 and 14 go to different lines depending on the
property: Form 4797 line 4 or 5, Form 4797 line 10 or 16, or Schedule D line 4 or 11. The software asks the filer
which applies. Should it instead work out the holding period from dates? And when a like-kind exchange may also be
reported on the installment method, what should an unanswered installment question mean?

**The IRS text.** Instructions for Form 6252 (2025), Line 26: "For trade or business property held more than 1
year, enter this amount on Form 4797, line 4. If the property was held 1 year or less or you have an ordinary gain
from the sale of a noncapital asset (even if the holding period is more than 1 year), enter this amount on Form
4797, line 10". Instructions for Form 8824 (2025), Line 22: "Report a gain from the exchange of property used in
a trade or business (and other noncapital assets) on Form 4797, line 5 or line 16." Line 14: the gain or loss on
other property given up "must be reported on your tax return. Report gain or (loss) as if the exchange were a
sale." "If the installment method applies to this exchange: 1. See section 453(f)(6) to determine the installment
sale income taxable for this year and report it on Form 6252".

**What the software does.** The filer picks one of six destinations for each amount (section 1231 property,
ordinary noncapital property, capital asset short-term or long-term, personal-use property short-term or
long-term). The software does not derive the holding period from the dates: Form 8824 has no acquisition date for
the property given up, and a capital asset and a business asset held for the same time go to different lines.
An amount with no destination makes the return wait. A loss on personal-use property is reported nowhere (Pub. 544:
"Loss from the sale or exchange of property held for personal use is not deductible"). An unanswered installment
question reads as No when the return has no Form 6252, and makes the return wait when it has one.

**Our best recommendation.** Keep it. Where Form 6252 dates are present, the interview could check them against
the holding period the filer chooses.

**What we would like a reviewer to check.** Whether reading an unanswered installment question as No, on a return
with no Form 6252, is safe.

**Where it lives.** `form6252:/form6252Sales/*/writableLine26ReportingDestination`,
`form8824:/form8824Exchanges/*/writableLine22ReportingDestination`, `form8824:/form8824Exchanges/*/writableLine14ReportingDestination`,
`form8824:/form8824Exchanges/*/writableInstallmentMethodApplies`, `form4797:/form8824Exchanges/*/form4797InstallmentMethodApplies`.

### IN-50 — Form 8621 line 8: a QEF distribution above the year's inclusion

**The question.** A qualified electing fund pays the shareholder more (line 8b) than the shareholder includes in
income for the year (line 8a). How is the excess taxed, and which figure does the software ask for?

**The IRS text.** Instructions for Form 8621 (Rev. 12-2025), page 13, Line 8: "If the total amount distributed (line
8b) exceeds the amount included in income (line 8a), the excess is treated as distributed out of the most recently
accumulated earnings and profits. This amount is not taxable to you if you can satisfactorily demonstrate that the
excess was previously included in your income or the income of another U.S. person. [...] If the excess has not been
previously included in your income or the income of another U.S. person, then the excess is subject to tax according
to the rules of section 301(c)." IRC 1(h)(11)(C)(iii) excludes a dividend from a passive foreign investment company
from qualified dividend income.

**What the software does.** For any QEF it reads line 8b, asks how much of the excess over line 8a the filer can show
was previously included, and taxes the rest as an ordinary dividend on the Form 8621 dividend line (Form 1040 line
3b). Unanswered, the return waits.

**Why the call was made.** Section 301(c) makes a distribution a dividend to the extent of earnings and profits, and the
instructions place the excess in the most recently accumulated earnings and profits; the software therefore treats
it wholly as a dividend. A distribution beyond the fund's earnings and profits (a return of basis, then gain) is not
separately modelled.

**Our best recommendation.** Keep. Add a return-of-capital branch if a filer shows the fund lacks the earnings and
profits.

**What we would like a reviewer to check.** That line 8b is the right intake for a QEF shareholder who does not make
election B (the form says to complete lines 8 and 9 only for election B).

**Where it lives.** `form8621: /form8621Funds/*/writableLine8bExcessPreviouslyIncluded`,
`form8621: /form8621Funds/*/qefDistributionDividend`, `form8621: /form8621Funds/*/ordinaryDividends`.

### IN-51 — Form 8621 election B for several funds: the deferred tax

**The question.** A shareholder makes election B (to extend the time to pay tax on a QEF's undistributed earnings)
for two or more funds. Each fund's line 9c is its line 9a total tax less its line 9b tax without that fund's line 8e.
Can the deferred amounts simply be added?

**The IRS text.** IRC 1294(b)(1): the undistributed PFIC earnings tax liability "means, in the case of any taxpayer,
the excess of- (A) the tax imposed by this chapter for the taxable year, over (B) the tax which would be imposed by
this chapter for such year without regard to the inclusion in gross income under section 1293 of the undistributed
earnings of a qualified electing fund." Instructions for Form 8621 (Rev. 12-2025), page 13: "Line 9b. Calculate your
total tax as if your total taxable income did not include your share of the undistributed earnings of the QEF (line
8e)."

**What the software does.** With one deferring fund, nothing changes: line 9b is the figure. With two or more, it asks
once for the total tax figured without the undistributed earnings of all the deferring funds, and defers no more than
the total tax less that figure (and no more than the sum of the funds' line 9c). Unanswered, the return waits.

**Why the call was made.** The statute defines one excess for the taxpayer; each fund's line 9c is measured against
the whole return, so their sum overstates the excess when the inclusions push income into higher brackets. The
software cannot compute a second return, so the filer supplies the recomputed tax, as for line 9b.

**Our best recommendation.** Keep. Obtain Temp. Reg. 1.1294-1T to allocate the deferral among the funds, so each
printed line 9c also comes out right.

**What we would like a reviewer to check.** That the return-wide figure is the right cap when the funds' own line 9c
amounts are reported separately.

**Where it lives.** `form8621: /writableForm8621TotalTaxWithoutElectedUndistributedEarnings`,
`form8621: /form8621CurrentTaxDeferral`.

### IN-52 — Form 8621 Part I: when the value exceptions excuse it

**The question.** A shareholder of a passive foreign investment company must complete Part I of Form 8621 unless an
exception applies. Which exceptions does the software apply, and with what figures?

**The IRS text.** Instructions for Form 8621 (Rev. 12-2025), page 6: "Exception if aggregate value of shareholder’s
PFIC stock is $25,000 or less. A shareholder is not required to complete Part I with respect to a specific section 1291
fund if the shareholder meets the $25,000 exception on the last day of the shareholder’s tax year and the shareholder
does not receive an excess distribution from, or recognize gain on the sale or disposition of the stock of, the
section 1291 fund." The threshold counts "all PFIC stock ... owned directly or indirectly other than PFIC stock owned
through another U.S. person or PFIC stock owned through another PFIC", and "Shareholders filing a joint return have a
combined threshold of $50,000". A second exception covers indirect ownership of a section 1291 fund worth "$5,000 or
less".

**What the software does.** For each fund it shows Part I unless the fund is a section 1291 fund with no excess
distribution or disposition gain and either the Part I line 4 values of the filer's funds (leaving out stock owned
through another U.S. person or PFIC) total $25,000 or less ($50,000 on a joint return), or the fund is owned
indirectly and its line 4 value is $5,000 or less.

**Why the call was made.** These are the exceptions the instructions state with figures the return already has. The
software treats the list of funds entered as all the PFIC stock the filer owns, uses line 4 as the value tested, and
prints Part I whenever an answer the exceptions need is missing: printing an unneeded Part I costs nothing in tax.

**Our best recommendation.** Keep. Add the estate, trust and chain-of-ownership exceptions if filers need them.

**What we would like a reviewer to check.** That Part I line 4 (the shares' fair market value) is the value the $5,000
test means by the shareholder's proportionate share for indirect stock.

**Where it lives.** `form8621: /form8621Funds/*/partIRequired`, `form8621: /form8621PartIAggregateValue`.

### IN-53 — Form 1099-MISC box 3: compensation of an H-2A agricultural worker

**The question.** An agricultural employer reports in Form 1099-MISC box 3 the pay of an H-2A visa worker who did
not give a taxpayer identification number. The recipient instruction for box 3 says to report box 3 "Generally"
as other income on Schedule 1. Is this amount other income (Schedule 1 line 8z) or wages (Form 1040 line 1h)?

**The IRS text.** Instructions for Forms 1099-MISC and 1099-NEC (2025), page 6, Box 3: "Foreign agricultural
workers. Report in box 3 compensation of $600 or more paid in a calendar year to an H-2A visa agricultural worker
who did not give you a valid TIN." Publication 225 (2025), page 86: "The employer must report the wages and
backup withholding on Form 1099-MISC." IRC 32(c)(2)(A)(i), earned income means "wages, salaries, tips, and other
employee compensation". Form 1040 (2025), page 1: line 1a is "Total amount from
Form(s) W-2, box 1"; line 1h is "Other earned income".

**What the software does.** The box 3 question offers a fourth answer, pay for farm work on an H-2A visa. That
amount leaves Schedule 1 line 8z and is added to the payee filer's Form 1040 line 1h, so it counts as earned
income (for example for the earned income credit). It owes no Schedule SE and no Form 8919: H-2A pay is exempt
from social security and Medicare tax. Box 4 backup withholding is credited as before. On a community-property
return that allocates income the return is refused until the wage split is built.

**Why.** The statute is clear that the amount is employee compensation, and Publication 225 calls it wages. Line
1a is only the Form W-2 box 1 total, and this pay is on no Form W-2, so line 1h is the line left for wages no Form
W-2 reports (the same line the software uses for foreign-government wages with no Form W-2). The recipient
instruction's "Generally" leaves room for this case.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether the IRS expects line 1h (with a type entered) or line 1a for
these wages, and whether a 1040-NR filer's line differs.

**Where it lives.** `form1099Misc: /form1099Miscs/*/isH2aAgriculturalWorkerCompensation`,
`form1099Misc: /form1099Miscs/*/h2aAgriculturalWorkerCompensation`,
`form1099Misc: /primaryFilerForm1099MiscH2aCompensation`, `form1099Misc: /secondaryFilerForm1099MiscH2aCompensation`,
`income: /primaryFilerOtherEarnedIncome`.

### IN-54 — Community property: a taxable state or local income tax refund on a separate return

**The question.** Spouses domiciled in a community-property state file separately and allocate community income
on Form 8958. One return has a taxable state or local income tax refund (Schedule 1 line 1). Is the refund
community income, split half to each spouse, or does it belong to one spouse?

**The IRS text.** Form 8958 (Rev. November 2023), page 4, Line 4: "Identify the state income tax refund from each
payer on separate lines." Publication 525 (2025), page 23, Recoveries, for a filer not filing a joint Form 1040
with the same person: "any refund of a deduction claimed on that state or local income tax return must be
allocated to the person that paid the expense. If both persons paid a portion of the expense, allocate the refund
based on your individual portion." Publication 555 (12-2024), page 7, Personal expenses: "If these expenses are
paid from community funds, divide the deduction equally between you and your spouse." Publication 555 is silent
on refunds as such.

**What the software does.** A separate return that allocates community income and carries a taxable refund is
refused, with the reason, until the split is built. The build follows this reading.

**Our reading.** The refund follows the funds that paid the tax. Tax paid from community funds (including income
tax withheld from community wages, which Publication 555 credits half to each spouse) was paid half by each
spouse, so its refund is split evenly; tax paid from one spouse's separate funds is refunded to that spouse. Each
return then includes only the part its own earlier deduction made taxable. Form 8958 gives the refund a line of
its own, which it would not need if the refund were never split.

**Our best recommendation.** Keep the refusal until the split is built, then build this reading: one question
per refund (paid from community funds, separate funds, or both, with the share).

**What we would like a reviewer to check.** Whether a refund of tax paid from community funds is community
property under every community-property state's law, and whether the tax-benefit test should be applied per
spouse, as we read it.

**Where it lives.** `filers: /communityPropertyAllocationInputsComplete` (the refusal),
`income: /taxableStateAndLocalIncomeTaxRefunds`.

### IN-55 — Community property: income a spouse kept from the other spouse (IRC 66(b))

**The question.** IRC 66(b) lets the IRS disregard community-property law for income a spouse treated as solely
theirs without telling the other spouse. Must the software ask about this and, if so, put the whole item on the
filer's return?

**The IRS text.** IRC 66(b): "The Secretary may disallow the benefits of any community property law to any
taxpayer with respect to any income if such taxpayer acted as if solely entitled to such income and failed to
notify the taxpayer's spouse before the due date (including extensions) for filing the return". Publication 555
(12-2024), page 8: "You are responsible for reporting all of that income item if: 1. You treat the item as if only
you are entitled to the income, and 2. You don't notify your spouse of the nature and amount of the income by the
due date for filing the return (including extensions)."

**What the software does.** It asks no such question. A filer who allocates community income reports half of each
community item, as state law provides.

**Why.** The statute makes this a power of the IRS ("may disallow"), exercised after the return, not a rule the
return applies to itself; the owner's standing rule follows the statute when it is clear. A filer who splits an
item on Form 8958 is, on the return itself, treating it as community income.

**Our best recommendation.** Keep, but we record that Publication 555 words the rule as the filer's own duty.

**What we would like a reviewer to check.** Whether a return preparer should ask a filer who allocates income
whether any item was kept from the spouse, and report that item in full, as Publication 555's wording suggests.

**Where it lives.** `filers: /isCommunityPropertyAllocationReturn`, `form8958` (the allocation lines).
### IN-56 — Form 1099-PATR distributions on a return without Schedule F

**The question.** A cooperative reports patronage dividends, nonpatronage distributions, per-unit retain allocations
and redemptions on Form 1099-PATR (boxes 1, 2, 3 and 5). A farmer puts them on Schedule F. Where do they go on a
return that does not file Schedule F?

**The IRS text.** Form 1099-PATR (Rev. 4-2025), page 4, Instructions for Recipient: "Generally, if you are an
individual, report any amounts shown in boxes 1, 2, 3, and 5 as ordinary income, unless nontaxable, on your income tax
return." Box 1: "Any dividends paid on (1) property bought for personal use or (2) capital assets or depreciable
property used in your business are not taxable." 2025 Instructions for Form 1040, page 92, Schedule 1 line 8z: "Other
income. Use line 8z to report any taxable income not reported elsewhere". 2025 Instructions for Schedule C, line 6,
lists "Amounts you received in your trade or business as shown on Form 1099-PATR."

**What the software does.** On a return that does not claim Schedule F farm income, the boxes 1, 2, 3 and 5 total goes
to Schedule 1 line 8z as ordinary income, less the part the filer says was received in a nonfarm business (that part is
Schedule C line 6 other income for the business) and less the box 1 dividends the filer says were paid on personal-use
purchases or on capital or depreciable business assets (not taxable). On a farm return it stays on Schedule F lines 3a
and 3b. The box 4 backup withholding is credited on Form 1040 line 25b either way.

**Why the call was made.** The recipient instructions make the amounts ordinary income by default, and without
Schedule F no printed line names them, so line 8z is the line the Form 1040 instructions give for such income. The
alternative the software had, reaching no line while crediting the withholding, under-reported income. Refusing the
return was the other alternative and was not needed, because a line exists.

**Our best recommendation.** Keep. The two questions are asked at return level (the nontaxable box 1 amount) and per
Schedule C business (the amount received in it), not per Form 1099-PATR.

**What we would like a reviewer to check.** That line 8z, rather than Schedule C line 6, is right for an individual
with no business, and that nonpatronage distributions in box 2 are ordinary income there too.

**Where it lives.** `income: /schedule1Line8zCooperativeDistributionsWithoutScheduleF`, read by
`income: /schedule1TotalOtherIncome`.

### IN-57 — Capital gain distributions received as a nominee, and their 25% and 28% parts

**The question.** A Form 1099-DIV in the filer's name shows capital gain distributions (box 2a), part of which belongs
to someone else. Box 2b (unrecaptured section 1250 gain) and box 2d (collectibles gain) are parts of box 2a. How much
of boxes 2b and 2d leaves with the nominee share?

**The IRS text.** Instructions for Schedule D (2025), page 2: "If you received capital gain distributions as a
nominee (that is, they were paid to you but actually belong to someone else), report on Schedule D, line 13, only the
amount that belongs to you. Attach a statement showing the full amount you received and the amount you received as a
nominee." Publication 550 (2025), Nominees: "report only the amount that belongs to you on Form 1040 or 1040-SR, line
7a; or Schedule D (Form 1040), line 13, whichever is appropriate." Neither says how boxes 2b and 2d divide.

**What the software does.** It asks, per Form 1099-DIV, how much of box 2a belongs to someone else, and reports only
the rest on line 13 (or line 7a). Boxes 2b and 2d are reduced in the same proportion as box 2a: the filer keeps box 2b
times the part of box 2a the filer keeps, divided by all of box 2a (the same for box 2d).

**Why.** A nominee holds shares of the same fund for the owner, so the owner's share of one distribution is the same
share of each of its parts. Asking the filer for two more split figures would add questions a nominee usually cannot
answer from the form.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether a nominee arrangement can give the owner a different mix of box
2b or box 2d than of box 2a, so that the parts should be asked instead.

**Where it lives.** `dividendReports: /dividendReports/*/writableNomineeCapitalGainDistributions`,
`dividendReports: /dividendReports/*/capitalGainDistributionsBelongingToFiler`,
`dividendReports: /dividendReports/*/unrecapturedSection1250GainBelongingToFiler`,
`dividendReports: /dividendReports/*/collectiblesGainBelongingToFiler`, `dividendReports: /capitalGainDistributions`.

### IN-58 — Schedule K-1 (Form 8865): the publicly traded partnership question and the foreign marker

**The question.** A U.S. partner in a foreign partnership receives Schedule K-1 (Form 8865). It is entered as a partnership
K-1, but it prints no item D ("Check if this is a publicly traded partnership"), which the software requires on every
partnership K-1. Should the question be asked of this partner, or waived? And how does the software know the item is from a
foreign partnership?

**The IRS text.** IRC 469(k)(2): "the term 'publicly traded partnership' means any partnership if (A) interests in such
partnership are traded on an established securities market, or (B) interests in such partnership are readily tradable on a
secondary market (or the substantial equivalent thereof)." Schedule K-1 (Form 8865) (2025), Part I, prints items A1, A2 and B
only. Form 8865 is the "Return of U.S. Persons With Respect to Certain Foreign Partnerships".

**What the software does.** It asks the question of a Schedule K-1 (Form 8865) partner in the statute's words ("Are interests
in this partnership traded on an established securities market, or readily tradable on a secondary market?"), and the item
stays unfinished until it is answered. The item is marked foreign by the Schedule E line 28 column (c) "foreign partnership"
answer, which is set for every Schedule K-1 (Form 8865).

**Why.** The publicly traded partnership rule reaches any partnership, foreign or not, and it changes how the passive loss
rules treat the item, so the form's silence does not make the answer irrelevant. A foreign partnership that files Form 8865
needs no other marker: column (c) is the printed place for it.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether a foreign partnership's interests traded only on a foreign exchange count
as traded on an "established securities market" for this purpose.

**Where it lives.** `scheduleE: /formK1s/*/writableIsPubliclyTradedPartnership`, `scheduleE: /formK1s/*/itemDUnanswered`,
`scheduleE: /formK1s/*/writableLine28cForeignPartnership`.

### IN-59 — A limited partner's self-employment earnings from Schedule K-1 box 14 code A

**The question.** Schedule SE tells a limited partner to include only guaranteed payments for services. Should the software
take anything out of the Schedule K-1 (Form 1065) box 14 code A amount for a limited partner, or use the box as the
partnership issued it?

**The IRS text.** Instructions for Schedule SE (2025), page 3: "enter on line 1a or line 2, whichever applies, the amount of
net earnings from self-employment from box 14, code A, of Schedule K-1 (Form 1065). [...] Limited partners should include only
guaranteed payments for services actually rendered to or on behalf of the partnership." Partner's Instructions for Schedule
K-1 (Form 1065) (2025), page 22, Code A: "If you're a general partner, reduce this amount before entering it on Schedule SE
(Form 1040) by any section 179 expense deduction claimed, unreimbursed partnership expenses claimed, and depletion claimed on
oil and gas properties." The partner's instructions give no reduction for a limited partner.

**What the software does.** Schedule SE takes box 14 code A as issued. It does not ask a limited partner to subtract anything.

**Why.** The partnership figures box 14 code A for each partner, and for a limited partner it reports the guaranteed
payments for services; the partner's instructions list reductions for general partners only, and whether a partner is a
limited partner for this purpose (section 1402(a)(13)) is settled when the partnership fills in the box.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether a limited partner whose box 14 code A includes more than guaranteed
payments should be asked to correct it on the return rather than ask the partnership for a corrected K-1.

**Where it lives.** `scheduleE: /primaryFilerK1SeEarnings`, `scheduleSE: /primaryFilerSeNetProfitOrLoss`.

### IN-60 — The lump-sum election for a filer who must use Pub. 590-A Appendix B

**The question.** A filer who receives social security benefits, contributes to a traditional IRA and is covered by a
retirement plan at work figures both the IRA deduction and the taxable benefits on the Appendix B worksheets of
Pub. 590-A, not on Worksheet 1 of Pub. 915. If that filer also receives a lump-sum payment for earlier years and elects
the lump-sum method, Worksheet 4 lines 3 through 7 say "Enter the amount from Worksheet 1". Which IRA deduction goes
into Worksheet 4 line 7, and is the IRA deduction itself refigured under the election?

**The IRS text.** Publication 915 (2025), page 5: "You contributed to a traditional individual retirement arrangement
(IRA) and you or your spouse is covered by a retirement plan at work. In this situation, you must use the special
worksheets in Appendix B of Pub. 590-A to figure both your IRA deduction and your taxable benefits." Page 18,
Worksheet 4: "7. Enter the amount from Worksheet 1, line 7". Publication 590-A (2025), page 56, Appendix B
Worksheet 3: "2. Deduction(s) from line 7 of Worksheet(s) 2"; page 55, Worksheet 2 line 7: "Enter this amount on your
Schedule 1 (Form 1040), line 20."; page 54, Worksheet 1 line 2: "Enter the amount in box 5 of all Forms SSA-1099 and
RRB-1099". Neither publication speaks of the two together.

**What the software does.** For that filer, Worksheet 4 reads Appendix B Worksheet 3 in place of Worksheet 1: its line 7
subtracts the other adjustments and the IRA deduction as claimed on Schedule 1 line 20. The IRA deduction is figured once,
on Appendix B Worksheet 1, from all of box 5, and is not refigured under the election.

**Why.** Pub. 915 sends this filer to Appendix B for the taxable benefits, so Appendix B Worksheet 3 is the worksheet
Worksheet 4 builds on, and Worksheet 3 subtracts the deduction Worksheet 2 produced. Appendix B Worksheet 1 line 2 enters
the whole of box 5, with no lump-sum adjustment, so the deduction stays as claimed. Before this reading the software
left the IRA deduction out of Worksheet 4 for this filer, which made the election help less than it should.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether the IRA deduction (through the modified AGI of section
219(g)(3)(A)(ii)) should itself be refigured with the benefits the election includes, which would change Appendix B
Worksheet 1 line 2 for an electing filer.

**Where it lives.** `socialSecurity: /lumpSumElectionWksht4Line8`, `iraDeduction: /appendixBSsIraWorksheetsApply`.

### IN-62 — Section 469(g): releasing a disposed passive activity's losses beside other passive activities

**The question.** A filer sells the entire interest in a passive activity (a rental, or a partnership or S corporation
activity) to an unrelated person in a fully taxable sale. The activity has a current-year result and prior-year
unallowed losses. The statute releases "the excess of" the activity's loss "over any net income or gain for such
taxable year from all other passive activities". Must the software net the loss against the other passive activities
before releasing it?

**The IRS text.** IRC 469(g)(1)(A) (2024 edition, page 1636): "If all gain or loss realized on such disposition is
recognized, the excess of" the loss from the activity "over" the "net income or gain for such taxable year from all
other passive activities" "shall be treated as a loss which is not from a passive activity." Instructions for Form 8582
(2025), page 9, Disposition of an Entire Interest: "If you disposed of your entire interest in a passive activity or a
former passive activity to an unrelated person in a fully taxable transaction during the tax year, your losses
allocable to the activity for the year aren’t limited by the PAL rules." Reporting an Entire Disposition: "Combine all
income and losses (including any prior-year unallowed losses) from the activity for the tax year to see if you have an
overall gain or loss." An overall loss is not entered on Form 8582; an overall gain is reported in Part IV or V.

**What the software does.** It follows the instructions' procedure. For the disposed activity it combines the
current-year result (after the at-risk limit) with the prior-year unallowed loss. An overall loss is deducted in full as
a nonpassive loss and the activity contributes nothing to Form 8582; an overall gain stays in the Form 8582 pool as
usual. Other passive activities on the return are not read. It applies to rentals, partnership and S corporation
activities, publicly traded partnerships (on the entire disposition of the PTP interest) and former passive activities
(whose whole carry-in is released).

**Why the call was made.** The two procedures give the same taxable income: the part of the loss the statute leaves
passive equals the other activities' net passive income it is measured against, and that part is then allowed against
that income on Form 8582. The instructions' procedure needs no cross-activity figure, which is why the earlier build
refused a disposition beside other passive activities; it is now released.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** That the equality holds where the character of the income matters beyond
taxable income (the net investment income tax on Form 8960), and that a rental disposed of with the $25,000 special
allowance in play is right to take its overall loss outside Form 8582 rather than through Part II.

**Where it lives.** `scheduleE: /formK1s/*/dispositionReleasedLoss`, `scheduleE: /formK1s/*/partIINonpassivePartBeforeSection179`,
`scheduleE: /formK1s/*/ptpDispositionReleasedLoss`, `scheduleE: /formK1s/*/formerPassiveDispositionReleasedLoss`,
`scheduleE: /rentalProperties/*/dispositionReleasesOverallLoss`, `scheduleE: /rentalProperties/*/repAwareNonpassiveNet`.

### IN-63 — Section 469(g): the disposed activities still refused

**The question.** Which disposed passive activities does the software still refuse, and why?

**The IRS text.** Instructions for Form 8582 (2025), page 9: "Combine all income and losses (including any prior-year
unallowed losses) from the activity for the tax year to see if you have an overall gain or loss." The combination is
per activity.

**What the software does.** It refuses (1) a Schedule K-1 that carries a box 22 or box 23 statement splitting it into
several activities, because the prior-year unallowed loss is asked once for the whole K-1 and cannot be combined
activity by activity; and (2) a passive, non-PTP K-1 with a box 12 section 179 deduction, because whether the activity
has an overall loss depends on the section 179 share, and that share depends, through the Form 4562 line 11 business
income limitation, on whether the released loss is nonpassive.

**Why the call was made.** Both are missing pieces the software does not have (a per-activity carry-in; an ordering
for the section 179 limitation), not open readings of the law. Guessing either would misstate the release.

**Our best recommendation.** Build a per-activity carry-in under the statements, and figure the disposed elector's
section 179 share before the release decision.

**What we would like a reviewer to check.** Whether practice figures the Form 4562 line 11 limitation before or after
releasing a disposed activity's loss.

**Where it lives.** `scheduleE: /formK1s/*/entireDispositionReleaseNotBuilt`,
`scheduleE: /knockoutPassiveEntireDispositionReleaseNotBuilt`.

### IN-64 — Schedule SE line 1a: which partnership is a farm partnership

**The question.** Schedule SE line 1a takes the self-employment earnings of "farm partnerships" and line 2 takes those of
every other partnership. The Schedule K-1 (Form 1065) box 14 code A amount does not say which kind of partnership issued
it. How does the software tell them apart?

**The IRS text.** Schedule SE (2025), line 1a: "Net farm profit or (loss) from Schedule F, line 34, and farm partnerships,
Schedule K-1 (Form 1065), box 14, code A"; line 2: "Schedule K-1 (Form 1065), box 14, code A (other than farming)".
Instructions for Schedule SE (2025), page 3: "include on line 1a or line 2, whichever applies, the amount of net earnings
from self-employment from box 14, code A, of Schedule K-1 (Form 1065)." Partner's Instructions for Schedule K-1 (Form 1065)
(2025), page 31, Code AN: "If the partnership is involved in a farming or fishing business, it will report your distributive
share of gross income and gains, as well as the losses and deductions attributable to such business activities."

**What the software does.** A K-1 that reports box 20 code AN is a farm partnership: its box 14 code A goes on the
partner's own line 1a, and line 2 takes the partner's box 14 code A less that amount. A partner who asks for the
calculated farm optional method beside a farm partnership K-1 is not computed (the calculation reads Schedule F line 9
alone, while gross farm income also includes the K-1's box 14 code B).

**Why the call was made.** Code AN is the only place the K-1 says the partnership is in a farming business. Line 3
combines lines 1a and 2, so the placement does not change self-employment tax; it changes the printed lines and what the
farm optional method skips. Code AN also covers a fishing business, so a fishing partnership's box 14 code A prints on
line 1a, where a nonfarm amount belongs; no tax figure moves.

**Our best recommendation.** Keep, and ask the partner whether a code AN partnership farms or fishes if the printed line
matters to a reviewer.

**What we would like a reviewer to check.** Whether practice treats code AN as marking a farm partnership for Schedule SE
line 1a.

**Where it lives.** `scheduleE: /formK1s/*/reportsFarmingOrFishingBusiness`, `scheduleSE: /primaryFilerScheduleSeLine1a`,
`scheduleSE: /primaryFilerScheduleSeLine2`.

### IN-65 — Section 7873: a tribe member's fishing rights income is left off the return

**The question.** Section 1402(a)(15) applies the special rules of section 7873 to a member of an Indian tribe. Section
7873 exempts income from a fishing rights-related activity of the tribe from income tax and self-employment tax. Nothing on
Schedule C or Schedule SE names this income. How does the return keep it untaxed?

**The IRS text.** IRC 7873(a)(1): "No tax shall be imposed by subtitle A on income derived-" "by a member of an Indian tribe
directly or through a qualified Indian entity, or" "by a qualified Indian entity," "from a fishing rights-related activity
of such tribe." Publication 525 (2025), page 34, Indian fishing rights: a member of a qualified tribe with fishing rights
secured as of March 17, 1988, does not include in income "amounts you receive from activities" related to those fishing
rights, and that income is not "subject to income tax, self-employment tax, or" employment taxes. IRC 265(a)(1) disallows
"Any amount otherwise allowable as a deduction which is allocable to one or more classes of income other than interest"
where that income is "wholly exempt from the taxes imposed by this subtitle".

**What the software does.** The income is not reported: the Schedule C business list and its line 1 gross receipts tell the
filer to leave it out, and the expenses allocable to it are not deducted. A business that is wholly such an activity is
not a Schedule C, so it reaches neither Schedule 1 line 3 nor Schedule SE line 2 or line 3, nor the earned income, IRA
compensation and qualified business income figures that read those lines. A Form 1099-MISC that reports such income
(box 5 fishing boat proceeds, box 11 fish purchased for resale) is excused from the Schedule C receipts reconciliation by
its per-document attestation that the income is reported correctly, which now names this case.

**Why the call was made.** The statute is clear and the publication tells the member not to include the income, so the
exclusion is where the income enters the return, not a subtraction after it. A per-business attestation that subtracts the
income later would have to reach every figure that reads Schedule C net profit (Schedule SE, the earned income credit, IRA
compensation, the qualified business income deduction) and would still leave the allocable expenses to be removed; leaving
the income and its expenses out reaches all of them at once. Section 265(a)(1) is why the expenses go with the income.

**Our best recommendation.** Keep. Not covered: income a member derives through a qualified Indian entity that issues a
Schedule K-1 (the K-1 is transcribed as issued), and wages from such an entity reported on a Form W-2.

**What we would like a reviewer to check.** Whether a member with a mixed business (fishing rights fish and other fish)
should report only the non-rights part, and whether section 265(a)(1) reaches the shared expenses of such a business.

**Where it lives.** `scheduleC: /scheduleCs`, `scheduleC: /scheduleCs/*/writableGrossReceipts`, `form1099Misc: /form1099Miscs/*/writableScheduleCReceiptsReportedCorrectly`.

### IN-66 — Form 1099-G box 3 left blank: which year the box 2 refund is for

**The question.** Box 2 of Form 1099-G reports a state or local income tax refund, and box 3 names the tax year it is
for. The 2024 State and Local Income Tax Refund Worksheet applies only to a refund of tax paid in 2024; a refund for any
other year is figured under Publication 525. When the payer leaves box 3 blank, which year is the refund for?

**The IRS text.** Instructions for Form 1099-G (Rev. 3-2024), page 2, Box 3: "No entry is required in box 3 if the
refund, credit, or offset is for the current tax year. If it is for any other tax year, enter the year". 2025
Instructions for Form 1040, page 88, Schedule 1 line 1: "If the refund was for a tax you paid in 2024 and you deducted
state and local income taxes on your 2024 Schedule A, use the State and Local Income Tax Refund Worksheet"; Exception 1:
"You received a refund in 2025 that is for a tax year other than 2024."

**What the software does.** When box 3 shows a year, that year decides: 2024 goes through the 2024 worksheet, any other
year through Publication 525 (or the no-tax-benefit route). When box 3 is blank, the filer is asked whether the refund is
for tax paid for 2024; until answered, Schedule 1 line 1 is not computed.

**Why the call was made.** The payer instruction's "current tax year" does not say whose current year: the year the
form reports payments for (2025), or the year the refund relates to on the recipient's return. Payers commonly issue the
2025 form for refunds of 2024 tax, and both readings are in use. Reading a blank as 2024 would put a refund of an older
year's tax through the wrong worksheet; reading it as 2025 would send every such refund to Publication 525. The filer
knows which return the refund came from, so the software asks. The earlier refund-only screen asked the same question for
every document.

**Our best recommendation.** Keep. The software can prefill "yes" when the refund's source is known to be the 2024 return.

**What we would like a reviewer to check.** Whether the IRS reads a blank box 3 on a 2025 Form 1099-G as 2024 for
recipients, which would let the question be dropped.

**Where it lives.** `unemployment: /form1099Gs/*/writableBox2RefundIsForTaxYear2024WhenBox3Blank`,
`unemployment: /form1099Gs/*/box2RefundIsForTaxYear2024`, read by `income: /form1099GPersonalBox2RefundTotal`.

### IN-67 — Form 1099-G box 6 taxable grants: Schedule 1 line 8z or the business schedule

**The question.** Box 6 of Form 1099-G reports taxable grants from a federal, state or local government. The recipient
instruction names no line. Where does the grant go?

**The IRS text.** Form 1099-G (Rev. 3-2024), page 5, Instructions for Recipient: "Box 6. Shows taxable grants you
received from a federal, state, or local government." 2025 Instructions for Form 1040, page 92, line 8z: "Other income.
Use line 8z to report any taxable income not reported elsewhere". 2025 Instructions for Schedule C, page 5, line 6:
"Report on line 6 business income not reported elsewhere in Part I."

**What the software does.** For each Form 1099-G with a box 6 amount the filer answers whether the grant is income of
a trade or business (including farming). No: the grant goes on Schedule 1 line 8z (typed "Taxable grants (Form 1099-G)").
Yes: it is not entered on Schedule 1; the filer includes it in the business's other income (Schedule C line 6 or
Schedule F line 8). Unanswered with an amount: Schedule 1 line 9 is not computed.

**Why the call was made.** A grant is gross income (IRC 61(a)); which line takes it depends on whether it is income of a
business, which the form does not say. Line 8z is the line for taxable income reported nowhere else, and Schedule C
line 6 is the line for business income not reported elsewhere. Putting every grant on line 8z would leave business
grants out of self-employment income; refusing was not needed because each answer has a line.

**Our best recommendation.** Keep. A later build can link the grant to one Schedule C business and add it to line 6.

**What we would like a reviewer to check.** Whether an energy-conservation or home-related grant can be nontaxable
(the payer reports only taxable grants in box 6) and whether a grant for rental property belongs on Schedule E instead.

**Where it lives.** `unemployment: /form1099Gs/*/writableTaxableGrantIsTradeOrBusinessIncome`,
`unemployment: /form1099Gs/*/taxableGrantForScheduleOneLine8z`, `income: /schedule1Line8zForm1099GTaxableGrants`.

### IN-68 — Form 1099-G boxes 7 and 9 on Schedule F

**The question.** Box 7 reports agriculture payments and box 9 market gain on CCC loans; the recipient instructions
send both to the Schedule F instructions. The filer also types Schedule F lines 4b and 6a/6b as totals that include
the Form 1099-G amounts. How do the document amounts reach Schedule F without counting twice?

**The IRS text.** 2025 Instructions for Schedule F, page 4: the Forms 1099 table sends Form 1099-G "For disaster
payments" to line 6a and "For other agricultural program payments" to line 4a, and "Include the Form 1099 or
CCC-1099-G amounts in the total amount reported on that line." Lines 4a and 4b: "On line 4b, report only the taxable
amount. For example, don't report the market gain shown on Form CCC-1099-G on line 4b if you elected to report CCC
loan proceeds as income". Publication 225 (2025), page 11: a landlord who does not materially participate reports farm
income on Form 4835.

**What the software does.** For each box 7 amount the filer says whether it is a crop disaster payment. On a return
that claims Schedule F: when line 4b is left blank, it takes the box 7 program payments plus box 9 market gain (box 9
left out when the CCC loan election is in effect); a typed line 4b is used as entered. The box 7 disaster payments are a
floor for line 6a, like Form 1099-MISC crop insurance: line 6a must be entered and at least that amount, or line 6b is not
computed. A return with a box 7 or box 9 amount that claims neither Schedule F nor a Form 4835 farm rental is refused.

**Why the call was made.** The typed lines are totals the instructions tell the filer to include the documents in, so
adding the documents on top would count them twice; filling only a blank line (the Form 1099-PATR line 3b rule in this
software) reaches the filer who entered the documents and nothing else. The disaster payment follows the crop insurance
floor already built for Form 1099-MISC box 9. A filer with neither farm schedule has no line the sources give, so the
return is refused rather than placed on a line the instructions do not name.

**Our best recommendation.** Keep. A Form 4835 farm rental does not yet fill its line 3b from the documents (the filer
types it).

**What we would like a reviewer to check.** Whether a blank line 4b should default to the full program payments when a
cost-sharing exclusion may apply, and whether a non-farmer landowner's Conservation Reserve Program payments belong on
Schedule 1 line 8z or Schedule E rather than being refused.

**Where it lives.** `unemployment: /form1099Gs/*/writableAgriculturePaymentsAreCropDisasterPayments`,
`scheduleF: /form1099GScheduleFLine4bPayments`, `scheduleF: /scheduleFLine4b`, `scheduleF: /scheduleFLine6aDocumentedProceeds`,
`unemployment: /knockoutForm1099GAgriculturePaymentsWithoutAFarmSchedule`.

### IN-69 — A publicly traded partnership's box 10 gain and Form 4952: line 4d, not the partnership's line 4a amount

**The question.** A publicly traded partnership's overall gain is nonpassive income, and the partner instructions say
it is included in investment income for Form 4952. When the overall gain comes from the partnership's box 10 net
section 1231 gain (reported on Form 4797), does that part go on Form 4952 line 4a with the rest of the partnership's
income, or somewhere else?

**The IRS text.** 2025 Partner's Instructions for Schedule K-1 (Form 1065), page 10: "If you have an overall gain from a
PTP, the net gain is nonpassive income. In addition, the nonpassive income is included in investment income to figure
your investment interest expense deduction." 2025 Instructions for Form 4952, page 3, line 4a: "Also include on line 4a
(or 4d, if applicable) net passive income from a passive activity of a publicly traded partnership" and "Don’t include
on line 4a any net gain from the disposition of property held for investment. Instead, enter it on line 4d." 2025
Instructions for Form 8582, page 15: "you may be able to include the nonpassive income in investment income".

**What the software does.** The partnership's amount on Form 4952 line 4a (and so line 4h) is the positive part of the
smaller of its Schedule E result and its result with box 10 combined. A box 10 gain therefore adds nothing there: that
part of the gain is a net gain from a disposition, which the filer enters on line 4d (with the line 4e and 4g rules for
net capital gain). A box 10 passive loss lowers the amount, because only the net gain portion is nonpassive income.

**Why the call was made.** Form 4952 sends a disposition gain to line 4d and keeps it off line 4a, and the section 1231
gain may become net capital gain, which counts as investment income only by election (IRC 163(d)(4)(B)). Adding it
through line 4a would bypass that election. Line 4d is entered by the filer in this software, so the software does not
compute it twice.

**Our best recommendation.** Keep. A later build could fill line 4d from the partnership's box 10 gain when the filer
leaves it blank.

**What we would like a reviewer to check.** Whether a publicly traded partnership's section 1231 gain is gain from the
disposition of "property held for investment" for line 4d at all, given that the partner does not hold the partnership's
business assets for investment.

**Where it lives.** `scheduleE: /formK1s/*/ptpNonpassiveGainInInvestmentIncome`,
`form4952: /writableNetGainFromInvestmentPropertyDispositions`.

### IN-70 — A publicly traded partnership's passive box 10 loss beside its own Schedule E income

**The question.** A publicly traded partnership reports Schedule E income and a passive box 10 net section 1231 loss
(reported on Form 4797). How much of the loss is allowed, on which form, and how is the Schedule E income printed?

**The IRS text.** 2025 Partner's Instructions for Schedule K-1 (Form 1065), page 10: "If you have an overall gain, the
net gain portion (total gain minus total losses) is nonpassive income. On the form or schedule you normally use, report
the net gain portion as nonpassive income and the remaining income and the total losses as passive income and loss";
"If you have an overall loss ... the losses are allowed to the extent of the income, and the excess loss is carried
forward"; and the example: "If you have Schedule E (Form 1040) income of $8,000, and a Form 4797 ... prior-year
unallowed loss of $3,500 ... you have a $4,500 overall gain ... report the $4,500 net gain as nonpassive income in column
(k). In column (h), report the remaining Schedule E (Form 1040) gain of $3,500". 2025 Instructions for Form 8582, page
13, Part IX line 1b: "Enter any net income from the activity that’s reported on the same form or schedule".

**What the software does.** The loss is allowed on Form 4797 line 2 up to the partnership's Schedule E-side income; the
rest is carried forward. The income it is allowed against prints in Schedule E line 28 column (h), and only the net
gain portion prints in column (k) and counts for Form 4952. On the entire disposition of the interest the whole loss is
allowed on Form 4797. A Schedule E side at or below zero allows none of the loss.

**Why the call was made.** The instructions allow the losses to the extent of the income and allocate an unallowed loss
among the forms by each form's net loss (Form 8582 Part IX); a Schedule E side with net income has no net loss, so the
whole unallowed part falls on the Form 4797 loss. The example prints exactly this split.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether the carried-forward part, which the software carries as one
prior-year unallowed loss for the partnership, should be kept apart as a Form 4797 loss for next year.

**Where it lives.** `scheduleE: /formK1s/*/ptpSection1231PassiveLossAllowedAgainstIncome`,
`scheduleE: /formK1s/*/ptpSection1231PassiveLossAllowedOnForm4797`, `form4797: /formK1s/*/section1231GainForForm4797`.

### IN-75 — Form 499R-2/W-2PR: wages of a filer who is not a bona fide resident of Puerto Rico, and box 22

**The question.** A filer enters a Form 499R-2/W-2PR, the Puerto Rico withholding statement. Where do its wages go on
Form 1040 when the filer is not a bona fide resident of Puerto Rico, and does Form 8959 count its Medicare wages?

**The IRS text.** Publication 570 (2025), page 20, Not a Bona Fide Resident of Puerto Rico: a U.S. citizen or resident
alien "but not a bona fide resident of Puerto Rico during the tax year" files "A U.S. tax return reporting income from
worldwide sources. Generally, you can claim a foreign tax credit for income taxes paid to Puerto Rico on the Puerto Rico
income that is subject to Puerto Rico taxes and not exempt from U.S. taxes". Instructions for Form 8959 (2025), page 1:
"References to Form W-2 on Form 8959 and in these instructions also apply to Forms W-2AS, W-2CM, W-2GU, W-2VI, and
499R-2/W-2PR. However, for Form 499R-2/W-2PR, Medicare wages and tips are reported in box 22 and Medicare tax withheld
is reported in box 23." Form 499R-2/W-2PR instructions, boxes 7 and 8: "Include in these boxes the amount of wages and
commissions paid, net of cash contributions made to a pension or retirement system".

**What the software does.** It refuses a return with a Form 499R-2/W-2PR that shows compensation unless the filer
answers yes to the bona fide Puerto Rico residence question. It also refuses a return whose Medicare wages, counting box
22, are above the Additional Medicare Tax threshold, or where one statement's box 22 is above $200,000 (the employer may
have withheld Additional Medicare Tax that Form 8959 credits). A bona fide resident's Puerto Rico wages stay off the
return (section 933 exclusion).

**Why the call was made.** The wages are income on the U.S. return, but the statement measures them under the Puerto
Rico Code (net of pension contributions), no Form 1040 instruction names the line, and the Puerto Rico tax is a Form 1116
credit this software does not fill from the statement. A wages-only route would file a return without that credit.
Form 8959 does not add box 22 yet, so only the returns where box 22 changes the tax or the withholding credit are refused.

**Our best recommendation.** Keep the refusal until the U.S. wage figure, its Form 1040 line, the foreign tax credit
and Form 8959 lines 1 and 19 are built.

**What we would like a reviewer to check.** Which Form 1040 line takes Puerto Rico wages of a filer who is not a bona
fide resident (line 1a with Forms W-2, or line 1h), and how the box 7 figure is adjusted for the pension contributions
it excludes.

**Where it lives.** `formW2s: /knockoutForm499R2W2PrAmountsNotCarried`, `formW2s: /form499R2W2Prs/*/showsCompensation`,
`formW2s: /form499R2W2PrMedicareWagesAndTipsTotal`, `ctcOdc: /isBonaFidePuertoRicoResident`.

### IN-71 — A home also rented 15 days or more: outside the passive activity rules

**The question.** A dwelling unit the filer used as a home and rented 15 days or more has its deductions limited to
its rents (IRC 280A(c)(5)). Is its profit or loss a passive activity item on Form 8582, and what if the unit carries a
passive loss from an earlier year when it was not used as a home?

**The IRS text.** IRC 469(j)(10) (U.S. Code p. 1639): "If a passive activity involves the use of a dwelling unit to
which section 280A(c)(5) applies for any taxable year, any income, deduction, gain, or loss allocable to such use shall
not be taken into account for purposes of this section for such taxable year." 2025 Instructions for Form 8582, page 3,
among the activities that are not passive: "The rental of a dwelling unit you used as a residence if section 280A(c)(5)
applies." IRC 469(f)(1)(A) (p. 1636), for a former passive activity: "any unused deduction allocable to such activity
under subsection (b) shall be offset against the income from such activity for the taxable year".

**What the software does.** A unit used as a home (personal days above the greater of 14 or 10% of the fair rental
days) with 15 or more fair rental days is kept off Form 8582: its net after the Worksheet 5-1 limit goes to Schedule E
line 26 as nonpassive, a profit no longer absorbs other passive losses, and a loss is deducted in full. A carried
passive loss the unit's own income covers is subtracted from that income; one larger than the income is refused.

**Why the call was made.** Section 280A(c)(5) applies to every home rented 15 days or more, whether or not the limit
binds, so the test is the home test and the day count, not whether expenses exceed the rents. The carried loss arose
while the unit was a passive rental, so the former passive activity rule settles it.

**Our best recommendation.** Keep. The refused corner needs the leftover carried loss put back into Form 8582.

**What we would like a reviewer to check.** Whether a unit's carried passive loss from years before the home use is
"allocable to such use" (and so also outside section 469) rather than a former passive activity loss.

**Where it lives.** `scheduleE: /rentalProperties/*/section469j10Applies`,
`scheduleE: /rentalProperties/*/section469j10NonpassiveNet`, `scheduleE: /knockoutRentalDwellingUsedAsHomePriorLossNotAbsorbed`.

### IN-72 — A rental also used personally: the personal part of its mortgage interest and taxes on Schedule A

**The question.** The filer enters a rental's whole-year expenses and the software keeps only the rental part on
Schedule E. Where does the personal part of the mortgage interest and real estate taxes go, and when is it deductible?

**The IRS text.** Publication 527 (2025), page 25: "Only your rental expenses may be deducted on Schedule E (Form 1040).
Some of your personal expenses may be deductible on Schedule A (Form 1040) if you itemize your deductions." Page 30:
"Be sure to report only the personal portion of your real estate taxes on line 5b of Schedule A" and "Be sure to claim
only the personal portion of your deductible mortgage interest on Schedule A." IRC 163(h)(4)(A)(i) (U.S. Code p. 746): a
qualified residence is the principal residence and "1 other residence of the taxpayer which is selected by the taxpayer
for purposes of this subsection for the taxable year and which is used by the taxpayer as a residence (within the
meaning of section 280A(d)(1))".

**What the software does.** For every rental with personal use days, the personal part of the real estate taxes (the
taxes less their rental part) is added to Schedule A line 5b. For a rental the filer used as a home, the personal part
of the Schedule E line 12 mortgage interest is added to line 8a; for a rental not used as a home it is personal interest
and is not deducted. The filer leaves these amounts out of their own Schedule A entries. Two or more rented homes with
personal mortgage interest are refused, because only one can be the selected other residence.

**Why the call was made.** The software already divides the whole-year amounts, so the personal part is known exactly;
asking the filer to divide them again invites errors. A rented unit is a qualified residence only when used as a home.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether Schedule E line 16 on a dwelling unit can be read as real estate
taxes, and whether the personal part of other interest (line 13) should also reach Schedule A when it is mortgage interest
not reported on Form 1098.

**Where it lives.** `scheduleE: /rentalProperties/*/realEstateTaxesPersonalPart`,
`scheduleE: /rentalProperties/*/homeMortgageInterestPersonalPart`, `scheduleA: /realEstateTaxesIncludedInStateLocalTaxes`,
`scheduleA: /scheduleALine8aHomeMortgageInterestOn1098`, `scheduleE: /knockoutRentalHomesMortgageInterestOnMoreThanOneSecondHome`.

### IN-87 — Form 499R-2/W-2PR: U.S. Government wages of a bona fide resident of Puerto Rico

**The question.** A bona fide resident of Puerto Rico excludes Puerto Rico source income under section 933. What
happens when a Form 499R-2/W-2PR reports wages paid by the U.S. Government or one of its agencies?

**The IRS text.** IRC 933(1): a bona fide resident excludes "income derived from sources within Puerto Rico (except
amounts received for services performed as an employee of the United States or any agency thereof)". Publication 570
(2025), page 20, U.S. Government employees: "Although bona fide residents of Puerto Rico may generally exclude Puerto Rico
source income from their U.S. tax return, these wages are also subject to U.S. tax because U.S. Government wages do not
qualify for the exclusion. However, the cost-of-living allowances are excludable from U.S. gross income. A foreign tax
credit is available in order to avoid double taxation."

**What the software does.** It asks, for each Form 499R-2/W-2PR that shows compensation, whether the employer is the U.S.
Government or one of its agencies. A bona fide resident who answers yes, or leaves it unanswered, is refused.

**Why the call was made.** The statute is clear that the wages are taxed, but the statement does not give the U.S. figure:
its boxes follow the Puerto Rico Code (net of pension contributions), the cost-of-living allowances are excludable, and the
Puerto Rico tax on the wages is a Form 1116 credit this software does not fill from the statement. Carrying box 7 to line
1a would file a return with the wrong wage figure and no credit.

**Our best recommendation.** Keep the refusal until the U.S. wage figure, its Form 1040 line and the foreign tax credit are
built.

**What we would like a reviewer to check.** Whether a federal agency in Puerto Rico reports these wages on Form
499R-2/W-2PR or on Form W-2, and which figure (box 7 or box 20) is the U.S. wage measure.

**Where it lives.** `formW2s: /knockoutForm499R2W2PrAmountsNotCarried`,
`formW2s: /form499R2W2Prs/*/writableEmployerIsUsGovernment`, `formW2s: /form499R2W2Prs/*/mayReportUsGovernmentCompensation`.

### IN-88 — Schedule 3 line 11: Form 499R-2/W-2PR box 21 in the excess social security credit

**The question.** A filer has a Form 499R-2/W-2PR from a Puerto Rico employer and a Form W-2 (or a second Form
499R-2/W-2PR) from another employer, and total social security tax withheld above the annual maximum. Does the Puerto Rico
withholding count on Schedule 3 line 11?

**The IRS text.** Instructions for Form 1040 (2025), page 117, Schedule 3 Line 11: "If you, or your spouse if filing a
joint return, had more than one employer for 2025 and total wages of more than $176,100, too much social security or tier
1 railroad retirement (RRTA) tax may have been withheld. You can take a credit on this line for the amount withheld in
excess of $10,918.20. But if any one employer withheld more than $10,918.20, you can't claim the excess on your return."
Instructions for Schedule 8812 (2025), page 9: "Enter the social security tax withheld (Form(s) W-2, box 4, and Puerto
Rico Form(s) 499R-2/W-2PR, box 21)". IRC 3121(e)(2): "The term "United States" when used in a geographical sense includes
the Commonwealth of Puerto Rico".

**What the software does.** Box 21 joins each filer's withholding for line 11 (capped at $10,918.20 per statement),
boxes 20 and 24 join the wages for the $176,100 test (capped at the wage base per statement), and each statement counts as
an employer. A statement whose employer also issued the filer another Form W-2 or Form 499R-2/W-2PR, with box 21 withholding
and total withholding above the maximum, is refused rather than grouped.

**Why the call was made.** Puerto Rico employment is covered by the same social security tax, the line 11 instruction
counts every employer, and the IRS's own Schedule 8812 worksheet treats box 21 as social security tax withheld beside Form
W-2 box 4. Leaving it out lost the credit for a filer with a Puerto Rico employer and a second employer.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether box 24 social security tips belong in the wage test beside box 20, as
Form W-2 box 7 does beside box 3.

**Where it lives.** `schedule3: /excessSocialSecurityTaxWithheld`, `schedule3: /primaryFilerTotalOasdiWithholdingForExcess`,
`schedule3: /primaryFilerExceedsMaxOasdiOrTier1Wages`, `schedule3: /form499R2W2Prs/*/socialSecurityTaxWithheldForExcess`,
`formW2s: /form499R2W2Prs/*/sharesEmployerWithAnotherStatementOfItsFiler`.

### IN-91 — Form 8997 Part III: an attested inclusion amount rounded to whole dollars

**The question.** The includible gain on a qualified opportunity fund disposition is figured to the cent (the 10 percent
and 5 percent basis increases leave cents). The filer also enters the amount on the Form 8949 code-Y row. When the two
differ only by the rounding of cents to whole dollars, do they agree?

**The IRS text.** IRC 1400Z-2(b)(2)(A): "The amount of gain included in gross income under subsection (a)(1)(A) shall be
the excess of" "the lesser of the amount of gain excluded under paragraph (1) or the fair market value of the investment"
over the basis. 2025 Instructions for Form 1040, page 23, Rounding Off to Whole Dollars: "You can round off cents to
whole dollars on your return and schedules. If you do round to whole dollars, you must round all amounts. To round, drop
amounts under 50 cents and increase amounts from 50 to 99 cents to the next dollar."

**What the software does.** The attested amount and the computed amount disagree, and the return is refused, only when
they are $1 or more apart.

**Why.** A filer who rounds reaches the whole-dollar figure either by rounding the included gain (11,110.50 becomes
11,111) or by rounding the proceeds and basis on the code-Y row separately (12,345 less 1,235 is 11,110); both are
within $1 of the exact amount. Refusing them would refuse a lawfully rounded return.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Nothing specific.

**Where it lives.** `form8997: /qofInclusionDispositions/*/qofInclusionAttestedGainDisagrees`,
`form8997: /knockoutQofInclusionAttestedGainDisagreesWithFormula`.

### IN-92 — Form 8997 Part II: the statutory limits on a QOF deferral are attested, not computed

**The question.** The deferral is allowed only for gain from a sale to an unrelated person, up to the amount invested
within 180 days, and not for a sale whose earlier election is still in effect. Form 8997 prints none of the amount
invested, the sale date or the relationship. Should the software compute the limits, attest them, or refuse?

**The IRS text.** IRC 1400Z-2(a)(1): "In the case of gain from the sale to, or exchange with, an unrelated person of any
property held by the taxpayer, at the election of the taxpayer-" "gross income for the taxable year shall not include so
much of such gain as does not exceed the aggregate amount invested by the taxpayer in a qualified opportunity fund during
the 180-day period beginning on the date of such sale or exchange,". IRC 1400Z-2(a)(2)(A): no election "with respect to
a sale or exchange if an election previously made with respect to such sale or exchange is in effect". Form 8997
(Rev. December 2025), General Instructions: the investment "must have occurred within the 180-day period".

**What the software does.** It asks one question confirming all four limits whenever a deferral is claimed, and refuses
the return until the answer is Yes.

**Why.** The limits rest on the filer's own records; the 180-day period has later start dates under the regulations for
gain passed through from a partnership, S corporation, estate or trust, for section 1231 gain and for installment sales,
and those regulations are not part of this release's sources. A computed amount-invested cap alone would check one of the
four limits. An explicit attestation with a refusal is the posture this release takes for other filer-held facts (the
Form 8881 and Form 8941 deduction reductions).

**Our best recommendation.** Keep for 2025; compute the amount-invested cap when a per-investment amount is collected.

**What we would like a reviewer to check.** Whether an attestation is enough, or the amount invested should be collected.

**Where it lives.** `form8997: /writableQofDeferralWithinStatutoryLimits`, `form8997: /knockoutQofDeferralLimitsNotAttested`.

### IN-97 — Schedule 3 line 11: territorial Forms W-2 (W-2AS, W-2GU, W-2VI) box 4 in the excess social security credit

**The question.** A filer has a Form W-2AS, W-2GU or W-2VI from a territorial employer and a Form W-2 (or a second
territorial statement) from another employer, and total social security tax withheld above the annual maximum. Does
the territorial withholding count on Schedule 3 line 11, the same as Puerto Rico's does under IN-88?

**The IRS text.** IRC 3121(e)(2): "The term 'United States' when used in a geographical sense includes the
Commonwealth of Puerto Rico, the Virgin Islands, Guam, and American Samoa" — the SAME sentence IN-88 read for Puerto
Rico continues, in the very next clause, to name the other three territories on identical footing. Instructions for
Form 1040 (2025), page 117, Schedule 3 Line 11: "If you, or your spouse if filing a joint return, had more than one
employer for 2025 and total wages of more than $176,100, too much social security or tier 1 railroad retirement
(RRTA) tax may have been withheld. You can take a credit on this line for the amount withheld in excess of
$10,918.20. But if any one employer withheld more than $10,918.20, you can't claim the excess on your return."

**What the software does.** Box 4 joins each filer's withholding for line 11 (capped at $10,918.20 per statement),
box 3 joins the wages for the $176,100 test (capped at the wage base per statement), and each territorial statement
counts as an employer. A Form W-2AS or W-2GU statement whose employer also issued the filer another Form W-2 or a
second statement in the same collection, with box 4 withholding and the filer's collection total above the maximum,
is refused rather than grouped (case (5) of `formW2s:/knockoutTerritorialFormW2`). Form W-2VI gets the same
computation for completeness, but it is moot: every Form W-2VI already refuses pending Form 8689 (S1527).

**Why the call was made.** The statute IN-88 already read for Puerto Rico names Guam, the Virgin Islands and
American Samoa in the same breath; there is no textual basis to treat one territory's social security tax as
countable and the other three as not. `formW2s:/knockoutTerritorialFormW2`'s pre-existing OASDI wage-base leg looked
like it already refused every case this could matter for, but it measured Form W-2 box 3 alone against the wage
base — not the Schedule 3 line 11 wage measure, which also counts box-14 Tier 1 RRTA compensation for a railroad
employee whose Form W-2 box 3 is blank by printed rule. That gap let a railroad-employee-plus-territorial-statement
return file computed, with the territorial withholding silently uncounted (S2791).

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether an American Samoa employer's box 4 should instead route through
the Form 4563 exclusion mechanism (IRC 931) rather than a straight social security credit; whether cross-collection
employer sharing (a territorial employer that also issues a domestic Form W-2 or a Form 499R-2/W-2PR to the same
filer) is a real population worth building the comparison for, left unchecked here as unsourced.

**Where it lives.** `schedule3: /excessSocialSecurityTaxWithheld`, `schedule3: /{primary,secondary}FilerTotalOasdiWithholdingForExcess`,
`schedule3: /{primary,secondary}FilerExceedsMaxOasdiOrTier1Wages`, `schedule3: /formW2Ass/*/socialSecurityTaxWithheldForExcess`
(and its W-2GU/W-2VI twins), `formW2s: /formW2Ass/*/sharesEmployerWithAnotherStatementOfItsFiler` (and its W-2GU twin),
`formW2s: /knockoutTerritorialFormW2`.

### IN-180 — Schedule C line 30, simplified method: counting the months of a year in which business use of the home began

**The question.** A filer who begins using part of the home for business during the year, and uses the
simplified method, averages the allowable square feet over the 12 months. Which date starts the count, and
how is the 15-day rule applied to the first month (and to the last month when use also stops)?

**The statute and instructions.** Publication 587 (2025), page 11, "Part-year use or area changes (for
simplified method only)": "If your qualified business use was for a portion of the year (for example, a
seasonal business, a business that begins during the year, or you moved during the year) or you changed the
square footage of your qualified business use, your deduction is limited to the average monthly allowable
square footage." And: "Additionally, if your qualified business use was less than 15 days in a month, you
must use -0- for that month." Page 12, Example 1: "On July 20, Jay began using 420 square feet at the home for
a qualified business use. ... The average monthly allowable square footage is 125 square feet, which is
figured using 300 square feet for each month, August through December, divided by the number of months in
the year".

**What the software does.** The count runs from the day qualified business use of the home began in 2025 to
the day it stopped (December 31 if it did not stop). A month counts when at least 15 of its days fall in that
period. The start day is the answer to "On what date did you first use this home for this business?" when it
is in 2025 (January 1 when it is earlier). When that question is unanswered and the business itself began in
2025, the date the business began is used, because home use for a business cannot start before the business
does; when neither date is known for a business that began in 2025, the deduction is left undecided rather
than given for the full year.

**Why we chose it.** The publication's rule is about qualified business use of the home, and its only worked
example starts the count on the day that use began (Example 1). The business start date is a floor, not the
answer: a business can begin before it uses the home, so using that date alone could count months with no
home use. It is used only when the filer has not given the home date.

**Our best recommendation.** Keep. Confidence high for the rule, medium for the business-date floor.

**What we would like a reviewer to check.** Whether the business start date is an acceptable floor when the
home date is unanswered, or whether the home date should simply be required. An area change during the year
that is not a full start or stop is not averaged (the answered square feet apply to every counted month).

**Where it lives.** `scheduleC: /scheduleCs/*/simplifiedMethodQualifiedUseStartDate`,
`scheduleC: /scheduleCs/*/simplifiedMethodQualifiedUseEndDate`,
`scheduleC: /scheduleCs/*/simplifiedMethodPartYearMonthsQualifying`.

#### IN-180 amendment — no floor when the home first-use date is unanswered (owner, 2026-10-05)

**Decision.** The month count runs from the home's qualified first-use date. A month counts only with at least 15 days of use (Rev. Proc. 2013-13 §4.08(4); Pub. 587 (2025)).
- **Unanswered date.** When the home first-use date is unanswered, the return holds until it is answered. The business start date is no longer used as a floor in that case.
- **The clamp stays.** An answered home date earlier than the business start still uses the business start.

**Example.** The business began March 1 and home use began July 18. Left unanswered, the old floor counted 10 months (a 250 square foot average, $1,250); the actual answer gives 5 months (125 square feet, $625).

**Why.** The floor could only over-deduct. GEN-01 says the software does not fill a reached box with a guess, and the entry itself invited this check. The owner decided on 2026-10-05.

### IN-181 — Schedule C line 30, simplified method: line 3c to two decimal places

**The question.** The Simplified Method Worksheet multiplies the $5 rate by the daycare decimal on line 3c
"and enter the result to two decimal places" before line 4 multiplies by the square footage. Is the rate
rounded before line 4, and how?

**The statute and instructions.** Instructions for Schedule C (2025), page 11, Simplified Method Worksheet,
line 3c: "Multiply line 3a by line 3b and enter the result to two decimal places"; line 4: "Multiply line 2
by line 3c".

**What the software does.** It rounds line 3c to the cent before line 4, then rounds line 5 to whole dollars.
For a daycare decimal of 0.3425 and 300 square feet, line 3c is $1.71 and line 4 is $513.00 (the unrounded
rate would give $513.75, which rounds to $514). The cent rounding is ordinary rounding; the one case the
worksheet does not address, a product ending in exactly half a cent, rounds to the even cent.

**Why we chose it.** The worksheet prints the order and the precision. Rounding only the final amount
overstates or understates by up to $1.50 on a daycare return.

**Our best recommendation.** Keep. Confidence high.

**What we would like a reviewer to check.** Whether an exact half cent on line 3c should round up.

**Where it lives.** `scheduleC: /scheduleCs/*/simplifiedMethodLine3cRate`,
`scheduleC: /scheduleCs/*/homeOfficeDeductionSimplified`.

#### IN-181 amendment — line 5 keeps cents; the tie rule is confirmed (owner, 2026-10-05)

**Decision.**
- **Line 3c tie confirmed.** An exact half cent on line 3c rounds to the even cent, as above. The Form 1040 instructions' "$2.50 becomes $3" rule governs rounding cents to whole dollars and does not reach a tie at the third decimal. The engine's cents arithmetic is half-to-even.
- **Line 5 amended.** It is no longer rounded to whole dollars: it keeps cents, consistent with IN-285 (every Schedule C and Form 8829 line keeps cents). The average area is the exact quotient, "Divide line 6m by 12" (Pub. 587 (2025)), and line 4 is figured to the cent.

**Example.** 250 square feet used from August 10 gives an average of 1,250 ÷ 12 = 104.1667 square feet, so line 4 = 520.83. The superseded reading gave 521.00.

**Why.** IN-285 is the later rule for the whole schedule. The tie question was researched and the existing rule kept. The owner decided on 2026-10-05.

### IN-182 — Form 8829 lines 10-17: home mortgage interest and real estate taxes by the deduction the filer takes

**The question.** On Form 8829, the business part of the home's mortgage interest and real estate taxes can be
deducted outside the gross income limit (lines 10 and 11, line 14) or as operating expenses under it (lines 16
and 17). Which applies, and what happens on Schedule A?

**The statute and instructions.** Instructions for Form 8829 (2025), page 3, "Lines 9, 10, and 11": "If you
claim the standard deduction, you will not include any mortgage interest or real estate taxes on lines 10 and
11; instead, you will claim the entire business use of the home portion of those expenses using lines 16 and
17." Page 4, "Line 16": "If you are claiming the standard deduction, enter all the home mortgage interest paid
for loans used to buy, build, or substantially improve the home in which you conducted business in column (b)
of line 16." "Line 17": "If you are claiming the standard deduction, enter all the real estate taxes paid on
the home in which you conducted business in column (b) of line 17." For an itemizer, page 3, "Mortgage
interest reported on Schedule A" includes on Schedule A only the interest not attributable to the business
home and the personal portion of line 10, and page 4, "Real estate taxes reported on Schedule A": "do not
include the business portion of your state and local real estate taxes (including line 6 of the Line 11
Worksheet) on line 5b of Schedule A."

**What the software does.** A filer who claims the standard deduction has nothing on line 14; the business
part of the home's mortgage interest and real estate taxes goes on lines 16 and 17, is allowed up to the
income limit, and any excess carries to next year. A filer who itemizes puts the business part on lines 10 and 11
(with any excess on lines 16 and 17) and the personal part on Schedule A; see IN-220.

**Why we chose it.** The instructions are explicit for both populations. Refusing the itemizer rather than
computing lines 10 and 11 avoids deducting the same dollars on Form 8829 and Schedule A.

**Our best recommendation.** Keep. The itemizer split is IN-220. Confidence high.

**What we would like a reviewer to check.** Whether the direct (column (a)) real estate taxes of a
standard-deduction filer belong on line 17 column (a) with the daycare reduction, as built.

**Where it lives.** `scheduleC: /scheduleCs/*/form8829MortgageInterestAndTaxesDeduction`,
`scheduleC: /scheduleCs/*/form8829StandardDeductionMortgageInterestAndTaxes`,
`form8829: /knockoutForm8829ItemizerMortgageInterestAndTaxesNotSplit`.

### IN-220 — Form 8829 lines 10, 11, 16 and 17 and Schedule A lines 5b and 8a: an itemizer's home mortgage interest and real estate taxes

**The question.** A filer who itemizes and uses part of the home for a business splits the home's mortgage
interest and real estate taxes: the business part on Form 8829, the personal part on Schedule A. How is the
split figured, where does the filer enter the amounts, and how does the Line 11 Worksheet's state and local tax
limit, whose own limit depends on adjusted gross income, fit a return that cannot iterate?

**The statute and instructions.** Instructions for Form 8829 (2025), page 3, "Mortgage interest reported on line
10": "Step 1. Treat all the mortgage interest you paid as a personal expense and figure the amount that would be
deductible as an itemized deduction on Schedule A." "Step 2. Include in column (b) of line 10 the amount of
deductible mortgage interest figured in Step 1 that is attributable to the home in which you conducted the
business." Page 4, "Line 16": "include the excess attributable to the loans used to buy, build, or substantially
improve the home in which you conducted business in column (b) of line 16." Page 4, Line 11 Worksheet: line 6
"Multiply line 2 by the percentage on Form 8829, line 7"; line 9 "Subtract line 7a from line 8"; line 10 "Enter
the smaller of line 6 or line 9 here and in column (a) of Form 8829, line 11"; line 11 "Subtract line 10 from
line 6" (excess real estate taxes on line 17). Page 4, "Real estate taxes reported on Schedule A": "do not
include the business portion of your state and local real estate taxes (including line 6 of the Line 11
Worksheet) on line 5b of Schedule A." Publication 587 (2025), page 18: "only include the personal part of your
deductible mortgage interest on Schedule A (Form 1040), line 8a or 8b"; page 19: "The personal portion of your
real estate taxes will generally be the amount of real estate taxes you paid for the home reduced by the
business or rental portions deducted or carried over as a business or rental expense on Schedule C, E, or F,
or any form other than Schedule A."

**What the software does.** The filer enters the home's mortgage interest and real estate taxes once, on the
Form 8829 questions, with the real estate tax part named, and leaves them out of the Schedule A questions. The
business percentage of the taxes (Line 11 Worksheet line 6) goes to Form 8829; the rest is added to Schedule A
line 5b. The business percentage of the interest goes to Form 8829; the rest is added to Schedule A line 8a, where
the home mortgage interest limits apply to it. The part of the business interest on line 10 is the business
interest times the same debt-limit fraction Schedule A applies (Publication 936, Table 1, which applies the
limit in proportion to all the qualified interest); the rest is line 16. The part of line 6 on line 11 is the
smaller of line 6 or the state and local tax limit less the other state and local taxes (line 7a, which equals
Schedule A line 5d); the rest is line 17. The two parts of each amount add to the amount paid. The deduction
(Schedule C line 30) counts all of line 6 on line 11 except where line 7a is at least $40,000 ($20,000 if
married filing separately), where none of it is: when line 14 is no more than line 8, moving an amount from line
11 to line 17 leaves lines 28, 34 and 36 unchanged, so the deduction is exact whatever the limit, and the printed
lines 14, 15, 26 and 27 show the worksheet's split. A return where the split would change the deduction
(line 14 above line 8) and depends on the limit (line 5 above $10,000, line 7a below $40,000, and not all of line
6 within a $40,000 limit) is the worksheet's iteration, and is refused. So are a direct (column (a)) amount, two
businesses with these amounts, and a Form 8396 credit beside the home mortgage interest.

**Why we chose it.** Entering the home's amounts once and adding the personal part to Schedule A makes the
identity the publications state (personal part plus business part equals the amount paid) true by construction
and cannot deduct the business part twice; the same shape already carries a rental home's personal taxes and
interest to lines 5b and 8a. The debt-limit fraction is what Schedule A applies to every qualified loan, so
Step 1's deductible amount for the business home is the home's interest times that fraction. The invariance of
lines 28 to 36 under a move between lines 11 and 17 is arithmetic on the printed lines, which is why the
deduction needs the adjusted-gross-income-dependent limit only on the refused population.

**Our best recommendation.** Keep. Confidence high for the split and the Schedule A side; medium for applying
the debt-limit fraction in proportion to the business home's interest when the filer has more than one home.

**What we would like a reviewer to check.** Whether a filer with two homes and debt over the limit should
attribute the Step 1 limit to the business home in proportion (as built) or by tracing the loans.

**Where it lives.** `scheduleC: /scheduleCs/*/writableForm8829IndirectRealEstateTaxes`,
`scheduleC: /scheduleCs/*/form8829Line10DeductibleMortgageInterestBusinessPart`,
`scheduleC: /scheduleCs/*/form8829Line11RealEstateTaxesForTheIncomeLimit`,
`form8829: /scheduleCs/*/form8829Line11WorksheetRealEstateTaxesOnLine11`,
`scheduleC: /form8829PersonalHomeRealEstateTaxesTotal`, `scheduleC: /form8829PersonalHomeMortgageInterestTotal`,
`form8829: /knockoutForm8829ItemizerMortgageInterestAndTaxesNotSplit`.

### IN-190 — Schedule C line 9: business parking fees and tolls under the actual-expense method

**The question.** The Schedule C instructions add parking fees and tolls to the standard mileage amount on
line 9. A filer who deducts actual car expenses takes only the business-use share of operating costs. Are
business parking fees and tolls under that method also a share, or deducted in full?

**The statute and instructions.** Instructions for Schedule C (2025), page 6, Line 9: "Multiply the number of
business miles driven by 0.70" and "Add to this amount your parking fees and tolls; and". Publication 463
(2025), chapter 4: "Parking fees and tolls. In addition to using the standard mileage rate, you can deduct any
business-related parking fees and tolls. (Parking fees you pay to park your car at your place of work are
nondeductible commuting expenses.)"; its list of actual car expenses includes "Tolls" and "Parking fees".

**What the software does.** It asks for the business parking fees and tolls once, and adds them to line 9 in
full under either method. The actual-expense share (business miles over total miles) applies only to the
operating costs, which the filer enters without parking and tolls.

**Why we chose it.** The business-use share exists to separate personal from business use of the car.
Parking and tolls asked for here are business-related by the question itself (a business trip), so the whole
amount is business. Prorating them would under-deduct.

**Our best recommendation.** Keep. Confidence high.

**What we would like a reviewer to check.** Whether a filer on actual expenses should instead include
business parking and tolls in the operating costs (and so prorate them).

**Where it lives.** `scheduleC: /scheduleCs/*/writableParkingFeesAndTolls`,
`scheduleC: /scheduleCs/*/carTruckExpenses`.

### IN-183 — Schedule C line 30: the gross income limitation of the business use of the home (worksheet line 1, Form 8829 line 8)

**The question.** The home-office deduction beyond mortgage interest and taxes is limited by the gross income
from the business use of the home. How is that limit figured, and what does the software assume when the
filer does not say where the income was earned or does not report a gain or loss?

**The statute and instructions.** Instructions for Schedule C (2025), page 11, Simplified Method Worksheet line
1: "If all gross income from your trade or business is from this qualified business use of your home, figure
your gross income limitation as follows", A "Enter the amount from Schedule C, line 29", B "Enter any gain
derived from the business use of your home and shown on Form 8949 (and included on Schedule D) or Form 4797",
D "Enter the total amount of any losses (as a positive number) shown on Form 8949 (and included on Schedule D)
or Form 4797 that are allocable to the business, but not allocable to the business use of the home"; and "If
some of the income is from a place of business other than your home, you must first determine the part of your
gross income (Schedule C, line 7, and gains from Form 8949, Schedule D and Form 4797) from the business use of
your home." Instructions for Form 8829 (2025), page 2, Line 8, says the same for line 8.

**What the software does.** It asks whether all of the business's gross income is from the business use of
the home, and does not complete line 30 until the filer answers. Yes: line 29 plus the home-use gain minus the
unrelated losses. No: the filer's home-use share of gross income minus Schedule C line 28 and the unrelated
losses. A blank gain or loss is $0.

**Why we chose it.** The two routes are printed; the choice between them is a fact about the business that
nothing else on the return shows, so it is asked, and an unanswered question is not read as Yes (Yes gives
the larger limit). The gain and loss lines are the worksheet's own optional entries ("Enter any"), so a blank
is zero, as for the other optional printed entries.

**Our best recommendation.** Keep. Confidence high for the arithmetic; medium for treating a blank loss as $0,
which favours the filer when a loss exists and was not reported.

**What we would like a reviewer to check.** Whether the unrelated-loss question should be required rather than
blank-is-zero.

**Where it lives.** `scheduleC: /scheduleCs/*/homeOfficeGrossIncomeLimitation`,
`scheduleC: /scheduleCs/*/writableHomeOfficeAllGrossIncomeFromHomeUse`, `form8829: /scheduleCs/*/form8829Line8BusinessIncomeLimit`.

### IN-184 — Form 8829 line 41: a home first used for business before 1987 (Pub. 534 ACRS)

**The question.** For a home first used for business from 1981 through 1986, Form 8829 line 41 sends the filer
to Publication 534. What percentage applies in 2025, and when can the software compute line 42 instead of
asking for it?

**The statute and instructions.** Instructions for Form 8829 (2025), page 5, Line 41: a home first used for
business "before 1987," takes "the percentage given in Pub. 534, Depreciating Property Placed in Service Before
1987." Publication 534 (Rev. November 2016), page 19, Tables 14 and 15: the 45-year alternate ACRS rows
"12-45th" and "11-45th" read 2.2 in every month column; the regular and 35-year tables end before recovery
year 40.

**What the software does.** For such a home still in business use at year end, with the additions attested
absent or all listed, it computes line 42 as line 40 times 2.2 percent when the 45-year alternate method was
elected, and $0 otherwise, and prints that percentage on line 41. It no longer needs the filer's own line 42.
A home whose business use stopped during the year still uses the filer's figure, because Pub. 534's
full-month disposition convention for 15-year and early 18-year real property is not reconciled with the
mid-month convention used elsewhere.

**Why we chose it.** The percentage is printed; the only fact the return lacks is the historical election,
which is asked. A full year of use involves no disposition convention.

**Our best recommendation.** Keep. Confidence medium: the 0 percent for the non-45-year population is read
from where each table ends, not from a printed statement.

**What we would like a reviewer to check.** The exhaustion reading for the regular and 35-year tables.

**Where it lives.** `scheduleC: /scheduleCs/*/form8829Pub534IsModeled`,
`scheduleC: /scheduleCs/*/form8829Pub534DepreciationPercentage`, `scheduleC: /scheduleCs/*/form8829HomeDepreciation`.

## Adjustments and deductions

### IN-160 — Claim of right (IRC 1341) on a Schedule J income-averaging return: both taxes are figured with Schedule J

**The question.** A farmer or fisher who elects income averaging repays more than $3,000 taxed in an earlier year,
and the repayment changes the deduction on Form 1040 line 12e. The section 1341 comparison needs the tax for the year
with the deduction and without it. Is each of those the income-averaged tax, and what if the farm income elected is
more than the taxable income would be with the deduction?

**The statute and the form.** IRC 1341(a) (U.S. Code p. 2429): the tax is "the lesser of the following": "(4) the tax
for the taxable year computed with such deduction; or" "(A) the tax for the taxable year computed without such
deduction, minus" the earlier-year decrease. IRC 1301(a) (U.S. Code p. 2423): "At the election of an individual
engaged in a farming business or fishing business, the tax imposed by section 1 for such taxable year shall be equal
to the sum of-" "(1) a tax computed under such section on taxable income reduced by elected farm income, plus" "(2)
the increase in tax imposed by section 1 which would result if taxable income for each of the 3 prior taxable years
were increased by an amount equal to one-third of the elected farm income." Schedule J (2025), page 1, line 2a:
"Enter your elected farm income. See instructions. Do not enter more than the amount on line 1".

**What the software does.** The election stays in force on both sides of the comparison, because the filer made it
and section 1301 then defines "the tax imposed by section 1" for the year. Each side is the Schedule J tax figured on
that side's taxable income: the Tax Table or rate-schedule tax on the taxable income with (or without) the deduction
less the elected farm income (Schedule J lines 3 and 4 on that side), plus the base-year increase (lines 8, 12 and 16
less lines 19 to 21), which depends only on the elected farm income and the earlier years and so is the same on both
sides. The comparison then takes the lesser as IN-03 describes. The computed population keeps the other limits of
IN-03 (no qualified dividends or net capital gain, so Schedule J lines 2b and 2c are $0 and line 4 is the ordinary
tax; no Form 2555; no alternative minimum tax or nonrefundable credit on the side chosen). A return whose elected farm
income is more than its taxable income with the deduction is refused: on that side line 2a would exceed line 1, and
how much farm income to elect there is the filer's choice, not one the software may make for them.

**Why.** The statute leaves no room for a comparison that drops the election on one side: section 1301 is the tax on
an electing return, so "the tax computed with such deduction" is the section 1301 tax. The base-year term does not
move with the current year's taxable income, so only line 4 differs between the sides.

**Our best recommendation.** Keep. The over-election refusal is narrow (a filer electing nearly all of a small taxable
income) and could be lifted by asking the filer for the amount they would elect with the deduction.

**What we would like a reviewer to check.** Whether practitioners keep the income-averaging election on both sides of
the section 1341 comparison, as the statute reads.

**Where it lives.** `taxCalculations: /ordinaryRateIncomeWithClaimOfRightDeduction`,
`taxCalculations: /ordinaryRateIncomeWithoutClaimOfRightDeduction`, `taxCalculations: /taxWithClaimOfRightDeduction`,
`taxCalculations: /taxWithoutClaimOfRightDeduction`, `taxCalculations: /claimOfRightComparisonIsExact`,
`scheduleJ: /scheduleJBaseYearsTaxIncrease`.

### AD-05 — Self-employed health insurance and the premium tax credit: which calculation method

**The question.** A self-employed filer who buys Marketplace coverage has a circular computation: the
self-employed health insurance deduction lowers income, which raises the premium tax credit, which lowers the
premium that can be deducted. Publication 974 offers two ways to solve it.

**The IRS text.** Publication 974 (2025), *Premium Tax Credit*, page 47: "you may choose to use either the
Simplified Calculation Method or the Iterative Calculation Method to compute your self-employed health
insurance deduction and PTC. The Simplified Calculation Method is shorter, but in some cases will not produce a
result as favorable as the Iterative Calculation Method."

**What the software does.** Both methods. The simplified calculation method is computed, and so is the
Iterative Calculation Method (run for up to ten rounds, each to the cent, stopping when both the deduction
and the credit change by less than $1.00); the filer gets the more favorable of the two. If the iterative
method does not settle, the simplified result is used, as the publication directs.

**Why the owner chose it.** The first call was the simplified method alone: IRS-approved and fully
deterministic. After review the owner chose to build the iterative method too and use the better result.

**Our best recommendation — partly differs.** Keep the simplified method for this release; it is lawful. But
the publication says outright that it can cost the filer money. We would either add the iterative method later
and use whichever result is better, or tell affected filers that another method may give a lower tax.

**The owner's decision after review (2026-09-25).** The owner decided to follow our recommendation. It is
built: "What the software does" above describes the software as it is now.

**What we would like a reviewer to check.** How large the difference between the two methods usually is in
practice.

**Where it lives.** `form7206:/pub974SimplifiedMethodApplies`, `form7206:/pub974IterativeMethodApplies`,
`form7206:/pub974CoordinatedSelfEmployedHealthInsuranceDeduction`, the `form7206:/pub974IterativeRound*` facts
and the monthly `form7206:/pub974Section162lMonth*` facts.

### AD-01 — HSA last-month rule: does deemed coverage decide the married-couple rules on line 6?

**The question.** Under the last-month rule, a person eligible for an HSA in December is treated as eligible for
the whole year, with December's coverage. For spouses with separate HSAs, Form 8889 line 6 has special rules
when either "had family coverage [...] at any time". A filer who had family coverage in some real months but
self-only coverage in December: are they treated as having had family coverage at any time?

**The competing texts.**
- IRC 223(b)(8)(A)(ii) (U.S. Code p. 970) treats the individual "as having been enrolled, during each of the
  months such individual is treated as an eligible individual solely by reason of clause (i), in the same high
  deductible health plan in which the individual was [...]" enrolled in the last month. The deeming reaches
  only the months the person was *not* actually eligible.
- Instructions for Form 8889 (2025), page 4, Line 3, rule 2: "If the last-month rule [...] applies, you are
  considered an eligible individual for the entire year. You are treated as having the same HDHP coverage for
  the entire year as you had on the first day of the last month of your tax year." Page 4, Line 1: "If you were
  covered, or considered covered, by a self-only HDHP and a family HDHP at different times during the year,
  check the box for the plan that was in effect for a longer period."
- Instructions for Form 8889 (2025), page 7, Line 6: "Spouses who have separate HSAs and had family coverage
  under an HDHP at any time during 2025, use the following rules to figure the amount on line 6."

**What the software does.** It follows the form. Where the last-month rule supplied the limitation, the filer
is treated as having December's coverage all year, so a self-only December means no family coverage "at any
time", and line 6 is simply line 5.

**Why the owner chose it.** The form computes on "considered covered" coverage in its own words; the owner
ruled for the form. The difference was priced at about $50 per affected couple.

**Our best recommendation.** Keep it, with low confidence. The statute's "solely by reason of clause (i)" is a
real limit on the deeming, and a court might read the statute over the form. But the form is the IRS's
operational position, the amount is small, and a filer following the form is following published IRS
instructions.

**What we would like a reviewer to check.** Which reading you apply for a couple in this situation.

**Where it lives.** `hsa:/filers/*/hsaLine6HadFamilyCoverageAnyMonth`, `hsa:/filers/*/hsaLine3LastMonthRuleApplies`.

### AD-02 — HSA: employer contributions for someone who can be claimed as a dependent

**The question.** A person who can be claimed as someone else's dependent cannot deduct HSA contributions. If
their employer contributes to their HSA (Form W-2 box 12 code W), is the contribution excludable, or an excess
contribution subject to the 6% tax?

**The competing texts.**
- IRC 223(b)(6) (U.S. Code p. 970): "No deduction shall be allowed under this section to any individual with
  respect to whom a deduction under section 151 is allowable to another taxpayer". It denies the *deduction*.
- IRC 106(d)(1) (U.S. Code p. 544): "In the case of an employee who is an eligible individual (as defined in
  section 223(c)(1)), amounts contributed by such employee’s employer to any health savings account [...] shall
  be treated as employer-provided coverage for medical expenses under an accident or health plan to the extent
  such amounts do not exceed the limitation under section 223(b) (determined without regard to this
  subsection)". The definition of "eligible individual" in IRC 223(c)(1) (p. 970) turns on high deductible
  health plan coverage and other coverage; it does not mention dependents.
- Instructions for Form 8889 (2025), page 2: "However, you cannot be enrolled in Medicare or be another
  person's dependent."

**What the software does.** It follows the instructions: a claimable dependent is not an eligible individual,
the line 3 limit is $0, and the employer contribution is an excess contribution on Form 5329.

**Why the owner chose it.** The owner ruled for the printed Form 8889 / Form 5329 reading.

**Our best recommendation.** Keep it, with medium confidence. Read on its own words the statute only denies
the deduction and would let the employer contribution be excluded. But the IRS instructions state the opposite
plainly, and a return that follows them is defensible. If a reviewer knows of guidance that reconciles the
two, it would settle this.

**What we would like a reviewer to check.** How you treat a dependent's employer HSA contribution.

**Where it lives.** `hsa:/filers/*/hasHsaContributionsAndCanBeClaimedAsDependent`.

### AD-04 — HSA: a prior-year excess with no 2025 contributions

**The question.** A filer carried an excess HSA contribution from 2024 but made no 2025 contributions. The
unused 2025 limit absorbs the excess (Form 5329 line 43) — but that limit needs the filer's 2025 coverage,
which the software asks only of filers who contributed.

**The IRS text.** Form 5329 (2025), line 43: "If the contributions to your HSAs for 2025 are less than the
maximum allowable contribution, see instructions. Otherwise, enter -0-".

**What the software does.** Today this filer is refused. The owner ruled to ask the coverage questions whenever
there is a carried-in excess, and to add the missing case to the deduction (scheduled for a later update).

**Why the owner chose it.** Without the coverage answers the absorbed amount cannot be figured, and the filer
loses a deduction the form allows.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `hsa:/filers/*/hsaHdhpCoverageStatusDerived`, `hsa:/filersWithHsaContributions`,
`hsa:/filers/*/hsaTotalDeductibleAmount`.

### AD-03 — HSA: exceptions to the additional 20% tax

**The question.** Non-medical HSA distributions carry an additional 20% tax unless the account holder died,
became disabled or turned 65. How does the software know?

**The IRS text.** Form 8889 (2025), line 17a: "If any of the distributions included on line 16 meet any of the
Exceptions to the Additional 20% Tax (see instructions), check here", and line 17b: "Enter 20% (0.20) of the
distributions included on line 16 that are subject to the additional 20% tax."

**What the software does.** The filer states the amount and the reason (age 65, disability, death, or none).
Age 65 is also derived from the date of birth; disability and death are the filer's statements. Only a missing
reason or amount holds the return.

**Why the owner chose it.** Disability and death cannot be derived from anything else on the return.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `hsa:/filers/*/writableHsaCollectionExceptionReason`, `hsa:/hsaCollectionExceptionReasonOptions`,
`hsa:/filers/*/hsaAdditionalTaxExceptionAmountDerived`.

### AD-06 — Form 8283: the $500 filing test

**The question.** Form 8283 must be attached for noncash contributions over $500. Over $500 per item, or in
total?

**The competing texts.** Form 8283 (Rev. December 2025), page 1 heading: "Attach one or more Forms 8283 to your
tax return if you claimed a total deduction of over $500 for all contributed property." Instructions for Form
8283 (Rev. December 2025), page 1, Who Must File: "You must file one or more Forms 8283 if the amount of your
deduction for each noncash contribution is more than $500. You must also file Form 8283 if you have a group of
similar items for which a total deduction of over $500 is claimed."

**What the software does.** The total over all noncash property. Because every item is included in the total,
any single item or group over $500 also passes the total test, so the software never omits a form the
per-item reading would require. It attaches the form in one extra case: several items each $500 or less that
together exceed $500.

**Why the owner chose it.** It follows the current form's heading, and the extra attachment is informational;
no tax amount changes.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `form8283:/form8283TotalDeductionForFilingTest`.

### AD-07 — Form 4562 Part V: which later-year car limit applies to a car placed in service before 2025

**The question.** The passenger-automobile depreciation limit for 2025 depends on how many tax years the car has
been in service and, for cars placed in service 2004 through 2017, on whether it is a truck or van. The tables
count "tax years in service", not calendar years.

**The IRS text.** 2025 Instructions for Form 4562, page 15: "the total of columns (h) and (i) on line 26 or 27 and
column (h) on line 25 for that automobile cannot exceed the applicable limit shown in Table 1, 2, 3, or 4."
Page 16, Table 2: a car placed in service in 2024 with "2" tax years in service, "$19,800"; in 2023 with "3",
"$11,700"; 2022 "4 or more", "$6,460"; 2021 "$5,860"; 2018 to 2020 "$5,760". Table 3 ("excluding trucks and vans
placed in service after 2002"): 2004-2005 "$1,675", 2006-2011 "$1,775", 2012-2017 "$1,875". Table 4 (trucks and
vans): 2004-2008 "$1,875", 2009 "$1,775", 2010-2012 "$1,875", 2013-2015 "$1,975", 2016-2017 "$2,075".
Publication 946 (2025), chapter 5, prints the same figures by "1st Year", "2nd Year", "3rd Year", "4th & Later Year".

**What the software does.** It counts the 2025 tax year in service as 2025 minus the placed-in-service year plus
one (a calendar-year return), caps column (h) at the table figure times the column (c) percentage, asks
"electric?" for cars placed in service August 6, 1997 through 2006 and "truck or van?" for non-electric cars
placed in service 2003 through 2017. For years the 2025 publications no longer print it uses the 2004 and 1998
editions of Publication 946 (the limit is fixed when the car is placed in service): 2003 $1,775 (truck or van
$1,975); 1997-2002 $1,775; electric cars $5,125 to $5,425; 1995-1997 $1,775; 1993-1994 $1,675; "Pre-1993"
$1,575, read as 1987-1992. A car placed in service before 1987 is refused: no publication in hand prints its limit.

**Why the call was made.** A 1040 return in this software is a calendar-year return, so the placed-in-service year
is the first tax year in service. Publication 946 (1998) prints "Pre-1993 ... 1,575" as one row; the software
applies it to the MACRS years 1987-1992 only, because a pre-1987 car was recovered under ACRS.

**Our best recommendation.** Keep the counting and the prior-year tables. Vendor a pre-1987 limit table if
that population appears, and lift the refusal.

**What we would like a reviewer to check.** That a car placed in service in a short first tax year still counts
that year as year 1; the Table 3/Table 4 split for 2003-2017; and the reading of "Pre-1993" as 1987-1992.

**Where it lives.** `form4562: /form4562ListedProperties/*/section280FLaterYearLimit`,
`form4562: /form4562ListedProperties/*/depreciationDeductionWithin280FCap`,
`form4562: /form4562ListedProperties/*/writableIsTruckOrVan`, `form4562: /form4562ListedProperties/*/writableIsElectricVehicle`,
`form4562: /knockoutPassengerAutomobilePlacedInServiceBefore1987`.

### AD-08 — Form 2555 housing deduction carryover when this year has no housing cost amount

**The question.** A filer could not deduct all of last year's foreign housing deduction, and carries the rest
to 2025. In 2025 the filer still has foreign earned income left over after the exclusions, but no housing cost
amount of their own (line 33 is not more than line 36). May the carryover be deducted?

**The IRS text.** IRC 911(c)(4)(C) (2024 edition of the United States Code, Title 26, page 2153): the amount not
allowed "shall be treated as a deduction allowable in computing adjusted gross income for the succeeding taxable
year (and only for the succeeding taxable year) to the extent of the limitation of clause (ii) for such
succeeding taxable year", and that limitation "is the excess of (I) the limitation of subparagraph (B) for such
taxable year, over (II) amounts treated as a deduction under subparagraph (A) for such taxable year."
Publication 54 (2025), page 19, Carryover: "The amount of carryover you can deduct is limited to your foreign
earned income for the year of the carryover minus the total of your foreign earned income exclusion, foreign
housing exclusion, and foreign housing deduction for that year." Form 2555 (2025), page 3, Part IX: "Complete
this part only if (a) line 33 is more than line 36, and (b) line 27 is more than line 43."

**What the software does.** Follows the Code and Publication 54: line 49 is the smaller of the carryover and
line 47 minus line 48, whether or not line 33 is more than line 36. The owner ruled this on 2026-09-27; the
software earlier followed the printed Part IX condition and dropped the carryover.

**Why the owner chose it.** The owner's general instruction is that the statute governs over a form. Here the
form adds a condition the Code and the IRS's own publication do not state, and the carryover is lost for good if
it is not used this year.

**Our best recommendation.** Keep it, as ruled. We found no regulation or other text that adds the form's
condition; a reviewer who knows of one should say so.

**What we would like a reviewer to check.** Whether Treas. Reg. 1.911-4 (which the maintainers do not hold) or any
other authority supports the printed form's condition (a).

**Where it lives.** `form2555Housing:/form2555Line49HousingDeductionCarryover`,
`form2555Housing:/writableForm2555Line49HousingDeductionCarryoverFromPriorTaxYear`.

### AD-09 — Form 2555 limit on housing expenses for a 366-day qualifying period

**The question.** A fiscal-year filer's qualifying period in the tax year can be 366 days. The Limit on Housing
Expenses Worksheet takes the full-year figure when line 1 is 365 and the daily figure when it is "less than
365". Which applies to 366?

**The IRS text.** Instructions for Form 2555 (2025), page 5, worksheet line 2: "No. If the amount on line 1 is less
than 365, skip line 2 and go to line 3." and "Yes. Locate the amount under the column Limitation on Housing
Expenses (full year)"; line 4: "Multiply line 1 by line 3. This is your limit on housing expenses." Form 2555
(2025), page 3, line 32: "Multiply $56.99 by the number of days on line 31. If 365 is entered on line 31, enter
$20,800 here."

**What the software does.** The daily figure times 366. Only exactly 365 days takes the full-year figure. This is
the maintainers' reading, not an owner ruling: the worksheet does not address 366.

**Why it was chosen.** Line 32 of the form, built the same way, gives the full-year figure only for 365 and
multiplies the daily rate by the days otherwise; the daily route never gives less than the full-year figure.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Whether the IRS expects a 366-day filer to use the full-year figure.

**Where it lives.** `form2555Housing:/form2555HousingLocations/*/limit`,
`form2555Housing:/form2555HousingLocations/*/days`.

### AD-10 — Form 7206 line 2: which age picks the long-term care premium limit?

**The question.** Line 2 caps each covered person's qualified long-term care premiums by an age band. The
statute speaks of the age "attained before the close of the taxable year". For other age tests (the age-65
additional standard deduction, for example) the IRS treats a person born on January 1 as reaching the new age
on the last day of the prior year. Does that day-before convention apply here, so that a person born
January 1, 1985 counts as 41 for 2025 (limit $900) and not 40 (limit $480)?

**The IRS text.** 26 U.S.C. 213(d)(10)(A) (2024 edition), page 938: "In the case of an individual with an
attained age before the close of the taxable year of:". Form 7206 (2025), page 1, line 2(b): "The amount shown
below. Use the person’s age at the end of the tax year." Instructions for Form 7206 (2025), page 2: "The amount
shown below. Use the person's age at the end of the tax year."

**What the software does.** It uses the age the person reaches in 2025 on the calendar: 2025 minus the birth
year. The day-before convention is not applied, so a person born January 1 stays in the lower band for that
year. This is the software's own reading; there is no owner ruling.

**Why the call was made.** The form and its instructions state the rule for this line in plain words, "age at
the end of the tax year", and neither mentions the day-before convention. Where the IRS applies that
convention it says so: Publication 501 (2025), page 3, "A child born on January 1, 2007, is considered to be
age 19 at the end of 2025" (the age test for reporting a child's income on the parent's return). Nothing like
it is printed for this line.

**Our best recommendation.** Keep it. The population is people born on January 1 whose age sits just below a
band boundary and whose premiums exceed the lower limit. If the reading is wrong, the filer is over-taxed by
the difference between two adjacent band limits ($420 to $3,010).

**What we would like a reviewer to check.** Whether the IRS applies the day-before convention to the section
213(d)(10) age bands, in any guidance other than the form and its instructions.

**Where it lives.** `form7206:/filers/*/form7206LongTermCarePremiumAgeBandLimit`,
`form7206:/familyAndHousehold/*/form7206LongTermCarePremiumAgeBandLimit`.
### AD-11 — Form 4562 line 12 on a return with more than one business: what the Summary prints

**The question.** When a filer with several businesses divides the section 179 deduction among them, does Part I
line 9 (and so lines 12 and 13) come from the listed property, or from the amounts the filer allocated?

**The IRS text.** 2025 Instructions for Form 4562, page 5, Line 12: "if you have more than one business or activity,
you may allocate your allowable section 179 expense deduction among them. To do so, enter “Summary” at the
top of Part I of the separate Form 4562 you are completing for the total amounts from all businesses or
activities. ... On line 12 of the Form 4562 you prepare for each separate business or activity, enter the amount
allocated to the business or activity from the “Summary.”" Page 5, Line 6: a partner reports a Schedule K-1
section 179 share on line 6 ("from Schedule K-1 (Form 1065)").

**What the software does.** The return's Form 4562 Part I is the Summary: line 9 comes from the line 6 and line 7
property, line 12 is lines 9 and 10 capped at line 11, and line 13 is what line 12 leaves. The amounts the filer
allocates to the activities must add up to that line 12; if they do not, the return is refused until they do
(owner ruling NE-8 applied: the instructions settle it).

**Why the call was made.** The instructions compute the Summary from the totals and allocate its line 12; an
allocation cannot replace line 9 without breaking the printed line 13.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** That a partner's Schedule K-1 section 179 amount belongs on the Summary
line 6 (and not only on the partnership activity's own form).

**Where it lives.** `form4562: /form4562Line12BeforeIncomeLimitation`, `form4562: /knockoutSection179AllocationDoesNotDivideSummaryLine12`.

### AD-12 — Form 4562 Part III column (g) and Part VI column (f): how the software computes them

**The question.** Form 4562 lets a filer figure 2025 depreciation on new property either with the optional Pub. 946
tables or by the instructions' own steps, and the two can differ by a dollar or so. Which does the software use,
and how does it count months of amortization?

**The IRS text.** 2025 Instructions for Form 4562, page 12, column (g): "you may use optional Tables A through E ...
Multiply column (c) by the applicable rate from the appropriate table ... Or, you may compute the deduction yourself
by completing the following steps." Step 1: divide 2.00 (200 DB), 1.50 (150 DB) or 1.00 (straight line) by the
recovery period; Step 3: multiply by the convention decimal (half-year 0.5; mid-quarter 0.875 to 0.125; mid-month
0.9583 to 0.0417). Page 19, line 42 column (f): "Dividing the amount in column (c) by the number of months over which
the costs are to be amortized and multiplying the result by the number of months in the amortization period
included in your tax year".

**What the software does.** Column (g) of a typed Section B or C row is column (c) times the Step 1 rate times the
Step 3 decimal, rounded to whole dollars; a test checks it against the Pub. 946 Appendix A table rate within the
table's printed precision. The 50-year classes take the mid-month decimals (the form preprints MM for them).
Column (f) counts the month amortization begins as a full month (13 less the beginning month). A row the filer did
not classify keeps the figure typed on the form; a row whose answers the law does not allow together is refused.
Operator ruling (NE-8, Q6): compute what the sources settle, refuse what they do not.

**Why the call was made.** The steps are the instructions' own computation and cover every classification and
class-life period with one rule; the tables are printed rounded to two or three decimals of a percent.

**Our best recommendation.** Keep the steps; if a reviewer prefers the tables, the constraint already carries them.

**What we would like a reviewer to check.** The one-dollar-plus-rounding tolerance between the two methods; the
full-month count of the beginning month on line 42.

**Where it lives.** `form4562: /form4562Assets/*/firstYearDepreciationRate`, `form4562: /form4562Assets/*/depreciationDeductionAllowed`,
`form4562: /form4562AdsAssets/*/depreciationDeductionAllowed`, `form4562: /form4562AmortizedCosts/*/amortizationForThisYearAllowed`,
`form4562: /knockoutForm4562DepreciationOrAmortizationRowContradicted`.
### AD-21 — Form 8689 line 25: the IRA deduction includes a section 219(f)(6) deduction

**The question.** Form 8689 line 25 allocates "your IRA deduction" to USVI income. When a filer's Schedule 1 line
20 includes a deduction under section 219(f)(6) for a prior-year excess contribution absorbed by this year's unused
limit, is that part of "your IRA deduction"?

**The IRS text.** Form 8689 (2025), page 4, Line 25: "Figure the amount to report on line 25 by (1) dividing your
USVI compensation or earned income by your total (worldwide) compensation or earned income, and (2) multiplying the
amount of your IRA deduction by the result in (1). Figure the amount of your spouse’s IRA deduction the same way."
IRC 219(f)(6) treats the absorbed excess as a contribution made for the year, so it is deducted under section 219
and reported on Schedule 1 line 20.

**What the software does.** Line 25 multiplies each spouse's own Schedule 1 line 20 IRA deduction, including the
section 219(f)(6) amount, by that spouse's USVI share of compensation. The filer no longer types the deduction a
second time.

**Why the call was made.** The deduction is an IRA deduction on the return; leaving it out would understate USVI
adjusted gross income deductions and the USVI share of tax.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** That no Form 8689 practice treats the section 219(f)(6) amount
separately.

**Where it lives.** `form8689: /form8689Line25`.

### AD-22 — Form 1040 line 10 for a filer who excludes territory income

**The question.** A bona fide resident of Puerto Rico (or another U.S. territory) who excludes territory income
under IRC 931 or 933 may deduct only part of the Schedule 1 adjustments. Which amount goes on Form 1040 line 10
and Schedule 1 line 26: the adjustments in full, or the part allowed?

**The IRS text.** Publication 1321 (Rev. 10-2025), page 6: "You cannot take any deductions from Part II of
Schedule 1 (Adjustments to Income) directly related to excluded Puerto Rico Income. For example, you cannot deduct
one-half of self-employment tax (Schedule SE) if you are excluding your self-employment income (Schedule C).
Adjustments to income which are not directly related to excluded Puerto Rico income must be allocated using the
formula for allocating the standard deduction shown above." Publication 570 (2025), page 33, on the
self-employment tax deduction: "The result is your self-employment tax on nonexcluded income. Include the
deductible part of this amount on Schedule 1 (Form 1040), line 15." Form 1040 (2025), line 11a: "Subtract line 10
from line 9. This is your adjusted gross income."

**What the software does.** It prints the part allowed on line 10 and on Schedule 1 line 26, and subtracts that
same amount from line 9 for adjusted gross income, so lines 9, 10 and 11a add up. The part allowed is figured on
the total: the self-employment tax deduction at the amount its own fraction allows, and the rest of the
adjustments by the gross-income fraction Publication 1321 gives for the standard deduction. Schedule 1 lines 11
through 25 still show each adjustment in full, so for these filers the Schedule 1 lines do not add up to line 26.

**Why the call was made.** Both publications have the filer enter only the deductible part on Schedule 1, and
adjusted gross income is line 9 less line 10. Printing the full adjustments on line 10 while subtracting less
would file a return whose own lines disagree.

**Our best recommendation.** Keep. Apportion each Schedule 1 line as well, so the schedule adds up to line 26.

**What we would like a reviewer to check.** Whether the IRS expects each Schedule 1 line to carry its apportioned
amount, or accepts the apportioned total on line 26 alone.

**Where it lives.** `taxCalculations: /adjustmentsToIncome` (line 10), `taxCalculations: /allowableAdjustmentsToIncome`
(the apportionment), `taxCalculations: /adjustmentsToIncomeBeforeTerritoryApportionment` (the full adjustments).

### AD-23 — HSA family limit: an agreed division between spouses, including on separate returns

**The question.** When spouses each have an HSA and either has family coverage, the family contribution limit is
divided equally between them unless they agree on a different division. The software used to divide it equally in
every case. Can a filer state an agreed share, and how is it checked when the spouses file separately and the other
spouse's return is not in front of the software?

**The IRS text.** IRC 223(b)(5)(B)(ii), page 970, left column: the limitation "after such reduction, shall be
divided equally between them unless they agree on a different division." Instructions for Form 8889 (2025), page 7,
Line 6: "divide the amount on line 5 equally between you and your spouse, unless you both agree on a different
allocation (such as allocating nothing to one spouse). Enter your allocable share on line 6." The statute speaks of
"individuals who are married to each other", with no condition on filing status.

**What the software does.** Each spouse may state an agreed share. On line 6 the stated share replaces the half,
capped at line 5 (the first bullet) or at the Step 1 amount (the second bullet, where it replaces the Step 2
half). On a joint return, if either spouse states a share and the two spouses' line 6 amounts add up to more than
the shared line 5, the return is refused until the shares are corrected. On a separate return the stated share is
taken as the filer's statement of the agreement, capped at line 5; the other spouse's share cannot be seen.

**Why the call was made.** The statute is clear that a different division is allowed and does not limit it to joint
returns, so the software follows it (the standing rule to follow the statute when it is clear). The cap is the one
check the law itself implies: a share of the limit cannot be more than the whole limit.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether practice expects any statement or election to be attached when
spouses filing separately divide the limit unequally.

**The Archer MSA twin.** IRC 220(b)(3)(B) states the same rule for an Archer MSA: when either spouse has family
coverage, the limitation "shall be divided equally between them unless they agree on a different division", and the
Instructions for Form 8853 (2025), page 4, Line 3, say for a separate return "if you and your spouse agree to divide
the 75% of the annual deductible in a different manner, enter your share." The software reads it the same way: a
stated share is Form 8853 line 3, capped at the undivided 75% limitation for the filer's months; on a joint return
two shares that add up to more than the couple's limitation are refused; on a separate return the filer's statement
is taken.

**Where it lives.** `hsa: /filers/*/writableHsaAgreedFamilyLimitShare`, `hsa: /filers/*/hsaLine6EqualDivisionHalfShare`,
`hsa: /knockoutHsaAgreedFamilyLimitDivisionExceedsTheLimit`; the Archer twin `hsa: /filers/*/writableArcherMsaAgreedFamilyLimitShare`,
`hsa: /filers/*/archerMsaForm8853Line3Limitation`, `hsa: /knockoutArcherMsaAgreedFamilyLimitDivisionExceedsTheLimit`.

### AD-24 — Qualified business income: the self-employed retirement plan deduction among several businesses

**The question.** The deduction for contributions to a SEP, SIMPLE or qualified plan (Schedule 1 line 16) reduces
qualified business income. When the return has more than one self-employment trade or business, how much of it
reduces each business's QBI?

**The IRS text.** Treas. Reg. 1.199A-3(b)(1)(vi) (26 CFR, 2025 edition, page 368): "deductions such as the deductible
portion of the tax on self-employment income under section 164(f), the self-employed health insurance deduction under
section 162(l), and the deduction for contributions to qualified retirement plans under section 404 are considered
attributable to a trade or business to the extent that the individual's gross income from the trade or business is
taken into account in calculating the allowable deduction, on a proportionate basis to the gross income received from
the trade or business." Instructions for Form 8995 (2025), page 2: QBI must account for items including the
"deductible part of self-employment tax, self-employed health insurance deduction, and contributions to qualified
retirement plans."

**What the software does.** Line 16 is multiplied by each business's net profit and divided by the total net profit of
every profitable self-employment business on the return (Schedule C line 31, Schedule F line 34, Schedule K-1 box 14
code A; the Form 7206 line 5 total). The Schedule C businesses' share reduces the QBI derived from Schedule C, on both
Form 8995 and Form 8995-A. A farm's or partnership's share reduces that business's own QBI, which the filer enters.
With one profitable business the whole line 16 amount reduces its QBI, as before.

**Why the call was made.** The regulation settles the attribution: proportionate to the income from each business
that was taken into account in figuring the deduction. The deduction is figured from net earnings from
self-employment, so net profit is the measure the return has for each business; a business with a loss contributes
nothing and gets no share. Line 16 is one figure for the return, so on a joint return where each spouse has a plan the
software prorates the total over both spouses' businesses.

**Our best recommendation.** Keep. If joint filers with separate plans need it, ask which business each plan covers.

**What we would like a reviewer to check.** That net profit (rather than gross receipts) is the right reading of
"gross income received from the trade or business" here, and the joint-return proration.

**Where it lives.** `qbi: /qbiScheduleCSelfEmployedRetirementPlanDeduction`,
`qbi: /qualifiedBusinesses/*/scheduleCAttributableRetirementPlanDeduction`.

### AD-25 — Qualified business income: the section 224 tips deduction among several businesses

**The question.** Qualified tips deducted under section 224 are not QBI. The deduction is figured once for the return
(Schedule 1-A line 5 and line 6). When a filer has two or more Schedule C businesses, how much of it leaves each
business's QBI on Form 8995-A?

**The IRS text.** Instructions for Form 8995-A (2025), page 1: "Do not include in QBI amounts that were deducted under
IRC 224 for qualified tips." Treas. Reg. 1.199A-3(b)(5) (26 CFR, 2025 edition, page 369): items attributable to more
than one trade or business are allocated "using a reasonable method based on all the facts and circumstances."

**What the software does.** Each linked Schedule C business takes the return's tips exclusion multiplied by its net
profit and divided by the total net profit of the profitable Schedule C businesses. The shares add up to the return
amount, so the exclusion leaves QBI once. With one profitable Schedule C the whole amount leaves that business.

**Why the call was made.** Before, the whole return amount left every business, which counted it once per business.
No printed line splits the tips among businesses, and section 224(c) limits business tips to each business's net
income, so net profit is a reasonable measure of where they can sit.

**Our best recommendation.** Keep. If filers need it, ask for the tips received in each business.

**What we would like a reviewer to check.** That the net-profit proration is a reasonable method when the filer has
not traced the tips to a business.

**Where it lives.** `qbi: /qualifiedBusinesses/*/scheduleCAttributableTipsExclusion`,
`qbi: /qbiScheduleCProfitableNetProfitTotal`.

### AD-26 — Educator expenses and the savings bond exclusion (Form 8815)

**The question.** Educator expenses must be reduced by the U.S. savings bond interest excluded on Form 8815.
But the Form 8815 exclusion depends on modified adjusted gross income, which includes the educator deduction.
How does the software break that loop, and how does one exclusion meet two educators' limited expenses on a
joint return?

**The IRS text.** IRC 62(d)(2) (U.S. Code, section 62(d), web edition): "A deduction shall be allowed under
subsection (a)(2)(D) for expenses only to the extent the amount of such expenses exceeds the amount excludable
under section 135, 529(c)(1), or 530(d)(2) for the taxable year." The Form 1040 instructions (2025), page 93:
"You must reduce your qualified expenses by the following amounts", the first being "Excludable U.S. series EE
and I savings bond interest from Form 8815". Form 8815 (2025), page 4, footnote: "For purposes of figuring the
amount to put on Form 8815, line 9, do not reduce your educator expenses, if any, by the amount on Form 8815,
line 14."

**What the software does.** (1) Schedule 1 line 11 is the entered expenses less the Form 8815 exclusion, then
limited to $300 per educator; on a joint return the exclusion is taken first from expenses above the limits
and only then from the limited amounts (the primary filer's first), so line 11 is the smaller of the limited
total and the total expenses less the exclusion. (2) Form 8815 line 9 uses the educator deduction before the
reduction, as the footnote says. So do the other modified AGIs the exclusion depends on (the IRA deduction,
social security benefits, the student loan interest deduction and the passive activity rules); adjusted gross
income itself uses the reduced line 11.

**Why we chose it.** The statute measures the expenses against the exclusion, and the instructions reduce the
expenses before the $300 limit; taking the exclusion from expenses above the limits first is the reading most
favourable to the filer that the words allow. The publications leave the loop between the IRA deduction, the
taxable social security benefits and the exclusion open; the Form 8815 footnote closes it for line 9 by
using the unreduced figure, and the software uses the same figure in the other modified AGIs so that the
computation has an order. In that small population those modified AGIs can be lower than a literal reading by
at most the reduction ($600 at most).

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** That the modified AGIs other than Form 8815 line 9 may use the
unreduced educator deduction, and the order in which one exclusion meets two educators' expenses.

**Where it lives.** `educatorAdjustment: /educatorExpensesAdjustment`,
`educatorAdjustment: /educatorExpensesBeforeSavingsBondExclusion`,
`taxCalculations: /adjustmentsToIncomeBeforeTerritoryApportionment`.

### AD-27 — No tax on tips and overtime: a joint return where one spouse has no valid SSN

**The question.** On a joint return, one spouse has a social security number valid for employment and the other does
not. The spouse without one received part of the qualified tips (or qualified overtime). Is the whole deduction lost,
or only that spouse's part?

**The IRS text.** IRC 224(e)(1) and 225(d)(1): "No deduction shall be allowed under this section unless the taxpayer
includes on the return of tax for the taxable year such individual's social security number." Instructions for Form
1040 (2025), Schedule 1-A, Part II: "If you are married filing a joint return, the spouse who received the qualified
tips must have a valid SSN." Part III says the same for overtime.

**What the software does.** When the spouse without a valid SSN received part of the amount, the filer states that
part. It is taken out of the amount the deduction counts (Schedule 1-A line 6 or line 14c as printed), and the rest,
received by the spouse with a valid SSN, is deducted within the cap and the phase-out. Until the part is stated, the
deduction waits.

**Why the call was made.** The statute conditions the deduction on "such individual's" number, the individual who
received the tips or overtime, and the instructions put the condition on "the spouse who received" them. Nothing
denies the other spouse's amounts. Denying the whole deduction, as the software used to, over-taxed these filers.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** That the per-spouse split is right on a joint return, and that line 6 and
line 14c should print the amount after that spouse's part is left out.

**Where it lives.** `schedule1A: /writableTipsReceivedByIneligibleSsnSpouseAmount`,
`schedule1A: /schedule1ATipsReceivedByIneligibleSsnSpouse`, `schedule1A: /allowableQualifiedTipsAmount` and their
overtime twins.

### AD-28 — Schedule A when adjusted gross income is negative

**The question.** Schedule A figures the medical floor as 7.5% of adjusted gross income and the charitable ceilings as
percentages of it. When adjusted gross income is negative, a percentage of it is negative. Does the medical deduction
then exceed the expenses, and can the charitable deduction be negative?

**The IRS text.** IRC 213(a): "There shall be allowed as a deduction the expenses paid during the taxable year [...]
for medical care [...] to the extent that such expenses exceed 7.5 percent of adjusted gross income." IRC
170(b)(1)(H): "the term 'contribution base' means adjusted gross income (computed without regard to any net operating
loss carryback to the taxable year under section 172)." Schedule A (2025), line 4: "Subtract line 3 from line 1. If
line 3 is more than line 1, enter -0-."

**What the software does.** The medical floor and every charitable percentage ceiling are figured on adjusted gross
income floored at zero. With a negative AGI, line 3 is $0 and the medical deduction equals the medical expenses; the
charitable ceilings are $0, so gifts subject to them are carried over and line 14 is not negative.

**Why the call was made.** The deduction is of "the expenses paid", so it cannot be more than they are; before, a
negative AGI made line 4 larger than line 1. A negative contribution base allows no current charitable deduction;
before, line 14 could go negative and raise taxable income.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** That a zero floor, not a negative one, is right for line 3, and that gifts
limited to 50% of AGI with no ceiling below it (cash to 60% organizations) are treated the same way.

**Where it lives.** `scheduleA: /scheduleAAgiForPercentageLimits`, `scheduleA: /medicalExpenseDeduction`,
`scheduleA: /charitableContributionsDeduction`.

### AD-30 — A minister's W-2 salary in IRA compensation

**The question.** A minister's salary reported on Form W-2 is wages in box 1, and the Schedule SE instructions also put it
on Schedule SE line 2. The IRA Deduction Worksheet adds wages (line 8) and self-employment earned income (line 9). Does
the salary count on both lines?

**The IRS text.** Form 1040 instructions (2025), page 98, IRA Deduction Worksheet line 8: "Wages, salaries, tips, etc.
Generally, this is the amount reported in box 1 of Form W-2." Line 9: "Enter the earned income you (and your spouse if
filing jointly) received as a self-employed individual or a partner." Instructions for Schedule SE (2025), page 1: "If you
must pay SE tax, include this income on Schedule SE, line 2." IRC 219(b)(1)(B) limits the deduction to "an amount equal to the
compensation includible in the individual’s gross income for such taxable year."

**What the software does.** The salary counts once, as wages on line 8. Line 9 takes the minister's Schedule SE
earnings less the ministerial W-2 salary, less Schedule 1 line 15 (and line 16), not below zero.

**Why the call was made.** The salary is included in gross income once, so it is compensation once. Line 9 asks for
earned income received as a self-employed individual; the salary was received as an employee and is already on line 8.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether the part of the Schedule 1 line 15 deduction that comes from the
salary should also reduce line 9, as the worksheet's literal words do, or be left out of it.

**Where it lives.** `scheduleSE: /primaryFilerSelfEmploymentEarnedIncomeForIraCompensation`,
`scheduleSE: /secondaryFilerSelfEmploymentEarnedIncomeForIraCompensation`.

### AD-32 — Section 933/931 exclusion: the self-employed health insurance deduction and a penalty on excluded interest

**The question.** A bona fide resident of Puerto Rico (or another territory) excludes some income and may take
no deduction "properly allocable to or chargeable against" it. Publication 1321 disallows adjustments directly
related to excluded income and apportions the rest. Where do the self-employed health insurance deduction and
the penalty on early withdrawal of savings fall?

**The IRS text.** Publication 1321 (Rev. October 2025), page 6: "You cannot take any deductions from Part II of
Schedule 1 (Adjustments to Income) directly related to excluded Puerto Rico Income." IRC 933(1): no deduction
"properly allocable to or chargeable against amounts excluded". 26 CFR 1.861-8(e)(9), which 1.933-1(c) points
to, lists among deductions "not definitely related to any gross income" the "deduction for medical expenses
allowed by section 213". IRC 162(l)(2)(A) limits the self-employed health insurance deduction to "earned income
(within the meaning of section 401(c))", and IRC 401(c)(2)(A)(iv) figures that earned income "without regard to
items which are not included in gross income".

**What the software does.** The self-employed health insurance deduction stays among the apportioned adjustments,
and the excluded Schedule C profit comes off its earned income limit on Form 7206 line 12 (the line that takes off
the Form 2555 exclusion). A penalty on a deposit the filer says earned excluded territory interest is directly
related to excluded income and is not deducted; other penalties stay apportioned.

**Why the call was made.** The earned income limit is statutory and clear, so it is built. The deduction itself is
for medical-care insurance, which the regulation treats as not definitely related to any income, so it is
apportioned like the other adjustments rather than disallowed. The penalty is forfeited interest or principal on
the deposit that produced the excluded interest, so it is allocable to that income. Form 7206 line 12 names only
Form 2555; the statute reaches every excluded item, so the territory amount goes on the same line.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether the section 162(l) deduction should instead be split by the
self-employment fraction, like the deductible part of self-employment tax, when the plan business's income is
partly excluded.

**Where it lives.** `form7206: /form7206Line12TerritoryExcludedEarnedIncome`, `/form7206Line12Form2555ExclusionOrZero`;
`interest: /interestReports/*/writableEarlyWithdrawalPenaltyOnExcludedTerritoryInterest`,
`/earlyWithdrawalPenaltyOnExcludedTerritoryInterest`; `taxCalculations: /allowableAdjustmentsToIncome`.

### AD-13 — Form 4562 for each business or activity: which line 22 goes where

**The question.** A filer with several businesses files a separate Form 4562 for each. How does the software
carry each form's line 22 to the right schedule, and what is each form's line 12?

**The IRS text.** 2025 Instructions for Form 4562, page 2: "File a separate Form 4562 for each business or activity
on your return for which Form 4562 is required." Page 5, Line 12: "On line 12 of the Form 4562 you prepare for each
separate business or activity, enter the amount allocated to the business or activity from the “Summary.”"
Form 4562 line 22: "Enter here and on the appropriate lines of your return."

**What the software does.** Up to five per-business copies (three Schedule C businesses, a Schedule F, a Form 4835;
the Schedule C limit is the three the self-employment forms print). The filer numbers the copies, assigns each
property row to a copy, and names the copy on each schedule; the schedule's depreciation line then carries that
copy's line 22 (its allocated line 12, lines 14 to 17, and its property). Each copy's line 12 is the amount the filer
allocates; the allocations must add up to the Summary line 12 (with one business, the whole of it), else the return
is refused. A return that numbers nothing works as before (one Form 4562, amounts entered on the schedules).
Operator ruling NE-8, Q2.

**Why the call was made.** The instructions make the allocation a filer choice ("you may allocate"), so the software
asks for it and checks the total rather than choosing a split. A copy per rental is not built: Schedule E computes its
own depreciation, and a Form 4562 copy would be a second source of the same number.

**Our best recommendation.** Keep it; add rental copies when Schedule E reads a Form 4562 line 22.

**What we would like a reviewer to check.** That a one-business return entering its whole Summary line 12 on its copy
is the right reading of "No other entry is required in Part I of the separate Form 4562".

**Where it lives.** `form4562: /form4562Copy1Line22Total` (and copies 2 to 5), `scheduleC: /scheduleCs/*/line13DepreciationAndSection179Entered`,
`scheduleF: /scheduleFLine14`, `form4835: /form4835Line12`, `form4562: /knockoutForm4562CopyLinkedTwiceOrNotAtAll`.

### AD-29 — Form 8283 line 1 column (d): a contribution date outside 2025 on a carryover-year return

**The question.** Form 8283 line 1 column (d) asks for the date property was contributed. A fgv audit
finding asked whether any date outside 2025 should be refused, since the field was a free string with no
validation at all.

**The IRS text.** Instructions for Form 8283 (2025), "Noncash Contributions Carried Over to Later Year":
"If your noncash contribution was subject to one or more limits based on your adjusted gross income, and
your unused charitable deduction from a previous year may be claimed in the current year, you must attach
to your current return a completed copy of the Form 8283 from the previous year" (a two-column extraction;
`https://www.irs.gov/pub/irs-pdf/i8283.pdf` line 815 LEFT, line 816 LEFT).

**What the software does.** `/form8283Items/*/writableContributionDate` is now typed as a calendar date
(it was an unvalidated free string). A test-only bound constraint,
`/constraints/federal/form8283/contributionDateInTaxYearUnlessCarryoverYear`, states that an item's date
falls in 2025 unless the whole return is a charitable carryover year
(`/writableForm8283RequiredForCarryoverYear` true), in which case a prior year's date is expected and
correct. No return is refused for a date outside 2025.

**Why the call was made.** The instructions themselves describe a legitimate population — a carryover-year
attachment — whose date is correctly outside the current tax year. An absolute knockout on any non-2025
date would refuse that population's legitimate return, which the project owner's standing rule (follow the
statute; never refuse a population the source itself describes as valid) forecloses. Flagging the
non-carryover population via a constraint, rather than a runtime knockout, keeps the return computable
while making the anomaly checkable.

**Our best recommendation.** Keep it. A future SERVICE-facing validation (a soft warning at intake when
the typed date falls outside 2025 and the carryover question is unanswered or No) would catch a likely
data-entry error earlier than a constraint alone, but is a screen-design decision outside this pass.

**What we would like a reviewer to check.** Whether a non-carryover return with a genuinely out-of-year
date (not a data-entry error — for example a fiscal-year filer) exists and needs its own carve-out.

**Where it lives.** `form8283: /form8283Items/*/writableContributionDate`,
`/writableForm8283RequiredForCarryoverYear`,
`/constraints/federal/form8283/contributionDateInTaxYearUnlessCarryoverYear`.

### AD-31 — Schedule A line 12: noncash gifts to 50% limit organizations other than capital gain property at fair market value

**The question.** Publication 526 Worksheet 2 line 9 takes noncash gifts to 50% limit organizations other than
capital gain property deducted at fair market value: ordinary income property, and capital gain property whose value
the filer reduced under the capital gain property election. Their deduction is reduced (IRC 170(e)(1)(A)) and they are
limited to 50% of AGI. Does the return compute the reduction, and where does Schedule K-1 code C go?

**The IRS text.** IRC 170(b)(1)(A): a contribution to a listed organization "shall be allowed to the extent that the
aggregate of such contributions does not exceed 50 percent of the taxpayer's contribution base for the taxable year."
IRC 170(e)(1)(A): the contribution is reduced by "the amount of gain which would not have been long-term capital gain".
Publication 526 (2025), page 26, Instructions for Worksheet 2: "For contributions of property, enter the property's FMV
unless you elected (or were required) to reduce the FMV as explained under Giving Property That Has Increased in Value.
In that case, enter the reduced amount." Page 27, Worksheet 2 line 17: "Deductible amount. Enter the smaller of line 9
or line 16." Instructions for Schedule K-1 (Form 1065) (2025), page 19: "Code C. Noncash contributions (50%). Report this
amount, subject to the 50% AGI limitation, on Schedule A (Form 1040), line 12."

**What the software does.** A new question takes the line 9 amount after the reduction, as the worksheet asks. The
deduction is the smaller of that amount and 50% of AGI minus the deductible cash gifts to 50% limit organizations
(line 17); the excess carries over (line 18). Line 9 then reduces the room for gifts to other organizations and for
capital gain property at fair market value, and line 17 comes before the 20% capital gain tier and qualified
conservation contributions, as Worksheet 2 orders them. Schedule K-1 code C joins line 9. Before, such gifts could only
be entered with capital gain property at fair market value and were held to 30% of AGI, and code C was held to 30% too.

**Why the call was made.** The statute's 50% limit is clear, and the worksheet itself has the filer enter the reduced
amount; computing the reduction would need the holding period and character of each item, which the return does not
collect. The K-1 instruction names the 50% limitation for code C.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** That the capital gain property election, which is not a question on the
return, is fairly left to the filer: once elected it covers all capital gain property given to 50% limit organizations
that year, including a Schedule K-1 code E amount, and it changes the carryover of earlier unelected gifts.

**Where it lives.** `scheduleA: /writableCharitable50PctOrgNonCash`, `scheduleA: /charitable50PctOrgNonCashDeductible`,
`scheduleA: /charitable50PctOrgNonCashCarryoverToNextYear`, `scheduleA: /charitable50PctOrgNonCashIncludingK1`.

### AD-45 — Form 8829 line 9: a home office casualty from a federally declared disaster

**The question.** A home used in a Schedule C business has a casualty or theft loss. Where does the part that results
from a federally declared disaster go, and what if two businesses use the home?

**The IRS text.** Instructions for Form 8829 (2025), page 3, Casualty losses reported on line 9: "Step 1. Complete a
worksheet version of Section A of Form 4684 treating all your casualty losses (and gains) as personal expenses." "Step
2. Include in column (b) of line 9 the loss amounts from lines 15 and 18 of this worksheet version of Form 4684 that are
attributable to the home in which you conducted the business and are the result of a federally declared disaster."
Instructions for Form 4684 (2025), page 10: "If the loss involved a home used for a business for which you are filing
Schedule C (Form 1040), Profit or Loss From Business, figure your deductible casualty or theft loss on Form 8829".

**What the software does.** It figures a home casualty through Form 8829 line 29 (the excess casualty loss, under the
income limit) and does not build line 9. It refuses a Schedule C home casualty unless the filer answers that the loss is
not from a federally declared disaster, and it refuses a home casualty on a return where two or more businesses file
Form 8829.

**Why the call was made.** Line 9 keeps the disaster share outside the income limit; putting it on line 29 would defer
or lose it. A home two businesses use needs its loss split between their Forms 8829, and the software links a home
casualty to one business.

**Our best recommendation.** Keep until line 9 (with the personal portion on Form 4684 Section A) and the split are
built.

**What we would like a reviewer to check.** Whether a filer claiming the standard deduction with no net qualified
disaster loss can be served now (line 9 is then zero).

**Where it lives.** `form8829: /knockoutForm8829HomeCasualtyNotCarried`,
`form4684: /casualtyEvents/*/homeCasualtyNotAttestedOutsideAFederallyDeclaredDisaster`.

### AD-46 — Form 4684 property columns: safe harbor and drywall figures, and a fifth column

**The question.** A filer enters the damaged properties of one event one by one (columns A to D) and also says the Rev.
Proc. 2018-08 safe harbor or the Rev. Proc. 2010-36 corrosive drywall procedure was used. Which figure goes on lines 7
and 8, and what happens to a fifth property?

**The IRS text.** Instructions for Form 4684 (2025), page 8, Lines 5 and 6: "When completing Form 4684, do not enter an
amount on line 5 or line 6 for each property. Instead, enter the decrease in the FMV determined in the relevant safe
harbor method on line 7." Page 7: "If more than four items were lost or damaged, use additional sheets". Publication 547
(2025), page 6: "Line 8. Enter the amount you paid to repair the damage to your home and household appliances due to
corrosive drywall."

**What the software does.** It refuses an event that is entered property by property and takes either method, because
the columns do not yet ask the per-property figure, and an event with more than four properties, because the extra
sheet is not printed. A Schedule C home prints its Form 8829 line 35 loss on line 27 of its one column, and a home
entered with more than one property is refused.

**Why the call was made.** The instructions put the method's figure on each property's line; using the fair market
values instead would ignore the method the filer chose.

**Our best recommendation.** Build the per-column figures and the additional sheet; keep the refusal until then.

**What we would like a reviewer to check.** Nothing beyond the build.

**Where it lives.** `form4684: /knockoutCasualtyPropertyColumnsNotCarried`,
`form4684: /casualtyEvents/*/propertyColumnsCannotBeCarried`,
`form4684: /casualtyEvents/*/properties/*/sectionBLineTwentySevenCasualtyLoss`.

## Credits

### CR-01 — Child and dependent care credit: Form 2441 line 29 zero or less

**The question.** In Part III of Form 2441, if employer-provided care benefits use up the whole dollar limit,
line 29 is zero or negative. Are lines 30-31 still completed (which would put a negative number on line 31 and
line 3)?

**The IRS text.** Form 2441 (2025), page 2, line 29: "Subtract line 28 from line 27. If zero or less, stop. You
can’t take the credit. Exception. If you paid 2024 expenses in 2025, see the instructions for line 9b". Line 31:
"Enter the smaller of line 29 or 30. Also, enter this amount on line 3 on page 1 of this form". Instructions for
Form 2441 (2025), page 4, Line 9b, sends the filer only to Worksheet A.

**What the software does.** Stop: lines 30-31 are left blank and line 3 is zero. Nothing negative is printed
or transmitted.

**Why the owner chose it.** The form says "stop".

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `cdcc:/cdccNetAllowableAmount`, `cdcc:/cdccSmallerOfTotalQualifyingExpensesAmount`,
`cdcc:/cdccQualifyingExpenses`.

### CR-02 — Child and dependent care credit: earned income of clergy and church employees

**The question.** How are wages that are also reported on Schedule SE (clergy, church employees) counted in
earned income for the credit, without counting them twice?

**The IRS text.** Instructions for Form 2441 (2025), page 4, Lines 4 and 5: earned income is "The amount shown
on Form 1040, 1040-SR, or 1040-NR, line 1z, minus any amount: [...] b. Also reported on Schedule SE (Form 1040)
because you were a member of the clergy or you received $108.28 or more of church employee income", plus "The
amount shown on Schedule SE (Form 1040), line 3, minus any deduction you claim on Schedule 1 (Form 1040), line
15", and "If you received church employee income of $108.28 or more, subtract any deduction you claim on
Schedule 1 (Form 1040), line 15, from the total of the amounts shown on Schedule SE (Form 1040), lines 3, 4b,
and 5a."

**What the software does.** It follows the list as written. The owner ratified the reading that the church
employee part needed no change.

**Why the owner chose it.** The instructions are explicit.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `income:/cdccPrimaryActualEarnedIncomeForCreditsUnfloored`,
`scheduleSE:/primaryFilerSelfEmploymentEarnedIncomeNetOfLoss`.

### CR-03 — General business credit (Form 3800): components not yet computed

**The question.** Form 3800 collects dozens of business credits, many from K-1s. Most component credits are not
yet computed. Should the software pass through an amount the filer states, or refuse?

**What the software does.** It refuses a return that carries a general business credit it does not compute: a
stated Schedule 3 line 6a amount, a K-1 credit code outside the few that are built, an estate or trust K-1
credit, or a Form 1099-PATR box 10 (investment credit) or box 11 (work opportunity credit) amount. A Form
1099-PATR box 12 (other credits and deductions) amount is treated the same way UNLESS Form 8941 line 15
already carries a pass-through credit, since Form 8941's own line 15 help text names box 12 as one of that
line's sources; box 12 mixes credits and deductions with no field to tell them apart, so an uncovered amount
is refused even where it might only be a deduction, rather than risk silently dropping a credit. The clean
vehicle credits that are built still file.

**Why the owner chose it.** The owner's words: "have a knockout for Form 3800 for now so we can have correctness
for what has been built". An uncomputed credit is either lost (over-tax) or unchecked (possible over-claim); the
box 12 reading follows the same logic where the box's own text does not settle which the filer holds.

**Our best recommendation.** Keep it (GEN-02). For box 12, build the document-to-Form-8941-line intake link, or a
Form 1099-PATR "credit or deduction" question, so a pure deduction is no longer refused.

**What we would like a reviewer to check.** Which component credits matter most to individual filers, so they
are built first; whether a Form 1099-PATR box 12 entry is ever a deduction in practice, which would help decide
whether the conservative refusal above is worth relaxing.

**Where it lives.** `form3800:/knockoutForm3800CreditComponentNotComputed`,
`form3800:/form1099PatrCreditComponentNotComputed`, `form3800:/form1099Patrs/*/form3800CreditComponentNotComputed`,
`form3800:/form3800PatrBox12CreditCarriedByForm8941`.

### CR-04 — Foreign tax credit: which Schedule K-3 recipients are refused

**The question.** A partnership or S corporation reports a partner's or shareholder's foreign taxes, their
reductions and redeterminations, and the category of foreign income on Schedule K-3. The software records the
schedule but does not carry its amounts to Form 1116 by itself; the filer enters them. Should it refuse every
return with a Schedule K-3, or only the cases it cannot handle?

**The IRS text.** Instructions for Form 1116 (2025), page 8: for Schedule K-3 Part III line 1, "Foreign taxes.
[...] Include these amounts in Part II of each of the applicable Forms 1116 (that is, a separate Form 1116 for
each category of income you received)". Page 9: for line 2, "Reduction of taxes. [...] Include these amounts on
line 12 of each of the applicable Forms 1116"; for line 3, "Foreign tax redeterminations. [...] Include these
amounts on each of the applicable Schedules C (Form 1116)". Page 2: "Generally, if you take the credit for any
eligible foreign taxes, you can’t take any part of that year’s foreign taxes as a deduction." Partner's
Instructions for Schedule K-3 (Form 1065) (2025), page 10: "Report the taxes on line 1 in the applicable
portions of Form 1116, Part II, [...] for the applicable separate category of income." Shareholder's
Instructions for Schedule K-3 (Form 1120-S) (2025), page 7: "Report the taxes on line 1 in the applicable
portions of Form 1116, Part II, for the applicable separate category of income." Instructions for Form 1040
(2025), page 115, the exception to filing Form 1116: "All of your foreign source gross income was from interest
and dividends and all of that income and the foreign tax paid on it were reported to you on Form 1099-INT, Form
1099-DIV, or Schedule K-3 (or substitute statement)."

**What the software does.** A Schedule K-3 recipient files when the return carries what the schedule reports,
and is refused only where it cannot be carried or is not carried. Refused: (A) a reduction of taxes on a return
that claims the credit with Form 1116 line 12 blank; (B) any foreign tax redetermination (Schedule C of Form 1116
is not built); (C) non-passive foreign income on the no-Form-1116 exception; (D) direct foreign taxes in a
category other than the one the return's Form 1116 reports (the software holds one Form 1116, and each category
needs its own); (E) on the Form 1116 route, Part II (before the holding-period and contested-tax bars) carrying
less than the Schedule K-3 direct foreign taxes of that category; (F) on the no-Form-1116 route, direct foreign
taxes outside the passive category; (G) on the no-Form-1116 route, a foreign tax entry smaller than the Schedule
K-3 direct foreign taxes. A Schedule K-3 row that gives only its total, with no category columns, is treated as
belonging to the category the Form 1116 reports. A filer who chose the deduction is not refused (CR-05).

**Why this call.** The owner's rule is to follow the instructions where they are clear and refuse only what the
software cannot carry, with the reason. The instructions say where each Schedule K-3 line goes and that the
credit, once taken, covers all of the year's eligible foreign taxes. So a return that carries them in full on a
matching Form 1116 or on the Schedule 3 line 1 entry files; a second category, a partial carry, a redetermination
and the exception mismatches are refused with the reason.

**Our best recommendation.** As built. Refusing every Schedule K-3 recipient would turn away returns that
already carry the schedule correctly; refusing none would file a credit that silently drops a category or part
of the tax.

**What we would like a reviewer to check.** (1) Whether a Part II total below the Schedule K-3 direct foreign
taxes of the same category can ever be correct (for example, taxes the filer lawfully leaves off Form 1116), in
which case refusal (E) and (G) is too strict. (2) Whether the Schedule K-3 column (f) "Other" taxes belong only
on a Form 1116 for section 901(j) income or income re-sourced by treaty.

**Where it lives.** `scheduleK3:/knockoutScheduleK3ForeignAmountsNotCarried`,
`scheduleK3:/scheduleK3DirectForeignTaxesOutsideForm1116Category`,
`scheduleK3:/scheduleK3Form1116PartIIGrossTaxesCompared`, `scheduleK3:/scheduleK3CreditClaimedOnForm1116`,
`scheduleK3:/scheduleK3CreditClaimedWithoutForm1116`, `scheduleK3:/scheduleK3ForeignTaxReductionsTotal`,
`scheduleK3:/formK3s/*/foreignTaxRedeterminationRows`, `foreignTaxCredit:/qualifiesForNoForm1116Exception`,
`form1116:/writableForm1116Line12ReductionInForeignTaxes`.

### CR-05 — Foreign tax credit: a Schedule K-3 recipient who deducts foreign taxes

**The question.** A Schedule K-3 reports direct foreign taxes, but neither credit route (Form 1116 or the
no-Form-1116 exception) carries an amount. If the filer has chosen to deduct foreign taxes instead of claiming
the credit, should the return still be refused?

**The IRS text.** IRC 901(a) (2024 edition of the United States Code, Title 26, page 2109): the credit is
allowed "if the taxpayer chooses to have the benefits of this subpart". Instructions for Form 1116 (2025),
page 2: "Instead of claiming a credit for eligible foreign taxes, you can choose to deduct foreign income taxes."

**What the software does.** The return files. The refusal applies only when the filer has not answered the
credit-or-deduction question. The owner ruled to release the filer who chose the deduction; this replaces an
earlier call that kept the refusal until the Schedule K-3 amounts were carried to Schedule A automatically.

**Why the owner chose it.** A filer who deducts is not claiming the credit, so no credit amount is missing.

**Our best recommendation.** Keep the release. The remaining risk is that the Schedule K-3 taxes never reach
Schedule A line 6, which the filer enters by hand.

**What we would like a reviewer to check.** Whether filers who deduct commonly omit Schedule K-3 foreign taxes
from Schedule A.

**Where it lives.** `foreignTaxCredit:/knockoutScheduleK3ForeignTaxesReachNoLine`,
`foreignTaxCredit:/writableElectsForeignTaxCreditUnderSection901`.

### CR-06 — Foreign tax credit without Form 1116, when the filer chose the deduction

**The question.** A filer whose foreign income is all passive and whose foreign taxes are no more than $300 ($600
joint) may claim the credit without filing Form 1116. If that filer answers that they deduct foreign taxes
instead, should the software still give the credit on Schedule 3 line 1?

**The IRS text.** IRC 904(j)(1)(A) (2024 edition of the United States Code, Title 26, page 2128): for an
individual to whom the subsection applies, "the limitation of subsection (a) shall not apply". Instructions for
Form 1116 (2025), page 1: "By making this election, the foreign tax credit limitation (lines 15 through 23 of the
form) won't apply to you." The same instructions, page 2: "Instead of claiming a credit for eligible foreign
taxes, you can choose to deduct foreign income taxes."

**What the software does.** No credit. The exception only removes the limitation for a filer who claims the
credit; a filer who chose the deduction has no credit to claim, and the taxes belong on Schedule A line 6. If
the question is unanswered, the software behaves as before. The owner ruled to build this.

**Why the owner chose it.** The Code makes the credit an election (IRC 901(a)), and the exception is part of that
election, not a separate benefit.

**Our best recommendation.** Keep it, as ruled.

**What we would like a reviewer to check.** Nothing further, unless a filer can take the credit for some foreign
taxes and deduct others in the same year (we read the instructions as saying no).

**Where it lives.** `foreignTaxCredit:/foreignTaxCreditAmount`,
`foreignTaxCredit:/qualifiesForNoForm1116Exception`,
`foreignTaxCredit:/writableElectsForeignTaxCreditUnderSection901`.

### CR-07 — Energy efficient home improvement credit: a typed total with no QMID for each item

**The question.** Form 5695 asks for the qualified manufacturer identification number (QMID) of each item of
specified property: the printed lines 19a to 29f take one or a few items each with their QMIDs, and lines 19e, 20b,
22b, 23b, 24b, 29b, 29d and 29f take "all other" items with a statement listing each item's QMID and cost. When a
filer types a cost total for a category, or a line b amount without that statement, the return holds at most one
QMID for the category and none for the other items. Does that typed amount earn a credit?

**The IRS text.** IRC 25C(h)(1) (2024 edition of the United States Code, Title 26): "No credit shall be allowed
under subsection (a) with respect to any item of specified property placed in service after December 31, 2024,
unless" the item "is produced by a qualified manufacturer" and "the taxpayer includes the qualified product
identification number of such item on the return of tax for the taxable year." Instructions for Form 5695 (2025),
page 6, Line 19e: "If you enter an amount on line 19e, attach a statement to your return listing the QMID and cost
of each item included on line 19e", with the same instruction for lines 20b, 22b, 23b, 24b, 29b, 29d and 29f.

**What the software does.** A typed category total, and a typed line b amount given without the per-item
statement, add $0 to the category's cost and credit. Items itemized on the printed lines with their own QMIDs, and
items listed on the statement with their QMIDs, count as before. The return is not refused. This is the owner's
ruling (NE-6, 2026-09-27: "follow the statute").

**Why.** The statute allows the credit item by item and only for an item whose own QMID is on the return. A typed
total cannot show which of its dollars, if any, belong to the one item whose QMID is reported. The owner chose a
$0 credit for that total over refusing the return until it is itemized.

**Our best recommendation.** Keep. The enabling property line 25c, which the form prints as one total with two QMID
boxes, is not changed.

**What we would like a reviewer to check.** That a single-item category entered as a typed total with the item's
QMID (for example one central air conditioner) should earn nothing until it is entered on the printed item line.

**Where it lives.** `form5695:/form5695Line19fOtherDoorCosts`, `form5695:/form5695Line19eOtherDoorCostsOrZero`,
`form5695:/form5695Line20cWindowSkylightCosts`, `form5695:/form5695Line22cCentralAcCosts`,
`form5695:/form5695Line23cFossilFuelWaterHeaterCosts`, `form5695:/form5695Line24cFurnaceBoilerCosts`,
`form5695:/form5695Line29HeatPumpCosts`, `form5695:/form5695Line29HeatPumpWaterHeaterCosts`,
`form5695:/form5695Line29BiomassCosts` and the line b `...CostsOrZero` facts of lines 20b, 22b, 23b, 24b, 29b,
29d and 29f.

### IN-270 — Form 5695 line 10 and the joint-occupancy cost ceiling: fuel cell capacity counts in whole half kilowatts

**The question.** Form 5695 line 10 prints "Kilowatt capacity of property on line 8 above" followed by "x $1,000".
Read literally, a 1.3 kW fuel cell gives $1,300. The joint-occupancy rule caps the cost that all occupants may
take into account at "$1,667 for each one-half kilowatt of capacity". Read as a rate, 1,300 W gives
$1,667 × 1,300 / 500 = $4,334.20. Does capacity between two half-kilowatt steps count in proportion, or only in
whole half kilowatts?

**The IRS text.** IRC 25D(b)(1) (2024 edition of the United States Code, Title 26): the credit "shall not exceed
$500 with respect to each half kilowatt of capacity of the qualified fuel cell property". IRC 25D(e)(4)(A): the
maximum expenditures "shall be $1,667 in the case of each half kilowatt of capacity". The 2026-09-22 preliminary
text is unchanged; Pub. L. 119-21 changed only 25D(g) and (h). Instructions for Form 5695 (2025), page 4, Line 10:
"The nameplate capacity must be 0.5 kW or greater to claim the credit and may only be claimed in half kW
increments. Multiply the kW capacity by $1,000 and enter the result." Form 5695 (2025), line 10: "If less than
0.5 kW, enter -0-."

**What the software should do (implementation in progress).** Count capacity in whole half kilowatts: line 10 is
$500 times the number of whole half kilowatts, and the joint-occupancy ceiling is $1,667 times that number. So
1,300 W gives $1,000 on line 10 and a $3,334 ceiling, and 750 W gives $500 and $1,667. Verify's open rows
FED-5695-P1-FUELCELLKW-039 and FED-5695-P1-JOINTOCC-037 found that today's facts scale linearly with watts.

**Why.** The statute grants the amount "with respect to each half kilowatt", and the instructions say capacity
"may only be claimed in half kW increments". The form's "x $1,000" is the same rule stated per kilowatt for a
capacity that is already a half-kilowatt multiple. Statute and instructions agree, so this is not a statute-over-form
departure. It records how a capacity between steps is read.

**Our best recommendation.** Keep (whole half kilowatts, rounded down).

**What we would like a reviewer to check.** That a capacity between steps rounds DOWN (1.3 kW counts as 1.0 kW, not
1.5 kW). The instructions' "only be claimed in half kW increments" implies it, but does not state the direction.

**Where it lives.** `form5695:/form5695Line10CapacityLimitForPrint`, `form5695:/form5695Line11FuelCellCreditAllowed`,
`form5695:/form5695FuelCellJointCapacityCreditLimit`, `form5695:/form5695FuelCellJointMaximumCombinedCost`. The
constraints that state it are `line10IsWholeHalfKilowattsTimes500ForJointOccupants` and
`fuelCellJointCostWithinWholeHalfKilowattCeiling` in `dictionary/ty2025-constraints/form5695Constraints.xml`.

### IN-271 — Form 5695 Part II: the QMID printed on an item's own line decides whether the item counts (ruled — lead 2026-09-30)

**The question.** The form prints a QMID box on each item line (19b, 19d, 20a, 22a, 23a, 24a, 25d, 29a, 29c, 29e),
and the "all other" lines (19e, 20b, 22b, 23b, 24b, 29b, 29d, 29f) take a statement listing each item's QMID and
cost. Suppose an item's QMID is held somewhere that does not print, or a line b amount is typed with no statement.
Does the item count?

**The IRS text.** IRC 25C(h)(1)(B) (2024 edition): no credit "unless" the "taxpayer includes the qualified product
identification number of such item on the return of tax" (26 U.S.C. 25C, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section25C&num=0&edition=2024). Instructions for Form 5695
(2025), page 1, What's New: the "qualified manufacturer identification number (QMID) for each item" (line 37).
Page 6: "If you enter an amount on line 20b, attach a statement" (line 413) "listing the QMID and cost of each item"
(line 414). Page 6, Line 19d: "next most expensive qualifying exterior doors in 2025" (line 398).

**Proposed call.**
- An item counts only when its QMID is in the box printed on its own line, or on the line b statement.
- Otherwise its printed cost is $0. That covers a QMID held only in an unprinted field, a row with no QMID, and a
  typed line b with no statement.
- The line totals add what is printed.
- Other items on the same line, each with its own QMID, still count. A missing QMID on one item never zeroes another.

**Why.** The statute allows the credit per item and only for a QMID that is on the return. A value the return does not print is not on the return.

**Where it lives.** The form5695 constraints `line22aCountsOnlyWithItsPrintedQmid` (and the 24a, 29a, 29c, 29e, 19a,
19d, 20a, 23a and 25c twins), and the cases `t5695-qmid-*`, `t5695-print-19d-entry-without-qmid` and
`t5695-print-20b-typed-without-statement`.

### IN-272 — Form 5695 line 25e: which enabled property makes enabling property creditable (ruled — lead 2026-09-30)

**The question.** Enabling property (a panelboard, sub-panelboard, branch circuit or feeder) qualifies when it is
"installed in conjunction with" a qualified improvement or qualified energy property. Must a credit be allowed for
the enabled property? And what if no line 25b code is entered?

**The IRS text.** IRC 25C(d)(2)(D)(iii) (2024 edition): "(I) any qualified energy efficiency improvements, or"
(26 U.S.C. 25C, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section25C&num=0&edition=2024); "(II) any qualified energy property described in subparagraphs (A) through (C) for which
a credit is allowed under this section for expenditures with respect to such property" (:156). Instructions for
Form 5695 (2025), page 6, Line 25b, codes A-G (lines 460-477): code A is windows and skylights on line 20a (an
energy efficiency improvement); codes B-G are energy property on lines 22a, 23a, 24a, 29a, 29c and 29e.

**Proposed call.**
- **Code A:** needs no credit to be allowed for the windows (subclause (I) has no such clause).
- **Codes B-G:** need a credit to be allowed for the enabled property on its own line (subclause (II)).
- **No code:** no enabled property is identified, so line 25e is $0.

**Where it lives.** The constraints `enablingCreditNeedsCreditOnTheEnabledEnergyProperty` and
`line25bCode1IsOneOfAThroughG`..`Code7`; the cases `t5695-enabling-code-b-*`.

**Code A addition (lead 2026-10-01, build pre-audit 3).** Code A counts only when a window or skylight is reported
on line 20a and taken into account on this return: Section A open (17a-17c Yes, 17e No) and a line 20a amount that
earns credit. The enabling property must be installed in conjunction with qualified energy efficiency improvements
(26 U.S.C. 25C, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section25C&num=0&edition=2024) on the principal residence, and the code list reads "Windows and skylights
reported on Form 5695, line 20a" (https://www.irs.gov/pub/irs-pdf/i5695.pdf, page 6). With Section A closed or no qualifying
window, code A earns nothing on line 25e or in the line 28 numerator.

### IN-273 — Form 5695 line 32a: joint occupants share the Part II limits (ruled — lead 2026-09-30)

**Lead ruling (2026-09-30).** Calls 1-4 adopted. On line 29h the seat-F reading (prorate only when the
occupant's own 30 percent exceeds $2,000) is rejected: the general paragraph names line 29h among the lines where the
allocable share is entered (lines 210-211) and triggers on the aggregate credit of all occupants (lines 204-205); the
line 223 paragraph applies the same $2,000 times own over total fraction and narrows nothing. Case
`t5695-jointocc-heat-pump-aggregate-over-2000` ($1,000) is the pin.

**The question.** How does a joint occupant who checks line 32a figure the Part II lines?

**The IRS text.** Instructions for Form 5695 (2025), page 3, Joint occupancy (Part II) (lines 198-227):
- "If the aggregate credit that would be allowed to all occupants for" an item "exceeds the credit limit below, then
  you must figure your allocable share" (lines 204-206). It is "the credit limit for that property multiplied by" a
  fraction (line 207) whose denominator "is the total amount paid by you and all other occupants" (line 209).
  This is entered "on lines 18b, 19c, 19h, 20d, 22d, 23d, 24d, 25e, 26c, and 29h" (lines 210-211).
- "If the total on line 27 is more than $1,200, then the credit" (line 214) is "$1,200" times a fraction whose
  numerator "is the sum of the amounts on lines 18a, 19a, 19f, 20a," 20b, 22a, 22b, 23a, 23b, 24a, 24b, 25c and 26b
  (lines 214-218).
- "If line 29h is more than $2,000" (line 223), the credit is "$2,000" times line 29g over the total paid
  (lines 223-226).

IRC 25C(f)(1) applies rules "similar to" 25D(e)(4) (26 U.S.C. 25C, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section25C&num=0&edition=2024). That joint-occupancy rule is written
for expenditures, so the instructions supply the credit-limit mechanics, which are used here.

**Proposed call.**
1. Each listed line is the smaller of the usual figure and the limit times own ÷ (own + others), rounded to whole
   dollars. This is the same as "prorate only when the occupants' combined credit exceeds the limit".
2. Line 28: when the occupant's own line 27 is over $1,200, line 28 is $1,200 times the lines 18a-26b amounts over
   those amounts plus the others' payments for the same properties. Otherwise line 28 is line 27.
3. Line 29h is in the per-property list, so rule 1 applies to it whenever the occupants' combined credit exceeds
   $2,000, even when the occupant's own 30 percent is not over $2,000. The separate "line 29h is more than $2,000"
   paragraph (read as the amount before the cap; the printed line never exceeds $2,000) adds nothing beyond rule 1.
4. The return is computed, not refused.

**Compared with the earlier readings.** These are the same, provided they apply rule 1 to line 29h when only the combined
credit, and not the occupant's own 30 percent, is over $2,000. The case `t5695-jointocc-heat-pump-aggregate-over-2000`
checks that: own $1,500, combined $3,000, line 29h $1,000.

**Addition (ruled 2026-10-01): which own figure goes into the fractions.** Adopted: the own figure is the printed, gated line amount (already limited to its nonbusiness part), and the denominator adds the others' payments for the corresponding properties only (i5695:218); the raw amount paid is rejected because it would put expenditures the statute does not take into account into the fraction. The per-line
fraction's numerator is "the amount you paid" (i5695:208). Line 28's numerator is "the sum of the amounts on lines
18a, 19a, 19f, 20a, 20b, 22a, 22b, 23a, 23b, 24a, 24b, 25c, and 26b" (i5695:216-217). The instructions also tell the
occupant to "enter the amounts you paid for the items on lines 18a, 19a," and the rest (i5695:200-202). So the figure
entered on those lines is the amount paid. Proposed reading:
- **Own figure:** the amount printed on each line. That is the amount paid, already limited to its nonbusiness part
  by the 80 percent rule (25D(e)(7) through 25C(f)(1)), since only that part "shall be taken into account".
- **Blank lines:** a line left blank because its section is closed (17a, 17b or 17c No; 21a or 21b No; 26a No)
  contributes nothing.
- **Denominator:** the own figure plus what the other occupants paid "for the corresponding properties" (i5695:218).
  A property with no amount on this return is not a corresponding property, so the others' payment for it is left
  out.
- **The alternative:** the raw "amount you paid" before the 80 percent rule. It would put money the statute does not
  take into account into the fractions.
- **Cases:** `t5695-jointocc-gate-a-closed-*` and `t5695-jointocc-line26a-no-audit-entered`. The constraint is
  `line28JointOccupantShare` (others counted only for properties with an amount on this return).

### IN-274 — Form 5695 lines 7c-8: a joint occupant whose fuel cell is used less than 80 percent for nonbusiness purposes (ruled — lead 2026-10-01)

**The question.** Which applies first: the 80 percent nonbusiness rule or the joint-occupancy ceiling?

**The IRS text.**
- IRC 25D(e)(7): "If less than 80 percent of the use of an item is for nonbusiness purposes, only that portion of
  the expenditures for such item which is properly allocable to use for nonbusiness purposes shall be taken into
  account" (26 U.S.C. 25D, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section25D&num=0&edition=2024).
- IRC 25D(e)(4)(B): the expenditures allocated to an individual are the lesser of "the amount of expenditures made
  by such individual" and the maximum times a fraction (lines 112-120).

**Proposed call.** Apply (e)(7) first, then (e)(4):
- the occupant's expenditure taken into account is the nonbusiness portion;
- the fraction is that portion over that portion plus the other occupants' payments (all occupants' total less this
  occupant's whole cost);
- the allocated cost is the lesser of the portion and the ceiling share.

Neither the occupant nor the return is held for this population. Example (`generic/a1-main-fuel-mixed-use-below-80`):
- $12,000 at 79% gives $9,480;
- the others paid $8,000;
- 5 kW gives a $16,670 ceiling;
- $16,670 × 9,480 / 17,480 = $9,040.71;
- so line 9 is $2,712.

**Why.** Section (e)(7) says what "shall be taken into account" for every purpose of the section, including the
(e)(4) allocation. The order matters only when the ceiling binds, as in this example. The cases with an
item-list line 8 (`t5695-jointfc-*`) use capacities where it does not bind.

### IN-275 — Form 5695 typed figures carried from another form: the other home's line 30, and a typed line 10 (ruled — lead 2026-10-01)

**The question.**
- A joint return with two main homes enters the other home's line 30 by hand. What if it is above $3,200?
- A typed line 10 (kW × $1,000) can disagree with the kilowatt capacity entered. Which one counts?

**The IRS text.**
- Instructions for Form 5695 (2025), page 3: "1. Complete lines 17a through 30 of a separate Form 5695 for"
  (line 190) each main home. Each form's line 28 is at most $1,200 (f5695:197) and its line 29h at most $2,000
  (f5695:220).
- Line 10: "may only be claimed in half kW increments. Multiply the kW" capacity by $1,000 (i5695:267).

**Proposed call.**
- **Other home's line 30 above $3,200:** it cannot be the other form's line 30. Line 30 is held (the return is
  Incomplete, with the hold visible in flowIncomplete), not capped and not passed through. Up to $3,200 flows
  unchanged.
- **Typed line 10:** the capacity decides. A typed amount that is not $500 times whole half kilowatts does not
  override the capacity (1.3 kW gives $1,000 whatever the typed figure).
- **The line 12 carryforward:** it comes from the 2024 Form 5695 line 16, which has no printed cap, so its only
  source range is "not below zero".

**Where it lives.**
- Constraints: `line30SecondHomeWithinItsOwnCaps`, `line10IsAMultipleOf500`, `line12StaysInItsPrintedRange`.
- Cases: `t5695-mfj-second-home-line30-*`, `t5695-fuel-typed-line10-not-a-half-kw-step`,
  `generic/a1-main-fuel-typed-line10-yields-to-capacity`.

### CR-08 — Provisional credit for a contested foreign tax: is the election made without Form 7204?

**The question.** A filer states a contested foreign income tax on Form 1116 and answers that they elect the
provisional credit for it, but does not say they are filing Form 7204, the provisional foreign tax credit agreement.
Is the contested tax credited?

**The IRS text.** Treas. Reg. 1.905-1(c)(3) (2025 edition, page 1025): "To make the election, a taxpayer must file
a Form 1116 (Foreign Tax Credit (Individual, Estate, or Trust)) or Form 1118 (Foreign Tax Credit—Corporations), and
the agreement described in paragraphs (d)(4)(ii) and (iii) of this section." Paragraph (d)(4) (page 1027) says the
same for the accrual-method election. Instructions for Form 1116 (2025), page 5: "To make the election, you must file
Form 1116 for the tax year the contested liability is paid and Form 7204."

**What the software does.** Asks, for each country row with an election, whether Form 7204 is filed. The contested
tax is credited only when both the election and the Form 7204 answer are yes. When the Form 7204 question is
unanswered or answered no, the election is not made, so the contested amount stays out of column (u) and is not
credited this year. The return is not refused. This follows the owner's direction of 2026-09-27 to build the
condition the regulation imposes.

**Why.** The regulation makes filing the agreement part of making the election. Without it no election exists and
the general rule applies: a contested tax is not creditable until the contest is resolved.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** That a later filing of the agreement (with an amended return) is the
only remedy, so denial on this return is right.

**Where it lives.** `form1116:/form1116ForeignCountries/*/writableFilesForm7204ProvisionalCreditAgreement`,
`form1116:/form1116ForeignCountries/*/writableElectsProvisionalCreditForContestedTaxes`,
`form1116:/form1116ForeignCountries/*/form1116ColumnUContestedTaxesNotCreditable`.

### CR-13 — Form 8801: which answer gives the 2024 filing status

**The question.** Form 8801 lines 11, 33 and 54 refigure the 2024 minimum tax, and the top of the 26 percent band
depends on the 2024 filing status. The software asks on the Form 8801 screen whether the filer was married filing
separately for 2024. A filer may also have given the 2024 filing status for the state and local income tax refund
worksheet. Which answer is used when the Form 8801 question is left blank, and which wins when the two disagree?

**The IRS text.** Form 8801 (2025), page 1, line 11: "All others: If line 10 is $232,600 or less ($116,300 or less if
married filing separately for 2024), multiply line 10 by 26% (0.26)." The status is a fact about the 2024 return;
no instruction ranks one answer over another.

**What the software does.** The Form 8801 answer decides when it is given. When it is blank, the 2024 filing status
given for the refund worksheet decides (married filing separately, or any other status). When both are given and
disagree, the Form 8801 answer wins. With neither given, the lines fall back as before.

**Why.** Both questions ask for the same 2024 fact, so a second question is not needed when the first was answered.
The Form 8801 question is asked for this computation, so it is the better answer when the two conflict.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether a disagreement should instead stop the return until the filer
corrects one of the answers.

**Where it lives.** `form6251: /form8801PriorYearFilingStatusWasMarriedFilingSeparately`,
`form6251: /form8801PriorYearAmtRateBreakpoint`, `form6251: /form8801PriorYearAmtRateSubtraction`,
`income: /writablePriorYearFilingStatus`.

### CR-14 — Form 8396: a reissued certificate at a higher rate, and a home that was the main home for part of the year

**The question.** (1) A filer who refinanced holds a reissued mortgage credit certificate whose credit rate is above the
original certificate's. Is a credit allowed under it? (2) A filer's home was the main home for only part of 2025. Is the
credit lost for the year, or figured for part of it?

**The IRS text.** Form 8396 (2025), page 2, Refinanced Mortgage: "You can refinance your mortgage without losing this credit
if your existing MCC is reissued and the reissued certificate meets all of the following conditions. [...] The credit rate of
the reissued certificate cannot exceed the credit rate of the existing certificate." IRC 25(e)(3)(A): a certificate "shall be
treated as in effect with respect to interest attributable to the period" beginning on its issue date and ending on the
earlier of its revocation or the date "the residence to which such certificate relates ceases to be the principal residence".

**What the software does.** (1) No credit is allowed under a reissued certificate whose rate is above the original's: line 3
is $0 in a year after the refinance, and in the refinance year only the original certificate's part is kept. (2) A filer whose
home was the main home for part of the year enters on line 1 only the interest for that part and answers the main-home
question Yes; the credit is figured on that interest.

**Why.** The form makes the rate condition part of keeping the credit through a refinance, and the statute ties the
certificate to interest for the period the home is the principal residence.

**Our best recommendation.** Keep.

**What we would like a reviewer to check.** Whether the refinance-year statement for a higher-rate reissued certificate
should show the reissued period at all.

**Where it lives.** `form8396: /form8396ReissuedRateAboveOriginal`, `form8396: /form8396TentativeCredit`,
`form8396: /form8396ReissuedMccSplitReissuedCredit`, `form8396: /writableMccHomeIsMainHomeInIssuersJurisdiction`.

### CR-15 — Form 8941: the two phaseout reductions, rounded or exact, and the zero floor

**The question.** (1) Worksheets 5 and 6 turn each phaseout into a decimal "rounded to at least 3 places" before
multiplying. How many places does the software keep? (2) Both reductions are taken from line 7. When together they are
more than line 7 (for example 20 full-time equivalent employees and $60,000 average wages), Worksheet 6 line 7 prints no
floor, so the subtraction would go below zero. Is line 9 negative, or $0?

**The IRS text.** IRC 45R(c): "The amount of the credit determined under subsection (b) without regard to this
subsection shall be reduced (but not below zero) by the sum of the following amounts:" and (c)(1): "Such amount
multiplied by a fraction the numerator of which is the total number of full-time equivalent employees of the employer in
excess of 10 and the denominator of which is 15." Instructions for Form 8941 (2025), page 8, Worksheet 5 line 4: "Divide
line 3 by 15. Enter the result as a decimal (rounded to at least 3 places)"; Worksheet 6 line 7: "Subtract line 6 from
line 1. Report this amount on Form 8941, line 9".

**What the software does.** (1) It multiplies line 7 by the exact fraction and rounds the product once, to the cent.
(2) Line 9 is never below $0. This is the maintainers' reading under the standing rule to follow the statute where it is
clear, not an owner ruling.

**Why it was chosen.** The statute states the exact fraction, and an exact fraction is a decimal of at least three places,
so the form allows it. PR-03 keeps exactly three places for Form 2555 line 35 because that decimal is a printed box; the
worksheet decimals here are not printed on Form 8941, so there is no box to match, and rounding once avoids a second
rounding step. The floor is the statute's own words; a negative line 9 would make line 12 negative and reduce other
general business credits on Form 3800.

**Our best recommendation.** Keep both.

**What we would like a reviewer to check.** Whether the IRS expects the three-place decimal in practice (the difference is
cents), and confirm the floor.

**Where it lives.** `form8941: /form8941Line8`, `form8941: /form8941Line9`.

### CR-16 — Form 8881: which employees line 6a counts, a plan with no eligible rank-and-file employee, and the prior-plan test for the contributions credit

**The question.** (1) Form 8881 line 6a asks for "the number of employees from the preceding tax year". Does it count
every employee, or only those paid at least $5,000, the count that decides whether an employer is eligible at all? And is
that the same count the Part III caution ("more than 100 employees in the preceding tax year") means? (2) Line 4 is at
least $500 even when line 3 is zero. Is a startup costs credit allowed for a plan in which no employee who is not highly
compensated is eligible? (3) The statute applies its prior-plan disqualification to the contributions credit only in the
year the plan is established. Does a disqualified employer get the contributions credit in the plan's later years?

**The IRS text.** IRC 45E(f)(4) (U.S. Code, Title 26, page 275): "whether an employer is an eligible employer and the
number of employees of an employer shall be determined under the rules of subsection (c), except that paragraph (2)
thereof shall only apply to the taxable year during which the eligible employer plan to which this section applies is
established with respect to the eligible employer." Subsection (c) takes the eligible employer of IRC 408(p)(2)(C)(i),
"an employer which had no more than 100 employees who received at least $5,000 of compensation from the employer for the
preceding year" (page 1317). IRC 45E(d)(1)(B) (page 274): qualified startup costs do not "include any expense in
connection with a plan that does not have at least 1 employee eligible to participate who is not a highly compensated
employee." Form 8881 (Rev. December 2025), page 1, line 4: "Enter the greater of $500 or the amount from line 3 (Do not
enter more than $5,000)". Instructions for Form 8881 (Rev. December 2025), page 2: "you are not an eligible employer if
during the 3 tax years preceding the tax year during which the plan becomes effective, you established or maintained a
qualified employer plan with respect to which contributions were made or benefits were accrued for substantially the same
employees as are in the new eligible employer plan".

**What the software does.** (1) Line 6a asks for the employees paid at least $5,000 in the preceding tax year, and the
same answer decides the Part III 100-employee caution. (2) No startup costs credit (line 5 is $0) when the line 3 count is
zero. (3) One question asks whether a qualified plan covered substantially the same employees in the 3 years before the
plan; a Yes gives $0 on line 5 and on line 6g in every year.

**Why.** (1) The statute says the number of employees for the contributions credit is determined under subsection (c),
which counts only employees paid at least $5,000, and IRC 45AA(c) uses the same eligible-employer definition. (2) The
statute is clear, and it governs over a printed line that does not repeat the condition: costs of such a plan are not
qualified startup costs, so line 1 is $0 and so is the credit. (3) The limit to the establishment year stops the new
plan itself, which exists in the plan's later years, from disqualifying it; it does not read as reopening the credit to an
employer that was disqualified when the plan began, and the instructions tie the test to the year the plan becomes
effective.

**Our best recommendation.** Keep (1) and (2). (3) is the weaker reading: an expert may read the text literally, which
allows the credit from the second plan year on.

**What we would like a reviewer to check.** Reading (3); and whether an employer that grows past 100 employees keeps the
contributions or military spouse credit under the two-year grace period of IRC 408(p)(2)(C)(i)(II), which this software
does not apply (it gives $0 above 100 employees).

**Where it lives.** `form8881: /writableForm8881Line6aEmployeesPrecedingTaxYear`, `form8881: /form8881PartIiiEmployerEligible`,
`form8881: /form8881Section1EmployerEligible`, `form8881: /form8881Line5`, `form8881: /form8881Line6g`.

### CR-17 — Form 8936 Schedule A copies: does the MAGI limitation deny the business AND personal halves of the new clean vehicle credit?

**The question.** IRC 30D(f)(10) denies "the credit allowed under subsection (a)" outright when the lesser of the
taxpayer's current- and prior-year modified AGI exceeds the threshold. Subsection (a) is the whole new clean vehicle
credit; (c)(1) and (c)(2) later re-characterize part of that same allowance as a general business credit (business/
investment use) and part as a personal credit. When a filer enters one or more Schedule A (Form 8936) vehicle copies (as
opposed to using the single-vehicle scalar intake), does the MAGI denial reach the business-use amount transcribed onto
Schedule A line 11 (box f230), or only the personal-use amount on line 12?

**The IRS text.** IRC 30D(f)(10)(A) (U.S. Code, Title 26, prelim, current through Sept. 22, 2026): "No credit shall be
allowed under subsection (a) for any taxable year if- the lesser of- the modified adjusted gross income of the taxpayer
for such taxable year, or the modified adjusted gross income of the taxpayer for the preceding taxable year, exceeds-
the threshold amount." IRC 30D(c)(1): "So much of the credit which would be allowed under subsection (a) for any taxable
year (determined without regard to this subsection) that is attributable to property of a character subject to an
allowance for depreciation shall be treated as a credit listed in section 38(b)." 2025 Instructions for Form 8936, "Part
I-Modified Adjusted Gross Income (MAGI) Amount": "Enter your modified AGI for the current and prior tax year. For 2025,
there is a limitation on the modified AGI" - printed once, ahead of both Part II (business/investment use) and Part III
(personal use), not restated separately for either. Schedule A (Form 8936), page 1, line 8d: "Yes. Stop here.", which
stops the filer before reaching either line 11 (business, box f230) or line 12 (personal, box f240).

**What the software does.** Denies BOTH halves: when a Schedule A copy is entered and the shared MAGI test (computed
once for the taxpayer, not per vehicle and not per business/personal split) fails for both years, Form 8936 line 6
(business-use sum) AND line 9 (personal-use sum) are each $0, gated the same way the single-vehicle scalar arm's own
business and personal lines already were. A MAGI test that cannot yet be decided (AGI or filing status unanswered)
leaves the line Incomplete, not $0. (Line 9's fix landed in the same pass that raised this entry, after the lead
flagged the asymmetry noted below as a live silent over-credit needing an immediate fix, not a deferral.)

**Why.** (c)(1) reassigns only "so much of the credit which would be allowed under subsection (a)"; (f)(10) makes that
allowance zero before the (c)(1)/(c)(2) split ever runs, so nothing reaches section 38(b) to reassign. The statute does
not carve the business/investment-use portion out of the denial, and the Form 8936 instructions compute MAGI once, ahead
of the Part II/Part III split, not once per use. Schedule A's own line 8d "stop here" instruction reaches a filer before
either line 11 or line 12, so a correctly prepared paper Schedule A would already show the business amount at $0 or blank
when MAGI denies; the graph enforces the same result independently rather than trusting an unverified transcribed figure.

**Update (same day, same pass): the personal-use arm is fixed too.** The first cut of this reading fixed only the
business half and left the personal-use Schedule A copies arm (line 9/12, box f240) as a named, unresolved asymmetry:
its sibling constraint (`/constraints/federal/form8936/form8936Line9ZeroWhenMagiExceedsTheLimitBothYears`) explicitly
stated it was "not engaged on the Schedule A copies arm, whose line 12 amounts are transcribed." The owner's standing
rule (FACT-SKILL-1 §2.8: "a live tax bug is fixed now, never deferred") applies here without qualification: this was
already a live silent OVER-CREDIT (the personal collection sum kept paying a credit the statute denies), not a
disputed reading needing more review. `form8936PartIIIPersonalUseCreditFromScheduleA` now takes the identical
three-way split as the business arm (MAGI denies -> $0; allows -> unchanged; undecided -> Incomplete). Fixing it
surfaced a second, pre-existing defect: the OLDER identity constraint
`form8936Line9NotBelowEveryVehicleOnTheScheduleACopies` ("line 9 never resolves below the sum of every entered
vehicle") had no MAGI exception in its own condition of application, so it VIOLATED the moment line 9 was correctly
zeroed by a MAGI denial. That constraint's Applies is corrected to exclude the MAGI-denies population (the identity
is a statement about the ordinary case, not about a year in which subsection (a) allows no credit at all) - a case of
"the constraint misread its source," per FACT-CONSTRAINT §2.5, not a fact defect.

**Our best recommendation.** Keep this reading for both halves; it follows the statute's plain text and the Form 8936
instructions' own single, unsplit MAGI computation. Nothing left open on this question.

**What we would like a reviewer to check.** Whether a corporation, estate or trust filer (for whom "the modified
adjusted gross income limitation does not apply", 2025 Instructions for Form 8936, "Part I" caution) could ever reach
this arm through a pass-through Schedule A copy; this dictionary's single-filer, individual-return scope does not model
that population today.

**Where it lives.** `form8936: /form8936PartIIBusinessUseCreditFromScheduleA`, `form8936: /form8936PartIIIPersonalUseCreditFromScheduleA`,
`cleanVehicleCreditRepayment: /newCleanVehicleMagiAllowsCredit`,
`/constraints/federal/form8936/form8936Line6ZeroWhenMagiExceedsTheLimitBothYears`,
`/constraints/federal/form8936/form8936Line9ZeroWhenMagiExceedsTheLimitBothYearsOnTheScheduleACopies`.

### CR-37 — Form 8881: the third-year per-employee cap on line 6c

**The question.** The line 6c instructions tell the filer not to include contributions of more than $1,334 per employee
in the third year of the plan. At that year's 75% applicable percentage, $1,334 gives $1,000.50. Is the cap $1,334, or
the $1,333.33 that keeps the credit at the statute's $1,000?

**The IRS text.** IRC 45E(f)(2)(A) (U.S. Code, Title 26, section 45E; the current text is unchanged since the 2022
amendment): "The amount determined under paragraph (1) (before the application of subparagraph (B)) with respect to any
employee of the employer shall not exceed $1,000." IRC 45E(f)(3) sets the applicable percentage at 75 percent for the
second taxable year after the year the plan is established, which the form counts as the third year of the plan.
Instructions for Form 8881 (December 2025), page 4, Line 6c: "The employer contribution credit is subject to a $1,000
limit per employee after taking into account the percentage that applies on Line 6g" and "include contributions of more
than $1,334 per employee."

**What the software does.** The line 6c help text tells the filer to count no more than $1,333.33 for any one employee in
the third plan year, and says the printed $1,334 would give $1,000.50. Line 6c is the filer's capped total; this return
does not take contributions employee by employee.

**Why.** The statute is clear and states the cap as a credit amount, $1,000 per employee; the instructions' own first
sentence says the same. $1,334 is a rounded-up conversion of that credit cap into contributions, and the statute governs
over a narrower or rounded printed figure (owner rule, follow the statute when it is clear).

**Our best recommendation.** Keep. The difference is at most $0.50 per employee.

**What we would like a reviewer to check.** Whether the IRS intends $1,334 as an administrative whole-dollar convention
that a filer may rely on.

**Where it lives.** `form8881: /writableForm8881Line6cCappedEmployerContributions`.

## Other taxes

### CR-09 — Earned income credit: foreign-government wages reported twice

**The question.** A U.S. citizen paid by a foreign government or an international organization for services
in the United States usually gets no Form W-2. The wages go on Form 1040 line 1h, and IRC 1402(c)(2)(C) also
makes them self-employment income on Schedule SE line 2. EIC earned income adds wages and net earnings from
self-employment. Are these wages counted once or twice?

**The IRS text.** IRC 32(c)(2)(A) (U.S. Code p. 137): earned income means "(i) wages, salaries, tips, and
other employee compensation ... plus (ii) the amount of the taxpayer's net earnings from self-employment".
The Schedule SE instructions (2025), "U.S. Citizens Employed by Foreign Governments or International
Organizations", put the income on Schedule SE line 2. No printed source addresses the EIC for this population.
The Form 1040 instructions (2025), page 43, treat the two other dual-reported populations, clergy and church
employees: subtract the amount also reported on Schedule SE from the line 1z (or 1a) figure on the EIC
worksheet.

**What the software does.** It counts the wages once: the amount that is on both line 1h and Schedule SE line 2
is subtracted from the wage figure, and the self-employment earnings keep it, as the Clergy instruction does.

**Why we chose it.** The statute adds two categories of amounts; one amount that falls in both is still one
amount of income earned. The only printed treatment of dual-reported earned income removes the duplicate from
the wage figure. Counting it twice would raise the credit on the phase-in and plateau and cut it above the
phaseout threshold, on no reading of the statute.

**Our best recommendation.** Keep it. Confidence is medium because no IRS text names this population.

**What we would like a reviewer to check.** Whether the IRS figures the EIC for these filers from line 1h or
from Schedule SE (the result is the same either way once the amount counts once).

**Where it lives.** `eitc:/eitcForeignGovernmentWagesDualReportedSubtrahend`, `eitc:/eitcEarnedIncomeBase`.

### CR-10 — Earned income credit: a child born and died with no SSN and no document, beside a counted sibling

**The question.** A child born and died in 2025 with no SSN can still be listed on Schedule EIC if the
birth certificate, death certificate or hospital records are attached. When there is neither an SSN nor the
document, the child cannot be claimed as a dependent or counted for the EIC. Must the return be refused when the
filer has another child who is counted?

**The IRS text.** Schedule EIC (2025), line 2: "The child must have an SSN as defined in the instructions for
Form 1040, line 27a, unless the child was born and died in 2025 or you are claiming the self-only EIC". IRC
32(c)(3)(D) (U.S. Code p. 137) takes a qualifying child into account only with the child's TIN on the return.

**What the software does.** Such a child is left out of the EIC count and appears on no printed row. The return
files: the credit is figured on the counted children, or on the self-only amount when no child is counted. The
refusal stays only when such a child is not an EIC qualifying child at all, or when the child would be the head
of household qualifying person.

**Why we chose it.** Nothing in the instructions refuses the return; they list a child only when the child has
an SSN, the document, or the filer claims the self-only credit. The earlier refusal rested on a row the return
does not have. The owner's standing rule is to follow the sources where they settle a case.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Whether such a child should still be listed on Schedule EIC with a
blank line 2 when a sibling is counted.

**Where it lives.** `familyAndHousehold:/knockoutPersonBornAndDiedInTaxYearWithoutTin`.

### CR-11 — Education credits: a 2024 Form 1098-T with box 7 checked, and no 2025 statement

**The question.** Form 8863 line 22 asks, for each institution, whether the student received a Form 1098-T
for 2025 and whether the student received one for 2024 with box 7 checked. A student may answer No to the
first and Yes to the second. Does that student meet the Form 1098-T requirement for 2025?

**The IRS text.** IRC 25A(g)(8) (U.S. Code p. 97): "Except as otherwise provided by the Secretary, no credit
shall be allowed under this section unless the taxpayer receives a statement furnished under section 6050S(d)
which contains all of the information required by paragraph (2) thereof." Form 8863 (2025), page 2, line 22,
asks "(3) Did the student receive Form 1098-T from this institution for 2024 with box 7 checked?", and line
22(4) asks for the institution's EIN if the filer checked Yes in (2) or (3). The instructions (page 4) add:
"You cannot use any amount you paid in 2024 or 2026 to figure the qualified education expenses you use to
figure your 2025 education credit(s)."

**What the software does.** A Yes on line 22(3) meets the statement requirement for that institution, as a
Yes on line 22(2) does. The expenses entered must still be amounts paid in 2025.

**Why we chose it.** The statute asks for a statement furnished under section 6050S(d) and does not say it
must be for the year of the credit. A 2024 statement with box 7 checked reports amounts for an academic period
that begins in the first three months of 2025. The form asks (3) beside (2) and treats them alike for the EIN.
The instructions do not say what a Yes on (3) alone means. Reading it as a failed requirement would deny the
credit to a student the form itself seems to cover, so we follow the statute's plain words.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Whether IRS guidance treats a prior-year box 7 statement as meeting
the requirement only for amounts it reports (paid in 2024, so not usable in 2025), in which case a student with
2025 payments and no 2025 statement would not qualify.

**Where it lives.** `form8863: /aotcFirstInstitutionPayeeStatementMet`, `form8863: /llcPayeeStatementMet`.

### CR-12 — Adoption credit: a carryforward a separate return cannot use this year

**The question.** A married person filing separately may use a prior-year adoption credit carryforward only if,
for the year the credit first became allowable, the person was unmarried or filed a joint return. A lot that
fails that test cannot be used on the 2025 separate return. Does it still carry to 2026, or is it lost?

**The IRS text.** IRC 23(c)(1) (U.S. Code, section 23(c), web edition): an unused credit "shall be carried to the succeeding taxable
year and added to the credit allowable under subsection (a) for such taxable year", and 23(c)(2) ends a
carryforward only "following the fifth taxable year after the taxable year in which the credit arose". The
Form 8839 instructions (2025), page 2, allow the separate filer the carryforward "provided that, if the person
was married in the year in which the qualified adoption expenses first became allowable for the credit, the
person filed a joint return for that year". The carryforward worksheet (page 8) enters every prior lot on
lines 2 through 6 and has no separate-return branch.

**What the software does.** The lot is not used on the 2025 return and is carried to 2026 in the total
carryforward, until the five-year limit ends it. A separate return that cannot use any of its carryforward
carries every lot except the 2020 one, which expires.

**Why we chose it.** The statute carries an unused credit forward and ends it only by the five-year limit; no
text says a lot barred for one year is forfeited. The printed worksheet reaches the same total, since it
starts from all the prior lots, not from the amount on line 15.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Whether the worksheet's oldest-first spending should skip a lot
that could not be used this year when it decides which lot expires first.

**Where it lives.** `form8839: /form8839CreditCarryforwardTo2026`.

### OT-03 — Net investment income tax: citizen married to a nonresident alien

**The question.** A U.S. citizen married to a nonresident alien may elect to file a joint income tax return. If
they do not also elect joint treatment for the net investment income tax, how is that tax figured?

**The IRS text.** 26 CFR 1.1411-2(a)(2)(iii)(A) (p. 63), "Default treatment": "In the case of a United States
citizen or resident who is married to a nonresident alien individual, the spouses will be treated as married
filing separately for purposes of section 1411. For purposes of calculating the tax imposed under section
1411(a)(1), the United States citizen or resident spouse will be subject to the threshold amount for a married taxpayer filing
a separate return in paragraph (d)(1)(ii) of this section, and the nonresident alien spouse will not be subject
to tax under section 1411. In accordance with the rules for married individuals filing separate returns, the
spouse that is a United States citizen or resident must determine his or her own net investment income and
modified adjusted gross income." The same paragraph continues: "(B) Taxpayer election.
Married taxpayers who file a joint Federal income tax return pursuant to a section 6013(g) election for purposes
of chapter 1 and chapter 24 also may elect to be treated as making a section 6013(g) election for purposes of
chapter 2A". Instructions for Form 8960 (2025), page 23: "If you’re a U.S. citizen or resident married to an
NRA, your filing status is married filing separately unless you made an election under section 6013(g) or
6013(h) to file jointly with your NRA spouse."

**What the software does (partly built).** A citizen who files as head of household while married to a
nonresident alien gets the $125,000 threshold. On a joint return without the NIIT election, the threshold is
$125,000 and the citizen's own investment income is used; the citizen's own modified adjusted gross income is
being built from per-spouse amounts, and is left incomplete where an item cannot be split between spouses.

**Why the owner chose it.** The owner's words: "do what is right for the law even if more complicated."

**Our best recommendation.** Keep it; the regulation is explicit.

**What we would like a reviewer to check.** How many Forms 8960 you attach to such a joint return, and how the
separately figured tax reaches the joint Form 1040; we found no IRS text that says.

**Where it lives.** `form8960:/niitThreshold`, `form8960:/niitPrimaryFilerSeparateNiiForNraSpouseElection`.

### OT-01 — Alternative minimum tax: incentive stock options and the Part III refigure

**The question.** Stock acquired by exercising an incentive stock option has a different basis for the AMT.
When it is sold, and when the AMT capital gain figures differ from the regular ones, Form 6251 Part III must be
refigured. The software does not yet do this.

**The IRS text.** Instructions for Form 6251 (2025), page 4: "Increase your AMT basis in any stock acquired
through the exercise of an ISO by the amount of the adjustment."

**What the software does.** It refuses a return that is exposed to the AMT and shows evidence the refigure
matters (a line 2k disposition adjustment, a different AMT capital gain figure, or an estate or trust K-1 AMT
capital gain adjustment). An exercise with the stock still held does not trigger it.

**Why the owner chose it.** A knockout for this release (GEN-02).

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `form6251:/knockoutAmtPart3RefigureUnbuilt`.

### OT-02 — Alternative minimum tax: which rental and business returns are refused

**The question.** The software does not compute AMT depreciation adjustments. Must every return with rental or
business income in the AMT range be refused?

**The IRS text.** Instructions for Form 6251 (2025), page 5, "What Depreciation Isn’t Refigured for the AMT?":
"Don’t refigure depreciation for the AMT for the following." The first item is "Residential rental property
placed in service after 1998."

**What the software does.** It refuses only a return that carries an accelerated-depreciation intake (or an
unexplained depreciation override) and is in the AMT range. Straight-line residential rental buildings compute.

**Why the owner chose it.** The earlier blanket refusal turned away many returns that have no AMT adjustment at
all.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `form6251:/knockoutAmtUnmodeledPreference`.

### OT-04 — Mortgage subsidy recapture (Form 8828)

**The question.** (1) When Form 8828 is started but the questions that decide whether the recapture applies are
unanswered, is the recapture $0 or unknown? (2) Are the holding-period month counts the filer's statement or
derived from the dates?

**What the software does.** (1) Unknown: the Schedule 2 total waits for the answers, and the printed Schedule
2 box shows only a recapture actually owed. (2) The month counts are derived from the loan closing, repayment
and sale dates.

**Why the owner chose it.** An unanswered question should not become a silent $0 (GEN-01); dates the filer has
already entered are more reliable than a separate count.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `form8828:/form8828SubjectToRecaptureTax`, `form8828:/form8828Line23RecaptureTax`,
`schedule2:/schedule2Line17bMortgageSubsidyRecaptureTax`, `schedule2:/schedule2Line17bMortgageSubsidyRecaptureTaxPrinted`.

### OT-05 — Form 8915-F line 32 on Form 5329: before or after the exceptions

**The question.** A filer who did not repay a qualified distribution for the purchase or construction of a main
home in a disaster area carries the unrepaid amount on Form 8915-F line 32, and enters on this return how much of
it is subject to the additional tax on early distributions. Is that entry the amount before the Form 5329
exceptions (so the exceptions are still taken on line 2), or already after them?

**The IRS text.** Instructions for Form 8915-F (Rev. 12-2025), page 26, Lines 27 Through 32: "Most distributions
from qualified retirement plans (including IRAs) made to you before you reach age 59 1/2 are subject to an
additional tax on early distributions and are reported on Form 5329", and the unrepaid qualified distributions
"may be subject to this additional tax unless you qualify for an exception. See the Instructions for Form 5329 for
information on exceptions to this tax." Instructions for Form 5329 (2025), page 5, Line 2: "The additional tax on
early distributions doesn't apply to the distributions described next. Enter on line 2 the amount that you can
exclude." IRC 72(t)(2)(A)(i): the tax does not apply to a distribution "made on or after the date on which the
employee attains age 59 1/2".

**What the software does.** Reads the entry as before the exceptions: it goes on Form 5329 line 1 of the filer
whose Form 8915-F it is, and the exceptions go on line 2. The question asks for the part received before age
59 1/2, and for an owner who was 59 1/2 on every day of 2025 the whole entry is also placed on line 2 (exception
12, derived from the date of birth), so it is not taxed. This follows the project owner's direction of 2026-09-27 to
settle what the sources decide; the sources decide it.

**Why.** The Form 8915-F instruction sends the line 32 amount to Form 5329 "unless you qualify for an exception"
and points to the Form 5329 instructions for the exceptions, which are claimed on line 2. Reading the entry as
already net would let an exception be missed with nothing to catch it; reading it as gross lets the return apply
the exceptions it can derive.

**Our best recommendation.** Keep. The other exceptions (for example disability, or an IRA first home up to
$10,000) are not derived for this amount; the primary filer can still claim them on the typed line 2 entry when
no Form 1099-R is on the return.

**What we would like a reviewer to check.** That exception 12's printed wording (distributions coded 1, J or S on
a Form 1099-R) is an acceptable place to carry the age 59 1/2 exception for an amount that arrives through Form
8915-F rather than a Form 1099-R.

**Where it lives.** `form5329:/writableForm5329Line1Form8915FLine32AdditionalTaxAmount`,
`form5329:/form5329PrimaryFilerForm8915FLine32Amount`, `form5329:/form5329SecondaryFilerForm8915FLine32Amount`,
`form5329:/form5329PrimaryFilerDerivedException12Amount`, `form5329:/form5329SecondaryFilerDerivedException12Amount`.

### OT-06 — Mortgage subsidy recapture: a transfer to a spouse that is not incident to divorce

**The question.** A home financed with a qualified mortgage bond or a mortgage credit certificate is
transferred to the owner's spouse (not incident to a divorce), with no gain or loss recognized. Is recapture
tax owed on the transfer?

**The IRS text.** IRC 143(m)(8)(C), as in the vendored U.S. Code: "Paragraph (1) shall not apply to any
transfer on which no gain or loss is recognized under section 1041. In any such case, the transferee shall be
treated under this subsection in the same manner as the transferor would have been treated had such transfer
not occurred." The Form 8828 instructions (Rev. November 2024, page 1) say under Divorce that the transfer "does
not result in recapture tax to either person" if "It is incident to divorce", and speak of no other transfer
between spouses.

**What the software does.** Any transfer to a spouse, or to a former spouse incident to divorce, on which
section 1041 recognizes no gain or loss, owes no recapture tax. The spouse who receives the home stands in the
transferor's place for a later sale.

**Why we chose it.** Section 1041 covers every transfer between spouses, not only transfers incident to
divorce, and the statute bars recapture on any such transfer. The instructions describe the common case but
do not narrow the statute. The owner's standing rule is to follow the statute when it is clear.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `form8828: /writableForm8828TransferToSpouseWithNoGainOrLossRecognizedUnderSection1041`,
`form8828: /form8828SubjectToRecaptureTax`.

### OT-07 — Form 8938: the any-time reporting threshold for a part-year specified individual

**The question.** Form 8938's dollar thresholds test the aggregate value of specified foreign
financial assets "at any time during the taxable year." A filer can be a "specified individual"
(for example, a resident alien) for only part of the year. Is the any-time test measured over the
whole tax year, or only the part of it during which the filer was a specified individual?

**The IRS text.** Treas. Reg. 1.6038D-2(a)(9) (vendored at
`26 CFR 1.6038D-2, https://www.ecfr.gov/current/title-26/section-1.6038D-2` line 43): "The reporting period covered by Form 8938
is the specified person's taxable year, except the reporting period for a specified person that is
a specified individual for less than an entire taxable year is the portion of the taxable year that
the specified person is a specified individual."

**What the software does.** The any-time aggregate (`/form8938ComputedMaximumValue`, feeding
`/form8938EffectiveMaximumValue`) still sums each row's whole-year maximum. The regulation is
decided in the filer's favor for a part-year specified individual, but the module holds no fact for
when specified-individual status began or ended, so the part-year window cannot be computed. The
whole-year sum is an upper bound on the true part-year peak (already disclosed by the
`ANYTIMEAGG-001` fix), so the direction is over-refusal only: some part-year filers are asked to
complete Form 8938 when a correctly-scoped computation would not require it. No filer is under-asked.

**Why the call was made.** The regulation is clear and vendored, so the reading is decided rather
than left open. Building the part-year computation itself needs a new intake (the specified-individual
period) that does not exist in this module; adding a fact for one reading without the data to compute
it would not close the gap, so the call is to disclose the direction and name the successor rather
than build a partial answer.

**Our best recommendation.** Keep the whole-year aggregate (it is conservative, never under-taxing)
until a specified-individual period intake is built; then re-scope the any-time aggregate to it.

**What we would like a reviewer to check.** Whether a part-year specified-individual intake belongs
in this module or in the residency/filing-status modules that already ask about part-year presence.

**Where it lives.** `form8938: /form8938ComputedMaximumValue`, `/form8938EffectiveMaximumValue`,
`/form8938AboveReportingThreshold`.

### OT-08 — Form 8912: where a pre-October-2008 QZAB credit sits in the bond-credit limitation order

**The question.** Form 8912 combines the credit to holders of clean renewable energy bonds (CREB,
IRC 54), qualified tax credit bonds (IRC 54A) and build America bonds (BAB, IRC 54AA) on one line.
Each section's own tax-liability limitation excludes a different set of the others' credits before
computing its own limit. A pre-October-4-2008 qualified zone academy bond (QZAB) credit, governed by
the now-repealed IRC 1397E, is also part of the mix. Where does it sit in the limitation order?

**The IRS text.** IRC 1397E(k) (vendored at `26 U.S.C. 1397E, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2016-title26-section1397E&num=0&edition=2016` line 111): "the credit
allowed by this section shall be treated as a credit allowable under subpart H of part IV of
subchapter A of this chapter." IRC 1397E(c)(2) (line 28) excludes "subpart C thereof, relating to
refundable credits, and subparts H, I, and J thereof" from its own limitation reduction — H, I and J
being itself, IRC 54A and IRC 54AA. IRC 54(c)(2) (`26 U.S.C. 54, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2016-title26-section54&num=0&edition=2016` line 59) excludes
only "subparts C, I, and J, section 1400N(l), and this section" — not subpart H. IRC 54A(c)(1)(B)
excludes only subparts C and J and its own subpart. IRC 54AA(c)(1)(B) excludes only subpart C and
its own subpart.

**What the software does.** With more than one bond, Form 8912 line 12 is split between the bond
kinds in this order (`/form8912LimitationOrderOldQzabAllowed`, then `...CrebAllowed`,
`...QualifiedTaxCreditBondAllowed`, `...BabAllowed`), each kind taking the smaller of its credit and
what line 12 leaves; `/form8912Bonds/*/allowedCreditAllocation` gives a bond of a wholly allowed kind
its own credit, the only bond of the partly allowed kind that kind's share, and uses the filer's
`allocatedAllowedCredit` only to split the partly allowed kind among two or more bonds of that kind,
which the statute does not order. The total allowed credit is unchanged; the split between a
deductible unused CREB or old-QZAB credit and a carried-forward qualified tax credit bond or BAB
credit now follows the statute.

**Why the call was made.** The statute is clear and vendored (1397E was repealed but its pre-repeal
text governs the pre-October-2008 QZAB population Form 8912 still serves, the same posture as the
already-vendored 2016-edition sections 54, 54A and 54AA). Old-QZAB (1397E) excludes every other
subpart from reducing its own limit, so it is computed first, ignoring the rest; CREB's own limit
(54) is then reduced by the old-QZAB credit already used (54 does not exclude subpart H); 54A's
limit is reduced by both; 54AA's limit last. Order: old-QZAB, then CREB, then qualified tax credit
bonds, then BAB.

**Our best recommendation.** Keep the order as built. The split among bonds of one kind stays a
filer answer, because each section orders itself against the other sections, not against bonds of
its own kind.

**What we would like a reviewer to check.** Whether any committed or synthetic multi-bond-type
scenario would actually move the deduction/carryforward split under this order, to prioritize the
successor build.

**Where it lives.** `form8912: /form8912Bonds/*/allowedCreditAllocation`,
`/form8912LimitationOrderOldQzabAllowed` (and the Creb, QualifiedTaxCreditBond and Bab siblings),
`/form8912Bonds/*/allocatedAllowedCredit`, `/form8912AllocatedCreditTotal`.

### OT-09 — Form 965-A: an increase due to negligence, disregard or fraud is not spread over the installments

**The question.** A filer who elected to pay a net 965 tax liability in eight installments has the liability
increased in 2025, for example by an audit. The instructions spread such an increase over all the
installments, with the part belonging to installments already due paid now. Does that apply to every
increase, and what does the return assume when the filer says nothing about how the increase arose?

**The IRS text.** IRC 965(h)(4): "the deficiency shall be prorated to the installments payable under
paragraph (1)" and "The part of the deficiency so prorated to any installment the date for payment of which
has arrived shall be paid upon notice and demand from the Secretary. This subsection shall not apply if the
deficiency is due to negligence, to intentional disregard of rules and regulations, or to fraud with intent
to evade tax." Instructions for Form 965-A (Rev. January 2021), page 3: "An adjustment of a net 965 tax
liability elected to be paid in installments is generally prorated to all installments", with an example
that states "there was no negligence, intentional disregard, or fraud on the part of TP".

**What the software does.** A question on each Part I row with a 2025 increase: is the increase a
deficiency due to negligence, intentional disregard of rules and regulations, or fraud? When the answer is
yes, the whole increase is payable in 2025: the part the normal 2025 installment already carries plus the
rest. When the answer is no or not given, the increase is prorated as the instructions' example shows.

**Why the call was made.** The statute is clear that the proration does not apply to a culpable
deficiency, so the return builds the exception rather than refusing it. The culpability itself is a fact
the filer knows (it comes from the examination that produced the increase) and the return cannot derive,
so it is asked. An unanswered question takes the general rule because the instructions call proration
the general case and give no default the other way.

**Our best recommendation.** Keep. Later years' installments on such a row are figured on later returns and
are not refigured here.

**What we would like a reviewer to check.** Whether a culpable increase should be reported in Part I
column (j) at all, or kept off the installment record entirely once it is paid on notice and demand.

**Where it lives.** `form965A: /form965ALiabilities/*/writableCurrentYearAdjustmentDueToNegligenceOrFraud`,
`/form965ALiabilities/*/currentYearAdjustmentNotProrated`, `/form965ALiabilities/*/catchUpDue`.

### OT-10 — Form 6251: Who Must File statement 4, line 7 without lines 2c through 3

**The question.** The fourth reason to attach Form 6251 needs line 7 figured a second time, without lines
2c through 3. Line 7 on a return with capital gains or qualified dividends comes from Part III. How is the
second line 7 figured?

**The IRS text.** Instructions for Form 6251 (2025), page 1, Who Must File: "Attach Form 6251 to your return
if any of the following statements are true." Statement 4: "The total of Form 6251, lines 2c through 3, is
negative and line 7 would be greater than line 10 if you" did not take into account lines 2c through 3.

**What the software does.** It refigures line 4 without lines 2c through 3 (including the married filing
separately addition), the line 5 exemption on that amount, line 6, and line 7 at the 26 and 28 percent rates.
When the lines 2c through 3 total is negative and that line 7 is greater than line 10, Form 6251 is attached.

**Why the call was made.** Part III can only make line 7 smaller than the 26 and 28 percent figure, so the
flat-rate line 7 is an upper bound. Reading statement 4 with it never misses a return the statement reaches.
On a return that completes Part III it can attach Form 6251 where the statement would not require it; an
attached Form 6251 changes no amount on the return. A second Part III run on the refigured line 6 would make
the test exact and is not built.

**Our best recommendation.** Keep; build the refigured Part III only if over-attachment is a problem in
practice.

**What we would like a reviewer to check.** Whether attaching Form 6251 when it is not required has any
consequence for an e-filed return.

**Where it lives.** `form6251: /amtWhoMustFileStatement4`, `/amtStatement4Line7FlatRateWithoutLines2cThrough3`,
`/requiresForm6251`.

### IN-150 — Schedule H: qualified parking and commuter reimbursements leave the household employee's wages

**The question.** A household employer who reimburses an employee in cash for qualified parking, for a
commuter highway vehicle or for transit passes: do those reimbursements count as cash wages for the $2,800
test and for Schedule H lines 1, 3 and 5, and for line 15 (FUTA)?

**The statute and instructions.** Instructions for Schedule H (2025), page 5, "Transportation (commuting)
benefits": "If you reimburse your employee for qualified parking, transportation in a commuter highway
vehicle, or transit passes, you may be able to exclude the cash reimbursement amounts from counting as cash
wages subject to social security and Medicare taxes." The same passage: "For 2025, you can reimburse your
employee up to $325 per month for qualified parking and $325 per month for combined commuter highway vehicle
transportation and transit passes" and "Any cash reimbursement over these amounts is included as wages."
IRC 3121(a)(20) and IRC 3306(b)(16) each exclude from wages "any benefit provided to or on behalf of an
employee if at the time such benefit is provided it is reasonable to believe that the employee will be able
to exclude such benefit from income under section 74(c), 108(f)(4), 117, or 132". Both texts were checked
against the current U.S. Code (prelim, 2026-09-29): unamended since the 2024 edition.

**What the software does.** Each household employee row takes two amounts: parking reimbursements and
commuter-vehicle/transit reimbursements, both already inside the cash wages entered. Each is capped at
twelve months of $325 ($3,900) and the two are subtracted from the cash wages before the $2,800 test and
before lines 1, 3, 5 and 15. Reimbursements larger than the cash wages entered refuse the return.

**Why we chose it.** The FUTA exclusion is in the statute even though the Schedule H passage names only
social security and Medicare, and the statute is clear. The instruction removes the reimbursements "from
counting as cash wages", which is the figure the $2,800 test reads, so the test runs on the net amount. The
return does not ask month by month, so the annual ceiling is the monthly limit times twelve; the filer is
told to count at most $325 for each month.

**Our best recommendation.** Keep. Confidence medium: a filer who exceeded $325 in some months but not
others and entered the whole year's reimbursement would understate the tax, up to the ceiling.

**What we would like a reviewer to check.** Whether practitioners run the $2,800 test before or after the
excluded reimbursements, and whether a monthly entry is worth asking.

**Where it lives.** `scheduleH:/householdEmployees/*/writableQualifiedParkingReimbursement`,
`scheduleH:/householdEmployees/*/writableCommuterTransitReimbursement`,
`scheduleH:/householdEmployees/*/transportationReimbursementExclusion`,
`scheduleH:/householdEmployees/*/cashWagesSubjectToEmploymentTaxes`.

### IN-151 — Schedule H: F, J, M or Q nonimmigrant household employees and totalization agreements

**The question.** The printed Schedule H exclusion lists name only relatives and employees under 18. Is an
au pair on a J-1 visa, or an employee whose wages a totalization agreement leaves to a foreign social
security system, reported on Schedule H?

**The statute.** IRC 3121(b)(19) excludes from employment "Service which is performed by a nonresident alien
individual for the period he is temporarily present in the United States as a nonimmigrant under
subparagraph (F), (J), (M), or (Q) of section 101(a)(15) of the Immigration and Nationality Act, as amended,
and which is performed to carry out the purpose specified in subparagraph (F), (J), (M), or (Q), as the case
may be"; IRC 3306(c)(19) carries the same exclusion for FUTA. IRC 3101(c) and IRC 3111(c): "wages received by
or paid to an individual shall be exempt from the taxes imposed by this section to the extent that such
wages are subject under such agreement exclusively to the laws applicable to the social security system of
such foreign country". IRC 3306 has no totalization provision. Checked against the current U.S. Code
(prelim, 2026-09-29): unamended.

**What the software does.** Each employee row asks both questions. F/J/M/Q visa-purpose service is off lines
1, 3, 5 and 15 and does not count toward the $2,800 test; totalization-covered wages are off lines 1, 3 and 5
but stay on line 15. A line A Yes resting only on such an employee is refused.

**Why we chose it.** The statute is clear and is followed over the narrower printed lists (standing owner
rule).

**Our best recommendation.** Keep. Confidence high.

**What we would like a reviewer to check.** Nothing specific.

**Where it lives.** `scheduleH:/householdEmployees/*/writableIsNonresidentAlienVisaPurposeService`,
`scheduleH:/householdEmployees/*/writableIsCoveredByTotalizationAgreement`,
`scheduleH:/householdEmployees/*/isExcludedFromSocialSecurityAndMedicareWages`,
`scheduleH:/householdEmployees/*/isExcludedFromFutaWages`.

### IN-152 — Schedule H: household employees reported on a business return or by an agent

**The question.** A filer who reports a household employee's taxes on the Form 941, 943 or 944 of their
business, or whose employee's taxes a section 3504 agent or a government agency reports and pays: does
Schedule H still carry that employee?

**The instructions.** Instructions for Schedule H (2025), page 10, "Rules for Business Employers": "Don't use
Schedule H if you chose to report employment taxes for your household employees along with your other
employees on Form 941 or 941 (sp), Employer's QUARTERLY Federal Tax Return; Form 943, Employer's Annual
Federal Tax Return for Agricultural Employees; or Form 944, Employer's ANNUAL Federal Tax Return." Page 2:
"If a government agency or third-party agent reports and pays the employment taxes on wages paid to your
household employee on your behalf, you don't need to file Schedule H to report those taxes."

**What the software does.** Each employee row asks whether the taxes are reported that way; a Yes takes the
employee off lines 1, 3, 5 and 15. Withheld income tax on such an employee is left out of line 7.

**Why we chose it.** The agent rule is written per employee; the business-return rule covers every
household employee the filer reports that way, which a per-employee answer also covers. Keeping the row
lets a filer who has both kinds of employee file correctly.

**Our best recommendation.** Keep. Confidence high.

**What we would like a reviewer to check.** Nothing specific.

**Where it lives.** `scheduleH:/householdEmployees/*/writableTaxesReportedOnBusinessReturnOrByAgent`,
`scheduleH:/householdEmployees/*/taxesReportedOnBusinessReturnOrByAgent`.

## Payments and penalties

### IN-250 — Schedule H: a joint return with two household employers files two schedules

**The question.** On a joint return where both spouses employ household workers, does the return attach one
combined Schedule H or one per spouse, and what does each spouse's schedule print on the lines the return
answers only once (lines A, B, C and 9, line 27)?

**The instructions.** Instructions for Schedule H (2025), page 4, "Name of employer": "Only two Schedules H
can be attached to Form 1040, 1040-SR, and 1040-SS, one Schedule H for each of the primary taxpayer and the
secondary taxpayer." Schedule H (2025) line 27: "Yes. Stop. Include the amount from line 26 above on Schedule
2 (Form 1040), line 9." Schedule 2 (2025) line 9: "Household employment taxes. Attach Schedule H".

**What the software does.** Each spouse who has a household employee, a line 17 state row or a Schedule H
answer of their own gets a printed Schedule H with their own name and SSN; when nothing is attributed to
either spouse, one schedule prints for the primary taxpayer. Each schedule carries that spouse's lines 1-8,
lines 10-24 and line 17 rows, and its own line 25 and line 26. Line 7 (income tax withheld), the state
disability subtraction on line 8, and lines 13 and 14 are asked of each spouse for their own schedule.
Line A prints Yes on a spouse's schedule when the return answered Yes and that spouse paid an employee on
line A's list $2,800 or more. Line B prints Yes on a schedule whose line A is No when that spouse's own
line 7 is more than zero, or, with only one employer on the return, when the return answered line B Yes.
Lines C and 9 print the return's one answer to the $1,000-a-quarter question, which is how the return
decides whether Part II applies; line 27 and Part IV print the return's one answer on both schedules.
Schedule 2 line 9 is unchanged: the two schedules' line 26 amounts add to it.

**Why we chose it.** The instruction is clear that each spouse files their own schedule. Lines A and B ask
about "any" employee and "any" withholding of the person filing the schedule, and the employee list and
each spouse's own line 7 say which spouse that is. The $1,000 quarter test is asked of the return once
today, and Part II already reads that single answer, so printing it on both schedules keeps the printed
routing consistent with the tax computed.

**Our best recommendation.** Keep. Confidence high for two schedules; medium for line B, because the return
records withholding per schedule only through each spouse's line 7 amount.

**What we would like a reviewer to check.** Whether the $1,000 quarter test should be asked per spouse (each
spouse is a separate employer), and whether a spouse whose only entry is a line 7 answer of zero should
still print a schedule.

**Where it lives.** `scheduleH:/filersFilingScheduleH`, `scheduleH:/filers/*/scheduleHFilesOwnSchedule`,
`scheduleH:/filers/*/scheduleHLineA`, `scheduleH:/filers/*/scheduleHLineB`,
`scheduleH:/filers/*/scheduleHLine26`, `scheduleH:/filers/*/writableScheduleHLine7FederalIncomeTaxWithheld`.

### IN-251 — Schedule H line 17: more states than the form has rows

**The question.** Schedule H line 17 prints two state rows. Where do a third and later state go?

**The instructions.** Instructions for Schedule H (2025), page 6, Line 17: "If you need more space, attach a
statement using the same format as line 17."

**What the software does.** The first two of a spouse's states print on that spouse's line 17. Every further
state prints on a statement attached after that Schedule H: it names the form and line, the spouse's name and
SSN, repeats the line 17 column headings (a) through (h), and lists each further state as rows 3, 4 and so
on. Line 18 on the form already totals every row, the attached ones included.

**Why we chose it.** The instruction asks for exactly this, and the totals the form carries forward already
count every state.

**Our best recommendation.** Keep. Confidence high.

**Where it lives.** `scheduleH:/filers/*/scheduleHFutaStateContributions`.

### PP-01 — Combat zone or contingency operation service and the estimated tax penalty

**The question.** For people serving in a combat zone or a qualifying contingency operation (and their
spouses), the time to pay tax, including estimated tax installments, is postponed. The software does not yet
compute the postponed dates. What should it do?

**The statute and instructions.** IRC 7508(a) (our copy is the Office of the Law Revision Counsel's
online text of the 2024 edition, without printed pages): "the period of service in such area or operation,
plus the period of continuous qualified hospitalization attributable to such injury, and the next 180 days
thereafter, shall be disregarded in determining" whether acts were timely, including "(B) Payment of any
income, estate, gift, employment, or excise tax or any installment thereof". Instructions for Form 2210 (2025),
page 1, "The IRS Will Figure the Penalty for You": "If you want us to figure the penalty for you, complete your
return as usual. Leave the penalty line on your return blank; don’t file Form 2210."

**What the software does.** When the return shows combat-zone service (the combat zone notation, or combat pay
on a Form W-2) and the filer checks no Form 2210 Part II box (or only box A or box E, which need only page 1),
the penalty line is left blank and the IRS figures the penalty with the postponement; Form 2210 is not filed.
Only a filer who must file Form 2210 with a penalty on it (box B, C or D, or a Form 2210-F with a penalty) is
still refused.

**Why the owner chose it.** The first call was a refusal (the owner's words: "ok, another knockout for combat
zone"), because computing the penalty on the unpostponed dates would overcharge. After review the owner chose
the blank penalty line.

**Our best recommendation — differs.** Do not refuse; leave the penalty line blank for this population and let
the IRS figure it, exactly as the Form 2210 instructions allow any filer to do. The filer is served, and no
wrong penalty is filed. Refusal turns away service members for an amount the IRS offers to compute itself. The
one exception is a filer who must file Form 2210 (for example, to claim a waiver or the annualized method);
that smaller group could still be refused. Our confidence is medium, because leaving the line blank means the
filer may get a bill if the IRS does not apply the postponement.

**The owner's decision after review (2026-09-25).** The owner decided to follow our recommendation. It is
built: "What the software does" above describes the software as it is now.

**What we would like a reviewer to check.** Whether leaving the penalty blank for combat-zone filers is how
you handle it in practice.

**Where it lives.** `form1040:/knockoutForm2210CombatZoneMustFilePostponementNotModeled`,
`form2210:/form2210CombatZoneServiceShown`, `form2210:/form2210CombatZoneIrsFiguresPenalty`,
`form1040:/writableForm1040CombatZoneNotation`, `formW2s:/allCombatPay`, `form2210:/form2210Penalty`,
`form2210:/form2210FLine16Penalty`.

### PP-02 — Form 1042-S: which box is the withholding credit (box 10, not box 11)

**The question.** A filer of Form 1040 can receive Form 1042-S (for example, a resident alien paid as a
nonresident earlier in the year). Box 10 is the total withholding credit; box 11 is tax the withholding agent
paid from its own funds. Which amount is credited on Form 1040 line 25c, and what happens when boxes 7b, 7c or 11
are used?

**The statute and instructions.** IRC 1462 (our copy is the Office of the Law Revision Counsel's online text of
the 2024 edition, without printed pages): "any amount of tax so withheld shall be credited against the amount of
income tax as computed in such return." Instructions for Form 1042-S (2025), page 29, Box 11: "Enter the total
amount of tax paid by you and not withheld from the payment to the recipient. The amounts reported in box 11
should be the amounts paid by the withholding agent from its own funds rather than through withholding from the
payment to the recipient. Any amount reported in this box must not be included in box 10." Publication 519
(2025), page 43, the table of where each document shows the tax withheld: "1042-S . . . Box 10".

**What the software does.** It credits box 10 on line 25c. It refuses a return with box 7b checked (tax not
deposited, escrow procedures), box 7c checked (withholding in a later year on a partnership interest), or an
amount in box 11, because the rule for each of those is not yet built. The income a Form 1042-S reports is not
yet placed on any Form 1040 line either, so any entered Form 1042-S is currently refused on that ground as well.

**Why the owner chose it.** Box 10 is the amount the form and Publication 519 name as the credit; the rest is a
refusal instead of a guess (GEN-02).

**Our best recommendation.** Box 11 is never part of the line 25c credit: it was not withheld from the
recipient's payment, so it is not tax "so withheld" under section 1462, and the instructions keep it out of
box 10. Whether the agent's payment is additional income to the recipient is a separate question we have not
settled, so keep the refusal for box 11 until it is. Our confidence is medium.

**What we would like a reviewer to check.** Whether tax a withholding agent pays from its own funds (box 11) is
income to the recipient, and whether a box 7b or 7c amount changes the year or the amount of the box 10 credit.

**Where it lives.** `form1042S:/form1042Ss/*/withholdingCreditOnThisReturn`, `form1042S:/form1042SWithholding`,
`form1042S:/form1042Ss/*/writableTaxPaidByWithholdingAgent`, `form1042S:/knockoutForm1042SWithholdingCreditUnbuilt`,
`taxCalculations:/otherFormWithholding`.

### IN-100 — Form 2210 Schedule AI: the Form 4972, Form 8814 and alternative minimum taxes of each period

**The question.** A filer who uses the annualized income installment method (Form 2210 box C, Schedule AI)
may also owe tax on a lump-sum distribution (Form 4972), tax on a child's interest and dividends reported on
the parent's return (Form 8814), or alternative minimum tax. Where do those taxes go on Schedule AI, how is
each period's amount figured, and does owing one of them stop the schedule from being computed?

**The statute and instructions.** Instructions for Form 2210 (2025), page 10, "Line 16": "Enter all of the
other taxes you owed because of events that occurred during the months shown in the column headings. Include
the same taxes used to figure Form 2210, Part I, line 2 (except self-employment tax), plus the tax from Form
4972, Tax on Lump-Sum Distributions; Form 8814, Parents’ Election To Report Child’s Interest and Dividends; and
any alternative minimum tax (AMT)." The same page: "To figure the AMT, Form 1040 or 1040-SR filers use Form
6251; estates and trusts use Schedule I (Form 1041). Figure alternative minimum taxable income based on your
income and deductions during the periods shown in the column headings. Multiply this amount by the
annualization amounts shown for each column on Schedule AI, line 2, before subtracting the AMT exemption."
Line 14 of the schedule is "Figure your tax on the amount on line 13" (Form 2210 (2025), page 3).
Publication 505 (2025), page 26, describing its own annualized worksheet, is looser: "Add the tax from Forms
8814, 4972, and 6251 for the period" and then "Figure the tax based on your income and deductions during the
period shown in the column headings. Multiply this amount by the annualization amounts".

**What the software does.** All three taxes go on line 16, never on line 14: line 14 is the tax on line 13 by
the Tax Table or a tax worksheet, which none of the three is. Owing one of them no longer stops line 14 from
being figured, so the return is computed rather than turned away. The filer enters line 16 for each period.
For the alternative minimum tax the filer follows the Form 2210 instruction (period income, annualized before
the exemption). The Form 4972 and Form 8814 taxes are entered in the period in which the distribution or the
child's income occurred, and carried into each later period because the periods are cumulative. The software
checks that the full-year column equals the annual amounts, now including the Form 4972 and Form 8814 taxes,
and refuses the return when it does not.

**Why we chose it.** The Form 2210 instructions govern Form 2210 and are specific: they annualize only the
alternative minimum taxable income and describe the other two as taxes "because of events" in the months of
the column. Publication 505's worksheet paraphrase reads as if all three were annualized, but it describes a
different worksheet and its "this amount" follows a sentence about income, matching the Form 2210 text for
the alternative minimum tax. Line 16 is already an entry the filer makes for each period (the Net Investment
Income Tax and the Additional Medicare Tax are figured the same way), so the software treats these three taxes
exactly like the others on that line.

**Our best recommendation.** Keep. The earlier behaviour refused every such return and pushed the filer to the
regular method, which is never lower. Our confidence is medium: the software does not refigure the alternative
minimum tax for each period itself, so an understated early-period figure would lower the penalty, the same
exposure the other line 16 taxes carry; the full-year check and the rule that each period includes the
previous ones are the only guards.

**What we would like a reviewer to check.** Whether practitioners enter the Form 8814 and Form 4972 taxes by
the period of the event (as here) or annualize them, and whether a period alternative minimum tax figured on
annualized income before the exemption is how you complete line 16.

**Where it lives.** `form2210:/form2210ScheduleAiLine16ColA` through `form2210:/form2210ScheduleAiLine16ColD`,
`form2210:/form2210ScheduleAiPart1AttestationsConsistent`, `form2210:/form2210ScheduleAiExactLadderFenceSatisfied`,
`form2210:/form2210ScheduleAiPreferentialCharacterInputsCompleteColA` through
`form2210:/form2210ScheduleAiPreferentialCharacterInputsCompleteColD`.


### IN-210 — Form 2210: household employment taxes and the estimated-tax penalty base

**The question.** A household employer owes Schedule H taxes. When do those taxes stay out of Form 2210
Part I line 2 (and so out of line 4, the required installments and the penalty), and out of Schedule AI line 16?

**The statute and instructions.** IRC 3510(b)(1) (our copy is the Office of the Law Revision Counsel's text
of the 2024 edition, checked against the current online text): "Solely for purposes of section 6654,
domestic service employment taxes imposed with respect to any calendar year shall be treated as a tax
imposed by chapter 2". IRC 3510(b)(2): "Paragraph (1) shall not apply to any employer for any calendar year
if- (A) no credit for wage withholding is allowed under section 31 to such employer for the taxable year of
the employer which begins in such calendar year, and (B) no addition to tax would (but for this section) be
imposed under section 6654 for such taxable year by reason of section 6654(e)." Instructions for Form 2210
(2025), page 2, Line 2 table footnote: "Don't include household employment taxes if both of the following
are true: (1) you didn't have federal income tax withheld from your income, and (2) you wouldn't be required
to make estimated tax payments even if the household employment taxes weren't included." Schedule AI line 16
takes "the same taxes used to figure Form 2210, Part I, line 2".

**What the software does.** Condition (A) reads Form 1040 line 25d (all federal income tax withheld) as
zero. Condition (B) is one of the two section 6654(e) exceptions figured without the household employment
taxes: line 4 less line 6 under $1,000 (section 6654(e)(1), the tax shown reduced by the section 31 credit,
as the form's line 7 test states it), or the no-liability exception of section 6654(e)(2). When both hold,
line 2 and Schedule AI line 16 column (d) leave the household employment taxes out; the return is then
exempt from the penalty.

**Why we chose it.** The statute names section 6654(e) only, so the section 6654(d) safe harbors (paying
90 percent of this year's tax or 100 or 110 percent of last year's) do not take the taxes out, even though
the footnote's "you wouldn't be required to make estimated tax payments" could be read more widely. The
section 6654(e)(3) waivers (casualty, disaster, retirement after 62, disability) are determinations the IRS
makes on request, which the software does not figure, so they never take the taxes out. Line 6 includes the
excess social security credit and the Form 8689 credit as the form does; with no income tax withheld these
are almost always zero.

**Our best recommendation.** Keep. Confidence high for the rule; medium for leaving out the section
6654(e)(3) waivers (a filer granted one owes less than the software shows only if the waiver was partial).

**What we would like a reviewer to check.** Whether the section 6654(d) safe harbors should count under the
footnote's wording.

**Where it lives.** `estimatedPayments:/form2210HouseholdEmploymentTaxesLeaveTheBase`,
`estimatedPayments:/form2210HouseholdEmploymentTaxesOnLine2`,
`estimatedPayments:/form2210PartILine2OtherTaxesExcludingHouseholdEmploymentTaxes`.

## Printing and computation conventions

### PR-01 — An amount multiplied by a ratio: rounding once or twice

**The question.** Several lines multiply a dollar amount by a ratio, for example a line 6 of $1,005 times 0.499
= $501.495. Rounded once to whole dollars that is $501. Rounded first to cents ($501.50) and then to dollars it
is $502. Which is right?

**The IRS text.** Instructions for Form 1040 (2025), page 23, Rounding Off to Whole Dollars: "If you do round to
whole dollars, you must round all amounts. To round, drop amounts under 50 cents and increase amounts from 50 to
99 cents to the next dollar."

**What the software does.** Cents first, then whole dollars, as a filer working on paper writes the product to
the cent and then rounds. This affects about ten lines (Form 8814 lines 9-10, Form 8839 line 10, Form 8863
phase-outs, Form 8815, Form 8615 line 13, Form 2555 line 40, the Schedule A mortgage interest limit). No
change was made.

**Why the owner chose it.** It matches paper practice, and it changes at most $1.

**Our best recommendation.** Keep it, but apply it everywhere. One line (Form 2555 line 36) was earlier changed
to round the exact product once; the two conventions should not coexist.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `form8814:/form8814Children/*/line9QualifiedDividendsIncluded`, `form8839:/form8839Children/*/line10`,
`form8863:/aotcCreditAfterPhaseout`, `form2555Housing:/form2555ComputedLine36HousingExclusion` (the one line
that differs).

### PR-02 — Schedule 2 lines with a typed amount: the printed box

**The question.** Some Schedule 2 lines carry an amount the filer types. The total adds the amount floored at
$0, but the box could print a negative number, so the form would not add up.

**What the software does.** The printed box shows exactly the amount added to the total (floored at $0), on
every Schedule 2 line whose amount the filer types.

**Why the owner chose it.** A printed form must add up.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm.

**Where it lives.** `schedule2:/schedule2Line17zAnyOtherTaxesPrinted`, `schedule2:/schedule2Line16LowIncomeHousingCreditRecapturePrinted`,
`schedule2:/schedule2Line17bMortgageSubsidyRecaptureTaxPrinted`.

### PR-03 — Form 2555 line 35: "rounded to at least three places"

**The question.** Line 35 divides line 34 by line 27 and says to enter the result "as a decimal (rounded to at
least three places)". How many places does the software keep, and which way does it round?

**The IRS text.** Form 2555 (2025), page 3, line 35: "Divide line 34 by line 27. Enter the result as a decimal
(rounded to at least three places), but don’t enter more than “1.000”."

**What the software does.** Exactly three places, rounded half up once from the exact quotient (for example
5,004.96 / 10,000 is 0.500, not 0.501), and never more than 1.000. This is the maintainers' reading, not an owner
ruling: the form allows more places and does not say which way to round.

**Why it was chosen.** Three places is what the form's box shows, and rounding once from the exact figure avoids
the double rounding a cents step would add.

**Our best recommendation.** Keep it.

**What we would like a reviewer to check.** Nothing specific; confirm that three places is acceptable.

**Where it lives.** `form2555Housing:/form2555Line35EmployerProvidedRatioThousandths`.

## What this release does not cover

These are scope decisions, not tax interpretations. They are listed so a reviewer knows what the software will
not do. Where a covered return reaches one of these forms, the software refuses rather than guess.

- **Return types:** Form 1040-NR (nonresident aliens), Form 1041 (estates and trusts), and the entity returns
  (Forms 1065, 1120, 1120-S, 990-T) and Form 1040-SS. These are not Form 1040 returns.
- **Forms outside the release (Form 1040 filers who need them are refused):** Form 8611 (recapture of the
  low-income housing credit), Form 8697 (look-back interest under the completed contract method, including its
  supporting schedule), Form 8866 (look-back interest under the income forecast method), Form 8621 (passive
  foreign investment companies), Form 965-A, Form 8834, Form 8911, Form 8912, Form 4136, Form
  8689 and Schedule J (farm income averaging). The owner's instruction: "Keep the form [...] OUT for now. but if
  there is a wrong calculation, we have to fix" it. Parts of some of these forms exist in the dictionary (IN-18
  touches Form 8621) and are kept correct, but the forms are not in the release's scope.
- **Form 1099-SB** (life insurance contract information) is taken in as a document, but its tax treatment is
  refused.
- **Covered, for clarity:** every state of residence (the federal return does not depend on the filer's
  state); the fiscal-year and short-year rules for estimated tax; the Commonwealth of the Northern Mariana
  Islands and territorial wage statements; Form 8997 (qualified opportunity fund investments), except that a
deferral or inclusion of a section 1231 gain from Form 4797 is refused, as is a deferral by a foreign eligible
taxpayer who has not waived the treaty benefits.

## Choices for tax year 2026 (a separate, future release)

The owner also decided how the 2026 dictionary will be labelled. These are not interpretations of 2025 law;
they decide how the software marks figures that are not yet final.

- The 2026 dictionary starts from this 2025 release and changes only what 2026 law changes.
- Every 2026 figure is labelled by how certain it is: enacted and scheduled; inflation-indexed (a status that
  becomes "enacted" when the IRS publishes the figure); derived from other figures; or taken from a draft form
  only. Figures fixed by statute are cited to the statute. A statutory fraction (for example the 2/37 in the
  2026 limitation on itemized deductions) is carried as an exact ratio, not a rounded decimal.
- A 2026 schedule based on proposed regulations is built but refused until final. The owner applied this to the
  proposed rules published in the Federal Register, Vol. 91, No. 160 (August 20, 2026), page 53812, REG-119882-25,
  "Application of the Personal Responsibility and Work Opportunity Reconciliation Act of 1996 to the Refunded
  Portion of Certain Federal Refundable Tax Credits", which "would provide that the refunded portion of certain
  refundable Federal income tax credits available to individuals is a ‘‘Federal public benefit’’".

## Appendix — owner decisions on process, not on tax law

Listed only so the record is complete. None of them changes how tax is computed.

- A second completeness count for the release, beside the strict one; the release boundary is frozen.
- How and when releases are cut, reviewed, tagged and published.
- Removing internal development notes from the published files before release.
- Where fact descriptions keep their history (outside the published files).
- Printing one copy of a per-person form for each spouse, each mapped to that spouse's figures.
- Taking every printed box of a payer's form as an input, whether or not the federal return uses it.
- Storing monthly HSA coverage as a twelve-month list per person.
- Entering the Form 8962 allocation percentages as numbers, with the printed text derived from them.
- The interview rule that every Form 1095-A on a return either carries a shared-policy group key or none does.
- Keeping existing exported fact names stable for downstream users.
- Citing sources in published files by publisher, printed page and quotation.
- Mapping the printed Form 8801 Part III boxes to the computed facts.

### IN-280 — Schedule C: statutory-employee wages combined with other receipts on one schedule (ruled — lead 2026-10-01)

**The question.** A filer enters statutory-employee wages (Form W-2 box 13) and other self-employment
receipts on the same Schedule C. What does the return do?

**The IRS text.** Instructions for Schedule C (2025): "If you had both self-employment income and statutory
employee income, you must file two Schedules C. You cannot combine these amounts on a single Schedule C"
(https://www.irs.gov/pub/irs-pdf/i1040sc.pdf, page 5).

**Ruling.** The combined schedule is an entry the instructions forbid, so no figure computed from it is
the tax. The return is held with a named flowIncomplete reason that directs the filer to a second
Schedule C. Two Schedules C, the supported route, compute: the statutory one is kept off Schedule SE and
the other is charged self-employment tax (case `tsc-060-two-schedules-statutory-one-off-schedule-se`).
No supported return is refused and no SE tax is silently lost (verify row FED-1040SC-LINE1-STATUTORY-COMMINGLING-060).

### IN-281 — Form 461 line 5 (Schedule E rental): is a Schedule E rental a trade or business for the excess business loss limitation? (ruled — lead 2026-10-01)

**The question.** Is a Schedule E rental a trade or business for the excess business loss limitation?

**The IRS text.** Instructions for Form 461 (2025): "Trade or business. An activity qualifies as a trade or business if your primary purpose for engaging in the activity" and "Enter any supplemental income or loss reported on a Schedule E" (https://www.irs.gov/pub/irs-pdf/i461.pdf, pages 1-2). Whether a rental meets that test is a facts-and-circumstances question the return cannot answer from its figures.

**Proposed answer.** Ruled: ask per rental (`/rentalProperties/*/writableRentalIsTradeOrBusiness`); Yes keeps it on line 5, No adds its loss or income back on lines 10-11; unanswered on a return that reaches Form 461 holds.

**Where it is tested.** Cases `tsc-029-form461-line5-rental-is-a-trade-or-business` (line 8p 7,000) and `-not-a-trade-or-business` (0).

### IN-282 — Form 461 line 3 (capital gains and losses): which capital gains count on Form 461, and how are capital losses treated? (ruled — lead 2026-10-01)

**The question.** Which capital gains count on Form 461, and how are capital losses treated?

**The IRS text.** Instructions for Form 461 (2025): "Losses from sales or exchanges of capital assets are not included" and gains "should not exceed the lesser of capital gain net income limited to only gains and losses attributable to a trade or business, or capital gain net income" (https://www.irs.gov/pub/irs-pdf/i461.pdf, pages 1-2).

**Proposed answer.** Ruled: ask the capital gain net income attributable to the trade or business (`/writableForm461BusinessCapitalGainNetIncome`); line 3 takes Form 1040 line 7a, gains above the smaller of that amount and capital gain net income are added back on line 10, and capital losses are added back on line 11.

**Where it is tested.** Case `tsc-029-form461-line3-capital-gain-part-business` (line 8p 57,000).

### IN-283 — Form 8582 Part VII (Schedule C loss activities): the ratable split of the unallowed loss leaves an odd cent: which activity carries it? (ruled — lead 2026-10-01)

**The question.** The ratable split of the unallowed loss leaves an odd cent: which activity carries it?

**The IRS text.** Instructions for Form 8582 (2025): "The total of all the ratios must equal 1.00" and "Multiply each ratio in column (b) by the amount on line C" (https://www.irs.gov/pub/irs-pdf/i8582.pdf, pages 12-13). The form adds the column; it says nothing about a cent left by rounding.

**Proposed answer.** Ruled: round each share half up to the cent and give the residual (plus or minus) to the last listed loss activity, so column (c) totals line C exactly.

**Where it is tested.** Case `tsc-028-two-loss-businesses-cent-allocation`.

### IN-284 — Schedule C line 31 / Form 8582 Part V column (c): how does a prior-year unallowed passive loss of a Schedule C business enter the return? (ruled — lead 2026-10-01)

**The question.** How does a prior-year unallowed passive loss of a Schedule C business enter the return?

**The IRS text.** Instructions for Schedule C (2025): "Use Form 8582 to figure the amount of prior year unallowed passive activity losses you may include on line 31" (https://www.irs.gov/pub/irs-pdf/i1040sc.pdf, page 14); Instructions for Form 8582 (2025): "Column (c). Enter the unallowed losses for the prior years for each activity" (https://www.irs.gov/pub/irs-pdf/i8582.pdf, page 10).

**Proposed answer.** Ruled: ask it per business (`/scheduleCs/*/writablePriorYearUnallowedPassiveLoss`, the 2024 Form 8582 Part VII column (c)); it enters Part V column (c); the allowed part reduces line 31 (PAL); the rest carries forward.

**Where it is tested.** Case `tsc-028-prior-year-unallowed-passive-loss-carried-in`.

### IN-285 — Schedule C lines 1-31 and Form 8829: lines 7, 29 and 31 now keep cents; line 30 is Form 8829 line 36 rounded to whole dollars. Which? (ruled — lead 2026-10-01)

**The question.** Lines 7, 29 and 31 now keep cents; line 30 is Form 8829 line 36 rounded to whole dollars. Which?

**The IRS text.** Instructions for Form 1040 (2025): "If you do round to whole dollars, you must round all amounts" (https://www.irs.gov/pub/irs-pdf/i1040gi.pdf, page 23).

**Proposed answer.** Ruled: one rule for the schedule: either every Schedule C and Form 8829 line keeps cents (rounding only at Form 1040), or every one rounds; today the existing constraint rounds line 30 while F kept cents on 7, 29 and 31.

**Where it is tested.** Transcripts of the s1567 fixtures round line 30 per the existing constraint; they change if the lead rules cents.

**Lead ruling (2026-10-01).** Keep cents on every Schedule C and Form 8829 line; whole-dollar rounding, if any, happens
only where Form 1040 rounds. The existing constraint that rounds line 30 is retargeted to the cents value, so lines 7,
29, 30 and 31 agree.

### IN-286 — Form 461 / Form 172 (farming losses): does the farming-loss ordering change Schedule 1 line 8p? (ruled — lead 2026-10-01)

**The question.** Does the farming-loss ordering change Schedule 1 line 8p?

**The IRS text.** Instructions for Form 461 (2025): "you must allocate the threshold amount first to the farming losses to the extent you have an NOL" (https://www.irs.gov/pub/irs-pdf/i461.pdf, page 1).

**Proposed answer.** Ruled: no; the ordering (threshold first to farming losses) only characterizes the resulting NOL for the 2-year farming carryback; line 8p is unchanged.

**Where it is tested.** Case `tsc-029-form461-line6-schedule-f-loss` asserts line 8p only.

### IN-287 — Schedule C checkboxes (line 1 statutory box, line H): is a checkbox left unchecked an unanswered question that holds? (ruled — lead 2026-10-01)

**The question.** Is a checkbox left unchecked an unanswered question that holds?

**The IRS text.** Schedule C (2025): "check the box if this income was reported to you on Form W-2" and "If you started or acquired this business during 2025, check here" (https://www.irs.gov/pub/irs-pdf/f1040sc.pdf, page 1).

**Proposed answer.** Ruled: no; a "check if" box unanswered is unchecked (the statutory box is decided by a statutory Form W-2 link; line H by the business-began date when start-up costs are entered, which holds when unanswered).

**Where it is tested.** Cases `tsc-base-single` (box unchecked computes) and `tsc-gate-startup-business-began-unanswered` (holds).

#### IN-287 amendment — line H for a reopened business (2026-10-05, print only)

Line H is checked when the business was begun or acquired in 2025, **or** when it was reopened or restarted in 2025 after a temporary closing with no 2024 Schedule C for it. The instructions say "reopening or restarting this business after temporarily closing it" (Instructions for Schedule C (2025), line H). A reopened business is the same business, so its began date stays the original date (IN-334). Line H therefore needs its own reopened answer, and an unanswered reopened question leaves the box unchecked. This is print only. Ruled under the product owner's delegation of 2026-10-05.

### IN-288 — Form 461 lines 4, 5 (K-1 box 1) and 6: are Form 4797 Part I items, Schedule K-1 box 1 business income and Schedule F trade or business items without asking? (ruled — lead 2026-10-01)

**The question.** Are Form 4797 Part I items, Schedule K-1 box 1 business income and Schedule F trade or business items without asking?

**The IRS text.** Instructions for Form 461 (2025): "If you own an interest in a partnership or S corporation, the trade or business determination is made at that entity's level" (https://www.irs.gov/pub/irs-pdf/i461.pdf, page 1); Instructions for Form 4797 (2025): "property used in your trade or business" (https://www.irs.gov/pub/irs-pdf/i4797.pdf, page 1).

**Proposed answer.** Ruled: yes; Form 4797 Part I property is property used in a trade or business, a K-1 business is decided at the entity level, and Schedule F is a farming business; no question is asked.

**Where it is tested.** Cases `tsc-029-form461-line4-*`, `-line5-k1-*`, `-line6-*`; constraint `scheduleOneLine8pIsTheFormFourSixtyOneExcessBusinessLossWithOtherBusinessLines`.

### IN-289 — Schedule C / Form 8829 gate questions: which Schedule C and Form 8829 questions hold when unanswered (IN-277 applied to this module)? (ruled — lead 2026-10-01)

**The question.** Which Schedule C and Form 8829 questions hold when unanswered (IN-277 applied to this module)?

**The IRS text.** Form 8829 (2025): "For daycare facilities not used exclusively for business, go to line 4. All others, go to line 7." (https://www.irs.gov/pub/irs-pdf/f8829.pdf, page 1); Instructions for Form 8829 (2025): "Enter any amount from your 2024 Form 8829, line 43." (https://www.irs.gov/pub/irs-pdf/i8829.pdf, page 5).

**Proposed answer.** Ruled: hold: line G and line 32 with a loss; 32b amount at risk; vehicle method and business miles; home office method; Form 8829 total area, all-income-from-home, daycare non-exclusive, itemize, use stopped, additions, line 37 basis, operating expenses; simplified square feet and shared; gross receipts. Do not hold: checkboxes (IN-287), Form 8829 carryovers (an absent carryover is $0 by its text: "Enter any amount from your 2024 Form 8829").

**Where it is tested.** The gate and input matrix of the Schedule C round-5 source cases; cases `tsc-gate-*`, `tsc-input-*`.

**Lead ruling (2026-10-01).** Adopted, except the carryovers: on the regular method, an unanswered prior-year Form 8829
carryover (operating expenses, excess casualty losses and depreciation) holds with a named reason like every other
input a money line needs (IN-277); it is not read as $0. A filer with no carryover answers $0.

### IN-276 — Form 5695 line 25d: three or more items of enabling property (ruled — lead 2026-10-01)

**The IRS text.** "To qualify for the energy efficient home improvement credit for specified property, you must
provide a valid QMID for each item" (https://www.irs.gov/pub/irs-pdf/i5695.pdf, page 5). Line 25c is one cost total and
line 25d prints two QMID boxes, (i) and (ii) (https://www.irs.gov/pub/irs-pdf/f5695.pdf, page 3).

**Ruling.** With two items, both boxes are required. A third item's QMID cannot be reported on the return, and its
cost cannot be separated from the single line 25c total, so the return holds with a named reason
(`/form5695EnablingPropertyQmidsReported`) rather than crediting an item whose QMID is not reported (verify row
FED-5695-P2-PRINTEDQMID-048; pre-audit finding A9).

**Where it is tested.**
- `tests/nodes/ty2025/form5695/t5695-enabling-three-items-held` (three items: held).
- `t5695-enabling-two-items-one-qmid-held` (two items, 25d(ii) blank: held).
- `t5695-enabling-two-items-both-qmids` (two items, both boxes: line 25e computes, $300).

### IN-277 — Form 5695 Part II: a section question left unanswered with a cost behind it (ruled — lead 2026-10-01)

**The IRS text.** Line 17a asks whether the improvements are installed in or on the main home, and "If you checked
the 'No' box for line 17a, 17b, or 17c, you cannot claim" the Section A credit (https://www.irs.gov/pub/irs-pdf/f5695.pdf, page 2);
line 21a asks the Section B question (f5695:131-132).

**Ruling.** A Yes is a condition of the credit, a No denies it, and an unanswered question decides neither. When a
cost is entered behind an unanswered 17a-17c, 17e (extended 2026-10-01: an unanswered 17e decides neither way under IN-278), 21a-21b or 26a, the return holds with a named reason. The credit, the
printed cost lines (18a, 19a, ... 26b) and the joint-occupancy line 28 numerator all read the same gate test, so a
printed box never disagrees with its total and line 28 never counts a line the credit excludes (verify row
FED-5695-P2-JOINTOCCGATE-050; pre-audit probes P11, P13, finding A4).

**Generalized (lead 2026-10-01, pre-audit 2).** The rule is not a list of questions. It covers EVERY question on the
form that a printed line is conditioned on (a "skip lines ... if No" gate: 7a, 17a-17c, 17e, 21a-21b, 25a, 26a, 32a and
any other) and EVERY input a money line needs (for example the line 10 kW capacity behind line 11):
- unanswered, with an amount behind it: the return holds with a named reason; never a silent $0;
- answered so that the form says to skip: every skipped line is blank or $0 in every reader (credits, printed lines,
  line 28 numerator, the allocation flag), and nothing behind it is asked or holds;
- answered so that the line applies: the line computes.
- two readings: (a) line 32a is a check box, so an unanswered 32a with no
  other-occupant amount entered is the unchecked box and the return computes; only an other-occupant amount behind
  an unanswered 32a holds. (b) the 80% nonbusiness gate answered No means no item is used less than 80% for
  nonbusiness purposes, so 25D(e)(7) (26 U.S.C. 25D, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section25D&num=0&edition=2024) takes nothing away and each cost counts in
  full; only the gate left unanswered with an item lacking its share holds.
- build pre-audit 3 rulings (lead 2026-10-01, one batch):
  (c) line 7c is a check box like 32a ("check here", https://www.irs.gov/pub/irs-pdf/f5695.pdf, page 1): unanswered with no
  joint-occupancy worksheet amount is the unchecked box and computes; unanswered WITH a worksheet amount entered holds.
  (d) the two-homes question unanswered with the other home's line 30 entered holds (never a silent drop of that home).
  (e) the 80% gate unanswered with a Part I or Part II cost behind it holds on every route, typed line total and item
  list alike; one gate state, one outcome.
  (f) an input whose value cannot be what the form asks (a negative kW capacity, a negative cost) holds as an invalid
  answer; it never resolves to a silent $0.
  (g) the two-homes rule is read by every line that totals the credit: on a joint return with two main homes, line 30
  carries the other home's line 30 even when this home has no cost, so line 32 and whether Form 5695 is required read
  it too (i5695:185-193).
- rulings (2026-10-01):
  (h) an invalid (negative) answer: the line shows its floored value and the return holds with a named reason
  ("floor plus hold"), so the printed field stays in range and nothing is filed on the bad answer.
  (i) the 80% gate unanswered holds on every route, including an item that carries its own share; the gate is the
  form's question and one gate state has one outcome.
  (j) line 25c with code A and no qualifying window prints $0, as with no code (IN-272).
  (k) Part I active and whether Form 5695 is required follow what is counted: behind a 5a No or 7a No with nothing
  else counted, Part I is not active and the form is not required by Part I.

### IN-278 — Form 5695 line 17e: improvements related to the construction of the main home (ruled — lead 2026-10-01)

**The IRS text.** Instructions: "If you are claiming the credit only for expenses for qualified improvements to an
existing home or for an addition to or renovation of an existing home, check the 'No' box. If the qualified
improvements for which you are seeking to claim the credit are related to the construction of a new home, check the
'Yes' box. If you check the 'Yes' box, skip lines 18a through 20d" (https://www.irs.gov/pub/irs-pdf/i5695.pdf, page 5).
The form under the question: "If you checked the 'Yes' box, you can only claim the energy efficient home improvement
credit for qualifying improvements that were not related to the construction of the home"
(https://www.irs.gov/pub/irs-pdf/f5695.pdf, page 2).

**Ruling.** Follow the instructions. A filer who claims improvements not related to construction answers No, so a
Yes means the claimed improvements are construction costs, and Section A (lines 18a-20d) earns nothing. The intake
question must carry the instructions' guidance, so a filer reading only the form's sentence does not answer Yes for
non-construction improvements.

**What we would like a reviewer to check.** The form's own sentence reads as if a Yes still allows non-construction
improvements. Confirm that the instructions' skip governs.

### IN-290 to IN-299 — Schedule C spec review readings (ruled — lead 2026-10-01)

Ruled in one batch. Each summary row above
states the ruling and its source. IN-294 rests on Instructions for Form 461 (2025): excess losses "should be determined
without regard to any deductions, gross income, or gains attributable to any trade or business of performing services of an
employee" (https://www.irs.gov/pub/irs-pdf/i461.pdf, page 1). IN-295 rests on "allocate the amount shown on line 36 to each business
using any method that is reasonable under the circumstances" (https://www.irs.gov/pub/irs-pdf/i8829.pdf, page 5).

#### IN-297 amendment — car-loan interest beside the standard mileage rate (owner, 2026-10-05)

**Decision.** The standard mileage rate replaces depreciation, lease payments and actual operating expenses (Instructions for Schedule C (2025), line 9). It does not replace the business share of interest on a loan for that vehicle. A self-employed filer deducts that share on line 16b, and never deducts the same interest again on Schedule 1-A. IN-297's phrase "the separate interest deduction for that vehicle" now means only that Schedule 1-A double deduction.

**Source.**
- Pub. 463 (2025): a self-employed filer may deduct the business part of car-loan interest "even if you use the standard mileage rate".
- IRC 163(h)(2)(A): interest on a trade or business loan is not personal interest.
- The line 9 instructions bar only "depreciation, rent or lease payments, or your actual operating expenses", and their caution forbids only double use with Schedule 1-A.

**Example.** $1,000 of interest at 60% business use puts $600 on line 16b.

**Why.** Both independent source derivations (the package author and the blind meaning reviewer) found the publication and statute against the earlier reading. The owner amended it on 2026-10-05.



### IN-300 — Form 5695 exterior doors: individual joint shares and payment normalization (bounded alpha candidate, 2026-10-04)

**The source text.** IRC 25C(b)(4)(A) caps an exterior door at $250; (B) supplies the $500 aggregate door ceiling. Instructions for Form 5695 (2025), page 3, Joint occupancy, require the allocable credit from each property to use its credit limit multiplied by the filer's payment fraction. Instructions for Form 1040 (2025), Rounding Off to Whole Dollars, say to include cents when adding amounts and round only the total. Internal source locators: `26 U.S.C. 25C, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section25C&num=0&edition=2024`, `https://www.irs.gov/pub/irs-pdf/i5695.pdf, page 3`, `https://www.irs.gov/pub/irs-pdf/i1040gi.pdf, page 23`.

**Bounded implementation.** The joint door route applies the individual $250 ceiling to the main door, each printed additional door, and each statement door using that door's own and other-occupant payments. Hidden contributions keep cents and round the total once. Printed 19g stays its existing binding. An unknown required distribution holds the credit and return rather than refusing the population.

**Input normalization.** Per FACT-SKILL-1 §2.4b and the alpha lead decision, complete individual raw payments supply the denominator. The typed all-door payment total is a cross-check: an absolute difference below $1 is accepted, while $1 or more holds. Negative required individual values remain invalid. A zero aggregate establishes missing individual zeroes only if no explicit individual value contradicts zero. This clarifies intake normalization, not the legal category-cap trigger.

**Unresolved.** IN-273's existing category allocation remains in place. SC-06 challenges when that category allocation must trigger after individual-door limits; this entry does not adjudicate it. Native Dollar intermediates round to cents before the final whole-dollar sum: SC-07's exact source total `225 + 250×76/854 + 250×76/854` rounds to 269 but the cent-intermediate candidate produces 270. A protected engine/procedure follow-up is required. Neither a normal-corpus pass nor this entry accepts the whole door family or procedure.


#### IN-300 amendment — SC-06 household category trigger (2026-10-04)

**Decision.** Apply the individual $250 limits first. Sum the household credit from every qualifying physical door before any whole-dollar rounding. Only if that sum exceeds $500 apply the additional all-door $500 payment-share ceiling, without increasing the filer's item-limited credit. Equality does not trigger allocation. This amends IN-273's unconditional all-door ceiling for this alpha branch only; it does not revise the separate line 28 corresponding-property rule.

**Source and reasoning.** IRS Instructions for Form 5695 (2025), printed page 3, Joint occupancy, `https://www.irs.gov/pub/irs-pdf/i5695.pdf, page 3,230-231`: “If the aggregate credit that would be allowed to all occupants” and “exceeds the credit limit below”. IRC 25C(b)(4)(A)-(B), `26 U.S.C. 25C, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section25C&num=0&edition=2024`, supplies both per-door and aggregate limits. Section 25C(f)(1) imports rules similar to 25D(e)(4), including the smaller-of allocation. Current statute snapshot `26 U.S.C. 25C, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section25C&num=0&edition=prelim` preserves these limits. The post-item reading gives meaning to both limits and the conditional trigger. This is the lead's researched interpretation under FACT-SKILL-1 §2.8, implemented on the user's instruction to fix the SC-06 household category trigger, not an IRS worked example or external VERIFY acceptance.

**Worked examples.** A pays $900 for one door and B pays $2,100 for another. Each household door credit is $250; the $500 household sum does not exceed the limit, so each retains $250. Likewise A's shares $900/$1,000 and $300/$3,000 are $225+$25=$250 with household total $500. If B also pays $1 for a third qualifying door, the household credit is $500.30, so category allocation applies even though $500.30 would print as $500. Retain the unrounded trigger.

**Intake and migration.** Itemize other payments separately on each of the filer's doors. Also itemize every qualifying door paid entirely by other occupants, with zero own cost, and affirm that both inventories jointly cover all qualifying household doors without duplicates. A new interview derives totals; it never asks for an additional typed all-door aggregate. An existing aggregate is optional and, when supplied alongside a complete attested inventory, reconciles to ALL household other payments with the established less-than-$1 tolerance. Without new inventory inputs, an exactly matching legacy total may establish no additional other-only doors. Any residual requires the missing door breakdown: even a sub-dollar extra door can move a household at $500 across the trigger. Partial new inputs never fall back to legacy inference. Unknown or negative required values hold via the existing named line32a input reason.

**Scope.** Other-only doors affect the household door-category calculation; they never add to the filer's printed costs or the line28 denominator for corresponding properties. Per-door eligible payments already exclude rebates, installation labor, disallowed financing and ineligible business-use portions; the software must retain qualification/manufacturer evidence. Exact sub-cent arithmetic, printed-door caps on a return that is not joint, and statement generation remain separate work.


#### IN-300 amendment — independent door limits and exact allocation (2026-10-04)

**Decision.** Apply the section 25C(b)(4)(A) $250 limit independently to every physical door, regardless of the printed slot or business-use ordering. Preserve line 19g as the form's raw 30% multiplication. Line 19h uses the sum after all individual caps and then the category limit. A computation statement explains a difference from the printed subtotal; sorting alone cannot enforce this statutory rule after differing use adjustments.

**Authority.** `26 U.S.C. 25C, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section25C&num=0&edition=prelim` and `26 U.S.C. 25C, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section25C&num=0&edition=2024` limit any exterior door to $250 and all doors to $500. `https://www.irs.gov/pub/irs-pdf/f5695.pdf, page 2` supplies the printed 19g/19h arithmetic. The statute's item limit controls when the printed shortcut omits an individual cap. Joint occupancy in `https://www.irs.gov/pub/irs-pdf/i5695.pdf, page 3` allocates the item ceiling by payments. General rounding instructions `https://www.irs.gov/pub/irs-pdf/i1040gi.pdf, page 23` support adding amounts before rounding a total.

**Precision.** After the existing eligible-cost adjustment boundary, keep all per-door fractions, household item sums, strict household trigger and category fraction exact. Round the final filed door line once to whole dollars (HALF_UP). This prevents the source-derived SC-07 total 115075/427 from becoming 270 instead of269, and preserves a household total500.003 as strictly greater than500. A dedicated additive engine unit supplies BigInt rational arithmetic and explicit Dollar conversion; it changes no existing Dollar operator. Legacy cent-valued observational helpers do not drive the new allocation decision.

**Evidence and scope.** Independent source author cases `issue1199-*` and `issue1200-*`, exact arithmetic JVM/JS contracts and frozen-dictionary conformance substantiate the repair. This is the lead's source-based alpha interpretation, not a new IRS worked example or withdrawal of VERIFY findings. The prior SC-06 amendment remains in force. Wider form money findings and production release acceptance remain outside this door repair.


#### IN-300 amendment — exterior-door printed placement and subtotal (2026-10-04)

**Decision.** Preserve the accepted exact monetary computation. For presentation, rank the three individually entered doors by qualifying cost after the nonbusiness-use adjustment, with original-entry order breaking ties. Move the entire physical door's qualifying cost, both QMID segments, and allocated exact credit together. Recompute printed 19d/19f from those actual costs. Printed 19g retains the raw 30% multiplication of reordered costs when no positive qualifying itemized statement contributes, including an explicitly empty statement. With positive qualifying statement costs, it sums the individual capped allocated contributions of the remaining two doors and the itemized inventory before rounding once. Incomplete selected statements hold; a closed Section A prints zero.

**Source.** Instructions for Form 5695 (2025), page 6, `https://www.irs.gov/pub/irs-pdf/i5695.pdf, page 6`, require the most expensive exterior door, its QMID, the next two qualifying doors, and a statement for other doors. Page 1, lines 62-65, applies the nonbusiness-use portion to the reported costs. IRC 25C(b)(4), `26 U.S.C. 25C, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section25C&num=0&edition=prelim`, says “$250 in the case of any exterior door” and supplies the aggregate limit. That statutory individual cap governs the printed credit subtotal where a raw multiplication would contradict it. Joint allocation remains governed by the corrected instructions at `https://www.irs.gov/pub/irs-pdf/i5695.pdf, page 3`; the current IRS correction notice independently confirms the specified allocated-credit lines. The rounding instruction at `https://www.irs.gov/pub/irs-pdf/i1040gi.pdf, page 23` requires “amounts and round off only the total”.

**Boundaries.** This is the lead's source-priority interpretation, not an IRS worked example. Statement rows remain on 19e rather than being promoted onto the face of the form. Joint household allocation and independently rounded printed subtotals can still differ from plain addition; the implementation does not invent costs or subtract a residual merely to force equality. The former raw helper remains a compatibility observation but no longer feeds the PDF's 19g box. The ordinary misordered and business-use witnesses print 250 + 150 = 400; the itemized-only $1,000 witness prints 0 + 250 = 250. Existing monetary paths remain unchanged. Only VERIFY can retire its finding.


### IN-301 — Schedule 1 line 20: the section 501(c)(18) deduction, the phaseout and modified AGI (ruled 2026-10-04)

**The statute.** IRC 219(e)(2) (U.S. Code p. 949) makes "any amount contributed on behalf of any individual to a plan described in section 501(c)(18)" a qualified retirement contribution, deductible under 219(a). 219(b)(1) caps "the amount allowable as a deduction under subsection (a)", meaning all of them together, at "the lesser of— (A) the deductible amount, or (B) ... the compensation". 219(b)(3) gives the 501(c)(18) deduction its own cap, "Notwithstanding paragraph (1)": the lesser of $7,000 or 25 percent of compensation. That $7,000 is a flat statutory figure with no cost-of-living clause; it equals the 2025 deductible amount only by coincidence. 219(g)(1) (p. 950) reduces "each of the dollar limitations contained in subsections (b)(1)(A) and (c)(1)(A)", which is the deductible amount. 219(g)(2)(B)-(C) floor the reduced limitation at $200 and round the reduction down to $10. 219(g)(3)(A)(ii) figures adjusted gross income "without regard to ... the deduction allowable under this section". 219(g)(5)(B) (p. 951) makes anyone "who makes deductible contributions to a trust described in section 501(c)(18)" an active participant.

**The IRS text.** Pub. 590-A (2025) pp. 9-11 says the IRA limit "is reduced by any contributions to a section 501(c)(18) plan". Neither the IRA Deduction Worksheet in the Form 1040 instructions nor Pub. 590-A Worksheet 1-2 has a 501(c)(18) step. Both modified-AGI computations (Form 1040 instructions, worksheet line 4; Pub. 590-A Worksheet 1-1, p. 16) add back only line 20 and leave line 24f subtracted.

**What the software does.** Let D be the 501(c)(18) deduction allowable under 219(b)(3), the Schedule 1 line 24f amount after that cap; it is not the raw code H contribution. A filer with D > $0 is an active participant. Modified AGI adds D back with line 20. The steps, in statute order:
1. reduction = deductible amount × (modified AGI − threshold) ÷ band, rounded down to $10;
2. limitation = deductible amount − reduction, floored at $200 unless the reduction reaches the whole amount;
3. ceiling = the lesser of the limitation and compensation;
4. IRA deduction limit = max(0, ceiling − D).

The floor and the rounding apply before D is subtracted. The same net ceiling is the IRA amount allowable for 219(f)(6) and 4973(b).

**Why the owner chose it.** The owner's standing rule is to follow the statute where it is clear, and here it is clear on both points. The order follows from (g)(1) reducing the (b)(1)(A) dollar limitation, which leaves (b)(3)'s separate cap protecting the 501(c)(18) deduction itself. Because the phased base is the flat amount, rounding the reduction down and rounding the remaining limit up give the same figure. The add-back follows from (e)(2) and (g)(3)(A)(ii). The IRS worksheets are a convenience that omit a rare plan type; Pub. 590-A's own note agrees that the limit is reduced. Direction: the statute gives a higher modified AGI and a smaller deduction than the worksheets for this very small population of filers in plans created before June 25, 1959. Two independent source-only derivations, by the package author and the blind meaning reviewer, reached this reading. The product owner delegated the call on 2026-10-04: "do research on Q2 and Q4, use the best answers after consulting advisors".

### IN-302 — Schedule 1 line 20, married filing jointly: the pooled-compensation shortcut (ruled 2026-10-04)

**The statute.** IRC 219(b)(1)(B) (U.S. Code p. 949) caps each individual's deduction at "the compensation includible in the individual's gross income". 219(f)(2) says the maximum deduction "shall be computed separately for each individual". 219(c)(1) raises the limit only for "an individual to whom this paragraph applies". By (c)(2), that is a joint filer whose compensation "is less than the compensation includible in the gross income of the individual's spouse". For that spouse, the limit is the lesser of the dollar amount, or the spouse's own compensation plus the other spouse's compensation reduced by three things:
- (I) the other spouse's 219(a) deduction;
- (II) the other spouse's designated nondeductible contribution;
- (III) the other spouse's Roth IRA contribution.

**The IRS text.** The Form 1040 instructions' IRA Deduction Worksheet line 10 adds both spouses' compensation and sends a joint return to Pub. 590-A only when that total is below $14,000, $15,000 or $16,000. The Form 5329 instructions (line 10) say a joint filer's limit is "generally" $7,000/$8,000 each. Pub. 590-A (2025) p. 9 "General Limit" (the smaller of the dollar amount and "your taxable compensation") and p. 11 (the spousal rule for "the spouse with less compensation") agree with the statute.

**What the software does.** Each spouse's limit uses that spouse's own 219(f)(1) compensation. The spousal increase applies only to the spouse with strictly less compensation; equal compensation gives neither spouse the increase. The pooled total is never a cap. The two readings differ in one situation: the higher-paid spouse is 50 or older with compensation of at least $7,000 but under $8,000, and the pooled total reaches the worksheet's threshold. Example: compensation $7,600 (age 52) and $7,400 (age 40), contributions $8,000 and $7,000. The deductions are $7,600 and $7,000, and the $400 excess owes $24 on Form 5329. The pooled reading allows $15,000.

**Why the owner chose it.** The standing rule is to follow the statute where it is clear. The statute is clear, and the IRS's own publication agrees, so the worksheet's line 10 is a screening shortcut, not a limit. Direction: the statute allows less deduction than the shortcut in that one situation. Two independent source-only derivations agreed. The product owner delegated the call on 2026-10-04: "do research on Q2 and Q4, use the best answers after consulting advisors".

### IN-303 — Schedule 1 line 20: which alimony is IRA compensation (ruled 2026-10-04)

**The statute.** Before the 2017 act, IRC 219(f)(1) ended: "The term 'compensation' shall include any amount includible in the individual's gross income under section 71 with respect to a divorce or separation instrument described in subparagraph (A) of section 71(b)(2)." The 2017 act struck that sentence. Its effective-date note limits the change to instruments "executed after Dec. 31, 2018" and to earlier instruments modified to adopt it (U.S. Code, note to section 219, 2017 amendment). For pre-2019 instruments, the struck text still governs. Former IRC 71(b)(2) (2016 edition, cited because section 71 is now repealed) has three kinds of instrument: (A) "a decree of divorce or separate maintenance or a written instrument incident to such a decree", (B) "a written separation agreement", and (C) a support decree. The sentence names (A) only.

**The IRS text.** Pub. 590-A (2025) p. 7 agrees: compensation includes alimony "you receive under a decree of divorce or separate maintenance", for instruments executed by December 31, 2018 and not modified. The Form 1040 instructions (Schedule 1 line 20) simplify this to all alimony reported on Schedule 1 line 2a.

**What the software does.** Alimony counts as a spouse's compensation only when that spouse received it under an (A) instrument executed before 2019 and not modified to adopt the repeal. Payments under (B) or (C) are not compensation. This needs a per-spouse alimony amount and the instrument type, neither of which is asked today (one return-level amount only).

**Why the owner chose it.** The statute names the instrument by letter, and the publication tracks it; the instructions' line is a simplification. Direction: less compensation than the instructions' reading for (B) and (C) recipients, so a smaller deduction in the rare case where compensation binds. The independent meaning reviewer's reading (finding F-M01) was adopted over the package author's. The product owner delegated the call on 2026-10-04, as for IN-301 and IN-302.

#### IN-303 amendment — whose alimony it is on a joint return (2026-10-05)

**The question.** On a joint return, Schedule 1 line 2a is one combined amount. The software asks for the spouse's part. When that answer is blank, should the whole amount be treated as the primary filer's?

**The statute.** The deduction is "computed separately for each individual" (IRC 219(f)(2), 26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section219&num=0&edition=2024). The alimony sentence counts as compensation only an amount includible in "the individual's gross income" (former IRC 219(f)(1), lines 351-358). No source assigns combined alimony to one spouse by default.

**Decision.** A blank spouse's-part answer holds; it is never defaulted to either spouse. The hold applies when all of these are true:
- the return is married filing jointly;
- taxable pre-2019 alimony is above $0;
- either spouse's traditional contribution is answered.

This matches the blank instrument kind and the blank Schedule 1 line 16 split, which also hold. Before any contribution is answered, the earlier treatment stands, because compensation cannot bind. Answering the part as $0 or as the whole amount remains possible.

**Second amendment (2026-10-05): when the instrument-kind question is reached on a joint return.** A filer's alimony is compensation for the other spouse's spousal limit too (IRC 219(c)(1)(B)(ii), "the compensation includible in the gross income of such individual's spouse"; Form 1040 instructions, IRA Deduction Worksheet line 8, "your (and your spouse's if filing jointly)"). So on a joint return, each filer's instrument-kind question is reached when that filer's taxable pre-2019 alimony is above $0 and EITHER spouse's traditional contribution is answered. The same reach applies to the share question above. A reached, blank kind holds. Found by the build-side challenge (ira-CH BREAK-3, 2026-10-05).

**Why.** A default picks a side. That changes each spouse's compensation cap, the higher-compensated-spouse test and the spousal limit, and no source supports any particular split. Found by the independent bindings reviewer (ira-R2D, 2026-10-05). The call was delegated by the product owner on 2026-10-05.

### IN-304 — Form 8606 line 1: the total cap on the difficulty-of-care increase (ruled 2026-10-04)

**The statute.** IRC 408(o)(5) lets a filer who excludes difficulty-of-care payments under section 131 elect to raise the nondeductible limit by "the lesser of" (A) the deductible amount in effect under section 219(b) less (B) compensation, or the amount so excluded. Section 4973 does not cap the result. The cap comes from IRC 408(a)(1): an individual retirement account will not accept contributions "in excess of the amount in effect for such taxable year under section 219(b)(1)(A)".

**The IRS text.** Pub. 590-A (2025) p. 15: the payments "may increase the amount of nondeductible IRA contributions you can make but not above the $7,000 IRA deductible amount ($8,000 if you are age 50 or older)".

**What the software does.** The increase is the lesser of the excluded payments and the deductible amount less compensation. Total contributions on which the increase acts never exceed the deductible amount. For a filer without a spousal limit the cap holds by construction. It binds a spouse whose section 219(c) room already covers part of the deductible amount.

**Why the owner chose it.** Statute and publication agree. The package author's procedure left the cap out (an omitted obligation, finding F-M02), so this records it rather than resolving a conflict. The product owner delegated the call on 2026-10-04, as for IN-301 and IN-302.

#### IN-304 amendment — what the increase can shelter, in Form 8606 line 1 terms (2026-10-04)

**Correction.** The sentence above, "It binds a spouse whose section 219(c) room already covers part of the deductible amount", treated the spousal room as the limit the increase acts on. That is wrong. IRC 408(o)(2)(B)(i) defines the nondeductible limit from the amount allowable under section 219 "for such contributions", with and without section 219(g), so it depends on what was actually contributed. Contributions within that allowable amount are made nondeductible by the filer's election not to deduct them (IRC 408(o)(2)(B)(ii)), never by the difficulty-of-care increase.

**Decision.** Form 8606 line 1 follows the form's own rule (Instructions for Form 8606 (2025), Line 1): the smaller of the compensation-side limit and the contributions, minus the deduction actually taken, plus any repayment of a qualified reservist distribution.
- **The increase.** The section 408(o)(5) increase, the lesser of the excluded difficulty-of-care payments and the deductible amount less compensation, raises only the compensation side.
- **Where it applies.** The instructions say it raises "the nondeductible IRA contribution limit". They name no line. Placing it on the compensation side is this entry's reading.
- **The cap.** That side never exceeds the deductible amount (IRC 408(a)(1); Pub. 590-A (2025): "but not above the $7,000 IRA deductible amount").
- **The base amount.** The increase is measured from the flat deductible amount, not a limit reduced by a section 501(c)(18) deduction (finding F8606-010, unchanged).

**Worked results.**
- **Spouse with no compensation** (contributes 2,000, deducts all 2,000, excludes 500 of payments, repays 100): line 1 is min(7,000, 2,000) − 2,000 + 100 = 100. A line 1 entry of 600 has no undeducted contribution behind it.
  - The earlier regression expectation (a ceiling of 600 and no refusal) is superseded. A coherent version of that case is a spouse who elects to deduct only 1,400 and designates 600.
- **Spouse with 8,000 contributed, 6,000 room and 1,000 compensation:** line 1 is 1,000, matching the package witness.
- **The same spouse contributing 5,000 and deducting 5,000:** line 1 is 0. The superseded formula ("deductible amount less spousal room") would have allowed 1,000 of unsupported basis.

**Why.** The source-first review of the package (seat rs-RS1, on the repair seat's report of a conflicting regression test) found that the original cap was right in its result for the package witness but stated against the wrong quantity. The product owner delegated the call on 2026-10-04, as for IN-301 and IN-302.

### IN-305 — Form 5329, the spouse with less compensation: the section 4973 allowable amount (ruled 2026-10-04)

**The statute.** IRC 4973(b)(1) measures the excess against "(B) the amount allowable as a deduction under section 219 for such contributions". The flush sentence computes that amount "without regard to section 219(g)". For the spouse with less compensation, 219(c)(1)(B)(ii) reduces the other spouse's compensation by "(I) the amount allowed as a deduction under subsection (a) to such spouse", "(II) ... any designated nondeductible contribution" and "(III) ... any contribution ... to a Roth IRA".

**The IRS text.** Pub. 590-A's spousal worksheet subtracts the other spouse's IRA contributions.

**What the software does.** The lower spouse's section 4973 allowable amount is that spouse's section 219(c) limit computed without 219(g). It uses the other spouse's allowed deduction (after that spouse's own 219(g) phaseout), designated nondeductible contribution and Roth contribution, never the other spouse's raw contribution. An undesignated excess of the higher-paid spouse therefore does not shrink the lower spouse's room.

**Why the owner chose it.** The statute's words are "allowable" and "allowed", and the publication's wording is a simplification that differs only when the higher-paid spouse has an undesignated excess. The independent meaning reviewer's reading (finding F-M04) was adopted. The product owner delegated the call on 2026-10-04, as for IN-301 and IN-302.

### IN-306 — Form 5329 line 11: earnings returned with a contribution before the due date (ruled 2026-10-04)

**The statute.** IRC 408(d)(4): "Paragraph (1) does not apply to the distribution of any contribution" returned by the due date with "the amount of net income attributable to such contribution", and "for purposes of section 61, any net income ... shall be deemed to have been earned and receivable in the taxable year in which such contribution is made". IRC 4973(b)(2)(A) reduces the carried excess by "distributions ... which were included in the gross income of the payee under section 408(d)(1)".

**The IRS text.** The Form 5329 instructions, line 11: "withdrawals from your traditional IRAs that are included in your income".

**What the software does.** The earnings are income under section 61 for the contribution year. They are not a line 11 amount, because the distribution is outside section 408(d)(1). No intake for the earnings exists today, so this ruling changes no computed value. The unbuilt intake is recorded as an inventory obligation.

**Why the owner chose it.** The statute is explicit. The instructions' general wording does not reach a distribution that 408(d)(4) takes out of 408(d)(1). The independent meaning reviewer's reading (finding F-M05) was adopted. The product owner delegated the call on 2026-10-04, as for IN-301 and IN-302.

### IN-307 — Schedule SE and Schedule 1 line 15: whole dollars on each printed line (ruled 2026-10-04)

**The IRS text.** Form 1040 instructions (2025) p. 23, Rounding Off to Whole Dollars: "You can round off cents to whole dollars on your return and schedules. If you do round to whole dollars, you must round all amounts." When adding amounts, "include cents when adding the amounts and round off only the total."

**What is already recorded.** The return rounds to whole dollars. Products are figured to the cent and then rounded (PR-01). Schedule C and Form 8829 keep cents until the amount reaches a Form 1040 line (IN-285, IN-299). The dictionary already rounds each printed Schedule SE line.

**What the software does.** This entry records the convention for Schedule SE rather than adopting a new one.
- **Printed Schedule SE lines.** Every printed line is a whole-dollar amount. A product such as 92.35% of line 3 is figured to the cent and then rounded half-up, away from zero (the engine's Round).
- **Schedule C cents.** They may flow into lines 2 and 3 as addends, which is the "include cents when adding" rule.
- **Schedule 1 line 15.** It adds each filer's rounded line 13.
- **IRA worksheet line 9.** Self-employment earnings minus "any deductions on Schedule 1, lines 15 and 16". It reads those printed amounts and rounds only its own total.

**Why the owner chose it.** The return rounds every amount, as the instructions require of a return that rounds at all. A cents-only Schedule SE chain would mix the two treatments. The package author and the independent meaning reviewer had derived exact cents from the IRS text alone; this entry supersedes the reviewer's pass-B item (d). The product owner delegated the call on 2026-10-04, as for IN-301 and IN-302.

### IN-308 — IRA compensation: foreign-government wages with no Form W-2 (ruled 2026-10-04)

**The statute.** IRC 219(b)(1)(B) caps the deduction at "the compensation includible in the individual's gross income". 219(f)(1) says compensation "includes earned income (as defined in section 401(c)(2))". That widens the term; it does not replace wages. IRC 1402(c)(2)(C) makes this service a trade or business for self-employment tax, so the same pay is also on Schedule SE line 2.

**The IRS text.** Pub. 590-A (2025) p. 6: "Wages, salaries, tips, professional fees, bonuses, and other amounts you receive for providing personal services are compensation". No Form W-2 is required. The IRA Deduction Worksheet puts wages on line 8 and self-employment earnings on line 9.

**What the software does.** The wages count once, as wages on line 8, and line 9 leaves them out. That mirrors AD-30, which places a minister's dual-reported W-2 salary the same way under IRC 219.

This is a separate concept from CR-09. CR-09 keeps the same pay in self-employment earnings, following a printed EIC instruction under IRC 32(c)(2). The two statutes define different amounts, so the placement is one per statute, and the difference is deliberate.

One question stays open together with AD-30's: whether the wage share of the half-SE-tax deduction also reduces other self-employment earnings. It is moot when the filer has no other self-employment income.

**Why the owner chose it.** It follows the IRA statute's own definition and the record's existing IRC 219 placement (AD-30). Both independent derivations reached this reading. Direction: at most the half-SE-tax share more deduction than the alternative, and only when compensation binds. The product owner delegated the call on 2026-10-04, as for IN-301 and IN-302.

### IN-309 — IRC 219(f)(6): a prior-year excess deducted this year, with Roth contributions under the phaseout (ruled 2026-10-04, provisional)

**The statute.**
- IRC 219(f)(6)(A) treats a prior-year excess as contributed this year, up to the excess of "the maximum amount allowable as a deduction under this section" over "the amount contributed". IRC 219(g)(1) phases that maximum for an active participant.
- IRC 219(f)(6)(B) defines "amount contributed" with no Roth clause, and IRC 219(b)(1) is never reduced by Roth contributions.
- The act that added "(including the amount contributed to a Roth IRA)" placed it in IRC 4973(b)(2)(C) only, the excise-absorption room, which the flush sentence computes "without regard to section 219(g)". IRC 408A(c)(2) reduces the Roth limit by traditional contributions, never the reverse.

**What the software does.** Let E be the prior-year excess, P the phased limit, U the unphased limit, K the traditional contributions and R the Roth contributions.
- **Deemed contribution.** The least of E, P − K, and U − K − R.
- **Remainder.** Any amount the excise room absorbs but the phased room does not deduct becomes Form 8606 line 1 basis (Q11), not a carried excess.
- **Where Roth enters.** Roth contributions reduce the room only through the excise cap U − K − R, which is exactly where the statute puts them.

Pub. 590-A Worksheet 1-5 and the Form 5329 line 10 / IRA Deduction Worksheet line 11 bridge reach the same result. The literal reading that subtracts Roth contributions from the phased room (P − K − R) is rejected: no text makes Roth contributions consume phased deduction room.

**Why the owner chose it.** It reads the statute's own placement of Roth, and the two IRS computations corroborate it. It is marked provisional because no source addresses this exact combination. The facts it governs carry an `interpretation:provisional` tag. Direction if wrong: an over-deduction of up to the Roth amount, for a very small population. The product owner delegated the call on 2026-10-04, as for IN-301 and IN-302.

#### IN-309 amendment — Roth contributions do not cap the section 219(f)(6) deduction (2026-10-06; reverses the provisional cap)

**The statute is clear.** IRC 219(f)(6)(A) deems the lesser of two amounts contributed (26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section219&num=0&edition=2024):
- (i) the excess of "the maximum amount allowable as a deduction under this section" over "the amount contributed";
- (ii) "the amount of the excess contributions for such taxable year (determined under section 4973(b)(2) **without regard to subparagraph (C) thereof**)".

Subparagraph (C) of IRC 4973(b)(2) is the only place Roth contributions enter, "(including the amount contributed to a Roth IRA)" (26 U.S.C. 4973, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section4973&num=0&edition=2024). Clause (ii) excludes it by name. IRC 219(f)(6)(B) defines "amount contributed" with no Roth clause. Pub. 590-A (2025) Worksheet 1-5 subtracts only traditional contributions (https://www.irs.gov/pub/irs-pdf/p590a.pdf, page 36). The Instructions for Form 5329 (2025), line 10, subtract Roth contributions too and carry that amount to the IRA Deduction Worksheet (https://www.irs.gov/pub/irs-pdf/i5329.pdf, page 6). Under the standing rule, an instruction yields where the statute is clear.

**Decision. Two quantities that the 2026-10-04 text conflated are now kept apart.** As before, E is the prior-year excess, P the phased limit, U the unphased limit, K the traditional contributions and R the Roth contributions.
- **The deduction, IRC 219(f)(6):** the lesser of P − K and E′, never below 0. E′ is the prior-year excess reduced only by the IRC 4973(b)(2)(A) and (B) distributions, so its Roth room is never subtracted. Roth contributions never reduce it.
- **The excise absorption, IRC 4973(b)(2)(C), Form 5329 line 10:** U − K − R, Roth included. This is unchanged.

The two can now differ. When Roth contributions use up the excise room, the deduction can exceed what Form 5329 line 10 absorbs. Part of the prior-year excess then stays an excess on Form 5329 while also being deducted, which is what the statute produces.

The remainder rule above (Q11) is unchanged in substance. An amount absorbed by the excise room but not deducted becomes Form 8606 line 1 basis. Under the split it arises only when the phased room is smaller than the excise room.

**Why.** The 2026-10-04 entry correctly placed Roth contributions in IRC 4973(b)(2)(C), then applied that room to the deduction anyway. That is the error corrected here.

Direction: the old reading under-deducted, by up to the Roth amount, for filers whose Roth contributions use up the excise room. Raised by verify row FED-1040-IRADED-F6ROTHCAP-039, refuted at two earlier pins and sustained at the third. Research covered the statute, Pub. 590-A and the Form 5329 instructions; the advisor was consulted. This reverses a provisional ruling, under the product owner's delegation of 2026-10-05 ("even for IN-*, the previous ruling").

### Rulings of 2026-10-05: Schedule C and Form 1099-R (IN-310 onward)

These entries were ruled under the product owner's delegation of 2026-10-05: "use research, advisor for the best decisions, even for IN-*, the previous ruling. no need to ask". Each one rests on a read-only research memo checked by an independent advisor. Each follows the standing rule that the statute governs where it is clear and a form or publication never overrides it. The package author and the blind meaning reviewer derived the underlying obligations independently, from sources only.

#### IN-310 — Form 8829 lines 6 and 7: the exact ratio

IRC 280A(c)(4)(C) limits a daycare provider's deduction to "an amount which bears the same ratio" as the hours of use to the hours available. A rounded-up percentage can exceed that cap; the exact ratio cannot. Form 8829 sets no precision. Pub. 587 (2025)'s printed 17.12% and 17.86% are the exact ratio shown to two decimals. **Decision:** the ratio is used exact, never as a rounded percentage. **Example:** Pub. 587's Rene example comes to 1,755.13 rather than 1,754.85.

#### IN-311 — Form 8829 line 33: casualty before depreciation

Pub. 587 (2025) deducts the otherwise nondeductible expenses "with depreciation of your home taken last". Its worksheet line 33 is "the total of the casualty losses shown on lines 10 and 31", so the casualty share of a line 31 carryover matters whenever line 31 is above $0.

**Decision.**
- **Order:** casualty losses first, current and carried; depreciation last.
- **Carryover:** the casualty part of a line 31 carryover is an "only if any" amount (IN-296), so a blank reads $0.

**Example:** line 28 = 1,000, line 29 = 600 and line 30 = 1,500. Line 35 is 600, and the 1,100 carryover is all depreciation.

#### IN-312 — Section 179 and the home-office limit: Pub. 946's eight steps

Each limit depends on the other. IRC 179(b)(3)(C) figures business income before section 179 only, so the home-office deduction reduces it. IRC 280A(c)(5)(B)(ii) subtracts the business's other deductions, section 179 included. The Instructions for Form 4562 (2025) send this case to Pub. 946: "If you have to apply another Code section that has a limitation based on taxable income, see Pub. 946".

**Decision:** Pub. 946's eight-step procedure, with Form 8829 line 36 (or simplified line 5) as the other deduction. It is a fixed sequence, not an iteration.

**Example:** section 179 allowed is 14,000 rather than 20,000, the carryover is 11,000 rather than 5,000, and Schedule C line 31 is 0 rather than −6,000.

#### IN-313 — Community income and self-employment tax

IRC 1402(a)(5)(A) gives self-employment income from community property to the spouse who carries on the business, or by distributive shares when both spouses operate it, whatever the filing status. The Schedule SE instructions say the same when both spouses participate. Pub. 555 says registered domestic partners report self-employment income "the same way they do for income tax purposes". IRC 66(a) reaches IRC 1402(a)(5) through IRC 879(a)(2).

**Decision.**
- **Separate returns:** the add-back is built for a business one spouse carries on.
- **Registered domestic partners:** no add-back.
- **IRC 66(a):** no add-back, because the income and self-employment splits already agree.
- **IRC 66(b):** follows IN-55; no question is asked.
- **Amended 2026-10-05:** a business both spouses operate splits self-employment income by their distributive shares on any filing status. That applies even when a joint return reports the business on one Schedule C. Each spouse's Schedule SE line 2 takes that spouse's share. The intake asks whether both spouses participated and asks the share; an unanswered share then holds.
  - The current computation stands until that repair lands. Its witness (about $3,436 of self-employment tax under-charged on the example) stays red meanwhile.

#### IN-314 — Simplified method: 300 square feet per spouse

Rev. Proc. 2013-13 section 4.08(5): spouses, "regardless of filing status", may "each use the safe harbor method ... for up to 300 square feet of different portions of the home". **Decision:** each spouse has their own 300 square foot cap, and shared space is not counted twice. **Example:** each spouse uses 250 square feet, giving $2,500 in total rather than $1,500 under one shared cap.

#### IN-315 — A Schedule C excluded under IRC 933 (provisional)

IRC 933(1): the income "shall not be included in gross income". Pub. 570 (2025)'s worked example counts only non-excluded income as gross income. Schedule 1 has no IRC 933 offset line.

**Decision:** the Schedule C is computed and attached, feeding Schedule SE line 2 and Form 7206 (AD-32). Its line 31 is left off Schedule 1 line 3.

It is provisional, because no source states the presentation outright; AGI and tax are the same either way.

#### IN-316 — Section 195: an unanswered election means the deduction is taken

IRC 195(b) allows the deduction "if a taxpayer elects". Pub. 535 says no statement is needed; the filer forgoes the deduction only "by affirmatively electing to capitalize". The Instructions for Form 4562 (2025) agree that a statement is "not required".

**Decision:** an unanswered election means the deduction is taken. This matches IN-287: an affirmative act left unanswered is not taken.

**Example:** $20,000 of start-up costs for a business begun in July 2025 gives 5,000 + 15,000 × 6/180 = $5,500 deducted.

#### IN-317 — Daycare direct expenses: the time ratio

The statute caps these expenses by the time ratio (IRC 280A(c)(4)(C)), and Pub. 587 (2025) applies it to Rene's painting. The Form 8829 instruction to "Enter 100% of your direct expenses" chooses the column; it does not lift the cap. **Decision:** the ratio applies. This confirms the build and IN-182.

#### IN-318 — Section 179 active conduct when line G is No

Active conduct means meaningful participation, a lower bar than material participation (Instructions for Form 4562 (2025)). **Decision:**
- **Line G Yes:** implies active conduct; no question is asked.
- **Line G No with a section 179 election:** a meaningful-participation question is asked, and unanswered holds (the IN-289 pattern).

#### IN-319 — QCD from a SEP or SIMPLE IRA

IRC 408(d)(8)(B) excludes a "plan described in subsection (k) or (p)". IRC 408(k)(2) makes SEP status year by year: it is "satisfied ... for a year only if for such year the employer contributes". Pub. 590-B (2025) and the Form 1040 instructions exclude only an "ongoing" SEP or SIMPLE IRA, a term Pub. 590-B defines for the same wording in the HSA funding rule.

**Decision:** only an ongoing plan, one with an employer contribution for the year, is excluded.

Confidence is medium-high for a SEP and medium for a SIMPLE, because IRC 408(p) has no year-by-year wording. **Example:** an $8,000 QCD is excluded rather than taxable.

#### IN-320 — Terminal illness on a code 1D form

IRC 72(q)(2) lists no terminal-illness exception. That exception is IRC 72(t)(2)(L), which reaches only qualified plans. Pub. 575 (2025) lists terminal illness among its general exceptions, but its own paragraph limits it to "a distribution from a qualified retirement plan". **Decision:** the 10% additional tax applies to a nonqualified annuity. **Example:** an $8,000 taxable amount gives $800 on Form 5329 line 4.

#### IN-321 — Simplified Method table: completed years

The statute's bands are "Not more than 55 / More than 55 but not more than 60". The IRS tables print whole ages, and where the Code means a half year it says so (59 1/2). **Decision:** age at the annuity starting date is taken in completed years, so age 55 1/2 uses 360 payments.

#### IN-322 — Exception 16 for IRC 72(q)(2)(G), (I) and (J)

The Form 5329 instructions' entry for exception 16 continues: "For additional exceptions that apply to annuities, see ... Pub. 575". That Pub. 575 list is exactly clauses F, G, I and J, and Pub. 575 says to use the Form 5329 number. **Decision:** exception 16 (print only).

#### IN-323 — A QCD above the ceiling when the owner has basis

IRC 408(d)(8)(D) treats the whole charitable distribution as taxable first, "notwithstanding section 72". The amount above the ceiling is still a qualified charitable distribution by definition; the ceiling only limits the exclusion. **Decision:** the excess is fully taxable and stays off Form 8606 line 7 (consistent with IN-230). **Example:** $12,000 taxable rather than $11,436; the difference is preserved as basis.

#### IN-324 — Public safety officer premiums

In every 2025 case, Form 1040 line 5b is the same under the instructions and under IRC 402(l)(3)(B). The two differ only in how much cost counts as recovered for later years. **Decision:** follow the instructions for every 2025 line. The statute's "proper adjustments" in later years are recorded as not modelled.

#### IN-325 — The line 4c statement: per return

Lines 4b and 4c are return-level lines, and the instruction says "applies to you". **Decision:** exceptions are counted per return (print only).

#### IN-326 — A 2025 Form 1099-R coded JP

The Instructions for Form 8606 (2025) say "don't report the distribution on your 2025 tax return" for a returned Roth excess, and the statute puts the earnings in the contribution year. **Decision:** the form is left off 2025 line 4a (print only).

#### IN-327 — The QCD age date (provisional)

IRC 408(d)(8)(B)(ii) says "on or after the date" the owner attains 70 1/2. Treas. Reg. 1.401(a)(9)-6 places 70 1/2 six calendar months after the 70th birthday. The project's age-59 1/2 ruling of 2026-09-10 already uses this rule.

**Decision:** 70 1/2 is the date six calendar months after the 70th birthday, or the last day of that month when that day does not exist. The QCD is computed, not refused. The dictionary's existing "age attained" concept is reused, not redefined.

- **Date answer:** Form 1099-R carries no distribution date, so births from July 2, 1954 through June 30, 1955 need a date answer.
- **Why provisional:** the regulation is applied by analogy.

**Example:** born June 30, 1955, a $10,000 QCD on December 30, 2025 is excluded rather than refused.

#### IN-328 — Form 8880 line 4: a beneficiary's distribution

IRC 25B(d)(2) counts distributions from entities to which contributions may be made. No contribution or rollover may go into a non-spouse inherited IRA, so that IRA is not such an entity. A surviving spouse's is. The statute's "not the surviving spouse" matches the form's "nonspousal".

**Decision:**
- **Counting:** a surviving spouse beneficiary's distribution counts on line 4; a non-spouse beneficiary's does not.
- **The question:** asked only when Form 8880 is in play and an IRA code 4 form exists; unanswered holds (GEN-01).

Today every code 4 form is excluded, which over-credits a spouse beneficiary.

**Also decided (2026-10-05, completing research item 5):**
- **A QCD counts on line 4.** IRC 25B(d)(2)(A) counts distributions from the listed plans and excepts only a closed list of rolled-over, transferred and corrective amounts, and a QCD is not on that list. A distribution excluded from income is still "received" (example: a $1,000 QCD reduces a $200 credit to $100).
- **Military retirement pay does not count,** as the Form 8880 instructions say. It is not a distribution from a plan listed in IRC 25B(d)(2). The form's exclusion is applied; no vendored text states its reason.
- **A section 408(d)(5) return counts.** IRC 25B(d)(2) excepts only section 408(d)(4) returns, and the form's "excess contributions or deferrals" item matches the statute's corrective terms.

#### IN-329 — Form 1099-NEC above Schedule C line 1

The Instructions for Schedule C (2025) say only "attach a statement explaining the difference". Nothing treats the difference as income. **Decision:** the return computes from line 1 as entered; the explanation statement is required, and an unanswered statement holds the return (GEN-01).

#### IN-330 — A positive section 481(a) adjustment

The Instructions for Schedule C (2025) say the adjustment is taken in "generally ... over a period of 4 years". The authority for that ratable period (Rev. Proc. 2015-13 section 7.03) is not vendored.

**Decision:** the filer enters this year's portion on line 6, as a filer figure (the S604/IN-91 pattern). There is no computed spread and no hold.

#### IN-331 — How the nondeductible election is expressed

**The statute.** IRC 408(o)(2)(B)(ii) lets an individual elect to treat contributions as nondeductible. IRC 408(o)(2)(C)(ii) makes the designated nondeductible contribution the amount so designated.

**The IRS text.** The Instructions for Form 8606 (2025), Line 1, subtract "line 12 of the worksheet (or the amount you chose to deduct on Schedule 1 (Form 1040), line 20, if less)". The Form 1040 instructions let a filer "deduct a smaller amount and treat the rest as a nondeductible contribution".

**Decision.**
- **A designation alone is the election.** With no elected-deduction amount, the deduction taken is the lesser of the allowable deduction and (min(compensation side, contributions + deemed amount) − designation), never below zero. This is the Form 8606 line 1 relation solved for the deduction. A designation therefore first absorbs any part the phaseout has already made nondeductible. Example: 7,000 contributed, 2,800 deductible after the phaseout, 4,200 designated gives a deduction of 2,800, not 0. The deduction falls below the allowable amount only by the excess of the designation over that already-nondeductible part (corrected 2026-10-05).
- **An elected deduction is the other expression.** An elected-deduction amount says the same thing from the other side.
- **Both given:** they must agree within $1, or the return is refused with a reason. This rests on the project rule against resolving conflicting filer entries (FACT-SKILL-1 §2.4b), not on tax law.
- **Neither given:** the full allowable deduction is taken.
- **The upper bound:** a designation above the most that can be designated, min(compensation side, contributions + deemed amount) per the IN-304 amendment, is refused (the $100 over-designation penalty, IRC 408(o)(4)).
- **What the designation is:** Form 8606 line 1 keeps its meaning as the whole printed line, including any qualified reservist repayment. The designation is line 1 less the repayment, never below zero.

**Superseded expectations.**
- **A 500 contribution with a 500 designation:** now files with deduction 0. The old expectation was deduction 500 and a refusal.
- **A designation $1 over the old default ceiling (primary and spouse):** now reduces the deduction by $1 and files. A designation $1 over the most that can be designated still refuses.
- **A spouse who deducted 5,000 and designated 1,000 of the same 5,000:** now deducts 4,000, and the other spouse's §219(c) leg is 5,000. The old expectation counted both, a double count.

**Direction if wrong.** A filer who mis-entered line 1 loses deduction silently where the old convention refused. That is the trade made.

**Why.** The instructions build line 1 from the deduction chosen, and the statute makes the designation the election. The package author derived the rule from sources and the repair seat surfaced the conflicting tests. The independent advisor check sustained the rule and added the upper bound. Ruled under the product owner's delegation of 2026-10-05.

**Open presentation question (not ruled).** Form 1040 line 5a with mixed fully and partly taxable pensions keeps the dictionary's documented convention. The instructions point both ways, and the e-file business rules that would settle it are not vendored.

#### IN-332 — Section 179 and home offices across several businesses (extends IN-312)

**The statute and IRS text.**
- **The §179 limit is per taxpayer.** It is "aggregate amount of taxable income ... from the active conduct ... of any trade or business" (IRC 179(b)(3)). Pub. 946 (2025) says it applies to "each taxpayer, not to each business", "totaling the net income and losses from all trades and businesses". Wages count in that income (Instructions for Form 4562 (2025)).
- **The home-office limit is per business.** It subtracts "the deductions allocable to the trade or business ... in which such use occurs" (IRC 280A(c)(5)(B)(ii)).
- **Allocation is the filer's.** The filer "may allocate" the allowable section 179 deduction among businesses (Instructions for Form 4562, Summary). Without a selection, "the total carryover will be allocated equally among the properties you elected to expense" (Pub. 946 (2025)).

**Decision.**
- **Two kinds of income.** Pub. 946's steps 1, 5 and 7 use aggregate income: every business plus wages, before section 179 and before every home office. Steps 4 and 8 use each home-office business's own Form 8829 line 8, less that business's share of the hypothetical or actual section 179 amount.
- **Allocation when the income limit binds.** The filer's selection governs. An unanswered selection computes on Pub. 946's equal-per-property default and does not hold, because the publication states the default (the IN-316 pattern).
- **No binding limit.** Each business takes its own elected cost, so there is nothing to allocate.

**Provisional parts.**
- Applying the carryover default to the hypothetical step 2 as well as step 6 is this entry's reading.
- When an equal share exceeds a property's elected cost, the share is capped at that cost and the excess spread equally over the rest. No vendored text addresses this case (Treas. Reg. 1.179-3(e) is not vendored).

**Direction if wrong.** The total of all lines 31 is usually unchanged. What moves is the split between Form 4562 line 13 and the Form 8829 carryovers, and each business's line 31. That matters for self-employment tax when the businesses belong to different spouses, and for QBI, at-risk and passive rules.

**Example.** Business A has 20,000 of income and 12,000 elected; business B has 4,000 of income and 18,000 elected. A has a home office with 9,000 of Form 8829 operating expenses and no tier-1 amounts; there are no wages.
- **Default allocation:** section 179 is 15,000, A's line 31 is 6,500 and B's is −6,500.
- **Filer carries B's property forward:** section 179 allowed is 16,000, and 14,000 (all B's property) carries forward on Form 4562 line 13. Both lines 31 are 0, and the Form 8829 carryover is 1,000.
- **Clarification (2026-10-05): a home used by several businesses.** "Each business's own Form 8829 line 8" means the line 8 of the Form 8829 for that home. The instructions fill it from "Schedule(s) C, line 29" for the businesses that use the home (Instructions for Form 8829 (2025), line 8, https://www.irs.gov/pub/irs-pdf/i8829.pdf, page 2). So steps 4 and 8 run once per Form 8829. They use that form's line 8, reduced by the section 179 share of every business that uses the home. The IN-295 allocation of line 36 among those businesses then follows. A business with no home office takes no part in steps 4 and 8. Found by the Schedule C delta reviewer (scheduleC-R1D, R1D-M-04).
- **Erratum (2026-10-05):** the first text of this example gave "section 179 is 14,000" for the second bullet. That figure is the carryover. Both lines 31 at 0 with a 1,000 Form 8829 carryover force 24,000 − 8,000 = 16,000 allowed. The home-office facts were added so the example can be checked. Found by the Schedule C source author (scheduleC-S1 revision 3).

#### IN-333 — Section 195 start-up costs in the year the business is disposed of

**The statute.** If the business is "completely disposed of ... before the end of the period", the remaining deferred expenses become deductible "to the extent allowable under section 165" (IRC 195(b)(2)). IRC 165(c)(1) allows losses "incurred in a trade or business".

**Decision.**
- **The 2025 total.** It is the unamortized balance on January 1 under every month convention.
- **What the ruling decides.** Only the split between them: Form 4562 Part VI amortization runs through the month of disposition, mirroring the inclusive beginning month in IRC 195(b)(1)(B), and the remainder is an ordinary deduction.
- **Where the remainder goes.** Schedule C line 27b, through Part V. That is a presentation convention; no source names the line.
- **Scope.** "Completely disposed of" excludes partial disposals and temporary closings.

**Open (not ruled).** On a sale, it is unsettled whether IRC 165(a)'s "compensated for ... otherwise" lets the proceeds absorb part of the balance. If so, that part would reduce gain on Form 4797 instead of being deducted on Schedule C. This entry covers a cessation.

**Example.** 23,000 of costs, begun January 2023, 100 a month after a 5,000 first-year amount, ceasing June 30, 2025. The 2025 total is 15,600, made of 600 of amortization and 15,000 released.

#### IN-334 — Section 195 for a business reopened in 2025 (provisional in part)

**The statute.** The first-year amount belongs to "the taxable year in which the active trade or business begins". Amortization runs over 180 months "beginning with the month in which the active trade or business begins" (IRC 195(b)(1)). Reopening costs do not create "an active trade or business" (IRC 195(c)(1)(A)(ii)). The Schedule C instructions say "If your business began in 2025".

**Decision.**
- **"Began" means when the business first operated,** not when it reopened. A business reopened in 2025 gets no 2025 first-year amount.
- **Reopening costs** are current expenses of the existing business, entered on their own lines.
- **The intake** separates "the same business resumed" from "a new business begun in 2025 after the old one was completely disposed of". Only the second gets a new first-year amount, and its disposal releases the old balance under IN-333.
- **Provisional:** a temporary closing does not suspend the 180-month period, and a business reopened during 2025 takes all 12 months. Both rest on the statute's fixed period; nothing vendored addresses dormant periods.

**Example.** A business begun May 2019 (a 15,000 remainder) and reopened in February 2025: the first-year amount is 0, amortization is 1,000.00, and 3,000 of reopening advertising is a current expense.


#### IN-335 — Form 4972 lines 24 and 27: whole dollars before the ×10 (2026-10-05)

**The form.** Line 24 is "Tax on amount on line 23. Use the Tax Rate Schedule in the instructions", and line 25 says "Multiply line 24 by 10.0". Lines 27 and 28 are the same pair for line 26 (Form 4972 (2025), https://www.irs.gov/pub/irs-pdf/f4972.pdf, page 1). The schedule's base amounts carry cents ($130.90, $260.50 and so on), so the tax on line 23 can end in cents. Neither the form nor its instructions says whether line 24 is entered in cents. The only rounding text on the form is line 20's decimal "rounded to at least three places", a ratio.

**The general rule.** "You can round off cents to whole dollars on your return and schedules. If you do round to whole dollars, you must round all amounts ... $2.50 becomes $3" (Instructions for Form 1040 (2025), Rounding Off to Whole Dollars, https://www.irs.gov/pub/irs-pdf/i1040gi.pdf, page 23).

**Decision.**
- Every printed Form 4972 dollar line is in whole dollars, the IN-307 pattern for Schedule SE.
- Line 24 (and line 27) is figured to the cent from the schedule, then rounded half-up.
- Line 25 (and line 28) multiplies the printed, rounded amount by 10.
- The other multiplication lines (7, 13, 15, 21, 23, 26) are likewise figured to the cent and the printed line rounded.

This is a consumer of IN-307's shared rounding convention, not a new definition.

**Effect.** At most $5 on lines 25 and 28, and through them on lines 29 and 30. Example: a line 24 tax of $1,270.50 prints as $1,271, so line 25 is $12,710, not $12,705.

**Superseded expectations.** Package cases or fixtures that carry line 24 in cents (for example 1,270.50 → 12,705) are superseded by this entry. Retire them with a "superseded by IN-335" header and write replacements; do not edit them in place. A gap larger than rounding, such as the capital-gain-election case, is a separate defect.

**Why.** The form gives no cents instruction for this line. The house already prints whole dollars on every line it rounds (IN-285, IN-307), and the Form 1040 rule requires rounding all amounts once any are rounded. Raised by the Form 1099-R repair seat (1099R-I1) on translation-review finding R2T-15. Research: Form 4972 (2025) and its instructions, the Form 1040 instructions; advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### IN-336 — a payment to an inherited IRA is an excess contribution (2026-10-05)

**The statute.**
- **No deduction.** "No deduction shall be allowed under this section with respect to any amount paid to an inherited individual retirement account or individual retirement annuity" (IRC 219(d)(4), 26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section219&num=0&edition=2024).
- **Excess contributions.** These are "(A) the amount contributed for the taxable year to the accounts ... (other than a contribution to a Roth IRA or a rollover contribution ...), over (B) the amount allowable as a deduction under section 219 for such contributions" (IRC 4973(b)(1), 26 U.S.C. 4973, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section4973&num=0&edition=2024).

**Decision.**
- **The whole payment is excess.** New money a non-spouse beneficiary pays into an inherited IRA is an amount contributed, and its allowable amount is $0. It enters Form 5329 line 15, and the 6% tax on line 17 applies.
- **Mixed contributions.** With own and inherited contributions in one year, only the inherited payment is denied; the own contribution keeps its own allowable amount.
- **Prior-year excess and §219(f)(6).** The same phrase "amount contributed ... to the accounts" appears in IRC 4973(b)(2)(C) and IRC 219(f)(6)(A). So the payment also reduces the room that absorbs a prior-year excess and the deemed-contribution room. No case asserts this yet.
- **Transfers are not contributions.** A trustee-to-trustee transfer of the decedent's balance into an inherited IRA is not a contribution. The question and its card must ask for new money paid in, not for the amount in or moved to the account.
- **Blank amount.** If the amount is unanswered after a yes answer, the deduction and lines 15-17 hold (lead, 2026-10-05; the GEN-01 pattern).

**The IRS text.** The Instructions for Form 5329 (2025), lines 15-16, measure the excess "over the contribution limit" (https://www.irs.gov/pub/irs-pdf/i5329.pdf, pages 6-7). That is a simplification of the statute, of the same kind as the Form 1040 line set aside in IN-303. Pub. 590-B says a beneficiary "can't make any contributions" to an inherited IRA. That supports this reading: such a payment is the clearest case of an excess contribution.

**Superseded behavior.** The engine's current reading measures against the general contribution limit. In the mixed case it gives a line 15 of 2,000 and a line 17 of 120. This entry replaces that behavior with 3,000 and 180 (verify row FED-1040-IRADED-INHERITED-006).

**Why.** The statute is clear and the standing rule is that the statute governs. Research by ira-S1 (Q14); advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### IN-337 — the 25% base of IRC 219(b)(3)(B) (2026-10-05; provisional in part)

**The statute.**
- **The limit.** The 501(c)(18) deduction may not exceed 25% of "the compensation (as defined in section 415(c)(3)) includible in the individual's gross income" (IRC 219(b)(3)(B)).
- **The §415 definition.** Section 415(c)(3)(A) defines "the compensation of the participant from the employer for the year" (26 U.S.C. 415, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section415&num=0&edition=2024).
- **IRC 219(f)(1).** It widens "compensation" "for purposes of this section" with alimony and earned income.
- **IRC 219(f)(7).** It restores combat pay only for subsection (b)(1)(B) and subsection (c).

**Decision.**
- **The base.** It is section 415(c)(3) compensation includible in gross income, not the section 219(f)(1) IRA compensation.
  - Subsection (b)(3)(B) names its own definition by cross-reference, which displaces the section-wide (f)(1) widening.
  - Section 219(f)(7) lists where the combat-pay override reaches, and (b)(3) is not on the list.
- **What is out.** Combat pay, taxable alimony and non-wage stipends are outside the base. The section 415(c)(3)(D) elective deferrals are also out, because (b)(3)(B) adds "includible in gross income". So W-2 box 1 governs.
- **What follows from the allowed amount.** The law-correct Schedule 1 line 24f entry and the line 24f refusal (card 1346) both follow the allowed amount.

**Provisional: which employer.** The base is the box 1 wages of the W-2s that report code H, meaning the employer that maintains the plan. Several such W-2s are added together. Wages from an employer without code H do not count. Treas. Reg. 1.415(c)-2 is not vendored, and no vendored text addresses several employers. If this is wrong, the base would be all wages: a larger allowed amount for a filer with a second job. The section 401(c)(1) substitution in section 415(c)(3)(B) does not apply, because 501(c)(18) plans are employee plans.

**Clarifications (lead, 2026-10-05, on ira-I1's repair).**
- A W-2 whose code H amount is $0 is not the plan employer's W-2.
- Box 1 wages excluded under IRC 931 or 933 are not "includible in gross income", so they come out of the base.

- **Box 11 is outside the base (provisional).** Box 11 nonqualified deferred compensation included in box 1 comes out of the base. Section 219(f)(1) excludes "any amount received as deferred compensation" from compensation. The 415(c)(3) regulation that would settle this for subsection (b)(3) (Treas. Reg. 1.415(c)-2) is not vendored, so the exclusion is provisional. If wrong, the allowed 501(c)(18) amount would be larger for a filer with box 11 amounts. Found by the build-side challenge (ira-CH UNC-2).
- **Section 911 wages are outside the base.** Foreign earned income excluded under IRC 911 is not includible in gross income, so it comes out of the base. This is unreachable today, because Form 2555 returns are refused. Record it for when that refusal retires (ira-CH UNC-1).

**Why.** Statute text. Research by ira-S1 (Q15, Q16); advisor consulted. The call was delegated by the product owner on 2026-10-05. Verify row FED-1040-IRADED-501C18BASE-038.

#### IN-338 — the spousal limit, term (I) (2026-10-05)

**The statute.** The spouse's compensation is reduced by "(I) the amount allowed as a deduction under subsection (a) to such spouse for such taxable year" (IRC 219(c)(1)(B)(ii)(I)).
- **501(c)(18).** Subsection (a) allows a deduction for qualified retirement contributions, and these include section 501(c)(18) contributions (IRC 219(e)(2)).
- **§219(f)(6).** It treats the taxpayer "as having made an additional contribution for the taxable year" (26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section219&num=0&edition=2024), and that contribution's deduction is allowed under subsection (a).

**Decision.** Term (I) is the spouse's whole section 219(a) deduction:
- the IRA deduction, including any section 219(f)(6) amount;
- plus the spouse's allowed 501(c)(18) deduction.

The higher earner's own IRA deduction is the lesser of the dollar limit and compensation, less the 501(c)(18) deduction (IN-301).

**Why.** Statute text; low dispute. Research by ira-S1 (Q17); advisor consulted. The call was delegated by the product owner on 2026-10-05. Verify row FED-1040-IRADED-KBH-005.

#### IN-339 — a QCD reduced by the post-70½ deduction offset is still reported under Exception 3 (2026-10-05)

**The statute.** IRC 408(d)(8)(A) (26 U.S.C. 408, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section408&num=0&edition=prelim) excludes qualified charitable distributions from gross income. The amount excluded "shall be reduced (but not below zero)" by the post-70½ IRA deductions not already used. Section 408(d)(8)(B) defines a "qualified charitable distribution" by how it is made (directly by the trustee, to an eligible organization, and so on). The offset reduces only the amount excluded. It does not change whether the distribution is a QCD.

**The IRS text.**
- Exception 3 of the Instructions for Form 1040 (2025), lines 4a and 4b (https://www.irs.gov/pub/irs-pdf/i1040gi.pdf, page 27): "If all or part of the distribution is a qualified charitable distribution (QCD), enter the total distribution on line 4a ... Check box 2 on line 4c." Its "-0- on line 4b" text assumes the whole QCD is excluded.
- Pub. 590-B (2025), Jim's example (https://www.irs.gov/pub/irs-pdf/p590b.pdf, pages 14-15), shows a QCD with "no excludable qualified charitable distribution" for 2025.

**Decision.** A distribution that meets section 408(d)(8)(B) is reported under Exception 3 even when the offset reduces its exclusion, in part or in full:
- line 4a is the total distribution;
- line 4b is the amount includible after the offset (in Jim's 2025 case, the whole 6,000), not -0-;
- box 2 on line 4c is checked.

The "fully taxable, no entry on line 4a" rule does not apply, because the distribution is a QCD, and Exception 3 is the specific rule for one.

**Why.** Statute text. Raised by form1099Rs-S1 (Q-r3-2); the call was delegated by the product owner on 2026-10-05.

#### IN-340 — a Roth contribution returned by the due date, in spousal term (III) (2026-10-06)

**The statute.**
- **Term (III).** The spouse's compensation is reduced by "(III) the amount of any contribution on behalf of such spouse to a Roth IRA" (IRC 219(c)(1)(B)(ii)(III), 26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section219&num=0&edition=2024).
- **Section 408(d)(4)** only switches off section 408(d)(1), the inclusion in gross income, for a contribution returned with its earnings by the due date.
- **Section 4973's flush sentence** treats such a contribution "as an amount not contributed", but only "for purposes of this subsection" (26 U.S.C. 4973, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section4973&num=0&edition=2024).
- **Section 408A** has no rule on returned contributions. Its (d)(6) addresses trustee-to-trustee transfers, the recharacterizations (26 U.S.C. 408A, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section408A&num=0&edition=2024).

So no statute decides whether a returned Roth contribution is "any contribution" for term (III).

**The IRS text.**
- **Instructions for Form 8606 (2025), Return of IRA Contributions:** "the returned contributions are treated as if they were never contributed", with no restriction of purpose (https://www.irs.gov/pub/irs-pdf/i8606.pdf, page 7).
- **Pub. 590-A (2025)** gives the same treatment "for purposes of determining excess contributions" (https://www.irs.gov/pub/irs-pdf/p590a.pdf, page 43).

**Decision.** A Roth contribution returned with its earnings in a section 408(d)(4) distribution by the due date is not counted in term (III). The statute is silent on the point, so the standing rule that the statute governs has nothing to follow, and the IRS instruction's unrestricted reading governs. The amount is the returned contribution, capped at the Roth contribution answered.

**Scope.** Two other uses of the same returned amount rest directly on IRC 4973(b)'s flush sentence and need no ruling. That sentence reads: "For purposes of this subsection, any contribution which is distributed ... in a distribution to which section 408(d)(4) applies shall be treated as an amount not contributed" (26 U.S.C. 4973, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section4973&num=0&edition=2024). IRC 4973(f)'s flush sentence governs only Roth excess contributions under subsection (f). The two uses are:
- Form 5329 line 10;
- the section 219(f)(6) excess-absorption room.

This entry decides term (III) only.

**Direction if wrong.** If returned contributions still count in term (III), the other spouse's spousal limit is too large by the returned amount. That person is under-charged, but only when the spousal limit binds.

**Why.** It records the reading the implementation already follows (round 3, `740b641b60`). That reading is now challenged by verify row FED-1040-IRADED-ROTHRETURNED-041, sustained because no canonical entry recorded it. Research: the statute, section 408A and Pub. 590-A. Advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### IN-341 — IRC 219(f)(6)(C): the closed-year reduction comes off the deemed deduction, not the room (2026-10-06)

**The statute.**
- **The deemed contribution.** IRC 219(f)(6)(A) treats the filer as contributing "the lesser of" (i) the excess of the maximum deductible amount over the amount contributed and (ii) the prior-year excess contributions determined under IRC 4973(b)(2) without its subparagraph (C) (26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section219&num=0&edition=prelim).
- **The reduction.** "Proper reduction shall be made in the amount allowable as a deduction by reason of this paragraph for any amount allowed as a deduction under this section for a prior taxable year for which the period for assessing deficiency has expired if the amount so allowed exceeds the amount which should have been allowed for such prior taxable year" (IRC 219(f)(6)(C), 26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section219&num=0&edition=prelim).
- **Why the reduction is needed.** IRC 4973(b)(1) measures an excess against "the amount allowable as a deduction under section 219", not the amount allowed (26 U.S.C. 4973, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section4973&num=0&edition=2024). An excess wrongly deducted in a year now closed therefore stays in the carried excess. Without subparagraph (C), IRC 219(f)(6) would deduct it a second time.

**The IRS text.** Pub. 590-A (2025) says the deduction for the correction year "must be reduced by the amount of the excess contribution deducted in the closed year" (https://www.irs.gov/pub/irs-pdf/p590a.pdf, page 38). Its Worksheet 1-6 then subtracts that amount from the maximum deduction before measuring the room, and caps the result at the excess in the IRA (https://www.irs.gov/pub/irs-pdf/p590a.pdf, page 38).

**Decision.** Let P be the maximum deduction, K the traditional contributions, E′ the carried excess under IRC 4973(b)(2)(A) and (B), and X the excess deducted in a closed year. The deemed deduction is max(0, min(P − K, E′) − X).
- **The object is fixed by the text.** The reduction falls on "the amount allowable as a deduction by reason of this paragraph", which is min(P − K, E′). The word "proper" leaves the mechanics open, not the object.
- **Worksheet 1-6 is not a reasonable reading.** It reduces the room, min(max(0, P − X − K), E′). It never gives less than the statute, and the two agree only when the room binds (P − K ≤ E′) or when X is at least the room, so both are $0. When the excess binds and the room is ample, it reduces nothing: P 7,000, K 2,000, E′ 2,000 and X 1,000 give 2,000 under the worksheet, the whole excess, so the closed-year amount is deducted twice. The statute gives 1,000. A reading under which the required reduction sometimes makes no reduction does not fit the text, so the standing rule applies and the statute governs.
- **Scope.** The rule applies per spouse. It reduces only the IRC 219(f)(6) deduction. Form 5329 lines 9, 10 and 14 are IRC 4973 amounts and do not change; line 10 uses the maximum deductible amount, which subparagraph (C) does not touch.
- **The intake.** The amount is the closed-year over-deduction not already applied as a reduction in an earlier year. The carried excess E′ is the true IRC 4973(b) excess, which includes the over-deducted amount.

**Open.** If X exceeds this year's deemed amount, whether the unused part reduces a later year's IRC 219(f)(6) amount is not addressed by either text. No regulation under IRC 219(f)(6)(C) is vendored. Until it is settled, the intake asks for the amount not yet applied, and the deduction is floored at $0.

**Direction if wrong.** If Worksheet 1-6 governs, the software under-deducts by up to X, and only when the carried excess is smaller than the room.

**Why.** Statute text and the structure of IRC 4973(b). Research by ira-RQ (Q18) on ira-S1's revision 10; advisor consulted. The call was delegated by the product owner on 2026-10-05. Verify row FED-1040-IRADED-F6CLOSEDYEAR-042.

#### IN-342 — the closed-year amount is not Form 8606 basis (2026-10-06)

**The law.** Basis in a traditional IRA is the filer's nondeductible contributions: "you have a cost basis (investment in the contract) equal to the amount of those contributions" (Pub. 590-B (2025), https://www.irs.gov/pub/irs-pdf/p590b.pdf, page 15). A designated nondeductible contribution is one designated as a contribution for which a deduction is not allowable, and "Any designation under clause (i) shall be made on the return of tax imposed by chapter 1 for the taxable year" (IRC 408(o)(2)(C), 26 U.S.C. 408, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section408&num=0&edition=prelim). The nondeductible limit is the deduction without IRC 219(g) less the deduction with it (IRC 408(o)(2)(B)(i), 26 U.S.C. 408, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section408&num=0&edition=prelim). Subparagraph (C) of IRC 219(f)(6) reduces both terms alike, so the closed-year amount never widens that difference.

**The IRS text.** The Instructions for Form 8606 (2025), line 1, take the smaller of IRA Deduction Worksheet line 10 or line 11, less line 12 (https://www.irs.gov/pub/irs-pdf/i8606.pdf, page 9). Line 11 includes the Form 5329 bridge amount (https://www.irs.gov/pub/irs-pdf/i5329.pdf, page 6). That worksheet has no closed-year line, so followed mechanically it would turn the reduction into basis. The instructions' Pub. 590-A branch enters only nondeductible contributions from that worksheet (https://www.irs.gov/pub/irs-pdf/i8606.pdf, page 9), and Worksheet 1-6 has no such line.

**Decision.** The closed-year amount does not enter Form 8606 line 1. Any remainder that becomes line 1 basis (the IN-309 remainder rule) is what the bridge amount B absorbs beyond both the closed-year amount and this year's deemed deduction: max(0, B − X − D6), with D6 from IN-341. When X is not more than min(P − K, E′), this is max(0, B − min(P − K, E′)). It is never max(0, B − D6), which would make X basis. In one sentence: the closed-year dollars are absorbed by Form 5329 line 10 and leave the excise base, are not deducted again (IN-341), and are not basis.

**Direction if wrong.** If the form route governed, basis would be overstated by up to X, and a later distribution of that amount would be untaxed although it was deducted in the closed year.

**Why.** The amount was deducted, and a deducted amount is not an investment in the contract. Its designation year is closed. Research by ira-RQ (Q19); advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### IN-343 — the closed-year amount left unanswered holds the deemed deduction (2026-10-06)

**The rule applied.** An unanswered question the filer reached, whose answer can change a money line, holds that line; the software "does not fill such a box with a guess" (GEN-01). The same module applied it on 2026-10-05 to a blank inherited-IRA payment (IN-336), and Schedule C applies it to carried losses (IN-290).

**Decision.** The question "excess contribution deducted in a closed year" is reached, per spouse, only when the answer can change the deduction: when the deemed amount before the reduction, min(P − K, E′), is above $0. When it is reached and unanswered, the IRC 219(f)(6) deduction, Schedule 1 line 20 and every line that follows from them hold. Form 5329 lines 9, 10 and 14 do not depend on it and are computed. When the room or the carried excess is $0, the question is not reached and nothing holds.

**Not the "enter any" pattern.** IN-289 and IN-296 read some blank amount lines as $0, because the form's own text makes an absent amount $0. Worksheet 1-6 line 3 also says "enter any excess contributions that were deducted in a closed tax year. Otherwise, enter -0-" (https://www.irs.gov/pub/irs-pdf/p590a.pdf, page 38), but its "Otherwise" means line 2 is not less than line 1, not a blank. Worksheet 1-6 is used only by a filer who has already identified the closed-year error (https://www.irs.gov/pub/irs-pdf/p590a.pdf, page 38). For the general population with a prior-year excess, the answer is the gate itself, so it must be asked.

**Not inconsistent with IRA-003.** A blank 2024 prior-year excess still reads as $0 today. That is an operator deferral of the repair (2026-10-04), not a ruling that a blank reads $0. This entry follows the rule IRA-003 states and has not yet built.

**Population.** Every filer with a carried traditional IRA excess and unused room. Fixtures that reach the question answer $0.

**Direction if wrong.** If a blank read $0, a filer who over-deducted in a closed year and skipped the question would deduct the amount again.

**Why.** GEN-01 and IN-336. Research by ira-RQ (Q20); advisor consulted. The call was delegated by the product owner on 2026-10-05.


#### Summary rows for IN-341 to IN-343

These rows belong in the Summary table above. They are kept here for now because inserting rows there would move the line-pinned references that the knowledge packages hold into this document.

| ID | Form / line | Question | Our current call | Our best recommendation | Agrees? | Confidence | Population affected | Direction if wrong | Authority | Facts (file: key fact) |
|---|---|---|---|---|---|---|---|---|---|---|
| IN-341 | Schedule 1 line 20, a prior-year excess deducted this year after an excess was deducted in a closed year (IRC 219(f)(6)(C)) | What does the closed-year reduction reduce? | The deemed deduction itself: max(0, min(P − K, E′) − X), not the room as in Pub. 590-A Worksheet 1-6, which reduces nothing when the carried excess binds; per spouse; Form 5329 lines 9, 10 and 14 unchanged | Keep | Yes | High | Filers with a carried traditional IRA excess who deducted part of an excess in a closed year | Under-deduction of up to the closed-year amount if the worksheet governs | IRC 219(f)(6)(A), (C), 4973(b)(1); Pub. 590-A (2025) Worksheet 1-6 | `iraDeduction: /primaryFilerSection219f6PriorYearExcessDeduction` |
| IN-342 | Form 8606 line 1 with a closed-year reduction | Does the closed-year amount become basis? | No: it was deducted; the line 1 remainder is max(0, B − X − D6), never max(0, B − D6) | Keep | Yes | High | Same as IN-341 | Basis overstated by up to the closed-year amount if wrong | IRC 408(o)(2)(B)-(C); Instructions for Form 8606 (2025), line 1; Pub. 590-B (2025) | `form8606: /form8606Line1ComparisonSide` |
| IN-343 | Schedule 1 line 20, the closed-year amount unanswered | Hold, or read $0? | Hold the deemed deduction and line 20 when the deemed amount before the reduction is above $0 (GEN-01, IN-336); Form 5329 lines 9, 10 and 14 compute; not reached otherwise | Keep | Yes | High | Filers with a carried traditional IRA excess and unused room | Re-deduction of a closed-year amount if a blank read $0 | GEN-01; IN-336; Pub. 590-A (2025) Worksheet 1-6 | `iraDeduction: /writablePrimaryFilerExcessContributionDeductedInClosedYear` (intake to build) |

#### IN-344 — IRC 219(f)(6)(C): a closed-year amount larger than this year's deemed amount carries forward (2026-10-06; TY2025 and TY2026; provisional in part)

Settles the point IN-341 left open. Gate B question GB-01 of the IRA two-year pilot.

**The statute.**
- **The reduction.** "Proper reduction shall be made in the amount allowable as a deduction by reason of this paragraph for any amount allowed as a deduction under this section for a prior taxable year for which the period for assessing deficiency has expired" (IRC 219(f)(6)(C), 26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section219&num=0&edition=2024, two-column; the same text single-column at 26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section219&num=0&edition=prelim). The object of the reduction is the whole closed-year over-deduction. Nothing limits it to one later year. Paragraph (6) allows a deduction again in every later year with unused room (IRC 219(f)(6)(A), 26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section219&num=0&edition=2024).
- **Why the dollars stay.** IRC 4973(b)(1) measures an excess against "the amount allowable as a deduction under section 219", not the amount allowed (26 U.S.C. 4973, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section4973&num=0&edition=2024). So the closed-year dollars stay in the carried excess E′. IRC 4973(b)(2)(C) then removes them only as later room absorbs them (26 U.S.C. 4973, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section4973&num=0&edition=2024).
- **What a lapse would do.** If the unapplied part lapsed, a later year's IRC 219(f)(6) amount would deduct those same dollars a second time. That is the outcome subparagraph (C) exists to prevent (IN-341).

**The IRS text.** Pub. 590-A (2025) gives the rule and Worksheet 1-6 for one correction year only (https://www.irs.gov/pub/irs-pdf/p590a.pdf, page 38). It says nothing about a closed-year amount larger than one year's room.

**Decision.** Use IN-341's terms, per spouse:
- P is the phased maximum, K the traditional contributions and E′ the carried excess.
- X is the closed-year amount not yet applied (the IN-341 intake).
- G = max(0, min(P − K, E′)) is the deemed amount before the reduction.
- D6 = max(0, G − X) is the IRC 219(f)(6) deduction (IN-341).
- B is the bridge amount that IN-342 uses: the part of the prior-year excess that Form 5329 line 10 absorbs this year.

The carry to the next year is C = max(0, X − max(G, B)).
- A closed-year dollar is neutralized once. Either it reduces a deemed deduction (up to G, IN-341), or it is absorbed this year without becoming basis (up to B, IN-342).
- C is the part that neither reaches. It is still inside next year's carried excess, so it reduces the next IRC 219(f)(6) amount in the same way.
- C never exceeds Form 5329 line 14, the prior-year excess that carries it. The closed-year dollars sit inside the carried excess, so X ≤ E′; an answered X above E′ is capped there and does not carry beyond it.
- When X ≤ G, C = $0. That is the only case IN-341 and IN-342 have exercised so far.
- The intake wording IN-341 already uses ("the amount not yet applied as a reduction in an earlier year") is the receiving end of C.

**Example (both readings, from sources).** A single filer, not covered by a plan, age 40, with compensation of $50,000 in both years and no Roth contributions.
- **2025.** P = U = 7,000, K = 6,000, E′ = 3,000 and X = 2,500.
  - G = min(1,000, 3,000) = 1,000, so D6 = max(0, 1,000 − 2,500) = 0.
  - Form 5329 line 10 = 7,000 − 6,000 = 1,000, so B = min(1,000, 3,000) = 1,000.
  - The IN-342 remainder is max(0, 1,000 − 2,500 − 0) = 0, so nothing becomes basis.
  - Form 5329 line 14 = 3,000 − 1,000 = 2,000 carries into 2026.
  - The carry is C = max(0, 2,500 − max(1,000, 1,000)) = 1,500.
- **2026.** P = U = 7,500 (Notice 2025-67), K = 5,000 and E′ = 2,000, so G = min(2,500, 2,000) = 2,000.
  - **Lapse reading:** D6 = 2,000, and Schedule 1 line 20 = 7,000.
  - **This ruling:** D6 = max(0, 2,000 − 1,500) = 500, and line 20 = 5,500.
- **Check.** Of the $3,000 carried excess, $2,500 was deducted in the closed year, so $500 more is the whole remaining deduction. This ruling deducts $500. The lapse reading deducts $2,000 and so deducts $1,500 twice.

**Why max(G, B) and not G alone.** Take P = 1,500, U = 7,000, K = 1,000, E′ = 3,000 and X = 2,500.
- G = 500 and D6 = 0.
- B = min(6,000, 3,000) = 3,000, and the IN-342 remainder is max(0, 3,000 − 2,500 − 0) = 500.
- Form 5329 line 14 is 0, so the whole excess is absorbed this year and the closed-year dollars leave with it.
- C = max(0, 2,500 − 3,000) = 0. A carry of X − G = 2,000 would instead cut a later deduction of some unrelated future excess.

**Scope.** TY2025 and TY2026; the text of IRC 219(f)(6)(C) is the same in the current-law view (26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section219&num=0&edition=prelim). The carry crosses years only through paired facts: TY2025 emits C per spouse, and TY2026's closed-year intake receives it. Form 5329 lines 9, 10 and 14 do not change (IN-341).

**Provisional in part.** No regulation under IRC 219(f)(6)(C) is vendored. That the amount carries forward follows from the text and from IRC 4973(b). The measure max(G, B) is derived here, not stated by any source. It follows from IN-341 and IN-342, so it falls if either of them is reversed.

**Direction if wrong.** If the unapplied amount lapses, the software under-deducts by up to C in a later year, and only for a filer whose closed-year over-deduction is larger than one year's room.

**Why.** Statute text and the structure of IRC 4973(b). Research by seat RB (ira-pilot gate B, GB-01); advisor consulted. The call was delegated by the product owner on 2026-10-05. Verify row FED-1040-IRADED-F6CLOSEDYEAR-042.

#### IN-345 — IRC 408(o)(2)(B)(i): the closed-year reduction enters each term with its own floor (2026-10-06; TY2025 and TY2026; corrects the reasoning of IN-342)

Gate B question GB-03 of the IRA two-year pilot.

**The statute.** The nondeductible limit is the excess of "(I) the amount allowable as a deduction under section 219 (determined without regard to section 219(g)), over (II) the amount allowable as a deduction under section 219 (determined with regard to section 219(g))" (IRC 408(o)(2)(B)(i), 26 U.S.C. 408, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section408&num=0&edition=prelim). Each term is a complete IRC 219 computation. That includes the IRC 219(f)(6) amount and its subparagraph (C) reduction, and the deduction it yields cannot fall below $0 (IN-341).

**Decision.**
- Compute each term separately:
  - Term (I) = min(K, U) + max(0, G_u − X), where G_u = min(U − K, E′).
  - Term (II) = min(K, P) + max(0, G_g − X), where G_g = min(P − K, E′).
  - The limit is (I) − (II).
- IN-342 said the reduction falls on "both terms alike, so the closed-year amount never widens that difference". That holds only when X ≤ G_g. When X is larger, the reduction in term (II) stops at G_g. The difference then narrows to max(0, G_u − X), and it never widens.
- **IN-342's decision formula is unchanged.** The Form 8606 line 1 remainder max(0, B − X − D6) equals this limit in every case. This was checked for X ≤ G_g, G_g < X ≤ G_u and X > G_u, with no Roth contributions, no distributions on Form 5329 lines 11 and 12, and K ≤ P. So this entry corrects the reasoning and the limit, not line 1.

**Example (a covered single filer in the phase-out band, from sources).** P = 2,800, U = 7,000, K = 1,000, E′ = 3,000, X = 2,500 and R = 0.
- With section 219(g): G_g = min(1,800, 3,000) = 1,800, so D6 = max(0, 1,800 − 2,500) = 0 and term (II) = 1,000 + 0 = 1,000.
- Without section 219(g): G_u = min(6,000, 3,000) = 3,000, so max(0, 3,000 − 2,500) = 500 and term (I) = 1,000 + 500 = 1,500.
- **This ruling:** the limit is 1,500 − 1,000 = 500.
- **Reading "alike" (the same 2,500 off both terms, unfloored):** (1,000 + 3,000 − 2,500) − (1,000 + 1,800 − 2,500) = 1,500 − 300 = 1,200.
- **Line 1 under IN-342:** B = min(6,000, 3,000) = 3,000, so the remainder is max(0, 3,000 − 2,500 − 0) = 500. This equals the limit under this ruling.
- The readings differ in the limit itself: 500 against 1,200. Through IN-331 that changes how much a filer can designate before the IRC 408(o)(2)(B)(ii) election.
- The IN-342 witness (P 2,800, K 1,000, E′ 3,000, X 1,000, B 3,000; line 1 = 1,200) is in the X ≤ G_g case, and both readings give 1,200 there.

**Scope.** TY2025 and TY2026; IRC 408(o) is unchanged in the current-law view. Limits:
- Roth contributions can make B smaller than G_u (IN-309 amendment). In that case line 1 is the IN-342 remainder and this limit is only its ceiling.
- The (B)(ii) election raises the limit as IN-331 states.

**Direction if wrong.** If "alike" governed, the limit would be overstated by up to G_u − G_g, but only when the closed-year amount is larger than the deemed amount with section 219(g).

**Why.** Statute text: each term is an "amount allowable", which is a floored quantity. Research by seat RB (ira-pilot gate B, GB-03); advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### IN-346 — Recharacterized contributions (IRC 408A(d)(6)): the amounts are entered net, as made to the second IRA (2026-10-06; TY2025 and TY2026)

Gate B question GB-04 of the IRA two-year pilot. This is a gap the family inherited: no obligation in the package mentioned recharacterization.

**The statute.** Except as the Secretary provides, a contribution moved by a trustee-to-trustee transfer on or before the due date "shall be treated as having been made to the transferee plan (and not the transferor plan)", "for purposes of this chapter" (IRC 408A(d)(6)(A), 26 U.S.C. 408A, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section408A&num=0&edition=2024). The transfer must carry the net income ((B)(i)). It applies "only to the extent no deduction was allowed with respect to the contribution to the transferor plan" ((B)(ii); 26 U.S.C. 408A, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section408A&num=0&edition=2024).

**The IRS text.**
- The Instructions for Form 8606 (2025), Recharacterizations, say to treat the contribution "as though the amount of the contribution was originally contributed to the second IRA" (https://www.irs.gov/pub/irs-pdf/i8606.pdf, page 6). They also require an attached statement, and when a Roth contribution is recharacterized in 2025 they put the amount transferred on line 4a.
- Pub. 590-A (2025) gives the same rule and the same three duties (https://www.irs.gov/pub/irs-pdf/p590a.pdf, page 29).

**Decision.**
- **The amounts.** A contribution recharacterized by the due date counts as made to the second IRA.
  - Traditional contributions (IRA Deduction Worksheet line 11, https://www.irs.gov/pub/irs-pdf/i1040gi.pdf, page 98; Form 5329 line 15) are the amounts after every recharacterization: a recharacterized traditional contribution is left out and one recharacterized into a traditional IRA is put in.
  - Roth contributions for IRC 219(c)(1)(B)(ii)(III) and IRC 4973(b)(2)(C) follow the same rule.
- **What changes.** This is intake meaning only. The computation does not change.
- **Out of the family's scope:**
  - The attached statement. It is a reporting obligation with no intake today and is named for gate C, in the same shape as IN-329's "statement required".
  - The line 4a amount for a 2025 Roth-to-traditional recharacterization. That is the 1099-R family's distribution reporting (code R).
  - A recharacterization made after the due date under Treas. Reg. 301.9100-2. It needs an amended return.

**Example (from sources).** A single filer, not covered by a plan, with compensation of $50,000. They contributed $7,000 to a traditional IRA and recharacterized $3,000 of it, with its earnings, to a Roth IRA by the due date.
- **This ruling:** K = 4,000 and R = 3,000.
  - Schedule 1 line 20 = 4,000.
  - Form 5329 line 15 = 0.
  - The Roth limit (IRC 408A(c)(2)) is 7,000 − 4,000 = 3,000, so there is no Roth excess.
- **Gross entry (K = 7,000, R = 3,000):** line 20 = 7,000. That over-deducts $3,000. It also gives a false IRC 4973(f) excess of $3,000 if Part IV is filled from the same answers.

**Limits.** Outside a joint return, the family has no general Roth-contribution intake: the Roth question is scoped to the spousal term (III) (IN-340). So the Roth side of a traditional-to-Roth recharacterization is only partly expressible. Gate C words the traditional intake so the net rule is stated where the filer answers.

**Direction if wrong.** No reading of the statute gives the gross amounts. The risk lies in the intake wording: a filer who enters gross amounts is over-deducted by the amount recharacterized.

**Why.** Statute text ("for purposes of this chapter"), with the Form 8606 instructions in agreement. Research by seat RB (ira-pilot gate B, GB-04); advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### IN-347 — Form 5329 Part IV (Roth excess) is entered by the filer and held, not computed by this family (2026-10-06; TY2025 and TY2026)

Gate B question GB-08 of the IRA two-year pilot, raised by the gate A review (note N2).

**The law.** A Roth excess is the amount contributed over "the amount allowable as a contribution under sections 408A(c)(2) and (c)(3)", plus the carried Roth excess less distributions and unused room (IRC 4973(f), 26 U.S.C. 4973, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section4973&num=0&edition=2024). Computing it takes three inputs this family does not model:
- the IRC 408A(c)(2) limit, net of contributions to other IRAs;
- the IRC 408A(c)(3) modified AGI phase-out, which has its own modified AGI (26 U.S.C. 408A, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section408A&num=0&edition=2024; the phased figures are in Notice 2024-80, https://www.irs.gov/pub/irs-drop/n-24-80.pdf, page 5, and Notice 2025-67, https://www.irs.gov/pub/irs-drop/n-25-67.pdf, page 5);
- the Roth distributions (Form 5329 line 20).

Form 5329 (2025) Part IV is lines 18-25 (https://www.irs.gov/pub/irs-pdf/f5329.pdf, page 1).

**The record.**
- The package's obligation IRA-036 covers Parts IV-VIII as an inventory obligation. Its own note names KNOCKOUT-023.
- Verify row FED-1040-IRADED-KNOCKOUT-023 is retired in verify's record. The knockout it closed now says:
  - lines 18 through 23 are taxpayer entries;
  - the leg keyed on Part IV line 24 holds only an answered Part IV whose December 31 value is blank;
  - "a Roth over-contributor ... now file[s] with the 4973(f) excise unassessed", and that population is named on the contract.

**Decision.**
- **Not computed in this family, in either year.** Lines 18-23 are filer entries. Lines 24 and 25 are computed from them, under the existing completeness hold. The family reads Roth contributions only for IRC 219(c)(1)(B)(ii)(III) (IN-340) and IRC 4973(b)(2)(C) (IN-309).
- **No new knockout.** A Roth over-contributor who leaves Part IV blank is the population the retired row put on the contract. Refusing it now would reverse a resolved row. And a knockout does not repair a money gap.
- **The family statement is corrected.** Part IV is an adjacent consumer for intake and print, and is not part of the computed family. Gate C re-labels the 18 Part IV units that gate A mapped only to IRA-036 as "adjacent, intake-only".
- **Named gap.** A computed Roth excess needs its own unit: an IRC 408A(c) package plus the Roth parameter rows. Gate A found that neither year's ledger has a Roth row (for 2026, $153,000 and $242,000, https://www.irs.gov/pub/irs-drop/n-25-67.pdf, page 5).

**Example (from sources).** A single filer with modified AGI of $100,000 and compensation of $100,000 (the 2025 Roth phase-out for a single filer is $150,000 to $165,000, https://www.irs.gov/pub/irs-drop/n-24-80.pdf, page 5, so it is not reached). They contributed $7,000 to a traditional IRA and $2,000 to a Roth IRA.
- **Under the statute:** the IRC 408A(c)(2) limit is 7,000 − 7,000 = 0, so the Roth excess is $2,000 and the excise is 6% × 2,000 = $120.
- **Under this ruling:** the excise is $120 if the filer enters line 23 = 2,000. It is $0 if the filer leaves Part IV blank. That is the named, contracted gap.

**Direction if wrong.** If Part IV were ruled into the computed family, the gap would be an in-scope money discrepancy. The fix would be the IRC 408A(c) unit, never a knockout.

**Why.** The verify record and the state of the existing knockout. Research by seat RB (ira-pilot gate B, GB-08); advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### Summary rows for IN-344 to IN-347

Kept here, as for IN-341 to IN-343, so that the line-pinned references into this document do not move.

| ID | Form / line | Question | Our current call | Our best recommendation | Agrees? | Confidence | Population affected | Direction if wrong | Authority | Facts (file: key fact) |
|---|---|---|---|---|---|---|---|---|---|---|
| IN-344 | Schedule 1 line 20, IRC 219(f)(6)(C), closed-year amount above this year's deemed amount | Does the unapplied part carry? | Yes: carry C = max(0, X − max(G, B)), capped at Form 5329 line 14, per spouse, emitted to the next year | Keep | Yes | Medium (no regulation vendored) | Filers whose closed-year over-deduction is larger than one year's room | Under-deduction of up to C if it lapses | IRC 219(f)(6)(C), 4973(b); Pub. 590-A (2025) Worksheet 1-6 | `iraDeduction: /writablePrimaryFilerExcessContributionDeductedInClosedYear` (receiving intake; carry fact to build) |
| IN-345 | Form 8606 line 1, IRC 408(o)(2)(B)(i) with a closed-year amount | Does the reduction enter both terms alike? | Each term separately, floored at $0; IN-342 line 1 formula unchanged | Keep | Yes | High | Same as IN-341 | Nondeductible limit overstated by up to G_u − G_g | IRC 408(o)(2)(B)(i), 219(f)(6)(C) | `form8606: /form8606Line1ComparisonSide` |
| IN-346 | Schedule 1 line 20, Form 5329 lines 15 and 23, Form 8606 line 1 | How are recharacterized contributions entered? | Net, as made to the second IRA (IRC 408A(d)(6)); statement and line 4a outside the family | Keep | Yes | High | Filers who recharacterized by the due date | Over-deduction by the recharacterized amount if entered gross | IRC 408A(d)(6); Instructions for Form 8606 (2025) | `iraDeduction: /primaryFilerTraditionalIraContributions` (intake wording) |
| IN-347 | Form 5329 Part IV | Computed or entered? | Entered by the filer, with the line 24 hold; no new knockout; IRC 408A(c) unit named as a gap | Keep | Yes | High | Roth over-contributors | Unassessed IRC 4973(f) excise when Part IV is left blank (contracted) | IRC 4973(f), 408A(c); verify KNOCKOUT-023 (retired) | `form5329: /form5329PartIvExcessWithoutAccountValue` |

#### IN-344-RQ2 — amendment to IN-344: the carry and its measure are accepted, not provisional (2026-10-07; TY2025 and TY2026)

Seat RQ2 re-examined both halves of IN-344. The product owner delegated rulings on 2026-10-05.

**Does a carry exist? Yes: accepted.**
- **The text has no one-year limit.** The reduction falls on "the amount allowable as a deduction by reason of this paragraph" and is made "for any amount allowed as a deduction under this section for a prior taxable year" whose assessment period has expired (IRC 219(f)(6)(C), 26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section219&num=0&edition=prelim). Paragraph (6) produces such an amount in every year with unused room (26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section219&num=0&edition=prelim).
- **The dollars stay in the excess.** IRC 4973(b)(1) measures an excess against the amount allowable, not the amount allowed (26 U.S.C. 4973, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section4973&num=0&edition=2024). The closed-year dollars therefore stay in the carried excess until IRC 4973(b)(2)(C) absorbs them (26 U.S.C. 4973, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section4973&num=0&edition=2024).
- **The lapse reading is rejected.** It deducts the same dollars twice, which is what subparagraph (C) prevents. IN-344's two-year example shows this: $2,000 deducted where $500 is right.
- **Re-entering the whole amount every year is also rejected.** Pub. 590-A (2025) describes one "later correction year", and Worksheet 1-6 line 3 asks for "any excess contributions that were deducted in a closed tax year" (https://www.irs.gov/pub/irs-pdf/p590a.pdf, page 38). Read literally and repeated each year, that would reduce the deduction again for amounts already applied, which is not a "proper" reduction. The worksheet is a one-year form. It is not a rule against a carry, and it is not a rule for a repeated one.

**Is max(G, B) the measure? Yes: accepted.** "Derived, not stated" was too weak a label: with no Roth contributions, the measure follows from IRC 408(o)(2) and the rulings already accepted.
- **The single assumption.** Of the excess that Form 5329 line 10 absorbs this year (B), the measure treats the closed-year dollars as leaving first. IN-342's remainder max(0, B − X − D6) makes the same assumption.
- **The alternative: never-deducted dollars leave first.** On that reading the closed-year amount is neutralized only by the IRC 219(f)(6)(C) reduction. Basis is then max(0, B − G) and the carry is min(X − min(X, G), Form 5329 line 14).
- **The statute rules the alternative out.** The designated nondeductible contributions for a year "shall not exceed the nondeductible limit" (IRC 408(o)(2)(A), 26 U.S.C. 408, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section408&num=0&edition=prelim).
  - That limit is term (I) less term (II), each an amount allowable under IRC 219 (26 U.S.C. 408, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section408&num=0&edition=prelim).
  - Each term carries its own IRC 219(f)(6)(C) reduction with its own $0 floor (IN-345).
  - With no Roth contributions and no Form 5329 line 11 or 12 distributions, G_u = min(U − K, E′) equals B. With K ≤ P the limit is then max(0, B − X) − D6, which is IN-342's remainder.
  - The alternative's basis, B − G, exceeds that limit whenever X > G and B > G. So it designates more than IRC 408(o)(2)(A) allows.

**Example (from sources).** A single filer covered by a plan, with compensation of $4,000. Modified AGI puts the filer in the phase-out band, which leaves a limit of P = 1,500. U = 4,000, K = 1,000, R = 0, E′ = 5,000 and X = 2,500.
- G = min(500, 5,000) = 500, so D6 = 0.
- B = min(5,000, 4,000 − 1,000) = 3,000, and Form 5329 line 14 = 2,000.
- The IRC 408(o)(2)(B)(i) limit is (1,000 + max(0, 3,000 − 2,500)) − (1,000 + 0) = 500.
- **This ruling:** basis is max(0, 3,000 − 2,500 − 0) = 500, which is within the limit. The carry is min(max(0, 2,500 − max(500, 3,000)), 2,000) = 0.
- **The alternative:** basis is 3,000 − 500 = 2,500, which is five times the limit. The carry is min(2,000, 2,000) = 2,000.

**What rides on IN-342 alone.** With Roth contributions, B can be smaller than G_u. Then both orderings fit inside the IRC 408(o)(2)(B)(i) limit. Take P 1,500, U 7,000, K 1,000, R 4,000, E′ 5,000 and X 2,500: the limit is 2,500, while basis is 0 under IN-342 and B − G = 1,500 under the alternative. On that branch the measure rests on IN-342's accepted formula, and IN-344 already says it falls with IN-342. This is a dependency, not an open reading.

**Residual, named and not ruled.** One case is open: closed-year dollars that leave the IRA in a distribution included in income under IRC 408(d)(1) (Form 5329 line 11), which reduces E′ by IRC 4973(b)(2)(A) (26 U.S.C. 4973, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section4973&num=0&edition=2024).
- Neither the statute nor Pub. 590-A says whether such dollars still count in X.
- **Reading 1 (today's intake wording, "not yet applied as a reduction"):** they still count, because inclusion is not a reduction. Example: line 9 3,000, a 2,500 line 11 distribution, X 2,500 and ample room give D6 = max(0, 500 − 2,500) = 0.
- **Reading 2:** the inclusion already reversed the over-deduction, so X falls to 0 and D6 = 500.
- The carry is capped by Form 5329 line 14 under both readings.
- A regulation under IRC 219(f)(6)(C) would settle it, and none is vendored. Population: a closed-year over-deduction later withdrawn as a taxable distribution while an excess remains. This is an IN-341 intake-wording question and is recorded for a later unit.

**Consequence for the code.**
- The merged XML computes C = min(max(0, X − max(G, B)), Form 5329 line 14) (`/primaryFilerClosedYearExcessDeductionCarryoverToNextYear` and its twin). No body changes and no witness changes.
- The `interpretation:provisional` mark on those two facts can be retired, citing this amendment.
- IRA-072 loses its "provisional in part" qualifier. Its status `gap` is about something else: the production consumer of the emitted fact is the TY2026 `…FromPriorTaxYear` intake, and no ty2026 dictionary exists. An accepted unit needs a downstream-consumer execution record (inner_models/WORKFLOW.md). IRA-072 can therefore leave `gap` only in one of two ways: a built TY2026 consumer, or a split that keeps the TY2025 emit here and moves the receive side to a TY2026 obligation. Whether the split satisfies the accepted-unit rule is a workflow call for the lead, not a tax ruling.

**Direction if wrong.** Unchanged from IN-344.

**Why.** Statute text: IRC 219(f)(6)(C), 4973(b) and 408(o)(2)(A)-(B), with IN-342 and IN-345. Research by seat RQ2; advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### IN-348 — TY2026: the closed-year amount and the carry-in are one quantity, so the larger governs and they are never added (2026-10-07; TY2026; settles question GC-02, reading R1)

The ira-pilot lead recorded reading R1 without a ruling seat, as question GC-02 (package meaning.md and procedure step 9a). Seat RQ2 rules on it here.

**The law fixes one quantity.** IRC 219(f)(6)(C) reduces this year's IRC 219(f)(6) amount for the closed-year over-deduction (26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section219&num=0&edition=prelim). IN-341 and IN-344 measure what remains of that over-deduction as the amount "not yet applied as a reduction in an earlier year". The statute defines one quantity: the unapplied closed-year over-deduction. The software asks for it in two ways:
- **X**, the IN-341 intake, which asks for that quantity directly;
- **the carry-in**, the `…FromPriorTaxYear` attestation of the TY2025 return's emitted C (IN-344).

**Decision.**
- In TY2026, X is the larger of the answered closed-year amount and the carry-in. The two are never added.
- **X above the carry-in is legitimate.** Every year another year's assessment period expires. An over-deduction from a year that was still open when the 2025 return was filed can be closed by the time the 2026 return is filed, and then it joins the unapplied amount. A TY2026 build must not refuse X > carry-in.
- **X below the carry-in contradicts the 2025 return.** The carry-in is a floor on the unapplied amount, and the larger governs. A refusal would also be lawful. Choosing between the two is product policy, not tax law, and it is left to the TY2026 unit.
- **Reached and unanswered.** If neither is answered and the question is reached (G > 0), hold (IN-343). If only one is answered, that one is X.
- **The wording that makes R1 exact.** The TY2026 X question says that its amount includes any amount carried from the 2025 return.

**Readings, with a discriminating example (TY2026, from sources).** A single filer, not covered by a plan: P = U = 7,500 (Notice 2025-67, https://www.irs.gov/pub/irs-drop/n-25-67.pdf, page 4), K = 5,000 and E′ = 2,000, so G = 2,000. The carry-in is 1,500. Another $300 over-deduction comes from a year whose assessment period expired after the 2025 return was filed. So X answered is 1,800, the whole unapplied amount.
- **R1 (this ruling):** X = 1,800, D6 = 200 and Schedule 1 line 20 = 5,200.
- **R2 (sum):** X = 3,300, D6 = 0 and line 20 = 5,000. The carried $1,500 is counted twice. R2 is only another way of asking: it gives the same result if X is reworded "not included in the carry". Under the IN-341 wording it double-counts.
- **R3 (replace):** X = 1,500, D6 = 500 and line 20 = 5,500. The newly closed $300 is dropped and deducted twice.

**Residual.** If IN-344's named residual is later ruled for reading 2, a filer could lawfully answer X below the carry-in. That ruling would then have to revisit the floor.

**Consequence for the code.**
- **TY2025.** No consequence: the XML does not combine the two.
- **TY2026.** Only the candidate witness `ty26-in344-carry-in-and-legacy-x-single` exercises this (carry-in 1,500 and X 1,800 give X 1,800, D6 200 and line 20 5,200). It stays as written. The rule binds the TY2026 unit that builds the `…FromPriorTaxYear` writables, and it needs no TY2025 change.

**Direction if wrong.** If the sum governed under the existing wording, the software would under-deduct by up to the carry-in. If replace governed, it would over-deduct by any newly closed amount.

**Why.** Statute text (IRC 219(f)(6)(C)), IN-341 and IN-344.

#### IN-349 — Form 8606 line 1: a closed-year amount larger than the bridge never reduces current-year contributions (2026-10-07; TY2025 and TY2026; settles question GC-03, reading A)

The ira-pilot lead recorded reading A without a ruling seat, as question GC-03 (package meaning.md; procedure.md step 11). Seat RQ2 rules on it here.

**The statute.**
- **What the reduction reaches.** IRC 219(f)(6)(C) reduces only "the amount allowable as a deduction by reason of this paragraph" (26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section219&num=0&edition=prelim). That is the deemed prior-year amount. The deduction for this year's own contributions K is allowable under IRC 219(a) and (b) without paragraph (6), so the closed-year amount X cannot reach it.
- **What can be designated.** A designated nondeductible contribution is "any contribution to an individual retirement plan for the taxable year" so designated (IRC 408(o)(2)(C)(i), 26 U.S.C. 408, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section408&num=0&edition=prelim).
- **The election.** The nondeductible limit rises by any allowable amount the filer elects not to deduct (IRC 408(o)(2)(B)(ii), 26 U.S.C. 408, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section408&num=0&edition=prelim). This year's K is allowable whatever X is.
- **Each term is floored separately (IN-345).** Each term of IRC 408(o)(2)(B)(i) carries its own IRC 219(f)(6)(C) reduction, floored at $0 (26 U.S.C. 408, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section408&num=0&edition=prelim).
- **Instructions for Form 8606 (2025), line 1.** The line takes the smaller of IRA Deduction Worksheet line 10 or line 11, less line 12 (https://www.irs.gov/pub/irs-pdf/i8606.pdf, page 9). Line 11 is K plus the bridge amount (https://www.irs.gov/pub/irs-pdf/i5329.pdf, page 6). The worksheet has no closed-year line. X enters only through IN-342, and IN-342 removes it from the bridge part.

**Decision.** The line 1 ceiling is M = min(CS, K + max(0, B − X)). X is floored inside its own term, which is reading A.

The rejected reading is reading B: min(CS, max(0, K + B − X)). When X > B, it takes the excess out of this year's contributions. That is a reduction subparagraph (C) does not make, applied to contributions IRC 408(o)(2)(C)(i) lets the filer designate. No text supports it. It arises only from simplifying K + max(0, B − X) as if B − X could not be negative.

**Example (from sources; the package witness `ira-pa-c-r3-designation-x-above-bridge-single`).** A single filer, not covered by a plan: U = P = 7,000, K = 4,000, R = 2,500, E′ = 3,000 and X = 1,500, so B = min(3,000, 7,000 − 4,000 − 2,500) = 500. G = 3,000 and D6 = 1,500. The filer designates N = 4,000.
- **Reading A:** M = min(7,000, 4,000 + 0) = 4,000, so the designation files. Line 1 = 4,000 and the deduction taken = 5,500 − 4,000 = 1,500.
- **Reading B:** the ceiling is min(7,000, 4,000 + 500 − 1,500) = 3,000, so the designation refuses. That refuses $1,000 of this year's own contributions, which IRC 408(o)(2)(B)(ii) and (C)(i) let the filer designate.
- **Without a designation** the two readings give the same line 1 whenever X is reached. A designation is what separates them.

**Consequence for the code.**
- The merged XML already computes reading A: both Form 8606 comparison sides, the six inline Plain/SSBW pools, and the designation bound M on both spouses (gate D review, r2).
- No body changes and no witness changes. The witness above, and the r2 natural red for the secondary GC-03 floor, stay as they are.
- The "provisional (question GC-03)" labels in procedure.md step 11, meaning.md and coverage IRA-026 can be retired by the next package unit, citing this entry.

**Direction if wrong.** If reading B governed, the software would allow a designation up to X − B too large, and only when X > B.

**Why.** Statute text: IRC 219(f)(6)(C) and 408(o)(2)(B)-(C), with IN-342 and IN-345. Research by seat RQ2; advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### IN-309-RQ2 — second amendment to IN-309: the provisional label stays, for a reason the first amendment did not address (2026-10-07; TY2025 and TY2026)

The IRA deduction repair hand-off lists the IN-309 amendment as provisional, although its heading does not say so. Seat RQ2 re-examined whether the label is still warranted. It is, but for a different reason from the one the 2026-10-04 text gave.

**What the amendment settled.** IRC 219(f)(6)(A)(ii) measures the excess "determined under section 4973(b)(2) without regard to subparagraph (C) thereof" (26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section219&num=0&edition=prelim). So the IRC 4973(b)(2)(C) Roth room (26 U.S.C. 4973, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section4973&num=0&edition=2024) never limits clause (ii). That point stands.

**What it did not settle.** Clause (i) is the excess of the maximum deductible amount "for contributions to an individual retirement plan" over "the amount contributed" (26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section219&num=0&edition=prelim). Subparagraph (B) defines that amount without any Roth clause (lines 176-182). But "Except as provided in this section, a Roth IRA shall be treated for purposes of this title in the same manner as an individual retirement plan" (IRC 408A(a), 26 U.S.C. 408A, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section408A&num=0&edition=2024). On that reading, Roth contributions are part of "the amount contributed" in clause (i). The parenthetical in IRC 4973(b)(2)(C) does not decide the point either way.

**The IRS texts disagree with each other.**
- **Pub. 590-A (2025)** subtracts "any amounts contributed to your traditional IRAs for this year" (https://www.irs.gov/pub/irs-pdf/p590a.pdf, page 36).
- **The Instructions for Form 5329 (2025), line 10,** subtract Roth contributions as well. They then carry the smaller of line 10 and the remaining excess into the IRA Deduction Worksheet (https://www.irs.gov/pub/irs-pdf/i5329.pdf, page 6).

**Three readings, one discriminating example.** The example is the package witness `ira-s1-r8-in309a-roth-under-phaseout-deducts-past-excise-room-single`: P = 2,800, U = 7,000, K = 500, R = 5,000, E′ = 3,000 and X = 0.

| Reading | Rule | D6 | Schedule 1 line 20 |
|---|---|---|---|
| Amended reading (kept as primary) | D6 = min(P − K, E′) | 2,300 | 2,800 |
| Form route (the 2026-10-04 reading) | D6 = min(E′, P − K, U − K − R) | 1,500 | 2,000 |
| IRC 408A(a) reading | D6 = min(E′, max(0, P − K − R)) | 0 | 500 |

Form 5329 line 10 is 1,500 under all three, so lines 14 and 17 do not change.

**Decision.**
- **The amended reading stays primary.** Verify sustained row FED-1040-IRADED-F6ROTHCAP-039 on it. Pub. 590-A's own text matches it. No vendored source makes the IRC 408A(a) reading prevail, and a primary reading is not reversed on an unproven alternative.
- **The label stays provisional.** A materially competing reading survives: IRC 408A(a) gives the IRC 408A(a) reading statutory footing, and the Form 5329 instruction supports the form route.
- **Against the amended reading.** It lets a deduction stand for dollars that IRC 4973(b)(2)(C) does not absorb, so they remain excess. The IRC 408A(a) reading avoids that result.
- **What would settle it.** A regulation or published guidance under IRC 219(f)(6) that addresses Roth contributions, or a Pub. 590-A worksheet that shows a Roth contribution. None is vendored.

**Consequence for the code.**
- The merged XML computes the amended reading. No body changes and no witness changes.
- The `interpretation:provisional` marks on the D6, bridge and excise-room facts stay.
- Under the IRC 408A(a) reading, D6 and Schedule 1 line 20 would fall in every in309a witness and in the secondary-Roth n6 witness. The Form 8606 line 1 pools would also change.

**Direction if wrong.** If either competing reading governs, the software over-deducts by up to the Roth amount. This holds only where Roth contributions eat into the phased room or the excise room.

**Why.** Statute text (IRC 219(f)(6)(A)-(B) and 408A(a)) and the conflict between the two IRS texts. Research by seat RQ2; advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### IN-337-RQ2 — amendment to IN-337: both provisional points stay provisional; the box 11 basis is restated (2026-10-07; TY2025 and TY2026)

The IRA deduction repair hand-off lists IN-337 as provisional. Seat RQ2 re-examined both provisional points, and both stay provisional. The rest of IN-337 is accepted and not reopened: the base is IRC 415(c)(3) compensation includible in gross income, and combat pay and alimony are out of it.

**1. Which employer.**
- **The text is pulled two ways.** IRC 415(c)(3)(A) is "the compensation of the participant from the employer for the year" (26 U.S.C. 415, https://uscode.house.gov/view.xhtml?req=granuleid:USC-2024-title26-section415&num=0&edition=2024). IRC 219(b)(3)(B) imports that definition, but for compensation "includible in the individual's gross income" (26 U.S.C. 219, https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section219&num=0&edition=prelim). Pub. 525 (2025) states the limit as "the lesser of $7,000 or 25% of your compensation", with no employer qualifier (https://www.irs.gov/pub/irs-pdf/p525.pdf, page 9).
- **Readings.**
  - **(a), kept:** the box 1 wages of the W-2s that report code H.
  - **(b):** all of the individual's IRC 415(c)(3)-type compensation.
- **Example.** A code H W-2 with box 1 of 8,000, a second W-2 of 12,000, and code H of 6,000. Reading (a) allows min(7,000, 2,000, 6,000) = 2,000. Reading (b) allows min(7,000, 5,000, 6,000) = 5,000.
- **What would settle it.** Treas. Reg. 1.415(c)-2, which is not vendored.

**2. Box 11.**
- **Reading (a), kept:** box 11 amounts inside box 1 are out of the base.
- **The stated basis was wrong.** IN-337 rested this on IRC 219(f)(1)'s "deferred compensation" exclusion. But IN-337's own decision holds that IRC 219(b)(3)(B)'s cross-reference to IRC 415(c)(3) displaces IRC 219(f)(1). The basis is therefore restated: whether these amounts are IRC 415(c)(3) compensation is a question for the IRC 415 regulation.
- **Reading (b):** they are wages includible in gross income and stay in.
- **Example.** Box 1 of 20,000 including box 11 of 8,000, and code H of 6,000. Reading (a) allows 3,000. Reading (b) allows 5,000.
- **What would settle it.** Treas. Reg. 1.415(c)-2, which is not vendored.

**Decision.** No change to the computation. Both points stay provisional with the readings above, and the box 11 reasoning is replaced as stated.

**Consequence for the code.**
- No XML or witness change.
- The `/primaryFilerSection415c3CompensationFor501c18` Description (and its twin) should cite this amendment rather than IRC 219(f)(1) for box 11, at the next touch.

**Direction if wrong.** Unchanged from IN-337: the allowed 501(c)(18) amount is too small.

**Why.** Statute text, Pub. 525, and the absence of the regulation. Research by seat RQ2; advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### Summary rows for IN-344-RQ2, IN-348, IN-349, IN-309-RQ2 and IN-337-RQ2

Kept here, as for IN-341 to IN-347, so that the line-pinned references into this document do not move.

| ID | Form / line | Question | Our current call | Our best recommendation | Agrees? | Confidence | Population affected | Direction if wrong | Authority | Facts (file: key fact) |
|---|---|---|---|---|---|---|---|---|---|---|
| IN-344-RQ2 | Schedule 1 line 20, the IRC 219(f)(6)(C) carry | Is the carry, and its measure max(G, B), still provisional? | No: both accepted. IRC 408(o)(2)(A)-(B) with IN-345 rules out the other ordering when R = 0; with Roth the measure rests on IN-342. The IRC 408(d)(1) distribution residual is named and not ruled | Keep | Yes | High (residual: low population) | Filers whose closed-year over-deduction exceeds one year's room | Under-deduction of up to C if the carry lapses | IRC 219(f)(6)(C), 4973(b), 408(o)(2) | `iraDeduction: /primaryFilerClosedYearExcessDeductionCarryoverToNextYear` |
| IN-348 | TY2026 Schedule 1 line 20, the closed-year amount and the carry-in | Larger, sum or replace? | The larger, never the sum; X above the carry-in is legitimate (a newly closed year) | Keep | Yes | High | TY2026 filers with a carry-in | Under- or over-deduction by the carry-in or by a newly closed amount | IRC 219(f)(6)(C); IN-341; IN-344 | `iraDeduction (TY2026): /writablePrimaryFilerClosedYearExcessDeductionCarryoverFromPriorTaxYear` (to build) |
| IN-349 | Form 8606 line 1 ceiling, X above the bridge | Can X reduce this year's contributions? | No: M = min(CS, K + max(0, B − X)) | Keep | Yes | High | Filers who designate, with X above B | A designation ceiling too large by up to X − B | IRC 219(f)(6)(C), 408(o)(2)(B)-(C); IN-345 | `form8606: /form8606Line1ComparisonSide` |
| IN-309-RQ2 | Schedule 1 line 20, IRC 219(f)(6) with Roth contributions | Is the amended reading settled? | No: it stays primary and provisional; IRC 408A(a) and the Form 5329 line 10 route compete | Keep, provisional | Yes | Medium | Filers with a prior-year excess and Roth contributions | Over-deduction of up to the Roth amount | IRC 219(f)(6)(A)-(B), 408A(a); Pub. 590-A; Instructions for Form 5329 | `iraDeduction: /primaryFilerSection219f6PriorYearExcessDeduction` |
| IN-337-RQ2 | Schedule 1 line 24f base | Are which employer and box 11 settled? | No: both stay provisional; the box 11 basis is restated as an IRC 415(c)(3) question | Keep, provisional | Yes | Medium | 501(c)(18) filers with several W-2s or box 11 | Allowed amount too small | IRC 219(b)(3)(B), 415(c)(3); Pub. 525 | `iraDeduction: /primaryFilerSection415c3CompensationFor501c18` |

### Rulings of 2026-10-07: return-wide whole-dollar rounding (IN-359 onward)

The product owner decided on 2026-10-07 that whole-dollar rounding is one return-wide concept with one owner, the shared knowledge package `return-whole-dollar-rounding` 0.1.0. Its author left three questions open (IQ-RND-1 to IQ-RND-3) and one gap (RND-G5). Seat RQ-RND rules on them here, under the product owner's delegation of 2026-10-05 (research plus advisor; the advisor was consulted on every entry). The package itself is not edited by these entries; its author folds them in.

The general rule is in the Instructions for Form 1040 (2025), Rounding Off to Whole Dollars (https://www.irs.gov/pub/irs-pdf/i1040gi.pdf, page 23): "You can round off cents to whole dollars on your return and schedules. If you do round to whole dollars, you must round all amounts. To round, drop amounts under 50 cents and increase amounts from 50 to 99 cents to the next dollar. For example, $1.39 becomes $1 and $2.50 becomes $3." The next paragraph adds: "If you have to add two or more amounts to figure the amount to enter on a line, include cents when adding the amounts and round off only the total" (lines 1333-1337). Pub. 17 (2025), Rounding off dollars, repeats both paragraphs word for word (sources/p17--ty2025--2026-07.xml lines 1801-1802).

#### IN-359 — An exact amount with a fraction of a cent, and a tie at exactly 50 cents (2026-10-07; TY2025; settles IQ-RND-1, reading A, and gap RND-G5)

**The question.** An amount kept exactly, for example $10.00 + $0.99/4 + $0.99/4 = $10.495, reaches the whole-dollar step with 49.5 cents. Is it entered as $10 or $11? And how does a tie at exactly 50 cents go where a form says only "nearest whole dollar"?

**The texts.**
- **Form 1040 instructions:** "drop amounts under 50 cents and increase amounts from 50 to 99 cents" (https://www.irs.gov/pub/irs-pdf/i1040gi.pdf, page 23). 49.5 cents is under 50 cents and is not in "50 to 99 cents". The text is consistent at this point: it drops.
- **Form 8949 instructions:** "drop cent amounts under 50 cents and increase cent amounts over 49 cents to the next dollar. For example, $1.49 becomes $1 and $1.50 becomes $2" (https://www.irs.gov/pub/irs-pdf/i8949.pdf, page 3). At 49.5 cents both of its clauses apply: it is under 50 cents and over 49 cents. A text that contradicts itself at the disputed point cannot ground the round-up reading. Its own examples are whole cents, which is all it was written for.
- **Form 8962 and Pub. 974:** lines 8a and 8b, and Worksheets I and III lines 2, 6 and 7, are "rounded to the nearest whole dollar amount" (https://www.irs.gov/pub/irs-pdf/i8962.pdf, page 12; https://www.irs.gov/pub/irs-pdf/p974.pdf, page 42). The nearest whole dollar to $10.495 is $10.
- **A tie, from an IRS worked example.** In Pub. 974 (2025), Andrew's line 8a is $4,290 and "the monthly contribution amount he enters on line 8b is $358" (https://www.irs.gov/pub/irs-pdf/p974.pdf, page 24). $4,290 divided by 12.0 is $357.50 exactly, so a tie under "nearest whole dollar" goes up. That matches every other rounding statement in the sources: $2.50 becomes $3 (Form 1040), $1.50 becomes $2 (Form 8949), $8.50 rounds to $9 (Form 8621, https://www.irs.gov/pub/irs-pdf/i8621.pdf, page 3).

**Decision.**
- **Reading A is accepted.** Whole-dollar rounding is to the nearest dollar of the amount as figured. A fraction strictly below 50 cents, including 49.5 cents, is dropped. $10.495 is entered $10. Reading B (round up anything "over 49 cents") is rejected.
- **RND-G5 is settled.** A tie at exactly 50 cents goes up to the next dollar, for the optional rounding and for every "nearest whole dollar" line alike. This is stated by an IRS example, not inferred.
- **Signed amounts (RND-G1) are not ruled here.** The 50-cent rule is written for positive amounts. A negative tie stays with each consumer's own ruling.

**What this does not decide: the cent stage (PR-01).** This entry rules how an amount that still carries a fraction of a cent is rounded. It does not rule whether a line must be figured exactly or to the cent first. PR-01, the owner's recorded convention, figures a product to the cent first and then rounds. The engine's dollar type keeps two decimal places, rounding half to even, so a product of exactly $501.495 becomes $501.50 and then $502 (PR-01's own example). The result matches reading B's result, by a different route. PR-01 is a separate recorded convention for products typed as dollars. It is not reopened here, and the two are not a contradiction: under PR-01 a fraction of a cent never reaches the whole-dollar step. The reviewer may want to look at the two side by side. Line 8a of Form 8962 already avoids the cent stage: the dictionary truncates the product to the cent before rounding, so a product of 1,115.4958 is entered 1,115, as "nearest whole dollar" requires.

**Consequence for the code.**
- **form5695-residential-energy.** Its exact door amounts are rounded with the engine's exact-to-dollar rounding, which is half-up with no cent step. That is reading A. Its retained sub-cent witness (exact 269.4965, entered 269) stands. No change.
- **ira-deduction.** Its lines follow the PR-01 pattern (IN-307: figure to the cent, then round half-up), so it does not depend on this question. No change.
- **Form 8962 lines 8a and 8b.** Line 8b rounds the quotient half-up, which matches the tie rule ($357.50 gives $358). No change.

**Direction if wrong.** If reading B governed, an exactly kept amount with 49.5 to 49.99 cents would be $1 too low. Only form5695's door lines keep amounts exactly today.

**Why.** The texts above. Research by seat RQ-RND; advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### IN-360 — A later line adds the entered, rounded figures of earlier lines (2026-10-07; TY2025; settles IQ-RND-2, reading A; amends IN-300 for Form 5695 line 19h)

**The question.** On a return that rounds, line 1a is $1.30 (entered $1) and line 1b is $2.30 (entered $2). Line 2 is "Add lines 1a and 1b". Is line 2 $3 (the entered figures) or $4 (their cents, rounded once)?

**The texts.**
- "If you do round to whole dollars, you must round all amounts" (https://www.irs.gov/pub/irs-pdf/i1040gi.pdf, page 23). Once line 1a is entered, its amount is $1.
- The form faces add lines, not underlying figures: "Add lines 1a through 1h" (Form 1040 line 1z) and "Add lines 1z, 2b, 3b, 4b, 5b, 6b, 7a, and 8. This is your total income" (Form 1040 line 9) (https://www.irs.gov/pub/irs-pdf/f1040.pdf, page 1).
- The sum sentence, "include cents when adding the amounts and round off only the total" (https://www.irs.gov/pub/irs-pdf/i1040gi.pdf, page 23), governs amounts that are not themselves entered on a line, such as several Forms W-2 or several items, summed to make one line. On a rounded return, an entered line has no cents left to include.
- Where the IRS spells the chain out, a later line uses the rounded line. Form 8962 line 8b says to "Divide line 8a by 12.0", where line 8a is "rounded to the nearest whole dollar amount" (https://www.irs.gov/pub/irs-pdf/i8962.pdf, page 12). Pub. 974's example divides the entered line 8a of $4,290 (https://www.irs.gov/pub/irs-pdf/p974.pdf, page 24).
- Pub. 974 has to tell the filer "Do not round to whole dollars when performing the computations under this method. Instead, use dollars and cents" for its iterative method (https://www.irs.gov/pub/irs-pdf/p974.pdf, page 52). The caution is needed only because rounded lines otherwise feed later lines.

**Decision.**
- **Reading A is accepted.** A later line that adds, subtracts or otherwise uses an entered line takes the figure as entered. On a return that rounds, that is the whole-dollar figure. Reading B (the underlying cents) is rejected.
- **The sum sentence keeps its own reach.** Amounts that are never entered on a line of the return (per-item amounts, per-door credits, document boxes) keep their cents when added, and only the line total is rounded (RND-004).
- **Consumer rulings already on this footing.** IN-307 (Schedule 1 line 15 adds the two rounded Schedule SE line 13 amounts) and IN-335 (Form 4972 lines 25 and 28 multiply the printed whole-dollar lines 24 and 27).

**Form 5695 line 19h (amends IN-300's precision amendment).** Line 19h is "Add lines 19c and 19g. Do not enter more than $500" (https://www.irs.gov/pub/irs-pdf/f5695.pdf, page 2). Today the dictionary computes it by adding the exact per-door credits and rounding once, citing the sum sentence. Lines 19c and 19g are entered lines, so on the route where the form's arithmetic is also the statutory arithmetic, that is reading B.
- **Measured (scratch probe, 2026-10-07, not a corpus case).** A filer with no joint occupancy has a most expensive door of $501.50 and one other door of $501.50, both qualifying. Line 19c is 30% of 501.50 = 150.45, entered 150. Line 19g is the same, entered 150. The dictionary enters 301 on line 19h, from the exact 300.90. Reading A gives 150 + 150 = 300. The difference is at most $1, in either direction (two amounts of 150.55 give 302 under A and 301 today).
- **Ruling.** Where line 19h is the form's own sum, it adds the entered lines 19c and 19g and applies the $500 limit. This covers a filer without joint occupancy for whom every door's credit is the printed figure, with no door over the $250 limit inside line 19g.
- **Where IN-300 stands unchanged.** IN-300's exact computation stays where the statutory computation departs from the printed shortcut: the IRC 25C(b)(4)(A) per-door limit inside line 19g, and joint-occupancy allocation. There the addends are per-door credits that are never entered on a line, so including cents and rounding the total once is reading A applied correctly. The exact household trigger (more than $500) is a comparison, not an entry, and also stays.
- **The retained SC-07 witness is not disturbed.** SC-07 is a joint-occupancy case, so it is on the route where IN-300 stands: its exact total 225 + 250 × 76/854 + 250 × 76/854 = 269.4965 is entered 269. It would also enter 269 on the face route (the two shares add to 44.4965, entered 44, and 225 + 44 = 269). IN-300's concern was the cent-stage result of 270 (22.25 + 22.25 = 44.50, then 45). Neither route produces it.

**Classification and consequence for the code.**
- **form5695-residential-energy.** This is a preexisting implementation defect at line 19h, relative to this ruling. It is an interpretation dispute that IN-300 resolved toward B and this entry resolves toward A. It affects `form5695: /form5695DoorCredit` and `/form5695DoorCreditBeforeJointOccupancy` on the face route. The XML computes differently from this ruling by up to $1 on line 19h, and the difference flows to the credit. The defect is owned by the form5695 package and is not repaired here. The probe above is the red witness for its author to retain. The package's integration claim of reading A holds downstream of line 19h, but not at line 19h. This amendment is a ruling. It retires no verify finding on IN-300, which verify still owns.
- **ira-deduction.** Schedule SE line 13 is rounded on each filer's own schedule, and Schedule 1 line 15 adds the two rounded amounts (`scheduleSE: /primaryFilerSelfEmploymentTaxDeduction`). That is reading A. No change.

**Direction if wrong.** If reading B governed, the lines that add entered lines would be off by up to $1 per line, in either direction, wherever cents were dropped or raised on the earlier lines.

**Why.** The texts above, IN-307 and IN-335. Research by seat RQ-RND; advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### IN-361 — A form with its own rounding sentence follows the return's one choice when it is attached to Form 1040 (2026-10-07; TY2025; settles IQ-RND-3, reading B)

**The question.** Form 8621's instructions say "The shareholder may enter decimal points and cents when completing Form 8621 ... The shareholder must either round off all amounts on Form 8621 to whole dollars or use cents for all amounts" (https://www.irs.gov/pub/irs-pdf/i8621.pdf, page 3). Form 8949's say "You can round off cents to whole dollars on Form 8949. If you do round to whole dollars, round all amounts" (https://www.irs.gov/pub/irs-pdf/i8949.pdf, page 3). On a Form 1040 return that rounds, may Form 8621 or Form 8949 keep cents?

**The readings.**
- **Reading A (a per-form choice).** Each form's sentence is its own election. Support: the Form 1040 instructions speak of "your return and schedules" (https://www.irs.gov/pub/irs-pdf/i1040gi.pdf, page 23) and do not name attached forms, and Form 8621 says the shareholder "may enter decimal points and cents".
- **Reading B (one return-wide choice).** The Form 1040 sentence "If you do round to whole dollars, you must round all amounts" is unconditional (lines 1320-1323). A form's sentence restates all-or-nothing within that form.

**Why the form carries its own sentence.** Form 8621 is not only a Form 1040 attachment. It is attached "to the shareholder's tax return (or, if applicable, partnership or exempt organization return)", and a shareholder not required to file a return files it directly with the IRS (https://www.irs.gov/pub/irs-pdf/i8621.pdf, page 2). A form filed with a partnership return, or alone, needs its own rounding rule. That explains the sentence without making it an exception to the Form 1040 rule. Nothing in either form says its choice holds whatever the return does. Form 8949 has no either/or at all.

**Decision.** Reading B is accepted, with medium confidence. When Form 8621 or Form 8949 is part of a Form 1040 return, it follows the return's one choice (RND-002). Its own sentence governs it when it is filed without a Form 1040 (Form 8621 only), and restates all-or-nothing within the form. This is also the reading that fits the product owner's decision of one return-wide owner.

**Consequence for the code.** None today. No consumer imports Form 8621 or Form 8949, the return-wide choice is not yet bound to a writable (gap RND-G4), and the software produces a return that rounds throughout. A return with one uniform choice is correct under both readings, so no XML computes differently.

**Direction if wrong.** None today. If reading A governed and a cents mode were ever offered for these forms alone, refusing it would only withhold an option. No tax changes.

**Why.** The texts above. Research by seat RQ-RND; advisor consulted. The call was delegated by the product owner on 2026-10-05.

#### Summary rows for IN-359 to IN-361

| ID | Form / line | Question | Our current call | Our best recommendation | Agrees? | Confidence | Population affected | Direction if wrong | Authority | Facts (file: key fact) |
|---|---|---|---|---|---|---|---|---|---|---|
| IN-359 | Every whole-dollar line; Form 8962 lines 8a and 8b; Pub. 974 worksheets | An exact amount with 49.5 cents, and a tie at 50 cents | Nearest dollar of the amount as figured: 49.5 cents is dropped; exactly 50 cents goes up (Pub. 974 example, $357.50 to $358). PR-01's cent stage for products is a separate convention, not reopened | Keep | Yes | High | Lines that keep exact amounts (Form 5695 doors today) | $1 low if the round-up reading governed | Instructions for Form 1040, Form 8949, Form 8962; Pub. 974 | `form5695: /form5695DoorCredit` |
| IN-360 | Every line that adds entered lines; Form 5695 line 19h | Entered figures or their underlying cents? | Entered figures. The sum sentence covers amounts never entered on a line. Form 5695 line 19h on the face route adds the entered 19c and 19g (amends IN-300; not yet built) | Keep | Yes | High | Every return that rounds; Form 5695 door claimants | Up to $1 per line, either direction | Instructions for Form 1040; Form 1040; Form 5695; Instructions for Form 8962; Pub. 974 | `form5695: /form5695DoorCredit`; `scheduleSE: /primaryFilerSelfEmploymentTaxDeduction` |
| IN-361 | Form 8621 and Form 8949 attached to Form 1040 | Their own choice, or the return's? | The return's one choice; the form's own sentence governs a Form 8621 filed without a Form 1040 | Keep | Yes | Medium | None today (no consumer; the return always rounds) | None today | Instructions for Form 1040, Form 8621, Form 8949 | none (no consumer) |
