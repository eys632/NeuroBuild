# Phase 4 — Explicit Renovation Workflow

2026-09-20. 실제 IFC inventory와 별도 Target Confirmation / Proposal Approval을 PostgreSQL revision commit에 연결했다. LLM 없이 synthetic IFC4로 서비스 흐름을 검증한다. 원격 checkpoint는 STATUS 및 후속 실행 기록을 따른다.

## 구현

`RenovationService`가 IFC 검증/import, SemanticRequirement 접수, 대상 확인/거절, Proposal 생성, 정확한 ID/fingerprint의 별도 승인/거절, Apply를 명시적인 메서드로 제공한다. Phase1~3의 Domain/IFC/Persistence를 사용하며 새 패키지/framework는 추가하지 않았다.

Authority는 service-owned frozen record다. 입력 requirement는 검증·복사하고 반환 snapshot은 deep copy한다. Caller가 반환 객체나 원래 requirement를 변조해도 내부 승인·operation은 바뀌지 않는다. Workflow별 lock을 사용하며 다른 workflow의 동시 head 변경은 PostgreSQL CAS가 보호한다.

미승인/거절/unsupported/clarification/stale는 실행되지 않는다. Apply는 현재 head와 exact requirement/target/confirmation/proposal/approval binding을 검사한다. Stable execution ID를 고정하고 deterministic output의 hash/size로 final artifact를 검증한다. Orphan을 자동 삭제하거나 덮어쓰지 않는다. 이미 COMMITTED인 재시도는 승인·intent·결과 binding과 artifact integrity를 확인한 뒤 기존 Revision을 반환한다.

## 검증

- Root 전체 **108 tests PASS**(12.378s), PostgreSQL skip0. Domain29/Artifact20/IFC25/Persistence13/Workflow21. DISPLAY/WAYLAND_DISPLAY를 제거한 환경에서 실행했다.
- 독립 workflow21 tests PASS(8.640s). 실제 PostgreSQL + IfcOpenShell + synthetic boxed furniture로 V0 → 대상 확인 → Proposal → 별도 승인 → 이동 → V1을 검증했다.
- 대상 확인만으로 Apply 거절, 실제 inventory 외 ID 거절, non-ready/명시 거절, exact proposal fingerprint, 변조 snapshot/입력의 권한 우회 차단.
- Project/base 결합, stale/중복 Apply, 같은 base의 동시 두 요청 중 하나만 성공, source/hash 보존.
- 잘못된 IFC는 intent/artifact 생성 전에 거절. 엔진 실패 및 실제 DB CHECK 실패는 old head/source를 보존하며 동일 execution으로 재시도했다. Final orphan을 동일 bytes로 복구했다.
- DB commit 후 응답 유실 → 다른 workflow가 V2까지 진행 → engine unavailable에서도 이전 execution 재시도로 V1 반환/headV2 유지 확인.
- 새 service instance가 이전 human review를 갖지 않는다는 제한도 테스트했다. 추가 독립 real-PG probe4/4도 PASS: 다른 workflow의 committed ID 재사용, 잘못된 orphan, 같은 execution 동시 요청, committed artifact 손상을 검증했다. UUID alias로 입력 authority가 바뀔 수 있는 경계를 deepcopy와 회귀로 보강했다. Pip check/diff check PASS. 전체 로그는 ignored var/phase4-tests.log.

## Review / 범위

공통 Application code에 GPU/서버 주소 분기는 없다. A100 CPU/headless에서 실측했고 RTX5090은 **UNVERIFIED**다. 직접 inventory 선택은 실제 객체 존재 확인이며 자연어 object resolution의 구현은 아니다. Authorization 계약은 trusted Python service 경계이며 사용자 인증/endpoint 권한 검사는 Phase8의 책임이다.

Review 상태는 프로세스 메모리에만 존재한다. Phase2의 Revision/artifact/execution intent는 durable하지만 human wait/restart/queue는 아직 제공하지 않는다. 계획대로 Phase7에서 durable human review + PostgreSQL queue + single worker/session advisory lock을 추가한다. 이번 단계가 browser/LLM MVP 완료를 뜻하지 않는다.

Phase4 gate/원격 checkpoint 이후 Phase5에서 허용 GPU3의 점유·disk·driver 조건을 다시 확인하고 실제 local model runtime/평가를 진행한다. 필수 inference가 막히면 benchmark를 모의 결과로 대체하지 않고 blocker로 기록한다.
