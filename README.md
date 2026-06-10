# Claude Code Statusline (Python)

Three-row, low-noise statusline with adaptive tips.

## Quick start

```bash
# The entry point is the bash shim at ~/.claude/statusline/statusline.sh
# which exec's `python3 -m statusline`. Claude Code invokes this via
# ~/.claude/settings.json (statusLine.command).

# To run tests:
cd ~/.claude/statusline
pip install -e ".[dev]"
pytest -v
```

## Layout

```
◆ Claude 4.6 Sonnet | 📁 ~/projects/example | ⎇ main
CTX 43% | CACHE 92% | ↕ TOK ↑12.3k ↓200 /13.0k | ✦ TIP /plan the next refactor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 43%
```

## Architecture

The statusline is a Python 3.10+ package with strict module boundaries:

| Module | Responsibility |
|---|---|
| `statusline/parse.py` | JSON → typed `Context` (frozen dataclass) |
| `statusline/state.py` | `TipRotation` + `SessionEpoch`, atomic writes |
| `statusline/tips.py` | 6 priority pools, enum-driven, rot_idx routed |
| `statusline/detect.py` | git / CLAUDE.md / project type (timeout-safe) |
| `statusline/render.py` | 3-row assembly |
| `statusline/output.py` | ANSI color codes + truncation (NO_COLOR-aware) |
| `statusline/main.py` | Orchestrator + catch-all (only stdout writer) |

## Bug-class defenses

This rewrite eliminates four bug classes by structure, not discipline:

- **A-class** (hardcoded literals in priority branches): `tips.py` priority
  decisions return `TipPool` enum; the AST-walk test in
  `tests/test_regressions.py` enforces no `return "<literal>"` in priority
  functions.
- **B-class** (silent state file writes): `TipRotation.advance()` is frozen
  and always returns a new instance; `persist_rotation()` uses
  `tempfile` + `os.replace` and touches the file on every call.
- **C-class** (`set -e` equivalent): `main()` has a catch-all `except
  Exception` that prints 3 blank lines so the user never sees a missing
  statusline.
- **D-class** (wrong field reads): `parse.py` is the single point of JSON
  contact; the dataclass types make field typos a `NameError` at import time.
  The D-class regression test pins the specific `total_input_tokens` field.

## Testing

- `pytest -v` — 73 tests covering unit, regression, invariant, and smoke
- `tests/test_regressions.py` — pins the 4 known bugs forever
- `tests/test_invariants.py` — AST-walks that catch structural regressions

## AI integration (optional)

`ai_tip_daemon.sh` is unchanged from the bash version — it writes tips to
`~/.claude/statusline/ai_tip_cache`, which the Python statusline reads
(fresh for 5 minutes).

See the daemon's plist/systemd install instructions in the git history
(commit `chore: keep ai_tip_daemon.sh`).

## Dependencies

- Runtime: **stdlib only** (any Python 3.10+)
- Dev: `pytest>=7.0`
