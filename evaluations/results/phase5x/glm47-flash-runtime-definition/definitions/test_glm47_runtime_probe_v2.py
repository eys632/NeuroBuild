"""Focused saved-receipt controls only; no native/HTTP/GPU/dataset work."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

ROOT = Path('/home/a202192020/NeuroBuild_v2')
HELPER = ROOT / 'var/research/glm47_flash_runtime_probe_v2.py'
module = ModuleType('glm_runtime_v2_controls')
module.__file__ = str(HELPER)
exec(compile(HELPER.read_bytes(), str(HELPER), 'exec'), module.__dict__)
CONFIG = ROOT / 'var/research/glm47-flash-native-launch-epoch1.json'
CONFIG_SHA = '4824463fcabca13c2eaa07a9774c324b7980a2383915868f4f493b149dc245c4'
PROOF = ROOT / 'var/research/native-glm47-contract/final-cpu-proof.json'


class GlmReceiptControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config, _ = module.load_config(CONFIG, CONFIG_SHA)
        cls.proof = json.loads(PROOF.read_bytes())

    def consume_changed(self, proof, expected_error):
        # Give the changed receipt an honestly recomputed candidate SHA so the
        # test reaches structural checks; immutable linked pins remain fixed.
        raw = module.encoded(proof)
        sha = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory(dir=ROOT / 'var/research') as tmp:
            path = Path(tmp) / 'proof.json'; path.write_bytes(raw)
            with patch.object(module, 'FINAL_CPU_SHA', sha):
                with self.assertRaisesRegex(ValueError, expected_error):
                    module.cpu_provenance(self.config, path, sha)

    def test_actual_saved_aggregate_matches(self):
        provenance, token = module.cpu_provenance(self.config, PROOF, module.FINAL_CPU_SHA)
        self.assertEqual(token, 220)
        self.assertEqual(provenance['candidate_variant'], 'glm47-flash-gguf-nonthinking-v1')
        self.assertEqual(provenance['official_tokenizer_parity']['id_match_count'], 20)
        self.assertEqual(provenance['cpu_proof_refs'], module.CPU_REFS)

    def test_wrong_receipt_hash_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'GLM_FINAL_CPU_HASH_MISMATCH'):
            module.cpu_provenance(self.config, PROOF, '0' * 64)

    def test_profile_model_and_reference_mismatch(self):
        for key, value in (('sampling_profile', 'qwen38_nonthinking_llama_cpp'),
                           ('protocol', 'modern_json_schema'), ('revision', '0' * 40),
                           ('header_sha256', '0' * 64), ('official_tokenizer_normalizer', 'NFC'),
                           ('application_input_output_nfc_repair', True), ('template_override_used', True)):
            with self.subTest(field=key):
                changed = deepcopy(self.proof); changed[key] = value
                self.consume_changed(changed, 'GLM_CPU_PROVENANCE_MISMATCH')

    def test_full_cap_and_frozen_split_controls(self):
        for field, value in (('max_output_tokens', 128), ('max_context_tokens', 8192)):
            with self.subTest(field=field):
                changed = deepcopy(self.proof); changed[field] = value
                self.consume_changed(changed, 'GLM_CONTEXT_LIMIT_MISMATCH')
        for field, value in (('dataset_sha256', '0' * 64), ('input_count', 80),
                             ('max_input_plus_output', 4024), ('max_input_tokens', 3329)):
            with self.subTest(field=field):
                changed = deepcopy(self.proof); changed['splits']['exposed120'][field] = value
                self.consume_changed(changed, 'GLM_CONTEXT_SPLIT_MISMATCH')

    def test_actual_parity_token_and_linked_receipt_required(self):
        changed = deepcopy(self.proof); changed['official_tokenizer_parity']['id_match_count'] = 19
        self.consume_changed(changed, 'GLM_OFFICIAL_PARITY_REQUIRED')
        changed = deepcopy(self.proof); changed['resource_probe_token']['token_id'] = 582
        self.consume_changed(changed, 'GLM_PUBLIC_TOKEN_INVALID')
        changed = deepcopy(self.proof); changed['proof_refs']['vocab_context']['sha256'] = '0' * 64
        self.consume_changed(changed, 'GLM_CPU_REFERENCES_MISMATCH')
        original = module.read_json
        def altered_link(path):
            value, raw = original(path)
            return (value, raw + b' ') if path == ROOT / module.CPU_REFS['public_vocab']['path'] else (value, raw)
        with patch.object(module, 'read_json', side_effect=altered_link):
            with self.assertRaisesRegex(ValueError, 'GLM_CPU_REFERENCE_HASH_MISMATCH'):
                module.cpu_provenance(self.config, PROOF, module.FINAL_CPU_SHA)

    def test_live_entrypoint_stays_blocked_before_epoch_and_http(self):
        with patch.object(module, 'FINAL_CPU_SHA', None), patch.object(module, 'load_config') as load, \
                patch.object(module, 'epoch') as epoch, \
                patch.object(module, 'request_json') as request:
            with self.assertRaisesRegex(ValueError, 'GLM_ROOT_FINAL_RUNTIME_REVIEW_PENDING'):
                module.begin(CONFIG, CONFIG_SHA, PROOF, module.FINAL_CPU_SHA)
            load.assert_not_called(); epoch.assert_not_called(); request.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
