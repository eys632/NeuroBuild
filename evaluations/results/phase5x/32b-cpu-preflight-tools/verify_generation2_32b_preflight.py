"""Pinned 32B tokenizer/metadata/grammar CPU check; no model or weight load."""
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
assert os.environ.get("HF_HUB_OFFLINE") == "1"
assert os.environ.get("TRANSFORMERS_OFFLINE") == "1"
ROOT = Path(__file__).resolve().parents[2]
sha = lambda data: hashlib.sha256(data).hexdigest()
manifest_path = ROOT / "var/research/qwen3-32b-awq-feasibility/0499c3ac83fdef8810b907a23894ba91e95eddd8/qwen3-32b-awq.json"
manifest = json.loads(manifest_path.read_text())
revision = manifest["revision"]
assert revision == "0499c3ac83fdef8810b907a23894ba91e95eddd8"
model_path = ROOT / "var/models/Qwen--Qwen3-32B-AWQ" / revision
assert sha((model_path / "neurobuild-manifest.json").read_bytes()) == sha(manifest_path.read_bytes())
metadata_results = []
for record in manifest["files"]:
    if record["name"].endswith(".safetensors"):
        continue
    assert record["bytes"] < 20 * 1024 * 1024
    path = model_path / record["name"]
    assert not path.is_symlink() and path.resolve().is_relative_to(model_path.resolve())
    data = path.read_bytes()
    assert len(data) == record["bytes"] and sha(data) == record["sha256"], record["name"]
    metadata_results.append({"name": record["name"], "bytes": len(data), "sha256": sha(data)})
assert len(metadata_results) == 9
config = json.loads((model_path / "config.json").read_text())
tokenizer_config = json.loads((model_path / "tokenizer_config.json").read_text())
assert not (model_path / "chat_template.jinja").exists()
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
assert "torch" not in sys.modules
assert tokenizer.chat_template == tokenizer_config["chat_template"]
template_sha = sha(tokenizer.chat_template.encode("utf-8"))
prompt_path = ROOT / "prompts/requirement_generation_v2_v2.txt"
prompt = prompt_path.read_text()
schema_path = ROOT / "schemas/requirement_generation_v2_decision_branches.schema.json"
schema = json.loads(schema_path.read_text())


def messages(source, context):
    return [{"role": "system", "content": prompt}, {"role": "user", "content": json.dumps(
        {"source_text": source, "axis_convention": context}, ensure_ascii=False)}]


control = tokenizer.apply_chat_template(messages("책상을 X축 +1m 옮겨줘.", "project_xy"),
    tokenize=False, add_generation_prompt=True, enable_thinking=False)
suffix = control.rsplit("<|im_start|>assistant\n", 1)[1]
assert suffix == "<think>\n\n</think>\n\n"
splits = {}
for name, filename, count in (
    ("development", "evaluations/requirement_hardening_v1_development.jsonl", 40),
    ("exposed_previous_holdout_regression", "evaluations/requirement_hardening_v1_holdout.jsonl", 80),
    ("unused_v2_holdout_length_only", "evaluations/requirement_hardening_v2_holdout.jsonl", 80),
):
    raw = (ROOT / filename).read_bytes()
    rows = [json.loads(line) for line in raw.splitlines() if line]
    assert len(rows) == count
    lengths = [len(tokenizer.apply_chat_template(messages(row["input"], row["context"].get("axis_convention")),
        tokenize=True, add_generation_prompt=True, enable_thinking=False)) for row in rows]
    assert max(lengths) + 768 <= 4096
    splits[name] = {"dataset": filename, "dataset_sha256": sha(raw), "count": count,
        "minimum_input_tokens": min(lengths), "maximum_input_tokens": max(lengths),
        "max_input_plus_output": max(lengths) + 768, "remaining_context": 4096 - max(lengths) - 768,
        "scope": ("INPUT_LENGTH_ONLY; unopened model-output holdout; no case text or gold disclosed" if name == "unused_v2_holdout_length_only" else "INPUT_LENGTH_ONLY; already exposed material, not new unseen holdout")}
assert "torch" not in sys.modules

from jsonschema import Draft202012Validator
from neurobuild.application.requirement_generation import GenerationContract, parse_generated_requirement
validator = Draft202012Validator(schema)
Draft202012Validator.check_schema(schema)
inputs = [json.loads(line.removeprefix("입력: ")) for line in prompt.splitlines() if line.startswith("입력: ")]
examples = [json.loads(line.removeprefix("출력: ")) for line in prompt.splitlines() if line.startswith("출력: ")]
assert len(inputs) == len(examples) == 7
for source, output in zip(inputs, examples):
    assert validator.is_valid(output)
    parse_generated_requirement(json.dumps(output, ensure_ascii=False), generation_contract=GenerationContract.QUOTES,
        source_text=source["source_text"], axis_convention=source["axis_convention"],
        requirement_id=uuid4(), project_id=uuid4(), base_revision_id=uuid4())

# xgrammar imports Torch for CPU grammar operations only, after tokenization.
import xgrammar as xgr
import torch
assert not torch.cuda.is_initialized()
util_path = ROOT / ".conda-vllm/lib/python3.12/site-packages/vllm/model_executor/guided_decoding/utils.py"
spec = importlib.util.spec_from_file_location("nb_guided_utils", util_path)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)
assert not utils.has_xgrammar_unsupported_json_features(schema)
compiler = xgr.GrammarCompiler(xgr.TokenizerInfo.from_huggingface(tokenizer,
    vocab_size=config["vocab_size"]), max_threads=2)
started = time.monotonic()
grammar = compiler.compile_json_schema(schema, any_whitespace=True)
compile_seconds = time.monotonic() - started
ready = {"schema_version": "2.0", "decision": "READY", "target_selection_quote": "회의실 책상",
    "current_instruction_quote": "회의실 책상을 X축 +1m, Y축 -2cm 옮겨줘.",
    "dx_evidence": "X축 +1m", "dy_evidence": "Y축 -2cm", "reason": None}
nonready = {"schema_version": "2.0", "decision": "CLARIFICATION", "target_selection_quote": "회의실 책상",
    "current_instruction_quote": None, "dx_evidence": None, "dy_evidence": None, "reason": "조건 확인이 필요합니다."}
fixtures = [(f"prompt_example_{i + 1}", obj, True) for i, obj in enumerate(examples)]
fixtures.append(("ready_both_axes", ready, True))
fixtures.extend([
    ("root_version_only", {"schema_version": "2.0"}, False),
    ("ready_no_axis", dict(ready, dx_evidence=None, dy_evidence=None), False),
    ("ready_null_target", dict(ready, target_selection_quote=None), False),
    ("ready_null_instruction", dict(ready, current_instruction_quote=None), False),
    ("ready_nonnull_reason", dict(ready, reason="확인"), False),
    ("wrong_version", dict(ready, schema_version="1.0"), False),
    ("extra_approval", dict(ready, approval=True), False),
    ("nonready_null_reason", dict(nonready, reason=None), False),
])
for decision in ("CLARIFICATION", "UNSUPPORTED"):
    for field in ("current_instruction_quote", "dx_evidence", "dy_evidence"):
        fixtures.append((decision + "_nonnull_" + field,
            dict(nonready, decision=decision, **{field: "X축 +1m"}), False))
fixture_results = []
for name, output, expected in fixtures:
    assert validator.is_valid(output) == expected, name
    matcher = xgr.GrammarMatcher(grammar)
    tokens_ok = all(matcher.accept_token(token) for token in tokenizer.encode(
        json.dumps(output, ensure_ascii=False), add_special_tokens=False))
    accepted = tokens_ok and matcher.accept_token(tokenizer.eos_token_id)
    assert accepted == expected, name
    fixture_results.append({"case": name, "expected_accepted": expected,
                            "tokens_and_eos_accepted": accepted})
assert not torch.cuda.is_initialized()
proof = {
    "kind": "CPU_ONLY_GENERATION2_32B_AWQ_PREFLIGHT", "status": "PASS",
    "model_id": manifest["model_id"], "model_revision": revision,
    "weight_manifest_sha256": sha(manifest_path.read_bytes()),
    "local_downloader_manifest_matches": True, "small_metadata_verified": metadata_results,
    "small_metadata_count": len(metadata_results), "weights_read": False,
    "license": manifest["license"], "tokenizer_class": type(tokenizer).__name__,
    "chat_template_origin": "tokenizer_config.json embedded chat_template; no separate jinja file",
    "chat_template_sha256": template_sha, "actual_tokenizer_template_equals_embedded": True,
    "enable_thinking": False, "assistant_generation_suffix": suffix,
    "empty_think_prefix_is_template_not_model_reasoning": True,
    "transformers": importlib.metadata.version("transformers"),
    "torch_imported_during_tokenization": False, "torch_imported_for_cpu_grammar": True,
    "prompt_sha256": sha(prompt_path.read_bytes()), "schema_sha256": sha(schema_path.read_bytes()),
    "adapter_sha256": sha((ROOT / "src/neurobuild/application/requirement_generation.py").read_bytes()),
    "legacy_parser_sha256": sha((ROOT / "src/neurobuild/application/requirements.py").read_bytes()),
    "system_prompt_tokens": len(tokenizer.encode(prompt, add_special_tokens=False)),
    "context_limit": 4096, "output_cap": 768, "splits": splits,
    "grammar": {"xgrammar": importlib.metadata.version("xgrammar"),
        "vllm_unsupported_features": False, "vocab_size": config["vocab_size"],
        "compile_seconds": compile_seconds, "fixtures": fixture_results,
        "accepted_count": sum(row[2] for row in fixtures),
        "rejected_count": sum(not row[2] for row in fixtures),
        "prompt_examples_schema_adapter_legacy_pass": 7},
    "cuda_visible_devices": "", "cuda_initialized": torch.cuda.is_initialized(),
    "model_calls": 0, "network_calls": 0, "gpu_queries": 0,
    "scope": "Existing 32B metadata/tokenizer/CPU grammar only. Original120 are exposed regression; new v2 80 used only for CPU input-length accounting, without model calls or input/gold disclosure. No model quality result or GPU runtime verification.",
}
destination = ROOT / "var/research" / ("generation2-32b-preflight-" + uuid4().hex + ".json")
with destination.open("x") as handle:
    json.dump(proof, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
print(json.dumps({"proof_path": str(destination.relative_to(ROOT)), "proof_sha256": sha(destination.read_bytes()),
    "manifest_sha256": proof["weight_manifest_sha256"], "template_sha256": template_sha,
    "small_metadata_count": len(metadata_results), "system_tokens": proof["system_prompt_tokens"],
    "splits": splits, "compile_seconds": compile_seconds,
    "valid_fixtures": proof["grammar"]["accepted_count"], "invalid_fixtures": proof["grammar"]["rejected_count"],
    "cuda_initialized": False}, ensure_ascii=False))
