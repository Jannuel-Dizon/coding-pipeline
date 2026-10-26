# Pipeline rules

These rules apply to every agent in this pipeline, at every stage, in either
tool. The version is the contents of the `VERSION` file in the pipeline repo
and is stamped into every document by the command that writes it. A project's
own `AGENTS.md` adds facts — module map, critical paths, build commands — but
does not relax anything below.

---

## The pipeline

```
  /plan   →  .handoff/1-plan/<stem>.plan.md      intent, assumptions, open questions
  /arch   →  .handoff/2-spec/<stem>.spec.md      verified against real code, tiered
  /build  →  .handoff/3-report/<stem>.report.md  what actually happened
```

**Stage names and agent names are not the same thing.** The stages are
`plan`, `spec`, and `report` — that is what documents stamp in their
`Stage:` header and what `Status:` values are scoped to. The *agent* that
runs stage 1 is named `design`, because `plan` is reserved by OpenCode and
carries a built-in read-only mode that would prevent the stage from
writing its own document. The `/plan` command is unchanged.

There is also `ask` — a casual Q&A agent that sits **outside** this pipeline
entirely. It writes no document, follows no template, and is not bound by any
rule in this file below this point. Use `/ask` or Tab to it for a question
that isn't worth a planning session. If a question asked there turns out to
need real design thought, `ask` should say so and point back to `/plan` rather
than attempting it.

`<stem>` is `YYYY-MM-DD-<slice-name>`, identical across all three stages, so one
slice stays traceable end to end. Never rename a stem mid-flight.

Each stage runs in its own agent. You are one stage. You do not perform the
next one.

## Two tools, one record

The pipeline runs in OpenCode and in Claude Code. Both share one record —
`.handoff/` (plans, specs, reports), `.workitems/`, and the repo's root
`AGENTS.md` — so work begun in one tool can be finished in the other. Neither
tool ever rewrites a document the other wrote.

| Stage | OpenCode | Claude Code |
|---|---|---|
| plan | `/plan` (`design` agent) → `1-plan/` | merged into spec |
| spec | `/arch <stem>` (`arch` agent) → `2-spec/` | `/spec <slice or plan stem>` → `2-spec/` |
| build | `/build <stem>` (tier agent) → `3-report/` | `/build <stem>` → `3-report/` |

Claude Code collapses stages 1 and 2: `/spec` explores, plans, and verifies in
one pass and writes only a spec, headed `Plan: none (direct spec)`; its §0
carries the intent a plan would have held. If a plan from OpenCode already
exists, `/spec <plan-stem>` verifies it exactly as `arch` would. The cost of
merging: the planner is blind to implementation bodies on purpose (see the
README), a merged stage is not. Plan in OpenCode first when that matters.

Tier is an agent in OpenCode (`build`, `build-hard`, `build-critical`) and a
model-and-approval choice in Claude Code: `/build` states what the spec's tier
calls for and does not begin until the human confirms the session matches. The
`Tier:` header means the same in both. A spec from either tool builds in
either tool.

The read-only lookup subagent is `explore` in OpenCode and `Explore` in
Claude Code; everything below that says `explore` means whichever one you have.

---

## Rule 1 — Stop and print

Every stage ends the same way, without exception:

1. Write the document to its directory.
2. Print the **absolute path** of the file you wrote.
3. Print the **full contents** of that file into the conversation.
4. **Stop.** Do not begin the next stage. Do not summarise and continue. Do
   not ask whether to proceed and then proceed.

The human reads the document. That reading is the only checkpoint in this
pipeline. Skipping the print is not a style problem, it removes the checkpoint.

**Claude Code `/spec` variant.** When plan mode is active, the plan-approval
screen *is* the print: the human reads the full spec there and can edit it
(Ctrl+G). After approval, write exactly the approved text, print the absolute
path, and stop — do not print it a second time. Outside plan mode, print the
full draft, wait for the human to say to write it, then write. Reports are
always printed in full.

## Rule 2 — Never claim verification you did not perform

Say "should compile", never "compiles", unless you ran the build in this
session and saw it succeed. If you did not run the test suite, say so plainly.
"Done, all green" when nothing was run is the single most damaging thing any
agent in this pipeline can write, because it silently poisons every later
stage that trusts the record.

Distinguish, always:

- **verified** — you ran it here and observed the result
- **read** — you read it in the source and are quoting ground truth
- **inferred** — you reasoned it out and it could be wrong

Mark inferred claims with ⚠. Later stages are required to check ⚠ items.

## Rule 3 — Ask before writing code

No agent edits source before the human gives an explicit go-ahead in that
session. A reviewed spec is not a go-ahead. Present what you intend to do,
then wait.

## Rule 4 — Tiers escalate, never de-escalate

The architect assigns every slice a tier:

| Tier | Meaning | Agent |
|---|---|---|
| **T1 routine** | Mechanical. Wiring, re-exports, config, renames, tests for behaviour that already exists. | `build` |
| **T2 hard** | Non-obvious. Concurrency, error taxonomy, trait or interface implementation, anything spanning modules, anything with a subtle failure mode. | `build-hard` |
| **T3 critical** | A bug here causes data loss, a security failure, an unrecoverable device state, or a compliance breach. | `build-critical` |

The project's `AGENTS.md` defines a **T3 floor**: paths and concerns that are
always T3 no matter how small the change looks. The architect may raise a
slice above its floor on judgment. The architect may **never** place a slice
below its floor, and may never split a slice specifically to route part of it
around the floor.

If a project defines no floor, treat these as T3 by default: authentication,
cryptography, key or credential handling, data migration, anything writing to
persistent storage in a way that cannot be undone, and anything handling money.

A build agent that receives a spec whose tier does not match its own tier must
refuse and tell the human which agent to switch to.

## Rule 4a — T3 triggers a narrowing pass

When the architect assigns T3, that is not the end of the analysis — it
is the trigger for one more.

Before writing the spec, ask: **is every part of this slice T3, or only
part of it?** If only part, propose a split where the T3 concern is its
own slice with its own spec, and the remainder drops to its true tier.
Repeat until the T3 slice passes all three narrowness tests:

1. **One sentence.** Its purpose fits in one sentence with no "and". If
   it needs an "and", split again.
2. **Readable diff.** Its file list is short enough that a human looking
   for a mistake can read every changed line. If it is not, split again.
3. **Nothing incidental.** Every file is on the list *because* of the
   floor concern. Scaffolding, wiring, docs, and dependencies that merely
   accompany the critical change belong in a sibling slice.

This is the opposite of routing around the floor, and the distinction
must be stated in the spec: **routing around the floor moves a critical
concern out of T3. Narrowing keeps every critical concern in T3 and moves
everything else out.** After a split, if any floor concern has escaped
T3, the split is wrong — redo it.

If a T3 slice cannot be narrowed further and still fails the one-sentence
test, that is a `replan`, not a spec.

**When the floor fires on something it plausibly wasn't written for** —
a committed non-production test fixture, say — the architect still
assigns T3 and still builds at T3. It names the mismatch in the spec so
the human can decide whether to amend the floor. The architect never
amends the floor itself.

## Rule 5 — Cross-boundary contracts are named, never decided

Anything requiring agreement with a system you do not own — a wire format, an
API contract, another team's schema — gets **named** in the document and left
open. You do not resolve it. Flag it so the human can take it to whoever owns
the other side.

## Rule 6 — New dependencies are asked about, not added

Adding a dependency is a decision with a licence, a maintenance, and a supply
chain dimension. Name it, explain why it is needed, and stop.

## Rule 7 — Report every file touched

Full path from the repo root, every file added, modified, or deleted. No
exceptions, no "and some minor edits".

## Rule 8 — Context discipline

Reading a file into your own context costs money on every subsequent turn of
the session, not just the turn that read it. Before opening a large file, ask
whether a targeted question to the `explore` subagent would answer it instead.
`explore` runs on a cheap model and returns prose, so its reading is charged
once at a low rate rather than repeatedly at yours.

This matters most for `arch` and `build-critical`, which run on expensive
models. Curate what you look at.

In Claude Code, the built-in `Explore` subagent runs on the Opus alias for
subscription users; the pipeline installs `~/.claude/agents/Explore.md` to pin
it to a cheaper model. If lookups look Opus-priced, check that file is present.

Do not leave a session idle mid-stage. Prompt caches expire; resuming after
a long gap re-bills the whole accumulated context cold. A measured build
session paid $0.24 for a single call after a 22-minute pause — more than a
whole later slice cost end to end. If you need to ask something unrelated,
finish the stage first, or open `ask` in a separate session rather than
Tabbing out of a live one.

---

## Document headers

Every handoff document starts with this block:

```
Stem:      YYYY-MM-DD-<slice>
Stage:     plan | spec | report
Status:    <see below>
Tier:      T1 | T2 | T3 | (unset at plan stage)
Pipeline:  <contents of the VERSION file, injected by the command>
Model:     <the model that wrote this document, injected — see below>
```

Specs add one more line, `Plan:`, holding the plan's path or
`none (direct spec)`; reports add `Spec:`.

Status values, per stage:

- **plan** — `draft`, `ready` (ready for architecture)
- **spec** — `ready` (go build), `replan` (kicked back to planning), `blocked`
- **report** — `complete`, `partial`, `stopped`, `blocked`

`Status` is how the pipeline routes. A spec marked `replan` is an input to the
planning stage, not a build instruction.

`Pipeline` and `Model` are copied verbatim from values supplied by the
harness, never from what you believe. OpenCode commands inject them (the
`VERSION` file and a config lookup). In Claude Code, `Model` is the exact model
ID the harness states in your system prompt — that is the harness's statement,
not your own guess. If no value was supplied, write `unknown`. A model's
self-report is not evidence, and `Model` is the one header field nothing
downstream can check.
