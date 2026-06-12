# Row 2 Polish — TOK total separator + TIP icon harmonization

**Date:** 2026-06-12
**Scope:** Two small, related cleanups on row 2 of the statusline:
1. Replace the ambiguous `/` prefix on the TOK total with `Σ` (sum sigma).
2. Replace the `💡` TIP icon with `💭` (thought balloon) so it stops
   clashing with `⚡` on color and with `🧠 / ⚡ / 🔁` on register.
3. Clean up two collateral inline-emoji uses inside the GENERIC tip pool
   that would otherwise visually collide with the new row-2 labels.
**Status:** Approved for implementation.

## Motivation

Two reports from real usage of the row-2 emoji redesign:

1. **TOK is hard to read.** The current format `🔁 TOK ↑225.2k ↓1.0k /226.2k`
   has three problems compounded:
   - The total (`226.2k`) is what actually matters — it determines
     context-window pressure — but it is rendered in the *dimmest*
     style. The bright headline number is just the input.
   - The `/` prefix on the total is ambiguous. It reads as "per" or
     "of" rather than "sum of". On a row that includes TIP text full
     of slash commands (`/plan`, `/review`, …), `/` is doubly noisy.
   - Total is mathematically equal to in + out, but the relationship
     is not made explicit by the punctuation.

2. **`💡` does not harmonize with `🧠 / ⚡ / 🔁`.** Two failures:
   - **Color collision.** `💡` and `⚡` are both vibrant yellow.
     Two yellow icons in a four-slot row unbalance the palette.
   - **Register mismatch.** `🧠 / ⚡ / 🔁` are all "abstract concepts
     or processes" (working memory, energy, cyclic flow). `💡` is a
     "depicted physical object" (a literal lightbulb). The other three
     are verb-like; `💡` is noun-like.

`💭` (thought balloon) resolves both: white/light color breaks the yellow
cluster, and "a thought" is an abstract concept matching the register of
its row-mates. `Σ` (Greek capital sigma, the conventional math symbol for
sum) makes the total's relationship to in + out unambiguous.

## Design

### Before

```
🧠 CTX 42%  |  ⚡ CACHE 99%  |  🔁 TOK ↑225.2k ↓1.0k /226.2k  |  💡 TIP …
```

### After

```
🧠 CTX 42%  |  ⚡ CACHE 99%  |  🔁 TOK ↑225.2k ↓1.0k Σ226.2k  |  💭 TIP …
```

### Glyph / format table

| Slot              | Old              | New              | Codepoint              | Status  |
|-------------------|------------------|------------------|------------------------|---------|
| TOK total prefix  | `/`              | `Σ`              | U+03A3 GREEK CAPITAL SIGMA | Changed |
| TIP icon          | `💡`             | `💭`             | U+1F4AD THOUGHT BALLOON | Changed |
| CTX icon          | `🧠`             | `🧠`             | unchanged              | Untouched |
| CACHE icon        | `⚡`             | `⚡`             | unchanged              | Untouched |
| TOK icon          | `🔁`             | `🔁`             | unchanged              | Untouched |
| TOK `↑in ↓out` formatting and color hierarchy | unchanged | — | — | Untouched |

### Collateral cleanup in the GENERIC tip pool

After the TIP-icon swap, two existing tips in `statusline/tips.py`
contain *leading inline emojis* that visually collide with the new
row-2 layout:

| File:line | Before | After | Reason |
|-----------|--------|-------|--------|
| `statusline/tips.py:99`  | `"💡 /brainstorming before non-trivial features"` | `"/brainstorming before non-trivial features"` | The inline `💡` was redundant when the TIP label was also `💡`; with `💡 → 💭` it now reads as a stray lightbulb next to the new thought-balloon label. |
| `statusline/tips.py:105` | `"⚡ /dispatching-parallel-agents fan out independent tasks"` | `"/dispatching-parallel-agents fan out independent tasks"` | The inline `⚡` reproduces the row's CACHE icon, creating two `⚡` on the same row whenever this tip is selected. |

The other nine inline-emoji-prefixed tips in the GENERIC pool
(🐛, ✅, 🔍, 📋, 🌿, 📌, 🤖, 🎨, ♻️) are **left intact** — none collides
with the new row-2 set, and they serve as visual category markers.
The pool's existing tests do not pin specific tip text (only pool
selection and rotation variation), so removing two leading emojis is a
safe edit.

## Rationale

- **`Σ` over `/`:** `Σ` (sigma) is the conventional math notation for
  sum. Anyone who has read mathematical notation understands
  `Σ226.2k = ↑225.2k + ↓1.0k` at a glance. `/` had no such convention.
  `Σ` is a single-cell text character that takes `CLR_DIM` ANSI color
  cleanly — no emoji-color override.
- **`💭` over `💡`:** Thought balloon is the conventional emoji for
  "a thought / something in mind" (used in Apple/Notion/many UIs for
  "draft / hint / suggestion"). Renders white/light in every emoji
  font, distinct from yellow `⚡`. Same cell width (2) as `💡`, so
  row layout is unchanged.
- **Visual hierarchy is fixed without changing color logic:** we keep
  the existing `↑in` = bright, `↓out` = dim, total = dim coloring. The
  total stays dim because in `_fmt_tokens` semantics it is *derived*
  data; the bright + dim split correctly says "input is the volume you
  caused, output is what was returned, total is the sum." Replacing `/`
  with `Σ` resolves the ambiguity without re-shuffling colors.

## Trade-offs we are accepting

- **`Σ` requires a Greek-letter glyph in the terminal font.** This is
  available in every modern monospace font (DejaVu, JetBrains Mono,
  Fira Code, SF Mono, Cascadia, etc.). Legacy terminals lacking it
  would show a fallback box, identical to how `/` would show in a
  font missing the slash (effectively never).
- **`💭` is double-width like `💡` was.** No row-width change.
- **Two GENERIC tips lose their inline emoji.** They become slightly
  less visually distinctive when rotated in, but they still carry
  their slash command and full description. The TIP label icon itself
  remains for the category cue.

## Affected files

| File                          | Change                                                                                                |
|-------------------------------|-------------------------------------------------------------------------------------------------------|
| `statusline/render.py:114`    | TOK total format string: `f'/{total_fmt}'` → `f'Σ{total_fmt}'`                                        |
| `statusline/render.py:119`    | TIP icon: `"💡 TIP"` → `"💭 TIP"`                                                                       |
| `statusline/tips.py:99`       | Remove leading `"💡 "` from the brainstorming tip                                                       |
| `statusline/tips.py:105`      | Remove leading `"⚡ "` from the dispatching-parallel-agents tip                                          |
| `tests/test_render.py`        | (1) Update existing `test_row2_uses_emoji_icons`: change `"💡 TIP"` → `"💭 TIP"` and docstring "lightbulb" → "thought". (2) Add new `test_row2_tok_uses_sigma_for_total` pinning `"Σ"` before the total. |
| `README.md:8`                 | Sample rendering: `/13.0k` → `Σ13.0k` AND `💡 TIP` → `💭 TIP` (one line, two glyph changes)            |

Verified via `grep`:
- `💡` exists ONLY at `render.py:119`, `tests/test_render.py:126`,
  `tips.py:99`, and `README.md:8` — all in scope.
- `/{total_fmt}` exists ONLY at `render.py:114` (also in scope).
- No test in `tests/test_tips.py` pins the text of the two tips being
  edited (`grep -n "brainstorming\|dispatching-parallel" tests/` →
  zero matches in tip-text assertions).

## Out of scope

- The other nine inline-emoji tips in the GENERIC pool (no collision).
- Row 1 (`✨`, `📁`, `⎇`) — unchanged.
- Row 2 CTX / CACHE / TOK icons (`🧠`, `⚡`, `🔁`) — unchanged.
- Row 3 progress bar — unchanged.
- `_fmt_tokens` number formatting (decimal-k notation, rounding rule)
  is unchanged. Only the *prefix character* on the total changes.
- TOK color hierarchy (`↑in` bright, `↓out` and total dim) is
  unchanged. The earlier brainstorming considered re-ranking colors;
  we explicitly chose the minimal-change option.

## Verification

1. **New pin test** in `tests/test_render.py` asserts `"Σ"` appears
   directly before the total in `row2()` output AND that `"💭 TIP"`
   is present (the existing `test_row2_uses_emoji_icons` covers the
   TIP swap once its assertion is updated).
2. **Full suite** passes: `pytest -v`. No existing test asserts on
   `/` as a TOK-total prefix or on `💡` outside the to-be-updated
   assertion.
3. **Live render**: `python3 -m statusline < tests/fixtures/sample.json`
   shows `Σ` before the total on row 2's TOK segment and `💭 TIP`
   leading the TIP segment.

## Rollback

The implementation lands as two commits (matching prior pattern in
this branch):
1. Code + tests + tips.py cleanups together (one commit).
2. README sync (separate commit).

Rollback = `git revert` of the two commits in reverse order. No
state-file migration, no config surface. The four affected source/test
files all rollback cleanly.
