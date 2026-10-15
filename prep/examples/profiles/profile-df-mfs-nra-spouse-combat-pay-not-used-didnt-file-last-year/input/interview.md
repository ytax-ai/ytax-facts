# Client interview — Marge Lord — Direct File scenario mfs-nra-spouse-combat-pay-not-used-didnt-file-last-year

**Profile:** `profile-df-mfs-nra-spouse-combat-pay-not-used-didnt-file-last-year` · **Tax year:** 2025 · **Filing status:** marriedFilingSeparately

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfs-nra-spouse-combat-pay-not-used-didnt-file-last-year.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Marge Lord (born 1991-01-01) of 123 Sesame St, Nashua, NH 03301 file(s) married filing separately — IRS Direct File test scenario `mfs-nra-spouse-combat-pay-not-used-didnt-file-last-year` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $8,101.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, DFAS-CL/JFLP, EIN 00-1234567 (box 1 $8,101.00; box 2 $545.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No; spouse: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: Not answered in the scenario; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfs-nra-spouse-combat-pay-not-used-didnt-file-last-year.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 d60d4fe3994dee59…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /filers/#fc190671-ce54-4171-af4e-d029f33c1a7f/dateOfBirth 1990-01-01 → 1991-01-01. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
