# Gemma4-12B 단회 결과 독립 검토

**저장 응답 재검산 PASS, 모델 품질 gate FAIL**이다.
Clean/pushed302edf1d4d7927ab502cec1971f41d64f4c9cc54의30개 Git blob snapshot,
사전 동결된67파일과 replayb96c007643e553bb99ad27d711dea62344976892dbd487419b400a280427ff49를 사용했다.
Snapshot record70796723f66fb967c1cf9d687ad22910faf852b91e19b134c42805081824c62e,
freeze3d8ef116b569d660926c42b8f84834bed61c1fa5494122ae9181b0ec818d959c다.

새 run20260920T155657Z-430e9203623a477eb655af9521bec051의 final JSON125행을 한 번만 CPU 재생했다.
Exit0/0.365초/stderr0이며 schema120/parser118/semantic112/rawFP3/58/unsafe1/120/FN0/62/raw관측120,
warmup5/5 및 저장 전체 집계가 일치했다. 원본·snapshot·동결 hash는 전후 동일하다.
Proof SHAa080e21f9c771ad4c7c768323cf496cdd6a99ab38571e8ddee0fe85a2ac7e99b.

이 검사는 저장 응답의 처리 일치이며 모델 반복 출력이나 unseen 품질의 증거는 아니다.
기존125개 진단·85개 평가 또는 다른 완료 후보를 재생하지 않았다. 모델·HTTP·GPU·weight 읽기0회다.
단회3개 gate 미달이 명확하여 같은 후보 추가 반복·V2·미사용80 접근 없이 종료했다.
Gold는AUTO-GENERATED / NOT HUMAN VERIFIED이며 오류·분모·threshold를 변경하지 않았다.
현재 생산 코드의418회귀 PASS를 재사용했고, 시스템 환경과 다른 사용자 프로세스는 변경하지 않았다.

[원본·재검산·종료 보관본](../../evaluations/results/phase5x/exposed-native-gemma12-diagnostic/README.md).
