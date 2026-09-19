# Qwen3-14B-AWQ 디코딩 검토

2026-09-20 KST 조사. 공식 모델 카드·배포 문서와 설치된 vLLM 0.8.5 소스를 읽었다. 설치, 모델 호출, GPU 접근, production 소스 변경은 하지 않았다. 아래 설정은 **실험 후보이며 미검증**이다. Development v3/v4 실패를 temperature, AWQ 또는 grammar 한 가지 원인으로 단정할 근거는 없다.

## 공식 권고와 현재 설정

| 모드 | temperature | top_p | top_k | min_p |
|---|---:|---:|---:|---:|
| Qwen 공식 non-thinking 권고 | 0.7 | 0.8 | 20 | 0 |
| Qwen 공식 thinking 권고 | 0.6 | 0.95 | 20 | 0 |
| 현재 NeuroBuild non-thinking | 0 | greedy에서 1 | greedy에서 -1 | 0 |

모델 카드의 “DO NOT use greedy decoding” 문장은 **thinking 설정 항목**에 있다. Non-thinking도 sampling 값을 권장하지만, 해당 문장을 모든 non-thinking greedy 사용의 금지나 현재 퇴행 원인의 증명으로 확대하면 부정확하다. AWQ 카드에는 quantized model의 `presence_penalty=1.5` 권고도 있으며, 큰 penalty가 언어 혼합이나 성능 저하를 일으킬 수 있다는 단서가 있다. [Qwen3-14B 카드](https://huggingface.co/Qwen/Qwen3-14B#best-practices), [Qwen3-14B-AWQ 카드](https://huggingface.co/Qwen/Qwen3-14B-AWQ#best-practices).

현재 client는 `temperature=0`, `seed=42`, `enable_thinking=False`를 명시한다. 설치된 vLLM의 `SamplingParams.__post_init__`은 temperature가 greedy 기준보다 작으면 top_p=1, top_k=-1, min_p=0으로 바꾼다. 따라서 checkpoint의 `generation_config.json`에 top_k=20/top_p=.95가 있어도 현 T0 실행이 그 sampling 조합을 사용한 것은 아니다. Request에서 생략한 값은 model generation config/default를 상속할 수 있으므로 향후 비교에서는 모든 sampling 값을 명시한다. [공식 SamplingParams](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/sampling_params.py#L378), [공식 요청 변환](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/entrypoints/openai/protocol.py#L453).

## vLLM 0.8.5의 실제 경로

Qwen 배포 문서는 0.8.5에서 `--enable-reasoning --reasoning-parser deepseek_r1`을 사용하며, `qwen3` parser는 0.9.0부터라고 명시한다. 특히 **0.8.5의 reasoning parser와 `enable_thinking=False`는 호환되지 않는다**고 경고한다. 현재 non-thinking 서버에 reasoning parser를 켜지 않은 것은 이 안내와 일치한다. [Qwen 배포 안내](https://qwen.readthedocs.io/en/latest/deployment/vllm.html#parsing-thinking-content).

vLLM 0.8.5 공식 문서는 reasoning+structured output을 **V0 engine에서만** 지원한다고 설명하며 `VLLM_USE_V1=0`을 요구한다. 지원 표에는 DeepSeek/QwQ가 나오고 Qwen3 자체는 없다. Qwen3-AWQ에 `deepseek_r1`을 쓰는 근거는 별도의 Qwen 공식 모델 카드와 배포 안내다. 두 문서의 범위를 혼동하지 않는다. [vLLM 0.8.5 reasoning+structured output](https://docs.vllm.ai/en/v0.8.5/features/reasoning_outputs.html#structured-output), [Qwen AWQ Quickstart](https://huggingface.co/Qwen/Qwen3-14B-AWQ#quickstart).

로컬 설치 소스에서 다음 경로를 확인했다.

1. `EngineArgs.create_engine_config`가 enable_reasoning일 때 reasoning_parser를 decoding config에 넣는다. V0 `AsyncLLMEngine`은 guided-decoding builder에 그 값을 전달한다.
2. Builder는 `ReasoningParserManager`에서 `deepseek_r1`을 생성하고 XGrammar logits processor에 전달한다. 현재 registry에는 deepseek_r1/granite가 있으며 qwen3는 없다.
3. XGrammar processor는 `</think>`가 생성되기 전에는 grammar mask를 적용하지 않고, 종료 후 JSON mask를 적용한다. Reasoning 본문은 schema 제약 대상이 아니다.
4. Chat serving은 완료 결과를 `reasoning_content`와 최종 `content`로 분리한다. DeepSeek parser는 종료 marker가 없으면 content=None을 반환한다. 이 경우 현재 client는 유효한 완료 응답으로 수용하지 않는다.

[공식 guided-decoding builder](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/model_executor/guided_decoding/__init__.py#L98), [XGrammar 전환 조건](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/model_executor/guided_decoding/xgrammar_decoding.py#L346), [DeepSeek parser](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/reasoning/deepseek_r1_reasoning_parser.py), [Chat serving 분리](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/entrypoints/openai/serving_chat.py#L938).

위 경로 중 아래 6개 로컬 파일은 작은 공식 raw source를 메모리에서 받아 **v0.8.5 태그와 byte 단위 동일함**을 확인했다. GPU 모듈을 import하지 않았다.

| `vllm/` 아래 경로 | SHA-256 |
|---|---|
| `model_executor/guided_decoding/xgrammar_decoding.py` | `c65607b1a9211d7559a90dd0ad606d54ae00718565bd26b148642aa38d032642` |
| `model_executor/guided_decoding/__init__.py` | `4e9149a04578b6250e247deaddf2dc479a370509d4b4f11f30b33290c28a89d9` |
| `reasoning/deepseek_r1_reasoning_parser.py` | `a21a4857ab368f47e16b7626bb12955051598e2aef4edabc4c64ece6bf6a90ce` |
| `reasoning/__init__.py` | `9e2a22026f7c072f46603d54d820a3d308302e939c781a22392eee99dca591c0` |
| `sampling_params.py` | `c8fef374c69c75c01f77ff35913a255ae92231bf5363a41a692fced66f10b308` |
| `entrypoints/openai/protocol.py` | `41035c9a6fb42af1e78049511008f29ff0009bf97ca94284fe774d78a9929937` |

## 제한된 비교 순서

먼저 같은 T0/non-thinking/schema/checkpoint에서 간결한 v5 prompt를 development 전체에 적용해 prompt 변경 효과를 분리한다. 40개 1회 진단은 빠른 방향 확인이며 3회 평가나 holdout 통과를 대체하지 않는다. 실패한 v3/v4 run은 보존한다.

그다음 필요하면 **같은 prompt**의 별도 non-thinking sampling profile을 고정한다: temperature=.7, top_p=.8, top_k=20, min_p=0, presence_penalty=1.5, frequency_penalty=0, repetition_penalty=1, seed=42. 이는 공식 AWQ 권고를 출발점으로 한 비교이며 NeuroBuild의 최적값이나 성공 설정이 아니다. Penalty 영향도 따로 볼 경우 그 역시 사전에 고정한 별도 profile/run으로 기록한다. Sampling에서도 동일 seed 반복을 독립 확률 표본으로 세지 않는다.

Thinking 비교가 필요하다면 환경 upgrade 없이 검토 가능한 최소 조합은 다음과 같다. 기존 허용 GPU·TP1·loopback·V0·eager·단일 sequence·메모리 제한·watchdog는 유지한다.

```text
추가 server flags: --enable-reasoning --reasoning-parser deepseek_r1
request.chat_template_kwargs: {"enable_thinking": true}
temperature=0.6, top_p=0.95, top_k=20, min_p=0
presence_penalty=1.5, frequency_penalty=0, repetition_penalty=1, seed=42
guided_json=<기존 schema>, guided_decoding_backend="xgrammar:no-fallback"
stream=false, max_tokens=2048  # 아래의 제한된 실험 예산이며 공식 권장 길이가 아님
```

현재 launcher에는 위 reasoning flags가 없고 client는 thinking/temperature를 고정하므로 **설정·manifest·fake transport 검증을 추가하기 전 그대로 실행할 수 있는 profile은 아니다**. Server parser 없이 enable_thinking만 true로 바꾸면 처음부터 JSON grammar가 적용되어 의도한 reasoning→JSON 경로가 되지 않는다. 반대로 parser를 켠 서버에 false 요청을 섞는 것도 0.8.5에서 피한다. 자동 fallback은 추가하지 않는다.

로컬 tokenizer로 v5 SHA `ca51aee26257f734bcdbc9e375b681ee2058f823153c9311cdaa4c54b4086b8d`의 development40을 CPU/offline에서 계산했다. Thinking=true chat 입력 최대1258 tokens, 전체 출력2048을 더하면3306/4096이다. Torch 미import를 확인했다. 이는 **토큰 창에 들어간다는 확인**이며 reasoning 완료·latency·VRAM peak·품질 성공의 증거가 아니다. 공식 카드의 일반 출력 권고32768과도 다른 짧은 실험이다. 0.8.5 요청 모델에는 별도 thinking-budget 필드를 찾지 못했으며 max_tokens는 reasoning과 최종 답변의 합산 한도다.

## 추론 내용 미보존과 평가 경계

Thinking 실험에서는 server 내부와 HTTP 응답의 일시 메모리에 reasoning이 존재할 수 있다. 저장하지 않는다는 보장을 메모리에조차 존재하지 않는다는 뜻으로 표현하지 않는다. 현재 client는 envelope에서 final `content`만 Completion으로 반환하고 `reasoning_content`를 반환하거나 기록하지 않는다. 숫자 token usage만 허용하며 reasoning token 수가 별도로 제공되지 않으면 추측하지 않는다. Launcher의 request/access logging 비활성화를 유지하고 raw envelope, streaming 덤프, exception 본문, reasoning history를 파일이나 콘솔로 출력하지 않는다. 공식 예제의 reasoning print 코드는 사용하지 않는다.

`finish_reason=stop`, 유효 final content, schema, 원문 grounding, 기존 semantic scorer와 승인 경계를 모두 유지한다. 길이 초과·종료 marker 누락·content의 think tag·잘못된 JSON은 실패로 집계하고 분모에서 빼지 않는다. Prompt의 reasoning 금지 문구와 thinking 실험 의도도 사전에 명확히 하며, prompt를 수정하면 그 효과까지 포함된 별도 version임을 기록한다. Thinking이 조건 의미나 잘못된 target 선택을 자동 해결한다고 가정하지 않는다.

다음 실험은 development에만 적용한다. Model revision, prompt/schema/parser/scorer hash, 모든 sampling 값, reasoning parser와 true/false, output cap, seed, launch hash를 고정한 후 평가해야 한다. 이 조사 자체는 모델 선정 gate 통과, 새 profile 구현 완료, RTX 실행 확인이 아니다.
