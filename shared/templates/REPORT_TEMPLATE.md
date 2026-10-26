# Report — <slice name>

```
Stem:      YYYY-MM-DD-<slice>
Stage:     report
Status:    complete | partial | stopped | blocked
Tier:      T1 | T2 | T3
Pipeline:  <VERSION, injected by the command>
Model:     <model that wrote this>
Spec:      .handoff/2-spec/<stem>.spec.md
```

> A report, not a sales pitch. What went wrong is worth more to the next
> planning session than what went right.

> The `Status:` value above is authoritative. If body prose (e.g. a later
> §8 update) changes the effective status, edit the header field to match
> in the same edit — never leave the two disagreeing.

---

## 1. Files changed

Full paths from the repo root. Every file, no exceptions.

**Added**

| Path | What it is |
|---|---|

**Modified**

| Path | What changed |
|---|---|

**Deleted**

| Path | Why |
|---|---|

## 2. Verification

**Do not record anything as verified that was not actually run in this
session.**

| What | Command | Result |
|---|---|---|
| Check / build | `<exact command>` | not run / passed / failed |
| Tests | `<exact command>` | <n> added, not run / passed / failed |
| Real environment | — | not tested — requires human |

If the check was not run, say so plainly here rather than implying it passed.

## 3. Where the build diverged from the spec

The most important section. For each divergence:

- **Spec said:** <what>
- **Reality:** <what the code or dependency actually required>
- **Done instead:** <what was built>
- **Needs planning review?** yes / no

If nothing diverged, write "none" — do not pad it.

## 4. Spec claims that turned out wrong

Specifically the ⚠ items and signatures the spec asserted.

| Spec claimed | Actual | Where checked |
|---|---|---|

## 5. Decisions made during the build

Things the spec did not cover that had to be settled to keep going. Each one is
a candidate for the project's decision record.

- **<decision>** — reasoning: <why>. Reversible: yes / no.

## 6. Adversarial analysis *(T3 only)*

The failure modes considered and how each is handled. Interruption at each
state-changing boundary, malformed input, partial completion, ordering, and the
failure-that-looks-like-success.

| Failure mode | Handled how | Confidence |
|---|---|---|

**Still needs testing in a real environment:** <list>

## 7. Still open

- **Unbuilt from this spec:** <what and why>
- **New questions raised:** <what the build surfaced that nobody anticipated>
- **Cross-boundary contracts hit:** <carry forward — these never resolve on
  their own>

## 8. Next

What the planning stage should look at next, given what now exists and what
this build learned.
