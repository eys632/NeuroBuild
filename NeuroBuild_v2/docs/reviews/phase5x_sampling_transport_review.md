# Phase5.x sampling transport 및 출력 경로 검토

2026-09-20 KST. Source 구현과 실제 모델 품질을 분리한다. SamplingProfile은 legacy_greedy/qwen3_nonthinking_awq 두 고정 enum이며, 기본 legacy는 기존 HTTP body와 byte 동일하다. 모델/GPU/응답으로 자동 선택하지 않는다. Qwen profile은 공식 nonthinking AWQ 권고에서 출발한 명시8값이며 thinkingfalse/schema/no-fallback 계약을 유지한다. Manifest는 실제 client의 sampling_parameters 복사본에서 값을 얻고 동일seed 반복을 독립표본으로 세지 않는다. 지원 범위/parser/gold/semantic scoring logic은 바꾸지 않았다.

Root 독립 client검토 및 runtime 담당 교차 검토 PASS. Architecture 담당의 evaluator manifest/CLI와 guard path 독립 검토도 PASS. Unknown profile의 HTTP 이전 거절, 두 structured dialect, snapshot 변조, 서버 거절시 fallback 없음, 실제 sampling값 기록을 검증했다. Targeted client+harness39PASS, 전체245PASS/skip0/16.377s(realPG/IFC, DISPLAY unset).

Guard의 log는 var/logs, mutable report는 var/reports로 한정한다. 모델/IFC/DB/cache 및 namespace 교차, symlink escape와 기존 hardlink alias는 GPU query/launch 전에 거절한다. 정상 live report 갱신과 log append는 유지한다. 이는 신뢰하는 project/현재UID 운영 경계이며 동일UID 악성 프로세스의 임의 filesystem 경합 격리라는 주장은 아니다. 모델 runtime flag나 할당 예산은 변경하지 않았으며 새 source hash와 freshpreflight로 실제 재기동한다.

개발40×1 진단은 최종3trial gate나 heldout 통과를 대신하지 않는다. RTX의 실제 sampling/runtime 호환성은 계속 PREDICTED_UNVERIFIED다.
