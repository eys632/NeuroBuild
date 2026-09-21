# Native transport / cleanup independent review

2026-09-20, read-only review by runtime_skeleton. **PASS for the reviewed source boundaries; actual native runtime remains unverified.** No native binary, GPU query, inference, cleanup operation or future holdout-v2 body was accessed in this review.

## Source and compatibility

Compared against `52ffb5a2847e15ef79678fce54625dfb7f59841e`:

- `local_model.py` adds the explicit `llama_cpp_json_schema` dialect and `qwen38_nonthinking_llama_cpp` recipe. There is no response-driven detection, model-name selection, retry, correction or external fallback. Mixing this recipe with vLLM, or old Qwen3 recipes with native transport, fails before HTTP. Native greedy remains a transport control; the evaluator rejects it as the declared candidate recipe.
- Native request uses `response_format.json_schema.schema`, matching pinned llama.cpp `tools/server/server-common.cpp:1193–1195`. The request explicitly disables thinking and sets T=.7, top_p=.8, top_k=20, min_p=0, presence/frequency=0, repeat_penalty=1, repeat_last_n=0, seed42 and ordered samplers temperature/top_k/top_p/min_p. A fresh list is returned each time. This is a deliberate native experiment, not the model card's presence-penalty recipe or a determinism claim.
- Existing final-content, response-size/time limits, model identity, no-redirect/proxy handling, truncation/tool/reasoning-in-content rejection and safe errors remain unchanged. A separate reasoning field is discarded rather than retained in Completion or logs.
- Evaluator additions validate native metadata and GGUF/tokenizer/protocol/profile bindings. Native records do not invent Torch/vLLM/xgrammar versions. Hashes are operator-supplied evidence bindings, explicitly not live-process attestation. Build, shared-library closure, header/template, startup and listener evidence still require separate verification.
- `evaluate_trial`, semantic scoring, raw-READY counting, unknown-response handling, summary formulas and denominators are unchanged. The 52ff comparison reports no tracked changes under Domain, Application, prompts, schemas or evaluations. No gold or canonical parser relaxation occurred.

Reviewed current SHA256:

- client: `3ebef3a1b3cf16b577566c7644952ac5da0def1d1dc11cc0d0b01c581b9d9f1c`
- evaluator: `b4a4357672ba7d33a908f91635b330b5346defbf8337aeb800e13ffceafd17d7`

## Verification evidence and limits

Root-produced `var/reports/native-client-legacy-wire-proof.json` (SHA256 `12dca2839f71b0b5e006760013379595c2cd81b7cc26e38eb9a2d34a3a70184e`) records 24 exact historical request comparisons: contracts1/2/3 × legacy/modern vLLM dialects × four existing sampling profiles. Its current-client hash matches the reviewed source. I inspected this evidence and the source diff; I did not rerun that comparison.

Root's full actual PostgreSQL/headless IFC regression log `var/phase5x-native-runtime-regression.log` records **376 tests PASS, skip0, 19.473s**, SHA256 `1d069d1136cd5fdc5a2abc6f09084ab07df696c04bc2356ede1269990a234ac5`. The log/hash were independently read; no duplicate full-suite run was performed. My earlier guard verification is separately recorded in `var/research/native_guard_cpu_proof.json`: **57 CPU/fake tests PASS**, original vLLM argv/environment equality for both modes, own CPU same-PID exec/parent-death SIGKILL/core-limit0. These do not establish native CUDA loading, kernels, GBNF/tokenizer parity, placement, resource fit, listeners, latency or quality.

## Cleanup helper follow-up

Reviewed `var/research/cleanup_unused_moe_cache.py`, final SHA256 `6161cc54603ce62a616fc2d03cbb9ddbe44a31eb783a734e962c3b51d4251fac`. **Not executed by this reviewer.** Both previously reported findings are fixed:

1. `/proc/<pid>` is opened as a directory and `fstat` UID is checked before reading contents. Command line, maps and descriptor traversal use relative directory FDs, closing the numeric-PID reuse path into foreign process contents. Permission failures remain failures; disappeared processes may be skipped. No foreign process is signalled or altered.
2. The initial exclusive IN_PROGRESS report is flushed/fsynced and its parent directory fsynced before the first deletion. Subsequent progress reports and affected directories are fsynced. Existing report paths are not silently overwritten at startup.

The operation is restricted to four manifest-pinned, fully hashed, same-UID regular single-link MoE cache shards, under the shared project model lock, with recorded prior STOPPED evidence and per-file inode/size/time rechecks. Metadata/evaluations are retained and the download restoration command is recorded. This is bounded cache removal, not an atomic multi-file transaction: interruption can leave partial progress. The process scan is a point-in-time check, not proof that an uncooperative same-UID process cannot open a file later; root's serial operation and shared guard lock remain part of the execution assumption. This review does not authorize a different cleanup scope.

No remaining material issue found within the reviewed boundaries. Native launch and model-quality gates remain pending, and no model adoption or Phase5.x completion is asserted.

## Guard collision follow-up (same day)

After the transport/cleanup review, model_research identified a separate native-launcher input-preservation bug: a live report could replace a pinned proof stored under `var/reports`. This was fixed in `scripts/llama_server.py` by rejecting report/log collisions with config, binary/model, build/source/header proofs, dependencies and SONAME aliases before output writing or GPU query. Regression cases preserve original bytes and assert zero queries/spawns; the CLI configuration itself is protected before entering the guard.

The updated focused suite is **60 tests PASS, skip0, 2.588s**, recorded in `var/research/native_guard_cpu_proof_v2.json`; the earlier 57-test proof is preserved. The 376-test full regression above describes the prior guard state and must not be cited as a full-suite run after this fix. Root will run the final full regression separately. Client/evaluator/Domain/parser/prompt/schema/gold were not changed by this guard fix.
