"""Selective context retrieval and INDEX.md reindexing for .active_context/."""
import re
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from mad.store import init_store


def _tokenize(text: str) -> set[str]:
    return {tok for tok in re.split(r"\W+", text.lower()) if tok}


def parse_frontmatter(text: str) -> tuple[str, list[str], str]:
    title = ""
    keywords: list[str] = []
    updated = ""
    if not text.startswith("---\n"):
        return title, keywords, updated
    end = text.find("\n---", 4)
    if end == -1:
        return title, keywords, updated
    block = text[4:end]
    for raw_line in block.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        k, v = (part.strip() for part in line.split(":", 1))
        if k == "title":
            title = v
        elif k == "keywords":
            inner = v.strip("[]")
            keywords = [item.strip().lower() for item in inner.split(",") if item.strip()]
        elif k == "updated":
            updated = v
    return title, keywords, updated


def fetch_context(root: Path, query: Sequence[str], budget_bytes: int = 24000) -> list[Path]:
    query_tokens: set[str] = set()
    for arg in query:
        query_tokens.update(_tokenize(arg))
    if not query_tokens:
        return []

    ctx_dir = root / ".active_context"
    if not ctx_dir.is_dir():
        return []

    scored: list[tuple[int, str, Path]] = []
    for path in ctx_dir.glob("*.md"):
        if path.name == "INDEX.md":
            continue
        text = path.read_text(encoding="utf-8")
        title, keywords, _ = parse_frontmatter(text)
        kw_set = {kw.lower() for kw in keywords}
        title_tokens = _tokenize(title)

        score = 2 * len(query_tokens & kw_set) + 1 * len(query_tokens & title_tokens)
        if score > 0:
            scored.append((-score, path.name, path))

    scored.sort(key=lambda item: (item[0], item[1]))

    selected: list[Path] = []
    used_bytes = 0
    for _, _, path in scored:
        size = path.stat().st_size
        if used_bytes + size <= budget_bytes:
            selected.append(path)
            used_bytes += size
    return selected


def reindex_context(root: Path, today: date | None = None) -> Path:
    init_store(root, today=today)
    today_str = (today or datetime.now(UTC).date()).isoformat()
    ctx_dir = root / ".active_context"
    index_path = ctx_dir / "INDEX.md"

    topics = sorted(p for p in ctx_dir.glob("*.md") if p.name != "INDEX.md")
    lines = [
        "---\n",
        "title: Active context index\n",
        "keywords: [index]\n",
        f"updated: {today_str}\n",
        "---\n\n",
        "# Active context\n\n",
        "One topic per file. Regenerate this index with mad fetch --reindex.\n\n",
    ]
    if not topics:
        lines.append("(no topics yet)\n")
    else:
        for p in topics:
            title, keywords, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
            kw_str = ", ".join(keywords)
            rel = p.relative_to(root)
            lines.append(f"- {rel} — {title} [{kw_str}]\n")

    index_path.write_text("".join(lines), encoding="utf-8")
    return index_path
