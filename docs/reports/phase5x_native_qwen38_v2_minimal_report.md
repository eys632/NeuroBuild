# Native Qwen3.8 V2 단회 평가 — FAIL

1차 진단117/120 PASS 후 별도 동결한 V2 최소 평가가 **73/80, rawFP1/40, unsafe1/80**으로 실패했다.
현재 후보를 채택하지 않고 다른 모델 후보를 비교한다. 같은 후보의 추가 반복과 Phase6 진행은 하지 않는다.
기존125개 진단과 독립 재생 PASS는 그대로 보존하며 다시 실행하지 않았다.

## 실행과 품질 결과

Run `20260920T075607Z-1c4b930f002d484f962d4f4458b44cdb`, clean pushed source
`1571d327d78207017277d96bce7d2c822dc4d41b`. Candidate freeze SHA
`e09a143794d7c9ddaae6215502ba85314222c6b9a184bee09b417ab0e4cd5976`의121개 SHA를 실행 전후 확인했다.
사용자 지시를 반영한 별도 addendum로80×1+warmup5를 수행했다. 기존 dataset freeze의80×3 기록은 덮어쓰지 않았다.
Generation2.0, single pipeline, 기존 promptv2/branch schema, native non-thinking profile,
output768/timeout120/ctx4096/parallel1/batch64/ubatch64다. 자동 재시도나 응답 보정은 없다.

| 관측 | 결과 | 사전 기준 |
|---|---:|---:|
| Generation schema | 80/80 | 80/80 |
| Adapter / canonical parser | 79/80 | 별도 관측 |
| Semantic rubric | 73/80 (91.25%) | ≥76/80 |
| Raw READY FP | 1/40 | 0/40 |
| Unsafe accepted READY | 1/80 | 0/80 |
| FN | 3/40 | 별도 관측 |
| Raw decision 관측 | 80/80 | 80/80 |
| 오류 | UNGROUNDED_REQUIREMENT1 | 분모 제외 없음 |

HTTP end-to-end 평균5.490056751971133초/p95 6.278982890769839초다. TTFT 또는 decode 속도는 아니다.
Warmup은 schema5/5/semantic4/5로 본시험에서 제외했다. 모든85개 final JSON을 보존했으며
별도 reasoning은 보존하지 않았다. Unknown/미보존 응답은0이다.

실패7건은 원문 인용 재배열1건, 실제 출입문 READY1건, 정상 요구사항 과잉 거절2건,
non-READY 대상 범위 불일치3건이다. 마지막3건은 비실행 판정 자체는 맞았지만 고정 target rubric에서 실패했다.
그3건의 표현을 더 관대하게 해석하더라도 실제 출입문을 가구 이동으로 수용한 오류가 남아 safety gate는 FAIL이다.
Gold/parser/점수를 사후 변경하지 않았다. 실제 IFC/tool 실행은 없었다.
각 사례와 격리 인용 대조의 범위는 [독립 검토](../reviews/phase5x_native_qwen38_v2_minimal_review.md)에 기록했다.

## 자원·종료·재현

Epoch6 child3567367/guard3566951의 own UID/start ticks/전체 argv/부모/loopback을 확인했다.
동일 build/model/config의 과거 계약·자원 검증을 재사용하고, 현재 epoch는 health GET1과 identity만 최소 확인했다.
기존 startup/resource/public suite를 처음부터 반복하지 않았다. 실행 전 잔여3,400.967초가 사전 예산3,150초 이상이었다.

전체 lifetime762.113초/1,349표본에서 GPU3 aggregate baseline 증가 최대18,344MiB,
free 최소18,030MiB였다. 예상 peak28,672MiB와 safety floor7,275MiB를 유지했다.
이 값은 process별 peak 또는 allocator hard cap이 아니다. GPU0/1/2 fallback은 없었다.

완료 후 검증한 own guard에만 pidfd SIGTERM을 보냈다. 기존 lifecycle이 own child group에 TERM 후
잔여 group KILL을 보내고 child를 exit0으로 회수했으므로 STOPPED/exit0/reaped를 확인했다.
광범위 process matching이나 다른 사용자 process 신호는 없었다. 종료 뒤5회 모두 GPU3
free36,373MiB/used3,965MiB/util0%로 시작 전 수준에 복귀했다.

고정 source snapshot29파일로85개 저장 응답을 독립 CPU 재생했으며 adapter/parser/평가행/모든 집계가 일치했다.
이는 저장 응답 처리의 재현성이고 모델 출력을 다시 생성한 결과가 아니다. 기존125개 재생도 반복하지 않았다.
Production src/scripts/tests는 직전386 PASS/skip0/20.430초 이후 변경0이다. 당시 실제 PostgreSQL/IfcOpenShell
회귀를 승계하며, 이번 증거·문서 변경에는 hash/원본 일치/링크 검사를 수행한다. 신규 준비 helper의 CPU10검사와
replay fixture10·변조61거절 검사는 실행 전에 이미 통과했다. 이를386개 회귀 수에 더하지 않는다.

[원본과 종료 증거](../../evaluations/results/phase5x/v2-native-qwen38-minimal/README.md),
[독립 replay](../../evaluations/results/phase5x/v2-native-qwen38-minimal/independent_replay.json),
[기존 단회 보고서](phase5x_native_qwen38_diagnostic_report.md).

## 다음 판단과 한계

Semantic/rawFP/unsafe 세 gate에서 명백한 FAIL이므로 재현성 반복으로 해결할 경계선 결과가 아니다.
다음 작업은 다른 후보의 공식 자료·기존 runtime 호환성·전체 VRAM·디스크 조건 비교다.
추가 최적화는 future optimization이며 품질 실패를 가리기 위해 runtime 검증을 반복하지 않는다.
Application/Domain/IFC 계약과 target 확인·별도 proposal 승인 경계는 변경하지 않았다.

V2는 이제 MODEL_OUTPUT_SEEN / EXPOSED다. 이후 조정의 regression 자료로만 해석하고 새로운 unseen 성공으로
부르지 않는다. Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED이며 기존 입력 노출 addendum도 유지한다.
공식 HF token ID19/20 FAIL과 raw-reference20/20은 별개다. NFC 보정은 없다.
RTX5090은 PREDICTED_UNVERIFIED이고 사람 검수·실제 IFC 적용·외부 pilot을 검증한 결과가 아니다.
