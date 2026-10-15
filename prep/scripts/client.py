#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The minimum runnable client: one command, on this machine, nothing leaves it.

    YTAX_ENGINE_HOME=/path/to/engine-home python3 scripts/client.py
    python3 scripts/client.py --example wages-and-child-single-cdcc
    python3 scripts/client.py --facts my-return.json
    python3 scripts/client.py --example wages-single-mid --workbook case.xlsx   # seed, then edit
    python3 scripts/client.py --workbook case.xlsx                             # one round, in place
    python3 scripts/client.py --workbook case.xlsx --fill out/ [--identity-file case.identity.ini]

What runs: the service's own `prepare_return`, IN-PROCESS (`transport.local_sender`), against
the pinned engine at YTAX_ENGINE_HOME — the Java runner as a local subprocess. No REST
server, no API key, no network. The client pieces are the ones the rest of the repo uses: the
case projection (`project_case` refuses anything unclassified before it is sent anywhere, even
in-process), the gap loop, the interview's own words, the workbook, the AcroForm fill.

Inputs, one of:
  --example NAME   a bundled SYNTHETIC return from tests/fixtures/contract (default
                   wages-single-mid: tax 4,115.00,
                   overpayment 1,285.00). `--list-examples` names them all.
  --facts FILE     your own facts, in the REST request shape {"tax_year": 2025, "facts": {...}}
                   (a bare facts object is accepted; --tax-year supplies the year). The fact
                   schema carries no names, addresses, taxpayer-ID digits or birth days, so a
                   facts file cannot hold them; identity lives in the separate identity file.
  --workbook FILE  the Excel workbook: alone, one compute round written back in place (the
                   Computed return tab); with --example or --facts, the workbook is SEEDED from
                   them first, then run once, so you can edit it and run again.

The gap round: whatever the service still needs is asked here in the interview's own words —
an amount in dollars, true/false, or one of the schema's own choices. `--no-input` (or a
non-terminal stdin) prints the open questions and exits 2 instead of asking.

The submit-time gate: the assumptions are shown and you are asked
whether you reviewed them; `--decision reviewed|declined` answers non-interactively. Saying
nothing refuses to render.

Synthetic data only in this repo; your own facts stay on your machine — that boundary is why
no example here is ever a real return.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ytax_prep.client import LoopRefused, PayloadRefused, run_gap_loop  # noqa: E402
from ytax_prep.client.interview import choices_for, open_questions  # noqa: E402
from ytax_prep.client.transport import (  # noqa: E402
    ServiceUnreachable, TransportRefused, local_sender,
)
from ytax_prep.client.workbook.__main__ import run_workbook  # noqa: E402
from ytax_prep.client.workbook.reader import read_open_questions, read_outcome  # noqa: E402
from ytax_prep.client.workbook.writer import build_workbook  # noqa: E402
from ytax_prep.engine import EngineNotAvailable  # noqa: E402
from ytax_prep.facts import ServiceFactsError  # noqa: E402

FIXTURES = REPO / "tests" / "fixtures" / "contract"
DEFAULT_EXAMPLE = "wages-single-mid"

EXIT_OK, EXIT_GAPS, EXIT_REFUSED, EXIT_NO_ENGINE, EXIT_USAGE = 0, 2, 3, 4, 64


class ClientStop(Exception):
    """A stop this script can name: the message a person reads, and the exit code."""

    def __init__(self, message: str, code: int):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------- inputs

def example_names() -> list:
    return sorted(p.name[:-len(".facts.json")] for p in FIXTURES.glob("*.facts.json"))


def load_example(name: str) -> tuple:
    """(case, comment): the fixture's facts under the pinned year, and the words its blessed
    expectation carries about the return — printed before the numbers so a person knows what
    the example is."""
    path = FIXTURES / f"{name}.facts.json"
    if not path.is_file():
        raise ClientStop(f"no bundled example named {name!r}; --list-examples names them", EXIT_USAGE)
    facts = json.loads(path.read_text(encoding="utf-8"))["facts"]
    expected = FIXTURES / f"{name}.expected.json"
    comment = json.loads(expected.read_text(encoding="utf-8")).get("comment", "") if expected.is_file() else ""
    return {"tax_year": 2025, **facts}, comment


def load_facts_file(path: str, tax_year: int | None) -> dict:
    """The REST request body shape, or a bare facts object — the same words either way."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ClientStop(f"could not read {path}: {e}", EXIT_USAGE)
    if not isinstance(doc, dict):
        raise ClientStop(f"{path} must hold a JSON object", EXIT_USAGE)
    if "facts" in doc and isinstance(doc["facts"], dict):
        year = doc.get("tax_year", tax_year)
        facts = doc["facts"]
    else:
        year, facts = tax_year, doc
    if not isinstance(year, int):
        raise ClientStop("the tax year is not given: put \"tax_year\" beside \"facts\", or pass "
                         "--tax-year", EXIT_USAGE)
    return {"tax_year": year, **facts}


# ---------------------------------------------------------------- the gap round

def parse_answer(fact: str, raw: str):
    """A typed answer from what a person typed: dollars for an amount (whole cents, never
    rounded — the workbook's rule), true/false for a yes-or-no, one of the schema's own codes
    for a choice, a plain integer for a count or an index. Refuses by name otherwise."""
    field = fact.rsplit(".", 1)[-1]
    text = raw.strip()
    choices = choices_for(field)
    if choices:
        if text not in choices:
            raise ValueError(f"must be one of: {', '.join(choices)}")
        return text
    if field.endswith("_cents"):
        cleaned = text.replace("$", "").replace(",", "").replace(" ", "")
        negative = cleaned.startswith("(") and cleaned.endswith(")")
        if negative:
            cleaned = cleaned[1:-1]
        try:
            amount = Decimal(cleaned)
        except (InvalidOperation, ValueError):
            raise ValueError("is not an amount — dollars, like 1234.56")
        if not amount.is_finite():
            raise ValueError("is not an amount")
        cents = amount * 100
        if cents != cents.to_integral_value():
            raise ValueError("is not a whole number of cents")
        return -int(cents) if negative else int(cents)
    lowered = text.lower()
    if lowered in ("true", "yes", "y"):
        return True
    if lowered in ("false", "no", "n"):
        return False
    if text.lstrip("-").isdigit():
        return int(text)
    return text


def describe_gap(gap: dict) -> str:
    lines = ", ".join(f"line {line}" for _form, line in (gap.get("consumed_by") or []))
    where = f" (Form 1040 {lines})" if lines else ""
    return f"  {gap['fact']}{where}\n    {gap.get('why', '')}"


def make_answerer(no_input: bool):
    interactive = not no_input and sys.stdin.isatty()
    stopped = False  # a blank answer ends the asking; the next round lists what is left and stops

    def answer(gaps: list) -> dict:
        nonlocal stopped
        print("\nStill needed before a return can be computed:")
        for gap in gaps:
            print(describe_gap(gap))
        if not interactive or stopped:
            return {}
        print("\nAnswer each one (dollars for an amount, true/false, or one of the choices "
              "named); leave one blank to stop here — what was answered is kept, the rest is listed.")
        supplied = {}
        for gap in gaps:
            while True:
                raw = input(f"  {gap['fact']} = ").strip()
                if not raw:
                    stopped = True
                    return supplied
                try:
                    supplied[gap["fact"]] = parse_answer(gap["fact"], raw)
                    break
                except ValueError as e:
                    print(f"    {raw!r} {e}")
        return supplied

    return answer


def make_acknowledger(decision: str | None, no_input: bool):
    interactive = not no_input and sys.stdin.isatty()

    def acknowledge(assumptions: list):
        print("\nWhat the service assumed about this return — nobody supplied these, and each "
              "changes the return if it is wrong:")
        for a in assumptions or ["(the service reported none)"]:
            print(f"  • {a}")
        if decision:
            print(f"  -> {decision} (--decision)")
            return decision
        if not interactive:
            print("  -> no decision given (pass --decision reviewed or --decision declined); "
                  "the return is not rendered")
            return None
        print("\n  [r] I reviewed them   [d] I decline to review   [enter] neither")
        return {"r": "reviewed", "d": "declined"}.get(input("  your decision: ").strip().lower())

    return acknowledge


# ---------------------------------------------------------------- output

def dollars(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}{abs(cents) // 100:,}.{abs(cents) % 100:02d}"


def print_lines(forms: list) -> None:
    for form in forms:
        print(f"\nForm {form.get('form_id', '?')}")
        for ln in form.get("lines", []):
            cite = (ln.get("citation") or {}).get("locator", "")
            print(f"  {ln['line_id']:>4}  {dollars(ln['value_cents']):>14}  {ln.get('label', '')}"
                  f"{'  — ' + cite if cite else ''}")


def print_result(result) -> int:
    response = result.response or {}
    print(f"\nOutcome: {result.outcome} ({result.stopped_because}; {result.passes} pass(es))")
    if result.outcome == "complete":
        print_lines(result.forms)
    for r in response.get("refusals") or []:
        print(f"\nRefused: {r.get('boundary') or r.get('message') or r.get('words') or r}")
    if result.unasked_boundary:
        print("\nNot asked, by design (the coverage boundary):")
        for b in result.unasked_boundary:
            if isinstance(b, dict):
                print(f"  • {b.get('fact_class', '?')} — {b.get('why_not_supported', '')}")
            else:
                print(f"  • {b}")
    if result.outcome == "incomplete" and result.gaps:
        print("\nStopped at the questions above; answer them and run again.")
    prov = response.get("provenance") or {}
    if any(prov.values()):
        print(f"\nEngine {prov.get('engine_version')}, dictionary {prov.get('dictionary_hash')}, "
              f"input hash {prov.get('input_hash')}, computed {prov.get('computed_at')}")
    if result.outcome == "complete":
        return EXIT_OK
    if result.outcome == "incomplete":
        return EXIT_GAPS
    return EXIT_REFUSED


# ---------------------------------------------------------------- modes

def run_case(case: dict, args) -> int:
    try:
        result = run_gap_loop(case, local_sender(), make_answerer(args.no_input),
                              make_acknowledger(args.decision, args.no_input))
    except ServiceUnreachable as e:
        raise ClientStop(str(e), EXIT_NO_ENGINE)
    except (TransportRefused, LoopRefused, PayloadRefused, ServiceFactsError) as e:
        raise ClientStop(f"stopped: {e}", EXIT_REFUSED)
    return print_result(result)


def seed_workbook(case: dict, path: Path) -> None:
    """The workbook `collect` would write for these facts, with no documents behind them."""
    path.write_bytes(build_workbook(case, [], open_questions(case)))
    print(f"wrote {path} (seeded from the facts; edit it and run again)")


def run_workbook_round(path: Path, out: Path | None) -> int:
    data = path.read_bytes()
    when = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        written = run_workbook(data, local_sender(), stated_at=when)
    except ServiceUnreachable as e:
        raise ClientStop(str(e), EXIT_NO_ENGINE)
    target = out or path
    target.write_bytes(written)
    print(f"wrote {target} — open the Computed return tab; running compute IS the review.")
    # the round's last words say whether the return is complete, and when it is not, WHERE
    # each open question is — the same list the Computed return tab leads with — so a return that
    # needs several rounds is walked, not hunted. The exit code stays 0: the round ran and the
    # workbook was written; what is open is said, not signalled.
    still_open = read_open_questions(written)
    outcome = read_outcome(written)
    if still_open:
        print(f"INCOMPLETE — {len(still_open)} still open. Fill these and run compute again:")
        for said, where in still_open:
            print(f"  {said}: {where}")
    elif outcome == "complete":
        print("COMPLETE — nothing is open; the Computed return tab holds every line.")
    else:
        print(f"NOT COMPLETE — outcome {outcome or 'none'}; the Computed return tab says why.")
    return EXIT_OK


def fill_pdfs(workbook: Path, out_dir: str, identity: str | None) -> int:
    from ytax_prep.client.workbook.__main__ import _fill
    try:
        return _fill(argparse.Namespace(workbook=str(workbook), out=out_dir, identity=identity))
    except EngineNotAvailable as e:
        raise ClientStop(f"no engine: {e}", EXIT_NO_ENGINE)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__)
    p.add_argument("--example", default=None, metavar="NAME",
                   help=f"a bundled synthetic return (default {DEFAULT_EXAMPLE})")
    p.add_argument("--list-examples", action="store_true")
    p.add_argument("--facts", default=None, metavar="FILE", help="your facts, as JSON")
    p.add_argument("--tax-year", type=int, default=None, dest="tax_year")
    p.add_argument("--workbook", default=None, metavar="FILE",
                   help="the Excel workbook to run (or to seed, with --example/--facts)")
    p.add_argument("--out", default=None, help="write the run workbook elsewhere")
    p.add_argument("--fill", default=None, metavar="DIR",
                   help="after a workbook run, write the IRS fillable PDFs here")
    p.add_argument("--identity-file", default=None, metavar="PATH",
                   help="the local case.identity.ini for --fill (never sent anywhere)")
    p.add_argument("--no-input", action="store_true",
                   help="never prompt: print the open questions and stop")
    p.add_argument("--decision", choices=("reviewed", "declined"), default=None,
                   help="answer the assumptions gate without a prompt")
    args = p.parse_args(argv)

    try:
        if args.list_examples:
            print("\n".join(example_names()))
            return EXIT_OK
        if args.example and args.facts:
            raise ClientStop("--example and --facts are two sources; pick one", EXIT_USAGE)
        if args.fill and not args.workbook:
            raise ClientStop("--fill renders a run workbook's reviewed lines; give --workbook", EXIT_USAGE)

        case = comment = None
        if args.facts:
            case = load_facts_file(args.facts, args.tax_year)
        elif args.example or not args.workbook:
            case, comment = load_example(args.example or DEFAULT_EXAMPLE)
            print(f"Example {args.example or DEFAULT_EXAMPLE} — synthetic, from "
                  f"tests/fixtures/contract{': ' + comment if comment else ''}")

        if args.workbook:
            workbook = Path(args.workbook)
            if case is not None:
                seed_workbook(case, workbook)
            code = run_workbook_round(workbook, Path(args.out) if args.out else None)
            if args.fill:
                code = fill_pdfs(Path(args.out) if args.out else workbook, args.fill,
                                 args.identity_file)
            return code
        return run_case(case, args)
    except ClientStop as stop:
        print(str(stop), file=sys.stderr)
        return stop.code


if __name__ == "__main__":
    sys.exit(main())
