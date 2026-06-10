"""State persistence: TipRotation + SessionEpoch.

B-class bug defense:
- TipRotation is frozen; advance() always returns a new instance.
- Atomic writes via tempfile + os.replace; failures log to stderr, never raise.
- schema_version field enables safe future migration (mismatch → reset).
- Every persist() touches the file, not just on 60s expiry.
"""
from __future__ import annotations
import json
import os
import pathlib
import sys
import tempfile
from dataclasses import dataclass, asdict


STATE_DIR = pathlib.Path.home() / ".claude" / "statusline"
TIP_ROTATE_FILE: pathlib.Path = STATE_DIR / ".tip_rotate"
SESSION_START_FILE: pathlib.Path = STATE_DIR / ".session_start"
TIP_ROTATE_INTERVAL = 60
SESSION_MAX_AGE = 12 * 3600
SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class TipRotation:
    idx: int
    last_epoch: int
    schema_version: int = SCHEMA_VERSION

    def advance(self, now: int) -> "TipRotation":
        if now - self.last_epoch >= TIP_ROTATE_INTERVAL:
            return TipRotation(idx=self.idx + 1, last_epoch=now)
        return self


@dataclass(frozen=True, slots=True)
class SessionEpoch:
    start: int

    @classmethod
    def current(cls, now: int) -> "SessionEpoch":
        if not SESSION_START_FILE.exists():
            return cls.reset(now)
        try:
            saved = int(SESSION_START_FILE.read_text().strip())
            if 0 <= (now - saved) <= SESSION_MAX_AGE:
                return cls(start=saved)
        except (ValueError, OSError):
            pass
        return cls.reset(now)

    @staticmethod
    def reset(now: int) -> "SessionEpoch":
        ep = SessionEpoch(start=now)
        _atomic_write(SESSION_START_FILE, str(now))
        return ep

    def elapsed(self, now: int) -> int:
        return now - self.start


def _atomic_write(path: pathlib.Path, content: str) -> None:
    """tempfile + os.replace. Never raises."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=path.parent,
            prefix=path.name + ".",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(content)
            tmp = pathlib.Path(f.name)
        os.replace(tmp, path)
    except OSError as e:
        print(f"statusline: state write failed: {path}: {e}", file=sys.stderr)


def load_rotation() -> TipRotation:
    """Load TipRotation from disk. Missing/corrupt/wrong-schema → default.
    Never raises."""
    if not TIP_ROTATE_FILE.exists():
        return TipRotation(idx=0, last_epoch=0)
    try:
        data = json.loads(TIP_ROTATE_FILE.read_text())
    except (json.JSONDecodeError, ValueError, OSError) as e:
        print(f"statusline: corrupt state file: {TIP_ROTATE_FILE}: {e}", file=sys.stderr)
        return TipRotation(idx=0, last_epoch=0)
    if data.get("schema_version") != SCHEMA_VERSION:
        print(
            f"statusline: schema mismatch in {TIP_ROTATE_FILE}: "
            f"got {data.get('schema_version')}, expected {SCHEMA_VERSION}; resetting",
            file=sys.stderr,
        )
        return TipRotation(idx=0, last_epoch=0)
    return TipRotation(
        idx=int(data.get("idx") or 0),
        last_epoch=int(data.get("last_epoch") or 0),
    )


def persist_rotation(rot: TipRotation) -> None:
    """Write TipRotation to disk atomically. Touches file on every call.
    Never raises."""
    _atomic_write(TIP_ROTATE_FILE, json.dumps(asdict(rot)))
