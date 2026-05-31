#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

. .venv/bin/activate

export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8000}"
export HF_HOME="${HF_HOME:-$PWD/models}"

python -m backend.app
