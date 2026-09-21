# Native Qwen3.8 후속 정식 평가 사전 계획

상태: **SUPERSEDED BEFORE EVALUATION — 사용자 checkpoint 지시로 실행하지 않은 과거 계획**.

2026-09-20 최신 지시와 D036이 아래 자동120×3·V2×3 계획을 대체한다. 현재 단회 진단은1차 gate를
통과했고 동일120개 추가 반복0회로 판단했다. 다음 계획은 checkpoint 뒤 V2 80×1+warmup5의 별도 사전 동결이다.
아래 내용은 준비 경위 보존용이며 실행 지시나 현행 필수 gate가 아니다.

과거 계획 상태: **NOT_RUN — 조건부 계획**. Exposed120×1 진단의 결과를 가정하지 않는다.
이 문서는 정식 exposed120×3 또는 V2 평가를 실행했다는 증거가 아니며 후보 채택이나
Phase5.x 완료를 선언하지 않는다. [단회 진단 계획](native_qwen38_quality_diagnostic_plan.md),
[D024의 반복·동결 원칙](DECISIONS.md), [V2 데이터 계획](hardening_v2_dataset.md)을 연결한다.

## 순서와 진입 조건

1. 현재 native exposed120×1+warmup5를 완료하고 원본 결과·manifest·실행 증거를 보존한다.
   독립 재생에서 schema120/120, semantic≥114/120, raw READY FP0/58,
   unsafe accepted READY0/120 및 정식120개 모두의 raw decision 관측을 확인해야 한다.
   실패하거나 미완료이면 아래 두 평가를 시작하지 않고 실패를 보존·검토한다.
2. 진단을 통과한 동일 후보를 별도로 동결·commit·push한 뒤 **exposed120×3**을 실행한다.
   완료 후 전체 trial과 warmup을 독립 재생하고 아래 정식 gate를 확인한다.
3. 정식 exposed gate까지 통과한 경우에만 후보 선택 근거와 **V2 80×3** 조건을 별도
   동결·commit·push한다. **V2 첫 warmup부터 245호출 계획으로 진입**한다.
   V2 일부 미리보기, 단회80개 진단, warmup 피드백을 이용한 설정 변경은 하지 않는다.

단계별 freeze와 실제 manifest는 서로 연결하되 이전 파일을 덮어쓰지 않는다.
정식 exposed 또는 V2 결과를 다른 실행의 성공 응답과 합쳐 gate를 만들지 않는다.

## 자료·순서·분모

| 항목 | 정식 exposed | 첫 V2 평가 |
|---|---:|---:|
| 자료 | 기존 노출120개 | 모델 출력 미관측80개 |
| Manifest split | `development` | `heldout` |
| Case당 반복 | 3 | 3 |
| 정식 trial / 별도 warmup | 360 / 5 | 240 / 5 |
| 총 모델 HTTP 호출 | **365** | **245** |
| Gold READY / non-READY trial | **186 / 174** | **120 / 120** |
| Schema gate | **360/360** | **240/240** |
| Semantic gate | **342/360 이상** | **228/240 이상** |
| Raw READY FP gate | **0/174** | **0/120** |
| Unsafe accepted READY gate | **0/360** | **0/240** |
| READY의 잘못된 이동 / FN 분모 | 각각186 | 각각120 |

Exposed는 `requirement_hardening_v1_exposed_regression.jsonl`의 기존 순서120개,
V2는 `requirement_hardening_v2_holdout.jsonl`의 기존 순서80개를 사용한다.
각 run의 dataset 앞5개가 warmup이며 정식 품질·latency 분모에서 제외한다.
정식 순서는 **case-major, 각 case의 trial1→2→3**다. 요청마다 seed42를 유지한다.
V2는 READY40/CLARIFICATION20/UNSUPPORTED20개이므로 정식 trial은120/60/60이다.
옛 V1 holdout의 non-READY114/READY126 분모를 V2에 재사용하지 않는다.
같은 seed의 반복은 독립 표본이 아니며 run 간 정확도를 합산하지 않는다.

## 유지할 후보와 동결 증거

단회 진단과 동일한 `qwen38-gguf-raw-unicode-v1`을 사용한다. 모델은
`ggml-org/Qwen3.8-27B-GGUF` revision `efbb3b1f70a21d97fd4495240648405f7228554f`의
Q4_K_M, llama.cpp commit `f072b103714dfa1eee531f80b24512faf38e3dd2`다.
GPU3/internalCUDA0, context4096/sequence1, batch64/ubatch64, F16 KV,
flash/graphs/fit OFF, rollback0을 유지한다. 다른 GPU·batch·runtime으로 자동 전환하지 않는다.

Pipeline은 single generation2.0, 기존 `requirement_generation_v2_v2` prompt와
decision-branch schema, 기존 quote adapter→canonical parser→scorer다.
Native `llama_cpp_json_schema`/GBNF와 `qwen38_nonthinking_llama_cpp` profile을 명시한다.
T0.7/P0.8/K20/minP0/seed42/presence0/frequency0/repeat1/window0,
samplers temperature→top_k→top_p→min_p, thinkingfalse/deepseek,
completion768/timeout120초/concurrency1/자동 retry0을 그대로 기록한다.
CLI의 legacy 기본값에 의존하지 않으며 input/output 정규화·quote 보정은 없다.

각 첫 요청 전에 dataset/reference 및 기존 dataset-only freeze, source·client·adapter·parser·
scorer·schema·prompt, GGUF/embedded tokenizer/template, native build/binary/shared libraries,
launch 설정과 실제 epoch의 startup/listener/resource/공개 smoke 증거를 hash로 연결한다.
현재 native wire/CPU grammar/context 증거의 source/template/prompt 일치를 확인한다.
V2 길이검사 결과만을 추론 성공으로 해석하지 않는다. 파일이 바뀌면 기존 증거를 무조건
승계하지 않고 영향 검토·필요 검증과 새 동결을 먼저 수행한다.
실제 요청 전 clean checkpoint의 commit/push/remote 일치를 확인하고 각 manifest에 남긴다.

## 실행 시간과 GPU3 자원

[자원 계획](native_qwen38_resource_plan.md)의 전체 예상28,672MiB와 추가 free margin,
own process 감시·종료 조건은 유지한다. 공유 GPU 전체 관측을 per-process hard cap이라 부르지 않는다.
실행 전후 own PID/startticks/argv/loopback과 frozen epoch를 대조한다.

현재 guard의 `max_seconds=10800`은 **child spawn 이후 경과 한도**이며 run마다 새로 주어지는 시간이 아니다.
보고서의 `elapsed_seconds`를 기준으로 남은 시간을 계산한다. `started_at_utc`에는 기동 전 검사 시간도 포함된다.
각 freeze에 총 호출365 또는245, 직전 완료 진단의 mean/p95와 최대 문맥 probe를 근거로 한
보수적인 요청 시간 예산, tail·기록·자체 종료 여유, guard 경과/잔여 시간을 명시한다.
필요 시간은 `총 호출 수 × 계획 요청 시간 + 여유`로 산정하고 잔여 시간보다 작아야 한다.
Timeout120초를 모든 요청의 실제 시간으로 가정하지 않으며 이 계획이 완료를 보장한다고도 하지 않는다.
오류나 지연으로 deadline에 닿으면 guard 종료와 INCOMPLETE 규칙을 적용한다.

현재 최대 문맥 실측25.678초를365회에 적용하면9372.52초이며 tail·검증 여유가 필요하다.
진단 통과 후 formal은 새 epoch의 `max_seconds=14400`을 사전 계획한다. 보수적인 운영 가정은
365×30초+900초=11850초다.30초는 실측 probe보다 크지만 grammar·공유 부하를 포함한 엄밀 상한은 아니다.
기존 코드의 최대43200초 범위 안이며 추론 설정·VRAM 예산을 변경하지 않는다. 모든 호출이 timeout120초에
도달하면43800초로 최대 lifetime도 넘으므로 완료 보장을 주장하지 않는다. V2는 별도 epoch 또는
그 시점의 남은 시간을 다시 심사하며245×30초+900초=8250초를 초기 계획 기준으로 삼는다.

잔여 시간이 부족하거나 epoch가 바뀌어야 하면 기존 own 서버를 안전하게 정리하고 동일 후보의
새 epoch를 사용한다. 새 fresh GPU3 사전 검사·startup/listener·공개 smoke/resource 검증을
수행하고 새 runtime metadata를 해당 단계의 freeze에 묶는다. 실행 중 guard 한도나 후보 설정을
늘리지 않으며 타인 process 또는 다른 GPU를 변경하지 않는다.

## 결과 판정과 한계

Raw READY는 generation schema/adapter/parser 거절 전에 계수한다. Accepted FP와 gold READY의
잘못된 target/XY를 합한 unsafe 지표도 별도로 유지한다. Timeout·truncation·schema/parser 실패와
unknown은 전체 정식 분모에 남긴다. Raw decision은 정식360/360 또는240/240 모두 관측되어야
PASS를 선언할 수 있다. 미관측을 안전한 non-READY나 FP0의 증거로 바꾸지 않는다.

중단되면 계획/완료/미완료 수와 원인을 기록하고 **INCOMPLETE, gate 미통과**로 둔다.
기술적 재실행은 사유와 이전 증거를 보존한 별도 전체 run이며 성공 응답만 재사용하지 않는다.
완료 결과는 원본 보존 후 전체 stage·SI·semantic·집계·분모를 독립 재생한다.
Category별 오류, case별3회 일관성, raw 관측률, FN, latency mean/p95, token·자원·오류 정보를
함께 보고한다. 새 사후 threshold를 만들거나 raw reasoning/chain-of-thought를 저장하지 않는다.

V2는 모델 출력 미관측 자료이지만 root의 일부 입력/gold 노출 이력은
[기존 addendum](../evaluations/hardening_v2_input_exposure_addendum.json)에 유지한다.
완전 맹검이나 사람 검수라고 부르지 않는다. Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다.
V2 출력을 보고 조정하면 이 자료도 이후 regression/development이며 새 unseen 통과로 표시하지 않는다.
공식 HF tokenizer ID19/20 FAIL과 별도 raw reference/roundtrip20/20을 모두 보존한다.
두 gate 통과는 이 고정 A100 synthetic 조합의 내부 후보 채택 근거이며 실제 IFC 승인·불변성,
후속 Phase, 사람 검수 또는 외부 pilot을 대신하지 않는다. RTX5090은 **PREDICTED_UNVERIFIED**다.
