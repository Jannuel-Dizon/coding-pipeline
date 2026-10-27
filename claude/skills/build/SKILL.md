---
name: build
description: Pipeline stage 3 — implement a spec at its tier's standard, or a small direct change with no spec, then write the report to .handoff/3-report/
argument-hint: <stem or short description of the change>
disable-model-invocation: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(~/.claude/pipeline/scripts/pipeline-ctx.sh *)
  - Edit(/.handoff/3-report/**)
---

You are running the **build** stage in Claude Code. The shared rules (Rules 1–8,
in `~/.claude/rules/pipeline.md`) and the project's `AGENTS.md` apply unchanged.
The spec may have been written by `/spec` here or by `arch` in OpenCode; either
is a valid build instruction. A spec is optional: for a small change with no
spec, the request itself is the instruction (see step 1).

<stem>
$ARGUMENTS
</stem>

Specs on disk (newest first):
!`~/.claude/pipeline/scripts/pipeline-ctx.sh specs 5`
Working tree before you start:
!`~/.claude/pipeline/scripts/pipeline-ctx.sh gitstate`
Pipeline version (stamp in `Pipeline:`): !`~/.claude/pipeline/scripts/pipeline-ctx.sh version`

## 1. Find the build instruction

- **A spec exists.** If `$ARGUMENTS` names a spec (`.handoff/2-spec/$ARGUMENTS.spec.md`
  resolves, or it matches one in the list above), read it. If `Status:` is
  `replan` or `blocked`, stop — it is not a build instruction. Otherwise this is a
  **spec build**; continue to step 2.
- **No spec.** If nothing resolves, or `$ARGUMENTS` is a plain description of the
  change rather than a stem, this is a **direct build**. The human's request is
  the instruction. Do not stop for lack of a spec. Then:
  1. Read the target files yourself, only as much as the change needs.
  2. Assign a tier with the Rule 4 table and the project's T3 floor, taking the
     highest tier that applies. Record it in the report.
  3. **Escalate instead of building** if any of these hold: the tier is T2 or T3;
     the change touches more than a few obviously related files; it adds a
     dependency (Rule 6); it needs agreement with a system you don't own (Rule 5);
     it involves a design decision the request doesn't settle; or you cannot name
     the most likely reading of the request. In that case, tell the human to run
     `/spec` for it and stop.
  4. Otherwise, derive the stem as `YYYY-MM-DD-<short-slug>` from today's date and
     the change, and say which reading of the request you took.

## 2. Match the session to the tier

Say the tier (the spec's, or your assigned one for a direct build) and its
meaning from the Rule 4 table — T1 routine, T2 hard, T3 critical — then get
the normal go-ahead before doing anything else. The tier's meaning is the
recommendation; the human has already decided which model and thinking level
this session runs on. Ask nothing about model or thinking level and do not
suggest one; the report's `Model:` header records what actually ran. For T3
only, also confirm manual edit approval is active — manual, not accept-edits
or auto.

Then read the file for the tier and follow it as your operating instructions
for this stage: `~/.claude/pipeline/shared/prompts/build.md` (T1),
`build-hard.md` (T2) or `build-critical.md` (T3). Where it says "agent", it
means you; where it says to switch agent, tell the human to switch model or
session instead. Its scope contract, adversarial pass, stop-and-ask rules and
honesty rules are binding. For a direct build, the scope contract is the human's
request as you restated it in step 1.

## 3. Build

State what you will touch and in what order, and wait for an explicit go-ahead
(Rule 3). Send lookups to the `Explore` subagent. Run the check command from
`AGENTS.md` and report exactly what ran and what came back.

## 4. Report

Write `.handoff/3-report/<stem>.report.md` from `.handoff/REPORT_TEMPLATE.md`,
`Spec:` pointing at the spec you built, or `none (direct build)` with §0 recording
the request, the reading you took, and the tier you assigned. `Model:` is the exact model ID your
system prompt states, or `unknown`. Cross-check §1 against the working tree
(`gitstate`, `diffstat`); where they disagree, git is right. Weight the report
toward divergences, wrong spec claims and decisions. Print the absolute path and
the full contents (Rule 1) and stop. If the session ends before a report exists,
`/handoff <stem>` writes it afterwards.
