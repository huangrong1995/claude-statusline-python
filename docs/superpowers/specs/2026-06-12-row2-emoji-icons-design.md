# Row 2 Icon Redesign — Emoji Set

**Date:** 2026-06-12
**Scope:** Visual redesign of the four leading icons in row 2 of the statusline.
**Status:** Approved for implementation.

## Motivation

Row 2's current icons (`◑ CTX`, `⚡ CACHE`, `↕ TOK`, `✦ TIP`) are basic
Unicode geometric/symbol glyphs. They read as "1990s symbol font" rather
than a modern terminal aesthetic. We are replacing three of the four with
emoji that carry direct conceptual metaphors (brain, cycle, lightbulb).
The fourth (`⚡` for CACHE) is already the strongest possible symbol for
"fast retrieval" and is kept unchanged.

## Design

### Before

```
◑ CTX 43%  |  ⚡ CACHE 92%  |  ↕ TOK ↑12.3k ↓200 /13.0k  |  ✦ TIP /plan ...
```

### After

```
🧠 CTX 43%  |  ⚡ CACHE 92%  |  🔁 TOK ↑12.3k ↓200 /13.0k  |  💡 TIP /plan ...
```

### Glyph table

| Slot  | Old | New | Codepoint | Semantic |
|-------|-----|-----|-----------|----------|
| CTX   | `◑` | `🧠` | U+1F9E0 BRAIN | Model working memory filling up |
| CACHE | `⚡` | `⚡` | U+26A1 HIGH VOLTAGE | Fast retrieval (unchanged) |
| TOK   | `↕` | `🔁` | U+1F501 CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS | In/out token flow |
| TIP   | `✦` | `💡` | U+1F4A1 ELECTRIC LIGHT BULB | Idea / hint |

## Rationale

- **Brain (CTX):** The CTX column reports `used_percentage` of the
  context window. A brain emoji communicates "working memory capacity"
  more directly than a half-filled circle.
- **Bolt (CACHE):** Already correct — kept to avoid change for change's
  sake and to preserve the one icon that already pops.
- **Cycle (TOK):** Tokens flow in *and* out (the value next to it is
  `↑in ↓out /total`). A cyclic-arrow emoji rhymes visually with the
  inline `↑` `↓` and reads as "throughput".
- **Lightbulb (TIP):** Universal idea/hint metaphor.

## Trade-offs we are accepting

- **Cell width:** 🧠, 🔁, 💡 are double-width on terminals that follow
  the emoji presentation rule. Row 2 grows by ~3 cells overall. There
  is no cross-row alignment requirement (row 3 is an independent fixed-
  width progress bar), so this is purely a length change.
- **Color rendering:** `colorize("🧠 CTX", CLR_DIM)` wraps the emoji in
  the dim ANSI attribute. Color-emoji terminals render the emoji
  glyph in its native colors regardless, so the emoji visually
  *foregrounds* itself against the dimmed label. This is desirable
  for a "modern, icon-led" look.
- **Legacy terminals:** Terminals without an emoji font will render
  boxes. The statusline still produces well-formed three rows — it
  degrades gracefully, never breaks.

## Affected files

| File | Change |
|------|--------|
| `statusline/render.py` | 4 string-literal edits, one per `_row2_*` function. `_row2_cache` ends up touching only the `⚡` literal (already correct), but the edit re-confirms it. In practice, only 3 literals change. |
| `README.md`            | Line 8 sample rendering updated to match the new output so the README example matches reality. |

## Out of scope

- Row 1 and row 3 icons (`◆`, `📁`, `⎇`, the progress bar blocks) are
  unchanged.
- Color scheme, label text, value formatters, separators, and rotation
  logic are unchanged.
- No new config knob — the icons are constants in `render.py`. A future
  redesign could move them to a theme dict, but YAGNI for now.

## Verification

After implementation, the change is verified by:

1. Running `python3 -m statusline < tests/fixtures/sample.json` and
   confirming the printed row 2 begins with `🧠 CTX ` and contains
   ` 🔁 TOK ` and ` 💡 TIP `.
2. Running `pytest -v` — all 75 tests must continue to pass without
   modification. No test currently pins the icon literals (verified by
   `grep -n "◑\|⚡\|↕\|✦" tests/*.py` → 0 matches).
3. Visual confirmation in the user's actual Claude Code statusline.

## Rollback

A single `git revert` of the implementation commit fully restores the
prior icons. No state-file migration, no config compatibility surface.
