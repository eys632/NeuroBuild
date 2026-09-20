# Generation2 greedy 비교 사전 검토

2026-09-20, 실제 추론 전 CPU/read-only 검토. **진행을 막는 compatibility 또는
reproducibility blocker를 찾지 못했다.** 기존 `legacy_greedy` profile로 동일한 MoE,
generation2 branch schema, prompt v2의 development40×3을 비교하는 것은 타당하다.
이 문서는 새 모델 호출이나 greedy 품질 통과의 증거가 아니다.

Root가 보고한 직전 neutral formal 결과는 semantic119/120, raw READY FP0이지만
HD-F02 trial3의 target scope/exclusion 손실로 unsafe accepted1이다. 기존 gate에서는
**FAIL**이다. 이를 보존하고 동일한 전체 자료·3회·gold·parser·threshold로 새 run을
기록한다. 실패한 trial 하나만 다시 호출하거나 성공 trial을 합치지 않는다.

## 실제 client 요청의 CPU 캡처

Backend `.conda`에서 기존 `LocalRequirementClient`를 아래 설정으로 생성하고,
HTTP opener를 메모리 내 capture 객체로 대체했다. 객체는 Request의 JSON bytes를 읽은
뒤 의도적으로 `URLError`를 발생시켰다. Client의 안전한
`LOCAL_MODEL_UNAVAILABLE` 변환까지 확인했다. **네트워크 연결·모델 추론·GPU 접근은 0회**다.

| 항목 | 캡처 결과 |
|---|---|
| model / generation contract | `neurobuild-moe` / `2.0` |
| sampling profile | `legacy_greedy` |
| 실제 sampling wire | `{"temperature": 0, "seed": 42}` |
| 생략 field | `top_p`, `top_k`, `min_p`, `presence_penalty`, `frequency_penalty`, `repetition_penalty` |
| mode / cap / timeout | `enable_thinking=false`, `max_tokens=768`, timeout60초 |
| transport | `stream=false`, `guided_json`은 선택한 branch schema와 정확히 동일, `guided_decoding_backend="xgrammar:no-fallback"` |
| prompt SHA256 | `99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6` |
| schema SHA256 | `36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2` |

근거는 [client](../../src/neurobuild/infrastructure/local_model.py)의
`sampling_parameters`(199행), `complete`(222행)와 실제 Request 캡처다.
Profile에 따라 기본 prompt/schema가 자동 변경되지 않으므로 generation2와 두 파일을
모두 명시했다. 기존 source/prompt/schema/gold는 변경하지 않았다.

## 현재 설치 서버의 생략값 처리

아래는 **설치된 vLLM0.8.5+cu118의 소스와 현재 서버 startup log**로 확인한 동작이다.
추후 다른 runtime의 동일 동작을 보장하지 않는다.

- 현재 pinned MoE의 `generation_config.json`은 temperature0.7, top_p0.8, top_k20,
  `do_sample=true`를 담는다. 서버는 `generation_config='auto'`로 기동했고
  `var/logs/qwen3-30b-instruct-v1-server.log` 31–33행에 chat defaults
  `{'temperature': 0.7, 'top_k': 20, 'top_p': 0.8}`를 기록했다.
- `vllm/config.py:1200`의 `get_diff_sampling_param()`은 지원한 sampling field만
  추린다. `do_sample`은 이 목록에 없다. `serving_chat.py:113`에서 이 defaults를
  보존하고 222행의 `request.to_sampling_params()`에 넘긴다.
- `entrypoints/openai/protocol.py:454`의 chat 변환은 요청 field가 **None일 때만**
  fallback한다. 따라서 명시적 temperature0은 모델의0.7로 덮어쓰이지 않는다.
  생략한 top_p/top_k는 우선0.8/20, min_p0, repetition_penalty1.0이 된다.
  Request 정의의 presence/frequency defaults는 각각0.0이다.
- `sampling_params.py:380`은 temperature가 sampling epsilon 미만이면
  **top_p=1.0, top_k=-1, min_p=0.0**으로 설정한다. 529행의 `sampling_type`도
  seed 유무보다 먼저 `GREEDY`를 반환한다. 이 설정에서 seed42는 요청에 보존되지만
  확률 sampling을 선택하게 만들지 않는다.

따라서 이 서버에서 예상되는 최종 처리값은 다음과 같다. 이는 wire에 모두 명시한
값이라는 뜻이 아니라, 읽은 installed source에 근거한 처리 경로다.

| 항목 | 최종 처리값 |
|---|---:|
| temperature | 0 |
| top_p / top_k / min_p | 1.0 / -1 / 0.0 |
| presence / frequency / repetition | 0.0 / 0.0 / 1.0 |
| sampling type | GREEDY |

원래 neutral profile은 T0.7/top_p0.8/top_k20 등8개 값을 명시했다. 새 비교는 greedy
decoding과 이에 수반되는 filter 해제를 함께 바꾸므로, 오직 temperature 수치 하나의
독립적 효과로 설명하지 않는다. Manifest는 실제 wire와 생략 field를 계속 구분해야 한다.

## 판단과 한계

직전 실패는 동일 구성의 반복 중 target 보존이 달라진 사례다. 이를 계기로 이미 존재하는
greedy profile을 전체40×3에 적용하는 것은 범위가 제한된 유용한 비교다. 이전4B/1.0
greedy 실패는 그대로 남기며, 모델·표현 계약이 달라진 이번 결과를 대신하지 않는다.

Greedy는 올바른 target span을 강제하지 않는다. 잘못된 가장 높은 확률의 답을 반복할 수도
있고, floating-point/kernel/scheduling 차이까지 포함한 byte-identical 재현성을 보장하지
않는다. 동일 seed의3회는 독립 표본이 아니다. 기존 unsafe0/raw FP0/schema100%/semantic≥95%
gate를 그대로 적용하고, formal development 통과와 독립 검토·freeze 뒤에만 holdout을
시작한다. Holdout은 첫 warm-up부터 노출로 취급하는 기존 절차를 유지한다.

이 검토는 파일 읽기와 CPU Request 캡처만 수행했다. 서버 재시작·설정 변경·추론·weight
읽기·GPU 조회는 하지 않았다.
