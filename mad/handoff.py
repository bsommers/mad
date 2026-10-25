"""State handoff artifact (.opengsd_handoff.md) writer, validator, and launcher."""
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
import os
from pathlib import Path
import re
import tempfile

from mad.store import VALID_AGENTS, append_log

REQUIRED_SECTIONS = (
    "## Unresolved problem",
    "## Next exact steps",
    "## Context files to load",
    "## Verify with",
)


def _flatten(text: str) -> str:
    return re.sub(r"[\r\n]+", " ", text.strip())


def write_handoff(
    root: Path,
    agent: str,
    problem: str,
    steps: Sequence[str],
    context_files: Sequence[str] = (),
    verify_cmds: Sequence[str] = (),
    handoff_path: Path | None = None,
    today: date | None = None,
    now: datetime | None = None,
) -> Path:
    if agent not in VALID_AGENTS:
        raise ValueError(f"unknown agent: {agent}")
    if not problem or not problem.strip():
        raise ValueError("handoff problem cannot be empty")
    clean_steps = [_flatten(s) for s in steps if s and s.strip()]
    if not clean_steps:
        raise ValueError("handoff requires at least one step")

    today_str = (today or datetime.now(UTC).date()).isoformat()
    target = handoff_path if handoff_path is not None else (root / ".opengsd_handoff.md")

    steps_block = "".join(f"{idx}. {step}\n" for idx, step in enumerate(clean_steps, start=1))
    clean_ctx = [_flatten(c) for c in context_files if c and c.strip()]
    ctx_block = "".join(f"- {c}\n" for c in clean_ctx) if clean_ctx else "- (none)\n"
    clean_verify = [_flatten(v) for v in verify_cmds if v and v.strip()]
    verify_block = "".join(f"- {v}\n" for v in clean_verify) if clean_verify else "- pytest -q\n"

    body = (
        "---\n"
        "title: Session handoff\n"
        "keywords: [handoff, state]\n"
        f"updated: {today_str}\n"
        "---\n\n"
        "# Session handoff\n\n"
        "## Unresolved problem\n\n"
        f"{problem.strip()}\n\n"
        "## Next exact steps\n\n"
        f"{steps_block}\n"
        "## Context files to load\n\n"
        f"{ctx_block}\n"
        "## Verify with\n\n"
        f"{verify_block}"
    )

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

    append_log(
        root,
        "handoff",
        agent,
        {
            "task": _flatten(problem),
            "next": "; ".join(clean_steps),
            "file": str(target.relative_to(root) if target.is_relative_to(root) else target),
        },
        now=now,
    )
    return target


def validate_handoff(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"handoff file not found: {path}")
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"handoff file not found: {path}")
    if not content.startswith("---\n"):
        raise ValueError(f"malformed handoff file (missing OKF frontmatter): {path}")
    fm_end = content.find("\n---", 4)
    if fm_end == -1:
        raise ValueError(f"malformed handoff file (missing OKF frontmatter): {path}")

    body = content[fm_end + 4 :]
    pos = 0
    for sec in REQUIRED_SECTIONS:
        match = re.search(rf"(?m)^{re.escape(sec)}\s*$", body[pos:])
        if match is None:
            raise ValueError(f"malformed handoff file (missing section '{sec}'): {path}")
        pos += match.end()
    return content


def build_handoff_command(content: str, model: str, env: Mapping[str, str]) -> list[str]:
    binary = env.get("MAD_AGY_BIN", "agy")
    return [binary, "--model", model, "-i", content]
