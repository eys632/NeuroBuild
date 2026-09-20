"""New12 boundary controls only. Synthetic headers; no GGUF/native/model access."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import unittest

HERE=Path(__file__).parent

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

m=load('gemma12_audit',HERE/'inspect_gemma4_12b_gguf.py')
c=load('gemma12_compare',HERE/'compare_gemma4_12b_tokenizer_headers.py')
CONFIG=json.loads((m.ROOT/m.META/'config.json').read_text())
OLD=json.loads((m.ROOT/c.OLD_REPORT).read_text())


def numeric_array(values,subtype):
    return {'type':9,'element_type':subtype,'count':len(values),
            'elements_wire_sha256':hashlib.sha256(b''.join(struct.pack('<'+m.SCALARS[subtype],x) for x in values)).hexdigest(),
            'wire_bytes':12+len(values)*struct.calcsize('<'+m.SCALARS[subtype])}


def fixture():
    h=copy.deepcopy(OLD['header'])
    values={k:v['value'] for k,v in h['metadata'].items() if 'value' in v}
    values.update({'general.architecture':'gemma4','general.type':'model','tokenizer.ggml.model':'gemma4',
                   'gemma4.block_count':48,'gemma4.embedding_length':3840,'gemma4.feed_forward_length':15360,
                   'gemma4.attention.head_count':16,'gemma4.final_logit_softcapping':30.0,
                   'gemma4.attention.head_count_kv':[1 if i%6==5 else 8 for i in range(48)],
                   'gemma4.attention.sliding_window_pattern':[i%6!=5 for i in range(48)],
                   'tokenizer.ggml.suppress_tokens':[258883,258882]})
    for k,v in values.items():
        if type(v) is list:h['metadata'][k]=numeric_array(v,7 if type(v[0]) is bool else 5)
        elif type(v) is not str:h['metadata'][k]['value']=v
    h['tensor_count']=667
    h['tensors']=[{'name':n,'shape':dims,'type_id':next(iter(types))}
                  for n,(dims,types) in m.tensor_spec(CONFIG).items()]
    h['dtype_counts']={'f32':338,'q6_K':1,'q4_0':328}
    token_bind={x:h['metadata']['tokenizer.ggml.'+x]['elements_wire_sha256'] for x in ('tokens','merges')}
    gen={'generation_eos_token_ids':[1,106,50],'source_eog_token_ids':[1,106,50]}
    return h,values,token_bind,gen


def synthetic_report(h):
    return {'kind':'GGUF_HEADER_AUDIT','status':'PASS','model_id':m.MODEL_ID,'revision':m.REVISION,
            'file_sha256':m.FILE_SHA,'file_bytes':m.FILE_BYTES,'full_file_sha256_verified':True,
            'helper_sha256':c.AUDITOR_SHA,'runtime_source_revision':m.RUNTIME,
            'source_metadata_sha256':{'tokenizer':m.TOKENIZER_SHA,'template':m.TEMPLATE_SHA},'header':h}


class NewGemma12Boundaries(unittest.TestCase):
    def test_config48_geometry_strict_and_source_inventory_not_claimed(self):
        h,v,t,g=fixture();result=m.validate_candidate(h,v,CONFIG,t,g)
        self.assertEqual((result['expected_tensor_names_shapes_matched'],result['expected_text_tensor_roles']),(667,666))
        self.assertIsNone(result['qat_text_index_names_matched'])
        self.assertEqual(result['kv_f16_context4096_seq1_ubatch64_swa_full_false_mib'],464)
        spec=m.tensor_spec(CONFIG)
        self.assertEqual(spec['blk.0.attn_q.weight'],([3840,4096],{2}))
        self.assertEqual(spec['blk.5.attn_q.weight'],([3840,8192],{2}))
        self.assertEqual(spec['blk.5.attn_k.weight'],([3840,512],{2}))
        self.assertNotIn('blk.5.attn_v.weight',spec)
        self.assertEqual(spec['token_embd.weight'],([3840,262144],{14}))
        for key,value in [('num_hidden_layers',60),('num_global_key_value_heads',4),('final_logit_softcapping',0.0)]:
            with self.subTest(key=key), self.assertRaises(m.AuditError):
                bad=copy.deepcopy(CONFIG);bad['text_config'][key]=value;m.tensor_spec(bad)

    def test_new_role_policy_rejects_embedding_or_matrix_vector_changes(self):
        for name,typ in [('token_embd.weight',2),('blk.0.attn_q.weight',14),('blk.0.attn_norm.weight',1)]:
            with self.subTest(name=name), self.assertRaises(m.AuditError):
                h,v,t,g=fixture();next(x for x in h['tensors'] if x['name']==name)['type_id']=typ
                m.validate_candidate(h,v,CONFIG,t,g)
        h,v,t,g=fixture();h['tensors'][-1]['shape']=[3840,2048]
        with self.assertRaises(m.AuditError):m.validate_candidate(h,v,CONFIG,t,g)

    def test_softcap30_and_kv48_wire_types_required(self):
        for key,value,typ in [('gemma4.final_logit_softcapping',0.0,6),
                              ('gemma4.final_logit_softcapping',30,4),
                              ('gemma4.final_logit_softcapping',30.0,12)]:
            with self.subTest(value=value,typ=typ),self.assertRaises(m.AuditError):
                h,v,t,g=fixture();v[key]=value;h['metadata'][key]['type']=typ
                m.validate_candidate(h,v,CONFIG,t,g)
        h,v,t,g=fixture();h['metadata']['gemma4.attention.head_count_kv']['element_type']=4
        with self.assertRaises(m.AuditError):m.validate_candidate(h,v,CONFIG,t,g)

    def test_suppression_signed_array_exact_and_valid_ids(self):
        for ids,subtype in [([258883,258882],4),([258883],5),([258883,258883],5),
                            ([True,258882],5),([-1,258882],5),([262144,258882],5),([258882,258883],5)]:
            with self.subTest(ids=ids,subtype=subtype),self.assertRaises(m.AuditError):
                h,v,t,g=fixture();k='tokenizer.ggml.suppress_tokens';v[k]=ids
                h['metadata'][k]=numeric_array(ids,subtype);m.validate_suppression(h,v,g)
        h,v,t,g=fixture();del h['metadata']['tokenizer.ggml.suppress_tokens']
        with self.assertRaises(m.AuditError):m.validate_suppression(h,v,g)

    def test_suppression_source_and_header_eog_collisions_rejected(self):
        generation={'suppress_tokens':[258883,258882],'eos_token_id':[1,106,50]}
        stub={'model':{'vocab':{'<eos>':1,'<turn|>':106,'<|tool_response>':50}}}
        self.assertEqual(m.generation_bindings(generation,stub)['source_eog_token_ids'],[1,50,106])
        stub['model']['vocab']['[EOS]']=258883
        with self.assertRaises(m.AuditError):m.generation_bindings(generation,stub)
        h,v,t,g=fixture();k='tokenizer.ggml.eot_token_id';h['metadata'][k]={'type':4,'value':258882};v[k]=258882
        with self.assertRaises(m.AuditError):m.validate_suppression(h,v,g)

    def test_saved_metadata_exact_except_suppression_not_full_sampling_equivalence(self):
        h,_,_,_=fixture();r=c.compare(OLD,synthetic_report(h),m)
        self.assertEqual(r['new_tokenizer_metadata_key_count'],r['old_tokenizer_metadata_key_count']+1)
        self.assertFalse(r['sampling_difference']['complete_effective_sampling_equivalent'])
        self.assertEqual(r['new_native_public_or_vocab_or_context_executions'],0)

    def test_saved_metadata_rejects_any_tokenizer_value_type_hash_or_presence_delta(self):
        for key,field,value in [('tokenizer.ggml.scores','elements_wire_sha256','0'*64),
                               ('tokenizer.ggml.tokens','element_type',5),
                               ('tokenizer.ggml.add_bos_token','value',False),
                               ('tokenizer.chat_template','sha256','0'*64)]:
            with self.subTest(key=key),self.assertRaises(m.AuditError):
                h,_,_,_=fixture();h['metadata'][key][field]=value;c.compare(OLD,synthetic_report(h),m)
        for add in (False,True):
            with self.subTest(add=add),self.assertRaises(m.AuditError):
                h,_,_,_=fixture()
                if add:h['metadata']['tokenizer.chat_template.tool_use']={'type':8,'bytes':0,'sha256':hashlib.sha256(b'').hexdigest()}
                else:del h['metadata']['tokenizer.ggml.mask_token_id']
                c.compare(OLD,synthetic_report(h),m)

    def test_saved_metadata_requires_real_full_audit_identity_and_exact_suppression_hash(self):
        for key,value in [('status','DIAGNOSTIC_NOT_PASS'),('file_sha256','0'*64),
                          ('full_file_sha256_verified',False),('helper_sha256','0'*64)]:
            with self.subTest(key=key),self.assertRaises(m.AuditError):
                h,_,_,_=fixture();new=synthetic_report(h);new[key]=value;c.compare(OLD,new,m)
        h,_,_,_=fixture();h['metadata']['tokenizer.ggml.suppress_tokens']['elements_wire_sha256']='0'*64
        with self.assertRaises(m.AuditError):c.compare(OLD,synthetic_report(h),m)


if __name__=='__main__':unittest.main()
