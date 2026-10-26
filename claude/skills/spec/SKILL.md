---
name: spec
description: Pipeline stages 1+2 in one pass — explore, plan and verify a slice, then write the spec to .handoff/2-spec/
argument-hint: <slice description | ticket ID | plan stem>
disable-model-invocation: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(~/.claude/pipeline/scripts/pipeline-ctx.sh *)
  - Edit(/.handoff/2-spec/**)
---

You are running the **spec** stage in Claude Code: pipeline stages 1 and 2 in
one pass. The shared rules (Rules 1–8, in `~/.claude/rules/pipeline.md`) and the
project's `AGENTS.md` apply unchanged. You write exactly one file — the spec —
and never touch source.

<request>
$ARGUMENTS
</request>

Date: !`~/.claude/pipeline/scripts/pipeline-ctx.sh date`
Pipeline version (stamp in `Pipeline:`): !`~/.claude/pipeline/scripts/pipeline-ctx.sh version`
Plans on disk (newest first):
!`~/.claude/pipeline/scripts/pipeline-ctx.sh plans 5`
Recent reports:
!`~/.claude/pipeline/scripts/pipeline-ctx.sh reports 3`
Ticket tracking:
!`~/.claude/pipeline/scripts/pipeline-ctx.sh tracking`

## 1. Work out which mode you are in

- **Verify mode** — the request is the stem of a plan in the list above (with or
  without `.plan.md`). Read that plan. The spec's stem is the plan's own `Stem:`
  header, never the raw argument. Set `Plan:` to the plan's path and delete §0.
  Resolve every ⚠ assumption.
- **Direct mode** — anything else. If the first word is a ticket ID and tracking
  is `yes`, read `.workitems/items/<ID>.md` (and `items/done/` if absent): its
  definition of done becomes your acceptance section and its dependencies carry
  over. Set `Plan: none (direct spec)` and fill §0 with the intent a plan would
  have held. Stem: `YYYY-MM-DD-<slice-slug>`, letters, digits and `-` only.

## 2. Settle intent (direct mode only)

State your reading of what is wanted, what is out of scope, and anything that
looks too big for one build pass. Ask only about what you cannot infer, in one
round. Do not start exploring until the human has answered or confirmed.

## 3. Explore and verify

Read `~/.claude/pipeline/shared/prompts/arch.md` and follow its "Your job",
"Context discipline", "Verification effort" and "Tiering" sections as written —
read "the architecture stage" as you, and `explore` as the `Explore` subagent.
Use `.handoff/MAP.md` if it exists (note its commit against `HEAD`). Send
searches to `Explore`; read a file yourself only when you need it closely. Mark
every claim **[read]**, **[ran]** or ⚠.

## 4. Write the spec

Follow `.handoff/SPEC_TEMPLATE.md`. `Model:` is the exact model ID your system
prompt states; if it states none, write `unknown`. Assign the tier with one
sentence of reasoning and run the T3 floor and narrowing checks (Rules 4, 4a).

## 5. Hand it over (Rule 1, Claude Code variant)

- **In plan mode:** present the complete spec through `ExitPlanMode`. After the
  human approves, write exactly the approved text to
  `.handoff/2-spec/<stem>.spec.md`, print its absolute path, and stop.
- **Not in plan mode:** print the complete draft, wait for the human to say to
  write it, then write the file, print its absolute path, and stop.

If the target file exists, stop and tell the human — never overwrite. End by
naming the tier and the session `/build <stem>` calls for. Do not build.
