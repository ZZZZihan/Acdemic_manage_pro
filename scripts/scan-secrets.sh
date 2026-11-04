#!/usr/bin/env bash
# Scan the current worktree. This does not scan git history.
# History still needs a separate purge; see SECURITY.md.
set -euo pipefail
cd "$(dirname "$0")/.."
gitleaks detect --no-git --source . --config .gitleaks.toml --redact --verbose
