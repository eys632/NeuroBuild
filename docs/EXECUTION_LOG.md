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

## 2026-09-20 — Phase2 remote checkpoint / Phase3 환경

- Phase2 commit18c7e21cc367cbf5e0f2c7b61c5981f30f476a98 push 성공 및 git ls-remote hash 일치 확인. 이후 Phase3 시작.
- 기존 backend/Python3.12.14/pip/CONDA_PREFIX/disk84G 확인 후 IfcOpenShell0.8.5 PyPI manylinux_2_31 wheel와 dependency를 hash lock로 설치했다. pip check는 통과했으나 실제 import에서 GLIBC_2.32 부재 오류: wheel tag와 실제 ABI 요구가 다름. 성공으로 기록하지 않고 system glibc 변경 없이 호환되는 배포 build를 조사한다.
- pip 설치 후 Backend590M/cache271M/root84G. 모델 환경/weight는 미생성.

- IfcOpenShell 공식설치문서의 stable conda-forge 방식으로 전환. 초기0.8.3 dry-solver는 최신0.8.5의 glibc>=2.17 build 확인 후 본 작업의 process만 종료하고0.8.5로 바꿨다. 시스템/다른사용자 process 미변경.
- Conda dryrun152.5MiB 확인 후 pip의 ifcopenshell/numpy/shapely만 uninstall하여 파일중복을 방지하고 Conda0.8.5 py312hfac0a26_8 설치. import IFC4 및 headless create_shape(8vertices) PASS. Conda manifest/URL-SHA256 lock 갱신. Backend1.4G/cache802M/root83G.
- 해당 native Conda build에는 pip dist-info가 없어 pyproject pip dependency로 선언하면 pip check가 missing으로 나온다. Conda manifest를 필수native dependency의 source로 두고 pyproject 중복선언 제거; import/version/IFC tests로 실물검증한다.

- Root actualIFC4→V0→worldXY 이동→V1 PostgreSQL/artifact smoke PASS: mm file+33도부모회전, 두fullsnapshots/head/원본hash/inventory 보존. Test-owned schema만 정리. 사용자승인 workflow검증은 Phase4이며 이저수준smoke에포함하지않음.
- 독립 review에서 nativeparser의 잘못된DATA무시와 큰좌표·큰delta의relative-tolerance 손실허용을 실제재현. Gate완료로간주하지않고 SPF framing/record검사와 절대metre오차검증, regression을보강중.

## 2026-09-20 — Phase3 gate

- Root 전체87 tests PASS(3.728s, skip0), independent IFC25 PASS(0.501s). 수정 후 malformed scanner probe14개 중 invalid11개 모두거절/valid3개수용. 기존1m손실/Decimal0.25m손실/overflow/underflow/context누락 거절 및 subnormal정규화 확인. 알려진 gate blocker 없음.
- Narrow SPF recordscanner, exactFraction 절대metre오차/Decimal변환오차, 필수singleidentitycontext를 최종계약에기록했다. Full EXPRESS/STEP grammar 검증으로과장하지않는다.
- pip check/runtime-info 회귀/diff check PASS. 신규소스와syntheticgenerator/테스트/lock/report만checkpoint, 사용자IFC/native환경/artifact/cache는Git제외. Phase3commit/push를다음명령으로확정한다.

## 2026-09-20 — Phase3 remote checkpoint / Phase4 진입

- Phase3 commit56926a0a8fe1d67587e1997f30b4347380375927 push 성공, 원격v2 hash 일치 확인.
- Phase4 Explicit Renovation Workflow 시작. 기존 Backend/PG/IFC 환경을 재사용하며 추가설치가필요하지않다.
- Application Service가 자신의 frozen review state를 소유하고 실제inventory의targetconfirmation과 정확한proposalcontent승인을 분리한다. PG/IFC를결합한합성E2E와failure/stale/duplicate/동시성 검증을구현한다. Durable humanreview/queue는계획된Phase7 범위이며 Phase4메모리review를재시작내구성으로과장하지않는다.

## 2026-09-20 — Phase4 검증

- Root DISPLAY/WAYLAND_DISPLAY 제거 환경에서 실제 private PG DSN과 bash scripts/test_backend.sh: 전체106 tests PASS(11.806s), skip0. Independent Workflow19 PASS(7.756s).
- 실제 IFC+PG end-to-end, 별도 승인, forged snapshot/원래input 변경 거절, stale/duplicate/concurrency, invalidimport, engine/DB실패+orphanretry 확인. Commit응답유실 후 다른workflow의V2/engine장애 상황에서 기존execution이V1만반환하고headV2보존 확인.
- In-memory review는 재시작하면 소실되는 것을 테스트했으며 durable humanreview 성공으로 주장하지 않는다. 새 dependency 없이 common service 경계를 유지했다. pip check/diff check PASS. 최종 독립 review 후 commit/push한다.

- 최종 입력 UUID alias/deepcopy 회귀 추가 후 root 전체108 tests PASS(12.378s, skip0), independent Workflow21 PASS(8.640s). 추가 독립realPG probe4/4 PASS: 다른workflow의committed eid거절, 잘못된orphan거절, 동일eid동시요청의단일결과, committed artifact손상거절. 현재 material gate blocker 없음.
- Phase4 source/docs/tests/report 최종diff check 후 commit/push를수행한다.

## 2026-09-20 01:00 KST — Phase4 remote checkpoint / Phase5 blocker

- Phase4 commit dd58b596fab2aaa24c5aba4322d56bc5d127440c push 성공, git ls-remote hash 일치 확인. Worktree clean 후 Phase5 GPU/environment preflight.
- nvidia-smi -i 3 targeted query: A10040GB/driver535.183.01, total40960 used3965 free36373MiB, util0%; compute process3개(1746/1772/414MiB). Phase0 점유 상태가 유지됐다. GPU0/1/2는 조회/사용하지 않았다.
- 현재 uid의 ps PID 목록만 대조하여 GPU process가 본인 소유가 아님(0/3)을 확인했다. 다른 사용자의 명령/파일/환경/소유자 신원은 조회하지 않았고 process를 변경하지 않았다.
- root96%/83G, Backend1.4G/cache803M/PG82M, .conda-vllm 없음. Shell의 systemPython3.8.10은 기본 진단에만 사용했으며 model package/weight 설치 없음.
- Root AGENTS 예상 밖 GPU process 중단 규칙에 따라 BLOCKED_GPU_OCCUPIED. 실제 OOM/모델 startup 실패로 기록하지 않는다. 필수 benchmark NOT_RUN, Phase5 gate 미통과. Phase5.x~11 우회 구현 없음.
- 사용자에게 현재 점유와 정책 근거를 보고하고 GPU3 사용 가능 시점을 요청했다. STATUS/Phase5 report/runtime/README에 완료범위·제약·재개 절차를 기록한다. Private PostgreSQL은 계속 실행 중이며 관리/종료 명령은 STATUS에 있다.

- 보고서 작성 뒤 GPU3만 다시 조회했으며 process3개/used3965/free36373MiB/util0%로 동일했다. 후속 변경은 상태 문서만이며 Application tests를 불필요하게 반복하지 않았다. Current-state Markdown25개 상대링크 및 git diff --check PASS. 독립 문서검토 후 blocker checkpoint를 push한다.

- 독립 문서 검토 통과: Phase0~4 완료/108 PASS/Phase5 정책 blocker/후속 미진행/메모리 review 한계가 일관됨. README roadmap 설명의 범위를 Phase0~11로 맞췄다.

## 2026-09-20 04:32 KST — 사용자 GPU 정책 변경 / Phase5 재개

- 사용자가 GPU3의 다른 process 존재만으로 중단하는 규칙을 대체했다. 타인 process/환경 변경 금지 및 GPU3 only는 유지하며 free VRAM/utilization, 후보peak+margin으로 판단한다. 관련 현재정책/상태문서를갱신하고 과거중단기록은 historical로보존했다.
- 전역/프로젝트 AGENTS와 계획/상태/결정/실행기록, git status/log를 읽었다. Remote checkpoint6b3dfd2, worktree clean에서 재개.
- 설치 전 root/기존환경/Python/pip/CONDA_PREFIX/disk 확인: Backend .conda1.4G, modelenv없음, 기본shellsystem3.8.10, conda미활성, root83G/free96%, cache803M. 두환경 목적은 Backend 유지 + model-only .conda-vllm Python3.12.
- GPU3 only6samples/2s간격(10초): 모두 total40960/used3965/free36373MiB, util0%, driver535.183.01. 초기 safety margin20%free=7275MiB, 후보예산29098MiB. 실제fit보장은 아니며 launch직전/실행중재검증한다.

- .conda-vllm Python3.12.14/pip26.2.1을 conda-forge로 생성했다. 활성화 후 python/python3/pip/CONDA_PREFIX가 모두 프로젝트 model 환경임을 확인했다. Backend는 jsonschema4.26.0과 4개 dependency를 SHA256 고정하여 추가하고 editable reinstall/pip check를 통과했다.
- 공식 vLLM0.8.5+cu118/Torch2.6.0+cu118 wheel과 호환 핵심 dependency를 제한한 resolver 결과148개를 SHA256 lock으로 저장했다. --require-hashes --only-binary --no-deps 설치 진행. ray[cgraph]가 요구하는 cupy-cuda12x13.4.1도 lock에 기록하지만 V0/uni에서는 해당 cgraph 경로를 사용하지 않는다.
- Qwen3-14B-AWQ full revision31c69efc29464b6bb0aee1398b5a7b50a99340c3의 11파일/9,992,683,140bytes manifest를 고정했다. weights뿐 아니라 config/tokenizer/license도 pin한다. 다운로드는 20GiB 디스크 reserve와 파일별size/SHA256검증을 사용한다. root free81GiB에서 시작했으며 병행 설치 중75GiB를 재확인했다. 실제 GPU inference는 아직 실행하지 않았다.

- GPU preflight 13개 fake측정 회귀 PASS. 실제GPU3 재측정5회도 free36373MiB/util0%로 동일하여 estimated18432+margin7275MiB 후보가 예산 안에 들어왔다. 이는 launch 성공이 아닌 사전예산 검사다. 변경 중간 Backend회귀145개 PASS(13.078s,skip0), 기존PG/IFC 포함.

- 정책/사전측정 guard 중간checkpoint81b06054617295654c54130bfc615ae1bbbc4e9c를 commit/push하고 remote v2 hash 일치를 확인했다. Phase5 완료checkpoint는 아니다.
- Runtime hash lock148개 설치 완료. pip check PASS; torch2.6.0+cu118/vllm0.8.5+cu118/transformers4.51.3/xgrammar0.1.18/xformers0.0.29.post2 및 vllm._C/번들FA2 nativeimport PASS. 해당 검사는 CUDA allocation을 수행하지 않았다. .conda-vllm7.6GiB/cache5.1GiB, root약67GiB free를 재확인했다.

- 작은 CUDA smoke 전 GPU3를 estimatedpeak1024MiB로5회 재측정해허용. mask3/PCI_BUS_ID/devicecount1, cuda:0 UUID와물리GPU3 UUID일치를 확인했다. Torch FP16 128×128 matmul과결과비교PASS, Torchpeak allocated8,585,216/reserved23,068,672bytes. 이는 PyTorch allocator 측정이며 process전체VRAM이나모델peak가아니다. Smoke process는정상종료했다.

- Qwen3-14B-AWQ pinned11파일총9,992,683,140bytes 다운로드및직접SHA256검증완료. 실제localtokenizer/nonthinking chattemplate에서 seed20 입력은1868–2075tokens, output768 reserve와합쳐context4096에모두fit함을CPU로확인했다.

- 첫모델startup: GPU3만5회재검사후guardlaunch, mask/UUID검증PASS, Qwen3-14B-AWQ가 awq_marlin/FP16으로로드됐다. 모델로드9.3639GiB, firsthealth200 약20.666초(2초poll,최신watchdog0.5초표본기준;filesystemcache를flush한cold측정아님). 전체GPUbaseline대비관측peak증가10946MiB,최소free25428MiB. 256KVblocks/context4096/seq1/eager/TP1,loopback8003서버정상.
- 독립검토가 guard강제소멸시child잔존가능성과 숫자suffix grounding결함을발견했다. 아직LLM평가를수행하지않고자신의guard에중단요청하여server를정상종료했다. 타인process를변경하지않았다. parentdeathsignal/안전한PG회수및numericboundary회귀를추가한뒤다시launch한다.

- Guard修正을독립검토하고16tests(PDEATHSIG/own descendant 실제CPU-only2포함) PASS. Parentdeath SIGKILL은torchimport전에설정하며 WNOWAIT로자기leaderPID를유지한상태에서TERM/KILL후reap한다. 숫자suffix/exponent/comma/fraction/산술식/잘린unit 거절을추가했고 parser27+HTTP16+Domain29=72PASS. Downloader외부symlink/metadata no-clobber13테스트PASS.
- 수정한guard로14B-AWQ재시작후한국어첫JSON추론PASS(회의실책상 +X1m). xgrammar:no-fallback/nonthinking, input1879/output95tokens,첫요청latency6.118초(워밍업성격,정규평가에서제외). 이후seed20×3+warmup5실측시작. Root회귀194PASS(13.242s,skip0); 후속다운로더13개도별도PASS.

- 14B-AWQ promptv1 baseline완료: run20260919T195704Z-9b3cd95a46a646dbacebd0bc6eec40b5, warmup5제외60trials. JSON/schema60/60,parser51/60,semanticrubric45/60(75%),criticalFP모델/수용0/33,criticalFN6/27. mean2.9605s/p954.2152s,관측aggregatepeak증가11568MiB/minfree24806MiB. 실제단위/target실패를누락하지않고evaluations/results/phase5에보존했다.
- 실패5cases: D01비연속target이어붙임,F01숫자철자0.5→0.50,I01X성분을dy배치(Backend거절),F02대상제외조건누락,J01범위밖설계제안을clarification분류. v1/source/gold는그대로고정해8B비교에사용하고v2prompt를별도로작성한다. 현재품질로최종모델/gate완료를선언하지않는다.
- 완료후자신의guardCtrl-C중nvidia-smi子process가중단되어종료reason이GPU_QUERY_FAILED로남았다. 이미60trial완료후이며자기servergroup만TERM/KILL회수,childexit0/free36373MiB복귀확인. 이는추론실패/VRAM부족이아니다. 다음부터자기guardPID에직접SIGTERM하여조회중단과운영중단원인을구분한다.
- Qwen3-8B pinnedrevision b968826d9c46dd6066d109eabc6255188de91218(전체16,397,459,696bytes)공식manifest검증후두번째후보다운로드시작. root62GiB여유에서20GiBreserve조건을통과했다. 두GPU모델동시실행은하지않는다.

- 중간checkpoint 전 전체207tests PASS(14.755s,skip0), real PostgreSQL/IFC/HTTP·GPU guard fake/own CPU lifecycle 포함. GPU-model 품질 gate는 아직 미통과로 유지한다.

- Runtime/contract/실패보존 중간checkpoint51a07d5131c5b4aa435787e13633f42ef7963451 push및remotehash일치확인. Phase5 최종gate는아님.
- 14B promptv2 baseline실패를개선한별도버전으로실측: 60schema/parserPASS,semantic57/60(95%), BUT 조건부E02에서모든3trial이READY여서criticalFP3/33. 0건gate미충족으로채택하지않음. mean3.0032s/p954.2863s. 원본v1/gold/parser는바꾸지않았고v2전체결과도별도보존. 직접own guardPID SIGTERM으로정상종료STOP_REQUESTED/exit0.
- 8B14개파일총16,397,459,696bytes직접SHA256검증완료,root약47GiBfree/cache5.3GiB/전체weights25GiB. 이전모델종료후8B BF16 estimatedpeak23552MiB/util0.60/allocator0.60으로다시GPU3preflight+단독launch. 동일v1/seed/schema/client로비교하며v3조건판단prompt는별도파일로준비한다.

- 8B BF16 startup/inferencePASS: health약20.353s,model15.2683GiB,baseline대비관측peak증가17024MiB/minfree19350MiB(초기). 14B와동일v1/seed60실측: schema60/60,parser57/60,semantic45/60(75%),criticalFP6/33(복수가구D01,조건E02),criticalFN3/27,mean2.6570s/p953.6554s. F01모델단위변환은Backend가거절하고F02대상수식어손실/J01오분류도보존했다.
- V3 prompt는 v1/v2/gold/parser를유지한새파일이며외부조건을이동값만으로참으로가정하지못하도록완전한이동값+미확인조건신규예제를보강했다. 6synthetic예시parser/schemaPASS,token최대2606+output768=3374/4096. 먼저이미로드된8B에동일seed60/5warmup으로v3평가중이며,이후14B와같은v3를비교한다. v2의criticalFP를숨기거나qualitygate를낮추지않는다.

- 8B promptv3평가완료: schema60/60,parser/semantic54/60(90%),criticalFP0/33,지원누락6/27. A02음의부호누락/I01모델단위변환각3회는Backend에서거절했다. mean2.4280s/p953.6323s. 결과/manifest를별도보존했으며14B와v3비교는아직미실행.
- Root가오직자신이시작한8B modelPID의socket FD/inode만대조한추가점검에서,API는127.0.0.1:8003/Gloo보조socket은127.0.1.1이나PyTorch rendezvous TCPStore한개가IPv6wildcard에listen함을확인했다. 다른사용자socket/process는출력/조사하지않았다. 60trial완료후자기guardPID SIGTERM→자기group종료/childexit0. 외부접속이있었다는증거는없으며이관측은bind주소에대한것이다.
- 다음launch전단일rank NCCL FileStore를project var의고유경로에미리생성하고,Gloo/NCCLinterface를loopback으로고정하는개선중이다. vLLM의이미초기화된defaultprocessgroup재사용경로를공식설치source에서확인했다. 시스템/다른process는변경하지않는다.

- FileStore/loopback/단일프로젝트실행lock개선20tests PASS(2.216s). 실제14B재launch/NCCL/vLLMstartup PASS(health약20.362s). own PID의socket FD로TCP listener5개모두127.0.0.1확인,IPv6wildcard TCPStore는없음. 실제launcher sourceSHA와runmetadata기록도일치했다. 이후v3/seed60평가진행중. CPUfake검증만으로네트워크범위를확정하지않고실제GPU서버로확인했다.

- 05:40 KST Phase5 final actualcomparison:14B-AWQv3 run20260919T202351Z-12fdb88f79be4e96bda18cd4395b6d65,60/60schema/parser/semantic,FP0/33,FN0/27,mean3.0361/p954.2843s. All5run archives+failedprompts preserved. Selected14B-AWQv3internaldevelopment; nohumangoldclaim.
- Explicitlegacy/modernstructuredprotocoladapter+manifestdialect/split,profilesmodelrevision/promptupdated. FakeHTTP20+parser27PASS. Actuallegacypost-changeA01/E02/F023/3PASS, noexternalcall. Fullbackend215testsPASS/skip0/15.671s(realPG/IFC,DISPLAYunset); independentreview5runmetrics+60outputreplay+launcher20PASS. Root47GiBfree, no systemchanges/foreignprocesssignals.

- Phase5remotecheckpoint d6e39c89658c552c59a8049d7198da051290bd3b exacthash확인후Phase5.x시작. 비교완료미선정8B캐시는본인project아래manifestidentity/정확한파일set/size/UID/regular/no-symlink/currentactivepath배제확인후정리(16,397,462,179B). 공식downloadmanifest와평가결과는Git보존,재다운로드가능. rootfree47→62GiB; cache전체삭제없음.

- Phase5.x사전검토에서Unicode분수/곱셈·축부호잘림,특수공백/구분자suffix를발견했다. 같은경계누락반복에따라개별기호목록이아닌Unicode숫자/공백/기호·문장부호경계순회와원문quantity+axis동일occurrence대조로접근수정중. frozenprompt/gold미변경, 실제hardeningmodel호출전이다.
- 중간전체회귀233PASS16.139s, listener불변reportfix후234PASS16.064s. 이는최종Unicode추가수정전중간기록이다. ActualownchildTCP5개loopback/3nonTCP확인. CPU검토기간GPUrelease를위해자기Phase5guard3363488에만SIGTERM;STOP_REQUESTED/childexit0/FileStorecleanup확인,used3965/free36373MiB/util0%복귀. Snapshot과shutdownreport모두보존.

- Phase5.xfinalpre-inference: parsera940f395...fb4a,236testsPASS/skip0/16.056s, independent19maliciousreject+4normalcontrols, 120handreferencePASS. Datasetdev85734d7c...ff88/hold12c08e85...4d78, manifest959d3340...6605。Promptv3anddatasetgoldunchanged. FormalfiniteboundaryfixincludesUnicodeMarks/unknownpunctuation, whitespacepreserved; NLPmeaningstillLLMresponsibility. FreezeJSONtimestamps/hashpinsrecordedbeforefirstmodelcalls.
- GPU3freshguardpreflightpassed; 14BhardeningserverstartuphealthPASS24.057s wrapperobserved(includespreflight,filesystemcachenotflushed),5actualTCPlistenersall127.0.0.1; noforeignprocesschanges.

- Phase5.x developmentv3 run20260919T205840Z-469fdecdb1fd476f82202df54a1808a7 completed120trials. schema120/parser111/semantic108;rawFP3/60acceptedFP0;wrongacceptedmove0/FN9/60;mean3.32248/p954.67003s. FourcasefailuresB01directionmissing,D02twoaxes,F01/F02modelunitconversion. Alloldseed60stillPASS,new20×3=48/60. GateFAILpreserved;heldoutnotcalled;v4development-onlypromptiterationauthorized.

- V4development-onlyprompt개정: singleobjectXYcomponents≠multipleobjects, unsignedaxisCLARIFICATION, originalliteralunitcopy. 기존externalcondition거절예제유지,heldout출력미호출. SHA2fdd6a5a92860cde27d14adc10916a242b2221e1569015541ddf31581d1a14d8,7newexemplarsschema/parserPASS; maxv4chat+output3538/4096 CPU확인. RootindependentpromptreviewPASS;additionalresearcherreview는별도로이어진다. v3/code/goldhash모두보존,새v4freeze후동일dev120재평가.

- V4freeze f154a7f2b1bc3b4728d9214778b2f85168e38c54 push/remotehash일치. 추가modelresearch독립promptreview7/7PASS회신은v4inference전도착. SameGPUserver/runtime/model/gold/parser/scorer로prompt만v4로바꾸어development40×3시작;warmup5제외.


## 2026-09-20 — Development v4 실패와 전략 재검토

Run20260919T211340Z-cebc5bbdaeea46b188caf6d27c4ff804: schema/parser120/120, semantic96/120(80%), raw/acceptedFP0/60, unsafeaccepted0/120, FN24/60, mean2.96099s/p955.05258s. 8case×3 모두불필요한거절: A01/A02/H01/HD-A02/B02/C02/H02는명시된방향이나미요청축을추가질문했고HD-D02는단일가구XY를미지원으로오인했다. 원문unit복사는개선됐지만전체gateFAIL. 결과/manifest/resources를development-v4에보존하며heldout은미호출이다.

긴예제prompt보강반복을재검토하여V5는847token English policy로전환,한축/두축지원과미요청축null을명시한다. 같은T0/runtime/model/schema/parser/gold로40development×1진단을먼저실행한다. 이는최종3회gate가아니며,개선시동일설정정식평가가필요하다. Qwen공식decoding지침은별도로검토하며무조건T0가원인이라고단정하지않는다.
