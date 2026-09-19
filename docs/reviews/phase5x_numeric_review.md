# Phase5.x 독립 수치 경계 및 listener 검사 검토

검토일: 2026-09-20 KST. **판정: 명시한 lexical 계약과 검사 도구 범위 PASS,
남은 중대 blocker 없음.** 이 문서는 CPU-only 소스 검토와 악성 model-output
probe 기록이다. 실제 모델 정확도, heldout 통과 또는 전체 Phase5.x 완료를
뜻하지 않는다. 합성 예시는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다.

## 수치·축 경계

[requirements.py](../../src/neurobuild/application/requirements.py)의 변경과
[계약 테스트](../../tests/test_requirements.py)를 독립 검토했다. 같은 원문
evidence occurrence에서 quantity와 axis의 전체 토큰을 함께 확인하는 변경은
타당하다. `1⁄2m`, `1×2m`, Unicode `−1m`의 suffix를 임의로 선택하는 기존
우회가 `UNGROUNDED_REQUIREMENT`로 차단됨을 직접 재현했다.

추가 probe에서 아래 누락을 발견해 코드 소유자에게 수정 요청했다.

| 원문 표현 | 잘린 evidence / 출력 | 수정 전 결과 |
|---|---|---|
| `1 250mm` (U+00A0), `1 250mm` (U+2009), `1 250mm` (U+202F) | `250mm X축 양의 방향` / 250mm | READY 0.250m |
| `1` + U+2028 + `250mm` | 위와 동일 | READY 0.250m |
| `1·2m`, `1:2m` | `2m X축 양의 방향` / 2m | READY 2m |
| `X축- 방향으로 +1m`, `X축 - 방향으로 +1m`, `X- 방향으로 +1m` | 전체 표현 / +1m | READY +1m |
| `X축+ 방향으로 -1m` | 전체 표현 / -1m | READY -1m |
| `X축 +1m%`, `X축 +1m％`, `X축 +1m‰`, `X축 +1m‱` | `X축 +1m` / +1m | READY +1m |

Root 검토자는 combining overlay U+0338 및 accent U+0301로 `1`과 `2m`를
연결한 입력에서 같은 suffix 누락도 찾아 코드 소유자에게 전달했다.

Unicode whitespace를 수치 경계 scan에서 ASCII whitespace와 다르게 취급하거나,
축 뒤 ASCII 부호를 실제 후속 quantity의 시작인지 확인하지 않고 허용한 경우다.
지원하지 않는 표기를 정규화해 추측하는 대신 거절하는 것이 현재 계약에 맞다.
최종본은 Unicode numeric/whitespace와 punctuation/symbol/mark/control의 인접
구간을 검사하고, 괄호·인용 부호와 명시한 문장 구분자만 harmless delimiter로
허용한다. `%` 계열과 combining mark는 delimiter가 아니다. ASCII 축 뒤 부호는
실제로 검증하는 quantity의 시작에 해당할 때만 허용한다. 지원하지 않는 표기를
ASCII로 정규화하거나 산술 계산하지 않는다.

수정 후 기존 13개 + 비율 modifier 4개 + combining mark 2개, 합계 **19개 독립
거절 probe가 모두 `UNGROUNDED_REQUIREMENT`로 실패**했다. 정상 `X축 +1m`,
`-X축으로 1m`, `(-X축)으로 12mm`, `'X축' +12mm`의 **4개 control은 통과**했다.
`PYTHONPATH=src .conda/bin/python -B -m unittest tests.test_requirements -v`:
**33 tests PASS, skip0, 0.067s**. 기존 seed20 표현 가능성과 정상 whitespace,
원문 단위·부호·정확한 Decimal 변환도 유지됐다. `git diff --check`가 통과했다.

독립 검토한 최종 parser SHA-256:
`a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a`.
새 hardening reference120개의 별도 재검증과 freeze는 해당 담당자의 기록을 따른다.
이 문서의 단위 테스트나 참조 표현 가능성은 model inference 성공과 별개다.

이 guard는 자연어 전체의 의미를 증명하지 않는다. 예를 들어 `음의 X축으로
+1m`에서 모델이 evidence를 `X축으로 +1m`만 선택하면 앞의 방향 단어 누락을
원문 토큰 경계만으로 판별하지 못한다. 조건·부정·현재 지시·대상 수식어와 함께
이러한 의미 누락은 모델 평가와 후속 사람의 proposal 검토 책임이다. 이번
회귀를 모든 Unicode 표현이나 방향 의미의 완전 검증으로 표시하면 안 된다.

## 자체 PID listener checker

[verify_model_listeners.py](../../scripts/verify_model_listeners.py)는 현재 UID의
명시적인 PID 한 개만 대상으로 한다. Proc directory FD를 먼저 고정하고 UID를
검사한 뒤 상대 경로를 읽어 PID 재사용이 다른 프로세스로 읽기를 돌리지 않게 한다.
시작/종료 starttime과 자체 socket inode 집합을 대조한다. Namespace network table은
자체 FD inode만 join하여 TCP listener 주소를 해석·출력하며 다른 PID를 순회하지 않는다.
UNIX/UDP/netlink/raw socket은 별도 분류하고 unknown·권한 오류·종료·race는 실패한다.

보고서는 `var/reports/` 아래 새로운 파일에만 atomic no-clobber 방식으로 게시한다.
이미 존재하거나 경쟁 생성된 파일을 덮어쓰지 않는다. 한 PID에서 TCP listener가
하나 이상 관측되고 모두 loopback일 때만 PASS다. 이는 한 시점의 TCP 관측이며
descendant, UDP 노출, firewall 또는 이후 listener의 안전성을 보장하지 않는다.

`PYTHONPATH=src .conda/bin/python -B -m unittest tests.test_model_listeners -v`:
**15 tests PASS, skip0, 0.272s**. 자체 CPU child의 실제 IPv4/IPv6 loopback·wildcard,
UNIX/UDP 혼합과 synthetic identity/FD race·권한·미분류·경로 제한·기존 파일 보존을
검증했다. Child는 stdin EOF로 정상 종료했으며 GPU 실행/조회나 signal은 사용하지 않았다.
Root의 실제 모델 PID 검사와 별개인 checker 자체 검증이다.
Architecture 담당자의 최종 read-only 독립 소스 검토에서도 추가 중대 blocker는
발견되지 않았다.

본 검토자는 모델 요청, GPU 조회, 환경 설치, 타인 프로세스 접근 또는 변경을
수행하지 않았다. A100과 RTX5090는 공통 parser를 사용하며, 이 CPU 검증은 RTX
runtime이나 현장 inference 성공의 증거가 아니다.
