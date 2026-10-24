# Phase 3: Telemetry & limits - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-23
**Phase:** 03-telemetry-limits
**Areas discussed:** Claude JSONL transcript counting, agy concurrency & rate-limit state, Claude Code UserPromptSubmit hook, execution mode

---

## Claude JSONL transcript counting (TEL-02)

| Question | Selected Option |
|----------|-----------------|
| How to count user prompts in `~/.claude/projects/*/*.jsonl` | Count `type == 'user'` lines within `window_hours` in `MAD_CLAUDE_PROJECTS_DIR` (default `~/.claude/projects`), excluding `isMeta: true` and `tool_result`-only messages, skipping malformed lines |

---

## agy concurrency & rate-limit state (TEL-03)

| Question | Selected Option |
|----------|-----------------|
| How `mad check` determines `agy.running` and `agy.last_rate_limit` | Read/preserve `agy.running` and `agy.last_rate_limit` from `.agent_telemetry.json` (with `MAD_AGY_RUNNING` env override and `--record-rate-limit` CLI flag) so tests never scan host processes |

---

## Project UserPromptSubmit hook (TEL-04)

| Question | Selected Option |
|----------|-----------------|
| How `.claude/settings.json` hook is structured | Call `scripts/claude-check-hook.sh`, which runs `bin/mad check` and emits `hookSpecificOutput` `additionalContext` JSON on exit 10 |

---

## Execution

| Question | Selected Option |
|----------|-----------------|
| Proceed with Phase 3 execution | Write `03-CONTEXT.md` + `03-01-PLAN.md` and execute Phase 3 end-to-end with TDD now |

## Deferred Ideas

None.
