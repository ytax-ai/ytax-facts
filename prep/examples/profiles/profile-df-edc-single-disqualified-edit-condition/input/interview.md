# Client interview — Samuel Smith — Direct File scenario edc-single-disqualified-edit-condition

**Profile:** `profile-df-edc-single-disqualified-edit-condition` · **Tax year:** 2025 · **Filing status:** single

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/edc-single-disqualified-edit-condition.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Samuel Smith (born 1993-08-02) of 413 Maple Street, Panama City, FL 32401 file(s) single — IRS Direct File test scenario `edc-single-disqualified-edit-condition` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $16,000.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, Testers R Us, EIN 00-2222314 (box 1 $16,000.00; box 2 $0.00)
- 2025 estimated tax payments: $425.00

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No; spouse: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: No; IRA contributions: No; K-12 educator: Yes; estimated payments: Yes.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/edc-single-disqualified-edit-condition.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 86be65c82c75b9d7…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /filers/#046c72a2-d64a-45f2-ac25-34af70f0fd2e/dateOfBirth 1965-03-19 → 1966-03-19; /filers/#21c742ca-8fef-4b5b-b2ff-169185154a2b/dateOfBirth 1992-08-02 → 1993-08-02. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
