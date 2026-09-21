# GLM-4.7-Flash 공개 CPU 계약 검사 설계

**설계만 완료, 검사는 미실행이다.** 기존 모델의 200개 길이 입력, V2, 미사용 holdout 또는 평가 결과는 읽지 않는다.
다음 단계가 승인되면 새 GLM 전용 ignored 경로에 증거를 만들고 이전 Qwen/Gemma/EXAONE 실패와 helper는 보존한다.

1. **공식 tokenizer reference 20개.** `public_tokenizer_cases_design.json`의 고정 공개 문자열만 사용한다.
   기존 `.conda-vllm`의 `tokenizers.Tokenizer.from_file`로 pinned tokenizer JSON을 읽되 Transformers/Torch는 불러오지 않는다.
   `add_special_tokens=False`, decode `skip_special_tokens=False`를 명시한다. 원문 byte roundtrip, token ID 순서,
   added special token 인식, 한글·accent NFC/NFD, 공백·CRLF·literal U+2581·emoji·GLM marker를 각각 기록한다.
   현재 normalizer가 null이라는 정적 사실을 PASS로 바꾸지 않는다. 차이가 나면 원본 fixture/결과를 보존하고,
   normalization·문자열 치환·사례 삭제 없이 root가 의미와 다음 범위를 결정한다.

2. **공식 Jinja와 native full-system fidelity.** 원본 3120 B template를 고정하고 공식 Jinja2 reference와
   pinned f072 minja가 같은 공개 message 배열을 렌더한 전체 바이트를 대조한다. 최소 공개 matrix는 system+user,
   system 없음, 빈 system/user, multiple system, assistant history, reasoning history와 clear_thinking true/false,
   tools 없음/빈 배열/공개 schema, tool 결과, content text-parts, whitespace/Unicode, thinking true/false,
   add_generation_prompt true/false를 포함한다. 지원하지 않는 입력은 reference와 native의 거절 범위도 기록한다.
   Production profile이 고정되면 fake opener로 실제 client request를 잡아 전체 system 정책과 원래 public user
   JSON bytes가 공식 reference prompt에 정확히 들어가고 native 전체 prompt와 같은지 확인한다.
   길이가 짧아도 ‘정상’이라고 넘기지 않으며, 메시지 순서 변경·system을 user로 합치기·원문 repair는 하지 않는다.
   이 단계에서 기존 policy prompt, generation2 schema, parser의 바이트는 바꾸지 않는다.

3. **Native request→grammar→final JSON.** 기존 CPU static library 194개 정의/해시 inventory를 재검증한 후,
   새 translation unit만 같은 compiler flags로 compile/link할 수 있다. 원본 upstream/build/Qwen/Gemma/EXAONE binary는 불변이다.
   실행 전 ELF dependency가 CPU-only인지 검증하고 empty CUDA/RLIMIT_CORE0 및 stderr body 미보존을 강제한다.
   `common_chat_templates_apply`가 실제 OpenAI 호환 `response_format.json_schema`와 생각 비활성 설정을 해석하게 한다.
   `generation_prompt` 전체를 grammar에 prefill하고 branch/null/axis/extra-property의 기존 공개 10 accept/20 reject를 검사한다.
   Native generation grammar가 허용하는 출력과 `common_chat_parse`가 final content로 분리하는 문자열을 구분한다.
   Plain/fenced JSON, tool marker, 잘못된 branch, incomplete thought, artificial thought+final JSON의 지원/거절을
   실제 native parser로 확인하되 final JSON bytes를 임의로 trim/unwrap/repair하지 않는다. 별도 thought 본문은 저장하지 않는다.
   GLM의 prefix `</think>`를 사용자 출력으로 오인하거나 기존 모델의 parser enum을 그대로 가정하지 않는다.

4. **실제 GGUF는 별도 승인 후.** 다운로드 full SHA와 독립 header가 먼저 통과해야 한다.
   Header의 architecture/file type/dtypes/tokenizer/pretype/token IDs/template를 실제 관측하고 원본 current revision과의
   conversion gap을 닫거나 정확히 남긴다. 원본 API만으로 embedded parity를 주장하지 않는다.
   그 후 `vocab_only`, `no_alloc`, `LOAD_MODE_NONE`, empty devices, GPU layers0/MTP disabled로 새 CPU helper가
   실제 vocab을 읽도록 하고 model context/backend/tensor/decode는 생성하지 않는다.
   공식 공개20 ID·raw roundtrip, model-aware full prompt와 template/token-special behavior, per-token grammar+EOG를
   별도 검증한다. 지금은 이 후단 실행을 허용받지 않았다.

5. **Sampling과 길이.** 공식 일반 benchmark T1/P0.95와 프로젝트의 neutral extra parameter/order/seed를 구분한다.
   고정 production payload가 나온 뒤 native oaicompat 및 server sampler parser가 그 값을 인식하는지 확인한다.
   top-k0가 무효화라는 static source 해석만으로 실제 payload capture를 생략하지 않는다.
   품질용 output768/context4096은 프로젝트 제약이며 긴 benchmark completion과 동등하지 않다.
   평가 input 길이는 root의 별도 승인 이후에만 aggregate-only로 검사한다. 현재 200개 입력은 읽거나 재실행하지 않는다.

Relevant pinned source는 [native template](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/models/templates/GLM-4.7-Flash.jinja),
[chat.cpp](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/common/chat.cpp),
[differential analyzer](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/common/chat-diff-analyzer.cpp),
[PEG generator](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/common/chat-auto-parser-generator.cpp),
[conversion/base.py](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/conversion/base.py)다.
`chat.cpp:1296`는 schema를 입력하고, `:1334` 부근은 differential autoparser,
`:1432`는 template 적용, `:1439`는 final parse 경계다. Converter `:1588`의 GLM-4.7-Flash fingerprint
`cdf5f35325780597efd76153d4d1c16778f766173908894c04afc20108536267`는 `glm4` pretype으로 매핑된다.
현재 tokenizer에 이 fingerprint probe를 실행한 적은 없으며, 관련 source SHA는 `provenance.json`에 있다.

품질 gate/원문 인용/canonical 결정 계약은 그대로다. 이 계획의 어느 CPU PASS도 A100 최대 peak,
RTX5090 실행, 한국어 정확도 또는 모델 채택을 증명하지 않는다. 전체 weight/MoE expert 상주와 MLA/cache/workspace
자원 계획은 독립 resource 검토의 별도 조건이다.
