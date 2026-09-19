# NeuroBuild SLM Fine-tuning 결과 보고서 요약

## 핵심 요약
- 목표: 한국어 프롬프트를 NeuroBuild backend가 이해할 수 있는 JSON 수정 명령으로 변환하는 SLM 성능 개선
- 모델: Qwen/Qwen2.5-7B-Instruct (로컬 snapshot)
- 학습: LoRA(adapter, LoRA로 학습된 추가 가중치) 방식
- QLoRA는 bitsandbytes 미설치로 사용하지 못했고 LoRA fallback 사용
- 데이터: train 60 / valid 20 / test 40

## 파이프라인
사용자 프롬프트 → fine-tuned SLM → JSON 수정 명령 → NeuroBuild backend → IFC 생성/수정 → 3D viewer → 다운로드

## 데이터셋 경로
- /home/eys632/26-2proj-FineTuning/data/seed_train.jsonl (60)
- /home/eys632/26-2proj-FineTuning/data/seed_valid.jsonl (20)
- /home/eys632/26-2proj-FineTuning/data/seed_test.jsonl (40)
- /home/eys632/26-2proj-FineTuning/data/train_messages.jsonl
- /home/eys632/26-2proj-FineTuning/data/valid_messages.jsonl
- /home/eys632/26-2proj-FineTuning/data/test_messages.jsonl

## 평가 지표(의미)
- JSON parse success: 출력이 JSON으로 정상 파싱되는 비율
- schema validity: JSON이 schema(데이터 형식 규칙)를 만족하는 비율
- op exact match: edits 목록이 정답과 완전히 일치하는 비율
- slot accuracy: op와 value(세부 값) 조합이 정답과 얼마나 맞는지의 평균 정확도

## 최종 결과(40개 test)
- base_qwen25_7b
  - schema_valid_rate 0.85
  - op_exact_match_rate 0.55
  - slot_accuracy_avg 0.6375
- fine_tuned_qwen25_7b_lora
  - schema_valid_rate 0.975
  - op_exact_match_rate 0.95
  - slot_accuracy_avg 0.95

## 결과 해석
fine-tuning 이후 op 정확도가 0.55 → 0.95로 개선되었고, 전체 지표가 상승했다. 모델은 도면을 직접 생성하지 않으며, JSON 수정 명령만 생성한다.

## 실패 사례(요약)
- 지원 불가/애매한 요청에 대해 임의의 창문 개수를 생성하는 오류가 일부 유지됨
- 특정 방향(동쪽 벽 등) 지정은 스키마 위반 필드 생성으로 실패

## 한계 및 향후 계획
- 테스트셋이 40개로 작다.
- QLoRA 대신 LoRA로 학습했다.
- 향후 backend에 연결해 API 수준/웹 UI 수준에서 동일 프롬프트 비교 검증이 필요하다.
