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

spec = importlib.util.spec_from_file_location('qwen38_header_audit', Path(__file__).with_name('inspect_qwen38_gguf.py'))
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
        tensors=[('f32',[8],0,0),('q4',[256],12,32),('q6',[256],14,192),('q8',[32],8,416)]
        h,_,_=parse(make(tensors=tensors))
        self.assertEqual(h['dtype_counts'],{'f32':1,'q4_K':1,'q6_K':1,'q8_0':1})

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
        self.bad(make(tensors=[('x',[255],12,0)]),'QUANT_ROW_INVALID')

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

    def test_candidate_log_config_template_binding(self):
        # Only pinned small public metadata is read. No GGUF/payload is opened.
        config=json.loads(m.read_bound(m.META/'upstream/config.json',m.CONFIG_SHA,65536))
        prov=json.loads(m.read_bound(m.META/'template_and_conversion_provenance.json',m.PROVENANCE_SHA,1048576))
        log=m.read_bound(m.META/'gguf/convert.log',m.LOG_SHA,1048576).decode()
        segment=log.split("as Q4_K_M\n",1)[1].split('llama_tensor_get_type:',1)[0]
        values={}; metadata={}
        for line in segment.splitlines():
            match=__import__('re').search(r'- kv\s+\d+:\s+(\S+)\s+(u32|i32|f32|bool|str)\s+= (.*)$',line)
            if not match:continue
            key,kind,raw=match.groups()
            if kind in ('u32','i32'):v=int(raw);typ=4 if kind=='u32' else 5
            elif kind=='f32':v=float(raw);typ=6
            elif kind=='bool':v=raw=='true';typ=7
            else:v=raw;typ=8
            values[key]=v;metadata[key]={'type':typ}
        values['general.file_type']=15  # Log displays BF16 INPUT; Q4 output is type 15.
        values['qwen35.attention.recurrent_layers']=[i%4!=3 for i in range(64)]
        values['qwen35.rope.dimension_sections']=[11,11,10,0]
        for key,subtype,count in [('qwen35.attention.recurrent_layers',7,64),('qwen35.rope.dimension_sections',5,4),
                                  ('tokenizer.ggml.tokens',8,248320),('tokenizer.ggml.token_type',5,248320),
                                  ('tokenizer.ggml.merges',8,247587)]:
            metadata[key]={'type':9,'element_type':subtype,'count':count}
        metadata['tokenizer.chat_template']={'type':8,'bytes':8952,'sha256':m.TEMPLATE_SHA}
        rows=[{'name':r['name'],'shape_padded':list(map(int,r['shape_text'].split(','))),
               'dtype':r['destination_dtype']} for r in prov['logged_output_tensor_rows']]
        header={'metadata':metadata,'tensors':rows,'tensor_count':851,
                'dtype_counts':{'q6_K':17,'f32':353,'q4_K':193,'q8_0':288},
                'tensor_payload_bytes':18_962_876_416}
        self.assertEqual(m.validate_candidate(header,values,config,prov)['conversion_log_tensors_matched'],851)
        cases=[]
        h=copy.deepcopy(header);v=copy.deepcopy(values);v['qwen35.block_count']=65;cases.append((h,v))
        h=copy.deepcopy(header);h['metadata']['tokenizer.chat_template']['sha256']='0'*64;cases.append((h,values))
        h=copy.deepcopy(header);h['tensors'][0]['shape_padded'][0]+=1;cases.append((h,values))
        h=copy.deepcopy(header);h['tensors'][0]['dtype']='q4_K';cases.append((h,values))
        h=copy.deepcopy(header);h['metadata']['tokenizer.ggml.tokens']['count']-=1;cases.append((h,values))
        h=copy.deepcopy(header);h['metadata']['qwen35.attention.recurrent_layers']['element_type']=5;cases.append((h,values))
        h=copy.deepcopy(header);h['metadata']['qwen35.rope.freq_base']['type']=4;cases.append((h,values))
        h=copy.deepcopy(header);h['tensors'][0]['name']='undeclared.weight';cases.append((h,values))
        for h,v in cases:
            with self.subTest():
                with self.assertRaises(m.AuditError):m.validate_candidate(h,v,config,prov)


if __name__=='__main__':
    unittest.main()
