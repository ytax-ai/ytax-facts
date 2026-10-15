# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""One long-lived engine process instead of one per calculation.

Measured at the pin: **2.90 s** per calculation forking a JVM versus
**~0.1 s marginal** through a warm `--batch` child — about 29×, nearly all of the cold cost being
JVM start plus dictionary load. This is the wrapper that measurement called for.

**The acceptance bar is determinism, not speed.** A faster engine that answers differently is
worthless, so `tests/test_warm_engine.py` asserts the warm answer is byte-identical to the cold one
before it asserts anything else.

WHY PROCESS-SERIALISED, and why that is not a limitation to route around: the runner builds a fresh
`Graph` per resolve over an immutable dictionary, so nothing leaks between scenarios — but its
`dictCache` is an unsynchronised `mutable.Map` whose `getOrElseUpdate` races on concurrent first
touch. That **selects** one calculation at a time per process, scaled by running more processes.
Threading is a question for the build repo, not something to paper over here.

THREE HAZARDS, each read from the runner at the pin:

1. **`sys.exit(2)` on any malformed stdin line** — one bad command kills the process serving every
   queued request, so commands are validated BEFORE they are written.
2. **The frame is a progress line, not a designed token.** A command ends when the runner prints
   `[runner] Done. N scenarios.`; if a pin bump reworded it this wrapper would HANG rather than
   fail, which is why the string is pinned and tested against the real runner.
3. **The child dies.** An in-flight request fails as `EngineNotAvailable` — retryable, which is what
   `ENGINE_UNAVAILABLE` means to a caller — and the next request silently gets a fresh process.

Nothing here relaxes the child environment: `child_env()`'s allowlist applies unchanged, and a
LONG-LIVED child makes it matter more, not less — it would hold the customer API-key list for the
lifetime of the service rather than for one fork.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from .adapter import EngineNotAvailable, child_env, child_window, discover_pin
from .workspace import work_root

# The line the runner prints at the end of every command (`processDir`'s last `println`). Pinned
# because it is a HUMAN-READABLE progress message doing protocol work: reword it and this wrapper
# waits forever. `tests/test_warm_engine.py` checks it against the real runner.
DONE_FRAME = "[runner] Done."

# A command is three TAB-separated fields on one line. These two characters are structural, so a
# path containing either is not a bad request — it is a fatal one.
_FORBIDDEN = ("\t", "\n", "\r")


def _validate_command(dict_dir: str, scen_dir: str, golden_dir: str) -> str:
    """Build the stdin line, or refuse. Called BEFORE anything is written.

    The runner's response to a malformed line is `sys.exit(2)`, which takes down the process serving
    every queued request. That makes validation here a availability control, not tidiness."""
    fields = (str(dict_dir), str(scen_dir), str(golden_dir))
    for name, value in zip(("dictionary", "scenario", "golden"), fields):
        if not value:
            raise EngineNotAvailable(
                f"refusing to send an empty {name} path to the engine: the runner exits 2 on a "
                f"malformed command, which would kill every other request in flight")
        for bad in _FORBIDDEN:
            if bad in value:
                label = {"\t": "tab", "\n": "newline", "\r": "carriage return"}[bad]
                raise EngineNotAvailable(
                    f"refusing to send the {name} path to the engine: it contains a {label}, which "
                    f"is the command separator. The runner would read a malformed line and exit 2, "
                    f"killing every other request in flight.")
    return "\t".join(fields)


class WarmEngine:
    """A resident `--batch` child, one calculation at a time.

    Interface-compatible with `EngineAdapter.resolve_facts` on purpose: the service should be able
    to adopt it without learning a second vocabulary, and the two must stay comparable so the
    byte-identical test keeps meaning something.
    """

    def __init__(self, pin=None, timeout: float = 300.0):
        self.pin = pin or discover_pin()
        self.timeout = timeout
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()      # serialised per process; see the module docstring
        self.last_frame_lines: list[str] = []

    # ---- process lifecycle -------------------------------------------------------------------

    @property
    def pid(self):
        return self._proc.pid if self._proc and self._proc.poll() is None else None

    def _start(self) -> subprocess.Popen:
        # stderr is merged into stdout deliberately. Two reasons: an undrained stderr pipe fills and
        # DEADLOCKS a long-lived child, and the framing line is on stdout anyway. Engine diagnostics
        # are never served to a caller, so interleaving costs nothing.
        try:
            self._proc = subprocess.Popen(
                [*self.pin.command, "--batch"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                cwd=str(self.pin.home), env=child_env(str(self.pin.home), self.pin.runner_today),
                text=True, bufsize=1, **child_window())
        except OSError as e:
            raise EngineNotAvailable(f"could not start the engine: {e}")
        return self._proc

    def _live(self) -> subprocess.Popen:
        if self._proc is None or self._proc.poll() is not None:
            return self._start()
        return self._proc

    def close(self) -> None:
        """Shut the child down. Closing stdin ends its read loop; it is killed if it does not go."""
        proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
            proc.wait(timeout=10)

    def kill_for_test(self) -> None:
        """Kill the child outright, to exercise the recovery path. Named so it cannot be mistaken
        for part of the interface: a death test that never kills anything proves nothing."""
        if self._proc and self._proc.poll() is None:
            self._proc.kill()
            self._proc.wait(timeout=10)

    # ---- one calculation ---------------------------------------------------------------------

    def resolve_facts(self, engine_facts: dict) -> str:
        """Resolve an in-memory persister fact set and return the resolved-facts TSV verbatim.

        Byte-identical to `EngineAdapter.resolve_facts` — same temp scenario dir, same empty golden
        dir, same emitted file read back. Only the JVM's lifetime differs."""
        with self._lock:
            # Under the service's ONE work root: a resident process that is OOM-killed
            # mid-calculation leaves this behind, and the next start is what removes it.
            tmp = tempfile.mkdtemp(prefix="warm-", dir=str(work_root()))
            try:
                scen_dir = Path(tmp) / "scen"
                golden_dir = Path(tmp) / "golden"   # empty -> the runner EMITS the resolved facts
                scen_dir.mkdir()
                golden_dir.mkdir()
                (scen_dir / "return.json").write_text(json.dumps(engine_facts))
                # as they are, a drive letter included (EngineAdapter._run says why)
                command = _validate_command(str(self.pin.dict_dir), str(scen_dir), str(golden_dir))

                proc = self._live()
                self._send(proc, command)
                self._read_until_frame(proc)

                emitted = golden_dir / "return.tsv"
                if not emitted.is_file():
                    # The child answered but produced nothing. Treat the process as suspect rather
                    # than retry into it: whatever state it is in, it is not one we can reason about.
                    self.close()
                    raise EngineNotAvailable(
                        "the engine finished a command without emitting resolved facts")
                return emitted.read_text(encoding="utf-8")
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

    def _send(self, proc: subprocess.Popen, command: str) -> None:
        try:
            proc.stdin.write(command + "\n")
            proc.stdin.flush()
        except (BrokenPipeError, ValueError, OSError) as e:
            self.close()
            raise EngineNotAvailable(
                f"the engine process was gone when the request was written ({e}). This is "
                f"retryable: the next request starts a fresh one.")

    def _read_until_frame(self, proc: subprocess.Popen) -> None:
        """Read the child's output until this command's terminal line.

        A dead child returns EOF here rather than the frame, which is the difference between a
        retryable failure and a hang — so EOF is checked explicitly instead of read in a loop that
        assumes the line arrives."""
        deadline = threading.Event()
        timer = threading.Timer(self.timeout, deadline.set)
        timer.start()
        lines: list[str] = []
        try:
            while True:
                if deadline.is_set():
                    self.close()
                    raise EngineNotAvailable(
                        f"the engine did not finish within {self.timeout:.0f}s; the process was "
                        f"replaced rather than left in an unknown state")
                line = proc.stdout.readline()
                if line == "":                      # EOF: the child died mid-command
                    self.close()
                    raise EngineNotAvailable(
                        "the engine process ended without answering. This is retryable: the next "
                        "request starts a fresh one.")
                lines.append(line.rstrip("\n"))
                if DONE_FRAME in line:
                    return
        finally:
            timer.cancel()
            self.last_frame_lines = lines
