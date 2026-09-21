# Phase 2 — Project / Revision / Artifact Persistence

2026-09-20. 목표는 immutable full snapshot과 PostgreSQL metadata 사이의 실패·재시도·동시성 안전성이다. Quality gate를 통과했으며 이 보고와 함께 commit/push한다. 최종 원격 checkpoint는 STATUS/후속 실행 기록을 따른다.

## 구현과 환경

- Backend .conda Python3.12.14에 PostgreSQL17.11/psycopg3.2.10만 추가. conda-forge lock와 editable metadata를 갱신했다.
- 프로젝트 소유 cluster/private Unix socket0700/peer auth/no TCP, fsync 및 synchronous_commit on. scripts/postgres.py는 marker/uid/경로를 검사하고 이 cluster만 관리한다. 시작 옵션도 listen_addresses를 비운다.
- LocalArtifactStore는 stage → file fsync → no-clobber hardlink → directory fsync로 공개한다. 기존 파일을 덮어쓰지 않고 hash/size/symlink/nonregular/path traversal을 검사한다.
- Durable execution intent가 artifact ID와 project/base/proposal/content를 먼저 예약한다. 파일 finalize 후 project row lock/head CAS transaction으로 immutable artifact metadata/revision/head/COMMITTED intent를 함께 저장한다.
- 동일 실행은 정확히 같은 binding일 때 기존 결과를 돌려준다. 다른 payload, duplicate proposal execution, stale base는 거절한다. source와 완전한 orphan은 삭제하지 않는다.

## 검증 결과

`NEUROBUILD_TEST_DSN`을 private socket으로 설정한 `bash scripts/test_backend.sh`: **62개 PASS**, skip 없음(3.271s). Domain29 + Artifact20 + real PostgreSQL13이다. 로그는 ignored var/phase2-tests.log.

- 독립 PG integration13개: full snapshots/immutable SQL trigger/same-project FK/idempotency/동시 same-base 요청 중 하나만 성공.
- 실제 DB CHECK 실패 주입으로 head·intent 보존과 metadata rollback, final orphan 보존 및 retry 복구 확인.
- 응답을 버린 뒤 새 connection으로 exact retry하면 기존 revision 반환.
- file publication 후 directory fsync 실패가 남긴 orphan을 검증·fsync하고 복구할 수 있도록 root review에서 보강. verify의 fsync 실패는 DB publish 전에 거절한다.
- Root가 project PostgreSQL을 실제 종료·시작한 뒤 head/revision/hash/execution/exact retry 유지 확인. 정상 종료·재시작 검증이며 OS 강제전원손실 검증은 아니다.
- pip check, diff check 통과. 새 시작 옵션 실행 후 SHOW listen_addresses가 empty인 것도 확인했다.

## Review와 범위

독립 review에서 project lock/CAS, parameterized SQL/quoted schema, immutable bindings, error normalization, 공용 서버 범위를 확인했다. GPU·다른 사용자·시스템 DB·driver 변경은 없다. DB owner의 의도적 DDL이나 artifact owner의 악의적 변경에 대한 보안 경계는 아니며 읽을 때 corruption을 검출한다.

Backend 모듈은 공통 코드이며 Linux filesystem과 PostgreSQL17을 가정한다. A100 CPU/headless에서 실측했다. RTX5090은 동일 dependency/계약 사용이 예상되지만 **UNVERIFIED**다. migration은 editable checkout 내 SQL을 사용하며 standalone wheel 배포 지원을 주장하지 않는다.

IFC 문법/geometry, 승인 workflow, GPU inference, queue/API/browser는 이번 단계에서 검증하지 않았다. 다음 Phase3에서 IFC4 synthetic fixture와 deterministic MOVE_FURNITURE를 구현한다.
