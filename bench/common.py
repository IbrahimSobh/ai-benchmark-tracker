"""Shared pieces: the clean row format, polite fetching, raw-page saving, alerts."""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = "Mozilla/5.0 (compatible; benchmark-tracker/0.1; weekly personal research)"

# Trust labels. Every row carries exactly one.
INDEPENDENT = "independent"          # a third party ran the model on the benchmark
CROWD = "crowd-preference"           # ranking built from public human votes
VENDOR = "vendor-reported"           # the model maker reported the score (never mixed with the others)


@dataclasses.dataclass
class Row:
    benchmark: str            # e.g. "SWE-Bench Pro V2 (Full)"
    version: str              # publisher's version label, or ""
    model: str                # canonical name (filled in by names.canonicalize)
    model_raw: str            # name exactly as the publisher wrote it
    setup: str                # effort / harness / agent, as published
    score: float
    unit: str                 # "%", "Elo", "score"
    margin_low: float | None  # lower bound of the published interval, if any
    margin_high: float | None # upper bound of the published interval, if any
    cost: float | None        # USD, as published
    cost_basis: str           # what the cost means, e.g. "USD per task"
    rank: int | None          # publisher's rank, if published
    source_url: str
    trust: str
    source_date: str          # newest date the publisher shows for this data
    collected: str            # date we collected it
    note: str = ""


class CollectorAlert(Exception):
    """Raised when a source looks broken (zero rows, odd shape)."""


def today() -> str:
    return dt.date.today().isoformat()


def fetch(url: str, timeout: int = 45) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    return r.text


def fetch_bytes(url: str, timeout: int = 60) -> bytes:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    return r.content


def save_raw(day: str, name: str, content: str | bytes) -> Path:
    """Keep every raw page with its date, so any number can be re-checked later."""
    folder = DATA / "raw" / day
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / name
    if isinstance(content, bytes):
        p.write_bytes(content)
    else:
        p.write_text(content, encoding="utf-8")
    return p


def sha(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()[:16]


def next_flight(html: str) -> str:
    """Decode the data a Next.js page embeds in self.__next_f.push(...) calls."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
    return "".join(json.loads('"' + c + '"') for c in chunks)


def json_after(text: str, marker: str):
    """Parse the JSON value that starts right after `marker` in `text`."""
    i = text.find(marker)
    if i < 0:
        raise CollectorAlert(f"marker {marker!r} not found; page layout may have changed")
    value, _ = json.JSONDecoder().raw_decode(text[i + len(marker):])
    return value


def board_failed(alerts: list | None, collector: str, benchmark: str, board: str, e: Exception) -> None:
    """Record one broken board so the collector can keep its other boards.

    Call inside `except`. With no alert list (a collector run on its own), the error is raised again.
    """
    if alerts is None:
        raise e
    alerts.append({"level": "error", "source": collector, "benchmark": benchmark,
                   "message": f"{board} failed, other boards kept: {type(e).__name__}: {e}"})


def require_rows(rows: list, source: str, minimum: int = 3) -> list:
    if len(rows) < minimum:
        raise CollectorAlert(f"{source}: only {len(rows)} rows (expected at least {minimum})")
    return rows
