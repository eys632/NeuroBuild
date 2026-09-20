# NeuroBuild_v2 프로젝트 지침

## 적용 범위와 단계

- A100 작업 root: `/home/a202192020/NeuroBuild_v2`. RTX5090에서는 checkout root를 기준으로 상대 경로를 사용한다.
- 서버 환경 관리는 해당 서버의 전역 정책이 담당한다. A100에서는 먼저 `/home/a202192020/.codex/AGENTS.md`를 읽는다. 이 파일은 제품/저장소 지침이며 전역 정책을 대체하지 않는다.
- 2026-09-19 사용자 지침 변경: Phase 0 기반부터 Phase 11 Internal Technical MVP까지 자율 개발한다. Phase별 사용자 승인 대기는 폐지했다. 현재 단계와 blocker는 `docs/STATUS.md`를 기준으로 한다.
- 2026-09-20 checkpoint 지시: 완료한125개 단회 진단과 독립 재생을 반복하지 않는다. 동일 모델의 전체3회 평가를 자동으로 요구하지 않는다. 단회4gate 미달이면 다음 후보를 검토하고, 통과/경계선일 때만 미확정 사실을 해결하는 최소 반복을 판단한다. V2는1차 gate 통과 후에만 실행한다. 이미 완료한 runtime/resource 검사를 처음부터 반복하지 않고 Phase를 막지 않는 최적화는 future optimization으로 둔다. 최신 반복 판단은 D036과 STATUS를 따른다.
- 과거 코드는 참고 자료다. Git에 보존된 `NeuroBuild_v1/`, 기존 `NeuroBuild_v2/` placeholder를 새 Application에 import하거나 검증 없이 복사하지 않는다.

## 공통 코드와 실행 환경

- A100 + RTX5090는 단일 코드베이스/공통 `v2` 브랜치를 사용한다. 서버별 Application 브랜치/소스 복제/하드웨어별 business logic 분기는 금지한다.
- 차이는 `configs/common.json`, `configs/a100.json`, `configs/rtx5090.json`과 환경변수, 향후 `runtime/`의 dependency 정의로 격리한다.
- Backend `.conda`는 Python 3.12를 계획한다. Model `.conda-vllm`은 선택한 runtime의 공식 요구사항에 맞춰 별도 계획한다. 대형 inference dependency를 Backend에 넣지 않는다.
- A100: physical GPU **3**만, `CUDA_VISIBLE_DEVICES=3`. RTX5090: physical GPU **1**만, `CUDA_VISIBLE_DEVICES=1`. 프로세스 내부에는 `cuda:0`으로 보인다. TP=1. 다른 GPU로 fallback하지 않는다.
- 2026-09-20 사용자 지침: 다른 프로세스의 존재만으로 GPU 실행을 중단하지 않는다. 허용 GPU만 nvidia-smi로 free VRAM/utilization을 반복 측정하고, 후보의 startup/inference 예상 peak(전체 weight/KV/workspace 포함)+안전 margin이 가용량 안에 들어올 때만 실행한다. 타인 VRAM을 침범하거나 OOM 위험이 있는 후보는 실행하지 않는다. 실행 중 여유 감소 시 자신의 모델 작업만 안전하게 중단한다. 다른 사용자의 파일/프로세스/환경을 변경하거나 종료하지 않으며 GPU0/1/2로 fallback하지 않는다.
- sudo, 시스템 Python/CUDA/Driver 변경, `pip --user`, base에 프로젝트 dependency 설치는 금지한다. 설치/다운로드 전후 root 디스크와 프로젝트 cache 크기를 확인한다.
- A100 실측과 RTX5090 predicted/unverified를 구분한다. 설정 파일은 설치/실행/benchmark 성공의 증거가 아니다.
- Headless 필수: GUI/X/monitor/interactive window를 요구하지 않는다. 결과는 artifact/API/브라우저로 제공한다.

## 제품과 데이터 불변 조건

- LLM은 판단하고 BIM Engine은 실행한다. LLM은 raw IFC/geometry를 직접 수정하거나 GlobalId를 생성하지 않는다.
- 초기 scope는 IFC4의 단일 IfcFurniture, 같은 Storey, 상대 XY 이동만. 내부 길이 단위는 metre, 단위 변환/산술은 코드로 처리한다. Z/회전/scale/층 변경은 거절한다. 지원 placement가 불명확하면 변경하지 않는다.
- Modular Monolith와 명시적인 Application Service를 사용한다. LangChain/LangGraph, Redis/Celery, 불필요한 framework를 먼저 도입하지 않는다.
- Revision/full IFC snapshot/finalized artifact는 immutable. DB는 metadata, 파일은 artifact storage. 기존 IFC overwrite 금지.
- Proposal은 base revision에 묶고 Apply 직전 head와 비교한다. target confirmation과 proposal approval은 별도 상태/행위로 관리한다.
- 상태 전이는 명시적이다. PostgreSQL queue, Single Workflow Worker, Session Advisory Lock을 우선한다. Worker는 human review 대기 중 점유하지 않는다. DB/파일 간 commit protocol, retry/idempotency/recovery를 검증한다.
- Viewer는 IFC Engine에서 분리하고 GLB + GlobalId metadata를 브라우저에서 표시하는 방향을 따른다.

## 검증, 기록, Git

- 변경에 맞는 검증을 수행한다. 이후 실제 기능에는 contract/거절 경로/승인 분리/stale revision/중복 실행/IFC 불변 조건 테스트를 둔다. 실행하지 않은 테스트를 PASS라고 쓰지 않는다.
- 로그는 trace_id/project_id/job_id/proposal_id/revision_id/execution_id로 연결한다. chain-of-thought와 secret은 저장하지 않는다. 사용자에게 stack trace를 노출하지 않는다.
- 외부 LLM API production fallback 금지. synthetic 비교도 사용자 승인 없이 API key/외부 전송을 설정하지 않는다.
- GitHub `https://github.com/eys632/NeuroBuild`가 source of truth. milestone에서 status/diff/secret 제외를 확인하고 의미 있는 commit과 push를 수행한다. push 성공까지 Phase checkpoint가 완료된 것이 아니다.
- force push/history rewrite/기존 branch 삭제/remote data 삭제 금지. 기존 main 이력을 보존한다. 환경·weight·cache·DB data·IFC 사용자 파일·runtime artifact·local secret은 commit하지 않는다.
- Git에 저장할 것은 재현 정의, schema/prompt, synthetic evaluation, 테스트, 문서다. 실제 dependency 버전은 설치를 검증하는 단계에서 고정한다.

## 자율 실행과 재개

- 재개 시 전역 지침, 이 파일, `docs/MASTER_PLAN.md`, `docs/STATUS.md`, `docs/DECISIONS.md`, `docs/EXECUTION_LOG.md`를 읽고 `git status`, `git log --oneline --decorate -n 10`을 확인한다. 완료된 Phase를 다시 구현하지 않는다.
- 각 Phase는 PLAN → IMPLEMENT → TEST → REVIEW → DOCUMENT → COMMIT → PUSH → NEXT PHASE 순서다. acceptance/unit/integration(가능한 경우)/regression/architecture/security-safety/cross-server review를 통과해야 다음 단계로 간다.
- 실패하면 코드·로그·dependency·가정을 확인해 수정한다. 유사 실패3회면 접근을 재검토한다. 미실행 검증으로 gate를 통과시키거나 요구사항을 약화하지 않는다.
- `docs/reports/phaseX_report.md`에 목표/구현/테스트/문제/architecture/cross-server/다음 판단을 남긴다. STATUS는 현재 요약, EXECUTION_LOG는 command와 관측 결과를 기록한다. chain-of-thought는 기록하지 않는다.
- 사람 검수 전 evaluation gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**로 표시한다. 내부 개발은 계속할 수 있지만 외부 pilot 전 사람이 검수해야 한다.
- hard blocker: sudo 또는 system driver/CUDA 변경, 다른 사용자 GPU/process 변경, 장기간 GPU3 점유로 필수 benchmark 불가, force push/history rewrite, secret/API key, 민감 IFC, public exposure/pilot, 사용자 product/business 결정, 유료 외부 API, 필수 RTX5090 현장 검증 없이는 결정 불가한 architecture, 데이터 손실 가능 destructive operation. 해당 조건에서는 사용자 결정 전 의존 작업을 중단한다.
- Git author가 없으면 추측하지 말고 사용자에게 요청한다. 인증 부재로 push 불가하면 local commit을 보존하고 기록하며 checkpoint를 통과했다고 표시하지 않는다.
- 세부 naming/module/test/SQL/repository/library/prompt/UI/API/refactor 결정은 기존 원칙 안에서 자율적으로 한다. 환경 설치 전 전역 정책의 조사/계획/경로/디스크 확인은 유지한다.
- Phase11에서 Browser upload→V0→자연어→대상 확인→별도 proposal 승인→job→MOVE_FURNITURE→V1→viewer/download와 불변성·stale/duplicate/unsupported/ambiguity/failure/restart를 검증한다.
- Public production, 고객 pilot, New Build 전체, 벽/문/창 변경, 구조/법규 보장, Jeonju RAG, fine-tuning/LoRA, swarm, microservices/Kubernetes는 자동 범위 밖이다.
- Phase11을 통과하면 `docs/FINAL_INTERNAL_MVP_REPORT.md`를 작성하고 최종 사용자 검토를 요청한 뒤 멈춘다.
