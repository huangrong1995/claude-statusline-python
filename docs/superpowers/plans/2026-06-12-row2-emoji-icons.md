# Row 2 Emoji Icon Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace three of the four row-2 leading icons in the Python statusline with emoji (🧠 for CTX, 🔁 for TOK, 💡 for TIP); the CACHE icon (⚡) is already correct and stays unchanged.

**Architecture:** The four icons are string literals inside four small functions in `statusline/render.py` (`_row2_ctx`, `_row2_cache`, `_row2_tok`, `_row2_tip`). The change is purely cosmetic — no new data, no new state, no new config. We pin the new icons with a test first (TDD), then make the substitutions, then update the README's example rendering so docs match reality.

**Tech Stack:** Python 3.10+ stdlib, pytest. No new dependencies.

**Spec reference:** `docs/superpowers/specs/2026-06-12-row2-emoji-icons-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `statusline/render.py` | Modify (3 string literals) | Emit row 2 with new icons |
| `tests/test_render.py` | Modify (1 new test) | Pin the new icon literals against regression |
| `README.md` | Modify (1 line) | Sample rendering must match real output |

No new files. No file splits. No structural changes.

---

## Task 1: Pin new icons with a failing test

**Files:**
- Modify: `tests/test_render.py` (append a new test after `test_row2_includes_all_four_sections`)

- [ ] **Step 1: Append failing test**

Add this test at the end of the existing CTX/CACHE/TOK/TIP block in `tests/test_render.py` (after `test_row2_handles_unknown_ctx_pct`, before the `# ── Usage integration with row1 ──` separator on line 100):

```python
def test_row2_uses_emoji_icons():
    """Pin the row-2 leading-icon design: brain / bolt / cycle / lightbulb.

    See docs/superpowers/specs/2026-06-12-row2-emoji-icons-design.md.
    The ANSI-color wrapper does not split the icon and label, so plain
    substring checks suffice without _strip_ansi.
    """
    ctx = make_ctx()
    rot = TipRotation(idx=0, last_epoch=0)
    out = row2(ctx, rot, ai_tip="", state_tags=[])
    assert "🧠 CTX" in out, f"CTX should lead with brain emoji: {out!r}"
    assert "⚡ CACHE" in out, f"CACHE should lead with bolt: {out!r}"
    assert "🔁 TOK" in out, f"TOK should lead with cycle emoji: {out!r}"
    assert "💡 TIP" in out, f"TIP should lead with lightbulb emoji: {out!r}"
```

- [ ] **Step 2: Run the new test to verify it fails**

Run: `pytest tests/test_render.py::test_row2_uses_emoji_icons -v`

Expected: **FAIL** — the assertion for `"🧠 CTX"` (or whichever runs first) fails because `render.py` currently emits `◑ CTX`, `↕ TOK`, `✦ TIP`. The `⚡ CACHE` assertion would pass on its own but the test fails on the first missing icon.

Sample expected output line:
```
AssertionError: CTX should lead with brain emoji: '...◑ CTX...'
```

If the test passes (which it should not), stop and re-check the assertions — the icons in `render.py` may have been edited out of order.

---

## Task 2: Make the test pass — substitute the icons in render.py

**Files:**
- Modify: `statusline/render.py:81` (CTX icon)
- Modify: `statusline/render.py:104` (TOK icon)
- Modify: `statusline/render.py:119` (TIP icon)
- (CACHE on line 89 already uses `⚡` — no edit needed.)

- [ ] **Step 1: Swap the CTX icon**

In `statusline/render.py`, locate `_row2_ctx` (around line 79). The current line 81 reads:

```python
    label = colorize("◑ CTX", CLR_DIM)
```

Change it to:

```python
    label = colorize("🧠 CTX", CLR_DIM)
```

- [ ] **Step 2: Swap the TOK icon**

In `statusline/render.py`, locate `_row2_tok` (around line 100). The current line 104 reads:

```python
    label = colorize("↕ TOK", CLR_DIM)
```

Change it to:

```python
    label = colorize("🔁 TOK", CLR_DIM)
```

- [ ] **Step 3: Swap the TIP icon**

In `statusline/render.py`, locate `_row2_tip` (around line 118). The current line 119 reads:

```python
    label = colorize("✦ TIP", CLR_DIM)
```

Change it to:

```python
    label = colorize("💡 TIP", CLR_DIM)
```

- [ ] **Step 4: Confirm CACHE icon was left alone**

In `statusline/render.py`, locate `_row2_cache` (around line 87). Verify line 89 is still:

```python
    label = colorize("⚡ CACHE", CLR_DIM)
```

If it differs, restore it — the spec explicitly preserves the bolt.

- [ ] **Step 5: Run the new test to verify it passes**

Run: `pytest tests/test_render.py::test_row2_uses_emoji_icons -v`

Expected: **PASS**. The output shows `1 passed`.

- [ ] **Step 6: Run the full render-test file to catch collateral breakage**

Run: `pytest tests/test_render.py -v`

Expected: **all tests PASS**. In particular, `test_row2_includes_all_four_sections` and `test_row2_tok_uses_session_cumulative_not_model_max` should still pass because they assert on label *words* (`CTX`, `CACHE`, `TOK`, `TIP`) and on the formatted token value, not on the leading icon characters.

If anything fails, read the failure carefully — almost certainly a typo in one of the three substitutions above.

- [ ] **Step 7: Run the entire test suite**

Run: `pytest -v`

Expected: **all 75 (now 76) tests PASS**. No test in this repo pins the OLD icon literals (verified during brainstorming with `grep -n "◑\|⚡\|↕\|✦" tests/*.py` → 0 matches), so the only test that should be affected is the new one we just added.

- [ ] **Step 8: Commit the code change together with its test**

```bash
git add tests/test_render.py statusline/render.py
git commit -m "feat(render): modernize row 2 icons (🧠/⚡/🔁/💡)

Replace CTX ◑→🧠, TOK ↕→🔁, TIP ✦→💡. CACHE ⚡ kept — already
the strongest possible 'fast retrieval' symbol. New test in
tests/test_render.py pins the four leading icons against future
drift.

Spec: docs/superpowers/specs/2026-06-12-row2-emoji-icons-design.md

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Sync the README example to match real output

**Files:**
- Modify: `README.md:8` (the sample rendering at the top)

- [ ] **Step 1: Edit the sample rendering**

In `README.md`, line 8 currently reads:

```
◑ CTX 43%  |  ⚡ CACHE 92%  |  ↕ TOK ↑12.3k ↓200 /13.0k  |  ✦ TIP /plan the next refactor
```

Change it to:

```
🧠 CTX 43%  |  ⚡ CACHE 92%  |  🔁 TOK ↑12.3k ↓200 /13.0k  |  💡 TIP /plan the next refactor
```

The surrounding lines (line 7 `◆ Claude 4.6 Sonnet…` and line 9 `▰▰▰…`) are unchanged — only row 2 needs updating.

- [ ] **Step 2: Run the README-rendered smoke check by hand**

Generate a fresh row 2 from the real code and diff it against the README:

```bash
python3 -c "
from statusline.parse import (
    Context, ModelInfo, WorkspaceInfo, ContextWindowInfo,
    ThinkingInfo, VimInfo, EffortInfo,
)
from statusline.state import TipRotation
from statusline.render import row2
import re

ctx = Context(
    model=ModelInfo(display_name='Claude 4.6 Sonnet', id='x'),
    workspace=WorkspaceInfo(
        current_dir='/tmp/foo', git_worktree='main', worktree_name='',
        repo_owner='u', repo_name='n',
    ),
    context_window=ContextWindowInfo(
        used_percentage=43.0, context_window_size=200000,
        total_input_tokens=12345, total_output_tokens=678,
        current_usage=None,
    ),
    thinking=ThinkingInfo(enabled=False),
    vim=VimInfo(mode=''),
    effort=EffortInfo(level=''),
    raw_present=True,
)
out = row2(ctx, TipRotation(idx=0, last_epoch=0), ai_tip='', state_tags=[])
print(re.sub(r'\x1b\[[0-9;]*m', '', out))
"
```

Expected: a line that begins with `🧠 CTX 43%` and contains `⚡ CACHE`, `🔁 TOK`, `💡 TIP` in that order, separated by ` | `. The exact TIP text varies (rotates from the pool); CTX/CACHE/TOK should match the README's `43%` / `--` / `↑12.3k` content shape.

If the README's sample uses a TIP string that no longer appears in the pool, that's pre-existing and out of scope for this plan.

- [ ] **Step 3: Commit the README sync**

```bash
git add README.md
git commit -m "docs(readme): sync row 2 sample to new emoji icons

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: End-to-end visual verification

**Files:** none modified.

- [ ] **Step 1: Run the in-repo end-to-end smoke**

Run: `pytest tests/test_smoke.py tests/test_main.py -v`

Expected: **all PASS**. These two files invoke the statusline end-to-end via subprocess + the sample fixture. They check structural invariants (3 lines, no crash, NO_COLOR honored) — none of them pin icon literals, so they should pass without changes.

- [ ] **Step 2: Visually inspect a real-fixture render**

Run:

```bash
python3 -m statusline < tests/fixtures/sample.json
```

Expected output: three lines. Line 2 must begin with `🧠 CTX` (followed by a percentage) and must contain ` ⚡ CACHE `, ` 🔁 TOK `, ` 💡 TIP ` as ` | `-separated segments.

If the emoji render as boxes in your terminal, the implementation is still correct — the terminal lacks an emoji font. This is the trade-off captured in the spec.

- [ ] **Step 3: Confirm branch state is ready to merge**

Run:

```bash
git log --oneline master..HEAD
git status
```

Expected: three commits on `row2-emoji-icons` (spec + impl + readme), clean working tree.

Sample output:
```
abc1234 docs(readme): sync row 2 sample to new emoji icons
def5678 feat(render): modernize row 2 icons (🧠/⚡/🔁/💡)
b24c9cd docs: row 2 emoji icon redesign spec
nothing to commit, working tree clean
```

The branch is now ready for the `finishing-a-development-branch` skill (merge / PR / cleanup decision) — but that hand-off is out of scope for this plan and is the user's choice.

---

## Self-Review

**1. Spec coverage:**
- ✅ Brain (CTX) → Task 2 Step 1
- ✅ Bolt (CACHE) → Task 2 Step 4 (explicit no-op verification)
- ✅ Cycle (TOK) → Task 2 Step 2
- ✅ Lightbulb (TIP) → Task 2 Step 3
- ✅ README.md line 8 update → Task 3
- ✅ Verification: pytest passes + smoke + visual → Task 2 Steps 6-7, Task 4
- ✅ Rollback (git revert) → covered by per-task commit granularity; not an action step

**2. Placeholder scan:** no TBD/TODO/"appropriate error handling" — every step has the literal new text and exact pytest commands. Pass.

**3. Type consistency:** the test (Task 1) uses identifiers (`make_ctx`, `TipRotation`, `row2`) that already exist in `tests/test_render.py:1-12`; no new symbols introduced. Pass.

**4. Ambiguity:** "around line 81" / "around line 100" / "around line 119" — line numbers may drift if the file is edited concurrently, but each location is also pinned by its surrounding function name (`_row2_ctx`, `_row2_tok`, `_row2_tip`) and by the exact old line being shown verbatim. The engineer cannot confuse which line to change. Pass.
