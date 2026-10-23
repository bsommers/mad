from datetime import UTC, date, datetime

import pytest

from mad.handoff import (
    REQUIRED_SECTIONS,
    build_handoff_command,
    validate_handoff,
    write_handoff,
)


def test_write_and_validate_handoff(tmp_path):
    t = datetime(2026, 10, 23, 18, 0, 0, tzinfo=UTC)
    hp = write_handoff(
        tmp_path,
        agent="claude",
        problem="MQTT reconnect drops subscriptions",
        steps=["Reproduce in test_mqtt.py", "Resubscribe inside on_connect"],
        context_files=[".active_context/mqtt.md"],
        verify_cmds=["pytest tests/test_mqtt.py -q"],
        today=date(2026, 10, 23),
        now=t,
    )
    assert hp == tmp_path / ".opengsd_handoff.md"
    content = validate_handoff(hp)
    assert content.startswith("---\ntitle: Session handoff\n")
    for sec in REQUIRED_SECTIONS:
        assert sec in content
    assert "1. Reproduce in test_mqtt.py\n2. Resubscribe inside on_connect\n" in content
    assert "- .active_context/mqtt.md\n" in content
    assert "- pytest tests/test_mqtt.py -q\n" in content

    log_text = (tmp_path / ".global_dev_log.md").read_text(encoding="utf-8")
    assert "## 2026-10-23T18:00:00Z · handoff · claude\n" in log_text
    assert "- task: MQTT reconnect drops subscriptions\n" in log_text


def test_validate_handoff_missing_or_empty(tmp_path):
    missing = tmp_path / ".opengsd_handoff.md"
    with pytest.raises(ValueError, match="handoff file not found"):
        validate_handoff(missing)

    missing.write_text("   \n", encoding="utf-8")
    with pytest.raises(ValueError, match="handoff file not found"):
        validate_handoff(missing)


def test_validate_handoff_malformed_sections(tmp_path):
    bad = tmp_path / ".opengsd_handoff.md"
    bad.write_text("---\ntitle: x\nkeywords: [x]\nupdated: 2026-10-23\n---\n\n## Unresolved problem\nx\n", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed handoff file"):
        validate_handoff(bad)


def test_build_handoff_command():
    cmd = build_handoff_command("handoff body", "gemini-4-argon-high", {"MAD_AGY_BIN": "/tmp/agy_stub"})
    assert cmd == ["/tmp/agy_stub", "--model", "gemini-4-argon-high", "-i", "handoff body"]
