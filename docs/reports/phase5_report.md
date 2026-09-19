# Phase 5 — Local Model Runtime 진행 기록

> 2026-09-20 04:32 KST 갱신: 사용자가 VRAM 예산과 안전 margin 기반 공존 실행을 허용했다. 아래 01:00 중단은 당시 기록이며 현재는 Phase5를 재개했다. 최신 상태는 ../STATUS.md 및 EXECUTION_LOG.md를 따른다.

2026-09-20 01:00 KST. **Phase5는 완료하지 않았다.** Phase4 remote checkpoint `dd58b596fab2aaa24c5aba4322d56bc5d127440c` 확인 후 허용 GPU와 환경을 조사했다. 현재 중단 조건은 **BLOCKED_GPU_OCCUPIED**다.

## 실제 관측

오직 physical GPU3을 조회했다.

```sh
nvidia-smi -i 3 --query-gpu=index,name,uuid,driver_version,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader
nvidia-smi -i 3 --query-compute-apps=pid,used_gpu_memory --format=csv,noheader
```

| 항목 | 관측 |
|---|---|
| GPU | 3 / NVIDIA A100-PCIE-40GB |
| Driver | 535.183.01 |
| Total / used / free | 40960 / 3965 / 36373 MiB |
| GPU utilization | 0% at inspection |
| Compute process | 3개; 개별 VRAM1746/1772/414MiB |
| 현재 사용자 소유 여부 | `ps -u <현재 uid> -o pid=`의 본인 PID 집합과 대조: 0/3 |
| Root disk | 96%, 약83G free |
| 기존 Backend | .conda Python3.12.14, 약1.4G |
| Cache / private PostgreSQL data | 약803M / 82M |
| Model environment | .conda-vllm 없음 |

다른 사용자의 process 소유자/명령/파일/환경을 조사하지 않았다. GPU compute 목록과 **본인 process 목록**만 비교했고 process를 종료하거나 변경하지 않았다. Phase0에서도 process3개와3965MiB를 관측했으며 이번에도 점유가 유지됐다.

기본 shell의 `python`은 없고 `python3`는 system3.8.10이며 CONDA_PREFIX는 비어 있었다. 이는 Backend 환경 부재를 뜻하지 않는다. Backend는 `.conda/bin/python`으로 실행하여 앞 단계까지 검증했고 시스템 Python은 기본 조사에만 사용했다. 모델 설치는 시작하지 않았으므로 잘못된 shell Python에 package를 설치하지 않았다.

## 정책상 중단 이유

Root AGENTS.md는 “GPU를 실행하기 전 허용 GPU만 점유 확인한다. 예상 밖 프로세스가 있으면 실행을 중단하고 보고한다”라고 정한다. 사용자 자율 실행 지침의 장기 GPU3 점유/타인 process 변경 금지 조건과 함께 적용했다.

현재 0% utilization과 남은 VRAM은 다른 작업과 동시에 모델을 실행해도 된다는 허가가 아니다. **실제 runtime OOM 또는 모든 모델의 메모리 부족을 측정한 것은 아니다.** GPU 사용 조건이 충족되지 않아 필수 실제 benchmark로 진행할 수 없다는 상태다. 다른 GPU fallback, process 종료, driver/CUDA 변경, 작은 모델/mock으로 gate 대체를 하지 않았다.

## 미실행과 재개 조건

- .conda-vllm 생성, torch/vLLM/Transformers 설치, weight 다운로드: NOT_RUN.
- Model startup/inference, schema/semantic/critical-error 평가, latency/VRAM benchmark: NOT_RUN.
- Final model 선정: NOT_SELECTED. Phase0 공식 shortlist는 조건부 계획으로 유지한다.
- Driver535/glibc2.31에서 실제로 실행 가능한 model/runtime 조합: UNVERIFIED. 시스템 변경이 필요하다고 단정하지 않는다.
- RTX5090: UNVERIFIED. Phase5.x~11은 미시작. Browser Internal MVP는 아직 완료되지 않았다.

GPU3를 사용할 수 있는 시점에 점유 상태부터 다시 확인한다. 이후 디스크와 공식 model/runtime ABI·license·quantization 조건을 검토하고 project `.conda-vllm`에 한 후보씩 준비하여 실제 평가한다. Phase1~4의 common source와 108 tests를 유지한다. 현재 상태/실행 근거/재개 조건을 commit/push하여 작업을 보존한다.
