# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Fill the pinned IRS fillable PDFs, client-side, stdlib only.

`reader` parses a template's cross-reference streams, object streams and AcroForm field tree;
`writer` appends an incremental update that sets field values and never rewrites the template
bytes; `registers` reads build's `configuration.yml` field registers. The design record is
`docs/superpowers/specs/2026-09-01-form-fill-design.md`.
"""
from .reader import PdfTemplate, PdfSurprise  # noqa: F401
