# Client interview — Rainbow Bright — Direct File scenario qss-75k

**Profile:** `profile-df-qss-75k` · **Tax year:** 2025 · **Filing status:** qualifiedSurvivingSpouse

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/qss-75k.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Rainbow Bright (born 1981-03-17) of 123 Rainbow St, Sky, FL 32401 file(s) qualifying surviving spouse — IRS Direct File test scenario `qss-75k` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Murky Dismal (born 2015-06-01, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $75,000.00 of box 1 wages; 1 Form(s) 1099-INT ($100.00).

## Documents provided

- 2025 Form W-2, The Sun, EIN 00-1234567 (box 1 $75,000.00; box 2 $5,000.00)
- 2025 Form 1099-INT, Bank of Rainbows (box 1 $100.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: Yes; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/qss-75k.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 4399f0ba88107253…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#9ea10c6c-7d7e-4aa2-9f79-bd8d53a37ced/dateOfBirth 2014-06-01 → 2015-06-01; /filers/#ca6346c9-e955-421b-a74a-089d61d83624/dateOfBirth 1980-03-17 → 1981-03-17. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
