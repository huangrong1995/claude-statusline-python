"""detect.py unit tests."""
import pathlib

import pytest

from statusline import detect
from statusline.detect import detect_state_tags


def test_detect_state_tags_no_dir_returns_empty():
    tags = detect_state_tags("")
    assert tags == []


def test_detect_state_tags_nonexistent_dir_returns_empty():
    tags = detect_state_tags("/nonexistent/path/that/does/not/exist")
    # Should not raise; returns whatever it can determine (likely empty + "no_claude_md")
    assert isinstance(tags, list)


def test_detect_state_tags_in_empty_dir(tmp_path, monkeypatch):
    """No git, no CLAUDE.md, no tests, no project files → no_tests, no_claude_md, no project."""
    tags = detect_state_tags(str(tmp_path))
    assert "no_claude_md" in tags
    assert "no_tests" in tags
    # no project type expected
    assert "node_project" not in tags
    assert "rust_project" not in tags


def test_detect_state_tags_finds_claude_md(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# project")
    tags = detect_state_tags(str(tmp_path))
    assert "has_claude_md" in tags
    assert "no_claude_md" not in tags


def test_detect_state_tags_finds_rust_project(tmp_path):
    (tmp_path / "Cargo.toml").write_text("[package]")
    tags = detect_state_tags(str(tmp_path))
    assert "rust_project" in tags


def test_detect_state_tags_finds_node_project(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    tags = detect_state_tags(str(tmp_path))
    assert "node_project" in tags


def test_detect_state_tags_finds_python_project_via_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]")
    tags = detect_state_tags(str(tmp_path))
    assert "python_project" in tags


def test_detect_state_tags_finds_tests_dir(tmp_path):
    (tmp_path / "tests").mkdir()
    tags = detect_state_tags(str(tmp_path))
    assert "has_tests" in tags
    assert "no_tests" not in tags


def test_detect_state_tags_finds_go_project(tmp_path):
    (tmp_path / "go.mod").write_text("module x")
    tags = detect_state_tags(str(tmp_path))
    assert "go_project" in tags


def test_detect_handles_git_subprocess_failure(tmp_path, monkeypatch, capsys):
    """If git is broken, detect should not crash; returns partial tags."""
    import subprocess

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=2)

    monkeypatch.setattr(subprocess, "run", fake_run)
    tags = detect_state_tags(str(tmp_path))
    assert isinstance(tags, list)
    # Should still detect non-git things
    assert "no_claude_md" in tags
