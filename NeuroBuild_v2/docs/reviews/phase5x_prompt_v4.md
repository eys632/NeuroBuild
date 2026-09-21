# Phase5.x development 실패 분석과 prompt v4

작성일: 2026-09-20 KST. [v3 development 결과](../../evaluations/results/phase5x/development-v3/results.json)는
40 case × 3회에서 schema120/120, parser111/120, semantic108/120이었다. Gold non-READY의
raw model READY는3/60, accepted READY는0/60이며, gold READY의 잘못된 accepted 이동은0/60,
FN은9/60이다. 같은 case의 3회 반복을 독립 오류 유형으로 세지 않았다.

| 실패 case | 실제 문제 | V4 대응 |
|---|---|---|
| HD-B01, 3회 | unsigned X 거리에서 양의 방향을 추측해 READY. Parser는 거절 | 축·거리와 양음 방향을 분리하고 양수 숫자가 방향의 근거가 아님을 명시. 새 unsigned Y 예시는 CLARIFICATION |
| HD-D02, 3회 | 가구 하나의 X/Y 두 성분을 여러 가구로 오분류해 UNSUPPORTED | 변경할 대상 수와 이동 성분 수를 구분. 단일 가구 두 축과 두 가구 이동을 각각 예시로 제시 |
| HD-F01/F02, 각3회 | 대상·제외 span은 맞지만 원문16cm를 -0.16m로 환산해 parser 거절 | 물리 변환 오류가 아니라 원문 추출 계약 위반이다. Negative cm와 소수점·뒤의0을 그대로 복사하는 새 예시로 보강 |

Gold나 parser 오류로 확인된 실패는 없었다. 기존 실패 run과 v3를 보존하고 새
[requirement_v4.txt](../../prompts/requirement_v4.txt)만 만들었다. Schema/parser/scorer,
dataset의 정답·split, client 기본 prompt는 변경하지 않았다. V4의 실제 모델 성공은
아직 이 작성 기록으로 주장하지 않는다.

Root의 독립 규칙·예시 검토는 PASS다. 추가 model_research 검토는 작성 시점에
진행 중이며, 이 문서에서 완료된 것으로 표시하지 않는다.

## 프롬프트 전략

규칙과 예시를 재구성했다. 포괄적인 “여러 변경” 거절보다 실제 대상 수와 동작 종류를
먼저 구분하도록 설명하고, 한 가구의 X/Y는 한 이동의 두 성분이라고 명시했다. 숫자·단위는
원문 추출이며 metre 변환은 코드의 책임이라는 규칙을 모아 표현했다. 원문 ASCII 부호는
보존하고, 부호 없는 크기에 음의 방향이 명시된 경우에만 `-`를 한 번 붙인다.

새 합성 예시4개는 음의 cm와 제외 대상, 과거 지시 폐기와 단일 가구 두 축·혼합 단위,
방향 없는 Y 이동, 서로 다른 두 가구의 이동이다. Development의 문장·대상·수치 정답을
복제하지 않았다. V3의 설계 거절과 “축·거리도 명확하지만 외부 조건은 미확인”인 예시2개는
유지해 과거 조건 오판을 잊지 않도록 했다. 중복 예시를 교체해 총7개로 구성했다.

변경 근거는 development 결과와 기존 공통 계약이다. 작성자는 이전 단계에서 추론 전
heldout gold 검토에 참여했지만, 그 내용을 이번 prompt 변경의 근거나 예시로 사용하지
않았다. Heldout 모델 호출·출력 열람은 없었다. CPU token 길이 검사는 입력만 사용했고
gold를 tokenization하거나 응답을 생성하지 않았다. 이 변경은 development tuning이며
unseen 또는 human-verified 개선 증거가 아니다.

## CPU 검증

**AUTO-GENERATED / NOT HUMAN VERIFIED** 예시7개를 현재 JSON Schema와 parser에
통과시켰다. READY2, CLARIFICATION3, UNSUPPORTED2가 모두 일치했다. READY의 코드 변환
결과는 첫 예시 `dx=-0.2340m, dy=0m`, 두 번째 `dx=0.035m, dy=-0.062m`다. 모델 출력에는
각각 원문 `-23.40cm`, `35mm`/`-6.2cm`를 유지한다. 이는 예시의 표현 가능성 확인이며
실제 모델 정확도 검증이 아니다.

로컬 Qwen3-14B-AWQ tokenizer revision
`31c69efc29464b6bb0aee1398b5a7b50a99340c3`를 CPU/offline으로 사용했다.
`CUDA_VISIBLE_DEVICES=''`, `USE_TORCH=0`, `USE_TF=0`, `USE_FLAX=0`을 적용했고
`torch`가 import되지 않았음을 확인했다. Client와 동일한 system/user JSON 및
`add_generation_prompt=True`, `enable_thinking=False`를 사용했다.

| 입력 | 입력 token 범위 | 출력 예산 포함 최대 |
|---|---:|---:|
| Development40 | 2390–2765 | 3533 / 4096 |
| Holdout80, 길이만 측정 | 2396–2770 | 3538 / 4096 |

System prompt는2350 tokens이며 v3보다9 tokens 짧다. 출력 예산은768 그대로다.
최종 prompt SHA-256:
`2fdd6a5a92860cde27d14adc10916a242b2221e1569015541ddf31581d1a14d8`.
Token 한도 통과는 응답 완결성이나 의미 정확도를 보장하지 않는다.

## 반복 실패에 대한 접근 재검토

원문 숫자 형식·단위 복사 실패가 반복되어, 규칙을 계속 덧붙이는 방식의 한계를 검토했다.
현재 출력은 evidence와 value/unit에 같은 정보를 중복 표현한다. 모델이 정상적인 물리
환산을 수행해도 원문 복사 계약에는 실패할 수 있다. 이번에는 동결한 계약 안에서
규칙·예시를 재구성한 v4를 development에서 먼저 평가해 비교 가능한 근거를 확보한다.

같은 실패가 계속되면 prompt만 추가하는 대신 **evidence span 중심의 versioned 계약**을
검토해야 한다. 모델은 decision/대상/현재 지시/각 축의 원문 evidence를 선택하고 코드는
원문 경계가 확인된 evidence에서 제한된 문법으로 수치·단위·부호를 추출하는 방식이다.
중복 value/unit 필드를 없애는 장점이 있지만, evidence의 선택 오류·방향 누락·조건 의미는
여전히 해결하지 못하며 불명확하면 계속 거절해야 한다.

그 전환에는 별도 schema version, parser/client/scorer와 회귀 검증, source grounding 및
승인 경계 유지, 새 hash 동결과 전후 결과 구분이 필요하다. 이번 작업에서 해당 재설계를
구현하거나 현재 parser를 완화하지 않았다. V4는 development 결과를 먼저 확인하고,
충족되지 않은 gate를 heldout 호출이나 다음 Phase 구현으로 우회하지 않는다.

추가 model_research 독립검토도 v4freeze 직후,실제v4모델호출전에PASS했다. 동일SHA및7exemplars를직접schema/parser재검증했고규칙/예시모순이나변경필요gold를발견하지않았다. 이는모델품질평가통과가아니며development재평가를따른다. Freeze파일의pending표시는그파일작성시점기록으로보존한다.
