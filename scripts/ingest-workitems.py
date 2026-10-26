#!/usr/bin/env python3
"""
ingest-workitems.py — convert a task source into the canonical work item format.

The pipeline never reads your task tracker directly. It reads
`.workitems/`, which this script generates. Swap the source and no
agent, prompt, or command changes.

SOURCES
    --from-html FILE        HTML breakdown with ID/Task/P/SP/Deps tables
    --from-csv FILE_OR_URL  CSV/TSV export, or a published Google Sheet URL
    --from-appflowy         AppFlowy Cloud database rows (see below)

DONE ITEMS
    Tickets whose status matches a "done" value are written to
    `items/done/<ID>.md` instead of `items/<ID>.md`, and dropped from the
    main table in WORKITEMS.md (a one-line count is kept). This is purely a
    read-side split — the tracker (AppFlowy / sheet / HTML) is still the only
    place status is ever set. Rerunning the script moves a ticket between
    `items/` and `items/done/` automatically as its tracked status changes.

    Defaults: done, complete, completed, closed (case-insensitive).
    Add more with --done-status, repeatable:

        ./ingest-workitems.py --from-csv sheet.tsv --out .workitems \
            --done-status shipped --done-status merged

APPFLOWY — FIRST RUN
    Credentials come from the environment, never from a file you might commit:

        export APPFLOWY_URL=https://task-mgt.example.com
        export APPFLOWY_EMAIL=you@example.com
        export APPFLOWY_PASSWORD=...
        # or, if you already have a JWT:
        export APPFLOWY_TOKEN=eyJ...

    Then discover, in this order:

        ./ingest-workitems.py --from-appflowy --list-databases
        ./ingest-workitems.py --from-appflowy --database <id> --list-fields
        ./ingest-workitems.py --from-appflowy --database <id> --sample-row

    `--list-fields` prints your actual column names. Put them in a config file
    (suggested: .workitems/appflowy.json) so you don't retype them:

        {
          "url": "https://task-mgt.example.com",
          "workspace": "43c08af4-...",
          "database": "4070083a-...",
          "field_map": {
            "id": "Ticket",
            "title": "Name",
            "description": "Description",
            "dod": "Definition of Done",
            "priority": "Priority",
            "points": "Story Points",
            "deps": "Blocked by",
            "owner": "Assignee",
            "status": "Status"
          }
        }

    Only `id` and `title` are required. Anything unmapped is left blank rather
    than guessed at.

        ./ingest-workitems.py --from-appflowy \
            --config .workitems/appflowy.json \
            --out .workitems

OUTPUT (identical for every source)
    <out>/WORKITEMS.md           compact index — what the planner and /tickets read
    <out>/items/<ID>.md          full detail per active item — read on demand
    <out>/items/done/<ID>.md     full detail per done item — read on demand
    <out>/TRACKING.md            "Tracking: yes" + sources, counts, last ingest date
                                 (`/init` creates it as "Tracking: none" in repos
                                 with no tracker; the first successful run here
                                 flips it, so the answer to "are tickets tracked
                                 in this repo?" is always one file)
"""

import argparse
import hashlib
import html as htmllib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# Identifier scheme: [Prefix]-S[num]-T[num] or [Prefix]-T[num] by default.
# Matches both E-series (E1-S1-T1) and A-series (A1-S1-T1, A1-T1), or any letter prefix.
DEFAULT_ID_PATTERN = r"\b([A-Za-z]+\d*-(?:S\d+-)?T\d+)\b"

# Status values (case-insensitive) treated as "done" for the items/done/
# split. Extend per-run with --done-status; this is read-side sorting only —
# it never writes a status back to the tracker.
DEFAULT_DONE_STATUSES = {"done", "complete", "completed", "closed"}

CANONICAL_FIELDS = [
    "id", "title", "description", "dod",
    "priority", "points", "deps", "owner", "status",
    # Hierarchy, when the source has it (a Level/M column, or nesting).
    # A task's parent story usually carries the "as a X, I want Y so that Z"
    # that the task itself lacks — that is the intent the planner needs.
    "story", "story_title", "user_story", "epic_title",
]


# ---------------------------------------------------------------- shared ---

def natural_sort_key(s: str):
    """Sort alphanumeric strings naturally (e.g. E1-S1-T2 before E1-S1-T10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", str(s))]


def strip_tags(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", htmllib.unescape(text)).strip()


def split_dod(body: str):
    """Isolate a trailing 'DOD:' clause — it maps onto the spec's acceptance."""
    m = re.search(r"\bDOD\s*:\s*(.+)$", body, flags=re.S | re.I)
    if not m:
        return body.strip(), ""
    return body[: m.start()].strip(), m.group(1).strip()


def make_item(raw: dict, id_re: re.Pattern) -> dict:
    """Normalise a partially-filled dict into a complete canonical item."""
    item = {k: (raw.get(k) or "") for k in CANONICAL_FIELDS}
    if not isinstance(item["deps"], (str, list)):
        item["deps"] = ""

    item["epic"] = raw.get("epic") or ""
    if not item["epic"]:
        em = re.match(r"([A-Za-z]+\d*)", str(item["id"]))
        if em:
            item["epic"] = em.group(1).upper()

    if not item["title"]:
        head = re.match(r"(.{0,110}?)(?:\.\s|\s{2,}|$)", item["description"] or "")
        item["title"] = (head.group(1) if head else item["description"][:110]).strip(" .")

    if not item["dod"]:
        item["description"], item["dod"] = split_dod(item["description"])

    deps = raw.get("deps") or ""
    joined = " ".join(str(d) for d in deps) if isinstance(deps, list) else str(deps)
    item["deps"] = id_re.findall(joined)

    for k in ("priority", "points"):
        item[k] = item[k] or "—"

    return item


def is_done_item(item: dict, done_statuses: set) -> bool:
    return str(item.get("status") or "").strip().lower() in done_statuses


def write_index(items, out_dir: Path, source_name: str, source_hash: str,
                done_statuses: set):
    active = [it for it in items if not is_done_item(it, done_statuses)]
    done = [it for it in items if is_done_item(it, done_statuses)]

    lines = [
        f"# Work items — {source_name}",
        "",
        "```",
        f"Generated:    {datetime.now().isoformat(timespec='seconds')}",
        f"Source:       {source_name}",
        f"Source hash:  {source_hash}",
        f"Item count:   {len(items)} ({len(active)} active, {len(done)} done)",
        "```",
        "",
        "> Generated by `scripts/ingest-workitems.py`. Do not edit by hand —",
        "> regenerate from the source, or the hash stops meaning anything.",
        ">",
        "> **Status is set on the tracker, never here.** Done items are",
        "> sorted into `items/done/` for a shorter list below, but that sort",
        "> is read-side only — mark a ticket done in AppFlowy / the sheet /",
        "> the HTML source, then rerun this script. It moves automatically.",
        ">",
        "> **SP is effort, not risk.** Story points say how much work an item",
        "> is. They say nothing about blast radius. A 2-point change to a path",
        "> on the project's T3 floor is still T3. Never let a point value pick",
        "> a build agent — that is the architect's call against the floor.",
        "",
        "Full detail for any active item is in `items/<ID>.md`; done items are",
        "in `items/done/<ID>.md`. Read this index to choose what to work on;",
        "read the item file when you plan it.",
        "",
    ]

    has_status = any(i.get("status") for i in active)
    if has_status:
        lines += ["| ID | Title | Status | P | SP | Deps | Owner |",
                  "|---|---|---|---|---|---|---|"]
    else:
        lines += ["| ID | Title | P | SP | Deps | Owner |",
                  "|---|---|---|---|---|---|"]

    for it in sorted(active, key=lambda x: natural_sort_key(x["id"])):
        title = it["title"].replace("|", "\\|")
        if len(title) > 80:
            title = title[:77] + "..."
        deps = ", ".join(it["deps"]) if it["deps"] else "—"
        owner = (it["owner"] or "—").replace("|", "\\|")
        cells = [f"`{it['id']}`", title]
        if has_status:
            cells.append(it.get("status") or "—")
        cells += [str(it["priority"]), str(it["points"]), deps, owner]
        lines.append("| " + " | ".join(cells) + " |")

    if done:
        lines += ["", f"**Done:** {len(done)} item(s), not listed above — see "
                       f"`items/done/`."]

    groups = {}
    for it in active:
        g = it.get("epic") or "—"
        groups.setdefault(g, {"count": 0, "sp": 0})
        groups[g]["count"] += 1
        if str(it["points"]).isdigit():
            groups[g]["sp"] += int(it["points"])

    lines += ["", "## By epic (active only)", "", "| Epic | Items | SP |", "|---|---|---|"]
    for g in sorted(groups, key=natural_sort_key):
        lines.append(f"| {g} | {groups[g]['count']} | {groups[g]['sp']} |")
    lines.append("")

    (out_dir / "WORKITEMS.md").write_text("\n".join(lines), encoding="utf-8")


def write_tracking(out_dir: Path, source_name: str, source_hash: str,
                   n_total: int, n_done: int):
    lines = [
        "# Work item tracking",
        "",
        "Tracking: yes",
        "",
        f"- Sources: {source_name}",
        f"- Items: {n_total} ({n_total - n_done} active, {n_done} done)",
        f"- Last ingest: {datetime.now().strftime('%Y-%m-%d')}",
        f"- Source hash: {source_hash}",
        "",
        "> Generated by `scripts/ingest-workitems.py`. Do not edit by hand —",
        "> rerun the script. Index: `WORKITEMS.md`; detail: `items/<ID>.md`,",
        "> finished tickets in `items/done/`.",
        "",
    ]
    (out_dir / "TRACKING.md").write_text("\n".join(lines), encoding="utf-8")


def write_items(items, out_dir: Path, source_name: str, done_statuses: set):
    items_dir = out_dir / "items"
    done_dir = items_dir / "done"
    items_dir.mkdir(parents=True, exist_ok=True)
    done_dir.mkdir(parents=True, exist_ok=True)
    by_id = {i["id"]: i for i in items}

    current_ids = {i["id"] for i in items}

    # Stale = no longer in the source at all, wherever it currently sits.
    existing = {f.stem: f for f in items_dir.glob("*.md")}
    existing.update({f.stem: f for f in done_dir.glob("*.md")})
    stale = [f for stem, f in existing.items() if stem not in current_ids]
    if stale:
        print(f"removing {len(stale)} item file(s) no longer in the source: "
              f"{', '.join(sorted(f.stem for f in stale))}", file=sys.stderr)
        for f in stale:
            f.unlink()

    moved = []
    for it in items:
        done = is_done_item(it, done_statuses)
        target_dir = done_dir if done else items_dir
        other_dir = items_dir if done else done_dir

        # Status changed since the last run — clear the copy in the old spot
        # so a ticket never appears in both items/ and items/done/ at once.
        stale_copy = other_dir / f"{it['id']}.md"
        if stale_copy.exists():
            stale_copy.unlink()
            moved.append(it["id"])

        out = [f"# {it['id']}", ""]
        out += [
            "```",
            f"Ticket:    {it['id']}",
            f"Epic:      {it.get('epic') or '—'}",
            f"Status:    {it.get('status') or '—'}",
            f"Priority:  {it['priority']}",
            f"Points:    {it['points']}",
            f"Owner:     {it['owner'] or '—'}",
            f"Source:    {', '.join(it.get('_sources') or [source_name])}",
            "```",
            "",
            f"## {it['title']}",
            "",
            it["description"] or "_No description beyond the title in this source._",
            "",
        ]

        if it.get("user_story") or it.get("story_title"):
            out += ["## Why — parent story", ""]
            if it.get("story"):
                out.append(f"**{it['story']} — {it.get('story_title', '')}**".rstrip(" —"))
                out.append("")
            if it.get("user_story"):
                out += [it["user_story"], ""]
            if it.get("epic_title"):
                out += [f"_Epic: {it['epic_title']}_", ""]
            out += [
                "> This is the intent the task title omits. Plan against it,",
                "> not against the title alone.",
                "",
            ]

        if it["dod"]:
            out += [
                "## Definition of done", "",
                it["dod"], "",
                "> Carry this into the spec's acceptance section verbatim. It",
                "> is the ticket's own statement of what finished means — do",
                "> not restate it in weaker words.",
                "",
            ]

        out += ["## Dependencies", ""]
        if it["deps"]:
            for d in it["deps"]:
                dep = by_id.get(d)
                suffix = f" — {dep['title']}" if dep else " — *(not in this source)*"
                out.append(f"- `{d}`{suffix}")
        else:
            out.append("_None recorded._")
        out.append("")

        blocks = sorted(o["id"] for o in items if it["id"] in o["deps"])
        if blocks:
            out += ["## Blocks", ""] + [f"- `{b}`" for b in blocks] + [""]

        out += [
            "## Pipeline", "",
            f"- Plan with `/plan {it['id']} <what you want>`",
            "- Tier is assigned by `arch` against the project's T3 floor.",
            "  The point value above has no bearing on it.",
            "",
        ]

        (target_dir / f"{it['id']}.md").write_text("\n".join(out), encoding="utf-8")

    if moved:
        print(f"moved {len(moved)} item(s) between items/ and items/done/ "
              f"(status changed since last run): {', '.join(sorted(moved))}",
              file=sys.stderr)


# ------------------------------------------------------------ html source ---

def parse_html(path: Path, id_re: re.Pattern):
    raw = path.read_text(encoding="utf-8", errors="replace")
    items, seen = [], set()

    for table in re.findall(r"<table.*?</table>", raw, flags=re.S):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, flags=re.S)
        if not rows:
            continue
        header = [strip_tags(c).lower()
                  for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", rows[0], flags=re.S)]
        if "id" not in header or "task" not in header:
            continue

        def col(*names):
            for n in names:
                if n in header:
                    return header.index(n)
            return None

        idx = {
            "id": col("id"), "task": col("task"),
            "priority": col("p", "priority"), "points": col("sp", "points"),
            "deps": col("deps", "dependencies"), "owner": col("owner", "owners"),
            "status": col("status"),
        }

        for row in rows[1:]:
            cells = [strip_tags(c)
                     for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S)]
            if idx["id"] is None or idx["id"] >= len(cells):
                continue
            item_id = cells[idx["id"]].strip()
            if not id_re.fullmatch(item_id) or item_id in seen:
                continue
            seen.add(item_id)

            def get(key):
                i = idx[key]
                return cells[i].strip() if i is not None and i < len(cells) else ""

            items.append(make_item({
                "id": item_id,
                "description": get("task"),
                "priority": get("priority"),
                "points": get("points"),
                "deps": get("deps"),
                "owner": get("owner"),
                "status": get("status"),
            }, id_re))

    return items


# ------------------------------------------------- csv / sheet / tsv source ---

def _load_delimited(src: str):
    """Read a CSV/TSV from a path or an http(s) URL into rows of dicts."""
    import csv
    import io

    if src.startswith(("http://", "https://")):
        req = urllib.request.Request(
            src,
            headers={
                "Accept": "text/csv,text/plain;q=0.9,*/*;q=0.8",
                "User-Agent": "Mozilla/5.0 (compatible; ingest-workitems/1.0)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                text = r.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as e:
            raise RuntimeError(f"cannot fetch {src}: {e}") from None
        if text.lstrip()[:15].lower().startswith("<!doctype") or "<html" in text[:400].lower():
            raise RuntimeError(
                "got HTML, not CSV — the sheet is not publicly readable.\n"
                "  File > Share > Publish to web, or download it and pass the path.")
    else:
        text = Path(src).read_text(encoding="utf-8", errors="replace")

    text = text.lstrip("\ufeff")  # strip UTF-8 BOM if present
    sample = text[:4096]
    delim = "\t" if sample.count("\t") > sample.count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delim))


def parse_csv(src: str, id_re: re.Pattern, id_column: str = ""):
    """
    Parse a flat table that may encode hierarchy in a `Level` or `M` column
    (EPIC / STORY / TASK), as exported from Google Sheets.

    Only TASK-level rows become work items — those are the buildable unit.
    Epic and story rows are kept as context and folded into their children,
    because the story row is where the user story lives and the task rows
    are usually just a title.
    """
    rows = _load_delimited(src)
    if not rows:
        return []

    # Tolerant header lookup: strip, lowercase, ignore punctuation.
    def norm(s):
        return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

    headers = {norm(k): k for k in rows[0].keys() if k}

    def col(row, *names, default=""):
        for n in names:
            key = headers.get(norm(n))
            if key is not None:
                val = (row.get(key) or "").strip()
                if val:
                    return val
        return default

    # Supports "Level", "M" (Model/Milestone column), or "Type"
    has_level = any(k in headers for k in ("level", "m", "type"))
    items = []
    epics, stories = {}, {}
    cur_epic = cur_story = ""

    for row in rows:
        row_id = col(row, id_column, "id", "taskid", "key", "ticket", "workitemid") if id_column \
            else col(row, "id", "taskid", "key", "ticket", "workitemid")
        if not row_id:
            for value in row.values():
                found = id_re.search(str(value or ""))
                if found:
                    row_id = found.group(0)
                    break
        if not row_id:
            continue

        level = col(row, "level", "m", "type").upper() if has_level else ""
        title = col(row, "titledescription", "title", "task", "name", "summary", "description")
        narrative = col(row, "userstory", "story", "notes", "detail")

        if not level:  # infer from the id shape and regex match
            if id_re.search(row_id):
                level = "TASK"
            else:
                depth = row_id.count("-")
                level = ("EPIC", "STORY", "TASK")[min(depth, 2)]

        if level == "EPIC":
            cur_epic, cur_story = row_id, ""
            epics[row_id] = {"title": title, "narrative": narrative}
            continue
        if level == "STORY":
            cur_story = row_id
            stories[row_id] = {
                "title": title,
                "narrative": narrative,
                "owner": col(row, "owner", "assignee", "assigned"),
                "epic": cur_epic,
            }
            continue
        if level not in ("TASK", "SUBTASK"):
            continue

        if not id_re.search(row_id):
            continue

        # Prefer the row's own parent id over positional state where derivable.
        parent_story = cur_story
        m = re.match(r"(.+)-[A-Za-z]+\d+$", row_id)
        if m:
            prefix = m.group(1)
            if prefix in stories:
                parent_story = prefix
            elif prefix in epics:
                cur_epic = prefix

        story = stories.get(parent_story, {})
        epic_id = story.get("epic", cur_epic)

        items.append(make_item({
            "id": id_re.search(row_id).group(0),
            "title": title,
            "description": col(row, "description", "detail", "notes"),
            "dod": col(row, "dod", "definitionofdone", "acceptancecriteria"),
            "priority": col(row, "p", "priority"),
            "points": col(row, "sp", "points", "storypoints", "estimate"),
            "deps": col(row, "deps", "dependencies", "blockedby"),
            "owner": col(row, "owner", "assignee", "assigned") or story.get("owner", ""),
            "status": col(row, "status", "state"),
            "epic": epic_id,
            "story": parent_story,
            "story_title": story.get("title", ""),
            "user_story": story.get("narrative", ""),
            "epic_title": epics.get(epic_id, {}).get("title", ""),
        }, id_re))

    return items


# ----------------------------------------------------------------- merge ---

def merge_items(sources, id_re: re.Pattern):
    """
    Combine several sources into one item set, keyed by ID.

    Precedence is source order: the first source to supply a non-empty value
    for a field wins. So put your richest content source first and overlay
    live status from the tracker after it. Provenance is recorded per item so
    a surprising value can be traced back to where it came from.
    """
    merged = {}
    for label, items in sources:
        for it in items:
            tgt = merged.setdefault(it["id"], {"_sources": []})
            for field, value in it.items():
                if field.startswith("_"):
                    continue
                empty = value in ("", "—", [], None)
                if not empty and tgt.get(field) in (None, "", "—", []):
                    tgt[field] = value
            if label not in tgt["_sources"]:
                tgt["_sources"].append(label)

    out = []
    for item_id, data in merged.items():
        data["id"] = item_id
        srcs = data.pop("_sources")
        item = make_item(data, id_re)
        item["_sources"] = srcs
        out.append(item)
    return out


# -------------------------------------------------------- appflowy source ---

class AppFlowyError(RuntimeError):
    pass


class AppFlowy:
    def __init__(self, base_url: str, token: str = "", timeout: int = 30):
        self.base = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _request(self, method, path, params=None, body=None, auth=True):
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/json")
        if data:
            req.add_header("Content-Type", "application/json")
        if auth and self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:400]
            raise AppFlowyError(f"HTTP {e.code} on {method} {path}\n  {detail}") from None
        except urllib.error.URLError as e:
            raise AppFlowyError(f"cannot reach {self.base}: {e.reason}") from None

    def login(self, email, password):
        resp = self._request("POST", "/gotrue/token",
                             params={"grant_type": "password"},
                             body={"email": email, "password": password},
                             auth=False)
        token = resp.get("access_token")
        if not token:
            raise AppFlowyError(f"no access_token in response: {list(resp)}")
        self.token = token
        return token

    @staticmethod
    def _payload(resp):
        if isinstance(resp, dict):
            for key in ("data", "items", "result"):
                if key in resp:
                    return resp[key]
        return resp

    def workspaces(self):
        return self._payload(self._request("GET", "/api/workspace"))

    def databases(self, ws):
        return self._payload(self._request("GET", f"/api/workspace/{ws}/database"))

    def fields(self, ws, db):
        return self._payload(
            self._request("GET", f"/api/workspace/{ws}/database/{db}/fields"))

    def row_ids(self, ws, db):
        return self._payload(
            self._request("GET", f"/api/workspace/{ws}/database/{db}/row"))

    def row_details(self, ws, db, ids):
        out = []
        for i in range(0, len(ids), 50):
            resp = self._request("GET", f"/api/workspace/{ws}/database/{db}/row/detail",
                                 params={"ids": ",".join(ids[i:i + 50])})
            payload = self._payload(resp)
            out.extend(payload if isinstance(payload, list) else [payload])
        return out


def _extract_id(obj):
    if isinstance(obj, dict):
        for k in ("id", "row_id", "database_id", "view_id", "object_id", "uuid"):
            if isinstance(obj.get(k), str):
                return obj[k]
        return ""
    return obj if isinstance(obj, str) else ""


def _text_of(v):
    if v is None:
        return ""
    if isinstance(v, (str, int, float)):
        return str(v)
    if isinstance(v, list):
        return ", ".join(_text_of(x) for x in v if x is not None)
    if isinstance(v, dict):
        for k in ("value", "text", "content", "name", "title", "data"):
            if k in v:
                return _text_of(v[k])
        return ""
    return str(v)


def _row_cells(row: dict) -> dict:
    container = None
    for key in ("cells", "fields", "data"):
        if isinstance(row.get(key), (dict, list)):
            container = row[key]
            break
    if container is None:
        container = row

    cells = {}
    if isinstance(container, dict):
        for name, val in container.items():
            cells[str(name)] = _text_of(val)
    elif isinstance(container, list):
        for entry in container:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name") or entry.get("field_name") or entry.get("field_id")
            if name:
                cells[str(name)] = _text_of(
                    entry.get("value", entry.get("text", entry.get("data"))))
    return cells


def parse_appflowy(cfg: dict, args, id_re: re.Pattern):
    base = cfg.get("url") or os.environ.get("APPFLOWY_URL", "")
    if not base:
        raise AppFlowyError("no AppFlowy URL (set APPFLOWY_URL or put 'url' in config)")

    client = AppFlowy(base, os.environ.get("APPFLOWY_TOKEN", ""))
    if not client.token:
        email = os.environ.get("APPFLOWY_EMAIL", "")
        password = os.environ.get("APPFLOWY_PASSWORD", "")
        if not (email and password):
            raise AppFlowyError("no credentials — set APPFLOWY_TOKEN, "
                                "or APPFLOWY_EMAIL + APPFLOWY_PASSWORD")
        client.login(email, password)
        print("authenticated", file=sys.stderr)

    ws = args.workspace or cfg.get("workspace") or os.environ.get("APPFLOWY_WORKSPACE", "")
    if not ws:
        print(json.dumps(client.workspaces(), indent=2)[:3000])
        raise AppFlowyError("no workspace given — pick one above, pass --workspace")

    if args.list_databases:
        print(json.dumps(client.databases(ws), indent=2)[:6000])
        print("\nPick the database whose views include the id from your AppFlowy "
              "URL, then rerun with --database <database_id> --list-fields",
              file=sys.stderr)
        return None

    db = args.database or cfg.get("database", "")
    if not db:
        raise AppFlowyError("no database given — run --list-databases first")

    if args.list_fields:
        print(json.dumps(client.fields(ws, db), indent=2)[:6000])
        print("\nCopy the column names above into your config's field_map.",
              file=sys.stderr)
        return None

    ids = [i for i in (_extract_id(x) for x in (client.row_ids(ws, db) or [])) if i]
    if not ids:
        raise AppFlowyError("no row ids returned — check the database id")
    print(f"{len(ids)} rows", file=sys.stderr)

    rows = client.row_details(ws, db, ids)

    if args.sample_row:
        print(json.dumps(rows[0] if rows else {}, indent=2)[:6000])
        print("\nFlattened to:", file=sys.stderr)
        print(json.dumps(_row_cells(rows[0]) if rows else {}, indent=2)[:3000])
        return None

    fmap = cfg.get("field_map", {})
    if not fmap.get("id") or not fmap.get("title"):
        raise AppFlowyError("field_map needs at least 'id' and 'title' — run --list-fields")

    items, skipped = [], 0
    for row in rows:
        cells = _row_cells(row)
        raw = {}
        for canon in CANONICAL_FIELDS:
            col = fmap.get(canon)
            if col:
                raw[canon] = cells.get(col, "")
        found = id_re.search(str(raw.get("id") or ""))
        if not found:
            skipped += 1
            continue
        raw["id"] = found.group(0)
        items.append(make_item(raw, id_re))

    if skipped:
        print(f"skipped {skipped} rows with no id matching {id_re.pattern}",
              file=sys.stderr)
    return items


# ------------------------------------------------------------------ main ---

def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-html", type=Path, metavar="FILE")
    ap.add_argument("--from-csv", metavar="FILE_OR_URL",
                    help="CSV/TSV export, or a published Google Sheet URL")
    ap.add_argument("--from-appflowy", action="store_true")
    ap.add_argument("--config", type=Path, help="AppFlowy config JSON")
    ap.add_argument("--workspace", help="override workspace id")
    ap.add_argument("--database", help="override database id")
    ap.add_argument("--list-databases", action="store_true")
    ap.add_argument("--list-fields", action="store_true")
    ap.add_argument("--sample-row", action="store_true",
                    help="dump one raw row and its flattening, then exit")
    ap.add_argument("--id-pattern", default=DEFAULT_ID_PATTERN)
    ap.add_argument("--id-column", default="",
                    help="column holding the identifier, if not named ID")
    ap.add_argument("--prefix", help="filter items by ID prefix (e.g. 'A' or 'E')")
    ap.add_argument("--epic", help="filter items by epic ID (e.g. 'A1' or 'E1')")
    ap.add_argument("--done-status", action="append", default=[],
                    help="additional status value (case-insensitive) treated "
                         "as done, sorted into items/done/. Repeatable. "
                         "Defaults already cover: " +
                         ", ".join(sorted(DEFAULT_DONE_STATUSES)))
    ap.add_argument("--out", type=Path, help="e.g. <repo>/.workitems")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-prune", action="store_true",
                    help="confirm deletion when >=40%% of existing items would "
                         "be removed in one run")
    args = ap.parse_args()

    id_re = re.compile(args.id_pattern)
    done_statuses = DEFAULT_DONE_STATUSES | {
        s.strip().lower() for s in args.done_status if s.strip()
    }
    discovery = args.list_databases or args.list_fields or args.sample_row

    if not args.out and not discovery and not args.dry_run:
        ap.error("--out is required unless discovering or --dry-run")

    if not (args.from_html or args.from_csv or args.from_appflowy):
        ap.error("pick at least one source: --from-html, --from-csv, --from-appflowy")

    sources = []
    try:
        if args.from_html:
            if not args.from_html.is_file():
                ap.error(f"not a file: {args.from_html}")
            got = parse_html(args.from_html, id_re)
            print(f"  {args.from_html.name}: {len(got)} items", file=sys.stderr)
            sources.append((args.from_html.name, got))

        if args.from_csv:
            got = parse_csv(args.from_csv, id_re, args.id_column)
            label = args.from_csv.split("/")[-1][:40] or "csv"
            print(f"  {label}: {len(got)} items", file=sys.stderr)
            sources.append((label, got))

        if args.from_appflowy:
            cfg = {}
            if args.config:
                if not args.config.is_file():
                    ap.error(f"no config at {args.config}")
                cfg = json.loads(args.config.read_text())
            got = parse_appflowy(cfg, args, id_re)
            if got is None:
                return 0
            label = f"AppFlowy:{(cfg.get('database') or args.database or '')[:8]}"
            print(f"  {label}: {len(got)} items", file=sys.stderr)
            sources.append((label, got))
    except AppFlowyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    items = merge_items(sources, id_re) if len(sources) > 1 else sources[0][1]
    for it in items:
        it.setdefault("_sources", [sources[0][0]])

    # Optional prefix or epic filtering
    if args.prefix:
        pref = args.prefix.strip().upper()
        items = [i for i in items if i["id"].upper().startswith(pref)]
    if args.epic:
        target_epic = args.epic.strip().upper()
        items = [i for i in items if (i.get("epic") or "").upper() == target_epic]

    source_name = " + ".join(label for label, _ in sources)
    source_hash = hashlib.sha256(
        json.dumps(sorted(i["id"] for i in items)).encode()).hexdigest()[:12]

    if not items:
        print("No work items found. Check the id pattern and the field map.",
              file=sys.stderr)
        return 1

    total_sp = sum(int(i["points"]) for i in items if str(i["points"]).isdigit())
    n_done = sum(1 for i in items if is_done_item(i, done_statuses))
    print(f"parsed {len(items)} items ({n_done} done), {total_sp} SP, "
          f"source hash {source_hash}")

    if args.dry_run:
        for it in sorted(items, key=lambda x: natural_sort_key(x["id"]))[:15]:
            done_flag = " [done]" if is_done_item(it, done_statuses) else ""
            print(f"  {it['id']:<14}{it['priority']:<4}{str(it['points']):>3}SP  "
                  f"{it['title'][:58]}{done_flag}")
        if len(items) > 15:
            print(f"  ... and {len(items) - 15} more")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)

    items_dir = args.out / "items"
    done_dir = items_dir / "done"
    existing = []
    if items_dir.is_dir():
        existing += list(items_dir.glob("*.md"))
    if done_dir.is_dir():
        existing += list(done_dir.glob("*.md"))
    current_ids = {i["id"] for i in items}
    stale = [f for f in existing if f.stem not in current_ids]
    total_before = len(existing) or 1
    suspicious = len(stale) >= 5 and (len(stale) / total_before) >= 0.4

    if stale and suspicious and not args.force_prune:
        print(f"\nWARNING: this run would remove {len(stale)} of {len(existing)} "
              f"existing item files:", file=sys.stderr)
        for f in sorted(stale, key=lambda p: natural_sort_key(p.stem))[:15]:
            print(f"    {f.stem}", file=sys.stderr)
        if len(stale) > 15:
            print(f"    ... and {len(stale) - 15} more", file=sys.stderr)
        print("\nThat's a lot at once for one run — check whether a --from-* "
              "flag was left off a multi-source command before assuming this "
              "many tickets actually vanished. Nothing was written; the index "
              "and items/ are untouched. If this removal is real, rerun with "
              "--force-prune.", file=sys.stderr)
        return 3

    write_index(items, args.out, source_name, source_hash, done_statuses)
    write_items(items, args.out, source_name, done_statuses)
    write_tracking(args.out, source_name, source_hash, len(items), n_done)
    print(f"wrote {args.out / 'WORKITEMS.md'} and {len(items)} item files "
          f"({len(items) - n_done} in items/, {n_done} in items/done/)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
