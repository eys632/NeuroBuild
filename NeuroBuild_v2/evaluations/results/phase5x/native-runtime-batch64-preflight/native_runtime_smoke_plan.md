# Native startup and public resource probe — PREPARED, NOT EXECUTED

This is Phase 5.x runtime validation preparation. It does not authorize a launch by itself, establish model quality, select this candidate, or begin Phase 6. Root may proceed autonomously after the technical gates below; no new user approval is implied. No future v2 input/gold is used. The helper and its tests made **zero HTTP, model, GPU, native-binary or foreign-process calls**.

## Preconditions and ownership

Root must first finish the pinned GGUF download/header audit, CPU public grammar/template/tokenizer/context proofs, whole-VRAM review, fresh permitted-GPU3 preflight and explicit native launch config. Use the existing `scripts/llama_server.py` guard: physical GPU3/internal CUDA0 only, verified UUID/count, no GPU fallback, whole-process lifetime lock, own child-group cleanup, aggregate free floor and explicit whole-peak bound. The native process has no Torch allocator cap. Aggregate monitoring is neither a memory reservation nor a guaranteed per-process peak measurement.

The original batch1/ubatch1 profile failed in epochs1/2 at the native startup two-token sequence-removal capability test. The reviewed current profile is context4096/one sequence/**logical batch2 / physical ubatch1**/F16 K and V/flash-attention off/graphs off/no context shift. This changes the startup logical batch bound only; epoch3 must have fresh config and runtime proof. Startup and probes run sequentially within the same guarded epoch. stdout/stderr go to DEVNULL; `--log-disable`, own-child core limit zero, no verbose response fields. Do not change runtime/source/quantization/shape parameters after these probes and reuse their proof as if the epoch were unchanged.

Root has not yet authorized actual startup for this plan. A failed/timeout/unknown probe is a failure, never a reason to retry invisibly, shrink the probe, relax the floor or launch another GPU. If the HTTP client times out, the inference may still be winding down; root must reconcile the existing own epoch and stop it if needed before another operation.

## Helper/API

`var/research/native_runtime_probe.py` is import-only: no `main`, no import-time file/process/network operations. `test_native_runtime_probe.py` has fourteen CPU/fake tests, PASS (0.018s): exact request fields, strict boundary response, loopback-only/no redirect/bounded response, alias/path/context/template checks, evaluator metadata contract, exclusive report bundle, one public extraction call with no body returned, real multi-hop SONAME report shape, fixture-vs-native parity separation, and config/preflight budget mismatch rejection.

Root can import it with `importlib.util.spec_from_file_location` from backend `.conda`, then call only the chosen step. The helper never launches, downloads, signals or retries a process.

1. `load_config(path, expected_sha)` binds the exact NativeLaunchConfig JSON and non-thinking mode.
2. `binding(config)` rehashes the pinned source/build/header proofs, installed binary and all project shared libraries; checks the same-directory exact SONAME aliases, including verified multi-hop `.so → .so.0 → versioned.so` chains and complete `.so*` inventory. It binds the current owned GGUF size/header to the guard's full-model SHA validation. It deliberately does not rehash 18 GiB during every probe. Files must remain immutable during the epoch; this is not hostile same-UID sandboxing.
3. `epoch(config, pid, expected_ticks=None)` uses anchored `ProcReader` UID/start-time/executable/complete argv checks and the existing `verify_model_listeners`. All owned TCP listeners must be loopback, and the configured IPv4 API port must belong to this own PID. No other PID is scanned. Listener PASS is a time-bounded snapshot, not a promise about future sockets.
4. `capture_startup(config_path, config_sha, platform, runtime_variant=..., context_proof_path=..., context_proof_sha=...)` performs exactly three GETs and returns five immutable JSON byte artifacts. `platform` must contain root's freshly checked compiler/CMake/CUDA/driver/GPU name/GPU UUID facts; the function cannot attest these through HTTP. It does no GPU query. Reconfirm own epoch and guard state after GETs.
5. `public_smoke(config, runtime_variant=..., context_proof_path=..., context_proof_sha=..., timeout=120)` makes exactly one actual production client extraction on the existing public CPU fixture. Root must run `epoch`/`validate_guard` immediately before and after this call. The result contains only PASS/FAIL, a safe error code and latency, no final text/reasoning. No retry and no quality-gate claim.
6. `run_resource_smoke(config_path, config_sha, runtime_variant=..., context_proof_path=..., context_proof_sha=..., timeout=900)` makes exactly one native completion POST after artifact/own epoch/free-floor checks. It requires at least timeout+30 seconds of remaining guarded lifetime. Root may pick one explicit bound up to1800 seconds before execution; no timeout extension after seeing an incomplete result.
7. `write_bundle(new_absolute_var_reports_dir, {name: raw_bytes})` makes a new0700 directory, exclusively creates files, fsyncs files and directories; prior evidence cannot be overwritten. Incomplete partial bundles remain for diagnosis. Root may later copy exact bytes into the tracked archive.

Suggested startup use, **only after root's gates and launch**:

```python
bundle = probe.capture_startup(
    config_path, config_sha256, measured_platform_facts,
    runtime_variant="qwen38-gguf-raw-unicode-v1",
    context_proof_path=context_cpu_report, context_proof_sha=context_cpu_report_sha256)
proof_hashes = probe.write_bundle(ROOT / 'var/reports/qwen38-native-startup-epoch1', bundle)
```

The five outputs are `launch_config.json` (exact input bytes), `resource_report.json` (one exact live guard snapshot), `listeners.json`, `startup.json`, and `runtime_metadata.json`. Do not replace the resource snapshot after computing `startup.resource_report_sha256`. The runtime metadata uses the exact evaluator native field set: no fabricated Torch/vLLM/xgrammar versions. It pins source/build/shared-library evidence, GGUF/header, template, config, startup and listener hashes. The source report is provenance; the build is still statically compiled evidence and becomes runtime-observed only when this separate startup/smoke succeeds.

## Startup HTTP observations

- `/health` must return HTTP200 and `{status: ok}`.
- `/v1/models` must list exactly the requested alias and `meta.n_ctx == 4096`.
- `/v1/models` does **not** expose the actual GGUF path. `/props` is therefore needed: require exact model_path, alias, total_slots1, default_generation_settings.n_ctx4096 and expected embedded chat-template SHA.
- `/props` includes template text. The bounded response exists only in memory; save its SHA and scalar facts, never raw body. Guard reports continue saying `ready:false` because the guard itself performs no HTTP health test; startup proof is the separate readiness evidence, not a reason to alter historical guard semantics.

Pinned source: `tools/server/server-context.cpp` get_res_model_info/get_res_props (~4544–4635) and get_health (~4654), `tools/server/server.cpp` route registrations. Native guard entry arguments remain the authority for GPU/cache/mode flags; HTTP alias alone cannot establish them.

## Public production-wire smoke

Use the existing public sentence `검사실 책상을 X축 양의 방향으로 1m 옮겨줘.` and current explicit generation2 branch schema/promptv2/native protocol. Production profile remains `qwen38_nonthinking_llama_cpp`, max_tokens768, thinkingfalse, no retries. The exact parser/domain chain is unchanged. Require READY, target `검사실 책상`, dx1m/dy0m. A differing target or refusal is recorded as smoke FAIL, not repaired. The synthetic result is not included in evaluation denominators and does not reveal v2 inputs or outputs.

The helper discards final model output after parsing and never returns reasoning. The ordinary production client's bounded response/strict finish/schema checks apply. A later fixed quality freeze and separate exposed-dataset run are still mandatory; passing this one public sentence does not establish safety/quality.

## Maximum configured-context resource probe

Source supports a list of integer token IDs as one `/completion` prompt without automatic BOS/template insertion (`server-common.cpp`, tokenize_mixed/tokenize_input_subprompt ~869,980). Use the single ordinary space token from the explicitly derived raw-Unicode public reference, pinned SHA `9658eb53fae81adee1b775b45f796f3484db69aea41e04a020765fa05d770514`; repeat it3328 times. The original official-HF fixture remains unchanged at SHA `79c4448b7ee949add0a80e8a7f0fc0d73575aaf01ff6e52beb3cfae8434ea1bd`. Its native comparison FAILED19/20 at index11. This failure is mandatory provenance, not superseded by the derived raw reference. The helper requires a separate `NATIVE_CONTEXT_RAW_UNICODE_CPU_PROOF` PASS for the explicit variant, exact model/header/v4 CPU binary binding, both context splits and native parity20 against the derived reference. A prepared fixture or relabeled official-HF PASS is insufficient. This is public synthetic resource data, not an instruction or a held-out case.

Fixed request: integer prompt length3328, n_predict768, ignore_eos=true, cache_prompt=false, stream=false, return_tokens=false, stop=[], no grammar/response_format, n_probs0, neutral penalties, greedy temperature0/seed42. Resource-only sampling intentionally differs from quality sampling; no causal quality comparison is made. `response_fields` requests only token counts, stop/limit flags and numeric timing fields. Native `server-task.cpp` (~341–362) filters the native response before serialization, so generated content/prompt/token IDs are absent from the successful HTTP body. Reject extra fields. Transport bounds the body to8192B and discards errors without printing them.

`server-schema.cpp` ~31,44,78,475 implements cache/n_predict/field-filter/EOG suppression. `server-context.cpp` ~3217,3409 sets uncached n_past0, so `timings/prompt_n` must equal3328. Cache disabling guarantees no prompt-prefix computational reuse for this request; it does not return the native CUDA memory pool to a cold state.

**Boundary detail:** `process_token` ~1886 stops when existing prompt positions+1 >=4096, before decoding the final sampled token. Consequently the fixed expected response is tokens_evaluated3328, tokens_predicted768, tokens_cached4095, stoptrue, stop_type`limit`, truncatedtrue, and matching timing counts. This reaches the configured server's no-shift generation boundary; it does **not** claim4096 tokens were all decoded into KV. An unexpected count/stop is FAIL pending source/observation reconciliation, not silently accepted as close enough.

This long prefill+decode exercises the configured shape and persistent CUDA pool under the same guard. Repeated spaces do not prove all content-dependent worst cases or every GPU-resident tensor. The recorded minimum free/aggregate peak are lifetime aggregate readings (including startup/public smoke and other users' allowed-device activity), not isolated per-request/per-process attribution. A successful observed peak below the floor/limit does not upgrade the estimate to a universal guarantee.

## Remaining facts after a successful probe

Actual CUDA allocation/kernel compatibility, public-wire/schema behavior and the measured same-epoch resource envelope can then be reported. Compiler/storage hashes, installed shared-library checks, own-UID loopback proof and source flags remain separate evidence. Native internal CPU input embeddings/unsupported CPU ops are not forbidden by all-layer offload flags; CPU capacity fallback is disabled by explicitCUDA0/all/fitoff. No RTX5090 execution or SM120 claim is established. Adoption still requires the unchanged model rawREADY/unsafe/semantic gates and governed quality evaluation.

## Review corrections before execution

Root caught and corrected two pre-execution assumptions: actual SONAME aliases can have two hops, and the public parity fixture is not itself a native PASS proof. Architecture independently confirmed the integer-token/no-BOS, slash response field names and4095-cached final boundary; requested config/preflight peak/free-floor binding was added. All three now have regression cases. `max_seconds` is caller config plus elapsed report, not a separately reported server property; root must keep the exact original launch config immutable and archive it. No runtime call has been made by this task.


## D033 explicit raw-Unicode variant (no HF-equivalence claim)

The currently prepared experimental candidate is **`qwen38-gguf-raw-unicode-v1`**, not an official-HF-equivalent tokenizer. Actual original HF comparison stays FAIL19/20/index11; native raw byte roundtrip is20/20. A separate reference changes only HF tokenizer NFC normalizer toNone in memory, preserving all20 public strings and order; native vs this reference is20/20. This is a bounded observation, not Unicode equivalence for all text or a model quality result. No source quote normalization or application input/output repair is added.

All three runtime entrypoints require the caller's exact `runtime_variant` plus SHA-pinned new-kind raw context report. Before any HTTP request they check `hf_equivalence`/`raw_reference` records, actual original failed proof and actual derived successful proof, original and derived fixtures, exact model/header/v4 CPU binary/build/CPP hashes, and context split counts. Missing/misleading provenance, official-equivalence relabeling, silent NFC repair, old report kind or different binary fail closed. CPU tests include real public proof/fixture bytes and rejection before the HTTP/client construction boundary. No context dataset is read by this helper.

The production evaluator's strict native metadata field set remains unchanged. `startup.json` now includes `runtime_variant`, `reference_kind`, `context_cpu_proof_sha256`, `hf_equivalence` (FAIL19/20/index11 with original proof/fixture hashes), `raw_reference` (separate20/20 and native raw-roundtrip20 provenance), `context_tokenizer=native_raw_unicode_no_nfc_repair`, and `application_input_output_nfc_repair=false`. The existing `runtime_metadata.startup_report_sha256` binds this entire record. The later quality freeze must also explicitly duplicate-bind `candidate_variant`, `tokenizer_contract` and these proof hashes and retain both failure and raw-reference evidence. HTTP model alias, a raw-context PASS, or a metadata hash alone must not be described as official HF parity PASS.

Public-smoke and resource reports carry the same provenance. Runtime metadata has no new automatic variant inference. The previous ten-test preparation proof remains immutable; the new preparation proof is separate. Source/prompt/schema/scorer/gold and original HF fixture/proofs remain unchanged.


## Final consumer and epoch bindings before startup

Context consumers require top-level output cap768/context4096, both exact frozen split SHA values/counts, and each split `max_input_plus_output == max_input_tokens + 768 <=4096`. This rejects an otherwise same-count proof generated with a smaller cap or different inputs. No dataset body is opened for this check. Root's completed raw-context proof SHA `5d37568d7b51d1b689b168f0e9fa6fb46ac487b70f451c82611c146f978e59be` passed this report-only consumer validation; that is not an additional native/model execution.

Resource return now contains the launch config SHA, own PID, process start ticks and guard started_at_utc from its already-verified before/after epoch. Root's public-smoke wrapper must add the same four fields only after performing own-epoch checks before/after the single call. The freeze consumer compares both smoke epochs to startup plus the exact archived guard snapshot, and validates the full evaluator metadata against the same config/proof hashes. Before/after guard hashes in the resource report describe the observed mutable reports; they are not claims that standalone snapshot files were saved by this function.

Planned tracked storage (root controls publication):

- Startup five-JSON bundle: `evaluations/results/phase5x/qwen38-native-startup-epoch1/`
- Public smoke: `evaluations/results/phase5x/qwen38-native-public-smoke-epoch1/report.json`
- Resource smoke: `evaluations/results/phase5x/qwen38-native-resource-epoch1/report.json`

The helper writes new proof bundles under var/reports only; root publishes exact bytes at those archive paths. Failed/runtime-incomplete reports remain failures. No source/prompt/schema/gold/evaluator change is part of this task.

## Batch2 consumer update

After root observed the sanitized epoch2 assertion `llama-context.cpp:1734`, production fixes logical batch2/physical ubatch1. The evidence consumer now requires exact integer config.batch_size2/config.ubatch_size1 and an identical guard report; old batch1, booleans and mismatched report/config values fail. Other gates remain unchanged. Fourteen focused CPU/fake tests passed in0.034s. Original batch1 helper/test/proof bytes are preserved under `var/research/native-runtime-probe-history/batch1/`; original14-test proof is not overwritten. Root will use fresh epoch3 archive paths instead of the earlier proposed epoch1 paths above. No HTTP/native/GPU call was made during this update.
