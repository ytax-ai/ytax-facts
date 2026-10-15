# Client interview — Mama Bear — Direct File scenario hoh-cdcc-multiple-careproviders

**Profile:** `profile-df-hoh-cdcc-multiple-careproviders` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hoh-cdcc-multiple-careproviders.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Mama Bear (born 1988-03-22) of 543 Main St, Oak, CA 94203 file(s) head of household — IRS Direct File test scenario `hoh-cdcc-multiple-careproviders` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Baby One (born 2021-08-23, childOrDescendants); Bubba Two (born 2011-12-21, childOrDescendants); Nondeppy Three (born 2000-10-10, childOrDescendants); NonD Benny (born 2023-05-22, childOrDescendants); NonCustodial BennySplit (born 2019-09-23, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $45,000.58 of box 1 wages.

## Documents provided

- 2025 Form W-2, ABC Company, EIN 00-1234232 (box 1 $45,000.58; box 2 $0.00)
- Form 2441 provider: Loyal Non-profit, $500.58 paid
- Form 2441 provider: Mama Goose, $200.58 paid
- Form 2441 provider: Las Manitas, $7,000.58 paid
- Form 2441 provider: Raggedy Ann, $1,300.58 paid

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: No; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hoh-cdcc-multiple-careproviders.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 631373c69a10abeb…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#010947ac-4cf0-4de6-9229-1c78ba27c955/dateOfBirth 1999-10-10 → 2000-10-10; /familyAndHousehold/#010947ac-4cf0-4de6-9229-1c78ba27c955/writableChildEmancipationDate 2017-10-10 → 2018-10-10; /familyAndHousehold/#1979aec3-be19-4b51-a6c3-53db837f42d0/dateOfBirth 2010-12-21 → 2011-12-21; /familyAndHousehold/#89387295-5488-432f-874f-ba6f2353d6a3/dateOfBirth 2018-09-23 → 2019-09-23; /familyAndHousehold/#d8ef6a22-3823-48b1-a1b6-1f728b96c8d2/dateOfBirth 2022-05-22 → 2023-05-22; /familyAndHousehold/#e626fc63-667a-4639-ac65-1e68ce9d0d2e/dateOfBirth 2020-08-23 → 2021-08-23; /filers/#36f1c4f8-0d18-4aaa-9267-7e7f049320d9/dateOfBirth 1987-03-22 → 1988-03-22. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- SCOPE: Direct File flags this return with /formW2s/*/causesDependentCareBenefitsKO — its TY2024 scope excluded W-2 box 10 dependent care benefits. ytax computes Form 2441 Part III (cdcc:/cdccTaxableBenefits, /cdccExcludedBenefitsAmount), so the return is in scope here and resolves Complete; the flag is read by no TY2025 fact.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
