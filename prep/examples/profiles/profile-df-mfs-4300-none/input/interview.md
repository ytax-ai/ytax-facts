# Client interview — Homer Simpson — Direct File scenario mfs-4300-none

**Profile:** `profile-df-mfs-4300-none` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfs-4300-none.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Homer Simpson (born 1989-09-09) of 1234 4th st nw, washington, NY 10014 file(s) head of household — IRS Direct File test scenario `mfs-4300-none` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $43,000.00 of box 1 wages; 1 Form(s) 1099-INT ($123.00); 1 Form(s) SSA-1099 ($-300.00 net).

## Documents provided

- 2025 Form W-2, something, EIN 00-1000321 (box 1 $43,000.00; box 2 $1,200.00; NY box 16 $20,000.00 / box 17 $1,000.00)
- 2025 Form 1099-INT, Vanguard (box 1 $123.00)
- 2025 Form SSA-1099 (box 5 $-300.00; box 6 $200.00)
- 2025 estimated tax payments: $1,100.00

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No; spouse: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: No; IRA contributions: No; K-12 educator: Yes; estimated payments: Yes.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfs-4300-none.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 e0cf0f2a24c46048…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#04282192-cc89-47a6-8728-07bc050b580f/dateOfBirth 2002-09-09 → 2003-09-09; /familyAndHousehold/#04282192-cc89-47a6-8728-07bc050b580f/writableChildEmancipationDate 2020-09-09 → 2021-09-09; /filers/#4fe185d4-3cd1-46bf-befb-3627a41c215b/dateOfBirth 1988-09-09 → 1989-09-09. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
