# claude-statusline-python

A three-row statusline for [Claude Code](https://docs.anthropic.com/en/docs/claude-code),
rewritten from bash to Python to make four classes of bugs **structurally impossible**.

```
◆ Claude 4.6 Sonnet  |  📁 ~/projects/example  |  ⎇ main
🧠 CTX 43%  |  ⚡ CACHE 92%  |  🔁 TOK ↑12.3k ↓200 /13.0k  |  💡 TIP /plan the next refactor
▰▰▰▰▰▰▰▰▰▰▰▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱ 43%
```

- One typed `Context` dataclass flows through the pipeline; no string parsing after `parse.py`.
- Six priority pools (context pressure, thinking, vim, long session, AI, project state) all
  route through a single rotation index — no hardcoded literals can hijack the tip.
- State files are written via `tempfile` + `os.replace` (POSIX-atomic) on **every** call.
- `main()` has a catch-all that emits three blank lines on any exception — the user never
  sees a missing statusline.
- Zero runtime dependencies. Pure Python 3.10+ stdlib.

## Install

```bash
git clone git@github.com:huangrong1995/claude-statusline-python.git
cd claude-statusline-python
pip install -e ".[dev]"   # only needed for the test suite
```

Then point Claude Code at the entry script in `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "/absolute/path/to/claude-statusline-python/statusline.sh"
  }
}
```

The `statusline.sh` shim is four lines: `cd` into the project, `exec python3 -m statusline`.

## How it works

```
stdin JSON
    │
    ▼
parse.py ─────────► Context (frozen dataclass)
    │
    ▼
state.py ──────────► TipRotation (idx, last_epoch, schema_version)
    │
    ▼
tips.py ───────────► TipResult (text, pool, is_ai)
    │
    ▼
render.py ─────────► Row1, Row2, Row3
    │
    ▼
output.py ─────────► ANSI-colored strings (NO_COLOR-aware)
    │
    ▼
stdout (3 lines)
```

| Module | Does | Touches |
|---|---|---|
| `parse.py`     | JSON → typed `Context`             | JSON |
| `state.py`     | `TipRotation` + `SessionEpoch`     | state files |
| `tips.py`      | priority pool selection + rotation | nothing |
| `detect.py`    | git / CLAUDE.md / project type     | subprocess |
| `render.py`    | 3-row assembly                     | nothing |
| `output.py`    | ANSI codes + truncation            | nothing |
| `main.py`      | orchestrator + catch-all           | stdin + stdout |

`main.py` is the only module that reads stdin or writes stdout. `state.py` is the only
module that touches state files. `detect.py` is the only module that runs subprocesses
(each one with a 2-second timeout).

## The four bug classes — defended by structure

The bash predecessor had four bug classes that kept biting. Each one has a structural
defense in this rewrite:

### A — Hardcoded literals in priority branches

The "TIP" row would get stuck on a single message because a priority branch like
`Thinking` would `echo "<literal>"` and bypass the rotation index.

**Defense:** `tips._select_pool()` returns a `TipPool` enum, never a string. The
text lookup goes through `_POOL_TABLE[pool][rot_idx % len(table)]`. An AST-walk test
in `tests/test_regressions.py` walks `tips.py` and fails on any
`return "<literal>"` in a priority function — preventing regression at code-review time.

### B — Silent state file writes

`.tip_rotate` would only get written when its 60-second cache expired, so the rotation
index would mysteriously not advance.

**Defense:** `TipRotation.advance()` always returns a new instance.
`persist_rotation()` calls `_atomic_write()` (tempfile + `os.replace`) **every call**,
with no caching. mtime advances on every invocation. IO failures are caught and logged
to stderr, never raised.

### C — `set -e` (errexit) aborting the whole statusline

One failing subcommand would blank the entire three rows.

**Defense:** `main()` ends with a catch-all `except Exception` that prints three blank
lines and a diagnostic to stderr, then returns exit code 1. Subprocess calls in
`detect.py` use `subprocess.run(check=False, capture_output=True, timeout=2)`.
A 16-pathological-input test in `tests/test_parse.py` confirms the parser never raises.

### D — Wrong JSON field reads

"TOK" once showed `1.0M` (the model context window size) instead of session-cumulative
token usage, because the bash code read `context_window_size` when it meant
`total_input_tokens + total_output_tokens`.

**Defense:** `parse.py` is the only module that touches JSON. Field names are spelled
out on frozen dataclasses, so a typo is a `NameError` at import time. The D-class
regression test (`test_tok_uses_session_cumulative_not_model_max`) pins the specific
field semantics: given `context_window_size=1_000_000` and
`total_input_tokens=11_000`, the rendered output must contain `11.0k`, never `1.0M`.

## Tests

```bash
pytest -v
```

75 tests across nine files:

| File | Coverage |
|---|---|
| `test_parse.py`        | field mappings + 16-pathological-input safety |
| `test_state.py`        | `advance()` monotonicity; corrupt/missing/schemaversion |
| `test_tips.py`         | six priority branches; rot_idx wrap; pool table coverage |
| `test_detect.py`       | git status mock; CLAUDE.md; project types; rg-absent safety |
| `test_output.py`       | ANSI codes; NO_COLOR; truncation |
| `test_render.py`       | three-row assembly; D-class regression |
| `test_regressions.py`  | pins the 4 known bugs forever |
| `test_invariants.py`   | AST-walk structural checks |
| `test_main.py`         | end-to-end with real-world JSON sample |
| `test_smoke.py`        | subprocess invocation + NO_COLOR end-to-end |

## Layout

```
claude-statusline-python/
├── statusline.sh              # bash shim: exec python3 -m statusline
├── statusline/                # Python package
│   ├── __init__.py
│   ├── __main__.py            # enables `python -m statusline`
│   ├── main.py                # orchestrator + catch-all
│   ├── parse.py               # JSON → typed Context (D-class)
│   ├── state.py               # TipRotation + atomic writes (B-class)
│   ├── tips.py                # 6 priority pools, enum-driven (A-class)
│   ├── detect.py              # git / CLAUDE.md / project type
│   ├── render.py              # 3-row assembly
│   └── output.py              # ANSI codes (NO_COLOR-aware)
├── ai_tip_daemon.sh           # unchanged bash — background AI tip generator
├── tests/                     # pytest suite
│   ├── conftest.py
│   ├── fixtures/sample.json
│   ├── test_parse.py
│   ├── test_state.py
│   ├── test_tips.py
│   ├── test_detect.py
│   ├── test_output.py
│   ├── test_render.py
│   ├── test_regressions.py
│   ├── test_invariants.py
│   ├── test_main.py
│   └── test_smoke.py
├── pyproject.toml
└── README.md
```

## AI tip integration (optional)

`ai_tip_daemon.sh` (preserved verbatim from the bash version) is a background daemon
that fetches context-aware tips from a remote endpoint and writes them to
`ai_tip_cache`. The Python statusline reads that file and treats the tip as fresh for
300 seconds (5 minutes). When the daemon is not running, the statusline falls back to
local tips from the priority pools.

## Dependencies

- **Runtime:** Python 3.10+ stdlib only. No third-party packages.
- **Dev:** `pytest>=7.0`

## Background

This is the second major revision of a statusline I've been iterating on for a while.
The bash version worked, but it kept breaking in the same handful of ways: the rotation
index would stall, the wrong field would get displayed, the tip would get stuck on one
message, the whole line would blank out on a transient git failure. Each fix was a
patch; each patch had a sibling that bit me the next week. The Python rewrite isn't
faster or smaller — it's just structured so those failure modes **cannot recur**.