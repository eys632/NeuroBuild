# EXAONE 4.5 33B: independent native feasibility review

Status: **conditional source-only candidate plan; not adopted, not runtime validated**. This review used pinned official metadata and the already-verified local llama.cpp source/build. It did not execute a native binary, compile, invoke CUDA/GPU, query a model HTTP endpoint, download weights, install packages, or inspect evaluation outputs. Production files and prior proofs were unchanged. Arithmetic and exact input/source hashes are in `exaone45_native_feasibility_numbers.json` (SHA256 `ffea32e0db61e65a3ff321b7505afde19d8c588671a675b68293b37f10024dc8`).

## Verdict and gates

No new architectural or CUDA11.8/SM80 source blocker was found for the text-only EXAONE4 path in pinned llama.cpp `f072b103714dfa1eee531f80b24512faf38e3dd2`. A **28,672 MiB aggregate-rise planning envelope** is plausible for ctx4096/seq1/batch64/ubatch64, F16 K/V, flash attention OFF, CUDA graphs OFF, all requested decoder layers on masked GPU3. This is a budget for a bounded experiment, not a derived worst-case allocation bound. Several allowance rows below are engineering reserves, not independently measured requirements.

Current execution blockers remain: the metadata agent's disk snapshot fails the 20.5 GiB download reserve; actual GGUF/header/storage types/tokenizer are not inspected; model-specific CPU template/tokenizer/schema/context verification and explicit request-profile integration are pending. After those gates, a fresh GPU preflight plus guarded startup/public-wire/max-context resource probes are still required. No inference, quality, throughput, or RTX claim follows from this review.

## Exact candidate and loader path

The official artifact is `LGAI-EXAONE/EXAONE-4.5-33B-GGUF`, revision `0e969634ef24db05151b435970297a6dee634b7e`, file `EXAONE-4.5-33B-Q4_K_M.gguf`, **20,047,839,424 bytes**, LFS SHA256 `5ba3839b67dcee5618ea7b2206cedc8f9e2ec90fbcec3c95a8cc8b33967f6baf`. Its filename is not evidence of every tensor's quantization type. The metadata-only download manifest additionally includes the official README and LICENSE; total 20,047,878,049 bytes.

Upstream revision `570aa4b15a4f45ba1133072b45f50198f6e3b4fd` declares `Exaone4_5_ForConditionalGeneration`: hidden5120, FFN27392, 64 decoder layers plus one MTP layer, heads40/KVheads8/head_dim128, vocab153600, untied embeddings, and LLLG sliding/global attention. Config specifies sliding_window4096 while the card lists128. Use4096 conservatively until actual GGUF metadata is inspected. This review excludes the separately distributed vision projector and vision requests.

Local pinned source anchors:

- `conversion/exaone.py:219–272` maps this exact architecture's text tower to EXAONE4, preserves optional MTP tensors, and records nextn metadata.
- `src/models/exaone4.cpp:24–71` loads ordinary QKV/output, Q/K norm, dense SiLU FFN, post norms and optional rope tables. MTP tensors receive `TENSOR_SKIP`; its graph uses the 64 main layers. If the output matrix is absent, the loader can duplicate embeddings: actual tensor inventory must verify the official untied-output assumption.
- `src/llama-model.cpp:2676–2680` excludes nextn layers from the normal context cache; `:2720` passes that filter to ISWA. `src/llama-kv-cache-iswa.cpp:51–66` preserves the filter for sliding and global caches. Expected normal KV is therefore64 layers, not65. The plan keeps an extra16 MiB anyway.
- `src/CMakeLists.txt:9` includes model sources, and the preserved build's `src/CMakeFiles/llama.dir/Unity/unity_2_cxx.cxx:15` contains `models/exaone4.cpp`. No rebuild requirement was identified.
- `ggml/src/ggml-cuda/mmq.cu:266–334` supports ordinary Q4_K/Q6_K paths and SM80 tensor-core MMQ selection. `ggml-cuda.cu:1823–1878` chooses quantized MMVQ/MMQ or a cuBLAS conversion path according to layout/dtype. No new FP8, Blackwell, or CUDA12-only requirement is inherent in these declared shapes. Actual GGUF types remain a gate.

## Whole-memory planning arithmetic (MiB)

| Component | Plan | Evidence or limitation |
| --- | ---: | --- |
| Entire GGUF, rounded upward | 19,120 | Actual remote file is19,119.109558 MiB; counts even inactive MTP/CPU-held portions conservatively. |
| F16 K and V, 65 full4096 layers | 1,040 | `65×4096×8×128×2×2 / 2^20`; normal64-layer expectation is1,024. SW4096+ubatch64 clamps to4096 then pads256. |
| Largest single F32 matrix expansion | 3,000 | `153600×5120×4 / 2^20`; largest FFN matrix is535 MiB. |
| Graph/intermediate allowance | 2,048 | Planning reserve; not a measured or proven graph allocation bound. |
| Driver/modules/handles allowance | 1,024 | Planning reserve; common build/driver provenance can be reused, per-model residency is unmeasured. |
| Pool/workspace/alignment allowance | 1,024 | Additional to the3,000 MiB maximum matrix conversion above; planning reserve. |
| Loading/fragmentation/unresolved allowance | 1,416 | Remaining explicit contingency inside the proposed whole budget. |
| **Total planning envelope** | **28,672** | **No allowance outside this whole estimate is assumed.** |

At the historical reference free36,373 MiB, `margin=max(6144,ceil(0.20×36373))=7275`, so available29,098 MiB. Plan28,672 leaves426 MiB below that available budget; predicted remaining free is7,701 MiB. Those are arithmetic on a reference snapshot, not fresh capacity claims. Native runtime has no Torch allocator cap. Aggregate sampling/free-floor shutdown cannot prevent every sub-interval transient peak or isolate other users' allocations.

The layer dimensions make the reserves plausible: at ubatch64 one F32 attention score plane is40 MiB (two80), one FFN activation6.6875, QKV1.75, and all64 vocabulary logits37.5. These examples do not enumerate the entire execution graph. cuBLAS conversion allocates src0 plus activation/src1 and possibly output scratch (`ggml-cuda.cu:1441–1534`); include both the largest weight expansion and the separate scratch reserve. The VMM pool's LIFO free reduces `pool_used` while retaining mapped physical highwater (`:535–691`), so sequential decoder layers do not imply64 retained complete dequantizations. Its32 GiB virtual-address reservation is neither an up-front32 GiB physical allocation nor an application cap. Graphs OFF avoids the concurrent-branch optimizer/pool multiplication considered in prior common-runtime review. This rationale depends on preserved single-device/VMM/graphs-OFF configuration, verified build, and actual supported tensor layouts; it is not a proof that any possible checkpoint will remain below28,672.

## New model-specific work, with common safety unchanged

1. Header audit must bind exact whole-file SHA, sizes, architecture, block/nextn metadata, SWA/heads/rope, separate output and embedding tensors, all shapes/storage types, tokenizer pretype, and embedded template. Update the memory estimate if actual metadata differs. Keep the existing GPU3 UUID/count bootstrap, own-child/process-group lifecycle, core dumps disabled, loopback-only sockets, fresh preflight/watchdog, explicit no-fit/no-offload capacity fallback, and stdout/stderr discard.
2. Add a named EXAONE native request profile and exact model/quantization tuple; do not select it by response or silently reuse Qwen/Gemma settings. The card recommends T0.6/top_p0.95/top_k20/presence1.5 for Korean, with a distinct text-only T1/top_p0.95 recommendation. Choose and freeze one explicitly. **Presence1.5 alone would currently be ineffective:** the Qwen/Gemma native chain omits `penalties` and sets repeat_last_n0. `common/sampling.cpp:380` constructs penalties only when requested, and `src/llama-sampler.cpp:2920` records no history for window0. If following presence1.5, declare penalties position and a nonzero window, and verify prompt/history semantics. Neutral penalties are a possible explicit experiment, but must not be labeled the full Korean recipe.
3. Official template defaults thinkingtrue. Explicit nonthinkingfalse creates an empty `<think>` segment in the assistant prefix. EXAONE uses the generic chat autoparser in `common/chat.cpp:1223–1365`; a new CPU fixture must prove final-content/schema binding, empty reasoning handling, marker rejection, and one-call production payload without retries or text repair. Preserve3→2→1/2→1 application semantics and existing gold/gates unchanged. No guarantee follows merely from supported architecture.
4. New official tokenizer ID/roundtrip and model-aware template/context gates are required. Upstream tokenizer has NFC+BPE and an EXAONE-MOE-style regex. `src/llama-vocab.cpp:2320` maps GGUF pretype `exaone4` to GPT2, while `exaone-moe` selects its explicit regex at:521. Only the actual GGUF can identify which lineage is present; neither equivalence nor failure is established yet. Do not inherit Qwen's raw-Unicode experimental variant or normalize application source/evidence. Check BOS and pinned Jinja source normalization separately from embedded-template bytes.
5. After CPU gates and fresh resource checks, reuse the common resource-probe method with this model's proven ordinary token and full4096 occupancy, then measure actual lifetime aggregate peak. Startup/template/resource attestations must carry new model/header/profile identities. Shared binary/build/driver proofs can remain historical and explicitly labeled; old models' resource/quality results cannot establish this candidate's behavior.

## Disk and license boundaries

The metadata agent recorded free28,136,112,128 bytes before any cleanup; downloading the20,047,878,049-byte manifest would leave8,088,234,079 bytes, below the22,011,707,392-byte (20.5 GiB) reserve. The shortfall is13,923,473,313 bytes. This review performed no deletion or download and does not treat that recorded snapshot as current free space.

The pinned official **EXAONE AI Model License Agreement1.2-NC** allows specified research/educational activities and restricts commercial use, including outputs, while separate permission is needed for uses beyond its terms. Root has identified this investigation as internal noncommercial research. This is a scope observation, not legal advice or a commercial-deployment clearance; preserve the license, attribution and provenance, and do not describe the candidate as permissively licensed.

Primary references: [official pinned config](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B/blob/570aa4b15a4f45ba1133072b45f50198f6e3b4fd/config.json), [official pinned GGUF card](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B-GGUF/blob/0e969634ef24db05151b435970297a6dee634b7e/README.md), [official pinned license](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B-GGUF/blob/0e969634ef24db05151b435970297a6dee634b7e/LICENSE), [pinned converter](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/conversion/exaone.py), [pinned model](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/models/exaone4.cpp).
