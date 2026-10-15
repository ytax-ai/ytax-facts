# Client interview — Taxi Taxington — Direct File scenario hoh-43k-plus-interest

**Profile:** `profile-df-hoh-43k-plus-interest` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/ty2024/hoh-43k-plus-interest.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Taxi Taxington (born 2005-02-28) of 2 N Main St, Andover, MA 02301 file(s) head of household — IRS Direct File test scenario `hoh-43k-plus-interest` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Taxibaby Taxington McFile (born 2024-04-20, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $42,386.00 of box 1 wages; 1 Form(s) 1099-INT ($1,200.00).

## Documents provided

- 2025 Form W-2, Andover Public, EIN 00-5346547 (box 1 $42,386.00; box 2 $4,000.00; MA box 16 $42,386.00 / box 17 $400.00)
- 2025 Form 1099-INT, Vanguard (box 1 $1,200.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/ty2024/hoh-43k-plus-interest.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 f6781c829bd17746…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#7436eb94-12bd-469a-9791-514c8a54e540/dateOfBirth 2023-04-20 → 2024-04-20; /filers/#1abbf795-4e41-4ced-889f-e39fabdf7941/dateOfBirth 2001-11-23 → 2002-11-23; /filers/#a5642561-23fe-476b-8e03-50a55ea9ef0b/dateOfBirth 2004-02-29 → 2005-02-28; /secondaryFilerDateOfDeath 2023-07-04 → 2024-07-04. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
