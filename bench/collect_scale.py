"""Scale Labs leaderboards. Method: plain HTML; rows are JSON embedded by Next.js."""
from __future__ import annotations

import json
import re

from .common import INDEPENDENT, CollectorAlert, Row, fetch, next_flight, require_rows, save_raw
from .names import canonicalize

BOARDS = [
    # (url slug, benchmark name, version, note)
    ("swe-atlas", "SWE Atlas", "v1.1", "Scale says v1.1 scores are not comparable with v1.0."),
    ("swe_bench_pro_public_v2", "SWE-Bench Pro V2", "", ""),
    ("swe_bench_pro_public", "SWE-Bench Pro", "", "Scale marks this board deprecated in favour of V2."),
    ("mcp_atlas", "MCP-Atlas", "", ""),
]


def _entry_lists(flight: str):
    """Yield (variant label, entries) for every leaderboard table on the page."""
    seen = set()
    for m in re.finditer(r'"entries":\[', flight):
        start = m.end() - 1
        entries, _ = json.JSONDecoder().raw_decode(flight[start:])
        if not entries or "score" not in entries[0]:
            continue
        key = json.dumps(entries, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        head = flight[max(0, m.start() - 200):m.start()]
        labels = re.findall(r'"label":"([^"]+)"', head)
        yield (labels[-1] if labels else ""), entries


def collect(day: str) -> list[Row]:
    rows: list[Row] = []
    for slug, bench, board_version, board_note in BOARDS:
        url = f"https://labs.scale.com/leaderboard/{slug}"
        html = fetch(url)
        save_raw(day, f"scale_{slug}.html", html)
        flight = next_flight(html)
        footnotes = sorted(set(re.findall(r'"text":"(\*[^"]{3,120})"', flight)))
        board_rows = []
        for label, entries in _entry_lists(flight):
            variant = label.replace(bench, "").strip(" ()-") if label else ""
            name = f"{bench} ({variant})" if variant else bench
            newest = max(e.get("createdAt", "")[:10] for e in entries)
            for e in entries:
                if e.get("deprecated"):
                    continue
                model, setup = canonicalize(e["model"])
                ci = e.get("confidenceInterval_upper")
                notes = [board_note] if board_note else []
                if e["model"].strip().endswith("*") and footnotes:
                    notes.append(footnotes[0].lstrip("*").strip())
                if e.get("contaminationMessage"):
                    notes.append("Contamination: " + e["contaminationMessage"])
                board_rows.append(Row(
                    benchmark=name, version=board_version, model=model,  # Scale's per-row "version" field is an API route, not used
                    model_raw=e["model"], setup=setup, score=float(e["score"]), unit="%",
                    margin_low=(e["score"] - ci) if ci else None,
                    margin_high=(e["score"] + ci) if ci else None,
                    cost=None, cost_basis="", rank=e.get("rank"), source_url=url,
                    trust=INDEPENDENT, source_date=newest, collected=day,
                    note=" | ".join(notes),
                ))
        if not board_rows:
            raise CollectorAlert(f"Scale {slug}: no leaderboard entries found")
        rows += board_rows
    return require_rows(rows, "Scale")
