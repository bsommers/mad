"""State handoff artifact (.opengsd_handoff.md) writer, validator, and launcher."""
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from mad.store import append_log

REQUIRED_SECTIONS = (
    "## Unresolved problem",
    "## Next exact steps",
    "## Context files to load",
    "## Verify with",
)


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
    if not problem or not problem.strip():
        raise ValueError("handoff problem cannot be empty")
    clean_steps = [s.strip() for s in steps if s and s.strip()]
    if not clean_steps:
        raise ValueError("handoff requires at least one step")

    today_str = (today or datetime.now(UTC).date()).isoformat()
    target = handoff_path if handoff_path is not None else (root / ".opengsd_handoff.md")

    steps_block = "".join(f"{idx}. {step}\n" for idx, step in enumerate(clean_steps, start=1))
    ctx_block = (
        "".join(f"- {c.strip()}\n" for c in context_files if c.strip())
        if context_files
        else "- (none)\n"
    )
    verify_block = (
        "".join(f"- {v.strip()}\n" for v in verify_cmds if v.strip())
        if verify_cmds
        else "- pytest -q\n"
    )

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

    append_log(
        root,
        "handoff",
        agent,
        {
            "task": problem.strip(),
            "next": "; ".join(clean_steps),
            "file": str(target.relative_to(root) if target.is_relative_to(root) else target),
        },
        now=now,
    )
    target.write_text(body, encoding="utf-8")
    return target


def validate_handoff(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"handoff file not found: {path}")
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"handoff file not found: {path}")
    if not content.startswith("---\n") or "\n---" not in content[4:]:
        raise ValueError(f"malformed handoff file (missing OKF frontmatter): {path}")

    pos = 0
    for sec in REQUIRED_SECTIONS:
        idx = content.find(sec, pos)
        if idx == -1:
            raise ValueError(f"malformed handoff file (missing section '{sec}'): {path}")
        pos = idx + len(sec)
    return content


def build_handoff_command(content: str, model: str, env: Mapping[str, str]) -> list[str]:
    binary = env.get("MAD_AGY_BIN", "agy")
    return [binary, "--model", model, "-i", content]
