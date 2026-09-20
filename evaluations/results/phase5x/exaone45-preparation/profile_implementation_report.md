# Explicit EXAONE Korean native sampling profile

Implemented only the authorized four tracked files: `src/neurobuild/infrastructure/local_model.py`, `scripts/evaluate_requirements.py`, `tests/test_local_model.py`, and `tests/test_native_requirement_evaluation.py`. No model adoption or measured native execution is asserted.

The new enum is `EXAONE45_NONTHINKING_LLAMA_CPP`, value `exaone45_nonthinking_llama_cpp`. It requires `llama_cpp_json_schema`; evaluation additionally binds exact model ID `LGAI-EXAONE/EXAONE-4.5-33B-GGUF` and quantization `Q4_K_M`. The requested settings are:

```json
{"temperature":0.6,"top_p":0.95,"top_k":20,"min_p":0.0,"presence_penalty":1.5,"frequency_penalty":0.0,"repeat_penalty":1.0,"repeat_last_n":64,"seed":42,"samplers":["penalties","top_k","top_p","min_p","temperature"]}
```

The official pinned card recommends temperature0.6, top_p0.95, top_k20 and presence_penalty1.5 for Korean inputs. Window64 and the active sampler order follow the pinned native defaults, while explicit min_p0, neutral repeat/frequency and seed42 are our declared experimental settings. They must not be represented as additional official Korean model-card requirements. The full native default chain also contains DRY, top_n_sigma, typical and XTC; their inactive defaults are omitted from this explicit chain. Presence is applied before top-k/top-p and temperature, unlike the preserved Qwen/Gemma recipes' temperature-first chain.

Pinned source `f072b103714dfa1eee531f80b24512faf38e3dd2`: `common/common.h:239–269` declares window64, repeat1, frequency0 and the default order; `common/sampling.cpp:340–381` constructs the requested chain; `tools/server/server-schema.cpp:126–138,505–514` binds request fields. `src/llama-sampler.cpp:2889–2891,2920–2936,2952–2976` disables penalties for window0 or all-neutral settings and otherwise subtracts1.5 once for each token present in the window. Frequency0 contributes no count-dependent term, repeat1 contributes no multiplicative change.

**Window semantics include both prompt and generated tokens.** `tools/server/server-context.cpp:409–424` resets the sampler then accepts all prompt tokens with `is_generated=false`. `common/sampling.cpp:467–502` still accepts those tokens into the sampling chain; generated tokens also enter it. Thus the first generated token can be penalized for matching the most recent64 prompt/template tokens. This is not generated-output-only history and may affect exact quoting; no source/evidence repair or hidden disabling has been added. The effect on task quality is unmeasured.

The request remains explicitly `enable_thinking=false`, `stream=false`, one call, schema-bound. Existing final-only handling is reused: separate `message.reasoning_content` is not included in Completion or semantic parsing; inline `<think`/`</think` is rejected rather than removed. The native server's existing reasoning-off/deepseek/no-reasoning-preserve configuration is unchanged. The official EXAONE empty-thinking-prefix/native-parser behavior remains a separate model-specific CPU contract gate. No response-driven profile selection, retry, schema fallback or normalization was introduced.

Validation: eight new fake-opener tests PASS (0.276s), checking native-only selection, exact Korean wire and2→1 domain extraction, isolated sampler metadata, separate reasoning discard, inline reasoning rejection, truncation/rejection/no-final/fenced-output failures without retry, and exact model/quantization pairing. A separate metadata-only proof compared all33 valid old-profile/protocol/contract request bodies against checkpoint `f46b2cfe2c81769a10df06a92a4a28f1c4a72f84`: byte-identical; all21 previously invalid combinations retain the same rejection. Canonical parser and generation adapter bytes are unchanged; evaluator AST changes only `build_manifest`'s candidate map, leaving scoring and denominators unchanged. Full regression is reserved for root.

Receipt: `var/research/exaone45-profile-cpu-proof.json`, SHA256 `03ba52e6defe6056b19f4c301c1d7bd57de98bf8f56f5e7a19af14dab9b4f4c8` (includes four final source hashes). No sockets/HTTP, native binary, model, GPU, install, or holdout read occurred in this implementation task.

Official metadata source: [pinned EXAONE GGUF README](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B-GGUF/blob/0e969634ef24db05151b435970297a6dee634b7e/README.md); preserved local SHA256 `7616b420f4f3861ae28d4eb8acbc0ac9f004fa4e33ea82b061579409ccc4cdba`. See `exaone45_native_feasibility_review.md` for the separate resource/license/header limitations.
