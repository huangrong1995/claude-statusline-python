"""3-row statusline assembly.

Row 1: MODEL · DIRECTORY · GIT · USAGE
Row 2: CTX | CACHE | TOK | TIP
Row 3: progress bar + percentage
"""
from __future__ import annotations

import os

from statusline.parse import Context
from statusline.state import TipRotation
from statusline.tips import select_tip, TipResult
from statusline.usage import UsageInfo, UsageWindow, format_resets_in
from statusline.output import (
    CLR_DIM, CLR_TEXT, CLR_ACCENT, CLR_RESET,
    colorize, truncate, pct_color,
)


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        v = (n + 50_000) // 100_000
        return f"{v // 10}.{v % 10}M"
    v = (n + 50) // 100
    return f"{v // 10}.{v % 10}k"


def _row1_git(ctx: Context) -> str:
    ws = ctx.workspace
    display = ""
    if ws.git_worktree and ws.git_worktree != "null":
        display = ws.git_worktree
    elif ws.worktree_name and ws.worktree_name != "null":
        display = ws.worktree_name
    elif ws.repo_owner and ws.repo_name:
        display = f"{ws.repo_owner}/{ws.repo_name}"
    if not display:
        return colorize("--", CLR_DIM)
    if len(display) > 30:
        display = "…" + display[-29:]
    return f"{CLR_DIM}⎇ {display}{CLR_RESET}"


def _row1_usage_window(label: str, w: UsageWindow) -> str:
    """Format one window segment: 5h[27%]⏰1h28m →42%

    Brackets get pct_color(); countdown + arrow + projection stay DIM."""
    used = colorize(f"{w.used_pct:3.0f}%", pct_color(w.used_pct))
    countdown = colorize(f"⏰{format_resets_in(w.resets_in_seconds)}", CLR_DIM)
    projection = colorize(f"→{w.projected_pct:3.0f}%", CLR_DIM)
    return f"{CLR_TEXT}{label}{CLR_RESET}[{used}]{countdown} {projection}"


def _row1_usage(usage: UsageInfo | None) -> str:
    """Render the usage segment, or '' when no windows are present."""
    if usage is None:
        return ""
    parts: list[str] = []
    if usage.five_hour is not None:
        parts.append(_row1_usage_window("5h", usage.five_hour))
    if usage.seven_day is not None:
        parts.append(_row1_usage_window("7d", usage.seven_day))
    return f"{CLR_DIM} | {CLR_RESET}".join(parts)


def row1(ctx: Context, usage: UsageInfo | None = None) -> str:
    model = colorize(ctx.model.display_name or "--", CLR_ACCENT)
    directory = colorize(truncate(ctx.workspace.current_dir or "", 40), CLR_DIM)
    git = _row1_git(ctx)
    sep = f"{CLR_DIM} | {CLR_RESET}"
    base = f"{CLR_ACCENT}✨ {CLR_RESET}{model}{sep}{CLR_DIM}📁 {CLR_RESET}{directory}{sep}{git}"
    usage_seg = _row1_usage(usage)
    if usage_seg:
        return f"{base}{sep}{usage_seg}"
    return base


def _row2_ctx(ctx: Context) -> str:
    pct = ctx.context_window.used_percentage
    label = colorize("🧠 CTX", CLR_DIM)
    if pct < 0:
        return f"{label} {colorize('--', CLR_DIM)}"
    return f"{label} {colorize(f'{pct:.0f}%', pct_color(pct))}"


def _row2_cache(ctx: Context) -> str:
    cw = ctx.context_window
    label = colorize("⚡ CACHE", CLR_DIM)
    if not cw.current_usage:
        return f"{label} {colorize('--', CLR_DIM)}"
    u = cw.current_usage
    total = u.cache_read_input_tokens + u.cache_creation_input_tokens
    if total == 0:
        return f"{label} {colorize('--', CLR_DIM)}"
    rate = (u.cache_read_input_tokens * 100) // total
    return f"{label} {colorize(f'{rate}%', CLR_TEXT)}"


def _row2_tok(ctx: Context) -> str:
    """D-class defense: uses total_input_tokens + total_output_tokens,
    NOT context_window_size (which is the model max and a different concept)."""
    cw = ctx.context_window
    label = colorize("🔁 TOK", CLR_DIM)
    if cw.total_input_tokens == 0 and cw.total_output_tokens == 0:
        return f"{label} {colorize('--', CLR_DIM)}"
    total = cw.total_input_tokens + cw.total_output_tokens
    in_fmt = _fmt_tokens(cw.total_input_tokens)
    out_fmt = _fmt_tokens(cw.total_output_tokens)
    total_fmt = _fmt_tokens(total)
    return (
        f"{label} {colorize(f'↑{in_fmt}', CLR_TEXT)} "
        f"{colorize(f'↓{out_fmt}', CLR_DIM)} "
        f"{colorize(f'/{total_fmt}', CLR_DIM)}"
    )


def _row2_tip(ctx: Context, rot: TipRotation, ai_tip: str, state_tags: list[str], elapsed: int) -> str:
    label = colorize("💡 TIP", CLR_DIM)
    result: TipResult = select_tip(
        ctx, rot, state_tags=state_tags, elapsed=elapsed, ai_tip=ai_tip,
    )
    color = CLR_ACCENT if result.is_ai else CLR_TEXT
    return f"{label} {colorize(result.text, color)}"


def row2(
    ctx: Context,
    rot: TipRotation,
    *,
    ai_tip: str = "",
    state_tags: list[str] | None = None,
    elapsed: int = 0,
) -> str:
    parts = [
        _row2_ctx(ctx),
        _row2_cache(ctx),
        _row2_tok(ctx),
        _row2_tip(ctx, rot, ai_tip, state_tags or [], elapsed),
    ]
    sep = f"{CLR_DIM} | {CLR_RESET}"
    return sep.join(parts)


def row3(ctx: Context) -> str:
    pct = ctx.context_window.used_percentage
    width = 28
    if "COLUMNS" in os.environ:
        try:
            cols = int(os.environ["COLUMNS"])
            if cols > 60:
                width = max(10, min(20, cols * 20 // 100))
        except (ValueError, TypeError):
            pass

    BLK_FILLED = "▰"
    BLK_EMPTY = "▱"
    pct_int = int(pct) if pct >= 0 else 0
    pct_int = max(0, min(100, pct_int))
    filled = pct_int * width // 100
    empty = width - filled

    if pct < 0:
        empty_bar = BLK_EMPTY * width
        return f"{colorize(empty_bar, CLR_DIM)} {colorize('--', CLR_DIM)}"

    filled_str = BLK_FILLED * filled
    empty_str = BLK_EMPTY * empty
    fill_color = pct_color(pct_int)
    return (
        f"{colorize(filled_str, fill_color)}"
        f"{colorize(empty_str, CLR_DIM)}"
        f" {colorize(f'{pct_int:3d}%', fill_color)}"
    )
