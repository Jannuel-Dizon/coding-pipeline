#!/usr/bin/env bash
# install-global.sh [--opencode] [--claude]
#
# Run once per device (default: both tools). Everything is a symlink into this
# cloned repo, so updating a device afterwards is just:
#
#   cd <this repo> && git pull
#
# OpenCode  (~/.config/opencode): opencode/{opencode.jsonc,commands} and
#           shared/{AGENTS.md,prompts,templates}, plus `pipeline` -> this repo (scripts and VERSION).
# Claude    (~/.claude): `pipeline` -> this repo, rules/pipeline.md (the shared
#           rules), skills/<name> for each pipeline skill, agents/Explore.md,
#           and the PreToolUse handoff guard merged into settings.json.
#
# Personal per-device OpenCode tweaks go in local-overrides.jsonc, which this
# script creates once and NEVER touches again (loaded via OPENCODE_CONFIG).
# Claude settings.json is only ever merged into, with a timestamped backup.

set -euo pipefail

DO_OPENCODE=1; DO_CLAUDE=1
case "${1:-}" in
  --opencode) DO_CLAUDE=0 ;;
  --claude)   DO_OPENCODE=0 ;;
  "")         ;;
  *) echo "usage: $0 [--opencode] [--claude]" >&2; exit 2 ;;
esac

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
OVERRIDE_FILE="$CONFIG_DIR/local-overrides.jsonc"


link_to() {  # <src> <dst>
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"

  if [ -L "$dst" ]; then
    echo "already symlinked: $dst -> $(readlink "$dst")"
    ln -sfn "$src" "$dst"
    return
  fi

  if [ -e "$dst" ]; then
    local backup="$dst.bak.$(date +%Y%m%d%H%M%S)"
    echo "backing up existing $dst -> $backup"
    mv "$dst" "$backup"
  fi

  ln -s "$src" "$dst"
  echo "linked: $dst -> $src"
}

if [ "$DO_OPENCODE" = 1 ]; then
echo "== OpenCode =="
link_to "$REPO_DIR/opencode/opencode.jsonc" "$CONFIG_DIR/opencode.jsonc"
link_to "$REPO_DIR/opencode/commands"       "$CONFIG_DIR/commands"
for f in AGENTS.md prompts templates; do
  link_to "$REPO_DIR/shared/$f" "$CONFIG_DIR/$f"
done
link_to "$REPO_DIR" "$CONFIG_DIR/pipeline"
mkdir -p "$CONFIG_DIR"
if [ ! -e "$OVERRIDE_FILE" ]; then
  cat > "$OVERRIDE_FILE" << 'EOF'
{
  "$schema": "https://opencode.ai/config.json"

  // Personal, per-device overrides. This file is NEVER touched by
  // `git pull` in the pipeline repo — it lives outside it, in
  // ~/.config/opencode/, and is loaded on top of opencode.jsonc via
  // OPENCODE_CONFIG. Deep-merges: only the keys you set here override
  // the template; everything else still comes from opencode.jsonc.
  //
  // Example — swap the T1 build model to the free tier on this device:
  // "agent": {
  //   "build": {
  //     "model": "opencode/deepseek-v4-flash-free"
  //   }
  // }
}
EOF
  echo "created override file: $OVERRIDE_FILE (edit this for personal tweaks)"
else
  echo "override file already exists, leaving it alone: $OVERRIDE_FILE"
fi

case "$SHELL" in
  */zsh) SHELL_RC="$HOME/.zshrc" ;;
  */bash) SHELL_RC="$HOME/.bashrc" ;;
  *) SHELL_RC="$HOME/.profile" ;;
esac
EXPORT_LINE="export OPENCODE_CONFIG=\"$OVERRIDE_FILE\""

if ! grep -qF "OPENCODE_CONFIG=" "$SHELL_RC" 2>/dev/null; then
  echo ""
  echo "Add this line to $SHELL_RC (or your shell's rc file) and restart your shell:"
  echo ""
  echo "  $EXPORT_LINE"
  echo ""
else
  echo "OPENCODE_CONFIG already set in $SHELL_RC — check it points at $OVERRIDE_FILE"
fi

fi

if [ "$DO_CLAUDE" = 1 ]; then
echo "== Claude Code =="
link_to "$REPO_DIR" "$CLAUDE_DIR/pipeline"
link_to "$REPO_DIR/shared/AGENTS.md" "$CLAUDE_DIR/rules/pipeline.md"
for d in "$REPO_DIR"/claude/skills/*/; do
  n="$(basename "$d")"
  link_to "${d%/}" "$CLAUDE_DIR/skills/$n"
done
"$REPO_DIR/scripts/build-explore-agent.sh" >/dev/null
link_to "$REPO_DIR/claude/agents/Explore.md" "$CLAUDE_DIR/agents/Explore.md"
python3 "$REPO_DIR/scripts/merge-claude-settings.py" \
  "$CLAUDE_DIR/settings.json" "$REPO_DIR/claude/settings.pipeline.json"
fi

echo ""
echo "Done. To update this device in future: cd $REPO_DIR && git pull"
echo "Re-run only if a new skill or file is added upstream (it is idempotent)."
