"""JSON → typed Context.

D-class bug defense: this is the ONLY module that touches the JSON. All field
reads go through frozen dataclasses so a typo is a NameError at import time,
not a silent wrong value at render time.
"""
from __future__ import annotations
import json
from dataclasses import dataclass


def _dict(d) -> dict:
    """Return d if it's a dict, else empty dict. Used to safely traverse
    subobjects in the statusline JSON without ever raising."""
    return d if isinstance(d, dict) else {}


@dataclass(frozen=True, slots=True)
class ModelInfo:
    display_name: str
    id: str


@dataclass(frozen=True, slots=True)
class WorkspaceInfo:
    current_dir: str
    git_worktree: str
    worktree_name: str
    repo_owner: str
    repo_name: str


@dataclass(frozen=True, slots=True)
class UsageInfo:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int


@dataclass(frozen=True, slots=True)
class ContextWindowInfo:
    used_percentage: float       # -1.0 if unknown
    context_window_size: int     # model max (informational only)
    total_input_tokens: int      # session cumulative — what TOK total should use
    total_output_tokens: int     # session cumulative
    current_usage: UsageInfo | None


@dataclass(frozen=True, slots=True)
class ThinkingInfo:
    enabled: bool


@dataclass(frozen=True, slots=True)
class VimInfo:
    mode: str  # "" if absent


@dataclass(frozen=True, slots=True)
class EffortInfo:
    level: str  # "" if absent


@dataclass(frozen=True, slots=True)
class Context:
    """Immutable parsed view of Claude Code statusline JSON.
    Never raises on parse failure; bad input returns safe defaults."""
    model: ModelInfo
    workspace: WorkspaceInfo
    context_window: ContextWindowInfo
    thinking: ThinkingInfo
    vim: VimInfo
    effort: EffortInfo
    raw_present: bool


def _empty_context() -> Context:
    return Context(
        model=ModelInfo(display_name="", id=""),
        workspace=WorkspaceInfo(
            current_dir="", git_worktree="", worktree_name="",
            repo_owner="", repo_name="",
        ),
        context_window=ContextWindowInfo(
            used_percentage=-1.0,
            context_window_size=0,
            total_input_tokens=0,
            total_output_tokens=0,
            current_usage=None,
        ),
        thinking=ThinkingInfo(enabled=False),
        vim=VimInfo(mode=""),
        effort=EffortInfo(level=""),
        raw_present=False,
    )


def _usage_from(d) -> UsageInfo | None:
    d = _dict(d)
    if not d:
        return None
    return UsageInfo(
        input_tokens=int(d.get("input_tokens") or 0),
        output_tokens=int(d.get("output_tokens") or 0),
        cache_read_input_tokens=int(d.get("cache_read_input_tokens") or 0),
        cache_creation_input_tokens=int(d.get("cache_creation_input_tokens") or 0),
    )


def parse(json_str: str) -> Context:
    """Parse Claude Code statusline JSON into a typed Context.

    Never raises. Garbage input returns _empty_context() with raw_present=False.
    """
    if not json_str or not json_str.strip():
        return _empty_context()
    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, ValueError, RecursionError, MemoryError):
        return _empty_context()
    if not isinstance(data, dict):
        return _empty_context()

    model = _dict(data.get("model"))
    workspace = _dict(data.get("workspace"))
    repo = _dict(workspace.get("repo"))
    cw = _dict(data.get("context_window"))
    thinking = _dict(data.get("thinking"))
    vim = _dict(data.get("vim"))
    effort = _dict(data.get("effort"))

    return Context(
        model=ModelInfo(
            display_name=str(model.get("display_name") or ""),
            id=str(model.get("id") or ""),
        ),
        workspace=WorkspaceInfo(
            current_dir=str(workspace.get("current_dir") or ""),
            git_worktree=str(workspace.get("git_worktree") or ""),
            worktree_name=str(_dict(data.get("worktree")).get("name") or ""),
            repo_owner=str(repo.get("owner") or ""),
            repo_name=str(repo.get("name") or ""),
        ),
        context_window=ContextWindowInfo(
            used_percentage=float(cw.get("used_percentage") if cw.get("used_percentage") is not None else -1.0),
            context_window_size=int(cw.get("context_window_size") or 0),
            total_input_tokens=int(cw.get("total_input_tokens") or 0),
            total_output_tokens=int(cw.get("total_output_tokens") or 0),
            current_usage=_usage_from(cw.get("current_usage")),
        ),
        thinking=ThinkingInfo(enabled=bool(thinking.get("enabled", False))),
        vim=VimInfo(mode=str(vim.get("mode") or "")),
        effort=EffortInfo(level=str(effort.get("level") or "")),
        raw_present=True,
    )
