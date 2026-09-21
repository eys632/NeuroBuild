# Phase5.x MoE-Instruct v3 진단 독립 검토

2026-09-20 KST. **FAIL — semantic34/40(85%), raw FP1건, unsafe accepted1건.**
Development40×1 진단이며 gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다.
검토자는 저장된 최종 semantic JSON만 CPU에서 재생했다. 추가 model/GPU/HTTP 호출,
CoT 열람, source·parser·scorer·schema·gold 변경은 수행하지 않았다.

Run `20260919T231243Z-194bbb3212944ebcb8e0e54bfa1b28b5`의
[결과](../../evaluations/results/phase5x/development-moe-v3-diagnostic/results.json)와
[manifest](../../evaluations/results/phase5x/development-moe-v3-diagnostic/manifest.json)는
로컬 원본과 byte 단위로 일치한다. SHA-256은 각각
`3f0cbd72790043875fad5aa562865b751fbabd4e84321998a92c8b8decc82e99`,
`316bad3fc3d43e9bd8c8ec853675c94d049b6003f44da882615e733a2d2db471`이다.

## 재검산

40개 모두 schema, parser의 수용/거절·오류 코드, SI 변환값, 모든 scorer 필드를
재검산했고 `summarize` 전체가 원본과 일치했다. Manifest의 dataset/prompt/schema/
weight manifest/runtime metadata/parser/client/scorer SHA8개도 현재 파일과 일치했다.
Latency는 추가 측정 없이 원래 값만 재집계했다. Warmup5개는 아래 분모에서 제외한다.

| 지표 | 결과 |
|---|---:|
| JSON / schema | 각각40/40 |
| Parser accepted | 36/40 |
| Semantic rubric | **34/40, 85%** |
| Non-READY gold의 raw READY / accepted READY | **1/20 / 0/20** |
| READY gold의 accepted READY 누락 | **4/20** |
| READY gold에서 accepted이지만 rubric 불일치 | **1/20** |
| Unsafe accepted total | **1/40** |
| SI 축/거리 일치 | 32/40 축 slots |
| Latency mean / p95 | 4.240959 / 6.079516초 |

## 여섯 실패의 구분

| Case | 실제 출력의 문제 | 결과 |
|---|---|---|
| F02 | instruction의 `책상을`을 `책사를`로 바꿨다. target도 `창가 쪽 책상`만 남겼다. | 원문에 없는 instruction으로 `UNGROUNDED_REQUIREMENT`; target의 장소·제외 누락도 별도로 존재 |
| I02 | instruction에 최신 명령뿐 아니라 과거 X축 지시까지 포함한 원문 전체를 복사했다. | instruction 축 집합과 출력 축 집합 불일치로 거절 |
| HD-A02 | `Y축 음의 방향으로 125mm` evidence를 보존했지만 value는 `125`였다. | 필요한 음수 부호 누락으로 거절 |
| HD-B01 | 방향이 없는 `X축으로 1m`를 READY/value=`1`로 판단했다. | 방향 근거 부족으로 거절; 모델 raw FP는 그대로1건 |
| HD-D02 | 한 탁자의 X/Y 이동을 여러 가구 변경이라고 설명하며 UNSUPPORTED로 분류했다. | Parser는 유효한 non-READY 형식을 수용하지만 의미 판정 실패 |
| HD-F02 | target을 `복도 쪽 낮은 장`으로 줄여 장소·제외 대상을 누락했다. | READY로 수용되어 unsafe accepted1건 |

**I02는 원문 변조나 잘못된 40cm 추출이 아니다.** 출력 instruction_text는 입력 전체와
정확히 같고 target=`회의실 책상`, dy=`40`/`cm`, dx=null도 최신 요청의 의도와 맞는다.
그러나 선택된 instruction 안에는 폐기된 과거 `X축 양의 방향으로 2m`와 현재
`Y축 양의 방향으로 40cm`가 모두 있다. 공통 parser는 모델이 선택한 **현재 instruction**에
있는 축을 누락하지 않도록 검사하므로 `{x,y}`와 `{y}`의 불일치를 거절했다.
이는 현재 계약에서 instruction 범위를 지나치게 넓게 선택한 오류다. 배경 지시를
parser가 자연어로 재분류하도록 바꾸거나, 이 건을 성공으로 재채점하지 않았다.

**HD-F02는 instruction 전체는 보존하고 target만 축약했다.** 원문 target span은
`연구실 내벽 쪽 높은 장 말고 복도 쪽 낮은 장`이다. 출력의 긍정 대상과 dx=-0.16m는
맞지만 장소·제외 제약이 target_description에 남지 않아 strict rubric을 통과하지 못했다.
이는 조사 한 글자의 표면 차이와 다르며, 실제 선택 제약의 누락이다. 다만 실제
GlobalId 선택이나 IFC 이동을 수행한 것은 아니다. Lexical 출처 검사는 span 밖의
의미를 전부 보존했다는 증명이 아니고, 별도 target 확인과 proposal 승인은 유지된다.

## 해석의 범위

최대 completion261tokens로 output cap768에 미달했고 transport/truncation 오류는 없다.
문법100%와 성공한 AWQ Marlin startup이 의미 정확도를 보장하지 않는 사례다.
구성은 제3자 ELVISIO 고정 revision `9f41ff709102dbe73e614f9365f8280170db268e`,
FP16/AWQ Marlin, vLLM0.8.5+cu118, 기존 v3, neutral `qwen3_nonthinking`,
thinking=false/parser=null, guided_json/xgrammar:no-fallback, context4096/output768이다.
Git은 `28cfcab9655ca37547886aa986efc80d473b6328`, **dirty=true**로 기록됐다.
실행 파일 hash 일치와 worktree 청결 여부는 구분한다.

이40회는 정식 development40×3 또는 holdout80×3 gate를 대신하지 않는다.
같은 seed 반복과 합성 gold의 한계도 유지한다. 다른 크기·architecture·정밀도의
모델과 차이를 단일 요인의 효과로 해석하지 않는다. 다음 비교는 **기존 v4**를 같은
모델·runtime·sampling으로 적용하는 별도 development 진단이며, 개선을 가정하거나
gold/strict metric을 완화하지 않는다. Holdout 결과를 사용한 튜닝은 수행하지 않았다.
