# Client interview — Rory Gilmore — Direct File scenario ny-rejected-0126

**Profile:** `profile-df-ny-rejected-0126` · **Tax year:** 2025 · **Filing status:** single

**SYNTHETIC — IRS DIRECT FILE TEST SCENARIO** — a fictional household the IRS wrote for its Direct File test suite (`scenarios/upstream/generic/ny-rejected-0126.json`, vendored per UPSTREAM.md), adapted to TY2025 by the declared rules in the notes; identities are the IRS's own test identifiers as printed, not a real taxpayer record. The facts are the scenario as adapted; this document is generated from them by `python -m syndoc.generate`; regenerate rather than edit.

## Household and background

Rory Gilmore (born 2003-02-03) of 2556 Stars Hollow ct, Flagstaff, AZ 85001 file(s) single — IRS Direct File test scenario `ny-rejected-0126` (a TY2024 fact graph the IRS wrote for its own test suite), adapted to TY2025 by the declared date rule in the notes.

Income documents on record: 1 Form(s) W-2 totalling $7,000.00 of box 1 wages.

## Documents provided

- 2025 Form W-2, NY Doooses Market, EIN 00-1245767 (box 1 $7,000.00; box 2 $250.00; AZ box 16 $7,000.00 / box 17 $50.00)

## Interview

**Q.** Any digital-asset activity this year (received, sold or exchanged)?

**A.** Received: No; disposed: No.

**Q.** Any foreign financial accounts or foreign trusts?

**A.** Accounts: No; trusts: No.

**Q.** Can anyone claim you (or your spouse) as a dependent?

**A.** Primary: Yes.

**Q.** Student loan interest, IRA contributions, educator expenses, estimated payments?

**A.** Student loan interest: No; IRA contributions: No; K-12 educator: Yes; estimated payments: No.

## Preparer notes

- SOURCE: IRS Direct File backend test scenario `scenarios/upstream/generic/ny-rejected-0126.json` (vendored from IRS-Public/direct-file@e365f9f43446, UPSTREAM.md), sha256 c51fd32f5cf9fd23…; identities as printed (IRS test TINs, group 00 / 9XX area; `00-` EINs).
- TY2025 ADAPTATION (declared rule, tested): every Day fact +1 year — /filers/#a9e7d72a-7d4e-4c0e-ae66-48b9d9348496/dateOfBirth 2002-02-03 → 2003-02-03. A structurally issuable TIN is replaced by a 900-range stand-in — /formW2s/#aa98a3ba-b409-4544-b886-dfffd65b8354/tin → 976-06-3219. Every other dollar amount and answer is byte-identical to the source.
- DROPPED: none — every source path is a TY2025 writable.
- NOT AN ANSWER KEY: the scenario is an input set. The TY2024 expected outputs in scenarios/upstream-expected-candidates/ (where one exists) are outputs of the TY2024 dictionary and are never compared against this profile's lines.
- IDENTITY: the W-2's employee TIN differs from the filer's 400-00-0009 (a W-2/filer mismatch fixture). The IRS prints a structurally issuable number there; adaptation rule 4 replaces it with the 900-range stand-in named above, still different from the filer's.
- FACSIMILE FIDELITY: each box mirrors the fact it is drawn from; a payer address the scenario does not carry (1099-INT, 1099-G) is the generic placeholder. The interview Q&A restates the scenario's own yes/no answers; nothing here was authored by ytax.

---

*The writable facts in `input/facts.json` follow from the answers above; the return in `output/` and the workbook are derived from those facts by the engine — interview → return → workbook.*
