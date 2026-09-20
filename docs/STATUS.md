# NeuroBuild_v2 실행 상태

갱신: **2026-09-20 KST — GLM 준비 checkpoint 원격 보존, 실제 vocabulary·입력 길이 PASS**.
Phase0~5 원격 checkpoint는 완료했다. **Phase5.x 미완료, 현재 후보 미채택, Phase6 미시작**이다.

| 항목 | 현재 상태 |
|---|---|
| 완료 Phase | 0 Foundation, 1 Domain, 2 Persistence, 3 IFC Engine, 4 Explicit Workflow, 5 Local Model |
| 마지막 완료 Phase checkpoint | `d6e39c89658c552c59a8049d7198da051290bd3b` |
| GitHub | 공통 `v2`; 기존 단회 `704e9f6`, V2 실패 `3a89af9`, Gemma 실패 `f46b2cf`, EXAONE 진단동결 `c466013439e6d202e627ed48c7a4ed1e45cf82c0` push·원격 일치 확인; EXAONE 실패·종료 `daeccacee7bb1912e03c8be696572b80b12c9f4c` push·원격 일치 확인 |
| 현재 작업 | **GLM 실제 header·공개 CPU 계약·공식 vocabulary·입력 길이 PASS 보존, runtime 증거 연결 준비** |
| 최근 후보 | EXAONE4.5-33B Q4_K_M: 첫 의미 정확도 gate FAIL. Gemma4-31B 첫 안전 gate FAIL, Qwen3.8 V2 FAIL |
| Qwen 1차 품질 결과 | 노출120×1: schema120, parser119, semantic117, rawFP0/58, unsafe0/120 — PASS 보존 |
| Gemma 1차 품질 결과 | 노출120×1: schema/parser120, semantic115, rawFP1/58, unsafe2/120 — **FAIL** |
| EXAONE 1차 품질 결과 | 노출120×1: schema120, parser119, semantic106, rawFP0/58, unsafe0/120 — **FAIL** |
| V2 품질 결과 | 80×1: schema80, parser79, semantic73, rawFP1/40, unsafe1/80 — FAIL |
| 회귀 검증 | **416 tests PASS**, skip0, 실제 PostgreSQL/IfcOpenShell, headless19.398초. GLM 명시 profile·실제 metadata의 정확한 모델/type 연결 검증 |
| Hard blocker | 없음. 품질 gate 미달로 Phase6 진행 불가, Phase5.x 다른 후보 검토 계속 |
| 모델 실행 | Qwen/Gemma/EXAONE 자체 서버 모두 STOPPED·exit0/reaped. EXAONE 종료 후5회 GPU3 free36,373MiB/used3,965MiB/util0% |
| Backend | `.conda`: Python3.12.14/PostgreSQL17.11/psycopg3.2.10/IfcOpenShell0.8.5 |
| 다음 검증 | 실제 CPU proof와 GLM runtime 설정 연결 검토 후 GPU3 자원 여유 확인. GPU 실행·품질 평가 전이며 이전 실패 후보 반복0회 |

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
이 검사는 채점·추론이 아니며 공개20개 재실행도 없다. 아직 GPU/model 품질 호출0이고
미사용80개도 접근하지 않았다. [준비 보고서](reports/phase5x_glm47_flash_preparation_report.md),
[실제 CPU 보고서](reports/phase5x_glm47_flash_native_cpu_report.md).

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

완료 Phase5.x 기록은 **26 run /2,240 평가 trial /130 warmup 사례**다. 서로 다른 split·실행을
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
