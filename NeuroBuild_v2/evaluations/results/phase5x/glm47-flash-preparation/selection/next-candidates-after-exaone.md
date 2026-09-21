# EXAONE 실패 뒤의 다음 후보 — 사전검증 비교만

2026-09-20 UTC 공식 primary 자료 재확인. **추천 순서는 GLM-4.7-Flash 사전검증 → Gemma4-12B 자원 우선 fallback → Qwen3.6-35B-A3B 후순위**다. 이는 다음 비교의 정보 가치와 준비 비용에 대한 판단이며, 한국어 품질 순위나 채택 판정이 아니다. EXAONE의 최초 진단 106/120, raw FP 0, unsafe 0은 semantic 114/120 gate를 충족하지 못한다. 실패한 EXAONE 또는 기존 Qwen/Gemma exact 모델을 재실행하는 제안은 없다.

| distinct 후보 / 실제 배포본 | 공식 metadata로 확인한 파일 | 우선순위 근거와 한계 |
|---|---:|---|
| **GLM-4.7-Flash**, Z.ai 30B-A3B; `ggml-org/GLM-4.7-Flash-GGUF` | `GLM-4.7-Flash-Q4_K.gguf`, **18,244,193,920 B / 16.991 GiB** | 아직 실패하지 않은 다른 학습 계열이며 nonthinking과 native 구현이 존재한다. 한국어 정확 인용·가구 한정·승인 보존의 직접 성능 근거는 없다. GGUF는 원저자 Z.ai가 아닌 llama.cpp 개발 조직의 변환본이다. |
| **Gemma4-12B IT QAT**, `google/gemma-4-12B-it-qat-q4_0-gguf` | `gemma-4-12b-it-qat-q4_0.gguf`, **6,975,879,296 B / 6.497 GiB** | Google 공식 QAT 배포본이고 A100/32GiB 장비의 자원 여유가 가장 크다. 실패한 31B와 다른 checkpoint이지만 같은 계열이므로 더 작다는 사실이 의미 오류 개선을 보장하지 않는다. |
| **Qwen3.6-35B-A3B**, `ggml-org/Qwen3.6-35B-A3B-GGUF` | `Qwen3.6-35B-A3B-Q4_K_M.gguf`, **20,419,565,568 B / 19.017 GiB** | 35B total/3B active의 별도 checkpoint이며 Qwen3.8-27B와 동일 모델은 아니다. source revision 연결이 공개돼 있다. 기존 Qwen 계열의 반복 실패와 큰 전체 weight 때문에 우선순위를 낮춘다. active 3B를 메모리 크기로 사용하지 않는다. |

파일 존재·정확 바이트/LFS SHA는 각각 [GLM GGUF revision](https://huggingface.co/ggml-org/GLM-4.7-Flash-GGUF/tree/7559e96b7e324ab405897dc2b91492b0f376ad4a), [Google QAT GGUF revision](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf/tree/29d097773436b69ff9feafd636ab4cf873786537), [Qwen GGUF revision](https://huggingface.co/ggml-org/Qwen3.6-35B-A3B-GGUF/tree/baec3ebee244827cda0f4557eafa8b28f7545fa6)의 HF API metadata GET으로 확인했다. 웹 렌더러가 일부 pinned 파일 URL을 429/접근 오류로 처리했으므로 API 성공과 웹 렌더러 실패를 혼동하지 않는다. Weight resolve/download는 하지 않았다. 상세 URL·정확 SHA·API 응답 hash·부분 config·고정 native source hash는 [structured refs](next-candidates-after-exaone-refs.json)에 있다.

| 후보 | immutable GGUF repo revision / full-file LFS SHA256 | 원본 모델 / 라이선스 근거 |
|---|---|---|
| GLM | `7559e96b7e324ab405897dc2b91492b0f376ad4a` / `b6019edc5fbe37d3660d2e994d16c839a7855a6f03362c5dcf8142ba479cd0d2` | `zai-org/GLM-4.7-Flash@7dd20894a642a0aa287e9827cb1a1f7f91386b67`, [원본 card MIT](https://huggingface.co/zai-org/GLM-4.7-Flash/blob/7dd20894a642a0aa287e9827cb1a1f7f91386b67/README.md). GGUF card license 필드는 비어 있고 README는 43 B로 원본 conversion revision을 제공하지 않는다. 배포 전 attribution/원본 license 보존과 provenance 확인이 남는다. |
| Gemma12 | `29d097773436b69ff9feafd636ab4cf873786537` / `93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b` | QAT source `google/gemma-4-12B-it-qat-q4_0-unquantized@b6ed86275a6a5735884e208bfed95b445a684ca2`, [Google Apache2 card](https://ai.google.dev/gemma/docs/core/model_card_4). 관측한 최신 source revision이 GGUF 변환 때의 source revision이라는 증거는 없다. |
| Qwen3.6 | `baec3ebee244827cda0f4557eafa8b28f7545fa6` / `671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7` | `Qwen/Qwen3.6-35B-A3B@995ad96eacd98c81ed38be0c5b274b04031597b0`, Apache2. GGUF [.src_sha](https://huggingface.co/ggml-org/Qwen3.6-35B-A3B-GGUF/blob/baec3ebee244827cda0f4557eafa8b28f7545fa6/.src_sha)의 PRIMARY 값이 이 revision과 같다. 실제 tensor 변환 정확성을 검증한 것은 아니다. |

GLM 원본 config는 `Glm4MoeLiteForCausalLM`, hidden 2048, vocab 154880, main 47층 + MTP 1층, routed experts 64개 중 4개와 shared 1개다. [공식 template](https://huggingface.co/zai-org/GLM-4.7-Flash/blob/7dd20894a642a0aa287e9827cb1a1f7f91386b67/chat_template.jinja)는 `enable_thinking=false`이면 assistant prefix를 `</think>`로 끝낸다. 공식 card의 일반 sampling은 T1/P.95이지만 그 benchmark의 긴 completion 예산은 이 프로젝트의 768 cap 성능 근거가 아니다. [원본 card](https://huggingface.co/zai-org/GLM-4.7-Flash)의 agent/coding 결과는 shortlist 참고에만 사용하며 한국어 정책 처리 우위로 환산하지 않았다.

Gemma12는 11.95B dense/unified 48층, SW 40층 + global 8층이고 system role과 nonthinking을 공식 지원한다. 공식 권장 sampling은 T1/P.95/K64이며 nonthinking에서도 빈 thought channel이 존재할 수 있다. [Google card](https://ai.google.dev/gemma/docs/core/model_card_4)의 multilingual 범위는 이 작업의 exact Korean quote 또는 unsupported false-positive 보장이 아니다. Multimodal projector·assistant/drafter는 텍스트 전용 후보에 포함하지 않는다.

Qwen3.6은 40층 중 Gated DeltaNet 30층과 full attention 10층을 사용한다. [공식 card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)는 `enable_thinking=false`와 T.7/P.8/K20/minP0/presence1.5/repetition1을 제시한다. 과거 Qwen3.8의 penalty0 실험 profile을 자동 승계하지 않는다. mmproj/MTP/dflash 파일은 별도이고 텍스트 단일 호출 후보 파일 크기에 포함하지 않았다.

현재 설치된 vLLM 0.8.5는 세 모델의 검증된 실행 경로가 아니다. Qwen card는 >=0.19.0, GLM card는 해당 main/nightly 계열을 제시하고 Gemma unified 역시 설치 버전보다 새 architecture다. 현재 driver535/CUDA11.8/Ubuntu20.04에서 새 vLLM 설치가 된다고 추정하지 않으며, NVFP4/Hopper·Blackwell 전용 배포본을 A100용으로 선택하지 않는다. 제안은 이미 빌드된 **llama.cpp `f072b103714dfa1eee531f80b24512faf38e3dd2`**에 대한 후보별 사전검증이다.

고정 source의 구현은 다음과 같다. 여기서 source 확인은 실행 성공과 구분된다.

- [GLM converter](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/conversion/glm.py#L247)는 `Glm4MoeLiteForCausalLM`을 **DEEPSEEK2**에 연결한다. [loader/graph](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/models/deepseek2.cpp#L24)에 GLM Lite gating과 기본 MTP skip이 있고, [GLM chat tests](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/tests/test-chat.cpp#L4393)에 nonthinking/content 및 thinking separation 경로가 있다. `glm4moe_lite`라는 별도 GGUF architecture를 가정하면 안 된다.
- [Gemma unified converter](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/conversion/gemma.py#L812)와 [Gemma4 graph](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/models/gemma4.cpp)가 존재한다. 과거 31B template/grammar 증거는 12B 실제 embedded tokenizer·template 검증을 대체하지 않는다.
- [Qwen MoE converter](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/conversion/qwen.py#L643)는 QWEN35MOE이고, [qwen35moe graph](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/models/qwen35moe.cpp)에 GDN/state와 MoE 처리가 있다. 다른 Qwen의 실제 GPU proof를 이 checkpoint의 runtime proof로 재사용하지 않는다.


GLM tokenizer 경로도 고정 [conversion/base.py:1588–1590](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/conversion/base.py#L1588)에 GLM-4.7-Flash fingerprint→`glm4`가 명시돼 있다. 이는 이번 pinned HF tokenizer와 실제 GGUF의 ID/roundtrip parity를 실행한 증거는 아니다. 세 후보 모두 native 기본 sampler를 묵시적으로 사용하는 대신 candidate profile의 top-k/min-p/penalties/window/order/seed를 사전에 명시해야 한다. GLM 공식 card는 T1/P.95 외의 그 항목을 완전히 지정하지 않으므로 Qwen/Gemma profile을 이름만 바꿔 사용하면 안 된다. 현재 엄격 model/profile/quant tuple의 새 항목 등록은 별도 승인·CPU 검토 범위이며, 이 조사에서 client/evaluator/launcher는 수정하지 않았다.

A100 screening 기준은 parent가 제공한 free 36373 − 별도 safety 7275 = **whole peak 최대 29098 MiB**다. 아래는 ctx4096/seq1/F16KV를 가정한 일부 항의 산술이며 **전체 peak 상한 또는 startup 허용표가 아니다**.

| 후보 | full-file proxy MiB | KV/state screening MiB | single vocab F32 확장 MiB | 29098에서 이 항들만 뺀 여지 MiB |
|---|---:|---:|---:|---:|
| Gemma12 | 6652.717 | SW padded1280 + global4096 KV = 464 | 3840 | 18141.283 |
| GLM | 17399.019 | 의도적으로 expanded K/V를 잡은 47×4096×20×(256+256)×2B = 3760 | 1210 | 6728.981 |
| Qwen3.6 | 19473.615 | full KV80 + F32 recurrent state 1벌60 = 140 | 1940 | 7544.385 |

실제 GGUF mixed dtype/shape, tied output 복제, MLA layout, GDN checkpoint 및 rollback buffer, packed expert matmul scratch, graph liveness, logits/scheduler, VMM/pool retention, driver/modules/handles, alignment/단편화와 일시적 복사를 더 검토해야 한다. 위 F32 항은 단일 vocab 행렬의 방어적 확장량이지 전체 dequant workspace의 상한이 아니다. 기존 MMQ 빌드 및 graphsOFF라고 모든 임시 할당이 없어지지 않는다. 특히 GLM filename `Q4_K`를 현재 evaluator의 `Q4_K_M`로 몰래 바꾸지 말고 실제 header의 type/quantization identity부터 확인해야 한다. 이 단계는 세 후보 모두 자원 사전검증을 진행할 여지가 있다는 판단까지만 제공한다.

32GiB RTX는 Gemma12가 가장 넓은 예상 여유를 가진다. GLM/Qwen도 weight 파일 자체는 들어가지만 전체 peak·사용 중 VRAM·여유 정책을 반영한 적합성은 미확정이다. 현재 A100 SM80 binary는 RTX5090 SM120 지원 증거가 아니므로 별도 빌드/driver/runtime 검사 없이 이식 가능성을 주장하지 않는다. 서버별 business logic 복제는 필요조건으로 제안하지 않는다.

디스크 read-only 관측은 **25,654,026,240 B / 23.892GiB** free다. 20GiB + .5GiB 보존 뒤 남는 공간은 3.392GiB이므로 세 파일 모두 지금 바로 받을 수 없다. inactive cache의 root 승인·hash/UID/regular/nlink/FD-map/lock 확인 후 회수 절차와 bounded download가 선행해야 한다. Root가 확인한 inactive EXAONE weight는 **20,047,839,424 B / 18.671GiB**이며, 이 단일 파일 회수가 별도 승인·검사를 통과할 경우에만 여유가 늘어난다. 그 파일을 자동 삭제하거나 회수 완료로 계산하지 않았다. 이 조사에서는 삭제·다운로드를 실행하지 않았다.

다음 한 단계는 **GLM의 공개 metadata/header 예상 규격과 native CPU template/tokenizer/GBNF·final-content 구조, MLA/MoE 전체 VRAM 계획을 확정할지 root가 선택하는 것**이다. 원본 revision/라이선스/변환 lineage가 부족하면 부족한 채로 기록한다. 승인 뒤의 실제 header·fullSHA·public CPU·wholepeak·own guarded startup/public/resource·freeze/commit/push가 모두 통과해야 첫 exposed120×1+warmup5에 갈 수 있다. schema120/semantic≥114/rawFP0 of58/unsafe0 of120, raw observation120 및 unknown/error 처리, source/quote adapter/domain/gold는 그대로다. 실패 후보의 자동 반복이나 V2 실행은 없다. 새 unused80에는 접근하지 않았다.

작업 범위: 공식 웹/소형 metadata GET, 고정 source 읽기, 산술, 이 ignored note와 structured refs 생성만 수행했다. 실제 GGUF header/payload 읽기, 모델/HTTP inference/GPU/native 실행, install/build, 환경·production·gold 수정, completed125 replay는 모두 0이다.
