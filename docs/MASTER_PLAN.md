# NeuroBuild_v2 장기 실행 계획

갱신: 2026-09-19 KST. 목표는 **동일한 Application Code를 사용하는 A100/RTX 5090 Internal Technical MVP**다. 현재 진행 상태는 [STATUS.md](STATUS.md), 결정은 [DECISIONS.md](DECISIONS.md), 실행 근거는 [EXECUTION_LOG.md](EXECUTION_LOG.md)에 기록한다.

## 실행 권한과 종료 범위

최신 사용자 지침은 Phase마다 사용자 승인을 기다리라는 과거 지침을 대체한다. 각 단계는 **PLAN → IMPLEMENT → TEST → REVIEW → DOCUMENT → COMMIT → PUSH → NEXT PHASE** 순서로 자율 진행한다. Phase의 acceptance criteria와 quality gate, 원격 checkpoint를 통과하기 전에는 다음 Phase를 시작하지 않는다.

Phase 11을 통과하면 `docs/FINAL_INTERNAL_MVP_REPORT.md`를 작성하고 최종 사용자 검토를 요청한 뒤 자동 실행을 멈춘다. Public Production Deployment, 실제 고객 Pilot, Fine-tuning/LoRA, Jeonju Local RAG/Product specialization은 자동 완료 범위 밖이다. New Build 전체, wall/door/window editing, 구조공학/법규 보증, multi-agent swarm 제품 기능, microservice 전환, Kubernetes도 구현 범위가 아니다.

## 고정된 제품·운영 조건

- 공통 `v2` branch와 단일 source tree를 사용한다. 서버별 Application 복제와 business logic 분기를 금지한다. 차이는 GPU runtime, network/deployment, resource configuration에 둔다.
- A100은 physical GPU 3만, RTX 5090은 physical GPU 1만 사용한다. 각각 `CUDA_VISIBLE_DEVICES=3`/`1`, 내부 논리 장치 `cuda:0`, 초기 TP=1이다. 다른 GPU fallback이나 타인 process 조작은 하지 않는다.
- RTX 5090은 접근 불가능하므로 PREDICTED/UNVERIFIED다. 나중에 동일 commit으로 별도 compatibility validation을 할 수 있게 준비하며 실측하지 않은 결과를 VERIFIED로 표시하지 않는다.
- Headless 동작을 유지한다. IFC → server conversion → GLB/object metadata → browser/Three.js/WebGL로 표시한다. X/monitor/GUI window를 요구하지 않는다.
- LLM은 semantic requirement와 제안을 만들고 BIM Tool은 검증된 operation을 결정론적으로 실행한다. LLM은 GlobalId, raw IFC rewrite, geometry mutation, 단위 변환 등 deterministic arithmetic을 담당하지 않는다.
- 첫 capability는 IFC4, 단일 IfcFurniture, 동일 Storey의 상대 XY 이동 `MOVE_FURNITURE`다. 내부 표준 단위는 **metre**다. Z/rotation/scale/floor 변화 금지, GlobalId 보존, unsupported placement 거절을 유지한다.
- Target Confirmation과 Proposal Approval은 별도 상태/행위다. Revision은 immutable full IFC snapshot이고 proposal은 base revision에 결합한다. stale 및 duplicate Apply를 차단한다.
- PostgreSQL은 metadata/state, filesystem은 artifact를 저장한다. DB/FS 공통 transaction을 가정하지 않으며 Artifact Commit Protocol을 구현한다.
- 초기 durable runtime은 PostgreSQL Job Queue + **Single Workflow Worker + Session Advisory Lock**이다. human wait 중에는 Worker를 반환한다. Redis/Celery/Temporal/LangChain/LangGraph는 구체적인 필요가 입증되기 전 도입하지 않는다.
- 환경은 `.conda`(Backend Python 3.12)와 `.conda-vllm`(선택 runtime 호환 Python)로 분리한다. 전역 환경·공용 서버 정책은 계속 적용하며 sudo/system Python/driver/CUDA 변경, `pip --user`, base 프로젝트 dependency 설치를 금지한다.

## Phase 계획과 acceptance criteria

이 표는 앞으로 수행할 계획이다. `STATUS.md`가 완료 사실을 구분한다. 2026-09-20 SSH 인증 해결 후 원격v2와 local HEAD `f131644` 일치를 확인하여 Phase0 checkpoint를 완료했다.

| Phase | 목표와 핵심 산출물 | Acceptance criteria | 선행 조건과 관계 |
| --- | --- | --- | --- |
| **0 Foundation checkpoint** | 기존 환경/Git/architecture/profile/model shortlist 결과를 검증하고 commit/push, 상태 문서 외부화 | 기존 staged 검증, 올바른 Git author, secret/환경/weight 제외, local commit 및 원격 `v2` push 확인 | 완료: remote/current HEAD f131644 |
| **1 Domain Contract** | Requirement, Operation, Target, Proposal, Revision, Review, Execution 계약; 상태/오류/schema | metre의 명시적 변환 규칙, single XY scope, target 확인≠apply 승인, stale/unsupported/ambiguity 규칙의 deterministic unit tests | Phase 0 checkpoint; 필요한 Backend 최소 환경을 전역 정책에 따라 준비. GPU/모델은 불필요 |
| **2 Project / Revision / Artifact Persistence** | PostgreSQL metadata/migration, local artifact storage, immutable full snapshots, commit/recovery | source overwrite 금지, head의 원자적 갱신, concurrent/stale Apply 차단, finalize/DB 실패의 안전한 recovery, idempotency 및 orphan 참조 보호 테스트 | Phase 1; 사용자 권한 범위의 PostgreSQL 제공 방식 및 디스크 검토 |
| **3 IFC Engine + MOVE_FURNITURE** | IfcOpenShell Adapter, synthetic IFC4 fixture, inventory, 지원 placement의 XY 이동 | 실제 fixture에서 metre/IFC unit 변환, 대상 XY 변화, Z/rotation/scale/storey/GlobalId/비대상 보존, unsupported placement 무변경 거절 | Phase 1~2; 필요한 IfcOpenShell을 Backend 환경에 추가 |
| **4 Explicit Renovation Workflow** | explicit Python services로 target review → proposal → approval → apply 연결 | target 확인과 approval 분리, approval 없는 Apply 거절, stale/duplicate/실패 시 head 보존, LLM 없이 synthetic end-to-end 서비스 검증 | Phase 1~3; Phase 7의 durable queue와 동일 서비스 경계 유지 |
| **5 Local Model Runtime / Model Selection / Requirement Pipeline** | 공식 자료 기반 후보 순차 benchmark, local model adapter, semantic requirement pipeline | 허용 GPU에서 실제 startup/inference, schema와 semantic/critical-error 지표, runtime/VRAM/latency 기록, deterministic unit conversion의 코드 처리, 실측 근거로 모델 선택 | Phase 4; GPU3 점유·디스크·driver 호환성 해결. 필수 실측이 막히면 gate를 통과한 것으로 처리하지 않음 |
| **5.x Requirement Quality Hardening** | 한국어, target preservation, ambiguity, unit/value, 부정/조건/복수 요청/unsupported/tool selection 회귀 | versioned evaluation의 schema/semantic/critical FP/FN 결과, 원문 대상/제외 조건 보존, unsupported subset 자동 실행 금지, prompt/schema regression | Phase 5; AUTO-GENERATED / NOT HUMAN VERIFIED와 사람 검수 여부를 분리 |
| **6 Object Resolution / Natural Language Technical Vertical Slice** | 실제 inventory에서 후보를 찾고 한국어 요청부터 새 revision까지 연결 | LLM GlobalId 생성 금지, 모호성 시 사용자 확인, 별도 proposal 승인, 단일 가구 XY 변경과 V0/V1 artifact 검증 | Phase 2~5.x; real local model과 synthetic IFC의 결합 검증 |
| **7 Durable Job Runtime / Worker / Human Review Persistence** | PostgreSQL queue, single worker session advisory lock, durable review/resume, retry | 두 Worker의 동시 active 처리 방지, session lock/연결 상실 시 안전 중단, human wait 중 worker free, restart/duplicate delivery/실패 복구, approve+enqueue 일관성 | Phase 2/4/6; 초기 workflow를 durable execution에 연결 |
| **8 FastAPI Backend API** | project/upload/revision/requirement/review/proposal/job/artifact interface | 장기 작업은 job ID로 반환, 명시 오류/접근 경계, 승인 우회 차단, upload/download 및 API integration/regression, 내부 stack trace 비노출 | Phase 7; localhost/internal 운영만, 공용 인터넷 노출 금지 |
| **9 Frontend / Browser Viewer** | React/TypeScript 기반 UI와 IFC→GLB/object mapping, 이전/현재 revision 확인 | 브라우저 project/upload/target review/proposal approval/job/viewer/download 흐름, GlobalId selection 정합성, headless server, 설정 기반 URL | Phase 8; 필요한 frontend runtime과 conversion dependency의 호환성/용량 검토 |
| **10 Minimal Admin** | runtime/server/URL/model/worker/job/storage/revision/error visibility | 현재 profile/접속 URL, model 상태, job/error와 storage 상태, trace/project/job/proposal/revision/execution 식별 연결, secret/chain-of-thought 비저장 | Phase 8~9; 최소 내부 운영 UI/API로 제한 |
| **11 Internal Technical MVP Stabilization** | 전체 browser flow, failure/restart/concurrency regression, runbook와 최종 보고 | 아래 전체 MVP 흐름과 불변 조건을 실제로 확인, 문서/재현 정의/phase report/commit/push 완료, 검증되지 않은 RTX 항목과 human GT 한계를 명시 | Phase 1~10 전부 gate 통과. 최종 보고 후 사용자 검토 요청하고 자동 실행 종료 |

Phase는 순서대로 진행한다. 선행 Phase의 테스트를 유지하고 필요한 integration을 뒤 단계에서 추가한다. 특정 환경 문제로 필수 gate를 만족하지 못하면 뒤 Phase를 구현하여 그 실패를 감추지 않는다. 같은 Phase 안에서 blocker와 독립적인 문서/진단/복구 작업은 계속할 수 있다.

## 모든 Phase의 Quality Gate

1. Acceptance criteria와 요구사항 충족 여부를 확인한다. 테스트 통과를 위해 scope나 안전 조건을 약화하지 않는다.
2. 구현 중 unit/deterministic test를 함께 실행한다. Integration test는 가능한 실제 경계에서 수행하고 불가능하면 이유와 미검증 범위를 남긴다. Phase에 필수인 integration을 생략한 채 완료 선언하지 않는다.
3. 기존 regression test를 실행한다. Domain/Persistence/IFC/concurrency/artifact/job/LLM schema/Object Resolution의 실제 실패 위험을 우선한다.
4. Architecture review: 단순한 명시 서비스 경계, 불필요한 complexity/framework 여부, deterministic 작업의 LLM 위임 여부를 확인한다.
5. Security/safety review: 승인 우회, 타 사용자/GPU 접근, secret/민감 데이터, 실패 시 head/artifact 보존, restart 복구를 확인한다.
6. Cross-server impact review: common layer에 서버 분기가 유입되지 않았는지, dependency/runtime/config 차이가 설명되는지 확인한다. RTX 결과는 예측/미검증으로 남긴다.
7. 문서와 `docs/reports/phaseX_report.md`를 작성한다. 목표, 구현, 테스트, 결과, 문제, architecture 변화, cross-server 영향, 다음 Phase 판단을 포함한다. 기존 `docs/phase0_report.md`는 당시 기록으로 보존한다.
8. `STATUS.md`, `DECISIONS.md`, `EXECUTION_LOG.md`를 실제 repository/test 결과에 맞춰 갱신한다. 적용 불가능한 검증은 N/A와 근거를 적으며 실행하지 않은 결과를 PASS로 채우지 않는다.
9. `git status`/diff/제외 규칙을 검토하고 의미 있는 commit을 만든다. local commit만으로 remote checkpoint 완료라고 쓰지 않는다.
10. 공통 `v2` push와 원격 commit 확인까지 성공한 뒤 NEXT PHASE로 이동한다. 일시적인 push 실패는 local commit을 보존하고 원인에 맞춰 재시도한다. 인증이 없다면 무한 반복하지 않는다.

같은 접근으로 유사한 실패가 3회 이상 반복되면 가정/전략을 재검토한다. 구현 오류는 우선 자율 수정하고 기술 세부 선택 때문에 사용자 승인을 다시 요청하지 않는다.

## Internal MVP의 실제 완료 흐름

Browser에서 다음 흐름이 실제로 동작해야 한다.

`Project → IFC upload → Revision V0 → Natural Language Request → Requirement interpretation → Object Resolution → Target Review → Proposal → Proposal Approval → Job → MOVE_FURNITURE → Validation → Artifact Commit → Revision V1 → Browser Viewer → Previous/Current Revision 확인 → IFC Download`

Source V0 immutable, stale proposal 차단, duplicate Apply 차단, unsupported 거절, ambiguity 시 사용자 확인, job failure 안전성, server restart 후 상태 보존을 검증한다. 모델을 호출하지 않은 stub flow만으로 최종 MVP 완료를 선언하지 않는다. 내부 테스트 데이터는 synthetic IFC를 사용하고 실제 고객/민감 IFC를 자동으로 도입하지 않는다.

## 사용자에게 멈추어 결정을 요청할 Hard Blocker

최신 사용자 지침의 중단 조건은 다음과 같다.

1. sudo가 필요함.
2. NVIDIA Driver/System CUDA 변경이 필요함.
3. 다른 사용자의 GPU/process 변경이 필요함.
4. GPU3의 장기 점유로 필수 benchmark가 불가능함.
5. force push/history rewrite가 필요함.
6. secret/API key 또는 작업에 필요한 인증이 필요함.
7. 실제 고객/민감 IFC 데이터 사용이 필요함.
8. public network exposure가 필요함.
9. 실제 외부 Pilot을 시작해야 함.
10. 사용자가 결정해야 하는 Product/Business 정책이 있음.
11. 비용이 발생하는 외부 API가 필요함.
12. RTX5090 실측 없이는 결정할 수 없는 필수 architecture 문제가 있음.
13. 데이터 손실 가능성이 있는 destructive operation이 필요함.

Git author와 GitHub 인증 blocker는 해결됐다. 사용자가 인증과 함께 정리한 현재 commit/remote 설정을 보존한다. 승인 범위 내의 safe library/SQL/interface/naming/refactor/prompt/UI/API 설계는 자율 결정한다. 설치 전 디스크 부족 등 전역 운영 제한도 무시하지 않으며 안전한 범위의 대안을 먼저 검토한다.

## 재개 절차

전역 `~/.codex/AGENTS.md` → root `AGENTS.md` → 이 문서 → `STATUS.md` → `DECISIONS.md` → `EXECUTION_LOG.md`를 읽은 뒤 `git status`, `git log --oneline --decorate -n 10`을 확인한다. 실제 repository 상태를 우선하고 완료된 Phase를 처음부터 반복하지 않는다. 오래된 Phase 0의 승인 대기 문구는 최신 자율 지침에 의해 대체되었다.
