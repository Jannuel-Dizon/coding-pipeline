---
description: Write the change report for the slice just built
---

<summary>
You MUST first confirm you are running as build, build-hard, or build-critical
— the agent that actually did the work. If you are plan, arch, ask, or
anything else, refuse and tell the human to switch to the build agent that
ran this slice. Do not write a report for work you didn't do.
You MUST write a change report for the work completed in this session.
You SHOULD record every file touched with its full path, and be exact about
what was and was not actually run.
You MUST print the report's absolute path and full contents, then stop.
</summary>

<stem>
$ARGUMENTS
</stem>

If you are not one of the three build agents, stop here — do not read the
rest of this command. A report is a claim that specific work was verified in
this session. An agent that never ran the build has nothing to verify and
nothing to report; writing one anyway would put an unearned claim into the
project's decision record.

Follow `.handoff/REPORT_TEMPLATE.md`. Write to
`.handoff/3-report/$ARGUMENTS.report.md`. Never overwrite an existing report:
if that file exists, stop and tell me.

Files changed in the working tree:
!`git status --porcelain`

Diff summary:
!`git diff --stat`

Pipeline version (stamp this in the header's `Pipeline:` field):
!`cat ~/.config/opencode/pipeline/VERSION 2>/dev/null || echo unknown`

Models configured, per build agent (copy the line for the agent you are
running as, verbatim, into `Model:`):
!`for a in build build-hard build-critical; do echo "$a: $(~/.config/opencode/pipeline/scripts/configured-model.sh $a)"; done`

Cross-check that list against your own account of what you edited. If they
disagree, the git output is right and your memory is wrong — say so in the
report.

Weight the report toward §3 (divergences), §4 (spec claims that were wrong),
and §5 (decisions you made). Those are the sections the next planning session
reads. Do not record anything as verified that you did not run in this session.
