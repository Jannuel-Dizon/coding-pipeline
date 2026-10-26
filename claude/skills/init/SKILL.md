---
name: init
description: Set up the shared pipeline layout and .claude config in this repo (safe on new or existing repos)
disable-model-invocation: true
allowed-tools:
  - Bash(~/.claude/pipeline/scripts/init-project.sh *)
---

(Overrides Claude Code's built-in `/init` so the pipeline layout is built the
same way as OpenCode's `/init`. Use `/init` from either tool; both run the same
script and it is idempotent.)

Script output (it never overwrites; existing files are skipped and named; an
older layout is only moved with `--migrate`):
!`~/.claude/pipeline/scripts/init-project.sh "$PWD" || true`

Relay that report accurately — created, skipped, flagged — and then stop. Do not
redo any of it or edit files. Then say only what applies, in order:

1. If it flagged `.opencode/handoff`, `.opencode/workitems`, `.opencode/AGENTS.md`
   or `.opencode/MAP.md`: those are pre-2.0 locations and nothing was moved. To
   move them the human runs `~/.claude/pipeline/scripts/init-project.sh --migrate`.
2. If it created `AGENTS.md`: the **T3 floor** section is a human decision, left
   as TODO on purpose. Do not suggest values.
3. Run `/map` once to generate `.handoff/MAP.md`, and again after structural changes.
4. If `.workitems/TRACKING.md` says `Tracking: none`, say so in one line.
