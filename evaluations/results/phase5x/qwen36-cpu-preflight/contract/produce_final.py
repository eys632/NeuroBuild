"""Join reviewed saved proofs only. No native/encode/render/corpus/weight execution."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
import os
import sys

ROOT=Path('/home/a202192020/NeuroBuild_v2')
BASE=Path('var/research/native-qwen36-contract')
PUBLIC_HELPER=BASE/'public_check.py'
PUBLIC_HELPER_SHA='7bb13bb7abd0fc596194d592d9f17b1ba5d5103d15dfae3193a0dd2c181f98fc'
COMPARATOR=Path('var/research/compare_qwen36_qwen38_saved_headers.py')
COMPARATOR_SHA='e4325ae6f952f5aaf8b277b75af33da835b8e2fe01834c69cc0b5cf66042b756'
REPORT=BASE/'final-cpu-proof.json'
VARIANT='qwen36-gguf-raw-unicode-v1'


def require(ok,code):
    if not ok:raise ValueError(code)


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def load(path,digest,name):
    require(sha(ROOT/path)==digest,'HELPER_HASH_MISMATCH')
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--header-sha256',required=True)
    p.add_argument('--comparison-sha256',required=True)
    p.add_argument('--public-sha256',required=True)
    p.add_argument('--build-sha256',required=True)
    p.add_argument('--candidate-variant',required=True,choices=[VARIANT])
    args=p.parse_args()
    require(Path(sys.prefix)==ROOT/'.conda' and os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU_ENV_REQUIRED')
    h=load(PUBLIC_HELPER,PUBLIC_HELPER_SHA,'qwen36_public_definition_only')
    c=load(COMPARATOR,COMPARATOR_SHA,'qwen36_comparison_definition_only')
    m=c.auditor()
    refs={
      'header':{'path':str(h.HEADER),'sha256':args.header_sha256},
      'tokenizer_comparison':{'path':str(h.COMPARISON),'sha256':args.comparison_sha256},
      'public_contract':{'path':str(BASE/'public-proof.json'),'sha256':args.public_sha256},
      'public_build':{'path':str(h.BUILD),'sha256':args.build_sha256},
      'historical_header':{'path':str(c.OLD_HEADER),'sha256':c.OLD_HEADER_SHA},
      'historical_context':{'path':str(c.OLD_CONTEXT),'sha256':c.OLD_CONTEXT_SHA},
      'historical_official':{'path':str(c.OLD_OFFICIAL),'sha256':c.OLD_OFFICIAL_SHA},
      'historical_raw':{'path':str(c.OLD_RAW),'sha256':c.OLD_RAW_SHA},
      'historical_raw_fixture':{'path':'var/research/native-tokenizer-public-parity-raw-diagnostic.json',
        'sha256':'9658eb53fae81adee1b775b45f796f3484db69aea41e04a020765fa05d770514'},
      'source_equivalence':{'path':str(h.EQUIVALENCE),'sha256':h.EQUIVALENCE_SHA}}
    docs={k:json.loads(m.read_bound(Path(v['path']),v['sha256'],2*1024**2)) for k,v in refs.items()}
    header,comparison,public,build,eq=(docs[k] for k in ('header','tokenizer_comparison','public_contract','public_build','source_equivalence'))
    require(header['kind']=='GGUF_HEADER_AUDIT' and header['status']=='PASS'
      and header['model_id']==m.MODEL_ID and header['revision']==m.REVISION
      and header['file_sha256']==m.FILE_SHA and header['full_file_sha256_verified'] is True,'HEADER_NOT_PASS')
    require(comparison['kind']=='QWEN36_QWEN38_SAVED_TYPED_TOKENIZER_COMPARISON'
      and comparison['status']=='PASS_EXACT_TYPED_TOKENIZER_EXCEPT_DECLARED_TEMPLATE'
      and comparison['typed_tokenizer_equal_excluding_template'] is True
      and comparison['new_model_id']==m.MODEL_ID and comparison['new_revision']==m.REVISION
      and comparison['new_gguf_sha256']==m.FILE_SHA
      and comparison['proof_refs'][str(h.HEADER)]==args.header_sha256
      and comparison['helper_sha256']==COMPARATOR_SHA,'TOKENIZER_NOT_EQUAL')
    require(public['kind']=='QWEN36_NATIVE_RESTRICTED_TEMPLATE_CPU_PROOF' and public['status']=='PASS'
      and public['model_id']==m.MODEL_ID and public['revision']==m.REVISION
      and public['gguf_sha256']==m.FILE_SHA and public['header_sha256']==args.header_sha256
      and public['comparison_sha256']==args.comparison_sha256
      and public['template_sha256']==m.TEMPLATE_SHA and public['source_pin']==m.RUNTIME
      and public['source_sha256']==h.SOURCE_PINS and public['sampling_request_parameters']==h.SAMPLE
      and public['protocol']=='llama_cpp_json_schema' and public['sampling_profile']=='qwen36_nonthinking_llama_cpp'
      and public['helper_sha256']==PUBLIC_HELPER_SHA and public['source_equivalence_sha256']==h.EQUIVALENCE_SHA
      and public['build_report_sha256']==args.build_sha256,'PUBLIC_NOT_BOUND')
    h.validate_native(public['native'],0,0) # Saved fixed scalar receipt only; no binary invocation.
    require(public['new_public_request_count']==public['native_process_count']==1
      and public['old_public_corpus_calls']==public['tokenizer_parity_cases']==public['context_requests']==0
      and public['weight_accesses']==public['model_inference_calls']==public['http_calls']==public['gpu_calls']==0
      and public['input_output_nfc_repair'] is False,'PUBLIC_SCOPE_CHANGED')
    require(build['kind']=='QWEN36_NATIVE_CONTRACT_CPU_BUILD' and build['status']=='COMPILE_PASS_NOT_EXECUTED'
      and public['binary_sha256']==build['binary_sha256'] and build['source_pin']==m.RUNTIME
      and len(build['phases'])==2 and all(x['exit_code']==0 for x in build['phases']), 'BUILD_NOT_BOUND')
    require(eq['kind']=='QWEN36_QWEN38_SELECTED_INPUT_SOURCE_EQUIVALENCE'
      and eq['status']=='PASS_STATIC_RESTRICTED_INPUT_PATH'
      and eq['current_source_sha256']==h.SOURCE_PINS
      and eq['request_construction_through_Request_AST_equal'] is True
      and eq['fixed_prompt_and_schema_match_historical_public_runner'] is True
      and eq['native_selected_parser']['same_branch'] is True
      and eq['old_context_source_client_sha256']==docs['historical_context']['pinned_inputs']['src/neurobuild/infrastructure/local_model.py']
      and eq['historical_context_sha256']==c.OLD_CONTEXT_SHA,'INPUT_PATH_NOT_EQUAL')
    for path,digest in {**h.PINS,**eq['reference_sha256']}.items():
        require(sha(ROOT/path)==digest,'SOURCE_CHANGED')
    measured=comparison['historical_measurements']
    official={'status':'FAIL','case_count':20,'id_match_count':19,'mismatch_indices':[11],
              'native_original_roundtrip_count':20}
    raw={'status':'PASS','case_count':20,'id_match_count':20,
         'reference_kind':'hf-tokenizer-json-with-nfc-normalizer-disabled'}
    require(measured['official_hf_id_equivalence']==official and measured['raw_reference']==raw,'HISTORY_CHANGED')
    fixture=docs['historical_raw_fixture']
    space=[r for r in fixture['tokenizer_parity'] if r['text']==' ']
    require(len(space)==1 and space[0]['expected_token_ids']==[220],'HISTORICAL_RESOURCE_TOKEN_CHANGED')
    row=dict(measured['exposed120'],measurement_kind='CARRIED_FORWARD',measured_model_id=c.OLD_MODEL)
    require(row['dataset_sha256']==c.EXPOSED_SHA and row['input_count']==120
      and row['min_input_tokens']==2133 and row['max_input_tokens']==2409
      and row['max_input_plus_output']==row['max_input_tokens']+768==3177,'CARRIED_COUNTS_CHANGED')
    result={
      'kind':'QWEN36_NATIVE_CONTRACT_CPU_PROOF','status':'PASS_CURRENT_PUBLIC_AND_CARRIED_EXPOSED120',
      'created_utc':datetime.now(timezone.utc).isoformat(),'candidate_variant':args.candidate_variant,
      'model_id':m.MODEL_ID,'revision':m.REVISION,'gguf_sha256':m.FILE_SHA,'header_sha256':args.header_sha256,
      'template_sha256':m.TEMPLATE_SHA,'tokenizer_json_sha256':m.TOKENIZER_SHA,'source_pin':m.RUNTIME,
      'protocol':'llama_cpp_json_schema','sampling_profile':'qwen36_nonthinking_llama_cpp',
      'sampling_request_parameters':h.SAMPLE,'source_sha256':h.SOURCE_PINS,
      'enable_thinking':False,'enable_reasoning':False,'template_override_used':False,
      'max_output_tokens':768,'max_context_tokens':4096,'splits':{'exposed120':row},
      'historical_hf_equivalence':official,'historical_raw_reference':raw,
      'sampling_equivalent':False,'application_input_output_nfc_repair':False,
      'tokenizer_contract':'historical_raw_reference_by_exact_typed_metadata_and_restricted_input_equivalence',
      'normalization_limitation':'Historical Qwen3.8 official HF NFC reference IDs matched 19/20 (index11 mismatch), while native raw original roundtrip and explicitly NFC-disabled reference matched 20/20. These measurements remain historical; actual typed native tokenizer equality and restricted effective-input equivalence support carry to the explicit Qwen3.6 raw-Unicode variant. Official HF equivalence is not newly measured or asserted; no application input/output normalization repair.',
      'template_input_equivalence':{'status':'PASS','scope':eq['scope'],
         'byte_exact_public_native_render':True,'proof_ref':'source_equivalence'},
      'resource_probe_token':{'text':' ','token_id':220,'native_token_count':1,'native_roundtrip':True,
         'measurement_kind':'CARRIED_FORWARD_BY_TYPED_VOCAB_EQUALITY'},
      'new_executions':{'public_request_count':1,'native_compile_count':1,'context_request_count':0,
         'public_parity_cases':0,'old_corpus_replays':0,'model_inference':0,'http':0,'gpu':0},
      'proof_refs':refs,'helper_sha256':sha(Path(__file__)),
      'limits':['Only one new public native template/sampler request was executed.',
        'Public parity and exposed120 lengths are historical carry, not fresh 20/120/200 execution.',
        'Old V2 and unused80 were not opened; no new model quality or runtime resource claim.']}
    data=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
    with m.safe_open(ROOT,REPORT,write=True) as f:f.write(data)
    print(json.dumps({'status':result['status'],'report':str(REPORT),'report_sha256':hashlib.sha256(data).hexdigest()}))
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        print(json.dumps({'status':'FAIL','code':'QWEN36_SAVED_PROOF_CLOSURE_REJECTED'}))
        raise SystemExit(1)
