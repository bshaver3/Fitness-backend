#!/bin/bash
# PostToolUse hook for Edit|Write: format and autofix edited Python files.
path=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty')
case "$path" in
  *.py) ;;
  *) exit 0 ;;
esac
[ -f "$path" ] || exit 0
command -v ruff >/dev/null || exit 0
ruff check --fix --quiet "$path" >/dev/null 2>&1
ruff format --quiet "$path"
