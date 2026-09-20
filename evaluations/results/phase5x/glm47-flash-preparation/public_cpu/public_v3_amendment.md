# GLM 공개 CPU v3: 실제 prefix에서 final-content 경계 검사

최초 FAIL `7eba381e…b5b43`은 실제 grammar에 다른 prefix를 붙여 reasoning 수용을 요구한 helper 오류였다. v2 FAIL `534f6aba…5ae01`은 실제 prefix로 되돌린 뒤 complete reasoning을 거절해야 한다고 가정한 두 번째 helper 오류다. 두 FAIL과 각 source/build/binary는 그대로 보존한다. v2가 stage70 / CPP309에서 실패했다는 것은 설정 prefix 뒤의 완결된 공개 thought 블록을 실제 grammar가 수용했다는 관측이다.

Pinned f072 `common/chat-auto-parser-generator.cpp:105–112`는 reasoning 추출 여부를 reasoning format과 감지된 template mode로 결정한다. `:120–125`의 response-format parser는 optional reasoning 뒤에 schema JSON 또는 json fence를 둔다. `:141–154`는 완결된 `<think>…</think>`를 optional로 만들며 이 분기에 `enable_thinking` 검사는 없다. `common/chat-peg-parser.cpp:869–877`은 generation prefix를 literal로 묶는다. `common/chat.cpp:1457–1459`는 **실제** `params.generation_prompt`를 입력 앞에 붙여 파싱한다. `common/chat-peg-parser.cpp:315–329`의 mapper는 reasoning/content를 각각의 필드로 옮긴다.

따라서 nonthinking 요청은 native grammar가 모든 reasoning 문법을 금지한다는 보장이 아니다. 제품의 계약은 final content의 정확한 JSON과 별도 reasoning 필드 폐기다. 이 계약을 새 `validator_v3.cpp`에서 측정한다. 실제 `<|assistant|></think>` prefix는 바꾸지 않고 complete public synthetic thought+JSON의 grammar 수용, 같은 `final_parser`를 통한 final JSON exact bytes, 별도 reasoning의 공개 marker exact bytes, tool call 0, OAI content 동일을 요구한다. 잘못된 prefix의 grammar 수용 여부는 scalar 관측만 남긴다. 모델이 thought를 생성했다거나 다른 runtime mode를 실행했다는 뜻은 아니다.

공개 marker 본문, parser input/output 또는 stderr는 artifact에 출력하지 않는다. scalar field와 hash만 남긴다. 기존 Jinja20/system/user/full prompt, sampling, 30schema, plain/fenced final20, bad-native4, optional official vocab 코드와 production/template/prompt/schema는 그대로다. `build_v3.py`/`public_check_v3.py`는 새 파일 이름을 사용하고 두 최초 FAIL 및 이전 source/binaries의 exact hash를 요구한다. 공식20 tokenizer fixture는 다시 실행하지 않는다.

이 수정은 실제 optional-reasoning 수용 관측과 native source 및 제품 요구에 근거한다. 아직 v3 compile/public parse는 실행하지 않았으므로 final boundary PASS를 주장하지 않는다. 실패하면 새 receipt로 보존한다. GGUF/길이200/모델 품질 실행은 이 작업에 포함되지 않는다.
