# NeuroBuild_v2

A100과 RTX5090에서 같은 Application 코드를 사용하는 BIM 시스템의 greenfield rewrite.
현재 **Phase 0: Cross-Server Environment & Architecture Foundation**이다.
Application, DB, IFC Engine, model server, frontend는 아직 구현/설치하지 않았다.

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
URL은 localhost 예제, model은 미선정, runtime은 `NOT_TESTED`다. [설정 안내](configs/README.md)

## 문서

| 문서 | 내용 |
|---|---|
| [Phase 0 보고서](docs/phase0_report.md) | 요청한 24개 항목과 검증/남은 결정 |
| [프로젝트 맥락](docs/project_context.md) | Greenfield 범위와 계승할 원칙 |
| [아키텍처](docs/architecture_blueprint.md) | 공통 코드, 승인/Revision/Artifact/Worker/Viewer 설계 |
| [환경](docs/environment.md) | A100 실측, 환경2개/디스크/cache 계획 |
| [호환성](docs/runtime_compatibility.md) | A100 측정과 RTX5090 미검증 구분 |
| [모델 후보](docs/model_selection_plan.md) | 최신 공식 출처의 후보5개와 평가 우선순위 |
| [평가 계획](docs/model_evaluation_plan.md) | 한국어/BIM 평가 metric과 재현 방법 |
| [평가 seed](evaluations/requirement_seed.jsonl) | 10개 분류의 synthetic 사례20개 |
| [Roadmap](docs/implementation_roadmap.md) | Phase0–10/5.x와 각 단계 완료 조건 |
| [Git 운영](docs/git_workflow.md) | 기존 이력 보존, 공통v2, commit/push 준비 |

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

`.conda`, `.conda-vllm`, `var/`, Application `src/`, frontend는 아직 생성하지 않았다.
서버별 `runtime/`에는 dependency 계획만 있고 Application 소스 복제는 없다.

## 현재 제약과 다음 단계

- A100은 40GB이며 허용 GPU3에 예상 밖 process3개가 있었다. 종료/변경하지 않았다.
- root disk는 조사 당시96% 사용, 약86G 남음. 대형 설치/모델 다운로드를 보류한다.
- driver535.183.01에서 최신 후보의 검증된 vLLM build는 아직 없다.
- RTX5090은 예상32GB/physicalGPU1 계획이며 실제 runtime/benchmark는 미검증이다.
- 현재 Git 작성자 미설정으로 milestone commit/push는 아직 없다. 상세 상태는 보고서를 따른다.

**Phase1은 사용자 승인 후에만 시작한다.** 환경/모델 설치 없이 Domain 계약 설계를 먼저 진행할 수 있다.
