"""Shared StateBackend contract checks used for both FilesBackend and MadsBackend."""
from pathlib import Path
from typing import Any
import pytest

from mad.backend import StateBackend
from mad.handoff import validate_handoff


def check_append_only_log_growth(backend: StateBackend, root: Path) -> None:
    e1 = backend.append_log("task", "claude", {"task": "first entry"})
    log_path = root / ".global_dev_log.md"
    assert log_path.is_file()
    snap1 = log_path.read_text(encoding="utf-8")
    assert "first entry" in e1
    assert "first entry" in snap1

    e2 = backend.append_log("note", "agy", {"task": "second entry"})
    snap2 = log_path.read_text(encoding="utf-8")
    assert snap2.startswith(snap1)
    assert len(snap2) > len(snap1)
    assert "second entry" in e2
    assert "second entry" in snap2

    with pytest.raises(ValueError):
        backend.append_log("invalid_kind", "claude", {"task": "x"})
    with pytest.raises(ValueError):
        backend.append_log("task", "invalid_agent", {"task": "x"})


def check_handoff_validation_and_write(backend: StateBackend, root: Path) -> None:
    with pytest.raises(ValueError, match="problem"):
        backend.write_handoff("claude", "   ", ["step 1"])

    with pytest.raises(ValueError, match="step"):
        backend.write_handoff("claude", "real problem", [])

    with pytest.raises(ValueError, match="step"):
        backend.write_handoff("claude", "real problem", ["   "])

    out = backend.write_handoff(
        agent="claude",
        problem="MQTT broker drops after 60s",
        steps=["Inspect keepalive", "Run integration suite"],
        context_files=[".active_context/mqtt.md"],
        verify_cmds=["pytest -q"],
    )
    assert out.is_file()
    validated = validate_handoff(out)
    assert "MQTT broker drops after 60s" in validated
    assert "1. Inspect keepalive" in validated
    assert "2. Run integration suite" in validated


def check_context_respects_budget_bytes(backend: StateBackend, root: Path) -> None:
    ctx_dir = root / ".active_context"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    for idx in range(5):
        (ctx_dir / f"topic_{idx}.md").write_text(
            "---\n"
            f"title: Topic {idx} Architecture\n"
            "keywords: [architecture,mqtt,topic]\n"
            "updated: 2026-10-30\n"
            "---\n\n"
            + ("payload line\n" * 20),
            encoding="utf-8",
        )

    for budget in (0, 10, 40, 200, 24000):
        res = backend.fetch_context(["architecture", "mqtt"], budget_bytes=budget)
        assert len(res.encode("utf-8")) <= budget


def check_telemetry_round_trip(backend: StateBackend, root: Path) -> None:
    assert backend.read_telemetry() == {}
    sample = {
        "version": 1,
        "updated": "2026-10-30T20:00:00Z",
        "claude": {
            "window_hours": 5,
            "window_message_budget": 45,
            "handoff_ratio": 0.8,
            "messages_in_window": 12,
            "oldest_in_window": "2026-10-30T16:00:00Z",
        },
        "agy": {
            "max_concurrent": 2,
            "running": 1,
            "last_rate_limit": None,
        },
    }
    path = backend.write_telemetry(sample)
    assert path.is_file()
    loaded = backend.read_telemetry()
    for key in ("version", "updated", "claude", "agy"):
        assert loaded[key] == sample[key]


def check_handoff_take_round_trip(backend: Any, root: Path) -> None:
    backend.write_handoff("claude", "Take test problem", ["Step one"])
    taken = backend.take_handoff("agy")
    assert "Take test problem" in taken
    assert "1. Step one" in taken


def check_slot_claim_and_release(backend: Any, root: Path) -> None:
    lease = backend.claim_slot("agy", max_concurrent=2, ttl_s=60)
    assert lease["slot"] == 1
    assert lease["resource"] == "agy:slot:1"
    assert "claim_id" in lease
    assert "fencing_token" in lease
    rel = backend.release_slot(lease["claim_id"], lease["fencing_token"])
    assert rel == {"released": True}
