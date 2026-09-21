# GLM4.7 Flash header preparation — no actual GGUF read

This is an executable strict first-version auditor plus metadata-only diagnostic,
not proof of the downloaded model. The original 8 bounded parser definitions are
AST-identical to `inspect_qwen38_gguf.py` (cb8ef9e…1940c). Only GLM model-specific
reference checks and allowed dtype constants are new. Ten new GLM synthetic tests
passed; no old candidate tests/replays, GPU, native executable, or model bytes were
read by this preparation.

## Artifact versus current default recipe: unresolved before actual header

The official publisher file is pinned at 18,244,193,920 bytes with LFS SHA
b6019edc5fbe37d3660d2e994d16c839a7855a6f03362c5dcf8142ba479cd0d2. Its conversion
revision and quantizer command are unpublished. `general.file_type` must be read
from the actual artifact: 14 means Q4_K_S; 15 means Q4_K_M. The filename Q4_K does
not select M.

Using current f072 defaults strictly, the 868 tensors occupy:

| Default type | Packed payload bytes | File minus payload bytes |
|---|---:|---:|
| Q4_K_S | 17,808,178,944 | 436,014,976 |
| Q4_K_M | 18,895,625,984 | -651,432,064 |

Both are incompatible with the fixed total size and the 32 MiB header limit.
Therefore **the artifact cannot satisfy every current default layout/type rule**.
The strict first version is intentionally not widened. Root should first use its
`--metadata-only` mode after code review to preserve actual metadata/layout/type
facts as `DIAGNOSTIC_NOT_PASS`, and authorize a separately versioned narrow change
only when the source/artifact difference is understood. This inference uses only
config, source names, quantizer code and public file size; it is not an actual
header finding. Do not claim the downloaded artifact has 868 tensors or any of
these dtype counts yet.

## Expected contract, provenance and unresolved runtime work

The current converter registers Glm4MoeLiteForCausalLM as deepseek2, stores main47
plus MTP1 by default, merges 64 experts per projection and splits/transposes MLA
K_B/V_B. The source index has exactly 9703 names. The auditor requires their exact
set, 868 derived tensor names/shapes, separate global embedding/output, six MTP
extras including its own embedding/output, and no unexpected tensor or architecture
key. The index scalar total_size is not used: it disagrees with shard API totals.

Metadata bindings require compressed-MLA heads1/key576/value512 and MLA head256,
q-LoRA768/kv-LoRA512, experts64/top4/shared1, hidden2048, intermediate10240 and
expert1536, 48 stored layers, vocabulary154880, source template exact3120 bytes,
ordered token/merge/type wire hashes, and special token IDs. Static padding is
24 [PAD154856]…[PAD154879] entries. This checks stored content only; tokenizer
encode/decode normalization of added literals, actual native IDs, public grammar,
context, successful loading, and quality remain separate gates.

The ordinary default quantization role policy is F32 norms/bias/router, Q4_K
matrices, Q6_K global output, subtype/layer-specific ffn_down promotion, and Q5_0
only for split K_B. The static expected counts are S: F32290/Q5_048/Q4_K518/
Q5_K11/Q6_K1; M: F32290/Q5_048/Q4_K482/Q6_K48. No F16/BF16/Q8 or unknown dtype is
silently accepted. A custom published/observed quantizer role is a new reviewed
contract, not an automatic exception.

## Q5_0 source and memory addendum (old VRAM estimate unchanged)

Pinned `src/llama-quant.cpp` categorizes `attn_k_b.weight` as OTHER, starts from
Q4_K and falls back Q4_K→Q5_0 when first dimension cannot divide 256. The converter
and loader require K_B `[192,512,20]`, so first-dimension192 divides Q5_0 block32.
The block is22 bytes (18? no: Q5_0 is fp16 scale2 + high-bit4 + low-quants16 =22),
which gives 1,351,680 bytes per K_B versus 7,864,320 bytes if expanded to F32.
All48 K_B tensors would total61.875 MiB in Q5_0 and360 MiB expanded to F32; a
single K_B expansion is7.5 MiB. These tensors are already included in the full
file-size weight term. Q5_0 does not enlarge the previously budgeted1536 MiB
largest expert expansion. It does not prove that no multiple temporary buffers
coexist.

Pinned `ggml/src/ggml-cuda/mmq.cu` explicitly lists Q5_0 in supported types and
routes it to the same MMA/shared-memory capability decision as Q4_K/Q6_K.
This is static kernel availability, not a native A100 execution result. The build
has neither FORCE_MMQ nor FORCE_CUBLAS; runtime dispatch and retained pool/graph
highwater remain covered by the earlier conditional allowances and actual guard
resource gate. The immutable `glm47_flash_whole_vram_plan.md/.json` is not changed.

## Invocation boundary (root only, after review)

`.conda/bin/python -B var/research/inspect_glm47_gguf.py --model var/models/ggml-org--GLM-4.7-Flash-GGUF/7559e96b7e324ab405897dc2b91492b0f376ad4a/GLM-4.7-Flash-Q4_K.gguf --report var/reports/glm47-flash-gguf-header-diagnostic.json --metadata-only`

The metadata-only path never reads/hashes numeric payload, never emits PASS, and
never authorizes the launcher. A strict full audit follows metadata validation
with a single-FD whole SHA stream and padding/size/stat/path rechecks, then emits
`GGUF_HEADER_AUDIT/PASS` only if every check passed. All reports use exclusive
creation and owned no-follow paths; errors retain only fixed codes. Actual parser
support limitations are preserved as failures; no guessing of unknown block sizes.
