"""OKF Markdown state store: .global_dev_log.md and .active_context/."""
import re
from datetime import UTC, date, datetime
from pathlib import Path

VALID_KINDS = frozenset({"task", "transition", "decision", "handoff", "note"})
VALID_AGENTS = frozenset({"claude", "agy", "human", "mad"})


def find_root(start: Path) -> Path:
    cur = start.resolve()
    for p in (cur, *cur.parents):
        if (p / ".global_dev_log.md").exists() or (p / ".git").exists():
            return p
    return cur


def _log_header(today_str: str) -> str:
    return (
        "---\n"
        "title: Global dev log\n"
        "keywords: [log, history, decisions, handoffs]\n"
        f"updated: {today_str}\n"
        "---\n\n"
        "# Global dev log\n\n"
        "Append-only. Newest entries at the bottom.\n"
    )


def _index_header(today_str: str) -> str:
    return (
        "---\n"
        "title: Active context index\n"
        "keywords: [index]\n"
        f"updated: {today_str}\n"
        "---\n\n"
        "# Active context\n\n"
        "One topic per file. Regenerate this index with mad fetch --reindex.\n"
    )


def init_store(root: Path, today: date | None = None) -> list[Path]:
    today_str = (today or datetime.now(UTC).date()).isoformat()
    created: list[Path] = []

    ctx_dir = root / ".active_context"
    if not ctx_dir.exists():
        ctx_dir.mkdir(parents=True)
        created.append(ctx_dir)

    index_file = ctx_dir / "INDEX.md"
    if not index_file.exists():
        index_file.write_text(_index_header(today_str), encoding="utf-8")
        created.append(index_file)

    log_file = root / ".global_dev_log.md"
    if not log_file.exists():
        log_file.write_text(_log_header(today_str), encoding="utf-8")
        created.append(log_file)

    return created


def append_log(root: Path, kind: str, agent: str, fields: dict[str, str],
               now: datetime | None = None) -> str:
    if kind not in VALID_KINDS:
        raise ValueError(f"unknown log kind: {kind}")
    if agent not in VALID_AGENTS:
        raise ValueError(f"unknown agent: {agent}")

    init_store(root)
    ts = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [f"\n## {ts} · {kind} · {agent}\n"]
    for k, v in fields.items():
        flat_v = re.sub(r"[\r\n]+", " ", str(v))
        lines.append(f"- {k}: {flat_v}\n")
    entry = "".join(lines)

    log_file = root / ".global_dev_log.md"
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(entry)
    return entry
