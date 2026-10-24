# Phase 2: Context skills - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-23
**Phase:** 02-context-skills
**Areas discussed:** mad fetch scoring & budget, mad handoff & CLI options, context_orchestrator & route_task, install-skills.sh target paths

---

## mad fetch scoring & budget

| Question | Selected Option |
|----------|-----------------|
| Tie-breaking order | `(-score, filename)` — Highest score first, then alphabetical by filename |
| Budget enforcement | Skip files that exceed remaining budget and keep checking lower-scored files that still fit; hard cap at budget |
| Token matching | Case-insensitive exact token match (`\W+` split, 2 pts per distinct keyword hit, 1 pt per distinct title word hit) |
| `--reindex` format | OKF header + bullet list sorted by filename: `- <path> — <title> [kw1, kw2]` (or `(no topics yet)`) |

---

## mad handoff & CLI options

| Question | Selected Option |
|----------|-----------------|
| Flags on `mad handoff` | Support optional `--model M` (default `gemini-4-argon-high`) and `--dry-run` |
| Handoff file override & missing handling | Support optional `--file PATH` (default `root/.opengsd_handoff.md`); exit 1 with stderr `mad: handoff file not found: <path>` |
| Log entry on launch | No duplicate log entry on launch (`context_orchestrator` already appends `handoff`) |
| Section validation | Validate OKF frontmatter and all four spec §6 headings before exec; exit 1 on malformed file |

---

## context_orchestrator & route_task

| Question | Selected Option |
|----------|-----------------|
| Deterministic helper for `context_orchestrator` | Provide `mad handoff --write --agent A --problem P --step S... [--context C...] [--verify V...]` CLI helper |
| `mad check` in Phase 2 | Add a Phase 2 stub for `mad check` (`ok`/exit 0, or `MAD_FORCE_HANDOFF=1` → `handoff`/exit 10) |
| Subagent model-tier policy placement | Include in `skills/route_task/SKILL.md` alongside the pre-task `mad check` gate |

---

## install-skills.sh target paths

| Question | Selected Option |
|----------|-----------------|
| Default target dirs & env overrides | `~/.claude/skills` and `~/.gemini/config/skills`, overridable via `MAD_CLAUDE_SKILLS_DIR` and `MAD_AGY_SKILLS_DIR` |
| Existing target collision handling | `ln -sfn` for symlinks, `mkdir -p` for parent dirs, refuse to overwrite real non-symlink directories (exit 1) |
| `--dry-run` output format | `ln -sfn <abs_source> <abs_dest>` one per line |
| Skill discovery | Only directories in `skills/` containing `SKILL.md` (sorted alphabetically) |

---

## Claude's Discretion

- Module layout for Phase 2 (`mad/context.py`, `mad/handoff.py`).
- Exact OKF frontmatter metadata on `.opengsd_handoff.md`.

## Deferred Ideas

None.
