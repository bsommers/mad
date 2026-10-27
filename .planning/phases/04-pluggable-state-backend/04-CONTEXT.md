# Phase 4: Pluggable state backend - Context

**Gathered:** 2026-10-26
**Status:** Draft, not ready for planning (awaiting user go-ahead and the mads store's Task 10)

<domain>
## Phase Boundary

Let mad keep shared state either in the controlled files (today, default) or in the separate `mads` embedded store, behind a 5-method `StateBackend` protocol. Out of this phase: any change to `route.classify`, any database access from mad's own code, API keys, and building `mads` itself (lives in `~/src/meso/mads`).

</domain>

<decisions>
## Decisions (owner, 2026-10-26)

- **D-01:** The "no SQLite or Redis" invariant is amended, not dropped: SQLite may exist only inside the separate `mads` binary, reached through `mads --json`. Amendment text is in the step plan; apply it in its Task 5.
- **D-02:** `files` stays the default and stays authoritative unless `mads` is selected. In `mads` mode the Markdown/JSON files are regenerated projections so `agy -i "$(cat .opengsd_handoff.md)"` keeps working.
- **D-03:** One mads DB per project, at the main-worktree root. Agent identity is open strings checked against a roster table.

## Open items to settle at approval

- `state_backend` in `config/routing.json` (default) or a new `config/state.json`
- Whether telemetry moves at all (default: stays on `files`, mirrored into `mads`)

## Canonical references

- Step plan: `docs/superpowers/plans/2026-10-26-phase-4-pluggable-state-backend.md`
- mads spec and wire contract (`mads.contract/1`): `~/src/meso/mads/SPEC.md` §4

</decisions>
