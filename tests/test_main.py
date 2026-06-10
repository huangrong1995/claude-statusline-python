"""main.py integration tests — C-class defense (never raise, always 3 lines)."""
import io
import json
import sys

import pytest

from statusline import main as main_mod
from statusline.main import main, _read_ai_tip


def test_main_with_valid_json_produces_3_lines(sample_statusline_json, capsys):
    rc = main()
    out = capsys.readouterr().out
    lines = out.rstrip("\n").split("\n")
    assert rc == 0
    assert len(lines) == 3
    # Row 2 should mention key sections
    assert "CTX" in lines[1]
    assert "TOK" in lines[1]
    assert "TIP" in lines[1]


def test_main_with_garbage_json_prints_3_lines(monkeypatch, capsys):
    """C-class defense: garbage input must not crash; must produce 3 lines."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json {{{"))
    rc = main()
    out = capsys.readouterr().out
    lines = out.rstrip("\n").split("\n")
    assert rc == 0
    assert len(lines) == 3


def test_main_with_empty_stdin_prints_3_lines(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    rc = main()
    out = capsys.readouterr().out
    lines = out.rstrip("\n").split("\n")
    assert rc == 0
    assert len(lines) == 3


def test_main_with_state_corruption_still_works(tmp_state_dir, monkeypatch, capsys):
    """B-class: corrupt state file should not abort render."""
    # Write garbage into the state file
    import statusline.state as state
    state.STATE_DIR.mkdir(parents=True, exist_ok=True)
    state.TIP_ROTATE_FILE = tmp_state_dir / ".tip_rotate"
    state.TIP_ROTATE_FILE.write_text("totally not json")

    json_str = json.dumps({
        "model": {"display_name": "x"},
        "workspace": {"current_dir": "/tmp"},
        "context_window": {"used_percentage": 0},
    })
    monkeypatch.setattr(sys, "stdin", io.StringIO(json_str))
    rc = main()
    captured = capsys.readouterr()
    out = captured.out
    err = captured.err
    assert rc == 0
    assert out.count("\n") == 3  # 3 lines, each terminated by \n
    # And a diagnostic was written to stderr
    assert "corrupt" in err.lower() or "statusline" in err.lower()


def test_read_ai_tip_returns_empty_when_no_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(main_mod, "AI_TIP_CACHE", tmp_path / "nonexistent")
    assert _read_ai_tip() == ""


def test_read_ai_tip_returns_text_when_fresh(monkeypatch, tmp_path):
    import time
    cache = tmp_path / "ai_tip_cache"
    cache.write_text("try /plan the next refactor\n2026-06-10T00:00:00Z\nhaiku\n")
    monkeypatch.setattr(main_mod, "AI_TIP_CACHE", cache)
    monkeypatch.setattr(main_mod, "AI_TIP_MAX_AGE", 300)
    assert _read_ai_tip() == "try /plan the next refactor"


def test_read_ai_tip_returns_empty_when_stale(monkeypatch, tmp_path):
    import time
    cache = tmp_path / "ai_tip_cache"
    cache.write_text("stale tip\n")
    # Set mtime to 1 hour ago
    import os
    old_time = time.time() - 3600
    os.utime(cache, (old_time, old_time))
    monkeypatch.setattr(main_mod, "AI_TIP_CACHE", cache)
    monkeypatch.setattr(main_mod, "AI_TIP_MAX_AGE", 300)
    assert _read_ai_tip() == ""
