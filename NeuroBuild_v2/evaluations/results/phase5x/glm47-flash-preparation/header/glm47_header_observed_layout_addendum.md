# GLM observed GGUF layout — strict v2 preparation

Root's first metadata-only receipt is
`var/reports/glm47-flash-gguf-header-diagnostic.json`, SHA
`e97d4d6412ea35295961e024476d6c43b4ac9a7fc593e4d57c031b7a9a8e961b`.
It remains **DIAGNOSTIC_NOT_PASS / CONFIG_METADATA_MISMATCH**, with no payload hash
claim. The original inspector d21a53…46c69 and its static default-recipe arithmetic
are unchanged. Root's downloader previously verified the full pinned LFS SHA.
The new inspector must still perform its own one-FD full SHA before emitting a
strict header PASS; this preparation has not opened the GGUF.

The explicit artifact layout name is
`glm47-flash-q4-k-m-47main-no-mtp-q8-output-kb-v1`. This is a storage description,
not a claim about exact conversion command/revision or successful native loading.

## Source-supported observed contract

The header has general.file_type15 = Q4_K_M, deepseek2.block_count47, no
nextn_predict_layers metadata, split K_B/V_B, KV-head1 with key576/value512 and
MLA key/value256. All shapes match pinned loader declarations. The untouched
upstream config/index describes47 main + MTP1; exact9703 source names decompose
into9491 main names and exactly212 layer47 MTP names. The artifact stores844
tensors: global3 + dense-layer0's13 + 46 MoE layers×18. All six MTP-specific GGUF
extras and the entire MTP decoder layer are absent. Both untied global embedding
and output are present.

The pinned converter explicitly supports `no_mtp`, filters layer>=47 and omits
the nextn metadata. This makes the observed layout supported, while it does not
prove which historical command produced the artifact. See
[conversion/glm.py](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/conversion/glm.py#L247)
and [deepseek2 loader](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/models/deepseek2.cpp#L55).
The loader recognizes47-layer/154880-vocabulary GLM Lite, and metadata absence
means no MTP layer is instantiated.

Observed types are exactly F32281, Q4_K470, Q6_K45, Q8_048. Q8_0 occurs only on
output.weight and47 attn_k_b.weight tensors. F32 covers norms, routing matrices
and correction biases; the remaining attention/gate/up matrices are Q4_K.
Q6_K is restricted to ffn_down roles at layers
0,1,2,3,4,7,10,13,16,19,22,25,28,31,34,37,40,41,42,43,44,45,46,
which exactly match the current quantizer's47-layer Q4_K_M promotion rule.
The quantizer supports explicit output and tensor type selection and a Q6_K→Q8_0
fallback; none of these possible paths is asserted as the unpublished command.
See [quantizer](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-quant.cpp#L372).

The v2 policy accepts only this ftype, no-MTP metadata absence, exact tensor
names/shapes and exact per-role dtypes. It rejects S, legacy unsplit MLA, MTP
addition, lost output, arbitrary Q8 promotion and relaxed tokenizer/template
bindings. This is an independently checked artifact-specific contract, not a
change to the application's semantics or quality gate.

## Exact byte coverage and whole-VRAM implications

The shapes and explicit block formats derive18,234,718,720 bytes of tensor payload,
zero per-tensor padding. Header9,475,170 plus30 alignment bytes gives data offset
9,475,200. Their sum is exactly18,244,193,920 bytes; the parser independently
requires contiguous aligned offsets, no overlap/gaps/trailing bytes, and later
full-SHA/padding/stat/path checks. Token/merges/types wire hashes and original
3120-byte template match the independently derived official metadata unchanged.

Q8_0 block32 occupies34 bytes. The actual output matrix occupies337,018,880 bytes
(321.40625 MiB); all47 K_B matrices together occupy93.6328125 MiB, each1.9921875 MiB.
The embedding is170.15625 MiB. These are already in the whole-file weight proxy
17399.019165 MiB and must not be added twice. Largest dense/any actual F32 tensor
expansion is the vocabulary matrix1210 MiB; each K_B expansion is7.5 MiB. The
existing1536 MiB defensive fused-expert dequant allowance remains larger. The
actual split-expert tensor expansion is768 MiB each, so no larger new tensor is
introduced by Q8_0. This says nothing about multiple temporary buffers coexisting.

Pinned [CUDA MMQ](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/ggml/src/ggml-cuda/mmq.cu#L28)
instantiates Q8_0 and includes it in should_use_mmq's supported type switch before
the common MMA/shared-memory capability decision. Q8_0 is known to the pinned
block-size table and generic tensor loader. This is source support, not an A100
kernel execution result. No FORCE_MMQ setting is invented; the existing build
keeps its actual flags. The old28672 MiB whole estimate and separate7275 MiB safety
margin remain unchanged. Actual metadata supports compressed K-only cache211.5
MiB for47×4096×576×F16; the earlier3840 MiB expanded48-layer screening allowance
remains conservative. Graph/workspace, retained pool, loading and driver
allowances still need the planned fresh guarded startup/resource observations.

## Focused validation, without another weight read

Seven new controls validate the saved metadata and synthetic negative mutations:
exact variant/bytes/source omission; unchanged generic8 and tokenizer AST;
original v1 still rejecting this header; no S/MTP widening; Q8 roles and47-layer
promotion; shape/byte/padding/output failures; unchanged MLA/tokenizer/template
requirements. No old diagnostic response replay, model, tokenizer execution,
GPU/native/HTTP call or weight-file open occurred. Header/fullSHA PASS and actual
runtime CPU/quality gates remain pending root's separately authorized calls.
