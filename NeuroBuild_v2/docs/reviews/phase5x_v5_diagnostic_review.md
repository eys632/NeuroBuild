# Phase5.x v5 diagnostic 독립 검토

2026-09-20 KST. 검토 대상은 run `20260919T212748Z-bba084e02f46432aab7f11883d625467`의 development40 × 1회 결과다. Warm-up 5회는 지표에서 제외한다. [Manifest](../../evaluations/results/phase5x/development-v5-diagnostic/manifest.json), [결과](../../evaluations/results/phase5x/development-v5-diagnostic/results.json), [자원 기록](../../evaluations/results/phase5x/development-v5-diagnostic/resource_report.json)을 보존했다. **AUTO-GENERATED / NOT HUMAN VERIFIED** gold이며 holdout 결과가 아니다.

결론: 저장 결과와 고정 parser/scorer의 재검증이 일치한다. Gold·scorer 오류나 다른 dataset/prompt가 평가됐다는 근거는 찾지 못했다. V5는 READY 분류 후 원문 수치·단위·null 표현을 지키지 못했고, 별도의 의미 오판도 있었다. 현재 기준을 낮춰 성공으로 처리할 근거가 없다.

## 재현·artifact 확인

- Run의 dataset snapshot40은 동결된 development40과 동일하다. Dataset, v5 prompt, schema, parser hash가 manifest와 모두 일치한다.
- Run commit `f154a7f2b1bc3b4728d9214778b2f85168e38c54`의 scorer를 읽어 SHA `eafab91bd72839469ba515216550463ab2e50c130d2a8d05ebc88d902ad965cb`를 확인했다. 당시 scorer로 실제 출력40개를 재검증했고 저장된 모든 판정·집계와 일치했다.
- 병렬 sampling-profile 구현 중 발생한 일시 import 불일치는 감사 시점의 working tree 상태였다. 완료된 run의 원인으로 취급하지 않았다. Historical scorer의 client import만 메모리에서 제외하고 실제 scoring 함수를 그대로 사용했다. 이후 새 working tree의 scoring/metric 함수6개도 AST 단위로 동일함을 확인했다.
- 참조 응답40개는 같은 schema/parser/scorer에서 **40/40 PASS**였다. Rejected 모델 출력을 허용하기 위한 gold 또는 parser 수정은 하지 않았다.
- 보존한 manifest/results는 원래 `var/runs/` 파일과 byte 단위 동일하다. Recorded checkpoint는 Qwen3-14B-AWQ `31c69efc29464b6bb0aee1398b5a7b50a99340c3`, runtime은 vLLM0.8.5+cu118/AWQ-Marlin/FP16이다. T0, seed42, non-thinking, xgrammar:no-fallback, output768, context4096, concurrency1이었다.
- HTTP/timeout/truncation/schema 오류는 기록되지 않았고 오류24개는 전부 `UNGROUNDED_REQUIREMENT`다. 자원 snapshot은 RUNNING/중단 사유 없음이다. 이는 해당 server epoch의 누적 aggregate 기록이며 v5만의 peak나 실제 loaded weight를 독립 증명하지 않는다. 설정 기록만으로 quantization·kernel·grammar의 품질 영향을 배제할 수도 없다.

## 지표 재계산

| 지표 | 결과 |
|---|---:|
| JSON/schema | 40/40 |
| Parser accepted | 16/40 |
| Semantic rubric | 13/40, 32.5% |
| Gold non-READY의 raw model READY | 5/20 |
| Gold non-READY의 accepted READY | 0/20 |
| Gold READY의 잘못된 accepted 이동 | 0/20 |
| Gold READY의 accepted READY 누락 | 19/20 |
| 전체 unsafe accepted READY | 0/40 |
| End-to-end mean / p95 | 4.18646초 / 5.94240초 |

Gold READY20개를 모델은 **전부 raw READY로 분류**했다. 그중 H01만 parser와 의미 검증을 통과했다. 나머지19개와 gold non-READY를 READY로 오판한5개를 합쳐 parser 거절24개다. 나머지 semantic 실패3개는 parser가 수용한 비실행 응답의 분류 오류다. 따라서 19/20 FN을 모두 모델의 불필요한 CLARIFICATION으로 설명하면 틀리다.

## 출력 오류 분류

아래 수치는 gold READY20개 중의 **겹치는 분류**이며 합산하지 않는다.

| 유형 | Case 수 | 관측 예 |
|---|---:|---|
| 같은 단위에서 원문 숫자 철자 변경 | 13 | `1`→`1.00`, `125`→`125.00`, `-16`→`-16.00` |
| 모델이 단위를 환산 | 5 | 원문250mm를 -0.25m, 30cm를0.30m로 출력 |
| 요청하지 않은 축을 객체로 생성 | 12 | 실제 JSON null 대신 축 객체 생성 |
| 위12개 중 문자열 null 사용 | 5 | `{value:"null", unit:"m", evidence:"null"}` |
| 위12개 중 0축 생성 | 7 | Y evidence를 dx에도 붙이고0.00으로 출력 |
| Target span 불일치 | 5 | 위치·제외 scope 삭제 또는 이동 문장까지 target에 포함 |

수치 표기 변경과 단위 환산은 물리량 자체가 등가인 경우도 있으나 현재 **원문 추출 계약**을 위반한다. JSON Schema의 string 타입은 `"null"`이나 원문에 없는 소수점 표기까지 자동으로 거절하지 않으므로 schema100%와 backend acceptance는 다른 지표다. 요청하지 않은 축에 Y evidence를 복사한 dx는 축·근거 대응도 위반한다.

In-memory 진단으로 거절된 gold READY19개의 **값·단위만 참조의 원문 표기로 바꾸고 미요청 축을 null로** 바꿨다. Target/instruction/요청 축 evidence는 그대로 뒀다. Parser19/19가 통과했고 semantic14/19가 통과했다. 남은5개는 F01, F02, I02, HD-F01, HD-F02의 target 문제였다. 이 진단은 parser가 유효한 동일 요청을 표현할 수 있음을 확인한 것이며, 모델 응답을 실제로 보정하거나 원래 점수를 높인 것이 아니다.

Gold non-READY의 raw FP는 **B02, D01, E02, HD-B01, HD-I02**다. 누락 거리 발명, 서로 다른 두 대상 이동의 병합, 미확인 조건 무시, 누락 방향 추정을 포함한다. 별도의 비실행 분류 오류 **D02, HD-D01, J01**에서는 회전 포함 이동이나 설계안 요청을 UNSUPPORTED 대신 CLARIFICATION으로 처리했다.

## Accepted FP 0의 해석

Parser 거절이 의미적 위험까지 판정했다는 뜻은 아니다. Synthetic in-memory counterfactual에서 E02의 값 표기/null, HD-I02의 미요청축 null, D01의 숫자 표기만 바로잡으면 parser는 READY를 수용한다. 하지만 미확인 개수·충돌 조건과 두 대상 병합이라는 **원래 의미 오류는 그대로**이므로 scorer는 실패한다. 이 세 입력에 대한 모델/IFC 호출이나 apply는 수행하지 않았고 수정 응답도 저장하지 않았다.

따라서 이 run의 accepted FP0은 우연히 함께 발생한 표현 오류가 위험한 raw READY를 막은 경우를 포함한다. Backend grounding은 전체 자연어 조건·대상 수를 판정하는 안전 증명이 아니다. Raw FP와 semantic 오류를 계속 gate에 반영하고, grounding·실제 inventory 확인·대상 확인·proposal 승인을 유지해야 한다.

## 다음 비교 판단

V5가 짧거나 영어라는 이유만으로 개선될 것이라는 가정은 실측에서 성립하지 않았다. 한 번의 변경은 길이·언어·few-shot 유무·문구를 함께 바꾸었으므로 어느 요소가 원인인지 분리되지 않는다. T0가 그 원인이라는 결론도 아직 없다.

더 나았던 v3 prompt를 그대로 두고 [공식 AWQ non-thinking sampling profile](../qwen3_decoding_review.md)을 별도 version/run으로 비교하는 것은 다음 제한된 진단으로 타당하다. 같은 development40 전체를 사용하고 실패 run을 보존한다. 1회 진단은 정식 반복 평가나 heldout gate를 대체하지 않으며, 결과를 본 뒤 gold/schema/parser를 완화하지 않는다. 이 감사에서는 요청받은 검토 문서 외의 파일 변경, 모델 호출, GPU 접근을 하지 않았다.
