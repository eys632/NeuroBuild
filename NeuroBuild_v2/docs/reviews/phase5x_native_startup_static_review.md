# Qwen3.8 native epoch 1: static diagnosis

This is a source review, not a captured assertion or GPU reproduction. Epoch 1 report records SIGABRT (-6), 7.781 s, baseline-relative aggregate peak 18,290 MiB, minimum free 18,084 MiB, ready=false, child reaped. No HTTP/model requests were made in that epoch. No code, model, runtime configuration, private dataset, or GPU was changed by this reviewer.

## Concrete startup conflict

At pinned llama.cpp `f072b103714dfa1eee531f80b24512faf38e3dd2`:

- `common/common.h:371,394–400`: speculative default NONE makes `need_n_rs_seq()` zero; `common/common.cpp:1723` transfers it to context parameters.
- `tools/server/server-context.cpp:1240` unconditionally calls `common_context_can_seq_rm(ctx_tgt)` while loading the server.
- `common/common.cpp:1583–1627`: with a memory module and zero rollback slots, that function submits exactly two tokens in a single `llama_decode` call. It does not clamp to logical batch size.
- `src/llama-context.cpp:1734`: `GGML_ASSERT(n_tokens_all <= cparams.n_batch)` fails for 2 > 1 before physical microbatch splitting.
- Warmup is different: `common/common.cpp:1535` clamps its token count with `min(tmp.size(), params.n_batch)`. It may finish before the later two-token check aborts.

This is a definite incompatibility if startup reaches this check, and a strong candidate for the observed SIGABRT. It does not establish that the actual epoch reached that line: bounded sanitized filename/line diagnostics must confirm or identify an earlier failure. Flash attention, CUDA version, and gated-delta assertions should not be changed speculatively. Public upstream issue searches found other-backend/fork reports, not evidence tying this exact epoch to an alternative bug.

Pinned primary source: [seq_rm check](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/common/common.cpp#L1583), [server startup](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/tools/server/server-context.cpp#L1240), [decode assertion](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-context.cpp#L1734).

## Conditional minimal variant: logical batch 2, physical ubatch 1

After diagnostic confirmation, this removes the identified 2 > 1 conflict without increasing concurrency or context length. It is a recommendation only; the reviewer did not implement or execute it.

- `src/llama-context.cpp:241–243`: `n_ubatch=min(n_batch, requested_ubatch)` stays 1.
- `src/llama-context.cpp:594–596`: reserve token count remains `min(ctx, n_ubatch)=1`; `graph_max_nodes(1)` and one-token physical graph shapes stay fixed.
- `src/llama-memory-hybrid.cpp:67–102`: the two logical tokens become sequential single-token microbatches. Speculative NONE means no additional recurrent rollback snapshots.
- Weights, seq1, ctx4096 KV allocation, F16 cache, flash-off, and graph-disable settings are unchanged. The source does not use `n_batch` to size the fixed hybrid memory module.
- `src/llama-context.cpp:2057–2143`: logical output IDs grow by one. If an additional output row is requested, F32 logits add 248,320 × 4 = 993,280 bytes (0.9473 MiB); backend sampling output arrays can add a few more MiB. This output buffer selects CPU/device host buffer memory, not a second model or a doubled KV cache. Normal last-token-only output may still reserve one row.

This supports a small resource delta, not a measured peak or an allocation guarantee. Retain the full 28 GiB estimate, fresh permitted-GPU baseline/free margin and watchdog. Warmup now processes two tokens through two microbatches; seq_rm then evaluates two tokens and clears memory. No prompt/input normalization, sampling, representation or quality gate changes follow from logical batch 2. Semantic and bitwise equivalence are not claimed.
