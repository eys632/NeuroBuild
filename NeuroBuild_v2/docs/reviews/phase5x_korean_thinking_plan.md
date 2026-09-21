# Phase5.x 한국어 v3 정책의 thinking 비교 계획

2026-09-20 KST. V6 영어 thinking 진단은 root 보고상 semantic17/40, parser20/40, raw FP4/20, unsafe accepted2/40으로 실패했다. 모든 응답이 stop으로 종료했고 최대 completion971 tokens였다는 관측은 그 run에서 단순 truncation만으로 실패를 설명하기 어렵다는 근거다. 이 문서는 v7 실행 전 계획이며 새 모델 성공을 주장하지 않는다.

## 변경 범위와 비교 목적

비교 대상으로 가장 나았던 한국어 v3 정책을 되돌려 사용한다. V3는 non-thinking/T0 development120회에서108회가 맞았고, 공식 non-thinking sampling 진단도36/40이었다. 새 영어 규칙이나 few-shot을 작성하지 않는다.

[requirement_v7.txt](../../prompts/requirement_v7.txt)는 v3의 다음 **한 문장만** 교체했다.

```text
이전: 설명, Markdown, 추론 내용, <think>는 출력하지 않는다.
이후: 내부 추론은 허용하며 최종 content에는 JSON 객체만 출력하고 설명, Markdown, 추론 내용, <think>는 포함하지 않는다.
```

교체 대상은 v3에 정확히 한 번 존재하며, 새 문장을 역치환하면 v3와 byte 단위 동일하다. 모든 분류·조건·대상·숫자/단위 규칙과 synthetic 예시는 불변이다. Gold/schema/parser/scorer의 기준도 변경하지 않는다.

| Prompt | SHA-256 |
|---|---|
| V3 | `716137f3e275cb0030f1f497f8e23bbeeefd8a62eae757378231b7d910db3c3e` |
| V7 | `83fd605035d867e604115d25cce28971121895bb155dd2ac648056bd9c53c89b` |

이는 **원래 한국어 정책을 보존한 thinking 설정 비교**다. V3 non-thinking과 비교하면 reasoning 활성화·최종 형식 문구뿐 아니라 sampling, output cap, timeout도 다르므로 순수 reasoning 효과만 측정하는 단일 변수 실험은 아니다. V6와 비교하면 정책·언어·예시 길이와 output cap이 함께 다르다. 관측 결과를 특정 변수의 인과 효과로 단정하지 않는다.

## 고정할 실행 설정

현재 thinking 서버를 유지한다. 환경·모델 weight·GPU/context 예산을 바꾸지 않는다.

| 항목 | 값 |
|---|---|
| Model/tokenizer | Qwen3-14B-AWQ `31c69efc29464b6bb0aee1398b5a7b50a99340c3` |
| Runtime | vLLM0.8.5+cu118, V0, AWQ-Marlin, FP16 |
| Reasoning | `--enable-reasoning --reasoning-parser deepseek_r1`; `enable_thinking=true` |
| Sampling | temperature=.6, top_p=.95, top_k=20, min_p=0 |
| Penalty | presence=1.5, frequency=0, repetition=1 |
| Seed / concurrency | 42 / 1 |
| JSON | 기존 schema, `guided_json`, `xgrammar:no-fallback`, non-streaming |
| Output / timeout | **reasoning+final 합계1280 tokens** / 120초 |
| Context / GPU | 4096 / physical GPU3, TP1 |

공식 설정 근거와 legacy reasoning/grammar 경로는 [디코딩 검토](../qwen3_decoding_review.md)를 따른다. 1280은 context 안의 제한된 실험 예산이며 모델의 충분한 reasoning 길이를 보장하지 않는다. 기존 loopback·FileStore·logging 비활성화·allocation cap·watchdog·점유시간 제한을 유지하고 root가 서버와 남은 실행 예산을 확인한다.

## CPU 토큰 적합성

기존 tokenizer를 CPU/offline, `USE_TORCH=0`, `USE_TF=0`, `USE_FLAX=0`으로 실행했다. `torch` 미import를 확인했다. 실제 client와 같은 system/user JSON, `add_generation_prompt=True`, `enable_thinking=True`를 사용했다. V7 system text는2378 tokens다.

| 입력 | Chat 입력 token 범위 | 최대 입력 + output1280 |
|---|---:|---:|
| Development40 | 2414–2789 | **4069 / 4096** |
| Holdout80, 입력 길이만 | 2420–2794 | **4074 / 4096** |

두 split 모두1280 예산이 들어가므로1200으로 낮추지 않는다. 최소 여유가22 tokens뿐이므로 prompt·chat template·user JSON 포맷이나 tokenization 설정이 달라지면 재측정한다. 미공개 지시를 덧붙이거나 source를 잘라 맞추지 않는다. 이 확인은 token 산술이며 GPU peak, 종료 성공, 품질의 실측이 아니다.

Development hash는 `85734d7c5845bbc52af43941631adfa66f3b43cc7494177e1230de6dfb18ff88`, holdout은 `12c08e85a3b64c459fe7385e1cab35a4a036c6ceb3bc1d27d137ba3515e74d78` 그대로다. Holdout은 입력 길이만 계산했으며 gold를 tokenization하거나 모델을 호출하지 않았다.

## 실행·판정 절차

독립 prompt diff 검토와 실제 profile/hash freeze 후, warm-up5회를 제외하고 **development40 전체 × 1회**를 고정 순서로 진단한다. 오류 case만 다시 실행하거나 성공 응답을 골라 합치지 않는다. 원래 v3/v4/v5/v6와 sampling run은 보존한다.

Semantic/schema는40, raw/accepted FP는 non-READY20, 잘못된 accepted 이동과 FN은 READY20을 분모로 보고한다. Final 부재, length 종료, timeout, schema/parser 실패도 전체 분모에 유지한다. Output1280 부족이 관측되면 그 제한과 실패를 기록하고, run 중 몰래 cap을 바꾸지 않는다. 추후 더 큰 예산은 별도 version·자원 검토·freeze가 필요하다.

진단이 추가 검증을 정당화할 때만 같은 후보를 development40 × 3회의 새 run으로 평가한다. Schema100%, semantic≥95%, raw FP0, unsafe accepted0 기준은 유지한다. 진단과 반복 run을 합산해 통과 수치를 만들지 않는다. Holdout 호출은 이 계획에 포함하지 않으며, 이후 평가는 [holdout 사전 프로토콜](phase5x_holdout_protocol_review.md)을 따른다.

추론 내용은 server/HTTP의 일시 메모리에서 분리·폐기하고 최종 content 및 허용된 숫자 usage만 반환·보존한다. 원문 reasoning, envelope dump, 예외 본문, reasoning history를 저장하지 않는다. 기존 finish_reason=stop, final think tag 금지, JSON/schema/source-grounding, 대상 확인·proposal 승인 경계는 그대로 유지한다.

Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**이며 같은 seed 반복과 공유 synthetic grammar의 한계도 유지된다. 이 문서 작성에서는 v7와 본 계획 외의 파일 변경, 설치, GPU 접근, 모델 호출을 하지 않았다.
