# Final 실패 사례 분석 (qwen25_7b_lora_final)

## 요약
- base -> fine-tuned 개선: 16건
- base -> fine-tuned 역전: 0건
- 둘 다 실패: 2건

## base는 틀렸지만 fine-tuned는 맞힌 사례

### 사례 1
- id: delta_006
- 카테고리: window_size
- 프롬프트: 환기창만 넣어줘.
- gold:
```json
{"edits":[{"op":"set_windows_size_preset","value":"small"}],"notes":""}
```
- base 출력:
```json
{"edits":[{"op":"set_windows_per_wall","value":1}],"notes":""}
```
- fine-tuned 출력:
```json
{"edits":[{"op":"set_windows_size_preset","value":"small"}],"notes":""}
```
- 오류 유형: op 선택 오류(창문 크기 vs 개수 혼동)

### 사례 2
- id: delta_008
- 카테고리: avoid_bathroom
- 프롬프트: 욕실 쪽 외벽 창문은 빼줘.
- gold:
```json
{"edits":[{"op":"set_avoid_bathroom_zone","value":true}],"notes":""}
```
- base 출력:
```json
{"edits":[{"op":"remove_all_windows","value":null}],"notes":""}
```
- fine-tuned 출력:
```json
{"edits":[{"op":"set_avoid_bathroom_zone","value":true}],"notes":""}
```
- 오류 유형: op 선택 오류 + schema 형식 오류(value null)

### 사례 3
- id: delta_011
- 카테고리: exterior_door
- 프롬프트: 외벽 출입문은 빼줘.
- gold:
```json
{"edits":[{"op":"set_exterior_door","value":false}],"notes":""}
```
- base 출력:
```json
{"edits":[{"op":"remove_all_windows"}],"notes":"외벽 출입문 제거 요청은 지원되지 않는 옵션입니다. window 관련 옵션만 제공됩니다."}
```
- fine-tuned 출력:
```json
{"edits":[{"op":"set_exterior_door","value":false}],"notes":""}
```
- 오류 유형: op 선택 오류(출입문 제거를 창문 제거로 오해)

## base는 맞았지만 fine-tuned는 틀린 사례
- 없음

## 둘 다 틀린 사례

### 사례 1
- id: delta_025
- 카테고리: unsupported
- 프롬프트: 동쪽 벽에만 창문을 넣어줘.
- gold:
```json
{"edits":[],"notes":"지원하지 않는 요청: 특정 방향 벽 지정"}
```
- base 출력:
```json
{"edits":[{"op":"set_windows_per_wall","value":1,"wall":"east"}],"notes":""}
```
- fine-tuned 출력:
```json
{"edits":[{"op":"set_windows_per_wall","value":1,"wall_dir":"east"}],"notes":""}
```
- 오류 유형: 지원 불가 요청 처리 오류 + schema 형식 오류(허용되지 않는 필드)

### 사례 2
- id: delta_026
- 카테고리: ambiguous
- 프롬프트: 창문 좀 늘려줘.
- gold:
```json
{"edits":[],"notes":"애매함: 창문 개수 불명확"}
```
- base 출력:
```json
{"edits":[{"op":"set_windows_per_wall","value":5}],"notes":""}
```
- fine-tuned 출력:
```json
{"edits":[{"op":"set_windows_per_wall","value":4}],"notes":""}
```
- 오류 유형: 지원 불가/애매한 요청 처리 오류

## 오류 유형 분포(요약)
- base
  - schema 형식 오류: 6
  - op/slot 선택 오류: 6
  - 복합 명령 처리 오류: 4
  - 지원 불가 요청 처리 오류: 2
- fine-tuned
  - schema 형식 오류: 1
  - 지원 불가 요청 처리 오류: 1

## 개선 방향
- 지원 불가/애매한 요청에 대해 edits를 빈 배열로 유지하도록 더 강한 제약 추가
- avoid_bathroom / exterior_door 같은 boolean 계열 의도는 오탐을 줄이도록 규칙 강화
- schema 위반(허용되지 않는 필드) 생성 방지를 위한 지시문 강화
