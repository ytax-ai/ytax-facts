# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Neutral intermediate representation for ingested tax documents.

This is the *only* output shape of the ingestion pipeline. It is deliberately
engine-agnostic: it carries document fields, confidences, and source regions —
never any downstream engine's node types or fact-paths. Mapping the neutral IR
into a specific target (e.g. Fact Graph writable facts) is a separate adapter's
job, kept strictly outside this package.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class FormType(str, Enum):
    W2 = "W-2"
    # Certain Gambling Winnings. A DISTINCT type, never a variant of the W-2 above it: `form w-2`
    # is a prefix of `Form W-2G`, and the first time a real one was tested it classified as a W-2
    # and had W-2 box extraction applied to boxes that are not W-2 boxes.
    W2G = "W-2G"
    F1099_INT = "1099-INT"
    F1099_DIV = "1099-DIV"
    F1099_B = "1099-B"
    F1099_R = "1099-R"
    # three information returns whose fact groups the service already covers, none of them
    # readable before this — 1099-MISC was refused by name (`classify._UNSUPPORTED`), and 1099-G /
    # 1099-SA had no signature at all, so a real page classified UNKNOWN.
    F1099_MISC = "1099-MISC"
    F1099_G = "1099-G"
    F1099_SA = "1099-SA"
    # Form 1099-OID, *Original Issue Discount*: covered since the pinned dictionary carries its
    # module; before that a real page classified UNKNOWN.
    F1099_OID = "1099-OID"
    F1098 = "1098"
    K1_1065 = "K-1 (1065)"
    # The S corporation's own Schedule K-1. Same shared title
    # ("Schedule K-1") as the 1065 and the 1041, but its own chrome names its form number
    # directly under it ("(Form 1120-S)") and its box numbering differs (interest is box 4, not
    # box 5; dividends 5a, not 6a; royalties 6, not 7) — and it has NO guaranteed-payments box at
    # all (that is a partnership-only concept, IRC section 707(c)). Splitting it out as its own
    # FormType, rather than reading it through K1_1065's label map, is what keeps a shareholder's
    # figures from being read against partnership box numbers or offered a box the form never
    # prints (`classify._UNSUPPORTED` used to refuse this form by name; see that module for why
    # it moved).
    K1_1120S = "K-1 (1120-S)"
    # The estate/trust Schedule K-1, the third and last of the three
    # forms `classify._UNSUPPORTED` used to refuse under the shared "Schedule K-1" title. Its
    # numbering is not a shift of either sibling's — box 1 is *interest* income (not ordinary
    # business income), box 6 is ordinary business income, and the form prints no royalties box
    # at all (an estate or trust's royalties live inside box 5, "Other portfolio and nonbusiness
    # income" — a box this client cannot single out a royalties figure from, so it is not read
    # as one). Its own chrome names its form number directly under the shared title, the same
    # disambiguation the 1120-S entry uses.
    K1_1041 = "K-1 (1041)"
    UNKNOWN = "UNKNOWN"


@dataclass
class SourceRegion:
    """Where on the source document a value came from (1-based page)."""
    page: int
    x0: float
    y0: float
    x1: float
    y1: float

    def as_bbox(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)


@dataclass
class ExtractedField:
    """A single labeled value pulled from a document.

    `value` is the raw string as read. `confidence` is an extraction-evidence
    score in [0, 1] (label matched + value parsed cleanly), NOT a model's
    self-rated certainty. Numeric normalization to integer cents is left to the
    downstream adapter; `value_cents` is populated only when a money string
    parses unambiguously, as a convenience.
    """
    label: str
    value: str
    confidence: float
    source: Optional[SourceRegion] = None
    value_cents: Optional[int] = None


class FieldOutcome(str, Enum):
    """What happened when the extractor looked for one declared field.

    The distinction this exists for: a box that is BLANK on the form and a box the extractor could
    not locate are opposite facts, and collapsing them to "absent" made the downstream adapter
    unable to tell "the taxpayer had no federal withholding" from "we failed to read box 2". Only
    the second needs a human, and only the second may not be treated as zero.
    """

    FOUND = "found"              # a value was read
    EMPTY = "empty"              # the label IS on the form and nothing follows it -> the box is blank
    NOT_LOCATED = "not_located"  # the label never appeared -> we do not know what the form says


@dataclass
class FieldReport:
    """One declared field and what became of it. Reported for EVERY declared field, found or not —
    which is what makes "we looked and there was nothing there" expressible at all."""
    label: str
    outcome: FieldOutcome


@dataclass
class ExtractedDocument:
    """The complete neutral IR for one source document."""
    form_type: FormType
    source_path: str
    fields: list[ExtractedField] = field(default_factory=list)
    # One entry per DECLARED field of this form type, whatever became of it. `fields` stays
    # found-only on purpose: `pipeline.py`'s tier logic counts it, and quietly changing what that
    # count means would make the ingestion summary wrong.
    outcomes: list[FieldReport] = field(default_factory=list)
    raw_text: str = ""
    warnings: list[str] = field(default_factory=list)

    def field_by_label(self, label: str) -> Optional[ExtractedField]:
        for f in self.fields:
            if f.label == label:
                return f
        return None

    def to_json(self, indent: int = 2) -> str:
        """Serialise for `out/sources/`. **`raw_text` is deliberately excluded.**

        `pipeline`'s privacy note promises that only redacted PDFs, the manifest and the IR reach
        the output directory — and the IR was quietly the leak: `raw_text` is the whole page text,
        captured from the PASS-1 file, where the K-1's partnership EIN is deliberately still present
        for extraction. Measured before this changed: `out/sources/k1_sample.json` contained
        `A Partnership's EIN 00-1112223` in plaintext while the redacted PDF beside it did not.
        Anything the redactor MISSES lands here verbatim too, which is the worse case.

        It stays on the in-memory object — assisted extraction may want it within a run — and never
        reaches the directory you would hand to someone. Found by an adversarial review, 2026-08-12.
        """
        d = asdict(self)
        d.pop("raw_text", None)
        d["form_type"] = self.form_type.value
        for report in d.get("outcomes", []):
            report["outcome"] = (report["outcome"].value
                                 if hasattr(report["outcome"], "value") else report["outcome"])
        return json.dumps(d, indent=indent)

    @classmethod
    def from_json(cls, text: str) -> "ExtractedDocument":
        """Read an IR back from `out/sources/`. The other half of resume.

        WHY RELOAD RATHER THAN RE-EXTRACT. A second sitting must not redo redaction — it is
        expensive and destructive by design — but the artifact left behind is not always enough to
        re-derive the IR from. On a K-1, pass 2 deliberately burns the partnership EIN *after*
        extraction has read it, so the final redacted PDF no longer contains what the first run
        legitimately extracted. **The IR JSON is the durable record of that sitting**, and reloading
        it is the only way a resumed run reports what the first one found.

        `raw_text` does not come back, and must not: `to_json` excludes it because it is whole-page
        text from the pass-1 file, carrying anything redaction missed. Absent on disk, absent here.
        """
        d = json.loads(text)
        return cls(
            form_type=FormType(d["form_type"]),
            source_path=d.get("source_path", ""),
            fields=[
                ExtractedField(
                    label=f["label"], value=f["value"], confidence=f["confidence"],
                    source=SourceRegion(**f["source"]) if f.get("source") else None,
                    value_cents=f.get("value_cents"),
                )
                for f in d.get("fields", [])
            ],
            outcomes=[FieldReport(label=o["label"], outcome=FieldOutcome(o["outcome"]))
                      for o in d.get("outcomes", [])],
            warnings=list(d.get("warnings", [])),
        )


_MONEY_RE = re.compile(r"^\s*\$?\s*(-?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|-?\d+(?:\.\d{1,2})?)\s*$")
# ACCOUNTING PARENTHESES: `(12,000.00)` is minus twelve thousand. Not a style question — it is what
# the printed Schedule K-1 uses for a negative, in its own chrome: item L reads `Withdrawals and
# distributions . . . $( )`, pre-printed, because that line is always a decrease. Nine of Part III's
# boxes are titled *(loss)*, box 1 among them, so a partnership loss is an ordinary reading of that
# form and not an edge case. Before this it came back as an unparsed string — `value_cents=None`,
# confidence 0.7 — which is a figure the taxpayer supplied arriving at the IR unread.

# ⚠ AND A BARE PARENTHESIZED INTEGER IS A FOOTNOTE MARKER, NOT A NEGATIVE. `(1)` occurs 428 times
# across the 157 real IRS PDFs in `sources/` — enumerations, note references, `(Form 1065)`, `(2)`
# in a list of conditions. Accepting those turned a token this function had always REFUSED (None,
# confidence 0.7) into a confident WRONG NEGATIVE (`(2025)` -> -$2,025.00 at 0.9), which is the one
# direction that is worse than not reading at all. A printed loss always carries a decimal point, a
# thousands comma or a currency mark inside the parentheses, so that is the requirement. Found by
# adversarial review, 2026-08-14.
_PARENS_RE = re.compile(r"^\s*\((.*)\)\s*$", re.DOTALL)
_MONEY_MARK = (".", ",", "$")


def parse_money_cents(s: str) -> Optional[int]:
    """Parse a money string to integer cents, or None if not clean.

    Conservative: returns None on anything ambiguous so the caller can treat the
    field as unparsed (unknown) rather than guess. Accounting parentheses negate,
    but only around something written as an AMOUNT — a bare `(1)` is a footnote
    marker. An amount signed BOTH ways (`(-5)`) is ambiguous and stays refused.
    """
    if s is None:
        return None
    parens = _PARENS_RE.match(s)
    if parens:
        inner = parens.group(1)
        if "-" in inner or not any(mark in inner for mark in _MONEY_MARK):
            return None      # a second sign, or a bare integer: not ours to guess at
        cents = parse_money_cents(inner)
        return None if cents is None else -cents
    m = _MONEY_RE.match(s)
    if not m:
        return None
    num = m.group(1).replace(",", "")
    neg = num.startswith("-")
    num = num.lstrip("-")
    if "." in num:
        whole, frac = num.split(".")
        frac = (frac + "00")[:2]
    else:
        whole, frac = num, "00"
    try:
        cents = int(whole) * 100 + int(frac)
    except ValueError:
        return None
    return -cents if neg else cents
