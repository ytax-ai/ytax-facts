# Client interview — Grace Griffin — Direct File scenario mfj-15k

**Profile:** `profile-df-mfj-15k` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mfj-15k.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Grace Griffin (born 1973-05-09) and Jason Ash (born 1976-02-10) of 148 S East St, St Louis, NY 10014 file(s) married filing jointly — IRS Direct File test scenario `mfj-15k` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Jason Ash (born 2004-02-10, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $15,000.00 of box 1 wages; 1 Form(s) 1099-INT ($300.00).

## Documents provided

- 2025 Form W-2, Ajax Corp, EIN 00-0980980 (box 1 $15,000.00; box 2 $2,000.00; NY box 16 $15,000.00 / box 17 $1,500.00)
- 2025 Form 1099-INT, Ajax Corp (box 1 $300.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mfj-15k.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 936a42718b14cb78…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#e65bb83a-c8f5-41b9-b3c3-5629d48d5d4b/dateOfBirth 2003-02-10 → 2004-02-10; /filers/#5a965e67-e945-45a5-9011-aa8b44be4d1e/dateOfBirth 1975-02-10 → 1976-02-10; /filers/#89bb6e83-7920-46c0-9c6e-c781c4473cda/dateOfBirth 1972-05-09 → 1973-05-09. A W-2 box 4 above 6.2% of boxes 3 + 7, or box 6 above the Medicare rates on box 5, is impossible on a real W-2 and is set to the rate figure — /formW2s/#466e936d-b2c0-4ccb-b4bb-71804bad31b5/writableMedicareWithholding 2000.00 → 217.50; /formW2s/#466e936d-b2c0-4ccb-b4bb-71804bad31b5/writableOasdiWithholding 2000.00 → 930.00. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
