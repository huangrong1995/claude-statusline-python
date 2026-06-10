"""usage.py unit tests — cache TTL, fetch paths, parse, projection, formatting."""
import json
import os
import pathlib
import subprocess
import time

import pytest

from statusline import usage
from statusline.usage import (
    UsageInfo, UsageWindow, load_usage, _parse_response,
    format_resets_in,
)


FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "usage_response.json"


def _read_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def _write_cache_file(content: dict | str, mtime: float | None = None) -> pathlib.Path:
    path = usage.CACHE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, dict):
        path.write_text(json.dumps(content), encoding="utf-8")
    else:
        path.write_text(content, encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


# ── 1. Fresh cache → no fetch ──────────────────────────────────────────

def test_load_usage_with_fresh_cache_skips_fetch(tmp_state_dir, monkeypatch):
    """When cache mtime is fresh (< 300s), subprocess.run must NOT be called."""
    fixture_data = _read_fixture()
    _write_cache_file(fixture_data, mtime=time.time() - 60)  # 60s old → fresh

    calls: list[tuple] = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("subprocess.run should not be called when cache is fresh")

    monkeypatch.setattr(usage.subprocess, "run", fake_run)
    monkeypatch.delenv("ANTHROPIC_ADMIN_API_KEY", raising=False)

    info = load_usage()
    assert calls == []
    assert info.raw_present is True
    assert info.five_hour is not None
    assert info.seven_day is not None


# ── 2. Stale cache → fetch triggered ──────────────────────────────────

def test_load_usage_with_stale_cache_triggers_fetch(tmp_state_dir, monkeypatch):
    """When cache mtime > 300s, subprocess.run MUST be called."""
    fixture_data = _read_fixture()
    _write_cache_file(fixture_data, mtime=time.time() - 301)  # 301s old → stale

    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "test-key")

    def fake_run(*args, **kwargs):
        body = json.dumps(fixture_data).encode("utf-8")
        class _R:
            stdout = body + b"\n200"
            stderr = b""
            returncode = 0
        return _R()

    monkeypatch.setattr(usage.subprocess, "run", fake_run)
    info = load_usage()
    assert info.raw_present is True
    assert info.five_hour is not None


# ── 3. No cache → fetch and write ──────────────────────────────────────

def test_load_usage_with_no_cache_fetches_and_writes(tmp_state_dir, monkeypatch):
    """Empty dir → fetch → file exists afterwards."""
    assert not usage.CACHE_FILE.exists()
    fixture_data = _read_fixture()

    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "test-key")

    def fake_run(*args, **kwargs):
        body = json.dumps(fixture_data).encode("utf-8")
        class _R:
            stdout = body + b"\n200"
            stderr = b""
            returncode = 0
        return _R()

    monkeypatch.setattr(usage.subprocess, "run", fake_run)
    info = load_usage()
    assert usage.CACHE_FILE.exists(), "fetch should have written the cache"
    assert info.raw_present is True


# ── 4. No API key → empty ──────────────────────────────────────────────

def test_load_usage_with_no_api_key_returns_empty(tmp_state_dir, monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_ADMIN_API_KEY", raising=False)
    info = load_usage()
    err = capsys.readouterr().err
    assert info.five_hour is None
    assert info.seven_day is None
    assert info.raw_present is False
    assert err == ""


# ── 5. 401 → log + empty ───────────────────────────────────────────────

def test_load_usage_with_401_logs_and_returns_empty(tmp_state_dir, monkeypatch, capsys):
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "bad-key")

    def fake_run(*args, **kwargs):
        class _R:
            stdout = b'{"error":"unauthorized"}\n401'
            stderr = b""
            returncode = 0
        return _R()

    monkeypatch.setattr(usage.subprocess, "run", fake_run)
    info = load_usage()
    err = capsys.readouterr().err
    assert info.five_hour is None
    assert info.seven_day is None
    assert "401" in err or "usage" in err.lower()


# ── 6. Network timeout → empty ─────────────────────────────────────────

def test_load_usage_with_network_timeout_returns_empty(tmp_state_dir, monkeypatch, capsys):
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "test-key")

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="curl", timeout=3)

    monkeypatch.setattr(usage.subprocess, "run", fake_run)
    info = load_usage()
    err = capsys.readouterr().err
    assert info.five_hour is None
    assert info.seven_day is None
    assert "usage" in err.lower() or "timeout" in err.lower()


# ── 7. Malformed cache → treat as missing ──────────────────────────────

def test_load_usage_with_malformed_cache_treats_as_missing(tmp_state_dir, monkeypatch, capsys):
    """Invalid JSON in cache → fetch should be attempted (not crash)."""
    _write_cache_file("not json {{{", mtime=time.time() - 60)

    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "test-key")
    fixture_data = _read_fixture()

    def fake_run(*args, **kwargs):
        body = json.dumps(fixture_data).encode("utf-8")
        class _R:
            stdout = body + b"\n200"
            stderr = b""
            returncode = 0
        return _R()

    monkeypatch.setattr(usage.subprocess, "run", fake_run)
    info = load_usage()
    err = capsys.readouterr().err
    # Either corrupted-cache log appears, or fetch succeeded.
    # The key assertion: no exception was raised and a valid UsageInfo returned.
    assert isinstance(info, UsageInfo)
    assert info.raw_present is True
    assert "corrupt" in err.lower()


# ── 8. Stale cache + failed fetch → use stale ─────────────────────────

def test_load_usage_with_stale_cache_and_failed_fetch_uses_stale(tmp_state_dir, monkeypatch, capsys):
    """600s old cache + fetch failure → return cached data (better than nothing)."""
    fixture_data = _read_fixture()
    _write_cache_file(fixture_data, mtime=time.time() - 600)

    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "test-key")

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="curl", timeout=3)

    monkeypatch.setattr(usage.subprocess, "run", fake_run)
    info = load_usage()
    err = capsys.readouterr().err
    assert info.five_hour is not None
    assert info.seven_day is not None
    assert info.raw_present is True
    assert "stale" in err.lower()


# ── 9. Very old cache + failed fetch → empty ──────────────────────────

def test_load_usage_with_very_old_cache_and_failed_fetch_returns_empty(tmp_state_dir, monkeypatch, capsys):
    """>24h old cache + fetch failure → return empty UsageInfo."""
    fixture_data = _read_fixture()
    # 25h old: well past MAX_STALE_AGE (24h)
    _write_cache_file(fixture_data, mtime=time.time() - (25 * 3600))

    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "test-key")

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="curl", timeout=3)

    monkeypatch.setattr(usage.subprocess, "run", fake_run)
    info = load_usage()
    assert info.five_hour is None
    assert info.seven_day is None
    assert info.raw_present is False


# ── 10. _parse_response computes projection correctly ────────────────

def test_parse_response_computes_projection(tmp_state_dir):
    """Given a fixture with resets_in = 5280s (1h28m) into a 5h window,
    verify projected_pct matches the formula:
        burn_rate = used_pct / elapsed
        projected = used_pct + burn_rate * resets_in
    """
    data = _read_fixture()
    # Pin "now" so we can compute the expected values deterministically.
    # The fixture's five_hour resets_at is 2099-01-01T00:00:00Z.
    from datetime import datetime, timezone
    now = datetime(2099, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp() - 5280  # 1h28m before
    info = _parse_response(data, now=now)

    fh = info.five_hour
    assert fh is not None
    # Window length 18000s, elapsed = 18000 - 5280 = 12720
    elapsed = 5 * 3600 - 5280
    burn_rate = 27.0 / elapsed
    expected = 27.0 + burn_rate * 5280
    assert abs(fh.projected_pct - expected) < 1e-6, (
        f"projection mismatch: got {fh.projected_pct}, expected {expected}"
    )
    assert fh.used_pct == 27.0
    assert fh.resets_in_seconds == 5280


# ── 11. _parse_response handles window just reset ─────────────────────

def test_parse_response_handles_window_just_reset(tmp_state_dir):
    """When elapsed = 0 (window just reset), projected = used_pct."""
    data = {
        "five_hour": {
            "utilization": 0.10,
            "resets_at": "2099-01-01T00:00:00Z",
        }
    }
    # Pick "now" such that the window has just reset:
    # resets_in = 5*3600 → elapsed = 0.
    from datetime import datetime, timezone
    now = datetime(2099, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp() - 5 * 3600
    info = _parse_response(data, now=now)
    fh = info.five_hour
    assert fh is not None
    assert fh.used_pct == 10.0
    # projected = used_pct (no burn-rate scaling when elapsed == 0)
    assert fh.projected_pct == 10.0


# ── 12. _format_resets_in ─────────────────────────────────────────────

def test_format_resets_in_hours_and_minutes():
    assert format_resets_in(5280) == "1h28m"  # 1*3600 + 28*60 = 5280


def test_format_resets_in_minutes_only():
    assert format_resets_in(47 * 60) == "47m"


def test_format_resets_in_seconds_only():
    assert format_resets_in(12) == "12s"


def test_format_resets_in_handles_negative():
    assert format_resets_in(-5) == "0s"
