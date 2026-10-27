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
  - Bash(graphify *)
  - Edit(/.handoff/MAP.md)
---

Regenerate `.handoff/MAP.md`, a short structural map. Keep it under 200 lines —
it is read every spec session, so its size is a recurring cost. Print it when
done, then stop.

Generated from commit: !`~/.claude/pipeline/scripts/pipeline-ctx.sh head`

Find the shape yourself with Glob and Grep (or `find . -maxdepth 3 -type d`,
skipping `.git`, `node_modules`, `target`). Send broad sweeps to the `Explore`
subagent.

Knowledge graph refresh (Graphify):
- If the `graphify` CLI is not on PATH: stamp `Graph: not available` in the
  MAP.md header and proceed with the map exactly as before. The map never
  fails because of Graphify.
- Else: when `graphify-out/graph.json` exists, run `graphify update .`;
  otherwise run `graphify extract . --code-only` followed by
  `GRAPHIFY_BACKEND=none graphify cluster-only .` (first build; extract alone
  writes no GRAPH_REPORT.md, and without the env var cluster-only makes a
  model call to name communities).
  Never inside a `!`-injected snippet.
- Read `graphify-out/GRAPH_REPORT.md` as one input to the map write
  (god nodes, communities, surprises). `graphify query|explain|god-nodes`
  are cheap targeted reads. NEVER read `graph.json` wholesale.
- Stamp one header line: Graph: built <commit-hash>, graphify <version>
  — or Graph: rebuild failed (<reason>), and still complete the map.

Cover: (1) modules/crates/packages — name, one-line purpose, built / partial /
stub; (2) the dependency graph between them; (3) public surface — names only;
(4) feature flags and build configuration; (5) entry points per target.

A map, not documentation: names and one-liners. Record the commit hash at the
top so a stale map is obvious. If it outgrows 200 lines, cut detail.
