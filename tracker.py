"""Weekly benchmark tracker.

  python tracker.py collect   # fetch all sources -> data/raw/<date>/, data/clean/<date>.csv, data/alerts/<date>.json
  python tracker.py report    # build reports/<date>-report.md from the newest clean CSV (+ last week's for changes)
  python tracker.py all       # both
"""
from __future__ import annotations

import csv
import dataclasses
import datetime as dt
import json
import sys
import traceback
from pathlib import Path

from bench import collect_aa, collect_arena, collect_gdpx, collect_scale
from bench.common import DATA, ROOT, Row, today
from bench.names import canonicalize

COLLECTORS = {
    "Scale": collect_scale.collect,
    "Artificial Analysis": collect_aa.collect,
    "GDPx (SemiAnalysis)": collect_gdpx.collect,
    "Arena": collect_arena.collect,
}

# Order and labels of the report. Benchmarks not listed here stay in the CSV only.
REPORT = [
    ("SWE Atlas (Overall)", "Coding"),
    ("SWE-Bench Pro V2 (Full)", "Coding (issue fixing)"),
    ("Terminal-Bench 4.0", "Agentic coding"),
    ("MCP-Atlas", "Agentic tool use"),
    ("GDPval-AA", "Work"),
    ("GDPx", "Work (frontier)"),
    ("Agent Arena", "Real-world agents"),
    ("WebDev Arena", "Human preference (optional)"),
]
TOP_N = 12
# Per-benchmark limits on how many rows the public report shows.
# GDPx terms allow quoting but forbid a derivative leaderboard, so the report quotes only the top 3.
# data/clean/ is public (it is in the GitHub repo), so collect() also saves only these rows.
TOP_N_OVERRIDE = {"GDPx": 3}
CREDIT_LINE = {"GDPx": "Quoted from GDPx by SemiAnalysis (top 3 only); full leaderboard at "
                       "[gdpx.semianalysis.com](https://gdpx.semianalysis.com/)."}
# Benchmarks whose top scores sit near 100%: the report adds a line with the top score and
# how many models are too close to call, using only numbers from the table itself.
SPREAD_NOTE = {"SWE-Bench Pro V2 (Full)"}
STALE_DAYS = 30
FIELDS = [f.name for f in dataclasses.fields(Row)]


# ---------------------------------------------------------------- collect
def collect(day: str) -> None:
    rows: list[Row] = []
    alerts: list[dict] = []
    for name, fn in COLLECTORS.items():
        try:
            got = fn(day)
            rows += got
            print(f"  {name}: {len(got)} rows")
        except Exception as e:  # one broken source must not stop the others
            alerts.append({"level": "error", "source": name, "message": f"{type(e).__name__}: {e}"})
            print(f"  {name}: FAILED - {e}")
            traceback.print_exc()

    # The saved data is public: keep only the rows the report may quote for limited sources (GDPx).
    for bench, n in TOP_N_OVERRIDE.items():
        keep = sorted((r for r in rows if r.benchmark == bench), key=lambda r: -r.score)[:n]
        rows = [r for r in rows if r.benchmark != bench] + keep

    # Old-page check: the newest date a publisher shows should be recent.
    limit = (dt.date.fromisoformat(day) - dt.timedelta(days=STALE_DAYS)).isoformat()
    for bench in sorted({r.benchmark for r in rows}):
        newest = max(r.source_date for r in rows if r.benchmark == bench)
        if newest and newest < limit:
            alerts.append({"level": "warning", "source": bench,
                           "message": f"newest data dated {newest}, older than {STALE_DAYS} days"})

    # A benchmark that existed last week but is missing now is an alert too.
    prev = previous_csv(day)
    if prev:
        before = {r["benchmark"] for r in read_csv(prev)}
        for missing in sorted(before - {r.benchmark for r in rows}):
            alerts.append({"level": "error", "source": missing,
                           "message": f"0 rows this week (had rows on {prev.stem})"})

    if not rows:  # every source failed: keep any existing files for this date untouched
        print("No rows collected from any source; nothing written.")
        for a in alerts:
            print(f"  {a['source']}: {a['message']}")
        sys.exit(1)

    (DATA / "clean").mkdir(parents=True, exist_ok=True)
    out = DATA / "clean" / f"{day}.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(dataclasses.asdict(r))
    (DATA / "alerts").mkdir(parents=True, exist_ok=True)
    (DATA / "alerts" / f"{day}.json").write_text(json.dumps(alerts, indent=2), encoding="utf-8")
    print(f"Wrote {out} ({len(rows)} rows, {len(alerts)} alerts)")


# ---------------------------------------------------------------- helpers
def read_csv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("score", "margin_low", "margin_high", "cost"):
            r[k] = float(r[k]) if r[k] not in ("", None) else None
        r["rank"] = int(r["rank"]) if r["rank"] else None
        # Re-apply today's name rules so alias fixes also correct past weeks.
        r["model"] = canonicalize(r["model_raw"])[0]
    return rows


def previous_csv(day: str) -> Path | None:
    """The most recent earlier run (used for 'source missing since last run' alerts)."""
    files = sorted(p for p in (DATA / "clean").glob("*.csv") if p.stem < day)
    return files[-1] if files else None


COMPARE_DAYS = 7


def baseline_csv(day: str) -> Path | None:
    """The earlier run the 'Change' column compares with: the run closest to 7 days before `day`.

    Extra manual runs in between are skipped, so the comparison stays week-to-week. Ties go to the
    older run. If every earlier run is less than 7 days old, the oldest of them is the closest.
    """
    target = dt.date.fromisoformat(day) - dt.timedelta(days=COMPARE_DAYS)
    files = [p for p in (DATA / "clean").glob("*.csv") if p.stem < day]
    if not files:
        return None
    return min(files, key=lambda p: (abs((dt.date.fromisoformat(p.stem) - target).days), p.stem))


def fmt(x: float | None, unit: str) -> str:
    if x is None:
        return ""
    if unit == "%":
        return f"{x:.1f}%"
    if unit == "Elo":
        return f"{x:.0f}"
    return f"{x:.3f}"


def overlaps(a: dict, b: dict) -> bool | None:
    if None in (a["margin_low"], a["margin_high"], b["margin_low"], b["margin_high"]):
        return None
    return a["margin_low"] <= b["margin_high"] and b["margin_low"] <= a["margin_high"]


def md_escape(s: str) -> str:
    return s.replace("|", "\\|")


# ---------------------------------------------------------------- report
def report(day: str | None = None) -> Path:
    files = sorted((DATA / "clean").glob("*.csv"))
    if not files:
        sys.exit("No clean data yet. Run: python tracker.py collect")
    cur_file = DATA / "clean" / f"{day}.csv" if day else files[-1]
    day = cur_file.stem
    cur = read_csv(cur_file)
    prev_file = baseline_csv(day)
    prev = read_csv(prev_file) if prev_file else []
    prev_idx = {(r["benchmark"], r["model"], r["setup"]): r for r in prev}
    alerts_file = DATA / "alerts" / f"{day}.json"
    alerts = json.loads(alerts_file.read_text(encoding="utf-8")) if alerts_file.exists() else []

    L: list[str] = []
    L.append(f"# Frontier AI benchmark tracker: week of {day}\n")
    L.append(f"Collected {day}. "
             + (f"Changes compare with {prev_file.stem}." if prev_file else "First week: no changes to compare yet.")
             + " Every score below comes from the linked publisher page. Scores from different "
               "benchmarks are not comparable with each other.\n")
    # The summary and insights live in a separate file the AI writes, so re-running this never erases them.
    L.append(f"Summary and insights: [{day}-insights.md]({day}-insights.md) "
             "(written by AI from these tables).\n")

    # Show alerts for tables in the report and whole-collector failures; all alerts stay in data/alerts/.
    shown = {b for b, _ in REPORT} | set(COLLECTORS)
    alerts = [a for a in alerts if a["source"] in shown]
    if alerts:
        L.append("## Collection alerts\n")
        for a in alerts:
            L.append(f"- **{a['level']}**, {a['source']}: {a['message']}")
        L.append("")

    for bench, area in REPORT:
        rows = [r for r in cur if r["benchmark"] == bench]
        if not rows:
            L.append(f"## {area}: {bench}\n\n_No data this week (see alerts)._\n")
            continue
        rows.sort(key=lambda r: (r["rank"] if r["rank"] is not None else 10**6, -r["score"]))
        unit, url, trust = rows[0]["unit"], rows[0]["source_url"], rows[0]["trust"]
        version = rows[0]["version"]
        newest = max(r["source_date"] for r in rows)
        has_margin = any(r["margin_low"] is not None for r in rows)
        has_cost = any(r["cost"] is not None for r in rows)
        leader = rows[0]
        top_n = TOP_N_OVERRIDE.get(bench, TOP_N)
        L.append(f"## {area}: {bench}{' ' + version if version else ''}\n")
        L.append(f"Source: [{url}]({url}) · Trust: {trust} · Publisher data dated {newest} · "
                 f"{len(rows)} models listed, top {min(top_n, len(rows))} shown\n")
        if bench in CREDIT_LINE:
            L.append(f"_{CREDIT_LINE[bench]}_\n")
        if bench in SPREAD_NOTE:
            close = sum(1 for r in rows[1:] if overlaps(r, leader))
            L.append(f"_Top score {fmt(leader['score'], unit)}; {close} other model"
                     f"{'s are' if close != 1 else ' is'} too close to call with #1._\n")
        head = ["#", "Model", "Setup", "Score"]
        if has_margin:
            head.append("95% interval")
        if has_cost:
            head.append(f"Cost ({rows[0]['cost_basis'] or next(r['cost_basis'] for r in rows if r['cost_basis'])})")
        head += ["Change", "Vs. #1"]
        L.append("| " + " | ".join(head) + " |")
        L.append("|" + "---|" * len(head))
        for r in rows[:top_n]:
            p = prev_idx.get((bench, r["model"], r["setup"]))
            if not prev_file:
                change = ""
            elif p is None:
                change = "new"
            else:
                d = r["score"] - p["score"]
                change = "same" if abs(d) < 1e-9 else (f"{d:+.1f}" if unit != "score" else f"{d:+.3f}")
            if r is leader:
                call = "leader"
            else:
                o = overlaps(r, leader)
                call = "too close to call" if o else ("behind" if o is False else "no margin published")
            cells = [str(r["rank"] or ""), md_escape(r["model"]), md_escape(r["setup"]), fmt(r["score"], unit)]
            if has_margin:
                cells.append(f"{fmt(r['margin_low'], unit)} to {fmt(r['margin_high'], unit)}"
                             if r["margin_low"] is not None else "")
            if has_cost:
                cells.append(f"${r['cost']:.2f}" if r["cost"] is not None else "")
            cells += [change, call]
            L.append("| " + " | ".join(cells) + " |")
        notes = sorted({n.strip() for r in rows[:top_n] for n in r["note"].split(" | ")
                        if n.strip() and not n.startswith("API price")})
        for n in notes:
            star = "Rows marked * in the source: " if n.startswith("Run with") else ""
            L.append(f"\n_Note: {star}{n}_")
        L.append("")

    # Names that only one publisher uses: a hint that an alias may be missing.
    pubs: dict[str, set] = {}
    for r in cur:
        pubs.setdefault(r["model"], set()).add(r["source_url"].split("/")[2])
    lonely = sorted(m for m, s in pubs.items() if len(s) == 1)
    L.append("## Method\n")
    L.append("- **Trust labels.** *independent*: a third party ran the models. *crowd-preference*: "
             "ranking from public human votes. Vendor-reported scores are never mixed in.")
    L.append("- **Too close to call.** Shown when a model's published 95% interval overlaps the leader's. "
             "Where a publisher shows no interval, the table says *no margin published*.")
    L.append("- **GDPx score** is GDPx's own formula (equal weight per domain and per partner) applied to "
             "the data GDPx publishes; it matches the numbers on gdpx.semianalysis.com. Credit: GDPx by SemiAnalysis.")
    L.append("- **Arena** data comes from Arena's official dataset "
             "([lmarena-ai/leaderboard-dataset](https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset), CC-BY-4.0).")
    L.append(f"\n<details><summary>Model names seen at only one publisher ({len(lonely)})</summary>\n")
    L.append(", ".join(md_escape(m) for m in lonely) + "\n\n</details>\n")

    (ROOT / "reports").mkdir(exist_ok=True)
    out = ROOT / "reports" / f"{day}-report.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"Wrote {out}")
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    d = today()
    if cmd in ("collect", "all"):
        collect(d)
    if cmd in ("report", "all"):
        report()
