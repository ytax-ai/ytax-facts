# Client interview — Mr Potato Head of Household — Direct File scenario single-eitc-agi-exceeds-earned-income

**Profile:** `profile-df-single-eitc-agi-exceeds-earned-income` · **Tax year:** 2025 · **Filing status:** single

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/single-eitc-agi-exceeds-earned-income.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Mr Potato Head of Household (born 1986-01-23) of 2345 Spud Way, Manteca, CA 90210 file(s) single — IRS Direct File test scenario `single-eitc-agi-exceeds-earned-income` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $7,300.00 of box 1 wages; 1 Form(s) 1099-G ($8,502.00).

## Documents provided

- 2025 Form W-2, Happy Tuber Farms, EIN 00-2399211 (box 1 $7,300.00; box 2 $300.00)
- 2025 Form 1099-G, State of California (box 1 $8,502.00; box 4 $920.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/single-eitc-agi-exceeds-earned-income.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 b231be6d586aadfa…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /filers/#56717ca8-2607-4f6b-becf-a8463d762c06/dateOfBirth 1985-01-23 → 1986-01-23. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
