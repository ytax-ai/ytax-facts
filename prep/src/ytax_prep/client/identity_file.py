# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The one local file a person actually edits — in a format a person can actually edit.

`case.identity.json` held names, TINs and an address as JSON. JSON is a poor choice for a file a
taxpayer opens: one missing comma or stray quote makes the whole thing unparseable, and the error
they get back names a byte offset. This is the same data as INI — sections, `key = value`, comments
— which every text editor understands and which fails locally rather than globally when someone
mistypes.

WHY NOT THE ALTERNATIVES, checked rather than assumed:

  * **YAML** is not in the standard library, and `src/` ships in the container. An unpinned
    dependency in the served surface is not available to us.
  * **TOML** can be READ by `tomllib` but not written — the standard library has no emitter, so we
    would hand-roll quoting and escaping for exactly the values most likely to break it: names with
    apostrophes, accents, or commas.
  * **INI** reads and writes from the standard library. Its one trap is real and is handled here:
    `configparser` interpolates `%` by default, so an address containing `50%` raises. Every reader
    and writer below passes `interpolation=None`.

THE SECTIONS ARE THE FORM'S OWN TERMS. They come from
`generated/identity_fields_f1040_ty2025.json`, derived from the real Form 1040 AcroForm — so this
file cannot ask for something no box wants, and cannot omit a box that needs filling. `primary.ssn`
is `[primary] ssn`; `address.city` is `[address] city`. The layout is the vocabulary.

It never leaves the machine, and the file says so in its first line — the person editing it is
entitled to know that without reading any documentation.
"""
from __future__ import annotations

import configparser
import json
import os
from pathlib import Path
from .._paths import data_root

FILENAME = "case.identity.ini"

# Owner read/write only. This file is a durable plaintext store of names, TINs and addresses — the
# plan calls it the largest new exposure it introduces — and the default umask makes it 0644, so
# every local user on a shared firm machine could read it. Measured before this was set.
FILE_MODE = 0o600

# What the file explains about itself. A person opening it should not have to be told elsewhere what
# it is, what happens to it, or that deleting it is allowed.
HEADER = """\
# YOUR DETAILS — THIS FILE NEVER LEAVES YOUR COMPUTER.
#
# Nothing here is sent to ytax. The figures from your tax documents are sent to be
# calculated; the details below are used only on this machine, to fill in the finished
# forms. You can delete this file at any time -- doing so removes only these details and
# leaves the rest of the return intact.
#
# Edit it in any text editor. Lines starting with # are notes and are ignored.
# Leave anything you do not have blank.
"""

# A short note under each section, so the file is self-explaining.
SECTION_NOTES = {
    "primary": "The person this return is for.",
    "spouse": "Only if you are filing jointly -- otherwise leave blank.",
    "address": "Where the return should show you living.",
}


class IdentityFileError(ValueError):
    """The file could not be read as written. Raised rather than guessed at."""


# What each entry is called when a sentence names it: the file's own sections and keys, in
# plain words. "your" and "your spouse's" because the person reads it about their own return.
WORDS = {
    "address.street": "the street address", "address.apt": "the apartment or suite number",
    "address.city": "the city", "address.state": "the state", "address.zip": "the ZIP code",
    "primary.first_name": "your first name", "primary.last_name": "your last name",
    "primary.ssn": "your taxpayer ID",
    "spouse.first_name": "your spouse's first name", "spouse.last_name": "your spouse's last name",
    "spouse.ssn": "your spouse's taxpayer ID",
}


def words_for(term: str) -> str:
    return WORDS.get(term, term.replace("_", " "))


def _terms(identity_map: dict) -> dict:
    """`{"primary": ["first_name", ...], ...}` from the form's own identity terms, in form order."""
    sections: dict = {}
    for term in identity_map["fields"].values():
        section, _, key = term.partition(".")
        sections.setdefault(section, [])
        if key not in sections[section]:
            sections[section].append(key)
    return sections


def load_identity_map(repo_root=None) -> dict:
    root = Path(repo_root) if repo_root else data_root()
    return json.loads((root / "generated" / "identity_fields_f1040_ty2025.json").read_text(encoding="utf-8"))


# What a proposed value says about itself, above the line it sits on. A COMMENT LINE, never an
# inline `; ...` marker: this parser runs with `interpolation=None` and no `inline_comment_prefixes`,
# so `ssn = 900-10-0001 ; proposed` would read the marker back AS PART OF THE SSN.
PROPOSED_NOTE = "# ↑ read from {source} — NOT checked by anyone. Correct it by typing over it."


def write(path, values: dict, identity_map: dict | None = None,
          proposed: dict | None = None) -> Path:
    """Write the identity file, including every box the form has — blank where unknown.

    Writing the blanks is the point: a person can see what is still needed without being asked, and
    an empty `ssn =` is a question they can answer in place.

    `proposed` maps a term to the document it was read from, and marks that value as **not yet
    checked by anyone**. The plan's failure mode is that *prefill trains people to skim* — if
    proposals are usually right, confirmation becomes clicking — so a proposal has to look different
    from an answer. The mitigation it asks for is exactly two things: proposals are visibly
    unconfirmed, and **a wrong prefill is no harder to correct than an empty one**. The second is why
    the value sits in the field normally rather than behind any ceremony: correcting it is typing
    over it, the same gesture as filling a blank.
    """
    identity_map = identity_map or load_identity_map()
    path = Path(path)
    parser = configparser.ConfigParser(interpolation=None)   # `%` is a legal character in an address
    for section, keys in _terms(identity_map).items():
        parser[section] = {key: values.get(f"{section}.{key}", "") for key in keys}

    proposed = proposed or {}
    body = [HEADER]
    for section, keys in _terms(identity_map).items():
        body.append(f"\n[{section}]\n")
        note = SECTION_NOTES.get(section)
        if note:
            body.append(f"# {note}\n")
        for key in keys:
            term = f"{section}.{key}"
            body.append(f"{key} = {values.get(term, '')}\n")
            if term in proposed:
                body.append(PROPOSED_NOTE.format(source=proposed[term]) + "\n")
    return write_private(path, "".join(body))


def write_private(path, text: str) -> Path:
    """Write `text` to `path` readable by its owner alone.

    Shared rather than reimplemented, deliberately: an earlier fix once reached one identity
    store and left the other, so a second private copy of this rule would set that up again. Any
    file holding identity goes through here.
    """
    path = Path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, FILE_MODE)
    _restrict(path)          # O_CREAT does not change an EXISTING file's mode
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def _restrict(path: Path) -> None:
    """Force owner-only permissions, where the platform has them.

    Windows has no POSIX mode bits and `chmod` there is close to a no-op; failing the write over
    that would be worse than writing the file, so this is best-effort and silent. The security
    claim this module can honestly make is therefore POSIX-only, and it is stated rather than
    implied.
    """
    try:
        os.chmod(path, FILE_MODE)
    except (OSError, NotImplementedError):
        pass


def delete(path) -> bool:
    """Remove the identity file. Returns True if it was there.

    The file's own header tells the person *"You can delete this file at any time"*, and until now
    nothing in the module could. A promise the code does not keep is worse than one it never made —
    and the plan names an explicit deletion path as part of this file's lifecycle.

    Only the identity half goes: the facts and the rest of the return are untouched, which is what
    the header promises too.
    """
    path = Path(path)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False


JOINT = "mfj"


def against_return(values: dict, facts: dict) -> str | None:
    """the `[spouse]` lines belong to a joint return only — the boxes they fill are Form
    1040's joint-return boxes, and the file says so under its own heading. Any spouse value
    supplied while the return's filing status is answered and not joint is a sentence, naming
    the status in the interview's own words and the two fixes; nothing here names a person.
    None while the status is still open (compute has not settled it) or when the file fits."""
    if not any(term.startswith("spouse.") for term in values):
        return None
    status = facts.get("filing_status")
    if status is None or status == JOINT:
        return None
    from .interview import CHOICES
    words = dict(CHOICES["filing_status"]).get(status, str(status))
    return (f"case.identity.ini names a spouse, and this return is filed as {words}. Form 1040 "
            f"carries a spouse's name only on a joint return. Leave the [spouse] lines blank, or "
            f"change the filing status on the Household tab.")


def read(path, identity_map: dict | None = None) -> dict:
    """Read it back as `{term: value}`, dropping anything left blank.

    Blank means "not supplied", not "supplied as empty" — the same absence-is-not-zero rule the
    fact side follows. An unknown section or key is REFUSED rather than ignored: it is almost always
    a typo, and silently dropping it would lose whatever the person meant to tell us.
    """
    identity_map = identity_map or load_identity_map()
    known = _terms(identity_map)
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(str(path), encoding="utf-8")
    except configparser.Error as e:
        raise IdentityFileError(f"could not read {path}: {e}")

    values = {}
    for section in parser.sections():
        if section not in known:
            raise IdentityFileError(
                f"[{section}] is not a section this file uses ({', '.join(sorted(known))}). "
                f"Refusing rather than ignoring it — a section nobody reads is a detail you "
                f"believed you had supplied.")
        for key, value in parser[section].items():
            if key not in known[section]:
                raise IdentityFileError(
                    f"[{section}] has no entry called {key!r} "
                    f"(it uses {', '.join(known[section])}).")
            if value.strip():
                values[f"{section}.{key}"] = value.strip()
    return values
