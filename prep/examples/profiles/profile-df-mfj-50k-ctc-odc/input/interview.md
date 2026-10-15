# Client interview — Jeffrey Spaulding — Direct File scenario mfj-50k-ctc-odc

**Profile:** `profile-df-mfj-50k-ctc-odc` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/ty2024/mfj-50k-ctc-odc.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Jeffrey Spaulding (born 1987-02-18) and Margaret Rittenhouse (born 1941-03-04) of 321 Subordinate Ave, Metropolis, AZ 85001 file(s) married filing jointly — IRS Direct File test scenario `mfj-50k-ctc-odc` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Zeppo Jamison (born 1992-04-05, notRelated); Calvin Spaulding (born 1993-04-05, childOrDescendants); Jeffrey Spaulding (born 2023-06-07, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $49,999.99 of box 1 wages; 1 Form(s) 1099-INT ($1.35).

## Documents provided

- 2025 Form W-2, Endless Explorations Ltd, EIN 00-5555555 (box 1 $49,999.99; box 2 $0.00)
- 2025 Form 1099-INT, Socialite Bank and Trust (box 1 $1.35)
- 2025 estimated tax payments: $10.49

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No; spouse: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: No; IRA contributions: No; K-12 educator: Yes; estimated payments: Yes.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/ty2024/mfj-50k-ctc-odc.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 6279f68f5c82fcda…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /achPaymentDate 2025-04-15 → 2026-04-15; /familyAndHousehold/#3524705d-35f2-44dd-bb0a-ea4481b06502/dateOfBirth 1991-04-05 → 1992-04-05; /familyAndHousehold/#9d45c664-8966-42e0-a179-4883b593f939/dateOfBirth 2022-06-07 → 2023-06-07; /familyAndHousehold/#ac82b88d-c13b-4c6f-a08b-c74d01f57a4a/dateOfBirth 1992-04-05 → 1993-04-05; /familyAndHousehold/#ac82b88d-c13b-4c6f-a08b-c74d01f57a4a/writableChildEmancipationDate 2010-04-05 → 2011-04-05; /filers/#c68cebda-d749-4620-9d04-89745de6ef3b/dateOfBirth 1940-03-04 → 1941-03-04; /filers/#f00acd09-a4cb-45e2-a19e-f313f436a1f2/dateOfBirth 1986-02-18 → 1987-02-18. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
