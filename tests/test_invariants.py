"""Structural invariant tests — keep the codebase's design rules enforced.

These run AST-walks over the source to catch structural regressions
that runtime tests would miss.
"""
import ast
import pathlib

import pytest

from statusline.tips import TipPool, _POOL_TABLE


def test_every_tip_pool_has_non_empty_table():
    for pool in TipPool:
        assert pool in _POOL_TABLE, f"TipPool.{pool.name} missing from _POOL_TABLE"
        assert len(_POOL_TABLE[pool]) > 0, f"TipPool.{pool.name} has empty table"


def test_no_string_literal_return_in_priority_funcs():
    tree = ast.parse(pathlib.Path("statusline/tips.py").read_text())
    priority_funcs = {"_select_pool"}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in priority_funcs:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Constant):
                    if isinstance(sub.value.value, str):
                        pytest.fail(
                            f"tips.py:{sub.lineno}: priority function "
                            f"{node.name}() returns string literal — must return TipPool enum"
                        )


def test_state_dataclasses_have_schema_version():
    """Future migration safety: persisted dataclasses must declare schema_version."""
    import dataclasses
    from statusline import state
    for cls in (state.TipRotation,):
        fields = {f.name for f in dataclasses.fields(cls)}
        assert "schema_version" in fields, f"{cls.__name__} missing schema_version field"


def test_main_catch_all_exists():
    """C-class defense: main() must have a catch-all except clause."""
    tree = ast.parse(pathlib.Path("statusline/main.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            for sub in ast.walk(node):
                if isinstance(sub, ast.ExceptHandler):
                    if sub.type is None or "Exception" in ast.unparse(sub.type):
                        return  # found
            pytest.fail("main() lacks a catch-all `except Exception` block")


def _stdout_prints(tree: ast.AST) -> list[tuple[int, str]]:
    """Return (line, src) for every `print()` call that writes to stdout.

    A call is considered to write to stdout when it has NO `file=` keyword,
    or has `file=sys.stdout`. Calls like `print(..., file=sys.stderr)` are
    diagnostics and are allowed.
    """
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Identify the print() callee by name (handles `print`, `builtins.print`).
        func = node.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name != "print":
            continue
        # Check the `file=` kwarg.
        for kw in node.keywords:
            if kw.arg == "file":
                v = kw.value
                # Allow `file=sys.stderr` (and any non-stdout expression).
                is_stdout = (
                    (isinstance(v, ast.Attribute) and v.attr == "stdout")
                    or (isinstance(v, ast.Name) and v.id == "stdout")
                )
                if is_stdout:
                    findings.append((node.lineno, ast.unparse(node)))
                # Any explicit `file=` other than `sys.stdout` is OK; stop.
                break
        else:
            # No `file=` kwarg → default stdout.
            findings.append((node.lineno, ast.unparse(node)))
    return findings


def test_no_module_writes_to_stdout_except_main():
    """Only main.py may write to stdout (separation of concerns).

    `print(..., file=sys.stderr)` is allowed (diagnostics). `print()` with
    no `file=` arg, or `file=sys.stdout`, is not — except inside main.py.
    """
    pkg = pathlib.Path("statusline")
    for py_file in pkg.glob("*.py"):
        if py_file.name == "main.py":
            continue
        text = py_file.read_text()
        tree = ast.parse(text)
        for lineno, src in _stdout_prints(tree):
            pytest.fail(
                f"{py_file.name}:{lineno} writes to stdout: {src} "
                f"— only main.py may write to stdout (use file=sys.stderr instead)"
            )
