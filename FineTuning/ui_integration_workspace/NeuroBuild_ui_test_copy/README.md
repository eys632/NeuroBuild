# IFC MVP (Prompt → IFC → 3D Viewer → Download)

프롬프트를 입력하면 IFC를 생성하고, 브라우저에서 3D로 확인한 뒤 IFC를 다운로드할 수 있는 로컬 MVP입니다.

- 백엔드: FastAPI (IFC 생성/수정 API + 정적 웹)
- IFC 생성: ifcopenshell
- 3D 뷰어: three.js + web-ifc-three (브라우저에서 IFC 로딩)
- LLM(선택):
  - 내장 모드: Transformers로 `Qwen/Qwen2.5-7B-Instruct` 로컬 추론
  - 분리 모드: vLLM(OpenAI 호환 API) 서버를 따로 띄우고 백엔드는 HTTP로 호출

접속 URL은 기본적으로 `http://127.0.0.1:<PORT>/` 입니다.

---

## 폴더 구조

- `backend/`: FastAPI 서버 및 IFC/LLM 로직
- `web/`: 브라우저 뷰어(단일 페이지)
- `models/`: Hugging Face 캐시(HF_HOME). 모델이 자동 다운로드됨
- `output/`: 생성된 IFC (`<uuid>.ifc`)

---

## 설치

```bash
cd /home/eys632/26-2project

python -m venv .venv
. .venv/bin/activate

pip install -r requirements.txt
```

모델은 최초 실행 시 `models/`에 자동 다운로드됩니다(기본 `HF_HOME=$PWD/models`).

---

## 실행 (권장 2가지)

### A) 단일 프로세스 실행 (내장 LLM 사용)

LLM 서버를 따로 띄우지 않고, FastAPI가 Transformers로 직접 추론합니다.

```bash
cd /home/eys632/26-2project
HOST=0.0.0.0 PORT=8000 ./run.sh
```

- 접속: `http://127.0.0.1:8000/`
- GPU가 있으면 자동으로 GPU 0번을 사용합니다(CPU도 가능하지만 매우 느릴 수 있음).

### B) vLLM 분리 실행 (LLM 서버 + 웹/백엔드 서버 분리)

포트 충돌을 피하려면 **vLLM과 웹/백엔드를 서로 다른 포트**로 띄워야 합니다.
아래 예시는 “vLLM=8000, 웹/백엔드=8001” 구성입니다.

#### 1) vLLM 실행 (단일 GPU 예시)

vLLM이 설치되어 있지 않다면(옵션 기능):

```bash
pip install vllm
```

```bash
cd /home/eys632/26-2project
. .venv/bin/activate

pkill -f "vllm serve" || true

export CUDA_VISIBLE_DEVICES=0
export HF_HOME=$PWD/models

vllm serve Qwen/Qwen2.5-7B-Instruct \
  --served-model-name qwen25-7b \
  --host 0.0.0.0 --port 8000 \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --trust-remote-code \
  --enforce-eager
```

vLLM 응답 확인:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/v1/models | head

curl -sS http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen25-7b","temperature":0,"max_tokens":64,"messages":[{"role":"user","content":"ping"}]}' | head
```

#### 2) 웹/백엔드 실행 (vLLM 연결)

백엔드가 내장 Transformers 대신 vLLM을 호출하도록 환경변수를 설정합니다.

```bash
cd /home/eys632/26-2project

export VLLM_BASE_URL=http://127.0.0.1:8000
export VLLM_MODEL=qwen25-7b

HOST=0.0.0.0 PORT=8001 ./run.sh
```

- 접속: `http://127.0.0.1:8001/`

> 포트를 바꾸고 싶다면: vLLM 또는 웹/백엔드 중 한쪽만 바꾸면 됩니다.
> 예) 웹을 8000으로 쓰고 싶으면 vLLM을 8002 같은 다른 포트로 띄운 뒤 `VLLM_BASE_URL`만 바꾸세요.

---

## 웹에서 사용 방법

1) 브라우저에서 `/` 접속
2) 프롬프트 입력 후 **생성/수정 실행**
3) 우측 3D 뷰어에서 IFC 로딩 확인
4) **IFC 다운로드** 링크로 파일 저장

수정(멀티턴)은 `base_file_id`를 이용합니다.
- 첫 생성 후에는 브라우저가 `last_file_id`를 저장하고, 다음 요청을 “기존 도면에 적용(수정)”으로 보냅니다.
- 서버가 재시작되면 메모리 상태가 초기화되므로, 예전 `base_file_id`는 더 이상 유효하지 않을 수 있습니다.

---

## 프롬프트 예시

치수/기본 형태:
- `12x9x3.2 wall=0.25 slab=0.15`
- `width=15 depth=10 height=4`
- `가로 20 세로 12 높이 4`

수정(지원되는 편집만 확실히 적용):
- `창문을 모두 제거해`
- `모든 외벽에 창문을 벽마다 2개씩`
- `창문 크게(large)로`
- `욕실 쪽 외벽 창문은 빼줘`
- `외벽에 밖으로 나갈 수 있는 문 추가해줘`
- `화장실 하나 추가해줘`
- `화장실 2개로 해`

---

## API 요약

아래 예시에서는 백엔드 URL을 변수로 둡니다(포트는 실행 구성에 맞게 바꾸세요).

```bash
export BACKEND=http://127.0.0.1:8000
# 분리 모드라면 예: export BACKEND=http://127.0.0.1:8001
```

### IFC 생성/수정: `POST /api/generate`

요청:

```bash
curl -sS $BACKEND/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"12x9x3.2","use_llm":true,"base_file_id":null}' | head
```

응답 핵심 필드:
- `file_id`: 생성된 IFC의 UUID
- `file_url` / `download_url`: `/api/files/<uuid>.ifc`
- `parsed.applied_ops` / `parsed.skipped_ops`: 수정 요청에서 적용/미적용된 작업 목록

### 에이전트 생성/수정(검증 후 필요 시 재시도): `POST /api/agent/generate`

지원 intent 일부에 대해 “요구가 반영됐는지”를 확인하고, 미반영이면 더 명시적인 프롬프트로 1~N회 재시도합니다.

```bash
curl -sS $BACKEND/api/agent/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"창문을 모두 제거해","use_llm":true,"base_file_id":null,"max_iters":2}' | head
```

응답:
- `iterations[]`: 각 시도별 `verification.unmet`, `next_prompt` 포함
- `final`: 최종 생성 결과(`/api/generate`와 동일 스키마)

### 프롬프트 구조화(초기 설계 해석): `GET/POST /api/interpret`

```bash
curl -sS "$BACKEND/api/interpret?prompt=%EA%B0%80%EB%A1%9C%2012%20%EC%84%B8%EB%A1%9C%209%20%EB%86%92%EC%9D%B4%203" | head
```

### IFC 다운로드: `GET /api/files/<uuid>.ifc`

브라우저에서 내려받거나, CLI로 저장:

```bash
curl -L -o out.ifc $BACKEND/api/files/<uuid>.ifc
```

---

## 편집이 “확실히” 적용되는 방식 (Ops 기반)

이 프로젝트는 “아무 말이나 프롬프트로 던지면 조용히 무시되는” 실패를 줄이기 위해,
수정 요청을 **지원되는 작업 목록(Ops)** 으로 바꾼 뒤 서버가 그 Ops만 적용합니다.

- 적용된 작업은 `parsed.applied_ops`에 기록
- 지원하지 않거나 애매한 작업은 `parsed.skipped_ops`에 기록(왜 못 했는지 힌트 포함)

현재 지원 Ops(요약):
- 창문: `remove_all_windows`, `set_windows_per_wall`, `set_windows_size_preset`, `set_avoid_bathroom_zone`
- 외벽 출입문: `set_exterior_door`
- 욕실/화장실: `set_bathroom_count`, `add_bathroom`(누적)

---

## 트러블슈팅

- `Unknown base_file_id` 오류: 서버 재시작으로 메모리 상태가 초기화된 경우입니다. 새로 생성부터 다시 시작하세요.
- vLLM을 쓰는데 백엔드가 GPU를 잡는 것 같음: `VLLM_BASE_URL`이 설정돼 있는지 확인하세요. 설정되면 백엔드는 vLLM로만 호출합니다.
- 모델 저장 위치 확인: `HF_HOME`이 없으면 기본으로 `models/`를 사용합니다.
  - 예) `du -sh models`
- 포트 충돌: vLLM과 웹/백엔드는 같은 포트를 동시에 사용할 수 없습니다. 한쪽 포트를 바꾸고 URL/env를 맞추세요.
