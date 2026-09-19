# Phase 5 — Local Model Runtime 진행 기록

**IN PROGRESS.** 사용자 지침에 따라 GPU3 공존 실행을 VRAM 예산으로 판단한다. 점유 존재만으로 중단하는 과거 정책은 폐지됐다. Phase5 완료/최종 모델 선정은 아직 아니다.

## 현재 구현과 실제 검증

- 분리된 `.conda-vllm`: Python3.12.14, vLLM0.8.5+cu118, Torch2.6.0+cu118, Transformers4.51.3, xgrammar0.1.18. 정확한wheel SHA256 lock148개와 Python Conda lock을 보존했다. pipcheck/nativeimport PASS. 시스템 driver/CUDA/일반 Python을 변경하지 않았다.
- GPU3만 반복 측정: baseline used3965/free36373MiB/util0%. 예상peak18432MiB+margin7275MiB가 가용량 안에 들어오며 GPU0/1/2 fallback은 없다. torch 작은 FP16 연산과 mask3→cuda:0→physical3 UUID일치 검증 PASS.
- Qwen3-14B-AWQ revision31c69efc29464b6bb0aee1398b5a7b50a99340c3의 11파일9,992,683,140bytes를 직접size/SHA256검증했다. license Apache2.0, local files/offline/trust_remote_code=false.
- 첫 서버 startup PASS: 실제 quantization awq_marlin/FP16, TP1/context4096/seq1/eager/KV256 blocks/gpuutil0.50. firsthealth200 약20.666초(2초poll,watchdog표본0.5초); filesystem cache를flush한 cold 측정은 아니다. 관측 전체GPUbaseline대비peak증가10946MiB,최소free25428MiB. 다른workload 변동 때문에 이 차이를 process전용peak라고 주장하지 않는다.
- 독립검토에서 guard비정상소멸시child잔존가능성과 숫자suffix grounding오류를발견해 자신의서버를정상종료했다. free36373/used3965MiB로복귀했다. parentdeath/PG회수와 숫자경계를보강한뒤추론평가를진행한다. 타인process에는변경없음.
- Backend 중간회귀161 tests PASS/skip0(12.929s), launcher fake13 PASS. CPU xgrammar 실제schema compile 및 허용/거절 token검증 PASS. 실제 model inference와 v1 seed 평가를 마쳤으며 결과는 아래에 보존한다.

## 첫 후보 v1 평가 — 품질 기준 미충족

Qwen3-14B-AWQ, 20 development seed×3회, warmup5 제외. Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED다. [정확한 manifest](../../evaluations/results/phase5/qwen3-14b-awq-v1/manifest.json), [전체 결과](../../evaluations/results/phase5/qwen3-14b-awq-v1/results.json), [VRAM 관측](../../evaluations/results/phase5/qwen3-14b-awq-v1/resource_report.json)을 보존했다.

| 지표 | 결과 |
| --- | --- |
| JSON/schema | 60/60 |
| Backend parser 수용 | 51/60 |
| 자동 의미 rubric | 45/60 (75%) |
| 비실행 gold에 대한 READY 오판 | 모델/Backend 모두0/33 |
| 지원 요청 누락 | 6/27 |
| 요청 end-to-end mean/p95 | 2.9605s / 4.2152s |
| 전체 GPU baseline 대비 관측peak 증가 / 최소free | 11568 / 24806MiB |

D01 target 이어붙임, F01 숫자철자 변경, I01 X/Y slot 오류는 Backend에서 거절됐다. F02의 대상 범위·제외조건 손실은 parser를 통과했으며 J01은 범위 밖 설계제안을 clarification으로 분류했다. 따라서0/33만으로 안전성이 입증됐다고 주장하지 않는다. Promptv1과 gold를 고정해8B 후보를 비교하고, 새v2 prompt에서 일반 규칙과 별도 synthetic예제를 개선한다. 현재결과로 최종 model선정을 완료하지 않는다.

## 남은 gate

수정후 guarded startup/inference → seed20×3실제평가(5warmups별도) → 안전한두번째후보와비교 → independentreview → 최종report/commit/push 순서다. Schema/원문grounding/단위변환은코드로검증하며 LLM결과는대상확인이나적용승인이아니다. Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED다.

Root free약62GiB, modelenv7.4GiB/weights9.4GiB/cache5.3GiB. RTX5090은UNVERIFIED이고이cu118build를SM120에실행했다고주장하지않는다. Phase5.x~11은아직gate전이다.

## 과거 01:00 중단 기록 — 현재 정책과 상태가 아님

다음은 당시 기록이며 현재 결정은 위 현황과 [STATUS](../STATUS.md), [EXECUTION_LOG](../EXECUTION_LOG.md)를 따른다.

2026-09-20 01:00 KST. **Phase5는 완료하지 않았다.** Phase4 remote checkpoint `dd58b596fab2aaa24c5aba4322d56bc5d127440c` 확인 후 허용 GPU와 환경을 조사했다. 현재 중단 조건은 **BLOCKED_GPU_OCCUPIED**다.

### 실제 관측

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

### 정책상 중단 이유

Root AGENTS.md는 “GPU를 실행하기 전 허용 GPU만 점유 확인한다. 예상 밖 프로세스가 있으면 실행을 중단하고 보고한다”라고 정한다. 사용자 자율 실행 지침의 장기 GPU3 점유/타인 process 변경 금지 조건과 함께 적용했다.

현재 0% utilization과 남은 VRAM은 다른 작업과 동시에 모델을 실행해도 된다는 허가가 아니다. **실제 runtime OOM 또는 모든 모델의 메모리 부족을 측정한 것은 아니다.** GPU 사용 조건이 충족되지 않아 필수 실제 benchmark로 진행할 수 없다는 상태다. 다른 GPU fallback, process 종료, driver/CUDA 변경, 작은 모델/mock으로 gate 대체를 하지 않았다.

### 미실행과 재개 조건

- .conda-vllm 생성, torch/vLLM/Transformers 설치, weight 다운로드: NOT_RUN.
- Model startup/inference, schema/semantic/critical-error 평가, latency/VRAM benchmark: NOT_RUN.
- Final model 선정: NOT_SELECTED. Phase0 공식 shortlist는 조건부 계획으로 유지한다.
- Driver535/glibc2.31에서 실제로 실행 가능한 model/runtime 조합: UNVERIFIED. 시스템 변경이 필요하다고 단정하지 않는다.
- RTX5090: UNVERIFIED. Phase5.x~11은 미시작. Browser Internal MVP는 아직 완료되지 않았다.

GPU3를 사용할 수 있는 시점에 점유 상태부터 다시 확인한다. 이후 디스크와 공식 model/runtime ABI·license·quantization 조건을 검토하고 project `.conda-vllm`에 한 후보씩 준비하여 실제 평가한다. Phase1~4의 common source와 108 tests를 유지한다. 현재 상태/실행 근거/재개 조건을 commit/push하여 작업을 보존한다.
