# NeuroBuild_v2 실행 상태

갱신: **2026-09-20 12:39 KST**. **Phase 0~5 원격 checkpoint 완료. Phase5.x 품질 gate는 미통과이며 Internal Technical MVP는 아직 완료되지 않았다.**

| 항목 | 현재 상태 |
|---|---|
| 완료 Phase | 0 Foundation, 1 Domain, 2 Persistence, 3 IFC Engine, 4 Explicit Workflow, 5 Local Model |
| 마지막 완료 Phase checkpoint | `d6e39c89658c552c59a8049d7198da051290bd3b` |
| GitHub | 공통 `v2`, 마지막 원격 확인 `0fd60350b6e9df6538e5cf3d1ee1b13fa949fccc` |
| 회귀 검증 | **346 tests PASS**, skip 0, 실제 PostgreSQL/IfcOpenShell, headless 18.730초 |
| 현재 작업 | **32B facts3.0 FAIL 보존 완료, 같은32B의 기존2.0+thinking 제한 비교 준비**. 최종 모델 미채택, Phase6 시작 전 |
| 잠정 모델 | Phase5 작은 seed 범위의 Qwen3-14B-AWQ/v3. 확대 gate 통과를 뜻하지 않음 |
| Hard blocker | 없음. 품질 문제를 해결 중이며 GPU3 메모리 예산은 실행 가능했음 |
| Backend | `.conda`: Python3.12.14 / PostgreSQL17.11 / psycopg3.2.10 / IfcOpenShell0.8.5 |
| Model runtime | `.conda-vllm`: Python3.12.14 / cu118 vLLM0.8.5 / Torch2.6.0. 새32B thinking epoch RUNNING, 아직 품질 호출0 |
| 다음 검증 | 기존2.0+thinking, 총completion1024/timeout120의 단일 비교를 CPU 검증 PASS, runtime 검증 PASS, 동결·push 준비. Gold·parser·gate 유지 |

## 최근 품질 결과

| 구성·자료 | 의미 정확도 | Raw READY 오판 | 잘못 수용한 READY | 결과 |
|---|---:|---:|---:|---|
| MoE generation2 첫 holdout80×3 | 211/240 | 9/114 | 12/240 | FAIL |
| 14B single2.0, exposed120×1 | 113/120 | 2/58 | 3/120 | FAIL |
| 14B staged, exposed120×1 | 93/120 | 11/58 | 6/120 | FAIL |
| 32B single2.0, exposed120×1 | 103/120 | 1/58 | 1/120 | FAIL |
| 32B facts3.0, exposed120×1 | **95/120** | **3/58** | **1/120** | **FAIL** |

Facts3.0은 schema120, facts projection101, canonical parser99, FN10/62였다.
근거 검증 거절21건은 facts 단계19건과 기존2.0 단계2건이다. Raw 분류 정답은115/120이지만
잘못된 대상 범위·인용과 누락된 외부 조건이 남았다. 125개 응답의 독립 재생과 원래 집계가 일치했다.
정식 반복은 시작하지 않으며 구조 검사를 없애거나 decision을 보정해 실패를 감추지 않는다.
[상세 검토](reviews/phase5x_generation3_32b_exposed_review.md), [전체 실험 목록](phase5x_experiment_register.md).

완료된 Phase5.x 기록은 **21 run / 1,680 평가 trial / 105 warmup 사례**다.
서로 다른 split과 반복 실행을 합산한 정확도나 독립 표본 수로 해석하지 않는다.
Gate는 **schema100% / semantic≥95% / raw READY 오판0 / 잘못 수용한 READY0**이다.
기존120개는 노출된 regression이며 새로운 unseen 자료가 아니다.
V2 80개는 모델 호출0이지만 root가 일부 입력/gold를 본 이력이 있다.
[노출 기록](../evaluations/hardening_v2_input_exposure_addendum.json)을 유지하며 완전 맹검이라고 부르지 않는다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**이며 AI 검토는 사람 검수가 아니다.

## 운영 상태와 남은 범위

**GPU3만 사용한다.** 마지막32B facts epoch는 own guard3476219/child3476232의 UID·시작 시각·실행 인자를
확인한 뒤 종료했다. STOPPED/exit0/reaped/FileStore 정리를 확인했고 TERM→KILL escalation도 기록했다.
Epoch1402.678초 동안 GPU 전체 baseline 대비 증가 최대21,862MiB, 최소 free14,512MiB였다.
이는 process별 peak나 hard isolation이 아니다. 종료 후 GPU3 used3,965MiB/free36,373MiB/util0%다.
다른 사용자의 process와 GPU0/1/2는 변경하지 않았다.

Private PostgreSQL은 project 안의0700 Unix socket과 peer 인증을 사용하며 TCP는 비활성이다.
Root disk는 마지막 확인 약27.6GiB free(df28G/99%)이며 새로운 설치·다운로드는 없었다.
환경·weight·cache는 Git에서 제외한다. 사용을 마친4B weight 정리 이력과 복원 manifest는 보존했고
14B/MoE/32B weight는 다음 비교 판단 전까지 보존한다.

Phase4 human review는 아직 메모리에만 보존한다. Object resolution/API/browser는 미구현이며
영속 review/queue/worker는 Phase7 예정이다. **RTX5090은 PREDICTED_UNVERIFIED**다.
Public exposure/pilot/민감 IFC/fine-tuning은 자동 범위 밖이다.
