#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Fetch the blank IRS forms the fill writes on, into the engine home, and keep only the exact ones.

    YTAX_ENGINE_HOME=<engine home> python3 scripts/fetch_irs_forms.py [--only IRS1040 ...]

Each form's field map (`dictionary/pdf/2025/<FORM>/en/configuration.yml`) was written against one
revision of that IRS form, so a blank form is kept only when its bytes are that revision:
`generated/irs_blank_forms.json` names each file and its SHA-256. The script asks irs.gov for the
current file, then for the archived one, and writes the first whose hash matches. A form that is
not available at that revision is listed and not written; the page reads documents and computes
without it, and refuses by name only to print that one form.

This sends nothing about a return anywhere: it asks for public blank forms by file name, and
nothing else is in the request. Run it once per engine home.

`--base-url` replaces the two irs.gov addresses (a mirror, or a local folder as file:///...);
`{file}` in it is the form's file name and `{stem}` the name without `.pdf`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "generated" / "irs_blank_forms.json"
SOURCES = ("https://www.irs.gov/pub/irs-pdf/{file}",
           "https://www.irs.gov/pub/irs-prior/{stem}--2025.pdf")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_manifest(pdf_root: Path) -> int:
    """Development side: the manifest from an engine home assembled at the pin."""
    forms = {}
    for pdf in sorted(pdf_root.glob("*/en/*.pdf")):
        data = pdf.read_bytes()
        forms[pdf.parent.parent.name] = {"file": pdf.name, "sha256": sha256(data), "bytes": len(data)}
    MANIFEST.write_text(json.dumps({"tax_year": 2025, "forms": forms}, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(f"wrote {MANIFEST.relative_to(REPO)} ({len(forms)} forms)")
    return 0


def fetch(url: str) -> bytes | None:
    request = urllib.request.Request(url, headers={"User-Agent": "ytax-prep"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except (urllib.error.URLError, OSError, ValueError):
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--engine-home", default=os.environ.get("YTAX_ENGINE_HOME"))
    ap.add_argument("--only", action="append", default=[], help="a form key such as IRS1040")
    ap.add_argument("--base-url", action="append", default=[])
    ap.add_argument("--write-manifest", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if not args.engine_home:
        print("set YTAX_ENGINE_HOME (or --engine-home) to the engine home", file=sys.stderr)
        return 2
    pdf_root = Path(args.engine_home) / "dictionary" / "pdf" / "2025"
    if not pdf_root.is_dir():
        print(f"{pdf_root} is not there: the engine home has no form registers", file=sys.stderr)
        return 2
    if args.write_manifest:
        return write_manifest(pdf_root)

    forms = json.loads(MANIFEST.read_text(encoding="utf-8"))["forms"]
    if args.only:
        unknown = sorted(set(args.only) - set(forms))
        if unknown:
            print(f"not a form this version fills: {', '.join(unknown)}", file=sys.stderr)
            return 2
        forms = {k: v for k, v in forms.items() if k in args.only}
    sources = args.base_url or list(SOURCES)
    kept = present = 0
    missing = []
    for key, want in sorted(forms.items()):
        folder = pdf_root / key / "en"
        target = folder / want["file"]
        if target.is_file() and sha256(target.read_bytes()) == want["sha256"]:
            present += 1
            continue
        if not folder.is_dir():
            missing.append(f"{key}: no register for it in this engine home")
            continue
        stem = want["file"][:-len(".pdf")]
        for source in sources:
            data = fetch(source.format(file=want["file"], stem=stem))
            if data is not None and sha256(data) == want["sha256"]:
                target.write_bytes(data)
                kept += 1
                break
        else:
            missing.append(f"{key}: {want['file']} at the revision its field map was written for was "
                           f"not found")
    print(f"{present} already in place, {kept} fetched, {len(missing)} not available")
    for line in missing:
        print(f"  {line}")
    if missing:
        print("A form listed here is not printed; reading documents and computing do not need it.")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
