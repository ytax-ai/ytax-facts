# Client interview — Wendy Wallaby — Direct File scenario mef-ats-balance-due

**Profile:** `profile-df-mef-ats-balance-due` · **Tax year:** 2025 · **Filing status:** single

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/ty2024/mef-ats-balance-due.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Wendy Wallaby (born 1989-03-04) of 123 Main St, Port St Lucie, FL 34984 file(s) single — IRS Direct File test scenario `mef-ats-balance-due` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $100,000.00 of box 1 wages; 1 Form(s) 1099-INT ($1,000.00).

## Documents provided

- 2025 Form W-2, Golden Lasso Co, EIN 00-1234567 (box 1 $100,000.00; box 2 $2,400.00)
- 2025 Form 1099-INT, Test (box 1 $1,000.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: Not answered in the scenario; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/ty2024/mef-ats-balance-due.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 b36c8c2ceee7493d…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /achPaymentDate 2025-04-15 → 2026-04-15; /filers/#45058e1f-2caf-4345-afcc-c9b788932df1/dateOfBirth 1988-03-04 → 1989-03-04. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
