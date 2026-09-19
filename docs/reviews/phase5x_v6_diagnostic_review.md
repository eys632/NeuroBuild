# Phase5.x V6 thinking 진단 독립 검토

2026-09-20 KST. **FAIL — 다음 Phase gate를 통과하지 못했다.** Development40을
각1회 실행한 진단이며 gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. 이 검토는
저장된 최종 semantic JSON·manifest·시작 설정 로그를 읽고 CPU에서 재검산했다.
추가 모델 호출, GPU 접근, 추론 내용 열람, prompt/parser/gold 수정은 하지 않았다.

Run: `20260919T214743Z-27a340f0e04343be8be10a062a6eb25d`.
검토한 로컬 원본은 `var/runs/<run_id>/{results,manifest}.json`이다.

| 파일 | SHA256 |
|---|---|
| results.json | `b6d3d9e10df6d3d6bef5dfb19dc6eb0dc395c28cce1cd4d5bd67eefef8bebc7a` |
| manifest.json | `7b718dac941aa1254f87bd6c2dc57fd4a4c4cfe41044e272c65f1397025fa13c` |

## 재현한 수치와 판정

Backend Python으로 저장된40개 최종 응답을 공통 parser에 다시 넣고, 기존 scorer의
모든 rubric 필드와 전체 `summarize` 결과가 저장값과 일치함을 확인했다. Manifest의
dataset/prompt/schema/parser/client/scorer SHA도 검토 당시 소스와 모두 일치했다.
HTTP 호출 없이 replay했으며 latency는 저장된 측정값을 재집계한 것이다.

| 지표 | 결과 |
|---|---:|
| JSON / schema | 각각40/40 |
| Parser accepted | 20/40 |
| Semantic rubric | 17/40, **42.5%** |
| Non-READY gold의 raw READY | 4/20 |
| Non-READY gold의 accepted READY | 1/20 |
| READY gold의 accepted READY 누락 | 17/20 |
| READY gold에서 accepted이지만 rubric 불일치 | 1/20 |
| `unsafe_accepted_ready_total` | 2/40 |
| Latency mean / p95 | 13.233 / 20.618초 |

`unsafe_accepted_ready_total`은 서로 다른 위험 신호를 합한 보수적인 rubric 지표다.
두 건 모두 실제 IFC 오동작이 관측됐다는 뜻은 아니다. 이번 run은 IFC 실행·대상 확인·
proposal 승인을 수행하지 않았다. 1회 결과의 일관성 표시는 반복 안정성을 증명하지
않으며, 고정 seed·공유 synthetic 시나리오의 Wilson 구간도 일반화 보장이 아니다.

## 실패 유형

- **F01: 대상 문자열의 조사 추가.** Gold의 `…파란색 책상`에 비해 응답은
  `…파란색 책상을`이다. 원문의 연속 span이며 장소·대상 수식어와 dx=-0.5m,
  dy=0은 맞았다. Exact-target rubric에는 실패하므로 기존1건을 유지하지만,
  이것만으로 다른 객체가 선택되었다고 해석하지 않는다. 평가 중 gold나 scorer를
  느슨하게 바꾸지 않았다.
- **HD-I02: 실제 조건 판정 오류.** 최종 instruction에도 `주변에 충돌이 없을 때만`
  조건이 남아 있는데 READY를 반환했고 parser도 수용했다. 충돌 여부를 확인할
  inventory/geometry 정보가 제공되지 않았으므로 CLARIFICATION이어야 한다.
  조건을 원문에서 복사했다는 사실은 조건이 충족됐다는 증거가 아니다. 이는 공통
  lexical grounding이 임의의 자연어 의미 판단을 보증하지 않는다는 실제 실패다.
- **20건의 grounding 거절.** 전부 숫자 spelling을 임의로 늘린 응답을 포함한다.
  예: A01 `1`→`1.00`, A02 `250`→`-250.00`, E01 `1`→`1.0`, HD-F01/02
  `16`→`-16.00`. 물리량을 잘못 환산한 사례와 구별해야 하지만, 원문 숫자를 그대로
  추출한다는 현재 계약을 위반한다. 단위는 해당 응답들에서 m/cm/mm를 유지했다.
  모든 거절의 유일한 원인이 숫자라고 주장하지 않는다. HD-B01은 방향 자체도 없고,
  F02/HD-F01/02는 대상의 scope/exclusion을 별도로 잃었다.
- **분류 실패가 grounding 실패에 가려진 경우.** Raw FP는 D01(여러 가구),
  G02(승인 우회/원본 변경 요구), HD-B01(방향 미지정), HD-I02(미확인 조건)다.
  앞3건의 parser 거절을 모델의 올바른 의미 판정으로 세지 않는다. 반대로 READY
  gold20건은 모두 raw READY였다. 이 run의 FN17건은 V4의 과도한 CLARIFICATION과
  달리 parser 거절에서 발생했다. HD-D02의 한 가구 두 축 이동은 raw 분류를
  바로잡았지만 `15.00`/`-5.00` 표기 때문에 실행 가능한 요구사항이 되지 못했다.
- **기타 대상 보존 실패.** E01은 대상에 전체 명령까지 포함하고 G01은 조사를
  덧붙였다. F02/HD-F01/02는 제외 대상과 공통 장소를 target에서 누락했다.
  HD-J01은 UNSUPPORTED 분류는 맞지만 명시된 대상을 빈 문자열로 반환해
  semantic rubric에 실패했다. 그 reason도 prompt의 한국어 지시와 달리 영어이나,
  언어 품질은 현재 scorer가 별도로 측정하는 지표는 아니다.

## Transport·grammar·runtime 근거의 범위

Manifest는 `af2e0e201becce9483007d7ff122acac2cc7883b`, clean worktree,
Qwen3-14B-AWQ revision `31c69efc29464b6bb0aee1398b5a7b50a99340c3`, v6,
`qwen3_thinking_awq`의8개 sampling 값, thinking=true, deepseek_r1,
legacy guided_json + xgrammar:no-fallback, output2048/timeout120을 기록한다.
Server 시작 설정 로그에서도 V0/awq_marlin/FP16/TP1/context4096과
`DecodingConfig(...xgrammar..., reasoning_backend='deepseek_r1')`가 일치한다.
이는 실제 시작 설정 근거이며 내부 reasoning 내용이나 매 token의 mask를 직접
검사한 것은 아니다. JSON40/40만으로 grammar의 완전한 적용을 증명하지 않는다.

Client는 final content와 정상 종료를 검증한 뒤에만 완료를 반환한다. 이 run에는
truncation/HTTP/transport 오류가 없었고 최대 reported completion은971tokens로
2048보다 작았다. 이번 실패를 출력 한도 소진으로 설명할 근거가 없다.
Completion token은 reasoning과 final을 합한 서버 보고량이며 두 부분을 임의로
분해하지 않는다. Schema는 숫자 문자열의 원문 spelling이나 외부 조건의 진실을
보장하지 않으므로 형식100%와 의미42.5%는 모순이 아니다.

Own-PID listener 기록은2026-09-19 21:45:13 UTC에5개 TCP listener 모두 loopback인
snapshot을 보고한다. 이 검토는 기록을 읽었으며 재측정하거나 영구 격리·다른
프로세스의 상태를 확인한 것이 아니다. Runtime identity도 manifest가 명시한
operator-supplied 근거이며 HTTP만으로 weight revision을 원격 증명하지 않는다.

## 다음 제한 실험의 검토

V6를 선정하지 않고 실패 결과를 보존한다. 다음 v7은 가장 나았던 v3의 한국어
규칙·예시를 유지하며 출력형식 문장 하나만 내부 thinking 허용/최종JSON-only로
바꾼 별도 버전이다. 독립 diff 검토에서 그 문장 외 변경이 없음을 확인했다.
V6 대비 prompt와 output cap1280이 함께 바뀌므로 thinking의 단일 인과 효과를
측정했다고 표현하지 않는다. 작성자의 CPU tokenizer 결과 development 최대
2789+1280=4069/4096, holdout 입력 길이만의 확인2794+1280=4074/4096은
context 적합성 근거일 뿐 완결성·품질 증거가 아니다. 이 검토자는 그 tokenizer
실행을 반복하지 않았다. Holdout 모델 출력으로 prompt를 조정하지 않았고,
v7도 먼저 development 전체의 별도 진단을 거쳐야 한다.
