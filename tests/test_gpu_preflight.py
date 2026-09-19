"""Deterministic budget tests: never invoke nvidia-smi or access a GPU."""

from dataclasses import replace
import json
from contextlib import redirect_stdout
from io import StringIO
import subprocess
import unittest
from unittest.mock import patch

from scripts.gpu_preflight import Policy, PreflightError, Reading, _query_gpu, evaluate_budget, main, parse_reading, run_preflight


class GpuPreflightTests(unittest.TestCase):
    def setUp(self):
        self.policy = Policy("a100", 24000)
        self.reading = Reading(40960, 36373, 3965, 0)

    def sample(self, policy=None, rows=None, mask="3"):
        policy = policy or self.policy
        rows = rows or ["40960, 36373, 3965, 0"] * policy.samples
        values, queried, slept = iter(rows), [], []

        def query(index):
            queried.append(index)
            return next(values)

        report = run_preflight(policy, environ={"CUDA_VISIBLE_DEVICES": mask}, query=query, sleep=slept.append)
        return report, queried, slept

    def test_other_allocations_do_not_blanket_block_a_stable_budget(self):
        report, queried, slept = self.sample()
        self.assertTrue(report["allowed"])
        self.assertEqual(queried, [3] * 5)
        self.assertEqual(slept, [1.0] * 4)
        self.assertEqual(report["measured"]["maximum_used_mib"], 3965)
        self.assertEqual(report["budget"]["required_safety_margin_mib"], 7275)
        self.assertEqual(report["budget"]["available_model_budget_mib"], 29098)
        self.assertFalse(report["memory_fit_guaranteed"])
        self.assertEqual(report["runtime_validation"], "NOT_TESTED")
        self.assertLessEqual(report["required_launch_limit"]["maximum_fraction_of_total_vram"] * 40960, 29098)

    def test_fixed_floor_and_relative_margin_use_the_larger_reserve(self):
        small = [Reading(32768, 20000, 12000, 0)] * 5
        report = evaluate_budget(small, replace(self.policy, estimated_peak_mib=13856))
        self.assertTrue(report["allowed"])
        self.assertEqual(report["budget"]["required_safety_margin_mib"], 6144)
        report = evaluate_budget(small, replace(self.policy, estimated_peak_mib=13857))
        self.assertFalse(report["allowed"])
        self.assertIn("INSUFFICIENT_MEMORY_BUDGET", report["reason_codes"])

    def test_high_utilization_or_memory_swing_blocks_even_when_peak_fits(self):
        cases = (
            ([self.reading] * 4 + [Reading(40960, 36373, 3965, 11)], "GPU_UTILIZATION_HIGH"),
            ([self.reading] * 4 + [Reading(40960, 35000, 5338, 0)], "FREE_MEMORY_UNSTABLE"),
        )
        for readings, code in cases:
            with self.subTest(code=code):
                report = evaluate_budget(readings, self.policy)
                self.assertFalse(report["allowed"])
                self.assertIn(code, report["reason_codes"])
                self.assertIsNone(report["required_launch_limit"]["maximum_total_runtime_peak_mib"])

    def test_budget_uses_minimum_free_sample_and_all_peak_components_are_named(self):
        readings = [self.reading] * 4 + [Reading(40960, 36200, 4138, 5)]
        report = evaluate_budget(readings, self.policy)
        self.assertTrue(report["allowed"])
        self.assertEqual(report["budget"]["available_model_budget_mib"], 28960)
        self.assertEqual(set(report["budget"]["estimate_must_include"]),
                         {"weights", "KV_cache", "workspace", "CUDA_context", "allocator_overhead"})

    def test_wrong_empty_multiple_or_missing_cuda_mask_never_queries_gpu(self):
        for mask in (None, "", "0", "1", "3,0", "GPU-unknown", "3 "):
            with self.subTest(mask=mask):
                report, queried, slept = self.sample(mask=mask)
                self.assertFalse(report["allowed"])
                self.assertEqual(report["reason_codes"], ["CUDA_MASK_MISMATCH"])
                self.assertEqual(queried, [])
                self.assertEqual(slept, [])

    def test_rtx_profile_queries_only_its_explicit_permitted_index_with_fake_data(self):
        report, queried, _ = self.sample(Policy("rtx5090", 16000), rows=["32768, 31000, 1000, 0"] * 5, mask="1")
        self.assertTrue(report["allowed"])
        self.assertEqual(queried, [1] * 5)
        self.assertEqual(report["required_cuda_visible_devices"], "1")

    def test_invalid_or_unknown_readings_are_rejected(self):
        invalid = ("", "N/A, 20000, 100, 0", "40960, 30000, 10000, [Not Supported]",
                   "40960, 30000, 10000, 0\n40960, 30000, 10000, 0", "40960 MiB, 30000, 10000, 0",
                   "40960, 50000, 0, 0", "40960, 35000, 35000, 0", "40960, 30000, 10000, 101",
                   "40960, -1, 10000, 0", "40960, 30000, 10000", "40960, 30000, 10000, nan")
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(PreflightError):
                parse_reading(row)
        with self.assertRaises(PreflightError):
            Reading(True, 0, 0, 0)

    def test_partial_unknown_window_blocks_without_returning_a_launch_budget(self):
        report, queried, slept = self.sample(rows=["40960, 36373, 3965, 0", "N/A, N/A, N/A, N/A"])
        self.assertFalse(report["allowed"])
        self.assertEqual(report["reason_codes"], ["INVALID_READING"])
        self.assertEqual(len(report["samples"]), 1)
        self.assertNotIn("required_launch_limit", report)

    def test_changed_total_memory_and_incomplete_window_are_rejected(self):
        with self.assertRaises(PreflightError) as caught:
            evaluate_budget([self.reading] * 4 + [Reading(40000, 35000, 4000, 0)], self.policy)
        self.assertEqual(caught.exception.code, "UNSTABLE_TOTAL_MEMORY")
        with self.assertRaises(PreflightError):
            evaluate_budget([self.reading], self.policy)

    def test_policy_rejects_invalid_values_and_unsafe_margin_reductions(self):
        for changes in ({"profile": "auto"}, {"estimated_peak_mib": 0}, {"estimated_peak_mib": True},
                        {"samples": 1}, {"samples": 99}, {"interval_seconds": float("nan")},
                        {"samples": 20, "interval_seconds": 5}, {"safety_margin_mib": 0},
                        {"safety_margin_fraction": 0.19}, {"safety_margin_fraction": float("inf")},
                        {"max_utilization_percent": 100}, {"max_free_change_mib": -1}):
            with self.subTest(changes=changes), self.assertRaises(PreflightError):
                replace(self.policy, **changes)

    def test_query_command_is_scoped_and_never_requests_processes_or_other_devices(self):
        completed = subprocess.CompletedProcess([], 0, stdout="40960, 36373, 3965, 0", stderr="")
        with patch("scripts.gpu_preflight.subprocess.run", return_value=completed) as execute:
            _query_gpu(3)
            arguments = execute.call_args.args[0]
            self.assertEqual(arguments[:3], ["nvidia-smi", "-i", "3"])
            self.assertIn("--query-gpu=memory.total,memory.free,memory.used,utilization.gpu", arguments)
            self.assertFalse(any("process" in argument or "compute-apps" in argument for argument in arguments))
        with patch("scripts.gpu_preflight.subprocess.run", side_effect=AssertionError("Real GPU queries are forbidden in tests")):
            with self.assertRaises(PreflightError):
                _query_gpu(0)
            with self.assertRaises(PreflightError):
                _query_gpu(2)

    def test_query_failure_is_sanitized_and_blocks(self):
        with patch("scripts.gpu_preflight.subprocess.run", side_effect=subprocess.TimeoutExpired("private text", 5)):
            report = run_preflight(self.policy, environ={"CUDA_VISIBLE_DEVICES": "3"}, sleep=lambda _: None)
        self.assertFalse(report["allowed"])
        self.assertEqual(report["reason_codes"], ["GPU_QUERY_FAILED"])
        self.assertNotIn("private text", json.dumps(report))

    def test_cli_emits_json_and_nonzero_exit_without_gpu_access_for_wrong_mask(self):
        output = StringIO()
        with patch.dict("scripts.gpu_preflight.os.environ", {"CUDA_VISIBLE_DEVICES": "0"}), \
                patch("scripts.gpu_preflight._query_gpu", side_effect=AssertionError("Real GPU queries are forbidden in tests")), \
                redirect_stdout(output):
            status = main(["--profile", "a100", "--estimated-peak-mib", "20000"])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue())["reason_codes"], ["CUDA_MASK_MISMATCH"])


if __name__ == "__main__":
    unittest.main()
