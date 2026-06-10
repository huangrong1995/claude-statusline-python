"""output.py unit tests."""
import os

import pytest

from statusline import output
from statusline.output import (
    CLR_DIM, CLR_TEXT, CLR_ACCENT, CLR_SUCCESS, CLR_WARN,
    CLR_DANGER, CLR_PROGRESS, CLR_RESET, colorize, truncate,
)


def test_colorize_wraps_with_ansi():
    result = colorize("hello", CLR_ACCENT)
    assert "hello" in result
    assert CLR_ACCENT in result
    assert CLR_RESET in result


def test_colorize_no_color_when_no_color_env(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    # Force re-evaluation of the color constants
    import importlib
    importlib.reload(output)
    from statusline.output import colorize as c2
    result = c2("hello", output.CLR_ACCENT)
    # Either no ANSI or the value is empty after reload
    assert "\033[" not in result or output.CLR_ACCENT == ""
    # Restore
    monkeypatch.delenv("NO_COLOR", raising=False)
    importlib.reload(output)


def test_truncate_short_string_unchanged():
    assert truncate("hello", 10) == "hello"


def test_truncate_long_string_uses_ellipsis():
    result = truncate("a" * 50, 10)
    assert "…" in result
    assert len(result) <= 11  # 10 + ellipsis


def test_truncate_exact_length_unchanged():
    assert truncate("hello", 5) == "hello"


def test_truncate_default_max():
    """Default max is 40 (matches the old _sl_truncate behavior)."""
    s = "a" * 50
    result = truncate(s)
    assert "…" in result


def test_pct_color_high_is_danger():
    from statusline.output import pct_color
    assert pct_color(90.0) == CLR_DANGER


def test_pct_color_medium_is_warn():
    from statusline.output import pct_color
    assert pct_color(60.0) == CLR_WARN


def test_pct_color_low_is_success():
    from statusline.output import pct_color
    assert pct_color(30.0) == CLR_SUCCESS
