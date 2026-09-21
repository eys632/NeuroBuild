**독립 CPU 검토: 현재 고정된 조건에서 preflight PASS**

모델은 기존 공식 `Qwen/Qwen3-32B-AWQ`, revision
`0499c3ac83fdef8810b907a23894ba91e95eddd8`이다. 모델 호출·weight 읽기·새 환경 설치 없이
기존 client, 실제 tokenizer와 설치된 vLLM source를 확인했다.

최종 prompt의 변경은 첫 줄의 두 출력 형식 문장에 `최종 content` 범위를 명시한 것뿐이다.
역치환하면 기존 generation2/v2 prompt와 byte가 동일하며 두 번째 줄 이후 정책·7개 예시도
byte가 동일하다. Canonical parser, 2.0 adapter를 포함한 application module, client,
evaluator, 기존 prompt/schema 및 launcher는 실패 checkpoint `0fd60350...` 대비 byte
불변이다. 전체 346개 테스트를 다시 수행했다고 주장하지 않는다.

Actual client fake capture 200개에서 single 2.0 계약, legacy guided JSON,
`xgrammar:no-fallback`, `enable_thinking=true`, 전체 출력1024/timeout120을 확인했다.
Sampling은 T0.6, top_p0.95, top_k20, min_p0, presence1.5, frequency0, repetition1,
seed42를 모두 명시한다. Fake response의 두 reasoning 필드는 Completion에 남지 않았고
허용한 숫자 usage만 유지됐다. 별도 synthetic 3경로에서 length 종료, final content 부재,
final content의 think tag를 기존 오류 코드로 거절했다. Reasoning fixture는 일시 메모리의
불투명 marker일 뿐 실제 모델 추론이 아니며 envelope와 marker를 저장하지 않았다.

실제 tokenizer metadata 5개 파일의 크기·SHA가 공식 pinned manifest와 일치한다. 별도
`chat_template.jinja`는 없고 tokenizer_config의 template를 정확히 사용한다.
Thinking=true는 `<|im_start|>assistant\n`까지만 넣으며 자동 `<think>` 시작 문구를 추가하지
않는다. False 요청에서만 들어가는 빈 think block을 true 요청에 붙이지 않았다.
최대 입력2923 + 전체 출력1024 = **3947/4096**이다. V2 80개는 입력 길이만 측정했고
본문·gold·사례별 정보는 공개하지 않았다.

기존 branch schema를 xgrammar0.1.18로 실제 compile했고 7개 예시 모두 token/EOS와
2.0→1.0 parsing을 통과했다. Backend는 그대로 유지되며 grammar 통과가 의미 정확성이나
조건의 완전성을 보장한다는 주장은 하지 않는다.

설치된 vLLM source의 다음 경로를 읽고 hash를 proof에 남겼다.

1. `engine/arg_utils.py`는 reasoning 활성화 때만 parser를 decoding config에 연결하고,
   V0 engine은 그 값을 guided-decoding builder에 전달한다.
2. Builder가 `deepseek_r1` 인스턴스를 xgrammar processor에 넘긴다. 현재 registry에는
   `qwen3` parser가 없으므로 이 환경에서 해당 이름을 대체 사용하지 않는다.
3. 실제 `XGrammarLogitsProcessor.__call__` AST를 격리 실행한 CPU probe는 종료 marker
   전에는 scores를 그대로 반환하고 marker 뒤에는 grammar 초기화로 진입함을 확인했다.
   실제 GPU logits processor를 실행한 검증은 아니다.
4. 설치된 DeepSeek parser의 실제 메서드를 추출한 4개 split probe와 2개 marker probe도
   통과했다. 종료 marker 또는 최종 내용이 없으면 content가 None이고 client는 이를
   유효한 최종 답변으로 받아들이지 않는다. Chat serving은 reasoning_content와 content를
   분리하며 client는 final content만 반환한다.

기존 14B v6/v7 thinking 진단은 동일 vLLM0.8.5+cu118/deepseek_r1 및 guided JSON으로 각각
40개 schema-valid 최종 결과를 남겼다. 이력의 manifest/results hash와 요약 수치만 proof에
연결했다. 이는 실제로 실행된 legacy protocol 근거지만 32B thinking의 품질·완결성이나
이번 1024 예산을 검증한 결과는 아니다. 기존 공식 소스 근거는
[디코딩 검토](../../../../docs/qwen3_decoding_review.md)에 있으며 이번에는 설치 source를
직접 확인했다. 해당 과거 문서의 당시 미구현 상태 서술은 현 client 상태 설명으로 사용하지 않는다.

Runtime 실제 기동에서는 `VLLM_USE_V1=0`, `--enable-reasoning`,
`--reasoning-parser deepseek_r1`를 함께 명시해야 한다. 이 0.8.5 parser 서버에 non-thinking
요청을 혼용하지 않는다. Loopback, request/access logging 비활성화, 기존 GPU3 guard,
single sequence/context4096/KV256 및 자원 제한은 parent의 별도 기동 검증 대상이다.

이번 비교는 thinking·sampling·출력 지시 범위·cap이 함께 바뀐다. 실패가 특정 원인 하나를
입증하거나 reasoning 전체의 한계를 뜻하지 않는다. 잘림·timeout·final JSON 부재와
unknown raw decision을 원래 분모의 실패로 보존하고, 재시도·repair·gate 완화 없이 평가한다.
CPU PASS 뒤에도 actual startup, 새 freeze와 고정 exposed 진단이 남는다. RTX 실행과
최종 모델 선정은 검증되지 않았다.
