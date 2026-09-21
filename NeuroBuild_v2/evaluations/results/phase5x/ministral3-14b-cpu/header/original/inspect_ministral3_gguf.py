#!/usr/bin/env python3
"""Pinned Ministral3 text GGUF structural audit. Stdlib only.

Definitions only until root authorizes the exact file. One owned, nofollow fd
parses the bounded header and hashes the entire payload. Numeric weights are
never decoded. Structural PASS is NOT tokenizer/template/native/runtime/quality
PASS. The publisher did not publish a conversion revision or per-tensor recipe.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import sys

ROOT=Path('/home/a202192020/NeuroBuild_v2')
META=Path('var/research/ministral3-14b-candidate-metadata')
MODEL_ID='mistralai/Ministral-3-14B-Instruct-2512-GGUF'
REVISION='74fac473c43357d7fb2671713608183cc72496d0'
UPSTREAM_REFERENCE='3cea74c1ebaf5ce5f5a2553de470e2ceab825142'
RUNTIME='f072b103714dfa1eee531f80b24512faf38e3dd2'
FILE_NAME='Ministral-3-14B-Instruct-2512-Q4_K_M.gguf'
FILE_BYTES=8_239_593_024
FILE_SHA='824e0f3373e69b84f2cae46fdcb9bd1ebc6ab3bfc7acc125d818b7b8178cc613'
MODEL_PATH=Path('var/models')/'mistralai--Ministral-3-14B-Instruct-2512-GGUF'/REVISION/FILE_NAME
CONFIG_SHA='b1897778395bb1795489a048ebde2e6d216eee21014ce9c18193d15f097454a6'
INDEX_SHA='50d07948f11d89b5eddc5fb21485484555376c0627a9537b37f3f17cc9f5a103'
PARAMS_SHA='b2fc120fee26653d0aa07052122793f86750db9c12b6e11bcf7dfb36440da077'
TEKKEN_SHA='600bb27946565481ecf51ba8aee252e49b9a68507866080ac9c30185bb312843'
TEMPLATE_REFERENCE_SHA='2f545122222db8bb43ca0ea0c49e9185320a8670f7d35575b0da0eb48b1e8970'
INVENTORY_SHA='b6c279498d99d9fa2c65f87faf5bb4c629326b8b2fd397d198dbe1d32f152249'
MANIFEST=Path('runtime/models/ministral3-14b-instruct-q4-k-m.json')
MANIFEST_SHA='ebc2763eed81cbc64fc07713dc784022244a0b45df51659a562a128ae2c7962c'
DOWNLOAD=Path('var/reports/ministral3-14b-guarded-download.json')
DOWNLOAD_SHA='34beef404d2aa470bfaf3aac1b39f174b318623128c811220fbd51d8b2c30fca'
# Pinned ggml.h enum and ggml-common.h block sizes; not a quant-recipe claim.
TYPES={0:('f32',1,4),1:('f16',1,2),8:('q8_0',32,34),
       12:('q4_K',256,144),13:('q5_K',256,176),14:('q6_K',256,210),30:('bf16',1,2)}
MATRIX_TYPES=frozenset(TYPES)
SCALARS={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'B',10:'Q',11:'q',12:'d'}
HEADER_CAP=32*1024**2
STRING_CAP=1024**2
ARRAY_CAP=1_000_000
NAME=re.compile(r'[A-Za-z0-9_.-]{1,127}\Z')


class AuditError(Exception):
    """Only fixed error codes are surfaced, never metadata text/token strings."""


def require(condition, code):
    if not condition:
        raise AuditError(code)


@contextmanager
def safe_open(root: Path, relative: Path, *, write=False):
    require(not relative.is_absolute() and relative.parts and
            all(x not in ('', '.', '..') for x in relative.parts), 'PATH_INVALID')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        require(os.fstat(fd).st_uid == os.getuid(), 'PATH_NOT_OWNED')
        for part in relative.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            require(os.fstat(fd).st_uid == os.getuid(), 'PATH_NOT_OWNED')
        flags = os.O_NOFOLLOW | (os.O_WRONLY | os.O_CREAT | os.O_EXCL if write else os.O_RDONLY | os.O_NONBLOCK)
        leaf = os.open(relative.name, flags, 0o600, dir_fd=fd)
        with os.fdopen(leaf, 'wb' if write else 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode), 'NOT_REGULAR')
            require(info.st_uid == os.getuid(), 'PATH_NOT_OWNED')
            require(info.st_nlink == 1, 'FILE_MULTIPLE_LINKS')
            yield stream
            if write:
                stream.flush()
                os.fsync(stream.fileno())
        if write:
            os.fsync(fd)
    finally:
        os.close(fd)


def read_bound(relative, digest, cap):
    with safe_open(ROOT, relative) as f:
        before = os.fstat(f.fileno())
        require(before.st_size <= cap, 'METADATA_TOO_LARGE')
        data = f.read(cap + 1)
        require(len(data) == before.st_size, 'METADATA_CHANGED')
        require(stat_key(before) == stat_key(os.fstat(f.fileno())), 'METADATA_CHANGED')
    require(hashlib.sha256(data).hexdigest() == digest, 'METADATA_HASH_MISMATCH')
    return data


def stat_key(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


class Reader:
    def __init__(self, stream, size):
        self.stream, self.size, self.offset = stream, size, 0
        self.sha = hashlib.sha256()

    def read(self, n, *, header=True):
        require(type(n) is int and n >= 0 and n <= self.size-self.offset, 'TRUNCATED')
        require(not header or self.offset+n <= HEADER_CAP, 'HEADER_TOO_LARGE')
        result = self.stream.read(n)
        require(len(result) == n, 'TRUNCATED')
        self.offset += n
        self.sha.update(result)
        return result

    def num(self, fmt):
        return struct.unpack('<'+fmt, self.read(struct.calcsize('<'+fmt)))[0]

    def string(self, cap=STRING_CAP):
        n = self.num('Q')
        require(n <= cap, 'STRING_TOO_LARGE')
        raw = self.read(n)
        try:
            text = raw.decode('utf-8', 'strict')
        except UnicodeDecodeError:
            raise AuditError('INVALID_UTF8') from None
        return text, raw

    def value(self, typ):
        if typ == 8:
            return self.string()[0]
        require(typ in SCALARS, 'UNKNOWN_METADATA_TYPE')
        value = self.num(SCALARS[typ])
        if typ == 7:
            require(value in (0, 1), 'INVALID_BOOL')
            return bool(value)
        if typ in (6, 12):
            require(math.isfinite(value), 'NONFINITE_METADATA')
        return value


def parse_header(r: Reader):
    require(r.read(4) == b'GGUF', 'MAGIC_INVALID')
    require(r.num('I') == 3, 'VERSION_UNSUPPORTED')
    count, kvcount = r.num('Q'), r.num('Q')
    require(0 < count <= 2048 and 0 < kvcount <= 1024, 'COUNT_INVALID')
    metadata, values = {}, {}
    for _ in range(kvcount):
        key, _raw = r.string(256)
        require(NAME.fullmatch(key) is not None, 'METADATA_KEY_INVALID')
        require(key not in metadata, 'DUPLICATE_METADATA')
        typ = r.num('I')
        start = r.offset
        # Keep only small scalar values/numeric arrays. Never retain token/merge strings.
        if typ == 9:
            subtype, n = r.num('I'), r.num('Q')
            require(subtype in SCALARS or subtype == 8, 'UNKNOWN_ARRAY_TYPE')
            require(n <= ARRAY_CAP, 'ARRAY_TOO_LARGE')
            arr = [] if subtype != 8 and n <= 128 else None
            digest = hashlib.sha256()
            for _ in range(n):
                if subtype == 8:
                    _s, raw = r.string()
                    digest.update(struct.pack('<Q', len(raw)))
                    digest.update(raw)
                else:
                    v = r.value(subtype)
                    digest.update(struct.pack('<'+SCALARS[subtype], v))
                    if arr is not None:
                        arr.append(v)
            summary = {'type': typ, 'element_type': subtype, 'count': n,
                       'elements_wire_sha256': digest.hexdigest()}
            if arr is not None:
                values[key] = arr
        elif typ == 8:
            v, raw = r.string()
            summary = {'type': typ, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            if not key.startswith('tokenizer.chat_template') and len(raw) <= 128:
                values[key] = v
        else:
            v = r.value(typ)
            summary = {'type': typ, 'value': v}
            values[key] = v
        summary['wire_bytes'] = r.offset-start
        metadata[key] = summary
    alignment = values.get('general.alignment', 32)
    require('general.alignment' not in metadata or metadata['general.alignment']['type'] == 4,
            'ALIGNMENT_TYPE_INVALID')
    require(type(alignment) is int and 0 < alignment <= 4096 and alignment & (alignment-1) == 0,
            'ALIGNMENT_INVALID')
    tensors, names = [], set()
    for _ in range(count):
        name, raw = r.string(127)
        require(NAME.fullmatch(name) is not None, 'TENSOR_NAME_INVALID')
        require(name not in names, 'DUPLICATE_TENSOR')
        names.add(name)
        nd = r.num('I')
        require(1 <= nd <= 4, 'DIMENSIONS_INVALID')
        dims = [r.num('Q') for _ in range(nd)]
        require(all(0 < n <= 2**31-1 for n in dims), 'SHAPE_INVALID')
        typ, offset = r.num('I'), r.num('Q')
        require(typ in TYPES, 'TENSOR_TYPE_UNSUPPORTED')
        dtype, block, blockbytes = TYPES[typ]
        require(dims[0] % block == 0, 'QUANT_ROW_INVALID')
        elems = math.prod(dims)
        nbytes = (elems//block)*blockbytes
        require(0 < elems < 2**63 and 0 < nbytes <= r.size, 'TENSOR_SIZE_INVALID')
        require(offset % alignment == 0, 'OFFSET_ALIGNMENT_INVALID')
        tensors.append({'name':name, 'shape':dims, 'shape_padded':dims+[1]*(4-nd),
                        'type_id':typ, 'dtype':dtype, 'offset':offset, 'bytes':nbytes})
    header_bytes = r.offset
    data_offset = (header_bytes+alignment-1)//alignment*alignment
    require(not any(r.read(data_offset-header_bytes)), 'NONZERO_HEADER_PADDING')
    # Candidate is a single packed GGUF. Arbitrary gaps/overlap/trailing data are rejected.
    end = 0
    for row in sorted(tensors, key=lambda t:t['offset']):
        require(row['offset'] == end, 'TENSOR_GAP_OR_OVERLAP')
        end += (row['bytes']+alignment-1)//alignment*alignment
        require(data_offset+end <= r.size, 'TENSOR_OUT_OF_BOUNDS')
    require(data_offset+end == r.size, 'FILE_COVERAGE_MISMATCH')
    return {'version':3, 'tensor_count':count, 'metadata_count':kvcount,
            'header_bytes':header_bytes, 'data_offset':data_offset, 'alignment':alignment,
            'tensor_payload_bytes':sum(t['bytes'] for t in tensors),
            'tensor_padding_bytes':end-sum(t['bytes'] for t in tensors),
            'dtype_counts':dict(Counter(t['dtype'] for t in tensors)),
            'metadata':metadata, 'tensors':tensors}, values


def finish_hash(r: Reader, header):
    for row in sorted(header['tensors'], key=lambda t:t['offset']):
        remaining = row['bytes']
        while remaining:
            n = min(4*1024**2, remaining)
            r.read(n, header=False)
            remaining -= n
        padding = (-row['bytes']) % header['alignment']
        require(not any(r.read(padding, header=False)), 'NONZERO_TENSOR_PADDING')
    require(r.offset == r.size and not r.stream.read(1), 'FILE_COVERAGE_MISMATCH')
    return r.sha.hexdigest()


class HeaderCaptureReader(Reader):
    """Keep only the bounded header for a second metadata-only template extraction."""
    def __init__(self, stream, size):
        super().__init__(stream,size)
        self.header_copy=bytearray()

    def read(self, n, *, header=True):
        value=super().read(n,header=header)
        if header:
            self.header_copy.extend(value)
        return value


def extract_text_metadata(raw_header):
    """Read no tensor data; retain actual template and first1000 special entries only."""
    require(len(raw_header)<=HEADER_CAP,'HEADER_TOO_LARGE')
    r=Reader(io.BytesIO(raw_header),len(raw_header))
    require(r.read(4)==b'GGUF' and r.num('I')==3,'VERSION_UNSUPPORTED')
    r.num('Q')
    count=r.num('Q')
    require(0<count<=1024,'COUNT_INVALID')
    template=None
    specials={}
    special_types={}
    for _ in range(count):
        key,_=r.string(256)
        typ=r.num('I')
        if typ==9:
            subtype,n=r.num('I'),r.num('Q')
            require((subtype in SCALARS or subtype==8) and n<=ARRAY_CAP,'ARRAY_METADATA_MISMATCH')
            for i in range(n):
                if subtype==8:
                    value,_raw=r.string()
                else:
                    value=r.value(subtype)
                if i<1000 and key=='tokenizer.ggml.tokens':
                    specials[i]=value
                if i<1000 and key=='tokenizer.ggml.token_type':
                    special_types[i]=value
        elif typ==8:
            _value,raw=r.string()
            if key=='tokenizer.chat_template':
                require(template is None,'DUPLICATE_METADATA')
                template=raw
        else:
            r.value(typ)
    require(template is not None and 0<len(template)<=64*1024 and b'\0' not in template,
            'EMBEDDED_TEMPLATE_MISSING_OR_INVALID')
    return template,specials,special_types


def expected_metadata(config):
    tc=config['text_config'];rp=tc['rope_parameters'];a='mistral3'
    require(config['architectures']==['Mistral3ForConditionalGeneration']
            and config['model_type']=='mistral3' and tc['model_type']=='ministral3'
            and tc['num_hidden_layers']==40 and tc['hidden_size']==5120
            and tc['intermediate_size']==16384 and tc['vocab_size']==131072
            and tc['num_attention_heads']==32 and tc['num_key_value_heads']==8
            and tc['head_dim']==128 and tc['sliding_window'] is None,
            'OFFICIAL_CONFIG_IDENTITY_MISMATCH')
    return {
        'general.architecture':a,'general.type':'model','general.file_type':15,
        'general.quantization_version':2,
        f'{a}.block_count':40,f'{a}.context_length':tc['max_position_embeddings'],
        f'{a}.embedding_length':5120,f'{a}.feed_forward_length':16384,
        f'{a}.attention.head_count':32,f'{a}.attention.head_count_kv':8,
        f'{a}.attention.key_length':128,f'{a}.attention.value_length':128,
        f'{a}.rope.dimension_count':128,
        f'{a}.attention.layer_norm_rms_epsilon':float(tc['rms_norm_eps']),
        f'{a}.rope.freq_base':float(rp['rope_theta']),
        f'{a}.rope.scaling.type':'yarn',f'{a}.rope.scaling.factor':float(rp['factor']),
        f'{a}.rope.scaling.original_context_length':rp['original_max_position_embeddings'],
        f'{a}.rope.scaling.yarn_beta_fast':float(rp['beta_fast']),
        f'{a}.rope.scaling.yarn_beta_slow':float(rp['beta_slow']),
        f'{a}.rope.scaling.yarn_log_multiplier':float(rp['mscale_all_dim']),
        f'{a}.attention.temperature_scale':float(rp['llama_4_scaling_beta']),
        'tokenizer.ggml.model':'gpt2','tokenizer.ggml.pre':'tekken',
        'tokenizer.ggml.bos_token_id':1,'tokenizer.ggml.eos_token_id':2,
        'tokenizer.ggml.unknown_token_id':0,'tokenizer.ggml.padding_token_id':11,
        'tokenizer.ggml.add_bos_token':True,'tokenizer.ggml.add_eos_token':False,
    }


def validate_candidate(header,values,config,index,params,inventory,tekken,template,specials,special_types):
    expected=expected_metadata(config)
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
            require(row['type_id'] in MATRIX_TYPES,'MATRIX_TYPE_UNSUPPORTED')
        role=re.sub(r'^blk\.\d+\.','blk.*.',row['name'])
        role_types.setdefault(role,Counter())[row['dtype']]+=1
    for key,sub,count in [('tokenizer.ggml.tokens',8,131072),('tokenizer.ggml.token_type',5,131072)]:
        m=header['metadata'].get(key,{})
        require(m.get('type')==9 and m.get('element_type')==sub and m.get('count')==count,
                'TOKENIZER_ARRAY_METADATA_MISMATCH')
    merges=header['metadata'].get('tokenizer.ggml.merges',{})
    require(merges.get('type')==9 and merges.get('element_type')==8
            and type(merges.get('count')) is int and 0<merges['count']<=ARRAY_CAP,
            'TOKENIZER_MERGES_METADATA_MISMATCH')
    if 'tokenizer.ggml.scores' in header['metadata']:
        scores=header['metadata']['tokenizer.ggml.scores']
        require(scores.get('type')==9 and scores.get('element_type')==6
                and scores.get('count')==131072,'TOKENIZER_SCORES_METADATA_MISMATCH')
    require(tekken['config']['version']=='v13'
            and tekken['config']['default_vocab_size']==131072
            and tekken['config']['default_num_special_tokens']==1000
            and len(tekken['special_tokens'])==1000 and len(tekken['vocab'])==130072,
            'TEKKEN_REFERENCE_IDENTITY_MISMATCH')
    canonical={r['rank']:r['token_str'] for r in tekken['special_tokens']}
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
        'tokenizer_special_entries_matched':1000,'tokenizer_arrays_typed_and_hashed':True,
        'tokenizer_full_vocab_or_merges_equivalence':'PENDING',
        'embedded_template_sha256':actual_template_sha,'embedded_template_bytes':len(template),
        'reference_template_sha256':TEMPLATE_REFERENCE_SHA,
        'reference_template_byte_equal':actual_template_sha==TEMPLATE_REFERENCE_SHA,
        'template_compatibility':'PENDING_NEW_CPU_CONTRACT',
        'tokenizer_compatibility':'PENDING_NEW_REFERENCE_AND_NATIVE_PARITY',
        'runtime_compatibility':'PENDING','quality':'PENDING',
        'tensor_payload_numeric_validity':'NOT_DECODED_OR_TESTED',
    }


def audit(relative):
    require(relative==MODEL_PATH,'PINNED_MODEL_PATH_MISMATCH')
    manifest=json.loads(read_bound(MANIFEST,MANIFEST_SHA,64*1024))
    download=json.loads(read_bound(DOWNLOAD,DOWNLOAD_SHA,64*1024))
    require(manifest['model_id']==MODEL_ID and manifest['revision']==REVISION
            and len(manifest['files'])==2
            and next((x for x in manifest['files'] if x['name']==FILE_NAME),None)
                =={'name':FILE_NAME,'bytes':FILE_BYTES,'sha256':FILE_SHA},
            'DOWNLOAD_MANIFEST_MISMATCH')
    require(download['kind']=='GUARDED_PINNED_PUBLIC_MODEL_DOWNLOAD'
            and download['status']=='PASS_DOWNLOAD_ONLY_NOT_RUNTIME_VALIDATED'
            and download['model_id']==MODEL_ID and download['revision']==REVISION
            and download['source_pin']==RUNTIME and download['verified_files']==2
            and download['downloaded_manifest_sha256']==MANIFEST_SHA
            and download['input_sha256'][MANIFEST.as_posix()]==MANIFEST_SHA
            and download['gpu_or_native_execution'] is False,
            'DOWNLOAD_RECEIPT_MISMATCH')
    config=json.loads(read_bound(META/'bf16/config.json',CONFIG_SHA,64*1024))
    index=json.loads(read_bound(META/'bf16/model.safetensors.index.json',INDEX_SHA,256*1024))
    params=json.loads(read_bound(META/'bf16/params.json',PARAMS_SHA,64*1024))
    inventory=json.loads(read_bound(META/'expected_text_inventory.json',INVENTORY_SHA,256*1024))
    tekken=json.loads(read_bound(META/'bf16/tekken.json',TEKKEN_SHA,20*1024**2))
    read_bound(META/'bf16/chat_template.jinja',TEMPLATE_REFERENCE_SHA,64*1024)
    with safe_open(ROOT,relative) as f:
        before=os.fstat(f.fileno())
        require(before.st_size==FILE_BYTES,'PINNED_FILE_SIZE_MISMATCH')
        reader=HeaderCaptureReader(f,before.st_size)
        header,values=parse_header(reader)
        digest=finish_hash(reader,header)
        require(digest==FILE_SHA,'PINNED_FILE_HASH_MISMATCH')
        require(stat_key(before)==stat_key(os.fstat(f.fileno())),'FILE_CHANGED_DURING_AUDIT')
        template,specials,special_types=extract_text_metadata(bytes(reader.header_copy))
    with safe_open(ROOT,relative) as f:
        require(stat_key(before)==stat_key(os.fstat(f.fileno())),'PATH_CHANGED_DURING_AUDIT')
    # Finish full SHA before semantic header validation, retaining a bounded diagnostic
    # on structural mismatch so the same full payload is not needlessly hashed again.
    try:
        bindings=validate_candidate(header,values,config,index,params,inventory,tekken,
                                    template,specials,special_types)
        status='STRUCTURAL_PASS';failure=None
    except AuditError as exc:
        status='STRUCTURAL_FAIL';failure=str(exc)
        bindings={'validation_scope':'FILE_IDENTITY_VERIFIED_STRUCTURAL_CHECK_FAILED',
                  'template_compatibility':'PENDING','tokenizer_compatibility':'PENDING',
                  'runtime_compatibility':'PENDING','quality':'PENDING'}
    result={
        'kind':'GGUF_HEADER_AUDIT','status':status,'failure_code':failure,
        'model_path':relative.as_posix(),'model_id':MODEL_ID,'revision':REVISION,
        'reference_upstream_revision':UPSTREAM_REFERENCE,'conversion_source_revision':None,
        'runtime_source_revision':RUNTIME,'file_sha256':digest,'file_bytes':before.st_size,
        'full_file_sha256_verified':True,'created_utc':datetime.now(timezone.utc).isoformat(),
        'read_mode':'SINGLE_OPEN_FD_HEADER_THEN_PAYLOAD_SHA256_STREAM','stat_unchanged':True,
        'header':header,'metadata_values':values,'bindings':bindings,
        'source_metadata_sha256':{'config':CONFIG_SHA,'bf16_index':INDEX_SHA,'params':PARAMS_SHA,
                                 'tekken':TEKKEN_SHA,'reference_template':TEMPLATE_REFERENCE_SHA,
                                 'expected_inventory':INVENTORY_SHA},
        'download_evidence':{'manifest_path':MANIFEST.as_posix(),'manifest_sha256':MANIFEST_SHA,
                             'report_path':DOWNLOAD.as_posix(),'report_sha256':DOWNLOAD_SHA},
        'gpu_or_native_execution':False,
        'limits':{'header_bytes':HEADER_CAP,'single_string_bytes':STRING_CAP,
                  'array_elements':ARRAY_CAP,'metadata_entries':1024,'tensors':2048},
        'limitations':[
            'STRUCTURAL_PASS does not authorize native/runtime/quality; all remain PENDING.',
            'Full SHA binds payload bytes; numeric tensor values were not decoded.',
            'Current FP8/BF16 references do not establish actual conversion source revision.',
            'Quantization filename/ftype and observed role types do not establish an unpublished recipe.',
            'First1000 canonical specials are checked; normal token/merge content and native Unicode behavior need separate proof.',
            'Actual embedded template is exported unchanged; it is not required to match the current reference.',
            'No corpus, template render, tokenization, native backend, CUDA or model inference was executed.',
        ],
    }
    return result,template


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',required=True,type=Path)
    parser.add_argument('--report',required=True,type=Path)
    parser.add_argument('--template-out',required=True,type=Path)
    args=parser.parse_args()
    try:
        for path,suffix in [(args.report,'.json'),(args.template_out,'.jinja')]:
            require(path.parts[:2]==('var','reports') and path.suffix==suffix,
                    'REPORT_PATH_INVALID')
            require(not (ROOT/path).exists(),'OUTPUT_ALREADY_EXISTS')
        result,template=audit(args.model)
        # Exclusive writes. The template has no effect on runtime until separately reviewed.
        with safe_open(ROOT,args.template_out,write=True) as f:f.write(template)
        result['template_export']={'path':args.template_out.as_posix(),'bytes':len(template),
                                   'sha256':hashlib.sha256(template).hexdigest()}
        result['helper_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        payload=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
        with safe_open(ROOT,args.report,write=True) as f:f.write(payload)
        print(json.dumps({'kind':result['kind'],'status':result['status'],
                          'failure_code':result['failure_code'],'report':args.report.as_posix(),
                          'report_sha256':hashlib.sha256(payload).hexdigest(),
                          'file_sha256':FILE_SHA,'tensor_count':result['header']['tensor_count'],
                          'template_sha256':result['template_export']['sha256'],
                          'tokenizer_runtime_quality':'PENDING'}))
        return 0 if result['status']=='STRUCTURAL_PASS' else 1
    except (AuditError,OSError,ValueError,KeyError,TypeError,struct.error) as exc:
        code=str(exc) if isinstance(exc,AuditError) else 'AUDIT_INPUT_OR_IO_INVALID'
        print(json.dumps({'kind':'GGUF_HEADER_AUDIT','status':'FAIL','code':code}))
        return 1


if __name__=='__main__':
    sys.exit(main())
