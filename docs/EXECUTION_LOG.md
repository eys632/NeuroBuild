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

- V4실패보존/V5진단freeze중간checkpoint db32f6e8c0a124a998500c7f1b2a8186a618ef29 push와remotehash일치확인. Runtime담당의추가V5read-review도중대모순없음으로회신. 이는실제품질통과가아니다.


## V5 간결한 영어 prompt 진단 실패

Run20260919T212748Z-bba084e02f46432aab7f11883d625467, development40×1/warmup5: schema40/40, parser16/40, semantic13/40, rawFP5/20, acceptedFP0/20, unsafeaccepted0/40, FN19/20. Mean4.18646s/p955.94240s. 지원gold20개는모두rawREADY였으나19개는숫자원문표기변경(1→1.00),단위선변환,미요청축의0/fake-null삽입등으로거절됐다. 단순길이축소/영어화는품질개선으로이어지지않았다. 이진단을3회반복gate로표시하지않으며모든실패결과를보존한다.

다음실험은기존development최고성능v3prompt를고정하고공식Qwen AWQ nonthinking sampling profile만변경한다(T.7/top_p.8/top_k20/min_p0/presence1.5/frequency0/repetition1/seed42). Legacy기본요청은그대로유지하며실제요청값을manifest에기록한다. Gold/parser/지원범위는유지하고heldout은계속미호출이다. 설정구현동안자기모델guard만정상종료했으며GPU3used3965/free36373MiB/util0%복귀를확인했다.

- Samplingpreset/manifest연동과guardoutputnamespace수정후전체245testsPASS/skip0/16.377s(realPG/IFC,DISPLAYunset). 기존legacywire동일/양쪽protocol/invalidconfig/변조된snapshot/재시도금지/실제samplingmanifest일치를검증했다. Log는var/logs,report는var/reports로한정하여artifact/model경로·symlink·hardlinkalias덮어쓰기거절. 수치parser/gold/scoringlogic미변경.


## V3 공식 non-thinking sampling 진단

Run20260919T213630Z-f42a9eb2a41d4368942b0575dda2893d:40×1,warmup5. Schema40/parser37/semantic36(90%),rawFP1/20,acceptedunsafe0/40,FN3/20,mean3.19669s/p954.46478s. V3/T0와같은4case오류(HD-B01방향추정,D02단일가구XY복수오인,F01/F02모델단위선변환)가남아gateFAIL. 공식권고만으로품질이해결된다는가정은성립하지않았으며기존실패를보존했다.

다음실험은짧은policy와명시적thinking/deepseek_r1/V0/xgrammar의문서화된경로를검증한다. Reasoning은일시메모리만경유하고finalJSON만평가/보존한다. Context4096/전체출력2048/timeout120을미리검증하고기존parser/gold/승인계약은변경하지않는다. v3는긴입력으로동일출력2048이4096을초과하므로그대로사용하지않는다.

- Thinking명시설정후전체251testsPASS/skip0/16.683s, client+harness42PASS. Source/gold검증기준미변경;finalJSON만노출하고reasoning누출/미완료/overlimit거절. Runtime metadata는실제launchmode와clientmode의선언일치를확인하며HTTP상태만으로모드를증명하지않는다. V6는v5의출력형식문장하나만수정,CPUoffline dev최대3322/4096(전체출력2048포함),heldout길이만3327/4096검증. 새freeze후actualthinking구성실험예정.

- af2e0e201becce9483007d7ff122acac2cc7883b freeze commit/push remote일치, root독립agent구현검토후dev40×1 thinking진단시작. 추가architecture독립harness/launcher/v6검토도PASS. FreshGPU3preflight/health/ownloopbacklistenersPASS; tokenizer출력창한도검증과actual품질은분리한다.


## V6 짧은영어policy+thinking 진단 실패

Run20260919T214743Z-27a340f0e04343be8be10a062a6eb25d:40×1,warmup5. Schema40/parser20/semantic17,rawFP4/20,unsafeaccepted2/40,FN17/20,mean13.23336s/p9520.61753s. 전체stop종료이며truncation/timeout없음,completion243–971(mean462.275). 숫자원문표기변경(1→1.00)과target손실,외부조건판단오류가남았다. Acceptedunsafe2는F01대상span에조사추가와HD-I02충돌조건무시이며같은심각도라고단정하지않지만고정exacttarget/criticalgate에서둘다실패다. 실제IFC실행이나승인은수행하지않았다.

추론모드자체가계약준수를보장하지않는다. 짧은영어policy는nonthinking/thinking모두실패했으며가장좋았던한국어v3지시/예제는유지한비교가필요하다. v7은v3출력형식문장하나만internalthinking/finalJSON구분으로명확히하고같은thinkingserver에서명시출력1280으로비교한다. Context4096CPU검증후40개진단하며gold/parser/게이트는유지한다.


## V7 한국어정책복원+thinking 진단 실패 / 모델후보재검토

Run20260919T220158Z-72efdc2dad274cb98b1d61b669597b75:40×1,warmup5,allstop. Schema40/parser35/semantic30(75%),rawFP0/20,unsafeaccepted0/40,FN8/20,mean14.55889s/p9528.66420s. HD-B01방향누락과HD-D02단일가구XY분류는개선됐으나5개수치lexical거절,3개불필요외부조건확인,2개조회분류오류가남았다. Thinking자체는최고nonthinkingv3의90%를넘지못했고고정gateFAIL이다. 결과/manifest/resource를보존하고자기모델guard만정상종료했다.

프롬프트·샘플링·추론모드반복실패후instruction전용post-trainingcheckpoint로모델선정을재검토한다. Qwen3-4B-Instruct-2507공식cdbee75f17c01a7cc42f958dc650907174af0554/Apache2.0/BF16은공식최소버전및로컬소스검토상기존runtime에서시험근거가있다. 크기만으로채택하지않고동일dev40자료/기존최고v3prompt/고정schema-parser-gold로순차평가한다. Fullpeak16384MiB추정+freshmargin,각파일다운로드와20GiB디스크reserve를확인한다. BF16비교sampling은.7/.8/K20/min0/presence0/frequency0/repetition1/seed42로명시하고AWQpenalty를자동재사용하지않는다. 실제quality/startup은아직미검증이다.

- Qwen3-4B-Instruct-2507 manifest:12files/8,060,915,998bytes/SHA70546521745f90e12e4fee0db9f73a7ec8a9296928b06b39d0f282cf1030c056. 공개 Apache2.0 후보로, weight3개 shard의 Hub LFS hash와 작은 파일 SHA를 확인했다. 다운로드 전 root free66,160,959,488bytes로 20GiB reserve를 포함한27.507GiB 필요량을 충족했다. 기존 download_model.py로 project var/models에 순차 다운로드/size+SHA검증 중이다. 이전 thinkingserver는 STOPPED/exit0/FileStorecleanup이며 GPU3used3965/free36373MiB/util0% 복귀를 확인했다.
- Neutral nonthinking preset 추가 후 client30/client+harness44/전체253testsPASS, skip0,16.900s. 기본 legacy와 다른 preset, GPU/schema/parser/gold는 유지하고8개sampling값과manifest를 명시했다.

- d05a000a7e19f2020c74b672f19dc3ba17ff6386 freeze commit/push remotehash일치. 4B12files size/SHA검증완료,실제tokenizer template SHA도계획과일치. Rootfree약55GiB,20GiBreserve유지. FreshGPU3preflight의free36373/util0%,16GiB추정+margin조건통과후BF16단독기동PASS. Health21.027s(별도probe기준/cacheunflushed),ownloopbackTCP5개PASS,기동중최소free27476MiB. V3/neutralpreset/dev40×1/warmup5 actual비교시작.


## 4B Instruct v3 진단 — 개선됐으나 gate 미충족

Run20260919T222220Z-6df72f2113474c108c488c98faefca20:40×1,warmup5. Schema40/parser39/semantic37(92.5%),rawFP1/20,unsafeaccepted2/40,FN0/20,mean2.81185s/p953.73833s. HD-B01은명시방향없이READY라Backend거절,HD-F01/F02는16cm원문단위를올바르게복사했으나target와instruction에서연구실scope/제외대상을잘라냈다. 모든지원gold가READY로수용되었다는것이대상보존성공을뜻하지않는다. 기존14B에서실패했던동일가구XY와단위변환은개선됐으나고정gate는FAIL이다.

다음은이미고정된v4prompt를동일4B/runtime/neutral sampling/dev40×1에적용한다. 14B에서v4가과잉거절했던결과는보존하며새instructioncheckpoint에서도같을지실제로비교한다. 새prompt/gold/검증기준수정이나heldout호출은하지않는다.


## 4B v3 failure review and v4 comparison freeze

Independent replay confirmed schema40/parser39/semantic37, rawFP1 and unsafeaccepted2. All result/manifest bytes match archives. Existing v4 policy specifically covers unsigned direction and full target scope/exclusion; CPU context maxima3529/3534 including768 output cap fit4096. Freeze records same model/runtime/sampling and unchanged parser/schema/gold. Only development40×1 next; no heldout inference. Previous regression253 PASS remains applicable because no source changes.


## 4B Instruct v4 diagnostic failure

Run20260919T223253Z-6038073ec36044adb6251920c5d6b285, development40×1/warmup5: schema/parser40, semantic34/40(85%), rawFP1/20, acceptedFP1/20, wrongacceptedtarget2/20, unsafeaccepted3/40, FN3/20. Mean2.35471s/p953.56743s. HD-B01 unsigned direction is fixed, but E01 preservation clauses and HD-F02 exclusion cause incorrect UNSUPPORTED, HD-A02 explicit negative direction causes CLARIFICATION, F02/HD-F01 lose target scope, and HD-I02 ignores an unverified collision condition. All responses completed without transport/parser errors. This does not pass the fixed gate; all outputs/resources are retained.

V4 replaced many instructions and examples simultaneously and regressed relative to 4B/v3. The next bounded experiment will retain v3 in full and clarify only direction/extraction reminders after examples, using general rules and unrelated sample nouns/numbers. No gold/parser/schema/scoring change or heldout inference. This is a development-driven prompt revision, not blind selection.


## 4B v8 failure and decoding reassessment

Run20260919T223831Z-af6ebcd137394488a0adc427bd63edcf: development40×1/warmup5, schema40/parser39/semantic36(90%), rawFP1/20, unsafeaccepted2/40, FN1/20, mean2.57006s/p953.45012s. HD-B01 still guesses unsigned direction and is blocked; HD-D02 regresses to multiple-furniture refusal; HD-F01/02 retain wrong short targets despite full instructions. All failures retained. V8 is not selected and heldout remains uncalled.

Three 4B prompt variants did not satisfy the unchanged gate. Stop expanding prompts. Compare the best existing v3 using existing legacy_greedy (temperature0/seed42) versus prior neutral sampling, all40 cases once. Other legacy sampling fields are omitted and inherit pinned server/model defaults; this is not an all-parameters-controlled ablation. Non-thinking greedy is an experiment, not an official quality guarantee. No source changes or validation weakening. If it fails, reconsider model/representation rather than repeat reminders.


## 4B v3 greedy control failure and model reassessment

Run20260919T224246Z-64a5648ea1b546c78b1f961bf3b6c094: schema40/parser38/semantic36(90%), rawFP1/20, unsafeaccepted2/40, FN1/20, mean2.57311s/p953.40377s. I01 changes750mm to-.75m and is rejected; HD-B01 guesses unsigned direction and is rejected; HD-F01/02 still drop location/exclusion in both target and instruction. Summary replay matches all recorded metrics. Changing decoding does not meet the gate. No holdout calls or IFC execution.

Stop 4B prompt/decoding trials and reassess a distinct instruction MoE checkpoint. Own 4B guard was verified by UID, cmdline and starttime before SIGTERM; child exited normally and rendezvous was cleaned. An initial attempt to use os.pidfd_open stopped without signalling because this Python build lacks that API; the existing verified-own-guard procedure completed shutdown. Other processes were untouched. Candidate metadata/static reviews and new GPU3 preflight are required before any new launch.

- 30B-A3B instruction AWQ comparison download: pinned third-party ELVISIO manifest32ff8e50,15files/16830441067bytes; fresh free58061914112bytes exceeds model+20GiBreserve. Source/config/kernel static reviews found no blocker; startup/quality remain unverified. Downloader verifies each size/SHA into project var/models; no new environment or package install.


## MoE candidate download and guarded startup

Pinned15files/16,830,441,067bytes completed size+SHA verification. Independent CPU header audit checked all56,115 names/shapes/F16-I32 dtypes/offsets/shard assignments, no mismatches; this is separate from semantic/kernel validation. Actual downloaded tokenizer/template SHA and v3 context maxima3538/3543 including768 output also matched the frozen preparation. Disk remained39G free.

Fresh GPU3 launcher preflight measured five stable samples free36373MiB/util0%; estimated fullpeak24576 plusmargin7275 fit. Own child3409891 started with FP16/autoawq_marlin/TP1/context4096/seq1/eager/KV256blocks/.60runtime+.60allocator/noCPUoffload. Health probe observed42.037s from its separate start, caches unflushed; not exact cold startup. Independent current-UID TCP inspection found five listeners all127.0.0.1. Initial observed aggregate baseline rise17126MiB/minfree19248MiB remained within guard limits. VLLM reports weights15.7406GiB, actual CUDA total39.39GiB*.60=23.64GiB budget (nominal board40GiB differs due reserved VRAM), and KV override uses256blocks rather than its larger computed available pool.

Startup log warnings about missing packed_modules_mapping and default MoE tuning were reviewed against this config and source; no incompatible mapping/kernel or OOM was observed. Weight header integrity and engine health do not establish Korean semantic quality. Root starts frozen v3/neutral/all40development×1/warmup5 next, with no heldout inference. Source/schema/parser/gold unchanged; original freeze0302507 and later documentation checkpoint28cfcab are pushed and verified.


## MoE v3 diagnostic failure

Run20260919T231243Z-194bbb3212944ebcb8e0e54bfa1b28b5, development40×1/warmup5: schema40/parser36/semantic34(85%), rawFP1/20, unsafeaccepted1/40, FN4/20; mean4.24096s/p956.07952s. F02 changes a source character, I02 fails source grounding, HD-A02 loses the negative sign, HD-B01 guesses unsigned direction, HD-D02 misclassifies one furniture's XY as multiple furniture, HD-F02 loses the scope/excluded target. Startup success does not satisfy semantic gate. Full results/resource/manifest preserved.

Next: reuse existing v4 with identical checkpoint/runtime/neutral sampling, all40 development once. If copying/interpretation failure persists, revisit the redundant generation representation rather than download more models or weaken gold/parser/gates. Existing1.0 parser/domain remains frozen throughout this comparison. Holdout still uncalled.


## 2026-09-20 08:31 KST — MoE v4 failure and next plan

Pushed3a13b240e4d1273db79947cf5d11c8becc9230f0 before v4 call. Evaluator: same explicit MoE revision/manifest/runtime, existing v4, neutral qwen3_nonthinking, output768/timeout60, all40development/warmup5/trial1. Run20260919T232550Z-fb632f6b5f1d405f9618dfe892b0f42a completed40 responses; server request count45→90. Schema40/parser37/semantic34/rawFP1/unsafe2/FN2, mean3.995633s/p955.909745s. Results/manifest/resource snapshot archived without edits.

Plan changed to separate quote-only generation2 adapter through unchanged1.0 parser, with explicit client mode and evaluator accounting. No new model/runtime install. Independent adapter boundary, prompt/client, and evaluator implementation/review work is separated by owned files. Holdout remains uncalled; no later Phase implementation.


Generation2 implementation checks: explicit adapter/schema/client/harness, no canonical1.0 source change. Full `env -u DISPLAY -u WAYLAND_DISPLAY bash scripts/test_backend.sh` with private PostgreSQL DSN: **290 tests PASS, skip0,17.329s** (`var/phase5x-generation2-regression.log`). Added regression forces a schema-valid but ungrounded adapter projection and verifies the final1.0 parser rejects it; raw READY remains visible. Independent replay of all12 historical hardening archives (640 trials) matches parser/errors/SI/scorer and complete metrics. New model quality remains unmeasured.


## 2026-09-20 08:44 KST — Generation2 actual diagnostic

Pushed91b464eee1d19ede3708ebb4ae0772dee0d35244; clean manifest before first2.0model request. Explicit --generation-contract2.0, generation2/v1 prompt+schema, same running MoE/neutral/output768,40development/warmup5/trial1. Run20260919T233958Z-5e2143732d36479ab880ab2fc32dfbb3 completed40; request count90→135. Generation shape40,adapter/parser/semantic29, rawFP1,unsafe0,FN0; latencymean4.132092/p955.313616s. All20READY gold pass; ten nonREADY null-rule violations and unsigned direction1 are retained failures. Independent40trials+5warmups replay exactly matches stage flags/projections/metrics.

Next: separate branch generation schema and generation2/v2 prompt, same frozen adapter/parser/gold/client/scorer. Null rules become generation constraints rather than posthoc stripping; generic unsigned-direction fewshot reflects existing policy. CPU grammar/token/context and independent review before committing/freeze/new run. No heldout inference or later Phase bypass.


Decision-branch CPU check: draft regex compiled but rejected Korean token fixtures; draft/result preserved and not used for inference. Removed only generation regex, backend nonempty rules remain. Final schema36d42b9f accepts13 valid (including7prompt examples) and rejects18 invalid (including root-only, nonREADYnonnull,READYnoaxis,wrongversion/extraapproval). Five grammar-valid backend-invalid controls are still rejected. GPU hidden/CUDA not initialized. Prompt99d73712, exact7exampleadapter parity PASS, dev max3678/held INPUT LENGTH ONLY3683 includingoutput768of4096. Targeted proof sufficient for prompt/schema-only change; previously290PASS source bytes unchanged. New freeze and preserved13th failed diagnostic committed before nextcall.


## 2026-09-20 08:57 KST — First expanded diagnostic PASS

Pushed29a6c7760423f8af79502ddc70fa1ba603b79a1c, hashesverified/currentguardRUNNING. All40development/warmup5/trial1 using generation2/v2 prompt +decisionbranches schema, sameMoE/neutral/max768/timeout60. Run20260919T235318Z-504ae53e55864b4fba35c6bb108c8c05 completed40; cumulative serverrequests135→180. Allschema/adapter/parser/semantic40/40,rawFP0/20,unsafe0/40,FN0/20; mean3.899002,p955.125593s. Results/resource/manifest archived unchanged, independentreplay requested. Formal40×3 freeze follows with same configuration. Holdout uncalled.


## Generation2 branch 정식 development 실패와 greedy 비교

Run20260919T235909Z-741a32ddc5394455943e3b480f8863c3,40×3/warmup5: schema/adapter/canonical/parser120/120,semantic119/120(99.17%),raw/acceptedFP0/60,FN0/60,unsafeaccepted1/120,mean3.994758s/p955.410634s. HD-F02trial3은 전체 current instruction과 -0.16m를 보존했지만 target을 `복도 쪽 낮은 장`으로 줄여 `연구실` 및 제외 대상을 빠뜨렸다. 이전 단회 PASS나 높은 평균으로 unsafe0 기준을 상쇄하지 않는다. 원본·manifest·resource를 그대로 보존했다. Holdout은 계속 미호출이다.

다음 비교는 prompt/schema/adapter/parser/scorer/model/runtime를 그대로 두고 기존 legacy_greedy 요청(T0/seed42)으로 전체40×3을 평가한다. 다른 sampling 필드는 생략하여 고정 서버 기본값을 따르므로 단일 temperature만 통제한 ablation으로 부르지 않는다. Greedy에서도 runtime 수치 비결정성은 가능하다. 과거4B/legacy계약의 greedy 실패도 보존한다. 새 representation+MoE에서 아직 비교하지 않은 decoding 차이이며, 실패case만 반복하거나 성공run만 선택하지 않는다. 현290testsPASS는 소스 변경 없이 유지된다.


## Greedy 정식 development PASS 및 첫 holdout 동결 준비

Pushed468f6f0e3b6ba83053c34292c8d9e506b0dfafb9 뒤 clean manifest로 시작했다. Run20260920T001240Z-7daf0ae403de40cfa9043c628abf9d8d:40×3/warmup5, schema/adapter/canonical/parser/semantic120/120,rawFP0/60,unsafe0/120,FN0/60,error0,mean4.394291s/p955.910858s. Server cumulative success305→430. 결과SHA b47a63f0927e90290e334b3a81e15b5fff71b25f49d2f88f84a0a4560d748d99. 모든 원본/manifest/resource를 보존했으며 독립120+5replay를 수행한다.

고정된 기존 heldout80을 처음으로 모델에 노출하기 전에 같은 모델·2.0branch·promptv2·greedy와 전체 source/runtime/data hash를 별도 freeze한다. 계획5warmups+240formal; schema240/240,semantic≥228/240,rawFP0/114,unsafe0/240를 유지한다. 첫 warmup부터 노출로 보며, 이후 튜닝하면 같은80개를 새 unseen 성공으로 부르지 않는다. 현 guard 잔여시간과245회×development평균/p95로 예산을 점검하되 timeout 최악시간까지 보장하지 않는다. 중단되면 INCOMPLETE/미통과다. 사람 미검수/입력·gold 사전AI검토/공유문법/반복상관 한계는 유지한다.


## 첫 holdout 실행 시작 및 generation2 Application 경계

첫 warmup 전에64040dee5e83a2966d7f4fff7de558e64fdc902c commit/push와remotehash일치를 확인했다. Frozen21개 파일·launch/runtime hash 및 clean Git을 다시 확인하고, guard 잔여2677.129초에서 같은MoE/2.0branch/promptv2/legacy_greedy/output768/timeout60으로 heldout80×3/warmup5를 시작했다. Run20260920T002629Z-6742bb1a50b44acd9e02228d83e2747d, manifestdirtyfalse, 시작servercounter430. 첫노출뒤 candidate/source/gold/gate 변경 없음.

동시에 별도의 고정 합성 generation2 JSON→canonical parser→RenovationService를 실제 privatePG/IfcOpenShell로 검증했다. 최종4probesPASS/skip0/1.250초,18개거절, 각headV0/revision1/importintent1/artifact1/sourcebytes불변. 최초probe의list/tuple비교오류만고친후재실행했고 Application 수정없음. 테스트가만든schema/artifact8개모두정리, 관련15개source/data해시전후동일. 이는 모델품질이아닌 승인경계검증이며 heldout출력은읽지않았다.


## 첫 holdout FAIL 및 자체 MoE 정상 종료

Run20260920T002629Z-6742bb1a50b44acd9e02228d83e2747d completed240+5; servercounter430→675. Schema240/parser231/semantic211,raw+acceptedFP9/114,wrongacceptedtarget3/126,unsafe12/240,FN6/126,UNGROUNDED9,mean4.215746s/p955.308297s. Original results SHA848827007c5381d3ca6ce67856822951f71154e1c499f33220975e34880588b3,240+5independentreplayexact. Sourcefreeze21hash/archivebytes/protocol/runtimeidentities일치. NoPhase5.xcompletion/noPhase6/no finalconfigadoption. Existing80becomesexposedregressionforfuturecomparisons; source/goldunchanged.

Verifiedownchild3409891 UID/startticks andparent3409876 expectedlauncher/reportarguments+unchangedstarttimebeforeSIGTERMguard. GuardSTOPPED/STOP_REQUESTED/childexit0/FileStorecleaned,elapsed5719.653s, aggregateincrementmax17732/minfree18642. Archivedshutdown_moe_instruct_epoch1.json. GPU3onlyfreshqueryafterexit:total40960/free36373/used3965/util0;rootdisk39Gfree/98%. Otherusersuntouched. Next bounded control: retained14Bwithidenticalnewgeneration2representation, GPU3freshbudget andCPUtemplate/grammar proofbeforelaunch. Newunusedholdoutv2preparedseparately.


## 14B + 동일generation2 CPU 검증과 새 launch

새 다운로드 없이 기존Qwen3-14B-AWQ31c69ef를 재사용한다. 실제tokenizer metadata9files size/SHA일치, embeddedtemplateSHAa55ee1b1…74d8, nonthinking빈thinkprefix는inputtemplate이며generatedreasoning아님. Dev40max3682/exposed80max3687including768 capof4096. CPUxgrammar8validEOS/14invalid/7promptadaptercanonicalPASS,CUDAnotinitialized. PreservedCPUproofSHAd609be2f…fd54a.

GPU3fresh5samplesfree36373/util0,peak18432+margin7275fitsbudget29098; FP16/autoawq_marlin/context4096/TP1/eager/seq1/KV256/fraction.50/allocator.50,새 child3446165. Health200/aliasneurobuild-local/ownTCP5loopbackPASS;초기 aggregatepeak10946/minfree25428. Logweights9.36GiB/CPUoffload0. 새 launchSHAe34887fa0896b8e8950be91a326f66b3a0f6799ccf96d1f08253ad2f76f6d4a4,metadataSHA2f814cf45f2c1d61c04dbef17699f63569f8fab194cdf799986081a326970b8a. 이번 cold startup 시간은 측정하지 않았다.

기존 dev40 bytes와 oldhold80 bytes를 변경 없이 결합한 exposed regression120의 SHA는7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b이며 READY62/CLF23/UNSUP35다. 전체120×1/warmup5의 동일2.0branch/promptv2/legacygreedy 진단을 별도 동결하며 과거 holdout 성공으로 취급하지 않는다.


## 기존14B generation2 노출120개 진단 FAIL 및 분리 실험 계획

Run20260920T005540Z-1f4757de74ec4e75adcc48e3c31c148d 완료120+5. Schema/adapter/canonical/parser120,semantic113,rawFP2/58,unsafe3/120,FN4/62,error0,mean3.0748559527s,p953.7770193405s. 독립 검토는 완료 당시 clean007d893 source를 git에서 ignored tree로 꺼내 SHA17개와120+5replay/전체metrics를 확인했다. 완료 이후 시작한 staged source 수정과 구분했다. Archive original bytes 보존, resultsSHAe160815a082b46d3055ec8cbf63b09f847d8e277e04ff7cdfbeb09a11e1154f9.

동일14B guard는GPU3에서계속RUNNING. 관측minfree24460MiB/aggregateincrement11914/floor7275,다른process변경없음. 신규다운로드없고rootdisk39Gfree/98%. 다음실험은 명시적classification→boundextraction두단계, fullsource양쪽전달, 기존2adapter/1parser필수, rawclassifierREADY를후단실패와무관하게집계한다. 새로운v2holdout80초안은별도작성/검토중이며모델호출없음.


## 두 단계 구현/회귀 및 unused v2 데이터 동결

LocalJSONCompletionClient로 기존 loopback/HTTP/두 dialect/sampling 전송을 공유하고 LocalRequirementClient의1.0/2.0 기본 동작을 유지했다. LocalStagedRequirementClient는 classification-1.0 → decision으로 제한한2.0 추출을 순차 호출하며, 전체 원문과 context를 양쪽에 전달한다. 기존 adapter SHA6c5c9d50…9f31과 parser SHAa940f395…4a는 불변이다. 독립 검토자가 재현한 RuntimeError 시 첫 분류 기록 손실을 수정했다. Ordinary Exception에는 첫 READY를 보존하고 안전 오류를 반환하며, BaseException은 전파한다.

기존 HTTP36개와 신규 staged15개, root의 staged 평가기9개 테스트가 통과했다. DISPLAY/WAYLAND를 해제하고 private PostgreSQL DSN으로 scripts/test_backend.sh를 실행하여 전체314 PASS/skip0/16.945초를 확인했다. 로그는 var/phase5x-staged-v1-regression.log다. Shared client SHA9732ad69f9f563f6acb3892ec0c187958d04d006a89251264779123445bc57c3, staged client SHA7e79b1c488a00e3f81b443fb32f86019f510a274228f56058c4eeae66038efee, evaluator SHAe114488454bd8289fb1de0462ae88c711b54917ac243db752e8400b95b66a36a.

V2 unused holdout은80개이며 A–J 각8개, READY40/CLARIFICATION20/UNSUPPORTED20이다. Dataset SHA7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40, dataset-only freeze SHA34e3823a6633faa5237849725f4b3120dee348aa19208d0c62403fedda5c5995. 사람 검수80행은 공란이고 모델 호출은0이다. 기존v1은 불변이며 독립 reference80개 검증과 중복 검사를 통과했다. 사전 gold의 모호성1건을 모델 노출 전에 명확히 했다. Root/prompt 작성자는 원문/gold 내용을 읽지 않았다. 최종 후보 동결과 모델 품질 평가는 별개다.

최종 actual transport로 v2의80개×3 decision=240 cycle/480개 요청 body를 in-memory fake opener에서 확인했다. 분류 source/axis와 추출의 classified_decision/schema를 포함한 JSON bytes가 기대값과 같았다. 입력을 출력하지 않고 실제 captured messages의14B token 최대값만 확인했다: 분류1125+128=1253, 추출1192+768=1960. 기존 데이터 freeze9개 hash는 불변이며 socket/network/model/GPU/weight 호출 없이 수행했다. 새 증거는 evaluations/results/phase5x/holdout-v2-preflight/staged_transport_binding.json, SHA540e2a47ad5a38309e12ebb6e009d94212f4651ac4e23e18701cc7f1aa91d2c1이다.


## Staged v1 독립 검토 및 GPU 진단 사전 동결

독립 검토에서 수정 후11개 downstream fault가 raw READY/FP1을 유지하고2개 interrupt가 전파됨을 확인했다. 기존1/2 × legacy/modern의4개 요청 wire bytes도 이전007d893과 같았다. Actual14B CPU grammar4개에서 valid8/invalid20 모두 예상대로 판정했고 exposed120의 양쪽 실제 message/token 최대는2035/4096이었다. CUDA는 초기화하지 않았으며 model/network/weight 호출은0이다. Proof SHA: CPU29382a48d00c286d1adff107550508799379d1d70aa4289565468867152da86f, error-accounting1da2cdde897f8624ed1a39ba70bc3ef4c0182611df69a98e6db0afd594c76223, wire-parity1c3a2fb6cd57dcc2fbca872c0d2fb396b1387cac5675d166b62f6cfe444bd81b.

기존14B epoch/동일runtime와 staged_v1/2.0/greedy를120×1+warmup5로 비교하는 후보 freeze를 작성했다. 파일31개 hash와 별도 unusedv2 dataset freeze9개 hash를 확인했다. 사전동결 SHA dd293c8bb3216335130915824e827fa0a3374ccea56d0ec65f586e5122a0d010. Schema120/120,semantic≥114/120,rawFP0/58,unsafe0/120 기준은 유지한다. Commit/push 및 clean source 재검사 전에는 모델 호출하지 않는다.


## 후보 동결 후 Git 검사에서 발생한 v2 입력 노출

`git diff --cached --check`가 검수 CSV의 CRLF를 trailing whitespace로 표시하면서 일부 v2 입력/gold를 root tool output에 노출했다. 직전 후보31개 파일 동결 뒤의 사건이며, 후속 hash 검증에서 prompt/code 포함31개 모두 동일했다. 이 시점에 root 입력 맹검은 종료됐고 앞의 미열람 문장은 과거 시점의 사실로만 해석한다. 모델은 아직 v2에 호출하지 않았다. 별도 hardening_v2_input_exposure_addendum.json과 현재 STATUS/report에 공개했다.

Freeze의 CSV bytes를 바꾸지 않고 `git -c core.whitespace=trailing-space,space-before-tab,cr-at-eol diff --cached --check`를 로그 파일로 redirect하여 재검사했고 PASS다. 초기 검사 실패 뒤에는 commit/추론을 실행하지 않았다. CRLF-aware 검사는 CSV 형식의 줄 끝만 허용하며 다른 trailing whitespace 검사를 유지한다. 향후 후보 변경 시 입력 노출을 다시 명시하고 독립 holdout 필요성을 재검토한다.


## Staged14B 진단 FAIL 및 모델 서버 종료

Pushed45858d6da4aba547be657812663e382eff717dda/clean 상태와 후보31hash·v2dataset9hash를 확인한 뒤 기존14B epoch에서 실행했다. Run20260920T013141Z-f3266f57faac473ebd0b9df66cb3cd75,120×1+warmup5, servercounter125→375. Schema120/parser103/semantic93,rawFP11/58,acceptedFP5/58,unsafe6/120,FN11/62,UNGROUNDED17,mean4.691022s,p955.581566s. 독립125개 재생에서 판정/SI/rubric/전체metrics가 같았다. 후보28hash를 독립 확인했고 미래v2관련3개는 해당 검토자가 읽지 않았다. 원본/manifest/dataset/replay/resource/integrity를 보존했다. ResultsSHAe1a7735a277ebd56dbbd6e8fc4bbb400f59b7eeab333a427f6f3b81870bbc905.

Own guard3446143/child3446165의 UID/startticks/model/report arguments를 확인하고 guard에SIGTERM을 보냈다. Guard는 STOP_REQUESTED/STOPPED, child_exit_code0, reaped, FileStorecleaned다. Shutdown에는 TERM과KILL escalation이 모두 기록됐다. Wrapper84605는exit0이었다. 종료 시 xgrammar/nanobind binding 정리 경고가 있었고 GPU자원은 반환됐다. Epoch elapsed3147.173s, minfree24460MiB, aggregate increment11914MiB. 종료 뒤 GPU3 free36373/used3965/util0. 다른 사용자의 process나 다른GPU는 변경하지 않았다.

디스크는 usable 약38.10GiB로32B 모델18.013GiB를 받을 경우20GiB reserve 위 약92MiB만 남으므로 충분한 운영 여유로 보지 않았다. 사용을 마친4B cache의3개 safetensors에 대해 즉시전체SHA/UID/regular-file/single-link/inode검증 후8,044,982,000 bytes를 제거했다. 기존 manifest/metadata/평가 결과는 그대로다. Free40909565952→48954236928 bytes(df46G). 정리기록과 복원명령을 evaluations/results/phase5x/unused_4b_weight_cache_cleanup.json에 보존했다.32B weight는 아직 다운로드하지 않았다.


## 공식32B 다운로드 전 checkpoint 준비

2026-09-20 11:02 KST. 공식Qwen/Qwen3-32B-AWQ rev0499c3ac83fdef8810b907a23894ba91e95eddd8의13파일manifest와 Apache2 LICENSE, 정적 호환성, provenance 및 메모리 계획을 보존했다. 총19,341,523,989bytes이며 manifestSHAfbb3d1c98f3ceeeceb2fd5306dde9439d1be12516dd5054c0b2f5a299a260e03. GPU3free36373/util0, wholepeak25600+margin7275 뒤3498MiB잔여다. 최종fraction.60/.60과allowance0을 명시한다. 실제CUDA가보고하는총량과non-Torch 때문에 fraction을 wholecap으로 해석하지 않는다. 현재45.59GiBfree에서 다운로드후27.58GiB를 예상하고 downloader의20GiB reserve를 유지한다. 새dependency/GPU모델호출/weightdownload는 이 checkpoint 전에 없었다.


## 32B 다운로드 완료와 저장dtype 불일치 조사

049ab13f15e34bf527846e5a121610047431b1a4 commit/push/remotehash/clean 확인 후 기존downloader를 실행했다. Exit0,13개파일SHA/size검증과 완료manifest일치,partial0, usable27.568GiB. GPU3별도5회preflight는minimumfree36373/util0/swing0, margin7275/wholepeak25600/remaining3498 PASS. Tokenizer/CPUgrammar는valid8/invalid14/예시7, exposed120최대3687 및v2 length-only3612/4096이었다. Header는실제707BF16과896I32를발견했고 configfloat16 가정과 달라 기동을보류했다. Loadercast와CPUfinite/FP16range검증을추가하며 원본weight/config는바꾸지않는다. 이시점32B GPU모델호출0.


## 32B CPU 경계 해결·실제 GPU3 기동·진단 동결

CPUheader1603/BF16707/I32896/shape-shard-offsetcoverage PASS. Indexmetadata19338405888 vs actualtensor19325298688 차이를보존했다. 추가CPU2threads/8MiBchunks로707BF16tensor/1,800,295,424원소를33.307초검사, nonfinite/FP16overflow/castnonfinite0. Scale448개는strictpositive/값변경0/zero0, 일반embedding/norm/head에서는392411rounding과2335zero를경고로보존했다. Tokenizer/grammar/context와loadercopy_경계까지검토하고actualGPU기동을허용했다. Source/prompt/gold/환경변경0,314회귀재실행하지않음.

CUDA_VISIBLE_DEVICES=3 .conda/bin/python scripts/model_server.py --profile a100 --model-path var/models/Qwen--Qwen3-32B-AWQ/0499c3ac83fdef8810b907a23894ba91e95eddd8 --dtype half --estimated-peak-mib 25600 --peak-allowance-mib 0 --gpu-memory-utilization 0.60 --torch-memory-fraction 0.60 --max-model-len 4096 --max-seconds 7200 --log-file var/logs/qwen3-32b-generation2-v2-server.log --report-file var/reports/qwen3-32b-generation2-v2-server.json

Guardsession97831/child3467850, fresh5samplefree36373/util0/swing0/margin7275. ActualAWQMarlin/FP16기동, weight18.1453GiB/activation0.76GiB/nonTorch0.09GiB/KV256. Health200 및v1/models의alias/root/context확인; ownTCP5개127.0.0.1 PASS. 초기minfree16042/aggregatepeak20332. 현재환경버전도별도importmetadata/TorchCUDA와GPU3name/driverquery로runtime_metadata와일치확인. 아직inference호출0.

Freeze helper를실행하여 actualCPU/header/cast/download/launch/listener/source연결29hash와v2freeze9hash를검증했다. Single32B120x1 사전동결SHA0e525113175e9617c2f46f3e32958b184dd4d76918873157ee978de25d26e023. Independentreview/commit/push/clean재검사뒤에만warmup을시작한다.


## 32B single 진단 시작

Pushededb586af8e8cefd10b4e2574d48b7d1cf24cc8e1/remotehash일치/clean/freeze29hash확인후2026-09-20T02:23:18Z 시작. Run20260920T022318Z-88be9f58a8fa4017b9ad432ea95740b9, pipeline single/contract2.0/branchschema/promptv2/legacy_greedy, exposed120×1+warmup5/output768/timeout60. Manifestdirtyfalse. Own32Bguard잔여6889.53초에서시작했으며모델품질결과는아직미완료다. 시작뒤source/prompt/gold/gate변경없음.


## 32B 단일2.0 FAIL 및 자체서버 종료

Run20260920T022318Z-88be9f58a8fa4017b9ad432ea95740b9 exit0/125HTTPsuccess/120trial+5warmups완료. Schema/parser120,semantic103,raw+acceptedFP1/58,unsafe1/120,FN11/62,error0,mean5.077785380704639s,p956.068347116932273s. 125개독립replay/전체row/metrics일치. ResultsSHAf6ba0506921464c084899d7cfa457d6241b685e952caffa224c71f842472eec3. FAIL보존,formal미실행. 다음한호출facts계약을설계검토하며source/prompt/gold/gate는아직변경없다.

자체child3467850/guard3467820의UID/startticks와정확한model/report인자를재확인한뒤guard에SIGTERM. Guardsession97831exit0, STOPPED/STOP_REQUESTED/child_exit0/reaped/FileStorecleaned이며TERM+KILL이기록됐다. Epoch998.119초,minfree13834/aggregatepeak22540. ShutdownSHA8f47637db6434a67782132864146d21c954ea42dfc9406cdef21362f12275894. GPU3free36373used3965util0복귀. 다른process나GPU0/1/2변경없음.


## Facts3.0 구현 및 실행 전 검증

기존32B 실패 checkpoint16d67895 뒤 explicit3.0 enum/adapter/prompt/schema/client/evaluator를 추가했다. 한 호출의11개 facts와최종rootdecision을검증해 원래6값을그대로2.0으로투영하고 기존2→1adapter/canonicalparser를반드시통과시킨다. 누락의미를코드로추가하거나decision을보정하지않는다. 평가기는검증전rawREADY와각단계통과여부를별도기록한다. 기존1/2defaultwire6쌍byteequal,2adapterhelper3개AST/함수본문동일,canonicalparserSHAa940f395…fb4a불변.

BackendprivatePG DSN으로 env -u DISPLAY -u WAYLAND_DISPLAY bash scripts/test_backend.sh 실행:346testsPASS/skip0/18.730s, log var/phase5x-generation3-regression.log. 신규17facts+9평가기+6실제loopbackHTTPtests다. 개발중두testfixture오류를수정했고production거절규칙은완화하지않았다. CPU actual32tokenizer/payloadcapture200회:exposed최대3622/4096(output1024포함),v2길이만3547. xgrammar0.1.18의24controls와두예시/domain통과,10rawREADY오류경로분자·분모보존,interrupt전파확인. 실제모델품질호출은아직0이다.

FreshGPU3preflight5회free36373/util0/swing0, wholepeak25600+margin7275 뒤3498MiB잔여PASS. 같은모델/FP16AWQMarlin/ctx4096/seq1/KV256/fraction.60/.60/allowance0로 새generation3-v1 epoch기동을시작했다. Guard는자체5회preflight를반복한다. 이번epochmaxseconds10800으로제한하고freefloor/aggregate감시를유지한다. 다른process변경이나GPUfallback없다. rootfilesystemdf28Gfree/99%이며새download/install은없다.

새32B facts epoch 2026-09-20T02:56:53.177123Z, own guard3476219/child3476232. Health200/v1models alias·root·ctx4096, ownTCP5개127.0.0.1검증. FreshCPUversionprobe와localtemplate를새launch/runtimehash에연결했다. Initialsnapshotelapsed186.288s/minfree16060/aggregate20314/floor7275/limit25600. AWQMarlinFP16/weights18.1453GiB/activation.76GiB/KV256. 새freeze820c16c7bd130666fbe8e2446cfd22a308cd9902c4bb1b3ac3481961939bb831는44개source/proofhash와별도v2고정9개를검증했다. 진단120×1+warmup5/generation3.0/output1024/T0/onecall,gate불변. 아직completion0이며commit/push후freshliveness와hash를확인하고시작한다.


## Facts3.0 실제 진단 FAIL 및 서버 종료

Commit/push/remotehash/clean c6bdbeb400c37016897bfe6b08ab080cc33ee8cf와 freeze44hash/현재own runtime을 확인했다.
2026-09-20T03:02:27Z부터 run20260920T030227Z-e8d3568e4a1243d69e674ea3d6fc9727을 실행했다.
Session18482 exit0,125요청 완료, schema120/facts101/parser99/semantic95/rawFP3/58/unsafe1/120/FN10/62,
UNGROUNDED21,mean7.859892285009846/p959.356667160987854. Warmup5는 semantic4이며 평가 분모에서 제외했다.
독립125개 재생과 집계가 일치했다. Exit0는 결과 저장 완료이며 품질 gate는 FAIL이다.

모델 응답·gold·parser를 수정하지 않았다. Source/프롬프트/평가 조건은 실행 중 고정했다.
Own guard3476219/child3476232의 UID·startticks·model/report 실행 인자를 확인하고 guard에 SIGTERM을 보냈다.
Session2033 exit0. STOPPED/STOP_REQUESTED/child exit0/reaped/FileStore cleaned, TERM+KILL 기록을 확인했다.
Epoch1402.678초/minfree14512/aggregatepeak21862. Shutdown artifact SHA
a5b7608a9205d5509095284b7ee86e2f6214949d153bbb0b946b688b725e43b6.
종료 뒤 nvidia-smi GPU3 only는 total40960/used3965/free36373/util0이었다.
다른 사용자 process와 GPU0/1/2 변경은 없었다. Formal 반복은 시작하지 않는다.


## 기존2.0 계약의 thinking 제한 비교 준비

실패 기록과 다음 계획을0fd60350b6e9df6538e5cf3d1ee1b13fa949fccc로 commit/push했고 remote hash 및 clean을 확인했다.
별도 thinking prompt는 기존generation2/v2 첫 줄의 출력 지시만 최종 content에 적용됨을 명시하며,
첫 줄 이후의 정책·7예시는 byte 그대로다. 신규 파일 SHA db1880ecebf697a215d4f3fedb970e0cdb1668837d0b121c92276cda8f6870e2.
Application·schema·parser·gold 변경은 없으며 기존346 회귀 결과를 유지한다. 최종 prompt로 CPU 검증을 별도 수행한다.

FreshGPU3 preflight5회는 free36373/util0/swing0, peak25600+margin7275 뒤3498MiB로 PASS였다.
Guard가 같은 조건을 다시 측정한 뒤 같은32B/FP16/AWQMarlin/ctx4096/seq1/KV256/.60/.60/allowance0를 기동했다.
새 session93856, --enable-reasoning 명시, maxseconds10800, generation2-thinking-v1의 새 log/report 경로다.
보고서에서 enable_reasoning=true/deepseek_r1 및 own child3483717 RUNNING을 확인했다.
Startup 관측 minfree16060/aggregatepeak20314였다. Model completion은 아직0이며 CPU·runtime 증거와
사전 동결·원격 checkpoint 확인 뒤에만120×1+warmup5를 실행한다. Disk df28G/99%, 추가 설치·다운로드 없음.

최종 독립 CPU proof는200 fake payload/7예시/grammar/추론 경계 검증 PASS이며, exposedmax3947/4096 및v2길이만3872/4096이다.
CPU proof SHA2b40e70de79b7f0224f7afd80079246c9cb2c4f34286ab89a405290915d2002c.
새 runtime five JSON은 own guard3483689/child3483717와 실제 true/deepseek_r1/5loopback에 연결했다.
Thinking freeze e0bf7d237fdbfa61d3e4fe09aefa6d706872a4a3db100fec5541ec0eebc0c19d의41파일 hash를 독립 재검증했다.
V2 보존9개/weight4stat/기존346회귀log도 확인했고 모델 호출은 아직0이다. 정식 품질 성공이나 완결성 보장이 아니다.

## 32B thinking 제한 진단 완료 — FAIL

Pushed59e9b64312e32582371553a3a243bd566a72c845/clean 및 freeze41개 hash 확인 후
2026-09-20T03:40:14Z부터 run20260920T034014Z-0e8af7789bbe419db3f717de65242735를 실행했다.
Single2.0/branch/thinking-v1/qwen3_thinking_awq, 총completion1024/timeout120,
exposed120×1+warmup5다. Session69648 exit0은 저장 완료를 뜻하며 품질 gate는 FAIL이다.
Schema117/parser116/semantic109, rawFP2/58/acceptedFP1/58/unsafe1/120/FN0/62,
TRUNCATED3/UNGROUNDED1, mean19.93557890569015s/p9529.995699994266033s다.
Results SHA959202b4690d96856ffc95a50caa49e29e1579d479f41b8811d6f583bd559009.
보존된117trial+5warmup의 독립 frozen 재생과 전체 metrics가 일치했다.
잘린3응답의 body/decision은 보존되지 않아 raw unknown이며 전체 관측117/120,
non-READY 관측55/58을 함께 기록한다. 원래 분모에서 제외하거나 non-READY 정답으로 바꾸지 않았다.

실패11개는 truncation3, lookup→unsupported4, non-READY target 누락2,
분수1/2m의 raw READY1(parser 거절), 방화문 이동 raw READY1(parser 수용)이다.
Raw label 정답111/120, READY gold62개는 모두 semantic 정답이다. Reasoning 본문은 열람·보존하지 않았다.
완료된 Phase5.x 누적은22run/1800평가trial/110warmup사례이며 합산 정확도로 해석하지 않는다.

독립 RUNNING resource snapshot 보존 후 own guard3483689/child3483717의 UID/startticks/
PPID/model/report 인자를 재확인하고 guard에SIGTERM을 보냈다. Session93856 exit0,
STOPPED/STOP_REQUESTED/child exit0/reaped/FileStore cleaned, TERM+KILL 기록을 확인했다.
Epoch3144.173초/minfree13832MiB/aggregatepeak22542MiB, shutdown SHA
16fc05d924f0584eeb8d0b42a806ebfb830a7aace6dae668cec0a0a1958136c8.
2026-09-20T04:23:30Z 종료 뒤 GPU3 used3965/free36373/util0이었다. 다른process/GPU 변경은 없다.
Formal 반복과 Phase6는 시작하지 않는다. 다음은 pinned llama.cpp/Qwen3.8-27B의
HOME 내 CPU source-build 가능성과 별도 안전 경계를 먼저 검증하는 계획이다.

## Native runtime source build와 CPU 계약 준비

고정 llama.cpp f072b103714dfa1eee531f80b24512faf38e3dd2와 CMake3.23.5를 project의
ignored var 아래 준비했다. Bootstrap에서3,607 Git blobs/172,243,701 bytes와 파일 mode,
archive 및 tool digest를 확인했다. 시스템 CUDA/Driver/Python과 기존 두 Conda 환경은 변경하지 않았다.
CUDA mask를 비우고 GCC9.5/nvcc11.8/명시80-real/parallel2, 낮은 disk budget과 자체 child guardian으로
configure→ggml-cuda→llama-server를 수행했다. 2026-09-20T04:56:31Z~05:17:17Z, 세 단계exit0,
child group cleanup/reaped 모두 true. 원본 report SHA0c78c5b9a927408986e024d3ef5adad6cb420d3a9aaae8d88be89a8eb2f19654.

정적 ELF 검사에서 빈 RUNPATH tail을 발견해 source/object를 바꾸지 않고 `$ORIGIN`으로 relink했다.
334개 object inventory와 compile commands는 동일했다. 최종 binary SHA
a0494b9885b25ba4cc2679dae5077e7ab18ad5baff161a7a152f19f43afdca0d.
후속 verifier의 CMake cache regex가 빈 줄/주석을 key에 포함하는 오류를 고쳤으며 물리 행 단위와
중복 key 거절14개 검사를 통과했다. 최종 정적 report는
ee6004f691015540ed694f721de7a0fd05ddc37b406419f9e527a860e6cb8b37,
runtime libraries8/aliases14/source3,607/SM80 CUDA commands143 확인이다.
GGML build string unknown은 source archive의 Git history 부재이며 전체 tree hash 검증과 구분한다.
Native executable/GPU 모델은 이 단계에서 실행하지 않았다.

Native client의 기존 wire24개를52ffb5a checkpoint와 byte 비교했고 동일했다. Canonical parser 불변.
독립 launcher 검토에서 output이 native proof를 덮어쓸 수 있는 충돌을 발견해 실행 전 거절로 수정했다.
다운로드 완료 순간 경쟁 target을 덮어쓰는 기존 replace도 atomic link publication으로 고쳤다.
실제 private PostgreSQL DSN/headless 전체 회귀382tests PASS/skip0/20.178s,
log var/phase5x-native-runtime-regression-v3.log. 기존376/379회 결과와 최종382회를 구분한다.

MoE cache 정리 첫 시도는 같은UID nondumpable 로그인서비스 maps 접근 거절로 삭제 전에 중단됐다.
정확한 sd-pam/sshd cmdline·comm만 확인 가능한 예외를 명시하고 다른 접근 거절은 계속 차단했다.
자기27개 process maps/FD 검사 및 종료증거/project lock/각 shard size·SHA 확인 후4개를 제거했다.
16,809,467,824B 회수, free45,528,395,776B. Report SHA
7e6024c2cbc148eec7861fd97da531c324bfd98706919407b1699d32b5652ee8.
두 로그인서비스 메모리/FD는 미확인으로 남겼고 다른 사용자 process는 읽거나 변경하지 않았다.
Metadata/manifests/results와 복원 명령은 보존했다.

단일 Qwen3.8-27B-Q4_K_M guarded download를 시작했다. 당시 free42.4GiB에서 weight17.67GiB와
CPU build3GiB 상한을 모두 차감해도21.73GiB가 남아20.5GiB floor를 충족했다.
Download는2초 disk poll/1800초 phase timeout/자체 descendant 정리로 보호한다.
별도 CPU-only native contract helper도 같은 source와 guardian으로 build를 시작했다.
실제 tokenizer JSON을 읽는 CPU-only tokenizers library로 공개 합성20개 fixture를 만들었다.
이는 native tokenizer parity PASS가 아니며 실제 helper/header/전체 VRAM 검증이 남아 있다.


### 2026-09-20 — GGUF 검증 완료와 CPU tokenizer 원인 분리

Guarded download는 PASS, GGUF18,973,870,528B/SHA c600de0300ae8a0eb3a6c0b8b96f16bd2c863c2a66c42de29d391a747이다.
다운로드 최소 free24.65356GiB로20.5GiB floor를 유지했고 자체 curl descendant를 reaped했다.
전체 GGUFv3/header851 tensor/packed coverage/metadata/template 검사는 PASS,
report SHA ff168aeee125b2934b8b5204c14971915c7555c5dfc660d6fda46c2bf7fc810a.
이는 weight 수치 검증이나 GPU tensor 배치 확인이 아니다.

CPU helper 첫 compile에서 custom JSON 정수 비교 오류가 발생했다. 타입 확인 후 int64 비교로
수정한v2 build는 PASS, upstream194 object/static library는 불변이었다. 공개 grammar10accept/
20reject, final content10개, generation prefix41bytes, sampling/schema 연결과 stderr0을 확인했다.
Vocab/context 시도는 실패했다. 본문을 출력하지 않는 공개 합성 진단v3/v4로 원인을 분리했다.
공식 HF reference19/20 FAIL(index11), native raw roundtrip20/20, NFC만 끈 별도 reference20/20이다.
원래 fixture SHA79c4448b7ee949add0a80e8a7f0fc0d73575aaf01ff6e52beb3cfae8434ea1bd 불변.
실패/이전 binary·source·report를 보존했고 D033에 raw-Unicode 실험 후보와 한계를 명시했다.

GPU3 driver metadata만 별도 조회해 UUID/count1, VMM 지원과2MiB allocation granularity를 확인했다.
Context 생성이나 할당은 요청하지 않았고 조회 전후 free36,373MiB/util0%였다.
CUDA-linked llama binary/model inference는 아직0회다. Native 전체 peak 예산28GiB의 독립
source/VRAM 검토를 마쳤으며 fresh GPU3 측정과 별도 실제 raw-native context 검증이 남아 있다.


### 2026-09-20 15:30 KST — Raw native context PASS와 첫 GPU startup FAIL

별도 CPU raw context wrapper는13개 fake 검사를 통과하고 독립 읽기 검토를 마쳤다.
실행에서 exposed120 native input2133~2409/+768최대3177,
v2길이80 input2154~2365/+768최대3133 PASS, model inference0.
보고서 SHA5d37568d7b51d1b689b168f0e9fa6fb46ac487b70f451c82611c146f978e59be.
공식 HF19/20 FAIL과 rawreference20/20/원문roundtrip20/20을 함께 고정했다.

`CUDA_VISIBLE_DEVICES=3 CUDA_DEVICE_ORDER=PCI_BUS_ID .conda/bin/python -B scripts/llama_server.py
--config var/research/qwen38-native-launch-epoch1.json`으로 첫 시작을 실행했다.
Config SHAc92048ae165dc62f4548e30a294459d5ed1c2e07d2a934c495a39517ccb6510e.
전체GGUF/hash검증 후 fresh5회 free36373/util0/swing0으로 예산28672+margin7275를 통과했다.
Child3527525의 허용장치UUID/count 확인 후7.781초에SIGABRT(-6) CHILD_EXITED.
STOPPED/TERM+KILL/reaped, observedaggregatepeak18290/minfree18084이다.
종료 후 nvidia-smi -i3 free36373/used3965/util0. HTTP/model evaluation 요청은0회다.
Startup 내부 warmup 실행 여부는 미확인이고 runtime readiness PASS를 주장하지 않는다.
원래 stdout/stderr는폐기되어 원인미상이며 OOM이라단정하지 않는다. raw본문저장 없는 제한된
stderr code/source 위치 진단을 준비한다. 실패config/report는 epoch1-failed archive에 보존했다.
