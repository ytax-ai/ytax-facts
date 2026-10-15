# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Top-level forward adapter: neutral documents + interview -> one FG :class:`FactSet`.

This is the assembly point the engine integration hands to the engine runner. It merges
interview-entered writable facts with per-document writable facts, allocating one collection instance per
document and accumulating collection membership. Instance ids are injectable so tests can
assert byte-exact persister output; the default is a random UUID per document.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from ..ingest.models import ExtractedDocument
from .facts import FactSet
from .interview import Interview
from .mapping import FORM_MAPPINGS, map_document


@dataclass
class DocumentInput:
    """One ingested document plus the filer it belongs to (default: the primary filer)."""

    ir: ExtractedDocument
    filer_id: str | None = None


def adapt(
    documents: list[DocumentInput],
    interview: Interview,
    *,
    id_factory: Callable[[int], str] | None = None,
) -> FactSet:
    """Build the merged writable-fact set for a return.

    Interview facts are emitted first (filers, filing status, dependents), then each document
    is mapped to its collection instance. Raises ``UnsupportedForm`` if a document's form has
    no writable mapping — the caller decides whether to pre-filter (we never invent a path).
    """
    make_id = id_factory or (lambda _i: str(uuid.uuid4()))
    fs = FactSet()
    fs.extend(interview.build_facts())

    for index, doc in enumerate(documents):
        instance_id = make_id(index)
        filer_id = doc.filer_id or interview.primary_filer_id
        fs.extend(map_document(doc.ir, instance_id, filer_id))
        fs.add_collection_member(FORM_MAPPINGS[doc.ir.form_type].collection, instance_id)

    return fs


__all__ = ["DocumentInput", "Interview", "ExtractedDocument", "adapt"]
