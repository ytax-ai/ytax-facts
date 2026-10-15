# Client interview — Optimus Prime — Direct File scenario qss-12k

**Profile:** `profile-df-qss-12k` · **Tax year:** 2025 · **Filing status:** qualifiedSurvivingSpouse

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/qss-12k.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Optimus Prime (born 1951-09-09) of 123 Main ST NW, Canton, AZ 85001 file(s) qualifying surviving spouse — IRS Direct File test scenario `qss-12k` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $12,000.00 of box 1 wages; 1 Form(s) 1099-INT ($500.00).

## Documents provided

- 2025 Form W-2, Robots In Disguise, EIN 00-9999999 (box 1 $12,000.00; box 2 $300.00)
- 2025 Form 1099-INT, Robots R Us (box 1 $500.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/qss-12k.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 5d0230b288971fdb…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#c027236c-4514-4bc8-874b-e1aae71126e2/dateOfBirth 2022-09-13 → 2023-09-13; /filers/#ecefb630-13ae-45b5-a508-abf06c88de4e/dateOfBirth 1950-09-09 → 1951-09-09. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
