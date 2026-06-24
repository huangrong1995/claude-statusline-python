"""Orchestrator: stdin JSON → 3-line statusline on stdout.

C-class defense: catch-all at the bottom guarantees 3 lines of output for
any input. All exceptions logged to stderr.
"""
from __future__ import annotations
import pathlib
import sys
import time

from statusline import parse, state, detect, render, usage


AI_TIP_CACHE: pathlib.Path = pathlib.Path.home() / ".claude" / "statusline" / "ai_tip_cache"
AI_TIP_MAX_AGE = 300


def _read_ai_tip() -> str:
    """Read AI tip from cache if fresh. Empty string otherwise."""
    if not AI_TIP_CACHE.exists():
        return ""
    try:
        mtime = AI_TIP_CACHE.stat().st_mtime
    except OSError:
        return ""
    if (time.time() - mtime) > AI_TIP_MAX_AGE:
        return ""
    try:
        first_line = AI_TIP_CACHE.read_text(encoding="utf-8").split("\n", 1)[0].strip()
    except OSError:
        return ""
    return first_line


def main() -> int:
    """Entry point. Reads stdin, writes 3 lines to stdout. Never raises."""
    try:
        try:
            json_str = sys.stdin.read()
        except (OSError, UnicodeDecodeError) as e:
            print(f"statusline: stdin read failed: {e}", file=sys.stderr)
            json_str = ""

        ctx = parse.parse(json_str)

        now = int(time.time())
        rot = state.load_rotation()
        # Persist on every call (B-class defense)
        state.persist_rotation(rot)
        # Advance for next call
        next_rot = rot.advance(now)
        if next_rot is not rot:
            state.persist_rotation(next_rot)

        session = state.SessionEpoch.current(now=now)
        elapsed = session.elapsed(now)

        state_tags = detect.detect_state_tags(ctx.workspace.current_dir)
        branch = detect.detect_branch(ctx.workspace.current_dir)
        ai_tip = _read_ai_tip()

        # load_usage() handles all failures internally and returns an empty
        # UsageInfo when the API/cache is unavailable. The main() catch-all
        # below is a backstop.
        usage_info = usage.load_usage()

        line1 = render.row1(ctx, usage=usage_info, branch=branch)
        line2 = render.row2(
            ctx, next_rot,
            ai_tip=ai_tip,
            state_tags=state_tags,
            elapsed=elapsed,
        )
        line3 = render.row3(ctx)

        sys.stdout.write(line1 + "\n" + line2 + "\n" + line3 + "\n")
        sys.stdout.flush()
        return 0

    except Exception as e:
        # Last-resort: never let the user see a blank statusline
        print(f"statusline: fatal: {e}", file=sys.stderr)
        try:
            sys.stdout.write("\n\n\n")
            sys.stdout.flush()
        except OSError:
            pass
        return 1
