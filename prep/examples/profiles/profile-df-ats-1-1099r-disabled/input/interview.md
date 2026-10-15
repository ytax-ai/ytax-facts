# Client interview — Susan Miranda — Direct File scenario ats-1-1099r-disabled

**Profile:** `profile-df-ats-1-1099r-disabled` · **Tax year:** 2025 · **Filing status:** single

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/ats-1-1099r-disabled.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Susan Miranda (born 1985-01-26) of 2030 Pecan Street, Monroe, MA 02301 file(s) single — IRS Direct File test scenario `ats-1-1099r-disabled` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 2 Form(s) W-2 totalling $39,674.00 of box 1 wages; 2 Form(s) 1099-R ($4,200.00 gross).

## Documents provided

- 2025 Form W-2, Our Flower Shop, EIN 00-0000004 (box 1 $15,205.00; box 2 $1,405.00; MA box 16 $15,205.00 / box 17 $507.00)
- 2025 Form W-2, Magnolia Floral Design, EIN 00-0000007 (box 1 $24,469.00; box 2 $5,869.00; MA box 16 $24,469.00 / box 17 $1,502.00)
- 2025 Form 1099-R, Payer Name (box 1 $200.00; box 2a $1,000.00; box 4 $300.00; code 7)
- 2025 Form 1099-R, Payer 2 Name (box 1 $4,000.00; box 2a $3,000.00; box 4 $0.00; code 7)

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

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/ats-1-1099r-disabled.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 62e24f88103f1594…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /filers/#363812c5-2b5d-46fd-a1f7-49f07bcf59d7/dateOfBirth 1984-01-26 → 1985-01-26. Every dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
