# A100 환경 조사와 환경 구성 계획

후속 상태(2026-09-20): Phase1 진입 후 Miniconda26.7.1와 Backend `.conda` Python3.12.14를 설치했다. 설치 후 root96%/84G, base939M/Backend258M/var346M. 재현 정의는 [requirements](../requirements/README.md), 현재 상태는 [STATUS](STATUS.md)를 따른다. 아래 실측 표는 Phase0 당시 기록이다.

조사: 2026-09-19 18:00 KST 전후. 전역 `/home/a202192020/.codex/AGENTS.md`를 먼저 읽었다.
이번 Phase 0에서는 package, Miniconda, 환경, weight, PostgreSQL, frontend를 **설치하지 않았다**.

## 실측 결과

| 항목 | A100 관측값 |
|---|---|
| Project root | `/home/a202192020/NeuroBuild_v2`, 시작 시 빈 디렉터리 |
| OS / Kernel | Ubuntu 20.04.6 LTS / Linux 5.15.0-139-generic x86_64 |
| libc | glibc 2.31 |
| CPU | Intel Xeon Gold 5218R 2.10GHz × 2 socket, 40 physical cores / 80 logical CPUs |
| RAM / Swap | RAM 503GiB total, 477GiB available; swap 2GiB |
| Root / HOME filesystem | `/dev/nvme0n1p2`, 1.8T total, 1.7T used, 86G available, 96% used |
| 사용자 HOME | 약 1.7G: VS Code server 1.6G, Codex 142M, cache 24K |
| GPU3 | NVIDIA A100-PCIE-40GB, compute capability 8.0 |
| GPU3 VRAM | total 40960MiB, reserved 620MiB, used 3965MiB, free 36373MiB |
| NVIDIA driver | 535.183.01 |
| nvidia-smi CUDA 표시 | 12.2 (설치 Toolkit 버전과 다름) |
| CUDA Toolkit | `/usr/local/cuda` → alternatives, Toolkit 11.8 / nvcc V11.8.89 |
| Docker | CLI 28.1.1; daemon 접근/GPU container 지원은 확인하지 않음 |
| System Python | `/usr/bin/python3` 3.8.10; `python` 명령 없음 |
| System pip | `python3 -m pip` 24.3.1, `/usr/local/lib/python3.8/dist-packages/pip`; 사용/변경하지 않음 |
| Conda / 환경 | `conda` 없음, `~/miniconda3` 없음, `.conda`/`.conda-vllm`/`.venv` 없음; CONDA_PREFIX 비어 있음 |
| Node / npm / pnpm | `/usr/bin/node` v10.19.0, npm 6.14.4, pnpm PATH 없음 |
| PostgreSQL | psql/postgres/pg_ctl/pg_config PATH 없음; `/usr/lib/postgresql`, `/etc/postgresql` 없음; 5432 TCP listener 미관측 |
| Git / gh | Git 2.25.1, gh 없음; Git user.name/user.email 미설정 |

PostgreSQL은 위 범위에서 발견되지 않았다는 뜻이다. 다른 사용자 HOME/프로세스/container를 조사하지 않아 서버 전체 부재를 단정하지 않는다. Docker CLI 존재도 사용 권한이나 daemon health를 뜻하지 않는다.

## GPU 점유 발견

허용 GPU3에 예상하지 못한 compute process 3개가 있었다. `nvidia-smi -i 3 --query-compute-apps=pid,used_gpu_memory --format=csv`만 사용했다.

| 관측 PID | 보고된 VRAM |
|---|---:|
| 3869026 | 1746MiB |
| 3892606 | 1772MiB |
| 1137659 | 414MiB |

PID 소유자/명령행/메모리 내용은 조회하지 않았다. 종료/신호 전송/재설정하지 않았다. GPU 점유는 사용자에게 즉시 보고했으며 model 실행을 하지 않았다. 사용자가 GPU3 사용 가능 상태를 확인한 뒤에도 실행 직전 재확인해야 한다.
GPU0/1/2의 process 조사는 다른 사용자/GPU 접근 금지에 따라 생략했다. `nvidia-smi -i 3 -q`의 장치 수 표시는 4개지만 다른 GPU의 모델/상태는 측정하지 않았다.

## 포트 및 네트워크

`ss -H -ltn`으로 TCP listener만 확인했다. process/owner를 조회하지 않았다.
8001, 8002, 8005, 8010, 5174, 11434 등은 이미 수신 중이었다. 서비스의 소유자/내용은 조사하지 않았다.
3000(frontend), 8000(API), 8003(model), 5432(DB)는 당시 listener가 없어 **후보**로 정했다.
bind/reservation, firewall, 외부 접속, DNS를 검증하지 않았다. 실행 직전 재확인하고 충돌 시 명시적 설정을 바꾼다. 자동으로 다른 서비스에 연결하지 않는다.
예제는 `127.0.0.1`에 한정한다. 브라우저 접근은 향후 승인된 SSH tunnel 또는 별도 배포 설정으로 제공한다. PUBLIC_BASE_URL은 접속 안내용이며 listen host나 proxy 신뢰 설정을 자동 변경하지 않는다.

## 환경 2개 계획

| 경로 | 목적 / Python | dependency 정책 |
|---|---|---|
| `.conda` | Backend/Domain/persistence/IFC, Python **3.12** | psycopg, IfcOpenShell, jsonschema 등. 서버 간 동일 버전/lock. Phase 1에서 필요한 최소부터 단계별 추가 |
| `.conda-vllm` | local model server/GPU inference, Python **3.12 우선 검토** | vLLM이 요구하는 PyTorch/CUDA wheel/Transformers/xgrammar 조합을 함께 고정. 모델 및 build 확정 후 Python 버전 최종 결정 |

추가 test 환경은 만들지 않는다. Backend는 GPU package를 import하지 않는다. Miniconda 필요 시 `/home/a202192020/miniconda3`, base는 관리자용이며 자동 활성화는 끈다. 실제 설치 전 계획/용량을 제시하고 해당 단계의 설치 요청 범위에서 진행한다.
현재 `requirements/README.md`, `runtime/{a100,rtx5090}/README.md`는 계획서이며 설치 가능한 lock가 아니다. 검증하지 않은 version pin이나 빈 lock를 완료 결과로 만들지 않는다.

## Driver/Toolkit/runtime 구분

PyTorch/vLLM wheel의 CUDA runtime은 시스템 nvcc 11.8과 별개다. Conda 환경 생성만으로 호스트 driver 제약은 사라지지 않는다.
NVIDIA 문서의 CUDA12 minor compatibility 최소 driver 범위에는 535가 들어가지만 PTX/JIT와 새 driver 기능에는 제한이 있다. 따라서 CUDA12.8/12.9 wheel이 무조건 실패한다고도, 무조건 동작한다고도 판단하지 않는다. CUDA13의 일반 경로는 R580 이상을 요구하므로 현재 driver에서 최신 기본 wheel을 곧바로 설치하는 계획은 사용하지 않는다. [NVIDIA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)

최신 vLLM 문서는 Python 3.10–3.13 및 NVIDIA compute capability 7.5 이상을 안내하고 build별 PyTorch/CUDA 결합을 설명한다. 이것은 최신 모델별 release/quant kernel 지원 보장이 아니다. 해당 모델을 지원하는 정확한 vLLM commit/release, wheel의 CUDA/GLIBC tag, torch 빌드와 PTX/Triton 동작을 먼저 검토해야 한다. [vLLM GPU installation](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/)

RTX5090는 공식 사양상 Blackwell CC12.0/32GB다. PyTorch 2.7에서 CUDA12.8 Blackwell 지원이 도입됐지만 최신 2.12는 CUDA12.8 wheel을 더 이상 표준 제공하지 않고 새 Blackwell 경로로 CUDA13+를 안내한다. 따라서 오래된 최소 버전만 보고 배포 조합을 고정하지 않는다. RTX5090 실제 OS/driver는 아직 알 수 없다. [NVIDIA GPU](https://developer.nvidia.com/cuda/gpus), [PyTorch 2.7](https://pytorch.org/blog/pytorch-2-7/), [PyTorch 2.12](https://pytorch.org/blog/pytorch-2-12-release-blog/)

호환 조합을 찾지 못하면 model 검증을 blocked로 남기고 보고한다. sudo/driver 교체/system CUDA 변경/검증되지 않은 compatibility library 주입으로 우회하지 않는다. 필요 시 사용자가 관리자와 조율할 수 있지만 이번 작업에서 연락하거나 변경하지 않는다.

## Disk와 cache

96% 사용률은 대형 설치를 보류할 근거다. 86G가 model weight만 들어간다고 충분한 것은 아니다.
추가 peak 용량 = 환경 + Conda/pip 다운로드 및 압축해제 + model snapshot + 임시 다운로드 + compile cache + benchmark/artifact + 서버 공용 여유분.
향후 최소 50GiB 여유를 남기는 보수적 프로젝트 기준을 제안한다. 이는 서버 관리자 quota가 아니며 후속 설치 범위와 peak 용량 검토를 마치기 전에는 대형 다운로드하지 않는다. 공용 사용량 변동을 반영해 전후 `df -h /` 확인을 반복한다.

| 자료 | 계획 위치 |
|---|---|
| HF snapshot/model | `$PROJECT_ROOT/var/models/huggingface` (`HF_HOME`) |
| pip cache | `$PROJECT_ROOT/var/cache/pip` (`PIP_CACHE_DIR`) |
| Torch / Triton | `$PROJECT_ROOT/var/cache/torch`, `.../triton` |
| vLLM / CUDA compile | `$PROJECT_ROOT/var/cache/vllm`, `.../cuda` |
| Conda packages | `$PROJECT_ROOT/var/cache/conda/pkgs` (실제 생성 시 검토) |
| DB / artifact / run | `$PROJECT_ROOT/var/postgres`, `var/artifacts`, `var/runs` |

위 경로는 아직 만들지 않았다. 한 model snapshot을 cache와 별도 weight 디렉터리에 복제하지 않는다. 순차 평가하고 사용량을 확인하되 cache/모델 전체를 자동 삭제하지 않는다. `var/` 전체는 Git에서 제외한다.

## 재확인 절차

환경/패키지 설치 전, 그리고 대상 환경 활성화 후 아래 기본 확인을 다시 수행한다. Python 경로가 대상 prefix와 일치하지 않으면 설치를 중단한다.

```sh
pwd
command -v python || true
command -v python3 || true
python --version 2>/dev/null || true
python3 --version 2>/dev/null || true
python -m pip --version 2>/dev/null || true
python3 -m pip --version 2>/dev/null || true
echo "$CONDA_PREFIX"
df -h /
du -xhd1 "$HOME" 2>/dev/null | sort -hr
```

`show_runtime_info.py`의 system Python 실행은 stdlib를 통한 기본 상태 확인 용도에 한정한다. Python3.8을 Backend 개발 환경으로 채택한 것이 아니다.
