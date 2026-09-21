# Phase5.x Requirement → Application 경계 검토

검토일: 2026-09-20 KST. 판정: **검토 범위 PASS, 추가 중대 blocker 없음**.
Phase5.x freeze checkpoint `931c625` 이후 평가가 진행되는 동안 수행했다.
Frozen parser/client/scorer/prompt/gold를 변경하거나 모델 응답을 사용하지 않았다.
이는 Phase5.x 실제 모델 평가 통과나 Phase6 구현 완료 판정이 아니다.

## 소스에서 확인한 승인 경계

[Requirement parser](../../src/neurobuild/application/requirements.py)는 code가 공급한
requirement/project/base UUID와 원문을 사용한다. 출력 schema의 추가 필드는 거절하며
반환하는 `SemanticRequirement`에는 approval이나 resolved GlobalId 필드가 없다.
대상 description은 원문 문자열이고 실제 IFC 객체 식별·유일성 확인 결과가 아니다.
CLARIFICATION/UNSUPPORTED는 실행 operation을 가질 수 없다.

[RenovationService.begin](../../src/neurobuild/application/workflow.py)는 전달된 Domain
값을 재구성·검증·복사하고 project/base/current head를 확인한다. READY는 실제 base IFC의
inventory를 읽어 `WAIT_TARGET`으로 시작한다. 이 단계에서 confirmation/proposal/approval을
자동 생성하지 않는다. 나머지 두 decision은 각각 `WAIT_CLARIFICATION`/`UNSUPPORTED`로
남으며 target/proposal review와 apply 전이가 차단된다.

Target confirmation은 실제 inventory의 GlobalId 하나를 명시적으로 선택해야 한다.
그 후 proposal을 생성해도 `WAIT_APPROVAL`이며 별도의 bool 승인과 정확한 proposal
ID/fingerprint가 필요하다. Apply는 service가 소유한 원래 requirement, inventory target,
confirmation, proposal operation, approval의 binding을 확인한다. 반환 snapshot을 변조해도
내부 authority는 바뀌지 않는다. 새 실행에는 head 검증과 DB CAS가 적용되며, committed
retry도 기존 review authority와 execution/result binding을 확인한다.

기존 [Workflow tests](../../tests/test_workflow.py)의 별도 승인·실제 target membership·
forged snapshot·project/base·stale/duplicate·recovery 검증을 읽었다. 이번 검토에서 전체
회귀를 중복 실행하거나 과거 테스트 결과를 새 실행 결과로 표시하지 않았다.

## 실제 경계 probe

Backend `.conda/bin/python -B`에서 실제 PostgreSQL private Unix socket과 IfcOpenShell을
사용한 임시 `unittest` probe 2개가 **2/2 PASS, skip0, 0.688s**였다. 기존 workflow test의
synthetic IFC fixture와 setup/cleanup을 재사용하되, Requirement는 고정한 합성 JSON을
현재 parser에 통과시켜 만들었다. 모델 stub의 품질이나 실제 모델 추론을 측정한 것이 아니다.

| Probe | 확인 결과 |
|---|---|
| Parsed READY → review guard | `WAIT_TARGET`와 빈 confirmation/proposal/approval 확인. 즉시 apply는 `TARGET_NOT_CONFIRMED`. 대상 description을 GlobalId로 제출하면 `IFC_TARGET_NOT_FOUND`. 실제 target 확인·proposal 생성 이후에도 apply는 `PROPOSAL_NOT_APPROVED`. 반환 snapshot에 approval을 위조해도 동일하게 거절 |
| Non-READY / malformed → rejection | Parsed CLARIFICATION/UNSUPPORTED에서 confirm/create/approve/apply 모두 거절. JSON의 추가 approval/GlobalId는 `INVALID_MODEL_OUTPUT`. 이미 만들어진 Domain의 nested axis를 변조해도 begin에서 `INVALID_REQUIREMENT`로 거절 |

두 probe 모두 종료 시 head는 V0, revision은 1개, execution intent는 import용 1개,
artifact는 import용 1개였다. Source artifact bytes도 원본과 같았다. 테스트가 직접 만든
무작위 `nb_test_<uuid>` schema와 프로젝트 `var/tests/workflow`의 임시 artifact만 정리했다.
기존 DB/서버·다른 사용자·GPU·모델 서버에는 변경을 가하지 않았다.

## 신뢰 경계와 남은 작업

`begin`은 검증된 Domain 입력을 받는 내부 Python API이며 모델 JSON을 직접 받는
endpoint가 아니다. 임의의 trusted Python caller가 직접 만든 유효한 Domain이 parser를
통과했다고 증명하지도 않는다. 향후 자연어 진입점에서는 공통 client/parser 경로를
사용하고 모델에게 confirm/approve 호출 권한을 주지 않아야 한다.

현재 review는 메모리 상태이며 bool 결정을 누가 보냈는지 인증하는 시스템은 아니다.
Phase7의 durable review/worker와 Phase8의 인증·접근 경계가 남아 있다. 서비스 내부의
private registry에 접근 가능한 임의 Python 코드를 격리하는 sandbox라고 주장하지 않는다.

Parser의 원문 일치와 Domain 검증은 조건·부정·대상 제외의 의미를 증명하지 않는다.
잘못된 READY는 별도 승인 없이 IFC를 변경할 수 없지만, 잘못된 제안을 만들 수 있으므로
모델의 critical FP/잘못된 이동 지표를 승인 단계가 대신하지 않는다. 자동 object resolution,
실제 로컬 모델부터 IFC 변경까지의 연결, API/browser 흐름은 아직 이번 검토 범위 밖이다.

이 경로에는 A100/RTX별 business logic 분기가 없다. 같은 parser/Domain/Application을
사용하지만 모델 runtime별 의미 정확도와 RTX5090 실제 실행은 별도로 검증해야 한다.
