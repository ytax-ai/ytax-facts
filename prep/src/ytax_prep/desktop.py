# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The packaged application's entry: `ytax-prep.exe` on Windows, `ytax-prep.app` on macOS.

Double-clicked, it starts the local page's server on 127.0.0.1, opens the page in the person's
browser, and serves until the page's Quit. There is no window and no terminal. A second
double-click while it runs opens the running page again instead of starting another copy.

Where things are:
  - the program: the unzipped folder, read only. The bundled Node.js runtime, the engine (compiled
    to JavaScript) and its dictionary, the blank IRS forms and the license documents sit inside it
    (`bundle_layout`).
  - the person's data: only the working folder they choose on the page, asked every time the
    program starts (one folder per return, so one per client), never a folder of the program's
    own: its input/ (the documents and the saved answers), output/ (the filled forms and the
    workbook) and temp/ (the engine's working files, removed after each calculation, and a log,
    ytax-prep.log). The page suggests Documents/ytax-prep and creates nothing until a folder is
    confirmed.
  - one file outside it: the address of the copy that is running (ytax-prep-running.json in the
    system's temporary folder), so a second double-click finds it before any folder is chosen.

Once running it connects to nothing but this computer: every socket connection to an address
other than a loopback one is refused (`refuse_outside_connections`), so no part of the program,
and no library it carries, can reach the network.
"""
from __future__ import annotations

import ipaddress
import json
import os
import socket
import sys
import tempfile
import urllib.request
import webbrowser
from pathlib import Path

APP = "ytax-prep"


# ---- where things are ------------------------------------------------------------------------

def documents_folder() -> Path:
    """The person's Documents folder: on Windows the one Windows itself names (it may be moved,
    to OneDrive for one), elsewhere ~/Documents."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD),
                            ("d", ctypes.c_ubyte * 8)]
            # FOLDERID_Documents {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
            documents = GUID(0xFDD39AD0, 0x238F, 0x46AF, (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
            out = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(documents), 0, None, ctypes.byref(out)) == 0:
                try:
                    return Path(out.value)
                finally:
                    ctypes.windll.ole32.CoTaskMemFree(out)
        except (OSError, AttributeError, ValueError):
            pass
    return Path.home() / "Documents"


def suggested_folder() -> Path:
    """What the page suggests as the working folder; nothing is created until one is confirmed."""
    return documents_folder() / APP


def bundle_layout(root: Path) -> dict:
    """The packaged resources under `root` (the frozen app's resource folder). The Node.js
    runtime the engine runs on is one executable (a universal one on macOS)."""
    node = root / "node" / ("node.exe" if sys.platform == "win32" else "node")
    return {"engine_home": root / "engine-home", "node_dir": node.parent, "node": node,
            "about": root / "about", "examples": root / "examples"}


def resource_root() -> Path:
    """The frozen app's resource folder (PyInstaller's), or the repository when run from source."""
    frozen = getattr(sys, "_MEIPASS", None)
    return Path(frozen) if frozen else Path(__file__).resolve().parents[2]


# ---- local only --------------------------------------------------------------------------------

def _is_local(address) -> bool:
    if isinstance(address, (str, bytes)) and not isinstance(address, tuple):
        return True                                   # an AF_UNIX path: this computer
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, bytes):
        host = host.decode()
    if host in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False                                  # a name: never resolved, never reached


def refuse_outside_connections() -> None:
    """Every socket connection to a non-loopback address fails with an OSError naming it.
    Installed once, before anything else runs."""
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def connect(self, address):
        if not _is_local(address):
            raise OSError(f"{APP} connects to nothing outside this computer (refused: {address!r})")
        return original_connect(self, address)

    def connect_ex(self, address):
        if not _is_local(address):
            raise OSError(f"{APP} connects to nothing outside this computer (refused: {address!r})")
        return original_connect_ex(self, address)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex


# ---- the working folder -----------------------------------------------------------------------

_log_folder: Path | None = None       # the confirmed working folder's temp/, once there is one


def use_working_folder(folder) -> None:
    """The person confirmed `folder` on the page: the engine's working files and the log go into
    its temp/ from now on, and working files a crashed run left there are removed."""
    global _log_folder
    temp = Path(folder) / "temp"
    temp.mkdir(parents=True, exist_ok=True)
    from .engine.workspace import WORK_ROOT_ENV, sweep
    os.environ[WORK_ROOT_ENV] = str(temp)
    sweep()
    _log_folder = temp
    _log(f"{APP} working in {folder}")


def arm_environment(layout: dict) -> None:
    """The engine, the Node.js runtime and the About documents, for this run."""
    os.environ["YTAX_ENGINE_HOME"] = str(layout["engine_home"])
    os.environ["YTAX_NODE"] = str(layout["node"])
    os.environ["PATH"] = str(layout["node_dir"]) + os.pathsep + os.environ.get("PATH", "")
    os.environ["YTAX_ABOUT_DIR"] = str(layout["about"])
    os.environ.setdefault("YTAX_SHOWCASE_PROFILES", str(layout["examples"] / "profiles"))


# ---- one copy at a time ----------------------------------------------------------------------

def _running_path() -> Path:
    return Path(tempfile.gettempdir()) / f"{APP}-running.json"


def running_page() -> str | None:
    """The page of a copy that is already serving, or None."""
    try:
        url = json.loads(_running_path().read_text(encoding="utf-8"))["url"]
    except (OSError, ValueError, KeyError):
        return None
    try:
        state = url.replace("/?t=", "/api/state?t=")
        with urllib.request.urlopen(state, timeout=2) as answer:
            return url if answer.status == 200 else None
    except OSError:
        return None


def _log(text: str) -> None:
    """A line in the working folder's temp/ytax-prep.log; before a folder is chosen, nowhere."""
    if _log_folder is None:
        return
    try:
        with open(_log_folder / "ytax-prep.log", "a", encoding="utf-8") as log:
            log.write(text.rstrip() + "\n")
    except OSError:
        pass


# One synthetic return (tests/fixtures/contract/wages-single-mid): $52,000 of wages, $5,400 withheld.
SELF_TEST_FACTS = {
    "filing_status": "single", "residence_state": "il", "received_alaska_pfd": False,
    "received_digital_assets": False, "disposed_digital_assets": False,
    "foreign_financial_account": False, "foreign_trust_grantor": False,
    "foreign_trust_transactions": False, "eitc_reduced_or_disallowed": False,
    "ctc_odc_reduced_or_disallowed": False, "qualifying_child_of_another": False,
    "paid_estimated_taxes": False, "paid_student_loan_interest": False,
    "persons": [{"role": "primary", "birth_year": 1990, "birth_month": 6,
                 "tin_type": "ssn_valid_for_employment", "is_blind": False, "k12_educator": False,
                 "made_ira_contributions": False, "someone_can_claim_you": False,
                 "made_hsa_contributions": False}],
    "w2s": [{"person": 0, "wages_cents": 5200000, "withholding_cents": 540000,
             "statutory_employee": False, "retirement_plan": False, "third_party_sick_pay": False,
             "has_rrta_codes": False}],
}
SELF_TEST_EXPECTED_CENTS = {"24": 411500, "34": 128500}   # Form 1040 lines 24 and 34


def self_test(out_path: Path) -> int:
    """Compute one synthetic return through the packaged runtimes and engine, with no window and no
    browser, and check the About folder's documents, and write what happened to `out_path` (JSON).
    Exit 0 only when the engine is the pinned one, the lines are the expected ones, and every
    relative link in the About folder's documents resolves inside it."""
    result = {"app": APP, "python": sys.version.split()[0], "ok": False}
    from .intake.server import ABOUT_DIR_ENV, about_broken_links, about_documents
    about = Path(os.environ.get(ABOUT_DIR_ENV) or "")
    if os.environ.get(ABOUT_DIR_ENV) and about.is_dir():
        result["about_documents"] = len(about_documents(about))
        result["about_broken_links"] = about_broken_links(about)
    else:
        result["about_broken_links"] = [f"no About folder ({ABOUT_DIR_ENV})"]
    ops = None
    try:
        from .engine.adapter import discover_pin
        from .service.operations import Operations
        pin = discover_pin()
        result.update(engine_kind="js", matches_pin=pin.matches_pin)
        ops = Operations()
        served = ops.calculate_return({"tax_year": 2025, "facts": SELF_TEST_FACTS})
        lines = {row["line_id"]: row["value_cents"] for form in served["result"]["forms"]
                 if form["form_id"] == "1040" for row in form["lines"]}
        result["lines"] = {k: lines.get(k) for k in SELF_TEST_EXPECTED_CENTS}
        result["ok"] = (bool(pin.matches_pin) and result["lines"] == SELF_TEST_EXPECTED_CENTS
                        and not result["about_broken_links"])
    except Exception as why:                       # reported, never raised: there is no console
        result["error"] = f"{type(why).__name__}: {why}"
        # why, not only what: the served message ("the calculation engine is unavailable") says
        # nothing a fix can start from; the diagnostic and the engine's own last lines do. The
        # return is the synthetic one above, so nothing here is a person's data.
        if getattr(why, "detail", None):
            result["detail"] = why.detail
        lines = getattr(getattr(ops, "_adapter", None), "last_frame_lines", None)
        if lines:
            result["engine_output"] = list(lines[-20:])
    Path(out_path).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if result["ok"] else 1


def main(argv=None) -> int:
    refuse_outside_connections()
    argv = list(sys.argv[1:] if argv is None else argv)
    root = resource_root()
    layout = bundle_layout(root)
    version_file = layout["about"] / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else "source"
    if argv[:1] == ["--version"]:
        print(f"{APP} {version}")
        return 0
    arm_environment(layout)
    if argv[:1] == ["--self-test"] and len(argv) == 2:
        return self_test(Path(argv[1]))
    already = running_page()
    if already:
        webbrowser.open(already)
        return 0
    from .intake.server import make_server
    # every start asks where to work (one folder per return): nothing is remembered between runs
    server, url = make_server(suggested_folder(), on_folder=use_working_folder, ask_first=True,
                              stop_when_page_closed=True)
    _running_path().write_text(json.dumps({"url": url}), encoding="utf-8")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        try:
            _running_path().unlink()
        except OSError:
            pass
        reason = getattr(server, "stop_reason", None)
        _log(f"{APP} {version} stopped" + (f": {reason}" if reason else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
