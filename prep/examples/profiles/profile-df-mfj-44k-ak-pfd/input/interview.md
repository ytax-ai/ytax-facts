# Client interview — Bob Smith — Direct File scenario mfj-44k-ak-pfd

**Profile:** `profile-df-mfj-44k-ak-pfd` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/ty2024/mfj-44k-ak-pfd.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Bob Smith (born 1981-03-05) and Sally Richards (born 1982-08-15) of 123 Main St, Los Angeles, AK 99501 file(s) married filing jointly — IRS Direct File test scenario `mfj-44k-ak-pfd` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Billy Smith (born 2022-07-16, childOrDescendants); Richard Manfield (born 2023-02-02, childOrDescendants).

Income documents on record: 2 Form(s) W-2 totalling $81,096.00 of box 1 wages; 1 Form(s) 1099-INT ($1,500.00). Also on record, without a rendered facsimile: form1099Miscs.

## Documents provided

- 2025 Form W-2, Transom Corp, EIN 00-4514859 (box 1 $43,512.00; box 2 $784.00)
- 2025 Form W-2, Hammock operations inc, EIN 00-4548188 (box 1 $37,584.00; box 2 $0.00) — spouse's
- 2025 Form 1099-INT, Mail-a-Ham (box 1 $1,500.00)
- 2 item(s) in /form1099Miscs — carried as facts, no facsimile

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/ty2024/mfj-44k-ak-pfd.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 c582af467dc1a487…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /achPaymentDate 2025-04-15 → 2026-04-15; /familyAndHousehold/#44a34635-2101-44b7-a6f8-d30f6c5c87dd/dateOfBirth 2022-02-02 → 2023-02-02; /familyAndHousehold/#8a85cb6d-9c18-4720-bf1e-ed518b17d154/dateOfBirth 2021-07-16 → 2022-07-16; /familyAndHousehold/#cbd23888-cc8c-4b4d-b08a-6525a8b5db36/dateOfBirth 1996-07-06 → 1997-07-06; /filers/#5e7d111f-5ae6-4933-93de-5683e8dd725b/dateOfBirth 1980-03-05 → 1981-03-05; /filers/#df3b9333-94f7-41bb-8d5d-dd9918525793/dateOfBirth 1981-08-15 → 1982-08-15. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
