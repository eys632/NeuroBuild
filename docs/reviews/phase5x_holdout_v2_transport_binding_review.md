# Holdout v2: 실제 staged transport와 CPU context 대조

**Payload/context 검증 PASS. 모델 추론·품질 평가와 grammar/native kernel 검증은 수행하지 않았다.**

최종 `LocalStagedRequirementClient.complete_staged()`의 두 실제 transport에 메모리 fake opener를
주입했다. 새 holdout80개 각각에 READY/CLARIFICATION/UNSUPPORTED를 모두 통과시키는240회 경로,
총480개 가짜 HTTP request를 캡처했다. Classifier의 서로 다른 request는80개, extractor는
80개×3decision=240개다. 고정된 schema 모양의 가짜 응답은 gold와 무관하며 점수에 사용하거나
저장하지 않았다. Socket 생성을 차단했고 실제 HTTP server/model에 연결하지 않았다.

모든 request body의 UTF-8 bytes가 수동 구성한 기대 payload와 정확히 일치했다. 전체 원문과
axis_convention은 변하지 않았고, classifier에는 classified_decision이 없으며 extractor의
user field와 bound schema는 같은 decision을 가리켰다. 기본 JSON 공백, key 순서, system prompt,
T0/seed42, 출력128/768, thinking=false, legacy guided_json/xgrammar:no-fallback을 대조했다.
모델명은 실제 서버와 구분되는 `transport-binding-fixture`를 사용했다.

| 실제 캡처 messages / 14B tokenizer | 최대 입력 | 출력 예산 | 합계 / context4096 |
|---|---:|---:|---:|
| Classification | 1125 | 128 | 1253 |
| Extraction (세 decision 전체) | 1192 | 768 | 1960 |

Tokenizer/template metadata는 기존 고정 manifest와 일치했고 Transformers4.51.3의
apply_chat_template(add_generation_prompt=True, enable_thinking=False)로 캡처 messages를 계산했다.
이전 published CPU context proof의 최대 입력값과 동일하다. GPU mask, Torch 미import,
network/model/GPU call0회, weight 읽기0회를 유지했다. 원문·gold·case별 결과는 root와 현재
후보 prompt 작성자에게 전달하지 않았으며 request/가짜 response 본문도 별도 보존하지 않았다.

| 검증한 최종 소스 | SHA-256 |
|---|---|
| `staged_requirement.py` | `7e79b1c488a00e3f81b443fb32f86019f510a274228f56058c4eeae66038efee` |
| `local_model.py` | `9732ad69f9f563f6acb3892ec0c187958d04d006a89251264779123445bc57c3` |
| Binding proof | `540e2a47ad5a38309e12ebb6e009d94212f4651ac4e23e18701cc7f1aa91d2c1` |

검증 전후 source/prompt/schema hash가 같았으며 기존 dataset freeze와 그9개 artifact hash는
모두 그대로다. 이전 proof나 freeze를 갱신하지 않고 [새 binding 증거](../../evaluations/results/phase5x/holdout-v2-preflight/staged_transport_binding.json)와
[검증 script](../../evaluations/results/phase5x/holdout-v2-preflight/verify_staged_transport_binding.py)를 추가했다.
Script는 기존 결과를 덮어쓰지 않으며 재검증을 보존할 때는 별도 출력 경로를 사용해야 한다.

이번 증거는 payload와 context 길이에 한정된다. Staged 실패 시 raw decision 보존, grammar 컴파일,
실제 runtime 및 품질 gate는 별도 검증이다. AI gold의 사람 미검수·절차적 분리 한계도 그대로다.
이후 source/prompt/schema/template가 바뀌면 실제 candidate freeze 전에 이 바인딩을 재확인해야 한다.
