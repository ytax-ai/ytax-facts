# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The engine adapter — one subprocess wrapper over the PINNED ytax engine.

Contract: the engine is a pinned artifact reached via the
``YTAX_ENGINE_HOME`` environment variable, which points at an engine home staged from the release
AT THE PIN. This module NEVER copies engine source, the dictionary, or scenario data into this
repo — it runs the engine compiled to JavaScript, on Node.js, as a subprocess and reads back the
resolved facts.

The engine's runner resolves a directory of fact-graph *persister-format* scenarios against the
dictionary and, per scenario, WRITES ``<goldenDir>/<name>.tsv`` when that golden is absent (else it
diffs). ``resolve()`` exploits the write path: it points the golden dir at a fresh temp dir so the
runner EMITS the resolved facts, then reads them back verbatim.

Determinism is held by ``RUNNER_TODAY`` (default the pinned 2026-06-13); same input ⇒ byte-identical
resolved facts, which is what makes the service's provenance contract (same input_hash ⇒ identical
bytes) possible downstream.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# The pin: the engine repository's commit these bytes came from (a label) and, below, the hashes
# the code checks against. Bumping the pin is its own reviewed change.
PINNED_COMMIT = "4cdc717ac1d86d9d2daa51894bb4607dfe85f10b"
PINNED_DESCRIBE = "alpha-1-2"

# THE PIN IS THE PAIR, AND IT IS CONTENT — not a commit.

# All tax logic lives in `dictionary/ty2025/**`, loaded at RUNTIME. Pin only the engine and you
# have pinned nothing about computed values — a dictionary change would move every fixture with the
# engine hash unchanged, which is the worst failure shape there is for cent-exact verification.

# And a COMMIT check is not enough either: `head_commit` passes for a checkout sitting at the right
# commit with a dirty tree. Measured — the live build checkout's dictionary differs from the one at
# its own recorded commit. So the commit below is a LABEL (which commit produced these
# bytes) and these two hashes are the CHECK.
PINNED_DICTIONARY_SHA256 = (
    "sha256:d825b1e6616aedb1ba6146508bc895f62189f70bcacf52f2b45479f1dcc2be79")
# The engine compiled to JavaScript, as the engine's build links and commits it
# (js/engine/factgraph.js). The packaged application runs this, on Node.js; the Scala.js link is not
# byte-stable, so the linked file itself is pinned, not the source it came from.
PINNED_FACTGRAPH_SHA256 = "538a7e2530397bbb2139e396e990b8c8727ca34efc7e7dcf1d6ad26c7cf10d1d"
RUNNER_TODAY = "2026-06-13"

# How long one engine invocation may take. Named rather than inline because the crash-residue
# sweep (engine/workspace.py) derives its age threshold from it: anything still running has by
# definition not exceeded this, which is what separates live work from a dead process's leftovers.
SUBPROCESS_TIMEOUT_SECONDS = 300
# The engine on JavaScript, as the packaged application carries it: the runner bundled with the
# engine compiled to JavaScript (src/ytax_prep/engine/js/runner.mjs), the dictionary generated from
# dictionary/ty2025 beside it, and a record of which dictionary it was generated from.
JS_RUNNER_RELPATH = "js-engine/bin/runner.mjs"
JS_BUILT_FROM_RELPATH = "js-engine/BUILT-FROM.json"
NODE_ENV = "YTAX_NODE"                   # the node executable to run the JS engine with
DICT_RELPATH = "dictionary/ty2025"
ENGINE_HOME_ENV = "YTAX_ENGINE_HOME"


# what the engine's child process is allowed to see. An ALLOWLIST, not a denylist — this process holds the
# customer API-key list in YTAX_API_KEYS (Secret Manager -> env), and handing the child
# `dict(os.environ)` put every customer's credential in every calculation's process environment,
# readable from /proc/<pid>/environ or a crash report. A denylist would leak the
# next secret someone adds; only names the runner actually needs pass.
# PATH, HOME and LANG everywhere; on Windows also the system folders, without which the engine's
# runtime does not start (measured: node.exe exits 134 with no SYSTEMROOT). Folder names, no secrets.
CHILD_ENV_PASSTHROUGH = ("PATH", "HOME", "LANG", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")


def child_env(repo_root: str, runner_today: str) -> dict:
    """The complete environment handed to the pinned runner. Nothing inherited implicitly."""
    env = {k: os.environ[k] for k in CHILD_ENV_PASSTHROUGH if k in os.environ}
    env["RUNNER_TODAY"] = runner_today
    env["REPO_ROOT"] = repo_root
    return env


def child_window() -> dict:
    """Keyword arguments that keep an engine child off the desktop. A windowed process —
    `yTax.exe` — has no console, so Windows allocates a fresh one for every console-subsystem
    child it starts; the warm engine is long-lived, so that window stayed for the life of the
    app. Nothing is passed on other platforms; the interview's own console (`CREATE_NEW_CONSOLE`
    in the window) is intentional and not made here."""
    if sys.platform == "win32":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {}


def dictionary_sha256(dict_dir) -> str:
    """Content hash of a dictionary tree: every file's relative path and bytes, in sorted order.

    ONE implementation, deliberately. This same value is served as `dictionary_hash` provenance in
    every response envelope (`service/operations.py`) AND is what the pin check enforces — if the
    two computed it differently, the number a caller verifies against would not be the number the
    pin protects. os.walk (not listdir) because nested dictionary content must be covered, or a
    change there would leave the hash unchanged."""
    import hashlib
    h = hashlib.sha256()
    dd = str(dict_dir)
    for root, _dirs, files in sorted(os.walk(dd)):
        for name in sorted(files):
            p = os.path.join(root, name)
            with open(p, "rb") as f:
                # The relative path with FORWARD slashes whatever the OS: on Windows `os.sep` is a
                # backslash, and hashing it made the same bytes a different dictionary — the pin
                # check failed on a byte-identical copy. On POSIX this changes nothing.
                h.update(os.path.relpath(p, dd).replace(os.sep, "/").encode())
                h.update(f.read())
    return "sha256:" + h.hexdigest()


def file_sha256(path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class EngineNotAvailable(RuntimeError):
    """Raised when no pinned engine is reachable (env unset, or runner/dict missing). Callers that must
    stay green without an engine (CI, contract tests) catch this and skip."""


@dataclass(frozen=True)
class EnginePin:
    """A resolved, on-disk engine artifact at ``home`` (validated to have the runner + dict)."""

    home: Path
    dict_dir: Path
    js_runner: Path
    runner_today: str = RUNNER_TODAY

    @property
    def command(self) -> list[str]:
        """The engine runner's command line, before its own arguments: the packaged application
        names its own Node.js (YTAX_NODE); otherwise the one on PATH."""
        return [os.environ.get(NODE_ENV) or "node", str(self.js_runner)]

    @property
    def head_commit(self) -> str | None:
        """The engine checkout's current HEAD (best-effort), so a caller can warn on pin drift.
        Returns None if ``home`` is not a git checkout."""
        try:
            out = subprocess.run(
                ["git", "-C", str(self.home), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=10, **child_window())
            return out.stdout.strip() or None if out.returncode == 0 else None
        except Exception:
            return None

    @property
    def dictionary_hash(self) -> str:
        return dictionary_sha256(self.dict_dir)

    @property
    def matches_pin(self) -> bool:
        """True only when the BYTES are the pinned ones. Deliberately not a commit comparison: a
        dirty checkout at the right commit serves different content and would pass that."""
        try:
            if self.dictionary_hash != PINNED_DICTIONARY_SHA256:
                return False
            # the generated dictionary the runner resolves against was made from these bytes, and
            # the runner was bundled with the pinned engine
            built = json.loads((self.home / JS_BUILT_FROM_RELPATH).read_text(encoding="utf-8"))
            return (built.get("dictionary_sha256") == PINNED_DICTIONARY_SHA256
                    and built.get("factgraph_sha256") == PINNED_FACTGRAPH_SHA256)
        except (OSError, ValueError):
            return False

    @property
    def matches_pin_commit(self) -> bool:
        """The LABEL check, kept separate: which commit the checkout is on. Useful for a warning;
        never sufficient on its own (see matches_pin)."""
        return self.head_commit == PINNED_COMMIT


def discover_pin(engine_home: str | os.PathLike | None = None) -> EnginePin:
    """Locate the pinned engine artifact. ``engine_home`` overrides the ``YTAX_ENGINE_HOME`` env.
    Raises EngineNotAvailable if the home, runner, or dictionary is missing."""
    home_str = str(engine_home) if engine_home is not None else os.environ.get(ENGINE_HOME_ENV, "")
    if not home_str:
        raise EngineNotAvailable(
            f"{ENGINE_HOME_ENV} is not set; point it at a build checkout at pin {PINNED_DESCRIBE}")
    home = Path(home_str).expanduser().resolve()
    dict_dir = home / DICT_RELPATH
    js_runner = home / JS_RUNNER_RELPATH
    if not js_runner.is_file():
        raise EngineNotAvailable(
            f"no engine runner at {js_runner} (stage the engine home: BUILD.md, 'Run from the "
            f"source files')")
    if not dict_dir.is_dir():
        raise EngineNotAvailable(f"dictionary not found at {dict_dir}")
    return EnginePin(home=home, dict_dir=dict_dir, js_runner=js_runner)


class EngineAdapter:
    """Thin subprocess adapter over the pinned engine. One instance = one pinned artifact."""

    def __init__(self, pin: EnginePin | None = None, *, engine_home: str | os.PathLike | None = None):
        self.pin = pin if pin is not None else discover_pin(engine_home)

    def _run(self, dict_dir: Path, scen_dir: Path, golden_dir: Path) -> subprocess.CompletedProcess:
        env = child_env(str(self.pin.home), self.pin.runner_today)
        home = str(self.pin.home)
        # cwd = the engine home, as the warm engine already runs. The paths go as they are, a drive
        # letter included: the runner (engine/js/runner.mjs) reads them with Node's fs and splits
        # nothing on ':' (the JVM runner did, and the application no longer runs it), so the working
        # folder may be on another drive than the application (seen 2026-10-13: unzipped on D:,
        # working files on C:).
        return subprocess.run(
            [*self.pin.command, str(dict_dir), str(scen_dir), str(golden_dir)],
            capture_output=True, text=True, env=env, cwd=home, timeout=SUBPROCESS_TIMEOUT_SECONDS,
            **child_window())

    @staticmethod
    def _workspace():
        # Local import: workspace.py reads SUBPROCESS_TIMEOUT_SECONDS from this module, so importing
        # it at module scope would be circular.
        from .workspace import workspace
        return workspace()

    def resolve_scenario_file(self, scenario_json: str | os.PathLike) -> str:
        """Resolve one persister-format scenario JSON file and return its resolved-facts TSV verbatim
        (the exact bytes the engine would write as a golden). Deterministic under the pin."""
        scenario_json = Path(scenario_json)
        if not scenario_json.is_file():
            raise FileNotFoundError(scenario_json)
        name = scenario_json.stem
        # Under the service's ONE work root, so a crash's residue is sweepable.
        with self._workspace() as tmp:
            scen_dir = Path(tmp) / "scen"
            golden_dir = Path(tmp) / "golden"      # empty -> runner EMITS the resolved facts here
            scen_dir.mkdir()
            golden_dir.mkdir()
            (scen_dir / f"{name}.json").write_bytes(scenario_json.read_bytes())
            proc = self._run(self.pin.dict_dir, scen_dir, golden_dir)
            # Write-mode over an empty golden dir: the runner emits and exits 0. A non-zero rc means
            # the engine hit an unexpected state (bad runner, load error) — never trust a stray file.
            if proc.returncode != 0:
                raise EngineNotAvailable(
                    f"engine exited {proc.returncode} resolving {name}. stderr:\n{proc.stderr}")
            emitted = golden_dir / f"{name}.tsv"
            if not emitted.is_file():
                raise EngineNotAvailable(
                    f"engine did not emit {name}.tsv (rc={proc.returncode}). stderr:\n{proc.stderr}")
            return emitted.read_text(encoding="utf-8")

    def resolve_facts(self, engine_facts: dict) -> str:
        """Resolve an in-memory persister fact set ({"facts": {...}}) and return the resolved-facts
        TSV verbatim. Same deterministic path as resolve_scenario_file (write to a temp scenario,
        empty golden dir, read back the emitted TSV)."""
        import json
        with self._workspace() as tmp:
            scen = Path(tmp) / "scen"
            scen.mkdir()
            p = scen / "return.json"
            p.write_text(json.dumps(engine_facts))
            return self.resolve_scenario_file(p)

    def reproduces_golden(self, scenario_json: str | os.PathLike,
                          golden_tsv: str | os.PathLike) -> bool:
        """True iff resolving ``scenario_json`` via the adapter reproduces ``golden_tsv`` byte-for-byte."""
        resolved = self.resolve_scenario_file(scenario_json)
        return resolved == Path(golden_tsv).read_text(encoding="utf-8")


# Convenience singleton-ish accessor for the pin metadata without requiring an on-disk engine.
PINNED = {
    "commit": PINNED_COMMIT,
    "describe": PINNED_DESCRIBE,
    "runner_today": RUNNER_TODAY,
    "js_runner_relpath": JS_RUNNER_RELPATH,
    "dict_relpath": DICT_RELPATH,
    "engine_home_env": ENGINE_HOME_ENV,
}
