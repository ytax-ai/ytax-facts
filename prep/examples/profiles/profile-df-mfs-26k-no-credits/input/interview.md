# Client interview — Nora Ceampach — Direct File scenario mfs-26k-no_credits

**Profile:** `profile-df-mfs-26k-no-credits` · **Tax year:** 2025 · **Filing status:** marriedFilingSeparately

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfs-26k-no_credits.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Nora Ceampach (born 2006-04-15) of Ten 43rd 1/2 St, Pittsburgh, WY 83002 file(s) married filing separately — IRS Direct File test scenario `mfs-26k-no_credits` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $26,000.00 of box 1 wages; 1 Form(s) 1099-INT ($5.56); 1 Form(s) 1099-G ($700.00).

## Documents provided

- 2025 Form W-2, Testing Co, EIN 00-7777777 (box 1 $26,000.00; box 2 $1,600.00)
- 2025 Form 1099-INT, Blah Bank (box 1 $5.56)
- 2025 Form 1099-G, Wyoming (box 1 $700.00; box 4 $0.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: Yes; spouse: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: Not answered in the scenario; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfs-26k-no_credits.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 161695774ba61a3c…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /filers/#d9bf58cb-21b7-482f-b400-0ad62c9d6be4/dateOfBirth 2005-04-15 → 2006-04-15. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
