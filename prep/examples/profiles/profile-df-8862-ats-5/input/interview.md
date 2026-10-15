# Client interview — Andrew Pope — Direct File scenario 8862-ats-5

**Profile:** `profile-df-8862-ats-5` · **Tax year:** 2025 · **Filing status:** qualifiedSurvivingSpouse

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/8862-ats-5.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Andrew Pope (born 1994-12-27) of 701 Olive Street, Rawlins, WY 82301 file(s) qualifying surviving spouse — IRS Direct File test scenario `8862-ats-5` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Ashley Pope (born 2015-09-29, childOrDescendants); Tatum Pope (born 2020-10-18, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $35,592.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, New York Life, EIN 00-0000029 (box 1 $35,592.00; box 2 $1,947.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/8862-ats-5.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 a69dcabaeb31e682…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#775ae299-7bab-43ca-b9bb-f67a46071bd6/dateOfBirth 2014-09-29 → 2015-09-29; /familyAndHousehold/#f6876bd0-21e9-40fe-8c54-94cfd3f1601b/dateOfBirth 2019-10-18 → 2020-10-18; /filers/#c78eca17-45a3-428d-aa62-df40a08f8b67/dateOfBirth 1993-12-27 → 1994-12-27. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
