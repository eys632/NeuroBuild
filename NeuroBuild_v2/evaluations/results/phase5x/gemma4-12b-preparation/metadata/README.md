# Gemma 4 12B QAT: pinned metadata and conditional native feasibility

2026-09-20 UTC. Metadata-only preparation; **no weight/header/native/GPU/model evaluation**. No package installation, cache cleanup, tokenizer encode/decode, template render, or evaluation input/result access was performed. The parent owns any later download and execution decision.

## Conclusion

The pinned metadata presents no clear architecture/resource blocker for the existing `llama.cpp@f072b103714dfa1eee531f80b24512faf38e3dd2` text-only runtime. This is conditional source analysis, **not a successful 12B load, tokenizer contract, peak measurement, or quality result**. A native rebuild is not justified solely by the currently observed metadata.

`candidate_download_manifest_draft.json` uses the existing downloader's two-file format: pinned official README plus one text-model GGUF. It is a draft in ignored research storage, not an authorization or a tracked production manifest. The mmproj and all unquantized/drafter weights are excluded.

## Official identity, lineage and license

| Artifact | Pin |
| --- | --- |
| GGUF repository | `google/gemma-4-12B-it-qat-q4_0-gguf@29d097773436b69ff9feafd636ab4cf873786537` |
| Selected file | `gemma-4-12b-it-qat-q4_0.gguf`, 6,975,879,296 B |
| Published LFS SHA256 | `93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b` |
| QAT reference source | `google/gemma-4-12B-it-qat-q4_0-unquantized@b6ed86275a6a5735884e208bfed95b445a684ca2` |
| Original IT comparison | `google/gemma-4-12B-it@707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7` |
| QAT config SHA256 | `a323d02f68420f6fa3a3548130a0d36356075a4047a622e57148558f8eee7077` |

The pinned [GGUF card](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf/blob/29d097773436b69ff9feafd636ab4cf873786537/README.md) declares the QAT source repository; its card declares original IT. Neither inspected metadata publishes the exact source revision or converter revision that produced the GGUF. There is no conversion log or safetensors index in the inspected QAT repository; its single safetensors payload was not requested. Do not infer an exact tensor inventory from the 31B index.

The pinned GGUF commit title mentions corrected vocabulary and “280 sequence length.” That title is preserved in `gguf-commits.json`; it does not establish a text context limit of 280 or prove equality with current source tokenizer metadata. The reference config states 262144 positions, while this project would use 4096. Actual GGUF fields remain a required check.

All three pinned APIs/cards declare Apache-2.0. There is no standalone repository LICENSE in their file inventories. Google's [linked license page](https://ai.google.dev/gemma/docs/gemma_4_license) and the canonical Apache text are preserved under `official-license/`; the latter is not misrepresented as a repository file.

## Differences from the existing 31B path

12B uses `Gemma4UnifiedForConditionalGeneration`, 48 layers, hidden3840, FFN15360, vocabulary262144. Its 40 sliding layers have 8 KV heads ×256 and its 8 full layers have 1 KV head ×512. Sliding window1024, tied embeddings, zero shared-KV layers, zero per-layer embedding dimension, no MoE and no double-wide MLP agree with the ordinary dense path. The unified vision/audio metadata is irrelevant to this text-only scope; no projector is selected.

`conversion/gemma.py:812–830` explicitly registers Unified for `GEMMA4`; its inherited converter and `src/models/gemma4.cpp` use generic arrays/shapes. The size-label switch at model lines27–33 lacks 48 layers and gives `LLM_TYPE_UNKNOWN`. In this path that label is descriptive; the inspected loader/graph has no 31B-type condition. This absence is not proof that every future 12B GGUF tensor will load. Actual architecture, dimensions, tensor roles, types, packing and RoPE remain unknown until the artifact is inspected.

The downloaded official tokenizer is **byte-identical** to prior 31B QAT (32,169,626 B, SHA `cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f`). Original 12B IT has the same pinned LFS metadata. Both 12B templates are byte-identical to prior 31B (18,683 B, SHA `ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4`). Tokenizer config changes to `Gemma4UnifiedProcessor` and removes redundant prior auxiliary keys; the explicit special-token names and response parsing contract remain present.

The same tokenizer's space→U+2581 normalization and inverse decoder retain the prior literal-U+2581 limitation. No new encode/decode was performed and no all-Unicode preservation claim is made. Existing 31B witness/proof bytes remain unchanged.

Official sampling remains temperature1.0/top_p0.95/top_k64. Neutral penalties, min_p0, repeat window0, seed42 and explicit sampler order are **project choices**, as before. New official `generation_config.json` additionally suppresses IDs258883 and258882. `conversion/gemma.py:817–830` writes this list; `src/llama-vocab.cpp:2660–2677` reads the INT32 array and `common/sampling.cpp:325–337` adds -infinity biases. Future header inspection must verify `tokenizer.ggml.suppress_tokens` and both IDs. Reusing the 31B HTTP profile does not make the effective sampler identical if these model-owned biases differ.

## Conditional whole-resource plan

`resource_plan.json` binds local source hashes and the arithmetic. With context4096, sequence1, batch/ubatch64, F16 K/V, flash OFF and CUDA graphs OFF, ordinary padded SWA uses464MiB (400 sliding +64 global). The deliberately larger full4096 K/V estimate is1344MiB. Largest vocabulary-output F32 expansion is3840MiB; largest FFN weight expansion225MiB. Input embedding remains CPU and the tied output is GPU; counting the whole GGUF as a GPU weight proxy already covers the one output copy.

| Whole-peak term | MiB |
| --- | ---: |
| Weight ceiling (file is6652.717MiB) | 6912 |
| Defensive full F16 KV | 1536 |
| Largest weight dequantization | 4096 |
| Graph/activation/scheduler/logits | 2048 |
| Driver/modules/handles | 1024 |
| Pool temporaries/rounding | 1024 |
| Loading staging | 256 |
| Remaining fragmentation/uncertainty | 1536 |
| **Conditional total** | **18432** |

Against the historical budget29098MiB this leaves10666MiB; historical free36373MiB would leave17941MiB after the plan, above margin7275MiB. No fresh GPU query was made here. Graph/driver/pool/loading amounts are defensive allowances, not measured bounds or a VRAM reservation. Actual header and runtime evidence can invalidate this estimate.

Disk free before fetch was25,534,849,024B. The two-file candidate manifest totals6,975,908,556B, so downloading now would leave less than20.5GiB even before metadata overhead. No cleanup or weight transfer was performed.

## Minimal reuse boundary and next decision

Reuse the pinned native binary/libraries, generic GGUF parser, Gemma JSON/fence/final-content parser, existing model-independent checks, and exact tokenizer/template reference bytes. Do not rebuild all194 CPU objects or rerun old model evaluations. Prior public20/context200 evidence may be carried forward only if new typed GGUF tokenizer fields/default and tool template bytes/BOS-EOS flags match the prior artifact and current request/schema/prompt behavior is explicitly shown equivalent. The new suppression list is a separate model-specific difference. Header mismatches require a bounded new check; they do not authorize input normalization, template repair or permissive dtype acceptance.

The new GGUF identity and 48-layer tensor/header checks cannot inherit 31B PASS. A new candidate allowlist/manifest binding and actual own-runtime resource evidence would be needed before any quality run, under the parent's decision. Prior 31B quality failure establishes no 12B quality prediction.

## Preservation

`download_ledger.json` records 20 fetched metadata objects, total32,651,983B, each actual SHA256/size and official Git blob or LFS digest where available. `fetch_metadata.py` enforces public HTTPS, file allowlisting, per-object caps, no overwrite and a cumulative99MiB cap. The API, selected text metadata and license bytes are saved, including the large tokenizer only in ignored storage. `provenance.json`, `candidate_download_manifest_draft.json`, `resource_plan.json` and `integrity.json` provide the review closure. No secret/authentication material is used.
