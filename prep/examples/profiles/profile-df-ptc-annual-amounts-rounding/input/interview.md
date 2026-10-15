# Client interview — Alice Test — Direct File scenario ptc-annual-amounts-rounding

**Profile:** `profile-df-ptc-annual-amounts-rounding` · **Tax year:** 2025 · **Filing status:** marriedFilingSeparately

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/ty2024/ptc-annual-amounts-rounding.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Alice Test (born 1991-10-10) of 123 Main St, dfsa, CA 90210 file(s) married filing separately — IRS Direct File test scenario `ptc-annual-amounts-rounding` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $45,000.00 of box 1 wages; 1 Form(s) 1099-INT ($100.00). Also on record, without a rendered facsimile: 1095As.

## Documents provided

- 2025 Form W-2, Bank, EIN 00-9748329 (box 1 $45,000.00; box 2 $0.00)
- 2025 Form 1099-INT, bank (box 1 $100.00)
- 1 item(s) in /1095As — carried as facts, no facsimile

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No; spouse: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: No; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/ty2024/ptc-annual-amounts-rounding.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 36f030d813e562c2…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /1095As/#013c7812-f552-4f16-a640-c78e5c578823/writablePolicyEndDate 2024-12-12 → 2025-12-12; /1095As/#013c7812-f552-4f16-a640-c78e5c578823/writablePolicyStartDate 2024-01-20 → 2025-01-20; /filers/#fcf986d5-47fc-4c4a-abb8-bdd63abe93a9/dateOfBirth 1990-10-10 → 1991-10-10. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
