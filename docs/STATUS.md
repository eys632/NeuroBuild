# NeuroBuild_v2 실행 상태

갱신: **2026-09-20 04:32 KST**. **Phase 0~4 원격 checkpoint 완료 / Phase5 가용량 기반 공존 실행 준비**.

| 항목 | 현재 상태 |
|---|---|
| 완료 Phase | 0 Foundation, 1 Domain, 2 Persistence, 3 IFC Engine, 4 Explicit Workflow |
| 마지막 완료 Phase checkpoint | `dd58b596fab2aaa24c5aba4322d56bc5d127440c` — Phase4 commit/push, remote hash 일치 |
| GitHub | 공통 `v2`, SSH push 정상. 이 상태 보고 자체의 최신 commit은 `git log -1` 참고 |
| 검증 | 전체 **108 tests PASS**, skip0, 실제 PostgreSQL/IfcOpenShell 포함, DISPLAY 없이 실행 |
| 현재 Phase | 5: GPU 실행 전 조사 완료. runtime 설치/startup/inference/benchmark 미실행 |
| Hard blocker | 점유 존재 자체의 blocker는 사용자 지침으로 해제. 후보 peak+margin/ABI 검증 중 |
| Backend | `.conda` Python3.12.14 / PostgreSQL17.11 / psycopg3.2.10 / IfcOpenShell0.8.5 Conda build |
| Model Runtime | `.conda-vllm` Python3.12.14 생성. cu118 vLLM0.8.5/Torch2.6.0 설치 및 Qwen3-14B-AWQ 다운로드 진행; startup/선정 미완료 |
| 다음 단계 | 공식 cu118 runtime import/단일 GPU3 guard 검증, 14B-AWQ startup 및 한국어 평가 |

## 완료 근거

- Phase1 `e68baa4`: Domain29 tests.
- Phase2 `18c7e21`: immutable artifacts/PostgreSQL intent·CAS·idempotency, 실제 프로젝트 PostgreSQL 종료·재시작 후 데이터 보존.
- Phase3 `56926a0`: 실제 IFC4 m/cm/mm·회전 부모·headless mesh 이동, 비대상/원본/GlobalId/Z/rotation/storey 보존, 미지원·잘못된 입력·정밀도 손실 거절.
- Phase4 `dd58b59`: 실제 inventory 대상 확인과 별도 제안 승인, Apply→V1, stale/duplicate/concurrency/실패·응답 유실 복구.
- 최종 회귀: Domain29 + Artifact20 + IFC25 + Persistence13 + Workflow21 = **108 PASS**(12.378s). 독립 workflow21 및 추가 real-PG probe4/4 PASS.
- 상세: [Phase4 보고](reports/phase4_report.md), [Phase5 blocker](reports/phase5_report.md).

## 중단 조건과 재개

GPU3: A100-PCIE-40GB, driver535.183.01, total40960/used3965/free36373MiB, utilization0%. Process3개는 현재 사용자 소유 PID 목록에 포함되지 않았다. 소유자 신원·파일·환경은 조회하지 않았고 종료/변경하지 않았다. Phase0에서도 process3개/3965MiB가 관측됐으며 이번 Phase5에서도 계속 남아 있다.

2026-09-20 최신 사용자 지침에 따라 **점유 존재만으로 중단하지 않는다**. GPU3에서 free VRAM/utilization을 10초간6회 재확인했고 모두 free36373MiB/util0%였다. 후보 전체 startup/inference peak와 안전 margin을 비교하여 충분한 경우만 테스트한다. 타인 process/환경은 변경하지 않고 GPU0/1/2 fallback은 금지한다.

Backend는 재사용하고 Model Runtime만 별도 .conda-vllm에 둔다. 실제 startup/inference/평가를 통과하기 전 Phase5 gate나 모델 선정을 완료로 표시하지 않는다. 이전 중단 경위는 Phase5 report의 historical section에 보존했다.

## 현재 운영 상태와 미완료 범위

프로젝트 PostgreSQL은 실행 중이며 private Unix socket `var/run/postgresql`만 사용한다. TCP listener가 없고 peer auth다. lifecycle은 `scripts/postgres.py`, 종료는 `.conda/bin/python scripts/postgres.py stop`이다. Root disk96%/약83G free, Backend1.4G/cache803M/PostgreSQL data82M.

Phase4 Human Review는 **메모리 상태**다. 재시작 후 review 복구/job queue/worker는 Phase7 범위다. LLM 의미 해석·자연어 object resolution·API·브라우저는 아직 구현하지 않았다. **Internal Technical MVP 완료가 아니다.** Phase5.x~11은 미시작이며 막힌 Phase를 우회하지 않는다.

RTX5090은 PREDICTED/UNVERIFIED, synthetic fixture/gold는 AUTO-GENERATED / NOT HUMAN VERIFIED다. Public exposure/pilot/민감 IFC/fine-tuning은 이번 자동 범위 밖이다.
