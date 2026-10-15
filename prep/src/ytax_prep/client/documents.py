# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Turn the Collector's extraction IR into a fact set — the missing link in the full flow.

Documents are read by the **Collector** (`collector/`, READ-ONLY from here): a PDF
goes in, a neutral IR comes out — labelled boxes, integer cents, page coordinates, a confidence, and
the document's `raw_text`. Nothing anywhere turned that IR into the fact set this service accepts.
This is that step, and it belongs on the client side of the boundary, where the documents are.

WHAT THE COLLECTOR ACTUALLY DOES TODAY, checked rather than assumed: **W-2 extraction is real**
(six boxes, confidence 0.9), and **1099-INT, 1099-DIV, 1099-R, K-1, 1099-MISC, 1099-G and 1099-SA
read real boxes too** — off the same kind of box map `collector/ingest/extract.py`
uses for the W-2; a given document can still come back with none of them read, but that is the
page, not a standing zero. Rule 1 now matters most for a form the Collector classifies but
declares no box map for at all (1099-B, 1098).

FOUR RULES, each a defect this repo has already paid for once (there were three when this was
written, and rule 4 arrived later — the heading was never updated):

1. **A form the Collector RECOGNISED but could not extract is a REFUSAL, not a skip.** The caller
   handed us a 1099-INT; continuing without it computes a return as though they had no interest
   income. That is #55 (elections dropped) and work item 0b (`wages_cents` defaulted) in a new
   costume, and it is the single most valuable thing this module does.

2. **`raw_text` and `source_path` are never read.** `raw_text` is the whole document as text —
   names, TINs, addresses — and a filename is routinely a person's name; neither may leave this computer.
   `project_case` would refuse them as unclassified, but relying on the downstream control means
   building a structure that only accidentally never leaves.

3. **A box with nowhere to go is DECLARED, not dropped.** Same shape as the mapper's
   assumed/plumbing split: named, with why, and anything not on the list refuses.

4. **An UNREAD box is not a zero** (decided 2026-08-11: `withholding_cents` stays schema-optional,
   and the component handling the W-2 must reflect what is really on the PDF). The extractor walks
   six known boxes and appends only the ones it finds, so a box that was **blank on the form** and a
   box whose label it **failed to locate** are both simply absent — and they mean opposite things. A
   blank box 2 is a fact (this taxpayer had no federal withholding) and must cross as an explicit
   `0`; an unread box 2 is ignorance, and omitting it makes the service compute zero payments, the
   $5,400 error the gap spike found. So an unread box is neither dropped nor defaulted: it is
   **asked about**, and answering it is a statement about the paper.

   **Root cause FIXED at source (2026-08-11).** The IR now reports an outcome for every DECLARED
   field: `found`, `empty` (the label is on the form with nothing after it — the box is blank) or
   `not_located` (the label never appeared). Only `not_located` needs a human. An `empty` box
   crosses as an explicit `0` with no question asked, because the document already answered it.

   An IR with no `outcomes` — an older extraction — is treated as `not_located` throughout. That is
   the fail-closed reading: an old document cannot tell us which case it was, so it asks.

   **Which boxes may not be left unanswered is the FORM's business, not the W-2's**.
   `REQUIRED_LABELS` declares it per form type, and both readers go through one `_fields_of`: the
   rule that refuses a W-2 with no wages was living inside `w2s_from` alone, so the dispatching
   function every form now flows through had neither it nor the explicit `0` above.

   **On a REQUIRED box, `empty` is a question, not an answer.** The explicit `0` above is right for
   a box the return survives without, and wrong for the box the return is built on — because the
   extractor reports `empty` for an attribution failure too, and `wages_cents: 0` passes
   every downstream check a real figure passes. Read `REQUIRED_LABELS` for the evidence.

   **This layer transcribes; it does not correct.** A confirmation for a box already answered —
   extracted, or blank where blank is an answer — refuses. Applying it would let a typed figure
   overwrite the paper silently; dropping it would lose what the caller said just as silently.

No tax knowledge lives here beyond the box→field correspondence, which is transcription, not
judgement. What a figure MEANS is the engine's business.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .filer import FilerProposal, propose_filer
from .form_labels import label_for

# Collector label -> the fact-schema field it becomes. Transcription only.
W2_LABEL_TO_FIELD = {
    "box1_wages": "wages_cents",
    "box2_fed_withholding": "withholding_cents",
    "box3_ss_wages": "social_security_wages_cents",
    "box4_ss_withholding": "social_security_withheld_cents",
    "box5_medicare_wages": "medicare_wages_cents",
    # box 6 IS a payment line once Additional Medicare Tax applies — Form 8959 line 24
    # carries the excess over the regular rate on box 5 into Form 1040 lines 25d and 33. The
    # old claim here (that box 6 "is not reported on Form 1040 and is not a payment line") was
    # false the moment a filer crossed that threshold, and this client had no field to carry it.
    "box6_medicare_withholding": "medicare_withheld_cents",
}

# Extracted, and the fact schema has no field for it. Declared with the reason it is harmless —
# NOT silently dropped, because "we ignored a number you gave us" needs to be a decision somebody
# wrote down. Anything not here and not in the map above refuses. Empty today (box 6, the only
# entry, was retired); the mechanism stays for the next box the extractor reads that this schema
# has nowhere to put.
UNMAPPED_BUT_HARMLESS = {}

# Form 1099-INT. Only the boxes `schema/common/facts/int1099.schema.json` can hold — a box with
# nowhere to go would be a figure the taxpayer supplied and the return silently dropped.
INT1099_LABEL_TO_FIELD = {
    "box1_interest": "interest_cents",
    "box4_fed_withholding": "federal_withholding_cents",
    "box8_tax_exempt_interest": "tax_exempt_interest_cents",
    # boxes 2 and 9-13.
    "box2_early_withdrawal_penalty": "early_withdrawal_penalty_cents",
    "box9_private_activity_bond_interest": "private_activity_bond_interest_cents",
    "box10_market_discount": "market_discount_cents",
    "box11_bond_premium": "bond_premium_cents",
    "box12_treasury_bond_premium": "treasury_bond_premium_cents",
    "box13_tax_exempt_bond_premium": "tax_exempt_bond_premium_cents",
}

# Form 1099-DIV. Only the boxes `schema/common/facts/div1099.schema.json` can hold.
DIV1099_LABEL_TO_FIELD = {
    "box1a_ordinary_dividends": "ordinary_dividends_cents",
    "box1b_qualified_dividends": "qualified_dividends_cents",
    "box2a_capital_gain_distributions": "capital_gain_distributions_cents",
    "box4_fed_withholding": "federal_withholding_cents",
}

# Form W-2G, *Certain Gambling Winnings*. Only the boxes `schema/common/facts/w2g.schema.json` can
# hold — the form has eighteen and this schema holds two, so the other sixteen (2 date won, 3 type
# of wager, 5-18) have no fact field at all.

# ⚠ THE BOX NUMBER IS PART OF THE LABEL, and the extractor's own comment says why: FOUR boxes on
# this form say *winnings* — 1 Reportable winnings, 7 Winnings from identical wagers, 14 State
# winnings, 16 Local winnings — and so does the form's title. Nothing here re-derives the labels;
# they are the extractor's canonical names, and `test_the_client_knows_exactly_the_boxes_the_
# extractor_looks_for` locks the two tables together so a third box added there cannot be silently
# ignored here.
W2G_LABEL_TO_FIELD = {
    "box1_reportable_winnings": "winnings_cents",
    "box4_fed_withholding": "federal_withholding_cents",
}

# Schedule K-1 (Form 1065), *Partner's Share of Income, Deductions, Credits, etc.* Only the boxes
# `schema/common/facts/k1.schema.json` can hold — Part III carries some thirty more (2, 3, 4c,
# 6b, 6c, 8, 9a-9c, 10-19, 21-23) and none of them has a fact field.

# ⚠ BOX 20 IS THE ONE FACT FIELD THAT IS NOT READ, and the reason is the box's shape
# rather than an omission. Box 20 prints ONE caption — "20 Other information" — over a list of
# code-and-amount pairs, and the code Z figure the schema holds is not on the page at all: it is
# on the section 199A statement attached to the K-1. A label-then-next-value read of "20 Other
# information" would return whichever pair happened to be printed first, and a wrong code's
# amount routed to Form 8995 line 6 is a wrong return. So `qualified_ptp_income_cents` is ASKED
# (interview.GROUP_PROMPTS), the schema description says so, and nothing here guesses. The
# `section_199a_qbi_cents` is the same statement on a K-1 that is not a PTP's (box 17 code V on
# the Form 1120-S), asked for the same reason.

# ⚠ THE BOX NUMBER IS PART OF THE LABEL, and on this form for two reasons at once. Part III stacks
# its boxes in one narrow column, so a bare `ordinary dividends` is box 6a AND box 6b — and the
# schema has ONE dividend field, of which 6a is the total, exactly the way the 1099-DIV's section
# 897 boxes impersonated its box 1a. A bare `interest income` is also the 1099-INT's box 1, the
# collision that made every real K-1 classify as a 1099-INT. As everywhere else here, the
# labels are the extractor's canonical names and nothing is re-derived: `test_the_client_knows_
# exactly_the_boxes_the_extractor_looks_for` locks the two tables together.

# ⚠ THESE AMOUNTS CAN BE NEGATIVE, which no earlier form here could produce. Box 1 is *Ordinary
# business income (LOSS)*; the form prints a loss in accounting parentheses and the
# extractor reads `(12,000.00)` as -1,200,000 cents. Nothing on this path may flatten that sign —
# `_fields_of` takes `value_cents` as-is, a confirmation is checked for INT and not for positivity,
# and `payload.INTEGER_FIELDS` asks the same question. A loss read as a gain is a wrong return.
K1_1065_LABEL_TO_FIELD = {
    "box1_ordinary_business_income": "ordinary_business_income_cents",
    "box4a_guaranteed_payments_services": "guaranteed_payments_services_cents",
    "box4b_guaranteed_payments_capital": "guaranteed_payments_capital_cents",
    "box5_interest_income": "interest_income_cents",
    "box6a_ordinary_dividends": "dividend_income_cents",
    "box7_royalties": "royalties_cents",
}

# Schedule K-1 (Form 1120-S), *Shareholder's Share of Income, Deductions, Credits, etc.*.
# Three of the four `k1.schema.json` money fields the 1065 reads, at this
# form's OWN box numbers — Part III shifts everything after box 1 by one relative to the 1065,
# because this form has no 4a-4c guaranteed-payments boxes to make room for. THERE IS NO
# guaranteed_payments_* ENTRY HERE AT ALL: that box does not exist on this form (guaranteed
# payments are a partnership-only concept, IRC section 707(c)), and this map's job is to say what
# a box IS, not to propose a figure for one the form never prints.

# ⚠ ROYALTIES PRINTS ON THIS FORM (box 6) AND IS STILL NOT READ HERE — the one case in this table
# where the box exists on the PAPER and the omission is not about the form. `mapper.py`'s own
# `_K1_FIELDS_NOT_ON["s_corp"]` refuses `royalties_cents` on every s_corp item BY NAME: "royalties
# are carried at the pin for the Form 1065 K-1's box 7 only" — the pinned engine's writable
# fact-graph has no route for an S corporation shareholder's royalties at all. That is a dictionary
# gap, not a reading one (an engine defect is evidence for the engine's own repository, never an
# edit made here) — proposing a candidate the service refuses on arrival would be exactly the
# defect this unit exists to close, in a new place. `se_earnings_cents`, `general_partner` and
# `publicly_traded_partnership` are the same `_K1_FIELDS_NOT_ON` refusal for other s_corp fields,
# but none of them are printed boxes this map would otherwise read anyway (14A / item D / G are
# 1065-only rows the interview asks about, never boxes this reader extracts).
K1_1120S_LABEL_TO_FIELD = {
    "box1_ordinary_business_income": "ordinary_business_income_cents",
    "box4_interest_income": "interest_income_cents",
    "box5a_ordinary_dividends": "dividend_income_cents",
}

# Schedule K-1 (Form 1041), *Beneficiary's Share of Income, Deductions, Credits, etc.*.
# Only the boxes `k1.schema.json` can hold for an `estate_trust` item — which,
# unlike the 1065/1120-S maps above, is not "every box the form prints" but a strict SUBSET of it:
# `mapper.py`'s own `_K1_FIELDS_NOT_ON["estate_trust"]` refuses `royalties_cents` and every
# partnership/s_corp-only field (basis, at-risk, guaranteed payments, item D/G, box 20) on an
# estate_trust item by name, so the four boxes below are the whole intersection of "this form
# prints it" and "this item can carry it."

# ⚠ THE NUMBERING IS A GENUINE REMAPPING, NOT A SHIFT — the one K-1 form where that is true. Box 1
# on the 1065/1120-S is *Ordinary business income (loss)*; on THIS form box 1 is *Interest income*,
# and ordinary business income is box 6. Box 2a is *Ordinary dividends* (the 1065's 6a / the
# 1120-S's 5a) and 2b is *Qualified dividends* right beside it — a neighbour, not a second field,
# same as the other two forms.

# ⚠ THERE IS NO ROYALTIES BOX ON THIS FORM AT ALL — the one case among the three K-1s where the
# absence is about the PAPER, not the pin. An estate or trust's royalties are folded into box 5,
# "Other portfolio and nonbusiness income," which this schema has no field to receive (reading it
# as `royalties_cents` would report a figure that might not be royalties at all). Nothing here
# reads box 5, so nothing here proposes a royalties candidate — consistent with, not contradicted
# by, `mapper.py` refusing `royalties_cents` on this item type for a different reason (the pinned
# engine carries no route for one at all).
K1_1041_LABEL_TO_FIELD = {
    "box1_interest_income": "interest_income_cents",
    "box2a_ordinary_dividends": "dividend_income_cents",
    "box2b_qualified_dividends": "qualified_dividends_cents",
    "box6_ordinary_business_income": "ordinary_business_income_cents",
}

# What each form type contributes, and under which fact group. A document whose type is NOT here is
# refused rather than skipped — that invariant is the whole safety net, and widening the set of
# forms must not weaken it.
# Form 1099-R. The boxes `schema/common/facts/r1099.schema.json` holds and a statement
# prints on its face. Two of them are not money — the first such boxes this map has carried: box 7
# is a one- or two-character CODE, and 2b and IRA/SEP/SIMPLE are MARKS. `LABEL_KINDS` says which,
# and `_fields_of` reads each kind as itself: a code is text checked against the schema's own
# pattern, a mark is a boolean, and neither is ever integer cents.
R1099_LABEL_TO_FIELD = {
    "box1_gross_distribution": "gross_distribution_cents",
    "box2a_taxable_amount": "taxable_amount_cents",
    "box2b_taxable_amount_not_determined": "taxable_amount_not_determined",
    "box4_fed_withholding": "federal_withholding_cents",
    "box7_distribution_code": "distribution_code",
    "box7b_ira_sep_simple": "ira_sep_simple",
}

# Form 1099-MISC (box 2 added later). The boxes `schema/common/facts/misc1099.schema.json`
# can hold: box 2, royalties (summed by the mapper into the one return-level royalty activity —
# no per-item engine writable), and box 3, other income. `is_alaska_pfd` is required-when-reached
# by the schema but is on no box — the engine's own per-form question, asked rather than read
# (`interview.GROUP_PROMPTS`, same treatment as the K-1's box 20) only once box 3 carries an
# amount; a royalty-only form (box 3 blank) answers it automatically, never asked.
MISC1099_LABEL_TO_FIELD = {
    "box2_royalties": "royalties_cents",
    "box3_other_income": "other_income_cents",
    "box4_fed_withholding": "federal_withholding_cents",
}

# Form 1099-OID. Every box `schema/common/facts/oid1099.schema.json` can hold. The box 2
# tax-exempt answer is on no box — it is asked (`gaps_for`), never read from a page.
OID1099_LABEL_TO_FIELD = {
    "box1_original_issue_discount": "original_issue_discount_cents",
    "box2_other_periodic_interest": "other_periodic_interest_cents",
    "box3_early_withdrawal_penalty": "early_withdrawal_penalty_cents",
    "box4_fed_withholding": "federal_withholding_cents",
    "box5_market_discount": "market_discount_cents",
    "box6_acquisition_premium": "acquisition_premium_cents",
    "box8_oid_on_treasury_obligations": "treasury_oid_cents",
    "box10_bond_premium": "bond_premium_cents",
    "box11_tax_exempt_oid": "tax_exempt_oid_cents",
    "fatca_filing_requirement": "fatca_filing_requirement",
}

# Form 1099-B. The boxes build's printed-box list can find on a page (not
# every box): 1f, 1g, 4 and the box 7 mark. Boxes 1d and 1e are required and asked, box 2 is
# asked where a date is missing (the dates, a Day, are not read yet), and box 3's two marks are
# asked on every form.
B1099_LABEL_TO_FIELD = {
    "box1f_accrued_market_discount": "accrued_market_discount_cents",
    "box1g_wash_sale_loss_disallowed": "wash_sale_loss_disallowed_cents",
    "box4_fed_withholding": "federal_withholding_cents",
    "box7_loss_not_allowed": "loss_not_allowed",
}

# Form 1099-G. Only the boxes `schema/common/facts/g1099.schema.json` can hold: box 1 and
# box 4. `repaid_cents` is on no box (the Schedule 1 line 7 repayment entry space) and box 2
# (state/local refunds) is not covered at all.
G1099_LABEL_TO_FIELD = {
    "box1_unemployment_compensation": "unemployment_compensation_cents",
    "box4_fed_withholding": "federal_withholding_cents",
}

# Form 1099-SA. Only the boxes `schema/common/facts/hsa_distribution.schema.json` can hold:
# box 1 and box 3 (a CODE — see `LABEL_KINDS`). `qualified_medical_expenses_cents` is required by
# the schema but is on no box: "the recipient's own records (Form 8889 line 15), never a 1099-SA
# box" — the synthetic page's own payer statement.
SA1099_LABEL_TO_FIELD = {
    "box1_gross_distribution": "gross_distribution_cents",
    "box3_distribution_code": "hsa_distribution_code",
}

MONEY, CODE, CHECK = "money", "code", "check"
LABEL_KINDS = {                      # every label not named here is money
    "box7_distribution_code": CODE,
    "box2b_taxable_amount_not_determined": CHECK,
    "box7b_ira_sep_simple": CHECK,
    # 1099-SA box 3, the same treatment as the 1099-R's box 7. This dict is checked
    # byte-for-byte against the Collector's own `extract.FIELD_KINDS`
    # (`test_1099r_layouts.TheKindsAgreeWithTheClientTest`), so `CODE_RE` below stays the shared,
    # looser pattern; the schema's tighter ENUM (1-6, not the r1099 pattern's open one-or-two
    # alnum) is checked separately, in `HSA_CODE_ENUM` below.
    "box3_distribution_code": CODE,
    "fatca_filing_requirement": CHECK,        # Form 1099-OID
    "box7_loss_not_allowed": CHECK,           # Form 1099-B
}
# `r1099.schema.json`'s own pattern for `distribution_code`, locked to it by test.
CODE_RE = re.compile(r"^[0-9A-Z]{1,2}$")
# `hsa_distribution.schema.json`'s own enum for `hsa_distribution_code` — unlike the 1099-R's
# open pattern, this box's codes are a closed set, so a misread of `7` or `G` (both CODE_RE-shaped)
# is caught here rather than waiting for a schema refusal downstream with no box named in it.
# Per-label, because `CODE_RE` above must stay the one pattern shared with the Collector.
CODE_ENUMS = {
    "box3_distribution_code": frozenset({"1", "2", "3", "4", "5", "6"}),
}

# A box the document reports BLANK is normally a stated 0 (`_box_state` → BLANK → 0). Two kinds of
# box may not be answered that way. A MARK reported blank is unchecked, which the schema spells as
# absent. And box 2a is money whose blank is NOT zero: the schema says so in its own words — "absence
# is NOT zero: without it the return KNOCKS OUT ... because determining a taxable amount the payer
# did not state is advice this service refuses to give". A 0 there would compute a tax-free pension
# nobody stated. Both are OMITTED, and the engine says what it says.
BLANK_OMITS = frozenset({"box2a_taxable_amount"})

FACT_GROUPS = {
    "W-2": ("w2s", W2_LABEL_TO_FIELD),
    "1099-INT": ("int1099s", INT1099_LABEL_TO_FIELD),
    "1099-OID": ("oid1099s", OID1099_LABEL_TO_FIELD),
    "1099-B": ("b1099s", B1099_LABEL_TO_FIELD),
    "1099-DIV": ("div1099s", DIV1099_LABEL_TO_FIELD),
    "1099-R": ("r1099s", R1099_LABEL_TO_FIELD),
    "W-2G": ("w2gs", W2G_LABEL_TO_FIELD),
    "K-1 (1065)": ("k1s", K1_1065_LABEL_TO_FIELD),
    "K-1 (1120-S)": ("k1s", K1_1120S_LABEL_TO_FIELD),
    "K-1 (1041)": ("k1s", K1_1041_LABEL_TO_FIELD),
    "1099-MISC": ("misc1099s", MISC1099_LABEL_TO_FIELD),
    "1099-G": ("g1099s", G1099_LABEL_TO_FIELD),
    "1099-SA": ("hsa_distributions", SA1099_LABEL_TO_FIELD),
}

# Non-money fields a FORM TYPE fixes, rather than reads off the page. Still transcription: the value
# comes from which form the Collector classified, not from any judgement about the taxpayer.

# `k1.schema.json` is the only fact schema whose items require anything beyond `person`: it requires
# `source`, an enum of partnership / s_corp / estate_trust, because the one `k1s` group carries
# three different Schedules K-1. Form **1065** IS the partnership return, so the form type already
# says which. Leaving it out would produce an item the schema rejects — and reject it MISLEADINGLY,
# because `mapper._refuse_missing_or_mistyped` runs BEFORE the coverage refusal, so the partner
# would be told a field was missing instead of being told the honest thing (`k1s` is not covered).

# ⚠ WHAT THIS CONSTANT RESTS ON, said exactly, because the first version of this comment overstated
# it. "The form type says 1065" is a fact about the CLASSIFIER, not about the words "Schedule K-1":
# that title is shared by the 1065, the 1041 and the 1120-S, and until review measured it, all three
# real pages classified as `K1_1065`. An 1120-S prints box 1 as `1 Ordinary business income (loss)`,
# character for character, so a shareholder's figure extracted and was stamped `partnership` here —
# found by review of this very unit, on the real page. The guarantee this constant needs therefore
# lives in `collector/collector/ingest/classify.py`, which gives each K-1 its OWN classifier
# outcome: the 1120-S has its own `K1_1120S` signature (and so its own row below, `s_corp`), and
# the 1041 was later given the same treatment (`K1_1041`, `estate_trust`) once its
# genuine box remapping was measured and built — neither ever reaches THIS row. If any of the
# three classifies as `K1_1065` (a needle broadened, a signature merged), THIS LINE BECOMES A LIE —
# `test_classification_real_forms` and `test_the_source_constant_rests_on_a_classifier_guard` hold
# it in place from the other side.

# `source` used to be asked as an open interview question, per k1s[]
# INDEX, whenever a document's own reader (`intake/readers/documents.py`) left it unset — which it
# always did, since that newer tiered reader never applied this table at all. Answering an
# index-keyed question from a profile's own array order is exactly how a reader item ends up
# carrying one document's money boxes and a DIFFERENT document's entity type: nothing ties the two
# together except position, and nothing requires the reader's read order to match any array order a
# profile (real or synthetic) happens to use. `source` is not a judgement call — it is the one fact
# a K-1 document declares about its own identity by nature of which FORM it is — so the intake
# reader now applies this table too (`read_document`), tying it to the SAME index its own money-box
# candidates use, from the SAME document, every time.
FORM_CONSTANTS = {
    "K-1 (1065)": {"source": "partnership"},
    "K-1 (1120-S)": {"source": "s_corp"},
    "K-1 (1041)": {"source": "estate_trust"},
}

# A constant may not occupy a field some box also writes: the two would race, and whichever ran last
# would win silently. Declared-or-refused at import, in the style of every other table here — this
# is a wiring mistake, so it should stop the process rather than wait for a document to reveal it.

# ⚠ IT IS THE MAP'S VALUES THAT MATTER, not its keys. `_fields_of` writes `out[mapping[label]]`, so
# the fields an item actually holds are the TARGET fields — `ordinary_business_income_cents` — while
# the keys are extractor labels (`box1_ordinary_business_income`), which are never item fields at
# all. The first version of this guard intersected the keys and would therefore have waved through
# the one collision it exists to catch. Both axes are checked now: a constant colliding with a LABEL
# is harmless today but means somebody has confused the two vocabularies, which is worth stopping on.
# `person` is in the protected set too: `_new_item` writes it from filer resolution BEFORE the
# constants are applied via `update`, so a constant named `person` would silently override the
# filer match — the field the filer-resolution guards exist to protect (the verify pass demonstrated exactly that).
def _constant_clash(constants, mapping):
    """One function for the guard AND its test, so the two cannot drift apart."""
    return set(constants) & (set(mapping.values()) | set(mapping) | {"person"})


for _form, _constants in FORM_CONSTANTS.items():
    _mapping = FACT_GROUPS.get(_form, (None, {}))[1]
    _clash = _constant_clash(_constants, _mapping)
    if _clash:
        raise RuntimeError(
            f"FORM_CONSTANTS[{_form!r}] sets {sorted(_clash)}, which its label map also writes. A "
            f"constant and an extracted box cannot share a fact field — one would silently "
            f"overwrite the other.")
del _form, _constants, _mapping, _clash

# Below this, the Collector is guessing. A guessed figure that reaches a return is precisely what
# this service must never serve; the threshold is arguable, using an unreviewed guess is not.
MINIMUM_CONFIDENCE = 0.75

# The boxes a form cannot be WITHOUT, declared PER FORM TYPE. This was `REQUIRED_W2_LABELS`,
# checked only inside `w2s_from` — a W-2-only rule that was never generalised, so the dispatching
# path every form now flows through had no required box at all and a W-2 with no wages in it passed.

# REQUIRED MEANS ANSWERED BY THE EXTRACTOR OR BY A HUMAN — and `empty` is NEITHER. That is the one
# thing this rule may not concede, because `empty` is not a proven-blank signal: the extractor's
# `_value_after_label` sets `label_seen` BEFORE it tries to attribute a value, so every attribution
# failure (no column for the label, the row-below loop breaking, the tail filter) reaches EMPTY. The
# extractor's own docstring records it happening — where boxes 2/4/6 were last on their line,
# reported EMPTY, and crossed as an explicit 0. For a box the return survives without, that trade is
# right. For the figure the return is BUILT on it is a $0 return nobody was asked about, and nothing
# downstream catches it: `wages_cents: 0` satisfies `mapper.REQUIRED_ITEM_FIELDS` exactly as a real
# figure does. So a blank REQUIRED box is a QUESTION (`unread_boxes` asks it, in its own words).

# Every form in FACT_GROUPS declares a set — empty or not — so adding a form is a decision somebody
# wrote down rather than a rule that quietly fails to apply to it.
REQUIRED_LABELS = {
    "W-2": frozenset({"box1_wages"}),      # the figure the return is built on
    # The information returns require nothing today, which is the conservative reading rather than a
    # claim that no box matters: their unread boxes are ASKED about (`unread_boxes`), and a form
    # that should refuse instead of asking now says so in one line, here.
    "1099-INT": frozenset(),
    "1099-DIV": frozenset(),
    # 1099-OID: nothing required — the form carries any subset of its boxes (a Treasury-only form
    # has a blank box 1), and the mapper sends every blank as a stated zero.
    "1099-OID": frozenset(),
    # 1099-B: nothing READ is required. Its two required boxes, 1d and 1e, are not read at
    # all (build's list cannot find them) — the interview asks them.
    "1099-B": frozenset(),
    # W-2G: box 1 is REQUIRED, which is the W-2's posture rather than the information returns'.
    # THE PAPER SAYS SO. A W-2G is issued *because* a reportable win crossed a threshold — the form
    # exists for box 1, and `w2g.schema.json` holds exactly one winnings figure, so a blank box 1 is
    # a W-2G reporting no winnings: not impossible, but unusual enough that the reading of
    # `empty` (the label was seen, the value could not be attributed) is the likelier one. That is
    # precisely the ask-blank case, and the human holding the paper settles it in one answer.
    # The service-side check now agrees, and it did not when this row was written. The note here used to read
    # "`w2gs` is in `UNSUPPORTED_STREAMS`, so this stream has no service-side check of any kind to
    # fall back on — every guard it gets, it gets here." The service then covered the stream and made
    # `winnings_cents` required in `w2g.schema.json` and in `mapper.REQUIRED_ITEM_FIELDS`, off the
    # same reading of the same paper. So the box is now guarded twice, and the two guards say
    # different things on purpose: HERE it is an ASK (the human is holding the form and can read the
    # box), and at the service it is a REFUSAL for a caller who supplied nothing. Neither is a zero.
    # Box 4 stays OPTIONAL for the same reason the W-2's box 2 does: withholding applies to some
    # wager types and amounts and not others, so blank is an ORDINARY state of that box, and its
    # stated 0 is a fact about the document rather than a suspicion.
    "W-2G": frozenset({"box1_reportable_winnings"}),
    # 1099-R: box 1 and box 7 — the mapper's own required pair (`REQUIRED_ITEM_FIELDS["r1099s"]`,
    # the form is issued because a distribution happened, and the code says what
    # kind). Box 2a is NOT required here — blank is an ordinary state of that box — but its blank
    # is not a 0 either; see `BLANK_OMITS`.
    "1099-R": frozenset({"box1_gross_distribution", "box7_distribution_code"}),
    # K-1 (1065): NOTHING is required, which is the information returns' posture and the OPPOSITE
    # call from the W-2G's one row above. The two were decided against the same test, and the paper
    # answers it differently.

    # THE W-2G IS ISSUED BECAUSE A BOX-1 THRESHOLD WAS CROSSED, so a blank box 1 contradicts the
    # form's own existence. A SCHEDULE K-1 IS ISSUED TO EVERY PARTNER: "The partnership uses
    # Schedule K-1 to report your share of the partnership's income, deductions, credits, etc."
    # (*Purpose of Schedule K-1*, Partner's Inst. for Sch. K-1 (Form 1065) (2025), p. 1). There is
    # no threshold and no box the form is "for" — a partner gets one whatever their shares happen to
    # be, and the instructions' own box-1 wording is conditional throughout: "If income is reported
    # in box 1… If a loss is reported in box 1…" (same instructions, Box 1, p. 14).

    # AND A LEGITIMATE K-1 CAN LEAVE ALL FOUR OF OUR BOXES BLANK. Part III has ~30 boxes and this
    # client reads four. A rental-only partnership reports box 2 (*Net rental real estate income
    # (loss)*, which has no fact field here); a partnership with only guaranteed payments reports
    # 4a-4c. Requiring box 1 would refuse those ordinary documents outright — the exact damage the
    # unreadable-box refusal is about, arriving from the required-box side instead of the unreadable side.

    # What this does NOT concede: an unread box is still ASKED about (`unread_boxes`), and a box the
    # document reports blank still crosses as an explicit, STATED 0. The `empty`-is-an-attribution-
    # failure suspicion is real here too — it is simply not strong enough to refuse an
    # ordinary K-1 over, where on the W-2G it was.
    "K-1 (1065)": frozenset(),

    # K-1 (1120-S): the same reading as the 1065 immediately above,
    # for the same reason — a Schedule K-1 is furnished to EVERY shareholder to report that
    # shareholder's share, whatever it happens to be, and this client reads four of its ~19 boxes.
    # An S corporation with no ordinary business activity (all passive/portfolio income, reported
    # elsewhere in Part III) leaves box 1 blank on a perfectly ordinary K-1.
    "K-1 (1120-S)": frozenset(),

    # K-1 (1041): the same reading again, for the same reason — every
    # beneficiary of an estate or trust is furnished a Schedule K-1 for their share, whatever it
    # happens to be, and this client reads four of Part III's fourteen boxes. A beneficiary whose
    # share is entirely, say, rental or capital-gain income (Part III's other boxes, none of them
    # covered here) leaves all four blank on a perfectly ordinary K-1.
    "K-1 (1041)": frozenset(),

    # The alignment test only requires a SUBSET of the mapper's own required set
    # (`REQUIRED_ITEM_FIELDS`), so each of the three below is a fresh reading of the same
    # question the 1099-R/W-2G/K-1 rows above already answer for other forms: is a BLANK printed
    # box unusual enough on THIS form that a human should be asked, or an ordinary state that
    # crosses as a stated 0?

    # 1099-MISC: NOTHING required — the K-1/1099-DIV posture, not the 1099-R one. A 1099-MISC is
    # issued for many reasons (rents, royalties, medical payments, ...) and this schema covers only
    # box 3 of them. MEASURED ON THE SYNTHETIC CORPUS: all three 1099-MISC pages available
    # (`profile-royalty`, `profile-royalty-oil-gas`, `profile-multi-stream`) are ROYALTY forms —
    # box 2 carries the money and box 3 prints BLANK on every one, which is the ordinary state of a
    # box this form does not exist "for." Requiring it would ask a question on every routine
    # royalty 1099-MISC for no reason the paper gives. A blank box 3 crosses as a stated 0, which
    # is correct here (there IS no other income on that page) and still satisfies the mapper's
    # `other_income_cents` presence requirement — required-at-the-schema-level and
    # required-to-ask-a-human are different questions, and this form answers them differently.
    "1099-MISC": frozenset(),
    # 1099-G: box 1 required — `g1099.schema.json`'s own words for `unemployment_compensation_cents`
    # are the 1099-R posture verbatim ("the form is issued because compensation was paid, so a
    # blank box is an unread box, not compensation of nothing"), and `REQUIRED_ITEM_FIELDS["g1099s"]`
    # requires it too. Box 4 stays optional, the W-2's box 2 posture: withholding is voluntary on
    # this form (Form W-4V) and blank is ordinary.
    "1099-G": frozenset({"box1_unemployment_compensation"}),
    # 1099-SA: box 1 and box 3 required — the 1099-R posture again, and the mapper's own words for
    # `hsa_distribution_code` (all four fields "required" on `hsa_distributions`) plus box 1 being
    # the form's whole reason to exist. Measured on the one synthetic page in this corpus
    # (`profile-hsa-distribution`): both boxes are filled, so this required pair asks nothing on
    # it today, but the reading holds for a page where one comes back genuinely blank.
    "1099-SA": frozenset({"box1_gross_distribution", "box3_distribution_code"}),
}


def _path(group: str, index: int, fact: str) -> str:
    """The one spelling of a fact path — `w2s[1].wages_cents` — that questions are asked under,
    confirmations are keyed by, and refusals name. One function, so the three cannot drift."""
    return f"{group}[{index}].{fact}"


def _plan(documents: list, consumable, skip_unknown: bool = False) -> list:
    """`(doc, form_type, group, mapping, index-within-group)` for each document, in order.

    The single source of the group/index arithmetic every fact path is built from, so
    `unread_box_questions`, `facts_from`, `w2s_from` and the leftover-confirmation check agree
    on what `w2s[1].wages_cents` means — the second W-2 in the batch, whatever sits between them.

    `consumable` is the set of form types the caller can read; anything else refuses as rule 1,
    unless `skip_unknown` (the question list, which has nothing to ask about a form `facts_from`
    will refuse anyway).
    """
    plan = []
    counts: dict = {}
    for doc in documents:
        form_type = doc.get("form_type")
        if form_type not in consumable:
            if skip_unknown:
                continue
            raise _unconsumable(form_type, doc)
        group, mapping = FACT_GROUPS[form_type]
        index = counts.get(group, 0)
        counts[group] = index + 1
        plan.append((doc, form_type, group, mapping, index))
    return plan


def _outcomes(doc: dict) -> dict:
    """label -> outcome, from the IR. An extraction with none is treated as `not_located`
    throughout: an older document cannot say which case it was, so it asks rather than assumes."""
    return {report["label"]: report["outcome"] for report in doc.get("outcomes") or []}


# How ONE box stands, once the extraction has been read. Four states, and the split that matters is
# between the two that are ANSWERED (nobody to ask; a confirmation for them is a correction, which
# this layer does not do) and the two that are OPEN.
EXTRACTED = "extracted"          # the Collector read a figure out of the box
BLANK = "blank"                  # reported `empty`, and this box may be answered that way: a fact
ASK_BLANK = "ask-blank"          # reported `empty` on a REQUIRED box — see REQUIRED_LABELS
ASK_UNREAD = "ask-unread"        # `not_located`, or an IR too old to say: fail closed and ask
ANSWERED = (EXTRACTED, BLANK)


def _box_state(label: str, found: set, outcomes: dict, required: frozenset) -> str:
    """The one place that decides what an absent box MEANS. `_fields_of` and the question list read
    a document through this, so what the caller is asked and what the reader refuses cannot drift.
    """
    if label in found:
        return EXTRACTED
    if outcomes.get(label) == "empty":
        return ASK_BLANK if label in required else BLANK
    return ASK_UNREAD


def _answer_clause(kind: str) -> str:
    """The last clause of a box question: what an answer looks like for this KIND of box."""
    if kind == CODE:
        return "enter the code(s) printed in the box"
    if kind == CHECK:
        return "true if the box is checked on the paper, false if it is not"
    return "send the figure, or 0 if the box is empty"


def _question(state: str, box: str, confirm: str, kind: str = MONEY) -> str:
    """What to ask about one open box — the wording, in one place, so the refusal and the prompt
    say the same thing. Two slots, because the sentence has two readers: `box` is
    how the box is NAMED — the form's own caption for a person (`2 Federal income tax withheld`),
    the Collector's key for an API caller — and `confirm` is the instruction clause, which names
    the fact path for the caller who must key a confirmation by it and names no path at all for
    the person who will type into a cell."""
    if state == ASK_BLANK:
        answer = ("send the amount, or 0 if the box really is blank on the paper" if kind == MONEY
                  else _answer_clause(kind))
        return (f"the document reports {box} BLANK, and a blank {box} is unusual on this form. "
                f"The extractor also reports a box blank when it found the label but could not "
                f"attribute a value to it, so on the one box this form is built on that is a "
                f"question rather than an answer. {confirm}: {answer}.")
    return (f"{box} was not read from the document, and this client cannot tell whether the box "
            f"is BLANK on the form or whether extraction simply missed it — the two mean opposite "
            f"things and only someone looking at the paper can say. {confirm}: "
            f"{_answer_clause(kind)}. Omitting it would compute the return as though the "
            f"box were empty without anyone having checked.")


# The person-facing instruction clause. It names no path: the person answers in a cell (the
# workbook) or at a prompt that shows the path beside it (`scripts/client.py`).
CONFIRM_FOR_A_PERSON = "Confirm this box"


def unread_box_questions(documents: list) -> dict:
    """`{fact_path: what to ask}` for every box a human must answer.

    Two kinds, and they are asked differently. A `not_located` box is silence — blank form or missed
    label, indistinguishable. A REQUIRED box the document reports blank is a claim this client will
    not take on trust (`REQUIRED_LABELS`), so it is asked in words that say what the document said.

    `box6_medicare_withholding` used to be excluded here unconditionally — it had no fact
    field, so its absence changed no number. It now has one (Form 8959's Additional Medicare Tax
    reaches lines 25d and 33) and follows the ordinary optional-box rule, the same as box 2's
    federal withholding: a reported-blank box crosses as a stated 0 with no question, and a
    NOT-LOCATED box is asked like any other, because an unread box is not a zero."""
    asking: dict = {}
    for doc, form_type, group, mapping, index in _plan(documents, FACT_GROUPS, skip_unknown=True):
        found = {f.get("label") for f in doc.get("fields") or []}
        outcomes = _outcomes(doc)
        required = REQUIRED_LABELS.get(form_type, frozenset())
        for label, fact in mapping.items():
            state = _box_state(label, found, outcomes, required)
            if state in ANSWERED:
                continue
            path = _path(group, index, fact)
            # Keyed by the PATH (the machine half); worded in the form's CAPTION (the human half).
            asking[path] = _question(state, label_for(group, fact), CONFIRM_FOR_A_PERSON,
                                     LABEL_KINDS.get(label, MONEY))
    return asking


def unread_boxes(documents: list) -> list:
    """Boxes only a human can resolve, as fact paths a caller can confirm. `unread_box_questions`
    says what to ask about each; this is the same list, sorted, for a caller that has its own
    prompt."""
    return sorted(unread_box_questions(documents))


class DocumentsRefused(ValueError):
    """Reading stopped. Raised instead of producing a fact set that quietly omits something."""


def _unconsumable(form_type, doc: dict) -> DocumentsRefused:
    """Rule 1, in one voice. Recognised and empty is the dangerous case: the caller supplied it."""
    return DocumentsRefused(
        f"a {form_type} was recognised but this client cannot extract it into facts "
        f"({len(doc.get('fields') or [])} field(s) available). Refusing rather than continuing "
        f"without it — you supplied the document, and a return computed as though you had not is a "
        f"wrong number, not a smaller one.")


def _refuse_unconsumed(confirmations: dict, plan: list) -> None:
    """A confirmation key that names no box on any document supplied is refused BY NAME.

    `facts_from([ir], {"w2s[1].wages_cents": 999999})` used to succeed with one W-2 and the second
    figure simply vanished: no document produced `w2s[1]`, and nothing looked for leftovers. A
    typo'd fact name did the same; so did a figure aimed at a box with no fact field. That is the
    silent-drop class already closed for answered boxes, one cell over — a human supplied a figure and
    nothing consumed or refused it.

    This runs BEFORE any box is read, so the human who mis-spelled `wages_cents` is told that their
    key matched nothing, rather than that the box they believe they answered is still open.
    """
    addressable = {_path(group, index, fact)
                   for _doc, _form, group, mapping, index in plan for fact in mapping.values()}
    leftover = sorted(set(confirmations) - addressable)
    if leftover:
        raise DocumentsRefused(
            f"{len(leftover)} confirmation key(s) match no box on any document supplied: "
            f"{', '.join(leftover)}. Refusing rather than dropping a figure a human typed — a "
            f"confirmation answers one box of one document, and the paths that can be answered "
            f"are exactly what `unread_boxes()` lists for this batch. Check the group, the "
            f"document's position in the batch, and the spelling of the fact.")


def read_extractions(sources_dir) -> list:
    """Read a Collector `out/sources/` directory. Order is sorted, so the same documents in the same
    folder always produce the same fact set (the determinism contract starts here, not at the API).
    """
    sources_dir = Path(sources_dir)
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(sources_dir.glob("*.json"))]
    if not docs:
        raise DocumentsRefused(
            f"no extraction files in {sources_dir}. Refusing rather than returning an empty fact "
            f"set — a return computed from no documents is not an empty return, it is a wrong one.")
    return docs


def _filer_for(doc: dict, index: int, persons: list | None, located: list | None) -> int:
    """Which filer this document belongs to, or a refusal saying why it cannot be told.

    A W-2 does not name its filer in any field we keep — the employee's name is what redaction
    removes — so with more than one filer this is answered by matching what redaction LOCATED. It
    refuses rather than defaulting, because the default is what made an ordinary joint return
    unfilable, and because the failure it hides (a spouse's wages on the primary's line) is not
    visible on a finished return.
    """
    if not persons or len(persons) <= 1:
        return 0
    found = (located or [])[index] if located and index < len(located) else {}
    outcome = propose_filer(found, persons)
    if isinstance(outcome, FilerProposal):
        return outcome.person
    raise DocumentsRefused(
        f"cannot tell which filer document {index + 1} belongs to ({outcome.reason}). There are "
        f"{len(persons)} filers, and putting one person's wages on another's line is a wrong "
        f"return that looks finished — say whose it is rather than letting it default.")


def _new_item(form_type: str, doc: dict, index: int, persons: list | None,
              located: list | None) -> dict:
    """The non-money half of ONE fact item: whose it is, and whatever its form type fixes.

    Both readers go through here for the same reason both go through `_fields_of`. `w2s_from`
    built its item inline, so `FORM_CONSTANTS` applied on the dispatching path and silently did not
    on the W-2 path. That costs nothing TODAY — the W-2 declares no constants — which is exactly the
    kind of dormant divergence that gets discovered later by a wrong return rather than by a test.
    """
    item = {"person": _filer_for(doc, index, persons, located)}
    item.update(FORM_CONSTANTS.get(form_type, {}))
    return item


def facts_from(documents: list, confirmations: dict | None = None,
               persons: list | None = None, located: list | None = None,
               *, unread_required: str = "refuse") -> dict:
    """Every supplied document, turned into the fact groups it belongs to.

    THE INVARIANT THIS KEEPS, while widening what can be read: **a document nobody can consume
    refuses the batch.** `w2s_from` enforced that by refusing anything that was not a W-2, which was
    right when a W-2 was the only thing readable and became the reason a taxpayer with a savings
    account could not file at all. Dispatching by form type must not turn that refusal into a silent
    skip — *you supplied the document, and a return computed as though you had not is a wrong
    number, not a smaller one.*

    Returns `{group: [items]}` for the groups that have anything in them, so a batch of one W-2
    yields exactly what it did before.

    `unread_required` decides what a REQUIRED box the extractor did not read does. The
    default `"refuse"` is unchanged: the batch refuses, because an API caller must confirm the box
    before a return is built on it. `"gap"` omits the box instead of refusing — the item exists
    without it, and the required-fact gap surfaces downstream as an open question. This is only for
    the workbook flow, where the person answers a required box by typing into a yellow cell rather
    than by re-submitting; the box is never dropped, only deferred to that cell. It must NEVER cross
    as a `0`, which is why the box is omitted (an absent fact is a gap) rather than defaulted (a
    present `0` is a $0-wage return nobody was asked about)."""
    if unread_required not in ("refuse", "gap"):
        raise ValueError(f"unread_required must be 'refuse' or 'gap', got {unread_required!r}")
    confirmations = confirmations or {}
    plan = _plan(documents, FACT_GROUPS)
    _refuse_unconsumed(confirmations, plan)
    groups: dict = {}
    for index, (doc, form_type, group, mapping, group_index) in enumerate(plan):
        if form_type not in REQUIRED_LABELS:
            raise DocumentsRefused(
                f"{form_type} is consumable (FACT_GROUPS) but declares nothing in REQUIRED_LABELS. "
                f"Refusing rather than reading it under no required-box rule at all — which box a "
                f"form cannot be without is a decision somebody has to write down, even when the "
                f"answer is none.")
        required = REQUIRED_LABELS[form_type]
        # `must_answer` is what may not be left OPEN. On the workbook flow an unread required box is
        # answered in a cell, so nothing is forced here (`frozenset()`); `required` still tells
        # `_box_state` a blank box is a question, so the box is omitted, never crossed as a 0.
        must_answer = frozenset() if unread_required == "gap" else required
        item = _new_item(form_type, doc, index, persons, located)
        item.update(_fields_of(doc, mapping, group, group_index, confirmations, required, must_answer))
        groups.setdefault(group, []).append(item)
    return groups


def _fields_of(doc: dict, mapping: dict, group: str, index: int, confirmations: dict,
               required: frozenset, must_answer: frozenset) -> dict:
    """The money fields of ONE document, under one form's label map — the single path both
    `facts_from` and `w2s_from` read a document through.

    Refuses on anything unreadable: an undeclared label, a guess, a non-integer. Then it accounts
    for every box the extractor looks for — rule 4 — because an absent box is either a blank box or
    a missed one and those mean opposite things.

    `required` is what `_box_state` uses to decide whether a box reported blank is a fact or a
    question. `must_answer` is the set of labels that may not be left OPEN: the form's required set
    on the dispatching path, and every mapped box for `w2s_from`, whose bar has always been the
    higher one. A box is ANSWERED by the extractor, by a blank the form is allowed to state, or by a
    human confirming it — and that third one is what makes this an ask rather than a wall.
    """
    out: dict = {}
    for field in doc.get("fields") or []:
        label = field.get("label")
        if label in UNMAPPED_BUT_HARMLESS:
            continue
        if label not in mapping:
            raise DocumentsRefused(
                f"the Collector extracted {label!r}, which this client has no fact field for "
                f"and has not declared harmless. Refusing rather than ignoring a figure you "
                f"supplied — declare it in the form's label map or UNMAPPED_BUT_HARMLESS.")
        confidence = field.get("confidence", 0)
        if confidence < MINIMUM_CONFIDENCE:
            raise DocumentsRefused(
                f"{label} was extracted with confidence {confidence}, below "
                f"{MINIMUM_CONFIDENCE}. Refusing rather than computing a return on a guess — "
                f"review the document and enter the figure directly.")
        kind = LABEL_KINDS.get(label, MONEY)
        if kind == CODE:
            # Read as text, never as cents: `7` is a distribution code, not 700. Checked
            # against the schema's own pattern here, so a misread reaches the person as a
            # sentence about the box it actually is (this used to say "box 7" for every
            # code-kind box, which was wrong the moment a second one — the 1099-SA's box 3 —
            # existed) rather than as a schema refusal downstream.
            box = label_for(group, mapping[label])
            text = str(field.get("value") or "").strip().upper()
            enum = CODE_ENUMS.get(label)
            if not CODE_RE.match(text) or (enum is not None and text not in enum):
                raise DocumentsRefused(
                    f"{label} was read as {field.get('value')!r}, which is not a distribution "
                    f"code (one or two characters, a digit or a capital letter each). Refusing "
                    f"rather than guessing — enter the code as printed in {box}.")
            out[mapping[label]] = text
            continue
        if kind == CHECK:
            out[mapping[label]] = True         # the extractor reports a mark, or nothing
            continue
        cents = field.get("value_cents")
        # Taken as-is, never re-parsed from the display string: the Collector already did that with
        # its own tests behind it, and a second implementation is free to disagree by a cent, which
        # is a wrong return.
        if not isinstance(cents, int) or isinstance(cents, bool):
            raise DocumentsRefused(
                f"{label} carries no integer `value_cents`. Money is integer cents everywhere "
                f"in this system; a display string is not a substitute.")
        out[mapping[label]] = cents

    found = {f.get("label") for f in doc.get("fields") or []}
    outcomes = _outcomes(doc)
    for label, fact in mapping.items():
        state = _box_state(label, found, outcomes, required)
        path = _path(group, index, fact)

        if state in ANSWERED:
            if path in confirmations:
                # A figure typed for a box the document already answered. Applying it silently
                # overwrites what is on the paper; dropping it silently loses what the caller
                # said. Neither is a decision this layer gets to make on its own.
                answered_by = ("the Collector extracted it" if state == EXTRACTED else
                               f"the document reports {label} blank, which is a stated 0")
                raise DocumentsRefused(
                    f"a confirmation was supplied for {path}, but {answered_by}. Refusing rather "
                    f"than choosing between the two figures: this layer transcribes a document, "
                    f"it does not correct one. Confirmations answer the boxes the extractor did "
                    f"NOT report — `unread_boxes()` lists exactly those. If the extracted figure "
                    f"is wrong, the document or the extraction is what needs fixing.")
            if state == BLANK:
                # The extractor found the label with nothing after it: the box is on the form and
                # blank. That is a FACT about the document, so it crosses as an explicit 0 — no
                # human, no default. Dropping it would turn a STATED zero into an ASSUMED one.
                # Except where blank is not 0 (`BLANK_OMITS`, a mark): the fact is OMITTED, which
                # is the schema's own spelling of unchecked and of "no taxable amount stated".
                if label not in BLANK_OMITS and LABEL_KINDS.get(label, MONEY) == MONEY:
                    out[fact] = 0
            continue

        kind = LABEL_KINDS.get(label, MONEY)
        if path in confirmations:
            value = confirmations[path]
            if kind == CODE:
                text = str(value).strip().upper() if isinstance(value, str) else ""
                enum = CODE_ENUMS.get(label)
                if not CODE_RE.match(text) or (enum is not None and text not in enum):
                    raise DocumentsRefused(
                        f"the confirmation for {path} must be the distribution code as printed "
                        f"(one or two characters, a digit or a capital letter each), got "
                        f"{value!r}.")
                out[fact] = text
                continue
            if kind == CHECK:
                if not isinstance(value, bool):
                    raise DocumentsRefused(
                        f"the confirmation for {path} must be true or false — whether the box "
                        f"is checked on the paper — got {type(value).__name__}.")
                out[fact] = value
                continue
            if not isinstance(value, int) or isinstance(value, bool):
                raise DocumentsRefused(
                    f"the confirmation for {path} must be integer cents, got "
                    f"{type(value).__name__}. Money is integer cents everywhere in this system.")
            out[fact] = value
            continue

        if label in must_answer:
            # The API caller's refusal: the Collector's key and the path the confirmation is keyed by.
            raise DocumentsRefused(_question(state, label, f"Confirm {path}", kind))
    return out


def w2s_from(documents: list, confirmations: dict | None = None,
             persons: list | None = None, located: list | None = None) -> list:
    """The `w2s` fact group, from every W-2 in the batch. Refuses on anything it cannot carry.

    `confirmations` answers the boxes the extractor did not report — `{fact_path: cents}` — where
    `0` means *I looked at the form and that box is empty*. Every path in `unread_boxes()` needs one,
    because the alternative is guessing which of two opposite things the silence meant.

    `persons` and `located` answer WHOSE W-2 each one is. `located[i]` is what redaction
    found on document `i`, in the document's own terms. With one filer there is nobody else it could
    belong to; with several, the name is matched and an unmatched or ambiguous document is REFUSED
    rather than defaulted.

    That default is what this fixes. Every W-2 used to be filer 0, so two spouses with one W-2 each
    looked like one filer holding two — which `refuse_multiple_employers` correctly refuses, making
    the most ordinary joint return unfilable. The mirror case is worse and refuses nothing: a
    spouse's wages landing on the primary's line, where a rendered return looks finished.

    Reads each document through the same `_fields_of` as `facts_from` — there is one copy of
    rule 4, not two that can drift apart, which is how the dispatching path came to be missing it.
    What stays this function's own is the bar: a W-2 must answer every box it MAPS (box 6 is looked
    for and deliberately excluded — no fact field, so no number changes), where the dispatching path
    refuses only the form's `REQUIRED_LABELS` and reports the rest through `unread_boxes` for the
    caller to ask about.
    """
    confirmations = confirmations or {}
    must_answer = frozenset(W2_LABEL_TO_FIELD)
    required = REQUIRED_LABELS["W-2"]
    plan = _plan(documents, {"W-2"})
    _refuse_unconsumed(confirmations, plan)
    w2s = []
    for index, (doc, form_type, group, mapping, group_index) in enumerate(plan):
        w2 = _new_item(form_type, doc, index, persons, located)
        w2.update(_fields_of(doc, mapping, group, group_index, confirmations, required, must_answer))
        w2s.append(w2)
    return w2s
