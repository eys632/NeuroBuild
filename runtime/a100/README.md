# A100 model runtime — Phase5 실제 검증

이 문서의 14B 선택과 실행 예시는 **Phase5의 과거 checkpoint 재현용**이다.
Phase5.x에서는 같은 환경에서 4B 및 30B-A3B instruction 후보를 추가 비교했다.
현재 MoE 서버의 실측 설정은 [launch 기록](../../evaluations/results/phase5x/moe-instruct-v1-launch/),
품질 gate와 다음 비교는 [STATUS](../../docs/STATUS.md)를 따른다. 확대 평가의 최종 모델은 아직 선정하지 않았다.

프로젝트 `.conda-vllm` Python3.12.14와 공식 **vLLM0.8.5+cu118 / PyTorch2.6.0+cu118**를 설치했다. pip check 및 torch/vllm._C/번들 FlashAttention2/xgrammar import는 통과했다. GPU3 startup/JSON inference를 실제 통과했다. 14B-AWQ promptv3를 내부 개발용으로 선정했다. 고정 development seed20×3에서 schema/parser/자동 의미60/60, READY오판0/33이다. 자동생성 gold이며 heldout/human 정확도가 아니다. 시스템 driver535.183.01, CUDA11.8, glibc2.31을 변경하지 않았다. Backend `.conda`에는 GPU dependency를 설치하지 않는다.

재현 정의:

- `python-linux-64.conda.lock`: Python/pip 및 개인 환경의 native library SHA256 URL.
- `model-runtime.in`: 선택한 runtime/build와 호환 제약의 근거.
- `model-runtime.lock`: resolver의 148개 정확한 wheel과 SHA256.
- `model-runtime.freeze.txt`: 설치 직후 pip freeze.
- `model.environment.yml`: 환경 목적과 Python 버전.
- `../models/qwen3-14b-awq.json`: 첫 후보의 full model revision, 11개 파일 크기/해시.

기존 환경과 디스크를 먼저 확인한다. 없는 환경을 생성할 때만 다음을 사용한다. 환경 생성 후 python/pip/CONDA_PREFIX가 해당 프로젝트를 가리키는지 확인하고 설치한다.

```sh
cd /home/a202192020/NeuroBuild_v2
source "$HOME/miniconda3/etc/profile.d/conda.sh"
export CONDA_PKGS_DIRS="$PWD/var/cache/conda/pkgs"
conda create -p "$PWD/.conda-vllm" --file runtime/a100/python-linux-64.conda.lock
conda activate "$PWD/.conda-vllm"
command -v python
python --version
python -m pip --version
echo "$CONDA_PREFIX"
df -h /
export PIP_CACHE_DIR="$PWD/var/cache/pip-model"
export TMPDIR="$PWD/var/tmp"
mkdir -p "$TMPDIR"
python -m pip install --require-hashes --only-binary=:all: --no-deps -r runtime/a100/model-runtime.lock
python -m pip check
```

`ray[cgraph]`가 요구하는 cupy-cuda12x13.4.1은 metadata를 만족하기 위해 기록한다. 실제 serving은 V0/uni 단일 process이며 CUDA12 cgraph는 실행하지 않는다. 이 cu118 build를 RTX5090 SM120용으로 주장하지 않는다. RTX runtime은 별도 검증 대상이다.

GPU3 only, mask3, logical cuda:0, TP1이다. 시작 직전 [GPU budget guard](../../docs/gpu_budget.md)가 측정 free VRAM과 peak+margin을 비교한다. 현재 다른 process 점유 자체는 blocker가 아니며 다른 GPU fallback이나 타인 process 변경은 금지한다. initial context4096/seq1/eager/gpu utilization0.50/KV256 blocks를 사용한다.0.50은 모든 allocation을 제한하는 hard GPU isolation이 아니다.

모델 다운로드는 `.conda/bin/python scripts/download_model.py runtime/models/qwen3-14b-awq.json`으로 프로젝트 var 아래에 저장한다. 파일별 size/SHA256검증과 20GiB root disk reserve를 적용하며 모델 remote code를 사용하지 않는다.

선정한 모델을 다시 시작할 때는 검증된 local weight와 위 환경을 사용한다. 다음은
Phase5 14B checkpoint의 명시적 launch 설정이다. `configs/*.json`을 변경해도 이 CLI의 인자가
자동으로 바뀌지는 않는다. 실행기는 **매번 새 preflight**에서 GPU3의 현재 free/utilization을
측정하고 예상 peak18432MiB와 안전 여유를 비교한다. 과거의 여유7275MiB나 fit 결과를
새 실행의 허가로 재사용하지 않는다. 이미 이 프로젝트 guard가 실행 중이면 lock 때문에
두 번째 실행은 거절된다.

```sh
cd /home/a202192020/NeuroBuild_v2
nb_run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
CUDA_VISIBLE_DEVICES=3 .conda/bin/python scripts/model_server.py \
  --profile a100 \
  --model-path var/models/Qwen--Qwen3-14B-AWQ/31c69efc29464b6bb0aee1398b5a7b50a99340c3 \
  --dtype half \
  --estimated-peak-mib 18432 \
  --gpu-memory-utilization 0.50 \
  --torch-memory-fraction 0.50 \
  --max-model-len 4096 \
  --served-model-name neurobuild-local \
  --port 8003 \
  --log-file "var/logs/qwen3-14b-awq-${nb_run_id}.log" \
  --report-file "var/reports/qwen3-14b-awq-${nb_run_id}.json" \
  --max-seconds 3600
```

Guard는 foreground에서 자식을 감시한다. 정상 중단은 해당 guard terminal의 Ctrl-C를
사용하며 다른 프로세스를 찾거나 종료하지 않는다. 매번 새 log/report 이름을 사용한다.
Guard report는 현재 상태를 갱신하는 파일이고, 평가 run 및 listener proof는 별도의
새 파일로 보존한다. `RUNNING`은 HTTP health/추론 성공의 증거가 아니다. 시작 후
[자체 PID listener 검사](../../docs/model_listener_check.md)로 report의 `child_pid`만
검사하고, [평가 명령](../../docs/evaluation_harness.md)의 `--model`도 반드시
`neurobuild-local`과 맞춘다.

[Phase5.x launch 기록](../../evaluations/results/phase5x/launch_config.json)과
[runtime metadata](../../evaluations/results/phase5x/runtime_metadata.json)는 측정한
한 실행의 보존 예시다. 새 실행의 버전·template·launch 정의를 확인해 해당 metadata와
hash를 새로 기록한다. 보관된 metadata를 새 서버의 자동 attestation으로 사용하지 않는다.

실제 실행/평가 결과는 [Phase5 보고](../../docs/reports/phase5_report.md)에 기록한다. Import 성공이나 구성 파일의 존재를 startup/품질 성공으로 간주하지 않는다.
