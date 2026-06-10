"""render.py unit tests — 3-row assembly."""
import pytest

from statusline.parse import (
    Context, ModelInfo, WorkspaceInfo, ContextWindowInfo, UsageInfo,
    ThinkingInfo, VimInfo, EffortInfo,
)
from statusline.state import TipRotation
from statusline.tips import TipPool
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
