# 공개 CPU v2 기대값 수정 — 실행 전

원래 `public-proof.json`의 FAIL(SHA `7eba381e83c09f14d9dcfaf898e20dd02badc3cc02362ac5e8eab5d9eb9b5b43`)은 stage70 / CPP307이다. 설정된 nonthinking grammar를 만든 뒤 검사 코드만 generation prefix를 `<|assistant|>`로 바꾸고 synthetic thought 수용을 요구했다. 실제 native prefix는 앞선 assert가 확인한 `<|assistant|></think>`다. 이 FAIL을 원래 frozen 정의의 PASS로 바꾸지 않는다.

Pinned source `f072b103714dfa1eee531f80b24512faf38e3dd2`의 `common/chat-auto-parser-generator.cpp:37,64,79–81,133–134`는 실제 template의 generation prefix로 parser와 eager grammar를 함께 만든다. `common/chat-peg-parser.cpp:869–877`의 `prefix()`는 이 문자열에서 reasoning 시작 delimiter 전까지를 literal로 고정한다. GLM nonthinking suffix에는 `<think>` 시작 태그가 없으므로 닫힌 prefix 전체가 남는다. 따라서 helper가 prefix만 바꾸어 검사한 positive 요구는 실제 production 경로와 다르다.

별도 `validator_v2.cpp`는 그 positive parse 요구를 제거하고 **동일한 설정 prefix 뒤의 complete synthetic thought를 grammar가 거절하는지** 검사한다. Native parser가 다른 thinking-mode에서 무엇을 지원하는지는 이 후보 gate에 포함하지 않는다. 공개 JSON 30개, plain/fenced grammar와 final JSON exact bytes, 전체 system/user/Jinja20, native sampler, optional vocabulary 루프는 유지한다. 이 단계에서 configured-prefix rejection은 아직 실행 전 기대값이며, 실패한다면 새로운 FAIL receipt를 보존해야 한다. 원래 실패가 이 수정의 성공을 미리 증명하지 않는다.

Root가 이미 실행한 공식 tokenizer reference20/raw20와 added literal36, 첫 compile PASS는 원래 산출물로 그대로 보존한다. v2는 tokenizer fixture를 재생성하지 않고 SHA로만 묶는다. `build_v2.py`는 새 TU/object/binary/report/log를 만들며 기존 194 objects와 원래 GLM binary까지 전후 확인한다. `public_check_v2.py`는 새 build와 새 output 이름만 사용하고 최초 실패·원본 source·공식 fixture를 필수 pin으로 확인한다. 기존 source/template/prompt/schema/client와 실제 모델 설정은 변경하지 않는다.

준비된 다음 명령은 이 문서 작성 시 실행하지 않았다.

```sh
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-glm47-contract/build_v2.py
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-glm47-contract/public_check_v2.py
```

GGUF vocabulary와 200개 길이 입력은 계속 별도 승인 및 실제 strict header PASS 이후다. 이번 작업은 신규 파일 작성과 source/AST/hash 대조만 수행했다.
