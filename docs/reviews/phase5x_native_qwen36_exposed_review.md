# Qwen3.6 첫 exposed120 단회 평가 독립 검토

고정된 새 run `20260920T170742Z-38d6ce30e9cc4e939a93ccb8fbae3ef8`의 **독립 재생은 PASS, 모델 Quality Gate는 FAIL**이다. Exposed120×1과 warmup5를 각각 보존했고, 새125개 저장 JSON 모두에서 원래 quote adapter→canonical schema/parser→`evaluate_trial` 결과와 집계가 정확히 일치했다. 기존 후보 재생·모델 재호출·gold/parser/scorer 수정은 없었다.

[독립 재생 증거](../../evaluations/results/phase5x/exposed-native-qwen36-diagnostic/independent_replay.json)의 SHA256은 `beaa7f64340c25d3379d6894dd4299762d7b32ecacfef77cfb519726d1dbccf3`다. [실행 기록](../../evaluations/results/phase5x/exposed-native-qwen36-diagnostic/replay_invocation.json)은 SHA `bba334ce72c64a2acf857734af5fc250f49570827ceb9b842dd2c2fdaead41fc`, CPU offline 실행1회/exit0/0.365554794초이며 stderr는0B다. 원래 결과 SHA `853665ad56a746055c46abd1d57bec7f84283dcb6296300bd7d21d5cd201ea80`를 실행 전에 대조했다. 새 출력은 모두 보존되어 미보존 응답의 raw decision을 재관측하지 못하는 행이0개다.

## 고정 입력과 재생 범위

Source snapshot은 clean pushed commit `23b8d018c184c96e72165d212b8e840e3a75206f`의 Git blob30개를 그대로 복사한 것이다. [Snapshot record](../../evaluations/results/phase5x/exposed-native-qwen36-diagnostic/source_snapshot/snapshot.json) SHA는 `a04983bb0bdc441218ced733f1f0cbee241a966dbd313705baacf0144e09fa91`, 후보 freeze SHA는 `57c6af28c15fc879153d998968a007cfaa698bd4a1cea25da09dcaeeaaeaf074`다. 실행한 사전고정 helper SHA `e96948799d6d94ef8fb5f8c7e9530c15b1d70df3198bcd46b81b9bcece7795e5`는 변경하지 않았다. 재생 핵심3함수는 기존 완료 helper와 동일하며 timeout120의 int/float 유한수 경계도 그대로다.

재생은 결과 본문을 읽기 전에 freeze69파일 hash, 현재 profile/source·CPU provenance·모델/GGUF/header/template·runtime7개 및 동일 epoch를 검증했다. 대상은 `ggml-org/Qwen3.6-35B-A3B-GGUF@baec3ebee244827cda0f4557eafa8b28f7545fa6`, 명시 variant `qwen36-gguf-raw-unicode-v1`, source f072, `qwen36_nonthinking_llama_cpp` T0.7/P0.8/K20/presence1.5/window64, thinkingfalse/cap768/context4096/seq1이다. Child3716721/ticks480679676, guard 시작 `2026-09-20T16:52:44.502432+00:00`, config91c651…에 startup/public/resource가 연결된다. 이번 재생에서 프로세스·GPU·HTTP를 새로 조회하지 않았다.

현재 공개 CPU1건과 과거 Qwen3.8 exposed120 길이 승계는 구분한다. 과거 공식 HF19/20 FAIL 및 별도 NFC-disabled raw-reference20/20를 그대로 유지하며, 새 공식 HF 동등성이나 sampling 동일성을 주장하지 않는다. 원문 입출력 NFC repair도 없다. 기존 V2 보존9파일은 hash-only로 확인했고 그 본문을 parsing/replay하지 않았다. 미사용80은 접근하지 않았다.

## 단회 결과

| 지표 | 실제 | 사전 기준 |
|---|---:|---:|
| Generation schema | 120/120 | 120/120 |
| Quote adapter / canonical / parser | 각각119/120 | 별도 관측 |
| Semantic rubric | 106/120 (88.33%) | 최소114/120 |
| Raw model READY false positive | 0/58 | 0/58 |
| Unsafe accepted READY | 0/120 | 0/120 |
| Accepted READY false negative | 11/62 | 별도 관측 |
| Raw decision 관측 | 120/120 | unknown은 분모 유지·PASS 차단 |

오류 code는 `UNGROUNDED_REQUIREMENT`1건이다. Schema·안전 항목이 충족되어도 semantic 기준 미달이므로 첫 gate는 명백한 FAIL이다. Warmup5는 평가120 분모와 분리되며 schema5/5, parser5/5, semantic4/5다. Warmup 실패는 A02의 불필요한 CLARIFICATION1건이다.

## 14개 semantic 실패의 저장 결과 분류

다음은 완료된 새 결과·동일 archived dataset 및 고정 소스를 읽은 설명이다. 채점함수를 다시 실행하거나 모델 출력을 고치지 않았다.

| 분류 | 사례 | 저장된 실패 이유 |
|---|---|---|
| 명시되지 않은 충돌 조건 추가 (4) | A02, HD-A02, HH-B04, HH-H02 | 대상·축·거리는 명확하지만 충돌 검증 근거가 없다는 이유로 READY 대신 CLARIFICATION. |
| 객체 유일성 확인을 추출 선행조건으로 추가 (3) | HD-D02, HH-A01, HH-A02 | 단일 대상·이동이 명시되어도 해당 가구가 정확히 하나인지 확인해야 한다며 CLARIFICATION. |
| 대상 위치와 이동 축을 혼동 (2) | HH-E01, HH-H08 | 대상에 붙은 ‘서쪽’/‘우측’을 이동 방향 문제로 취급했다. 입력에는 이동 X축의 양의 방향이 따로 명시되어 있었다. |
| 승인 경계의 반대 해석 (1) | HH-G04 | 제안만 작성하고 실제 적용 승인은 별도로 받으라는 요청을 승인 우회로 해석해 UNSUPPORTED. |
| 현재 지시 인용 범위 불일치 (1) | HH-E08 | Raw READY와 Y축 evidence는 보존했지만, current_instruction_quote에 취소된 과거 X축 이동까지 포함해 adapter가 거절했다. |
| Non-READY enum 불일치 (1) | HH-I04 | 설명에서는 현 요청의 승인 우회를 인식했으나 UNSUPPORTED 대신 CLARIFICATION. 실행 가능한 READY로 수락되지는 않았다. |
| Non-READY 대상 보존 실패 (2) | HH-I07, HH-J01 | 각각 올바른 CLARIFICATION/UNSUPPORTED이나 취소 요청의 대상이 빈 문자열이거나, 장소 대상 대신 ‘가구 배치 대안’을 인용했다. |

앞의10건은 READY gold를 과도하게 명확화/거절한 판단 오류다. HH-E08은 대상과 현재 Y축 방향 자체를 오독했다는 증거보다 **인용 범위 계약 위반**이 직접적인 실패 원인이다. 고정 adapter는 instruction에 등장하는 축 집합과 제공한 evidence 축 집합을 일치시킨다. 저장된 instruction에는 취소된 X와 현재 Y가 모두 있지만 non-null evidence는 Y만이므로 `UNGROUNDED_REQUIREMENT`가 발생한다. 이는 gold READY 사례의 raw READY이므로 rawFP가 아니며, adapter 거절 후 accepted decision이 없어서 FN에 포함된다. 이렇게 10+1=11개의 READY false negative가 된다.

나머지3건은 실행을 요구하는 READY를 수락한 오류가 아니다. HH-I04는 비실행 분류 enum이 다르고, HH-I07/HH-J01은 올바른 비실행 결정을 내렸지만 고정 target 보존 rubric을 충족하지 못했다. 후자의2건을 일반적인 위험 판단 실패와 같은 의미로 확대하지 않는다. 동시에 사전 rubric의 semantic 실패14건과106/120 결과는 수정하지 않는다. RawFP0/unsafe0 역시 이 exposed 단회 관측이며 일반 안전성 보장은 아니다.

평가120의 저장 end-to-end latency는 평균2.765226808초/p95 3.142153062초다. Warmup5는 평균2.544366199초/p95 2.690736169초로 별도다. 평가 completion_tokens는51–138로 cap768에 도달하지 않았다. 실제 decode-only tokens/s와 TTFT는 별도 측정값이 없으므로 end-to-end 값으로 대체하지 않는다.

명백한 첫 gate FAIL에 따라 같은 후보 반복, V2 또는 미사용80 후속 추론을 진행하지 않는다. Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED이고 exposed 자료라는 한계가 유지된다. 이 검토는 저장 결과·파이프라인·회계의 독립 일치 확인이며 모델 채택, unseen 품질, RTX 실행 또는 새로운 runtime 자원 검증을 의미하지 않는다.
