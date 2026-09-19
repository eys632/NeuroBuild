# NeuroBuild UI Integration Plan (Copy Only)

## Goal
Integrate LLM switching (base vs LoRA vs vLLM) in the copied UI workspace without touching the original project. Validate API behavior and produce UI-focused artifacts.

## Scope
- Target workspace: ui_integration_workspace/NeuroBuild_ui_test_copy
- Do not modify: /home/eys632/26-2project (original)

## Model Modes
- base: local model, no adapter, standard HF generate
- lora: local model + PEFT adapter
- vllm: remote/sidecar vLLM endpoint (no local load)

## Env Vars
- NB_LLM_MODE: base | lora | vllm
- NB_MODEL_ID: local model path or HF id
- NB_ADAPTER_PATH: local LoRA adapter path
- NB_VLLM_URL / NB_VLLM_MODEL / NB_VLLM_TOKEN: vLLM settings

## APIs to Validate
- POST /api/generate
  - input: {"prompt": "...", "use_llm": true, "base_file_id": "..."}
  - output: includes llm.edits array
- GET /api/llm/status
  - verify mode/model_id/adapter_path/loaded

## Test Data
- submission/ui_test_cases.jsonl (10 prompts)
- includes expected_op and expected_empty_edits

## Compare Script
- submission/run_ui_api_compare.py
- runs base + lora endpoints, stores jsonl results + summary

## Steps
1) Start base server (8101) and lora server (8102)
2) Confirm /api/llm/status for each
3) Run compare script against ui_test_cases.jsonl
4) Review summary and diffs

## Expected Outputs
- submission/ui_base_results.jsonl
- submission/ui_lora_results.jsonl
- submission/ui_compare_results.json
- submission/ui_api_compare_summary.md

## Notes
- If vLLM is used, set NB_LLM_MODE=vllm and NB_VLLM_*; local load is skipped
- Failures are recorded in compare outputs (status/error fields)
