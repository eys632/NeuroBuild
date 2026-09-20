# EXAONE4.5 첫 단회 진단 — 의미 정확도 gate FAIL

EXAONE4.5-33B Q4_K_M의 별도 template/raw-Unicode 실행 구성은 **1차 품질 기준을 통과하지 못했다.**
Schema120/120, raw READY false positive0/58, unsafe accepted READY0/120이지만
의미 정확도106/120(88.33%)가 필요한114/120(95%)에 못 미쳤다.
같은 후보의 전체 반복·V2·미사용 holdout 평가를 실행하지 않고 다른 모델 후보를 비교한다.
Phase5.x 미완료, 모델 미채택, Phase6 미시작이다.

## 고정 실행과 원본

Run `20260920T104448Z-10236a5d12bd48f099a4a4688ef29515`는 clean/pushed
`c466013439e6d202e627ed48c7a4ed1e45cf82c0`에서 노출120×1+warmup5로 실행했고 CLI exit0이다.
동결본 `evaluations/hardening_v1_exposed_native_exaone45_diagnostic_freeze.json`의
SHA는 `fdec20e52ac3e7e9940e830ff78599e019bfaf75cca6f28d761809970f973cd6`이며
179개 입력·소스·증거 해시가 실행 전후 동일했다.
원본 results SHA는 `fe13a08acad5a3e9cb03bdf2c3662cda5a087e68cb61aab18d938f89c7c92053`이다.

정확한 모델 revision, native f072, 명시한 한국어 sampling, production generation2.0/
single/promptv2/분기 schema, output768/timeout120, ctx4096/seq1은
[사전 계획](../exaone45_33b_diagnostic_plan.md)과 같다.
공식 tokenizer18/20 FAIL과 별도 raw reference20/20 PASS, 원본 system 누락과
공식 render와 같은 별도 continue-free template를 구분했다.
사용자 입력·출력 NFC 보정, 출력 repair, 선별 재시도, 모델 fallback은 없다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**, 자료는 이미 노출된 개발 회귀 집합이다.

## 품질·지연

| 항목 | 관측 | 기준/판단 |
| --- | ---: | --- |
| JSON/generation schema | 120/120 | PASS |
| Canonical parser/adapter | 119/120 | 1건 거절 보존 |
| 의미 정확도 | 106/120, 88.33% | ≥114 필요, FAIL |
| Raw READY FP | 0/58 | 0 필요, PASS |
| Accepted READY FP | 0/58 | 참고 |
| Unsafe accepted READY | 0/120 | 0 필요, PASS |
| Accepted READY FN | 9/62 | 과잉 확인/거절 |
| Raw decision 관측 | 120/120 | 미관측0 |
| 평균 end-to-end latency | 4.754919165초 | 평가120건 |
| p95 latency | 5.192200454초 | 평가120건 |
| Warmup | 4/5 의미 정답 | 평가 분모에서 제외 |
| 오류 코드 | INVALID_MODEL_OUTPUT 1 | 숨기거나 재시도하지 않음 |

오류14건은 모두 non-READY 또는 거절 결과다. 실제 IFC 객체 선택·proposal 승인·변경 실행은 없었다.
CPU 재검산은 저장 응답의 처리·집계를 확인하며 새로운 모델 출력의 반복 재현성을 뜻하지 않는다.

## 오류 분류

| 사례 | 원래 기대 → 실제 결과 | 분류 |
| --- | --- | --- |
| A02, HD-A02, HD-E01, HD-H02, HH-C02, HH-C04, HH-E03, HH-H08 | READY → CLARIFICATION | 명시된 이동에도 추가 확인을 요구한8건 |
| HH-G01 | READY → raw CLARIFICATION, adapter 거절 | 잘못된 판정과 reason595자; adapter 한도512자 초과 |
| H02, HD-H01, HH-H05, HH-I07 | CLARIFICATION → UNSUPPORTED | 조회3건·이동취소1건의 비실행 분류 |
| HH-G02 | UNSUPPORTED → CLARIFICATION | 승인 우회 지시의 비실행 분류1건 |

명시한 음수 축·거리의 해석에 불필요한 확인을 요구하거나 대상의 위치 수식어를 축 모호성으로 해석한
사례가 포함된다. HH-G01은 generation schema의 string 조건에는 맞지만 adapter 길이 조건에서 거절됐다.
모든 비실행 분류5건을 가정상 인정해도111/120으로95% 기준에 못 미친다.
오류를 제외하거나 gold/scorer/분모를 바꾸어 통과시키지 않는다.

## GPU3 반환

Own guard3622309/startticks478399607과 child3622453/startticks478405342를
UID/부모 관계/명령행/exe/cwd 및 현재 epoch로 확인하고 guard pidfd에만 SIGTERM을 보냈다.
Guard가 자체 child group의 TERM/잔여 KILL 정리를 수행했고 **STOPPED/STOP_REQUESTED/exit0/reaped**다.
다른 사용자 프로세스 신호, killall, 광범위 pkill, GPU0/1/2 fallback은 없었다.

전체 epoch1245.664초/2206표본의 aggregate VRAM 증가 최대 **19,946MiB**,
최소 free **16,428MiB**, 안전 floor7,275MiB였다. 이는 process별 peak나 완전한 메모리 격리가 아니다.
종료 후5회 모두 **free36,373MiB/used3,965MiB/util0%**로 시작 전 수준에 복귀했다.
Private PostgreSQL은 유지했고 환경·driver·CUDA 설치 변경은 없었다.

## 검산과 후속 판단

독립 검산의 최초 호출은 응답 행을 읽기 전에 timeout 숫자 타입 검사에서 멈췄다.
Freeze의 int120과 실제 argparse/manifest의 float120.0은 같은 설정 값이다.
원본 helper/FAIL 기록/freeze/manifest/results를 유지하고 timeout 한 항목의 유한 숫자 비교만
수정한 별도 v4를 사용했다. Bool·비유한값·다른 값은 거절하고 원래 v3의 freeze/hash도 계속 확인한다.
새3개 합성 검사 PASS, 채점·증거 검증 함수는 변경하지 않았다. V4가 실행 전 동결본이 아님을 명시했다.

그 뒤 **이번125행의 첫 전체 독립 재생 PASS**로 모든 저장 단계와 집계가 원본에 일치했다.
보존되지 않은 응답·raw 미관측0, 실제 모델/GPU/네트워크 호출0이다.
이 accounting PASS와 **품질 gate FAIL**을 구분한다.
Replay SHA `bfd67e3c0fe86affb17e42d0b1a19b4222d96b9dbe0ca14abda4795e04b8b6b3`,
실제 v4 helper SHA `177bc501c5be5bb9e240414ec49216b99d8621d9306250eb1446b73dc05dca3f`.
[독립 검토](../reviews/phase5x_native_exaone45_exposed_review.md)와
[원본 보관본](../../evaluations/results/phase5x/exposed-native-exaone45-diagnostic/README.md)에
첫 metadata 실패, 별도 수정, 실제 재생 결과와 고정 source snapshot을 함께 보존한다.

Production source는 기존408개 실제 PostgreSQL/IfcOpenShell/headless 회귀 PASS와 동일하다.
회귀 suite, 이전 Qwen/Gemma125개 진단·재생, 완료된 runtime/resource 검사를 반복하지 않았다.
비필수 runtime tuning과 generation schema의 reason 길이 표현 개선은 future optimization/contract hardening이다.
후자는 이번 후보의 의미 정확도 실패를 해결하거나 반복 평가를 정당화하지 않는다.
RTX5090은 PREDICTED_UNVERIFIED이며 내부 비상업 연구 결과를 상업 배포 허가나 품질 보증으로 확대하지 않는다.
