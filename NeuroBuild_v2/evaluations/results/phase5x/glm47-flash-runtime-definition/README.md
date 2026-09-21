# GLM runtime definition and saved CPU evidence

Prepared from source commit `0ffb1e24c86aeb016cb585b2b9abd66d6cabe910`. This archive records definitions and saved CPU validation only. It contains no GLM GPU startup, HTTP generation, resource-probe or quality result.

`aggregate/final-cpu-proof.json` combines the actual saved public/header/vocabulary/context receipts. The official tokenizer IDs and raw roundtrips matched 20 public cases, and the 200 recorded context inputs fit 4096 with output cap 768. This does not guarantee arbitrary Unicode roundtrips. Prior public expectation failures stay in the earlier preparation archive. Linked exact copies are listed in `references.json`.

The six new CPU controls passed before the final readiness release. The final missing-pin readiness boundary was then checked once. `proofs/glm47-runtime-v2-cpu-proof.json` identifies both source states and logs; the tested CPU-provenance function is unchanged. Finalization only replaced the unconditional readiness blocker with the root-reviewed aggregate pin and added source-observed native startup warmup scope. Historical preparation files and pre-final definitions are retained.

The following explicit commands were used for the first GLM epoch after the root resource decision and guard readiness. The completed probes are preserved in adjacent observation archives; do not repeat them.

```sh
CUDA_VISIBLE_DEVICES='' PYTHONPATH=src .conda/bin/python var/research/run_native_glm47_epoch1_probe_v2.py startup --cpu-proof-sha256 54ab0062c5d22112ed3349e0021391a4dd17f6d5f8698ac8a02cc096b08a1847
CUDA_VISIBLE_DEVICES='' PYTHONPATH=src .conda/bin/python var/research/run_native_glm47_epoch1_probe_v2.py public --cpu-proof-sha256 54ab0062c5d22112ed3349e0021391a4dd17f6d5f8698ac8a02cc096b08a1847
CUDA_VISIBLE_DEVICES='' PYTHONPATH=src .conda/bin/python var/research/run_native_glm47_epoch1_probe_v2.py resource --cpu-proof-sha256 54ab0062c5d22112ed3349e0021391a4dd17f6d5f8698ac8a02cc096b08a1847
```

Startup performs three metadata GETs. Public performs one production POST, and resource performs one independent nongrammar synthetic boundary POST. Response bodies/reasoning are not archived. The server has its native internal startup warmup enabled; explicit HTTP-generation counts do not count those internal decodes. The historical generic helper is copied without changes and its source hash remains pinned. Full source/build/GGUF validation and own-process safety are provided by the existing guarded launcher, not by this archive.
