# EXAONE 4.5 CPU 사전 검증

명시적 후보 `exaone45-gguf-continue-free-raw-unicode-korean-v1`은 CPU 계약 검사를 통과했다.
공식 HF tokenizer 동등성은 **18/20 FAIL**이며 그대로 보존했다. 별도 raw 기준의 성공을 공식 동등성이나
모델 품질 성공으로 바꾸어 해석하지 않는다. 이 단계에서 모델 추론·GPU·HTTP 호출은 없었다.

공식 EXAONE 4.5 33B GGUF revision `0e969634ef24db05151b435970297a6dee634b7e`를 사용한다.
고정 native source는 `f072b103714dfa1eee531f80b24512faf38e3dd2`이며, 실제 header/full-file SHA 검증 후
CPU vocab만 읽었다. Tensor allocation, model context, backend initialization, decode는 하지 않았다.

| 검사 | 실측 |
|---|---|
| 원본 공식 tokenizer와 native IDs | 18/20, 분해 한글·combining accent 두 공개 사례 불일치 |
| 같은 공개 20개 native raw 왕복 | 20/20 |
| NFC만 disabled한 별도 reference와 native | IDs 20/20, raw 왕복 20/20 |
| 공식 Jinja 원본·등가 override·native render | 공개 18개에서 exact bytes; 실제 system/user 포함 |
| Native vocab 문법 | plain/fenced 20허용·40거절, EOG 검사 |
| 노출120 길이 | input 1,900–2,122; 출력768 포함 최대 2,890 |
| 기존 V280 길이 | input 1,915–2,088; 출력768 포함 최대 2,856 |
| Context 한도 | 4,096 |

공식 template의 첫 system 분기에서 native Jinja가 출력 누적을 잃는 원본 실패는
[template 사전 검증 보고서](phase5x_exaone45_template_preflight_report.md)에 있다.
별도 override는 첫 `continue`를 동등한 `if/elif`로 제거했다. 메시지 재배치, 정책 변경, system→user 병합은 없다.
공식 embedded template과 effective override의 hash를 각각 유지한다.

공식 tokenizer의 NFC와 native raw Unicode 처리는 다르다. 공식 tokenizer/fixture/GGUF는 바꾸지 않았고,
NFC-off reference는 진단용 메모리에만 만들었다. Application 입력·출력에 NFC 보정이나 quote 수리를 적용하지 않는다.
공개20 일치로 전체 Unicode 보존을 보장할 수 없다. 입력200은 이미 노출된 자료의 길이만 검사했으며,
gold를 평가하지 않았고 새 미사용 holdout에는 접근하지 않았다.

[최종 CPU proof](../../evaluations/results/phase5x/exaone45-cpu-preflight/contract/final-cpu-proof.json)의 SHA256은
`2a937a8adeca827f4724c9b65947291005aa34dc8ca4af823739fd09ca248209`다.
[공식 실패](../../evaluations/results/phase5x/exaone45-cpu-preflight/contract/public-vocab-proof.json),
[별도 raw 성공](../../evaluations/results/phase5x/exaone45-cpu-preflight/contract/raw-vocab-proof.json),
[길이 집계](../../evaluations/results/phase5x/exaone45-cpu-preflight/contract/vocab-context-raw-proof.json),
[재현 정의와 한계](../../evaluations/results/phase5x/exaone45-cpu-preflight/contract/README.md)를 각각 보존했다.
CPU 준비 성공은 native CUDA 기동, 실제 peak VRAM, 고정 semantic/rawFP/unsafe 품질 gate의 성공을 대신하지 않는다.
라이선스 적용 범위는 기존에 정한 내부 비상업 연구 비교이며, 제품 배포 허용을 주장하지 않는다.
