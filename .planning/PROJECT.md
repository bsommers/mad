# mad

## What This Is

mad (Multi-Agent Intelligent Orchestration & Routing System) is a local orchestration layer for one developer
who has two subscriptions: Claude Code Pro (`claude`) and Google AI Ultra (`agy`). It routes each task to the
right CLI and model, gives agents only the context they need, and keeps a shared Markdown log so that work can
hand off between the CLIs before a usage limit stops it. It extends the OpenGSD and superpowers workflows rather than replacing them.

## Core Value

A handoff never loses state. Whichever CLI picks up a task gets the unresolved problem and the next steps in one file,
and the global log shows how the task got there.

## Requirements

### Validated

- [x] Markdown state store: `.global_dev_log.md` (append-only) and `.active_context/` (STORE-01, STORE-02) — Validated in Phase 1: Foundation
- [x] Router: agent choice, model choice, launch with dry-run (ROUTE-01..03) — Validated in Phase 1: Foundation

### Active

<!-- Milestone v1.0: Orchestration core (brief Phases 1-3). -->

- [ ] Skills: context_orchestrator, context_fetcher, route_task, `mad handoff`, skill install (CTX-01..05)
- [ ] Telemetry and limit enforcement with a Claude Code hook (TEL-01..04)

### Out of Scope

- API keys and HTTP APIs — the whole point is to use subscription limits only
- SQLite/Redis — agents read and grep Markdown directly; a database needs bridge tooling (brief §2)
- Switching a live session's model — no CLI supports it; subagent model choice covers the need
- Exact quota measurement — neither subscription exposes it; Phase 3 estimates it
- Editing the plugin skills `compacting-context-safely` / `handing-off-sessions` — they belong to plugins; context_orchestrator supersedes them for this workflow

## Context

- Original brief: `multi-agent-intelligent-orchestration-routing-specification.md`. Design of record: `docs/superpowers/specs/2026-10-23-mad-design.md`.
- The brief's `agy --file` doesn't exist (use `-i`), and its Gemini 1.5 model names are obsolete (current ids are Gemini 3.8 Flash and Gemini 4 Argon).
- Greenfield repo. Python 3.14 + pytest, bats and shellcheck are available.

## Constraints

- **Tech stack**: Bash entry point, Python standard library only at runtime — no install step, so it works in both CLIs' shells
- **Safety**: tests never launch real `claude`/`agy`; binaries are injected via env vars
- **Process**: controlled mode — interactive, no auto-advance; each phase needs the user's go-ahead

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GSD artifacts only (no Claude install of gsd-core) | User choice 2026-10-23; same as the focker repo | — Pending |
| Milestone v1.0 = brief Phases 1-3 | User choice 2026-10-23 | — Pending |
| Bash + stdlib Python | User choice 2026-10-23 | — Pending |
| Ties and no-signal prompts route to claude | Cheaper, faster loop; the brief puts only heavy work on agy | — Pending |
| Claude usage estimated from local transcripts, threshold ceil(45 × 0.8) = 36 | No usage API; reconciles the brief's "~35 messages" and "80%" | — Pending |

---
*Last updated: 2026-10-23 after onboarding*
