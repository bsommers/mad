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
