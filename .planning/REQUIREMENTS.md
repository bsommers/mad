# Requirements: mad

**Defined:** 2026-10-23 (v1.0)
**Core Value:** A handoff never loses state. Whichever CLI picks up a task gets the unresolved problem and the next steps in one file, and the global log shows how the task got there.

## v1 Requirements

Milestone v1.0, Orchestration core. Details for every requirement are in `docs/superpowers/specs/2026-10-23-mad-design.md`.

### Store

- [x] **STORE-01**: `mad init` creates `.active_context/` (with an `INDEX.md` stub) and `.global_dev_log.md` (with an OKF header) when missing, never overwrites, and is idempotent (design §3, §5)
- [x] **STORE-02**: `mad log` appends exactly one entry in the design §3 format. Earlier bytes of the log stay byte-identical, and multi-line values are flattened

### Route

- [x] **ROUTE-01**: `mad route` picks the agent by the scoring rule in design §4.1 (keywords from `config/routing.json`, >5 files = an agy signal, ties go to claude) and prints the Decision JSON
- [x] **ROUTE-02**: The model is chosen per the design §4.2 table (haiku/sonnet/opus for claude; flash/argon ids for agy), with `--model` override
- [x] **ROUTE-03**: `mad run` builds the argv (`claude --model M PROMPT` / `agy --model M -i PROMPT`), appends a `transition` log entry and execs. `--dry-run` prints the argv and changes nothing. Binaries come from `MAD_CLAUDE_BIN` / `MAD_AGY_BIN`

### Context skills

- [x] **CTX-01**: `context_orchestrator` skill appends a `handoff` entry and writes `.opengsd_handoff.md` with the four sections in design §6
- [x] **CTX-02**: `mad fetch KEYWORD...` scores `.active_context/*.md` (keywords 2 points, title words 1 point), prints paths highest first within `fetch_budget_bytes`; `--reindex` regenerates `INDEX.md`. The `context_fetcher` skill wraps it
- [x] **CTX-03**: `route_task` skill runs `mad check`; on `handoff` it runs context_orchestrator, stops, and prints the handoff command
- [x] **CTX-04**: `mad handoff` execs agy with the handoff file as the initial prompt, and exits 1 when the file is missing
- [x] **CTX-05**: `scripts/install-skills.sh` symlinks the skills into `~/.claude/skills/` and the agy plugin dir; `--dry-run` lists the actions; it is never run by tests

### Telemetry

- [x] **TEL-01**: `.agent_telemetry.json` follows the design §7 schema; writes are atomic (temp file + rename)
- [x] **TEL-02**: Claude window usage is estimated from user-prompt entries in `~/.claude/projects/*/*.jsonl` within `window_hours`; the transcript root is overridable for tests
- [x] **TEL-03**: `mad check` exits 10 (`handoff`) at `ceil(budget × ratio)` claude messages, or when agy is at `max_concurrent` or was rate-limited within 15 min; otherwise exits 0 (`ok`)
- [x] **TEL-04**: A project `.claude/settings.json` `UserPromptSubmit` hook runs `mad check` and, on exit 10, injects the context_orchestrator instruction

## Planned (v1.1, not started)

- [ ] **BACK-01**: A `StateBackend` protocol (`mad/backend.py`) fronts append_log, write_handoff, fetch_context and telemetry read/write; `FilesBackend` reproduces today's output byte-for-byte
- [ ] **BACK-02**: `MAD_STATE_BACKEND` (`files` default | `mads`) selects the backend; an unknown value exits 2
- [ ] **BACK-03**: `mad/mads_client.py` (stdlib `subprocess` + `json`, no `shell=True`) calls the `mads` CLI and maps its closed error set; `STORE_BUSY` retries up to 3 times
- [ ] **BACK-04**: If `mads` is selected but absent, mad falls back to `files` and logs one `note` entry; routing decisions are identical in both modes
- [ ] **BACK-05**: `AGENTS.md` is amended so SQLite may exist only inside the separate `mads` binary; exported `.opengsd_handoff.md` equals the files-backend output

## Out of Scope

| Feature | Reason |
|---------|--------|
| API keys / HTTP APIs | Subscription limits only (brief §1) |
| SQLite / Redis | Markdown is native to agents (brief §2). Phase 4 (planned) permits SQLite only inside the separate `mads` binary, never in mad's own code |
| Live model switching | No CLI supports it; subagent tiers cover it |
| Exact quota readout | No source exists; estimate instead |
| Editing plugin-owned skills | They belong to plugins; supersede instead |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STORE-01 | Phase 1 | Complete |
| STORE-02 | Phase 1 | Complete |
| ROUTE-01 | Phase 1 | Complete |
| ROUTE-02 | Phase 1 | Complete |
| ROUTE-03 | Phase 1 | Complete |
| CTX-01 | Phase 2 | Complete |
| CTX-02 | Phase 2 | Complete |
| CTX-03 | Phase 2 | Complete |
| CTX-04 | Phase 2 | Complete |
| CTX-05 | Phase 2 | Complete |
| TEL-01 | Phase 3 | Complete |
| TEL-02 | Phase 3 | Complete |
| TEL-03 | Phase 3 | Complete |
| TEL-04 | Phase 3 | Complete |

| BACK-01 | Phase 4 | Pending |
| BACK-02 | Phase 4 | Pending |
| BACK-03 | Phase 4 | Pending |
| BACK-04 | Phase 4 | Pending |
| BACK-05 | Phase 4 | Pending |

**Coverage:** 14 v1 requirements, 14 mapped, 0 unmapped. 5 planned v1.1 requirements, 5 mapped.
