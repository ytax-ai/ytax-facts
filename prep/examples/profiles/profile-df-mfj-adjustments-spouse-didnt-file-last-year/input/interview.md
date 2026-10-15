# Client interview — George Bailey — Direct File scenario mfj-adjustments-spouse-didnt-file-last-year

**Profile:** `profile-df-mfj-adjustments-spouse-didnt-file-last-year` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfj-adjustments-spouse-didnt-file-last-year.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

George Bailey (born 1981-01-01) and Mary Bailey (born 1981-01-01) of 123 Sesame St, Bedford Falls, NH 03301 file(s) married filing jointly — IRS Direct File test scenario `mfj-adjustments-spouse-didnt-file-last-year` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Janie Bailey (born 2013-01-01, childOrDescendants); Zuzu Bailey (born 2016-01-01, childOrDescendants); Pete Bailey (born 2011-01-01, childOrDescendants); Tommy Bailey (born 2020-01-01, childOrDescendants); Mama Bailey (born 1962-01-01, parentOrAncestors).

Income documents on record: 1 Form(s) W-2 totalling $50,000.00 of box 1 wages; 1 Form(s) 1099-INT ($25.00).

## Documents provided

- 2025 Form W-2, Bedford Falls Building and Loan, EIN 00-1234567 (box 1 $50,000.00; box 2 $500.00)
- 2025 Form 1099-INT, Bedford Falls Building and Loan (box 1 $25.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No; spouse: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: Yes; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfj-adjustments-spouse-didnt-file-last-year.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 297f8e1c494de9cb…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#1efc8013-daa6-42c3-b704-ec52f7a1dacd/dateOfBirth 2012-01-01 → 2013-01-01; /familyAndHousehold/#2d07210c-7ddb-41b8-bcca-bd57e2d0e1c8/dateOfBirth 1961-01-01 → 1962-01-01; /familyAndHousehold/#348e109d-fba3-4311-a2fc-02e8b7b3a1b1/dateOfBirth 2010-01-01 → 2011-01-01; /familyAndHousehold/#9d87d8db-a657-4960-ad7d-73511a170416/dateOfBirth 2015-01-01 → 2016-01-01; /familyAndHousehold/#ed36e540-f3e4-4015-9787-6cd895bd2fea/dateOfBirth 2019-01-01 → 2020-01-01; /filers/#0975a470-0768-4fb0-a8ec-9da6ef9187a6/dateOfBirth 1980-01-01 → 1981-01-01; /filers/#280ae688-a4d6-4c4e-bc69-b5eb1b4ce252/dateOfBirth 1980-01-01 → 1981-01-01. A W-2 box 4 above 6.2% of boxes 3 + 7, or box 6 above the Medicare rates on box 5, is impossible on a real W-2 and is set to the rate figure — /formW2s/#e6ed7417-c524-46bd-bb18-eb06fb4c5f8b/writableMedicareWithholding 726.00 → 725.00. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
