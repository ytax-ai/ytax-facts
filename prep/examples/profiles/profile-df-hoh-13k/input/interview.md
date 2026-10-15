# Client interview — Schnauzer McSchnauzerson — Direct File scenario hoh-13k

**Profile:** `profile-df-hoh-13k` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hoh-13k.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Schnauzer McSchnauzerson (born 1976-07-19) of 123 Main Street apartment 5, Chattanooga, TN 37011 file(s) head of household — IRS Direct File test scenario `hoh-13k` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Jay Kay (born 1992-01-01, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $12,500.00 of box 1 wages; 2 Form(s) 1099-G ($2,000.00).

## Documents provided

- 2025 Form W-2, United States of America, EIN 00-1111111 (box 1 $12,500.00; box 2 $500.00)
- 2025 Form 1099-G, Mayor Tim Kelley (box 1 $1,000.00; box 4 $0.00)
- 2025 Form 1099-G, Mayor Tim Kelley (box 1 $1,000.00; box 4 $0.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: Yes; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hoh-13k.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 dbf03845474e341b…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#2b39b3eb-119b-4aec-8115-9b1d3eecfd35/dateOfBirth 1991-01-01 → 1992-01-01; /filers/#b8f6e5a0-5c35-482c-8bd2-5cb896cb6fdd/dateOfBirth 1975-07-19 → 1976-07-19. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
