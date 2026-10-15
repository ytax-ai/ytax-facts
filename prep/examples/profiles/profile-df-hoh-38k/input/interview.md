# Client interview — Chilindrina Ramon — Direct File scenario hoh-38k

**Profile:** `profile-df-hoh-38k` · **Tax year:** 2025 · **Filing status:** headOfHousehold

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/hoh-38k.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Chilindrina Ramon (born 1981-01-01) of 123 Vecindad, Cheyenne, WY 83002 file(s) head of household — IRS Direct File test scenario `hoh-38k` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes. Household members on the return: Kiko Mesa (born 2012-02-02, childOrDescendants).

Income documents on record: 1 Form(s) W-2 totalling $37,898.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, Chespirito Corp., EIN 00-6797983 (box 1 $37,898.00; box 2 $587.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: No.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: Yes; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/hoh-38k.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 f15915eef0a9feba…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /familyAndHousehold/#a84c6a78-ac5c-45cd-bee5-031c1e1ae536/dateOfBirth 2011-02-02 → 2012-02-02; /filers/#a8f921cd-a4db-4782-9627-4a3d6d946046/dateOfBirth 1980-01-01 → 1981-01-01. A W-2 box 4 above 6.2% of boxes 3 + 7, or box 6 above the Medicare rates on box 5, is impossible on a real W-2 and is set to the rate figure — /formW2s/#27974e7a-0e83-45d7-8da4-c583f6266b9f/writableOasdiWithholding 54.00 → 11.16. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
