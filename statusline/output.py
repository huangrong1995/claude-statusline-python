"""ANSI color codes and string utilities.

NO_COLOR respected: when the env var is set, all color codes are empty.
"""
from __future__ import annotations
import os


def _esc(code: str) -> str:
    return f"\033[{code}m"


if not os.environ.get("NO_COLOR"):
    CLR_DIM = _esc("38;2;139;149;167")
    CLR_TEXT = _esc("38;2;216;222;233")
    CLR_ACCENT = _esc("38;2;232;197;165")
    CLR_SUCCESS = _esc("38;2;82;209;143")
    CLR_WARN = _esc("38;2;232;197;165")
    CLR_DANGER = _esc("38;2;240;113;120")
    CLR_PROGRESS = _esc("38;2;111;140;255")
else:
    CLR_DIM = ""
    CLR_TEXT = ""
    CLR_ACCENT = ""
    CLR_SUCCESS = ""
    CLR_WARN = ""
    CLR_DANGER = ""
    CLR_PROGRESS = ""

CLR_RESET = _esc("0") if not os.environ.get("NO_COLOR") else ""


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{CLR_RESET}"


def truncate(s: str, max_len: int = 40) -> str:
    if len(s) <= max_len:
        return s
    keep = (max_len - 1) // 2
    return f"{s[:keep]}…{s[-keep:]}"


def pct_color(pct: float) -> str:
    if pct > 75.0:
        return CLR_DANGER
    if pct > 50.0:
        return CLR_WARN
    return CLR_SUCCESS
