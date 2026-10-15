# Client interview — L Kahn — Direct File scenario mfj-1dep-1nondep

**Profile:** `profile-df-mfj-1dep-1nondep` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfj-1dep-1nondep.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

L Kahn (born 1902-03-05) and Esther Kahn (born 1910-02-26) of 204 Sunrise Ln, Philadelphia, NY 10014 file(s) married filing jointly — IRS Direct File test scenario `mfj-1dep-1nondep` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Alexandra Tyng (born 1947-01-01, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $50,000.00 of box 1 wages; 1 Form(s) 1099-INT ($1,250.00); 1 Form(s) 1099-G ($521.00).

## Documents provided

- 2025 Form W-2, Pennsylvania University, EIN 00-3123123 (box 1 $50,000.00; box 2 $4,999.00; NY box 16 $50,000.00 / box 17 $499.00)
- 2025 Form 1099-INT, Bank (box 1 $1,250.00)
- 2025 Form 1099-G, Company (box 1 $521.00; box 4 $20.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfj-1dep-1nondep.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 5b5bdb03766ccb52…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#bc16d3cc-c9ea-4240-bc3a-7645ca171ce9/dateOfBirth 1946-01-01 → 1947-01-01; /familyAndHousehold/#bc16d3cc-c9ea-4240-bc3a-7645ca171ce9/writableChildEmancipationDate 1964-01-01 → 1965-01-01; /familyAndHousehold/#e93deeef-cb90-48b0-911d-b074959f2319/dateOfBirth 1921-07-14 → 1922-07-14; /familyAndHousehold/#e93deeef-cb90-48b0-911d-b074959f2319/writableChildEmancipationDate 1939-07-14 → 1940-07-14; /filers/#37ad9545-8806-45de-a87c-0905cff65bd1/dateOfBirth 1901-03-05 → 1902-03-05; /filers/#bf659a96-f32c-4bdf-8c61-859132badee5/dateOfBirth 1909-02-26 → 1910-02-26. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
