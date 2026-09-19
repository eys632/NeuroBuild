#!/usr/bin/env bash
set -euo pipefail

BASE_PID_FILE="/home/eys632/26-2proj-FineTuning/submission/ui_eval_results/server_logs/base_8101.pid"
LORA_PID_FILE="/home/eys632/26-2proj-FineTuning/submission/ui_eval_results/server_logs/lora_8102.pid"

stop_pid() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    echo "${name}: pid 파일 없음"
    return 0
  fi

  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ -z "$pid" ]]; then
    echo "${name}: pid 비어있음"
    return 0
  fi

  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    echo "${name}: 종료 요청 (pid=${pid})"
  else
    echo "${name}: 이미 종료됨 (pid=${pid})"
  fi
}

stop_pid "base_8101" "$BASE_PID_FILE"
stop_pid "lora_8102" "$LORA_PID_FILE"
