"""parse.py unit tests — covers D-class bug defense (wrong field reads)."""
import json
import pytest

from statusline.parse import (
    parse, Context, ModelInfo, WorkspaceInfo, ContextWindowInfo,
    UsageInfo, ThinkingInfo, VimInfo, EffortInfo,
)


def test_parses_valid_json_to_context():
    raw = json.dumps({
        "model": {"display_name": "Claude 4.6 Sonnet", "id": "claude-sonnet-4-6"},
        "workspace": {
            "current_dir": "/tmp/foo",
            "git_worktree": "main",
            "repo": {"owner": "u", "name": "n"},
        },
        "context_window": {
            "used_percentage": 50.0,
            "context_window_size": 200000,
            "total_input_tokens": 1000,
            "total_output_tokens": 200,
            "current_usage": None,
        },
        "thinking": {"enabled": True},
        "vim": {"mode": "INSERT"},
        "effort": {"level": "high"},
    })
    ctx = parse(raw)
    assert isinstance(ctx, Context)
    assert ctx.raw_present is True
    assert ctx.model.display_name == "Claude 4.6 Sonnet"
    assert ctx.workspace.current_dir == "/tmp/foo"
    assert ctx.workspace.git_worktree == "main"
    assert ctx.context_window.used_percentage == 50.0
    assert ctx.context_window.total_input_tokens == 1000
    assert ctx.context_window.total_output_tokens == 200
    assert ctx.thinking.enabled is True
    assert ctx.vim.mode == "INSERT"
    assert ctx.effort.level == "high"


def test_parses_current_usage_subfields():
    raw = json.dumps({
        "model": {"display_name": "x"},
        "workspace": {"current_dir": "/tmp"},
        "context_window": {
            "used_percentage": 0,
            "current_usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "cache_read_input_tokens": 30,
                "cache_creation_input_tokens": 40,
            },
        },
    })
    ctx = parse(raw)
    usage = ctx.context_window.current_usage
    assert usage is not None
    assert usage.input_tokens == 10
    assert usage.output_tokens == 20
    assert usage.cache_read_input_tokens == 30
    assert usage.cache_creation_input_tokens == 40


def test_garbage_json_returns_safe_default():
    ctx = parse("not json {{{")
    assert ctx.raw_present is False
    assert ctx.model.display_name == ""
    assert ctx.context_window.used_percentage == -1.0
    assert ctx.thinking.enabled is False


def test_empty_string_returns_safe_default():
    ctx = parse("")
    assert ctx.raw_present is False


def test_missing_fields_use_safe_sentinels():
    raw = json.dumps({"model": {"display_name": "x"}})
    ctx = parse(raw)
    assert ctx.workspace.current_dir == ""
    assert ctx.context_window.used_percentage == -1.0
    assert ctx.context_window.total_input_tokens == 0
    assert ctx.context_window.current_usage is None
    assert ctx.thinking.enabled is False
    assert ctx.vim.mode == ""
    assert ctx.effort.level == ""


def test_context_is_frozen():
    """Context must be immutable — accidental mutation would propagate to
    downstream modules and is exactly the kind of state-leak bug we want to
    prevent."""
    from dataclasses import FrozenInstanceError
    raw = json.dumps({"model": {"display_name": "x"}, "workspace": {"current_dir": "/tmp"}})
    ctx = parse(raw)
    with pytest.raises(FrozenInstanceError):
        ctx.model = ModelInfo(display_name="y", id="z")  # type: ignore[misc]


def test_non_dict_subobjects_return_safe_default():
    """parse() must never raise, even when subobjects are non-dict types
    (str, list, int, bool, null, etc.). This is the C-class defense contract."""
    pathological_inputs = [
        {"model": [1, 2, 3]},
        {"model": "string-not-dict"},
        {"workspace": []},
        {"workspace": 42},
        {"worktree": "main"},          # string where dict expected
        {"worktree": []},
        {"worktree": 42},
        {"worktree": True},
        {"vim": [1, 2]},
        {"vim": False},
        {"context_window": "oops"},
        {"thinking": 99},
        {"effort": None},
        {"context_window": {"current_usage": "not a dict"}},
        {"context_window": {"current_usage": [1, 2, 3]}},
        {"context_window": {"current_usage": 0}},  # falsy but type-correct
    ]
    for payload in pathological_inputs:
        raw = json.dumps(payload)
        ctx = parse(raw)
        assert isinstance(ctx, Context), f"parse({payload!r}) did not return Context"
        assert ctx.raw_present is True, f"parse({payload!r}) set raw_present=False but JSON was valid"
        # All other fields should still be at safe defaults
        assert ctx.model.display_name == ""
        assert ctx.workspace.current_dir == ""
        assert ctx.vim.mode == ""
        assert ctx.context_window.used_percentage == -1.0


def test_used_percentage_zero_is_not_treated_as_unknown():
    """The sentinel for unknown is -1.0, NOT 0.0. A real 0% must stay 0.0."""
    raw = json.dumps({
        "model": {"display_name": "x"},
        "workspace": {"current_dir": "/tmp"},
        "context_window": {"used_percentage": 0.0},
    })
    ctx = parse(raw)
    assert ctx.context_window.used_percentage == 0.0
    assert ctx.context_window.used_percentage != -1.0


def test_used_percentage_missing_is_treated_as_unknown():
    """When the field is absent, sentinel -1.0 is used (not 0.0)."""
    raw = json.dumps({
        "model": {"display_name": "x"},
        "workspace": {"current_dir": "/tmp"},
    })
    ctx = parse(raw)
    assert ctx.context_window.used_percentage == -1.0
