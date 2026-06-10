"""Shared pytest fixtures."""
import json
import pathlib
import pytest


@pytest.fixture
def tmp_state_dir(tmp_path, monkeypatch):
    """Redirect state files to a temporary directory so tests don't
    touch the real ~/.claude/statusline/."""
    import statusline.state as state

    monkeypatch.setattr(state, "STATE_DIR", tmp_path)
    monkeypatch.setattr(state, "TIP_ROTATE_FILE", tmp_path / ".tip_rotate")
    monkeypatch.setattr(state, "SESSION_START_FILE", tmp_path / ".session_start")
    return tmp_path


@pytest.fixture
def sample_statusline_json():
    """Real-world Claude Code statusline JSON sample."""
    return json.dumps({
        "model": {"id": "claude-sonnet-4-6", "display_name": "Claude 4.6 Sonnet"},
        "workspace": {
            "current_dir": "/home/user/projects/example",
            "git_worktree": "main",
            "repo": {"owner": "user", "name": "example"},
        },
        "worktree": {"name": ""},
        "context_window": {
            "used_percentage": 42.5,
            "context_window_size": 200000,
            "total_input_tokens": 12345,
            "total_output_tokens": 678,
            "current_usage": {
                "input_tokens": 1500,
                "output_tokens": 200,
                "cache_read_input_tokens": 12000,
                "cache_creation_input_tokens": 100,
            },
        },
        "thinking": {"enabled": False},
        "vim": {"mode": ""},
        "effort": {"level": ""},
    })
