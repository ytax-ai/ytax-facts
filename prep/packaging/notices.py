# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""THIRD-PARTY-NOTICES.txt for the packaged application, and the check that nothing copyleft is
bundled without approval.

    python notices.py --dists > dists.json     (run with the build environment's own Python)

prints the bundled Python distributions (name, version, license, source, license texts) as JSON;
`build_package.py` adds the Python runtime, PyInstaller's bootloader, Node.js, the libraries
compiled into the engine and the IRS blank forms, and writes the file with `write_notices`.

A component whose license or license text names a copyleft license (the GNU licenses, MPL, EPL)
stops the build unless its name is in `pins.json` "approved_copyleft": each is approved, with
its reason in "approved_copyleft_notes", before it is bundled. Output is sorted and carries no build path, so two runs write the same
bytes.
"""
from __future__ import annotations

import json
import re
import sys

COPYLEFT = re.compile(r"\b(?:A?GPL|LGPL|MPL|EPL)\b|GNU (?:Lesser |Affero )?General Public License|"
                      r"Mozilla Public License|Eclipse Public License", re.I)
# Present in the build environment to freeze the application, never inside it.
BUILD_ONLY = {"pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "macholib", "pefile",
              "pywin32-ctypes", "packaging", "setuptools", "pip", "wheel"}
# a top-level LICENSE/COPYING/NOTICE/AUTHORS file, or anything under a dist-info licenses/ folder
# (pypdfium2 carries its PDFium build's per-library texts under licenses/data/<platform>/BUILD_LICENSES/)
LICENSE_FILE = re.compile(r"(^|/)(licen[cs]e|copying|notice|authors)[^/]*$|/licen[cs]es?/.+$", re.I)


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def bundled_distributions() -> list[dict]:
    """Every distribution in the running environment except the freezer's own tools."""
    import importlib.metadata as md
    out = []
    for dist in md.distributions():
        meta = dist.metadata
        name = meta["Name"]
        if not name or _norm(name) in BUILD_ONLY:
            continue
        classifiers = [c.split("::")[-1].strip() for c in (meta.get_all("Classifier") or [])
                       if c.startswith("License ::")]
        license_text = meta.get("License-Expression") or (meta.get("License") or "").strip()
        if len(license_text) > 120 or "\n" in license_text:
            license_text = ""                       # a full text in the field: carried below instead
        urls = dict(u.split(", ", 1) for u in (meta.get_all("Project-URL") or []) if ", " in u)
        source = (urls.get("Source") or urls.get("Source Code") or urls.get("Repository")
                  or urls.get("Homepage") or meta.get("Home-page") or f"https://pypi.org/project/{name}/")
        texts = []
        for f in sorted(dist.files or [], key=str):
            if LICENSE_FILE.search(str(f)):
                try:
                    data = f.locate().read_bytes()
                except OSError:
                    continue
                texts.append((str(f).split("/")[-1], data.decode("utf-8", errors="replace")))
        out.append({"name": name, "version": meta["Version"],
                    "license": license_text or "; ".join(classifiers) or "see license text",
                    "source": source, "texts": texts})
    return sorted(out, key=lambda d: _norm(d["name"]))


def copyleft_hits(components: list[dict]) -> list[str]:
    """Names of components whose license or license texts name a copyleft license."""
    hits = []
    for c in components:
        blob = c["license"] + "\n" + "\n".join(t for _, t in c.get("texts", []))
        if COPYLEFT.search(blob):
            hits.append(c["name"])
    return hits


def write_notices(path, components: list[dict], header: str) -> None:
    rule = "=" * 78
    lines = [header.rstrip(), "", "Bundled components:", ""]
    for c in components:
        lines.append(f"  {c['name']} {c['version']} — {c['license']} — {c['source']}")
    lines.append("")
    for c in components:
        lines += [rule, f"{c['name']} {c['version']}", f"License: {c['license']}",
                  f"Source: {c['source']}"]
        for note in c.get("notes", []):
            lines.append(note)
        for name, text in c.get("texts", []):
            lines += ["", f"--- {name} ---", text.rstrip()]
        lines.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as out:
        out.write("\n".join(lines).rstrip() + "\n")


if __name__ == "__main__":
    if sys.argv[1:] == ["--dists"]:
        json.dump(bundled_distributions(), sys.stdout, indent=1, sort_keys=True)
    else:
        print(__doc__)
        sys.exit(2)
