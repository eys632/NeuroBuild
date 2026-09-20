# Phase 5.x native Qwen3.8 exposed 진단 독립 검토

**독립 replay PASS, 사전 고정한 exposed 진단 gate PASS다.** 본시험 120개 중 schema 120개, parser 119개, 의미 판정 117개(97.5%)가 통과했다. Raw READY false positive는 0/58, unsafe acceptance는 0/120이다. 이는 이미 노출된 synthetic regression의 1회 진단이며, 최종 모델 선정·미사용 holdout 통과·Phase 5.x 완료를 뜻하지 않는다.

원본과 실행 증거는 [진단 archive](../../evaluations/results/phase5x/exposed-native-qwen38-diagnostic/), 평가 조건은 [freeze](../../evaluations/results/phase5x/exposed-native-qwen38-diagnostic/freeze.json), 결과는 [results.json](../../evaluations/results/phase5x/exposed-native-qwen38-diagnostic/results.json)에 보존한다. Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다.

## 고정 조건과 재생 범위

- Run: `20260920T071218Z-d9e611b184ea4f8cbb0d7369982ef361`.
- 실제 clean checkpoint: `bec9000e697c6b4930d077822ae30ca484a395ba`.
- Freeze SHA256: `7a1f67bd71c65f0c2d2aacc2b03cb765d7c38ac8eaa31bf7618847c4a5380fd9`.
- Model: `ggml-org/Qwen3.8-27B-GGUF`, revision `efbb3b1f70a21d97fd4495240648405f7228554f`, Q4_K_M.
- Runtime variant: `qwen38-gguf-raw-unicode-v1`; llama.cpp source `f072b103714dfa1eee531f80b24512faf38e3dd2`; A100 physical GPU3 → logical CUDA0, context4096, sequence1, logical batch64 / physical ubatch64, F16 KV, flash attention off.
- Generation 2.0 → 기존 quote adapter → canonical 1.0 parser. Prompt `requirement_generation_v2_v2.txt`, decision-branch schema, parser, gold, 의미 rubric은 freeze의 원본 SHA로 검증했다.
- Native `response_format.json_schema` / GBNF, non-thinking, deepseek final-content splitter, 출력 최대768, timeout120초, 요청당 1회. Temperature0.7 / top-p0.8 / top-k20 / min-p0 / seed42, presence0 / frequency0 / repeat1 / repeat window0, sampler 순서 temperature → top-k → top-p → min-p다. Native 전용 실험 recipe이며 공식 model card의 presence1.5를 그대로 따랐다고 표현하지 않는다.

검토자는 고정 commit에서 `git show`로 만든 28개 파일 snapshot을 사용했다. Manifest/model revision/quant/embedded tokenizer/template, source·runtime·launch·GGUF header hash, 동일 startup epoch 및 loopback 증거, 공식 HF 비교 실패와 raw reference, CPU context 길이 검증, 사전 resource probe를 결과 본문보다 먼저 확인했다. Native binary나 모델을 다시 실행하거나 weight를 다시 읽지 않았다.

저장된 본시험120개와 별도 warmup5개 **모두** schema-valid final generation JSON이 남아 있어 2→1 projection, canonical parser, metre 정규화, frozen `evaluate_trial` 전체 행, `summarize` 전체 결과를 다시 계산했다. 원본과 정확히 일치했다. 미보존 응답과 unknown 결정은 이번 run에서 각각 0개이며, helper는 이들이 발생할 경우 전체 분모를 유지하고 재관측했다고 주장하지 않는다.

V2 자료는 이미 승인된 9개 파일의 SHA만 확인했다. V2 본문·gold를 파싱하거나 출력하지 않았고 V2 모델 결과를 읽지 않았다. 기존 input-exposure addendum은 유지되며 완전한 blind 평가라고 주장하지 않는다.

## 독립 집계

| 항목 | 본시험 결과 | 고정 기준 |
|---|---:|---:|
| Schema | 120/120 | 120/120 |
| Quote adapter / canonical schema / parser | 각 119/120 | 참고 지표 |
| 의미 rubric | 117/120, 97.5% | 114/120 이상 |
| Raw READY false positive | 0/58 | 0/58 |
| Accepted READY false positive | 0/58 | unsafe 지표에 포함 |
| Unsafe accepted READY | 0/120 | 0/120 |
| READY gold false negative | 0/62 | 참고 지표 |
| Raw decision 관측 | 120/120 | unknown을 안전 판정으로 계산하지 않음 |
| 평균 / p95 latency | 5.215413초 / 5.811240초 | 저장된 전체 경과시간 |

Warmup5개는 schema/parser/semantic 모두 5/5이며 본시험 분모에 합치지 않았다. 본시험 오류는 `UNGROUNDED_REQUIREMENT` 1개다. READY gold62개는 모두 정확한 대상·이동값으로 수용됐고, 의미 실패3개는 모두 non-READY gold다.

## 실패3개: 원본과 gold를 변경하지 않음

| ID | 관측 및 원인 | 안전 경계 |
|---|---|---|
| H02 | 조회 요청에 대한 CLARIFICATION 결정은 맞다. 그러나 `회의실에 어떤 책상들이…`에서 `회의실 책상`이라는 비연속 결합을 target quote로 생성했다. 원문에 동일 substring이 없어 adapter가 `UNGROUNDED_REQUIREMENT`로 거절했다. | 적절한 grounding 거절이다. 자연스러운 요약으로 원문 인용을 대체한 모델 계약 위반이며 parser false negative로 분류하지 않는다. |
| HH-B05 | 축 기준 미지정은 정보를 보충해야 하는 CLARIFICATION gold다. 모델은 같은 부족 정보를 이유로 UNSUPPORTED를 반환했다. 대상 quote는 정확하고 parser는 수용했으나 고정 결정 rubric과 다르다. | 안전한 non-READY 유지지만 의미 판정 오류다. Gold 또는 label 기준을 완화하지 않는다. |
| HH-J05 | 법규 적합성 보증·자동 배치에 대한 UNSUPPORTED 결정은 맞다. Target quote `가구를`에 필수 장소 `다목적실`이 빠져 target preservation rubric을 통과하지 못했다. | 실행 가능 상태로 승격되지는 않았지만 대상 범위 보존 실패다. Full-source fallback이나 인용 보정으로 숨기지 않는다. |

## 해석과 다음 검증의 한계

공식 HF tokenizer와 native token ID는 공개20개 중19개만 일치했다. 해당 **FAIL을 유지**한다. NFC normalizer만 끈 별도 reference와 native의20/20 일치·raw UTF-8 roundtrip20/20, 실제 native context 길이 검증을 근거로 raw-Unicode variant를 명시했다. Application 원문·출력에 NFC 보정을 넣지 않았다. 이 차이의 의미 품질 영향을 없다고 단정할 수 없다.

120개는 이전에 공개된 development40 + 기존 exposed80이다. 모델/양자화/runtime/sampling이 함께 바뀌었으므로 개선 원인을 모델 크기나 한 가지 설정으로 분리해 주장할 수 없다. 고정 seed의 반복은 독립 표본이 아니며 0 false positive는 실제 사용 위험이 0이라는 증거가 아니다. GPU 수치는 허용 GPU의 aggregate 관측이고 per-process VRAM peak는 측정하지 않았다. RTX5090 실측과 실제 IFC 변경 검증도 이 진단 범위 밖이다.

후속 formal 반복과 별도로 고정된 미사용 holdout gate가 필요하다. 이번 실패3개를 근거로 gold·parser·gate를 조용히 바꾸거나 이미 노출된 자료를 다시 unseen으로 부르지 않는다. 이번 판정은 다음 고정 평가를 진행할 수 있다는 진단 결과다.

## 무결성

- 독립 proof 원본: `var/research/native-qwen38-exposed-replay-20260920T071218Z.json`, SHA256 `6a9ce259b60348504cfa1afec9ddb7838d30190e46b88f2b1ab33917e46836ab`.
- 실행 helper: `var/review-tools/replay_native_qwen38_exposed.py`, SHA256 `c1f063fe4a6ea14c9eaa57bb6e10467460f6765d9a3b4fce67a6fca0f69ac592`; 실행 전 별도 agent의 읽기 검토 PASS.
- Snapshot record: SHA256 `abc8aad84c596526648d5e40c5fc9fda1d68a146d74c15bf1bd95fa3a89bc6b7`.
- 원본 `results.json`: SHA256 `e16c753dd9701f1115a8d56445f27f68835e20b9323787316db776606769da48`.
- 원본 `manifest.json`: SHA256 `51261e31972b8c39bf59114c2258411381004134356c098801744c024ab73258`.
- 원본 `dataset.json`: SHA256 `174783772ae29325c63b41d44d7d5fe4904dc568ac08e8c3484bc369aa28a6bc`.

Root가 위 proof/helper/snapshot과 원본 artifact를 archive에 exact bytes로 보존하고 별도 integrity를 작성한다. 본 검토자는 이 보고서와 독립 proof만 작성했으며 원본 결과·freeze·source·평가 조건은 변경하지 않았다.
