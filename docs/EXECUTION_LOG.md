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
