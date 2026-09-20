# EXAONE override-aware runtime probe v2: design, not execution evidence

Status: **PLAN; pending final launcher pin, actual public override CPU proof, full GGUF/context proof and explicit tokenizer contract**. No v2 live helper has been enabled. The v1 helper remains byte-exact (`3e3dca…d49ef`) with its unconditional tokenizer-pending rejection; generic helper `ac100d…f9f63` and Gemma v3 also remain unchanged. No HTTP, process inspection, native/model/GPU calls or dataset-body reads occurred in this design task.

Machine-readable inputs: `exaone45_runtime_probe_v2_input_plan.json`, SHA256 `87c5160b235aa6d29ba2c21aaf992427d5b1d1074faa8d0efd015eb5cc3d456f`. Its required-PASS fields are expectations for later evidence, not observed outcomes; unknown pins are null.

## Candidate and three different template identities

Candidate label: `exaone45-gguf-continue-free-korean-v1`. This identifies the derived template and Korean sampling experiment; it does not select a raw-Unicode policy or imply official-template execution. Original source/gold/prompt/user text are unchanged. The motivation is root's observed original-minja failure dropping the first8974-byte system message and producing a177-byte native prompt; preserve that earlier failure independently, even if earlier grammar-only checks passed.

| Identity | Bytes | SHA256 |
| --- | ---: | --- |
| Official original / GGUF embedded template | 5930 | `e4ece7acc79ba82121d4d57791fb7ecb796e39185087197377da5d2286bec0e5` |
| Explicit effective override file | 5829 | `7de6c8ba3df6db54564c7a63385cc29572c0a616d5848961e969ecbb8c349851` |
| Expected `/props` representation of override | 5828 | `b8bc1ef1b1fcd30cdd28fe7655bf79020aec666142107c01231b7b59f15cb1ef` |

The override is `var/research/native-exaone45-contract/chat_template_continue_override.jinja`. Its current bytes contain no CR and end in LF; pinned Jinja lexer removes one terminal LF from the template source reported by props. This is a source-derived expectation, not an HTTP observation. No arbitrary strip/normalization of templates, application input, generated content or evidence is allowed.

Proposed metadata meaning: strict production `runtime_metadata.chat_template_sha256` becomes the **effective override** SHA for this new candidate. It previously equaled the embedded template only because no override existed. Preserve `original_embedded_chat_template_sha256/bytes`, `effective_chat_template_sha256/bytes`, `props_reported_template_sha256/bytes` and derivation label separately in startup/CPU evidence. The unchanged metadata schema's `startup_report_sha256` binds variant and those extra fields. The future freeze should repeat the exact binding and explicitly declare the override; it must never call effective bytes the original embedded template.

## Minimum implementation surface in a new helper

Create a separate `exaone45_runtime_probe_v2.py` after the input design is finalized. Do not edit v1 or generic helpers.

1. Pin the newly reviewed launcher file SHA as well as the unchanged native binary/build/source/library closure. The launcher pin is currently unavailable. A new config must carry both non-null `chat_template_path` and `chat_template_sha256` matching the exact approved override. The legacy generic `load_config` does not turn this optional string into Path; v2 needs a small own loader that additionally converts this one field, then invokes the same `NativeLaunchConfig` validation. Missing/half-paired/other-template inputs must fail before HTTP or process inspection.
2. Call the generic artifact binding for model/header/binary/library/source checks, then call the new production `pinned_chat_template` (or identically bounded checked-file/hash validation) for the small override. Augment the returned artifacts with exactly `chat_template_override={path: project-relative, sha256: effective_hash}`. The generic `validate_guard` can then compare the entire dictionary to the live guard's `native_artifacts` including this member. The existing `epoch` calls the current pinned production `native_arguments`, which includes `--chat-template-file <exact path>`, so full-argv identity includes the override without relaxing the own-UID/PID/startticks checks. An earlier epoch without the override cannot satisfy this equality.
3. Require the final header to bind original embedded SHA and official tokenizer metadata, separately from the override. Model path/revision/file SHA/bytes, exact manifest, profile/native protocol, GPU3/internal0,64/64, context4096/seq1/F16KV and whole28672/allowance0 stay unchanged. No automatic fallback to embedded template, other Unicode mode, or another runtime is allowed.
4. Replace only model-specific CPU provenance and props expectation/metadata construction. Keep common before/after guard checks, own loopback listeners, bounded GET/POST transport, no raw-body persistence, one public production-schema call and one full4096 resource call. A caller-supplied proof hash is required but cannot replace inspection of scope/status/field relationships. All live entrypoints remain fail-closed until actual evidence and root's technical contract decision exist.

## Evidence schema agreed with the CPU owner

The final aggregate remains `EXAONE45_NATIVE_CONTRACT_CPU_PROOF` and includes explicit model/revision/manifest/protocol/profile/source pin, original GGUF/header/tokenizer hashes, five application-source hashes,768/4096 caps, frozen split length summaries and actual native token evidence. Add:

```text
chat_template_override = {
  path, sha256, bytes,
  original_embedded_template_sha256,
  transform: "continue-free-system-message-branch-v1"
}
template_render_parity = {
  status: "PASS", reference_cases: 18,
  official_original_derived_reference_byte_equal: true,
  derived_native_system_and_user_exact: true,
  derived_native_prompt_equals_official_reference: true,
  proof_ref: {path, sha256}
}
```

These are required future values, not claims that the18 native comparisons have run. The CPU owner plans a separate `public-proof-v3.json` with kind `EXAONE45_NATIVE_PUBLIC_TEMPLATE_CPU_PROOF`; it is insufficient by itself for model launch. Proposed concrete public fields are top-level `template_reference_cases=18`, `official_original_derived_reference_byte_equal=true`, `official_embedded_template_sha256`, `candidate_template_sha256`; native fields `public_template_reference_cases=18`, `derived_native_system_and_user_exact=true`, `derived_native_prompt_equals_official_reference=true`. The aggregate consumer must bind those exact native/top-level fields to the map above and retain its proof hash. Results establish parity only over those scoped public cases and the captured production request, not arbitrary chat histories.

The actual production request capture must bind final client SHA, prompt SHA and request bytes/hash. Reference/native rendered-byte equality must include the entire system policy and user JSON in order, not merely find one marker or count a few substrings. The original failure and prior public proofs remain separate immutable evidence. No semantic policy text or few-shot changes are part of this template control-flow workaround.

Unicode remains a separate unresolved contract. The official reference fixture currently records raw-original roundtrip18/20, normalized-source match20/20 and indices11,12; this is not actual native GGUF parity. Preserve those observations and later actual native ID/raw-roundtrip results explicitly. Do not inherit Qwen's raw-Unicode variant, label18/20 as20/20, or introduce input/output NFC repair. A full context proof and proven native ordinary resource token must reflect whichever exact contract root selects later.

## Narrow future controls

When v2 is implemented, use only new fake controls for the changed boundary: reject missing/changed override and launcher pin before live work; parse optional path correctly; require config/file/guard artifact/full argv agreement; reject original-embedded or props hash where effective hash is required; reject public proof without exact system/user preservation or native/reference equality; reject missing/fake full CPU or unapproved tokenizer contract. Keep zero live calls while pending. The inherited resource/lifecycle suite and old model probes need not be rerun merely to test this template-binding addition.
