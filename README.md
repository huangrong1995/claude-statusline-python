# Claude Code Statusline

Three-row, low-noise statusline with adaptive tips and optional AI integration.

## Layout

```
◆ Claude 3.5 Sonnet | 📁 ~/projects/forge | ⎇ main
CTX 68% | CACHE 92% | ↕ TOK ↑1.2k ↓300 /200.0k | TIME 01:24 | ✦ TIP /plan the next refactor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━──── 68%
```

## Modules

| File              | Purpose                                              |
|-------------------|------------------------------------------------------|
| `render.sh`       | Orchestrator: parses JSON, calls modules, assembles  |
| `model.sh`        | Model name display                                   |
| `git.sh`          | Branch + worktree indicator                          |
| `context.sh`      | Context window percentage                            |
| `cache.sh`        | Cache hit rate                                       |
| `timer.sh`        | Session elapsed time                                 |
| `progress.sh`     | Unicode progress bar (━/─)                           |
| `tip.sh`          | Adaptive tips (state detection + AI)                 |
| `ai_tip_daemon.sh`| Background AI tip generator (optional)               |
| `statusline.sh`   | Top-level entry script called by Claude Code         |

## Adaptive Tips — How It Works

`tip.sh` chooses what to show across six layers, in priority order:

1. **Context pressure** — when context window ≥ 60% / 85%, warns about
   `/compact` or `/clear` (color-coded orange / red).
2. **Mode/state** — shows "Thinking on…" or "Vim INSERT · Esc…" when active.
3. **Long session** — after 20 min, nudges to save memory with `#`.
4. **AI-generated** — reads from `~/.claude/statusline/ai_tip_cache` if
   the daemon has produced a tip within the last 5 minutes.
5. **State-detected** — no AI required, looks at:
   - git status (clean, dirty, dirty_many, unpushed)
   - presence of `CLAUDE.md`
   - test directory presence
   - project type (node/rust/go/python via lockfile/manifest)
   - TODO/FIXME count (via `rg` if installed)
6. **Generic rotating** — pool of ~30 useful tips, rotates every 5 min.

State detection runs on every render (~30 ms) using only data already
loaded plus a few fast filesystem checks. It is enabled by default and
requires nothing extra.

## AI Integration (Optional)

`ai_tip_daemon.sh` is a background process that periodically calls Claude
Haiku to generate a tip tailored to the current state, and writes it to
`~/.claude/statusline/ai_tip_cache`. The statusline reads this cache on
each render (fresh for 5 min, else ignored). AI tips are rendered in
the accent color so you can tell them apart from heuristic ones.

### What the AI sees

A small JSON blob (~150 tokens):
- model, effort, thinking mode
- context percentage, session elapsed
- project type (node/rust/go/python)
- `has_claude_md`, `git_branch`, `git_modified_files`, `git_unpushed_commits`

### What the AI produces

A single tip string ≤ 60 chars, no prefix, no quotes. The daemon
trims/sanitizes the output before writing.

### Cost

~150 input + 30 output tokens per call. With `AI_TIP_INTERVAL=240`
(every 4 min), that's ~24 calls/hour ≈ 0.5¢/hour with Haiku pricing.

### Required environment

- `ANTHROPIC_API_KEY` — your key (use a dedicated key with low spend limit)

### Optional environment

| Variable          | Default                                          |
|-------------------|--------------------------------------------------|
| `AI_TIP_INTERVAL` | `240` (seconds between refreshes)                |
| `AI_TIP_MODEL`    | `claude-haiku-4-5`                               |
| `AI_TIP_CACHE`    | `~/.claude/statusline/ai_tip_cache`              |

### Install — macOS (launchd)

Save as `~/Library/LaunchAgents/com.claudecode.ai-tip-daemon.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.claudecode.ai-tip-daemon</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/YOU/.claude/statusline/ai_tip_daemon.sh</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>ANTHROPIC_API_KEY</key>
    <string>sk-ant-...</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/ai-tip-daemon.out</string>
  <key>StandardErrorPath</key>
  <string>/tmp/ai-tip-daemon.err</string>
</dict>
</plist>
```

Then:

```bash
launchctl load ~/Library/LaunchAgents/com.claudecode.ai-tip-daemon.plist
```

### Install — Linux (systemd user timer)

Save as `~/.config/systemd/user/ai-tip-daemon.service`:

```ini
[Unit]
Description=Claude Code AI Tip Daemon
After=network-online.target

[Service]
Type=simple
ExecStart=/bin/bash %h/.claude/statusline/ai_tip_daemon.sh
Environment=ANTHROPIC_API_KEY=sk-ant-...
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

And `~/.config/systemd/user/ai-tip-daemon.timer`:

```ini
[Unit]
Description=Restart AI tip daemon on failure

[Timer]
OnBootSec=30
OnUnitActiveSec=4min

[Install]
WantedBy=timers.target
```

Then:

```bash
systemctl --user daemon-reload
systemctl --user enable --now ai-tip-daemon.timer
```

### Install — quick & dirty

```bash
export ANTHROPIC_API_KEY=sk-ant-...
nohup ~/.claude/statusline/ai_tip_daemon.sh &
```

Logs go to `~/.claude/statusline/ai_tip_daemon.log`.

### Disable

Just don't run the daemon. The statusline falls back to the
state-detection and generic tip layers automatically — no configuration
needed.

To temporarily ignore a stale cache:

```bash
rm ~/.claude/statusline/ai_tip_cache
```

## Cache File Format

`~/.claude/statusline/ai_tip_cache`:

```
Try /plan the next refactor
2026-06-09T14:32:11+00:00
claude-haiku-4-5
```

Line 1: tip text. Line 2: ISO-8601 timestamp. Line 3: model id.

The statusline only reads line 1 and uses file mtime for freshness.
Lines 2-3 are informational and for debugging.

## Performance Notes

- All tip selection runs in <30 ms on each statusline render.
- `git status --porcelain` and `git log '@{u}..'` add ~10-20 ms in
  git repos. The detection uses `wc -l` and is intentionally
  lightweight — no diff parsing, no file content reads.
- `rg` is optional; `many_todos` state is simply not detected without it.
- AI daemon runs every 4 min in the background and never blocks the
  statusline render.

## Customizing Tips

Edit `tip.sh`:

- **Priority 1-3** (context pressure, mode, long session): edit the
  top of `_sl_tip()`.
- **State detection**: edit `_sl_tip_detect_state()` to add new tags.
- **State → tip mapping**: edit `_sl_tip_for_state()`.
- **Generic pool**: edit `_sl_tip_generic()`.

No restart needed — statusline re-sources on every render.
