# Neurobuild Real v2

Streamlit 기반 건축설계 에이전트입니다. CEO 요청을 입력하면 기획팀, 법무팀, 디자인팀, 예산팀, 설계팀이 순서대로 검토하고 2D 평면, 3D BIM 프리뷰, IFC 파일, JSON 보고서를 생성합니다.

## 핵심 기능

- AI 직원 스탠드업 화면: 네모 대신 머리, 몸통, 팔, 다리가 있는 사람형 아이콘이 움직입니다.
- BIM 뷰어: 생성된 IFC 텍스트를 브라우저에서 web-ifc 계열 로더로 먼저 읽고, 실패하면 Three.js BIM 프리뷰로 자동 전환합니다.
- Hugging Face 연결: `.env`의 `HF_TOKEN`과 팀별 모델 설정을 사용해 OpenAI 호환 Chat Completion API를 호출합니다.
- fallback 생성: Hugging Face 호출이 실패해도 도면, IFC, 보고서는 생성됩니다.

## Windows 실행

```powershell
cd "C:\Users\imw37\OneDrive\바탕 화면\efinal\neurobuild_real_v2"
.\run_windows.ps1
```

현재 Python 3.14 환경에서는 `requirements.txt`가 `streamlit==1.58.0`을 사용합니다.

## Linux 실행

```bash
cd ~/neurobuild_work/neurobuild_real_v2
chmod +x run_linux_no_sudo.sh
./run_linux_no_sudo.sh
```

## 환경 변수

`.env.example`을 `.env`로 복사한 뒤 Hugging Face User Access Token을 넣습니다.

```env
USE_HF_LLM=1
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Inference Providers를 실제 호출하려면 Hugging Face 토큰에 `Make calls to Inference Providers` 권한이 필요합니다. 권한이 없으면 앱은 fallback 보고서로 계속 동작합니다.

## 접속 주소

```text
http://127.0.0.1:8502
```

## 산출물 위치

```text
outputs/
```

생성된 `.ifc`와 `.report.json` 파일이 저장됩니다.

## 빠른 검증

```powershell
.\.venv\Scripts\python.exe scripts\test_generate.py
```
