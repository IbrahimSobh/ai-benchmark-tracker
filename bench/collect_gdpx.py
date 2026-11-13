"""GDPx by SemiAnalysis. Method: plain HTML + the site's own script bundle.

The leaderboard is drawn in the browser from a JSON blob shipped inside a script file.
The page states the formula: "averages each model across all 11 domains, each weighted
equally, as is each partner within a domain". This collector applies exactly that
formula, rounds to one decimal like the page, and stops with an alert if any model
is missing a domain (the formula would then not match the page).

Terms: GDPx allows non-commercial quoting with the credit "GDPx by SemiAnalysis" and
forbids operating a derivative leaderboard. See README before publishing GDPx tables.
"""
from __future__ import annotations

import json
import re
import statistics as st

from .common import INDEPENDENT, CollectorAlert, Row, fetch, require_rows, save_raw
from .names import canonicalize

BASE = "https://gdpx.semianalysis.com"


def collect(day: str) -> list[Row]:
    home = fetch(BASE + "/")
    save_raw(day, "gdpx_home.html", home)
    scripts = sorted(set(re.findall(r'src="(/_next/static/[^"]+\.js)"', home)))
    data = partners = None
    for s in scripts:
        js = fetch(BASE + s)
        if data is None and '"updatedAt"' in js and "JSON.parse('" in js:
            for blob in re.findall(r"JSON\.parse\('(.*?)'\)", js, re.S):
                d = json.loads(blob.replace("\\'", "'"))
                if isinstance(d, dict) and {"models", "results"} <= d.keys():
                    data = d
                    save_raw(day, "gdpx_data.json", json.dumps(d, indent=1))
        if partners is None and 'a("aria"' in js:
            partners = dict(re.findall(r'a\("([a-z0-9-]+)","[^"]+","([a-z0-9-]+)"', js))
    if not data or not partners:
        raise CollectorAlert("GDPx: data blob or partner list not found in scripts")

    domains = set(partners.values())
    overall = data.get("overall", {})
    rows = []
    for m in data["models"]:
        by_domain: dict[str, list[float]] = {}
        for r in data["results"]:
            if r["modelId"] == m["id"]:
                if r["partnerId"] not in partners:
                    raise CollectorAlert(f"GDPx: unknown partner {r['partnerId']}")
                by_domain.setdefault(partners[r["partnerId"]], []).append(r["score"])
        if set(by_domain) != domains:
            raise CollectorAlert(f"GDPx: {m['name']} has {len(by_domain)}/{len(domains)} domains")
        score = st.mean(st.mean(v) for v in by_domain.values())
        model, _ = canonicalize(m["name"])
        cost = overall.get(m["id"], {}).get("costPerTask")
        rows.append(Row(
            benchmark="GDPx", version="v1.0", model=model, model_raw=m["name"],
            setup=f"{m.get('harness', '')}, {m.get('reasoning', '')}".strip(", "),
            score=round(score, 1), unit="%", margin_low=None, margin_high=None,
            cost=cost, cost_basis="USD per task" if cost is not None else "", rank=None,
            source_url=BASE + "/", trust=INDEPENDENT, source_date=data.get("updatedAt", ""),
            collected=day, note="GDPx by SemiAnalysis",
        ))
    return require_rows(rows, "GDPx")
