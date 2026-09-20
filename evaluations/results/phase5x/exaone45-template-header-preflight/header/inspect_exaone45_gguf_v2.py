#!/usr/bin/env python3
"""EXAONE4.5 pinned text GGUF audit, stdlib CPU only.

Preparation does not read model bytes. Root must authorize each real invocation.
Default: exact header/layout/metadata then one streaming full SHA256; no numeric
weight decoding. --metadata-only: bounded header diagnosis, NEVER a PASS receipt.
Unknown dtypes and unsupported layouts fail closed; no automatic policy widening.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
META = Path('var/research/exaone45-33b-candidate-metadata/upstream')
MODEL_ID = 'LGAI-EXAONE/EXAONE-4.5-33B-GGUF'
REVISION = '0e969634ef24db05151b435970297a6dee634b7e'
UPSTREAM_MODEL_ID = 'LGAI-EXAONE/EXAONE-4.5-33B'
UPSTREAM_REVISION = '570aa4b15a4f45ba1133072b45f50198f6e3b4fd'
RUNTIME = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
FILENAME = 'EXAONE-4.5-33B-Q4_K_M.gguf'
FILE_BYTES = 20_047_839_424
FILE_SHA = '5ba3839b67dcee5618ea7b2206cedc8f9e2ec90fbcec3c95a8cc8b33967f6baf'
MODEL_RELATIVE = Path('var/models/LGAI-EXAONE--EXAONE-4.5-33B-GGUF')/REVISION/FILENAME
CONFIG_SHA = '29e21fcbfe95268e11a151577b6440d77385064b41c960aceff83a2b70eea090'
TOKENIZER_SHA = '0bd798efa30739e209d51f36cfc2f0a636711e37ad9d69b77e4e5c8ca5f09fab'
TOKENIZER_CONFIG_SHA = '41fd7d740786df4f0a2edbe58d74341c4b83556b185b698e5b4d177a56e7b5e9'
TEMPLATE_SHA = 'e4ece7acc79ba82121d4d57791fb7ecb796e39185087197377da5d2286bec0e5'
TEMPLATE_BYTES = 5930
INDEX_SHA = 'fb5d6e4ec8c9c86a2c50c562c29724b911effe90272a6921552f71fe92c9a00c'
PRETYPE_PROOF = Path('var/research/native-exaone45-contract/tokenizer-pretype-fingerprint.json')
PRETYPE_PROOF_SHA = '751bf9715b594401381a6e89b71382de3955bb2532edbd0958268ffc09335931'
BASE_HELPER_SHA = 'cb8ef9e58aea7066c050d3e96da24708b4be4eae0c7c7498f879e2dddc41940c'
SOURCE_PINS = {'conversion/exaone.py': '9f3dd7859cf59bcf6e900560954fb094e931d603cd3d8b1300ec664ad778b356', 'conversion/base.py': 'e0ae8621e67e8b8ea2682177b1f16adbe95b2c154ee8e2de975e942148d66575', 'src/models/exaone4.cpp': '6b71eec534bf3f56c25e67c1046f32c4eb598442fc441ded16e1d13cf38582f3', 'src/llama-quant.cpp': 'a33dea76120a10b2eac8b5d81b9425dcd401e2c8ae4bb04f59b00922f0355fdd', 'src/llama-hparams.cpp': 'ef6fbef7d12a23441b42cfac8e3a3a3045c7d3123402351ba98e69702e193301', 'src/llama-model.cpp': '530dff0cd544382346cc18520cbdb7d7a6f6743c35f7af52aae0bec11d18992a', 'gguf-py/gguf/constants.py': 'df0078c283a48061260ca4b3f35df36611230c3e7c2ac271bb8a11d2632839ba', 'gguf-py/gguf/tensor_mapping.py': 'df97c2291dc1d8e8992ae91b800e0cf139f94d5173b9ed4705f5ef75a371d924', 'gguf-py/gguf/vocab.py': '16cddd93700f86c8b72e6f9e741e2362189155b9f96aa9e3bbb0995060095f1a', 'gguf-py/gguf/gguf_writer.py': '7e3ff8d04b290dde083ae30d1091b67c95299f6865958fe1cdcb7e35dd201766', 'ggml/include/ggml.h': '12ee71f99db7db9b353bc02b1fbb57c344ee17c01ac5fb7952b41a637a747ea9', 'ggml/src/ggml-common.h': '0061131b615c5721fc88a78feeb22c1f8c450f1c2646a317d80796a653bf595c', 'src/llama-vocab.cpp': '82e8996cbbd81c1648b1f4946b5f481138aa897a1343dcd8b1a4abe8cff0b5fc'}
# Pinned ggml enum/block structs, and Q4_K_M quantizer role paths only.
TYPES = {0:('f32',1,4), 12:('q4_K',256,144), 14:('q6_K',256,210)}
SCALARS = {0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'B',10:'Q',11:'q',12:'d'}
HEADER_CAP = 32*1024**2
STRING_CAP = 1024**2
ARRAY_CAP = 1_000_000
NAME = re.compile(r'[A-Za-z0-9_.-]{1,127}\Z')


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



def require_config(config):
    require(config.get('architectures') == ['Exaone4_5_ForConditionalGeneration']
            and config.get('model_type') == 'exaone4_5'
            and config.get('tie_word_embeddings') is False, 'UPSTREAM_CONFIG_UNEXPECTED')
    tc = config['text_config']
    expected = {'hidden_size':5120, 'vocab_size':153600, 'intermediate_size':27392,
                'num_hidden_layers':64, 'num_attention_heads':40, 'num_key_value_heads':8,
                'num_nextn_predict_layers':1, '_num_mtp_layers':1, 'mtp_share_layers':True,
                'sliding_window':4096, 'sliding_window_pattern':'LLLG',
                'max_position_embeddings':262144, 'hidden_act':'silu'}
    require(all(type(tc.get(k)) is type(v) and tc[k] == v for k,v in expected.items()),
            'UPSTREAM_CONFIG_UNEXPECTED')
    require(tc['layer_types'] == ['full_attention' if i%4==3 else 'sliding_attention'
                                 for i in range(64)], 'UPSTREAM_CONFIG_UNEXPECTED')
    rope = tc['rope_scaling']
    require(rope == {'factor':16.0, 'high_freq_factor':4.0, 'low_freq_factor':1.0,
                    'original_max_position_embeddings':8192, 'rope_theta':1000000.0,
                    'rope_type':'llama3'}, 'UPSTREAM_ROPE_UNEXPECTED')
    return tc


def tensor_spec(config, index):
    """Source index name coverage + pinned converter/model dimensions.

    Upstream shapes are derived from config/model code, not the shape-free index.
    The exact quantization command is unpublished. Q4_K_M's source permits Q6_K
    for attn_v/ffn_down/output; no arbitrary per-tensor override is inferred.
    """
    require_config(config)
    f32, q4, mixed = {0}, {12}, {12,14}
    spec = {'token_embd.weight':([5120,153600],q4),
            'output.weight':([5120,153600],{14}),
            'output_norm.weight':([5120],f32), 'rope_freqs.weight':([64],f32)}
    source = {'model.language_model.embed_tokens.weight',
              'model.language_model.norm.weight','lm_head.weight'}
    roles = {
      'self_attn.q_proj.weight':('attn_q',[5120,5120],q4),
      'self_attn.k_proj.weight':('attn_k',[5120,1024],q4),
      'self_attn.v_proj.weight':('attn_v',[5120,1024],mixed),
      'self_attn.o_proj.weight':('attn_output',[5120,5120],q4),
      'self_attn.q_norm.weight':('attn_q_norm',[128],f32),
      'self_attn.k_norm.weight':('attn_k_norm',[128],f32),
      'post_attention_layernorm.weight':('post_attention_norm',[5120],f32),
      'post_feedforward_layernorm.weight':('post_ffw_norm',[5120],f32),
      'mlp.gate_proj.weight':('ffn_gate',[5120,27392],q4),
      'mlp.up_proj.weight':('ffn_up',[5120,27392],q4),
      'mlp.down_proj.weight':('ffn_down',[27392,5120],mixed),
    }
    for i in range(65):
        prefix = f'model.language_model.layers.{i}' if i < 64 else 'mtp.layers.0'
        for hf,(name,dims,types) in roles.items():
            source.add(f'{prefix}.{hf}')
            spec[f'blk.{i}.{name}.weight'] = (dims,types)
    for hf,name,dims,types in [
        ('fc','eh_proj',[10240,5120],q4),
        ('pre_fc_norm_embedding','enorm',[5120],f32),
        ('pre_fc_norm_hidden','hnorm',[5120],f32),
        ('norm','shared_head_norm',[5120],f32)]:
        source.add(f'mtp.{hf}.weight')
        spec[f'blk.64.nextn.{name}.weight'] = (dims,types)
    actual = {n for n in index['weight_map'] if not n.startswith('model.visual.')}
    require(actual == source and len(source) == 722 and len(spec) == 723
            and len(index['weight_map']) == 1064, 'UPSTREAM_TEXT_MTP_INDEX_MISMATCH')
    return spec


def strings_wire_sha(strings):
    digest = hashlib.sha256()
    for value in strings:
        require(type(value) is str, 'TOKENIZER_SOURCE_INVALID')
        raw = value.encode('utf-8')
        digest.update(struct.pack('<Q',len(raw)))
        digest.update(raw)
    return digest.hexdigest()


def tokenizer_bindings(tokenizer, tokenizer_config):
    model = tokenizer['model']
    require(model['type'] == 'BPE' and model['byte_fallback'] is False
            and tokenizer['normalizer'] == {'type':'NFC'}, 'TOKENIZER_SOURCE_INVALID')
    vocab = model['vocab']
    require(len(vocab) == 153600 and all(type(v) is int for v in vocab.values())
            and set(vocab.values()) == set(range(153600)), 'TOKENIZER_SOURCE_INVALID')
    ordered = [None]*153600
    for token,idx in vocab.items():
        ordered[idx] = token
    require(len(tokenizer['added_tokens']) == 362, 'TOKENIZER_SOURCE_INVALID')
    token_types = [1]*153600  # NORMAL; converter CONTROL=3, USER_DEFINED=4.
    seen = set()
    for added in tokenizer['added_tokens']:
        idx,content = added['id'],added['content']
        require(type(idx) is int and idx not in seen and 0 <= idx < 153600
                and ordered[idx] == content and added['normalized'] is False
                and type(added['special']) is bool and '\u2581' not in content,
                'TOKENIZER_SOURCE_INVALID')
        seen.add(idx)
        looks_special = (content in ('<pad>','<mask>','<2mass>','[@BOS@]')
                         or content.startswith('<|') and content.endswith('|>')
                         or content.startswith('<｜') and content.endswith('｜>')
                         or content.startswith('<unused') and content.endswith('>'))
        token_types[idx] = 3 if added['special'] or looks_special else 4
    require(Counter(token_types) == {1:153238,3:292,4:70}, 'TOKENIZER_SOURCE_INVALID')
    merges = model['merges']
    require(len(merges) == 152982 and all(type(pair) is list and len(pair)==2
            and all(type(x) is str for x in pair) for pair in merges), 'TOKENIZER_SOURCE_INVALID')
    special = {k:vocab[tokenizer_config[k+'_token']] for k in ('bos','eos','pad','unk')}
    require(special == {'bos':1,'eos':53,'pad':0,'unk':3}, 'TOKENIZER_SOURCE_INVALID')
    return {'tokens':strings_wire_sha(ordered),
            'merges':strings_wire_sha(' '.join(x.replace(' ',chr(288)) for x in pair)
                                     for pair in merges),
            'token_type':hashlib.sha256(b''.join(struct.pack('<i',n) for n in token_types)).hexdigest(),
            'special':special}


def expected_metadata(config):
    tc = require_config(config)
    return {'general.architecture':'exaone4', 'general.type':'model',
            'general.file_type':15, 'general.quantization_version':2,
            'exaone4.block_count':65, 'exaone4.nextn_predict_layers':1,
            'exaone4.context_length':262144, 'exaone4.embedding_length':5120,
            'exaone4.feed_forward_length':27392, 'exaone4.vocab_size':153600,
            'exaone4.attention.head_count':40, 'exaone4.attention.head_count_kv':8,
            'exaone4.attention.sliding_window':4096,
            'exaone4.attention.sliding_window_pattern':[i%4!=3 for i in range(64)]+[True],
            'exaone4.attention.layer_norm_rms_epsilon':float(tc['rms_norm_eps']),
            'exaone4.rope.freq_base':1000000.0,
            'tokenizer.ggml.model':'gpt2', 'tokenizer.ggml.pre':'exaone-moe',
            'tokenizer.ggml.bos_token_id':1, 'tokenizer.ggml.eos_token_id':53,
            'tokenizer.ggml.padding_token_id':0, 'tokenizer.ggml.unknown_token_id':3}


def check_metadata_value(meta, actual, expected):
    if type(expected) is float:
        return (meta.get('type')==6 and type(actual) is float
                and math.isclose(actual,expected,rel_tol=1e-6,abs_tol=0))
    if type(expected) is list:
        return (meta.get('type')==9 and meta.get('element_type')==7
                and meta.get('count')==len(expected) and actual==expected
                and all(type(x) is bool for x in actual))
    typ = {bool:7,int:4,str:8}[type(expected)]
    return meta.get('type')==typ and type(actual) is type(expected) and actual==expected


def validate_candidate(header, values, config, index, token_bind):
    expected = expected_metadata(config)
    # Derived by the runtime when absent; contradictory explicit keys are rejected.
    optional = {'exaone4.attention.key_length':128, 'exaone4.attention.value_length':128,
                'exaone4.rope.dimension_count':128, 'exaone4.rope.scaling.type':'none',
                'tokenizer.ggml.add_bos_token':False,'tokenizer.ggml.add_eos_token':False}
    for key,value in expected.items():
        require(key in header['metadata'] and key in values, 'CONFIG_METADATA_MISSING')
        require(check_metadata_value(header['metadata'][key],values[key],value),
                'CONFIG_METADATA_MISMATCH')
    for key,value in optional.items():
        if key in header['metadata']:
            require(key in values and check_metadata_value(header['metadata'][key],values[key],value),
                    'OPTIONAL_METADATA_MISMATCH')
    require(not {k for k in header['metadata'] if k.startswith('exaone4.')} - set(expected) - set(optional),
            'ARCHITECTURE_METADATA_UNEXPECTED')
    for key,subtype,count in [('tokens',8,153600),('token_type',5,153600),('merges',8,152982)]:
        meta = header['metadata'].get('tokenizer.ggml.'+key,{})
        require(meta.get('type')==9 and meta.get('element_type')==subtype and meta.get('count')==count,
                'TOKENIZER_ARRAY_MISMATCH')
        require(meta.get('elements_wire_sha256')==token_bind[key], 'TOKENIZER_CONTENT_MISMATCH')
    require('tokenizer.ggml.scores' not in header['metadata'], 'TOKENIZER_SCORES_UNEXPECTED')
    template = header['metadata'].get('tokenizer.chat_template',{})
    require(template.get('type')==8 and template.get('bytes')==TEMPLATE_BYTES
            and template.get('sha256')==TEMPLATE_SHA, 'EMBEDDED_TEMPLATE_MISMATCH')
    spec = tensor_spec(config,index)
    require(header['tensor_count']==len(spec)==723 and len(header['tensors'])==723
            and {t['name'] for t in header['tensors']}==set(spec), 'EXPECTED_TENSOR_SET_MISMATCH')
    for row in header['tensors']:
        dims,types = spec[row['name']]
        require(row['shape']==dims and row['type_id'] in types, 'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH')
    counts = dict(Counter(t['dtype'] for t in header['tensors']))
    require(header['dtype_counts']==counts and counts.get('f32')==265
            and counts.get('q4_K',0)+counts.get('q6_K',0)==458,
            'ROLE_DTYPE_DISTRIBUTION_MISMATCH')
    largest = max(math.prod(t['shape'])*4 for t in header['tensors'] if len(t['shape'])==2)
    require(largest==3000*1024**2, 'MAX_DENSE_MATRIX_MISMATCH')
    return {'upstream_text_mtp_index_names_matched':722,
            'expected_tensor_names_shapes_matched':723,'generated_rope_tensor_count':1,
            'config_values_bound':len(expected),'main_layer_count':64,'nextn_layer_count':1,
            'stored_layer_count':65,'nextn_execution':'SKIPPED_BY_PINNED_LOADER',
            'untied_output':'Separate output.weight and token_embd.weight both required',
            'main_kv_f16_context4096_seq1_mib':1024,
            'conservative_65_layer_kv_f16_mib':1040,
            'sliding_layer_count':48,'global_layer_count':16,'sliding_window':4096,
            'largest_dense_matrix_f32_bytes':largest,
            'role_type_policy':'F32 vectors/rope; Q4_K matrices; Q6_K output; Q4_K|Q6_K attn_v and ffn_down only',
            'actual_role_dtype_counts':counts,
            'exact_per_tensor_quant_recipe':'UNPUBLISHED; source-derived role allowlist plus pinned whole-file SHA',
            'embedded_template_sha256':TEMPLATE_SHA,
            'vocabulary_order_wire_sha256':token_bind['tokens'],
            'merges_order_wire_sha256':token_bind['merges'],
            'token_type_wire_sha256':token_bind['token_type'],
            'tokenizer_pretype':'exaone-moe','tokenizer_source_normalizer':'NFC',
            'tokenizer_content_parity':'Stored vocab/merges/types only; runtime token IDs and raw roundtrip NOT_PROVED',
            'tensor_payload_numeric_validity':'NOT_DECODED_OR_TESTED'}


def load_reference():
    pins = {}
    for name,digest in SOURCE_PINS.items():
        p = Path('var/runtime-src')/('llama.cpp-'+RUNTIME)/name
        read_bound(p,digest,1024**2)
        pins[p.as_posix()] = digest
    config = json.loads(read_bound(META/'config.json',CONFIG_SHA,65536))
    index = json.loads(read_bound(META/'model.safetensors.index.json',INDEX_SHA,1024**2))
    tok = json.loads(read_bound(META/'tokenizer.json',TOKENIZER_SHA,20*1024**2))
    tokconfig = json.loads(read_bound(META/'tokenizer_config.json',TOKENIZER_CONFIG_SHA,65536))
    read_bound(META/'chat_template.jinja',TEMPLATE_SHA,65536)
    read_bound(PRETYPE_PROOF,PRETYPE_PROOF_SHA,65536)
    return config,index,tokenizer_bindings(tok,tokconfig),pins


def audit(relative, *, metadata_only=False):
    require(relative==MODEL_RELATIVE, 'PINNED_MODEL_PATH_MISMATCH')
    config,index,token_bind,pins = load_reference()
    with safe_open(ROOT,relative) as stream:
        before = os.fstat(stream.fileno())
        require(before.st_size==FILE_BYTES, 'PINNED_FILE_SIZE_MISMATCH')
        reader = Reader(stream,before.st_size)
        header,values = parse_header(reader)
        bindings,error = None,None
        try:
            bindings = validate_candidate(header,values,config,index,token_bind)
        except AuditError as exc:
            if not metadata_only:
                raise
            error = str(exc)
        header_read_bytes = reader.offset
        digest = None if metadata_only else finish_hash(reader,header)
        require(metadata_only or digest==FILE_SHA, 'PINNED_FILE_HASH_MISMATCH')
        require(stat_key(before)==stat_key(os.fstat(stream.fileno())), 'FILE_CHANGED_DURING_AUDIT')
    with safe_open(ROOT,relative) as stream:
        require(stat_key(before)==stat_key(os.fstat(stream.fileno())), 'PATH_CHANGED_DURING_AUDIT')
    return {'kind':'GGUF_METADATA_DIAGNOSTIC' if metadata_only else 'GGUF_HEADER_AUDIT',
            'status':'DIAGNOSTIC_NOT_PASS' if metadata_only else 'PASS',
            'model_id':MODEL_ID,'revision':REVISION,'model_path':relative.as_posix(),
            'upstream_model_id':UPSTREAM_MODEL_ID,'upstream_revision':UPSTREAM_REVISION,
            'gguf_conversion_upstream_revision':'NOT_PUBLISHED',
            'runtime_source_revision':RUNTIME,'file_bytes':before.st_size,
            'file_sha256':digest,'full_file_sha256_verified':not metadata_only,
            'created_utc':datetime.now(timezone.utc).isoformat(),
            'read_mode':'BOUNDED_HEADER_ONLY' if metadata_only else 'SINGLE_OPEN_FD_HEADER_THEN_PAYLOAD_SHA256_STREAM',
            'bytes_read':header_read_bytes if metadata_only else before.st_size,
            'stat_unchanged':True,'header':header,'bindings':bindings,
            'candidate_validation_error':error,
            'architecture_metadata_values':{k:v for k,v in values.items()
                                             if k.startswith('exaone4.') or k in ('general.architecture','tokenizer.ggml.pre')},
            'source_metadata_sha256':{'config':CONFIG_SHA,'template':TEMPLATE_SHA,
                'tokenizer':TOKENIZER_SHA,'tokenizer_config':TOKENIZER_CONFIG_SHA,'upstream_index':INDEX_SHA,
                'tokenizer_pretype_fingerprint':PRETYPE_PROOF_SHA},
            'runtime_source_files_sha256':pins,'copied_generic_parser_source_sha256':BASE_HELPER_SHA,
            'limits':{'header_bytes':HEADER_CAP,'single_string_bytes':STRING_CAP,
                      'array_elements':ARRAY_CAP,'metadata_entries':1024,'tensors':2048},
            'gpu_or_native_execution':False,
            'limitations':['Metadata-only mode cannot authorize a launcher and never verifies the payload hash.',
              'Header and whole-file SHA do not prove tensor numerical validity or successful native loading.',
              'Per-tensor quantization recipe and conversion upstream revision are unpublished.',
              'Official source tokenizer uses NFC; all-Unicode raw roundtrip is not guaranteed.',
              'No native tokenization/grammar/inference/VRAM/quality claim; separate candidate gates remain.',
              'MTP weights are inventoried but skipped by the pinned normal model loader.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',required=True,type=Path)
    parser.add_argument('--report',required=True,type=Path)
    parser.add_argument('--metadata-only',action='store_true')
    args = parser.parse_args()
    try:
        require(args.model==MODEL_RELATIVE, 'PINNED_MODEL_PATH_MISMATCH')
        require(args.report.parts[:2]==('var','reports'), 'REPORT_PATH_INVALID')
        result = audit(args.model,metadata_only=args.metadata_only)
        result['helper_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        payload = (json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
        with safe_open(ROOT,args.report,write=True) as stream:
            stream.write(payload)
        print(json.dumps({'kind':result['kind'],'status':result['status'],
                          'report':args.report.as_posix(),'report_sha256':hashlib.sha256(payload).hexdigest(),
                          'tensor_count':result['header']['tensor_count'],
                          'candidate_validation_error':result['candidate_validation_error']}))
    except (AuditError,OSError,ValueError,KeyError,TypeError,struct.error) as exc:
        code = str(exc) if isinstance(exc,AuditError) else 'AUDIT_INPUT_OR_IO_INVALID'
        print(json.dumps({'kind':'GGUF_METADATA_DIAGNOSTIC' if args.metadata_only else 'GGUF_HEADER_AUDIT',
                          'status':'FAIL','code':code}))
        return 1
    return 0


if __name__=='__main__':
    sys.exit(main())
