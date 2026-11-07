---
gsd_state_version: '1.0'
milestone: v1.2
milestone_name: Worker leases & atomic handoff claims
current_phase: 5
current_phase_name: Worker leases & atomic handoff claims
status: complete
stopped_at: Phase 5 complete (Milestone v1.2 complete)
last_updated: '2026-11-07T21:14:00Z'
last_activity: 2026-11-07
last_activity_desc: Phase 05 complete, Milestone v1.2 complete
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 5
  completed_plans: 5
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-30)

**Core value:** A handoff never loses state. Whichever CLI picks up a task gets the unresolved problem and the next steps in one file, and the global log shows how the task got there.
**Current focus:** Milestone v1.2 Worker leases & atomic handoff claims — Complete

## Current Position

Milestone: v1.2 Worker leases & atomic handoff claims
Phase: 5 (Worker leases & atomic handoff claims), of phases 1-5
Plan: 05-01-PLAN.md (complete)
Status: Milestone v1.2 complete
Last activity: 2026-11-07 — Phase 5 (Worker leases & atomic handoff claims) completed and verified

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 5

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in the PROJECT.md Key Decisions table.

- [Onboarding]: GSD artifacts were written by hand. GSD Core isn't installed for Claude Code (user choice: artifacts only).
- [Onboarding]: Milestone v1.0 covers brief Phases 1-3. Language: Bash + stdlib Python. Git initialized with a first commit (user choices).
- [Onboarding]: Fixed against the installed tools: `agy` has no `--file` (use `-i`); Gemini 1.5 ids replaced with Gemini 3.8 Flash / 4 Argon.
- [Phase 1]: Renamed repository, package, and CLI from `maiors` to `mad` (user choice).
- [Phase 2]: Provided `mad handoff --write` CLI helper for atomic handoff generation + logging (`D-09`) and `mad check` stub (`MAD_FORCE_HANDOFF=1` → exit 10) for pre-Phase-3 skill testing (`D-10`).
- [Phase 3]: Estimated Claude window usage from non-meta, non-tool-result user prompts in `MAD_CLAUDE_PROJECTS_DIR/*/*.jsonl` (`D-05`), preserved `agy` concurrency/rate-limit state in `.agent_telemetry.json` via atomic write-and-rename (`D-02`, `D-07`), and wired `.claude/settings.json` `UserPromptSubmit` hook to `scripts/claude-check-hook.sh` (`D-10`, `D-11`).
- [Phase 4]: Added 5-method `StateBackend` protocol (`mad/backend.py`) with `FilesBackend` (default, `"state_backend": "files"` in `config/routing.json`, `D-04`) and `MadsBackend` (`mad/mads_backend.py` + `mad/mads_client.py` speaking `mads.contract/1`), keeping `.agent_telemetry.json` on `files` and mirroring to `mads` (`D-05`), and amending `AGENTS.md` (`D-01`).
- [Phase 5]: Kept `StateBackend` at 5 methods (`D-01`) and introduced a separate 3-member `CoordinationBackend` protocol (`take_handoff`, `claim_slot`, `release_slot`) implemented by `FilesBackend` (no-op / file validation) and `MadsBackend` (`mads tool take_handoff`, `claim_task`, `release_task`).

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-11-07
Stopped at: Phase 5 complete (Milestone v1.2 complete)
Resume file: .planning/ROADMAP.md
