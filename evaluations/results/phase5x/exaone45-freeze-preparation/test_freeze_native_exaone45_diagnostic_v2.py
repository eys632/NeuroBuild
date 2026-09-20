"""New EXAONE freeze metadata/epoch links only. All runtime access is fake."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace, ModuleType
from contextlib import redirect_stdout
from io import StringIO
import sys
from unittest.mock import patch
import ast,hashlib,importlib.util,json,unittest

spec=importlib.util.spec_from_file_location('exaone_freezer_v2',Path(__file__).with_name('freeze_native_exaone45_diagnostic_v2.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class SavedEvidenceTests(unittest.TestCase):
    def setUp(self):
        # Existing small CPU receipts only; never datasets, responses or weights.
        self.cpu=json.loads((m.ROOT/m.CPU).read_bytes())
        self.provenance=json.loads((m.ROOT/'var/research/exaone45-runtime-v4-cpu-consumer-proof.json').read_bytes())['consumed_provenance']
        self.cfg=SimpleNamespace(max_seconds=7200,port=8003,estimated_peak_mib=28672,peak_allowance_mib=0,batch_size=64,ubatch_size=64,report_file=Path('var/reports/FAKE-NOT-READ.json'))
        self.hashes={m.CPU:m.CPU_SHA,m.CPU_ARCHIVED_PROOF:m.CPU_SHA,m.START+'launch_config.json':m.CONFIG_SHA,m.START+'startup.json':'a'*64,m.START+'listeners.json':'b'*64,m.START+'resource_report.json':'c'*64}
        self.guard={'native_artifacts':{'chat_template_override':{'path':m.EFFECTIVE_TEMPLATE,'sha256':m.EFFECTIVE_TEMPLATE_SHA}},'child_pid':1234,'started_at_utc':'2000-01-01T00:00:00+00:00','required_free_floor_mib':7275,'aggregate_increment_limit_mib':28672}
        epoch={'launch_config_sha256':m.CONFIG_SHA,'pid':1234,'process_start_ticks':5678,'guard_started_at_utc':self.guard['started_at_utc']}
        startup={**deepcopy(self.provenance),**epoch,'kind':'EXAONE45_NATIVE_STARTUP_HTTP_PROOF','status':'PASS','http_get_calls':3,'model_inference_calls':0,'raw_http_bodies_saved':False,'embedded_chat_template_sha256':m.EMBEDDED_TEMPLATE_SHA,'embedded_chat_template_bytes':5930,'effective_chat_template_sha256':m.EFFECTIVE_TEMPLATE_SHA,'effective_chat_template_bytes':5829,'chat_template_sha256':m.EFFECTIVE_TEMPLATE_SHA,'props_reported_template_sha256':'b8bc1ef1b1fcd30cdd28fe7655bf79020aec666142107c01231b7b59f15cb1ef','props_reported_template_bytes':5828,'resource_report_sha256':'c'*64}
        self.expected_metadata={k:'FAKE' for k in ('compiler','cmake','cuda','driver','gpu','gpu_uuid')}
        self.expected_metadata.update(chat_template_sha256=m.EFFECTIVE_TEMPLATE_SHA,startup_report_sha256='a'*64,listener_report_sha256='b'*64,launch_config_sha256=m.CONFIG_SHA)
        public={**deepcopy(self.provenance),**epoch,'kind':'EXAONE45_NATIVE_PUBLIC_PRODUCTION_SMOKE','status':'PASS','http_calls_attempted':1,'quality_gate_pass':False,'generated_body_retained':False,'sampling_profile':m.PROFILE}
        resource={**deepcopy(self.provenance),**epoch,'kind':'EXAONE45_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE','status':'PASS','http_post_calls':1,'guard_required_free_floor_mib':7275,'guard_aggregate_increment_limit_mib':28672,'guard_minimum_observed_free_mib':17000,'guard_aggregate_peak_mib':20000}
        listeners={'verdict':'PASS','all_loopback':True,'snapshot_complete':True,'uid':m.os.getuid(),'pid':1234,'process_start_ticks':5678}
        self.records={m.CPU:self.cpu,m.START+'startup.json':startup,m.START+'runtime_metadata.json':deepcopy(self.expected_metadata),m.PUBLIC:public,m.RESOURCE:resource,m.START+'resource_report.json':self.guard,m.START+'listeners.json':listeners}
        self.probe=SimpleNamespace(load_config=lambda *a:(self.cfg,b''),cpu_provenance=lambda *a:(deepcopy(self.provenance),582),make_metadata=lambda *a:deepcopy(self.expected_metadata),base=SimpleNamespace(RESOURCE_FIELDS=()),validate_resource=lambda v:None,exaone_binding=lambda c:deepcopy(self.guard['native_artifacts']),validate_guard=lambda *a:None)

    def check(self):
        with patch.object(m,'load',side_effect=lambda name:deepcopy(self.records[name])),patch.object(m,'digest',side_effect=lambda name:self.hashes[name]):
            return m.validate_saved(self.probe,m.CPU_SHA)

    def test_complete_fake_bundle_matches_without_live_access(self):
        self.assertEqual(self.check()[0],self.cfg)

    def test_main_drycheck_validates_fake_evidence_without_publication(self):
        self.cfg.served_model_name='FAKE_EXAONE'
        self.cfg.source_report=Path('var/reports/FAKE_SOURCE.json')
        self.cfg.build_report=Path('var/reports/FAKE_BUILD.json')
        self.cfg.model_header_report=Path('var/reports/FAKE_HEADER.json')
        self.cfg.chat_template_path=Path(m.EFFECTIVE_TEMPLATE)
        startup=self.records[m.START+'startup.json']
        replay_proof=json.loads((m.ROOT/m.REPLAY_PROOF).read_bytes())
        hashes=dict(m.FIXED)
        hashes.update({m.CPU:m.CPU_SHA,m.CPU_ARCHIVED_PROOF:m.CPU_SHA,m.REPLAY:m.REPLAY_SHA,m.REPLAY_PROOF:m.REPLAY_PROOF_SHA})
        for ref in self.cpu['proof_refs'].values():hashes[ref['path']]=ref['sha256']
        def digest(name):return hashes.get(name,'f'*64)
        def load(name):
            if name==m.REPLAY_PROOF:return replay_proof
            if name==m.SELFTEST:return {'status':'PASS','helper_sha256':'f'*64,'test_source_sha256':'f'*64}
            raise AssertionError('Unexpected main read')
        fake_client=ModuleType('neurobuild.infrastructure.local_model')
        fake_client.LocalRequirementClient=lambda *a,**k:SimpleNamespace(sampling_parameters=deepcopy(m.SAMPLING),enable_thinking=False)
        output=SimpleNamespace(exists=lambda:False,is_symlink=lambda:False,open=lambda *a:(_ for _ in ()).throw(AssertionError('PUBLICATION_FORBIDDEN')))
        observation={'guard_max_seconds':7200,'elapsed_seconds_at_freeze':20,'remaining_seconds_at_freeze':7180,'first_request_requires_fresh_root_time_decision':True}
        stream=StringIO()
        with patch.object(m,'OUT',output),patch.object(m,'load',side_effect=load),patch.object(m,'digest',side_effect=digest),patch.object(m,'validate_fixed',return_value=({'source_sha256':{}},{'sha256':{}})),patch.object(m,'import_probe',return_value=self.probe),patch.object(m,'validate_saved',return_value=(self.cfg,self.provenance,self.cpu,startup,{},self.guard)),patch.object(m,'validate_current',return_value=(self.guard,observation)) as current,patch.object(m,'collect_files',return_value=set(hashes)),patch.object(m.subprocess,'check_output',return_value='1'*40),patch.dict(sys.modules,{'neurobuild.infrastructure.local_model':fake_client}),patch.object(sys,'argv',['freezer','--cpu-proof-sha256',m.CPU_SHA,'--dry-check']),patch.dict(m.os.environ,{'CUDA_VISIBLE_DEVICES':''}),redirect_stdout(stream):
            m.main()
        self.assertEqual(current.call_count,2)
        self.assertEqual(json.loads(stream.getvalue())['status'],'ACTUAL_PREREQUISITES_PASS_NOT_FROZEN')

    def test_original_blocked_draft_is_preserved(self):
        path=Path(__file__).with_name('freeze_native_exaone45_diagnostic.py')
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),'e59e33cd18a7ac8048af31b3d6584543c77006d43748982a284d5239951ca652')

    def test_cpu_archive_link_must_match_exact_aggregate(self):
        self.hashes[m.CPU_ARCHIVED_PROOF]='0'*64
        with self.assertRaisesRegex(ValueError,'CPU_ARCHIVE_LINK'):self.check()

    def test_original_effective_props_templates_cannot_be_conflated(self):
        original=deepcopy(self.records[m.START+'startup.json'])
        for key,value in [('embedded_chat_template_sha256',m.EFFECTIVE_TEMPLATE_SHA),('effective_chat_template_sha256',m.EMBEDDED_TEMPLATE_SHA),('props_reported_template_sha256',m.EFFECTIVE_TEMPLATE_SHA),('props_reported_template_bytes',5829)]:
            self.records[m.START+'startup.json']=deepcopy(original);self.records[m.START+'startup.json'][key]=value
            with self.assertRaisesRegex(ValueError,'TEMPLATE_REPRESENTATION'):self.check()

    def test_cpu_scope_cannot_be_relabeled_official_success(self):
        original=deepcopy(self.cpu)
        for key,value in [('application_input_output_nfc_repair',True),('runtime_variant',m.TEMPLATE_VARIANT)]:
            self.records[m.CPU]=deepcopy(original);self.records[m.CPU][key]=value
            with self.assertRaises(ValueError):self.check()
        self.records[m.CPU]=deepcopy(original);self.records[m.CPU]['official_hf_equivalence']['status']='PASS'
        with self.assertRaisesRegex(ValueError,'ORIGINAL_FAILURE'):self.check()

    def test_every_stage_must_have_actual_pass(self):
        for path in (m.START+'startup.json',m.PUBLIC,m.RESOURCE):
            self.records[path]['status']='FAIL'
            with self.assertRaises(ValueError):self.check()
            self.records[path]['status']='PASS'

    def test_metadata_and_receipt_hashes_must_bind(self):
        original=deepcopy(self.expected_metadata)
        for key in ('startup_report_sha256','listener_report_sha256','launch_config_sha256','compiler'):
            self.records[m.START+'runtime_metadata.json']=deepcopy(original);self.records[m.START+'runtime_metadata.json'][key]='0'*64
            with self.assertRaises(ValueError):self.check()

    def test_all_three_receipts_share_same_exact_epoch(self):
        for path in (m.START+'startup.json',m.PUBLIC,m.RESOURCE):
            original=deepcopy(self.records[path])
            for key,value in [('launch_config_sha256','0'*64),('pid',9999),('process_start_ticks',1),('guard_started_at_utc','DIFFERENT')]:
                self.records[path]=deepcopy(original);self.records[path][key]=value
                with self.assertRaises(ValueError):self.check()
            self.records[path]=original

    def test_guard_two_field_override_cannot_be_cpu_five_field_map(self):
        self.guard['native_artifacts']['chat_template_override']=deepcopy(self.cpu['chat_template_override'])
        with self.assertRaisesRegex(ValueError,'GUARD_OVERRIDE'):self.check()

    def test_each_receipt_must_retain_full_cpu_provenance(self):
        for path in (m.START+'startup.json',m.PUBLIC,m.RESOURCE):
            self.records[path]['official_hf_equivalence']['status']='PASS'
            with self.assertRaisesRegex(ValueError,'CPU_PROVENANCE'):self.check()
            self.records[path]['official_hf_equivalence']=deepcopy(self.provenance['official_hf_equivalence'])

    def test_resource_floor_peak_and_fixed_config_checked(self):
        original=deepcopy(self.records[m.RESOURCE])
        for key,value in [('guard_aggregate_peak_mib',28673),('guard_minimum_observed_free_mib',7274),('guard_aggregate_increment_limit_mib',29098)]:
            self.records[m.RESOURCE]=deepcopy(original);self.records[m.RESOURCE][key]=value
            with self.assertRaisesRegex(ValueError,'RESOURCE_BUDGET'):self.check()
        self.records[m.RESOURCE]=original;self.cfg.max_seconds=7201
        with self.assertRaisesRegex(ValueError,'CONFIG_PLAN'):self.check()

    def test_public_body_retention_or_extra_call_rejected(self):
        self.records[m.PUBLIC]['generated_body_retained']=True
        with self.assertRaisesRegex(ValueError,'PUBLIC_SMOKE'):self.check()
        self.records[m.PUBLIC]['generated_body_retained']=False;self.records[m.PUBLIC]['http_calls_attempted']=2
        with self.assertRaisesRegex(ValueError,'PUBLIC_SMOKE'):self.check()

    def test_only_expected_small_cpu_refs_and_no_path_escape(self):
        with patch.object(m,'digest',side_effect=lambda name:next(r['sha256'] for r in [*self.cpu['proof_refs'].values(),self.cpu['official_hf_equivalence']['proof_ref'],self.cpu['raw_reference']['proof_ref'],self.cpu['official_reference_fixture_ref']] if r['path']==name)):
            self.assertEqual(len(m.cpu_references(self.cpu)),6)
        bad=deepcopy(self.cpu);bad['raw_reference']['proof_ref']['path']='../OUTSIDE'
        with patch.object(m,'digest',return_value='0'*64),self.assertRaises(ValueError):m.cpu_references(bad)

if __name__=='__main__':unittest.main()
