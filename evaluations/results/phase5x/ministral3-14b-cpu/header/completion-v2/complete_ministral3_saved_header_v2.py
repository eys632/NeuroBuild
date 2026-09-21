#!/usr/bin/env python3
"""Complete one pinned failed structural audit using saved metadata only.

No GGUF open/stat, no model/native/tokenization/HTTP/GPU/context/corpus access.
The original full SHA/shape audit and firstFAIL stay unchanged. INT32 all-zero
scores are accepted because pinned loader/writer explicitly support them.
Ordered token/type arrays are reconstructed using canonical byte mapping plus
two explicitly observed native-only THINK special strings, not a tokenizer call. No full header body is duplicated in the completion.
"""
from __future__ import annotations
import argparse
import ast
import base64
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
import types

ROOT=Path('/home/a202192020/NeuroBuild_v2')
BASE=Path('var/research/inspect_ministral3_gguf.py')
BASE_SHA='cd3ff0cf422933fa67566256be629f3660254b779bfb5ac24e504756ffee6ea7'
AUDIT=Path('var/reports/ministral3-gguf-header.json')
AUDIT_SHA='587e2f3b56d70184496554ddd642d7487dbbe9ccd74e6dd0db02f57139928d58'
TEMPLATE=Path('var/reports/ministral3-embedded-chat-template.jinja')
TEMPLATE_SHA='6cc0f8c0cfbafcfd8b146d60e947a1b2511ace4db907b0a73f6a474d04bdca9b'
V1=Path('var/research/complete_ministral3_saved_header.py')
V1_SHA='b004ff14be33b99e3c585b94d8f5d9980266e91a55e7365b575ff0b4fbab011c'
V1_FAILURE=Path('var/research/ministral3-header-completion-cli.log')
V1_FAILURE_SHA='7fffef94071b229c1ddb940920bb2824822b845538babeeb9eb4b0f0d74d45c7'
TOKEN_DIAG=Path('var/research/ministral3-header-token-diagnostic.json')
TOKEN_DIAG_SHA='0f2a85ba731be998768b3aab8c7ddceed5af25ddfa53b1c13e4b4c305d6224d9'
TOKEN_DIAG_HELPER=Path('var/research/diagnose_ministral3_header_tokens.py')
TOKEN_DIAG_HELPER_SHA='7fddc52c529ecdab17ee5b334842c33e22148bd510538b98dfde138ead81564f'
ARRAY_DIAG=Path('var/research/ministral3-saved-header-array-diagnostic.json')
ARRAY_DIAG_SHA='767f9a35846a88610693ab05fe551e8eb2114509a802b7d95267c8741b0f526f'
NATIVE_SPECIAL_OVERRIDES={34:'[THINK]',35:'[/THINK]'}
SOURCE_PINS={'var/runtime-src/llama.cpp-f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-vocab.cpp': '82e8996cbbd81c1648b1f4946b5f481138aa897a1343dcd8b1a4abe8cff0b5fc', 'var/runtime-src/llama.cpp-f072b103714dfa1eee531f80b24512faf38e3dd2/gguf-py/gguf/vocab.py': '16cddd93700f86c8b72e6f9e741e2362189155b9f96aa9e3bbb0995060095f1a', 'var/runtime-src/llama.cpp-f072b103714dfa1eee531f80b24512faf38e3dd2/gguf-py/gguf/gguf_writer.py': '7e3ff8d04b290dde083ae30d1091b67c95299f6865958fe1cdcb7e35dd201766', 'var/runtime-src/llama.cpp-f072b103714dfa1eee531f80b24512faf38e3dd2/gguf-py/gguf/constants.py': 'df0078c283a48061260ca4b3f35df36611230c3e7c2ac271bb8a11d2632839ba', 'var/research/ministral3-14b-candidate-metadata/official-tokenizer-source/tekken.py': '914d6e6f4ae4e1ba3709557a9992ee540644ffd16075efc9474a6e12c15ae6f3'}


class CompletionError(Exception):
    pass


def require(condition,code):
    if not condition:
        raise CompletionError(code)


def load_base():
    # Exact source bytes, no audit/main invocation; imported module only defines functions.
    data=(ROOT/BASE).read_bytes()
    require(hashlib.sha256(data).hexdigest()==BASE_SHA,'ORIGINAL_HELPER_CHANGED')
    module=types.ModuleType('ministral3_original_header_definition')
    module.__file__=str(ROOT/BASE)
    exec(compile(data,str(ROOT/BASE),'exec'),module.__dict__)
    return module


def bytes_to_unicode() -> dict[int, str]:
    """
    Returns list of utf-8 byte and a mapping to unicode strings. We specifically avoids mapping to whitespace/control
    characters the bpe code barfs on.

    The reversible bpe codes work on unicode strings. This means you need a large # of unicode characters in your vocab
    if you want to avoid UNKs. When you're at something like a 10B token dataset you end up needing around 5K for
    decent coverage. This is a significant percentage of your normal, say, 32K bpe vocab. To avoid that, we want lookup
    tables between utf-8 bytes and unicode strings.
    """
    bs = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("¡"), ord("¬") + 1))
        + list(range(ord("®"), ord("ÿ") + 1))
    )
    cs = bs[:]
    n = 0
    for b in range(2**8):
        if b not in bs:
            bs.append(b)
            cs.append(2**8 + n)
            n += 1
    cs_str = [chr(n) for n in cs]
    return dict(zip(bs, cs_str))


def validate_saved_candidate(base,header,values,config,index,params,inventory,tekken,template,specials,special_types):
    expected=base.expected_metadata(config)
    for key,wanted in expected.items():
        actual=values.get(key);typ=header['metadata'].get(key,{}).get('type')
        if type(wanted) is float:
            match=type(actual) is float and math.isclose(actual,wanted,rel_tol=1e-6,abs_tol=0)
            wiretype=6
        else:
            match=type(actual) is type(wanted) and actual==wanted
            wiretype={int:4,bool:7,str:8}[type(wanted)]
        require(key in values and match,'CONFIG_METADATA_MISMATCH')
        require(typ==wiretype,'CONFIG_METADATA_TYPE_MISMATCH')
    # These are absent in the source text model; loader defaults must not enable them.
    for key in ['mistral3.expert_count','mistral3.expert_used_count',
                'mistral3.nextn_predict_layers','mistral3.attention.sliding_window']:
        if key in header['metadata']:
            require(type(values.get(key)) is int and values[key]==0
                    and header['metadata'][key]['type']==4,'UNEXPECTED_MODEL_FEATURE')
    require(not any(k.startswith(('clip.','mtp.','qwen.')) for k in header['metadata']),
            'UNEXPECTED_MODEL_FEATURE')
    if 'mistral3.vocab_size' in header['metadata']:
        require(values.get('mistral3.vocab_size')==131072
                and header['metadata']['mistral3.vocab_size']['type']==4,'VOCAB_SIZE_MISMATCH')
    require(params.get('tied_embeddings') is False,'UNTIED_OUTPUT_SOURCE_MISMATCH')
    names=index['weight_map']
    source_text=[n for n in names if n.startswith('language_model.')]
    require(len(source_text)==363 and 'language_model.lm_head.weight' in names
            and 'language_model.model.embed_tokens.weight' in names,'SOURCE_TEXT_INDEX_MISMATCH')
    require(inventory['kind']=='MINISTRAL3_OFFICIAL_CONFIG_LOADER_TEXT_INVENTORY'
            and inventory['status']=='EXPECTED_NOT_ACTUAL_GGUF'
            and inventory['tensor_count']==363,'INVENTORY_IDENTITY_MISMATCH')
    rows=inventory['expected_rows']
    shape_map={r['name']:r['shape'] for r in rows}
    require(len(rows)==len(shape_map)==header['tensor_count']==363,'EXPECTED_TENSOR_COUNT_MISMATCH')
    require({r['name'] for r in header['tensors']}==set(shape_map),'EXPECTED_TENSOR_SET_MISMATCH')
    role_types={}
    for row in header['tensors']:
        require(row['shape']==shape_map[row['name']],'EXPECTED_TENSOR_SHAPE_MISMATCH')
        if len(row['shape'])==1:
            require(row['type_id']==0,'VECTOR_TYPE_MISMATCH')
        else:
            require(row['type_id'] in base.MATRIX_TYPES,'MATRIX_TYPE_UNSUPPORTED')
        role=re.sub(r'^blk\.\d+\.','blk.*.',row['name'])
        role_types.setdefault(role,Counter())[row['dtype']]+=1
    for key,sub,count in [('tokenizer.ggml.tokens',8,131072),('tokenizer.ggml.token_type',5,131072)]:
        m=header['metadata'].get(key,{})
        require(m.get('type')==9 and m.get('element_type')==sub and m.get('count')==count,
                'TOKENIZER_ARRAY_METADATA_MISMATCH')
    merges=header['metadata'].get('tokenizer.ggml.merges',{})
    require(merges.get('type')==9 and merges.get('element_type')==8
            and type(merges.get('count')) is int and 0<merges['count']<=base.ARRAY_CAP,
            'TOKENIZER_MERGES_METADATA_MISMATCH')
    if 'tokenizer.ggml.scores' in header['metadata']:
        scores=header['metadata']['tokenizer.ggml.scores']
        require(scores.get('type')==9 and scores.get('element_type')==5
                and scores.get('count')==131072
                and scores.get('elements_wire_sha256')==hashlib.sha256(bytes(131072*4)).hexdigest(),
                'TOKENIZER_INT32_ZERO_SCORES_MISMATCH')
    require(tekken['config']['version']=='v13'
            and tekken['config']['default_vocab_size']==131072
            and tekken['config']['default_num_special_tokens']==1000
            and len(tekken['special_tokens'])==1000 and len(tekken['vocab'])==130072,
            'TEKKEN_REFERENCE_IDENTITY_MISMATCH')
    canonical={r['rank']:r['token_str'] for r in tekken['special_tokens']}
    canonical.update(NATIVE_SPECIAL_OVERRIDES)
    require(set(canonical)==set(range(1000)) and specials==canonical,'TOKENIZER_SPECIAL_TEXT_MISMATCH')
    require(special_types=={i:3 for i in range(1000)},'TOKENIZER_SPECIAL_TYPE_MISMATCH')
    embedded=header['metadata'].get('tokenizer.chat_template',{})
    actual_template_sha=hashlib.sha256(template).hexdigest()
    require(embedded.get('type')==8 and embedded.get('bytes')==len(template)
            and embedded.get('sha256')==actual_template_sha,'TEMPLATE_EXTRACTION_MISMATCH')
    conditional={r['name']:r['conditional_f072_q4_k_m_dtype'] for r in rows}
    return {
        'validation_scope':'FILE_IDENTITY_AND_TEXT_MODEL_STRUCTURE_ONLY',
        'config_values_bound':len(expected),'text_tensors_shape_matched':363,'layers':40,
        'quantization':'Q4_K_M','ftype':15,
        'quantization_policy':'KNOWN_DENSE_STORAGE_FORMATS; publisher per-role recipe unpublished',
        'actual_per_role_dtypes':{k:dict(v) for k,v in sorted(role_types.items())},
        'conditional_f072_default_recipe_matches':all(conditional[r['name']]==r['dtype'] for r in header['tensors']),
        'conditional_recipe_match_is_conversion_proof':False,
        'untied_output_present':True,'vision_projector_tensors':0,'mtp_layers':0,'moe_experts':0,
        'tokenizer_special_entries_bound':1000,'canonical_special_entries_matched':998,
        'native_special_overrides':NATIVE_SPECIAL_OVERRIDES,'tokenizer_arrays_typed_and_hashed':True,
        'tokenizer_full_vocab_or_merges_equivalence':'PENDING',
        'embedded_template_sha256':actual_template_sha,'embedded_template_bytes':len(template),
        'reference_template_sha256':base.TEMPLATE_REFERENCE_SHA,
        'reference_template_byte_equal':actual_template_sha==base.TEMPLATE_REFERENCE_SHA,
        'template_compatibility':'PENDING_NEW_CPU_CONTRACT',
        'tokenizer_compatibility':'PENDING_NEW_REFERENCE_AND_NATIVE_PARITY',
        'runtime_compatibility':'PENDING','quality':'PENDING',
        'tensor_payload_numeric_validity':'NOT_DECODED_OR_TESTED',
    }


def canonical_array_hashes(tekken):
    cfg=tekken['config']
    require(cfg['version']=='v13' and cfg['default_vocab_size']==131072
            and cfg['default_num_special_tokens']==1000,'TEKKEN_REFERENCE_IDENTITY_MISMATCH')
    special=tekken['special_tokens'];ordinary=tekken['vocab']
    require(len(special)==1000 and len(ordinary)==130072,'TEKKEN_REFERENCE_SIZE_MISMATCH')
    encoder=bytes_to_unicode()
    tok=hashlib.sha256();canonical_tok=hashlib.sha256();typ=hashlib.sha256();seen=set();specials={}
    for i,row in enumerate(special):
        require(type(row['rank']) is int and row['rank']==i and row['is_control'] is True,
                'TEKKEN_SPECIAL_ORDER_MISMATCH')
        value=row['token_str'];require(type(value) is str,'TEKKEN_SPECIAL_STRING_MISMATCH')
        raw=value.encode('utf-8');require(raw not in seen,'DUPLICATE_CANONICAL_TOKEN');seen.add(raw)
        canonical_tok.update(struct.pack('<Q',len(raw)));canonical_tok.update(raw)
        native_value=NATIVE_SPECIAL_OVERRIDES.get(i,value)
        native_raw=native_value.encode('utf-8')
        tok.update(struct.pack('<Q',len(native_raw)));tok.update(native_raw);typ.update(struct.pack('<i',3))
        specials[i]=native_value
    seen_bytes=set()
    for i,row in enumerate(ordinary):
        require(type(row['rank']) is int and row['rank']==i,'TEKKEN_ORDINARY_ORDER_MISMATCH')
        rawbytes=base64.b64decode(row['token_bytes'],validate=True)
        require(rawbytes and rawbytes not in seen_bytes,'TEKKEN_ORDINARY_BYTES_MISMATCH')
        require(i>=256 or rawbytes==bytes([i]),'TEKKEN_INITIAL_BYTE_ORDER_MISMATCH')
        seen_bytes.add(rawbytes)
        # Exact f072 MistralVocab.token_bytes_to_string byte -> GPT-2-unicode rule.
        value=''.join([encoder[ord(char)] for char in rawbytes.decode('latin-1')])
        raw=value.encode('utf-8')
        tok.update(struct.pack('<Q',len(raw)));tok.update(raw);typ.update(struct.pack('<i',1))
        canonical_tok.update(struct.pack('<Q',len(raw)));canonical_tok.update(raw)
    return {'tokens':tok.hexdigest(),'canonical_tokens':canonical_tok.hexdigest(),'token_types':typ.hexdigest(),
            'zero_scores':hashlib.sha256(bytes(131072*4)).hexdigest()},specials


def validate_override_evidence(base,original,tekken,hashes):
    base.read_bound(V1,V1_SHA,64*1024)
    prior=json.loads(base.read_bound(V1_FAILURE,V1_FAILURE_SHA,4096))
    require(prior=={'kind':'GGUF_HEADER_STRUCTURAL_COMPLETION','status':'FAIL',
                    'code':'SAVED_CANONICAL_ARRAY_MISMATCH'},'PRIOR_FAILURE_MISMATCH')
    base.read_bound(TOKEN_DIAG_HELPER,TOKEN_DIAG_HELPER_SHA,64*1024)
    d=json.loads(base.read_bound(TOKEN_DIAG,TOKEN_DIAG_SHA,64*1024))
    a=json.loads(base.read_bound(ARRAY_DIAG,ARRAY_DIAG_SHA,64*1024))
    require(d['kind']=='MINISTRAL3_HEADER_ONLY_TOKEN_REFERENCE_DIAGNOSTIC'
            and d['original_audit_sha256']==AUDIT_SHA
            and d['canonical_tekken_sha256']==base.TEKKEN_SHA
            and d['source_helper_sha256']==V1_SHA and d['helper_sha256']==TOKEN_DIAG_HELPER_SHA
            and d['model_path']==base.MODEL_PATH.as_posix()
            and d['header_bytes_read']==8393191 and d['tensor_payload_bytes_read']==0
            and d['gguf_open_count']==1 and d['all_saved_array_fingerprints_match'] is True
            and d['total_mismatches']==d['special_mismatches']==2 and d['ordinary_mismatches']==0
            and all(d[k]==0 for k in ('native_calls','tokenize_calls','model_calls')),
            'OBSERVED_TOKEN_DIAGNOSTIC_MISMATCH')
    require(d['critical_special_id_text_matches']=={str(i):True for i in (0,1,2,3,4,9,11,17,18,32)},
            'CRITICAL_TOKEN_DIAGNOSTIC_MISMATCH')
    require([r['id'] for r in d['mismatches']]==[34,35],'SPECIAL_OVERRIDE_SCOPE_MISMATCH')
    for row in d['mismatches']:
        i=row['id'];native=NATIVE_SPECIAL_OVERRIDES[i].encode('utf-8')
        reference=tekken['special_tokens'][i]['token_str'].encode('utf-8')
        require(row=={'id':i,'kind':'special','saved_token_bytes':len(native),
                      'reference_token_bytes':len(reference),
                      'saved_token_sha256':hashlib.sha256(native).hexdigest(),
                      'reference_token_sha256':hashlib.sha256(reference).hexdigest(),
                      'canonical_index_of_saved_token':None},'SPECIAL_OVERRIDE_TEXT_HASH_MISMATCH')
    require(a['kind']=='MINISTRAL3_SAVED_HEADER_ARRAY_DIAGNOSTIC'
            and a['original_audit_sha256']==AUDIT_SHA and a['completion_helper_sha256']==V1_SHA
            and a['gguf_reads']==a['tokenizer_calls']==a['model_calls']==0,
            'ARRAY_DIAGNOSTIC_IDENTITY_MISMATCH')
    rows={r['array']:r for r in a['arrays']}
    require(set(rows)=={'tokens','token_type','scores'},'ARRAY_DIAGNOSTIC_SCOPE_MISMATCH')
    for label,key,sub,want in [('tokens','tokens',8,hashes['canonical_tokens']),
                              ('token_type','token_type',5,hashes['token_types']),
                              ('scores','scores',5,hashes['zero_scores'])]:
        row=rows[label];actual=original['header']['metadata']['tokenizer.ggml.'+key]
        require(row['count']==131072 and row['type']==sub and row['canonical_sha256']==want
                and row['saved_sha256']==actual['elements_wire_sha256']
                and row['match'] is (label!='tokens'),'ARRAY_DIAGNOSTIC_HASH_MISMATCH')
    return d


def complete_saved(base):
    original=json.loads(base.read_bound(AUDIT,AUDIT_SHA,2*1024**2))
    require(original['kind']=='GGUF_HEADER_AUDIT' and original['status']=='STRUCTURAL_FAIL'
            and original['failure_code']=='TOKENIZER_SCORES_METADATA_MISMATCH',
            'ORIGINAL_AUDIT_STATE_MISMATCH')
    require(original['model_id']==base.MODEL_ID and original['revision']==base.REVISION
            and original['model_path']==base.MODEL_PATH.as_posix()
            and original['file_sha256']==base.FILE_SHA and original['file_bytes']==base.FILE_BYTES
            and original['full_file_sha256_verified'] is True and original['stat_unchanged'] is True
            and original['helper_sha256']==BASE_SHA
            and original['runtime_source_revision']==base.RUNTIME
            and original['gpu_or_native_execution'] is False,'ORIGINAL_AUDIT_IDENTITY_MISMATCH')
    require(original['download_evidence']=={'manifest_path':base.MANIFEST.as_posix(),
            'manifest_sha256':base.MANIFEST_SHA,'report_path':base.DOWNLOAD.as_posix(),
            'report_sha256':base.DOWNLOAD_SHA},'ORIGINAL_DOWNLOAD_BINDING_MISMATCH')
    for path,digest in SOURCE_PINS.items():
        base.read_bound(Path(path),digest,2*1024**2)
    config=json.loads(base.read_bound(base.META/'bf16/config.json',base.CONFIG_SHA,64*1024))
    index=json.loads(base.read_bound(base.META/'bf16/model.safetensors.index.json',base.INDEX_SHA,256*1024))
    params=json.loads(base.read_bound(base.META/'bf16/params.json',base.PARAMS_SHA,64*1024))
    inventory=json.loads(base.read_bound(base.META/'expected_text_inventory.json',base.INVENTORY_SHA,256*1024))
    tekken=json.loads(base.read_bound(base.META/'bf16/tekken.json',base.TEKKEN_SHA,20*1024**2))
    base.read_bound(base.META/'bf16/chat_template.jinja',base.TEMPLATE_REFERENCE_SHA,64*1024)
    template=base.read_bound(TEMPLATE,TEMPLATE_SHA,64*1024)
    require(original['template_export']=={'path':TEMPLATE.as_posix(),'bytes':len(template),
                                         'sha256':TEMPLATE_SHA},'TEMPLATE_EXPORT_BINDING_MISMATCH')
    h=original['header'];m=h['metadata']
    hashes,specials=canonical_array_hashes(tekken)
    diagnostic=validate_override_evidence(base,original,tekken,hashes)
    for key,sub,count,digest in [('tokenizer.ggml.tokens',8,131072,hashes['tokens']),
                               ('tokenizer.ggml.token_type',5,131072,hashes['token_types']),
                               ('tokenizer.ggml.scores',5,131072,hashes['zero_scores'])]:
        actual=m.get(key,{})
        require(actual.get('type')==9 and actual.get('element_type')==sub
                and actual.get('count')==count and actual.get('elements_wire_sha256')==digest,
                'SAVED_CANONICAL_ARRAY_MISMATCH')
    # Full ordered hash equality after exactly2 separately observed special-name changes
    # binds998 canonical specials and130072 unchanged ordinary entries. No raw input repair.
    bindings=validate_saved_candidate(base,h,original['metadata_values'],config,index,params,
                                     inventory,tekken,template,specials,{i:3 for i in range(1000)})
    require(h['dtype_counts']=={'q4_K':241,'q6_K':41,'f32':81}
            and h['tensor_payload_bytes']==8231178240,'SAVED_STORAGE_INVENTORY_MISMATCH')
    bindings.update({'ordered_tokens_and_types':'EXACT_FULL_WIRE_HASH_MATCH_WITH_TWO_OBSERVED_SPECIAL_NAMES',
                     'canonical_token_array_sha256':hashes['canonical_tokens'],
                     'actual_token_array_sha256':hashes['tokens'],
                     'ordinary_tokens_exact':130072,'canonical_special_tokens_exact':998,
                     'canonical_full_token_equivalence':False,
                     'native_special_name_override_count':2,'input_text_repair':False,
                     'canonical_type_array_sha256':hashes['token_types'],
                     'tokenizer_scores':{'wire_type':'INT32(5)','count':131072,
                         'all_zero_wire_sha256':hashes['zero_scores'],
                         'native_conversion':'static_cast<float>(iscores[i])',
                         'numeric_equivalence_to_float_zero':True},
                     'merges_content_equivalence':'PENDING_NATIVE_TOKENIZATION_REFERENCE',
                     'native_token_id_parity':'PENDING','native_raw_roundtrip':'PENDING'})
    return {'kind':'GGUF_HEADER_STRUCTURAL_COMPLETION','status':'STRUCTURAL_PASS','completion_revision':2,
            'created_at_utc':datetime.now(timezone.utc).isoformat(),
            'model_id':base.MODEL_ID,'revision':base.REVISION,'model_path':base.MODEL_PATH.as_posix(),
            'file_sha256':base.FILE_SHA,'file_bytes':base.FILE_BYTES,
            'full_file_sha256_verified':True,
            'full_file_sha256_verification_scope':'INHERITED_EXACT_ORIGINAL_FULL_AUDIT; NO_NEW_WEIGHT_READ',
            'original_audit':{'path':AUDIT.as_posix(),'sha256':AUDIT_SHA,
                              'status':'STRUCTURAL_FAIL','failure_code':'TOKENIZER_SCORES_METADATA_MISMATCH'},
            'original_helper':{'path':BASE.as_posix(),'sha256':BASE_SHA},
            'prior_completion_failure':{'helper_path':V1.as_posix(),'helper_sha256':V1_SHA,
                'receipt_path':V1_FAILURE.as_posix(),'receipt_sha256':V1_FAILURE_SHA,
                'status':'FAIL','code':'SAVED_CANONICAL_ARRAY_MISMATCH'},
            'token_reference_diagnostic':{'path':TOKEN_DIAG.as_posix(),'sha256':TOKEN_DIAG_SHA,
                'array_diagnostic_path':ARRAY_DIAG.as_posix(),'array_diagnostic_sha256':ARRAY_DIAG_SHA,
                'special_mismatches':2,'ordinary_mismatches':0,'gguf_payload_bytes_read':0},
            'conversion_source_revision':None,
            'runtime_source_revision':base.RUNTIME,'source_sha256':SOURCE_PINS,
            'reference_tekken':{'path':(base.META/'bf16/tekken.json').as_posix(),'sha256':base.TEKKEN_SHA},
            'bindings':bindings,'template_export':original['template_export'],
            'tensor_summary':{'count':363,'payload_bytes':h['tensor_payload_bytes'],'dtype_counts':h['dtype_counts']},
            'completed_remaining_checks':['INT32 all-zero scores supported by pinned loader/writer',
                'Full131072 token strings match after exactly2 observed native special-name substitutions',
                'Ordinary130072 and special998 canonical entries exact; all131072 type entries exact',
                'Exact saved embedded template export/hash and original candidate structural conditions'],
            'new_execution_counts':{'gguf_opens':0,'gguf_stats':0,'weight_hashes':0,'native':0,
                                    'tokenize':0,'template_render':0,'corpus':0,'model':0,'http':0,'gpu':0},
            'limitations':['Original firstFAIL and helper are immutable; this is a separately sourced completion.',
                'Saved fullSHA/coverage are historical observations, not a current file integrity refresh.',
                'Canonical full-token equality is false at IDs34/35; observed native THINK labels are explicit artifact facts.',
                'The two label substitutions reconstruct metadata only; no input normalization or tokenizer installation changes.',
                'Byte/type array reconstruction is not native tokenizer/merge-regex parity.',
                'Actual template differs from current reference; new CPU contract remains pending.',
                'No source revision lineage, runtime peak or semantic quality PASS is asserted.']}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--report',type=Path,required=True)
    args=ap.parse_args()
    try:
        require(args.report==Path('var/reports/ministral3-gguf-header-completion-v2.json'),'REPORT_PATH_INVALID')
        base=load_base()
        result=complete_saved(base)
        result['helper_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        data=(json.dumps(result,indent=2)+'\n').encode()
        with base.safe_open(ROOT,args.report,write=True) as f:f.write(data)
        print(json.dumps({'kind':result['kind'],'status':result['status'],'report':str(args.report),
                          'report_sha256':hashlib.sha256(data).hexdigest(),
                          'file_sha256':result['file_sha256'],'new_gguf_reads':0,
                          'tokenizer_runtime_quality':'PENDING'}))
        return 0
    except Exception as exc:
        # No raw metadata/token strings or OS paths are surfaced from unexpected errors.
        code=str(exc) if isinstance(exc,CompletionError) else 'SAVED_COMPLETION_INPUT_INVALID'
        print(json.dumps({'kind':'GGUF_HEADER_STRUCTURAL_COMPLETION','status':'FAIL','code':code}))
        return 1


if __name__=='__main__':
    sys.exit(main())
