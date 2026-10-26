#!/usr/bin/env bash
# configured-model.sh <agent>
#
# Prints the model OpenCode is configured to use for <agent>, read from the
# config files in precedence order (global < OPENCODE_CONFIG override <
# project). Commands inject this into handoff headers so the `Model:` field is
# a value read from config, not a model's guess about itself.
#
# Best effort: it greps the JSONC rather than parsing OpenCode's real merge, so
# it prints "unresolved" instead of guessing when it cannot find a model line.
# Commented-out lines (`// "model": ...`) are ignored.

set -u

agent="${1:-}"
if [ -z "$agent" ]; then
  echo "usage: $0 <agent>" >&2
  exit 1
fi

cfg_home="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"
found=""

for f in \
  "$cfg_home/opencode.jsonc" "$cfg_home/opencode.json" \
  "${OPENCODE_CONFIG:-}" \
  "$PWD/opencode.jsonc" "$PWD/opencode.json" \
  "$PWD/.opencode/opencode.jsonc" "$PWD/.opencode/opencode.json"
do
  [ -n "$f" ] && [ -f "$f" ] || continue
  m=$(grep -v '^[[:space:]]*//' "$f" \
      | grep -A12 "\"$agent\"[[:space:]]*:" \
      | grep -m1 '"model"' \
      | sed -E 's/.*"model"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')
  [ -n "$m" ] && found="$m"
done

echo "${found:-unresolved}"
