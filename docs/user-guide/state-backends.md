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
