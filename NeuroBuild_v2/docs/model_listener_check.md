# 자체 모델 PID의 TCP listener 점검

`scripts/verify_model_listeners.py`는 현재 UID가 소유한 **명시적인 PID 하나**의
TCP listener를 확인한다. 모델 시작/종료, GPU 조회, process 목록 순회는 하지 않는다.
Linux procfs와 표준 Python만 필요하며 Backend `.conda`에서 실행한다.

```sh
.conda/bin/python scripts/verify_model_listeners.py \
  --pid <own-model-pid> \
  --report-file var/reports/model-listeners.json
```

PID는 guard JSON의 `child_pid`처럼 자신이 시작한 모델의 실제 PID를 사용한다.
Report 경로는 선택 사항이며 checkout `var/reports/` 아래의 **새 파일만** 허용한다.
임시 파일을 완성한 뒤 atomic no-clobber 방식으로 게시하며, 기존 파일은 덮어쓰지 않는다.
반복 검사에는 시각/실행 ID를 넣은 새로운 파일명을 사용한다. 다른 working directory에서도
상대 report 경로는 checkout 기준이다. Stdout JSON의 `verdict=PASS`/exit0은 TCP listener가
하나 이상 관측됐고 모두 loopback이라는 뜻이다. Wildcard `0.0.0.0`/`::`와 외부·사설
주소 bind는 `NON_LOOPBACK_LISTENER`/exit2다. TCP listener가 없거나 검증이 불완전해도
exit2이며, 서비스가 꺼져 있는 것을 정상 노출 검사로 통과시키지 않는다.

처음 `/proc/<pid>` directory FD를 열어 UID를 확인한 뒤 모든 내용을 그 FD에 대한
상대 경로로 읽는다. UID가 다르면 proc 내용/FD/network table을 읽지 않는다.
Directory FD 고정과 시작/종료 starttime 검사는 PID 재사용을 다른 프로세스로 따라가지
않도록 한다. Socket FD의 inode 집합도 전후 비교한다. 권한 오류, process 종료,
identity/inode 변화, 해석할 수 없는 socket/table은 원문 오류를 출력하지 않고 실패한다.

`/proc/<pid>/net/tcp*`도 해당 network namespace의 전체 테이블이다. 따라서 먼저
검증한 PID의 FD에서 얻은 inode만 테이블에 대조하고, 매칭된 TCP listener의 주소/port만
해석·반환한다. 다른 PID를 탐색하거나 타 socket의 주소/행을 출력·보존하지 않는다.
TCP 이외의 UNIX/UDP/UDP6/netlink/raw/raw6 socket은 같은 방식으로 **자체 inode만**
분류하여 TCP 누락과 구분한다. 끝까지 분류되지 않은 inode는 무시하지 않는다.
[Linux TCP procfs 형식](https://docs.kernel.org/networking/proc_net_tcp.html)

Report에는 PID/current UID/start ticks, 검사 UTC, 자체 socket inode 수, TCP 이외
socket 수, TCP listener 목록, `snapshot_complete`, `all_loopback`, `reason_codes`가 있다.
IPv4 loopback127/8, IPv6::1 및 IPv4-mapped loopback을 지원한다. 이 결과는 **한 PID의
한 시점 TCP listener 관측**이다. Descendant의 socket, UDP 노출, firewall, 이후 새로
만들어진 listener, 두 관측 사이 잠깐 나타났다 사라진 socket은 보장하지 않는다.
장기 실행에서는 시작 후와 평가 중 필요한 시점에 다시 검사한다.

`tests/test_model_listeners.py`는 자신의 짧은 CPU child가 생성한 IPv4/IPv6
loopback/wildcard ephemeral listener와 UNIX/UDP socket을 사용한다. Child는 stdin EOF로
정상 종료시키며 signal/kill/GPU를 사용하지 않는다. Synthetic proc reader로 foreign UID의
내용 읽기 차단, 권한/종료/identity/inode race, unknown socket, 무관한 namespace 행 배제,
report 경로 제한과 기존 파일/동시 생성 파일 보존도 검증한다.
