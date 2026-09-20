"""Focused CPU/fake-only controls. Never open sockets, processes, models or GPU."""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path('/home/a202192020/NeuroBuild_v2')
spec = importlib.util.spec_from_file_location('gemma4_probe_tested', ROOT / 'var/research/gemma4_runtime_probe.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def config():
    return SimpleNamespace(source_commit='f072b103714dfa1eee531f80b24512faf38e3dd2',
        binary_sha256='a'*64, source_report_sha256='b'*64, build_report_sha256='c'*64,
        model_sha256=m.MODEL_SHA, model_header_report_sha256='d'*64, model_revision=m.REVISION,
        model_path=Path('/fixture/gemma.gguf'), model_header_report='header', port=8003, served_model_name='gemma-owned',
        enable_reasoning=False, batch_size=64, ubatch_size=64, report_file='guard', max_seconds=3600)


def platform():
    return {'compiler':'GCC9.5','cmake':'3.23.5','cuda':'11.8','driver':'535.183.01',
            'gpu':'A100-PCIE-40GB','gpu_uuid':'GPU-00000000-0000-0000-0000-000000000000'}


def cpu_fixture():
    ref = {'path':'var/research/public-proof.json','sha256':m.digest(b'{}')}
    return {'kind':'GEMMA4_NATIVE_CONTRACT_CPU_PROOF','status':'PASS','model_id':m.MODEL_ID,
        'revision':m.REVISION,'gguf_sha256':m.MODEL_SHA,'header_sha256':'d'*64,
        'template_sha256':m.TEMPLATE_SHA,'tokenizer_json_sha256':m.TOKENIZER_SHA,
        'model_inference_calls':0,'application_input_output_nfc_repair':False,
        'max_output_tokens':768,'max_context_tokens':4096,
        'official_tokenizer_parity':{'status':'PASS','case_count':20,'id_match_count':20,
                                   'native_original_roundtrip_count':20},
        'splits':{name:{'input_count':count,'dataset_sha256':sha,'min_input_tokens':2000,
                       'max_input_tokens':2400,'max_input_plus_output':3168}
                  for name,(count,sha) in m.CONTEXT_SPLITS.items()},
        'source_sha256':{path:m.digest((ROOT/path).read_bytes()) for path in m.CPU_SOURCE_PATHS},
        'proof_refs':{name:dict(ref) for name in ('public_contract','vocab_context','tokenizer_fixture')},
        'resource_probe_token':{'text':' ','token_id':236743,'native_token_count':1,'native_roundtrip':True}}


def guard():
    return {'child_pid':1234,'started_at_utc':'2030-01-01T00:00:00Z','elapsed_seconds':100,
            'minimum_observed_free_mib':15000,'observed_baseline_relative_peak_mib':21000,
            'required_free_floor_mib':7275,'aggregate_increment_limit_mib':28672}


def resource_value():
    return {'tokens_evaluated':3328,'tokens_predicted':768,'tokens_cached':4095,
        'truncated':True,'stop':True,'stop_type':'limit','timings/prompt_n':3328,
        'timings/predicted_n':768,'timings/prompt_ms':3000.0,'timings/predicted_ms':20000.0}


class GemmaProbeTests(unittest.TestCase):
    def test_pinned_generic_reuse_excludes_qwen_entrypoints(self):
        self.assertEqual(m.digest(m.BASE_PATH.read_bytes()),m.BASE_SHA)
        for name in ('binding','load_config','validate_guard','epoch','request_json',
                     'resource_payload','validate_resource','write_bundle'):
            self.assertIs(getattr(m,name),getattr(m.base,name))
        for name in ('raw_context_provenance','ordinary_token'):
            self.assertFalse(hasattr(m,name))
        self.assertIsNot(m.capture_startup,m.base.capture_startup)
        self.assertIsNot(m.public_smoke,m.base.public_smoke)

    def validate_cpu(self,proof,*,bad_link=False):
        raw=m.encoded(proof)
        def read(path):
            return (proof,raw) if path=='cpu-proof' else ({},b'changed' if bad_link else b'{}')
        with patch.object(m,'read_json',side_effect=read):
            return m.cpu_provenance(config(),'cpu-proof',m.digest(raw))

    def test_cpu_receipt_scoped_official_parity_and_hash_closure(self):
        report, token = self.validate_cpu(cpu_fixture())
        self.assertEqual(token,236743)
        self.assertEqual(report['official_tokenizer_parity']['id_match_count'],20)
        self.assertNotIn('runtime_variant',report)
        self.assertIs(report['cpu_checks_rerun'],False)
        with self.assertRaisesRegex(ValueError,'REFERENCE_HASH_MISMATCH'):
            self.validate_cpu(cpu_fixture(),bad_link=True)

    def test_cpu_rejects_missing_native_parity_wrong_identity_and_caps(self):
        original=cpu_fixture()
        edits=[('kind','NATIVE_CONTEXT_RAW_UNICODE_CPU_PROOF'),('status','PUBLIC_TEMPLATE_ONLY'),
            ('revision','0'*40),('gguf_sha256','0'*64),('header_sha256','0'*64),
            ('template_sha256',m.base.TEMPLATE_SHA),('tokenizer_json_sha256','0'*64),
            ('model_inference_calls',True),('application_input_output_nfc_repair',True),
            ('max_output_tokens',512),('max_context_tokens',8192),
            ('official_tokenizer_parity',{**original['official_tokenizer_parity'],'id_match_count':19}),
            ('resource_probe_token',{'text':' ','token_id':True,'native_token_count':1,'native_roundtrip':True}),
            ('resource_probe_token',{'text':' ','token_id':262144,'native_token_count':1,'native_roundtrip':True})]
        for key,value in edits:
            with self.subTest(field=key,value=value),self.assertRaises(ValueError):
                self.validate_cpu({**original,key:value})
        for key,value in [('input_count',119),('dataset_sha256','0'*64),
                          ('max_input_tokens',2401),('min_input_tokens',True)]:
            changed=deepcopy(original);changed['splits']['exposed120'][key]=value
            with self.subTest(split_field=key),self.assertRaises(ValueError):self.validate_cpu(changed)
        changed=deepcopy(original);changed['source_sha256']['src/neurobuild/infrastructure/local_model.py']='0'*64
        with self.assertRaisesRegex(ValueError,'SOURCE_HASH_MISMATCH'):self.validate_cpu(changed)
        changed=deepcopy(original);changed['proof_refs']['public_contract']['path']='../outside'
        with self.assertRaisesRegex(ValueError,'REFERENCE_PATH_INVALID'):self.validate_cpu(changed)

    def test_gemma_model_binding_precedes_generic_disk_checks(self):
        good=config()
        with patch.object(m,'binding',return_value={'bound':True}) as generic, \
             patch.object(m,'read_json',return_value=({'file_bytes':m.MODEL_BYTES},b'header')), \
             patch.object(m,'digest',return_value='d'*64):
            self.assertEqual(m.gemma_binding(good),{'bound':True})
            generic.reset_mock()
            for key,value in [('model_sha256','0'*64),('model_revision','0'*40),('enable_reasoning',True),
                              ('batch_size',2),('source_commit','a'*40)]:
                changed=SimpleNamespace(**{**vars(good),key:value})
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'GEMMA_CONFIG_MISMATCH'):
                    m.gemma_binding(changed)
            generic.assert_not_called()

    def test_props_health_models_template_bound_and_raw_body_absent(self):
        cfg=config();template='PUBLIC_SYNTHETIC_TEMPLATE'
        props={'model_alias':cfg.served_model_name,'total_slots':1,'model_path':str(cfg.model_path),
            'default_generation_settings':{'n_ctx':4096},'chat_template':template,'is_sleeping':False}
        models={'data':[{'id':cfg.served_model_name,'meta':{'n_ctx':4096}}]}
        with patch.object(m.base,'checked_file',side_effect=lambda path,root:path), \
             patch.object(m,'TEMPLATE_SHA',m.digest(template.encode())):
            receipt=m.validate_health_models_props(cfg,{'status':'ok'},models,props)
            self.assertNotIn('chat_template',receipt)
            for key,value in [('model_alias','other'),('total_slots',True),('model_path','/other'),
                              ('chat_template','QWEN_TEMPLATE'),('is_sleeping',True)]:
                with self.subTest(field=key),self.assertRaises(ValueError):
                    m.validate_health_models_props(cfg,{'status':'ok'},models,{**props,key:value})
            with self.assertRaises(ValueError):m.validate_health_models_props(cfg,{'status':'loading'},models,props)
            with self.assertRaises(ValueError):m.validate_health_models_props(cfg,{'status':'ok'},{'data':[]},props)

    def test_metadata_is_exact_new_evaluator_contract(self):
        result=m.make_metadata(config(),platform(),'1'*64,'2'*64,'3'*64)
        self.assertEqual(result['quantization'],'Q4_0')
        self.assertEqual(result['chat_template_sha256'],m.TEMPLATE_SHA)
        self.assertEqual(result['gguf_sha256'],m.MODEL_SHA)
        self.assertEqual(result['startup_report_sha256'],'2'*64)
        self.assertIs(result['enable_reasoning'],False)
        self.assertEqual(result['reasoning_parser'],'deepseek')
        with self.assertRaises(ValueError):m.make_metadata(config(),{**platform(),'torch':'none'},'1'*64,'2'*64,'3'*64)

    def test_entrypoints_reject_cpu_gate_before_any_http_or_process(self):
        options={'cpu_proof_path':'missing','cpu_proof_sha':'0'*64}
        with patch.object(m,'load_config',return_value=(config(),b'{}')), \
             patch.object(m,'cpu_provenance',side_effect=ValueError('GEMMA_CPU_PROVENANCE_MISMATCH')), \
             patch.object(m,'epoch') as proc,patch.object(m,'request_json') as http, \
             patch('neurobuild.infrastructure.local_model.LocalRequirementClient') as client, \
             patch.object(m.resource,'setrlimit'):
            for call in [lambda:m.capture_startup('config','1'*64,platform(),**options),
                         lambda:m.public_smoke('config','1'*64,**options),
                         lambda:m.run_resource_smoke('config','1'*64,**options)]:
                with self.assertRaisesRegex(ValueError,'GEMMA_CPU_PROVENANCE_MISMATCH'):call()
        proc.assert_not_called();http.assert_not_called();client.assert_not_called()

    def test_finish_rejects_epoch_change_and_decreasing_clock(self):
        before=guard();first={'process_start_ticks':9999}
        with patch.object(m,'epoch',return_value=first) as proc,patch.object(m,'validate_guard'):
            for key,value in [('child_pid',4567),('started_at_utc','NEW'),('elapsed_seconds',99)]:
                with patch.object(m,'read_json',return_value=({**before,key:value},b'after')), \
                     self.subTest(field=key),self.assertRaisesRegex(ValueError,'GUARD_EPOCH_CHANGED'):
                    m.finish(config(),'1'*64,{},before,b'before',first)
            proc.assert_called_with(unittest.mock.ANY,1234,9999)

    def entry_mocks(self):
        stack=ExitStack();self.addCleanup(stack.close)
        before=guard();first={'process_start_ticks':9999,'pid':1234,'verdict':'PASS','listeners':[]}
        provenance={'model_id':m.MODEL_ID,'cpu_proof_sha256':'9'*64}
        stack.enter_context(patch.object(m,'begin',return_value=(config(),b'{}',provenance,236743,{},before,b'before',first)))
        stack.enter_context(patch.object(m,'epoch',return_value=first))
        stack.enter_context(patch.object(m,'read_json',return_value=({**before,'elapsed_seconds':130},b'after')))
        stack.enter_context(patch.object(m,'validate_guard'))
        return stack

    def test_startup_three_gets_receipt_metadata_hashes_match_exact_bundle(self):
        stack=self.entry_mocks()
        calls=stack.enter_context(patch.object(m,'request_json',return_value=({},.1)))
        stack.enter_context(patch.object(m,'validate_health_models_props',return_value={'health_http_status':200}))
        bundle=m.capture_startup('config','1'*64,platform(),cpu_proof_path='proof',cpu_proof_sha='9'*64)
        self.assertEqual([x.args[1] for x in calls.call_args_list],['/health','/v1/models','/props'])
        self.assertEqual(set(bundle),{'launch_config.json','resource_report.json','listeners.json','startup.json','runtime_metadata.json'})
        startup=json.loads(bundle['startup.json']);metadata=json.loads(bundle['runtime_metadata.json'])
        self.assertEqual(metadata['startup_report_sha256'],m.digest(bundle['startup.json']))
        self.assertEqual(metadata['listener_report_sha256'],m.digest(bundle['listeners.json']))
        self.assertEqual(startup['resource_report_sha256'],m.digest(bundle['resource_report.json']))
        self.assertEqual(startup['model_inference_calls'],0)
        self.assertEqual(startup['launch_config_sha256'],'1'*64)
        self.assertEqual(startup['pid'],1234)
        self.assertEqual(startup['process_start_ticks'],9999)
        self.assertEqual(startup['guard_started_at_utc'],guard()['started_at_utc'])

    def test_public_single_production_client_profile_no_text_retained(self):
        from decimal import Decimal
        from neurobuild.domain.contracts import SemanticRequirement,RequirementStatus,MoveFurniture,Length,LengthUnit
        stack=self.entry_mocks();seen=[]
        class Client:
            def __init__(self,*args,**kwargs):seen.append(kwargs)
            def extract(self,source,**kwargs):
                seen.append(source)
                return SemanticRequirement(kwargs['requirement_id'],kwargs['project_id'],kwargs['base_revision_id'],
                    source,'검사실 책상',RequirementStatus.READY,
                    MoveFurniture(Length(Decimal(1),LengthUnit.M),Length(Decimal(0),LengthUnit.M)))
        stack.enter_context(patch('neurobuild.infrastructure.local_model.LocalRequirementClient',Client))
        result=m.public_smoke('config','1'*64,cpu_proof_path='proof',cpu_proof_sha='9'*64)
        self.assertEqual(result['status'],'PASS');self.assertEqual(len(seen),2)
        self.assertEqual(seen[0]['sampling_profile'],'gemma4_nonthinking_llama_cpp')
        self.assertEqual(seen[0]['protocol'],'llama_cpp_json_schema')
        self.assertEqual(seen[0]['max_tokens'],768);self.assertEqual(seen[1],m.PUBLIC_SOURCE)
        self.assertNotIn(m.PUBLIC_SOURCE,json.dumps(result,ensure_ascii=False))
        self.assertFalse(result['quality_gate_pass']);self.assertFalse(result['generated_body_retained'])
        self.assertEqual(result['http_calls_attempted'],1)

    def test_resource_one_bounded_scalar_post_and_epoch_receipt(self):
        stack=self.entry_mocks()
        calls=stack.enter_context(patch.object(m,'request_json',return_value=(resource_value(),25.0)))
        result=m.run_resource_smoke('config','1'*64,cpu_proof_path='proof',cpu_proof_sha='9'*64)
        calls.assert_called_once();args=calls.call_args
        self.assertEqual(args.args[1],'/completion');self.assertEqual(args.kwargs['max_bytes'],8192)
        self.assertEqual(set(args.args[2]['prompt']),{236743});self.assertEqual(len(args.args[2]['prompt']),3328)
        self.assertEqual(args.args[2]['n_predict'],768);self.assertFalse(args.args[2]['cache_prompt'])
        self.assertNotIn('grammar',args.args[2]);self.assertNotIn('content',args.args[2]['response_fields'])
        self.assertEqual(result['tokens_cached'],4095);self.assertEqual(result['pid'],1234)
        self.assertEqual(result['process_start_ticks'],9999);self.assertEqual(result['launch_config_sha256'],'1'*64)
        self.assertTrue(result['lifetime_aggregate_values_not_probe_isolated'])
        self.assertFalse(result['quality_evaluation']);self.assertNotIn('prompt',result)


if __name__=='__main__':unittest.main()
