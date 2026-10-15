# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The intake loop: candidates confirmed, gaps asked in served words, answers parsed by
rule, and the confirmed case computed and filled by the unchanged core.

Order of turns: a conflict between readers first (the person names the value), then each
document's pending candidates in one confirmation, then the interview's first required question
(`interview.open_questions`, whose `ask`/`why` are the served wording, carried verbatim), then —
when nothing is open — `prepare_return`: COMPLETE with the served lines, or REFUSED with the
service's own refusals. Three things are derived rather than asked, each with its reason on the
record: the filer's row (a return always has one), the spouse's row on a joint return, and an
item's `person` when the return has exactly one filer. Dependents are asked once, as a count.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
from types import SimpleNamespace
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .answers import AnswerError, parse_answer
from .case import NOT_GIVEN, Candidate, Case, Evidence

# on this route nothing is removed from a page before it is read, so the
# interview's own explanation for `REMOVED_BEFORE_READING` fields ("names and taxpayer IDs are
# removed from every document before it is read") is false here. What IS true on this route: the
# page names the person, and the return never carries names, so which person it is gets asked.
INTAKE_WHY = {
    "person": "Your document names the person, but this return never carries names, so it is asked instead.",
}

DEPENDENTS = "dependents"      # an intake question, not a fact: how many dependent rows to add
DEPENDENTS_ASK = "How many dependents are on this return? Enter 0 if there are none."
DEPENDENTS_WHY = "Each dependent is then asked about in turn."

# Streams the service covers that no document added may still be on the return: each is asked once,
# as a count, only while no document has filled it. Each new row starts from its owner (`person`,
# derived when the return has one filer) or, for a group with no owner field, from its first
# required field in the interview's own words. Path `count:<group>` is an intake question, not a fact.
ANY = "any:"                    # "do you have any …?" — opens a stream, never a fact
MORE = "more:"                  # "…another?" — asked after each row this conversation added
TOPIC = "topic:"
ATTEST = "attest:"     # a form's own scope question, answered before its figures: "did this apply to you?" — a form this version
                                # does not read; a tick opens that form's own lines, never a fact
TYPED = "typed:"                # one of those lines: an engine input typed by the person
STREAM_ENTRIES = (
    ("rentals", "person",
     "Did you rent out any property in 2025?",
     "A property you rented out is asked about in turn — used for Schedule E and Form 1040 line 8.",
     "Do you have another rental property to add?"),
    ("schedule_c", "person",
     "Did you run a business on your own in 2025, the kind reported on Schedule C?",
     "Each business is asked about in turn — used for Schedule C and Form 1040 line 8.",
     "Do you have another business to add?"),
    ("ssa1099s", "person",
     "Do you have a Social Security or railroad retirement benefit statement (SSA-1099 or RRB-1099) to add?",
     "Each statement is asked about in turn — used for Form 1040 lines 6a and 6b.",
     "Do you have another benefit statement to add?"),
    ("g1099s", "person",
     "Do you have a Form 1099-G for unemployment compensation to add?",
     "Each form is asked about in turn — used for Schedule 1 line 7.",
     "Do you have another Form 1099-G to add?"),
    ("misc1099s", "person",
     "Do you have a Form 1099-MISC to add?",
     "Each form is asked about in turn — used for Schedule 1 line 8 and Schedule E royalties.",
     "Do you have another Form 1099-MISC to add?"),
    ("hsa_distributions", "person",
     "Do you have a Form 1099-SA (health savings account distributions) to add?",
     "Each form is asked about in turn — used for Form 8889.",
     "Do you have another Form 1099-SA to add?"),
    ("care_providers", "provider_type",
     "Did you pay anyone for child or dependent care in 2025?",
     "Each provider is asked about in turn — used for Form 2441.",
     "Do you have another care provider to add?"),
)
STREAM_GROUPS = frozenset(entry[0] for entry in STREAM_ENTRIES)

# Decided 2026-09-28: once the documents are read, "how many more of these forms?" — every
# form a person receives on paper (`layout.RECEIVED_FORMS`), each 0 until changed. A number above 0
# puts that many rows in the workbook to type the form into; the typed rows come back as answers
# through the one way a workbook comes in (`add_workbook`). Path `forms:<group>` is an intake
# question, never a fact. It answers the stream question for the groups it lists, so nothing is
# asked twice: a 0 is the "no", and a number above 0 means the rows come from the workbook.
FORMS = "forms:"
MORE_FORMS_MAX = 50


YES_NO = ("false", "true")             # a yes-or-no question offers No and Yes, never a blank box

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December")

_ITEM_PATH = __import__("re").compile(r"^([a-z_0-9]+)\[(\d+)\]\.[a-z_0-9]+$")


def choices_for_fact(fact: str):
    """What a question offers instead of an empty box: the schema's own codes, No and Yes for a
    yes-or-no question, and the twelve months by number for a month (a month was a box that
    refused anything but 1 to 12, which a person had to guess)."""
    from ..client.interview import choices_for
    field = fact.rsplit(".", 1)[-1]
    if field == "birth_month":
        return [str(n) for n in range(1, 13)]
    offered = choices_for(field)
    if offered:
        return offered
    return list(YES_NO) if _is_boolean_field(fact) else None


def _is_boolean_field(fact: str) -> bool:
    from ..intake.answers import _SPECS
    spec = _SPECS.get(fact.rsplit(".", 1)[-1]) or {}
    return spec.get("type") == "boolean"


def _checkbox_label(question) -> str:
    """A tick box carries the question's OWN served words. An earlier cut rewrote them into
    statements and mangled the ones that do not start with their verb ("At any time during the
    year, did you …" became "Receive …"), and a person who meets the same fact twice must meet the
    same sentence twice."""
    return question.ask or question.fact


# Where a question touches who a person is — their birth date, their taxpayer-ID
# type — the fact is stated where it is asked. The answer goes into the return on this computer
# and nowhere else; the identity boxes the filled forms need are asked at the end, the same way.
STAYS_LOCAL = "Your answer stays on this computer and is not sent anywhere."
BIRTH_DATE = "birth_date"             # one date on the page; the facts keep its month and year
RESIDENCE_STATE = "residence_state"   # proposed from W-2 box 15, then confirmed


def parse_birth_date(text: str, tax_year: int = 2025) -> tuple[int, int, int]:
    """`(year, month, day)` from a date typed or picked — `1985-06-15`, `6/15/1985`.

    The DAY is kept, on this computer. It is still not a fact — the fact schema
    holds a month and a year and can hold no birth day — so the case keeps it beside
    the facts and it reaches the engine through the in-process seam, never a request."""
    import datetime
    import re as _re
    typed = (text or "").strip()
    iso = _re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", typed)
    us = _re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", typed)
    if iso:
        year, month, day = (int(g) for g in iso.groups())
    elif us:
        month, day, year = (int(g) for g in us.groups())
    else:
        raise AnswerError("Must be a date, like 1985-06-15")
    try:
        datetime.date(year, month, day)
    except ValueError:
        raise AnswerError("Must be a real date")
    if not 1900 <= year <= tax_year:
        raise AnswerError(f"Must be a year between 1900 and {tax_year}")
    return year, month, day
_LOCAL_NOTE_FIELDS = frozenset({"birth_year", "birth_month", "tin_type"})


def _with_local_note(path: str | None, why: str | None) -> str | None:
    if path and path.rsplit(".", 1)[-1] in _LOCAL_NOTE_FIELDS:
        return f"{why} {STAYS_LOCAL}".strip() if why else STAYS_LOCAL
    return why


_YES = frozenset({"true", "t", "yes", "y", "1"})
_NO = frozenset({"false", "f", "no", "n", "0"})


def _yes(reply) -> bool:
    return reply is True or (isinstance(reply, str) and reply.strip().lower() in _YES)


def _no(reply) -> bool:
    return reply is False or (isinstance(reply, str) and reply.strip().lower() in _NO)


@dataclass
class Turn:
    id: str
    kind: str                          # "confirm" | "question" | "complete" | "refused"
    path: str | None = None
    ask: str | None = None
    why: str | None = None
    choices: list | None = None
    candidates: list | None = None
    lines: dict | None = None
    refusals: list | None = None
    optional: bool = False             # an invitation with a stated default: a blank reply keeps it
    rows: int | None = None            # on an "any/another?" turn: rows this stream already holds
    missing: list | None = None        # on the workbook wait: each counted form whose rows are empty
    items: list | None = None          # on a checklist: [{"path", "label"}], all answered at once
    answers: list | None = None        # on the review: what was answered, in the words asked
    computed_at: str | None = None     # on a complete turn: when these figures were computed
    typed: list | None = None          # on a complete turn: the lines the person typed, said


def _why_here(q) -> str:
    """The question's `why` as it is true on this route: a field the interview explains as
    "removed before reading" gets this route's own clause, with the interview's line clause kept."""
    words = INTAKE_WHY.get(q.field)
    if words is None:
        return q.why
    lines = [line for _form, line in (q.consumed_by or [])]
    where = (f"It is used to compute Form 1040 line(s) {', '.join(lines)}." if lines
             else "It is needed to build the return.")
    return f"{words} {where}"


def _dollars(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    whole, part = divmod(abs(int(cents)), 100)
    return f"{sign}{whole}.{part:02d}"


def _now_words() -> str:
    """The local clock, as a person reads it: `2026-09-15 10:42`."""
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


class WorkbookNotTaken(Exception):
    """A workbook this page will not take, said in one sentence a person can act on."""


def _flatten_facts(facts: dict) -> dict:
    """`{path: value}` — roots, and `group[i].field` for every item field, the shape the case's
    answers are keyed by."""
    out = {}
    for key, value in (facts or {}).items():
        if isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    for field, v in item.items():
                        out[f"{key}[{i}].{field}"] = v
        elif not isinstance(value, dict):
            out[key] = value
    return out


def facts_hash(facts: dict) -> str:
    """One value for a set of answers, so a workbook read back can be told from the one written.
    A hash, never a figure."""
    flat = _flatten_facts({k: v for k, v in (facts or {}).items() if k != "tax_year"})
    return hashlib.sha256(json.dumps(flat, sort_keys=True, default=str).encode("utf-8")).hexdigest()


# a Yes / No on a form's card that starts unchosen — the forms-not-read page's own shape.
CARD_CHOICES = ("", "false", "true")
CARD_CHOICE_LABELS = ("Choose…", "No", "Yes")


class IntakeLoop:
    def __init__(self, case: Case, ops=None, model=None, pdf_root=None, reader=None):
        self.case = case
        if ops is None:
            from ..service import Operations
            ops = Operations()
        self.ops = ops
        self.model = model
        # the running page reads with build's printed-box lists, from the engine home
        # on this computer. A caller that names a root keeps it; none named means the pin's own.
        if pdf_root is None:
            from .registers import pin_pdf_root
            pdf_root = pin_pdf_root()
        self.pdf_root = pdf_root
        self._reader = reader
        self.documents: list = []
        self._counts: dict = {}
        self._ids = itertools.count(1)
        self._dependents_asked = False
        self._declined: set = set()        # optional questions answered with a blank
        self._checked: set = set()         # facts answered on a checklist page, asked once
        self._reviewed = False             # the answers were shown once before the figures
        self._topics_asked = False         # the forms-not-read checklist, asked once
        self._topics_ticked: list = []     # …and what was ticked, in the list's own order
        self._closed: set = set()          # stream groups the person said they had no more of
        self._stubs: dict = {}             # group -> a row promised by a yes, not yet started
        self.last_envelope = None
        self.computed_at: str | None = None     # when the figures on the screen were computed
        self.filled_for: str | None = None      # the return's fingerprint when the forms were last filled
        self.workbook_for: str | None = None    # the answers return-workbook.xlsx was written from
        self.workbook_declined: str | None = None   # an edited workbook the person said not to use
        self._more_forms_asked = False     # the "how many more of these forms?" page, asked once
        self._more_forms: dict = {}        # group -> how many more the person said they have
        self._more_taken = False           # a workbook was taken since those rows were written
        self.more_workbook: str | None = None   # where the workbook with those rows was written
        self.workbook_dir = None           # the output folder; the page sets it, never the corpus

    # ------------------------------------------------------------------ documents
    def read_only(self, pdf: Path):
        """Read a document WITHOUT taking it into the return. The page reads first and asks second
        where a form looks like one already read: a figure must not enter the return
        and then have to be taken back out of it."""
        reader = self._reader
        if reader is None:
            from .readers.documents import read_document as reader
        return reader(Path(pdf), 0, model=self.model, pdf_root=self.pdf_root)

    def add_document(self, pdf: Path):
        return self.attach(self.read_only(pdf))

    def add_workbook(self, data: bytes, name: str = "workbook.xlsx"):
        """The other way in (2026-09-22): a person who would rather fill the
        SPREADSHEET than answer questions gives it back here, and what they wrote becomes their
        answers. The same workbook this page writes, read by the same shipped reader
        (`client.workbook.read_workbook`) the desktop client has always used — one reader, so a
        figure means the same thing whichever way it arrived.

        A cell is an ANSWER, not a candidate: nobody read it off a document, the person typed it,
        and the summary already lists every answer with a control to change it. Nothing enters the
        return unless the WHOLE file reads: a value the reader will not swear to is refused by
        name and this workbook is not taken."""
        from ..client.workbook.reader import WorkbookRefused, read_workbook
        try:
            read = read_workbook(data)
        except WorkbookRefused as why:
            raise WorkbookNotTaken(f"{name} is not this return's workbook: {why}")
        if read.refusals:
            named = "; ".join(str(r) for r in read.refusals[:4])
            more = f" (and {len(read.refusals) - 4} more)" if len(read.refusals) > 4 else ""
            raise WorkbookNotTaken(
                f"{name} has {len(read.refusals)} cell(s) this reader will not guess at: {named}"
                f"{more}. Nothing from it was used — correct those cells and add it again.")
        from ..client.form_labels import label_for
        from ..client.interview import PROMPTS
        answered = 0
        for path, value in sorted(_flatten_facts(read.facts).items()):
            if path == "tax_year":
                continue                       # the folder's own year, asked before anything is read
            field = path.rsplit(".", 1)[-1]
            group = path.split("[", 1)[0] if "[" in path else None
            words = (label_for(group, field) if group else None) or PROMPTS.get(field) or field
            self.case.answer(path, value, f"{words} — from {name}")
            answered += 1
        record = SimpleNamespace(document=name, form_type="workbook", group=None, unconsumed=None,
                                 not_carried=[], vocabulary="workbook", index=None,
                                 digest=hashlib.sha256(data).hexdigest(), content=None,
                                 work_state=None, work_state_evidence=None, candidates=[],
                                 unread=[], answered=answered,
                                 # `read` is the one name the page's list and the saved session ask
                                 # for; for a workbook it counts answers, not boxes read
                                 read=answered)
        self.documents.append(record)
        self._reviewed = False
        if any(self._more_forms.values()):
            self._more_taken = True        # from here on, a counted row still empty is named
        return record

    def attach(self, result):
        """Take a read into the return: its figures become candidates a person confirms."""
        if result.group:
            n = self._counts.get(result.group, 0)
            self._counts[result.group] = n + 1
            try:
                result.index = n               # which row of its group this document became
            except AttributeError:
                pass
            first = f"{result.group}[0]."
            for cand in result.candidates:
                path = (f"{result.group}[{n}]." + cand.path[len(first):]
                        if cand.path.startswith(first) else cand.path)
                self.case.propose(Candidate(path, cand.value, cand.evidence))
        self.documents.append(result)
        # A new document changes the return: its figures, and the questions they raise, are shown
        # with the answers before anything is computed — as a workbook's already were. Without
        # this a return reviewed once went straight to its figures (seen 2026-09-22).
        self._reviewed = False
        return result

    def fingerprint(self) -> str:
        """One value for everything the figures are computed from, so filled forms can be told
        apart from the return they were filled for (figures carry when they were computed; so do
        the forms). A hash, never a figure."""
        body = json.dumps({"tax_year": self.case.tax_year, "facts": self._facts(),
                           "typed": self.case.typed() or {},
                           "birth_days": {str(k): v for k, v in (self.case.birth_days() or {}).items()}},
                          sort_keys=True, default=str)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------ turns
    def _id(self) -> str:
        return f"t{next(self._ids)}"

    def _facts(self) -> dict:
        return {k: v for k, v in self.case.facts().items() if k != "tax_year"}

    def next_turn(self) -> Turn:
        conflicts = self.case.conflicts()
        if conflicts:
            path = conflicts[0]
            cands = self.case.pending()[path]
            return Turn(self._id(), "confirm", path=path, candidates=cands,
                        ask=f"Two readings of {cands[0].evidence.caption} disagree. Which is on the paper?")
        pending = self.case.pending()
        if pending:
            document = next(iter(pending.values()))[0].evidence.document
            cands = [c for group in pending.values() for c in group if c.evidence.document == document]
            return Turn(self._id(), "confirm", candidates=cands,
                        ask=f"Check the figures read from {document}.",
                        items=self._document_asks(cands))
        turn = self._state_proposal()
        if turn is not None:
            return turn
        turn = self._employer_page()
        if turn is not None:
            return turn
        # after the documents' own pages, before the questions: a W-2 typed into the workbook
        # comes back through the employer page above, like one read
        turn = self._more_forms_turn()
        if turn is not None:
            return turn
        turn = self._next_question()
        if turn is not None:
            return turn
        turn = self._topic_turn()            # after everything the service asks, before the review
        if turn is not None:
            return turn
        if not self._reviewed:
            return self._review_turn()
        env = self.ops.prepare_return({"facts": self._facts(), "tax_year": self.case.tax_year},
                                      engine_extras=self.case.typed() or None,
                                      birth_days=self.case.birth_days() or None)
        self.last_envelope = env
        result = env["result"]
        if result["outcome"] == "complete":
            lines = {line["line_id"]: line["value_cents"] for line in result["forms"][0]["lines"]}
            # Figures carry the moment they were computed, so a return on the
            # screen is never mistaken for one from another day or another set of documents.
            self.computed_at = _now_words()
            return Turn(self._id(), "complete", lines=lines, computed_at=self.computed_at,
                        typed=self.typed_statement() or None)
        if result["outcome"] in ("refused", "knocked_out"):
            # A knockout is a refusal the dictionary names; both end the conversation the same way.
            return Turn(self._id(), "refused", refusals=env.get("refusals") or result.get("refusals") or [])
        gaps = result.get("gaps") or []
        if gaps:
            gap = gaps[0]
            return Turn(self._id(), "question", path=gap["fact"], ask=gap.get("why"), why=gap.get("why"))
        return Turn(self._id(), "refused", refusals=[{"boundary": (
            "The return is not complete, and the service named nothing further to ask.")}])

    MORE_FORMS_ASK = ("Do you have any more of these forms to add? Enter how many of each; 0 means "
                      "none.")
    MORE_FORMS_WHY = ("Each number above 0 adds that many rows to a workbook in your output folder, "
                      "to type that form's boxes into. The figures you type there are used for this "
                      "return.")
    MORE_FORMS_WAIT_WHY = ("This page goes on once the saved workbook is used for your answers: it "
                           "asks when you come back to it. To add fewer forms, change the numbers "
                           "below.")
    MORE_FORMS_EMPTY = "Fill the rest and save the workbook again, or change the number below."
    MORE_FORMS_TYPED = ("This return has lines you typed for a form this version does not read, and "
                        "in this version those cannot be on one return with forms typed into the "
                        "workbook. Enter 0 for each form to keep the typed lines.")
    TYPED_MORE_FORMS = ("This return has forms typed into the workbook, and in this version those "
                        "cannot be on one return with the lines of a form this version does not "
                        "read. Leave these unticked to keep the workbook's forms.")

    def _documents_read(self) -> list:
        return [d for d in self.documents if getattr(d, "form_type", None) != "workbook"]

    def _form_words(self, group: str) -> str:
        from ..client.workbook.layout import RECEIVED_FORMS
        return dict(RECEIVED_FORMS)[group]

    def _missing_rows(self) -> list:
        """`(group, count, filled)` for each counted form whose rows the return does not hold yet:
        the documents read of that form plus the count, against the rows there are."""
        rows = self._facts()
        out = []
        for group, count in self._more_forms.items():
            if count <= 0:
                continue
            filled = len(rows.get(group) or []) - self._counts.get(group, 0)
            if filled < count:
                out.append((group, count, max(filled, 0)))
        return out

    def _more_forms_turn(self):
        """Once the documents are read (decided 2026-09-28): how many more of each form, each
        0 until changed; then, while a counted form's rows are not in the return, the page waits
        for the workbook they are typed into. Asked only of a return some document was read into:
        with none read, the page's own questions are the way in, as before."""
        if not self._documents_read():
            return None
        from ..client.workbook.layout import RECEIVED_FORMS
        if not self._more_forms_asked:
            items = []
            for group, words in RECEIVED_FORMS:
                read = self._counts.get(group, 0)
                label = (f"{words} — how many more, beyond the {read} read" if read
                         else f"{words} — how many")
                items.append({"path": FORMS + group, "label": label, "type": "count", "value": "0"})
            return Turn(self._id(), "more_forms", items=items, ask=self.MORE_FORMS_ASK,
                        why=self.MORE_FORMS_WHY)
        missing = self._missing_rows()
        if not missing:
            return None
        items = [{"path": FORMS + group, "label": f"{self._form_words(group)} — how many",
                  "type": "count", "value": str(count)}
                 for group, count in self._more_forms.items() if count > 0]
        named = None
        if self._more_taken:
            # the person said they had N; the workbook came back with fewer — said, never dropped
            named = [f"{self._form_words(group)}: you said {count}, and the workbook has {filled} "
                     f"filled in." for group, count, filled in missing] + [self.MORE_FORMS_EMPTY]
        where = self.more_workbook or "the output folder"
        return Turn(self._id(), "workbook_wait", items=items, missing=named,
                    ask=(f"The workbook is ready: {where}. Open it, type each form's boxes into "
                         f"its rows, and save it."),
                    why=self.MORE_FORMS_WAIT_WHY)

    def _counts_given(self, turn, reply, most=None) -> dict:
        """Each count on the page, a whole number; parsed in full before anything changes."""
        given = reply if isinstance(reply, dict) else None
        if given is None:
            raise AnswerError("Enter a number for each form, then send the page")
        known = {i["path"] for i in turn.items or []}
        if [p for p in given if p not in known]:
            raise AnswerError("That is not one of the boxes on this page")
        out = {}
        for item in turn.items or []:
            raw = given.get(item["path"])
            text = "0" if raw is None or str(raw).strip() == "" else str(raw).strip()
            if not text.isdigit():
                raise AnswerError(f'"{item["label"]}": "{text}" is not a whole number')
            top = MORE_FORMS_MAX if most is None else most[item["path"]]
            if int(text) > top:
                raise AnswerError(f'"{item["label"]}": must be between 0 and {top}')
            out[item["path"][len(FORMS):]] = int(text)
        return out

    def _write_more_forms(self, counts: dict) -> None:
        """The workbook with a row per counted form, written where a fill writes it."""
        from ..client.workbook.reader import read_workbook
        from . import workbook_out
        if self.workbook_dir is None:
            raise AnswerError("No output folder is chosen, so the workbook cannot be written")
        try:
            path = workbook_out.write_added(self._facts(), self.case.tax_year, self.workbook_dir,
                                            {g: n for g, n in counts.items() if n > 0})
        except OSError as why:
            raise AnswerError(f"The workbook could not be written in {self.workbook_dir}: {why}. "
                              f"If it is open, close it, then send this page again.")
        self.more_workbook = str(Path(path).resolve())
        # what the file SAYS, read back: an untouched workbook is not "edited"
        self.workbook_for = facts_hash(read_workbook(Path(path).read_bytes()).facts)

    def _state_proposal(self):
        """The residence state, proposed from W-2 box 15 and confirmed by the person (s-state-from-w2).

        Box 15 names the state an employer reported the wages to, which is not always where the
        person lived, so the reading is never a fact: it is a `Candidate` the turn carries, proposed
        and confirmed together when the person answers (keeping it, or choosing another state). It
        is offered only while the question is unanswered and only when every document that names a
        state names the same one; two W-2s naming two states propose nothing, and the question is
        asked as before. The candidate is built here rather than held pending in the case, so a
        document added before the answer is weighed too."""
        if RESIDENCE_STATE in self.case.confirmed():
            return None
        named = [d for d in self.documents if getattr(d, "work_state", None)]
        if not named or len({d.work_state for d in named}) != 1:
            return None
        from ..client.interview import PROMPTS, choice_words
        first = named[0]
        state = first.work_state
        e = first.work_state_evidence
        where = (e.document, e.page, e.rect, e.raw, e.tier) if e is not None else (first.document, 1, None, state.upper(), "geometry")
        # The caption is the question itself: a state the person changes is listed among their
        # answers in the words it is asked in cold.
        evidence = Evidence(where[0], where[1], PROMPTS[RESIDENCE_STATE], where[2], where[3], where[4])
        words = (choice_words(RESIDENCE_STATE) or {}).get(state, state)
        return Turn(self._id(), "confirm", path=RESIDENCE_STATE,
                    candidates=[Candidate(RESIDENCE_STATE, state, evidence)],
                    choices=choices_for_fact(RESIDENCE_STATE),
                    ask=(f"Box 15 of Form W-2 ({evidence.document}) names {words}. Which U.S. state, "
                         f"or the District of Columbia, did you live in and earn income in during "
                         f"the year?"),
                    why=(f"{words} is proposed from that box, which names the state the wages were "
                         f"reported to, not always where you lived. Keep it or choose another."))

    def _employer_page(self):
        """More than one Form W-2 for one person: which of them came from the same employer.

        The mapper refuses a filer's second W-2 without `employer_ref` (the excess Social
        Security credit turns on having had more than one employer, and nothing else on a W-2 says
        so), and until now NOTHING asked it — the page read both forms, then served that refusal
        with its field names in it, and the person had no question to answer and no way on. The
        service holds no employer name, so each W-2 is named here the way the person can tell them
        apart: the document it was read from, and what its box 1 says.
        """
        facts = self._facts()
        rows = list(enumerate(facts.get("w2s") or []))
        # A W-2 whose person is not answered yet is the one filer's only where the return can have
        # no second filer — the same rule `_next_question` derives `person` by. On a joint return
        # it waits for "whose Form W-2 is this?": counted as the primary's, one W-2 each for a
        # couple was asked about as two employers of one person (profile-dependent-care, found by
        # the corpus the day this page shipped).
        status = facts.get("filing_status")
        filers = [p for p in facts.get("persons") or [] if p.get("role") in ("primary", "spouse")]
        one_filer = status is not None and status != "mfj" and len(filers) <= 1
        by_person: dict = {}
        for index, w2 in rows:
            if "person" not in w2 and not one_filer:
                continue
            by_person.setdefault(w2.get("person", 0), []).append((index, w2))
        for person, held in sorted(by_person.items()):
            if len(held) < 2:
                continue                       # one W-2: the credit cannot arise, nothing to ask
            first, first_row = held[0]
            if "employer_ref" not in first_row:
                # the first W-2 of this person starts the first employer; the labels are relative,
                # so this is a statement of how they are counted, not an answer about the paper
                self.case.derive(f"w2s[{first}].employer_ref", 0,
                                 "the first Form W-2 for this person starts the first employer")
                first_row["employer_ref"] = 0
            items = []
            for index, w2 in held[1:]:
                if "employer_ref" in w2:
                    continue
                choices = sorted({held[j][1].get("employer_ref") for j in range(len(held))
                                  if held[j][0] != index and held[j][1].get("employer_ref") is not None})
                labels = [f"The same employer as {self._w2_words(held, group)}" for group in choices]
                choices = [str(group) for group in choices]
                labels.append("A different employer")
                choices.append(str(max(int(c) for c in choices) + 1))
                items.append({"path": f"w2s[{index}].employer_ref",
                              "label": self._w2_words(held, None, index),
                              "type": "choice", "choices": choices, "labels": labels})
            if items:
                return Turn(self._id(), "checklist", items=items,
                            ask="You added more than one Form W-2 for this person. Which employer "
                                "is each of them from?",
                            why="A person who had more than one employer can be owed the excess "
                                "Social Security withholding credit — Schedule 3, line 11 — and a "
                                "person who had one employer cannot. This service holds no employer "
                                "name, so each Form W-2 is named by the document it was read from "
                                f"and what it shows in box 1. {STAYS_LOCAL}")
        return None

    def _w2_words(self, held, group, index=None) -> str:
        """One Form W-2 as a person can tell it apart: the document it came from and its box 1."""
        if index is None:
            index = next(i for i, w2 in held if w2.get("employer_ref") == group)
        confirmed = self.case.confirmed()
        wages = confirmed.get(f"w2s[{index}].wages_cents")
        document = wages[1].document if wages and wages[1].document else None
        # a person reads money with its separators and its sign; `_dollars` here is the fill's
        # review key format, which must not change
        cents = wages[0] if wages and isinstance(wages[0], int) else None
        amount = None if cents is None else f"${cents // 100:,}.{cents % 100:02d}"
        if document and amount:
            return f"the Form W-2 read from {document}, box 1 {amount}"
        if document:
            return f"the Form W-2 read from {document}"
        return f"Form W-2 number {index + 1}"

    def _next_question(self):
        from ..client.interview import open_questions
        for _ in range(8):                                   # each pass derives at most one row
            facts = self._facts()
            persons = facts.get("persons") or []
            filers = [i for i, p in enumerate(persons) if p.get("role") in ("primary", "spouse")]
            derived = False
            questions = list(open_questions(facts))
            checklist = self._checklist_turn(questions)
            if checklist is not None:
                return checklist
            person_page = self._person_page(questions)
            if person_page is not None:
                return person_page
            optional = self._optional_page(questions)
            if optional is not None:
                return optional
            for q in questions:
                if q.optional:
                    if q.fact in self._declined:
                        continue
                    return Turn(self._id(), "question", path=q.fact, ask=q.ask, why=q.why,
                                choices=q.choices or choices_for_fact(q.fact), optional=True)
                if q.fact == "persons":
                    if not persons:
                        self.case.derive("persons[0].role", "primary", "every return has a filer")
                        derived = True
                    elif facts.get("filing_status") == "mfj" and len(filers) < 2:
                        self.case.derive(f"persons[{len(persons)}].role", "spouse",
                                         "a joint return names the spouse")
                        derived = True
                    elif not self._dependents_asked:
                        return Turn(self._id(), "question", path=DEPENDENTS, ask=DEPENDENTS_ASK,
                                    why=DEPENDENTS_WHY)
                    else:
                        return Turn(self._id(), "question", path=q.fact, ask=q.ask, why=q.why)
                    break
                if q.fact in STREAM_GROUPS:
                    # a required gap can name a bare stream group (`care_providers`, once a
                    # qualifying person's expenses are answered) — the same group STREAM_ENTRIES
                    # already asks about count-first. Deferring to `_stream_turn` below asks it in
                    # the one shape a reply can answer (`count:<group>`, then each row), instead of
                    # a bare group path nothing in `respond` recognizes.
                    break
                if q.field == "person" and len(filers) == 1 and facts.get("filing_status") != "mfj":
                    self.case.derive(q.fact, filers[0], "the one filer on this return")
                    derived = True
                    break
                return Turn(self._id(), "question", path=q.fact, ask=q.ask,
                            why=_with_local_note(q.fact, _why_here(q)),
                            choices=q.choices or choices_for_fact(q.fact))
            if derived:
                continue
            if persons and not self._dependents_asked:
                return Turn(self._id(), "question", path=DEPENDENTS, ask=DEPENDENTS_ASK, why=DEPENDENTS_WHY)
            turn = self._stream_turn(facts, filers)
            if turn == "derived":
                continue
            return turn
        return None

    CHECKLIST_ASK = ("Tick everything that applied to you in 2025. Anything you leave unticked is "
                     "answered no.")
    CHECKLIST_WHY = ("These are the yes-or-no questions this return asks of everyone. Each one is "
                     "a line or a checkbox on the return; you can change any of them later.")

    OPTIONAL_ASK = ("Fill in anything below that applies to you. Leave the rest blank and it stays "
                    "as it is.")
    OPTIONAL_WHY = "Each one says what a blank answer means."

    def _optional_page(self, questions):
        """the invitations, on one page of fields instead of one screen each. A blank keeps
        the stated default, exactly as a blank reply to the single question did."""
        batch = [q for q in questions if q.optional and q.fact not in self._declined
                 and q.fact not in self._checked]
        if len(batch) < 2:
            return None
        items = [{"path": q.fact, "label": q.ask, "why": q.why, "type": "amount", "optional": True}
                 for q in batch]
        return Turn(self._id(), "checklist", ask=self.OPTIONAL_ASK, why=self.OPTIONAL_WHY, items=items)

    def _document_asks(self, candidates) -> list:
        """The yes-or-no boxes of the form being confirmed (by design: a W-2's own
        questions belong on the W-2's card). Same rows, same page: box 13's three checkboxes are
        answered where the figures from that W-2 are checked, not as separate turns afterwards."""
        from ..client.interview import NOT_ON_ANY_DOCUMENT, open_questions
        prefixes = {c.path.rsplit(".", 1)[0] for c in candidates if "[" in c.path}
        if not prefixes:
            return []
        # Ask as if these figures were already confirmed: until they are, the return holds no such
        # W-2 at all, so nothing about box 13 is open yet and the card would carry no boxes.
        facts = self._facts()
        for cand in candidates:
            match = _ITEM_PATH.match(cand.path)
            if match is None:
                continue
            group, index = match.group(1), int(match.group(2))
            rows = facts.setdefault(group, [])
            while len(rows) <= index:
                rows.append({})
            rows[index].setdefault(cand.path.rsplit(".", 1)[-1], cand.value)
        items = []
        for q in open_questions(facts):
            if q.optional or q.choices is not None or "[" not in q.fact:
                continue
            if q.fact.rsplit(".", 1)[0] in prefixes and _is_boolean_field(q.fact):
                if q.fact.rsplit(".", 1)[-1] in NOT_ON_ANY_DOCUMENT:
                    # an answer that is on no printed box. As a tick, left unticked it was a
                    # NO nobody gave; it stays on the card (fewer screens) as a Yes /
                    # No that starts unchosen, and the card waits for it.
                    items.append({"path": q.fact, "label": q.ask, "type": "choice",
                                  "choices": list(CARD_CHOICES), "labels": list(CARD_CHOICE_LABELS)})
                else:
                    items.append({"path": q.fact, "label": q.ask, "type": "tick"})
        return items

    def _person_page(self, questions):
        """Who this person is, asked once: the birth month by name, the birth year, and the kind of
        taxpayer ID — never its digits, and never a birth day, which is an identifier this service
        cannot hold (the birth date is asked in one place)."""
        wanted = ("birth_month", "birth_year", "tin_type")
        by_person: dict = {}
        for q in questions:
            match = _ITEM_PATH.match(q.fact)
            field = q.fact.rsplit(".", 1)[-1]
            if match is None or match.group(1) != "persons" or field not in wanted or q.optional:
                continue
            by_person.setdefault(int(match.group(2)), []).append((field, q))
        for index in sorted(by_person):
            found = dict(by_person[index])
            if len(found) < 2:
                continue
            items = []
            if "birth_month" in found or "birth_year" in found:
                # one date, not a month and a year asked apart
                items.append({"path": f"persons[{index}].{BIRTH_DATE}", "label": "Date of birth",
                              "type": "date"})
            if "tin_type" in found:
                q = found["tin_type"]
                from ..client.interview import CHOICES
                items.append({"path": f"persons[{index}].tin_type",
                              "label": "Kind of taxpayer ID (never its digits)", "type": "choice",
                              "choices": [c for c, _w in CHOICES["tin_type"]],
                              "labels": [w for _c, w in CHOICES["tin_type"]]})
            return Turn(self._id(), "checklist", items=items,
                        ask=f"About person {index + 1}.",
                        why=("This return is computed from the date of birth — the day decides a "
                             "line only where an age test falls on it, such as a child who turns 17 "
                             f"on January 1. {STAYS_LOCAL}"))
        return None

    def _checklist_turn(self, questions):
        """One page of tick boxes instead of a yes/no question each.

        Only questions that stand on their own are batched: a root yes-or-no this return asks of
        everyone, which nothing else in the batch gates. A follow-up (a gate behind an amount, a
        per-document box, a per-person answer) keeps its own turn, so nobody is asked something
        whose own question has not been answered yet."""
        from ..facts import mapper
        batch = [q for q in questions
                 if q.fact in mapper.EVERY_RETURN_ROOT_FIELDS and q.choices is None
                 and not q.optional and q.fact not in self._checked]
        batch = [q for q in batch if _is_boolean_field(q.fact)]
        items = [{"path": q.fact, "label": _checkbox_label(q), "type": "tick"} for q in batch]
        # The per-person yes/no answers belong on the same page, said of the person they are about
        # ("Is this person blind?" and the ones after it are tick boxes).
        for q in questions:
            if q.optional or q.choices is not None or q.fact in self._checked:
                continue
            match = _ITEM_PATH.match(q.fact)
            if match is None or match.group(1) != "persons" or not _is_boolean_field(q.fact):
                continue
            items.append({"path": q.fact, "type": "tick",
                          "label": f"Person {int(match.group(2)) + 1}: {_checkbox_label(q)}"})
        # The streams belong on the same page ("Do you have a Form 1099-G for…"
        # is a tick box, not a turn of its own). Only a stream nothing has opened yet: one a
        # document already filled is asked "another?" in its own turn, where the count is visible.
        facts = self._facts()
        for group, _first, ask_any, _why, _ask_more in STREAM_ENTRIES:
            if group in self._closed or self._stubs.get(group) or facts.get(group):
                continue
            items.append({"path": ANY + group, "label": ask_any})
        if len(items) < 2:
            return None
        return Turn(self._id(), "checklist", ask=self.CHECKLIST_ASK, why=self.CHECKLIST_WHY,
                    items=items)

    # Decided 2026-09-19: say the form is not accepted yet, and that the return
    # is still computed if the person chooses — with its lines typed in, or without the form.
    TOPICS_ASK = ("Did any of these apply to you in 2025? These are forms this version does not read "
                  "from a document — they are not accepted yet.")
    TOPICS_WHY = ("The return is still computed if you choose: tick a form to type its lines in, and "
                  "they are used; leave it unticked and the return is computed without that form.")
    TOPIC_WHY = ("These are lines of the form itself. Every line is answered — a no or a 0 is an "
                 "answer. To leave this form off the return after all, leave every line blank.")

    def _topic_turn(self):
        """The dictionary-driven fallback's first unit. Once the service has
        nothing left to ask: one checklist of the forms on the allow-list
        (`facts.fallback_topics`), then one page per ticked form carrying that form's own lines.
        A form is answered in full or not at all (`facts.extras`, rule 5), so every line on the
        page is required; a person who ticked one by mistake unticks it on the summary."""
        from ..facts import fallback_topics as topics
        # A form about ONE of something is offered only to a return that HAS one: with
        # no Schedule C there is nothing to attach a Form 8829 to.
        offered = topics.topics_for(self._facts())
        if not offered:
            return None
        if not self._topics_asked:
            items = [{"path": TOPIC + key, "label": f"{topic['label']} — {topic['form']}"}
                     for key, topic in offered.items()]
            return Turn(self._id(), "checklist", items=items, ask=self.TOPICS_ASK, why=self.TOPICS_WHY)
        typed = self.case.typed()
        for key in self._topics_ticked:
            topic = offered.get(key)
            if topic is None:
                continue
            rows = topics.rows_for(topic, self._facts())
            row = next((r for r in rows
                        if not all(topics.path_for(p, r) in typed for p in topic["writables"])), None)
            if row is None and rows != [None]:
                continue                      # every business is answered
            if rows == [None] and all(path in typed for path in topic["writables"]):
                continue
            items = []
            for name, att in (topic.get("attestations") or {}).items():
                # Before the figures, deliberately: a person who answers one of these the other way
                # is not asked for ten amounts this version would then refuse to use.
                items.append({"path": ATTEST + f"{key}.{name}" + ("" if row is None else f".{row}"),
                              "label": att["ask"],
                              "why": att["rule"], "optional": False, "type": "choice",
                              "choices": ["", *YES_NO], "labels": ["Choose…", "No", "Yes"]})
            for path, entry in topic["writables"].items():
                item = {"path": TYPED + topics.path_for(path, row), "label": entry["ask"],
                        "optional": False}
                if entry["kind"] == topics.BOOLEAN:
                    # no answer chosen for the person: a dropdown's first option is what an
                    # untouched one sends, and a line nobody answered is refused, not a No
                    item.update(type="choice", choices=["", *YES_NO], labels=["Choose…", "No", "Yes"])
                elif entry["kind"] == topics.INT:
                    item.update(type="text", whole_number=True)
                else:
                    item.update(type="amount")
                items.append(item)
            ask = topic["form"] if row is None else f"{topic['form']} — business {row + 1}"
            return Turn(self._id(), "checklist", items=items, ask=ask, why=self.TOPIC_WHY)
        return None

    def _answer_typed(self, path: str, text: str, label: str) -> None:
        """One typed line, parsed as its form line's kind; refused in the copy rules' formulas."""
        from ..facts import fallback_topics as topics
        from ..facts.extras import _offered_form
        _key, entry = topics.offered_writables()[_offered_form(path)]
        raw = text.strip()
        if entry["kind"] == topics.BOOLEAN:
            if raw.lower() not in YES_NO:
                raise AnswerError(f'"{label}" is answered yes or no')
            value = raw.lower() == "true"
        elif entry["kind"] == topics.INT:
            if not raw.isdigit():
                raise AnswerError(f'"{label}": "{raw}" is not a whole number')
            value = int(raw)
        else:
            amount = raw.replace("$", "").replace(",", "").strip()
            if not re.fullmatch(r"\d+(?:\.\d{1,2})?", amount):
                raise AnswerError(f'"{label}": "{raw}" is not an amount')
            value = int(Decimal(amount) * 100)
        low, high = entry.get("min", 0), entry.get("max")
        scale = 100 if entry["kind"] == topics.DOLLAR else 1
        if entry["kind"] != topics.BOOLEAN and (value < low * scale or (high is not None and value > high * scale)):
            raise AnswerError(f'"{label}": must be between {low} and {high}' if high is not None
                              else f'"{label}": must be {low} or more')
        self.case.type_in(path, value, label)

    def _review_turn(self):
        """Everything answered, shown once before the figures are computed."""
        return Turn(self._id(), "review", ask="Check your answers before the figures are computed.",
                    why="Change anything that is not what you meant; nothing is sent anywhere.",
                    answers=self.answers())

    def _stream_turn(self, facts: dict, filers: list):
        """A stream is opened by a yes, one row at a time, and closed by a no (by
        design: "do you have rental properties", then "do you have more"). Nobody is asked to
        count forms they have not looked at yet. A stream whose rows a document already created is
        never asked whether it has any — only whether there is another."""
        from ..client.interview import GROUP_PROMPTS, PROMPTS, choices_for
        for group, first, _ask_any, _why, _ask_more in STREAM_ENTRIES:
            if not self._stubs.get(group):
                continue
            index = len(facts.get(group) or [])
            path = f"{group}[{index}].{first}"
            if first == "person" and len(filers) == 1 and facts.get("filing_status") != "mfj":
                self.case.derive(path, filers[0], "the one filer on this return")
                self._stubs[group] = 0
                return "derived"
            ask = GROUP_PROMPTS.get((group, first)) or PROMPTS.get(first) or f"What is {first}?"
            return Turn(self._id(), "question", path=path, ask=ask,
                        why="This starts the row your last answer added.",
                        choices=choices_for(first) or choices_for_fact(path))
        for group, _first, ask_any, why, ask_more in STREAM_ENTRIES:
            if self._stream_done(group):
                continue
            rows = len(facts.get(group) or [])
            if rows:                      # a document already added one: only "another?" is honest
                return Turn(self._id(), "question", path=MORE + group, ask=ask_more, why=why,
                            rows=rows, choices=list(YES_NO))
            return Turn(self._id(), "question", path=ANY + group, ask=ask_any, why=why, rows=0,
                        choices=list(YES_NO))
        return None

    def _stream_done(self, group: str) -> bool:
        return group in self._closed

    def respond(self, turn: Turn, reply) -> None:
        if turn.kind == "more_forms":
            counts = self._counts_given(turn, reply)
            if any(counts.values()):
                if self.case.typed():
                    raise AnswerError(self.MORE_FORMS_TYPED)
                self._write_more_forms(counts)
            self._more_forms = counts
            self._more_forms_asked = True
            self._more_taken = False
            for group in counts:
                if group in STREAM_GROUPS:
                    # asked here, so never again as its own question: 0 is the no, and a number
                    # above 0 is rows that come from the workbook
                    self._closed.add(group)
                    self._stubs[group] = 0
            self._reviewed = False
            return
        if turn.kind == "workbook_wait":
            most = {i["path"]: int(i["value"]) for i in turn.items or []}
            counts = self._counts_given(turn, reply, most)
            self._more_forms.update(counts)
            return
        if turn.kind == "checklist":
            # A tick is a yes; everything left unticked is the no the page said it would be. A page
            # of fields sends a value per path instead, and a blank keeps the stated default.
            given = reply if isinstance(reply, dict) else None
            if given is None:
                if not isinstance(reply, (list, tuple, set)):
                    raise AnswerError("Tick the ones that apply, then send the page")
                given = {str(p): True for p in reply}
            known = {i["path"] for i in (turn.items or [])}
            unknown = [p for p in given if p not in known]
            if unknown:
                raise AnswerError("That is not one of the boxes on this page")
            if any(i["path"].startswith(TOPIC) for i in (turn.items or [])):
                # the forms-not-read checklist — a tick opens that form's lines
                ticked = [i["path"][len(TOPIC):] for i in turn.items
                          if given.get(i["path"]) is True
                          or (isinstance(given.get(i["path"]), str) and _yes(given[i["path"]]))]
                if ticked and any(self._more_forms.values()):
                    raise AnswerError(self.TYPED_MORE_FORMS)
                self._topics_ticked = ticked
                self._topics_asked = True
                self._reviewed = False
                return
            if any(i["path"].startswith(TYPED) for i in (turn.items or [])):
                # …and one form's lines: every one answered, parsed first so a bad line changes nothing
                blank = [i for i in turn.items
                         if given.get(i["path"]) is None or not str(given.get(i["path"])).strip()]
                if len(blank) != len(turn.items):
                    # The form's own scope questions, answered before its figures are looked at: a
                    # person who answers one the other way is told why in that form's own words,
                    # and the page stays open. Left entirely blank the page still means "not this
                    # form after all", which is the branch below — so this runs only when something
                    # was filled in.
                    from ..facts import fallback_topics as topics
                    for item in turn.items:
                        if not item["path"].startswith(ATTEST):
                            continue
                        key, name = item["path"][len(ATTEST):].split(".")[:2]
                        att = topics.TOPICS[key]["attestations"][name]
                        answer = str(given.get(item["path"]) or "").strip().lower()
                        if answer not in YES_NO:
                            raise AnswerError(f'"{item["label"]}" is answered yes or no')
                        if (answer == "true") is not att["must_be"]:
                            raise AnswerError(att["refusal"])
                if len(blank) == len(turn.items):
                    # EVERY line blank is "not this form after all" — the way back for a form ticked
                    # by mistake: this page comes before the summary, so without it a person who
                    # mis-ticked could never finish. The form and anything typed under it come off.
                    from ..facts import fallback_topics as topics
                    offered = topics.offered_writables()
                    from ..facts.extras import _offered_form
                    keys = {offered[_offered_form(i["path"][len(TYPED):])][0] for i in turn.items
                            if i["path"].startswith(TYPED)}
                    self._topics_ticked = [k for k in self._topics_ticked if k not in keys]
                    for key in keys:
                        # every row's spelling of this form's lines, not just the return's own
                        self.case.untype([topics.path_for(p, r)
                                          for p in topics.TOPICS[key]["writables"]
                                          for r in topics.rows_for(topics.TOPICS[key], self._facts())])
                    self._reviewed = False
                    return
                if blank:
                    raise AnswerError(f'"{blank[0]["label"]}" is required')
                staged = Case(self.case.tax_year)
                keep, self.case = self.case, staged
                try:
                    for item in turn.items:
                        if not item["path"].startswith(TYPED):
                            continue          # a scope question, already answered above
                        self._answer_typed(item["path"][len(TYPED):], str(given[item["path"]]), item["label"])
                finally:
                    self.case = keep
                for path, (value, words) in staged.typed_with_words().items():
                    self.case.type_in(path, value, words)
                self._reviewed = False
                return
            for item in turn.items or []:
                path, value = item["path"], given.get(item["path"])
                if item.get("type") == "date":
                    typed = "" if value is None else str(value).strip()
                    if not typed:
                        raise AnswerError(f'"{item["label"]}" is required')
                    self._answer_birth_date(path, typed, item["label"])
                    continue
                if item.get("type") in ("amount", "text", "choice"):
                    typed = "" if value is None else str(value).strip()
                    if not typed:
                        if not item.get("optional", item.get("type") == "amount"):
                            raise AnswerError(f'"{item["label"]}" is required')
                        self._declined.add(path)          # the stated default stands
                    else:
                        self.case.answer(path, parse_answer(path, typed), item["label"])
                        self._checked.add(path)
                    continue
                ticked = value is True or (isinstance(value, str) and _yes(value))
                if path.startswith(ANY):                  # a stream: a tick opens it, a blank closes it
                    group = path[len(ANY):]
                    if ticked:
                        self._stubs[group] = 1
                    else:
                        self._closed.add(group)
                    continue
                self.case.answer(path, ticked, item["label"])
                self._checked.add(path)
            return
        if turn.kind == "review":
            self._reviewed = True
            return
        if turn.kind == "confirm" and turn.path == RESIDENCE_STATE and turn.choices:
            # the proposal from box 15: the person keeps it or names another state
            value = reply.get(turn.path) if isinstance(reply, dict) else reply
            chosen = parse_answer(turn.path, "" if value is None else str(value))
            # Recorded as the person's ANSWER even when they keep the proposal: they picked it from
            # the question's own list, and an answer is what the summary lists with a control to
            # change it — a later W-2 naming another state must not leave a state
            # nobody can change without starting over.
            from ..client.interview import PROMPTS
            self.case.answer(turn.path, chosen, PROMPTS[RESIDENCE_STATE])
            return
        if turn.kind == "confirm":
            corrections = dict(reply) if isinstance(reply, dict) else {}
            answers = {}
            for item in turn.items or []:                 # the form's own yes/no boxes, same card
                value = corrections.pop(item["path"], None)
                if item.get("type") == "choice":
                    # a question, not a printed box — nothing is recorded from this card
                    # until every one of them is chosen.
                    text = "" if value is None else str(value).strip().lower()
                    if value is not True and value is not False and not (_yes(text) or _no(text)):
                        raise AnswerError("Choose Yes or No for each question on this form")
                    answers[item["path"]] = value is True or (value is not False and _yes(text))
                else:
                    answers[item["path"]] = value is True or (isinstance(value, str) and _yes(value))
            for item in turn.items or []:
                self.case.answer(item["path"], answers[item["path"]], item["label"])
                self._checked.add(item["path"])
            if turn.path is not None and turn.path not in corrections:
                raise AnswerError("Name the value that is on the paper")
            for path in dict.fromkeys(c.path for c in turn.candidates):
                if path in self.case.pending():
                    self.case.confirm(path, corrections.get(path, NOT_GIVEN))
            return
        if turn.kind != "question":
            raise AnswerError("There is nothing to answer")
        if turn.path and (turn.path.startswith(ANY) or turn.path.startswith(MORE)):
            group = turn.path.split(":", 1)[1]
            if _yes(reply):
                self._stubs[group] = 1
            elif _no(reply):
                self._closed.add(group)
            else:
                raise AnswerError("Must be true or false")
            return
        stub = next((g for g, first, _a, _w, _m in STREAM_ENTRIES
                     if self._stubs.get(g) and turn.path and turn.path.startswith(f"{g}[")
                     and turn.path.endswith(f".{first}")), None)
        if turn.path == DEPENDENTS:
            text = str(reply).strip()
            if not text.isdigit():
                raise AnswerError(f'"{text}" is not a whole number')
            base = len(self._facts().get("persons") or [])
            for k in range(int(text)):
                self.case.derive(f"persons[{base + k}].role", "dependent", "a dependent named in the conversation")
            self._dependents_asked = True
            return
        if turn.optional and (reply is None or str(reply).strip() == ""):
            self._declined.add(turn.path)          # the stated default stands
            return
        value = parse_answer(turn.path, reply) if isinstance(reply, str) else reply
        self.case.answer(turn.path, value, turn.ask or "")
        if stub is not None:
            self._stubs[stub] = 0

    # ------------------------------------------------------------------ changing an answer
    def answers(self) -> list:
        """What this person has answered, in the words they were asked — the list a refusal offers
        so the conversation can go back, every question together. Each row carries what it
        may be changed TO: the choices a choice question offers, with their words,
        or the kind of box a free answer takes — so the summary is a list with a control per answer,
        not a dropdown of questions and a second screen."""
        from ..client.interview import choice_words
        out = []
        for path, (value, evidence) in self.case.confirmed().items():
            if evidence.tier != "answer":
                continue
            field = path.rsplit(".", 1)[-1]
            choices = choices_for_fact(path)
            row = {"path": path, "question": evidence.caption or path, "value": value}
            if choices:
                words = choice_words(field) or {}
                if not words and list(choices) == list(YES_NO):
                    words = {"false": "No", "true": "Yes"}
                if field == "birth_month":
                    words = {str(n): MONTHS[n - 1] for n in range(1, 13)}
                row["type"] = "choice"
                row["choices"] = list(choices)
                row["labels"] = [words.get(c, c) for c in choices]
                row["shown"] = words.get(str(value).lower() if isinstance(value, bool) else str(value), str(value))
            else:
                row["type"] = "amount" if field.endswith("_cents") else "text"
                row["shown"] = _dollars(value) if field.endswith("_cents") and isinstance(value, int) else str(value)
            out.append(row)
        # a birth month and year answered together are one "Date of birth" row; the
        # day was never kept, so the row shows the month and year and takes a new date
        from collections import OrderedDict
        merged, births = [], OrderedDict()
        for row in out:
            m = _ITEM_PATH.match(row["path"])
            field = row["path"].rsplit(".", 1)[-1]
            if m and m.group(1) == "persons" and field in ("birth_year", "birth_month"):
                slot = births.setdefault(row["path"].rsplit(".", 1)[0], {})
                if not slot:
                    merged.append(slot)
                slot[field] = row["value"]
                continue
            merged.append(row)
        out = []
        for row in merged:
            if "path" in row:
                out.append(row)
                continue
            base = next(b for b, v in births.items() if v is row)
            year, month = row.get("birth_year"), row.get("birth_month")
            match = _ITEM_PATH.match(f"{base}.birth_year")
            day = self.case.birth_days().get(int(match.group(2))) if match is not None else None
            shown = " ".join(p for p in (MONTHS[month - 1] if isinstance(month, int) and 1 <= month <= 12 else "",
                                         str(day) if day is not None else "",
                                         str(year) if year is not None else "") if p)
            out.append({"path": f"{base}.{BIRTH_DATE}", "question": "Date of birth", "value": shown,
                        "type": "date", "shown": f"{shown} (kept on this computer)"})
        return out + self._typed_answers()

    TYPED_WORKBOOK = ("The workbook is not written for this return: it holds only what this version "
                      "reads and asks, so its figures would leave out the lines you typed and would "
                      "not match these forms.")

    def typed_statement(self) -> list:
        """The standing provenance of a return with typed lines: one sentence that
        says so, then each line in the words it was asked in with what was typed. A figure a person
        typed is never indistinguishable from one read off a document or asked by the service."""
        from ..facts import fallback_topics as topics
        typed, offered = self.case.typed_with_words(), topics.offered_writables()
        if not typed:
            return []
        rows = []
        for path, (value, words) in typed.items():
            kind = offered[path][1]["kind"] if path in offered else None
            shown = ("Yes" if value else "No") if kind == topics.BOOLEAN else \
                _dollars(value) if kind == topics.DOLLAR else str(value)
            rows.append(f"{words} {shown}")
        count = len(rows)
        return [f"{count} line{'s' if count != 1 else ''} on this return {'were' if count != 1 else 'was'} "
                f"typed by you, from a form this version does not read — not read from a document "
                f"and not checked against one:"] + rows

    def _typed_answers(self) -> list:
        """The forms-not-read checklist as one yes/no row per form, and under a yes
        each line the person typed — every one with its control, like any other answer. A no takes
        the form and its lines off the return."""
        from ..facts import fallback_topics as topics
        if not self._topics_asked:
            return []
        out, typed = [], self.case.typed_with_words()
        for key, topic in topics.offered_topics().items():
            ticked = key in self._topics_ticked
            out.append({"path": TOPIC + key, "question": f"{topic['label']} — {topic['form']}",
                        "value": ticked, "type": "choice", "choices": list(YES_NO),
                        "labels": ["No", "Yes"], "shown": "Yes" if ticked else "No"})
            if not ticked:
                continue
            for path, entry in topic["writables"].items():
                if path not in typed:
                    continue
                value, words = typed[path]
                row = {"path": TYPED + path, "question": words, "value": value, "typed_by_you": True}
                if entry["kind"] == topics.BOOLEAN:
                    row.update(type="choice", choices=list(YES_NO), labels=["No", "Yes"],
                               shown="Yes" if value else "No")
                elif entry["kind"] == topics.DOLLAR:
                    row.update(type="amount", shown=_dollars(value))
                else:
                    row.update(type="text", shown=str(value))
                out.append(row)
        return out

    def _answer_birth_date(self, path: str, typed: str, label: str) -> None:
        base = path.rsplit(".", 1)[0]
        year, month, day = parse_birth_date(typed, self.case.tax_year)
        for field, value in (("birth_year", year), ("birth_month", month)):
            self.case.answer(f"{base}.{field}", value, label)
            self._checked.add(f"{base}.{field}")
        match = _ITEM_PATH.match(f"{base}.birth_year")
        if match is not None and match.group(1) == "persons":
            self.case.keep_birth_day(int(match.group(2)), day)

    def change(self, path: str, reply) -> None:
        """Change one answer in place from the summary: forget it, then answer it
        again as the question it was — the same parse, the same words — so the questions continue
        from there. A stream row's first field reopens its stream, as `reopen` does."""
        if path.endswith("." + BIRTH_DATE):
            base = path.rsplit(".", 1)[0]
            parse_birth_date(str(reply or ""), self.case.tax_year)   # refuse before forgetting
            for field in ("birth_year", "birth_month"):
                self.reopen(f"{base}.{field}")
            self._answer_birth_date(path, str(reply), "Date of birth")
            return
        if path.startswith(TOPIC):                   # a form put on, or taken off
            from ..facts import fallback_topics as topics
            key, offered = path[len(TOPIC):], topics.offered_topics()
            if key not in offered or not self._topics_asked:
                raise AnswerError("That is not one of your answers")
            if not isinstance(reply, bool) and str(reply).lower() not in YES_NO:
                raise AnswerError("This is answered yes or no")
            wanted = reply if isinstance(reply, bool) else str(reply).lower() == "true"
            if wanted and any(self._more_forms.values()):
                raise AnswerError(self.TYPED_MORE_FORMS)
            if wanted and key not in self._topics_ticked:
                self._topics_ticked = [k for k in offered if k in self._topics_ticked or k == key]
            if not wanted:
                self._topics_ticked = [k for k in self._topics_ticked if k != key]
                self.case.untype(offered[key]["writables"])      # the form's lines go with it
            self._reviewed = False
            return
        if path.startswith(TYPED):                   # …or one typed line changed: parsed first
            words = self.case.typed_with_words().get(path[len(TYPED):])
            if words is None:
                raise AnswerError("That is not one of your answers")
            self._answer_typed(path[len(TYPED):], str(reply).lower() if isinstance(reply, bool) else str(reply), words[1])
            self._reviewed = False
            return
        question = next((a["question"] for a in self.answers() if a["path"] == path), None)
        if question is None:
            raise AnswerError("That is not one of your answers")
        # Parse BEFORE forgetting: a value the question refuses leaves the old answer standing,
        # with the refusal in the question's own words — never a silently emptied answer.
        value = parse_answer(path, reply) if isinstance(reply, str) else reply
        self.reopen(path)
        self.case.answer(path, value, question)

    def reopen(self, path: str) -> None:      # noqa: D401 — the summary and the refusal both use it
        """Forget one answer and ask it again. The stream a row belongs to reopens with it, so a
        person who said `true` by mistake is not stuck with the row it promised."""
        self.case.forget(path)
        self._declined.discard(path)
        self._checked.discard(path)
        self._reviewed = False                # the answers are shown again before the figures
        group = path.split("[", 1)[0] if "[" in path else None
        if group in STREAM_GROUPS:
            self._closed.discard(group)
            self._stubs[group] = 0

    # ------------------------------------------------------------------ the core
    def compute(self) -> dict:
        return self.ops.calculate_return({"facts": self._facts(), "tax_year": self.case.tax_year},
                                         engine_extras=self.case.typed() or None,
                                         birth_days=self.case.birth_days() or None)

    def fill(self, out_dir: Path, identity_path=None, notations_path=None):
        from ..client.formfill import fill_return
        from ..client.formlint import lint_filled
        env = self.compute()
        reviewed = {f"1040 {line['line_id']}": _dollars(line["value_cents"])
                    for line in env["result"]["forms"][0]["lines"]}
        facts = self._facts()
        typed = self.case.typed() or None      # the same typed lines at every resolve
        report = fill_return(facts, out_dir, reviewed_lines=reviewed,
                             tax_year=self.case.tax_year, identity_path=identity_path,
                             notations_path=notations_path, engine_extras=typed,
                             birth_days=self.case.birth_days() or None)
        # Every fill is linted where it happens — on the person's machine too — so
        # a box the fill should have filled and did not is counted and named, never assumed.
        report.lint = lint_filled(out_dir, facts, tax_year=self.case.tax_year,
                                  identity_path=identity_path, notations_path=notations_path,
                                  engine_extras=typed,
                                  birth_days=self.case.birth_days() or None).summary()
        return report
