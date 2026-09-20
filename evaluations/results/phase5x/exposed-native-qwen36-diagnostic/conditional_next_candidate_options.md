# Qwen3.6 첫 gate FAIL일 때의 다음 선택 — 조건부 검토

2026-09-21 KST. 작성 범위는 기존 보고서·shortlist와 공식 공개 metadata, 고정 native source 읽기다. Qwen3.6은 root가 clean `23b8d018`에서 첫120×1+warmup5를 실행 중이라고 전달했으며, 이 검토는 결과·응답·dataset을 읽지 않았다. **아래 FAIL 분기는 실제 실패가 확인될 때만 적용한다. PASS이면 기존 후속 판단을 따른다. Phase5.x 미완료·Phase6 차단은 그대로다.**

권고는 **기존 실패 모델/계약 재실행 대신, 미검증 Mistral 계열의 공식 Ministral 3 14B Instruct GGUF 한 후보에 대한 metadata/source 사전검토**다. 이는 다음 다운로드·GPU 실행을 예약하거나 성공 확률을 주장하는 결정이 아니다. 새 후보가 지금까지와 무엇이 다른지, 기존 예산에서 어떤 미확인 가설 하나를 검증할지 먼저 등록한다.

## 남아 있는 후보와 이미 닫힌 가설

[Phase0 shortlist](../../docs/model_selection_plan.md)의 Qwen3.8/Gemma31/Gemma12/EXAONE/Qwen3.6 중 현재 Qwen3.6만 첫 결과 대기다. [후속 shortlist](next-candidates-after-exaone.md)의 GLM도 이미 실행했다. 따라서 이 목록에 있는 미실행 후속 모델을 단순히 꺼내 쓸 수는 없다.

| 완료된 비교 | 기존 보고서의 결과·다음 선택에 주는 의미 |
|---|---|
| Qwen3.8 | 노출120은117/120, rawFP0/unsafe0였으나 별도 V2는73/80, rawFP1/unsafe1로 실패. 노출120 적합성과 일반화를 구분한다. |
| Gemma31 / EXAONE33 / GLM Flash / Gemma12 | 각각 semantic115/106/104/112 of120. Gemma31·GLM·Gemma12에는 안전 gate 위반도 있었다. 크기·속도·공식 일반 benchmark만으로 다음 PASS를 예상할 근거가 없다. |
| Qwen14B 분류→추출 두 단계 | semantic93/120, rawFP11/unsafe6. 후단 차단으로 첫 raw READY를 지우지 않은 실패다. 분리 구조를 아직 안 해본 대안으로 제안하지 않는다. |
| Qwen32B facts3.0 / bounded thinking2.0 | 각각95/120 및109/120, rawFP3/2, unsafe1씩. Thinking 잘림3개를 모두 정답으로 가정해도112/120이므로 한도 확대만으로 통과한다는 가설도 이미 근거가 약하다. |

근거: [완료 Phase5.x 이력](../../docs/reports/phase5x_report.md), [Qwen3.8 V2](../../docs/reports/phase5x_native_qwen38_v2_minimal_report.md), [Gemma31](../../docs/reports/phase5x_native_gemma4_diagnostic_report.md), [EXAONE](../../docs/reports/phase5x_native_exaone45_diagnostic_report.md), [GLM](../../docs/reports/phase5x_native_glm47_diagnostic_report.md), [Gemma12](../../docs/reports/phase5x_native_gemma12_diagnostic_report.md). 서로 다른120·80 분모를 합친 모델 순위는 만들지 않았다.

## 새 미검증 선택지: 비교 2개, 우선 검토 1개

| 선택지 | 추가 정보가치 | 아직 없는 근거 / 판단 |
|---|---|---|
| **Ministral 3 14B Instruct 2512, Mistral 공식 GGUF Q4_K_M** | 지금까지 실행한 Qwen/Gemma/EXAONE/GLM과 다른 계열이다. 공식 원저자 GGUF, 한국어·system prompt·JSON 지원 표기와 작은 artifact가 있어 변환 출처·준비 비용을 함께 검토할 가치가 있다. | task 품질·정확 원문 인용·가구 한정·승인 경계는 미측정. 아래 native 특수 parser를 새로 검증해야 한다. **metadata/source 우선순위1**. |
| Mistral Small 3.2 24B Instruct 2506 | 공식 카드가 정밀 지시 따르기·반복 오류·function-call 개선을 명시한다. | 이 조사에서 exact 공식 GGUF artifact/변환 revision을 확정하지 않았다. BF16/FP16 공식 GPU 요구 약55GB는 현재 예산 밖이다. 별도 quant 출처와 전체 peak가 필요하다. 동일 Mistral 계열의 자동 두 번째 GPU 시도로 예약하지 않는다. |

공식 자료: [Ministral GGUF 카드](https://huggingface.co/mistralai/Ministral-3-14B-Instruct-2512-GGUF), [Mistral Small3.2 카드](https://huggingface.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506). 두 카드의 Apache2 표기와 지원 언어는 조사 근거이며 이 프로젝트 PASS 근거가 아니다. Ministral은 Instruct를 대상으로 하며 Reasoning 모델로 바꾸지 않는다. 카드의 temperature<0.1 권고를 확인했지만 나머지 sampler/window/seed와 native 실제 적용은 미정이다. 새로운 profile은 결과를 보기 전에 한 번 고정해야 한다.

Ministral의 관측 가능한 pin은 GGUF repository `mistralai/Ministral-3-14B-Instruct-2512-GGUF@74fac473c43357d7fb2671713608183cc72496d0`, 파일 `Ministral-3-14B-Instruct-2512-Q4_K_M.gguf`, **8,239,593,024B**, SHA256 **824e0f3373e69b84f2cae46fdcb9bd1ebc6ab3bfc7acc125d818b7b8178cc613**다. [고정 파일 페이지](https://huggingface.co/mistralai/Ministral-3-14B-Instruct-2512-GGUF/blob/74fac473c43357d7fb2671713608183cc72496d0/Ministral-3-14B-Instruct-2512-Q4_K_M.gguf)에서 SHA를, [main의 3줄 LFS pointer](https://huggingface.co/mistralai/Ministral-3-14B-Instruct-2512-GGUF/raw/main/Ministral-3-14B-Instruct-2512-Q4_K_M.gguf)에서 같은 SHA·정확 size를 확인했다. Weight payload는 받지 않았다. Pinned raw/API는 web 도구 접근 오류였으므로 metadata closure 완료라고 표시하지 않는다.

원본 BF16 저장소의 config 변경 commit은 `bbc49ba054267c5afcad5c6dfeb0d3d74cdd2ce6`로 확인했다. 이것이 GGUF 변환 시점의 source revision이라는 증거는 아직 없다. [공식 config](https://huggingface.co/mistralai/Ministral-3-14B-Instruct-2512-BF16/blob/bbc49ba054267c5afcad5c6dfeb0d3d74cdd2ce6/config.json)는 text40층/hidden5120/FFN16384/KV8×128/vocab131072 및 YaRN을 명시한다. 실제 GGUF shape/dtype/header, tokenizer·template bytes와 license 원문 보존은 다음 metadata 검토 대상이다.

## 현재 runtime과 비용 경계

고정 `f072b103714dfa1eee531f80b24512faf38e3dd2`에는 [Mistral3/Ministral3 converter](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/conversion/mistral3.py), [40층14B loader/graph](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/models/mistral3.cpp), [Ministral 전용 parser](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/common/parsers/ministral3.cpp)가 있다. 등록은 actual CUDA 실행 성공이 아니다.

특히 전용 parser는 system/assistant content를 typed block으로 바꾸고 schema 응답을 JSON fence로 감싼 뒤 final content를 분리한다. JSON-only에서도 `grammar_lazy=false`와 함께 `[TOOL_CALLS]` trigger metadata를 남기는 코드가 있다. 기존 Qwen의 trigger-empty 조건·raw 출력 기대를 이름만 바꿔 재사용하면 안 된다. 필요한 새 검사는 실제 system/user 전체 렌더링, grammar의 final JSON 제한, fence 제거 후 final bytes, optional reasoning/tool 경계다. 이는 transport/parser 호환성 검사이며 semantic/rawFP/unsafe 기준 변경을 허용하지 않는다. 자동생성 HF 사용 예시의 최신 binary 설치 명령은 현재 f072 증거로 간주하지 않는다.

부분 자원 screening은 full-file7857.888MiB + F16 KV `40×4096×8×128×2(K,V)×2B`=640MiB + 단일 vocab F32확장2560MiB = **11057.888MiB**다. 기존 GPU3 기준 free36373−별도margin7275=29098MiB 안에 나머지18040.112MiB가 남는다는 산술일 뿐, 완전한 peak 추정·상한·실측이 아니다. Output tying/복제, dequant pool, graph/workspace, driver, loading/단편화를 실제 metadata와 source로 채워야 한다. A100 native FP8을 가정하지 않고 RTX32GB/SM120도 미검증으로 둔다.

최근 저장된 Qwen3.6 download 최소 free22,601,879,552B는20.5GiB floor 위 약590MB뿐이며 현재 free가 아니다. 새8.24GB 파일을 곧바로 받을 근거가 없다. 현재 Qwen3.6은 실행 중이므로 비활성 artifact로 취급하지 않는다. FAIL 뒤 own 종료·보존이 완료되고 root의 fresh disk/정확 비활성 파일 검사와 별도 회수 절차가 충족되어야 새 download를 검토할 수 있다. 기존 binary/guard/schema/채점/replay 코어는 불변 부분의 증거만 승계한다.

## 실행을 유한하게 만드는 결정 규칙

1. Qwen3.6의 실제 첫 결과와 최초 독립 회계가 완료될 때까지 다음 GPU 후보를 시작하지 않는다. FAIL이면 해당 exact candidate의 반복·선별 재시도·V2·unused80은0회다.
2. 새 Ministral은 **metadata/source 검토1건**으로 먼저 제한한다. 공식 출처·현재 f072·whole-memory·원문 보존이 맞지 않으면 품질 호출 전에 보류한다. 현 단계에는 새 환경/설치/공통 runtime 변경이 필요하다고 가정하지 않는다.
3. 사전검토를 통과하고 실제 비교를 진행한다면 기존 generation2/single/prompt/gold/scorer 그대로 첫120×1+warmup5만 사전 등록한다. Schema120/120, semantic≥114/120, rawFP0/58, unsafe0/120, raw관측120/unknown 처리 및 원래 분모를 유지한다. Parser 수는 진단 지표이며 별도 preset gate를 새로 만들지 않는다. Downstream 차단을 rawFP 삭제로 바꾸지 않는다.
4. 이 새 계열도 실패하면 Small3.2·다른 quant·seed·prompt를 연속 대기열로 돌리지 않는다. **자동 GPU 후보 순회를 멈추고** 새 학습/입력설계가 왜 기존 실패와 다른지 증거를 먼저 작성한다. 공식자료 비교는 계속하되, 현재 근거로는 두 단계/facts/thinking 재시험이나 lexical 사후필터를 새 해법으로 추천하지 않는다.
5. 이후 별도 계약을 고려하려면 기존 gold의 의미와 rawREADY 회계를 보존하고, 실패 사례만 위한 규칙 없이 일반화 가능한 차이를 명시해야 한다. 사람의 의미 검토·독립 학습자료에 기반한 과업 적응은 장기 연구 선택지이지 현재 승인된 학습/평가 작업이 아니다. 기존 gold는 AUTO-GENERATED / NOT HUMAN VERIFIED이며 노출120의 선택 편향, 이미 본 V2, untouched80 경계를 유지한다.

이 메모에서 수행한 것은 위 기존 문서와 source 읽기·공식 web metadata 확인·산술·이 파일 작성뿐이다. 신규 weight 다운로드/설치/cleanup/native/HTTP inference/GPU/테스트/회귀/재생/평가·미사용 dataset 접근·production 변경은 모두0이다. 로컬 source SHA: converter `2557b19ac439836ae3deebefe5281b38e8ae4cb204c6f59815288de3e1d250ef`, loader `3cc33d10acfcc7bbabe93a76dbcaf5b138306481531982e1c2c2643c74489cbd`, chat dispatcher `ed5db316e93459c6528526633b11943f4b4611634c773b4eab30a66c1f4a91b3`.
