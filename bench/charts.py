"""SVG charts for the website, drawn straight from the saved data (data/clean/<date>.csv).

The AI never touches these numbers: every value comes from the same rows the tables show.

- rank_grid():     models x benchmarks, each cell = the model's rank (ranks, never scores, across benchmarks)
- margin_chart():  one benchmark: score dots with 95% interval lines and the leader's band
- small_multiples(): a grid of small margin charts, one per benchmark, grouped by trust label
"""
from __future__ import annotations

import html
import math

# Colours come from CSS variables defined in build_site.CSS, so charts follow light/dark mode.
ROW_H = 22
LABEL_W = 150
PLOT_W = 300
VALUE_W = 64


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
    start = math.floor(lo / step) * step
    ticks, t = [], start
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


def margin_chart(rows: list[dict], title: str = "", width: int | None = None) -> str:
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
    x0 = LABEL_W
    X = lambda v: x0 + (v - a) / ((z - a) or 1) * PLOT_W
    H = len(rows) * ROW_H + 30
    W = LABEL_W + PLOT_W + VALUE_W
    leader = rows[0]
    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" width="100%" role="img" '
           f'aria-label="{html.escape(title or "scores")}">']
    for t in ticks:  # light gridlines with rounded tick labels
        out.append(f'<line x1="{X(t):.1f}" y1="4" x2="{X(t):.1f}" y2="{len(rows) * ROW_H + 6}" class="grid"/>')
        out.append(f'<text x="{X(t):.1f}" y="{H - 6}" text-anchor="middle" class="tick">{tick_fmt(t, unit, step)}</text>')
    if has_m and leader["margin_low"] is not None:
        out.append(f'<rect x="{X(leader["margin_low"]):.1f}" y="4" '
                   f'width="{X(leader["margin_high"]) - X(leader["margin_low"]):.1f}" '
                   f'height="{len(rows) * ROW_H}" class="band"/>')
    for i, r in enumerate(rows):
        y = 16 + i * ROW_H
        st = status(r, leader)
        name = r["model"] + (f" ({r['setup']})" if r.get("_show_setup") else "")
        out.append(f'<text x="0" y="{y + 4}" class="lbl">{html.escape(name)}</text>')
        if has_m and r["margin_low"] is not None:
            out.append(f'<line x1="{X(r["margin_low"]):.1f}" y1="{y}" x2="{X(r["margin_high"]):.1f}" y2="{y}" class="ci {st}"/>')
        out.append(f'<circle cx="{X(r["score"]):.1f}" cy="{y}" r="4.5" class="dot {st}"/>')
        out.append(f'<text x="{W}" y="{y + 4}" text-anchor="end" class="val">{fmt(r["score"], unit)}</text>')
    out.append("</svg>")
    return "<div class='chartwrap'>" + "".join(out) + "</div>"


def legend(has_margin: bool = True) -> str:
    if not has_margin:
        return "<p class='chart-note'>No margin published: dots only, no tie can be judged.</p>"
    return ("<p class='chart-note'><span class='key lead'></span>leader "
            "<span class='key close'></span>too close to call "
            "<span class='key behind'></span>behind · shaded band = leader's 95% interval</p>")


def small_multiples(by_bench: dict[str, list[dict]], groups: list[tuple[str, list[str]]], n: int = 5) -> str:
    out = []
    for label, benches in groups:
        cells = []
        for b in benches:
            rows = by_bench.get(b, [])[:n]
            if not rows:
                continue
            has_m = rows[0]["margin_low"] is not None
            cells.append(f"<div class='mini'><p class='mini-t'>{html.escape(b)}</p>"
                         f"<p class='mini-s'>{'95% interval shown' if has_m else 'no margin published'}</p>"
                         f"{margin_chart(rows, b)}</div>")
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
    best: dict[str, dict[str, tuple[int, bool]]] = {}
    unranked = set()
    for b, _ in columns:
        rows = by_bench.get(b, [])
        if rows and rows[0]["rank"] is None:
            unranked.add(b)
        leader = rows[0] if rows else None
        for r in rows:
            rk, tie = rank_of(rows, r), status(r, leader) == "close"
            cur = best.setdefault(r["model"], {}).get(b)
            if cur is None or rk < cur[0]:  # same model with several setups: keep its best rank
                best[r["model"]][b] = (rk, tie)
    models = sorted(best, key=lambda m: (-len(best[m]), sum(v[0] for v in best[m].values()) / len(best[m])))
    # Choose by coverage (appears in most tables), then show the strongest average rank first.
    avg = lambda m: sum(v[0] for v in best[m].values()) / len(best[m])
    models = sorted(models[:n_models], key=avg)

    def cls(rk: int) -> str:
        return "r1" if rk == 1 else "r2" if rk == 2 else "r3" if rk == 3 else "r4" if rk <= 6 else "r5"

    head = "".join(
        f"<th class='{'crowd' if i == crowd_from else ''}'>{html.escape(lbl)}{'*' if b in unranked else ''}</th>"
        for i, (b, lbl) in enumerate(columns))
    body = []
    for m in models:
        cells = []
        for i, (b, _) in enumerate(columns):
            extra = " crowd" if i == crowd_from else ""
            if b in best[m]:
                rk, tie = best[m][b]
                cells.append(f"<td class='{cls(rk)}{extra}'>{rk}{' ≈' if tie else ''}</td>")
            else:
                cells.append(f"<td class='r0{extra}'>–</td>")
        body.append(f"<tr><th class='model'>{html.escape(m)}</th>{''.join(cells)}</tr>")
    note = ("Darker = higher rank · ≈ too close to call with #1 · – not in the rows the table shows · "
            "right of the dashed line: public votes")
    if unranked:
        note += " · * no rank published, ranked by score order"
    return (f"<div class='gridwrap'><table class='rankgrid'><tr><th></th>{head}</tr>{''.join(body)}</table></div>"
            f"<p class='chart-note'>{note}</p>")


CSS = """
:root{--lead:#185FA5;--close:#378ADD;--behind:#9a9890;--band:rgba(55,138,221,.13);--gridc:#e7e4dc;
--r1:#0C447C;--r1t:#E6F1FB;--r2:#185FA5;--r2t:#E6F1FB;--r3:#378ADD;--r3t:#042C53;--r4:#B5D4F4;--r4t:#0C447C;--r5:#E6F1FB;--r5t:#0C447C}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--lead:#85B7EB;--close:#378ADD;--behind:#7a7871;--band:rgba(133,183,235,.16);--gridc:#2c2c2a;
--r1:#B5D4F4;--r1t:#042C53;--r2:#85B7EB;--r2t:#042C53;--r3:#378ADD;--r3t:#042C53;--r4:#185FA5;--r4t:#E6F1FB;--r5:#0C447C;--r5t:#B5D4F4}}
:root[data-theme="dark"]{--lead:#85B7EB;--close:#378ADD;--behind:#7a7871;--band:rgba(133,183,235,.16);--gridc:#2c2c2a;
--r1:#B5D4F4;--r1t:#042C53;--r2:#85B7EB;--r2t:#042C53;--r3:#378ADD;--r3t:#042C53;--r4:#185FA5;--r4t:#E6F1FB;--r5:#0C447C;--r5t:#B5D4F4}
.chartwrap{overflow-x:auto}
svg.chart{display:block;margin:6px 0}
@media (max-width:560px){svg.chart{min-width:440px}}
svg.chart text{font:13px Inter,system-ui,sans-serif}
svg.chart .lbl{fill:var(--muted)} svg.chart .val{fill:var(--fg)} svg.chart .tick{fill:var(--muted);font-size:12px}
svg.chart .grid{stroke:var(--gridc);stroke-width:1} svg.chart .band{fill:var(--band)}
svg.chart .ci{stroke-width:2;stroke-linecap:round} svg.chart .ci.lead{stroke:var(--lead)} svg.chart .ci.close{stroke:var(--close)} svg.chart .ci.behind{stroke:var(--behind)}
svg.chart .dot.lead{fill:var(--lead)} svg.chart .dot.close{fill:var(--close)} svg.chart .dot.behind{fill:var(--behind)} svg.chart .dot.nomargin{fill:var(--muted)}
.chart-note{font-size:.8rem;color:var(--muted);margin:4px 0 12px}
.key{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px 0 8px;vertical-align:-1px}
.key.lead{background:var(--lead)} .key.close{background:var(--close)} .key.behind{background:var(--behind)}
.minis{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:12px}
.mini{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.mini-t{margin:0;font-weight:600;font-size:.92rem} .mini-s{margin:0;font-size:.75rem;color:var(--muted)}
.group{font-size:.85rem;color:var(--muted);margin:18px 0 6px}
.gridwrap{overflow-x:auto}
table.rankgrid{display:table;border-collapse:separate;border-spacing:3px;font-size:.85rem;margin:8px 0;min-width:560px}
table.rankgrid th,table.rankgrid td{border:0;padding:6px 8px;text-align:center;white-space:nowrap}
table.rankgrid tr:first-child th{background:none;font-weight:500;color:var(--muted);font-size:.78rem}
table.rankgrid th.model{background:none;text-align:left;font-weight:500}
table.rankgrid td{border-radius:4px;font-weight:600}
.r1{background:var(--r1);color:var(--r1t)} .r2{background:var(--r2);color:var(--r2t)} .r3{background:var(--r3);color:var(--r3t)}
.r4{background:var(--r4);color:var(--r4t)} .r5{background:var(--r5);color:var(--r5t)} .r0{background:var(--head);color:var(--muted);font-weight:400}
table.rankgrid .crowd{border-left:2px dashed var(--line)}
"""
