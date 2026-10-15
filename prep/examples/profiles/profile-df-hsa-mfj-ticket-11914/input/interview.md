# Client interview — Sean John — Direct File scenario hsa-mfj-ticket-11914

**Profile:** `profile-df-hsa-mfj-ticket-11914` · **Tax year:** 2025 · **Filing status:** marriedFilingJointly

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hsa-mfj-ticket-11914.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Sean John (born 1967-08-02) and Joan Jackson (born 1966-03-19) of 26 Dancing Daisy Drive, Charleston, FL 32401 file(s) married filing jointly — IRS Direct File test scenario `hsa-mfj-ticket-11914` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 2 Form(s) W-2 totalling $38,730.00 of box 1 wages. Also on record, without a rendered facsimile: hsaDistributions.

## Documents provided

- 2025 Form W-2, Speedway LLC, EIN 00-1111111 (box 1 $29,513.00; box 2 $1,254.00; FL box 16 $29,513.00 / box 17 $945.00)
- 2025 Form W-2, Kroger, EIN 00-0000013 (box 1 $9,217.00; box 2 $185.00; FL box 16 $9,217.00 / box 17 $123.00) — spouse's
- 2 item(s) in /hsaDistributions — carried as facts, no facsimile

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hsa-mfj-ticket-11914.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 026cfbc8deea7a10…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /filers/#678b2ad4-d28f-4036-b845-d87b644f0ccb/dateOfBirth 1966-08-02 → 1967-08-02; /filers/#89087401-24ff-4831-b3b4-ca32191bdfa5/dateOfBirth 1965-03-19 → 1966-03-19; /importedPrimaryFilerDateOfBirth 1966-08-02 → 1967-08-02. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
