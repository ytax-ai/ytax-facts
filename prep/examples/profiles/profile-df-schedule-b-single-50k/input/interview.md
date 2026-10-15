# Client interview — Britney Spears — Direct File scenario schedule-b-single-50k

**Profile:** `profile-df-schedule-b-single-50k` · **Tax year:** 2025 · **Filing status:** single

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/ty2024/schedule-b-single-50k.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Britney Spears (born 1986-05-04) of 123 Main Street, Hollywood, FL 32401 file(s) single — IRS Direct File test scenario `schedule-b-single-50k` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $46,000.00 of box 1 wages; 2 Form(s) 1099-INT ($5,001.32).

## Documents provided

- 2025 Form W-2, the Man, EIN 00-9099999 (box 1 $46,000.00; box 2 $5,000.00)
- 2025 Form 1099-INT, Local Bank (box 1 $3,000.77)
- 2025 Form 1099-INT, Local Bank 2 (box 1 $2,000.55)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: Yes; spouse: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: No; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/ty2024/schedule-b-single-50k.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 d081d3651f962871…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /achPaymentDate 2025-04-15 → 2026-04-15; /familyAndHousehold/#a08a50d0-7a18-4200-b208-9de096b49e1e/dateOfBirth 2015-09-09 → 2016-09-09; /filers/#c111a9f0-9830-4307-aafd-fdc9a4df4336/dateOfBirth 1985-05-04 → 1986-05-04. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
