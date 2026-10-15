# Client interview — Boris Smith — Direct File scenario hoh-13936-actc-eitc

**Profile:** `profile-df-hoh-13936-actc-eitc` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hoh-13936-actc-eitc.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Boris Smith (born 1981-02-01) of 1011 Ave A, New york, NY 10014 file(s) head of household — IRS Direct File test scenario `hoh-13936-actc-eitc` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Mary Smith (born 2022-01-23, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $12,452.00 of box 1 wages; 1 Form(s) 1099-INT ($235.02); 1 Form(s) 1099-G ($1,249.30).

## Documents provided

- 2025 Form W-2, Fishy fish Inc., EIN 00-3534535 (box 1 $12,452.00; box 2 $0.00)
- 2025 Form 1099-INT, Ally (box 1 $235.02)
- 2025 Form 1099-G, Government agency (box 1 $1,249.30; box 4 $0.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hoh-13936-actc-eitc.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 eea1670aedba6ac8…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#18ed77ea-0f7c-40e1-8037-2c8c7febb053/dateOfBirth 2021-01-23 → 2022-01-23; /filers/#e1486241-e334-4260-90cc-26b20924a5de/dateOfBirth 1980-02-01 → 1981-02-01. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
