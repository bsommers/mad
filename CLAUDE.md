# CLAUDE.md

Read `AGENTS.md`: it is the canonical briefing (commands, architecture, invariants, process).
Then read `.planning/STATE.md` for where work stands.

## Claude Code only

- Plan and execute with superpowers skills: `superpowers:writing-plans` for each phase's step plan,
  `superpowers:test-driven-development` while coding, and `superpowers:verification-before-completion` before claiming done.
- There are no `/gsd-*` slash commands here (GSD is artifacts-only). Edit `.planning/` files by hand from the
  gsd-core templates in `~/.gemini/config/plugins/gsd-core/gsd-core/templates/`.
- Model tiers for subagents follow the routing policy: `haiku` for docs, regex and lint; `sonnet` by default;
  `opus` only for deep logic bugs and whole-branch review.
- At about 80% of the 5-hour window, stop. Run the handoff (`context_orchestrator`, Phase 2) and print the `agy` command for the user.
  Don't keep working until the limit cuts you off.
