# Spec — <slice name>

```
Stem:      YYYY-MM-DD-<slice>
Stage:     spec
Status:    ready | replan | blocked
Tier:      T1 | T2 | T3
Pipeline:  <VERSION, injected by the command>
Model:     <model that wrote this>
Plan:      .handoff/1-plan/<stem>.plan.md | none (direct spec)
```

> Written by the architecture stage against the real codebase. Claims here are
> marked **[read]** (observed in the source, path cited), **[ran]** (a command
> was executed and this is its output), or **⚠ inferred** (reasoned out, still
> could be wrong).

---

## 0. Intent *(only when `Plan: none (direct spec)` — otherwise delete this section)*

A direct spec has no plan document behind it, so the intent a plan would have
held goes here. This is what lets a later reader tell an instruction that is
merely inconvenient from one whose reason no longer holds.

**What this builds:** <2–3 sentences, plain language>

**Explicitly out of scope:** <what this slice does NOT do>

**Why this shape:** <alternatives considered and why they lost>

**Depends on:** <what must already exist and be working>

## 1. Tier and why

**Tier:** <T1 | T2 | T3>

**Reasoning:** <one sentence>

**T3 floor check:** <which floor entries this slice touches, or "none">

**Build agent:** `build` | `build-hard` | `build-critical`

## 2. Verdict on the plan

**Status:** ready / replan / blocked

<If replan or blocked: what the planning stage needs to reconsider, and why.
Be specific about which part of the intent cannot be satisfied as written. Then
stop — the rest of this document is not needed.>

## 3. Assumption verification

Every ⚠ from the plan's §4, resolved. *(Direct spec: list the assumptions you
made about the existing code while exploring, each resolved the same way.)*

| # | Plan claimed | Actual | Verdict | Source |
|---|---|---|---|---|
| A1 | <claim> | <what is actually there> | confirmed / corrected / invalidated | `path:line` |

**Invalidated assumptions that affect other, not-yet-built slices:** <list, or
"none">

## 4. What to build

Exact interfaces, signatures, types, module placement. This is the layer the
plan deliberately guessed at.

```
// [read] existing shape this must match: path/to/file.ext:NN
<signature>
```

**Contract:** <what it guarantees, what callers may assume, what it must not do>

## 5. Files

| Path | Action | Notes |
|---|---|---|
| `path/to/file` | create / modify | <what changes> |

At T3 this list is **binding** — the build agent may not touch anything else.

## 6. Existing code this interacts with

| What | Where | Why it matters |
|---|---|---|
| <symbol / module> | `path:line` | <constraint it imposes> |

## 7. Dependency APIs used

| Dependency | Version | Item | Verified |
|---|---|---|---|
| <name> | <pinned version> | <function / type> | [read] `<where>` |

**New dependencies required:** <name and justify, or "none". Do not spec code
against a dependency nobody has agreed to add.>

## 8. Error handling and edge cases

Concrete, against the real error types in this codebase.

- <case> → <handling> — error type: `<actual type>` [read]

## 9. Cross-boundary contracts

Carried forward from the plan, plus anything the verification surfaced. Named,
not resolved.

- <item> — status: open / provisional / settled

## 10. Build order

1. <file / step>
2. <file / step>

**Checkpoint after:** <step, if the human should look before continuing>

## 11. Acceptance

- **Tests to write:** <specific>
- **Check command:** <the project's, and what "green" means>
- **Not verifiable here:** <needs hardware / staging / a real integration>

## 12. Still open

Anything the build stage must stop and ask about rather than decide.

- <question>
