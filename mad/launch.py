"""Command builder and exec helper for claude and agy CLIs."""
import os
from collections.abc import Mapping, Sequence
from typing import NoReturn

from mad.route import Decision


def build_command(decision: Decision, prompt: str, files: Sequence[str],
                  env: Mapping[str, str]) -> list[str]:
    full_prompt = prompt if not files else f"{prompt}\n\nFiles: {' '.join(files)}"
    if decision.agent == "claude":
        binary = env.get("MAD_CLAUDE_BIN", "claude")
        return [binary, "--model", decision.model, full_prompt]
    binary = env.get("MAD_AGY_BIN", "agy")
    return [binary, "--model", decision.model, "-i", full_prompt]


def exec_command(argv: list[str]) -> NoReturn:
    os.execvp(argv[0], argv)
