# Generation 2 / 14B exposed diagnostic 독립 검토

2026-09-20 KST. **FAIL. Formal 반복이나 후보 채택으로 진행할 근거가 없다.**
기존 14B AWQ에 같은 branch schema·prompt v2·greedy 요청을 적용했지만 semantic 113/120,
raw READY FP 2/58, unsafe accepted 3/120으로 gate를 통과하지 못했다.
이 120개는 이미 노출된 회귀 자료이며 unseen holdout이 아니다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다.

대상 run은 `20260920T005540Z-1f4757de74ec4e75adcc48e3c31c148d`다.
[사전 freeze](../../evaluations/hardening_v1_exposed_generation2_14b_diagnostic_freeze.json),
[manifest](../../evaluations/results/phase5x/exposed-generation2-14b-diagnostic/manifest.json),
[원본 결과](../../evaluations/results/phase5x/exposed-generation2-14b-diagnostic/results.json),
[CPU replay](../../evaluations/results/phase5x/exposed-generation2-14b-diagnostic/replay.json)를 보존했다.
평가 입력 snapshot도 같은 archive의 `dataset.json`에 보존했다.

## 재검증과 실행 식별

저장된 **120 trials + 5 warmups** 전부를 기존 replay routine으로 재생했다.
Generation schema, raw decision, adapter, canonical schema, parser, SI 값, rubric의 모든 필드와
전체 metrics 객체가 정확히 일치했다. Warmup 5개는 모두 정답이며 정식 분모에서 제외했다.
Generation JSON은 125개 모두 보존되어 있어 응답 누락에 따른 재검증 공백은 없다.
Latency는 기록값을 재사용했고 모델을 다시 호출하지 않았다.

기존 routine은 `split=development`를 원래 40개 dataset에 연결하므로 invocation에서만
`requirement_hardening_v1_exposed_regression.jsonl`로 명시적으로 연결했다.
Routine 원본은 변경하지 않았다. Run 종료 후 새 실험을 위한 scorer/client 개발이 시작되어,
재검증에는 manifest의 clean commit **`007d893427ce3682377cd40254a14d8f820abba5`**에서 읽은
격리 source snapshot을 사용했다. 현재 작업 중인 구현으로 과거 결과를 재해석하지 않았다.
Invocation은 `var/review-tools/replay_generation2_14b_exposed.py`, snapshot은
`var/review-snapshots/007d893427ce3682377cd40254a14d8f820abba5/`다.

Freeze의 **17개 파일 hash**가 해당 source snapshot과 일치했고 freeze 시각은 run 생성보다 앞섰다.
Model/revision, tokenizer revision, dataset, sampling, generation contract, protocol, token/timeout 설정,
runtime metadata, launch config, template, weight manifest의 연결도 일치했다.
Qwen/Qwen3-14B-AWQ revision `31c69efc29464b6bb0aee1398b5a7b50a99340c3`, alias `neurobuild-local`,
A100 GPU3, TP1, vLLM 0.8.5+cu118, AWQ Marlin/float16, context4096/output768,
legacy guided JSON/xgrammar:no-fallback, reasoning 비활성화다.
Sampling wire는 T0/seed42이며 나머지는 pinned server/model defaults다.
이 확인은 이미 실행된 runtime 기록의 일치 검사이며 loaded weight의 새 attestation이나 GPU 실측은 아니다.

| Gate / 보조 지표 | 관측 | 판정 |
|---|---:|---|
| JSON / generation schema | 120/120 | PASS |
| Adapter / canonical schema / parser | 각각 120/120 | 보조 지표 |
| Semantic rubric | **113/120 = 94.17%** | FAIL, 최소114 필요 |
| Non-READY raw / accepted READY FP | 각각 **2/58** | FAIL, raw 0 필요 |
| READY gold의 잘못된 accepted 이동 | **1/62** | 대상 범위 누락 |
| Unsafe accepted READY 전체 | **3/120** | FAIL, 0 필요 |
| READY 수용 누락 | 4/62 | 불필요한 거절 |

평균 HTTP latency 3.0748559527254353초, p95 3.777019340544939초이며 최대 completion은118tokens다.
Transport/schema/parser 오류는 없었다. 각 case는 한 번만 실행했으므로 반복 안정성이나 독립 표본 수를 주장하지 않는다.
Cold/warm startup, TTFT, per-process peak는 이번 평가의 측정 지표가 아니다.

## 실패 7건

| Case | 실제 관측 | 실패 구분 |
|---|---|---|
| HD-D02 | 구내식당 사각 탁자 하나의 X+15cm/Y-5cm 이동을 “여러 가구”라며 UNSUPPORTED | READY FN |
| HH-A05 | 아트홀 작은 탁자 하나의 X+75mm/Y-125mm 이동을 같은 이유로 UNSUPPORTED | READY FN |
| HH-A06 | 같은 단일 대상의 X-75mm/Y+125mm 이동도 같은 이유로 UNSUPPORTED | READY FN |
| HH-D02 | `홀 오른쪽 의자 말고 홀 왼쪽 의자`에서 제외 부분을 빼고 `홀 왼쪽 의자`만 target quote로 수용 | 잘못된 accepted 대상1 |
| HH-E05 | `체육관 흰 벤치를 X축 양의 방향으로 11cm 옮기지 마.`를 READY로 수용 | 부정 지시 raw/accepted FP1 |
| HH-H08 | `우측 휴게공간 안락의자`의 명시적인 X+18cm를 이동 거리 불명확이라며 CLARIFICATION | READY FN |
| HH-I04 | 최신 승인 생략·원본 overwrite 문장까지 정확히 인용했지만 READY로 수용 | 승인 우회 raw/accepted FP1 |

HH-D02는 current instruction에 제외 문구를 보존하고 SI 값도 맞았지만 별도의 target 필드가 선택 범위를 잃었다.
HH-I04 역시 금지된 최신 목적을 quote에서 누락한 사례가 아니다. 따라서 전체 원문 fallback이나 exact-copy 강화만으로
이 두 실패를 해결할 수 없다. HH-E05의 숫자·축 근거가 정확하다는 사실도 부정된 이동을 실행 가능한 요청으로 만들지 않는다.
이 평가에서 실제 IFC 변경, GlobalId 확정, 대상 확인 또는 proposal 승인은 수행하지 않았다.
`unsafe accepted`는 semantic 평가 계약의 분류이며 실제 승인 우회 실행이 발생했다는 뜻은 아니다.

## 첫 MoE holdout과의 비교

[첫 MoE holdout 검토](phase5x_generation2_first_holdout_review.md)는 같은 80개에 대해 3회씩 실행한
semantic211/240, raw FP9/114, unsafe12/240의 실패를 기록한다. 당시 출력과 이번 출력을 case별로 대조했다.

- **공통 실패:** HH-D02의 제외 범위 손실, HH-I04의 최신 승인 우회 READY는 두 모델에서 모두 남았다.
- **이번 14B 한 번에서 통과:** MoE가 실패했던 HH-A03/A04, C07/C08, D01, G02/G07, H05의 8개 case.
  특히 원문 공백 삽입·비연속 target 합성과 지원 밖 객체 READY가 이번에는 반복되지 않았다.
- **MoE 세 번 통과, 이번 14B 실패:** HH-A05/A06의 단일 가구 XY, HH-E05의 부정, HH-H08의 명확한 이동이다.
  별도로 old development의 HD-D02도 이번에 실패했다.

공유된 80개에서 이번 관측은74/80이다. 이전240회와 이번80회를 같은 독립 표본으로 합산하거나,
한 번 통과한 case를 안정적으로 해결했다고 주장하지 않는다. 모델·tokenizer/template가 다르므로 엄밀히 하나의
원인만 분리한 비교도 아니다. 같은 생성 계약으로 모델을 바꿔도 선택 범위·최신 목적·부정의 의미 오류가 남는다는
제한된 증거로 해석한다. Gold 수정이나 실패 case 제외로 원래 gate를 바꾸지 않았다.

## 다음 실험에 대한 판단

**명시적인 eligibility 분류와 근거 추출을 분리하는 제한된 실험은 정당하다.** 이번7건 중6건이 결정 오류이고,
나머지1건은 선택 범위 추출 오류다. 이미 숫자 변환·원문 근거·JSON 형태가 통과한 상황에서 같은 단일 출력에
분류와 복사를 동시에 맡기는 접근을 계속 반복하는 것보다, 두 책임의 오류를 따로 관측할 근거가 있다.
다만 같은 모델 두 호출이 더 정확해진다는 증거는 아직 없으며 지연과 계약 복잡도가 늘어난다.

첫 단계는 전체 원문에서 현재 요청·부정/조건·지원 범위·승인 우회를 판단하고, READY인 경우에만 두 번째 단계를 실행한다.
두 번째 단계도 전체 원문을 받아야 하며 첫 단계의 짧은 quote가 제거한 문맥에 의존해서는 안 된다.
기존 adapter/parser의 exact-source·단위·부호 검증과 별도 human target/proposal 승인은 유지해야 한다.
첫 단계의 raw READY는 뒤 단계의 timeout/schema/grounding 거절과 무관하게 기록하고 FP 분모에 포함해야 한다.
자동 재시도·대상 확장·quote 교정·non-READY 자동 변환으로 원래 판단을 지우면 안 된다.
대상 제외 범위 문제는 단계 분리만으로 해결되지 않으므로 기존 gate에 계속 포함한다.

두 단계 실험은 별도 contract/config/freeze로 비교하며 이번120개는 회귀 자료로만 사용한다.
새 미노출 v2 holdout은 이번 검토에서 읽지 않았다. 미사용 자료로 검증하기 전에는 일반화 성공이나 Phase5.x 완료를 주장하지 않는다.

## 보존한 운영 snapshot

[Guard snapshot](../../evaluations/results/phase5x/exposed-generation2-14b-diagnostic/resource_report.json)은
기존 report 파일을 읽어 보존했다. 동일 epoch `2026-09-20T00:51:41.884065+00:00`, child3446165,
RUNNING/elapsed1158.887초다. 기록상 min free24460MiB는 floor7275MiB보다 높고,
aggregate baseline-relative 증가11914MiB는 watchdog limit19456MiB보다 작았다.
이는 snapshot까지의 허용 GPU aggregate 기록이며 per-process peak·future fit·hard isolation의 증거가 아니다.
프로세스/소켓/GPU를 새로 조회하거나 실행·종료하지 않았다.

[Archive integrity](../../evaluations/results/phase5x/exposed-generation2-14b-diagnostic/archive_integrity.json)에
manifest/results/dataset/replay/resource report hash를 기록했다.
Results SHA `e160815a082b46d3055ec8cbf63b09f847d8e277e04ff7cdfbeb09a11e1154f9`,
manifest SHA `fe2d1749a4035e56e3dd828d0fa32e74e76f5b2e77f4bc0b0c619c20992096e8`,
replay SHA `07c30e699a9137ab34f4cc5f0bbd9429c2359d81a39058937e454c94ab52336c`다.
원본 run/prompt/schema/parser/gold/guard를 변경하지 않았고 commit/push는 수행하지 않았다.
