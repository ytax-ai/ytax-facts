# Client interview — Testy Testofferson — Direct File scenario mfj-20k

**Profile:** `profile-df-mfj-20k` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfj-20k.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Testy Testofferson (born 1991-01-01) and Tessa Testersson (born 1991-01-01) of 123 Fake Street, Ontario, AZ 85001 file(s) married filing jointly — IRS Direct File test scenario `mfj-20k` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $20,000.00 of box 1 wages; 1 Form(s) 1099-INT ($30.00).

## Documents provided

- 2025 Form W-2, Arby's, EIN 00-3333333 (box 1 $20,000.00; box 2 $0.00)
- 2025 Form 1099-INT, Bank Co (box 1 $30.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfj-20k.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 6bc4aafb94c0e90e…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#12cad005-1312-40bf-bcc1-3624237f1ea8/dateOfBirth 1996-01-01 → 1997-01-01; /filers/#8c2d66c3-f1f4-420a-9280-01040f932a0d/dateOfBirth 1990-01-01 → 1991-01-01; /filers/#da1297af-aeac-4961-ab06-a131ed5d0a72/dateOfBirth 1990-01-01 → 1991-01-01. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
