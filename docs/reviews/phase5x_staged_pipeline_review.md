# Phase5.x staged_v1 독립 검토

2026-09-20 KST. **Source/accounting/CPU compatibility 검토 PASS. 모델 품질 gate는 아직 검증하지 않았다.**
이 검토는 분류→decision 고정 추출 실험을 동결해 비교할 수 있는지 확인했다.
기존 단일 호출 14B 진단과 첫 MoE holdout의 실패는 유지되며 Phase5.x 완료나 후보 채택을 뜻하지 않는다.
미노출 v2 holdout의 입력·gold는 읽지 않았다.

## 계약과 회귀 경계

`LocalStagedRequirementClient`를 명시적으로 선택해야 두 단계가 실행된다.
첫 응답은 `classification-1.0`의 version/decision 두 필드이고, 그 decision을 코드가
기존 generation2 branch schema에 고정한 뒤 두 번째 요청을 보낸다.
READY의 X/Y/XY 세 branch와 각 non-READY의 null 규칙을 유지한다.
약화한 template·다른 version·추가 authority 필드는 거절하며 응답을 보고 계약을 자동 선택하지 않는다.

두 단계 모두 원래 source_text 전체와 axis_convention을 받는다. 두 번째에는 코드가 검사한 decision만 추가한다.
추출기가 분류를 바꾸거나 첫 단계가 선택한 짧은 문장으로 전체 문맥을 대체하는 경로는 없다.
정상 분류에서는 non-READY도 target/reason을 채우기 위해 두 번째 호출을 하므로 예정 호출 수는2다.
분류 실패에는 추출을 호출하지 않는다. 각 stage timeout60초를 선택하면 전체 지연은120초에 이를 수 있다.

최종 domain 객체는 기존 `parse_generated_requirement` → generation2 adapter → generation1 parser를 통과한다.
Adapter와 parser hash는 각각 `6c5c9d…9f31`, `a940f395…4a`로 이전과 같다.
숫자·부호·단위·원문 occurrence 검증, code-owned UUID 및 별도 target/proposal 승인 경계를 완화하지 않았다.
재시도, 투표, quote 교정, target 자동 확장, non-READY 재분류, 외부 API fallback도 추가하지 않았다.

공유 transport refactor는 loopback·proxy/redirect 금지·크기/timeout·model alias·truncation·reasoning 차단을 재사용한다.
Backend는 stdlib/jsonschema만 사용하고 Torch/vLLM을 import하지 않는다.
[독립 wire 비교](../../evaluations/results/phase5x/staged-v1-single-wire-parity.json)에서 clean007d893의
기존 client와 최종 client를 generation1.0/2.0 × legacy/modern dialect 4조합으로 비교했다.
URL, headers, timeout, JSON request bytes가 모두 동일했다. 실제 HTTP나 GPU 요청은 없었다.
이는 RTX5090 현대 runtime의 실행 검증을 대신하지 않는다.

## 발견한 문제와 수정 검증

최초 구현은 `complete_staged` 안에서 DomainError만 보존했다.
실제 classifier completion을 READY로 주고 extractor에 `RuntimeError`를 주입하면 evaluator의 바깥 generic catch가
classification을 없애 **raw decision=null, raw FP=0/1**로 집계하는 문제를 재현했다.
후속 단계 실패가 최초 판단을 지운다는 점에서 수정이 필요한 accounting 오류였다.

수정 후 ordinary Exception은 이미 받은 두 completion을 보존하면서 `LOCAL_MODEL_RESPONSE_INVALID`만 반환한다.
원래 예외 메시지를 출력에 넣지 않으며 KeyboardInterrupt/SystemExit는 계속 전파한다.
[독립 fault proof](../../evaluations/results/phase5x/staged-v1-error-accounting.json)는 실제 staged client에서
실제 evaluator/summarize까지 연결하여 아래 결과를 확인했다.

- Timeout, truncation, HTTP/response/unavailable/oversize/reasoning 오류7개와 RuntimeError/ValueError2개,
  추출 JSON/schema 오류2개: **11/11에서 raw READY와 FP1/1·전체 평가 분모 유지**, 최종 parser 수용은 거절.
- 예외 및 잘못된 응답에 넣은 sentinel 문자열은 저장된 row에 포함되지 않음.
- KeyboardInterrupt/SystemExit2개는 완료 trial로 바뀌지 않고 전파됨.

Classifier raw decision은 schema 판정과 후속 실패보다 앞에서 별도로 관측한다.
Schema-valid classification/extraction만 보존하고, canonical parser/rubric은 기존 평가 경로를 사용한다.
따라서 “추출에서 막았다”는 이유로 classifier READY false positive를 지우지 않는다.
Transport 단계에서 final 응답 자체가 없으면 raw decision은 unknown이며 row는 여전히 전체 분모에 남는다.

## 실제 14B tokenizer와 CPU grammar

[최종 CPU proof](../../evaluations/results/phase5x/staged-v1-cpu-preflight.json)는 공식 14B AWQ의
기존 local revision `31c69efc29464b6bb0aee1398b5a7b50a99340c3`를 사용했다.
실제 embedded chat template hash는 `a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8`이며
이전 [14B metadata/template 검증](phase5x_generation2_14b_preflight_review.md)과 같다.
Transformers4.51.3/xgrammar0.1.18, vocab151936에서 네 schema를 실제 tokenizer로 compile했다.

Classification, READY, CLARIFICATION, UNSUPPORTED schema 모두 installed vLLM의 unsupported-feature 검사에서 false였다.
각 decision과 X-only/Y-only/XY의 valid8개는 JSONSchema 및 token+EOS 검증을 통과했고,
잘못된 version/decision·추가 approval·null 규칙 위반 등 invalid20개는 모두 거절됐다.
Compiled schema가 canonical branch 조건을 우회하는 근거는 발견하지 못했다.

실제 client의 opener를 fake로 바꾸어 기존 exposed120개를 각 classifier decision으로 전달했다.
720개 fake transport 요청의 schema, 전체 원문, context, decision binding, T0/seed42,
non-thinking/no-fallback 및 stage별 output cap을 확인했다. Fake decision은 길이·계약 fixture이며 모델 예측이 아니다.
서버에 보낼 실제 messages를 tokenizer에 넣은 결과는 다음과 같다.

| Stage | 입력 tokens 범위 | 출력 cap | 최대 입력+출력 /4096 |
|---|---:|---:|---:|
| Classification | 820–1200 | 128 | 1328 |
| READY extraction | 885–1265 | 768 | 2033 |
| CLARIFICATION extraction | 887–1267 | 768 | **2035** |
| UNSUPPORTED extraction | 886–1266 | 768 | 2034 |

모든120개와 세 decision 길이를 검사했고 최대 여유는 위 최악 경로에서2061tokens다.
`CUDA_VISIBLE_DEVICES=''`, offline 설정, 실제 CUDA 미초기화를 확인했다.
Weight·모델 inference·GPU 조회·새 네트워크 요청은 없었으며 CPU grammar 처리에만 Torch를 import했다.
Tokenizer/schema/transport 검증은 분류의 의미 정확성이나 대상 제외 범위 보존을 보장하지 않는다.

## 증거 고정과 남은 gate

최종 proof는 실행 시작/종료의 source hash가 동일함을 확인했다.
Shared transport `9732ad69…57c3`, staged client `7e79b1c4…efee`, evaluator `e1144884…a36a`다.
전체 hash는 CPU proof에 있다.

| 보존 proof | SHA-256 |
|---|---|
| CPU preflight | `29382a48d00c286d1adff107550508799379d1d70aa4289565468867152da86f` |
| Error accounting | `1da2cdde897f8624ed1a39ba70bc3ef4c0182611df69a98e6db0afd594c76223` |
| Existing wire parity | `1c3a2fb6cd57dcc2fbca872c0d2fb396b1387cac5675d166b62f6cfe444bd81b` |

Root가 실행한 `var/phase5x-staged-v1-regression.log`의 **314 tests/skip0/16.945s/OK**를 읽어 확인했다.
독립 검토자는 이 전체 suite를 중복 실행하지 않고 위 CPU/fault/wire 검증을 수행했다.
실제 semantic 비교는 별도 freeze 후 같은 exposed120개와 그대로 유지한 gate로 해야 한다.
두 번의 모델 호출은 오류가 상관될 수 있고, 더 긴 지연과 새로운 실패 경로를 추가한다.
어떤 결과도 unseen v2 holdout의 대체 증거나 IFC 실행 승인으로 사용하지 않는다.
