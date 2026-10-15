# Client interview — Fanny Brice — Direct File scenario hoh-itin-ctc

**Profile:** `profile-df-hoh-itin-ctc` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hoh-itin-ctc.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Fanny Brice (born 1996-01-01) of 123 Sesame St, Nashua, NH 03301 file(s) head of household — IRS Direct File test scenario `hoh-itin-ctc` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Timmy Testerson (born 2021-01-01, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $25,000.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, Ziegfeld Follies, EIN 00-1234567 (box 1 $25,000.00; box 2 $500.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hoh-itin-ctc.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 e740ed407760d52b…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#c677912c-259c-41f0-8cc5-ff569d1a708d/dateOfBirth 2020-01-01 → 2021-01-01; /filers/#f7b2e8e0-c838-4b59-891e-a72e8f76d685/dateOfBirth 1995-01-01 → 1996-01-01. A W-2 box 4 above 6.2% of boxes 3 + 7, or box 6 above the Medicare rates on box 5, is impossible on a real W-2 and is set to the rate figure — /formW2s/#aead9e05-d32f-443e-a577-b58fbb623a74/writableMedicareWithholding 363.00 → 36.25. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
