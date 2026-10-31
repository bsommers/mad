"""File-backed state backend wrapping store.py, handoff.py, context.py, and telemetry.py."""
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

from mad.context import fetch_context as _fetch_context
from mad.handoff import write_handoff as _write_handoff
from mad.store import append_log as _append_log
from mad.telemetry import read_telemetry as _read_telemetry, write_telemetry_atomic as _write_telemetry_atomic


def _clip_utf8_lines(text: str, budget_bytes: int) -> str:
    if budget_bytes <= 0:
        return ""
    raw = text.encode("utf-8")
    if len(raw) <= budget_bytes:
        return text
    lines: list[str] = []
    used = 0
    for line in text.splitlines():
        candidate = line if not lines else f"\n{line}"
        clen = len(candidate.encode("utf-8"))
        if used + clen <= budget_bytes:
            lines.append(line)
            used += clen
        else:
            break
    if lines:
        return "\n".join(lines)
    return raw[:budget_bytes].decode("utf-8", errors="ignore")


class FilesBackend:
    """Default state backend storing OKF Markdown and JSON files directly on disk."""

    def __init__(
        self,
        root: Path,
        *,
        handoff_path: Path | None = None,
        today: date | None = None,
        now: datetime | None = None,
    ) -> None:
        self.root = root
        self.handoff_path = handoff_path
        self.today = today
        self.now = now

    def append_log(self, kind: str, agent: str, fields: Mapping[str, str]) -> str:
        return _append_log(self.root, kind, agent, dict(fields), now=self.now)

    def write_handoff(
        self,
        agent: str,
        problem: str,
        steps: Sequence[str],
        context_files: Sequence[str] = (),
        verify_cmds: Sequence[str] = (),
    ) -> Path:
        return _write_handoff(
            self.root,
            agent=agent,
            problem=problem,
            steps=steps,
            context_files=context_files,
            verify_cmds=verify_cmds,
            handoff_path=self.handoff_path,
            today=self.today,
            now=self.now,
        )

    def fetch_context(self, keywords: Sequence[str], budget_bytes: int) -> str:
        if budget_bytes <= 0:
            return ""
        paths = _fetch_context(self.root, keywords, budget_bytes=budget_bytes)
        joined = "\n".join(str(p.relative_to(self.root)) for p in paths)
        return _clip_utf8_lines(joined, budget_bytes)

    def read_telemetry(self) -> dict[str, Any]:
        return _read_telemetry(self.root)

    def write_telemetry(self, data: Mapping[str, Any]) -> Path:
        return _write_telemetry_atomic(self.root, data)
