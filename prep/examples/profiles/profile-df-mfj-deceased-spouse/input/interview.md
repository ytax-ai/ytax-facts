# Client interview — Elmo Muppet — Direct File scenario mfj-deceased-spouse

**Profile:** `profile-df-mfj-deceased-spouse` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/ty2024/mfj-deceased-spouse.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Elmo Muppet (born 2004-02-22) and Cookie Monster (born 1999-03-29) of 2345 Sesame Street, Phoenix, AZ 85001 file(s) married filing jointly — IRS Direct File test scenario `mfj-deceased-spouse` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Elmo McMuppet (born 2016-11-06, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $34,009.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, KQED, EIN 00-1239999 (box 1 $34,009.00; box 2 $2,099.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/ty2024/mfj-deceased-spouse.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 18e482d45546866e…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#c51c36fe-0587-4134-a24b-95b539bf9916/dateOfBirth 2015-11-06 → 2016-11-06; /filers/#1c52853a-2369-4a40-b119-581a69ca5767/dateOfBirth 1998-03-29 → 1999-03-29; /filers/#8a70def4-2e0a-4d6f-831f-329dd2e1403f/dateOfBirth 2003-02-22 → 2004-02-22; /secondaryFilerDateOfDeath 2024-01-12 → 2025-01-12. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
