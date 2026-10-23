# Phase 1: Foundation - Context

**Gathered:** 2026-10-23
**Status:** Ready for execution (awaiting user go-ahead)

## Phase Boundary

Markdown state store (`.global_dev_log.md`, `.active_context/`) and the router CLI (`init`, `route`, `run`, `log`).
Skills, `fetch`, `handoff`, and telemetry belong to Phases 2-3.

## Implementation Decisions

- Bash entry point + stdlib Python package `mad/` (user choice). pytest and bats for tests, shellcheck for lint.
- Routing is a score: agy wins only on a strictly higher score, so ties and no-signal prompts go to claude (spec §4.1).
- Model ids are in `config/routing.json`: claude `haiku|sonnet|opus`; agy `gemini-3.8-flash-medium` / `gemini-4-argon-high`.
- agy gets its initial prompt via `-i` (no `--file` exists).
- `run --dry-run` writes nothing. A real `run` logs a `transition` entry before exec.

## Canonical References

- `docs/superpowers/specs/2026-10-23-mad-design.md` §3-§5, §9
- `docs/superpowers/plans/2026-10-23-phase-1-foundation.md` (step-level plan)

## Deferred Ideas

- `mad fetch`, `mad handoff` → Phase 2; `mad check` and hooks → Phase 3.
