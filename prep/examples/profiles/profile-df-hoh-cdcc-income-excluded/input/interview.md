# Client interview — Test Testerface — Direct File scenario hoh-cdcc-income-excluded

**Profile:** `profile-df-hoh-cdcc-income-excluded` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hoh-cdcc-income-excluded.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Test Testerface (born 1988-11-11) of 123 sesame st, new york, NY 10014 file(s) head of household — IRS Direct File test scenario `hoh-cdcc-income-excluded` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Uno testerface (born 2017-11-11, childOrDescendants); Duo testerface (born 2020-11-11, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $50,000.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, USDS, EIN 00-1111111 (box 1 $50,000.00; box 2 $1,000.00)
- Form 2441 provider: Mrs Doubtfire, $2,000.00 paid

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hoh-cdcc-income-excluded.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 b7993e552d954886…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#60c874b4-bb7b-4c82-8550-5555b2b585f8/dateOfBirth 2016-11-11 → 2017-11-11; /familyAndHousehold/#93e7961f-dd7b-4c7f-9430-bb597123935f/dateOfBirth 2019-11-11 → 2020-11-11; /filers/#304ae232-4e05-4a26-8394-b583ef1c55aa/dateOfBirth 1987-11-11 → 1988-11-11. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- SCOPE: Direct File flags this return with /formW2s/*/causesDependentCareBenefitsKO — its TY2024 scope excluded W-2 box 10 dependent care benefits. ytax computes Form 2441 Part III (cdcc:/cdccTaxableBenefits, /cdccExcludedBenefitsAmount), so the return is in scope here and resolves Complete; the flag is read by no TY2025 fact.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
