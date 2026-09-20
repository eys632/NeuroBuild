# Gemma4-31B QAT 모델별 사전 검증

2026-09-20. **CPU·startup·자원 검증 PASS — 품질 미평가·미채택.**
Qwen3.8의 단회 PASS와 V2 FAIL을 보존한 뒤 다른 공식 모델을 비교한다.
이전125개 진단과 독립 재생은 반복하지 않았다. Phase5.x는 아직 미완료다.

후보는 `google/gemma-4-31B-it-qat-q4_0-gguf`의 revision
`59dde24573e7e61570dba08b18a2e1fe246955ed`다. 기존 CUDA11.8/SM80
llama.cpp `f072b103714dfa1eee531f80b24512faf38e3dd2` binary를 재사용한다.
새 패키지·환경·driver 설치는 없다. [후보 비교](../next_model_candidate_comparison.md),
[자원 계획](../gemma4_31b_resource_plan.md), [단회 진단 계획](../gemma4_31b_diagnostic_plan.md).

## 현재 증거와 실패 보존

| 항목 | 결과 |
| --- | --- |
| 다운로드 | 공식 README/GGUF 2개 size/SHA 확인; 최소 disk free28,231,639,040B |
| 실제 GGUF | 17,651,001,568B; 전체 SHA `179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b` |
| Header v2 | PASS; 833 tensor 이름·shape, 공식 vocab/merges/template 일치 |
| Header 첫 실패 | Q6_K embedding 미허용; 후속 진단에서 정수 배열의 I32 wire type도 확인 |
| 새 profile 회귀 | 실제 PostgreSQL/IfcOpenShell/headless 395 PASS, skip0, 19.339초 |
| 공개 template CPU 검사 | 유효 JSON10/거절20, fence 오류4, 합성 thought 분리1 PASS |
| 첫 vocab CPU 검사 | FAIL; model-aware BOS 처리 차이로 raw prompt equality 실패 |
| 실제 tokenizer/context | 공개20 ID/원문 roundtrip20/20, native grammar/EOG PASS; 입력200개 길이 확인 |
| GPU startup | PASS, localhost/own PID/시작시각/실행 인자/CPU·모델·runtime 증거 연결 |
| 공개 실제 요청 | 1회 PASS, HTTP end-to-end5.709282초 |
| 최대 context 자원 | 3328 prefill+768 decode/4095 cache PASS,25.059090초 |
| 첫 품질 진단 | NOT_RUN; 노출120×1+warmup5 동결 준비 |

Header v1은 파일명의 Q4_0를 embedding에도 허용 가능한 type으로 적용했으나 실제 파일은
F32 422개/Q4_0 410개/Q6_K embedding1개다. 고정 ggml source가 Q6_K block과 CUDA
dispatch를 지원한다. KV head 값60개는 예상과 같고 고정 writer가 이를 I32 배열로 기록한다.
V1 및 실패 receipt를 보존한 별도 v2에서 이 두 representation을 정확히 검사했다.
23개 CPU 검증이 통과했고 generic parser 8개 함수는 그대로다. 실제 전체 hash/header PASS는
`d867a3300b2a93534fb1b480e8e42b30321c894aaec05b5729a529e848817756`이다.

첫 vocab 검사는 embedded template bytes 일치 후 prompt 비교에서 실패했다.
고정 native source는 `add_bos=true`인 모델에서 template 선두 `<bos>`를 제거하고
tokenizer에 시작 토큰 추가를 맡긴다. Metadata만 사용한 template 렌더링에는 이 flag가 없다.
수정 검사는 정확한 단일 BOS 차이와 최종 token ID 배열의 일치를 함께 요구한다.
Grammar와 generation prompt의 byte 일치는 유지하며 application 입력·출력을 고치지 않는다.
이는 모델 품질 오류를 재시도로 감추는 작업이 아니라 첫 모델별 CPU 계약 검사의 수정이다.

수정된 native CPU 검사에서 공식 공개20개 token ID와 원문 복원이 모두 일치했다.
JSON10개 수락/20개 거절/EOG 검증, 실제 embedded template bytes와 grammar/generation prompt도 일치했다.
입력 길이는 exposed120이2339–2646, V2 길이80이2360–2593 token이다.
출력 예산768을 더한 최대값은 각각3414/3361로 context4096 이내다.
Model-aware native template/tokenizer로 측정했으며 context/backend/tensor 추론을 만들지 않았다.
Final CPU proof SHA는 `a27cd1f7a37899873aac346404e1cea8d0805c8db899f03eba6e3d7d7340029d`다.

첫 startup의 `PROPS_MISMATCH`도 보존했다. `/props`가 보고한 template은 원본의 마지막LF를
정확히1개 제거한18,682B이며 pinned Jinja lexer의 동작과 일치한다. 원본 GGUF18,683B 해시
ae5346…와 props 표시 해시6a1015…를 별도로 검증한 후 같은 서버에서 startup을 통과했다.
서버 재시작이나 prompt/schema/application 변경은 없었다.

## 자원과 채택 조건

Header의 실제 크기·shape를 반영해도 전체 예상 peak28,672MiB는 유지된다.
기동 전 GPU3의5표본은 free36,373MiB/util0%이고 안전 여유7,275MiB를 제외한 예산은29,098MiB였다.
Root가 같은 guard로 제한된 startup·공개 요청1회·자원 probe1회를 완료했다.
이 시점까지 aggregate 증가 최대18,864MiB/최소 free17,510MiB로 예산과 floor를 유지했다.
Process별 peak나 전체 epoch 종료 시점의 최종 peak, 모든 입력의 hard cap은 아니다.
기존 binary/driver/guard 검증은 재사용하며 GPU0/1/2 fallback은 없다.

증거: [CPU 보관본](../../evaluations/results/phase5x/gemma4-cpu-preflight/README.md),
[startup](../../evaluations/results/phase5x/gemma4-native-startup-epoch1/startup.json),
[공개 요청](../../evaluations/results/phase5x/gemma4-native-public-smoke-epoch1/report.json),
[자원 probe](../../evaluations/results/phase5x/gemma4-native-resource-epoch1/report.json).

공식 tokenizer의 공개20개 원문 roundtrip은 PASS였으나 literal U+2581은 공식 tokenizer
자체에서 ASCII space로 복원된다. 별도 실패 witness를 보존하며 모든 Unicode 보존을 주장하지 않는다.
실제 native에서도 해당 공개 witness의 ID는 공식 결과와 같았으나 원문 roundtrip은 실패했다.
별도 witness SHA `bbb9ed28cdae06bb07a3f66949c2e23e59728324f74440be82b567f0a8662e73`를
전체20개 PASS와 함께 보존한다. 입력·출력 보정이나 새 reference variant는 만들지 않았다.
GGUF의 정확한 변환 base revision도
공개되지 않았으므로 공식 QAT metadata와의 일치를 정확한 변환 계보 증명으로 표시하지 않는다.

첫 품질 평가는 계약·자원 검증과 조건 동결 후 exposed120×1+warmup5로만 계획한다.
1차 gate 미달이면 반복하지 않는다. 기존 V2는 이미 노출 자료이며 새 unseen 성능으로 쓰지 않는다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**, RTX5090은 **PREDICTED_UNVERIFIED**다.
비필수 runtime 최적화는 future optimization으로 남긴다.

Root 검토와 독립 소스 검토를 통과했다. Saved-response 재생의 핵심3함수는 기존 검증본과
AST가 같으며, 새 모델 ID/sampling/CPU/header/runtime/동일 epoch 연결만 추가했다.
Metadata 변조28개 거절 검증도 통과했다. 기존125개 결과나 이번 후보의 품질 결과를 읽는 검사는 아니다.
Application/Domain/IFC 및 기존395개 회귀 대상 source는 변경되지 않았다.
기동은 own UID/시작시각/실행 인자/loopback 연결·guard 예산으로 제한하며 다른 사용자에게 신호를 보내지 않았다.
