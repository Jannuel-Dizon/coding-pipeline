# coding-pipeline

A staged development pipeline for **OpenCode and Claude Code**: **plan →
architecture/spec → build**, with a markdown document at every seam and a hard
stop between stages. The record lives in the project, not in either tool, so
you can run Claude Code until its weekly limit runs out, then carry on in
OpenCode on free models from the same files.

Version **2.0.0** (see `VERSION`; `CHANGELOG.md` has the migration notes).

## One record, two tools

Every project gets this layout, written by `/init` from either tool:

```
.handoff/        plan / spec / report documents, templates, MAP.md   (shared)
.workitems/      work item index; TRACKING.md says whether tickets are tracked (shared)
.opencode/       opencode.jsonc — per-project OpenCode overrides      (OpenCode)
.claude/         settings.json — per-project Claude Code settings     (Claude Code)
AGENTS.md        project facts, T3 floor (shared)    CLAUDE.md  → imports AGENTS.md
```

| Stage | OpenCode | Claude Code | Writes |
|---|---|---|---|
| 1 plan | `/plan` | (skipped — `/spec` does 1+2) | `.handoff/1-plan/<stem>.plan.md` |
| 2 spec | `/arch <stem>` | `/spec <slice \| ticket \| plan stem>` in plan mode | `.handoff/2-spec/<stem>.spec.md` |
| 3 build | `/build <stem>` on the tier's agent | `/build <stem>` on the tier's model | `.handoff/3-report/<stem>.report.md` |
| late report | `/handoff <stem>` | `/handoff <stem>` | same |
| helpers | `/ask` `/status` `/tickets` `/map` `/init` | `/ask` `/progress` `/tickets` `/map` `/init` | — |

In Claude Code only `/spec` writes the spec (explore + plan mode, written after
you approve the plan) and only the build session writes the report. A hook
(`claude/hooks/check-handoff-write.py`) rejects handoff writes with the wrong
name, a missing or placeholder header, or an overwrite. The `Pipeline:` and
`Model:` header fields record which tool and model produced each document, so a
spec from one tool is a valid build instruction in the other.

Which models run which stage is configuration, not documentation:
`opencode/opencode.jsonc` for OpenCode; in Claude Code you choose with `/model`
and `/build` tells you what the spec's tier calls for.

## Quick start

```sh
# 1. Clone once per device
git clone <your-fork-url> ~/dev/coding-pipeline
cd ~/dev/coding-pipeline

# 2. Global layer, once per device (idempotent; default is both tools)
./scripts/install-global.sh              # or --opencode / --claude
# OpenCode: symlinks ~/.config/opencode/{opencode.jsonc,AGENTS.md,prompts,
#   commands,templates,pipeline}; creates local-overrides.jsonc (never touched
#   again) and prints an OPENCODE_CONFIG line for your shell rc.
# Claude:   symlinks ~/.claude/pipeline, rules/pipeline.md, skills/*,
#   agents/Explore.md; merges the handoff guard into ~/.claude/settings.json
#   (backup first, nothing of yours is overwritten).

# 3. Project layer, once per repo — from either tool, or directly:
cd /path/to/your/repo
~/dev/coding-pipeline/scripts/init-project.sh        # or run /init in a tool
# Checks what already exists, creates only what is missing, never overwrites.
# Existing pre-2.0 layouts (.opencode/handoff, .opencode/workitems, ...) are
# flagged, and moved only with:  init-project.sh --migrate   (uses git mv)
# --dry-run shows what it would do.

# 4. Fill in AGENTS.md — especially the T3 floor (left as TODO on purpose)
# 5. Run /map once to generate .handoff/MAP.md
```

Updating any device afterwards is `cd ~/dev/coding-pipeline && git pull`.

**Per-project overrides.** `.opencode/opencode.jsonc` (models, permissions) and
`.claude/settings.json` (permissions; see `project/claude-settings.json.example`)
are real files owned by the project. Everything else is a symlink into the clone
and updates on pull.

Then, in Claude Code: `/spec <what you want>` (in plan mode) → approve →
`/build <stem>` → `/handoff <stem>` if needed. In OpenCode:
`/plan <what you want>` → read the doc → `/arch <stem>` → read the doc → Tab to
the agent the tier names → `/build <stem>` → `/handoff <stem>`.

`/ask <question>` works from any tab, any time, for something not worth
interrupting that flow for. `/status [scope]` and `/tickets [filter]` are the
same idea, aimed specifically at the handoff record and the work item index.

## The agents

| Agent | Stage | Default model | Can it edit source? |
|---|---|---|---|
| `plan` | 1 | DeepSeek V4 Flash **(free)** | No — only `handoff/1-plan/` |
| `design` | 1 | DeepSeek V4 Flash **(free)** | No — only `handoff/1-plan/` |
| `arch` | 2 | DeepSeek V4 Flash | No — only `handoff/2-spec/` |
| `build` | 3 · T1 | DeepSeek V4 Flash **(free)** | Yes, on approval |
| `build-hard` | 3 · T2 | DeepSeek V4 Flash | Yes, on approval |
| `build-critical` | 3 · T3 | Claude Opus 5 | Yes, per-edit approval |
| `explore` | subagent | DeepSeek V4 Flash | No — read-only |
| `ask` | outside the pipeline | DeepSeek V4 Flash **(free)** | No — read-only |

**Why the stage-1 agent is called `design`, not `plan`.** `plan` is a
reserved agent name in OpenCode and carries a built-in read-only mode
that overrides an agent's own `permission` block. An agent named `plan`
therefore cannot write its own plan document — the one write the stage
exists to perform. The agent is `design`; the stage is still "plan," the
command is still `/plan`, and documents still stamp `Stage: plan`. Only
the agent key differs.

`build-critical` is deliberately the one agent that stays on a frontier model.
It is also the rarest and the narrowest — a binding file list, per-edit
approval, so its context stays small and it contributes very little to the
bill. Downgrading it saves cents per slice and spends them on the one tier
where a wrong answer is a bricked device rather than a failed build.

**As of 1.6.0, `arch` runs on DeepSeek V4 Flash rather than V4 Pro.** DeepSeek's
officially retrained Flash (July 31, 2026) now matches or beats Pro-Preview on
the agent benchmarks DeepSeek publishes, at roughly a third of the price —
see the 1.6.0 entry in `CHANGELOG.md` for the numbers and the caveats on how
much to trust them. This is the pipeline's own team consolidating on one
vendor for cost reasons rather than a verified quality upgrade; if you run
`arch` on real slices and its specs start missing things V4 Pro used to catch,
that is useful signal — pin `arch` back to `opencode/deepseek-v4-pro` in your
project's `opencode.jsonc` and it stops inheriting the global default.

Tab switches between primary agents. Models are OpenCode Zen ids; swap them for
any provider by editing the `model` field.

**On the free-tier defaults (`design`, `build`, `ask`):** OpenCode Zen's free
models carry a data-retention caveat the paid tier doesn't — submitted content
may be used to improve the model. These three roles default there because
each is either structurally blind to your source (`design` cannot read
implementation bodies at all), read-only and low-stakes (`ask`), or bounded
by an already-verified spec (`build`, T1). `arch`, `build-hard`, and `explore`
deliberately do **not** default to the free tier, because they do handle real
source, and on proprietary code the zero-retention guarantee of the paid tier
is usually worth the extra fraction of a cent per slice. Decide this per
project, not by leaving the default unexamined.

## Two design choices worth understanding

### The planner cannot read implementation bodies

Deliberate. A planner that reads the current implementation starts designing
the next slice to resemble it, and stops designing. It can read manifests,
docs, public entry points (`lib.rs`, `mod.rs`, `index.ts`, `__init__.py`) and
the whole handoff history — enough to know what exists, not enough to be
anchored by how it works.

It does not produce a list of things for the architect to grep. It produces
**assumptions and open questions**; the architect owns retrieval strategy and
decides how to verify them. That division is the point.

`grep` is denied for the planner as well as `read`, because grep returns
content lines and would otherwise be a way around the restriction. `glob` is
allowed — it returns paths only.

If this is too tight for a given project, loosen it in the project layer. Be
aware of what you are trading away.

### Tiers escalate but never de-escalate

The architect assigns T1, T2, or T3 to every slice and states why in one
sentence. The project's `AGENTS.md` defines a **T3 floor** — paths and concerns
that are always critical no matter how small the diff. The architect can raise
a slice above its floor on judgment; it cannot lower one below, and it cannot
split a slice so part of it escapes.

Build agents check the tier in the spec header before doing anything and refuse
work that is not theirs. `build-critical` requires per-edit approval, a binding
file list, and a written adversarial pass before any code is written.

**Fill in the T3 floor yourself.** `/init` deliberately leaves it as
TODO. An agent guessing at what is safety-critical in your project defeats the
purpose of having a floor at all.

## The stop-and-print rule

Every stage ends by writing its document, printing the absolute path, printing
the full contents, and halting. No stage advances to the next on its own.

This is the load-bearing rule. When planning and building lived in separate
tools, the tool boundary forced you to read each document. In one TUI it is
easy to Tab straight through without reading anything, and then the handoff
documents become an audit trail nobody audits. The pause is the only checkpoint
in the pipeline.

## Global and project layers

**Global** (`~/.config/opencode/`) is process: agent prompts, tier definitions,
commands, templates. Project-agnostic, applies to every repo on your machine.

**Project** (`.opencode/`) is facts: module map, T3 floor, check commands,
conventions, cross-boundary contracts, model overrides.

Config merges global → project, with project winning per key. That is fine for
settings but ambiguous for agent definitions, so:

> **If a repo's `opencode.json` defines agents at all, it defines all six.**

Partial overrides give you one agent name with two definitions and no clear
signal about which one ran. Repos that do not need overrides should simply not
have an `agent` block, and inherit global wholesale.

Every handoff document stamps `Pipeline: <version>` in its header. When a
document from six months ago reads strangely, that line tells you which process
version produced it.

## Cost

Cost is context size × turns, not how often you invoke an agent. The planner is
the most-used stage and among the cheapest, because it never loads source. The
architect used to be the expensive one because it reads the whole codebase —
as of 1.6.0 it's on the same cheap Flash tier as everything else except
`build-critical`, so the biggest remaining cost lever is elsewhere now.

The levers, in order of effect:

0. **Pick the tier down.** Still the biggest lever if you're pinning your own
   models: `arch` on a frontier model reading a whole codebase is where most
   of a slice's cost used to land before 1.6.0. If you've overridden `arch`
   back to a frontier model in your project config, moving it to a strong
   mid-tier model typically cuts a full plan→arch→build pass by several
   times over — that was the whole rationale for the 1.5.0 and 1.6.0 defaults.

1. **Scope the architect.** Give it a slice and a file list, not "look at the
   repo".
2. **Use `explore`.** It reads on a cheap model and returns prose. A file the
   architect pulls into its own context is re-billed on every subsequent turn
   of that session; a question delegated to `explore` is billed once, cheaply.
3. **Keep `MAP.md` short.** Under 200 lines. The planner reads it every
   session.
4. **Keep T3 narrow.** Narrow scope is simultaneously the safety property and
   the cost control.

### DeepSeek peak vs off-peak

DeepSeek V4 Flash and Pro are billed at **half price outside peak hours**.
Peak is 01:00–04:00 and 06:00–10:00 UTC. Convert that to your own timezone
before assuming it doesn't matter — for UTC+8, peak lands on roughly
09:00–12:00 and 14:00–18:00 local, which is precisely the working day. A long
architecture session moved to late afternoon or evening costs half what the
same session costs mid-morning. This matters more as of 1.6.0 than it did
before — `arch` is now one of the two DeepSeek-billed stages (alongside
`build-hard`) instead of running on a flat-rate frontier model, so its cost
actually responds to when you run it.

The $0.22 figure was measured during DeepSeek's *peak* window (08:27–09:17
UTC); the $3.50 baseline's build stage ran off-peak at half price. The
like-for-like gap is therefore wider than 15×, not narrower.

### On free-tier models

Zen's free models — including DeepSeek V4 Flash Free — carry a data-retention
caveat the paid tier does not: during the free period, submitted data may be
used to improve the model. Everything else on Zen is zero-retention.

That is a per-project judgement, not a universal answer. For `ask` (read-only,
no artifacts) and for T1 work on a hobby project it is usually fine. For T1
work on proprietary code it means your source is leaving the zero-retention
boundary for a saving of a fraction of a cent per slice — worth deciding
deliberately rather than inheriting. Switching `build` to the paid
`opencode/deepseek-v4-flash` is a one-line change.

Other Zen free-tier models exist beyond DeepSeek's (Laguna S 2.1, Nemotron 3
Ultra, MiMo-V2.5, Hy3, and the unidentified "Big Pickle") and some — Laguna S
2.1 in particular — publish benchmark claims competitive with DeepSeek V4
Flash on coding-specific suites. None of them have been run against real
slices in this pipeline as of 1.6.0. If you evaluate one, do it the same way
1.5.0's retiering was decided: measure a real plan→arch→build pass, don't
retier off a vendor chart alone.

## Files

```
shared/                         used by both tools
  AGENTS.md                     rules that apply to every stage
  prompts/                      one system prompt per stage / agent
  templates/                    the three handoff templates
opencode/                       → ~/.config/opencode/
  opencode.jsonc                seven agents: models and permissions
  commands/                     /plan /arch /build /handoff /map /init /ask /tickets /status
claude/                         → ~/.claude/
  skills/                       /spec /build /handoff /ask /progress /tickets /map /init
  agents/Explore.md             generated from shared/prompts/explore.md
  hooks/, settings.pipeline.json  handoff write guard and its settings entry
project/                        examples copied into each repo by /init
  opencode.jsonc.example        → .opencode/opencode.jsonc
  claude-settings.json.example  → .claude/settings.json
  AGENTS.md.example, CLAUDE.md.example
scripts/
  install-global.sh             one-time per-device setup: symlinks both tools in
  init-project.sh               per-project setup for both tools (idempotent; --migrate, --dry-run)
  install-global.sh             per-device setup (--opencode / --claude)
  pipeline-ctx.sh               read-only context helper the Claude skills call
  configured-model.sh           reads the configured model for an OpenCode agent
  build-explore-agent.sh        generates claude/agents/Explore.md from the shared explore prompt
  merge-claude-settings.py      merges the hook into ~/.claude/settings.json safely
  ingest-workitems.py           task tracker(s) -> .workitems/ (html, csv/sheets, appflowy — combinable)
```

**On file extensions:** `.jsonc` (not `.json`) throughout this template,
specifically so real comments (`// like this`) are safe to use. A JSON object
key literally named `"//"` is *not* a comment in either format — it's a real
property name, and OpenCode's `permission` schema validates every key inside
a `permission` block strictly, so a `"//"` key there fails to load. Don't
reintroduce that pattern; use `.jsonc` and a real `//` comment line instead.

## Updating across devices and projects

Setup is covered in [Quick start](#quick-start) above — this section is just
the mechanics of what happens on a version bump, once that's done.

### What updates automatically vs. what needs a manual pass

| File | Updates on `git pull`? |
|---|---|
| Global `opencode.jsonc`, `AGENTS.md`, `prompts/`, `commands/`, `templates/` | Yes — pure process |
| Project handoff templates (`*_TEMPLATE.md`) | Yes — pure process |
| Project `opencode.jsonc` (the filled instance) | No — has to hold real facts, edit by hand |
| Project `AGENTS.md` (the filled instance) | No — same reason |

A version bump that only touches prompts, commands, or templates needs zero
action from you beyond the `git pull`. A version bump that changes something
structural in `opencode.json` itself — a new agent, a changed permission
default — is worth a quick look at what changed and a manual decision about
whether to port it into each project's filled config. The `CHANGELOG.md` in
this repo (start one if you haven't) is the right place to flag which kind of
change a release is, so you're not diffing blind.

### On other machines

The same clone-and-link steps apply to any machine — laptop, work desktop,
wherever. Each device needs its own clone and its own one-time
`install-global.sh` run, but after that, `git pull` on that device's clone is
the entire update procedure, same as any other machine tracking the same repo.

## Work items

Tickets live in whatever your team uses — AppFlowy, a shared HTML file, a
Google Sheet, more than one of those at once. The pipeline does not read any
of them directly. `scripts/ingest-workitems.py` converts one or several
sources into a canonical tree:

```
.workitems/
├── WORKITEMS.md          compact index — the planner and /tickets read this
└── items/<ID>.md         full detail — read on demand when planning that item
```

Two tiers for the same reason `MAP.md` is capped: a full breakdown can be
20k tokens, too much to re-read every session. The index is a few KB; the
detail file is pulled only for the item actually being planned.

### Sources

Three so far, and they combine — use one or all three in the same run:

```sh
# shared HTML breakdown
./scripts/ingest-workitems.py --from-html BREAKDOWN.html --out .workitems

# CSV / TSV export, or a published Google Sheet URL
./scripts/ingest-workitems.py --from-csv sheet.tsv --out .workitems
./scripts/ingest-workitems.py --from-csv "https://docs.google.com/.../pub?output=csv" \
    --out .workitems

# AppFlowy — discover first, then configure, then pull
export APPFLOWY_URL=https://tasks.example.com
export APPFLOWY_EMAIL=you@example.com APPFLOWY_PASSWORD=...
./scripts/ingest-workitems.py --from-appflowy --list-databases
./scripts/ingest-workitems.py --from-appflowy --database <id> --list-fields
./scripts/ingest-workitems.py --from-appflowy --config .workitems/appflowy.json \
    --out .workitems
```

**Combine them in one run** when different sources hold different parts of
the truth — e.g. a detailed HTML spec plus a sheet that tracks live status:

```sh
./scripts/ingest-workitems.py \
  --from-html BREAKDOWN.html \        # technical detail, DOD, dependencies
  --from-csv sheet.tsv \              # hierarchy, user stories, owner, SP
  --out .workitems
```

Merge order matters — **first non-empty value per field wins**, so list your
richest source first and thinner overlays (a live status board, say) after
it. Every item file records which source(s) it came from, so a surprising
value is traceable rather than mysterious.

Adding a new source means writing one function that returns the same dicts.
Nothing downstream — the templates, the commands, the agents — changes.

### Handling inconsistent formats

Real trackers don't agree on column names project to project. Three knobs
absorb that without touching the script:

- **Header matching is fuzzy** — case, spacing, and punctuation are ignored,
  and common fields have aliases built in (`SP`/`Points`/`Story Points`;
  `Deps`/`Dependencies`/`Blocked by`; `Owner`/`Assignee`).
- **`--id-pattern`** for non-default ID schemes. `E1-S1-T1` style is the
  default; `--id-pattern '\b[A-Z]{2,}-[A-Z]+-\d+\b'` matches something like
  `BV-SETUP-001` instead.
- **`--id-column`** when the identifier isn't under a column literally named
  ID — common on kanban-style boards where the primary text field doubles as
  the key. Without it, the parser falls back to scanning each row for
  anything matching `--id-pattern`.

### Hierarchy — epic / story / task

`--from-csv` understands a `Level` column (`EPIC`/`STORY`/`TASK`), or infers
depth from the ID's own dash-count if there isn't one. Only TASK-level rows
become work items — that's the buildable unit — but each task's **parent
story is folded in as context**, because the story row is usually where the
actual user story lives ("As a DM Server, I want ... so that ...") and the
task row is often just a title. That intent lands in the generated item file
under **Why — parent story**, above the technical detail, so the planner
sees why the task exists, not only what it says.

### Why materialise rather than let agents fetch live

The planner has `bash` and `webfetch` denied on purpose — the read wall is
what keeps it designing rather than describing. Beyond that: a plan that
references a ticket which has since changed records nothing about *which*
version it was planned against, re-fetching costs tokens on every session,
and a network dependency breaks offline. The generated files carry a source
hash, so a stale snapshot is visible instead of silent.

`ask` is the exception worth making — a live connector there is genuinely
useful for throwaway "what's still open" questions that shouldn't require
regenerating anything. Note that a source can be live-only and still useful
that way even if it's too thin to plan from — a kanban board with just an ID
and a status column tells `/tickets` what's in progress right now, even
though `--from-html` or `--from-csv` is doing the actual content.

### Story points are not tiers

The one mapping to never make. Points measure **effort**; tiers measure
**blast radius**. A 1-point change to signature verification is T3. An
8-point mechanical refactor across twenty files is T1. Points legitimately
inform *slicing* — an 8-pointer usually wants splitting before planning —
and nothing else. The generated index says so in its own header, and
`/tickets` is instructed never to infer a tier from points.

### The flow

`/tickets <filter>` browses the index on the cheap `ask` agent and reports
candidates, leading with what is unblocked. It cannot plan and cannot switch
agents — you pick. Then `/plan <ID> <what you want>` starts the pipeline
normally. The ticket's definition-of-done carries into the spec's acceptance
section; its dependencies carry into the plan's; its parent story's user
story carries into the plan's own intent section.

`/status [scope]` is the same idea pointed at the *pipeline's own* history —
what's been planned, specced, and actually built, distinguishing `complete`
from `partial`/`stopped`/still-in-progress rather than rounding everything
up to "done". It's a summary for the conversation, not a new record: if a
status write-up should persist, that's what `/handoff` and a real report are
for. Letting a convenient Q&A answer quietly become a second, informal
decision record is exactly the failure mode the stop-and-print discipline
elsewhere in this pipeline exists to prevent — `ask` deliberately can't
write files at all, so this can't happen by accident.

### Rerunning as tickets change

Rerun the same command whenever tickets are added, edited, or finished — it's
a full regeneration from the source(s), not an incremental diff, so there's
no separate "sync" step:

```sh
./scripts/ingest-workitems.py --from-html BREAKDOWN.html --out .workitems
```

Added and changed tickets just show up correctly. Removed tickets (finished
and taken off the board, deleted, renamed) have their `items/<ID>.md` deleted
too — the index and the detail files always move together.

If a rerun would remove an unusually large share of what's currently on disk
(≥5 items and ≥40% of the total), it refuses and lists what it *would* have
removed instead of deleting anything. That pattern is far more often a
`--from-*` flag left off a multi-source command than that many tickets
actually vanishing at once — confirm with `--force-prune` if the removal is
genuinely real.

Since the output is committed, `git diff` after a rerun is the actual
audit trail: added items are new files, finished ones show a status change,
removed ones show as deletions.

### One tracker doesn't mean one output

If different boards genuinely track different projects, run the ingester
once per project with a different `--out`. Merging is for combining sources
that describe the *same* work; it isn't for combining unrelated work into one
index just because it's convenient to fetch in one pass.

## Adapting it

Written with a Rust workspace in mind, but nothing is Rust-specific except some
default glob patterns. To port it, change three things in the project layer:

1. **Planner read globs** — deny your source extensions, allow your public
   entry points.
2. **Check and build commands** in `AGENTS.md` and the build agents' bash
   permissions.
3. **The T3 floor** — what is unrecoverable in *this* system.
