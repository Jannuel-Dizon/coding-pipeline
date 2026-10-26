---
description: Stage 1 — design a slice with the planning agent
agent: design
---

<summary>
You MUST run the planning stage for the slice described below.
You SHOULD read `.handoff/PLAN_TEMPLATE.md` and the most recent
documents in `.handoff/3-report/` before responding.
You MUST end by writing the plan, printing its absolute path and full contents,
and stopping.
</summary>

<slice>
$ARGUMENTS
</slice>

Today's date: !`date +%Y-%m-%d`

Pipeline version (stamp this in the header's `Pipeline:` field):
!`cat ~/.config/opencode/pipeline/VERSION 2>/dev/null || echo unknown`

Recent reports (context for what already exists):
!`ls -t .handoff/3-report/*.md 2>/dev/null | head -3`

Open items from the last report:
!`ls -t .handoff/3-report/*.md 2>/dev/null | head -1 | xargs -r sed -n '/## 7. Still open/,/## 8./p'`

Model actually configured for this agent (stamp this verbatim in `Model:`):
!`~/.config/opencode/pipeline/scripts/configured-model.sh design`

Start by discussing the slice with me. Do not write the document until I say
the plan is settled.
