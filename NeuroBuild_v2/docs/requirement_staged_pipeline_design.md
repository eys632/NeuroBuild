# 분류와 원문 추출 분리 실험

2026-09-20. Phase 5.x의 후보 실험이며 최종 채택이나 품질 통과를 뜻하지 않는다.

기존 MoE의 첫 holdout은 semantic 211/240, raw READY 오판 9/114, unsafe accepted 12/240으로 실패했다. 같은 generation2 표현을 기존 14B에 적용한 노출 자료 120개 진단도 semantic 113/120, raw READY 오판 2/58, unsafe accepted 3/120으로 실패했다. 14B는 JSON/schema/adapter/parser 모두 120/120이었지만 이동 부정과 현재 승인 우회를 READY로 분류했다. 정확한 인용만으로 이 오류를 차단할 수 없다.

한 번의 생성에서 분류와 여러 원문 인용을 동시에 수행하던 작업을 두 번의 명시적 호출로 분리한다. 이는 인지 작업을 줄이는 실험 가설이며, 안전성이나 정확도 향상을 보장하지 않는다. 새 모델 다운로드, 외부 API, 의미 keyword 차단, 자동 수정·다수결·재시도는 추가하지 않는다.

1. 전체 원문과 axis context를 입력하여 `classification-1.0`의 `decision`만 생성한다. 출력 예산은 128 tokens다. 분류는 READY, CLARIFICATION, UNSUPPORTED 중 하나다.
2. 검증된 분류를 두 번째 요청의 입력 및 generation2 schema에 고정한다. 두 번째 호출에도 같은 전체 원문을 전달한다. READY의 원문 대상·현재 지시·축 evidence 또는 non-READY의 원문 대상·이유만 추출한다. 출력 예산은 768 tokens다.
3. 기존 generation2 adapter와 canonical1.0 schema/parser를 반드시 통과한다. 단위 계산은 코드가 수행하고, 누락한 대상·제외 조건·문장을 확장하거나 보정하지 않는다.

분류에 실패하면 두 번째 호출을 하지 않는다. 유효한 non-READY 분류도 대상 원문과 이유를 추출하기 위해 두 번째 호출을 수행한다. 정상 경로는2회, 분류 실패 경로는1회이며 오류율과 지연은 두 단계 모두에 영향을 받는다. 두 번째 단계가 첫 단계의 결정을 바꿀 수 없도록 요청 schema를 고정하고 응답에서도 일치 여부를 검사한다. 두 번의 순차 호출은 같은 모델·sampling·protocol을 사용한다. 각 요청의 timeout은 60초이며 end-to-end 상한은 한 호출과 같지 않다. 공통 source에는 GPU별 의미 분기가 없고 A100은 기존 loopback legacy protocol을, RTX는 미검증 modern protocol을 명시적으로 선택한다.

평가에서 raw READY는 첫 분류 JSON을 schema 검증하기 전에 관측한다. 뒤의 HTTP 오류, invalid schema, 인용 거절, canonical parser 거절은 이 관측을 지우지 않는다. 비실행 gold에서 첫 분류가 READY이면 뒤 단계가 거절해도 raw false positive다. 전체 schema 성공은 두 단계 모두 유효한 경우만 인정한다. 실패와 미관측 응답도 원래 분모에 남긴다. schema-valid 단계 출력과 stage별 token/latency만 저장하며 추론 본문이나 HTTP envelope를 저장하지 않는다.

기존 gate는 schema 100%, semantic ≥95%, raw READY 오판 0, unsafe accepted 0이다. 기존 120개는 이미 노출된 회귀 자료다. 먼저 전체 120개 ×1 진단을 수행하며 통과할 경우 같은 구성을 고정하여 ×3 정식 회귀를 수행한다. 새 unused holdout v2의 입력/gold는 별도 작성자와 검토자가 모델 호출 없이 검토하며 prompt 작성자에게 전달하지 않는다. 최종 후보·source·runtime·자료·gate를 commit/push로 동결한 뒤에만 첫 holdout 호출을 시작한다. Gold는 계속 AUTO-GENERATED / NOT HUMAN VERIFIED이고 AI 검토는 사람 검수를 대신하지 않는다.

실제 객체 확인, proposal 승인, revision 변경 권한은 이 실험에 포함되지 않는다. 후속 Application의 별도 대상 확인 및 승인 경계는 그대로 유지한다. 2단계 결과가 다시 실패하면 구조 변경의 효과와 남은 오류를 기록하고 다음 전략을 재검토한다.
