"""Artificial Analysis evaluation pages. Method: plain HTML; the page embeds `initialModels` JSON.

Artificial Analysis also offers an official API (free key). If the page layout changes,
switching to that API is the next method to try.
"""
from __future__ import annotations

import re

from .common import INDEPENDENT, Row, fetch, json_after, next_flight, require_rows, save_raw
from .names import canonicalize

PAGES = [
    # slug, benchmark name, field, unit, interval field (or None)
    ("terminalbench-4-0", "Terminal-Bench 4.0", "terminalBench40", "%", None),
    ("gdpval-aa", "GDPval-AA", "gdpval", "Elo", "gdpvalBreakdown"),
]


def collect(day: str) -> list[Row]:
    rows: list[Row] = []
    for slug, bench, field, unit, ci_field in PAGES:
        url = f"https://artificialanalysis.ai/evaluations/{slug}"
        html = fetch(url)
        save_raw(day, f"aa_{slug}.html", html)
        title = re.search(r"<title>([^<|]+)", html)
        version = ""
        if title:
            v = re.search(r"\bv(\d+(?:\.\d+)*)\b", title.group(1))
            version = f"v{v.group(1)}" if v else ""
        models = json_after(next_flight(html), '"initialModels":')
        newest = max((m.get("releaseDate") or "") for m in models)
        page_rows = []
        for m in models:
            val = m.get(field)
            if val is None:
                continue
            model, setup = canonicalize(m["name"])
            low = high = None
            if ci_field and isinstance(m.get(ci_field), dict):
                low = m[ci_field].get("lower95ci")
                high = m[ci_field].get("upper95ci")
            score = val * 100 if unit == "%" else val
            pin, pout = m.get("price1mInputTokens"), m.get("price1mOutputTokens")
            page_rows.append(Row(
                benchmark=bench, version=version, model=model, model_raw=m["name"],
                setup=setup, score=round(score, 2), unit=unit, margin_low=low, margin_high=high,
                cost=None, cost_basis="", rank=None, source_url=url, trust=INDEPENDENT,
                source_date=newest, collected=day,
                note=(f"API price ${pin}/${pout} per 1M input/output tokens" if pin is not None else ""),
            ))
        # Artificial Analysis publishes no rank number, so rank stays empty (ties exist).
        rows += require_rows(page_rows, f"Artificial Analysis {slug}")
    return rows
