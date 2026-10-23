# Roadmap: mad

## Milestones

- 🚧 **v1.0 Orchestration core** - Phases 1-3 (in progress)

## Overview

Milestone v1.0 builds the brief's three phases in order:

1. the state store and the router, the foundation everything else writes to
2. the three skills that move context between agents, plus the handoff command
3. telemetry that notices an approaching limit and forces a handoff before work is lost

## Phases

- [x] **Phase 1: Foundation** - Markdown store and router CLI (completed 2026-10-23)
- [ ] **Phase 2: Context skills** - context_orchestrator, context_fetcher, route_task, handoff
- [ ] **Phase 3: Telemetry & limits** - usage estimate, `mad check`, Claude Code hook

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

**Plans**: TBD (written at phase start with superpowers:writing-plans)

### Phase 3: Telemetry & limits

**Goal**: Work hands off before a usage limit cuts it off
**Depends on**: Phase 2
**Requirements**: TEL-01, TEL-02, TEL-03, TEL-04
**Success Criteria** (what must be TRUE):

  1. With a fixture transcript holding 36 user prompts in the last 5 h, `mad check` exits 10; with 35 it exits 0
  2. Prompts older than the window aren't counted
  3. The telemetry file is valid JSON after any interrupted write (atomic rename)
  4. The project hook runs `mad check` and injects the orchestrator instruction on exit 10

**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 1/1 | Complete    | 2026-10-23 |
| 2. Context skills | v1.0 | 0/TBD | Not started | - |
| 3. Telemetry & limits | v1.0 | 0/TBD | Not started | - |
