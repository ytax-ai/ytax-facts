# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The application's transport: `prepare_return` run IN-PROCESS against the pinned engine.

Nothing here opens a socket. `local_sender` calls the service's own code on this machine, the
engine runs as a local subprocess, and every byte stays here. The HTTP senders that post a return to
a REST server are server-side tooling and are not part of the application.

THE RULE THAT MATTERS. An error this module cannot truthfully express in the loop's vocabulary
STOPS. It does not get assigned the nearest-looking outcome: a missing required field is not
`refused`, because `refused` means *no data fixes this*, which is exactly false.
"""
from __future__ import annotations


# Codes that mean "try again" — the return may be fine; something else was not.
_RETRYABLE = {"ENGINE_UNAVAILABLE", "RATE_LIMITED"}


class TransportRefused(ValueError):
    """The shim stopped rather than translate something it cannot say truthfully."""


class ServiceUnreachable(TransportRefused):
    """Nothing was reached at all — a different fact from a service that answered with a
    refusal, and the caller's crossed/stated logic needs to tell them apart: a payload that never
    left cannot have been stated to anybody. A subclass, so callers that only distinguish
    refusal-vs-success keep working."""


def flatten_prepare_envelope(envelope: dict) -> dict:
    """One `prepare_return` envelope -> the loop's shape. Flattening only, nothing invented; the
    one function every sender calls, so no two paths can read the same answer two ways."""
    result = envelope.get("result") or {}
    return {
        "outcome": result.get("outcome"),
        "versions": result.get("versions") or {},      # ECHOED, not asserted
        "gaps": result.get("gaps") or [],
        "assumptions": result.get("assumptions") or [],
        "assumption_details": result.get("assumption_details") or [],
        "unasked_boundary": result.get("unasked_boundary") or [],
        "forms": result.get("forms") or [],
        "refusals": envelope.get("refusals") or [],
        "provenance": {k: envelope.get(k) for k in
                       ("engine_version", "dictionary_hash", "input_hash", "computed_at")},
    }


NO_ENGINE_HELP = (
    "no engine on this machine: {reason}. Point YTAX_ENGINE_HOME at an engine home at the "
    "pin — the package build stages one (BUILD.md, 'Run from the source files'); put it "
    "somewhere that survives a reboot, not /tmp. Nothing was computed.")


def local_sender(ops=None):
    """The `send` callable for `prepare_return` IN-PROCESS: the service's own code against
    the pinned engine at YTAX_ENGINE_HOME, on this machine. No server, no key, no network —
    the engine runs as a local subprocess and every byte stays here.

    The same flatten and the same error mapping the REST server applies, so the two paths cannot
    disagree: a retryable code (`ENGINE_UNAVAILABLE`,
    `RATE_LIMITED`) is the loop's `error` outcome; every other `OperationError` STOPS by name
    (`SCHEMA_INVALID` included — a missing field is not `refused`, the rule this file exists
    for); an engine that cannot be found is `ServiceUnreachable` with the recipe; anything else is
    an `internal error` with the exception TYPE and never its text (a transcript is a log).

    `ops` is injectable for tests; the default constructs `Operations()` lazily, which needs no
    engine until a return is actually resolved (the gap round is engine-free)."""
    from ..engine import EngineNotAvailable
    from ..engine.adapter import discover_pin
    from ..service import OperationError, Operations
    operations = ops if ops is not None else Operations()

    def send(payload: dict) -> dict:
        facts = {k: v for k, v in payload.items() if k != "tax_year"}
        try:
            envelope = operations.prepare_return({"tax_year": payload["tax_year"], "facts": facts})
        except OperationError as e:
            if e.code == "ENGINE_UNAVAILABLE":
                # An engine that is not THERE is not a transient outage to retry into: name the
                # recipe. (The service wraps the missing home in the same code a crashed engine
                # gets, because to a caller on the wire they are the same thing; here they are
                # not — the person reading this can fix one of them.)
                try:
                    discover_pin()
                except EngineNotAvailable as reason:
                    raise ServiceUnreachable(NO_ENGINE_HELP.format(reason=reason))
            if e.code in _RETRYABLE:
                return {"outcome": "error"}
            raise TransportRefused(f"{e.code}: {e.message}")
        except EngineNotAvailable as e:
            raise ServiceUnreachable(NO_ENGINE_HELP.format(reason=e))
        except Exception as e:  # never leak internals: the server's own shape, the type only
            raise TransportRefused(f"SCHEMA_INVALID: internal error ({type(e).__name__})")
        return flatten_prepare_envelope(envelope)

    return send
