# NeuroBuild_v2 실행 상태

갱신: **2026-09-20 08:31 KST**. **Phase 0~5 원격 checkpoint 완료. Phase 5.x 평가 확대 진행 중이며, Internal Technical MVP는 아직 완료되지 않았다.**

| 항목 | 현재 상태 |
|---|---|
| 완료 Phase | 0 Foundation, 1 Domain, 2 Persistence, 3 IFC Engine, 4 Explicit Workflow, 5 Local Model |
| 마지막 완료 Phase checkpoint | `d6e39c89658c552c59a8049d7198da051290bd3b`: Phase 5 commit/push 및 remote hash 일치 |
| GitHub | 공통 `v2`, SSH push 정상. 마지막 확인 checkpoint `3a13b24` |
| 회귀 검증 | 전체 **290 tests PASS**, skip 0. 실제 PostgreSQL/IfcOpenShell, DISPLAY 없이 17.329초 |
| 현재 작업 | **MoE v4도34/40, raw FP1, 잘못 수용2로 실패. 별도 quote-only generation2 구현 및 전체 회귀290개 통과, 모델 진단 준비**. 기존1.0 parser/domain 및 gold/gate는 유지 |
| 잠정 모델 | Phase 5 범위의 **Qwen3-14B-AWQ + v3**. 확대 평가 gate 통과 전 최종 채택으로 보지 않음 |
| Hard blocker | 없음. GPU 3 가용량을 측정한 공존 실행 조건 통과 |
| Backend | `.conda`: Python 3.12.14 / PostgreSQL 17.11 / psycopg 3.2.10 / IfcOpenShell 0.8.5 |
| Model Runtime | `.conda-vllm`: Python 3.12.14 / cu118 vLLM 0.8.5 / Torch 2.6.0. 현재 MoE 후보 서버 가동. TP 1 / context 4096 / sequence 1 |
| 다음 검증 | 진단이 개선되면 같은 설정으로 development 40×3 평가. 이후 고정된 holdout 80×3 평가 |

## Phase 5.x 평가 상태

120개 자료를 development 40개와 holdout 80개로 고정했다. **Holdout은 아직 한 번도 모델에 호출하지 않았다.** 현재까지 확대 평가 gate를 통과한 후보는 없다.

| 최근 development 진단 | 의미 정확도 | Raw READY 오판 | 잘못 수용된 출력 | 판단 |
|---|---:|---:|---:|---|
| 4B Instruct + v3 | **37/40 (92.5%)** | 1/20 | 2/40 | 현재 최고 정확도이나 gate 미충족 |
| 4B Instruct + v4 | 34/40 (85%) | 1/20 | 3/40 | gate 미충족 |
| 4B Instruct + v8 | 36/40 (90%) | 1/20 | 2/40 | gate 미충족 |
| 4B Instruct + v3 greedy | 36/40 (90%) | 1/20 | 2/40 | gate 미충족 |
| 30B-A3B Instruct AWQ + v3 | 34/40 (85%) | 1/20 | 1/40 | gate 미충족 |
| 30B-A3B Instruct AWQ + v4 | 34/40 (85%) | 1/20 | 2/40 | gate 미충족 |

Raw READY 오판의 분모는 non-READY gold 20개이고, 잘못 수용된 출력의 분모는 전체 40개다. Backend가 수용한 결과에도 대상 범위 손실 등 의미 오류가 남아 있다. 40개 단회 진단은 정식 3회 평가를 대신하지 않는다. Gate는 **schema 100% / 의미 정확도 95% 이상 / raw READY 오판 0 / 잘못 수용된 출력 0**을 유지한다.

V8 run `20260919T223831Z-af6ebcd137394488a0adc427bd63edcf`는 schema 40/40, parser 39/40, FN 1/20이다. 세 프롬프트 비교 후 추가 prompt 수정을 중단했다. 기존 v3의 `legacy_greedy` profile 비교도 실패했다. 새 MoE 후보는 파일 검증과 fresh GPU3 예산 검사, 실제 기동 및 loopback 검증을 통과했다. [후보 근거](moe_instruction_candidate.md)와 고정 v3/neutral 진단 기록을 사용한다. 채택 전 실제 runtime·품질 검증이 남아 있다.

기존 14B의 prompt·sampling·thinking 실험과 4B 비교 결과는 실패를 포함해 보존했다. 상세 수치와 판단은 [Phase 5.x 보고서](reports/phase5x_report.md), [4B v3 독립 검토](reviews/phase5x_4b_v3_diagnostic_review.md), [v4 실패 및 v8 사전 검토](reviews/phase5x_4b_v4_v8_review.md)를 따른다.

## 완료 근거와 실제 한계

- Phase 1 `e68baa4`: Domain 검증. Phase 2 `18c7e21`: immutable artifact, PostgreSQL intent/CAS/idempotency 및 실제 재시작 검증.
- Phase 3 `56926a0`: IFC4 단위·회전 부모·headless mesh·불변 조건 검증. Phase 4 `dd58b59`: 대상 확인과 별도 승인, Apply V1, stale/duplicate/recovery 검증.
- Phase 5: 공개 seed 20×3에서 14B/v3 의미 정확도 60/60, READY 오판 0/33. 비교 8B는 54/60. 실제 5개 run의 결과·manifest·VRAM snapshot을 `evaluations/results/phase5/`에 보존했으며 독립 재계산을 통과했다. [Phase 5 보고서](reports/phase5_report.md), [독립 검토](reviews/phase5_final_review.md).
- Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. 반복 측정은 독립 표본이 아니며, 개발 자료와 holdout은 좁은 작업 문법을 공유한다. AI의 사전 gold 검토는 사람 검수나 맹검 평가가 아니다. [Holdout 해석과 절차](reviews/phase5x_holdout_protocol_review.md).

## 운영 상태

**GPU 3만 사용한다.** 이전 14B 서버는 자신의 guard와 child만 정상 종료했고, `neurobuild-instruct` alias의 4B BF16 서버도 자신의 guard를 통해 정상 종료했다. 현재 `neurobuild-moe` 후보 서버만 GPU3에서 실행한다. 예상 peak24,576MiB와 안전 여유7,275MiB로 재검사했고 v3 진단을 포함한 관측 최소 free는18,734MiB다. 다른 사용자의 프로세스·파일·환경은 변경하지 않았으며 다른 GPU로 fallback하지 않는다.

4B 시작 전 GPU 3 free 36,373MiB / utilization 0%에서 예상 전체 peak 16,384MiB와 margin 7,275MiB가 들어감을 확인했다. Guard의 free 하한은 **7,275MiB**, 현재 구간의 최종 관측 최소 free는 **26,530MiB**다. 종료 후 free 36,373MiB / utilization 0%로 복귀했다. 이는 GPU 전체 관측값이며 전용 메모리 예약이나 정확한 process peak 보장이 아니다. 기동 시 실제 TCP listener 5개가 모두 `127.0.0.1`임을 확인했다.

Private PostgreSQL은 `var/postgres`에 있으며, `0700` 권한의 `var/run/postgresql` 디렉터리 내 Unix socket과 peer 인증만 사용한다. TCP는 비활성이다. 마지막 디스크 확인에서 root filesystem 여유는 약 **39GiB (사용률 98%)**다. 환경·weight·cache는 프로젝트 내부에 두고 Git에서 제외하며, 다운로드 시 **20GiB reserve**와 설치 전 디스크 확인을 유지한다.

Phase 4의 human review 상태는 아직 메모리에만 보존한다. 영속 review/queue/worker는 Phase 7 예정이며 object resolution/API/browser도 아직 구현 전이다. **RTX5090은 PREDICTED_UNVERIFIED**이며 현장 검증이 필요하다. [Runtime protocol 및 SM120 검토](model_protocol_compatibility.md). Public exposure/pilot/민감 IFC/fine-tuning은 자동 범위 밖이다.
