# Plan — <slice name>

```
Stem:      YYYY-MM-DD-<slice>
Stage:     plan
Status:    draft | ready
Tier:      (unset — assigned by the architecture stage)
Pipeline:  <VERSION, injected by the command>
Model:     <model that wrote this>
```

> Written by the planning stage, which can see the project's shape but not its
> implementation. **Intent here is authoritative. Everything about the existing
> code is a claim to be checked.** Anything marked ⚠ must be verified by the
> architecture stage before anything is built on it.

---

## 1. The slice

**What this builds:** <2–3 sentences, plain language>

**Where it lives:** <modules / crates / packages expected to be touched>

**Explicitly out of scope:** <what this slice does NOT do — the most useful
section in this document, because slices grow silently>

**Depends on:** <what must already exist and be working>

## 2. Why this shape

<The reasoning, not just the conclusion. What alternatives were considered and
why they lost. This is what survives when the code changes, and what lets the
architecture stage tell the difference between an instruction that is merely
inconvenient and one whose reason no longer holds.>

## 3. Behaviour and contracts

For each thing being built: what it must guarantee, what a caller may assume,
what it must not do. Prose is fine and often better than a signature here —
the exact shape is the architecture stage's decision.

- **<name>** — contract: <...>

## 4. Assumptions about the existing code ⚠

Every claim being made about what already exists. Be generous — a surfaced
assumption is cheap, a buried one costs a build session.

| # | Assumption | Why it matters if wrong |
|---|---|---|
| A1 | ⚠ <claim> | <consequence> |

## 5. Error handling and edge cases

- Invalid input →
- External call failure →
- Empty / zero-length case →
- Interruption partway through →
- Resource exhaustion →

## 6. Cross-boundary contracts touched

Anything requiring agreement with a system or team not owned here. **Name
them; do not resolve them.**

- <item> — status: open / provisional / settled

## 7. Acceptance

- **Behaviour to test:** <specific inputs → expected outputs>
- **Not verifiable without a real environment:** <what needs hardware, staging,
  or a real integration>

## 8. Open questions

Ambiguity this stage could not resolve. If the build stage hits a decision not
covered here, it belongs in this list next time.

- <question>

## 9. Suggested slicing

If this is bigger than one build pass, say how it splits and what order.

1. <step>
2. <step>
