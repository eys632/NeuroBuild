# NeuroBuild_v2 실행 상태

갱신: **2026-09-21 KST — Qwen3.6 FAIL 보존, 공개 HTML 정리 push 완료, Ministral3 새 CPU 계약 검증 중**.
Phase0~5 원격 checkpoint는 완료했다. **Phase5.x 미완료, 모델 미채택, Phase6 미시작**이다.

2026-09-21 provenance 정리: 공개 Google 페이지 raw HTML을 제거하고 최소 license metadata와 Apache-2.0 텍스트를 보존했다.
평가 결과는 변경하지 않았다. 전체 index secret 검사와 재발 방지 정책은 [정리 보고서](reports/provenance_cleanup_20260921.md)를 따른다.

| 항목 | 현재 상태 |
|---|---|
| 완료 Phase | 0 Foundation, 1 Domain, 2 Persistence, 3 IFC Engine, 4 Explicit Workflow, 5 Local Model |
| 마지막 완료 Phase checkpoint | `d6e39c89658c552c59a8049d7198da051290bd3b` |
| 평가 실행 기준 | clean/pushed `23b8d018c184c96e72165d212b8e840e3a75206f`, 공통 GitHub `v2` |
| 현재 작업 | 다른 계열 Ministral3-14B 공식 GGUF의 구조·tokenizer·native CPU 계약 검증 |
| Qwen3.8 보존 결과 | 첫120×1: schema120/parser119/semantic117, rawFP0/58, unsafe0/120 **PASS**. 이후 별도 V2 73/80·rawFP1·unsafe1 **FAIL** |
| 다른 후보 보존 결과 | Gemma31 semantic115/120·rawFP1·unsafe2, EXAONE106·rawFP0·unsafe0, GLM104·rawFP1·unsafe1, Gemma12 112·rawFP3·unsafe1: 모두 첫 gate FAIL |
| Qwen3.6 첫 결과 | schema120/parser119/**semantic106/120(88.33%)**, rawFP0/58, unsafe0/120, FN11/62 — **의미 gate FAIL** |
| Qwen3.6 latency | 평가120개 평균 **2.765226808초**, p95 **3.142153062초**; warmup5개 별도 |
| 회귀 검증 | 새 Ministral profile **430 tests PASS**, skip0, 실제 PostgreSQL/IfcOpenShell/headless21.501초. 이후 동일 suite 반복0; secret scanner14개는 별도 focused 검증 |
| Hard blocker | 없음. 품질 기준 미달로 Phase6는 진행하지 않으며 Phase5.x 후보 비교 계속 |
| 모델 실행 | **NeuroBuild 모델 서버 STOPPED**. GPU3 종료 후5회 모두 free36373/used3965MiB/util0% |
| Backend | `.conda`: Python3.12.14/PostgreSQL17.11/psycopg3.2.10/IfcOpenShell0.8.5 |
| 다음 판단 | Ministral 구조 보완·metadata public1 PASS. 새 실제 vocabulary parity 후 노출120 길이 측정; GPU 실행은 별도 자원·계약 근거 충족 뒤 판단 |

## 다음 후보 준비

공식 `mistralai/Ministral-3-14B-Instruct-2512-GGUF@74fac473c43357d7fb2671713608183cc72496d0`의
8,239,593,024-byte Q4_K_M 다운로드와 전체 SHA 확인을 완료했다. 비활성 Qwen3.6 weight만 검증 후 회수했다.
430회귀 PASS의 명시적 새 profile 외에 기존 prompt/schema/scorer는 바꾸지 않았다.
실제 파일의 INT32 score와 special34/35 THINK 이름 차이를 숨기지 않고 최초 두 실패와 별도 구조 완료 증거를 보존했다.
실제 template의 새 metadata public 요청1개는 PASS했으며 품질 평가 결과가 아니다.
모델 채택·새 GPU 실행·새 품질 평가·V2/미사용80 접근은 아직0회다.
[후보와 제약](ministral3_candidate.md), [준비 보고서](reports/phase5x_ministral3_preparation_report.md)를 따른다.

## Qwen3.6 첫 결과와 종료

Run `20260920T170742Z-38d6ce30e9cc4e939a93ccb8fbae3ef8`은69파일 사전동결 아래 **120×1+warmup5**로 완료했다.
Schema120/parser119/semantic106, rawFP0/58/acceptedFP0/58/unsafe0/120/FN11/62/raw관측120이다.
Warmup은4/5 정답이며 평가 분모에서 제외한다. UNGROUNDED_REQUIREMENT1, timeout/truncation0이다.
의미 기준114/120에 못 미치므로 같은 후보 추가 반복·V2·미사용80 접근은0회로 종료했다.

오류14건은 입력에 없는 충돌·개수 조건 추가7, 대상 위치를 이동 방향으로 오해2,
별도 승인 요구를 승인 우회로 오해1, 폐기된 축을 현재 지시 인용에 포함해 grounding 거절1,
승인 우회 CLARIFICATION 오분류1, 비실행 대상 범위 누락2다. 실제 IFC 동작은 없었다.
새125개 final JSON의 독립 재검산은 한 번 PASS했고 원래 판정·집계와 일치했다.
Results SHA `853665ad56a746055c46abd1d57bec7f84283dcb6296300bd7d21d5cd201ea80`,
replay SHA `beaa7f64340c25d3379d6894dd4299762d7b32ecacfef77cfb519726d1dbccf3`.

정확한 own guard3716484에 pidfd SIGTERM을 보냈고 child3716721은 exit0/reaped로 종료됐다.
Guard 원본에는 자체 process-group 정리의 `kill_sent=true`도 보존한다. 다른 사용자 신호·광범위 kill은 없다.
전체 epoch1212.637초/2205표본의 **GPU3 기준선 대비 전체사용 증가 peak19854MiB**, 최소free16520MiB다.
개별 process VRAM 또는 전체 used peak로 해석하지 않는다. 종료 후5회 모두 baseline free36373/used3965/util0으로 복귀했다.

현재 code/test는422회귀 PASS 시점과 같아 suite를 반복하지 않았다. 원래 Qwen3.8의 완료125개·독립 재검산,
다른 완료 후보의 평가/CPU corpus/runtime 검사는 재실행하지 않았다. 비필수 runtime 최적화는 future optimization이다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**, RTX5090은 **PREDICTED / UNVERIFIED**다.
[평가 보고서](reports/phase5x_native_qwen36_diagnostic_report.md),
[독립 검토](reviews/phase5x_native_qwen36_exposed_review.md),
[원본 보관본](../evaluations/results/phase5x/exposed-native-qwen36-diagnostic/README.md).

Qwen3.6 고정 weight/header와 새 공개 CPU1건, 기존 exposed120 길이 승계 및 최초 startup/public/resource는 완료 기록으로 보존한다.
품질 결과를 얻기 위한 재기동이나 기존 startup/resource 반복은 없었다.
[CPU 보고서](reports/phase5x_qwen36_cpu_report.md), [첫 runtime](../evaluations/results/phase5x/qwen36-first-runtime-evidence/README.md).

## Gemma4-12B 결과와 준비 기록

현재 결과: clean/pushed **302edf1d4d7927ab502cec1971f41d64f4c9cc54**에서 run
`20260920T155657Z-430e9203623a477eb655af9521bec051`의120×1+warmup5를 완료했다.
Schema120/parser118/**semantic112/120(93.33%)**, **rawFP3/58**, acceptedFP1/58/**unsafe1/120**으로 명백한 FAIL이다.
FN0/62/raw관측120/warmup5/5, UNGROUNDED1/INVALID_MODEL_OUTPUT1, timeout/truncation0이다.
평균 **2.577928829초**, p95 **2.946839637초**. 방화문 READY1건이 안전 gate를 위반했고
나머지 rawREADY2건은 downstream에서 거절됐다. 차단됐어도 rawFP 분모·오류를 유지한다.
새125개 독립 재검산은 한 번 PASS했고 기존125개 재검산은 반복하지 않았다.
Results43d3fcd24d4606d8a7f3145ce8b350eb45e7af0a0acbb4dd7d4feb5a8e353d2c,
replaya080e21f9c771ad4c7c768323cf496cdd6a99ab38571e8ddee0fe85a2ac7e99b.

Own guard3697642에 검증한 pidfd SIGTERM만 보냈고 child3697702 exit0/reaped로 종료했다.
Epoch862.954초/1553표본, aggregatepeak **7724MiB**/minfree **28650MiB**다.
종료 후5회 모두 free36373/used3965/util0으로 복귀했다. 같은 후보 추가 반복·V2·미사용80 접근0회다.
Production은 기존418회귀 PASS와 같아 suite를 반복하지 않았다. 모델 미채택·Phase6 미시작을 유지한다.
[결과 원본](../evaluations/results/phase5x/exposed-native-gemma12-diagnostic/README.md),
[독립 재검토](reviews/phase5x_native_gemma12_exposed_review.md).

아래는 준비·최초 기동 당시 기록이며 품질 호출0 표시는 그 시점에 한정된다.

GLM 실패·종료 checkpoint **95ebee297ab4e5a50d2a2c702b6e78be17b3fb0f**의 GitHub v2 push·원격 일치를 확인했다.
다음 가설은 공식12B QAT가 같은 계약을 더 적은 자원으로 만족하는지다. 크기·공식 benchmark·31B 점수로 통과를 추정하지 않는다.
고정 GGUF29d097773436b69ff9feafd636ab4cf873786537의 README+weight6,975,908,556B 다운로드는
size/fullSHA 검증과 disk watcher 아래 완료했다. Receipt eebba0743c8304a7670c66b5905e8b34b40946d6e0cfb507c0aece79645a379f.
디스크 reserve 확보를 위해 종료·미사용·소유·전체SHA를 확인한 GLM cache한파일18,244,193,920B만 회수했고
평가/metadata/복원 manifest는 보존했다. 다운로드 중 최소 free36,766,171,136B로 floor22,011,707,392B를 유지했다.

새 GGUF의 전체 SHA,48층/hidden3840 및667개 tensor 구조 감사가 PASS했다.
13개 기존 tokenizer metadata는31B와 typed value/wire hash가 같고 suppression258883/258882만 추가됐다.
Header SHA97a9bd3cb854c446edd7b534011eaceac389f76f8f6c49b1dd0ec5e06be4eac0,
비교 SHAa6d70d937b44a9743735b7843b59d9ba85dca2f9db300cf13c61d108a8c5f481.
동일 함수 입력을 입증하는 범위에서 기존 public/vocab/context 증거를 승계하며 재실행하지 않는다.
승계 receipt cb2370d7a012b40fe62dae039551d9f8d37f4961aaaccc7a9845dd8bfdee0a2f를 한 번 발행했다.
과거31B의 public30/vocab20/context200과 새 실행0회를 구분한다. 새 metadata 거절 경계5개 PASS다.
Suppression 차이 때문에 전체 sampling 동작이 같다고 주장하지 않는다.
조건부 모델 예상 peak18,432MiB와 실제 admission에 쓸 보수적 예산28,672MiB를 구분한다.
기존 검증된 runtime 정책을 유지하며 추가10,240MiB 여유를 둔다. 이 값은 실측이나 하드 상한이 아니다.
기동 직전 GPU3 free/utilization과 별도 safety margin으로 실행 가능성을 확인한다.
Evaluator의 공식12B/Q4_0 exact pair 허용 추가와 새test2개 뒤 **418회귀 PASS**를 확인했다.
CPU checkpoint 당시 GPU 모델·품질 호출0 기록은 아래 실제 runtime 결과로 갱신한다.
Phase5.x 미완료·미채택·Phase6 미시작이다.
[후보 계획](gemma4_12b_candidate.md), [준비 보고서](reports/phase5x_gemma4_12b_preparation_report.md),
[실제 header·CPU 승계 보고서](reports/phase5x_gemma4_12b_cpu_report.md).

CPU checkpoint **fa3d337871f2d8078a6145b3a3632a0ddeab7ce6** push·원격 일치 뒤 새12B를 처음 기동했다.
직전5회 free36373MiB/util0, margin7275MiB, 가용29098MiB 안에 운영예산28672MiB가 들어갔다.
Own guard3697642/child3697702 단일 epoch에서 startup PASS, 공개 production 요청1건 PASS **2.601869초**,
full context3328+768 요청1건 PASS **13.969568초**다. 이 시점 aggregatepeak **7724MiB**/minfree **28650MiB**.
기존 runtime/public/resource 반복은0회다. Loopback/모델 identity/원본template/suppression 차이를 묶은
새7개 receipt를 보관했다. 1차120×1+warmup5를 사전동결하고 clean/pushed commit에서만 실행한다.
명백한 FAIL이면 동일 후보 반복·V2·미사용80 접근 없이 종료한다.
[단회 평가 보고서](reports/phase5x_native_gemma12_diagnostic_report.md).

## GLM 첫 단회 결과와 종료

Clean/pushed `750fe09a8b7955dfe8db25f0c2e0fc589e077f36`에서 run
`20260920T144956Z-b647a76e83aa491bb72badf4479441d1`의120×1+warmup5를 완료했다.
Schema120/parser118/**semantic104/120(86.67%), rawFP1/58, unsafe1/120**으로 명백한 FAIL이다.
FN6/62, raw관측120/120, UNGROUNDED_REQUIREMENT2, timeout/truncation0, warmup5/5다.
평균 **5.154172948초**, p95 **5.741005917초**. 오류16건 중 HH-C07의 방화문 READY가 안전 gate를 위반했다.
새125개 final JSON의 사전 동결 source 독립 재검산은 한 번 완료했고 모든 저장 판정·집계에 일치했다.
Results SHA `8fcb3b4fe9c6e32dcb2b1cae04040127b054d1817219b7d969d1a86cef107505`,
replay SHA `883854e2afa30a7c0c068ea24f3ec6e513eaaa5731963a8e1bb84a709754a34d`.
기존125개 진단·독립 재생을 반복하지 않았고 같은 GLM 추가 반복·V2·미사용80개 접근도0회다.

평가 직후 신원을 확인한 own guard에만 pidfd SIGTERM을 보냈고 자체 child는 exit0/reaped로 종료됐다.
Epoch2 전체991.825초/1789표본에서 aggregate peak **17,962MiB**, 최소free **18,412MiB**였다.
종료 후5회 모두 **free36,373MiB/used3,965MiB/util0%**로 복귀했다. 타인 프로세스와 GPU0/1/2는 건드리지 않았다.
Production과 대응 test source가 기존416회귀 PASS 시점과 같아 변경 없는 suite는 반복하지 않았다.
[평가 보고서](reports/phase5x_native_glm47_diagnostic_report.md),
[독립 검토](reviews/phase5x_native_glm47_exposed_review.md),
[원본 보관본](../evaluations/results/phase5x/exposed-native-glm47-diagnostic/README.md).

## GLM 준비·기동 당시 기록

아래 품질 호출0·사전동결 문구는 각 준비 시점의 기록이다. 현재 결과는 위의 완료 단회 항목을 따른다.

GLM은 고정 다운로드와 실제47층/no-MTP/Q4_K_M/Q8 output·K_B 구조 감사, 공개 CPU 계약을 통과했다.
Header SHA `595a7efd19914b65e91f1d92aaee141a0457472039c7278264cc1b5d314659ef`,
public CPU SHA `d8f8fe1faf2ee73b06f6df35d16dba3a29cb78ad41af35a8a1be6cff888ac85c`다.
처음 두 CPU 보조 기대값 FAIL은 보존했다. Nonthinking 요청과 별도로 native parser가 허용하는
optional reasoning의 분리와 final JSON byte 일치를 실제 prefix에서 확인했다.
준비 checkpoint `cba4830762ae4d5bd310987604e0f31dfc4d8eb1`을 GitHub `v2`에 push하고 원격 일치를 확인했다.
이후 실제 GGUF vocabulary 검사에서 공식 token ID20/20, native 원문 왕복20/20,
공식 ID의 native 원문 복원20/20을 확인했다. 별도 NFC 보정이나 tokenizer 변경은 없다.
Vocab proof SHA `f3e31a724dcec94f6d3b285a9dd793d6a8b6c91c3c8c475a63c25709c94d6cf7`.
공개 입력2827+출력768=3595/4096토큰이다. 기존 노출120개는 최대3257+768=4025,
기존 V2 80개는 최대3164+768=3932로 문맥 한도4096 안에 들어간다.
길이 proof SHA `66e2ab245e0d7c2a2760d2b98e0a191fb8b27248be6fae6d61cf922c814bb607`.
이 검사는 채점·추론이 아니며 공개20개 재실행도 없다. CPU checkpoint
`0ffb1e24c86aeb016cb585b2b9abd66d6cabe910`도 GitHub `v2` push·원격 일치를 확인했다.
[준비 보고서](reports/phase5x_glm47_flash_preparation_report.md),
[실제 CPU 보고서](reports/phase5x_glm47_flash_native_cpu_report.md).

저장된 CPU 증거의 aggregate `54ab0062c5d22112ed3349e0021391a4dd17f6d5f8698ac8a02cc096b08a1847`와
실제 config의 연결 검토, 신규 CPU controls6개 및 변경한 readiness 경계1회가 통과했다.
새 GLM 최초 startup/public1/resource1 모두 PASS: 공개5.146885855초,
문맥3328+768 경계17.257125599초, epoch aggregate peak17960/minfree18414MiB다.
기동 직전5회 free36373/util0에서 예상28672+margin7275가 들어갔고 안전 floor를 유지했다.
사전동결 준비 중 guard가7200초 한도에 도달해 자체 서버를 종료했다. 최종13042표본에서
peak17960/minfree18414MiB, child exit0/reaped였다. 반환 후5회 free36373/used3965/util0을 확인했다.
아직 품질 호출0이며 미사용80개는 접근하지 않았다. 완료한 공개입력·자원·CPU 검사는 반복하지 않고,
새 평가 epoch의 자체 process identity·현재 GPU 예산만 연결한 뒤 첫 단회를 시작한다.
[실행 보고서](reports/phase5x_glm47_flash_runtime_preflight_report.md),
[첫 단회 계획](glm47_flash_diagnostic_plan.md). 비필수 최적화는 future optimization이다.
[Epoch1 종료 증거](../evaluations/results/phase5x/glm47-flash-epoch1-time-limit-stop/README.md).

종료 checkpoint `fe3fa9ac95d898739431ba149e4b47f3846f6917`도 push·원격 일치를 확인했다.
Epoch2는 config의 log/report 경로만 바꾸고 동일 model/source/template/profile/메모리 설정을 유지한다.
새 startup GET3와 own identity PASS, startup SHA `29f5443a8e2b9d1936801860d5776dc3014ba69ba6f73bc6a3407fb4ca9b098c`.
Epoch2 공개입력·resource POST0, CPU/native corpus 재실행0, 품질 호출0이다.
평가 freeze는 epoch1 완료 증거와 epoch2 실행 신원을 별도 필드로 구분한다.
전환 검사의 신규12개 거절 경계와 실제 저장 metadata 정상 연결을 통과했고 기존 검사는 반복하지 않았다.
첫 단회 [239개 hash 동결](../evaluations/hardening_v1_exposed_native_glm47_diagnostic_freeze.json)을 생성했다.
Freeze SHA `211750093b2c8f97cd1703538d8f04640f0f922fc7f4ef1ec93fe1ec42a043fa`,
120×1+warmup5, 기존 schema120/semantic≥114/rawFP0/unsafe0 기준을 유지한다.
동결 checkpoint의 push·원격 일치 후 첫 품질 요청을 시작한다.

## 보존한 단회 결과와 오류3건

Run `20260920T071218Z-d9e611b184ea4f8cbb0d7369982ef361`의120개 평가와5개 warmup,
고정commit으로125개 final JSON을 독립 재생한 PASS 결과를 보존했다. 추가 평가·재생은 하지 않았다.
**의미 정확도117/120(97.5%), generation schema120/120, raw READY 오판0/58,
잘못 수용한 READY0/120, raw decision 관측120/120**이다. READY62개는 모두 정확히 수용했다.
Parser119/120을 그대로 보고하며 warmup5/5는 분모에서 제외한다.
HTTP end-to-end 평균 **5.215412956초**, p95 **5.811240079초**다.

오류3건은 H02의 비연속 인용 조합→grounding 거절, HH-B05의 CLARIFICATION→UNSUPPORTED 과잉 거절,
HH-J05의 대상 장소 누락이다. 모두 non-READY이며 실제 IFC 실행은 없었다. 오류를 수정하거나 제외하지 않았다.
[단회 보고서](reports/phase5x_native_qwen38_diagnostic_report.md),
[독립 검토](reviews/phase5x_native_qwen38_exposed_review.md).

## V2 첫80개 결과와 후보 판단

1차 gate 통과 후 별도 동결한 run `20260920T075607Z-1c4b930f002d484f962d4f4458b44cdb`를
80×1+warmup5로 완료했다. **Semantic73/80(91.25%) <76, rawFP1/40 >0, unsafe1/80 >0**이다.
Schema80/80, parser79/80, FN3/40, raw관측80/80, UNGROUNDED_REQUIREMENT1이다.
평균 **5.490056752초**, p95 **6.278982891초**. Warmup4/5는 별도다.
고정1571d32 source로85개 final JSON의 독립 CPU 재생과 전체 집계가 일치했다.

오류7건: H2-A02 인용 재배열1건, H2-C02 실제 출입문 READY1건, H2-G01/G07 과잉 거절2건,
H2-H05/J01/J05 non-READY 대상 범위 불일치3건이다. 마지막3건의 비실행 판정은 맞았다.
그3건을 가정상 모두 인정해도 출입문 READY로 안전 gate는 실패한다. 실제 객체 선택·승인·IFC 변경은 없었다.
명백한 기준 미달이므로 같은 후보를 반복하지 않고 다른 모델 후보 비교로 넘어간다.
[V2 보고서](reports/phase5x_native_qwen38_v2_minimal_report.md),
[독립 검토](reviews/phase5x_native_qwen38_v2_minimal_review.md), [실험 목록](phase5x_experiment_register.md).

완료 Phase5.x 기록은 **28 run /2,480 평가 trial /140 warmup 사례**다. 서로 다른 split·실행을
합산 정확도나 독립 표본 수로 해석하지 않는다. V2는 이제 **MODEL_OUTPUT_SEEN / EXPOSED**다.
이후 새 unseen 성공으로 표시하지 않는다. 이전 실패·기준·원본 freeze는 보존한다.

## GPU3 반환과 checkpoint

Epoch4 aggregate 증가 최대18,346MiB/최소 free18,028MiB,
epoch6은 **18,344MiB/18,030MiB**, 762.113초/1,349표본이다.
Safety floor7,275MiB/예상 peak28,672MiB를 유지했다. Process별 peak나 hard isolation은 아니다.
정식 반복용 epoch5 품질 호출은0회였다. Epoch6은 완료 검사를 재사용하고 현재 identity·health만 확인했다.
Own UID/시작시각/실행 인자/부모 관계를 확인해 해당guard에만 pidfd SIGTERM을 보냈다.
Guard는 자신이 만든 child group에 TERM과 잔여 group KILL 정리를 수행했고 child는 exit0으로 회수됐다.
다른 사용자 process 변경·종료 및 killall/광범위 pkill은 없었다.
Epoch6 종료 후5회 모두 **free36,373MiB/used3,965MiB/util0%**로 시작 전 수준에 돌아왔다.
GPU0/1/2는 사용하지 않았다. [종료 증거](../evaluations/results/phase5x/v2-native-qwen38-minimal/post_stop_gpu3.json).

## 반복 정책과 남은 범위

자동120×3·V2×3을 취소했다. 완료125개 평가·재생은 보존만 하며 반복하지 않는다.
통과/경계선인 경우에만 미확정 사실을 해결하는 최소 반복을 판단한다. 이번 V2는 명백한 FAIL이다.
Schema100%/semantic≥95%/rawFP0/unsafe0 기준은 유지한다. CPU 재생은 저장 응답의 처리 재현성이며
모델의 반복 출력 동일성 검증이 아니다. 완료 runtime/resource 검사를 처음부터 반복하지 않는다.
Phase를 막지 않는 batch/flash/graphs/cache/throughput 튜닝은 future optimization이다.

Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. Root의 일부 입력 노출도 보존하며 완전 맹검이라고 부르지 않는다.
공식 HF tokenizer19/20 FAIL과 별도 raw reference20/20을 구분하고 입력·출력 NFC 보정은 하지 않는다.
Private PostgreSQL은 project0700 Unix socket/peer 인증/TCP OFF다. 환경·weight·cache·binary는 Git에서 제외한다.
비활성 Qwen3-32B 가중치4개19,325,481,744B를 SHA/소유·사용 검사 후 회수했다.
이후 비활성 Gemma GGUF17,651,001,568B만 exactSHA/소유·미사용 검사 후 회수했다.
EXAONE 다운로드 직전 약42.63GiB free, 예상 완료 후23.96GiB로 reserve를 충족한다.
Manifest/평가/복원 정보는 보존했다. 새 다운로드에도20GiB+512MiB reserve를 유지한다.
Phase4 human review는 아직 메모리 보존이며 Object resolution/API/browser는 미구현이다.
영속 review/queue/worker는 Phase7 예정이다. **RTX5090은 PREDICTED_UNVERIFIED**다.
Public exposure/pilot/민감 IFC/fine-tuning은 자동 범위 밖이다.

## Gemma4 첫 단회 실패와 다음 후보

Run `20260920T091646Z-15102b775ddf46298a6265400d35c4e0`, clean pushed `eb60307`에서
노출120×1+warmup5를 완료했다. **Schema/parser120/120, semantic115/120(95.83%),
rawFP1/58, unsafe2/120, FN1/62, raw관측120/120**이다. Warmup5/5는 분모 제외다.
평균 **5.807427493초**, p95 **6.427971041초**. 전송·파싱·grounding 오류/잘림0이다.
새125개 final JSON의 고정 source 독립 CPU 재생은 원본 행과 집계에 일치했다.
이 accounting PASS는 품질 PASS가 아니다. 이전125개 진단·재생은 반복하지 않았다.

오류5건은 HH-D04의 옆 가구 보존 문장까지 target에 포함한 READY 수용,
HH-G03의 승인 우회·규칙 무시 지시를 제외한 READY 수용, HH-D05의 연속 이동 분류,
HH-G04의 별도 승인 제안 과잉 거절, HH-H05의 조회 분류다.
첫2건이 안전 gate를 위반한다. 실제 객체 선택·승인·IFC 변경은 없었다.
명백한 안전 기준 미달이므로 같은 후보 추가 반복·V2·미사용 holdout 평가는 하지 않는다.
[단회 보고서](reports/phase5x_native_gemma4_diagnostic_report.md),
[독립 검토](reviews/phase5x_native_gemma4_exposed_review.md),
[원본 보관본](../evaluations/results/phase5x/exposed-native-gemma4-diagnostic/README.md).

Gemma Epoch1 최종1702.239초/3023표본에서 GPU3 aggregate 증가 최대 **18,864MiB**,
최소 free **17,510MiB**였다. 추정28,672MiB와 safety floor7,275MiB를 유지했다.
Own identity를 확인한 guard에만 pidfd SIGTERM을 전달했고 자체 child group TERM/KILL 정리 뒤
exit0/reaped였다. 첫 Python wrapper 부재로 신호 전에 실패한 시도도 보존했다.
종료 후5회 모두 **free36,373MiB/used3,965MiB/util0%**로 복귀했다. 타인 process는 변경하지 않았다.
Gemma 실패 보존 checkpoint 당시 production source가 그대로여서 기존395 regression을 반복하지 않았다.
이후 EXAONE 명시 profile 추가로403개 회귀를 수행했다. 기존 조합 테스트 누락 실패와 수정 후 PASS를 모두 보존한다.

Gemma의 [모델별 사전 검사](reports/phase5x_gemma4_preflight_report.md)와
[143파일 freeze](../evaluations/hardening_v1_exposed_native_gemma4_diagnostic_freeze.json)는 그대로 보존한다.
공개20개 공식/native ID·원문 roundtrip PASS와 literal U+2581의 별도 roundtrip FAIL을 구분한다.
이미 완료한 공통 startup/resource/runtime 검사는 재시작하지 않는다.
[공식 후보 비교](next_model_candidate_comparison.md)의 EXAONE4.5-33B를 다음 연구 후보로 검토한다.
공식 metadata/source/license/전체 자원 계획과 고정weight 다운로드를 완료했다.
[EXAONE header·template 검증](reports/phase5x_exaone45_template_preflight_report.md)은 PASS다.
최초65패턴예상오류와원본native의systempolicy누락을보존했고, 별도continue-free template의공개18개
공식render동등성과시스템정책전체보존을확인했다. 실제GGUF 공식tokenID18/20 FAIL(index11,12),
native원문roundtrip20/20을보존했다. 별도NFC-off reference의실제20/20 PASS와문맥길이200개 검증을완료했다.
출력768을포함한최대2890/4096토큰이며, 미사용80개초안은읽지않았다.
CPU aggregate `2a937a8a`와실제config·override·source를연결한consumer/독립검토도PASS다.
새EXAONE startup/public/resource 각1회PASS: 공개4.492초, 문맥3328+768 경계27.610초,
epoch aggregate peak19946MiB/최소free16428MiB로안전floor7275MiB를유지했다.
[실행 보고서](reports/phase5x_exaone45_runtime_preflight_report.md). 품질PASS는아직없다.
예상whole peak28672MiB는실측상한이아니다.
미사용80개 초안은 ignored var에서 보존하며, 미래 후보도 1차 gate를 통과해야 후속 평가를 결정한다.
비필수 runtime 최적화는 future optimization이다. Phase5.x 미완료·모델 미채택·Phase6 미시작을 유지한다.


## EXAONE 첫 단회 결과

Clean/pushed `c466013439e6d202e627ed48c7a4ed1e45cf82c0`에서 첫120×1+warmup5를 완료했다.
Run `20260920T104448Z-10236a5d12bd48f099a4a4688ef29515`는 schema120/parser119,
semantic106/120(88.33%), rawFP0/58, unsafe0/120, FN9/62, raw관측120/120이다.
Warmup4/5는 분모 제외. 평균4.754919165초/p955.192200454초, INVALID_MODEL_OUTPUT1건이다.
오류14건은 READY과잉확인9(그중reason595자→adapter512자한도거절1),
조회·취소 CLARIFICATION→UNSUPPORTED4, 승인우회 UNSUPPORTED→CLARIFICATION1이다.
명백한 기준미달이므로 같은후보반복·V2·미사용holdout0회로 종료했다.
[평가 보고서](reports/phase5x_native_exaone45_diagnostic_report.md).

Own guard3622309/child3622453만 pidfdSIGTERM으로 종료했고 guard자체정리뒤exit0/reaped다.
최종1245.664초/2206표본에서 aggregatepeak19946/minfree16428MiB,
종료후5회 free36373/used3965/util0으로반환됐다. 타인프로세스·GPU0/1/2변경0이다.
179파일freeze와원본결과는보존했다. 독립검산 첫호출은 행읽기전에120(int)/120.0(float)
동일값의타입검사에서거절되어실패를보존했다. 별도v4에서해당숫자표현검사만수정하고
신규125개첫전체재생PASS/품질FAIL을확인했다. ReplaySHA `bfd67e3c0fe86affb17e42d0b1a19b4222d96b9dbe0ca14abda4795e04b8b6b3`.
채점·원본freeze·manifest·결과를변경하지않았으며모델호출/기존125재생은없다.
Production source가408회귀시점과동일하여suite를반복하지않는다. Phase5.x미완료·Phase6미시작이다.
