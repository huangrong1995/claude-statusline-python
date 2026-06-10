"""state.py unit tests — covers B-class bug defense (silent state writes)."""
import json
import pathlib
import time

import pytest

from statusline import state
from statusline.state import (
    TipRotation, SessionEpoch,
    load_rotation, persist_rotation,
)


def test_tip_rotation_advance_increments_after_interval():
    rot = TipRotation(idx=0, last_epoch=1000)
    rot1 = rot.advance(1001)  # 1s later, < 60s
    assert rot1.idx == 0  # not yet
    rot2 = rot1.advance(1061)  # 61s later
    assert rot2.idx == 1


def test_tip_rotation_is_frozen():
    from dataclasses import FrozenInstanceError
    rot = TipRotation(idx=0, last_epoch=1000)
    with pytest.raises(FrozenInstanceError):
        rot.idx = 5  # type: ignore[misc]


def test_persist_writes_file_unconditionally(tmp_state_dir):
    """B-class defense: every persist() must update mtime, not just on 60s."""
    rot = TipRotation(idx=0, last_epoch=1000)
    state.STATE_DIR.mkdir(parents=True, exist_ok=True)
    state.TIP_ROTATE_FILE = tmp_state_dir / ".tip_rotate"

    persist_rotation(rot)
    mtime1 = state.TIP_ROTATE_FILE.stat().st_mtime

    # Same idx, but call again immediately — file should still be touched
    time.sleep(0.05)
    persist_rotation(rot)
    mtime2 = state.TIP_ROTATE_FILE.stat().st_mtime
    assert mtime2 > mtime1, "persist_rotation must touch file on every call"


def test_persist_uses_atomic_rename(tmp_state_dir):
    """No .tmp files should remain after a successful persist."""
    state.STATE_DIR.mkdir(parents=True, exist_ok=True)
    state.TIP_ROTATE_FILE = tmp_state_dir / ".tip_rotate"
    rot = TipRotation(idx=3, last_epoch=2000)
    persist_rotation(rot)

    leftover = list(tmp_state_dir.glob(".tip_rotate.*"))
    assert leftover == [], f"atomic write left temp files: {leftover}"


def test_load_rotation_returns_default_when_file_missing(tmp_state_dir):
    state.TIP_ROTATE_FILE = tmp_state_dir / ".tip_rotate"
    rot = load_rotation()
    assert rot.idx == 0
    assert rot.schema_version == 1


def test_load_rotation_rejects_corrupt_file(tmp_state_dir, capsys):
    state.TIP_ROTATE_FILE = tmp_state_dir / ".tip_rotate"
    state.TIP_ROTATE_FILE.write_text("not json {{{")
    rot = load_rotation()
    assert rot.idx == 0
    err = capsys.readouterr().err
    assert "corrupt" in err.lower() or "statusline" in err


def test_load_rotation_rejects_wrong_schema_version(tmp_state_dir, capsys):
    state.TIP_ROTATE_FILE = tmp_state_dir / ".tip_rotate"
    state.TIP_ROTATE_FILE.write_text(json.dumps({
        "idx": 5, "last_epoch": 1000, "schema_version": 999,
    }))
    rot = load_rotation()
    assert rot.idx == 0  # treated as missing
    err = capsys.readouterr().err
    assert "schema" in err.lower() or "statusline" in err


def test_session_epoch_current_creates_file_if_missing(tmp_state_dir):
    state.SESSION_START_FILE = tmp_state_dir / ".session_start"
    ep = SessionEpoch.current(now=5000)
    assert ep.start == 5000
    assert state.SESSION_START_FILE.exists()


def test_session_epoch_current_resets_on_stale(tmp_state_dir):
    state.SESSION_START_FILE = tmp_state_dir / ".session_start"
    state.SESSION_START_FILE.write_text("1000")  # ancient
    ep = SessionEpoch.current(now=5000 + state.SESSION_MAX_AGE + 100)
    assert ep.start > 5000  # reset to now


def test_session_epoch_current_keeps_fresh_value(tmp_state_dir):
    state.SESSION_START_FILE = tmp_state_dir / ".session_start"
    state.SESSION_START_FILE.write_text("4000")
    ep = SessionEpoch.current(now=5000)
    assert ep.start == 4000


def test_session_epoch_elapsed():
    ep = SessionEpoch(start=1000)
    assert ep.elapsed(now=1060) == 60
