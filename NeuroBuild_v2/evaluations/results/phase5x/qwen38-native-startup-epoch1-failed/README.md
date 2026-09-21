# 첫 native GPU startup 실패 기록

CPU grammar/raw-tokenizer/context와 VRAM 계획을 검증한 뒤2026-09-20 실행했다.
전체 파일 hash 후 fresh GPU3 5회 모두 free36,373MiB/util0/swing0이었다.
예상 peak28,672MiB와 margin7,275MiB가 들어와 guard가 실행을 허용했다.
Physical3/internalCUDA0의 UUID/count 검증 후 child3527525가 약7.781초에SIGABRT(-6)로 종료했다.
Own group 정리/reaped는 완료했으며 종료 후 free36,373MiB/used3,965MiB/util0으로 복귀했다.
관측 aggregate 증가 최대18,290MiB/최소 free18,084MiB였으며 process별 peak나 연속 측정은 아니다.
이 수치만으로 OOM 여부 또는 원인을 단정하지 않는다. 원인 진단이 필요하다.

HTTP/model evaluation 요청은0회다. Native startup 자체의 internal warmup/kernel 실행 범위는
미확인이므로 GPU 연산0이라고 주장하지 않는다. stdout/stderr는DEVNULL, log파일은0bytes다.
이 기록에는 health/listener/공개 inference PASS가 없다. 재시도는 별도 config/report로 보존한다.
타인 process/VRAM을 변경하거나 GPU0/1/2로 fallback하지 않았다.
