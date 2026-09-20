# NeuroBuild_v2 실행 상태

갱신: **2026-09-20 15:33 KST**. **Phase 0~5 원격 checkpoint 완료. Phase5.x 품질 gate는 미통과이며 Internal Technical MVP는 아직 완료되지 않았다.**

| 항목 | 현재 상태 |
|---|---|
| 완료 Phase | 0 Foundation, 1 Domain, 2 Persistence, 3 IFC Engine, 4 Explicit Workflow, 5 Local Model |
| 마지막 완료 Phase checkpoint | `d6e39c89658c552c59a8049d7198da051290bd3b` |
| GitHub | 공통 `v2`, 마지막 원격 확인 `52ffb5a2847e15ef79678fce54625dfb7f59841e` |
| 회귀 검증 | **382 tests PASS**, skip 0, 실제 PostgreSQL/IfcOpenShell, headless 20.178초 |
| 현재 작업 | **Native runtime 첫 GPU3 startup SIGABRT 원인 진단**. 최종 모델 미채택, Phase6 시작 전 |
| 잠정 모델 | Phase5 작은 seed 범위의 Qwen3-14B-AWQ/v3. 확대 gate 통과를 뜻하지 않음 |
| Hard blocker | 없음. 품질 문제를 해결 중. CUDA 빌드·정적 검사 및 native guard CPU 검증 통과. GGUF/header·raw-native context200 통과. 첫 GPU startup은 SIGABRT로 실패, 자체 정리 완료; 원인 진단 중 |
| Backend | `.conda`: Python3.12.14 / PostgreSQL17.11 / psycopg3.2.10 / IfcOpenShell0.8.5 |
| Model runtime | `.conda-vllm`: Python3.12.14 / cu118 vLLM0.8.5 / Torch2.6.0. 모든 자체 model server STOPPED |
| 다음 검증 | 시작 실패의 제한된 진단 후 fresh GPU3 예산 재검사. 공식 HF19/20 FAIL과 raw variant를 분리하며 gold·parser·gate 유지 |

## 최근 품질 결과

| 구성·자료 | 의미 정확도 | Raw READY 오판 | 잘못 수용한 READY | 결과 |
|---|---:|---:|---:|---|
| MoE generation2 첫 holdout80×3 | 211/240 | 9/114 | 12/240 | FAIL |
| 14B single2.0, exposed120×1 | 113/120 | 2/58 | 3/120 | FAIL |
| 14B staged, exposed120×1 | 93/120 | 11/58 | 6/120 | FAIL |
| 32B single2.0, exposed120×1 | 103/120 | 1/58 | 1/120 | FAIL |
| 32B facts3.0, exposed120×1 | 95/120 | 3/58 | 1/120 | FAIL |
| 32B thinking2.0, exposed120×1 | **109/120** | **2/58** | **1/120** | **FAIL** |

Thinking 진단은 schema117/parser116/FN0이며 truncation3건과 grounding 거절1건이 있었다.
READY gold62개는 모두 맞았지만 방화문 이동 수용, 분수 표현 READY, lookup 분류와 대상 누락이 남았다.
잘린3건은 raw decision unknown이다. 전체 관측117/120·non-READY 관측55/58을 함께 보존하며,
2/58은 미관측3건의 안전성을 보장하지 않는다. 보존된117trial+5warmup의 독립 재생과 원래 집계가 일치했다.
[상세 검토](reviews/phase5x_generation2_32b_thinking_exposed_review.md), [전체 실험 목록](phase5x_experiment_register.md).

완료된 Phase5.x 기록은 **22 run / 1,800 평가 trial / 110 warmup 사례**다.
서로 다른 split과 반복 실행을 합산한 정확도나 독립 표본 수로 해석하지 않는다.
Gate는 **schema100% / semantic≥95% / raw READY 오판0 / 잘못 수용한 READY0**이다.
기존120개는 노출된 regression이며 새로운 unseen 자료가 아니다.
V2 80개는 모델 호출0이지만 root가 일부 입력/gold를 본 이력이 있다.
[노출 기록](../evaluations/hardening_v2_input_exposure_addendum.json)을 유지하며 완전 맹검이라고 부르지 않는다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**이며 AI 검토는 사람 검수가 아니다.

## 운영 상태와 남은 범위

**GPU3만 사용한다.** 마지막32B thinking epoch는 own guard3483689/child3483717의 UID·시작 시각·실행 인자를
확인한 뒤 종료했다. STOPPED/exit0/reaped/FileStore 정리와 TERM→KILL 기록을 보존했다.
Epoch3144.173초 동안 GPU 전체 baseline 대비 증가 최대22,542MiB, 최소 free13,832MiB였다.
이는 process별 peak나 hard isolation이 아니다. 종료 후 GPU3 used3,965MiB/free36,373MiB/util0%다.
다른 사용자의 process와 GPU0/1/2는 변경하지 않았다.

Private PostgreSQL은 project 안의0700 Unix socket과 peer 인증을 사용하며 TCP는 비활성이다.
CUDA11.8/SM80 source build와 `$ORIGIN` relink, source3,607개/ELF/library 정적 검사를 통과했다.
GPU startup 성공은 아직 아니다. 단일 후보 다운로드·헤더 검사와 독립 CPU helper 빌드는 완료했다.
공개 CPU 문법30개 및 native final-content/sampling 검사는 통과했다. 공식 HF와의 NFC 차이로
19/20 동등성 검사는 FAIL이며 raw variant의20/20 공개 비교와 실제 native context200개는 PASS다.
노출120 input+768 최대3177/v2길이80 최대3133으로4096 이내다. 입력·출력 보정은 없다.
382개 회귀 검사가 native guard 및 다운로드 파일 덮어쓰기 방지 수정까지 포함한다.

종료된 MoE의 검증된 가중치4개(16,809,467,824 bytes)를 정리했고 당시 free는 약42.4GiB였다.
기존4B 정리와 이번 MoE의 manifest·복원 명령·평가 자료는 보존한다. 14B/32B 가중치는 유지했다.
Qwen3.8 GGUF17.67GiB의 전체 SHA/851 tensor 검사를 통과했다. 다운로드 후 약24.65GiB free로
20GiB+512MiB reserve를 유지했다. GPU3 드라이버 metadata만 조회해 VMM/2MiB granularity를
확인했으며 context/메모리 할당은 요청하지 않았다. 전체 예상 peak28GiB와 별도 margin을
[자원 검증 계획](native_qwen38_resource_plan.md)에 기록했다. CPU gate와 fresh5회 검사를 통과한 첫 시작은7.781초 만에SIGABRT(-6)로 종료했다.
관측 최소 free18,084MiB/aggregate 증가18,290MiB였으며 자체 child 정리 후36,373MiB로 복귀했다.
HTTP 평가 요청0, stdout/stderr 폐기·core0이며 원인을 단정하지 않고 제한된 진단을 준비한다.
[후보와 현재 검증](modern_local_runtime_candidate.md)은 모델 품질 또는 GPU 실행 성공을 뜻하지 않는다.
환경·weight·cache·binary는 Git에서 제외한다.

Phase4 human review는 아직 메모리에만 보존한다. Object resolution/API/browser는 미구현이며
영속 review/queue/worker는 Phase7 예정이다. **RTX5090은 PREDICTED_UNVERIFIED**다.
Public exposure/pilot/민감 IFC/fine-tuning은 자동 범위 밖이다.
