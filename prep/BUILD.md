# Building ytax-prep

`ytax-prep` is the application for estimating federal tax and preparing the IRS forms for a 2025
return. It runs on the person's own computer, on the calculation engine and fact dictionary in the
rest of this repository; nothing about a return leaves that computer.

## Packages

This release is source: build the package for your computer as described below. Ready-made
packages will be offered on this repository's Releases page in a later release. The build writes

- `ytax-prep-<version>-windows-x64.zip` — Windows 10 or 11, 64-bit
- `ytax-prep-<version>-macos-universal.zip` — macOS 11 or later, Apple silicon and Intel (not yet
  tested on a Mac; its `README-FIRST.txt` says so)

Each zip carries everything the application needs (Python, Node.js, the engine and its
dictionary, the blank IRS forms); nothing else is installed. Unzip it and follow the
`README-FIRST.txt` inside. The source of the Node.js and Python runtimes it carries is linked from
`THIRD-PARTY-NOTICES.txt` inside the zip.

## Build the package yourself

`prep/packaging/build_package.py` builds the same zip from the files in this repository. Run it
on the platform you are building for (Windows x64, or macOS for the universal package), from the
repository root:

```
python prep/packaging/build_package.py --version <version> --out <folder>
```

It needs, on the build machine only (none of these goes into the package):

- **Python 3.13.16** (`prep/packaging/pins.json`); on macOS, python.org's universal2 build, and
  Rosetta 2 on Apple silicon, because the universal app is built once per processor;
- **Node.js and npm**, to run the engine's dictionary generator (`js/`, from `js/package-lock.json`);
- network access to download what the build pins by SHA-256: Node.js 24.21.0 (`pins.json`), the
  Python packages and PyInstaller (`prep/packaging/requirements-*.txt`), the blank IRS forms the
  application prints (`prep/generated/irs_blank_forms.json`), and the dictionary generator's
  dependencies (pinned by `js/package-lock.json`).

No JDK and no sbt: the engine comes already compiled to JavaScript, as `js/engine/factgraph.js`.
The build checks its SHA-256 against the application's engine pin and stops if it differs, and
checks the libraries listed in `js/engine/factgraph.libraries.tsv` against the reviewed licenses
in `prep/packaging/engine-licenses.json`.

What it does: generates the engine's dictionary from `dictionary/ty2025`; bundles the engine
runner (`prep/src/ytax_prep/engine/js/runner.mjs`) with `js/engine/factgraph.js`;
fetches Node.js and the blank forms; freezes the application with PyInstaller in a hash-checked
environment; adds the license documents and the generated `THIRD-PARTY-NOTICES.txt`; and writes
the zip. Two runs on the same platform give the same zip, byte for byte (`SOURCE_DATE_EPOCH`
dates every entry). The build stops, naming the component, if a bundled component's license is
copyleft and not listed as approved in `pins.json`.

## Run from the source files

With the package built once, its staged engine can be used directly:

```
cd prep
bash collector/setup.sh                      # a virtual environment with the reader's packages
export YTAX_ENGINE_HOME=<folder>/work/engine-home YTAX_ENGINE_KIND=js
PYTHONPATH=src:collector collector/.venv/bin/python -m ytax_prep.desktop    # opens the page
```

## Checks that run without the development harness

- The package build checks that `dictionary/ty2025` is the dictionary the application is pinned
  to, that the engine's generated dictionary was made from it, that every download matches its
  pinned hash, and that every bundled component has its license text in the notices.
- `scripts/client.py --example NAME`, with `YTAX_ENGINE_HOME` and `YTAX_ENGINE_KIND=js` set as
  above, computes one bundled synthetic return from `tests/fixtures/contract/NAME.facts.json`;
  its expected lines are in `NAME.expected.json`.
- The application's test suites are not part of this release; they stay in its development
  repository.
