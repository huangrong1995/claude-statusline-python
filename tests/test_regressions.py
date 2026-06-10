"""Regression tests for the 4 bug classes that motivated this rewrite.

Each test corresponds to a real bug observed in the bash statusline.
These tests MUST stay green forever.
"""
import ast
import io
import json
import pathlib
import sys
import time

import pytest

from statusline.parse import (
    Context, ModelInfo, WorkspaceInfo, ContextWindowInfo, UsageInfo,
    ThinkingInfo, VimInfo, EffortInfo,
)
from statusline import main as main_mod
from statusline.main import main
from statusline.state import TipRotation


# ── Bug A: hardcoded literal in priority branch ─────────────────────────

def test_bug_A_no_priority_branch_returns_string_literal():
    """A-class structural defense: priority decision functions must
    return TipPool enum, not string literals. AST-walk tips.py."""
    tree = ast.parse(pathlib.Path("statusline/tips.py").read_text())
    priority_funcs = {"_select_pool"}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in priority_funcs:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Constant):
                    if isinstance(sub.value.value, str):
                        pytest.fail(
                            f"tips.py:{sub.lineno}: priority function "
                            f"{node.name}() returns string literal "
                            f"{sub.value.value!r} — must return TipPool enum"
                        )


def test_bug_A_thinking_pool_uses_rot_idx():
    """The Thinking pool was the original culprit (8 hardcoded messages
    bypassed rot_idx). Verify the new code uses rot_idx for it."""
    from statusline.tips import _render_pool, TipPool, _POOL_TABLE
    ctx = Context(
        model=ModelInfo(display_name="x", id="y"),
        workspace=WorkspaceInfo(
            current_dir="/tmp", git_worktree="", worktree_name="",
            repo_owner="", repo_name="",
        ),
        context_window=ContextWindowInfo(
            used_percentage=0, context_window_size=200000,
            total_input_tokens=0, total_output_tokens=0, current_usage=None,
        ),
        thinking=ThinkingInfo(enabled=True),
        vim=VimInfo(mode=""),
        effort=EffortInfo(level=""),
        raw_present=True,
    )
    seen = set()
    for idx in range(0, 8):
        rot = TipRotation(idx=idx, last_epoch=0)
        result = _render_pool(TipPool.THINKING, ctx, rot)
        seen.add(result.text)
    assert len(seen) >= 8, "THINKING pool should yield 8 distinct tips over 8 idx values"


# ── Bug B: silent state file write ──────────────────────────────────────

def test_bug_B_persist_touches_file_every_call(tmp_state_dir):
    """Even when rot doesn't advance, file mtime must update on every persist."""
    from statusline import state
    state.STATE_DIR.mkdir(parents=True, exist_ok=True)
    state.TIP_ROTATE_FILE = tmp_state_dir / ".tip_rotate"
    rot = TipRotation(idx=0, last_epoch=0)
    state.persist_rotation(rot)
    mtime1 = state.TIP_ROTATE_FILE.stat().st_mtime
    time.sleep(0.05)
    state.persist_rotation(rot)
    mtime2 = state.TIP_ROTATE_FILE.stat().st_mtime
    assert mtime2 > mtime1


# ── Bug C: set -e equivalent (unhandled raise) ──────────────────────────

def test_bug_C_main_never_raises_on_garbage_input(monkeypatch, capsys):
    """Even with truly bizarre input, main() must return 0 and print 3 lines."""
    garbage_inputs = [
        "not json {{{",
        "",
        "\x00\x01\x02",
        "[" * 1000,
        "null",
        "true",
        "123",
        '{"unterminated":',
    ]
    for garbage in garbage_inputs:
        monkeypatch.setattr(sys, "stdin", io.StringIO(garbage))
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0, f"main() returned {rc} for input {garbage!r}"
        assert out.count("\n") == 3, f"main() produced wrong line count for {garbage!r}: {out!r}"


def test_bug_C_main_handles_corrupt_state_file(tmp_state_dir, monkeypatch, capsys):
    """B-class + C-class combined: corrupt state must not abort main()."""
    from statusline import state
    state.STATE_DIR.mkdir(parents=True, exist_ok=True)
    state.TIP_ROTATE_FILE = tmp_state_dir / ".tip_rotate"
    state.TIP_ROTATE_FILE.write_text("totally not json")
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"model":{"display_name":"x"},"workspace":{"current_dir":"/tmp"}}'))
    rc = main()
    out = capsys.readouterr().out
    assert rc == 0
    assert out.count("\n") == 3


# ── Bug D: wrong field read (TOK used model max) ────────────────────────

def test_bug_D_tok_uses_session_cumulative_not_model_max():
    """When context_window_size=1M (model max, NOT what we want) and
    total_input_tokens=11k (session cumulative, the correct source),
    TOK must show ~12k, NOT 1.0M."""
    from statusline.render import row2
    ctx = Context(
        model=ModelInfo(display_name="x", id="y"),
        workspace=WorkspaceInfo(
            current_dir="/tmp", git_worktree="", worktree_name="",
            repo_owner="", repo_name="",
        ),
        context_window=ContextWindowInfo(
            used_percentage=10.0,
            context_window_size=1_000_000,   # model max — MUST NOT use
            total_input_tokens=11_000,        # session — MUST use
            total_output_tokens=1_300,
            current_usage=None,
        ),
        thinking=ThinkingInfo(enabled=False),
        vim=VimInfo(mode=""),
        effort=EffortInfo(level=""),
        raw_present=True,
    )
    rot = TipRotation(idx=0, last_epoch=0)
    out = row2(ctx, rot)
    assert "1.0M" not in out, f"TOK leaked model max: {out!r}"
    # Should show 11.0k or 12.3k or similar
    assert any(s in out for s in ("11.0k", "12.3k", "13.0k")), f"TOK missing session total: {out!r}"
