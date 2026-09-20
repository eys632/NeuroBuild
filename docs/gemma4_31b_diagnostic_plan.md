# Gemma 4 31B QAT 다음 단회 진단 계획

사전 평가 상태: **runtime/자원 검증 PASS, 첫 품질 평가 준비**.
실제 고정 조건은 [candidate freeze](../evaluations/hardening_v1_exposed_native_gemma4_diagnostic_freeze.json)를 따른다.
Qwen3.8의 보존125개 진단과 V2 실패를 반복하지 않고 다른 공식 모델을 비교한다.
[후보 비교](next_model_candidate_comparison.md)와 [전체 자원 계획](gemma4_31b_resource_plan.md)을 따른다.

## 후보와 변경 범위

`google/gemma-4-31B-it-qat-q4_0-gguf@59dde24573e7e61570dba08b18a2e1fe246955ed`,
`gemma-4-31B_q4_0-it.gguf`, SHA `179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b`.
공식 QAT 모델이며 일반 IT weight와 동일하다는 뜻이 아니다. Exact 변환 source revision은 공개되지 않았다.
공개 QAT reference metadata와 실제 GGUF를 별도로 대조한다.
[Manifest](../runtime/models/gemma4-31b-qat-q4-0.json), [계보·한계](../runtime/models/gemma4-31b-qat-q4-0.provenance.json).

기존 CUDA11.8/SM80 llama.cpp f072 binary, shared guard, localhost transport를 재사용한다.
새 환경·패키지·시스템 변경은 필요하지 않다. Application/Domain/IFC 업무 코드와 gold/scorer/quote adapter는 유지한다.
Client에는 명시 `gemma4_nonthinking_llama_cpp` profile을 추가하고 evaluator는 정확한 모델 ID/Q4_0 조합만 받는다.
기존 Qwen/vLLM profile을 Gemma에 자동으로 대입하지 않는다.

공식 권고 temperature1.0/top_p0.95/top_k64를 사용한다. 프로젝트 실험 선택으로 min_p0,
presence0/frequency0/repeat_penalty1/repeat_last_n0/seed42와 sampler 순서 temperature,top_k,top_p,min_p를 명시한다.
추가값까지 Google 권고라고 주장하지 않는다. Non-thinking template의 빈 thought channel과 native JSON fence는
고정 native parser가 처리해야 한다. 애플리케이션은 JSON을 고치거나 fence를 벗겨 재시도하지 않는다.
Final content에 Gemma thought/channel marker가 남으면 실패시키고 reasoning은 저장하지 않는다.

## 모델별 필요한 검증

1. 고정 GGUF의 전체 SHA/header/tensor coverage·shape/type, 실제 embedded template/tokenizer를 확인한다.
   원래 Qwen tokenizer·tensor 증거를 Gemma 검증으로 표시하지 않는다.
2. 기존 CPU static library로 새 모델의 template/grammar/sampler/final-content 분리를 검증한다.
   공개 synthetic 정상·거절 예제와 실제 vocab 원문 왕복/공식 reference/입력+completion context를 확인한다.
   이전125개 응답 재생이나 완료된 runtime 전체 검사는 수행하지 않는다.
3. 자원 계획의 header 조건을 충족하고 fresh GPU3 여유·utilization과28,672MiB+안전 margin이 맞을 때만 기동한다.
   새 모델의 startup·최대 context 추론 자원은 미검증이므로 한 번의 제한 probe가 필요하다.
   기존 binary/driver/guard 자체의 완료 검증은 재사용한다. 다른 GPU/offload/OOM 후 fallback은 없다.
4. 새 코드의 회귀, runtime 계약과 모델별 자원 검증이 모두 통과한 뒤 실제 epoch/proofs/조건을 freeze하고
   commit/push·첫 호출 전 identity를 확인한다. 이 문서는 그 실행 승인이 완료됐다는 증거가 아니다.

## 단회 품질 판단

Gemma epoch1에서 startup·공개 요청1건·최대 context 자원 probe1건을 통과했다.
공개 요청5.709초, 자원 probe25.059초, aggregate 증가 최대18,864MiB/최소 free17,510MiB다.
공식 tokenizer 공개20개 native ID/원문 roundtrip20/20, 최대 입력2646+출력768=3414 token을 확인했다.
원래BOS/props template 표현 검사 실패와 별도 literalU+2581 roundtrip 실패는 보존했다.
단회 품질 평가에서는 같은 guard epoch를 사용하고 완료된 계약·자원 검사는 반복하지 않는다.

첫 진단은 기존 **exposed120개×1+warmup5**다. Generation2.0 single, promptv2/branch schema,
output768/timeout120/ctx4096/sequence1을 유지한다. Schema120/120, semantic≥114/120,
raw READY FP0/58, unsafe accepted READY0/120, raw decision 관측120/120을 모두 요구한다.
Timeout/잘림/파싱 실패/unknown은 분모에서 제외하지 않는다. Warmup은 따로 기록한다.

명백한 실패이면 반복하지 않고 결과·서버 종료·VRAM 반환 증거를 남겨 다른 후보와 비교한다.
통과/경계선일 때만 미확정 사실을 해결할 최소 검증을 판단한다. 동일 전체3회 반복은 계획하지 않는다.
저장 응답의 CPU 재생은 집계 검증이며 모델 출력 재생성과 구분한다.

기존 V2도 이제 출력 노출 자료다. 그80개에서 후속 성능이 좋아져도 새 unseen 성공이라고 하지 않는다.
1차 gate를 통과한 후보의 새 일반화 확인은 별도로 사전 고정한 미사용 자료를 사용해야 하며,
현재 모델의1차 진단 통과 전 그 추가 품질 평가를 시작하지 않는다.
Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED, RTX5090은 PREDICTED_UNVERIFIED다.
비필수 batch/flash/graph/throughput 최적화는 future optimization으로 둔다.
