"""New model-combination fixtures only; all live entrypoints remain blocked."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path('/home/a202192020/NeuroBuild_v2')
spec = importlib.util.spec_from_file_location('exaone_probe_tested', ROOT / 'var/research/exaone45_runtime_probe.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def config():
    return SimpleNamespace(source_commit='f072b103714dfa1eee531f80b24512faf38e3dd2',
        model_revision=m.REVISION, model_sha256=m.MODEL_SHA,
        model_header_report_sha256=m.digest(b'header'), model_header_report='header',
        model_path=Path('/fixture/EXAONE-4.5-33B-Q4_K_M.gguf'),
        enable_reasoning=False, batch_size=64, ubatch_size=64, estimated_peak_mib=28672,
        peak_allowance_mib=0, binary_sha256='a'*64, source_report_sha256='b'*64,
        build_report_sha256='c'*64, port=8003, served_model_name='exaone-owned',
        report_file='guard', max_seconds=3600)


def cpu_fixture():
    return {'kind':'EXAONE45_NATIVE_CONTRACT_CPU_PROOF','status':'PASS',
        'runtime_variant':m.RUNTIME_VARIANT,'model_id':m.MODEL_ID,'revision':m.REVISION,
        'manifest_sha256':m.MANIFEST_SHA,'protocol':'llama_cpp_json_schema','sampling_profile':m.PROFILE,
        'source_pin':config().source_commit,'gguf_sha256':m.MODEL_SHA,
        'header_sha256':config().model_header_report_sha256,'template_sha256':m.TEMPLATE_SHA,
        'tokenizer_json_sha256':m.TOKENIZER_SHA,'model_inference_calls':0,
        'application_input_output_nfc_repair':False,'max_output_tokens':768,'max_context_tokens':4096,
        'official_reference_limitation':deepcopy(m.OFFICIAL_REFERENCE_LIMITATION),
        'official_fixture_sha256':m.OFFICIAL_FIXTURE_SHA,
        'source_sha256':{path:m.digest((ROOT/path).read_bytes()) for path in m.CPU_SOURCE_PATHS},
        'splits':{name:{'input_count':count,'dataset_sha256':sha,'min_input_tokens':2000,
                       'max_input_tokens':2400,'max_input_plus_output':3168}
                  for name,(count,sha) in m.CONTEXT_SPLITS.items()},
        'proof_refs':{name:{'path':'var/research/fake-linked-proof.json','sha256':m.digest(b'{}')}
                      for name in ('public_contract','vocab_context','tokenizer_fixture')}}


class ExaoneProbeDraftTests(unittest.TestCase):
    def fake_reader(self, proof):
        raw=m.encoded(proof)
        def read(path):
            if path=='aggregate': return proof,raw
            if path==m.OFFICIAL_FIXTURE_PATH:
                original=m.OFFICIAL_FIXTURE_PATH.read_bytes()
                return json.loads(original),original
            return {},b'{}'
        return patch.object(m,'read_json',side_effect=read),m.digest(raw)

    def test_generic_functions_remain_pinned_and_metadata_is_exaone_q4km(self):
        self.assertEqual(m.digest(m.BASE_PATH.read_bytes()),m.BASE_SHA)
        for name in ('binding','load_config','validate_guard','epoch','request_json',
                     'resource_payload','validate_resource','write_bundle'):
            self.assertIs(getattr(m,name),getattr(m.base,name))
        self.assertFalse(hasattr(m,'raw_context_provenance'))
        platform={'compiler':'GCC9.5','cmake':'3.23.5','cuda':'11.8','driver':'535.183.01',
                  'gpu':'A100','gpu_uuid':'GPU-00000000-0000-0000-0000-000000000000'}
        metadata=m.make_metadata(config(),platform,'1'*64,'2'*64,'3'*64)
        self.assertEqual(metadata['quantization'],'Q4_K_M')
        self.assertEqual(metadata['gguf_sha256'],m.MODEL_SHA)
        self.assertEqual(metadata['chat_template_sha256'],m.TEMPLATE_SHA)
        self.assertEqual(metadata['startup_report_sha256'],'2'*64)
        self.assertNotIn('runtime_variant',metadata)  # strict production schema; startup hash binds variant

    def test_exact_manifest_and_model_budget_bound_before_generic_files(self):
        original=m.read_json
        def read(path):
            return ({'file_bytes':m.MODEL_BYTES},b'header') if path=='header' else original(path)
        with patch.object(m,'read_json',side_effect=read),patch.object(m,'binding',return_value={}) as bind:
            self.assertEqual(m.exaone_binding(config()),{})
            bind.reset_mock()
            for key,value in [('model_revision','0'*40),('model_sha256','0'*64),
                              ('enable_reasoning',True),('batch_size',2),('estimated_peak_mib',28673),
                              ('peak_allowance_mib',1),('model_path',Path('/fixture/other.gguf'))]:
                with self.subTest(field=key),self.assertRaisesRegex(ValueError,'EXAONE_CONFIG_MISMATCH'):
                    m.exaone_binding(SimpleNamespace(**{**vars(config()),key:value}))
            bind.assert_not_called()
        with patch.object(m,'MANIFEST_SHA','0'*64),patch.object(m,'binding') as bind:
            with self.assertRaisesRegex(ValueError,'EXAONE_MANIFEST_MISMATCH'):m.exaone_binding(config())
            bind.assert_not_called()

    def test_common_cpu_fields_preserve_official_failure_and_reject_wrong_bindings(self):
        proof=cpu_fixture();reader,sha=self.fake_reader(proof)
        with reader: common=m.validate_cpu_common_fields(config(),'aggregate',sha)
        self.assertEqual(common['official_reference_limitation']['raw_original_roundtrip_count'],18)
        self.assertEqual(common['runtime_variant'],m.RUNTIME_VARIANT)
        self.assertEqual(common['tokenizer_contract_status'],m.TOKENIZER_CONTRACT_STATUS)
        self.assertNotIn('status',common)
        for key,value in [('kind','EXAONE45_NATIVE_PUBLIC_TEMPLATE_CPU_PROOF'),
                          ('status','PENDING'),('runtime_variant','qwen38-gguf-raw-unicode-v1'),
                          ('protocol','legacy_guided_json'),('sampling_profile','gemma4_nonthinking_llama_cpp'),
                          ('source_pin','0'*40),('header_sha256','0'*64),('manifest_sha256','0'*64),
                          ('max_output_tokens',512),('max_context_tokens',8192),
                          ('application_input_output_nfc_repair',True),('model_inference_calls',True),
                          ('official_reference_limitation',{'status':'PASS','case_count':20})]:
            changed={**proof,key:value};reader,sha=self.fake_reader(changed)
            with self.subTest(field=key),reader,self.assertRaises(ValueError):
                m.validate_cpu_common_fields(config(),'aggregate',sha)
        changed=deepcopy(proof);changed['splits']['exposed120']['max_input_plus_output']=3167
        reader,sha=self.fake_reader(changed)
        with reader,self.assertRaisesRegex(ValueError,'EXAONE_CONTEXT_SPLIT_MISMATCH'):
            m.validate_cpu_common_fields(config(),'aggregate',sha)

    def test_even_synthetic_complete_claim_cannot_open_live_entrypoints(self):
        reader,sha=self.fake_reader(cpu_fixture())
        with reader,patch.object(m,'load_config',return_value=(config(),b'{}')), \
             patch.object(m,'epoch') as proc,patch.object(m,'request_json') as http, \
             patch.object(m,'exaone_binding') as bind,patch.object(m.resource,'setrlimit'), \
             patch('neurobuild.infrastructure.local_model.LocalRequirementClient') as client:
            options={'cpu_proof_path':'aggregate','cpu_proof_sha':sha}
            for call in (lambda:m.capture_startup('cfg','1'*64,{},**options),
                         lambda:m.public_smoke('cfg','1'*64,**options),
                         lambda:m.run_resource_smoke('cfg','1'*64,**options)):
                with self.assertRaisesRegex(ValueError,'EXAONE_TOKENIZER_CONTRACT_PENDING'):call()
            proc.assert_not_called();http.assert_not_called();bind.assert_not_called();client.assert_not_called()

    def test_props_use_single_lf_representation_without_changing_embedded_hash(self):
        raw=(ROOT/'var/research/exaone45-33b-candidate-metadata/upstream/chat_template.jinja').read_bytes()
        self.assertTrue(raw.endswith(b'\n'));self.assertNotIn(b'\r',raw)
        self.assertEqual((len(raw),m.digest(raw)),(m.EMBEDDED_TEMPLATE_BYTES,m.TEMPLATE_SHA))
        self.assertEqual((len(raw[:-1]),m.digest(raw[:-1])),(m.PROPS_TEMPLATE_BYTES,m.PROPS_TEMPLATE_SHA))
        cfg=config();props={'model_alias':cfg.served_model_name,'total_slots':1,'model_path':str(cfg.model_path),
            'default_generation_settings':{'n_ctx':4096},'chat_template':raw[:-1].decode(),'is_sleeping':False}
        models={'data':[{'id':cfg.served_model_name,'meta':{'n_ctx':4096}}]}
        with patch.object(m.base,'checked_file',side_effect=lambda path,root:path):
            value=m.validate_health_models_props(cfg,{'status':'ok'},models,props)
            self.assertEqual(value['chat_template_sha256'],m.TEMPLATE_SHA)
            self.assertEqual(value['props_reported_template_sha256'],m.PROPS_TEMPLATE_SHA)
            self.assertNotIn('chat_template',value)
            for template in (raw.decode(),raw[:-2].decode(),raw[:-1].decode()+' '):
                with self.subTest(template_hash=m.digest(template.encode())),self.assertRaisesRegex(ValueError,'PROPS_MISMATCH'):
                    m.validate_health_models_props(cfg,{'status':'ok'},models,{**props,'chat_template':template})


if __name__=='__main__':unittest.main()
