# NeuroBuild_v2 실행 상태

갱신: **2026-09-20 KST — 사용자 checkpoint**. **Phase0~5 원격 checkpoint 완료.
현재 Qwen3.8 후보는1차 품질 gate PASS이며 Phase5.x 전체 검증은 진행 중이다.**

| 항목 | 현재 상태 |
|---|---|
| 완료 Phase | 0 Foundation,1 Domain,2 Persistence,3 IFC Engine,4 Explicit Workflow,5 Local Model |
| 마지막 완료 Phase checkpoint | `d6e39c89658c552c59a8049d7198da051290bd3b` |
| GitHub | 공통 `v2`, 직전 원격 확인 `bec9000e697c6b4930d077822ae30ca484a395ba`; 이번 결과 checkpoint 준비 |
| 현재 작업 | **단회 진단·독립 재생 PASS 보존, 모델 서버 종료, checkpoint** |
| 현재 후보 | Qwen3.8-27B Q4_K_M / pinned llama.cpp / raw-Unicode variant, 최종 미채택 |
| 품질 결과 | 노출120×1: schema120,parser119,semantic117,rawFP0/58,unsafe0/120 |
| 회귀 검증 | **386 tests PASS**, skip0, 실제 PostgreSQL/IfcOpenShell,headless20.430초 |
| Hard blocker | 없음 |
| 모델 실행 | **NeuroBuild 모델 서버 STOPPED**, epoch4·5 exit0/child reaped |
| Backend | `.conda`: Python3.12.14/PostgreSQL17.11/psycopg3.2.10/IfcOpenShell0.8.5 |
| 다음 검증 | Checkpoint push 후 V2 80×1+warmup5 사전 동결. 같은120개 추가 반복0회 |

## 단회 결과와 오류

Run `20260920T071218Z-d9e611b184ea4f8cbb0d7369982ef361`의120개 평가와5개 warmup을
완료했고, 고정commit으로125개 final JSON을 독립 재생해 모든 단계·집계가 일치했다.
**의미 정확도117/120(97.5%), generation schema120/120, raw READY 오판0/58,
잘못 수용한 READY0/120, raw decision 관측120/120**이다. READY62개는 모두 정확히 수용했다.
Parser119/120은 그대로 보고하며 별도 사전100% gate가 아니었다. Warmup5/5는 분모에서 제외한다.
HTTP end-to-end 평균 **5.215412956초**, p95 **5.811240079초**다.

오류3건은 H02의 비연속 인용 조합→grounding 거절, HH-B05의 CLARIFICATION→UNSUPPORTED 과잉 거절,
HH-J05의 대상 장소 누락이다. 모두 non-READY이며 실행 오류는 없었다. 오류를 수정하거나 제외하지 않았다.
[평가 보고서](reports/phase5x_native_qwen38_diagnostic_report.md),
[독립 검토](reviews/phase5x_native_qwen38_exposed_review.md), [실험 목록](phase5x_experiment_register.md).

완료 Phase5.x 기록은 **23 run /1,920 평가 trial /115 warmup 사례**다. 서로 다른 split·실행을
합산 정확도나 독립 표본 수로 해석하지 않는다. 이전 실패와 기준은 그대로 보존한다.

## GPU3 반환과 checkpoint

평가 epoch4 전체의 GPU aggregate 증가 최대18,346MiB/최소 free18,028MiB,
safety floor7,275MiB/예상 peak28,672MiB였다. Process별 peak나 hard isolation이 아니다.
정식 반복용 epoch5의 품질 호출은 **0회**다. Startup 확인·공개 응답1회만 수행했고 resource probe는 미실행이다.
사용자 지시 후 own UID/시작시각/실행 인자/부모 관계를 확인해 해당guard에만 pidfd SIGTERM을 보냈다.
Epoch4와5 모두 STOPPED/exit0/reaped. 다른 사용자 process는 변경·종료하지 않았다.
GPU3 종료 후5회 모두 **free36,373MiB/used3,965MiB/util0%**이며 GPU0/1/2는 사용하지 않았다.

## 반복 정책과 남은 범위

사용자 최신 지시가 이전 자동120×3·V2×3 계획을 대체한다. 현재 단회 결과는1차4gate를 통과했다.
추가 같은 자료 반복 없이 checkpoint 뒤 동일 설정의 **V2 80×1+warmup5**를 사전 동결한다.
Schema100%/semantic≥95%/rawFP0/unsafe0 기준은 유지한다. 실제 모델의 반복 출력 동일성은 미검증이며
125개 CPU 재생을 그 증거로 대신하지 않는다. 이미 완료한 runtime/resource 검사를 처음부터 반복하지 않는다.
Phase를 막지 않는 batch/flash/graphs/cache/throughput 튜닝은 future optimization이다.

V2 모델 호출은 **0회**다. Root의 일부 입력/gold 노출 기록을 유지하며 완전 맹검이라고 부르지 않는다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**이고 AI 검토는 사람 검수가 아니다.
공식 HF tokenizer 비교19/20 FAIL과 별도 raw reference20/20을 구분한다. 입력·출력 NFC 보정은 없다.

Private PostgreSQL은 project0700 Unix socket/peer 인증/TCP OFF다. 환경·weight·cache·binary는 Git에서 제외한다.
모델 다운로드 뒤 디스크 약24.65GiB free로20GiB+512MiB reserve를 유지한다.
Phase4 human review는 아직 메모리 보존이며 Object resolution/API/browser는 미구현이다.
영속 review/queue/worker는 Phase7 예정이다. **RTX5090은 PREDICTED_UNVERIFIED**다.
Public exposure/pilot/민감 IFC/fine-tuning은 자동 범위 밖이다.
