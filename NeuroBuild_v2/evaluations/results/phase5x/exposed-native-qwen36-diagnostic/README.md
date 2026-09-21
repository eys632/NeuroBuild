# Qwen3.6 first single diagnostic — semantic quality FAIL

Run20260920T170742Z-38d6ce30e9cc4e939a93ccb8fbae3ef8, clean pushed23b8d018c184c96e72165d212b8e840e3a75206f.
Exactly120 trials plus five separate warmups. Schema120/parser119/semantic106;
raw READY FP0/58, accepted FP0/58, unsafe0/120, FN11/62, raw observed120.
Mean2.765226808s/p953.142153062s. UNGROUNDED_REQUIREMENT1, warmups4/5,
no timeout/truncation. No IFC action. Semantic gate114/120 failed.

Independent replay of only these NEW125 final JSONs ran once and matched the stored rulings and metrics.
Accounting PASS does not change quality FAIL. Same-candidate repeat/V2/unused80 access all0.
Historical completed125/replay/startup/resource/corpus suites were not rerun.
Current production/tests still match saved422-test PASS; unchanged suite was not repeated.

Only pinned own guard3716484 received the external pidfd SIGTERM request. Child3716721 exited0 and was reaped.
Guard's own group cleanup records term_sent=true and kill_sent=true; original flags are preserved.
Epoch1212.637s/2205samples: GPU3 aggregate baseline-relative increase peak19854MiB/minfree16520MiB.
Post-stop five GPU3 observations returned to free36373/used3965/util0, both own PIDs absent.
No foreign process changes or other GPU fallback; aggregate peak is not a per-process measurement.

This archive preserves exact result/manifest/dataset,30 Git source blobs and snapshot record,
CLI/replay/analysis/owned shutdown/post-stop/regression carry evidence.
Earlier69-file freeze and CPU/runtime evidence remain in their prior archives.
Preparation wording and original source whitespace are preserved as historical bytes.
Conditional next-candidate memo was written before quality outcome and only recommends metadata/source investigation.
Gold is AUTO-GENERATED / NOT HUMAN VERIFIED; Phase5.x incomplete, no model adopted, Phase6 not started.
