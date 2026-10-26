#!/usr/bin/env python3
"""
merge-claude-settings.py <settings.json> <snippet.json>

Adds the pipeline's hook (and any permission rules) to a Claude Code
settings.json WITHOUT touching anything you already have there.

  - hooks:        a matcher group is appended only if no existing group for the
                  same event has the same matcher and the same hook command
  - permissions:  allow / deny / ask lists are unioned, order preserved
  - other keys:   set only when absent, never overwritten

Idempotent — a second run reports "no changes" and writes nothing. When it does
change the file it first copies it to <settings>.bak.<timestamp>. If the
existing file is not valid JSON it stops and touches nothing.
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


def load(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8") or "null") or default
    except json.JSONDecodeError as e:
        sys.exit(f"{path} is not valid JSON ({e}); not touching it. Merge by hand from the snippet.")


def hook_commands(group: dict):
    return {h.get("command") for h in group.get("hooks", []) if isinstance(h, dict)}


def merge(target: dict, snippet: dict):
    changes = []

    for event, groups in (snippet.get("hooks") or {}).items():
        existing = target.setdefault("hooks", {}).setdefault(event, [])
        for g in groups:
            want = hook_commands(g)
            already = any(
                eg.get("matcher") == g.get("matcher") and want <= hook_commands(eg)
                for eg in existing
            )
            if not already:
                existing.append(g)
                changes.append(f"hooks.{event}[{g.get('matcher', '*')}]")

    for kind, rules in (snippet.get("permissions") or {}).items():
        if not isinstance(rules, list):
            continue
        cur = target.setdefault("permissions", {}).setdefault(kind, [])
        for r in rules:
            if r not in cur:
                cur.append(r)
                changes.append(f"permissions.{kind}: {r}")

    for k, v in snippet.items():
        if k in ("hooks", "permissions"):
            continue
        if k not in target:
            target[k] = v
            changes.append(k)

    return changes


def main() -> int:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    settings_path, snippet_path = Path(sys.argv[1]).expanduser(), Path(sys.argv[2])
    snippet = load(snippet_path, None)
    if snippet is None:
        sys.exit(f"snippet not found: {snippet_path}")

    target = load(settings_path, {})
    changes = merge(target, snippet)
    if not changes:
        print(f"{settings_path}: no changes (pipeline settings already present)")
        return 0

    if settings_path.exists():
        backup = settings_path.with_name(
            f"{settings_path.name}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}")
        shutil.copy2(settings_path, backup)
        print(f"backed up {settings_path} -> {backup}")
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(target, indent=2) + "\n", encoding="utf-8")
    for c in changes:
        print(f"  + {c}")
    print(f"{settings_path}: updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
