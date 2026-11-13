# Weekly task: collect, write insights, publish

Run these steps in order from the repository root. Stop and report if a step fails.

1. Install dependencies: `pip install -r requirements.txt`
2. Collect and build the tables: `python tracker.py all`
   - This writes `data/clean/<date>.csv`, `data/alerts/<date>.json` and `reports/<date>-report.md`,
     where `<date>` is today's date.
   - If every collector failed (the CSV has no rows), stop: do not publish an empty week.
3. Read `reports/<date>-report.md` and write `reports/<date>-insights.md`, following every rule in
   `prompts/analyze.md`. Use only numbers that appear in the tables file.
4. Check the insights: every number in `reports/<date>-insights.md` must appear in
   `reports/<date>-report.md`. Fix any that do not.
5. Build the website: `python build_site.py`
6. Commit `data/clean/`, `data/alerts/`, `reports/` and `docs/` to the `main` branch with the message
   `Weekly update <date>` and push. GitHub Pages publishes `docs/` automatically.

Never commit `data/raw/` (it is in `.gitignore`).
