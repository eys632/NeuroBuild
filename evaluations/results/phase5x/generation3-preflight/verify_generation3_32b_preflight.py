"""Prepared offline generation3 CPU proof; run only after implementation is ready.

Tokenizes actual fake-captured client payloads; checks schema/xgrammar and
adapter fixtures. V2 data is used for INPUT LENGTH ONLY. No input/gold/case ID,
model output, or reasoning is printed. No weight tensor or real HTTP call.
"""
import ast
from copy import deepcopy
from email.message import Message
from hashlib import sha256
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
REVISION = "0499c3ac83fdef8810b907a23894ba91e95eddd8"
MODEL = ROOT / "var/models/Qwen--Qwen3-32B-AWQ" / REVISION
PROMPT = ROOT / "prompts/requirement_generation_v3_v1.txt"
SCHEMA = ROOT / "schemas/requirement_generation_v3.schema.json"
BASELINE = ROOT / "var/research/generation3_legacy_baseline.json"
OUTPUT_CAP = 1024
CONTEXT = 4096
ROOT_ORDER = ("schema_version", "facts", "target_selection_quote", "current_instruction_quote",
              "dx_evidence", "dy_evidence", "reason", "decision")
FACT_ORDER = ("intent", "condition", "condition_quote", "target_class", "target_count", "motion",
              "axis_completeness", "authority", "authority_quote", "selection_scope_quote", "selection_exclusion_quote")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def deny_network(*args, **kwargs):
    raise RuntimeError("NETWORK_DISABLED_FOR_CPU_PROOF")


def text(obj):
    """Fixture order follows the proposed grammar; never reorder model outputs."""
    if type(obj) is dict:
        obj = {**{key: obj[key] for key in ROOT_ORDER if key in obj},
               **{key: value for key, value in obj.items() if key not in ROOT_ORDER}}
        if type(obj.get("facts")) is dict:
            facts = obj["facts"]
            obj["facts"] = {**{key: facts[key] for key in FACT_ORDER if key in facts},
                            **{key: value for key, value in facts.items() if key not in FACT_ORDER}}
    return json.dumps(obj, ensure_ascii=False)


class Response(io.BytesIO):
    status = 200

    def __init__(self, data):
        super().__init__(data)
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"
        self.headers["Content-Length"] = str(len(data))


class Capture:
    def __init__(self):
        self.payload = None
        self.calls = 0

    def open(self, request, *, timeout):
        self.payload = json.loads(request.data)
        self.calls += 1
        # Transport fixture only; its empty JSON is not scored as model output.
        return Response(json.dumps({"model": "neurobuild-local", "choices": [{"index": 0,
            "finish_reason": "stop", "message": {"role": "assistant", "content": "{}"}}]}).encode())


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert os.environ.get("HF_HUB_OFFLINE") == os.environ.get("TRANSFORMERS_OFFLINE") == "1"
    assert os.environ.get("USE_TORCH") == "0" and "torch" not in sys.modules
    socket.create_connection = deny_network
    socket.getaddrinfo = deny_network
    files = [PROMPT, SCHEMA, ROOT / "src/neurobuild/application/requirements.py",
             ROOT / "src/neurobuild/application/requirement_generation.py",
             ROOT / "src/neurobuild/application/requirement_facts.py",
             ROOT / "src/neurobuild/infrastructure/local_model.py", ROOT / "scripts/evaluate_requirements.py",
             ROOT / "docs/requirement_facts_contract_design.md", ROOT / "runtime/models/qwen3-32b-awq.json"]
    source_hashes = {str(path.relative_to(ROOT)): digest(path) for path in files}
    baseline = json.loads(BASELINE.read_text())
    assert source_hashes["src/neurobuild/application/requirements.py"] == baseline["canonical_parser_sha256"]
    nodes = {node.name: node for node in ast.parse((ROOT / "src/neurobuild/application/requirement_generation.py").read_text()).body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    actual_ast = {name: sha256(ast.dump(nodes[name], include_attributes=False).encode()).hexdigest()
                  for name in baseline["generation2_function_ast_sha256"]}
    assert actual_ast == baseline["generation2_function_ast_sha256"]
    manifest = json.loads((ROOT / "runtime/models/qwen3-32b-awq.json").read_text())
    assert manifest["model_id"] == "Qwen/Qwen3-32B-AWQ" and manifest["revision"] == REVISION
    assert digest(MODEL / "neurobuild-manifest.json") == source_hashes["runtime/models/qwen3-32b-awq.json"]
    metadata = {row["name"]: row for row in manifest["files"]}
    checked = {}
    for name in ("config.json", "tokenizer_config.json", "tokenizer.json", "vocab.json", "merges.txt"):
        path = MODEL / name
        assert not path.is_symlink() and path.stat().st_size == metadata[name]["bytes"]
        assert digest(path) == metadata[name]["sha256"]
        checked[name] = metadata[name]
    config = json.loads((MODEL / "config.json").read_text())
    tokenizer_config = json.loads((MODEL / "tokenizer_config.json").read_text())
    assert not (MODEL / "chat_template.jinja").exists()
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True, trust_remote_code=False)
    assert "torch" not in sys.modules and tokenizer.chat_template == tokenizer_config["chat_template"]
    prompt = PROMPT.read_text()
    schema = json.loads(SCHEMA.read_text())
    from neurobuild.infrastructure.local_model import LocalRequirementClient
    from neurobuild.application.requirement_generation import GenerationContract, parse_generated_requirement
    from neurobuild.domain.errors import DomainError
    from jsonschema import Draft202012Validator
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    client = LocalRequirementClient("http://127.0.0.1:8003", "neurobuild-local", generation_contract="3.0",
                                    prompt_path=PROMPT, schema_path=SCHEMA, max_tokens=OUTPUT_CAP)
    assert client.generation_contract is GenerationContract.FACTS
    capture = Capture()
    client._opener = capture

    def captured_tokens(source, context):
        client.complete(source, axis_convention=context)
        payload = capture.payload
        assert payload["guided_json"] == schema and payload["guided_decoding_backend"] == "xgrammar:no-fallback"
        assert payload["max_tokens"] == OUTPUT_CAP and payload["temperature"] == 0 and payload["seed"] == 42
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        assert payload["messages"] == [{"role": "system", "content": prompt}, {"role": "user", "content":
            json.dumps({"source_text": source, "axis_convention": context}, ensure_ascii=False)}]
        assert "structured_outputs" not in payload
        return len(tokenizer.apply_chat_template(payload["messages"], tokenize=True,
            add_generation_prompt=True, enable_thinking=False))

    splits = {}
    for name, relative, expected_count in (
        ("development", "evaluations/requirement_hardening_v1_development.jsonl", 40),
        ("exposed_previous_holdout_regression", "evaluations/requirement_hardening_v1_holdout.jsonl", 80),
        ("v2_input_length_only", "evaluations/requirement_hardening_v2_holdout.jsonl", 80),
    ):
        data = (ROOT / relative).read_bytes()
        rows = [json.loads(line) for line in data.splitlines() if line]
        assert len(rows) == expected_count
        lengths = [captured_tokens(row["input"], row["context"].get("axis_convention")) for row in rows]
        assert max(lengths) + OUTPUT_CAP <= CONTEXT
        splits[name] = {"dataset_sha256": sha256(data).hexdigest(), "count": len(rows),
                       "minimum_input_tokens": min(lengths), "maximum_input_tokens": max(lengths),
                       "max_input_plus_output": max(lengths) + OUTPUT_CAP,
                       "remaining_context": CONTEXT - max(lengths) - OUTPUT_CAP,
                       "scope": "INPUT_LENGTH_ONLY; no input, gold, case IDs, or model outputs disclosed"}
    assert "torch" not in sys.modules
    template_text = tokenizer.apply_chat_template(capture.payload["messages"], tokenize=False,
        add_generation_prompt=True, enable_thinking=False)
    assert template_text.rsplit("<|im_start|>assistant\n", 1)[1] == "<think>\n\n</think>\n\n"

    inputs = [json.loads(line.removeprefix("입력: ")) for line in prompt.splitlines() if line.startswith("입력: ")]
    examples = [json.loads(line.removeprefix("출력: ")) for line in prompt.splitlines() if line.startswith("출력: ")]
    assert len(inputs) == len(examples) == 2
    fixtures = [(f"prompt_example_{i + 1}", inp["source_text"], obj, True, True)
                for i, (inp, obj) in enumerate(zip(inputs, examples))]
    source = "검토용 책상을 X축 +7cm, Y축 -9mm 옮겨줘."
    ready = {"schema_version": "3.0", "facts": {
        "intent": "CURRENT_MOVE", "condition": "NONE", "condition_quote": None,
        "target_class": "FURNITURE", "target_count": "ONE", "motion": "ONE_RELATIVE_XY_VECTOR",
        "axis_completeness": "EXPLICIT", "authority": "NONE", "authority_quote": None,
        "selection_scope_quote": None, "selection_exclusion_quote": None},
        "target_selection_quote": "검토용 책상", "current_instruction_quote": source,
        "dx_evidence": "X축 +7cm", "dy_evidence": "Y축 -9mm", "reason": None, "decision": "READY"}
    fixtures.append(("ready_xy", source, ready, True, True))
    for decision in ("CLARIFICATION", "UNSUPPORTED"):
        obj = dict(ready, decision=decision, current_instruction_quote=None, dx_evidence=None,
                   dy_evidence=None, reason="검토용 fixture: 모델 label을 코드가 승격하지 않습니다.")
        fixtures.append(("nonready_not_promoted_" + decision, source, obj, True, True))
        fixtures.append(("nonready_bad_instruction_" + decision, source, dict(obj, current_instruction_quote=source), False, False))
    for name, obj in (
        ("root_version_only", {"schema_version": "3.0"}),
        ("wrong_version", dict(ready, schema_version="2.0")),
        ("extra_approval", dict(ready, approval=True)),
        ("ready_null_axes", dict(ready, dx_evidence=None, dy_evidence=None)),
        ("ready_reason", dict(ready, reason="추가 설명")),
        ("missing_final_decision", {k: v for k, v in ready.items() if k != "decision"}),
        ("facts_extra_reasoning", dict(ready, facts=dict(ready["facts"], reasoning="추가 서술"))),
        ("unknown_fact_enum", dict(ready, facts=dict(ready["facts"], intent="OTHER"))),
    ):
        fixtures.append((name, source, obj, False, False))
    for name, change in (
        ("ready_condition", {"condition": "UNRESOLVED", "condition_quote": "검토용"}),
        ("ready_multiple_targets", {"target_count": "MULTIPLE"}),
        ("ready_sequential_motion", {"motion": "SEQUENTIAL_OR_MULTI_ACTION"}),
        ("ready_authority_bypass", {"authority": "CURRENT_BYPASS_OR_OVERWRITE", "authority_quote": "검토용"}),
    ):
        fixtures.append((name, source, dict(ready, facts=dict(ready["facts"], **change)), False, False))
    for name, change in (
        ("authority_none_nonnull_quote", {"authority_quote": "검토용"}),
        ("history_missing_quote", {"authority": "HISTORICAL_OR_QUOTED_ONLY"}),
        ("scope_missing_in_target", {"selection_scope_quote": "옮겨줘"}),
        ("quote_not_in_source", {"selection_exclusion_quote": "원문에 없는 제외"}),
    ):
        fixtures.append((name, source, dict(ready, facts=dict(ready["facts"], **change)), True, False))
    unsigned_source = "검토용 책상을 X축 7cm 옮겨줘."
    unsigned = dict(ready, current_instruction_quote=unsigned_source, dx_evidence="X축 7cm", dy_evidence=None)
    fixtures.append(("facts_pass_quote_parser_rejects_unsigned", unsigned_source, unsigned, True, False))

    # Only this section imports Torch, through CPU xgrammar; masked GPU remains uninitialized.
    import xgrammar as xgr
    import torch
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    util_path = ROOT / ".conda-vllm/lib/python3.12/site-packages/vllm/model_executor/guided_decoding/utils.py"
    spec = importlib.util.spec_from_file_location("nb_gen3_guided_utils", util_path)
    utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils)
    assert not utils.has_xgrammar_unsupported_json_features(schema)
    compiler = xgr.GrammarCompiler(xgr.TokenizerInfo.from_huggingface(tokenizer, vocab_size=config["vocab_size"]), max_threads=2)
    started = time.monotonic()
    grammar = compiler.compile_json_schema(schema, any_whitespace=True)
    compile_seconds = time.monotonic() - started
    results = []
    for name, source_text, obj, expected_schema, expected_parse in fixtures:
        assert validator.is_valid(obj) == expected_schema
        rendered = text(obj)
        matcher = xgr.GrammarMatcher(grammar)
        accepts = all(matcher.accept_token(token) for token in tokenizer.encode(rendered, add_special_tokens=False))
        accepts = accepts and matcher.accept_token(tokenizer.eos_token_id)
        assert accepts == expected_schema
        error = None
        try:
            requirement = parse_generated_requirement(rendered, generation_contract=GenerationContract.FACTS,
                source_text=source_text, requirement_id=uuid4(), project_id=uuid4(), base_revision_id=uuid4(),
                axis_convention="project_xy")
        except DomainError as exc:
            parsed = False
            error = exc.code
        else:
            parsed = True
            assert requirement.status.value == obj["decision"]
        assert parsed == expected_parse
        results.append({"fixture": name, "json_schema_valid": expected_schema,
                        "grammar_token_eos_accepted": accepts, "full_adapter_parser_accepted": parsed,
                        "error_code": error})
    assert not torch.cuda.is_initialized()
    assert all(digest(ROOT / relative) == value for relative, value in source_hashes.items())
    proof = {"kind": "CPU_ONLY_GENERATION3_32B_PREFLIGHT", "status": "PASS", "model_id": manifest["model_id"],
             "model_revision": REVISION, "sha256": source_hashes, "legacy_baseline_sha256": digest(BASELINE),
             "legacy_v2_function_ast_unchanged": actual_ast, "canonical_parser_byte_unchanged": True,
             "metadata_verified": checked, "weight_payloads_read": False, "tokenizer_class": type(tokenizer).__name__,
             "chat_template_sha256": sha256(tokenizer.chat_template.encode()).hexdigest(),
             "chat_template_origin": "tokenizer_config.json; no separate jinja", "enable_thinking": False,
             "empty_think_prefix_is_template_not_model_reasoning": True,
             "actual_client_fake_capture_count": capture.calls, "context_limit": CONTEXT, "output_cap": OUTPUT_CAP,
             "system_prompt_tokens": len(tokenizer.encode(prompt, add_special_tokens=False)), "splits": splits,
             "grammar": {"xgrammar": importlib.metadata.version("xgrammar"), "compile_seconds": compile_seconds,
                         "vllm_unsupported_features": False, "fixtures": results, "prompt_examples": len(examples)},
             "transformers": importlib.metadata.version("transformers"), "torch": importlib.metadata.version("torch"),
             "torch_imported_during_tokenization": False, "torch_imported_for_cpu_grammar": True,
             "cuda_initialized": False, "cuda_visible_devices": "", "model_calls": 0, "network_calls": 0, "gpu_queries": 0,
             "limitations": "Structural/backend fixture checks and CPU lengths are not semantic quality or actual GPU grammar enforcement. V2 length-only text/gold is not published by this proof; previous root exposure remains disclosed elsewhere."}
    out = ROOT / "var/research" / ("generation3-32b-preflight-" + uuid4().hex + ".json")
    with out.open("x") as handle:
        json.dump(proof, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"proof_path": str(out.relative_to(ROOT)), "proof_sha256": digest(out),
        "source_hashes": source_hashes, "splits": splits, "fixtures": len(results), "compile_seconds": compile_seconds,
        "cuda_initialized": False, "model_calls": 0}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never print source/gold, fixture content, tokenizer spans, or traceback.
        print(json.dumps({"status": "FAILED", "code": "GENERATION3_CPU_PREFLIGHT_FAILED"}))
        raise SystemExit(1) from None
