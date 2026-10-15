# Client interview — Marjorie Simpson — Direct File scenario ptc-high-income

**Profile:** `profile-df-ptc-high-income` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/ty2024/ptc-high-income.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Marjorie Simpson (born 1956-03-09) and Souse Tester (born 1977-10-01) of 742 Evergreen Terrace, Springfield, MA 02301 file(s) married filing jointly — IRS Direct File test scenario `ptc-high-income` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $90,125.00 of box 1 wages. Also on record, without a rendered facsimile: 1095As.

## Documents provided

- 2025 Form W-2, USDS, EIN 00-7896541 (box 1 $90,125.00; box 2 $0.00)
- 1 item(s) in /1095As — carried as facts, no facsimile

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/ty2024/ptc-high-income.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 28eefe1e5c536438…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /1095As/#fd6dd5c4-c190-46f4-91b6-238dd3b1f152/writablePolicyEndDate 2024-07-14 → 2025-07-14; /1095As/#fd6dd5c4-c190-46f4-91b6-238dd3b1f152/writablePolicyStartDate 2024-02-13 → 2025-02-13; /filers/#2b1ee52a-7cfa-4f76-9e80-fff39260ca0d/dateOfBirth 1976-10-01 → 1977-10-01; /filers/#58e455cb-81d9-4ed5-a99d-2b8ee2b9abdd/dateOfBirth 1955-03-09 → 1956-03-09; /importedPrimaryFilerDateOfBirth 1955-03-09 → 1956-03-09. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
