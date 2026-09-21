"""Only new raw-variant provenance controls; no native/GPU/HTTP or dataset reads."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT=Path('/home/a202192020/NeuroBuild_v2')
spec=importlib.util.spec_from_file_location('exaone_raw_pending',ROOT/'var/research/exaone45_runtime_probe_v3.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RawVariantTests(unittest.TestCase):
    def test_actual_official_failure_stays_separate_from_template_pass(self):
        value=m.validate_official_hf_failure()
        self.assertEqual((value['status'],value['id_match_count'],value['mismatch_indices']),('FAIL',18,[11,12]))
        self.assertEqual(m.validate_override_public()['reference_cases'],18)
        self.assertNotEqual(m.RUNTIME_VARIANT,m.TEMPLATE_VARIANT)
        self.assertIsNone(m.RAW_VOCAB_SHA);self.assertIsNone(m.RAW_CONTEXT_SHA)
    def test_relabelled_or_different_actual_observation_rejected(self):
        original,raw=m.read_json(m.OFFICIAL_VOCAB_PATH)
        changes=[('status','PASS'),('runtime_variant',m.RUNTIME_VARIANT),
                 ('tokenizer_fixture_sha256','0'*64),('effective_template_sha256',m.ORIGINAL_TEMPLATE_SHA),
                 ('application_input_output_nfc_repair',True)]
        for key,value in changes:
            changed={**original,key:value}
            with self.subTest(field=key),patch.object(m,'read_json',return_value=(changed,raw)),self.assertRaises(ValueError):
                m.validate_official_hf_failure()
        for key,value in [('tokenizer_id_match_count',20),('tokenizer_id_mismatch_mask',0),
                          ('tokenizer_reference_parity','PASS'),('official_reference_gate_pass',True),
                          ('tokenizer_native_raw_roundtrip_count',19)]:
            changed=deepcopy(original);changed['native'][key]=value
            with self.subTest(native=key),patch.object(m,'read_json',return_value=(changed,raw)),self.assertRaises(ValueError):
                m.validate_official_hf_failure()
    def test_selected_variant_cannot_enable_live_without_raw_proofs(self):
        with patch.object(m,'validate_cpu_common_fields',return_value={}), \
             patch.object(m,'epoch') as process,patch.object(m,'request_json') as http:
            with self.assertRaisesRegex(ValueError,'EXAONE_TOKENIZER_CONTRACT_PENDING'):
                m.cpu_provenance(None,None,None)
            process.assert_not_called();http.assert_not_called()
if __name__=='__main__':unittest.main()
