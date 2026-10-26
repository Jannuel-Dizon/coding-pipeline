#!/usr/bin/env bash
# build-explore-agent.sh [--check]
#
# claude/agents/Explore.md is the OpenCode `explore` prompt wrapped in Claude
# Code subagent frontmatter. The prompt body has ONE source of truth —
# shared/prompts/explore.md — and this script regenerates the Claude copy from
# it. Run it after editing that prompt; `--check` exits non-zero if the two have
# drifted (use it before committing).
#
# Why a copy at all: Claude Code subagents are files with frontmatter, and an
# OpenCode prompt file has none. Why named `Explore`: a user subagent with the
# built-in's name replaces it, which is how the model gets pinned to Haiku —
# the built-in runs on the Opus alias for subscription users.

set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SRC="$REPO_DIR/shared/prompts/explore.md"
DST="$REPO_DIR/claude/agents/Explore.md"

render() {
  cat <<'FM'
---
name: Explore
description: Read-only lookup. Answers one specific question about the codebase in prose with path:line citations, so the main session does not have to read the files itself. Use for searches that would otherwise pull many files into context.
tools: Read, Grep, Glob
model: haiku
maxTurns: 10
---

FM
  cat "$SRC"
}

if [ "${1:-}" = "--check" ]; then
  if render | diff -q - "$DST" >/dev/null 2>&1; then
    echo "Explore.md is in sync with shared/prompts/explore.md"
  else
    echo "claude/agents/Explore.md has drifted from shared/prompts/explore.md — run scripts/build-explore-agent.sh" >&2
    exit 1
  fi
else
  render > "$DST"
  echo "wrote $DST"
fi
