# Phase5.x holdout 실행 전 프로토콜 검토

작성 기준시각: **2026-09-19 21:49:52 UTC / 2026-09-20 06:49:52 KST**. Root가 holdout 미호출 상태임을 알린 뒤 작성했으며, 본 검토자는 holdout 모델 출력이나 진행 중인 v6 development 진단 출력을 읽지 않았다. 이 문서는 결과를 보기 전 해석·보고 원칙이다. Gold/prompt/scorer/threshold는 변경하지 않았다.

## 고정 자료와 gate

[최초 freeze](../../evaluations/hardening_v1_freeze.json)와 [작성 manifest](../../evaluations/hardening_v1_manifest.json)를 확인하고 현재 holdout bytes가 SHA `12c08e85a3b64c459fe7385e1cab35a4a036c6ceb3bc1d27d137ba3515e74d78`와 같음을 재검증했다. Gate는 최초 freeze의 네 조건을 그대로 유지한다.

| Gate | 전체 holdout에서 필요한 결과 |
|---|---|
| Schema100% | **240/240** |
| Semantic≥95% | **228/240 이상** |
| Raw model READY critical FP0 | Gold non-READY114 trials에서 **0건** |
| Unsafe accepted READY0 | 전체240 trials에서 **0건** |

Unsafe accepted READY는 gold non-READY의 accepted READY와 gold READY의 잘못된 accepted target/XY 이동을 합한 수다. 후자는 별도로 READY126 trial 분모에서도 보고한다. Raw FP와 accepted FP를 합치거나 parser가 거절했다는 이유로 raw FP를 지우지 않는다. 네 조건 중 하나라도 실패하면 이 holdout gate는 실패다. 일부 category의 성공이나 높은 전체 평균으로 상쇄하지 않는다.

| 구성 | Case | 3회 평가 trial |
|---|---:|---:|
| READY | 42 | 126 |
| CLARIFICATION | 15 | 45 |
| UNSUPPORTED | 23 | 69 |
| Non-READY 합계 | 38 | 114 |
| 전체 | 80 | 240 |

A–J 각8case/24trial이며 최소쌍40그룹이다. 모든 case를 고정 순서로3회 평가한다. Warm-up5회는 정식240회·latency 통계에서 제외한다. **현재 harness는 해당 dataset 앞5개를 warm-up에 사용하므로 holdout의 첫 노출은 첫 warm-up 요청부터다.** Warm-up 결과를 보고 후보나 설정을 바꾸면 이미 holdout 피드백을 사용한 것이다.

## 첫 요청 전 확정할 것

Development 진단과 필요한 반복 검증을 끝내고 한 후보를 선택한다. 최초 freeze의 v3 prompt 기록은 데이터 작성 당시 기준이며, 이후 후보의 실제 설정 freeze를 대신하지 않는다. 최종 후보에 대해 다음을 별도 기록한 뒤 **첫 holdout warm-up 전** checkpoint를 남긴다.

- Dataset/gold, model·tokenizer revision/weight manifest, prompt, schema, parser, scorer, client, runtime·launch 설정의 정확한 hash/version.
- Thinking true/false와 reasoning parser, structured-output dialect/backend, 전체 출력 cap, timeout, 모든 sampling/penalty 값과 seed42, concurrency1, context4096.
- 80×3 protocol, warm-up5, GPU3 자원·시간 예산, 위 gate, 선택 근거가 development 결과라는 점.

실행 중 timeout·truncation·schema/parser 실패를 분모에서 제거하지 않는다. Raw decision을 관측하지 못한 경우는 미관측으로 보고하며, 그 경우 raw FP0은 관측된 하한일 수 있다. Run이 중단되면 계획240/완료N/미완료 수와 중단 이유를 보고하고 **INCOMPLETE, gate 미통과**로 둔다. 미시도 응답을 만들어 채우거나 부분 결과만으로 전체 통과를 선언하지 않는다. 기술적 재실행도 이전 run을 보존하고 동일 조건·사유·전체 범위를 기록하며 성공 응답만 골라 합치지 않는다.

## 통과·실패의 해석

통과하면 **이 고정 synthetic holdout, 이 A100 checkpoint/runtime/prompt/profile 조합이 네 gate를 충족했다**고 보고한다. 그 조합을 내부 개발 후보로 채택하는 근거가 되지만 사람 검수, 실제 IFC 적용, 외부 pilot 안전성, RTX 실행 성공을 뜻하지 않는다. Requirement 추출과 inventory 대상 확인·proposal approval·IFC 불변성 검증은 계속 별도다.

실패하면 실제 count/denominator, 실패 category/case, raw decision·parser 결과·semantic 차이, timeout/latency/token 정보를 그대로 남긴다. 기준을 낮추거나 gold를 결과에 맞춰 고치지 않는다. 실패 원인에 관한 추정과 재현된 사실을 구분한다. Raw reasoning은 수집·노출하지 않고 최종 structured output과 허용된 숫자 metadata만 검토한다.

최종 보고에는 네 gate뿐 아니라 schema/parser/semantic 비율, raw decision 관측률, accepted FP, 잘못된 accepted 이동, FN, ambiguity/unsupported 지표, category별 결과, case별3회 일관성, 전체 latency와 오류 유형을 포함한다. 기존 gate에 없던 metric을 사후 통과 기준으로 만들거나 불리한 metric을 숨기지 않는다.

Holdout 출력을 본 뒤 prompt·sampling·schema·parser·scorer·gold를 조정하면 같은80개는 이후 **regression/development 자료**다. 새 version과 변경 이유를 기록하더라도 같은 자료의 재평가를 새로운 unseen holdout 성공으로 부르지 않는다. 새로운 일반화 주장은 별도로 사전 작성·검토·동결한 미사용 자료가 필요하다. 새로운 gold 오류가 확인되면 이전 score를 보존하고 수정 version으로 분리하며, 유리한 case만 제외하지 않는다.

## 독립성·blinding 한계

Gold 상태는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. 작성자와 독립 AI 검토자는 추론 전에 holdout 입력·gold를 읽었다. Prompt 작성에 참여한 AI도 사전 gold 검토에 참여한 이력이 있으므로 사람 검수 또는 엄격한 blind evaluation이라고 주장하지 않는다. Human-review 양식의 빈 칸은 검수 완료를 뜻하지 않는다.

Split은 scenario 최소쌍을 함께 묶었지만 development/holdout에 좁은 XY grammar·분류 원칙·명사/수치 변형·generator scaffold가 공유된다. 따라서 완전히 독립된 의미 family나 실사용 BIM 분포에 대한 검증이 아니다. Plaintext 파일과 generator에 gold가 있으므로 봉인은 접근 제어가 아닌 **결과를 보기 전 고정하고 이후 튜닝하지 않는 절차**다.

각 case를 같은 seed42로3회 실행하므로240회는 독립된240문제가 아니다. 확률 sampling에서도 같은 seed 반복은 같은 응답을 반복할 수 있다. 80case와40pairgroup 사이에도 상관이 있다. Harness의 trial Wilson interval은 독립 Bernoulli 가정을 만족한다는 보장이 없는 참고 수치이며, 실제 안전 위험의 엄밀한 상한으로 제시하지 않는다. Case별 일관성·오류 수와 분류별 결과를 함께 보여주고, 관측 오류0을 실제 위험0으로 해석하지 않는다.

이 검토는 새 평가의 통과 선언이나 holdout 호출 자체가 아니다. 검토 문서 외 파일 변경, GPU 접근, 모델 호출은 수행하지 않았다.
