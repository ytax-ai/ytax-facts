# Client interview — Andrew Pope — Direct File scenario mef-ats-5

**Profile:** `profile-df-mef-ats-5` · **Tax year:** 2025 · **Filing status:** qualifiedSurvivingSpouse

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mef-ats-5.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Andrew Pope (born 1994-12-27) of 701 Olive Street, Rawlins, WY 82301 file(s) qualifying surviving spouse — IRS Direct File test scenario `mef-ats-5` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Ashley Pope (born 2015-09-29, childOrDescendants); Tatum Pope (born 2020-10-18, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $35,592.00 of box 1 wages; 1 Form(s) 1099-G ($814.00).

## Documents provided

- 2025 Form W-2, New York Life, EIN 00-0000029 (box 1 $35,592.00; box 2 $1,947.00)
- 2025 Form 1099-G, Government (box 1 $814.00; box 4 $0.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mef-ats-5.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 b8db4ca3cd34e3a4…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#1477d5d0-ee20-4a0e-a3b6-330a491c8967/dateOfBirth 2019-10-18 → 2020-10-18; /familyAndHousehold/#cad41efc-79f2-4743-8ae2-06a440b5a87d/dateOfBirth 2014-09-29 → 2015-09-29; /filers/#ba954602-f0b8-4054-b364-5a6e4728109f/dateOfBirth 1993-12-27 → 1994-12-27. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
