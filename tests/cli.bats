#!/usr/bin/env bats

setup() {
  REPO="$(cd "$BATS_TEST_DIRNAME/.." && pwd -P)"
  MAD="$REPO/bin/mad"
  export MAD_CLAUDE_BIN="$REPO/tests/stub_cli.sh"
  export MAD_AGY_BIN="$REPO/tests/stub_cli.sh"
  export STUB_OUT="$BATS_TEST_TMPDIR/argv"
  cd "$BATS_TEST_TMPDIR"
  mkdir -p .git
}

@test "route prints claude/sonnet for debug" {
  run "$MAD" route "debug the reconnect" a.py
  [ "$status" -eq 0 ]
  parsed="$(printf '%s' "$output" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["agent"],d["model"])')"
  [ "$parsed" = "claude sonnet" ]
}

@test "run --dry-run prints argv and writes nothing" {
  run "$MAD" run --dry-run "design the uns tree"
  [ "$status" -eq 0 ]
  [ "$output" = "$MAD_AGY_BIN --model gemini-4-argon-high -i 'design the uns tree'" ]
  [ ! -e ".global_dev_log.md" ]
}

@test "run execs stub and logs transition" {
  run "$MAD" run "debug x"
  [ "$status" -eq 0 ]
  mapfile -t lines < "$STUB_OUT"
  [ "${lines[0]}" = "--model" ]
  [ "${lines[1]}" = "sonnet" ]
  [ "${lines[2]}" = "debug x" ]
  grep -Fq "· transition · claude" .global_dev_log.md
  grep -Fq -- "- reasons: kw:debug" .global_dev_log.md
}

@test "init twice" {
  run "$MAD" init
  [ "$status" -eq 0 ]
  run "$MAD" init
  [ "$status" -eq 0 ]
  [ "$output" = "nothing to do" ]
}

@test "prompt starting with dash after --" {
  run "$MAD" route -- "-v flag is broken, debug it"
  [ "$status" -eq 0 ]
  agent="$(printf '%s' "$output" | python3 -c 'import json,sys;print(json.load(sys.stdin)["agent"])')"
  [ "$agent" = "claude" ]
}

@test "works through a symlink from another dir" {
  ln -s "$MAD" "$BATS_TEST_TMPDIR/m"
  cd /tmp
  run "$BATS_TEST_TMPDIR/m" route "x"
  [ "$status" -eq 0 ]
}

@test "no args is a usage error" {
  run "$MAD"
  [ "$status" -eq 2 ]
}

@test "log with bad --field" {
  run "$MAD" log --kind note --agent human --field nokv msg
  [ "$status" -eq 2 ]
}

@test "fetch prints only matching docker file and --reindex updates INDEX.md" {
  "$MAD" init
  cat > .active_context/docker_guidelines.md <<'EOF'
---
title: Docker Guidelines
keywords: [docker, container]
updated: 2026-10-23
---

Use multi-stage builds.
EOF
  cat > .active_context/ui_components.md <<'EOF'
---
title: UI Components
keywords: [react, css]
updated: 2026-10-23
---

Use CSS variables.
EOF
  run "$MAD" fetch docker
  [ "$status" -eq 0 ]
  [ "$output" = ".active_context/docker_guidelines.md" ]

  run "$MAD" fetch --reindex
  [ "$status" -eq 0 ]
  [ "$output" = ".active_context/INDEX.md" ]
  grep -Fq ".active_context/docker_guidelines.md — Docker Guidelines [docker, container]" .active_context/INDEX.md
}

@test "handoff --write creates .opengsd_handoff.md and handoff launches agy stub" {
  run "$MAD" handoff
  [ "$status" -eq 1 ]

  run "$MAD" handoff --write --agent claude --problem "MQTT drop" --step "Check broker" --context ".active_context/mqtt.md" --verify "pytest -q"
  [ "$status" -eq 0 ]
  [ -f ".opengsd_handoff.md" ]
  grep -Fq "## Unresolved problem" .opengsd_handoff.md
  grep -Fq "## Next exact steps" .opengsd_handoff.md
  grep -Fq "## Context files to load" .opengsd_handoff.md
  grep -Fq "## Verify with" .opengsd_handoff.md
  grep -Fq "· handoff · claude" .global_dev_log.md

  run "$MAD" handoff
  [ "$status" -eq 0 ]
  grep -Fq -- "--model" "$STUB_OUT"
  grep -Fq "gemini-4-argon-high" "$STUB_OUT"
  grep -Fq "## Unresolved problem" "$STUB_OUT"
}

@test "check stub exits 0 by default and 10 when MAD_FORCE_HANDOFF=1" {
  run "$MAD" check
  [ "$status" -eq 0 ]
  [ "$output" = "ok" ]

  MAD_FORCE_HANDOFF=1 run "$MAD" check
  [ "$status" -eq 10 ]
  [ "$output" = "handoff" ]
}
