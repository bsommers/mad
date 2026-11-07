#!/usr/bin/env python3
"""Stateful stub for the `mads` CLI speaking `mads.contract/1`."""
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any

ERROR_CODES: dict[str, tuple[int, bool]] = {
    "USAGE": (2, False),
    "CONFLICT": (3, False),
    "NOT_FOUND": (4, False),
    "VALIDATION": (5, False),
    "STORE_BUSY": (6, True),
    "LEASE_LOST": (7, False),
    "FORBIDDEN": (8, False),
    "INTERNAL": (9, False),
}


def _emit_ok(data: dict[str, Any]) -> int:
    print(json.dumps({"ok": True, "data": data, "contract": "mads.contract/1"}))
    return 0


def _emit_err(code: str, message: str, detail: dict[str, Any] | None = None) -> int:
    exit_code, retryable = ERROR_CODES.get(code, (9, False))
    print(
        json.dumps(
            {
                "ok": False,
                "error": {
                    "code": code,
                    "message": message,
                    "retryable": retryable,
                    "detail": detail or {},
                },
            }
        )
    )
    return exit_code


def _flatten(text: str) -> str:
    return re.sub(r"[\r\n]+", " ", text.strip())


def _render_handoff_md(body: dict[str, Any], date_str: str) -> str:
    problem = str(body.get("problem", "")).strip()
    steps = [_flatten(s) for s in body.get("steps", []) if str(s).strip()]
    ctx = [_flatten(c) for c in body.get("context_refs", []) if str(c).strip()]
    verify = [_flatten(v) for v in body.get("verify", []) if str(v).strip()]
    steps_block = "".join(f"{i}. {s}\n" for i, s in enumerate(steps, start=1))
    ctx_block = "".join(f"- {c}\n" for c in ctx) if ctx else "- (none)\n"
    verify_block = "".join(f"- {v}\n" for v in verify) if verify else "- pytest -q\n"
    return (
        "---\n"
        "title: Session handoff\n"
        "keywords: [handoff, state]\n"
        f"updated: {date_str}\n"
        "---\n\n"
        "# Session handoff\n\n"
        "## Unresolved problem\n\n"
        f"{problem}\n\n"
        "## Next exact steps\n\n"
        f"{steps_block}\n"
        "## Context files to load\n\n"
        f"{ctx_block}\n"
        "## Verify with\n\n"
        f"{verify_block}"
    )


def _state_path() -> Path:
    env_p = os.environ.get("MADS_STUB_STATE")
    if env_p:
        return Path(env_p)
    return Path.cwd() / ".mads" / "stub_state.json"


def _load_state() -> dict[str, Any]:
    p = _state_path()
    if p.is_file():
        try:
            state = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(state, dict):
                state.setdefault("events", [])
                state.setdefault("artifacts", {})
                state.setdefault("handoffs", {})
                state.setdefault("claims", {})
                state.setdefault("fence", {})
                return state
        except (OSError, json.JSONDecodeError):
            pass
    return {"events": [], "artifacts": {}, "handoffs": {}, "claims": {}, "fence": {}}


def _save_state(state: dict[str, Any]) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state), encoding="utf-8")


def main(argv: list[str]) -> int:
    sleep_s = os.environ.get("MADS_STUB_SLEEP_S")
    if sleep_s:
        time.sleep(float(sleep_s))

    if os.environ.get("MADS_STUB_RAW_STDOUT") == "1":
        print("not valid json {{{")
        return 1

    if os.environ.get("MADS_STUB_EMPTY_FAIL") == "1":
        return 1

    busy_file = os.environ.get("MADS_STUB_BUSY_COUNT_FILE")
    if busy_file:
        bf = Path(busy_file)
        remaining = int(bf.read_text(encoding="utf-8").strip()) if bf.is_file() else 0
        if remaining > 0:
            bf.write_text(str(remaining - 1), encoding="utf-8")
            return _emit_err("STORE_BUSY", "database is locked")

    force_err = os.environ.get("MADS_STUB_FORCE_ERROR")
    if force_err:
        return _emit_err(force_err, f"forced {force_err}")

    args = list(argv)
    if args and args[0] == "--json":
        args = args[1:]
    if not args:
        return _emit_err("USAGE", "missing subcommand")

    if args[0] == "version":
        print("mads.contract/1")
        return 0

    if args[0] == "init":
        state = _load_state()
        _save_state(state)
        return _emit_ok(
            {
                "db_path": str(_state_path()),
                "schema_version": 3,
                "gitignore_updated": False,
            }
        )

    if args[0] == "export":
        fmt = "md"
        key = None
        out_dir = None
        i = 1
        while i < len(args):
            if args[i] == "--format" and i + 1 < len(args):
                fmt = args[i + 1]
                i += 2
            elif args[i] == "--key" and i + 1 < len(args):
                key = args[i + 1]
                i += 2
            elif args[i] == "--out" and i + 1 < len(args):
                out_dir = args[i + 1]
                i += 2
            elif args[i] == "--force":
                i += 1
            else:
                i += 1
        state = _load_state()
        if fmt == "md" and key:
            hof = state["handoffs"].get(key)
            if not hof:
                return _emit_err("NOT_FOUND", "handoff not found")
            sys.stdout.write(_render_handoff_md(hof["body"], hof["date"]))
            return 0
        if fmt == "md" and out_dir:
            return _emit_ok({"written": [], "skipped": []})
        return _emit_err("USAGE", "invalid export arguments")

    verb = args[1] if (args[0] == "tool" and len(args) > 1) else args[0]
    raw_in = sys.stdin.read()
    try:
        req = json.loads(raw_in) if raw_in.strip() else {}
    except json.JSONDecodeError as exc:
        return _emit_err("USAGE", f"invalid json: {exc}")

    if "simulate_error" in req:
        code = str(req["simulate_error"])
        return _emit_err(code, f"simulated {code}")

    state = _load_state()

    if verb == "event.append":
        seq = len(state["events"]) + 1
        state["events"].append({"seq": seq, **req})
        _save_state(state)
        return _emit_ok({"seq": seq})

    if verb == "write_handoff":
        problem = str(req.get("problem", "")).strip()
        steps = [_flatten(s) for s in req.get("steps", []) if str(s).strip()]
        if not problem:
            return _emit_err("VALIDATION", "handoff problem cannot be empty")
        if not steps:
            return _emit_err("VALIDATION", "handoff requires at least one step")
        hof_id = f"hof_{len(state['handoffs']) + 1:04d}"
        today_str = datetime.now(UTC).date().isoformat()
        body = {
            "from_agent": req.get("from_agent", "mad"),
            "to_agent": req.get("to_agent"),
            "run_id": req.get("run_id", "mad_legacy"),
            "problem": problem,
            "steps": steps,
            "context_refs": [_flatten(c) for c in req.get("context_refs", []) if str(c).strip()],
            "verify": [_flatten(v) for v in req.get("verify", []) if str(v).strip()],
        }
        state["handoffs"][hof_id] = {"body": body, "date": today_str, "taken": False}
        _save_state(state)
        return _emit_ok({"handoff_id": hof_id})

    if verb == "take_handoff":
        target_run_id = req.get("run_id", "mad_legacy")
        target_agent = req.get("agent")
        matched_hof_id = None
        matched_hof = None
        for hof_id, hof in state["handoffs"].items():
            if hof.get("taken", False):
                continue
            hof_body = hof.get("body", {})
            if hof_body.get("run_id", "mad_legacy") != target_run_id:
                continue
            if hof_body.get("to_agent") not in (None, target_agent):
                continue
            matched_hof_id = hof_id
            matched_hof = hof
            break

        if matched_hof is None:
            return _emit_err("NOT_FOUND", "no open handoff", {"run_id": target_run_id})

        matched_hof["taken"] = True
        _save_state(state)
        return _emit_ok({"handoff_id": matched_hof_id, **matched_hof["body"]})

    if verb == "claim_task":
        resource = str(req.get("resource", ""))
        if resource.startswith("handoff:"):
            return _emit_err("VALIDATION", "resource namespace is reserved", {"field": "resource"})
        ttl_raw = req.get("ttl_s", 60)
        try:
            ttl_s = int(ttl_raw)
            if ttl_s < 1 or ttl_s > 86400:
                raise ValueError()
        except (ValueError, TypeError):
            return _emit_err("VALIDATION", "ttl_s out of range", {"field": "ttl_s"})

        for c in state["claims"].values():
            if c.get("resource") == resource and c.get("released_at") is None:
                return _emit_err("CONFLICT", "resource is already claimed", {"resource": resource})

        token = int(state["fence"].get(resource, 0)) + 1
        state["fence"][resource] = token
        claim_id = f"clm_{len(state['claims']) + 1:04d}"
        expires_at = "2099-01-01T00:00:00.000Z"
        state["claims"][claim_id] = {
            "claim_id": claim_id,
            "resource": resource,
            "agent": req.get("agent", "agy"),
            "run_id": req.get("run_id", "mad_legacy"),
            "fencing_token": token,
            "released_at": None,
            "expires_at": expires_at,
            "outcome": None,
        }
        _save_state(state)
        return _emit_ok({"claim_id": claim_id, "fencing_token": token, "expires_at": expires_at})

    if verb == "release_task":
        claim = state["claims"].get(str(req.get("claim_id", "")))
        if not claim:
            return _emit_err("NOT_FOUND", "claim not found")

        try:
            req_token = int(req.get("fencing_token", -1))
        except (ValueError, TypeError):
            req_token = -1

        if int(claim.get("fencing_token", -1)) != req_token:
            return _emit_err("LEASE_LOST", "lease lost", {"reason": "stale_token", "claim_id": claim["claim_id"]})

        outcome = req.get("outcome")
        if outcome is not None and outcome in ("expired", "rolled_back", "taken"):
            return _emit_err("VALIDATION", "outcome is reserved", {"field": "outcome"})

        if claim["released_at"] is None:
            claim["released_at"] = datetime.now(UTC).isoformat()
            claim["outcome"] = outcome or "released"
            _save_state(state)

        return _emit_ok({"released": True})

    if verb == "get_agent_context":
        if os.environ.get("MADS_STUB_CONTEXT_NOT_FOUND") == "1":
            return _emit_err("NOT_FOUND", "run not found")
        budget = int(req.get("budget_bytes", 24000))
        task = str(req.get("task", ""))
        text = f"## recall\n- {task}\n" if task else ""
        encoded = text.encode("utf-8")[:budget].decode("utf-8", errors="ignore")
        return _emit_ok({"text": encoded, "items": [], "truncated": len(text.encode("utf-8")) > budget})

    if verb == "put_artifact":
        kind = str(req.get("kind", ""))
        key = str(req.get("key", ""))
        art_key = f"{kind}:{key}"
        prev = state["artifacts"].get(art_key, {"version": 0})
        ver = int(prev["version"]) + 1
        seq = len(state["events"]) + 1
        state["artifacts"][art_key] = {"version": ver, "body": req.get("body"), "event_seq": seq}
        _save_state(state)
        return _emit_ok({"version": ver, "event_seq": seq, "sha256": "0" * 64})

    if verb == "get_artifact":
        kind = str(req.get("kind", ""))
        key = str(req.get("key", ""))
        art_key = f"{kind}:{key}"
        if art_key not in state["artifacts"]:
            return _emit_err("NOT_FOUND", "artifact not found")
        return _emit_ok(state["artifacts"][art_key])

    return _emit_err("USAGE", f"unknown verb: {verb}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
