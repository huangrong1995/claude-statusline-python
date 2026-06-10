#!/usr/bin/env bash
# Statusline shim — delegates to the Python package.
# The actual implementation lives in statusline/ (Python 3.10+).
set -euo pipefail
cd "$(dirname "$0")"
exec python3 -m statusline "$@"
