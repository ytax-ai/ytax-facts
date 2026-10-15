# Client interview — Lal Boone — Direct File scenario mfj-42505-ctck12

**Profile:** `profile-df-mfj-42505-ctck12` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfj-42505-ctck12.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Lal Boone (born 1991-07-07) and Diesel Boone (born 1991-05-05) of 123 ABC St, San Diego, CA 94203 file(s) married filing jointly — IRS Direct File test scenario `mfj-42505-ctck12` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Lal Boone (born 2017-08-17, childOrDescendants); Chester Boone (born 2019-07-07, inlaws).

Income documents on record: 2 Form(s) W-2 totalling $82,505.00 of box 1 wages; 2 Form(s) 1099-INT ($1,200.00).

## Documents provided

- 2025 Form W-2, Initech, EIN 00-5454555 (box 1 $42,505.00; box 2 $4,000.00; CA box 16 $42,505.00 / box 17 $400.00)
- 2025 Form W-2, Acme, EIN 00-1211111 (box 1 $40,000.00; box 2 $4,000.00; CA box 16 $40,000.00 / box 17 $400.00) — spouse's
- 2025 Form 1099-INT, Wells Fargo (box 1 $800.00)
- 2025 Form 1099-INT, Fannie Mae (box 1 $400.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: Yes; spouse: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: Yes; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfj-42505-ctck12.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 17f62f2049eaab1d…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#0dea6e9a-f314-4789-b07e-2aaaf1adbb65/dateOfBirth 2016-08-17 → 2017-08-17; /familyAndHousehold/#8957bee4-c79c-4b04-916a-eea160ccbf53/dateOfBirth 2018-07-07 → 2019-07-07; /filers/#14230982-62c5-48ea-868f-c3613edb610f/dateOfBirth 1990-05-05 → 1991-05-05; /filers/#5abb8b14-ee0b-4a48-9e62-60f8061c436d/dateOfBirth 1990-07-07 → 1991-07-07. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
