**Multi-Agent Intelligent Orchestration & Routing Specification**

## 1. System Architecture & Objective

Design an intelligent orchestration layer to manage local development across Google AI Ultra (`agy`) and Claude Code Pro (`claude`), strictly utilizing subscription limits without API keys. The system extends `openGSD` and `superpowers` workflows by introducing intelligent model routing (agent-level and internal), context pruning ("just enough context"), and a globally persistent running log.

## 2. State Management & Storage Evaluation

**Decision:** Rely on **OKF (Open Knowledge Format) Markdown with structured frontmatter** over Redis or SQLite.

* **Why not SQLite/Redis:** While databases offer robust querying, they require custom bridge scripts or tools for CLI agents to interact with them effectively. This adds latency and fragility to the workflow.
* **Why OKF Markdown:** LLMs natively read, write, and index file systems. A structured Markdown directory (acting as a flat-file Knowledge Graph) allows agents to instantly `grep`, read, and append to state without complex database abstractions.

**The Context Architecture:**

* `.global_dev_log.md`: An append-only running log of all tasks, agent transitions, and architectural decisions.
* `.active_context/`: A directory containing modular, highly-compacted context files (e.g., `mqtt_topology.md`, `current_snyk_alerts.md`). Agents pull *only* the specific files needed for the current task.

## 3. Intelligent Model Routing & Switching

Implement a local routing script (`router.sh` or a custom skill) that evaluates the prompt's complexity and scope to determine the execution path.

### 3.1 Agent-Level Routing (Agy vs. Claude)

* **Google AI Ultra (`agy`)**
* *Triggers:* Prompts containing >5 files, "design," "architect," "refactor all," or requests involving large documentation sets (e.g., BFO/CCO ontologies, massive Unified Namespace trees).
* *Role:* Heavy-lifting, context ingestion, and asynchronous batch processing.


* **Claude Code Pro (`claude`)**
* *Triggers:* Prompts containing "debug," "write test," "fix error," or tight RED-GREEN-REFACTOR loops.
* *Role:* High-precision, step-by-step logic execution and fast CLI terminal loops.



### 3.2 Internal Model Switching

Agents will use system prompts/skills to downgrade or upgrade models internally to save subscription limits:

* **Within Claude:** Default to Sonnet for standard coding. Fall back to Haiku (if exposed via CLI/skills) for simple documentation generation, regex writing, or linting. Escalate to Opus *only* for deep logical bugs.
* **Within Agy:** Default to Gemini 1.5 Flash for file scaffolding and basic queries. Escalate to Pro/Ultra for multi-file architectural logic and deep repository context windows.

## 4. Global Skill Evolution Plan

You currently have skills for context clearing, compacting, and handoffs. Here is the plan to extend and replace them:

1. **Upgrade `handoff_prep` -> `context_orchestrator**`:
* Instead of just saving a state, this skill will now dynamically evaluate the current session. It will extract the *delta* (what changed), append it to `.global_dev_log.md`, and output a synthesized `.opengsd_handoff.md` containing only the unresolved problem and next exact steps.


2. **New Skill: `context_fetcher` (Just Enough Context)**:
* Before executing a complex task, the agent runs this skill to query the `.active_context/` directory. It uses keyword matching to load only the required Markdown nodes (e.g., if working on Docker, it loads `docker_guidelines.md` and ignores `ui_components.md`).


3. **New Skill: `route_task**`:
* A meta-skill that assesses the current token burn and task size. If Claude hits ~35 messages in the 5-hour window, it automatically triggers `context_orchestrator`, halts, and prints: `run agy --file .opengsd_handoff.md`.



## 5. Implementation Roadmap for Claude Code & Agy

Provide the following prompt/spec to Claude Code and Agy to build the system:

**Phase 1: Foundation & Storage**

* Create the `.active_context` directory and `.global_dev_log.md`.
* Write a baseline Node.js/Python or Bash script that acts as the `router` to intercept user commands and launch the appropriate CLI (`claude` or `agy`) based on file count and keyword heuristics.

**Phase 2: Skill Refactoring**

* Rewrite existing compacting skills into the `context_orchestrator`. Ensure it strictly formats outputs in OKF Markdown.
* Implement the `context_fetcher` skill allowing agents to specifically request required domain knowledge rather than loading the whole repo.

**Phase 3: Telemetry & Limit Enforcement**

* Update the `.agent_telemetry.json` tracker.
* Embed logic in the `context_orchestrator` to forcefully trigger a handoff when the 5-hour Claude limit nears 80% capacity or when Google Ultra hits concurrency limits, ensuring zero downtime.


