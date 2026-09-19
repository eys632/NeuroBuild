#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export CUDA_VISIBLE_DEVICES=0
export NB_LLM_MODE=base
export NB_MODEL_ID=/home/eys632/26-2project/models/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28

/home/eys632/26-2proj-FineTuning/.venv_ui/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8101
