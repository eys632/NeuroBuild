# Native Qwen3.8 exposed 진단 사전 계획

Phase5.x에서 `qwen38-gguf-raw-unicode-v1` 후보를 한 번 비교한다. 실제 GPU startup과 공개
문맥 자원 검사를 통과하고 그 증거와 실행 조건을 동결·commit·push한 뒤에만 시작한다.
기존22개 완료 실험 기록과 분모는 그대로 유지한다. 이 문서는 아직 모델 평가를 실행한 증거가 아니다.

모델은 ggml-org/Qwen3.8-27B-GGUF revision efbb3b1f70a21d97fd4495240648405f7228554f의
Q4_K_M이다. llama.cpp f072b103714dfa1eee531f80b24512faf38e3dd2, GPU3/internalCUDA0,
ctx4096/seq1/batch1/ubatch1/F16KV/flashoff/graphsoff/fitoff 조건을 고정한다.
공식 HF NFC 동등성은19/20 FAIL이며 원문을 그대로 처리하는 별도 native 후보다. 이 차이는
startup proof와 그 SHA를 가진 runtime metadata, quality freeze에 명시한다. 입력/출력 정규화,
인용 보정, parser 완화는 없다. V2 모델 호출은 이번 노출 자료 진단에서 수행하지 않는다.

단일 generation2.0, 기존 prompt requirement_generation_v2_v2와 decision-branch schema를
사용한다. Native JSON-schema protocol, sampling qwen38_nonthinking_llama_cpp,
T0.7/P0.8/K20/minP0/seed42/presence0/frequency0/repeat1/window0,
samplers temperature→top_k→top_p→min_p, thinkingfalse/deepseek를 고정한다.
Completion768/timeout120초/동시성1/자동 retry0다. Public smoke와 자원 probe는 평가 분모에서
제외한다. 모델·양자화·runtime·sampling이 함께 바뀌므로 단일 변경의 인과효과를 주장하지 않는다.

이미 노출된 requirement_hardening_v1_exposed_regression120개를 원래 순서대로1회 실행하고
기존5 warmup을 제외한다. 실제 평가125호출, gold READY62/non-READY58이다. 모든 오류·
잘림·unknown은120개 분모에 남는다. Raw READY는 schema/quote/parser 거절 전에 관측한다.
Gate는 schema120/120, semantic≥114/120, raw READY FP0/58, unsafe accepted READY0/120이다.
Fail이면 모델 채택이나 Phase6 진행을 하지 않고 실제 실패 증거를 검토한다.

기존 scorer와 canonical parser/quote adapter를 사용한다. Metadata는 실제 native source/
build/GGUF/template/launch/listener/startup hashes를 담으며 Torch/vLLM 버전을 대신 쓰지 않는다.
Runtime 증거·source/prompt/schema/dataset hashes·sampling·원문 tokenizer 차이를 별도 freeze에
고정한다. 실행 전후 같은 own PID/startticks/argv/localhost와 guard 자원 조건을 확인한다.
결과는 독립 재생으로 집계와 안전 지표를 확인한 뒤 보존한다. Reasoning 원문은 보존하지 않는다.

이120개는 unseen이 아니다. V2 80개는 아직 모델 출력 미관측이며 root의 일부 입력/gold 노출
이력을 지우지 않는다. Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED다. 노출 진단 통과가
후속 반복/미관측 평가 또는 사람 검수를 대신하지 않는다. RTX5090은 미검증으로 유지한다.
