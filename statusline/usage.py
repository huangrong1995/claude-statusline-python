"""Anthropic usage window loading with on-disk cache fallback.

The statusline is best-effort UI. This module:
- Fetches /v1/organizations/usage on a 300s TTL (5-minute) cache.
- Stale-on-error: if cache is younger than MAX_STALE_AGE (24h) and the fetch
  fails, return the stale cache rather than nothing. Older than that, return
  empty so we never show week-old numbers after an outage.
- Converts the API's 0.0-1.0 utilization fraction to 0.0-100.0 percent at the
  parse boundary (the rest of the module and its callers work in percent).

This is the only module that touches the Anthropic API or the usage cache file.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

from statusline.state import STATE_DIR


CACHE_FILE: pathlib.Path = STATE_DIR / "usage_cache.json"
CACHE_TTL = 300              # seconds — fresh cache window
MAX_STALE_AGE = 86_400       # 24h — beyond this, stale-on-error gives up
API_TIMEOUT = 3              # seconds — bounded fetch
PROJECTION_CAP = 999.0       # never render runaway projections
WINDOW_LENGTHS = {
    "five_hour": 5 * 3600,
    "seven_day": 7 * 24 * 3600,
}
USAGE_ENDPOINT = "https://api.anthropic.com/v1/organizations/usage"


@dataclass(frozen=True, slots=True)
class UsageWindow:
    used_pct: float           # 0.0-100.0 (already converted from API's 0.0-1.0)
    resets_in_seconds: int    # seconds until window resets
    projected_pct: float      # projected % at reset time, capped at 999.0


@dataclass(frozen=True, slots=True)
class UsageInfo:
    five_hour: UsageWindow | None
    seven_day: UsageWindow | None
    raw_present: bool         # False if cache missing AND fetch failed


def _atomic_write_bytes(path: pathlib.Path, content: bytes) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=path.name + ".",
            delete=False,
        ) as f:
            f.write(content)
            tmp = pathlib.Path(f.name)
        os.replace(tmp, path)
    except OSError as e:
        print(f"statusline: usage: write failed: {path}: {e}", file=sys.stderr)


def _format_resets_in(seconds: int) -> str:
    """Format a duration as 1h28m, 47m, 12s depending on magnitude."""
    if seconds < 0:
        seconds = 0
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h{m}m"
    if seconds >= 60:
        m = seconds // 60
        return f"{m}m"
    return f"{seconds}s"


def _is_cache_fresh(path: pathlib.Path, now: float) -> bool:
    if not path.exists():
        return False
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return False
    return (now - mtime) <= CACHE_TTL


def _cache_age(path: pathlib.Path, now: float) -> float | None:
    """Return age in seconds, or None if file is missing/unreadable."""
    if not path.exists():
        return None
    try:
        return now - path.stat().st_mtime
    except OSError:
        return None


def _read_cache(path: pathlib.Path) -> dict | None:
    """Read cache file. Returns None on missing/malformed.

    A cache containing an "error" field is treated as missing (the spec calls
    this out — the key may have been added since the last error).
    """
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError) as e:
        print(f"statusline: usage: corrupt cache: {path}: {e}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        return None
    if "error" in data:
        return None
    return data


def _fetch_api(key: str) -> bytes | None:
    """Call the Anthropic usage endpoint via curl. Returns response body on
    HTTP 2xx, None otherwise. Never raises (subprocess timeout, missing curl,
    or non-zero exit all yield None)."""
    try:
        result = subprocess.run(
            [
                "curl", "-sS",
                "-H", f"x-api-key: {key}",
                "-H", "anthropic-version: 2023-06-01",
                "-w", "\n%{http_code}",
                USAGE_ENDPOINT,
            ],
            capture_output=True,
            timeout=API_TIMEOUT,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        print(f"statusline: usage: fetch failed: {e}", file=sys.stderr)
        return None

    if result.returncode != 0:
        print(
            f"statusline: usage: curl exited {result.returncode}: "
            f"{result.stderr.decode(errors='replace').strip()}",
            file=sys.stderr,
        )
        return None

    raw = result.stdout
    # Last non-empty line is the HTTP status code we asked curl to print.
    parts = raw.rsplit(b"\n", 1)
    if len(parts) != 2:
        return None
    body, status_line = parts
    try:
        status = int(status_line.strip())
    except ValueError:
        return None
    if status != 200:
        print(f"statusline: usage: API returned HTTP {status}", file=sys.stderr)
        return None
    return body


def _parse_response(data: dict, now: float) -> UsageInfo:
    """Convert raw API JSON to UsageInfo. Always returns a fully-populated
    UsageInfo (with None windows for missing fields). Never raises."""
    five_hour = _parse_window(data.get("five_hour"), WINDOW_LENGTHS["five_hour"], now)
    seven_day = _parse_window(data.get("seven_day"), WINDOW_LENGTHS["seven_day"], now)
    return UsageInfo(
        five_hour=five_hour,
        seven_day=seven_day,
        raw_present=True,
    )


def _parse_window(raw, window_length: int, now: float) -> UsageWindow | None:
    """Compute a single UsageWindow from a raw API dict, or None if fields
    are missing/unparseable. Projection is capped at PROJECTION_CAP."""
    if not isinstance(raw, dict):
        return None
    util = raw.get("utilization")
    resets_at = raw.get("resets_at")
    if not isinstance(util, (int, float)) or not isinstance(resets_at, str):
        return None
    # Convert API fraction (0.0-1.0) to percent at the parse boundary.
    used_pct = float(util) * 100.0
    if used_pct < 0:
        used_pct = 0.0
    resets_epoch = _parse_iso8601(resets_at)
    if resets_epoch is None:
        return None
    resets_in = int(round(resets_epoch - now))
    if resets_in < 0:
        resets_in = 0
    elapsed = window_length - resets_in
    if elapsed <= 0:
        projected = used_pct
    else:
        burn_rate = used_pct / elapsed
        projected = used_pct + burn_rate * resets_in
    if projected > PROJECTION_CAP:
        projected = PROJECTION_CAP
    if projected < 0.0:
        projected = 0.0
    return UsageWindow(
        used_pct=used_pct,
        resets_in_seconds=resets_in,
        projected_pct=projected,
    )


def _parse_iso8601(s: str) -> float | None:
    """Parse an ISO-8601 timestamp to epoch seconds. Returns None on failure."""
    if not s:
        return None
    # Accept 'Z' or '+00:00' as UTC.
    cleaned = s.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def load_usage(now: float | None = None) -> UsageInfo:
    """Return current usage info. May fetch from the network.

    Behavior matrix (per spec):
    - cache fresh → read cache, no fetch
    - cache missing/malformed/error → fetch; success → write + return; failure → empty
    - cache stale → fetch; success → write + return; failure → use stale if
      < MAX_STALE_AGE old, else empty
    """
    if now is None:
        now = time.time()

    cache_fresh = _is_cache_fresh(CACHE_FILE, now)
    cached = _read_cache(CACHE_FILE)

    if cache_fresh and cached is not None:
        return _parse_response(cached, now)

    key = os.environ.get("ANTHROPIC_ADMIN_API_KEY", "").strip()
    if not key:
        # No key. Only return cached if we have it AND it's not too old.
        age = _cache_age(CACHE_FILE, now)
        if cached is not None and age is not None and age <= MAX_STALE_AGE:
            return _parse_response(cached, now)
        return UsageInfo(five_hour=None, seven_day=None, raw_present=False)

    body = _fetch_api(key)
    if body is None:
        # Fetch failed. Stale-on-error applies.
        age = _cache_age(CACHE_FILE, now)
        if cached is not None and age is not None and age <= MAX_STALE_AGE:
            print(
                f"statusline: usage: serving stale cache (age={int(age)}s)",
                file=sys.stderr,
            )
            return _parse_response(cached, now)
        return UsageInfo(five_hour=None, seven_day=None, raw_present=False)

    # Fetch succeeded — parse, write, return.
    try:
        data = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"statusline: usage: malformed response: {e}", file=sys.stderr)
        # Don't poison the cache with garbage.
        return UsageInfo(five_hour=None, seven_day=None, raw_present=False)
    if not isinstance(data, dict):
        return UsageInfo(five_hour=None, seven_day=None, raw_present=False)

    _atomic_write_bytes(CACHE_FILE, body)
    return _parse_response(data, now)
