"""Task 3 tests: mads_client subprocess wire protocol and error mapping."""
from pathlib import Path
import pytest

from mad.mads_client import CLOSED_ERROR_CODES, MadsError, call

STUB_PATH = str(Path(__file__).resolve().parent / "stubs" / "mads_stub.py")


def test_call_success_envelope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MADS_BIN", STUB_PATH)
    monkeypatch.setenv("MADS_STUB_STATE", str(tmp_path / "state.json"))

    data = call(
        "event.append",
        {
            "run_id": "mad_legacy",
            "kind": "mad_log_entry",
            "agent": "claude",
            "payload": {"log_kind": "task", "entry": "## 2026-10-30T00:00:00Z · task · claude\n- task: hi\n"},
        },
        cwd=tmp_path,
    )
    assert data == {"seq": 1}


@pytest.mark.parametrize(
    ("code", "expected_retryable"),
    [
        ("USAGE", False),
        ("CONFLICT", False),
        ("NOT_FOUND", False),
        ("VALIDATION", False),
        ("STORE_BUSY", True),
        ("LEASE_LOST", False),
        ("FORBIDDEN", False),
        ("INTERNAL", False),
    ],
)
def test_each_error_code_raises_mads_error_with_retryable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    code: str,
    expected_retryable: bool,
) -> None:
    assert code in CLOSED_ERROR_CODES
    monkeypatch.setenv("MADS_BIN", STUB_PATH)
    monkeypatch.setenv("MADS_STUB_STATE", str(tmp_path / "state.json"))

    with pytest.raises(MadsError) as exc_info:
        call("event.append", {"simulate_error": code}, cwd=tmp_path)

    err = exc_info.value
    assert err.code == code
    assert err.retryable is expected_retryable
    assert f"simulated {code}" in err.message


def test_non_json_stdout_raises_internal_mads_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MADS_BIN", STUB_PATH)
    monkeypatch.setenv("MADS_STUB_RAW_STDOUT", "1")

    with pytest.raises(MadsError) as exc_info:
        call("event.append", {}, cwd=tmp_path)
    assert exc_info.value.code == "INTERNAL"
    assert exc_info.value.retryable is False


def test_nonzero_exit_with_no_envelope_raises_internal_mads_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MADS_BIN", STUB_PATH)
    monkeypatch.setenv("MADS_STUB_EMPTY_FAIL", "1")

    with pytest.raises(MadsError) as exc_info:
        call("event.append", {}, cwd=tmp_path)
    assert exc_info.value.code == "INTERNAL"


def test_timeout_raises_mads_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MADS_BIN", STUB_PATH)
    monkeypatch.setenv("MADS_STUB_SLEEP_S", "0.5")
    monkeypatch.setenv("MADS_TIMEOUT_S", "0.05")

    with pytest.raises(MadsError) as exc_info:
        call("event.append", {}, cwd=tmp_path)
    assert exc_info.value.code == "INTERNAL"
    assert "timed out" in exc_info.value.message.lower()
