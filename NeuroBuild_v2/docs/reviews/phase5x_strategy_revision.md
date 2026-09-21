# Phase5.x 반복 실패 후 전략 재검토

작성일: 2026-09-20 KST. V4 development run
`20260919T211340Z-cebc5bbdaeea46b188caf6d27c4ff804`는 schema/parser120/120이지만
semantic96/120(80%), FN24/60이었다. Raw/accepted critical FP와 잘못된 accepted
이동은 모두0건이다. V3 development의 semantic108/120(90%), FN9/60보다 악화했다.
Gate를 통과하지 않았으며 heldout 모델 출력은 아직 없다.

## 실패 해석

V4는 F01/F02의 cm 원문 보존 오류를 고쳤지만, 7개 지원 가능한 단일 축 case를
CLARIFICATION으로 거절했다. 일부는 요청하지 않은 Y축을 요구했고, 일부는 원문에
명시된 양음 방향을 없다고 답했다. HD-D02의 단일 가구 두 축 이동도 계속 UNSUPPORTED로
판정했다. 이는 실제 입력이 부족해서가 아니라 모델이 허용 범위를 잘못 해석한 결과다.
같은 case의 3회 반복을 새로운 독립 실패 유형으로 세지는 않는다.

이번에는 예시나 경고를 계속 덧붙이지 않는다. 이전 숫자·단위 실패와 이번 과잉 거절을
함께 검토해, 장문의 규칙과 거절 예시 패턴이 supported move의 해석을 방해할 가능성을
진단한다. 짧은 [English policy v5](../../prompts/requirement_v5.txt)로 바꾸며 긴 few-shot
세트를 제거했다. 한국어 입력·대상 원문·비실행의 한국어 reason은 유지한다.

핵심은 “가구 하나의 X만/Y만/XY 모두 지원”, “요청하지 않은 축은 null이며 질문하지
않음”, “명시된 방향을 누락 정보로 재질문하지 않음”이다. 숫자·단위는 읽기 전용 원문
추출로 유지하고 외부 조건·복수 대상·순차 이동·미지원 변경·승인 우회 거절도 보존했다.
영어화·길이 축소·예시 제거를 함께 바꾸므로 결과가 좋아져도 원인을 언어 하나로
단정하거나 모든 한국어 작업에서 영어 prompt가 우수하다고 주장할 수 없다.

## 모델·runtime 가설도 분리해 검토

| 가설 | 현재 근거와 제한 |
|---|---|
| Prompt의 장문 규칙/거절 예시가 분류를 유도 | V4가 단위 복사를 개선하면서 명확한 이동의 거절을 늘렸다. 상관관계이며 원인 확정은 아니다 |
| Greedy/non-thinking 설정의 영향 | 현재 temperature0, seed42, thinking off가 고정되어 있다. 공식 모델 권고와의 차이는 별도 조사하며 이번 prompt 진단과 동시에 바꾸지 않는다 |
| AWQ quantization 또는 모델 자체의 한계 | BF16 동일14B·동일데이터 대조가 없어 quantization 손실을 분리 측정하지 못했다. 8B와14B 비교만으로 quant 원인을 증명할 수 없다 |
| Structured decoding과 의미 판단의 상호작용 | Schema/parser가120/120이어도 의미는 틀렸다. Grammar 성공은 의미 추론 성공을 보장하지 않는다. 반대로 이것만으로 grammar가 원인이라고 단정할 수도 없다 |

근거 없이 temperature/thinking/quant/schema를 동시에 바꾸지 않는다. Thinking 활성화는
출력 길이·template·guided decoding 호환성·추론 내용 비저장까지 다시 검토해야 하며,
현재 JSON 응답이 완결됐다는 사실로 다른 설정의 안전한 호환성을 가정하지 않는다.

## 진단과 후속 판단

Root는 고정된 development40 전체를 각1회 실행하는 **진단 run**을 먼저 수행한다.
유리한 case만 고르지 않으며 이40회 결과를 최종3회 반복 gate로 표시하지 않는다.
유망한 결과면 같은 설정으로40×3 정식 평가를 실행하고 전체 semantic/FP/FN/잘못된
이동/분류별 실패를 확인한다. V3/V4 실패 결과와 정확한 hash를 계속 보존한다.

Schema/parser/client/v3/v4/gold는 변경하지 않았다. 지원 범위를 축소하거나 정답을
바꿔 점수를 높이지 않는다. 같은 의미 오류가 남으면 prompt 문장만 추가하지 않고
모델·runtime 설정의 통제된 비교를 재검토해야 한다. 이전에 검토한 evidence-only
versioned 계약은 중복 value/unit 추출 실패를 줄일 수 있지만, 이번의 잘못된
CLARIFICATION/UNSUPPORTED 분류를 직접 해결하는 대안은 아니다. 아직 구현하지 않았다.

Heldout은 development 진단을 통과한 설정을 고정한 뒤에만 호출한다. 작성자는 앞선
추론 전 gold 검토에 참여했으나, v5 규칙은 이번 development 오답과 공통 계약에서
도출했으며 heldout 정답을 새 예시로 사용하지 않았다. 모든 gold는 여전히
**AUTO-GENERATED / NOT HUMAN VERIFIED**다.

## CPU token 검증

Qwen3-14B-AWQ tokenizer revision `31c69efc29464b6bb0aee1398b5a7b50a99340c3`를
offline/CPU에서 사용했다. CUDA를 숨기고 USE_TORCH/USE_TF/USE_FLAX=0으로 실행했으며
torch 미import를 확인했다. 실제 client와 같은 JSON messages 및 non-thinking template다.
Heldout은 입력 token 길이만 계산했고 gold나 모델 응답을 사용하지 않았다.

| 항목 | Token 수 |
|---|---:|
| V5 system prompt | 847 |
| Development 입력 | 887–1262 |
| Development 입력 + 출력768 최대 | 2030 / 4096 |
| Holdout 입력, 길이 검사만 | 893–1267 |
| Holdout 입력 + 출력768 최대 | 2035 / 4096 |

Prompt SHA-256:
`ca51aee26257f734bcdbc9e375b681ee2058f823153c9311cdaa4c54b4086b8d`.
이 검사는 길이 확인이며 모델 품질 개선이나 Phase5.x 완료 증거가 아니다.
