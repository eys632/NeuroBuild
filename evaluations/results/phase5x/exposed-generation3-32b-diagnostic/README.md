**32B generation3 exposed diagnostic — 원본 보존 및 독립 재계산**

Run `20260920T030227Z-e8d3568e4a1243d69e674ea3d6fc9727`, clean checkpoint
`c6bdbeb400c37016897bfe6b08ab080cc33ee8cf`. Quality gate **FAIL**:
semantic 95/120, raw READY FP 3/58, unsafe accepted 1/120. Independent replay
**PASS** means original accounting is reproducible, not candidate acceptance.

- `results.json`, `manifest.json`, `dataset.json`: exact original run bytes; all exposed-v1 synthetic data.
- `freeze.json`: exact preregistered generation3 freeze bytes.
- `replay.json`: exact stdout from the offline frozen-source replay, 120 trials and 5 separate warmups.
- `resource_report.json`: exact RUNNING watchdog snapshot saved before the parent stopped its server; SHA256 `af0245a50541eadf95ac689820935fd6d2318d882831a2b951a63b981cb4aeb3`.
- `failure_classification.json`: post-run explanation by first failing invariant. No result, gold or decision is repaired.
- `replay_generation3_32b_exposed.py`: exact executed replay helper.
- `check_generation3_replay_synthetic.py` and `replay_preparation_selfcheck.json`: eight synthetic paths and six rejected row mutations, run before actual result inspection.
- `source_snapshot/`: exact 19-file `git show c6bdbeb:path` snapshot and its SHA manifest; includes the exposed-v1 dataset, no v2 inputs or model weights.
- `original_copy_provenance.json`: original paths, byte counts and hashes for exact copies.
- `integrity.json`: archive file hashes; excludes itself to avoid a recursive hash.

All 125 final generation JSON objects were retained, so replay covered their complete
3.0→2.0→1.0 validation and frozen `evaluate_trial` output. The helper also supports
reporting unretained malformed/transport/schema bodies as unreobservable and does
not reconstruct them or erase their recorded raw READY. This run had zero such rows.
Timing/token usage is retained measurement, not a new benchmark. The resource
report is aggregate GPU sampling, not per-process VRAM attribution. Runtime
metadata is bound to the archive; replay does not attest loaded weights remotely.

Helpers depend on their original location and are **not directly runnable in this
archive directory**. To reproduce in the repository root, restore the exact helper
to `var/review-tools/replay_generation3_32b_exposed.py`, and `source_snapshot/` to
`var/review-snapshots/c6bdbeb400c37016897bfe6b08ab080cc33ee8cf/`. Verify bytes first;
do not overwrite a different existing file. The snapshot record SHA is
`3c99c2cfbfa9cefe8d9edcb73e77c2b6578592ddb60e45158d38d1cde9fd8944`.
The backend environment must supply the existing jsonschema dependency.

```sh
CUDA_VISIBLE_DEVICES='' .conda/bin/python -B var/review-tools/replay_generation3_32b_exposed.py \
  evaluations/results/phase5x/exposed-generation3-32b-diagnostic \
  --freeze evaluations/hardening_v1_exposed_generation3_32b_diagnostic_freeze.json \
  --runtime-dir evaluations/results/phase5x/32b-generation3-v1-launch
```

This requires the preregistered repository files to retain their recorded hashes,
including the nine v2 files (streaming hash only). It makes no network/model/GPU
calls or weight reads. The v2 exposure addendum is preserved: root saw some v2
inputs/gold before this candidate, so fully blind evaluation is not claimed.
Gold is **AUTO-GENERATED / NOT HUMAN VERIFIED**. No IFC execution occurred.

See [independent review](../../../../docs/reviews/phase5x_generation3_32b_exposed_review.md)
for failure families and the comparison with the prior same-model generation2 run.
