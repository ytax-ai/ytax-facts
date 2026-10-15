# Client interview — Chris Bacon — Direct File scenario mfj-30k

**Profile:** `profile-df-mfj-30k` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfj-30k.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Chris Bacon (born 1970-04-20) and Amanda HugAndKiss (born 1903-08-12) of 123 Alphabet lane, Reno, NV 89433 file(s) married filing jointly — IRS Direct File test scenario `mfj-30k` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Lord Brain (born 2012-01-12, childOrDescendants); Donald Duck (born 2021-07-30, childOrDescendants).

Income documents on record: 2 Form(s) W-2 totalling $50,000.00 of box 1 wages; 1 Form(s) 1099-INT ($10.00); 1 Form(s) 1099-G ($1,000.00).

## Documents provided

- 2025 Form W-2, Sam and Ella’s pizzeria, EIN 00-0878909 (box 1 $30,000.00; box 2 $1,500.00; NV box 16 $500.00 / box 17 $500.00)
- 2025 Form W-2, Amigone Funeral Home, EIN 00-0878909 (box 1 $20,000.00; box 2 $750.00) — spouse's
- 2025 Form 1099-INT, Silicon Valley Bank (box 1 $10.00)
- 2025 Form 1099-G, Tequila Mockingbird (box 1 $1,000.00; box 4 $0.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfj-30k.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 3f7e0c06bcdfc2c9…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#331f1a2a-cd1c-4082-a6b0-7a333e72919b/dateOfBirth 2020-07-30 → 2021-07-30; /familyAndHousehold/#e1e40e93-83d3-417d-b8ba-a1e720976ec4/dateOfBirth 2011-01-12 → 2012-01-12; /filers/#2688f236-cf3f-4ded-a921-07d6bc88e374/dateOfBirth 1969-04-20 → 1970-04-20; /filers/#54077829-3405-4a52-bda5-5ddc3096f93f/dateOfBirth 1902-08-12 → 1903-08-12. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
