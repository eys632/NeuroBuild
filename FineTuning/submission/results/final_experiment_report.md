# 최종 실험 보고서: qwen25_7b_lora_final

## 1. 과제 목표
한국어 프롬프트를 NeuroBuild backend가 이해할 수 있는 delta JSON 수정 명령으로 변환하는 SLM을 학습/평가한다.
모델이 직접 IFC/파이썬 코드를 생성하지 않고, JSON 형태의 편집 명령만 생성하는 것을 목표로 한다.

## 2. NeuroBuild와의 연결성
NeuroBuild의 현재 backend contract(ops 스키마)를 기준으로 학습/평가를 구성했다.
모델은 “자연어 → JSON 수정 명령”만 담당하며, 실제 IFC 생성/수정은 기존 deterministic backend가 수행한다.

## 3. 사용 모델
- base 모델: Qwen/Qwen2.5-7B-Instruct (로컬 snapshot)
  - /home/eys632/26-2project/models/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28
- fine-tuning 방식: LoRA
- QLoRA는 시도했으나 bitsandbytes 미설치로 LoRA fallback 사용

## 4. 데이터셋 구성
- train: 60
- valid: 20
- test: 40
- 형식: messages 기반 SFT 데이터
- gold는 op 키 기준의 canonical JSON

## 5. 학습 방식
- TRL SFTTrainer + PEFT(LoRA)
- 1 GPU( CUDA_VISIBLE_DEVICES=0 ) 사용
- 3 epoch 학습
- 학습 출력: checkpoints/qwen25_7b_lora_final/adapter

## 6. 평가 지표
- JSON parse success
- schema validity
- op exact match
- slot accuracy

## 7. 최종 결과 표
| 모델 | json_parse_success_rate | schema_valid_rate | op_exact_match_rate | slot_accuracy_avg | total_examples |
|---|---:|---:|---:|---:|---:|
| base_qwen25_7b | 1.0 | 0.85 | 0.55 | 0.6375 | 40 |
| fine_tuned_qwen25_7b_lora | 1.0 | 0.975 | 0.95 | 0.95 | 40 |

## 8. 결과 해석
- LoRA fine-tuning 이후 schema_valid_rate, op_exact_match_rate, slot_accuracy_avg가 모두 상승했다.
- 특히 op_exact_match_rate가 0.55 → 0.95로 개선되어, delta ops 선택 정확도가 크게 향상되었다.

## 9. 실패 사례 분석 요약
- base: schema 위반(허용되지 않는 필드), op 선택 오류, 복합 명령 처리 오류가 주요 원인
- fine-tuned: 지원 불가/애매한 요청 처리에서 일부 오답 유지
- 상세 사례는 results/failure_analysis_final.md 참고

## 10. 한계
- QLoRA는 환경 제약(bitsandbytes 미설치)으로 적용하지 못했다.
- 테스트 세트가 40개로 작아 일반화 성능 판단에는 한계가 있다.

## 11. 향후 개선 방향
- bitsandbytes 환경 정리 후 QLoRA 재시도
- 지원 불가/애매한 요청에 대한 “빈 edits” 규칙을 더 강화
- 복합 명령 사례 확장 및 평가 데이터 확장
