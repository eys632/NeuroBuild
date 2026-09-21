# Phase5.x V7 thinking 진단 독립 검토

검토일: 2026-09-20 KST. **평가 판정 FAIL, 보존 증거와 CPU 재계산의 일치 PASS.**
V7은 40개 development case 중 semantic 30/40이며 모델 선정 근거가 되지 않는다.
이 검토는 새 모델 요청, GPU 조회, 프로세스 signal, 설치 또는 heldout 출력 열람을
수행하지 않았다. 합성 gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다.

## 대상과 재계산

대상은 run `20260919T220158Z-72efdc2dad274cb98b1d61b669597b75`의
[manifest](../../evaluations/results/phase5x/development-v7-thinking-diagnostic/manifest.json)와
[results](../../evaluations/results/phase5x/development-v7-thinking-diagnostic/results.json)다.
두 보존 파일은 원래 `var/runs/` 파일과 byte 단위로 일치했다.

Frozen Git `6a3275da978070f69c499201839c32701c153eb1`의 dataset, V7 prompt,
schema, parser, scorer, client SHA-256은 manifest와 모두 일치했다. 현재 dataset,
prompt, schema, parser, scorer도 해당 hash와 같다. 현재 client는 후속 neutral
sampling profile 추가 때문에 hash가 다르므로, 보존 결과를 새 client의 실제 추론
증거로 취급하지 않는다. 후속 client 변경은 아래에서 별도로 읽기 검토했다.

원래 dataset의 case order와 UUID 생성 규칙을 사용해 40개 trial과 5개 warmup을
현재 JSON Schema validator 및 `parse_requirement`로 재검증했다. 각 출력의 schema
판정, parser error, SI 정규화 operation 및 `score_output`의 모든 필드가 저장값과
일치했다. `summarize(results["trials"])`도 저장된 metrics dictionary와 정확히
일치했다. 이는 저장된 최종 출력에 대한 CPU replay이며 모델 추론 재실행은 아니다.

실행 설정은 Qwen/Qwen3-14B-AWQ revision
`31c69efc29464b6bb0aee1398b5a7b50a99340c3`, alias `neurobuild-thinking`, A100 GPU3,
vLLM `0.8.5+cu118`, AWQ Marlin/float16, TP1, context4096이다. V7 prompt와
`qwen3_thinking_awq` recipe(T0.6, top_p0.95, top_k20, min_p0, presence1.5,
frequency0, repetition1, seed42), thinking=true, `deepseek_r1` parser,
`legacy_guided_json`/`xgrammar:no-fallback`, max_tokens1280, timeout120s,
concurrency1을 사용했다. Development 40개를 각 1회 평가했고 warmup5는 점수에서
제외했다. 같은 고정 seed의 단일 trial은 반복 안정성 검증이 아니다.

## 결과와 실패 원인

| 항목 | 재계산 결과 |
|---|---:|
| JSON / schema | 각각 40/40 |
| Parser 수락 | 35/40 |
| Semantic 일치 | 30/40 (75%) |
| Non-ready gold에서 raw / accepted READY FP | 각각 0/20 |
| READY gold에서 accepted READY FN | 8/20 |
| 부정확한 accepted move / 전체 unsafe accepted READY | 각각 0/20, 0/40 |
| 대상 보존 | 29/40 target slot |
| 단위·값 추출 | 24/40 axis slot |

Slot 지표의 분모는 case 수와 다르다. Target 보존은 대상 slot 40개이며, 단위·값은
READY gold 20개의 X/Y slot 40개다. 모든 12개 accepted READY는 rubric과 일치했지만
불필요한 거절과 오분류 때문에 전체 semantic gate는 실패했다.

실패 10개는 다음과 같이 분리된다.

| 종류 | Case | 관측 내용 |
|---|---|---|
| 원문 수치·단위 변경으로 parser 거절 (5) | HD-A01, HD-A02 | 원문 125mm를 0.125m / -0.125m로 바꿔 `UNGROUNDED_REQUIREMENT` |
| 위와 동일 | HD-B02 | 원문 `1m`를 값 문자열 `1.0`/m로 바꿔 lexical grounding 실패 |
| 위와 동일 | HD-F01, HD-F02 | 원문 16cm를 -0.16m로 변경하고 대상의 장소·제외 수식어도 누락 |
| 불필요한 clarification (3) | F01, HD-I01 | 명시되지 않은 충돌·존재 확인 조건을 요구하여 READY 지시를 거절 |
| 위와 동일 | F02 | 단일 대상 확인을 추가 요구하고 제외 대상을 표현한 수식어도 누락 |
| Non-ready 세부 분류 오류 (2) | H02, HD-H01 | 목록 조회를 gold CLARIFICATION 대신 UNSUPPORTED로 분류 |

앞의 5개 parser 거절과 3개 clarification이 READY FN 8개를 구성한다. 마지막
2개는 operation이 없는 안전한 거절이지만 고정된 분류 rubric에는 불일치한다.
SI 물리량이 같더라도 원문 value/unit 보존 계약을 완화하거나 gold를 변경해 성공으로
재분류하면 안 된다. 다섯 오류는 모두 grounding 오류이며 transport timeout이나
출력 잘림은 기록되지 않았다.

전체 end-to-end 지연 평균은 14.559s, p95는 28.664s다. 기록된 completion token 합은
20,071개이며 가장 긴 응답은 1,241개다. Token/전체응답시간 값은 decode-only 처리량이
아니고 reasoning과 final content의 token 분리가 제공되지 않았다. TTFT, decode-only
처리량, cold/warm 시작 시간, per-process GPU peak와 tool 실행 성공은 측정하지 않았다.
0/20 FP의 Wilson 95% 상한은 약 16.1%이며, 작은 합성·상관 표본의 기술 통계이므로
실사용 오류율이 0임을 뜻하지 않는다. 이 V7 실패는 이전 thinking 실험의 실패 증거를
대체하거나 삭제하지 않으며, 두 실험을 모델 선정 PASS로 표시할 근거가 없다.

## 종료 보존과 관측 한계

Root가 이미 종료 요청한 live report가 STOPPED인 것을 파일로 확인하고
[shutdown_thinking_epoch1.json](../../evaluations/results/phase5x/shutdown_thinking_epoch1.json)에
원본 byte를 exclusive-create 방식으로 보존했다. SHA-256:
`f4df71aa58a95b866ff4fbbc9d7e71fa837219469d04a771dbd3a074fc31a38e`.

기록은 `STOP_REQUESTED`, child PID3389724 exit0, `child_reaped=true`,
FileStore cleanup=true, elapsed1754.412s다. 이 server epoch는 V6와 V7을 포함하므로
baseline 대비 aggregate GPU 사용 증가의 관측 최댓값 12,064MiB 및 최소 free24,310MiB를
V7 전용 값이나 모델 단독 peak로 부를 수 없다. STOPPED 보고서는 종료 절차 기록이며,
이 검토자가 종료 후 VRAM 반환을 새로 측정했다는 뜻도 아니다.

Runtime identity는 manifest의 operator-supplied 기록이다. HTTP alias 확인만으로
서버가 실제 읽은 weight revision을 독립 attestation하지 않는다. 보존된 source hash와
명시 launch 설정은 재현 근거이며, 이후 서버를 시작할 때는 새 preflight가 필요하다.
RTX5090의 실행·정확도·메모리 적합성은 이 A100 결과로 검증되지 않았다.

## 후속 neutral profile 읽기 검토

`local_model.py`의 `QWEN3_NONTHINKING="qwen3_nonthinking"` 추가를 별도로 읽었다.
명시 recipe는 T0.7/top_p0.8/top_k20/min_p0/presence0/frequency0/repetition1/seed42이며
thinking=false다. Legacy 기본값 및 기존 두 AWQ recipe는 변경되지 않았고 모델명으로
profile을 선택하거나 오류 후 다른 설정으로 retry하는 경로가 없다. 정확한 enum/string
입력만 허용하며 반환하는 sampling metadata는 새 dict다. 새 테스트는 두 protocol,
enum/string, unknown 값, 모델명 비연동 및 HTTP400의 단일 요청을 다룬다.

읽기 검토에서 추가 중대 blocker는 발견하지 못했다. Client30 tests PASS는 구현
담당자의 실행 증거이며 본 검토자는 해당 HTTP 테스트나 새 모델 요청을 재실행하지
않았다. 이 변경의 코드 적합성과 후속 후보의 실제 정확도는 별도 판정 대상이다.
