# Generation2 설계·adapter·평가기 독립 검토

2026-09-20 KST. **CPU 경계/호환성 검토 PASS, 새로운 모델 품질은 아직 미검증.**
[설계](../requirement_generation_v2_design.md), adapter/schema, client의 명시 계약 연결,
평가기 변경과 경계 테스트를 읽었다. 검토자는 model/HTTP/GPU 호출, 설치,
source·prompt·gold 수정 없이 CPU 재생과 아래 독립 probe만 수행했다.

## 검토한 파일 snapshot

| 파일 | SHA-256 |
|---|---|
| `application/requirements.py` | `a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a` |
| `application/requirement_generation.py` | `6c5c9d509a919f32262a3a95f7350a79c2a7229cf23940ca7f8c3ccdd8bd9f31` |
| `infrastructure/local_model.py` | `89c02812a454c292eb906e71cf2d2c487d29ba1e1e96e8bccd87a32468d294b8` |
| `schemas/semantic_requirement.schema.json` | `dd131db08fe9087e795059445b075f22876e44b42481201cc0ea70608a708f94` |
| `schemas/requirement_generation_v2.schema.json` | `6ca6fed3e8666244cd4bd779d33c0dd647490d5f641134307930008ea440436c` |
| `scripts/evaluate_requirements.py` | `938dfa586c5d23f7d92b7634f19ea1202c547780201f381bcaab086ea4fba210` |
| `tests/test_requirement_generation.py` | `98f69ce6874443f769b63090c6436ef5e4e071a23158c027eb00b371728d07a1` |
| `tests/test_requirement_generation_evaluation.py` | `431bf1a80276f2d2c4e4874c9431f4cc03cbbee1bacc590ac506061a3d2e8b93` |

앞의 application/infrastructure 경로는 `src/neurobuild/` 기준이다.
기존 parser/schema bytes와 gold는 그대로 유지됐다. 새 version2.0은 별도 generation
계약이며 최종 domain projection은1.0이다. 응답이나 GPU/model 이름으로 버전을 추측하지
않고, 알려진 client 설정만 enum으로 변환한다. Wrapper는 정확한 enum만 받는다.

## 검증 경계

일곱 key/version/type/길이/JSON 중복과 READY/non-READY 교차 조건을 투영 전에 검사한다.
Non-READY에 들어온 instruction/evidence를 버려서 유효하게 만들지 않는다. READY의
reason, 빈 evidence, 추가 GlobalId/approval/value/unit도 거절한다. 원본 source와
code-owned UUID/context를 최종 기존 parser에 그대로 전달한다.

수량은 한 evidence의 `_QUANTITY` 일치 하나에서 얻고 원래 숫자 spelling을 보존한다.
Positive/negative 후보를 각각 기존 `_axis_length`에 **선택 instruction과 전체 source**로
검사한다. Float/Decimal 재직렬화, 단위 산술, Unicode 부호 정규화, source 축소가 없다.
명시 plus와 leading/trailing zero, word/axis negative, 한국어 단위 매핑도 기존 계약이다.
Signed zero를 수치 동등성으로 합치지 않으며 null/빈 문자열/0을 구분한다.

Adapter 자체의 축 집합·all-zero 검사 뒤에도 최종 `parse_requirement()`가 필수다.
Schema-valid이지만 원문과 다른 숫자의1.0 projection을 adapter mock이 반환하도록 한
독립 테스트에서 **adapter_accepted=true / legacy_schema_valid=true /
parser_accepted=false / UNGROUNDED_REQUIREMENT**를 직접 확인했다.
기존 축 누락 테스트는 adapter에서 먼저 거절하므로 최종 parser 실행을 직접 증명하지
않았다. 보강을 권고했고, root가 추가한 뒤1개 focused 실행이 PASS했다.

별도 **20개 CPU probes PASS**: 정확한0.50·+001.20·한국어 단위·negative-axis,
signed -0와 다른 축 nonzero 보존; all-zero·누락 축·comma/fraction/exponent/NBSP/
combining-mark suffix·상충 sign·wrong-axis·빈 evidence·version spoof·추가 field·
non-READY 교차 위반·string contract 거절을 확인했다. 이는 합성 경계 검사이며
사람이 검수한 요구사항 또는 LLM 정확도 검증은 아니다.

## 오류 집계와 기존 결과 보존

Raw decision/READY는 generation schema와 adapter보다 먼저 관측한다. Adapter 실패가
CLARIFICATION으로 바뀌거나 raw FP에서 빠지지 않는다. Schema-valid generation2
원출력은 `generation_output`,1.0 projection은 `semantic_output`으로 분리한다.
`schema_valid`는 해당 run의 **generation shape** 통과율이다. Generation/adapter/
canonical schema/final parser 수용 여부를 따로 기록하고 실패도 전체 분모에 남긴다.
원문 target scope를 gold로 복구하거나 정답으로 재채점하는 경로는 없다.

새 harness로 **기존 Phase5.x 12개 archive,640개 응답**을 모두 재생했다. 기존 parser
수용/오류·SI·각 scorer 필드와 `summarize` 전체가 저장된 결과와 exact match였다.
V3/v4 각120회와 나머지10개 단회 진단 각40회를 포함한다. Legacy run에는 새
generation2 단계 지표가 추가되지 않으며 기존 metric 정의·gold·archive는 바뀌지 않았다.
Manifest는 명시한 generation contract와 generation schema/prompt, adapter,
canonical schema, parser/client/scorer hash를 구분한다.

## 한계와 다음 gate

반복 인용 검사는 **어떤 유효 occurrence가 존재함**을 확인할 뿐 모델이 의도한 위치,
최신 지시, 조건 충족 또는 누락된 대상 scope의 완전성을 증명하지 않는다. Target나
instruction을 늘려 복구하지 않으며, READY는 대상 확인·proposal 승인 권한이 아니다.
Generation2는 중복 숫자 작성 부담을 줄이는 표현 변경이다. 의미 정확도 향상을
미리 인정하거나1.0과 generation schema 통과율만으로 우열을 판단하지 않는다.

담당자가 제공한 [CPU grammar/token 증거](../../evaluations/results/phase5x/generation2-cpu-preflight.json)를
읽고 hash `488ae1a1510fa2c210a38e45f432088ed9a44c832961d0ad299f2e46006da109`를
대조했다. 이는 검토자가 다시 실행한 GPU/grammar 테스트가 아니다. 그 증거는
6개 예시 parity와 token/EOS 수용, 추가 approval 거절, context4096 내 development3571/
holdout 입력 길이만3576 tokens(출력 cap768 포함)을 기록한다. 실제 모델 호출 성공이나
semantic gate 통과를 뜻하지 않는다.

현 범위의 추가 blocker는 없다. Root가 실행한 전체290 tests PASS/skip0(17.329초)의
통합 증거와 독립 CPU 검토를 구분하며, frozen 신규 diagnostic 뒤 정식 development와
holdout gate가 필요하다. Gold는 계속 **AUTO-GENERATED / NOT HUMAN VERIFIED**다.
