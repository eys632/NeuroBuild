# Common Backend environment

2026-09-20 A100에 project `.conda`, Python3.12.14를 만들었다. Phase1 Domain은 표준 라이브러리만 사용한다.
Phase2에서 실제 transaction 검증을 위해 PostgreSQL17.11과 psycopg3.2.10을 추가했다.
Conda는 Python/pip/build 도구와 PostgreSQL/client를 공급하며 base에 프로젝트 dependency를 설치하지 않는다.

- `backend.environment.yml`: 이식 가능한 환경 의도. conda-forge만 사용한다.
- `backend-linux-64.conda.lock`: Python과 모든 resolved Conda package URL/SHA256. Linux x86_64용이며 RTX5090 현장 검증은 아직 없다.
- root `pyproject.toml`: Application metadata/build 정의. Domain의 외부 dependency는 없으며 infrastructure는 psycopg를 사용한다.

환경이 없는 새 checkout에서 디스크/기존 환경을 먼저 확인한 다음 실행한다. 아래 명령은 기존 환경을 삭제하지 않는다.

```sh
source "$HOME/miniconda3/etc/profile.d/conda.sh"
export CONDA_PKGS_DIRS="$PWD/var/cache/conda/pkgs"
conda create -p "$PWD/.conda" --file requirements/backend-linux-64.conda.lock
conda activate "$PWD/.conda"
command -v python
python --version
python -m pip --version
echo "$CONDA_PREFIX"
python -m pip install --no-build-isolation --no-deps -e .
bash scripts/test_backend.sh
```

Miniconda bootstrap는 [공식 index](https://repo.anaconda.com/miniconda/)의
`Miniconda3-py312_26.7.1-1-Linux-x86_64.sh`, SHA256
`b27f60ab63e77eeab50a5417c989120f767e863df32400190d4c7262369f8695`로 검증했다.
설치 위치는 A100에서 `~/miniconda3`, base 자동 활성화는 false, shell init은 수행하지 않았다.
다른 서버에서는 공식 host 지원과 hash를 확인한 뒤 동일 위치 정책을 적용한다.

PostgreSQL lifecycle과 실제 통합 테스트는 root README를 따른다. Phase3 IfcOpenShell은 해당 Phase에서 사유와 lock를 추가한다.
torch/vLLM/Transformers/CUDA wheel은 `.conda-vllm`에만 둔다. 모델 환경은 현재 미생성이다.
