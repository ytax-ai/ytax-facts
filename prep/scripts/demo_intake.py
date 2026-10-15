#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Start the local intake page for a review, on synthetic documents only.

    YTAX_ENGINE_HOME=<pin> collector/.venv/bin/python scripts/demo_intake.py [--port 8766] [--profile profile-C]

Makes a working folder under this repo's gitignored `tmp/demo-intake/<profile>/`, copies the
showcase profile's SYNTHETIC PDFs beside it (`documents/`, for dropping onto the page), starts
the server on 127.0.0.1 and prints the one URL that opens it (the launch token is in the URL).
Nothing leaves the machine: the page, the reader, the engine and the filled forms all run here.
Stop it with Ctrl+C, or `kill` the process the first line names.
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for p in (REPO / "src", REPO / "collector", REPO):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# The demo profiles shipped with the application, unless YTAX_SHOWCASE_PROFILES names another set.
SHOWCASE = (Path(os.environ["YTAX_SHOWCASE_PROFILES"]) if os.environ.get("YTAX_SHOWCASE_PROFILES")
            else REPO / "examples" / "profiles")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--profile", default="all",
                    help="one demo profile's documents, or `all` (default): every profile's, "
                         "each in its own folder under documents/, so any input form can be tried; "
                         "or `examples`: this repo's examples/forms/, one PDF per form read")
    args = ap.parse_args(argv)
    if not os.environ.get("YTAX_ENGINE_HOME"):
        print("set YTAX_ENGINE_HOME to the pinned engine home (BUILD.md, 'Run from the source files')",
              file=sys.stderr)
        return 2
    if args.profile != "examples" and not SHOWCASE.is_dir():
        print(f"no demo profiles at {SHOWCASE}; set YTAX_SHOWCASE_PROFILES to a profiles directory",
              file=sys.stderr)
        return 2
    if args.profile not in ("all", "examples") and not (SHOWCASE / args.profile / "input").is_dir():
        print(f"no demo profile {args.profile!r} under {SHOWCASE}", file=sys.stderr)
        return 2
    folder = REPO / "tmp" / "demo-intake" / args.profile
    docs = folder / "documents"
    docs.mkdir(parents=True, exist_ok=True)
    if args.profile == "examples":
        chosen = []
        for pdf in sorted((REPO / "examples" / "forms").glob("*.pdf")):
            shutil.copy(pdf, docs / pdf.name)
        copied = len(list(docs.glob("*.pdf")))
    else:
        chosen = sorted(d for d in SHOWCASE.iterdir() if d.is_dir() and (d / "input").is_dir()) \
            if args.profile == "all" else [SHOWCASE / args.profile]
        copied = 0
    for profile in chosen:
        target = docs / profile.name if args.profile == "all" else docs
        target.mkdir(parents=True, exist_ok=True)
        for pdf in sorted((profile / "input").glob("*.pdf")):
            shutil.copy(pdf, target / pdf.name)
            copied += 1
    print(f"{copied} synthetic documents from "
          f"{'examples/forms' if args.profile == 'examples' else f'{len(chosen)} profile(s)'}",
          flush=True)
    from ytax_prep.intake.server import make_server
    server, url = make_server(folder, port=args.port)
    print(f"pid {os.getpid()}", flush=True)
    print(f"URL {url}", flush=True)
    print(f"documents to drop: {docs}", flush=True)
    print(f"working folder (the page asks for it): {folder}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
