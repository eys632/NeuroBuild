# Phase5.x thinking 진단 계획

2026-09-20 KST. 이 문서는 **실행 전 계획과 CPU 검증**이다. Thinking 추론·품질·VRAM 성공을 주장하지 않는다. Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**이며 새로운 모델 호출은 development에만 한정한다.

## 목적과 비교 한계

V5 non-thinking/T0 진단은40개 중 semantic13, parser16으로 실패했다. V3는 T0의120회에서108회가 맞았으며, 공식 AWQ non-thinking sampling의40개 진단도36개가 맞았다고 root가 보고했다. 단순 sampling 변경으로 해결되지 않은 실패가 있어, 같은 checkpoint의 thinking 경로를 제한된 개발 진단으로 비교한다. [V5 독립 감사](phase5x_v5_diagnostic_review.md), [디코딩 공식 근거](../qwen3_decoding_review.md)를 따른다.

V6는 v5의 business rule·추출 계약·예시 구성을 그대로 둔다. 다만 **reasoning 활성화와 prompt의 추론 허용 문구 명확화**가 함께 바뀐다. V5/T0에 비하면 sampling, 전체 출력 예산, timeout도 바뀌므로 완전한 단일 변수 실험이 아니다. V3와도 prompt가 달라 reasoning의 순수 인과 효과를 측정했다고 쓰지 않는다. 결과는 이 조합의 관측 성능이다.

## Prompt 변경 범위

[requirement_v6.txt](../../prompts/requirement_v6.txt)는 [v5](../../prompts/requirement_v5.txt)의 다음 문장만 교체했다.

```text
이전: No prose, Markdown, reasoning, IFC, GlobalId, generated IDs, or approval.
이후: Internal thinking is allowed. The final content must be only the JSON object, with no reasoning, prose, Markdown, IFC, GlobalId, generated IDs, or approval.
```

치환 대상이 정확히 한 번만 존재함을 확인했고, 새 문장을 역치환하면 v5와 byte 단위 동일했다. 새로운 분류 규칙·few-shot·지원 범위·승인 예외는 추가하지 않았다. Schema/parser/gold/scorer를 수정하거나 실패 출력을 보정하지 않는다.

| Prompt | SHA-256 |
|---|---|
| V5 | `ca51aee26257f734bcdbc9e375b681ee2058f823153c9311cdaa4c54b4086b8d` |
| V6 | `c16d5949ee0a0da59b36a72f639b265a74164659d6927dc48d6a560ab6336023` |

## 실행 후보 설정

| 항목 | 고정값 |
|---|---|
| Checkpoint/tokenizer | Qwen3-14B-AWQ `31c69efc29464b6bb0aee1398b5a7b50a99340c3` |
| Runtime | 현재 vLLM0.8.5+cu118, V0, AWQ-Marlin, FP16 |
| Reasoning | Server `--enable-reasoning --reasoning-parser deepseek_r1`; request `enable_thinking=true` |
| Sampling | temperature=.6, top_p=.95, top_k=20, min_p=0 |
| Penalty | presence=1.5, frequency=0, repetition=1 |
| Seed / concurrency | 42 / 1 |
| Structured output | 기존 guided_json schema, `xgrammar:no-fallback`, non-streaming |
| Output / timeout | **reasoning+final 합계2048 tokens** / 120초 |
| Context / GPU | 4096 / physical GPU3만, TP1 |

Reasoning+structured output의 V0 지원과 deepseek_r1 사용은 공식 문서·로컬 소스에서 확인했다. `qwen3` parser는 이 버전의 대안이 아니다. JSON grammar는 reasoning 종료 marker 이후 적용되므로, final JSON의 schema 보장이 내부 reasoning 내용의 제약을 뜻하지 않는다. 위 sampling은 Qwen 공식 thinking/AWQ 권고에 근거하지만 전체 출력2048은 공용 서버의 **짧은 진단 예산**이며 공식 모델 카드의 일반 출력 권고32768과 다르다. 종료 전 예산 소진은 실패다.

서버의 reasoning 설정, client의 명시적 profile, run manifest와 fake HTTP 검증이 준비돼야 한다. Non-thinking 요청을 이 0.8.5 reasoning-parser 서버와 섞지 않는다. 기존 loopback, FileStore, eager, 단일 sequence, GPU preflight·allocation cap·watchdog·최대 점유시간 정책은 유지한다. 환경 설치나 GPU 설정 변경은 이 계획에 포함하지 않는다.

## CPU 토큰 검증

기존 로컬 tokenizer를 `USE_TORCH=0`, `USE_TF=0`, `USE_FLAX=0`, offline 모드로 읽었고 `torch` 미import를 확인했다. Client와 동일한 system/user JSON, `add_generation_prompt=True`, `enable_thinking=True`를 사용했다. System prompt는863 tokens다.

| 입력 | Chat 입력 token 범위 | 최대 입력 + 전체 출력2048 |
|---|---:|---:|
| Development40 | 899–1274 | 3322 / 4096 |
| Holdout80, 입력 길이만 | 905–1279 | 3327 / 4096 |

Development SHA는 `85734d7c5845bbc52af43941631adfa66f3b43cc7494177e1230de6dfb18ff88`, holdout SHA는 `12c08e85a3b64c459fe7385e1cab35a4a036c6ceb3bc1d27d137ba3515e74d78`다. Holdout gold는 tokenization하지 않았고 응답을 생성하거나 열람하지 않았다. 길이 적합성은 실제 reasoning 완결성·latency·peak memory 성공의 증거가 아니다.

## 진단 순서와 기록

1. Prompt와 실제 profile, launch 설정, schema/parser/scorer/client hash를 고정하고 root의 독립 검토·checkpoint를 남긴다. 가동 전 기존 GPU3 preflight와 timeout·응답 내용 미보존 경계 검증을 통과한다.
2. Warm-up5회 후 **development40 전체를 각1회**, 고정된 case 순서로 실행한다. 성공 사례만 고르거나 특정 실패만 재시도해 점수에 합치지 않는다. Timeout·length 종료·final 부재·schema/parser 실패를40회 분모에 유지한다.
3. Raw READY FP(분모20), accepted READY FP(20), 잘못된 accepted 이동(READY20), FN(20), semantic/schema(전체40), truncation/timeout, latency와 전체 token 수를 확인한다. 추론 중 token을 별도로 서버가 제공하지 않으면 임의 추산하지 않는다.
4. 진단이 기존 품질 목표에 근접하고 위험 지표가 허용 기준을 충족해 추가 평가 근거가 있을 때만 **같은 설정으로 전체40 × 3회**를 새 run으로 검증한다. 진단1회 결과에 반복 결과를 섞지 않는다. 기존 semantic≥95%, schema100%, critical 오류0의 목표를 낮추지 않는다.
5. 실패 원인을 검토하고 기록한다. 이 계획으로 holdout을 호출하거나 그 출력을 prompt 조정에 쓰지 않는다. Development 반복 성공도 별도 holdout 검토·평가 gate를 대체하지 않는다.

Completion에는 최종 `content`와 허용된 숫자 usage만 반환한다. HTTP envelope의 reasoning은 일시 메모리에서 폐기하며 파일·콘솔·예외 본문·대화 history에 넣지 않는다. Request/access logging 비활성화를 유지한다. `finish_reason=stop`, 비어 있지 않은 final content, think tag 금지, schema와 source-grounding 검증은 그대로 적용한다. Raw reasoning의 질을 사람이 읽고 판단하는 평가도 수행하지 않는다.

기존 v3/v4/v5와 sampling 진단의 실패 run을 보존한다. 결과가 좋아져도 원문 추출 계약이나 실제 대상 확인·proposal 승인 경계를 생략하지 않는다. 이 문서 작성에서는 v6와 본 계획 외의 파일 변경, GPU 접근, 모델 호출, 설치를 하지 않았다.
