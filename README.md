# NeuroBuild_v2

A100과 RTX5090에서 같은 Application 코드를 사용하는 BIM 시스템의 greenfield rewrite.
현재 **Phase0~5 원격 checkpoint 완료**, **Phase5.x 미완료·모델 미채택·Phase6 미시작**이다.
전체 회귀 테스트는 **395개 PASS, skip 0**이며 PostgreSQL/IfcOpenShell과 headless 조건을 포함한다.
Qwen3.8-27B 단회120개는 semantic117/120, rawFP0/58, unsafe0/120으로 첫 gate를 통과했다.
Warmup 포함125개 독립 재생 PASS를 보존하고 반복하지 않았다. 이후 V2 단회80개는
semantic73/80, rawFP1/40, unsafe1/80으로 실패했다.
다른 후보 Gemma4-31B QAT의 첫120개도 semantic115/120이나 rawFP1/58, unsafe2/120으로 실패했다.
각 결과와 자체 모델 서버 종료·GPU3 VRAM 반환 증거를 보존했다. 실제 IFC 실행은 없었다.
동일 모델 전체3회 반복을 취소했으며, 명백한 실패 후보는 재평가·V2 없이 다른 후보 비교로 넘어간다.
Gold는 자동 생성·사람 미검수이며 Internal Technical MVP는 아직 완료되지 않았다.
최신 상태는 [STATUS](docs/STATUS.md), 비교 수치는 [실험 목록](docs/phase5x_experiment_register.md)을 따른다.
Durable review/job queue, API와 frontend는 후속 단계다.

LLM은 요구사항을 구조화하고, 결정론적인 BIM Engine이 승인된 변경을 실행한다.
첫 vertical slice는 IFC4의 단일 IfcFurniture를 같은 층에서 상대 XY 이동하는 `MOVE_FURNITURE`다.

작업 root는 `/home/a202192020/NeuroBuild_v2`, 공통 개발 branch는 `v2`다.
기존 구현은 Git 이력과 기존 디렉터리에 보존하며 새 코드에 편입하지 않는다.

## 빠른 확인

패키지 설치 없이 설정을 확인한다. 이 명령은 서비스/GPU를 실행하거나 probe하지 않는다.
시스템 Python은 이 기본 진단에만 사용하고 향후 Backend 개발은 Python3.12 `.conda`에서 진행한다.

```sh
cd /home/a202192020/NeuroBuild_v2
/usr/bin/python3 scripts/show_runtime_info.py --profile a100
/usr/bin/python3 scripts/show_runtime_info.py --profile a100 --json
```

RTX5090 profile도 `--profile rtx5090`으로 열람할 수 있다. 이는 원격 서버 테스트가 아니다.
Profile은 필수이며 shell에 다른 `CUDA_VISIBLE_DEVICES`가 설정돼 있으면 오류를 반환한다.
URL은 localhost 기본값이다. A100은14B-AWQ의 inference/seed평가를 실측했고 RTX runtime은 `PREDICTED_UNVERIFIED`다. [설정 안내](configs/README.md)

## 문서

| 문서 | 내용 |
|---|---|
| [MASTER PLAN](docs/MASTER_PLAN.md) | Phase11 Internal Technical MVP까지의 자율 개발 목표/완료 조건 |
| [STATUS](docs/STATUS.md) | 재개 시 확인할 현재 단계와 blocker |
| [DECISIONS](docs/DECISIONS.md) | 결정/대안/재검토 조건 |
| [EXECUTION LOG](docs/EXECUTION_LOG.md) | command, 검증 결과, 실패와 수정 기록 |
| [Phase 0 보고서](docs/phase0_report.md) | 요청한 24개 항목과 검증/남은 결정 |
| [프로젝트 맥락](docs/project_context.md) | Greenfield 범위와 계승할 원칙 |
| [아키텍처](docs/architecture_blueprint.md) | 공통 코드, 승인/Revision/Artifact/Worker/Viewer 설계 |
| [환경](docs/environment.md) | A100 실측, 환경2개/디스크/cache 계획 |
| [호환성](docs/runtime_compatibility.md) | A100 측정과 RTX5090 미검증 구분 |
| [모델 후보](docs/model_selection_plan.md) | 최신 공식 출처의 후보5개와 평가 우선순위 |
| [평가 계획](docs/model_evaluation_plan.md) | 한국어/BIM 평가 metric과 재현 방법 |
| [확대 평가 실험 목록](docs/phase5x_experiment_register.md) | 실패를 포함한 모든 Phase5.x 실행과 고정 gate |
| [평가 seed](evaluations/requirement_seed.jsonl) | 10개 분류의 synthetic 사례20개 |
| [Roadmap](docs/implementation_roadmap.md) | Phase0–11/5.x와 각 단계 완료 조건 |
| [Git 운영](docs/git_workflow.md) | 기존 이력 보존, 공통v2, commit/push 준비 |

IFC 지원 범위는 [IFC Engine 계약](docs/ifc_engine.md), 별도 확인·승인·Apply 흐름은 [Workflow 계약](docs/workflow.md)을 따른다.

## 현재 디렉터리

```text
NeuroBuild_v2/                 # 이 checkout root가 새 프로젝트
├── AGENTS.md
├── README.md
├── .gitignore
├── configs/
│   ├── common.json
│   ├── a100.json
│   ├── rtx5090.json
│   ├── runtime.env.example
│   └── README.md
├── scripts/show_runtime_info.py
├── docs/
├── evaluations/requirement_seed.jsonl
├── requirements/README.md
├── runtime/
│   ├── a100/README.md
│   └── rtx5090/README.md
├── NeuroBuild_v1/              # 기존 main의 과거 자료, 미변경/미사용
└── NeuroBuild_v2/readme.md     # 기존 2-byte placeholder, 미변경/미사용
```

Backend `.conda`, local data `var/`, Application `src/`, `tests/`, `migrations/`가 있다.
`.conda-vllm`에는 모델 전용 runtime을 설치했고 frontend는 후속 단계다. 환경·weight·data는 Git에서 제외한다.
서버별 `runtime/`에 재현 정의를 두며 Application 소스 복제는 없다.

## 현재 제약과 다음 단계

- A100은 physical GPU3만 사용한다. 가용 VRAM·utilization과 전체 peak 추정·안전 margin을 비교하며 다른 프로세스를 변경하지 않는다.
- 모델 다운로드 전후 디스크를 측정하며 20GiB reserve를 유지한다.
- driver535.183.01에서 cu118 vLLM0.8.5/Qwen3-14B-AWQ를 검증했다. 최신 architecture용 runtime은 별도 검증이 필요하다.
- RTX5090은 예상32GB/physicalGPU1 계획이며 실제 runtime/benchmark는 미검증이다.
- GitHub SSH 인증이 해결됐고 공통 `v2` push를 확인했다. Phase0 현재 이력은 `a2761eb`, 자율 실행 계획은 `f131644`다.

**Phase별 승인 대기는 폐지했다.** Quality Gate와 commit/push를 통과하면 Phase11까지 자율 진행한다.
최신 진행 상황과 검증 결과는 STATUS를 따른다.

## Backend와 private PostgreSQL

환경 재생성은 [requirements](requirements/README.md), persistence 계약은 [persistence](docs/persistence.md)를 따른다. Checkout 기반 editable 실행을 지원한다.

```sh
.conda/bin/python scripts/postgres.py init
.conda/bin/python scripts/postgres.py start
export NEUROBUILD_TEST_DSN="$(.conda/bin/python scripts/postgres.py dsn)"
bash scripts/test_backend.sh
```

PostgreSQL은 project `var/postgres`와 private Unix socket을 사용하며 TCP를 열지 않는다. 종료는 `.conda/bin/python scripts/postgres.py stop`이다. DSN 없이 테스트하면 PostgreSQL 통합 검증은 skip되므로 Phase gate로 인정하지 않는다.
