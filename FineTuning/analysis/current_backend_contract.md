# Current Backend Delta Contract (Local NeuroBuild)

본 문서는 로컬 NeuroBuild 코드 기준의 delta edit contract를 정리한 문서다.
이 문서를 기준으로 dataset/schema/eval을 설계한다.

## Source of truth (local)
- /home/eys632/26-2project/backend/llm_qwen.py
- /home/eys632/26-2project/backend/app.py
- /home/eys632/26-2project/backend/edit_ops.py

## Delta edit contract 요약
- 출력은 JSON 객체 1개만 사용한다.
- top-level 필수 키: edits (array)
- top-level 선택 키: notes (string)
- backend는 notes를 사용하지 않는다(로그용).

## edits item 형식
- 필수 키: op (string)
- 선택 키: value (op에 따라 필수/선택)
- edit_ops.py는 op 대신 type 키도 허용한다(하지만 dataset은 op만 사용).

## 지원 op 목록 및 필드
- set_windows_per_wall
  - value: int (0..10) 필수
- remove_all_windows
  - value 없음
- set_windows_size_preset
  - value: small|medium|large 필수
- set_avoid_bathroom_zone
  - value: bool 필수
- set_exterior_door
  - value: bool 필수 (backend는 value 누락 시 true로 처리)
- add_exterior_door
  - value: bool 선택 (누락 시 true)
- set_bathroom_count
  - value: int (0..10) 필수
- add_bathroom
  - value: int (1..10) 선택 (누락 시 1)
- increment_bathroom_count
  - value: int (1..10) 선택 (누락 시 1)

## llm_qwen.py vs edit_ops.py vs app.py mismatch
1) increment_bathroom_count
- edit_ops.py는 지원하지만 llm_qwen.py의 delta prompt에는 없다.

2) op vs type
- edit_ops.py는 op 또는 type 키를 모두 허용한다.
- llm_qwen.py는 op만 안내한다.

3) value 필수 여부
- add_exterior_door/add_bathroom은 backend에서 value를 생략해도 동작한다.
- llm_qwen.py의 안내는 value를 필수로 설명한다.

4) 실행 경로
- app.py는 base_file_id가 있을 때만 llm_data.edits를 apply_ops에 전달한다.
- 그 이후에도 parse_prompt_delta(rule-based)가 항상 적용되어 LLM 결과 없이도 일부 변경이 일어날 수 있다.

## Gold dataset 기준
- 실제 실행 경로에 맞춘 JSON만 사용: {"edits": [...], "notes": ""}
- 학습용 canonical 표현은 op 키만 사용(type 사용 안 함)
- 지원 op는 edit_ops.py 목록 기준
- 지원 불가/애매한 요청은 edits를 빈 배열로 두고 notes에 짧은 이유를 기록
- 평가 스키마는 backend 호환을 위해 op 또는 type 둘 다 허용

## Baseline evaluation (Phase 1) metrics
- JSON parse success
- Schema validity (configs/delta_ops_schema.json)
- Ops exact match (gold vs pred)
- Slot/value accuracy (op+value 기준의 multiset overlap)

## Phase 3 평가 메트릭 정의(요약)
- op_exact_match: edits 항목을 op/value 기준으로 정규화한 뒤, 정렬된 리스트의 완전 일치 여부
- slot_accuracy: 정규화된 (op,value) 항목의 multiset overlap 비율(분모는 gold edits 개수)
