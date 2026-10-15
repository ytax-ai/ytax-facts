# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""A second reading by a local AI model, asked for, never trusted on its own say-so.

The page asks whether a person wants an AI model on their own computer to read their documents and
their filled forms again. What it tells them first is provenance only, as the parties themselves
state it: the address the page images go to and where that address came from, Ollama's own
documentation sentence about local use, and the model's name, file size and license as Ollama
reports them. It is offered only when every one of these holds — the address is this computer
(loopback, or under WSL the Windows side of the same machine), and the model is a model FILE on it
(`LocalModel.survey`), with the vision capability a page image needs. Anything else is said, not
offered.

What the model is given: page images and box captions, no tools. What it can change: nothing. Its
reading is compared here, box by box, with what the page read (documents) or what was written
(filled forms), and the differences are listed for the person to look at. On a filled form the
names and taxpayer IDs the person typed are blanked before the page is rendered, so the identity
kept on this computer never reaches a model (the page's own promise on the identity section).
"""
from __future__ import annotations

import io
import ipaddress
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

OLLAMA_FAQ_URL = "https://docs.ollama.com/faq"
# Verbatim from Ollama's FAQ (fetched 2026-09-16), quoted as theirs, never restated as ours.
OLLAMA_LOCAL_WORDS = "Ollama runs locally. We don't see your prompts or data when you run locally."
OLLAMA_CLOUD_WORDS = ("When using cloud-hosted models, we process your prompts and responses to "
                      "provide the service but do not store or log that content and never train on it.")

AGREES, DIFFERS, MODEL_BLANK, MODEL_ONLY = ("agrees", "reads differently", "not read by the model",
                                            "read only by the model")
EMPTY, CARRIED, NOT_CARRIED, PART_OF, SAME_AMOUNT, NOT_PRINTED, LINE_UNREAD = (
    "the top of the page reads as empty", "carried to this line", "not on the line it is carried to",
    "counted in this line with other documents", "the same amount appears here",
    "does not print on the filled forms", "that line was not found in the read-back")
MODEL_SEES_EMPTY = "the model reads this as empty; look at it"


class Remembered:
    """A model client that keeps every reply and gives the same question the same answer without
    asking again, since a model is slow to read: a page read once is not read again. THE SAME
    QUESTION means the same model, the same prompt, the same
    answer shape and byte-identical images — so a document or a filled form that changed, or a
    different model, is asked afresh; nothing is guessed. The replies are kept in the working
    folder beside the return (`input/case.model-readings.json`), on this computer only, and the
    model log says each time one is reused."""

    KEEP = 5000                                     # the most recent replies kept

    def __init__(self, inner, path, log=None):
        self.inner, self.path, self.log = inner, Path(path), log or (lambda text: None)
        try:
            self.store = json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else {}
        except (OSError, ValueError):
            self.store = {}                         # an unreadable file: asked afresh, rewritten

    @property
    def model(self):
        return getattr(self.inner, "model", None)

    @model.setter
    def model(self, name):
        self.inner.model = name

    def _key(self, images, prompt, schema) -> str:
        h = hashlib.sha256()
        for part in (str(self.model or ""), prompt, json.dumps(schema, sort_keys=True)):
            h.update(part.encode("utf-8")); h.update(b"\0")
        for image in (images if isinstance(images, (list, tuple)) else [images]):
            h.update(hashlib.sha256(image).digest())
        return h.hexdigest()

    def extract(self, images, prompt, schema):
        key = self._key(images, prompt, schema)
        kept = self.store.get(key)
        if kept is not None:
            self.log(f"[{time.strftime('%H:%M:%S')}] reused {self.model}'s reading from {kept.get('when', 'earlier')} "
                     f"— the same page and the same question; not asked again")
            return kept["reply"]
        reply = self.inner.extract(images, prompt, schema)
        self.store[key] = {"reply": reply, "model": self.model, "when": time.strftime("%Y-%m-%d %H:%M")}
        if len(self.store) > self.KEEP:
            for old in list(self.store)[:len(self.store) - self.KEEP]:
                del self.store[old]
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.store), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            pass                                    # kept in memory; the check goes on
        return reply


class Logged:
    """A model client whose every call is written to the page's model log: the
    request (the model, how many images, the prompt), then the reply exactly as the model sent it
    and how long it took — or the error. Images are counted, never written."""

    def __init__(self, inner, log):
        self.inner, self.log = inner, log

    @property
    def model(self):
        return getattr(self.inner, "model", None)

    @model.setter
    def model(self, name):
        self.inner.model = name

    def extract(self, images, prompt, schema):
        count = len(images) if isinstance(images, (list, tuple)) else 1
        self.log(f"[{time.strftime('%H:%M:%S')}] request to {self.model}: {count} image(s)\n{prompt}")
        started = time.monotonic()
        self.inner.last_raw = None
        try:
            reply = self.inner.extract(images, prompt, schema)
        except Exception as why:
            raw = getattr(self.inner, "last_raw", None)
            self.log(f"[{time.strftime('%H:%M:%S')}] ERROR after {time.monotonic() - started:.0f} s: "
                     f"{type(why).__name__}: {why}" + (f"\nreply as it came: {raw}" if raw else ""))
            raise
        raw = getattr(self.inner, "last_raw", None) or json.dumps(reply)
        self.log(f"[{time.strftime('%H:%M:%S')}] reply after {time.monotonic() - started:.0f} s:\n{raw}")
        return reply


# ------------------------------------------------------------------ where the pages would go
def _wsl_gateway() -> str | None:
    """Under WSL, the Windows side of this same computer is the default gateway. None elsewhere."""
    try:
        if "microsoft" not in Path("/proc/version").read_text().lower():
            return None
        for line in Path("/proc/net/route").read_text().splitlines()[1:]:
            cells = line.split()
            if len(cells) > 2 and cells[1] == "00000000":
                return str(ipaddress.IPv4Address(bytes.fromhex(cells[2])[::-1]))
    except (OSError, ValueError):
        return None
    return None


def where(address: str, gateway=_wsl_gateway) -> str:
    """`loopback`, `wsl-windows` (the Windows side of this computer, seen from WSL) or `other`."""
    host = urlparse(address).hostname or ""
    if host == "localhost":
        return "loopback"
    try:
        if ipaddress.ip_address(host).is_loopback:
            return "loopback"
    except ValueError:
        return "other"
    return "wsl-windows" if host == (gateway() if callable(gateway) else gateway) else "other"


def _size_words(n: int) -> str:
    return f"{n / 1e9:.1f} GB" if n >= 1e9 else f"{n / 1e6:.0f} MB"


def offer(survey: dict, gateway=_wsl_gateway) -> dict:
    """The page's words and choices, from `LocalModel.survey()`. `models` is empty whenever the
    check is not offered, and `note` then says why in one sentence."""
    address = survey["address"]
    place = where(address, gateway)
    source = ("the address set in OLLAMA_HOST" if survey.get("source") == "OLLAMA_HOST"
              else "Ollama's default address")
    out = {"offered": False, "models": [], "note": None, "facts": [], "address": address}
    if not survey.get("reachable"):
        out["note"] = (f"No AI model on this computer was found: Ollama did not answer at {address} "
                       f"({source}). Where Ollama runs on Windows and this page runs in WSL, "
                       "OLLAMA_HOST names the Windows side's address.")
        return out
    if place == "other":
        out["note"] = (f"Ollama answers at {address} ({source}), which is not this computer, so a "
                       "check by a model there is not offered.")
        return out
    usable = [m for m in survey.get("models", []) if m.get("local") and m.get("vision")]
    if not usable:
        out["note"] = (f"Ollama answers at {address}, but no model on it both reads images and is a "
                       "model file on this computer; a cloud-hosted model is not offered.")
        return out
    here = ("this computer's own loopback address" if place == "loopback"
            else "the default gateway, which under WSL is the Windows side of this computer")
    out["offered"] = True
    out["models"] = [{"name": m["name"],
                      "words": f"{m['name']} — a model file on this computer "
                               f"({_size_words(m['bytes'])}), license {m.get('license') or 'not stated by Ollama'}"}
                     for m in usable]
    out["facts"] = [
        f"The page images go to Ollama at {address}, {source}: {here}.",
        f"Ollama's documentation says: “{OLLAMA_LOCAL_WORDS}” ({OLLAMA_FAQ_URL})",
        f"The same documentation says of cloud-hosted models: “{OLLAMA_CLOUD_WORDS}” "
        "Those are not offered here, and OLLAMA_NO_CLOUD=1 turns them off in Ollama.",
        "The model is given the page images and the box names only, and no tools. It changes "
        "nothing: what it reads is listed beside what this page read, for you to compare.",
        "A document page is shown to the model as it is. On the filled forms, the names and "
        "taxpayer IDs you typed are blanked before the model sees them.",
    ]
    return out


# ------------------------------------------------------------------ values, as a person reads them
_MONEY_TEXT = re.compile(r"^\(?-?\$?\s*[\d,]*\d(\.\d{1,2})?\)?$")


def cents_of(text) -> int | None:
    """`"43,780.00"`, `"$43,780"`, `"(12.50)"` → cents; None when the text is not an amount."""
    t = str(text or "").strip()
    if not t or not _MONEY_TEXT.match(t):
        return None
    negative = t.startswith("(") or "-" in t
    digits = t.strip("()").replace("-", "").replace("$", "").replace(",", "").strip()
    whole, _, frac = digits.partition(".")
    cents = int(whole or "0") * 100 + int((frac + "00")[:2])
    return -cents if negative else cents


def _dollars(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) / 100:,.2f}"


def _words(kind: str, value) -> str:
    if kind == "check":
        return "checked" if value is True else "not checked"
    if kind == "money" and isinstance(value, int):
        return _dollars(value)
    return str(value)


def _same(kind: str, ours, raw) -> bool:
    if kind == "money":
        return cents_of(raw) == ours
    if kind == "check":
        return (ours is True) == (str(raw).strip().lower() in {"x", "[x]", "☒", "☑", "✓", "✔", "true", "yes", "checked"})
    return str(raw).strip().upper() == str(ours).strip().upper()


# ------------------------------------------------------------------ the documents
def _values(confirmed: dict) -> dict:
    """`Case.confirmed()` holds `(value, Evidence)` at every path — the figure and who said it.
    Both checks below want the figure. Taking the pair whole compared a Python object with what
    the model read, so every box on a restored return said "reads differently" and printed the
    object beside it (seen 2026-09-22). A bare value raises here rather than reaching a
    row: the shape is the case's, and a caller that invents its own is the way this got through."""
    out = {}
    for path, pair in confirmed.items():
        if not (isinstance(pair, tuple) and len(pair) == 2):
            raise TypeError(f"{path}: a confirmed entry is (value, Evidence), not {pair!r}")
        out[path] = pair[0]
    return out


def document_figures(documents: list, confirmed: dict) -> list[tuple]:
    """`[(document name, printed caption, kind, value, group, field)]` — each box of each read
    document, with the value the return now uses for it (the reading, or the person's correction).
    `confirmed` is `Case.confirmed()`: `(value, Evidence)` at every path."""
    from ..client.documents import FACT_GROUPS
    from ..client.form_labels import label_for
    from .readers.model import _kind_for_field
    out = []
    for doc in documents:
        if doc.form_type not in FACT_GROUPS:
            continue
        group, _ = FACT_GROUPS[doc.form_type]
        ours = {c.path.rsplit(".", 1)[-1]: c.value for c in doc.candidates}
        index = getattr(doc, "index", None)
        if index is not None:
            for path, value in _values(confirmed).items():
                if path.startswith(f"{group}[{index}]."):
                    ours[path.rsplit(".", 1)[-1]] = value
        for field, value in ours.items():
            try:
                caption = label_for(group, field)
            except KeyError:
                continue
            out.append((Path(doc.document).name, caption, _kind_for_field(doc.form_type, field), value,
                        group, field))
    return out


def check_documents(documents: list, confirmed: dict, model, model_name: str, progress=None,
                    render=None, input_folder=None, rows=None, proposed: dict | None = None) -> list[dict]:
    """Every box of every read document, read again by the model and compared with the value the
    return now uses for it (the reading, or the person's correction). One row per box either side
    has a value for. `confirmed` is `Case.confirmed()` — `(value, Evidence)` at every path;
    `proposed` is one bare value per path, the reading nobody has confirmed yet."""
    from ..client.documents import FACT_GROUPS
    from .readers.model import _kind_for_field, read_with_model
    if render is None:
        from .readers.documents import _render_png as render
    readable = [d for d in documents if d.form_type in FACT_GROUPS and getattr(d, "document", None)]
    rows = [] if rows is None else rows          # a caller's list keeps what was read before a failure
    for i, doc in enumerate(readable):
        if progress:
            progress(i, len(readable), Path(doc.document).name)
        group, label_to_field = FACT_GROUPS[doc.form_type]
        from ..client.form_labels import label_for
        captions = {}
        for field in dict.fromkeys(label_to_field.values()):
            try:
                captions[field] = label_for(group, field)   # the caption as printed (dir42)
            except KeyError:
                continue                                    # no printed box to read it from
        model.model = model_name
        path = Path(doc.document)
        if not path.is_file() and input_folder is not None:
            path = Path(input_folder) / path.name
        read = dict(read_with_model(render(path), doc.form_type, captions, model))
        # THE PAGE'S OWN SIDE, from the CASE and not only from this object. A document read in an
        # EARLIER SITTING is restored without its candidates — the session keeps the case, not the
        # reader's proposals — so taking the page's side from `doc.candidates` alone left every row
        # saying "read only by the model" after any restart, and the check produced no comparison
        # at all (seen 2026-09-22). The case has both halves: what is still proposed, and
        # what the person has confirmed, which wins.
        ours = {}
        for cand in doc.candidates:
            ours[cand.path.rsplit(".", 1)[-1]] = cand.value
        index = getattr(doc, "index", None)
        if index is not None:
            for source in (proposed or {}, _values(confirmed)):
                for path, value in source.items():
                    if path.startswith(f"{group}[{index}]."):
                        ours[path.rsplit(".", 1)[-1]] = value
        for field, caption in captions.items():
            kind = _kind_for_field(doc.form_type, field)
            have, raw = field in ours, read.get(field)
            if not have and raw is None:
                continue
            if have and raw is None:
                verdict, model_words = MODEL_BLANK, ""
            elif not have:
                verdict, model_words = MODEL_ONLY, raw
            else:
                verdict = AGREES if _same(kind, ours[field], raw) else DIFFERS
                model_words = raw
            rows.append({"where": Path(doc.document).name, "box": caption,
                         "page": _words(kind, ours[field]) if have else "",
                         "model": model_words, "verdict": verdict})
    if progress:
        progress(len(readable), len(readable), "")
    return rows


# ------------------------------------------------------------------ the filled forms
_BATCH = 4                                  # progress moves every few rows on a slow machine
_PAGE = re.compile(r"Page(\d+)\[")


def blanked(pdf_bytes: bytes, is_f1040: bool, identity_values, mask: str = "") -> bytes:
    """A copy with every identity box emptied, or set to `mask`: what the fill writes from the
    identity file — Form 1040's identity boxes — plus, on any form, a box whose text carries one of
    the identity values typed on the page (a schedule's "First Last & First Last" header too)."""
    from ..client.formfill import _identity_plane
    from ..client.pdfform.reader import PdfTemplate, field_value
    from ..client.pdfform.writer import fill_fields
    tpl = PdfTemplate(pdf_bytes)
    id_fields, _ = _identity_plane(None)
    typed = [str(v).strip() for v in identity_values if str(v or "").strip()]
    # a name or street is matched inside a box's text (a header joins two names); anything with a
    # digit — an SSN, a ZIP, an apartment "12" — only as the whole box, or it would blank amounts
    words = [t for t in typed if len(t) >= 3 and not any(c.isdigit() for c in t)]
    exact = set(typed)
    blank = {}
    for dotted, fld in tpl.fields.items():
        value = field_value(tpl, fld)
        if value in (None, "") or fld.field_type == "Btn":
            continue
        if ((is_f1040 and dotted.rsplit(".", 1)[-1] in id_fields) or value.strip() in exact
                or any(t in value for t in words)):
            blank[dotted] = mask
    return fill_fields(pdf_bytes, blank) if blank else pdf_bytes


def entries(pdf_bytes: bytes) -> dict:
    """{page index: [(written value, widget rectangle)]} — every non-blank, non-zero text entry.
    A zero prints as a zero on a line nothing reaches; a model's minute is spent where a figure is."""
    from ..client.pdfform.reader import PdfTemplate, field_value
    tpl = PdfTemplate(pdf_bytes)
    pages: dict = {}
    for dotted, fld in tpl.fields.items():
        if fld.field_type == "Btn":
            continue
        value = field_value(tpl, fld)
        if value in (None, "") or cents_of(value) == 0:
            continue
        widget = tpl.resolve(fld.widget_ref)
        rect = widget.get("/Rect") if isinstance(widget, dict) else None
        m = _PAGE.search(dotted)
        if not rect or not m:
            continue
        pages.setdefault(int(m.group(1)) - 1, []).append((value, [float(c) for c in rect]))
    return pages


def render_page(pdf_bytes: bytes, index: int, dpi: int = 150) -> bytes:
    """One whole page with its form fields drawn — the filled values, as they print."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf_bytes)
    try:
        doc.init_forms()
        image = doc[index].render(scale=dpi / 72, may_draw_forms=True).to_pil().convert("RGB")
    finally:
        doc.close()
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def render_rows(pdf_bytes: bytes, index: int, rects: list, dpi: int = 200) -> list[bytes]:
    """Each entry's row, cut from the page as it prints (form fields drawn): from the left margin,
    where the line number and caption are printed, to the right edge of the entry's box."""
    import pypdfium2 as pdfium
    scale = dpi / 72
    doc = pdfium.PdfDocument(pdf_bytes)
    try:
        doc.init_forms()
        page = doc[index]
        width, height = page.get_size()
        image = page.render(scale=scale, may_draw_forms=True).to_pil().convert("RGB")
    finally:
        doc.close()
    rows = []
    for x0, y0, x1, y1 in rects:
        # one point either side: four showed the edge of the neighbouring line, and a model read
        # line 8's zero for line 9's total (measured, synthetic profile-C)
        box = (0, int(max(0, height - y1 - 1) * scale), int(min(width, x1 + 4) * scale),
               int(min(height, height - y0 + 1) * scale))
        buf = io.BytesIO()
        image.crop(box).save(buf, format="PNG")
        rows.append(buf.getvalue())
    return rows


def _rows_schema(n: int) -> dict:
    item = {"type": "object", "properties": {"line": {"type": "string"}, "value": {"type": "string"}},
            "required": ["line", "value"], "additionalProperties": False}
    keys = [f"image_{i + 1}" for i in range(n)]
    return {"type": "object", "properties": {k: item for k in keys}, "required": keys,
            "additionalProperties": False}


def check_filled(out_dir, identity_values, form_names: dict, model, model_name: str,
                 progress=None, render=render_rows, rows=None, readings=None) -> list[dict]:
    """Every figure written on the filled forms, read back by the model off the printed page — a
    row cut around each entry, the line number named by the model from what is printed there (the
    PDF's internal field names carry no meaning). A box that prints blank, or prints something else,
    is listed; one `agrees` row per form says how many matched."""
    work = []
    for pdf in sorted(Path(out_dir).glob("*.pdf")):
        stem = pdf.stem.partition("-")[0]
        copy = blanked(pdf.read_bytes(), stem == "f1040", identity_values)
        for index, found in sorted(entries(copy).items()):
            for start in range(0, len(found), _BATCH):
                work.append((pdf, stem, copy, index, found[start:start + _BATCH]))
    total = sum(len(w[4]) for w in work)
    done, agreed = 0, {}
    rows = [] if rows is None else rows
    for pdf, stem, copy, index, batch in work:
        where_ = f"{pdf.name}, page {index + 1}"
        if progress:
            progress(done, total, where_)
        form = form_names.get(stem, pdf.stem)
        prompt = (f"Each image is one row cut from page {index + 1} of {form}, a filled tax form, in order "
                  "image_1, image_2, and so on. For each image give the line number printed at the "
                  "left of the row (\"line\") and the entry typed in the rightmost box (\"value\"), "
                  "exactly as printed; an empty string when that box is blank.")
        model.model = model_name
        reply = model.extract(render(copy, index, [r for _, r in batch]), prompt, _rows_schema(len(batch)))
        reply = reply if isinstance(reply, dict) else {}
        for i, (value, _) in enumerate(batch):
            got = reply.get(f"image_{i + 1}") or {}
            line = str(got.get("line") or "").strip() if isinstance(got, dict) else ""
            seen = str(got.get("value") or "").strip() if isinstance(got, dict) else ""
            cents = cents_of(value)
            same = (cents_of(seen) == cents) if cents is not None else seen.upper() == value.strip().upper()
            if readings is not None:
                readings.append({"file": pdf.name, "page": index + 1, "line": line, "written": value,
                                 "seen": seen, "same": same})
            if same:
                agreed[pdf.name] = agreed.get(pdf.name, 0) + 1
                continue
            rows.append({"where": where_, "box": f"line {line}" if line else "an entry",
                         "page": _dollars(cents) if cents is not None else value, "model": seen,
                         "verdict": DIFFERS if seen else MODEL_BLANK})
        done += len(batch)
    for name in sorted(agreed):
        rows.append({"where": name, "box": f"{agreed[name]} " + ("entry" if agreed[name] == 1 else "entries"),
                     "page": "", "model": "", "verdict": AGREES})
    if progress:
        progress(total, total, "")
    return rows


# ------------------------------------------------------------------ what is empty, and where figures print
_TOP = {"type": "string", "enum": ["filled", "empty", "no such box"]}
_REVIEW = {"type": "object", "properties": {
    "name_at_top": _TOP, "ssn_at_top": _TOP,
    "empty_boxes": {"type": "array", "maxItems": 5, "items": {
        "type": "object", "properties": {"line": {"type": "string"}, "caption": {"type": "string"}},
        "required": ["line", "caption"], "additionalProperties": False}}},
    "required": ["name_at_top", "ssn_at_top", "empty_boxes"], "additionalProperties": False}
PRIVATE = "(kept on this computer)"


def page_count(pdf_bytes: bytes) -> int:
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf_bytes)
    try:
        return len(doc)
    finally:
        doc.close()


_LINE_NUMBER = re.compile(r"^\s*(line\s+)?\d{1,2}[a-z]?\s*$", re.I)


def review_blanks(out_dir, identity_values, form_names: dict, model, model_name: str,
                  progress=None, render=None, rows=None, pages=page_count, joint: bool = False) -> list[dict]:
    """Each filled page, looked over by the model for boxes that print EMPTY where the form asks for
    an entry — the check a read-back cannot make, because it reads only what was written. The
    identity typed on the page is shown to the model as the words "(kept on this computer)", never
    as itself, so a filled name box still reads as filled."""
    render = render or render_page
    rows = [] if rows is None else rows
    work = []
    for pdf in sorted(Path(out_dir).glob("*.pdf")):
        stem = pdf.stem.partition("-")[0]
        copy = blanked(pdf.read_bytes(), stem == "f1040", identity_values, mask=PRIVATE)
        work += [(pdf, stem, copy, i) for i in range(pages(copy))]
    for n, (pdf, stem, copy, index) in enumerate(work):
        where_ = f"{pdf.name}, page {index + 1}"
        if progress:
            progress(n, len(work), where_)
        form = form_names.get(stem, pdf.stem)
        status = ("a joint return" if joint else
                  "not a joint return, so every spouse box is rightly empty")
        prompt = (f"This image is page {index + 1} of {form}, a filled U.S. tax form; it is {status}. "
                  "Say whether the name box and the social security number box at the top of the page "
                  "are filled or empty (the words \"(kept on this computer)\" in a box count as "
                  "filled). Then list up to 5 numbered lines whose amount box is empty although a "
                  "line after it on this page carries an amount built from it — give each one's "
                  "printed line number and caption. Do not list spouse or dependent boxes, optional "
                  "boxes, or boxes with no line number.")
        model.model = model_name
        reply = model.extract(render(copy, index), prompt, _REVIEW)
        reply = reply if isinstance(reply, dict) else {}
        for key, words in (("name_at_top", "Name(s) shown on the return, at the top"),
                           ("ssn_at_top", "Social security number, at the top")):
            # measured: on Form 1040 page 2, which has no header, the model answered "empty" —
            # a form's name and number are at the top of its first page only
            if index == 0 and reply.get(key) == "empty":
                rows.append({"where": where_, "box": words, "page": "", "model": "empty",
                             "verdict": EMPTY})
        for box in (reply.get("empty_boxes") or [])[:5]:
            if not isinstance(box, dict):
                continue
            line, caption = str(box.get("line") or ""), str(box.get("caption") or "")
            # measured (synthetic profile-C, single): the model listed the spouse's boxes ("N/A")
            # and the signature block ("Sign Here") — rightly empty; only a numbered line is kept
            if not _LINE_NUMBER.match(line) or (not joint and "spouse" in caption.lower()):
                continue
            line = re.sub(r"(?i)^\s*line\s+", "", line).strip()
            rows.append({"where": where_, "box": f"line {line} {caption}".strip(), "page": "",
                         "model": "empty", "verdict": MODEL_SEES_EMPTY})
    if progress:
        progress(len(work), len(work), "")
    return rows


def trace(figures: list, readings: list, rows=None, line_map=None) -> list[dict]:
    """Each amount read from a document, and where it shows on the filled forms. Where the service's
    own line table says a Form 1040 line is built from that box (`LINE_MAP` `derived_from`), the
    line is named: "carried to this line" when the line prints exactly that amount, "counted in this
    line with other documents" when several documents feed it, and "not on the line it is carried
    to" when this document alone feeds it and the line prints something else. Any other amount is
    only ever "the same amount appears here" — an equal figure elsewhere is a coincidence to look
    at, not proof (a W-2's boxes 1, 3 and 5 are often equal, and boxes 3 and 5 print on no Form
    1040 line)."""
    if line_map is None:
        from ..service.lines import LINE_MAP as line_map
    rows = [] if rows is None else rows
    feeds = {}
    for spec in line_map:
        for source in spec.get("derived_from", []):
            feeds.setdefault(source, []).append(spec["line_id"])
    sources = {}
    for figure in figures:
        sources[f"{figure[4]}[].{figure[5]}"] = sources.get(f"{figure[4]}[].{figure[5]}", 0) + 1
    on_1040 = {}
    for r in readings:
        if r["file"].startswith("f1040.") and r["line"]:
            on_1040[r["line"].strip().lower()] = r
    for document, caption, kind, value, group, field in figures:
        if kind != "money" or not isinstance(value, int) or value == 0:
            continue
        key = f"{group}[].{field}"
        lines = feeds.get(key, [])
        if lines:
            for line in lines:
                reading = on_1040.get(line.lower())
                printed = cents_of(reading["written"]) if reading else None
                if printed == value:
                    verdict = CARRIED
                elif sources.get(key, 0) > 1:
                    verdict = PART_OF
                elif reading is None:
                    verdict = LINE_UNREAD           # a zero line is not read back; nor is a misread label
                else:
                    verdict = NOT_CARRIED
                rows.append({"where": document, "box": caption, "page": _dollars(value),
                             "model": f"Form 1040, line {line}" + (f", which prints {_dollars(printed)}"
                                                                   if printed is not None and printed != value else ""),
                             "verdict": verdict})
            continue
        hits = [r for r in readings if cents_of(r["seen"]) == value or cents_of(r["written"]) == value]
        where_ = "; ".join(f"{r['file']}, page {r['page']}" + (f", line {r['line']}" if r["line"] else "")
                           for r in hits)
        rows.append({"where": document, "box": caption, "page": _dollars(value), "model": where_,
                     "verdict": SAME_AMOUNT if hits else NOT_PRINTED})
    return rows
