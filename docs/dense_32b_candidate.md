# 공식 32B AWQ 단일 호출 비교 계획

2026-09-20. **다운로드 전 계획 / A100 실행·품질 미검증 / RTX5090 PREDICTED_UNVERIFIED**.

14B의 generation2 단일 호출은 노출된120개에서 의미113/120, raw READY 오판2/58,
unsafe3/120이었다. 분류와 추출을 나눈 후보는93/120, raw11/58, unsafe6/120으로
실패했다. 분리 구조를 채택하지 않고 기존 단일 호출의 모델만 바꾸는 비교를 수행한다.
Canonical parser, quote adapter, promptv2, branch schema, greedy sampling, gold와 gate를
유지한다. 분리 실험에서는 prompt/schema도 바뀌었으므로 구조만의 효과라고 단정하지 않는다.

후보는 [공식 Qwen/Qwen3-32B-AWQ](https://huggingface.co/Qwen/Qwen3-32B-AWQ/tree/0499c3ac83fdef8810b907a23894ba91e95eddd8),
revision `0499c3ac83fdef8810b907a23894ba91e95eddd8`다. Apache-2.0 LICENSE 원문을
[보존](../runtime/licenses/qwen3-32b-awq.LICENSE)한다. Dense Qwen3ForCausalLM,
AWQ4/group128/zero point이며 설치된 vLLM0.8.5의 Qwen3/SM80 Marlin 정적 조건을
충족한다. 실제 tensor/header와 기동 검증은 다운로드 후 별도로 수행한다.

[고정 manifest](../runtime/models/qwen3-32b-awq.json)는13파일19,341,523,989bytes
(18.0132GiB), SHA256 `fbb3d1c98f3ceeeceb2fd5306dde9439d1be12516dd5054c0b2f5a299a260e03`다.
Weight4개 합계19,325,481,744bytes다. Index의 metadata.total_size는 실제 shard 크기와
다르므로 다운로드 예산에는 공식 LFS의 실제 파일 크기를 사용한다. 전체 다운로드는
각 파일 SHA/size 검증과20GiB reserve를 적용한다.

| GPU3 실행 계획 | 값 |
|---|---:|
| 관측 free / utilization | 36,373MiB / 0% |
| 전체 startup/inference peak 계획 | 25,600MiB |
| 추가 peak allowance | 0MiB |
| 안전 margin | 7,275MiB |
| 계획 peak와 margin을 뺀 잔여 | 3,498MiB |
| vLLM / Torch fraction | 0.60 / 0.60 |
| Context / sequence / FP16 KV | 4096 / 1 / 1,024MiB |

이 수치는 실측 peak나 hard isolation 보장이 아니다. Torch fraction은 CUDA가 보고하는
총량에 적용되며 non-Torch allocation까지 제한하지 않는다. 전체25GiB 계획에는
weight/KV/prefill/repack/non-Torch/fragmentation과 보수적 여유를 포함한다.
`--peak-allowance-mib 0`으로 감시 중 baseline 대비 aggregate 증가가25GiB를 넘거나
free margin이 깨지면 자신의 모델 process group만 종료한다. 다른 process의 변화도
aggregate 측정에 포함되며, 관측 사이 순간 peak를 완벽하게 차단하는 장치로 해석하지 않는다.
기동 직전 GPU3에서5회 측정하고 기존 안정성/utilization 조건도 다시 적용한다.
TP1, FP16, eager, awq_marlin, context4096, sequence1, KV256 blocks, CPU offload0,
swap0, loopback endpoint를 사용한다. GPU0/1/2 fallback은 없다.

다운로드 전 usable disk48,954,236,928bytes에서18.0132GiB를 받으면 약27.58GiB가
남는 계획이다. 이전4B의 검증된 inactive weight3개만 정리했으며
[정리 기록](../evaluations/results/phase5x/unused_4b_weight_cache_cleanup.json)을 보존했다.
환경/패키지 추가 설치는 없다. 기존 backend와 GPU 환경을 분리해서 사용한다.

실제 파일 검증 → CPU tokenizer/template/xgrammar/context 검증 → fresh GPU3 preflight →
자체 guarded server 기동/loopback 검증 → 후보 동결/commit/push → exposed120×1 진단
순서다. Schema120/120, 의미≥114/120, raw FP0/58, unsafe0/120을 모두 충족해야
120×3 정식 회귀와 v2 holdout 평가로 진행한다. 실패 출력과 오류도 분모에 보존한다.

V2는 모델 출력 미노출 상태지만 root가 일부 입력/gold를 본
[사건](../evaluations/hardening_v2_input_exposure_addendum.json)이 있다. 이번 비교는 그
사건 뒤 모델을 바꾸므로 완전 맹검으로 주장하지 않는다. 사용하는 prompt는 v2 작성 전부터
고정됐으며 사건 뒤 source/prompt/gold 수정은 없다. 향후 holdout 결과는 이 한계를 함께 보고한다.

RTX5090은 같은25GiB 계획에20% free margin을 적용하려면 최소32,000MiB free가
필요하다. SM120을 지원하는 별도 runtime의 실제 memory/quality/compatibility 측정은
아직 없으며, A100 runtime fraction을 그대로 복사해 적합성을 주장하지 않는다.
공통 Application 코드는 유지한다.

세부 산정과 출처는 [사전 메모리 계획](../evaluations/results/phase5x/32b-predownload/predownload_memory_plan.json),
[정적 검토](../evaluations/results/phase5x/32b-predownload/static_feasibility.json),
[독립 검토](reviews/phase5x_32b_predownload_review.md)에 보존한다.
