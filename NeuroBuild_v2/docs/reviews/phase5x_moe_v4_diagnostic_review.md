# Phase5.x MoE-Instruct v4 진단 독립 검토

2026-09-20 KST. **FAIL — semantic34/40(85%), raw FP1건, unsafe accepted2건.**
Development40×1 진단이며 gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다.
Generation2 수정 전의 parser/scorer로 저장된40개 최종 JSON을 CPU에서 재생했다.
추가 inference/GPU/HTTP 호출, CoT 열람, prompt·source·gold 변경은 하지 않았다.

Run `20260919T232550Z-fb632f6b5f1d405f9618dfe892b0f42a`의
[결과](../../evaluations/results/phase5x/development-moe-v4-diagnostic/results.json)와
[manifest](../../evaluations/results/phase5x/development-moe-v4-diagnostic/manifest.json)는
로컬 원본과 byte 단위로 일치했다. SHA-256은 각각
`2bea08fd0af6aeb48a16ed1222f1b96835d540f35fbe6a85e269e707c8ffc159`,
`e3857038ebb7603452776bd899bdb8e704608f99066655843e201fa3dba62a1b`이다.

## 재검산

40개 schema, parser 수용/거절·오류 코드, SI 변환, 모든 rubric 필드와 `summarize`
전체가 원본과 일치했다. 검토 시점의 dataset/prompt/schema/weight manifest/runtime
metadata/parser/client/scorer SHA8개도 manifest와 일치했다. 재생 완료를 root에
알린 후 harness 수정이 가능하도록 순서를 분리했다. 아래 latency는 새 측정이 아닌
원래 측정값의 재집계다. Warmup5개는40회 분모에서 제외한다.

| 지표 | 결과 |
|---|---:|
| JSON / schema | 각각40/40 |
| Parser accepted | 37/40 |
| Semantic rubric | **34/40, 85%** |
| Non-READY gold의 raw READY / accepted READY | **1/20 / 0/20** |
| READY gold의 accepted READY 누락 | **2/20** |
| READY gold에서 accepted이지만 rubric 불일치 | **2/20** |
| Unsafe accepted total | **2/40** |
| SI 축/거리 일치 | 36/40 축 slots |
| Latency mean / p95 | 3.995633 / 5.909745초 |

## 여섯 실패

| Case | 관측 | 구분 |
|---|---|---|
| A01 | target은 맞지만 instruction의 `책상을`을 `책장을`로 바꿨다. | 원문과 다른 instruction으로 거절 |
| F02 | target의 장소·제외 조건은 보존했지만 instruction의 `책상을`을 `책장을`로 바꿨다. | 원문과 다른 instruction으로 거절 |
| H02 | 먼저 어떤 책상이 있는지 알려 달라는 조회를 UNSUPPORTED로 분류했다. | 현재 gold/계약의 CLARIFICATION과 불일치 |
| HD-F01 | target을 `내벽 쪽 높은 장`만 남겼다. | READY 수용, 장소·제외 조건 누락 |
| HD-F02 | target을 `복도 쪽 낮은 장`만 남겼다. | READY 수용, 장소·제외 조건 누락 |
| HD-I02 | 충돌이 없을 때만 이동하라는 미해결 조건을 READY로 판단했고 target을 `행정실 창가 캐비ット`으로 출력했다. | Raw FP; 실제 parser 거절 원인은 원문에 없는 target 철자 |

**HD-I02의 accepted FP0을 조건 판정 성공으로 해석하면 안 된다.** 원문은
`행정실 창가 캐비닛`인데 출력에는 일본어 문자가 섞인 `캐비ット`이 들어갔다.
Instruction은 충돌 조건을 포함한 원문 부분을 보존했고 dy=-0.12m도 맞았다.
Parser는 target의 원문 일치를 먼저 검사해 `UNGROUNDED_REQUIREMENT`로 거절했다.
따라서 이 건은 잘못된 copy가 조건 누락의 실행 가능 출력을 우연히 막은 사례다.
숫자 grounding이 조건의 충족 여부를 검증했다고 주장하거나 raw FP1건을 없애지 않는다.

HD-F01/F02는 instruction 전체와 dx=-0.16m를 보존했지만 target_description에서
`연구실`과 제외 대상이 빠졌다. 두 target은 원문의 연속 부분이어서 lexical guard를
통과했고, 실제 선택 제약의 누락 때문에 unsafe accepted2건으로 유지한다.
단순 조사 차이와 다르지만 실제 GlobalId 선택·IFC 이동이 발생했다는 뜻은 아니다.
별도 대상 확인과 proposal 승인 경계는 그대로 필요하다.

## v3 대비와 다음 판단

[같은 모델 v3](phase5x_moe_v3_diagnostic_review.md)에서 실패한 I02/HD-A02/HD-B01/
HD-D02는 이번에 통과했다. A01/H02/HD-F01/HD-I02는 새로 실패했고,
F02/HD-F02는 계속 실패했다. Semantic은34/40으로 같고 FN은4→2로 줄었지만,
unsafe accepted는1→2로 늘었다. Parser accepted나 FN 개선만으로 안전성이
개선됐다고 결론낼 수 없다. 같은40개·단일 seed 진단이며 독립적인 일반화 증거도 아니다.

최대 completion143tokens이고 transport/truncation 오류는 없다. 같은 제3자 ELVISIO
revision `9f41ff709102dbe73e614f9365f8280170db268e`, AWQ Marlin/FP16,
neutral `qwen3_nonthinking`, non-thinking, guided_json/xgrammar:no-fallback,
context4096/output768에서 기존 v4를 사용했다. Git은
`3a13b240e4d1273db79947cf5d11c8becc9230f0`, **dirty=false**로 기록됐다.

누적 실패를 보존하고 generation2의 인용 중심 출력 계약을 별도로 검토하는 근거는
있지만, 그것이 원문 copy·조건·대상 scope 오류를 해결한다는 증거는 아직 없다.
기존 parser/gold/metric을 완화하지 않고 새 계약·adapter·prompt·평가를 별도로
버전화해야 한다. 이번 결과는 정식 development40×3 또는 holdout80×3 gate를
대신하지 않으며 holdout 출력으로 조정하지 않았다.
