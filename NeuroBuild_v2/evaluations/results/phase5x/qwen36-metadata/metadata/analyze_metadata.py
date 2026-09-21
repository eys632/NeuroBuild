"""Analyze already saved public metadata; never tokenize, render, or load a model."""
from pathlib import Path
import collections
import difflib
import hashlib
import json
import math
import re

BASE = Path(__file__).resolve().parent
OLD = BASE.parent / "qwen38-candidate-metadata" / "upstream"
ROOT = BASE.parents[2]
def sha(b): return hashlib.sha256(b).hexdigest()
def read(path): return json.loads(path.read_bytes())
def stable(value): return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())
def save(name, value):
    with (BASE / name).open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write("\n")

ledger = read(BASE / "download_ledger.json")
assert ledger["network_payload_bytes"] <= 128 * 1024 ** 2
for item in ledger["records"]:
    data = (BASE / item["path"]).read_bytes()
    assert len(data) == item["bytes"] and sha(data) == item["sha256"]
u, g = read(BASE / "upstream-api.json"), read(BASE / "gguf-api.json")
assert u["sha"] == "995ad96eacd98c81ed38be0c5b274b04031597b0"
assert g["sha"] == "baec3ebee244827cda0f4557eafa8b28f7545fa6"
selected = next(x for x in g["siblings"] if x["rfilename"] == "Qwen3.6-35B-A3B-Q4_K_M.gguf")
assert selected["size"] == 20419565568
assert selected["lfs"]["sha256"] == "671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7"
src = dict(line.split("=", 1) for line in (BASE / "gguf/.src_sha").read_text().splitlines())
assert src["PRIMARY"] == u["sha"]
c = read(BASE / "upstream/config.json"); t = c["text_config"]
tokenizer = read(BASE / "upstream/tokenizer.json"); old_tokenizer = read(OLD / "tokenizer.json")
tc = read(BASE / "upstream/tokenizer_config.json"); old_tc = read(OLD / "tokenizer_config.json")
template = (BASE / "upstream/chat_template.jinja").read_bytes()
assert tc["chat_template"].encode() == template
assert len(tokenizer["model"]["vocab"]) == 248044 and len(tokenizer["model"]["merges"]) == 247587
comparison = {"kind": "QWEN36_QWEN38_SAVED_METADATA_COMPARISON",
    "status": "STATIC_DIFFERENCES_RECORDED_NOT_NATIVE_EQUIVALENCE_PASS",
    "files": {}, "tokenizer_components": {}, "tokenizer_config_different_keys": [],
    "metadata_only": True, "render_encode_native_or_corpus_calls": 0}
for name in ["config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json", "chat_template.jinja", "LICENSE"]:
    new, old = (BASE / "upstream" / name).read_bytes(), (OLD / name).read_bytes()
    comparison["files"][name] = {"new_bytes": len(new), "new_sha256": sha(new), "old_bytes": len(old),
                                "old_sha256": sha(old), "bytes_equal": new == old}
for key in sorted(set(tokenizer) | set(old_tokenizer)):
    comparison["tokenizer_components"][key] = {"equal": tokenizer.get(key) == old_tokenizer.get(key),
        "new_structured_sha256": stable(tokenizer.get(key)), "old_structured_sha256": stable(old_tokenizer.get(key))}
comparison["tokenizer_config_different_keys"] = [k for k in sorted(set(tc) | set(old_tc)) if tc.get(k) != old_tc.get(k)]
comparison["added_tokens"] = {"new_count": len(tokenizer["added_tokens"]), "old_count": len(old_tokenizer["added_tokens"]),
    "old_only_ids": [x["id"] for x in old_tokenizer["added_tokens"] if x not in tokenizer["added_tokens"]],
    "new_only_ids": [x["id"] for x in tokenizer["added_tokens"] if x not in old_tokenizer["added_tokens"]],
    "tokenizer_config_added_tokens_decoder_count": len(tc["added_tokens_decoder"]),
    "decoder_vs_json_count_difference_requires_actual_converted_header_check": True}
comparison["normalizer"] = tokenizer["normalizer"]
comparison["restricted_template_path"] = {"conditions": ["enable_thinking=false", "one nonempty system message",
    "one string user message", "no tools", "no assistant history", "no multimodal content"],
    "source_diff_suggests_same_rendered_bytes": True, "rendered_byte_equality_measured": False,
    "differences_outside_restricted_path": ["reasoning_effort instruction injection", "empty system handling",
        "historical thinking preservation default and inline thought extraction", "empty tool arguments condition"],
    "full_template_hash_equal": False}
comparison["reuse_limit"] = "No inherited native parity/context/template PASS. Compare actual typed GGUF metadata and effective request path first. Existing NFC mismatch cannot become official-equivalence PASS by relabeling."
save("metadata_comparison_qwen38.json", comparison)
with (BASE / "chat_template_vs_qwen38.diff").open("x", encoding="utf-8") as f:
    f.writelines(difflib.unified_diff((OLD / "chat_template.jinja").read_text().splitlines(True), template.decode().splitlines(True),
                                     fromfile="pinned-Qwen3.8/chat_template.jinja", tofile="pinned-Qwen3.6/chat_template.jinja"))

log_raw = (BASE / "gguf/convert.log").read_bytes(); lines = log_raw.decode().splitlines()
start = next(i for i, line in enumerate(lines) if line.startswith("+ ") and "llama-quantize" in line and "Q4_K_M.gguf" in line)
end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("+ "))
rows = []
pattern = re.compile(r"^\[\s*(\d+)/\s*(\d+)\] (\S+)\s+- \[([^]]+)\], type =\s*(\w+), (.*)$")
for line in lines[start:end]:
    m = pattern.match(line)
    if not m: continue
    dest = re.search(r"converting to (\w+)", m[6])
    rows.append({"ordinal": int(m[1]), "total": int(m[2]), "name": m[3], "shape": [int(x) for x in m[4].split(",")],
                 "source_dtype": m[5], "destination_dtype": dest[1] if dest else m[5]})
assert len(rows) == 733 and [r["ordinal"] for r in rows] == list(range(1, 734))
inventory = {"kind": "QWEN36_PUBLIC_CONVERSION_LOG_TENSOR_INVENTORY",
    "status": "EXPECTED_FROM_PUBLISHED_LOG_NOT_ACTUAL_GGUF", "source_path": "gguf/convert.log",
    "source_sha256": sha(log_raw), "source_lines_inclusive": [start + 1, end], "command": lines[start],
    "tensor_count": len(rows), "destination_dtype_counts": dict(collections.Counter(r["destination_dtype"] for r in rows)),
    "tensor_rows": rows, "actual_gguf_header_read": False, "weight_payload_read": False,
    "source_primary_conversion_no_mtp": "--no-mtp" in lines[4],
    "runtime_conversion_commit": "NOT_PUBLISHED_AS_EXACT_COMMIT_IN_OBSERVED_LOG"}
if (BASE / "conversion_tensor_inventory.json").exists():
    assert read(BASE / "conversion_tensor_inventory.json") == inventory
else:
    save("conversion_tensor_inventory.json", inventory)
types = {"f32": (1, 4), "q4_K": (256, 144), "q6_K": (256, 210), "q8_0": (32, 34)}
payload = sum(math.prod(r["shape"]) // types[r["destination_dtype"]][0] * types[r["destination_dtype"]][1] for r in rows)
build_short = re.search(r"llama_print_build_info: build = \d+ \(([^)]+)\)", "\n".join(lines[start:end]))[1]
save("conversion_summary.json", {"status": "PUBLISHED_LOG_NOT_ACTUAL_GGUF", "tensor_count": len(rows),
    "destination_dtype_counts": dict(collections.Counter(r["destination_dtype"] for r in rows)),
    "expected_tensor_payload_bytes": payload, "published_file_bytes": selected["size"],
    "file_minus_expected_payload_bytes": selected["size"] - payload,
    "primary_no_mtp": "--no-mtp" in lines[4], "primary_block_count": 40,
    "quantizer_build_short_commit": build_short, "quantizer_compiler": "GNU 14.2.0 Linux x86_64",
    "full_converter_commit_verified": False, "local_runtime_source_commit": "f072b103714dfa1eee531f80b24512faf38e3dd2",
    "runtime_equals_converter_build_claimed": False, "gguf_header_read": False,
    "warning": "Loader dump describes input BF16 file_type32; final Q4_K_M header is not observed. Actual quantized rows, not command override names, define expected mixed tensor types.",
    "source_log_sha256": sha(log_raw), "source_lines_inclusive": [start + 1, end]})

by_path = {r["path"]: r for r in ledger["records"]}
manifest = {"model_id": g["id"], "revision": g["sha"], "license": "apache-2.0",
            "source": f"https://huggingface.co/api/models/{g['id']}/revision/{g['sha']}?blobs=true", "files": []}
for name in ["README.md", ".src_sha", "convert.log"]:
    r = by_path["gguf/" + name]
    manifest["files"].append({"name": name, "bytes": r["bytes"], "sha256": r["sha256"]})
manifest["files"].append({"name": selected["rfilename"], "bytes": selected["size"], "sha256": selected["lfs"]["sha256"]})
save("candidate_download_manifest_draft.json", manifest)
recipe = {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0, "presence_penalty": 1.5,
          "frequency_penalty": 0.0, "repeat_penalty": 1.0, "repeat_last_n": 64, "seed": 42,
          "samplers": ["penalties", "top_k", "top_p", "min_p", "temperature"]}
save("sampling_profile_proposal.json", {"status": "METADATA_AND_SOURCE_REVIEW_ONLY_NOT_IMPLEMENTED",
    "profile_name": "qwen36_nonthinking_llama_cpp", "protocol": "llama_cpp_json_schema",
    "official_card_nonthinking": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0,
                                 "presence_penalty": 1.5, "repetition_penalty": 1.0},
    "official_generation_config_defaults": read(BASE / "upstream/generation_config.json"),
    "explicit_project_request_proposal": recipe, "enable_thinking": False, "enable_reasoning": False,
    "reasoning_parser": "deepseek", "max_output_tokens": 768, "max_context_tokens": 4096,
    "not_fully_specified_by_official_card": ["repeat_last_n", "frequency_penalty", "seed", "sampler_order", "output_context_caps"],
    "prior_project_basis": "Existing EXAONE native presence1.5 profile uses window64 and this active sampler order; this is a project choice, not extra official Qwen recommendations.",
    "prompt_and_generated_tokens_both_contribute_to_presence_history": True,
    "zero_history_window_would_disable_presence_penalty": True,
    "application_input_output_normalization_or_repair": False, "automatic_raw_unicode_variant_inheritance": False,
    "old_v2_context_automatically_requested": False, "future_context_scope_if_needed": "exposed120 only after separate authorization",
    "source_refs": ["tools/server/server-schema.cpp:126", "common/sampling.cpp:346", "common/sampling.cpp:380",
                    "common/sampling.cpp:496", "tools/server/server-context.cpp:424", "src/llama-sampler.cpp:2885"],
    "official_card_ref": {"path": "upstream/README.md", "sha256": by_path["upstream/README.md"]["sha256"], "lines": [1008, 1009]}})
save("provenance.json", {"kind": "QWEN36_PINNED_CANDIDATE_METADATA", "status": "METADATA_VERIFIED_NOT_RUNTIME_OR_QUALITY_VALIDATED",
    "upstream": {"model_id": u["id"], "revision": u["sha"], "api_ref": by_path["upstream-api.json"]},
    "gguf": {"model_id": g["id"], "revision": g["sha"], "api_ref": by_path["gguf-api.json"],
             "selected_weight_metadata": selected, "payload_downloaded": False, "header_observed": False},
    "conversion_source": {"src_sha_entries": src, "primary_revision_matches_pinned_upstream": True,
        "source_revision_ref": by_path["gguf/.src_sha"], "public_log_ref": by_path["gguf/convert.log"],
        "quantizer_short_commit": build_short, "full_conversion_source_commit_verified": False,
        "local_runtime_same_conversion_build_claimed": False, "imatrix_calibration_not_documented_in_preserved_log": True,
        "no_mtp_primary": True, "mmproj_mtp_dflash_excluded": True},
    "license": {"upstream_api_card": u.get("cardData", {}).get("license"), "gguf_api_card": g.get("cardData", {}).get("license"),
        "upstream_license_original": by_path["upstream/LICENSE"], "copyright_notice": "Copyright 2026 Alibaba Cloud",
        "gguf_standalone_license_published": any(s["rfilename"] in ["LICENSE", "LICENSE.txt"] for s in g["siblings"])},
    "metadata_download": {"original_file_count": len(ledger["records"]), "network_payload_bytes": ledger["network_payload_bytes"],
        "individual_cap_bytes": ledger["individual_cap_bytes"], "total_cap_bytes": ledger["total_cap_bytes"],
        "preserved_failures": ledger["failures"], "disk_free_before_bytes": ledger["disk_free_before_bytes"]},
    "architecture": {"hf_architecture": c["architectures"], "native_expected_architecture": "qwen35moe",
        "hidden_size": t["hidden_size"], "vocab_size": t["vocab_size"], "layers": t["num_hidden_layers"],
        "layer_type_counts": dict(collections.Counter(t["layer_types"])), "routed_experts": t["num_experts"],
        "active_experts": t["num_experts_per_tok"], "expert_intermediate": t["moe_intermediate_size"],
        "shared_expert_intermediate": t["shared_expert_intermediate_size"], "config_mtp_layers": t["mtp_num_hidden_layers"],
        "published_primary_conversion_mtp_layers": 0, "tied_embeddings": t["tie_word_embeddings"]},
    "template": {"official_sha256": sha(template), "bytes": len(template), "tokenizer_config_inline_exact": True,
        "equals_qwen38_bytes": False, "actual_embedded_verified": False},
    "tokenizer": {"json_sha256": by_path["upstream/tokenizer.json"]["sha256"], "normalizer": tokenizer["normalizer"],
        "public_native_parity_observed": False, "qwen38_metadata_comparison": "metadata_comparison_qwen38.json"},
    "scope": {"weights_or_ranges": 0, "installs": 0, "native_or_GPU": 0, "tokenizer_encode_or_render": 0,
        "corpus_or_heldout_reads": 0, "model_calls": 0, "production_edits": 0},
    "limits": ["Published conversion metadata is not an actual header/payload audit.",
        "Equal base BPE model does not prove entire tokenizer equality: added token inventories differ.",
        "Restricted template source equivalence has not been rendered or measured.",
        "NFC normalizer is retained; no old raw-reference variant is automatically adopted.",
        "The explicit candidate recipe remains a proposal until separately implemented and frozen."]})
print(json.dumps({"status": "METADATA_ANALYSIS_SAVED", "raw_files": len(ledger["records"]), "payload_bytes": ledger["network_payload_bytes"],
                  "published_tensors": len(rows), "expected_tensor_payload_bytes": payload, "quantizer_short_commit": build_short}))
