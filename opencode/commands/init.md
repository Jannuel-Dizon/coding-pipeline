---
description: Set up the shared pipeline layout in this repo (safe on new or existing repos)
agent: ask
---

<summary>
The setup below was already performed by a script before you saw this message.
You MUST NOT redo it, edit files, or run anything yourself.
You MUST relay the script's report accurately — what it created, what it
skipped because it already existed, and what it flagged — and then stop.
</summary>

Script output (it never overwrites anything; existing files are skipped and
named, and a layout from an older pipeline version is only moved with
`--migrate`):
!`~/.config/opencode/pipeline/scripts/init-project.sh "$PWD" || true`

Relay the report above. Then tell the human, in this order and only what
applies:

1. If it flagged an old `.opencode/handoff`, `.opencode/workitems`,
   `.opencode/AGENTS.md`, or `.opencode/MAP.md`: those are the pre-2.0 locations.
   Nothing was moved. To move them, the human runs
   `~/.config/opencode/pipeline/scripts/init-project.sh --migrate` themselves.
2. If it created `AGENTS.md`: the **T3 floor** section is a human decision and
   is left as TODO on purpose. Do not suggest values for it.
3. Run `/map` once to generate `.handoff/MAP.md`, and again after any structural
   change. `/init` sets the layout up; `/map` keeps it accurate.
4. If `.workitems/TRACKING.md` says `Tracking: none`, say so in one line. It
   flips to `yes` by itself the first time `scripts/ingest-workitems.py` runs.
