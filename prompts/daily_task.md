# Daily task: check for new data, write insights, publish

This file is the only source of the steps: the scheduled routine's prompt just says to follow it.
Run these steps in order from the repository root. Stop and report if a step fails.

1. Install dependencies: `python -m pip install -r requirements.txt` (use `python -m pip` so packages go to the same Python that runs the scripts)
2. Collect and build the tables: `python tracker.py all` (run it on its own, not piped into `tail` or
   `head`, so you see its exit code and its last line)
   - This collects from Scale, Artificial Analysis, GDPx and the Arena Hugging Face dataset, and writes
     `data/clean/<date>.csv`, `data/alerts/<date>.json` and `reports/<date>-report.md`,
     where `<date>` is today's UTC date.
   - If every collector failed, the script exits with an error and writes nothing: stop, do not commit
     or push, and report the errors.
   - If the script prints `NO NEW DATA` (exit code 3), every publisher's data matches the previous run:
     stop here, do not commit or push, and finish with the one-line summary
     `No new data since <previous date>; nothing published.`
   - If only some collectors failed, still publish: the report's alerts section shows which ones.
3. Open `prompts/analyze.md`, read all of it, and follow its steps to write `reports/<date>-insights.md`
   from `reports/<date>-report.md`.
4. Check the insights with the script: `python check_insights.py <date>`. It lists every number, link
   or section that breaks the rules. Fix the insights file (never the tables file) and run it again until
   it prints "Insights check passed". If it still fails after 3 attempts, do not commit or push: stop and
   report the problems it lists.
5. Build the website: `python build_site.py`
6. `git add data/clean data/alerts reports docs`, commit to the `main` branch and push.
   GitHub Pages publishes `docs/` automatically. Commit message:
   - If `reports/<date>-report.md` has a "Collection alerts" section: first line
     `Update <date> ⚠ <N> collection alerts`, then one line per alert copied from that section,
     so the alerts show in the GitHub commit list.
   - Otherwise: `Update <date>`.
   - If pushing to `main` is refused, push the same commit to a branch named `update-<date>`
     and say so in the final summary.

Rules:
- Never commit `data/raw/` (it is in `.gitignore`; it holds copies of publishers' pages).
- Never edit `reports/<date>-report.md` by hand; only the script writes it.

Finish with a short summary: rows collected per source, alerts, the headline of the insights, and
whether the push to `main` succeeded.
