#!/usr/bin/env bash
# deploy.sh — commit, push, and trigger the update-readme workflow
set -euo pipefail

WORKFLOW_FILE="update-readme.yml"
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# ── 1. Stage & commit (skip if tree is clean) ────────────────────────────────
echo "📦 Staging changes..."
git add -A

if git diff --staged --quiet; then
  echo "✅ Nothing to commit – working tree is clean."
else
  git commit -m "chore: update readme config"
  echo "✅ Committed."
fi

# ── 2. Push ──────────────────────────────────────────────────────────────────
echo "🚀 Pushing to origin/$BRANCH..."
git push origin "$BRANCH"
echo "✅ Pushed."

# ── 3. Trigger workflow_dispatch ─────────────────────────────────────────────
echo "⚙️  Triggering '$WORKFLOW_FILE' via workflow_dispatch..."

if command -v gh &>/dev/null; then
  gh workflow run "$WORKFLOW_FILE" --ref "$BRANCH"
  echo "✅ Workflow triggered via GitHub CLI."
  echo ""
  echo "👀 Watching run (Ctrl+C to detach)..."
  sleep 3   # give GH a moment to register the run
  gh run watch "$(gh run list --workflow="$WORKFLOW_FILE" --limit=1 --json databaseId --jq '.[0].databaseId')"
else
  echo "⚠️  GitHub CLI (gh) not found – triggering via REST API instead."
  echo "   Make sure GH_TOKEN or GITHUB_TOKEN is set in your environment."

  TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
  if [[ -z "$TOKEN" ]]; then
    echo "❌ No token found. Set GH_TOKEN or GITHUB_TOKEN and re-run." >&2
    exit 1
  fi

  REMOTE_URL=$(git remote get-url origin)
  # Extract "owner/repo" from https or ssh remote URL
  REPO=$(echo "$REMOTE_URL" \
    | sed -E 's|.*github\.com[:/]||; s|\.git$||')

  curl -s -o /dev/null -w "HTTP %{http_code}\n" \
    -X POST \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer $TOKEN" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/$REPO/actions/workflows/$WORKFLOW_FILE/dispatches" \
    -d "{\"ref\":\"$BRANCH\"}"

  echo "✅ Workflow dispatch sent."
  echo "   Check progress at: https://github.com/$REPO/actions"
fi
