# Generation2 Requirement → Application 독립 검토

2026-09-20 KST. **범위 내 PASS: CPU+실제 private PostgreSQL/IfcOpenShell probe4/4, skip0.**
첫 holdout 실행 중 별도 고정 합성 응답으로 검증했다. Holdout 출력·모델 서버·GPU에 접근하지 않았다.
자료는 **AUTO-GENERATED / NOT HUMAN VERIFIED**이며 실제 모델 의미 정확도를 평가한 결과가 아니다.

[Generation2 adapter](../../src/neurobuild/application/requirement_generation.py)의 명시적
`GenerationContract.QUOTES`로 branch 형태 JSON을 해석한 뒤 기존 `SemanticRequirement`를
[RenovationService](../../src/neurobuild/application/workflow.py)에 전달했다. READY/CLARIFICATION/
UNSUPPORTED 정상 입력은 [분기 schema](../../schemas/requirement_generation_v2_decision_branches.schema.json)로도 확인했다.
실제 [workflow fixture](../../tests/test_workflow.py)의 setup/cleanup을 재사용했으며 전체 회귀를 재실행하지 않았다.

| Probe | 실제 관측 | 거절 수 |
|---|---|---:|
| READY의 두 review 경계 | dx1m/dy-0.25m로 파싱해도 WAIT_TARGET, confirmation/proposal/approval 없음. Description은 GlobalId로 사용할 수 없음. 실제 inventory target 확인 후 TARGET_CONFIRMED, proposal 생성 후 WAIT_APPROVAL. 틀린 fingerprint 승인 및 미승인 apply 거절 | 5 |
| 반환 snapshot 승인 위조 | 반환 객체에 올바른 ID/fingerprint의 가짜 approval과 APPROVED 상태를 넣어도 내부 상태는 WAIT_APPROVAL이며 apply 거절 | 1 |
| Non-READY 두 종류 | CLARIFICATION→WAIT_CLARIFICATION, UNSUPPORTED→UNSUPPORTED. Operation 없음. 각 상태에서 confirm/create proposal/approve/apply를 모두 거절 | 8 |
| Model 권한·버전 필드 주입 | 추가 approval, 추가 global_id, 1.0 version spoof, non-READY의 nonnull instruction/evidence를 schema와 adapter가 거절 | 4 |

**총18개 DomainError 거절**을 확인했다. 각 probe 종료 때 head=V0, revision1개,
import execution intent1개, artifact1개였고 원본 IFC bytes와 SHA가 그대로였다.
정상 승인이나 apply 성공을 호출하지 않았으므로 새 revision은 생성되지 않았다.

최종4개 실행 시간은 unittest 기준1.250초(후처리 포함1.263초)다. 최초 실행의 probe가
`list_revisions` 반환 list를 tuple과 직접 비교해 실패했으므로 probe 비교만 고친 뒤 재실행했다.
Application 수정은 없었다. 두 실행에서 직접 만든 무작위 `nb_test_<uuid>` schema 총8개와
프로젝트 `var/tests/workflow`의 임시 artifact directory8개를 모두 정리하고 부재를 확인했다.
기존 DB 상태·서버 설정·다른 사용자 자료는 변경하지 않았다.

사용한 임시 routine은 `var/review-tools/probe_generation2_application.py`, SHA
`fd8be2c611cf414b1c803a2d63ac82765763dda06007eea68621cd5422732bb4`다.
Adapter/parser/client/scorer/두 schema/prompt/두 dataset와 workflow/domain/persistence/IFC/fixture 등
**15개 파일 hash가 probe 전후 동일**했다. Frozen 평가 소스는 변경하지 않았다.

이 경로에서 model quote는 승인이나 resolved GlobalId를 만들지 못한다. 다만 원문 부분문자열이
대상 범위·조건의 올바른 의미를 증명하지는 않으며, 승인 단계가 모델 unsafe 지표를 면제하지 않는다.
현재 review registry는 메모리 상태이고 trusted Python 내부 API이며 사용자 인증·durable review가 아니다.
실제 모델→자동 대상 해석→승인 UI→IFC 적용, 향후 API/worker 연결과 RTX 실행은 이번 검토 범위 밖이다.
