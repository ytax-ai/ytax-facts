# ytax Collector — document ingestion

Privacy-preserving ingestion of US tax-document PDFs into a **neutral intermediate
representation** (IR): structured fields with confidences and source regions. Built fresh,
self-contained, synthetic-data-only. Useful standalone; also the clean-room basis for the
ytax `collector/` track (it emits a neutral IR, never any downstream engine's format).

## What it does

```
raw PDFs  →  decrypt (if needed)  →  classify (intact text)  →  manifest
          →  redact pass 1  →  extract → neutral IR  →  redact pass 2 (K-1 only)
          →  redacted_docs/  +  sources/*.json  +  manifest.json  +  summary_report.txt
```

- **Decrypt** — `pypdf` (BSD-3-Clause; AES via the `[crypto]` extra); password taken
  in-memory only (prompted hidden, never logged or written), wrong-password vs corrupt-file
  distinguished.
- **Classify** — IRS form type from page-1 identifier strings (W-2, 1099-INT/DIV/B/R, 1098,
  K-1 1065). Text layer first; an injectable OCR backend handles scans. Unknown → flagged,
  never guessed.
- **Redact** — true content removal, not boxes-on-top: the redacted PDF is **rebuilt from the
  surviving words only** (extract-filter-rebuild on the permissive PDF stack; redacted text is never
  written to the output, and non-text page content is dropped — a **deliberate** design
  tradeoff, recorded in `ingest/redact.py`). SSN/EIN matched in **dashed format only** so
  CUSIPs/lot numbers survive;
  name/address burned by label anchor; account/routing only with a context label. Per-form
  policy drives the **K-1 two-pass** case (pass 1 keeps the partnership EIN for extraction;
  pass 2 burns it).
- **Extract** — conservative, label-anchored, into the neutral IR. Each field carries a
  source region (page + bbox) for a later reconciliation/crop view. Money parses to integer
  cents when unambiguous; otherwise left unparsed (never guessed).
- **Report** — three tiers (ok / warnings / could-not-process) + a priority "nothing
  detected" list. Assists review; does **not** certify — eyeball redacted PDFs before they
  leave the machine.

## Install & run

This is a normal Python package. Use an isolated virtual environment (Ubuntu/Debian mark the
system Python as "externally managed", so installing into it directly is blocked by design).

**Fastest path — one script does everything (venv + install + sample run + tests):**

```bash
bash setup.sh
```

**Manual, equivalent:**

```bash
python3 -m venv .venv          # if this errors: sudo apt install python3-venv python3-full
source .venv/bin/activate      # prompt shows (.venv); do this in each new shell
pip install -e .               # reads pyproject.toml; no --break-system-packages needed
```

Then run it:

```bash
python -m collector.fixtures.synthetic     # writes sample_docs/*.pdf (all fake data)
collector-ingest --input sample_docs/ --output out/
# encrypted inputs: prompted once (hidden); or pass --password / --no-prompt
# leave the environment later with:  deactivate
```

Outputs: `out/redacted_docs/` (safe to move), `out/sources/<doc>.json` (neutral IR),
`out/manifest.json`, `out/summary_report.txt`. Raw inputs are never copied to `out/`.

## Layout

```
collector/                 ← project root (config, venv, tests, this README)
├── pyproject.toml
├── setup.sh
├── collector/             ← the importable package (import collector.ingest ...)
│   ├── ingest/            ← decrypt, classify, redact, extract, report, pipeline
│   └── fixtures/          ← synthetic (fake-data) PDF generator
└── tests/                 ← pytest suite
```

The outer `collector/` is the project; the inner `collector/` is the Python package — the
standard convention, and why imports read `collector.ingest`.

## Neutral IR shape

```json
{
  "form_type": "W-2",
  "source_path": "out/redacted_docs/my_w2.pdf",
  "fields": [
    {"label": "box1_wages", "value": "48,250.00", "confidence": 0.9,
     "source": {"page": 1, "x0": 228.7, "y0": 189.3, "x1": 273.2, "y1": 203.0},
     "value_cents": 4825000}
  ],
  "raw_text": "...",
  "warnings": []
}
```

No engine-specific node types or fact-paths appear here, by design. Mapping the IR into a
specific target (e.g. Fact Graph writable facts) is a separate adapter's job, deliberately
outside this package.

## Coverage status (honest)

- **Complete & tested:** decrypt, classification (all listed forms), redaction (incl.
  CUSIP-survival and K-1 two-pass), the **W-2** field extractor, reporting, the full
  pipeline, resume. 23 passing tests, synthetic fixtures only.
- **Extension points (wired, extractor not yet written):** 1099-INT/DIV/B/R, 1098, K-1
  field extraction. Classification and redaction already work for these; adding one is a new
  entry in `EXTRACTORS` + a label map, with no change to the IR or pipeline. 1099-B lots are
  tabular and intended for assisted extraction rather than generic rules.
- **OCR:** an injectable backend; the default is a no-op (text-layer path needs no OCR). For
  scanned PDFs install the `ocr` extra (`pip install -e ".[ocr]"`, pulls `easyocr` + torch,
  ~500MB models) and pass an `easyocr`-backed callable to `classify`/`page1_text`. Kept
  optional so the core stays lightweight and installable.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

## Notes & guarantees

- **Synthetic data only** in the repo: SSNs use the never-issued `000-` area; EINs and names
  are fake. The privacy fence is in `.gitignore` (`raw_docs/`, `redacted_docs/`, `out/`,
  `sources/`, `config.py`).
- Redaction is best-effort and **assists** manual review; it does not replace eyeballing a
  redacted file before transfer.
- This tool does no tax computation and produces no fil. It ingests documents to facts-ready
  data; everything downstream is a separate concern.
