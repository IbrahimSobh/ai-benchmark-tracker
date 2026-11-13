"""Arena (arena.ai). Method: Arena's official Hugging Face dataset (CC-BY-4.0).

arena.ai pages sit behind a Cloudflare bot check, so this collector does NOT scrape them.
Dataset: https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset
"""
from __future__ import annotations

import io

import pandas as pd

from .common import CROWD, Row, fetch_bytes, require_rows, save_raw
from .names import canonicalize

HF = "https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/resolve/main/{cfg}/latest-00000-of-00001.parquet"
BOARDS = [
    # dataset config, benchmark name, page url, score col, low col, high col, unit
    ("agent", "Agent Arena", "https://arena.ai/leaderboard/agent",
     "score", "score_ci_lower", "score_ci_upper", "score"),
    ("webdev", "WebDev Arena", "https://arena.ai/leaderboard/code/webdev",
     "rating", "rating_lower", "rating_upper", "Elo"),
]


def collect(day: str) -> list[Row]:
    rows: list[Row] = []
    for cfg, bench, page, sc, lo, hi, unit in BOARDS:
        raw = fetch_bytes(HF.format(cfg=cfg))
        save_raw(day, f"arena_{cfg}.parquet", raw)
        df = pd.read_parquet(io.BytesIO(raw))
        df = df[df["category"] == "overall"]
        board = []
        for _, r in df.iterrows():
            model, setup = canonicalize(r["model_name"])
            cost = r.get("cost_per_task_p50")
            board.append(Row(
                benchmark=bench, version="", model=model, model_raw=r["model_name"], setup=setup,
                score=round(float(r[sc]), 4 if unit == "score" else 1), unit=unit,
                margin_low=round(float(r[lo]), 4 if unit == "score" else 1),
                margin_high=round(float(r[hi]), 4 if unit == "score" else 1),
                cost=None if cost is None or pd.isna(cost) else round(float(cost), 2),
                cost_basis="USD per task (median)" if cost is not None and not pd.isna(cost) else "",
                rank=int(r["rank"]), source_url=page, trust=CROWD,
                source_date=str(r["leaderboard_publish_date"]), collected=day,
                note="Arena leaderboard dataset, CC-BY-4.0",
            ))
        rows += require_rows(board, f"Arena {cfg}")
    return rows
