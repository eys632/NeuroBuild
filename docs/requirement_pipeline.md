# Local Requirement pipeline

Phase5의 model 경계는 공통 [기본 prompt v3](../prompts/requirement_v3.txt) → loopback HTTP final completion → [generation schema](../schemas/semantic_requirement.schema.json)와 원문 근거 검증 → `SemanticRequirement`다. 이전 v1/v2는 별도 평가 재현용으로 보존하며 `prompt_path`로 명시할 수 있다. IFC 변경, 실제 GlobalId 선택, target confirmation, proposal approval을 수행하지 않는다. 이 문서와 fake HTTP 테스트만으로 실제 GPU/model 실행 성공을 주장하지 않는다. 실제 평가 결과는 별도 run manifest와 Phase 보고서를 따른다.

## 호출과 반환

```python
from neurobuild.infrastructure.local_model import LocalRequirementClient, StructuredOutputProtocol

client = LocalRequirementClient(
    "http://127.0.0.1:8003",
    "configured-served-model",
    protocol=StructuredOutputProtocol.LEGACY_GUIDED_JSON,
)
# code-owned UUID와 원문을 전달한다. 외부 API로 자동 fallback하지 않는다.
requirement = client.extract(
    source_text,
    requirement_id=requirement_id,
    project_id=project_id,
    base_revision_id=base_revision_id,
    axis_convention="project_xy",
)
```

`complete(source_text, axis_convention=...)`는 synthetic 평가용 `Completion(content, usage, latency_seconds, model)`을 돌려준다. 이것은 parser 통과나 의미적 정확성을 뜻하지 않는다. malformed final JSON도 평가할 수 있지만 HTTP envelope 오류, 잘린 출력, tool call, `<think>`가 섞인 content는 거절한다. `extract()`는 `complete()` 결과를 `parse_requirement()`로 변환한다. ID는 모델 출력에서 받지 않는다.

`usage`는 서버가 제공한 정수 token count만 보존한다. reasoning token **수**가 제공되면 `reasoning_tokens`로 표시하지만 reasoning 내용은 버린다. 누락 usage는 `None`이며 임의0으로 채우지 않는다. latency는 client 요청부터 final envelope 수신까지의 end-to-end 시간이다. TTFT나 decode-only tokens/sec로 표시하지 않는다. prompt/schema의 실제 bytes SHA256은 client의 `prompt_sha256`, `schema_sha256`에서 얻는다. 명시한 dialect는 `client.protocol.value`로 run manifest에 기록한다.

## 출력 계약 1.0

Top-level은 `schema_version`, `decision`, `target_text`, `operation`, `reason`만 허용한다. decision은 READY/CLARIFICATION/UNSUPPORTED다. READY만 operation을 가지며 reason은 null이다. 나머지는 operation=null과 짧은 이유가 필수다.

operation은 `MOVE_FURNITURE`, `PROJECT_WORLD_XY`, 현재 전체 지시의 exact span인 `instruction_text`, `dx`, `dy`다. 각 축은 원문 숫자를 유지한 `value` 문자열, m/cm/mm `unit`, 축·방향·거리의 exact span인 `evidence`를 가진다. 한 축만 명시되었을 때 다른 축은 null이며, code가 검증 후0m로 채운다. 현재 instruction의 명시 축과 출력 축이 다르면 거절한다. 과거 명령의 축이나 숫자를 현재 evidence로 끌어오지 않는다.

target은 원문 exact span이며 대상의 위치/색/층/제외 조건을 보존하도록 prompt에 명시한다. 숫자 spelling과 원래 unit도 유지한다. `250mm`를 모델이 `0.25m`로 계산해 내보내면 거절하고, code가 Decimal로 변환한다. 음의 방향이나 `-X축`처럼 부호가 말/축에 표현되어도 magnitude와 근거가 일치하면 지원한다. 명시된 부호가 없는 `X축 1m`는 양의 방향으로 추측하지 않는다.

Backend 한도: source16000자, model final16384자, target1024자, current instruction4096자, axis evidence/reason512자, decimal30자(정수부 최대16자리/소수부 최대12자리). 중복 JSON key, NaN/Infinity, 추가 key, UUID/GlobalId/approval/raw IFC 필드, 임의 unit·산술식·지수표현을 거절한다. 오류는 내용 echo 없는 `INVALID_MODEL_OUTPUT`, `INVALID_REQUIREMENT_INPUT`, `UNGROUNDED_REQUIREMENT`다.

이 결정론적 검증은 숫자/원문 grounding을 검사한다. 조건/부정의 의미, 전체 target 수식어를 빠짐없이 선택했는지, 현재 지시 span의 완전성까지 증명하지는 않는다. 조건부/이동 금지/복수 작업/승인 우회가 READY로 분류되지 않는지는 별도 semantic evaluation의 필수 항목이다. 실패한 모델 출력을 정답으로 덮어쓰거나 키워드 parser로 LLM 정확도를 대체하지 않는다. `tests/test_requirements.py`의 seed20 변환은 **AUTO-GENERATED / NOT HUMAN VERIFIED** representability fixture이며 LLM accuracy 측정이 아니다.

## vLLM transport와 제한

`/v1/chat/completions`에 temperature0, seed42, stream=false, 기본 max_tokens768과 `chat_template_kwargs={"enable_thinking": false}`를 보낸다. protocol은 `StructuredOutputProtocol` enum 또는 동일한 문자열을 명시한다. 기존 A100 호출의 기본값은 `legacy_guided_json`이며 모델명/GPU/응답으로 추측하지 않는다.

| protocol | 요청 필드 | Grammar backend 설정 |
|---|---|---|
| `legacy_guided_json` | `guided_json=schema`, `guided_decoding_backend="xgrammar:no-fallback"` | A100의 기존 vLLM0.8.5 요청 계약 |
| `structured_outputs` | `structured_outputs={"json": schema}` | 선택한 현대 runtime의 server launch 설정에서 명시 |

현대 요청에는 legacy backend 필드를 넣지 않는다. server의 backend/fallback 옵션은 버전별로 다르므로 [프로토콜 호환성 조사](model_protocol_compatibility.md)를 따라 별도로 pin한다. 미지원 protocol은 HTTP 호출 전에 거절하고, HTTP 오류나 비정상 응답 후 다른 dialect 또는 schema 없는 요청으로 자동 재시도하지 않는다. vLLM0.8.5가 xgrammar에서 지원하지 않는 minLength/maxLength는 generation schema에서 제외했고 Backend 한도는 유지한다. 숫자의 lexical pattern도 Backend에서 검사한다.

두 dialect의 fake HTTP 검증은 client가 올바른 필드를 전송한다는 근거다. HTTP200이나 유효 JSON 한 건은 서버의 grammar 적용 증거가 아니다. 현대 server가 legacy 필드를 조용히 무시할 수 있으므로 runtime/protocol pin과 현장 통합 검증이 필요하다. RTX5090 또는 현대 runtime을 실행·검증했다고 해석하지 않는다.

설치된 vLLM0.8.5 + xgrammar0.1.18에서 CPU 검증했다. `has_xgrammar_unsupported_json_features`가 최종 schema에 False를 반환했고, Qwen3-14B-AWQ revision `31c69efc29464b6bb0aee1398b5a7b50a99340c3`의 local tokenizer(vocab151936)로 grammar compile이 성공했다. READY/CLARIFICATION 예시2개의 token과 EOS를 수락하고 추가 approval 필드는 거절했다. GPU를 숨긴 offline process에서 tokenizer만 사용한 결과이며 모델 weight 로드나 실제 inference 검증은 아니다.

단일 choice/index0, role=assistant, finish_reason=stop, 설정과 같은 model 이름만 받는다. length/tool_calls/content_filter 등으로 끝나면 실행 가능한 결과로 반환하지 않는다. 선택적 reasoning 필드는 저장/반환/출력하지 않는다. 로그도 남기지 않으며 caller는 평가 저장 시 final schema-valid structured output만 선택해야 한다.

HTTP 주소는 numeric loopback 또는 localhost만 가능하고 localhost는127.0.0.1로 고정한다. 환경 proxy와 redirect를 차단하고 credentials/query/fragment/외부 주소를 거절한다. 기본 timeout60초(설정 상한300초), HTTP response262144bytes 한도가 있으며 socket I/O timeout과 response body elapsed-time budget을 검사한다. timeout은 실시간 스케줄러 보장은 아니다. `LOCAL_MODEL_*` 오류는 서버 원문/body/stack trace를 사용자 메시지에 포함하지 않는다. 이 client는 GPU 자원 점검이나 서버 프로세스 시작을 대신하지 않는다.

`tests/test_local_model.py`는 실제 임시 loopback HTTP 서버로 두 dialect의 요청 필드와 공통 parser 연결, unknown protocol 거절, grammar 없는 재시도 금지, redirect/proxy 차단, timeout/크기/불완전 응답, safe errors, reasoning 비보존을 검증한다. GPU와 외부 네트워크를 사용하지 않는다.
