Root requested that bounded metadata description recognize additional known byte
formats without accepting their candidate roles. The final preparation extends
only the TYPES table by F16 (1,1,2), Q8_0 (8,32,34), BF16 (30,1,2), from pinned
ggml.h / ggml-common.h. All strict tensor_spec rules remain unchanged; a new test
rejects each added format on a normal candidate matrix. Unknown IDs still fail.
The 8 generic parser AST definitions remain exact. Eleven focused tests passed.

The previous helper/tests are preserved under *_pre_description_types.py with
their original hashes, along with the original ten-test proof and preparation
notes. Those notes' statement about no F16/BF16/Q8 acceptance refers to the strict
candidate contract; final metadata-only description can now inventory them. This
is not a revised model acceptance policy or evidence of any actual dtype.

Small memory clarification: Q5_0's block is exactly22 bytes (fp16 scale2 + high
bits4 + low quants16), independently verified by the pinned block declaration.
No numeric weight, GGUF header, tokenizer execution, native/GPU/HTTP was used in
this preparation. Root owns the first real metadata-only invocation.
