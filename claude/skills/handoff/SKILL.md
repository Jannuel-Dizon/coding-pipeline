---
name: handoff
description: Write the change report for the slice just built in this session
argument-hint: <stem>
disable-model-invocation: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(~/.claude/pipeline/scripts/pipeline-ctx.sh *)
  - Edit(/.handoff/3-report/**)
---

You MUST first confirm that **this session did the build** for the stem below.
If it did not (a fresh session, or a different tool did the work), refuse and
tell the human to run `/handoff` in the session that built it. A report is a
claim that specific work was verified here; an agent that did not do the work
has nothing to report, and writing one would put an unearned claim into the
decision record.

<stem>
$ARGUMENTS
</stem>

Follow `.handoff/REPORT_TEMPLATE.md`. Write to
`.handoff/3-report/$ARGUMENTS.report.md`. Never overwrite an existing report:
if that file exists, stop and tell the human.

Files changed in the working tree:
!`~/.claude/pipeline/scripts/pipeline-ctx.sh gitstate`
Diff summary:
!`~/.claude/pipeline/scripts/pipeline-ctx.sh diffstat`
Pipeline version (stamp in `Pipeline:`): !`~/.claude/pipeline/scripts/pipeline-ctx.sh version`

`Model:` is the exact model ID your system prompt states, or `unknown`.

Cross-check the list against your own account of what you edited. If they
disagree, git is right and your memory is wrong — say so in the report.

Weight the report toward §3 (divergences), §4 (spec claims that were wrong) and
§5 (decisions). Record nothing as verified that you did not run in this session.
Print the absolute path and full contents, then stop.
