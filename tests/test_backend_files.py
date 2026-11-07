"""Task 1 tests: StateBackend protocol, FilesBackend parity, and unknown MAD_STATE_BACKEND exit code."""
from datetime import UTC, date, datetime
from pathlib import Path
import pytest

from mad import cli, handoff, store
from mad.backend import CoordinationBackend, StateBackend, get_backend
from mad.files_backend import FilesBackend
from tests import backend_contract


def test_files_backend_satisfies_protocol(tmp_path: Path) -> None:
    backend: StateBackend = FilesBackend(tmp_path)
    assert isinstance(backend, FilesBackend)


def test_files_backend_append_log_equals_store_append_log(tmp_path: Path) -> None:
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()

    fixed_now = datetime(2026, 10, 30, 12, 0, 0, tzinfo=UTC)
    fixed_today = date(2026, 10, 30)
    store.init_store(root_a, today=fixed_today)
    store.init_store(root_b, today=fixed_today)

    fields = {"task": "verify parity", "step": "1"}
    out_store = store.append_log(root_a, "task", "claude", fields, now=fixed_now)
    fb = FilesBackend(root_b, now=fixed_now, today=fixed_today)
    out_backend = fb.append_log("task", "claude", fields)

    assert out_backend == out_store
    assert (root_b / ".global_dev_log.md").read_text(encoding="utf-8") == (
        root_a / ".global_dev_log.md"
    ).read_text(encoding="utf-8")


def test_files_backend_write_handoff_equals_handoff_write_handoff(tmp_path: Path) -> None:
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()

    fixed_now = datetime(2026, 10, 30, 12, 0, 0, tzinfo=UTC)
    fixed_today = date(2026, 10, 30)
    store.init_store(root_a, today=fixed_today)
    store.init_store(root_b, today=fixed_today)

    path_a = handoff.write_handoff(
        root_a,
        agent="claude",
        problem="Broker reconnect drops",
        steps=["Inspect backoff", "Add test"],
        context_files=[".active_context/mqtt.md"],
        verify_cmds=["pytest -q"],
        today=fixed_today,
        now=fixed_now,
    )
    fb = FilesBackend(root_b, now=fixed_now, today=fixed_today)
    path_b = fb.write_handoff(
        agent="claude",
        problem="Broker reconnect drops",
        steps=["Inspect backoff", "Add test"],
        context_files=[".active_context/mqtt.md"],
        verify_cmds=["pytest -q"],
    )

    assert path_b.read_text(encoding="utf-8") == path_a.read_text(encoding="utf-8")
    assert (root_b / ".global_dev_log.md").read_text(encoding="utf-8") == (
        root_a / ".global_dev_log.md"
    ).read_text(encoding="utf-8")


def test_unknown_mad_state_backend_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    monkeypatch.setenv("MAD_STATE_BACKEND", "redis")

    code = cli.main(["log", "--kind", "note", "--agent", "human", "hello"])
    assert code == 2


def test_files_backend_satisfies_coordination_protocol(tmp_path: Path) -> None:
    backend: CoordinationBackend = FilesBackend(tmp_path)
    assert isinstance(backend, FilesBackend)


def test_files_backend_take_handoff(tmp_path: Path) -> None:
    fb = FilesBackend(tmp_path)
    with pytest.raises(ValueError, match="unknown agent"):
        fb.take_handoff("invalid_agent")

    with pytest.raises(ValueError, match="handoff file not found"):
        fb.take_handoff("agy")

    backend_contract.check_handoff_take_round_trip(fb, tmp_path)


def test_files_backend_claim_and_release_slot(tmp_path: Path) -> None:
    fb = FilesBackend(tmp_path)
    with pytest.raises(ValueError, match="unknown agent"):
        fb.claim_slot("invalid_agent")

    with pytest.raises(ValueError, match="max_concurrent"):
        fb.claim_slot("agy", max_concurrent=0)

    with pytest.raises(ValueError, match="ttl_s"):
        fb.claim_slot("agy", ttl_s=0)

    with pytest.raises(ValueError, match="claim_id"):
        fb.release_slot("", 0)

    with pytest.raises(ValueError, match="claim_id"):
        fb.release_slot("   ", 0)

    backend_contract.check_slot_claim_and_release(fb, tmp_path)

    lease = fb.claim_slot("agy", max_concurrent=5, ttl_s=120)
    assert lease == {
        "slot": 1,
        "resource": "agy:slot:1",
        "claim_id": "files-noop",
        "fencing_token": 0,
        "expires_at": None,
    }
    rel = fb.release_slot("files-noop", 0, outcome="success")
    assert rel == {"released": True}
