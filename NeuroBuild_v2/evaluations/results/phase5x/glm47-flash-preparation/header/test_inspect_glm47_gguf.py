"""GLM-only synthetic controls; no real GGUF, native, dataset or GPU access."""
import ast
from collections import Counter
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

p=Path(__file__).with_name('inspect_glm47_gguf.py')
s=importlib.util.spec_from_file_location('glm_audit',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


def toy(typ=6, dims=(192,)):
    def string(x):
        b=x.encode();return struct.pack('<Q',len(b))+b
    data=b'GGUF'+struct.pack('<IQQ',3,1,1)
    data+=string('general.architecture')+struct.pack('<I',8)+string('synthetic')
    data+=string('toy.weight')+struct.pack('<I',len(dims))+b''.join(struct.pack('<Q',x) for x in dims)+struct.pack('<IQ',typ,0)
    data+=b'\0'*(-len(data)%32)
    n=__import__('math').prod(dims)//m.TYPES.get(typ,('',1,1))[1]*m.TYPES.get(typ,('',1,1))[2]
    return data+b'\0'*n+b'\0'*(-n%32)


class ParserReuseTests(unittest.TestCase):
    def test_eight_generic_definitions_ast_exact(self):
        old=Path(__file__).with_name('inspect_qwen38_gguf.py').read_bytes()
        self.assertEqual(hashlib.sha256(old).hexdigest(),m.BASE_HELPER_SHA)
        a,b=ast.parse(old),ast.parse(p.read_bytes())
        for name in ('AuditError','require','safe_open','read_bound','stat_key','Reader','parse_header','finish_hash'):
            aa=next(n for n in a.body if getattr(n,'name',None)==name)
            bb=next(n for n in b.body if getattr(n,'name',None)==name)
            self.assertEqual(ast.dump(aa),ast.dump(bb),name)

    def test_new_q5_0_and_q5_k_block_layout_and_unknown_rejection(self):
        self.assertEqual(set(m.TYPES),{0,1,6,8,12,13,14,30})
        for typ,dims,nbytes in ((6,(192,),132),(13,(256,),176),(1,(192,),384),(8,(192,),204),(30,(192,),384)):
            raw=toy(typ,dims);r=m.Reader(io.BytesIO(raw),len(raw));h,_=m.parse_header(r)
            self.assertEqual(h['tensor_payload_bytes'],nbytes)
            self.assertEqual(m.finish_hash(r,h),hashlib.sha256(raw).hexdigest())
        for typ in (2,7,9,99):
            raw=toy(typ)
            with self.assertRaisesRegex(m.AuditError,'TENSOR_TYPE_UNSUPPORTED'):
                m.parse_header(m.Reader(io.BytesIO(raw),len(raw)))
        raw=toy(12,(192,))
        with self.assertRaisesRegex(m.AuditError,'QUANT_ROW_INVALID'):
            m.parse_header(m.Reader(io.BytesIO(raw),len(raw)))

    def test_new_audit_diagnostic_never_reads_payload_or_emits_pass(self):
        raw=toy()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);fp=root/m.MODEL_RELATIVE;fp.parent.mkdir(parents=True);fp.write_bytes(raw)
            with patch.object(m,'ROOT',root),patch.object(m,'FILE_BYTES',len(raw)),patch.object(m,'load_reference',return_value=({}, {}, {}, {})),patch.object(m,'validate_candidate',side_effect=m.AuditError('CONFIG_METADATA_MISMATCH')),patch.object(m,'finish_hash',side_effect=AssertionError('PAYLOAD_READ')):
                out=m.audit(m.MODEL_RELATIVE,metadata_only=True)
                self.assertEqual(out['status'],'DIAGNOSTIC_NOT_PASS')
                self.assertFalse(out['full_file_sha256_verified']);self.assertIsNone(out['file_sha256'])
                self.assertLess(out['bytes_read'],len(raw))
                with self.assertRaisesRegex(m.AuditError,'CONFIG_METADATA_MISMATCH'):m.audit(m.MODEL_RELATIVE)

    def test_new_audit_fullhash_and_path_required(self):
        with patch.object(m,'load_reference',side_effect=AssertionError('REFERENCE_READ')):
            with self.assertRaisesRegex(m.AuditError,'PINNED_MODEL_PATH_MISMATCH'):m.audit(Path('var/other'))
        raw=toy()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);fp=root/m.MODEL_RELATIVE;fp.parent.mkdir(parents=True);fp.write_bytes(raw)
            with patch.object(m,'ROOT',root),patch.object(m,'FILE_BYTES',len(raw)),patch.object(m,'load_reference',return_value=({}, {}, {}, {})),patch.object(m,'validate_candidate',return_value={}),patch.object(m,'FILE_SHA','0'*64):
                with self.assertRaisesRegex(m.AuditError,'PINNED_FILE_HASH_MISMATCH'):m.audit(m.MODEL_RELATIVE)


class GlmSemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Existing pinned official metadata/source only, never model/header bytes.
        cls.cfg,cls.index,cls.bind,cls.pins=m.load_reference()

    def fixture(self,ftype=14):
        v=m.expected_metadata(self.cfg,ftype)
        meta={k:{'type':{str:8,int:4,float:6,bool:7}[type(x)]} for k,x in v.items()}
        for k,typ,n in [('tokens',8,154880),('token_type',5,154880),('merges',8,321649)]:
            meta['tokenizer.ggml.'+k]={'type':9,'element_type':typ,'count':n,'elements_wire_sha256':self.bind[k]}
        meta['tokenizer.chat_template']={'type':8,'bytes':m.TEMPLATE_BYTES,'sha256':m.TEMPLATE_SHA}
        rows=[]
        for name,(dims,types) in m.tensor_spec(self.cfg,self.index,ftype).items():
            typ=next(iter(types));rows.append({'name':name,'shape':dims.copy(),'type_id':typ,'dtype':m.TYPES[typ][0]})
        return {'metadata':meta,'tensors':rows,'tensor_count':len(rows),'dtype_counts':dict(Counter(r['dtype'] for r in rows))},v

    def validate(self,h,v,cfg=None,index=None):
        return m.validate_candidate(h,v,cfg or self.cfg,index or self.index,self.bind)

    def test_two_real_ftype_variants_determined_not_filename_assumed(self):
        for ftype,name,counts in [(14,'Q4_K_S',{'f32':290,'q4_K':518,'q5_K':11,'q5_0':48,'q6_K':1}),
                                  (15,'Q4_K_M',{'f32':290,'q4_K':482,'q5_0':48,'q6_K':48})]:
            h,v=self.fixture(ftype);out=self.validate(h,v)
            self.assertEqual(out['quantization'],name);self.assertEqual(out['actual_role_dtype_counts'],counts)
            self.assertEqual(out['expected_tensor_names_shapes_matched'],868)
            self.assertEqual(out['main_kv_f16_context4096_seq1_mib'],211.5)
            self.assertEqual(out['largest_tensor_f32_bytes'],1210*1024**2)
        for ftype in (False,14.0,12,13,16):
            h,v=self.fixture();v['general.file_type']=ftype
            with self.assertRaisesRegex(m.AuditError,'FILE_TYPE_UNSUPPORTED'):self.validate(h,v)

    def test_default_s_m_layer_rules_and_q5_0_exact_role(self):
        for ftype in (14,15):
            for name,wrong in [('blk.0.attn_k_b.weight',12),('blk.1.attn_v_b.weight',6),
                ('blk.1.ffn_gate_inp.weight',12),('output.weight',12),
                ('blk.47.nextn.shared_head_head.weight',14),('blk.7.ffn_down_exps.weight',14),
                ('blk.0.ffn_down.weight',12),('blk.1.ffn_gate_exps.weight',14)]:
                h,v=self.fixture(ftype);r=next(r for r in h['tensors'] if r['name']==name)
                r.update(type_id=wrong,dtype=m.TYPES[wrong][0])
                with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH'):self.validate(h,v)
        h,v=self.fixture(14);v['general.file_type']=15
        with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH'):self.validate(h,v)

    def test_no_legacy_mla_silent_mtp_drop_fusion_or_tied_output(self):
        for name in ('output.weight','token_embd.weight','blk.47.nextn.embed_tokens.weight',
                     'blk.47.nextn.shared_head_head.weight','blk.47.nextn.eh_proj.weight'):
            h,v=self.fixture();h['tensors']=[r for r in h['tensors'] if r['name']!=name]
            with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SET_MISMATCH'):self.validate(h,v)
        for name in ('blk.0.attn_kv_b.weight','blk.1.ffn_gate_up_exps.weight','rope_freqs.weight'):
            h,v=self.fixture();h['tensors'][0]['name']=name
            with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SET_MISMATCH'):self.validate(h,v)
        cfg=copy.deepcopy(self.cfg);cfg['tie_word_embeddings']=True;h,v=self.fixture()
        with self.assertRaisesRegex(m.AuditError,'UPSTREAM_CONFIG_UNEXPECTED'):self.validate(h,v,cfg=cfg)
        idx=copy.deepcopy(self.index);idx['weight_map'].pop('model.layers.47.hnorm.weight')
        with self.assertRaisesRegex(m.AuditError,'UPSTREAM_MTP_INDEX_MISMATCH'):self.validate(h,v,index=idx)

    def test_geometry_and_metadata_overrides_fail(self):
        for key,val in [('deepseek2.block_count',47),('deepseek2.nextn_predict_layers',0),
            ('deepseek2.attention.head_count_kv',20),('deepseek2.attention.key_length',256),
            ('deepseek2.attention.value_length_mla',512),('deepseek2.expert_count',8)]:
            h,v=self.fixture();v[key]=val
            with self.assertRaisesRegex(m.AuditError,'CONFIG_METADATA_MISMATCH'):self.validate(h,v)
        for name in ('blk.0.attn_k_b.weight','blk.1.ffn_down_exps.weight','blk.47.nextn.eh_proj.weight'):
            h,v=self.fixture();r=next(r for r in h['tensors'] if r['name']==name);r['shape'][0]+=32
            with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['metadata']['deepseek2.sliding_window']={'type':4};v['deepseek2.sliding_window']=128
        with self.assertRaisesRegex(m.AuditError,'ARCHITECTURE_METADATA_UNEXPECTED'):self.validate(h,v)

    def test_padded_vocab_types_merges_template_and_special_flags_exact(self):
        for key in ('tokens','token_type','merges'):
            h,v=self.fixture();h['metadata']['tokenizer.ggml.'+key]['elements_wire_sha256']='0'*64
            with self.assertRaisesRegex(m.AuditError,'TOKENIZER_CONTENT_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['metadata']['tokenizer.ggml.tokens']['count']=154856
        with self.assertRaisesRegex(m.AuditError,'TOKENIZER_ARRAY_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['metadata']['tokenizer.chat_template']['bytes']-=1
        with self.assertRaisesRegex(m.AuditError,'EMBEDDED_TEMPLATE_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['metadata']['tokenizer.ggml.add_bos_token']={'type':7};v['tokenizer.ggml.add_bos_token']=True
        with self.assertRaisesRegex(m.AuditError,'OPTIONAL_METADATA_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['metadata']['tokenizer.ggml.add_space_prefix']={'type':7};v['tokenizer.ggml.add_space_prefix']=True
        with self.assertRaisesRegex(m.AuditError,'TOKENIZER_METADATA_UNEXPECTED'):self.validate(h,v)

    def test_description_types_never_authorize_candidate_roles(self):
        for typ in (1,8,30):
            h,v=self.fixture();r=next(r for r in h['tensors'] if r['name']=='blk.1.attn_q_a.weight')
            r.update(type_id=typ,dtype=m.TYPES[typ][0])
            with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH'):self.validate(h,v)

    def test_scalar_wire_type_and_dtype_summary_not_trusted(self):
        h,v=self.fixture();h['metadata']['deepseek2.expert_weights_norm']['type']=4
        with self.assertRaisesRegex(m.AuditError,'CONFIG_METADATA_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['dtype_counts']['q4_K']+=1
        with self.assertRaisesRegex(m.AuditError,'ROLE_DTYPE_DISTRIBUTION_MISMATCH'):self.validate(h,v)


if __name__=='__main__': unittest.main(verbosity=2)
