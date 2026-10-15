# Client interview — Marjorie Simpson — Direct File scenario hsa-mfj-one-8889

**Profile:** `profile-df-hsa-mfj-one-8889` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hsa-mfj-one-8889.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Marjorie Simpson (born 1956-03-09) and Scott Spouse (born 1941-01-01) of 742 Evergreen Terrace, Springfield, FL 32401 file(s) married filing jointly — IRS Direct File test scenario `hsa-mfj-one-8889` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $50,000.00 of box 1 wages. Also on record, without a rendered facsimile: hsaDistributions.

## Documents provided

- 2025 Form W-2, test, EIN 00-2394682 (box 1 $50,000.00; box 2 $0.00)
- 1 item(s) in /hsaDistributions — carried as facts, no facsimile

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hsa-mfj-one-8889.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 c367de5de6c05b13…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /filers/#1c78d0ba-7e4a-4706-a05b-795dbb69a9c8/dateOfBirth 1955-03-09 → 1956-03-09; /filers/#2ac435d5-0c03-4ada-a010-6008c4d8aabe/dateOfBirth 1940-01-01 → 1941-01-01; /importedPrimaryFilerDateOfBirth 1955-03-09 → 1956-03-09. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
