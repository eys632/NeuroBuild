# NeuroBuild SLM Fine-tuning 결과 보고서

## 1. 프로젝트 개요
NeuroBuild는 사용자의 한국어 프롬프트를 받아 건축도면 생성/수정 명령으로 해석하고, 기존 backend가 IFC를 생성/수정한 뒤 웹 3D viewer에서 확인하고 다운로드하는 시스템이다. 본 실험에서 모델은 도면을 직접 생성하지 않으며, 한국어 프롬프트를 JSON 수정 명령으로 변환하는 역할만 수행한다.

## 2. 과제 목표
Free SLM을 사용해 NeuroBuild의 프롬프트 해석 성능을 개선하고, backend가 이해 가능한 JSON 수정 명령을 더 정확히 생성하는 것이 목표다.

## 3. 전체 파이프라인
사용자 프롬프트
→ fine-tuned SLM
→ JSON 수정 명령
→ NeuroBuild backend
→ IFC 생성/수정
→ 3D viewer
→ 다운로드

## 4. 사용 모델
- 모델: Qwen/Qwen2.5-7B-Instruct
- 경로: /home/eys632/26-2project/models/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28

## 5. 사용 데이터셋
| 구분 | 경로 | 개수 |
|---|---|---:|
| train | /home/eys632/26-2proj-FineTuning/data/seed_train.jsonl | 60 |
| valid | /home/eys632/26-2proj-FineTuning/data/seed_valid.jsonl | 20 |
| test | /home/eys632/26-2proj-FineTuning/data/seed_test.jsonl | 40 |
| train_messages | /home/eys632/26-2proj-FineTuning/data/train_messages.jsonl | 60 |
| valid_messages | /home/eys632/26-2proj-FineTuning/data/valid_messages.jsonl | 20 |
| test_messages | /home/eys632/26-2proj-FineTuning/data/test_messages.jsonl | 40 |

데이터셋은 한국어 프롬프트와 정답 JSON으로 구성되며, messages 포맷(SFT용 대화 형식)으로 변환해 학습에 사용한다.

## 6. 데이터 형식
- prompt_ko: 한국어 사용자 프롬프트
- gold: 정답 JSON
- edits: 수정 명령 목록
- op(실행할 작업 이름): 적용할 작업의 종류
- value(작업에 필요한 세부 값): op에 필요한 값
- notes(보조 설명): 애매함/미지원 이유 등 간단한 메모

예시(JSON):
```json
{
  "id": "delta_train_001",
  "category": "window_remove",
  "prompt_ko": "외벽 창문 전부 없애줘.",
  "gold": {
    "edits": [
      {"op": "remove_all_windows"}
    ],
    "notes": ""
  }
}
```

## 7. 학습 방법
- 방식: LoRA(adapter, LoRA로 학습된 추가 가중치)
- QLoRA는 시도했으나 bitsandbytes 미설치로 사용하지 못했고 LoRA fallback을 사용했다.
- 3 epoch 학습, 단일 GPU(CUDA_VISIBLE_DEVICES=0) 사용
- adapter 경로: checkpoints/qwen25_7b_lora_final/adapter

## 8. 평가 방법
원본 모델과 fine-tuned 모델을 동일한 test set(40개)으로 평가했다. 동일한 프롬프트에 대해 생성된 JSON을 정답과 비교하여 지표를 계산했다.

## 9. 평가 지표 설명
- JSON parse success: 모델 출력이 JSON으로 정상 파싱되는 비율
- schema validity: JSON이 schema(데이터 형식 규칙)를 만족하는 비율
- op exact match: edits 목록이 정답과 완전히 일치하는 비율
- slot accuracy: op와 value(세부 값) 조합이 정답과 얼마나 맞는지의 평균 정확도

## 10. 실험 결과
| 모델 | json_parse_success_rate | schema_valid_rate | op_exact_match_rate | slot_accuracy_avg | total_examples |
|---|---:|---:|---:|---:|---:|
| base_qwen25_7b | 1.0 | 0.85 | 0.55 | 0.6375 | 40 |
| fine_tuned_qwen25_7b_lora | 1.0 | 0.975 | 0.95 | 0.95 | 40 |

## 11. 결과 해석
fine-tuning 이후 모든 지표가 개선되었다. 특히 op exact match가 0.55에서 0.95로 상승해, 어떤 수정 명령(op)을 선택할지에 대한 정확도가 크게 좋아졌다.

## 12. 실패 사례 분석
대표 사례(발췌):

- base는 틀렸지만 fine-tuned는 맞힌 사례
  - delta_006: "환기창만 넣어줘"에서 base는 창문 개수로 오해, fine-tuned는 창문 크기(small)로 정확히 해석
  - delta_008: "욕실 쪽 외벽 창문은 빼줘"에서 base는 모든 창문 제거로 오해, fine-tuned는 욕실 쪽 제외로 정확히 해석

- 둘 다 틀린 사례
  - delta_025: "동쪽 벽에만 창문"은 지원 불가 요청인데 두 모델 모두 지원하지 않는 필드를 생성
  - delta_026: "창문 좀 늘려줘"는 애매한 요청인데 두 모델 모두 임의로 창문 개수를 결정

세부 내용은 results/failure_analysis_final.md를 참고한다.

## 13. 한계
- 테스트셋이 40개로 작아 일반화 평가에 한계가 있다.
- QLoRA가 아니라 LoRA로 학습했다.
- 실제 도면 품질이나 건축 법규 적합성은 평가하지 않았다.
- 지원 불가/애매한 요청 처리 정확도는 추가 개선이 필요하다.

## 14. 기존 UI 적용 및 검증 계획
다음 단계로 fine-tuned 모델을 기존 NeuroBuild backend에 연결하고, 웹 UI에서 동일 프롬프트를 원본 모델과 fine-tuned 모델에 입력하여 결과를 비교해야 한다. API 수준 평가(응답 JSON 비교)와 UI 수준 평가(3D 결과 확인)를 모두 수행해야 한다.

## 15. 결론
NeuroBuild 전용 데이터로 LoRA fine-tuning을 수행한 결과, 한국어 건축도면 수정 프롬프트를 JSON 수정 명령으로 변환하는 성능이 개선되었다. 모델은 도면을 직접 생성하지 않고 backend가 이해할 수 있는 JSON 수정 명령을 생성하는 역할을 수행한다.
