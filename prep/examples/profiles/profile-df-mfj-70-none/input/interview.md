# Client interview — Hot Wheels — Direct File scenario mfj-70-none

**Profile:** `profile-df-mfj-70-none` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfj-70-none.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Hot Wheels (born 1996-01-01) and cold wheels (born 1995-01-02) of 123 Main St, New York, NY 10014 file(s) married filing jointly — IRS Direct File test scenario `mfj-70-none` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $70,000.00 of box 1 wages; 1 Form(s) 1099-INT ($1,499.00); 1 Form(s) 1099-G ($30,000.00).

## Documents provided

- 2025 Form W-2, Wheels Co., EIN 00-8888888 (box 1 $70,000.00; box 2 $15,000.00; NY box 16 $70,000.00 / box 17 $15,000.00)
- 2025 Form 1099-INT, Gert Unlimited (box 1 $1,499.00)
- 2025 Form 1099-G, Speckle Dust LLC (box 1 $30,000.00; box 4 $0.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfj-70-none.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 8b0acef05fbdfb11…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /filers/#35f3405b-b196-46d0-a0f4-f8b4dcaf97ba/dateOfBirth 1994-01-02 → 1995-01-02; /filers/#7397cf0a-5866-403e-ba0b-40dcffe442ab/dateOfBirth 1995-01-01 → 1996-01-01. A W-2 box 4 above 6.2% of boxes 3 + 7, or box 6 above the Medicare rates on box 5, is impossible on a real W-2 and is set to the rate figure — /formW2s/#c5d398cc-f754-4049-8bf3-fc1ecc079efb/writableMedicareWithholding 15000.00 → 1015.00; /formW2s/#c5d398cc-f754-4049-8bf3-fc1ecc079efb/writableOasdiWithholding 15000.00 → 4340.00. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
