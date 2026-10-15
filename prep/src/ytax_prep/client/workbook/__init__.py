# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The collection/review workbook: the surface where a person sees the whole fact set and corrects it.

Documents are read by the Collector, turned into facts by `client/documents.py`, and the residue is
asked as an interview — but nothing let a person see the whole thing at once and fix it. This is
that surface. **Running compute IS the review**: no sign-off tab, no `confirmed?`
column, iterate as often as you like.

Written and read back with the STDLIB — `zipfile` plus hand-built OOXML — so the served container
carries no spreadsheet dependency at all.

`build_workbook` / `rewrite_workbook` write; `read_workbook` reads. Nothing else is public.
"""
from .reader import WorkbookRead, WorkbookRefused, read_workbook
from .writer import WriterRefused, build_workbook, rewrite_workbook

__all__ = ["build_workbook", "rewrite_workbook", "WriterRefused",
           "read_workbook", "WorkbookRead", "WorkbookRefused"]
