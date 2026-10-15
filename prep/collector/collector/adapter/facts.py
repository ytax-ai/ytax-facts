# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""FG writable facts — the ONLY output shape of the document->fact adapter.

A :class:`Fact` is a (dictionary writable fact-path, typed value) pair. Serialization
matches the Fact Graph's own *persister wrapper* format — the identical JSON shape used by
``scenarios/upstream/*.json`` (``gov.irs.factgraph.persisters.*Wrapper``) — so the engine
integration can feed a :class:`FactSet` straight into the engine runner with no translation.

Collector invariants, enforced here:
  * **Writable-only.** Every emitted path must be a *writable* fact-path in
    ``dictionary/ty2025/``; :meth:`FactSet.validate` checks this via ``tools.factpaths``.
    No foreign-engine node types or tags ever cross this boundary.
  * **Integer cents end-to-end.** Money is carried as ``int`` cents; :func:`cents_to_decimal`
    is the single place cents become the engine's ``"dollars.cents"`` decimal string.
  * **Unknown-not-zero.** An absent input produces *no* fact (the constructors are only ever
    called for present, parsed values); the adapter never manufactures a zero.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from collector.tools import factpaths

_PERSISTER = "gov.irs.factgraph.persisters.{}Wrapper"


def cents_to_decimal(cents: int) -> str:
    """Render integer cents as the engine's signed ``"dollars.cents"`` decimal string.

    The DollarWrapper persists a fixed two-decimal string (e.g. ``4825000 -> "48250.00"``,
    ``-550 -> "-5.50"``). This is the sole cents->string conversion in the adapter.
    """
    neg = cents < 0
    magnitude = abs(cents)
    body = f"{magnitude // 100}.{magnitude % 100:02d}"
    return f"-{body}" if neg else body


def decimal_to_cents(value: str) -> int:
    """Inverse of :func:`cents_to_decimal`: a ``"dollars.cents"`` string back to integer cents.

    The single string->cents conversion (reads a Dollar writable's value back out of a
    :class:`FactSet`). Raises on a sub-cent value, keeping cents exact.
    """
    amount = Decimal(value) * 100
    if amount != amount.to_integral_value():
        raise ValueError(f"sub-cent dollar value: {value!r}")
    return int(amount)


@dataclass(frozen=True)
class Fact:
    """One writable fact: its dictionary path, a persister wrapper kind, and the item payload.

    ``kind`` is the short wrapper name (``"Dollar"``, ``"Day"``, ``"Enum"``, ``"String"``,
    ``"Boolean"``, ``"CollectionItem"``, ``"Collection"``); ``item`` is the already-shaped
    JSON payload for that wrapper. Use the module-level constructors rather than building
    these directly — they own the per-type payload shape.
    """

    path: str
    kind: str
    item: object

    def to_persister(self) -> dict[str, object]:
        return {"$type": _PERSISTER.format(self.kind), "item": self.item}


# ---- typed constructors ------------------------------------------------------
def dollar(path: str, cents: int) -> Fact:
    return Fact(path, "Dollar", cents_to_decimal(cents))


def day(path: str, iso_date: str) -> Fact:
    return Fact(path, "Day", {"date": iso_date})


def enum(path: str, value: str, options_path: str) -> Fact:
    return Fact(path, "Enum", {"enumOptionsPath": options_path, "value": [value]})


def string(path: str, value: str) -> Fact:
    return Fact(path, "String", value)


def boolean(path: str, value: bool) -> Fact:
    return Fact(path, "Boolean", value)


def integer(path: str, value: int) -> Fact:
    """A whole-number writable (the engine's IntWrapper), e.g. a calendar month 1-12."""
    return Fact(path, "Int", value)


def collection(path: str, ids: list[str]) -> Fact:
    return Fact(path, "Collection", {"items": list(ids)})


def collection_item(path: str, item_id: str) -> Fact:
    return Fact(path, "CollectionItem", {"id": item_id})


def tin(path: str, area: str, group: str, serial: str) -> Fact:
    """A taxpayer identification number (SSN/ITIN), persisted as area-group-serial parts."""
    return Fact(path, "Tin", {"area": area, "group": group, "serial": serial})


def ein(path: str, prefix: str, serial: str) -> Fact:
    """An employer identification number, persisted as prefix + serial parts."""
    return Fact(path, "Ein", {"prefix": prefix, "serial": serial})


def address(
    path: str,
    *,
    street: str,
    city: str,
    state: str,
    postal_code: str,
    country: str = "",
) -> Fact:
    """A US postal address (``stateOrProvence`` matches the engine's wrapper spelling)."""
    return Fact(
        path,
        "Address",
        {
            "streetAddress": street,
            "city": city,
            "stateOrProvence": state,
            "postalCode": postal_code,
            "country": country,
        },
    )


# ---- ordered, conflict-checked, self-validating fact store -------------------
class FactConflict(ValueError):
    """Two different values were emitted for the same fact-path."""


class FactSet:
    """An ordered set of writable facts, keyed by path.

    Adding the *same* value for an existing path is idempotent; adding a *different* value
    raises :class:`FactConflict` (a mapping bug, never silently overwritten). Collection
    membership is accumulated through :meth:`add_collection_member` so multiple documents of
    one form (e.g. two W-2s) extend a single ``/formW2s`` collection in insertion order.
    """

    def __init__(self) -> None:
        self._facts: dict[str, Fact] = {}
        self._members: dict[str, list[str]] = {}

    def add(self, fact: Fact) -> None:
        existing = self._facts.get(fact.path)
        if existing is not None and (existing.kind, existing.item) != (fact.kind, fact.item):
            raise FactConflict(
                f"conflicting values for {fact.path}: "
                f"{existing.item!r} != {fact.item!r}"
            )
        self._facts[fact.path] = fact

    def extend(self, facts: list[Fact]) -> None:
        for f in facts:
            self.add(f)

    def add_collection_member(self, collection_path: str, item_id: str) -> None:
        """Append ``item_id`` to ``collection_path``'s membership, refreshing its Collection fact."""
        members = self._members.setdefault(collection_path, [])
        if item_id not in members:
            members.append(item_id)
        # Replace (not add) — membership grows as documents are processed.
        self._facts[collection_path] = collection(collection_path, members)

    def paths(self) -> list[str]:
        return list(self._facts)

    def get(self, path: str) -> Fact | None:
        """The fact stored at ``path`` (exact match), or ``None``."""
        return self._facts.get(path)

    def __iter__(self):
        """Iterate the stored :class:`Fact` objects in insertion order."""
        return iter(self._facts.values())

    def overlay(self, changes: FactSet) -> FactSet:
        """A new FactSet = this one with ``changes`` facts *replacing* any same-path facts.

        Unlike :meth:`add`, an overlaid path is overwritten without a :class:`FactConflict` — this
        is how a partial FactSet is applied on top of a baseline to produce the state the engine
        re-resolves. The originals are untouched (returns a copy).
        """
        out = FactSet()
        out._facts = dict(self._facts)
        out._members = {k: list(v) for k, v in self._members.items()}
        for fact in changes._facts.values():
            out._facts[fact.path] = fact
        return out

    def validate(self, dict_dir: Path = factpaths.DEFAULT_DICT_DIR) -> list[str]:
        """Return any emitted paths that are NOT writable in the dictionary (empty == valid)."""
        return factpaths.unknown_paths(self.paths(), dict_dir)

    def to_persister_dict(self) -> dict[str, dict[str, object]]:
        """The scenario-persister JSON shape: ``{path: {"$type": ..., "item": ...}}``."""
        return {path: fact.to_persister() for path, fact in self._facts.items()}
