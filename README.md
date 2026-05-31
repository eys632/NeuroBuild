# NeuroBuild

이 레포지토리는 두 개의 독립된 작업공간으로 구성되어 있습니다.

- [origin/](origin): 프롬프트 → IFC 생성/수정 → 3D 뷰어 → 다운로드를 제공하는 본 프로젝트
- [FineTuning/](FineTuning): 원본 프로젝트와 분리된 fine-tuning / evaluation 작업공간

## 폴더 안내

### [origin/](origin)
NeuroBuild의 메인 애플리케이션입니다.

- FastAPI 기반 백엔드
- ifcopenshell 기반 IFC 생성/수정
- three.js + web-ifc-three 기반 브라우저 3D 뷰어
- Transformers 내장 모드 또는 vLLM 분리 모드 지원

실행 방법과 API 설명은 [origin/README.md](origin/README.md)를 참고하세요.

### [FineTuning/](FineTuning)
모델 실험과 평가를 위한 별도 공간입니다.

- 데이터셋 생성 및 검증
- SFT / LoRA 실험
- 베이스라인 및 어댑터 평가
- 제출용 리포트 및 결과물 정리

세부 실행 방법은 [FineTuning/README.md](FineTuning/README.md)를 참고하세요.

## 빠른 시작

### 메인 애플리케이션 실행

```bash
cd /home/eys632/NeuroBuild/origin
HOST=0.0.0.0 PORT=8000 ./run.sh
```

### fine-tuning 작업공간 준비

```bash
cd /home/eys632/NeuroBuild/FineTuning
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-train.txt
```

## 저장소 운영 원칙

- `origin/`은 애플리케이션 소스와 실행 파일만 담습니다.
- `FineTuning/`은 학습/평가/결과물만 담습니다.
- 가상환경, 모델 캐시, 생성물처럼 큰 파일은 커밋하지 않습니다.