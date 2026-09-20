"""Native evidence/manifest boundaries; no executable, GPU or model calls."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from neurobuild.application.requirement_generation import GenerationContract
from neurobuild.infrastructure.local_model import LocalRequirementClient
from scripts.evaluate_requirements import ROOT, build_manifest, runtime_metadata


def native_metadata():
    # Synthetic identities; these fixtures are not runtime validation evidence.
    return {
        "runtime_kind": "llama_cpp", "profile": "a100",
        "llama_cpp_commit": "a" * 40,
        "binary_sha256": "1" * 64, "source_provenance_sha256": "2" * 64,
        "build_report_sha256": "3" * 64, "gguf_sha256": "b" * 64,
        "gguf_header_sha256": "4" * 64, "chat_template_sha256": "5" * 64,
        "launch_config_sha256": "6" * 64, "startup_report_sha256": "7" * 64,
        "listener_report_sha256": "8" * 64,
        "compiler": "GNU 9.5.0", "cmake": "3.23.5", "cuda": "11.8.89",
        "driver": "535.183.01", "gpu": "NVIDIA A100-PCIE-40GB",
        "gpu_uuid": "GPU-12345678-1234-1234-1234-123456789abc",
        "cuda_architecture": "80-real", "physical_gpu": 3, "logical_gpu": 0,
        "max_model_len": 4096, "max_sequences": 1, "quantization": "Q4_K_M",
        "enable_reasoning": False, "reasoning_parser": "deepseek",
    }


def historical_metadata():
    return {
        "python": "3.12.14", "vllm": "0.8.5+cu118", "torch": "2.6.0+cu118",
        "cuda": "11.8", "transformers": "4.51.3", "xgrammar": "0.1.18",
        "driver": "535.183.01", "gpu": "NVIDIA A100-PCIE-40GB",
        "quantization": "awq", "dtype": "float16", "profile": "a100",
        "physical_gpu": 3, "max_model_len": 4096, "tensor_parallel_size": 1,
        "chat_template_sha256": "c" * 64, "launch_config_sha256": "d" * 64,
    }


class NativeRequirementEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.runtime = self.base / "runtime.json"
        self.weights = self.base / "weights.json"
        self.weight_data = {
            "model_id": "ggml-org/Qwen3.8-27B-GGUF", "revision": "e" * 40,
            "files": [{"name": "Qwen3.8-27B-Q4_K_M.gguf", "bytes": 123, "sha256": "b" * 64}],
        }
        self.weights.write_text(json.dumps(self.weight_data))
        self.write_runtime(native_metadata())
        self.client = LocalRequirementClient(
            "http://127.0.0.1:8003", "synthetic-native",
            generation_contract=GenerationContract.QUOTES,
            prompt_path=ROOT / "prompts/requirement_generation_v2_v2.txt",
            schema_path=ROOT / "schemas/requirement_generation_v2_decision_branches.schema.json",
            protocol="llama_cpp_json_schema", sampling_profile="qwen38_nonthinking_llama_cpp",
        )
        self.kwargs = {
            "dataset": ROOT / "evaluations/requirement_seed.jsonl",
            "prompt": ROOT / "prompts/requirement_generation_v2_v2.txt",
            "schema": ROOT / "schemas/requirement_generation_v2_decision_branches.schema.json",
            "weights": self.weights, "runtime": self.runtime,
            "revision": "e" * 40, "tokenizer_revision": "e" * 40,
            "run_id": "synthetic-native", "warmups": 5, "trials": 3,
        }

    def write_runtime(self, value):
        self.runtime.write_text(json.dumps(value))

    def test_native_manifest_preserves_real_runtime_kind_and_native_wire(self):
        with patch.object(self.client, "complete") as transport:
            manifest = build_manifest(self.client, **self.kwargs)
        transport.assert_not_called()
        self.assertEqual(manifest["runtime"], native_metadata())
        self.assertEqual(manifest["protocol"]["structured_output_protocol"], "llama_cpp_json_schema")
        self.assertEqual(manifest["protocol"]["required_server_structured_backend"], "llama_cpp_gbnf")
        self.assertEqual(manifest["protocol"]["response_format_type"], "json_schema")
        self.assertIsNone(manifest["protocol"]["guided_decoding_backend"])
        self.assertFalse(manifest["protocol"]["enable_thinking"])
        self.assertEqual(manifest["protocol"]["reasoning_parser"], "deepseek")
        self.assertEqual(manifest["protocol"]["sampling_request_parameters"], self.client.sampling_parameters)
        self.assertNotIn("torch", manifest["runtime"])
        self.assertNotIn("vllm", manifest["runtime"])
        self.assertNotIn("xgrammar", manifest["runtime"])
        self.assertIn("not remote attestation", manifest["runtime_identity_evidence"])
        self.assertIsNone(manifest["measurements_not_performed"]["gpu_peak_used_mib"])

    def test_historical_metadata_defaults_and_output_remain_unchanged(self):
        old = historical_metadata()
        self.write_runtime(old)
        self.assertEqual(runtime_metadata(self.runtime), dict(old, enable_reasoning=False, reasoning_parser=None))
        self.assertNotIn("runtime_kind", runtime_metadata(self.runtime))
        old_explicit = dict(old, enable_reasoning=True, reasoning_parser="deepseek_r1")
        self.write_runtime(old_explicit)
        self.assertEqual(runtime_metadata(self.runtime), old_explicit)
        self.write_runtime(dict(old, enable_reasoning=False, reasoning_parser="deepseek"))
        with self.assertRaises(ValueError):
            runtime_metadata(self.runtime)

    def test_native_evidence_requires_all_fields_exact_hashes_and_no_fake_dependencies(self):
        base = native_metadata()
        for missing in base:
            with self.subTest(missing=missing):
                self.write_runtime({key: value for key, value in base.items() if key != missing})
                with self.assertRaises(ValueError):
                    runtime_metadata(self.runtime)
        invalid = (
            {"runtime_kind": "vllm"}, {"runtime_kind": None}, {"llama_cpp_commit": "main"},
            {"binary_sha256": "1" * 63}, {"gguf_header_sha256": "A" * 64},
            {"startup_report_sha256": None}, {"compiler": "GNU\nSECRET"},
            {"torch": "2.6.0"}, {"vllm": "not_applicable"}, {"xgrammar": "none"},
            {"api_key": "SECRET"},
        )
        for changed in invalid:
            with self.subTest(changed=changed):
                self.write_runtime(dict(base, **changed))
                with self.assertRaises(ValueError):
                    runtime_metadata(self.runtime)

    def test_native_profile_cannot_hide_device_context_or_mode_changes(self):
        invalid = (
            {"physical_gpu": 0}, {"physical_gpu": True}, {"logical_gpu": 1},
            {"logical_gpu": False}, {"max_sequences": 2}, {"max_sequences": True},
            {"max_model_len": 2048}, {"max_model_len": 4096.0},
            {"profile": "auto"}, {"profile": []}, {"cuda_architecture": "native"},
            {"cuda_architecture": "120-real"}, {"gpu_uuid": "GPU-unknown"},
            {"quantization": "auto"}, {"enable_reasoning": True}, {"enable_reasoning": 0},
            {"reasoning_parser": None}, {"reasoning_parser": "deepseek_r1"},
        )
        for changed in invalid:
            with self.subTest(changed=changed):
                self.write_runtime(dict(native_metadata(), **changed))
                with self.assertRaises(ValueError):
                    runtime_metadata(self.runtime)

    def test_gguf_digest_and_embedded_tokenizer_bind_to_weight_manifest(self):
        wrong = deepcopy(self.weight_data)
        wrong["files"][0]["sha256"] = "f" * 64
        multiple = deepcopy(self.weight_data)
        multiple["files"].append({"name": "other.gguf", "bytes": 123, "sha256": "b" * 64})
        missing = deepcopy(self.weight_data)
        missing["files"][0]["name"] = "model.safetensors"
        for data in (wrong, multiple, missing):
            with self.subTest(data=data):
                self.weights.write_text(json.dumps(data))
                with patch.object(self.client, "complete") as transport:
                    with self.assertRaises(ValueError):
                        build_manifest(self.client, **self.kwargs)
                transport.assert_not_called()
        self.weights.write_text(json.dumps(self.weight_data))
        with self.assertRaises(ValueError):
            build_manifest(self.client, **dict(self.kwargs, tokenizer_revision="f" * 40))

    def test_metadata_dialect_mismatch_fails_before_inference_in_both_directions(self):
        vllm = LocalRequirementClient(
            "http://127.0.0.1:8003", "synthetic-native", generation_contract=GenerationContract.QUOTES,
            prompt_path=self.kwargs["prompt"], schema_path=self.kwargs["schema"])
        with patch.object(vllm, "complete") as transport:
            with self.assertRaises(ValueError):
                build_manifest(vllm, **self.kwargs)
        transport.assert_not_called()
        self.write_runtime(historical_metadata())
        with patch.object(self.client, "complete") as transport:
            with self.assertRaises(ValueError):
                build_manifest(self.client, **self.kwargs)
        transport.assert_not_called()

    def test_native_greedy_transport_control_is_not_the_declared_candidate_profile(self):
        control = LocalRequirementClient(
            "http://127.0.0.1:8003", "synthetic-native", generation_contract=GenerationContract.QUOTES,
            prompt_path=self.kwargs["prompt"], schema_path=self.kwargs["schema"],
            protocol="llama_cpp_json_schema", sampling_profile="legacy_greedy")
        with patch.object(control, "complete") as transport:
            with self.assertRaises(ValueError):
                build_manifest(control, **self.kwargs)
        transport.assert_not_called()

    def gemma_client(self):
        return LocalRequirementClient(
            "http://127.0.0.1:8003", "synthetic-native", generation_contract=GenerationContract.QUOTES,
            prompt_path=self.kwargs["prompt"], schema_path=self.kwargs["schema"],
            protocol="llama_cpp_json_schema", sampling_profile="gemma4_nonthinking_llama_cpp")

    def test_gemma_manifest_records_explicit_model_quantization_and_sampling(self):
        weights = deepcopy(self.weight_data)
        weights["model_id"] = "google/gemma-4-31B-it-qat-q4_0-gguf"
        weights["files"][0]["name"] = "gemma-4-31B_q4_0-it.gguf"
        self.weights.write_text(json.dumps(weights))
        self.write_runtime(dict(native_metadata(), quantization="Q4_0"))
        client = self.gemma_client()
        with patch.object(client, "complete") as transport:
            manifest = build_manifest(client, **self.kwargs)
        transport.assert_not_called()
        self.assertEqual(manifest["model_id"], weights["model_id"])
        self.assertEqual(manifest["runtime"]["quantization"], "Q4_0")
        self.assertEqual(manifest["protocol"]["sampling_profile"], "gemma4_nonthinking_llama_cpp")
        self.assertEqual(manifest["protocol"]["sampling_request_parameters"], client.sampling_parameters)
        self.assertFalse(manifest["protocol"]["enable_thinking"])

    def test_native_profile_model_and_quantization_cannot_be_cross_paired(self):
        gemma = "google/gemma-4-31B-it-qat-q4_0-gguf"
        qwen = self.weight_data["model_id"]
        for client, model_id, quantization in (
            (self.client, qwen, "Q4_0"), (self.client, gemma, "Q4_K_M"),
            (self.gemma_client(), gemma, "Q4_K_M"), (self.gemma_client(), qwen, "Q4_0"),
            (self.gemma_client(), "other/gemma-4-31B-it-qat-q4_0-gguf", "Q4_0"),
            (self.gemma_client(), "google/gemma-4-31B-it-qat-q4_0-gguf-copy", "Q4_0"),
        ):
            with self.subTest(model_id=model_id, quantization=quantization):
                self.weights.write_text(json.dumps(dict(self.weight_data, model_id=model_id)))
                self.write_runtime(dict(native_metadata(), quantization=quantization))
                with patch.object(client, "complete") as transport:
                    with self.assertRaisesRegex(ValueError, "exact model ID and quantization"):
                        build_manifest(client, **self.kwargs)
                transport.assert_not_called()

    def test_duplicate_native_fields_are_not_silently_repaired(self):
        encoded = json.dumps(native_metadata())
        self.runtime.write_text(encoded[:-1] + ',"runtime_kind":"llama_cpp"}')
        with self.assertRaises(ValueError):
            runtime_metadata(self.runtime)


if __name__ == "__main__":
    unittest.main()
