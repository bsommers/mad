# Requirements: maiors

**Defined:** 2026-10-23 (v1.0)
**Core Value:** A handoff never loses state. Whichever CLI picks up a task gets the unresolved problem and the next steps in one file, and the global log shows how the task got there.

## v1 Requirements

Milestone v1.0, Orchestration core. Details for every requirement are in `docs/superpowers/specs/2026-10-23-maiors-design.md`.

### Store

- [ ] **STORE-01**: `maiors init` creates `.active_context/` (with an `INDEX.md` stub) and `.global_dev_log.md` (with an OKF header) when missing, never overwrites, and is idempotent (design §3, §5)
- [ ] **STORE-02**: `maiors log` appends exactly one entry in the design §3 format. Earlier bytes of the log stay byte-identical, and multi-line values are flattened

### Route

- [ ] **ROUTE-01**: `maiors route` picks the agent by the scoring rule in design §4.1 (keywords from `config/routing.json`, >5 files = an agy signal, ties go to claude) and prints the Decision JSON
- [ ] **ROUTE-02**: The model is chosen per the design §4.2 table (haiku/sonnet/opus for claude; flash/argon ids for agy), with `--model` override
- [ ] **ROUTE-03**: `maiors run` builds the argv (`claude --model M PROMPT` / `agy --model M -i PROMPT`), appends a `transition` log entry and execs. `--dry-run` prints the argv and changes nothing. Binaries come from `MAIORS_CLAUDE_BIN` / `MAIORS_AGY_BIN`

### Context skills

- [ ] **CTX-01**: `context_orchestrator` skill appends a `handoff` entry and writes `.opengsd_handoff.md` with the four sections in design §6
- [ ] **CTX-02**: `maiors fetch KEYWORD...` scores `.active_context/*.md` (keywords 2 points, title words 1 point), prints paths highest first within `fetch_budget_bytes`; `--reindex` regenerates `INDEX.md`. The `context_fetcher` skill wraps it
- [ ] **CTX-03**: `route_task` skill runs `maiors check`; on `handoff` it runs context_orchestrator, stops, and prints the handoff command
- [ ] **CTX-04**: `maiors handoff` execs agy with the handoff file as the initial prompt, and exits 1 when the file is missing
- [ ] **CTX-05**: `scripts/install-skills.sh` symlinks the skills into `~/.claude/skills/` and the agy plugin dir; `--dry-run` lists the actions; it is never run by tests

### Telemetry

- [ ] **TEL-01**: `.agent_telemetry.json` follows the design §7 schema; writes are atomic (temp file + rename)
- [ ] **TEL-02**: Claude window usage is estimated from user-prompt entries in `~/.claude/projects/*/*.jsonl` within `window_hours`; the transcript root is overridable for tests
- [ ] **TEL-03**: `maiors check` exits 10 (`handoff`) at `ceil(budget × ratio)` claude messages, or when agy is at `max_concurrent` or was rate-limited within 15 min; otherwise exits 0 (`ok`)
- [ ] **TEL-04**: A project `.claude/settings.json` `UserPromptSubmit` hook runs `maiors check` and, on exit 10, injects the context_orchestrator instruction

## Out of Scope

| Feature | Reason |
|---------|--------|
| API keys / HTTP APIs | Subscription limits only (brief §1) |
| SQLite / Redis | Markdown is native to agents (brief §2) |
| Live model switching | No CLI supports it; subagent tiers cover it |
| Exact quota readout | No source exists; estimate instead |
| Editing plugin-owned skills | They belong to plugins; supersede instead |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STORE-01 | Phase 1 | Pending |
| STORE-02 | Phase 1 | Pending |
| ROUTE-01 | Phase 1 | Pending |
| ROUTE-02 | Phase 1 | Pending |
| ROUTE-03 | Phase 1 | Pending |
| CTX-01 | Phase 2 | Pending |
| CTX-02 | Phase 2 | Pending |
| CTX-03 | Phase 2 | Pending |
| CTX-04 | Phase 2 | Pending |
| CTX-05 | Phase 2 | Pending |
| TEL-01 | Phase 3 | Pending |
| TEL-02 | Phase 3 | Pending |
| TEL-03 | Phase 3 | Pending |
| TEL-04 | Phase 3 | Pending |

**Coverage:** 14 v1 requirements, 14 mapped, 0 unmapped.
