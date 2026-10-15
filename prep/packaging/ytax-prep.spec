# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

# PyInstaller spec for the packaged application, run by packaging/build_package.py, which sets the
# YTAX_PKG_* variables below. One folder, no console window: ytax-prep.exe on Windows, and on
# macOS ytax-prep.app (bundle id ai.ytax.prep) with no Dock icon, since the application's window is
# the page it opens in the browser. The engine, Node.js, the license documents and the examples are
# added to the frozen folder by build_package.py after this runs.
import glob
import os
import re

SRC = os.environ["YTAX_PKG_SRC"]                  # prep/src
COLLECTOR = os.environ["YTAX_PKG_COLLECTOR"]      # prep/collector
DATA = os.environ["YTAX_PKG_DATA"]                # prep/ (schema/, generated/)
VERSION = os.environ["YTAX_PKG_VERSION"]
ARCH = os.environ.get("YTAX_PKG_ARCH") or None    # macOS: arm64 or x86_64, one pass each
# Info.plist's version keys take numbers only (alpha-0.1.0 is 0.1.0 there); the label itself is what
# the About page, README-FIRST.txt and the zip's name show
PLIST_VERSION = re.search(r"\d+(?:\.\d+){0,2}", VERSION).group(0)

page = [(f, "ytax_prep/intake/page") for f in sorted(glob.glob(os.path.join(SRC, "ytax_prep", "intake", "page", "*")))]
data = []
for top in ("schema", "generated"):
    for path in sorted(glob.glob(os.path.join(DATA, top, "**", "*"), recursive=True)):
        if os.path.isfile(path):
            data.append((path, os.path.dirname(os.path.relpath(path, DATA))))

a = Analysis(
    [os.path.join(SPECPATH, "entry.py")],
    pathex=[SRC, COLLECTOR],
    datas=page + data,
    hiddenimports=["ytax_prep.intake.server", "collector.ingest.pdftext", "pdfplumber", "pypdf"],
    excludes=["tkinter", "numpy", "rapidocr", "onnxruntime", "cv2", "reportlab", "pytest",
              "openpyxl", "IPython", "setuptools", "pip"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [("X utf8_mode=1", None, "OPTION")], exclude_binaries=True,
          name="ytax-prep", console=False, disable_windowed_traceback=False, upx=False,
          strip=False, target_arch=ARCH, codesign_identity=None, entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="ytax-prep")
if os.environ.get("YTAX_PKG_PLATFORM") == "macos":
    # macOS 13.5: the minimum the bundled Node.js 24 binaries declare (LC_BUILD_VERSION minos, both
    # architectures); the bundled Python asks for less
    app = BUNDLE(coll, name="ytax-prep.app", bundle_identifier="ai.ytax.prep", version=PLIST_VERSION,
                 info_plist={"CFBundleName": "ytax-prep", "CFBundleDisplayName": "ytax-prep",
                             "CFBundleShortVersionString": PLIST_VERSION, "CFBundleVersion": PLIST_VERSION,
                             "LSUIElement": True, "NSHighResolutionCapable": True,
                             "LSMinimumSystemVersion": "13.5"})
