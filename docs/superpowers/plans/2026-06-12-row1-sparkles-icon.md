# Row 1 Sparkles Icon Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the row-1 model-prefix icon `◆` with `✨` (sparkles), so the icon that introduces the model name carries the modern industry-standard "AI" meaning.

**Architecture:** Row 1 is assembled in a single f-string inside `row1()` in `statusline/render.py` (line 72). The icon is one literal character inside that string. The change is purely cosmetic — no new data, no state, no config. We pin the new icon with a test first (TDD), then swap the literal, then update the README example so the docs match.

**Tech Stack:** Python 3.10+ stdlib, pytest. No new dependencies.

**Spec reference:** `docs/superpowers/specs/2026-06-12-row1-sparkles-icon-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `statusline/render.py` | Modify (1 character in 1 line) | Emit row 1 with the new icon |
| `tests/test_render.py` | Modify (1 new test) | Pin the new icon literal against regression |
| `README.md`            | Modify (1 line) | Sample rendering must match real output |

No new files. No file splits. No structural changes. The row-2 redesign that just landed used exactly this same shape; this plan mirrors it for row 1.

---

## Task 1: Pin new icon with a failing test

**Files:**
- Modify: `tests/test_render.py` (append a new test next to the other `row1` tests, immediately after `test_row1_handles_missing_git_info`)

- [ ] **Step 1: Append failing test**

Add this test to `tests/test_render.py` immediately after `test_row1_handles_missing_git_info` (currently ending around line 50) and BEFORE `test_row2_includes_all_four_sections` (around line 53). It reuses the existing `make_ctx()` helper and the already-imported `row1`.

```python
def test_row1_uses_sparkles_icon():
    """Pin the row-1 model-prefix icon: ✨ (sparkles).

    See docs/superpowers/specs/2026-06-12-row1-sparkles-icon-design.md.
    The icon and its trailing space sit between two ANSI sequences as
    a contiguous block, so `"✨ " in out` is a valid substring check.
    """
    ctx = make_ctx()
    out = row1(ctx)
    assert "✨ " in out, f"row1 should lead with sparkles emoji: {out!r}"
    assert "◆" not in out, f"row1 still contains old diamond glyph: {out!r}"
```

- [ ] **Step 2: Run the new test to verify it fails**

Run: `pytest tests/test_render.py::test_row1_uses_sparkles_icon -v`

Expected: **FAIL** — `render.py:72` currently emits `◆`. The first assertion (`"✨ " in out`) fails with an AssertionError because the output contains `◆ ` instead of `✨ `.

Sample expected output:
```
AssertionError: row1 should lead with sparkles emoji: '\x1b[...m◆ \x1b[0m...'
```

If the test passes (which it should not), stop and re-check the assertions — `render.py` may have already been edited out of order.

---

## Task 2: Make the test pass — substitute the icon in render.py

**Files:**
- Modify: `statusline/render.py:72` (the only icon swap)

- [ ] **Step 1: Swap the model-prefix icon**

In `statusline/render.py`, locate `row1()` (around line 67). The current line 72 reads:

```python
    base = f"{CLR_ACCENT}◆ {CLR_RESET}{model}{sep}{CLR_DIM}📁 {CLR_RESET}{directory}{sep}{git}"
```

Change it to:

```python
    base = f"{CLR_ACCENT}✨ {CLR_RESET}{model}{sep}{CLR_DIM}📁 {CLR_RESET}{directory}{sep}{git}"
```

Only the `◆` immediately after `{CLR_ACCENT}` changes. The directory icon `📁`, the `CLR_ACCENT` color wrapper, the spacing, the separators, the rest of the f-string — all unchanged.

- [ ] **Step 2: Confirm the directory icon was left alone**

Verify the same line still contains `{CLR_DIM}📁 {CLR_RESET}{directory}`. If you accidentally edited the folder emoji, restore it — the spec explicitly preserves it.

- [ ] **Step 3: Run the new test to verify it passes**

Run: `pytest tests/test_render.py::test_row1_uses_sparkles_icon -v`

Expected: **PASS**. Output shows `1 passed`.

- [ ] **Step 4: Run the full render-test file to catch collateral breakage**

Run: `pytest tests/test_render.py -v`

Expected: **all tests PASS**. In particular:
- `test_row1_includes_model_and_dir` should still pass — it asserts on `"Claude 4.6 Sonnet"`, `"main"`, and `"/tmp/foo"`, not on the leading icon.
- `test_row1_handles_missing_git_info` should still pass for the same reason.
- The row-2 emoji-icon test that already exists must continue to pass — we are not touching row 2.

If anything fails, read the failure carefully — almost certainly a typo in the substitution above.

- [ ] **Step 5: Run the entire test suite**

Run: `pytest -v`

Expected: **all tests PASS**. The row-2 redesign added one new test (`test_row2_uses_emoji_icons`), so the suite should be at 95 tests total after this task adds `test_row1_uses_sparkles_icon`. No test in this repo pins `◆` (verified during brainstorming with `grep -rn "◆" tests/` → 0 matches), so the only test that should be affected by this commit is the new one.

- [ ] **Step 6: Commit the code change together with its test**

```bash
git add tests/test_render.py statusline/render.py
git commit -m "feat(render): swap row 1 model icon ◆ → ✨

Replace the diamond prefix on row 1 with the sparkles emoji — the
modern industry-standard 'AI' glyph (Apple Intelligence, Notion AI,
ChatGPT, Gemini, Anthropic). The CLR_ACCENT color wrapper is kept
in place as a no-op for color emoji and as forward compatibility if
the icon is ever reverted to a text glyph.

New test in tests/test_render.py pins '✨ ' in row1() output and
asserts the old '◆' glyph no longer appears.

Spec: docs/superpowers/specs/2026-06-12-row1-sparkles-icon-design.md

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Sync the README example to match real output

**Files:**
- Modify: `README.md:7` (the first line of the sample rendering at the top)

- [ ] **Step 1: Edit the sample rendering**

In `README.md`, line 7 currently reads:

```
◆ Claude 4.6 Sonnet  |  📁 ~/projects/example  |  ⎇ main
```

Change it to:

```
✨ Claude 4.6 Sonnet  |  📁 ~/projects/example  |  ⎇ main
```

Lines 8 (`🧠 CTX 43% | …`) and 9 (`▰▰▰…`) are unchanged — only line 7 needs updating.

- [ ] **Step 2: Verify only line 7 changed**

Run: `git diff README.md`

Expected: exactly one hunk — `-` line 7 with `◆`, `+` line 7 with `✨`. No other changes anywhere in the file.

- [ ] **Step 3: Confirm no other ◆ remains in the README**

Run: `grep -n '◆' README.md`

Expected: no matches (empty output, exit code 1 from grep). If any `◆` remains, find and replace it — the spec requires the README to show no stale icons.

- [ ] **Step 4: Run the README-rendered smoke check by hand**

Generate a fresh row 1 from the real code and visually compare to the new README line:

```bash
python3 -c "
from statusline.parse import (
    Context, ModelInfo, WorkspaceInfo, ContextWindowInfo,
    ThinkingInfo, VimInfo, EffortInfo,
)
from statusline.render import row1
import re

ctx = Context(
    model=ModelInfo(display_name='Claude 4.6 Sonnet', id='x'),
    workspace=WorkspaceInfo(
        current_dir='~/projects/example', git_worktree='main', worktree_name='',
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
out = row1(ctx)
print(re.sub(r'\x1b\\[[0-9;]*m', '', out))
"
```

Expected: a line that begins with `✨ Claude 4.6 Sonnet` and contains ` | 📁 ~/projects/example | ⎇ main`. The exact separator spacing is from `render.py`'s `sep` and matches the README pattern (` | `).

- [ ] **Step 5: Commit the README sync**

```bash
git add README.md
git commit -m "docs(readme): sync row 1 sample to sparkles icon

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: End-to-end visual verification

**Files:** none modified.

- [ ] **Step 1: Run the in-repo end-to-end smoke**

Run: `pytest tests/test_smoke.py tests/test_main.py -v`

Expected: **all PASS**. These two files invoke the statusline end-to-end via subprocess + the sample fixture. They check structural invariants (3 lines, no crash, NO_COLOR honored) — none pin icon literals, so they should pass without changes.

- [ ] **Step 2: Visually inspect a real-fixture render**

Run:

```bash
python3 -m statusline < tests/fixtures/sample.json
```

Expected output: three lines. **Line 1 must begin with `✨ ` followed by the model name.** Line 2 still shows the row-2 emoji icons (`🧠 CTX … ⚡ CACHE … 🔁 TOK … 💡 TIP …`) from the prior redesign. Line 3 is the progress bar.

If the emoji renders as a box in your terminal, the implementation is still correct — the terminal lacks an emoji font. This is the trade-off captured in the spec.

- [ ] **Step 3: Confirm branch state is ready to merge**

Run:

```bash
git log --oneline master..HEAD
git status
```

Expected: seven commits on `row2-emoji-icons` (four from the row-2 work + the row-1 spec + impl + readme), clean working tree.

Sample output:
```
ghi8901 docs(readme): sync row 1 sample to sparkles icon
def4567 feat(render): swap row 1 model icon ◆ → ✨
5abb567 docs: row 1 sparkles icon redesign spec
958de2f docs(readme): sync row 2 sample to new emoji icons
861b165 feat(render): modernize row 2 icons (🧠/⚡/🔁/💡)
84a1fbd docs(plan): row 2 emoji icon redesign implementation plan
b24c9cd docs: row 2 emoji icon redesign spec
nothing to commit, working tree clean
```

The branch is now ready for the `finishing-a-development-branch` skill (merge / PR / cleanup decision) — but that hand-off is out of scope for this plan and is the user's choice.

---

## Self-Review

**1. Spec coverage:**
- ✅ Replace `◆` with `✨` on row 1 → Task 2 Step 1
- ✅ Directory `📁` unchanged → Task 2 Step 2 (explicit confirmation)
- ✅ Git glyph `⎇` unchanged → not in scope of any task; the f-string section `{git}` is untouched
- ✅ Color wrapper `CLR_ACCENT` preserved → Task 2 Step 1 (kept verbatim in the new line)
- ✅ README.md line 7 update → Task 3
- ✅ Pin test added → Task 1 + Task 2 Step 3
- ✅ Verification: pytest + smoke + visual → Task 2 Steps 4-5, Task 4
- ✅ Rollback path (two `git revert`s) → covered by the per-task commit grouping (Task 2 = test+impl commit, Task 3 = README commit)

**2. Placeholder scan:** no TBD / TODO / "appropriate error handling" / "etc.". Every step has the literal new text and exact pytest commands. Pass.

**3. Type consistency:** the new test (Task 1) uses identifiers (`make_ctx`, `row1`) that already exist in `tests/test_render.py:1-12`; no new symbols introduced. The commit message in Task 2 uses the spec path `docs/superpowers/specs/2026-06-12-row1-sparkles-icon-design.md`, which matches the committed spec file. Pass.

**4. Ambiguity:** "around line 72" is supplemented by showing the verbatim line so the engineer can't confuse which line to change. The test placement in Task 1 ("immediately after `test_row1_handles_missing_git_info` and BEFORE `test_row2_includes_all_four_sections`") is pinned by surrounding-symbol-name, not just line number. Pass.
