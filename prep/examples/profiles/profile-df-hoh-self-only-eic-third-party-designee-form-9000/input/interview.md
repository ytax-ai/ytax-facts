# Client interview — Christy Colleran — Direct File scenario hoh-self-only-eic-third-party-designee-form-9000

**Profile:** `profile-df-hoh-self-only-eic-third-party-designee-form-9000` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hoh-self-only-eic-third-party-designee-form-9000.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Christy Colleran (born 2004-01-01) of 123 Sesame St, New York, NY 10014 file(s) head of household — IRS Direct File test scenario `hoh-self-only-eic-third-party-designee-form-9000` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Timmy Testerson (born 2021-01-01, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $8,101.00 of box 1 wages; 1 Form(s) 1099-INT ($8.89).

## Documents provided

- 2025 Form W-2, The Morning Post, EIN 00-1234567 (box 1 $8,101.00; box 2 $545.00; NY box 16 $8,101.00 / box 17 $52.00)
- 2025 Form 1099-INT, The Bank (box 1 $8.89)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: No; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hoh-self-only-eic-third-party-designee-form-9000.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 87e3a31a4c443032…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#1dc2e299-cca5-45e1-b8b2-745f8d9bedec/dateOfBirth 2020-01-01 → 2021-01-01; /filers/#f148e87f-5ceb-4f4a-8c2c-002fc096fdf0/dateOfBirth 2003-01-01 → 2004-01-01. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
