# Roadmap: mad

## Milestones

- ✅ **v1.0 Orchestration core** - Phases 1-3 (completed 2026-10-23)
- ✅ **v1.1 Pluggable state backend** - Phase 4 (completed 2026-10-30)
- ✅ **v1.2 Worker leases & atomic handoff claims** - Phase 5 (completed 2026-11-07)

## Overview

Milestone v1.0 builds the brief's three phases in order:

1. the state store and the router, the foundation everything else writes to
2. the three skills that move context between agents, plus the handoff command
3. telemetry that notices an approaching limit and forces a handoff before work is lost

## Phases

- [x] **Phase 1: Foundation** - Markdown store and router CLI (completed 2026-10-23)
- [x] **Phase 2: Context skills** - context_orchestrator, context_fetcher, route_task, handoff (completed 2026-10-23)
- [x] **Phase 3: Telemetry & limits** - usage estimate, `mad check`, Claude Code hook (completed 2026-10-23)
- [x] **Phase 4: Pluggable state backend** - `files` (default) or `mads` store behind one protocol (completed 2026-10-30)
- [x] **Phase 5: Worker leases & atomic handoff claims** - `agy` slot leasing (`claim_task`/`release_task`) and `mad handoff --take` (`take_handoff`) when `mads` backend is active (completed 2026-11-07)

## Phase Details

### Phase 1: Foundation

**Goal**: Any prompt can be routed to the right CLI and model, and every launch is recorded in an append-only log
**Depends on**: Nothing
**Requirements**: STORE-01, STORE-02, ROUTE-01, ROUTE-02, ROUTE-03
**Success Criteria** (what must be TRUE):

  1. `bin/mad init` run twice leaves the same files, and an existing log stays byte-identical
  2. `bin/mad route "debug the reconnect" a.py` prints `"agent": "claude", "model": "sonnet"`; with 6 files and "design" it prints agy / `gemini-4-argon-high`
  3. `bin/mad run --dry-run ...` prints the exact argv; without `--dry-run`, the stub binary receives it and a `transition` entry is appended
  4. `pytest -q && bats tests/cli.bats && shellcheck bin/mad` pass

**Plans**: 1/1 plans complete

Plans:

- [x] 01-01-PLAN.md — store, route, launch, CLI (steps in docs/superpowers/plans/2026-10-23-phase-1-foundation.md)

### Phase 2: Context skills

**Goal**: An agent can load only the context a task needs, and hand off to the other CLI with one command
**Depends on**: Phase 1
**Requirements**: CTX-01, CTX-02, CTX-03, CTX-04, CTX-05
**Success Criteria** (what must be TRUE):

  1. With fixture files `docker_guidelines.md` and `ui_components.md`, `mad fetch docker` prints only the docker file
  2. Running context_orchestrator produces `.opengsd_handoff.md` with exactly the four design §6 sections and appends a `handoff` entry
  3. `mad handoff` passes the handoff file's content to the agy stub via `-i`, and exits 1 without the file
  4. `install-skills.sh --dry-run` lists the symlinks it would create and touches nothing

**Plans**: 1/1 plans complete

Plans:

- [x] 02-01-PLAN.md — context fetcher, handoff writer/launcher, skills, installer (steps in docs/superpowers/plans/2026-10-23-phase-2-context-skills.md)

### Phase 3: Telemetry & limits

**Goal**: Work hands off before a usage limit cuts it off
**Depends on**: Phase 2
**Requirements**: TEL-01, TEL-02, TEL-03, TEL-04
**Success Criteria** (what must be TRUE):

  1. With a fixture transcript holding 36 user prompts in the last 5 h, `mad check` exits 10; with 35 it exits 0
  2. Prompts older than the window aren't counted
  3. The telemetry file is valid JSON after any interrupted write (atomic rename)
  4. The project hook runs `mad check` and injects the orchestrator instruction on exit 10

**Plans**: 1/1 plans complete

Plans:

- [x] 03-01-PLAN.md — telemetry store, transcript counter, `mad check`, Claude Code hook (steps in docs/superpowers/plans/2026-10-23-phase-3-telemetry-limits.md)

### Phase 4: Pluggable state backend

**Goal**: mad keeps shared state in the controlled files (default, unchanged) or in the `mads` embedded store, chosen by one setting, with identical CLI behavior and exit codes
**Depends on**: Phase 3; external: `~/src/meso/mads` Task 10 (stable CLI verbs). Ships safely without `mads` built, since `files` stays the default
**Requirements**: BACK-01, BACK-02, BACK-03, BACK-04, BACK-05
**Status**: Complete (2026-10-30)
**Success Criteria** (what must be TRUE):

  1. With `MAD_STATE_BACKEND` unset, all existing `pytest -q` and `bats tests/cli.bats` tests pass with no assertion edits
  2. One shared contract suite passes for `FilesBackend` and for `MadsBackend` against a stub `MADS_BIN`
  3. With `mads` absent and `MAD_STATE_BACKEND=mads`, mad falls back to `files` and appends exactly one `note`
  4. `route` output is identical in both modes
  5. The handoff exported from `mads` equals the files-backend `.opengsd_handoff.md` modulo the `updated:` date

**Plans**: 1/1 plans complete

Plans:

- [x] 04-01-PLAN.md — backend protocol, FilesBackend, mads_client, MadsBackend, AGENTS.md amendment (steps in docs/superpowers/plans/2026-10-26-phase-4-pluggable-state-backend.md)

### Phase 5: Worker leases & atomic handoff claims

**Goal**: Prevent concurrent `agy` workers from exceeding `agy_max_concurrent` or double-consuming a handoff when `MAD_STATE_BACKEND=mads`, while remaining a safe no-op in `files` mode
**Depends on**: Phase 4
**Requirements**: COORD-01, COORD-02, COORD-03
**Status**: Complete (2026-11-07)
**Success Criteria** (what must be TRUE):

  1. In `mads` mode, `mad handoff --take` claims and consumes the oldest open handoff via `mads tool take_handoff`; a second concurrent taker receives exit `1` (`no open handoff`)
  2. `mad claim` / `mad release` (or `mad check` slot probe) acquires/releases `agy:slot:<N>` up to `agy_max_concurrent` (2) via `mads tool claim_task` / `release_task`
  3. In `files` mode (default), all existing behavior and tests remain unchanged

**Plans**: 1/1 plans complete

Plans:

- [x] 05-01-PLAN.md — atomic handoff take and `agy` concurrency lease primitives (steps in docs/superpowers/plans/2026-11-07-phase-5-worker-leases-and-handoff-claims.md)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 1/1 | Complete    | 2026-10-23 |
| 2. Context skills | v1.0 | 1/1 | Complete    | 2026-10-23 |
| 3. Telemetry & limits | v1.0 | 1/1 | Complete    | 2026-10-23 |
| 4. Pluggable state backend | v1.1 | 1/1 | Complete    | 2026-10-30 |
| 5. Worker leases & atomic handoff claims | v1.2 | 1/1 | Complete | 2026-11-07 |
