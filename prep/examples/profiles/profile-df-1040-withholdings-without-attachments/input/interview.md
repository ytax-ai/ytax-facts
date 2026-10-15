# Client interview — Staale Svensen — Direct File scenario 1040-withholdings-without-attachments

**Profile:** `profile-df-1040-withholdings-without-attachments` · **Tax year:** 2025 · **Filing status:** single

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/1040-withholdings-without-attachments.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Staale Svensen (born 1993-11-16) of 25 E 55 St, New York, NY 10014 file(s) single — IRS Direct File test scenario `1040-withholdings-without-attachments` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 3 Form(s) 1099-R ($90,985.56 gross).

## Documents provided

- 2025 Form 1099-R, Mastodon Retirement Services (box 1 $12,992.75; box 2a $9,122.04; box 4 $911.75; code 7)
- 2025 Form 1099-R, Event Horizon Investments (box 1 $57,992.81; box 2a $0.00; box 4 $0.00; code GB)
- 2025 Form 1099-R, Infidelity Investments (box 1 $20,000.00; box 2a $20,000.00; box 4 $1,507.51; code 7B)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/1040-withholdings-without-attachments.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 bdbe84aabf0e1fc8…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /filers/#bffe2d91-48da-405b-a210-86b7432512e1/dateOfBirth 1992-11-16 → 1993-11-16; /importedPrimaryFilerDateOfBirth 1992-11-16 → 1993-11-16. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
