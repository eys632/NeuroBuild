# Native Qwen3.8 V2 첫 단회 — 품질 FAIL

Run `20260920T075607Z-1c4b930f002d484f962d4f4458b44cdb`, clean pushed
`1571d327d78207017277d96bce7d2c822dc4d41b`. 원본 manifest/dataset/results와 source_snapshot은 exact bytes다.
V2 80×1+warmup5, schema80/parser79/semantic73/rawFP1of40/unsafe1of80/FN3of40/raw관측80이다.
Warmup4/5는 분모에서 제외한다. Mean5.490056752초/p95 6.278982891초다.
Results SHA `db15a165b4448dc1ceb4ba4709f6b016df9e4b83b1e11355756a1528379d1ef9`.

`independent_replay.json`은 고정 source29파일로85개 final JSON을 재생한 PASS 증거이며 품질 PASS가 아니다.
`a02_lexical_audit.json`은 원문 인용으로 한 필드만 바꾼 격리 CPU 대조다. 공식 결과를 고치지 않았다.
별도 reasoning 원문은 보존하지 않았다. 기존125개 모델 평가·CPU 재생은 반복하지 않았다.
`candidate_freeze.json`과 addendum는 사전 동결 원본이고 preflight/postflight는121개 SHA와 동일 epoch를 연결한다.
기존 native 검증은 재사용하며 이 epoch에서 full startup/resource/public suite를 반복하지 않았다.

`final_resource_report.json`:762.113초/1,349표본, GPU3 aggregate 증가18,344MiB/minfree18,030MiB.
이는 process별 peak가 아니다. `stop_request.json`은 own guard pidfd SIGTERM 요청 증거다.
Guard의 own child group TERM/KILL 정리 후 STOPPED/exit0/reaped였고 `post_stop_gpu3.json`의5표본 모두
free36,373MiB/used3,965MiB/util0%다. 다른 사용자 신호나 GPU0/1/2 사용은 없다.

같은 후보를 반복하거나 채택하지 않는다. V2는 이제 MODEL_OUTPUT_SEEN / EXPOSED이며 새 unseen 결과로
재사용할 수 없다. Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED다. 공식 HF tokenizer19/20 FAIL과
raw-Unicode variant를 구분한다. RTX5090/실제 IFC 적용/사람 검수의 증거가 아니다.

[평가 보고서](../../../../docs/reports/phase5x_native_qwen38_v2_minimal_report.md),
[독립 검토](../../../../docs/reviews/phase5x_native_qwen38_v2_minimal_review.md).
