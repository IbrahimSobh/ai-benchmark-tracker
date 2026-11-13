"""Check an AI-written insights file against its tables file, without any AI.

  python check_insights.py            # newest reports/<date>-insights.md
  python check_insights.py 2026-11-13

Fails (exit code 1) and lists every problem when:
- a number in the insights does not appear in the tables file (dates and list numbers are skipped);
- a link points somewhere the tables file never links (except the GDPx home page and the tables file itself);
- the title, the "Written from" line, the Summary or the Insights section is missing or misdated;
- there are not 3 or 4 numbered insights, or an insight has no source link;
- the summary is longer than 5 sentences;
- the tables file says "First update" but the insights do not say so.
The daily task runs this after writing the insights, fixes every problem, and runs it again.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPORTS = Path(__file__).resolve().parent / "reports"
ALLOWED_LINKS = {"https://gdpx.semianalysis.com/"}
NUM = re.compile(r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?%?")


def numbers(text: str) -> set[str]:
    """Numbers as written, without $ , % so that '80.5%' in the insights matches '80.5%' or '80.5' in the tables."""
    return {m.group(0).strip("$%").replace(",", "") for m in NUM.finditer(text)}


def check(day: str) -> list[str]:
    ins_file, rep_file = REPORTS / f"{day}-insights.md", REPORTS / f"{day}-report.md"
    if not ins_file.exists() or not rep_file.exists():
        return [f"missing {ins_file.name} or {rep_file.name}"]
    ins, rep = ins_file.read_text(encoding="utf-8"), rep_file.read_text(encoding="utf-8")
    problems: list[str] = []

    # Shape
    if not ins.startswith(f"# Frontier AI benchmarks: summary and insights, update of {day}\n"):
        problems.append(f"first line must be '# Frontier AI benchmarks: summary and insights, update of {day}'")
    if f"Written from [{day}-report.md]({day}-report.md)" not in ins:
        problems.append(f"missing the line 'Written from [{day}-report.md]({day}-report.md) ...'")
    summary = re.search(r"^## Summary\s*\n(.*?)(?=^## )", ins, re.S | re.M)
    insights = re.search(r"^## Insights\s*\n(.*)", ins, re.S | re.M)
    if not summary:
        problems.append("missing '## Summary' section (it must come before '## Insights')")
    elif len(re.findall(r"[.!?](?:\s|$)", summary.group(1).strip())) > 5:
        problems.append("summary is longer than 5 sentences")
    if not insights:
        problems.append("missing '## Insights' section")
    else:
        items = re.split(r"(?m)^\d+\.\s", insights.group(1))[1:]
        if not 3 <= len(items) <= 4:
            problems.append(f"found {len(items)} numbered insights; write 3 or 4")
        for i, item in enumerate(items, 1):
            if "](http" not in item:
                problems.append(f"insight {i} has no source link")

    # Rule 10 of prompts/analyze.md: say so when there is nothing to compare yet
    if "First update: no changes to compare yet" in rep and "first update" not in ins.lower():
        problems.append("the tables file says this is the first update; say 'first update, nothing to compare yet'")

    # Links: only pages the tables file links to
    rep_links = set(re.findall(r"\]\((https?://[^)\s]+)\)", rep)) | set(re.findall(r"https?://[^\s)|>]+", rep))
    for link in sorted(set(re.findall(r"\]\((https?://[^)\s]+)\)", ins))):
        if link not in rep_links and link not in ALLOWED_LINKS:
            problems.append(f"link not found in the tables file: {link}")

    # Numbers: every number must appear in the tables file
    body = re.sub(r"\]\([^)]*\)", "]", ins)                      # drop link targets
    body = re.sub(r"\d{4}-\d{2}-\d{2}", "", body)                 # dates
    body = re.sub(r"(?m)^\s*\d+\.\s", "", body)                   # list numbers
    missing = sorted(n for n in numbers(body) - numbers(rep) if n)
    for n in missing:
        ctx = re.search(rf".{{0,40}}(?<![\w.]){re.escape(n)}.{{0,25}}", body)
        problems.append(f"number {n} is not in the tables file: ...{ctx.group(0).strip() if ctx else n}...")
    return problems


def main() -> None:
    if len(sys.argv) > 1:
        day = sys.argv[1]
    else:
        files = sorted(REPORTS.glob("*-insights.md"))
        if not files:
            sys.exit("No insights file yet.")
        day = files[-1].name[:10]
    problems = check(day)
    if problems:
        print(f"Insights check FAILED for {day} ({len(problems)} problem(s)):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print(f"Insights check passed for {day}.")


if __name__ == "__main__":
    main()
