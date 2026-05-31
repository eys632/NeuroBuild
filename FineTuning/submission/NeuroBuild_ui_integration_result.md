# NeuroBuild UI Integration Result (Phase 5)

## 1. Phase 5 목표
- 복사본 UI에서 base/lora 전환 동작을 검증하고 API 결과를 비교

## 2. 원본 프로젝트를 수정하지 않고 복사본에서 실험한 이유
- 원본 안정성 보존 및 회귀 방지

## 3. 복사본 경로
- /home/eys632/26-2proj-FineTuning/ui_integration_workspace/NeuroBuild_ui_test_copy

## 4. 수정한 복사본 파일 목록
- backend/llm_qwen.py
- backend/app.py
- run_base_8101.sh
- run_lora_8102.sh
- requirements-lora.txt

## 5. base/lora 실행 방식
- base: 8101 포트, GPU 0
- lora: 8102 포트, GPU 1
- 실행 명령
  - nohup bash run_base_8101.sh > submission/ui_eval_results/server_logs/base_8101.log 2>&1 &
  - nohup bash run_lora_8102.sh > submission/ui_eval_results/server_logs/lora_8102.log 2>&1 &
- 실행 환경
  - Python 3.10 가상환경: /home/eys632/26-2proj-FineTuning/.venv_ui
  - 토큰화 빌드 이슈로 Python 3.13 대신 Python 3.10 사용

## 6. /api/llm/status 확인 결과
- base (8101)
  - mode: base
  - model_id: /home/eys632/26-2project/models/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28
  - adapter_path: null
  - loaded: false
- lora (8102)
  - mode: lora
  - model_id: /home/eys632/26-2project/models/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28
  - adapter_path: /home/eys632/26-2proj-FineTuning/checkpoints/qwen25_7b_lora_final/adapter
  - loaded: false

## 7. API 비교 실행 명령어
- /api/generate 기반 비교
- 명령:
  - /home/eys632/26-2proj-FineTuning/.venv_ui/bin/python submission/run_ui_api_compare.py \
    --base-url http://127.0.0.1:8101 \
    --lora-url http://127.0.0.1:8102 \
    --dataset submission/ui_test_cases.jsonl \
    --output-dir submission/ui_eval_results

## 8. API 비교 결과 요약
- total: 10
- base_pass: 7
- lora_pass: 8
- 서버 오류: 없음 (base/lora 모두 200)
- IFC 생성 응답: file_id/file_url 모두 10건 확인

## 9. base보다 lora가 더 나은 사례
- ui_009: "동쪽 벽에만 창문을 넣어줘."
  - base: set_windows_per_wall + set_avoid_bathroom_zone (fail)
  - lora: 빈 edits (pass)

## 10. lora도 실패한 사례
- ui_001: "환기창만 넣어줘."
  - base/lora 모두 set_avoid_bathroom_zone로 오해
- ui_010: "창문 좀 늘려줘."
  - lora: set_windows_per_wall=2 (fail)
  - base: no_edits (pass 아님)

## 11. 브라우저 UI 수동 검증 수행 여부
- 수동 UI 검증 미수행
- 접속 주소:
  - base UI: http://127.0.0.1:8101
  - lora UI: http://127.0.0.1:8102
- 체크리스트는 NeuroBuild_ui_manual_test_checklist.md 참고

## 12. 원본 프로젝트 무수정 확인 결과
- Git status: clean (no local changes)
- 증빙: ui_integration_workspace/original_audit/
- 확인 문구는 original_untouched_check.md에 기록

## 13. 남은 문제
- Python 3.13 환경에서 tokenizers 빌드 실패 (PyO3 지원 버전 이슈)
- 일부 모호 프롬프트(ui_010)에서 lora 오버해석 발생
- 환기창/크기 관련 의도(ui_001) 개선 필요

## 14. 다음 개선 방향
- 모호한 요청에 대해 빈 edits/clarify 정책 강화
- 환기창/크기 프롬프트 학습 데이터 보강
- UI 수동 검증 수행 및 스크린샷 기반 기록 추가
