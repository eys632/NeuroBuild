# 제출용 요약 (qwen25_7b_lora_final)

## 1. 과제 주제
한국어 프롬프트를 NeuroBuild 백엔드가 이해할 수 있는 JSON 수정 명령(Delta Ops)으로 변환하는 SLM을 구축한다.
모델이 도면을 직접 생성하지 않고, 기존 deterministic backend가 IFC를 생성/수정할 수 있도록 명령만 제공한다.

## 2. NeuroBuild와의 연결성
본 실험은 NeuroBuild의 로컬 delta contract를 기준으로 학습/평가했다.
모델 출력은 backend가 적용 가능한 ops 형식만 사용한다.

## 3. 사용 모델
- Qwen/Qwen2.5-7B-Instruct (로컬 snapshot)
- 경로: /home/eys632/26-2project/models/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28

## 4. 학습 방식
- TRL SFTTrainer + PEFT(LoRA)
- QLoRA는 시도했으나 bitsandbytes 미설치로 LoRA fallback 사용
- 단일 GPU(CUDA_VISIBLE_DEVICES=0)
- 3 epoch 학습

## 5. 데이터셋 구성
- train 60 / valid 20 / test 40
- messages 포맷(SFT)
- gold는 op 키 기반 canonical JSON 유지

## 6. 평가 지표
- JSON parse success
- schema validity
- op exact match
- slot accuracy

## 7. 최종 결과 요약
- base
  - schema_valid_rate: 0.85
  - op_exact_match_rate: 0.55
  - slot_accuracy_avg: 0.6375
- fine-tuned
  - schema_valid_rate: 0.975
  - op_exact_match_rate: 0.95
  - slot_accuracy_avg: 0.95
- compare
  - improvement 16 / regression 0 / tie 24

## 8. 실행 방법

```bash
cd /home/eys632/26-2proj-FineTuning

# final train
CUDA_VISIBLE_DEVICES=0 bash scripts/run_with_live_logs.sh train \
  --config configs/train_qlora.yaml \
  --train-dataset data/train_messages.jsonl \
  --valid-dataset data/valid_messages.jsonl \
  --output-dir checkpoints/qwen25_7b_lora_final \
  --num-train-epochs 3 \
  --model-id /home/eys632/26-2project/models/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28 \
  --device cuda

# final base eval
CUDA_VISIBLE_DEVICES=0 bash scripts/run_with_live_logs.sh eval \
  --dataset data/seed_test.jsonl \
  --schema configs/delta_ops_schema.json \
  --system-prompt configs/delta_system_prompt.txt \
  --mode hf \
  --model-id-or-path /home/eys632/26-2project/models/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28 \
  --device cuda \
  --max-samples 40 \
  --output results/base_hf_seed_test_final.jsonl

# final fine-tuned eval
CUDA_VISIBLE_DEVICES=0 bash scripts/run_with_live_logs.sh eval \
  --dataset data/seed_test.jsonl \
  --schema configs/delta_ops_schema.json \
  --system-prompt configs/delta_system_prompt.txt \
  --mode hf \
  --model-id-or-path /home/eys632/26-2project/models/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28 \
  --adapter-path checkpoints/qwen25_7b_lora_final/adapter \
  --device cuda \
  --max-samples 40 \
  --output results/ft_hf_seed_test_final.jsonl

# final compare
bash scripts/run_with_live_logs.sh compare \
  --base results/base_hf_seed_test_final.jsonl \
  --candidate results/ft_hf_seed_test_final.jsonl \
  --output results/compare_base_vs_ft_final.json
```

## 9. 제출 파일 설명
- results/final_experiment_report.md: 최종 실험 보고서
- results/final_metrics_table.csv: 제출용 지표 표
- results/failure_analysis_final.md: 실패 사례 분석
- results/compare_base_vs_ft_final.json: base vs fine-tuned 비교 결과
- results/base_hf_seed_test_final.summary.json: base 평가 요약
- results/ft_hf_seed_test_final.summary.json: fine-tuned 평가 요약
- checkpoints/qwen25_7b_lora_final/train_summary.json: 학습 요약
- scripts/*.py, configs/*.json|txt|yaml, data/seed_*.jsonl: 재현용 코드/설정/데이터

## 10. 한계 및 향후 개선 방향
- QLoRA는 bitsandbytes 미설치로 적용하지 못했다.
- 테스트 세트 규모가 작아 일반화 판단에 한계가 있다.
- 향후 bitsandbytes 환경 정리 후 QLoRA 재시도, 지원 불가/애매 요청 처리 규칙 강화가 필요하다.
