from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from mad.store import append_log, find_root, init_store


def test_init_creates_then_is_idempotent(tmp_path):
    created = init_store(tmp_path, today=date(2026, 10, 23))
    assert sorted(p.name for p in created) == [".active_context", ".global_dev_log.md", "INDEX.md"]
    assert "updated: 2026-10-23" in (tmp_path / ".global_dev_log.md").read_text()
    assert init_store(tmp_path) == []


def test_init_never_overwrites(tmp_path):
    (tmp_path / ".global_dev_log.md").write_bytes(b"mine\n")
    init_store(tmp_path)
    assert (tmp_path / ".global_dev_log.md").read_bytes() == b"mine\n"


def test_append_preserves_prior_bytes(tmp_path):
    t = datetime(2026, 10, 23, 14, 2, 11, tzinfo=UTC)
    append_log(tmp_path, "task", "claude", {"task": "one"}, now=t)
    before = (tmp_path / ".global_dev_log.md").read_bytes()
    entry = append_log(tmp_path, "decision", "human", {"task": "two"}, now=t)
    after = (tmp_path / ".global_dev_log.md").read_bytes()
    assert after.startswith(before) and after[len(before):].decode() == entry
    assert entry == "\n## 2026-10-23T14:02:11Z · decision · human\n- task: two\n"


def test_append_creates_log_with_header_first(tmp_path):
    append_log(tmp_path, "note", "mad", {"task": "x"})
    assert (tmp_path / ".global_dev_log.md").read_text().startswith("---\ntitle: Global dev log\n")


def test_multiline_values_flattened(tmp_path):
    e = append_log(tmp_path, "task", "agy", {"task": "a\nb\r\n\nc"})
    assert "- task: a b c\n" in e and e.count("\n") == 3


def test_unknown_kind_or_agent_rejected(tmp_path):
    with pytest.raises(ValueError):
        append_log(tmp_path, "oops", "claude", {})
    with pytest.raises(ValueError):
        append_log(tmp_path, "task", "gpt", {})


def test_find_root(tmp_path):
    (tmp_path / ".git").mkdir()
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert find_root(sub) == tmp_path
