# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The local model client: Ollama on the person's own machine, nothing else.

`LocalModel` talks to `http://127.0.0.1:11434` — Ollama's default bind — over stdlib
`urllib.request` alone; no new dependency. It lists the installed models that declare the
`"vision"` capability (`POST /api/show` per tag, per Ollama's documented API) and runs one
`POST /api/chat` call per page with `format` set to a JSON schema and `stream: false`, so the
reply is exactly the schema's shape or the call fails — never free text to be parsed loosely.

Ollama simply not running (the common case: nobody has it, or hasn't started it) is not an error
here: `available()` treats a refused connection as "no vision models" (`[]`), the same as an
installed-but-vision-less model list. Anything else — a real request that fails after Ollama does
answer — raises `ModelUnavailable`, which the caller (the model reader, the loop) treats as "this
page goes unread by the model tier", never as a value.

`FakeModel` carries the identical two-method interface (`available`, `extract`) so every test in
this repo — and the corpus harness — can drive the model tier with no network and no GPU: it
returns canned dicts in order and records every call it received.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse

_NETWORK_ERRORS = (urllib.error.URLError, OSError, TimeoutError, ConnectionError)

DEFAULT_BASE = "http://127.0.0.1:11434"


def ollama_base(environ=None) -> tuple[str, str]:
    """`(base URL, where it came from)`. Ollama's own variable, `OLLAMA_HOST`, names where its
    server listens; the same variable is how a person points this page at it (inside
    WSL, Ollama running on the Windows side is at the default gateway, not at 127.0.0.1). Ollama
    accepts a bare `host`, `host:port` or a URL; a missing port is its default 11434, and the bind
    address `0.0.0.0` is reached as 127.0.0.1, as Ollama's own client does."""
    host = ((environ if environ is not None else os.environ).get("OLLAMA_HOST") or "").strip()
    if not host:
        return DEFAULT_BASE, "default"
    if "://" not in host:
        host = "http://" + host
    parsed = urlparse(host)
    name = parsed.hostname or "127.0.0.1"
    if name == "0.0.0.0":
        name = "127.0.0.1"
    if ":" in name:
        name = f"[{name}]"
    return f"{parsed.scheme or 'http'}://{name}:{parsed.port or 11434}", "OLLAMA_HOST"


class ModelUnavailable(RuntimeError):
    """Ollama is running but a specific call failed, or no vision model is installed at all."""


class LocalModel:
    """A thin, stdlib-only client for Ollama's HTTP API, scoped to what the model reader needs."""

    def __init__(self, model: str | None = None, base: str | None = None,
                 timeout: float = 300):
        self.model = model
        self.source = "given"
        if base is None:
            base, self.source = ollama_base()
        self.base = base.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> dict:
        request = urllib.request.Request(self.base + path, method="GET")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base + path, data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def available(self) -> list[str]:
        """Installed models with the `"vision"` capability. `[]` when Ollama is not running —
        a connection refusal is silence, not a fault; a fault surfaces only from `extract()`."""
        try:
            tags = self._get("/api/tags")
        except _NETWORK_ERRORS:
            return []
        names = [entry["name"] for entry in tags.get("models", []) if "name" in entry]
        vision = []
        for name in names:
            try:
                info = self._post("/api/show", {"model": name})
            except _NETWORK_ERRORS:
                continue
            if "vision" in info.get("capabilities", []):
                vision.append(name)
        return vision

    def survey(self) -> dict:
        """What a person is told before choosing a local check, as Ollama itself
        reports it: whether it answered at this address, its version, and each installed model
        with its file size, license and whether it is a model file on this computer at all.

        A model is `local` only when Ollama reports a model FILE for it — a GGUF of non-zero size
        and no remote host. Ollama also lists cloud-hosted models, whose prompts Ollama's own
        documentation says it processes on its servers; those are never offered. `vision` is the
        capability a page image needs."""
        out = {"address": self.base, "source": self.source, "reachable": False,
               "version": None, "models": [], "problem": None}
        try:
            tags = self._get("/api/tags")
        except _NETWORK_ERRORS:
            out["problem"] = f"Ollama did not answer at {self.base}."
            return out
        out["reachable"] = True
        try:
            out["version"] = self._get("/api/version").get("version")
        except _NETWORK_ERRORS:
            pass
        for entry in tags.get("models", []):
            name = entry.get("name")
            if not name:
                continue
            try:
                info = self._post("/api/show", {"model": name})
            except _NETWORK_ERRORS:
                continue
            details = entry.get("details") or info.get("details") or {}
            remote = bool(entry.get("remote_host") or entry.get("remote_model")
                          or info.get("remote_host") or info.get("remote_model"))
            size = entry.get("size") or 0
            # ASSUMED, not observed (no cloud model on the box that measured this, Ollama 0.34.1):
            # a cloud model's tags entry carries a remote host, or no file size, or "cloud" in its
            # name. Any one refuses it — a local model named "cloudy" is refused too, the safe way.
            # Check against a real cloud entry at the next Ollama upgrade.
            local = (not remote and size > 0 and details.get("format") == "gguf"
                     and "cloud" not in name.lower())
            license_name = (info.get("model_info") or {}).get("general.license")
            if not license_name:
                text = (info.get("license") or "").strip()
                license_name = text.splitlines()[0].strip() if text else None
            out["models"].append({"name": name, "bytes": size, "license": license_name,
                                  "vision": "vision" in (info.get("capabilities") or []),
                                  "local": local})
        return out

    @staticmethod
    def _chat_payload(model: str, image_png: bytes, prompt: str, schema: dict) -> dict:
        """The exact body `extract()` posts to `/api/chat` — a pure function so request-building
        is testable with no network at all."""
        return {
            "model": model,
            "messages": [{
                "role": "user",
                "content": prompt,
                # one page, or (the filled-forms check) several cut rows in order
                "images": [base64.b64encode(image).decode("ascii")
                           for image in (image_png if isinstance(image_png, (list, tuple)) else [image_png])],
            }],
            "format": schema,
            "stream": False,
        }

    def extract(self, image_png: bytes, prompt: str, schema: dict) -> dict:
        """One page, one call: the model's JSON reply, already schema-shaped by Ollama's own
        `format` constraint. Raises `ModelUnavailable` for anything short of that — no model
        installed, Ollama refuses the call, or the reply is not the JSON it promised."""
        model = self.model
        if model is None:
            available = self.available()
            if not available:
                raise ModelUnavailable("no vision-capable model is installed")
            model = available[0]
        payload = self._chat_payload(model, image_png, prompt, schema)
        try:
            result = self._post("/api/chat", payload)
        except _NETWORK_ERRORS as exc:
            raise ModelUnavailable(str(exc)) from exc
        try:
            content = result["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise ModelUnavailable("Ollama's reply carried no message content") from exc
        self.last_raw = content                  # the reply as it came, for the page's model log
        try:
            parsed = json.loads(content)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ModelUnavailable("the model's reply was not JSON") from exc
        return parsed


class FakeModel:
    """Same interface as `LocalModel`, no network. `replies` is consumed in order by `extract()`;
    an entry that is an exception instance is raised instead of returned, so tests can exercise
    `ModelUnavailable` propagation without touching a socket."""

    def __init__(self, replies: list):
        self._replies = list(replies)
        self.calls: list[dict] = []

    def available(self) -> list[str]:
        return ["fake-vision-model"]

    def extract(self, image_png: bytes, prompt: str, schema: dict):
        self.calls.append({"image_png": image_png, "prompt": prompt, "schema": schema})
        reply = self._replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return reply
