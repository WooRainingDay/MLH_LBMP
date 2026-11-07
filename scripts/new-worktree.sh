#!/usr/bin/env bash
# Usage: scripts/new-worktree.sh <name>
# Creates ../<repo>-<name> on a new branch feat/<name> from origin/main (or main),
# copies .env files and .claude/settings.local.json, and installs dependencies.
set -euo pipefail

if [ $# -ne 1 ] || [ -z "$1" ]; then
  echo "Usage: $0 <name>" >&2
  exit 1
fi
NAME="$1"

ROOT="$(git rev-parse --show-toplevel)"
REPO="$(basename "$ROOT")"
DEST="$(dirname "$ROOT")/${REPO}-${NAME}"
BRANCH="feat/${NAME}"

if [ -e "$DEST" ]; then
  echo "Error: $DEST already exists." >&2
  exit 1
fi

git -C "$ROOT" fetch origin main --quiet 2>/dev/null || true
if git -C "$ROOT" rev-parse --verify --quiet origin/main >/dev/null; then
  BASE="origin/main"
elif git -C "$ROOT" rev-parse --verify --quiet main >/dev/null; then
  BASE="main"
else
  echo "Error: neither origin/main nor main exists." >&2
  exit 1
fi

echo "Creating worktree $DEST on $BRANCH from $BASE"
# --no-track: the new branch must not have origin/main as its upstream.
git -C "$ROOT" worktree add --no-track -b "$BRANCH" "$DEST" "$BASE"

# Copy env files (none is fine) and local Claude settings.
shopt -s nullglob dotglob
copied=0
for f in "$ROOT"/.env "$ROOT"/.env.*; do
  if [ -f "$f" ] && [ "$(basename "$f")" != ".env.example" ]; then
    cp "$f" "$DEST/" && copied=$((copied + 1))
  fi
done
shopt -u nullglob dotglob
echo "Copied $copied env file(s)."

if [ -f "$ROOT/.claude/settings.local.json" ]; then
  mkdir -p "$DEST/.claude"
  cp "$ROOT/.claude/settings.local.json" "$DEST/.claude/"
  echo "Copied .claude/settings.local.json"
fi

# Install dependencies with the package manager matching the lockfile.
cd "$DEST"
if [ -f pnpm-lock.yaml ]; then
  pnpm install
elif [ -f yarn.lock ]; then
  yarn install
elif [ -f bun.lockb ] || [ -f bun.lock ]; then
  bun install
elif [ -f package-lock.json ] || [ -f package.json ]; then
  npm install
else
  echo "No JS lockfile or package.json; skipping JS install."
fi
if [ -f requirements.txt ]; then
  echo "Python project: create a venv and run 'pip install -r requirements.txt' in the new worktree."
fi

echo
echo "Done. Next:"
echo "  cd \"$DEST\" && claude"
