# Gemma12 실패 뒤 Qwen3.6-35B-A3B: 저장 자료만으로 한 사전 판단

2026-09-21 KST. 상태: **METADATA-CLOSURE-PENDING / NOT_QUEUED**. 권고는 소형 metadata 원본 확보 여부를 먼저 결정하는 것이며, 지금 weight 다운로드나 다음 GPU 평가를 예약하지 않는다. Root가 전달한 새 Gemma12 첫 결과는 semantic112/120, rawFP3/58, unsafe1/120로 FAIL이다. 해당 결과 본문은 이 검토에서 읽지 않았다. 낮은 VRAM/짧은 지연은 그 안전성 실패를 상쇄하지 않으며 같은 후보 재시도·V2·미사용80 접근은 하지 않는다.

## 정확히 남아 있는 출처

| 항목 | 저장된 공식자료 추출 기록 |
|---|---|
| 원본 | `Qwen/Qwen3.6-35B-A3B@995ad96eacd98c81ed38be0c5b274b04031597b0` |
| 변환 배포 | `ggml-org/Qwen3.6-35B-A3B-GGUF@baec3ebee244827cda0f4557eafa8b28f7545fa6` — Qwen 원저자와 ggml-org 변환자를 구분 |
| 유일한 weight 후보 | `Qwen3.6-35B-A3B-Q4_K_M.gguf`, **20,419,565,568 B**, SHA256 `671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7` |
| 원본 연결 | `.src_sha`의 PRIMARY가 위 원본 revision과 같았다는 기록; 파일 SHA256 `ec3a62c6b2e66aab222c8ea8d5aa426e4587625128d71b7267c8ac3eaf9e1a74` |
| config | **3,686 B**, SHA256 `93a4693fa9d8392fbfccd4b3c9873f4bfdcb14fdede978b123d07d19675efe99` |
| API 응답 | GGUF SHA `2cfa6a3eebc25fdc1e56b0e065730b6e0e644cc2cf24354b4f4c793301e30408`; 원본 SHA `4b61353e6b53715915493d9ddd62aca50cffc272c2b59491063b92ea32ec782e` |
| license | 원본 card의 `apache-2.0` 표기 기록. LICENSE 원문·GGUF attribution의 실제 bytes/hash는 아직 보존하지 않았음 |

근거는 [saved refs](next-candidates-after-exaone-refs.json)와 [기존 조사](next-candidates-after-exaone.md)다. 조사 담당자도 별도 Qwen3.6 원본 응답 파일을 보존하지 않았다고 확인했다. 따라서 위는 **당시 공식 API/web의 structured extraction + hash 기록**이며 지금 원본 bytes를 다시 해시한 검증이 아니다. API hash는 당시 main 응답의 hash이며 pinned endpoint 응답의 동일 hash를 주장하지 않는다. config 원문, README, generation_config, tokenizer/json/config, template, LICENSE, safetensors index 및 변환 log의 실제 파일 크기·합계는 미확인이다. tokenizer/template가 Qwen3.8과 같다고 주장할 근거도 없다. 향후 metadata만 허용되더라도 먼저 API 크기표로 총량을 정하고 bounded GET해야 한다.

원래 pinned 주소: [원본 card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md), [GGUF revision](https://huggingface.co/ggml-org/Qwen3.6-35B-A3B-GGUF/tree/baec3ebee244827cda0f4557eafa8b28f7545fa6), [.src_sha](https://huggingface.co/ggml-org/Qwen3.6-35B-A3B-GGUF/blob/baec3ebee244827cda0f4557eafa8b28f7545fa6/.src_sha). 이번에는 이 URL에 접속하지 않았다.

## 검증할 만한 가설과 한계

등록 가능한 가설은 “기존 Qwen3.8 dense와 다른 **35B total/3B active MoE checkpoint**가 같은 generation2 계약·원문 인용·가구 범위·승인 경계에서 semantic≥114/120와 rawFP/unsafe0을 동시에 만족하는가”다. 기존 Qwen3.8의 exposed117/120·rawFP0·unsafe0은 이 계열의 좁은 계약 적합성 가능성을 보였지만, 이미 노출된 별도 V2에서73/80·rawFP1·unsafe1로 실패했다. 따라서 이는 미검증 checkpoint의 비교 가설이지 개선 예측, 한국어 benchmark 우위, 새 학습계열 추가, 또는 MoE 효과를 분리한 인과 실험이 아니다. quantization·학습·구조가 함께 달라진다.

Gemma12의 작은 장비 배포 가설은 이번 gate FAIL로 닫는다. Qwen3.6은 약20.42GB weight라 그 저비용 대안 가설을 계승하지 않는다. 동일 노출120에서 여러 후보를 선택하는 과정 자체가 선택 편향을 늘린다. 다음 checkpoint를 선택하더라도 첫 gate 한 번의 사전 등록된 비교까지만 의미가 있으며 FAIL이면 반복/추가 holdout 없이 닫는다. 메타데이터가 Qwen3.8와의 비교 비용을 충분히 줄이지 못하거나 전체 peak 근거가 부족하면, 임의의 또 다른 모델을 자동 투입하는 것보다 사용자와 제품 범위·요구 정확도·모델 선택 기준을 다시 정하는 편이 명확하다. 현재 prompt/parser/gold/gate 수정 제안은 아니다.

## 요청 profile: 공식값과 프로젝트 선택을 분리

당시 원본 card 기록은 `enable_thinking=false`, T0.7/P0.8/K20/minP0/presence1.5/repetition1이다. 반면 기존 `qwen38_nonthinking_llama_cpp`는 원문 인용 토큰에 대한 penalty 영향을 피하려고 presence0/frequency0/repeat1/window0, seed42, `temperature,top_k,top_p,min_p` 순서를 명시한 실험 profile이었다. 이를 공식 Qwen3.6 권장 설정과 같다고 부르면 안 된다.

새 profile는 미정이다. 비교 요인을 줄이려면 같은 중립 HTTP recipe를 **별도 이름의 실험 조건**으로 사전 등록할 수 있으나 공식 presence1.5를 따랐다고 주장할 수 없다. 공식값을 선택한다면 native penalty history에 prompt가 포함되는 점, repeat_last_n 및 sampler 순서를 별도 결정해야 한다. 현재 저장된 공식 기록에는 window/order/seed/frequency의 완전한 값이 없다. 두 recipe를 결과에 따라 왕복 탐색하거나 3.8의 raw-Unicode variant를 자동 승계하지 않는다.

## 재사용과 반드시 새로 확인할 경계

고정 f072 converter의 `Qwen3_5MoeForConditionalGeneration`→QWEN35MOE 등록과 loader의40층→35B_A3B 분기는 존재한다. 저장 config는 hidden2048/vocab248320/40층 중 GDN30+full10, routed256 중8+shared, MTP1을 말한다. 기존3.8은 QWEN35 dense/hidden5120/64층이므로 GPU graph·expert scratch·GDN state·실제 tensor inventory의 동일성을 주장할 수 없다.

- **정의 재사용:** 고정 native binary/source와194개 CPU 객체, owned guard·부모 사망/loopback/core/log 제어, JSON-schema wire/adapter/scorer, bounded download/header parser, saved-result replay의 공통 코어. 그대로인 부분의 검증을 다시 실행하지 않는다.
- **현재 승계 불가:** 3.8 actual header, tokenizer20/reference 또는 raw-NFC-off PASS, template/전체 system fidelity, context200, VRAM/runtime 및 품질 PASS. 실제3.6 metadata/header와 exact typed tokenizer/template/flags·effective request/source 동등성을 먼저 비교해야 조건부 승계 여부를 알 수 있다. 서로 다른 값이 있으면 그 차이에 필요한 공개 CPU 검사만 새로 설계한다. 공식 tokenizer normalizer를 지금 추정하지 않는다.
- **후보별 필수 새 근거:** 원본 metadata/license closure, 실제 GGUF fullSHA와 strict tensor/header/config/quant identity, native QWEN35MOE whole-peak 계획 및 새 owned startup/resource, 명시 profile/model tuple와 실제 request binding. 파일명의 Q4_K_M이나 source 등록만으로 실행 성공을 주장하지 않는다. mmproj/MTP/dflash 추가 파일은 후보에 포함하지 않는다.

## 자원과 디스크: 허가표가 아닌 screening

저장된 A100 기준은 free36373−safety7275=**29098 MiB**다. weight proxy19473.615 + full F16 KV80 + F32 recurrent state 한 벌60 + 단일 vocab F32확장1940 =21653.615 MiB로, **7544.385 MiB**가 나머지 항에 남는다. 이 합은 upper bound가 아니다. recurrent checkpoint/rollback, packed experts·MoE matmul, graph liveness, VMM/pool highwater, driver/modules/handles, alignment/복사/단편화를 아직 포함하지 않았다. 3B active를 weight 상주량 또는 최대 workspace로 쓰지 않는다. 기존28,672 MiB 계획을 이름만 바꿔 적용할 근거는 없으며 새 whole-peak 합과 fresh GPU 정책이 필요하다.

가장 최근 이 검토에서 읽은 디스크 근거는 Gemma12 [download receipt](../../evaluations/results/phase5x/gemma4-12b-preparation/download/result.json)의 **2026-09-20T15:22:47Z minimum_free_bytes=36,766,171,136**이다. 현재 free를 조회하지 않았다. 그 값에서 Qwen weight를 빼면16,346,605,568 B로20.5GiB floor22,011,707,392 B보다 **5,665,101,824 B 부족**하다. 향후 종료·비활성·소유권/FD-map/lock 등을 root가 확인하고 별도 허용한 경우에만 Gemma12 한 파일6,975,879,296 B의 회수를 고려할 수 있다. 단순 조건부 계산상 회수 후 새 weight 잔량은23,322,484,864 B, floor 위1,310,777,472 B이며 metadata/새 helper/로그의 추가 공간은 여기서 더 빠진다. 삭제·재다운로드·정리 실행은 제안에 포함하지 않았다.

보존 근거 SHA256: refs `464691073f5628a5bd9f691a9cfe67fb0d642a493e1972c8426f807e057dbee2`; 기존 조사 `97bba4e86c9f263ee0c4a76a58db679b17df487d9e3cd40967c9a94c28d8de7d`; download receipt `eebba0743c8304a7670c66b5905e8b34b40946d6e0cfb507c0aece79645a379f`; f072 conversion/qwen.py `b783f53598e1a65cb0ef7fbe0d0f52da472e2784f63acf13a5aea00f623cfaa6`; qwen35moe.cpp `ada74c413bfda274f1ffe8c4c32dbd80e999c777a5888244cc118da832f635a7`.

작업 범위: 이미 저장된 조사/metadata/집계 receipt와 고정 source 읽기, 산술, 이 ignored note 작성만 수행했다. 새 HTTP/download/native/compile/tests/weights/GPU/평가·replay/미사용 자료 접근·production 변경은 모두0이다.
