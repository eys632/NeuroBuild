# Phase 3 IFC Engine / MOVE_FURNITURE

`IfcEngine`는 IFC byte를 입력받아 실제 inventory 또는 새로운 full snapshot byte를 반환하는 headless adapter다. source 파일을 열어 쓰거나 artifact/DB를 직접 수정하지 않는다. `inventory(source: bytes)`는 frozen `InventoryItem(target: Target, name: str | None)`의 tuple을 반환하고, `move_furniture(source, target, operation: MoveFurniture)`는 검증한 새 IFC bytes를 반환한다. Runtime/GPU/network profile 분기가 없다.

## 지원 범위

- IFC-SPF/UTF-8 입력과 **IFC4**만 지원한다. IFC2X3/IFC4X3, 불완전 문서, parser 오류, attribute/cardinality schema 오류를 거절한다. 모든 IfcRoot의 GlobalId는 유효한 22자 형식이고 유일해야 한다.
- 하나의 IfcProject와 명시적인 SI LENGTHUNIT가 필요하다. `METRE`의 prefix 없음/`CENTI`/`MILLI`만 지원한다. conversion-based unit, 중복 또는 누락 length unit은 거절한다.
- 대상은 실제 inventory에 있는 **단일 IfcFurniture**, 직접 연결된 **유일한 IfcBuildingStorey**다. Target의 GlobalId/storey/type이 실제 IFC와 일치해야 한다. LLM이 GlobalId를 생성하지 않는다.
- 모든 배치된 product는 finite한 3D `IfcLocalPlacement` chain을 가져야 한다. +Z upright orientation과 XY 회전/translation을 지원하며 부모의 회전도 처리한다. 방향벡터의 길이는 scale이 아니라 방향비이므로 정규화한다.
- grid/linear/2D placement, cycle, 누락 placement, tilt/inverted Z, zero direction은 거절한다. Axis/RefDirection은 모두 명시하거나 모두 생략해야 한다.
- furniture가 aggregate/nest의 부모 또는 자식이거나 opening/projection/filling feature에 연결되면 거절한다. 부분 assembly 이동을 수행하지 않는다.
- 이 단계의 world XY는 **project engineering frame**이다. Project에 명시적으로 연결된 유일한 3D representation context와 identity WorldCoordinateSystem을 요구하고 IfcMapConversion을 거절한다. mapped representation의 non-unit scale도 보수적으로 거절한다. geographic CRS나 화면상의 오른쪽은 이 연산의 좌표계가 아니다.

Import 안전성을 위해 하나의 furniture 또는 배치된 product라도 지원 범위를 벗어나면 inventory 전체를 거절한다. 지원 가능한 객체 일부만 골라 파일을 암묵적으로 수용하지 않는다. 이것은 초기 slice의 명시적인 제한이며 일반적인 IFC viewer/importer의 호환성 범위를 주장하지 않는다.

## 단위와 placement 변경

Domain이 보존한 source value/unit를 metre로 정확히 바꾼 뒤 IFC adapter 경계에서 finite double로 변환한다. Decimal과 double의 정확한 Fraction 표현으로 변환 오차를 검사한다. m/cm/mm project unit scale로 변환하고 부모의 XY 회전의 역변환을 적용하여 local XY displacement를 구한다. 부모 회전이 있는 모델에서 world X 이동을 local X 이동으로 오인하지 않는다. Double에서 underflow/overflow 또는 의미 있는 요청 이동을 보존하지 못하면 거절한다. 방향비는 최대 component로 먼저 rescale하여 subnormal/큰 방향벡터도 정규화 중 길이를 잃지 않는다.

기존 Location/Axis/Placement를 수정하지 않는다. 새로운 `IfcCartesianPoint`, `IfcAxis2Placement3D`, `IfcLocalPlacement` **3개만 추가**하고 대상의 `ObjectPlacement` reference만 교체한다. 기존 parent와 Axis/RefDirection reference는 그대로 사용한다. 공유 placement/point나 그것을 참조하는 다른 product/child placement는 기존 entity를 계속 참조하므로 자동으로 움직이지 않는다. 소유관계가 assembly/nesting인 경우는 위 지원 범위에서 별도로 거절한다.

일반 `edit_object_placement` API는 child의 world position을 보존하기 위해 child local placement를 재작성할 수 있다. 이 adapter는 기존 비대상 entity의 attribute까지 보존해야 하므로 해당 API를 사용하지 않는다. [공식 placement API](https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/geometry/edit_object_placement/index.html)

## Serialize / reopen 후 검증

결과를 IFC로 직렬화하고 다시 parse하여 다음을 검사한 뒤에만 bytes를 반환한다.

1. 모든 원래 entity ID/type/직접 attribute가 동일하다. 허용된 차이는 대상의 ObjectPlacement reference 하나뿐이며 신규 entity는 정확히 3개다.
2. GlobalId와 target/storey/type/name inventory, length unit이 동일하다.
3. 모든 비대상 product의 world transform이 동일하다.
4. 대상의 world rotation basis와 Z가 동일하며 world XY delta가 원래 Decimal 요청값과 일치한다. 정확한 Fraction 차이로 **absolute tolerance 최대 1e-9 metre**를 검사하고 큰 요청량에 상대 tolerance를 곱하여 metre 단위 오차를 허용하지 않는다. 작은 nonzero 요청은 `min(1e-9 metre, |요청| × 1e-9)`로 더 엄격하게 검사하여 0으로 사라지지 않게 한다.

STEP whitespace/문자열 escape/숫자 표기까지 원본과 같다는 byte equality는 보장하지 않는다. 원본 bytes는 그대로 보존하고 entity attribute/참조와 operation 의미를 검증한다. 실제 geometry 생성/mesh/clash/법규/구조 검증을 수행하는 기능은 아니다. Approval/stale/duplicate 검사는 Domain/Application/Persistence에서 별도로 결합한다.

오류는 `DomainError`의 `IFC_INVALID`, `IFC_UNSUPPORTED_SCHEMA`, `IFC_UNSUPPORTED_UNIT`, `IFC_UNSUPPORTED_PLACEMENT`, `IFC_UNSUPPORTED_STRUCTURE`, `IFC_DUPLICATE_GLOBAL_ID`, `IFC_TARGET_NOT_FOUND`, `IFC_TARGET_MISMATCH`, `IFC_INVALID_OPERATION`, `IFC_INVARIANT_VIOLATION`으로 전달한다. parser/IFC 원문/내부 stack trace를 public error message에 포함하지 않는다.

## 근거와 검증 경계

[IfcOpenShell file API](https://docs.ifcopenshell.org/autoapi/ifcopenshell/file/index.html)의 `from_string/create_entity/to_string`으로 parse/생성/직렬화한다. [공식 placement utility](https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/placement/index.html)의 local/world matrix 의미를 기준으로 upright XY transform을 좁게 구현한다. [공식 validation 문서](https://docs.ifcopenshell.org/autoapi/ifcopenshell/validate/index.html)에 따라 parse log와 attribute/cardinality validation을 확인한다. Native parser가 무시하는 malformed DATA를 막기 위해 앞단에서 문자열/doubled apostrophe/주석을 구분하는 narrow record scanner로 standard HEADER 3개, DATA 1개, ENDSEC/terminator, balanced parentheses, simple `#positive_id=ENTITY(...)` records와 numeric ID 유일성을 검사한다. Parse 후 entity ID set도 모든 DATA record와 대조한다. Complex entity instance, 추가 header/data section은 현재 지원하지 않는다. EXPRESS 전체 WHERE rule 또는 모든 SPF 문법을 검증했다고 주장하지 않는다. Adapter 내부 parse/log 처리는 process lock으로 묶지만 다른 code가 직접 IfcOpenShell global log에 접근하는 사용법은 피해야 한다.

Synthetic IFC4 fixture는 m/mm/cm, 회전된 부모, 공유 placement/point, 원본/비대상/Z/rotation/storey/GlobalId 불변성과 미지원 입력 거절을 독립 테스트한다. 이는 A100 CPU에서 실행하는 공통 backend 검증이며 RTX5090 현장 실행을 검증한 결과는 아니다.
