# Client interview — Sam Singleton — Direct File scenario single-33k-no_credits

**Profile:** `profile-df-single-33k-no-credits` · **Tax year:** 2025 · **Filing status:** single

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/ty2024/single-33k-no_credits.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Sam Singleton (born 1998-10-03) of 1111 Constitution Ave, Washington, CA 94203 file(s) single — IRS Direct File test scenario `single-33k-no_credits` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $33,333.00 of box 1 wages; 1 Form(s) 1099-INT ($1,000.00).

## Documents provided

- 2025 Form W-2, MTV, EIN 00-2394905 (box 1 $33,333.00; box 2 $1,234.00; CA box 16 $33,333.00 / box 17 $300.00)
- 2025 Form 1099-INT, Bank of Money (box 1 $1,000.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/ty2024/single-33k-no_credits.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 5f9fe02556004b6e…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /achPaymentDate 2025-04-15 → 2026-04-15; /filers/#acf14a3a-c258-4815-a74b-affabb9e2bb3/dateOfBirth 1997-10-03 → 1998-10-03. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
