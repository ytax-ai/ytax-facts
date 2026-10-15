# Client interview — Roberto Gonzalez — Direct File scenario mef-ats-1040sr-eic

**Profile:** `profile-df-mef-ats-1040sr-eic` · **Tax year:** 2025 · **Filing status:** marriedFilingSeparately

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mef-ats-1040sr-eic.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Roberto Gonzalez (born 1956-01-17) of 500 Little New York Way, Dallas, NH 03275 file(s) married filing separately — IRS Direct File test scenario `mef-ats-1040sr-eic` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Roberto Gonzalez (born 2023-07-20, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $5,728.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, Giants Foodie, EIN 00-0000024 (box 1 $5,728.00; box 2 $261.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No; spouse: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: Not answered in the scenario; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mef-ats-1040sr-eic.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 fe97a92ca359ee74…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#182e52d8-282a-4542-9ef2-a85406913732/dateOfBirth 2022-07-20 → 2023-07-20; /filers/#a9dceff8-aa06-4e58-8d3d-66059f10c05b/dateOfBirth 1955-01-17 → 1956-01-17. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
