"""Independent fake-only legacy wire/rawREADY probes; no datasets/network/GPU.

Run after root declares the client/harness implementation ready. Uses the
16d67895 pre-generation3 checkpoint as the 1.0/2.0 payload baseline.
"""
import ast
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import types
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "var/research/generation3_legacy_baseline.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def deny(*args, **kwargs):
    raise RuntimeError("NETWORK_FORBIDDEN")


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    socket.create_connection = deny
    socket.getaddrinfo = deny
    baseline = json.loads(BASELINE.read_text())
    files = ["src/neurobuild/infrastructure/local_model.py", "scripts/evaluate_requirements.py",
             "src/neurobuild/application/requirements.py", "src/neurobuild/application/requirement_generation.py",
             "src/neurobuild/application/requirement_facts.py", "schemas/requirement_generation_v3.schema.json"]
    hashes = {name: digest(ROOT / name) for name in files}
    assert hashes["src/neurobuild/application/requirements.py"] == baseline["canonical_parser_sha256"]
    nodes = {node.name: node for node in ast.parse((ROOT / "src/neurobuild/application/requirement_generation.py").read_text()).body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert {name: sha256(ast.dump(nodes[name], include_attributes=False).encode()).hexdigest()
            for name in baseline["generation2_function_ast_sha256"]} == baseline["generation2_function_ast_sha256"]
    from neurobuild.infrastructure import local_model as current
    from neurobuild.application.requirement_generation import GenerationContract
    from neurobuild.domain.errors import DomainError
    from jsonschema import Draft202012Validator
    fixture_transport = load_file("nb_generation3_cpu_fixture", ROOT / "var/research/verify_generation3_32b_preflight.py")
    old_source = subprocess.check_output(["git", "show", baseline["commit"] + ":src/neurobuild/infrastructure/local_model.py"], cwd=ROOT)
    old = types.ModuleType("nb_pre_generation3_client")
    old.__file__ = str(ROOT / "src/neurobuild/infrastructure/local_model.py")
    sys.modules[old.__name__] = old
    exec(compile(old_source, old.__file__, "exec"), old.__dict__)
    pairs = []
    for contract, explicit in (("1.0", False), ("2.0", False), ("2.0", True)):
        for protocol in ("legacy_guided_json", "structured_outputs"):
            kwargs = {"generation_contract": contract, "protocol": protocol}
            if explicit:
                kwargs.update(prompt_path=ROOT / "prompts/requirement_generation_v2_v2.txt",
                              schema_path=ROOT / "schemas/requirement_generation_v2_decision_branches.schema.json")
            requests = []
            for cls in (old.LocalRequirementClient, current.LocalRequirementClient):
                client = cls("http://127.0.0.1:8003", "neurobuild-local", **kwargs)
                capture = fixture_transport.Capture()
                # Preserve exact serialized bytes as well as semantic payload.
                original_open = capture.open
                def open_request(request, *, timeout, original_open=original_open):
                    requests.append(request.data)
                    return original_open(request, timeout=timeout)
                capture.open = open_request
                client._opener = capture
                client.complete("검증용 작업대를 X축 +7mm 옮겨줘.", axis_convention="project_xy")
                assert capture.calls == 1
            assert requests[0] == requests[1]
            pairs.append({"contract": contract, "protocol": protocol, "explicit_branch_prompt_schema": explicit,
                          "payload_sha256": sha256(requests[1]).hexdigest(), "byte_equal": True})
    harness = load_file("nb_generation3_harness_review", ROOT / "scripts/evaluate_requirements.py")
    schema = json.loads((ROOT / "schemas/requirement_generation_v3.schema.json").read_text())
    validator = Draft202012Validator(schema)
    source = "검증용 작업대를 X축 +7mm 옮기되 통로가 확보되어 있을 때만 실행해."
    base = {"schema_version": "3.0", "facts": {
        "intent": "CURRENT_MOVE", "condition": "NONE", "condition_quote": None,
        "target_class": "FURNITURE", "target_count": "ONE", "motion": "ONE_RELATIVE_XY_VECTOR",
        "axis_completeness": "EXPLICIT", "authority": "NONE", "authority_quote": None,
        "selection_scope_quote": None, "selection_exclusion_quote": None}, "decision": "READY",
        "target_selection_quote": "검증용 작업대", "current_instruction_quote": source,
        "dx_evidence": "X축 +7mm", "dy_evidence": None, "reason": None}
    case = {"id": "LOCAL-PROBE", "category": "independent_synthetic_fault_probe", "input": source,
            "context": {"axis_convention": "project_xy"},
            "gold": {"decision": "clarify", "target_text": "검증용 작업대"}}

    class FakeClient:
        generation_contract = GenerationContract.FACTS
        model = "neurobuild-local"
        def __init__(self, obj):
            self.obj = obj
        def complete(self, *args, **kwargs):
            return current.Completion(json.dumps(self.obj, ensure_ascii=False), None, 0.1, self.model)

    results = []
    def check(name, obj, *, use_case=None, patch_target=None, error=None, expected=None):
        target_case = use_case or case
        if patch_target:
            with patch.object(harness, patch_target, side_effect=error):
                row = harness.evaluate_trial(FakeClient(obj), target_case, validator, 1, run_id="gen3-review")
        else:
            row = harness.evaluate_trial(FakeClient(obj), target_case, validator, 1, run_id="gen3-review")
        assert row["raw_model_decision"] == "READY" and row["model_ready_observed"] is True
        metrics = harness.summarize([row])
        assert metrics["critical_fp_model_ready"]["numerator"] == metrics["critical_fp_model_ready"]["denominator"] == 1
        assert metrics["json_parse_valid"]["denominator"] == 1
        if expected:
            for field, value in expected.items():
                assert row[field] == value
        assert "PRIVATE_SENTINEL" not in json.dumps(row)
        results.append({"probe": name, "raw_ready_preserved": True, "raw_fp_numerator": 1, "raw_fp_denominator": 1,
                        "generation_schema_valid": row["generation_schema_valid"],
                        "facts_projection_accepted": row["facts_projection_accepted"],
                        "adapter_accepted": row["adapter_accepted"], "legacy_schema_valid": row["legacy_schema_valid"],
                        "parser_accepted": row["parser_accepted"], "error_code": row["error_code"],
                        "unsafe_accepted_numerator": metrics["unsafe_accepted_ready_total"]["numerator"]})
        return row

    # Deliberately omitted condition demonstrates the known entailment limit,
    # and proves it is counted as unsafe rather than quietly made correct.
    check("known_omitted_condition_counted_unsafe", base, expected={"parser_accepted": True, "semantic_rubric_correct": False})
    obj = deepcopy(base); obj["facts"].update(condition="UNRESOLVED", condition_quote="통로가 확보되어 있을 때만")
    check("generation_schema_rejection", obj, expected={"generation_schema_valid": False, "generation_output": None, "parser_accepted": False})
    obj = deepcopy(base); obj["facts"]["selection_scope_quote"] = "통로"
    check("facts_scope_rejection", obj, expected={"generation_schema_valid": True, "facts_projection_accepted": False, "parser_accepted": False})
    obj = deepcopy(base); obj["facts"]["authority_quote"] = "실행해"
    check("facts_null_consistency_rejection", obj, expected={"generation_schema_valid": True, "facts_projection_accepted": False, "parser_accepted": False})
    unsigned_source = "검증용 작업대를 X축 7mm 옮겨줘."
    obj = deepcopy(base); obj.update(current_instruction_quote=unsigned_source, dx_evidence="X축 7mm")
    check("projection_then_quote_parser_rejection", obj, use_case=dict(case, input=unsigned_source),
          expected={"generation_schema_valid": True, "facts_projection_accepted": True, "adapter_accepted": False, "parser_accepted": False})
    for name, target, error, facts_ok, adapter_ok in (
        ("facts_domain_error", "adapt_generation_v3", DomainError("INVALID_MODEL_OUTPUT", "PRIVATE_SENTINEL"), False, False),
        ("facts_runtime_error", "adapt_generation_v3", RuntimeError("PRIVATE_SENTINEL"), False, False),
        ("quote_domain_error", "adapt_generation_v2", DomainError("UNGROUNDED_REQUIREMENT", "PRIVATE_SENTINEL"), True, False),
        ("canonical_domain_error", "parse_requirement", DomainError("INVALID_MODEL_OUTPUT", "PRIVATE_SENTINEL"), True, True),
        ("canonical_runtime_error", "parse_requirement", RuntimeError("PRIVATE_SENTINEL"), True, True),
    ):
        check(name, base, patch_target=target, error=error, expected={"facts_projection_accepted": facts_ok,
              "adapter_accepted": adapter_ok, "parser_accepted": False})
    for exception in (KeyboardInterrupt, SystemExit):
        try:
            with patch.object(harness, "adapt_generation_v3", side_effect=exception()):
                harness.evaluate_trial(FakeClient(base), case, validator, 1, run_id="gen3-review")
        except exception:
            pass
        else:
            raise AssertionError("INTERRUPT_SWALLOWED")
    assert all(digest(ROOT / name) == expected for name, expected in hashes.items())
    assert "torch" not in sys.modules
    proof = {"kind": "GENERATION3_INDEPENDENT_FAKE_ONLY_BOUNDARY_REVIEW", "status": "PASS",
             "baseline_commit": baseline["commit"], "source_sha256": hashes,
             "legacy_wire_pairs": pairs, "raw_ready_fault_probes": results,
             "interrupts_propagated": ["KeyboardInterrupt", "SystemExit"],
             "canonical_sha_and_v2_function_ast_unchanged": True,
             "actual_network_calls": 0, "model_calls": 0, "gpu_calls": 0, "datasets_read": 0,
             "scope": "Synthetic fixtures only; omitted-condition acceptance is a documented limitation and deliberately counted as unsafe. No model quality inference."}
    destination = ROOT / "var/research" / ("generation3-boundary-review-" + uuid4().hex + ".json")
    with destination.open("x") as handle:
        json.dump(proof, handle, indent=2); handle.write("\n")
    print(json.dumps({"proof": str(destination.relative_to(ROOT)), "sha256": digest(destination),
                      "wire_pairs": len(pairs), "raw_ready_probes": len(results), "status": "PASS"}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(json.dumps({"status": "FAILED", "code": "GENERATION3_BOUNDARY_PROBE_FAILED"}))
        raise SystemExit(1) from None
