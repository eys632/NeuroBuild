# Gemma4-12B 첫 단회 품질 진단

Gemma4-12B QAT의 **첫 품질 gate는 FAIL**이다. Schema120/120이지만 semantic112/120(93.33%)가
기준114/120에 못 미쳤고 raw READY FP3/58 및 unsafe accepted READY1/120이 있었다.
동일 후보 반복·V2·미사용80 접근 없이 own 모델 서버를 종료했다. Gemma12 미채택·Phase6 미시작이다.

Clean/pushed302edf1d4d7927ab502cec1971f41d64f4c9cc54에서
run`20260920T155657Z-430e9203623a477eb655af9521bec051`의120×1+warmup5를 완료했다.
CLI exit0/stderr0, resultsSHA43d3fcd24d4606d8a7f3145ce8b350eb45e7af0a0acbb4dd7d4feb5a8e353d2c.
Parser118/120, acceptedFP1/58, FN0/62, raw관측120/120, warmup5/5다.
평균 **2.577928829초**, p95 **2.946839637초**이며 UNGROUNDED_REQUIREMENT1/INVALID_MODEL_OUTPUT1,
timeout/truncation0이다. 모든READY gold62건은 의미 rubric에 맞았지만 non-READY 안전 오류가 남았다.

저장 의미 오류8건은 조회→UNSUPPORTED3(HD-H01/HH-H03/HH-H05), 방화문 READY1(HH-C07),
분수 표현 rawREADY 후 grounding 거절1(HH-B07), 올바른 거절 후 대상 누락2(HH-G07/HH-I04),
이동 취소 rawREADY 후 잘못된 출력 거절1(HH-I07)이다. 방화문은dx+0.20m MOVE_FURNITURE로 수용됐다.
나머지 rawFP2개가 downstream에서 차단돼도 rawFP 지표에서 제거하지 않는다. 실제 IFC 실행은 없다.
자세한 원본 보존 분석은 [failure_analysis.json](../../evaluations/results/phase5x/exposed-native-gemma12-diagnostic/failure_analysis.json)에 있다.

## 실행 계약

공식 Google12B QAT29d097773436b69ff9feafd636ab4cf873786537,
GGUF93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b,
alias`neurobuild-gemma4-12b-qat-q4-0`, profile`gemma4_nonthinking_llama_cpp`다.
기존 노출120개를 한 번씩, warmup5개를 별도로 실행한다. Single pipeline/contract2.0,
promptv2_v2/branch schema/출력768/context4096/concurrency1/timeout120초다.
HTTP sampling은T1/P.95/K64/minP0/repeat1/window0/seed42, thinkingfalse다.
Suppression258883/258882는 원본 모델 동작이며31B와 전체 sampling이 같다고 표시하지 않는다.

Gate는 schema120/120, semantic≥114/120, rawREADY FP0/58, unsafe acceptedREADY0/120이다.
Unknown raw decision은 분모를 줄이거나 안전한 non-READY로 처리하지 않는다.
응답 repair/retry/fallback과3회 전체 반복은 없다. 명백한 FAIL이면 같은 후보 추가 반복과V2를 실행하지 않는다.
PASS/경계선이면 미확정 사실을 검토해 최소 재현성 확인만 판단한다. V2는1차 품질 gate PASS 후에만 가능하다.
Synthetic gold는AUTO-GENERATED / NOT HUMAN VERIFIED, 현재120개는EXPOSED다.

## 최초 runtime 실측

CPU checkpointfa3d337871f2d8078a6145b3a3632a0ddeab7ce6을 push한 뒤 최초 기동했다.
Guard3697642/start480286400, child3697702/start480288365,
guard timestamp2026-09-20T15:48:00.053772+00:00다.
PhysicalGPU3/logical0/TP1/loopback127.0.0.1:8003/nativef072/SM80-cu118,
batch64/ubatch64/F16KV/flashOFF/graphsOFF를 유지한다.

직전5표본 free36373MiB/used3965MiB/util0으로 margin7275MiB와
운영예산28672MiB가 가용29098MiB 안에 들어갔다. 다른 사용자의 프로세스는 변경하지 않았다.
Startup GET3 PASS(HTTP generation0; native startup warmup은 켜짐), 공개 요청1건 PASS **2.601869003초**다.
긴 문맥3328입력+768출력, cached4095, 의도한limit/truncated 경계1건 PASS **13.969568458초**다.
Resource 시점까지 aggregate 증가 peak **7724MiB**, 최소 free **28650MiB**, floor7275MiB다.
이 값은 epoch 누적 관측이며 process별 peak나 hard isolation, 품질 평가 완료치가 아니다.

Startup9949a39bb15dff4aa3d195f72f354b2055fb92407ab0a19b040f0f4842993213,
public042ed74b7c23ebcd084c36579fd39f4e5ca0680960a2b49da7d45f2e8b2d5e5f,
resourceb2edfb4c0fc73615a456b97547690b75138f01310a042fb8141767d3388666c5.
7개 새 runtime receipt의 모델/config/PID/startticks/guard timestamp가 같은 epoch를 가리킨다.
기존31B CPU public30/vocab20/context200은 정확 입력 동등성에 의한 승계cb2370d7…이며 재실행하지 않았다.
기존 startup/resource 검사는 반복하지 않았다.

## 검증과 한계

새 CPU 승계 소비자 경계4개를 한 번 검사해 PASS했다. Activation 변경 후 소비자의 실행 AST와
기존 collector 함수는 같으므로 다시 검사하지 않았다. 생산 코드가 기존418회귀 PASS와 같아 suite도 재실행하지 않았다.
실제 품질 응답을 보기 전에 freezer와 독립 offline replay 정의를 고정하고 같은 source를 보관한다.
학습 계열·공식 benchmark·작은 모델 크기·공개1건 성공을 한국어 의미/안전 gate의 대용으로 쓰지 않는다.
U+2581 한계와 unpublished conversion provenance, RTX5090 predicted/unverified는 유지한다.
예산 하향·batch/flash/graphs/throughput 등 비필수 runtime 최적화는 future optimization이다.

Freeze `3d8ef116b569d660926c42b8f84834bed61c1fa5494122ae9181b0ec818d959c`는
현재 source·노출 입력·과거 길이 입력 SHA·CPU 승계·7개 runtime·회귀 근거·freezer/replay 정의67개를 묶는다.
Freezer를 한 번 실행해 당시 FROZEN_NOT_EVALUATED를 기록했다. Offline replay 핵심3함수는 기존과 AST가 같다.
평가 직전 clean/pushed commit과 own epoch의 남은6710.309초를 확인한 뒤 이번 새 응답만 재검산했다.

## 완료 재검산과 종료

동결 replay와30개 Git blob source snapshot으로 **새125행을 한 번만** 재생해 모든 저장 판정·집계가 일치했다.
Snapshot70796723f66fb967c1cf9d687ad22910faf852b91e19b134c42805081824c62e,
replaya080e21f9c771ad4c7c768323cf496cdd6a99ab38571e8ddee0fe85a2ac7e99b.
67개 frozen 파일과 원본 결과는 전후 동일하다. Accounting PASS는 품질FAIL을 변경하지 않는다.

평가 직후 own guard3697642/start480286400의 UID/argv/exe/cwd와 child3697702/start480288365의
부모·epoch를 확인해 guard pidfd에만 SIGTERM을 보냈다. Guard 자체 TERM/잔여KILL 정리 뒤
STOPPED/STOP_REQUESTED/child exit0/reaped를 확인했다. 다른 사용자의 프로세스에는 접근·신호하지 않았다.
Epoch전체862.954초/1553표본에서 aggregatepeak7724MiB/minfree28650MiB, floor7275MiB였다.
종료 후5표본 모두 free36373MiB/used3965MiB/util0으로 반환됐다. GPU0/1/2 fallback은 없다.
Finalguard44ebe0f38b7ac554a3dbfa7092e6d24b5f74008275025ced88815e1b12f99929,
poststopb7ebb2ab0c2dd5e9d311dc18a0e04e44f23813e7ee79d1160c79afdd7db2d9b1.

Production·대응 tests는 이전418회귀 PASS source와 동일하며 결과 보존 변경에 같은 suite를 반복하지 않았다.
기존 완료 평가·runtime·public/vocab/context 검사도 반복하지 않았다. 다음 후보는 새 가설·정보가치·비용을
등록한 뒤 비교하며, 현재 실패를 runtime 최적화나 반복 평가로 희석하지 않는다.
[원본 archive](../../evaluations/results/phase5x/exposed-native-gemma12-diagnostic/README.md),
[독립 검토](../reviews/phase5x_native_gemma12_exposed_review.md).
