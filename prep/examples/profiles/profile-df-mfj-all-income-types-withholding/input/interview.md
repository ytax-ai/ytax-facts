# Client interview — Michael Bluth — Direct File scenario mfj-all-income-types-withholding

**Profile:** `profile-df-mfj-all-income-types-withholding` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfj-all-income-types-withholding.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Michael Bluth (born 1986-04-22) and Maggie Lizer (born 1978-03-22) of 2290 Stairway drive, Santa Clarita, CA 90210 file(s) married filing jointly — IRS Direct File test scenario `mfj-all-income-types-withholding` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 2 Form(s) W-2 totalling $160,000.00 of box 1 wages; 4 Form(s) 1099-INT ($1,480.00); 2 Form(s) SSA-1099 ($3,000.00 net); 2 Form(s) 1099-G ($17,500.00).

## Documents provided

- 2025 Form W-2, Bluth Company, EIN 00-2291111 (box 1 $100,000.00; box 2 $12,000.00)
- 2025 Form W-2, Lizer Lizer and Cutestory, EIN 00-8200020 (box 1 $60,000.00; box 2 $5,500.00) — spouse's
- 2025 Form 1099-INT, Bank of Banktown USA (box 1 $600.00)
- 2025 Form 1099-INT, Lendquick (box 1 $500.00)
- 2025 Form 1099-INT, Banky (box 1 $300.00)
- 2025 Form 1099-INT, savings usa (box 1 $80.00)
- 2025 Form SSA-1099 (box 5 $4,000.00; box 6 $300.00)
- 2025 Form SSA-1099 (box 5 $-1,000.00; box 6 $200.00) — spouse's
- 2025 Form 1099-G, State of California (box 1 $2,500.00; box 4 $500.00)
- 2025 Form 1099-G, State of california (box 1 $15,000.00; box 4 $2,500.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfj-all-income-types-withholding.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 8f90eb838ba4cb14…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /filers/#6e683c7b-2694-4884-b269-87275170fa53/dateOfBirth 1985-04-22 → 1986-04-22; /filers/#fe689e56-8317-4e63-9807-26c7042d9dae/dateOfBirth 1977-03-22 → 1978-03-22. A W-2 box 4 above 6.2% of boxes 3 + 7, or box 6 above the Medicare rates on box 5, is impossible on a real W-2 and is set to the rate figure — /formW2s/#27b51972-33d4-4c94-96bc-b4514506fbcd/writableMedicareWithholding 1500.00 → 870.00; /formW2s/#65104ace-78fb-4216-a0d3-312ecf968d31/writableMedicareWithholding 3000.00 → 1450.00. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
