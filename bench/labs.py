"""Which lab makes each model, with the lab's colour and logo for the website.

Colours for the first five labs match the Coding Agents Digest tool colours (Claude Code coral = Anthropic,
Antigravity blue = Google, Codex green = OpenAI), so both sites read alike. Logos are the same files the
digest uses (docs/assets/logos/, copied from IbrahimSobh/coding-agents-digest): Claude for Anthropic,
Antigravity for Google, Codex for OpenAI. The other labs' logos come from the ai-news-reel skill library;
MiniMax and Inkling logos were supplied by the repo owner. docs/assets/logos/CREDITS.md lists each file's source
and licence. Labs without a logo get a short text badge instead.
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
    "MiniMax":     {"color": "#e8506e", "logo": "minimax.png", "fill": True},
    "Inkling":     {"color": "#5c5560", "logo": "inkling.png", "fill": True, "wide": True},
    "Mistral AI":  {"color": "#d9a066", "logo": "mistral.png"},
    "Xiaomi":      {"color": "#e09a6b", "logo": "xiaomi.png"},
    "Other":       {"color": "#8a8494", "logo": None},
}

# First word(s) of the canonical model name -> lab
PREFIXES = [
    (r"^Claude\b", "Anthropic"), (r"^(Gemini|Gemma)\b", "Google"), (r"^(GPT|O\d|OpenAI)\b", "OpenAI"),
    (r"^(Muse|Llama)", "Meta"), (r"^Kimi\b", "Moonshot AI"), (r"^DeepSeek\b", "DeepSeek"),
    (r"^Grok\b", "xAI"), (r"^Qwen", "Qwen"), (r"^GLM\b", "Zhipu AI"), (r"^MiniMax\b", "MiniMax"),
    (r"^(Mistral|Devstral|Codestral)\b", "Mistral AI"), (r"^Mimo\b", "Xiaomi"), (r"^Inkling\b", "Inkling"),
]


def lab_of(model: str) -> str:
    for pat, lab in PREFIXES:
        if re.search(pat, model, re.I):
            return lab
    return "Other"


def color_of(model: str) -> str:
    return LABS[lab_of(model)]["color"]


def badge_text(lab: str, model: str = "") -> str:
    """Short text for a lab with no logo: the lab's initials, or for 'Other' the model name's first letters."""
    if lab == "Other":
        word = re.sub(r"[^A-Za-z0-9]", "", (model.split() or ["?"])[0]) or "?"
        return word[:2].capitalize()
    words = re.findall(r"[A-Za-z0-9]+", lab)
    return ("".join(w[0] for w in words) if len(words) > 1 else lab[:2]).upper()[:3]


def logo_html(lab: str, size: int = 22, model: str = "") -> str:
    """The lab's mark on a white tile (as on the digest, visible in both themes), or a text badge."""
    info = LABS.get(lab, LABS["Other"])
    if not info["logo"]:
        name = model if lab == "Other" and model else lab
        return (f"<span class='lbadge' style='--lc:{info['color']};height:{size}px;min-width:{size}px;"
                f"font-size:{max(9, round(size * 0.42))}px' title='{html.escape(name)}' aria-hidden='true'>"
                f"{html.escape(badge_text(lab, model))}</span>")
    cls = "tlogo" + (" fill" if info.get("fill") else "") + (" wide" if info.get("wide") else "")
    width = round(size * 2.2) if info.get("wide") else size  # wordmarks that may not be cropped get a wider tile
    return (f"<img class='{cls}' src='assets/logos/{info['logo']}' width='{width}' height='{size}' "
            f"alt='' title='{html.escape(lab)}'>")
