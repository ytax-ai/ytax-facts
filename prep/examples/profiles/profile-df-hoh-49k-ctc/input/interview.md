# Client interview — Test User — Direct File scenario hoh-49k-ctc

**Profile:** `profile-df-hoh-49k-ctc` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hoh-49k-ctc.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Test User (born 1930-01-01) of 1 Street Place North, Beverly Hills, CA 94203 file(s) head of household — IRS Direct File test scenario `hoh-49k-ctc` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: George Washington (born 2014-12-12, childOrDescendants); John Adams (born 2025-01-12, childOrDescendants).

Income documents on record: 2 Form(s) W-2 totalling $50,000.00 of box 1 wages; 2 Form(s) 1099-INT ($1,001.00); 1 Form(s) SSA-1099 ($23,123.00 net); 1 Form(s) 1099-G ($2,198.00).

## Documents provided

- 2025 Form W-2, Some Company, EIN 00-2345543 (box 1 $40,000.00; box 2 $7,000.00; CA box 16 $38,000.00 / box 17 $3,000.00)
- 2025 Form W-2, Second Company, EIN 00-2345234 (box 1 $10,000.00; box 2 $2,000.00)
- 2025 Form 1099-INT, #1 Bank Name (box 1 $1.00)
- 2025 Form 1099-INT, #2 Bank Name (box 1 $1,000.00)
- 2025 Form SSA-1099 (box 5 $23,123.00; box 6 $2,000.00)
- 2025 Form 1099-G, California - Free Cash (box 1 $2,198.00; box 4 $200.00)
- 2025 estimated tax payments: $999.00

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: Yes; IRA contributions: No; K-12 educator: Yes; estimated payments: Yes.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hoh-49k-ctc.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 292327ceaf2d8bb8…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#2d6142ff-50ad-43b7-bd5f-20bd4bd2a282/dateOfBirth 2013-12-12 → 2014-12-12; /familyAndHousehold/#fbda543b-ede3-4395-ad54-a400d2b03561/dateOfBirth 2024-01-12 → 2025-01-12; /filers/#81b0042b-db57-4ed7-af6e-bda579f3a4d5/dateOfBirth 1929-01-01 → 1930-01-01. A W-2 box 4 above 6.2% of boxes 3 + 7, or box 6 above the Medicare rates on box 5, is impossible on a real W-2 and is set to the rate figure — /formW2s/#00578e4e-c567-4b31-bcca-f5dbcd1dca3f/writableMedicareWithholding 950.00 → 478.50; /formW2s/#92660967-aff8-43ad-a9d9-714f68bd9771/writableMedicareWithholding 400.00 → 130.50. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
