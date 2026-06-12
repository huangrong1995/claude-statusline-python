"""tips.py unit tests — covers A-class bug defense (hardcoded literals)."""
import ast
import pathlib

import pytest

from statusline.parse import (
    Context, ModelInfo, WorkspaceInfo, ContextWindowInfo, UsageInfo,
    ThinkingInfo, VimInfo, EffortInfo,
)
from statusline.state import TipRotation
from statusline.tips import (
    TipPool, TipResult, select_tip, _POOL_TABLE, _select_pool, _render_pool,
)


def make_ctx(**overrides) -> Context:
    """Build a Context with sensible defaults for tests."""
    base = dict(
        model=ModelInfo(display_name="x", id="y"),
        workspace=WorkspaceInfo(
            current_dir="/tmp", git_worktree="", worktree_name="",
            repo_owner="", repo_name="",
        ),
        context_window=ContextWindowInfo(
            used_percentage=0.0, context_window_size=200000,
            total_input_tokens=0, total_output_tokens=0, current_usage=None,
        ),
        thinking=ThinkingInfo(enabled=False),
        vim=VimInfo(mode=""),
        effort=EffortInfo(level=""),
        raw_present=True,
    )
    base.update(overrides)
    return Context(**base)


def test_every_tip_pool_has_non_empty_table():
    for pool in TipPool:
        assert pool in _POOL_TABLE, f"TipPool.{pool.name} missing from _POOL_TABLE"
        assert len(_POOL_TABLE[pool]) > 0, f"TipPool.{pool.name} has empty table"


def test_context_pressure_pool_when_ctx_high():
    ctx = make_ctx(
        context_window=ContextWindowInfo(
            used_percentage=90.0, context_window_size=200000,
            total_input_tokens=0, total_output_tokens=0, current_usage=None,
        )
    )
    rot = TipRotation(idx=0, last_epoch=0)
    result = select_tip(ctx, rot)
    assert result.pool == TipPool.CONTEXT_PRESSURE
    assert "/compact" in result.text or "/clear" in result.text


def test_thinking_pool_when_thinking_enabled():
    ctx = make_ctx(thinking=ThinkingInfo(enabled=True))
    rot = TipRotation(idx=0, last_epoch=0)
    result = select_tip(ctx, rot)
    assert result.pool == TipPool.THINKING
    assert "Thinking" in result.text


def test_vim_pool_when_vim_mode_active():
    ctx = make_ctx(vim=VimInfo(mode="INSERT"))
    rot = TipRotation(idx=0, last_epoch=0)
    result = select_tip(ctx, rot)
    assert result.pool == TipPool.VIM
    assert "INSERT" in result.text


def test_generic_pool_is_fallback():
    ctx = make_ctx()
    rot = TipRotation(idx=0, last_epoch=0)
    result = select_tip(ctx, rot)
    assert result.pool == TipPool.GENERIC


def test_rot_idx_advances_through_pool():
    """rot_idx must select a different tip after enough advances."""
    ctx = make_ctx()
    seen = set()
    for idx in range(0, 20):
        rot = TipRotation(idx=idx, last_epoch=0)
        result = select_tip(ctx, rot)
        seen.add(result.text)
    # 20 idx values against a pool of 20+ tips should yield multiple distinct texts
    assert len(seen) > 1, "rot_idx did not produce variation"


def test_select_tip_never_raises_on_partial_context():
    """Even with a weird ctx, select_tip must return a TipResult, not raise."""
    ctx = make_ctx(
        context_window=ContextWindowInfo(
            used_percentage=-1.0, context_window_size=0,
            total_input_tokens=0, total_output_tokens=0, current_usage=None,
        )
    )
    rot = TipRotation(idx=0, last_epoch=0)
    result = select_tip(ctx, rot)
    assert isinstance(result, TipResult)


def test_render_pool_unknown_falls_back_safely():
    """If _POOL_TABLE is somehow wrong, _render_pool must not crash."""
    # Use a real pool to exercise the index logic
    pool = TipPool.GENERIC
    rot = TipRotation(idx=999999, last_epoch=0)  # huge idx
    result = _render_pool(pool, make_ctx(), rot)
    assert isinstance(result, TipResult)
    assert result.text in _POOL_TABLE[pool]


def test_priority_functions_return_enum_not_string():
    """A-class structural defense: _select_pool returns TipPool enum,
    never a string literal. This is the test that enforces no return '<literal>'
    in priority decision code."""
    tree = ast.parse(pathlib.Path("statusline/tips.py").read_text())
    priority_func_names = {"_select_pool"}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in priority_func_names:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Constant):
                    if isinstance(sub.value.value, str):
                        pytest.fail(
                            f"tips.py:{sub.lineno}: priority function "
                            f"{node.name}() returns string literal "
                            f"{sub.value.value!r} — must return TipPool enum"
                        )


def test_generic_pool_no_inline_icons_collide_with_row2_labels():
    """Structural invariant: no GENERIC tip leads with 💡 or ⚡.

    See docs/superpowers/specs/2026-06-12-row2-polish-design.md.
    💡 was the old TIP label; ⚡ is the CACHE label. A GENERIC tip
    that starts with either glyph would visually collide with the
    row-2 row labels when selected. Other category-marker emojis
    (🐛, ✅, 🔍, 📋, 🌿, 📌, 🤖, 🎨, ♻️) are fine — they don't appear
    as row-2 labels.
    """
    for tip in _POOL_TABLE[TipPool.GENERIC]:
        assert not tip.startswith("💡 "), (
            f"GENERIC tip leads with 💡 (old TIP label): {tip!r}"
        )
        assert not tip.startswith("⚡ "), (
            f"GENERIC tip leads with ⚡ (CACHE label): {tip!r}"
        )
