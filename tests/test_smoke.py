"""End-to-end smoke test using a real-world Claude Code statusline JSON."""
import json
import pathlib

import pytest

from statusline.main import main as run_main
from statusline.parse import parse
from statusline.render import row1, row2, row3


FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "sample.json"


def test_fixture_loads_and_parses():
    raw = FIXTURE.read_text()
    ctx = parse(raw)
    assert ctx.raw_present is True
    assert ctx.model.display_name == "Claude 4.6 Sonnet"
    assert ctx.workspace.current_dir == "/home/user/projects/example"
    assert ctx.workspace.git_worktree == "main"
    assert ctx.context_window.used_percentage == 42.5
    assert ctx.context_window.total_input_tokens == 12345


def test_full_render_with_fixture():
    """Smoke: parse + render all 3 rows with the real fixture."""
    raw = FIXTURE.read_text()
    ctx = parse(raw)
    from statusline.state import TipRotation
    rot = TipRotation(idx=0, last_epoch=0)
    out1 = row1(ctx)
    out2 = row2(ctx, rot, state_tags=[], elapsed=0)
    out3 = row3(ctx)
    assert "Claude 4.6 Sonnet" in out1
    assert "main" in out1
    assert "CTX" in out2
    assert "TOK" in out2
    assert "TIP" in out2
    # fixture: input=1500, cache_read=12000, cache_creation=100, window=200000
    # → (1500+12000+100)/200000 ≈ 6.8% (CTX real % is "input+cache", not upstream input-only)
    assert "7%" in out3 or "6%" in out3  # rounding


def test_no_color_mode_produces_no_ansi():
    """Run the statusline in a subprocess with NO_COLOR=1 and verify no ANSI
    escapes leak into stdout. Subprocess isolation prevents module-reload
    side effects from corrupting global state for other tests."""
    import subprocess
    import sys as _sys

    raw = FIXTURE.read_text()
    env = {**_sys.modules["os"].environ, "NO_COLOR": "1"}
    # Strip our own PYTHONPATH manipulation; let the installed package be used.
    result = subprocess.run(
        [_sys.executable, "-m", "statusline"],
        input=raw,
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "\033[" not in result.stdout
    # The 3-line contract still holds
    assert result.stdout.count("\n") == 3
