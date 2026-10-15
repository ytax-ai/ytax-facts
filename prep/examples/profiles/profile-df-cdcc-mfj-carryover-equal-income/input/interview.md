# Client interview — Mama Bear — Direct File scenario cdcc-mfj-carryover-equal-income

**Profile:** `profile-df-cdcc-mfj-carryover-equal-income` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/cdcc-mfj-carryover-equal-income.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Mama Bear (born 1988-03-22) and Buggy Boo (born 2001-03-27) of 543 Main St, Oak, CA 94203 file(s) married filing jointly — IRS Direct File test scenario `cdcc-mfj-carryover-equal-income` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Baby One (born 2021-08-23, childOrDescendants).

Income documents on record: 2 Form(s) W-2 totalling $47,000.00 of box 1 wages; 1 Form(s) 1099-INT ($1,200.00); 1 Form(s) SSA-1099 ($2,600.00 net); 1 Form(s) 1099-G ($1,200.00).

## Documents provided

- 2025 Form W-2, ABC Company, EIN 00-1234232 (box 1 $45,000.00; box 2 $0.00)
- 2025 Form W-2, Main, EIN 00-3412342 (box 1 $2,000.00; box 2 $0.00) — spouse's
- 2025 Form 1099-INT, Bubbles (box 1 $1,200.00)
- 2025 Form SSA-1099 (box 5 $2,600.00; box 6 $0.00) — spouse's
- 2025 Form 1099-G, fasdf (box 1 $1,200.00; box 4 $0.00)
- Form 2441 provider: Loyal Non-profit, $500.00 paid
- Form 2441 provider: Mama Goose, $200.00 paid
- Form 2441 provider: Las Manitas, $7,000.00 paid
- Form 2441 provider: Raggedy Ann, $1,300.00 paid

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/cdcc-mfj-carryover-equal-income.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 0b7dade31156484c…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#e626fc63-667a-4639-ac65-1e68ce9d0d2e/dateOfBirth 2020-08-23 → 2021-08-23; /filers/#36f1c4f8-0d18-4aaa-9267-7e7f049320d9/dateOfBirth 1987-03-22 → 1988-03-22; /filers/#b6691a4b-a985-49d0-a351-bcd4e346702b/dateOfBirth 2000-03-27 → 2001-03-27. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
