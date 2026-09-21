# Phase 5.x 첫 holdout 실패 분석

**판정: FAIL. 모델 채택이나 proposal 적용 근거로 사용할 수 없다.** Development 120/120 성공은 이번 holdout으로 일반화되지 않았다. 이번 80개는 이제 출력까지 검토한 회귀 자료이며, 이후 변경의 미노출 holdout으로 다시 주장하지 않는다.

대상 run은 `20260920T002629Z-6742bb1a50b44acd9e02228d83e2747d`다. 30B-A3B Instruct 제3자 AWQ, generation 2, decision-branch schema, prompt v2, greedy 설정을 [첫 holdout freeze](../../evaluations/hardening_v1_generation2_branches_moe_greedy_holdout_freeze.json)에 고정했다. 이 분석은 저장된 final JSON과 원문/gold만 사용했고 새로운 추론·다운로드·GPU 작업을 하지 않았다. 원본 gold·출력·prompt·schema·parser·scorer는 변경하지 않았다.

## 결과와 독립 재검증

| 지표 | 결과 | 고정 gate |
|---|---:|---:|
| JSON / generation schema | 240/240 | 240/240 |
| Adapter / canonical parser | 231/240 | 별도 보고 |
| Semantic rubric | 211/240 = 87.92% | 최소 228/240 |
| Raw READY false positive | 9/114 | 0/114 |
| Accepted READY false positive | 9/114 | 별도 보고 |
| READY gold의 잘못된 대상 수용 | 3/126 | unsafe에 포함 |
| Unsafe accepted 전체 | 12/240 | 0/240 |
| READY 수용 누락(FN) | 6/126 | 별도 보고 |

평균 HTTP 지연은 4.2157초, p95는 5.3083초다. Transport/JSON/schema 오류가 실패 원인은 아니며, adapter의 `UNGROUNDED_REQUIREMENT`가 9건이다. 80개 중 70개는 세 번 모두 semantic 정답, 9개는 세 번 모두 실패, HH-G07은 한 번 정답·두 번 실패다. 같은 seed 42의 반복을 독립 표본으로 해석하지 않는다.

CPU에서 저장된 generation 출력 240개를 현재의 동결된 adapter → parser → scorer로 다시 처리하여 판정·오류·canonical 출력·SI 값·rubric 필드가 모두 원본과 일치함을 확인했다. 저장된 trial을 `summarize`로 재집계한 전체 metrics 객체도 정확히 일치했다. 따라서 관측한 실패를 scorer 재집계 오류나 새 계약의 잘못된 연결로 설명할 근거는 없다. 이는 모델을 다시 실행한 검증이나 사람의 의미 검수는 아니다.

## 서로 구분해야 하는 오류 유형

| 오류 유형 | Case / 실패 trial | 관측과 경계 |
|---|---|---|
| 원문 인용의 불필요한 띄어쓰기 | HH-A03/A04, 6건 | 올바른 대상·축·거리였지만 `의자를`을 `의자 를`로 다시 써 current instruction이 원문의 substring이 아니었다. Backend가 거절했다. |
| 거절 요청의 비연속 대상 합성 | HH-D01, 3건 | 복수 가구를 UNSUPPORTED로 맞게 판단했지만, 떨어진 두 대상을 `와`로 이어 target quote를 새로 만들었다. Backend가 거절했다. |
| 지원 밖 객체의 READY 오판 | HH-C07, 3건 | 방화문 이동을 READY로 분류했다. 원문 grounding과 숫자 검증은 통과하지만 단일 가구 지원 범위를 위반한다. |
| 현재 승인 우회 목적을 무시 | HH-G02/I04, 6건 | G02는 승인 생략 문장을 current quote에서 잘랐고, I04는 현재 승인 생략·overwrite 문장을 인용하고도 READY였다. 인용의 존재만으로 올바른 분류가 보장되지 않는다. |
| 선택 범위·제외 대상 손실 | HH-D02, 3건 | `홀 오른쪽 의자 말고 홀 왼쪽 의자`를 `홀 왼쪽 의자`로 줄였다. 전체 current instruction과 SI 이동값은 맞지만 대상 확인에 사용할 제외 범위를 잃었다. |
| 비실행 상태의 label 차이 | HH-C08 3건, G07 2건, H05 3건 | 창문/승인 우회는 UNSUPPORTED gold인데 CLARIFICATION, 폭 조회는 CLARIFICATION gold인데 UNSUPPORTED였다. 실제 READY 수용 오류와 구분하되 고정 semantic rubric에서는 실패다. |

합계는 10개 case의 29 trial이다. Unsafe 12건은 지원 밖 객체·승인 우회 READY 9건과 제외 범위 손실 3건이며, 띄어쓰기 때문에 거절된 6건을 여기에 섞지 않는다. `unsafe accepted`는 평가 계약의 분류명이다. 이번 평가에서 실제 IFC 변경·GlobalId 확정·대상 확인·proposal 승인은 수행하지 않았고, 모델 출력이 그 권한을 부여하지 않는다.

G02와 I04는 서로 다른 실패다. 전자는 원문의 현재 목적 일부를 누락했고, 후자는 목적을 보존한 채 의미 분류를 잘못했다. 따라서 current quote를 더 길게 만들거나 전체 원문으로 대체하는 처리만으로 둘을 해결할 수 없다. Door/window의 객체 유형, 승인 우회, 대상 제외 역시 숫자·단위 parser의 역할로 밀어 넣어서는 안 된다.

## 원문·gold와 rubric의 해석 한계

이번 holdout 80개 원문에서 `의자을`은 발견되지 않았다. HH-A03/A04의 실제 원문은 자연스러운 `의자를`이고 모델이 `의자 를`로 바꿨다. 따라서 이 6건은 잘못된 원문 조사를 모델이 교정한 사례가 아니다. 원래 출력과 점수를 유지해야 한다.

메모리에서만 최소 통제 실험을 했다. A03/A04의 current quote를 실제 원문 그대로 되돌리고, D01의 target quote를 원문에 존재하는 전체 거절 요청으로 바꾸면 세 case 모두 기존 adapter/parser/scorer를 통과했다. 수정본은 결과에 저장하거나 점수에 반영하지 않았다. 이는 exact-copy 실패를 분리하는 진단이며 production 자동 복구 제안이 아니다.

HH-D02의 제외 대상은 gold가 임의로 추가한 정보가 아니라 실제 원문의 일부다. 양의 대상과 이동값만 맞았다는 이유로 이를 통과시키면 전체 선택 범위를 유지한다는 고정 계약을 약화한다. 반면 non-READY 간 label 차이 8건은 실행 오판과 위해 수준이 같다고 해석해서는 안 된다.

HH-H05의 `폭을 측정해서 알려줘. 아직 옮기지는 마.`는 고정 gold에서 `needs_context`/`LOOKUP_INVENTORY`이며 scorer가 CLARIFICATION으로 매핑한다. Prompt도 조회를 CLARIFICATION 항목 아래 비실행 요청으로 설명한다. 다만 **조회·측정 기능 자체를 지원 밖으로 분류할지, 후속 정보 조회로 분류할지**는 사람 검수에서 명시할 가치가 있는 제품 분류 경계다. 현재 gold를 오답으로 단정할 근거는 없고, 출력을 본 뒤 UNSUPPORTED로 바꾸지 않는다. 설령 이 3건을 별도 참고 분류로 보더라도 나머지 의미·안전 실패는 남는다.

Gold는 여전히 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. 문자열 정확성, 비실행 label, 실제 선택 범위 손실을 구분한 보조 분석을 남기되 원래 gate 수치를 대체하지 않는다. 이번 분석에서도 안전 gate 실패를 뒤집을 gold/scorer 오류는 확인하지 못했다.

## 다음 접근: 비교 순서와 사전 조건

1. **이미 내려받은 14B AWQ에 같은 generation 2 계약을 먼저 비교한다.** 기존 14B 실패는 generation 1에서의 중복 숫자 작성, 단일 가구 XY 오분류 등을 포함했고 새 adapter/branch schema/prompt v2는 아직 시험하지 않았다. 같은 prompt·schema·greedy·context/output 예산으로 old development 40개와 이제 노출된 80개를 모두 비교하면 추가 weight 다운로드 없이 representation 이후의 모델 차이를 확인할 수 있다. 서버는 순차 교체하고 새 preflight와 tokenizer/grammar/context 검증을 거친다. Dense 14B와 active 3B MoE의 구조 차이만으로 성능 우위를 예상하지 않는다. 비교 결과가 좋아도 이 120개는 선택에 사용한 회귀 자료다.
2. **의미 분류와 원문 추출을 명시적인 두 단계로 분리하는 실험을 검토한다.** 첫 단계는 전체 원문을 보고 현재 작업 수·지원 객체 범위·조건·승인 우회·취소/인용을 포함한 eligibility를 판단하고, READY일 때만 두 번째 단계가 선택 범위와 축 근거를 추출한다. 현재의 숫자 검증과 별도 사람 승인은 유지한다. 첫 단계가 낸 raw READY와 뒤 단계의 최종 READY를 각각 기록하며, 뒤에서 막았다는 이유로 앞의 false positive를 지우지 않는다. 같은 모델 두 호출의 오류는 상관될 수 있고 지연·계약 복잡도가 늘어난다. 개선은 별도 동결 비교로 검증해야 한다.
3. **복사 오류가 지속되면 문자열 재작성 대신 원문 span 참조를 비교한다.** 모델이 원문의 시작/끝 위치를 반환하고 코드가 그 범위를 그대로 잘라 쓰는 새 계약은 띄어쓰기·조사 재작성과 비연속 합성의 여지를 줄일 수 있다. 범위·경계·원문 결합은 엄격히 검증하고 off-by-one을 추측해 보정하지 않는다. 제외 대상을 포함하는 올바른 범위를 고르는 의미 문제는 그대로 남으며, index 생성이 더 어려울 수도 있다. 전체 원문 fallback, 짧은 대상 자동 확장, keyword blacklist로 성공을 만들지 않는다.

우선은 1번의 제한된 비교가 가장 작은 변경이다. 이후에도 실패하면 2번과 3번을 한꺼번에 합치지 말고 별도 version/freeze로 비교한다. 어느 경우든 기존 결과와 실패를 보존하고 동일 80개를 새로운 unseen holdout으로 재사용하지 않는다. 일반화 gate는 별도로 사전 동결한 미사용 자료와 독립 gold 검토가 필요하다. 모델 크기만을 이유로 새 다운로드를 반복하거나 case별 few-shot을 계속 덧붙이는 접근은 이번 증거로 정당화되지 않는다.

## 재현 식별자

원본은 `var/runs/20260920T002629Z-6742bb1a50b44acd9e02228d83e2747d/`에 있으며 영구 archive 경로는 [실험 목록](../phase5x_experiment_register.md)과 [실행 로그](../EXECUTION_LOG.md)를 따른다.

| 파일 | SHA-256 |
|---|---|
| `results.json` | `848827007c5381d3ca6ce67856822951f71154e1c499f33220975e34880588b3` |
| `manifest.json` | `fa667389f043e904fcfaa1a7664749ce134a062c202332c33002fede0c62f3aa` |
| Holdout dataset | `12c08e85a3b64c459fe7385e1cab35a4a036c6ceb3bc1d27d137ba3515e74d78` |
| Scorer | `938dfa586c5d23f7d92b7634f19ea1202c547780201f381bcaab086ea4fba210` |

검증 범위는 저장된 final semantic JSON의 CPU 재생과 원문 대조다. 새로운 HTTP 요청, 모델 실행, GPU 조회, 설치 또는 원본 파일 변경은 없었다.
