# NeuroBuild_v2 구현 로드맵

기준일: 2026-09-19. **이번 작업의 범위는 Phase 0까지다. Phase 1은 사용자 승인 후 시작한다.** 아래 단계는 계획이며 완료 선언이 아니다. Phase 0 결과와 환경 제약은 [project_context.md](project_context.md), 제품/데이터 불변 조건은 [architecture_blueprint.md](architecture_blueprint.md)를 따른다.

## 단계와 완료 기준

| 단계 | 범위 | 해당 단계에서 확인할 완료 기준 |
| --- | --- | --- |
| **0 — Cross-Server Environment & Architecture Foundation** | read-only 환경/Git 조사, 공통 `v2`, 지침과 문서, runtime/network 설정 예제, runtime info, model shortlist와 평가 계획, Git 제외 규칙과 commit 준비 | 실측/예측 구분; 양 서버 단일 코드 원칙; GPU/디스크 문제 공개; 대형 설치·Application 구현 없음; 변경을 검토 가능한 상태로 정리 |
| **1 — Domain Contract** | Operation/Requirement/Target/Proposal/Revision/Review/Execution 계약, 오류와 상태 전이, 단위/좌표계/support policy 정의 | MOVE_FURNITURE의 허용/거절 예시; target 확인≠apply 승인; immutable revision/base=head 규칙; schema 및 의미 검증 기준 확정 |
| **2 — Project / Revision / Artifact Persistence** | PostgreSQL metadata/migration, Local Artifact Storage, full snapshot revision, Artifact Commit Protocol | head의 경쟁 갱신 차단; DB/FS crash 시점별 복구; overwrite 방지; retry/idempotency; orphan 정리의 참조/intent 보호 |
| **3 — IFC Engine + MOVE_FURNITURE** | IfcOpenShell Adapter, IFC4 inventory, 지원 placement의 단일 IfcFurniture 상대 XY 이동 | 실제 synthetic IFC fixture에서 이동 검증; Z/rotation/scale/storey/GlobalId/비대상 객체 보존; 미지원 placement는 무변경 거절 |
| **4 — Explicit Renovation Workflow** | 명시 Application Service로 analyze/target confirm/propose/approve/apply 연결 | 대상 확인과 proposal 승인 분리; approval 없는 Apply 차단; stale proposal 차단; 실패 시 head 유지; LLM 없이도 결정론적 흐름 검증 |
| **5 — Model Runtime + Requirement Pipeline** | `.conda-vllm` 구성, A100 우선 후보 1~2개 평가, local Model Adapter, schema 기반 Requirement parsing | 허용 GPU만 사용; runtime 호환성/라이선스/메모리 확인; endpoint contract 검증; 평가 재현 정보; 최종 모델 선택은 실측 근거로 결정 |
| **5.x — Requirement Quality Hardening** | 한국어 표현, 모호성, 부정/조건, 단위, 복수 operation, target preservation, unsupported handling 강화 | 고정 evaluation set의 semantic/critical-error 지표 및 regression 확인; 단순 JSON 성공률만으로 통과시키지 않음 |
| **6 — Object Resolution + Natural Language Technical Vertical Slice** | 실제 revision inventory의 후보 조회, 사용자 target 확인, 한국어 요청에서 MOVE_FURNITURE까지 연결 | LLM 생성 GlobalId 채택 금지; 모호한 후보는 사용자 선택; 별도 proposal 승인 후 새 IFC revision까지 end-to-end 확인 |
| **7 — Durable Job/Worker + Human Review Persistence** | PostgreSQL job queue, lease/heartbeat, retry/idempotency, durable review/resume | Worker crash/중복 delivery/lease 만료 검증; review 대기 시 Worker 반환; approve와 enqueue 원자성; 중복 Apply가 새 revision을 만들지 않음 |
| **8 — API** | 공통 service를 HTTP interface로 노출, project/revision/review/job/artifact 접근, 오류 계약 | 장기 요청은 job ID 반환; 승인/프로젝트 접근 검증; 내부 trace 비노출; API integration test; network 설정으로 서버 전환 |
| **9 — Frontend + Viewer** | React/TypeScript 및 Next.js 검토, review UI, IFC→GLB+metadata, 브라우저 viewer | 서버 GUI 없이 동작; object selection와 GlobalId mapping; target 확인/proposal 승인 UI 분리; revision별 파생 artifact 일관성 |
| **10 — Admin / Observability** | runtime/server/URL/GPU/model health, worker/job/storage/revision/error 관리 | trace/project/job/proposal/revision/execution 연결; secret/chain-of-thought 비저장; 실패·용량·복구 상태 확인 |

Phase 4~6은 Phase 7의 durable 실행을 미리 production 수준으로 구현하지 않는다. 대신 Application service, 별도 human review, 명시 상태를 유지하여 Phase 7에서 queue/recovery를 붙일 수 있게 한다. Phase 2의 Apply/Artifact idempotency와 Phase 7의 job delivery idempotency는 서로 다른 실패 경계를 다룬다.

## 단계 전체에 적용할 운영 조건

- 설치 전 project root, 기존 환경, Python 버전, 환경 개수/목적, 설치 위치, root disk를 확인한다. 설치할 때는 실제 활성화한 환경의 Python/pip 경로를 재확인한다.
- Backend는 `.conda`/Python 3.12를 기본으로 계획하고 Model Runtime은 `.conda-vllm`에서 별도 지원 버전을 확인한다. 환경 자체는 Git에서 제외하고 검증된 재현 정의를 남긴다.
- A100 physical GPU 3 또는 RTX 5090 physical GPU 1만 사용한다. 예상 밖 점유가 있으면 실행하지 않고 보고한다. 다른 사용자 프로세스 종료나 다른 GPU fallback은 하지 않는다.
- 대형 dependency/model 다운로드 전에 디스크의 peak 사용량을 계산한다. 현재 A100 root 사용률이 높으므로 다운로드 크기만 보고 설치 가능 여부를 판단하지 않는다. 사용자 cache를 자동 삭제하지 않는다.
- Runtime build/version/dtype/quantization/context/동시성 설정은 공식 자료와 실제 테스트로 고정한다. 설정 예제가 호환성 보증이 되지 않는다.
- milestone마다 `git status`, diff, Git 제외 항목을 확인하고 의미 있는 commit과 GitHub push를 준비한다. 공통 소스는 한 서버에만 남기지 않는다. secret/환경/모델/DB/사용자 IFC/cache/runtime artifact는 push하지 않는다.

## A100 모델 평가 단계의 진입 조건

Phase 0에서는 shortlist까지만 작성한다. 실제 다운로드와 GPU 실행은 후속 작업 범위가 승인되고 다음 조건이 확인되었을 때 진행한다.

1. GPU 3의 기존 점유가 해소되었거나 사용자에게 해당 실행이 허용된 상황이 명확해져야 한다. 알 수 없는 process를 종료하여 자리를 만들지 않는다.
2. root 여유 공간을 다시 측정하고 runtime 설치, model download/cache, 평가 artifact, 임시 공간을 포함한 용량 계획이 있어야 한다.
3. A100의 현재 driver와 선택한 PyTorch/vLLM/CUDA runtime 조합이 공식 지원 범위에 있어야 한다. 시스템 driver/CUDA를 바꿔 맞추지 않는다.
4. [model_selection_plan.md](model_selection_plan.md)의 우선 후보부터 순차 평가한다. 모든 후보를 동시에 다운로드하지 않는다.
5. dataset/prompt/schema/model revision/runtime/config/evaluation code/seed/측정 조건을 기록한다. schema valid rate, semantic accuracy, critical false positive/negative, target preservation, unit/value extraction, ambiguity/unsupported/tool selection, latency mean/p95, tokens/sec, VRAM, startup time을 측정한다.

## RTX 5090 재접속 후 Compatibility Validation

현재 RTX 5090은 predicted/unverified다. 재접속 전 성공을 가정하거나 실제 테스트 결과로 표시하지 않는다. 접속 가능해지면 다음 순서로 검증한다.

1. OS, driver/CUDA compatibility, GPU 1 실제 VRAM/점유, disk, Python/runtime 도구를 read-only로 재조사한다. GPU 0은 사용하지 않는다.
2. 공통 `v2`의 동일 commit과 같은 Backend dependency 정의를 준비한다. local URL/storage 설정만 분리한다.
3. 공식 Blackwell 지원과 현재 driver의 호환 조건에 맞는 GPU runtime build를 확인한다. model weight revision과 quantization 방식도 함께 기록한다.
4. `CUDA_VISIBLE_DEVICES=1`, TP=1로 시작하고 다른 GPU fallback 없이 startup, model health, structured output, tool behavior, VRAM, latency를 측정한다.
5. 공통 contract/IFC/workflow tests와 동일 synthetic model evaluation set을 실행한다. precision/runtime 차이가 target 선택과 critical errors에 미치는 영향을 비교한다.
6. [runtime_compatibility.md](runtime_compatibility.md)의 해당 항목만 증거와 날짜를 붙여 MEASURED로 갱신한다. 한 항목의 통과를 전체 운영 검증으로 확대하지 않는다.

## Phase 1 시작 전에 확인할 결정

**필수 사용자 결정은 Phase 0 결과 검토 후 Phase 1 진행 승인이다.** 이번 작업에서 자동으로 다음 단계를 시작하지 않는다. 다음은 계약을 작성하며 확정할 기술 항목이며 모두를 이유로 불필요한 별도 승인 절차를 만들지는 않는다.

| 항목 | 현재 방향 | 확정할 시점 |
| --- | --- | --- |
| 최초 XY 좌표계/길이 단위/Placement 범위 | 상대 XY, 동일 Storey, 미지원은 거절 | Phase 1 계약 및 Phase 3 fixture 검증 |
| Domain 상태/오류/schema version | 문서의 명시 상태 초안에서 시작 | Phase 1 |
| PostgreSQL 제공 방식/접속/저장 위치 | 시스템 변경 없는 사용자 권한 범위; provisioning 미수행 | Phase 2 설치·운영 계획 전 |
| Artifact durability/보존/백업 | finalize 후 DB commit, immutable full snapshot | Phase 2 |
| 정확한 dependency lock | Backend 공통, GPU runtime 별도 | 해당 환경 구축 및 검증 시 |
| 모델/runtime/quantization/context | shortlist만; 최종 모델 미선정 | Phase 5 평가 후 |
| URL/domain/gateway | 설정 분리, 실제 외부 배포 미수행 | API/배포 작업 시 |

GPU 점유와 디스크 문제는 먼저 보고하고 설치·평가를 보류해야 하는 실제 환경 제약이다. 이 문제가 해결되지 않았더라도 사용자 승인을 받은 Domain 계약 설계 자체는 GPU/DB/model 설치 없이 진행할 수 있다.

## 이후 확장

Phase 10 이후에는 **Operation Expansion → New Build → RAG → Jeonju Local Plugin → Fine-tuning** 순서를 기준으로 필요성과 평가 근거를 검토한다. 현재의 MOVE_FURNITURE 계약을 일반 geometry 생성 권한으로 넓히거나, RAG/fine-tuning/framework 도입을 미리 구현하지 않는다. 각 확장에서도 LLM 판단과 결정론적 실행, target 확인과 proposal 승인, immutable revision을 유지한다.
