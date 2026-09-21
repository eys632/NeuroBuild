# Gemma4 첫 단회 진단 보관본

Run `20260920T091646Z-15102b775ddf46298a6265400d35c4e0`, clean eb60307,
exposed120×1+warmup5. **품질 FAIL**, 독립 저장 응답125개 재생·집계 PASS.

Schema/parser120, semantic115, rawFP1/58, unsafe2/120, FN1/62, raw관측120이다.
Warmup5/5는 분모에서 제외했다. 최종 GPU3 aggregate peak18,864MiB/minfree17,510MiB,
자체 server STOPPED/exit0/reaped 뒤5회 free36,373MiB/used3,965MiB/util0%를 확인했다.
실제 IFC 실행, 동일 후보 재평가, V2/미사용 holdout 호출은 없다.

`manifest.json`, `dataset.json`, `results.json`과 freeze/replay는 원본 bytes다.
`source_snapshot/`은 eb60307의29개 Git blob 및 고정 record다.
`preflight/`, `postflight/`, 종료 receipt·최종 guard·메모리 반환 증거를 함께 보관한다.
Python pidfd wrapper 부재로 신호 전에 중단된 첫 종료 시도도 보존한다.
이후 검증된 own guard에만 pidfd SIGTERM을 전달했고 guard의 자체 group TERM/KILL 정리를 기록했다.

`integrity.json`의 원래 경로와 hash를 따라 재현할 수 있다. 실제 모델 재호출은 이 보관본 검증의 일부가 아니다.
재생 도구의 CLI에는 `--completed-run` 및 freeze/source snapshot/commit의 독립 pin이 필요하다.
Startup/resource 선행 증거는 인접한 `gemma4-native-*-epoch1`과 `gemma4-cpu-preflight` 보관본을 참조한다.
Model weight·환경·native binary·reasoning 본문은 포함하지 않는다.
Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED이며 미래 평가의 unseen 자료가 아니다.
