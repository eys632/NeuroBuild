# Phase 3 — IFC Engine / MOVE_FURNITURE

2026-09-20. IFC4 synthetic 모델에서 단일 IfcFurniture의 같은 Storey 상대 project-world XY 이동을 구현했다. 실제 source/비대상/GlobalId/Z/rotation/scale/storey 불변성을 검증한다. 원격 checkpoint는 STATUS 및 후속 실행 기록을 따른다.

## 구현과 환경

- Backend IfcOpenShell0.8.5 conda-forge py312hfac0a26_8, CPU/headless. GPU/시스템 driver/CUDA/glibc 미변경.
- PyPI wheel은 GLIBC_2.32 import 오류로 사용하지 않았다. Conda 호환 build와 transitive library를 lock에 고정했다. PyPI/Conda 파일 중복을 피하고 native dependency 확인을 pip metadata와 구분했다. Backend1.4G/cache802M/root83G.
- Stateless IfcEngine.inventory / move_furniture는 bytes를 받아 실제 Target inventory 또는 새로운 full IFC bytes만 반환한다. File/DB/LLM/승인 로직을 포함하지 않는다.
- m/cm/mm, upright3D LocalPlacement와 부모 XY 회전 지원. 단일project/context, identity WCS와 direct Storey containment를 요구한다. 지원하지 않는 placement/units/assembly/schema/context는 명시 거절한다. 자세한 범위는 ../ifc_engine.md.
- 대상의 CartesianPoint/Axis2Placement3D/LocalPlacement3개만 추가하고 ObjectPlacement ref만 교체한다. 기존 shared entity를 수정하지 않는다. Serialize/reopen 후 모든 원래 entity와 product world transform을 감사한다.

## 검증과 수정

- Root 전체87 tests PASS(3.728s, PostgreSQL skip0): Domain29/Artifact20/IFC25/PostgreSQL13. Independent IFC25 tests도 통과했다. 최종 scanner probe14개(잘못된입력11/정상3)와 수치손실 재검증에서 알려진 gate blocker가 없다.
- Independent realIFC tests: m/cm/mm, arbitrary parent rotation/translation, shared placement/point/child reference, source bytes/hash, 비대상전체entity, inventory/GlobalId/storey/Z/rotation, schema roundtrip, headless native mesh vertex displacement.
- Invalid input/schema/type/id/storey, grid/2D/tilted/cyclic placement, ambiguous units/containment, duplicate numeric/global IDs, context와 수치 범위 거절.
- Root real PostgreSQL integration smoke: mm+33도부모회전 synthetic IFC4를 V0 저장 → 이동 → V1 full snapshot 저장. sourcehash/head/lineage/두revision/inventory 보존 PASS. 승인 workflow가 포함된 검증은 아니다.
- Independent 추가60개 합성 변환 probe: 모두통과, 최대오차4.27e-14m. 생성 fixture는 AUTO-GENERATED / NOT HUMAN VERIFIED.

Review에서 발견한 실제문제를 회귀로 보강했다. Nativeparser가 DATA garbage/missing ENDSEC를 로그없이무시하는 문제에는 narrow SPF framing/record scanner를 추가했다. 큰좌표/큰delta의 상대허용오차 및 Decimal→double 변환이 metre단위손실을숨기는 문제에는 exact Fraction과 최대1e-9m 절대오차를 사용했다. 작은요청은 요청크기에비례한 더엄격한오차를사용한다. Subnormal direction은 rescale 후정규화한다. 잘못된입력을정상화하여성공으로처리하지않는다.

## Review와 한계

공통 Python adapter에 하드웨어분기는없다. A100 CPU에서실측했고 RTX5090은 동일Linux/Conda계약이예상되지만 **UNVERIFIED**다. GUI/display/외부LLM/민감IFC를사용하지않았다. IFC형식의전체 EXPRESS/STEP grammar/clash/구조/법규를검증하는기능은아니며 지원범위가좁다. Nativeparser log 접근은 adapter내 lock으로묶는다.

Phase4에서 별도TargetConfirmation과ProposalApproval을 실제 IFC inventory/Revision/Persistence에 연결한다. 이 단계의저수준 IFC/DB API는 사용자권한검사를대신하지않는다.
