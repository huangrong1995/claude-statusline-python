"""render.py unit tests — 3-row assembly."""
import pytest

from statusline.parse import (
    Context, ModelInfo, WorkspaceInfo, ContextWindowInfo, UsageInfo as CtxUsageInfo,
    ThinkingInfo, VimInfo, EffortInfo,
)
from statusline.state import TipRotation
from statusline.tips import TipPool
from statusline.usage import UsageInfo, UsageWindow
from statusline.render import row1, row2, row3


def make_ctx(**overrides) -> Context:
    base = dict(
        model=ModelInfo(display_name="Claude 4.6 Sonnet", id="x"),
        workspace=WorkspaceInfo(
            current_dir="/tmp/foo", git_worktree="main", worktree_name="",
            repo_owner="u", repo_name="n",
        ),
        context_window=ContextWindowInfo(
            used_percentage=42.0, context_window_size=200000,
            total_input_tokens=12345, total_output_tokens=678,
            current_usage=None,
        ),
        thinking=ThinkingInfo(enabled=False),
        vim=VimInfo(mode=""),
        effort=EffortInfo(level=""),
        raw_present=True,
    )
    base.update(overrides)
    return Context(**base)


def test_row1_includes_model_and_dir():
    ctx = make_ctx()
    out = row1(ctx)
    assert "Claude 4.6 Sonnet" in out
    assert "main" in out
    assert "/tmp/foo" in out


def test_row1_handles_missing_git_info():
    ctx = make_ctx(workspace=WorkspaceInfo(
        current_dir="/tmp", git_worktree="", worktree_name="",
        repo_owner="", repo_name="",
    ))
    out = row1(ctx)
    # Should not crash; should still contain the directory
    assert "/tmp" in out


def test_row1_uses_sparkles_icon():
    """Pin the row-1 model-prefix icon: ✨ (sparkles).

    See docs/superpowers/specs/2026-06-12-row1-sparkles-icon-design.md.
    The icon and its trailing space sit between two ANSI sequences as
    a contiguous block, so `"✨ " in out` is a valid substring check.
    """
    ctx = make_ctx()
    out = row1(ctx)
    assert "✨ " in out, f"row1 should lead with sparkles emoji: {out!r}"
    assert "◆" not in out, f"row1 still contains old diamond glyph: {out!r}"


def test_row2_includes_all_four_sections():
    ctx = make_ctx()
    rot = TipRotation(idx=0, last_epoch=0)
    out = row2(ctx, rot, ai_tip="", state_tags=[])
    assert "CTX" in out
    assert "CACHE" in out
    assert "TOK" in out
    assert "TIP" in out


def test_row2_tok_uses_session_cumulative_not_model_max():
    """D-class regression: model_max=1M should NOT be displayed; session
    cumulative (12.3k) should be."""
    ctx = make_ctx(context_window=ContextWindowInfo(
        used_percentage=10.0,
        context_window_size=1_000_000,   # model max — DO NOT USE
        total_input_tokens=11_000,        # session — USE THIS
        total_output_tokens=1_300,
        current_usage=None,
    ))
    rot = TipRotation(idx=0, last_epoch=0)
    out = row2(ctx, rot, ai_tip="", state_tags=[])
    assert "1.0M" not in out, f"TOK leaked model max into output: {out!r}"
    assert "12.3k" in out or "11.0k" in out or "13.0k" in out


def test_row2_tok_uses_sigma_for_total():
    """Pin the row-2 TOK total-prefix design: Σ (sum sigma), not /.

    See docs/superpowers/specs/2026-06-12-row2-polish-design.md.
    Σ is the conventional math symbol for sum; the previous '/' was
    ambiguous between 'per', 'of', and 'slash command'. The total
    here is 12345 + 678 = 13023, which _fmt_tokens formats as '13.0k'.
    """
    ctx = make_ctx(context_window=ContextWindowInfo(
        used_percentage=10.0,
        context_window_size=200000,
        total_input_tokens=12345,
        total_output_tokens=678,
        current_usage=None,
    ))
    rot = TipRotation(idx=0, last_epoch=0)
    out = row2(ctx, rot, ai_tip="", state_tags=[])
    assert "Σ13.0k" in out, f"TOK total should be prefixed with Σ: {out!r}"


def test_row3_includes_progress_bar():
    ctx = make_ctx(context_window=ContextWindowInfo(
        used_percentage=50.0, context_window_size=200000,
        total_input_tokens=0, total_output_tokens=0, current_usage=None,
    ))
    out = row3(ctx)
    assert "50%" in out
    assert "▰" in out or "▱" in out  # progress bar chars


def test_row2_handles_unknown_ctx_pct():
    ctx = make_ctx(context_window=ContextWindowInfo(
        used_percentage=-1.0, context_window_size=0,
        total_input_tokens=0, total_output_tokens=0, current_usage=None,
    ))
    rot = TipRotation(idx=0, last_epoch=0)
    out = row2(ctx, rot, ai_tip="", state_tags=[])
    assert "CTX" in out
    assert "--" in out  # placeholder for unknown


def test_row2_uses_emoji_icons():
    """Pin the row-2 leading-icon design: brain / bolt / cycle / thought.

    See docs/superpowers/specs/2026-06-12-row2-emoji-icons-design.md
    and docs/superpowers/specs/2026-06-12-row2-polish-design.md.
    The ANSI-color wrapper does not split the icon and label, so plain
    substring checks suffice without _strip_ansi.
    """
    ctx = make_ctx()
    rot = TipRotation(idx=0, last_epoch=0)
    out = row2(ctx, rot, ai_tip="", state_tags=[])
    assert "🧠 CTX" in out, f"CTX should lead with brain emoji: {out!r}"
    assert "⚡ CACHE" in out, f"CACHE should lead with bolt: {out!r}"
    assert "🔁 TOK" in out, f"TOK should lead with cycle emoji: {out!r}"
    assert "💭 TIP" in out, f"TIP should lead with thought-balloon emoji: {out!r}"


# ── Usage integration with row1 ──────────────────────────────────────

def _make_usage_info() -> UsageInfo:
    return UsageInfo(
        five_hour=UsageWindow(used_pct=27.0, resets_in_seconds=5280, projected_pct=42.0),
        seven_day=UsageWindow(used_pct=79.0, resets_in_seconds=41280, projected_pct=88.0),
        raw_present=True,
    )


def _strip_ansi(s: str) -> str:
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def test_row1_includes_usage_fields_when_present():
    ctx = make_ctx()
    out = _strip_ansi(row1(ctx, usage=_make_usage_info()))
    assert "5h[" in out, f"row1 missing 5h segment: {out!r}"
    assert "7d[" in out, f"row1 missing 7d segment: {out!r}"
    # Sanity: 27% and 79% formatted
    assert "27%" in out
    assert "79%" in out


def test_row1_omits_usage_when_no_data():
    ctx = make_ctx()
    out = _strip_ansi(row1(ctx, usage=None))
    assert "5h" not in out, f"row1 should not contain 5h when usage is None: {out!r}"
    assert "7d" not in out, f"row1 should not contain 7d when usage is None: {out!r}"


def test_row1_omits_usage_when_both_windows_none():
    ctx = make_ctx()
    usage_empty = UsageInfo(
        five_hour=None, seven_day=None, raw_present=False,
    )
    out = _strip_ansi(row1(ctx, usage=usage_empty))
    # Both windows None → row1 looks exactly like before
    assert "5h" not in out
    assert "7d" not in out
    # But the base content is still there
    assert "Claude 4.6 Sonnet" in out
    assert "main" in out
