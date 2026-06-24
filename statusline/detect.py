"""State detection: git status, CLAUDE.md, project type, test presence.

C-class defense: subprocess calls use timeout=2, check=False, capture_output=True
and never raise. Detection failures return partial results.
"""
from __future__ import annotations
import os
import pathlib
import shutil
import subprocess


def _expand_home(path: str) -> str:
    if path.startswith("~"):
        return str(pathlib.Path.home()) + path[1:]
    return path


def _run_git(dir: str, *args: str) -> str:
    """Run git with timeout. Returns stdout or empty string on failure.
    Never raises."""
    try:
        result = subprocess.run(
            ["git", "-C", dir, *args],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        return result.stdout if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def _is_git_repo(dir: str) -> bool:
    if pathlib.Path(dir, ".git").exists():
        return True
    return bool(_run_git(dir, "rev-parse", "--git-dir"))


def detect_branch(dir: str) -> str:
    """Return the current git branch for `dir`, or '' on any failure.
    Never raises. Used to display branch instead of repo owner/name."""
    if not dir:
        return ""
    dir = _expand_home(dir)
    if not pathlib.Path(dir).is_dir():
        return ""
    return _run_git(dir, "branch", "--show-current").strip()


def detect_state_tags(dir: str) -> list[str]:
    """Return a list of state tags for the given directory.
    Never raises. Empty list if dir is empty/inaccessible."""
    if not dir:
        return []
    dir = _expand_home(dir)
    if not pathlib.Path(dir).is_dir():
        return []

    tags: list[str] = []

    # Git state
    if _is_git_repo(dir):
        changes_output = _run_git(dir, "status", "--porcelain")
        changes = len([line for line in changes_output.splitlines() if line.strip()])
        if changes > 0:
            tags.append("git_dirty")
            if changes >= 5:
                tags.append("git_dirty_many")
        else:
            tags.append("git_clean")

        unpushed_output = _run_git(dir, "log", "--oneline", "@{u}..")
        if unpushed_output.strip():
            tags.append("git_unpushed")

    # CLAUDE.md
    if pathlib.Path(dir, "CLAUDE.md").is_file():
        tags.append("has_claude_md")
    else:
        tags.append("no_claude_md")

    # Tests
    if (
        pathlib.Path(dir, "tests").is_dir()
        or pathlib.Path(dir, "test").is_dir()
        or pathlib.Path(dir, "__tests__").is_dir()
    ):
        tags.append("has_tests")
    else:
        tags.append("no_tests")

    # Project type
    p = pathlib.Path(dir)
    if (p / "package.json").is_file():
        tags.append("node_project")
    if (p / "Cargo.toml").is_file():
        tags.append("rust_project")
    if (p / "go.mod").is_file():
        tags.append("go_project")
    if (p / "pyproject.toml").is_file() or (p / "setup.py").is_file():
        tags.append("python_project")

    # TODO pressure (optional, only if rg is available)
    rg = shutil.which("rg")
    if rg:
        try:
            result = subprocess.run(
                [rg, "-c", "--no-heading", "-e", "TODO|FIXME|XXX", dir],
                capture_output=True, text=True, timeout=2, check=False,
            )
            if result.returncode == 0:
                todos = len([line for line in result.stdout.splitlines() if line.strip()])
                if todos >= 5:
                    tags.append("many_todos")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    # Composite: has_claude_md + git_clean
    if "has_claude_md" in tags and "git_clean" in tags:
        tags.append("has_claude_md_clean")

    return tags
