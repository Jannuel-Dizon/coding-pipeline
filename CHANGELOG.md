# Changelog

Each entry notes whether the change is safe to pull automatically (pure
process — prompts, commands, templates) or needs a manual look at each
project's filled `opencode.jsonc` / `AGENTS.md` (structural — new agents,
changed defaults, changed permission shape).

## 2.0.0

**Structural — manual step required per project.** The handoff record and work
items move out of `.opencode/` so OpenCode and Claude Code share them, and a
Claude Code pipeline is added.

- **Repo renamed `coding-pipeline`; `global/` split** into `shared/` (AGENTS.md, prompts, templates, used by both tools) and `opencode/` (opencode.jsonc, commands). Re-run `install-global.sh` once to repoint the symlinks.
- **New layout.** `.handoff/` (plan/spec/report, templates, `MAP.md`),
  `.workitems/` (with `TRACKING.md`: `Tracking: yes|none`), `.opencode/`,
  `.claude/`. Prompts, commands, templates and scribe permissions all use the
  new paths. Migrate an existing project with
  `scripts/init-project.sh --migrate` (`--dry-run` first); it never moves
  anything without the flag. Projects with their own `agent` permission block
  that names `.opencode/handoff/**` must change it to `.handoff/**` by hand.
- **Claude Code pipeline.** Skills `/spec`, `/build`, `/handoff`, `/ask`,
  `/progress`, `/tickets`, `/map`, `/init` (`claude/skills/`); a custom
  `Explore` subagent on Haiku built from the shared explore prompt; shared rules
  imported through `~/.claude/rules/pipeline.md`; a PreToolUse guard on handoff
  writes. Only `/spec` writes specs and only the build session writes reports.
- **`/init` in both tools** runs `scripts/init-project.sh`, which checks for
  existing files first and only creates what is missing.
- `install-global.sh` takes `--opencode` / `--claude`; both tools get a
  `pipeline` symlink to the clone. `link-project.sh` and `project/handoff/` are
  removed (superseded).
- Fixes: `Pipeline:` and `Model:` header values are now injected rather than
  hard-coded; `@path` references in commands (not expanded by OpenCode V2) are
  explicit read instructions; `ingest-workitems.py` writes `TRACKING.md`.
- **Unverified in a real session** (tested only as scripts): skill `!` injection
  and `allowed-tools` pre-approval in Claude Code; the hook firing on a real
  `Write`; `/init` overriding Claude Code's built-in; the Explore override.
  Try each once and tell me what breaks.

## 1.6.9

**Manual step required.** New subagent added to the global config shape,
plus permission changes across every agent that writes a handoff document
or `MAP.md`. Projects with their own `agent` block override these per-agent
and will need this ported by hand if they want it.

Motivation: the primary agents (`design`, `arch`, `build`, `build-hard`,
`build-critical`) each carry their own copy of the same write-mechanics
permission block — near-duplicated per-directory `edit`/`write` allows,
each one a place the absolute-vs-relative-path issue from 1.6.6 or a stem
mismatch could recur independently. `explore` already showed the pattern
for pulling a narrow, cheap, single-purpose job out into a subagent; this
does the same for the write step, not the exploratory-read step.

- **New subagent `scribe`.** Write-only. Takes a `stage` (`plan` | `spec` |
  `report` | `map`), a `stem`, and fully-composed content from the calling
  agent, and places it at the correct path. It does not compose content,
  judge tier, or decide anything — `design`/`arch`/`build*` still own
  writing the actual document text against the template; `scribe` is pure
  I/O. Runs on `opencode/hy3-free` at `temperature: 0`, no read/grep/bash/
  webfetch/task access, `write` scoped to `.opencode/handoff/{1-plan,2-spec,
  3-report}/**` and `.opencode/MAP.md`, `edit` scoped to `.opencode/MAP.md`
  only.
- **Sanity checks live in `scribe`, not the caller.** For plan/spec/report:
  refuses to write if the content's own `Stem:` header disagrees with the
  `stem` argument (never silently picks one), and refuses to overwrite an
  existing file (the caller must resolve a collision explicitly — this is
  the same "never destroy a prior session's record" concern Rule 7 and the
  report template's status-authority note already carry, just enforced at
  the write site now instead of by convention).
- **`MAP.md` gets a deliberate exception.** It doesn't carry a `Stem:`/
  `Stage:`/etc. header — it stamps a commit hash instead, per `/map`'s own
  format — so `scribe` checks for that line instead. It's also regenerated
  in place rather than created fresh per slice, so `scribe` **does**
  overwrite it, unlike every other stage. This is the one intentional
  break from the no-overwrite rule above.
- **`scribe` still returns full content back to the caller.** Writing the
  file is not the checkpoint — the primary agent still prints the absolute
  path and full contents itself per Rule 1. This subagent removes duplicate
  write-permission plumbing; it does not touch the stop-and-print discipline
  or Rule 3's go-ahead-before-code gate, which remain entirely with the
  primary agents.
- `design`, `arch`, `build`, `build-hard`, `build-critical` gain
  `task: { "scribe": "allow" }` alongside the existing `explore: "allow"`,
  and lose their own `.opencode/handoff/**` (and, for `arch`, `.opencode/
  MAP.md`) entries from `edit`/`write` — those permission grants move to
  `scribe`. Source-file `edit`/`write` behavior (the 1.6.8 catch-alls,
  `build-critical`'s per-edit `ask`) is **unchanged** — this release only
  touches handoff-document and map writes, nothing about source code.

**Known open issue this interacts with, not resolved here:** the
1.6.7–1.6.8 discrepancy around whether `arch` actually has `/map` write
permission is still unresolved. Routing `MAP.md` writes through `scribe`
changes *where* that permission lives but doesn't independently confirm
which shape is correct — verify that discrepancy and this change together
in the same test pass, not as two separate unknowns.

**Not yet done, per the "verify before promoting" principle:** this has
not been run through a real plan→arch→build pass. In particular, unverified:
whether `task` output survives back to the calling agent's context intact
enough to satisfy Rule 1's "print full contents" step without truncation
or summarization by the runtime, and whether a stem-mismatch refusal from
`scribe` surfaces clearly enough in the primary agent's next action rather
than being silently swallowed. Test in `local-overrides.jsonc` before
promoting to `project/opencode.jsonc.example` or the global default.

**Also needs updating once verified, not done in this release:**
`project/opencode.jsonc.example`'s "must define ALL SEVEN" comment (now
eight) and the README's agent table.

## 1.6.8

**Manual step required.** Structural change to `global/opencode.jsonc`'s
permission shape — not a prompt/command/template change. Projects with their
own `agent` block already override these per-agent, but should review whether
they want the same loosening applied locally.

Motivation: too much prompt friction during normal use — `arch` was asking
per-command for anything outside its small bash allowlist, and `build` /
`build-hard` were asking per-file on every edit despite Rule 3 already
requiring an explicit human go-ahead in chat before any code gets touched.
The conversational gate was being enforced twice, once by the agent and once
by the permission layer.

- **`bash` catch-all changed `"ask"` → `"allow"`, globally and in `arch`,
  `build`, `build-hard`.** Named destructive commands (`rm *`, `git push*`,
  `git reset*`, `git checkout*`, `git commit*`) stay explicitly denied or
  ask, since deny/ask entries after a catch-all still win. `build-critical`
  is unchanged — its bash catch-all stays `"ask"`.
- **`edit` and `write` catch-alls changed `"ask"` → `"allow"` in `build` and
  `build-hard`.** Rationale: the human's go-ahead already happened in chat
  per Rule 3 before any edit begins; the per-file prompt was a redundant
  second confirmation for T1/T2. `build-critical` is deliberately **unchanged**
  — its `edit`/`write` stay `"ask"` per-edit, per the existing project rule
  that per-edit approval is the T3 mechanism itself, not incidental friction.
- **`external_directory` catch-all changed `"ask"` → `"allow"`, with a new
  top-level `edit: "*": "ask"` layered on to try to keep external writes
  gated while external reads pass through.** This follows OpenCode's
  documented pattern (external_directory grants baseline access; a matching
  `edit` rule restricts writes on the same paths) but has **not been
  verified to actually prompt** — OpenCode has an open upstream bug
  (`anomalyco/opencode` issue #18441) where `external_directory: "allow"`
  can bypass `edit` ask/deny rules for writes entirely. Treat this as
  unconfirmed until tested with a real external write attempt; if it
  doesn't prompt, this is a gap, not a config error on our side.

**Known risk accepted, not mitigated, in this release:** the `bash`
catch-all allow is not limited to read-only commands — it also applies
inside `build` and `build-hard`, which execute real build/check/test
commands from a spec, and named denies don't cover everything (`sudo`,
`curl | sh`, `mv`, `cargo publish`, `npm install <pkg>`, etc. all pass as
`allow`). Combined with `edit`/`write` also now unrestricted in those same
two agents, a build session can run arbitrary shell and write arbitrary
files with no prompts at all once past the initial go-ahead. This lands
hardest on `build`, currently pinned to `nemotron-3-ultra-free` — a model
not yet run through a real plan→arch→build slice per §3.7. No narrowed
bash allowlist (e.g. project check/build commands specifically) was
substituted in this release; that remains a possible follow-up if the
blast radius turns out to matter in practice.

**Not yet done, per the "verify before promoting" principle:** none of
this has been run through a real plan→arch→build pass yet. Treat the first
several sessions on this config the way any tier or permission change
should be treated — watch closely for anything it lets through that
shouldn't have, before trusting it as settled.

## 1.6.6

**Safe to pull.** Prompt and command changes only — no agent, model, or
permission-structure changes.

- **`arch` command: fixed the spec-stem corruption bug.** The write target
  was `.opencode/handoff/2-spec/$ARGUMENTS.spec.md` — a raw concatenation
  with no fallback if the argument already carried an extension. The `@`
  plan reference has always had a fallback list (`ls -t 1-plan/*.md`) for
  exactly this case; the write path didn't. Observed in practice: an
  invocation with `$ARGUMENTS = 2026-08-19-ota-test-server.plan.md`
  produced a write target of `...plan.md.spec.md`, silently corrupting the
  stem downstream. Fixed by deriving the write stem from the plan
  document's own `Stem:` header once it loads, never from the raw
  argument — the header is the one place the stem can't drift, since every
  earlier stage stamped it there deliberately. If the argument and the
  header disagree, `arch` now trusts the header and says so in passing
  rather than guessing.
- **`arch` prompt: new verification-effort item — existence is not default
  behaviour.** A presence check (`which <tool>`, an import resolving)
  proves a dependency is there; it proves nothing about its default listen
  address, auth mode, or config-file requirements. `arch` had previously
  marked "required external binaries are available — confirmed for this
  environment" on the strength of `which mosquitto` alone, then specified a
  bare `mosquitto -p <port>` invocation — correct-looking, wrong under
  mosquitto 2.0's local-only default, and only caught after a full hardware
  round trip and a device panic. The prompt now requires checking a
  runtime's *default behaviour* directly whenever a spec depends on it, not
  just its presence, and marking anything short of that ⚠ inferred rather
  than confirmed.

**Also observed this round, not yet promoted into the shared template:** a
project session hit permission denials on `.opencode/handoff/2-spec/**`-style
allows when the tool call used an absolute path, while an allow written
against the absolute path itself succeeded. The affected project's
`opencode.json` now carries both the relative and the absolute form for every
handoff-directory `edit`/`write` entry as a defensive workaround. This is
**not** promoted into `project/opencode.jsonc.example` yet — the fix as
applied embeds one machine's literal absolute path, and the underlying
matcher behavior isn't root-caused against OpenCode's own implementation.
Treat it as a hypothesis worth continuing to test (verify any new path allow
with a throwaway write before trusting it), not a confirmed pipeline-wide bug,
until it reproduces cleanly enough to generalize into the template.

## 1.6.5

**Safe to pull.** Script-only — no agent, permission, or template changes.

- **`scripts/ingest-workitems.py` now sorts finished tickets into
  `items/done/`.** Any item whose `status` matches a done value (default:
  `done`, `complete`, `completed`, `closed`, case-insensitive; extend with
  repeatable `--done-status`) is written to `items/done/<ID>.md` instead of
  `items/<ID>.md`, and dropped from `WORKITEMS.md`'s main table in favour of
  a one-line count. Rerunning the script moves a ticket between the two
  locations automatically as its tracked status changes — nothing is ever
  set locally. This is a read-side split only: the tracker (AppFlowy /
  sheet / HTML) stays the sole place status is written, consistent with the
  "materialise, don't let agents fetch or mutate live" principle the
  ingester was already built on.
- **Considered and deliberately not built:** teaching `/status` or `/tickets`
  to move files themselves. Both are bound to `ask`, which has `write` and
  `edit` denied on purpose — the 1.4.0 rule that "`ask` summarizes the
  record, it never becomes the record" would break the moment a Q&A agent
  gained a filesystem side effect. Sorting on status belongs in the
  ingester, which already reads that column and already regenerates the
  tree wholesale on every run.
- The existing stale-file safety check (1.3.1: refuse to prune ≥5 items /
  ≥40% of the total without `--force-prune`) now scans `items/` and
  `items/done/` together, so it can't be fooled by files that moved between
  the two rather than actually leaving the source.
- `--dry-run` output now flags done items inline (`[done]`) rather than
  only being visible after a real write.

## 1.6.3

**Manual step required** if your project defines its own `agent` block:
the stage-1 agent is renamed and `default_agent` changes with it.

- **Stage-1 agent renamed `plan` → `design`.** `plan` is reserved by
  OpenCode and carries a built-in read-only mode that overrides an agent's
  own `permission` block, so an agent named `plan` could not write to
  `.opencode/handoff/1-plan/**` even though its config explicitly allowed
  that path — the one write the stage exists to perform. Observed live: a
  planning session had to hand three finished plan documents back through
  chat for the human to paste in by hand. The `/plan` command, the `Stage:
  plan` header value, and the `plan` status values are all unchanged; only
  the agent key moved.
- **`arch`: the "at least three `explore` queries" floor is gone.**
  Replaced with a judgment standard — resolve every ⚠ by the cheapest
  route that actually answers it, and record "not verified" when neither
  a read nor a delegation does. The fixed count was forcing full re-runs
  whenever a delegated query stalled.
- **`arch`: multiple specs print one per turn.** A three-spec session hit
  the response-length limit and printed none of them, which silently
  removed Rule 1's checkpoint — three `ready` specs, one T3, reached disk
  unread.
- **`explore`: 8-call budget, no repeated searches, no narration.** One
  lookup emitted the same "let me search more broadly" sentence several
  hundred times and returned nothing; the target was under `.opencode/`,
  which `glob` does not reliably match. The prompt now says to `read` the
  directory path instead.
- **New Rule 4a — T3 triggers a narrowing pass.** A T3 assignment now
  requires re-checking whether the whole slice is critical or only part of
  it, and splitting until the T3 portion passes a one-sentence test, a
  readable-diff test, and a nothing-incidental test. Narrowing keeps every
  floor concern in T3; routing around the floor does not — the spec must
  state which it did. Motivating case: a `build-critical` pass on Claude
  Opus 5 cost $3.19 and produced no code, because the slice bundled a
  1100-line firmware port around one genuinely critical marker format.

## 1.6.2

**Safe to pull.** Prompt, command, and template changes only — no agent,
model, or permission changes.

Follows a real before/after measurement of two comparable slices
(2026-08-17 facade core/verify at $3.48, facade hal/envelope at $0.22),
per the framework's own "measure it on real tasks" requirement.

- `Model:` is now injected from config rather than self-reported. The
  core/verify report stamped `claude-sonnet-5`; billing shows the build ran
  entirely on `deepseek-v4-pro`. Self-report is not evidence.
- `plan` prompt: ⚠ is the stage's only marker. The cheap planner asserted
  nine of ten assumptions as `[read]` fact, one of which was wrong and
  self-contradicting, leaving `arch` no prioritised work list.
- `arch` prompt: minimum of three `explore` queries and an explicit
  unverified-claims pass before writing. The frontier arch's visible
  advantage was turn count (9 vs 5), which is buyable at current prices.
- No retiering. `build-hard` on Flash did the same work as Pro — 50 vs 41
  calls, 5.3M vs 4.5M cumulative input — at a tenth the cost, with no
  quality drop detectable in the reports.

## 1.6.1

Changed the arch agent from deepseek v4 flash to gpt 5.6 luna

## 1.6.0

**Manual step required** if your project pins its own models: this changes
a default model assignment. Projects with an `agent` block in their own
`opencode.jsonc` keep whatever they already pin — update those by hand.

- **`arch` moves from DeepSeek V4 Pro to DeepSeek V4 Flash.** This is a
  retiering decision, not a benchmark chase: DeepSeek's officially retrained
  V4-Flash (shipped July 31, 2026) now matches or beats V4-Pro-Preview on
  every agent benchmark DeepSeek publishes — Terminal-Bench 2.1 82.7 vs 72.1,
  DeepSWE 54.4 vs 7.3 — while costing roughly a third as much. `arch` was
  already identified in 1.5.0 as the single largest cost driver in a
  plan→arch→build pass, so this is the same lever pulled one step further.
- **Caveat, stated plainly because it matters for a decision this size:**
  the DeepSeek numbers above are vendor-self-reported under DeepSeek's own
  harness, which was not independently reproducible at time of writing.
  Separately, an independent re-run on the contamination-resistant DeepSWE
  benchmark put V4-Pro's pass@1 at 8%, far below its 80.6% vendor-reported
  SWE-bench Verified score — a reminder that the whole V4 family's published
  numbers deserve real skepticism, not just Pro's. This move is a deliberate
  bet that Flash's own trajectory (cheaper, and no longer behind Pro on
  DeepSeek's own suite) is worth taking, not a claim that arch's output
  quality has been independently verified against the old default. Treat the
  first several `arch` sessions after upgrading the way any tier change
  should be treated — read the specs it produces closely, the way Rule 1
  (stop and print) already asks you to.
- `explore` and `build-hard` stay on DeepSeek V4 Flash — unchanged, already
  the cheapest paid tier that clears the bar for those roles.
- `ask`, `plan`, and `build` stay on DeepSeek V4 Flash Free — unchanged.
  These roles either can't see implementation code (`plan`) or are read-only
  / mechanical by design, so the free tier's data-retention caveat and lower
  ceiling aren't costing anything real here.
- `build-critical` stays on Claude Opus 5 — unchanged, and not up for
  retiering on cost grounds. It's the rarest, narrowest agent by design, so
  it contributes little to the bill regardless of model, on the one tier
  where a wrong answer is a bricked device or a security hole rather than a
  failed build.
- **Considered and deliberately not adopted this round:** several other Zen
  models surfaced as candidates — Poolside's Laguna S 2.1 (free tier;
  vendor claims Terminal-Bench 2.1 and SWE-Bench Pro parity with DeepSeek V4
  Flash at a fraction of the parameter count) and NVIDIA's Nemotron 3 Ultra
  (free tier; published architecture paper, not just a launch blog) both
  looked promising enough to name here. Neither has been run against real
  slices in this pipeline yet. The project decision for this release is to
  consolidate on DeepSeek across the pipeline rather than diversify vendors
  further; revisit Laguna/Nemotron for `arch` and `build-hard` in a future
  release once they've been benchmarked against actual specs and reports,
  not just vendor tables.

## 1.5.1

**Safe to pull.** Prompt-only fix — no agent, permission, or model changes.

- **Fixed:** `/handoff` had no agent guard, unlike every other stage-bound
  command. In practice the permission system already prevents `plan`, `arch`,
  or `ask` from actually writing to `3-report/` — each is scoped to its own
  directory or, for `ask`, denied edit outright — so no fabricated report
  could ever land on disk. But without a guard, running `/handoff` from the
  wrong agent meant composing a full report, hitting a silent write denial,
  and possibly printing the fabricated content into chat as if it had saved.
  `/handoff` now checks it's running as `build`, `build-hard`, or
  `build-critical` before doing anything, and refuses with a redirect
  otherwise — same self-check pattern `/build` already uses for tier
  matching, applied to agent identity instead.

## 1.5.0

**Manual step required** if your project pins its own models: this changes
default model assignments. Projects with an `agent` block in their own
`opencode.jsonc` keep whatever they already pin — update those by hand.

Cost-driven retiering after a real measurement: one plan→arch→build-hard pass
came in at ~$3.50, with `arch` on a frontier model reading the codebase
accounting for most of it.

| Agent | Was | Now |
|---|---|---|
| `plan` | Claude Sonnet 5 | DeepSeek V4 Flash |
| `arch` | Claude Opus 5 | DeepSeek V4 Pro |
| `build` (T1) | DeepSeek V4 Flash | DeepSeek V4 Flash Free |
| `build-hard` (T2) | DeepSeek V4 Pro | DeepSeek V4 Flash |
| `build-critical` (T3) | Claude Opus 5 | **unchanged** |

- `build-critical` deliberately stays on Opus 5. It is the rarest agent and
  the narrowest by design (binding file list, per-edit approval), so its
  context stays small and it contributes little to the bill — downgrading it
  saves cents per slice on the one tier where a wrong answer is a bricked
  device rather than a failed build.
- README gained a note that DeepSeek V4 Flash/Pro are half price outside peak
  hours (01:00–04:00 and 06:00–10:00 UTC), which for UTC+8 lands squarely on
  the working day.
- README gained an explicit free-tier retention note: free models may use
  submitted data to improve the model, unlike the rest of Zen.

## 1.4.0

**Safe to pull.** New command, prompt update — no agent or permission
changes. `ask` already had `read: "*": "allow"`, so nothing needed unlocking;
the gap was that its prompt never told it to look at the handoff record.

- `ask`'s prompt now explicitly covers status questions — "what's been done
  on E1", "summarize the last few reports" — and is told to actually read
  `3-report/`, `2-spec/`, and `.opencode/workitems/` rather than answer from
  whatever's already in context.
- Added a hard line: **`ask` summarizes the record, it never becomes the
  record.** A status answer exists for that conversation only. If it should
  persist, the prompt now redirects to `/handoff` — real reports are written
  by `build`, not improvised in a Q&A reply. Without this, a convenient
  status summary could quietly become a second, informal decision record
  that contradicts or duplicates the real one.
- Added `/status [scope]`, bound to `ask`. Reads recent files across all
  three handoff stages and reports where each stem actually got to —
  distinguishing `complete` from `partial`/`stopped`, and flagging anything
  planned or specced but never reported as built, rather than rounding
  everything mentioned up to "done".

## 1.3.1

**Safe to pull.** Bug fix in the ingester — no agent, permission, or template
changes.

- **Fixed:** rerunning `ingest-workitems.py` never deleted item files for
  tickets removed from the source. `WORKITEMS.md` would stop listing a
  finished/removed ticket, but its `items/<ID>.md` stayed on disk untracked
  by anything — a silent orphan. Reruns now remove stale item files, so
  add / update / finish / remove are all reflected correctly.
- **Added a safety check for the fix above:** if a run would remove ≥5 items
  *and* ≥40% of what's currently on disk, it refuses and prints the list
  instead of deleting, since that pattern is far more often a `--from-*` flag
  left off a multi-source command than that many tickets actually vanishing.
  Nothing is written in that case — index and `items/` are left exactly as
  they were. Confirm with `--force-prune` if the removal is real.
- The index and `items/` directory now always update together or not at all
  — the mass-removal check runs before either file is touched, so a blocked
  run can never leave them disagreeing with each other.

## 1.3.0

**Safe to pull.** Script-only — no agent, permission, or template changes.

- `scripts/ingest-workitems.py` gained `--from-csv`: CSV/TSV files or a
  published Google Sheets URL. Handles a `Level` column (EPIC/STORY/TASK) or
  infers depth from ID dash-count; folds each task's parent story — including
  its user story — into the generated item file under a new **Why — parent
  story** section, since task titles alone usually lack the actual intent.
- **Multiple sources can now be combined in one run.** First non-empty value
  per field wins, in the order sources are given; every item file records
  which source(s) it came from.
- Added `--id-column` for boards where the identifier isn't under a column
  literally named ID (common on kanban grids) — falls back to scanning row
  values against `--id-pattern` when no column is given.
- Header matching is now fuzzy (case/spacing/punctuation-insensitive) with
  common field aliases built in, so mildly different exports from project to
  project don't need per-project script changes.

## 1.2.0

**Safe to pull.** No agent or permission changes — one new command and one
new script.

- Added `scripts/ingest-workitems.py`: converts a task source into a canonical
  `.opencode/workitems/` tree (compact `WORKITEMS.md` index plus per-item
  detail files). Two sources so far: `--from-html` for shared HTML breakdowns,
  `--from-appflowy` for AppFlowy Cloud database rows. Adding a source means
  writing one function; nothing downstream changes.
- Added `/tickets` command, bound to the `ask` agent — browse and filter work
  items to decide what to work on. Deliberately cannot plan or switch agents:
  delegation stays a human decision.
- Item files compute a **Blocks** section by inverting the dependency graph,
  which most trackers do not show.


## 1.1.0

**Manual look recommended** if you have existing projects on 1.0.0 — a new
agent was added to the global config shape.

- Added `ask`: a fourth agent outside the plan → arch → build pipeline, for
  quick questions that aren't worth a planning session. No handoff document,
  no template, no tier. Defaults to `deepseek-v4-flash-free` since it's
  read-only and produces no artifact.
- Added `/ask` command, callable from any tab.
- Renamed `/init-pipeline` to `/init`. Output now explicitly tells you to run
  `/map` next.
- Fixed: `project/opencode.json.example` had `"//"` keys inside `permission`
  blocks that fail OpenCode's schema validation. Converted to `.jsonc` with
  real `//` comments.
- Added `scripts/install-global.sh` and `scripts/link-project.sh` for
  symlink-based updates across devices and projects.

## 1.0.0

Initial release. `plan` → `arch` → `build`/`build-hard`/`build-critical`,
tiered by criticality, with a stop-and-print handoff document at every seam.
