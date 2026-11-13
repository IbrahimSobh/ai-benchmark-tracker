"""SVG / HTML charts for the website, drawn straight from the saved data (data/clean/<date>.csv).

The AI never touches these numbers: every value comes from the same rows the tables show.
Styling follows the Coding Agents Digest ("editorial paper"): each model wears its lab's colour,
cards are soft and rounded, and hover tooltips are cards with a border in the lab's colour.

- rank_grid():       models x benchmarks, each cell = the model's rank (ranks, never scores, across benchmarks)
- margin_chart():    one benchmark: score dots with 95% interval lines and the leader's band
- small_multiples(): a grid of small margin charts, one per benchmark, grouped by trust label

Tooltips: every hover target carries data-tip (lines separated by newlines) and data-tc (border colour).
SVG targets also carry a <title> so the facts still show as a plain browser tooltip without JavaScript.
"""
from __future__ import annotations

import html
import re
import math

from .labs import color_of, lab_of, logo_html

ROW_H = 24
LABEL_W = 160
PLOT_W = 300
VALUE_W = 64

PUBLISHERS = {"labs.scale.com": "Scale Labs", "artificialanalysis.ai": "Artificial Analysis",
              "gdpx.semianalysis.com": "GDPx by SemiAnalysis", "arena.ai": "Arena"}


def publisher(url: str) -> str:
    host = url.split("/")[2] if "//" in url else url
    return PUBLISHERS.get(host, host)


def fmt(v: float, unit: str) -> str:
    if unit == "%":
        return f"{v:.1f}%"
    if unit == "Elo":
        return f"{v:.0f}"
    return f"{v:.3f}"


def tick_fmt(v: float, unit: str, step: float) -> str:
    whole = abs(step - round(step)) < 1e-9 and step >= 1
    if unit == "%":
        return f"{v:.0f}%" if whole else f"{v:.1f}%"
    if unit == "Elo":
        return f"{v:.0f}"
    return f"{v:.2f}".rstrip("0").rstrip(".") if step >= 0.01 else f"{v:.3f}"


def nice_ticks(lo: float, hi: float, target: int = 4) -> list[float]:
    span = hi - lo or abs(hi) or 1
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=10 * mag)
    ticks, t = [], math.floor(lo / step) * step
    while t <= hi + step * 0.001:
        ticks.append(round(t, 10))
        t += step
    if ticks[-1] < hi:
        ticks.append(round(ticks[-1] + step, 10))
    return ticks


def status(row: dict, leader: dict) -> str:
    if row is leader:
        return "lead"
    if None in (row["margin_low"], row["margin_high"], leader["margin_low"], leader["margin_high"]):
        return "nomargin"
    overlap = row["margin_low"] <= leader["margin_high"] and leader["margin_low"] <= row["margin_high"]
    return "close" if overlap else "behind"


STATUS_TEXT = {"lead": "Leader", "close": "Too close to call with #1", "behind": "Behind #1",
               "nomargin": "No margin published"}


def tip_text(r: dict, bench: str, st: str, rank: int | None = None) -> str:
    lines = [f"{r['model']} · {bench}"]
    if r.get("setup"):
        lines.append(f"Setup: {r['setup']}")
    lines.append((f"Rank {rank} · " if rank else "") + f"Score {fmt(r['score'], r['unit'])}")
    if r["margin_low"] is not None:
        lines.append(f"95% interval {fmt(r['margin_low'], r['unit'])} to {fmt(r['margin_high'], r['unit'])}")
    lines.append(STATUS_TEXT[st])
    lines.append(f"{lab_of(r['model'])} · source: {publisher(r['source_url'])}")
    return "\n".join(lines)


def bench_id(bench: str) -> str:
    """Anchor id of a benchmark's chart card, so rank-grid tiles can link to it."""
    return "b-" + re.sub(r"[^a-z0-9]+", "-", bench.lower()).strip("-")


def tip_attrs(text: str, color: str) -> str:
    return f'data-tip="{html.escape(text)}" data-tc="{color}" tabindex="0"'


def margin_chart(rows: list[dict], title: str = "") -> str:
    """Dots for scores, lines for 95% intervals, shaded band for the leader's interval."""
    if not rows:
        return ""
    unit = rows[0]["unit"]
    has_m = rows[0]["margin_low"] is not None
    lows = [r["margin_low"] if has_m and r["margin_low"] is not None else r["score"] for r in rows]
    highs = [r["margin_high"] if has_m and r["margin_high"] is not None else r["score"] for r in rows]
    ticks = nice_ticks(min(lows), max(highs))
    a, z = ticks[0], ticks[-1]
    step = ticks[1] - ticks[0] if len(ticks) > 1 else 1
    X = lambda v: LABEL_W + (v - a) / ((z - a) or 1) * PLOT_W
    H = len(rows) * ROW_H + 30
    W = LABEL_W + PLOT_W + VALUE_W
    leader = rows[0]
    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" width="100%" role="img" '
           f'aria-label="{html.escape(title or "scores")}">']
    for t in ticks:
        out.append(f'<line x1="{X(t):.1f}" y1="4" x2="{X(t):.1f}" y2="{len(rows) * ROW_H + 6}" class="grid"/>')
        out.append(f'<text x="{X(t):.1f}" y="{H - 6}" text-anchor="middle" class="tick">{tick_fmt(t, unit, step)}</text>')
    if has_m and leader["margin_low"] is not None:
        out.append(f'<rect x="{X(leader["margin_low"]):.1f}" y="4" rx="6" '
                   f'width="{X(leader["margin_high"]) - X(leader["margin_low"]):.1f}" '
                   f'height="{len(rows) * ROW_H}" class="band"/>')
    for i, r in enumerate(rows):
        y = 16 + i * ROW_H
        st = status(r, leader)
        col = color_of(r["model"])
        name = r["model"] + (f" ({r['setup']})" if r.get("_show_setup") else "")
        tip = tip_text(r, title, st, r["rank"])
        out.append(f'<g class="row {st}" data-model="{html.escape(r["model"])}" {tip_attrs(tip, col)}><title>{html.escape(tip)}</title>'
                   f'<rect x="0" y="{y - ROW_H / 2:.1f}" width="{W}" height="{ROW_H}" class="hit"/>'
                   f'<circle cx="7" cy="{y}" r="5" fill="{col}"/>'
                   f'<text x="18" y="{y + 4}" class="lbl">{html.escape(name)}</text>')
        if has_m and r["margin_low"] is not None:
            out.append(f'<line x1="{X(r["margin_low"]):.1f}" y1="{y}" x2="{X(r["margin_high"]):.1f}" y2="{y}" '
                       f'stroke="{col}" class="ci"/>')
        out.append(f'<circle cx="{X(r["score"]):.1f}" cy="{y}" r="6" fill="{col}" class="dot"/>'
                   f'<text x="{W}" y="{y + 4}" text-anchor="end" class="val">{fmt(r["score"], unit)}</text></g>')
    out.append("</svg>")
    return "<div class='chartwrap'>" + "".join(out) + "</div>"


def scale_for(rows: list[dict]) -> tuple[float, float, list[float], float]:
    """Shared axis for one benchmark: (min, max, ticks, step) covering every score and interval."""
    has_m = rows[0]["margin_low"] is not None
    lows = [r["margin_low"] if has_m and r["margin_low"] is not None else r["score"] for r in rows]
    highs = [r["margin_high"] if has_m and r["margin_high"] is not None else r["score"] for r in rows]
    ticks = nice_ticks(min(lows), max(highs))
    return ticks[0], ticks[-1], ticks, (ticks[1] - ticks[0] if len(ticks) > 1 else 1)


CELL_W, CELL_H = 240, 28


def axis_svg(rows: list[dict]) -> str:
    """Tick labels for the chart column's header, on the same scale as every row's cell."""
    a, z, ticks, step = scale_for(rows)
    X = lambda v: 8 + (v - a) / ((z - a) or 1) * (CELL_W - 16)
    t = "".join(f'<text x="{X(v):.1f}" y="13" text-anchor="middle" class="tick">{tick_fmt(v, rows[0]["unit"], step)}</text>'
                for v in ticks)
    return f'<svg class="chart axis" viewBox="0 0 {CELL_W} 18" width="{CELL_W}" height="18" aria-hidden="true">{t}</svg>'


def cell_svg(rows: list[dict], r: dict, bench: str) -> str:
    """One row's chart cell: gridlines, the leader's band, this row's interval line and score dot."""
    a, z, ticks, _ = scale_for(rows)
    leader = rows[0]
    X = lambda v: 8 + (v - a) / ((z - a) or 1) * (CELL_W - 16)
    st = status(r, leader)
    col = color_of(r["model"])
    y = CELL_H / 2
    s = [f'<svg class="chart cell" viewBox="0 0 {CELL_W} {CELL_H}" width="{CELL_W}" height="{CELL_H}" aria-hidden="true">']
    s += [f'<line x1="{X(v):.1f}" y1="0" x2="{X(v):.1f}" y2="{CELL_H}" class="grid"/>' for v in ticks]
    if leader["margin_low"] is not None:
        s.append(f'<rect x="{X(leader["margin_low"]):.1f}" y="0" width="{X(leader["margin_high"]) - X(leader["margin_low"]):.1f}" '
                 f'height="{CELL_H}" class="band"/>')
    s.append(f'<g class="row {st}">')
    if r["margin_low"] is not None:
        s.append(f'<line x1="{X(r["margin_low"]):.1f}" y1="{y}" x2="{X(r["margin_high"]):.1f}" y2="{y}" stroke="{col}" class="ci"/>')
    s.append(f'<circle cx="{X(r["score"]):.1f}" cy="{y}" r="6" fill="{col}" class="dot"/></g></svg>')
    return "".join(s)


def legend(has_margin: bool = True) -> str:
    if not has_margin:
        return "<p class='chart-note'>No margin published: dots only, so no tie can be judged.</p>"
    return ("<p class='chart-note'>Each colour is the model's lab · full colour = leader or too close to "
            "call · faded = behind · shaded band = the leader's 95% interval · hover for details</p>")


def small_multiples(by_bench: dict[str, list[dict]], groups: list[tuple[str, list[str]]], n: int = 5) -> str:
    """Each card shows the top n models; 'Show all' (no JavaScript needed) opens every row the table shows."""
    out = []
    for label, benches in groups:
        cells = []
        for b in benches:
            all_rows = by_bench.get(b, [])
            rows = all_rows[:n]
            if not rows:
                continue
            has_m = rows[0]["margin_low"] is not None
            src = rows[0]["source_url"]
            more = ""
            if len(all_rows) > n:
                more = (f"<details class='more'><summary>Show all {len(all_rows)}</summary>"
                        f"<div class='all'>{margin_chart(all_rows, b)}</div></details>")
            cells.append(f"<div class='mini' id='{bench_id(b)}'><p class='mini-t'>{html.escape(b)}</p>"
                         f"<p class='mini-s'>{'95% interval shown' if has_m else 'no margin published'} · "
                         f"<a class='ext' href='{html.escape(src)}'>{html.escape(publisher(src))}</a></p>"
                         f"<div class='top'>{margin_chart(rows, b)}</div>{more}</div>")
        if cells:
            out.append(f"<p class='group'>{html.escape(label)}</p><div class='minis'>{''.join(cells)}</div>")
    out.append(legend(True))
    return "".join(out)


def rank_of(rows: list[dict], r: dict) -> int:
    """Publisher's rank if published; otherwise 1 + number of strictly higher scores (ties share a rank)."""
    if r["rank"] is not None:
        return r["rank"]
    return 1 + sum(1 for x in rows if x["score"] > r["score"])


def rank_grid(by_bench: dict[str, list[dict]], columns: list[tuple[str, str]], crowd_from: int,
              n_models: int = 6) -> str:
    """columns: (benchmark, short label). Columns from index crowd_from on are public-vote benchmarks."""
    best: dict[str, dict[str, tuple[int, str, dict]]] = {}
    unranked = set()
    for b, _ in columns:
        rows = by_bench.get(b, [])
        if rows and rows[0]["rank"] is None:
            unranked.add(b)
        leader = rows[0] if rows else None
        for r in rows:
            rk = rank_of(rows, r)
            cur = best.setdefault(r["model"], {}).get(b)
            if cur is None or rk < cur[0]:  # same model with several setups: keep its best rank
                best[r["model"]][b] = (rk, status(r, leader), r)
    models = sorted(best, key=lambda m: (-len(best[m]), sum(v[0] for v in best[m].values()) / len(best[m])))
    avg = lambda m: sum(v[0] for v in best[m].values()) / len(best[m])
    models = sorted(models[:n_models], key=avg)  # choose by coverage, show strongest average rank first

    def strength(rk: int) -> int:
        return 100 if rk == 1 else 78 if rk == 2 else 60 if rk == 3 else 40 if rk <= 6 else 22

    head = "".join(
        f"<th class='{'crowd' if i == crowd_from else ''}'>{html.escape(lbl)}{'*' if b in unranked else ''}</th>"
        for i, (b, lbl) in enumerate(columns))
    body = []
    for m in models:
        col = color_of(m)
        cells = []
        for i, (b, _) in enumerate(columns):
            extra = " crowd" if i == crowd_from else ""
            if b in best[m]:
                rk, st, r = best[m][b]
                s = strength(rk)
                ink = "#17101c" if s >= 60 else "var(--ink)"
                tip = tip_text(r, b, st, rk)
                cells.append(f"<td class='rk{extra}' style='background:color-mix(in srgb,{col} {s}%,var(--tile));"
                             f"color:{ink}' title=\"{html.escape(tip)}\" data-tc='{col}'>"
                             f"<a class='go' href='#{bench_id(b)}' data-model=\"{html.escape(m)}\" "
                             f"aria-label=\"{html.escape(m)}, rank {rk} on {html.escape(b)}: open its chart\">"
                             f"{rk}{' ≈' if st == 'close' else ''}</a></td>")
            else:
                cells.append(f"<td class='r0{extra}' title='{html.escape(m)}: not in the rows this table shows'>–</td>")
        body.append(f"<tr><th class='model'>{logo_html(lab_of(m), 20, m)}<span>{html.escape(m)}</span></th>"
                    f"{''.join(cells)}</tr>")
    note = ("Stronger tile = higher rank, in the lab's colour · ≈ too close to call with #1 · – not in the rows "
            "the table shows · right of the dashed line: public votes · hover a tile for details, click it to "
            "open that benchmark's chart")
    if unranked:
        note += " · * no rank published, ranked by score order"
    return (f"<p class='swipe'>Swipe sideways to see all {len(columns)} benchmarks →</p>"
            f"<div class='card gridcard'><div class='gridwrap'><table class='rankgrid'><tr><th></th>{head}</tr>"
            f"{''.join(body)}</table></div></div><p class='chart-note'>{note}</p>")


def labs_strip(by_bench: dict[str, list[dict]], n: int = 6) -> str:
    """'Tracking' strip under the headline: the labs that appear most often in the latest update's tables."""
    count: dict[str, int] = {}
    for rows in by_bench.values():
        for r in rows:
            lab = lab_of(r["model"])
            if lab != "Other":
                count[lab] = count.get(lab, 0) + 1
    labs = sorted(count, key=lambda l: -count[l])[:n]
    items = "".join(f"<span class='trk'>{logo_html(l, 28)}{html.escape(l)}</span>" for l in labs)
    return f"<div class='track'><span class='tk'>Most seen in the latest update</span>{items}</div>"


CSS = """
.chartwrap{overflow-x:auto}
svg.chart{display:block;margin:8px 0;overflow:visible}
@media (max-width:560px){svg.chart{min-width:440px}}
svg.chart text{font:13px "Schibsted Grotesk",system-ui,sans-serif}
svg.chart .lbl{fill:var(--muted)} svg.chart .val{fill:var(--ink);font-weight:500} svg.chart .tick{fill:var(--soft);font-size:12px}
svg.chart .grid{stroke:var(--line);stroke-width:1} svg.chart .band{fill:var(--accent);opacity:.14}
svg.chart .ci{stroke-width:3;stroke-linecap:round} svg.chart .dot{stroke:var(--card2);stroke-width:2}
svg.chart .row.behind .ci,svg.chart .row.behind .dot{opacity:.33}
svg.chart .hit{fill:transparent} svg.chart .row{cursor:default;outline:none}
svg.chart .row:hover .hit,svg.chart .row:focus .hit{fill:color-mix(in srgb,var(--ink) 5%,transparent)}
.chart-note{font-size:13px;color:var(--soft);margin:10px 0 0}
.minis{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,400px),1fr));gap:16px}
.mini{background:var(--card2);border-radius:20px;padding:16px 20px}
.mini-t{margin:0;font-family:var(--serif);font-size:20px;color:var(--ink)} .mini-s{margin:2px 0 0;font-size:13px;color:var(--soft)}
.mini-s a{color:var(--muted)}
.group{font-size:14px;color:var(--muted);margin:26px 0 10px}
.mini{display:flex;flex-direction:column}
.mini:has(details[open]) .top{display:none}
details.more{order:3;margin:6px 0 0}
details.more summary{list-style:none;cursor:pointer;display:inline-flex;align-self:flex-start;width:max-content;font-size:13px;padding:5px 13px;border-radius:9999px;border:1px solid var(--line);color:var(--muted)}
details.more summary::-webkit-details-marker{display:none}
details.more summary:hover{border-color:var(--ink);color:var(--ink)}
details.more[open] summary{font-size:0;padding:5px 13px} details.more[open] summary::after{content:"Show top 5";font-size:13px}
details.more .all{margin-top:4px}
.mini .top,.mini .all{order:2} details.more[open]{display:flex;flex-direction:column-reverse}
/* tables page: one card per benchmark, chart column inside the table */
.bcard{background:var(--card2);border-radius:20px;padding:22px 24px;margin:20px 0}
.bcard .area{font-size:13px;color:var(--soft);margin:0}
.bcard h2{margin:2px 0 10px;font-size:28px}
.metas{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 12px}
.metas .pill{font-size:13px;padding:4px 12px}
.bcard .note{font-size:13px;color:var(--soft);margin:8px 0 0}
table.combo{display:table;width:100%;background:none;padding:0;border-radius:0;margin:6px 0 0}
.combo-wrap{overflow-x:auto}
table.combo th,table.combo td{padding:6px 10px;vertical-align:middle}
table.combo td.cc,table.combo th.cc{padding:0 6px;width:252px}
table.combo td.num{font-variant-numeric:tabular-nums}
table.combo tr.r:hover td{background:color-mix(in srgb,var(--ink) 4%,transparent)}
svg.chart.cell,svg.chart.axis{display:block;margin:0}
.vs{font-size:12.5px;color:var(--muted)} .vs.lead{color:var(--ink);font-weight:500}
.vs.close::before{content:"≈ "}
.gridcard{padding:16px 18px}
.gridwrap{overflow-x:auto}
table.rankgrid{border-collapse:separate;border-spacing:4px;font-size:14px;min-width:720px;width:100%;margin:0;background:none;table-layout:fixed;display:table;padding:0;border-radius:0}
table.rankgrid tr:first-child th:first-child{width:190px}
@media (max-width:560px){table.rankgrid{min-width:600px;font-size:13px} table.rankgrid tr:first-child th:first-child{width:150px}}
table.rankgrid th,table.rankgrid td{border:0;padding:0;text-align:center;white-space:nowrap;background:none}
table.rankgrid tr:first-child th{font-weight:400;color:var(--soft);font-size:12.5px;padding:0 2px 4px;line-height:1.2;white-space:normal}
table.rankgrid th.model{text-align:left;font-weight:500;color:var(--ink);padding-right:10px}
table.rankgrid th.model>*{vertical-align:middle} table.rankgrid th.model .tlogo,table.rankgrid th.model .lbadge{margin-right:8px}
table.rankgrid td{height:32px;border-radius:9px;font-weight:700;font-size:13px;background:var(--tile)}
table.rankgrid td.r0{color:var(--soft);font-weight:400}
table.rankgrid td.rk{padding:0} table.rankgrid td.rk:hover,table.rankgrid td.rk:focus-within{outline:2px solid var(--ink);outline-offset:1px}
table.rankgrid a.go{display:flex;align-items:center;justify-content:center;height:100%;min-height:32px;color:inherit;text-decoration:none;border-radius:9px;outline:none}
table.rankgrid th.model{position:sticky;left:0;z-index:1;background:var(--card2)}
table.rankgrid tr:first-child th:first-child{position:sticky;left:0;z-index:1;background:var(--card2)}
.swipe{display:none;font-size:13px;color:var(--soft);margin:0 0 6px}
@media (max-width:760px){.swipe{display:block}}
.mini{scroll-margin-top:120px}
svg.chart .row.flash .hit{animation:flash 2.4s ease-out}
@keyframes flash{0%,40%{fill:color-mix(in srgb,var(--accent) 30%,transparent)}100%{fill:transparent}}
@media (prefers-reduced-motion:reduce){svg.chart .row.flash .hit{animation:none;fill:color-mix(in srgb,var(--accent) 22%,transparent)}}
table.rankgrid .crowd{position:relative}
table.rankgrid .crowd::before{content:"";position:absolute;left:-5px;top:-2px;bottom:-2px;border-left:2px dashed var(--line)}
"""
