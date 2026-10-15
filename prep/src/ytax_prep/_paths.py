# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Where the application's read-only data lives: `schema/` and `generated/`.

From source they sit at the repository root, beside `src/`. In the packaged application they sit
in the frozen app's resource folder (PyInstaller's `sys._MEIPASS`), inside the program's own
folder or app bundle, never above it.
"""
from __future__ import annotations

import sys
from pathlib import Path


def data_root() -> Path:
    frozen = getattr(sys, "_MEIPASS", None)
    return Path(frozen) if frozen else Path(__file__).resolve().parents[2]
