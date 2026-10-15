# Client interview — Boris Siberian — Direct File scenario mfj-11k

**Profile:** `profile-df-mfj-11k` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/ty2024/mfj-11k.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Boris Siberian (born 1996-02-10) and Mickey Barry (born 1998-06-21) of 999 Kitty St, Mewson, AZ 85001 file(s) married filing jointly — IRS Direct File test scenario `mfj-11k` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Valentina Siberia (born 2012-08-11, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $11,000.00 of box 1 wages; 1 Form(s) 1099-INT ($30.00).

## Documents provided

- 2025 Form W-2, CAt Toys Unlmtd, EIN 00-3333333 (box 1 $11,000.00; box 2 $2,000.00; AZ box 16 $11,000.00 / box 17 $1,100.00)
- 2025 Form 1099-INT, Purr City Bank (box 1 $30.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/ty2024/mfj-11k.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 9a5f5fb2a717ee6b…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#296aa849-b3b9-4c4c-bfe7-bc99e0cf90f7/dateOfBirth 2011-08-11 → 2012-08-11; /filers/#d06f0997-2eae-45d2-af3c-8c019498456d/dateOfBirth 1995-02-10 → 1996-02-10; /filers/#d651c904-6569-4fa3-8f90-8e14fd42285a/dateOfBirth 1997-06-21 → 1998-06-21; /secondaryFilerDateOfDeath 2024-11-01 → 2025-11-01. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
