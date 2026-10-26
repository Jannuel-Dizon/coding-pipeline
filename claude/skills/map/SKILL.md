---
name: map
description: Regenerate .handoff/MAP.md — the project shape the spec stage reads
disable-model-invocation: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(~/.claude/pipeline/scripts/pipeline-ctx.sh *)
  - Bash(find *)
  - Edit(/.handoff/MAP.md)
---

Regenerate `.handoff/MAP.md`, a short structural map. Keep it under 200 lines —
it is read every spec session, so its size is a recurring cost. Print it when
done, then stop.

Generated from commit: !`~/.claude/pipeline/scripts/pipeline-ctx.sh head`

Find the shape yourself with Glob and Grep (or `find . -maxdepth 3 -type d`,
skipping `.git`, `node_modules`, `target`). Send broad sweeps to the `Explore`
subagent.

Cover: (1) modules/crates/packages — name, one-line purpose, built / partial /
stub; (2) the dependency graph between them; (3) public surface — names only;
(4) feature flags and build configuration; (5) entry points per target.

A map, not documentation: names and one-liners. Record the commit hash at the
top so a stale map is obvious. If it outgrows 200 lines, cut detail.
