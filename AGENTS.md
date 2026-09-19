# NeuroBuild_v2 프로젝트 지침

## 적용 범위와 단계

- A100 작업 root: `/home/a202192020/NeuroBuild_v2`. RTX5090에서는 checkout root를 기준으로 상대 경로를 사용한다.
- 서버 환경 관리는 해당 서버의 전역 정책이 담당한다. A100에서는 먼저 `/home/a202192020/.codex/AGENTS.md`를 읽는다. 이 파일은 제품/저장소 지침이며 전역 정책을 대체하지 않는다.
- 현재 Phase 0: 문서, 설정 예제, runtime info 기반만. 사용자 승인 없이 Phase 1 또는 Domain/DB/IFC/LLM production 구현을 시작하지 않는다.
- 과거 코드는 참고 자료다. Git에 보존된 `NeuroBuild_v1/`, 기존 `NeuroBuild_v2/` placeholder를 새 Application에 import하거나 검증 없이 복사하지 않는다.

## 공통 코드와 실행 환경

- A100 + RTX5090는 단일 코드베이스/공통 `v2` 브랜치를 사용한다. 서버별 Application 브랜치/소스 복제/하드웨어별 business logic 분기는 금지한다.
- 차이는 `configs/common.json`, `configs/a100.json`, `configs/rtx5090.json`과 환경변수, 향후 `runtime/`의 dependency 정의로 격리한다.
- Backend `.conda`는 Python 3.12를 계획한다. Model `.conda-vllm`은 선택한 runtime의 공식 요구사항에 맞춰 별도 계획한다. 대형 inference dependency를 Backend에 넣지 않는다.
- A100: physical GPU **3**만, `CUDA_VISIBLE_DEVICES=3`. RTX5090: physical GPU **1**만, `CUDA_VISIBLE_DEVICES=1`. 프로세스 내부에는 `cuda:0`으로 보인다. TP=1. 다른 GPU로 fallback하지 않는다.
- GPU를 실행하기 전 허용 GPU만 점유 확인한다. 예상 밖 프로세스가 있으면 실행을 중단하고 보고한다. 다른 사용자의 파일/프로세스/GPU에 접근하거나 프로세스를 종료하지 않는다.
- sudo, 시스템 Python/CUDA/Driver 변경, `pip --user`, base에 프로젝트 dependency 설치는 금지한다. 설치/다운로드 전후 root 디스크와 프로젝트 cache 크기를 확인한다.
- A100 실측과 RTX5090 predicted/unverified를 구분한다. 설정 파일은 설치/실행/benchmark 성공의 증거가 아니다.
- Headless 필수: GUI/X/monitor/interactive window를 요구하지 않는다. 결과는 artifact/API/브라우저로 제공한다.

## 제품과 데이터 불변 조건

- LLM은 판단하고 BIM Engine은 실행한다. LLM은 raw IFC/geometry를 직접 수정하거나 GlobalId를 생성하지 않는다.
- 초기 scope는 IFC4의 단일 IfcFurniture, 같은 Storey, 상대 XY 이동만. Z/회전/scale/층 변경은 거절한다. 지원 placement가 불명확하면 변경하지 않는다.
- Modular Monolith와 명시적인 Application Service를 사용한다. LangChain/LangGraph, Redis/Celery, 불필요한 framework를 먼저 도입하지 않는다.
- Revision/full IFC snapshot/finalized artifact는 immutable. DB는 metadata, 파일은 artifact storage. 기존 IFC overwrite 금지.
- Proposal은 base revision에 묶고 Apply 직전 head와 비교한다. target confirmation과 proposal approval은 별도 상태/행위로 관리한다.
- 상태 전이는 명시적이다. Worker는 human review 대기 중 점유하지 않는다. DB/파일 간 commit protocol, retry/idempotency/recovery를 설계한다.
- Viewer는 IFC Engine에서 분리하고 GLB + GlobalId metadata를 브라우저에서 표시하는 방향을 따른다.

## 검증, 기록, Git

- 변경에 맞는 검증을 수행한다. 이후 실제 기능에는 contract/거절 경로/승인 분리/stale revision/중복 실행/IFC 불변 조건 테스트를 둔다. 실행하지 않은 테스트를 PASS라고 쓰지 않는다.
- 로그는 trace_id/project_id/job_id/proposal_id/revision_id/execution_id로 연결한다. chain-of-thought와 secret은 저장하지 않는다. 사용자에게 stack trace를 노출하지 않는다.
- 외부 LLM API production fallback 금지. synthetic 비교도 사용자 승인 없이 API key/외부 전송을 설정하지 않는다.
- GitHub `https://github.com/eys632/NeuroBuild`가 source of truth. milestone에서 status/diff/secret 제외를 확인하고 의미 있는 commit과 push 준비를 한다.
- force push/history rewrite/기존 branch 삭제/remote data 삭제 금지. 기존 main 이력을 보존한다. 환경·weight·cache·DB data·IFC 사용자 파일·runtime artifact·local secret은 commit하지 않는다.
- Git에 저장할 것은 재현 정의, schema/prompt, synthetic evaluation, 테스트, 문서다. 실제 dependency 버전은 설치를 검증하는 단계에서 고정한다.
