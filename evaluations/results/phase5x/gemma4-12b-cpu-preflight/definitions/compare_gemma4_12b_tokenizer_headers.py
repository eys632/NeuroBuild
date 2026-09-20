#!/usr/bin/env python3
"""Saved header metadata comparison only; never opens weights or executes native code.

A PASS establishes complete typed tokenizer metadata equality except the declared
12B suppression array. It does not itself carry forward public/context proofs or
claim new-model inference, sampling, runtime, or quality equivalence.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import struct
import sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
AUDITOR = Path('var/research/inspect_gemma4_12b_gguf.py')
AUDITOR_SHA = '5b2bb2b55578841cf31071a1bde46920962d55a0145664f4d6051c291fab338b'
OLD_REPORT = Path('var/reports/gemma4-gguf-header-v2.json')
OLD_SHA = 'd867a3300b2a93534fb1b480e8e42b30321c894aaec05b5729a529e848817756'
OLD_MODEL = 'google/gemma-4-31B-it-qat-q4_0-gguf'
OLD_REV = '59dde24573e7e61570dba08b18a2e1fe246955ed'
OLD_FILE_SHA = '179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b'


def auditor():
    if hashlib.sha256((ROOT/AUDITOR).read_bytes()).hexdigest() != AUDITOR_SHA:
        raise ValueError('AUDITOR_HASH_MISMATCH')
    spec = importlib.util.spec_from_file_location('gemma12_saved_metadata_auditor',ROOT/AUDITOR)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def compare(old, new, m):
    m.require(old.get('kind') == new.get('kind') == 'GGUF_HEADER_AUDIT'
              and old.get('status') == new.get('status') == 'PASS', 'HEADER_NOT_PASS')
    m.require(old.get('model_id') == OLD_MODEL and old.get('revision') == OLD_REV
              and old.get('file_sha256') == OLD_FILE_SHA
              and old.get('file_bytes') == 17651001568, 'OLD_HEADER_IDENTITY_MISMATCH')
    m.require(new.get('model_id') == m.MODEL_ID and new.get('revision') == m.REVISION
              and new.get('file_sha256') == m.FILE_SHA and new.get('file_bytes') == m.FILE_BYTES
              and new.get('full_file_sha256_verified') is True
              and new.get('helper_sha256') == AUDITOR_SHA, 'NEW_HEADER_IDENTITY_MISMATCH')
    m.require(old.get('runtime_source_revision') == new.get('runtime_source_revision') == m.RUNTIME,
              'RUNTIME_SOURCE_MISMATCH')
    for report in (old,new):
        pins = report['source_metadata_sha256']
        m.require(pins.get('tokenizer') == m.TOKENIZER_SHA and pins.get('template') == m.TEMPLATE_SHA,
                  'OFFICIAL_TOKENIZER_TEMPLATE_MISMATCH')
    before, after = old['header']['metadata'], new['header']['metadata']
    m.require(before.get('general.architecture') == after.get('general.architecture'),
              'ARCHITECTURE_METADATA_MISMATCH')
    old_tokens = {k:v for k,v in before.items() if k.startswith('tokenizer.')}
    new_tokens = {k:v for k,v in after.items() if k.startswith('tokenizer.')}
    suppression = 'tokenizer.ggml.suppress_tokens'
    m.require(suppression not in old_tokens
              and set(new_tokens) == set(old_tokens) | {suppression}, 'TOKENIZER_KEYSET_MISMATCH')
    expected = {'type':9,'element_type':5,'count':2,
                'elements_wire_sha256':hashlib.sha256(struct.pack('<ii',*m.SUPPRESS_TOKENS)).hexdigest(),
                'wire_bytes':20}
    m.require(new_tokens[suppression] == expected, 'SUPPRESSION_TYPED_METADATA_MISMATCH')
    m.require(all(new_tokens[k] == v for k,v in old_tokens.items()), 'TOKENIZER_TYPED_METADATA_MISMATCH')
    return {'kind':'GEMMA12_GEMMA31_SAVED_TOKENIZER_METADATA_COMPARISON',
            'status':'PASS_EXACT_TYPED_TOKENIZER_METADATA_EXCEPT_DECLARED_SUPPRESSION',
            'old_model_id':OLD_MODEL,'new_model_id':m.MODEL_ID,
            'same_runtime_source_revision':m.RUNTIME,'same_original_template_sha256':m.TEMPLATE_SHA,
            'same_official_tokenizer_sha256':m.TOKENIZER_SHA,
            'old_tokenizer_metadata_key_count':len(old_tokens),
            'new_tokenizer_metadata_key_count':len(new_tokens),
            'exact_shared_tokenizer_metadata_keys':sorted(old_tokens),
            'shared_typed_metadata_sha256':hashlib.sha256(json.dumps(old_tokens,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'allowed_added_metadata':{suppression:expected},
            'sampling_difference':{'model_suppress_tokens':m.SUPPRESS_TOKENS,
                 'wire_type':'INT32','native_effect':'Negative-infinity logit bias before the sampling recipe',
                 'complete_effective_sampling_equivalent':False},
            'new_native_public_or_vocab_or_context_executions':0,
            'model_inference_calls':0,'gpu_calls':0,'http_calls':0,
            'scope':'Saved full-audit header metadata comparison; no model payload access.',
            'carry_forward_status':'INPUT_METADATA_PREREQUISITE_ONLY; source/request/proof closure is separate',
            'limitations':['No new candidate quality, runtime, VRAM or sampling-equivalence PASS.',
                 'Prior public20/context200 observations remain historical and their Unicode limitations remain.']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate-report',type=Path,required=True)
    p.add_argument('--candidate-report-sha256',required=True)
    p.add_argument('--report',type=Path,required=True)
    args=p.parse_args()
    try:
        m=auditor()
        m.require(args.candidate_report.parts[:2] == ('var','reports')
                  and args.report.parts[:2] == ('var','reports'), 'REPORT_PATH_INVALID')
        old=json.loads(m.read_bound(OLD_REPORT,OLD_SHA,2*1024**2))
        new=json.loads(m.read_bound(args.candidate_report,args.candidate_report_sha256,2*1024**2))
        result=compare(old,new,m)
        result.update({'created_utc':datetime.now(timezone.utc).isoformat(),
                       'old_header_report':OLD_REPORT.as_posix(),'old_header_sha256':OLD_SHA,
                       'new_header_report':args.candidate_report.as_posix(),
                       'new_header_sha256':args.candidate_report_sha256,
                       'auditor_sha256':AUDITOR_SHA,
                       'helper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
        data=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
        with m.safe_open(ROOT,args.report,write=True) as f:f.write(data)
        print(json.dumps({'status':result['status'],'report':args.report.as_posix(),
                          'report_sha256':hashlib.sha256(data).hexdigest()}))
        return 0
    except Exception:
        # Suppress input/metadata text. Root can inspect the saved input receipts.
        print(json.dumps({'status':'FAIL','code':'SAVED_HEADER_COMPARISON_REJECTED'}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
