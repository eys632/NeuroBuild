# Phase 5 GPU budget preflight

최신 사용자 지침은 GPU3에 기존 process가 있다는 이유만으로 중단하는 정책을 변경했다. 허용 GPU의 실제 자원 여유를 측정하여 안전 margin을 유지하는 평가만 진행할 수 있다. 다른 사용자의 process/파일/환경을 조사하거나 변경·종료하지 않고 다른 GPU로 fallback하지 않는다. 이 도구는 **aggregate GPU memory/utilization만 read-only 조회**하며 process 목록을 요청하지 않는다.

`scripts/gpu_preflight.py`는 Python 표준 라이브러리만 사용한다. 서버에 맞는 profile과 정확한 CUDA mask를 명시한다. A100은 physical GPU **3**/mask `3`, RTX5090은 physical GPU **1**/mask `1`이다. 실행 환경을 자동 감지하거나 profile/mask를 바꾸지 않는다. A100에서 RTX profile 예제를 실행하면 안 된다. RTX profile의 synthetic test는 RTX 현장 측정을 뜻하지 않는다.

```sh
CUDA_VISIBLE_DEVICES=3 .conda/bin/python scripts/gpu_preflight.py \
  --profile a100 --estimated-peak-mib 24000
```

`24000`은 사용법을 위한 **가정값**이다. 실제 후보에 대해 weight, KV cache, workspace, CUDA context, allocator overhead를 포함하여 **startup/inference 중 더 큰 total peak**를 별도로 추정해야 한다. Weight 파일 크기만 넣거나 context/concurrency를 바꾸면서 이전 추정값을 재사용하지 않는다.

## 판단 규칙

기본값은 5번/1초 간격이다. 각 요청은 `nvidia-smi -i <허용 index> --query-gpu=memory.total,memory.free,memory.used,utilization.gpu --format=csv,noheader,nounits`로 제한하며 memory 단위는 MiB다. NVIDIA의 reserved memory 때문에 `used + free`가 `total`보다 작을 수 있으며 이를 사용 가능한 free로 더하지 않는다. [NVIDIA 공식 nvidia-smi 문서](https://docs.nvidia.com/deploy/nvidia-smi/index.html)

1. Profile/mask 불일치, query 실패, N/A/모르는 값, 복수 장치 출력, 불완전·비일관 숫자, total 변화는 거절한다.
2. Sample 중 utilization이 10%를 초과하거나 free memory의 최대-최소 차이가 256 MiB를 초과하면 거절한다. 일부 sample만 성공한 결과로 launch를 허용하지 않는다.
3. `minimum_free = min(각 sample의 free)`를 사용한다.
4. `margin = max(6144 MiB, ceil(minimum_free × 0.20))`를 남긴다.
5. `available_model_budget = max(0, minimum_free - margin)`이며 후보의 estimated total peak가 이 budget 이하여야 한다.

Flags로 sample/window, margin과 utilization/free-change threshold를 명시적으로 조정할 수 있다. Margin은 6144 MiB/20% 아래로 줄일 수 없다. Sample은 3~20개, interval은 0.1~5초이며 window는 최대 30초다. Utilization threshold는 최대 25%, free-change threshold는 최대 1024 MiB다. 더 보수적인 값으로 조정할 수 있으며 변경한 policy를 report에 그대로 남긴다.

## Report와 launch 연결

JSON `schema_version=1`에 profile/허용 index, sample별 total/free/used/utilization, 시작·종료 UTC, 실제 적용 policy, measured 집계와 estimated peak를 구분하여 기록한다. `allowed=true`/exit0의 의미는 **BUDGET_FITS_ESTIMATE**이며 runtime 실행·모델 fit·성능 검증 성공을 의미하지 않는다. 거절은 exit2와 `reason_codes`로 표시한다. 명령 문법 오류는 argparse 사용법과 exit2로 처리한다.

허용 시 `required_launch_limit.maximum_total_runtime_peak_mib`와 total VRAM 대비 내림한 `maximum_fraction_of_total_vram`을 제공한다. Launcher는 실제 runtime의 allocation/context/concurrency 설정으로 이 상한을 지켜야 한다. Phase0 profile의 계획값 `gpu_memory_utilization=0.90`을 그대로 사용하면 안 된다. Fraction 설정 하나가 모든 native allocation의 강제 상한이나 GPU 격리를 보장하는 것은 아니다. TP=1, 정확한 CUDA mask와 논리 device `cuda:0`을 유지한다.

Sampling 뒤 다른 workload가 성장할 수 있으므로 report는 예약/lock이 아니다. **Launch 직전에 다시 검사**하고 bounded startup/inference 측정으로 실제 peak와 OOM 여부를 검증해야 한다. 예상보다 높은 사용량, 메모리 부족 또는 불안정이 발생하면 해당 NeuroBuild 실행을 중단하여 재평가한다. 다른 사용자의 runtime을 변경하여 budget을 확보하지 않는다.

## 검증 범위

`tests/test_gpu_preflight.py`는 fake nvidia-smi rows와 injected query/sleep만 사용한다. Mask/index 범위, reserved memory 처리, min-free/margin/peak 경계, high utilization/free swing, N/A/invalid/partial readings, query 실패와 report를 검증한다. 이 테스트는 실제 GPU를 조회하거나 모델을 실행하지 않는다. 실제 sampling/startup/inference 결과는 Phase5 보고에서 별도 근거로 남긴다.

## Guarded model server

`scripts/model_server.py`는 Backend Python에서 실행하는 foreground guard다. 모델 서버는 프로젝트 `.conda-vllm/bin/python`으로 별도 process group에 생성한다. 명령 예시의 model directory는 미리 내려받아 검증한 실제 local directory로 지정한다. 실행기는 모델을 다운로드하지 않는다.

```sh
CUDA_VISIBLE_DEVICES=3 .conda/bin/python scripts/model_server.py \
  --profile a100 \
  --model-path var/models/<downloaded-model-directory> \
  --dtype half \
  --estimated-peak-mib 18432 \
  --served-model-name neurobuild-candidate \
  --port 8003 \
  --log-file var/logs/model-server.log \
  --report-file var/reports/model-server.json \
  --max-seconds 1800
```

Model/log/report 경로는 checkout 기준으로 해석하므로 다른 working directory에서도 같은 결과다. Model은 checkout 내부, log/report/cache는 `var/` 내부여야 한다. Model directory에는 `config.json`이 필요하다. Report는 원자적으로 교체하고 log는 append한다. 실제 manifest hash 검증은 다운로드 단계의 책임이며 launcher의 directory 확인이 모델 진위 검증을 대체하지 않는다. `--served-model-name` 기본값은 `neurobuild-local`이며 HTTP 요청의 `model`과 같아야 한다.

현재 build는 **A100만 실행**한다. `rtx5090` profile 이름은 인식하지만 `RUNTIME_PROFILE_NOT_VALIDATED`로 GPU 조회·launch 전에 거절한다. cu118 build는 RTX5090 SM120 검증 대상이 아니므로 별도 runtime 검증 후에만 physical GPU1 지원을 활성화할 수 있다.

실행 직전에 위 preflight를 다시 수행하고, `CUDA_VISIBLE_DEVICES=3`과 `CUDA_DEVICE_ORDER=PCI_BUS_ID`를 유지한다. 자식은 `nvidia-smi -i 3 --query-gpu=uuid`로 허용 장치 UUID만 읽어 PyTorch의 단일 logical device0과 비교한다. 일치하지 않으면 모델을 올리지 않는다. 다른 장치/프로세스 metadata는 읽지 않는다.

초기 옵션은 vLLM0.8.5 V0, TP1, `uni`, frontend multiprocessing off, eager, context4096, seq1, KV block256, swap0, prefix caching off, xgrammar다. `--max-model-len`은 256~4096으로 제한하고 block 수를 길이에 맞춘다. 서버는 `127.0.0.1`에만 bind하며 request/access log를 끈다. HF/Transformers offline과 프로젝트 HF/Torch/Triton/CUDA/vLLM/XDG/TMP cache를 명시한다. [옵션과 후보 근거](runtime_candidate_feasibility.md)

`--gpu-memory-utilization`과 `--torch-memory-fraction`은 기본0.50이며 둘 모두 `ceil(fraction × total_VRAM) <= measured_model_budget`이어야 한다. 후속 BF16 후보에0.60 등을 명시할 수 있으나 새 preflight를 통과해야 한다. Torch allocator cap은 같은 프로세스에서 vLLM을 시작하기 전에 설정한다. `--no-torch-cap`은 비교 실험에서 명시적으로만 사용하고 보고서에 null로 남긴다. 이 cap은 PyTorch allocator 대상이며 다른 native CUDA allocation 전체를 강제로 제한하지 않는다.

Guard는 명목0.5초 간격으로 GPU3 aggregate memory를 읽는다(query timeout은5초). 다음 경우 **자기가 생성한 process group만** 종료한다.

- GPU query 실패, 잘못된/N/A 값 또는 total VRAM 변화.
- 현재 free가 preflight의 `max(6144MiB, ceil(min_free × 0.20))` 미만.
- 현재 used에서 preflight의 최소 used를 뺀 증가량이 `min(estimated_peak + allowance, model_budget)` 초과. Allowance는 기본1024MiB이며0~1024로만 명시할 수 있다.
- `--max-seconds` 만료, guard가 받은 SIGINT/SIGTERM 또는 자식 종료.

SIGTERM grace는 최대10초, 그 후 SIGKILL과 최대5초 reap을 사용한다. 리더를 `waitid(WNOWAIT)`로 관찰해 group ID 재사용을 방지한 상태에서, 리더가 TERM에 먼저 종료했더라도 남은 자체 descendant에 SIGKILL을 보낸 다음 리더를 회수한다. 자식 bootstrap은 torch import 전에 Linux `PR_SET_PDEATHSIG(SIGKILL)`과 예상 guard PID 재검사를 설정한다. Guard가 SIGKILL 등으로 사라져도 모델 프로세스는 커널에 의해 종료된다. 이 보장은 same-process V0/uni 엔진을 전제로 한다. 다른 프로세스/그룹을 찾거나 종료하는 기능은 없다. [Linux parent-death signal](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html), [waitid/WNOWAIT](https://man7.org/linux/man-pages/man2/waitpid.2.html)

JSON report에는 preflight, 적용 cap/여유/증가량 한계, 감시 sample 수, 최소 free, `observed_baseline_relative_peak_mib`, elapsed, 종료 사유와 자체 child 종료 결과가 있다. `RUNNING`은 HTTP health/inference 성공을 의미하지 않는다. 종료 확인 실패는 `STOP_FAILED`이며 exit2다. 정상 요청 종료/시간 만료/자식 exit0은 자체 child 회수 확인 시 exit0이다. Raw prompt/response, 환경변수/secret, reasoning은 report에 저장하지 않는다.

**Baseline 대비 aggregate 증가량은 개별 모델 프로세스의 peak 측정이나 보장된 상한이 아니다.** 다른 workload 증가가 포함될 수 있고 다른 workload의 해제가 모델의 증가를 가릴 수도 있다. Sample 사이의 순간 peak 역시 놓칠 수 있다. Report는 `per_process_measurement=false`, `memory_fit_guaranteed=false`를 명시한다. Free-floor 감시와 allocator cap을 함께 사용하되 안전한 startup/inference 실측을 별도로 확인해야 한다.

`tests/test_model_server.py`는 fake GPU readings/child로 허용·거절·cap·query 오류·여유 침범·증가량 초과·자체 그룹 신호·report 실패를 검증한다. 추가 두 Linux CPU-only lifecycle test는 자신이 만든 작은 Python 프로세스만 사용해 parent-death SIGKILL과 TERM을 무시하는 자체 descendant 정리를 검증한다. Torch import, GPU 조회, 실제 모델 실행은 이 테스트에 없다.
