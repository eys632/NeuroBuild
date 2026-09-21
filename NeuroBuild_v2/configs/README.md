# Runtime / network profile

공통 non-secret 실행 설정이다. A100은 Qwen3-14B-AWQ/promptv3의 실제 개발 seed 추론을 검증했고 RTX5090은 PREDICTED_UNVERIFIED다. 설정을 읽는 행위는 서비스의 현재 건강 상태를 증명하지 않는다.

설정 우선순위는 `common.json` → 선택한 `a100.json` 또는 `rtx5090.json` → 아래 허용된 환경변수다. Profile은 `--profile` 또는 `NEUROBUILD_PROFILE`로 반드시 지정한다. 둘 다 지정하면 CLI가 우선하며, hostname/GPU 자동 감지나 fallback은 없다.

| 환경변수 | 설정 |
| --- | --- |
| `PUBLIC_BASE_URL` | `network.public_base_url` |
| `FRONTEND_BASE_URL` | `network.frontend_base_url` |
| `API_BASE_URL` | `network.api_base_url` |
| `MODEL_SERVER_URL` | `network.model_server_url` |
| `NEUROBUILD_MODEL_ID` | `runtime.model_id` (빈 문자열은 미선정) |

URL은 `http://host[:port]` 또는 `https://host[:port]` 형태의 origin만 허용한다. 마지막 `/`는 가능하지만 경로, 사용자 정보, query, fragment는 거절한다. API 경로나 model endpoint 경로는 향후 공통 API adapter가 관리한다. 실제 배포 주소는 shell 환경변수 또는 향후 deployment 설정으로 공급한다. `runtime.env.example`은 참고 파일이며 script는 `.env` 파일을 읽거나 shell에서 source하지 않는다. Secret을 이 파일 또는 출력용 설정에 넣지 않는다.

```sh
# Project root에서: 시스템 Python은 이 stdlib 기반 정보 조회에만 사용한다.
/usr/bin/python3 scripts/show_runtime_info.py --profile a100
/usr/bin/python3 scripts/show_runtime_info.py --profile a100 --json

# 다른 cwd에서도 script 위치를 기준으로 설정/Git을 찾는다.
NEUROBUILD_PROFILE=a100 /usr/bin/python3 /home/a202192020/NeuroBuild_v2/scripts/show_runtime_info.py
```

`--profile rtx5090`으로 A100에서 설정을 열람할 수 있지만 이는 RTX5090 접속/실행/검증이 아니다. 출력 hostname은 script를 실행한 현재 host이며, GPU 정보와 상태는 profile에 기록된 값이다. GPU interrogation, port check, health check, model loading, network 호출은 수행하지 않는다. Git commit과 dirty 여부는 checkout에서 read-only로 확인한다. Git이 없거나 checkout 정보가 없으면 `UNKNOWN`/`null`을 표시한다.

A100의 허용 physical GPU는 **3**, RTX5090은 **1**이다. 각각 `CUDA_VISIBLE_DEVICES=3`, `CUDA_VISIBLE_DEVICES=1`만 허용하며 process 내부 device는 `cuda:0`이다. GPU index는 환경변수로 override할 수 없다. 현재 shell의 `CUDA_VISIBLE_DEVICES`가 설정값과 다르면 정보 도구도 실패하며, 빈 mask나 복수 GPU mask도 허용하지 않는다. Mask가 아직 없으면 필요한 값을 출력하고 설정하거나 GPU를 사용하지 않는다. 실제 실행 전에는 해당 GPU의 점유를 별도로 확인해야 한다.

선정 모델은 Qwen3-14B-AWQ의 pinned revision/promptv3다. A100은 TP1/gpu_memory_utilization0.50/context4096/max_tokens768/FP16/AWQMarlin을 실측했다. 매번 GPU budget preflight가 필요하며 설정만으로 fit을 보장하지 않는다. A100 protocol은 legacy_guided_json, RTX 계획은 structured_outputs다. dialect 자동fallback은 없다. URL localhost:3000/8000은 향후 frontend/API 기본값,8003은 local model 기본값이며 설정 조회는 포트를 예약하지 않는다. 조사 당시 점유된 8001/8002/8010은 기본값으로 사용하지 않는다.

`paths`는 checkout root 기준 상대 경로다. Backend `.conda`는 Python 3.12를 계획하고 `.conda-vllm`의 Python/build는 runtime 호환성 검토 후 정한다. 이 script의 Python 3.8 호환성은 서버 기본 정보 조회를 위한 것이며 Application 개발 환경 버전을 정하지 않는다. 설정 로딩은 경로/환경/캐시 디렉터리를 생성하지 않는다.
