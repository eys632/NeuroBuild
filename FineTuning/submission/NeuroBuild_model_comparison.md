# NeuroBuild 모델 비교 요약 (기본 vs 파인튜닝)

이 문서는 처음 보는 사람도 이해할 수 있도록 기본 모델과 파인튜닝 모델의 차이, 학습 방법, 평가 지표를 친절하게 설명한다.

## 1) 결론부터 요약
- **파인튜닝 모델이 전반적으로 더 좋다.**
  - 오프라인 테스트(40개)에서 모든 지표가 개선됨
  - API 비교(10개)에서도 파인튜닝 모델이 1건 더 높은 pass
- 이유는 **도메인 데이터(한국어 건축 수정 프롬프트 → JSON 수정 명령)**로 학습되어, “어떤 수정 명령을 선택해야 하는지”를 더 정확히 학습했기 때문이다.

## 2) 두 모델이 하는 일
- **기본 모델(base)**: Qwen/Qwen2.5-7B-Instruct 원본
- **파인튜닝 모델(lora)**: 기본 모델에 LoRA 어댑터를 추가 학습한 모델
- 두 모델 모두 **도면을 직접 생성하지 않고**, 한국어 요청을 **JSON 수정 명령**으로 변환한다.

## 3) 어떤 데이터로 어떻게 학습했나
### 데이터 구성
- 목적: “한국어 프롬프트 → JSON 수정 명령” 변환 학습
- 데이터 크기
  - train: 60
  - valid: 20
  - test: 40

### 데이터 형태
- 기본 필드: `id`, `category`, `prompt_ko`, `gold`
- `gold`는 아래 구조의 JSON
  - `edits`: 수정 명령 목록
  - `notes`: 애매함/미지원 요청 등 보조 메모

예시:
```json
{
  "id": "delta_train_001",
  "category": "window_remove",
  "prompt_ko": "외벽 창문 전부 없애줘.",
  "gold": {
    "edits": [
      {"op": "remove_all_windows"}
    ],
    "notes": ""
  }
}
```

### 학습 방식
- **LoRA(저랭크 어댑터) 미세조정**
- 기본 모델은 유지하고, 작은 어댑터만 학습해 도메인 지식을 주입
- QLoRA는 bitsandbytes 미설치로 사용하지 못해 LoRA로 진행

## 4) 모델 비교 시 사용한 평가지표(자세 설명)
모델 출력(JSON)이 **정답과 얼마나 정확하고 안정적으로 일치하는지**를 평가한다.

1) **JSON parse success**
- 의미: 모델 출력이 “정상적인 JSON”으로 파싱되는 비율
- 이유: 서비스 파이프라인은 JSON 파싱이 불가하면 바로 실패

2) **Schema validity**
- 의미: JSON이 사전 정의된 스키마(키/타입/형식 규칙)를 만족하는 비율
- 이유: 구조가 조금이라도 틀리면 backend 적용이 불가능하거나 오류 발생

3) **Op exact match**
- 의미: `edits` 목록이 정답과 “완전히 동일”한 비율
- 이유: 어떤 수정 명령(op)을 선택하는지가 핵심(예: remove_all_windows vs set_windows_per_wall)

4) **Slot accuracy**
- 의미: `op`와 함께 필요한 `value`까지 맞는 정확도의 평균
- 이유: op가 맞아도 value가 틀리면 실제 동작이 달라짐(예: 창문 개수, 크기 등)

5) **API 비교 pass count(추가 검증)**
- 의미: 실제 API에서 프롬프트별 expected_op 또는 expected_empty_edits 기준 pass/fail
- 이유: 실제 서비스 경로에서 결과 일치 여부를 간단히 확인하기 위한 실사용 지표

## 5) 결과 비교 (핵심 수치)
### 오프라인 테스트(40개)
- base
  - json_parse_success_rate: 1.0
  - schema_valid_rate: 0.85
  - op_exact_match_rate: 0.55
  - slot_accuracy_avg: 0.6375
- lora
  - json_parse_success_rate: 1.0
  - schema_valid_rate: 0.975
  - op_exact_match_rate: 0.95
  - slot_accuracy_avg: 0.95

### API 비교(10개)
- base_pass: 7 / 10
- lora_pass: 8 / 10

## 6) 왜 파인튜닝 모델이 더 좋은가 (쉽게 설명)
- 기본 모델은 일반적인 지식은 많지만, **NeuroBuild 전용 JSON 규칙**을 충분히 알지 못한다.
- 파인튜닝 모델은 “한국어 건축 수정 요청 → JSON 수정 명령”을 직접 학습했다.
- 그래서 **어떤 op를 골라야 하는지**(op exact match)와 **값까지 정확히 맞추는 능력**(slot accuracy)이 크게 좋아졌다.

## 7) 남아 있는 한계
- 모호한 프롬프트는 여전히 오해 가능성 존재
  - 예: “창문 좀 늘려줘” 같은 불명확 요청
- 향후에는 애매한 요청을 비우거나 추가 확인하도록 정책 강화 필요

## 8) 요약 한 줄
- **파인튜닝 모델이 더 정확하고 안정적이며, 실제 서비스 요구(JSON 수정 명령 생성)에 더 적합하다.**
