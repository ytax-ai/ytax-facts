# Client interview — Edith Beale — Direct File scenario qss-additional-standard-deduction-disabled-eic-ip-pin-other-withholding

**Profile:** `profile-df-qss-additional-standard-deduction-disabled-eic-ip-pin-other-withholding` · **Tax year:** 2025 · **Filing status:** qualifiedSurvivingSpouse

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/qss-additional-standard-deduction-disabled-eic-ip-pin-other-withholding.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Edith Beale (born 1953-01-01) of 3 West End Road, East Hampton, NH 03301 file(s) qualifying surviving spouse — IRS Direct File test scenario `qss-additional-standard-deduction-disabled-eic-ip-pin-other-withholding` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Edith Beale (born 1972-04-15, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $25,000.00 of box 1 wages; 1 Form(s) 1099-INT ($1,499.00); 1 Form(s) SSA-1099 ($28,000.00 net).

## Documents provided

- 2025 Form W-2, Odd Jobs Co, EIN 00-1234567 (box 1 $25,000.00; box 2 $0.00)
- 2025 Form 1099-INT, The Bank (box 1 $1,499.00)
- 2025 Form SSA-1099 (box 5 $28,000.00; box 6 $20.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/qss-additional-standard-deduction-disabled-eic-ip-pin-other-withholding.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 f9fa5d796891d89e…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#7ce42bed-ff73-4856-b775-10c27cf3383a/dateOfBirth 1971-04-15 → 1972-04-15; /filers/#9621489e-3361-4083-96fc-4c0ae6b3dc8c/dateOfBirth 1952-01-01 → 1953-01-01. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
