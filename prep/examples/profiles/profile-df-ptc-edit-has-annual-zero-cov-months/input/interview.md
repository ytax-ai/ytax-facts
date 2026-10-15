# Client interview — Tom Simpson — Direct File scenario ptc-edit-has-annual-zero-cov-months

**Profile:** `profile-df-ptc-edit-has-annual-zero-cov-months` · **Tax year:** 2025 · **Filing status:** single

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/ty2024/ptc-edit-has-annual-zero-cov-months.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Tom Simpson (born 1956-03-09) of 742 Evergreen Terrace, wasilla, AK 99501 file(s) single — IRS Direct File test scenario `ptc-edit-has-annual-zero-cov-months` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 2 Form(s) W-2 totalling $58,300.00 of box 1 wages. Also on record, without a rendered facsimile: 1095As.

## Documents provided

- 2025 Form W-2, SPRINGFIELD ATOMIC POWER AND LIGHT, EIN 00-3456789 (box 1 $3,000.00; box 2 $0.00)
- 2025 Form W-2, Dog Catcher Inc, EIN 00-2334345 (box 1 $55,300.00; box 2 $5,000.00)
- 1 item(s) in /1095As — carried as facts, no facsimile

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/ty2024/ptc-edit-has-annual-zero-cov-months.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 1be5e6e213eac7bd…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /1095As/#b3c2a745-040c-4e36-b1c2-b9f377c422df/writablePolicyEndDate 2024-12-31 → 2025-12-31; /1095As/#b3c2a745-040c-4e36-b1c2-b9f377c422df/writablePolicyStartDate 2024-01-01 → 2025-01-01; /filers/#a18c3ed5-b8e1-446b-89cf-dc8fed682bd9/dateOfBirth 1955-03-09 → 1956-03-09; /importedPrimaryFilerDateOfBirth 1955-03-09 → 1956-03-09. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
