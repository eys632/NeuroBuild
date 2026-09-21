"""New EXAONE metadata/synthetic CPU controls; never open any real GGUF."""
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

spec=importlib.util.spec_from_file_location('exaone_audit',Path(__file__).with_name('inspect_exaone45_gguf.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def gguf(typ=12,dims=(256,),offset=0,padding=0):
    def string(s):
        b=s.encode();return struct.pack('<Q',len(b))+b
    data=b'GGUF'+struct.pack('<IQQ',3,1,1)
    data+=string('general.architecture')+struct.pack('<I',8)+string('synthetic')
    data+=string('toy.weight')+struct.pack('<I',len(dims))+b''.join(struct.pack('<Q',n) for n in dims)+struct.pack('<IQ',typ,offset)
    data+=b'\0'*(-len(data)%32)
    n=__import__('math').prod(dims)//m.TYPES.get(typ,('',1,1))[1]*m.TYPES.get(typ,('',1,1))[2]
    return data+b'\0'*n+bytes([padding])*(-n%32)


class GenericBoundaryTests(unittest.TestCase):
    def test_copied_generic_ast_exact(self):
        old=Path(__file__).with_name('inspect_qwen38_gguf.py').read_bytes()
        self.assertEqual(hashlib.sha256(old).hexdigest(),m.BASE_HELPER_SHA)
        a=ast.parse(old);b=ast.parse(Path(m.__file__).read_bytes())
        for name in ['AuditError','require','safe_open','read_bound','stat_key','Reader','parse_header','finish_hash']:
            left=next(n for n in a.body if getattr(n,'name',None)==name)
            right=next(n for n in b.body if getattr(n,'name',None)==name)
            self.assertEqual(ast.dump(left),ast.dump(right),name)

    def test_three_explicit_types_layout_and_stream_hash(self):
        self.assertEqual(set(m.TYPES),{0,12,14})
        for typ,nbytes in [(0,1024),(12,144),(14,210)]:
            data=gguf(typ);r=m.Reader(io.BytesIO(data),len(data));h,_=m.parse_header(r)
            self.assertEqual(h['tensor_payload_bytes'],nbytes)
            self.assertEqual(m.finish_hash(r,h),hashlib.sha256(data).hexdigest())

    def test_unknown_dtype_and_invalid_quant_shape_rejected(self):
        for typ in [1,2,8,30,99]:
            data=gguf(typ)
            with self.assertRaisesRegex(m.AuditError,'TENSOR_TYPE_UNSUPPORTED'):
                m.parse_header(m.Reader(io.BytesIO(data),len(data)))
        data=gguf(12,(255,))
        with self.assertRaisesRegex(m.AuditError,'QUANT_ROW_INVALID'):
            m.parse_header(m.Reader(io.BytesIO(data),len(data)))

    def test_payload_padding_not_silently_ignored(self):
        data=gguf(14,padding=1);r=m.Reader(io.BytesIO(data),len(data));h,_=m.parse_header(r)
        with self.assertRaisesRegex(m.AuditError,'NONZERO_TENSOR_PADDING'):m.finish_hash(r,h)

    def test_metadata_only_cannot_emit_pass_or_hash_payload(self):
        data=gguf()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/m.MODEL_RELATIVE;p.parent.mkdir(parents=True);p.write_bytes(data)
            with patch.object(m,'ROOT',root),patch.object(m,'FILE_BYTES',len(data)),patch.object(m,'load_reference',return_value=({}, {}, {}, {})),patch.object(m,'validate_candidate',side_effect=m.AuditError('CONFIG_METADATA_MISMATCH')),patch.object(m,'finish_hash',side_effect=AssertionError('PAYLOAD_READ')):
                out=m.audit(m.MODEL_RELATIVE,metadata_only=True)
                self.assertEqual(out['status'],'DIAGNOSTIC_NOT_PASS')
                self.assertEqual(out['kind'],'GGUF_METADATA_DIAGNOSTIC')
                self.assertEqual(out['candidate_validation_error'],'CONFIG_METADATA_MISMATCH')
                self.assertFalse(out['full_file_sha256_verified'])
                self.assertIsNone(out['file_sha256']);self.assertLess(out['bytes_read'],len(data))
                with self.assertRaisesRegex(m.AuditError,'CONFIG_METADATA_MISMATCH'):
                    m.audit(m.MODEL_RELATIVE)

    def test_full_mode_requires_expected_whole_hash(self):
        data=gguf()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/m.MODEL_RELATIVE;p.parent.mkdir(parents=True);p.write_bytes(data)
            with patch.object(m,'ROOT',root),patch.object(m,'FILE_BYTES',len(data)),patch.object(m,'load_reference',return_value=({}, {}, {}, {})),patch.object(m,'validate_candidate',return_value={}),patch.object(m,'FILE_SHA','0'*64):
                with self.assertRaisesRegex(m.AuditError,'PINNED_FILE_HASH_MISMATCH'):m.audit(m.MODEL_RELATIVE)

    def test_model_path_exact_before_any_open(self):
        with patch.object(m,'load_reference',side_effect=AssertionError('REFERENCE_OPEN')):
            with self.assertRaisesRegex(m.AuditError,'PINNED_MODEL_PATH_MISMATCH'):
                m.audit(Path('var/models/other')/m.REVISION/m.FILENAME)

    def test_symlink_hardlink_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'file').write_bytes(b'original')
            (root/'link').symlink_to(root/'file')
            with self.assertRaises(OSError):
                with m.safe_open(root,Path('link')):pass
            with self.assertRaises(FileExistsError):
                with m.safe_open(root,Path('file'),write=True):pass
            m.os.link(root/'file',root/'alias')
            with self.assertRaisesRegex(m.AuditError,'FILE_MULTIPLE_LINKS'):
                with m.safe_open(root,Path('file')):pass


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Pinned public metadata only; source hashes also checked here.
        cls.config,cls.index,cls.binding,cls.pins=m.load_reference()

    def fixture(self):
        v=m.expected_metadata(self.config)
        meta={}
        for k,x in v.items():
            meta[k]={'type':9,'element_type':7,'count':len(x)} if type(x) is list else {'type':{str:8,int:4,float:6}[type(x)]}
        for k,sub,n in [('tokens',8,153600),('merges',8,152982),('token_type',5,153600)]:
            meta['tokenizer.ggml.'+k]={'type':9,'element_type':sub,'count':n,'elements_wire_sha256':self.binding[k]}
        meta['tokenizer.chat_template']={'type':8,'bytes':5930,'sha256':m.TEMPLATE_SHA}
        rows=[]
        for n,(dims,types) in m.tensor_spec(self.config,self.index).items():
            typ=14 if n=='output.weight' else 12 if len(dims)==2 else 0
            rows.append({'name':n,'shape':dims.copy(),'type_id':typ,'dtype':m.TYPES[typ][0]})
        return {'metadata':meta,'tensor_count':723,'tensors':rows,'dtype_counts':dict(Counter(r['dtype'] for r in rows))},v

    def validate(self,h,v,config=None,index=None):
        return m.validate_candidate(h,v,config or self.config,index or self.index,self.binding)

    def test_exact_untied_main_mtp_geometry(self):
        h,v=self.fixture();out=self.validate(h,v)
        self.assertEqual(out['main_layer_count'],64);self.assertEqual(out['nextn_layer_count'],1)
        self.assertEqual(out['upstream_text_mtp_index_names_matched'],722)
        self.assertEqual(out['expected_tensor_names_shapes_matched'],723)
        self.assertEqual(out['main_kv_f16_context4096_seq1_mib'],1024)
        self.assertEqual(out['largest_dense_matrix_f32_bytes'],3145728000)
        self.assertEqual(len([r for r in h['tensors'] if r['name'].startswith('blk.64.')]),15)
        spec=m.tensor_spec(self.config,self.index)
        self.assertEqual(spec['blk.64.nextn.eh_proj.weight'][0],[10240,5120])
        self.assertEqual(spec['blk.0.attn_k.weight'][0],[5120,1024])
        self.assertEqual(spec['blk.63.ffn_down.weight'][0],[27392,5120])

    def test_main_nextn_layer_and_swa_metadata_tampering(self):
        for key,value in [('exaone4.block_count',64),('exaone4.nextn_predict_layers',0),('exaone4.attention.head_count_kv',40),('exaone4.attention.sliding_window',128)]:
            h,v=self.fixture();v[key]=value
            with self.assertRaisesRegex(m.AuditError,'CONFIG_METADATA_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();v['exaone4.attention.sliding_window_pattern'][3]=True
        with self.assertRaisesRegex(m.AuditError,'CONFIG_METADATA_MISMATCH'):self.validate(h,v)

    def test_model_config_and_hf_inventory_not_inferred_from_gguf(self):
        h,v=self.fixture();cfg=copy.deepcopy(self.config);cfg['tie_word_embeddings']=True
        with self.assertRaisesRegex(m.AuditError,'UPSTREAM_CONFIG_UNEXPECTED'):self.validate(h,v,config=cfg)
        idx=copy.deepcopy(self.index);idx['weight_map'].pop('mtp.norm.weight')
        with self.assertRaisesRegex(m.AuditError,'UPSTREAM_TEXT_MTP_INDEX_MISMATCH'):self.validate(h,v,index=idx)

    def test_missing_output_mtp_and_extra_tensor_rejected(self):
        for name in ['output.weight','token_embd.weight','blk.64.nextn.hnorm.weight','rope_freqs.weight']:
            h,v=self.fixture();h['tensors']=[r for r in h['tensors'] if r['name']!=name]
            with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SET_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['tensors'][0]['name']='visual.extra.weight'
        with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SET_MISMATCH'):self.validate(h,v)

    def test_shape_changes_and_q6_wrong_role_rejected(self):
        for name in ['output.weight','blk.0.attn_k.weight','blk.64.nextn.eh_proj.weight','rope_freqs.weight']:
            h,v=self.fixture();r=next(r for r in h['tensors'] if r['name']==name);r['shape'][0]+=256
            with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH'):self.validate(h,v)
        for name in ['token_embd.weight','blk.1.attn_q.weight','blk.1.ffn_gate.weight','blk.64.nextn.eh_proj.weight']:
            h,v=self.fixture();r=next(r for r in h['tensors'] if r['name']==name);r['type_id']=14;r['dtype']='q6_K'
            with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH'):self.validate(h,v)

    def test_q6_only_on_source_permitted_matrix_roles(self):
        h,v=self.fixture()
        for r in h['tensors']:
            if r['name'].endswith(('attn_v.weight','ffn_down.weight')):r.update(type_id=14,dtype='q6_K')
        h['dtype_counts']=dict(Counter(r['dtype'] for r in h['tensors']))
        self.validate(h,v)
        h['dtype_counts']['q6_K']+=1
        with self.assertRaisesRegex(m.AuditError,'ROLE_DTYPE_DISTRIBUTION_MISMATCH'):self.validate(h,v)

    def test_vector_dtype_and_matrix_f32_are_not_broadly_allowed(self):
        for name,typ in [('output_norm.weight',12),('blk.64.nextn.enorm.weight',14),('blk.0.attn_q.weight',0)]:
            h,v=self.fixture();r=next(r for r in h['tensors'] if r['name']==name);r['type_id']=typ
            with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH'):self.validate(h,v)

    def test_tokenizer_pretype_array_order_and_template_exact(self):
        h,v=self.fixture();v['tokenizer.ggml.pre']='exaone4'
        with self.assertRaisesRegex(m.AuditError,'CONFIG_METADATA_MISMATCH'):self.validate(h,v)
        for key in ['tokens','merges','token_type']:
            h,v=self.fixture();h['metadata']['tokenizer.ggml.'+key]['elements_wire_sha256']='0'*64
            with self.assertRaisesRegex(m.AuditError,'TOKENIZER_CONTENT_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['metadata']['tokenizer.chat_template']['bytes']-=1
        with self.assertRaisesRegex(m.AuditError,'EMBEDDED_TEMPLATE_MISMATCH'):self.validate(h,v)

    def test_architecture_extra_wrong_wire_type_bos_override(self):
        h,v=self.fixture();h['metadata']['exaone4.expert_count']={'type':4};v['exaone4.expert_count']=8
        with self.assertRaisesRegex(m.AuditError,'ARCHITECTURE_METADATA_UNEXPECTED'):self.validate(h,v)
        h,v=self.fixture();h['metadata']['exaone4.attention.sliding_window_pattern']['element_type']=4
        with self.assertRaisesRegex(m.AuditError,'CONFIG_METADATA_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['metadata']['tokenizer.ggml.add_bos_token']={'type':7};v['tokenizer.ggml.add_bos_token']=True
        with self.assertRaisesRegex(m.AuditError,'OPTIONAL_METADATA_MISMATCH'):self.validate(h,v)


if __name__=='__main__':unittest.main()
