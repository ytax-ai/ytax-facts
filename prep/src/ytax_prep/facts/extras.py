# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""`engine_extras` — the answers a person typed for engine inputs no service field reaches. A side-channel BESIDE the fact set, never inside it: the service's schema, refusals
and assumptions are untouched, and nothing here is part of the REST or MCP contract.

The rules, each a refusal by name (`validate`):
  1. only a writable the allow-list offers (`fallback_topics`) — never "any writable the dictionary
     has": the measurement served a wrong return three times in thirteen under that rule;
  2. typed as the dictionary types it, within the bounds the allow-list states — the dictionary's
     own `<Limit>` does not run on the persister path, so a bound is enforced
     here or nowhere;
  3. never over the service: a path the mapper emitted for this fact set is refused, not merged;
  4. a topic's gate is the ONE service-owned fact an extra may ever set, and only to TRUE; a fact
     set that already claims it keeps its own answer (written for Schedule A, board decision 8);
  5. a topic is answered IN FULL or not at all. Measured at the pin on the four offered topics
     (`tmp/fb_blank_sweep.py`, 2026-09-19): with every input typed each profile lands exactly on
     its oracle, and with any ONE left blank the return is still `complete` — with the topic
     contributing nothing. Never a wrong figure, but a credit the person said applies, dropped
     without a word. A no and a 0 are answers; a blank is not.

  6. a topic whose form belongs to ONE of something — a Form 8829 is about one business, not a
     return — declares that collection, and its lines are typed against a row BY ITS NUMBER:
     `/scheduleCs/[0]/writableForm8829DirectExpenses`. The engine keys that row by a uuid the
     mapper makes and the caller never sees, so the number is resolved HERE, against the row the
     mapper actually emitted, and a number that names no row is refused.

Amounts are integer cents, like every amount in this service.
"""
from __future__ import annotations

import re

from . import fallback_topics as topics

# What these are, for the partition every engine input belongs to (`mapper.DERIVED_FROM_INPUT`,
# `ASSUMED_ABOUT_TAXPAYER`, `ENGINE_PLUMBING` are the mapper's three): an input TYPED BY THE PERSON
# for a form this version does not read. Its publication is the provenance row each one gets.
TYPED_BY_PERSON = frozenset(path for topic in topics.TOPICS.values() for path in topic["writables"])
from .mapper import ServiceFactsError, _bool, _dollar, _int_wrap, _str, _tin, map_to_engine


def _typed(path: str, entry: dict, value):
    kind = entry["kind"]
    if kind == topics.BOOLEAN:
        if not isinstance(value, bool):
            raise ServiceFactsError(f"{entry['line']} is a yes-or-no answer; got {value!r}")
        # A form's own choice where only ONE arm is a method this version computes: the other is
        # refused in that form's words, never computed by a method the figures are not for
        # (board decision 8 — "a yes-or-no with a refusal on the answer that breaks it").
        if "must_be" in entry and value is not entry["must_be"]:
            raise ServiceFactsError(entry["refusal"])
        return _bool(value)
    if isinstance(value, bool) or not isinstance(value, int):
        unit = "a whole number of cents" if kind == topics.DOLLAR else "a whole number"
        raise ServiceFactsError(f"{entry['line']} is {unit}; got {value!r}")
    low, high = entry.get("min", 0), entry.get("max")
    scale = 100 if kind == topics.DOLLAR else 1
    if value < low * scale or (high is not None and value > high * scale):
        bounds = f"at least {low}" + (f" and at most {high}" if high is not None else "")
        raise ServiceFactsError(f"{entry['line']} must be {bounds}; got {value / scale:g}")
    return _dollar(value) if kind == topics.DOLLAR else _int_wrap(value)


# `/scheduleCs/[0]/writableX` — a row of a collection, by its number in the fact set (rule 6).
_MEMBER = re.compile(r"^(/[A-Za-z0-9]+)/\[(\d+)\]/([A-Za-z0-9]+)$")


def _offered_form(path: str) -> str:
    """The allow-list's own spelling of a path a caller typed: a member's row number becomes the
    `*` the dictionary and the list both use."""
    member = _MEMBER.match(path)
    return f"{member.group(1)}/*/{member.group(3)}" if member else path


def validate(extras: dict, engine_facts: dict) -> dict:
    """The engine facts these extras add — refused by name, as a whole, when any one of them breaks
    a rule above. `engine_facts` is what the mapper emitted for this fact set."""
    offered, out, ticked = topics.offered_writables(), {}, set()
    for path in sorted(extras):
        listed = _offered_form(path)
        if listed not in offered:
            raise ServiceFactsError(
                f"{path} is not an input this version offers to take as a typed answer; refused "
                f"rather than sent to the engine unread")
        if path in engine_facts:
            raise ServiceFactsError(
                f"{path} is already answered by this return's own facts, and that answer stands; "
                f"refused rather than overwritten")
        key, entry = offered[listed]
        out[path] = _typed(path, entry, extras[path])
        ticked.add(key)
    typed_rows: dict = {}
    for path in extras:
        member = _MEMBER.match(path)
        typed_rows.setdefault((_offered_form(path).rsplit("/*/", 1)[0] if member else None,
                               member.group(2) if member else None), set()).add(_offered_form(path))
    for key in sorted(ticked):
        listed_paths = set(topics.TOPICS[key]["writables"])
        # A form that is about ONE of something is answered in full FOR THAT ROW: two businesses
        # are two Forms 8829, and half of either is refused the same way half of one is.
        answered = set()
        for (_group, _row), paths in typed_rows.items():
            if paths & listed_paths:
                answered = paths & listed_paths if not answered else answered & paths
        unanswered = [entry["line"] for path, entry in topics.TOPICS[key]["writables"].items()
                      if path not in answered]
        if unanswered:
            raise ServiceFactsError(
                f"{topics.TOPICS[key]['form']} is answered in part — {', '.join(unanswered)} "
                f"{'is' if len(unanswered) == 1 else 'are'} not answered, and without "
                f"{'it' if len(unanswered) == 1 else 'them'} the engine leaves the whole of it out "
                f"of the return; refused rather than computed without it")
        for path, (kind, value) in (topics.TOPICS[key].get("companions") or {}).items():
            if path not in engine_facts:              # the service's own answer always wins
                out[path] = _str(value) if kind == "string" else _tin(*value)
        # An attestation the engine itself reads (`sends`): the page takes the form's figures only
        # once the person has answered it the way the topic computes (`must_be`; the other answer
        # is refused in its own words there), so that answer is the one sent.
        for att in (topics.TOPICS[key].get("attestations") or {}).values():
            if att.get("sends") and att["sends"] not in engine_facts:
                out[att["sends"]] = _bool(att["must_be"])
        gate = topics.TOPICS[key]["gate"]
        if gate is not None:
            # Rule 4, the one place an extra touches a fact the service owns — and only to TRUE.
            # Written for Schedule A (board decision 8): MEASURED on the pinned engine, without
            # `/hasItemizedDeductions` the typed amounts sit in the graph and move nothing, and the
            # return resolves as though the form had not been filled in at all. The service never
            # sets this fact itself, so there is nothing to overwrite; a fact set that DOES carry it
            # keeps its own answer, like every other input here.
            if gate in engine_facts:
                raise ServiceFactsError(
                    f"{topics.TOPICS[key]['form']} is already claimed by this return's own facts, "
                    f"and that answer stands; refused rather than overwritten")
            out[gate] = _bool(True)
    return out


def _resolve_rows(added: dict, engine_facts: dict) -> dict:
    """Rule 6: `/scheduleCs/[0]/writableX` -> the uuid the mapper gave that row. Read off the
    mapped document, never recomputed here: one place makes a collection's ids."""
    import re as _re
    out = {}
    for path, value in added.items():
        member = _MEMBER.match(path)
        if member is None:
            out[path] = value
            continue
        group, row, leaf = member.group(1), int(member.group(2)), member.group(3)
        ids = []
        for key in engine_facts:
            hit = _re.match(rf"^{_re.escape(group)}/(#[0-9a-f-]+)/", key)
            if hit and hit.group(1) not in ids:
                ids.append(hit.group(1))
        if row >= len(ids):
            raise ServiceFactsError(
                f"a line was typed for {group.lstrip('/')} number {row + 1}, and this return has "
                f"{len(ids)}; refused rather than typed against another one")
        out[f"{group}/{ids[row]}/{leaf}"] = value
    return out


def map_with_extras(facts: dict, tax_year: int = 2025, extras: dict | None = None,
                    birth_days: dict | None = None) -> dict:
    """`map_to_engine`, then the validated extras merged in. With no extras this IS `map_to_engine`
    — the same object, untouched — so every caller that has none behaves exactly as before."""
    doc = map_to_engine(facts, tax_year, birth_days=birth_days)
    if not extras:
        return doc
    added = _resolve_rows(validate(extras, doc["facts"]), doc["facts"])
    return {**doc, "facts": {**doc["facts"], **added}}
