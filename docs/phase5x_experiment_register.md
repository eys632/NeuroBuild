# Phase 5.x 실제 평가 실행 목록

2026-09-20 KST 작성. **AUTO-GENERATED / NOT HUMAN VERIFIED**. 작성 시 보존된 development 실행 **11개, 평가 응답 600개**를 모두 정리했다. Launch/runtime/shutdown 기록과 protocol smoke는 평가 run에서 제외했다. 각 run의 warmup 5개, 총55개도 아래 분모에 포함하지 않는다.

**모든 run이 품질 gate를 충족하지 못했다.** 최고 의미 정확도는 4B Instruct/v3/N의 **37/40 (92.5%)**이며 raw FP1건과 unsafe accepted2건이 남았다. 고정 gate는 schema100%, 의미 정확도95% 이상, raw FP0, unsafe accepted0이다. 단회 진단40개는 정식 development40×3 평가나 holdout80×3 평가를 대신하지 않는다. **Holdout 추론은 아직 수행하지 않았다.**

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

## 설정 해석

- **14B AWQ**: `Qwen/Qwen3-14B-AWQ`, revision `31c69efc29464b6bb0aee1398b5a7b50a99340c3`.
- **4B Instruct BF16**: `Qwen/Qwen3-4B-Instruct-2507`, revision `cdbee75f17c01a7cc42f958dc650907174af0554`.
- **30B-A3B Instruct AWQ**: 제3자 `ELVISIO/Qwen3-30B-A3B-Instruct-2507-AWQ`, revision `9f41ff709102dbe73e614f9365f8280170db268e`.
- 공통: A100 GPU3, vLLM0.8.5+cu118, context4096, TP1, concurrency1, `legacy_guided_json`/`xgrammar:no-fallback`, 요청마다 seed42. Thinking run만 `deepseek_r1` parser를 사용했다.
- 출력 상한/timeout: v6는2048/120초, v7은1280/120초, 나머지는768/60초다. Thinking 출력 상한에는 내부 reasoning과 final을 모두 포함하며, reasoning 본문은 보존하지 않는다.

| 표기 | 요청 sampling profile | T | top_p | top_k | min_p | presence | frequency | repetition |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| G / G* | `legacy_greedy`에 해당하는 T0/seed42 요청 | 0 | 생략 | 생략 | 생략 | 생략 | 생략 | 생략 |
| A | `qwen3_nonthinking_awq` | 0.7 | 0.8 | 20 | 0 | 1.5 | 0 | 1 |
| T | `qwen3_thinking_awq` | 0.6 | 0.95 | 20 | 0 | 1.5 | 0 | 1 |
| N | `qwen3_nonthinking` | 0.7 | 0.8 | 20 | 0 | 0 | 0 | 1 |

G*인 최초3개 manifest에는 profile 이름 필드가 없으며 기록된 temperature0/seed42를 기준으로 분류했다. 생략한 항목은 서버·모델 기본값을 따르므로 명시적으로 통제했다고 주장하지 않는다. 모델·정밀도·prompt·sampling·thinking·출력 예산의 변경이 섞여 있어 단일 요인의 효과로 전체 차이를 설명할 수 없다. 각 run의 정확한 prompt/schema/client/parser/scorer/runtime hash와 Git 상태는 연결한 manifest에 있다. V5, 4B/v3/N 및 MoE/v3의 `git.dirty=true` 기록도 그대로 보존한다.

## 등록 시 재검증과 한계

11개 `results.json`의 평가 trial만 읽어 현재 `summarize`를 각각 CPU에서 재실행했고, **전체 metrics 객체가 원본과 정확히 일치**했다. Manifest/result run ID, development split,40개×반복 횟수, warmup5개, dataset hash와 현재 보존된 prompt hash도 대조했다. 재집계에 사용한 scorer SHA는 `eff1da86d84775f6bb394b7c4ebbae104a91196a41f6dcac01c145ef0c67a1cc`다. 이는 저장된 trial 판정의 집계 재검증이며 모든 응답을 새로 추론하거나 parser로 재판정한 검증, 사람의 의미 검수는 아니다. 원본 파일은 수정하지 않았다.

같은40개와 고정 seed를 반복했으므로600회를 독립 표본으로 해석하지 않는다. Development 결과로 prompt와 모델을 선택했으며, synthetic gold와 좁은 작업 문법의 한계가 있다. Holdout 입력·gold의 사전 AI 검토도 맹검이나 사람 검수가 아니다. Raw READY 관측이 불가능한 응답은 오판0의 증거가 아니며 원본의 관측률/오류 지표를 함께 봐야 한다.

이 평가는 semantic JSON 추출만 수행했다. **실제 IFC 변경·GlobalId 확정·대상 확인·proposal 승인은 수행하지 않았다.** 평균/p95는 저장된 HTTP end-to-end 측정의 재집계이며 TTFT나 순수 decode 시간이 아니다. Resource report는 GPU 전체 사용량 관측으로, 정확한 process별 VRAM peak를 측정한 것이 아니다. RTX5090 실행 검증도 없다.

## 다음 비교 — 평가 결과 아님

MoE/v3 진단은 실제 기동 후 실패했으며 위 완료 표에 포함했다. 같은 checkpoint/runtime/sampling에서 기존 v4를 비교할 준비 중이다. v4의 CPU 입력 길이는 검증했지만 모델 품질 수치는 아직 없다. [후보 및 runtime 근거](moe_instruction_candidate.md), [고정 manifest](../runtime/models/qwen3-30b-a3b-instruct-2507-awq.json).

실패 원인과 다음 판단의 상세 근거는 [Phase 5.x 보고서](reports/phase5x_report.md)를 따른다. 이 목록은 Phase 5.x 완료나 최종 모델 채택을 선언하지 않는다.
