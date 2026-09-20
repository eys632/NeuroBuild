"""CPU/fake tests for only the new minimal attestation helper; no real HTTP/PID/GPU."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('minimal_attestation_tested', HERE / 'attest_native_epoch6_minimal.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


class MinimalAttestationTests(unittest.TestCase):
    def setUp(self):
        self.config_raw = (HERE / 'qwen38-native-launch-epoch6-minimal-v2.json').read_bytes()
        self.config = SimpleNamespace(**json.loads(self.config_raw))
        self.old = json.loads((HERE / 'qwen38-native-launch-epoch4.json').read_bytes())
        self.carry = {'kind': 'NATIVE_HISTORICAL_CONTRACT_CARRY_FORWARD',
            'status': 'VERIFIED_REUSED_NOT_RERUN', 'current_launch_config_sha256': m.digest(self.config_raw),
            'historical_freeze_path': m.FREEZE, 'historical_freeze_sha256': m.FREEZE_SHA,
            'tests_rerun': 0}
        self.provenance = {'runtime_variant': 'qwen38-gguf-raw-unicode-v1'}
        self.before = {'child_pid': 12345, 'started_at_utc': '2026-09-20T10:00:00+00:00',
                       'elapsed_seconds': 60, 'state': 'RUNNING'}
        self.after = {**self.before, 'elapsed_seconds': 61}
        self.listeners = {'verdict': 'PASS', 'snapshot_complete': True, 'all_loopback': True,
            'uid': os.getuid(), 'pid': 12345, 'process_start_ticks': 123456,
            'listeners': [{'address': '127.0.0.1', 'port': 8003}]}
        self.p = SimpleNamespace(
            encoded=encoded, request_json=Mock(return_value=({'status': 'ok'}, .01)),
            epoch=Mock(return_value=self.listeners),
            read_json=Mock(side_effect=[(self.before, encoded(self.before)), (self.after, encoded(self.after))]),
            validate_guard=Mock(), binding=Mock(return_value={}),
            load_config=Mock(return_value=(self.config, self.config_raw)),
            make_metadata=lambda config, platform, c, a, l: {
                'launch_config_sha256': c, 'startup_report_sha256': a, 'listener_report_sha256': l})

    def generate(self):
        return m.attest(self.p, self.config, self.config_raw, {}, self.carry, {}, self.provenance)

    def test_only_three_operational_fields_change(self):
        new = json.loads(self.config_raw)
        self.assertEqual(m.config_equivalence(self.old, new), sorted(m.ALLOWED_CHANGES))
        for key, value in (('batch_size', 2), ('binary_sha256', '0' * 64),
                           ('estimated_peak_mib', 28000), ('enable_reasoning', True)):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'INFERENCE_CONFIG_CHANGED'):
                m.config_equivalence(self.old, {**new, key: value})

    def test_bad_lifetime_or_output_is_rejected(self):
        new = json.loads(self.config_raw)
        for changes in ({'max_seconds': 3601}, {'max_seconds': True},
                        {'report_file': 'var/reports/qwen38-native-epoch4.json'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                m.config_equivalence(self.old, {**new, **changes})

    def test_exactly_one_health_and_no_contract_model_calls(self):
        bundle = self.generate()
        self.p.request_json.assert_called_once_with(8003, '/health', timeout=10, max_bytes=1024)
        self.assertEqual(self.p.epoch.call_count, 2)
        self.p.epoch.assert_called_with(self.config, 12345, 123456)
        a = json.loads(bundle['attestation.json'])
        self.assertEqual(a['kind'], 'NATIVE_MINIMAL_EPOCH_ATTESTATION')
        self.assertEqual(a['model_inference_calls'], 0)
        self.assertEqual(a['full_startup_probe_calls'], 0)
        self.assertEqual(a['carry_forward_sha256'], m.digest(bundle['contract_carry_forward.json']))
        self.assertEqual(json.loads(bundle['runtime_metadata.json'])['startup_report_sha256'],
                         m.digest(bundle['attestation.json']))

    def test_bad_carry_is_rejected_before_health(self):
        self.carry['current_launch_config_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'CARRY_FORWARD_CHANGED'):
            self.generate()
        self.p.request_json.assert_not_called()
        self.p.epoch.assert_not_called()

    def test_epoch_change_does_not_retry(self):
        changed = {**self.after, 'child_pid': 99999}
        self.p.read_json.side_effect = [(self.before, encoded(self.before)), (changed, encoded(changed))]
        with self.assertRaisesRegex(ValueError, 'GUARD_EPOCH_CHANGED'):
            self.generate()
        self.assertEqual(self.p.request_json.call_count, 1)

    def test_bad_health_does_not_retry(self):
        self.p.request_json.return_value = ({'status': 'loading model'}, .01)
        with self.assertRaisesRegex(ValueError, 'HEALTH_FAILED'):
            self.generate()
        self.assertEqual(self.p.request_json.call_count, 1)

    def validate_fake_bundle(self, bundle):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            root = Path(directory)
            folder = root / 'archive'
            folder.mkdir()
            for name, raw in bundle.items():
                (folder / name).write_bytes(raw)
            with patch.object(m, 'ROOT', root), patch.object(m, 'historical_contract',
                    return_value=(self.carry, {}, self.provenance)):
                self.p.request_json.reset_mock()
                self.p.epoch.reset_mock()
                result = m.validate_saved_bundle(self.p, folder)
                self.p.request_json.assert_not_called()
                self.p.epoch.assert_not_called()
                return result

    def test_saved_bundle_check_is_offline(self):
        result = self.validate_fake_bundle(self.generate())
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['historical_tests_rerun'], 0)

    def test_tampered_saved_carry_rejected(self):
        bundle = self.generate()
        carry = json.loads(bundle['contract_carry_forward.json'])
        carry['tests_rerun'] = 386
        bundle['contract_carry_forward.json'] = encoded(carry)
        with self.assertRaisesRegex(ValueError, 'CARRY_FORWARD_CHANGED'):
            self.validate_fake_bundle(bundle)

    def test_saved_epoch_or_metadata_rejected(self):
        base = self.generate()
        for name, key, value, code in (
            ('guard_after.json', 'child_pid', 99999, 'ATTESTATION_EPOCH_CHANGED'),
            ('runtime_metadata.json', 'startup_report_sha256', '0' * 64, 'CURRENT_METADATA_CHANGED')):
            with self.subTest(name=name):
                bundle = copy.deepcopy(base)
                data = json.loads(bundle[name]); data[key] = value; bundle[name] = encoded(data)
                with self.assertRaisesRegex(ValueError, code):
                    self.validate_fake_bundle(bundle)

    def test_pinned_small_input_hash_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            root = Path(directory)
            (root / 'proof.json').write_bytes(b'{}')
            (root / 'alias.json').symlink_to('proof.json')
            with patch.object(m, 'ROOT', root):
                self.assertEqual(m.read_local('proof.json', m.digest(b'{}')), b'{}')
                with self.assertRaisesRegex(ValueError, 'INPUT_HASH_MISMATCH'):
                    m.read_local('proof.json', '0' * 64)
                with self.assertRaisesRegex(ValueError, 'INPUT_PATH_INVALID'):
                    m.read_local('alias.json')


if __name__ == '__main__':
    unittest.main()
