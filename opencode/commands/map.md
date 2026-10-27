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

Knowledge graph refresh (Graphify — scoped):

- `graphify --version` failing → stamp `Graph: not available`; no question,
  no config write, no `.graphify-scopes/`; proceed with the map exactly as
  before. The map never fails because of Graphify.
- Config lives at `.graphify-scopes/config.json`:
  `{ "version": 1, "scopes": [{ "name": …, "root": … }] }`. `root` is
  relative to the project root (the directory `/map` runs in), POSIX
  separators; never `.`, `..`, or absolute. `name` is the lowercased root
  with every `[^a-z0-9]` replaced by `-`; on collision append `-2`, `-3`.
  `"scopes": []` records unscoped mode. Config present but invalid JSON or
  wrong shape (no `scopes` array, bad `root`) → stamp `Graph: skipped
  (scope config unreadable: .graphify-scopes/config.json)`; no build, no
  config write, no unscoped fallback.
- Argument grammar (`$ARGUMENTS`; one verb per run; an unrecognised argument
  is named in the reply and the run proceeds as `keep`):
  - none — config missing → first-run question; config with scopes →
    revision question; `scopes: []` → unscoped build, no question.
  - `keep` — build from the existing config; no question.
  - `none` — record `scopes: []`; unscoped build.
  - `reset` — ignore the existing config; first-run question; the answer
    overwrites it.
  - `add <path>[, <path>…]` — validate, append with generated names, build.
  - `remove <name>[, <name>…]` — drop from config, build. The abandoned
    `.graphify-scopes/<name>/` stays on disk and is listed in MAP.md.
- Candidates (printed before any question): `find . -mindepth 1 -maxdepth 2
  -type d`, drop dot-prefixed paths and `graphify-out`, sizes via `du -sk`,
  sorted largest first, capped at 40 lines. Hard-skip-named dirs are shown
  `[hard-skip]`, their children still listed to depth 2 (so `target/uno_dm`
  can be picked). Revision lists also drop paths already covered by a scope.
- Hard-skip names (for marking candidates and the `invisible under`
  warning): venv, .venv, node_modules, __pycache__, .git, dist, build,
  target, site-packages, lib64, .pytest_cache, .mypy_cache, .ruff_cache,
  .tox, .nox, .eggs, *.egg-info, graphify-out, lcov-report, visual-tests,
  visual-test, __snapshots__, storybook-static, dist-protected, .next,
  .nuxt, .turbo, .angular, .idea, .cache, .parcel-cache, .svelte-kit,
  .terraform, .serverless, .graphify, .obsidian, .smart-env, .worktrees.
- First run (config missing): print the candidate list and the argument
  grammar above, then stop — the user's next `/map <answer>` builds the
  scopes. Unanswered this run → unscoped mode for this run, stamped
  `Graph: unscoped root scan <commit>, graphify <version>; scopes not
  chosen (no answer this run)`; write nothing to config.
- Revision (config has scopes, no argument): print the current scopes
  (name, root) and the uncovered candidates with the keep / add / remove
  grammar, then stop; the user's next `/map <answer>` decides. Unparseable
  answer → keep. Unanswered this run → keep the existing config and build
  with it.
- Validate every chosen path — reject (dropped, named in MAP.md, the rest
  continue): does not exist; not a directory; a symlink (`find <p>
  -maxdepth 0 -type l`); absolute; contains `..`; `.`; equal to or an
  ancestor of `graphify-out` or `.graphify-scopes`. Overlapping scopes are
  allowed and warned in MAP.md (they double-count). Nothing survives →
  treated as `none`. Then for each kept root: `find <root> -mindepth 1
  -type d -name <skip> -prune -print` per skip name, cap 10 lines, recorded
  as `invisible under <name>:` in MAP.md. The chosen root itself may sit
  inside a skip-named dir.
- Build, step by step:
  1. Ensure `.graphify-scopes/` exists; write its `.gitignore` (contents
     `*`, then `!.gitignore`, then `!config.json`) only if absent; write
     `config.json` only when the answer changed it. Config write failing →
     proceed with this run's choice; stamp `; config not saved`.
  2. Per scope, in config order: `graphify extract <root> --out
     .graphify-scopes/<name> --code-only --no-cluster`. Never `--force`.
     Record the printed `wrote …: N nodes, E edges` line. Non-zero exit or
     missing root → scope failed (first stderr line); continue.
  3. Two or more scopes succeeded → `graphify merge-graphs
     <.graphify-scopes/<name>/graphify-out/graph.json for each succeeded
     scope> --out .graphify-scopes/merged/graph.json`, plus `--previous
     graphify-out/graph.json` when that file exists. Exactly one succeeded
     → skip merge-graphs: `cp .graphify-scopes/<name>/graphify-out/
     graph.json .graphify-scopes/merged/graph.json` and point step 5 at
     that file — likewise for the single implicit `unscoped` scope. Do NOT
     hand cluster-only a scope's own `graph.json` directly (paths under
     `.graphify-scopes/<name>/graphify-out/`): that parent is named
     `graphify-out`, so outputs would land
     inside the scope's extract dir instead of `./graphify-out/`. Never
     leave a stale `merged/graph.json` as the input when the merge step
     failed or was skipped. Zero succeeded → `rebuild failed (no
     scope extracted)`; stop the build here.
  4. Cross-scope relink — always, exactly once per build, after the merge
     correction and before cluster-only. No file is created and no helper
     script exists; run the block below verbatim (the code's column
     positions are part of it). Header-name matching is case-insensitive:
     include `modbusTCP.h` → placeholder `modbustcp` → that include's file
     node; if two candidate files in the matched scope differ only by case,
     the edge stays unresolved — never guessed. Type stubs are both the
     bare `<scope>::<class>` and the file-qualified
     `<scope>::<file-slug>_<class>` shapes graphify produces:

     ```
python3 - <<'PY'
import json, os, sys

def main():
    dry = '--dry' in sys.argv
    pdir = '.graphify-scopes/'
    if not os.path.exists(pdir + 'config.json'):
        print('skipped (fewer than two scopes)')
        return 0
    cfg = json.load(open(pdir + 'config.json'))
    scopes = [(s['name'], s['root'].rstrip('/')) for s in (cfg.get('scopes') or [])]
    if len(scopes) < 2:
        print('skipped (fewer than two scopes)')
        return 0
    gp = pdir + 'merged/graph.json'
    g = json.load(open(gp))
    nodes = g.get('nodes') or []
    links = g.get('links') or []
    idx = {n['id']: n for n in nodes}
    sroot = dict(scopes)

    def seg_lcp(a, b):
        pa, pb = a.split('/'), b.split('/')
        i = 0
        while i < len(pa) and i < len(pb) and pa[i] == pb[i]:
            i += 1
        return i

    def best_scope(imp):
        best, bk, tie = None, -1, False
        for name, r in scopes:
            if name == imp:
                continue
            k = seg_lcp(sroot[imp], sroot[name])
            if k > bk:
                best, bk, tie = name, k, False
            elif k == bk:
                tie = True
        return None if (tie or best is None or bk == 0) else best

    def is_ph(n):
        return n.get('file_type') == 'concept' and not n.get('repo') and not n.get('source_file')

    stems = {}
    fis = {}
    for n in nodes:
        sf = n.get('source_file')
        if sf and os.path.basename(str(sf)) == n.get('label'):
            fis[n['id']] = n
            stems.setdefault(str(sf).rsplit('.', 1)[0].lower(), set()).add(n.get('repo'))

    perstem = {}
    rep = {name: 0 for name, _ in scopes}
    unres = {name: 0 for name, _ in scopes}
    anom = {name: 0 for name, _ in scopes}
    changed = False

    for l in links:
        t = idx.get(l.get('target'))
        if t is None or not is_ph(t):
            continue
        src = idx.get(l.get('source'))
        imp = (src or {}).get('repo')
        if imp not in sroot:
            continue
        tl = str(t.get('label', '')).lower()
        if imp in stems.get(tl, ()):
            anom[imp] += 1
            continue
        b = best_scope(imp)
        if b is None or b not in stems.get(tl, ()):
            unres[imp] += 1
            continue
        cands = [nid for nid, n in fis.items()
                 if n.get('repo') == b and str(n['source_file']).rsplit('.', 1)[0].lower() == tl]
        if len(cands) != 1:
            unres[imp] += 1
            continue
        l['target'] = cands[0]
        l['_map_relinked'] = True
        perstem[(imp, tl)] = b
        rep[imp] += 1
        changed = True

    stubs = [n for n in nodes
             if n.get('repo') in sroot and not n.get('source_file') and n.get('label')
             and (n['id'] == str(n['repo']) + '::' + str(n.get('label', '')).lower()
                  or n['id'].rsplit('::', 1)[-1]
                  .endswith('_' + str(n.get('label', '')).lower()))]
    stub_repo = {n['id']: n['repo'] for n in stubs}
    srel, sdef = 0, 0
    stub_map = {}
    for s in stubs:
        b = best_scope(s['repo'])
        if b is None:
            sdef += 1
            continue
        real = [n for n in nodes
                if n.get('repo') == b and n.get('label') == s.get('label') and n.get('source_file')]
        if len(real) != 1:
            sdef += 1
            continue
        stem = str(real[0]['source_file']).rsplit('.', 1)[0].lower()
        if perstem.get((s['repo'], stem)) == b:
            stub_map[s['id']] = real[0]['id']
            srel += 1
        else:
            sdef += 1
    if stub_map:
        for l in links:
            sid = l.get('target')
            if sid in stub_map and ((idx.get(l.get('source')) or {}).get('repo') == stub_repo.get(sid)):
                l['target'] = stub_map[sid]
                l['_map_relinked'] = True
                changed = True

    kept = 0
    drop = {}
    drop_i = set()
    for i, l in enumerate(links):
        if not l.get('_cross_repo_call'):
            continue
        src = idx.get(l.get('source'))
        tgt = idx.get(l.get('target'))
        imp, tr = (src or {}).get('repo'), (tgt or {}).get('repo')
        if tr is not None and best_scope(imp) == tr:
            kept += 1
        else:
            drop_i.add(i)
            key = str(imp) + ' -> ' + str(tr)
            drop[key] = drop.get(key, 0) + 1
    if drop_i:
        links[:] = [l for i, l in enumerate(links) if i not in drop_i]
        changed = True

    live = set()
    for l in links:
        live.add(l.get('source'))
        live.add(l.get('target'))
    orph = [n['id'] for n in nodes if is_ph(n) and n['id'] not in live]
    if orph:
        orph_set = set(orph)
        nodes[:] = [n for n in nodes if n['id'] not in orph_set]
        for he in (g.get('hyperedges') or []):
            for f in ('members', 'nodes'):
                if isinstance(he.get(f), list):
                    he[f] = [x for x in he[f] if x not in orph_set]
        changed = True

    print(json.dumps({
        'repaired': rep, 'unresolved': unres, 'anomalies': anom,
        'stubs_relinked': srel, 'stubs_deferred': sdef,
        'orphans_removed': len(orph),
        'calls_dropped': drop, 'calls_kept': kept,
    }, ensure_ascii=False))
    if changed and not dry:
        tmp = gp + '.tmp'
        with open(tmp, 'w') as fh:
            json.dump(g, fh, ensure_ascii=False, separators=(',', ':'))
        os.replace(tmp, gp)
    return 0

try:
    sys.exit(main())
except Exception as e:
    print('relink failed: ' + type(e).__name__ + ': ' + str(e)[:300], file=sys.stderr)
    sys.exit(1)
PY
     ```

     Stdout is one line of JSON — the only graph content this stage ever
     reads. Stamp it into the `Graph scopes` block (rules in the Stamps
     bullet). Any non-zero exit means the merged graph stays unrepaired on
     purpose: append `; relink failed (<first stderr line>)` to the `Graph:`
     stamp and continue to step 5 on it. No retry, no fallback — the map
     never fails because of this step. A single scope or `unscoped` prints
     `skipped (fewer than two scopes)`. Because a repaired graph no longer
     holds placeholder nodes, cluster-only may refuse once with its
     "Refusing to overwrite" warning even on a keep run — that is the same
     deliberate shrink as after `remove`; the cp-then-retry-once rule in
     step 5 covers it.
  5. `graphify cluster-only . --graph .graphify-scopes/merged/graph.json
     --no-label` — outputs land in `./graphify-out/`. Non-zero exit, or
     `GRAPH_REPORT.md` / `graph.json` missing afterwards → `rebuild failed
     (cluster-only: …)`; this run's partial `graphify-out/` is not trusted
     and the report is not read. Only `graph.html` missing (large graphs)
     → note `html skipped`; the report is still used. If cluster-only
     refuses to overwrite (a shrink such as "new graph has N nodes but
     existing graph.json has more", or "saved semantic node(s) are
     missing", typical after `remove` and ordinary after step 4 relinked
     and removed placeholders),
     the shrink is deliberate: `cp .graphify-scopes/merged/graph.json
     graphify-out/graph.json` (explicit replacement, not a silent shrink),
     then run the identical cluster-only once more. A second refusal →
     `rebuild failed (cluster-only: …)`; do not retry further.
  6. Read `graphify-out/GRAPH_REPORT.md` only when step 5 succeeded in this
     run (god nodes, communities, surprises). NEVER read `graph.json`
     wholesale. `graphify query|explain|god-nodes` are cheap targeted reads.
  Unscoped mode is the same pipeline with the implicit scope `unscoped`
  (root `.`), feeding `.graphify-scopes/unscoped/graphify-out/` — not a
  root extract that folds into the merged graph.
- Stamps (the `Graph:` header line, replacing `built <commit>, graphify
  <version>`): `built <commit>, graphify <version>; scopes: <name>=<root>
  (<N> nodes), …` / `partial <commit>, graphify <version>; missing: <name>,
  …` / `unscoped root scan <commit>, graphify <version>; <reason>` /
  `skipped (<reason>)` / `rebuild failed (<step>: <reason>)` / `not
  available`. A non-zero relink step (4) appends `; relink failed
  (<reason>)` to whichever stamp was formed. Plus a `Graph scopes` block of
  at most 12 lines: one line per scope (name, root, node count; when step 4
  ran, `; relink <R> repaired / <U> unresolved[ / <A> self-copy]; stubs <S>
  relinked / <D> left` — the summary's stub counts are build-wide totals,
  so write the per-scope pair only after one extra aggregate pass for it;
  otherwise put the pair once on the calls-dropped line), the `invisible
  under …` lines, rejected paths, overlap warnings, and one extra line when
  the relink summary shows any: `cross-scope calls dropped: <importing
  scope>: <scope pair>=<n>, … (kept <K>)`. Root text may shorten (`…`) to
  fit the cap; counts never disappear.
- Never: `graphify update` (any path); `graphify extract .` outside the
  `unscoped` scope; `cluster-only` without `--graph`; `--force`; an
  env-prefixed graphify command (an env prefix may not match the shell
  permission pattern; `--no-label` does the same job). Once scopes exist,
  no step runs an unscoped rebuild over `graphify-out/`. Graphify never runs
  inside a `!`-injected snippet.

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
