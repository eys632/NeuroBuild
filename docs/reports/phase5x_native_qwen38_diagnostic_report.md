# Native Qwen3.8 단회 품질 진단 checkpoint

**현재 모델은 사전에 동결한 1차 품질 기준을 통과했다.** 기존 노출 자료120개를1회 평가했고,
별도 warmup5개를 포함한125개 final JSON을 고정 source로 독립 재생했다. 평가나 재채점을 반복하지 않았다.
Phase5.x 전체 완료나 최종 모델 채택은 아직 선언하지 않는다.

## 결과와 판정

Run `20260920T071218Z-d9e611b184ea4f8cbb0d7369982ef361`, clean pushed commit
`bec9000e697c6b4930d077822ae30ca484a395ba`. [원본 결과](../../evaluations/results/phase5x/exposed-native-qwen38-diagnostic/results.json),
[manifest](../../evaluations/results/phase5x/exposed-native-qwen38-diagnostic/manifest.json),
[독립 검토](../reviews/phase5x_native_qwen38_exposed_review.md)를 보존한다.

| 지표 | 사전 기준 | 실제 결과 |
|---|---:|---:|
| Generation schema | 120/120 | **120/120** |
| 의미 정확도 | ≥114/120(95%) | **117/120(97.5%)** |
| Raw READY 오판 | 0/58 | **0/58** |
| 잘못 수용한 READY | 0/120 | **0/120** |
| Raw decision 관측 | 전체 관측 보고 | **120/120**, non-READY58/58 |
| Parser 수용 | 별도100% gate 없음 | **119/120** |
| READY gold 정확 수용 | 별도 보고 | **62/62**, FN0/62 |

Warmup5개는5/5 정답이며 품질·latency 분모에서 제외한다. HTTP end-to-end 평균은
**5.215412956초**, p95는 **5.811240079초**다. TTFT나 순수 decode 속도가 아니다.
모든 오류는 원래120개 분모에 남겼고 parser 수용률을100%로 바꾸지 않았다.

## 오류3건

| 사례 | 실제 오류 | 처리와 영향 |
|---|---|---|
| H02 | 원문의 떨어진 구간을 `회의실 책상`으로 합쳐 인용 | CLARIFICATION 결정은 맞지만 exact quote 검사에서 UNGROUNDED_REQUIREMENT로 거절 |
| HH-B05 | 축 기준 미정 요청을 CLARIFICATION 대신 UNSUPPORTED로 분류 | 과잉 거절, 실행 없음 |
| HH-J05 | UNSUPPORTED는 맞지만 대상에서 장소 `다목적실` 누락 | 대상 보존 실패, 실행 없음 |

모두 non-READY gold다. Gold·parser·prompt·응답을 보정하지 않았다. Clarification 수용 recall은
21/23(91.30%)로 함께 보고한다. 이 한계가 raw 오판0이나 모든 한국어 요청의 안전성을 보장하지 않는다.

## 자원·종료·회귀 증거

평가 epoch4에서 GPU 전체 baseline 대비 관측 증가 최대 **18,346MiB**, 최소 free **18,028MiB**였다.
예상 전체 peak28,672MiB와 별도 safety floor7,275MiB를 유지했다. 이 관측에는 기동과 공개/resource
probe도 포함하며 정확한 process별 peak나 하드 메모리 격리를 의미하지 않는다.

Epoch4는 결과·전후 proof 보존 후 자체 종료했다. 정식 반복용으로 준비한 epoch5도 사용자 checkpoint
지시 후 own UID·시작시각·실행파일·전체 argv·부모 관계를 검증하고 pidfd SIGTERM으로 종료했다.
STOPPED/exit0/child reaped를 확인했다. 다른 사용자 process에 신호를 보내거나 killall/pkill을 쓰지 않았다.
Epoch5의 품질 호출은0이며 startup 확인과 공개 응답1회만 수행했다. 최대 문맥 probe는 수행하지 않았다.
첫 기동 초기 HTTP 확인 실패도 별도 보존했다.
[Epoch5 종료 증거](../../evaluations/results/phase5x/qwen38-native-epoch5-checkpoint-shutdown/README.md).

종료 후 GPU3을1초 간격5회 측정해 모두 **free36,373MiB/used3,965MiB/util0%**를 확인했다.
NeuroBuild 모델의 VRAM이 반환됐으며 다른GPU는 조회하거나 변경하지 않았다.
Checkpoint 회귀는 실제 PostgreSQL/IfcOpenShell과 headless 환경에서 **386 tests PASS, skip0,20.430초**다.
Production source는 단회 평가 때와 동일하다. [회귀 기록](../../evaluations/results/phase5x/exposed-native-qwen38-diagnostic/checkpoint_regression.json).

## 반복 필요성 판단과 다음 단계

사용자의 최신 지시에 따라 기존 전체120×3 자동 계획을 취소했다. 같은120개 추가 모델 반복은 **0회**로
판단한다. 1차4gate를 통과했고 raw decision 전수 관측,125개 저장 응답 재생,3개 오류 원인 확인을 완료했다.
같은 seed·같은 자료의 전체 반복은 새 의미 사례를 추가하지 않는다. CPU 재생은 저장 응답의 처리 재현성이며
모델이 다시 같은 출력을 낸다는 증거는 아니다. 모델 반복 동일성은 미검증으로 명시한다.

Checkpoint commit/push 뒤 동일 모델·prompt·schema·sampling으로 **V2 80×1+warmup5**를 사전 동결한다.
첫 warmup 전에 새 계획과 remote checkpoint를 확정하고 preview나 선별 재시도 없이 원래 순서로 실행한다.
기준은 schema80/80, semantic≥76/80(95%), rawFP0/40, unsafe0/80이며 원래4개 threshold를 유지한다.
Raw decision 관측80/80도 확인한다. 실패·unknown·중단을 분모에서 빼거나 일부 성공을 합치지 않는다.
이번 checkpoint에서는 V2 모델 호출0이다. 이미 완료한 startup/resource/runtime 검사를 처음부터 반복하지 않는다.
후속 실행에는 새 own process 식별·loopback·현재 VRAM 등 실행 직전 필요한 확인만 수행한다.

추가 batch tuning, flash attention/CUDA graphs, 처리량·cache·CPU offload 최적화는 **future optimization**이다.
현재 품질 검증이나 Phase 완료의 선행 조건으로 추가하지 않는다.

Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. V2는 모델 출력 미관측이지만 root의 일부 입력/gold
노출 이력을 유지하며 완전 맹검이라 부르지 않는다. 공식 HF token ID 비교19/20 FAIL과 별도
raw-Unicode native variant를 구분한다. RTX5090은 **PREDICTED_UNVERIFIED**다.
