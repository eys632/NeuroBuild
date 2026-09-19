# Phase1 — Domain Contract

2026-09-20. Acceptance/tests/review 통과. 이 보고서를 포함한 commit/push의 실제 결과는 Git 및 EXECUTION_LOG/STATUS에서 확인한다.

- 목표: GPU/DB/IFC library 없이 공통 Domain의 안전한 계약을 구현한다.
- 구현: frozen requirement/target/project/revision/artifact/proposal/approval/execution, 명시 상태, 정확한 Decimal m/cm/mm→metre, project-world XY MOVE_FURNITURE, 원문 target 보존, fingerprint와 승인 결합 guard.
- 거절: nonfinite/bool/묵시 숫자 변환, zero move, 다른 operation/frame/type, 잘못된 artifact path/metadata/lineage, target 미확인, 별도 approval 없음, project/base/target/content 불일치, stale/duplicate Apply.
- 테스트: 독립 agent 작성 unittest29개 및 다수 subTest 통과. root가 editable package 설치 후 scripts/test_backend.sh 재실행하여 동일29개 통과. pip check 정상. Runtime Info A100 JSON 회귀 실행 성공. git diff --check 정상.
- 환경: 공식 hash 검증 Miniconda26.7.1 + Backend3.12.14, pip26.2.1, setuptools84.0.0. Production Domain은 stdlib만 사용. 사용자 HOME 내 설치, base는 관리용, GPU환경/weight 없음. Conda explicit SHA256 lock와 재생성 명령 보존.
- Architecture review: Domain은 DB/IFC/GPU/network를 import하지 않는다. guard는 DB lock/CAS를 대신하지 않으며 실제 inventory membership은 다음 adapter 책임이다. actor 인증이나 durable approval을 구현했다고 주장하지 않는다.
- Safety review: source/target 내용을 오류에 넣지 않고 immutable metadata와 명시 승인 binding을 유지한다. 환경/weight/cache/artifact가 Git 제외됨을 확인한다.
- Cross-server: 공통 Python3.12 코드/Backend lock. RTX5090 실행은 아직 UNVERIFIED이며 GPU build를 Backend에 넣지 않았다.
- 문제/수정: metadata patch의 중복 경로 오류는 적용 전 거절되어 나누어 적용했다. 기능 테스트 실패는 없었다. 기존 인증 blocker는 SSH push 확인으로 해소됐다.
- 다음 판단: Phase1 checkpoint push 성공 후 Phase2 PostgreSQL + Artifact Persistence로 진행. 별도 사용자 승인 대기 없음.
