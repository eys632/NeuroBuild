# Epoch5 — 사용자 checkpoint에 따른 자체 종료

정식 반복 평가를 준비하던 native GPU3 서버의 실제 기동/공개 응답/종료 증거다.
품질 evaluation 호출0, maximum-context resource probe0. 첫 startup 확인은 child경과5.666초
직후 HTTP_STATUS_FAILED였고 HTTP상태번호/본문은 보존하지 않았다. 별도 후속 startup3GET은PASS,
공개 production 요청1회는PASS다. 이를 실패 없는 첫 시도라고 표시하지 않는다.

사용자 지시 후 own UID/executable/전체 argv/child-parent/startticks를 확인하고 guard3554992에
pidfd SIGTERM을 보냈다. Child3555443 exit0/STOPPED/reaped를 확인했다. Guard는 자체 process group
정리로 TERM/KILL을 기록했다. 다른 사용자 PID 조회/신호와 killall/광범위pkill은 사용하지 않았다.
종료 뒤 GPU3 5회 모두free36373MiB/used3965MiB/util0%. 다른GPU는 조회/변경하지 않았다.
Epoch5 aggregate 증가최대18342MiB/minfree18032MiB는 기동·공개 응답 관측이며 정식 품질 점수가 아니다.

14400초 formal launch 설정은 실행 기록으로만 보존한다. 사용자 지시가 기존 자동120×3 계획을 대체했다.
이 서버를 재기동하거나 완료한 runtime/resource 검사를 반복하라는 지침이 아니다.
