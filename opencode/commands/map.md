---
description: Regenerate .handoff/MAP.md — the project shape the planner reads
agent: arch
---

<summary>
You MUST regenerate `.handoff/MAP.md`, a short structural map of this project.
You SHOULD keep it under 200 lines — it is read by the planning agent on every
session and its size is a recurring cost.
You MUST print the file when done, then stop.
</summary>

Directory shape:
!`find . -maxdepth 3 -type d -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/target/*' | sort | head -60`

Manifests:
!`find . -name 'Cargo.toml' -o -name 'package.json' -o -name 'pyproject.toml' | grep -v node_modules | grep -v '/target/' | head -30`

Generated from commit:
!`git rev-parse --short HEAD`

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

Write `.handoff/MAP.md` covering:

1. **Modules / crates / packages** — name, one-line purpose, and whether it is
   built, partial, or a stub.
2. **The dependency graph between them** — who depends on whom.
3. **Public surface** — the main exported types and functions per module, names
   only, no signatures.
4. **Feature flags / build configuration** — what exists and what it gates.
5. **Entry points** — where execution starts, per target.

Names and one-line purposes only. This is a map, not documentation. If it is
growing past 200 lines, cut detail rather than raising the limit. Record the
commit hash at the top so a stale map is obvious.
