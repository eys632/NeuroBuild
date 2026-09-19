# A100 model runtime — Phase5 검증 진행

프로젝트 `.conda-vllm` Python3.12.14와 공식 **vLLM0.8.5+cu118 / PyTorch2.6.0+cu118**를 설치했다. pip check 및 torch/vllm._C/번들 FlashAttention2/xgrammar import는 통과했다. GPU3 startup/JSON inference를 실제 통과했다. 14B-AWQ의 첫 seed 의미 rubric은45/60으로 부족하여 품질 개선·후보 비교를 진행 중이다. 시스템 driver535.183.01, CUDA11.8, glibc2.31을 변경하지 않았다. Backend `.conda`에는 GPU dependency를 설치하지 않는다.

재현 정의:

- `python-linux-64.conda.lock`: Python/pip 및 개인 환경의 native library SHA256 URL.
- `model-runtime.in`: 선택한 runtime/build와 호환 제약의 근거.
- `model-runtime.lock`: resolver의 148개 정확한 wheel과 SHA256.
- `model-runtime.freeze.txt`: 설치 직후 pip freeze.
- `model.environment.yml`: 환경 목적과 Python 버전.
- `../models/qwen3-14b-awq.json`: 첫 후보의 full model revision, 11개 파일 크기/해시.

기존 환경과 디스크를 먼저 확인한다. 없는 환경을 생성할 때만 다음을 사용한다. 환경 생성 후 python/pip/CONDA_PREFIX가 해당 프로젝트를 가리키는지 확인하고 설치한다.

```sh
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

실제 실행/평가 결과는 [Phase5 보고](../../docs/reports/phase5_report.md)에 기록한다. Import 성공이나 구성 파일의 존재를 startup/품질 성공으로 간주하지 않는다.
