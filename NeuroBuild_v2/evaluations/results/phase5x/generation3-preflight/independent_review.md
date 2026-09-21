# Generation3 독립 CPU/통합 경계 검토

**검토 범위 PASS, 현재 발견된 material blocker 없음. 모델 품질·실제 GPU grammar 실행 PASS가 아니다.**
구현 source를 읽고, tokenizer/xgrammar CPU와 fake HTTP/fault injection만 실행했다.
Source·prompt·schema·gold를 변경하지 않았다. 실제 모델/HTTP/GPU query/weight payload 읽기0회다.

- CPU proof: `generation3-32b-preflight-70ea33d936e64c3f9697ed2c55d391ad.json`
  SHA256 `14b1b2149d96edb5385958906b693babacffd6e3ffb98f7aa8b2b0720e122699`.
- Boundary proof: `generation3-boundary-review-fbd5cad667514ebda8bf50637044e6f0.json`
  SHA256 `1ce7a5a3b929d377f769f560beb582a9b0d63a1ce08e84678f0fd4716fbedc39`.
- Baseline: `generation3_legacy_baseline.json`, checkpoint
  `16d67895dfa8bfabe2c59f66732f7ec25b0510ac`.

기존 canonical parser a940… hash는 byte 동일하고 `_validate_source`, `_quoted_axis`,
`adapt_generation_v2` 함수 AST 및 동작 경로가 유지된다. 중앙 모듈 diff는 FACTS enum과
명시3.0 dispatch 추가에 한정된다. 새 projection은 version만2.0으로 바꾸고 기존6필드는
그대로 전달하며, 이후 기존2adapter와 canonical parser를 호출한다. Non-READY 승격이나
별도 decision 재분류는 없다. Client의1/2/3 default와staged2-only 제약, manifest의3→2→1
chain·facts/quote schema hash를 읽기 검토했다.

기존1.0, 기본2.0, 명시 branch schema/prompt2.0 각각에 legacy/modern 두 protocol을 적용한
**6개 request body가 checkpoint 대비 byte 동일**했다. 가짜 HTTP 응답만 사용했다.

독립 synthetic **10개 rawREADY/실패 경로**에서 raw FP 분자1/분모1을 보존했다.
Generation schema 거절, facts quote/NULL 모순, facts 성공 뒤 unsigned axis 거절,
adapter/canonical DomainError·일반 예외를 포함한다. Schema-invalid output은 저장되지 않고,
3.0 generation/2.0 projection/canonical output 및 단계 flags가 구분된다. PRIVATE_SENTINEL
예외 문자열이 결과에 없고 KeyboardInterrupt/SystemExit는 전파된다.

조건을 모델 facts에서 NONE으로 누락한 의도적 한계 witness는 실제로 backend를 통과한다.
이 결과를 숨기지 않고 **unsafe1 및 semantic false**로 계수함을 확인했다. Exact quote와
facts 일관성은 원문 전체 의미·조건 누락·동일 substring의 최신성을 증명하지 못한다.

실제32B tokenizer와 현재 client payload를 **200회 fake capture**했다. 출력cap1024 기준:

| 입력 범위 | 수 | 최대 입력 | 입력+출력cap | 4096 대비 여유 |
|---|---:|---:|---:|---:|
| 기존 development | 40 | 2593 | 3617 | 479 |
| 기존 exposed holdout regression | 80 | 2598 | 3622 | 474 |
| v2 input-length only | 80 | 2523 | 3547 | 549 |

v2는 입력 길이만 계산했으며 본문/gold/개별caseID·길이를 root나 prompt 작성자에게 출력하지
않았다. 기존 root의 일부v2 입력 노출 이력은 없어지지 않는다. Tokenization 시 Torch import가
없고, grammar 확인 때만 masked CPU Torch를 사용했으며 CUDA initialized=false였다.

xgrammar0.1.18 compile **5.957초**, unsupported-feature flag false.
총 **24 fixtures: grammar10수락/14거절**, full adapter/parser5수락,
schema-valid이지만 backend가 거절해야 하는5개가 모두 거절됐다. Prompt 예시2개도 포함한다.
모든 source hash는 실행 전후 동일했다. 이 검증은 입력의 의미를 모델이 올바르게 판단한다는
증거가 아니며 출력cap 내 실제 completion·truncation 비율은 별도 실제 진단에서 확인해야 한다.

Full backend 회귀는 root 담당이다. 본 독립 증거를 그것의 대체나 새로운 모델 gate 통과로
기록하지 않는다. 기준 gate/gold/target exactness/FP 분모는 변경하지 않았다.
