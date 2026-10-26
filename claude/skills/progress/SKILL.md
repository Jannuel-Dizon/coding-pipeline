---
name: progress
description: Status summary from the handoff record and work item tracker — read-only
argument-hint: [ticket ID | epic | "last few slices"]
disable-model-invocation: true
model: haiku
effort: low
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(~/.claude/pipeline/scripts/pipeline-ctx.sh *)
---

(Named `progress` because Claude Code has a built-in `/status`.)

You MUST answer from the actual handoff files, not memory. You MUST distinguish
complete / partial / stopped / blocked, and call out anything planned or specced
but not yet reported as built. You MUST NOT write anything.

<scope>
$ARGUMENTS
</scope>

Reports: !`~/.claude/pipeline/scripts/pipeline-ctx.sh reports 10`
Specs (planned, maybe not built): !`~/.claude/pipeline/scripts/pipeline-ctx.sh specs 10`
Plans (earliest stage): !`~/.claude/pipeline/scripts/pipeline-ctx.sh plans 10`
Tracking: !`~/.claude/pipeline/scripts/pipeline-ctx.sh tracking`
Work item index:
!`~/.claude/pipeline/scripts/pipeline-ctx.sh workitems`

Those are filenames; read the ones the scope needs. For each stem work out where
it got to:

- Report `Status: complete` → built; say what was verified and what was not
  (read the report's own verification section).
- Report `partial` or `stopped` → say what is built and what is not. Never round
  up to "done".
- Spec, no report → specced, not built. Plan, no spec → still planning.
- Spec `Status: replan` → kicked back, waiting on the human.

If Tracking says `yes`, cross-check each stem's ticket ID against the index
(including `items/done/` when relevant) and name every disagreement — tracker
done but no report, report complete but tracker active, ticket missing. Do not
resolve them. If it says `none`, say so in one line.

End with one line per stem: stage reached, tracker status, divergence.
