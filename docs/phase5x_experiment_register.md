# Phase 5.x 실제 평가 실행 목록

최신 누적은 **27 run /2360 평가 trial /135 warmup 사례**다. 아래 초기16개와 당시3회 규칙은
역사 기록이며, 현재는 사용자 지시에 따라 자동 전체3회 반복을 폐지했다.
GLM 첫120개도 semantic104/120·rawFP1·unsafe1로 FAIL하여 같은 후보 반복·V2 없이 종료했다. 최신 항목은 문서 끝에 있다.

2026-09-20 KST 작성. **AUTO-GENERATED / NOT HUMAN VERIFIED**. 작성 시 보존된 development 실행 **16개, 평가 응답 960개**를 모두 정리했다. Launch/runtime/shutdown 기록과 protocol smoke는 평가 run에서 제외했다. 각 run의 warmup 5개, 총80개도 아래 분모에 포함하지 않는다.

**MoE generation2/분기 schema/v2의 greedy 정식 development120/120, raw FP0/60, unsafe0/120으로 정식 gate를 통과했다.** 이전 neutral 정식119/120/unsafe1 등 모든 실패를 보존했다. 정식 development와 holdout을 통과하기 전에는 Phase5.x 완료나 최종 모델 채택을 선언하지 않는다. 고정 gate는 schema100%, 의미 정확도95% 이상, raw FP0, unsafe accepted0이다. 단회 진단40개는 정식 development40×3 평가나 holdout80×3 평가를 대신하지 않는다. **첫 holdout80×3은 완료했으나211/240,raw9/114,unsafe12/240으로 FAIL이다. 아래 별도 기록하며 이후 같은80개는 exposed regression 자료다.**

## 완료된 실행

시간은 end-to-end 초이며 평균/p95를 소수 넷째 자리로 표시한다. `raw FP`는 non-READY gold에서 모델이 READY라고 응답한 수, `unsafe`는 non-READY gold의 accepted READY와 READY gold에서 대상·이동 rubric이 틀린 accepted READY의 합이다. `FN`은 READY gold를 READY로 수용하지 못한 수다. 분모를 각 셀에 표시했다. Backend 차단으로 raw FP를 지우지 않는다.

| 모델 | Prompt | Sampling | Thinking | 평가 방식 | Schema | Parser | Semantic | Raw FP | Unsafe | FN | 평균(s) | p95(s) | Run ID / 근거 |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 14B AWQ | v3 | G* | 꺼짐 | 정식 40×3=120 | 120/120 | 111/120 | 108/120 | 3/60 | 0/120 | 9/60 | 3.3225 | 4.6700 | [20260919T205840Z-469fdecdb1fd476f82202df54a1808a7](../evaluations/results/phase5x/development-v3/results.json) · [manifest](../evaluations/results/phase5x/development-v3/manifest.json) |
| 14B AWQ | v4 | G* | 꺼짐 | 정식 40×3=120 | 120/120 | 120/120 | 96/120 | 0/60 | 0/120 | 24/60 | 2.9610 | 5.0526 | [20260919T211340Z-cebc5bbdaeea46b188caf6d27c4ff804](../evaluations/results/phase5x/development-v4/results.json) · [manifest](../evaluations/results/phase5x/development-v4/manifest.json) |
| 14B AWQ | v5 | G* | 꺼짐 | 진단 40×1=40 | 40/40 | 16/40 | 13/40 | 5/20 | 0/40 | 19/20 | 4.1865 | 5.9424 | [20260919T212748Z-bba084e02f46432aab7f11883d625467](../evaluations/results/phase5x/development-v5-diagnostic/results.json) · [manifest](../evaluations/results/phase5x/development-v5-diagnostic/manifest.json) |
| 14B AWQ | v3 | A | 꺼짐 | 진단 40×1=40 | 40/40 | 37/40 | 36/40 | 1/20 | 0/40 | 3/20 | 3.1967 | 4.4648 | [20260919T213630Z-f42a9eb2a41d4368942b0575dda2893d](../evaluations/results/phase5x/development-v3-sampling-diagnostic/results.json) · [manifest](../evaluations/results/phase5x/development-v3-sampling-diagnostic/manifest.json) |
| 14B AWQ | v6 | T | 켜짐 | 진단 40×1=40 | 40/40 | 20/40 | 17/40 | 4/20 | 2/40 | 17/20 | 13.2334 | 20.6175 | [20260919T214743Z-27a340f0e04343be8be10a062a6eb25d](../evaluations/results/phase5x/development-v6-thinking-diagnostic/results.json) · [manifest](../evaluations/results/phase5x/development-v6-thinking-diagnostic/manifest.json) |
| 14B AWQ | v7 | T | 켜짐 | 진단 40×1=40 | 40/40 | 35/40 | 30/40 | 0/20 | 0/40 | 8/20 | 14.5589 | 28.6642 | [20260919T220158Z-72efdc2dad274cb98b1d61b669597b75](../evaluations/results/phase5x/development-v7-thinking-diagnostic/results.json) · [manifest](../evaluations/results/phase5x/development-v7-thinking-diagnostic/manifest.json) |
| 4B Instruct BF16 | v3 | N | 꺼짐 | 진단 40×1=40 | 40/40 | 39/40 | 37/40 | 1/20 | 2/40 | 0/20 | 2.8118 | 3.7383 | [20260919T222220Z-6df72f2113474c108c488c98faefca20](../evaluations/results/phase5x/development-4b-v3-diagnostic/results.json) · [manifest](../evaluations/results/phase5x/development-4b-v3-diagnostic/manifest.json) |
| 4B Instruct BF16 | v4 | N | 꺼짐 | 진단 40×1=40 | 40/40 | 40/40 | 34/40 | 1/20 | 3/40 | 3/20 | 2.3547 | 3.5674 | [20260919T223253Z-6038073ec36044adb6251920c5d6b285](../evaluations/results/phase5x/development-4b-v4-diagnostic/results.json) · [manifest](../evaluations/results/phase5x/development-4b-v4-diagnostic/manifest.json) |
| 4B Instruct BF16 | v8 | N | 꺼짐 | 진단 40×1=40 | 40/40 | 39/40 | 36/40 | 1/20 | 2/40 | 1/20 | 2.5701 | 3.4501 | [20260919T223831Z-af6ebcd137394488a0adc427bd63edcf](../evaluations/results/phase5x/development-4b-v8-diagnostic/results.json) · [manifest](../evaluations/results/phase5x/development-4b-v8-diagnostic/manifest.json) |
| 4B Instruct BF16 | v3 | G | 꺼짐 | 진단 40×1=40 | 40/40 | 38/40 | 36/40 | 1/20 | 2/40 | 1/20 | 2.5731 | 3.4038 | [20260919T224246Z-64a5648ea1b546c78b1f961bf3b6c094](../evaluations/results/phase5x/development-4b-v3-greedy-diagnostic/results.json) · [manifest](../evaluations/results/phase5x/development-4b-v3-greedy-diagnostic/manifest.json) |
| 30B-A3B Instruct AWQ | v3 | N | 꺼짐 | 진단 40×1=40 | 40/40 | 36/40 | 34/40 | 1/20 | 1/40 | 4/20 | 4.2410 | 6.0795 | [20260919T231243Z-194bbb3212944ebcb8e0e54bfa1b28b5](../evaluations/results/phase5x/development-moe-v3-diagnostic/results.json) · [manifest](../evaluations/results/phase5x/development-moe-v3-diagnostic/manifest.json) |
| 30B-A3B Instruct AWQ | v4 | N | 꺼짐 | 진단 40×1=40 | 40/40 | 37/40 | 34/40 | 1/20 | 2/40 | 2/20 | 3.9956 | 5.9097 | [20260919T232550Z-fb632f6b5f1d405f9618dfe892b0f42a](../evaluations/results/phase5x/development-moe-v4-diagnostic/results.json) · [manifest](../evaluations/results/phase5x/development-moe-v4-diagnostic/manifest.json) |
| 30B-A3B Instruct AWQ | generation2/v1 | N | 꺼짐 | 진단 40×1=40 | 40/40 | 29/40 | 29/40 | 1/20 | 0/40 | 0/20 | 4.1321 | 5.3136 | [20260919T233958Z-5e2143732d36479ab880ab2fc32dfbb3](../evaluations/results/phase5x/development-generation2-moe-diagnostic/results.json) · [manifest](../evaluations/results/phase5x/development-generation2-moe-diagnostic/manifest.json) |
| 30B-A3B Instruct AWQ | generation2/v2 + branches | N | 꺼짐 | 진단 40×1=40 | 40/40 | 40/40 | 40/40 | 0/20 | 0/40 | 0/20 | 3.8990 | 5.1256 | [20260919T235318Z-504ae53e55864b4fba35c6bb108c8c05](../evaluations/results/phase5x/development-generation2-branches-moe-diagnostic/results.json) · [manifest](../evaluations/results/phase5x/development-generation2-branches-moe-diagnostic/manifest.json) |

| 30B-A3B Instruct AWQ | generation2/v2 + branches | N | 꺼짐 | 정식 40×3=120 | 120/120 | 120/120 | 119/120 | 0/60 | 1/120 | 0/60 | 3.9948 | 5.4106 | [20260919T235909Z-741a32ddc5394455943e3b480f8863c3](../evaluations/results/phase5x/development-generation2-branches-moe-formal/results.json) · [manifest](../evaluations/results/phase5x/development-generation2-branches-moe-formal/manifest.json) |

| 30B-A3B Instruct AWQ | generation2/v2 + branches | G | 꺼짐 | 정식 40×3=120 | 120/120 | 120/120 | 120/120 | 0/60 | 0/120 | 0/60 | 4.3943 | 5.9109 | [20260920T001240Z-7daf0ae403de40cfa9043c628abf9d8d](../evaluations/results/phase5x/development-generation2-branches-moe-greedy-formal/results.json) · [manifest](../evaluations/results/phase5x/development-generation2-branches-moe-greedy-formal/manifest.json) |

## 설정 해석

- **14B AWQ**: `Qwen/Qwen3-14B-AWQ`, revision `31c69efc29464b6bb0aee1398b5a7b50a99340c3`.
- **4B Instruct BF16**: `Qwen/Qwen3-4B-Instruct-2507`, revision `cdbee75f17c01a7cc42f958dc650907174af0554`.
- **30B-A3B Instruct AWQ**: 제3자 `ELVISIO/Qwen3-30B-A3B-Instruct-2507-AWQ`, revision `9f41ff709102dbe73e614f9365f8280170db268e`.
- 공통: A100 GPU3, vLLM0.8.5+cu118, context4096, TP1, concurrency1, `legacy_guided_json`/`xgrammar:no-fallback`, 요청마다 seed42. Thinking run만 `deepseek_r1` parser를 사용했다.
- 위 초기16개 표의 출력 상한/timeout: v6는2048/120초, v7은1280/120초, 나머지는768/60초다. 이후 추가 실행의 값은 각 절의 manifest와 설명을 따른다. Thinking 출력 상한에는 내부 reasoning과 final을 모두 포함하며, reasoning 본문은 보존하지 않는다.

| 표기 | 요청 sampling profile | T | top_p | top_k | min_p | presence | frequency | repetition |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| G / G* | `legacy_greedy`에 해당하는 T0/seed42 요청 | 0 | 생략 | 생략 | 생략 | 생략 | 생략 | 생략 |
| A | `qwen3_nonthinking_awq` | 0.7 | 0.8 | 20 | 0 | 1.5 | 0 | 1 |
| T | `qwen3_thinking_awq` | 0.6 | 0.95 | 20 | 0 | 1.5 | 0 | 1 |
| N | `qwen3_nonthinking` | 0.7 | 0.8 | 20 | 0 | 0 | 0 | 1 |

G*인 최초3개 manifest에는 profile 이름 필드가 없으며 기록된 temperature0/seed42를 기준으로 분류했다. 생략한 항목은 서버·모델 기본값을 따르므로 명시적으로 통제했다고 주장하지 않는다. 모델·정밀도·prompt·sampling·thinking·출력 예산의 변경이 섞여 있어 단일 요인의 효과로 전체 차이를 설명할 수 없다. 각 run의 정확한 prompt/schema/client/parser/scorer/runtime hash와 Git 상태는 연결한 manifest에 있다. V5, 4B/v3/N 및 MoE/v3의 `git.dirty=true` 기록도 그대로 보존한다.

## 등록 시 재검증과 한계

각 run의 `results.json` 평가 trial을 등록 당시 `summarize`로 CPU 재집계했고, **전체 metrics 객체가 원본과 정확히 일치**했다. Manifest/result run ID, development split,40개×반복 횟수, warmup5개, dataset hash와 보존된 prompt hash도 대조했다. 처음12개 재집계에 사용한 scorer SHA는 `eff1da86d84775f6bb394b7c4ebbae104a91196a41f6dcac01c145ef0c67a1cc`다. 이는 저장된 trial 판정의 집계 재검증이며 모든 응답을 새로 추론하거나 parser로 재판정한 검증, 사람의 의미 검수는 아니다. 원본 파일은 수정하지 않았다.

같은40개와 고정 seed를 반복했으므로960회를 독립 표본으로 해석하지 않는다. Development 결과로 prompt와 모델을 선택했으며, synthetic gold와 좁은 작업 문법의 한계가 있다. Holdout 입력·gold의 사전 AI 검토도 맹검이나 사람 검수가 아니다. Raw READY 관측이 불가능한 응답은 오판0의 증거가 아니며 원본의 관측률/오류 지표를 함께 봐야 한다.

이 평가는 semantic JSON 추출만 수행했다. **실제 IFC 변경·GlobalId 확정·대상 확인·proposal 승인은 수행하지 않았다.** 평균/p95는 저장된 HTTP end-to-end 측정의 재집계이며 TTFT나 순수 decode 시간이 아니다. Resource report는 GPU 전체 사용량 관측으로, 정확한 process별 VRAM peak를 측정한 것이 아니다. RTX5090 실행 검증도 없다.

## 다음 비교 — 평가 결과 아님

MoE/v3와 v4 진단은 모두 실패했으며 위 완료 표에 포함했다. Generation2/v1도29/40으로 실패했다. READY20개는 모두 정확했으나 non-READY null 규칙 위반10건과 unsigned 방향 raw READY1건이 남았다. 같은 계약의 decision-first branch schema + promptv2 진단은40/40으로 통과했다. 정식 development는119/120이지만 HD-F02의 세 번째 응답이 공간 범위와 제외 대상을 빠뜨려 unsafe1로 실패했다. 같은 prompt/schema/runtime의 기존 legacy_greedy(T0/seed42) 전체40×3은120/120,raw0,unsafe0으로 통과했다. 독립 검토·동결 후 첫 holdout80×3을 수행했으나 아래와 같이 실패했다. 생략된 sampling 항목은 고정 서버 기본값이며 greedy가 결정론을 보장한다고 주장하지 않는다. 기존 canonical1.0 parser와 gold/gate는 그대로 유지한다. [후보 및 runtime 근거](moe_instruction_candidate.md), [고정 manifest](../runtime/models/qwen3-30b-a3b-instruct-2507-awq.json).

실패 원인과 다음 판단의 상세 근거는 [Phase 5.x 보고서](reports/phase5x_report.md)를 따른다. 이 목록은 Phase 5.x 완료나 최종 모델 채택을 선언하지 않는다.

Generation2 구현 뒤에도12개/640개 trial 전체를 새 평가기로 재생하여 parser/오류/SI/semantic 필드와 집계가 같음을 독립 확인했다. 상세 source snapshot은 [generation2 검토](reviews/phase5x_generation2_review.md)에 기록한다.


## 첫 holdout 결과 — gate FAIL

고정 commit64040de에서 최초 모델 노출을 시작했다. Run20260920T002629Z-6742bb1a50b44acd9e02228d83e2747d:80×3=240,warmup5별도, schema240/parser231/semantic211, rawFP9/114, unsafe12/240,FN6/126,mean4.2157s/p955.3083s. [결과](../evaluations/results/phase5x/heldout-generation2-branches-moe-greedy-formal/results.json)·[manifest](../evaluations/results/phase5x/heldout-generation2-branches-moe-greedy-formal/manifest.json)·[독립 검토](reviews/phase5x_generation2_first_holdout_review.md).

위 development16run/960trial와 합치면 총17개 평가run/1200formal또는diagnostictrial,85warmup이다. 서로 다른 split/평가용도를 혼합해 단일 정확도를 만들지 않는다. Firstholdout의FAIL은 그대로 남긴다. 앞으로 기존80개로 튜닝하거나 비교한 결과는 regression/development이며 새로운 unseen 성공으로 표시하지 않는다. 현재 후보는 미채택이고 다음Phase로 진행하지 않는다.


## 노출된 전체120개 — 기존14B/Generation2 비교 FAIL

Run `20260920T005540Z-1f4757de74ec4e75adcc48e3c31c148d`, clean007d893에서 기존14B-AWQ/2.0branch/promptv2/greedy로120×1+warmup5를 완료했다. Schema/adapter/canonical/parser120/120, semantic113/120(94.17%),raw+acceptedFP2/58,unsafe3/120,FN4/62. Mean3.074856s,p953.777019s. 단일가구 두 축 이동을 복수 요청으로 거절3건, 불필요확인1건, 제외대상누락1건, 이동부정/현재승인우회 READY2건이다. [결과](../evaluations/results/phase5x/exposed-generation2-14b-diagnostic/results.json), [독립검토](reviews/phase5x_generation2_14b_exposed_review.md).

기존17개에 이어18번째 완료run이며, 누적1320개의formal/diagnostictrial와90warmup이다. Split과 용도가 다르므로 합산 정확도를 만들지 않는다. 결과SHA `e160815a082b46d3055ec8cbf63b09f847d8e277e04ff7cdfbeb09a11e1154f9`. Formal 확대를 시작하지 않고 분류/추출 분리 실험을 준비한다.


## 두 단계14B 전체120개 진단 — FAIL

Run `20260920T013141Z-f3266f57faac473ebd0b9df66cb3cd75`, clean pushed45858d6에서 staged_v1/2.0/greedy로120×1+warmup5를 완료했다. 두 단계 schema120/120, parser103/120, semantic93/120(77.5%), rawFP11/58, acceptedFP5/58, unsafe6/120,FN11/62. Mean4.691022s/p955.581566s. 정상경로2호출이므로 실제HTTP는250회였고 warmup5사례는 평가분모에서 제외했다. [결과](../evaluations/results/phase5x/exposed-staged-14b-diagnostic/results.json), [독립125개 재생](reviews/phase5x_staged_14b_exposed_review.md).

Classifier decision 자체는108/120이며 rawFP11건 중6건은 후단이 거절하고5건은 수용했다. 17개 grounding 오류 중12개는 JSON null 대신 문자열 "null"을 evidence로 생성한 오류다. 이를 수작업 보정해 재채점하지 않는다. Parser 수용 뒤의 제외대상 손실1건을 더하면 unsafe6이다. 이전 single 실패7개 중6개를 해결했지만 신규 실패26개가 늘어 전체 의미 정확도는 악화했다. 분리 여부뿐 아니라 prompt/schema 제약 조합도 달라 단일 원인으로 단정하지 않는다. 이 후보는 채택하지 않고 formal 반복도 실행하지 않는다.

완료된 Phase5.x 평가는19run,1440 formal/diagnostictrial,95warmup사례다. 두 단계는 사례당 호출 수가 달라 HTTP 호출 수와 구분하며, 서로 다른 split을 합쳐 하나의 정확도를 만들지 않는다. Results SHA `e1a7735a277ebd56dbbd6e8fc4bbb400f59b7eeab333a427f6f3b81870bbc905`.


## 공식32B single2.0 전체120개 진단 — FAIL

Run20260920T022318Z-88be9f58a8fa4017b9ad432ea95740b9,cleanedb586a. Schema/parser120/120,semantic103/120,raw+acceptedFP1/58,unsafe1/120,FN11/62,errors0. Mean5.077785s/p956.068347s. Warmup5는semantic4/5이며분모제외. 125개독립재생일치. [독립검토](reviews/phase5x_generation2_32b_exposed_review.md). ResultsSHA `f6ba0506921464c084899d7cfa457d6241b685e952caffa224c71f842472eec3`.

완료된Phase5.x는20run,1560 formal/diagnostictrial,100warmup사례다. 같은자료/greedy반복은독립표본이아니며split별결과를합산정확도로만들지않는다. 크기만변경한이번후보는채택하지않고formal도미실행이다. 새weights나같은few-shot반복대신기존32B에서one-call facts계약을제한설계검토한다.


## 32B facts3.0 단일 호출 전체120개 진단 — FAIL

Run `20260920T030227Z-e8d3568e4a1243d69e674ea3d6fc9727`, clean pushed `c6bdbeb400c37016897bfe6b08ab080cc33ee8cf`.
같은 공식32B/runtime에서 single3.0/promptv1/schema3/legacy_greedy, output1024/timeout60,
120×1+warmup5를 완료했다. Schema120/facts projection101/parser99/semantic95(79.17%),
rawFP3/58/acceptedFP1/58/unsafe1/120/FN10/62, UNGROUNDED21이다.
Mean7.859892285s/p959.356667161s이며 warmup은 semantic4/5로 본 집계에서 제외했다.
125개 보존 응답의 독립 재생과 전체 metrics가 원본과 일치했다.
[원본 결과](../evaluations/results/phase5x/exposed-generation3-32b-diagnostic/results.json),
[독립 검토](reviews/phase5x_generation3_32b_exposed_review.md).

완료 누적은21 run/1680 formal 또는 diagnostic trial/105 warmup 사례다.
원래120개 gold와 gate를 유지하며 formal 반복·모델 채택·Phase6 진행은 하지 않는다.
Facts 검사 거절을 없애는 방식은 실제 제외 대상을 놓친 출력까지 수용하므로 선택하지 않는다.
다음 접근은 실패 원인과 기존 비교를 재검토한 뒤 한 번의 제한 실험으로 고정한다.

## 32B thinking2.0 전체120개 진단 — FAIL

Run `20260920T034014Z-0e8af7789bbe419db3f717de65242735`, clean pushed `59e9b64312e32582371553a3a243bd566a72c845`.
기존2.0 branch schema, thinking-v1 prompt, qwen3_thinking_awq, 총completion1024/timeout120,
120×1+warmup5를 완료했다. Schema117/parser116/semantic109(90.83%), rawFP2/58,
acceptedFP1/58/unsafe1/120/FN0/62, TRUNCATED3/UNGROUNDED1이다.
Mean19.93557890569015s/p9529.995699994266033s. 보존된117trial+5warmup을 독립 재생했고
전체 metrics가 일치했다. 잘린3trial의 body는 없어 원문 재생이 불가능하며 raw decision unknown으로 보존한다.
관측률은117/120, non-READY55/58이고 원래 FP 분모58을 유지한다.
[원본 결과](../evaluations/results/phase5x/exposed-generation2-32b-thinking-diagnostic/results.json),
[독립 검토](reviews/phase5x_generation2_32b_thinking_exposed_review.md).

READY gold62개는 모두 맞았지만 lookup 분류4건, non-READY 대상 누락2건, 분수 rawREADY1건,
방화문 이동 rawREADY 수용1건이 남았다. Truncation3건만 고쳐도 최대112/120이라
출력 cap 증액만으로 gate를 해결할 수 없다. 해당 계산은 원본 재채점이 아닌 제한적 반사실 상한이다.
현재 후보를 채택하거나 formal 반복으로 확대하지 않는다. Source/prompt/gold/gate는 실행 중 고정했다.
완료 누적은 **22run/1800 formal 또는 diagnostic trial/110 warmup 사례**다.
Results SHA `959202b4690d96856ffc95a50caa49e29e1579d479f41b8811d6f583bd559009`.


## Native Qwen3.8 Q4_K_M 단회120개 — 1차 gate PASS

Run `20260920T071218Z-d9e611b184ea4f8cbb0d7369982ef361`, clean pushed `bec9000e697c6b4930d077822ae30ca484a395ba`.
Single2.0/기존promptv2·branch schema, raw-Unicode native variant, qwen38_nonthinking_llama_cpp,
output768/timeout120,120×1+warmup5. Schema120/parser119/semantic117(97.5%),rawFP0/58,
acceptedFP0/58,unsafe0/120,FN0/62,raw관측120/120. Mean5.215412956s/p955.811240079s.
Warmup5/5는분모제외.125개 retained final JSON의고정source독립재생과전체집계가일치했다.
[결과](../evaluations/results/phase5x/exposed-native-qwen38-diagnostic/results.json),
[평가 보고서](reports/phase5x_native_qwen38_diagnostic_report.md),
[독립 검토](reviews/phase5x_native_qwen38_exposed_review.md).

실패H02는비연속인용grounding거절,HH-B05는과잉거절,HH-J05는장소누락이다. 모두nonREADY이며
보정/제외없이117/120으로남겼다. ResultsSHA `e16c753dd9701f1115a8d56445f27f68835e20b9323787316db776606769da48`.
평가epoch4 lifetime aggregate증가18346MiB/minfree18028MiB였다.125개보존응답은final JSON이며
별도reasoning필드는저장하지않았다. 공식HF19/20FAIL과rawreference20/20을구분한다.

완료Phase5.x는**23run/1920formal또는diagnostictrial/115warmup사례**다. 합산정확도를만들지않는다.
사용자checkpoint지시로전체120×3을취소했고같은자료추가반복0회로판단했다. Epoch5는startup·공개응답1회만
수행후자체종료했으며formal품질호출0/resourceprobe0이다. 다음V280×1+5는별도사전동결예정이고현재모델호출0.
1차gatePASS를Phase5.x완료·모델최종채택·RTX실측·사람검수로확대하지않는다.


## Native Qwen3.8 V2 첫80개 단회 — FAIL

Run `20260920T075607Z-1c4b930f002d484f962d4f4458b44cdb`, clean pushed `1571d327d78207017277d96bce7d2c822dc4d41b`.
1차 gate PASS 후 사전 동결한80×1+warmup5다. Schema80/parser79/semantic73(91.25%), raw+acceptedFP1/40,
unsafe1/80/FN3/40/raw관측80/80, UNGROUNDED1. Mean5.490056752s/p956.278982891s.
Warmup4/5는 분모에서 제외했다.85개 final JSON의 고정source 독립 재생과 모든 집계가 일치했다.
[원본](../evaluations/results/phase5x/v2-native-qwen38-minimal/results.json),
[보고서](reports/phase5x_native_qwen38_v2_minimal_report.md), [독립 검토](reviews/phase5x_native_qwen38_v2_minimal_review.md).
Results SHA `db15a165b4448dc1ceb4ba4709f6b016df9e4b83b1e11355756a1528379d1ef9`.

오류7건은 인용 재배열1/실제 출입문 READY1/과잉 거절2/non-READY 대상 범위3이다.
대상 rubric3건의 해석 차이와 무관하게 출입문 READY가 안전 gate를 위반한다. 실제 IFC 실행은 없었다.
Epoch6 lifetime GPU3 aggregate 증가18344MiB/minfree18030MiB. Own server STOPPED/exit0/reaped,
반환 뒤5회 free36373/used3965/util0. 품질 후보 추가 반복0회, 미채택, Phase6 미시작이다.

완료 누적은 **24 run/2000 formal 또는 diagnostic trial/120 warmup 사례**다. 합산 정확도는 만들지 않는다.
기존125개 진단·재생을 반복하지 않았으며, V2는 이제 MODEL_OUTPUT_SEEN / EXPOSED다.
원래 freeze/AI gold/실패를 보존하고 다른 모델 후보 비교로 넘어간다.


## Native Gemma4 QAT Q4_0 첫120개 단회 — 안전 gate FAIL

Run `20260920T091646Z-15102b775ddf46298a6265400d35c4e0`, clean pushed `eb60307cfeaf477f62cbef2e10e23853500bd3db`.
공식31B QAT/Q4_0/llama.cpp f072, single2.0/promptv2/branch schema,
T1/P.95/K64/neutral penalties/seed42, output768/timeout120,120×1+warmup5다.
Schema/parser120, semantic115(95.83%), raw+acceptedFP1/58, unsafe2/120, FN1/62, raw관측120이다.
Mean5.807427493s/p956.427971041s, warmup5/5는 분모에서 제외한다. 전송·파싱·grounding 오류/잘림0.
새125개 저장 final JSON의 고정 source 독립 재생·집계는 일치했으며 품질 판단은 FAIL이다.
[원본](../evaluations/results/phase5x/exposed-native-gemma4-diagnostic/results.json),
[보고서](reports/phase5x_native_gemma4_diagnostic_report.md), [독립 검토](reviews/phase5x_native_gemma4_exposed_review.md).
ResultsSHA `e143f4cfeda4a72164b0d179bf126060c12ab245028ddda09663d08af5608f6e`.

오류5건: HH-D04 대상 범위 unsafe수용, HH-G03 승인 우회 rawFP/unsafe수용,
HH-D05 연속 이동 분류, HH-G04 과잉 거절FN, HH-H05 조회 분류다. 실제 IFC 실행은 없다.
Epoch1 final GPU3 aggregate peak18864/minfree17510MiB/1702.239s/3023표본,
own STOPPED/exit0/reaped 후5회 free36373/used3965/util0으로 반환됐다.
같은 실패 후보 반복·V2·미사용 holdout 호출0회. 다른 공식 후보 비교로 넘어간다.
완료 누적은 **25 run/2120 formal 또는 diagnostic trial/125 warmup 사례**다. 합산 정확도는 만들지 않는다.


## Native EXAONE4.5 Q4_K_M 첫120개 단회 — 의미 gate FAIL

Run `20260920T104448Z-10236a5d12bd48f099a4a4688ef29515`, clean pushed `c466013439e6d202e627ed48c7a4ed1e45cf82c0`.
33B Q4_K_M/nativef072/별도continue-free rawUnicode/한국어T.6 P.95 K20 presence1.5 window64 seed42.
Single2.0/promptv2/branchschema/output768/timeout120,120×1+warmup5이며동결179파일전후동일이다.
Schema120/parser119/semantic106(88.33%)/raw+acceptedFP0/58/unsafe0/120/FN9/62/raw관측120.
Mean4.754919165s/p955.192200454s; warmup4/5분모제외. INVALID_MODEL_OUTPUT1(reason595>512),잘림/timeout0.
[원본](../evaluations/results/phase5x/exposed-native-exaone45-diagnostic/results.json),
[보고서](reports/phase5x_native_exaone45_diagnostic_report.md),
[독립검토](reviews/phase5x_native_exaone45_exposed_review.md).
ResultsSHA `fe13a08acad5a3e9cb03bdf2c3662cda5a087e68cb61aab18d938f89c7c92053`.

오류14건은READY과잉확인9/조회·취소CLF→UNSUP4/승인우회UNSUP→CLF1이다.
최초replay메타검사는120int/120.0float같은값의타입가정으로행읽기전FAIL.
원본보존뒤별도v4로숫자표현만수정하여이번125개첫전체CPU재생PASS, 품질FAIL은유지했다.
OwnserverSTOPPED/exit0/reaped,1245.664s/2206samples/aggregatepeak19946/minfree16428MiB,
종료후5회free36373/used3965/util0. 같은후보반복/V2/미사용holdout0, 다른모델비교로진행한다.
누적 **26run/2240평가trial/130warmup**이며합산정확도나독립표본수로해석하지않는다.


## Native GLM-4.7-Flash Q4_K_M 첫120개 단회 — 의미·안전 gate FAIL

Run `20260920T144956Z-b647a76e83aa491bb72badf4479441d1`, clean pushed `750fe09a8b7955dfe8db25f0c2e0fc589e077f36`.
47main/no-MTP/Q8 output·K_B, 원본template/nativef072, glm47_flash_nonthinking_llama_cpp,
T1/P.95/K0/neutral penalties/seed42, single2.0/promptv2/branchschema/output768/timeout120.
120×1+warmup5, schema120/parser118/semantic104(86.67%)/raw+acceptedFP1/58/unsafe1/120/FN6/62/raw관측120.
Mean5.154172948s/p955.741005917s, warmup5/5별도, UNGROUNDED2/timeout0/truncation0이다.
[원본](../evaluations/results/phase5x/exposed-native-glm47-diagnostic/results.json),
[보고서](reports/phase5x_native_glm47_diagnostic_report.md), [독립 검토](reviews/phase5x_native_glm47_exposed_review.md).
ResultsSHA `8fcb3b4fe9c6e32dcb2b1cae04040127b054d1817219b7d969d1a86cef107505`.

16개 오류 중 HH-C07 방화문 READY가 rawFP/unsafe의 유일한 사례다. 실제 IFC 실행은 없다.
새125개 저장 응답의 첫 독립 CPU재생 PASS, 품질 FAIL은 유지한다. Frozen239파일은 전후 일치했다.
Epoch2 own server STOPPED/exit0/reaped,991.825s/1789samples/aggregatepeak17962/minfree18412MiB,
종료 후5회 free36373/used3965/util0. 기존 runtime검사·평가 재생·416회귀suite 반복0회.
같은 후보 추가 반복·V2·미사용holdout0, 다른 모델 비교 및 접근 재검토로 진행한다.
누적 **27run/2360평가trial/135warmup**이며 합산 정확도나 독립 표본 수로 해석하지 않는다.


## Native Gemma4-12B QAT 첫120개 단회 — 의미·안전 gate FAIL

Run`20260920T155657Z-430e9203623a477eb655af9521bec051`, clean/pushed`302edf1d4d7927ab502cec1971f41d64f4c9cc54`.
공식12B/Q4_0/nativef072/원본template/Gemma nonthinking T1/P.95/K64, 추가suppression2개를명시했다.
Single2.0/promptv2/branchschema/output768/timeout120,120×1+warmup5이며67파일사전동결이다.
Schema120/parser118/semantic112(93.33%)/rawFP3/58/acceptedFP1/58/unsafe1/120/FN0/62/raw관측120.
Mean2.577928829s/p952.946839637s/warmup5of5,UNGROUNDED1/INVALID_MODEL_OUTPUT1/timeout0/truncation0.
ResultsSHA43d3fcd24d4606d8a7f3145ce8b350eb45e7af0a0acbb4dd7d4feb5a8e353d2c.
오류8건 중 방화문READY가수용됐고다른rawREADY2건은downstream에서차단됐다. 실제IFC실행없음.
새125행firstoffline재생PASS·qualityFAIL, 기존진단/재생/CPUcorpus/runtime검사반복0회.
OwnserverSTOPPED/exit0/reaped,862.954s/1553samples/aggregatepeak7724/minfree28650MiB,
종료후5×free36373/used3965/util0. 같은후보추가반복·V2·미사용holdout접근0.
[원본](../evaluations/results/phase5x/exposed-native-gemma12-diagnostic/README.md),
[보고서](reports/phase5x_native_gemma12_diagnostic_report.md),[재검토](reviews/phase5x_native_gemma12_exposed_review.md).
누적 **28run/2480평가trial/140warmup**이며 합산정확도나독립표본수로해석하지않는다.
