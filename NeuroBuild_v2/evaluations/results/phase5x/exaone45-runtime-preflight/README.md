# EXAONE runtime/replay preparation archive

Final runtime consumer: `runtime/exaone45_runtime_probe_v4.py`. Final offline replay: `replay/replay_native_exaone45_exposed_v3.py`. These files are exact source bytes; use their recorded original project paths when reproducing imports. Root owns launch and all live probes.

The explicit candidate is `exaone45-gguf-continue-free-raw-unicode-korean-v1`: effective continue-free template and a native raw-Unicode tokenizer contract. The original official HF token-ID comparison remains **FAIL 18/20**. The derived reference reports 20/20 on its public corpus; no all-Unicode or official-equivalence claim is made. CPU aggregate/linked proofs are archived separately in `../exaone45-cpu-preflight/`.

New runtime controls: four focused tests, 15 changed-evidence rejections, three wrong-proof entrypoint rejections. New replay controls: 18 metadata mutations rejected, three inherited replay core functions AST-identical, plus synthetic final identity compatibility. These checks did not replay any actual response or dataset and did not make model/HTTP/GPU/native calls. No full runtime or backend regression was repeated here; the source-matched 408-test receipt remains in `../exaone45-template-header-preflight/`.

`history/` preserves blocked drafts, earlier design assumptions and their receipts. They are not eligible launch or replay versions. One new selfcheck initially retained an old receipt filename; exclusive create blocked overwrite. The corrected receipt records this and the preserved old hash.

`root/` contains exact fresh config, one-step controller, config-binding receipt and prelaunch GPU3 receipt supplied by root. Static live-epoch evidence is separate: `../exaone45-native-startup-epoch1/` (five JSON files), `../exaone45-native-public-smoke-epoch1/report.json`, and `../exaone45-native-resource-epoch1/report.json`. This archive excludes the changing live guard report, response/reasoning bodies, weights, native binaries, environment files and datasets. No quality success or adoption is asserted.

`integrity.json` records all archive file SHA-256 values and exact original source paths. `source_refs.json` pins unchanged historical generic helpers without duplicating them. Production source, prompts, schemas and gold were not changed by this archive task.
