# Client interview — Bertha Brown — Direct File scenario hoh-35k

**Profile:** `profile-df-hoh-35k` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hoh-35k.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Bertha Brown (born 1981-01-01) of 123 Muffin Road, New York, NY 10014 file(s) head of household — IRS Direct File test scenario `hoh-35k` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Booper Brown (born 2022-01-01, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $35,000.00 of box 1 wages; 1 Form(s) 1099-INT ($500.00).

## Documents provided

- 2025 Form W-2, Writer Co., EIN 00-1000000 (box 1 $35,000.00; box 2 $300.00)
- 2025 Form 1099-INT, Writer Co. (box 1 $500.00)
- 2025 estimated tax payments: $400.00

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hoh-35k.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 f853cf3e0c260d55…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#d09ae8b5-6ab4-4384-943f-ab3a795f429a/dateOfBirth 2021-01-01 → 2022-01-01; /filers/#e23d78eb-acd3-49de-8d1f-84ebdaa58ab4/dateOfBirth 1980-01-01 → 1981-01-01. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
