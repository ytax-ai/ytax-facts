# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""`collect` and `run` — the two commands, and the one round between them.

    python3 -m ytax_prep.client.workbook collect \
        --sources collector/out/sources --out case.xlsx
    python3 -m ytax_prep.client.workbook run --workbook case.xlsx

`run` computes IN-PROCESS against the pinned engine at YTAX_ENGINE_HOME (`transport.local_sender`) — no server, no key, nothing leaves the machine.

**`run` IS the review**. There is no sign-off tab and no `confirmed?` column: a
person corrects a figure and runs again, as often as they like.

ONE ROUND, DELIBERATELY. `max_passes=1` and an `answer` that returns nothing, because the human is
the answerer — asynchronously, across runs. The gaps come back into cells and wait there. **There is
no second loop and no new compute path**: this is `run_gap_loop` and `local_sender`, the ones that
already existed.

`acknowledge` returns a fixed marker rather than `None`, because `run_gap_loop` refuses to render on
`None`. This is where the gate collapse cashes out: the library's submit-time gate still fires on
every run, and the workbook answers it BY CONSTRUCTION, because the assumptions are written visibly
onto Household and Computed return each time. The gate underneath is unchanged — only this surface's answer
to it is (this surface only).

`identity=None`, ALWAYS. If a response ever asks for identity fields the loop's own refusal fires and
`run` surfaces it on the Computed return tab. That is correct behaviour for a facts-only surface: identity
lives in the separate 33a workbook, which this surface does not build and does not touch.

LOCAL ONLY by construction of how it is used — this tool does not deploy, and the default URL is
127.0.0.1.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from ...engine import EngineNotAvailable
from ...facts import ServiceFactsError
from ..documents import DocumentsRefused, facts_from, read_extractions
from ..formfill import FillRefused
from ..identity_file import IdentityFileError
from ..pdfform.reader import PdfSurprise
from ..pdfform.registers import RegisterSurprise
from ..interview import open_questions
from ..loop import LoopRefused, run_gap_loop
from ..payload import PayloadRefused
from ..transport import ServiceUnreachable, TransportRefused, local_sender
from . import layout
from .ooxml import WorkbookXMLError
from .reader import WorkbookRefused, read_reviewed_lines, read_workbook
from .writer import build_workbook, rewrite_workbook

# Not None, and not a claim that anybody reviewed anything: the marker records that the gate was
# ASKED, which is the thing the gate is on.
ACKNOWLEDGEMENT = "workbook-run"

_PATH_IN_TEXT = re.compile(r"\b[a-z][a-z0-9_]*\[\d+\]\.[a-z][a-z0-9_]*\b")


def _attribute(message: str) -> dict:
    """Pull the fact path(s) out of a refusal the service RAISED, so the words land on the cell.

    `{path: message}` for every path this workbook holds — empty when it holds none, in which case
    the refusal reaches Computed return alone, unattributed rather than pinned to the wrong cell.
    The message goes to that tab either way; that is the caller's one line, not this function's."""
    return {path: message for path in dict.fromkeys(_PATH_IN_TEXT.findall(message))
            if layout.holds(path)}


def run_workbook(data: bytes, send, *, stated_at: str = "") -> bytes:
    """One whole round: read, send once, write back. Network-free — `send` is injected."""
    read = read_workbook(data)

    if read.refusals:
        # THE READER REFUSED, SO NOTHING IS SENT. Sending the parseable remainder would compute the
        # return as if the bad cell had never been supplied — a wrong number, not a smaller one.
        # Every refusal reaches Computed return, whether or not it also reached a cell (7.6):
        # the cell says which figure, the tab says what happened to the round.
        return rewrite_workbook(
            read,
            invalid={r.fact: r.message for r in read.refusals if layout.holds(r.fact)},
            extra_refusals=tuple(r.message for r in read.refusals),
            stopped_because=layout.STOPPED_READER_REFUSED, stated_at=stated_at)

    case = dict(read.facts)
    case["tax_year"] = read.tax_year
    try:
        result = run_gap_loop(case, send, lambda gaps: {},
                              lambda assumptions: ACKNOWLEDGEMENT,
                              identity=None, max_passes=1)
    except ServiceUnreachable as unreachable:
        # NOTHING WAS REACHED — a different fact from a refusal the service answered
        # with, and the difference is exactly `crossed`: a payload that never left cannot have
        # been stated to anybody, so the NOT-READ defaults stay the pale-blue defaults they are.
        return rewrite_workbook(read, extra_refusals=(str(unreachable),),
                                stopped_because=layout.STOPPED_UNREACHABLE,
                                stated_at=stated_at)
    except TransportRefused as refused:
        # A SCHEMA_INVALID never arrives as a response at all — the sender raises for every
        # non-retryable code — so it is caught here and put on the cell it names AND on Computed
        # return. The message reaches that tab whether or not a cell was pinned, because a refused round has to
        # say so where a person looks for the outcome.
        # `crossed=True`: the payload reached the service, and this is its answer. A NOT-READ
        # 0.00 in it was stated, even though no response came back.
        return rewrite_workbook(read, invalid=_attribute(str(refused)),
                                extra_refusals=(str(refused),),
                                stopped_because=layout.STOPPED_TRANSPORT_REFUSED,
                                stated_at=stated_at, crossed=True)
    except PayloadRefused as refused:
        # The projector refused the case before anything was sent. Its own reason, not the
        # transport's: nothing left the machine.
        return rewrite_workbook(read, extra_refusals=(str(refused),),
                                stopped_because=layout.STOPPED_PAYLOAD_REFUSED,
                                stated_at=stated_at)
    except LoopRefused as refused:
        # The loop refuses AFTER a response arrived (an identity request, say): the round crossed.
        return rewrite_workbook(read, extra_refusals=(str(refused),),
                                stopped_because=layout.STOPPED_LOOP_REFUSED, stated_at=stated_at,
                                crossed=True)

    response = dict(result.response)
    response["gaps"] = result.gaps
    response["assumptions"] = result.assumptions
    response["unasked_boundary"] = result.unasked_boundary
    when = stated_at or (response.get("provenance") or {}).get("computed_at") or ""
    return rewrite_workbook(read, response=response, stopped_because=result.stopped_because,
                            stated_at=when)


def _collect(args) -> int:
    documents = read_extractions(args.sources)
    case = {"tax_year": args.tax_year}
    case.update(facts_from(documents, unread_required="gap"))  # an unread required box is a yellow cell, not a stop
    Path(args.out).write_bytes(build_workbook(case, documents, open_questions(case)))
    print(f"wrote {args.out}")
    return 0


def _run(args) -> int:
    data = Path(args.workbook).read_bytes()
    # in-process against the local engine; nothing is sent anywhere.
    send = local_sender()
    print("computing in-process against the local engine")
    when = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = Path(args.out or args.workbook)
    out.write_bytes(run_workbook(data, send, stated_at=when))
    print(f"wrote {out}")
    return 0


# The two forms the covered surface renders today, in the person's words; anything else prints as
# its file name, which is also what they see in the output folder.
_FORM_NAMES = {"IRS1040": "Form 1040", "IRS1040S1": "Schedule 1 (Form 1040)",
               "IRSW2G": "Form W-2G copy"}


def _identity_blanks(blanks: list, identity_path) -> str:
    """The identity boxes left blank, in the file's own words: which entries, when a
    `case.identity.ini` was given, or that none was."""
    from ..identity_file import load_identity_map, words_for
    n = len(blanks)
    if identity_path is None:
        return (f"{n} name, taxpayer-ID and address {'box is' if n == 1 else 'boxes are'} blank — "
                f"no case.identity.ini values were given")
    fields = load_identity_map()["fields"]
    terms = [fields.get(dotted.rsplit(".", 1)[-1]) for dotted in blanks]
    named = ", ".join(words_for(t) for t in terms if t)
    return (f"{n} {'box is' if n == 1 else 'boxes are'} blank — left blank in case.identity.ini: "
            f"{named}")


def _fill(args) -> int:
    """The last task: the computed return, written into the IRS fillable forms.

    The Computed return tab is the review surface, so `fill` hands its recorded
    lines to `fill_return`, which refuses when they are absent (never run) or no longer match
    (edited since the last run). Rendering an unreviewed computation is what must stay
    impossible."""
    from ..formfill import fill_return  # local import: `fill` needs an engine home, the others don't
    data = Path(args.workbook).read_bytes()
    read = read_workbook(data)
    report = fill_return(read.facts, args.out, reviewed_lines=read_reviewed_lines(data),
                         tax_year=read.tax_year, identity_path=args.identity)
    for filled in report.filled:
        name = _FORM_NAMES.get(filled.form_key, filled.out_path.name)
        line = (f"wrote {filled.out_path} — {name}: {len(filled.written)} boxes carry the "
                f"computed return")
        blanks = next((v for reason, v in filled.blank.items()
                       if reason.startswith("identity not supplied")), [])
        if blanks:
            line += "; " + _identity_blanks(blanks, args.identity)
        print(line)
    for sentence in report.stated:
        print(sentence)
    if report.not_this_return:
        print(f"{len(report.not_this_return)} forms are not part of this return.")
    if report.gate_unresolved:
        named = ", ".join(_FORM_NAMES.get(k, k) for k in report.gate_unresolved)
        print(f"{len(report.gate_unresolved)} forms were not written because this return's "
              f"answers do not settle whether they belong to it: {named}.")
    if report.not_asked_here:
        print(f"{len(report.not_asked_here)} forms are ones this version does not ask about, so "
              f"they were not written.")
    if report.ungated:
        print(f"{len(report.ungated)} form templates carry no render rule yet and are never "
              f"written.")
    print("No PDF viewer ran here. Open each file and check its figures against the "
          "Computed return tab.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m ytax_prep.client.workbook",
        description="Collect documents into a review workbook, and run compute over it.")
    commands = parser.add_subparsers(dest="command", required=True)

    collect = commands.add_parser("collect", help="documents in, workbook out")
    collect.add_argument("--sources", required=True, help="a Collector out/sources directory")
    collect.add_argument("--out", required=True, help="the .xlsx to write")
    collect.add_argument("--tax-year", type=int, default=2025, dest="tax_year")

    run = commands.add_parser("run", help="one round of compute over the workbook, in place")
    run.add_argument("--workbook", required=True)
    run.add_argument("--out", default=None, help="write elsewhere instead of in place")

    fill = commands.add_parser(
        "fill", help="the last task: write the computed return into the IRS fillable forms")
    fill.add_argument("--workbook", required=True)
    fill.add_argument("--out", required=True, help="directory for the filled PDFs")
    fill.add_argument("--identity", default=None,
                      help="your local identity file; it never leaves this computer")

    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            return _collect(args)
        if args.command == "fill":
            return _fill(args)
        return _run(args)
    except (WorkbookRefused, DocumentsRefused, WorkbookXMLError, OSError,
            PdfSurprise, RegisterSurprise, EngineNotAvailable, IdentityFileError,
            FillRefused, ServiceFactsError) as refused:
        # A refusal is a sentence for the person at the terminal, not a stack for a developer —
        # and a path that is not there is the same kind of sentence. A rewrite that cannot be
        # written is caught here too: `_run` computes the whole file before it writes a byte, so
        # the input is untouched.
        print(f"refused: {refused}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
