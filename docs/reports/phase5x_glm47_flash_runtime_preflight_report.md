# GLM-4.7-Flash GPU3 최초 실행

2026-09-20. 새 GLM 후보의 startup·공개 입력1건·최대 문맥 자원 검사1건은 PASS다.
품질 평가 호출은 아직0이며 Phase5.x 미완료·모델 미채택·Phase6 미시작이다.
완료한 이전 모델 검사와 평가·독립 재생은 반복하지 않았다.

[실제 CPU 결과](phase5x_glm47_flash_native_cpu_report.md)의 저장된 hash5개와 source5개만
연결한 aggregate `54ab0062c5d22112ed3349e0021391a4dd17f6d5f8698ac8a02cc096b08a1847`를 사용했다.
연결 과정에서 모델 파일·dataset·native 실행을 다시 열지 않았다.
공식 tokenizer20/20, 원본 template, neutral sampling, 최대4025/4096 문맥이 같은 variant에 연결된다.
Runtime consumer의 새 CPU controls6개는0.028초 PASS였다. 이후 정확한 aggregate pin으로
readiness를 허용하는 변경에 해당 경계1개만0.001초 재검증했다. 나머지 검사·416 production regression은 반복하지 않았다.

## 고정 실행과 자원 판단

Variant `glm47-flash-gguf-nonthinking-v1`, config
`4824463fcabca13c2eaa07a9774c324b7980a2383915868f4f493b149dc245c4`,
collector `4399c90d32e0e472455bae5e907c8a479fdac550fed46978d8001c6d894d69ea`다.
PhysicalGPU3/logicalCUDA0/TP1/loopback8003/ctx4096/seq1/batch64/ubatch64/F16KV/flashOFF/graphsOFF,
원본 template/no override, reasoning off, guard 최대7200초를 사용한다.

실행 직전5회 모두 free36,373MiB/used3,965MiB/util0%였다.
안전 margin7,275MiB를 뺀29,098MiB 예산에 예상 whole peak28,672MiB가 들어갔다.
가중치/KV/workspace/driver/loading 여유를 포함한 공학적 추정이며 하드 할당 상한이나 GPU 격리는 아니다.
타인 프로세스의 존재만으로 중단하지 않고 aggregate 여유 감소를 감시해 자신의 서버만 종료한다.

Guard3646979/startticks479057809, native child3647152/startticks479062142,
guard 기록 시작12:23:14.135579 UTC다. Own UID/exe/argv/parent/startticks를 확인하고
identity receipt `7ef9e56d1e794ff44531a7565aaae215f2cdaabe42c8b7d14c457706ebff5833`로 보존했다.
타인 process 내용 접근·신호 및 GPU0/1/2 사용은 없다.

## 실제 관측

| 검사 | 결과 |
|---|---|
| Startup | own process/listener/model/header/source/CPU 연결, health/models/props GET3 PASS |
| Template | 실제 embedded·props 모두 원본3120B/SHA d63ad536…281375와 일치 |
| 공개 입력 | production client1 POST, READY·대상·XY 이동 해석 PASS, 5.146885855초 |
| 자원 경계 | uncached3328+sampled768, cached4095, limit 종료 PASS, 17.257125599초 |
| Epoch aggregate 증가 최대 | 17,960MiB |
| 최소 관측 free | 18,414MiB, 안전 floor7,275MiB 유지 |
| 품질 평가 | 0회, 사전동결·push 후 첫120×1+warmup5 예정 |

Resource의 truncated=true는4096 경계에서 limit까지 생성한 의도된 자원 검사 결과다.
품질 응답의 잘림 PASS로 해석하지 않는다. 공개/resource 응답 본문은 저장하지 않았다.
수치는 epoch 전체 aggregate 변화이며 이 POST만의 VRAM이나 process별 peak가 아니다.
종료 후 최종 관측값과 VRAM 반환을 별도로 보존한다.

Native 기본 empty-run startup warmup은 켜져 있다. Source의 기본값과 launch argv로 확인한 것이며
실제 decode counter 측정은 아니다. Startup의 model_inference_calls0은 명시적 HTTP 생성0회라는 범위다.
이는 이후 평가 warmup5와 별개이며 품질 호출 수/분모에 포함하지 않는다.

실제 [startup 보관본](../../evaluations/results/phase5x/glm47-flash-native-startup-epoch1/startup.json),
[공개 입력](../../evaluations/results/phase5x/glm47-flash-native-public-smoke-epoch1/report.json),
[자원 경계](../../evaluations/results/phase5x/glm47-flash-native-resource-epoch1/report.json)를 보존한다.
SHA는 각각 `2a19dde7fd90416638137a370cf68ed0b08ce66d7be277c32a4bbba27b10aaa0`,
`0b68dc9e0fad949f0bfac740354bb5ec89b7405f5634ccc1224392f5ad035b26`,
`a4a4ce4a0e5615704cc4fdf9ff391d1ad4ca90dbfacc8dd5e1d0a55b1d35b68b`다.

[독립 검토](../../evaluations/results/phase5x/glm47-flash-runtime-review/glm47-live-evidence-independent-review.json)는
저장된27개 hash/AST 연결을 확인했고 material finding0이었다. 검사·모델·GPU를 다시 실행하지 않았다.
공개/resource 단계의 전후 live guard는 hash로 연결했으며 원본 snapshot 전체를 별도로 보관하지 않은 한계도 기록했다.

[진단 계획](../glm47_flash_diagnostic_plan.md)에 따라 첫 gate 명백한 미달 시 같은 후보 반복·V2를 하지 않는다.
미사용80개는 아직 접근하지 않았다. RTX5090은 PREDICTED_UNVERIFIED이며 현재 A100 자원 계획을
32GiB RTX5090에서 검증된 설정이라고 주장하지 않는다. 비필수 runtime 최적화는 future optimization이다.
