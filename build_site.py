"""Build the GitHub Pages site in docs/ from the Markdown files in reports/.

  python build_site.py

docs/index.html          latest summary and insights, plus the archive of every dated week
docs/<date>-report.html   tables for that date
docs/<date>-insights.html summary and insights for that date
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"
TITLE = "Frontier AI Benchmarks"

CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--muted:#6b6a65;--line:#e4e1d8;--card:#ffffff;--accent:#2f5d8a;--head:#f3f1ea}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#161615;--fg:#ecebe6;--muted:#a3a19a;--line:#33322f;--card:#1f1f1d;--accent:#8db6e0;--head:#262624}}
:root[data-theme="dark"]{--bg:#161615;--fg:#ecebe6;--muted:#a3a19a;--line:#33322f;--card:#1f1f1d;--accent:#8db6e0;--head:#262624}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:960px;margin:0 auto;padding:32px 16px 64px}
a{color:var(--accent)}
h1{font-size:1.9rem;line-height:1.25;margin:0 0 8px}
h2{font-size:1.25rem;margin:36px 0 10px;padding-top:12px;border-top:1px solid var(--line)}
.nav{font-size:.9rem;margin-bottom:24px}
.muted,.nav{color:var(--muted)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:4px 20px 16px;margin:16px 0}
table{display:block;overflow-x:auto;border-collapse:collapse;font-size:.88rem;margin:12px 0;max-width:100%}
th,td{border-bottom:1px solid var(--line);padding:6px 10px;text-align:left;white-space:nowrap}
th{background:var(--head);font-weight:600}
ul.weeks{list-style:none;padding:0}
ul.weeks li{padding:10px 0;border-bottom:1px solid var(--line)}
ul.weeks .date{font-weight:600;margin-right:12px}
footer{margin-top:48px;font-size:.85rem;color:var(--muted);border-top:1px solid var(--line);padding-top:16px}
details{margin:12px 0}
"""

FOOTER = (
    "<footer><p>Scores belong to their publishers: "
    '<a href="https://labs.scale.com/leaderboard">Scale Labs</a>, '
    '<a href="https://artificialanalysis.ai">Artificial Analysis</a>, '
    '<a href="https://gdpx.semianalysis.com/">GDPx by SemiAnalysis</a> (top 3 quoted) and '
    '<a href="https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset">Arena</a> (CC-BY-4.0). '
    "Every table links to its source; check the source for the full and current leaderboard.</p>"
    "<p>Summaries and insights are written by AI (Claude) from the tables and published automatically.</p>"
    "</footer>"
)


def page(title: str, body: str, nav: str = "") -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body><main>"
        f"{nav}{body}{FOOTER}</main></body></html>"
    )


def md_to_html(text: str) -> str:
    out = markdown.markdown(text, extensions=["tables"])
    # Links between reports point to .md files; the site serves .html.
    out = re.sub(r'href="(\d{4}-\d{2}-\d{2}-(?:report|insights))\.md"', r'href="\1.html"', out)
    out = re.sub(r">(\d{4}-\d{2}-\d{2})-report\.md<", r">tables for \1<", out)
    return re.sub(r">(\d{4}-\d{2}-\d{2})-insights\.md<", r">summary and insights for \1<", out)


def strip_h1(text: str) -> str:
    """Drop the title and the 'Written from ...' line (the home page shows its own heading and link)."""
    text = re.sub(r"^# .*\n", "", text, count=1)
    return re.sub(r"^\s*Written from .*\n", "", text, count=1)


def build() -> None:
    DOCS.mkdir(exist_ok=True)
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")  # serve files as-is
    dates = sorted({m.group(1) for p in REPORTS.glob("*.md")
                    if (m := re.match(r"(\d{4}-\d{2}-\d{2})-(report|insights)\.md$", p.name))},
                   reverse=True)
    home = '<nav class="nav"><a href="index.html">All weeks</a></nav>'
    for d in dates:
        for kind in ("report", "insights"):
            src = REPORTS / f"{d}-{kind}.md"
            if src.exists():
                text = src.read_text(encoding="utf-8")
                h1 = re.match(r"# (.*)", text)
                (DOCS / f"{d}-{kind}.html").write_text(
                    page(h1.group(1) if h1 else f"{TITLE} {d}", md_to_html(text), home), encoding="utf-8")

    body = [f"<h1>{TITLE}</h1>",
            "<p class='muted'>A weekly view of how frontier AI models compare on coding, agentic and work "
            "benchmarks. Every number links to its publisher.</p>"]
    if dates:
        latest = dates[0]
        ins = REPORTS / f"{latest}-insights.md"
        body.append(f"<h2>Latest: week of {latest}</h2>")
        if ins.exists():
            body.append("<div class='card'>" + md_to_html(strip_h1(ins.read_text(encoding="utf-8"))) + "</div>")
        else:
            body.append("<p class='muted'>Insights for this week are not written yet.</p>")
        body.append(f"<p><a href='{latest}-report.html'>See all tables for {latest}</a></p>")
    body.append("<h2>All weeks</h2><ul class='weeks'>")
    for d in dates:
        links = [f"<a href='{d}-insights.html'>Summary and insights</a>"] if (REPORTS / f"{d}-insights.md").exists() else []
        if (REPORTS / f"{d}-report.md").exists():
            links.append(f"<a href='{d}-report.html'>Tables</a>")
        body.append(f"<li><span class='date'>{d}</span>{' · '.join(links)}</li>")
    body.append("</ul>")
    (DOCS / "index.html").write_text(page(TITLE, "".join(body)), encoding="utf-8")
    print(f"Built {DOCS} ({len(dates)} weeks)")


if __name__ == "__main__":
    build()
