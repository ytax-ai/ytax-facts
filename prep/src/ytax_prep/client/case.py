# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""A case that survives between sessions, and the revisions that let answers change.

A return is not prepared in one sitting. Documents arrive, get read, get confirmed; weeks pass; a
filing status changes; another 1099 turns up. So the case is saved locally and resumed, and this is
what it is saved as.

TWO FILES, NOT ONE — and this is the load-bearing part. Facts that may cross go in one file;
identity goes in another that never leaves the machine. Not a convention: a single file holding both
is one careless upload away from being the leak, and "we only send part of it" is a promise made by
code rather than by structure. Two files make the local half a thing you can point at, back up, and
delete on its own.

REVISIONS, because "correct an answer" and "answer a question" are different acts. `loop._set_fact`
refuses to overwrite a fact already supplied — right within one computation, where a value changing
mid-round makes the result depend on which pass you look at. But a person reviewing their return in
March and changing their filing status is not doing that; they are producing a **new revision** of
the case. So corrections are refused WITHIN a revision and are exactly how you start the next one.

THE BOUNDARY IS CHECKED AGAIN AT CONFIRMATION. Documents are scrubbed on the way in, but a person
typing into a review screen is a second entry point — and free text is where identity actually
leaks: an SSN pasted into a note, a name in a field nobody classified. So confirmed values are
checked before they are accepted, using the same shapes the outbound lint uses.
"""
from __future__ import annotations

import json
from pathlib import Path

from .identity_file import write_private
from .payload import PayloadRefused, project_case

FACTS_FILE = "case.facts.json"
IDENTITY_FILE = "case.identity.json"


class CaseRefused(ValueError):
    """A change was rejected. Raised rather than silently applied or silently dropped."""


class CaseFile:
    """One taxpayer's case, across however many sittings it takes.

    `facts` is what may be computed on; `identity` never leaves this machine. The split is
    maintained by `project_case`, which is the same control the wire uses — one implementation of
    "what may cross", not a second one free to disagree.
    """

    def __init__(self, facts: dict | None = None, identity: dict | None = None,
                 revision: int = 1, answered: set | None = None,
                 proposed: dict | None = None):
        self.facts = dict(facts or {})
        self.identity = dict(identity or {})
        self.revision = revision
        # Which paths this revision has already answered. A revision is monotonic; the next one is
        # where corrections live.
        self.answered = set(answered or ())
        # Identity terms READ OFF A DOCUMENT and not yet checked by a person, mapped to the document
        # they came from. The facts half has had this distinction since `prefill` was written — a
        # prefilled fact is deliberately not `answered` — and identity had no equivalent, so a name
        # nobody had looked at was indistinguishable from one somebody had confirmed. It persists
        # across a save, because a proposal is still a proposal next week.
        self.proposed = dict(proposed or {})

    # ---- persistence ------------------------------------------------------------------------

    @classmethod
    def load(cls, directory) -> "CaseFile":
        d = Path(directory)
        facts_path, identity_path = d / FACTS_FILE, d / IDENTITY_FILE
        if not facts_path.is_file():
            return cls()
        saved = json.loads(facts_path.read_text(encoding="utf-8"))
        identity = json.loads(identity_path.read_text(encoding="utf-8")) if identity_path.is_file() else {}
        return cls(facts=saved.get("facts", {}), identity=identity,
                   revision=saved.get("revision", 1), answered=set(saved.get("answered", [])),
                   proposed=saved.get("proposed", {}))

    def save(self, directory) -> None:
        """Write both halves. Separately, always — see the module docstring."""
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        # VERIFY the split rather than trust it. Projecting the facts half must yield an EMPTY
        # overlay: anything landing there is identity sitting in the file that may cross. Checking
        # only that projection succeeds would prove nothing — `project_case` CLASSIFIES a name as
        # local rather than refusing it, so a name in `facts` would pass silently. Found by the
        # test that asserted it.
        _payload, overlay = project_case(self.facts)
        if overlay:
            raise CaseRefused(
                f"identity is sitting in the facts half of this case: {', '.join(sorted(overlay))}. "
                f"It belongs in the identity file, which never leaves this machine — refusing to "
                f"write a case whose two halves are not actually separate.")
        # Owner-only as well, and this is a decision rather than an oversight either way. The facts
        # half carries no identity by construction — `_check_boundary` refuses it on the way in — so
        # it is not the exposure the identity half is. But it is still a taxpayer's wages,
        # withholding and filing status, and "contains no name" is not the same as "fine for every
        # user on this machine to read". The default umask was nobody's decision; this is.
        write_private(d / FACTS_FILE, json.dumps(
            {"revision": self.revision, "answered": sorted(self.answered),
             "proposed": self.proposed, "facts": self.facts},
            indent=2, sort_keys=True) + "\n")
        # Owner-only. This half holds names, TINs and addresses, and `save()` is the save/resume
        # path — the mechanism the whole flow is built on, run every time a case is put down. It was
        # once written at the process umask (0644); `identity_file` owns the rule so there is
        # one place it can be got right.
        write_private(d / IDENTITY_FILE,
                      json.dumps(self.identity, indent=2, sort_keys=True) + "\n")

    # ---- prefill and confirmation ------------------------------------------------------------

    def prefill(self, facts: dict, identity: dict | None = None,
                source: str | None = None) -> None:
        """Seed from what the documents produced. Prefilled values are NOT answered.

        The distinction matters: a value read off a document is a proposal until a person confirms
        it, and treating it as answered would make the first correction look like a contradiction.

        `source` names the document an identity value came from, and passing it marks those terms
        **unconfirmed** — which is what stops them filling a form box (`confirmed_identity`). Omit it
        and the identity is taken as already confirmed, which is the right default for values a
        person typed rather than a document offered.
        """
        self.facts.update(facts)
        if identity:
            self.identity.update(identity)
            if source:
                for term in identity:
                    self.proposed[term] = source

    def confirmed_identity(self) -> dict:
        """The identity a person has actually vouched for.

        What is unconfirmed is simply absent, so the merge refuses on it exactly as it refuses a
        value nobody supplied. That is the point: *a wrong prefill is worse than a blank, because a
        blank gets attention and a wrong value does not* — so an unchecked value must not be able to
        reach a rendered return by being quietly good enough.
        """
        return {term: value for term, value in self.identity.items()
                if term not in self.proposed}

    def confirm_identity(self, values: dict) -> None:
        """Record that a person has checked these identity terms, correcting any that were wrong.

        PER VALUE, never per document. Confirming the SSN says nothing about the name — the plan
        calls per-value confirmation *the strongest argument* against the alternative, because one
        glance at a document-shaped list is how a wrong value gets waved through.

        A term nobody proposed is accepted too: typing a value in is confirming it.
        """
        for term, value in sorted(values.items()):
            self.identity[term] = value
            self.proposed.pop(term, None)

    def confirm(self, changes: dict) -> None:
        """Apply a person's review of this revision.

        Refuses a correction to something this revision already answered — that is what
        `start_revision()` is for — and refuses any value carrying identity, wherever it was typed.
        """
        for path, value in sorted(changes.items()):
            if path in self.answered:
                raise CaseRefused(
                    f"{path} was already answered in revision {self.revision}. Changing it now "
                    f"would make the result depend on when you looked; start a new revision to "
                    f"correct it, which keeps what changed visible.")
            self._check_boundary(path, value)
        for path, value in sorted(changes.items()):
            _set(self.facts, path, value)
            self.answered.add(path)

    def start_revision(self) -> int:
        """Begin a new revision, so answers can be corrected.

        This is the honest shape for "my filing status changed": nothing is overwritten inside a
        computation, and the change is attributable to a revision rather than appearing as though
        the facts had always been that way.
        """
        self.revision += 1
        self.answered = set()
        return self.revision

    def _check_boundary(self, path: str, value) -> None:
        """The second look. Documents are scrubbed on the way in; a review screen is another door,
        and free text is where identity actually leaks."""
        if not isinstance(value, str):
            return
        try:
            from .payload import lint_payload
            lint_payload({path.rsplit(".", 1)[-1]: value})
        except PayloadRefused as e:
            raise CaseRefused(
                f"{path} was not accepted: {e}. Identity stays on this machine — correct the value "
                f"rather than sending it.")


def _set(target: dict, path: str, value) -> None:
    """Write `w2s[0].wages_cents` into the nested case.

    Shares the loop's path grammar and overrides its policy: the loop must be monotonic within a
    round, while a revision exists precisely so an answer can change. The guard here is `answered`,
    which is revision-scoped — so a correction is refused inside a revision and permitted across
    one, which is what a person reviewing in March actually needs."""
    from .loop import _set_fact
    _set_fact(target, path, value, overwrite=True)
