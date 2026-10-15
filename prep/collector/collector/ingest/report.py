# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Three-tier run summary. Assists review; it does NOT certify. Redacted PDFs
should still be eyeballed before they leave the machine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Tier(str, Enum):
    OK = "fully processed"
    WARN = "processed with warnings"
    FAIL = "could not process"


@dataclass
class FileResult:
    filename: str
    form_type: str
    tier: Tier
    rects_redacted: int = 0
    fields_extracted: int = 0
    notes: list[str] = field(default_factory=list)


def tier_for(result_notes: list[str], fields_extracted: int, processed: bool) -> Tier:
    if not processed:
        return Tier.FAIL
    if result_notes or fields_extracted == 0:
        return Tier.WARN
    return Tier.OK


def render_report(results: list[FileResult]) -> str:
    by_tier: dict[Tier, list[FileResult]] = {t: [] for t in Tier}
    for r in results:
        by_tier[r.tier].append(r)

    lines: list[str] = []
    lines.append("=" * 64)
    lines.append("INGESTION SUMMARY (assists review; does not certify)")
    lines.append("=" * 64)
    lines.append(
        f"total: {len(results)}  |  "
        f"ok: {len(by_tier[Tier.OK])}  "
        f"warn: {len(by_tier[Tier.WARN])}  "
        f"fail: {len(by_tier[Tier.FAIL])}"
    )
    for tier in (Tier.OK, Tier.WARN, Tier.FAIL):
        group = by_tier[tier]
        lines.append("")
        lines.append(f"[{tier.value.upper()}] ({len(group)})")
        for r in group:
            lines.append(
                f"  - {r.filename}  ->  {r.form_type}  "
                f"(redacted {r.rects_redacted}, fields {r.fields_extracted})"
            )
            for n in r.notes:
                lines.append(f"      ! {n}")

    # Highest-priority follow-up: nothing found at all.
    nothing = [r for r in results if r.rects_redacted == 0 and r.fields_extracted == 0]
    if nothing:
        lines.append("")
        lines.append("PRIORITY — nothing detected (likely total OCR/parse failure):")
        for r in nothing:
            lines.append(f"  * {r.filename}")
    lines.append("")
    return "\n".join(lines)
