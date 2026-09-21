import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path('/home/a202192020/NeuroBuild_v2')
spec = importlib.util.spec_from_file_location('native_probe', ROOT / 'var/research/native_runtime_probe.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def valid_resource():
    return {'tokens_evaluated': 3328, 'tokens_predicted': 768, 'tokens_cached': 4095,
            'truncated': True, 'stop': True, 'stop_type': 'limit',
            'timings/prompt_n': 3328, 'timings/predicted_n': 768,
            'timings/prompt_ms': 200.0, 'timings/predicted_ms': 300.0}


class ProbeTests(unittest.TestCase):
    def test_resource_request_exact_no_content_fields_or_grammar(self):
        request = m.resource_payload(220)
        self.assertEqual(len(request['prompt']), 3328)
        self.assertEqual(set(request['prompt']), {220})
        self.assertEqual(request['n_predict'], 768)
        self.assertIs(request['cache_prompt'], False)
        self.assertIs(request['ignore_eos'], True)
        self.assertNotIn('grammar', request)
        self.assertTrue(set(request['response_fields']).isdisjoint({'content', 'prompt', 'tokens', 'generation_settings'}))
        request['response_fields'].append('content')
        self.assertNotIn('content', m.RESOURCE_FIELDS)
        for bad in [True, -1, 1.0, '220']:
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, 'TOKEN_INVALID'):
                m.resource_payload(bad)

    def test_complete_context_boundary_and_rejections(self):
        self.assertFalse(m.validate_resource(valid_resource())['quality_evaluation'])
        changes = [('content', 'must never be returned'), ('tokens_predicted', 767),
                   ('tokens_cached', 4096), ('truncated', False), ('stop', 1),
                   ('timings/prompt_n', 1), ('timings/predicted_ms', float('nan')),
                   ('tokens_evaluated', True)]
        for key, value in changes:
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.validate_resource({**valid_resource(), key: value})

    def test_http_no_redirect_bounded_read_and_local_only(self):
        events = []
        class Connection:
            def __init__(self, host, port, timeout): events.append((host, port, timeout))
            def request(self, *args, **kwargs): events.append((args, kwargs))
            def getresponse(self): return self
            status = 200
            def getheader(self, key): return None
            def read(self, bound): events.append(bound); return b'{"status":"ok"}'
            def close(self): events.append('closed')
        with patch.object(m.resource, 'setrlimit'):
            value, _ = m.request_json(8003, '/health', connection=Connection)
        self.assertEqual(value, {'status':'ok'})
        self.assertEqual(events[0][0], '127.0.0.1')
        self.assertEqual(events[-2:], [131073, 'closed'])
        Connection.status = 302
        with patch.object(m.resource, 'setrlimit'), self.assertRaisesRegex(ValueError, 'HTTP_STATUS_FAILED'):
            m.request_json(8003, '/health', connection=Connection)
        Connection.status = 200
        with patch.object(m.resource, 'setrlimit'), self.assertRaisesRegex(ValueError, 'RESPONSE_LIMIT_FAILED'):
            m.request_json(8003, '/health', max_bytes=2, connection=Connection)
        with self.assertRaisesRegex(ValueError, 'INVALID_ROUTE'):
            m.request_json(8003, 'http://remote', connection=Connection)

    def test_props_checked_template_not_retained(self):
        config = SimpleNamespace(served_model_name='owned', model_path=Path('/fixture/model.gguf'))
        props = {'model_alias':'owned','total_slots':1,'model_path':'/fixture/model.gguf',
                 'default_generation_settings':{'n_ctx':4096},'chat_template':'PUBLIC_TEMPLATE','is_sleeping':False}
        models = {'data':[{'id':'owned','meta':{'n_ctx':4096}}]}
        with patch.object(m, 'checked_file', side_effect=lambda p,r:p), patch.object(m,'TEMPLATE_SHA',m.digest(b'PUBLIC_TEMPLATE')):
            result = m.validate_health_models_props(config, {'status':'ok'}, models, props)
            self.assertNotIn('chat_template', result)
            for key,value in [('model_path','/wrong'),('total_slots',2),('chat_template','CHANGED')]:
                with self.subTest(key=key),self.assertRaises(ValueError):
                    m.validate_health_models_props(config, {'status':'ok'},models,{**props,key:value})

    def test_resource_return_binds_verified_before_after_epoch(self):
        config=SimpleNamespace(model_sha256='a'*64,model_header_report_sha256='b'*64,report_file='guard',
                               max_seconds=1800,port=8003)
        guard={'child_pid':1234,'started_at_utc':'2030-01-01T00:00:00Z','elapsed_seconds':100,
               'minimum_observed_free_mib':15000,'observed_baseline_relative_peak_mib':21000,
               'required_free_floor_mib':7275,'aggregate_increment_limit_mib':28672}
        with patch.object(m,'load_config',return_value=(config,b'{}')), \
             patch.object(m,'raw_context_provenance',return_value={'runtime_variant':m.RUNTIME_VARIANT}), \
             patch.object(m,'binding',return_value={}),patch.object(m,'validate_guard'), \
             patch.object(m,'read_json',return_value=(guard,b'guard-snapshot')), \
             patch.object(m,'epoch',return_value={'process_start_ticks':9999}), \
             patch.object(m,'ordinary_token',return_value=220), \
             patch.object(m,'request_json',return_value=(valid_resource(),1.0)) as request:
            result=m.run_resource_smoke('config','c'*64,runtime_variant=m.RUNTIME_VARIANT,
                context_proof_path='fake',context_proof_sha='d'*64,timeout=900)
        self.assertEqual(result['launch_config_sha256'],'c'*64)
        self.assertEqual(result['pid'],1234)
        self.assertEqual(result['process_start_ticks'],9999)
        self.assertEqual(result['guard_started_at_utc'],guard['started_at_utc'])
        self.assertEqual(request.call_count,1)

    def test_runtime_metadata_exact_evaluator_contract(self):
        config = SimpleNamespace(source_commit='f'*40,binary_sha256='a'*64,source_report_sha256='b'*64,
            build_report_sha256='c'*64,model_sha256='d'*64,model_header_report_sha256='e'*64)
        platform={'compiler':'GCC9.5','cmake':'3.23.5','cuda':'11.8','driver':'535.183.01',
                  'gpu':'A100-PCIE-40GB','gpu_uuid':'GPU-00000000-0000-0000-0000-000000000000'}
        result=m.make_metadata(config,platform,'1'*64,'2'*64,'3'*64)
        self.assertEqual(result['max_model_len'],4096)
        self.assertIs(result['enable_reasoning'],False)
        self.assertEqual(result['reasoning_parser'],'deepseek')
        with self.assertRaises(ValueError):m.make_metadata(config,{**platform,'torch':'not-applicable'},'1'*64,'2'*64,'3'*64)

    def test_bundle_new_directory_no_clobber(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'var/tmp') as directory:
            root=Path(directory); (root/'var/reports').mkdir(parents=True)
            destination=root/'var/reports/new'
            with patch.object(m,'ROOT',root):
                result=m.write_bundle(destination,{'startup.json':b'{"status":"PASS"}\n'})
                self.assertEqual(result['startup.json'],m.digest((destination/'startup.json').read_bytes()))
                with self.assertRaises(ValueError):m.write_bundle(destination,{'startup.json':b'replace'})
                with self.assertRaises(ValueError):m.write_bundle(root/'outside',{'x.json':b'{}'})
                self.assertEqual((destination/'startup.json').read_bytes(),b'{"status":"PASS"}\n')

    def test_actual_build_report_multihop_sonames(self):
        # Real completed build-report shape; CPU filesystem checks, no ELF execution.
        build=json.loads((ROOT/'var/reports/llama-cuda-build-verified.json').read_text())
        binary=ROOT/'var/runtime-build/llama-f072-sm80-cu118/bin/llama-server'
        names={Path(item['path']).name for item in build['runtime_dependencies']}
        self.assertTrue(any(item['target'] != Path(item['real_path']).name
                            for item in build['runtime_dependency_symlinks']))
        m.validate_aliases(binary,build,names)
        wrong=json.loads(json.dumps(build));wrong['runtime_dependency_symlinks'][0]['target']='wrong.so'
        with self.assertRaisesRegex(ValueError,'LIBRARY_ALIAS_MISMATCH'):
            m.validate_aliases(binary,wrong,names)

    def raw_context_fixture(self):
        return {'kind':'NATIVE_CONTEXT_RAW_UNICODE_CPU_PROOF','status':'PASS','gguf_sha256':'a'*64,
                'header_sha256':'ff168aeee125b2934b8b5204c14971915c7555c5dfc660d6fda46c2bf7fc810a',
                'model_inference_calls':0,'max_output_tokens':768,'max_context_tokens':4096,
                'runtime_variant':m.RUNTIME_VARIANT,'reference_kind':m.REFERENCE_KIND,
                'context_tokenizer':'native_raw_unicode_no_nfc_repair','application_input_output_nfc_repair':False,
                'hf_equivalence':json.loads(json.dumps(m.HF_EQUIVALENCE)),
                'raw_reference':dict(m.RAW_REFERENCE),'cpu_build_report_sha256':m.CPU_BUILD_SHA,
                'binary_sha256':m.CPU_BINARY_SHA,'cpu_cpp_source_sha256':m.CPU_CPP_SHA,
                'splits':{name:{'input_count':count,'dataset_sha256':m.CONTEXT_SPLITS[name][1],
                    'max_input_tokens':2232,'max_input_plus_output':3000,'native':{'status':'PASS',
                    'native_tokenization':'PASS_VOCAB_ONLY','tokenizer_metadata_parity':'PASS',
                    'tokenizer_metadata_parity_cases':20}} for name,count in [('exposed120',120),('v2_length80',80)]}}

    def test_actual_original_failure_and_raw_reference_remain_distinct(self):
        proof=self.raw_context_fixture();raw=m.encoded(proof)
        original_reader=m.read_json
        def reader(path):
            return (proof,raw) if path=='future-raw-context' else original_reader(path)
        with patch.object(m,'read_json',side_effect=reader):
            report=m.raw_context_provenance('future-raw-context',m.digest(raw),runtime_variant=m.RUNTIME_VARIANT,
                model_sha=proof['gguf_sha256'],header_sha=proof['header_sha256'])
            self.assertEqual(type(m.ordinary_token()),int)
        self.assertEqual(report['hf_equivalence']['status'],'FAIL')
        self.assertEqual(report['hf_equivalence']['id_match_count'],19)
        self.assertEqual(report['raw_reference']['id_match_count'],20)
        self.assertEqual(report['runtime_variant'],m.RUNTIME_VARIANT)

    def test_raw_provenance_cannot_relabel_hf_or_silently_normalize(self):
        proof=self.raw_context_fixture()
        changes=[('kind','NATIVE_CONTEXT_CPU_PROOF'),('runtime_variant','official-hf'),
                 ('application_input_output_nfc_repair',True),('binary_sha256','9'*64),
                 ('hf_equivalence',{**proof['hf_equivalence'],'status':'PASS'}),
                 ('raw_reference',{**proof['raw_reference'],'fixture_sha256':m.PARITY_SHA})]
        for key,value in changes:
            changed={**proof,key:value};raw=m.encoded(changed)
            with self.subTest(key=key),patch.object(m,'read_json',return_value=(changed,raw)),self.assertRaises(ValueError):
                m.raw_context_provenance('future-raw-context',m.digest(raw),runtime_variant=m.RUNTIME_VARIANT,
                    model_sha=proof['gguf_sha256'],header_sha=proof['header_sha256'])
        with patch.object(m,'read_json') as reader,self.assertRaisesRegex(ValueError,'EXPLICIT_RAW_VARIANT_REQUIRED'):
            m.raw_context_provenance('future-raw-context','0'*64,runtime_variant='auto',model_sha='a'*64,header_sha='b'*64)
        reader.assert_not_called()

    def test_context_proof_cannot_use_smaller_cap_or_different_dataset(self):
        reference=self.raw_context_fixture()
        changes=[('max_output_tokens',512),('max_context_tokens',8192)]
        for split in m.CONTEXT_SPLITS:
            for key,value in [('dataset_sha256','0'*64),('max_input_tokens',2200),('max_input_plus_output',5000)]:
                changed=json.loads(json.dumps(reference));changed['splits'][split][key]=value
                changes.append(('splits',changed['splits']))
        for key,value in changes:
            changed={**reference,key:value};raw=m.encoded(changed)
            with self.subTest(key=key),patch.object(m,'read_json',return_value=(changed,raw)),self.assertRaises(ValueError):
                m.raw_context_provenance('future-raw-context',m.digest(raw),runtime_variant=m.RUNTIME_VARIANT,
                    model_sha=reference['gguf_sha256'],header_sha=reference['header_sha256'])

    def test_all_runtime_entrypoints_reject_provenance_before_http(self):
        config=SimpleNamespace(model_sha256='a'*64,model_header_report_sha256='b'*64,port=8003,served_model_name='owned')
        kwargs={'runtime_variant':m.RUNTIME_VARIANT,'context_proof_path':'not-ready','context_proof_sha':'0'*64}
        with patch.object(m,'load_config',return_value=(config,b'{}')), \
             patch.object(m,'raw_context_provenance',side_effect=ValueError('RAW_CONTEXT_PROVENANCE_MISMATCH')), \
             patch.object(m,'request_json') as http, \
             patch('neurobuild.infrastructure.local_model.LocalRequirementClient') as client, \
             patch.object(m.resource,'setrlimit'):
            for invoke in [lambda:m.capture_startup('config','0'*64,{},**kwargs),
                           lambda:m.run_resource_smoke('config','0'*64,**kwargs),
                           lambda:m.public_smoke(config,**kwargs)]:
                with self.assertRaisesRegex(ValueError,'RAW_CONTEXT_PROVENANCE_MISMATCH'):invoke()
        http.assert_not_called();client.assert_not_called()

    def test_guard_budget_cannot_be_substituted_for_other_config(self):
        config=SimpleNamespace(model_path=Path('/fixture/model.gguf'),served_model_name='owned',
                               max_seconds=1800,estimated_peak_mib=28672,peak_allowance_mib=0,batch_size=2,ubatch_size=1)
        report={'state':'RUNNING','runtime_family':'llama_cpp','native_identity_verified':True,
          'physical_gpu_index':3,'required_cuda_visible_devices':'3','max_model_len':4096,'max_num_seqs':1,
          'batch_size':2,'ubatch_size':1,'served_model_name':'owned','model_path':'/fixture/model.gguf',
          'native_artifacts':{},'enable_reasoning':False,'reasoning_parser':'deepseek',
          'native_output_policy':'DISCARD_STDOUT_STDERR','native_core_dump_limit_bytes':0,
          'preflight':{'allowed':True,'policy':{'estimated_peak_mib':28672},
             'budget':{'estimated_startup_or_inference_peak_mib':28672,'available_model_budget_mib':29098,
                       'required_safety_margin_mib':7275}},
          'minimum_observed_free_mib':15000,'required_free_floor_mib':7275,
          'observed_baseline_relative_peak_mib':21000,'aggregate_increment_limit_mib':28672,
          'peak_allowance_mib':0,'child_pid':1234,'elapsed_seconds':120}
        with patch.object(m,'checked_file',side_effect=lambda p,r:p):
            m.validate_guard(config,report,{})
            for key,value in [('batch_size',1),('batch_size',True),('ubatch_size',2),('ubatch_size',True)]:
                with self.subTest(batch=key,value=value),self.assertRaisesRegex(ValueError,'GUARD_BINDING_MISMATCH'):
                    m.validate_guard(config,{**report,key:value},{})
            for key,value in [('batch_size',1),('ubatch_size',2)]:
                changed=SimpleNamespace(**{**vars(config),key:value})
                with self.subTest(config=key),self.assertRaisesRegex(ValueError,'GUARD_BINDING_MISMATCH'):
                    m.validate_guard(changed,report,{})
            for key,value in [('aggregate_increment_limit_mib',29098),('required_free_floor_mib',6144),('peak_allowance_mib',1024)]:
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'GUARD_BUDGET_MISMATCH'):
                    m.validate_guard(config,{**report,key:value},{})

    def test_public_smoke_one_production_extract_no_body_retention(self):
        from decimal import Decimal
        from neurobuild.domain.contracts import SemanticRequirement,RequirementStatus,MoveFurniture,Length,LengthUnit
        observed=[]
        class FakeClient:
            def __init__(self,*args,**kwargs):observed.append((args,kwargs))
            def extract(self,source,**kwargs):
                observed.append(source)
                return SemanticRequirement(kwargs['requirement_id'],kwargs['project_id'],kwargs['base_revision_id'],
                    source,'검사실 책상',RequirementStatus.READY,MoveFurniture(Length(Decimal(1),LengthUnit.M),Length(Decimal(0),LengthUnit.M)))
        with patch('neurobuild.infrastructure.local_model.LocalRequirementClient',FakeClient),patch.object(m.resource,'setrlimit'),patch.object(m,'raw_context_provenance',return_value={'runtime_variant':m.RUNTIME_VARIANT}):
            result=m.public_smoke(SimpleNamespace(port=8003,served_model_name='owned',model_sha256='a'*64,model_header_report_sha256='b'*64),runtime_variant=m.RUNTIME_VARIANT,context_proof_path='fake',context_proof_sha='0'*64)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(len(observed),2)
        self.assertEqual(observed[0][1]['max_tokens'],768)
        self.assertEqual(observed[0][1]['protocol'],'llama_cpp_json_schema')
        self.assertNotIn('content',result)
        self.assertNotIn('reasoning_content',result)
        self.assertFalse(result['quality_gate_pass'])

if __name__ == '__main__':
    unittest.main()
