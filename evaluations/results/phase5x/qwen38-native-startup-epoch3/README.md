# Native logical batch2 startup 관측

고정 GGUF/runtime의 GPU3 epoch3 startup HTTP 및 own process/listener 검증 PASS다.
Logicalbatch2/physicalubatch1/ctx4096/seq1, fresh free/utilization과28GiB peak+margin guard를 적용했다.
이 폴더는 public inference 이전의 실제3GET 기록이다. Guard 자체 ready:false는 HTTP를 검사하지
않는 guard의 필드이며 별도 startup.json이 readiness 증거다. 모델 품질 PASS 또는 채택은 아니다.

Runtime은 qwen38-gguf-raw-unicode-v1이고 공식 HF19/20 FAIL과 raw reference20/20,
별도 native context200 PASS를 함께 hash로 고정한다. 입력/출력 NFC 보정은 없다.
Metadata의 startup_report_sha256이 이 차이를 포함한 실제 startup proof와 연결된다.
CPU proof나 compile proof의 과거 no-execution 상태는 이 새 관측으로 소급 변경하지 않는다.
