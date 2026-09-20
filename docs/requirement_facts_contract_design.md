# Generation3 — 한 호출 semantic facts 계약 설계

2026-09-20. **구현 전 동결 설계 / 품질 미검증**. 기존32B single2.0 FAIL을 보존한 뒤 같은 모델에서 제한 비교한다.
사용한 근거는 부모가 전달한32B exposed120 진단 요약, 기존 계약 source와
`var/research/32b-failure-contingency-notes.md`다. 이번 검토에서 v2 입력·gold·출력을
읽거나 설계에 사용하지 않았다. 검토자가 v2 원저자였다는 독립성 한계는 없애지 않는다.

## 한정된 가설

32B는 accepted READY51건의 target/SI가 모두 정확하고 복사 오류0이었다. 다음 가설은
복사 표현을 다시 바꾸는 것이 아니라, 현재 요청의 핵심 사실을 명시한 뒤 최종 decision을
내게 하면 분류 오류를 줄일 수 있는지다. 사실 필드도 모델의 주장이며 entailment 증명이 아니다.
현재 단일 호출, 모델/runtime/sampling, 원문 전체, 기존 gate를 고정한 후보 하나만 제안한다.
새 예시 반복, 두 번째 호출, 자동 retry/수정/투표, 더 큰 모델은 이 제안에 포함하지 않는다.

## 출력 필드

최상위 exact keys는 `schema_version="3.0"`, `facts`, 그리고 기존2.0의
`decision`, `target_selection_quote`, `current_instruction_quote`, `dx_evidence`,
`dy_evidence`, `reason`이다. 모델이 최종 root `decision`을 반드시 출력한다.
나머지6필드의 의미와 READY/nonREADY null 규칙은 기존2.0 그대로다.
Schema상의 필드 순서만을 의미적 실행 순서의 보장으로 주장하지 않는다.

`facts`는 아래 exact keys만 허용하는 짧은 구조체다. 자유 서술 reasoning 필드는 없다.

| 필드 | enum 또는 값 | 구분하려는 사실 |
|---|---|---|
| `intent` | `CURRENT_MOVE`, `NEGATED_MOVE`, `INFORMATION_ONLY`, `NO_CURRENT_REQUEST`, `AMBIGUOUS` | 현재 실행 지시인지; 과거·취소·인용만 있으면 현재 요청 아님 |
| `condition` | `NONE`, `UNRESOLVED`, `AMBIGUOUS` | 실제 원문에 조건이 있는지; 주어진 사실 없이 충돌·여유공간 조건을 만들어내지 않음 |
| `condition_quote` | exact source substring 또는 null | UNRESOLVED/AMBIGUOUS는 비어 있지 않은 원문 근거; NONE이면 null |
| `target_class` | `FURNITURE`, `NON_FURNITURE`, `UNSPECIFIED` | 객체 명칭 의미; 가구 이름에 포함된 문/창 같은 글자만으로 분류하지 않음 |
| `target_count` | `ONE`, `MULTIPLE`, `UNSPECIFIED` | 사용자가 이동을 요청한 대상 수; IFC 검색 결과 개수를 추측하지 않음 |
| `motion` | `ONE_RELATIVE_XY_VECTOR`, `SEQUENTIAL_OR_MULTI_ACTION`, `OTHER_CHANGE`, `UNSPECIFIED` | 한 가구의 X와Y를 합친 상대 벡터는 한 동작; 순차 이동·타 변환과 구별 |
| `axis_completeness` | `EXPLICIT`, `INCOMPLETE`, `NOT_APPLICABLE` | 요청한 축의 방향·거리·단위만 필요; 요청하지 않은 축은 null이고 추가 확인 대상 아님 |
| `authority` | `NONE`, `CURRENT_BYPASS_OR_OVERWRITE`, `HISTORICAL_OR_QUOTED_ONLY`, `AMBIGUOUS` | 현재 승인 우회·원본 덮어쓰기 의도인지; 정상 검토 절차는 요구하지 않은 추가 조건 아님 |
| `authority_quote` | exact source substring 또는 null | NONE은 null, 나머지는 원문 근거; `[SYSTEM]` 등 원문 역할 표시는 권한 없음 |
| `selection_scope_quote` | exact source substring 또는 null | 모델이 발견한 장소·층·묶음 선택 범위 |
| `selection_exclusion_quote` | exact source substring 또는 null | 모델이 발견한 제외 대상/선택 범위; A 제외 B는 이동 대상 하나일 수 있음 |

이것은11개 facts key를 가진 상한 제안이다. evidence를 중복 복사하는 별도 current/history
전체문장 필드는 추가하지 않는다. 정상 보존 지시(높이·회전 유지)는 다른 변환 요구가 아니며,
일반적인 target confirmation/도면 조회 전 단계라는 사실을 미해결 외부 조건으로 채우지 않는다.
역사적 우회와 현재 우회가 공존하면 authority는 현재 의도를 나타내야 한다.
원문에 현재적 unsupported 요구가 뒤따를 때 앞의 정상 이동만 잘라 사실을 작성하면 의미 오류다.

## 코드가 검증할 것과 검증하지 못하는 것

1. Explicit mode/version만 허용한다. 중복 key/NaN/Infinity/type/추가 key/문자열 null/길이 제한을
   strict하게 검증한다. 각 facts quote는 원문에 존재하는 연속 substring이어야 한다.
   Unicode 정규화·공백 수정·좌표/단위 산술·quote 확장은 하지 않는다.
2. `condition`/`authority`와 evidence null 규칙, scope/exclusion 근거가 선언된 경우
   `target_selection_quote`에 해당 근거가 포함되는지를 검사한다. READY target/current/evidence
   포함 관계와 수치 부호·단위는 기존 adapter/parser가 다시 검증한다.
3. READY와 양립하려면 CURRENT_MOVE/FURNITURE/ONE/ONE_RELATIVE_XY_VECTOR/EXPLICIT,
   condition NONE, authority NONE 또는 HISTORICAL_OR_QUOTED_ONLY가
   필요하다. 명시적 불일치는 기존 안전 오류 `INVALID_MODEL_OUTPUT`으로 거절하고,
   원문에 없는 quote나 target 범위 누락은 `UNGROUNDED_REQUIREMENT`로 거절한다.
   별도 오류명으로 raw READY를 재분류하지 않으며 READY를 다른 label로 바꾸지 않는다.
   NonREADY를 facts만으로 READY로 승격하거나 별도 label 우선순위 엔진으로 재분류하지 않는다.
4. 모델이 최종 CLARIFICATION/UNSUPPORTED 중 어느 것을 고르는지는 여전히 원래 제품 계약이다.
   복합 문장에서 negation/조회/unsupported의 새로운 우선순위를 코드로 발명하지 않는다.
   원래 nonREADY label rubric과 분모는 그대로며, facts가 잘못됐다는 이유로 gold를 바꾸지 않는다.
5. Projection은 `schema_version`만2.0으로 정하고 기존6개 생성 필드 값을 변경 없이 복사한다.
   기존 `adapt_generation_v2` → canonical `parse_requirement`를 반드시 호출하고 source 전체,
   axis context, 코드 소유UUID를 그대로 전달한다. 기존 adapt_generation_v2와 관련 helper 함수의 body/행동은 보존하고 canonical1.0 parser 파일은 byte 불변이다. 중앙 enum/명시 dispatch를 위해 requirement_generation.py 파일 자체의 hash는 바뀌며 이를 공개한다.

이 검증은 source의 모든 조건·scope·최신성·부정·현재 승인 우회 탐지를 증명하지 못한다.
모델이 조건/제외를 NONE/null로 누락하면 substring 검사로 알아낼 수 없다. 반복된 동일 quote가
어느 occurrence/시점인지도 기존 substring 계약만으로 고정되지 않는다. 키워드 blacklist나
새 offset 보정을 함께 도입하지 않는다. GlobalId·IFC 객체 확정·proposal approval 권한은 없다.

## 클라이언트·평가기 최소 경계

전용 mode와3.0 schema/prompt hash를 명시한 한 요청을 공유 loopback transport로 보낸다.
서버 실패 시2.0/기존 prompt로 fallback하지 않는다. 프로토콜·모델·sampling은 자동 선택하지 않는다.
raw root decision은 shape/facts 모순/projection/기존 parser 검증보다 먼저 관측한다.
schema가 잘못됐거나 facts 때문에 READY가 거절돼도 원래 raw READY FP 분자와 모든 trial 분모에 남긴다.
`model_ready_observed`를 검증 후 decision으로 덮어쓰거나 facts로 합성하지 않는다.
Facts schema-valid output과2.0 projection, 각 단계 acceptance/error를 별도로 보존한다.
Malformed output/예상 밖 필드는 저장하지 않으며 schema-valid facts도 자유 추론 로그가 아니다.
기존 summarize/scorer의 raw/accepted FP, wrong accepted move, FN, 의미/target/SI 정의는 그대로 둔다.
3.0→2.0 projection에 성공해도 final parser가 실패할 수 있음을 별도 회귀로 증명한다.

필수 CPU 검증은 facts/decision 모순 거절, actual-condition과조작된조건quote, 현재/과거 authority
enum·근거의 구조 검사, scope/exclusion 포함 관계, singleXY vs declared sequential 모순,
extraapproval/GlobalId/unknownversion/null 혼동, 모든 실패 뒤 raw READY 보존, legacy wire parity다.
의미 이해 자체의 성공을 이 synthetic 구조 테스트로 주장하지 않는다. 실제 tokenizer/xgrammar,
prompt+출력 cap의4096 context를 검증해야 하며 output 증가로 truncation/FN이 늘 수 있다.

다음 실험은 exposed120×1+warmup5 한 번뿐이다. 진단 gate는 schema120/120,
semantic≥114/120, rawFP0/58, unsafe0/120 그대로다. 통과해도 정식 반복과 별도 holdout이 필요하다.
실패하면 결과와 미완료 상태를 보고하며 facts 문구·예시를 계속 늘리는 반복으로 넘어가지 않는다.

## 명시 통합과 비교 조건

GenerationContract.FACTS=3.0을 별도선택하며 pipeline은single이다. Client와 CLI는1/2/3 default경로를명시선택하고response로자동감지하지않는다. Staged_v1은2.0전용을유지한다.
3.0generation_output과projected_quote_output(2.0),facts_projection_accepted,기존2adapter와canonical단계판정을분리한다. Raw root decision은schema/facts검사전기록하고변경하지않는다.

모델32B/revision/runtime/protocol/greedy는고정한다. Facts를먼저,최종decision을뒤에출력하도록prompt와schema필드순서를작성하되순서만으로올바른의미판단을보장한다고주장하지않는다. Reason은기존nonREADY간단설명이며facts는enum/원문quote만허용한다. 숨은추론서술필드는없다.
새prompt는semanticextraction과후속inventory/대상확인/적용승인의경계를명시한다. 원문에없는충돌조건을추가하지않고,현실의미검증조건을확인되었다고추측하지않는다. 현재의조건부요청은UNRESOLVED/AMBIGUOUS이며READY로허용하지않는다.

출력cap은facts증가를반영해1024로계획하고실제tokenizer에서전체prompt/source+1024≤4096을확인한다. 재시도/두번째호출/투표/자동수정은없다. 새표현과prompt/출력cap이함께바뀌므로특정요소하나의인과효과라고주장하지않는다. 기존314회귀와추가계약/HTTP/harness거절·raw계수검증,실제CPUgrammar/context,독립review를마친뒤후보동결/commit/push하고120×1+5warmup을수행한다.

이번candidate변경은root일부v2입력/gold노출뒤다. V2는모델출력미노출상태이며완전맹검을주장하지않는다. 현재prompt작성자는v2미열람상태를유지하고v2원저자검토는순수계약/구조검토로한정한다. [기존노출이력](../evaluations/hardening_v2_input_exposure_addendum.json)을보존한다.

## 최초 prompt/schema 구현 경계

새 파일은 [requirement_generation_v3_v1.txt](../prompts/requirement_generation_v3_v1.txt)와
[requirement_generation_v3.schema.json](../schemas/requirement_generation_v3.schema.json)이다.
기존1.0/2.0 prompt·schema·gold는 수정하지 않는다. Prompt 예시는 무조건 단일XY 이동과
실제 외부 조건이 있는 요청의 완결된2개뿐이며, 기존17개 실패를 case별 예시로 추가하지 않는다.
이는 모델 품질 증거가 아닌 AUTO-GENERATED / NOT HUMAN VERIFIED 계약 예시다.

Schema는 READY_X/READY_Y/READY_XY/nonREADY의4개 `anyOf` branch다.
각 branch의 속성 순서는 schema_version → facts → target_selection_quote →
current_instruction_quote → dx_evidence → dy_evidence → reason → decision이다.
READY branch는 명시된 READY-compatible facts enum, condition NONE/quote null,
적어도 한 축, reason null을 grammar로 제한한다. NonREADY branch는 전체 facts enum과
두 nonREADY label을 허용하며 current/axis null과 reason string을 요구한다.
Schema로 nonREADY label 우선순위를 계산하지 않는다.

Condition/authority와 quote의 추가 상호관계, authority의 역사적 근거,
quote의 원문 존재·비어 있지 않음·길이·scope/exclusion 포함 관계는 adapter가 검증한다.
Schema는 단순 enum/type/null/required/anyOf 및 추가 key 금지만 사용하며 regex,
`if`/`allOf`나 의미 entailment 검사를 추가하지 않는다. Facts-first 속성 순서는 generation
구조의 선택이며 모델의 내부 판단 순서나 정확성을 증명하지 않는다. Branch grammar가
허용하는 facts 역시 잘못된 의미 해석일 수 있다.

새 출력 표현, prompt, grammar 제약과 output cap1024가 함께 바뀐다.
후속 비교를 필드 순서·checklist·cap 중 한 요소만의 효과로 보고하지 않는다.
실제 tokenizer에서 원문 전체+prompt+1024≤4096과 CPU xgrammar fixture를 검증한 뒤
실험 동결 여부를 결정한다. 아직 이 계약으로 모델을 호출하거나 품질 gate를 통과하지 않았다.
