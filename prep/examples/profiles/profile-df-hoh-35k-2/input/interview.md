# Client interview — James Hariot — Direct File scenario hoh-35k-2

**Profile:** `profile-df-hoh-35k-2` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hoh-35k-2.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

James Hariot (born 2001-10-10) of 123 Test Lane, Testtown, NY 10014 file(s) head of household — IRS Direct File test scenario `hoh-35k-2` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Tia Testopolis (born 2012-10-10, siblingOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $35,000.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, Tenacious Testers, Inc., EIN 00-1111111 (box 1 $35,000.00; box 2 $800.00; NY box 16 — / box 17 $800.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hoh-35k-2.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 7b382b953397c1f8…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#7719ff80-0a4e-4b99-8ec9-17253a0b7ff0/dateOfBirth 2011-10-10 → 2012-10-10; /filers/#469a96ec-c09a-4720-8146-54ba67667a33/dateOfBirth 2000-10-10 → 2001-10-10. A W-2 box 4 above 6.2% of boxes 3 + 7, or box 6 above the Medicare rates on box 5, is impossible on a real W-2 and is set to the rate figure — /formW2s/#14a1e66d-ccf8-4748-a6ad-fa37889e95c8/writableMedicareWithholding 600.00 → 507.50. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
