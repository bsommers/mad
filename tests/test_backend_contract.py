"""Parametrized contract test suite over StateBackend implementations + MadsBackend behavior."""
from pathlib import Path
import pytest

from mad.backend import StateBackend, get_backend
from mad.files_backend import FilesBackend
from mad.mads_backend import MadsBackend, reset_fallback_notice_for_testing
from tests import backend_contract

STUB_PATH = str(Path(__file__).resolve().parent / "stubs" / "mads_stub.py")


@pytest.fixture(params=["files", "mads"])
def backend_and_root(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[StateBackend, Path]:
    kind = request.param
    if kind == "files":
        return FilesBackend(tmp_path), tmp_path
    if kind == "mads":
        monkeypatch.setenv("MADS_BIN", STUB_PATH)
        monkeypatch.setenv("MADS_STUB_STATE", str(tmp_path / ".mads" / "stub_state.json"))
        return MadsBackend(tmp_path), tmp_path
    raise ValueError(f"unknown backend fixture: {kind}")


def test_contract_append_only_log_growth(backend_and_root: tuple[StateBackend, Path]) -> None:
    backend, root = backend_and_root
    backend_contract.check_append_only_log_growth(backend, root)


def test_contract_handoff_validation_and_write(backend_and_root: tuple[StateBackend, Path]) -> None:
    backend, root = backend_and_root
    backend_contract.check_handoff_validation_and_write(backend, root)


def test_contract_context_respects_budget_bytes(backend_and_root: tuple[StateBackend, Path]) -> None:
    backend, root = backend_and_root
    backend_contract.check_context_respects_budget_bytes(backend, root)


def test_contract_telemetry_round_trip(backend_and_root: tuple[StateBackend, Path]) -> None:
    backend, root = backend_and_root
    backend_contract.check_telemetry_round_trip(backend, root)


def test_contract_handoff_take_round_trip(backend_and_root: tuple[StateBackend, Path]) -> None:
    backend, root = backend_and_root
    backend_contract.check_handoff_take_round_trip(backend, root)


def test_contract_slot_claim_and_release(backend_and_root: tuple[StateBackend, Path]) -> None:
    backend, root = backend_and_root
    backend_contract.check_slot_claim_and_release(backend, root)


def test_mads_backend_take_handoff_single_consumption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MADS_BIN", STUB_PATH)
    monkeypatch.setenv("MADS_STUB_STATE", str(tmp_path / ".mads" / "stub_state.json"))

    backend = MadsBackend(tmp_path)
    backend.write_handoff("claude", "Single consumption problem", ["First step"])

    taken = backend.take_handoff("agy")
    assert "Single consumption problem" in taken

    with pytest.raises(ValueError, match="no open handoff"):
        backend.take_handoff("agy")


def test_mads_backend_slot_claims_respect_max_concurrent_and_fencing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MADS_BIN", STUB_PATH)
    monkeypatch.setenv("MADS_STUB_STATE", str(tmp_path / ".mads" / "stub_state.json"))

    backend = MadsBackend(tmp_path)
    lease1 = backend.claim_slot("agy", max_concurrent=2, ttl_s=60)
    assert lease1["slot"] == 1
    assert lease1["resource"] == "agy:slot:1"
    assert lease1["fencing_token"] == 1

    lease2 = backend.claim_slot("agy", max_concurrent=2, ttl_s=60)
    assert lease2["slot"] == 2
    assert lease2["resource"] == "agy:slot:2"
    assert lease2["fencing_token"] == 1

    with pytest.raises(ValueError, match="all agy slots busy"):
        backend.claim_slot("agy", max_concurrent=2, ttl_s=60)

    rel1 = backend.release_slot(lease1["claim_id"], lease1["fencing_token"])
    assert rel1 == {"released": True}

    lease3 = backend.claim_slot("agy", max_concurrent=2, ttl_s=60)
    assert lease3["slot"] == 1
    assert lease3["resource"] == "agy:slot:1"
    assert lease3["fencing_token"] == 2

    with pytest.raises(ValueError, match="lease lost"):
        backend.release_slot(lease3["claim_id"], 1)


def test_mads_absent_falls_back_to_files_and_logs_one_note_per_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reset_fallback_notice_for_testing()
    env = {"MAD_STATE_BACKEND": "mads", "MADS_BIN": "/nonexistent/mads_binary", "PATH": ""}

    b1 = get_backend(tmp_path, env)
    b2 = get_backend(tmp_path, env)
    assert isinstance(b1, FilesBackend)
    assert isinstance(b2, FilesBackend)

    log_text = (tmp_path / ".global_dev_log.md").read_text(encoding="utf-8")
    assert log_text.count("· note · mad") == 1
    assert "falling back to files backend" in log_text.lower()


def test_mads_backend_retries_store_busy_twice_then_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    busy_file = tmp_path / "busy_count.txt"
    busy_file.write_text("2", encoding="utf-8")
    monkeypatch.setenv("MADS_BIN", STUB_PATH)
    monkeypatch.setenv("MADS_STUB_STATE", str(tmp_path / ".mads" / "stub_state.json"))
    monkeypatch.setenv("MADS_STUB_BUSY_COUNT_FILE", str(busy_file))

    backend = MadsBackend(tmp_path)
    entry = backend.append_log("task", "claude", {"task": "survived busy"})
    assert "survived busy" in entry
    assert busy_file.read_text(encoding="utf-8").strip() == "0"


def test_mads_backend_context_not_found_returns_empty_not_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MADS_BIN", STUB_PATH)
    monkeypatch.setenv("MADS_STUB_STATE", str(tmp_path / ".mads" / "stub_state.json"))
    monkeypatch.setenv("MADS_STUB_CONTEXT_NOT_FOUND", "1")

    backend = MadsBackend(tmp_path)
    out = backend.fetch_context(["docker"], budget_bytes=24000)
    assert out == ""


def test_route_output_identical_in_both_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from mad import cli

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    monkeypatch.setenv("MADS_BIN", STUB_PATH)

    prompts = [
        ["route", "debug the mqtt reconnect", "src/a.py"],
        ["route", "design the UNS tree", "a.py", "b.py", "c.py", "d.py", "e.py", "f.py"],
        ["route", "fix typo in readme"],
    ]
    for argv in prompts:
        monkeypatch.setenv("MAD_STATE_BACKEND", "files")
        assert cli.main(argv) == 0
        out_files = capsys.readouterr().out

        monkeypatch.setenv("MAD_STATE_BACKEND", "mads")
        assert cli.main(argv) == 0
        out_mads = capsys.readouterr().out

        assert out_mads == out_files
