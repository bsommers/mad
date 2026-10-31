# Phase 4: Pluggable state backend - Context

**Gathered:** 2026-10-26 (approved 2026-10-30)
**Status:** Approved for execution

<domain>
## Phase Boundary

Let mad keep shared state either in the controlled files (today, default) or in the separate `mads` embedded store, behind a 5-method `StateBackend` protocol. Out of this phase: any change to `route.classify`, any database access from mad's own code, API keys, and building `mads` itself (lives in `~/src/meso/mads`).

</domain>

<decisions>
## Decisions (owner, 2026-10-26 / 2026-10-30)

- **D-01:** The "no SQLite or Redis" invariant is amended, not dropped: SQLite may exist only inside the separate `mads` binary, reached through `mads` JSON-over-CLI. Amendment text is in the step plan; apply it in its Task 5.
- **D-02:** `files` stays the default and stays authoritative unless `mads` is selected. In `mads` mode the Markdown/JSON files are regenerated projections so `agy -i "$(cat .opengsd_handoff.md)"` keeps working.
- **D-03:** One mads DB per project, at the main-worktree root. Agent identity is open strings checked against a roster table.
- **D-04 (2026-10-30):** Keep `"state_backend": "files"` in `config/routing.json` (single config file, overridden by `MAD_STATE_BACKEND`).
- **D-05 (2026-10-30):** Keep `.agent_telemetry.json` on `files` in both modes and mirror it into `mads` (`put_artifact` with kind `telemetry`, key `mad/agent_telemetry`) when `mads` is active.

## Canonical references

- Step plan: `docs/superpowers/plans/2026-10-26-phase-4-pluggable-state-backend.md`
- mads spec and wire contract (`mads.contract/1`): `~/src/meso/mads/SPEC.md` §4

</decisions>
