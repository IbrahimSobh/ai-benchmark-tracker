# Prompt: write the summary and insights for a weekly report

Read this week's tables file `reports/<date>-report.md` (and earlier tables files, if they exist).
Write a separate file `reports/<date>-insights.md`. Never edit the tables file: the script rebuilds it.

The insights file has this shape:

```
# Frontier AI benchmarks: summary and insights, week of <date>

Written from [<date>-report.md](<date>-report.md) (data collected <date>). If that tables file is collected again, check these insights still match.

## Summary

<3 to 5 sentences>

## Insights

<3 or 4 numbered insights, each with its source link>
```

Rules (all must hold):
1. Use only numbers that appear in the tables file. Never compute, estimate or recall a number.
2. Every insight names the benchmark table it comes from and repeats that table's source link.
3. If the table says "too close to call", say the models are too close to call. Never call one of them the winner.
4. If the table says "no margin published", do not claim a clear gap unless the difference is large, and say no margin is published.
5. Never compare scores across different benchmarks (a % on one is not a % on another). Comparing a model's rank across benchmarks is fine.
6. Keep trust labels apart: never combine crowd-preference rankings (Arena) with independent test scores into one claim.
7. Mention every collection alert that affects a table you discuss.
8. Plain language for LinkedIn readers. Define each benchmark in a few words the first time you name it.
9. GDPx: quote only what the tables file shows, and credit "GDPx by SemiAnalysis".
