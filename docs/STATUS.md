# NeuroBuild_v2 실행 상태

갱신: 2026-09-19 23:11 KST. 현재 상태는 **Phase 0 foundation local committed / remote checkpoint BLOCKED**다. Phase 1은 시작하지 않았다.

## 완료·진행·남은 작업

| 항목 | 상태 / 증거 |
| --- | --- |
| Phase 0 foundation | 기존 22개 신규 파일의 문서·설정·runtime info·평가 seed 작성 완료. Application/DB/IFC/model 실행 구현 완료를 뜻하지 않음 |
| 기존 staged 검증 | `git diff --cached --check` 통과. 22개 모두 신규 파일, legacy 수정/환경/weight/runtime artifact staged 없음 |
| Git author | 사용자 제공 `eys632 <eys632@gmail.com>`을 repository-local 설정; author 부재 blocker 해소 |
| 기록 시점의 마지막 성공 Git commit | Foundation commit `29d47748035647d9ef16d5b44d47fd94106b3e8c`, 2026-09-19 23:05:40 +09:00, `Establish cross-server NeuroBuild v2 phase 0 foundation`. 현재 HEAD는 재개 시 `git log -1 --format='%H %aI %s'`로 확인 |
| GitHub checkpoint | **미완료**. `git push -u origin v2`가 HTTPS 인증 부재로 실패 |
| 마지막 원격 확인 | `git ls-remote --heads origin main v2`에서 `main=09145974c17d1a09abdd2c48863e940fe68678b9`만 관측; remote `v2` 없음 |
| SSH 대안 | strict checking을 유지한 read-only 인증 확인 실패. 알려진 GitHub host key/기본 outbound key/agent를 확인하지 못함. 자동 키 생성이나 검증 완화 없음 |
| 상태 외부화 | MASTER_PLAN/STATUS/DECISIONS/EXECUTION_LOG 및 자율 지침 갱신. 이 변경을 담은 local 문서 checkpoint는 현재 `git log`로 확인한다. remote push는 미완료 |
| Phase 1~11 | NOT_STARTED. 설치나 다음 Phase 구현을 시작하지 않음 |

## 현재 Hard Blocker

**GitHub의 공통 `v2`에 push할 인증이 필요하다.** 최신 사용자 지침은 push 성공까지 Phase checkpoint 완료로 간주하지 않으므로 사용자 측 인증 설정이 필요한 상태다. 기존 local commit은 보존되어 있다. 개인키/token 내용을 문서·로그·채팅에 기록하지 않고, 안전하게 구성된 인증 경로로 push를 재시도한다.

GitHub host key strict checking을 끄거나 새로운 SSH key를 임의 생성하지 않는다. 쓰기 인증이 없는 같은 HTTPS push를 반복해도 checkpoint가 해결되지 않는다. 단계별 승인을 기다리는 중이 아니라 **사용자 hard blocker 6번(필요한 인증/secret)** 때문에 중단한다.

## 이후 단계의 제약

- A100 GPU3에서 마지막 조사 당시 예상 밖 process 3개/약 4GB 점유를 관측했다. 타인 process를 조회·종료하지 않았다. 필수 model benchmark 전에 허용 GPU3만 재확인해야 한다.
- 마지막 root disk 조사 결과 사용 96%, 약 86G 여유였다. 현재값으로 간주하지 않고 설치 전후 재측정하며 peak 용량을 계산한다.
- Driver 535.183.01과 후보 model용 PyTorch/vLLM build 조합은 미확정이다. system driver/CUDA 변경으로 맞추지 않는다.
- RTX5090은 접근 불가능하며 PREDICTED/UNVERIFIED다. 실제 검증을 수행한 것으로 기록하지 않는다.
- 평가 seed 20개는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. 사람이 검수한 ground truth로 표시하지 않는다. 외부 Pilot 전 사용자 검수가 필요하다.

## 마지막 성공 검증과 미실행 항목

- 23:11 KST 문서 갱신 검증: Markdown16개 상대링크 정상, `git diff --check` PASS, legacy/config/script/evaluation/runtime 파일은 foundation commit 대비 미변경. 문서-only 변경이므로 제품 기능 테스트를 재실행했다고 기록하지 않는다.
- 현재 세션에서 재확인한 검증: foundation staged `git diff --cached --check` PASS, 파일 22개/legacy 변경 없음, 일반 token/private-key 패턴 미발견.
- 기존 Phase 0 보고에 기록된 검증: runtime info smoke 13건, JSON profile 3개, synthetic seed 20개/10개 분류/ID 유일성, Python syntax, 문서 상대링크, Git ignore 경로 11개. 이는 [당시 보고](phase0_report.md)의 증거이며 이 상태 문서 작성 중 재실행한 결과로 표시하지 않는다.
- Application unit/integration/regression, PostgreSQL, IFC operation, LLM benchmark, browser MVP는 **NOT_RUN / NOT_IMPLEMENTED**다. runtime info 검증을 제품 동작 검증으로 대체하지 않는다.
- Miniconda, 프로젝트 환경, package, model weight, PostgreSQL, frontend runtime을 이번 후속 작업에서 설치하지 않았다.

## 다음 재개 행동

1. 설정된 Git 인증을 확인하고 foundation 및 상태 문서의 commit/push를 끝낸다. remote `v2`에 저장된 commit을 확인한다.
2. Phase 0 checkpoint와 상태를 갱신한 뒤 Phase 1 Domain Contract를 시작한다. 별도의 Phase 승인 요청은 하지 않는다.
3. Backend 환경 준비 전 전역 정책의 root/기존 환경/Python/목적/위치/디스크 확인을 수행한다. **현재 remote checkpoint 이전에는 설치하지 않는다.**

전체 계획과 gate는 [MASTER_PLAN.md](MASTER_PLAN.md), 중요한 결정은 [DECISIONS.md](DECISIONS.md), 실행 command와 failure는 [EXECUTION_LOG.md](EXECUTION_LOG.md)를 따른다.
