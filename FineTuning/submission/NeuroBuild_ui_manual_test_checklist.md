# NeuroBuild UI Manual Test Checklist

## Preconditions
- Copy workspace only (ui_integration_workspace/NeuroBuild_ui_test_copy)
- Base model and LoRA adapter paths exist
- GPU visibility set (CUDA_VISIBLE_DEVICES)

## API Sanity
- [ ] GET /api/llm/status on base server shows mode=base and adapter_path=null
- [ ] GET /api/llm/status on lora server shows mode=lora and adapter_path set
- [ ] POST /api/generate returns 200 with llm.edits populated

## UI Behavior
- [ ] Open UI and connect to base server
- [ ] Run prompt ui_001..ui_010 and record edits
- [ ] Switch to lora server and repeat prompts
- [ ] Confirm lora improves expected_op for ui_001 and ui_002

## Regression Checks
- [ ] Non-LLM generation path still works
- [ ] JSON parsing errors are handled (no crash)
- [ ] Changes do not affect original project

## Notes
- If any failures occur, capture status code and response body snippet
