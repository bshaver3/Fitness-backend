#!/bin/bash
# PreToolUse hook for Edit|Write|NotebookEdit: block edits to secrets and
# generated files, and require confirmation for deploy config.
path=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty')
[ -z "$path" ] && exit 0
rel=${path#"${CLAUDE_PROJECT_DIR:-$PWD}"/}

decide() {
  jq -n --arg d "$1" --arg r "$2" \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: $d, permissionDecisionReason: $r}}'
  exit 0
}

case "$rel" in
  .env | .env.* | */.env | */.env.*)
    decide deny "$rel holds environment config; ask the user to edit it themselves." ;;
  .venv/* | __pycache__/* | .elasticbeanstalk/*)
    decide deny "$rel is generated (virtualenv / bytecode / EB CLI state); don't hand-edit it." ;;
  Procfile | .ebignore | .ebextensions/*)
    decide ask "$rel controls the Elastic Beanstalk deploy; confirm this change." ;;
esac
exit 0
