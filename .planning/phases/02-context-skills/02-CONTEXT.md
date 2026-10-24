# Phase 2: Context skills - Context

**Gathered:** 2026-10-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Selective context retrieval (`mad fetch` and `context_fetcher`), state handoff artifact generation (`mad handoff --write` and `context_orchestrator` → `.opengsd_handoff.md`), pre-task limit gating (`route_task` with a Phase 2 `mad check` stub), one-command handoff launch (`mad handoff`), and dual-CLI skill installation (`scripts/install-skills.sh`). Real usage telemetry and the Claude Code hook belong to Phase 3.

</domain>

<decisions>
## Implementation Decisions

### `mad fetch` scoring & budget
- **D-01:** Tie-breaking order is `(-score, filename)` — highest score first, then alphabetical by filename (`snake_case.md`). `.active_context/INDEX.md` is excluded from scoring.
- **D-02:** Budget enforcement (`fetch_budget_bytes`, default `24000`, configurable via `--budget` or `config/routing.json`) skips any file whose byte size exceeds the remaining budget and continues checking lower-scored files that still fit. No file larger than the budget is ever emitted.
- **D-03:** Query matching uses case-insensitive exact token matching: split query arguments and frontmatter `title` on non-word characters (`\W+`), and compare distinct lower-cased query tokens against lower-cased frontmatter `keywords` (`2` points per hit) and `title` tokens (`1` point per hit).
- **D-04:** `mad fetch --reindex` regenerates `.active_context/INDEX.md` with the standard OKF frontmatter (`title: Active context index`, `keywords: [index]`, `updated: <YYYY-MM-DD>`), `# Active context`, the explanatory line, and a bullet list sorted by filename: `- .active_context/<name>.md — <title> [kw1, kw2]` (or `(no topics yet)` if no topic files exist).

### `mad handoff` & CLI options
- **D-05:** `mad handoff` (launch mode) accepts optional `--model M` (default: `config["models"]["agy"]["heavy"]` = `gemini-4-argon-high`), `--dry-run` (prints shell-quoted argv and launches nothing), and `--file PATH` (default: `<root>/.opengsd_handoff.md`).
- **D-06:** When the handoff file is missing or empty, `mad handoff` exits `1` and prints `mad: handoff file not found: <path>` to stderr.
- **D-07:** Before execing `agy`, `mad handoff` validates that the handoff file has OKF frontmatter and all four required spec §6 headings (`## Unresolved problem`, `## Next exact steps`, `## Context files to load`, `## Verify with`), exiting `1` with an error message on stderr if malformed.
- **D-08:** `mad handoff` launch mode does not append a duplicate log entry — `context_orchestrator` (`mad handoff --write`) already appends the `handoff` log entry when producing `.opengsd_handoff.md`.

### `context_orchestrator` & `route_task`
- **D-09:** Provide `mad handoff --write --agent A --problem P --step S... [--context C...] [--verify V...] [--file PATH]` to atomically write a valid OKF `.opengsd_handoff.md` with the four spec §6 sections and append a `handoff` entry to `.global_dev_log.md`. `skills/context_orchestrator/SKILL.md` instructs the agent to gather the git/log delta and invoke this command.
- **D-10:** Add a Phase 2 stub subcommand `mad check` that prints `ok` (exit `0`) by default, or prints `handoff` (exit `10`) when `MAD_FORCE_HANDOFF=1` is set in the environment, enabling deterministic end-to-end testing of `route_task` before Phase 3 replaces the stub with real transcript/process telemetry.
- **D-11:** Include the in-session subagent model-tier policy (Claude `Agent` tool: `haiku`/`sonnet`/`opus`; `agy -p`: `gemini-3.8-flash-medium`/`gemini-4-argon-high`, per spec §4.2/§4.3) inside `skills/route_task/SKILL.md` alongside the pre-task `mad check` gate.

### `install-skills.sh` target paths
- **D-12:** `scripts/install-skills.sh` defaults to `~/.claude/skills` and `~/.gemini/config/skills`, overridable via `MAD_CLAUDE_SKILLS_DIR` and `MAD_AGY_SKILLS_DIR` environment variables so tests can verify real symlinking inside `$BATS_TEST_TMPDIR` without touching `$HOME`.
- **D-13:** `scripts/install-skills.sh` discovers only `skills/<name>` directories that contain a `SKILL.md` file (sorted alphabetically: `context_fetcher`, `context_orchestrator`, `route_task`).
- **D-14:** Missing target parent directories are created (`mkdir -p`), existing symlinks are replaced (`ln -sfn`), and if a destination path is an existing real (non-symlink) directory, the script refuses to overwrite it and exits `1`.
- **D-15:** `scripts/install-skills.sh --dry-run` prints `ln -sfn <abs_source> <abs_dest>` (one per line) and modifies nothing on disk.

### Claude's Discretion
- Module layout for the new Phase 2 logic (e.g., `mad/context.py` and `mad/handoff.py` wired into `mad/cli.py`).
- Exact OKF frontmatter keywords on `.opengsd_handoff.md` (`title: Session handoff`, `keywords: [handoff, state]`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design & Requirements
- `docs/superpowers/specs/2026-10-23-mad-design.md` §3, §4.3, §5, §6 — State store OKF format, subagent model switching, CLI subcommands, and Phase 2 skill specifications (`context_orchestrator`, `context_fetcher`, `route_task`, `install-skills.sh`).
- `.planning/REQUIREMENTS.md` — Requirements `CTX-01`, `CTX-02`, `CTX-03`, `CTX-04`, `CTX-05`.
- `.planning/ROADMAP.md` — Phase 2 success criteria.
- `AGENTS.md` — Repo invariants, CLI conventions, and verification gates.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mad/store.py` (`find_root`, `init_store`, `append_log`, `VALID_KINDS`, `VALID_AGENTS`) — Already supports `kind="handoff"` and creates `.active_context/INDEX.md` and `.global_dev_log.md`.
- `mad/route.py` (`load_config`) — Loads `config/routing.json` (can supply default `fetch_budget_bytes` and `models.agy.heavy`).
- `mad/launch.py` (`exec_command`) — Wraps `os.execvp` for launching `agy` from `mad handoff`.

### Established Patterns
- Pure functions in domain modules (`mad/route.py`, `mad/store.py`, `mad/launch.py`), thin argparse dispatch in `mad/cli.py`.
- All external binaries injected via environment variables (`MAD_CLAUDE_BIN`, `MAD_AGY_BIN`) and tested with `tests/stub_cli.sh` in `tests/cli.bats`.

### Integration Points
- `mad/cli.py` `_build_parser()` and `main()` — Add `fetch`, `handoff`, and `check` subparsers.
- `config/routing.json` — Add `"fetch_budget_bytes": 24000`.

</code_context>

<specifics>
## Specific Ideas

- `mad handoff --write` gives agents and tests a deterministic way to generate `.opengsd_handoff.md` and log the `handoff` event in one call.
- `scripts/install-skills.sh` must pass `shellcheck`.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-context-skills*
*Context gathered: 2026-10-23*
