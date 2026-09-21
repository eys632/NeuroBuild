"""Prepare a separately labelled diagnostic reference; never application repair."""
from pathlib import Path
import hashlib,json,os,resource,sys
from datetime import datetime,timezone
from tokenizers import Tokenizer,__version__
ROOT=Path('/home/a202192020/NeuroBuild_v2');BASE=ROOT/'var/research/native-exaone45-contract'
FIXTURE=BASE/'official-tokenizer-fixture.json';TOKENIZER=ROOT/'var/research/exaone45-33b-candidate-metadata/upstream/tokenizer.json'
FIXTURE_SHA='49b40b3390cba92f3088c22606632348ba261e69ea0b385b74aa9126be8c46cb'
TOKENIZER_SHA='0bd798efa30739e209d51f36cfc2f0a636711e37ad9d69b77e4e5c8ca5f09fab'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert len(sys.argv)==1 and Path(sys.prefix)==ROOT/'.conda-vllm' and os.environ.get('CUDA_VISIBLE_DEVICES')==''
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 assert sha(FIXTURE)==FIXTURE_SHA and sha(TOKENIZER)==TOKENIZER_SHA
 fixture=json.loads(FIXTURE.read_text());obj=json.loads(TOKENIZER.read_text());assert obj['normalizer']=={'type':'NFC'}
 original=dict(obj);obj['normalizer']=None
 assert {k:v for k,v in original.items() if k!='normalizer'}=={k:v for k,v in obj.items() if k!='normalizer'}
 derived=json.dumps(obj,ensure_ascii=False,separators=(',',':'));tokenizer=Tokenizer.from_str(derived)
 rows=[];observations=[]
 for i,row in enumerate(fixture['tokenizer_parity']):
  text=row['text'];ids=tokenizer.encode(text,add_special_tokens=False).ids;decoded=tokenizer.decode(ids,skip_special_tokens=False)
  rows.append({'text':text,'expected_token_ids':ids});observations.append({'index':i,'raw_roundtrip':decoded==text,'official_ids_equal':ids==row['expected_token_ids']})
 assert len(rows)==20 and all(x['raw_roundtrip'] for x in observations)
 assert [x['text'] for x in rows]==[x['text'] for x in fixture['tokenizer_parity']]
 assert 'torch' not in sys.modules and 'transformers' not in sys.modules
 report={'kind':'EXAONE45_DERIVED_NO_NFC_PUBLIC_DIAGNOSTIC_REFERENCE','status':'DIAGNOSTIC_REFERENCE_ONLY_NOT_ADOPTED',
  'at_utc':datetime.now(timezone.utc).isoformat(),'reference_kind':'official_metadata_with_only_NFC_normalizer_disabled',
  'official_fixture_sha256':FIXTURE_SHA,'official_tokenizer_sha256':TOKENIZER_SHA,'derived_in_memory_tokenizer_sha256':hashlib.sha256(derived.encode()).hexdigest(),
  'corpus_text_sha256':fixture['corpus_text_sha256'],'case_count':20,'official_fixture_text_order_unchanged':True,
  'raw_roundtrip_count':20,'official_id_difference_indices':[x['index'] for x in observations if not x['official_ids_equal']],
  'tokenizer_parity':rows,'observations':observations,'tokenizers_version':__version__,'helper_sha256':sha(Path(__file__)),
  'native_calls':0,'gpu_calls':0,'model_calls':0,'application_input_output_nfc_repair':False,
  'limitation':'Diagnostic derived reference is not official HF equivalence, not a production input transform, and not a selected runtime contract.'}
 p=BASE/'raw-reference-diagnostic.json'
 with p.open('x') as f:json.dump(report,f,indent=2,ensure_ascii=False);f.write('\n')
 print(json.dumps({'status':report['status'],'case_count':20,'raw_roundtrips':20,'path':str(p.relative_to(ROOT)),'sha256':sha(p)}))
if __name__=='__main__':main()
