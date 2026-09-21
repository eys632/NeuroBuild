#!/usr/bin/env python3
"""Compare saved audited header metadata; no weights/native/tokenizer/data access.

Only root invokes after the new full audit. A matching typed tokenizer is an
input prerequisite, not a new public/context/official-HF-equivalence PASS.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

ROOT=Path('/home/a202192020/NeuroBuild_v2')
AUDITOR=Path('var/research/inspect_qwen36_gguf.py')
AUDITOR_SHA='6e19db06be126b95ec619d434b7230a88dc4542d10d506c026f9cebb71114d97'
OLD_HEADER=Path('var/reports/qwen38-gguf-header.json')
OLD_HEADER_SHA='ff168aeee125b2934b8b5204c14971915c7555c5dfc660d6fda46c2bf7fc810a'
OLD_CONTEXT=Path('var/reports/native-contract-raw-cpu-context.json')
OLD_CONTEXT_SHA='5d37568d7b51d1b689b168f0e9fa6fb46ac487b70f451c82611c146f978e59be'
OLD_OFFICIAL=Path('var/research/native-vocab-public-probe-v4.json')
OLD_OFFICIAL_SHA='b537545d26a876a1496c2f85ad979330eba938f2880aae49190640b2404c63e0'
OLD_RAW=Path('var/research/native-vocab-public-probe-v4-raw-diagnostic.json')
OLD_RAW_SHA='12a5ebeafc16969f36435d9bb9e933ba12197d01ba05e8f26df41114f4e01d2d'
OLD_MODEL='ggml-org/Qwen3.8-27B-GGUF'
OLD_REV='efbb3b1f70a21d97fd4495240648405f7228554f'
OLD_FILE_SHA='c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747'
OLD_TEMPLATE_SHA='c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041'
EXPOSED_SHA='7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'


def auditor():
    if hashlib.sha256((ROOT/AUDITOR).read_bytes()).hexdigest()!=AUDITOR_SHA:
        raise ValueError('AUDITOR_HASH_MISMATCH')
    spec=importlib.util.spec_from_file_location('qwen36_saved_header_auditor',ROOT/AUDITOR)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compare(old,new,old_context,official,raw,m):
    m.require(old.get('kind')==new.get('kind')=='GGUF_HEADER_AUDIT'
              and old.get('status')==new.get('status')=='PASS','HEADER_NOT_PASS')
    m.require(old.get('model_id')==OLD_MODEL and old.get('revision')==OLD_REV
              and old.get('file_sha256')==OLD_FILE_SHA and old.get('file_bytes')==18973870528,
              'OLD_HEADER_IDENTITY_MISMATCH')
    m.require(new.get('model_id')==m.MODEL_ID and new.get('revision')==m.REVISION
              and new.get('file_sha256')==m.FILE_SHA and new.get('file_bytes')==m.FILE_BYTES
              and new.get('full_file_sha256_verified') is True
              and new.get('helper_sha256')==AUDITOR_SHA,'NEW_HEADER_IDENTITY_MISMATCH')
    m.require(old.get('runtime_source_revision')==new.get('runtime_source_revision')==m.RUNTIME,
              'RUNTIME_SOURCE_MISMATCH')
    template='tokenizer.chat_template'
    before,after=old['header']['metadata'],new['header']['metadata']
    m.require(before[template]=={'type':8,'bytes':8952,'sha256':OLD_TEMPLATE_SHA,'wire_bytes':8960}
              and after[template]=={'type':8,'bytes':7764,'sha256':m.TEMPLATE_SHA,'wire_bytes':7772},
              'EXPECTED_TEMPLATE_CHANGE_MISMATCH')
    m.require(old['source_metadata_sha256']['tokenizer']=='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'
              and new['source_metadata_sha256']['tokenizer']==m.TOKENIZER_SHA
              and new['source_metadata_sha256']['tokenizer_config']==m.TOKENIZER_CONFIG_SHA,
              'UPSTREAM_TOKENIZER_BINDING_MISMATCH')
    # Do not omit unknown tokenizer keys. An extra tokenizer template or flag is
    # a real difference, even if no known current fixture happens to expose it.
    old_tokens={k:v for k,v in before.items() if k.startswith('tokenizer.') and k!=template}
    new_tokens={k:v for k,v in after.items() if k.startswith('tokenizer.') and k!=template}
    difference=sorted(k for k in old_tokens.keys()|new_tokens.keys()
                      if old_tokens.get(k)!=new_tokens.get(k))
    exact=not difference
    m.require(old_context.get('kind')=='NATIVE_CONTEXT_RAW_UNICODE_CPU_PROOF'
              and old_context.get('status')=='PASS'
              and old_context.get('runtime_variant')=='qwen38-gguf-raw-unicode-v1'
              and old_context.get('gguf_sha256')==OLD_FILE_SHA
              and old_context.get('header_sha256')==OLD_HEADER_SHA
              and old_context.get('max_output_tokens')==768
              and old_context.get('max_context_tokens')==4096
              and old_context.get('application_input_output_nfc_repair') is False,
              'HISTORICAL_CONTEXT_IDENTITY_MISMATCH')
    # Select saved exposed metrics only. Never read the dataset or extract the
    # old V2 split; no old report is rewritten as a new candidate observation.
    exposed=old_context['splits']['exposed120']
    m.require(exposed['dataset_sha256']==EXPOSED_SHA and exposed['input_count']==120
              and exposed['min_input_tokens']==2133 and exposed['max_input_tokens']==2409
              and exposed['max_input_plus_output']==3177,'HISTORICAL_EXPOSED_COUNTS_MISMATCH')
    measured={key:exposed[key] for key in ('dataset_sha256','input_count','min_input_tokens',
                                        'max_input_tokens','max_input_plus_output')}
    op,rp=official['native'],raw['native']
    m.require(op['status']=='FAIL' and op['parity_cases_checked']==20
              and op['parity_id_matches']==19 and op['parity_mismatch_mask']==2048
              and op['parity_native_roundtrip_cases']==20,'HISTORICAL_OFFICIAL_FAILURE_MISMATCH')
    m.require(rp['status']=='PASS' and rp['tokenizer_metadata_parity']=='PASS'
              and rp['tokenizer_metadata_parity_cases']==20,'HISTORICAL_RAW_PROOF_MISMATCH')
    return {
        'kind':'QWEN36_QWEN38_SAVED_TYPED_TOKENIZER_COMPARISON',
        'status':'PASS_EXACT_TYPED_TOKENIZER_EXCEPT_DECLARED_TEMPLATE' if exact else 'DELTA_REQUIRED_NOT_EQUIVALENT',
        'new_model_id':m.MODEL_ID,'new_revision':m.REVISION,'new_gguf_sha256':m.FILE_SHA,
        'old_model_id':OLD_MODEL,'old_revision':OLD_REV,'old_gguf_sha256':OLD_FILE_SHA,
        'runtime_source_revision':m.RUNTIME,'typed_tokenizer_equal_excluding_template':exact,
        'old_tokenizer_metadata_key_count':len(old_tokens),'new_tokenizer_metadata_key_count':len(new_tokens),
        'differing_tokenizer_metadata_keys':difference,
        'typed_tokenizer_hashes':{
            'old':hashlib.sha256(json.dumps(old_tokens,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'new':hashlib.sha256(json.dumps(new_tokens,sort_keys=True,separators=(',',':')).encode()).hexdigest()},
        'template_change':{'old_sha256':OLD_TEMPLATE_SHA,'new_sha256':m.TEMPLATE_SHA,
                           'effective_input_equivalence':'PENDING_NEW_RESTRICTED_TEMPLATE_PUBLIC_PROOF'},
        'historical_measurements':{'measured_model_id':OLD_MODEL,'measured_revision':OLD_REV,
            'measured_gguf_sha256':OLD_FILE_SHA,'exposed120':measured,
            'official_hf_id_equivalence':{'status':'FAIL','case_count':20,'id_match_count':19,
                                        'mismatch_indices':[11],'native_original_roundtrip_count':20},
            'raw_reference':{'status':'PASS','case_count':20,'id_match_count':20,
                             'reference_kind':'hf-tokenizer-json-with-nfc-normalizer-disabled'}},
        'candidate_context_route':'PENDING_EFFECTIVE_INPUT_EQUIVALENCE_FOR_CARRY' if exact else 'EXPOSED120_ONLY_AFTER_DELTA_REVIEW',
        'candidate_official_hf_equivalence':'NOT_NEWLY_MEASURED_OR_ASSERTED',
        'candidate_raw_unicode_variant':'ROOT_EXPLICIT_DECISION_REQUIRED',
        'sampling_recipe_equivalent':False,'new_sampling_binding':'REQUIRED_PRESENCE_WINDOW_ORDER_CHANGED',
        'new_native_public_or_vocab_or_context_executions':0,
        'weight_accesses':0,'model_inference_calls':0,'gpu_calls':0,'http_calls':0,
        'evaluation_dataset_bodies_read':0,'application_input_output_nfc_repair':False,
        'carry_forward_status':'NOT_YET_AUTHORIZED_OR_PROVED_BY_THIS_METADATA_COMPARISON',
        'limitations':['A typed metadata match does not establish new effective-template execution or quality.',
            'Historical official NFC failure remains FAIL; a raw-reference PASS is not official equivalence.',
            'Only saved exposed120 measurements are projected; old V2/unused80 are never requested.',
            'No native process, tokenizer encode/decode or template renderer is called by this helper.']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate-report',type=Path,required=True)
    p.add_argument('--candidate-report-sha256',required=True)
    p.add_argument('--report',type=Path,required=True)
    args=p.parse_args()
    try:
        m=auditor()
        m.require(args.candidate_report.parts[:2]==('var','reports')
                  and args.report.parts[:2]==('var','reports') and args.report.suffix=='.json',
                  'REPORT_PATH_INVALID')
        specs=[(OLD_HEADER,OLD_HEADER_SHA),(args.candidate_report,args.candidate_report_sha256),
               (OLD_CONTEXT,OLD_CONTEXT_SHA),(OLD_OFFICIAL,OLD_OFFICIAL_SHA),(OLD_RAW,OLD_RAW_SHA)]
        docs=[json.loads(m.read_bound(path,digest,2*1024**2)) for path,digest in specs]
        result=compare(*docs,m)
        result.update({'created_utc':datetime.now(timezone.utc).isoformat(),
                       'proof_refs':{str(path):digest for path,digest in specs},
                       'auditor_sha256':AUDITOR_SHA,
                       'helper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
        data=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
        with m.safe_open(ROOT,args.report,write=True) as f:f.write(data)
        print(json.dumps({'status':result['status'],'report':str(args.report),
                          'report_sha256':hashlib.sha256(data).hexdigest(),
                          'candidate_context_route':result['candidate_context_route']}))
        return 0
    except Exception:
        print(json.dumps({'status':'FAIL','code':'SAVED_METADATA_COMPARISON_REJECTED'}))
        return 1


if __name__=='__main__':
    sys.exit(main())
