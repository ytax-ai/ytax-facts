# Client interview — Filer Person — Direct File scenario mfj-30k-eitc-ctc-actc

**Profile:** `profile-df-mfj-30k-eitc-ctc-actc` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfj-30k-eitc-ctc-actc.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Filer Person (born 1984-01-10) and Spouse Person (born 1984-01-01) of 1 Cat Street, Washington, NY 10014 file(s) married filing jointly — IRS Direct File test scenario `mfj-30k-eitc-ctc-actc` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: First Children (born 2021-01-01, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $30,000.00 of box 1 wages; 1 Form(s) 1099-INT ($1,100.00).

## Documents provided

- 2025 Form W-2, The USG, EIN 00-0000000 (box 1 $30,000.00; box 2 $2,500.00; NY box 16 $30,000.00 / box 17 $500.00) — spouse's
- 2025 Form 1099-INT, Bank (box 1 $1,100.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No; spouse: Yes.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: No; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfj-30k-eitc-ctc-actc.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 3db24acf4cdb74a9…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#97297bea-bbfa-4c77-bff6-12554186f6c9/dateOfBirth 2020-01-01 → 2021-01-01; /filers/#044b7b2d-5bb7-4ed4-b36c-8c9b4913b49e/dateOfBirth 1983-01-01 → 1984-01-01; /filers/#4ac86366-9dfd-426f-9525-12c60b485090/dateOfBirth 1983-01-10 → 1984-01-10. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- SCOPE: Direct File flags this return with /contradictory8832TPIsCustodialParentTriggeredKnockout (the filer's custodial-parent answers contradict the Form 8332 answers in its flow). ytax resolves the return Complete from the answers as given (EITC, CTC, ACTC computed); the flag is read by no TY2025 fact. Treat the household's 8332 answers as the scenario's, not as coherent.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
