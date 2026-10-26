---
name: tickets
description: Browse available work items — read-only, outside the pipeline
argument-hint: [filter, e.g. "unblocked P0" or an epic]
disable-model-invocation: true
model: haiku
effort: low
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(~/.claude/pipeline/scripts/pipeline-ctx.sh *)
---

You MUST answer from the generated work item files only. Do NOT plan, design or
propose an implementation; the decision of what to work on is the human's.

<filter>
$ARGUMENTS
</filter>

Tracking: !`~/.claude/pipeline/scripts/pipeline-ctx.sh tracking`
Index:
!`~/.claude/pipeline/scripts/pipeline-ctx.sh workitems`

If Tracking is `none` or the index is missing, say so in one line and stop. The
index comes from `scripts/ingest-workitems.py`, which also flips tracking to
`yes`.

Answer the filter against the index. Lead with what is unblocked (all
dependencies done). Quote points as effort only — never suggest a tier or call
anything simple or safe; tier is assigned by the spec stage against the T3
floor. Name blockers explicitly. Read `.workitems/items/<ID>.md` only for items
the human asks about.

End with the candidate IDs and nothing more. The human picks, then runs
`/spec <ID> <what they want>`.
