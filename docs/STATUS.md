# NeuroBuild_v2 실행 상태

갱신: **2026-09-20 01:00 KST**. **Phase 0~4 원격 checkpoint 완료 / Phase 5 BLOCKED_GPU_OCCUPIED**.

| 항목 | 현재 상태 |
|---|---|
| 완료 Phase | 0 Foundation, 1 Domain, 2 Persistence, 3 IFC Engine, 4 Explicit Workflow |
| 마지막 완료 Phase checkpoint | `dd58b596fab2aaa24c5aba4322d56bc5d127440c` — Phase4 commit/push, remote hash 일치 |
| GitHub | 공통 `v2`, SSH push 정상. 이 상태 보고 자체의 최신 commit은 `git log -1` 참고 |
| 검증 | 전체 **108 tests PASS**, skip0, 실제 PostgreSQL/IfcOpenShell 포함, DISPLAY 없이 실행 |
| 현재 Phase | 5: GPU 실행 전 조사 완료. runtime 설치/startup/inference/benchmark 미실행 |
| Hard blocker | 허용 GPU3에 예상 밖 compute process3개, used3965MiB. 프로젝트 GPU 규칙에 따라 모델 실행 중단 |
| Backend | `.conda` Python3.12.14 / PostgreSQL17.11 / psycopg3.2.10 / IfcOpenShell0.8.5 Conda build |
| Model Runtime | `.conda-vllm` 미생성, torch/vLLM/Transformers/weight 미설치, 최종 model 미선정 |
| 다음 단계 | GPU3 사용 가능 시 점유/디스크/runtime ABI를 재확인하고 Phase5부터 재개 |

## 완료 근거

- Phase1 `e68baa4`: Domain29 tests.
- Phase2 `18c7e21`: immutable artifacts/PostgreSQL intent·CAS·idempotency, 실제 프로젝트 PostgreSQL 종료·재시작 후 데이터 보존.
- Phase3 `56926a0`: 실제 IFC4 m/cm/mm·회전 부모·headless mesh 이동, 비대상/원본/GlobalId/Z/rotation/storey 보존, 미지원·잘못된 입력·정밀도 손실 거절.
- Phase4 `dd58b59`: 실제 inventory 대상 확인과 별도 제안 승인, Apply→V1, stale/duplicate/concurrency/실패·응답 유실 복구.
- 최종 회귀: Domain29 + Artifact20 + IFC25 + Persistence13 + Workflow21 = **108 PASS**(12.378s). 독립 workflow21 및 추가 real-PG probe4/4 PASS.
- 상세: [Phase4 보고](reports/phase4_report.md), [Phase5 blocker](reports/phase5_report.md).

## 중단 조건과 재개

GPU3: A100-PCIE-40GB, driver535.183.01, total40960/used3965/free36373MiB, utilization0%. Process3개는 현재 사용자 소유 PID 목록에 포함되지 않았다. 소유자 신원·파일·환경은 조회하지 않았고 종료/변경하지 않았다. Phase0에서도 process3개/3965MiB가 관측됐으며 이번 Phase5에서도 계속 남아 있다.

이는 **VRAM이 물리적으로 부족하다고 확정한 결과가 아니라 공용 GPU 실행 정책의 blocker**다. Utilization0%를 사용 허가로 해석하지 않는다. [AGENTS.md](../AGENTS.md)의 “예상 밖 프로세스가 있으면 실행을 중단하고 보고한다” 규칙을 따른다. GPU0/1/2로 fallback하지 않는다.

GPU3 사용 가능 시:

1. 이 문서와 MASTER_PLAN/DECISIONS/EXECUTION_LOG, Git 상태를 읽는다. Phase1~4를 다시 구현하지 않는다.
2. GPU3만 재확인하고 디스크·환경/Python/pip/CONDA_PREFIX·model runtime의 driver/glibc/architecture 호환성을 조사한다.
3. 기존 `.conda`를 재사용하고 `.conda-vllm`은 검증한 runtime 요구에 맞춰 별도로 준비한다. 모델은 하나씩 평가한다.
4. 실제 startup/inference/NeuroBuild benchmark를 통과한 뒤 Phase5 gate/commit/push를 진행한다. 미측정을 성공으로 대체하지 않는다.

## 현재 운영 상태와 미완료 범위

프로젝트 PostgreSQL은 실행 중이며 private Unix socket `var/run/postgresql`만 사용한다. TCP listener가 없고 peer auth다. lifecycle은 `scripts/postgres.py`, 종료는 `.conda/bin/python scripts/postgres.py stop`이다. Root disk96%/약83G free, Backend1.4G/cache803M/PostgreSQL data82M.

Phase4 Human Review는 **메모리 상태**다. 재시작 후 review 복구/job queue/worker는 Phase7 범위다. LLM 의미 해석·자연어 object resolution·API·브라우저는 아직 구현하지 않았다. **Internal Technical MVP 완료가 아니다.** Phase5.x~11은 미시작이며 막힌 Phase를 우회하지 않는다.

RTX5090은 PREDICTED/UNVERIFIED, synthetic fixture/gold는 AUTO-GENERATED / NOT HUMAN VERIFIED다. Public exposure/pilot/민감 IFC/fine-tuning은 이번 자동 범위 밖이다.
