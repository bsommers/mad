# Phase 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `bin/mad` CLI that routes a prompt to `claude` or `agy` with the right model, launches it, and records each launch in an append-only OKF Markdown log.

**Architecture:** The bash entry point `bin/mad` execs `python3 -m mad`. A pure `route.classify` makes the decision from `config/routing.json`. `store.py` owns `.global_dev_log.md` and `.active_context/`. `launch.py` builds the argv and execs it. `cli.py` is the argparse front end.

**Tech Stack:** Bash, Python 3.14 standard library, pytest 9 (tests only), bats, shellcheck.

**Spec:** `docs/superpowers/specs/2026-10-23-mad-design.md` (§3 store, §4 routing, §5 CLI, §9 testing). GSD: `.planning/phases/01-foundation/01-01-PLAN.md`, requirements STORE-01, STORE-02, ROUTE-01..03.

## Global Constraints

- Runtime code imports only the Python standard library.
- No test launches a real `claude` or `agy`: binaries come from `MAD_CLAUDE_BIN` / `MAD_AGY_BIN`, which tests point at stubs.
- `.global_dev_log.md` is opened only in append mode once it exists, and earlier bytes never change.
- Log heading format: `## <YYYY-MM-DDTHH:MM:SSZ> · <kind> · <agent>`. Kinds: `task transition decision handoff note`. Agents: `claude agy human mad`.
- Model ids: claude `haiku|sonnet|opus`; agy `gemini-3.8-flash-medium` (light) and `gemini-4-argon-high` (heavy).
- `agy_file_threshold` = 5 (strictly more than 5 files is one agy signal). Ties go to claude.
- Exit codes: 0 ok, 1 runtime error, 2 usage error.

## Review Focus

1. Keyword inside a longer word (`redesign`, `unsafe` containing `uns`) must **not** match → test in Task 1.
2. A prompt with newlines or ` · ` must not break the log's one-line values → test in Task 2.
3. `mad run` in a project whose log doesn't exist yet must create it with the header first, then append → test in Task 2.
4. A prompt that starts with `-` (for example `"-v flag is broken, debug it"`) must be accepted after `--` → test in Task 4.
5. `bin/mad` called through a symlink from another directory (installed on PATH) must still find its package → test in Task 4.

---

### Task 1: Routing config and `classify`

**Files:**
- Create: `pyproject.toml` (only `[tool.pytest.ini_options]` with `pythonpath = ["."]`, `testpaths = ["tests"]`)
- Create: `config/routing.json`
- Create: `mad/__init__.py` (empty), `mad/route.py`
- Test: `tests/test_route.py`

**Interfaces:**
- Produces:
  - `load_config(path: Path | None = None) -> dict`. With no path, it uses `$MAD_CONFIG` if set, otherwise `Path(__file__).resolve().parent.parent / "config" / "routing.json"`.
  - `@dataclass(frozen=True) class Decision: agent: str; model: str; reasons: list[str]; scores: dict[str, int]`, with `to_json() -> str` (`json.dumps(asdict(self))`, keys in field order).
  - `classify(prompt: str, files: Sequence[str], config: dict, agent: str | None = None, model: str | None = None) -> Decision`

- [ ] **Step 1: Write `config/routing.json`** with exactly the keys `claude_keywords`, `agy_keywords`, `opus_keywords`, `haiku_keywords`, `agy_file_threshold` (5), `models` (`{"claude": {"light": "haiku", "default": "sonnet", "deep": "opus"}, "agy": {"light": "gemini-3.8-flash-medium", "heavy": "gemini-4-argon-high"}}`). Copy the keyword lists from spec §4.1/§4.2 verbatim, in that order.

- [ ] **Step 2: Write the failing table test**

```python
CASES = [
    # prompt, files, agent_override, model_override, expected (agent, model, reasons, scores)
    ("debug the mqtt reconnect", ["a.py"], None, None, ("claude", "sonnet", ["kw:debug"], {"claude": 1, "agy": 0})),
    ("design the UNS tree", [], None, None, ("agy", "gemini-4-argon-high", ["kw:design", "kw:uns"], {"claude": 0, "agy": 2})),
    ("update the parser", list("abcdef"), None, None, ("agy", "gemini-4-argon-high", ["files:6>5"], {"claude": 0, "agy": 1})),
    ("update the parser", list("abcde"), None, None, ("claude", "sonnet", ["default"], {"claude": 0, "agy": 0})),
    ("debug it", list("abcdef"), None, None, ("claude", "sonnet", ["kw:debug", "files:6>5"], {"claude": 1, "agy": 1})),
    ("fix the race condition in the pool", [], None, None, ("claude", "opus", ["kw:race condition"], {"claude": 0, "agy": 0})),
    ("write a regex for dates", [], None, None, ("claude", "haiku", ["kw:regex"], {"claude": 0, "agy": 0})),
    ("write tests for the regex", [], None, None, ("claude", "sonnet", ["kw:write tests", "kw:regex"], {"claude": 1, "agy": 0})),
    ("list the files", [], "agy", None, ("agy", "gemini-3.8-flash-medium", ["override:agent"], {"claude": 0, "agy": 0})),
    ("debug x", [], None, "opus", ("claude", "opus", ["kw:debug", "override:model"], {"claude": 1, "agy": 0})),
    ("redesign the unsafe block", [], None, None, ("claude", "sonnet", ["default"], {"claude": 0, "agy": 0})),
]

@pytest.mark.parametrize("prompt,files,agent,model,expected", CASES)
def test_classify(prompt, files, agent, model, expected):
    d = classify(prompt, files, load_config(), agent=agent, model=model)
    assert (d.agent, d.model, d.reasons, d.scores) == expected

def test_to_json_roundtrip():
    d = classify("debug x", [], load_config())
    assert json.loads(d.to_json()) == {"agent": "claude", "model": "sonnet", "reasons": ["kw:debug"], "scores": {"claude": 1, "agy": 0}}
```

- [ ] **Step 3: Run it to make sure it fails**

Run: `pytest tests/test_route.py -q`. Expected: it fails with `ModuleNotFoundError: mad.route`.

- [ ] **Step 4: Implement `route.py`**

Matching: `re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", prompt.lower())`. Reasons are recorded in this order:
claude keyword hits (config order), agy keyword hits (config order), `files:N>T`, opus/haiku keyword hits that are not already listed, `override:agent`, `override:model`. If none, the list is `["default"]`. Scores count only `claude_keywords` and `agy_keywords` (+1 for files). The model rules follow spec §4.2 exactly. The opus and haiku hits are recorded as `kw:<phrase>` even though they don't score.

- [ ] **Step 5: Run the tests and make sure they pass**

Run: `pytest tests/test_route.py -q`. Expected: `12 passed`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml config/routing.json mad/__init__.py mad/route.py tests/test_route.py
git commit -m "feat: routing config and classify"
```

### Task 2: OKF store — `init_store`, `append_log`, `find_root`

**Files:**
- Create: `mad/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Produces:
  - `find_root(start: Path) -> Path`: the nearest ancestor (including `start`) that contains `.global_dev_log.md` or `.git`, otherwise `start`.
  - `init_store(root: Path, today: date | None = None) -> list[Path]`: creates any missing `root/.active_context/`, `root/.active_context/INDEX.md` and `root/.global_dev_log.md`, and returns the paths it created (an empty list when everything already exists).
  - `append_log(root: Path, kind: str, agent: str, fields: dict[str, str], now: datetime | None = None) -> str`: raises `ValueError` for an unknown kind or agent, calls `init_store(root)` first, appends the entry and returns the text it appended.
- Exact text (spec §3). Log header, with `{date}` as an ISO date:

```
---
title: Global dev log
keywords: [log, history, decisions, handoffs]
updated: {date}
---

# Global dev log

Append-only. Newest entries at the bottom.
```

  INDEX.md is the same frontmatter shape with `title: Active context index`, `keywords: [index]`, then `# Active context` and the line
  `One topic per file. Regenerate this index with mad fetch --reindex.`
  Each appended entry is `"\n## {ts} · {kind} · {agent}\n" + "".join(f"- {k}: {v}\n")`, where each `v` has every run of `\r` and `\n` replaced by a single space.

- [ ] **Step 1: Write the failing tests**

```python
def test_init_creates_then_is_idempotent(tmp_path):
    created = init_store(tmp_path, today=date(2026, 10, 23))
    assert sorted(p.name for p in created) == [".active_context", ".global_dev_log.md", "INDEX.md"]
    assert "updated: 2026-10-23" in (tmp_path / ".global_dev_log.md").read_text()
    assert init_store(tmp_path) == []

def test_init_never_overwrites(tmp_path):
    (tmp_path / ".global_dev_log.md").write_bytes(b"mine\n")
    init_store(tmp_path)
    assert (tmp_path / ".global_dev_log.md").read_bytes() == b"mine\n"

def test_append_preserves_prior_bytes(tmp_path):
    t = datetime(2026, 10, 23, 14, 2, 11, tzinfo=UTC)
    append_log(tmp_path, "task", "claude", {"task": "one"}, now=t)
    before = (tmp_path / ".global_dev_log.md").read_bytes()
    entry = append_log(tmp_path, "decision", "human", {"task": "two"}, now=t)
    after = (tmp_path / ".global_dev_log.md").read_bytes()
    assert after.startswith(before) and after[len(before):].decode() == entry
    assert entry == "\n## 2026-10-23T14:02:11Z · decision · human\n- task: two\n"

def test_append_creates_log_with_header_first(tmp_path):        # Review Focus 3
    append_log(tmp_path, "note", "mad", {"task": "x"})
    assert (tmp_path / ".global_dev_log.md").read_text().startswith("---\ntitle: Global dev log\n")

def test_multiline_values_flattened(tmp_path):                  # Review Focus 2
    e = append_log(tmp_path, "task", "agy", {"task": "a\nb\r\n\nc"})
    assert "- task: a b c\n" in e and e.count("\n") == 3

def test_unknown_kind_or_agent_rejected(tmp_path):
    with pytest.raises(ValueError): append_log(tmp_path, "oops", "claude", {})
    with pytest.raises(ValueError): append_log(tmp_path, "task", "gpt", {})

def test_find_root(tmp_path):
    (tmp_path / ".git").mkdir(); sub = tmp_path / "a" / "b"; sub.mkdir(parents=True)
    assert find_root(sub) == tmp_path
```

- [ ] **Step 2: Run the tests and make sure they fail.** Run: `pytest tests/test_store.py -q`. Expected: `ModuleNotFoundError`.
- [ ] **Step 3: Implement `store.py`** to the interfaces above. Use `open(path, "a", encoding="utf-8")` for appends, and `datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")` when `now` is None.
- [ ] **Step 4: Run the tests and make sure they pass.** Run: `pytest tests/test_store.py -q`. Expected: `7 passed`.
- [ ] **Step 5: Commit**

```bash
git add mad/store.py tests/test_store.py
git commit -m "feat: append-only OKF dev log and active context store"
```

### Task 3: Command builder

**Files:**
- Create: `mad/launch.py`
- Test: `tests/test_launch.py`

**Interfaces:**
- Consumes: `Decision` (Task 1).
- Produces:
  - `build_command(decision: Decision, prompt: str, files: Sequence[str], env: Mapping[str, str]) -> list[str]`. For claude: `[env.get("MAD_CLAUDE_BIN", "claude"), "--model", model, full_prompt]`. For agy: `[env.get("MAD_AGY_BIN", "agy"), "--model", model, "-i", full_prompt]`. `full_prompt` is `prompt` when `files` is empty, otherwise `prompt + "\n\nFiles: " + " ".join(files)`.
  - `exec_command(argv: list[str]) -> NoReturn`: `os.execvp(argv[0], argv)`.

- [ ] **Step 1: Write the failing tests:** `test_claude_argv` (`["claude", "--model", "sonnet", "debug x"]`), `test_agy_argv_uses_dash_i` (`["agy", "--model", "gemini-4-argon-high", "-i", "design y\n\nFiles: a.py b.py"]`), and `test_bin_override` (`env={"MAD_AGY_BIN": "/tmp/stub"}` gives argv[0] `/tmp/stub`).
- [ ] **Step 2: Run them and make sure they fail.** Run: `pytest tests/test_launch.py -q`.
- [ ] **Step 3: Implement `launch.py`.**
- [ ] **Step 4: Run them and make sure they pass.** Run: `pytest tests/test_launch.py -q`. Expected: `3 passed`.
- [ ] **Step 5: Commit:** `git add mad/launch.py tests/test_launch.py && git commit -m "feat: build claude/agy launch commands"`

### Task 4: CLI front end and `bin/mad`

**Files:**
- Create: `mad/cli.py`, `mad/__main__.py` (`raise SystemExit(main())`), `bin/mad` (mode 755)
- Create: `tests/stub_cli.sh` (writes each argument on its own line to `$STUB_OUT`)
- Test: `tests/cli.bats`

**Interfaces:**
- Consumes: `load_config`, `classify`, `Decision.to_json` (Task 1); `find_root`, `init_store`, `append_log` (Task 2); `build_command`, `exec_command` (Task 3).
- Produces: `main(argv: list[str] | None = None) -> int` with subcommands:
  - `init`: prints each created path relative to the root, one per line, or `nothing to do`.
  - `route [--agent {claude,agy}] [--model M] PROMPT [FILE...]`: prints `Decision.to_json()`.
  - `run [--agent] [--model] [--dry-run] PROMPT [FILE...]`: with `--dry-run`, prints `shlex.join(argv)` and writes nothing. Otherwise it calls `append_log(root, "transition", agent, {"model": m, "task": prompt, "reasons": ",".join(reasons)})`, then `exec_command`.
  - `log --kind K --agent A [--field k=v]... MESSAGE`: appends `{"task": MESSAGE, **fields}`. A malformed `--field` is a usage error (exit 2).
  - The root is always `find_root(Path.cwd())`. argparse errors exit 2, and a `ValueError` from the store prints `mad: <msg>` to stderr and returns 1.
- `bin/mad`: `#!/usr/bin/env bash`, `set -euo pipefail`, resolves its real directory with `readlink -f "${BASH_SOURCE[0]}"`, then `PYTHONPATH="$dir/..${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m mad "$@"`.

- [ ] **Step 1: Write the failing bats tests.** Every test runs in `$BATS_TEST_TMPDIR`, with `MAD_CLAUDE_BIN`/`MAD_AGY_BIN` set to `tests/stub_cli.sh` and `STUB_OUT=$BATS_TEST_TMPDIR/argv`:
  - `route prints claude/sonnet for debug`: the output, parsed with `python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["agent"],d["model"])'`, is `claude sonnet`
  - `run --dry-run prints argv and writes nothing`: the output is `<stub path> --model gemini-4-argon-high -i 'design the uns tree'`, and `.global_dev_log.md` doesn't exist
  - `run execs stub and logs transition`: the `$STUB_OUT` lines are `--model`, `sonnet`, `debug x`, and the log contains `· transition · claude` and `- reasons: kw:debug`
  - `init twice`: the second run prints `nothing to do`
  - `prompt starting with dash after --` (Review Focus 4): `mad route -- "-v flag is broken, debug it"` exits 0 with agent `claude`
  - `works through a symlink from another dir` (Review Focus 5): `ln -s "$REPO/bin/mad" "$BATS_TEST_TMPDIR/m"`, then from `/tmp`, `"$BATS_TEST_TMPDIR/m" route "x"` exits 0
  - `no args is a usage error`: the status is 2
  - `log with bad --field`: `mad log --kind note --agent human --field nokv msg` exits with status 2
- [ ] **Step 2: Run them and make sure they fail.** Run: `bats tests/cli.bats`. Expected: every test fails (`bin/mad` is missing).
- [ ] **Step 3: Implement `cli.py`, `__main__.py`, `bin/mad` and `tests/stub_cli.sh`.**
- [ ] **Step 4: Run the full gate.** Run: `pytest -q && bats tests/cli.bats && shellcheck bin/mad tests/stub_cli.sh`. Expected: pytest `22 passed`, bats `8 tests, 0 failures`, shellcheck silent.
- [ ] **Step 5: Dogfood.** Run `bin/mad init` in the repo root, then `bin/mad log --kind decision --agent human "Phase 1 foundation complete"`. Check that `.global_dev_log.md` has the header and one entry.
- [ ] **Step 6: Commit**

```bash
git add mad/cli.py mad/__main__.py bin/mad tests/stub_cli.sh tests/cli.bats .global_dev_log.md .active_context/INDEX.md
git commit -m "feat: mad CLI (init, route, run, log)"
```

### Task 5: Close the phase (GSD bookkeeping)

- [ ] Write `.planning/phases/01-foundation/01-01-SUMMARY.md` (from `summary-standard.md` in the gsd-core templates): what was built, the test counts from Task 4 Step 4, and any deviations.
- [ ] Mark STORE-01, STORE-02 and ROUTE-01..03 Complete in `.planning/REQUIREMENTS.md`, check Phase 1 in `.planning/ROADMAP.md`, and set STATE.md to Phase 2, "Not planned", 33%.
- [ ] Run `node ~/.gemini/config/plugins/gsd-core/gsd-core/bin/gsd-tools.cjs init onboard --raw`. Expected: `"next_action":{"kind":"ready"` (or the equivalent ready state).
- [ ] Commit: `git commit -am "docs: close phase 1 (foundation)"`. **Stop here.** Phase 2 starts only on the user's go-ahead.
