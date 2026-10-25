"""Unit tests for mad.telemetry (TEL-01, TEL-02, TEL-03)."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from mad.telemetry import (
    check_limits,
    count_claude_messages,
    read_telemetry,
    write_telemetry_atomic,
)


def _write_transcript(path: Path, lines: list[str | dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = []
    for item in lines:
        raw.append(item if isinstance(item, str) else json.dumps(item))
    path.write_text("\n".join(raw) + "\n", encoding="utf-8")


def test_count_claude_messages_filters_window_meta_and_tool_results(tmp_path: Path) -> None:
    now = datetime(2026, 10, 23, 15, 0, 0, tzinfo=timezone.utc)
    proj_a = tmp_path / "proj-a" / "session1.jsonl"
    proj_b = tmp_path / "proj-b" / "session2.jsonl"

    _write_transcript(
        proj_a,
        [
            # Valid user prompt inside window (4h ago)
            {"type": "user", "timestamp": "2026-10-23T11:00:00.123Z", "message": {"role": "user", "content": "hi"}},
            # Outside window (6h ago) -> ignored
            {"type": "user", "timestamp": "2026-10-23T08:59:59Z", "message": {"role": "user", "content": "old"}},
            # isMeta: true -> ignored
            {"type": "user", "timestamp": "2026-10-23T12:00:00Z", "isMeta": True, "message": {"role": "user", "content": "meta"}},
            # Tool result only -> ignored
            {
                "type": "user",
                "timestamp": "2026-10-23T12:30:00Z",
                "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
            },
            # Assistant turn -> ignored
            {"type": "assistant", "timestamp": "2026-10-23T13:00:00Z"},
            # Malformed JSON line -> skipped without crashing
            "{not valid json",
        ],
    )
    _write_transcript(
        proj_b,
        [
            # Simple fixture user prompt inside window (1h ago)
            {"type": "user", "timestamp": "2026-10-23T14:00:00Z"},
            # Multi-block user message with text + tool_result -> counted
            {
                "type": "user",
                "timestamp": "2026-10-23T14:30:00Z",
                "message": {"role": "user", "content": [{"type": "tool_result"}, {"type": "text", "text": "follow up"}]},
            },
        ],
    )

    count, oldest = count_claude_messages(tmp_path, window_hours=5, now=now)
    assert count == 3
    assert oldest == "2026-10-23T11:00:00Z"


def test_threshold_35_is_ok_and_36_triggers_handoff(tmp_path: Path) -> None:
    now = datetime(2026, 10, 23, 15, 0, 0, tzinfo=timezone.utc)
    transcripts = tmp_path / "projects"
    session = transcripts / "proj" / "s.jsonl"

    # 35 prompts within the last 5h + 2 prompts older than 5h (7h ago)
    entries: list[dict] = [
        {"type": "user", "timestamp": (now - timedelta(hours=7, minutes=i)).isoformat().replace("+00:00", "Z")}
        for i in range(2)
    ]
    for i in range(35):
        ts = (now - timedelta(hours=4) + timedelta(minutes=i)).isoformat().replace("+00:00", "Z")
        entries.append({"type": "user", "timestamp": ts})

    _write_transcript(session, entries)

    should_handoff, data = check_limits(tmp_path, transcripts_dir=transcripts, env={}, now=now)
    assert should_handoff is False
    assert data["version"] == 1
    assert data["updated"] == "2026-10-23T15:00:00Z"
    assert data["claude"]["messages_in_window"] == 35
    assert data["claude"]["oldest_in_window"] == "2026-10-23T11:00:00Z"

    # Add 36th prompt inside window -> ceil(45 * 0.8) == 36 -> handoff!
    entries.append({"type": "user", "timestamp": "2026-10-23T14:55:00Z"})
    _write_transcript(session, entries)

    should_handoff_36, data_36 = check_limits(tmp_path, transcripts_dir=transcripts, env={}, now=now)
    assert should_handoff_36 is True
    assert data_36["claude"]["messages_in_window"] == 36


def test_agy_concurrency_and_rate_limit_cooldown(tmp_path: Path) -> None:
    now = datetime(2026, 10, 23, 15, 0, 0, tzinfo=timezone.utc)
    transcripts = tmp_path / "empty_projects"

    # 1. agy.running == 2 (max_concurrent) via env override -> handoff
    handoff_conc, data_conc = check_limits(
        tmp_path, transcripts_dir=transcripts, env={"MAD_AGY_RUNNING": "2"}, now=now
    )
    assert handoff_conc is True
    assert data_conc["agy"]["running"] == 2

    # Reset running to 0, record a rate limit at `now` -> handoff
    handoff_rl, data_rl = check_limits(
        tmp_path,
        transcripts_dir=transcripts,
        record_rate_limit=True,
        env={"MAD_AGY_RUNNING": "0"},
        now=now,
    )
    assert handoff_rl is True
    assert data_rl["agy"]["last_rate_limit"] == "2026-10-23T15:00:00Z"

    # 10 minutes later (within 15m cooldown) -> still handoff, preserves last_rate_limit
    handoff_10m, _ = check_limits(
        tmp_path,
        transcripts_dir=transcripts,
        env={},
        now=now + timedelta(minutes=10),
    )
    assert handoff_10m is True

    # 16 minutes later (past 15m cooldown) -> ok
    handoff_16m, _ = check_limits(
        tmp_path,
        transcripts_dir=transcripts,
        env={},
        now=now + timedelta(minutes=16),
    )
    assert handoff_16m is False


def test_atomic_write_preserves_valid_json_on_interrupted_replace(tmp_path: Path) -> None:
    initial = {"version": 1, "updated": "2026-10-23T10:00:00Z", "claude": {}, "agy": {}}
    target = write_telemetry_atomic(tmp_path, initial)
    assert target == tmp_path / ".agent_telemetry.json"
    assert read_telemetry(tmp_path) == initial

    # Simulate an interrupted write where os.replace raises OSError
    updated = {"version": 1, "updated": "2026-10-23T15:00:00Z", "claude": {"messages_in_window": 99}, "agy": {}}
    with patch("mad.telemetry.os.replace", side_effect=OSError("simulated crash")):
        with pytest.raises(OSError, match="simulated crash"):
            write_telemetry_atomic(tmp_path, updated)

    # The telemetry file must still be valid JSON equal to initial, with no leftover temp file
    assert json.loads(target.read_text(encoding="utf-8")) == initial
    leftover_tmps = [p for p in tmp_path.iterdir() if p != target]
    assert leftover_tmps == []


def test_check_limits_handles_empty_or_invalid_agy_running(tmp_path: Path) -> None:
    now = datetime(2026, 10, 23, 15, 0, 0, tzinfo=timezone.utc)
    transcripts = tmp_path / "empty_projects"

    # Corrupt/null running in existing telemetry file + empty MAD_AGY_RUNNING="" -> defaults to 0
    write_telemetry_atomic(tmp_path, {"version": 1, "agy": {"running": None}})
    should_handoff, data = check_limits(
        tmp_path, transcripts_dir=transcripts, env={"MAD_AGY_RUNNING": "  "}, now=now
    )
    assert should_handoff is False
    assert data["agy"]["running"] == 0

    # Non-integer MAD_AGY_RUNNING raises clear ValueError
    with pytest.raises(ValueError, match="invalid MAD_AGY_RUNNING"):
        check_limits(tmp_path, transcripts_dir=transcripts, env={"MAD_AGY_RUNNING": "abc"}, now=now)
