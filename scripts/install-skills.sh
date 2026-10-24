#!/usr/bin/env bash
set -euo pipefail

dry_run=false
for arg in "$@"; do
  case "$arg" in
    --dry-run)
      dry_run=true
      ;;
    *)
      echo "install-skills.sh: unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

real_script="$(readlink -f "${BASH_SOURCE[0]}")"
repo_root="$(cd "$(dirname "$real_script")/.." && pwd -P)"
skills_root="$repo_root/skills"

claude_dir="${MAD_CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
agy_dir="${MAD_AGY_SKILLS_DIR:-$HOME/.gemini/config/skills}"

shopt -s nullglob
skill_files=("$skills_root"/*/SKILL.md)
shopt -u nullglob

for skill_md in "${skill_files[@]}"; do
  skill_dir="$(dirname "$skill_md")"
  skill_name="$(basename "$skill_dir")"
  for target_root in "$claude_dir" "$agy_dir"; do
    dest="$target_root/$skill_name"
    if [ -d "$dest" ] && [ ! -L "$dest" ]; then
      echo "install-skills.sh: refusing to overwrite real directory: $dest" >&2
      exit 1
    fi
    if [ "$dry_run" = true ]; then
      echo "ln -sfn $skill_dir $dest"
    else
      mkdir -p "$target_root"
      ln -sfn "$skill_dir" "$dest"
      echo "ln -sfn $skill_dir $dest"
    fi
  done
done
