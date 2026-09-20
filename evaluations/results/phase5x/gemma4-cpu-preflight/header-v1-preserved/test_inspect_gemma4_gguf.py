"""Synthetic stdlib CPU tests only. No real GGUF/model/native/GPU access."""
import importlib.util
import io
import json
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
import copy
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('gemma4_header_audit', Path(__file__).with_name('inspect_gemma4_gguf.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def string(s):
    b = s.encode() if isinstance(s,str) else s
    return struct.pack('<Q',len(b))+b


def value(typ,v):
    if typ == 8:
        return string(v)
    if typ == 9:
        subtype,items = v
        return struct.pack('<IQ',subtype,len(items))+b''.join(value(subtype,x) for x in items)
    return struct.pack('<'+m.SCALARS[typ],v)


def make(*,kv=None,tensors=None,version=3,tail=b'',padding_byte=0):
    kv = kv if kv is not None else [('general.architecture',8,'synthetic')]
    tensors = tensors if tensors is not None else [('toy.weight',[4],0,0)]
    data = b'GGUF'+struct.pack('<IQQ',version,len(tensors),len(kv))
    data += b''.join(string(k)+struct.pack('<I',t)+value(t,v) for k,t,v in kv)
    for name,dims,typ,offset in tensors:
        data += string(name)+struct.pack('<I',len(dims))
        data += b''.join(struct.pack('<Q',d) for d in dims)
        data += struct.pack('<IQ',typ,offset)
    data += bytes([padding_byte])*(-len(data)%32)
    extent = 0
    for _,dims,typ,offset in tensors:
        if typ in m.TYPES and dims:
            _,block,blockbytes = m.TYPES[typ]
            size = max(1,__import__('math').prod(dims)//block*blockbytes)
            extent = max(extent,offset+((size+31)//32)*32)
    if extent > 1024*1024:
        extent = 32
    return data+b'\0'*extent+tail


def parse(data):
    reader = m.Reader(io.BytesIO(data),len(data))
    header,values = m.parse_header(reader)
    digest = m.finish_hash(reader,header)
    return header,values,digest


class HeaderTests(unittest.TestCase):
    def bad(self, data, code=None):
        with self.assertRaises(m.AuditError) as cm:
            parse(data)
        if code:
            self.assertEqual(str(cm.exception),code)

    def test_valid_stream_hash_and_padding(self):
        data=make()
        h,v,digest=parse(data)
        self.assertEqual(digest,hashlib.sha256(data).hexdigest())
        self.assertEqual(h['tensor_payload_bytes'],16)
        self.assertEqual(h['tensor_padding_bytes'],16)
        self.assertEqual(v['general.architecture'],'synthetic')

    def test_all_four_quant_types(self):
        tensors=[('f32',[8],0,0),('q4',[32],2,32),('f16',[16],1,64),('bf16',[16],30,96)]
        h,_,_=parse(make(tensors=tensors))
        self.assertEqual(h['dtype_counts'],{'f32':1,'q4_0':1,'f16':1,'bf16':1})

    def test_strings_are_hashes_not_reported_tokens(self):
        h,values,_=parse(make(kv=[('tokenizer.ggml.tokens',9,(8,['secret token','다른 토큰'])),
                                 ('tokenizer.chat_template',8,'PRIVATE TEMPLATE')]))
        dump=json.dumps(h,ensure_ascii=False)
        self.assertNotIn('secret token',dump)
        self.assertNotIn('PRIVATE TEMPLATE',dump)
        self.assertNotIn('tokenizer.chat_template',values)
        self.assertNotIn('tokenizer.ggml.tokens',values)

    def test_magic_version_truncation(self):
        self.bad(b'BAD!'+make()[4:],'MAGIC_INVALID')
        for version in [1,2,4,0x03000000]:
            self.bad(make(version=version),'VERSION_UNSUPPORTED')
        self.bad(make()[:-1])

    def test_duplicate_metadata_and_tensors(self):
        self.bad(make(kv=[('x',4,1),('x',4,2)]),'DUPLICATE_METADATA')
        self.bad(make(tensors=[('x',[8],0,0),('x',[8],0,32)]),'DUPLICATE_TENSOR')

    def test_alignment_wrong_type_nonpower_huge(self):
        self.bad(make(kv=[('general.alignment',5,32)]),'ALIGNMENT_TYPE_INVALID')
        for val in [0,3,8192]:
            self.bad(make(kv=[('general.alignment',4,val)]),'ALIGNMENT_INVALID')
        self.bad(make(tensors=[('x',[8],0,1)]),'OFFSET_ALIGNMENT_INVALID')

    def test_shape_rank_and_quant_block(self):
        self.bad(make(tensors=[('x',[],0,0)]),'DIMENSIONS_INVALID')
        self.bad(make(tensors=[('x',[1]*5,0,0)]),'DIMENSIONS_INVALID')
        self.bad(make(tensors=[('x',[0],0,0)]),'SHAPE_INVALID')
        self.bad(make(tensors=[('x',[2**63],0,0)]),'SHAPE_INVALID')
        self.bad(make(tensors=[('x',[31],2,0)]),'QUANT_ROW_INVALID')

    def test_unknown_type_empty_name_and_nul(self):
        self.bad(make(tensors=[('x',[4],99,0)]),'TENSOR_TYPE_UNSUPPORTED')
        self.bad(make(tensors=[('',[4],0,0)]),'TENSOR_NAME_INVALID')
        self.bad(make(tensors=[('x\0y',[4],0,0)]),'TENSOR_NAME_INVALID')

    def test_gap_overlap_and_trailing_data(self):
        self.bad(make(tensors=[('x',[8],0,32)]),'TENSOR_GAP_OR_OVERLAP')
        self.bad(make(tensors=[('x',[8],0,0),('y',[8],0,0)]),'TENSOR_GAP_OR_OVERLAP')
        self.bad(make(tail=b'junk'),'FILE_COVERAGE_MISMATCH')

    def test_padding_nonzero(self):
        self.bad(make(padding_byte=1),'NONZERO_HEADER_PADDING')
        data=bytearray(make());data[-1]=1
        self.bad(bytes(data),'NONZERO_TENSOR_PADDING')

    def test_huge_counts_and_strings_without_allocation(self):
        self.bad(b'GGUF'+struct.pack('<IQQ',3,2**63,1),'COUNT_INVALID')
        self.bad(b'GGUF'+struct.pack('<IQQ',3,1,1)+struct.pack('<Q',2**63),'STRING_TOO_LARGE')
        prefix=b'GGUF'+struct.pack('<IQQ',3,1,1)+string('x')+struct.pack('<IIQ',9,8,2**63)
        self.bad(prefix,'ARRAY_TOO_LARGE')

    def test_metadata_invalid_types_bool_nan_utf8(self):
        prefix=b'GGUF'+struct.pack('<IQQ',3,1,1)+string('x')
        self.bad(prefix+struct.pack('<I',99),'UNKNOWN_METADATA_TYPE')
        self.bad(prefix+struct.pack('<IIQ',9,9,1),'UNKNOWN_ARRAY_TYPE')
        self.bad(make(kv=[('x',7,2)]),'INVALID_BOOL')
        self.bad(make(kv=[('x',6,float('nan'))]),'NONFINITE_METADATA')
        self.bad(prefix+struct.pack('<I',8)+string(b'\xff'),'INVALID_UTF8')

    def test_bounds_reader(self):
        r=m.Reader(io.BytesIO(b'1234'),4)
        with self.assertRaises(m.AuditError):r.read(5)
        r=m.Reader(io.BytesIO(b'1234'),m.HEADER_CAP+1);r.offset=m.HEADER_CAP
        with self.assertRaisesRegex(m.AuditError,'HEADER_TOO_LARGE'):r.read(1)

    def test_path_scope_symlink_and_no_clobber(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'safe').mkdir();(root/'safe/file').write_bytes(b'ok')
            (root/'link').symlink_to(root/'safe',target_is_directory=True)
            (root/'leaf').symlink_to(root/'safe/file')
            for p in [Path('../outside'),Path('/absolute')]:
                with self.assertRaises(m.AuditError):
                    with m.safe_open(root,p):pass
            for p in [Path('link/file'),Path('leaf')]:
                with self.assertRaises(OSError):
                    with m.safe_open(root,p):pass
            with self.assertRaises(FileExistsError):
                with m.safe_open(root,Path('safe/file'),write=True):pass
            self.assertEqual((root/'safe/file').read_bytes(),b'ok')

    def test_path_ownership_and_hardlink(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'file').write_bytes(b'ok')
            owner=m.os.getuid()
            with patch.object(m.os,'getuid',return_value=owner+1):
                with self.assertRaisesRegex(m.AuditError,'PATH_NOT_OWNED'):
                    with m.safe_open(root,Path('file')):pass
            m.os.link(root/'file',root/'alias')
            with self.assertRaisesRegex(m.AuditError,'FILE_MULTIPLE_LINKS'):
                with m.safe_open(root,Path('file')):pass
            m.os.mkfifo(root/'fifo')
            with self.assertRaisesRegex(m.AuditError,'NOT_REGULAR'):
                with m.safe_open(root,Path('fifo')):pass

    def test_generic_parser_unchanged_from_pinned_source(self):
        import ast
        old=Path(__file__).with_name('inspect_qwen38_gguf.py').read_bytes()
        self.assertEqual(hashlib.sha256(old).hexdigest(),m.BASE_HELPER_SHA)
        a=ast.parse(old);b=ast.parse(Path(m.__file__).read_bytes())
        for name in ['AuditError','require','safe_open','read_bound','stat_key','Reader','parse_header','finish_hash']:
            left=next(x for x in a.body if getattr(x,'name',None)==name)
            right=next(x for x in b.body if getattr(x,'name',None)==name)
            self.assertEqual(ast.dump(left),ast.dump(right),name)


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Pinned public JSON/config only. Never open any model/weight file.
        cls.config=json.loads(m.read_bound(m.META/'config.json',m.CONFIG_SHA,65536))
        cls.index=json.loads(m.read_bound(m.META/'model.safetensors.index.json',m.INDEX_SHA,1048576))
        tokenizer=json.loads(m.read_bound(m.META/'tokenizer.json',m.TOKENIZER_SHA,40*1024**2))
        tokconf=json.loads(m.read_bound(m.META/'tokenizer_config.json',m.TOKENIZER_CONFIG_SHA,1048576))
        cls.binding=m.tokenizer_bindings(tokenizer,tokconf)

    def fixture(self):
        # Candidate-sized header summaries; no allocation or reads of tensor bytes.
        values={
          'general.architecture':'gemma4','general.type':'model','general.file_type':2,
          'general.quantization_version':2,'gemma4.block_count':60,
          'gemma4.context_length':262144,'gemma4.embedding_length':5376,
          'gemma4.feed_forward_length':21504,'gemma4.attention.head_count':32,
          'gemma4.attention.head_count_kv':[16,16,16,16,16,4]*10,
          'gemma4.attention.key_length':512,'gemma4.attention.value_length':512,
          'gemma4.attention.key_length_swa':256,'gemma4.attention.value_length_swa':256,
          'gemma4.attention.sliding_window':1024,
          'gemma4.attention.sliding_window_pattern':[True,True,True,True,True,False]*10,
          'gemma4.attention.shared_kv_layers':0,'gemma4.embedding_length_per_layer_input':0,
          'gemma4.attention.layer_norm_rms_epsilon':1e-6,
          'gemma4.final_logit_softcapping':30.0,
          'gemma4.rope.freq_base':1000000.0,'gemma4.rope.freq_base_swa':10000.0,
          'gemma4.rope.dimension_count':512,'gemma4.rope.dimension_count_swa':256,
          'tokenizer.ggml.model':'gemma4','tokenizer.ggml.bos_token_id':2,
          'tokenizer.ggml.eos_token_id':1,'tokenizer.ggml.padding_token_id':0,
          'tokenizer.ggml.unknown_token_id':3,'tokenizer.ggml.add_bos_token':True,
          'tokenizer.ggml.add_space_prefix':False,
        }
        meta={}
        for k,v in values.items():
            if type(v) is list:
                meta[k]={'type':9,'element_type':7 if type(v[0]) is bool else 4,'count':len(v)}
            else:
                meta[k]={'type':{str:8,int:4,float:6,bool:7}[type(v)]}
        for key,typ,count in [('tokens',8,262144),('scores',6,262144),
                              ('token_type',5,262144),('merges',8,514906)]:
            meta['tokenizer.ggml.'+key]={'type':9,'element_type':typ,'count':count,
                 'elements_wire_sha256':self.binding.get(key,'0'*64)}
        meta['tokenizer.chat_template']={'type':8,'bytes':18683,'sha256':m.TEMPLATE_SHA}
        rows=[]
        for name,(dims,types) in m.tensor_spec(self.config,self.index).items():
            typ=2 if len(dims)==2 else 0
            rows.append({'name':name,'shape':dims.copy(),'type_id':typ,'dtype':m.TYPES[typ][0]})
        return {'tensor_count':833,'metadata':meta,'tensors':rows,
                'dtype_counts':dict(m.Counter(t['dtype'] for t in rows))},values

    def validate(self,h,v,config=None,index=None):
        return m.validate_candidate(h,v,config or self.config,index or self.index,self.binding)

    def test_candidate_geometry_and_public_token_binding(self):
        h,v=self.fixture();out=self.validate(h,v)
        self.assertEqual(out['expected_tensor_names_shapes_matched'],833)
        self.assertEqual(out['qat_text_index_names_matched'],832)
        self.assertEqual(out['largest_dense_matrix_f32_bytes'],5376*1024**2)
        self.assertEqual(out['kv_f16_context4096_seq1_ubatch64_swa_full_false_mib'],1320)
        self.assertIsNone(out['conversion_log_tensors_matched'])
        self.assertEqual(self.binding['tokens'],'a5a6b2886a2d1ccb33ba3c5ba62b32066be33c29c1d67fea478891721883e808')
        self.assertEqual(self.binding['merges'],'1fc76734735fa624f5091b768899592b570356e2737a717d4ca32aeda12f8ace')
        spec=m.tensor_spec(self.config,self.index)
        self.assertNotIn('output.weight',spec)
        self.assertEqual(sum('.attn_v.' in k for k in spec),50)
        self.assertNotIn('blk.5.attn_v.weight',spec)
        self.assertEqual(spec['blk.5.attn_q.weight'][0],[5376,16384])
        self.assertEqual(spec['blk.0.attn_q.weight'][0],[5376,8192])

    def test_metadata_strict_types_values_and_swa(self):
        for key,bad in [('gemma4.block_count',59),('general.file_type',15),
                        ('gemma4.embedding_length_per_layer_input',256),
                        ('gemma4.attention.shared_kv_layers',1),
                        ('tokenizer.ggml.bos_token_id',True),
                        ('gemma4.attention.head_count_kv',[16]*60),
                        ('gemma4.attention.sliding_window_pattern',[1]*60)]:
            with self.subTest(key=key):
                h,v=self.fixture();v[key]=bad
                with self.assertRaises(m.AuditError):self.validate(h,v)
        h,v=self.fixture();del h['metadata']['gemma4.rope.dimension_count_swa']
        with self.assertRaisesRegex(m.AuditError,'CONFIG_METADATA_MISSING'):self.validate(h,v)
        h,v=self.fixture();h['metadata']['gemma4.attention.head_count_kv']['element_type']=5
        with self.assertRaisesRegex(m.AuditError,'CONFIG_ARRAY_MISMATCH'):self.validate(h,v)

    def test_token_and_template_mismatch_rejected(self):
        for key,field,bad in [('tokens','count',262143),('tokens','elements_wire_sha256','0'*64),
                              ('merges','elements_wire_sha256','0'*64),('scores','element_type',12)]:
            h,v=self.fixture();h['metadata']['tokenizer.ggml.'+key][field]=bad
            with self.subTest(key=key,field=field):
                with self.assertRaises(m.AuditError):self.validate(h,v)
        for field,bad in [('bytes',18682),('sha256','0'*64)]:
            h,v=self.fixture();h['metadata']['tokenizer.chat_template'][field]=bad
            with self.assertRaisesRegex(m.AuditError,'EMBEDDED_TEMPLATE_MISMATCH'):self.validate(h,v)

    def test_tensor_coverage_shape_type_and_source_namespace(self):
        for field,bad in [('name','output.weight'),('shape',[5376,262143]),('type_id',12)]:
            h,v=self.fixture();h['tensors'][0][field]=bad
            with self.subTest(field=field):
                with self.assertRaises(m.AuditError):self.validate(h,v)
        h,v=self.fixture();h['tensors'].pop()
        with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SET_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['tensors'].append({'name':'blk.5.attn_v.weight','shape':[5376,2048],'type_id':2})
        with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SET_MISMATCH'):self.validate(h,v)
        idx=copy.deepcopy(self.index);idx['weight_map']['unexpected.weight']='x'
        with self.assertRaisesRegex(m.AuditError,'QAT_INDEX_NAMESPACE_UNEXPECTED'):m.tensor_spec(self.config,idx)
        idx=copy.deepcopy(self.index);del idx['weight_map']['model.language_model.norm.weight']
        with self.assertRaisesRegex(m.AuditError,'QAT_TEXT_INDEX_COVERAGE_MISMATCH'):m.tensor_spec(self.config,idx)

    def test_config_features_invalidate_prediction(self):
        for key,bad in [('hidden_size_per_layer_input',256),('num_kv_shared_layers',10),
                        ('attention_k_eq_v',False),('enable_moe_block',True),
                        ('num_hidden_layers',True)]:
            cfg=copy.deepcopy(self.config);cfg['text_config'][key]=bad
            with self.subTest(key=key):
                with self.assertRaisesRegex(m.AuditError,'QAT_CONFIG_UNEXPECTED'):m.tensor_spec(cfg,self.index)


if __name__=='__main__':
    unittest.main()
