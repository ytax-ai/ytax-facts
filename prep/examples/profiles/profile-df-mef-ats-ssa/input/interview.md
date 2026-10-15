# Client interview — Susan Miranda — Direct File scenario mef-ats-SSA

**Profile:** `profile-df-mef-ats-ssa` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/mef-ats-SSA.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Susan Miranda (born 1963-01-16) and John Symmetry (born 1960-01-01) of 2030 Pecan Street, Monroe, MA 02301 file(s) married filing jointly — IRS Direct File test scenario `mef-ats-SSA` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $24,469.00 of box 1 wages; 1 Form(s) 1099-INT ($1,499.00); 2 Form(s) SSA-1099 ($29,102.00 net).

## Documents provided

- 2025 Form W-2, Magnolia Floral Design, EIN 00-0000007 (box 1 $24,469.00; box 2 $5,869.00; MA box 16 $24,469.00 / box 17 $1,502.00)
- 2025 Form 1099-INT, Payer (box 1 $1,499.00)
- 2025 Form SSA-1099 (box 5 $12,038.00; box 6 $817.00)
- 2025 Form SSA-1099 (box 5 $17,064.00; box 6 $921.00) — spouse's

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/mef-ats-SSA.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 a714f17ec5435227…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /filers/#dc4aaf0d-b565-4ae7-af72-060d3c6992fd/dateOfBirth 1962-01-16 → 1963-01-16; /filers/#f49e45b4-28d2-483b-826a-a013e767810c/dateOfBirth 1959-01-01 → 1960-01-01. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
