# Client interview — Marjorie Simpson — Direct File scenario ticket-12386

**Profile:** `profile-df-ticket-12386` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/ticket-12386.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Marjorie Simpson (born 1956-03-09) and Homer Simpson (born 1961-05-05) of 742 Evergreen Terrace, Springfield, PA 15007 file(s) married filing jointly — IRS Direct File test scenario `ticket-12386` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Lisa Simpson (born 2016-05-05, childOrDescendants).

Income documents on record: 2 Form(s) W-2 totalling $60,001.16 of box 1 wages.

## Documents provided

- 2025 Form W-2, Test Employer, EIN 00-1111111 (box 1 $30,000.58; box 2 $1,000.58; PA box 16 $30,000.58 / box 17 $4,000.58)
- 2025 Form W-2, Test Employer 2, EIN 00-6666666 (box 1 $30,000.58; box 2 $1,000.58; PA box 16 $30,000.58 / box 17 $4,000.58) — spouse's
- Form 2441 provider: TEST TEST, $1,000.58 paid
- Form 2441 provider: care provider, $1,000.58 paid

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/ticket-12386.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 1ff3c046705fcbe6…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#9ee8ac69-e111-497b-b039-7c8a2959c911/dateOfBirth 2015-05-05 → 2016-05-05; /filers/#c2d50c7b-5050-46e7-9eed-fa42a8a23f48/dateOfBirth 1960-05-05 → 1961-05-05; /filers/#d4f83217-544d-449f-9e28-ee6e0bd6400e/dateOfBirth 1955-03-09 → 1956-03-09; /importedPrimaryFilerDateOfBirth 1955-03-09 → 1956-03-09. A W-2 box 4 above 6.2% of boxes 3 + 7, or box 6 above the Medicare rates on box 5, is impossible on a real W-2 and is set to the rate figure — /formW2s/#37be0b59-ecb1-4468-add6-290972aa3e08/writableOasdiWithholding 1000.58 → 620.04; /formW2s/#c5ed208b-bb5d-4ee1-998b-aa60ca574dd0/writableOasdiWithholding 1000.58 → 620.04. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- SCOPE: Direct File flags this return with /formW2s/*/causesDependentCareBenefitsKO — its TY2024 scope excluded W-2 box 10 dependent care benefits. ytax computes Form 2441 Part III (cdcc:/cdccTaxableBenefits, /cdccExcludedBenefitsAmount), so the return is in scope here and resolves Complete; the flag is read by no TY2025 fact.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
