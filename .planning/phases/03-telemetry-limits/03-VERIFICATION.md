---
phase: 03-telemetry-limits
verified: 2026-10-24T01:23:00Z
status: passed
score: 5/5 must-haves verified
---

# Phase 3: Telemetry & Limits Verification Report

**Phase Goal:** Work hands off before a usage limit cuts it off.
**Verified:** 2026-10-23
**Status:** passed

## Must-Haves Verification

| # | Must-Have | Status | Evidence |
|---|-----------|--------|----------|
| 1 | With a fixture transcript holding 36 user prompts in the last 5 h, `mad check` exits 10; with 35 it exits 0 | ✓ PASS | `tests/test_telemetry.py::test_threshold_35_is_ok_and_36_triggers_handoff`, `tests/cli.bats` ("mad check counts 35 prompts as ok and 36 as handoff, writing .agent_telemetry.json") |
| 2 | Prompts older than the window aren't counted | ✓ PASS | `tests/test_telemetry.py::test_count_claude_messages_filters_window_meta_and_tool_results`, `tests/test_telemetry.py::test_threshold_35_is_ok_and_36_triggers_handoff` |
| 3 | The telemetry file is valid JSON after any interrupted write (atomic rename) | ✓ PASS | `tests/test_telemetry.py::test_atomic_write_preserves_valid_json_on_interrupted_replace` |
| 4 | The project hook runs `mad check` and injects the orchestrator instruction on exit 10 | ✓ PASS | `.claude/settings.json`, `scripts/claude-check-hook.sh`, `tests/cli.bats` ("mad check --record-rate-limit triggers handoff and UserPromptSubmit hook injects instruction") |
| 5 | `pytest -q && bats tests/cli.bats && shellcheck bin/mad tests/stub_cli.sh scripts/install-skills.sh scripts/claude-check-hook.sh` pass | ✓ PASS | 37 passed (pytest), 15/15 passed (bats), 0 warnings (shellcheck) |

## Requirements Traceability

| Requirement | Plan | Status | Verified By |
|-------------|------|--------|-------------|
| TEL-01 | 03-01 | Complete | `mad/telemetry.py`, `tests/test_telemetry.py`, `tests/cli.bats` |
| TEL-02 | 03-01 | Complete | `mad/telemetry.py`, `tests/test_telemetry.py`, `tests/cli.bats` |
| TEL-03 | 03-01 | Complete | `mad/telemetry.py`, `mad/cli.py`, `tests/test_telemetry.py`, `tests/cli.bats` |
| TEL-04 | 03-01 | Complete | `.claude/settings.json`, `scripts/claude-check-hook.sh`, `tests/cli.bats` |

## Automated Checks

```bash
pytest -q                                                                                # 37 passed
bats tests/cli.bats                                                                      # 15/15 passed
shellcheck bin/mad tests/stub_cli.sh scripts/install-skills.sh scripts/claude-check-hook.sh  # clean
```
