---
name: build
description: Pipeline stage 3 — implement a spec at its tier's standard, then write the report to .handoff/3-report/
argument-hint: <stem>
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
is a valid build instruction.

<stem>
$ARGUMENTS
</stem>

Specs on disk (newest first):
!`~/.claude/pipeline/scripts/pipeline-ctx.sh specs 5`
Working tree before you start:
!`~/.claude/pipeline/scripts/pipeline-ctx.sh gitstate`
Pipeline version (stamp in `Pipeline:`): !`~/.claude/pipeline/scripts/pipeline-ctx.sh version`

## 1. Read the spec and gate on it

Read `.handoff/2-spec/$ARGUMENTS.spec.md` (pick from the list above if the name
does not resolve). If `Status:` is `replan` or `blocked`, stop — it is not a
build instruction.

## 2. Match the session to the tier

Say the spec's tier and what it calls for, then ask the human to confirm the
session matches before you do anything else. These are recommendations; the
human chooses (`/model` switches):

| Tier | Session |
|---|---|
| T1 routine | Sonnet, normal effort |
| T2 hard | Sonnet at high effort, or Opus |
| T3 critical | Opus, high effort, **manual edit approval — not accept-edits or auto** |

Then read the file for the tier and follow it as your operating instructions
for this stage: `~/.claude/pipeline/shared/prompts/build.md` (T1),
`build-hard.md` (T2) or `build-critical.md` (T3). Where it says "agent", it
means you; where it says to switch agent, tell the human to switch model or
session instead. Its scope contract, adversarial pass, stop-and-ask rules and
honesty rules are binding.

## 3. Build

State what you will touch and in what order, and wait for an explicit go-ahead
(Rule 3). Send lookups to the `Explore` subagent. Run the check command from
`AGENTS.md` and report exactly what ran and what came back.

## 4. Report

Write `.handoff/3-report/<stem>.report.md` from `.handoff/REPORT_TEMPLATE.md`,
`Spec:` pointing at the spec you built. `Model:` is the exact model ID your
system prompt states, or `unknown`. Cross-check §1 against the working tree
(`gitstate`, `diffstat`); where they disagree, git is right. Weight the report
toward divergences, wrong spec claims and decisions. Print the absolute path and
the full contents (Rule 1) and stop. If the session ends before a report exists,
`/handoff <stem>` writes it afterwards.
