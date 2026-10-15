# Client interview — Marjorie Simpson — Direct File scenario cdcc-mfj-filer-qp-multiple-qps

**Profile:** `profile-df-cdcc-mfj-filer-qp-multiple-qps` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/cdcc-mfj-filer-qp-multiple-qps.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Marjorie Simpson (born 1956-03-09) and Mama Shark (born 1989-05-16) of 742 Evergreen Terrace, Springfield, MA 01109 file(s) married filing jointly — IRS Direct File test scenario `cdcc-mfj-filer-qp-multiple-qps` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Baby Shark (born 2020-12-30, childOrDescendants); Sista Shark (born 2016-04-20, childOrDescendants); Brutha Shark (born 2015-03-19, childOrDescendants); Hapa Shark (born 2019-09-13, childOrDescendants); Delfin Shark (born 2014-08-25, childOrDescendants).

Income documents on record: 2 Form(s) W-2 totalling $50,500.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, Pretzel Corp, EIN 00-1234567 (box 1 $45,000.00; box 2 $0.00)
- 2025 Form W-2, ABC Gum, EIN 00-9878978 (box 1 $5,500.00; box 2 $0.00) — spouse's
- Form 2441 provider: Kid Care, $31,000.00 paid

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No; spouse: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: No; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/cdcc-mfj-filer-qp-multiple-qps.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 e809eab217d51abd…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#0bbf6ef9-a42a-429a-9c32-0a27f5a1330e/dateOfBirth 2018-09-13 → 2019-09-13; /familyAndHousehold/#529710a9-4ac5-43d8-b421-75f67ef59e21/dateOfBirth 2015-04-20 → 2016-04-20; /familyAndHousehold/#84bea8d8-4b2c-48a2-8257-0c8326acba6e/dateOfBirth 2014-03-19 → 2015-03-19; /familyAndHousehold/#d9508bb8-9e7f-476b-be04-2a59a7082dcd/dateOfBirth 2019-12-30 → 2020-12-30; /familyAndHousehold/#ebca1d8e-a856-4e91-8cbd-a9b8496d34af/dateOfBirth 2013-08-25 → 2014-08-25; /filers/#3364f249-f89e-44b2-b62a-43575975a076/dateOfBirth 1988-05-16 → 1989-05-16; /filers/#4bce88b1-e95f-4ae0-aefc-43c84ceadc50/dateOfBirth 1955-03-09 → 1956-03-09; /importedPrimaryFilerDateOfBirth 1955-03-09 → 1956-03-09. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- SCOPE: Direct File flags this return with /showSpecialEarnedIncomeKnockoutFlowInCredits (a student or disabled spouse, Form 2441 line 5 deemed earned income). ytax carries that rule (cdcc:/cdccDisabledOrInSchoolIncomePerMonthWithMultipleQps = $500) and the credit resolves ($1,100 on the runner); the flag is read by no TY2025 fact.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
