# Prompt: write the summary and insights for an update

You write `reports/<date>-insights.md` from the tables file `reports/<date>-report.md`. Readers are
LinkedIn readers: smart, busy, not benchmark experts. Accuracy matters more than style. Never edit the
tables file: the script rebuilds it.

## Steps (do them in order)

1. **Read** `reports/<date>-report.md` from top to bottom. If earlier tables files exist in `reports/`,
   read only their "Change" column through today's file; never compute a change yourself.
2. **Make notes for each table** (in your head or a scratch file you delete; never commit it):
   - the leader, its score copied exactly as written (for example `80.5%`, `1866`, `0.303`);
   - every model marked "too close to call";
   - whether the table says "no margin published";
   - the table's trust label: `independent` (tests) or `crowd-preference` (Arena public votes);
   - the table's source link (the `Source:` line).
3. **Pick 3 or 4 insights.** Good insights are patterns a reader cannot see in one table:
   who leads where; ties; a benchmark that no longer separates models; cost against score
   (only when the table shows cost); changes since the earlier update (only from the "Change" column).
4. **Write the file** in the exact shape below.
5. **Run** `python check_insights.py <date>`. Fix every problem it lists and run it again until it passes.
6. **Re-read the file against the checklist** at the end of this prompt and fix anything that fails.

## Exact shape of the file

```
# Frontier AI benchmarks: summary and insights, update of <date>

Written from [<date>-report.md](<date>-report.md) (data collected <date>). If that tables file is collected again, check these insights still match.

## Summary

<3 to 5 sentences, at most 110 words. Lead with the main pattern, not with a single winner.>

## Insights

1. **<Bold one-line claim.>** <2 to 4 sentences with the numbers, then the source link.>

2. ...
```

Each numbered insight ends every claim with its table's source link written as `([source](<link>))`.

## Rules (all must hold)

1. **Numbers:** use only numbers that appear in the tables file, copied exactly as written (keep the
   decimals and the % sign). Never round, compute, estimate, subtract or recall a number. Write counts
   in words ("three other models") unless the number is in the tables file.
2. **Sources:** every insight names its benchmark table and repeats that table's source link. Use only
   links that appear in the tables file.
3. **Ties:** if the table marks models "too close to call", say exactly that. Never call one of them the
   winner, never say it "beats" them. Write: "X leads with 80.5%, but Y and Z are too close to call."
4. **No margin:** if the table says "no margin published", add "no margin is published" and do not call
   a gap clear unless the table's numbers differ a lot.
5. **One benchmark at a time:** never compare scores across different benchmarks (80% on one is not
   80% on another). Comparing a model's rank across benchmarks is fine ("first on SWE Atlas and on GDPx").
6. **Tests and public votes stay apart:** `independent` tables are tests; `crowd-preference` tables
   (Agent Arena, WebDev Arena) are public votes. Never put both in one sentence or one claim. When an
   insight needs both, start the votes sentence with "Separately, in public votes on …".
7. **Alerts:** mention a collection alert only if the tables file shows it in its "Collection alerts"
   section and it affects a table you discuss. Never cite alerts from `data/alerts/`.
8. **Plain words:** define each benchmark the first time you name it, using the definitions below.
   No hype words ("crushes", "dominates", "game-changer", "revolutionary").
9. **GDPx:** quote only what the tables file shows, and add the credit "GDPx by SemiAnalysis" next to
   its source link.
10. **Changes:** say "first update, nothing to compare yet" when the tables file says so. Otherwise
    describe changes only with the "Change" column's values ("new", "same", "+1.2").

## Benchmark definitions (use these words)

- **SWE Atlas:** Scale's test of professional coding work: answering questions about a codebase,
  writing tests and refactoring.
- **SWE-Bench Pro V2:** fixing real issues in software projects.
- **Terminal-Bench 4.0:** coding tasks done in a computer terminal.
- **MCP-Atlas:** using tools and apps through MCP connections to finish multi-step tasks.
- **GDPval-AA:** realistic office-work tasks, rated with a chess-style Elo score.
- **GDPx:** very hard expert tasks in fields such as chip design, finance and law.
- **Agent Arena:** public votes: people rate AI agents on their own real tasks.
- **WebDev Arena:** public votes: people compare websites and apps built by two models.

## Checklist before you finish

- [ ] `python check_insights.py <date>` passes.
- [ ] Summary has 3 to 5 sentences and no single "winner" unless one model leads clearly everywhere.
- [ ] Every "too close to call" in the tables I mention is also said in my text.
- [ ] No sentence mixes a public-vote table with a test table.
- [ ] Every benchmark is defined the first time it appears.
- [ ] GDPx sentences carry "GDPx by SemiAnalysis".
