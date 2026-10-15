# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Pipeline orchestration + CLI.

Flow per file:
    decrypt (if needed) -> classify (intact text) -> record manifest
      -> redact pass 1 -> extract (from pass-1 output, EIN still present for K-1)
      -> redact pass 2 if required (K-1: burn partnership EIN)
      -> write neutral IR JSON
Then: write manifest.json and summary_report.txt.

Privacy: raw inputs stay in the input dir; only redacted PDFs, the manifest, and
per-document IR JSON are written to the output dir. Passwords live only in memory.
The IR's `raw_text` is held in memory and NOT serialised (models.to_json): it is
whole-page text captured from the pass-1 file, so it carried the K-1 partnership EIN
-- and anything redaction missed -- into out/sources/ in plaintext.

CLI:
    python -m collector.ingest.pipeline --input raw_docs/ --output out/
    python -m collector.ingest.pipeline --input raw_docs/ --output out/ --password ****
"""
from __future__ import annotations

import argparse
import getpass
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from . import decrypt as dec
from .classify import classify
from .extract import extract
from .models import ExtractedDocument, FormType
from .redact import policy_for, redact_file
from .report import FileResult, Tier, render_report, tier_for


def _needs_pass2(form_type: FormType) -> bool:
    return form_type is FormType.K1_1065


def _resume(
    in_path: Path, redacted_out: Path, ir_path: Path, notes: list[str],
) -> tuple[FileResult, Optional[ExtractedDocument]]:
    """Pick a file back up from the artifacts the previous sitting left.

    The IR JSON is preferred over re-extraction, and that is not an optimisation. On a K-1, pass 2
    burns the partnership EIN *after* extraction read it, so the final redacted PDF cannot yield
    what the first run legitimately got. The IR is the record of that sitting; re-deriving from the
    artifact would silently return less.

    Re-extraction is the fallback for a run interrupted between the two writes — the redacted PDF
    exists, the IR does not. It says so in the notes rather than presenting a thinner result as
    though it were the original.
    """
    if ir_path.exists():
        try:
            ir = ExtractedDocument.from_json(ir_path.read_text())
        except (ValueError, KeyError) as e:
            return FileResult(in_path.name, "(unreadable)", Tier.FAIL,
                              notes=notes + [f"resume: {ir_path.name} is not readable IR: {e}"]), None
        notes.append("resumed (redaction already done; IR reloaded)")
        return FileResult(
            in_path.name, ir.form_type.value, tier_for(notes, len(ir.fields), processed=True),
            fields_extracted=len(ir.fields), notes=notes,
        ), ir

    form_type, warn = classify(redacted_out)
    if warn:
        notes.append(warn)
    if form_type is FormType.UNKNOWN:
        return FileResult(in_path.name, form_type.value, Tier.FAIL,
                          notes=notes + ["resume: cannot classify the redacted artifact"]), None
    ir = extract(redacted_out, form_type)
    ir.source_path = str(redacted_out)
    ir_path.write_text(ir.to_json())
    notes.append("resumed (IR was missing; re-extracted from the redacted artifact)")
    notes.extend(ir.warnings)
    return FileResult(
        in_path.name, form_type.value, tier_for(notes, len(ir.fields), processed=True),
        fields_extracted=len(ir.fields), notes=notes,
    ), ir


def process_file(
    in_path: Path,
    out_dir: Path,
    password: Optional[str] = None,
) -> tuple[FileResult, Optional[ExtractedDocument]]:
    notes: list[str] = []
    redacted_dir = out_dir / "redacted_docs"
    sources_dir = out_dir / "sources"
    redacted_dir.mkdir(parents=True, exist_ok=True)
    sources_dir.mkdir(parents=True, exist_ok=True)

    redacted_out = redacted_dir / in_path.name
    ir_path = sources_dir / (in_path.stem + ".json")
    if redacted_out.exists():
        # RESUME. Redaction is skipped because it is expensive and destructive, and redoing it on an
        # already-redacted file would find nothing left to burn. Everything DOWNSTREAM of it must
        # still happen: the old code returned here with no IR, so a second sitting produced nothing
        # for the client to read, and the manifest was then rewritten without the skipped entries —
        # wiping it. The put-it-down-and-pick-it-up property the whole flow is built on was
        # exactly the one that did not hold.
        return _resume(in_path, redacted_out, ir_path, notes)

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        # 1. decrypt if needed
        working = tmp / in_path.name
        try:
            if dec.is_encrypted(in_path):
                dec.decrypt_to(in_path, working, password)
            else:
                shutil.copy2(in_path, working)
        except dec.WrongPassword:
            return FileResult(in_path.name, "(encrypted)", Tier.FAIL,
                              notes=["wrong/missing password"]), None
        except dec.CorruptFile as e:
            return FileResult(in_path.name, "(unreadable)", Tier.FAIL,
                              notes=[str(e)]), None

        # 2. classify on intact text
        form_type, warn = classify(working)
        if warn:
            notes.append(warn)
        if form_type is FormType.UNKNOWN:
            # Still copy through unredacted? No — unknown forms are not emitted.
            return FileResult(in_path.name, form_type.value, Tier.FAIL,
                              notes=notes or ["unknown form type"]), None

        # 3. redact pass 1
        pass1 = tmp / ("p1_" + in_path.name)
        rects = redact_file(working, pass1, policy_for(form_type, 1))

        # 4. extract from pass-1 output (K-1 EIN still present here)
        ir = extract(pass1, form_type)
        notes.extend(ir.warnings)

        # 5. redact pass 2 if required, else pass1 is final
        if _needs_pass2(form_type):
            rects += redact_file(pass1, redacted_out, policy_for(form_type, 2))
        else:
            shutil.copy2(pass1, redacted_out)

    # 6. write neutral IR JSON (point the IR at the redacted artifact)
    ir.source_path = str(redacted_out)
    (sources_dir / (in_path.stem + ".json")).write_text(ir.to_json())

    tier = tier_for(notes, len(ir.fields), processed=True)
    return FileResult(
        in_path.name, form_type.value, tier,
        rects_redacted=rects, fields_extracted=len(ir.fields), notes=notes,
    ), ir


def run(input_dir: Path, output_dir: Path, password: Optional[str]) -> list[FileResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(p for p in input_dir.iterdir() if p.suffix.lower() == ".pdf")
    results: list[FileResult] = []

    # MERGED, never replaced. The manifest is one of the three things `out/` carries, and a
    # run that touches one file must not erase what the others recorded. Rewriting it from this
    # run's results alone is what emptied it on a second sitting, when every file resumed.
    manifest_path = output_dir / "manifest.json"
    manifest: dict[str, str] = {}
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text())
            if isinstance(existing, dict):
                manifest.update({str(k): str(v) for k, v in existing.items()})
        except ValueError:
            pass        # unreadable manifest: rebuild it from this run rather than refuse the run

    for p in pdfs:
        res, _ir = process_file(p, output_dir, password=password)
        results.append(res)
        if res.form_type not in ("(skipped)", "(encrypted)", "(unreadable)", "UNKNOWN"):
            manifest[p.name] = res.form_type
    manifest_path.write_text(json.dumps(manifest, indent=2))
    (output_dir / "summary_report.txt").write_text(render_report(results))
    return results


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Privacy-preserving tax-document ingestion.")
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--password", default=None,
                    help="PDF password; if omitted you are prompted once (hidden).")
    ap.add_argument("--no-prompt", action="store_true",
                    help="do not prompt for a password even if files are encrypted")
    args = ap.parse_args(argv)

    password = args.password
    if password is None and not args.no_prompt:
        any_enc = any(
            dec.is_encrypted(p) for p in args.input.iterdir()
            if p.suffix.lower() == ".pdf"
        )
        if any_enc:
            password = getpass.getpass("PDF password (hidden, used in-memory only): ")

    results = run(args.input, args.output, password)
    print(render_report(results))
    print(f"Outputs in: {args.output}/  (redacted_docs/, sources/, manifest.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
