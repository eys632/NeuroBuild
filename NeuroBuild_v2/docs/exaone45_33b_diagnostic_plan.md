# EXAONE4.5-33B 첫 단회 진단 계획

> 후속 결과: 동결한 첫120×1+warmup5는 의미 정확도106/120으로 FAIL했다.
> 추가 반복·V2 없이 종료했고 새125개 독립 재생과 GPU3 반환을 보존했다.
> [결과 보고서](reports/phase5x_native_exaone45_diagnostic_report.md). 아래는 사전동결 당시 계획이다.

상태: **DRAFT — 별도 원문 보존 variant CPU·GPU runtime 검증 완료, 사전동결 전, 품질 호출0.**
[자원·계약 계획](exaone45_33b_resource_plan.md)의 선행 gate를 통과한 뒤 별도 freeze를 만든다.
이 문서나 metadata 다운로드만으로 실제 품질 평가를 시작하지 않는다.

## 최초 질문과 고정 조건

공식 EXAONE4.5-33B Q4_K_M을 기존 공개된120개에 한 번 적용해 1차 품질 기준을 만족하는지 확인한다.
서로 다른 모델 비교이며 실패한 Qwen/Gemma의 같은 모델 반복이 아니다.
입력 자료는 이미 노출된 `requirement_hardening_v1_exposed_regression.jsonl`이며 unseen으로 부르지 않는다.
Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED다. 이전 오류·gold·분모·scorer를 수정하지 않는다.

공식 GGUF revision0e969634ef24db05151b435970297a6dee634b7e,
고정 native f072/명시 exaone45_nonthinking_llama_cpp profile,
한국어T.6/P.95/K20/presence1.5/nativewindow64/repeat1/frequency0/min_p0/seed42,
samplers penalties→top_k→top_p→min_p→temperature, enable_thinking=false를 사용한다.
Window64는 prompt와 generated history 모두를 포함한다. 모델 카드의 4값과 native/project 조건을 구분한다.
Production generation2.0/single/promptv2/decision-branch schema,
output768/timeout120, ctx4096/sequence1/batch64/ubatch64/graphsOFF/flashOFF/F16KV다.
Final content만 보존하며 reasoning/tool invocation/repair/fallback/선별재시도는 없다.

실행 variant는 `exaone45-gguf-continue-free-raw-unicode-korean-v1`이다.
원본 native template의 system 누락은 공식 render와 공개18개가 같은 별도 continue-free template로 해결한다.
공식 HF token-ID18/20 FAIL을 그대로 보존하고 NFC만 끈 별도 reference20/20 PASS를 구분한다.
입력·출력 NFC 보정은 없으며 모든 Unicode의 동등성을 주장하지 않는다.
실제 CPU vocab-backed 길이 검증에서 기존120입력+출력768 최대2890/4096토큰이다.
기존V280 길이만 확인했으며 새 미사용80개는 읽거나 평가하지 않았다.

## 평가와 중단 판단

Warmup5를 별도 기록하고 평가120×1을 한 번 수행한다. CLI 기본 trials3을 사용하지 않고
`--trials 1`을 명시한다. 실제 최초 warmup 전에 profile/source/sampling/tokenizer variant/runtime epoch/
manifest/prompt/schema/dataset/scorer/gate를 해시로 동결하고 clean commit/push와 원격일치를 확인한다.
사전 완료된 공통 runtime 검사는 반복하지 않으며 현재 own epoch/free/util/남은시간을 확인한다.
실패하거나 중단된 호출도 감추지 않고 error/unknown/truncation/raw관측률에 보고한다.

| Gate | 기준 |
| --- | ---: |
| Generation schema | 120/120 |
| 의미 정확도 | ≥114/120 |
| Raw READY false positive | 0/58 |
| Unsafe accepted READY | 0/120 |
| Raw decision 관측 | 120/120; 미관측은 별도 명시 |

Parser/adapter pass, acceptedFP, FN/62, latency평균/p95, 전체 lifetime aggregate VRAM 증가와 최소free,
warmup 결과를 함께 보존한다. 실제 IFC 객체 선택·승인·apply는 이 평가에 포함하지 않는다.
저장된 새125개 final JSON은 고정 실행소스 snapshot으로 독립 CPU 재생하여 집계일치를 확인한다.
기존 완료 Qwen/Gemma125개를 재생하거나 재평가하지 않는다. Accounting PASS와 quality PASS는 구분한다.

명백한 기준 미달이면 같은 후보 반복·V2·미사용 holdout0회로 종료하고 다른 후보 판단을 한다.
1차 gate 통과/경계선에만 남아 있는 불확실성과 최소검증 범위를 먼저 정한다.
자동3회 전체 반복은 없다. 기존 V2는 MODEL_OUTPUT_SEEN/EXPOSED이며 새로운 unseen 결과가 될 수 없다.
미사용80개 초안은 별도 authoring/exposure/독립검토 기록이 있는 ignored draft다.
후속 실행 여부·고정 자료·사전 freeze는 첫 gate 결과를 보고 별도로 결정한다.

결과 보존 후 해당 NeuroBuild guard만 identity 확인하여 종료하고 GPU3 free 반환을 확인한다.
타인process신호/killall/광범위pkill/GPU0/1/2fallback은 없다. 새로운 변경에 필요한 regression과
보고서/독립검토/commit/push를 완료한다. 비필수 runtime tuning은 future optimization이다.
첫 gate 통과만으로 Phase5.x 완료/모델 최종채택/RTX 실측을 선언하지 않는다.
