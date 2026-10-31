"""mads-backed StateBackend implementation with STORE_BUSY retry and graceful fallback."""
from collections.abc import Mapping, Sequence
from datetime import date, datetime
import os
from pathlib import Path
import random
import tempfile
import time
from typing import Any

from mad.files_backend import FilesBackend, _clip_utf8_lines
from mad.handoff import _flatten
from mad.mads_client import MadsError, call, resolve_mads_bin
from mad.store import VALID_AGENTS, VALID_KINDS, append_log as _store_append_log
from mad.telemetry import read_telemetry as _read_telemetry, write_telemetry_atomic as _write_telemetry_atomic

MAD_RUN_ID = "mad_legacy"
TELEMETRY_KEY = "mad/agent_telemetry"
STORE_BUSY_RETRIES = 3

_FALLBACK_LOGGED = False


def reset_fallback_notice_for_testing() -> None:
    global _FALLBACK_LOGGED
    _FALLBACK_LOGGED = False


def resolve_mads_or_fallback(
    root: Path,
    env: Mapping[str, str] | None = None,
    *,
    handoff_path: Path | None = None,
) -> FilesBackend | "MadsBackend":
    global _FALLBACK_LOGGED
    environ = env if env is not None else os.environ
    if resolve_mads_bin(environ) is None:
        if not _FALLBACK_LOGGED:
            _FALLBACK_LOGGED = True
            _store_append_log(
                root,
                "note",
                "mad",
                {"task": "mads binary not found; falling back to files backend"},
            )
        return FilesBackend(root, handoff_path=handoff_path)
    return MadsBackend(root, env=environ, handoff_path=handoff_path)


class MadsBackend:
    """StateBackend backed by the `mads` CLI store (`mads.contract/1`) with file projections."""

    def __init__(
        self,
        root: Path,
        *,
        env: Mapping[str, str] | None = None,
        handoff_path: Path | None = None,
        today: date | None = None,
        now: datetime | None = None,
    ) -> None:
        self.root = root
        self.env = env
        self.handoff_path = handoff_path
        self.today = today
        self.now = now

    def _call(self, verb: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        retries_left = STORE_BUSY_RETRIES
        while True:
            try:
                return call(verb, payload, cwd=self.root, env=self.env)
            except MadsError as exc:
                if (exc.code == "STORE_BUSY" or exc.retryable) and retries_left > 0:
                    retries_left -= 1
                    time.sleep(random.uniform(0.01, 0.05))
                    continue
                raise

    def append_log(self, kind: str, agent: str, fields: Mapping[str, str]) -> str:
        if kind not in VALID_KINDS:
            raise ValueError(f"unknown log kind: {kind}")
        if agent not in VALID_AGENTS:
            raise ValueError(f"unknown agent: {agent}")

        entry = _store_append_log(self.root, kind, agent, dict(fields), now=self.now)
        self._call(
            "event.append",
            {
                "run_id": MAD_RUN_ID,
                "kind": "mad_log_entry",
                "agent": agent,
                "payload": {"log_kind": kind, "entry": entry},
            },
        )
        return entry

    def write_handoff(
        self,
        agent: str,
        problem: str,
        steps: Sequence[str],
        context_files: Sequence[str] = (),
        verify_cmds: Sequence[str] = (),
    ) -> Path:
        if agent not in VALID_AGENTS:
            raise ValueError(f"unknown agent: {agent}")
        if not problem or not problem.strip():
            raise ValueError("handoff problem cannot be empty")
        clean_steps = [_flatten(s) for s in steps if s and s.strip()]
        if not clean_steps:
            raise ValueError("handoff requires at least one step")

        clean_ctx = [_flatten(c) for c in context_files if c and c.strip()]
        clean_verify = [_flatten(v) for v in verify_cmds if v and v.strip()]

        resp = self._call(
            "write_handoff",
            {
                "from_agent": agent,
                "run_id": MAD_RUN_ID,
                "problem": problem.strip(),
                "steps": clean_steps,
                "context_refs": clean_ctx,
                "verify": clean_verify,
            },
        )
        handoff_id = str(resp["handoff_id"])
        exported = self._call("export", {"format": "md", "key": handoff_id})
        body = str(exported["markdown"])

        target = self.handoff_path if self.handoff_path is not None else (self.root / ".opengsd_handoff.md")
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".opengsd_handoff.", suffix=".tmp")
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(body)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_path, target)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

        self.append_log(
            "handoff",
            agent,
            {
                "task": _flatten(problem),
                "next": "; ".join(clean_steps),
                "file": str(target.relative_to(self.root) if target.is_relative_to(self.root) else target),
            },
        )
        return target

    def fetch_context(self, keywords: Sequence[str], budget_bytes: int) -> str:
        if budget_bytes <= 0:
            return ""
        task_str = " ".join(k.strip() for k in keywords if k and k.strip())
        mads_text = ""
        try:
            bundle = self._call(
                "get_agent_context",
                {
                    "agent": "mad",
                    "run_id": MAD_RUN_ID,
                    "task": task_str,
                    "budget_bytes": budget_bytes,
                },
            )
            mads_text = str(bundle.get("text", ""))
        except MadsError as exc:
            if exc.code != "NOT_FOUND":
                raise
            mads_text = ""

        local_files = FilesBackend(self.root).fetch_context(keywords, budget_bytes)
        if local_files:
            return local_files
        return _clip_utf8_lines(mads_text, budget_bytes)

    def read_telemetry(self) -> dict[str, Any]:
        local = _read_telemetry(self.root)
        if local:
            return local
        try:
            art = self._call("get_artifact", {"kind": "telemetry", "key": TELEMETRY_KEY})
            body = art.get("body")
            return body if isinstance(body, dict) else {}
        except MadsError as exc:
            if exc.code == "NOT_FOUND":
                return {}
            raise

    def write_telemetry(self, data: Mapping[str, Any]) -> Path:
        path = _write_telemetry_atomic(self.root, data)
        self._call(
            "put_artifact",
            {
                "kind": "telemetry",
                "key": TELEMETRY_KEY,
                "body": dict(data),
                "run_id": MAD_RUN_ID,
                "agent": "mad",
            },
        )
        return path
