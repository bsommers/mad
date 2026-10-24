---
name: context_fetcher
description: Use at the start of a task or when switching topics to load only the relevant .active_context/*.md files within the byte budget instead of reading the entire directory.
---

# context_fetcher

Loads only the `.active_context/*.md` topic files that match the current task's keywords, staying within `fetch_budget_bytes` (default 24,000 bytes).

## Steps

1. **Query matching context files** using task keywords:
   ```bash
   bin/mad fetch <keyword1> <keyword2> ...
   ```
   `mad fetch` scores `.active_context/*.md` (2 points per frontmatter `keywords` match, 1 point per `title` word match, sorted by `(-score, filename)`) and prints only the paths that fit within the byte budget.

2. **Read only the printed files.** Do not read unmatched `.active_context/*.md` files.

3. **Maintain `.active_context/INDEX.md`** whenever you create or update a `.active_context/<topic>.md` file (which must begin with OKF YAML frontmatter `title`, `keywords`, `updated`):
   ```bash
   bin/mad fetch --reindex
   ```
