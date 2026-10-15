# Client interview — Dobbie Elf — Direct File scenario qss-34K-ctc-2dependents

**Profile:** `profile-df-qss-34k-ctc-2dependents` · **Tax year:** 2025 · **Filing status:** qualifiedSurvivingSpouse

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/qss-34K-ctc-2dependents.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Dobbie Elf (born 2000-04-21) of 88 Dirth Lane Apt D, Oberlin, MA 02301 file(s) qualifying surviving spouse — IRS Direct File test scenario `qss-34K-ctc-2dependents` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Dobbie Elf (born 2014-03-25, childOrDescendants); dumb second (born 2017-08-23, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $34,000.00 of box 1 wages; 1 Form(s) 1099-INT ($13.88); 1 Form(s) SSA-1099 ($8,005.00 net).

## Documents provided

- 2025 Form W-2, Rainbows Inc., EIN 00-1212121 (box 1 $34,000.00; box 2 $6,023.12; MA box 16 $34,000.00 / box 17 $503.00)
- 2025 Form 1099-INT, FFFCU (box 1 $13.88)
- 2025 Form SSA-1099 (box 5 $8,005.00; box 6 $0.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: Yes; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/qss-34K-ctc-2dependents.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 6eeb95ee9b7d2fea…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#8973097c-5b46-4dd6-9f21-dfe07a9ea82b/dateOfBirth 2013-03-25 → 2014-03-25; /familyAndHousehold/#8b1c8ecb-0743-4323-bc25-438389a70ba1/dateOfBirth 2016-08-23 → 2017-08-23; /filers/#dccb2612-e7ee-4242-99e2-c03f4eed3ca2/dateOfBirth 1999-04-21 → 2000-04-21. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
