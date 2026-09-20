# 같은 batch1 설정의 제한된 startup 진단

첫 실패와 동일 binary/model/argv/environment/VRAM예산을 유지하고 새 출력 경로 및120초 한도만
구분했다. 공통 lifecycle guard를 재사용하며 stdout은DEVNULL, stderr는 메모리에서 한 행4KiB/
전체256KiB/최대16events만 분석하고 원문을 폐기했다. 실행 전CPU/fake11개 및 독립 검토PASS다.

실제 child는 다시SIGABRT(-6)로 종료했다. stderr347bytes/4lines에서
GGML_ASSERT_FAILED, llama-context.cpp:1734를 확인했다. 원문·assert 표현·backtrace는 저장하지
않았으며 위치fingerprint는정적source위치의SHA다. Overflow0/EOFtrue/readerclosed/diagnosticcomplete,
자체 child 정리/reaped를 확인했다. GPU3만사용했고HTTP요청0이다.

고정 source의 시작 seq_rm 검사는2token을decode하고 line1734는 n_tokens_all<=n_batch를 요구한다.
Logicalbatch1 충돌이 확인됐으므로 후속profile은 batch2/ubatch1을 별도로 검증한다. 이 실패
기록이나 source_snapshot을 후속설정으로 덮어쓰지 않는다. 모델품질 또는 readiness PASS가 아니다.
`source_snapshot`은 f114a9b checkpoint의 당시 launcher/guard/bootstrap/preflight 원문이다.
이 진단helper는현재production을import하므로과거실험재현은당시source와함께해야한다.
