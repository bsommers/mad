"""Task 5 real-binary integration test for MadsBackend (`mads.contract/1`)."""
from pathlib import Path
import re
import subprocess
import pytest

from mad import cli
from mad.files_backend import FilesBackend
from mad.handoff import validate_handoff
from mad.mads_client import resolve_mads_bin


def _normalize_updated_date(md: str) -> str:
    return re.sub(r"(?m)^updated: \d{4}-\d{2}-\d{2}$", "updated: YYYY-MM-DD", md)


def _require_real_mads() -> str:
    mads_bin = resolve_mads_bin()
    if not mads_bin or "mads_stub" in Path(mads_bin).name:
        pytest.skip("MADS_BIN is not set to a real mads binary")
    try:
        proc = subprocess.run(
            [mads_bin, "version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except OSError:
        pytest.skip("real mads binary could not be executed")
    if proc.returncode != 0 or "mads.contract/1" not in proc.stdout:
        pytest.skip("mads binary does not report mads.contract/1")
    return mads_bin


def test_real_mads_end_to_end_and_handoff_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mads_bin = _require_real_mads()

    proj_mads = tmp_path / "proj_mads"
    proj_files = tmp_path / "proj_files"
    proj_mads.mkdir()
    proj_files.mkdir()
    (proj_mads / ".git").mkdir()
    (proj_files / ".git").mkdir()

    monkeypatch.setenv("MADS_BIN", mads_bin)
    monkeypatch.setenv("MADS_DB", str(proj_mads / ".mads" / "store.db"))
    monkeypatch.setenv("MAD_STATE_BACKEND", "mads")
    monkeypatch.setenv("MAD_CLAUDE_PROJECTS_DIR", str(tmp_path / "empty_transcripts"))
    monkeypatch.chdir(proj_mads)

    assert cli.main(["init"]) == 0
    assert cli.main(["log", "--kind", "task", "--agent", "claude", "Implement backend adapter"]) == 0
    assert (
        cli.main(
            [
                "handoff",
                "--write",
                "--agent",
                "claude",
                "--problem",
                "Socket timeout under burst load",
                "--step",
                "Increase backoff cap",
                "--step",
                "Run stress test",
                "--context",
                ".active_context/net.md",
                "--verify",
                "pytest -q",
            ]
        )
        == 0
    )
    assert cli.main(["fetch", "socket"]) == 0
    assert cli.main(["check"]) == 0

    mads_handoff_path = proj_mads / ".opengsd_handoff.md"
    mads_handoff_text = validate_handoff(mads_handoff_path)

    fb = FilesBackend(proj_files)
    files_handoff_path = fb.write_handoff(
        agent="claude",
        problem="Socket timeout under burst load",
        steps=["Increase backoff cap", "Run stress test"],
        context_files=[".active_context/net.md"],
        verify_cmds=["pytest -q"],
    )
    files_handoff_text = validate_handoff(files_handoff_path)

    assert _normalize_updated_date(mads_handoff_text) == _normalize_updated_date(files_handoff_text)

    # Phase 5 (COORD-01..02): atomic take_handoff and 2-slot claim/release against real mads
    assert cli.main(["handoff", "--take", "--print"]) == 0
    assert cli.main(["handoff", "--take", "--print"]) == 1

    from mad.mads_backend import MadsBackend

    mb = MadsBackend(proj_mads)
    lease1 = mb.claim_slot("agy", max_concurrent=2, ttl_s=60)
    lease2 = mb.claim_slot("agy", max_concurrent=2, ttl_s=60)
    assert lease1["slot"] == 1
    assert lease2["slot"] == 2
    with pytest.raises(ValueError, match="all agy slots busy"):
        mb.claim_slot("agy", max_concurrent=2, ttl_s=60)
    assert mb.release_slot(lease1["claim_id"], lease1["fencing_token"]) == {"released": True}
    lease3 = mb.claim_slot("agy", max_concurrent=2, ttl_s=60)
    assert lease3["slot"] == 1
    assert lease3["fencing_token"] > lease1["fencing_token"]
