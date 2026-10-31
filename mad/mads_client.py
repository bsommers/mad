"""Subprocess JSON-over-CLI client for the `mads` store (`mads.contract/1`)."""
from collections.abc import Mapping
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

CLOSED_ERROR_CODES = frozenset(
    {"USAGE", "CONFLICT", "NOT_FOUND", "VALIDATION", "STORE_BUSY", "LEASE_LOST", "FORBIDDEN", "INTERNAL"}
)

TOOL_VERBS = frozenset(
    {
        "claim_task", "heartbeat", "release_task", "put_artifact", "get_artifact",
        "transition_status", "write_handoff", "take_handoff", "index_memory", "get_agent_context",
    }
)


class MadsError(ValueError):
    """Typed error raised by `mads_client.call`."""

    def __init__(
        self,
        code: str,
        message: str,
        retryable: bool = False,
        detail: Mapping[str, Any] | None = None,
    ) -> None:
        norm_code = code if code in CLOSED_ERROR_CODES else "INTERNAL"
        super().__init__(message)
        self.code = norm_code
        self.message = message
        self.retryable = bool(retryable) if norm_code != "STORE_BUSY" else True
        self.detail: dict[str, Any] = dict(detail) if detail else {}


def resolve_mads_bin(env: Mapping[str, str] | None = None) -> str | None:
    environ = env if env is not None else os.environ
    explicit = environ.get("MADS_BIN", "").strip()
    if explicit:
        p = Path(explicit)
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
        return shutil.which(explicit)
    return shutil.which("mads")


def _build_argv_and_stdin(
    mads_bin: str, verb: str, payload: Mapping[str, Any]
) -> tuple[list[str], str | None]:
    if verb == "init":
        return [mads_bin, "init"], None
    if verb == "export":
        fmt = str(payload.get("format", "md"))
        argv = [mads_bin, "export", "--format", fmt]
        if "key" in payload and payload["key"] is not None:
            argv.extend(["--key", str(payload["key"])])
        if "out" in payload and payload["out"] is not None:
            argv.extend(["--out", str(payload["out"])])
        if payload.get("force"):
            argv.append("--force")
        return argv, None
    if verb in TOOL_VERBS:
        return [mads_bin, "tool", verb], json.dumps(dict(payload))
    return [mads_bin, verb], json.dumps(dict(payload))


def call(
    verb: str,
    payload: Mapping[str, Any] | None = None,
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Invoke `mads` over subprocess (never shell=True) and parse its JSON envelope."""
    environ = dict(env if env is not None else os.environ)
    mads_bin = resolve_mads_bin(environ)
    if not mads_bin:
        raise MadsError("INTERNAL", "mads binary not found", retryable=False)

    raw_timeout = environ.get("MADS_TIMEOUT_S", "10").strip()
    try:
        timeout_s = float(raw_timeout)
    except ValueError:
        timeout_s = 10.0

    req_payload = payload if payload is not None else {}
    argv, stdin_text = _build_argv_and_stdin(mads_bin, verb, req_payload)

    try:
        proc = subprocess.run(
            argv,
            input=stdin_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(cwd) if cwd is not None else None,
            env=environ,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise MadsError("INTERNAL", f"mads {verb} timed out after {timeout_s}s") from exc
    except OSError as exc:
        raise MadsError("INTERNAL", f"cannot execute mads: {exc}") from exc

    stdout = proc.stdout or ""
    if verb == "export" and "key" in req_payload and proc.returncode == 0 and stdout.startswith("---\n"):
        return {"markdown": stdout}

    stripped = stdout.strip()
    if not stripped:
        raise MadsError("INTERNAL", f"mads {verb} exited {proc.returncode} with empty stdout")

    try:
        envelope = json.loads(stripped.splitlines()[-1])
    except json.JSONDecodeError as exc:
        raise MadsError("INTERNAL", f"mads {verb} returned non-JSON stdout") from exc

    if not isinstance(envelope, dict) or "ok" not in envelope:
        raise MadsError("INTERNAL", f"mads {verb} returned malformed envelope")

    if envelope.get("ok") is True:
        data = envelope.get("data")
        return data if isinstance(data, dict) else {"value": data}

    err = envelope.get("error")
    if isinstance(err, dict):
        code = str(err.get("code", "INTERNAL"))
        msg = str(err.get("message", f"mads {verb} failed"))
        retryable = bool(err.get("retryable", code == "STORE_BUSY"))
        detail = err.get("detail") if isinstance(err.get("detail"), dict) else None
        raise MadsError(code, msg, retryable=retryable, detail=detail)

    raise MadsError("INTERNAL", f"mads {verb} failed without error object")
