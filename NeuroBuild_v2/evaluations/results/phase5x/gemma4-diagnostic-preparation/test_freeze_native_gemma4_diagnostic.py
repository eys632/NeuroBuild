"""Synthetic metadata tests only; no real proof, dataset, process or model calls."""
import copy
import importlib.util
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('gemma_freezer',Path(__file__).with_name('freeze_native_gemma4_diagnostic.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class FreezeTests(unittest.TestCase):
    def fixture(self):
        config=SimpleNamespace(max_seconds=7200,port=8003,estimated_peak_mib=28672,peak_allowance_mib=0,
                               batch_size=64,ubatch_size=64,report_file='var/reports/synthetic.json')
        provenance={'cpu_proof_sha256':'a'*64,'sampling_profile':m.PROFILE}
        template='ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4'
        cpu={'enable_thinking':False,'gpu_or_http_calls':0,'template_sha256':template,'normalization_limitation':{
            'official_hf_literal_u2581_raw_roundtrip':False,'global_unicode_roundtrip_guarantee':False,
            'input_output_repair':False}}
        epoch={'launch_config_sha256':m.CONFIG_SHA,'pid':123,'process_start_ticks':456,
               'guard_started_at_utc':'2026-09-20T00:00:00+00:00'}
        startup={**provenance,**epoch,'kind':'GEMMA4_NATIVE_STARTUP_HTTP_PROOF','status':'PASS',
                 'http_get_calls':3,'model_inference_calls':0,'raw_http_bodies_saved':False,
                 'chat_template_sha256':template,'embedded_chat_template_sha256':template,
                 'embedded_chat_template_bytes':18683,'props_reported_template_bytes':18682,
                 'props_reported_template_sha256':'6a1015c47ccfcfa67c3b772385bccee357a4d37c3cda37bd202e9047f391ab82',
                 'resource_report_sha256':'g'*64}
        metadata={key:'synthetic' for key in ('compiler','cmake','cuda','driver','gpu','gpu_uuid')}
        metadata.update(startup_report_sha256='s'*64,listener_report_sha256='l'*64,
                        launch_config_sha256=m.CONFIG_SHA)
        public={**provenance,**epoch,'kind':'GEMMA4_NATIVE_PUBLIC_PRODUCTION_SMOKE','status':'PASS',
                'http_calls_attempted':1,'quality_gate_pass':False,'generated_body_retained':False,
                'sampling_profile':m.PROFILE}
        resource={**provenance,**epoch,'kind':'GEMMA4_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE','status':'PASS',
                  'http_post_calls':1,'guard_required_free_floor_mib':7275,'guard_aggregate_increment_limit_mib':28672,
                  'guard_minimum_observed_free_mib':9000,'guard_aggregate_peak_mib':27373}
        guard={'child_pid':123,'started_at_utc':epoch['guard_started_at_utc'],
               'required_free_floor_mib':7275,'aggregate_increment_limit_mib':28672,'elapsed_seconds':100}
        listeners={'verdict':'PASS','all_loopback':True,'snapshot_complete':True,'uid':os.getuid(),
                   'pid':123,'process_start_ticks':456}
        docs={m.CPU:cpu,m.START+'startup.json':startup,m.START+'runtime_metadata.json':metadata,
              m.PUBLIC:public,m.RESOURCE:resource,m.START+'resource_report.json':guard,
              m.START+'listeners.json':listeners}
        hashes={m.CPU:'a'*64,m.CPU_ARCHIVED_PROOF:'a'*64,m.START+'startup.json':'s'*64,m.START+'runtime_metadata.json':'m'*64,
                m.START+'listeners.json':'l'*64,m.START+'resource_report.json':'g'*64,
                m.START+'launch_config.json':m.CONFIG_SHA}
        observed=[]
        probe=SimpleNamespace(load_config=lambda *_:(config,b''),cpu_provenance=lambda *_:(provenance,42),
            make_metadata=lambda *_:copy.deepcopy(metadata),validate_resource=lambda _:observed.append('resource'),
            gemma_binding=lambda _:{'synthetic':True},validate_guard=lambda *_:observed.append('guard'),
            base=SimpleNamespace(RESOURCE_FIELDS=()),read_json=lambda _:(copy.deepcopy(guard),b''),
            epoch=lambda *_:observed.append('own_epoch'))
        return config,probe,docs,hashes,observed

    def validate(self,probe,docs,hashes):
        with patch.object(m,'load',side_effect=lambda name:copy.deepcopy(docs[name])),\
             patch.object(m,'digest',side_effect=lambda name:hashes[name]):
            return m.validate_saved(probe,'a'*64)

    def test_saved_bundle_pass_is_no_live_probe(self):
        config,probe,docs,hashes,calls=self.fixture()
        self.validate(probe,docs,hashes)
        self.assertEqual(calls,['resource','guard'])

    def test_unknown_cpu_normalization_limit_is_not_promoted(self):
        for key in ('official_hf_literal_u2581_raw_roundtrip','global_unicode_roundtrip_guarantee','input_output_repair'):
            with self.subTest(key=key):
                _,probe,docs,hashes,_=self.fixture();docs[m.CPU]['normalization_limitation'][key]=True
                with self.assertRaisesRegex(ValueError,'NORMALIZATION_LIMITATION_MISSING'):
                    self.validate(probe,docs,hashes)

    def test_config_and_cpu_pin_cannot_drift(self):
        config,probe,docs,hashes,_=self.fixture();config.max_seconds=14400
        with self.assertRaisesRegex(ValueError,'CONFIG_PLAN_CHANGED'):self.validate(probe,docs,hashes)
        _,probe,docs,hashes,_=self.fixture();hashes[m.CPU]='b'*64
        with self.assertRaisesRegex(ValueError,'CPU_PIN_MISMATCH'):self.validate(probe,docs,hashes)

    def test_archived_cpu_exactlink(self):
        _,probe,docs,hashes,calls=self.fixture()
        self.validate(probe,docs,hashes)
        calls.clear();hashes[m.CPU_ARCHIVED_PROOF]='b'*64
        with self.assertRaisesRegex(ValueError,'CPU_ARCHIVE_LINK_MISMATCH'):
            self.validate(probe,docs,hashes)
        self.assertEqual(calls,[])

    def test_embedded_and_props_template_are_separately_exact(self):
        _,probe,docs,hashes,_=self.fixture()
        self.validate(probe,docs,hashes)
        docs[m.START+'startup.json']['props_reported_template_sha256']=docs[m.CPU]['template_sha256']
        with self.assertRaisesRegex(ValueError,'TEMPLATE_REPRESENTATION_MISMATCH'):
            self.validate(probe,docs,hashes)
        _,probe,docs,hashes,_=self.fixture();docs[m.START+'startup.json']['props_reported_template_bytes']=18681
        with self.assertRaisesRegex(ValueError,'TEMPLATE_REPRESENTATION_MISMATCH'):
            self.validate(probe,docs,hashes)

    def test_hash_and_epoch_mismatches_reject(self):
        for name,key,value in [(m.START+'startup.json','resource_report_sha256','x'*64),
                (m.PUBLIC,'pid',999),(m.RESOURCE,'process_start_ticks',999),
                (m.START+'listeners.json','all_loopback',False)]:
            with self.subTest(name=name,key=key):
                _,probe,docs,hashes,_=self.fixture();docs[name][key]=value
                with self.assertRaises(ValueError):self.validate(probe,docs,hashes)

    def test_no_extra_public_calls_or_body_retention(self):
        for key,value in [('http_calls_attempted',2),('generated_body_retained',True),('quality_gate_pass',True)]:
            _,probe,docs,hashes,_=self.fixture();docs[m.PUBLIC][key]=value
            with self.assertRaisesRegex(ValueError,'PUBLIC_SMOKE_REQUIRED'):self.validate(probe,docs,hashes)

    def test_resource_unsafe_peak_and_free_floor_reject(self):
        for key,value in [('guard_aggregate_peak_mib',28673),('guard_minimum_observed_free_mib',7274)]:
            _,probe,docs,hashes,_=self.fixture();docs[m.RESOURCE][key]=value
            with self.assertRaisesRegex(ValueError,'RESOURCE_BUDGET_CHANGED'):self.validate(probe,docs,hashes)

    def test_live_observation_has_no_invented_completion_guarantee(self):
        config,probe,docs,_,calls=self.fixture();startup=docs[m.START+'startup.json'];guard=docs[m.START+'resource_report.json']
        _,obs=m.validate_current(probe,config,startup,{},guard)
        self.assertEqual(obs['remaining_seconds_at_freeze'],7100)
        self.assertIs(obs['first_request_requires_fresh_root_time_decision'],True)
        self.assertEqual(calls,['guard','own_epoch'])
        guard['elapsed_seconds']=float('nan')
        with self.assertRaisesRegex(ValueError,'GUARD_TIME_INVALID'):m.validate_current(probe,config,startup,{},guard)

    def test_json_duplicate_and_weight_paths_rejected_without_weight_read(self):
        with tempfile.TemporaryDirectory(dir=m.ROOT/'var') as tmp:
            folder=Path(tmp);duplicate=folder/'duplicate.json';duplicate.write_text('{"x":1,"x":2}')
            with self.assertRaisesRegex(ValueError,'JSON_DUPLICATE_KEY'):m.load(duplicate)
            fake_weight=folder/'fake.gguf';fake_weight.write_bytes(b'no actual weights')
            with self.assertRaisesRegex(ValueError,'PAYLOAD_OR_LARGE_ARTIFACT_FORBIDDEN'):m.digest(fake_weight)

    def test_incomplete_prerequisite_creates_no_freeze(self):
        with tempfile.TemporaryDirectory(dir=m.ROOT/'var') as tmp:
            destination=Path(tmp)/'new-freeze.json'
            with patch.object(m,'OUT',destination),patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':''}),\
                 patch.object(m.sys,'argv',['freezer','--cpu-proof-sha256','a'*64]),\
                 patch.object(m,'validate_fixed',return_value=({},{})),\
                 patch.object(m,'import_probe',return_value=object()),\
                 patch.object(m,'validate_saved',side_effect=ValueError('CPU_MISSING')):
                with self.assertRaisesRegex(ValueError,'CPU_MISSING'):m.main()
            self.assertFalse(destination.exists())


if __name__=='__main__':
    unittest.main()
