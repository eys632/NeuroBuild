# Native 노출 진단의 준비 정의

Freeze helper는 실제 startup/public/resource·386회귀·원문 tokenizer 차이·source 및 기존 gate를
검증한 뒤 실행 조건을 새 파일로 고정했다. 현재 채택·품질 PASS를 뜻하지 않는다. Replay helper는
독립 checkpoint/freeze/snapshot SHA를 받아 보존된 final JSON을 원래 parser/scorer로 재생한다.
미보존 응답의 raw decision을 새로 관측했다고 주장하지 않고 unknown과 실패 분모를 유지한다.

Helper 원래 위치는 var/research/freeze_native_qwen38_diagnostic.py와 var/review-tools의 동명파일이다.
추적본에서 직접 실행하기보다 같은 checkout의 원래 위치에 정확한 바이트로 복원한다. Model call이나
별도 GPU 실행을 자동 시작하는 묶음이 아니다. 향후 실제 source snapshot/result/replay는 별도 보존한다.
