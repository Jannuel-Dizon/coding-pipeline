---
description: Stage 3 — implement a spec (tier must match the current agent)
---

<summary>
You MUST check the spec's Tier header against your own tier before anything
else, and refuse if they do not match.
You SHOULD state your implementation plan and wait for an explicit go-ahead.
You MUST end by writing a report, printing its absolute path and full contents,
and stopping.
</summary>

<spec>
Load `.handoff/2-spec/$ARGUMENTS.spec.md` with your read tool before doing
anything else. (OpenCode V2 does not expand `@path` references inside command
templates, so the file is NOT already in your context.)

The spec may have been written by `arch` in OpenCode or by `/spec` in Claude
Code. Either is a valid build instruction; check `Status:` and `Tier:` the same
way.
</spec>

Available specs, if the stem above is wrong:
!`ls -t .handoff/2-spec/*.md 2>/dev/null | head -5`

Working tree state before you start:
!`git status --porcelain`

Tier routing: T1 → `build`, T2 → `build-hard`, T3 → `build-critical`. If the
spec's tier is not yours, stop and tell me which agent to switch to.

If the spec's Status is `replan` or `blocked`, stop — it is not a build
instruction.

Pipeline version (stamp this in the report header's `Pipeline:` field):
!`cat ~/.config/opencode/pipeline/VERSION 2>/dev/null || echo unknown`

Models configured, per build agent (when you write the report, copy the line
for the agent you are running as, verbatim, into `Model:`):
!`for a in build build-hard build-critical; do echo "$a: $(~/.config/opencode/pipeline/scripts/configured-model.sh $a)"; done`
