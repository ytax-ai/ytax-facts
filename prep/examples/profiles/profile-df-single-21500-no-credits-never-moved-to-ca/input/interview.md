# Client interview — Casey Williams — Direct File scenario single-21500-no-credits-never-moved-to-ca

**Profile:** `profile-df-single-21500-no-credits-never-moved-to-ca` · **Tax year:** 2025 · **Filing status:** single

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/ty2024/single-21500-no-credits-never-moved-to-ca.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Casey Williams (born 1981-01-01) of 123 Great St, Real City, MA 02301 file(s) single — IRS Direct File test scenario `single-21500-no-credits-never-moved-to-ca` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $21,500.00 of box 1 wages; 1 Form(s) 1099-INT ($1,500.00).

## Documents provided

- 2025 Form W-2, Robin Corp, EIN 00-3456789 (box 1 $21,500.00; box 2 $0.00)
- 2025 Form 1099-INT, Acme Bank (box 1 $1,500.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/ty2024/single-21500-no-credits-never-moved-to-ca.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 ca7b4cf3b7849373…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /achPaymentDate 2025-04-12 → 2026-04-12; /filers/#14276ea3-3a5c-43d3-a6e2-d0e6895cac81/dateOfBirth 1980-01-01 → 1981-01-01. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
