#!/usr/bin/env bash
# pipeline-ctx.sh <topic> [n]
#
# Read-only context for the Claude Code skills. Exists so each skill needs ONE
# pre-approved command instead of a different `ls | head | xargs sed` pipeline
# per line — Claude Code checks every piece of a compound command against the
# permission rules, and a skill whose injected command is not allowed aborts.
#
# Always exits 0 and always prints something, so an empty repo or a missing
# folder produces a readable line instead of an aborted skill. Run from the
# project root.
#
# topics:  date | version | plans [n] | specs [n] | reports [n]
#          tracking | workitems | gitstate | diffstat | head

set -u

topic="${1:-}"
n="${2:-5}"

list_md() {  # <dir> <n>
  if [ -d "$1" ] && ls "$1"/*.md >/dev/null 2>&1; then
    ls -t "$1"/*.md | head -n "$2"
  else
    echo "(none)"
  fi
}

case "$topic" in
  date)      date +%Y-%m-%d ;;
  version)   cat "$(dirname "${BASH_SOURCE[0]}")/../VERSION" 2>/dev/null || echo unknown ;;
  plans)     list_md .handoff/1-plan "$n" ;;
  specs)     list_md .handoff/2-spec "$n" ;;
  reports)   list_md .handoff/3-report "$n" ;;
  tracking)
    if [ -f .workitems/TRACKING.md ]; then head -8 .workitems/TRACKING.md
    else echo "no .workitems/TRACKING.md — run /init"; fi ;;
  workitems)
    if [ -f .workitems/WORKITEMS.md ]; then cat .workitems/WORKITEMS.md
    else echo "no workitems index"; fi ;;
  gitstate)  git status --porcelain 2>/dev/null || echo "(not a git repository)" ;;
  diffstat)  git diff --stat 2>/dev/null || echo "(not a git repository)" ;;
  head)      git rev-parse --short HEAD 2>/dev/null || echo "(no commits)" ;;
  *)         echo "usage: pipeline-ctx.sh date|version|plans|specs|reports|tracking|workitems|gitstate|diffstat|head [n]" ;;
esac
exit 0
