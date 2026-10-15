# Client interview — Matilda Dogg — Direct File scenario hoh-9300

**Profile:** `profile-df-hoh-9300` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hoh-9300.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Matilda Dogg (born 1997-09-17) of 333 Golden Pawsway, Boston, MA 02301 file(s) head of household — IRS Direct File test scenario `hoh-9300` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Jeremy Dogg (born 2020-05-01, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $9,300.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, Squeaky Dog Toys Inc, EIN 00-8888888 (box 1 $9,300.00; box 2 $1,200.00; MA box 16 $9,300.00 / box 17 $800.00)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hoh-9300.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 149478e9026a387e…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#d3fd5858-8bd0-4946-9561-e23d88197f66/dateOfBirth 2019-05-01 → 2020-05-01; /filers/#923f1be3-c637-4062-9bbc-2297bab56004/dateOfBirth 1996-09-17 → 1997-09-17. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
