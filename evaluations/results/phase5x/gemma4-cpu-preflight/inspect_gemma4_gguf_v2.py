#!/usr/bin/env python3
"""Gemma4 official QAT GGUF audit v2, stdlib/CPU only.

V1 failed on observed Q6_K embedding, then I32 head-count array. Its original
helper/tests/FAIL are preserved separately. V2 binds these two source-supported
representations explicitly; no broad unknown-type or metadata coercion.

Root executes only after the exact artifact is downloaded and this helper reviewed.
Header/layout plus streaming full SHA; no tensor numerical decoding/native/model call.
Generic parser/path/hash functions below are unchanged from the pinned prior auditor.
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
META = Path('var/research/gemma4-31b-qat-candidate-metadata/qat-unquantized')
MODEL_ID = 'google/gemma-4-31B-it-qat-q4_0-gguf'
REVISION = '59dde24573e7e61570dba08b18a2e1fe246955ed'
QAT_MODEL_ID = 'google/gemma-4-31B-it-qat-q4_0-unquantized'
QAT_REVISION = '1e4d8beecacb8b7590c1d8bedd7335f687bf311f'
RUNTIME = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
FILENAME = 'gemma-4-31B_q4_0-it.gguf'
FILE_BYTES = 17_651_001_568
FILE_SHA = '179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b'
CONFIG_SHA = '95b105ad23b315067985415e721ab9c19cfcf90918b34ea0fa479a08489d86b7'
TEMPLATE_SHA = 'ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4'
TOKENIZER_SHA = 'cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f'
TOKENIZER_CONFIG_SHA = '3ab5c7b94dc97d65ca7064496fa69b88ff875378e1cb7ee3e43070c3a8170999'
INDEX_SHA = 'd4aff3b976d69c123a29d1c085d7ba4de1ac3f4ca1726a7f81e1b11462a64ea2'
V1_HELPER_SHA = '1fddda7d091ce617e04b696e1feef779563cef34c0028fc9ee1cc0065472ab7a'
METADATA_DIAGNOSTIC_SHA = 'ffe0e7b1187081bf238e423272a3d265ccf793fe5bdca858c3e0d61bce035dc8'
BASE_HELPER_SHA = 'cb8ef9e58aea7066c050d3e96da24708b4be4eae0c7c7498f879e2dddc41940c'
SOURCE_PINS = {
 'gguf-py/gguf/gguf_writer.py':'7e3ff8d04b290dde083ae30d1091b67c95299f6865958fe1cdcb7e35dd201766',
 'ggml/include/ggml.h':'12ee71f99db7db9b353bc02b1fbb57c344ee17c01ac5fb7952b41a637a747ea9',
 'ggml/src/ggml-common.h':'0061131b615c5721fc88a78feeb22c1f8c450f1c2646a317d80796a653bf595c',
 'ggml/src/ggml-cuda/mmq.cu':'a35bb96dfc917c9026023482e24dcf47539fc08ccee1bb4236f40932e9fe540e',
 'ggml/src/ggml-cuda/mmvq.cu':'d4c70f68ab79d463fd6fd52cac66a62e915858397ba4b2b7f658a7fbf13121f3',
 'ggml/src/ggml-cuda/convert.cu':'8ebad5e72905e1218c93e3c636c8317896ba385b07d0c41a35a432ca88654c1c',
 'conversion/gemma.py':'872f3fea7496cefdcd39308ad02e2d30c9f507f68a18f8b4f6962995b09350f5',
 'src/models/gemma4.cpp':'765ee856e30b3ddc126fa75c8252e5fbca6bae0e11abd9b71f4c21d911810ecb',
 'gguf-py/gguf/constants.py':'df0078c283a48061260ca4b3f35df36611230c3e7c2ac271bb8a11d2632839ba',
}
# Pinned ggml.h enum and ggml-common.h Q4_0 block: half d + 16 packed bytes.
TYPES = {0:('f32',1,4), 1:('f16',1,2), 2:('q4_0',32,18), 14:('q6_K',256,210), 30:('bf16',1,2)}
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
    tc = config['text_config']
    expected = {'hidden_size':5376, 'vocab_size':262144, 'intermediate_size':21504,
                'num_hidden_layers':60, 'num_attention_heads':32,
                'num_key_value_heads':16, 'num_global_key_value_heads':4,
                'head_dim':256, 'global_head_dim':512, 'sliding_window':1024,
                'hidden_size_per_layer_input':0, 'num_kv_shared_layers':0,
                'attention_k_eq_v':True, 'tie_word_embeddings':True,
                'enable_moe_block':False, 'use_double_wide_mlp':False,
                'max_position_embeddings':262144}
    require(all(type(tc.get(k)) is type(v) and tc[k] == v for k,v in expected.items()),
            'QAT_CONFIG_UNEXPECTED')
    layers = ['full_attention' if i % 6 == 5 else 'sliding_attention' for i in range(60)]
    require(tc['layer_types'] == layers and config['tie_word_embeddings'] is True,
            'QAT_CONFIG_UNEXPECTED')
    return tc


def tensor_spec(config, index):
    """Fixed dense text names/shapes; index independently binds source name coverage.

    The 832 HF text names lack shapes. Shapes come from config + pinned model graph;
    the converter additionally emits one shared F32 proportional-RoPE tensor.
    We do not attribute a public converter log or exact conversion commit to Google.
    """
    tc = require_config(config)
    matrix = {0,1,2,30}
    floating = {0,1,30}
    spec = {'token_embd.weight':([5376,262144],{14}),
            'output_norm.weight':([5376],floating),
            'rope_freqs.weight':([256],{0})}
    source = {'model.language_model.embed_tokens.weight','model.language_model.norm.weight'}
    roles = {
      'input_layernorm.weight':('attn_norm',[5376],floating),
      'post_attention_layernorm.weight':('post_attention_norm',[5376],floating),
      'pre_feedforward_layernorm.weight':('ffn_norm',[5376],floating),
      'post_feedforward_layernorm.weight':('post_ffw_norm',[5376],floating),
      'layer_scalar':('layer_output_scale',[1],floating),
      'mlp.gate_proj.weight':('ffn_gate',[5376,21504],matrix),
      'mlp.up_proj.weight':('ffn_up',[5376,21504],matrix),
      'mlp.down_proj.weight':('ffn_down',[21504,5376],matrix),
    }
    for i,kind in enumerate(tc['layer_types']):
        hd,kv = (512,4) if kind == 'full_attention' else (256,16)
        local = dict(roles)
        local.update({
          'self_attn.q_proj.weight':('attn_q',[5376,32*hd],matrix),
          'self_attn.k_proj.weight':('attn_k',[5376,kv*hd],matrix),
          'self_attn.o_proj.weight':('attn_output',[32*hd,5376],matrix),
          'self_attn.q_norm.weight':('attn_q_norm',[hd],floating),
          'self_attn.k_norm.weight':('attn_k_norm',[hd],floating),
        })
        if kind == 'sliding_attention':
            local['self_attn.v_proj.weight'] = ('attn_v',[5376,kv*hd],matrix)
        for hf,(name,dims,types) in local.items():
            source.add(f'model.language_model.layers.{i}.{hf}')
            spec[f'blk.{i}.{name}.weight'] = (dims,types)
    actual = {name for name in index['weight_map'] if name.startswith('model.language_model.')}
    require(actual == source and len(source) == 832 and len(spec) == 833,
            'QAT_TEXT_INDEX_COVERAGE_MISMATCH')
    require(all(name.startswith(('model.language_model.','model.vision_tower.')) or
                name == 'model.embed_vision.embedding_projection.weight'
                for name in index['weight_map']), 'QAT_INDEX_NAMESPACE_UNEXPECTED')
    return spec


def strings_wire_sha(strings):
    digest = hashlib.sha256()
    for value in strings:
        require(type(value) is str, 'TOKENIZER_SOURCE_INVALID')
        b = value.encode('utf-8')
        digest.update(struct.pack('<Q',len(b)))
        digest.update(b)
    return digest.hexdigest()


def tokenizer_bindings(tokenizer, tokenizer_config):
    model = tokenizer['model']
    require(model['type'] == 'BPE' and model['byte_fallback'] is True,
            'TOKENIZER_SOURCE_INVALID')
    vocab = model['vocab']
    require(len(vocab) == 262144 and all(type(v) is int for v in vocab.values())
            and set(vocab.values()) == set(range(262144)), 'TOKENIZER_SOURCE_INVALID')
    ordered = [None]*262144
    for token,idx in vocab.items():
        ordered[idx] = token
    for token in tokenizer['added_tokens']:
        require(type(token['id']) is int and 0 <= token['id'] < len(ordered)
                and ordered[token['id']] == token['content'], 'TOKENIZER_SOURCE_INVALID')
    merges = model['merges']
    require(len(merges) == 514906, 'TOKENIZER_SOURCE_INVALID')
    require(all(type(pair) is list and len(pair) == 2 and
                all(type(x) is str for x in pair) for pair in merges), 'TOKENIZER_SOURCE_INVALID')
    # Same space encoding as the pinned gguf.SpecialVocab conversion.
    merge_strings = (' '.join(x.replace(' ',chr(288)) for x in pair) for pair in merges)
    special = {key:vocab[tokenizer_config[key+'_token']] for key in ('bos','eos','pad','unk')}
    require(special == {'bos':2,'eos':1,'pad':0,'unk':3}, 'TOKENIZER_SOURCE_INVALID')
    return {'tokens':strings_wire_sha(ordered), 'merges':strings_wire_sha(merge_strings),
            'special':special}


def validate_candidate(header, values, config, index, token_bind):
    tc = require_config(config)
    expected = {
      'general.architecture':'gemma4', 'general.type':'model',
      'general.file_type':2, 'general.quantization_version':2,
      'gemma4.block_count':60, 'gemma4.context_length':262144,
      'gemma4.embedding_length':5376, 'gemma4.feed_forward_length':21504,
      'gemma4.attention.head_count':32,
      'gemma4.attention.head_count_kv':[4 if i%6==5 else 16 for i in range(60)],
      'gemma4.attention.key_length':512, 'gemma4.attention.value_length':512,
      'gemma4.attention.key_length_swa':256, 'gemma4.attention.value_length_swa':256,
      'gemma4.attention.sliding_window':1024,
      'gemma4.attention.sliding_window_pattern':[i%6!=5 for i in range(60)],
      'gemma4.attention.shared_kv_layers':0, 'gemma4.embedding_length_per_layer_input':0,
      'gemma4.attention.layer_norm_rms_epsilon':float(tc['rms_norm_eps']),
      'gemma4.final_logit_softcapping':float(tc['final_logit_softcapping']),
      'gemma4.rope.freq_base':1000000.0, 'gemma4.rope.freq_base_swa':10000.0,
      'gemma4.rope.dimension_count':512, 'gemma4.rope.dimension_count_swa':256,
      'tokenizer.ggml.model':'gemma4', 'tokenizer.ggml.bos_token_id':2,
      'tokenizer.ggml.eos_token_id':1, 'tokenizer.ggml.padding_token_id':0,
      'tokenizer.ggml.unknown_token_id':3, 'tokenizer.ggml.add_bos_token':True,
      'tokenizer.ggml.add_space_prefix':False,
    }
    for k,v in expected.items():
        actual = values.get(k)
        require(k in header['metadata'] and k in values, 'CONFIG_METADATA_MISSING')
        meta = header['metadata'][k]
        if type(v) is float:
            require(meta['type'] == 6 and type(actual) is float and
                    math.isclose(actual,v,rel_tol=1e-6,abs_tol=0), 'CONFIG_METADATA_MISMATCH')
        elif type(v) is list:
            subtype = 7 if type(v[0]) is bool else 5
            require(meta['type'] == 9 and meta['element_type'] == subtype and meta['count'] == 60
                    and actual == v and all(type(a) is type(b) for a,b in zip(actual,v)),
                    'CONFIG_ARRAY_MISMATCH')
        else:
            typ = 7 if type(v) is bool else 4 if type(v) is int else 8
            require(meta['type'] == typ and type(actual) is type(v) and actual == v,
                    'CONFIG_METADATA_MISMATCH')
    for key,subtype,count in [('tokens',8,262144),('scores',6,262144),
                              ('token_type',5,262144),('merges',8,514906)]:
        meta = header['metadata'].get('tokenizer.ggml.'+key,{})
        require(meta.get('type') == 9 and meta.get('element_type') == subtype
                and meta.get('count') == count, 'TOKENIZER_ARRAY_MISMATCH')
        if key in ('tokens','merges'):
            require(meta['elements_wire_sha256'] == token_bind[key], 'TOKENIZER_CONTENT_MISMATCH')
    template = header['metadata'].get('tokenizer.chat_template',{})
    require(template.get('type') == 8 and template.get('bytes') == 18683
            and template.get('sha256') == TEMPLATE_SHA, 'EMBEDDED_TEMPLATE_MISMATCH')
    expected_tensors = tensor_spec(config,index)
    require(header['tensor_count'] == len(expected_tensors) == 833 and
            {t['name'] for t in header['tensors']} == set(expected_tensors),
            'EXPECTED_TENSOR_SET_MISMATCH')
    for row in header['tensors']:
        shape,types = expected_tensors[row['name']]
        require(row['shape'] == shape and row['type_id'] in types,
                'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH')
    require(header['dtype_counts'] == {'f32':422,'q6_K':1,'q4_0':410},
            'OBSERVED_ROLE_DTYPE_DISTRIBUTION_MISMATCH')
    require(sum(header['dtype_counts'].values()) == 833, 'DTYPE_COUNT_MISMATCH')
    # Compute budget-related actual payload geometry; no floating payload decoding.
    largest_f32 = max(math.prod(t['shape'])*4 for t in header['tensors'] if len(t['shape']) == 2)
    require(largest_f32 == 5376*1024**2, 'MAX_DENSE_MATRIX_MISMATCH')
    return {'config_values_bound':len(expected), 'qat_text_index_names_matched':832,
            'expected_tensor_names_shapes_matched':833, 'generated_rope_tensor_count':1,
            'conversion_log_tensors_matched':None,
            'matrix_type_policy':['q4_0','f16','bf16','f32'],
            'embedding_type_policy':['q6_K'], 'q6_k_permitted_tensor':'token_embd.weight',
            'actual_role_dtype_counts':dict(header['dtype_counts']),
            'head_count_kv_array_wire_type':'INT32(5)',
            'vector_type_policy':['f16','bf16','f32'], 'rope_type_policy':['f32'],
            'exact_per_tensor_quant_recipe':'UNPUBLISHED; allowed role types plus whole-file SHA',
            'per_layer_embedding_width':0, 'shared_kv_layer_count':0,
            'sliding_layer_count':50, 'global_layer_count':10,
            'kv_f16_context4096_seq1_ubatch64_swa_full_false_mib':1320,
            'largest_dense_matrix_f32_bytes':largest_f32,
            'tied_output':'No separate output.weight; native input CPU/output GPU mapping',
            'tokenizer_counts_bound':True, 'vocabulary_order_wire_sha256':token_bind['tokens'],
            'merges_order_wire_sha256':token_bind['merges'],
            'embedded_template_sha256':TEMPLATE_SHA,
            'tokenizer_content_parity':'VOCAB_AND_MERGES_EXACT; runtime normalization/tokenization NOT_PROVED',
            'token_score_type_content':'Counts/types bound; values retained as wire hash, not HF-ID proof',
            'tensor_payload_numeric_validity':'NOT_DECODED_OR_TESTED'}


def audit(relative):
    source_pins = {}
    for path,digest in SOURCE_PINS.items():
        full = Path('var/runtime-src')/('llama.cpp-'+RUNTIME)/path
        read_bound(full,digest,1024**2)
        source_pins[full.as_posix()] = digest
    config = json.loads(read_bound(META/'config.json',CONFIG_SHA,64*1024))
    index = json.loads(read_bound(META/'model.safetensors.index.json',INDEX_SHA,1024**2))
    tokconfig = json.loads(read_bound(META/'tokenizer_config.json',TOKENIZER_CONFIG_SHA,1024**2))
    tokenizer = json.loads(read_bound(META/'tokenizer.json',TOKENIZER_SHA,40*1024**2))
    read_bound(META/'chat_template.jinja',TEMPLATE_SHA,64*1024)
    token_bind = tokenizer_bindings(tokenizer,tokconfig)
    del tokenizer,tokconfig
    with safe_open(ROOT,relative) as f:
        before = os.fstat(f.fileno())
        require(before.st_size == FILE_BYTES, 'PINNED_FILE_SIZE_MISMATCH')
        reader = Reader(f,before.st_size)
        header,values = parse_header(reader)
        bindings = validate_candidate(header,values,config,index,token_bind)
        digest = finish_hash(reader,header)
        require(digest == FILE_SHA, 'PINNED_FILE_HASH_MISMATCH')
        require(stat_key(before) == stat_key(os.fstat(f.fileno())), 'FILE_CHANGED_DURING_AUDIT')
    with safe_open(ROOT,relative) as f:
        require(stat_key(before) == stat_key(os.fstat(f.fileno())), 'PATH_CHANGED_DURING_AUDIT')
    return {'kind':'GGUF_HEADER_AUDIT','status':'PASS','model_id':MODEL_ID,
            'model_path':relative.as_posix(),'revision':REVISION,
            'upstream_model_id':QAT_MODEL_ID,'upstream_revision':QAT_REVISION,
            'gguf_conversion_upstream_revision':'NOT_PUBLISHED',
            'runtime_source_revision':RUNTIME,'file_sha256':digest,'file_bytes':before.st_size,
            'created_utc':datetime.now(timezone.utc).isoformat(),
            'read_mode':'SINGLE_OPEN_FD_HEADER_THEN_PAYLOAD_SHA256_STREAM',
            'stat_unchanged':True,'header':header,'bindings':bindings,
            'source_metadata_sha256':{'config':CONFIG_SHA,'template':TEMPLATE_SHA,
              'tokenizer':TOKENIZER_SHA,'tokenizer_config':TOKENIZER_CONFIG_SHA,'qat_index':INDEX_SHA},
            'runtime_source_files_sha256':source_pins,
            'copied_generic_parser_source_sha256':BASE_HELPER_SHA,
            'superseded_v1_helper_sha256':V1_HELPER_SHA,
            'metadata_diagnostic_sha256':METADATA_DIAGNOSTIC_SHA,
            'limits':{'header_bytes':HEADER_CAP,'single_string_bytes':STRING_CAP,
                      'array_elements':ARRAY_CAP,'metadata_entries':1024,'tensors':2048},
            'gpu_or_native_execution':False,
            'limitations':['Full-file SHA and exact header layout only; tensor numeric values are not decoded.',
              'No native tokenizer/grammar/inference/VRAM or semantic quality proof.',
              'QAT config/index identity does not prove unpublished GGUF conversion revision.',
              'Per-tensor quant recipe is not published; role allowlists are explicit, not a convert-log attestation.',
              'Later opener must bind the same owned immutable artifact.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',required=True,type=Path)
    parser.add_argument('--report',required=True,type=Path)
    args = parser.parse_args()
    try:
        require(args.model.parts[:2] == ('var','models') and args.model.name == FILENAME
                and args.model.parent.name == REVISION, 'PINNED_MODEL_PATH_MISMATCH')
        require(args.report.parts[:2] == ('var','reports'), 'REPORT_PATH_INVALID')
        result = audit(args.model)
        result['helper_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        payload = (json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
        with safe_open(ROOT,args.report,write=True) as f:
            f.write(payload)
        print(json.dumps({'kind':'GGUF_HEADER_AUDIT','status':'PASS','report':args.report.as_posix(),
              'report_sha256':hashlib.sha256(payload).hexdigest(),'tensor_count':result['header']['tensor_count']}))
    except (AuditError,OSError,ValueError,KeyError,TypeError,struct.error) as exc:
        code = str(exc) if isinstance(exc,AuditError) else 'AUDIT_INPUT_OR_IO_INVALID'
        print(json.dumps({'kind':'GGUF_HEADER_AUDIT','status':'FAIL','code':code}))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
