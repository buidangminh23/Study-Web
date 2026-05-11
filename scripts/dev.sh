#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  ./scripts/setup.sh
fi

export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8036}"

./.venv/bin/python run.py
