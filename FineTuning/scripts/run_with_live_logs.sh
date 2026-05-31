#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "사용법: $0 <train|eval|compare> [args...]" >&2
  exit 2
fi

MODE="$1"
shift

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LIVE_DIR="$ROOT_DIR/results/live"
mkdir -p "$LIVE_DIR"

case "$MODE" in
  train)
    LOG_FILE="$LIVE_DIR/terminal_train.log"
    CMD=(python3 -u "$ROOT_DIR/scripts/train_sft.py" "$@")
    ;;
  eval)
    LOG_FILE="$LIVE_DIR/terminal_eval.log"
    CMD=(python3 -u "$ROOT_DIR/scripts/run_baseline_eval.py" "$@")
    ;;
  compare)
    LOG_FILE="$LIVE_DIR/terminal_eval.log"
    CMD=(python3 -u "$ROOT_DIR/scripts/compare_results.py" "$@")
    ;;
  *)
    echo "알 수 없는 모드: $MODE" >&2
    exit 2
    ;;
esac

stdbuf -oL -eL "${CMD[@]}" 2>&1 | tee -a "$LOG_FILE"
