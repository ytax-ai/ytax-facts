# Client interview — Anthony Stark — Direct File scenario mfj-40k-eitc-ctc

**Profile:** `profile-df-mfj-40k-eitc-ctc` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfj-40k-eitc-ctc.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Anthony Stark (born 1971-05-29) and Pepper Potts (born 1973-07-04) of 350 5th Ave, New York, NY 10014 file(s) married filing jointly — IRS Direct File test scenario `mfj-40k-eitc-ctc` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Morgan Stark (born 2020-02-21, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $35,000.00 of box 1 wages; 1 Form(s) 1099-INT ($145.00); 1 Form(s) 1099-G ($5,600.00).

## Documents provided

- 2025 Form W-2, S.H.I.E.L.D., EIN 00-3456789 (box 1 $35,000.00; box 2 $15,000.00; NY box 16 $35,000.00 / box 17 $2,000.00)
- 2025 Form 1099-INT, Bank (box 1 $145.00)
- 2025 Form 1099-G, NYUI (box 1 $5,600.00; box 4 $0.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: Yes; spouse: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: No; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfj-40k-eitc-ctc.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 4796258da6ea2728…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#7b9e390b-d359-4573-b181-6874bf0c2af2/dateOfBirth 2019-02-21 → 2020-02-21; /filers/#e1814b60-b24f-40b2-b98c-212d3c4e4566/dateOfBirth 1972-07-04 → 1973-07-04; /filers/#e9ba8db8-c9ea-41ee-a675-1681b9471500/dateOfBirth 1970-05-29 → 1971-05-29. A W-2 box 4 above 6.2% of boxes 3 + 7, or box 6 above the Medicare rates on box 5, is impossible on a real W-2 and is set to the rate figure — /formW2s/#9e257898-2b2a-4778-8cff-980f0bf488e6/writableMedicareWithholding 1000.00 → 507.50. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
