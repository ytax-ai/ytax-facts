# Client interview — Marge Simpson — Direct File scenario mfs-20k-no-credits

**Profile:** `profile-df-mfs-20k-no-credits` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfs-20k-no-credits.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Marge Simpson (born 1995-05-10) of 123 main, placeholder, NY 10014 file(s) head of household — IRS Direct File test scenario `mfs-20k-no-credits` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Maggie Simpson (born 1995-01-03, siblingOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $45,000.00 of box 1 wages; 1 Form(s) 1099-INT ($1,000.00).

## Documents provided

- 2025 Form W-2, IRS, EIN 00-3456789 (box 1 $45,000.00; box 2 $4,000.00; NY box 16 $123.00 / box 17 $123.00)
- 2025 Form 1099-INT, Cathay Bank (box 1 $1,000.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfs-20k-no-credits.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 b3f2e4412152664e…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#e1ac3565-557f-41f8-8c20-5b21cf5fd061/dateOfBirth 1994-01-03 → 1995-01-03; /familyAndHousehold/#e1ac3565-557f-41f8-8c20-5b21cf5fd061/writableChildEmancipationDate 2012-01-03 → 2013-01-03; /filers/#6a956021-6423-4b34-8da8-b18bc0ca1935/dateOfBirth 1994-05-10 → 1995-05-10. A W-2 box 4 above 6.2% of boxes 3 + 7, or box 6 above the Medicare rates on box 5, is impossible on a real W-2 and is set to the rate figure — /formW2s/#6144fd65-6e4c-47e2-8282-3ce7c6fb1add/writableOasdiWithholding 2000.00 → 124.00. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
