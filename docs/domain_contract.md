# Phase 1 Domain Contract

공통 package는 `src/neurobuild/domain`이며 Python 3.12 표준 라이브러리만 사용한다. Domain은 GPU/profile, 모델, IFC library, DB, filesystem mutation, network에 의존하지 않는다. 모든 record는 frozen dataclass이고 nested value도 불변 type으로 제한한다. 입력 위반은 `DomainError.code`로 구분한다. API schema/strict deserialization과 실제 inventory 검증은 뒤 단계 adapter의 책임이다.

## Requirement와 이동 단위

`SemanticRequirement`는 `requirement_id`, `project_id`, `base_revision_id`, 원문 `source_text`, 그대로 보존한 `target_description`, 상태 및 선택적인 operation/reason을 가진다. GlobalId 필드가 없으며 LLM 출력이 GlobalId를 생성하도록 맡기지 않는다. 원문과 description은 trim/번역/재작성하지 않는다.

| 상태 | 계약 |
| --- | --- |
| `READY` | 비어 있지 않은 target description과 단일 `MoveFurniture` 필수, reason 없음 |
| `CLARIFICATION` | reason 필수, executable operation 없음. 방향·거리·대상 등 모호성이 해결되기 전 실행 금지 |
| `UNSUPPORTED` | reason 필수, executable operation 없음. 지원 가능한 부분만 골라 자동 실행 금지 |

`Length(value: Decimal, unit: LengthUnit)`는 입력 수치와 단위 `m/cm/mm`를 보존하고 `.metres`로 정확하게 변환한다. float/int/bool/문자열을 묵시적으로 숫자로 변환하지 않으며 NaN/Infinity를 거절한다. 외부 숫자는 adapter가 검증 후 `Decimal`로 전달해야 한다. Decimal coefficient/exponent로 변환하므로 전역 precision/rounding 설정에 영향을 받지 않는다. LLM에는 단위 변환이나 산술을 맡기지 않는다.

`MoveFurniture(dx, dy)`는 **IFC project engineering/world 좌표계의 상대 XY 변위**다. 객체 local axis 또는 화면상의 오른쪽을 뜻하지 않는다. 방향이 이 좌표계로 해석되지 않으면 clarification한다. 최소 한 축의 이동이 0이 아니어야 한다. Z/rotation/scale/storey 변경 필드는 제공하지 않고 다른 kind/frame을 거절한다. 하나의 proposal은 하나의 target만 가진다. IFC Adapter는 이 world displacement를 지원되는 placement chain에 변환하되 Z/rotation/scale/storey와 비대상을 보존해야 한다.

## Identity와 revision

Application entity ID는 `UUID` 값이다. 문자열을 직접 허용하지 않는다. `Target`은 `IfcFurniture`의 실제 inventory GlobalId와 storey GlobalId를 받으며 IFC compressed GlobalId의 22자 형식을 검사한다. **형식 통과가 inventory 존재나 올바른 storey의 증거는 아니다.** Object Resolver/IFC Adapter가 base revision inventory에서 가져온 target만 전달하고 적용 직전 다시 검증해야 한다.

`ArtifactRef`는 artifact ID, lowercase SHA256, 양수 byte size, canonical relative POSIX storage key를 가진다. 절대 경로/상위 경로/비정규 경로를 거절한다. 실제 파일의 hash/size, storage root containment 및 symlink 안전성은 Storage Adapter가 검증한다. 이 record를 생성해도 파일은 생성/수정되지 않는다.

`Revision`은 project, number, immutable full IFC4 snapshot reference, parent를 가진다. V0만 parent가 없고 이후 revision은 parent가 필요하며 self-parent는 금지한다. 부모의 project/순번/존재와 artifact immutability는 repository가 검증해야 한다. `Project`의 head는 아직 upload가 없으면 `None`이다. `validate_project_head`는 head ID/project의 일치를 확인한다.

## 대상 확인과 별도 변경 승인

`TargetConfirmation`은 project/base/requirement와 단일 inventory target에 결합하고 `confirmed`가 명시적인 bool이어야 한다. `Proposal`은 그 confirmation ID, 같은 requirement/base/project, target, operation에 결합한다. `ProposalApproval`은 별도의 ID와 `approved` bool을 가지며 proposal ID/base/project/**content fingerprint**에 결합한다. 대상 확인을 proposal 승인으로 변환하지 않는다.

Fingerprint는 contract version, 모든 proposal binding ID, target/storey/type, operation/frame, 원래 값/단위 및 변환된 metre를 canonical JSON으로 직렬화한 SHA256이다. `1`, `1.0`, `1.00` 같은 동일한 Decimal 값과 +/-0의 표기 차이는 같은 fingerprint다. 단위 또는 원본 수치가 바뀌면 같은 metre라도 content 변경으로 취급한다. 이것은 content binding이며 서명/인증 토큰이 아니다. 사용자 인증/approval 생성 권한은 Application/API 경계에서 검증해야 한다.

`require_apply_authorization(project, current_head, confirmation, proposal, approval, already_applied=False)`는 다음을 모두 요구한다.

1. 저장된 execution 기록으로 해당 proposal이 이미 적용되지 않았음.
2. Project와 실제 current head의 project/ID가 일치하고 proposal base가 현재 head임.
3. 명시적으로 확인한 target의 confirmation ID/project/base/requirement/target이 proposal과 일치함.
4. 별도의 승인 record가 approved이며 project/proposal/base/fingerprint가 정확하게 일치함.

중복은 `ALREADY_APPLIED`, stale base는 `STALE_PROPOSAL`, target 확인 누락은 `TARGET_NOT_CONFIRMED`, 별도 승인 누락은 `PROPOSAL_NOT_APPROVED`다. 각 binding 오류는 `PROJECT_MISMATCH`, `INVALID_HEAD`, `CONFIRMATION_MISMATCH`, `APPROVAL_MISMATCH`로 구분한다. 이 함수는 pure guard이며 동시성 제어 수단이 아니다. Repository가 transaction/head compare-and-swap 및 unique execution 제약 아래에서 다시 검사해야 한다.

## Execution 상태

`Execution`은 project/proposal/base와 연결된다. 전이는 새 immutable record를 반환한다.

| 현재 | 허용되는 다음 상태 | 결과 조건 |
| --- | --- | --- |
| `PENDING` | `RUNNING`, `FAILED` | 실행 전 거절도 FAILED로 기록 가능 |
| `RUNNING` | `SUCCEEDED`, `FAILED` | 작업 완료 또는 실패 |
| `SUCCEEDED` | 없음 | base와 다른 result revision 필수, error 없음 |
| `FAILED` | 없음 | error code 필수, result revision 없음 |

Retry는 기존 terminal record를 덮어쓰는 전이가 아니다. Durable job/execution 정책은 뒤 단계에서 별도로 구현하며 사용자 review 대기는 이 execution 상태로 worker를 점유하지 않는다.

## 검증 범위와 이후 단계

Phase 1 unit test는 단위/precision, semantic 상태, 지원 범위, 불변성, fingerprint, target/approval 분리, stale/duplicate/cross-project/mismatched binding, revision와 execution 상태를 검증한다. PostgreSQL transaction, 실제 IFC placement/inventory, LLM schema, 사용자 인증, queue/restart는 이 계약의 unit test로 검증했다고 간주하지 않는다. Phase 2 이후 관련 integration을 추가한다.
