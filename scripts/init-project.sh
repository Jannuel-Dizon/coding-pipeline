#!/usr/bin/env bash
# init-project.sh [--migrate] [--dry-run] [project-dir]
#
# Sets up the shared pipeline layout in a repo. Called by /init in OpenCode and
# in Claude Code, and safe to run by hand. Deterministic and token-free: no
# model decides what gets created.
#
#   <project>/
#     .handoff/{1-plan,2-spec,3-report}/   the shared record; templates symlinked
#     .workitems/TRACKING.md               says whether tickets are tracked
#     .opencode/opencode.jsonc             OpenCode project overrides (all commented)
#     .claude/settings.json                Claude Code project permissions
#     AGENTS.md                            project facts (both tools; T3 floor = TODO)
#     CLAUDE.md                            "@AGENTS.md" + Claude notes
#
# It never overwrites anything. Every path that already exists is reported as
# kept; a file that exists but looks wrong is flagged, not fixed. Output
# legend:  + created   = kept   > moved   ! needs a human look
#
# If the project is a git repo (.git beside it), every path above is also
# added to .git/info/exclude so it stays out of `git status`. Local only; the
# tracked .gitignore is untouched, and files git already tracks are unaffected.
#
# --migrate   move a pre-2.0 layout into place: .opencode/handoff -> .handoff,
#             .opencode/workitems -> .workitems, .opencode/MAP.md ->
#             .handoff/MAP.md, .opencode/AGENTS.md -> AGENTS.md. Uses `git mv`
#             for tracked paths, never overwrites, skips on conflict. Without
#             this flag the old paths are only flagged.
# --dry-run   print what would happen, change nothing.

set -euo pipefail

MIGRATE=0
DRY=0
PROJECT=""

for arg in "$@"; do
  case "$arg" in
    --migrate) MIGRATE=1 ;;
    --dry-run) DRY=1 ;;
    -h|--help) sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "unknown option: $arg" >&2; exit 2 ;;
    *) PROJECT="$arg" ;;
  esac
done

PROJECT="${PROJECT:-$PWD}"
if [ ! -d "$PROJECT" ]; then
  echo "not a directory: $PROJECT" >&2
  exit 2
fi
PROJECT="$(cd "$PROJECT" && pwd -P)"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
VERSION="$(cat "$REPO_DIR/VERSION" 2>/dev/null || echo unknown)"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

created=0; kept=0; moved=0; flagged=0
say_created() { echo "  + $1"; created=$((created + 1)); }
say_kept()    { echo "  = $1"; kept=$((kept + 1)); }
say_moved()   { echo "  > $1"; moved=$((moved + 1)); }
say_flag()    { echo "  ! $1"; flagged=$((flagged + 1)); }
act()         { if [ "$DRY" = 1 ]; then :; else "$@"; fi; }
exists()      { [ -e "$1" ] || [ -L "$1" ]; }

echo "init-project: $PROJECT"
echo "pipeline $VERSION$( [ "$DRY" = 1 ] && echo '  (dry run — nothing will be written)' )"
echo ""

# ---------------------------------------------------------------- migrate ---

in_git() { git -C "$PROJECT" rev-parse --is-inside-work-tree >/dev/null 2>&1; }

move_path() {  # <src-rel> <dst-rel>
  local src="$PROJECT/$1" dst="$PROJECT/$2"
  exists "$src" || return 0
  if exists "$dst"; then
    say_flag "both $1 and $2 exist — left both alone; reconcile by hand"
    return 0
  fi
  if [ "$MIGRATE" != 1 ]; then
    say_flag "pre-2.0 layout: $1 (now lives at $2) — rerun with --migrate to move it"
    return 0
  fi
  if [ "$DRY" = 1 ]; then say_moved "would move $1 -> $2"; return 0; fi
  mkdir -p "$(dirname "$dst")"
  if in_git && git -C "$PROJECT" ls-files --error-unmatch -- "$1" >/dev/null 2>&1; then
    git -C "$PROJECT" mv -- "$1" "$2"
  else
    mv "$src" "$dst"
  fi
  say_moved "$1 -> $2"
}

move_path ".opencode/handoff"   ".handoff"
move_path ".opencode/workitems" ".workitems"
move_path ".opencode/MAP.md"    ".handoff/MAP.md"
move_path ".opencode/AGENTS.md" "AGENTS.md"

# A legacy path that is still waiting to be moved must not get an empty twin
# created beside it — that would leave --migrate with a conflict it refuses to
# resolve. Scaffold each group only once its old location is out of the way.
pending() { exists "$PROJECT/$1" && ! exists "$PROJECT/$2"; }
SKIP_HANDOFF=0;   if pending ".opencode/handoff"   ".handoff";   then SKIP_HANDOFF=1;   fi
SKIP_WORKITEMS=0; if pending ".opencode/workitems" ".workitems"; then SKIP_WORKITEMS=1; fi
SKIP_AGENTS=0;    if pending ".opencode/AGENTS.md" "AGENTS.md";  then SKIP_AGENTS=1;    fi
skip_note() { echo "    (skipped: $1 — create it only after --migrate has moved the old one)"; }

# ---------------------------------------------------------------- handoff ---

ensure_dir() {  # <rel>
  if [ -d "$PROJECT/$1" ]; then say_kept "$1/"; else act mkdir -p "$PROJECT/$1"; say_created "$1/"; fi
}

if [ "$SKIP_HANDOFF" = 1 ]; then
  skip_note ".handoff/"
else
for d in 1-plan 2-spec 3-report; do
  ensure_dir ".handoff/$d"
  if [ "$DRY" != 1 ] && [ -z "$(ls -A "$PROJECT/.handoff/$d" 2>/dev/null)" ]; then
    : > "$PROJECT/.handoff/$d/.gitkeep"
  fi
done

link_template() {  # <file-name>
  local name="$1" src="$REPO_DIR/shared/templates/$1" dst="$PROJECT/.handoff/$1"
  if [ -L "$dst" ]; then
    act ln -sfn "$src" "$dst"
    say_kept ".handoff/$name (symlink, refreshed)"
  elif exists "$dst"; then
    if diff -q "$dst" "$src" >/dev/null 2>&1; then
      say_kept ".handoff/$name (real file, identical to the repo template)"
    else
      say_flag ".handoff/$name is a real file that differs from the repo template — kept. See: diff $src $dst"
    fi
  else
    act ln -s "$src" "$dst"
    say_created ".handoff/$name -> $src"
  fi
}
link_template PLAN_TEMPLATE.md
link_template SPEC_TEMPLATE.md
link_template REPORT_TEMPLATE.md
fi

# -------------------------------------------------------------- workitems ---

TRACKING="$PROJECT/.workitems/TRACKING.md"
if [ "$SKIP_WORKITEMS" = 1 ]; then
  skip_note ".workitems/"
else
ensure_dir ".workitems"
if exists "$TRACKING"; then
  say_kept ".workitems/TRACKING.md"
elif exists "$PROJECT/.workitems/WORKITEMS.md"; then
  if [ "$DRY" != 1 ]; then
    cat > "$TRACKING" <<'EOF'
# Work item tracking

Tracking: yes

Sources: unknown (this directory predates TRACKING.md — rerun
`scripts/ingest-workitems.py` with your usual flags and this file is rewritten
with the real sources and counts).

Index: `WORKITEMS.md`. Detail per ticket: `items/<ID>.md`, finished ones in
`items/done/`.
EOF
  fi
  say_created ".workitems/TRACKING.md (Tracking: yes — existing index found)"
else
  if [ "$DRY" != 1 ]; then
    cat > "$TRACKING" <<'EOF'
# Work item tracking

Tracking: none

No task tracker is wired to this repo, so there is no `WORKITEMS.md` and the
planner has no ticket index to read. Plans and specs are driven by the slice
description alone.

To start tracking: run `scripts/ingest-workitems.py` (see the pipeline README,
"Work items"). It writes the index and per-ticket files here and rewrites this
file to `Tracking: yes`, with the sources and counts.
EOF
  fi
  say_created ".workitems/TRACKING.md (Tracking: none)"
fi
fi

# ------------------------------------------------------------ project facts ---

safe_name="$(printf '%s' "$(basename "$PROJECT")" | tr -c 'A-Za-z0-9 ._-' '_')"

if [ "$SKIP_AGENTS" = 1 ]; then
  skip_note "AGENTS.md"
elif exists "$PROJECT/AGENTS.md"; then
  say_kept "AGENTS.md"
  if ! grep -qi 'T3 floor' "$PROJECT/AGENTS.md" 2>/dev/null; then
    say_flag "AGENTS.md has no 'T3 floor' section — until you add one (see $REPO_DIR/project/AGENTS.md.example) the pipeline falls back to its default floor (auth, crypto, keys, irreversible writes, money)"
  fi
else
  if [ "$DRY" != 1 ]; then
    awk -v n="$safe_name" '{ gsub(/<PROJECT NAME>/, n) } 1' \
      "$REPO_DIR/project/AGENTS.md.example" > "$PROJECT/AGENTS.md"
  fi
  say_created "AGENTS.md (skeleton — the T3 floor is left TODO on purpose; that list is a human decision)"
fi

if exists "$PROJECT/CLAUDE.md"; then
  say_kept "CLAUDE.md"
  if ! grep -q '^@AGENTS\.md' "$PROJECT/CLAUDE.md" 2>/dev/null; then
    say_flag "CLAUDE.md does not import AGENTS.md — Claude Code will not see your project facts or the T3 floor. Add a line '@AGENTS.md' to it."
  fi
else
  act cp "$REPO_DIR/project/CLAUDE.md.example" "$PROJECT/CLAUDE.md"
  say_created "CLAUDE.md (imports AGENTS.md)"
fi

# ------------------------------------------------------------ tool folders ---

ensure_dir ".opencode"
if exists "$PROJECT/.opencode/opencode.jsonc" || exists "$PROJECT/.opencode/opencode.json"; then
  say_kept ".opencode/opencode.jsonc (existing project config)"
else
  act cp "$REPO_DIR/project/opencode.jsonc.example" "$PROJECT/.opencode/opencode.jsonc"
  say_created ".opencode/opencode.jsonc (every override commented out — inherits the global config)"
fi

ensure_dir ".claude"
if exists "$PROJECT/.claude/settings.json"; then
  say_kept ".claude/settings.json (existing project settings)"
else
  act cp "$REPO_DIR/project/claude-settings.json.example" "$PROJECT/.claude/settings.json"
  say_created ".claude/settings.json (deny .env reads, git push, rm -rf; ask on commit)"
fi

# ------------------------------------------------------------ git exclude ---
# Local-only ignore: the paths this script manages go into the repo's
# .git/info/exclude, so they stay out of `git status` without touching the
# tracked .gitignore. Exclude rules never affect files git already tracks.
# Only a repo root (.git beside PROJECT) is touched; a subdirectory of a larger
# repo would otherwise get root-anchored entries in the wrong place.

EXCLUDE_PATHS=(.handoff .workitems .opencode .claude AGENTS.md CLAUDE.md)

if [ -e "$PROJECT/.git" ] && in_git; then
  exclude_file="$(git -C "$PROJECT" rev-parse --git-path info/exclude)"
  case "$exclude_file" in /*) ;; *) exclude_file="$PROJECT/$exclude_file" ;; esac
  for p in "${EXCLUDE_PATHS[@]}"; do
    if [ "$DRY" != 1 ] && ! exists "$PROJECT/$p"; then continue; fi
    if [ -f "$exclude_file" ] && grep -qxF "/$p" "$exclude_file"; then
      say_kept ".git/info/exclude already has /$p"
    elif [ "$DRY" = 1 ]; then
      echo "  + .git/info/exclude += /$p (would add)"
    else
      mkdir -p "$(dirname "$exclude_file")"
      if [ -s "$exclude_file" ] && [ -n "$(tail -c1 "$exclude_file")" ]; then echo >> "$exclude_file"; fi
      echo "/$p" >> "$exclude_file"
      echo "  + .git/info/exclude += /$p"
    fi
  done
elif [ -e "$PROJECT/.git" ]; then
  say_flag ".git is present but git cannot read this repo — .git/info/exclude not updated"
fi

# ----------------------------------------------------------- global layers ---

[ -e "$CONFIG_HOME/opencode/pipeline" ] || \
  say_flag "OpenCode global layer not installed (no $CONFIG_HOME/opencode/pipeline) — run: $REPO_DIR/scripts/install-global.sh --opencode"
[ -e "$HOME/.claude/pipeline" ] || \
  say_flag "Claude Code global layer not installed (no ~/.claude/pipeline) — run: $REPO_DIR/scripts/install-global.sh --claude"

echo ""
echo "created $created · kept $kept · moved $moved · flagged $flagged"
