# 다음 로컬 모델 후보 비교 — 2026-09-20

> 후속 상태: Gemma4-31B 사전 검증 뒤 첫120개 품질 gate가 rawFP1/unsafe2로 실패했다.
> 아래 내용은 선택 당시의 비교 기록이다. 현재는 같은 후보 반복·V2 없이 EXAONE4.5의 조건부
> metadata/source 검토와 첫 단회까지 완료했으나 EXAONE도 semantic106/120으로 FAIL했다.
> 같은 후보 반복·V2 없이 다른 모델을 비교한다. [최신 상태](STATUS.md),
> [EXAONE 결과](reports/phase5x_native_exaone45_diagnostic_report.md), [Gemma 결과](reports/phase5x_native_gemma4_diagnostic_report.md).

상태: **METADATA/SOURCE_REVIEW_ONLY — 미채택, 다운로드·설치·기동·품질 호출 없음.**
Qwen3.8-27B의 첫 V2 결과는 semantic 73/80, raw READY FP 1/40,
unsafe accepted READY 1/80로 실패했다. 이 문서는 실패 후보를 재실행하는 계획이
아니라, 다른 모델 3개의 다음 사전 검증 우선순위를 정한다.

**우선 권고는 Google 공식 Gemma 4 31B QAT Q4_0 GGUF의 CPU/자원 사전 검증이다.**
서로 다른 학습 계열, 공식 QAT 배포, Apache-2.0, 현재 native pin의 모델·chat parser
지원이 선택 이유다. 한국어 원문 인용과 가구/문의 의미 구분이 개선된다는 실측 근거는
아직 없다. 더 큰 모델이라는 이유나 공개 종합 점수만으로 품질 통과를 예상하지 않는다.

참조한 기존 기록은 [Phase 0 후보](model_selection_plan.md),
[이전 native 후보](modern_local_runtime_candidate.md),
[실험 기록](phase5x_experiment_register.md)이다. 이미 실패한 Qwen3 8B/14B/32B,
Qwen3-4B-Instruct-2507, Qwen3-30B-A3B-Instruct-2507 AWQ, Qwen3.8-27B는
새 후보에서 제외했다. Phase 0에서 검토만 했던 아래 모델은 이 프로젝트의 품질 실행 이력이 없다.

## 후보와 선택 근거

| 후보 | 근거와 기대 역할 | 결정적인 한계 | 우선순위 |
| --- | --- | --- | --- |
| `google/gemma-4-31B-it-qat-q4_0-gguf` | Google 공식 QAT Q4_0, Apache-2.0, instruction-tuned dense 모델. 원문 보존 작업에 별도 모델 계열을 비교할 수 있다. | 한국어 exact-span·가구 전용 정책의 공개 통과 증거 없음. thought 채널과 native grammar wrapper를 새로 검증해야 한다. | **1: 다음 사전 검증 권고** |
| `LGAI-EXAONE/EXAONE-4.5-33B-GGUF`, Q4_K_M | LG 공식 GGUF. 한국어 KMMLU-Pro/KoBALT와 instruction-following 평가를 직접 공개한 후보. | EXAONE License 1.2-NC의 연구·교육 범위 조건. 공개 언어 점수는 원본 모델의 reasoning 평가이며 Q4 non-thinking 성능이 아니다. | 2: 연구 범위 조건부 비교 |
| `google/gemma-4-12B-it-qat-q4_0-gguf` | Google 공식 QAT, Apache-2.0. 31B보다 작은 디스크·메모리 부담의 별도 모델. | 자원 절감 대안이며 31B보다 추출 정확도가 낫다는 근거 없음. 같은 Gemma 계열이므로 계열 독립성은 EXAONE보다 낮다. | 3: 자원·지연 대안 |

Google은 QAT GGUF와 비추론 모드를 공식 제공하며, Gemma 4의 다국어·system role
지원을 설명한다. 이는 한국어 요구사항의 정확한 부분문자열 추출이나 건축 객체 분류를
검증한 결과가 아니다. [공식 QAT 카드](https://huggingface.co/google/gemma-4-31B-it-qat-q4_0-gguf),
[Gemma 4 모델 카드](https://ai.google.dev/gemma/docs/core/model_card_4),
[공식 12B QAT 카드](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf).

EXAONE 공식 카드의 원본 reasoning 점수는 KMMLU-Pro 67.6, KoBALT 52.1,
IFEval 89.6이다. 카드가 non-reasoning 모드도 제공하지만 기본값은 thinking=true이므로
명시적으로 꺼야 한다. 연구 비교 근거로만 사용하며 우리 768-token JSON 계약의 성능으로
해석하지 않는다. [LG 공식 GGUF 카드](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B-GGUF).
라이선스는 연구·교육 사용을 규정하고 상업 사용은 별도 계약 대상으로 둔다.
이 문서는 제품 배포나 상업 사용 허가를 판단하지 않는다.
[공식 라이선스](https://github.com/LG-AI-EXAONE/EXAONE-4.5/blob/main/LICENSE).

## 고정할 수 있는 배포 식별자

공개 HF API의 `revision/<full-sha>?blobs=true`를 재조회하여 아래 revision,
`gated=false`, 파일 크기와 LFS SHA를 확인했다. 이는 **원격 메타데이터의 digest**이며
실제 파일을 받아 검증한 SHA가 아니다. 모델 weight나 GGUF header는 읽지 않았다.
Google의 원본 IT revision은 비교용 lineage 식별자이며, QAT GGUF가 그 원본 weight와
동일하다는 뜻이 아니다. 실제 선택 artifact는 각 QAT/GGUF revision 자체다.

| 후보 | 원본 IT 모델 revision | 공식 GGUF repository revision |
| --- | --- | --- |
| Gemma 4 31B | `842da3794eaa0b77d5f08bae87a17459d91ff475` | `59dde24573e7e61570dba08b18a2e1fe246955ed` |
| EXAONE 4.5 33B | `570aa4b15a4f45ba1133072b45f50198f6e3b4fd` | `0e969634ef24db05151b435970297a6dee634b7e` |
| Gemma 4 12B | `707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7` | `29d097773436b69ff9feafd636ab4cf873786537` |

| text-model artifact | bytes / GiB | LFS SHA-256 |
| --- | --- | --- |
| `gemma-4-31B_q4_0-it.gguf` | 17,651,001,568 / 16.439 | `179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b` |
| `EXAONE-4.5-33B-Q4_K_M.gguf` | 20,047,839,424 / 18.671 | `5ba3839b67dcee5618ea7b2206cedc8f9e2ec90fbcec3c95a8cc8b33967f6baf` |
| `gemma-4-12b-it-qat-q4_0.gguf` | 6,975,879,296 / 6.497 | `93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b` |

Exact metadata:
[31B API](https://huggingface.co/api/models/google/gemma-4-31B-it-qat-q4_0-gguf/revision/59dde24573e7e61570dba08b18a2e1fe246955ed?blobs=true),
[EXAONE API](https://huggingface.co/api/models/LGAI-EXAONE/EXAONE-4.5-33B-GGUF/revision/0e969634ef24db05151b435970297a6dee634b7e?blobs=true),
[12B API](https://huggingface.co/api/models/google/gemma-4-12B-it-qat-q4_0-gguf/revision/29d097773436b69ff9feafd636ab4cf873786537?blobs=true).
text-only 범위에는 별도 mmproj, vision/audio encoder, drafter weight를 포함하지 않는다.
GGUF 안에 포함된 보조 tensor의 실제 로딩 여부는 header/loader 검사에 남긴다.

## A100 경로: native는 정적 지원, 새 후보 실행은 미검증

현재 재사용 가능한 native pin은
`ggml-org/llama.cpp@f072b103714dfa1eee531f80b24512faf38e3dd2`이다.
이 pin의 기존 A100 SM80/CUDA 11.8 빌드·공통 runtime 실행 증거는 보존한다.
새 모델에 필요한 연산, tokenizer, peak, 품질이 이미 검증됐다는 뜻은 아니다.
새 driver/CUDA/패키지를 요구하는 vLLM 경로를 우회하기 위해 기존 native binary의
지원 가능성을 먼저 확인한다. 시스템 또는 사용자 공간의 libcuda 교체는 제안하지 않는다.

pin에는 `Gemma4ForConditionalGeneration`, `Gemma4UnifiedForConditionalGeneration`,
`Exaone4_5_ForConditionalGeneration`의 변환 등록과 `gemma4`/`exaone4` graph가 있다.
EXAONE 4.5 text tower는 기존 `exaone4`로 매핑한다.
[Gemma 변환 소스](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/conversion/gemma.py),
[EXAONE 변환 소스](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/conversion/exaone.py),
[Gemma graph](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/models/gemma4.cpp),
[EXAONE graph](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/models/exaone4.cpp).

현재 설치된 vLLM 0.8.5 registry에는 위 새 architecture가 없다. 최신 문서에
Gemma 4/Unified와 EXAONE 4.5가 등록된 사실은 확인했지만, 그것으로 현재
cu118 환경·535 driver에서 지원된다고 주장할 수 없다. 최신 wheel 설치나
CUDA 변경을 이번 선택의 전제로 삼지 않는다.
[vLLM 0.24 공식 지원 목록](https://docs.vllm.ai/en/v0.24.0/models/supported_models/).

Gemma에는 특히 새 CPU protocol 검증이 필요하다. non-thinking에서도 빈 thought
태그가 나오고 경우에 따라 thought 채널이 생성될 수 있다는 공식 설명이 있다.
고정 native `gemma4` parser의 response-format 경로는 생성 grammar에 JSON fence를
포함하지만 JSON 부분만 `content`로 분리한다. 따라서 기존 Qwen의 token prefix나
raw JSON fixture를 그대로 적용하면 안 된다. 최종 content가 기존 JSON 계약 그대로인지,
reasoning이 별도로 분리되고 저장되지 않는지, EOF/length/누락 시 실패하는지를 증명해야 한다.
애플리케이션의 Markdown 제거·응답 보정은 허용하지 않는다.
[공식 prompt format](https://ai.google.dev/gemma/docs/core/prompt-formatting-gemma4),
[고정 Gemma parser](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/common/parsers/gemma4.cpp).

새 sampling profile도 호출 전에 명시해야 한다. Google 카드의 권장값은
temperature 1.0 / top_p 0.95 / top_k 64이며, 기존 Qwen profile을 이름만 바꿔
승계하지 않는다. seed·penalty·sampler 순서·enable_thinking=false와 총 output cap을
함께 고정하고, 공식 권장과 다른 값은 실험 선택으로 구분한다.
[Google sampling 지침](https://huggingface.co/google/gemma-4-31B-it-qat-q4_0-gguf#best-practices).

## 메모리·디스크의 정적 선별

GPU3 baseline free 36,373 MiB와 최소 안전 여유 7,275 MiB를 적용하면 후보 전체
peak 허용치는 **29,098 MiB**다. 이전 Qwen의 28,672 MiB 추정이나 실제 peak는
새 후보에 자동 승계하지 않는다. 아래는 선택 가능성을 판단할 항목별 산술이며
완성된 peak 보증이나 기동 승인이 아니다.

가정: context 4096, sequence 1, ubatch 64 이하, F16 K/V, SWA full-cache 비활성,
speculative/MTP 실행 없음, text-only. K/V 공유로 줄어드는 양은 계산에서 공제하지 않는다.

| 후보 | GGUF 전체 bytes 환산 MiB | 보수적 K/V 산술 MiB | 큰 단일 행렬 F32 확장 가정 MiB | 29,098에서 앞 세 항목을 뺀 잔여 MiB |
| --- | ---: | ---: | ---: | ---: |
| Gemma 4 31B | 16,833.307 | 1,320 | 5,376 | 5,568.693 |
| EXAONE 4.5 33B | 19,119.110 | 1,040 | 3,000 | 5,938.890 |
| Gemma 4 12B | 6,652.717 | 464 | 3,840 | 18,141.283 |

Gemma31은 SW 50층 × (16 KV heads × 256)과 global 10층 × (4 × 512),
Gemma12는 SW 40층 × (8 × 256)과 global 8층 × (1 × 512)다.
pin의 SW cache는 `min(context, window + ubatch)`를 256 단위로 올리므로
1024+64는 1280 cells다. K와 V 각각 2bytes를 곱하면 표의 1320/464 MiB가 나온다.
EXAONE은 64 본층+1 보조층 모두에 4096 cells와 8×128 K/V를 잡아 1040 MiB로
여유를 둔다. 카드에는 SW128, 고정 config에는 SW4096이라는 차이가 있어 작은 카드
수치를 메모리 절감 근거로 사용하지 않았다.
[31B config](https://huggingface.co/google/gemma-4-31B-it/blob/842da3794eaa0b77d5f08bae87a17459d91ff475/config.json),
[12B config](https://huggingface.co/google/gemma-4-12B-it/blob/707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7/config.json),
[EXAONE config](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B/blob/570aa4b15a4f45ba1133072b45f50198f6e3b4fd/config.json),
[고정 SW cache 소스](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-kv-cache-iswa.cpp).
Gemma31의 1000+320 MiB 및 잔여 공간 산술은 별도 에이전트가 제공된 형상값으로
독립 확인했다. 그 검토는 새 config/header 실행 검증이나 전체 peak 측정이 아니다.

F32 항목은 `vocab × hidden × 4bytes`인 embedding/output 규모를 한 번 펼친다는
방어적 가정이다. 실제로 그 크기가 항상 할당되거나 그 하나만 남는다는 뜻은 아니다.
나머지 공간에서 graph liveness, retained CUDA pool, 추가 matmul workspace,
embedding/output 중복, modules/handles, 정렬·fragmentation 및 모델 로딩 임시 버퍼까지
합산해야 한다. GGUF tensor shape/type 및 loader 배치가 이 가정과 다르면 다시 산정한다.
따라서 세 후보는 **정적 사전 검증 대상으로 타당**, 현재 상태로 **전체 peak PASS는 미확정**이다.

부모가 제공한 현재 디스크 free 24.65 GiB에 20 GiB+0.5 GiB reserve를 적용하면
사용 가능분은 약 4.15 GiB다. 단일 파일과 reserve만 충족하는 데 필요한 추가 회수량도
31B 약 12.29 GiB, EXAONE 약 14.52 GiB, 12B 약 2.35 GiB이며, metadata/log 여유는 별도다.
그러므로 어떤 후보든 받기 전 정확히 식별된 비활성 프로젝트 model artifact만 대상으로
회수 계획을 확인해야 한다. 이번 조사에서는 삭제·다운로드·cache 정리를 하지 않았다.

## 다음 작업의 제한된 순서

1. Gemma31을 다음 사전 검증 후보로 명시하고 원격 license/config/tokenizer/template와
   pinned GGUF manifest를 고정한다. 기존 raw-Unicode Qwen 변형을 새 모델에 이식하거나
   입력을 정규화하지 않는다. tokenizer 특성이 다르면 사실과 runtime variant를 별도로 기록한다.
2. 디스크 회수 필요량과 inactive artifact 소유·사용 상태를 확인한 뒤에만 향후 다운로드를
   진행한다. 실제 SHA/header/tensor coverage와 모델별 전체 peak 추정을 먼저 완성한다.
3. 기존 CPU verifier를 모델의 실제 template·vocab·native grammar에 맞게 한정 적용한다.
   공개 한국어/부호/combining mark의 왕복, reasoning 분리, branch schema의 긍정·부정 예,
   고정 prompt+output cap의 context 적합성을 검증한다. 다른 모델의 CPU PASS를 대체 증거로 쓰지 않는다.
4. 통과한 새 runtime profile만 동일 공통 guard/transport로 GPU3에 연결한다.
   fresh 여유 검사·UUID/internal-device0·own-PID loopback·전체 peak watchdog를 유지하고
   자동 offload/다른 GPU/무제약 재시도/fallback를 사용하지 않는다. 서버별 업무 코드 복제는 없다.
5. 품질 호출 전 새 candidate/profile/proofs를 freeze하고 단일 진단으로 판정한다.
   기존 policy/gold/quote adapter/canonical parser/scorer와 네 gate(schema100%, semantic≥95%,
   raw READY FP0, unsafe accepted READY0), raw unknown 분모를 유지한다.
   실패 후보의 자동 반복이나 3회 평가를 되살리지 않는다. 기존 V2는 이제 출력 노출 자료이므로
   새로운 일반화 판정에는 별도로 사전 고정한 미사용 holdout이 필요하다.

A100에서 다음 후보가 통과하더라도 RTX5090의 SM120 native binary, 32 GiB 메모리,
runtime protocol·성능은 별도 검증 대상이다. 현재 비교는 RTX 실측, 모델 채택,
Phase5.x 완료 또는 Phase6 진입의 근거가 아니다.
