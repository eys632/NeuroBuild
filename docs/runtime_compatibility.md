# Runtime compatibility matrix

기준일 2026-09-20. **MEASURED는 그 행의 관측만 뜻하며 inference PASS가 아니다.**
RTX5090에는 접속하지 않았다. 모든 RTX runtime/benchmark 항목은 PREDICTED 또는 UNVERIFIED다.

| 항목 | A100: MEASURED / 계획 구분 | RTX5090: PREVIOUSLY KNOWN / PREDICTED / UNVERIFIED |
|---|---|---|
| OS / kernel / libc | MEASURED Ubuntu20.04.6 / 5.15.0-139 / glibc2.31 | UNVERIFIED; Linux/x86_64 계획 |
| GPU | MEASURED A100-PCIE-40GB / CC8.0, 장치 수 4 표시 | 사용자 제공 RTX5090 ×2; 공식 CC12.0, 현장 미검증 |
| 사용 GPU | physical3만, 다른 GPU 조사/실행 금지 | physical1만; physical0 fallback 금지 |
| VRAM | MEASURED 40960MiB, free36373MiB at inspection | PREVIOUSLY KNOWN 32GB; 실제 free/occupied UNVERIFIED |
| Driver | MEASURED 535.183.01 | UNVERIFIED; 선택 wheel/Blackwell 요구사항 충족 필요 |
| CUDA compatibility | nvidia-smi12.2; CUDA12 minor/JIT 제한 별도 검증 | UNVERIFIED; CC12.0 지원 runtime/build 필요 |
| System toolkit | MEASURED nvcc11.8 | UNVERIFIED |
| System Python | MEASURED 3.8.10, 진단 전용 | UNVERIFIED |
| Backend Python | MEASURED .conda Python3.12.14 | 동일3.12 patch/lock 목표, 미생성/미검증 |
| Backend dependency | MEASURED psycopg3.2.10; pinned backend lock | 동일 manifest 예정, UNVERIFIED |
| IfcOpenShell | MEASURED IfcOpenShell0.8.5 Conda py312hfac0a26_8; CPU/headless import+geometry PASS; PyPI wheel ABI 실패 | 동일 Conda 버전/IFC 결과 테스트 필요; UNVERIFIED |
| PostgreSQL | MEASURED project PostgreSQL17.11; private Unix socket; noTCP; restart PASS | UNVERIFIED; 공통 migration/major 목표 |
| Model Python | MEASURED .conda-vllm Python3.12.14 | 선택 runtime 요구사항에 따라 별도 lock |
| PyTorch | MEASURED torch2.6.0+cu118; GPU3 FP16 smoke PASS | UNVERIFIED; CC12.0 포함 build 필요 |
| vLLM | MEASURED vLLM0.8.5+cu118; Qwen3 startup/inference PASS | UNVERIFIED; exact release/quant/parser 검증 필요 |
| Model | Qwen3-14B-AWQ 실측, 8B 비교 준비; 최종 미선정 | 같은 logical model 우선, 양자화 artifact 차이는 명시 |
| dtype | 14B-AWQ FP16 activation; 8B BF16 비교 예정 | 미정; 32GB 전체 runtime fit 검증 필요 |
| quantization | 14B awq_marlin W4A16 actual PASS; FP8/NVFP4 미검증 | INT4/FP8/NVFP4는 모델/CC12.0 kernel별 검증 필요 |
| context | 4096 tokens 실제 launch, concurrency1 | 같은 contract/평가 context 우선; fit UNVERIFIED |
| tensor parallel | MEASURED1, GPU3 only | PLANNED1, 실행 없음 |
| GPU memory fraction | 0.50 + KV256blocks, preflight/watchdog 실행 | config0.50 시작안; 실측 아님 |
| Runtime status | CANDIDATE_INFERENCE_VERIFIED; peak+margin 공존 guard 사용 | UNVERIFIED / 서버 접근 불가 |
| Benchmark status | 14Bv1 seed60: schema60/60, 의미45/60; 품질 개선·비교 중 | NOT_RUN / 어떠한 PASS도 없음 |
| Docker | CLI28.1.1만 확인; daemon/GPU toolkit 미확인 | UNVERIFIED |
| Frontend runtime | system node10.19.0/npm6.14.4 관측; 프로젝트용 미선택 | UNVERIFIED; Phase9에서 공통 요구 버전 결정 |
| Network | 모델127.0.0.1:8003 실제 실행/종료; Backend/Frontend 후속 | 같은 port 예제만; 실제 hostname/port 미확인 |

공식 근거와 host 조사는 [environment.md](environment.md), 모델별 실제 weight 크기/라이선스/지원은 [model_selection_plan.md](model_selection_plan.md)에 기록한다. 행마다 설치/측정 일시, exact wheel/model revision, git commit, 검증 명령과 결과 artifact 경로를 추가해 갱신한다.

## 이후 validation gate

1. 허용 physical GPU만 free VRAM/utilization을 반복 측정하고 후보 peak+margin과 비교한다. 충분한 예산을 입증하지 못한 후보는 실행하지 않는다.
2. 디스크 peak 계획과 여유 확인. GPU별 호환 wheel/tag/Python/Torch/vLLM/quant kernel을 고정한다.
3. model revision/tokenizer/template/parser/schema의 hash를 기록한다. 가중치 다운로드는 1개씩 한다.
4. 선택 GPU만 노출한 단일 장치 확인 후 startup/JSON/schema/tool parser/한국어 계약을 시험한다.
5. [evaluation plan](model_evaluation_plan.md)의 전체 metric과 OOM/restart 결과를 남긴다.
6. RTX5090 접속 가능 시 위 절차를 현장에서 반복한다. 같은 commit과 공통 semantic regression set으로 비교한다.

현재 driver535에서 Qwen3용 cu118 경로를 실제 검증했다. 더 최신 architecture의 runtime 경로는 별도 과제다. A100에서 메모리에 들어갈 것으로 보이는 것과 현재 이 서버에서 실행 가능한 것은 별개다.
