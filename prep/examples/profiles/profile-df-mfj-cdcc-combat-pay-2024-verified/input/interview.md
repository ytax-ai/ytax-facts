# Client interview — Marjorie Simpson — Direct File scenario mfj-cdcc-combat-pay-2024-verified

**Profile:** `profile-df-mfj-cdcc-combat-pay-2024-verified` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfj-cdcc-combat-pay-2024-verified.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Marjorie Simpson (born 1981-06-18) and Homer Simpson (born 1981-01-15) of 123 Sesame Stt, Springfield, TN 37011 file(s) married filing jointly — IRS Direct File test scenario `mfj-cdcc-combat-pay-2024-verified` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Bartholomew Simpson (born 2016-01-01, childOrDescendants).

Income documents on record: 2 Form(s) W-2 totalling $72,000.00 of box 1 wages; 1 Form(s) 1099-INT ($3,200.00). Also on record, without a rendered facsimile: hsaDistributions.

## Documents provided

- 2025 Form W-2, Goods and Stuff, EIN 00-1234567 (box 1 $2,000.00; box 2 $200.00)
- 2025 Form W-2, Burns Enterprises, EIN 00-1234567 (box 1 $70,000.00; box 2 $5,500.00) — spouse's
- 2025 Form 1099-INT, Bank of Springfield (box 1 $3,200.00)
- Form 2441 provider: Patty and Selma Care, $9,000.00 paid
- 1 item(s) in /hsaDistributions — carried as facts, no facsimile

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfj-cdcc-combat-pay-2024-verified.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 ea1f4c39b4ffe86f…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#d4aab682-94c9-482b-8bd9-3a31fd861353/dateOfBirth 2015-01-01 → 2016-01-01; /filers/#7470a973-e6d2-4f5b-8308-82bf45f8035b/dateOfBirth 1980-06-18 → 1981-06-18; /filers/#ff764204-9368-4aad-8a2c-a9eac969d345/dateOfBirth 1980-01-15 → 1981-01-15; /importedPrimaryFilerDateOfBirth 1980-06-18 → 1981-06-18. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
