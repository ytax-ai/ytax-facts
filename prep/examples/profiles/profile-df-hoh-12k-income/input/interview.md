# Client interview — marge simpson — Direct File scenario hoh-12k-income

**Profile:** `profile-df-hoh-12k-income` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hoh-12k-income.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

marge simpson (born 1991-10-10) of 1234 Main St apt 2, queensville, NY 10014 file(s) head of household — IRS Direct File test scenario `hoh-12k-income` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Nelson The Cat (born 2012-10-10, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $12,000.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, coforma, EIN 00-4738465 (box 1 $12,000.00; box 2 $100.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hoh-12k-income.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 19dd635ba55c93e7…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#9eecdf4c-6171-44eb-90c4-722afd12715a/dateOfBirth 2011-10-10 → 2012-10-10; /filers/#4fb5fca2-b325-47c7-946e-8020f489c4d6/dateOfBirth 1920-10-10 → 1921-10-10; /filers/#f5b9b7a1-50d1-4e21-abbc-27cb065b19c8/dateOfBirth 1990-10-10 → 1991-10-10. A W-2 box 4 above 6.2% of boxes 3 + 7, or box 6 above the Medicare rates on box 5, is impossible on a real W-2 and is set to the rate figure — /formW2s/#98422df2-afe4-4b8a-8bdc-cc2fecc45dd8/writableOasdiWithholding 100.00 → 6.20. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
