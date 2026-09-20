# Generation3 계약·통합 검토

2026-09-20 UTC. **구현·회귀·CPU 검토 PASS, 고정된32B 진단1회 진행 조건 충족.**
모델 의미 정확도·Phase5.x 완료·Phase6 진행을 승인하는 결과가 아니다.
이번 검토에서는 데이터셋 원문/gold를 읽거나 v2 내용을 사용하지 않았다.
검토자가 v2 원저자였다는 한계와 [기존 root 노출 기록](../../evaluations/hardening_v2_input_exposure_addendum.json)은 유지한다.

## 계약과 집계 경계

새 [설계](../requirement_facts_contract_design.md)의 `GenerationContract.FACTS=3.0`은
명시적으로 선택한 한 HTTP 요청이다. Client/CLI의 기존1.0/2.0 기본 경로·요청은 유지되며,
응답 version에 따른 자동 전환·retry·수정은 없다. Staged3.0은 client/자료 읽기 전에 거절된다.
Schema의11facts와2예시를 adapter의 enum/null/512·1024·4096자 한도와 대조했고 구조 모순은 없다.
READY는 condition NONE만 허용하고, 현재 authority 우회·선언한 scope/exclusion 누락은 거절한다.

Root의 최종 `decision`은 strict JSON 이후, generation schema와 facts 검증 **이전**에 관측된다.
Schema/facts/2.0 adapter/canonical parser 실패가 raw READY를 지우거나 다른 label로 바꾸지 않는다.
평가기에는3.0 `generation_output`,2.0 `projected_quote_output`,1.0 `semantic_output`과 단계별
판정이 분리된다. Facts projection 뒤에도 기존2.0 adapter와 canonical parser를 반드시 실행한다.
형태가 잘못된 projection은 다음 adapter로 보내거나 저장하지 않고, source 전체·axis context·코드UUID를 유지한다.
오류 trial도 원래 분모에 남으며 malformed/추가 필드·raw HTTP·추론 내용은 저장하지 않는다.

`score_output`, `rate`, `latency_summary`, `run_evaluation`, `strict_json`, `load_cases` 함수 source는
checkpoint `16d67895dfa8bfabe2c59f66732f7ec25b0510ac`과 exact 일치했다.
기존 raw/accepted FP·wrong accepted move·FN·target/SI·의미 rubric 공식은 그대로이며
`facts_projection_accepted`만 추가된다. 기존2.0 함수3개의 source와 canonical parser bytes도 그대로다.
중앙 enum/dispatch를 추가했으므로 `requirement_generation.py` 파일 전체 hash는 바뀌었다.

## 실행된 검증

- 작성자 실행: 신규 facts17 + 기존 quote22 + canonical33 = **72 PASS**.
- 별도 작성자 실행: 신규 평가기9, 실제 루프백 fake HTTP6. HTTP는 양 protocol에서 한 요청,
  정확한 version/원문/SI, 오류 뒤 재시도 없음과3.0→2.0 응답 fallback 거절을 검증했다.
- Root 전체 회귀: headless·개인 PostgreSQL/실제 IFC 환경에서 **346 PASS, skip0,18.730초**.
  기존314에 신규17+9+6이 추가됐다. 검토자는 `var/phase5x-generation3-regression.log`의 완료 결과를 확인했다.
- 독립 fake-only boundary probe: 기존1.0/2.0 × 양 protocol 및2.0 branch 설정의 **6 wire pairs byte 동일**,
  raw READY fault10개 보존, KeyboardInterrupt/SystemExit 전파. Dataset/model/network/GPU 호출0.
- 독립 CPU xgrammar:24 controls 중14개 grammar 거절,10개 grammar 허용 중5개 backend 추가 거절,
  나머지5개 최종 parser 통과. Prompt 예시2개 포함이며 vLLM unsupported feature 없음.
  실제 client payload와32B tokenizer로 exposed120 최대 input+output1024 = **3,622/4,096**.
  별도 담당자의 v2 길이만 검사는3,547이며 이 문서에는 원문·case ID·gold를 싣지 않는다.

CPU proof의 source9개 및 boundary proof의 source6개 hash를 현재 파일과 독립 재대조했다.
Canonical parser SHA는 `a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a`,
facts adapter는 `2e47ed917640740777c98d7037a853446de2ac3ac5acc8beee4cbb817a86fec5`,
중앙 generation은 `fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198`다.
[CPU proof](../../evaluations/results/phase5x/generation3-preflight/cpu_preflight.json) SHA는
`14b1b2149d96edb5385958906b693babacffd6e3ffb98f7aa8b2b0720e122699`,
[boundary proof](../../evaluations/results/phase5x/generation3-preflight/boundary_review.json) SHA는
`1ce7a5a3b929d377f769f560beb582a9b0d63a1ce08e84678f0fd4716fbedc39`다.
원본은 각각 `var/research/generation3-32b-preflight-70ea33d936e64c3f9697ed2c55d391ad.json`,
`var/research/generation3-boundary-review-fbd5cad667514ebda8bf50637044e6f0.json`이다.
전체 회귀 로그 SHA는 `3084c6160da596a6bbc9d87ed0d619ab4144702735c317099be8f1b80a30bf95`다.
실행 helper와 복원 방법은 [증거 README](../../evaluations/results/phase5x/generation3-preflight/README.md),
추가 독립 source/fault 검토는 [독립 검토 기록](../../evaluations/results/phase5x/generation3-preflight/independent_review.md)에 보존됐다.

## 제한과 다음 gate

Facts가 실제 조건·authority·scope를 누락한 경우, exact quote/모순 검사는 이를 증명하지 못한다.
한계 witness는 이런 잘못된 READY가 backend를 통과할 수 있음을 보이고, 독립 probe도 이를
**unsafe로 계수**했다. 구조 검사 통과를 자연어 의미 안전성으로 확대하지 않는다.
Facts-first 순서는 내부 판단 순서의 증거가 아니며 새 표현·prompt·grammar·output cap이 함께 바뀐다.
RTX5090 실측은 없고 양 dialect HTTP 검증은 fake server 결과다.

출력 cap1024는 context4096/sequence1/KV256의 기존 전체 한도 안에 있다.
기존 whole-peak 추정25,600MiB를 새 runtime 실측으로 오인하지 않으며, GPU3 fresh preflight와
watchdog·실제 startup/health/listener 검증은 별도로 필수다. Source·runtime·gate 동결과
commit/push 후 exposed120×1+warmup5의 제한 진단1회를 진행할 수 있다.
Gate는 schema120/120, semantic≥114/120, rawFP0/58, unsafe0/120 그대로다.
실패하면 실패 결과와 미완료 상태를 보존하며, 통과해도 정식 반복과 별도 holdout이 남는다.
