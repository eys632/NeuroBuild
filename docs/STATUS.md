# NeuroBuild_v2 실행 상태

갱신: **2026-09-20 KST — 단회 진단 PASS 보존, V2 최소 평가 FAIL**.
Phase0~5 원격 checkpoint는 완료했다. **Phase5.x 미완료, 현재 후보 미채택, Phase6 미시작**이다.

| 항목 | 현재 상태 |
|---|---|
| 완료 Phase | 0 Foundation, 1 Domain, 2 Persistence, 3 IFC Engine, 4 Explicit Workflow, 5 Local Model |
| 마지막 완료 Phase checkpoint | `d6e39c89658c552c59a8049d7198da051290bd3b` |
| GitHub | 공통 `v2`; 단회 결과 `704e9f6`, V2 실패 보존 `3a89af9ebab50058529405e38af0fa398d71d783` push·원격 일치 확인 |
| 현재 작업 | **V2 실패 checkpoint 완료, Gemma4-31B QAT 사전 검증** |
| 현재 후보 | Qwen3.8-27B Q4_K_M / pinned llama.cpp / raw-Unicode variant: V2 FAIL, 미채택 |
| 1차 품질 결과 | 노출120×1: schema120, parser119, semantic117, rawFP0/58, unsafe0/120 — PASS |
| V2 품질 결과 | 80×1: schema80, parser79, semantic73, rawFP1/40, unsafe1/80 — FAIL |
| 회귀 검증 | **395 tests PASS**, skip0, 실제 PostgreSQL/IfcOpenShell, headless19.339초. Gemma 명시profile 추가 검증 |
| Hard blocker | 없음. 품질 gate 미달로 Phase6 진행 불가, Phase5.x 다른 후보 검토 계속 |
| 모델 실행 | Epoch4·5·6 모두 STOPPED/exit0/reaped, GPU3 메모리 반환 확인 |
| Backend | `.conda`: Python3.12.14/PostgreSQL17.11/psycopg3.2.10/IfcOpenShell0.8.5 |
| 다음 검증 | Gemma4-31B QAT 공식 metadata·출력 계약·전체 VRAM 검증. 동일 실패 후보 반복0회 |

## 보존한 단회 결과와 오류3건

Run `20260920T071218Z-d9e611b184ea4f8cbb0d7369982ef361`의120개 평가와5개 warmup,
고정commit으로125개 final JSON을 독립 재생한 PASS 결과를 보존했다. 추가 평가·재생은 하지 않았다.
**의미 정확도117/120(97.5%), generation schema120/120, raw READY 오판0/58,
잘못 수용한 READY0/120, raw decision 관측120/120**이다. READY62개는 모두 정확히 수용했다.
Parser119/120을 그대로 보고하며 warmup5/5는 분모에서 제외한다.
HTTP end-to-end 평균 **5.215412956초**, p95 **5.811240079초**다.

오류3건은 H02의 비연속 인용 조합→grounding 거절, HH-B05의 CLARIFICATION→UNSUPPORTED 과잉 거절,
HH-J05의 대상 장소 누락이다. 모두 non-READY이며 실제 IFC 실행은 없었다. 오류를 수정하거나 제외하지 않았다.
[단회 보고서](reports/phase5x_native_qwen38_diagnostic_report.md),
[독립 검토](reviews/phase5x_native_qwen38_exposed_review.md).

## V2 첫80개 결과와 후보 판단

1차 gate 통과 후 별도 동결한 run `20260920T075607Z-1c4b930f002d484f962d4f4458b44cdb`를
80×1+warmup5로 완료했다. **Semantic73/80(91.25%) <76, rawFP1/40 >0, unsafe1/80 >0**이다.
Schema80/80, parser79/80, FN3/40, raw관측80/80, UNGROUNDED_REQUIREMENT1이다.
평균 **5.490056752초**, p95 **6.278982891초**. Warmup4/5는 별도다.
고정1571d32 source로85개 final JSON의 독립 CPU 재생과 전체 집계가 일치했다.

오류7건: H2-A02 인용 재배열1건, H2-C02 실제 출입문 READY1건, H2-G01/G07 과잉 거절2건,
H2-H05/J01/J05 non-READY 대상 범위 불일치3건이다. 마지막3건의 비실행 판정은 맞았다.
그3건을 가정상 모두 인정해도 출입문 READY로 안전 gate는 실패한다. 실제 객체 선택·승인·IFC 변경은 없었다.
명백한 기준 미달이므로 같은 후보를 반복하지 않고 다른 모델 후보 비교로 넘어간다.
[V2 보고서](reports/phase5x_native_qwen38_v2_minimal_report.md),
[독립 검토](reviews/phase5x_native_qwen38_v2_minimal_review.md), [실험 목록](phase5x_experiment_register.md).

완료 Phase5.x 기록은 **24 run /2,000 평가 trial /120 warmup 사례**다. 서로 다른 split·실행을
합산 정확도나 독립 표본 수로 해석하지 않는다. V2는 이제 **MODEL_OUTPUT_SEEN / EXPOSED**다.
이후 새 unseen 성공으로 표시하지 않는다. 이전 실패·기준·원본 freeze는 보존한다.

## GPU3 반환과 checkpoint

Epoch4 aggregate 증가 최대18,346MiB/최소 free18,028MiB,
epoch6은 **18,344MiB/18,030MiB**, 762.113초/1,349표본이다.
Safety floor7,275MiB/예상 peak28,672MiB를 유지했다. Process별 peak나 hard isolation은 아니다.
정식 반복용 epoch5 품질 호출은0회였다. Epoch6은 완료 검사를 재사용하고 현재 identity·health만 확인했다.
Own UID/시작시각/실행 인자/부모 관계를 확인해 해당guard에만 pidfd SIGTERM을 보냈다.
Guard는 자신이 만든 child group에 TERM과 잔여 group KILL 정리를 수행했고 child는 exit0으로 회수됐다.
다른 사용자 process 변경·종료 및 killall/광범위 pkill은 없었다.
Epoch6 종료 후5회 모두 **free36,373MiB/used3,965MiB/util0%**로 시작 전 수준에 돌아왔다.
GPU0/1/2는 사용하지 않았다. [종료 증거](../evaluations/results/phase5x/v2-native-qwen38-minimal/post_stop_gpu3.json).

## 반복 정책과 남은 범위

자동120×3·V2×3을 취소했다. 완료125개 평가·재생은 보존만 하며 반복하지 않는다.
통과/경계선인 경우에만 미확정 사실을 해결하는 최소 반복을 판단한다. 이번 V2는 명백한 FAIL이다.
Schema100%/semantic≥95%/rawFP0/unsafe0 기준은 유지한다. CPU 재생은 저장 응답의 처리 재현성이며
모델의 반복 출력 동일성 검증이 아니다. 완료 runtime/resource 검사를 처음부터 반복하지 않는다.
Phase를 막지 않는 batch/flash/graphs/cache/throughput 튜닝은 future optimization이다.

Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. Root의 일부 입력 노출도 보존하며 완전 맹검이라고 부르지 않는다.
공식 HF tokenizer19/20 FAIL과 별도 raw reference20/20을 구분하고 입력·출력 NFC 보정은 하지 않는다.
Private PostgreSQL은 project0700 Unix socket/peer 인증/TCP OFF다. 환경·weight·cache·binary는 Git에서 제외한다.
비활성 Qwen3-32B 가중치4개19,325,481,744B를 SHA/소유·사용 검사 후 회수했고 디스크 약42.8GiB free다.
Manifest/평가/복원 정보는 보존했다. 새 다운로드에도20GiB+512MiB reserve를 유지한다.
Phase4 human review는 아직 메모리 보존이며 Object resolution/API/browser는 미구현이다.
영속 review/queue/worker는 Phase7 예정이다. **RTX5090은 PREDICTED_UNVERIFIED**다.
Public exposure/pilot/민감 IFC/fine-tuning은 자동 범위 밖이다.

다음 후보는 [공식 후보 비교](next_model_candidate_comparison.md)의 Gemma4-31B QAT Q4_0다.
아직 품질·GPU 실행 미검증이며 기존 CUDA11.8/SM80 binary를 재사용할 수 있는지 모델별 계약을 확인한다.
공식 GGUF 다운로드는 고정SHA/디스크floor guard 아래 진행 중이다. GPU 모델 기동·품질 호출은 아직0이다.
새 후보의 준비를 기존 Qwen3.8 실패 수정이나 Phase5.x 완료로 표시하지 않는다.
