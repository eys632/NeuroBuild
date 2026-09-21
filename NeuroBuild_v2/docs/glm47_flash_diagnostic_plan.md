# GLM-4.7-Flash 첫 단회 진단 계획

상태: CPU·최초 GPU runtime 계약 PASS, epoch1 시간 제한 종료, 사전동결 전, 품질 호출0.
Phase5.x 미완료·모델 미채택이다. 완료한 runtime 증거를 재사용하고 새 own epoch와
현재 GPU 예산을 연결한 동결 commit/push 뒤에만 최초 평가를 시작한다.

기존 노출120개에 새 GLM 후보를 한 번 적용해 1차 Quality Gate를 확인한다.
Dataset은 `requirement_hardening_v1_exposed_regression.jsonl`이며 unseen이 아니다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. 기존 gold·scorer·분모·오류는 변경하지 않는다.
이전 Qwen/Gemma/EXAONE 평가·독립 재생은 반복하지 않는다.

## 고정 조건

`ggml-org/GLM-4.7-Flash-GGUF@7559e96b7e324ab405897dc2b91492b0f376ad4a`,
파일 `GLM-4.7-Flash-Q4_K.gguf`, 실제 header의 Q4_K_M을 사용한다.
SHA `b6019edc5fbe37d3660d2e994d16c839a7855a6f03362c5dcf8142ba479cd0d2`.
47개 main layer/no-MTP/Q8 output·K_B의 관측 구조와 원본 대비 범위는
[준비 보고서](reports/phase5x_glm47_flash_preparation_report.md)에 있다.
원본 card의 MIT 표기와 GGUF repository의 license 미선언을 구분하며 내부 연구 후보로만 다룬다.

실행 variant는 `glm47-flash-gguf-nonthinking-v1`, native source는
`f072b103714dfa1eee531f80b24512faf38e3dd2`, 명시 profile은 `glm47_flash_nonthinking_llama_cpp`다.
T1/P.95는 공식 일반 benchmark 값이며 한국어 nonthinking 전용 권고로 표현하지 않는다.
Project neutral 값은 K0/min_p0/presence0/frequency0/repeat1/window0/seed42,
samplers temperature→top_k→top_p→min_p다. enable_thinking=false, 원본 template, override0이다.
공식 tokenizer normalizer=null, 공개20 native ID·원문 일치와 전체 입력 길이 검증을 통과했다.
[CPU 보고서](reports/phase5x_glm47_flash_native_cpu_report.md).

Production generation2.0/single/promptv2/decision-branch schema,
output768/timeout120, ctx4096/sequence1/batch64/ubatch64/F16KV/flashOFF/graphsOFF를 고정한다.
노출120개 최대 입력3257+출력768=4025/4096이다. Physical GPU3/logical CUDA0/TP1만 사용한다.
현재 free/utilization과 예상 whole peak28672MiB+안전 margin 비교를 통과해야 기동한다.
예상 peak는 하드 할당 상한이 아니며 감시기는 자원 여유 감소 시 자신의 서버만 종료한다.

원문 입력·출력 NFC repair, 출력 수선, fallback, 선택적 재시도는 없다.
Native parser는 nonthinking 요청에서도 완결된 reasoning을 별도 필드로 분리할 수 있다.
평가에는 final content만 보존하며 reasoning과 tool invocation은 저장하지 않는다.

## 실행 범위와 결과 판단

Warmup5는 별도 기록하고 평가120×1만 수행한다. CLI 기본 trials3을 사용하지 않고
`--trials 1 --warmups 5`를 명시한다. 첫 warmup 전 source/profile/sampling/model/tokenizer/
runtime epoch/prompt/schema/dataset/scorer/gate를 해시로 동결하고 clean commit/push·원격 일치를 확인한다.
이미 완료한 공통 runtime 검사와 GLM epoch1의 startup/public1/resource1을 반복하지 않는다.
Epoch1은 평가 전7200초 제한으로 자체 종료했다. 새 epoch2는 동일 model/source/template/profile/
메모리 설정을 유지하고 log/report 경로와 process identity만 구분한다. 새 startup의 자체 listener와
health/models/props를 확인해 epoch1의 완료 public/resource 증거에 명시적으로 연결한다.
새 평가 epoch의 identity·남은 시간·resource guard 상태를 첫 요청 직전에 확인한다.
평가 warmup5는 HTTP 평가 요청이다. 별도로 native 기본 startup empty-run warmup이 켜져 있으며
이는 평가 호출 수나 품질 분모에 포함하지 않는다. Startup의 HTTP 생성0회는 내부 decode0회를 뜻하지 않는다.

| Gate | 기준 |
|---|---:|
| Generation schema | 120/120 |
| 의미 정확도 | ≥114/120 |
| Raw READY false positive | 0/58 |
| Unsafe accepted READY | 0/120 |
| Raw decision 관측 | 120/120; 미관측 별도 보고 |

Parser/adapter, acceptedFP, FN/62, 오류·timeout·truncation, latency 평균/p95,
전체 epoch aggregate VRAM 증가·최소free와 warmup 결과를 보존한다.
실제 객체 선택·승인·IFC 적용은 포함하지 않는다. 새125개 final JSON만 고정 source로 독립 CPU 재생해
원본 행과 집계의 일치를 확인한다. Accounting PASS와 품질 PASS를 구분한다.

명백한 기준 미달이면 같은 후보 반복·V2·미사용 holdout을 실행하지 않고 다음 후보를 판단한다.
통과/경계선인 경우에만 미확정 사실과 재현성 검증에 필요한 최소 반복 범위를 먼저 정한다.
자동 전체3회 반복은 없다. 기존 V2는 이미 노출된 자료이며 새 unseen 평가로 사용할 수 없다.
미사용80개 초안은 첫 gate 통과 전 접근하지 않으며 후속 평가 여부와 동결은 별도로 판단한다.

평가 후 해당 NeuroBuild guard의 정확한 identity를 확인해 종료하고 GPU3 VRAM 반환을 확인한다.
다른 사용자의 process에 신호를 보내지 않고 killall·광범위 pkill·GPU0/1/2 fallback은 사용하지 않는다.
결과·독립 검토·필요한 변경별 regression·보고서·checkpoint push를 완료한다.
비필수 runtime 최적화는 future optimization이다. 첫 gate만으로 Phase5.x 완료나 최종 모델 채택을 선언하지 않는다.
