# Phase 3: Telemetry & limits - Context

**Gathered:** 2026-10-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Atomic telemetry state persistence (`.agent_telemetry.json`), Claude Pro window message estimation from local JSONL transcripts (`~/.claude/projects/*/*.jsonl`), full `mad check` limit evaluation (Claude message threshold, `agy` concurrency, and 15-minute `agy` rate-limit cooldown), and project-level Claude Code `UserPromptSubmit` hook enforcement (`.claude/settings.json` + `scripts/claude-check-hook.sh`).

</domain>

<decisions>
## Implementation Decisions

### Telemetry schema & atomic writes (`TEL-01`)
- **D-01:** `.agent_telemetry.json` follows the exact spec §7 schema:
  ```json
  {
    "version": 1,
    "updated": "<UTC ISO-8601 seconds Z>",
    "claude": {
      "window_hours": 5,
      "window_message_budget": 45,
      "handoff_ratio": 0.8,
      "messages_in_window": 0,
      "oldest_in_window": null
    },
    "agy": {
      "max_concurrent": 2,
      "running": 0,
      "last_rate_limit": null
    }
  }
  ```
- **D-02:** All writes to `.agent_telemetry.json` use atomic write-and-rename (`tempfile.NamedTemporaryFile` in the same directory + `os.replace`) so an interrupted write never leaves truncated or corrupt JSON.
- **D-03:** Default thresholds live in `config/routing.json` under `"telemetry"` (`window_hours`: `5`, `window_message_budget`: `45`, `handoff_ratio`: `0.8`, `agy_max_concurrent`: `2`, `agy_rate_limit_cooldown_minutes`: `15`).

### Claude transcript counting (`TEL-02`)
- **D-04:** Transcript root defaults to `~/.claude/projects` (scanning `*/*.jsonl`), overridable via `MAD_CLAUDE_PROJECTS_DIR` environment variable or `mad check --transcripts-dir PATH` so tests never read real user transcripts.
- **D-05:** A JSONL line counts toward `messages_in_window` when:
  1. It parses as a JSON object with `"type": "user"`.
  2. `obj.get("isMeta")` is falsy.
  3. If `obj.get("message")` is a dict with a list `"content"`, the list is not composed solely of `{"type": "tool_result", ...}` blocks (so both bare fixture lines `{"type": "user", "timestamp": "..."}` and real human prompt lines count, while tool-result turns are ignored).
  4. `"timestamp"` parses as an ISO-8601 timestamp within `(now - window_hours, now]`.
  Malformed JSON lines or unreadable files are skipped without crashing.
- **D-06:** `oldest_in_window` is the earliest matching prompt timestamp formatted as UTC ISO-8601 seconds (`YYYY-MM-DDTHH:MM:SSZ`), or `null` when `messages_in_window == 0`.

### `mad check` limit evaluation (`TEL-03`)
- **D-07:** `mad check` preserves existing `agy.running` and `agy.last_rate_limit` values from `.agent_telemetry.json` when present (initializing to `0` and `null` if missing or corrupt). `MAD_AGY_RUNNING=<int>` overrides `agy.running`, and `mad check --record-rate-limit` sets `agy.last_rate_limit` to `now` (UTC ISO-8601 `Z`).
- **D-08:** `mad check` updates `.agent_telemetry.json` atomically on every run, then evaluates handoff conditions:
  - `MAD_FORCE_HANDOFF == "1"` (kept from Phase 2 `D-10` for manual/skill override), OR
  - `claude.messages_in_window >= math.ceil(window_message_budget * handoff_ratio)` (`ceil(45 * 0.8) = 36` by default), OR
  - `agy.running >= agy.max_concurrent` (`2` by default), OR
  - `agy.last_rate_limit` is within the last `15` minutes (`(now - last_rate_limit) <= 15 minutes`).
- **D-09:** When any handoff condition holds, `mad check` prints `handoff` and exits `10`; otherwise it prints `ok` and exits `0`.

### Claude Code `UserPromptSubmit` hook (`TEL-04`)
- **D-10:** `.claude/settings.json` defines a `UserPromptSubmit` command hook invoking `scripts/claude-check-hook.sh`.
- **D-11:** `scripts/claude-check-hook.sh` runs `bin/mad check`:
  - On exit `0`, outputs nothing and exits `0`.
  - On exit `10`, outputs valid Claude Code hook JSON (`hookSpecificOutput` with `hookEventName: "UserPromptSubmit"` and `additionalContext` instructing the agent to run `context_orchestrator` / `bin/mad handoff --write ...`, stop, and print `bin/mad handoff`) and exits `0` so Claude Code injects the instruction into the turn context.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design & Requirements
- `docs/superpowers/specs/2026-10-23-mad-design.md` §5, §7 — `mad check` specification, `.agent_telemetry.json` schema, transcript counting, and `.claude/settings.json` hook.
- `.planning/REQUIREMENTS.md` — Requirements `TEL-01`, `TEL-02`, `TEL-03`, `TEL-04`.
- `.planning/ROADMAP.md` — Phase 3 success criteria.
- `AGENTS.md` — Repo invariants, CLI conventions, and verification gates.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mad/store.py` (`find_root`, `_utc_iso`) — Root discovery and UTC ISO-8601 timestamp formatting (`YYYY-MM-DDTHH:MM:SSZ`).
- `mad/route.py` (`load_config`) — Loads `config/routing.json`.
- `mad/cli.py` — Already has `p_check = sub.add_parser("check")` stub from Phase 2.

### Integration Points
- `config/routing.json` — Add `"telemetry"` defaults block.
- `mad/telemetry.py` — New stdlib module implementing transcript scanning, atomic `.agent_telemetry.json` read/write, and `check_limits()`.
- `mad/cli.py` — Wire `mad check [--transcripts-dir PATH] [--record-rate-limit]` to `mad.telemetry`.
- `scripts/claude-check-hook.sh` and `.claude/settings.json` — Project-level Claude Code `UserPromptSubmit` hook.
- `.gitignore` — Ignore runtime `.agent_telemetry.json` and `.opengsd_handoff.md` so checks don't dirty git status.

</code_context>

<specifics>
## Specific Ideas

- `scripts/claude-check-hook.sh` must pass `shellcheck` alongside `bin/mad`, `tests/stub_cli.sh`, and `scripts/install-skills.sh`.
- Unit tests in `tests/test_telemetry.py` test `35` vs `36` messages in a 5h window, out-of-window timestamps, `isMeta` / `tool_result` filtering, `agy` concurrency and 15-minute rate-limit cooldown, and atomic write-and-rename resilience.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-telemetry-limits*
*Context gathered: 2026-10-23*
