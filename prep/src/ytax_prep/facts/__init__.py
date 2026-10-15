# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Fact mapping — derivative-only service facts -> engine persister-format facts.

The service accepts DERIVATIVE-ONLY facts (no identifiers). The engine needs a full persister fact
set including identifier writables (tin, dateOfBirth) and structural scaffolding. The mapper applies
the reviewed rename table + a base scaffold + synthesis (tin_type -> synthetic placeholder TIN;
birth_year/month -> placeholder-day dateOfBirth). Real identifiers never enter this repo or a stored
artifact — the synthesized placeholders live only inside the engine call.
"""
from .mapper import FactsSchemaError, ServiceFactsError, map_to_engine

__all__ = ["map_to_engine", "ServiceFactsError", "FactsSchemaError"]
