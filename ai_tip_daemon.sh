#!/usr/bin/env bash
# ai_tip_daemon.sh — Background generator for AI-powered statusline tips
#
# Periodically gathers the current workspace state, sends it to Claude Haiku
# with a small prompt, and writes the resulting tip to a cache file that
# the statusline reads on each render. Cheap (~150 tokens in, ~30 out),
# runs every $_AI_TIP_INTERVAL seconds.
#
# Cache file: ~/.claude/statusline/ai_tip_cache
#   line 1: tip text
#   line 2: ISO-8601 timestamp
#   line 3: model that produced it
#
# The statusline treats the cache as fresh for 5 minutes; the daemon
# refreshes every 4 minutes (configurable) to keep the cache live.
#
# Install:
#   macOS  — add a launchd plist (see README)
#   Linux  — add a systemd user timer (see README)
#   Quick  — run `nohup ai_tip_daemon.sh &` from a shell
#
# Required env:
#   ANTHROPIC_API_KEY   — your key (or use Claude Code's session token)
#
# Optional env:
#   AI_TIP_INTERVAL     — seconds between refreshes (default 240)
#   AI_TIP_MODEL        — model id (default claude-haiku-4-5)
#   AI_TIP_CACHE        — cache path (default ~/.claude/statusline/ai_tip_cache)

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────
INTERVAL="${AI_TIP_INTERVAL:-240}"
MODEL="${AI_TIP_MODEL:-claude-haiku-4-5}"
CACHE="${AI_TIP_CACHE:-${HOME}/.claude/statusline/ai_tip_cache}"
STATUSLINE_DIR="${HOME}/.claude/statusline"
LOCKFILE="${STATUSLINE_DIR}/.ai_tip_daemon.lock"
LOGFILE="${STATUSLINE_DIR}/ai_tip_daemon.log"

mkdir -p "$STATUSLINE_DIR"

# ── Single-instance lock ──────────────────────────────────────────────────
exec 9>"$LOCKFILE"
if ! flock -n 9; then
    echo "[$(date -Iseconds)] another instance running, exiting" >> "$LOGFILE"
    exit 0
fi

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*" >> "$LOGFILE"; }

# ── State collector ──────────────────────────────────────────────────────
# Produces a compact JSON-ish blob of current state for the LLM.
collect_state() {
    local dir="${PWD}"
    local ctx_pct="${_SL_CONTEXT_PCT:--1}"
    local elapsed="${_SL_SESSION_SECONDS:-0}"
    local model="${_SL_MODEL_RAW:-unknown}"
    local thinking="${_SL_THINKING:-false}"
    local effort="${_SL_EFFORT:-}"

    # Git state
    local git_branch="" git_status="" git_unpushed=0
    if git -C "$dir" rev-parse --git-dir >/dev/null 2>&1; then
        git_branch=$(git -C "$dir" branch --show-current 2>/dev/null || echo "")
        git_status=$(git -C "$dir" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
        git_unpushed=$(git -C "$dir" log --oneline '@{u}..' 2>/dev/null | wc -l | tr -d ' ')
    fi

    # Project shape
    local proj="unknown"
    [ -f "$dir/package.json" ] && proj="node"
    [ -f "$dir/Cargo.toml" ] && proj="rust"
    [ -f "$dir/go.mod" ] && proj="go"
    [ -f "$dir/pyproject.toml" ] && proj="python"

    cat <<EOF
{
  "model": "$model",
  "effort": "$effort",
  "thinking": "$thinking",
  "context_pct": $ctx_pct,
  "elapsed_sec": $elapsed,
  "project_type": "$proj",
  "has_claude_md": $([ -f "$dir/CLAUDE.md" ] && echo true || echo false),
  "git_branch": "$git_branch",
  "git_modified_files": ${git_status:-0},
  "git_unpushed_commits": ${git_unpushed:-0}
}
EOF
}

# ── LLM call ────────────────────────────────────────────────────────────
# Calls Claude API with a tight prompt asking for a short actionable tip.
# Falls back gracefully on any error.
call_llm() {
    local state_json="$1"

    if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
        log "no ANTHROPIC_API_KEY set, skipping"
        return 1
    fi

    local prompt
    prompt=$(cat <<'PROMPT'
You are a tip engine for a Claude Code statusline. Given the current
session state below, produce ONE short actionable tip (≤60 chars) the
user could act on RIGHT NOW. Be specific, not generic.

Tie tips to actual state signals:
- High context_pct → /compact, /clear, summarize
- Many modified files → /review, /commit, /simplify
- No CLAUDE.md → /init
- Long elapsed → save memory with #
- Quiet state (clean tree, low ctx) → /plan, /refactor, /deep-research
- Test failures / many TODOs → /systematic-debugging, cleanup sprint

Output ONLY the tip text. No quotes, no prefix, no explanation.
PROMPT
    )

    local request_body
    request_body=$(jq -n \
        --arg model "$MODEL" \
        --arg system "$prompt" \
        --argjson state "$state_json" \
        '{
            model: $model,
            max_tokens: 80,
            system: $system,
            messages: [{role: "user", content: ($state | tostring)}]
        }')

    local response
    response=$(curl -sS --max-time 15 \
        -H "Content-Type: application/json" \
        -H "x-api-key: $ANTHROPIC_API_KEY" \
        -H "anthropic-version: 2023-06-01" \
        -d "$request_body" \
        "https://api.anthropic.com/v1/messages" 2>/dev/null) || {
        log "curl failed"
        return 1
    }

    # Extract text from response
    local tip
    tip=$(printf '%s' "$response" | jq -r '.content[0].text // empty' 2>/dev/null)
    if [ -z "$tip" ]; then
        log "empty response: $(printf '%s' "$response" | head -c 200)"
        return 1
    fi

    # Trim to ≤60 chars
    tip="${tip:0:60}"
    # Strip surrounding whitespace/quotes
    tip="${tip#"${tip%%[![:space:]]*}"}"
    tip="${tip%"${tip##*[![:space:]]}"}"
    tip="${tip//\"/}"

    printf '%s' "$tip"
}

# ── Cache writer ────────────────────────────────────────────────────────
write_cache() {
    local tip="$1"
    local tmp="${CACHE}.tmp"

    {
        printf '%s\n' "$tip"
        printf '%s\n' "$(date -Iseconds)"
        printf '%s\n' "$MODEL"
    } > "$tmp"

    mv "$tmp" "$CACHE"
    log "wrote: $tip"
}

# ── Main loop ───────────────────────────────────────────────────────────
log "daemon started, interval=${INTERVAL}s, model=$MODEL"

cleanup() {
    log "daemon stopping"
    rm -f "$LOCKFILE"
    exit 0
}
trap cleanup INT TERM

# Initial refresh on startup so the cache is populated quickly
while true; do
    state_json=$(collect_state)
    tip=$(call_llm "$state_json" 2>/dev/null || echo "")
    if [ -n "$tip" ]; then
        write_cache "$tip"
    else
        log "no tip produced, will retry in ${INTERVAL}s"
    fi
    sleep "$INTERVAL" &
    wait $!
done
