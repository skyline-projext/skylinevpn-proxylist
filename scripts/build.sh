#!/usr/bin/env bash
# Fetch and decode the base64 upstream rule source, then merge and deduplicate it into proxy.list
set -euo pipefail

SRC_URL="${SRC_URL:-https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIST="${1:-$ROOT/proxy.list}"

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

curl -fsSL --retry 3 "$SRC_URL" | base64 -d > "$tmp"
python3 "$ROOT/scripts/merge.py" "$tmp" "$LIST"
