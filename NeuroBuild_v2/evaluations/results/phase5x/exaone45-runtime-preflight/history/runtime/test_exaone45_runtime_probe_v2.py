"""Only new override bindings, using own tiny files/fake metadata; no live calls."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path('/home/a202192020/NeuroBuild_v2')
spec=importlib.util.spec_from_file_location('exaone_override_probe_tested',ROOT/'var/research/exaone45_runtime_probe_v2.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from scripts.gpu_preflight import PreflightError


class OverrideProbeTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='exaone-override-test-',dir=ROOT/'var/research')
        self.addCleanup(self.temporary.cleanup);self.base=Path(self.temporary.name)
        self.template=self.base/'override.jinja'
        self.template.write_bytes((ROOT/'var/research/native-exaone45-contract/chat_template_continue_override.jinja').read_bytes())
        self.override_patch=patch.object(m,'OVERRIDE_PATH',self.template)
        self.override_patch.start();self.addCleanup(self.override_patch.stop)
        self.data={'profile':'a100','binary_path':str(self.base/'llama-server'),'binary_sha256':'a'*64,
            'build_report':str(self.base/'build.json'),'build_report_sha256':'b'*64,
            'source_report':str(self.base/'source.json'),'source_report_sha256':'c'*64,
            'source_commit':'f072b103714dfa1eee531f80b24512faf38e3dd2',
            'model_path':str(self.base/'EXAONE-4.5-33B-Q4_K_M.gguf'),'model_sha256':m.MODEL_SHA,
            'model_revision':m.REVISION,'model_header_report':str(ROOT/'var/reports/exaone45-gguf-header-v2.json'),
            'model_header_report_sha256':m.HEADER_SHA,'estimated_peak_mib':28672,
            'log_file':str(self.base/'server.log'),'report_file':str(self.base/'server.json'),
            'enable_reasoning':False,'served_model_name':'synthetic-exaone','port':8003,
            'max_seconds':3600,'max_model_len':4096,'peak_allowance_mib':0,
            'batch_size':64,'ubatch_size':64,'chat_template_path':str(self.template),
            'chat_template_sha256':m.TEMPLATE_SHA}
        for key in ('binary_path','model_path'):Path(self.data[key]).write_bytes(b'OWN_SYNTHETIC_NOT_EXECUTED')
        self.config_path=self.base/'config.json'

    def load(self, data=None):
        raw=m.encoded(self.data if data is None else data);self.config_path.write_bytes(raw)
        return m.load_config(self.config_path,m.digest(raw))[0]

    def test_optional_path_becomes_path_and_actual_argv_binds_exact_override(self):
        cfg=self.load()
        self.assertIsInstance(cfg.chat_template_path,Path)
        arguments=m.base.native_arguments(cfg,ROOT)
        self.assertEqual(arguments.count('--chat-template-file'),1)
        self.assertEqual(arguments[-2:],['--chat-template-file',str(self.template)])
        self.assertEqual(m.pinned_override(cfg),{'path':str(self.template.relative_to(ROOT)),'sha256':m.TEMPLATE_SHA})
        for changes in ({'chat_template_path':None,'chat_template_sha256':None},
                        {'chat_template_path':None},{'chat_template_sha256':None},
                        {'chat_template_sha256':m.ORIGINAL_TEMPLATE_SHA}):
            with self.subTest(changes=changes),self.assertRaisesRegex(ValueError,'EXAONE_OVERRIDE_CONFIG_REQUIRED'):
                self.load({**self.data,**changes})
        with patch.object(m,'LAUNCHER_SHA','0'*64),self.assertRaisesRegex(ValueError,'EXAONE_LAUNCHER_PIN_MISMATCH'):
            self.load()

    def test_actual_header_and_override_extend_generic_artifact_identity(self):
        cfg=self.load();generic={'binary_sha256':cfg.binary_sha256}
        with patch.object(m,'binding',return_value=generic):
            artifacts=m.exaone_binding(cfg)
        self.assertEqual(artifacts,dict(generic,chat_template_override=m.pinned_override(cfg)))
        self.assertNotIn('chat_template_override',generic)
        # Exercise the unchanged guard's whole-artifact equality before resource checks.
        report={'state':'RUNNING','runtime_family':'llama_cpp','native_identity_verified':True,
            'physical_gpu_index':3,'required_cuda_visible_devices':'3','max_model_len':4096,
            'max_num_seqs':1,'batch_size':64,'ubatch_size':64,'served_model_name':cfg.served_model_name,
            'model_path':str(cfg.model_path),'native_artifacts':generic}
        with self.assertRaisesRegex(ValueError,'GUARD_BINDING_MISMATCH'):
            m.validate_guard(cfg,report,artifacts)
        self.template.write_bytes(self.template.read_bytes().replace(b'system',b'SYSTEM',1))
        with self.assertRaises(PreflightError):m.pinned_override(cfg)

    def test_public_proof_requires_exact_system_reference_and_derived_template(self):
        receipt=m.validate_override_public()
        self.assertEqual(receipt['reference_cases'],18)
        self.assertEqual(receipt['proof_ref']['sha256'],m.PUBLIC_PROOF_SHA)
        original,raw=m.read_json(m.PUBLIC_PROOF_PATH)
        changes=[('candidate_template_sha256',m.ORIGINAL_TEMPLATE_SHA),
                 ('runtime_variant','exaone45-gguf-nonthinking-korean-v1'),
                 ('official_original_derived_reference_byte_equal',False)]
        for key,value in changes:
            changed={**original,key:value}
            with self.subTest(field=key),patch.object(m,'read_json',return_value=(changed,raw)),self.assertRaises(ValueError):
                m.validate_override_public()
        for key,value in [('derived_native_system_and_user_exact',False),
                          ('derived_native_prompt_equals_official_reference',False),
                          ('native_request_prompt_bytes',177)]:
            changed=deepcopy(original);changed['native'][key]=value
            with self.subTest(native_field=key),patch.object(m,'read_json',return_value=(changed,raw)),self.assertRaisesRegex(ValueError,'SYSTEM_POLICY_PROOF'):
                m.validate_override_public()

    def future_cpu_fixture(self,cfg):
        return {'kind':'EXAONE45_NATIVE_CONTRACT_CPU_PROOF','status':'PASS','runtime_variant':m.RUNTIME_VARIANT,
            'model_id':m.MODEL_ID,'revision':m.REVISION,'manifest_sha256':m.MANIFEST_SHA,
            'protocol':'llama_cpp_json_schema','sampling_profile':m.PROFILE,'source_pin':cfg.source_commit,
            'gguf_sha256':m.MODEL_SHA,'header_sha256':m.HEADER_SHA,'runtime_launcher_sha256':m.LAUNCHER_SHA,
            'original_embedded_template_sha256':m.ORIGINAL_TEMPLATE_SHA,'template_sha256':m.TEMPLATE_SHA,
            'tokenizer_json_sha256':m.TOKENIZER_SHA,'model_inference_calls':0,
            'application_input_output_nfc_repair':False,'max_output_tokens':768,'max_context_tokens':4096,
            'chat_template_override':{**m.pinned_override(cfg),'bytes':m.OVERRIDE_BYTES,
                'original_embedded_template_sha256':m.ORIGINAL_TEMPLATE_SHA,'transform':'continue-free-system-message-branch-v1'},
            'template_render_parity':m.validate_override_public(),
            'official_reference_limitation':deepcopy(m.OFFICIAL_REFERENCE_LIMITATION),
            'official_fixture_sha256':m.OFFICIAL_FIXTURE_SHA,
            'splits':{name:{'input_count':count,'dataset_sha256':sha,'min_input_tokens':2000,
                           'max_input_tokens':2400,'max_input_plus_output':3168}
                      for name,(count,sha) in m.CONTEXT_SPLITS.items()},
            'source_sha256':{path:m.digest((ROOT/path).read_bytes()) for path in m.CPU_SOURCE_PATHS},
            'proof_refs':{key:{'path':'var/research/fake-exaone-cpu.json','sha256':m.digest(b'{}')}
                          for key in ('public_contract','vocab_context','tokenizer_fixture')}}

    def test_full_cpu_still_pending_even_with_override_and_public_pass(self):
        cfg=self.load();proof=self.future_cpu_fixture(cfg);raw=m.encoded(proof);original=m.read_json
        def read(path):
            if path=='aggregate':return proof,raw
            if path==ROOT/'var/research/fake-exaone-cpu.json':return {},b'{}'
            return original(path)
        with patch.object(m,'read_json',side_effect=read):
            fields=m.validate_cpu_common_fields(cfg,'aggregate',m.digest(raw))
            self.assertEqual(fields['original_embedded_template_sha256'],m.ORIGINAL_TEMPLATE_SHA)
            self.assertEqual(fields['effective_chat_template_sha256'],m.TEMPLATE_SHA)
            self.assertEqual(fields['official_reference_limitation']['raw_original_roundtrip_count'],18)
            with patch.object(m,'epoch') as proc,patch.object(m,'request_json') as http, \
                 patch.object(m.resource,'setrlimit'),patch('neurobuild.infrastructure.local_model.LocalRequirementClient') as client:
                options={'cpu_proof_path':'aggregate','cpu_proof_sha':m.digest(raw)}
                for call in (lambda:m.capture_startup(self.config_path,m.digest(self.config_path.read_bytes()),{},**options),
                             lambda:m.public_smoke(self.config_path,m.digest(self.config_path.read_bytes()),**options),
                             lambda:m.run_resource_smoke(self.config_path,m.digest(self.config_path.read_bytes()),**options)):
                    with self.assertRaisesRegex(ValueError,'EXAONE_TOKENIZER_CONTRACT_PENDING'):call()
                proc.assert_not_called();http.assert_not_called();client.assert_not_called()

    def test_props_and_metadata_separate_original_effective_and_reported_sources(self):
        cfg=self.load();raw=self.template.read_bytes()
        self.assertEqual((len(raw),m.digest(raw)),(m.OVERRIDE_BYTES,m.TEMPLATE_SHA))
        self.assertEqual((len(raw[:-1]),m.digest(raw[:-1])),(m.PROPS_TEMPLATE_BYTES,m.PROPS_TEMPLATE_SHA))
        props={'model_alias':cfg.served_model_name,'total_slots':1,'model_path':str(cfg.model_path),
            'default_generation_settings':{'n_ctx':4096},'chat_template':raw[:-1].decode(),'is_sleeping':False}
        models={'data':[{'id':cfg.served_model_name,'meta':{'n_ctx':4096}}]}
        result=m.validate_health_models_props(cfg,{'status':'ok'},models,props)
        self.assertEqual(result['embedded_chat_template_sha256'],m.ORIGINAL_TEMPLATE_SHA)
        self.assertEqual(result['effective_chat_template_sha256'],m.TEMPLATE_SHA)
        self.assertEqual(result['props_reported_template_sha256'],m.PROPS_TEMPLATE_SHA)
        for value in (raw.decode(),(ROOT/'var/research/exaone45-33b-candidate-metadata/upstream/chat_template.jinja').read_text()):
            with self.assertRaisesRegex(ValueError,'PROPS_MISMATCH'):
                m.validate_health_models_props(cfg,{'status':'ok'},models,{**props,'chat_template':value})
        platform={'compiler':'GCC','cmake':'3.23.5','cuda':'11.8','driver':'535.183.01','gpu':'A100',
                  'gpu_uuid':'GPU-00000000-0000-0000-0000-000000000000'}
        metadata=m.make_metadata(cfg,platform,'1'*64,'2'*64,'3'*64)
        self.assertEqual(metadata['chat_template_sha256'],m.TEMPLATE_SHA)
        self.assertEqual(metadata['startup_report_sha256'],'2'*64)
        self.assertEqual(metadata['quantization'],'Q4_K_M')


if __name__=='__main__':unittest.main()
