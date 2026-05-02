#!/usr/bin/env bash
# dev.sh — starts the Next.js development server.
#
# Uses a process-unique NEXT_DIST_DIR to avoid conflicts with any stale
# root-owned Next.js process that may be watching next.config.ts and
# pre-populating the build directory with unwritable root-owned files.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/.next-run-$$"

mkdir -p "$DIST_DIR"
echo "▶  Lauren AI Chatbot dev server"
echo "   distDir: $DIST_DIR"
echo ""

# Pass extra args (e.g. --turbo, --port 3001) through
exec /root/.nvm/versions/node/v25.6.0/bin/node node_modules/.bin/next dev \
  --experimental-https=false "$@"
