# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The intake page's server: one page on this computer, over the intake loop.

Bound to 127.0.0.1 only. Every request needs the launch token — in the page's URL (`?t=`) or
the `X-Intake-Token` header the page's script sends — and a `Host` header naming exactly this
server, so no other page in the browser and no other process can drive it (a DNS-rebinding or
cross-site request carries the wrong Host or no token). Uploads are PDFs only, kept in the
working folder's `input\\`; filled forms go to `output\\`. Nothing is fetched from anywhere.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PAGE = Path(__file__).parent / "page"
STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/app.css": ("app.css", "text/css; charset=utf-8")}
MAX_UPLOAD = 20 * 1024 * 1024
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _dollars(cents) -> str:
    sign = "-" if cents < 0 else ""
    whole, part = divmod(abs(int(cents)), 100)
    return f"{sign}{whole:,}.{part:02d}"


_FACT_PATH = re.compile(r"^/\S+$")


def _sentence(boundary) -> str | None:
    """A boundary's words, or None when the boundary is a bare engine path (`/somePath`): a path is
    never shown to a person; a sentence always is."""
    if not isinstance(boundary, str) or not boundary.strip() or _FACT_PATH.match(boundary.strip()):
        return None
    return boundary


def _lint_words(lint: dict) -> str:
    checked, defects = lint.get("checked", 0), lint.get("defects", 0)
    if not checked:
        return "No filled form was checked."
    if not defects:
        return f"Every box that should be filled is filled ({checked} boxes checked)."
    return f"{defects} box(es) that should be filled are blank or wrong, of {checked} checked."


# What this page reads, why, and what else a person may receive. The first list is
# the reader's own table (served as `reads`); these two are the rest of the input-form universe
# build maintains (dictionary INPUT-FORMS-UNIVERSE.tsv, 53 forms IN), split by what the return
# carries. Typed in: the return carries the figures but no document reader exists yet.
TYPED_NOT_READ = ["SSA-1099 / RRB-1099 (Social Security benefits)", "1095-A (Marketplace coverage)"]
NOT_CARRIED = ["1098 (mortgage interest)", "1098-T and 1098-E (tuition, student loan interest paid)",
               "1099-B (broker sales)", "1099-NEC (nonemployee pay; Schedule C income is typed in)",
               "1099-K", "1099-Q and 1099-QA", "1099-S", "1099-C", "1099-PATR", "1099-LTC",
               "5498 and 5498-SA", "1095-B and 1095-C", "W-2c and the territorial W-2 forms", "1042-S",
               "Schedule K-1 (Form 8865) and Schedules K-3"]


def turn_json(turn) -> dict | None:
    if turn is None:
        return None
    out = {"id": turn.id, "kind": turn.kind, "path": turn.path, "ask": turn.ask, "why": turn.why,
           "choices": turn.choices, "optional": bool(getattr(turn, "optional", False))}
    if turn.choices:
        from ..client.interview import choice_words
        words = choice_words((turn.path or "").rsplit(".", 1)[-1]) or {}
        if not words and list(turn.choices) == ["false", "true"]:
            words = {"false": "No", "true": "Yes"}     # a yes-or-no question reads that way
        if not words and (turn.path or "").endswith("birth_month"):
            from .loop import MONTHS
            words = {str(n): MONTHS[n - 1] for n in range(1, 13)}
        # the dropdown shows words; the value it sends stays the code
        out["choice_labels"] = {c: words.get(c, c) for c in turn.choices}
    if turn.items:                         # a checklist page, ticked all at once
        out["items"] = [dict(item) for item in turn.items]
    if getattr(turn, "missing", None):     # the workbook wait: counted forms still empty, named
        out["missing"] = list(turn.missing)
    if turn.answers is not None:           # the summary, before the figures
        out["answers"] = [dict(a) for a in turn.answers]
    if turn.candidates:
        out["candidates"] = [{"path": c.path, "value": c.value, "caption": c.evidence.caption,
                              "document": c.evidence.document, "page": c.evidence.page,
                              "raw": c.evidence.raw, "tier": c.evidence.tier}
                             for c in turn.candidates]
    if turn.lines:
        out["lines"] = {k: _dollars(v) for k, v in turn.lines.items()}
    if turn.refusals:
        # WORDS, never the engine path. The page used to print `/hasForeignAccountsOrTrusts`
        # at a person who had no idea what it meant and no way back.
        # The EXACT reason, always. A coverage refusal carries the service's own
        # sentence under `boundary` (operations.prepare_return), which this used to skip — a
        # person read "outside what this service computes" for a return whose real reason was a
        # W-2 dropped twice. The bare line is the last resort, never the first.
        out["refusals"] = [r.get("words") or r.get("message") or _sentence(r.get("boundary"))
                           or r.get("detail") or "This return is outside what this service computes."
                           for r in turn.refusals]
    if getattr(turn, "computed_at", None):
        out["computed_at"] = turn.computed_at
    if getattr(turn, "typed", None):       # figures that rest on lines a person typed
        out["typed"] = list(turn.typed)
    return out


def _local_model():
    from .models.local import LocalModel
    return LocalModel(timeout=600)


class CheckStopped(Exception):
    """The person asked the model's check to stop; it stops between two pages."""


class _State:
    def __init__(self, folder: Path, loop, model_factory=None, gateway=None, on_folder=None):
        self.folder = folder
        self.on_folder = on_folder
        self.loop = loop
        self.turn = None
        self.lock = threading.Lock()
        self.filled: list = []
        # The local AI check — offered, answered, and run apart from the page's lock
        # (a 26B model takes most of a minute a page; the questions must not wait on it).
        self.model_factory = model_factory or _local_model
        self.gateway = gateway
        self.ai_offer = None
        self.ai = {"answer": None, "model": None,
                   # all three checks of the filled forms, and the check starting by itself
                   # after a fill, by design; each stays a choice on the page
                   "options": {"read_back": True, "empty_boxes": True, "trace": True, "after_fill": True}}
        self.session_problem: str | None = None    # a saved return that could not be read
        self.session_unreadable = False            # …and so must not be written over
        self.resumed_at: str | None = None          # when the return this folder holds was saved
        self.ai_log: list = []
        # a console for the work itself — what was read, what was computed, how long
        # the engine took, what was filled, in the model log's shape.
        self.work_log: list = []
        self.log_lock = threading.Lock()
        self.inbox_left: set = set()        # files in the input folder the person said to leave out
        self.page_watch = None              # the packaged app's: it stops once the page is gone
        self.reset_check()

    def reset_check(self):
        """A check's rows describe the documents and forms it read; a new document or a new fill
        makes them about something else, so they go (never a result from
        another moment shown as this one's)."""
        if getattr(self, "check", {}).get("status") != "running":
            self.check = {"status": "idle", "what": None, "parts": [], "part": None, "done": 0,
                          "total": 0, "now": "", "eta_seconds": None, "rows": [], "problem": None}

    def ai_state(self, refresh: bool = False) -> dict:
        from . import aicheck
        if self.ai_offer is None or refresh:
            client = self.model_factory()
            client.timeout = 10
            survey = client.survey()
            self.ai_offer = (aicheck.offer(survey) if self.gateway is None
                             else aicheck.offer(survey, gateway=self.gateway))
        return {**self.ai_offer, "answer": self.ai["answer"], "model": self.ai["model"],
                "options": self.ai["options"],
                "check": self.check, "filled": bool(self.forms()[0]),
                "filled_earlier": bool(self.forms()[1]),
                "documents": len(self.loop.documents)}

    FILLED_PARTS = ("read_back", "empty_boxes", "trace")

    STALE_FORMS = ("The forms in the output folder were filled before this return last changed, so "
                   "they are not this return's. Fill the forms again first.")

    def forms(self) -> tuple[list, list]:
        """The filled forms that are THIS return's, and the ones left from before it last changed.
        A folder was opened again, the filled forms were asked to be checked, and the model
        read forms from an earlier sitting (2026-09-22): a PDF on disk says nothing about which
        return it was filled for, so the fingerprint kept at the fill does."""
        if not self.filled:
            return [], []
        fingerprint = getattr(self.loop, "fingerprint", None)
        if fingerprint is not None and getattr(self.loop, "filled_for", None) == fingerprint():
            return list(self.filled), []
        return [], list(self.filled)

    def note(self, text: str) -> None:
        """One line for the page's console, with the local clock. Never a fact path, never an
        identifier: what a person reads here is the same words the page says elsewhere."""
        import datetime
        with self.log_lock:
            self.work_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {text}")
            del self.work_log[:-2000]

    def log_line(self, text: str):
        with self.log_lock:
            self.ai_log.append(text)
            del self.ai_log[:-3000]

    def start_check(self, what: str) -> dict:
        """Snapshot what the check reads under the page's lock, then run it on its own thread."""
        from ..client.formfill import FORM_NAMES
        if self.ai["answer"] != "yes" or not self.ai["model"]:
            raise ValueError("The check by a local AI model was not chosen.")
        if self.check["status"] == "running":
            raise ValueError("A check is already running.")
        documents, confirmed = list(self.loop.documents), dict(self.loop.case.confirmed())
        if what == "documents":
            if not documents:
                raise ValueError("No document has been read yet.")
            # A model re-reads the PAGES of a form this version reads. A workbook is not one of
            # those — it has no page to look at — and neither is a form this version does not read.
            # Counting every document here offered a check with nothing in it, and the log then
            # said the model returned nothing when the model was never asked (seen
            # 2026-09-22).
            from ..client.documents import FACT_GROUPS
            unreadable = [d for d in documents if getattr(d, "form_type", None) not in FACT_GROUPS]
            if len(unreadable) == len(documents):
                named = ", ".join(f"{Path(getattr(d, 'document', '') or '').name} "
                                  f"({getattr(d, 'form_type', 'not recognised')})"
                                  for d in unreadable[:4])
                raise ValueError(
                    f"Nothing here can be read again by a model: {named}. A model re-reads the "
                    f"pages of a form this version reads; a workbook has no page to read, and "
                    f"neither has a form this version does not read.")
            parts = ["documents"]
            job = {"documents": documents, "confirmed": confirmed, "input": self.folder / "input",
                   # what the page read and nobody has confirmed yet: a document restored from an
                   # earlier sitting carries no candidates of its own, and the case is where its
                   # readings actually live
                   "proposed": {path: cands[0].value
                                for path, cands in self.loop.case.pending().items() if cands}}
        elif what == "filled":
            current, earlier = self.forms()
            if not current:
                raise ValueError(self.STALE_FORMS if earlier else "No form has been filled yet.")
            parts = [p for p in self.FILLED_PARTS if self.ai["options"].get(p)]
            if "trace" in parts and "read_back" not in parts:
                parts.insert(0, "read_back")        # the trace places figures by the read-back's lines
            if not parts:
                raise ValueError("Choose at least one of the checks of the filled forms.")
            job = {"documents": documents, "confirmed": confirmed, "output": self.folder / "output",
                   "joint": self.loop._facts().get("filing_status") == "mfj",
                   "typed": [f["value"] for f in self.identity()["fields"] if f.get("value")],
                   "names": {"f" + k[3:].lower(): v for k, v in FORM_NAMES.items() if k.startswith("IRS")}}
        else:
            raise ValueError("Choose the documents or the filled forms.")
        self.check = {"status": "running", "what": what, "parts": parts, "part": None, "done": 0,
                      "total": 0, "now": "", "eta_seconds": None, "rows": [], "problem": None}
        # each check is headed with what it reads and when, so the log never reads as one run
        import datetime
        self.log_line(f"=== {datetime.datetime.now().strftime('%H:%M:%S')}: checking "
                      + ("the figures read from " + ", ".join(
                          Path(getattr(d, "document", "") or "").name for d in documents)
                         if what == "documents" else "the filled forms: " + ", ".join(self.filled))
                      + " ===")
        threading.Thread(target=self._run_check, args=(parts, job), daemon=True).start()
        return self.check

    def _run_check(self, parts, job):
        import time
        from . import aicheck
        from .models.local import ModelUnavailable
        check = self.check
        clock = {"started": time.monotonic()}

        def progress(done, total, now):
            # a person waited most of an hour on a check a processor-bound model was running,
            # with no way to end it (2026-09-23): a stop asked for is honoured before the next page
            if check.get("stop"):
                check.update(done=done, total=total)      # what finished is what the words count
                raise CheckStopped()
            eta = None
            if done:
                eta = round((time.monotonic() - clock["started"]) / done * (total - done))
            # …and say WHICH one in the log. Four checks were seen to log their heading and
            # nothing else (2026-09-22): the model log records the calls, so a check that stalls
            # before its first call names nothing at all, and the console cannot say where it got
            # to. One line per thing the model is about to read, by its own name.
            if now and now != check.get("now"):
                self.log_line(f"{done + 1} of {total}: {now}")
            check.update(done=done, total=total, now=now, eta_seconds=eta)
        rows = check["rows"]                           # filled as it goes; kept if the model fails
        name = self.ai["model"]
        try:
            # replies kept in the working folder: the same page and question are not asked twice
            model = aicheck.Remembered(aicheck.Logged(self.model_factory(), self.log_line),
                                       self.folder / "input" / "case.model-readings.json", self.log_line)
            readings = []
            for part in parts:
                clock["started"] = time.monotonic()
                check.update(part=part, done=0, total=0, eta_seconds=None)
                self.log_line(f"--- {part.replace('_', ' ')} ---")
                if part == "documents":
                    aicheck.check_documents(job["documents"], job["confirmed"], model, name, progress,
                                            input_folder=job["input"], rows=rows,
                                            proposed=job.get("proposed"))
                elif part == "read_back":
                    aicheck.check_filled(job["output"], job["typed"], job["names"], model, name, progress,
                                         rows=rows, readings=readings)
                elif part == "empty_boxes":
                    aicheck.review_blanks(job["output"], job["typed"], job["names"], model, name, progress,
                                          rows=rows, joint=job["joint"])
                elif part == "trace":
                    aicheck.trace(aicheck.document_figures(job["documents"], job["confirmed"]), readings,
                                  rows=rows)
            if not rows:
                # A finished check that compared nothing is not a running one, and the page used to
                # leave the running words on screen forever ("the page looked dead").
                # Say WHICH of the two it was: the model answered nothing, or it was never asked.
                self.log_line("nothing was compared" if not check.get("total")
                              else "the model returned nothing to compare")
            check.update(status="done", now="", eta_seconds=None)
        except CheckStopped:
            self.log_line("stopped, as asked")
            check.update(status="stopped", now="", eta_seconds=None,
                         problem=(f"The check was stopped, as asked, after {check.get('done', 0)} of "
                                  f"{check.get('total', 0)}. Nothing was changed; the rows below are "
                                  f"the ones it had finished."))
        except ModelUnavailable as why:
            check.update(status="error", now="", eta_seconds=None,
                         problem=f"The model could not be used: {why}. Nothing was changed; the model log says more.")
        except Exception as why:                       # said, never swallowed
            self.log_line(f"ERROR: {type(why).__name__}: {why}")
            check.update(status="error", now="", eta_seconds=None,
                         problem=f"The check stopped: {why}. Nothing was changed; the model log says more.")

    def workbook_edited(self) -> dict | None:
        """return-workbook.xlsx changed after this page wrote it, and would change the return: the
        page then asks whether to use it as input. Decided by what the workbook SAYS, never by its
        date: computing it again
        rewrites the file without changing an answer. Asked once per edit; a "no" holds until the
        workbook changes again."""
        from . import workbook_out
        from .loop import facts_hash
        written = getattr(self.loop, "workbook_for", None)
        path = self.folder / "output" / workbook_out.NAME
        if not written or not path.is_file():
            return None
        try:
            stat = path.stat()
            key = (str(path), stat.st_mtime_ns, stat.st_size)
            if getattr(self, "_workbook_seen", (None,))[0] != key:
                self._workbook_seen = (key, self._read_workbook(path.read_bytes()))
        except OSError:
            return None                          # open in Excel mid-save: asked on the next look
        found = self._workbook_seen[1]
        if found["hash"] in (written, getattr(self.loop, "workbook_declined", None),
                             facts_hash(self.loop._facts())):
            return None
        return {"name": workbook_out.NAME, "path": str(path.resolve()),
                "changes": self._workbook_changes(found.get("facts") or {}),
                "problem": found.get("problem")}

    def paper_values(self) -> dict:
        """`{path: cents}` — what the paper says, for the workbook's `From the form` column (seen
        2026-09-23: after an edited `Amount to use` was taken as the answer, the next
        fill wrote the new figure into `From the form` too, and the W-2's own figure was gone).
        A document's reading as confirmed on its card wins — a correction made there is what the
        paper says; the workbook this page last wrote carries the rest forward."""
        from . import workbook_out
        values = {}
        old = self.folder / "output" / workbook_out.NAME
        if old.is_file():
            try:
                from ..client.workbook.reader import read_workbook
                values.update({path: cents for path, cents in read_workbook(old.read_bytes()).originals.items()
                               if isinstance(cents, int)})
            except Exception:
                pass                         # a workbook that no longer reads carries nothing
        for path, (value, evidence) in self.loop.case.confirmed().items():
            if (path.endswith("_cents") and isinstance(value, int)
                    and getattr(evidence, "tier", "") != "answer"
                    and str(getattr(evidence, "document", "") or "").lower().endswith(".pdf")):
                values[path] = value
        return values

    @staticmethod
    def _read_workbook(data: bytes) -> dict:
        import hashlib
        from ..client.workbook.reader import WorkbookRefused, read_workbook
        from .loop import facts_hash
        try:
            read = read_workbook(data)
        except WorkbookRefused as why:
            return {"hash": hashlib.sha256(data).hexdigest(), "problem": str(why)}
        if read.refusals:
            named = "; ".join(str(r) for r in read.refusals[:4])
            return {"hash": hashlib.sha256(data).hexdigest(),
                    "problem": f"{len(read.refusals)} cell(s) cannot be read: {named}"}
        return {"hash": facts_hash(read.facts), "facts": read.facts}

    def _workbook_changes(self, facts: dict) -> list:
        """Each answer the workbook would change, in the question's own words, old and new."""
        from ..client.form_labels import label_for
        from ..client.interview import PROMPTS
        from .loop import _flatten_facts
        mine = _flatten_facts(self.loop._facts())
        theirs = _flatten_facts({k: v for k, v in facts.items() if k != "tax_year"})

        def shown(path, value):
            if value is None:
                return "(none)"
            if path.endswith("_cents") and isinstance(value, int):
                return _dollars(value)
            return {True: "Yes", False: "No"}.get(value, str(value)) if isinstance(value, bool) else str(value)
        out = []
        for path in sorted(set(mine) | set(theirs)):
            if mine.get(path) == theirs.get(path):
                continue
            field = path.rsplit(".", 1)[-1]
            group = path.split("[", 1)[0] if "[" in path else None
            # a field with no words of its own is never shown by its name
            words = (label_for(group, field) if group else None) or PROMPTS.get(field) or "An answer"
            if group:
                words += f" (row {int(path.split('[', 1)[1].split(']', 1)[0]) + 1})"
            if path not in theirs:
                # taking a workbook answers what it holds; it never takes an answer away
                out.append(f"{words}: {shown(path, mine.get(path))} — the workbook leaves this out; "
                           f"it stays as answered here, and can be changed in the list of answers")
            else:
                out.append(f"{words}: {shown(path, mine.get(path))} → {shown(path, theirs.get(path))}")
        return out

    def inbox(self) -> list:
        """The documents in the working folder's input that are not read yet (seen
        2026-09-22: a folder was chosen, and the file chooser still opened on the folder used last
        time — a browser opens it where it last looked, and no page can point it anywhere). The page
        lists these and reads them where they lie, so the folder chosen IS where the documents come
        from. Only what this page reads: PDF forms and the workbook, never the page's own files."""
        folder = self.folder / "input"
        if not folder.is_dir():
            return []
        read_names = {Path(getattr(d, "document", "") or "").name for d in self.loop.documents}
        read_digests = {getattr(d, "digest", None) for d in self.loop.documents} - {None}
        waiting = []
        for path in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
            name = path.name
            if (not path.is_file() or name.startswith(("case.", "~$", "."))
                    or path.suffix.lower() not in (".pdf", ".xlsx")
                    or name in read_names or name in self.inbox_left):
                continue
            try:
                if hashlib.sha256(path.read_bytes()).hexdigest() in read_digests:
                    continue                         # the same bytes, read under another name
            except OSError:
                continue                             # open in another program: listed next look
            waiting.append(name)
        return waiting

    def take_document(self, name: str, body: bytes, forced: bool = False, in_place: bool = False):
        """Read one document into the return: `(status, reply)`. An upload is written into the
        input folder first; a file already THERE (`in_place`) is read where it lies and never
        rewritten or deleted — it is the person's own file."""
        workbook = name.lower().endswith(".xlsx") and body.startswith(b"PK")
        if not workbook and (not name.lower().endswith(".pdf") or not body.startswith(b"%PDF-")):
            return 400, {"error": "Only PDF forms and this return's own workbook (.xlsx) are read here."}
        # The same document dropped twice is named, not read again — a second
        # copy of one W-2 made a one-W-2 return a two-W-2 return, and the refusal that followed
        # named neither the document nor the cause. Same name, or the same bytes under another
        # name, both count. The documents list is the record of what was read.
        digest = hashlib.sha256(body).hexdigest()
        for d in self.loop.documents:
            same_name = Path(getattr(d, "document", "") or "").name == name
            same_bytes = getattr(d, "digest", None) == digest
            if same_name or same_bytes:
                prior = Path(getattr(d, "document", "") or "").name
                return 400, {"error": (f"{name} was already read" if same_name else
                                       f"{name} is the same document as {prior}, which was already read")
                             + ". Each form is read once."}
        target = self.folder / "input" / name
        if not in_place:
            target.write_bytes(body)
        if workbook:
            # The other way in: the spreadsheet this page writes, filled in and given back.
            from .loop import WorkbookNotTaken
            try:
                record = self.loop.add_workbook(body, name)
            except WorkbookNotTaken as why:
                if not in_place:
                    target.unlink(missing_ok=True)
                return 400, {"error": str(why)}
            record.digest = digest
            self.turn = None
            self.reset_check()
            self.keep()
            self.note(f"read {name}: the workbook, {record.answered} answer(s)")
            return 200, {"document": name, "form": "workbook", "read": record.answered,
                         "unconsumed": None, "not_read": [], "identity_notes": [],
                         "turn": turn_json(self.current())}
        # Read first, ask second. A form whose every figure matches one already
        # read is the same form twice — a W-2 saved AND scanned, which the name-and-bytes check
        # cannot see and which doubles a wage. Nothing enters the return until the person says.
        from . import identity_check
        result = self.loop.read_only(target)
        content = identity_check.content_key(result)
        twin = next((d for d in self.loop.documents
                     if content and getattr(d, "content", None) == content), None)
        if twin is not None and not forced:
            if not in_place:
                target.unlink(missing_ok=True)
            prior = Path(getattr(twin, "document", "") or "").name
            return 409, {"duplicate": {
                "name": name, "prior": prior, "form": result.form_type,
                "read": len(result.candidates),
                "words": (f"{name} reads exactly like {prior}, which this return already holds: "
                          f"the same {result.form_type} and the same {len(result.candidates)} "
                          f"figures. Adding it again would count those figures twice. Is it a "
                          f"second form, or the same one again?")}}
        self.loop.attach(result)
        try:
            result.digest = digest
            result.content = content
            result.identity_notes = identity_check.check(
                target, {f["term"]: f["value"] for f in self.identity()["fields"] if f.get("value")})
        except AttributeError:
            pass
        self.turn = None
        self.reset_check()
        self.keep()
        self.note(f"read {name}: {result.form_type}, {len(result.candidates)} figure(s)"
                  + (f"; {result.unconsumed}" if result.unconsumed else ""))
        for said in getattr(result, "identity_notes", []) or []:
            self.note(said)
        return 200, {"document": name, "form": result.form_type,
                     "read": len(result.candidates), "unconsumed": result.unconsumed,
                     "not_read": list(getattr(result, "not_carried", []) or []),
                     "not_read_lines": dict(getattr(result, "not_carried_lines", {}) or {}),
                     "identity_notes": list(getattr(result, "identity_notes", []) or []),
                     "turn": turn_json(self.current())}

    def keep(self) -> None:          # noqa: D401 — the saved return, after anything that changed it
        """Write the return into the working folder after anything that changed it.
        A folder that cannot be written is SAID, never silent — but it never costs the answer the
        person just gave, which is already in the case."""
        from . import session
        if self.session_unreadable:
            # The folder holds a return this page could not open, and the person was told it is
            # left as it is. Writing over it now would destroy exactly what that sentence promised
            # they could recover; "Start this folder again" is the way past it.
            return
        try:
            session.save(self.loop, self.folder)
            self.session_problem = None
        except OSError as why:
            self.session_problem = (f"This return is not being kept in {self.folder}: "
                                    f"{why.strerror}. Your answers are still on this page.")

    def reopen_folder(self) -> None:
        """A folder the person just chose: carry on the return it holds, or start a new one."""
        from . import session
        self.session_problem, self.resumed_at = None, None
        self.inbox_left = set()
        self.session_unreadable = False
        try:
            doc = session.read(self.folder)
            restored = session.restore(doc, ops=self.loop.ops, pdf_root=self.loop.pdf_root,
                                       model=self.loop.model,
                                       reader=getattr(self.loop, "_reader", None)) if doc else None
        except session.SessionError as why:
            self.session_problem = str(why)
            self.session_unreadable = True
            return
        if doc is None:
            self.keep()                      # a new folder holds this return from now on
            return
        self.loop = restored
        # a file written the moment a folder was confirmed holds no work: it says nothing
        self.resumed_at = doc.get("saved_at") if session.carries_a_return(doc) else None
        self.turn = None
        self.filled = sorted(p.name for p in (self.folder / "output").glob("*.pdf"))
        self.reset_check()

    def current(self):
        if self.turn is None:
            self.turn = self.loop.next_turn()
        return self.turn

    def summary(self) -> dict:
        from ..client.documents import FACT_GROUPS
        # a document read in an earlier sitting carries the COUNT it read, not its candidates:
        # those are in the case already, confirmed or waiting
        docs = [{"name": Path(getattr(d, "document", "") or "").name, "form": d.form_type,
                 "read": len(d.candidates) if d.candidates else getattr(d, "read", 0),
                 "unconsumed": d.unconsumed,
                 "not_read": list(getattr(d, "not_carried", []) or []),
                 "not_read_lines": (None if getattr(d, "not_carried_lines", None) is None
                                    else dict(d.not_carried_lines)),
                 "identity_notes": list(getattr(d, "identity_notes", []) or [])}
                for d in self.loop.documents]
        current, earlier = self.forms()
        return {"documents": docs, "turn": turn_json(self.current()), "filled": current,
                "filled_earlier": earlier,
                # the return this folder holds, picked up where it stopped
                "resumed_at": self.resumed_at, "session_problem": self.session_problem,
                "work_log": "\n".join(self.work_log),
                "folder": str(self.folder.resolve()),
                "input_folder": str((self.folder / "input").resolve()),
                "output_folder": str((self.folder / "output").resolve()),
                # the page says which input forms it reads — from the same table the
                # reader runs on, so the sentence cannot drift from the code
                "reads": list(FACT_GROUPS),
                "typed_not_read": TYPED_NOT_READ,
                "not_carried": NOT_CARRIED,
                "input_windows": windows_form(self.folder / "input"),
                "identity": self.identity(),
                "notations": self.notations(),
                "computed_at": getattr(self.loop, "computed_at", None),
                "workbook_edited": self.workbook_edited(),
                "inbox": self.inbox()}

    def identity(self) -> dict:
        """The identity boxes the filled forms need — the eleven Form 1040 boxes
        from the form's own register, with what the working folder's identity file holds for each.
        Local only: these values never enter the case, the engine request or any model."""
        from ..client import identity_file
        terms = [term for term in identity_file.load_identity_map()["fields"].values()]
        path = self.folder / "input" / identity_file.FILENAME
        values, problem = {}, None
        if path.is_file():
            try:
                values = identity_file.read(path)
            except identity_file.IdentityFileError as why:
                # A hand-edited file that cannot be read is SAID, in the reader's own words, and
                # the page still opens with blank boxes; saving from the page rewrites it whole.
                problem = str(why)
        seen = []
        for term in terms:
            if term not in seen:
                seen.append(term)
        return {"fields": [{"term": term, "label": identity_file.words_for(term),
                            "value": values.get(term, "")} for term in seen],
                "file": str(path), "problem": problem}

    def notations(self) -> dict:
        """Form 1040's notation strip as the working folder holds it: what is
        ticked, the date of death, and the three Other entries — kept on this computer only."""
        from ..client import notations
        path = self.folder / "input" / notations.FILENAME
        problem, kept = None, {}
        try:
            kept = notations.read(path)
        except notations.NotationError as why:
            problem = str(why)
        return {"values": kept, "file": str(path), "problem": problem}

    def save_notations(self, given: dict) -> dict:
        from ..client import notations
        kept = notations.write(self.folder / "input" / notations.FILENAME, given, self.loop.case.tax_year)
        return {"values": kept, "file": str(self.folder / "input" / notations.FILENAME), "problem": None}

    def save_identity(self, given: dict) -> dict:
        from ..client import identity_file
        known = {f["term"] for f in self.identity()["fields"]}
        unknown = [k for k in given if k not in known]
        if unknown:
            raise ValueError("That is not one of the boxes the forms need.")
        values = {k: str(v).strip() for k, v in given.items() if str(v or "").strip()}
        problem = identity_file.against_return(values, self.loop._facts())
        if problem:
            raise ValueError(problem)
        path = self.folder / "input" / identity_file.FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        identity_file.write(path, values)
        return self.identity()


def _handler(state: _State, token: str):
    class Handler(BaseHTTPRequestHandler):
        expected_host = ""

        def log_message(self, *args):          # nothing about a request is logged anywhere
            pass

        def _send(self, code: int, body: bytes, ctype: str = "application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj):
            self._send(code, json.dumps(obj).encode("utf-8"))

        def _allowed(self) -> bool:
            if self.headers.get("Host", "") != Handler.expected_host:
                self._json(403, {"error": "This page answers only on its own address."})
                return False
            query = parse_qs(urlparse(self.path).query)
            given = self.headers.get("X-Intake-Token") or (query.get("t") or [""])[0]
            if not secrets.compare_digest(given, token):
                # The launch token is this RUN's: a page left open from an earlier run keeps the
                # old one in its address and every answer it sends is refused. Said as what it is
                # and what to do, because "open the link yTax gave you" left a person on a
                # dead page with no way to tell which link that was (2026-09-22).
                self._json(403, {"error": "This page was opened by an earlier run of yTax, and "
                                          "this run does not know it. Start yTax again and use "
                                          "the page it opens. Nothing in your folder is lost — "
                                          "the return is picked up where it stopped."})
                return False
            return True

        def do_GET(self):
            if not self._allowed():
                return
            route = urlparse(self.path).path
            if state.page_watch is not None:
                state.page_watch.seen()
            if route in STATIC:
                name, ctype = STATIC[route]
                body = (PAGE / name).read_bytes()
                if name == "index.html":
                    # the page's own stylesheet and script are fetched by the BROWSER, which
                    # sends no token with a relative URL — so they were refused and the page
                    # rendered as dead markup (a file chooser that did nothing). The token rides on
                    # the asset links instead of the check being dropped: a bare /app.js is still
                    # refused, and nothing on this page answers without the token.
                    for asset in ("app.css", "app.js"):
                        body = body.replace(f'"{asset}"'.encode(),
                                            f'"{asset}?t={token}"'.encode())
                self._send(200, body, ctype)
                return
            if route == "/api/answers":
                with state.lock:
                    self._json(200, {"answers": state.loop.answers()})
                return
            if route == "/api/browse":
                # A folder browser on the starting page. Folders only, never a
                # file's contents; the person's own machine, served only to the page's token.
                typed = (parse_qs(urlparse(self.path).query).get("path") or [""])[0]
                try:
                    self._json(200, browse_folder(typed, state.folder))
                except FolderError as why:
                    self._json(400, {"error": str(why)})
                return
            if route in ("/api/ai", "/api/check"):
                # asked of Ollama outside the page's lock — a survey waits on the
                # network, a running check on a model; neither holds up a question.
                refresh = bool((parse_qs(urlparse(self.path).query).get("refresh") or [""])[0])
                if route == "/api/ai":
                    self._json(200, state.ai_state(refresh))
                else:
                    with state.log_lock:
                        log = "\n".join(state.ai_log)
                    self._json(200, {**state.check, "log": log})
                return
            if route == "/api/inbox":
                with state.lock:
                    self._json(200, {"inbox": state.inbox(),
                                     "folder": str((state.folder / "input").resolve())})
                return
            if route == "/api/workbook/edited":
                # asked each time the person comes back to the page (from Excel, say): cheap, and
                # it computes nothing
                with state.lock:
                    self._json(200, {"workbook_edited": state.workbook_edited()})
                return
            if route == "/api/state":
                with state.lock:
                    self._json(200, state.summary())
                return
            if route == "/about":
                self._send(200, about_page().encode("utf-8"), "text/html; charset=utf-8")
                return
            self._json(404, {"error": "Not found."})

        def do_POST(self):
            if not self._allowed():
                return
            route = urlparse(self.path).path
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_UPLOAD:
                self._json(413, {"error": "That file is larger than this page takes."})
                return
            body = self.rfile.read(length) if length else b""
            if route == "/api/closing":
                # the page's tab is closing, or the page is reloading (sent as the page goes, with
                # the token in the address: a beacon carries no header)
                if state.page_watch is not None:
                    state.page_watch.closing()
                self._json(200, {"noted": True})
                return
            if state.page_watch is not None:
                state.page_watch.seen()
            if route == "/api/alive":
                self._json(200, {"alive": True})
                return
            if route == "/api/quit":
                # the packaged app has no window to close: the page's Quit stops this server, and
                # with it the program; the working folder keeps everything for the next start
                self.server.stop_reason = "Quit on the page"
                self._json(200, {"stopped": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if route == "/api/documents/pick":
                # The Windows "Open" window for the documents, starting in the working folder's
                # input (seen 2026-09-24: the browser's chooser opened on the folder used
                # last time, whatever folder was chosen). Outside the lock: it waits on a person.
                from . import folder_picker
                inbox = state.folder / "input"
                start = windows_form(inbox) or wsl_unc(inbox) or (str(inbox) if os.name == "nt" else "")
                try:
                    chosen = folder_picker.pick_files(start)
                except folder_picker.PickerUnavailable as why:
                    self._json(409, {"unavailable": str(why)})
                    return
                self._json(200, {"paths": chosen})
                return
            if route == "/api/folder/pick":
                # The Windows folder picker (2026-09-24). Opened by this program, not
                # the page — a browser never tells a page the path of a folder it picks — and held
                # OUTSIDE the page's lock: the window waits on a person.
                from . import folder_picker
                data = json.loads(body or b"{}")
                start = ""
                try:
                    here = resolve_folder(str(data.get("start") or "")) if data.get("start") else state.folder
                    while not here.is_dir() and here.parent != here:
                        here = here.parent             # a suggested folder not made yet: its parent
                    start = windows_form(here) or wsl_unc(here) or (str(here) if os.name == "nt" else "")
                except FolderError:
                    pass
                try:
                    chosen = folder_picker.pick_folder(start)
                except folder_picker.PickerUnavailable as why:
                    self._json(409, {"unavailable": str(why)})
                    return
                self._json(200, {"path": chosen, "cancelled": chosen is None})
                return
            try:
                with state.lock:
                    if route == "/api/documents":
                        self._document(body)
                    elif route == "/api/reply":
                        self._reply(body)
                    elif route == "/api/folder":
                        # the page asks where to work BEFORE anything is read or written. A
                        # folder that cannot be made is refused by name, not silently ignored.
                        data = json.loads(body or b"{}")
                        typed = str(data.get("path") or "").strip()
                        if not typed:
                            self._json(400, {"error": "Name a folder."})
                            return
                        try:
                            chosen = resolve_folder(typed)
                        except FolderError as why:
                            self._json(400, {"error": str(why)})
                            return
                        try:
                            (chosen / "input").mkdir(parents=True, exist_ok=True)
                            (chosen / "output").mkdir(parents=True, exist_ok=True)
                        except OSError as why:
                            self._json(400, {"error": f"That folder cannot be used: {why.strerror}."})
                            return
                        state.folder = chosen
                        state.reopen_folder()
                        if state.on_folder is not None:
                            # the bundle puts its working files and log in the folder's temp/; a
                            # temp/ that cannot be made costs only that, never the choice
                            try:
                                state.on_folder(chosen)
                            except OSError:
                                pass
                        self._json(200, {"folder": str(chosen.resolve()),
                                         "input_folder": str((chosen / "input").resolve()),
                                         "output_folder": str((chosen / "output").resolve())})
                    elif route == "/api/reopen":
                        data = json.loads(body or b"{}")
                        state.loop.reopen(data.get("path") or "")
                        state.turn = None
                        state.keep()
                        self._json(200, {"turn": turn_json(state.current())})
                    elif route == "/api/change":
                        # one answer changed in place from the summary's list; the
                        # questions continue from there.
                        data = json.loads(body or b"{}")
                        state.loop.change(data.get("path") or "", data.get("reply"))
                        state.turn = None
                        state.keep()
                        current, earlier = state.forms()
                        self._json(200, {"turn": turn_json(state.current()),
                                         "answers": state.loop.answers(),
                                         "filled": current, "filled_earlier": earlier})
                    elif route == "/api/session":
                        # start this folder again — the saved return is set aside,
                        # under its own name, and a new one begins
                        from . import session as _session
                        from .case import Case as _Case
                        from .loop import IntakeLoop as _Loop
                        kept = _session.set_aside(state.folder)
                        state.session_unreadable, state.session_problem = False, None
                        state.loop = _Loop(_Case(), ops=state.loop.ops, pdf_root=state.loop.pdf_root,
                                           model=state.loop.model)
                        state.turn, state.filled, state.resumed_at = None, [], None
                        state.inbox_left = set()
                        state.reset_check()
                        state.keep()
                        self._json(200, {"set_aside": str(kept) if kept else None,
                                         "turn": turn_json(state.current())})
                    elif route == "/api/notations":
                        # Form 1040's notation strip, kept on this computer
                        from ..client.notations import NotationError
                        data = json.loads(body or b"{}")
                        try:
                            self._json(200, {"notations": state.save_notations(data.get("values") or {})})
                        except NotationError as why:
                            self._json(400, {"error": str(why)})
                    elif route == "/api/identity":
                        # the identity the filled forms need, asked directly and kept
                        # on this computer — written to the working folder's identity file only.
                        data = json.loads(body or b"{}")
                        self._json(200, {"identity": state.save_identity(data.get("values") or {})})
                    elif route == "/api/ai":
                        # the person's answer to the offer, and which model
                        data = json.loads(body or b"{}")
                        answer = data.get("answer")
                        offer = state.ai_offer or {}
                        names = [m["name"] for m in offer.get("models", [])]
                        if answer not in ("yes", "no"):
                            self._json(400, {"error": "Answer yes or no."})
                            return
                        if answer == "yes" and data.get("model") not in names:
                            self._json(400, {"error": "Choose one of the models listed."})
                            return
                        options = dict(state.ai["options"])
                        for key, value in (data.get("options") or {}).items():
                            if key in options:
                                options[key] = bool(value)
                        state.ai = {"answer": answer, "model": data.get("model") if answer == "yes" else None,
                                    "options": options}
                        self._json(200, {"answer": state.ai["answer"], "model": state.ai["model"],
                                         "options": options})
                    elif route == "/api/check/stop":
                        if state.check.get("status") != "running":
                            self._json(409, {"error": "No check is running."})
                            return
                        state.check["stop"] = True
                        self._json(200, {**state.check})
                    elif route == "/api/check":
                        data = json.loads(body or b"{}")
                        self._json(200, state.start_check(str(data.get("what") or "")))
                    elif route == "/api/workbook":
                        # the person edited return-workbook.xlsx; compute it again
                        from . import workbook_out
                        try:
                            path = workbook_out.compute_again(state.folder / "output", ops=state.loop.ops)
                        except FileNotFoundError as why:
                            self._json(400, {"error": str(why)})
                            return
                        self._json(200, {"workbook": str(path.resolve())})
                    elif route == "/api/inbox/read":
                        # the documents already in the input folder, read where they lie, in order;
                        # one that reads like a form already held is asked about, as an upload is
                        data = json.loads(body or b"{}")
                        waiting = state.inbox()
                        names = [n for n in (data.get("names") or waiting) if n in waiting]
                        read, problems, duplicates = [], [], []
                        for name in names:
                            try:
                                raw = (state.folder / "input" / name).read_bytes()
                            except OSError as why:
                                problems.append({"name": name, "error": f"{name} cannot be opened: {why.strerror}."})
                                continue
                            status, answer = state.take_document(name, raw, bool(data.get("add_anyway")),
                                                                 in_place=True)
                            if status == 200:
                                read.append(answer)
                            elif status == 409:
                                duplicates.append(answer["duplicate"])
                            else:
                                problems.append({"name": name, "error": answer.get("error")})
                        self._json(200, {"read": read, "problems": problems, "duplicates": duplicates,
                                         "inbox": state.inbox(), "turn": turn_json(state.current())})
                    elif route == "/api/documents/take":
                        # The documents chosen in the Windows window, copied into the working
                        # folder's input (a file already there is left where it is) and then read
                        # like any other document waiting there — duplicates asked about the same way.
                        import shutil
                        data = json.loads(body or b"{}")
                        inbox = state.folder / "input"
                        names, problems = [], []
                        for typed in data.get("paths") or []:
                            try:
                                source = resolve_folder(str(typed))
                            except FolderError as why:
                                problems.append({"name": str(typed), "error": str(why)})
                                continue
                            if not source.is_file():
                                problems.append({"name": source.name,
                                                 "error": f"{source.name} cannot be opened from here."})
                                continue
                            name = _SAFE_NAME.sub("_", source.name)
                            target = inbox / name
                            try:
                                if source.resolve() != target.resolve():
                                    inbox.mkdir(parents=True, exist_ok=True)
                                    shutil.copyfile(source, target)
                            except OSError as why:
                                problems.append({"name": name, "error": f"{name} could not be copied: {why.strerror}."})
                                continue
                            names.append(name)
                        self._json(200, {"names": names, "problems": problems})
                    elif route == "/api/inbox/leave":
                        data = json.loads(body or b"{}")
                        name = str(data.get("name") or "")
                        if name not in state.inbox():
                            self._json(400, {"error": f"{name} is not waiting in the input folder."})
                            return
                        state.inbox_left.add(name)
                        state.note(f"left {name} out, as asked; it stays in the input folder")
                        self._json(200, {"inbox": state.inbox()})
                    elif route == "/api/workbook/use":
                        # the person's answer about an edited return-workbook.xlsx: its figures
                        # become their answers, or the edit is left where it is
                        from . import workbook_out
                        from .loop import WorkbookNotTaken
                        data = json.loads(body or b"{}")
                        edited = state.workbook_edited()
                        if edited is None:
                            self._json(409, {"error": "The workbook has not changed since this page wrote it."})
                            return
                        found = state._workbook_seen[1]
                        if not data.get("use"):
                            state.loop.workbook_declined = found["hash"]
                            state.keep()
                            state.note(f"left the edited {workbook_out.NAME} unused, as asked")
                            self._json(200, {"workbook_edited": None})
                            return
                        raw = (state.folder / "output" / workbook_out.NAME).read_bytes()
                        # the workbook taken before stands for this one: one row in the list, not one per edit
                        kept = [d for d in state.loop.documents
                                if not (getattr(d, "form_type", None) == "workbook"
                                        and Path(getattr(d, "document", "") or "").name == workbook_out.NAME)]
                        before = state.loop.documents
                        state.loop.documents = kept
                        try:
                            record = state.loop.add_workbook(raw, workbook_out.NAME)
                        except WorkbookNotTaken as why:
                            state.loop.documents = before
                            self._json(400, {"error": str(why)})
                            return
                        import hashlib
                        record.digest = hashlib.sha256(raw).hexdigest()
                        state.loop.workbook_for = found["hash"]     # taken: this edit is not asked again
                        state.turn = None
                        state.reset_check()
                        state.keep()
                        state.note(f"took the edited {workbook_out.NAME} as answers: "
                                   f"{len(edited['changes'])} change(s)")
                        current, earlier = state.forms()
                        self._json(200, {"turn": turn_json(state.current()), "workbook_edited": None,
                                         "filled": current, "filled_earlier": earlier})
                    elif route == "/api/compute":
                        env = state.loop.compute()
                        lines = {l["line_id"]: _dollars(l["value_cents"])
                                 for l in env["result"]["forms"][0]["lines"]}
                        self._json(200, {"lines": lines})
                    elif route == "/api/fill":
                        from ..client.notations import FILENAME as NOTATIONS_FILE
                        identity = state.folder / "input" / "case.identity.ini"
                        notes = state.folder / "input" / NOTATIONS_FILE
                        report = state.loop.fill(state.folder / "output",
                                                 identity_path=identity if identity.is_file() else None,
                                                 notations_path=notes if notes.is_file() else None)
                        state.filled = [f.out_path.name for f in report.filled if f.out_path]
                        state.loop.filled_for = state.loop.fingerprint()
                        state.reset_check()
                        state.keep()
                        # the original workbook beside the forms, to try scenarios in
                        workbook, workbook_problem = None, None
                        try:
                            if state.loop.case.typed():
                                # the workbook computes from the service facts alone
                                # and would disagree with forms that carry typed lines — not
                                # written, and said.
                                workbook_problem = state.loop.TYPED_WORKBOOK
                            else:
                                from . import workbook_out
                                written = workbook_out.write(
                                    state.loop._facts(), state.loop.case.tax_year,
                                    state.folder / "output", ops=state.loop.ops,
                                    originals=state.paper_values())
                                workbook = written.name
                                # what the file SAYS, read back — so a workbook nobody touched can
                                # never read as edited, whatever the writer leaves out
                                found = state._read_workbook(written.read_bytes())
                                from .loop import facts_hash
                                state.loop.workbook_for = (found["hash"] if "facts" in found
                                                           else facts_hash(state.loop._facts()))
                                state.keep()      # kept with the return, or a reopened page compares against the last one
                        except Exception as why:           # the forms stand; the workbook is said
                            workbook_problem = f"The workbook was not written: {why}"
                        started = None
                        if (state.filled and state.ai["answer"] == "yes"
                                and state.ai["options"].get("after_fill")):
                            # the check of the filled forms starts by itself
                            try:
                                started = state.start_check("filled")["status"]
                            except ValueError:
                                started = None
                        # a name alone left a person hunting for f1040.pdf. Say the folder.
                        lint = getattr(report, "lint", None) or {}
                        state.note(f"filled {len(state.filled)} form(s) into "
                                   f"{(state.folder / 'output').resolve()}; {_lint_words(lint)}"
                                   + (f"; wrote {workbook}" if workbook else ""))
                        self._json(200, {"filled": state.filled,
                                         "folder": str((state.folder / "output").resolve()),
                                         "stated": list(getattr(report, "stated", []) or [])
                                         + state.loop.typed_statement(),
                                         "lint": {"checked": lint.get("checked", 0),
                                                  "defects": lint.get("defects", 0),
                                                  "words": _lint_words(lint)},
                                         "check_started": started == "running",
                                         "workbook": workbook, "workbook_problem": workbook_problem})
                    else:
                        self._json(404, {"error": "Not found."})
            except Exception as why:                       # said, never swallowed
                self._json(400, {"error": str(why)})

        def _document(self, body: bytes):
            name = _SAFE_NAME.sub("_", Path(self.headers.get("X-Filename") or "document.pdf").name)
            forced = (self.headers.get("X-Add-Anyway") or "").strip() == "1"
            self._json(*state.take_document(name, body, forced))

        def _reply(self, body: bytes):
            data = json.loads(body or b"{}")
            turn = state.current()
            if data.get("turn_id") != turn.id:
                self._json(409, {"error": "That question has already moved on.", "turn": turn_json(turn)})
                return
            import time
            # the "how many more of these forms?" page writes its workbook where a fill writes one
            state.loop.workbook_dir = state.folder / "output"
            state.loop.respond(turn, data.get("reply"))
            if turn.kind == "more_forms" and any(state.loop._more_forms.values()):
                state.note(f"wrote {state.loop.more_workbook} with rows for "
                           + ", ".join(f"{n} {state.loop._form_words(g)}"
                                     for g, n in state.loop._more_forms.items() if n))
            state.turn = None
            state.keep()
            started = time.monotonic()
            nxt = state.current()
            took = time.monotonic() - started
            if nxt.kind == "complete":
                lines = nxt.lines or {}
                state.note(f"computed the return against the engine on this computer in {took:.1f} s "
                           f"— {len(lines)} Form 1040 line(s)"
                           + (f", line 24 {_dollars(lines['24'])}" if "24" in lines else ""))
            elif nxt.kind == "refused":
                state.note(f"the return was refused after {took:.1f} s: "
                           + "; ".join(turn_json(nxt).get("refusals") or [])[:400])
            current, earlier = state.forms()
            out = {"turn": turn_json(nxt), "filled": current, "filled_earlier": earlier}
            if nxt.kind in ("complete", "refused"):
                out["answers"] = state.loop.answers()   # drawn with the figures, not after them
            self._json(200, out)

    return Handler


class FolderError(ValueError):
    """A folder this page cannot use, said in words a person can act on."""


_WINDOWS_PATH = re.compile(r"^([A-Za-z]):[\\/](.*)$", re.S)
_UNC_PREFIX = "\\\\"
# `\\wsl.localhost\<distro>\…` (or `\\wsl$\…`): how Windows names a folder inside WSL — what the
# Windows folder picker returns for one. Under WSL, for THIS distribution, it is that Linux folder.
_WSL_UNC = re.compile(r"^\\\\(?:wsl\.localhost|wsl\$)\\([^\\]+)\\?(.*)$", re.I | re.S)


def wsl_unc(path: Path) -> str | None:
    """A Linux folder as Windows names it from outside WSL, or None when this is not WSL."""
    distro = os.environ.get("WSL_DISTRO_NAME")
    if not distro or os.name == "nt":
        return None
    return f"\\\\wsl.localhost\\{distro}" + str(Path(path).resolve()).replace("/", "\\")


def resolve_folder(typed: str, home=None, windows=None) -> Path:
    """What a person typed, as a folder on THIS machine.

    Three shapes reach this page. A Linux path is itself. A name with no leading slash means the
    person's own home, never whatever directory this process happens to run in, which is the bug
    that put the repository's path in front of the folder. A Windows path is translated to its
    mount, because this server can run inside WSL while the person reads Windows paths off their
    own screen; if that drive is not mounted here it is refused by name, rather than glued onto the
    home folder, which is what was actually seen.

    ON WINDOWS ITSELF a Windows path IS the path and nothing is translated. Measured 2026-09-17 in
    the shipped bundle: `C:\\Users\\…` was refused there with "drive C: is not available here:
    nothing is mounted at /mnt/c" — WSL's answer, given to a person whose computer has no WSL and
    whose folder was right in front of them.
    """
    typed = (typed or "").strip().strip('"')
    if not typed:
        raise FolderError("Name a folder.")
    inside = _WSL_UNC.match(typed)
    if (inside and not (os.name == "nt" if windows is None else windows)
            and inside.group(1).lower() == (os.environ.get("WSL_DISTRO_NAME") or "").lower()):
        return Path("/" + inside.group(2).replace("\\", "/"))     # this WSL's own folder
    if typed.startswith(_UNC_PREFIX):
        raise FolderError("A network path like that cannot be reached from here. Give a folder on "
                          "this computer.")
    if os.name == "nt" if windows is None else windows:
        return Path(typed).expanduser()          # a Windows path on Windows is itself
    drive = _WINDOWS_PATH.match(typed)
    if drive:
        letter = drive.group(1).lower()
        rest = drive.group(2).replace("\\", "/")
        mount = Path("/mnt") / letter
        if not mount.is_dir() or not any(mount.iterdir()):
            raise FolderError(
                f"{typed} is a Windows folder, and drive {letter.upper()}: is not available here: "
                f"nothing is mounted at {mount}. Give a folder on this computer instead.")
        return mount / rest
    path = Path(typed).expanduser()
    if not path.is_absolute():
        path = Path(home or Path.home()) / path
    return path


def windows_form(path: Path) -> str | None:
    """`/mnt/c/Users/x` as `C:\\Users\\x` — how a person finds a WSL-mounted folder from the
    Windows side; None for a folder that is not on a mounted drive."""
    parts = Path(path).resolve().parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "mnt" and len(parts[2]) == 1:
        return parts[2].upper() + ":\\" + "\\".join(parts[3:])
    return None


def browse_folder(typed: str, default: Path) -> dict:
    """One level of the folder tree for the page's browser: the folder itself, its parent, and its
    sub-folders by name (hidden ones skipped). A path that cannot be read is refused in words."""
    path = resolve_folder(typed) if (typed or "").strip() else Path(default)
    path = path.expanduser()
    if not path.is_dir():
        raise FolderError(f"{typed or path} is not a folder that can be opened here.")
    try:
        names = sorted(p.name for p in path.iterdir() if p.is_dir() and not p.name.startswith("."))
    except OSError as why:
        raise FolderError(f"{path} cannot be read: {why.strerror}.")
    parent = path.parent if path.parent != path else None
    return {"path": str(path), "parent": str(parent) if parent else None,
            "folders": names, "windows": windows_form(path)}


ABOUT_DIR_ENV = "YTAX_ABOUT_DIR"     # the packaged app's folder of version, license and notices


def about_documents(folder: Path) -> list:
    """The documents the About folder carries, in the order the About screen shows them."""
    return [doc for doc in [folder / "LICENSE", folder / "LICENSING.md",
                            *sorted((folder / "LICENSES").glob("*.txt")),
                            *sorted((folder / "legal").glob("*.md")), folder / "THIRD-PARTY-NOTICES.txt"]
            if doc.is_file()]


# a Markdown link's target: [text](target)
_DOC_LINK = re.compile(r"\]\(([^)\s]+)\)")


def about_broken_links(folder: Path) -> list:
    """Every relative link in the About folder's own Markdown documents (LICENSING.md, legal/) whose
    target is not in the folder, as "document -> target"; [] when all resolve. A web address or a
    #section is not checked, and neither are the third-party notices: they quote each component's
    license word for word, and a link there points into that component's own source tree."""
    broken = []
    root = folder.resolve()
    for doc in about_documents(folder):
        if doc.suffix != ".md":
            continue
        for target in _DOC_LINK.findall(doc.read_text(encoding="utf-8")):
            if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            path = (doc.parent / target.split("#", 1)[0]).resolve()
            if not (path.is_relative_to(root) and path.exists()):
                broken.append(f"{doc.relative_to(folder).as_posix()} -> {target}")
    return broken


def about_page() -> str:
    """The About screen: the application's name and version, and the license documents and
    third-party notices the package carries (read from the folder the packaged app names in
    YTAX_ABOUT_DIR). Run from source, it says so and shows no notices."""
    from html import escape
    folder = Path(os.environ[ABOUT_DIR_ENV]) if os.environ.get(ABOUT_DIR_ENV) else None
    version = "run from source"
    parts = []
    if folder is not None and folder.is_dir():
        version_file = folder / "VERSION"
        if version_file.is_file():
            version = version_file.read_text(encoding="utf-8").strip()
        for doc in about_documents(folder):
            if doc.is_file():
                name = doc.relative_to(folder).as_posix()
                parts.append(f'<h2>{escape(name)}</h2><pre>{escape(doc.read_text(encoding="utf-8"))}</pre>')
    body = "".join(parts) or "<p>License documents and third-party notices ship with the packaged application.</p>"
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>About ytax-prep</title><style>body{font:15px/1.5 system-ui,sans-serif;margin:24px;"
            "max-width:60rem}pre{white-space:pre-wrap;background:#f6f6f6;padding:12px}</style></head>"
            f"<body><h1>ytax-prep</h1><p>Version {escape(version)}. Everything runs on this computer; "
            "nothing about a return is sent anywhere.</p>" + body + "</body></html>")


def make_server(folder: Path, port: int = 0, loop=None, model_factory=None, gateway=None,
                on_folder=None, stop_when_page_closed: bool = False, ask_first: bool = False):
    """(server, url). The URL carries the launch token; serve with `server.serve_forever()`.
    With `ask_first` (the packaged app), `folder` is only the page's suggestion: nothing is
    created or read there until the person confirms a folder.
    With `stop_when_page_closed` (the packaged app), the server stops itself once its page is gone
    (page_watch.py); `server.stop_reason` says why it stopped."""
    folder = Path(folder)
    if not ask_first:
        (folder / "input").mkdir(parents=True, exist_ok=True)
        (folder / "output").mkdir(parents=True, exist_ok=True)
    if loop is None:
        from .case import Case
        from .loop import IntakeLoop
        loop = IntakeLoop(Case())
    token = secrets.token_urlsafe(24)
    state = _State(folder, loop, model_factory, gateway, on_folder)
    # the folder this page starts on may already hold a return; a suggested folder is opened only
    # once the person confirms it (the page asks where to work before anything else)
    if not ask_first:
        state.reopen_folder()
    handler = _handler(state, token)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.stop_reason = None
    handler.expected_host = f"127.0.0.1:{server.server_address[1]}"
    if stop_when_page_closed:
        from .page_watch import PageWatch

        def stop(reason):
            server.stop_reason = reason
            server.shutdown()

        def busy():
            # a return being computed holds the page's lock; a model's check runs on its own
            return state.lock.locked() or state.check.get("status") == "running"

        state.page_watch = PageWatch(stop, busy)
        state.page_watch.start()
    return server, f"http://{handler.expected_host}/?t={token}"
