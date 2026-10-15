# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""What ytax-prep.exe and ytax-prep.app start: the application's desktop entry."""
import sys

from ytax_prep.desktop import main

sys.exit(main())
