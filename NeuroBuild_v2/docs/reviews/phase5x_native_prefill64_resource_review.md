# Native batch64/ubatch64: bounded performance feasibility

2026-09-20. **Conditionally feasible within the retained 28,672MiB planning estimate plus fresh margin.** No concrete new large allocation/OOM path requiring rejection of64 in favor of16/32 was identified. This is source arithmetic, not a measured upper bound, runtime success, speedup promise, candidate adoption, or permission to change a running epoch. This reviewer made no GPU/native/HTTP/model call, read no evaluation bodies, and changed no production source/prompt/policy.

Pinned source: llama.cpp `f072b103714dfa1eee531f80b24512faf38e3dd2`; actual GGUF/header and A100 SM80/CUDA11.8 binary remain the previously verified artifacts. Proposed settings differ only in logical batch64 and physical ubatch64. Context4096, sequence1, all layers on selected GPU3/internal0, fit off, F16 KV, flash off, graphs off, recurrent rollback0, no speculative/MTP/LoRA, no cache/checkpoint expansion remain fixed. The actual build has FORCE_MMQ=OFF, FORCE_CUBLAS=OFF, VMM enabled; this review does not assume a rebuild.

## Persistent memory does not scale with batch

The existing whole-file weight proxy18,094.893MiB + full K/V256MiB + recurrent/conv149.625MiB =18,500.518MiB is unchanged. There is one model/context/sequence, not64 sequences. Rollback0 gives one recurrent state per layer, not64 state snapshots. Existing ubatch1 startup/public aggregate peak18,290MiB is background evidence only and is not used to certify64.

`llama-context.cpp` sets physical tokens to `min(ctx,n_ubatch)` for prefill graph reservation. At64 this is64; decode reserve remains sequence1. `ggml-alloc.c:727–817` counts children/views and frees or reuses temporaries after their last use. Qwen35 is a serial layer/residual inference graph; activations are not saved for a later backward pass. Scheduler reserve replaces old compute buffers rather than retaining a complete copy for each reserve call. Thus multiplying the entire one-token GPU use by64 or summing every layer's maximum temporary as simultaneously live is incorrect.

| F32 tensor / temporary scale (MiB) | ubatch16 | ubatch32 | ubatch64 |
|---|---:|---:|---:|
| One full-attention score plane,4096×24×B | 6 | 12 | 24 |
| One FFN activation,17408×B | 1.0625 | 2.125 | 4.25 |
| Q projection including gate,12288×B | 0.75 | 1.5 | 3 |
| All B logits rows,248320×B | 15.15625 | 30.3125 | 60.625 |
| One fused GDN output + final state | 3.375 | 3.75 | 4.5 |
| All48 GDN outputs, deliberately without reuse | 162 | 180 | 216 |
| Largest quantized MMQ activation,17408×B×144/128 bytes | 0.29883 | 0.59766 | 1.19531 |

These are individual shape calculations, not a summed complete allocator bound. Attention has logits/softmax and layout temporaries, plus F16/F32 cache conversion where needed. At64, two full attention planes are48MiB; Q/K/V/layout/residual tensors add single-digit/tens of MiB. The actual graph2GiB allowance continues to leave substantial room over these concurrent layer-local shapes and the deliberately unreused216MiB GDN tally. Host/device-host output buffers may hold additional sampling arrays; even all64 rows are hundreds of MiB rather than a repeated model or enlarged K/V cache. Driver/kernel-module and allocator uncertainties remain separately budgeted.

## DeltaNet: linear output growth, no64-way state copy

`src/models/delta-net-base.cpp:373–446` chooses fused GDN for multi-token input when `fused_gdn_ch` is supported, and passes **K=1**. `ggml-cuda/gated_delta_net.cu:223–317` uses existing graph output/state tensors and allocates no CUDA pool workspace. Its kernel keeps the state shard in registers and loops over tokens; the output grows as6144×B F32 and final state stays128×6144 F32=3MiB. CUDA's supports-op branch accepts this GDN operation; the kernel handles arbitrary n_tokens with fixed head128 dispatch. No explicit64 limit conflict was found.

If fused placement is rejected, the unfused Qwen GDN branch is non-KDA (`g.ne[0]=1`) and pads to chunk size64. Thus16/32/64 each occupy one64-token chunk, with64×64×48 F32 matrices=0.75MiB each, plus ordinary1.5MiB Q/K/V chunk tensors and3MiB state terms. Choosing16 instead of64 does not reduce those padded chunk dimensions. This is a conservative source contingency, not a claim that the native epoch uses that fallback.

## MMQ, cuBLAS and VMM

`ggml-cuda.cu:1823–1878` dispatches ordinary F32-activation/output quantized matmuls through MMVQ/MMQ before cuBLAS. `mmq.cu:266–334` supports Q4_K/Q6_K/Q8_0 and returns true for compiled Turing-or-newer MMA with sufficient shared memory; the actual SM80 build satisfies that architecture branch. `mmq-config-ampere.cuh` explicitly has J16/32/64 tiles for all three storage types, I=128. FORCE_MMQ=OFF does not imply forced dequantization on A100.

MMQ quantizes activations, not the whole weight. Its largest ordinary activation at64 is1.1953125MiB plus <=64×144bytes tile padding. Stream-K correction is allocated only when tiling does not divide the launch blocks; then the launch uses nSM blocks and requires `nSM×128×J×4` bytes, or32KiB per SM for J64. The source avoids that buffer entirely for exact tile launches. This is a small additional pool term; no GPU SM-count query was made here.

The cuBLAS fallback remains compiled for dtype/layout cases and attention operations. The largest possible F32 weight conversion is still output5120×248320=4,850MiB, independent of B. B64 adds1.25MiB F32 activation and60.625MiB output (F16 conversion30.3125MiB where required), covered by the separate pool/workspace allowance, not silently subtracted from the weight term. Attention cache conversion is much smaller than this matrix. No concurrent copies of every decoded layer weight are implied.

The exact compiled/device VMM route and2MiB granularity remain bound. With graphs OFF and one device, the inspected compute path uses one stream/pool. VMM retains its **largest simultaneous high water**, so previous smaller matmul buffers do not require summing all layer dequant sizes. Graph buffers are separate and are already budgeted separately. VMM's32GiB virtual reservation is neither physical use nor a process cap.

## Decision and next evidence

Retain `18095+256+150+4850+2048+1024+1024+1225=28672MiB` as a conservative **estimate** for this exact64/64 candidate. Graph2GiB, driver/module/handles1GiB, extra pool/rounding1GiB and uncertainty1225MiB are still explicit allowances; source arithmetic has not replaced them with a false mathematical bound. Existing VMM/library/allocator assumptions must remain unchanged. Fresh GPU3 measurement must still satisfy estimate+margin, and the aggregate watchdog remains necessary but is not isolation or spike prevention.

16/32 have smaller attention/linear-activation footprints as shown, but no current evidence makes64 infeasible while those are safe. A separately recorded64/64 candidate is therefore the direct bounded performance test; no automatic fallback/fit or silent candidate switch is justified. It needs new explicit config/consumer/source evidence, startup and maximum-context public resource testing before any quality freeze. Previous2/1 reports remain historical.

Performance is unmeasured. For2143 prompt tokens, the physical prefill calls decrease from2143 at ubatch1 to134/67/34 at16/32/64; for3328 tokens,64 requires52 physical prefill batches. Larger matmuls and fewer host/kernel dispatches are a concrete reason to test the change. GDN still has an internal token loop, and autoregressive decode still uses one token, so neither64× speedup nor the prior55.055s public latency scales by a guaranteed factor. Sampling numerics/outputs may also differ; frozen schema/parser/gold/raw-FP/semantic gates remain mandatory.

Primary source references are the pinned repository paths above, plus `src/llama-graph.cpp:build_attn_mha`, `src/models/qwen35.cpp`, `ggml/src/ggml-cuda/mmq.cuh:1398–1455`, and `ggml/src/ggml-cuda/common.cuh:turing_mma_available`. All were read from the bootstrap-verified local source; no current-main assumptions or weight decoding were used.
