# Phase 2: Context Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Selective context retrieval (`mad fetch`, `context_fetcher`), state handoff artifact generation and launch (`mad handoff --write`, `mad handoff`, `context_orchestrator`), task-start limit gating (`route_task`, `mad check` stub), and dual-CLI skill installation (`scripts/install-skills.sh`).

**Architecture:** `mad/context.py` parses OKF frontmatter, scores `.active_context/*.md` files against query keywords within `fetch_budget_bytes`, and regenerates `INDEX.md`. `mad/handoff.py` atomically writes `.opengsd_handoff.md` + appends a `handoff` entry to `.global_dev_log.md`, validates the four spec §6 sections, and builds the `agy -i` argv. `mad/cli.py` wires `fetch`, `handoff`, and the Phase 2 `check` stub. `skills/*/SKILL.md` and `scripts/install-skills.sh` package the shared agent skills.

**Tech Stack:** Bash, Python 3.14 standard library, pytest 9 (tests only), bats, shellcheck.

**Spec:** `docs/superpowers/specs/2026-10-23-mad-design.md` (§3 store, §4.3 subagent switching, §5 CLI, §6 skills). GSD: `.planning/phases/02-context-skills/02-01-PLAN.md`, `.planning/phases/02-context-skills/02-CONTEXT.md` (`D-01`–`D-15`), requirements `CTX-01..05`.

## Global Constraints

- Runtime code imports only the Python standard library.
- No test launches a real `claude` or `agy` or writes to `$HOME`: tests override `MAD_CLAUDE_BIN`, `MAD_AGY_BIN`, `MAD_CLAUDE_SKILLS_DIR`, and `MAD_AGY_SKILLS_DIR`.
- `.global_dev_log.md` remains strictly append-only.
- Exit codes: `0` ok, `1` runtime error, `2` usage error, `10` handoff needed (`mad check`).

---

### Task 1: Context fetcher and indexer (`mad/context.py`)

**Files:**
- Modify: `config/routing.json` (add `"fetch_budget_bytes": 24000`)
- Create: `mad/context.py`
- Test: `tests/test_context.py`

**Interfaces:**
- `parse_frontmatter(text: str) -> tuple[str, list[str], str]`: returns `(title, keywords, updated)`.
- `fetch_context(root: Path, query: Sequence[str], budget_bytes: int = 24000) -> list[Path]`:
  - Splits query arguments on `\W+` into distinct lower-cased tokens (`D-03`).
  - Scores `root / ".active_context" / "*.md"` (excluding `INDEX.md`): `2` points per query token in frontmatter `keywords` (lower-cased), `1` point per query token in frontmatter `title` words (`\W+` split, lower-cased).
  - Sorts positive-score files by `(-score, path.name)` (`D-01`).
  - Iterates in sorted order, skipping any file whose `stat().st_size` exceeds the remaining budget and continuing to check smaller lower-scored files (`D-02`).
- `reindex_context(root: Path, today: date | None = None) -> Path`:
  - Calls `init_store(root, today=today)`, scans `.active_context/*.md` (excluding `INDEX.md`) sorted by filename, and writes `.active_context/INDEX.md` with OKF frontmatter + `# Active context` + `One topic per file. Regenerate this index with mad fetch --reindex.` + bullet list `- .active_context/<name>.md — <title> [kw1, kw2]` (or `(no topics yet)` when empty) (`D-04`).

- [ ] **Step 1: Update `config/routing.json` and write failing tests in `tests/test_context.py`**
- [ ] **Step 2: Run `pytest tests/test_context.py -q` (expect `ModuleNotFoundError: No module named 'mad.context'`)**
- [ ] **Step 3: Implement `mad/context.py`**
- [ ] **Step 4: Run `pytest tests/test_context.py -q` (expect all pass)**
- [ ] **Step 5: Commit `feat(02-01): context fetcher and INDEX.md reindexer`**

---

### Task 2: Handoff writer, validator, and launcher (`mad/handoff.py`)

**Files:**
- Create: `mad/handoff.py`
- Test: `tests/test_handoff.py`

**Interfaces:**
- `REQUIRED_SECTIONS = ("## Unresolved problem", "## Next exact steps", "## Context files to load", "## Verify with")`
- `write_handoff(root: Path, agent: str, problem: str, steps: Sequence[str], context_files: Sequence[str] = (), verify_cmds: Sequence[str] = (), handoff_path: Path | None = None, today: date | None = None, now: datetime | None = None) -> Path` (`D-09`).
- `validate_handoff(path: Path) -> str`: raises `ValueError(f"handoff file not found: {path}")` when missing/empty (`D-06`), or `ValueError(f"malformed handoff file: {path}")` when OKF frontmatter or any of `REQUIRED_SECTIONS` is missing (`D-07`).
- `build_handoff_command(content: str, model: str, env: Mapping[str, str]) -> list[str]`: returns `[env.get("MAD_AGY_BIN", "agy"), "--model", model, "-i", content]` (`D-05`, `D-08`).

- [ ] **Step 1: Write failing tests in `tests/test_handoff.py`**
- [ ] **Step 2: Run `pytest tests/test_handoff.py -q` (expect `ModuleNotFoundError: No module named 'mad.handoff'`)**
- [ ] **Step 3: Implement `mad/handoff.py`**
- [ ] **Step 4: Run `pytest tests/test_handoff.py -q` (expect all pass)**
- [ ] **Step 5: Commit `feat(02-01): handoff writer, validator, and launcher`**

---

### Task 3: CLI wiring for `fetch`, `handoff`, and `check` (`mad/cli.py`)

**Files:**
- Modify: `mad/cli.py`
- Test: `tests/cli.bats`

**Interfaces:**
- `mad fetch [--reindex] [--budget N] [KEYWORD ...]`:
  - `--reindex` regenerates `.active_context/INDEX.md` and prints `.active_context/INDEX.md`.
  - `KEYWORD ...` prints matching paths relative to `root`, one per line, within `--budget` (default `cfg.get("fetch_budget_bytes", 24000)`).
  - Neither `--reindex` nor `KEYWORD` is a usage error (exit `2`).
- `mad handoff`:
  - `--write` mode: requires `--agent`, `--problem`, and at least one `--step` (optional `--context`, `--verify`, `--file`); writes `.opengsd_handoff.md` and appends the `handoff` log entry.
  - Launch mode (default): optional `--model` (defaults to `cfg["models"]["agy"]["heavy"]`), `--file` (defaults to `root / ".opengsd_handoff.md"`), `--dry-run`; validates handoff file, prints `shlex.join(cmd)` on `--dry-run`, or `exec_command(cmd)`.
- `mad check`:
  - Phase 2 stub (`D-10`): prints `handoff` and exits `10` when `MAD_FORCE_HANDOFF=1`, otherwise prints `ok` and exits `0`.

- [ ] **Step 1: Add failing bats tests in `tests/cli.bats` for `fetch`, `handoff --write`, `handoff`, and `check`**
- [ ] **Step 2: Run `bats tests/cli.bats` (expect new tests to fail)**
- [ ] **Step 3: Update `mad/cli.py`**
- [ ] **Step 4: Run `pytest -q && bats tests/cli.bats` (expect all pass)**
- [ ] **Step 5: Commit `feat(02-01): add fetch, handoff, and check CLI subcommands`**

---

### Task 4: Shared skills and `scripts/install-skills.sh`

**Files:**
- Create: `skills/context_orchestrator/SKILL.md`
- Create: `skills/context_fetcher/SKILL.md`
- Create: `skills/route_task/SKILL.md`
- Create: `scripts/install-skills.sh` (mode `0755`)
- Modify: `tests/cli.bats`

**Interfaces:**
- `skills/context_orchestrator/SKILL.md`: frontmatter (`name: context_orchestrator`, `description: ...`) + delta inspection + `bin/mad handoff --write` invocation + supersedes notice (`CTX-01`, `D-09`).
- `skills/context_fetcher/SKILL.md`: frontmatter (`name: context_fetcher`, `description: ...`) + `bin/mad fetch` & `bin/mad fetch --reindex` workflow (`CTX-02`).
- `skills/route_task/SKILL.md`: frontmatter (`name: route_task`, `description: ...`) + pre-task `bin/mad check` gate + in-session subagent model-tier table (`CTX-03`, `D-11`).
- `scripts/install-skills.sh`: symlinks `skills/*/SKILL.md` directories into `${MAD_CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}` and `${MAD_AGY_SKILLS_DIR:-$HOME/.gemini/config/skills}` via `ln -sfn`; supports `--dry-run`; refuses to overwrite real non-symlink directories (`CTX-05`, `D-12`–`D-15`).

- [ ] **Step 1: Add failing bats tests in `tests/cli.bats` for `install-skills.sh`**
- [ ] **Step 2: Run `bats tests/cli.bats` (expect installer tests to fail)**
- [ ] **Step 3: Create the three `SKILL.md` files and `scripts/install-skills.sh` (`chmod 755`)**
- [ ] **Step 4: Run `pytest -q && bats tests/cli.bats && shellcheck bin/mad tests/stub_cli.sh scripts/install-skills.sh`**
- [ ] **Step 5: Commit `feat(02-01): add shared skills and install-skills.sh`**

---

### Task 5: Close Phase 2 (GSD bookkeeping)

- [ ] Write `.planning/phases/02-context-skills/02-01-SUMMARY.md` and `.planning/phases/02-context-skills/02-VERIFICATION.md`.
- [ ] Mark `CTX-01..05` complete in `.planning/REQUIREMENTS.md`, check Phase 2 in `.planning/ROADMAP.md`, and advance `.planning/STATE.md` and `.planning/PROJECT.md`.
- [ ] Log Phase 2 completion via `bin/mad log --kind decision --agent mad "Phase 2 context skills complete"`.
- [ ] Commit `docs: close phase 2 (context skills)`. **Stop here.** Phase 3 starts only on the user's go-ahead.
