# Native whole-VRAM budget: independent source review

2026-09-20. **CPU/source arithmetic only; no native executable, CUDA/driver call, model inference, download, or v2 body read.** Fixed llama.cpp `f072b103714dfa1eee531f80b24512faf38e3dd2`; Qwen3.8-27B Q4_K_M GGUF revision `efbb3b1f70a21d97fd4495240648405f7228554f`. This review does not adopt the candidate or authorize a launch.

**Conclusion:** 28 GiB (28,672 MiB) is a plausible conservative *planning budget* for the fixed one-token compute path, but the evidence does **not** establish a complete upper bound below it. During this review, the parent independently verified GPU3 VMM support without creating a context/allocating memory, and this reviewer verified the final binary contains the VMM implementation. Thus the current candidate uses a single VMM high-water pool; the legacy-cache stress scenarios below are contingencies, not the selected pool. The proposed `18,500.518 + 4,850 + 5,321.482` arithmetic still omits whether its last allowance actually covers graph allocations, driver/modules and fragmentation. Do not describe this budget as measured peak, hard cap, or unconditional FIT/PASS. The missing evidence and conditional calculations below are explicit.

## Fixed execution assumptions and actual build

One physical GPU3 masked as CUDA0, one server context/sequence, context4096, batch1/ubatch1, F16 K/V, F32 recurrent state, speculative rollback0, no draft/MTP/LoRA/embedding endpoint, all requested layers on that GPU, fit OFF/context-shift OFF, ordinary prompt checkpoints0/cache-RAM0/idle-slot cache OFF. No automatic reduction of these settings is allowed to make the model fit.

The actual post-relink `CMakeCache.txt` says **GGML_CUDA_FORCE_MMQ=OFF**, `GGML_CUDA_GRAPHS=OFF`, `GGML_CUDA_NO_VMM=OFF`. Earlier hypothetical MMQ=ON notes are not evidence for this binary. CUDA architectures are SM80-real and the verified build uses CUDA11.8. The launcher must continue removing inherited GGML/CUDA allocator/compute/device overrides.

Graphs OFF matters beyond avoiding capture memory: `ggml-cuda.cu:4529–4555` makes graph optimization return when `use_cuda_graph=false`. The only assignments away from `curr_stream_no=0` are the corresponding concurrent-event evaluator paths. Thus the inspected single-backend compute path uses one stream/pool, not eight active pools merely because `GGML_CUDA_MAX_STREAMS=8`. Loader upload contexts may own a separate copy stream, but the inspected upload path does not run matmuls or create a second dequant pool. Single GPU also disables model pipeline parallelism (`llama-context.cpp:428`). This is source evidence, not observed device initialization.

## Persistent baseline and graph scope

| Component | Calculation / basis | MiB |
|---|---|---:|
| Weight proxy | Entire pinned GGUF file, 18,973,870,528 bytes | 18,094.8930 |
| Full-attention F16 K+V | 16 × 4096 × 4 KV heads × 256 × 2 × 2 bytes | 256 |
| Recurrent F32 S | 48 × 128 × 6144 × 4 bytes | 144 |
| Recurrent F32 convolution R | 48 × 3 × (6144 + 2×16×128) × 4 bytes | 5.625 |
| **Subtotal** | Seq1, speculative rollback0 | **18,500.5180** |

The public conversion log has 851 tensors. Its tensor payload plus CUDA128 alignment is 18,962,882,560 bytes; quantized first dimensions are multiples of512, so the inspected row-padding formula adds no rows for these shapes. The file proxy includes about10.48 MiB above logical payload and is a reasonable weight estimate **pending actual downloaded header/placement verification**. It is not an attestation that every CUDA weight allocator overhead fits in that difference. Token embeddings can have a different placement, but this estimate does not subtract them.

`llama-memory-recurrent.cpp:101` allocates `rows=mem_size*(1+n_rs_seq)` and hybrid allocation selects F32 R/S with `mem_size=max(1,n_seq_max)` (`llama-model.cpp:2634`). Thus rollback0 does not multiply recurrent state by the context length. Host serialized prompt checkpoints are a different mechanism and are disabled here.

Graphs OFF does **not** mean compute buffers OFF. Context startup reserves full-context prefill/decode graphs (`llama-context.cpp:582–699`), then keeps their allocator high water. `ggml-alloc.c:925–944` frees an old compute buffer before replacing it; reserve calls do not deliberately keep three complete old/new graph buffers. However, a fused-GDN support probe uses **16 tokens** even with user ubatch1 (`llama-context.cpp:53–56,512`), so startup graph planning cannot be described as exclusively one token. Probe graph reservation checks placement; it does not itself execute all16-token kernels.

Useful scale checks, not a graph upper bound: one batch1 fused DeltaNet output including final state is3.0234375 MiB; all48 such outputs sum145.125 MiB before lifetime reuse. One full-attention score plane at4096×24 F32 is0.375 MiB; one logits row is0.9473 MiB. At the16-token graph probe these are6 MiB and15.15625 MiB for score/logits, and one fused-GDN output is3.375 MiB. Other residual, normalization, conv, repeated Q/K, unfused delta and layout-copy tensors still need graph-allocation accounting. CPU backend buffer sizes must not be passed off as CUDA graph sizes.

## Quantized matmul and large temporary shapes

`ggml-cuda.cu:1823` first rejects unsuitable dtype/view-padding combinations to cuBLAS, then selects MMVF/MMF/MMVQ/MMQ. `mmvq.cu:318–415` selects MMVQ for the supported Q4_K/Q6_K/Q8_0 weights at A100/ne11=1; F32 activations and F32 output satisfy the normal quantized path. It quantizes the *activation* to a small Q8_1 temporary rather than fully dequantizing the weight (`mmvq.cu:1485`). Therefore huge weight conversion is **not the expected batch1 path**, even with FORCE_MMQ=OFF. Actual header, graph dtype/stride and supported dispatch remain required before treating this as runtime evidence.

Fallback remains compiled. `ggml_cuda_mul_mat_cublas_impl` converts all of src0 when its storage differs from compute dtype, with src1 conversion and sometimes output conversion alive at the same time (`ggml-cuda.cu:1441–1519`). On A100 a quantized normal fallback defaults to F16; explicit F32 precision or an environmental override changes this. We retain F32 as a stress calculation without asserting the output layer actually requests it.

| Weight shape class (GGML order) | Example / count | F16 MiB | F32 MiB |
|---|---|---:|---:|
| 5120 × 248320 | Output Q6_K; embedding has same shape but normal lookup does not dequantize its whole matrix | 2,425 | 4,850 |
| 5120 × 17408 or transpose | FFN up/gate/down,192 matrices | 170 | 340 |
| 5120 × 12288 | Full-attention Q,16 | 120 | 240 |
| 5120 × 10240 | DeltaNet QKV,48 | 100 | 200 |
| 5120 × 6144 or transpose | Gate/output,112 | 60 | 120 |
| 5120 × 1024 | Full-attention K/V,32 | 10 | 20 |
| 5120 × 48 | DeltaNet alpha/beta,96 | 0.46875 | 0.9375 |

Repeated layers do not imply repeated complete dequant copies are live. Operations share a pool and do not retain a private decoded weight per layer. Conversely, adding only the maximum shape does not bound the legacy pool.

## VMM versus legacy retained pool

`ggml-cuda.cu:535–690` selects VMM only if compiled support **and** `CU_DEVICE_ATTRIBUTE_VIRTUAL_MEMORY_MANAGEMENT_SUPPORTED` are true. Both are now established for the exact candidate: all143 CUDA compile units omit the VMM/HIP exclusions, `common.cuh:263–265` defines GGML_USE_VMM, and read-only `nm -D -C` on the verified CUDA library finds `ggml_cuda_pool_vmm::alloc/free/vtable` and the cuMemCreate/Map/AddressReserve imports. Parent report `var/reports/gpu3-vmm-capability.json` SHA `df019ecec2d0f07227be3612445d4893f793bd1d79af487b7eddb64795c0e2d6` records UUID-checked GPU3/internal0, one visible device and VMM=true; no context, allocation or native llama execution. The checked library is `bin/libggml-cuda.so.0.24.0`, SHA `8f1ff9d231592d3812b03d87bb146f2b130b9ea39843e577706562dbc1291c26`. This review itself made no driver call.

The32 GiB constant reserves virtual address space, not32 GiB of immediate physical memory and not a process-wide cap. Physical pages grow to the maximum simultaneous pool use, rounded to the queried recommended granularity. `free()` only decrements a LIFO position; it retains physical pages. Under a one-stream sequential matmul path, earlier smaller weight conversions share that retained high water. One F32 output conversion gives roughly4,850 MiB plus concurrently live activation/output/pointer buffers and granularity, **not** the sum of every layer's weights. VMM allocation/API failure aborts via CU_CHECK; this source does not silently catch it and switch to legacy. A different binary/device/capability result invalidates this selected-path argument. Actual granularity was not included in the parent's capability-only report and remains an unmeasured rounding term.

The legacy pool (`ggml-cuda.cu:418–530`) keeps up to256 free allocations, takes best-fit cached buffers, and allocates `ceil256(1.05*requested)` when none fits. It flushes cached buffers only after an allocation OOM; an OOM-triggered retry is not acceptable budget protection. Multiple increasing sizes remain cached. Pool entries can also be consumed by activation temporaries, and distinct compute dtypes can leave different retained allocations.

Illustrative conservative shape-cache scenarios (these are **not** proofs of exact lifetime or total allocation maxima):

| Scenario | Persistent + weight-conversion cache MiB | Remaining below28 GiB |
|---|---:|---:|
| VMM / one largest F32 conversion, before other live buffers/granularity | 23,350.5180 | 5,321.4820 |
| Legacy / one allocation per distinct F32 weight size, each +5% | 24,560.0024 | 4,111.9976 |
| Legacy stress / one per distinct F16 **and** F32 size, each +5% | 27,589.7446 | 1,082.2554 |

The legacy unique-F32 sizes sum5,770.9375 MiB; +5% gives6,059.484375 MiB (256-byte rounding adds less than2 KiB for these seven sizes). The mixed-dtype illustration is9,089.2265625 MiB before rounding. It deliberately overcounts possible cache reuse and is not asserted reachable for this fixed graph, but demonstrates why the residual5,321 MiB cannot simply be called a sufficient universal allowance. Generic pool operations/multiple simultaneously borrowed buffers prevent claiming even these illustrative totals are rigorous whole-pool upper bounds without a full allocation trace.

One Ampere cuBLAS handle has an explicit4 MiB workspace in `common.cuh:1540–1552`; library handle/module/context allocation is additional. CUDA kernels/driver mappings, graph buffers, alignment/granularity and external fragmentation have no project-enforced native per-process hard cap. MMQ force would not remove these costs or the initial dtype/view fallback.

## Decision boundary before launch

28 GiB leaves **7,701 MiB** of the historical36,373 MiB free, only426 MiB above a7,275 MiB reserve. This is arithmetic on a past snapshot, not a current resource check. A polling watchdog can terminate observed excess, but cannot prevent a short allocation spike or another user's contemporaneous allocation. Do not infer isolation from it.

To substantiate a28 GiB planning budget: verify the actual GGUF header/quant layout and final launch settings; retain the established VMM binary/device binding and determine allocation granularity; account for the startup16-token support-probe graph as well as full-context batch1 graph; and obtain a bounded observed model/context/compute/pool and process-memory peak covering loading, maximum-length prefill, first decode and repeated requests. Actual runtime observations must be made only by the root's authorized fresh-GPU guard after remaining CPU gates; this memo performs none. If a pre-launch certified whole-peak bound is required, current static evidence is **insufficient**, and a guarded observation must not be relabeled as that certification.

The defensible current result is **conditional feasibility, whole-peak upper bound unverified**. Current evidence supports investigating28 GiB; it does not establish FIT/PASS, permit retaining only the original4,850 MiB buffer term, transfer the budget to RTX5090, or bypass the policy/quality gates.

## Reproducible source snapshot

All reads use the bootstrap-verified pinned source. Official paths are `https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/<path>` with the line locations above. No current-main assumptions were used.

- `ggml/src/ggml-cuda/ggml-cuda.cu`: `af947e45946d0c47cfae9e056f589a25b61892e4273decf0a893e2dcad48d065`.
- `ggml/src/ggml-cuda/common.cuh`: `a210a71f965419ab55cce071b900df118c2520c1566ea5e068d8be07805644a2`.
- `ggml/src/ggml-cuda/mmvq.cu`: `d4c70f68ab79d463fd6fd52cac66a62e915858397ba4b2b7f658a7fbf13121f3`.
- `src/llama-context.cpp`: `9f246c4f7268d1438c3e6f4a544cd497feffe777095eeaa1606a24a3d2f07008`.
- `ggml/src/ggml-alloc.c`: `213b48d6ef6d6ffef55c438db837116105de72cdae3dd152673035e61508d384`.
- Public conversion metadata `var/research/qwen38-candidate-metadata/template_and_conversion_provenance.json`: `3cf9d3ceab25e02b24373f0c7e0929b1e7fcea7eb2f511be9280bfbdb506a4bd`.
- Actual post-relink `CMakeCache.txt`: `c456e964f4bf310932fb8ace22a06ed69bf8980819f0fdbe634c2d558e5ab001`.

Parallel task historical handoff: this agent repinned the CPU contract runner to CPP `19921771c0f559268868d01ec5327ab859e35c379e727841cb11b6d58a82bb42`, runner SHA `e88d840d669df2762db823de914739efb31c345743201aea1b090886babe7f2e`. Fourteen pure CPU cache/pin regressions passed. The parent's subsequent compile found a common_json comparison compilation error in that CPP; model_research now owns its correction and same-directory resume runner. This agent has stopped editing those helpers and did not execute their main/build/validator paths.

## Follow-up: actual header/granularity and proposed startup estimate

The later parent-run `var/reports/gpu3-vmm-granularity.json` (SHA `6f2a34f83dcb284de6ed8451dac4e2268e60102ae381a47146d3ca2e22bb8033`) is PASS with recommended granularity **2,097,152 bytes =2 MiB**, the same UUID-checked one visible GPU3/internal0, no context/allocation/native model, and unchanged36,373MiB free. This resolves the previously pending VMM rounding input; this reviewer only read the resulting report.

The actual downloaded GGUF report `var/reports/qwen38-gguf-header.json` SHA `ff168aeee125b2934b8b5204c14971915c7555c5dfc660d6fda46c2bf7fc810a` is PASS: full-file bytes/SHA match the fixed artifact; all851 tensors match public shape/type metadata; packed payload18,962,876,416 bytes, header/data offset10,994,112 bytes, zero on-disk padding, known metadata bindings and expected dtype counts. It does not prove decoded tensor numeric validity. This supersedes the earlier “actual header pending” qualification without changing the persistent/dequant arithmetic.

Independent review of the parent's `docs/native_qwen38_resource_plan.md`: `18095+256+150+4850+2048+1024+1024+1225=28672 MiB` exactly. In addition to persistent state and a full F32 output conversion, it explicitly budgets graph2GiB, driver/context/modules/handles1GiB, additional pool/alignment1GiB and uncertainty1,225MiB. The initial16-token GDN graph reservation and the distinction between whole GPU change versus per-process peak are stated. With the actual one-stream VMM path and verified shapes, **no concrete unaccounted large allocation or source evidence of inevitable OOM was found**. These allowances are estimates, but they are not a weight-only guess or reliance on legacy-cache flushing.

Verdict under the user's required **estimated whole peak + fresh margin** policy: the proposed28GiB estimate is reasonable for a bounded first startup **after** remaining CPU gates, exact input/settings checks and fresh GPU3 guard authorization. Mathematical certification is not an additional user requirement. This verdict preserves the stated uncertainty, sampled-watchdog limitation and sequential startup/public-resource-probe/quality-gate separation; it is not a runtime success claim. No different GPU, automatic fit, context/batch change or semantic-gate exception is covered.

The corrected same-directory CPU build also passed independent read-only evidence review: `var/reports/llama-native-contract-cpu-build-v2.json` SHA `ccb6a99305f9a62c1e2f9d1572380e428d20341a73f5dd65af4222f8b850aa36`, status COMPILE_PASS_NOT_EXECUTED, all8 input hashes and4 immutable prior-failure hashes match;194 reused upstream object/archive files are unchanged;3,607 source blobs before/after match; the resume child exits0 with own-process cleanup complete. Binary SHA `142e5ed957ced9b83a4389d77d79cdd518c79859bae24f2988913be914e0d32e` matches, and this reviewer's static readelf shows only ordinary system C/C++ dependencies and no CUDA/RPATH entries. This is build evidence; the parent's separate CPU grammar/tokenizer invocations are not attributed to this reviewer.
