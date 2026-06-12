# Row 1 First Icon Redesign — Sparkles

**Date:** 2026-06-12
**Scope:** Visual redesign of the leading icon on row 1 of the statusline (the one that prefixes the model name).
**Status:** Approved for implementation.

## Motivation

Row 1's leading icon is currently `◆` (filled diamond, U+25C6) — a generic
geometric glyph that signals nothing about what follows it (the model name).
Three pressures converge on changing it now:

1. **Semantic vacancy.** The icon prefixes the model name. It should *mean*
   "AI model". `◆` does not.
2. **Row 1 was already half-emoji.** The directory icon (`📁`) is already
   an emoji; only the model icon and the git glyph (`⎇`, kept) are not.
3. **Cross-row consistency.** Row 2 just landed on emoji (🧠 ⚡ 🔁 💡). A
   text-symbol diamond at the very start of the statusline is now visually
   the odd one out.

The replacement is `✨` (U+2728 SPARKLES) — the industry-standard "AI"
glyph (Apple Intelligence, Notion AI, ChatGPT, Gemini, and Anthropic's
own Claude branding all use a sparkle / star motif).

## Design

### Before

```
◆ Claude 4.6 Sonnet  |  📁 ~/projects/example  |  ⎇ main
```

### After

```
✨ Claude 4.6 Sonnet  |  📁 ~/projects/example  |  ⎇ main
```

### Glyph table

| Slot          | Old | New | Codepoint               | Status    |
|---------------|-----|-----|-------------------------|-----------|
| Model prefix  | `◆` | `✨` | U+2728 SPARKLES          | Changed   |
| Directory     | `📁` | `📁` | U+1F4C1 FILE FOLDER       | Unchanged |
| Git branch    | `⎇` | `⎇` | U+23C7 DENTISTRY SYMBOL  | Unchanged |

The git glyph stays a deliberately-technical Unicode character — a git
branch is a technical concept and the existing glyph reads correctly to
the audience.

## Rationale

- **Sparkles is the de facto modern AI marker.** It signals "this is the
  AI / model / generated output" instantly to anyone who has used a
  modern AI product in the last two years.
- **Distinct from row 2.** Row 2 uses 🧠 for CTX (working memory). Row 1
  uses ✨ for the model itself. No glyph repetition; the two icons cannot
  be confused for the same concept.
- **Color wrapper preserved.** The current `CLR_ACCENT` ANSI wrapper
  around `◆` is kept around `✨` for minimal-diff hygiene and for forward
  compatibility — if `✨` is ever reverted to a text glyph, the accent
  color comes back automatically. Color terminals render color emoji in
  their native colors regardless of ANSI fg, so the wrapper is a
  harmless no-op for the emoji case.

## Trade-offs we are accepting

- **Cell width:** `✨` is double-width on terminals that follow the
  emoji presentation rule, vs `◆` which is single-cell ambiguous-width.
  Row 1 grows by ~1 cell overall. No cross-row alignment requirement
  exists (row 2 is independent; row 3 is a fixed-width progress bar),
  so this is purely a length change.
- **Legacy terminals:** Terminals without an emoji font render a box.
  The statusline still produces three well-formed rows — it degrades
  gracefully.
- **Color metadata loss for the icon itself.** `CLR_ACCENT` previously
  brand-colored the `◆`. Color emoji ignore the ANSI fg, so the
  emoji's color is now whatever the terminal's emoji font provides
  (typically yellow / golden for `✨`). This is desirable for a "modern
  icon-led" look and consistent with the row-2 decision.

## Affected files

| File | Change |
|------|--------|
| `statusline/render.py:72` | One character swap inside `row1()`'s f-string: `"◆"` → `"✨"`. |
| `README.md:7`             | Sample rendering's first line updated to `✨ Claude 4.6 Sonnet …`. |

Verified via `grep -rn "◆" statusline/ tests/ README.md` — these two
lines are the only source/doc occurrences. Other `◆` matches in `docs/`
are historical "before" references inside the prior row-2 spec and plan,
which are correctly frozen and must not be edited.

## Out of scope

- The directory icon (`📁`) and git glyph (`⎇`) on row 1 are unchanged.
- Row 2 and row 3 are unchanged.
- The `CLR_ACCENT` definition itself is unchanged.
- No new config knob — the icon is a constant in `render.py`.

## Verification

After implementation, the change is verified by:

1. A new test in `tests/test_render.py` pinning `"✨ "` in `row1()` output.
2. Running `pytest -v` — all existing tests must continue to pass
   without modification. No test currently pins `◆` (verified via
   `grep -rn "◆" tests/` → 0 matches).
3. Running `python3 -m statusline < tests/fixtures/sample.json` and
   visually confirming the first character of row 1 is `✨`.

## Rollback

The implementation lands as two commits (matching the row-2 pattern):
test + render.py together, then README sync separately. Rollback is
`git revert` of both commits — first the README commit, then the
test+render commit. No state-file migration, no config compatibility
surface.
