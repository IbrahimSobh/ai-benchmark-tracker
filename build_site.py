"""Build the GitHub Pages site in docs/ from the Markdown files in reports/ and the data in data/clean/.

  python build_site.py

docs/index.html           headline, rank grid, margin charts, latest summary and insights, archive
docs/<date>-report.html   tables for that date, each with its chart
docs/<date>-insights.html charts plus the summary and insights for that date

Design: the "editorial paper" look of Coding Agents Digest (IbrahimSobh/coding-agents-digest):
plum-black dark theme by default, white light theme from the system setting or the toggle,
Newsreader serif headings with one italic word, Schibsted Grotesk text (fonts self-hosted, SIL OFL),
pill buttons, soft rounded cards, card tooltips. Lab colours and logos come from bench/labs.py.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import markdown

from bench import charts
from bench.labs import lab_of, logo_html
from tracker import DATA, REPORT, TOP_N, TOP_N_OVERRIDE, read_csv

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"
TITLE = "Frontier AI Benchmarks"
REPO = "https://github.com/IbrahimSobh/ai-benchmark-tracker"
LINKEDIN = "https://www.linkedin.com/in/ibrahim-sobh-phd-8681757/"
AUTHOR = "Ibrahim Sobh"
TAGLINE = "Which AI models lead coding, agent and work tests, with a source for every number"
# One schedule rule, used in the header, footer and README: checked daily, published only when data changes.
SCHEDULE = "checked daily at 9:00 Cairo time"
SCHEDULE_LONG = ("Checked every day at 9:00 Cairo time by a Claude scheduled task. A new update is published only "
                 "when a publisher's data has changed, so the date of the latest update can be a few days old.")

# Brand mark: the digest's rounded line style, with three podium bars in the lab colours.
# The bars rise and settle in a slow loop (stopped for readers who prefer reduced motion).
LOGO = ("<svg class='logo' viewBox='0 0 128 128' aria-hidden='true'>"
        "<rect x='14' y='14' width='100' height='100' rx='28' class='lg-glass'/>"
        "<rect class='lg-bar b1' x='33' y='60' width='18' height='38' rx='4' fill='#5b8def'/>"
        "<rect class='lg-bar b2' x='55' y='36' width='18' height='62' rx='4' fill='#e07a5f'/>"
        "<rect class='lg-bar b3' x='77' y='50' width='18' height='48' rx='4' fill='#2fb38a'/>"
        "<rect x='14' y='14' width='100' height='100' rx='28' class='lg-frame'/></svg>")
FAVICON = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 128 128'><style>@media (prefers-color-scheme: dark)"
           "{.ink{stroke:#f4eef2}.paper{fill:#17101c}}</style>"
           "<rect class='paper' x='14' y='14' width='100' height='100' rx='28' fill='#fff'/>"
           "<rect x='33' y='60' width='18' height='38' rx='4' fill='#5b8def'/>"
           "<rect x='55' y='36' width='18' height='62' rx='4' fill='#e07a5f'/>"
           "<rect x='77' y='50' width='18' height='48' rx='4' fill='#2fb38a'/>"
           "<rect class='ink' x='14' y='14' width='100' height='100' rx='28' fill='none' stroke='#17191c' "
           "stroke-width='9'/></svg>")

ICON_GH = ("<svg viewBox='0 0 16 16' width='17' height='17' fill='currentColor' aria-hidden='true'><path d='M8 0c4.42 0 8 "
           "3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 "
           "1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27"
           "-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06"
           " 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01"
           ".53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 "
           "8c0-4.42 3.58-8 8-8Z'/></svg>")
ICON_IN = ("<svg viewBox='0 0 16 16' width='16' height='16' fill='currentColor' aria-hidden='true'><path d='M0 1.15C0 .52"
           ".52 0 1.17 0h13.66C15.48 0 16 .52 16 1.15v13.7c0 .63-.52 1.15-1.17 1.15H1.17C.52 16 0 15.48 0 14.85zm4.83 "
           "12.24V6.17H2.43v7.22zM3.63 5.18c.84 0 1.36-.55 1.36-1.25-.02-.71-.52-1.25-1.34-1.25S2.3 3.22 2.3 3.93c0 .7.52"
           " 1.25 1.32 1.25zm4.9 8.21V9.36c0-.22.02-.43.08-.59.17-.43.57-.88 1.23-.88.87 0 1.22.66 1.22 1.63v3.87h2.4V9.25"
           "c0-2.22-1.18-3.25-2.76-3.25-1.27 0-1.84.7-2.16 1.19v.02h-.02l.02-.02V6.17H6.13c.03.68 0 7.22 0 7.22z'/></svg>")
ICON_THEME = ("<svg viewBox='0 0 16 16' width='16' height='16' aria-hidden='true'><circle cx='8' cy='8' r='6.5' "
              "fill='none' stroke='currentColor' stroke-width='1.5'/><path d='M8 1.5a6.5 6.5 0 0 1 0 13z' "
              "fill='currentColor'/></svg>")

CSS = """
:root,:root[data-theme="dark"]{
  --bg:#17101c; --card:#261b2e; --card2:#211728; --line:#3a2c45; --ink:#f4eef2; --muted:#b9abc2; --soft:#a597b0;
  --accent:#f3b999; --tile:#2e2238;
  --serif:Newsreader,Georgia,"Times New Roman",serif; color-scheme:dark}
:root[data-theme="light"]{
  --bg:#ffffff; --card:#ffffff; --card2:#f2f2f3; --line:#e6e6e8; --ink:#17191c; --muted:#61656f; --soft:#6b6f79;
  --accent:#5d2a1a; --tile:#e6e6e9; color-scheme:light}
@font-face{font-family:"Schibsted Grotesk";font-style:normal;font-weight:400 900;font-display:swap;src:url("assets/fonts/schibsted-grotesk-latin-wght-normal.woff2") format("woff2")}
@font-face{font-family:Newsreader;font-style:normal;font-weight:200 800;font-display:swap;src:url("assets/fonts/newsreader-latin-wght-normal.woff2") format("woff2")}
@font-face{font-family:Newsreader;font-style:italic;font-weight:200 800;font-display:swap;src:url("assets/fonts/newsreader-latin-wght-italic.woff2") format("woff2")}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 "Schibsted Grotesk",system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--ink);text-underline-offset:3px;text-decoration-color:color-mix(in srgb,var(--accent) 70%,transparent)}
a:hover{text-decoration-color:currentColor}
a.ext::after{content:"\\2197";font-size:.78em;margin-left:2px;opacity:.8}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:6px}
::selection{background:color-mix(in srgb,var(--accent) 32%,transparent)}
.wrap{max-width:1100px;margin:0 auto;padding:0 28px}
h1,h2,h3,.lede,.brand{font-family:var(--serif);font-weight:400;text-wrap:balance}
h1 em,h2 em,.lede em,.brand em{font-style:italic}
h1{font-size:44px;line-height:1.12;letter-spacing:-.8px;margin:36px 0 10px}
h2{font-size:30px;line-height:1.2;letter-spacing:-.4px;margin:64px 0 14px}
h3{font-size:22px;margin:28px 0 8px}
p,li{text-wrap:pretty}
.muted{color:var(--muted)}
/* header */
header.site{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 90%,transparent);backdrop-filter:blur(10px)}
.hbar{display:flex;align-items:center;gap:12px;height:72px}
.brand{font-size:25px;letter-spacing:-.3px;display:flex;gap:10px;align-items:center;white-space:nowrap;color:var(--ink);text-decoration:none}
.logo{width:30px;height:30px;flex:none}
.lg-glass{fill:var(--bg)} .lg-frame{fill:none;stroke:var(--ink);stroke-width:9}
.lg-bar{transform-box:fill-box;transform-origin:50% 100%;animation:lg-rise 6s ease-in-out infinite}
.lg-bar.b2{animation-delay:.25s} .lg-bar.b3{animation-delay:.5s}
@keyframes lg-rise{0%,100%{transform:scaleY(1)}40%{transform:scaleY(.55)}60%{transform:scaleY(1.04)}}
@media (prefers-reduced-motion:reduce){.lg-bar{animation:none}}
nav{display:flex;gap:4px;margin-left:auto}
nav a{color:var(--ink);text-decoration:none;font-size:15px;padding:6px 10px;white-space:nowrap}
nav a:hover,nav a.on{text-decoration:underline;text-underline-offset:6px}
.tbtn{border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:9999px;width:38px;height:38px;cursor:pointer;flex:none;display:inline-grid;place-items:center;text-decoration:none}
.tbtn:hover{border-color:var(--ink)}
.hsub{font-size:14px;color:var(--muted);margin-top:-12px;padding-bottom:12px}
/* home headline and tracking strip */
.lede{font-size:72px;line-height:1.08;letter-spacing:-1.8px;text-align:center;max-width:900px;margin:56px auto 0}
.track{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:10px 24px;margin:28px 0 8px;font-size:15px;color:var(--muted)}
.track .tk{font-size:14px}
.track .trk{display:inline-flex;align-items:center;gap:9px;color:var(--ink);font-weight:500;white-space:nowrap}
.track .tlogo{width:30px;height:30px;padding:5px;border-radius:50%}
.track .tlogo.fill{padding:0}
.tlogo{display:inline-block;box-sizing:border-box;padding:3px;border-radius:6px;background:#fff;border:1px solid rgba(128,138,160,.35);vertical-align:middle;object-fit:contain;flex:none}
.tlogo.fill{padding:0;border-color:transparent}
.lbadge{display:inline-flex;align-items:center;justify-content:center;box-sizing:border-box;padding:0 3px;border-radius:6px;background:color-mix(in srgb,var(--lc) 22%,transparent);border:1px solid color-mix(in srgb,var(--lc) 60%,transparent);color:var(--ink);font-weight:700;letter-spacing:.2px;line-height:1;vertical-align:middle;flex:none}
/* section heads with a pill on the right */
.shead{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:64px 0 14px}
.shead h2{margin:0}
.pill{display:inline-flex;gap:6px;align-items:center;font-size:14px;padding:7px 15px;border-radius:9999px;border:1px solid var(--line);color:var(--muted);white-space:nowrap;text-decoration:none}
a.pill:hover{border-color:var(--ink);color:var(--ink)}
.card{background:var(--card2);border-radius:20px;padding:22px 26px}
.card h2{font-size:24px;margin:26px 0 8px} .card h2:first-child{margin-top:4px}
.card ol{padding-left:22px} .card li{margin:10px 0}
/* tables (tables page) */
table{border-collapse:collapse;font-size:14px;margin:12px 0;display:block;overflow-x:auto;max-width:100%;background:var(--card2);border-radius:16px;padding:6px 10px}
th,td{border-bottom:1px solid var(--line);padding:8px 10px;text-align:left;white-space:nowrap}
tr:last-child td{border-bottom:0}
th{color:var(--muted);font-weight:500;font-size:13px}
td .tlogo,td .lbadge{margin-right:8px}
details{margin:12px 0;color:var(--muted)}
.ctag{font-size:13px;color:var(--soft);margin:0 0 4px;text-transform:none}
.scard{font-family:var(--serif);font-size:21px;line-height:1.5;padding:26px 30px}
.scard p:not(.ctag){margin:0} .scard .ctag{font-family:"Schibsted Grotesk",system-ui,sans-serif}
.icards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr));gap:16px;margin-top:16px}
.icard h3{margin:2px 0 8px;font-size:22px;line-height:1.25} .icard p{margin:0 0 8px} .icard p:last-child{margin-bottom:0}
.lead-p{color:var(--muted);max-width:760px}
ul.weeks{list-style:none;padding:0;margin:0}
ul.weeks li{padding:14px 0;border-bottom:1px solid var(--line);display:flex;gap:16px;flex-wrap:wrap;align-items:baseline}
ul.weeks .date{font-family:var(--serif);font-size:20px;min-width:120px}
/* tooltip card, as on the digest */
.tip{position:absolute;z-index:50;max-width:300px;background:color-mix(in srgb,var(--tc,transparent) 12%,var(--card));color:var(--ink);border:1.5px solid var(--tc,var(--line));border-radius:14px;padding:10px 12px;font-size:13px;line-height:1.45;box-shadow:0 4px 24px rgba(0,0,0,.18);pointer-events:none}
.tip b{display:block;margin-bottom:2px} .tip span{display:block;color:var(--muted)} .tip span:last-child{color:var(--soft);font-size:12px;margin-top:3px}
footer.site{margin:96px auto 36px;padding-top:24px;border-top:1px solid var(--line);font-size:14px;color:var(--soft);display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px 24px}
footer.site a{color:var(--muted)}
.logos-note{flex-basis:100%;font-size:12px}
@media (max-width:760px){
  .wrap{padding:0 16px} .lede{font-size:44px;letter-spacing:-1px;margin-top:32px} h1{font-size:32px} h2,.shead{margin-top:48px} h2{font-size:24px}
  .brand{font-size:19px} .tbtn{width:32px;height:32px} .hbar{gap:6px} nav a{font-size:14px;padding:4px 6px} .hsub{font-size:13px} .card{padding:16px 16px}
}
@media (max-width:420px){.brand{font-size:15px;gap:5px} .logo{width:22px;height:22px} .hbar{gap:4px} .tbtn{width:30px;height:30px} nav a{padding:4px 4px}}
/* tables page on phones: rank, model and score on one line, the chart on its own line, details below */
@media (max-width:640px){
  .bcard{padding:18px 16px}
  .combo-wrap{overflow:visible}
  table.combo,table.combo tbody{display:block}
  table.combo tr{display:flex;flex-wrap:wrap;align-items:center;border-bottom:1px solid var(--line);padding:6px 0 6px 28px}
  table.combo tr:first-child{border-bottom:0;padding:0 0 0 28px}
  table.combo tr:first-child th{display:none}
  table.combo tr:first-child th.cc{display:block;flex:1 0 100%;width:auto;padding:0}
  table.combo td{border:0;padding:2px 0}
  table.combo td.c-rk{flex:0 0 28px;margin-left:-28px;color:var(--soft)}
  table.combo td.c-md{flex:1 1 auto;min-width:0;font-weight:500}
  table.combo td.c-sc{flex:0 0 auto;font-weight:600;padding-left:8px}
  table.combo td.cc{order:4;flex:1 0 100%;width:auto;padding:0}
  table.combo td.c-st,table.combo td.c-ci,table.combo td.c-co,table.combo td.c-ch,table.combo td.c-vs{order:5;font-size:12.5px;color:var(--muted);padding-right:12px}
  table.combo td:empty{display:none}
  table.combo td[data-l]:not(:empty)::before{content:attr(data-l);color:var(--soft)}
  table.combo svg.chart.cell,table.combo svg.chart.axis{width:100%;height:auto;min-width:0}
}
"""

THEME_INIT = ("<script>try{var t=localStorage.getItem('afb-theme');if(t)document.documentElement.dataset.theme=t;"
              "else if(matchMedia('(prefers-color-scheme: light)').matches)document.documentElement.dataset.theme="
              "'light';}catch(e){}</script>")

SCRIPT = """<script>
(function(){
  var root=document.documentElement, tb=document.getElementById('theme');
  function tlabel(){if(tb)tb.setAttribute('aria-label','Switch to '+(root.dataset.theme==='light'?'dark':'light')+' theme')}
  if(tb)tb.onclick=function(){root.dataset.theme=root.dataset.theme==='light'?'dark':'light';tlabel();try{localStorage.setItem('afb-theme',root.dataset.theme)}catch(e){}};
  tlabel();
  // Card tooltips: move each plain title into data-tip so only the styled card shows
  document.querySelectorAll('[title][data-tc]').forEach(function(el){el.dataset.tip=el.getAttribute('title');el.removeAttribute('title')});
  document.querySelectorAll('svg [data-tip] > title').forEach(function(t){t.remove()});
  var tip=document.createElement('div');tip.className='tip';tip.hidden=true;document.body.appendChild(tip);
  function esc(s){return s.replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function show(el){var L=el.dataset.tip.split('\\n');tip.innerHTML='<b>'+esc(L[0])+'</b>'+L.slice(1).map(function(x){return'<span>'+esc(x)+'</span>'}).join('');
    tip.style.setProperty('--tc',el.dataset.tc||'');tip.hidden=false;var r=el.getBoundingClientRect(),w=tip.offsetWidth,h=tip.offsetHeight;
    var x=Math.min(Math.max(8,r.left+r.width/2-w/2),innerWidth-w-8),y=r.top-h-8;if(y<64)y=r.bottom+8;tip.style.left=(x+scrollX)+'px';tip.style.top=(y+scrollY)+'px'}
  function hide(){tip.hidden=true}
  document.querySelectorAll('[data-tip]').forEach(function(el){el.addEventListener('mouseenter',function(){show(el)});el.addEventListener('mouseleave',hide);el.addEventListener('focus',function(){show(el)});el.addEventListener('blur',hide)});
  addEventListener('scroll',hide,{passive:true});
  // Rank-grid tile -> that benchmark's chart card: open "Show all" if the model is not in the top 5, then highlight its row
  document.querySelectorAll('a.go').forEach(function(a){a.addEventListener('click',function(){
    var card=document.querySelector(a.getAttribute('href'));if(!card)return;hide();
    var m=a.dataset.model,sel=function(box){return box?[].filter.call(box.querySelectorAll('g.row'),function(g){return g.dataset.model===m}):[]};
    var rows=sel(card.querySelector('.top')),d=card.querySelector('details.more');
    if(d){if(!rows.length){d.open=true;rows=sel(card.querySelector('.all'))}else{d.open=false}}
    rows.forEach(function(g){g.classList.remove('flash');void g.getBoundingClientRect();g.classList.add('flash')});
  })});
})();
</script>"""

# Short column labels for the rank grid; the last two are public-vote (Arena) benchmarks.
GRID_COLUMNS = [
    ("SWE Atlas (Overall)", "SWE Atlas"), ("SWE-Bench Pro V2 (Full)", "SWE-Bench Pro V2"),
    ("Terminal-Bench 4.0", "Terminal-Bench"), ("MCP-Atlas", "MCP-Atlas"), ("GDPval-AA", "GDPval-AA"),
    ("GDPx", "GDPx"), ("Agent Arena", "Agent Arena"), ("WebDev Arena", "WebDev Arena"),
]
CROWD_FROM = 6
MULTIPLE_GROUPS = [
    ("Independent tests · each chart has its own scale",
     ["SWE Atlas (Overall)", "SWE-Bench Pro V2 (Full)", "MCP-Atlas", "GDPval-AA"]),
    ("No margin published · dots only", ["Terminal-Bench 4.0", "GDPx"]),
    ("Public votes (Arena) · kept separate from the tests", ["Agent Arena", "WebDev Arena"]),
]


def header(sub: str, on: str = "") -> str:
    return (f"<header class='site'><div class='wrap hbar'><a class='brand' href='index.html'>{LOGO}"
            f"Frontier AI <em>Benchmarks</em></a><nav><a href='index.html#weeks'{' class=on' if on == 'weeks' else ''}>"
            f"Archive</a></nav>"
            f"<a class='tbtn' href='{REPO}' target='_blank' rel='noopener noreferrer' title='Source on GitHub' "
            f"aria-label='Source on GitHub (opens in a new tab)'>{ICON_GH}</a>"
            f"<a class='tbtn' href='{LINKEDIN}' target='_blank' rel='noopener noreferrer' title='{AUTHOR} on LinkedIn' "
            f"aria-label='{AUTHOR} on LinkedIn (opens in a new tab)'>{ICON_IN}</a>"
            f"<button type='button' class='tbtn' id='theme' title='Switch light / dark theme' "
            f"aria-label='Switch theme'>{ICON_THEME}</button></div>"
            f"<div class='wrap hsub'>{sub}</div></header>")


FOOTER = (
    "<footer class='wrap site'><span>" + SCHEDULE_LONG + " Every number links its source. "
    f"Created by <a href='{LINKEDIN}' target='_blank' rel='noopener noreferrer'>{AUTHOR}</a>.</span>"
    "<span><a class='ext' href='https://labs.scale.com/leaderboard'>Scale Labs</a> · "
    "<a class='ext' href='https://artificialanalysis.ai'>Artificial Analysis</a> · "
    "<a class='ext' href='https://gdpx.semianalysis.com/'>GDPx by SemiAnalysis</a> (top 3 quoted) · "
    "<a class='ext' href='https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset'>Arena</a> (CC-BY-4.0) · "
    f"<a href='index.html#weeks'>Archive</a> · <a class='ext' href='{REPO}'>Source</a></span>"
    "<span class='logos-note'>Summaries and insights are written by AI (Claude) from the tables and published "
    "automatically. Scores belong to their publishers. Logos are trademarks of their owners and are used only "
    "to identify each lab.</span></footer>")


def new_tab(page_html: str) -> str:
    """Every link that leaves the site (sources, publishers, GitHub) opens in a new tab."""
    def fix(m: re.Match) -> str:
        tag = m.group(0)
        if "target=" in tag:
            return tag
        return tag[:-1] + ' target="_blank" rel="noopener noreferrer">'
    return re.sub(r"<a\b[^>]*\bhref=['\"]https?://[^>]*>", fix, page_html)


def page(title: str, body: str, sub: str, on: str = "") -> str:
    return new_tab(
        "<!doctype html><html lang='en' data-theme='dark'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><meta name='description' content='{html.escape(TAGLINE)}'>"
        f"{THEME_INIT}<link rel='icon' type='image/svg+xml' href='assets/favicon.svg'>"
        "<link rel='preload' href='assets/fonts/schibsted-grotesk-latin-wght-normal.woff2' as='font' type='font/woff2' crossorigin>"
        "<link rel='preload' href='assets/fonts/newsreader-latin-wght-normal.woff2' as='font' type='font/woff2' crossorigin>"
        f"<style>{CSS}{charts.CSS}</style></head><body>{header(sub, on)}<main class='wrap'>"
        f"{body}</main>{FOOTER}{SCRIPT}</body></html>"
    )


def md_to_html(text: str) -> str:
    out = markdown.markdown(text, extensions=["tables"])
    # Links between reports point to .md files; the site serves .html.
    out = re.sub(r'href="(\d{4}-\d{2}-\d{2}-(?:report|insights))\.md"', r'href="\1.html"', out)
    out = re.sub(r">(\d{4}-\d{2}-\d{2})-report\.md<", r">tables for \1<", out)
    out = re.sub(r">(\d{4}-\d{2}-\d{2})-insights\.md<", r">summary and insights for \1<", out)
    # Source links leave the site: mark them with the arrow, as the digest does.
    return re.sub(r'<a href="(https?://[^"]+)">', r'<a class="ext" href="\1">', out)


def insights_cards(md_text: str) -> str:
    """Summary in one wide card, then one card per numbered insight."""
    summary = re.search(r"## Summary\s*\n(.*?)(?=\n## |\Z)", md_text, re.S)
    ins = re.search(r"## Insights\s*\n(.*?)(?=\n## |\Z)", md_text, re.S)
    out = []
    if summary and summary.group(1).strip():
        out.append("<div class='card scard'><p class='ctag'>Summary</p>"
                   + md_to_html(summary.group(1).strip()) + "</div>")
    items = re.split(r"\n(?=\d+\.\s)", "\n" + ins.group(1).strip()) if ins else []
    cards = []
    for it in (x.strip() for x in items):
        m = re.match(r"(\d+)\.\s+(.*)", it, re.S)
        if not m:
            continue
        num, body = m.groups()
        title = re.match(r"\*\*(.+?)\*\*\s*(.*)", body, re.S)
        head, rest = (title.group(1), title.group(2)) if title else ("", body)
        cards.append(f"<div class='card icard'><p class='ctag'>Insight {num}</p>"
                     + (f"<h3>{md_to_html(head)[3:-4]}</h3>" if head else "") + md_to_html(rest.strip()) + "</div>")
    if cards:
        out.append("<div class='icards'>" + "".join(cards) + "</div>")
    return "".join(out)


def italic_title(t: str) -> str:
    """One italic phrase, as on the digest: the words after the colon, or 'Benchmarks'."""
    t = html.escape(t)
    if ": " in t:
        a, b = t.split(": ", 1)
        return f"{a}: <em>{b}</em>"
    return t


def rows_by_bench(day: str) -> dict[str, list[dict]]:
    """The same rows, in the same order, that the tables file shows for each benchmark."""
    csv_path = DATA / "clean" / f"{day}.csv"
    if not csv_path.exists():
        return {}
    cur = read_csv(csv_path)
    out = {}
    for bench, _ in REPORT:
        rows = [r for r in cur if r["benchmark"] == bench]
        rows.sort(key=lambda r: (r["rank"] if r["rank"] is not None else 10**6, -r["score"]))
        rows = rows[:TOP_N_OVERRIDE.get(bench, TOP_N)]
        names = [r["model"] for r in rows]
        for r in rows:  # same model listed twice (different setups): show the setup in charts
            r["_show_setup"] = names.count(r["model"]) > 1 and bool(r["setup"])
        out[bench] = rows
    return out


def overview_charts(by_bench: dict[str, list[dict]], day: str) -> str:
    if not by_bench:
        return ""
    n = sum(1 for b, _ in GRID_COLUMNS if by_bench.get(b))
    return (f"<div class='shead'><h2>Leaders at a glance · update of {day}</h2>"
            f"<span class='pill'>{n} benchmarks · 4 publishers</span></div>"
            "<p class='muted'>Each tile is the model's rank on that benchmark. Ranks, not scores, because "
            "scores from different benchmarks are not comparable.</p>"
            + charts.rank_grid(by_bench, GRID_COLUMNS, CROWD_FROM)
            + "<div class='shead'><h2>Who is <em>really</em> tied?</h2>"
            f"<a class='pill' href='{day}-report.html'>All tables</a></div>"
            "<p class='muted'>The top models on each benchmark: the dot is the score, the line its 95% interval.</p>"
            + charts.small_multiples(by_bench, MULTIPLE_GROUPS))


VS_TEXT = {"lead": "leader", "close": "too close to call", "behind": "behind", "nomargin": "no margin published"}


def report_body(day: str, md_text: str, by_bench: dict[str, list[dict]]) -> str:
    """Tables page, built from the same rows as reports/<date>-report.md: one card per benchmark,
    with the chart drawn inside the table (a chart column on one shared scale per benchmark)."""
    import json
    from tracker import COLLECTORS, CREDIT_LINE, SPREAD_NOTE, baseline_csv
    full = read_csv(DATA / "clean" / f"{day}.csv")
    listed = {b: sum(1 for r in full if r["benchmark"] == b) for b, _ in REPORT}
    prev_file = baseline_csv(day)
    prev = {(r["benchmark"], r["model"], r["setup"]): r for r in read_csv(prev_file)} if prev_file else {}
    alerts_file = DATA / "alerts" / f"{day}.json"
    shown = {b for b, _ in REPORT} | set(COLLECTORS)
    alerts = [a for a in (json.loads(alerts_file.read_text(encoding="utf-8")) if alerts_file.exists() else [])
              if a["source"] in shown]

    out = [f"<h1>Frontier AI benchmark tracker: <em>update of {day}</em></h1>",
           "<p class='lead-p'>" + (f"Changes compare with {prev_file.stem}. " if prev_file else
                                   "First update: no changes to compare yet. ")
           + "Every score comes from the linked publisher page. Scores from different benchmarks are not "
             "comparable with each other. Hover a row for details.</p>",
           f"<p><a class='pill' href='{day}-insights.html'>Summary and insights</a></p>"]
    if alerts:
        out.append("<div class='card'><p class='ctag'>Collection alerts</p><ul>"
                   + "".join(f"<li><b>{html.escape(a['level'])}</b>, {html.escape(a['source'])}: "
                             f"{html.escape(a['message'])}</li>" for a in alerts) + "</ul></div>")
    for bench, area in REPORT:
        rows = by_bench.get(bench, [])
        if not rows:
            out.append(f"<div class='bcard'><p class='area'>{html.escape(area)}</p><h2>{html.escape(bench)}</h2>"
                       "<p class='muted'>No data in this update (see alerts).</p></div>")
            continue
        r0, unit = rows[0], rows[0]["unit"]
        has_m = r0["margin_low"] is not None
        has_cost = any(r["cost"] is not None for r in rows)
        basis = next((r["cost_basis"] for r in rows if r["cost_basis"]), "")
        src = r0["source_url"]
        metas = [f"<a class='pill ext' href='{html.escape(src)}'>{html.escape(charts.publisher(src))}</a>",
                 f"<span class='pill'>{html.escape(r0['trust'])}</span>",
                 f"<span class='pill'>data dated {max(r['source_date'] for r in rows)}</span>",
                 f"<span class='pill'>{listed[bench]} listed · top {len(rows)} shown</span>"]
        head = ["#", "Model", "Setup", "Score", f"<th class='cc'>{charts.axis_svg(rows)}</th>"]
        if has_m:
            head.append("95% interval")
        if has_cost:
            head.append(f"Cost ({html.escape(basis)})")
        head += ["Change", "Vs. #1"]
        ths = "".join(h if h.startswith("<th") else f"<th>{h}</th>" for h in head)
        trs = []
        for r in rows:
            st = charts.status(r, r0)
            p = prev.get((bench, r["model"], r["setup"]))
            if not prev_file:
                change = ""
            elif p is None:
                change = "new"
            else:
                d = r["score"] - p["score"]
                change = "same" if abs(d) < 1e-9 else (f"{d:+.1f}" if unit != "score" else f"{d:+.3f}")
            tip = charts.tip_text(r, bench, st, r["rank"])
            cells = [str(r["rank"] or ""),
                     f"{logo_html(lab_of(r['model']), 20, r['model'])}{html.escape(r['model'])}",
                     html.escape(r["setup"]), charts.fmt(r["score"], unit)]
            cls = ["num c-rk", "c-md", "c-st", "num c-sc"]  # c-* classes drive the phone layout
            tds = "".join(f"<td class='{k}'>{c}</td>" for k, c in zip(cls, cells))
            tds += f"<td class='cc'>{charts.cell_svg(rows, r, bench)}</td>"
            if has_m:
                tds += (f"<td class='num c-ci' data-l='95% interval '>{charts.fmt(r['margin_low'], unit)} to "
                        f"{charts.fmt(r['margin_high'], unit)}</td>" if r["margin_low"] is not None else "<td class='c-ci'></td>")
            if has_cost:
                tds += f"<td class='num c-co' data-l='Cost '>{'$%.2f' % r['cost'] if r['cost'] is not None else ''}</td>"
            tds += (f"<td class='num c-ch' data-l='Change '>{change}</td>"
                    f"<td class='c-vs'><span class='vs {st}'>{VS_TEXT[st]}</span></td>")
            trs.append(f"<tr class='r' title=\"{html.escape(tip)}\" data-tc='{charts.color_of(r['model'])}'>{tds}</tr>")
        notes = sorted({n.strip() for r in rows for n in r["note"].split(" | ")
                        if n.strip() and not n.startswith("API price")})
        extra = []
        if bench in CREDIT_LINE:
            extra.append(md_to_html(CREDIT_LINE[bench])[3:-4])
        if bench in SPREAD_NOTE:
            close = sum(1 for r in rows[1:] if charts.status(r, r0) == "close")
            extra.append(f"Top score {charts.fmt(r0['score'], unit)}; {close} other model"
                         f"{'s are' if close != 1 else ' is'} too close to call with #1.")
        extra += [("Rows marked * in the source: " if n.startswith("Run with") else "") + html.escape(n) for n in notes]
        legend = ("Dot = score, line = 95% interval, shaded band = the leader's interval, colour = the model's lab."
                  if has_m else "No margin published: dots only, so no tie can be judged.")
        title = html.escape(bench) + (f" <em>{html.escape(r0['version'])}</em>" if r0["version"] else "")
        out.append(f"<div class='bcard'><p class='area'>{html.escape(area)}</p><h2>{title}</h2>"
                   f"<div class='metas'>{''.join(metas)}</div>"
                   f"<div class='combo-wrap'><table class='combo'><tr>{ths}</tr>{''.join(trs)}</table></div>"
                   f"<p class='note'>{legend}</p>"
                   + "".join(f"<p class='note'>{x}</p>" for x in extra) + "</div>")
    method = re.search(r"## Method\s*\n(.*)", md_text, re.S)
    if method:
        out.append("<div class='shead'><h2>Method</h2></div><div class='card'>" + md_to_html(method.group(1)) + "</div>")
    return "".join(out)


def strip_h1(text: str) -> str:
    """Drop the title and the 'Written from ...' line (the home page shows its own heading and link)."""
    text = re.sub(r"^# .*\n", "", text, count=1)
    return re.sub(r"^\s*Written from .*\n", "", text, count=1)


def build() -> None:
    DOCS.mkdir(exist_ok=True)
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")  # serve files as-is
    (DOCS / "assets").mkdir(exist_ok=True)
    (DOCS / "assets" / "favicon.svg").write_text(FAVICON, encoding="utf-8")
    dates = sorted({m.group(1) for p in REPORTS.glob("*.md")
                    if (m := re.match(r"(\d{4}-\d{2}-\d{2})-(report|insights)\.md$", p.name))},
                   reverse=True)
    for d in dates:
        by_bench = rows_by_bench(d)
        sub = f"{TAGLINE} · update of {d} · {SCHEDULE}"
        for kind in ("report", "insights"):
            src = REPORTS / f"{d}-{kind}.md"
            if not src.exists():
                continue
            text = src.read_text(encoding="utf-8")
            h1 = re.match(r"# (.*)", text)
            title = h1.group(1) if h1 else f"{TITLE} {d}"
            if kind == "report":
                body_html = report_body(d, text, by_bench)
            else:  # title and source line, then the charts, then one card for the summary and one per insight
                intro = re.search(r"^Written from .*$", text, re.M)
                body_html = (f"<h1>{italic_title(title)}</h1>"
                             + (md_to_html(intro.group(0)).replace("<p>", "<p class='lead-p'>", 1) if intro else "")
                             + overview_charts(by_bench, d)
                             + "<div class='shead'><h2>Summary and <em>insights</em></h2></div>"
                             + insights_cards(text))
            (DOCS / f"{d}-{kind}.html").write_text(page(title, body_html, sub), encoding="utf-8")

    body = ["<div class='lede'>Who is <em>really</em> ahead right now?</div>"]
    if dates:
        latest = dates[0]
        by_bench = rows_by_bench(latest)
        body.append(charts.labs_strip(by_bench))
        body.append(overview_charts(by_bench, latest))
        ins = REPORTS / f"{latest}-insights.md"
        body.append(f"<div class='shead'><h2>Summary and <em>insights</em></h2>"
                    f"<a class='pill' href='{latest}-insights.html'>Open latest</a></div>")
        if ins.exists():
            body.append(insights_cards(ins.read_text(encoding="utf-8")))
        else:
            body.append("<p class='muted'>Insights for this update are not written yet.</p>")
    body.append("<div class='shead' id='weeks'><h2>All updates</h2></div><ul class='weeks'>")
    for d in dates:
        links = [f"<a href='{d}-insights.html'>Summary and insights</a>"] if (REPORTS / f"{d}-insights.md").exists() else []
        if (REPORTS / f"{d}-report.md").exists():
            links.append(f"<a href='{d}-report.html'>Tables</a>")
        body.append(f"<li><span class='date'>{d}</span>{' · '.join(links)}</li>")
    body.append("</ul>")
    sub = f"{TAGLINE} · last updated {latest} · {SCHEDULE}" if dates else f"{TAGLINE} · {SCHEDULE}"
    (DOCS / "index.html").write_text(page(TITLE, "".join(body), sub), encoding="utf-8")
    print(f"Built {DOCS} ({len(dates)} updates)")


if __name__ == "__main__":
    build()
