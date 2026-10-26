#!/usr/bin/env python3
"""
check-handoff-write.py — Claude Code PreToolUse hook (matcher: Write).

Guards the shared handoff record. In OpenCode this job belongs to the `scribe`
subagent; here it is a deterministic check that costs no tokens and cannot be
talked out of it. It blocks a Write into .handoff/{1-plan,2-spec,3-report}/ when:

  1. the filename is not <stem>.<plan|spec|report>.md for that directory
     (this is what catches `$ARGUMENTS` leaking a sentence or a doubled
     extension such as `<stem>.plan.md.spec.md` into a filename);
  2. the file already exists — a handoff document is a record of what one
     session did, and overwriting it destroys that record;
  3. the content's header block is missing a field, still holds an unfilled
     template placeholder, disagrees with the filename on Stem/Stage, or has a
     Status/Tier value the stage does not allow.

Anything else passes: other paths, other tools, Edit (a report's status line
legitimately gets edited later), and any input this script cannot parse — it
fails open, because a broken guard must never stop real work.

Exit 2 blocks the write and sends stderr back to Claude as the reason.
"""

import json
import os
import re
import sys

DIRS = {"1-plan": "plan", "2-spec": "spec", "3-report": "report"}
PATH_RE = re.compile(r"(?:^|/)\.handoff/(1-plan|2-spec|3-report)/([^/]+)$")
NAME_RE = re.compile(r"^(?P<stem>\d{4}-\d{2}-\d{2}-[A-Za-z0-9][A-Za-z0-9_-]*)\.(?P<kind>plan|spec|report)\.md$")
HEADER_RE = re.compile(r"^\s*(Stem|Stage|Status|Tier|Pipeline|Model):[ \t]*(.*?)\s*$")
REQUIRED = ("Stem", "Stage", "Status", "Tier", "Pipeline", "Model")

STATUS = {
    "plan": {"draft", "ready"},
    "spec": {"ready", "replan", "blocked"},
    "report": {"complete", "partial", "stopped", "blocked"},
}
TIERS = {"T1", "T2", "T3"}


def block(msg: str) -> None:
    print(f"handoff guard: {msg}", file=sys.stderr)
    sys.exit(2)


def read_header(content: str) -> dict:
    found = {}
    for line in content.splitlines()[:40]:
        m = HEADER_RE.match(line)
        if m and m.group(1) not in found:
            found[m.group(1)] = m.group(2)
    return found


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(data, dict) or data.get("tool_name") != "Write":
        return 0

    tool_input = data.get("tool_input") or {}
    path = str(tool_input.get("file_path") or "").replace("\\", "/")
    m = PATH_RE.search(path)
    if not m:
        return 0

    folder, name = m.groups()
    kind = DIRS[folder]
    if name == ".gitkeep":
        return 0

    nm = NAME_RE.match(name)
    if not nm or nm.group("kind") != kind:
        block(
            f"'{name}' is not a valid name for .handoff/{folder}/. Expected "
            f"<YYYY-MM-DD-slice>.{kind}.md — a date, a slice slug of letters, digits, "
            f"'-' or '_', and exactly one .{kind}.md suffix. Take the stem from the "
            f"document's own Stem: header, never from the raw command argument."
        )
    stem = nm.group("stem")

    full = path if os.path.isabs(path) else os.path.join(str(data.get("cwd") or ""), path)
    if os.path.exists(full):
        block(
            f"{name} already exists. Handoff documents are never overwritten — they "
            f"record what an earlier session did. Stop and tell the human; either "
            f"they delete the old file, or the slice needs a new stem."
        )

    header = read_header(str(tool_input.get("content") or ""))
    missing = [k for k in REQUIRED if k not in header]
    if missing:
        block(
            f"the header block is missing: {', '.join(missing)}. Every handoff "
            f"document starts with Stem, Stage, Status, Tier, Pipeline and Model "
            f"(see .handoff/{kind.upper()}_TEMPLATE.md)."
        )

    for key in ("Pipeline", "Model", "Tier", "Status", "Stem"):
        v = header[key]
        if not v or "<" in v or ">" in v or "|" in v:
            if key == "Tier" and kind == "plan":
                continue
            block(
                f"header field {key}: '{v}' is empty or still a template placeholder. "
                f"Fill it from the value the command supplied; if none was supplied "
                f"write 'unknown' rather than guessing."
            )

    if header["Stem"] != stem:
        block(f"header Stem '{header['Stem']}' does not match the filename stem '{stem}'.")
    if header["Stage"] != kind:
        block(f"header Stage '{header['Stage']}' does not match the folder (expected '{kind}').")
    if header["Status"] not in STATUS[kind]:
        block(f"Status '{header['Status']}' is not valid for a {kind}: use one of {sorted(STATUS[kind])}.")
    if kind != "plan" and header["Tier"] not in TIERS:
        block(f"Tier '{header['Tier']}' must be one of T1, T2, T3 for a {kind}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
