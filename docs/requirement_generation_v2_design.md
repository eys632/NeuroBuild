# Quote-only requirement generation 2.0

## 상태와 목적

이 설계는 MoE + prompt v4가 기존 gate를 통과하지 못할 때만 진행할 계획이었다.
2026-09-20 root가 v4 diagnostic **34/40 FAIL**을 확인한 후 새 adapter/schema와
CPU 검증의 구현을 승인했다. 이 문서 작성 단계에서는 2.0 모델 호출이나 품질 향상을
검증하지 않았다. 실제 추론 결과와 최종 선택은 별도의 frozen run으로 판단한다.

모델은 대상·현재 지시·축별 근거를 원문에서 인용한다. 숫자와 단위를 별도로 다시
작성하거나 변환하지 않는다. 코드는 인용에 이미 있는 숫자 spelling/단위/부호를
검증하여 기존 1.0 JSON으로 투영하고, **변경하지 않은 1.0 parser**를 다시 통과시킨다.
중복 숫자 작성 오류를 줄일 수 있다는 가설이며, 의미 분류나 대상 범위 누락을
결정론적으로 해결했다는 주장은 아니다.

범위는 [새 adapter](../src/neurobuild/application/requirement_generation.py),
[새 generation schema](../schemas/requirement_generation_v2.schema.json),
[경계 테스트](../tests/test_requirement_generation.py)다. Client/prompt/evaluator 연결은
별도 변경으로 검토한다. Domain, IFC, workflow 승인, 기존 gold와 acceptance는 유지한다.

## 명시적 API와 호환성

```python
from neurobuild.application.requirement_generation import (
    GenerationContract,
    adapt_generation_v2,
    parse_generated_requirement,
)

# enum 정의: LEGACY = "1.0", QUOTES = "2.0"
legacy_json = adapt_generation_v2(response_text, source_text=original_source)

requirement = parse_generated_requirement(
    response_text,
    generation_contract=GenerationContract.QUOTES,
    source_text=original_source,
    requirement_id=requirement_id,
    project_id=project_id,
    base_revision_id=base_revision_id,
    axis_convention="project_xy",
)
```

`adapt_generation_v2(response_text: str, *, source_text: str) -> str`는 2.0의 형태,
상태별 null 규칙과 원문 근거를 검사하고 canonical 1.0 JSON 문자열을 반환한다.
Canonical은 UTF-8로 표현 가능한 문자열을 유지하는 `ensure_ascii=False`, key 정렬,
compact separators다. 원문 인용의 내용은 정렬·정규화하지 않는다. 이 반환값은
승인이나 완성된 `SemanticRequirement`가 아니다. UUID/context 검증을 포함한 최종
`parse_requirement()`가 필수이므로 제품 경계에서는 wrapper를 사용한다.

`parse_generated_requirement(response_text: str, *, generation_contract:
GenerationContract, source_text: str, requirement_id: UUID, project_id: UUID,
base_revision_id: UUID, axis_convention: str | None = None) -> SemanticRequirement`는
명시된 enum만 받으며 기본 contract가 없다. LEGACY는 원래 응답을 그대로 기존 parser에
전달한다. QUOTES만 adapter → 기존 parser를 거친다. 응답의 `schema_version`, 모델명,
GPU 종류, HTTP 오류를 보고 contract를 선택하거나 다른 버전으로 재시도하지 않는다.

Client는 기본값 LEGACY를 유지하고, 문자열 설정을 허용한다면 생성 시 알려진 enum으로만
변환해야 한다. Prompt/schema/contract를 함께 선택하고 manifest에 기록한다. Generation
contract는 `legacy_guided_json`/`structured_outputs`라는 **HTTP protocol과 별개**다.
어느 transport를 쓰든 명시한 generation contract를 검증해야 한다.

이 실험의 frozen 1.0 bytes는 다음과 같다. 공유 private helper를 같은 Application
package 안에서 import하여 현재 경계를 재사용한다. helper 추출/refactor는 이번 변경에
포함하지 않는다.

| 파일 | SHA256 |
|---|---|
| `src/neurobuild/application/requirements.py` | `a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a` |
| `schemas/semantic_requirement.schema.json` | `dd131db08fe9087e795059445b075f22876e44b42481201cc0ea70608a708f94` |

## 7개 필드 계약

JSON object에는 아래 일곱 key가 모두 있어야 하며 추가 key는 금지한다. UUID, GlobalId,
approval, operation, value/unit, tool call, raw IFC, reasoning을 출력에 넣지 않는다.

| 필드 | READY | CLARIFICATION / UNSUPPORTED |
|---|---|---|
| `schema_version` | 정확히 `"2.0"` | 정확히 `"2.0"` |
| `target_selection_quote` | 비어 있지 않은 원문 exact substring, 최대 1024자 | 원문 exact substring 또는 빈 문자열; 기존 v1 규칙 |
| `current_instruction_quote` | 비어 있지 않은 현재 전체 지시의 exact substring, 최대 4096자 | `null` |
| `dx_evidence` | X축·명시적 방향·단일 수량/단위를 함께 포함한 exact substring, 최대 512자 또는 `null` | `null` |
| `dy_evidence` | Y축·명시적 방향·단일 수량/단위를 함께 포함한 exact substring, 최대 512자 또는 `null` | `null` |
| `decision` | `"READY"` | `"CLARIFICATION"` 또는 `"UNSUPPORTED"` |
| `reason` | `null` | 비어 있지 않은 짧은 이유, 최대 512자 |

READY에서 `target_selection_quote`는 `current_instruction_quote` 안에 있어야 하고,
각 non-null axis evidence도 같은 선택 지시 안에 있어야 한다. 적어도 한 축이 non-null이어야
한다. Source 16000자, final JSON 16384자, decimal 30자·정수부 16자리·소수부 12자리 등
기존 한도를 유지한다. 중복 JSON key, NaN/Infinity, fence, 뒤에 붙인 JSON/text, 잘못된
scalar type, NUL/lone surrogate를 거절한다. 오류는 원문을 echo하지 않는 기존
`INVALID_MODEL_OUTPUT`, `INVALID_REQUIREMENT_INPUT`, `UNGROUNDED_REQUIREMENT`다.

```json
{
  "schema_version": "2.0",
  "target_selection_quote": "회의실 입구 쪽 책상 말고 창가 쪽 책상",
  "current_instruction_quote": "회의실 입구 쪽 책상 말고 창가 쪽 책상을 -X축으로 125.0mm 옮겨줘.",
  "dx_evidence": "-X축으로 125.0mm",
  "dy_evidence": null,
  "decision": "READY",
  "reason": null
}
```

Schema의 properties/required와 위 예시는 version → quotes → decision → reason 순서다.
JSON key 순서는 backend 의미 검증에 영향을 주지 않는다. 생성 prompt 예시도 같은 순서로
고정한다면 representation과 생성 순서가 함께 바뀐 실험이며 순서만의 인과 효과로
해석하지 않는다. 설치된 xgrammar 0.1.18 호환을 위해 generation schema에는 기존 schema와
같이 단순 type/enum/required/additionalProperties만 사용한다. 길이·상태별 null·원문
조건은 backend가 강제하며, schema 통과만으로 이를 통과했다고 기록하지 않는다.

## 원문 수량과 부호를 도출하는 경계

1. 각 non-null evidence에서 기존 `_QUANTITY`가 찾는 수량이 정확히 하나여야 한다.
   `group(1)`의 숫자 spelling과 `group(2)`의 원 단위를 사용한다. `_UNIT`은 m/cm/mm와
   같은 뜻의 한국어 단위 표기만 기존 방식으로 매핑한다.
2. 숫자에서 선행 ASCII 부호만 분리한 magnitude를 그대로 보존한다. Positive 후보는
   원 숫자에 `+`가 있었으면 이를 보존하고, 아니면 magnitude 그대로다. Negative 후보는
   `-` 하나와 magnitude다. `125.0`, `0001.2500`, `-0.00`을 float 또는 Decimal→str로
   다시 쓰지 않는다. 이 두 후보는 모델 재호출이나 의미 추측이 아닌 bounded validation이다.
3. 각 후보에 기존 `_axis_length({value, unit, evidence}, axis,
   selected_instruction, original_source)`를 호출한다. **원본 전체 source를 유지**한다.
   축/단일 수량/명시적 sign, 추가 숫자, 숫자·축의 온전한 source token span, Unicode
   operator/mark/control, 단위 suffix, arithmetic clipping 검사는 기존 helper가 담당한다.
   정확히 한 후보만 통과해야 한다. 명시 방향 없는 `X축 1m`, 상충 sign, 부호를 자른
   evidence는 거절하며 음수 두 개를 임의로 양수로 곱하지 않는다.
4. 선택된 current instruction의 명시 축 집합이 evidence의 축 집합과 같아야 한다.
   모든 명시 축이 0이면 거절한다. `null`만 미요청 축이다. 빈 문자열을 null로 바꾸거나
   숫자 0의 truthiness로 축을 생략하지 않는다. 한 축의 signed zero와 다른 축의 nonzero는
   원래 spelling으로 보존할 수 있다.
5. READY의 projection은 code-owned `MOVE_FURNITURE`, `PROJECT_WORLD_XY`, 원래 target와
   instruction, 검증한 축별 `{value, unit, evidence}`다. Non-READY는 원 decision/target/
   reason과 `operation=null`이다. 이후 원본 source, code-owned UUID, 원 context로 기존
   `parse_requirement()`를 실행한다. metre 변환과 미요청 축 0m 처리는 기존 코드 책임이다.

`_whole_source_tokens`는 instruction/evidence가 원문에 여러 번 나올 때 같은 occurrence의
온전한 axis와 quantity가 함께 존재하는지를 검사한다. 하나 이상의 유효 occurrence가
있다는 조건이다. 모델이 어느 동일 문자열 occurrence를 의도했는지, 시간상 최신 지시인지,
문장 밖 조건이 무엇인지를 이 검사로 증명하지 않는다. occurrence 모호성을 숨기기 위해
source를 evidence로 축소하지 않는다.

## 복구하지 않는 의미 정보

Target와 current instruction은 모델이 낸 exact substring을 그대로 유지한다. 누락된
위치/층/색/제외 조건을 inventory, gold 또는 전체 source에서 찾아 덧붙이지 않는다.
`current_instruction_quote`가 잘못되었을 때 전체 source로 fallback하지 않으며 서로
떨어진 인용을 이어 붙이지 않는다. Scorer의 `expected_ready_target()`은 gold 평가
전용이고 production adapter가 호출해서는 안 된다.

짧아진 target가 여전히 원문 부분 문자열이면 grounding만으로 누락을 판정할 수 없다.
조건·부정·복수 작업·현재 지시의 완전성·현재/과거 구별 역시 모델의 semantic 책임이다.
따라서 형식이 더 단순해져도 raw READY 오판이나 target 범위 손실은 여전히 실패다.
`SemanticRequirement`는 target confirmation, proposal approval, Apply 권한을 부여하지 않는다.

## 평가와 원래 오류의 보존

평가기는 응답을 strict JSON으로 decode한 직후, generation schema/adapter/parser 전에
알려진 `decision`의 `raw_model_decision`과 `model_ready_observed`를 기록한다. 이후
adapter가 거절해도 READY 관측은 지우지 않으며 CLARIFICATION으로 바꾸지 않는다.
JSON 자체가 잘못되어 decision을 읽을 수 없으면 unknown으로 남기고 별도 관측률을
기록한다. Malformed text를 regex로 구제하거나 reasoning에서 decision을 가져오지 않는다.

2.0의 단계는 `generation_schema_valid`, `adapter_accepted`, `legacy_schema_valid`,
`parser_accepted`로 구분한다. 기존 `schema_valid` 집계가 있으면 해당 run의 명시한
generation schema 통과율임을 정의한다. JSON parsing/schema/adapter 실패도 전체 trial
분모에서 제외하지 않는다. Schema-valid 2.0 final object와 adapter가 만든 1.0 projection은
별도 필드로 보존한다. 둘을 원본 모델 출력처럼 혼합하거나 기존 archived 결과를 rewrite하지
않는다. Malformed raw text, 알 수 없는 field, reasoning/HTTP body/secret은 저장하지 않는다.

최종 기존 scorer에는 검증된 1.0 projection 및 `SemanticRequirement`를 전달한다.
Adapter 실패 시 requirement는 없으므로 accepted decision/target/value 정답 점수를
얻지 못한다. Raw decision은 별도 원관측으로 유지하여 다음 지표를 동일하게 계산한다.

| 지표 | 유지할 정의 |
|---|---|
| Raw READY false positive | non-READY gold 중 원 모델이 READY를 낸 수 / non-READY gold 수; adapter 거절도 포함 |
| Accepted READY false positive | non-READY gold 중 최종 parser가 READY를 수용한 수 / non-READY gold 수 |
| READY false negative | READY gold 중 최종 READY로 수용하지 못한 수 / READY gold 수 |
| Unsafe accepted total | non-READY gold의 accepted READY + READY gold의 target/value 등이 틀린 accepted move / 전체 trial 수 |
| Target/unit/semantic | 기존 exact target scope/exclusion 및 metre/value rubric을 동일하게 적용; projection 실패를 정답으로 보정하지 않음 |

Manifest에는 generation contract, 선택한 generation schema/prompt SHA, adapter SHA,
기존 parser/legacy schema/scorer SHA, protocol/runtime/model/sampling 설정을 구분한다.
1.0 archived replay는 adapter 없이 동일 경로를 사용한다. 새 결과는 다른 run으로 보존한다.

## 최소 검증과 gate

- 기존 1.0 parser/schema bytes, legacy routing과 frozen metric replay가 유지되어야 한다.
- Exact spelling/leading zero/explicit plus/word 또는 axis minus/한국어 단위/precision
  context/signed zero/null을 검증한다. Unsupported 숫자·Unicode·잘린 sign/단위, 여러 수량,
  잘못된 축, 상충 방향, 한도 초과는 기존 경계 그대로 거절해야 한다.
- Target/source/current-instruction 정확성, 과거 evidence 재사용, 누락된 현재 두 번째 축,
  반복 인용, 두 축 0, non-READY null 규칙, strict 7개 key/version/type/UUID/context를 검사한다.
- Client는 explicit contract별 prompt/schema/adapter를 사용하고 기본 1.0 wire를 유지한다.
  버전 추측, 자동 fallback, grammar 없는 재시도는 없어야 한다.
- Evaluator는 raw READY를 schema/adapter 실패 뒤에도 보존하고 오류 분모를 유지해야 한다.
  Sanitized 2.0 output와 1.0 projection을 구분하며 기존 rubric/gold를 수정하지 않는다.
- Installed tokenizer/xgrammar의 CPU grammar compile와 strict-key accept/reject를 확인한 뒤
  신규 frozen model run으로 실제 transport와 semantic 성능을 검증한다. CPU fixture나
  HTTP200은 모델 정확도 증거가 아니다.

Acceptance는 기존 **schema 100% / semantic 95% 이상 / raw READY false positive 0 /
unsafe accepted output 0**을 유지한다. 고정 development/holdout 분리, 정식 반복 횟수,
holdout 결과 비열람 원칙과 **AUTO-GENERATED / NOT HUMAN VERIFIED** 표기도 유지한다.
Development 단회 진단은 정식 gate를 대신하지 않는다. Representability reference는
code 경계 검증이며 LLM 품질 결과가 아니다.

구현 직후 실행한 focused CPU 검증:

```sh
PYTHONPATH=src .conda/bin/python -B -m unittest \
  tests.test_requirement_generation tests.test_requirements -v
```

새 adapter 22개와 기존 parser 33개, 총 **55 tests PASS**. 별도 architecture agent의
20개 CPU boundary probe와 source review도 PASS이며 새로운 blocker는 보고되지 않았다.
이 결과는 adapter와 frozen parser 경계만을 검증한다. Client/evaluator 통합, grammar,
실제 모델 호출의 최종 증거는 각각 담당 검증과 run manifest를 따른다.
