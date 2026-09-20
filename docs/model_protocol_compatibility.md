# Local model server 프로토콜 호환성

공식 문서/소스 조회: **2026-09-20**. A100에서 사용하는 vLLM0.8.5와 향후 RTX5090
runtime의 HTTP payload 차이를 기록한다. 공통 client의 명시적 dialect 선택은 구현됐다.
**RTX5090 설치·실행·통합 검증은 수행하지 않았다.** 구현 및 fake HTTP 검증과 실제
현대 runtime의 검증 완료를 구분한다.

## 명시적인 dialect 설정

공통 [LocalRequirementClient](../src/neurobuild/infrastructure/local_model.py)는
`StructuredOutputProtocol` enum 또는 같은 문자열로 다음 두 dialect를 명시적으로
선택한다. 모델명·GPU·응답으로 자동 판별하거나 다른 dialect로 재시도하지 않는다.
Application/schema/parser/Domain/승인 로직은 공통이며, 서버별 차이는 transport 요청
필드와 runtime launch 설정에 한정한다. 별도의 `generation_contract` 선택은 어느
dialect에서도 같은 출력 계약을 사용하며 하드웨어에 따른 business logic 분기가 아니다.

| 구현된 dialect | 요청의 schema 필드 | Backend 선택 |
|---|---|---|
| `legacy_guided_json` | `"guided_json": schema`, `"guided_decoding_backend": "xgrammar:no-fallback"` | 현재 A100 v0.8.5 경로 |
| `structured_outputs` | `"structured_outputs": {"json": schema}` | 현대 runtime의 launch 설정에서 `xgrammar` 명시 |

[v0.8.5 공식 요청 계약](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/entrypoints/openai/protocol.py)은
legacy 필드를 지원한다. 실제 A100 평가는 client의 이 dialect를 사용한다.
[현행 structured output 문서](https://docs.vllm.ai/en/stable/features/structured_outputs/)는
`guided_json`, `guided_decoding_backend` 등 구형 필드가 **v0.12.0에서 제거**되었으며,
JSON schema를 `structured_outputs.json`으로 전달하도록 안내한다.

모델명이나 GPU 종류로 protocol을 추측하지 않는다. runtime과 dialect를 명시적으로
pin하고 run manifest에 기록한다. 실패 후 다른 dialect나 schema 없는 요청으로
자동 재시도하지 않는다. HTTP200 또는 우연히 유효한 JSON 한 건은 grammar 적용의
증거가 아니다. v0.12.0 및 v0.29.0의 base request model은 extra 필드를 허용하며
알 수 없는 필드가 무시될 수 있다. 따라서 legacy payload를 현대 서버에 보내면
요청은 성공하면서 schema 제약은 적용되지 않을 수 있다.
[v0.12.0 소스](https://github.com/vllm-project/vllm/blob/v0.12.0/vllm/entrypoints/openai/protocol.py#L87),
[v0.29.0 소스](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/entrypoints/serve/engine/protocol.py#L22)

## Backend와 fallback은 버전별로 고정

- **v0.8.5:** 요청의 `guided_decoding_backend="xgrammar:no-fallback"`를 유지한다.
  unsupported schema를 다른 backend로 바꾸는 것을 막는 legacy 옵션이다.
  [fallback 처리 소스](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/model_executor/guided_decoding/__init__.py)
- **v0.12.0:** server의 structured output config에 `backend`와 `disable_fallback`
  필드가 존재한다. 현대 요청에 legacy backend 필드를 넣지 않는다.
  [버전 고정 config 소스](https://github.com/vllm-project/vllm/blob/v0.12.0/vllm/config/structured_outputs.py)
- **v0.29.0:** launch에서 `--structured-outputs-config.backend=xgrammar`를 지정한다.
  명시적인 xgrammar 경로는 검증 실패 시 fallback하지 않고, `auto` 경로에서만 다른
  backend를 선택한다. 이 버전 config에는 `disable_fallback` 필드가 없으므로
  v0.12.0의 옵션을 그대로 복사하지 않는다.
  [검증 및 backend 선택](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/sampling_params.py#L1146),
  [config 정의](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/config/structured_outputs.py)

조회 시 최신 release는 **v0.29.0, 2026-09-09**다. 이는 RTX용 선정 버전이라는 뜻이
아니다. 해당 release의 기본 배포는 CUDA13.0이며 CUDA12.9 artifact도 제공한다.
일반 설치 페이지의 설명보다 선정한 release의 실제 wheel/metadata를 우선 확인한다.
[공식 release 및 artifact](https://github.com/vllm-project/vllm/releases/tag/v0.29.0)

## 구형 protocol 유지 대안과 검증 범위

vLLM0.9.2는 legacy `guided_json`을 지원하며 공식 기본 build가 CUDA12.8,
dependency가 Torch2.7.0이다. CMake에는 CUDA compiler12.8 이상일 때 SM12.0이
포함된다. 따라서 구형 protocol 유지용 **조사 후보**는 존재한다. 다만 이 근거는
RTX5090에서 특정 model/quantization kernel의 성공이나 VRAM fit을 입증하지 않는다.
[v0.9.2 structured output](https://docs.vllm.ai/en/v0.9.2/features/structured_outputs.html),
[GPU 설치 문서](https://docs.vllm.ai/en/v0.9.2/getting_started/installation/gpu.html),
[Torch dependency](https://github.com/vllm-project/vllm/blob/v0.9.2/requirements/cuda.txt),
[SM120 build 정의](https://github.com/vllm-project/vllm/blob/v0.9.2/CMakeLists.txt#L84)

API 필드 보존만을 이유로 RTX runtime을 오래된 버전에 고정하지 않는다. 현장
driver/OS와 SM120·선정 모델·quantization에 맞는 runtime을 고른 뒤 dialect를
설정하는 방식이 작은 변경으로 runtime 선택의 여지를 보존한다.

두 payload와 unknown dialect 거절·자동 fallback 부재는
[fake HTTP 회귀](../tests/test_local_model.py)로 검증하며, 실제 선택은 run manifest에
기록한다. A100 legacy 경로에는 실제 평가 근거가 있지만 modern payload의 fake 서버
검증만으로 RTX 서버의 grammar 적용을 입증하지 않는다. RTX 사용이 가능해지면
해당 서버의 허용 **physical GPU1**에서 사전 예산
검사를 거쳐 실제 modern protocol 통합을 검증해야 한다. pin한 버전의 요청 계약과
backend 설정을 확인하고 실제 schema/tokenizer compile, 제약이 적용되는 응답,
지원하지 않는 제약의 거절, 동일 synthetic 의미 회귀를 함께 확인한다. 기존 A100
성공이나 fake HTTP 테스트를 RTX 실측으로 표시하지 않는다.

아래14B의 dense Marlin 검토와30B-A3B의 MoE backend 검토는 별개다. 현재 MoE 후보의
정적 SM120 근거, 명시적 expert backend 및 emulation 금지 조건은
[MoE 후보 검토](moe_instruction_candidate.md)를 따른다. 어느 쪽도 RTX 현장 실행
또는 설치 가능한 dependency lock이 확정됐다는 뜻은 아니다.

## Qwen3-14B-AWQ의 RTX5090 실행 가능성 — PREDICTED_UNVERIFIED

동일 [공식 checkpoint manifest](../runtime/models/qwen3-14b-awq.json)의 W4A16을
RTX 후보로 유지할 **소스 수준 근거가 있다**. RTX에서 startup·inference·품질·peak는
모두 미측정이다. NVIDIA 표에서 RTX5090은 **SM12.0**, B200/GB200은 **SM10.0**으로
구분된다. 데이터센터 Blackwell 지원을 RTX 성공 근거로 대신 사용하지 않는다.
[NVIDIA compute capability 표](https://developer.nvidia.com/cuda/gpus)

- v0.29.0 registry에 `Qwen3ForCausalLM`이 명시되어 있다.
  [architecture registry](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/model_executor/models/registry.py#L200)
- Marlin build는 FP16/BF16 output 모두 CUDA13 이상에서 `12.0f`, 그 아래에서
  `12.0a;12.1a`를 명시한다. SM120에 대한 직접 근거다. Kernel generator에도
  RTX5090/SM120 구분과 AWQ-INT4 타입이 존재한다.
  [Marlin CMake](https://github.com/vllm-project/vllm/blob/v0.29.0/CMakeLists.txt#L609),
  [kernel generator](https://github.com/vllm-project/vllm/blob/v0.29.0/csrc/libtorch_stable/quantization/marlin/generate_kernels.py#L18)
- AutoAWQ는 FP16/BF16 activation을 지원하며, Marlin 검사에는 unsigned INT4 +
  runtime zero-point와 group128이 포함된다. 이는 checkpoint의 4bit/group128/
  zero-point 설정과 맞는다. 최종 layer shape와 실제 kernel load 검증은 남아 있다.
  [AutoAWQ config](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/model_executor/layers/quantization/auto_awq.py#L172),
  [지원 타입/그룹 검사](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/model_executor/layers/quantization/utils/marlin_utils.py#L36),
  [Marlin layer 검사](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/model_executor/kernels/linear/mixed_precision/marlin.py#L35)

v0.29.0에서는 `awq`, `awq_marlin`, `auto_awq`가 모두 AutoAWQConfig로 연결된다.
따라서 A100의 `awq_marlin` log와 이름만 같은 설정을 현대 runtime의 동일 kernel
증거로 보지 않는다. RTX 검증 후보는 해당 checkpoint + `--dtype half` +
`--linear-backend marlin`이며, 실제 선택된 `MarlinLinearKernel` log를 확인해야 한다.
`VLLM_MARLIN_INPUT_DTYPE`로 INT8/FP8 activation을 추가 선택하지 않아 W4A16을
유지한다. Linear backend 선택은 layer 종류에 따라 fallback할 수 있으므로 flag만으로
모든 layer의 kernel을 보장하지 않는다. 이는 앞 절의 **JSON grammar backend**와
서로 다른 설정이다.
[quantization alias](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/model_executor/layers/quantization/__init__.py#L139),
[linear backend 선택](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/model_executor/kernels/linear/__init__.py#L780)

v0.29.0의 다음 **공식 x86_64 wheel**을 metadata만 조사했다. 두 파일 모두
`cp38-abi3-manylinux_2_28`이지만 실제 `Requires-Python`은 **>=3.10,<3.15**다.
Python3.12는 이 범위 안이다. CUDA129/130 wheel의 ZIP central directory와 METADATA만
HTTP Range로 각각 628,852/628,812bytes 읽었으며 전체 wheel이나 weight는 받지 않았다.

| 배포 | 공식 asset | 전체 bytes | 게시 SHA256 |
|---|---|---:|---|
| CUDA12.9 | [0.29.0+cu129 wheel](https://github.com/vllm-project/vllm/releases/download/v0.29.0/vllm-0.29.0%2Bcu129-cp38-abi3-manylinux_2_28_x86_64.whl) | 548,493,389 | `22e8d8fec755986b3ad964004a1f8c65a55626ec948354bdbe95993e6b0289fe` |
| CUDA13.0 default | [0.29.0 wheel](https://github.com/vllm-project/vllm/releases/download/v0.29.0/vllm-0.29.0-cp38-abi3-manylinux_2_28_x86_64.whl) | 315,961,042 | `09d48617fc2be9c6cdcd5db480651ab0d84817b257204f2cc2e3ecbb70bbb635` |

게시 digest는 [공식 release API](https://api.github.com/repos/vllm-project/vllm/releases/tags/v0.29.0),
Python 범위는 실제 METADATA 및 [PyPI metadata](https://pypi.org/pypi/vllm/0.29.0/json)로
교차 확인했다. 실제 wheel METADATA는 torch2.13.0, torchaudio2.11.0,
torchvision0.28.0, transformers>=5.10.4, xgrammar>=0.2.1,<1.0.0,
flashinfer-python0.6.18을 요구한다. **Resolver/pip check/import는 수행하지 않았으므로
이 목록은 설치 성공 lock이 아니다.** RTX host driver/OS/ABI 확인 후 build를 선택하고
dependency 정합성을 별도로 검증한다. A100의 cu118 환경을 대체하지 않는다.

기존 AWQ weight9.292GiB와 context4096/seq1/FP16 KV640MiB는 용량 산술의 출발점일
뿐, 현대 runtime의 workspace·repack·CUDA context·allocator·startup peak는 추가다.
RTX32GB에서 모델 전체 BF16을 기본 대안으로 잡지 않고 W4A16과 실제 free VRAM 및
안전 margin을 검증한다. A100 peak를 RTX peak로 복사하거나 최신 wheel의 존재를
공통 모델 최종 선정/RTX gate 통과로 표시하지 않는다.

## 부록: thinking 선택 시 modern V1 경로 — PREDICTED_UNVERIFIED

2026-09-20 KST에 **v0.29.0 태그의 공식 문서·소스만** 추가 조사했다. 설치,
GPU 접근, RTX5090 실행은 하지 않았다. 아래는 A100 thinking 실험이 최종 선택될
경우의 호환성 근거이며 모델 품질 gate 통과나 RTX runtime 선정 결과가 아니다.

| 항목 | A100 v0.8.5 실험 설정 | RTX v0.29.0 조사 후보 |
|---|---|---|
| Engine | V0 | V1 |
| Server reasoning 옵션 | `--enable-reasoning --reasoning-parser deepseek_r1` | `--reasoning-parser qwen3` |
| JSON grammar | 요청 `guided_json` + `xgrammar:no-fallback` | 요청 `structured_outputs.json` + server `--structured-outputs-config.backend=xgrammar` |
| 요청 모드 | `chat_template_kwargs.enable_thinking=true` | 같은 공통 필드에 명시적 `true` |
| 응답에서 폐기할 reasoning 필드 | `reasoning_content` | `reasoning` |
| 실행 근거 | A100 실험 결과를 별도로 평가 | **PREDICTED_UNVERIFIED** |

v0.29.0의 engine/launcher CLI에는 구형 `--enable-reasoning` 등록이 없다.
`--reasoning-parser qwen3`가 parser를 선택하므로 A100 명령 전체를 복사하지 않는다.
이는 해당 태그의 CLI 정의를 읽은 결과이며 RTX에서 CLI를 실행한 검증은 아니다.
[Engine argument 정의](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/engine/arg_utils.py),
[Server argument 정의](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/entrypoints/launchers/cli_args.py)

공식 지원 표는 Qwen3의 `qwen3` parser와 JSON/regex 구조화 출력을 함께 명시한다.
V1 `StructuredOutputManager`는 요청의 template kwargs를 반영한 parser를 만들고,
reasoning 종료 전에는 grammar mask 적용과 grammar 상태 진행을 보류한다. 종료가
확인되면 최종 출력에 제약을 적용한다. 따라서 **V0 전용이라는 v0.8.5 제한을
v0.29.0에 그대로 적용할 근거는 없다**. 이 연결은 소스 수준 근거이며 해당
checkpoint·tokenizer·schema 조합의 실제 성공은 별도 확인해야 한다.
[Qwen3 지원 표](https://docs.vllm.ai/en/v0.29.0/features/reasoning_outputs/#supported-models),
[V1 reasoning/grammar 전환](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/v1/structured_output/__init__.py)

`structured_outputs_config.enable_in_reasoning`은 **false 기본값을 유지**한다.
이 값을 true로 바꾸면 reasoning 중에도 grammar가 적용되므로, 내부 thinking 후
최종 semantic JSON을 만드는 목적과 다르다. 공식 structured-output 문서의
Qwen3 **Coder** 예외를 현재 일반 Qwen3-14B-AWQ에 옮겨 적용하지 않는다.
[Config 기본값](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/config/structured_outputs.py),
[Structured output의 reasoning 안내](https://docs.vllm.ai/en/v0.29.0/features/structured_outputs/#reasoning-outputs)

Modern `qwen3` parser는 `enable_thinking=false`를 읽고 reasoning 없이 전체 출력을
최종 content로 처리하는 경로와 공식 회귀 테스트가 있다. 따라서 0.8.5의
deepseek_r1 + false 비호환을 modern Qwen3에도 적용하지 않는다. 다만 현재
NeuroBuild 평가 harness의 client/server mode 일치 요구는 **보수적인 실험 정책**으로
유지한다. 향후 한 modern 서버에서 두 모드를 섞으려면 server parser 활성화와
요청 thinking 여부를 별도로 기록하고 그 조합을 검증해야 한다. 지금은 이 정책이나
코드를 변경하지 않았다.
[Qwen3 parser](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/parser/qwen3.py),
[Non-thinking 공식 테스트](https://github.com/vllm-project/vllm/blob/v0.29.0/tests/reasoning/test_qwen3_reasoning_parser.py)

응답 필드가 modern에서는 `reasoning`으로 바뀌지만 공통 client는 `message.content`만
선택하므로 reasoning 필드명에 따른 business logic 분기가 필요하지 않다. 두 필드의
원문을 로그·artifact·exception에 보존하지 않고 최종 content의 finish reason,
크기, think tag, schema, grounding 검증을 유지한다. Modern의 별도
`thinking_token_budget`/`include_reasoning` 옵션은 이 조사로 자동 도입하지 않는다.
이를 추가하면 별도 설정·manifest·회귀 검증이 필요하다.
[Modern 요청·응답 계약](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/entrypoints/openai/chat_completion/protocol.py)

SM120 Marlin 지원 근거는 앞 절의 weight/kernel 조사와 별개로 결합해야 한다.
Reasoning/parser의 존재는 RTX5090의 driver/ABI, attention·quantization kernel,
startup/inference peak 또는 한국어 의미 정확도를 보장하지 않는다. RTX에서는
physical GPU1만 예산 검증 후 사용하고, V1 프로세스·socket·종료 보호도 현장에서
검증한다. 공통 client의 `enable_thinking`·schema·parser·승인 경계는 유지하고
`qwen3` parser 이름은 runtime 설정/metadata에만 둔다. 실제 통합에서는 final-only
반환과 reasoning 미보존, reasoning 종료 후 JSON 제약, truncation/미완료 거절,
동일 synthetic 의미 회귀를 확인해야 하며 A100 실측 수치를 대입하지 않는다.
