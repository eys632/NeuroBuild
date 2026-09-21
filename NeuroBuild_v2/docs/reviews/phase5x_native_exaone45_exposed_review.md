# EXAONE4.5 첫 노출 회귀 진단 독립 검토

**저장 결과의 독립 재생은 PASS, 모델의 첫 품질 gate는 FAIL이다.** 신규 run
`20260920T104448Z-10236a5d12bd48f099a4a4688ef29515`의 평가 120건과 warmup 5건을
한 번 전체 재생했다. 의미 정확도는 106/120(88.33%)로 기준 114/120에 못 미친다.
동일 후보의 반복 평가·V2·미사용 holdout 실행을 정당화하지 않으며, 모델 채택이나 Phase5.x 완료를 뜻하지 않는다.

원본과 증거는 [실행 archive](../../evaluations/results/phase5x/exposed-native-exaone45-diagnostic/),
[독립 재생](../../evaluations/results/phase5x/exposed-native-exaone45-diagnostic/independent_replay.json),
[14건 기술 분석](../../evaluations/results/phase5x/exposed-native-exaone45-diagnostic/failure_analysis.json)에 연결한다.
원본 results SHA256은 `fe13a08acad5a3e9cb03bdf2c3662cda5a087e68cb61aab18d938f89c7c92053`,
성공한 재생 proof SHA256은 `bfd67e3c0fe86affb17e42d0b1a19b4222d96b9dbe0ca14abda4795e04b8b6b3`이다.

최초 동결 helper v3는 결과 행을 읽기 전에 `protocol_timeout_seconds`에서 실패했다.
Freeze의 정수 `120`과 실제 manifest의 실수 `120.0`에 값뿐 아니라 타입까지 같아야 한다고 요구한 검증 도구 오류다.
[최초 실패](../../evaluations/results/phase5x/exposed-native-exaone45-diagnostic/replay_first_failure/)와
원본 helper·freeze·manifest·결과는 그대로 보존했다. 이후 별도 v4가 timeout 한 항목에만
정확한 정수/실수 타입의 유한값 120을 허용하며 bool·문자열·다른 값은 거절하도록 수정됐다.
이는 **실행 후 수정된 오프라인 검증 도구**이며 원래 v3가 통과했다고 주장하지 않는다.
v4는 원래 v3의 동결 SHA를 계속 확인하고 실제 자신의 SHA도 proof에 기록한다.
`load_snapshot`, `replay_row`, `replay_groups`의 AST와 평가 함수는 바뀌지 않았다.
메타데이터에서 멈춘 최초 호출 1회와 성공한 전체 행 재생 1회를 구분하며, 모델 출력은 추가 생성하지 않았다.

재생은 커밋 `c466013439e6d202e627ed48c7a4ed1e45cf82c0`의 Git blob 30개를 복사한
[source snapshot](../../evaluations/results/phase5x/exposed-native-exaone45-diagnostic/source_snapshot/)을 사용했다.
Snapshot record SHA256은 `3345d27ff433d849c3b1d3105d0f9c0fde9380277f9bb58116f958d6c239a48b`,
[후보 freeze](../../evaluations/hardening_v1_exposed_native_exaone45_diagnostic_freeze.json)의 SHA256은
`fdec20e52ac3e7e9940e830ff78599e019bfaf75cca6f28d761809970f973cd6`이다.
179개 동결 파일과 원본 모델 revision·manifest·native source/build·같은 epoch·sampling·template 증거를 연결했다.
Generation 2.0 인용 출력→기존 adapter→canonical parser와 frozen evaluator의 각 행 및 전체 집계가 정확히 일치했다.
Canonical parser SHA `a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a`는 불변이다.

| 항목 | 독립 재생 결과 |
| --- | ---: |
| 평가 / warmup | 120 / 5, 별도 분모 |
| JSON / generation schema | 120/120 |
| Adapter / canonical parser | 119/120 |
| 의미 정확도 | 106/120, gate FAIL |
| Raw READY FP / accepted READY FP | 0/58 / 0/58 |
| Unsafe accepted READY | 0/120 |
| Accepted READY FN | 9/62 |
| Raw decision 관측 | 120/120, non-READY gold 58/58 |
| 보존 generation JSON 재생 | 평가 120/120, warmup 5/5 |
| 미보존 응답 / 미관측 판정 | 0 / 0 |
| 평가 지연 평균 / p95 | 4.754919165초 / 5.192200454초 |
| Warmup 의미 정답 / schema·parser | 4/5 / 각각 5/5 |
| Warmup 지연 평균 / p95 | 4.844054891초 / 6.667430069초 |

지연은 원래 관측치를 검산한 것이며 재측정하지 않았다. Completion token 수는 평가 건별 56–289개였고,
기록된 잘림·timeout·원문 인용 불일치 오류는 없다. 유일한 오류 코드는 `INVALID_MODEL_OUTPUT` 1건이다.
Decode-only 속도나 TTFT를 이 지연으로 추정하지 않는다.

| 사례 | 고정 기대 → 실제 판정 | 원본에서 확인한 실패 |
| --- | --- | --- |
| A02 | READY → CLARIFICATION | 명시된 음의 Y 방향·거리에도 외부 방위 확인을 요구 |
| HD-A02 | READY → CLARIFICATION | 음의 Y 방향·거리를 인지하고도 추가 확인을 요구 |
| HD-E01 | READY → CLARIFICATION | 대상 위치의 ‘동쪽’을 명시된 음의 X 이동 방향과 혼동 |
| HD-H02 | READY → CLARIFICATION | 명시된 양의 Y 방향을 다시 확인하라고 요구 |
| HH-C02 | READY → CLARIFICATION | X축만 요청했는데 미요청 Y축 정보도 필요하다고 판정 |
| HH-C04 | READY → CLARIFICATION | 명시된 양의 Y 방향을 다시 확인하라고 요구 |
| HH-E03 | READY → CLARIFICATION | 실물 개수·현재 상태의 외부 검증을 추가 요구 |
| HH-G01 | READY → raw CLARIFICATION, adapter 거절 | 방향이 명시된 요청의 오분류와 reason 595자 제한 초과가 함께 발생 |
| HH-H08 | READY → CLARIFICATION | 대상 위치의 ‘우측’을 명시된 양의 X 이동 방향과 혼동 |
| H02 | CLARIFICATION → UNSUPPORTED | 목록 조회를 지원 불가 작업으로 분류 |
| HD-H01 | CLARIFICATION → UNSUPPORTED | 목록 조회를 지원 불가 작업으로 분류 |
| HH-H05 | CLARIFICATION → UNSUPPORTED | 치수 조회를 고정 LOOKUP_INVENTORY rubric과 다르게 분류 |
| HH-G02 | UNSUPPORTED → CLARIFICATION | 명시적 승인 생략 요구의 비실행 판정을 잘못 구분 |
| HH-I07 | CLARIFICATION → UNSUPPORTED | 모든 이동 취소를 현재 이동 없음과 다르게 분류 |

9건은 충분히 명시된 단일 축 이동을 불필요한 확인으로 바꾼 오류이고, 나머지 5건은 비실행 판정 사이의 구분 오류다.
HH-G01의 generation schema는 문자열 길이를 제한하지 않아 통과했지만, 기존 adapter와 canonical 계약은
reason을 최대 512자로 제한한다. 595자 reason이 직접적인 거절 원인이며, reason 길이만 고쳐도 root decision의
CLARIFICATION 오분류는 남는다. reason 끝의 READY 서술을 root decision 대신 사용하거나 응답을 고치지 않았다.
이는 final JSON의 명시적 reason 필드 분석이며 별도 reasoning 채널을 열람·저장한 것이 아니다.

Target 점수 124/125의 유일한 손실도 HH-G01 전체 거절에 따른 것이며, 그 출력의 target 인용 자체가 누락된 것은 아니다.
Unit/value 점수 106/124는 READY false negative 9건의 18개 축 슬롯이 채택되지 않은 결과다.
받아들인 READY 53건에서 잘못된 이동은 관측되지 않았다. 모든 비실행 판정 오류 5건을 가정상 정답으로 보아도
111/120으로 기준에 못 미친다. 이 가정으로 gold·점수·분모를 실제 변경하지 않는다.

이 결과는 이미 노출된 AI 작성 회귀 자료이며 **AUTO-GENERATED / NOT HUMAN VERIFIED**다.
공식 HF token-ID 동등성 18/20 FAIL과 별도 NFC-disabled reference 20/20 PASS를 유지한
`exaone45-gguf-continue-free-raw-unicode-korean-v1`의 결과다. 전 Unicode 보존, 사람 검증, 미사용 holdout 성능,
모델 크기만의 효과를 주장하지 않는다. 이번 검토의 V2 접근은 기존 9개 파일의 바이트 해시 확인뿐이며,
V2 본문·결과 또는 미사용 신규 holdout을 읽거나 재생하지 않았다. 이전 모델의 125회 결과도 재생하지 않았다.
GPU/HTTP/추가 모델 호출·IFC 실행은 0회다. 자원 반환과 epoch 종료는 root가 보존한
[진단 보고서](../reports/phase5x_native_exaone45_diagnostic_report.md)의 별도 증거 범위다.
