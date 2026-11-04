#!/usr/bin/env bash
# Scan every commit in this clone. CI checks out with fetch-depth: 0.
set -euo pipefail
cd "$(dirname "$0")/.."
gitleaks detect --source . --config .gitleaks.toml --redact --verbose --log-opts="--all"
