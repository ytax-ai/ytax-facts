# Client interview — Minnie Mouse — Direct File scenario HOH-32k-EITC

**Profile:** `profile-df-hoh-32k-eitc` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/HOH-32k-EITC.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Minnie Mouse (born 1990-04-03) of 123 Disney Lane, Orlando, FL 32401 file(s) head of household — IRS Direct File test scenario `HOH-32k-EITC` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Donald Duckerton (born 2017-05-01, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $32,000.00 of box 1 wages; 1 Form(s) 1099-INT ($34.00).

## Documents provided

- 2025 Form W-2, Disney World, EIN 00-5678909 (box 1 $32,000.00; box 2 $8,000.00; FL box 16 — / box 17 $4,000.00)
- 2025 Form 1099-INT, Goofy's bank (box 1 $34.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: Yes.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: No; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/HOH-32k-EITC.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 16a70e2022e3db9a…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#abac80a8-db81-44dc-9aae-12a134dafd73/dateOfBirth 2016-05-01 → 2017-05-01; /filers/#f5a7722f-5a2f-4653-886b-ba1fbb633b77/dateOfBirth 1989-04-03 → 1990-04-03. A W-2 box 4 above 6.2% of boxes 3 + 7, or box 6 above the Medicare rates on box 5, is impossible on a real W-2 and is set to the rate figure — /formW2s/#3c8bb910-c529-4369-810b-1e60e32c3d73/writableMedicareWithholding 2000.00 → 464.00; /formW2s/#3c8bb910-c529-4369-810b-1e60e32c3d73/writableOasdiWithholding 5000.00 → 1984.00. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
