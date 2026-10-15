# Client interview — Lisa Simpson — Direct File scenario cdcc-mfj-dep-care-benefits-only

**Profile:** `profile-df-cdcc-mfj-dep-care-benefits-only` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/cdcc-mfj-dep-care-benefits-only.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Lisa Simpson (born 1996-10-10) and Taylor Doe (born 1996-01-01) of 123 Sesame St, Springfield, TN 37011 file(s) married filing jointly — IRS Direct File test scenario `cdcc-mfj-dep-care-benefits-only` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: DepOne Truth (born 2022-04-22, childOrDescendants).

Income documents on record: 2 Form(s) W-2 totalling $29,000.00 of box 1 wages; 1 Form(s) 1099-G ($4,634.00).

## Documents provided

- 2025 Form W-2, SPRINGFIELD ATOMIC POWER AND LIGHT, EIN 00-3456789 (box 1 $7,000.00; box 2 $0.00)
- 2025 Form W-2, Altitude, EIN 00-1234233 (box 1 $22,000.00; box 2 $0.00) — spouse's
- 2025 Form 1099-G, Payer (box 1 $4,634.00; box 4 $60.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/cdcc-mfj-dep-care-benefits-only.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 b1f82e27c118dfcc…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#9d2b2ec6-9db3-46c9-8903-8c1e808b7c89/dateOfBirth 2021-04-22 → 2022-04-22; /filers/#12617845-ee97-41f6-bc0b-41d67a2e924e/dateOfBirth 1995-10-10 → 1996-10-10; /filers/#6cd2599b-6e55-4eac-8517-5d922e32d904/dateOfBirth 1995-01-01 → 1996-01-01; /importedPrimaryFilerDateOfBirth 1995-10-10 → 1996-10-10. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- SCOPE: Direct File flags this return with /formW2s/*/causesDependentCareBenefitsKO — its TY2024 scope excluded W-2 box 10 dependent care benefits. ytax computes Form 2441 Part III (cdcc:/cdccTaxableBenefits, /cdccExcludedBenefitsAmount), so the return is in scope here and resolves Complete; the flag is read by no TY2025 fact.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
