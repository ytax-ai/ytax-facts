#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

# One-shot setup + smoke test for the ytax Collector.
# Creates an isolated virtual environment, installs the package, generates
# synthetic sample documents, runs the pipeline, and runs the tests.
#
#   bash setup.sh
#
# Re-runnable. To use the tool afterwards in a new shell:
#   source .venv/bin/activate
set -euo pipefail
cd "$(dirname "$0")"

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "python3 venv module missing. On Ubuntu/Debian run:"
  echo "    sudo apt install python3-venv python3-full"
  exit 1
fi

echo "[1/5] creating virtual environment (.venv)"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/5] upgrading pip and installing the package (editable)"
python -m pip install --quiet --upgrade pip
# intake_ocr: the local AI intake's OCR reader tier — RapidOCR on ONNX Runtime.
pip install --quiet -e ".[dev,intake_ocr]"

echo "[3/5] generating synthetic sample documents (fake data only)"
python -m collector.fixtures.synthetic

echo "[4/5] running the ingestion pipeline on sample_docs/"
collector-ingest --input sample_docs/ --output out/ --no-prompt

if [ -d tests ]; then
  echo "[5/5] running tests"
  pytest -q
else
  echo "[5/5] skipping tests (this copy has no tests/ folder)"
fi

echo
echo "Done. Outputs are in out/ (redacted_docs/, sources/, manifest.json, summary_report.txt)."
echo "To use the tool in a new shell:  source .venv/bin/activate"
