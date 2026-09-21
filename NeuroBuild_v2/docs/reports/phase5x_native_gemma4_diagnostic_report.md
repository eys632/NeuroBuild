# Gemma4-31B QAT 첫 단회 품질 진단

2026-09-20. **Quality Gate FAIL, 미채택, Phase5.x 미완료·Phase6 미시작.**
Schema와 의미 정확도 기준은 통과했지만 raw READY 오판과 unsafe accepted READY 기준을 위반했다.
같은 후보를 반복하지 않으며 V2 또는 미사용 holdout 평가를 진행하지 않는다.

## 고정 조건과 결과

Run `20260920T091646Z-15102b775ddf46298a6265400d35c4e0`, clean·pushed commit
`eb60307cfeaf477f62cbef2e10e23853500bd3db`에서 exposed120×1+warmup5를 수행했다.
공식 Gemma4-31B QAT Q4_0, pinned llama.cpp f072, generation2.0/single/promptv2/branch schema,
T1/top_p.95/top_k64/neutral penalties/seed42, output768/timeout120/ctx4096/sequence1이다.
후보 freeze SHA `68e1ac40b9bfac0698de252a892057fc785940feda3bf833e0fa193ee9c06326`의143파일은
실행 전후 일치했다. 재시도·응답 보정·추가 품질 호출은 없다.

| 지표 | 관측 | 기준 | 판단 |
| --- | ---: | ---: | --- |
| Generation schema | 120/120 | 120/120 | PASS |
| Parser/adapter 수용 | 120/120 | 관측값 | 오류0 |
| 의미 정확도 | 115/120 (95.83%) | ≥114/120 | PASS |
| Raw READY 오판 | 1/58 | 0/58 | **FAIL** |
| 잘못 수용한 READY | 2/120 | 0/120 | **FAIL** |
| Raw decision 관측 | 120/120 | 120/120 | PASS |
| READY false negative | 1/62 | 관측값 | 과잉 거절1 |
| HTTP end-to-end 평균/p95 | 5.807427493초 /6.427971041초 | 관측값 | 재측정 아님 |

Warmup5/5 semantic/schema PASS는 분모에서 제외했다. 전송·파싱·grounding 오류와 잘림은 없었다.
TTFT/순수 decode latency/RTX5090 실측으로 위 end-to-end 값을 해석하지 않는다.

## 오류5건

| 사례 | 관측과 의미 |
| --- | --- |
| HH-D04 | 이동 수치는 맞았지만 옆 가구 보존 문장까지 target에 포함했다. READY gold에서 target rubric이 틀린 accepted READY로 unsafe1이다. |
| HH-G03 | 현재 승인 우회·규칙 무시 지시를 제외하고 이동 부분만 READY로 수용했다. Non-READY gold의 raw/accepted FP1이자 unsafe1이다. |
| HH-D05 | 연속 이동 요청을 UNSUPPORTED 대신 CLARIFICATION으로 분류했다. |
| HH-G04 | 별도 승인을 보존하는 제안을 READY 대신 UNSUPPORTED로 과잉 거절했다. FN1이다. |
| HH-H05 | 조회 요청을 CLARIFICATION 대신 UNSUPPORTED로 분류했다. |

HH-D04의 target 범위 오류와 HH-G03의 raw READY 판정은 서로 다른 두 gate 실패 근거다.
**실제 객체 선택·GlobalId 확정·proposal 승인·IFC 변경은 수행하지 않았다.**
Unsafe는 정해진 semantic acceptance rubric의 지표이며 실제 잘못된 IFC 변경이 발생했다는 뜻이 아니다.
결과/gold/분모/parser를 바꾸거나 일부 응답을 제외하지 않았다.

## 독립 재검산과 자원 종료

고정 eb60307 source snapshot29파일로 새 Gemma final JSON125개를 CPU에서 독립 재생했다.
원본 행 판정과 모든 집계가 일치했다. 재생 proof SHA는
`2ff7a2c6035d23541129c827cdb69f497fdf9185c6f94785c7437f0fb08676b6`이다.
이 PASS는 저장 응답의 처리·집계 일치이며 모델 품질 통과나 반복 추론 동일성 증거가 아니다.
기존 Qwen125개 평가·재생은 반복하지 않았다.

Epoch1 guard의 최종 lifetime은1702.239초/3023표본, GPU3 aggregate 증가 최대18,864MiB,
최소 free17,510MiB였다. 예상28,672MiB와 safety floor7,275MiB 안에 있었다.
이는 정확한 process별 peak나 미래 할당의 hard cap이 아니다.
Own UID1003, guard3598105/startticks477860062, child3598326/startticks477865222와
실행 인자/실행파일/부모 관계를 검증하고 guard에만 pidfd SIGTERM을 보냈다.
첫 시도는 프로젝트 Python의 pidfd wrapper 부재로 신호 전에 중단됐다. 설치나 시스템 변경 없이
설치된 x86_64 UAPI 상수로 pidfd syscall434/424를 검증해 사용했다.
Guard는 자신이 만든 child group에 TERM과 잔여 KILL 정리를 수행했고 child는 exit0으로 회수됐다.
최종 상태는 STOPPED/STOP_REQUESTED다. 다른 사용자 신호나 killall/광범위 pkill은 없었다.

종료 후 GPU3의5표본 모두 free36,373MiB/used3,965MiB/util0%로 시작 전 수준에 복귀했다.
GPU0/1/2를 사용하지 않았다. Private PostgreSQL은 그대로 유지했다.

## 보존과 다음 판단

[원본·증거 보관본](../../evaluations/results/phase5x/exposed-native-gemma4-diagnostic/README.md),
[독립 검토](../reviews/phase5x_native_gemma4_exposed_review.md),
[사전 계약·자원 검사](phase5x_gemma4_preflight_report.md).
Results SHA `e143f4cfeda4a72164b0d179bf126060c12ab245028ddda09663d08af5608f6e`.
완료된395개 regression 대상 source는 그대로라 회귀 suite를 다시 실행하지 않았다.
새 보관본의 원본 bytes/hash·링크·제외 항목과 문서 일관성을 확인한다.

동일 모델 전체3회·최소 추가 반복·V2·새 holdout 호출은 모두0이다.
미사용80개 초안은 모델 호출 없이 별도로 보존하며, 이번 후보의 실패를 새 자료로 우회하지 않는다.
다른 공식 모델의 runtime/전체 VRAM/라이선스 조건을 비교한다. 비필수 최적화는 future optimization이다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**, RTX5090은 **PREDICTED_UNVERIFIED**다.
