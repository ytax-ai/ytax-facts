# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Interview-entered writable facts.

Some facts the engine needs are on *no document* — the additional deduction for a filer 65 or
older turns on **age**, which a W-2/1099 never states. The Collector
therefore needs a path for manually-entered writable facts: filing status, filer dates of
birth, and dependents. These are emitted as the same FG writable facts the document adapter
produces, so interview and document facts merge into one :class:`~collector.adapter.facts.FactSet`.

Filer identity is owned here: :class:`Interview` allocates the primary (and optional secondary)
filer ids, and the document adapter links each income document's ``filer`` to one of them
(default: primary). Ids are injectable so tests can assert against fixed values.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from . import facts
from .facts import Fact

# Values of /filingStatusOptions (dictionary/ty2025/filingStatus.xml).
FILING_STATUS_OPTIONS_PATH = "/filingStatusOptions"
FILING_STATUSES = frozenset({
    "single",
    "marriedFilingJointly",
    "marriedFilingSeparately",
    "headOfHousehold",
    "qualifiedSurvivingSpouse",
})


def _check_iso_date(label: str, value: str) -> str:
    """Reject anything that is not a real ``YYYY-MM-DD`` date (fail loud, not silently)."""
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be ISO YYYY-MM-DD, got {value!r}") from exc
    return value


@dataclass(frozen=True)
class Dependent:
    """A household dependent. Date of birth is required (it drives age-based tests)."""

    date_of_birth: str
    first_name: str | None = None


@dataclass
class Interview:
    """Manually-entered writable facts for one return.

    Only provided fields are emitted (unknown-not-zero applies to interview input too): a
    ``None`` date of birth or filing status produces no fact. A secondary filer is created
    only when ``secondary_date_of_birth`` is given.
    """

    filing_status: str | None = None
    primary_date_of_birth: str | None = None
    secondary_date_of_birth: str | None = None
    # DirectFile's data model always carries *two* filer slots; non-MFJ returns keep the
    # second as an empty, non-primary placeholder. The engine's per-filer collection filters
    # (e.g. /secondaryFilerW2s, which gates dependent-care-benefit completeness) stay
    # Incomplete without it, so a single-filer return cannot fully resolve unless the slot
    # exists. Opt-in (default off) so existing single-filer mappings are unchanged; the
    # engine integration turns it on. A real secondary (secondary_date_of_birth) supersedes it.
    secondary_filer_placeholder: bool = False
    dependents: list[Dependent] = field(default_factory=list)
    # Collection-member ids are UUIDs (the engine's representation); injectable for tests.
    primary_filer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    secondary_filer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dependent_id_factory: Callable[[int], str] = field(
        default=lambda _i: str(uuid.uuid4())
    )

    def has_secondary(self) -> bool:
        return self.secondary_date_of_birth is not None

    def _has_secondary_slot(self) -> bool:
        """Whether a second filer entry exists at all (real spouse or empty placeholder)."""
        return self.has_secondary() or self.secondary_filer_placeholder

    def build_facts(self) -> list[Fact]:
        out: list[Fact] = []

        # Filers collection + per-filer flags/DOB.
        filer_ids = [self.primary_filer_id]
        if self._has_secondary_slot():
            filer_ids.append(self.secondary_filer_id)
        out.append(facts.collection("/filers", filer_ids))

        out.append(facts.boolean(f"/filers/#{self.primary_filer_id}/isPrimaryFiler", True))
        if self.primary_date_of_birth is not None:
            out.append(facts.day(
                f"/filers/#{self.primary_filer_id}/dateOfBirth",
                _check_iso_date("primary_date_of_birth", self.primary_date_of_birth),
            ))
        if self._has_secondary_slot():
            out.append(facts.boolean(f"/filers/#{self.secondary_filer_id}/isPrimaryFiler", False))
        if self.has_secondary():
            assert self.secondary_date_of_birth is not None  # narrows for mypy
            out.append(facts.day(
                f"/filers/#{self.secondary_filer_id}/dateOfBirth",
                _check_iso_date("secondary_date_of_birth", self.secondary_date_of_birth),
            ))

        # Filing status.
        if self.filing_status is not None:
            if self.filing_status not in FILING_STATUSES:
                raise ValueError(
                    f"unknown filing status {self.filing_status!r}; "
                    f"expected one of {sorted(FILING_STATUSES)}"
                )
            out.append(facts.enum("/filingStatus", self.filing_status, FILING_STATUS_OPTIONS_PATH))

        # Dependents -> /familyAndHousehold.
        dep_ids = [self.dependent_id_factory(i) for i in range(len(self.dependents))]
        if self.dependents:
            out.append(facts.collection("/familyAndHousehold", dep_ids))
        for dep, dep_id in zip(self.dependents, dep_ids):
            out.append(facts.day(
                f"/familyAndHousehold/#{dep_id}/dateOfBirth",
                _check_iso_date("dependent.date_of_birth", dep.date_of_birth),
            ))
            if dep.first_name:
                out.append(facts.string(
                    f"/familyAndHousehold/#{dep_id}/firstName", dep.first_name,
                ))

        return out
