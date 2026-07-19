#!/usr/bin/env bash
# sync.sh — pull and merge latest changes from origin (e.g. after the Action updates README.md)
set -euo pipefail

BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "🔄 Fetching origin/$BRANCH..."
git fetch origin "$BRANCH"

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [[ "$LOCAL" == "$REMOTE" ]]; then
  echo "✅ Already up to date."
  exit 0
fi

echo "⬇️  Merging origin/$BRANCH..."
git merge --no-edit origin "$BRANCH"
echo "✅ Merged. Local branch is now up to date."
