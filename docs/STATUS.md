# NeuroBuild_v2 실행 상태

갱신: 2026-09-20 KST. **Phase0 checkpoint 완료 / Phase1 checkpoint 완료 / Phase3 checkpoint 완료 / Phase4 Explicit Workflow 진행 중**.

| 항목 | 현재 상태 |
|---|---|
| 완료 Phase | 0 Foundation + 1 Domain + 2 Persistence + 3 IFC Engine; 전체87 tests PASS, 원격v2 확인 |
| 마지막 성공 checkpoint | 56926a0a8fe1d67587e1997f30b4347380375927 (Phase3 commit/push 성공) |
| GitHub | SSH origin, push 성공/Everything up-to-date, remote hash 일치 |
| 현재 Phase | 4: explicit review/approval/Apply 구현, 전체108 tests PASS; 독립 review 완료, commit/push 준비 |
| Backend 환경 | Miniconda26.7.1, project .conda Python3.12.14 생성/경로확인 완료; GPU 환경 미생성 |
| 현재 Hard Blocker | 없음. Git 인증 해결. Phase5 GPU/driver/disk 제약은 해당 단계 전에 재확인 |
| 다음 단계 | Phase4 gate/remote checkpoint 후 Phase5 local model/GPU preflight |

사용자가 인증 설정 과정에서 기존 local commit ID를 갱신했다. 29d4774/ee6848d는 이전 기록이다. 이 작업에서 이력을 다시 쓰거나 force push하지 않았다. 최신 HEAD는 git log -1로 확인한다.

## 마지막 성공 검증

- 원격 main0914597 보존, v2=f131644 확인. 재개 전 worktree clean.
- Backend Python3.12.14/pip26.2.1과 CONDA_PREFIX 경로 일치 확인.
- 이전 Phase0 runtime info smoke13건/JSON/seed/링크/Git 제외 검사 통과. Phase1 Domain unittest29개 PASS.

## 후속 제약

- 설치 후 root96%/83G, Miniconda939M/Backend1.4G/cache802M. 시스템 환경 미변경.
- A100 GPU3 마지막 관측은 process3개/약4GB 점유. 필수 benchmark 전에 재확인하고 타인 process를 건드리지 않는다.
- Driver535.183.01의 최신 모델 runtime 조합은 미확정이다.
- RTX5090은 PREDICTED/UNVERIFIED. 생성 gold는 AUTO-GENERATED / NOT HUMAN VERIFIED.
- Phase5~11 미시작. public exposure/pilot/실데이터/fine-tuning은 범위 밖이다.

계획은 [MASTER_PLAN](MASTER_PLAN.md), 결정은 [DECISIONS](DECISIONS.md), 실행 근거는 [EXECUTION_LOG](EXECUTION_LOG.md)를 따른다.

현재 project PostgreSQL17.11 실행 중: Unixsocket var/run/postgresql, port55432(socket명), TCP 없음, peer auth. .conda psycopg3.2.10. Lifecycle scripts/postgres.py.
