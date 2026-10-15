# Client interview — Homer Lake — Direct File scenario 8862-ctc-no-eitc

**Profile:** `profile-df-8862-ctc-no-eitc` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/8862-ctc-no-eitc.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Homer Lake (born 1988-11-11) and Spouse Testerface (born 1988-11-12) of 123 sesame st, new york, NY 10014 file(s) married filing jointly — IRS Direct File test scenario `8862-ctc-no-eitc` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Child testerface (born 2020-11-11, childOrDescendants); ODC Child Testerface (born 2020-11-11, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $100,000.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, USDS, EIN 00-1111111 (box 1 $100,000.00; box 2 $6,500.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/8862-ctc-no-eitc.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 d89e03a7ef747fe7…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#02eaee04-9897-4d29-9dc2-10efb198c103/dateOfBirth 2019-11-11 → 2020-11-11; /familyAndHousehold/#6b8cf1ae-b1be-48f9-a30e-2d8268b5c2a4/dateOfBirth 2019-11-11 → 2020-11-11; /filers/#0a873014-1d84-4169-a656-67b9007492ad/dateOfBirth 1987-11-12 → 1988-11-12; /filers/#32431d0c-2abc-49af-8a8e-a150671af7cd/dateOfBirth 1987-11-11 → 1988-11-11. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
