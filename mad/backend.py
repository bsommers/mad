"""Pluggable state backend protocol and selector."""
from collections.abc import Mapping, Sequence
import os
from pathlib import Path
from typing import Any, Protocol

from mad.files_backend import FilesBackend
from mad.route import load_config

VALID_BACKENDS = frozenset({"files", "mads"})


class BackendUsageError(Exception):
    """Raised when an invalid state backend name is configured."""


class StateBackend(Protocol):
    """5-method state backend protocol."""

    def append_log(self, kind: str, agent: str, fields: Mapping[str, str]) -> str: ...
    def write_handoff(
        self,
        agent: str,
        problem: str,
        steps: Sequence[str],
        context_files: Sequence[str] = (),
        verify_cmds: Sequence[str] = (),
    ) -> Path: ...
    def fetch_context(self, keywords: Sequence[str], budget_bytes: int) -> str: ...
    def read_telemetry(self) -> dict[str, Any]: ...
    def write_telemetry(self, data: Mapping[str, Any]) -> Path: ...


def get_backend(
    root: Path,
    env: Mapping[str, str] | None = None,
    *,
    handoff_path: Path | None = None,
) -> StateBackend:
    environ = env if env is not None else os.environ
    choice = environ.get("MAD_STATE_BACKEND", "").strip()
    if not choice:
        cfg = load_config()
        choice = str(cfg.get("state_backend", "files")).strip() or "files"

    if choice not in VALID_BACKENDS:
        raise BackendUsageError(f"unknown state backend: {choice} (expected files or mads)")

    if choice == "mads":
        from mad.mads_backend import resolve_mads_or_fallback

        return resolve_mads_or_fallback(root, environ, handoff_path=handoff_path)

    return FilesBackend(root, handoff_path=handoff_path)
