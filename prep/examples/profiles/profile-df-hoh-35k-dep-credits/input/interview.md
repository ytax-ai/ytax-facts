# Client interview — Cat Catface — Direct File scenario HOH-35K-dep-credits

**Profile:** `profile-df-hoh-35k-dep-credits` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/HOH-35K-dep-credits.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Cat Catface (born 1984-10-10) of 123 Cat Street, Cattown, AZ 85001 file(s) head of household — IRS Direct File test scenario `HOH-35K-dep-credits` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Kitten Catface (born 2017-12-12, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $35,000.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, Cats Incorporated, EIN 00-6666666 (box 1 $35,000.00; box 2 $3,000.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/HOH-35K-dep-credits.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 84a3b085e18b4420…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#606efa27-e8b4-4ec1-9f76-ade9c5e83870/dateOfBirth 2016-12-12 → 2017-12-12; /filers/#fd7d7413-cd8d-40b1-b8b8-601078e5bc85/dateOfBirth 1983-10-10 → 1984-10-10. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
