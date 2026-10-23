from datetime import date
from pathlib import Path

from mad.context import fetch_context, parse_frontmatter, reindex_context
from mad.store import init_store


def _write_topic(root: Path, name: str, title: str, keywords: list[str], body: str = "Body.\n") -> Path:
    init_store(root)
    kw_str = ", ".join(keywords)
    content = (
        f"---\n"
        f"title: {title}\n"
        f"keywords: [{kw_str}]\n"
        f"updated: 2026-10-23\n"
        f"---\n\n"
        f"{body}"
    )
    path = root / ".active_context" / name
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_frontmatter():
    text = "---\ntitle: Docker Guidelines\nkeywords: [docker, container, compose]\nupdated: 2026-10-23\n---\n\n# Body\n"
    title, keywords, updated = parse_frontmatter(text)
    assert title == "Docker Guidelines"
    assert keywords == ["docker", "container", "compose"]
    assert updated == "2026-10-23"


def test_fetch_matches_only_docker_fixture(tmp_path):
    p_docker = _write_topic(tmp_path, "docker_guidelines.md", "Docker Guidelines", ["docker", "containers"])
    _write_topic(tmp_path, "ui_components.md", "UI Components", ["react", "css"])
    matched = fetch_context(tmp_path, ["docker"])
    assert matched == [p_docker]


def test_fetch_weights_and_tie_break(tmp_path):
    # b_topic has keyword hit (2 pts), a_topic has title hit (1 pt) -> b_topic first
    p_a = _write_topic(tmp_path, "a_topic.md", "MQTT notes", ["broker"])
    p_b = _write_topic(tmp_path, "b_topic.md", "Broker setup", ["mqtt"])
    assert fetch_context(tmp_path, ["mqtt"]) == [p_b, p_a]

    # Equal score (both have keyword "broker" = 2 pts) -> alphabetical by filename
    assert fetch_context(tmp_path, ["broker"]) == [p_a, p_b]


def test_fetch_budget_skips_oversized_and_continues(tmp_path):
    # High score (keyword + title = 3 pts), but 500 bytes
    _write_topic(tmp_path, "big.md", "MQTT architecture", ["mqtt"], body="x" * 500)
    # Lower score (keyword = 2 pts), ~100 bytes
    p_small = _write_topic(tmp_path, "small.md", "Other topic", ["mqtt"], body="y" * 10)

    assert fetch_context(tmp_path, ["mqtt"], budget_bytes=300) == [p_small]
    assert fetch_context(tmp_path, ["mqtt"], budget_bytes=10) == []


def test_fetch_ignores_index_md(tmp_path):
    init_store(tmp_path)
    # INDEX.md has keyword "index" and title "Active context index"
    assert fetch_context(tmp_path, ["index", "active", "context"]) == []


def test_reindex_empty_and_populated(tmp_path):
    idx = reindex_context(tmp_path, today=date(2026, 10, 23))
    text_empty = idx.read_text(encoding="utf-8")
    assert "updated: 2026-10-23" in text_empty
    assert "(no topics yet)" in text_empty

    _write_topic(tmp_path, "z_ui.md", "UI Components", ["react", "ui"])
    _write_topic(tmp_path, "a_docker.md", "Docker Guidelines", ["docker", "compose"])
    reindex_context(tmp_path, today=date(2026, 10, 23))
    text_pop = idx.read_text(encoding="utf-8")
    expected_lines = (
        "- .active_context/a_docker.md — Docker Guidelines [docker, compose]\n"
        "- .active_context/z_ui.md — UI Components [react, ui]\n"
    )
    assert expected_lines in text_pop
