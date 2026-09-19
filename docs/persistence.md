# Phase 2 PostgreSQL / Artifact Persistence

`PostgresStore(dsn, artifacts, schema="neurobuild")`는 metadata와 revision head를 PostgreSQL에 저장한다. `LocalArtifactStore`는 immutable full snapshot byte를 사용자 project storage에 저장한다. 둘은 하나의 transaction이 아니며, 성공한 filesystem finalize 뒤 DB publish가 실패하면 안전한 orphan이 남는 방향을 택한다. 이 단계는 IFC 문법/geometry 검사나 사용자 승인 workflow를 구현하지 않는다.

## API와 commit protocol

`migrate()`는 dedicated schema에 `migrations/001_initial.sql`을 transaction으로 한 번 적용한다. schema 이름은 엄격한 lowercase identifier이며 SQL Identifier로 quote한다. 모든 값은 parameter로 전달하고 각 connection의 local search path를 해당 schema로 제한한다. migration은 repository checkout에 포함된 파일을 사용한다. Application role에 system-level 권한을 요구하지 않는다.

`create_project(name, project_id=None)`, `get_project(project_id)`, `get_revision(revision_id)`, `list_revisions(project_id)`가 metadata를 반환한다. connection은 호출별로 짧게 열고 commit/rollback 후 닫으며 model/GPU code를 호출하지 않는다.

Publish 순서는 다음과 같다.

1. `prepare_execution(execution_id, project_id, base_revision_id, proposal_id, payload_fingerprint, artifact_id=None)`를 호출한다. `artifact_id` 기본값은 execution ID다. project/base/proposal/fingerprint/artifact ID를 **별도 DB transaction으로 먼저 저장**하고 frozen `ExecutionIntent`를 반환한다.
2. `LocalArtifactStore.put_bytes(..., artifact_id=intent.artifact_id)` 또는 `put_file`로 stage/finalize한다. final artifact를 덮어쓰지 않는다.
3. V0는 `import_revision(project_id, artifact, execution_id)`를 호출한다. initial intent는 base/proposal이 `None`이고 payload fingerprint는 source byte의 SHA256이어야 한다.
4. V1 이후는 `commit_revision(project_id, base_revision_id, artifact, execution_id, proposal_id, payload_fingerprint=...)`를 호출한다. initial intent의 payload fingerprint는 승인된 `Proposal.fingerprint`다. fingerprint argument를 생략하면 이미 저장한 binding을 사용하며 Phase 4 Application Service에서는 승인 fingerprint를 명시적으로 전달해야 한다.

Prepare는 artifact를 만들지 않고 import/commit은 intent를 자동 생성하지 않는다. 파일을 finalize하기 전에 안정적인 execution ID와 hash/proposal fingerprint를 먼저 정한다. `get_execution(execution_id)`로 reserved artifact ID와 `PREPARED`/`COMMITTED` 및 result revision을 조회할 수 있다.

Commit은 final artifact의 실제 hash/size/경로를 검증하고 동일 file descriptor와 objects directory를 fsync한 뒤 project row를 `FOR UPDATE`로 잠근다. prepared intent의 모든 binding을 검사하고 현재 head가 base일 때만 artifact metadata, 새 full revision, project head, COMMITTED intent를 하나의 DB transaction으로 publish한다. head update는 추가로 compare-and-swap 조건을 사용한다. concurrent same-base Apply 중 하나만 성공하며 나머지는 `STALE_PROPOSAL`로 거절한다.

## Idempotency와 불변 조건

- 같은 execution ID의 prepare 재시도는 project/base/proposal/fingerprint/artifact ID가 모두 같을 때 기존 intent를 반환한다. 다르면 `IDEMPOTENCY_CONFLICT`다.
- proposal ID와 reserved artifact ID는 각각 하나의 execution에만 결합한다. 다른 execution ID로 같은 proposal을 재사용하면 거절한다.
- 이미 COMMITTED인 execution을 exact artifact ID/hash/size/key와 같은 binding으로 retry하면 기존 revision을 반환한다. head가 그 이후 전진해도 old result를 반환하며 새 revision을 만들지 않는다.
- 새 execution의 base가 head와 다르면 stale로 거절한다. 다른 initial import가 이미 head를 만들었으면 `PROJECT_ALREADY_INITIALIZED`다.
- DB trigger가 revisions/artifacts UPDATE/DELETE, intent binding 변경/삭제 및 COMMITTED 결과 변경을 거절한다. revision parent와 number의 연속성, same-project head/parent/base/result foreign key, unique revision number/execution/proposal/artifact도 DB가 검사한다.
- DB superuser/owner의 의도적인 DDL/trigger 비활성화에 대한 보안 경계는 아니다. 사용자 승인과 inventory membership 검증도 이 repository의 역할이 아니다.

Phase 4 Application Service는 target confirmation과 별도 proposal approval의 Domain guard를 통과한 뒤 이 API를 호출해야 한다. Repository에서 승인 record를 만들거나 Target Confirmation을 approval로 변환하지 않는다.

## Crash / failure recovery

| 실패 시점 | 보존되는 상태 | 재개 동작 |
| --- | --- | --- |
| Prepare 전/중 실패 | head/source unchanged | 같은 stable execution ID로 prepare 재시도 |
| Prepare 성공, final artifact 없음 | PREPARED intent | reserved artifact ID로 finalize 재시도 |
| Finalize 성공, DB publish 전/중 실패 | PREPARED intent + unreferenced final artifact, old head | intent의 artifact ID로 파일을 찾고 hash 검증 후 같은 commit 재시도 |
| Retry 전에 다른 Apply가 head 전진 | PREPARED stale intent와 orphan | commit 거절, 기존 head 보존; 자동 삭제/자동 rebase 금지 |
| DB commit 성공, 응답 유실 | COMMITTED intent/result | 같은 요청 retry로 기존 revision 반환 |

Final object를 무조건 삭제하는 compensation을 수행하지 않는다. `LocalArtifactStore.list_artifacts()`와 intent/revision metadata를 대조하여 orphan을 진단할 수 있다. 자동 garbage collection은 구현하지 않으며 참조 여부/보존 정책을 별도로 확인해야 한다. Atomic no-clobber finalize와 fsync의 보장은 local filesystem adapter에 한정되고 DB/FS 사이 atomicity를 주장하지 않는다.

실제 PostgreSQL integration tests에서 migration 반복, V0와 revisions, idempotency/payload conflict, immutable trigger, same-base concurrent Apply, DB 실패 후 orphan 재시도, reopen durability를 검증한다. Test별 isolated schema와 synthetic byte만 사용하며 타 사용자 DB/data/process에 접근하지 않는다. 테스트 실행 결과는 Phase report에 기록한다.
