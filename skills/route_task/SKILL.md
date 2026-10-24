---
name: route_task
description: Use before starting a large task or spawning subagents to check subscription capacity (mad check), trigger a clean handoff on exit 10, and select the right subagent model tier inside a live session.
---

# route_task

Checks subscription capacity before starting a large task and enforces the `mad` model-tier routing table for subagents inside a live session.

## 1. Pre-Task Capacity Check

Before starting a multi-file or complex task, run:

```bash
bin/mad check
```

- **Exit `0` (`ok`):** Proceed with the task.
- **Exit `10` (`handoff`):** Stop immediately. Execute the `context_orchestrator` skill (`bin/mad handoff --write ...`), do not start new work, and print:
  ```bash
  bin/mad handoff
  ```

## 2. In-Session Subagent Model Tiers

A running CLI session cannot switch its own top-level model mid-session. Apply the `config/routing.json` model policy when spawning subagents:

| Runtime | Mechanism | Tier / Condition | Model ID |
|---|---|---|---|
| Claude Code | `Agent` tool `model` | Deep logic bugs, race conditions, deadlocks, memory corruption (`opus_keywords`) | `opus` |
| Claude Code | `Agent` tool `model` | Docs, README, changelog, regex, lint, format, typo (`haiku_keywords`) with no debug/test signals | `haiku` |
| Claude Code | `Agent` tool `model` | Default implementation, TDD, debugging | `sonnet` |
| Antigravity (`agy`) | `agy -p --model` | Light single-file subtasks with no architecture signals | `gemini-3.8-flash-medium` |
| Antigravity (`agy`) | `agy -p --model` | Architecture, design, ontology/BFO/CCO, UNS, or >5 files | `gemini-4-argon-high` |
