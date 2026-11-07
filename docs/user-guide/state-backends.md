# State Backends (`files` and `mads`)

`mad` supports two state backends behind the `StateBackend` protocol (`mad/backend.py`):

| Backend | Default? | Authoritative Store | Dependencies |
| --- | --- | --- | --- |
| `files` | **Yes** | `.global_dev_log.md`, `.active_context/`, `.opengsd_handoff.md`, `.agent_telemetry.json` | Python stdlib only |
| `mads` | No | `.mads/store.db` via the `mads` CLI (`mads.contract/1`), with Markdown/JSON files maintained as projections | Python stdlib + external `mads` binary |

## When to Choose Each Backend

- **Choose `files` (default)** for single-developer, sequential CLI sessions where plain OKF Markdown and JSON files are sufficient and zero external binaries are desired.
- **Choose `mads`** when coordinating state across multiple concurrent workers (e.g., `agy_max_concurrent: 2`) or sharing run/event/artifact state with `climah`.

## How to Switch Backends

You can select the backend either per-invocation via environment variable or persistently in `config/routing.json`:

```bash
# Per-invocation / shell environment override
export MAD_STATE_BACKEND=mads
export MADS_BIN=/path/to/mads   # optional if `mads` is already on PATH
```

Or in `config/routing.json`:

```json
{
  "state_backend": "mads"
}
```

Valid values are `"files"` and `"mads"`. Any other value causes `mad` to exit with code `2` (usage error).

### Graceful Fallback

If `mads` is selected (`MAD_STATE_BACKEND=mads` or `"state_backend": "mads"`) but the `mads` binary is not found on `PATH` (or at `MADS_BIN`), `mad` automatically falls back to the `files` backend and appends a single `note` entry to `.global_dev_log.md` per process.

## Migrating Existing State to `mads`

To import existing `mad` files (`.global_dev_log.md`, `.opengsd_handoff.md`, `.agent_telemetry.json`) into the `mads` store:

```bash
# 1. Initialize the mads store at the repository root
mads init

# 2. Preview the import plan (dry-run by default)
mads import --from mad .

# 3. Apply the import (idempotent by content hash / event_id)
mads import --from mad --apply .
```

## Rolling Back to `files`

Because `MadsBackend` keeps `.global_dev_log.md`, `.opengsd_handoff.md`, and `.agent_telemetry.json` updated on disk as projections (and `mads export --format md --out . --force` can regenerate them at any time), rolling back to `files` requires only setting:

```bash
export MAD_STATE_BACKEND=files
```

or setting `"state_backend": "files"` in `config/routing.json`. Ensure `.global_dev_log.md` and `.opengsd_handoff.md` are writable (`chmod u+w .global_dev_log.md .opengsd_handoff.md` if previously exported read-only by `mads export --out`).

## Worker Leases & Atomic Handoff Claims (`v1.2`)

To prevent multiple concurrent `agy` workers from exceeding concurrency thresholds (`agy_max_concurrent`, default 2) or double-consuming open handoffs, `mad` provides worker leases and atomic handoff claiming across both backends via the `CoordinationBackend` interface:

### Atomic Handoff Take (`mad handoff --take`)

```bash
# Claim oldest open handoff, project to .opengsd_handoff.md, and launch agy (or print/dry-run)
mad handoff --take
mad handoff --take --print
mad handoff --take --dry-run
```

- **In `mads` mode**: Calls `mads tool take_handoff` inside an immediate transaction, atomically marking the oldest open handoff taken by the specified `--agent` (default `agy`). Projects the claimed markdown to `.opengsd_handoff.md`. If no open handoff exists, exits `1` (`mad: no open handoff`). `--write` and `--take` cannot be combined (exits `2`).
- **In `files` mode**: Deterministically reads and validates `.opengsd_handoff.md` as before (safe fallback).

### Worker Slot Leases (`mad claim` / `mad release`)

```bash
# Claim a concurrency slot lease (default agent: agy, default TTL: 60s)
mad claim --agent agy --ttl 60
# Outputs JSON: {"slot": 1, "resource": "agy:slot:1", "claim_id": "...", "fencing_token": 1, "expires_at": "..."}

# Release acquired slot lease when worker completes
mad release --claim-id <CLAIM_ID> --token <FENCING_TOKEN> [--outcome released]
# Outputs JSON: {"released": true}
```

- **In `mads` mode**:
  - `mad claim` acquires the lowest available slot among `1..max_concurrent` (configured in `config/routing.json` under `telemetry.agy_max_concurrent`). If all slots are occupied by active leases, exits `1` (`mad: all agy slots busy (max_concurrent=N)`).
  - `mad release` releases the claimed slot using monotonic fencing tokens to prevent zombie workers from releasing renewed leases. Exits `1` on token mismatch (`LEASE_LOST`) or missing claim.
- **In `files` mode**: Both commands act as deterministic no-ops returning valid JSON (`{"slot": 1, "claim_id": "files-noop", ...}` and `{"released": true}`), ensuring scripts running against `files` mode execute without modification or error.

