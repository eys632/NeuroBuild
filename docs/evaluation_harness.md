# Synthetic requirement 평가 도구

`scripts/evaluate_requirements.py`는 이미 실행 중인 loopback local model server를
호출한다. 모델 설치·실행, GPU 조회, IFC 변경, 대상 확인이나 적용 승인을 수행하지 않는다.
실행 전 [GPU 예산 절차](gpu_budget.md)와 launcher watchdog을 별도로 충족해야 한다.
평가 설계는 [model_evaluation_plan.md](model_evaluation_plan.md), 출력 계약은
[requirement_pipeline.md](requirement_pipeline.md)를 따른다.

Gold 상태는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. seed20은 공개 development
자료이며 9개 READY와 11개 non-READY rubric으로 구성된다. 기본 5회 warmup 후 각 case를
파일 순서대로 3회 연속 호출한다. 집계 분모는 60회, READY gold 27회, non-READY gold
33회다. warmup 응답은 별도 보존하며 품질/latency 분모에서 제외한다.

## 실행과 기록

Backend `.conda`에서 실행한다. GPU dependency는 필요하지 않다. 아래 명령의 모델과
revision은 실제 서버의 launch 기록 및 검증된 weight manifest와 일치해야 한다.
실제 모델 평가를 하지 않은 unit test 결과를 모델 성능으로 표시하지 않는다.
서버의 `--served-model-name`과 아래 `--model`은 `neurobuild-local`로 맞춘다.
Hugging Face checkpoint ID `Qwen/Qwen3-14B-AWQ`는 weight manifest에서 읽으며
HTTP model alias를 대신하지 않는다.

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
`--max-tokens 768`, `--timeout 60`, `--warmups 5`, `--trials 3`이 기본이다.
4096 context 등 서버 한도는 runtime metadata에 별도로 기록한다. max_tokens와 prompt가
context에 맞지 않아 서버가 거절하면 실패 trial이다. client는 temperature0, seed42,
thinking off, `xgrammar:no-fallback`, 동시 요청1을 사용한다.

Runtime metadata는 다음 **정확한 key 집합**을 가진 JSON이다. 버전은 설치된 runtime에서
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

Weight manifest는 downloader의 `model_id`, 정확한 `revision`, 각 파일의
`name`/`bytes`/`sha256` 목록을 사용한다. 평가 도구는 manifest를 검사하고 해시를
기록하지만 대형 weight를 다시 읽지 않는다. HTTP 응답의 model 이름은 configured
served model과 같아야 한다. 서버가 실제로 로드한 commit은 HTTP만으로 입증할 수
없으므로 runtime identity는 **operator supplied**, 파일 검증은 downloader의 책임으로
기록한다. tokenizer/template/launch 설정과 실제 프로세스의 연결도 launch 단계에서
확인한다. 모델 이름만으로 revision 검증 완료를 주장하지 않는다.

각 실행은 `var/runs/<UTC timestamp>-<UUID>/`를 새로 만들어 다음을 기록한다.

- `manifest.json`: model/tokenizer revision, runtime metadata, Git commit/dirty,
  dataset/prompt/schema/weight manifest/runtime/scorer/parser/client SHA256, 실제 protocol.
- `dataset.json`: synthetic source/context/gold snapshot과 검수 상태.
- `results.json`: warmup/trial별 최종 semantic JSON, parse/schema/parser 판정,
  안전한 error code, SI 환산값, token 수, latency, 집계와 한계.

파일은 exclusive create로 작성하며 이전 실행을 덮어쓰지 않는다. setup/storage 오류는
짧은 고정 error code로 종료한다. 잘못된 응답 원문, HTTP body, traceback, secret,
`reasoning_content`와 chain-of-thought는 저장하지 않는다. 구조에 맞지 않는 JSON은
원문 대신 판정/오류 코드만 저장한다. 유효한 최종 semantic JSON의 짧은 `reason`은
명시적인 clarification/unsupported 사유이며 모델 내부 추론을 요청하지 않는다.

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

기본값은 선정promptv3/max_tokens768/port8003/legacy_guided_json이다. `--protocol structured_outputs`는 최신runtime용 명시적 선택이며 서버backendxgrammar검증이 별도로 필요하다. `--split development_seed|development|heldout`를 manifest에 기록한다. dialect자동추측/무제약fallback없음. Phase5 frozen비교5개는이옵션추가전commit51a07d5의client/evaluatorhash를보존하며, 변경후별도actualsmoke3건은 `evaluations/results/phase5/protocol_smoke.json`이다.

Phase5.x부터 두 지표를 추가하며 기존FP/FN분모와동결결과는변경하지않는다. `accepted_incorrect_move_on_ready_gold`는 goldREADY 중 Backend가READY로수용했지만target/축/값rubric이틀린건수/goldREADY수다. `unsafe_accepted_ready_total`은 비실행gold의수용READY와그잘못된이동을합산한건수/전체trial이다. Parser가거절한지원요청은FN으로계속보고하며잘못된실행가능변경과구별한다. 이들은실제IFC실행이아닌요구사항단계의지표다.
