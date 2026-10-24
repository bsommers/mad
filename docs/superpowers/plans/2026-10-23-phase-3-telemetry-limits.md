# Phase 3: Telemetry & Limits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Estimate Claude Pro window usage from local JSONL transcripts, persist `.agent_telemetry.json` atomically, evaluate handoff thresholds in `mad check` (exit `0` vs `10`), and enforce pre-prompt limit checks via a project-level Claude Code `UserPromptSubmit` hook.

**Architecture:** `mad/telemetry.py` scans `~/.claude/projects/*/*.jsonl` (overridable via `MAD_CLAUDE_PROJECTS_DIR` or `--transcripts-dir`), counts non-meta user prompts within `window_hours`, merges/updates `.agent_telemetry.json` via atomic temp-file write + `os.replace`, and evaluates handoff thresholds (`ceil(budget * ratio)` Claude messages, `agy.running >= max_concurrent`, `agy.last_rate_limit` within 15 minutes, or `MAD_FORCE_HANDOFF=1`). `mad/cli.py` wires `mad check` to `mad.telemetry`. `.claude/settings.json` and `scripts/claude-check-hook.sh` implement the `UserPromptSubmit` hook.

**Tech Stack:** Bash, Python 3.14 standard library, pytest 9 (tests only), bats, shellcheck.

**Spec:** `docs/superpowers/specs/2026-10-23-mad-design.md` (§5 CLI, §7 Telemetry and limits). GSD: `.planning/phases/03-telemetry-limits/03-01-PLAN.md`, `.planning/phases/03-telemetry-limits/03-CONTEXT.md` (`D-01`–`D-11`), requirements `TEL-01..04`.

## Global Constraints

- Runtime code imports only the Python standard library.
- No test reads real `~/.claude/projects` or scans host processes: tests pass `tmp_path` or set `MAD_CLAUDE_PROJECTS_DIR`.
- `.agent_telemetry.json` writes are always atomic (`NamedTemporaryFile` in the target directory + `os.replace`).
- Exit codes: `0` ok, `1` runtime error, `2` usage error, `10` handoff needed (`mad check`).

---

### Task 1: Telemetry store, transcript counter, and limit evaluator (`mad/telemetry.py`)

**Files:**
- Modify: `config/routing.json` (add `"telemetry"` defaults)
- Create: `mad/telemetry.py`
- Test: `tests/test_telemetry.py`

**Interfaces:**
- `count_claude_messages(transcripts_dir: Path, window_hours: float = 5.0, now: datetime | None = None) -> tuple[int, str | None]`:
  - Scans `transcripts_dir.glob("*/*.jsonl")` (and `transcripts_dir.glob("*.jsonl")` if flat fixtures are passed, or `*/*.jsonl` per spec §7). Let's support both `transcripts_dir.rglob("*.jsonl")` when `transcripts_dir.exists()` so any project subdirectory layout under `transcripts_dir` works cleanly (`D-04`).
  - Counts lines that parse as JSON dicts where `obj.get("type") == "user"`, `not obj.get("isMeta")`, `message.content` (if a list) is not composed solely of `tool_result` blocks, and `obj.get("timestamp")` parses as an ISO-8601 timestamp in `[now - timedelta(hours=window_hours), now]` (`D-05`).
  - Returns `(messages_in_window, oldest_in_window_utc_iso_or_none)` (`D-06`).
- `read_telemetry(root: Path) -> dict`: reads `root / ".agent_telemetry.json"`, returning `{}` if missing or invalid JSON.
- `write_telemetry_atomic(root: Path, data: dict) -> Path`: writes JSON to a temp file in `root` and atomically replaces `root / ".agent_telemetry.json"` via `os.replace` (`D-01`, `D-02`).
- `check_limits(root: Path, cfg: dict | None = None, transcripts_dir: Path | None = None, record_rate_limit: bool = False, env: Mapping[str, str] | None = None, now: datetime | None = None) -> tuple[bool, dict]`:
  - Resolves `transcripts_dir` from argument -> `env.get("MAD_CLAUDE_PROJECTS_DIR")` -> `Path.home() / ".claude" / "projects"`.
  - Counts Claude window prompts via `count_claude_messages`.
  - Preserves existing `agy.running` and `agy.last_rate_limit` from `read_telemetry(root)`, applying `MAD_AGY_RUNNING` override if set and setting `last_rate_limit = _utc_iso(now)` if `record_rate_limit=True` (`D-07`).
  - Atomically writes updated `.agent_telemetry.json` (`D-08`).
  - Returns `(should_handoff, payload)` where `should_handoff` is `True` when `MAD_FORCE_HANDOFF == "1"`, `messages_in_window >= math.ceil(budget * ratio)`, `agy.running >= max_concurrent`, or `last_rate_limit` is within `cooldown_minutes` (`15` min) of `now` (`D-08`, `D-09`).

- [ ] **Step 1: Update `config/routing.json` and write failing unit tests in `tests/test_telemetry.py`**
- [ ] **Step 2: Run `pytest tests/test_telemetry.py -q` (expect `ModuleNotFoundError: No module named 'mad.telemetry'`)**
- [ ] **Step 3: Implement `mad/telemetry.py`**
- [ ] **Step 4: Run `pytest tests/test_telemetry.py -q` (expect all pass)**
- [ ] **Step 5: Commit `feat(03-01): telemetry transcript counter and atomic store`**

---

### Task 2: Wire `mad check` in `mad/cli.py` and Claude Code `UserPromptSubmit` hook

**Files:**
- Modify: `mad/cli.py`
- Create: `scripts/claude-check-hook.sh` (mode `0755`)
- Create: `.claude/settings.json`
- Modify: `tests/cli.bats`

**Interfaces:**
- `mad check [--transcripts-dir PATH] [--record-rate-limit]`:
  - Calls `check_limits(root, cfg=load_config(), transcripts_dir=..., record_rate_limit=ns.record_rate_limit, env=os.environ)`.
  - Prints `handoff` and exits `10` if `should_handoff` is `True`; prints `ok` and exits `0` otherwise (`D-09`).
- `scripts/claude-check-hook.sh`:
  - Runs `"$ROOT/bin/mad" check >/dev/null 2>&1` (capturing exit code `rc`).
  - If `rc -eq 10`, prints Claude Code `UserPromptSubmit` hook JSON with `hookSpecificOutput.additionalContext` instructing the agent to run `context_orchestrator` (`bin/mad handoff --write ...`), stop, and print `bin/mad handoff`, then exits `0` (`D-11`).
  - Otherwise outputs nothing and exits `0`.
- `.claude/settings.json`:
  - Configures `hooks.UserPromptSubmit` to run `scripts/claude-check-hook.sh` (`D-10`).

- [ ] **Step 1: Add failing bats tests in `tests/cli.bats` for `mad check` (35 vs 36 messages, rate limit, telemetry JSON creation) and `scripts/claude-check-hook.sh`**
- [ ] **Step 2: Run `bats tests/cli.bats` (expect new tests to fail)**
- [ ] **Step 3: Update `mad/cli.py`, create `scripts/claude-check-hook.sh` (`chmod 755`), and create `.claude/settings.json`**
- [ ] **Step 4: Run `pytest -q && bats tests/cli.bats && shellcheck bin/mad tests/stub_cli.sh scripts/install-skills.sh scripts/claude-check-hook.sh`**
- [ ] **Step 5: Commit `feat(03-01): wire mad check telemetry and UserPromptSubmit hook`**

---

### Task 3: Close Phase 3 & Milestone v1.0 (GSD bookkeeping)

- [ ] Write `.planning/phases/03-telemetry-limits/03-01-SUMMARY.md` and `.planning/phases/03-telemetry-limits/03-VERIFICATION.md`.
- [ ] Mark `TEL-01..04` complete in `.planning/REQUIREMENTS.md`, check Phase 3 in `.planning/ROADMAP.md`, and update `.planning/STATE.md` and `.planning/PROJECT.md`.
- [ ] Log Phase 3 completion via `bin/mad log --kind decision --agent mad "Phase 3 telemetry and limits complete"`.
- [ ] Commit `docs: close phase 3 (telemetry & limits)`.
