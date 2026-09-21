"""Offline CPU proof for the bounded 32B thinking / generation2 comparison.

Run this archived helper in place from the repository with masked GPUs:
CUDA_VISIBLE_DEVICES='' USE_TORCH=0 USE_TF=0 HF_HUB_OFFLINE=1 \
TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
  .conda-vllm/bin/python -B PATH/verify_cpu_preflight.py

The only generated artifact is exclusive cpu_preflight.json in this directory.
V2 source is used only for aggregate token lengths, never displayed. No model
output, input body, raw envelope or reasoning text is written or printed.
"""

import __future__
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
from types import SimpleNamespace
from uuid import uuid4

ARCHIVE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
PROMPT = ROOT / "prompts/requirement_generation_v2_thinking_v1.txt"
ORIGINAL = ROOT / "prompts/requirement_generation_v2_v2.txt"
SCHEMA = ROOT / "schemas/requirement_generation_v2_decision_branches.schema.json"
REVISION = "0499c3ac83fdef8810b907a23894ba91e95eddd8"
MODEL = ROOT / "var/models/Qwen--Qwen3-32B-AWQ" / REVISION
SITE = ROOT / ".conda-vllm/lib/python3.12/site-packages"
BASELINE_COMMIT = "0fd60350b6e9df6538e5cf3d1ee1b13fa949fccc"
CAP = 1024
CONTEXT = 4096
SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
            "presence_penalty": 1.5, "frequency_penalty": 0.0,
            "repetition_penalty": 1.0, "seed": 42}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def deny_network(*_args, **_kwargs):
    raise AssertionError("NETWORK_DISABLED_FOR_CPU_PROOF")


class Response(io.BytesIO):
    status = 200

    def __init__(self, raw):
        super().__init__(raw)
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"
        self.headers["Content-Length"] = str(len(raw))


class Capture:
    def __init__(self):
        self.calls = 0
        self.payload = None
        self.marker = uuid4().hex  # Opaque transport fixture, never actual reasoning.
        self.finish_reason = "stop"
        self.content = "{}"

    def open(self, request, *, timeout):
        assert timeout == 120
        self.calls += 1
        self.payload = json.loads(request.data)
        # The fixture envelope is only transient in-memory transport input.
        return Response(json.dumps({"model": "neurobuild-local", "choices": [{"index": 0,
            "finish_reason": self.finish_reason, "message": {"role": "assistant",
                "content": self.content, "reasoning_content": self.marker, "reasoning": self.marker}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3,
                      "completion_tokens_details": {"reasoning_tokens": 1}}}).encode())


def extracted_method(path, class_name, method_name):
    """Execute a small exact installed method without importing GPU vLLM."""
    tree = ast.parse(path.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == method_name)
    assert not method.decorator_list
    code = compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec",
                   flags=__future__.annotations.compiler_flag)
    namespace = {}
    exec(code, namespace)
    return namespace[method_name], sha256(ast.dump(method, include_attributes=False).encode()).hexdigest()


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert os.environ.get("USE_TORCH") == "0" and "torch" not in sys.modules
    assert os.environ.get("HF_HUB_OFFLINE") == os.environ.get("TRANSFORMERS_OFFLINE") == "1"
    socket.create_connection = deny_network
    socket.getaddrinfo = deny_network
    baseline = json.loads((ARCHIVE / "baseline.json").read_text())
    assert baseline["commit"] == BASELINE_COMMIT
    for name, expected in baseline["source_hashes"].items():
        assert digest(ROOT / name) == expected
    assert baseline["source_hashes"]["src/neurobuild/application/requirements.py"] == (
        "a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a")
    source_hashes = dict(baseline["source_hashes"])
    source_hashes[str(PROMPT.relative_to(ROOT))] = digest(PROMPT)
    source_hashes["docs/requirement_thinking_control_plan.md"] = digest(ROOT / "docs/requirement_thinking_control_plan.md")
    original = ORIGINAL.read_bytes()
    prompt_bytes = PROMPT.read_bytes()
    replacements = (
        ("지정 schema의 JSON 객체 하나만 출력한다.", "최종 content에는 지정 schema의 JSON 객체 하나만 출력한다."),
        ("설명, Markdown, 추론 내용, <think>는 출력하지 않는다.",
         "최종 content에 설명, Markdown, 추론 내용, <think>는 출력하지 않는다."),
    )
    expected_prompt = original
    inverse = prompt_bytes
    for old, new in replacements:
        assert original.count(old.encode()) == prompt_bytes.count(new.encode()) == 1
        expected_prompt = expected_prompt.replace(old.encode(), new.encode(), 1)
        inverse = inverse.replace(new.encode(), old.encode(), 1)
    assert expected_prompt == prompt_bytes and inverse == original
    assert original.split(b"\n", 1)[1] == prompt_bytes.split(b"\n", 1)[1]

    manifest_path = ROOT / "runtime/models/qwen3-32b-awq.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["model_id"] == "Qwen/Qwen3-32B-AWQ" and manifest["revision"] == REVISION
    assert digest(MODEL / "neurobuild-manifest.json") == digest(manifest_path)
    entries = {entry["name"]: entry for entry in manifest["files"]}
    metadata = {}
    for name in ("config.json", "tokenizer_config.json", "tokenizer.json", "vocab.json", "merges.txt"):
        path = MODEL / name
        assert not path.is_symlink() and path.stat().st_size == entries[name]["bytes"]
        assert digest(path) == entries[name]["sha256"]
        metadata[name] = entries[name]
    assert not (MODEL / "chat_template.jinja").exists()
    config = json.loads((MODEL / "config.json").read_text())
    tokenizer_config = json.loads((MODEL / "tokenizer_config.json").read_text())
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True, trust_remote_code=False)
    assert "torch" not in sys.modules
    assert tokenizer.chat_template == tokenizer_config["chat_template"]
    template_hash = sha256(tokenizer.chat_template.encode()).hexdigest()
    assert template_hash == "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8"

    from neurobuild.infrastructure.local_model import LocalRequirementClient, SamplingProfile
    from neurobuild.application.requirement_generation import GenerationContract, parse_generated_requirement
    from neurobuild.domain.errors import DomainError
    from jsonschema import Draft202012Validator
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    prompt = prompt_bytes.decode()
    client = LocalRequirementClient("http://127.0.0.1:8003", "neurobuild-local", timeout=120,
        max_tokens=CAP, prompt_path=PROMPT, schema_path=SCHEMA, generation_contract="2.0",
        sampling_profile=SamplingProfile.QWEN3_THINKING_AWQ)
    assert client.generation_contract is GenerationContract.QUOTES and client.enable_thinking is True
    assert client.sampling_parameters == SAMPLING
    capture = Capture()
    client._opener = capture

    def tokens_for(source, context):
        completion = client.complete(source, axis_convention=context)
        assert completion.content == "{}" and capture.marker not in repr(completion)
        assert not hasattr(completion, "reasoning") and not hasattr(completion, "reasoning_content")
        assert completion.usage == {"prompt_tokens": 1, "completion_tokens": 2,
                                    "total_tokens": 3, "reasoning_tokens": 1}
        payload = capture.payload
        expected = {"model": "neurobuild-local", "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps({"source_text": source, "axis_convention": context}, ensure_ascii=False)}],
            **SAMPLING, "max_tokens": CAP, "stream": False, "chat_template_kwargs": {"enable_thinking": True},
            "guided_json": schema, "guided_decoding_backend": "xgrammar:no-fallback"}
        assert payload == expected
        rendered = tokenizer.apply_chat_template(payload["messages"], tokenize=False,
            add_generation_prompt=True, enable_thinking=True)
        assert rendered.endswith("<|im_start|>assistant\n")
        assert not rendered.endswith("<think>\n\n</think>\n\n")
        return len(tokenizer.apply_chat_template(payload["messages"], tokenize=True,
            add_generation_prompt=True, enable_thinking=True))

    lengths = {}
    for name, relative, count in (
        ("development", "evaluations/requirement_hardening_v1_development.jsonl", 40),
        ("exposed_previous_holdout_regression", "evaluations/requirement_hardening_v1_holdout.jsonl", 80),
        ("v2_input_length_only", "evaluations/requirement_hardening_v2_holdout.jsonl", 80),
    ):
        raw = (ROOT / relative).read_bytes()
        rows = [json.loads(line) for line in raw.splitlines() if line]
        assert len(rows) == count
        # Gold is not sent or tokenized. No case text/ID/per-case length is saved.
        counts = [tokens_for(row["input"], row["context"].get("axis_convention")) for row in rows]
        assert max(counts) + CAP <= CONTEXT
        lengths[name] = {"dataset_sha256": sha256(raw).hexdigest(), "count": count,
            "min_input_tokens": min(counts), "max_input_tokens": max(counts),
            "max_input_plus_output": max(counts) + CAP, "context_slack_tokens": CONTEXT - max(counts) - CAP,
            "scope": "INPUT_LENGTH_ONLY; no input/gold/body/case ID/per-case lengths disclosed"}
    assert capture.calls == 200 and "torch" not in sys.modules
    # Separate synthetic final-content boundaries; still no actual server calls.
    transport_rejections = []
    for label, content, finish, expected_error in (
        ("truncated", "{}", "length", "LOCAL_MODEL_TRUNCATED"),
        ("missing_final_content", None, "stop", "LOCAL_MODEL_RESPONSE_INVALID"),
        ("reasoning_in_final_content", "<think></think>{}", "stop", "LOCAL_MODEL_REASONING_CONTENT"),
    ):
        capture.content, capture.finish_reason = content, finish
        try:
            client.complete("합성 transport 검사", axis_convention="project_xy")
        except DomainError as exc:
            assert exc.code == expected_error and capture.marker not in str(exc)
            transport_rejections.append({"fixture": label, "error_code": exc.code})
        else:
            raise AssertionError("transport_boundary_not_rejected")

    inputs = [json.loads(line[len("입력: "):]) for line in prompt.splitlines() if line.startswith("입력: ")]
    examples = [json.loads(line[len("출력: "):]) for line in prompt.splitlines() if line.startswith("출력: ")]
    assert len(inputs) == len(examples) == 7
    # xgrammar uses Torch on CPU; the explicit mask remains and CUDA stays uninitialized.
    import xgrammar as xgr
    import torch
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    utils_path = SITE / "vllm/model_executor/guided_decoding/utils.py"
    spec = importlib.util.spec_from_file_location("thinking_32b_guided_utils", utils_path)
    utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils)
    assert not utils.has_xgrammar_unsupported_json_features(schema)
    compiler = xgr.GrammarCompiler(xgr.TokenizerInfo.from_huggingface(tokenizer, vocab_size=config["vocab_size"]), max_threads=2)
    started = time.monotonic()
    grammar = compiler.compile_json_schema(schema, any_whitespace=True)
    compile_seconds = time.monotonic() - started
    example_results = []
    for number, (inp, example) in enumerate(zip(inputs, examples), 1):
        assert validator.is_valid(example)
        rendered = json.dumps(example, ensure_ascii=False)
        matcher = xgr.GrammarMatcher(grammar)
        assert all(matcher.accept_token(token) for token in tokenizer.encode(rendered, add_special_tokens=False))
        assert matcher.accept_token(tokenizer.eos_token_id)
        requirement = parse_generated_requirement(rendered, generation_contract=GenerationContract.QUOTES,
            source_text=inp["source_text"], requirement_id=uuid4(), project_id=uuid4(), base_revision_id=uuid4(),
            axis_convention=inp["axis_convention"])
        assert requirement.status.value == example["decision"]
        example_results.append({"example_number": number, "json_schema_valid": True,
            "grammar_tokens_and_eos_accepted": True, "quote_adapter_canonical_parser_accepted": True})

    # Installed V0 reasoning/grammar integration: source hashes and tiny exact-method CPU probes.
    names = ("engine/arg_utils.py", "engine/async_llm_engine.py", "engine/llm_engine.py",
        "model_executor/guided_decoding/__init__.py", "model_executor/guided_decoding/xgrammar_decoding.py",
        "reasoning/__init__.py", "reasoning/deepseek_r1_reasoning_parser.py", "entrypoints/openai/serving_chat.py")
    installed_hashes = {name: digest(SITE / "vllm" / name) for name in names}
    parser_path = SITE / "vllm/reasoning/deepseek_r1_reasoning_parser.py"
    is_end, end_hash = extracted_method(parser_path, "DeepSeekR1ReasoningParser", "is_reasoning_end")
    extract, extract_hash = extracted_method(parser_path, "DeepSeekR1ReasoningParser", "extract_reasoning_content")
    processor_path = SITE / "vllm/model_executor/guided_decoding/xgrammar_decoding.py"
    process, process_hash = extracted_method(processor_path, "XGrammarLogitsProcessor", "__call__")
    end_id = tokenizer.convert_tokens_to_ids("</think>")
    start_id = tokenizer.convert_tokens_to_ids("<think>")
    assert end_id != start_id and end_id != tokenizer.unk_token_id
    reasoner = SimpleNamespace(start_token="<think>", end_token="</think>", end_token_id=end_id)
    reasoner.is_reasoning_end = lambda ids: is_end(reasoner, ids)
    opaque = uuid4().hex
    for model_text, expected_final in (("<think>" + opaque + "</think>{}", "{}"),
                                       (opaque + "</think>{}", "{}"), (opaque, None), (opaque + "</think>", None)):
        transient_reasoning, final = extract(reasoner, model_text, None)
        assert transient_reasoning == opaque and final == expected_final
    del transient_reasoning, model_text, opaque
    assert is_end(reasoner, [start_id]) is False and is_end(reasoner, [end_id]) is True
    entered = []
    class GrammarEntered(Exception):
        pass
    def enter():
        entered.append(True)
        raise GrammarEntered()
    processor = SimpleNamespace(reasoner=reasoner, ctx=None, _ensure_ctx=enter)
    scores = object()
    assert process(processor, [start_id], scores) is scores and not entered
    try:
        process(processor, [end_id], scores)
    except GrammarEntered:
        pass
    else:
        raise AssertionError("reasoning_end_did_not_enter_grammar")
    assert entered == [True]
    historical = []
    for relative in ("evaluations/results/phase5x/development-v6-thinking-diagnostic",
                     "evaluations/results/phase5x/development-v7-thinking-diagnostic"):
        directory = ROOT / relative
        old_manifest = json.loads((directory / "manifest.json").read_text())
        old_result = json.loads((directory / "results.json").read_text())
        assert old_manifest["model_id"] == "Qwen/Qwen3-14B-AWQ"
        assert old_manifest["runtime"]["vllm"] == "0.8.5+cu118"
        assert old_manifest["runtime"]["reasoning_parser"] == "deepseek_r1"
        assert old_manifest["protocol"]["enable_thinking"] is True
        assert old_manifest["protocol"]["guided_decoding_backend"] == "xgrammar:no-fallback"
        historical.append({"archive": relative, "manifest_sha256": digest(directory / "manifest.json"),
            "results_sha256": digest(directory / "results.json"), "run_id": old_result["run_id"],
            "model_id": old_manifest["model_id"], "runtime": old_manifest["runtime"],
            "trials": len(old_result["trials"]), "schema_valid": old_result["metrics"]["schema_valid"],
            "parser_accepted": old_result["metrics"]["parser_accepted"],
            "scope": "Historical 14B protocol execution only; not 32B quality or completion-budget proof"})
        del old_result
    assert not torch.cuda.is_initialized()
    assert all(digest(ROOT / name) == value for name, value in source_hashes.items())
    assert all(digest(SITE / "vllm" / name) == value for name, value in installed_hashes.items())
    proof = {
        "status": "PASS", "kind": "CPU_ONLY_32B_THINKING_PREFLIGHT",
        "model_id": manifest["model_id"], "model_revision": REVISION, "generation_contract": "2.0",
        "sampling_profile": "qwen3_thinking_awq", "sampling_request_parameters": SAMPLING,
        "enable_thinking": True, "max_tokens": CAP, "timeout_seconds": 120, "context_limit": CONTEXT,
        "structured_output_protocol": "legacy_guided_json", "guided_decoding_backend": "xgrammar:no-fallback",
        "required_runtime": {"VLLM_USE_V1": "0", "enable_reasoning": True, "reasoning_parser": "deepseek_r1"},
        "source_hashes": source_hashes, "baseline_commit": BASELINE_COMMIT,
        "baseline_sha256": digest(ARCHIVE / "baseline.json"), "baseline_source_hashes": baseline["source_hashes"],
        "source_unchanged_vs_baseline": True, "prompt_inverse_byte_identity": True,
        "prompt_identity_evidence": {"replacement_count": 2, "changed_lines": [1],
            "all_lines_after_first_byte_identical": True,
            "old_sha256": digest(ORIGINAL), "new_sha256": digest(PROMPT),
            "scope": "Only two output-format clauses scoped to final content; no rules or example changes"},
        "tokenizer_metadata": metadata, "chat_template_sha256": template_hash,
        "thinking_template_assistant_suffix": "<|im_start|>assistant\\n",
        "system_prompt_tokens": len(tokenizer.encode(prompt, add_special_tokens=False)),
        "input_lengths": lengths, "fake_http_capture_count": 200, "additional_transport_boundary_calls": 3,
        "payload_exact_match": True, "reasoning_fields_discarded_in_200_fake_completions": True,
        "transport_rejections": transport_rejections, "grammar_compile_seconds": compile_seconds,
        "xgrammar_unsupported_features": False, "examples_validated": 7, "examples": example_results,
        "runtime_compatibility": {"installed_vllm_source_hashes": installed_hashes,
            "extracted_exact_method_ast_sha256": {"is_reasoning_end": end_hash,
                "extract_reasoning_content": extract_hash, "XGrammarLogitsProcessor.__call__": process_hash},
            "cpu_end_marker_controls": 2, "cpu_content_split_controls": 4, "cpu_grammar_gate_controls": 2,
            "findings": ["V0 config passes deepseek_r1 into the guided decoding builder",
                "Installed xgrammar processor leaves scores unchanged before reasoning end, enters grammar after end",
                "Installed parser returns no final content when end marker/final answer is missing",
                "OpenAI serving splits reasoning_content and final content; client returns only final content"],
            "historical_14b_runs": historical,
            "limitation": "Static source plus isolated CPU method probes and earlier 14B execution; no 32B thinking model call"},
        "versions": {name: importlib.metadata.version(name) for name in ("transformers", "xgrammar", "torch", "jsonschema", "vllm")},
        "helper_sha256": digest(Path(__file__)), "cuda_initialized": False,
        "real_http_calls": 0, "model_calls": 0, "gpu_calls": 0, "weight_payload_reads": 0,
        "limitations": ["1024 is the combined reasoning and final-answer budget; context fit does not ensure completion",
            "Thinking, sampling, prompt output scope and output cap differ together from prior greedy control",
            "Synthetic gold is not human verified; root v2 input exposure remains disclosed; v2 used here for length only",
            "RTX5090 actual execution and 32B thinking quality remain unverified"],
    }
    target = ARCHIVE / "cpu_preflight.json"
    with target.open("x") as stream:
        json.dump(proof, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "proof": str(target.relative_to(ROOT)), "proof_sha256": digest(target),
        "prompt_sha256": digest(PROMPT), "input_lengths": lengths, "examples": 7,
        "grammar_compile_seconds": compile_seconds, "cuda_initialized": False}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never print assertion operands, parsed inputs, raw envelopes or tracebacks.
        print(json.dumps({"status": "FAIL", "error_type": type(exc).__name__}), file=sys.stderr)
        raise SystemExit(1)
