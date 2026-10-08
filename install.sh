#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
destination=${CODEX_HOME:+$CODEX_HOME/skills}
destination=${destination:-"$HOME/.codex/skills"}
skill=${1:-all}

case "$skill" in
  all) names="douyin-xhs-crawler skillto-table" ;;
  douyin-xhs-crawler|skillto-table) names="$skill" ;;
  *) echo "Usage: ./install.sh [all|douyin-xhs-crawler|skillto-table]" >&2; exit 2 ;;
esac

mkdir -p "$destination"
for name in $names; do
  source_dir="$repo_root/skills/$name"
  target_dir="$destination/$name"
  test -f "$source_dir/SKILL.md" || { echo "Invalid skill source: $source_dir" >&2; exit 1; }
  test ! -e "$target_dir" || { echo "Destination already exists: $target_dir" >&2; exit 1; }
  cp -R "$source_dir" "$target_dir"
  echo "Installed $name -> $target_dir"
done
