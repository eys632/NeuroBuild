# NeuroBuild_v2 실행 기록

Timezone: Asia/Seoul (UTC+09:00). command/관측 결과/수정/실패를 기록하며 chain-of-thought와 인증 비밀은 저장하지 않는다. 분 단위 시각을 관측하지 않은 작업은 임의로 만들지 않는다.

## 2026-09-19 — 기존 Phase 0 검증과 Git author blocker

- 기존 foundation 신규 파일은 22개였다. `git diff --cached --check`는 exit 0/출력 없음으로 통과했고 `git diff --cached --name-status`는 모두 `A`였다. 변경량은 1,504줄 추가였다.
- `git diff --cached --stat` 및 파일 경로 검토에서 기존 `NeuroBuild_v1/`, 중첩 `NeuroBuild_v2/` 수정이 없었다. 환경/weight/cache/DB/runtime artifact는 신규 staged 파일에 없었다.
- staged `.gitignore`는 `.conda/`, `.conda-vllm/`, `.venv/`, `/var/`, secret/weight/artifact 등을 제외했다. `configs/runtime.env.example`은 localhost 예제와 빈 model ID를 담았다. 일반 token/private-key 패턴 검사에서 일치가 없었으며 완전한 secret 탐지 보장을 뜻하지 않는다.
- Git author와 author/committer 환경변수가 없음을 확인한 시점에는 최신 사용자 즉시 실행 지침에 따라 author만 요청하고 중단했다. author를 추측하여 commit하지 않았다.
- 기존 `docs/phase0_report.md`에는 runtime info smoke 13건, JSON profile 3개, seed 20개/10개 분류/고유 ID, Python syntax, 문서 링크, ignore 경로 11개 검증 결과가 기록되어 있다. 이 로그에서는 이를 **이전 보고의 결과**로 참조하며 위 read-only 재검토 중 모두 다시 실행했다고 기록하지 않는다.

## 2026-09-19 23:05:40 +09:00 — Phase 0 local commit

- 사용자 제공 Git identity: `eys632 <eys632@gmail.com>`.
- 설정 범위: 이 repository의 local Git configuration. 전역 identity로 확대하지 않았다.
- 마지막 성공 local commit: `29d47748035647d9ef16d5b44d47fd94106b3e8c`.
- Commit message: `Establish cross-server NeuroBuild v2 phase 0 foundation`.
- Branch: `v2`. 과거 main/legacy/history를 보존했다.
- 확인 command: `git log -1 --format='%H%n%aI%n%an <%ae>%n%s'`.
- 확인 결과: 위 hash, author, 시각과 message 일치.
- 이 시점의 local commit 성공은 GitHub push 성공을 의미하지 않는다.

## 2026-09-19 — HTTPS push 실패와 SSH 경로 확인

실행 command:

```sh
git push -u origin v2
```

관측된 오류(인증 비밀 없음):

```text
fatal: could not read Username for 'https://github.com': No such device or address
```

원격 쓰기 인증이 없어 push하지 못했다. local commit은 유지했다. 이후 `git ls-remote --heads origin main v2`에서는 `main=09145974c17d1a09abdd2c48863e940fe68678b9`만 관측되었고 remote `v2`는 없었다. 동일한 인증 없는 push를 반복하지 않고 기존 SSH 경로를 read-only로 확인했다.

```sh
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 -T git@github.com
```

관측된 오류:

```text
No ECDSA host key is known for github.com and you have requested strict checking.
Host key verification failed.
```

SSH 디렉터리 목록에서는 `authorized_keys`만 관측되었고 기본 outbound private key를 확인하지 못했다. private key 내용을 읽거나 출력하지 않았다. `ssh-add -l` 결과는 다음과 같았다.

```text
Could not open a connection to your authentication agent.
```

알려진 host key/기본 key/agent 부재를 넘어 모든 가능한 인증 수단이 없다고 단정하지 않는다. 실제 확인한 기존 경로로는 GitHub write authentication을 완료하지 못했다. host checking을 완화하거나 키를 자동 생성하지 않았다. 사용자 hard blocker 6번(필요한 인증/secret)으로 기록하고 안전하게 구성된 GitHub 인증이 필요함을 보고한다.

## 2026-09-19 23:06 KST 이후 — 자율 실행 상태 외부화

- 최신 사용자 장기 자율 실행 지침, 전역 `~/.codex/AGENTS.md`, root `AGENTS.md`를 읽었다.
- 최신 사용자 지침이 과거 Phase별 승인 대기를 대체함을 기록했다. 목표는 Phase 11 Internal Technical MVP이며 public production/pilot/fine-tuning/지역 특화는 제외했다.
- `docs/MASTER_PLAN.md`, `docs/STATUS.md`, `docs/DECISIONS.md`, `docs/EXECUTION_LOG.md`를 작성했다.
- Roadmap 1~11/5.x, 각 acceptance criteria/선행 조건, test-review-document-commit-push gate, hard blocker, metre 단위, PostgreSQL single worker/session advisory lock, AUTO-GENERATED / NOT HUMAN VERIFIED를 기록했다.
- Phase 0 remote checkpoint가 완료되지 않았으므로 Phase 1과 환경/패키지 설치는 시작하지 않았다. 이 네 문서 작성 자체를 Phase 1 구현으로 간주하지 않는다.
- 기록 시작 직전 `git status --short --branch`는 `## v2`로 깨끗한 local worktree를 표시했다. 이후 새 상태 문서 작성은 별도 변경이며 이 로그만으로 commit/push 완료라고 주장하지 않는다.
- 이번 상태 외부화에서 Application unit/integration, DB/IFC/LLM benchmark, browser tests를 실행하지 않았다. model benchmark 결과는 **NOT_RUN**이다.

## 이후 기록 방식

### 2026-09-19 23:11 KST — 자율 지침 문서 검증

- Root AGENTS/README/Git workflow/roadmap/project context를 새 자율 실행 범위로 갱신했다. 과거 Phase0 보고는 당시 기록으로 남기고 현재 상태 문서로 연결했다. AUTO-GENERATED / NOT HUMAN VERIFIED를 평가 계획에 명시했다.
- `docs/reports/phase0_report.md`에 foundation 구현 완료와 PUSH_PENDING_AUTH를 구분했다.
- `/usr/bin/python3 -B`의 stdlib 파일 검사로 Markdown16개 상대링크 정상 확인. 시스템 Python은 이 기본 파일 검사에만 사용했고 개발 환경으로 사용하지 않았다.
- `git diff --check` PASS. `git diff --exit-code 29d4774 -- NeuroBuild_v1 NeuroBuild_v2 configs scripts evaluations requirements runtime`는 exit0으로 기존 코드/설정/예제 미변경을 확인했다.
- 이 문서 변경은 별도 local checkpoint `Document autonomous MVP plan and authentication blocker`로 보존한다. 결과 hash는 `git log`가 기준이며 같은 commit 파일에 자기 hash를 미리 기록하지 않는다. 인증 상태가 바뀌지 않아 실패한 push를 반복하지 않는다. Phase1은 미시작이다.

새 항목마다 날짜/시각, 목표/변경, 실제 command, test 결과와 실패/수정, Git commit/push 상태를 남긴다. benchmark에는 dataset/prompt/schema/model/runtime/config/환경 revision과 측정 결과 artifact의 위치를 기록한다. 미측정은 NOT_RUN/UNVERIFIED로 남기고 성공 수치로 채우지 않는다. 각 Phase 상세 결과는 `docs/reports/phaseX_report.md`, 현재 요약은 `STATUS.md`에 유지한다.

## 2026-09-20 — 인증 해결과 Phase1 시작

- git push -u origin v2 성공/Everything up-to-date. git ls-remote --heads origin main v2로 main0914597 보존, v2=f1316443c473884079fb47533de2cabfa16f270a 확인.
- 현재 Foundation은 a2761ebb4ab89fe7b347b9855b80a1a46e6d7bef. 사용자 변경 상태를 수용했고 rewrite/force push를 하지 않았다. 사용자 GitHub noreply identity를 유지한다.
- 전역/project 지침 및 상태4문서를 읽고 Phase0 remote gate 통과 후 Phase1 시작.
- 설치 전 root/기존환경/Python/pip/CONDA_PREFIX/디스크 확인: Conda/환경 없음, system3.8.10/pip24.3.1, root96%/86G. Backend Python3.12 한 환경부터 계획했다.
- 공식 https://repo.anaconda.com/miniconda/ index의 Miniconda3-py312_26.7.1-1-Linux-x86_64.sh 다운로드 후 SHA256 b27f60ab63e77eeab50a5417c989120f767e863df32400190d4c7262369f8695 검증 PASS. batch install ~/miniconda3, shell init 없이 base auto_activate=false 설정.
- CONDA_PKGS_DIRS=<project>/var/cache/conda/pkgs conda create -y -p <project>/.conda --override-channels -c conda-forge python=3.12 pip 성공. 환경 활성화 후 Python3.12.14/pip26.2.1과 경로/CONDA_PREFIX 일치 확인.
- 설치 후 df:96%/84G. du: Miniconda939M, .conda258M, var346M. Base 프로젝트 dependency/GPU 환경/model weight/system 변경 없음.
- Phase1은 stdlib production + unittest로 단위/불변성/별도승인/stale/duplicate/거절 경로를 검증한다.

## 2026-09-20 — Phase1 검증 완료

- 대상 .conda를 activate하고 경로/버전/CONDA_PREFIX를 재확인한 뒤 python -m pip install --no-build-isolation --no-deps -e . 성공. python -m pip check 정상.
- bash scripts/test_backend.sh: unittest29개 PASS(0.004s); independent agent의 동일29개 검증과 root 재실행 결과 일치. stdlib-only Domain이며 DB/IFC/모델 통합 테스트를 주장하지 않는다.
- python -B scripts/show_runtime_info.py --profile a100 --json 회귀 확인. git diff --check 통과.
- Phase1 report/domain contract/backend lock/재생성 방법을 기록했다. commit message: Implement NeuroBuild domain contract. Push와 원격 hash 확인을 다음 명령으로 수행한다.

## 2026-09-20 — Phase1 remote checkpoint 완료 / Phase2 진입

- Phase1 commit e68baa4a9d34efaed6956866c8857755b3fd6940 생성 및 git push origin v2 성공. git ls-remote 결과와 local HEAD 일치, worktree clean 확인.
- Phase2 PostgreSQL/Artifact Persistence를 시작했다. 설치 전 Backend activate 후 Python/pip/CONDA_PREFIX/root84G 재확인.
- conda install --dry-run --json으로 postgresql17.11/psycopg3.2.10 추가 계획(다운로드12.9MiB)을 확인한 뒤 project .conda에만 설치했다. 설치 후 postgres17.11/psycopg3.2.10 import 정상, Backend319M/root84G.
- scripts/postgres.py init/start: var/postgres 사용자 소유 cluster, var/run/postgresql0700 Unix socket, auth-local peer/auth-host reject, TCP listen_addresses 비어 있음. current_user/current_database 확인. fsync/synchronous_commit on, data page checksum enabled.
- PostgreSQL server가 현재 프로젝트 전용으로 실행 중이다. 다른 사용자/시스템 DB/프로세스는 조회·변경하지 않았다. 재현 lifecycle은 scripts/postgres.py에서 marker/경로 소유자를 확인한다.
- Phase2는 runtime_skeleton(PG repository/migration), model_research(immutable artifact adapter/tests), architecture(독립 realPG integration tests)와 root(PG environment/lifecycle/review)로 파일 소유권을 나눴다. Product multi-agent 기능을 구현하는 것은 아니다.

## 2026-09-20 — Phase2 gate

- Independent real PostgreSQL13 tests PASS, root 전체62 tests PASS(3.271s, skip0). Domain29/Artifact20/Persistence13. Publication 이후 fsync 실패 recovery를 root review에서 발견해 verify(file+objects dir fsync)와 fault tests로 보강했다.
- Root controlled PostgreSQL stop/start smoke PASS: head/revision/hash/COMMITTED intent/exact retry 유지. Test-owned schema만 정리하고 synthetic artifact는 ignored var/tests/restart에 보존했다. 강제 OS crash 검증은 아니다.
- scripts/postgres.py start에 noTCP 옵션 강제 후 재시작/SHOW listen_addresses empty 확인. 현재 private PostgreSQL은 실행 중이다.
- Backend activate/path/version/CONDA_PREFIX/disk84G 재확인 → editable reinstall/no-deps → pip check PASS. independent architecture/security/cross-server review 완료, RTX는 UNVERIFIED.
- Phase2 report/requirements/README/compatibility 갱신, diff check PASS. Commit/push는 다음 checkpoint command 결과로 확정한다.
