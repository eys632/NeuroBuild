# NeuroBuild Fine-Tuning (Phase 3)

이 폴더는 NeuroBuild 원본 프로젝트와 분리된 fine-tuning / evaluation 작업 공간이다.
원본 프로젝트(/home/eys632/26-2project)는 읽기 전용으로 두고, 모든 실험/데이터/설정은 이 폴더 아래에 만든다.

## 목표 (Phase 3)
- HF base smoke eval
- smoke fine-tuning
- adapter eval 및 비교

## Final 실험
- 이름: qwen25_7b_lora_final
- 모델: Qwen/Qwen2.5-7B-Instruct (로컬 snapshot)
- 학습: LoRA (QLoRA 미사용)

## 구조
- analysis/: 현재 backend contract 정리 문서
- configs/: schema 및 system prompt
- data/: seed dataset(JSONL), messages(JSONL)
- scripts/: 검증/평가 스크립트
- results/: 평가 결과 저장

## 기준 문서
- analysis/current_backend_contract.md

## 빠른 시작

```bash
python -m venv .venv
. .venv/bin/activate

pip install -r requirements-train.txt
```

### 데이터 검증

```bash
python scripts/validate_dataset.py \
  --dataset data/seed_test.jsonl \
  --schema configs/delta_ops_schema.json
```

### 베이스라인 평가

- gold 모드(검증용): 예측을 gold로 복제하여 파이프라인만 점검

```bash
python scripts/run_baseline_eval.py \
  --dataset data/seed_test.jsonl \
  --schema configs/delta_ops_schema.json \
  --system-prompt configs/delta_system_prompt.txt \
  --mode gold
```

- vLLM 모드(선택): OpenAI 호환 API 사용

```bash
python scripts/run_baseline_eval.py \
  --dataset data/seed_test.jsonl \
  --schema configs/delta_ops_schema.json \
  --system-prompt configs/delta_system_prompt.txt \
  --mode vllm \
  --vllm-base-url http://127.0.0.1:8000 \
  --vllm-model qwen25-7b
```

## 결과
- 결과 JSONL과 요약 통계는 results/ 아래에 저장된다.

### SFT messages 변환

```bash
python scripts/build_sft_dataset.py \
  --system-prompt configs/delta_system_prompt.txt \
  --train-in data/seed_train.jsonl \
  --valid-in data/seed_valid.jsonl \
  --test-in data/seed_test.jsonl \
  --train-out data/train_messages.jsonl \
  --valid-out data/valid_messages.jsonl \
  --test-out data/test_messages.jsonl
```

생성 파일:
- data/train_messages.jsonl
- data/valid_messages.jsonl
- data/test_messages.jsonl

### 학습 설정
- configs/train_qlora.yaml

### Phase 3 smoke 실행 예시(실시간 로그 포함)

```bash
# base HF eval
CUDA_VISIBLE_DEVICES=0 bash scripts/run_with_live_logs.sh eval \
  --dataset data/seed_test.jsonl \
  --schema configs/delta_ops_schema.json \
  --system-prompt configs/delta_system_prompt.txt \
  --mode hf \
  --model-id-or-path /path/to/qwen \
  --device cuda \
  --max-samples 40 \
  --output results/base_hf_seed_test_smoke.jsonl

# smoke training
CUDA_VISIBLE_DEVICES=0 bash scripts/run_with_live_logs.sh train \
  --config configs/train_qlora.yaml \
  --train-dataset data/train_messages.jsonl \
  --valid-dataset data/valid_messages.jsonl \
  --output-dir checkpoints/qlora_smoke \
  --smoke \
  --model-id /path/to/qwen \
  --device cuda

# adapter eval
CUDA_VISIBLE_DEVICES=0 bash scripts/run_with_live_logs.sh eval \
  --dataset data/seed_test.jsonl \
  --schema configs/delta_ops_schema.json \
  --system-prompt configs/delta_system_prompt.txt \
  --mode hf \
  --model-id-or-path /path/to/qwen \
  --adapter-path checkpoints/qlora_smoke/adapter \
  --device cuda \
  --max-samples 40 \
  --output results/ft_hf_seed_test_smoke.jsonl

# compare
bash scripts/run_with_live_logs.sh compare \
  --base results/base_hf_seed_test_smoke.jsonl \
  --candidate results/ft_hf_seed_test_smoke.jsonl \
  --output results/compare_base_vs_ft_smoke.json

### 실시간 진행 상황 확인
- results/live/current_status.json
- results/live/progress.txt
- results/live/events.jsonl
- results/live/terminal_train.log
- results/live/terminal_eval.log

### Final 실험 실행 방법

```bash
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

### Final 결과 파일 위치
- adapter: checkpoints/qwen25_7b_lora_final/adapter
- base 평가: results/base_hf_seed_test_final.jsonl
- base 평가 요약: results/base_hf_seed_test_final.summary.json
- fine-tuned 평가: results/ft_hf_seed_test_final.jsonl
- fine-tuned 평가 요약: results/ft_hf_seed_test_final.summary.json
- 비교 결과: results/compare_base_vs_ft_final.json
- 제출용 표: results/final_metrics_table.csv
- 실패 사례 분석: results/failure_analysis_final.md
- 최종 실험 보고서: results/final_experiment_report.md

### Smoke vs Final 차이
- smoke: 소규모 학습/평가로 파이프라인 검증
- final: train 60 / valid 20 / test 40, epoch 3 기준 평가

### 최종 제출 파일 목록
- results/final_experiment_report.md
- results/final_metrics_table.csv
- results/compare_base_vs_ft_final.json
- results/base_hf_seed_test_final.summary.json
- results/ft_hf_seed_test_final.summary.json
- results/failure_analysis_final.md
```

## 주의
- 원본 NeuroBuild 코드는 수정하지 않는다.
- 학습용 canonical 출력은 op 키만 사용한다.
