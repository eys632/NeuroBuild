# Phase 4 Explicit Renovation Workflow

`RenovationService(store: PostgresStore, engine: IfcEngine)`는 Domain, 실제 IFC Engine, immutable artifact storage와 PostgreSQL revision publication을 연결하는 동기 Application Service다. LLM/API/job queue를 호출하거나 구현하지 않는다. 이 단계의 human review record는 **service process 메모리에만 저장**된다. Process 재시작 시 review/workflow는 사라지며 revision/artifact/execution intent만 durable하다. Human review와 resume/queue의 내구성은 Phase 7에서 구현한다.

## Public interface

| 메서드 | 결과 / 의미 |
| --- | --- |
| `import_ifc(project_id, source: bytes, execution_id)` | IFC inventory 검증 후 V0 `Revision` 저장. Invalid input은 intent/final artifact를 만들기 전에 거절 |
| `begin(requirement: SemanticRequirement)` | 현재 project/base와 결합한 frozen `Workflow` snapshot |
| `get(workflow_id)` | service가 소유한 상태의 분리된 snapshot |
| `confirm_target(workflow_id, global_id, confirmed: bool)` | 실제 inventory target에 대한 명시적 확인/거절 |
| `create_proposal(workflow_id)` | 확인된 target와 원래 operation으로 proposal을 생성하고 별도 approval 대기 |
| `approve_proposal(workflow_id, proposal_id, fingerprint, approved: bool)` | 정확한 stored proposal의 ID/content에 대한 별도 승인/거절 |
| `apply(workflow_id, execution_id)` | 승인 검증과 실제 IFC 이동 후 새 `Revision`; 동일 실행 재시도는 기존 결과 |

전이 메서드는 `Workflow`를 반환하고 `apply/import_ifc`만 `Revision`을 반환한다. Snapshot에는 `workflow_id`, 원래 requirement, status, inventory, confirmation/proposal/approval, stable execution ID, result revision ID, 안전한 error code가 담긴다. `workflow_id`는 이 slice의 trace 식별자로 사용할 수 있다. Job은 아직 없으므로 job ID를 만들지 않는다.

## 명시적인 상태 전이

`READY` requirement는 `WAIT_TARGET`에서 시작한다. `CLARIFICATION`과 `UNSUPPORTED`는 각각 `WAIT_CLARIFICATION`/`UNSUPPORTED`로 남고 실행할 수 없다. 수정된 해석은 새 requirement/workflow로 시작한다.

`WAIT_TARGET → TARGET_CONFIRMED → WAIT_APPROVAL → APPROVED → APPLIED`

Target 거절은 `TARGET_REJECTED`, proposal 거절은 `PROPOSAL_REJECTED`로 끝난다. `confirmed`와 `approved`는 실제 bool이어야 하며 truthy 문자열/숫자를 허용하지 않는다. 확인 단계에서 proposal이나 approval을 자동 생성하지 않는다. 승인 후 target/operation을 바꾸는 전이가 없으며 변경하려면 새 workflow와 새 확인/승인이 필요하다.

Service가 원래 requirement를 검증·복사하여 보유하고 반환 snapshot도 deep copy한다. 외부에서 snapshot을 교체/변조하거나 새 `ProposalApproval` 객체를 만들어도 service authority를 바꾸지 않는다. Mutation API는 service가 발급한 workflow/proposal ID와 정확한 fingerprint만 받는다. 이것은 동작 계약이며 trusted Python process 내부의 private attribute 접근을 막는 sandbox는 아니다. 사용자 인증과 approval endpoint의 권한 검사는 향후 API 경계의 책임이다.

## Apply 승인·데이터 검증

1. Service-owned READY requirement, actual inventory target, positive Target Confirmation, 원래 operation을 가진 Proposal, 별도의 positive Proposal Approval의 모든 project/base/requirement/ID/content binding을 검사한다.
2. 새 Apply 또는 PREPARED retry는 DB에서 fresh project/head를 읽고 Domain `require_apply_authorization`으로 stale head를 거절한다. Commit 때의 PostgreSQL row lock/CAS가 이 검사 이후의 race도 차단한다.
3. Immutable base artifact를 checksum 검증하며 읽고 실제 `IfcEngine.move_furniture`를 실행한다. Target membership/placement와 XY/Z/rotation/storey/GlobalId/비대상 보존 검증은 IFC Engine이 수행한다.
4. 승인된 proposal fingerprint로 durable execution intent를 먼저 저장한 뒤 expected output hash/size/canonical artifact key를 사용해 no-clobber finalize한다.
5. 동일 fingerprint를 `commit_revision`에 명시적으로 전달하여 DB publish한다. 성공한 result를 `APPLIED` 상태로 기록한다.

같은 workflow의 mutation은 해당 workflow lock으로 순서화한다. Registry lock은 lookup/save에만 짧게 사용하며 서로 다른 workflow 전체를 직렬화하지 않는다. 다른 proposal이 같은 base에서 경쟁하면 DB CAS에 의해 하나만 head를 전진시킬 수 있다.

## 실패와 재시도

승인된 첫 Apply 시도는 execution ID를 workflow에 고정한다. IFC/FS/DB 실패 뒤에는 approval을 유지하고 error code를 기록하여 **같은 execution ID**로 재시도할 수 있다. 실행 오류는 human approval 거절 상태와 구분하며 다른 execution ID로 같은 workflow를 다시 적용하지 않는다.

Finalize가 이미 성공했다면 `ARTIFACT_EXISTS`만 recovery 후보로 처리한다. Immutable base와 승인 operation으로 결과를 다시 계산한 **expected ArtifactRef**에 대해 hash/size/path 및 file/directory fsync를 검증한다. `list_artifacts()`가 현재 읽은 hash를 기대값으로 신뢰하지 않는다. Corruption/fsync failure는 DB publish 전에 중단하며 원본/final orphan을 삭제하거나 overwrite하지 않는다.

DB commit 후 응답이 유실되면 registry는 아직 APPROVED일 수 있다. Retry는 service-owned 승인 binding과 durable execution intent를 먼저 확인한다. 이미 COMMITTED인 정확한 실행이면 현재 head가 더 전진했어도 authoritative immutable result revision의 project/base/reserved artifact binding을 확인하고 저장된 hash/size로 artifact를 verify한 뒤 기존 revision을 반환한다. 이 경로는 IFC 결과를 재생성하지 않으므로 이후 engine 실패/변경이 알려진 완료 결과의 반환을 막지 않는다. 새 revision을 만들지 않으며 이미 수행한 동작을 fresh Apply로 재실행하지 않는다. 다른 workflow/proposal/payload에 사용된 execution ID는 거절한다.

V0 import도 source SHA256과 execution/project binding을 고정하고 exact source retry만 허용한다. Invalid IFC, unsupported/clarification, 승인 누락/변조, stale proposal, 실패한 execution은 source artifact를 수정하지 않는다. 성공한 DB commit 후 응답이 유실된 경우에는 durable head가 이미 전진했음을 구분한다.

## 검증 경계

Real PostgreSQL + real IfcOpenShell + synthetic IFC의 integration으로 import→requirement→target confirmation→proposal→별도 approval→move→V1을 검증한다. Negative tests는 승인 분리, forged snapshots, actual target membership, stale/duplicate/concurrent apply, engine/DB 실패, orphan 및 응답 유실 retry를 포함한다. Frozen in-process review를 durable human review/restart recovery가 완료된 것으로 표시하지 않는다. Queue, LLM 의미 해석, natural-language object matching, 브라우저 흐름은 이후 Phase의 작업이다.
