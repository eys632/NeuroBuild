# Native CPU contract validator 정적 검토

검토 결과: 발견한 grammar prefill 누락과 core dump 차단 누락을 수정했다. 최종 소스는 CPU build 단계로 진행할 수 있는 정적 상태이며 **compile, native 실행, grammar 통과, tokenizer 일치, 모델 품질은 아직 이 검토로 확인하지 않았다**. 본 검토에서는 build/실행 파일/모델/GPU/네트워크를 호출하지 않았고 v2 입력·골드를 읽지 않았다.

## 범위와 수정

- 고정 llama.cpp `f072b103714dfa1eee531f80b24512faf38e3dd2`의 CMake, server request parser, grammar sampler, chat parser 및 vocab-only load 경로를 대조했다. upstream source는 수정하지 않았다.
- 중요한 오류: Qwen3-Coder 계열 parser의 output-format grammar는 assistant 시작 부분을 포함한다(`common/parsers/qwen3-coder.cpp:75`). 실제 sampler는 `generation_prompt` 토큰을 먼저 소비한다(`common/sampling.cpp:280–309`). 이전 helper는 bare JSON만 native grammar에 넣어 정상 응답도 거절할 수 있었다. 현재 문자 검사는 `generation_prompt + JSON`을 넣으며, optional audited vocab 검사는 같은 prefill 토큰과 output token apply/accept/EOG를 사용한다. Prefix 및 output token-piece roundtrip도 같아야 한다. 이는 공개 고정 corpus의 한 tokenization 경로 검사이며 모든 가능한 tokenization을 증명하지 않는다.
- `common_chat_parse`는 자체적으로 generation prompt를 붙인다(`common/chat.cpp:1457` 근처). 그러므로 final parser에는 JSON만 넣고 content가 원문 JSON과 같은지 확인하는 기존 흐름을 유지했다. 이중 prefix를 넣지 않는다.
- 입력을 읽기 전에 `setrlimit(RLIMIT_CORE,{0,0})` 실패 시 종료하도록 수정했다. 외부 invocation wrapper도 같은 제한을 설정한다.
- Root 요청으로 optional metadata-tokenizer parity 배열 최대32개를 추가했다. Public synthetic fixture 생성기는 tokenizers만 사용하고, actual native 비교는 별도 vocab-only 실행에서만 수행한다. ID는 fixture에만 존재하며 validator/report stdout은 count/status만 출력한다.

## CPU 경계와 build runner

`CMakeLists.txt`는 static build, CPU ON, backend dynamic loading OFF이며 CUDA/HIP/MUSA/SYCL/Vulkan/Metal/OpenCL 등 GPU 경로와 OpenMP fetch/LLGUIDANCE/OpenSSL/subprocess/UI를 끈다. Runner는 CANN도 명시적으로 OFF로 고정한다. 고정 GCC/G++ 9.5.0와 CMake를 사용하며 `nb-native-contract-validator` target만 build한다. Server CMake를 include해도 전체 `all`, UI asset, install target을 요청하지 않는다.

Runner는 bootstrap/source Git blob 검증, compiler/CMake/helper pins, generated cache/compile commands 검증, build 전후 source 및 helper hash 확인, 20GiB reserve/3GiB 자체 build budget/parallel2/30분 제한을 연결한다. 수정된 cache parser는 한 줄마다 해석하고 duplicate key와 GPU compiler 설정을 거절한다. 이 검토에서는 runner main을 실행하지 않았다. 실제 build 이후 ELF NEEDED allowlist와 RPATH/RUNPATH 부재 확인은 **실행 전 필수 단계**이며 CMake 설정만으로 최종 링크 성공을 주장하지 않는다.

CPP는 backend init/context/decode 함수를 호출하지 않는다. Optional GGUF 경로는 empty device list, `n_gpu_layers=0`, `vocab_only=true`, `no_alloc=true`, `load_mode=NONE`을 사용한다. 고정 source `src/llama.cpp:158`의 명시적 device 경로와 `:364`의 vocab-only 반환은 GPU 열거와 tensor load 이전 경로다. Optional 실행은 full SHA/header audit 후 parent wrapper가 정확한 model/proof/path를 연결해야 한다. 실행하지 않은 상태에서 GGUF/template 실제 일치나 context 적합을 PASS로 기록하지 않는다.

## Grammar·로그·호출 계약

- 실제 `oaicompat_chat_params_parse`가 만든 grammar와 `json_schema_to_grammar(schema,true)`를 각각 검증한다. 기존 decision-branch schema의 anyOf/null/additionalProperties 거절을 공개7개 예시와 추가 positive/negative synthetic corpus에서 실행할 준비를 했다. 현재 wrapper corpus는 허용10/거절20이며 JSONSchema 라벨 확인 후 전달한다. Backend nonempty/grounding/의미 검증은 grammar 통과와 별도다.
- Native scalar schema parser로 T=.7/P=.8/K=20/minP=0, presence/frequency=0, repeat=1/window=0, seed42/output768 및 `temperature,top_k,top_p,min_p` 순서를 확인한다. 이는 별도 native neutral-penalty recipe이며 vLLM sampling 등가성이나 model-card presence1.5 준수를 주장하지 않는다.
- Actual client payload의 `reasoning_format` 생략을 허용하고 server option DEEPSEEK를 검사한다. 필드가 존재하면 deepseek만 허용한다. Thinking=false, stream=false, tool 없음, eager nonempty grammar/trigger 없음도 확인한다.
- Converter는 silent callback 밖에서 `fprintf(stderr)`로 incomplete warning을 출력한다(`common/json-schema-to-grammar.cpp:980`). CPP는 stderr pipe에서 byte수만 세고 내용을 버리며 한 byte라도 있으면 FAIL한다. Prompt/grammar/exception.what()/token/body는 출력하지 않는다. Common/native 로그도 끈다. Raw stderr 텍스트나 reasoning을 artifact로 남기지 않는다.
- Root public invocation helper는 fake opener를 쓰고 실제 HTTP를 호출하지 않는다. ELF allowlist, pinned inputs, core0, empty CUDA, 180초 timeout 뒤 고정 JSON 결과만 보존한다. 실제 child stderr가 발생하면 실패하며 원문을 출력하거나 저장하지 않는다. 본 검토의 그 helper 호출 횟수는 0이다.

## 남는 한계

CPP는 자체적으로 argv metadata/model 경로의 no-follow/소유권/SHA/TOCTOU를 모두 검증하지 않는다. 외부 wrapper의 owned-path와 immutable audit 증거가 전제다. Context 최대 길이는 실제 audited vocab-only 실행 전에는 미측정이다. Public grammar/tokenizer 검사는 inference·조건 판단·target scope 정확성의 증거가 아니다. 향후 v2 context 검사에서도 입력은 메모리에서만 전달하고 aggregate count/min/max만 보존해야 한다.

## 고정 대상

- `var/research/native-contract-validator/validator.cpp`: `19921771c0f559268868d01ec5327ab859e35c379e727841cb11b6d58a82bb42`
- `var/research/native-contract-validator/CMakeLists.txt`: `9dede1e5ac9ee2f9b46f81e655e801e1b3ac2a57132dece6291cd9bb5f9860b5`
- `var/research/prepare_native_tokenizer_parity.py`: `dbcf5505161469ad02e5e3826634c93ac9e30961fc04e7164b82d949c1dc8165`
- 정적 검토한 runner는 verifier `81285c40d1ee3862f747bbbc32fc9868d7a0604b4ea402dc8a8b5e9a1a06573e`와 위 최종 CPP를 연결해야 한다. Peer가 final CPP pin을 갱신 중이므로 runner 자체 최종 hash는 그 peer 증거를 사용한다.
- Python fixture/runner/invocation helper AST parse는 PASS. C++ syntax compile 및 executable 검증은 본 검토에서 실행하지 않았다.
