"""Actual saved CPU proof consumption and narrow new gate mutations only."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path('/home/a202192020/NeuroBuild_v2')
spec=importlib.util.spec_from_file_location('exaone_final_probe_tested',ROOT/'var/research/exaone45_runtime_probe_v4.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ActualRawGateTests(unittest.TestCase):
    def setUp(self):
        self.path=ROOT/'var/research/native-exaone45-contract/final-cpu-proof.json'
        self.cfg=SimpleNamespace(chat_template_path=m.OVERRIDE_PATH,chat_template_sha256=m.TEMPLATE_SHA,
            source_commit='f072b103714dfa1eee531f80b24512faf38e3dd2',model_sha256=m.MODEL_SHA,
            model_header_report_sha256=m.HEADER_SHA)
        self.patches=[patch.object(m,'epoch',side_effect=AssertionError('PROCESS_FORBIDDEN')),
                      patch.object(m,'request_json',side_effect=AssertionError('HTTP_FORBIDDEN'))]
        for p in self.patches:p.start();self.addCleanup(p.stop)
    def consume(self):return m.cpu_provenance(self.cfg,self.path,m.CPU_PROOF_SHA)
    def test_actual_proofs_pass_with_official_failure_and_derived_success_distinct(self):
        fields,token=self.consume()
        self.assertEqual(token,582)
        self.assertEqual(fields['official_hf_equivalence']['status'],'FAIL')
        self.assertEqual(fields['raw_reference']['official_hf_equivalence'],'NOT_ASSERTED_BY_DERIVED_REFERENCE')
        self.assertEqual(fields['runtime_variant'],m.RUNTIME_VARIANT)
        self.assertFalse(fields['normalization_limitation']['global_unicode_roundtrip_guarantee'])
    def changed_read(self,path,change):
        original=m.read_json;value,raw=original(path);value=deepcopy(value);change(value)
        return patch.object(m,'read_json',side_effect=lambda p:(value,raw) if p==path else original(p))
    def test_aggregate_contract_mutations_rejected(self):
        changes=[('officialpass',lambda x:x['official_hf_equivalence'].update(status='PASS')),
            ('oldvariant',lambda x:x.update(runtime_variant=m.TEMPLATE_VARIANT)),
            ('repair',lambda x:x.update(application_input_output_nfc_repair=True)),
            ('outputcap',lambda x:x.update(max_output_tokens=512)),
            ('dataset',lambda x:x['splits']['v2_length80'].update(dataset_sha256='0'*64)),
            ('totaltokens',lambda x:x['splits']['exposed120'].update(max_input_plus_output=2889)),
            ('raw19',lambda x:x['raw_reference'].update(id_match_count=19)),
            ('resourcetoken',lambda x:x['resource_probe_token'].update(token_id=583)),
            ('rawasofficial',lambda x:x['raw_reference'].update(official_hf_equivalence='PASS'))]
        for name,change in changes:
            with self.subTest(name=name),self.changed_read(self.path,change),self.assertRaises(ValueError):self.consume()
    def test_linked_actual_observation_mutations_rejected(self):
        public=ROOT/(m.PROOF_DIR+'raw-vocab-proof.json');ctx=ROOT/(m.PROOF_DIR+'vocab-context-raw-proof.json')
        cases=[(public,'lostsystem',lambda x:x['native'].update(derived_native_system_and_user_exact=False)),
            (public,'wrongref',lambda x:x.update(reference_kind='official_hf')),
            (public,'raw19',lambda x:x['native'].update(tokenizer_native_raw_roundtrip_count=19)),
            (ctx,'missinginputs',lambda x:x['native_checks'][1].update(input_count=79)),
            (ctx,'weakercontextcap',lambda x:x.update(max_context_tokens=8192)),
            (ctx,'grammarnotchecked',lambda x:x['native_checks'][0].update(native_vocab_grammar_eog_checked=False))]
        for path,name,change in cases:
            with self.subTest(name=name),self.changed_read(path,change),self.assertRaises(ValueError):self.consume()
    def test_wrong_proof_rejected_before_any_live_entrypoint(self):
        with patch.object(m,'load_config',return_value=(self.cfg,b'{}')),patch.object(m.resource,'setrlimit'):
            for call in (lambda:m.capture_startup('unused','unused',{},cpu_proof_path=self.path,cpu_proof_sha='0'*64),
                         lambda:m.public_smoke('unused','unused',cpu_proof_path=self.path,cpu_proof_sha='0'*64),
                         lambda:m.run_resource_smoke('unused','unused',cpu_proof_path=self.path,cpu_proof_sha='0'*64)):
                with self.assertRaisesRegex(ValueError,'EXAONE_CPU_PROVENANCE_MISMATCH'):call()
        m.epoch.assert_not_called();m.request_json.assert_not_called()
if __name__=='__main__':unittest.main()
