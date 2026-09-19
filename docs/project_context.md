# NeuroBuild_v2 프로젝트 맥락

기준일: 2026-09-19. 현재 단계는 **Phase 0 — Cross-Server Environment & Architecture Foundation**이다. 이 문서는 제품 목표와 결정의 배경을 보존한다. 서버 운영 제약은 전역 `/home/a202192020/.codex/AGENTS.md`, 저장소 작업 규칙은 루트 [AGENTS.md](../AGENTS.md)를 따른다.

## 재구축의 출발점

기존 RTX 5090 서버에서 개발하던 최신 NeuroBuild_v2에는 현재 접근할 수 없고, GitHub에도 완전한 백업이 없다. 이번 작업은 그 구현의 복구를 가정하지 않는 **greenfield rewrite**다. 사용자가 제공한 제품 원칙과 아키텍처 경험을 계승하되, 과거 구현을 검증 없이 가져오지 않는다.

- 현재 A100 프로젝트 root: `/home/a202192020/NeuroBuild_v2`.
- 중앙 source of truth: <https://github.com/eys632/NeuroBuild>.
- 새 개발 위치는 checkout root다. 저장소 안의 기존 `NeuroBuild_v1/`과 중첩 `NeuroBuild_v2/` placeholder는 과거 참고 자료로 보존하며 새 Application에 연결하지 않는다.
- 공통 개발 브랜치는 `v2`다. 기존 `origin/main`의 `0914597`에서 시작하여 과거 이력을 보존한다. 서버별 장기 Application 브랜치를 만들지 않는다.
- 기능 개발은 필요할 때 짧은 `feature/...` 브랜치를 사용하고 공통 `v2`로 통합한다. 기존 브랜치 삭제, force push, history rewrite는 하지 않는다.

## 단일 코드베이스의 의미

같은 commit을 checkout한 A100과 RTX 5090은 같은 Application 기능을 가져야 한다. Domain, Application Service, Persistence, migration, IFC Engine, Requirement Pipeline, Object Resolution, Job/Worker, API, Frontend, schema, prompt, tests는 공통이다.

차이는 다음 경계에 둔다.

| 계층 | 공통 또는 서버별 내용 | 관리 위치 |
| --- | --- | --- |
| Common Application | 제품 동작, 데이터 계약, workflow, 검증, 테스트 | 향후 `src/`, `schemas/`, `prompts/`, `tests/` |
| GPU / Model Runtime | GPU 노출, 호환 PyTorch/vLLM build, CUDA runtime, dtype/quantization, context, memory 설정 | `configs/<profile>.json`, `runtime/<profile>/` |
| Network / Deployment | hostname, URL, port, model endpoint, 로컬 경로와 secret | 공통 설정·profile·환경변수; local secret은 Git 제외 |

서버별 소스 복제, `if gpu == "A100"` 같은 business logic 분기, 고정 서버 IP는 허용하지 않는다. Runtime 구현은 Adapter 경계에 두고 공통 Application 계약을 따른다. Model precision이나 build가 달라지는 경우 모델 출력의 동등성은 별도 평가 대상이며 설정만으로 동일 품질을 보장하지 않는다.

Git은 source의 기준이다. DB, 사용자 IFC, artifact, model weight를 Git으로 동기화하지 않는다. 같은 source를 두 서버에 배포해도 사용자 데이터가 자동으로 공유되는 것은 아니다. 장기 gateway 전환에는 DB와 artifact의 일관된 백업·이동·복구 정책이 추가로 필요하다.

## 실제로 확인한 것과 앞으로 확인할 것

| 환경 | 증거 수준 | 해석 |
| --- | --- | --- |
| A100 | **MEASURED**: 2026-09-19 read-only 조사 | 서버 상태 확인만 수행했다. Application, IFC, DB, Model runtime 동작 검증을 뜻하지 않는다. |
| RTX 5090 | **PREDICTED / PREVIOUSLY KNOWN / UNVERIFIED** | 사용자 제공 과거 사양과 공식 호환성 자료에 근거한 계획이다. 이번 작업에서 접속·설치·실행·benchmark하지 않았다. |

A100의 할당 GPU는 physical GPU 3이며 GPU 0/1/2를 사용하지 않는다. RTX 5090은 physical GPU 1, 계획 VRAM 32GB이며 GPU 0 fallback을 금지한다. 각각 `CUDA_VISIBLE_DEVICES=3`, `CUDA_VISIBLE_DEVICES=1`로 한 장만 노출하고 프로세스 안에서는 `cuda:0`, tensor parallel은 1을 사용한다.

A100 read-only 조사에서는 GPU 3에 기존 프로세스 3개가 있었고 약 4GB를 사용 중이었다. 해당 프로세스를 조사·종료하지 않으며 Model runtime을 시작하지 않았다. root filesystem은 사용률 96%, 잔여 약 86GB로 확인되었으므로 수치만 보고 대형 설치 여유가 충분하다고 판단하지 않는다. Python 환경·runtime 설치 전에 다시 측정하고 다운로드·wheel·설치 해제·cache·artifact 증가를 합산해야 한다. 정확한 실측값과 도구 상태는 [environment.md](environment.md)를 기준으로 한다.

## 제품 원칙과 첫 범위

**LLM은 판단하고, BIM Engine은 실행한다.** LLM은 Requirement, Intent, Target description, Operation proposal, Design reasoning을 구조화한다. LLM이 raw IFC STEP text나 geometry를 직접 수정하거나 IFC GlobalId를 생성하지 않는다.

첫 Technical Vertical Slice는 Renovation의 `MOVE_FURNITURE` 하나다.

- IFC4의 실제 `IfcFurniture` 하나를 대상으로 한다.
- 같은 Storey에서 상대적인 XY 이동만 지원한다.
- Z, rotation, scale, 층을 변경하지 않는다.
- 지원하는 Placement에만 적용하고 기존 GlobalId를 보존한다.
- 대상, 단위, 좌표계 또는 지원 가능 여부가 불명확하면 변경하지 않고 clarification 또는 거절로 종료한다.

Target Confirmation과 Proposal Approval은 서로 다른 사용자 결정이다. 대상 선택을 IFC 변경 승인으로 해석하지 않는다. 후보 GlobalId는 해당 base revision의 실제 IFC Object Inventory에서만 얻는다.

## 데이터와 실행 방향

초기 구조는 Modular Monolith다. Backend/API, Workflow Worker, Local Model Server를 별도 프로세스로 운영할 수 있으나 제품 모듈을 다수의 microservice로 나누지 않는다. 명시적인 Python Application Service를 사용하며 초기 LangChain/LangGraph, Redis/Celery는 도입하지 않는다.

PostgreSQL은 metadata와 workflow/job 상태를 저장한다. IFC는 Local Artifact Storage에 두고 각 Revision은 immutable full IFC snapshot을 참조한다. Project의 `head_revision`이 변경되면 이전 base revision에 묶인 proposal은 Apply할 수 없다. 기존 IFC나 finalized artifact는 덮어쓰지 않는다. DB와 filesystem의 commit 경계 및 복구는 [architecture_blueprint.md](architecture_blueprint.md)에 설계한다.

Human review 대기 동안 Worker를 점유하지 않는다. Analyze → Target Review → Proposal → Proposal Approval → Apply를 각각 명시적인 상태와 작업 경계로 나눈다. 사용자 입력을 기다리는 작업은 종료하고 다음 사용자 행위가 새 작업을 요청한다.

## Headless와 접근 주소

서버는 GUI, X display, monitor, `cv2.imshow`, `plt.show`, 로컬 interactive window를 요구하지 않는다. 결과는 파일 artifact, API, 사용자 브라우저로 전달한다. Viewer는 IFC Engine과 분리하며 IFC를 GLB와 GlobalId metadata로 변환하여 브라우저의 Three.js/WebGL에 전달하는 방향이다.

개발 단계에서는 각 서버의 URL로 접근할 수 있다. 장기적으로 고정 Domain/Gateway가 활성 서버를 가리키도록 구성할 수 있게 URL과 endpoint를 설정으로 분리한다. 이번 단계에는 reverse proxy, tunnel, frontend, viewer를 설치하거나 배포하지 않는다.

## 환경과 모델 선택 방향

환경은 두 개로 분리한다. 현재 Miniconda나 프로젝트 환경이 준비되었다고 가정하지 않으며 Phase 0에서는 설치하지 않는다.

| 환경 | 위치 | 목적 |
| --- | --- | --- |
| Backend | `<project-root>/.conda` | Python 3.12, Application/Domain, PostgreSQL client, IfcOpenShell, validation; 양 서버 dependency를 가능한 동일 버전으로 유지 |
| Model Runtime | `<project-root>/.conda-vllm` | 별도 Python 호환성 확인 후 PyTorch, vLLM, Transformers, structured decoding; build 차이는 runtime profile로 관리 |

Local Model을 기본으로 한다. 외부 LLM API를 production fallback으로 자동 사용하지 않는다. 외부 비교 평가도 synthetic data만 사용하며 API key 설정·전송에는 사용자 승인이 필요하다.

Phase 0은 공식 model card, repository, vLLM support, license 기반 **shortlist**와 평가 계획까지만 수행한다. 최종 모델·정밀도·runtime 버전은 아직 선택하지 않는다. A100의 큰 메모리에만 맞추지 않고 single RTX 5090 32GB에서 실제 운영 가능한지까지 검토한다. 후보와 평가 기준은 [model_selection_plan.md](model_selection_plan.md), 서버별 지원 근거는 [runtime_compatibility.md](runtime_compatibility.md)에 기록한다.

## Phase 0의 완료 경계

이번 단계의 산출물은 read-only 환경 조사, 저장소/브랜치 전략, 프로젝트 지침, 아키텍처와 단계별 계획, runtime/network profile 예제, runtime info 기반, 호환성 matrix, model shortlist, 평가 계획, Git 제외 규칙과 commit 준비다.

Domain, Database, IFC, LLM production, Frontend 구현은 시작하지 않는다. PyTorch, vLLM, model weight, PostgreSQL, IfcOpenShell, Node, frontend package를 설치하지 않는다. Runtime info나 설정 검증 결과를 Application 실행 성공으로 기록하지 않는다.

이후 사용자 지침 변경(2026-09-19)에 따라 **Phase별 승인 대기는 폐지**했다. Phase11 Internal Technical MVP까지 Quality Gate와 commit/push를 통과한 뒤 자동 진행한다. 최신 계획/상태는 [MASTER_PLAN.md](MASTER_PLAN.md), [STATUS.md](STATUS.md)를 따른다. GPU 점유나 디스크 문제는 관련 GPU/설치 단계의 선행 조건이며 문서와 Domain 계약 설계의 성격을 혼동하지 않는다.
