"""Turn each publisher's model name into one canonical name plus a setup string.

Examples:
  "Claude Fable 5.2 (Max, Default Fallback)"   -> "Claude Fable 5.2", setup "Max, Default Fallback"
  "Fable 5.1 (Claude Code) high"               -> "Claude Fable 5.1", setup "Claude Code, high"
  "gpt-5.4 (xHigh)*"                           -> "GPT-5.4",          setup "xHigh"
  "Gemini-4-Argon"                             -> "Gemini 4 Argon"

Names the rules cannot place go to model_aliases.json ("raw name": "Canonical Name").
Unknown names are never guessed silently: the report lists every name that only
appears at one publisher, so a human can add an alias.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ALIASES_FILE = Path(__file__).resolve().parent.parent / "model_aliases.json"
EFFORT_WORDS = {"max", "xhigh", "high", "medium", "low", "minimal", "highest", "thinking", "none"}
CLAUDE_FAMILIES = {"opus", "fable", "sonnet", "haiku"}
UPPER_TOKENS = {"gpt": "GPT", "glm": "GLM", "ai": "AI", "vl": "VL"}
BRAND_CASE = {"deepseek": "DeepSeek", "minimax": "MiniMax", "openai": "OpenAI"}


def _aliases() -> dict[str, str]:
    if ALIASES_FILE.exists():
        return json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
    return {}


def split_name(raw: str) -> tuple[str, str]:
    """Return (base name, setup) from a raw publisher name."""
    s = raw.strip().rstrip("*").strip()
    setup = [p.strip() for p in re.findall(r"\(([^)]*)\)", s)]
    s = re.sub(r"\([^)]*\)", " ", s)
    words = s.split()
    while words and words[-1].lower() in EFFORT_WORDS:
        setup.append(words.pop())
    return " ".join(words), ", ".join(x for x in setup if x)


def canonical(base: str) -> str:
    """Canonical display name from a base name (effort and harness already removed)."""
    aliases = _aliases()
    if base in aliases:
        return aliases[base]
    b = re.sub(r"(?<=\d)p(?=\d)", ".", base)            # "glm-4p7"   -> "glm-4.7"
    # Two standalone single digits are a version: "opus-4-6" / "Opus 4 6" -> "4.6".
    b = re.sub(r"(?<![\w.])(\d)[- ](\d)(?![\w.])", r"\1.\2", b)
    tokens = re.sub(r"[\s_]+", " ", b.replace("-", " ")).strip().split(" ")
    tokens = [t for t in tokens if t]
    if not tokens:
        return base
    if tokens[0].lower() in CLAUDE_FAMILIES:
        tokens = ["claude"] + tokens
    out = []
    for t in tokens:
        low = t.lower()
        if low in UPPER_TOKENS:
            out.append(UPPER_TOKENS[low])
        elif low in BRAND_CASE:
            out.append(BRAND_CASE[low])
        elif re.fullmatch(r"[a-z]+", low):
            out.append(low.capitalize())
        elif re.fullmatch(r"[a-z]\d[\d.]*", low):          # "k3" -> "K3", "v4.1" -> "V4.1"
            out.append(low.upper())
        else:
            out.append(t)
    name = " ".join(out)
    # GPT names are written "GPT-6.1 Sol" by most publishers.
    name = re.sub(r"^GPT (\d)", r"GPT-\1", name)
    return aliases.get(name, name)


def canonicalize(raw: str) -> tuple[str, str]:
    base, setup = split_name(raw)
    return canonical(base), setup
