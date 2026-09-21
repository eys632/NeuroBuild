# EXAONE 4.5 33B Q4_K_M — metadata/source 조사

상태: **미선정, weight 미다운로드, native/GPU/모델 미실행**. 비상업 연구용 조건부 후보다.
현재 gate·prompt·parser·scorer·production 파일은 바꾸지 않았다. 새 Gemma 결과는 이 조사에서 읽지 않았다.
다른 모델 계열이라는 사실이나 한국어 종합 점수로 exact-quote 품질 향상을 보장하지 않는다.

## 공식 artifact와 lineage

2026-09-20 공식 HF current/pinned API를 각각 조회했다. 두 current revision은 기존 조사 pin과 일치한다.

| 항목 | 확인값 |
|---|---|
| 공식 GGUF | `LGAI-EXAONE/EXAONE-4.5-33B-GGUF` |
| GGUF revision | `0e969634ef24db05151b435970297a6dee634b7e` |
| 선택 가능한 단일 text weight | `EXAONE-4.5-33B-Q4_K_M.gguf` |
| 원격 크기 / LFS SHA-256 | 20,047,839,424 bytes / `5ba3839b67dcee5618ea7b2206cedc8f9e2ec90fbcec3c95a8cc8b33967f6baf` |
| 원본 모델 | `LGAI-EXAONE/EXAONE-4.5-33B` |
| 원본 revision | `570aa4b15a4f45ba1133072b45f50198f6e3b4fd` |
| 공개 여부 | 두 repository 모두 API `gated=false` |

[고정 GGUF API](https://huggingface.co/api/models/LGAI-EXAONE/EXAONE-4.5-33B-GGUF/revision/0e969634ef24db05151b435970297a6dee634b7e?blobs=true),
[고정 원본 API](https://huggingface.co/api/models/LGAI-EXAONE/EXAONE-4.5-33B/revision/570aa4b15a4f45ba1133072b45f50198f6e3b4fd?blobs=true).
Weight SHA는 **원격 LFS metadata**이며 실제 payload/header 검증 결과가 아니다.
GGUF 카드의 lineage는 `base_model_relation: quantized`다. QAT나 특정 calibration 절차를
수행했다는 근거는 보존된 카드·파일 목록에 없으므로 QAT라고 부르지 않는다.
실제 혼합 tensor dtype, GGUF 내부 template/tokenizer와 원본 metadata의 동일성은 미확인이다.
Vision/mmproj와 다른 quant 파일은 후보 manifest에서 제외했다.

`candidate_download_manifest.json`은 기존 downloader 형식의 **ignored 초안**이다.
README·LICENSE·단일 weight 합계 20,047,878,049 bytes,
SHA `98aa8ad498c2a55db6359754c80793e33b880f60c191ec3fbe449097833c4bb8`.
이를 작성한 행위는 weight 다운로드 승인이 아니다.

## 라이선스와 sampling

양 repository의 LICENSE bytes가 동일하며 SHA는
`8c1762fb4bd94c8f17e114c5caa567e0948e1da7d02b79b55e99be9616e0f9e3`다.
EXAONE License 1.2-NC §2.1은 비상업 연구·교육의 평가와 실험을 허용하며,
§2.2/3.1은 상업 제품·서비스와 경쟁 모델 개발·개선 사용 등을 제한한다.
따라서 내부 비상업 연구라는 범위에서만 후보로 고려하며 제품 채택·외부 배포 허가를 주장하지 않는다.
§4.3의 연구 결과 attribution 요구와 §9.1의 변경 조항도 유지해야 한다.
[고정 공식 LICENSE](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B-GGUF/blob/0e969634ef24db05151b435970297a6dee634b7e/LICENSE).

공식 카드에는 용도가 겹치는 복수 권고가 있다. 한국어/OCR/document는
temperature 0.6, top_p 0.95, top_k 20, presence_penalty 1.5;
일반 용도는 1.0/0.95/presence 1.5; text-only는 1.0/0.95다.
Thinking 기본값은 true여서 nonthinking은 false를 명시해야 한다.
generation_config는 sample=true/T1/P.95/presence1.5이며 top_k/min_p/frequency/repetition/seed는 없다.
카드의 native 예시는 min_p=0도 사용한다. 하나의 완전한 nonthinking 전용 preset이라고 합치지 않는다.
[고정 공식 카드](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B-GGUF/blob/0e969634ef24db05151b435970297a6dee634b7e/README.md).

고정 llama.cpp의 history penalty는 source/prompt token에도 영향을 줄 수 있다.
추후 neutral penalty를 선택한다면 공식 presence1.5와 다른 실험 설정으로 명시해야 한다.
현재 새 profile이나 sampler 설정은 구현·선택하지 않았다.

## config, tokenizer, 고정 native source

공식 text config는 hidden5120, FFN27392, vocab153600, 본층64+MTP1,
Q heads40/KV heads8/head128, LLLG attention, sliding_window4096이다.
카드의 window128을 메모리 절감 근거로 사용하지 않는다. `tie_word_embeddings=false`다.
[고정 config](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B/blob/570aa4b15a4f45ba1133072b45f50198f6e3b4fd/config.json).

실제 tokenizer.json은 12,160,205 bytes, SHA
`0bd798efa30739e209d51f36cfc2f0a636711e37ad9d69b77e4e5c8ca5f09fab`이다.
NFC normalizer + ByteLevel BPE이며 vocabulary153600/merges152982/added tokens362다.
공식 pretokenizer regex는 native `EXAONE_MOE` 패턴과 일치한다.
그러나 실제 GGUF의 `tokenizer.ggml.pre`는 아직 읽지 않았다. Native `exaone4`는 GPT2,
`exaone-moe`는 해당 패턴으로 연결되므로 모델 이름만으로 올바른 경로를 확정할 수 없다.
고정 BPE raw-text 경로에 NFC 변환이 보이지 않아 decomposed Unicode에서 HF/native 불일치 가능성이 있다.
이는 아직 실제 token 비교가 아니다. 기존 Qwen raw-Unicode variant를 재사용하거나
사용자 원문을 NFC로 바꾸는 해결책을 채택하지 않았다.
[고정 tokenizer](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B/blob/570aa4b15a4f45ba1133072b45f50198f6e3b4fd/tokenizer.json),
[native vocabulary 경로](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-vocab.cpp).

별도 chat_template.jinja는 5930 bytes/SHA
`e4ece7acc79ba82121d4d57791fb7ecb796e39185087197377da5d2286bec0e5`다.
system/user 문자열은 그대로 삽입하며 nonthinking generation suffix에 빈 think block을 넣는다.
과거 assistant content에 대한 strip과 현재 user 원문의 처리는 서로 다르다.
f072의 specialized dispatch에 EXAONE 전용 분기는 찾지 못했으며 이 template은 generic automatic
parser 경로로 예상된다. 실제 template render, branch JSON grammar, final-only content,
tool/unfinished reasoning 거절 및 EOG는 CPU 검사 전까지 미검증이다.
[공식 template](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B/blob/570aa4b15a4f45ba1133072b45f50198f6e3b4fd/chat_template.jinja),
[native chat dispatch](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/common/chat.cpp).

f072 converter에는 `Exaone4_5_ForConditionalGeneration` text tower→`EXAONE4` 등록이 있다.
Graph는 Q/K RMSNorm, SWA RoPE/global NoPE 및 SiLU FFN을 구현하며 MTP tensor는 loader에서
`TENSOR_SKIP` 처리하고 실행하지 않는다. 기존 A100 build를 새 모델 기동 PASS로 해석하지 않는다.
[converter](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/conversion/exaone.py),
[model loader/graph](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/models/exaone4.cpp).
설치된 vLLM0.8.5 registry는 구형 `ExaoneForCausalLM`만 등록하며 4.5 class는 없다.
원본 tokenizer_config의 `TokenizersBackend`도 설치된 Transformers4.51.3 경로를 그대로
지원한다고 가정할 수 없다. 새 환경 설치를 제안하지 않고 현재 native 후보의 정적 검토로 제한했다.

## 메모리와 다운로드 전 제약

가정은 text-only, context4096, sequence1, batch/ubatch64, F16 K/V,
flash attention off, CUDA graphs off, MTP/speculative off, 단일 허용 GPU3다.
공용 GPU baseline free36,373MiB에서 safety7,275MiB를 제외한 전체 peak 예산은29,098MiB다.

| 계산 가능한 항목 | MiB |
|---|---:|
| GGUF 전체 파일을 resident weight로 잡은 상한성 입력 | 19,119.110 |
| 65층 전부4096 cells, K/V 각각8×128×2bytes | 1,040 |
| 가장 큰 vocab×hidden 행렬의 F32 전개 1개 | 3,000 |
| 위 항목을 뺀 나머지 예산 | 5,938.890 |

FFN의 단일 F32 행렬은535MiB다. 큰 행렬 하나만 더하면 전체 peak가 되는 것은 아니다.
Native CUDA 경로에는 dequant allocation, cached pool/성장, graph/output/attention buffers,
CUDA modules/handles, loading 임시 공간과 fragmentation이 있다. Header 미관측 상태에서는
embedding/output 중복과 실제 dtype/offset도 확정할 수 없다. 따라서 이 표는 **조건부 자원 후보**를
뒷받침하며, 완성된 peak hard bound 또는 기동 승인이 아니다. 독립 source budget 검토를 별도 연결한다.
[CUDA allocation/pool](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/ggml/src/ggml-cuda/ggml-cuda.cu).

이번 관측 disk free28,136,112,128B에서 manifest를 받으면8,088,234,079B만 남는다.
20.5GiB reserve를 유지하려면 최소13,923,473,313B의 추가 여유가 필요하므로 **현재 download gate는 FAIL**이다.
이는 mutable filesystem의 시점 관측이며 삭제 권고나 실행이 아니다. 향후 root가 별도로
inactive artifact 소유·사용 여부와 fresh disk를 확인하기 전에는 weight를 받지 않는다.

Metadata payload 합계12,389,867B로50MiB cap 이내다. 모든 작은 파일의 실제 SHA/크기/요청 URL과
수집 시각, Git blob 또는 LFS 대조는 `fetch_receipts_stage*.json`과 `provenance.json`에 보존했다.
Weight/range, 모델 호출, native 실행, GPU 접근, 패키지 설치와 cache 삭제는 모두0회다.
