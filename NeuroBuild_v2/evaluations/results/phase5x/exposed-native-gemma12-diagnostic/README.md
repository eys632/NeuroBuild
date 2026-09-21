# Gemma4-12B first single diagnostic — quality FAIL

Run20260920T155657Z-430e9203623a477eb655af9521bec051, clean pushed302edf1d4d7927ab502cec1971f41d64f4c9cc54.
Exactly120 trials + five separate warmups. Schema120/parser118/semantic112;
raw READY FP3/58, accepted FP1/58, unsafe1/120, FN0/62, raw observed120.
Mean2.577928829s/p952.946839637s. UNGROUNDED_REQUIREMENT1 + INVALID_MODEL_OUTPUT1;
warmups5/5, no timeout or truncation. No IFC action occurred.

Independent replay of only these new125 saved final JSONs ran once and matched the original rulings/metrics.
Accounting PASS does not change the quality FAIL. No repeat, V2 or unused80 access followed.
Original historical125/replay/startup/resource suites were not rerun. Production still matches the saved418-test PASS.

Only exact owned guard3697642 was signaled via pidfd SIGTERM. Child3697702 exited0 and was reaped.
Guard STOPPED after862.954s/1553samples: aggregate peak7724MiB/minfree28650MiB.
Post-stop five GPU3-only observations returned to free36373/used3965/util0. No foreign-process changes or other GPU fallback.

The earlier67-file freeze and runtime/CPU evidence remain in their existing archives.
This archive preserves exact result/manifest/dataset bytes, source snapshot30 Git blobs,
CLI/replay/analysis/owned shutdown/post-stop/regression-carry evidence.
Source snapshot preserves original bytes, including any original whitespace.
Evidence created before execution retains its historical NOT_RUN wording.
