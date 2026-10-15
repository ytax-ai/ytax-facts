# Client interview — Mango Test — Direct File scenario hoh-40k-2

**Profile:** `profile-df-hoh-40k-2` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hoh-40k-2.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Mango Test (born 1981-01-01) of 123 main st, washington, CA 94203 file(s) head of household — IRS Direct File test scenario `hoh-40k-2` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Apricot Tester (born 2004-02-01, childOrDescendants); Apple Tester (born 2009-01-16, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $40,000.00 of box 1 wages; 2 Form(s) 1099-INT ($238.00); 1 Form(s) SSA-1099 ($377.00 net); 1 Form(s) 1099-G ($1,700.00).

## Documents provided

- 2025 Form W-2, gordon, EIN 00-3000000 (box 1 $40,000.00; box 2 $0.00)
- 2025 Form 1099-INT, HSBC (box 1 $137.00)
- 2025 Form 1099-INT, Samsung (box 1 $101.00)
- 2025 Form SSA-1099 (box 5 $377.00; box 6 $0.00)
- 2025 Form 1099-G, yes (box 1 $1,700.00; box 4 $0.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hoh-40k-2.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 de40b53256c0bdb3…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#bdb73e16-be14-4511-a504-963a1c93f8a0/dateOfBirth 2003-02-01 → 2004-02-01; /familyAndHousehold/#c431dda5-6778-4e2b-9f7d-f51f6380b18d/dateOfBirth 2008-01-16 → 2009-01-16; /filers/#8964b791-2817-482d-a52c-855af9d8d982/dateOfBirth 1980-01-01 → 1981-01-01. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
