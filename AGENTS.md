# AGENTS.md — mad

Canonical briefing for every agent CLI working here (Claude Code, Antigravity `agy`, opencode, Codex).
`CLAUDE.md` and `GEMINI.md` point here. Change rules in this file, not in the pointers.

## What this is

mad (Multi-Agent Intelligent Orchestration & Routing System) is a local layer that sends each
development task to the right subscription CLI (`claude` for Claude Code Pro, `agy` for Google AI Ultra)
and the right model inside it. It shares state between the two CLIs as plain Markdown files.

- **In scope:** a router CLI (`bin/mad`), the Markdown state store (`.global_dev_log.md`, `.active_context/`),
  three skills (`context_orchestrator`, `context_fetcher`, `route_task`), and limit telemetry (`.agent_telemetry.json`).
- **Out of scope:** API keys or direct API calls (subscriptions only), SQLite or Redis, and any GUI.

Source of intent: `multi-agent-intelligent-orchestration-routing-specification.md` (the original brief).
The design of record is `docs/superpowers/specs/2026-10-23-mad-design.md`. Where the two differ, the design wins.

## Commands

```bash
pytest -q                          # all Python tests (stdlib-only code, pytest for tests)
pytest tests/test_route.py -q      # one file
pytest tests/test_route.py::test_debug_goes_to_claude -q   # one test
bats tests/cli.bats                # bash entry-point tests
shellcheck bin/mad scripts/*.sh    # lint bash
bin/mad route "debug the mqtt reconnect" src/a.py    # print the routing decision as JSON, launch nothing
bin/mad run --dry-run "design the UNS tree"          # print the command it would exec
bin/mad init                       # create .active_context/ and .global_dev_log.md (idempotent)
bin/mad fetch docker               # score .active_context/*.md by keyword/title within byte budget
bin/mad handoff --write --agent claude --problem "..." --step "..."   # write .opengsd_handoff.md + log
bin/mad handoff                    # launch agy with .opengsd_handoff.md via -i
bin/mad check                      # update .agent_telemetry.json and exit 0 (ok) or 10 (handoff)
```

No test may launch a real `claude` or `agy`. Tests set `MAD_CLAUDE_BIN` / `MAD_AGY_BIN` to stub scripts.

## Architecture map

```
bin/mad            bash entry point: parses the subcommand and calls python3 -m mad
mad/               Python package, stdlib only
  route.py            classify(prompt, files) -> Decision(agent, model, reasons)  (pure; no I/O)
  store.py            init_store(), append_log()  (.global_dev_log.md, .active_context/)
  launch.py           build_command(decision, prompt) -> argv; exec or dry-run
  context.py          fetch_context(), reindex_context()  (.active_context/ scoring & INDEX.md)
  handoff.py          write_handoff(), validate_handoff(), build_handoff_command()  (.opengsd_handoff.md)
  telemetry.py        count_claude_messages(), write_telemetry_atomic(), check_limits()  (.agent_telemetry.json)
  cli.py              argparse front end for init / route / run / log / fetch / handoff / check
config/routing.json   keywords, file-count threshold, model ids, fetch budget, telemetry thresholds
skills/<name>/SKILL.md  Phase 2 skills (context_orchestrator, context_fetcher, route_task)
scripts/              install-skills.sh, claude-check-hook.sh
.claude/settings.json project UserPromptSubmit hook invoking scripts/claude-check-hook.sh
tests/                pytest (Python) + cli.bats (bash)
.planning/            OpenGSD artifacts (PROJECT, REQUIREMENTS, ROADMAP, STATE, phases/)
docs/superpowers/     superpowers specs/ and step-level plans/
```

New routing rules go in `config/routing.json`. New subcommands go in `cli.py`, with the logic in its own module.

## Invariants

- `.global_dev_log.md` is **append-only**. Code never rewrites or truncates it, and agents never edit earlier entries.
- Every state file is OKF Markdown: YAML frontmatter (`title`, `keywords`, `updated`), then a Markdown body. See the design spec, section 3.
- `mad/` uses the Python standard library only. pytest is a test dependency, not a runtime one.
- `route.classify` is pure and deterministic: the same prompt and files always give the same Decision.
- Model ids come from `config/routing.json`. Check `agy models` and `claude --help` before changing them.
- Subscriptions only: never add code that reads `ANTHROPIC_API_KEY`/`GEMINI_API_KEY` or calls an HTTP API.

## Pitfalls

- `agy` has **no `--file` flag** (the original brief says `agy --file`). Hand off with `agy -i "$(cat .opengsd_handoff.md)"`, or with `mad handoff` once it exists.
- The brief names Gemini 1.5 Flash/Pro. Those ids are obsolete. Current agy ids look like `gemini-3.8-flash-medium` and `gemini-4-argon-high` (from `agy models`).
- Claude Pro usage isn't exposed by any command. Phase 3 estimates it by counting user messages in local session transcripts, so treat it as an estimate.
- Not every model id in the routing table is accepted by every CLI. `claude --model` takes `haiku|sonnet|opus`, and `agy --model` takes the full ids.

## Process: OpenGSD + superpowers (controlled mode)

- Planning state lives in `.planning/`. Read `.planning/STATE.md` first in every session.
- Each phase: GSD phase context (`.planning/phases/NN-*/NN-CONTEXT.md`), then a superpowers step plan in
  `docs/superpowers/plans/`, then a GSD `NN-01-PLAN.md` that points to it. Execute with TDD
  (superpowers:test-driven-development), then write `NN-01-SUMMARY.md` and update STATE/ROADMAP/REQUIREMENTS.
- `config.json` mode is `interactive` and `auto_advance` is false. **Don't start the next phase without the user's go-ahead.**
- GSD Core is installed only for Gemini/agy (artifacts-only setup). Validate `.planning/` with:
  `node ~/.gemini/config/plugins/gsd-core/gsd-core/bin/gsd-tools.cjs init onboard --raw` (it should report `ready`).
- Log every task start/finish, agent switch, and architectural decision to `.global_dev_log.md` (via `bin/mad log` once it exists).

## Verification before commit

```bash
pytest -q && bats tests/cli.bats && shellcheck bin/mad
```

Report the real output. If a gate is skipped, say so.

## Style

- Conventional commit subjects (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- Subagents reply with status, changed paths, verify output and blockers. No narration.

## Living vs historical docs

Living: this file, the design spec, `.planning/{PROJECT,REQUIREMENTS,ROADMAP,STATE}.md`.
Historical: the original brief, phase SUMMARY files, and executed plans in `docs/superpowers/plans/`.
