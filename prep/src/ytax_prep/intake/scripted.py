# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The scripted person and the corpus run.

A `ScriptedPerson` answers the intake conversation from a profile's own facts, typing each answer
as a person would (dollars, true/false, a code, a person's number from 1) so the answer rules are
exercised, and confirms every candidate a reader proposed — recording, never hiding, any read that
disagrees with the profile. `run_profile` carries one showcase profile end to end: its PDFs read,
the conversation answered, the outcome and the lines compared with the oracle (the pinned engine on
the profile's own facts), and the forms filled.
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from .answers import AnswerError
from .case import Case
from .loop import ANY, ATTEST, DEPENDENTS, MORE, IntakeLoop
from .profiles import ProfileGap, oracle_lines, service_facts

_ITEM_PATH_RE = re.compile(r"^([a-z_0-9]+)\[(\d+)\]\.([a-z_0-9]+)$")

# Groups whose item identity a DOCUMENT states, rather than the order documents happened to be fed
# in: {group: the field a document's own reader proposes that names which real-world thing this
# item is}. `k1s` is the one today — a K-1's `source` (partnership / s_corp / estate_trust) comes
# straight off which FORM the document classified as (`FORM_CONSTANTS`), never off which position
# it landed at.

# WHY THIS TABLE EXISTS AT ALL: `book_of` below flattens a profile's own
# arrays by THEIR array position, and a reader assigns an item's index purely by arrival order
# (`IntakeLoop.add_document`, `loop.py`) — the only order that exists in production, since nothing
# about a stack of real K-1s ties them to how a synthetic generator happened to order its facts.
# Nothing requires those two orderings to agree, and for a multi-K-1 profile they need not: this
# profile's own three K-1s read in filename order (two 1065s then the 1120-S) while its facts list
# them partnership / s_corp / partnership. Comparing `k1s[1]` read against `k1s[1]` in the book
# blind would pair one document's money boxes with a DIFFERENT document's entity type — precisely
# the corruption `tests/test_intake_corpus.py::ContentMatchedItemIdentityTest` exists to catch.
# Matching by content instead of position is the harness's fix for that; matching a document's OWN
# identity field to its own facts (`readers/documents.py::_constant_candidates`) is the reader's.
IDENTITY_FIELDS = {"k1s": "source"}


def book_of(facts: dict) -> dict:
    """`{path: value}` — roots, and `group[i].field` for every item field."""
    book = {}
    for key, value in facts.items():
        if isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    for field, v in item.items():
                        book[f"{key}[{i}].{field}"] = v
        elif not isinstance(value, dict):
            book[key] = value
    return book


def typed(path: str, value) -> str:
    """What a person types for this value."""
    field = path.rsplit(".", 1)[-1]
    if isinstance(value, bool):
        return "true" if value else "false"
    if field == "person":
        return str(int(value) + 1)
    if field.endswith("_cents"):
        whole, part = divmod(abs(int(value)), 100)
        return f"{'-' if value < 0 else ''}{whole:,}.{part:02d}"
    return str(value)


# Forms the page takes only TYPED into its workbook (intake/server.py TYPED_NOT_READ): a person
# who holds one says so on the "how many more" page and types its boxes, which is what this
# harness does with the profile's own rows. Every other form is read off its document or not at all.
TYPED_ONLY_GROUPS = ("ssa1099s", "f1095as")


# What this person answers when the page asks something the profile does not state — a
# question an IRS or Direct File scenario was never asked because nothing its return computed
# reached it. Each is the arm that asks nothing further, and each is reported in `defaulted`
# and checked by the line-by-line comparison with the profile's own resolved return.
UNASKED_DEFAULTS = {
    "unable_to_care_for_self": "false",           # a dependent able to care for themselves
    "is_permanently_disabled": "false",           # not permanently and totally disabled
    "child_parents_living": "false",              # the ordinary rules, no non-parental split
    "parents_situation": "other",                 # no divorce or separation that splits benefits
    "couple_required_to_file": "true",            # neither spouse is anyone's dependent
    "community_property_domicile": "false",       # a yes is refused (Form 8958 is not carried)
    "materially_participated": "true",            # the sole proprietor's own business
    "all_investment_at_risk": "true",
    "amount_paid_cents": "0",                     # care paid by benefits only, nothing directly
    "child_emancipated": "false",                 # still in a parent's custody
    "has_other_biological_or_adoptive_parent": "false",
    "was_spouse_during_year": "false",
    "relationship_violates_local_law": "false",
}


class ScriptedPerson:
    def __init__(self, facts: dict, engine_facts: dict | None = None):
        self.facts = facts
        # the typed-lines fallback: the profile's OWN engine facts — the one place they feed typed answers. A
        # form is ticked when they hold any of its inputs, and each line is answered from them.
        self.engine_facts = engine_facts or {}
        self.typed_lines = 0
        self.defaulted: list = []      # questions answered from UNASKED_DEFAULTS
        self.typed_forms: dict = {}    # group -> rows typed into the workbook (TYPED_ONLY_GROUPS)
        self.attested: list = []       # scope questions this harness answered for the profile
        self.typed_as_none: list = []  # a form's line the profile does not carry: entered as none
        self.book = book_of(facts)
        self.mismatches: list = []       # (path, read, book)
        self.extras: list = []           # (path, read) a reader proposed what the profile does not carry
        self.unanswered: list = []
        self._aliases: dict = {}         # (group, reader index) -> the oracle array index it IS
        self._claimed: dict = {}         # group -> set of oracle indices already matched

    def typed_workbook(self, workbook_path) -> bytes:
        """The workbook the page wrote for the counted forms, with those rows typed in from the
        profile: what a person holding the paper does before saving it."""
        from ..client.interview import open_questions
        from ..client.workbook.reader import read_workbook
        from ..client.workbook.writer import build_workbook
        read = read_workbook(Path(workbook_path).read_bytes())
        case = dict(read.facts)
        for group in self.typed_forms:
            case[group] = [dict(row) for row in self.facts.get(group) or []]
        case.setdefault("tax_year", self.facts.get("tax_year", 2025))
        return build_workbook(case, [], open_questions(case))

    def _unasked_default(self, path: str):
        field = path.rsplit(".", 1)[-1]
        if field == "child_residence_state":
            # the household's own state where the profile states one, else a state whose age of
            # majority is 18 (Illinois): the custody rule's ordinary case
            self.defaulted.append(path)
            state = self.facts.get("residence_state")
            return state if isinstance(state, str) and len(state) == 2 else "il"
        if field in UNASKED_DEFAULTS:
            self.defaulted.append(path)
            return UNASKED_DEFAULTS[field]
        return None

    def _engine_fact(self, writable: str):
        """The profile's own value for one offered path. A form about ONE of something is asked
        against a row — `/scheduleCs/[0]/x` — and the PROFILE keys that row by its own id, so the
        row number is read against the ids this profile actually carries. `*` matches any row,
        which is what the checklist's "does this profile have one of these?" asks."""
        import re as _re
        if "/*/" not in writable and "/[" not in writable:
            return self.engine_facts.get(writable)
        group, leaf = _re.split(r"/(?:\*|\[\d+\])/", writable, maxsplit=1)
        ids = list(dict.fromkeys(
            m.group(1) for m in (_re.match(rf"^{_re.escape(group)}/(#[0-9a-f-]+)/", k)
                                 for k in self.engine_facts) if m))
        row = _re.search(r"/\[(\d+)\]/", writable)
        chosen = ids[int(row.group(1)):int(row.group(1)) + 1] if row else ids
        for cid in chosen:
            held = self.engine_facts.get(f"{group}/{cid}/{leaf}")
            if held is not None:
                return held
        return None

    def dependents(self) -> int:
        return sum(1 for p in self.facts.get("persons") or [] if p.get("role") == "dependent")

    def _resolve(self, group: str, index: int, candidates) -> int:
        """Which `self.facts[group]` array index this reader item (`group[index]`, everything read
        off ONE document) actually is — by CONTENT, not by the position it happened to arrive at.

        Arrival order (`index`) carries no information about the profile's own array order; nothing
        ties them together except what the item's own candidates say. If the group has an identity
        field (`IDENTITY_FIELDS`) and this batch named one, only an unclaimed oracle item agreeing
        on it is even considered — the K-1's `source` alone already disambiguates the S corp from
        either partnership here. Among what is left, the unclaimed item whose OWN fields disagree
        with the read candidates the LEAST wins; ties (typically: nothing else was read yet) keep
        the lowest unclaimed index, which is inert since their content cannot be told apart anyway.
        """
        key = (group, index)
        if key in self._aliases:
            return self._aliases[key]
        items = self.facts.get(group) or []
        claimed = self._claimed.setdefault(group, set())
        id_field = IDENTITY_FIELDS.get(group)
        read = {}
        for cand in candidates:
            parsed = _ITEM_PATH_RE.match(cand.path)
            if parsed and parsed.group(1) == group:
                read[parsed.group(3)] = cand.value
        if len(items) <= 1 or id_field is None:
            resolved = index if index < len(items) else len(items) - 1
        else:
            best, best_score = None, None
            for j, item in enumerate(items):
                if j in claimed:
                    continue
                if id_field in read and item.get(id_field) != read[id_field]:
                    continue
                score = sum(1 for field, value in read.items()
                            if field != id_field and item.get(field, value) != value)
                if best is None or score < best_score:
                    best, best_score = j, score
            resolved = best if best is not None else index
        claimed.add(resolved)
        self._aliases[key] = resolved
        return resolved

    def _book_path(self, path: str) -> str:
        """`path`, with its item index translated to the oracle array index `_resolve` recorded for
        it — the identity the book actually needs to be read at. A path outside `IDENTITY_FIELDS`,
        or one no confirm batch has resolved yet, passes through unchanged."""
        parsed = _ITEM_PATH_RE.match(path)
        if parsed is None:
            return path
        group, index, field = parsed.group(1), int(parsed.group(2)), parsed.group(3)
        alias = self._aliases.get((group, index))
        return path if alias is None else f"{group}[{alias}].{field}"

    def reply(self, turn):
        if turn.kind == "more_forms":
            # "how many more of these forms?": a form the page reads is the profile's document, so
            # 0 — the corpus reads those figures off the page, never out of a typed workbook. A form
            # the page only takes typed is counted from the profile's own rows.
            given = {}
            for item in turn.items or []:
                group = item["path"].split(":", 1)[1] if ":" in item["path"] else ""
                held = len(self.facts.get(group) or []) if group in TYPED_ONLY_GROUPS else 0
                given[item["path"]] = str(held)
                if held:
                    self.typed_forms[group] = held
            return given
        if turn.kind == "checklist":
            # Tick what this profile answers true, and every stream it actually holds rows for;
            # everything else is the no the page states.
            given = {}
            for item in turn.items or []:
                path = item["path"]
                if path.startswith("topic:"):
                    from ..facts import fallback_topics as topics
                    given[path] = any(self._engine_fact(w) is not None
                                      for w in topics.TOPICS[path[len("topic:"):]]["writables"])
                    continue
                if path.startswith(ATTEST):
                    # A form's own scope question is not an engine fact and no profile carries an
                    # answer to one: it is what a PERSON asserts about their own papers. The
                    # harness answers it the way the profile's oracle was computed — the modeled
                    # case, which is the arm the allow-list offers — and says so in `attested`.
                    from ..facts import fallback_topics as topics
                    key, name = path[len(ATTEST):].split(".")[:2]      # …and a row number, if any
                    given[path] = str(topics.TOPICS[key]["attestations"][name]["must_be"]).lower()
                    self.attested.append(path)
                    continue
                if path.startswith("typed:"):
                    writable = path[len("typed:"):]
                    held = self._engine_fact(writable)
                    if held is None:
                        # A form is ticked only when the profile carries one of its writables, and a
                        # profile's own facts are complete (its oracle resolves). So a writable this
                        # form asks for and this profile does not carry is one the household does
                        # not have — the dictionary's own "enter zero when none". Said out loud in
                        # `typed_as_none`, never silently.
                        from ..facts import fallback_topics as topics
                        entry = topics.offered_writables()[writable][1]
                        given[path] = "false" if entry["kind"] == topics.BOOLEAN else "0"
                        self.typed_as_none.append(path)
                        continue
                    value = held["item"]
                    given[path] = (str(value).lower() if isinstance(value, bool) else str(value))
                    self.typed_lines += 1
                    continue
                if item.get("type") == "date":
                    # a date of birth from the profile's month and year; the day is
                    # dropped by the page, so any real day serves (the 15th)
                    base = self._book_path(path).rsplit(".", 1)[0]
                    year, month = self.book.get(base + ".birth_year"), self.book.get(base + ".birth_month")
                    if year is None:
                        self.unanswered.append(path)
                        given[path] = ""
                    else:
                        given[path] = f"{int(year):04d}-{int(month or 1):02d}-15"
                    continue
                if item.get("type") in ("amount", "text", "choice"):
                    book_path = self._book_path(path)
                    if book_path in self.book:
                        given[path] = typed(path, self.book[book_path])
                    elif (fallback := self._unasked_default(path)) is not None:
                        given[path] = fallback
                    elif item.get("type") == "amount":
                        given[path] = ""                  # an invitation: the profile states nothing
                    else:
                        self.unanswered.append(path)
                        given[path] = ""
                elif path.startswith(ANY):
                    given[path] = bool(self.facts.get(path[len(ANY):]))
                else:
                    given[path] = self.book.get(self._book_path(path)) is True
            return given
        if turn.kind == "review":
            return "ok"
        if turn.kind == "confirm":
            # Resolve every item this batch touches BEFORE consulting the book — every candidate in
            # one confirm batch comes from the SAME document (`next_turn` groups them that way), so
            # they share one (group, index) and one resolution.
            seen = set()
            for cand in turn.candidates:
                parsed = _ITEM_PATH_RE.match(cand.path)
                if parsed and (parsed.group(1), parsed.group(2)) not in seen:
                    seen.add((parsed.group(1), parsed.group(2)))
                    self._resolve(parsed.group(1), int(parsed.group(2)), turn.candidates)
            corrections = {}
            for cand in turn.candidates:
                book_path = self._book_path(cand.path)
                if book_path in self.book:
                    if cand.value != self.book[book_path]:
                        self.mismatches.append((cand.path, cand.value, self.book[book_path]))
                        corrections[cand.path] = self.book[book_path]
                else:
                    self.extras.append((cand.path, cand.value))
            for item in turn.items or []:               # the form's own yes/no boxes, same card
                held = self.book.get(self._book_path(item["path"]))
                if item.get("type") == "choice":
                    # a question on the card — answered from the profile, or not at all: a
                    # profile that never states it leaves the card unchosen, and the run says so
                    if isinstance(held, bool):
                        corrections[item["path"]] = "true" if held else "false"
                    elif (fallback := self._unasked_default(item["path"])) is not None:
                        corrections[item["path"]] = fallback
                    else:
                        self.unanswered.append(item["path"])
                        corrections[item["path"]] = ""
                else:
                    corrections[item["path"]] = held is True
            if turn.path is not None and turn.path not in corrections:
                corrections[turn.path] = self.book.get(self._book_path(turn.path), turn.candidates[0].value)
            return corrections or "all"
        if turn.kind == "question":
            if turn.path == DEPENDENTS:
                return str(self.dependents())
            if turn.path.startswith(ANY) or turn.path.startswith(MORE):
                # "do you have any / another?" — yes while the profile still holds a row the
                # conversation has not started (`turn.rows` is what it holds already).
                group = turn.path.split(":", 1)[1]
                rows = turn.rows or 0
                return "true" if rows < len(self.facts.get(group) or []) else "false"
            book_path = self._book_path(turn.path)
            if book_path in self.book:
                return typed(turn.path, self.book[book_path])
            if getattr(turn, "optional", False):
                return ""                          # the profile states nothing: keep the default
            fallback = self._unasked_default(turn.path)
            if fallback is not None:
                return fallback
            self.unanswered.append(turn.path)
            return None
        return None


def oracle_knockouts(engine_doc: dict, engine_home=None) -> list:
    """The knockout facts the pinned engine itself resolves true on a profile's own facts. A
    profile whose oracle is knocked out cannot be matched "at the oracle's lines": those lines were
    computed on a return the engine marks as not fileable. Reported as a corpus boundary."""
    from ..engine.adapter import EngineAdapter, discover_pin
    tsv = EngineAdapter(discover_pin(engine_home)).resolve_facts(engine_doc)
    out = []
    for line in tsv.splitlines():
        parts = line.split("\t", 3)
        if len(parts) == 4 and "nockout" in parts[0].rsplit("/", 1)[-1] and parts[1] == "Complete" \
                and parts[3] == "true":
            out.append(parts[0])
    return sorted(out)


def _cents(dollars: str) -> int:
    sign = -1 if dollars.startswith("-") else 1
    whole, _, part = dollars.lstrip("-").partition(".")
    return sign * (int(whole) * 100 + int((part + "00")[:2]))


def run_profile(profile_dir: Path, max_turns: int = 400, model=None, pdf_root=None) -> dict:
    profile_dir = Path(profile_dir)
    out = {"profile": profile_dir.name, "documents": [], "read": {}, "unconsumed": [], "not_read": [],
           "vocabulary": {}, "questions": 0,
           "mismatches": [], "extras": [], "unanswered": [], "error": None, "outcome": None,
           "lines_equal": False, "line_diffs": {}, "filled": [], "oracle_knockouts": [],
           "lint_checked": 0, "lint_defects": 0, "typed": 0}
    doc = json.loads((profile_dir / "input" / "facts.json").read_text(encoding="utf-8"))
    try:
        facts = service_facts(doc)
    except ProfileGap as gap:
        out["outcome"] = "profile-gap"
        out["error"] = str(gap)
        return out
    oracle = {k: _cents(v) for k, v in oracle_lines(doc).items()}
    out["oracle_knockouts"] = oracle_knockouts(doc)
    if pdf_root is None:
        from .registers import pin_pdf_root
        pdf_root = pin_pdf_root()                 # the page's own root: the corpus IS the page
    try:
        return _run(profile_dir, out, facts, oracle, max_turns, model, pdf_root,
                    engine_facts=doc.get("facts") or {})
    except Exception as why:                     # one profile's failure is reported, never the run's
        out["outcome"] = "error"
        out["error"] = f"{type(why).__name__}: {why}"[:500]
        return out


def _run(profile_dir, out, facts, oracle, max_turns, model, pdf_root, engine_facts=None):
    loop = IntakeLoop(Case(), model=model, pdf_root=pdf_root)
    for pdf in sorted((profile_dir / "input").glob("*.pdf")):
        result = loop.add_document(pdf)
        out["documents"].append(pdf.name)
        if result.unconsumed:
            out["unconsumed"].append(f"{pdf.name}: {result.unconsumed}")
        for name in getattr(result, "not_carried", []) or []:
            out["not_read"].append(f"{pdf.name}: {name}")
        vocab = getattr(result, "vocabulary", "tables")
        out["vocabulary"][vocab] = out["vocabulary"].get(vocab, 0) + 1
        for cand in result.candidates:
            out["read"][cand.evidence.tier] = out["read"].get(cand.evidence.tier, 0) + 1
    person = ScriptedPerson(facts, engine_facts=engine_facts)
    import tempfile
    work = tempfile.TemporaryDirectory(prefix="ytax-corpus-")
    loop.workbook_dir = Path(work.name)        # where the page would write the typed-forms workbook
    turn = None
    for _ in range(max_turns):
        turn = loop.next_turn()
        if turn.kind in ("complete", "refused"):
            break
        if turn.kind == "workbook_wait":
            if not person.typed_forms or out.get("workbook_typed"):
                break                              # nothing this person can type, or typed once already
            loop.add_workbook(person.typed_workbook(loop.more_workbook), "workbook.xlsx")
            out["workbook_typed"] = dict(person.typed_forms)
            continue
        if turn.kind == "question":
            out["questions"] += 1
        reply = person.reply(turn)
        if reply is None:
            break
        try:
            loop.respond(turn, reply)
        except (AnswerError, ValueError) as why:
            out["error"] = f"{turn.path}: {why}"
            break
    out["outcome"] = turn.kind if turn is not None else None
    out["mismatches"] = [f"{p}: read {r!r}, profile {b!r}" for p, r, b in person.mismatches]
    out["extras"] = [f"{p}: read {r!r}" for p, r in person.extras]
    out["unanswered"] = person.unanswered
    out["defaulted"] = person.defaulted
    out["service_facts"] = loop._facts()       # what the page would send: for diagnosing a refusal
    out["typed"] = person.typed_lines          # lines a person would have typed
    out["attested"] = list(person.attested)    # …and the scope questions answered for the profile
    out["typed_as_none"] = list(person.typed_as_none)
    if turn is not None and turn.kind == "refused":
        out["error"] = "; ".join(str(r.get("boundary") or r) for r in (turn.refusals or []))[:500]
    if turn is not None and turn.kind == "complete":
        got = dict(turn.lines or {})
        out["line_diffs"] = {k: (got.get(k), oracle.get(k)) for k in sorted(set(got) | set(oracle))
                             if got.get(k) != oracle.get(k)}
        out["lines_equal"] = not out["line_diffs"]
        with tempfile.TemporaryDirectory() as tmp:
            try:
                report = loop.fill(Path(tmp))
                out["filled"] = [f.form_key for f in report.filled]
                # The filled forms are linted in the corpus too; a box the fill
                # should have filled and did not fails the profile, named.
                lint = getattr(report, "lint", None) or {}
                out["lint_checked"] = lint.get("checked", 0)
                out["lint_defects"] = lint.get("defects", 0)
                if out["lint_defects"]:
                    named = [d for f in lint.get("forms", {}).values() for d in f.get("defects", [])]
                    named += lint.get("unexpected_files", [])
                    out["error"] = f"lint: {out['lint_defects']} defect(s): " + "; ".join(named[:3])[:400]
            except Exception as why:              # a fill refusal is reported, never hidden
                out["error"] = f"fill: {why}"
    return out


def corpus_boundary(result: dict) -> bool:
    """The profile's own facts are knocked out at the pin: no run can pass it, and none should."""
    return bool(result.get("oracle_knockouts"))


def passed(result: dict) -> bool:
    return (result["outcome"] == "complete" and result["lines_equal"] and not result["unanswered"]
            and not result["error"])
