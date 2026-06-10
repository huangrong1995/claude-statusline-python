"""Adaptive, state-aware tips.

A-class bug defense: priority decisions return TipPool ENUM, never a string
literal. _render_pool() looks up text from _POOL_TABLE. The AST test in
test_tips.py enforces this structurally.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from statusline.parse import Context
from statusline.state import TipRotation


class TipPool(str, Enum):
    CONTEXT_PRESSURE = "context_pressure"
    THINKING = "thinking"
    VIM = "vim"
    LONG_SESSION = "long_session"
    AI = "ai"
    STATE_GIT_DIRTY_MANY = "state:git_dirty_many"
    STATE_GIT_DIRTY = "state:git_dirty"
    STATE_GIT_UNPUSHED = "state:git_unpushed"
    STATE_NO_CLAUDE_MD = "state:no_claude_md"
    STATE_HAS_CLAUDE_MD_CLEAN = "state:has_claude_md_clean"
    STATE_MANY_TODOS = "state:many_todos"
    STATE_NO_TESTS = "state:no_tests"
    GENERIC = "generic"


_POOL_TABLE: dict[TipPool, list[str]] = {
    TipPool.CONTEXT_PRESSURE: [
        "Ctx 60% · plan /compact soon",
        "Ctx 85% · /compact or /clear now",
        "Context high · /compact to free room",
        "Context critical · /clear to reset",
    ],
    TipPool.THINKING: [
        "Thinking on · expect deeper, slower answers",
        "Thinking on · plans before edits",
        "Thinking on · good for /plan and /architect",
        "Thinking on · /clear when it stalls",
        "Thinking on · more tokens per turn",
        "Thinking on · /rewind if a thought went sideways",
        "Thinking on · best with ambiguous tasks",
        "Thinking on · turn off with /effort low for chat",
    ],
    TipPool.VIM: [
        "Vim NORMAL · Esc to leave",
        "Vim INSERT · Esc to leave",
        "Vim VISUAL · Esc to leave",
        "Vim REPLACE · Esc to leave",
        "Vim COMMAND · Esc to leave",
        "Vim · Esc to leave",
    ],
    TipPool.LONG_SESSION: [
        "Long session · # to save what you learned",
        "20m+ in · consider saving insights with #",
        "Long thread · /rewind to compress",
        "Long session · /clear if context feels heavy",
    ],
    TipPool.AI: [
        "(ai-generated tip injected from cache)",
    ],
    TipPool.STATE_GIT_DIRTY_MANY: [
        "/review your pending changes",
        "/security-review before pushing",
        "/simplify cleanup + dedup pass",
        "/commit with a clear message",
        "/plan next steps on this branch",
    ],
    TipPool.STATE_GIT_DIRTY: [
        "/review before committing",
        "/verify your last change works",
        "/simplify the diff before commit",
    ],
    TipPool.STATE_GIT_UNPUSHED: [
        "Unpushed commits · consider /commit or PR",
        "Unpushed · /commit and push when ready",
    ],
    TipPool.STATE_NO_CLAUDE_MD: [
        "No CLAUDE.md · /init to bootstrap one",
        "No CLAUDE.md · /init scaffolds project memory",
    ],
    TipPool.STATE_HAS_CLAUDE_MD_CLEAN: [
        "Clean tree · /plan the next feature",
        "Quiet moment · /deep-research a topic",
        "Clean state · good time for /refactor",
    ],
    TipPool.STATE_MANY_TODOS: [
        "Many TODOs in code · /plan a cleanup sprint",
        "TODO debt · /simplify a focused pass",
    ],
    TipPool.STATE_NO_TESTS: [
        "No tests yet · /test-driven-development first",
        "No tests · add one with /test-driven-development",
    ],
    TipPool.GENERIC: [
        "💡 /brainstorming before non-trivial features",
        "🐛 /systematic-debugging when stuck on a bug",
        "✅ /test-driven-development write the test first",
        "🔍 /verification-before-completion check your work",
        "📋 /writing-plans multi-step? plan it first",
        "🌿 /using-git-worktrees isolate risky work",
        "⚡ /dispatching-parallel-agents fan out independent tasks",
        "/plan enter plan mode for the next change",
        "/review audit your last diff",
        "/security-review catch vulns before merge",
        "/clear start a fresh thread",
        "/compact summarize to free context",
        "📌 # memory persists facts across sessions",
        "🤖 /feature-dev guided feature work",
        "🎨 /frontend-design distinctive UI builds",
        "♻️ /rewind undo turns or messages",
        "Tab accept · Esc to redo",
        "!cmd run shell without leaving",
        "@path attach a file or directory",
        "Shift+Tab cycle permission mode",
        "Ctrl+R reverse-search history",
    ],
}


@dataclass(frozen=True, slots=True)
class TipResult:
    text: str
    pool: TipPool
    is_ai: bool = False


def _select_pool(ctx: Context, state_tags: list[str], elapsed: int) -> TipPool:
    """Decide which pool to use. Returns ENUM, never a string literal."""
    pct = ctx.context_window.used_percentage
    if pct >= 85.0:
        return TipPool.CONTEXT_PRESSURE
    if pct >= 60.0:
        return TipPool.CONTEXT_PRESSURE
    if ctx.thinking.enabled:
        return TipPool.THINKING
    if ctx.vim.mode and ctx.vim.mode != "null":
        return TipPool.VIM
    if elapsed >= 1200:
        return TipPool.LONG_SESSION
    if "git_dirty_many" in state_tags:
        return TipPool.STATE_GIT_DIRTY_MANY
    if "git_dirty" in state_tags:
        return TipPool.STATE_GIT_DIRTY
    if "git_unpushed" in state_tags:
        return TipPool.STATE_GIT_UNPUSHED
    if "no_claude_md" in state_tags:
        return TipPool.STATE_NO_CLAUDE_MD
    if "many_todos" in state_tags:
        return TipPool.STATE_MANY_TODOS
    if "no_tests" in state_tags:
        return TipPool.STATE_NO_TESTS
    if "has_claude_md_clean" in state_tags:
        return TipPool.STATE_HAS_CLAUDE_MD_CLEAN
    return TipPool.GENERIC


def _render_pool(pool: TipPool, ctx: Context, rot: TipRotation) -> TipResult:
    """Look up text from _POOL_TABLE. Every pool's text comes through here."""
    # VIM mode is hard signal: text must reflect the actual mode name.
    if pool == TipPool.VIM and ctx.vim.mode and ctx.vim.mode != "null":
        text = f"Vim {ctx.vim.mode} · Esc to leave"
        return TipResult(text=text, pool=pool)
    table = _POOL_TABLE.get(pool) or _POOL_TABLE[TipPool.GENERIC]
    idx = rot.idx % len(table)
    return TipResult(text=table[idx], pool=pool)


def select_tip(
    ctx: Context,
    rot: TipRotation,
    *,
    state_tags: list[str] | None = None,
    elapsed: int = 0,
    ai_tip: str = "",
) -> TipResult:
    """Choose a tip based on context, state, rotation, and optional AI tip.
    Never raises."""
    tags = state_tags or []

    # AI tip is highest priority if non-empty
    if ai_tip:
        return TipResult(text=ai_tip, pool=TipPool.AI, is_ai=True)

    pool = _select_pool(ctx, tags, elapsed)
    return _render_pool(pool, ctx, rot)
