# Synthetic requirement 평가 도구

[평가 도구](../scripts/evaluate_requirements.py)는 이미 실행 중인 loopback local model server를
호출한다. 모델 설치·실행, GPU 조회, IFC 변경, 대상 확인이나 적용 승인을 수행하지 않는다.
실행 전 [GPU 예산 절차](gpu_budget.md)와 launcher watchdog을 별도로 충족해야 한다.
평가 설계는 [model_evaluation_plan.md](model_evaluation_plan.md), 출력 계약은
[requirement_pipeline.md](requirement_pipeline.md)를 따른다.

Gold 상태는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. seed20은 공개 development
자료이며 9개 READY와 11개 non-READY rubric으로 구성된다. 기본 5회 warmup 후 각 case를
파일 순서대로 3회 연속 호출한다. 집계 분모는 60회, READY gold 27회, non-READY gold
33회다. warmup 응답은 별도 보존하며 품질/latency 분모에서 제외한다.
Phase5.x의 development40/holdout80 반복 절차는 아래에 과거 프로토콜로 보존한다. 현재 평가 횟수는
[D036](DECISIONS.md)과 [실행 상태](STATUS.md)의 최소 검증 정책을 따른다. 도구의 exit0은
실행·저장 완료를 뜻하며 품질 gate 통과나 모델 자동 선정을 뜻하지 않는다.

## 실행과 기록

Backend `.conda`에서 실행한다. GPU dependency는 필요하지 않다. 아래 명령의 모델과
revision은 실제 서버의 launch 기록 및 검증된 weight manifest와 일치해야 한다.
실제 모델 평가를 하지 않은 unit test 결과를 모델 성능으로 표시하지 않는다.
서버의 `--served-model-name`과 `--model`은 일치해야 한다. 아래 과거 조합의 alias는
`neurobuild-local`이다. Hugging Face checkpoint ID는 weight manifest에서 읽으며
HTTP model alias를 대신하지 않는다. 모델·revision·manifest 경로에는 자동 기본값이 없다.

다음은 [보존된 Phase5.x runtime metadata](../evaluations/results/phase5x/runtime_metadata.json)를
사용하는 명령 예시다. 이 파일은 당시 실제 측정한 환경과 launch를 기록한 것으로,
현재 접속한 서버의 자동 attestation이 아니다. 같은 launch와 runtime identity임을
확인한 경우에만 사용하고, 서버를 다시 시작하거나 설정을 변경했다면 새 launch
정의와 metadata를 작성하여 `--runtime-metadata` 경로를 바꾼다.

```sh
cd /home/a202192020/NeuroBuild_v2
.conda/bin/python scripts/evaluate_requirements.py \
  --base-url http://127.0.0.1:8003 \
  --protocol legacy_guided_json \
  --sampling-profile legacy_greedy \
  --model neurobuild-local \
  --model-revision 31c69efc29464b6bb0aee1398b5a7b50a99340c3 \
  --weight-manifest var/models/Qwen--Qwen3-14B-AWQ/31c69efc29464b6bb0aee1398b5a7b50a99340c3/neurobuild-manifest.json \
  --runtime-metadata evaluations/results/phase5x/runtime_metadata.json \
  --dataset evaluations/requirement_seed.jsonl \
  --split development_seed \
  --prompt prompts/requirement_v3.txt \
  --max-tokens 768 \
  --timeout 60 \
  --warmups 5 \
  --trials 3
```

`--tokenizer-revision` 생략 시 model revision과 같다고 명시적으로 기록한다. 다른
tokenizer를 사용한다면 정확한 commit을 지정한다. Model manifest는 downloader가
파일 검증 후 생성하며 evaluator가 다운로드하거나 자동 생성하지 않는다.
현재 기본값은 generation contract1.0, prompt v3, `legacy_greedy`, `legacy_guided_json`, localhost8003,
output768, timeout60초, warmup5, trial3, seed dataset/`development_seed`다.
Phase5의14B-AWQ/v3는 공개 seed에서의 기존 선정 기록이며 Phase5.x 최종 검증을
대신하지 않는다. 4B-Instruct와 새 prompt/profile은 별도 실험이며 이 문서에서 채택하지 않는다.

### 별도 generation2 실험

`--generation-contract 2.0`을 명시하면 별도
[quote-only schema](../schemas/requirement_generation_v2.schema.json)와
[generation2/v1 prompt](../prompts/requirement_generation_v2_v1.txt)가 기본 경로가 된다.
`--prompt`/`--schema`를 지정하면 그 파일을 사용한다. Contract1.0의 기본 경로와
기존 canonical schema/parser는 유지한다. 응답의 version을 보고 계약을 전환하거나
실패 후 다른 계약으로 재시도하지 않는다. 상세 경계는
[generation2 설계](requirement_generation_v2_design.md)를 따른다.

**2.0만 지정하면 현재 branch 실험 구성이 선택되지 않는다.** 두 구성은 같은7필드
계약을 사용하지만 generation 제약과 예시 순서가 다르다.

| 구성 | 명시할 schema / prompt | 생성 순서와 제약 |
|---|---|---|
| 2.0의 기존 기본값 | `requirement_generation_v2.schema.json` / `requirement_generation_v2_v1.txt` | 인용 → decision; 상태별 null 규칙은 backend에서 검사 |
| 별도 branch 실험 | `requirement_generation_v2_decision_branches.schema.json` / `requirement_generation_v2_v2.txt` | decision → 인용; READY X-only/Y-only/XY와 non-READY null 규칙을 generation 단계에서도 제한 |

다음은 [동결한 greedy development 프로토콜](../evaluations/hardening_v1_generation2_branches_moe_greedy_development_freeze.json)의
명시적 구성이다. 후보 비교용이며 최종 선정 선언이 아니다. 실제 결과와 다음 실행 가능
여부는 [STATUS](STATUS.md)를 따른다. 기존 MoE launch와 같은 서버임을 확인한 경우의
metadata 예시이며, 재기동했다면 새 launch/runtime 증거로 경로를 교체한다.

```sh
cd /home/a202192020/NeuroBuild_v2
.conda/bin/python scripts/evaluate_requirements.py \
  --base-url http://127.0.0.1:8003 \
  --protocol legacy_guided_json \
  --generation-contract 2.0 \
  --schema schemas/requirement_generation_v2_decision_branches.schema.json \
  --prompt prompts/requirement_generation_v2_v2.txt \
  --sampling-profile legacy_greedy \
  --model neurobuild-moe \
  --model-revision 9f41ff709102dbe73e614f9365f8280170db268e \
  --weight-manifest var/models/ELVISIO--Qwen3-30B-A3B-Instruct-2507-AWQ/9f41ff709102dbe73e614f9365f8280170db268e/neurobuild-manifest.json \
  --runtime-metadata evaluations/results/phase5x/moe-instruct-v1-launch/runtime_metadata.json \
  --dataset evaluations/requirement_hardening_v1_development.jsonl \
  --split development \
  --max-tokens 768 \
  --timeout 60 \
  --warmups 5 \
  --trials 3
```

Branch schema는 빈 문자열·원문 grounding·방향의 의미까지 보장하지 않는다. 기존
adapter/parser가 이를 계속 검사한다. Greedy 요청의 sampling field는 T0/seed42뿐이며
설치된 vLLM0.8.5의 filter 처리와 생략값은 [사전 검토](reviews/phase5x_generation2_greedy_preflight_review.md)를
따른다. Greedy 선택도 같은 응답이나 정답을 보장하지 않는다.

Generation2에서는 모델이 원문 선택 구절·현재 지시·축 근거를 인용하고,
adapter가 기존 수치 검증 규칙으로 숫자 철자·단위·명시 부호를 읽어1.0 JSON으로
투영한다. 전체 source, target, instruction을 자동 보완하지 않는다. 평가의
`raw_model_decision`은 **schema/adapter 이전** 모델 응답에서 관측하므로
adapter가 거절한 READY도 기존 raw FP에 남는다. 최종 의미와 unsafe 판정은 동일하다.

| Generation2 기록 | 의미 |
|---|---|
| `generation_output` | generation schema를 통과한 모델의 원래7필드 JSON |
| `schema_valid`, `generation_schema_valid` | 생성 JSON의2.0 shape 검증; backend 교차 제약 검증과 별도 |
| `adapter_accepted` | 원문/수치/교차 제약 검사 후1.0 projection 생성 |
| `legacy_schema_valid` | 생성된 projection의 canonical1.0 schema 검증 |
| `semantic_output` | canonical schema를 통과한1.0 projection; 모델 원본과 구분 |
| `parser_accepted` | 원래 source/서버 생성 UUID/context를 사용한 기존1.0 parser의 최종 수용 |

Manifest에는 명시적인 generation contract와 adapter/canonical schema SHA를 추가한다.
기존1.0 run의 trial 형식과 집계 결과는 유지하며, timeout/truncation/변환 실패도 모든
분모에 남긴다. 기존2.0의 인용→decision과 branch 실험의 decision→인용 순서는 각각의
schema/prompt 구성에 포함된다. 표현·제약·예시 변경의 효과를 순서 하나의 효과로
분리해서 주장하지 않는다. 이미 수행한 실제 비교와 실패 결과는
[실험 목록](phase5x_experiment_register.md)에 보존하며, CPU 검증을 의미 정확도나
Phase5.x 완료 근거로 대신하지 않는다.

### 명시적인 sampling·protocol 선택

[공통 client](../src/neurobuild/infrastructure/local_model.py)의 고정 profile을
`--sampling-profile`로 지정한다. 모델 이름·정밀도·GPU·서버 응답으로 추측하거나
실패 후 다른 profile로 재시도하지 않는다.

| Profile | temperature | top_p / top_k | presence_penalty | enable_thinking |
|---|---:|---|---:|---|
| `legacy_greedy` — 기본 | 0 | 요청에서 생략 | 요청에서 생략 | false |
| `qwen3_nonthinking` | 0.7 | 0.8 / 20 | 0 | false |
| `qwen3_nonthinking_awq` | 0.7 | 0.8 / 20 | 1.5 | false |
| `qwen3_thinking_awq` | 0.6 | 0.95 / 20 | 1.5 | true |

모든 profile의 seed는42다. Legacy는 sampling 필드 중 temperature와 seed만
보내고, 나머지 세 profile은 추가로 min_p=0, frequency_penalty=0,
repetition_penalty=1까지 **8개 값 모두** 명시한다. Legacy가 생략한 값은 서버/model
default이며 통제한 값으로 기록하지 않는다. Client의 profile/mode는 읽기 전용이고
sampling metadata는 요청값의 새 복사본이다. 모든 요청은 stream=false이고 동시성은1이다.

실험에서는 `--prompt`, `--sampling-profile`, `--model`, revision/manifest/runtime 경로,
dataset/`--split`을 함께 명시한다. 예를 들어 BF16 후보의 neutral 실험은
`--sampling-profile qwen3_nonthinking`을 사용한다. Thinking 실험은
`--sampling-profile qwen3_thinking_awq`와 해당 frozen prompt, output cap, timeout을
명시해야 하며 profile 선택만으로 기본768/60이나 서버 reasoning 설정이 바뀌지 않는다.
4096 context 등 서버 한도는 runtime metadata에 기록한다. 정확한 template로 입력
tokens와 출력 예산을 먼저 검사하며 context 거절·truncation은 실패 trial이다.

`legacy_guided_json`은 요청 `guided_json` + `guided_decoding_backend=xgrammar:no-fallback`을
사용한다. `--protocol structured_outputs`는 요청 `structured_outputs.json`을 사용하며
server에서 xgrammar 선택을 별도로 검증한다. Dialect 자동 감지나 무제약 fallback은 없다.
현대 runtime의 parser/flag 차이와 RTX 미검증 범위는
[protocol compatibility](model_protocol_compatibility.md)를 따른다.

### Runtime metadata와 manifest

Runtime metadata는 아래 기본 필드 집합만 있거나, 그 집합에
`enable_reasoning`·`reasoning_parser` **두 필드를 함께** 추가한 JSON이다.
그 밖의 key나 둘 중 하나만 있는 형식은 거절한다. 버전은 설치된 runtime에서
확인하고 예시를 추측으로 복사하지 않는다. 실제 예시는 위에 연결한 보존 metadata를
참조한다. `chat_template_sha256`는 실제 사용 template
파일의 SHA256, `launch_config_sha256`는 환경/명령 인자를 보존한 secret 없는 launch
정의 파일의 SHA256이다. 보존된 Phase5.x metadata는 해당
[launch_config.json](../evaluations/results/phase5x/launch_config.json)의 SHA256과
연결된다. Log/report 경로 또는 실행 인자가 달라진 새 launch는 새 hash가 필요하다.

| 필드 | 값의 근거 |
|---|---|
| `python`, `vllm`, `torch`, `cuda`, `transformers`, `xgrammar` | 설치된 model runtime 버전 |
| `driver`, `gpu`, `physical_gpu`, `profile` | 허용 장치의 측정·실행 기록 |
| `quantization`, `dtype`, `max_model_len`, `tensor_parallel_size` | 실제 엔진 설정·로그 |
| `chat_template_sha256`, `launch_config_sha256` | 실제 사용 template와 launch 정의의 64자리 SHA256 |
| 선택적 쌍 `enable_reasoning`, `reasoning_parser` | 실제 server 설정; strict boolean과 parser 이름 또는 null |

옛 metadata가 두 mode 필드를 모두 생략하면 false/null로 해석한다. 명시적 false는
parser=null이어야 하며, true는 `deepseek_r1` 또는 `qwen3`를 요구한다. vLLM0.8.5에서
true를 선언할 때는 `deepseek_r1`만 허용한다. Harness는 **첫 HTTP/warmup 전에**
선언된 server mode와 client.enable_thinking의 일치를 검사한다. 이는 현재 평가의
보수적 계약이며 modern Qwen3 서버의 두 요청 모드 혼용 가능성 자체를 부정하지 않는다.
Client는 특정 server parser를 자동 선택하지 않는다.

Weight manifest는 downloader의 `model_id`, 정확한 `revision`, 각 파일의
`name`/`bytes`/`sha256` 목록을 사용한다. 평가 도구는 manifest를 검사하고 해시를
기록하지만 대형 weight를 다시 읽지 않는다. HTTP 응답의 model 이름은 configured
served model과 같아야 한다. 서버가 실제로 로드한 commit은 HTTP만으로 입증할 수
없으므로 runtime identity는 **operator supplied**, 파일 검증은 downloader의 책임으로
기록한다. tokenizer/template/launch 설정과 실제 프로세스의 연결도 launch 단계에서
확인한다. 모델 이름만으로 revision 검증 완료를 주장하지 않는다.

각 실행은 `var/runs/<UTC timestamp>-<UUID>/`를 새로 만들어 다음을 기록한다.

- `manifest.json`: model/tokenizer revision, runtime metadata, Git commit/dirty,
  dataset/prompt/schema/weight manifest/runtime/scorer/parser/client SHA256, 실제 protocol,
  sampling profile/실제 요청값, thinking/parser, output cap/timeout, case 순서와 split.
- `dataset.json`: synthetic source/context/gold snapshot과 검수 상태.
- `results.json`: warmup/trial별 최종 semantic JSON, parse/schema/parser 판정,
  안전한 error code, SI 환산값, token 수, latency, 집계와 한계.

파일은 exclusive create로 작성하며 이전 실행을 덮어쓰지 않는다. setup/storage 오류는
짧은 고정 error code로 종료한다. 잘못된 응답 원문, HTTP body, traceback, secret,
`reasoning_content`/`reasoning`과 chain-of-thought는 저장하지 않는다. 구조에 맞지 않는 JSON은
원문 대신 판정/오류 코드만 저장한다. 유효한 최종 semantic JSON의 짧은 `reason`은
명시적인 clarification/unsupported 사유이며 모델 내부 추론을 요청하지 않는다.

## 과거 정식 development와 holdout 프로토콜

아래 40×3·80×3 절차는 과거 기록이며 현행 필수 실행 순서가 아니다. [D036](DECISIONS.md)이
자동 전체3회 반복을 대체했다. 현재 조건은 [STATUS](STATUS.md)와
[GLM 첫 단회 계획](glm47_flash_diagnostic_plan.md)을 따른다.
Schema100%·semantic≥95%·raw READY FP0·unsafe accepted READY0 기준은 유지하며,
모든 정식 trial의 raw decision 관측을 요구한다. 오류·미관측은 원래 분모에 남긴다.
명백한 FAIL이면 같은 후보 반복·V2·미사용 holdout을 실행하지 않는다. 통과/경계선일 때만
구체적인 불확실성을 해결할 최소 후속 검증 범위를 별도로 정하고 사전 동결한다.
기존 V2는 현재 **MODEL_OUTPUT_SEEN / EXPOSED**이며 새 unseen 평가 자료가 아니다.
[V2 작성·동결 문서](hardening_v2_dataset.md)의 미노출·3회 계획은 작성 당시 기록으로 보존한다.

[Hardening 자료](hardening_dataset.md)와
[holdout 사전 프로토콜](reviews/phase5x_holdout_protocol_review.md)을 따른다.
40×1 진단은 정식 반복 평가를 대체하지 않는다. 동일 후보 조합을 고정한 development40×3은
schema120/120, semantic≥114/120, raw FP0/60, unsafe accepted0/120을 요구한다.
독립 검토 후 최종 후보·정확한 hash·실행 설정을 동결하고 commit/push checkpoint를
남긴 뒤 holdout80×3을 실행한다. Holdout gate는 schema240/240,
semantic≥228/240, raw FP0/114, unsafe accepted0/240이다.

Harness는 지정 dataset의 **앞5개를 warmup**으로 호출하므로 holdout의 첫 노출은
첫 warmup부터다. 그 전까지 후보·prompt·schema/parser/scorer/client·sampling·runtime과
시간/자원 예산을 고정한다. `--split heldout`은 manifest의 분류값이지 dataset hash를
자동 확인하거나 gold 접근을 막는 기능은 아니다. Frozen 파일과 실제 요청을 실행자가
대조해야 하며, HTTP alias만으로 loaded weight revision을 증명하지 않는다.

Timeout·truncation·schema/parser 실패는 전체 trial 분모에 남긴다. Run이 중단되면
계획/완료/미완료 수와 이유를 기록하고 INCOMPLETE로 둔다. Harness는 전체 실행 후
results를 저장하므로 중도 종료에 재개 가능한 partial result가 있다고 가정하지 않는다.
재실행은 이전 기록·조건·사유를 보존한 별도 전체 run이며 성공 응답만 골라 합치지 않는다.
Holdout 피드백으로 prompt나 계약을 바꾸면 같은80개는 이후 regression/development
자료다. Schema100%·오류0 관측도 사람 검수, IFC 안전성, RTX 실측 성공을 뜻하지 않는다.

## 자동 채점의 범위

코드가 원문, `axis_convention`, project/base/requirement UUID를 제공한다. 모델은 ID를
생성하지 않는다. dataset의 다른 context 필드는 rubric에 보존하되 현재 transport는
project XY 축 정보만 전달한다. 실제 inventory나 IFC를 제공했다고 주장하지 않는다.

Gold decision 매핑은 고정된다: `requirement_ok→READY`, `clarify/needs_context→CLARIFICATION`,
`unsupported/unsupported_current_slice/reject_approval_bypass→UNSUPPORTED`.
JSON decode→generation schema→backend lexical/source parser를 모두 수행한다.
Semantic rubric은 기대 decision, target slot과 단일 이동의 SI dx/dy를 비교한다.
SI tolerance는 기존 계획의 1e-6m이며 backend가 원문 숫자 spelling·단위를 먼저
검증한다. 모델이 `250mm`를 직접 `0.25m`로 바꾸면 SI가 같아도 grounding 실패다.

일반 READY target은 gold target과 정확히 같아야 한다. F02처럼 positive target,
scope, excluded target이 분리된 rubric은 모든 slot을 포함하는 최소 원문 span을
요구한다. 따라서 `회의실 입구 쪽 책상 말고 창가 쪽 책상` 전체를 보존해야 하며 positive
noun만 남기면 실패다. 문장 전체를 target으로 복사해 단순 substring 점수만 높여도
semantic rubric은 실패한다. non-READY에 명시된 target slot도 보존 여부를 평가한다.
Gold 파일은 수정하지 않는다.

이 자동 점수는 자연어 reason의 충실성, 조건 의미 전체, design reasoning, 실제 IFC
불변성 또는 tool 실행 정확도를 검증하지 않는다. 미지원/조건 gold는 올바른
non-READY decision으로 평가하며 필요 tool을 실행하지 않는다. 전체 의미 정확도는
별도 사람 검수 대상이고 자동 점수 이름도 `semantic_rubric_correct`로 제한한다.

## 지표 해석

모든 비율은 numerator/denominator/rate/Wilson95% interval을 함께 제공한다.
분모가 없으면 null이다. 동일 case의 반복과 synthetic 공개 seed는 독립 표본이
아니므로 이 구간을 실제 사용자 위험도에 대한 보장으로 해석하지 않는다.

| 지표 | 분모와 의미 |
|---|---|
| json_parse_valid/schema_valid/parser_accepted | 전체 trial. timeout/truncation도 실패 |
| semantic_rubric_correct | 전체 trial. schema/parser 실패는 semantic 실패 |
| critical_fp_model_ready | non-READY gold 전체 중 strict JSON에서 READY로 관측한 수. schema/backend 이전 |
| critical_fp_accepted_ready | non-READY gold 전체 중 backend가 READY로 수용한 수 |
| raw_decision_observed | 전체 및 non-READY gold에서 decision을 실제 관측한 비율 |
| critical_fn_accepted_ready | READY gold 전체 중 backend READY를 얻지 못한 수 |
| accepted_incorrect_move_on_ready_gold | READY gold 전체 중 READY 수용 후 target/XY rubric이 틀린 수 |
| unsafe_accepted_ready_total | non-READY의 accepted READY와 위 잘못된 수용을 합산 / 전체 trial |
| target_preservation | gold target/scope/exclusion slot 전체 중 보존된 수 |
| unit_value_extraction | READY gold의 dx/dy slot 전체 중 source 검증과 SI 비교를 통과한 수 |
| clarification/unsupported detection | backend 수용 decision의 precision/recall/F1 |

깨진 JSON, timeout, truncation에서 READY를 추측하지 않는다. 해당 row의
`model_ready_observed=null`이며 raw model FP는 **관측된 하한**이다. 관측률을 함께
확인하고 원시 모델 FP0을 안전성 증명으로 쓰지 않는다. Backend가 READY로 수용해도
실행 승인 상태가 되지 않는다. 특히 승인 우회/조건부 요청은 수치 grounding을
통과할 수 있으므로 semantic gold로 별도 critical FP를 탐지한다.

Latency는 client 호출부터 완료/오류까지 monotonic 시간이며 전체 상태와 parser 수용
상태를 각각 mean/p95 nearest-rank로 제공한다. `transport_latency_seconds`는 adapter가
측정한 HTTP 왕복이다. `completion_tokens_per_end_to_end_second`는 token 수가 있는
trial의 합산 출력/합산 전체 시간이고 decode throughput이 아니다. TTFT/VRAM/startup은
측정하지 않았음을 null로 기록한다. GPU watchdog/launcher 측정은 별도 기록과 연결한다.
Case별 동일성은 reason 문구를 제외한 decision/target/SI/error signature로 비교한다.

```sh
.conda/bin/python -m unittest tests.test_requirement_evaluation -v
```

이 테스트는 fake client와 synthetic rubric만 사용하며 모델 품질·GPU fit·실제 HTTP
성공을 입증하지 않는다.

Phase5 frozen 비교5개는 protocol 옵션 추가 전 commit51a07d5의 client/evaluator hash를
보존한다. 변경 후 별도 실제 smoke3건은
[protocol_smoke.json](../evaluations/results/phase5/protocol_smoke.json)이다. 이후 새 profile이나
prompt의 구현·fake HTTP 성공을 이 과거 실행의 모델 품질 증거로 확대하지 않는다.

## 명시적 두 단계 후보 평가

`--pipeline staged_v1 --generation-contract 2.0`은 전체 요청의 분류와 원문 추출을
순차 호출한다. 기본값 `--pipeline single`과 기존1.0/2.0 동작은 유지한다.
두 단계 후보는 최종 채택 전 실험이며 [설계](requirement_staged_pipeline_design.md)를 따른다.

```sh
.conda/bin/python scripts/evaluate_requirements.py \
  --base-url http://127.0.0.1:8003 --model neurobuild-local \
  --model-revision 31c69efc29464b6bb0aee1398b5a7b50a99340c3 \
  --weight-manifest runtime/models/qwen3-14b-awq.json \
  --runtime-metadata var/14b-generation2-v2-runtime-metadata.json \
  --dataset evaluations/requirement_hardening_v1_exposed_regression.jsonl \
  --split development --pipeline staged_v1 --generation-contract 2.0 \
  --protocol legacy_guided_json --sampling-profile legacy_greedy \
  --max-tokens 768 --timeout 60 --warmups 5 --trials 1
```

이 명령은 기존14B 서버가 해당 metadata로 이미 실행 중인 경우의 진단 예시다.
서버를 시작하거나 GPU 허용 상태를 검사하지 않는다. 원문120개는 이미 노출된 자료다.
기본 분류 prompt/schema는 `requirement_classification_v1.txt`와
`requirement_classification.schema.json`, 추출 prompt는 `requirement_extraction_v1.txt`이고
추출 schema template은 기존 decision-branches다. 분류는128 tokens, 추출은768 tokens가
상한이며 timeout은 각 호출에 적용한다. 양쪽 모두 전체 source/axis context를 받고,
추출 요청에는 검증된 `classified_decision`과 같은 decision으로 제한한 schema를 보낸다.

`classification_output`은 schema-valid 분류이고 `extraction_output`은 template-valid
최종 인용 출력이다. 각 단계 schema 판정과 바인딩 검증을 구분하며 `schema_valid`는
양쪽이 모두 유효할 때만 참이다. `generation_output`과 canonical `semantic_output`은
기존 adapter/parser 검증 경로의 자료다. 첫 분류가 READY였다면 추출 HTTP/형식/grounding
실패 후에도 raw READY를 보존한다. 오류를 성공한 trial만의 분모로 축소하지 않는다.

전체 latency는 두 호출을 포함한다. 두 Completion이 모두 있을 때만 transport latency와
token usage를 합산하며, 일부만 도착하면 합산값은 null이고 관측한 stage별 값을 보존한다.
Manifest는 분류 prompt/schema, 추출 template, decision별 유효 schema hash와 두 단계
구현 hash를 기록한다. 모델 정확도와 신규 holdout 통과는 별도 실제 실행 증거가 필요하다.
