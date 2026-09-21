# Generation2 branch / 기존14B-AWQ CPU 사전 검토

2026-09-20. **현재 prompt v2·branch schema를 기존14B tokenizer/runtime에서 평가하기
위한 metadata/context/CPU grammar 검증은 PASS**다. 새로운14B 추론이나 품질 통과를
뜻하지 않는다. Source/prompt/schema/gold/config는 변경하지 않았고, MoE 채택 조건부
제안은 ignored 디렉터리에 미적용 상태로 남겼다.

MoE 첫 holdout은 실패했고 그 출력이 이미 공개됐다. 아래120개는 development40과
**노출된 이전 holdout80의 regression 자료**다. 기존 파일명에 holdout이 남아 있어도
이번 비교를 새로운 unseen holdout으로 부르지 않는다. 새로운 일반화 평가는 별도로
사전 작성·동결한 미사용 자료가 필요하다. 이 검토는 기존120개의 입력 길이만 계산하며
이전 모델 출력이나 의미 점수를 재검토하지 않았다.

## 고정 metadata와 실제 template

| 항목 | 확인값 |
|---|---|
| Checkpoint | `Qwen/Qwen3-14B-AWQ` |
| Revision | `31c69efc29464b6bb0aee1398b5a7b50a99340c3` |
| Manifest SHA256 | `208ed94ea360b214612d53f8002b69830670c3269246cef28a329c6ab3b41011` |
| 실제 tokenizer | `Qwen2TokenizerFast`, Transformers4.51.3, local files only, remote code false |
| 실제 template 출처 | `tokenizer_config.json`의 embedded `chat_template`; 별도 jinja 파일 없음 |
| Template SHA256 | `a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8` |
| Prompt SHA256 | `99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6` |
| Branch schema SHA256 | `36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2` |
| 기존 parser SHA256 | `a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a` |

[고정14B manifest](../../runtime/models/qwen3-14b-awq.json)의9개 작은 파일을 실제 local
파일의 bytes/SHA256과 대조했다. LICENSE, README, config, generation_config, merges,
safetensors index, tokenizer.json, tokenizer_config, vocab 총15,992,900bytes가 모두
일치했다. Local `neurobuild-manifest.json`도 고정 manifest와 byte hash가 같다.
2개 safetensors weight 내용은 읽거나 새로 hash하지 않았다. Apache2.0 LICENSE의 실제
존재·hash는 이번 작은 파일 검사에 포함된다.

`AutoTokenizer.from_pretrained(..., local_files_only=True, trust_remote_code=False)`가
선택한 template 문자열이 embedded 값과 정확히 같음을 확인했다. Client와 같은 system
prompt 및 `json.dumps({source_text, axis_convention}, ensure_ascii=False)` user message에
`add_generation_prompt=True`, **`enable_thinking=False`**를 적용했다.

이14B template의 assistant 생성 시작 부분에는 다음 **빈** prefix가 붙는다.

```text
<think>

</think>

```

이는 입력 template의 제어 문자열이고 모델이 생성한 reasoning이 아니다. MoE instruction
template와 byte가 같다고 가정하지 않았다. 실제 client가 응답 content 안의 reasoning을
거절하는 기존 정책은 그대로 유지하며, 이번 CPU 확인은 서버에서의 실제 응답을 대신하지 않는다.

## 현재 입력·출력 예산

System prompt는2499 tokens다. 모든 입력을 실제14B chat template의 위 non-thinking
설정으로 tokenize했고 출력 cap768을 더했다.

| 자료의 현재 용도 | 개수 | 입력 min–max | 최대 입력+768 | Context4096 잔여 |
|---|---:|---:|---:|---:|
| 기존 development | 40 | 2539–2914 | 3682 | 414 |
| 노출된 이전 holdout → regression | 80 | 2545–2919 | 3687 | 409 |

기존 dataset SHA는 각각 `85734d7c5845bbc52af43941631adfa66f3b43cc7494177e1230de6dfb18ff88`,
`12c08e85a3b64c459fe7385e1cab35a4a036c6ceb3bc1d27d137ba3515e74d78`로 유지됐다.
Tokenizer/길이 계산까지 Torch를 import하지 않았다. 이 여유는 현재 입력의 context
적합성이고 생성이768 안에 완료되거나 의미가 맞다는 보장은 아니다.

## CPU grammar와 범위

CUDA mask를 빈 문자열로 고정하고 offline 환경에서 xgrammar0.1.18을 사용했다.
설치된 vLLM0.8.5의 unsupported-feature 검사는 False, model vocab151936으로
branch grammar compile은 **1.886초**였다. Prompt7예시 모두 JSONSchema → adapter →
기존1.0 parser를 통과했다. 이7개와 두 축 READY 제어1개는 tokenizer token 및 EOS를
모두 수락했다. Root-only version, 잘못된 version, extra approval, READY의 null target/
instruction/양축과 non-null reason, non-READY의 null reason 또는 non-null current/axis
등 **14개 invalid control을 모두 거절**했다.

Xgrammar CPU 작업 단계에서만 Torch가 import됐으며 `torch.cuda.is_initialized()`는
전후 False였다. 네트워크·모델 추론·weight 읽기·GPU 조회/할당은 수행하지 않았다.
290개 전체 회귀를 다시 실행하지 않았으며 새로운 설치도 없다.

증거 JSON: [보존 CPU proof](../../evaluations/results/phase5x/generation2-14b-cpu-preflight.json).
SHA256: `d609be2f31396c57ac0dc6ea940a4462d713505c266a099f62c766c3c11fd54a`.
재현 script는 `var/research/verify_generation2_14b_preflight.py`이며 실제 모델을 부르지 않는다.

다음14B 비교는 허용 GPU3의 **fresh resource preflight와 별도 launch/freeze**가 있어야 한다.
과거14B startup/1.0 실패 또는 이번 CPU PASS를 현재 generation2 품질 결과로 재사용하지
않는다. Raw FP·unsafe accepted·target scope·모든 실패 분모와 사람 미검수 gold 표기를
그대로 유지한다. 이 검토 자체는 모델 선택이나 Phase5.x 완료 판단이 아니다.
