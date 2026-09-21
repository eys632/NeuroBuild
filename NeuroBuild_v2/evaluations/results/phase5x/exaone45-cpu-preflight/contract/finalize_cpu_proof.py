"""Bind completed scalar receipts for the explicit raw-Unicode override variant.

No tokenizer/native executable/dataset read, no inferred or repaired PASS.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json
ROOT=Path('/home/a202192020/NeuroBuild_v2');BASE=ROOT/'var/research/native-exaone45-contract'
HELPER_SHA='481a40c8c6372aadb1e146b977f90ea61231fca81a87fd3c9ecb02f32ffd892e'
LAUNCHER_SHA='6a58ee1ea09636df182125da4a4a2711012e6c53f5f90c06548a63b9915369ed'
OVERRIDE_SHA='7de6c8ba3df6db54564c7a63385cc29572c0a616d5848961e969ecbb8c349851'
ORIGINAL_SHA='e4ece7acc79ba82121d4d57791fb7ecb796e39185087197377da5d2286bec0e5'
TOKENIZER_SHA='0bd798efa30739e209d51f36cfc2f0a636711e37ad9d69b77e4e5c8ca5f09fab'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--context-proof-sha',required=True);args=parser.parse_args()
 assert sha(BASE/'raw_context_check.py')==HELPER_SHA
 s=importlib.util.spec_from_file_location('ex_raw_context_metadata',BASE/'raw_context_check.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 context=json.loads(m.read_bound(BASE/'vocab-context-raw-proof.json',args.context_proof_sha,1024*1024))
 assert context['kind']=='EXAONE45_NATIVE_RAW_VOCAB_CONTEXT_CPU_PROOF' and context['status']=='PASS'
 assert context['runtime_variant']==m.VARIANT and context['helper_sha256']==HELPER_SHA
 assert context['model_id']==m.MODEL_ID and context['revision']==m.REVISION and context['gguf_sha256']==m.MODEL_SHA and context['header_sha256']==m.HEADER_SHA
 assert context['source_sha256']==m.SOURCE_SHA256 and context['input_bodies_gold_token_ids_saved'] is False and context['gold_fields_scored'] is False
 for rel,h in m.SOURCE_SHA256.items():m.read_bound(ROOT/rel,h,2*1024**2)
 m.read_bound(ROOT/'scripts/llama_server.py',LAUNCHER_SHA,128*1024)
 override=ROOT/'runtime/templates/exaone45-continue-free.jinja'
 assert len(m.read_bound(override,OVERRIDE_SHA,65536))==5829
 for name,h in m.PINS.items():m.read_bound(BASE/name,h,2*1024**2)
 for rel,h in json.loads((BASE/'build-v5.json').read_text())['pinned_inputs'].items():assert sha(ROOT/rel)==h
 assert context['build_report_sha256']==sha(BASE/'build-v5.json') and context['binary_sha256']==sha(BASE/'exaone45-cpu-validator-v5')
 assert context['source_pin']=='f072b103714dfa1eee531f80b24512faf38e3dd2'
 assert set(context['splits'])==set(m.SPLITS) and len(context['native_checks'])==2
 for (name,(path,count,digest)),native in zip(m.SPLITS.items(),context['native_checks'],strict=True):
  m.validate_raw(0,native,count);item=context['splits'][name]
  assert item['input_count']==count and item['dataset_sha256']==digest
  assert all(item[k]==native[k] for k in ['min_input_tokens','max_input_tokens','max_input_plus_output'])
  assert native['effective_override_vocab_render_exact'] is True
 raw_ref=context['raw_public_proof_ref'];assert raw_ref['path']==str((BASE/'raw-vocab-proof.json').relative_to(ROOT))
 raw=json.loads(m.read_bound(ROOT/raw_ref['path'],raw_ref['sha256'],1024*1024))
 assert raw['status']=='PASS' and raw['official_native_failure_sha256']==m.PINS['public-vocab-proof.json'] and raw['raw_reference_sha256']==m.PINS['raw-reference-diagnostic.json']
 m.validate_raw(raw['exit_code'],raw['native'],1)
 original=json.loads((BASE/'public-vocab-proof.json').read_text());assert original['status']=='FAIL' and original['official_reference_native_id_mismatch_indices']==[11,12]
 assert original['native']['tokenizer_id_match_count']==18 and original['native']['tokenizer_native_raw_roundtrip_count']==20 and original['native']['tokenizer_reference_ids_raw_roundtrip_count']==18
 fixture=json.loads((BASE/'raw-reference-diagnostic.json').read_text());official_fixture=json.loads((BASE/'official-tokenizer-fixture.json').read_text())
 assert fixture['official_fixture_sha256']==m.PINS['official-tokenizer-fixture.json'] and fixture['official_tokenizer_sha256']==TOKENIZER_SHA
 assert fixture['reference_kind']=='official_metadata_with_only_NFC_normalizer_disabled' and fixture['case_count']==20 and fixture['raw_roundtrip_count']==20
 assert [x['text'] for x in fixture['tokenizer_parity']]==[x['text'] for x in official_fixture['tokenizer_parity']]
 public=json.loads((BASE/'public-proof-v3.json').read_text());assert public['status']=='PASS' and public['template_reference_cases']==18
 assert public['official_original_derived_reference_byte_equal'] is True and public['candidate_template_sha256']==OVERRIDE_SHA and public['official_embedded_template_sha256']==ORIGINAL_SHA
 assert public['native']['derived_native_system_and_user_exact'] is True and public['native']['derived_native_prompt_equals_official_reference'] is True
 token=context['resource_probe_token'];assert token=={'text':' ','token_id':582,'native_token_count':1,'native_roundtrip':True}
 assert all(n['resource_probe_token_id']==582 for n in context['native_checks'])
 def ref(name):return {'path':str((BASE/name).relative_to(ROOT)),'sha256':sha(BASE/name)}
 proof={'kind':'EXAONE45_NATIVE_CONTRACT_CPU_PROOF','status':'PASS','at_utc':datetime.now(timezone.utc).isoformat(),
  'runtime_variant':m.VARIANT,'template_proof_variant':'exaone45-gguf-continue-free-korean-v1',
  'model_id':m.MODEL_ID,'revision':m.REVISION,'gguf_sha256':m.MODEL_SHA,'header_sha256':m.HEADER_SHA,
  'source_pin':context['source_pin'],'protocol':'llama_cpp_json_schema','sampling_profile':'exaone45_nonthinking_llama_cpp',
  'cpu_binary_sha256':sha(BASE/'exaone45-cpu-validator-v5'),'cpu_cpp_source_sha256':sha(BASE/'validator_v5.cpp'),
  'cpu_build_report_sha256':sha(BASE/'build-v5.json'),'runtime_launcher_sha256':LAUNCHER_SHA,
  'template_sha256':OVERRIDE_SHA,'original_embedded_template_sha256':ORIGINAL_SHA,'tokenizer_json_sha256':TOKENIZER_SHA,
  'chat_template_override':{'path':str(override.relative_to(ROOT)),'sha256':OVERRIDE_SHA,'bytes':5829,
   'original_embedded_template_sha256':ORIGINAL_SHA,'transform':'continue-free-system-message-branch-v1'},
  'template_render_parity':{'status':'PASS','reference_cases':18,'official_original_derived_reference_byte_equal':True,
   'derived_native_system_and_user_exact':True,'derived_native_prompt_equals_official_reference':True,'proof_ref':ref('public-proof-v3.json')},
  'official_hf_equivalence':{'status':'FAIL','case_count':20,'id_match_count':18,'mismatch_indices':[11,12],
   'native_raw_roundtrip_count':20,'official_ids_raw_roundtrip_count':18,'proof_ref':ref('public-vocab-proof.json')},
  'raw_reference':{'reference_kind':'official_metadata_with_only_NFC_normalizer_disabled','fixture_ref':ref('raw-reference-diagnostic.json'),
   'proof_ref':ref('raw-vocab-proof.json'),'case_count':20,'id_match_count':20,'native_raw_roundtrip_count':20,
   'official_hf_equivalence':'NOT_ASSERTED_BY_DERIVED_REFERENCE'},
  'official_reference_fixture_ref':ref('official-tokenizer-fixture.json'),
  'context_tokenizer':'native_raw_unicode_no_nfc_repair','application_input_output_nfc_repair':False,
  'enable_thinking':False,'model_inference_calls':0,'gpu_or_http_calls':0,'max_output_tokens':768,'max_context_tokens':4096,
  'splits':context['splits'],'resource_probe_token':token,'source_sha256':m.SOURCE_SHA256,
  'proof_refs':{key:ref(name) for key,name in [('public_contract','public-proof-v3.json'),('vocab_context','vocab-context-raw-proof.json'),('tokenizer_fixture','raw-reference-diagnostic.json')]},
  'normalization_limitation':{'official_normalizer':'NFC','official_public_raw_roundtrip_count':18,
   'native_public_raw_roundtrip_count':20,'public_case_count':20,'global_unicode_roundtrip_guarantee':False},
  'helper_sha256':sha(Path(__file__)),
  'limits':['PASS applies to this explicit template-override/raw-Unicode CPU contract; original HF token-ID equivalence remains FAIL.',
   'Twenty public probes do not establish all-Unicode equivalence or preservation.',
   '200 inputs are length-only with source-byte fidelity in rendering; no model generation, GPU, quality scoring, or unused future holdout access.',
   'CPU vocabulary checks do not establish native CUDA loading, VRAM peak, or semantic gate success.']}
 output=m.save('final-cpu-proof.json',proof)
 print(json.dumps({'status':'PASS','proof':output,'official_hf_equivalence':'FAIL18/20','derived_reference':'PASS20/20','inputs':200}))
if __name__=='__main__':main()
