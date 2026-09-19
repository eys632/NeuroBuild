# Phase5.x 평가 계획·골드·수치 경계 검토

검토일: 2026-09-20 KST. Phase5의 원격 checkpoint는
`d6e39c89658c552c59a8049d7198da051290bd3b`다. 이 기록은 **추론 전 데이터와
평가 방법의 검토**이며 Phase5.x 모델 품질 통과 또는 Internal MVP 완료 판정이 아니다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다.

## 데이터와 정답 기준

독립 검토자가 [development40](../../evaluations/requirement_hardening_v1_development.jsonl),
[holdout80](../../evaluations/requirement_hardening_v1_holdout.jsonl)의 원문과 gold를 읽었다.
특히 heldout READY42개의 대상 수식어·제외 구문·축·부호·단위와 non-READY의
조건·취소·미지원 사유를 확인했다. 현재 계약에서 수정해야 할 모호한 정답은 찾지 못했다.
이후 I 분류 10개의 배경을 553–599자로 늘린 변경도 읽었으며, 추가된 설명이
현재 이동이나 조건을 새로 만들지 않는 것을 확인했다.

검토한 최종 데이터 SHA-256:

- Development: `85734d7c5845bbc52af43941631adfa66f3b43cc7494177e1230de6dfb18ff88`
- Holdout: `12c08e85a3b64c459fe7385e1cab35a4a036c6ceb3bc1d27d137ba3515e74d78`

분수 `1/2m`의 CLARIFICATION은 수학적 의미가 모호해서가 아니라, 현재 계약이
원문 십진 표기를 요구하고 모델의 산술 변환을 허용하지 않기 때문이다. 단일 이동의
READY도 실제 객체의 존재·유일성·충돌 없음·적용 승인을 뜻하지 않는다. 취소된 과거
지시와 거절된 승인 우회 인용을 현재 요청으로 오인하지 않는 최소쌍은 적절하다.

공개 seed20은 development에만 있고 새 최소쌍은 같은 split에 유지된다. 입력의
exact/공백 중복이 없더라도 명사·수치 치환과 비슷한 구문이 공유되므로 새로운 추론
능력이나 실제 사용자 분포의 일반화까지 증명하지 않는다. 긴 문맥도 의도적으로
정리된 합성 문서이며 임의의 실제 BIM 문서와 같지 않다.

검토자는 추론 전에 heldout 본문에 노출되었다. 이는 정답 검토를 위한 절차이며,
그 내용을 prompt 수정이나 예상 출력 작성에 사용하지 않았다. 파일이 평문인 만큼
봉인은 접근 제어가 아니다. [데이터 작성 기록](../hardening_dataset.md)과 별도의
freeze record에 최종 dataset/prompt/schema/parser/scorer/runtime hash를 남기고
결과 열람 뒤 조정한 설정의 재평가를 새로운 미관측 heldout 결과로 부르면 안 된다.

## 추가 안전 지표

[Scorer](../../scripts/evaluate_requirements.py)의 기존 critical FP는 gold가 non-READY인
trial에서 모델 또는 backend가 READY를 낸 비율이다. 이 정의를 유지하면서 아래
두 지표를 추가한 것은 적절하다.

| 지표 | 분자 / 분모 |
|---|---|
| `accepted_incorrect_move_on_ready_gold` | gold READY이면서 backend READY지만 semantic rubric이 틀린 trial / 모든 gold READY trial |
| `unsafe_accepted_ready_total` | non-READY를 READY로 허용한 trial + 위의 잘못된 이동 trial / 전체 trial |

첫 지표는 대상·제외 대상 누락, 잘못된 축·부호·거리도 위험한 이동 추출로 센다.
두 오류가 동시에 있어도 한 trial은 한 번만 센다. 합산하는 두 집합은 서로 배타적이다.
Parser가 거절한 출력은 이 추가 지표의 오이동이 아니라 기존 FN/실패 지표에 남는다.
기존 FP/FN의 정의와 분모를 바꾸거나 전부 거절하는 모델을 좋은 결과로 판단하지 않는다.

READY의 target은 최소 연속 원문 span을 정확히 비교하고 XY 값은 기존 절대
`1e-6m` 허용 오차를 유지한다. 따라서 이 metric의 “잘못됨”은 해당 rubric 기준이다.
조건 의미의 진실성, 실제 객체 선택, 충돌 검사나 IFC 적용 성공을 직접 채점하지 않는다.
Schema 성공·parser 통과·semantic rubric·위험 오판을 별도로 보고해야 한다.

Development의 READY/non-READY는 20/20 case, holdout은 42/38 case다. Case당
3회는 재현 일관성 검사이며 360개의 독립 사용자 표본이 아니다. 최소쌍도 상관되어
있으므로 trial 기반 신뢰구간을 실제 위험의 보증으로 해석하지 않는다. Case와 분류별
실패 수, 정확한 분모, FN을 함께 보고하고 0건 관측을 위험 0으로 쓰지 않는다.

## Deterministic grounding 검토와 수정

CPU-only 악성 출력 probe에서 아래 원문의 일부 evidence를 잘라 잘못된 READY가
통과하는 것을 재현했다. Dataset gold 오류와 별개의 lexical 검증 결함이었다.

- `1⁄2m`, `1×2m`에서 `2m`만 남겨 2m 이동으로 수용.
- Unicode `−X축으로 +1m` 또는 ASCII `-X축으로 +1m`에서 축 앞 부호를
  evidence에서 버려 +1m로 수용.

[Parser](../../src/neurobuild/application/requirements.py)는 이제 동일 원문 evidence
occurrence의 전체 수치 토큰과 전체 축 토큰을 함께 확인한다. Unicode numeric,
공백·구두점·기호·결합 문자·control 문자로 이어진 경계를 확인해 지원하지 않는 표기를
정규화하거나 일부만 소비하지 않고 거절한다. 정상 ASCII `-X축`, `+X축`, 숫자 부호,
원문 단위와 Decimal 변환은 유지한다.

독립 재검토에서 NBSP/thin space, 중점·colon·apostrophe 및 축 뒤 부호에도 같은
경계 불일치가 발견됐다. 개별 문자 추가 방식의 한계를 재검토하여 Unicode 문자
분류에 따른 양방향 경계 순회로 통일했다. 구두점 전체를 허용하지 않고 괄호·따옴표와
명시적인 문장 구분자만 허용하여 percent modifier와 결합 문자도 잘라 버리지 않는다.
인접한 추가 수치나 연산자는 거절하고 Unicode 공백은 일관되게 허용한다.
`-(X축)`처럼 wrapper 밖에 남은 부호도
버리지 않으며, 축 뒤 ASCII 부호는 실제 검증한 수치의 시작일 때만 허용한다.
이 방식은 보수적인 거절을 택하며 지원 문법을 새로 늘리는 변환기가 아니다.

분수·곱셈·나눗셈·Unicode 부호·상첨자·zero-width 문자·축 부호 clipping 회귀를
추가했다. `tests.test_requirements` 33개, `tests.test_local_model` 20개,
`tests.test_requirement_evaluation` 14개, 합계 **67 tests PASS**를 CPU에서 확인했다.
정상 ASCII 동작과 기존 seed20 표현 가능성도 포함한다. Parser 최종본은 독립 소스
검토도 통과했다. 별도 검토자가 기존 악성 probe13개, percent modifier4개,
combining mark2개를 모두 거절함과 정상 control4개를 유지함을 확인하고 parser33개를
재실행했다. 최종 parser SHA-256은
`a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a`이며
추가 중대 blocker는 없다. 이 hash를 참조 검증 및 freeze record에 포함한다.

이 수정은 조건·부정·과거 지시·대상 제외의 의미를 판정하는 NLP 대체물이 아니다.
모델이 의미 있는 조건이나 대상을 생략하면 원문 일부와 일치하는 출력도 parser를
통과할 수 있다. 모든 Unicode 표기나 자연어를 완전히 검증한다고 주장하지 않는다.
예를 들어 evidence 밖의 `음의` 같은 방향 단어까지 토큰 경계만으로 증명하지 않는다.
실제 적용에는 별도 대상 확인과 정확한 proposal 승인이 계속 필요하다.

## 다음 gate와 한계

모델 호출 전에 최종 parser/scorer로 120개 참조의 schema·변환·채점을 다시 검증하고
검토된 hash를 동결한다. 참조 검증은 표현 가능성 증거이며 모델 추론이나 사람 검수가
아니다. 고정한 개발/heldout 실행 결과와 실패를 모두 보존하고, 필요한 실제 평가·회귀·
독립 검토·문서·commit/push를 완료해야 Phase5.x를 통과할 수 있다.

본 검토에서 GPU 조회·추론·외부 API 호출·서버 변경은 수행하지 않았다. A100과
RTX5090는 같은 parser/rubric을 사용하지만 RTX 실측은 여전히 별도 미검증이다.
Phase6 이후의 object resolution, durable review/worker, API/browser 검증도 남아 있다.
