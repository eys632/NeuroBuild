"""One bounded header-only comparison; emit IDs/counts/hashes, never token text."""
from pathlib import Path
import base64, hashlib, json, os, struct, types

ROOT=Path('/home/a202192020/NeuroBuild_v2')
SCRIPT=ROOT/'var/research/complete_ministral3_saved_header.py'
SCRIPT_SHA='b004ff14be33b99e3c585b94d8f5d9980266e91a55e7365b575ff0b4fbab011c'
OUT=ROOT/'var/research/ministral3-header-token-diagnostic.json'

def main():
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='' and not OUT.exists()
    raw=SCRIPT.read_bytes();assert hashlib.sha256(raw).hexdigest()==SCRIPT_SHA
    m=types.ModuleType('ministral_saved_definition');m.__file__=str(SCRIPT)
    exec(compile(raw,str(SCRIPT),'exec'),m.__dict__)
    b=m.load_base()
    old=json.loads(b.read_bound(m.AUDIT,m.AUDIT_SHA,2*1024**2))
    tek=json.loads(b.read_bound(b.META/'bf16/tekken.json',b.TEKKEN_SHA,20*1024**2))
    encoder=m.bytes_to_unicode()
    expected=[x['token_str'].encode() for x in tek['special_tokens']]
    expected.extend(''.join(encoder[i] for i in base64.b64decode(x['token_bytes'],validate=True)).encode() for x in tek['vocab'])
    assert len(expected)==131072 and len(set(expected))==131072
    reverse={v:i for i,v in enumerate(expected)}
    mismatch=[];special_count=ordinary_count=0;critical={i:None for i in (0,1,2,3,4,9,11,17,18,32)}
    observed={}
    with b.safe_open(ROOT,b.MODEL_PATH) as stream:
        before=os.fstat(stream.fileno());assert before.st_size==b.FILE_BYTES
        r=b.Reader(stream,before.st_size)
        assert r.read(4)==b'GGUF' and r.num('I')==3
        assert r.num('Q')==363
        count=r.num('Q');assert count==53
        for _ in range(count):
            key,_raw=r.string(256);typ=r.num('I')
            if typ==9:
                sub,n=r.num('I'),r.num('Q');assert n<=b.ARRAY_CAP
                digest=hashlib.sha256()
                for i in range(n):
                    if sub==8:
                        value,content=r.string()
                        digest.update(struct.pack('<Q',len(content)));digest.update(content)
                        if key=='tokenizer.ggml.tokens':
                            assert n==131072
                            equal=content==expected[i]
                            if i in critical:critical[i]=equal
                            if not equal:
                                special_count+=int(i<1000);ordinary_count+=int(i>=1000)
                                mismatch.append({'id':i,'kind':'special' if i<1000 else 'ordinary',
                                    'saved_token_bytes':len(content),'reference_token_bytes':len(expected[i]),
                                    'saved_token_sha256':hashlib.sha256(content).hexdigest(),
                                    'reference_token_sha256':hashlib.sha256(expected[i]).hexdigest(),
                                    'canonical_index_of_saved_token':reverse.get(content)})
                    else:
                        assert sub in b.SCALARS
                        digest.update(struct.pack('<'+b.SCALARS[sub],r.value(sub)))
                observed[key]={'element_type':sub,'count':n,'elements_wire_sha256':digest.hexdigest()}
                assert all(old['header']['metadata'][key][k]==v for k,v in observed[key].items())
            elif typ==8:r.string()
            else:r.value(typ)
        assert b.stat_key(before)==b.stat_key(os.fstat(stream.fileno()))
        read_bytes=r.offset
    assert all(v is not None for v in critical.values())
    result={'kind':'MINISTRAL3_HEADER_ONLY_TOKEN_REFERENCE_DIAGNOSTIC',
        'original_audit_sha256':m.AUDIT_SHA,'canonical_tekken_sha256':b.TEKKEN_SHA,
        'source_helper_sha256':SCRIPT_SHA,'helper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'model_path':str(b.MODEL_PATH),'header_bytes_read':read_bytes,'tensor_payload_bytes_read':0,
        'gguf_open_count':1,'native_calls':0,'tokenize_calls':0,'model_calls':0,
        'all_saved_array_fingerprints_match':True,'total_mismatches':len(mismatch),
        'special_mismatches':special_count,'ordinary_mismatches':ordinary_count,
        'critical_special_id_text_matches':critical,'mismatches':mismatch,
        'note':'Diagnostic only. Exact conversion lineage and native behavior remain unproven. No token text emitted.'}
    with OUT.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('mismatches','critical_special_id_text_matches')}))
    print(json.dumps({'critical_specials_all_match':all(critical.values()),'mismatch_ids':[v['id'] for v in mismatch][:64],
        'report_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()}))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'status':'FAIL','error_type':type(exc).__name__}));raise SystemExit(1)
