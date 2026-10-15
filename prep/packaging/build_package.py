#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Build the downloadable package of ytax-prep from the released files.

    python prep/packaging/build_package.py --version alpha-0.1.0 [--out DIR]

Run from a checkout of the release (the folder that holds prep/, engine/, js/ and dictionary/),
on Windows x64 or macOS, with the Python that packaging/pins.json names. It writes

    ytax-prep-<version>-windows-x64.zip      on Windows
    ytax-prep-<version>-macos-universal.zip  on macOS (one app for Apple silicon and Intel)

(--version alpha-0.1.0 writes ytax-prep-alpha-0.1.0-windows-x64.zip; the same label is the
version the app's About page and README-FIRST.txt show.)

Each zip holds README-FIRST.txt, THIRD-PARTY-NOTICES.txt, examples/ (when the release carries
them) and the application: ytax-prep.exe with its _internal/ folder, or ytax-prep.app. The user
unzips it and double-clicks the launcher; the package carries every runtime it needs.

What it uses, and nothing else:
  - the released files: prep/ (this application), js/ (the engine compiled to JavaScript,
    js/engine/factgraph.js, pinned by SHA-256, with its library list and the TypeScript the runner
    imports), dictionary/ty2025/ and dictionary/pdf/2025/ (the dictionary and the
    IRS forms' field maps), LICENSE, LICENSING.md, LICENSES/ and legal/, and the engine's
    libraries' license and NOTICE files (js/engine/third-party/);
  - downloads pinned by SHA-256 in packaging/pins.json and packaging/requirements-<platform>.txt:
    Node.js, the Python packages and PyInstaller, and the IRS blank forms
    (generated/irs_blank_forms.json); npm fetches what js/package-lock.json pins;
  - a build tool that never enters the package: npm (to run the engine's dictionary generator).
    No JDK and no sbt: the release carries the engine already compiled to JavaScript.

Two runs on the same platform give the same zip, byte for byte: SOURCE_DATE_EPOCH (or
pins.json's default) dates every entry, entries are sorted, permissions are fixed, and no build
path or user name is written. On macOS the app is ad-hoc signed so it runs on Apple silicon;
Developer ID signing, notarization and an installer come later and need no change to this layout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent            # prep/packaging
PREP = HERE.parent                                 # prep/
PINS = HERE / "pins.json"
APP = "ytax-prep"


# A version label as it appears in the zip's name and on the About page: alpha-0.1.0, 0.1.0,
# 0.1.0-rc.4. Letters, digits, dots, plus and hyphens only, since it is part of a file name.
VERSION_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]*")


class Stop(RuntimeError):
    """The build cannot go on; the message says why and what to do."""


def say(text: str) -> None:
    print(f"[package] {text}", flush=True)


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    say(" ".join(str(c) for c in cmd))
    done = subprocess.run([str(c) for c in cmd], **kw)
    if done.returncode != 0:
        raise Stop(f"{cmd[0]} exited {done.returncode}")
    return done


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---- the platform and the pins -----------------------------------------------------------------

def target() -> str:
    if sys.platform == "win32" and platform.machine().lower() in ("amd64", "x86_64"):
        return "windows-x64"
    if sys.platform == "darwin":
        return "macos-universal"
    if sys.platform.startswith("linux"):
        return "linux-x64"                         # a test build only: never released (S-10)
    raise Stop(f"no package is built on {sys.platform} {platform.machine()}")


def load_pins() -> dict:
    if not PINS.is_file():
        raise Stop(f"{PINS} is missing: it pins Python, Node.js and PyInstaller by version and hash")
    return json.loads(PINS.read_text(encoding="utf-8"))


def check_python(pins: dict, plat: str, allow_other: bool) -> None:
    want = pins["python"]["version"]
    have = platform.python_version()
    if have != want and not allow_other:
        raise Stop(f"this build needs Python {want} (pins.json); this is {have}")
    if plat == "macos-universal":
        archs = subprocess.run(["lipo", "-archs", sys.executable], capture_output=True, text=True).stdout
        if not {"arm64", "x86_64"} <= set(archs.split()):
            raise Stop("the macOS package needs a universal2 Python (python.org's macOS installer); "
                       f"{sys.executable} is {archs.strip() or 'not universal'}")


def download(url: str, want_sha256: str, cache: Path) -> Path:
    """A pinned download: fetched once into the cache, and refused unless its SHA-256 matches."""
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / url.rsplit("/", 1)[-1]
    if dest.is_file() and sha256(dest) == want_sha256:
        return dest
    say(f"download {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": APP}), timeout=300) as r, \
                open(tmp, "wb") as out:
            shutil.copyfileobj(r, out)
    except OSError as why:                 # URLError and HTTPError are OSErrors
        raise Stop(f"{url}: {why}")
    got = sha256(tmp)
    if got != want_sha256:
        tmp.unlink()
        raise Stop(f"{url}: SHA-256 {got} is not the pinned {want_sha256}")
    tmp.replace(dest)
    return dest


# ---- the release -------------------------------------------------------------------------------

def check_release(root: Path) -> dict:
    need = {"prep": root / "prep", "js": root / "js", "factgraph.js": root / "js" / "engine" / "factgraph.js",
            "dictionary": root / "dictionary" / "ty2025", "pdf": root / "dictionary" / "pdf" / "2025",
            "LICENSE": root / "LICENSE", "LICENSING.md": root / "LICENSING.md", "LICENSES": root / "LICENSES",
            "legal": root / "legal", "third-party": root / "js" / "engine" / "third-party"}
    missing = [f"{k} ({p})" for k, p in need.items() if not p.exists()]
    if missing:
        raise Stop("the release is missing: " + ", ".join(missing))
    sys.path.insert(0, str(PREP / "src"))
    from ytax_prep.engine import adapter
    if adapter.dictionary_sha256(need["dictionary"]) != adapter.PINNED_DICTIONARY_SHA256:
        raise Stop("dictionary/ty2025 is not the dictionary this application is pinned to "
                   f"({adapter.PINNED_DICTIONARY_SHA256})")
    if sha256(need["factgraph.js"]) != adapter.PINNED_FACTGRAPH_SHA256:
        raise Stop("js/engine/factgraph.js is not the engine this application is pinned to "
                   f"(sha256 {adapter.PINNED_FACTGRAPH_SHA256})")
    return need


# ---- the engine on JavaScript ------------------------------------------------------------------

def build_js_engine(rel: dict, work: Path, engine_home: Path) -> None:
    """The engine compiled to JavaScript, its generated dictionary, and this application's runner
    bundled with them, into <engine-home>/js-engine/."""
    for tool in ("node", "npm"):
        if shutil.which(tool) is None:
            raise Stop(f"{tool} is needed to build the engine (prep/BUILD.md, 'Build tools')")
    src = work / "engine-src"
    if src.exists():
        shutil.rmtree(src)
    # never a stale build output from the release tree: node_modules, generated dictionaries
    # (named exactly: js/src/generatedDictionary.ts is source and must come along)
    skip = {"node_modules", "generated", "generated-l2"}
    shutil.copytree(rel["js"], src / "js", ignore=lambda folder, names: [n for n in names if n in skip])
    # the engine as the release carries it: linked once by the engine's own build and checked there
    # against the JVM, pinned here by SHA-256 (check_release). A link made here would not be the
    # same bytes twice: Scala.js does not write the exported methods in a stable order
    say(f"engine: the release's js/engine/factgraph.js (sha256 {sha256(rel['factgraph.js'])})")
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    run([npm, "ci", "--no-audit", "--no-fund"], cwd=src / "js")
    generated = src / "js" / "fact-dictionary" / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "FACT_DICTIONARY_SOURCE_DIR": generator_source_dir(rel["dictionary"], src / "js"),
           "FACT_DICTIONARY_OUTPUT_DIR": str(generated), "NODE_OPTIONS": "--max-old-space-size=4096"}
    run(["node", "--import", "tsx", "fact-dictionary/generate-src/generate.ts"], cwd=src / "js", env=env)
    esbuild = src / "js" / "node_modules" / ".bin" / ("esbuild.cmd" if sys.platform == "win32" else "esbuild")
    for name in ("facts", "paths", "wrappedFacts", "submissionBlockingFacts", "exportToStateFacts"):
        run([esbuild, generated / f"{name}.ts", "--format=cjs", "--platform=node",
             f"--outfile={generated / (name + '.js')}", "--log-level=warning"])
    # "\n" on every platform, so the engine is the same bytes wherever it is built
    (generated / "package.json").write_text('{"type": "commonjs"}\n', encoding="utf-8", newline="\n")

    out = engine_home / "js-engine"
    (out / "bin").mkdir(parents=True)
    # bundled from inside js/ with relative paths: esbuild names each module in a comment, and a
    # path relative to js/ is the same on every machine and every run
    shutil.copyfile(PREP / "src" / "ytax_prep" / "engine" / "js" / "runner.mjs", src / "js" / "ytax-runner.mjs")
    run([esbuild, "ytax-runner.mjs", "--bundle", "--platform=node", "--format=esm", "--target=node20",
         "--alias:ytax-js=.", "--legal-comments=eof", f"--outfile={out / 'bin' / 'runner.mjs'}",
         "--log-level=warning"], cwd=src / "js")
    shutil.copytree(generated, out / "fact-dictionary" / "generated",
                    ignore=shutil.ignore_patterns("*.ts"))
    from ytax_prep.engine import adapter
    (out / "BUILT-FROM.json").write_text(json.dumps(
        {"dictionary_sha256": adapter.dictionary_sha256(rel["dictionary"]),
         "factgraph_sha256": sha256(rel["factgraph.js"])}, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    # the libraries linked into it, as the engine's build lists them, for the notices
    shutil.copyfile(rel["js"] / "engine" / "factgraph.libraries.tsv", work / "engine-libraries.tsv")


def generator_source_dir(dictionary: Path, cwd: Path) -> str:
    """The dictionary folder as the generator is given it: relative to the folder it runs in. The
    generator reads FACT_DICTIONARY_SOURCE_DIR as a `:`-separated list of folders
    (js/fact-dictionary/generate-src/readRawFacts.ts), so a Windows path's drive letter (`D:\\...`)
    would split off as a folder named `D`."""
    try:
        relative = os.path.relpath(dictionary, cwd)
    except ValueError:                        # Windows: on another drive, no relative path exists
        raise Stop(f"the dictionary ({dictionary}) and the build folder ({cwd}) are on different "
                   "drives; put --out on the release's drive")
    if ":" in relative:
        raise Stop(f"the dictionary's path from the build folder has a ':' in it ({relative}), "
                   "which the generator reads as a separator")
    return relative


# What the application reads from dictionary/pdf/2025: each form's field map (configuration.yml)
# and printed-box sidecar (boxes.tsv), and the shared form-modules.tsv. The other registers there
# (gates, column-axes, continuations, transforms, box-aliases, printed-boxes-source, field-index)
# serve the dictionary's own generator checks; the reviews and reports are its development record.
_PDF_REGISTER_FILES = {"configuration.yml", "boxes.tsv", "form-modules.tsv"}


def _pdf_register_ignore(folder: str, names: list) -> set:
    return {n for n in names if n == "reviews"
            or (not (Path(folder) / n).is_dir() and n not in _PDF_REGISTER_FILES)}


def stage_engine_home(rel: dict, engine_home: Path, cache: Path, pins: dict) -> None:
    """The dictionary, the IRS forms' field maps, and the blank forms fetched by their pinned hash:
    only the forms this application prints (form-modules.tsv `render`); a form a person receives
    (a W-2, a 1099) is read, never printed, so its field map is enough."""
    shutil.copytree(rel["dictionary"], engine_home / "dictionary" / "ty2025")
    pdf = engine_home / "dictionary" / "pdf" / "2025"
    shutil.copytree(rel["pdf"], pdf, ignore=_pdf_register_ignore)
    forms = json.loads((PREP / "generated" / "irs_blank_forms.json").read_text(encoding="utf-8"))["forms"]
    from ytax_prep.client.pdfform.registers import form_kinds
    kinds = form_kinds(rel["pdf"])
    forms = {key: want for key, want in forms.items() if kinds.get(key) == "render"}
    sources = pins["irs_blank_forms"]["sources"]
    for key, want in sorted(forms.items()):
        folder = pdf / key / "en"
        if not folder.is_dir():
            continue
        stem = want["file"][:-len(".pdf")]
        for source in sources:
            try:
                got = download(source.format(file=want["file"], stem=stem), want["sha256"], cache / "irs")
            except Stop:
                continue
            shutil.copyfile(got, folder / want["file"])
            break
        else:
            raise Stop(f"{key}: no source gave {want['file']} at its pinned revision")


# ---- Node.js ----------------------------------------------------------------------------------

def stage_node(plat: str, pins: dict, cache: Path, work: Path, dest: Path) -> dict:
    """The node executable and its license, from the pinned archives; one universal binary on macOS."""
    node = pins["node"]
    dest.mkdir(parents=True)
    unpacked = {}
    for arch, entry in sorted(node["archives"][plat].items()):
        archive = download(entry["url"], entry["sha256"], cache / "node")
        out = work / f"node-{arch}"
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        if archive.name.endswith(".zip"):
            with zipfile.ZipFile(archive) as z:
                z.extractall(out)
        else:
            with tarfile.open(archive) as t:
                t.extractall(out, filter="data")
        (top,) = [p for p in out.iterdir() if p.is_dir()]
        unpacked[arch] = top
    first = next(iter(unpacked.values()))
    shutil.copyfile(first / "LICENSE", dest / "LICENSE")
    if plat == "windows-x64":
        shutil.copyfile(unpacked["x64"] / "node.exe", dest / "node.exe")
    elif plat == "macos-universal":
        run(["lipo", "-create", unpacked["arm64"] / "bin" / "node", unpacked["x64"] / "bin" / "node",
             "-output", dest / "node"])
        (dest / "node").chmod(0o755)
    else:
        shutil.copyfile(unpacked["x64"] / "bin" / "node", dest / "node")
        (dest / "node").chmod(0o755)
    return {"name": "Node.js", "version": node["version"], "license": "MIT (and the licenses of its "
            "bundled components, below)", "source": f"https://github.com/nodejs/node/tree/{node['version']}",
            "texts": [("LICENSE", (dest / "LICENSE").read_text(encoding="utf-8"))]}


# ---- the frozen application --------------------------------------------------------------------

REQUIREMENTS_OVERRIDE: Path | None = None


def freeze(plat: str, work: Path, version: str, arch: str | None, epoch: int) -> Path:
    """A hash-checked environment and a PyInstaller run; returns the frozen folder or app."""
    tag = f"{plat}-{arch}" if arch else plat
    venv = work / f"venv-{tag}"
    if venv.exists():
        shutil.rmtree(venv)
    prefix = ["arch", f"-{arch}"] if arch else []
    run([*prefix, sys.executable, "-m", "venv", venv])
    py = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    req = REQUIREMENTS_OVERRIDE or HERE / f"requirements-{'macos-' + arch if arch else plat}.txt"
    run([*prefix, py, "-m", "pip", "install", "--require-hashes", "--no-deps", "--only-binary=:all:",
         "--no-compile",
         "--no-input", "--disable-pip-version-check", "-r", req])
    env = {**os.environ, "YTAX_PKG_SRC": str(PREP / "src"), "YTAX_PKG_COLLECTOR": str(PREP / "collector"),
           "YTAX_PKG_DATA": str(PREP), "YTAX_PKG_VERSION": version, "YTAX_PKG_ARCH": arch or "",
           "YTAX_PKG_PLATFORM": "macos" if plat == "macos-universal" else plat,
           "SOURCE_DATE_EPOCH": str(epoch), "PYTHONHASHSEED": "0"}
    dist, build = work / f"dist-{tag}", work / f"build-{tag}"
    run([*prefix, py, "-m", "PyInstaller", "--noconfirm", "--clean", f"--distpath={dist}",
         f"--workpath={build}", HERE / "ytax-prep.spec"], env=env)
    dists = json.loads(run([*prefix, py, HERE / "notices.py", "--dists"], capture_output=True,
                           text=True).stdout)
    (work / f"dists-{tag}.json").write_text(json.dumps(dists), encoding="utf-8")
    pyinstaller = run([*prefix, py, "-c", "import PyInstaller,os;print(PyInstaller.__version__);"
                       "print(os.path.dirname(PyInstaller.__file__))"], capture_output=True, text=True).stdout.split("\n")
    (work / f"pyinstaller-{tag}.txt").write_text("\n".join(pyinstaller), encoding="utf-8")
    return dist / (f"{APP}.app" if plat == "macos-universal" else APP)


def drop_per_build_records(app: Path) -> None:
    """What each macOS build writes about itself, which differs between the two and is remade or
    dropped anyway: each installed distribution's file list (*.dist-info/RECORD, dropped from the
    package later) and the ad-hoc signature (_CodeSignature/, remade when the joined app is signed
    with codesign --deep)."""
    # Each Contents/Resources/*.dist-info is a link into Contents/Frameworks/, so a search finds
    # the same file twice: only a path that goes through no link is removed, and a file already
    # gone is not an error (seen on GitHub's macos-14, 2026-10-13).
    for record in sorted(app.rglob("*.dist-info/RECORD")):
        if not _through_link(record, app):
            record.unlink(missing_ok=True)
    for signature in sorted(app.rglob("_CodeSignature")):
        if not _through_link(signature, app) and signature.is_dir():
            shutil.rmtree(signature)


def _through_link(path: Path, root: Path) -> bool:
    """Whether `path`, or a folder between `root` and it, is a link."""
    here = root
    for part in path.relative_to(root).parts:
        here = here / part
        if here.is_symlink():
            return True
    return False


def fuse_universal(arm: Path, x86: Path, out: Path) -> None:
    """One app for both processors: files equal in both builds are kept, Mach-O files that differ
    are joined with lipo, and anything else that differs stops the build."""
    if out.exists():
        shutil.rmtree(out)
    for build in (arm, x86):
        drop_per_build_records(build)
    problems = []
    for src in sorted(arm.rglob("*")):
        rel = src.relative_to(arm)
        other, dest = x86 / rel, out / rel
        if src.is_symlink():
            if not other.is_symlink() or os.readlink(src) != os.readlink(other):
                problems.append(f"{rel}: symlink differs")
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(os.readlink(src), dest)
        elif src.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        elif not other.is_file():
            problems.append(f"{rel}: only in the arm64 build")
        elif src.read_bytes() == other.read_bytes():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        elif _macho(src) and _macho(other):
            dest.parent.mkdir(parents=True, exist_ok=True)
            run(["lipo", "-create", src, other, "-output", dest])
            dest.chmod(src.stat().st_mode & 0o777)
        else:
            problems.append(f"{rel}: differs between the arm64 and x86_64 builds")
    problems += [f"{p.relative_to(x86)}: only in the x86_64 build" for p in sorted(x86.rglob("*"))
                 if not (arm / p.relative_to(x86)).exists() and not (arm / p.relative_to(x86)).is_symlink()]
    if problems:
        raise Stop("the two macOS builds cannot be joined:\n  " + "\n  ".join(problems[:40]))


def _macho(path: Path) -> bool:
    with open(path, "rb") as f:
        return f.read(4) in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca")


# ---- the package -------------------------------------------------------------------------------

def resource_dirs(plat: str, app: Path) -> tuple[Path, Path]:
    """(code folder, data folder) inside the frozen app: PyInstaller's resource folder holds both
    on Windows; on macOS code goes in Contents/Frameworks and data in Contents/Resources, linked
    from Frameworks, the layout signing expects."""
    if plat == "macos-universal":
        return app / "Contents" / "Frameworks", app / "Contents" / "Resources"
    return app / "_internal", app / "_internal"


def add_data(code: Path, data: Path, name: str, source: Path) -> None:
    shutil.copytree(source, data / name, symlinks=True)
    if code != data:
        os.symlink(os.path.join("..", "Resources", name), code / name)


def about_folder(rel: dict, dest: Path, version: str, notices: Path) -> None:
    dest.mkdir(parents=True)
    (dest / "VERSION").write_text(version + "\n", encoding="utf-8")
    shutil.copyfile(rel["LICENSE"], dest / "LICENSE")
    shutil.copyfile(rel["LICENSING.md"], dest / "LICENSING.md")
    shutil.copytree(rel["LICENSES"], dest / "LICENSES")    # LICENSING.md and legal/ link to it
    shutil.copytree(rel["legal"], dest / "legal")
    shutil.copyfile(notices, dest / "THIRD-PARTY-NOTICES.txt")


def engine_components(work: Path, third_party: Path) -> list[dict]:
    """The libraries compiled into the engine's JavaScript, from the list the release carries beside
    it (js/engine/factgraph.libraries.tsv), each with its license from packaging/engine-licenses.json
    (reviewed at that version and license; an unknown library, or a version or SPDX license that
    differs from the list's, stops the build), and the NOTICE and other files the engine's build
    collected for it (js/engine/third-party/, named in its manifest.json): the Apache License asks
    that a work's NOTICE travel with it."""
    table = json.loads((HERE / "engine-licenses.json").read_text(encoding="utf-8"))
    manifest = third_party / "manifest.json"
    if not manifest.is_file():
        raise Stop(f"no {manifest}: the engine's libraries' license and NOTICE files")
    collected = {(e["organization"], e["name"]): e for e in json.loads(manifest.read_text(encoding="utf-8"))}
    report = work / "engine-libraries.tsv"
    if not report.is_file():
        raise Stop("no js/engine/factgraph.libraries.tsv beside the engine")
    seen, listed, coords = {}, {}, {}
    for line in report.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#") or line.startswith("organization\t"):
            continue
        org, name, version, license_ = (line.split("\t") + [""])[:4]
        seen[f"{org}:{name}"] = version
        listed[f"{org}:{name}"] = license_
        coords[f"{org}:{name}"] = (org, name)
    out, unknown = [], []
    for key, rev in sorted(seen.items()):
        if key in table.get("ours", []):
            continue
        base = re.sub(r"_(sjs1_)?(3|2\.13)$", "", key)
        entry = table["libraries"].get(base)
        if entry is None or entry["version"] != rev:
            unknown.append(f"{key} {rev}" + ("" if entry is None else f" (reviewed at {entry['version']})"))
            continue
        if entry["license"] != listed[key]:
            unknown.append(f"{key} {rev}: the engine's list says {listed[key]!r}, the review "
                           f"{entry['license']!r}")
            continue
        notes = ["Compiled into the engine's JavaScript (engine-home/js-engine/bin/runner.mjs)."]
        if entry.get("note"):
            notes.append(entry["note"])
        repo = entry["source"].replace("https://github.com/", "").strip("/").replace("/", "__")
        text = HERE / "licenses" / "engine" / f"{repo}.txt"
        texts = [("LICENSE", text.read_text(encoding="utf-8"))] if text.is_file() else []
        texts += [(extra, (HERE / "licenses" / "engine" / extra).read_text(encoding="utf-8"))
                  for extra in entry.get("extra_texts", [])]
        if not texts:
            unknown.append(f"{key} {rev} (no license text in packaging/licenses/engine/)")
            continue
        entry_files = collected.get(coords[key])
        if entry_files is None:
            unknown.append(f"{key} {rev} (not in js/engine/third-party/manifest.json)")
            continue
        have = {body.strip() for _, body in texts}
        for extra in [entry_files.get("notice_file"), *entry_files.get("extra_files", [])]:
            if not extra:
                continue
            path = third_party / extra
            if not path.is_file():
                unknown.append(f"{key} {rev} (js/engine/third-party/{extra} is missing)")
                continue
            body = path.read_text(encoding="utf-8")
            if body.strip() not in have:           # a text already carried is not repeated
                texts.append((extra, body))
                have.add(body.strip())
        out.append({"name": base, "version": rev, "license": entry["license"], "source": entry["source"],
                    "notes": notes, "texts": texts})
    if unknown:
        raise Stop("libraries in the engine with no reviewed license in engine-licenses.json: "
                   + ", ".join(unknown))
    return out


def notices_for(plat: str, work: Path, tags: list[str], node: dict, pins: dict,
                third_party: Path) -> list[dict]:
    dists = {}
    for tag in tags:
        for d in json.loads((work / f"dists-{tag}.json").read_text(encoding="utf-8")):
            dists.setdefault(d["name"].lower(), d)
    pyi_version, pyi_dir = (work / f"pyinstaller-{tags[0]}.txt").read_text(encoding="utf-8").split("\n")[:2]
    copying = Path(pyi_dir).parent / "COPYING.txt"
    copying = copying if copying.is_file() else Path(pyi_dir) / "COPYING.txt"
    py_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not py_license.is_file():
        found = sorted(Path(sys.base_prefix).rglob("LICENSE.txt"))
        py_license = found[0] if found else py_license
    components = [
        {"name": "Python", "version": platform.python_version(), "license": "PSF-2.0",
         "source": f"https://www.python.org/downloads/release/python-{platform.python_version().replace('.', '')}/",
         "texts": [("LICENSE.txt", py_license.read_text(encoding="utf-8"))] if py_license.is_file() else []},
        {"name": "PyInstaller bootloader and runtime hooks", "version": pyi_version,
         "license": "bootloader: GPL-2.0-or-later WITH PyInstaller bootloader exception; "
                    "runtime hooks and modules: Apache-2.0",
         "source": f"https://github.com/pyinstaller/pyinstaller/tree/v{pyi_version}",
         "notes": ["Unmodified bootloader from the pinned PyInstaller release."],
         "texts": [("COPYING.txt", copying.read_text(encoding="utf-8"))] if copying.is_file() else []},
        *sorted(dists.values(), key=lambda d: d["name"].lower()),
        node,
        *engine_components(work, third_party),
        {"name": "IRS blank forms", "version": "2025", "license": "Public domain (works of the U.S. "
         "Government, 17 U.S.C. 105)", "source": "https://www.irs.gov/forms-instructions", "texts": []},
        *pins.get("supplements", []),
    ]
    from notices import copyleft_hits
    approved = set(pins.get("approved_copyleft", []))
    unapproved = [n for n in copyleft_hits(components) if n not in approved]
    if unapproved:
        raise Stop("copyleft components not approved for bundling (pins.json approved_copyleft): "
                   + ", ".join(unapproved))
    return components


# The longest path an entry in the zip may have. Windows' own "Extract All" refuses a path over
# 260 characters (MAX_PATH), and it extracts into a folder named after the zip inside the person's
# Downloads folder (about 60 characters before the entry's own path); 140 leaves room for a longer
# user or OneDrive folder. Measured 2026-10-13: the example profiles' documents reached 204.
MAX_ENTRY = 140


def short_example_name(profile_folder: str, name: str) -> str:
    """A profile's document without the profile's name repeated in front of it: in
    profile-df-qss-.../input, profiledf-qss-..._w2_1.pdf is w2_1.pdf (the folder already says
    whose it is). A name without that prefix is kept."""
    prefix = profile_folder.replace("profile-", "profile", 1) + "_"
    return name[len(prefix):] if name.startswith(prefix) and len(name) > len(prefix) else name


def copy_examples(src: Path, dest: Path) -> None:
    """The examples, as the release carries them, with each profile's documents named short."""
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("alpha-*", "README.md"))
    for folder in sorted(p for p in (dest / "profiles").iterdir() if p.is_dir()):
        for doc in sorted(p for p in folder.rglob("*") if p.is_file()):
            short = doc.with_name(short_example_name(folder.name, doc.name))
            if short != doc:
                if short.exists():
                    raise Stop(f"examples: {short.relative_to(dest)} would be two documents")
                doc.rename(short)


def check_entry_lengths(stage: Path) -> None:
    too_long = sorted(p.relative_to(stage).as_posix() for p in stage.rglob("*")
                      if len(p.relative_to(stage).as_posix()) > MAX_ENTRY)
    if too_long:
        raise Stop(f"{len(too_long)} paths in the package are over {MAX_ENTRY} characters, which Windows "
                   "may refuse to extract: " + ", ".join(too_long[:5]))


def zip_name(version: str, plat: str) -> str:
    return f"{APP}-{version}-{plat}.zip"


def readme(plat: str, version: str, examples: bool) -> str:
    text = (HERE / f"README-FIRST-{'windows' if plat == 'windows-x64' else 'macos'}.txt").read_text(encoding="utf-8")
    # the title's underline is as long as the title once the label is in it
    title, rule, rest = text.split("\n", 2)
    title = title.replace("{version}", version)
    text = "\n".join([title, rule[0] * len(title), rest])
    if not examples:
        lines = text.split("\n")
        start = next(i for i, l in enumerate(lines) if "made-up households" in l)
        del lines[start:start + 2]
        text = "\n".join(lines)
    return text.replace("{version}", version)


def write_zip(root: Path, dest: Path, epoch: int) -> None:
    """Every entry under `root`, sorted, dated SOURCE_DATE_EPOCH, with fixed permissions; symlinks
    are stored as symlinks (macOS keeps them on unzip)."""
    import time
    stamp = time.gmtime(max(epoch, 315532800))[:6]
    entries = sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix())
    with zipfile.ZipFile(dest, "w") as z:
        for path in entries:
            name = path.relative_to(root).as_posix()
            if path.is_symlink():
                info = zipfile.ZipInfo(name, stamp)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o755) << 16
                z.writestr(info, os.readlink(path), compress_type=zipfile.ZIP_STORED)
            elif path.is_dir():
                info = zipfile.ZipInfo(name + "/", stamp)
                info.create_system = 3
                info.external_attr = (stat.S_IFDIR | 0o755) << 16
                z.writestr(info, b"")
            else:
                executable = bool(path.stat().st_mode & 0o111) or path.suffix.lower() in (".exe", ".dll")
                info = zipfile.ZipInfo(name, stamp)
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, path.read_bytes(), compresslevel=9)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--release-root", type=Path, default=PREP.parent)
    ap.add_argument("--out", type=Path, default=Path.cwd() / "ytax-prep-package")
    ap.add_argument("--any-python", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--requirements", type=Path, help=argparse.SUPPRESS)   # a local test build only
    ap.add_argument("--prebuilt-engine", type=Path, help=argparse.SUPPRESS)  # a local test build only
    args = ap.parse_args(argv)
    try:
        if not VERSION_LABEL.fullmatch(args.version):
            raise Stop(f"--version {args.version!r}: letters, digits, '.', '+' and '-' only (alpha-0.1.0)")
        global REQUIREMENTS_OVERRIDE
        REQUIREMENTS_OVERRIDE = args.requirements
        plat = target()
        pins = load_pins()
        check_python(pins, plat, args.any_python)
        epoch = int(os.environ.get("SOURCE_DATE_EPOCH") or pins["source_date_epoch_default"])
        rel = check_release(args.release_root.resolve())
        out = args.out.resolve()
        work, cache, stage = out / "work", out / "cache", out / "stage"
        for d in (work, stage):
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True)

        engine_home = work / "engine-home"
        stage_engine_home(rel, engine_home, cache, pins)
        if args.prebuilt_engine:
            # a local test: the engine's JavaScript (the same bytes on every platform) from an
            # earlier build of this script
            shutil.copytree(args.prebuilt_engine / "js-engine", engine_home / "js-engine")
            shutil.copyfile(rel["js"] / "engine" / "factgraph.libraries.tsv", work / "engine-libraries.tsv")
        else:
            build_js_engine(rel, work, engine_home)
        node = stage_node(plat, pins, cache, work, work / "node")

        if plat == "macos-universal":
            arm = freeze(plat, work, args.version, "arm64", epoch)
            x86 = freeze(plat, work, args.version, "x86_64", epoch)
            app = stage / f"{APP}.app"
            fuse_universal(arm, x86, app)
            tags = [f"{plat}-arm64", f"{plat}-x86_64"]
        else:
            frozen = freeze(plat, work, args.version, None, epoch)
            app = stage
            shutil.copytree(frozen, stage, dirs_exist_ok=True, symlinks=True)
            tags = [plat]

        # an installer's file list (it records each installed console script, whose first line
        # names the build environment's Python): not something the application reads
        for record in sorted(stage.rglob("*.dist-info/RECORD")):
            record.unlink()
        components = notices_for(plat, work, tags, node, pins, rel["third-party"])
        from notices import write_notices
        notices = work / "THIRD-PARTY-NOTICES.txt"
        write_notices(notices, components,
                      f"Third-party software in ytax-prep {args.version} ({plat}).\n"
                      "ytax-prep itself is licensed under the PolyForm Strict License 1.0.0 "
                      "(LICENSE, LICENSING.md and legal/ in the About folder).")
        code, data = resource_dirs(plat, app)
        add_data(code, data, "engine-home", engine_home)
        shutil.copytree(work / "node", code / "node")
        about = work / "about"
        about_folder(rel, about, args.version, notices)
        add_data(code, data, "about", about)
        shutil.copyfile(notices, stage / "THIRD-PARTY-NOTICES.txt")
        examples = PREP / "examples"
        has_examples = (examples / "profiles").is_dir()
        if has_examples:
            copy_examples(examples, stage / "examples")
        (stage / "README-FIRST.txt").write_text(readme(plat, args.version, has_examples), encoding="utf-8",
                                                newline="\r\n" if plat == "windows-x64" else "\n")
        if plat == "macos-universal":
            run(["codesign", "--force", "--sign", "-", code / "node" / "node"])
            run(["codesign", "--force", "--deep", "--sign", "-", app])
            run(["codesign", "--verify", "--deep", "--strict", app])
        name = zip_name(args.version, plat)
        if plat == "windows-x64":         # macOS has no such limit, and its app nests deeper
            check_entry_lengths(stage)
        write_zip(stage, out / name, epoch)
        say(f"wrote {out / name} ({(out / name).stat().st_size:,} bytes, sha256 {sha256(out / name)})")
        return 0
    except Stop as why:
        print(f"[package] STOPPED: {why}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    sys.exit(main())
