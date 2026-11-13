"""Which lab makes each model, with the lab's colour and logo for the website.

Colours for the first five labs match the Coding Agents Digest tool colours (Claude Code coral = Anthropic,
Antigravity blue = Google, Codex green = OpenAI), so both sites read alike. Logos are the same files the
digest uses (docs/assets/logos/, copied from IbrahimSobh/coding-agents-digest): Claude for Anthropic,
Antigravity for Google, Codex for OpenAI. The other labs' logos come from the ai-news-reel skill library;
docs/assets/logos/CREDITS.md lists each file's source and licence. Labs without a logo get a coloured dot.
Logos are trademarks of their owners and are used only to identify each lab.
"""
from __future__ import annotations

import html
import re

LABS = {
    "Anthropic":   {"color": "#e07a5f", "logo": "claude.png"},
    "Google":      {"color": "#5b8def", "logo": "antigravity.png"},
    "OpenAI":      {"color": "#2fb38a", "logo": "codex.png", "fill": True},
    "Meta":        {"color": "#e3b341", "logo": "meta.png"},
    "Moonshot AI": {"color": "#a78bfa", "logo": "kimi.png", "wide": True},  # official wordmark, unaltered
    "DeepSeek":    {"color": "#7f9cc7", "logo": "deepseek.png"},
    "xAI":         {"color": "#a3a3a8", "logo": "xai.png"},
    "Qwen":        {"color": "#c98fb0", "logo": "qwen.png"},
    "Zhipu AI":    {"color": "#8fb996", "logo": "zhipu.png"},
    "MiniMax":     {"color": "#c9a77c", "logo": None},
    "Mistral AI":  {"color": "#d9a066", "logo": "mistral.png"},
    "Xiaomi":      {"color": "#e09a6b", "logo": "xiaomi.png"},
    "Other":       {"color": "#8a8494", "logo": None},
}

# First word(s) of the canonical model name -> lab
PREFIXES = [
    (r"^Claude\b", "Anthropic"), (r"^(Gemini|Gemma)\b", "Google"), (r"^(GPT|O\d|OpenAI)\b", "OpenAI"),
    (r"^(Muse|Llama)\b", "Meta"), (r"^Kimi\b", "Moonshot AI"), (r"^DeepSeek\b", "DeepSeek"),
    (r"^Grok\b", "xAI"), (r"^Qwen", "Qwen"), (r"^GLM\b", "Zhipu AI"), (r"^MiniMax\b", "MiniMax"),
    (r"^(Mistral|Devstral|Codestral)\b", "Mistral AI"), (r"^Mimo\b", "Xiaomi"),
]


def lab_of(model: str) -> str:
    for pat, lab in PREFIXES:
        if re.search(pat, model, re.I):
            return lab
    return "Other"


def color_of(model: str) -> str:
    return LABS[lab_of(model)]["color"]


def logo_html(lab: str, size: int = 22) -> str:
    """The lab's mark on a white tile (as on the digest, visible in both themes), or a coloured dot."""
    info = LABS.get(lab, LABS["Other"])
    if not info["logo"]:
        return (f"<span class='ldot' style='--lc:{info['color']};width:{size}px;height:{size}px' "
                f"aria-hidden='true'></span>")
    cls = "tlogo" + (" fill" if info.get("fill") else "") + (" wide" if info.get("wide") else "")
    width = round(size * 2.2) if info.get("wide") else size  # wordmarks that may not be cropped get a wider tile
    return (f"<img class='{cls}' src='assets/logos/{info['logo']}' width='{width}' height='{size}' "
            f"alt='' title='{html.escape(lab)}'>")
